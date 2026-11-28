"""Universal router fingerprinting, ISP-vs-vendor separation, and interface capability discovery.

Implements Section 1 requirements across heterogeneous routers and ISP-branded devices:
- Distinguishes ISP branding (WE / TE Data, Orange, Vodafone, Etisalat, etc.) from the
  actual underlying hardware manufacturer (Huawei, ZTE, TP-Link, Tenda, D-Link, Nokia,
  Sercomm, Sagemcom, FiberHome, Netgear, ASUS, MikroTik, OpenWrt).
- Prioritizes authenticated/unauthenticated HTTP headers, HTML, JS tokens, UPnP/TR-064
  device descriptions, SNMP sysDescr/sysObjectID (only when enabled), and TR-069/USP
  port availability over raw MAC OUI fallbacks.
- Never bypasses authentication, exploits vulnerabilities, or brute-forces credentials.
"""

from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
import ssl
import struct
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.wifi.models import RouterCapabilities, RouterDiscoveryResult


# Expanded OUI prefixes used strictly as low-priority fallback when HTTP/UPnP/SNMP give no clue.
# Note: Some OUIs are shared across ODMs or rebranded ISP batches; HTTP/DOM signatures always override OUI.
EXTENDED_ROUTER_OUIS: Dict[str, str] = {
    # Huawei
    "F8:95:22": "Huawei",
    "E4:C3:2A": "Huawei",
    "CC:96:A0": "Huawei",
    "00:E0:FC": "Huawei",
    "28:6E:D4": "Huawei",
    "48:46:FB": "Huawei",
    "54:A5:1B": "Huawei",
    "70:72:3C": "Huawei",
    "88:53:D4": "Huawei",
    "AC:E2:15": "Huawei",
    "D4:6A:A8": "Huawei",
    "EC:23:3D": "Huawei",
    # ZTE
    "F4:28:53": "ZTE",
    "4C:16:FC": "ZTE",
    "C8:64:C7": "ZTE",
    "34:4B:50": "ZTE",
    "78:96:82": "ZTE",
    "84:74:2A": "ZTE",
    "9C:D2:4B": "ZTE",
    "D0:15:4A": "ZTE",
    # TP-Link
    "B0:95:75": "TP-Link",
    "50:C7:BF": "TP-Link",
    "C0:25:E9": "TP-Link",
    "98:DA:C4": "TP-Link",
    "EC:08:6B": "TP-Link",
    "14:CC:20": "TP-Link",
    "F4:F2:6D": "TP-Link",
    "AC:84:C6": "TP-Link",
    # Tenda
    "C8:3A:35": "Tenda",
    "CC:2D:21": "Tenda",
    "D8:32:14": "Tenda",
    "50:0F:F5": "Tenda",
    # D-Link
    "00:1B:11": "D-Link",
    "1C:7E:E5": "D-Link",
    "28:10:7B": "D-Link",
    "C8:BE:19": "D-Link",
    "F0:7D:68": "D-Link",
    # Nokia / Alcatel-Lucent
    "00:19:99": "Nokia",
    "00:25:68": "Nokia",
    "A4:2B:8C": "Nokia",
    "70:62:B8": "Nokia",
    # Sercomm
    "00:0E:8F": "Sercomm",
    "68:14:01": "Sercomm",
    "90:1A:CA": "Sercomm",
    "E8:6D:52": "Sercomm",
    # Sagemcom
    "00:19:70": "Sagemcom",
    "34:8A:AE": "Sagemcom",
    "7C:B7:33": "Sagemcom",
    "E4:5D:51": "Sagemcom",
    # FiberHome
    "00:0A:C2": "FiberHome",
    "38:97:D6": "FiberHome",
    "78:98:E8": "FiberHome",
    "C4:A8:1D": "FiberHome",
    # Netgear
    "00:1E:2A": "Netgear",
    "20:4E:7F": "Netgear",
    "A0:40:A0": "Netgear",
    "C0:3F:0E": "Netgear",
    # ASUS
    "04:92:26": "ASUS",
    "1C:87:2C": "ASUS",
    "38:D5:47": "ASUS",
    "70:8B:CD": "ASUS",
    "AC:9E:17": "ASUS",
    # MikroTik
    "00:0C:42": "MikroTik",
    "4C:5E:0C": "MikroTik",
    "6C:3B:6B": "MikroTik",
    "B8:69:F4": "MikroTik",
    "D4:CA:6D": "MikroTik",
    "DC:2C:6E": "MikroTik",
}


ISP_BRAND_MARKERS: List[Tuple[str, Tuple[str, ...]]] = [
    ("WE (TE Data)", ("dtedata", "isdtedata", "we.eg", "telecomegypt", "te-data", "te data", "we router", "we home", "wefax", "hg630 v2 home gateway", "dn8245v")),
    ("Orange", ("orange", "livebox", "funbox", "orange.eg", "orange home")),
    ("Vodafone", ("vodafone", "vodafonestation", "easybox", "gigabox")),
    ("Etisalat", ("etisalat", "eand", "e&")),
    ("STC", ("stc.com.sa", "stc fiber", "stc home")),
    ("Ooredoo", ("ooredoo",)),
]


@dataclass(frozen=True)
class VendorSignatureRule:
    adapter_id: str
    vendor_name: str
    strong_markers: Tuple[str, ...]
    weak_markers: Tuple[str, ...] = ()
    model_patterns: Tuple[str, ...] = ()
    default_protocols: Tuple[str, ...] = ()


# Strong markers match vendor-specific JS variables, API paths, CGI scripts, or unambiguous product families.
# Order only resolves ties when two vendors share identical confidence.
VENDOR_RULES: Tuple[VendorSignatureRule, ...] = (
    VendorSignatureRule(
        adapter_id="huawei",
        vendor_name="Huawei",
        strong_markers=(
            "/resource/common/safelogin.js",
            "/asp/getrandcount.asp",
            "x_hw_token",
            "sestokinfo",
            "dn8245",
            "hg8245",
            "hg8145",
            "eg8145",
            "hg630",
            "hg631",
            "hg658",
            "hg531",
            "hg532",
            "ws5200",
            "ax3",
            "b310",
            "b311",
            "b535",
            "echolife",
            "hilink",
        ),
        weak_markers=("huawei", "cfgmode"),
        model_patterns=(
            r"var\s+ProductName\s*=\s*['\"]([^'\"]+)['\"]",
            r"<ProductName>([^<]+)</ProductName>",
            r"\b((?:DN|HG|EG|WS|B)\d{3,4}[A-Za-z0-9\-\\x]*)\b",
        ),
        default_protocols=("http_web_asp", "hilink_xml", "web_dom"),
    ),
    VendorSignatureRule(
        adapter_id="zte",
        vendor_name="ZTE",
        strong_markers=(
            "frm_logintoken",
            "getpage.gch",
            "common_page/",
            "zxhn",
            "_sessionid",
            "loginchecktoken",
            "zxcpe",
        ),
        weak_markers=("zte", "zte corporation"),
        model_patterns=(
            r"\b(ZXHN\s*[A-Z0-9\-]+)\b",
            r"var\s+productName\s*=\s*['\"]([^'\"]+)['\"]",
        ),
        default_protocols=("http_gch", "web_dom"),
    ),
    VendorSignatureRule(
        adapter_id="tplink",
        vendor_name="TP-Link",
        strong_markers=(
            "stok=",
            "sysauth",
            "tplinklogin",
            "su.min.js",
            "tp-link",
            "tplink",
        ),
        weak_markers=("archer", "deco", "omada", "tl-wr", "vx230", "td-w"),
        model_patterns=(
            r"\b(Archer\s+[A-Z0-9\-]+)\b",
            r"\b(Deco\s+[A-Z0-9\-]+)\b",
            r"\b(VX\d+[A-Za-z0-9\-]*|TD-W\d+[A-Za-z0-9\-]*|TL-[A-Z0-9\-]+)\b",
        ),
        default_protocols=("stok_json", "http_cgi", "web_dom"),
    ),
    VendorSignatureRule(
        adapter_id="asus",
        vendor_name="ASUS",
        strong_markers=("asuswrt", "main_login.asp", "login.cgi?group_id", "rt-ax", "rt-ac", "zenwifi", "tuf-ax"),
        weak_markers=("asus",),
        model_patterns=(
            r"\b(RT-[A-Z0-9\-]+|ZenWiFi\s+[A-Z0-9\-]+|TUF-AX\d+|GT-[A-Z0-9\-]+)\b",
            r"productid\s*[:=]\s*['\"]([^'\"]+)['\"]",
        ),
        default_protocols=("asus_http_api", "web_dom"),
    ),
    VendorSignatureRule(
        adapter_id="mikrotik",
        vendor_name="MikroTik",
        strong_markers=("mikrotik", "routeros", "webfig", "winbox"),
        weak_markers=(),
        model_patterns=(r"\b(RB\d+[A-Za-z0-9\-]*|hAP\s+[A-Za-z0-9\-]*|CCR\d+[A-Za-z0-9\-]*)\b",),
        default_protocols=("routeros_rest", "routeros_api", "webfig", "snmp"),
    ),
    VendorSignatureRule(
        adapter_id="openwrt",
        vendor_name="OpenWrt",
        strong_markers=("luci", "/cgi-bin/luci", "openwrt", "uhttpd"),
        weak_markers=(),
        model_patterns=(r"OpenWrt\s+([0-9\.]+[^\s<]*)",),
        default_protocols=("ubus_rpc", "luci_web", "ssh"),
    ),
    VendorSignatureRule(
        adapter_id="tenda",
        vendor_name="Tenda",
        strong_markers=("goform/login", "tenda", "w15e", "ac1200", "rx2", "tx3", "f3"),
        weak_markers=(),
        model_patterns=(r"\b(AC\d+|RX\d+[A-Za-z0-9\-]*|TX\d+[A-Za-z0-9\-]*|F\d+)\b",),
        default_protocols=("tenda_goform", "web_dom"),
    ),
    VendorSignatureRule(
        adapter_id="dlink",
        vendor_name="D-Link",
        strong_markers=("dlink", "d-link", "hnap1", "/soapact", "dir-", "dsl-"),
        weak_markers=(),
        model_patterns=(r"\b((?:DIR|DSL|COVR|EXO|DAP)-[A-Z0-9\-]+)\b",),
        default_protocols=("hnap_soap", "web_dom"),
    ),
    VendorSignatureRule(
        adapter_id="nokia",
        vendor_name="Nokia",
        strong_markers=("nokia", "alcatel-lucent", "g-2425", "g-140w", "fastmile", "beacon"),
        weak_markers=(),
        model_patterns=(r"\b(G-\d+[A-Z\-]*|Beacon\s*[0-9\.]+|FastMile[^\s<'\"]*)\b",),
        default_protocols=("nokia_http", "web_dom"),
    ),
    VendorSignatureRule(
        adapter_id="sercomm",
        vendor_name="Sercomm",
        strong_markers=("sercomm", "vd625", "h300s", "fg4278"),
        weak_markers=(),
        model_patterns=(r"\b(VD\d+[A-Z0-9\-]*|H\d{3}[A-Z]|FG\d+[A-Z0-9\-]*)\b",),
        default_protocols=("sercomm_http", "web_dom"),
    ),
    VendorSignatureRule(
        adapter_id="sagemcom",
        vendor_name="Sagemcom",
        strong_markers=("sagemcom", "f@st", "fast5", "livebox"),
        weak_markers=(),
        model_patterns=(r"\b(F@?ST\s*\d+[A-Z0-9\-]*)\b",),
        default_protocols=("sagemcom_json", "web_dom"),
    ),
    VendorSignatureRule(
        adapter_id="fiberhome",
        vendor_name="FiberHome",
        strong_markers=("fiberhome", "hg6143", "hg6243", "an5506", "sr1041"),
        weak_markers=(),
        model_patterns=(r"\b((?:HG6|AN55|SR10)\d+[A-Z0-9\-]*)\b",),
        default_protocols=("fiberhome_http", "web_dom"),
    ),
    VendorSignatureRule(
        adapter_id="netgear",
        vendor_name="Netgear",
        strong_markers=("netgear", "currentsetting.htm", "nighthawk", "orbi", "genie"),
        weak_markers=(),
        model_patterns=(r"\b((?:R|RAX|RBK|XR|D)\d+[A-Z0-9\-]*)\b",),
        default_protocols=("netgear_soap", "web_dom"),
    ),
)

IMPLEMENTED_NATIVE_ADAPTERS = frozenset({"huawei", "zte", "tplink", "asus", "mikrotik"})


def _unescape_js_string(raw: str) -> str:
    """Decode common JS hex escapes like '\\x2d' -> '-' safely."""
    if not raw:
        return ""
    return re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), raw).strip()


def _detect_isp_brand(text_lower: str) -> Optional[str]:
    for isp_name, markers in ISP_BRAND_MARKERS:
        if any(m in text_lower for m in markers):
            return isp_name
    return None


def _extract_model_and_firmware(
    rule: Optional[VendorSignatureRule],
    body: str,
    headers: Dict[str, str],
    upnp_model: Optional[str],
    title_text: Optional[str],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (model, hardware_revision, firmware_version)."""
    model = upnp_model.strip() if upnp_model and upnp_model.strip() else None
    if not model and rule:
        for pat in rule.model_patterns:
            m = re.search(pat, body, re.IGNORECASE)
            if m:
                candidate = _unescape_js_string(m.group(1))
                if candidate and len(candidate) <= 64:
                    model = candidate
                    break
    if not model and title_text:
        clean_title = _unescape_js_string(title_text)
        # Skip generic titles like "Login" or empty strings
        if clean_title and clean_title.lower() not in {"login", "router", "welcome", "home", "index"}:
            model = clean_title[:64]

    hw_rev = None
    m_hw = re.search(
        r"(?:HardwareVersion|hwVer|hw_version|var\s+HardwareVer)\s*[:=]\s*['\"]?([A-Za-z0-9._\-]+)",
        body,
        re.IGNORECASE,
    )
    if m_hw:
        hw_rev = _unescape_js_string(m_hw.group(1))

    fw_ver = None
    for pat in (
        r"(?:SoftwareVersion|FirmwareVersion|fwVer|var\s+SoftwareVer|var\s+swVer)\s*[:=]\s*['\"]([^'\"]+)['\"]",
        r"(V\d{3}R\d{3}C\d{2,}[^\s'\"<]*)",
    ):
        m_fw = re.search(pat, body, re.IGNORECASE)
        if m_fw:
            fw_ver = _unescape_js_string(m_fw.group(1))
            break
    if not fw_ver and headers.get("server"):
        fw_ver = headers.get("server")

    return model, hw_rev, fw_ver


@dataclass
class InterfaceProbe:
    interface_type: str  # "https_web", "http_web", "upnp_igd", "tr069_cwmp", "usp", "snmp", "mikrotik_api", "ssh", "telnet", "web_dom"
    port: int
    transport: str  # "tcp" / "udp" / "browser"
    reachable: bool
    authorized: bool = False
    read_supported: bool = False
    write_supported: bool = False
    details: str = ""


@dataclass
class RouterFingerprint:
    management_ip: str
    management_url: Optional[str] = None
    gateway_mac: Optional[str] = None
    hardware_vendor: Optional[str] = None
    model: Optional[str] = None
    hardware_revision: Optional[str] = None
    firmware_version: Optional[str] = None
    isp_brand: Optional[str] = None
    adapter_id: str = "generic_probe"
    confidence: str = "low"  # "high", "medium", "low"
    wan_connection_hint: Optional[str] = None
    lan_subnet: Optional[str] = None
    supported_bands_hint: List[str] = field(default_factory=list)
    interfaces: List[InterfaceProbe] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    snmp_sys_descr: Optional[str] = None
    web_dom_available: bool = False


class RouterFingerprintService:
    """Universal hardware-vs-ISP router fingerprinting & open-interface detector."""

    @staticmethod
    def lookup_oui_vendor(mac: Optional[str]) -> Optional[str]:
        if not mac:
            return None
        prefix = mac.strip().upper().replace("-", ":")[:8]
        return EXTENDED_ROUTER_OUIS.get(prefix)

    @classmethod
    def classify_http_evidence(
        cls,
        *,
        headers: Dict[str, str],
        body: str,
        oui_vendor: Optional[str] = None,
        upnp_manufacturer: Optional[str] = None,
        upnp_model: Optional[str] = None,
        snmp_sys_descr: Optional[str] = None,
    ) -> Tuple[str, Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], str, List[str]]:
        """Classify vendor, model, hw_rev, fw_ver, isp_brand, confidence, evidence.

        Crucially keeps ``oui_vendor`` separate from HTTP/JS/UPnP/SNMP evidence so a mistaken
        or shared MAC OUI (such as Huawei DN8245V-56 using F8:95:22) NEVER overrides explicit
        portal markers like ``ProductName = 'DN8245V-56'`` or ``/asp/GetRandCount.asp``.
        Returns: (adapter_id, hardware_vendor, model, hw_rev, fw_ver, isp_brand, confidence, evidence)
        """
        hdr_lower = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
        snippet = body[:32768] if body else ""
        primary_text = " ".join(
            [
                hdr_lower.get("server", ""),
                hdr_lower.get("www-authenticate", ""),
                hdr_lower.get("set-cookie", ""),
                snippet,
                upnp_manufacturer or "",
                upnp_model or "",
                snmp_sys_descr or "",
            ]
        )
        primary_lower = primary_text.lower()
        title_m = re.search(r"<title[^>]*>(.*?)</title>", snippet, re.IGNORECASE | re.DOTALL)
        title_text = title_m.group(1).strip() if title_m else None

        isp_brand = _detect_isp_brand(primary_lower)
        evidence: List[str] = []

        best_score = 0
        best_rule: Optional[VendorSignatureRule] = None
        best_hits: List[str] = []

        for rule in VENDOR_RULES:
            score = 0
            hits: List[str] = []
            for marker in rule.strong_markers:
                if marker in primary_lower:
                    score += 10
                    hits.append(f"strong:{marker}")
            for marker in rule.weak_markers:
                if marker in primary_lower:
                    score += 3
                    hits.append(f"weak:{marker}")
            if upnp_manufacturer and rule.vendor_name.lower() in upnp_manufacturer.lower():
                score += 8
                hits.append(f"upnp_mfg:{upnp_manufacturer}")
            if snmp_sys_descr and rule.vendor_name.lower() in snmp_sys_descr.lower():
                score += 8
                hits.append("snmp_sysdescr")
            # Minor tie-breaker only if HTTP already hinted or nothing else matched
            if oui_vendor and rule.vendor_name.lower() in oui_vendor.lower():
                score += 1
                hits.append(f"oui:{oui_vendor}")

            if score > best_score:
                best_score = score
                best_rule = rule
                best_hits = hits

        if best_rule and best_score >= 3:
            model, hw_rev, fw_ver = _extract_model_and_firmware(
                best_rule, snippet, hdr_lower, upnp_model, title_text
            )
            adapter_id = (
                best_rule.adapter_id
                if best_rule.adapter_id in IMPLEMENTED_NATIVE_ADAPTERS
                else f"isp_generic:{best_rule.adapter_id}"
            )
            confidence = "high" if best_score >= 10 else "medium"
            evidence.extend(best_hits[:6])
            if isp_brand:
                evidence.append(f"isp_brand:{isp_brand}")
            if oui_vendor and best_rule.vendor_name.lower() not in oui_vendor.lower():
                evidence.append(f"oui_overridden:{oui_vendor}->{best_rule.vendor_name}")
            return (
                adapter_id,
                best_rule.vendor_name,
                model,
                hw_rev,
                fw_ver,
                isp_brand,
                confidence,
                evidence,
            )

        # Fallback if only OUI or UPnP/SNMP existed without known signature markers
        fallback_vendor = upnp_manufacturer or oui_vendor
        model = upnp_model or (
            title_text
            if title_text and title_text.lower() not in {"login", "welcome", "router", "index"}
            else None
        )
        adapter_id = "generic_probe"
        if fallback_vendor:
            fv_lower = fallback_vendor.lower()
            for rule in VENDOR_RULES:
                if rule.vendor_name.lower() in fv_lower and rule.adapter_id in IMPLEMENTED_NATIVE_ADAPTERS:
                    adapter_id = rule.adapter_id
                    fallback_vendor = rule.vendor_name
                    break
        if oui_vendor:
            evidence.append(f"oui_fallback:{oui_vendor}")
        if isp_brand:
            evidence.append(f"isp_brand:{isp_brand}")
        return (
            adapter_id,
            fallback_vendor,
            model,
            None,
            hdr_lower.get("server"),
            isp_brand,
            "medium" if upnp_manufacturer or snmp_sys_descr else "low",
            evidence,
        )

    @staticmethod
    def is_web_dom_available() -> bool:
        """Check whether QtWebEngine DOM automation is installed and importable."""
        try:
            import PySide6.QtWebEngineCore  # noqa: F401
            import PySide6.QtWebEngineWidgets  # noqa: F401
            return True
        except Exception:
            return False

    async def probe_management_interfaces(
        self,
        ip: str,
        *,
        discovery: Optional[RouterDiscoveryResult] = None,
        timeout_s: float = 0.7,
    ) -> List[InterfaceProbe]:
        """Probe which local management protocols/ports are actually open on the router."""
        # Restrict strictly to private/local RFC1918/ULA gateway IPs
        try:
            addr = ipaddress.ip_address(ip)
            if not (addr.is_private or addr.is_loopback or addr.is_link_local):
                return []
        except ValueError:
            return []

        tcp_targets: List[Tuple[str, int, str]] = [
            ("https_web", 443, "HTTPS Web Admin / REST / ASP"),
            ("http_web", 80, "HTTP Web Admin / REST / ASP"),
            ("https_alt", 8443, "Alternate HTTPS Web Admin"),
            ("http_alt", 8080, "Alternate HTTP Web Admin"),
            ("tr069_cwmp", 7547, "TR-069 / CWMP local endpoint (port check only)"),
            ("mikrotik_api_tls", 8729, "MikroTik RouterOS TLS API"),
            ("mikrotik_api", 8728, "MikroTik RouterOS Binary API"),
            ("ssh", 22, "SSH CLI (requires explicit user opt-in & authorization)"),
            ("telnet", 23, "Telnet CLI (disabled/discouraged unless explicitly open & authorized)"),
        ]

        async def _check_tcp(iface: str, port: int, desc: str) -> InterfaceProbe:
            def _try() -> bool:
                s = socket.socket(socket.AF_INET if addr.version == 4 else socket.AF_INET6, socket.SOCK_STREAM)
                s.settimeout(timeout_s)
                try:
                    return s.connect_ex((ip, port)) == 0
                except OSError:
                    return False
                finally:
                    try:
                        s.close()
                    except OSError:
                        pass

            ok = await asyncio.to_thread(_try)
            return InterfaceProbe(
                interface_type=iface,
                port=port,
                transport="tcp",
                reachable=ok,
                authorized=False,
                read_supported=False,
                write_supported=False,
                details=desc if ok else "port_closed",
            )

        probes = await asyncio.gather(*(_check_tcp(t, p, d) for t, p, d in tcp_targets))
        results = list(probes)

        # Read-only SNMP v1/v2c sysDescr probe on UDP/161 (single non-intrusive GetRequest, community 'public')
        snmp_probe = await asyncio.to_thread(self._probe_snmp_readonly, ip, timeout_s)
        results.append(snmp_probe)

        if discovery and (discovery.upnp_manufacturer or discovery.upnp_model):
            results.append(
                InterfaceProbe(
                    interface_type="upnp_igd",
                    port=1900,
                    transport="udp",
                    reachable=True,
                    authorized=True,
                    read_supported=True,
                    write_supported=False,
                    details=f"UPnP IGD ({discovery.upnp_manufacturer or ''} {discovery.upnp_model or ''})".strip(),
                )
            )
        else:
            results.append(
                InterfaceProbe(
                    interface_type="upnp_igd",
                    port=1900,
                    transport="udp",
                    reachable=False,
                    details="no_igd_response",
                )
            )

        web_dom_ok = self.is_web_dom_available()
        any_http = any(p.reachable and p.interface_type in {"https_web", "http_web", "https_alt", "http_alt"} for p in results)
        results.append(
            InterfaceProbe(
                interface_type="web_dom",
                port=443 if any(p.reachable and p.port == 443 for p in results) else 80,
                transport="browser",
                reachable=bool(web_dom_ok and any_http),
                authorized=False,
                read_supported=False,
                write_supported=False,
                details="PySide6 QtWebEngine DOM inspector available" if web_dom_ok else "QtWebEngine unavailable",
            )
        )
        return results

    @staticmethod
    def _probe_snmp_readonly(ip: str, timeout_s: float) -> InterfaceProbe:
        """Send a single ASN.1/BER SNMPv2c GetRequest for sysDescr.0 (1.3.6.1.2.1.1.1.0) on UDP/161."""
        # Pre-encoded SNMPv2c GetRequest (community="public", OID=1.3.6.1.2.1.1.1.0)
        pkt = bytes.fromhex(
            "3029"  # SEQUENCE len 41
            "020101"  # version = v2c (1)
            "04067075626c6963"  # community = "public"
            "a01c"  # GetRequest-PDU len 28
            "02041a2b3c4d"  # request-id
            "020100"  # error-status = 0
            "020100"  # error-index = 0
            "300e"  # varbind list
            "300c"  # varbind
            "06082b06010201010100"  # 1.3.6.1.2.1.1.1.0 (sysDescr.0)
            "0500"  # NULL
        )
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(min(timeout_s, 0.6))
        try:
            sock.sendto(pkt, (ip, 161))
            data, _ = sock.recvfrom(2048)
            # Extract printable ASCII runs if SNMP agent replied
            text_runs = re.findall(rb"[\x20-\x7e]{6,}", data)
            descr = " ".join(r.decode("ascii", errors="ignore") for r in text_runs if r != b"public")
            return InterfaceProbe(
                interface_type="snmp",
                port=161,
                transport="udp",
                reachable=True,
                authorized=True,
                read_supported=True,
                write_supported=False,  # Never assume read implies write
                details=descr[:200] or "SNMPv2c read-only responded",
            )
        except OSError:
            return InterfaceProbe(
                interface_type="snmp",
                port=161,
                transport="udp",
                reachable=False,
                details="snmp_closed_or_filtered",
            )
        finally:
            try:
                sock.close()
            except OSError:
                pass


class RouterCapabilityDetector:
    """Builds and verifies a strict RouterCapabilities profile.

    No capability is marked supported unless actually verified through an authenticated read/probe.
    """

    @staticmethod
    def build_unverified_baseline(
        discovery: RouterDiscoveryResult,
        fingerprint: Optional[RouterFingerprint] = None,
    ) -> RouterCapabilities:
        """Return a conservative capability profile prior to authenticated verification."""
        return RouterCapabilities(
            adapter_id=discovery.adapter_id,
            vendor_family=discovery.hardware_vendor or discovery.detected_vendor or "Generic",
            hardware_verified=False,
            supports_session_auth=bool(discovery.preferred_url or discovery.reachable_ports),
            supports_web_dom_inspection=bool(fingerprint and fingerprint.web_dom_available),
            supports_snmp_read=bool(
                fingerprint and any(p.interface_type == "snmp" and p.read_supported for p in fingerprint.interfaces)
            ),
            supports_tr069_or_usp=bool(
                fingerprint and any(p.interface_type == "tr069_cwmp" and p.reachable for p in fingerprint.interfaces)
            ),
            limitations=[
                (
                    f"Detected {discovery.hardware_vendor or discovery.detected_vendor or 'Unknown'} "
                    f"{discovery.detected_model or ''} (adapter={discovery.adapter_id}). "
                    "Capabilities remain unverified until authenticated inspection."
                ).strip()
            ],
        )
