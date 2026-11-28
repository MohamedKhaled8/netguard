"""Safe local router gateway discovery, passive HTTP/HTTPS fingerprinting, and read-only UPnP IGD."""

from __future__ import annotations

import asyncio
import http.client
import re
import socket
import ssl
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.monitoring.device_discovery import LocalNetworkScanner

_OUI_SCANNER = LocalNetworkScanner()
from app.wifi.models import RouterCapabilities, RouterDiscoveryResult, utc_now
from app.wifi.router.credentials import (
    evaluate_transport_security_warning,
    validate_local_router_url,
)
from app.wifi.router.fingerprint import RouterFingerprintService

# Signature heuristics retained as reference metadata; primary classification lives in RouterFingerprintService.
VENDOR_SIGNATURES: List[Tuple[str, str, Tuple[str, ...]]] = [
    ("huawei", "Huawei", ("/resource/common/safelogin.js", "/asp/getrandcount.asp", "x_hw_token", "huawei", "hg630", "hg631", "hg658", "dn8245", "sestokinfo", "hilink")),
    ("zte", "ZTE", ("zxhn", "zte corporation", "getpage", "common_page", "frm_logintoken")),
    ("tplink", "TP-Link", ("tp-link", "tplink", "archer", "deco", "sysauth", "stok=")),
    ("asus", "ASUS", ("asus", "asuswrt", "rt-ax", "rt-ac")),
    ("mikrotik", "MikroTik", ("mikrotik", "routeros", "webfig")),
    ("openwrt", "OpenWrt", ("openwrt", "luci")),
    ("tenda", "Tenda", ("tenda", "goform/login")),
    ("dlink", "D-Link", ("dlink", "d-link", "hnap1")),
    ("nokia", "Nokia", ("nokia", "alcatel-lucent", "g-2425", "fastmile")),
    ("sercomm", "Sercomm", ("sercomm", "vd625", "h300s")),
    ("sagemcom", "Sagemcom", ("sagemcom", "f@st", "livebox")),
    ("fiberhome", "FiberHome", ("fiberhome", "hg6143", "an5506")),
    ("netgear", "Netgear", ("netgear", "currentsetting.htm", "nighthawk")),
]


def _tcp_port_open(host: str, port: int, timeout_sec: float = 0.6) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_sec):
            return True
    except OSError:
        return False


def _passive_http_probe(
    url: str, *, allow_loopback: bool = False
) -> Tuple[bool, Optional[bool], Dict[str, str], str]:
    """Perform a single passive GET / to fingerprint vendor/headers without credential attempts."""
    scheme, host, port, is_https = validate_local_router_url(
        url, allow_loopback=allow_loopback
    )
    tls_trusted: Optional[bool] = None
    headers_map: Dict[str, str] = {}
    body_snippet = ""

    if is_https:
        try:
            ctx = ssl.create_default_context()
            conn: http.client.HTTPConnection = http.client.HTTPSConnection(
                host, port, timeout=1.5, context=ctx
            )
            conn.request("GET", "/", headers={"User-Agent": "NetGuardAI-Probe/1.0"})
            resp = conn.getresponse()
            tls_trusted = True
        except ssl.SSLError:
            tls_trusted = False
            ctx_unverified = ssl._create_unverified_context()
            conn = http.client.HTTPSConnection(
                host, port, timeout=1.5, context=ctx_unverified
            )
            try:
                conn.request("GET", "/", headers={"User-Agent": "NetGuardAI-Probe/1.0"})
                resp = conn.getresponse()
            except Exception:
                conn.close()
                return False, tls_trusted, {}, ""
        except Exception:
            return False, None, {}, ""
    else:
        conn = http.client.HTTPConnection(host, port, timeout=1.5)
        try:
            conn.request("GET", "/", headers={"User-Agent": "NetGuardAI-Probe/1.0"})
            resp = conn.getresponse()
        except Exception:
            conn.close()
            return False, None, {}, ""

    try:
        for hk, hv in resp.getheaders():
            headers_map[hk.lower()] = hv
        raw = resp.read(49152)
        body_snippet = raw.decode("utf-8", errors="replace")
        # If HTTP root returns a tiny meta/JS redirect or HTTP 30x to another local path, probe once
        if not body_snippet.strip() and headers_map.get("location"):
            loc = headers_map["location"]
            if loc.startswith("/"):
                try:
                    conn.close()
                    if is_https:
                        ctx_f = ssl.create_default_context() if tls_trusted else ssl._create_unverified_context()
                        conn2 = http.client.HTTPSConnection(host, port, timeout=1.5, context=ctx_f)
                    else:
                        conn2 = http.client.HTTPConnection(host, port, timeout=1.5)
                    conn2.request("GET", loc, headers={"User-Agent": "NetGuardAI-Probe/1.0"})
                    resp2 = conn2.getresponse()
                    for hk, hv in resp2.getheaders():
                        headers_map.setdefault(hk.lower(), hv)
                    body_snippet = resp2.read(49152).decode("utf-8", errors="replace")
                    conn2.close()
                except Exception:
                    pass
        conn.close()
        return True, tls_trusted, headers_map, body_snippet
    except Exception:
        return False, tls_trusted, headers_map, ""
    finally:
        conn.close()


def _detect_vendor_and_model(
    headers: Dict[str, str],
    body: str,
    oui_vendor: Optional[str],
    upnp_manufacturer: Optional[str],
    upnp_model: Optional[str],
) -> Tuple[str, Optional[str], Optional[str]]:
    """Return (adapter_id, vendor_name, model_name)."""
    adapter_id, vendor, model, _hw, _fw, _isp, _conf, _ev = RouterFingerprintService.classify_http_evidence(
        headers=headers,
        body=body,
        oui_vendor=oui_vendor,
        upnp_manufacturer=upnp_manufacturer,
        upnp_model=upnp_model,
    )
    resolved_adapter = (
        adapter_id
        if adapter_id in ("zte", "huawei", "tplink", "asus", "mikrotik") or adapter_id.startswith("isp_generic:")
        else "generic_probe"
    )
    return resolved_adapter, vendor, model


def _ssdp_discover_igd(gateway_ip: str, timeout_sec: float = 0.9) -> Optional[Dict[str, str]]:
    """Send read-only SSDP M-SEARCH on LAN strictly accepting the gateway IGD location."""
    msg = (
        "M-SEARCH * HTTP/1.1\r\n"
        "HOST: 239.255.255.250:1900\r\n"
        'MAN: "ssdp:discover"\r\n'
        "MX: 1\r\n"
        "ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n\r\n"
    ).encode("ascii")

    location: Optional[str] = None
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    try:
        sock.settimeout(timeout_sec)
        sock.sendto(msg, ("239.255.255.250", 1900))
        for _ in range(5):
            try:
                data, addr = sock.recvfrom(4096)
            except OSError:
                break
            if addr[0] != gateway_ip:
                continue
            text = data.decode("utf-8", errors="replace")
            for line in text.splitlines():
                if line.lower().startswith("location:"):
                    cand = line.split(":", 1)[1].strip()
                    try:
                        validate_local_router_url(cand)
                        location = cand
                        break
                    except Exception:
                        continue
            if location:
                break
    except Exception:
        return None
    finally:
        sock.close()

    if not location:
        return None

    try:
        parsed = urllib.parse.urlparse(location)
        host = parsed.hostname or gateway_ip
        port = parsed.port or 80
        path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        conn = http.client.HTTPConnection(host, port, timeout=1.2)
        conn.request("GET", path or "/")
        resp = conn.getresponse()
        xml_bytes = resp.read(65536)
        conn.close()
        root = ET.fromstring(xml_bytes)
        info: Dict[str, str] = {"location": location}
        for tag in (
            "friendlyName",
            "manufacturer",
            "modelName",
            "modelNumber",
            "WANAccessType",
            "NewWANAccessType",
            "ConnectionType",
            "NewExternalIPAddress",
        ):
            el = root.find(f".//{{*}}{tag}")
            if el is not None and el.text:
                info[tag] = el.text.strip()
        return info
    except Exception:
        return {"location": location}


class RouterDiscoveryService:
    """Safely discovers gateway management endpoints, vendor family, and capabilities."""

    def __init__(
        self,
        *,
        platform: Any = None,
        registry: Any = None,
        allow_loopback: bool = False,
        ssdp_fn: Optional[Callable[[str], Optional[Dict[str, str]]]] = None,
    ) -> None:
        self._platform = platform
        self._registry = registry
        self._allow_loopback = allow_loopback
        self._ssdp_fn = ssdp_fn or _ssdp_discover_igd

    async def _resolve_gateway_ip_and_mac(self) -> Tuple[Optional[str], Optional[str]]:
        gw_ip: Optional[str] = None
        if self._platform is not None and hasattr(self._platform, "get_default_gateway"):
            res = self._platform.get_default_gateway()
            if asyncio.iscoroutine(res) or hasattr(res, "__await__"):
                res = await res
            gw_ip = str(res).strip() if res else None

        if not gw_ip:
            gw_ip = await asyncio.to_thread(self._resolve_os_default_gateway)

        gw_mac: Optional[str] = None
        if gw_ip:
            gw_mac = await asyncio.to_thread(self._lookup_arp_mac, gw_ip)
        return gw_ip, gw_mac

    @staticmethod
    def _resolve_os_default_gateway() -> Optional[str]:
        import subprocess, sys

        try:
            kwargs: Dict[str, Any] = {}
            if sys.platform == "win32":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                kwargs = {"startupinfo": si, "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
                proc = subprocess.run(
                    ["route", "PRINT", "0.0.0.0", "MASK", "0.0.0.0"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=2,
                    **kwargs,
                )
                # Look for line starting with 0.0.0.0  0.0.0.0  <gateway_ip>
                for line in (proc.stdout or "").splitlines():
                    parts = line.split()
                    if len(parts) >= 3 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                        cand = parts[2].strip()
                        if re.match(r"^\d+\.\d+\.\d+\.\d+$", cand) and cand != "0.0.0.0":
                            return cand
            else:
                proc = subprocess.run(
                    ["ip", "route", "show", "default"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                m = re.search(r"default\s+via\s+(\S+)", proc.stdout or "")
                if m:
                    return m.group(1)
        except Exception:
            pass
        return None

    @staticmethod
    def _lookup_arp_mac(ip_addr: str) -> Optional[str]:
        import subprocess, sys

        try:
            kwargs: Dict[str, Any] = {}
            if sys.platform == "win32":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                kwargs = {"startupinfo": si, "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
            proc = subprocess.run(
                ["arp", "-a", ip_addr],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=2,
                **kwargs,
            )
            m = re.search(
                r"([0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2})",
                proc.stdout or "",
            )
            if m:
                return m.group(1).replace("-", ":").lower()
        except Exception:
            pass
        return None

    async def discover(
        self,
        *,
        override_gateway_url: Optional[str] = None,
        candidate_ports: Tuple[int, ...] = (443, 80, 8443, 8080),
        probe_extended_interfaces: bool = True,
    ) -> RouterDiscoveryResult:
        """Passively probe detected gateway HTTP/HTTPS, UPnP IGD, and authorized local interfaces."""
        gw_ip, gw_mac = await self._resolve_gateway_ip_and_mac()
        oui_vendor = _OUI_SCANNER.lookup_vendor(gw_mac) if gw_mac else None
        if oui_vendor in (None, "Unknown") and gw_mac:
            oui_vendor = RouterFingerprintService.lookup_oui_vendor(gw_mac)
        if oui_vendor == "Unknown":
            oui_vendor = None

        urls_to_try: List[str] = []
        reachable_ports: List[int] = []
        target_host = gw_ip

        if override_gateway_url:
            scheme, host, port, _ = validate_local_router_url(
                override_gateway_url, allow_loopback=self._allow_loopback
            )
            gw_ip = gw_ip or host
            target_host = host
            urls_to_try.append(override_gateway_url.rstrip("/"))
            if await asyncio.to_thread(_tcp_port_open, host, port):
                reachable_ports.append(port)
        elif gw_ip:
            port_checks = await asyncio.gather(
                *[asyncio.to_thread(_tcp_port_open, gw_ip, port) for port in candidate_ports]
            )
            for port, is_open in zip(candidate_ports, port_checks):
                if is_open:
                    reachable_ports.append(port)
                    scheme = "https" if port in (443, 8443) else "http"
                    default_port = 443 if scheme == "https" else 80
                    url = (
                        f"{scheme}://{gw_ip}"
                        if port == default_port
                        else f"{scheme}://{gw_ip}:{port}"
                    )
                    urls_to_try.append(url)

        best_url: Optional[str] = urls_to_try[0] if urls_to_try else None
        best_tls_trusted: Optional[bool] = None
        best_headers: Dict[str, str] = {}
        best_body = ""
        management_urls: List[str] = []

        for url in urls_to_try:
            ok, tls_ok, hdrs, body = await asyncio.to_thread(
                _passive_http_probe, url, allow_loopback=self._allow_loopback
            )
            if ok:
                management_urls.append(url)
                if not best_headers and not best_body:
                    best_url = url
                    best_tls_trusted = tls_ok
                    best_headers = hdrs
                    best_body = body

        upnp_info: Optional[Dict[str, str]] = None
        if gw_ip and not override_gateway_url:
            upnp_info = await asyncio.to_thread(self._ssdp_fn, gw_ip)

        fp_service = RouterFingerprintService()
        iface_probes = []
        snmp_sys_descr: Optional[str] = None
        if target_host and probe_extended_interfaces and not override_gateway_url:
            iface_probes = await fp_service.probe_management_interfaces(
                target_host, timeout_s=0.35
            )
            for p in iface_probes:
                if p.reachable and p.port not in reachable_ports and p.transport == "tcp":
                    reachable_ports.append(p.port)
                if p.interface_type == "snmp" and p.reachable:
                    snmp_sys_descr = p.details
        elif best_url:
            parsed_u = urllib.parse.urlparse(best_url)
            u_port = parsed_u.port or (443 if parsed_u.scheme == "https" else 80)
            from app.wifi.router.fingerprint import InterfaceProbe

            iface_probes.append(
                InterfaceProbe(
                    interface_type="https_web" if parsed_u.scheme == "https" else "http_web",
                    port=u_port,
                    transport="tcp",
                    reachable=bool(management_urls),
                    details=best_url,
                )
            )
            if fp_service.is_web_dom_available():
                iface_probes.append(
                    InterfaceProbe(
                        interface_type="web_dom",
                        port=u_port,
                        transport="browser",
                        reachable=bool(management_urls),
                        details="PySide6 QtWebEngine DOM inspector available",
                    )
                )

        (
            raw_adapter_id,
            vendor,
            model,
            hw_rev,
            fw_ver,
            isp_brand,
            confidence,
            evidence,
        ) = RouterFingerprintService.classify_http_evidence(
            headers=best_headers,
            body=best_body,
            oui_vendor=oui_vendor,
            upnp_manufacturer=upnp_info.get("manufacturer") if upnp_info else None,
            upnp_model=upnp_info.get("modelName") if upnp_info else None,
            snmp_sys_descr=snmp_sys_descr,
        )
        adapter_id = raw_adapter_id
        if self._registry is not None and self._registry.get_adapter(adapter_id) is None:
            if adapter_id.startswith("isp_generic:") and self._registry.get_adapter("isp_generic") is not None:
                pass
            else:
                adapter_id = "generic_probe"

        caps = RouterCapabilities(
            adapter_id=adapter_id,
            vendor_family=vendor or "Generic",
            hardware_verified=False,
            supports_session_auth=(adapter_id != "generic_probe"),
            supports_web_dom_inspection=fp_service.is_web_dom_available(),
            supports_snmp_read=any(p.interface_type == "snmp" and p.read_supported for p in iface_probes),
            supports_tr069_or_usp=any(p.interface_type == "tr069_cwmp" and p.reachable for p in iface_probes),
            limitations=[
                "Adapter capability matrix has not been verified against physical credentials yet."
            ],
        )
        if self._registry is not None:
            adapter = self._registry.get_adapter(adapter_id)
            if adapter is not None:
                caps = adapter.capabilities().model_copy(
                    update={
                        "supports_web_dom_inspection": fp_service.is_web_dom_available(),
                        "supports_snmp_read": any(p.interface_type == "snmp" and p.read_supported for p in iface_probes),
                        "supports_tr069_or_usp": any(p.interface_type == "tr069_cwmp" and p.reachable for p in iface_probes),
                    }
                )

        lan_subnet: Optional[str] = None
        if gw_ip:
            try:
                ip_obj = __import__("ipaddress").ip_address(gw_ip)
                if ip_obj.version == 4:
                    lan_subnet = f"{__import__('ipaddress').ip_network(f'{gw_ip}/24', strict=False)}"
            except Exception:
                lan_subnet = None

        is_https = bool(best_url and best_url.startswith("https://"))
        sec_warn = (
            evaluate_transport_security_warning(best_url, best_tls_trusted)
            if best_url
            else None
        )

        notes: List[str] = []
        if not gw_ip:
            notes.append("No default gateway IP detected on the active network interface.")
        elif not management_urls:
            notes.append(
                f"Gateway {gw_ip} detected, but web portal did not respond on standard HTTP/HTTPS ports."
            )
        else:
            brand_txt = f" | ISP: {isp_brand}" if isp_brand else ""
            notes.append(
                f"Passively discovered {vendor or 'Unknown'} {model or 'Router'}{brand_txt} at {best_url} (zero credentials guessed)."
            )

        wan_conn_type: Optional[str] = None
        if upnp_info:
            wan_conn_type = (
                upnp_info.get("WANAccessType")
                or upnp_info.get("NewWANAccessType")
                or upnp_info.get("ConnectionType")
            )
        if not wan_conn_type and best_body:
            b_low = best_body.lower()
            if "pppoe" in b_low:
                wan_conn_type = "PPPoE"
            elif "vdsl" in b_low:
                wan_conn_type = "VDSL"
            elif "adsl" in b_low:
                wan_conn_type = "ADSL"
            elif "gpon" in b_low or "ftth" in b_low:
                wan_conn_type = "Fiber / GPON"

        supported_bands: List[str] = []
        passive_blob = f"{best_body} {snmp_sys_descr or ''}".lower()
        if any(m in passive_blob for m in ("2.4g", "2.4 ghz", "2400mhz", "802.11n", "wl0")):
            supported_bands.append("2.4 GHz")
        if any(m in passive_blob for m in ("5g", "5 ghz", "5ghz", "5000mhz", "802.11ac", "wl1")):
            supported_bands.append("5 GHz")
        if any(m in passive_blob for m in ("6g", "6 ghz", "6ghz", "6000mhz", "wifi 6e", "802.11be")):
            supported_bands.append("6 GHz")

        upnp_ext_ip = upnp_info.get("NewExternalIPAddress") if upnp_info else None
        upnp_avail = bool(upnp_info) or any(
            p.interface_type == "upnp_igd" and p.reachable for p in iface_probes
        )

        return RouterDiscoveryResult(
            discovered_at=utc_now(),
            gateway_ip=gw_ip,
            gateway_mac=gw_mac,
            gateway_vendor_oui=oui_vendor,
            management_urls=management_urls,
            reachable_ports=sorted(set(reachable_ports)),
            preferred_url=best_url,
            is_https=is_https,
            tls_trusted=best_tls_trusted,
            security_warning=sec_warn,
            detected_vendor=vendor,
            hardware_vendor=vendor,
            detected_model=model,
            hardware_revision=hw_rev,
            firmware_version=fw_ver,
            isp_brand=isp_brand,
            wan_connection_type=wan_conn_type,
            lan_subnet=lan_subnet,
            supported_bands=supported_bands,
            adapter_id=adapter_id,
            detection_confidence=confidence,
            detection_evidence=evidence,
            available_interfaces=[
                {
                    "interface_type": p.interface_type,
                    "port": p.port,
                    "transport": p.transport,
                    "reachable": p.reachable,
                    "read_supported": p.read_supported,
                    "write_supported": p.write_supported,
                    "details": p.details,
                }
                for p in iface_probes
            ],
            snmp_sys_descr=snmp_sys_descr,
            web_dom_available=fp_service.is_web_dom_available(),
            upnp_igd_available=upnp_avail,
            upnp_device_friendly_name=upnp_info.get("friendlyName") if upnp_info else None,
            upnp_external_ip=upnp_ext_ip,
            capabilities=caps,
            notes=notes,
        )
