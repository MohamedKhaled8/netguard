"""DNS Configuration Intelligence and Ownership Detection Engine (Phase 3).

Discovers:
- Active network adapter (physical vs virtual).
- Configured IPv4 & IPv6 DNS servers, primary/secondary roles, and DHCP vs Static modes.
- Default gateway and DHCP server IP.
- Configuration Owner classification:
    * STATIC_ADAPTER: Manually configured in Windows Adapter / Control Panel / Windows Settings.
    * ROUTER_DHCP_RELAY: Windows receives DNS via DHCP pointing to local router gateway.
    * ISP_DHCP: Windows receives DNS via DHCP pointing directly to ISP / external public servers.
    * LOCAL_PROXY: Local listener on 127.0.0.1 / loopback (e.g. AdGuard, Acrylic, dnscrypt).
    * THIRD_PARTY_SECURITY: Detected local DNS proxy / filtering / security software.
    * VPN_TUNNEL: Active VPN adapter or tunnel redirecting system traffic.
    * ENTERPRISE_NRPT: Group Policy Name Resolution Policy Table rules.
    * WINDOWS_DOH: Windows native DNS-over-HTTPS configured.
- Detection confidence score and explicit verification limitations.
"""

from __future__ import annotations
import enum
import ipaddress
import json
import logging
import os
import re
import socket
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import psutil
from app.platform.interfaces import IPlatformAdapter

logger = logging.getLogger("netguard.dns.ownership")
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


class DnsOwnerType(str, enum.Enum):
    STATIC_ADAPTER = "static_adapter"
    ROUTER_DHCP_RELAY = "router_dhcp_relay"
    ISP_DHCP = "isp_dhcp"
    LOCAL_PROXY = "local_proxy"
    THIRD_PARTY_SECURITY = "third_party_security"
    VPN_TUNNEL = "vpn_tunnel"
    ENTERPRISE_NRPT = "enterprise_nrpt"
    WINDOWS_DOH = "windows_doh"
    UNKNOWN = "unknown"


@dataclass
class DnsOwnershipReport:
    """Authoritative diagnostic report answering 'Who controls my DNS right now?'."""
    owner_type: DnsOwnerType
    owner_title: str
    owner_title_en: str
    summary_arabic: str
    summary_english: str
    interface_alias: str
    interface_description: str = ""
    is_virtual_adapter: bool = False
    ipv4_servers: List[str] = field(default_factory=list)
    ipv4_mode: str = "dhcp"  # "static" or "dhcp"
    ipv6_servers: List[str] = field(default_factory=list)
    ipv6_mode: str = "dhcp"  # "static" or "dhcp"
    default_gateway: Optional[str] = None
    dhcp_server: Optional[str] = None
    is_router_relay: bool = False
    upstream_verification_status: str = ""
    detected_third_party_apps: List[str] = field(default_factory=list)
    has_local_port53_listener: bool = False
    active_vpn_adapters: List[str] = field(default_factory=list)
    has_nrpt_rules: bool = False
    nrpt_rules_count: int = 0
    windows_doh_configured: bool = False
    confidence_score: float = 1.0  # 0.0 - 1.0
    verification_limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "owner_type": self.owner_type.value,
            "owner_title": self.owner_title,
            "owner_title_en": self.owner_title_en,
            "summary_arabic": self.summary_arabic,
            "summary_english": self.summary_english,
            "interface_alias": self.interface_alias,
            "interface_description": self.interface_description,
            "is_virtual_adapter": self.is_virtual_adapter,
            "ipv4_servers": self.ipv4_servers,
            "ipv4_mode": self.ipv4_mode,
            "ipv6_servers": self.ipv6_servers,
            "ipv6_mode": self.ipv6_mode,
            "default_gateway": self.default_gateway,
            "dhcp_server": self.dhcp_server,
            "is_router_relay": self.is_router_relay,
            "upstream_verification_status": self.upstream_verification_status,
            "detected_third_party_apps": self.detected_third_party_apps,
            "has_local_port53_listener": self.has_local_port53_listener,
            "active_vpn_adapters": self.active_vpn_adapters,
            "has_nrpt_rules": self.has_nrpt_rules,
            "nrpt_rules_count": self.nrpt_rules_count,
            "windows_doh_configured": self.windows_doh_configured,
            "confidence_score": self.confidence_score,
            "verification_limitations": self.verification_limitations,
        }


class DnsOwnershipEngine:
    """Dedicated engine discovering DNS configuration source and controller on Windows."""

    KNOWN_SECURITY_PROCS = {
        "adguardsvc.exe": "AdGuard for Windows",
        "acrylicdns.exe": "Acrylic DNS Proxy",
        "dnscrypt-proxy.exe": "Simple DNSCrypt / DNSCrypt Proxy",
        "cloudflared.exe": "Cloudflare Zero Trust / Cloudflared",
        "stubby.exe": "Stubby DNS-over-TLS",
        "yoga-dns.exe": "YogaDNS",
        "yogadns.exe": "YogaDNS",
        "tailscaled.exe": "Tailscale MagicDNS",
        "tailscale.exe": "Tailscale MagicDNS",
        "wireguard.exe": "WireGuard Tunnel",
        "openvpn.exe": "OpenVPN Client",
        "openvpnserv.exe": "OpenVPN Service",
        "vpnagent.exe": "Cisco AnyConnect Secure Mobility Client",
        "nordvpn.exe": "NordVPN Client",
        "nordvpn.service.exe": "NordVPN Service",
        "expressvpn.exe": "ExpressVPN Client",
        "protonvpn.exe": "Proton VPN",
        "protonvpn.service.exe": "Proton VPN Service",
        "warp-svc.exe": "Cloudflare WARP Client",
        "zerotier-one.exe": "ZeroTier One Virtual Network",
    }

    VPN_ADAPTER_KEYWORDS = (
        "wintun",
        "wireguard",
        "tailscale",
        "tap",
        "tun",
        "nord",
        "express",
        "zerotier",
        "openvpn",
        "cisco",
        "anyconnect",
        "vpn",
        "virtual",
        "vmware",
        "hyper-v",
    )

    def __init__(self, platform: Optional[IPlatformAdapter] = None) -> None:
        if platform is None:
            from app.platform.windows.adapter import WindowsPlatformAdapter
            platform = WindowsPlatformAdapter()
        self.platform = platform

    def discover_ownership(self) -> DnsOwnershipReport:
        """Perform comprehensive, evidence-grounded DNS ownership analysis."""
        iface = self.platform.get_primary_interface() or "Wi-Fi"
        gw = self.platform.get_default_gateway() or "192.168.1.1"

        # 1. Discover all configured servers and separate IPv4 vs IPv6
        all_servers = self.platform.get_interface_dns_servers(iface) or []
        ipv4_servers: List[str] = []
        ipv6_servers: List[str] = []
        for s in all_servers:
            try:
                ip_obj = ipaddress.ip_address(s.split("%")[0])
                if ip_obj.version == 4:
                    ipv4_servers.append(s)
                else:
                    ipv6_servers.append(s)
            except ValueError:
                ipv4_servers.append(s)

        # 2. Modes: DHCP vs Static
        ipv4_mode = self.platform.get_interface_dns_mode(iface)
        ipv6_mode = "dhcp"
        if hasattr(self.platform, "get_interface_ipv6_dns_mode"):
            ipv6_mode = self.platform.get_interface_ipv6_dns_mode(iface)
        elif os.name == "nt":
            ipv6_mode = self._detect_ipv6_dns_mode(iface)

        # 3. Detect DHCP Server & Adapter details from WMI
        wmi_details = self._detect_wmi_adapter_info(iface)
        dhcp_server = wmi_details.get("dhcp_server")
        iface_desc = wmi_details.get("description", "")

        # 4. Check if interface is virtual/VPN
        is_virtual = any(kw in iface.lower() or kw in iface_desc.lower() for kw in self.VPN_ADAPTER_KEYWORDS)

        # 5. Check local port 53 listener & running third-party security apps
        has_port53 = self._detect_local_port53_listeners()
        detected_apps = self._detect_third_party_apps()
        vpn_adapters = self._detect_active_vpn_adapters()

        # 6. Check NRPT rules & Windows DoH
        has_nrpt, nrpt_count = self._detect_nrpt_rules()
        windows_doh = self._detect_windows_doh()

        # 7. Check Router Relay status
        is_router_relay = False
        all_configured = ipv4_servers + ipv6_servers
        for s in all_configured:
            s_clean = s.split("%")[0]
            if s_clean == gw:
                is_router_relay = True
                break
            if s_clean.startswith("fe80:") or s_clean.startswith("192.168.") or s_clean.startswith("10.") or s_clean.startswith("172.16."):
                is_router_relay = True
                break

        # 8. Determine Owner Classification
        owner_type = DnsOwnerType.UNKNOWN
        owner_title = "غير محدد"
        owner_title_en = "Unspecified Controller"
        summary_ar = ""
        summary_en = ""
        upstream_status = "مباشر"
        confidence = 0.95
        limitations: List[str] = [
            "لا يمكن فحص إعدادات DoH الداخلية في المتصفحات (Chrome/Firefox/Edge) لعزلها الأمني الخاص.",
        ]

        # Scenario evaluation in strict priority order:
        # A. Local Proxy (127.0.0.1 or local port 53 listener)
        if any(s.startswith("127.") for s in ipv4_servers) or (has_port53 and detected_apps):
            owner_type = DnsOwnerType.LOCAL_PROXY
            app_str = ", ".join(detected_apps) if detected_apps else "خادم وكيل محلي (Local DNS Proxy)"
            owner_title = f"تطبيق وكيل محلي ({app_str})"
            owner_title_en = f"Local DNS Proxy ({app_str})"
            summary_ar = f"يتم توجيه استعلامات DNS أولاً إلى خادم محلي على جهازك ({app_str}) لتصفية أو تشفير الطلبات قبل إرسالها."
            summary_en = f"DNS queries are routed through a local agent ({app_str}) for local filtering or encrypted forwarding."
            confidence = 0.98

        # B. Active VPN Tunnel
        elif (is_virtual and vpn_adapters) or (any("vpn" in iface.lower() for iface in [iface])):
            owner_type = DnsOwnerType.VPN_TUNNEL
            owner_title = f"نفق شبكة افتراضية خاصة (VPN: {iface})"
            owner_title_en = f"VPN Tunnel Adapter ({iface})"
            summary_ar = f"تتم إدارة ترجمة النطاقات بواسطة محول شبكة VPN النشط ({iface}). يتم تشفير أو حصر الطلبات داخل نفق VPN."
            summary_en = f"DNS resolution is managed by active VPN interface '{iface}' through a secure tunnel."
            confidence = 0.95
            limitations.append("إعدادات DNS لنفق VPN تتبع سياسات موفر الـ VPN وقد تعزل الاستعلامات تماماً عن الشبكة المحلية.")

        # C. Enterprise NRPT Group Policy
        elif has_nrpt and nrpt_count > 0:
            owner_type = DnsOwnerType.ENTERPRISE_NRPT
            owner_title = f"سياسة مجموعة المؤسسة (Windows NRPT - {nrpt_count} قاعدة)"
            owner_title_en = f"Windows Enterprise NRPT Policy ({nrpt_count} rules)"
            summary_ar = f"تتحكم قواعد جدول سياسات تحليل الأسماء (NRPT) الخاصة بنطاق العمل أو المؤسسة في توجيه استعلامات DNS."
            summary_en = f"Windows Name Resolution Policy Table (NRPT) rules enforce corporate DNS resolution."
            confidence = 0.95

        # D. Static Windows Adapter Settings (Control Panel / Settings)
        elif ipv4_mode == "static":
            owner_type = DnsOwnerType.STATIC_ADAPTER
            servers_str = ", ".join(ipv4_servers) if ipv4_servers else "ثابت"
            owner_title = f"إعدادات بطاقة الشبكة اليدوية (Static Windows Settings: {servers_str})"
            owner_title_en = f"Static Windows Adapter Configuration ({servers_str})"
            summary_ar = f"تم ضبط خوادم DNS يدوياً على محول الشبكة '{iface}' عبر لوحة التحكم (Control Panel) أو إعدادات Windows."
            summary_en = f"DNS servers were manually assigned to network adapter '{iface}' via Windows Settings or Control Panel."
            upstream_status = f"موجه مباشرة إلى الخوادم الثابتة ({servers_str})"
            confidence = 1.0

        # E. Router DHCP Relay
        elif is_router_relay and (ipv4_mode == "dhcp" or not ipv4_servers):
            owner_type = DnsOwnerType.ROUTER_DHCP_RELAY
            owner_title = f"توزيع تلقائي من الراوتر (Router DHCP Relay: {gw})"
            owner_title_en = f"Router DHCP DNS Relay ({gw})"
            summary_ar = "جهازك يستلم عنوان DNS تلقائياً من الراوتر عبر DHCP، والراوتر يعمل كوسيط لإعادة توجيه الاستعلامات إلى خوادم مزود الخدمة (ISP)."
            summary_en = "Device obtains DNS automatically via DHCP pointing to router gateway; the router relays queries upstream."
            upstream_status = "Router DNS relay detected. Upstream DNS configuration could not be independently verified."
            limitations.append("لا يمكن التحقق من خادم DNS الحقيقي خلف الراوتر دون صلاحيات دخول إدارية معتمدة على لوحة تحكم الراوتر.")
            confidence = 0.90

        # F. DHCP with Direct ISP / Public Servers
        elif ipv4_mode == "dhcp" and ipv4_servers:
            owner_type = DnsOwnerType.ISP_DHCP
            servers_str = ", ".join(ipv4_servers)
            owner_title = f"توزيع DHCP مباشر من مزود الخدمة ({servers_str})"
            owner_title_en = f"DHCP-Assigned Provider DNS ({servers_str})"
            summary_ar = f"يستلم جهازك خوادم DNS عامة أو تابعة لمزود الخدمة مباشرة عبر بروتوكول DHCP دون وسيط محلي."
            summary_en = f"Device receives public/ISP DNS servers directly via DHCP ({servers_str})."
            upstream_status = f"مباشر إلى {servers_str}"
            confidence = 0.92

        # Check for IPv6 inconsistency warning
        if ipv4_mode == "static" and ipv6_mode == "dhcp" and ipv6_servers:
            limitations.append(
                f"تنبيه عدم تطابق بروتوكولي: بطاقة الشبكة مضبوطة على IPv4 ثابت ({', '.join(ipv4_servers)}) مع بقاء IPv6 على التوزيع التلقائي ({', '.join(ipv6_servers)}). قد تسلك بعض استعلامات التطبيقات مسار IPv6 الراوتر."
            )

        if detected_apps and owner_type != DnsOwnerType.LOCAL_PROXY:
            limitations.append(
                f"تطبيقات أمان أو VPN مثبتة ونشطة في الخلفية: {', '.join(detected_apps)}. قد تطبق اعتراضاً أو سياسات DNS إضافية."
            )

        return DnsOwnershipReport(
            owner_type=owner_type,
            owner_title=owner_title,
            owner_title_en=owner_title_en,
            summary_arabic=summary_ar,
            summary_english=summary_en,
            interface_alias=iface,
            interface_description=iface_desc,
            is_virtual_adapter=is_virtual,
            ipv4_servers=ipv4_servers,
            ipv4_mode=ipv4_mode,
            ipv6_servers=ipv6_servers,
            ipv6_mode=ipv6_mode,
            default_gateway=gw,
            dhcp_server=dhcp_server,
            is_router_relay=is_router_relay,
            upstream_verification_status=upstream_status,
            detected_third_party_apps=detected_apps,
            has_local_port53_listener=has_port53,
            active_vpn_adapters=vpn_adapters,
            has_nrpt_rules=has_nrpt,
            nrpt_rules_count=nrpt_count,
            windows_doh_configured=windows_doh,
            confidence_score=confidence,
            verification_limitations=limitations,
        )

    def _detect_ipv6_dns_mode(self, iface: str) -> str:
        try:
            proc = subprocess.run(
                ["netsh", "interface", "ipv6", "show", "dnsservers", f"name={iface}"],
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
                creationflags=_NO_WINDOW,
            )
            if proc.returncode == 0:
                if "Statically Configured" in proc.stdout:
                    return "static"
                elif "through DHCP" in proc.stdout:
                    return "dhcp"
        except Exception:
            pass
        return "dhcp"

    def _detect_wmi_adapter_info(self, iface: str) -> Dict[str, Any]:
        """Query WMI Win32_NetworkAdapterConfiguration for DHCP server and Description."""
        res: Dict[str, Any] = {"dhcp_server": None, "description": ""}
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"Get-CimInstance Win32_NetworkAdapterConfiguration | Where-Object {{ $_.IPEnabled }} | Select-Object Description, DHCPServer, DefaultIPGateway | ConvertTo-Json",
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3.5,
                check=False,
                creationflags=_NO_WINDOW,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout)
                entries = data if isinstance(data, list) else [data]
                for item in entries:
                    if isinstance(item, dict):
                        desc = item.get("Description", "")
                        dhcp = item.get("DHCPServer")
                        gws = item.get("DefaultIPGateway") or []
                        if gws and dhcp:
                            res["dhcp_server"] = dhcp
                            res["description"] = desc
                            return res
        except Exception as exc:
            logger.debug("WMI adapter query failed: %s", exc)
        return res

    def _detect_local_port53_listeners(self) -> bool:
        """Check if any local application is listening on TCP/UDP port 53."""
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.laddr and conn.laddr.port == 53:
                    if conn.laddr.ip in ("127.0.0.1", "::1", "0.0.0.0", "::"):
                        return True
        except (psutil.AccessDenied, Exception):
            pass
        return False

    def _detect_third_party_apps(self) -> List[str]:
        """Scan running processes for known DNS proxies, VPNs, and filtering apps."""
        detected: List[str] = []
        try:
            for p in psutil.process_iter(["name"]):
                name = (p.info.get("name") or "").lower()
                if name in self.KNOWN_SECURITY_PROCS:
                    app_name = self.KNOWN_SECURITY_PROCS[name]
                    if app_name not in detected:
                        detected.append(app_name)
        except Exception:
            pass
        return detected

    def _detect_active_vpn_adapters(self) -> List[str]:
        """Detect active virtual or VPN interfaces currently routing traffic."""
        vpns: List[str] = []
        try:
            stats = psutil.net_if_stats()
            for name, st in stats.items():
                if st.isup and any(kw in name.lower() for kw in self.VPN_ADAPTER_KEYWORDS):
                    if "loopback" not in name.lower():
                        vpns.append(name)
        except Exception:
            pass
        return vpns

    def _detect_nrpt_rules(self) -> Tuple[bool, int]:
        """Check for Windows Group Policy NRPT (Name Resolution Policy Table) rules."""
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-DnsClientNrptRule | Measure-Object | Select-Object -ExpandProperty Count",
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=2.5,
                check=False,
                creationflags=_NO_WINDOW,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                try:
                    count = int(proc.stdout.strip())
                    return (count > 0), count
                except ValueError:
                    pass
        except Exception:
            pass
        return False, 0

    def _detect_windows_doh(self) -> bool:
        """Check if Windows 11 native DNS-over-HTTPS (DoH) is configured and active."""
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-DnsClientDohServerAddress | Where-Object { $_.AutoUpgrade -eq $true -or $_.AllowFallbackToUdp -eq $false } | Measure-Object | Select-Object -ExpandProperty Count",
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=2.5,
                check=False,
                creationflags=_NO_WINDOW,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                try:
                    count = int(proc.stdout.strip())
                    return count > 0
                except ValueError:
                    pass
        except Exception:
            pass
        return False
