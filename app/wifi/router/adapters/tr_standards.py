"""Standards-based local router inspection (UPnP IGD / TR-064 / TR-181 / TR-069 / USP awareness).

Never bypasses authentication or attempts exploit/credentialed CWMP/USP access without authorization.
"""

from __future__ import annotations

import http.client
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.wifi.router.credentials import validate_local_router_url


@dataclass
class StandardsInspectionResult:
    upnp_igd_reachable: bool = False
    tr064_reachable: bool = False
    tr069_port_open: bool = False
    usp_port_open: bool = False
    wan_external_ip: Optional[str] = None
    wan_connection_status: Optional[str] = None
    wan_uptime_sec: Optional[int] = None
    wan_down_max_bps: Optional[int] = None
    wan_up_max_bps: Optional[int] = None
    access_type: Optional[str] = None
    services_discovered: List[str] = field(default_factory=list)
    port_mappings_count: Optional[int] = None
    notes: List[str] = field(default_factory=list)


def _soap_post(
    control_url: str,
    service_type: str,
    action: str,
    *,
    allow_loopback: bool = False,
) -> Optional[str]:
    try:
        validate_local_router_url(control_url, allow_loopback=allow_loopback)
    except Exception:
        return None
    parsed = urllib.parse.urlparse(control_url)
    host = parsed.hostname or ""
    port = parsed.port or 80
    path = parsed.path or "/"
    body = (
        '<?xml version="1.0"?>'
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
        's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
        f'<s:Body><u:{action} xmlns:u="{service_type}"></u:{action}></s:Body>'
        "</s:Envelope>"
    )
    conn = http.client.HTTPConnection(host, port, timeout=1.3)
    try:
        conn.request(
            "POST",
            path,
            body=body.encode("utf-8"),
            headers={
                "Content-Type": 'text/xml; charset="utf-8"',
                "SOAPAction": f'"{service_type}#{action}"',
            },
        )
        resp = conn.getresponse()
        raw = resp.read(32768).decode("utf-8", errors="replace")
        return raw if resp.status == 200 else None
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _xml_text(xml_body: Optional[str], tag_name: str) -> Optional[str]:
    if not xml_body:
        return None
    try:
        root = ET.fromstring(xml_body)
        for el in root.iter():
            local = el.tag.split("}", 1)[-1]
            if local == tag_name and el.text:
                return el.text.strip()
    except Exception:
        pass
    return None


class TrStandardsInspector:
    """Inspects UPnP IGD / TR-064 device descriptions and records TR-069/USP/TR-181 capability status."""

    def inspect_upnp_description(
        self,
        location_url: Optional[str],
        *,
        allow_loopback: bool = False,
    ) -> StandardsInspectionResult:
        res = StandardsInspectionResult()
        if not location_url:
            return res
        try:
            validate_local_router_url(location_url, allow_loopback=allow_loopback)
        except Exception:
            return res

        parsed = urllib.parse.urlparse(location_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        conn = http.client.HTTPConnection(parsed.hostname or "", parsed.port or 80, timeout=1.3)
        try:
            conn.request("GET", parsed.path + (f"?{parsed.query}" if parsed.query else ""))
            resp = conn.getresponse()
            xml_bytes = resp.read(65536)
        except Exception:
            return res
        finally:
            try:
                conn.close()
            except Exception:
                pass

        try:
            root = ET.fromstring(xml_bytes)
        except Exception:
            return res

        res.upnp_igd_reachable = True
        services: Dict[str, str] = {}
        for svc in root.iter():
            if svc.tag.split("}", 1)[-1] != "service":
                continue
            st_el = None
            ctrl_el = None
            for child in svc:
                cname = child.tag.split("}", 1)[-1]
                if cname == "serviceType" and child.text:
                    st_el = child.text.strip()
                elif cname == "controlURL" and child.text:
                    ctrl_el = child.text.strip()
            if st_el and ctrl_el:
                full_ctrl = ctrl_el if ctrl_el.startswith("http") else f"{base}/{ctrl_el.lstrip('/')}"
                services[st_el] = full_ctrl
                res.services_discovered.append(st_el)
                if "dslforum-org" in st_el.lower():
                    res.tr064_reachable = True

        # Query WANIPConnection / WANPPPConnection safely if listed
        for st, ctrl in services.items():
            if "WANIPConnection" in st or "WANPPPConnection" in st:
                ext_xml = _soap_post(ctrl, st, "GetExternalIPAddress", allow_loopback=allow_loopback)
                res.wan_external_ip = res.wan_external_ip or _xml_text(ext_xml, "NewExternalIPAddress")
                st_xml = _soap_post(ctrl, st, "GetStatusInfo", allow_loopback=allow_loopback)
                res.wan_connection_status = res.wan_connection_status or _xml_text(st_xml, "NewConnectionStatus")
                up_txt = _xml_text(st_xml, "NewUptime")
                if up_txt and up_txt.isdigit():
                    res.wan_uptime_sec = int(up_txt)
            elif "WANCommonInterfaceConfig" in st:
                prop_xml = _soap_post(ctrl, st, "GetCommonLinkProperties", allow_loopback=allow_loopback)
                res.access_type = res.access_type or _xml_text(prop_xml, "NewWANAccessType")
                dn = _xml_text(prop_xml, "NewLayer1DownstreamMaxBitRate")
                up = _xml_text(prop_xml, "NewLayer1UpstreamMaxBitRate")
                if dn and dn.isdigit():
                    res.wan_down_max_bps = int(dn)
                if up and up.isdigit():
                    res.wan_up_max_bps = int(up)

        return res
