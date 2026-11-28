"""Generic read-only / UPnP IGD router adapter when vendor firmware API is unknown or unsupported."""

from __future__ import annotations

import http.client
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

from app.wifi.models import (
    ConnectedDeviceRecord,
    RouterAuthResult,
    RouterCapabilities,
    RouterChangeProposal,
    RouterConfigurationSnapshot,
    utc_now,
)
from app.wifi.router.adapters.base import IRouterAdapter, RouterHttpClient


class GenericProbeAdapter(IRouterAdapter):
    """Conservative fallback adapter: UPnP read-only inspection without fabricated writes."""

    adapter_id = "generic_probe"
    vendor_family = "Generic / UPnP IGD"
    hardware_verified = False

    def __init__(self, *, allow_loopback: bool = False) -> None:
        super().__init__(allow_loopback=allow_loopback)
        self._upnp_control_url: Optional[str] = None
        self._model_name: Optional[str] = None
        self._vendor_name: Optional[str] = None

    def configure_upnp_hint(
        self,
        *,
        control_url: Optional[str] = None,
        vendor_name: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        self._upnp_control_url = control_url
        self._vendor_name = vendor_name
        self._model_name = model_name

    def capabilities(self) -> RouterCapabilities:
        return RouterCapabilities(
            adapter_id=self.adapter_id,
            vendor_family=self._vendor_name or self.vendor_family,
            hardware_verified=False,
            supports_session_auth=False,
            supports_wifi_read=False,
            supports_wifi_write=False,
            supports_channel_write=False,
            supports_width_write=False,
            supports_tx_power_write=False,
            supports_connected_devices_read=False,
            supports_per_device_bandwidth=False,
            supports_sqm_or_qos_read=False,
            supports_sqm_or_qos_write=False,
            supports_dns_config_read=False,
            supports_dns_config_write=False,
            supports_backup_export=False,
            limitations=[
                "Generic probe adapter cannot log into proprietary web admin portals reliably.",
                "Use NetGuard recommendations to apply router Wi-Fi/QoS changes safely via browser.",
            ],
        )

    def authenticate(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        verify_tls: bool = True,
    ) -> RouterAuthResult:
        self._client = RouterHttpClient(
            base_url, verify_tls=verify_tls, allow_loopback=self._allow_loopback
        )
        self._base_url = base_url
        self._authenticated = False
        return RouterAuthResult(
            authenticated=False,
            adapter_id=self.adapter_id,
            base_url=base_url,
            used_https=base_url.startswith("https://"),
            message=(
                "No vendor-specific adapter matched this router model. "
                "Read-only discovery succeeded, but web admin login requires a vendor adapter."
            ),
        )

    def _soap_query(self, action: str) -> Optional[str]:
        if not self._upnp_control_url:
            return None
        parsed = urllib.parse.urlparse(self._upnp_control_url)
        host = parsed.hostname or ""
        port = parsed.port or 80
        path = parsed.path or "/"
        envelope = (
            '<?xml version="1.0"?>'
            '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
            's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            f'<s:Body><u:{action} xmlns:u="urn:schemas-upnp-org:service:WANIPConnection:1"></u:{action}></s:Body>'
            "</s:Envelope>"
        ).encode("utf-8")
        try:
            conn = http.client.HTTPConnection(host, port, timeout=1.5)
            conn.request(
                "POST",
                path,
                body=envelope,
                headers={
                    "Content-Type": 'text/xml; charset="utf-8"',
                    "SOAPAction": f'"urn:schemas-upnp-org:service:WANIPConnection:1#{action}"',
                },
            )
            resp = conn.getresponse()
            raw = resp.read(16384).decode("utf-8", errors="replace")
            conn.close()
            if resp.status == 200:
                return raw
        except Exception:
            pass
        return None

    def read_config(self) -> RouterConfigurationSnapshot:
        wan_ip: Optional[str] = None
        wan_status: Optional[str] = None
        ext_xml = self._soap_query("GetExternalIPAddress")
        if ext_xml:
            try:
                el = ET.fromstring(ext_xml).find(".//NewExternalIPAddress")
                if el is not None and el.text:
                    wan_ip = el.text.strip()
            except Exception:
                pass
        st_xml = self._soap_query("GetStatusInfo")
        if st_xml:
            try:
                el = ET.fromstring(st_xml).find(".//NewConnectionStatus")
                if el is not None and el.text:
                    wan_status = el.text.strip()
            except Exception:
                pass

        return RouterConfigurationSnapshot(
            captured_at=utc_now(),
            adapter_id=self.adapter_id,
            hardware_verified=False,
            vendor=self._vendor_name,
            model=self._model_name,
            wan_ip=wan_ip,
            wan_status=wan_status or ("Unknown" if not self._upnp_control_url else "Reported"),
            upnp_enabled=bool(self._upnp_control_url),
            notes=[
                "Generic probe provides read-only gateway discovery; router Wi-Fi channel/width settings were not read directly."
            ],
        )

    def get_connected_devices(self) -> List[ConnectedDeviceRecord]:
        return []

    def _write_setting_raw(self, proposal: RouterChangeProposal) -> tuple[bool, str]:
        return False, "Generic probe adapter is strictly read-only."

    def _extract_target_value(
        self, snapshot: RouterConfigurationSnapshot, proposal: RouterChangeProposal
    ) -> Optional[str]:
        return None
