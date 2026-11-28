"""Merged LAN device discovery (Windows Neighbor IPv4/IPv6 + ARP + Router API) and bandwidth control."""

from __future__ import annotations

import asyncio
import json
import re
import socket
import subprocess
import sys
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

import psutil

from app.monitoring.device_discovery import LocalNetworkScanner
from app.wifi.coordinator import DiagnosticCoordinator
from app.wifi.models import (
    ConnectedDeviceRecord,
    RouterApplyResult,
    RouterChangeProposal,
    utc_now,
)
from app.wifi.router.adapters.base import IRouterAdapter

_OUI_SCANNER = LocalNetworkScanner()


def _local_host_ips_and_macs() -> tuple[set[str], set[str], Dict[str, str]]:
    ips: set[str] = set()
    macs: set[str] = set()
    ip_to_mac: Dict[str, str] = {}
    try:
        for _, addr_list in psutil.net_if_addrs().items():
            if_ips: List[str] = []
            if_mac: Optional[str] = None
            for a in addr_list:
                if a.family == socket.AF_INET and not a.address.startswith("127."):
                    ips.add(a.address)
                    if_ips.append(a.address)
                elif a.family == getattr(psutil, "AF_LINK", -1) and a.address:
                    mac = a.address.replace("-", ":").lower()
                    if mac and mac != "00:00:00:00:00:00":
                        macs.add(mac)
                        if_mac = mac
            if if_mac:
                for ip_addr in if_ips:
                    ip_to_mac[ip_addr] = if_mac
    except Exception:
        pass
    return ips, macs, ip_to_mac


def _win_popen_kwargs() -> Dict[str, Any]:
    if sys.platform != "win32":
        return {}
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return {"startupinfo": si, "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}


def _probe_local_subnet_arp_wakeup(gateway_ip: Optional[str] = None) -> None:
    """Populate the Windows/OS ARP table with active LAN peers via fast non-blocking UDP probes."""
    local_ips, _, _ = _local_host_ips_and_macs()
    if not local_ips:
        return
    target_ip: Optional[str] = None
    if gateway_ip and re.match(r"^\d+\.\d+\.\d+\.\d+$", gateway_ip):
        gw_prefix = gateway_ip.rsplit(".", 1)[0]
        target_ip = next((ip for ip in local_ips if ip.rsplit(".", 1)[0] == gw_prefix), gateway_ip)
    if target_ip is None:
        target_ip = next(
            (ip for ip in local_ips if ip.startswith(("192.168.", "10.", "172."))),
            next(iter(local_ips), None),
        )
    if not target_ip:
        return
    prefix = target_ip.rsplit(".", 1)[0]
    sock: Optional[socket.socket] = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        for host_octet in range(1, 255):
            dst = f"{prefix}.{host_octet}"
            if dst in local_ips:
                continue
            try:
                sock.sendto(b"", (dst, 9))
            except OSError:
                pass
        # Allow L2 ARP replies from sleeping/idle phones, TVs, and APs to land in NetNeighbor/ARP cache
        time.sleep(0.4)
    except Exception:
        pass
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass


def _read_os_arp_devices(gateway_ip: Optional[str] = None, *, probe_subnet: bool = True) -> List[ConnectedDeviceRecord]:
    """Merge Windows Get-NetNeighbor (IPv4+IPv6 ND), arp -a, and active local host interfaces."""
    if probe_subnet and sys.platform == "win32":
        _probe_local_subnet_arp_wakeup(gateway_ip)
    local_ips, local_macs, ip_to_mac = _local_host_ips_and_macs()
    by_mac: Dict[str, ConnectedDeviceRecord] = {}
    records: List[ConnectedDeviceRecord] = []

    def _upsert(
        ip_s: Optional[str],
        mac_s: Optional[str],
        state_str: str,
        src_name: str,
        is_ipv6: bool = False,
    ) -> None:
        norm_mac = mac_s.replace("-", ":").lower() if mac_s else None
        if norm_mac in ("ff:ff:ff:ff:ff:ff", "00:00:00:00:00:00", ""):
            return
        if ip_s and (
            ip_s.startswith(("224.", "239.", "255.", "169.254.", "fe80:", "ff0"))
            or ip_s == "255.255.255.255"
        ):
            # Still attach valid non-link-local IPv6 to existing MAC if known
            if is_ipv6 and norm_mac and norm_mac in by_mac and not ip_s.startswith(("fe80:", "ff0")):
                if ip_s not in by_mac[norm_mac].ipv6_addresses:
                    by_mac[norm_mac].ipv6_addresses.append(ip_s)
            return

        vendor = _OUI_SCANNER.lookup_vendor(norm_mac) if norm_mac else None
        if vendor == "Unknown":
            vendor = None

        st_low = (state_str or "").lower()
        conn_status = (
            "connected"
            if any(k in st_low for k in ("reachable", "permanent", "dynamic"))
            else ("stale" if any(k in st_low for k in ("stale", "delay", "probe", "incomplete")) else "unknown")
        )

        if norm_mac and norm_mac in by_mac:
            rec = by_mac[norm_mac]
            if is_ipv6 and ip_s:
                if ip_s not in rec.ipv6_addresses:
                    rec.ipv6_addresses.append(ip_s)
            elif ip_s and not rec.ip_address:
                rec.ip_address = ip_s
            if src_name not in rec.discovery_sources:
                rec.discovery_sources.append(src_name)
            if conn_status == "connected":
                rec.connection_status = "connected"
            rec.vendor = rec.vendor or vendor
            return

        rec = ConnectedDeviceRecord(
            ip_address=None if is_ipv6 else ip_s,
            ipv6_addresses=[ip_s] if (is_ipv6 and ip_s) else [],
            mac_address=norm_mac,
            vendor=vendor,
            connection_type="unknown",
            connection_status=conn_status,
            last_seen=utc_now() if conn_status == "connected" else None,
            is_local_host=bool((ip_s and ip_s in local_ips) or (norm_mac and norm_mac in local_macs)),
            is_gateway=bool(gateway_ip and ip_s == gateway_ip),
            source="os_arp",
            discovery_sources=[src_name],
            supports_rate_limit=False,
        )
        if norm_mac:
            by_mac[norm_mac] = rec
        records.append(rec)

    # 1) Windows Get-NetNeighbor (IPv4 + IPv6 ND + Reachable/Stale classification)
    if sys.platform == "win32":
        try:
            ps_cmd = (
                "Get-NetNeighbor -ErrorAction SilentlyContinue | "
                "Where-Object { $_.LinkLayerAddress -and $_.LinkLayerAddress -ne '00-00-00-00-00-00' } | "
                "Select-Object IPAddress,LinkLayerAddress,State,AddressFamily | ConvertTo-Json -Compress"
            )
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=3.5,
                **_win_popen_kwargs(),
            )
            raw_json = (proc.stdout or "").strip()
            if raw_json.startswith(("{", "[")):
                items = json.loads(raw_json)
                if isinstance(items, dict):
                    items = [items]
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    ip_s = str(it.get("IPAddress") or "").strip()
                    mac_s = str(it.get("LinkLayerAddress") or "").strip()
                    st_s = str(it.get("State") or "").strip()
                    af = str(it.get("AddressFamily") or "")
                    _upsert(ip_s, mac_s, st_s, "windows_netneighbor", is_ipv6=(":" in ip_s or "IPv6" in af))
        except Exception:
            pass

    # 2) arp -a fallback (cross-platform & ensures dynamic ARP cache entries present)
    try:
        proc = subprocess.run(
            ["arp", "-a"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=2.5,
            **_win_popen_kwargs(),
        )
        for line in (proc.stdout or "").splitlines():
            m = re.search(
                r"(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F]{2}(?:[:-][0-9a-fA-F]{2}){5})\s+(\S+)",
                line,
            )
            if not m:
                continue
            ip_s, mac_s, kind = m.group(1), m.group(2), m.group(3).lower()
            if "static" in kind and gateway_ip != ip_s:
                # Filter Windows broadcast/multicast static placeholders unless it's the gateway
                continue
            _upsert(ip_s, mac_s, kind, "os_arp", is_ipv6=False)
    except Exception:
        pass

    # 3) Local PC host representation if on active subnet and not already listed
    if local_ips:
        host_name = socket.gethostname()
        primary_ip = next((ip for ip in local_ips if not gateway_ip or ip.rsplit(".", 1)[0] == gateway_ip.rsplit(".", 1)[0]), next(iter(local_ips)))
        primary_mac = ip_to_mac.get(primary_ip) or next(iter(local_macs), None)
        if not any(r.is_local_host for r in records):
            records.append(
                ConnectedDeviceRecord(
                    ip_address=primary_ip,
                    mac_address=primary_mac,
                    hostname=host_name,
                    vendor=_OUI_SCANNER.lookup_vendor(primary_mac) if primary_mac else "Local PC",
                    connection_type="unknown",
                    connection_status="connected",
                    last_seen=utc_now(),
                    is_local_host=True,
                    is_gateway=False,
                    source="os_arp",
                    discovery_sources=["local_interface"],
                    supports_rate_limit=False,
                    notes=["هذا الجهاز (NetGuard PC)."],
                )
            )
        else:
            for r in records:
                if r.is_local_host and not r.hostname:
                    r.hostname = host_name
                    r.connection_status = "connected"

    # 4) Concurrent reverse-DNS + NetBIOS/LAA enrichment so LAN devices never appear nameless when resolvable
    unresolved = [r for r in records if r.ip_address and not r.hostname and not r.is_gateway]
    if unresolved and probe_subnet:
        from concurrent.futures import ThreadPoolExecutor

        def _resolve_one(rec: ConnectedDeviceRecord) -> None:
            ip = rec.ip_address or ""
            try:
                name, _, _ = socket.gethostbyaddr(ip)
                if name and name != ip:
                    rec.hostname = name.split(".", 1)[0]
            except Exception:
                pass
            if not rec.hostname and sys.platform == "win32":
                try:
                    nb = subprocess.run(
                        ["nbtstat", "-A", ip],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=0.5,
                        **_win_popen_kwargs(),
                    )
                    m_nb = re.search(r"^\s*([A-Za-z0-9_\-]{2,15})\s+<00>\s+UNIQUE", nb.stdout or "", re.M)
                    if m_nb:
                        rec.hostname = m_nb.group(1).strip()
                except Exception:
                    pass

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(_resolve_one, unresolved[:24]))

    for r in records:
        if r.is_gateway and not r.hostname:
            r.hostname = "الراوتر الرئيسي (Gateway)"
            if r.vendor in (None, "ZTE Corporation", "Unknown"):
                r.vendor = "Gateway Router"
        elif not r.hostname and not r.vendor and r.mac_address:
            try:
                first_b = int(r.mac_address.split(":")[0], 16)
                if first_b & 0x02:
                    r.vendor = "هاتف / جهاز محمول (MAC خاص)"
            except Exception:
                pass

    return records


class DeviceManagementService:
    """Combines Windows neighbor/ARP discovery + router device APIs with strict limitation honesty."""

    def __init__(
        self,
        *,
        platform: Any = None,
        coordinator: Optional[DiagnosticCoordinator] = None,
    ) -> None:
        self._platform = platform
        self._coordinator = coordinator

    async def list_connected_devices(
        self,
        *,
        adapter: Optional[IRouterAdapter] = None,
        gateway_ip: Optional[str] = None,
        gateway_vendor_override: Optional[str] = None,
    ) -> tuple[List[ConnectedDeviceRecord], bool, str]:
        """Return (merged_devices, per_device_rate_limit_supported, limitation_explanation)."""
        if gateway_ip is None and self._platform is not None and hasattr(
            self._platform, "get_default_gateway"
        ):
            try:
                gw = self._platform.get_default_gateway()
                if asyncio.iscoroutine(gw) or hasattr(gw, "__await__"):
                    gw = await gw
                gateway_ip = str(gw) if gw else None
            except Exception:
                pass

        arp_devs = await asyncio.to_thread(_read_os_arp_devices, gateway_ip)
        router_devs: List[ConnectedDeviceRecord] = []
        supports_rate_limit = False

        if adapter is not None:
            caps = adapter.capabilities()
            supports_rate_limit = bool(caps.supports_per_device_bandwidth and adapter.is_authenticated)
            if adapter.is_authenticated and caps.supports_connected_devices_read:
                try:
                    router_devs = await asyncio.to_thread(adapter.get_connected_devices)
                except Exception:
                    router_devs = []

        # Merge by MAC first, fallback by IP
        by_mac: Dict[str, ConnectedDeviceRecord] = {}
        merged: List[ConnectedDeviceRecord] = []
        for d in arp_devs:
            if d.mac_address:
                by_mac[d.mac_address.lower()] = d
            merged.append(d)

        for rd in router_devs:
            key = (rd.mac_address or "").lower()
            vendor = rd.vendor or (_OUI_SCANNER.lookup_vendor(key) if key else None)
            if vendor == "Unknown":
                vendor = None
            if key and key in by_mac:
                existing = by_mac[key]
                existing.hostname = rd.hostname or existing.hostname
                existing.vendor = existing.vendor or vendor
                existing.connection_type = (
                    rd.connection_type
                    if rd.connection_type != "unknown"
                    else existing.connection_type
                )
                existing.connection_status = (
                    rd.connection_status
                    if rd.connection_status != "unknown"
                    else existing.connection_status
                )
                existing.radio_band = rd.radio_band or existing.radio_band
                existing.ssid = rd.ssid or existing.ssid
                existing.rssi_dbm = rd.rssi_dbm
                existing.link_rate_mbps = rd.link_rate_mbps
                existing.tx_rate_mbps = rd.tx_rate_mbps
                existing.rx_rate_mbps = rd.rx_rate_mbps
                existing.rx_limit_kbps = rd.rx_limit_kbps
                existing.tx_limit_kbps = rd.tx_limit_kbps
                existing.router_metadata = rd.router_metadata or existing.router_metadata
                existing.source = "merged"
                if "router_api" not in existing.discovery_sources:
                    existing.discovery_sources.append("router_api")
                existing.supports_rate_limit = supports_rate_limit
            else:
                rd_copy = rd.model_copy(
                    update={
                        "vendor": vendor,
                        "supports_rate_limit": supports_rate_limit,
                        "is_gateway": bool(gateway_ip and rd.ip_address == gateway_ip),
                        "discovery_sources": rd.discovery_sources or ["router_api"],
                    }
                )
                merged.append(rd_copy)

        merged.sort(
            key=lambda d: (
                not d.is_gateway,
                not d.is_local_host,
                d.connection_status != "connected",
                d.ip_address or "255.255.255.255",
            )
        )
        if gateway_vendor_override:
            for d in merged:
                if d.is_gateway:
                    d.vendor = gateway_vendor_override

        if supports_rate_limit:
            note = (
                "الراوتر يدعم تحديد السرعة لكل جهاز عبر الواجهة المصادق عليها؛ كل تعديل يتطلب موافقة مسبقة وتحققاً بالقراءة العكسية. "
                "(تذكير: سياسات Windows QoS في NetGuard تنطبق على هذا الكمبيوتر فقط وليس على الأجهزة الأخرى)."
            )
        else:
            note = (
                "التحكم في سرعة كل جهاز منفرداً غير متاح عبر واجهة هذا الراوتر أو لم يتم تسجيل الدخول المصادق بعد. "
                "سياسات NetGuard QoS على Windows تحكم حركة هذا الكمبيوتر فقط؛ للتحكم في أجهزة المنزل الأخرى استخدم صفحة QoS / Bandwidth Control في الراوتر مباشرة."
            )
        return merged, supports_rate_limit, note

    def apply_router_change_safely(
        self,
        *,
        adapter: Optional[IRouterAdapter],
        proposal: RouterChangeProposal,
        explicit_user_approval: bool = False,
    ) -> RouterApplyResult:
        """Apply a staged router change only after approval, meeting check, backup, and readback check."""
        if not explicit_user_approval:
            return RouterApplyResult(
                proposal_id=proposal.proposal_id,
                success=False,
                message="Explicit user approval is required before modifying router configuration.",
            )

        if adapter is None or not adapter.is_authenticated:
            return RouterApplyResult(
                proposal_id=proposal.proposal_id,
                success=False,
                message=(
                    "Router is not authenticated with a writable adapter. "
                    "Use the manual instructions in the proposal inside the router portal."
                ),
            )

        if proposal.requires_reconnect_warning and self._coordinator is not None:
            active, reason = self._coordinator.is_meeting_active()
            if active:
                return RouterApplyResult(
                    proposal_id=proposal.proposal_id,
                    success=False,
                    message=f"Blocked during active meeting because this router change drops Wi-Fi briefly: {reason}",
                )

        return adapter.safe_apply_change(
            proposal, explicit_user_approval=explicit_user_approval
        )

    def set_device_bandwidth_limit(
        self,
        *,
        adapter: Optional[IRouterAdapter],
        device: ConnectedDeviceRecord,
        rx_limit_kbps: int,
        tx_limit_kbps: int,
        explicit_user_approval: bool = False,
    ) -> RouterApplyResult:
        """Apply per-device bandwidth cap via router adapter only if authentically supported."""
        prop_id = f"devcap_{uuid.uuid4().hex[:6]}"
        if adapter is None or not adapter.is_authenticated:
            return RouterApplyResult(
                proposal_id=prop_id,
                success=False,
                message=(
                    "Router authentication is required. Local Windows OS cannot enforce upload/download rate caps on external household devices."
                ),
            )

        caps = adapter.capabilities()
        if not caps.supports_per_device_bandwidth:
            return RouterApplyResult(
                proposal_id=prop_id,
                success=False,
                message=(
                    f"Unsupported by adapter '{adapter.adapter_id}': this router firmware does not expose per-device rate limiting. "
                    "Alternatives: use NetGuard local per-app QoS for this PC or configure QoS/SQM manually in the router UI."
                ),
            )

        proposal = RouterChangeProposal(
            proposal_id=prop_id,
            category="device_rate_limit",
            title=f"Limit {device.hostname or device.ip_address or device.mac_address}",
            target_field=f"device_limit:{device.mac_address or device.ip_address}",
            band=None,
            current_value=f"rx={device.rx_limit_kbps},tx={device.tx_limit_kbps}",
            proposed_value=f"rx={rx_limit_kbps},tx={tx_limit_kbps}",
            reason="User requested per-device bandwidth ceiling.",
            expected_impact=f"Caps client at {rx_limit_kbps} kbps DL / {tx_limit_kbps} kbps UL.",
            risk_level="medium",
            requires_reconnect_warning=False,
            supported_by_adapter=True,
            requires_manual_apply=False,
        )
        return adapter.safe_apply_change(
            proposal, explicit_user_approval=explicit_user_approval
        )


ConnectedDeviceDiscoveryService = DeviceManagementService
