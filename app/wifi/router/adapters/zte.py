"""ZTE ZXHN router web API adapter (modular, backup/readback guarded, hardware_verified=False)."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

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


class ZteRouterAdapter(IRouterAdapter):
    """Adapter for ZTE ZXHN home gateway HTTP/JSON/Lua portals (requires live credential verification)."""

    adapter_id = "zte"
    vendor_family = "ZTE ZXHN"
    hardware_verified = False

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
            supports_tx_power_write=False,
            supports_connected_devices_read=True,
            supports_per_device_bandwidth=False,
            supports_sqm_or_qos_read=True,
            supports_sqm_or_qos_write=False,
            supports_dns_config_read=True,
            supports_dns_config_write=False,
            supports_backup_export=True,
            limitations=[
                "Firmware variations across ZTE ZXHN models (e.g. H168N/H188A/F670L) have not been physically verified with admin credentials in this environment.",
                "Automatic writes verify readback strictly and roll back if the firmware endpoint schema differs.",
                "Per-device bandwidth rate limiting is not exposed uniformly on standard ISP ZTE firmware.",
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
            # Query ZTE login token endpoint (JSON or token probe)
            tok_resp = client.get("/?_type=loginData&_tag=login_entry")
            sess_token = ""
            if isinstance(tok_resp.json_data, dict):
                sess_token = str(
                    tok_resp.json_data.get("sess_token")
                    or tok_resp.json_data.get("token")
                    or ""
                )
            pw_hash = (
                hashlib.sha256((password + sess_token).encode("utf-8")).hexdigest()
                if sess_token
                else password
            )
            login_resp = client.post_form(
                "/?_type=loginData&_tag=login_entry",
                {
                    "action": "login",
                    "Username": username,
                    "Password": pw_hash,
                    "_sessionTOKEN": sess_token,
                },
            )
            j = login_resp.json_data if isinstance(login_resp.json_data, dict) else {}
            ok = bool(
                login_resp.status == 200
                and (j.get("login_need_refresh") or j.get("authenticated") or j.get("result") == "ok")
                and not j.get("loginErrMsg")
            )
            if ok:
                self._authenticated = True
                return RouterAuthResult(
                    authenticated=True,
                    adapter_id=self.adapter_id,
                    base_url=base_url,
                    used_https=base_url.startswith("https://"),
                    message="Authenticated with ZTE session endpoint (software adapter unverified on physical hardware).",
                )
            err = str(j.get("loginErrMsg") or f"HTTP {login_resp.status}")
            return RouterAuthResult(
                authenticated=False,
                adapter_id=self.adapter_id,
                base_url=base_url,
                used_https=base_url.startswith("https://"),
                message=f"ZTE login rejected: {err}",
            )
        except Exception as exc:
            return RouterAuthResult(
                authenticated=False,
                adapter_id=self.adapter_id,
                base_url=base_url,
                used_https=base_url.startswith("https://"),
                message=f"ZTE login connection failed: {exc}",
            )

    def read_config(self) -> RouterConfigurationSnapshot:
        if not self._authenticated or self._client is None:
            raise RuntimeError("Router session is not authenticated.")

        wifi_resp = self._client.get("/?_type=menuData&_tag=wlan_basic_ad")
        sys_resp = self._client.get("/?_type=menuData&_tag=status_info")
        w_json = wifi_resp.json_data if isinstance(wifi_resp.json_data, dict) else {}
        s_json = sys_resp.json_data if isinstance(sys_resp.json_data, dict) else {}

        radios: Dict[str, RouterWifiRadioConfig] = {}
        for band_key, api_key in (("2.4 GHz", "radio_24"), ("5 GHz", "radio_5")):
            r_obj = w_json.get(api_key)
            if isinstance(r_obj, dict):
                radios[band_key] = RouterWifiRadioConfig(
                    band=band_key,
                    enabled=r_obj.get("enabled"),
                    ssid=r_obj.get("ssid"),
                    channel=str(r_obj.get("channel")) if r_obj.get("channel") is not None else None,
                    channel_width=str(r_obj.get("channel_width")) if r_obj.get("channel_width") is not None else None,
                    tx_power=str(r_obj.get("tx_power")) if r_obj.get("tx_power") is not None else None,
                    security_mode=r_obj.get("security_mode"),
                    band_steering_enabled=r_obj.get("band_steering"),
                )

        dns_raw = s_json.get("dns_servers") or []
        if isinstance(dns_raw, str):
            dns_raw = [x.strip() for x in dns_raw.split(",") if x.strip()]

        backup_blob = json.dumps({"wifi": w_json, "system": s_json}, ensure_ascii=False)
        return RouterConfigurationSnapshot(
            captured_at=utc_now(),
            adapter_id=self.adapter_id,
            hardware_verified=self.hardware_verified,
            vendor="ZTE",
            model=s_json.get("model") or "ZTE ZXHN",
            firmware_version=s_json.get("firmware_version"),
            wan_status=s_json.get("wan_status"),
            wan_ip=s_json.get("wan_ip"),
            dns_servers=list(dns_raw),
            dhcp_enabled=s_json.get("dhcp_enabled"),
            radios=radios,
            qos_enabled=s_json.get("qos_enabled"),
            qos_mode=s_json.get("qos_mode"),
            sqm_available=bool(s_json.get("sqm_available", False)),
            sqm_enabled=s_json.get("sqm_enabled"),
            raw_backup_blob=backup_blob,
        )

    def get_connected_devices(self) -> List[ConnectedDeviceRecord]:
        if not self._authenticated or self._client is None:
            return []
        resp = self._client.get("/?_type=menuData&_tag=lan_assoc_devs")
        data = resp.json_data if isinstance(resp.json_data, dict) else {}
        raw_devs = data.get("devices") or []
        out: List[ConnectedDeviceRecord] = []
        for d in raw_devs:
            if not isinstance(d, dict):
                continue
            out.append(
                ConnectedDeviceRecord(
                    ip_address=d.get("ip"),
                    mac_address=d.get("mac"),
                    hostname=d.get("hostname"),
                    connection_type=d.get("connection_type", "unknown"),
                    rssi_dbm=d.get("rssi"),
                    link_rate_mbps=d.get("link_rate_mbps"),
                    source="router_api",
                    supports_rate_limit=False,
                )
            )
        return out

    def _write_setting_raw(self, proposal: RouterChangeProposal) -> tuple[bool, str]:
        if not self._authenticated or self._client is None:
            return False, "Not authenticated."
        resp = self._client.post_json(
            "/?_type=menuData&_tag=wlan_basic_apply",
            {
                "band": proposal.band,
                "field": proposal.target_field,
                "value": proposal.proposed_value,
            },
        )
        j = resp.json_data if isinstance(resp.json_data, dict) else {}
        ok = resp.status == 200 and j.get("result") in ("ok", True, "success")
        return ok, str(j.get("message") or f"HTTP {resp.status}")

    def _extract_target_value(
        self, snapshot: RouterConfigurationSnapshot, proposal: RouterChangeProposal
    ) -> Optional[str]:
        if proposal.band and proposal.band in snapshot.radios:
            radio = snapshot.radios[proposal.band]
            if proposal.target_field == "channel":
                return radio.channel
            if proposal.target_field == "channel_width":
                return radio.channel_width
            if proposal.target_field == "tx_power":
                return radio.tx_power
        if proposal.target_field == "qos_enabled":
            return str(snapshot.qos_enabled) if snapshot.qos_enabled is not None else None
        return None
