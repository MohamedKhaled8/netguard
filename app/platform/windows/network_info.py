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
from typing import Dict, List, Any

_cached_isp_info: Dict[str, str] | None = None


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

    # 1. Try PowerShell Get-NetConnectionProfile for network name
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
            timeout=3.0,
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

    # 2. Inspect netsh wlan show interfaces with locale-independent parsing
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
    """Inspects active IPv4 DNS servers for the specified interface via PowerShell ConvertTo-Json."""
    try:
        cmd = [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            f"Get-DnsClientServerAddress -InterfaceAlias '{interface_name}' -AddressFamily IPv4 | Select-Object -ExpandProperty ServerAddresses | ConvertTo-Json",
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
            if isinstance(data, str) and re.match(r"^\d{1,3}(?:\.\d{1,3}){3}$", data):
                return [data]
            elif isinstance(data, list):
                return [s for s in data if isinstance(s, str) and re.match(r"^\d{1,3}(?:\.\d{1,3}){3}$", s)]
    except Exception:
        pass

    try:
        res = subprocess.run(
            ["netsh", "interface", "ipv4", "show", "dnsservers", interface_name],
            capture_output=True,
            text=True,
            timeout=2.0,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        if res.returncode == 0 and res.stdout:
            ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", res.stdout)
            if ips:
                return ips
    except Exception:
        pass

    return []


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

    has_goog = any(ip in ("8.8.8.8", "8.8.4.4") for ip in (primary, secondary))
    has_cf = any(ip in ("1.1.1.1", "1.0.0.1") for ip in (primary, secondary))
    has_quad9 = any(ip in ("9.9.9.9", "149.112.112.112") for ip in (primary, secondary))
    has_opendns = any(ip in ("208.67.222.222", "208.67.220.220") for ip in (primary, secondary))

    if has_goog and has_cf:
        return {
            "name": "Google + Cloudflare (مزدوج)",
            "ips": ips_str,
            "tag": "Google & Cloudflare",
            "is_google": True,
            "is_cloudflare": True,
        }
    elif has_goog:
        return {
            "name": "Google DNS الأساسي",
            "ips": ips_str,
            "tag": "Google DNS",
            "is_google": True,
            "is_cloudflare": False,
        }
    elif has_cf:
        return {
            "name": "Cloudflare DNS الأساسي",
            "ips": ips_str,
            "tag": "Cloudflare DNS",
            "is_google": False,
            "is_cloudflare": True,
        }
    elif has_quad9:
        return {
            "name": "Quad9 DNS الآمن",
            "ips": ips_str,
            "tag": "Quad9 DNS",
            "is_google": False,
            "is_cloudflare": False,
        }
    elif has_opendns:
        return {
            "name": "OpenDNS (Cisco)",
            "ips": ips_str,
            "tag": "OpenDNS",
            "is_google": False,
            "is_cloudflare": False,
        }
    elif primary == gateway_ip or primary.startswith("192.168.") or primary.startswith("10."):
        return {
            "name": "خادم الراوتر الافتراضي (DHCP)",
            "ips": ips_str,
            "tag": "راوتر محلي",
            "is_google": False,
            "is_cloudflare": False,
        }
    else:
        return {
            "name": f"خادم مخصص ({primary})",
            "ips": ips_str,
            "tag": "DNS مخصص",
            "is_google": False,
            "is_cloudflare": False,
        }


def get_isp_and_public_ip() -> Dict[str, str]:
    """Fast lookup of public IP and ISP company name."""
    global _cached_isp_info
    if _cached_isp_info:
        return _cached_isp_info

    try:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            "https://ipinfo.io/json",
            headers={"User-Agent": "NetGuardAI/2.0"},
        )
        with urllib.request.urlopen(req, timeout=2.0, context=ctx) as resp:
            data = json.loads(resp.read().decode())
            org = data.get("org", "")
            if "TE-AS" in org or "Telecom Egypt" in org:
                company = "Telecom Egypt (WE / المصرية للاتصالات)"
            elif "Orange" in org or "Mobinil" in org:
                company = "Orange Egypt (أورنج مصر)"
            elif "Vodafone" in org:
                company = "Vodafone Egypt (فودافون مصر)"
            elif "Etisalat" in org:
                company = "e& Egypt (اتصالات مصر)"
            else:
                company = org or "مزود خدمة محلي"

            _cached_isp_info = {
                "ip": data.get("ip") or "—",
                "city": data.get("city") or "—",
                "company": company,
            }
            return _cached_isp_info
    except Exception:
        return {
            "ip": "—",
            "city": "—",
            "company": "غير متوفر (غير متصل)",
        }
