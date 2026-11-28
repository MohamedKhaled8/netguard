"""Windows Real Network Environment & Hardware Inspector.

Detects:
- Active Wi-Fi SSID, Band (5GHz/2.4GHz), Signal Quality, and Network Card model.
- Active configured DNS servers.
- ISP Provider Company (Orange Egypt / Telecom Egypt WE) and Public IP.
- Default Gateway Router Address.
"""

from __future__ import annotations
import subprocess
import re
import urllib.request
import json
import logging
import socket
from typing import Dict, List, Any, Optional

logger = logging.getLogger("netguard.platform.network_info")

_cached_isp_info: Dict[str, str] | None = None
_cached_isp_gateway: Optional[str] = None
_cached_hop2_info: Optional[Dict[str, Any]] = None


_RE_SSID = re.compile(r"^\s*SSID\s*:\s*(.+)$", re.M)
_RE_BAND = re.compile(r"^\s*Band\s*:\s*(.+)$", re.M)
_RE_SIGNAL = re.compile(r"^\s*Signal\s*:\s*(.+)$", re.M)
_RE_DESC = re.compile(r"^\s*Description\s*:\s*(.+)$", re.M)
_RE_PROFILE = re.compile(r"All User Profile\s*:\s*(.+)")


def get_wifi_details() -> Dict[str, Any]:
    """Inspects native Windows WLAN interfaces and connection profile in a locale-independent manner."""
    ssid = None
    signal = None
    adapter = None
    band = "—"

    # 1. Fast path: Inspect netsh wlan show interfaces directly (<50ms)
    try:
        out = subprocess.check_output(
            ["netsh", "wlan", "show", "interfaces"],
            text=True,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        for line in out.splitlines():
            line = line.strip()
            if ":" not in line:
                continue
            k, v = [x.strip() for x in line.split(":", 1)]
            if not ssid and "ssid" in k.lower() and "bssid" not in k.lower():
                ssid = v
            m_sig = re.search(r"(\d+)\s*%", v)
            if m_sig:
                signal = f"{m_sig.group(1)}%"
            if any(term in k.lower() for term in ("desc", "وصف", "beschreibung", "nom")):
                adapter = v
            if any(term in k.lower() for term in ("band", "نطاق", "funktyp", "radio")):
                band = v
    except Exception:
        pass

    # 2. Fallback only if netsh yielded no SSID (e.g. wired Ethernet profile name)
    if not ssid:
        try:
            cmd_profile = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-NetConnectionProfile | Select-Object Name, InterfaceAlias, IPv4Connectivity | ConvertTo-Json",
            ]
            proc = subprocess.run(
                cmd_profile,
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout)
                if isinstance(data, list) and data:
                    data = data[0]
                if isinstance(data, dict):
                    ssid = data.get("Name")
        except Exception:
            pass

    if not ssid:
        return {
            "ssid": "غير متصل (أو سلكي)",
            "band": "—",
            "signal": "—",
            "adapter": adapter or "محول الشبكة",
            "is_hotspot": False,
            "hotspot_name": "—",
            "upstream_router": "الراوتر المنزلي",
            "upstream_summary": "اتصال سلكي أو محول متوقف",
        }

    is_hotspot = any(kw in ssid.lower() for kw in ("hotspot", "iphone", "galaxy", "pixel", "phone", "redmi", "huawei"))
    home_router_name = f"راوتر {ssid}"

    return {
        "ssid": ssid,
        "band": band if band != "—" else ("5 GHz" if signal and int(signal.replace('%', '')) > 70 else "2.4 GHz"),
        "signal": signal or "—",
        "adapter": adapter or "محول شبكة لاسلكي",
        "is_hotspot": is_hotspot,
        "hotspot_name": ssid if is_hotspot else "—",
        "upstream_router": home_router_name if is_hotspot else f"راوتر {ssid} المباشر",
        "upstream_summary": f"نقطة اتصال هاتف: {ssid}" if is_hotspot else "اتصال مباشر بالراوتر المنزلي",
    }


def get_active_dns_servers(interface_name: str = "Wi-Fi") -> List[str]:
    """Inspects active IPv4 and IPv6 DNS servers for the specified interface."""
    servers: List[str] = []
    try:
        cmd = [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            f"(Get-DnsClientServerAddress -InterfaceAlias '{interface_name}').ServerAddresses | ConvertTo-Json",
        ]
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3.0,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout)
            raw_list = [data] if isinstance(data, str) else (data if isinstance(data, list) else [])
            for item in raw_list:
                if isinstance(item, str) and item.strip():
                    try:
                        import ipaddress
                        ip_obj = ipaddress.ip_address(item.strip())
                        if not ip_obj.is_loopback and not ip_obj.is_unspecified and item.strip() not in servers:
                            servers.append(item.strip())
                    except ValueError:
                        pass
            if servers:
                return servers
    except Exception as exc:
        logger.debug("PowerShell DNS server query failed for %s: %s", interface_name, exc)

    try:
        for family in ("ipv4", "ipv6"):
            res = subprocess.run(
                ["netsh", "interface", family, "show", "dnsservers", interface_name],
                capture_output=True,
                text=True,
                timeout=2.0,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            if res.returncode == 0 and res.stdout:
                for line in res.stdout.splitlines():
                    for word in line.strip().split():
                        try:
                            import ipaddress
                            ip_obj = ipaddress.ip_address(word)
                            if not ip_obj.is_loopback and not ip_obj.is_unspecified and word not in servers:
                                servers.append(word)
                        except ValueError:
                            pass
        if servers:
            return servers
    except Exception as exc:
        logger.debug("netsh DNS server query failed for %s: %s", interface_name, exc)

    return servers


def resolve_dns_provider_label(dns_servers: List[str], gateway_ip: str = "") -> Dict[str, Any]:
    """Resolves DNS servers into canonical provider name, formatted IP string, and badge."""
    if not dns_servers:
        return {
            "name": "خادم الراوتر الافتراضي (DHCP)",
            "ips": gateway_ip or "192.168.1.1",
            "tag": "راوتر محلي",
            "is_google": False,
            "is_cloudflare": False,
        }

    primary = dns_servers[0].strip()
    secondary = dns_servers[1].strip() if len(dns_servers) > 1 else ""
    ips_str = f"{primary}  ·  {secondary}" if secondary else primary

    from app.dns.detector import identify_provider
    prov_name = identify_provider(primary)

    is_cf = (primary in ("1.1.1.1", "1.0.0.1") or secondary in ("1.1.1.1", "1.0.0.1"))
    is_goog = (primary in ("8.8.8.8", "8.8.4.4") or secondary in ("8.8.8.8", "8.8.4.4"))

    if is_cf and is_goog:
        return {
            "name": "Cloudflare + Google (مزدوج)",
            "ips": ips_str,
            "tag": "Cloudflare & Google",
            "is_google": True,
            "is_cloudflare": True,
        }

    if prov_name:
        if primary == "1.0.0.1":
            label = "Cloudflare DNS الاحتياطي"
        elif primary == "1.1.1.1":
            label = "Cloudflare DNS الأساسي"
        elif primary == "8.8.4.4":
            label = "Google DNS الاحتياطي"
        elif primary == "8.8.8.8":
            label = "Google DNS الأساسي"
        elif primary == "149.112.112.112":
            label = "Quad9 DNS الاحتياطي"
        elif primary == "9.9.9.9":
            label = "Quad9 DNS الآمن"
        else:
            label = prov_name

        return {
            "name": label,
            "ips": ips_str,
            "tag": prov_name,
            "is_google": is_goog,
            "is_cloudflare": is_cf,
        }

    if primary == gateway_ip or primary.startswith("192.168.") or primary.startswith("10.") or primary.startswith("172.16."):
        return {
            "name": "خادم الراوتر الافتراضي (DHCP)",
            "ips": ips_str,
            "tag": "راوتر محلي",
            "is_google": False,
            "is_cloudflare": False,
        }

    return {
        "name": f"خادم مخصص ({primary})",
        "ips": ips_str,
        "tag": "DNS مخصص",
        "is_google": False,
        "is_cloudflare": False,
    }


def get_local_ip(interface_name: str = "") -> str:
    """Detect internal local IPv4 address of the device."""
    try:
        import psutil
        if interface_name:
            addrs = psutil.net_if_addrs().get(interface_name, [])
            for a in addrs:
                if a.family == socket.AF_INET and not a.address.startswith("127."):
                    return a.address
        # Fallback to routing lookup via dummy UDP socket without sending packets
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        if local_ip and not local_ip.startswith("127."):
            return local_ip
    except Exception:
        pass

    try:
        import psutil
        for iface_name, addrs in psutil.net_if_addrs().items():
            for a in addrs:
                if a.family == socket.AF_INET and not a.address.startswith("127."):
                    return a.address
    except Exception:
        pass

    return "127.0.0.1"


def get_isp_and_public_ip(force_refresh: bool = False) -> Dict[str, str]:
    """Fast lookup of public IP and ISP company name with redundant fallback APIs."""
    global _cached_isp_info
    if _cached_isp_info and not force_refresh:
        return _cached_isp_info

    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    def _canonicalize_isp_name(org_str: str) -> str:
        if not org_str:
            return "مزود خدمة محلي"
        if "TE-AS" in org_str or "Telecom Egypt" in org_str or "TE Data" in org_str or "TEDATA" in org_str:
            return "المصرية للاتصالات (WE)"
        elif "Orange" in org_str or "Mobinil" in org_str:
            return "أورنج مصر (Orange)"
        elif "Vodafone" in org_str:
            return "فودافون مصر (Vodafone)"
        elif "Etisalat" in org_str or "e&" in org_str:
            return "اتصالات مصر (e&)"
        return org_str

    # 1. Primary: ipinfo.io
    try:
        req = urllib.request.Request("https://ipinfo.io/json", headers={"User-Agent": "NetGuardAI/2.0"})
        with urllib.request.urlopen(req, timeout=2.5, context=ctx) as resp:
            data = json.loads(resp.read().decode())
            pub_ip = data.get("ip") or "—"
            org = data.get("org") or ""
            company = _canonicalize_isp_name(org)
            if pub_ip != "—":
                _cached_isp_info = {
                    "ip": pub_ip,
                    "city": data.get("city") or "—",
                    "company": company,
                    "status": "ok",
                }
                return _cached_isp_info
    except Exception as exc:
        logger.debug("Primary ipinfo.io lookup failed: %s", exc)

    # 2. Secondary fallback: ip-api.com
    try:
        req = urllib.request.Request("http://ip-api.com/json/?fields=status,message,country,city,isp,org,query", headers={"User-Agent": "NetGuardAI/2.0"})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode())
            if data.get("status") == "success":
                pub_ip = data.get("query") or "—"
                isp_name = data.get("isp") or data.get("org") or ""
                company = _canonicalize_isp_name(isp_name)
                _cached_isp_info = {
                    "ip": pub_ip,
                    "city": data.get("city") or "—",
                    "company": company,
                    "status": "ok",
                }
                return _cached_isp_info
    except Exception as exc:
        logger.debug("Secondary ip-api.com lookup failed: %s", exc)

    return {
        "ip": "—",
        "city": "—",
        "company": "غير متوفر (غير متصل بالإنترنت)",
        "status": "unavailable",
    }


def get_hop2_diagnostics(gateway_ip: str = "192.168.1.1", force_refresh: bool = False) -> Dict[str, Any]:
    """Diagnoses Hop 2 (the next-hop router beyond local gateway) via real multi-protocol probes.

    Never automatically labels Hop 2 as DSLAM, BRAS, BNG, or an ISP cabinet.
    """
    global _cached_hop2_info, _cached_isp_gateway
    if _cached_hop2_info and not force_refresh:
        return _cached_hop2_info

    try:
        from app.diagnosis.traceroute import IcmpTracerouteEngine, HopClassification
        engine = IcmpTracerouteEngine()
        report = engine.run_trace("1.1.1.1", max_hops=4, probes_per_hop=2, timeout_ms=800)
        h2 = report.get_hop(2)

        if h2 and h2.ip and h2.classification == HopClassification.RESPONDING:
            _cached_isp_gateway = h2.ip
            _cached_hop2_info = {
                "hop_number": 2,
                "ip": h2.ip,
                "latency_ms": h2.avg_rtt_ms,
                "protocol": "ICMP",
                "classification": HopClassification.RESPONDING.value,
                "reason": "استجابت المحطة بنجاح وتم تسجيل عنوانها وزمن وصول الحزم الفعلي",
                "subsequent_responded": h2.subsequent_hops_responded,
                "status": "ok",
            }
            return _cached_hop2_info
        elif h2 and h2.classification == HopClassification.PATH_CONTINUES:
            _cached_hop2_info = {
                "hop_number": 2,
                "ip": None,
                "latency_ms": None,
                "protocol": "ICMP",
                "classification": HopClassification.PATH_CONTINUES.value,
                "reason": h2.reason or "حجب استجابات التحكم (Control-Plane ICMP) مع استمرار مرور البيانات للمحطات اللاحقة",
                "subsequent_responded": True,
                "status": "filtered_passing",
            }
            return _cached_hop2_info
        elif h2:
            _cached_hop2_info = {
                "hop_number": 2,
                "ip": None,
                "latency_ms": None,
                "protocol": "ICMP",
                "classification": h2.classification.value,
                "reason": h2.reason or "المحطة لم تستجب للاستطلاع المباشر",
                "subsequent_responded": h2.subsequent_hops_responded,
                "status": "inconclusive",
            }
            return _cached_hop2_info
    except Exception as exc:
        logger.debug("Hop 2 diagnostic lookup failed: %s", exc)

    # Fallback to existing tracert
    legacy_ip = _query_hop2_ip_cli(gateway_ip)
    _cached_hop2_info = {
        "hop_number": 2,
        "ip": legacy_ip,
        "latency_ms": None,
        "protocol": "ICMP",
        "classification": "RESPONDING" if legacy_ip else "SILENT_HOP",
        "reason": "استجابت المحطة" if legacy_ip else "المحطة لم تستجب للاستطلاع المباشر",
        "subsequent_responded": False,
        "status": "ok" if legacy_ip else "unknown",
    }
    return _cached_hop2_info


def _query_hop2_ip_cli(gateway_ip: str = "192.168.1.1") -> Optional[str]:
    try:
        proc = subprocess.run(
            ["tracert", "-d", "-h", "3", "-w", "700", "8.8.8.8"],
            capture_output=True,
            text=True,
            timeout=4.5,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for line in proc.stdout.splitlines():
            line_str = line.strip()
            parts = line_str.split()
            if parts and parts[0] == "2":
                ip_match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", line_str)
                if ip_match:
                    found_ip = ip_match.group(0)
                    if found_ip != gateway_ip and not found_ip.startswith("127."):
                        return found_ip
    except Exception as exc:
        logger.debug("Tracert hop 2 query failed: %s", exc)
    return None


def get_isp_gateway_ip(gateway_ip: str = "192.168.1.1") -> Optional[str]:
    """Discover 2nd hop gateway via real traceroute probe."""
    global _cached_isp_gateway
    if _cached_isp_gateway:
        return _cached_isp_gateway

    hop2 = get_hop2_diagnostics(gateway_ip)
    if hop2.get("ip"):
        _cached_isp_gateway = hop2.get("ip")
        return _cached_isp_gateway

    return None


def get_network_identity(platform_adapter=None, include_hop2: bool = True, include_isp: bool = True) -> Dict[str, Any]:
    """Collect authoritative, comprehensive real-time network environment identity."""
    if platform_adapter is None:
        from app.platform.windows.adapter import WindowsPlatformAdapter
        platform_adapter = WindowsPlatformAdapter()

    iface_raw = platform_adapter.get_primary_interface()
    gw_raw = platform_adapter.get_default_gateway()
    local_ip = get_local_ip(iface_raw or "")
    wifi = get_wifi_details()
    has_real_local = bool(local_ip and not str(local_ip).startswith("127."))
    ssid_raw = str(wifi.get("ssid") or "").strip()
    has_wifi_ssid = bool(ssid_raw and ssid_raw not in ("غير متصل", "—", "-", "غير متصل (أو سلكي)"))

    # Never synthesize a default "Wi-Fi" / "192.168.1.1" identity when adapter is disconnected.
    is_connected = bool(iface_raw or gw_raw or has_real_local or has_wifi_ssid)
    iface = iface_raw or ("Wi-Fi" if has_wifi_ssid else "")
    gw = gw_raw or ""
    dns_servers = platform_adapter.get_interface_dns_servers(iface) if iface else []

    if include_isp and is_connected:
        isp = get_isp_and_public_ip()
    elif not is_connected:
        isp = {"ip": "—", "city": "—", "company": "غير متصل بالشبكة", "status": "disconnected"}
    else:
        isp = _cached_isp_info or {"ip": "—", "city": "", "company": "جاري التحقق من مزود الخدمة...", "status": "checking"}

    if include_hop2 and is_connected and gw:
        hop2_diag = get_hop2_diagnostics(gw)
        isp_gateway = hop2_diag.get("ip") or get_isp_gateway_ip(gw)
        lat = hop2_diag.get("latency_ms")
    else:
        hop2_diag = _cached_hop2_info or {}
        isp_gateway = _cached_isp_gateway or hop2_diag.get("ip")
        lat = hop2_diag.get("latency_ms")

    # Determine connection type display name
    ssid_name = wifi.get("ssid") or "غير متصل"
    is_wifi = wifi.get("is_wifi", True) if "is_wifi" in wifi else ("wi-fi" in iface.lower() or "wlan" in iface.lower() or "wireless" in iface.lower())
    if not is_wifi and iface and ssid_name in ("غير متصل (أو سلكي)", "غير متصل", "—"):
        ssid_name = f"اتصال سلكي ({iface})"

    conn_type = "Wi-Fi" if (is_wifi and is_connected) else ("Ethernet" if (iface and is_connected) else "Disconnected")

    return {
        "iface": iface,
        "interface_name": iface,
        "gateway": gw,
        "gateway_ip": gw,
        "local_ip": local_ip if is_connected else "—",
        "ssid": ssid_name,
        "is_wifi": is_wifi,
        "is_connected": is_connected,
        "connection_type": conn_type,
        "signal": wifi.get("signal", "—"),
        "band": wifi.get("band", "—"),
        "wifi": wifi,
        "dns": dns_servers,
        "dns_servers": dns_servers,
        "isp": isp,
        "isp_company": isp.get("company", "غير متوفر"),
        "public_ip": isp.get("ip", "—"),
        "isp_gateway_ip": isp_gateway,
        "isp_gateway_latency_ms": lat,
        "hop2_diag": hop2_diag,
    }
