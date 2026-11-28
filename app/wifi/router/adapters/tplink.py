"""TP-Link router adapter supporting config read and guarded QoS/Wi-Fi writes."""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Optional

from app.wifi.models import (
    ConnectedDeviceRecord,
    RouterAuthResult,
    RouterCapabilities,
    RouterChangeProposal,
    RouterConfigurationSnapshot,
    RouterWifiRadioConfig,
    utc_now,
)
from app.wifi.router.adapters.base import IRouterAdapter, RouterHttpClient


class TpLinkRouterAdapter(IRouterAdapter):
    """Modular adapter for TP-Link Archer/Router web JSON stok APIs."""

    adapter_id = "tplink"
    vendor_family = "TP-Link"
    hardware_verified = False

    def __init__(self, *, allow_loopback: bool = False) -> None:
        super().__init__(allow_loopback=allow_loopback)
        self._stok: str = ""

    def capabilities(self) -> RouterCapabilities:
        return RouterCapabilities(
            adapter_id=self.adapter_id,
            vendor_family=self.vendor_family,
            hardware_verified=self.hardware_verified,
            supports_session_auth=True,
            supports_wifi_read=True,
            supports_wifi_write=True,
            supports_channel_write=True,
            supports_width_write=True,
            supports_tx_power_write=True,
            supports_connected_devices_read=True,
            supports_per_device_bandwidth=True,
            supports_sqm_or_qos_read=True,
            supports_sqm_or_qos_write=True,
            supports_dns_config_read=True,
            supports_dns_config_write=True,
            supports_backup_export=True,
            limitations=[
                "TP-Link firmware APIs vary across TD-W / Archer / Deco lines and require physical verification with admin credentials.",
                "Per-device QoS/bandwidth rules require firmware Bandwidth Control/QoS support.",
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
        client = RouterHttpClient(
            base_url, verify_tls=verify_tls, allow_loopback=self._allow_loopback
        )
        self._client = client
        self._base_url = base_url
        self._authenticated = False

        try:
            digest = hashlib.md5(password.encode("utf-8")).hexdigest()
            resp = client.post_form(
                "/cgi-bin/luci/;stok=/login?form=login",
                {"operation": "login", "username": username, "password": digest},
            )
            j = resp.json_data if isinstance(resp.json_data, dict) else {}
            data = j.get("data") if isinstance(j.get("data"), dict) else {}
            stok = str(data.get("stok") or j.get("stok") or "")
            if resp.status == 200 and stok and j.get("success") is not False:
                self._stok = stok
                self._authenticated = True
                return RouterAuthResult(
                    authenticated=True,
                    adapter_id=self.adapter_id,
                    base_url=base_url,
                    used_https=base_url.startswith("https://"),
                    message="Authenticated with TP-Link stok session.",
                )
            return RouterAuthResult(
                authenticated=False,
                adapter_id=self.adapter_id,
                base_url=base_url,
                used_https=base_url.startswith("https://"),
                message=f"TP-Link authentication failed (HTTP {resp.status}).",
            )
        except Exception as exc:
            return RouterAuthResult(
                authenticated=False,
                adapter_id=self.adapter_id,
                base_url=base_url,
                used_https=base_url.startswith("https://"),
                message=f"TP-Link connection error: {exc}",
            )

    def _api_path(self, endpoint: str) -> str:
        return f"/cgi-bin/luci/;stok={self._stok}{endpoint}"

    def read_config(self) -> RouterConfigurationSnapshot:
        if not self._authenticated or self._client is None:
            raise RuntimeError("Router session is not authenticated.")
        resp = self._client.get(self._api_path("/admin/wireless?form=wireless_summary"))
        j = resp.json_data if isinstance(resp.json_data, dict) else {}
        radios: Dict[str, RouterWifiRadioConfig] = {}
        for band_key in ("2.4 GHz", "5 GHz"):
            obj = j.get(band_key)
            if isinstance(obj, dict):
                radios[band_key] = RouterWifiRadioConfig(
                    band=band_key,
                    enabled=obj.get("enabled"),
                    ssid=obj.get("ssid"),
                    channel=str(obj.get("channel")) if obj.get("channel") is not None else None,
                    channel_width=str(obj.get("channel_width")) if obj.get("channel_width") is not None else None,
                    tx_power=str(obj.get("tx_power")) if obj.get("tx_power") is not None else None,
                    security_mode=obj.get("security_mode"),
                )
        return RouterConfigurationSnapshot(
            captured_at=utc_now(),
            adapter_id=self.adapter_id,
            hardware_verified=self.hardware_verified,
            vendor="TP-Link",
            model=j.get("model") or "TP-Link Router",
            firmware_version=j.get("firmware_version"),
            wan_status=j.get("wan_status"),
            wan_ip=j.get("wan_ip"),
            dns_servers=list(j.get("dns_servers", [])),
            radios=radios,
            qos_enabled=j.get("qos_enabled"),
            qos_mode=j.get("qos_mode"),
            sqm_available=bool(j.get("sqm_available", False)),
            sqm_enabled=j.get("sqm_enabled"),
            raw_backup_blob=json.dumps(j, ensure_ascii=False),
        )

    def get_connected_devices(self) -> List[ConnectedDeviceRecord]:
        if not self._authenticated or self._client is None:
            return []
        resp = self._client.get(self._api_path("/admin/dhcps?form=client"))
        j = resp.json_data if isinstance(resp.json_data, dict) else {}
        out: List[ConnectedDeviceRecord] = []
        for dev in j.get("clients", []):
            if isinstance(dev, dict):
                out.append(
                    ConnectedDeviceRecord(
                        ip_address=dev.get("ip"),
                        mac_address=dev.get("mac"),
                        hostname=dev.get("hostname"),
                        connection_type=dev.get("connection_type", "unknown"),
                        rx_limit_kbps=dev.get("rx_limit_kbps"),
                        tx_limit_kbps=dev.get("tx_limit_kbps"),
                        source="router_api",
                        supports_rate_limit=True,
                    )
                )
        return out

    def _write_setting_raw(self, proposal: RouterChangeProposal) -> tuple[bool, str]:
        if not self._authenticated or self._client is None:
            return False, "Not authenticated."
        resp = self._client.post_json(
            self._api_path("/admin/wireless?form=write"),
            {
                "category": proposal.category,
                "band": proposal.band,
                "field": proposal.target_field,
                "value": proposal.proposed_value,
            },
        )
        j = resp.json_data if isinstance(resp.json_data, dict) else {}
        ok = resp.status == 200 and j.get("success") is True
        return ok, str(j.get("err_msg") or f"HTTP {resp.status}")

    def _extract_target_value(
        self, snapshot: RouterConfigurationSnapshot, proposal: RouterChangeProposal
    ) -> Optional[str]:
        if proposal.band and proposal.band in snapshot.radios:
            r = snapshot.radios[proposal.band]
            if proposal.target_field == "channel":
                return r.channel
            if proposal.target_field == "channel_width":
                return r.channel_width
            if proposal.target_field == "tx_power":
                return r.tx_power
        if proposal.target_field == "qos_enabled":
            return str(snapshot.qos_enabled) if snapshot.qos_enabled is not None else None
        return None
