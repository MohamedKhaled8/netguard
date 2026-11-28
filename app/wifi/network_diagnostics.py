"""Sequential network baseline, gateway/public/IPv6 ICMP bursts, 5-hop trace, and condition analysis."""

from __future__ import annotations

import asyncio
import ipaddress
import os
import re
import socket
import statistics
import subprocess
import sys
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

import psutil

from app.diagnosis.traceroute import IcmpTracerouteEngine
from app.wifi.coordinator import CancellationToken, DiagnosticCoordinator
from app.wifi.models import (
    NetworkConditionReport,
    NetworkDiagnosticsReport,
    PingBurstStats,
    TracerouteDiagnosticResult,
    TracerouteHopSummary,
    utc_now,
)
from app.wifi.telemetry import WifiTelemetryService, _subprocess_kwargs

if sys.platform == "win32":
    import winreg


def _percentile(values: List[float], pct: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return round(ordered[idx], 2)


def _compute_jitter(rtts: List[float]) -> Optional[float]:
    """Compute sequential latency variation (mean absolute step difference) in ms."""
    if len(rtts) < 2:
        return 0.0 if len(rtts) == 1 else None
    diffs = [abs(rtts[i] - rtts[i - 1]) for i in range(1, len(rtts))]
    return round(sum(diffs) / len(diffs), 2)


def _summarize_burst(
    target: str,
    address_family: str,
    sent: int,
    rtts: List[float],
    started_at: Any,
    completed_at: Any,
    *,
    note: Optional[str] = None,
) -> PingBurstStats:
    received = len(rtts)
    loss_pct = round(((sent - received) / sent) * 100.0, 2) if sent > 0 else 100.0
    if received == 0:
        return PingBurstStats(
            target=target,
            address_family=address_family,  # type: ignore[arg-type]
            status="unreachable",
            packets_sent=sent,
            packets_received=0,
            packet_loss_pct=loss_pct,
            rtts_ms=[],
            started_at=started_at,
            completed_at=completed_at,
            note=note or "No ICMP echo replies received.",
        )
    return PingBurstStats(
        target=target,
        address_family=address_family,  # type: ignore[arg-type]
        status="ok",
        packets_sent=sent,
        packets_received=received,
        packet_loss_pct=loss_pct,
        avg_ms=round(statistics.fmean(rtts), 2),
        min_ms=round(min(rtts), 2),
        max_ms=round(max(rtts), 2),
        jitter_ms=_compute_jitter(rtts),
        p95_ms=_percentile(rtts, 95.0),
        rtts_ms=[round(r, 2) for r in rtts],
        started_at=started_at,
        completed_at=completed_at,
        note=note,
    )


def _detect_windows_proxy() -> Tuple[bool, Optional[str]]:
    if sys.platform == "win32":
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            )
            try:
                enabled_val, _ = winreg.QueryValueEx(key, "ProxyEnable")
                enabled = bool(enabled_val)
            except OSError:
                enabled = False
            try:
                server_val, _ = winreg.QueryValueEx(key, "ProxyServer")
                server = str(server_val).strip() or None
            except OSError:
                server = None
            try:
                pac_val, _ = winreg.QueryValueEx(key, "AutoConfigURL")
                pac = str(pac_val).strip() or None
            except OSError:
                pac = None
            winreg.CloseKey(key)
            if enabled and server:
                return True, server
            if pac:
                return True, f"PAC: {pac}"
        except OSError:
            pass
    for env_key in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "https_proxy", "http_proxy"):
        val = os.environ.get(env_key, "").strip()
        if val:
            return True, val
    return False, None


def _detect_vpn_interfaces(active_interface: Optional[str]) -> Tuple[bool, List[str]]:
    vpn_keywords = (
        "tap",
        "tun",
        "wireguard",
        "wg",
        "openvpn",
        "anyconnect",
        "cisco",
        "nord",
        "proton",
        "expressvpn",
        "mullvad",
        "tailscale",
        "zerotier",
        "warp",
        "cloudflare",
        "globalprotect",
        "fortinet",
        "ppp",
        "vpn",
    )
    found: List[str] = []
    try:
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()
        for name, st in stats.items():
            if not st.isup:
                continue
            low = name.lower()
            if any(k in low for k in vpn_keywords):
                has_ip = any(
                    a.family in (socket.AF_INET, socket.AF_INET6)
                    and not a.address.startswith(("127.", "::1", "fe80:"))
                    for a in addrs.get(name, [])
                )
                if has_ip:
                    found.append(name)
        if active_interface and any(k in active_interface.lower() for k in vpn_keywords):
            if active_interface not in found:
                found.append(active_interface)
    except Exception:
        pass
    return bool(found), found


def _has_usable_ipv6(interface_name: Optional[str]) -> Tuple[bool, str]:
    """Return True only if OS has a non-link-local global IPv6 address and default IPv6 route."""
    global_v6_addrs: List[str] = []
    try:
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        candidates = (
            {interface_name: addrs.get(interface_name, [])}
            if interface_name and interface_name in addrs
            else addrs
        )
        for name, addr_list in candidates.items():
            if name in stats and not stats[name].isup:
                continue
            if "loopback" in name.lower():
                continue
            for a in addr_list:
                if a.family == socket.AF_INET6:
                    raw = a.address.split("%")[0]
                    try:
                        ip_obj = ipaddress.IPv6Address(raw)
                        if ip_obj.is_global and not ip_obj.is_link_local and not ip_obj.is_loopback:
                            global_v6_addrs.append(raw)
                    except ValueError:
                        continue
    except Exception:
        pass

    if not global_v6_addrs:
        return False, "No global IPv6 address assigned to active interface."

    # Verify default IPv6 route via UDP connect test (no packets transmitted for UDP connect)
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        sock.connect(("2606:4700:4700::1111", 53))
        src_ip = sock.getsockname()[0].split("%")[0]
        sock.close()
        if src_ip and not ipaddress.IPv6Address(src_ip).is_loopback:
            return True, f"Global IPv6 configured ({src_ip})."
    except OSError as exc:
        return False, f"Global IPv6 present ({global_v6_addrs[0]}), but no usable default IPv6 route: {exc}."

    return False, "No usable default IPv6 route detected."


def _ping_ipv6_once(target: str, timeout_sec: float = 1.0) -> Tuple[bool, Optional[float]]:
    """Run one ICMPv6 echo probe via system ping utility without breaking IPv4 flow."""
    try:
        if sys.platform == "win32":
            timeout_ms = max(200, int(timeout_sec * 1000))
            cmd = ["ping", "-6", "-n", "1", "-w", str(timeout_ms), target]
        else:
            cmd = ["ping6", "-c", "1", "-W", str(max(1, int(timeout_sec))), target]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec + 1.0,
            **_subprocess_kwargs(),
        )
        if proc.returncode == 0 and proc.stdout:
            m = re.search(r"(?:time|zeit)[=<]\s*(\d+(?:\.\d+)?)\s*ms", proc.stdout, re.IGNORECASE)
            if m:
                return True, float(m.group(1))
            if "<1ms" in proc.stdout.lower() or "<1 ms" in proc.stdout.lower():
                return True, 0.5
            return True, 1.0
    except Exception:
        pass
    return False, None


class NetworkDiagnosticsService:
    """Executes non-concurrent baseline condition checks, ICMP bursts, IPv6 check, and 5-hop trace."""

    def __init__(
        self,
        *,
        platform: Any = None,
        coordinator: Optional[DiagnosticCoordinator] = None,
        wifi_telemetry: Optional[WifiTelemetryService] = None,
        traceroute_engine: Optional[IcmpTracerouteEngine] = None,
        ipv6_probe_fn: Optional[Callable[[str, float], Tuple[bool, Optional[float]]]] = None,
        ipv6_usable_fn: Optional[Callable[[Optional[str]], Tuple[bool, str]]] = None,
    ) -> None:
        self._platform = platform
        self._coordinator = coordinator
        self._wifi_telemetry = wifi_telemetry
        self._traceroute_engine = traceroute_engine or (
            IcmpTracerouteEngine(platform) if platform is not None else None
        )
        self._ipv6_probe_fn = ipv6_probe_fn or _ping_ipv6_once
        self._ipv6_usable_fn = ipv6_usable_fn or _has_usable_ipv6
        self._last_gateway: Optional[str] = None

    async def collect_conditions(
        self,
        *,
        sample_traffic_sec: float = 0.6,
    ) -> NetworkConditionReport:
        """Observe active interface, gateway changes, VPN, proxy, errors, and live competing traffic."""
        active_iface: Optional[str] = None
        iface_type: Optional[str] = None
        gateway: Optional[str] = None

        if self._platform is not None:
            try:
                if hasattr(self._platform, "get_primary_interface"):
                    p_if = await self._maybe_await(self._platform.get_primary_interface())
                    active_iface = getattr(p_if, "name", None) or (p_if if isinstance(p_if, str) else None)
                    iface_type = getattr(p_if, "interface_type", None)
                if hasattr(self._platform, "get_default_gateway"):
                    gw_res = await self._maybe_await(self._platform.get_default_gateway())
                    gateway = str(gw_res) if gw_res else None
            except Exception:
                pass

        gw_changed = False
        prev_gw = self._last_gateway
        if gateway and self._last_gateway and gateway != self._last_gateway:
            gw_changed = True
        if gateway:
            self._last_gateway = gateway

        vpn_active, vpn_ifaces = _detect_vpn_interfaces(active_iface)
        proxy_enabled, proxy_server = _detect_windows_proxy()

        disconnects = 0
        roams = 0
        rx_err = tx_err = rx_disc = 0
        if self._wifi_telemetry is not None:
            try:
                tel = await self._wifi_telemetry.collect_telemetry(
                    include_events=True, include_ps_driver_stats=True
                )
                if not active_iface and tel.interface_name:
                    active_iface = tel.interface_name
                    iface_type = "wifi"
                disconnects = sum(
                    1 for e in tel.recent_wlan_events if e.event_type == "disconnected"
                )
                roams = len(tel.roaming_events) + sum(
                    1 for e in tel.recent_wlan_events if e.event_type == "roam"
                )
                if tel.interface_stats:
                    rx_err = tel.interface_stats.rx_errors or 0
                    tx_err = tel.interface_stats.tx_errors or 0
                    rx_disc = tel.interface_stats.rx_discards or 0
            except Exception:
                pass

        # Sample competing background interface rate over short window without blocking loop
        rx_mbps: Optional[float] = None
        tx_mbps: Optional[float] = None
        competing_mbps: Optional[float] = None
        large_transfer = False
        if sample_traffic_sec > 0:
            try:
                c1 = psutil.net_io_counters(pernic=True)
                await asyncio.sleep(sample_traffic_sec)
                c2 = psutil.net_io_counters(pernic=True)
                target_nic = active_iface if (active_iface and active_iface in c1 and active_iface in c2) else None
                if target_nic is None and c1:
                    # fallback to busiest NIC
                    target_nic = max(c2.keys(), key=lambda k: c2[k].bytes_recv + c2[k].bytes_sent)
                if target_nic and target_nic in c1 and target_nic in c2:
                    d_rx = max(0, c2[target_nic].bytes_recv - c1[target_nic].bytes_recv)
                    d_tx = max(0, c2[target_nic].bytes_sent - c1[target_nic].bytes_sent)
                    rx_mbps = round((d_rx * 8.0) / (sample_traffic_sec * 1_000_000.0), 2)
                    tx_mbps = round((d_tx * 8.0) / (sample_traffic_sec * 1_000_000.0), 2)
                    competing_mbps = round(rx_mbps + tx_mbps, 2)
                    large_transfer = rx_mbps >= 4.0 or tx_mbps >= 1.5
            except Exception:
                pass

        meeting_active = False
        if self._coordinator is not None:
            meeting_active, _ = self._coordinator.is_meeting_active()

        warnings: List[str] = []
        if vpn_active:
            warnings.append(f"VPN interface active ({', '.join(vpn_ifaces)}): internet latency/routing may traverse VPN tunnel.")
        if proxy_enabled:
            warnings.append(f"System proxy enabled ({proxy_server}): HTTP/HTTPS throughput may reflect proxy path.")
        if gw_changed:
            warnings.append(f"Default gateway changed from {prev_gw} to {gateway}.")
        if large_transfer:
            warnings.append(
                f"Background traffic detected on {active_iface or 'interface'} "
                f"(DL {rx_mbps} Mbps, UL {tx_mbps} Mbps) which may elevate baseline latency."
            )
        if rx_err > 0 or tx_err > 0:
            warnings.append(f"Interface packet errors observed (RX={rx_err}, TX={tx_err}).")
        if disconnects > 0:
            warnings.append(f"{disconnects} recent WLAN disconnect event(s) in Windows log.")

        return NetworkConditionReport(
            captured_at=utc_now(),
            active_interface=active_iface,
            interface_type=iface_type,
            default_gateway=gateway,
            gateway_changed=gw_changed,
            previous_gateway=prev_gw,
            vpn_active=vpn_active,
            vpn_interfaces=vpn_ifaces,
            proxy_enabled=proxy_enabled,
            proxy_server=proxy_server,
            recent_disconnect_count=disconnects,
            recent_roam_count=roams,
            interface_rx_errors=rx_err,
            interface_tx_errors=tx_err,
            interface_rx_discards=rx_disc,
            competing_throughput_mbps=competing_mbps,
            large_transfer_suspected=large_transfer,
            active_interface_rx_mbps=rx_mbps,
            active_interface_tx_mbps=tx_mbps,
            meeting_active=meeting_active,
            warnings=warnings,
        )

    async def _run_icmp_v4_burst(
        self,
        target: str,
        *,
        count: int = 30,
        interval_sec: float = 0.08,
        timeout_sec: float = 1.0,
        token: Optional[CancellationToken] = None,
    ) -> PingBurstStats:
        started = utc_now()
        if not target:
            return PingBurstStats(
                target="",
                address_family="ipv4",
                status="unreachable",
                started_at=started,
                completed_at=utc_now(),
                note="No target IP available.",
            )

        rtts: List[float] = []
        sent = 0
        for i in range(count):
            if token and token.is_cancelled:
                return PingBurstStats(
                    target=target,
                    address_family="ipv4",
                    status="cancelled",
                    packets_sent=sent,
                    packets_received=len(rtts),
                    packet_loss_pct=round(((sent - len(rtts)) / max(1, sent)) * 100.0, 2),
                    rtts_ms=rtts,
                    started_at=started,
                    completed_at=utc_now(),
                    note="Cancelled before completion.",
                )
            sent += 1
            if self._platform is not None and hasattr(self._platform, "ping"):
                res = await self._maybe_await(
                    self._platform.ping(target, timeout_sec=timeout_sec)
                )
                ok = bool(getattr(res, "success", False))
                rtt = getattr(res, "latency_ms", None)
                if ok and rtt is not None:
                    rtts.append(float(rtt))
            if i < count - 1 and interval_sec > 0:
                await asyncio.sleep(interval_sec)

        return _summarize_burst(target, "ipv4", sent, rtts, started, utc_now())

    async def _run_icmp_v6_burst(
        self,
        target: str,
        *,
        interface_name: Optional[str],
        count: int = 30,
        interval_sec: float = 0.08,
        timeout_sec: float = 1.0,
        token: Optional[CancellationToken] = None,
    ) -> PingBurstStats:
        started = utc_now()
        usable, reason = await asyncio.to_thread(self._ipv6_usable_fn, interface_name)
        if not usable:
            return PingBurstStats(
                target=target,
                address_family="ipv6",
                status="not_configured",
                packets_sent=0,
                packets_received=0,
                packet_loss_pct=0.0,
                started_at=started,
                completed_at=utc_now(),
                note=f"IPv6 not tested as failure: {reason}",
            )

        rtts: List[float] = []
        sent = 0
        for i in range(count):
            if token and token.is_cancelled:
                return PingBurstStats(
                    target=target,
                    address_family="ipv6",
                    status="cancelled",
                    packets_sent=sent,
                    packets_received=len(rtts),
                    packet_loss_pct=round(((sent - len(rtts)) / max(1, sent)) * 100.0, 2),
                    rtts_ms=rtts,
                    started_at=started,
                    completed_at=utc_now(),
                    note="Cancelled before completion.",
                )
            sent += 1
            ok, rtt = await asyncio.to_thread(self._ipv6_probe_fn, target, timeout_sec)
            if ok and rtt is not None:
                rtts.append(float(rtt))
            if i < count - 1 and interval_sec > 0:
                await asyncio.sleep(interval_sec)

        return _summarize_burst(
            target, "ipv6", sent, rtts, started, utc_now(), note=reason
        )

    async def _run_traceroute(
        self,
        target: str = "1.1.1.1",
        max_hops: int = 5,
    ) -> TracerouteDiagnosticResult:
        started = utc_now()
        if self._traceroute_engine is None:
            return TracerouteDiagnosticResult(
                target=target,
                max_hops=max_hops,
                status="skipped",
                started_at=started,
                completed_at=utc_now(),
                interpretation_note="Traceroute engine unavailable without platform adapter.",
            )

        try:
            import inspect

            fn = self._traceroute_engine.run_trace
            if inspect.iscoroutinefunction(fn):
                report = await fn(
                    target_ip=target, max_hops=max_hops, probes_per_hop=2, timeout_ms=900
                )
            else:
                res = await asyncio.to_thread(
                    fn, target_ip=target, max_hops=max_hops, probes_per_hop=2, timeout_ms=900
                )
                report = await self._maybe_await(res)
            hops_out: List[TracerouteHopSummary] = []
            for h in getattr(report, "hops", []):
                rtts = list(getattr(h, "rtts_ms", []) or [])
                ip_addr = getattr(h, "ip_address", None) or getattr(h, "ip", None)
                responded = bool(rtts) or bool(ip_addr and ip_addr != "*")
                avg_ms = getattr(h, "avg_rtt_ms", None)
                if avg_ms is None:
                    avg_ms = getattr(h, "avg_ms", None)
                if avg_ms is None and rtts:
                    avg_ms = statistics.fmean(rtts)
                loss_pct = getattr(h, "loss_pct", None)
                if loss_pct is None:
                    loss_pct = 0.0 if responded else 100.0
                if responded:
                    interp = f"Responded ({float(avg_ms):.1f} ms avg)" if avg_ms is not None else "Responded"
                else:
                    interp = "No ICMP Time Exceeded reply (often router ICMP rate-limit or firewall; not standalone proof of loss)."
                hops_out.append(
                    TracerouteHopSummary(
                        hop_number=int(getattr(h, "hop_number", getattr(h, "ttl", len(hops_out) + 1))),
                        ip_address=ip_addr if ip_addr != "*" else None,
                        hostname=getattr(h, "hostname", None),
                        rtts_ms=[round(float(x), 2) for x in rtts],
                        avg_ms=round(float(avg_ms), 2) if avg_ms is not None else None,
                        loss_pct=float(loss_pct),
                        responded=responded,
                        interpretation=interp,
                    )
                )
            return TracerouteDiagnosticResult(
                target=target,
                max_hops=max_hops,
                status="ok",
                started_at=started,
                completed_at=utc_now(),
                hops=hops_out,
            )
        except Exception as exc:
            return TracerouteDiagnosticResult(
                target=target,
                max_hops=max_hops,
                status="failed",
                started_at=started,
                completed_at=utc_now(),
                interpretation_note=f"Traceroute failed: {exc}",
            )

    async def run_sequence(
        self,
        *,
        packet_count: int = 30,
        interval_sec: float = 0.05,
        public_target: str = "1.1.1.1",
        ipv6_target: str = "2606:4700:4700::1111",
        traceroute_hops: int = 5,
        sample_traffic_sec: float = 0.5,
    ) -> NetworkDiagnosticsReport:
        """Run baseline conditions -> Gateway 30 ICMP -> Internet 30 ICMP -> IPv6 -> 5-hop trace strictly sequentially."""
        started = utc_now()
        run_id = uuid.uuid4().hex[:10]
        seq_log: List[str] = []

        async def _execute(token: Optional[CancellationToken]) -> NetworkDiagnosticsReport:
            if self._coordinator:
                self._coordinator.update_progress(10.0, "conditions")
            cond = await self.collect_conditions(sample_traffic_sec=sample_traffic_sec)
            seq_log.append("E_conditions_baseline")

            if self._coordinator:
                self._coordinator.update_progress(30.0, "gateway_icmp")
            gw_ping = await self._run_icmp_v4_burst(
                cond.default_gateway or "",
                count=packet_count,
                interval_sec=interval_sec,
                token=token,
            )
            seq_log.append("A_gateway_icmp_30")

            if self._coordinator:
                self._coordinator.update_progress(55.0, "internet_icmp")
            inet_ping = await self._run_icmp_v4_burst(
                public_target,
                count=packet_count,
                interval_sec=interval_sec,
                token=token,
            )
            seq_log.append("B_internet_icmp_30")

            if self._coordinator:
                self._coordinator.update_progress(75.0, "ipv6_icmp")
            v6_ping = await self._run_icmp_v6_burst(
                ipv6_target,
                interface_name=cond.active_interface,
                count=packet_count,
                interval_sec=interval_sec,
                token=token,
            )
            seq_log.append("C_ipv6_check")

            if self._coordinator:
                self._coordinator.update_progress(90.0, "traceroute")
            trace_res = await self._run_traceroute(
                target=public_target, max_hops=traceroute_hops
            )
            seq_log.append("D_traceroute_5_hop")

            notes: List[str] = [
                "All probes executed sequentially without concurrent speed/throughput load."
            ]
            if gw_ping.status == "ok" and inet_ping.status == "ok":
                if gw_ping.packet_loss_pct >= 2.0 or (gw_ping.avg_ms and gw_ping.avg_ms > 20.0):
                    summary = (
                        f"Local LAN/Wi-Fi hop degraded (Gateway avg {gw_ping.avg_ms} ms, loss {gw_ping.packet_loss_pct}%)."
                    )
                elif inet_ping.packet_loss_pct >= 2.0 or (
                    inet_ping.avg_ms and gw_ping.avg_ms and (inet_ping.avg_ms - gw_ping.avg_ms) > 85.0
                ):
                    summary = (
                        f"Gateway clean ({gw_ping.avg_ms} ms) while upstream public path elevated "
                        f"({inet_ping.avg_ms} ms, loss {inet_ping.packet_loss_pct}%)."
                    )
                else:
                    summary = (
                        f"Baseline healthy: Gateway {gw_ping.avg_ms} ms ({gw_ping.packet_loss_pct}% loss), "
                        f"Internet {inet_ping.avg_ms} ms ({inet_ping.packet_loss_pct}% loss)."
                    )
            else:
                summary = (
                    f"Partial connectivity: Gateway={gw_ping.status}, Internet={inet_ping.status}."
                )

            return NetworkDiagnosticsReport(
                run_id=run_id,
                started_at=started,
                completed_at=utc_now(),
                sequence_order=seq_log,
                conditions=cond,
                gateway_ping=gw_ping,
                internet_ping=inet_ping,
                ipv6_ping=v6_ping,
                traceroute=trace_res,
                diagnosis_summary=summary,
                notes=notes,
            )

        if self._coordinator is not None:
            async with self._coordinator.async_exclusive(
                "network_sequence", "Sequential baseline & ICMP diagnostics"
            ) as token:
                return await _execute(token)
        return await _execute(None)

    @staticmethod
    async def _maybe_await(val: Any) -> Any:
        if asyncio.iscoroutine(val) or hasattr(val, "__await__"):
            return await val
        return val
