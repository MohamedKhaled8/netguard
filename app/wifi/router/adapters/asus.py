"""ASUS Asuswrt local HTTP adapter."""

from __future__ import annotations

import base64
import json
import re
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


class AsusRouterAdapter(IRouterAdapter):
    """Modular adapter for ASUS routers running Asuswrt / Merlin."""

    adapter_id = "asus"
    vendor_family = "ASUS"

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
            supports_per_device_bandwidth=True,
            supports_sqm_or_qos_read=True,
            supports_sqm_or_qos_write=False,
            supports_dns_config_read=True,
            supports_dns_config_write=False,
            supports_backup_export=False,
            supports_wan_read=True,
            supports_lan_dhcp_read=True,
            supports_logs_read=True,
            limitations=[
                "ASUS adapter has not been verified against physical Asuswrt hardware in this run.",
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
        client = RouterHttpClient(base_url, verify_tls=verify_tls, allow_loopback=self._allow_loopback)
        self._client = client
        self._base_url = base_url
        self._authenticated = False
        try:
            token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
            resp = client.post_form(
                "/login.cgi",
                {"login_authorization": token, "group_id": "", "action_mode": ""},
                headers={"Referer": f"{base_url}/Main_Login.asp"},
            )
            body_low = resp.text.lower()
            loc = (resp.headers.get("location") or "").lower()
            has_login_form = (
                'type="password"' in body_low
                or "type='password'" in body_low
                or "main_login.asp" in body_low
                or "error_status" in body_low
                or "auth required" in body_low
            )
            authenticated_signal = (
                "asus_token" in client.cookies
                or "index.asp" in loc
                or "index.asp" in body_low
                or "main_index" in body_low
                or "wan_proto" in body_low
                or "wl0_" in body_low
            )
            ok = resp.status in (200, 302, 303) and authenticated_signal and not has_login_form
            if ok:
                self._authenticated = True
                return RouterAuthResult(
                    authenticated=True,
                    adapter_id=self.adapter_id,
                    base_url=base_url,
                    used_https=base_url.startswith("https://"),
                    message="Authenticated with Asuswrt login.cgi.",
                )
            return RouterAuthResult(
                authenticated=False,
                adapter_id=self.adapter_id,
                base_url=base_url,
                used_https=base_url.startswith("https://"),
                message=f"ASUS authentication rejected (HTTP {resp.status}).",
            )
        except Exception as exc:
            return RouterAuthResult(
                authenticated=False,
                adapter_id=self.adapter_id,
                base_url=base_url,
                used_https=base_url.startswith("https://"),
                message=f"ASUS authentication failed: {exc}",
            )

    def _app_get(self, hook: str) -> Dict[str, Any]:
        if not self._client:
            return {}
        resp = self._client.get(f"/appGet.cgi?hook={hook}")
        return resp.json_data if isinstance(resp.json_data, dict) else {}

    def read_config(self) -> RouterConfigurationSnapshot:
        if not self._authenticated or self._client is None:
            raise RuntimeError("Router session is not authenticated.")
        nv = self._app_get(
            "nvram_get(productid);nvram_get(firmver);nvram_get(wl0_ssid);nvram_get(wl0_chanspec);"
            "nvram_get(wl1_ssid);nvram_get(wl1_chanspec);nvram_get(wan0_ipaddr);nvram_get(wan0_dns);"
            "nvram_get(qos_enable);nvram_get(qos_type);nvram_get(dhcp_enable_x);"
        )
        radios: Dict[str, RouterWifiRadioConfig] = {}
        if nv.get("wl0_ssid") or nv.get("wl0_chanspec"):
            ch = str(nv.get("wl0_chanspec") or "")
            radios["2.4 GHz"] = RouterWifiRadioConfig(
                band="2.4 GHz",
                enabled=True,
                ssid=nv.get("wl0_ssid"),
                channel=re.sub(r"[^0-9]", "", ch) or ch or None,
            )
        if nv.get("wl1_ssid") or nv.get("wl1_chanspec"):
            ch5 = str(nv.get("wl1_chanspec") or "")
            radios["5 GHz"] = RouterWifiRadioConfig(
                band="5 GHz",
                enabled=True,
                ssid=nv.get("wl1_ssid"),
                channel=re.sub(r"/.*$", "", ch5) or ch5 or None,
                channel_width="80" if "/80" in ch5 else ("40" if "/40" in ch5 else None),
            )
        dns_list = [x for x in str(nv.get("wan0_dns") or "").split() if x]
        return RouterConfigurationSnapshot(
            captured_at=utc_now(),
            adapter_id=self.adapter_id,
            hardware_verified=self.hardware_verified,
            vendor="ASUS",
            model=nv.get("productid") or "ASUS Router",
            firmware_version=nv.get("firmver"),
            wan_ip=nv.get("wan0_ipaddr"),
            dns_servers=dns_list,
            dhcp_enabled=(str(nv.get("dhcp_enable_x")) == "1") if "dhcp_enable_x" in nv else None,
            radios=radios,
            qos_enabled=(str(nv.get("qos_enable")) == "1") if "qos_enable" in nv else None,
            qos_mode=str(nv.get("qos_type") or "") or None,
            raw_backup_blob=json.dumps(nv, ensure_ascii=False),
        )

    def get_connected_devices(self) -> List[ConnectedDeviceRecord]:
        if not self._authenticated or self._client is None:
            return []
        data = self._app_get("get_clientlist()")
        clients = data.get("get_clientlist") if isinstance(data.get("get_clientlist"), dict) else {}
        out: List[ConnectedDeviceRecord] = []
        for mac, info in clients.items():
            if not isinstance(info, dict) or ":" not in mac:
                continue
            wl = str(info.get("isWL") or "0")
            ctype = "wifi_5" if wl == "2" else ("wifi_24" if wl == "1" else "ethernet")
            out.append(
                ConnectedDeviceRecord(
                    ip_address=info.get("ip"),
                    mac_address=mac.lower(),
                    hostname=info.get("name") or info.get("nickName"),
                    vendor=info.get("vendor"),
                    connection_type=ctype,
                    connection_status="connected" if str(info.get("isOnline")) == "1" else "stale",
                    rssi_dbm=int(info["rssi"]) if str(info.get("rssi", "")).lstrip("-").isdigit() else None,
                    source="router_api",
                    supports_rate_limit=True,
                )
            )
        return out

    def _write_setting_raw(self, proposal: RouterChangeProposal) -> tuple[bool, str]:
        if not self._authenticated or self._client is None:
            return False, "Not authenticated."
        unit = "1" if proposal.band == "5 GHz" else "0"
        payload: Dict[str, Any] = {"action_mode": "apply", "rc_service": "restart_wireless"}
        if proposal.target_field == "channel":
            payload[f"wl{unit}_channel"] = proposal.proposed_value
        elif proposal.target_field == "channel_width":
            payload[f"wl{unit}_bw"] = proposal.proposed_value
        elif proposal.target_field == "device_rate_limit" and proposal.target_mac:
            payload["qos_bw_rulelist"] = f"{proposal.target_mac}>{proposal.proposed_value}"
        else:
            return False, f"Unsupported ASUS write field: {proposal.target_field}"
        resp = self._client.post_form("/applyapp.cgi", payload)
        return resp.status == 200, f"HTTP {resp.status}"

    def _extract_target_value(self, snapshot: RouterConfigurationSnapshot, proposal: RouterChangeProposal) -> Optional[str]:
        if proposal.band and proposal.band in snapshot.radios:
            r = snapshot.radios[proposal.band]
            if proposal.target_field == "channel":
                return r.channel
            if proposal.target_field == "channel_width":
                return r.channel_width
        return None
