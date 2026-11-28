"""Data-driven ISP & additional vendor adapter (Tenda, D-Link, Nokia, Sercomm, Sagemcom, FiberHome, Netgear, OpenWrt).

Combines documented local HTTP/JSON/XML/SOAP endpoints with optional QtWebEngine DOM
inspection so new vendor families can be added cleanly without rewriting core logic.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

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


@dataclass(frozen=True)
class VendorEndpointProfile:
    vendor_name: str
    login_paths: Tuple[str, ...]
    read_paths: Dict[str, str]


VENDOR_PROFILES: Dict[str, VendorEndpointProfile] = {
    "openwrt": VendorEndpointProfile(
        vendor_name="OpenWrt",
        login_paths=("/cgi-bin/luci", "/ubus"),
        read_paths={"device_info": "/cgi-bin/luci/admin/status/overview", "wlan": "/cgi-bin/luci/admin/network/wireless"},
    ),
    "tenda": VendorEndpointProfile(
        vendor_name="Tenda",
        login_paths=("/login/Auth", "/goform/login"),
        read_paths={"wlan": "/goform/getWlanInfo", "wan": "/goform/getWanInfo", "qos": "/goform/getQos"},
    ),
    "dlink": VendorEndpointProfile(
        vendor_name="D-Link",
        login_paths=("/HNAP1/", "/session.cgi"),
        read_paths={"device_info": "/HNAP1/", "wlan": "/getcfg.php?SERVICES=WIFI.PHYINF"},
    ),
    "nokia": VendorEndpointProfile(
        vendor_name="Nokia",
        login_paths=("/login_web_app.cgi", "/login.cgi"),
        read_paths={"device_info": "/overview_status_web_app.cgi", "wlan": "/wlan_status_web_app.cgi"},
    ),
    "sercomm": VendorEndpointProfile(
        vendor_name="Sercomm",
        login_paths=("/login.cgi", "/api/v1/session"),
        read_paths={"device_info": "/api/v1/system", "wlan": "/api/v1/wifi"},
    ),
    "sagemcom": VendorEndpointProfile(
        vendor_name="Sagemcom",
        login_paths=("/API/ws", "/cgi-bin/luci"),
        read_paths={"device_info": "/API/ws", "wlan": "/API/ws/wifi"},
    ),
    "fiberhome": VendorEndpointProfile(
        vendor_name="FiberHome",
        login_paths=("/boaform/formLogin", "/login.cgi"),
        read_paths={"device_info": "/status/device_info.asp", "wlan": "/net/wlan_basic.asp"},
    ),
    "netgear": VendorEndpointProfile(
        vendor_name="Netgear",
        login_paths=("/soap/server_sa/", "/"),
        read_paths={"device_info": "/currentsetting.htm"},
    ),
}


class IspGenericRouterAdapter(IRouterAdapter):
    """Extensible read-first adapter supporting Tenda/D-Link/Nokia/Sercomm/Sagemcom/FiberHome/Netgear/OpenWrt."""

    def __init__(self, *, vendor_key: str = "generic", allow_loopback: bool = False) -> None:
        super().__init__(allow_loopback=allow_loopback)
        self.vendor_key = vendor_key.replace("isp_generic:", "").lower()
        profile = VENDOR_PROFILES.get(self.vendor_key)
        self.adapter_id = f"isp_generic:{self.vendor_key}" if profile else "isp_generic"
        self.vendor_family = profile.vendor_name if profile else "Generic/ISP"
        self._last_root_html: str = ""

    def capabilities(self) -> RouterCapabilities:
        return RouterCapabilities(
            adapter_id=self.adapter_id,
            vendor_family=self.vendor_family,
            hardware_verified=self.hardware_verified,
            supports_session_auth=True,
            supports_wifi_read=True,
            supports_wifi_write=False,
            supports_channel_write=False,
            supports_connected_devices_read=True,
            supports_dns_config_read=True,
            supports_sqm_or_qos_read=True,
            supports_wan_read=True,
            supports_web_dom_inspection=True,
            limitations=[
                f"{self.vendor_family} adapter runs read-first discovery/DOM inspection; write actions stay disabled unless verified per firmware.",
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
        profile = VENDOR_PROFILES.get(self.vendor_key)
        paths = profile.login_paths if profile else ("/login.cgi", "/login")
        try:
            for path in paths:
                resp = client.post_form(
                    path,
                    {"username": username, "user": username, "luci_username": username, "password": password, "luci_password": password},
                )
                if resp.status in (200, 302, 303) and (
                    client.cookies or '"result":"ok"' in resp.text.replace(" ", "").lower() or '"error":0' in resp.text.replace(" ", "").lower()
                ):
                    self._authenticated = True
                    return RouterAuthResult(
                        authenticated=True,
                        adapter_id=self.adapter_id,
                        base_url=base_url,
                        used_https=base_url.startswith("https://"),
                        message=f"Authenticated with {self.vendor_family} endpoint ({path}).",
                    )
            return RouterAuthResult(
                authenticated=False,
                adapter_id=self.adapter_id,
                base_url=base_url,
                used_https=base_url.startswith("https://"),
                message=f"{self.vendor_family} endpoint did not confirm authentication; Web DOM interactive login fallback available.",
            )
        except Exception as exc:
            return RouterAuthResult(
                authenticated=False,
                adapter_id=self.adapter_id,
                base_url=base_url,
                used_https=base_url.startswith("https://"),
                message=f"{self.vendor_family} auth attempt failed: {exc}",
            )

    def inspect_all_pages(self) -> Dict[str, Any]:
        if not self._authenticated or self._client is None:
            return {}
        profile = VENDOR_PROFILES.get(self.vendor_key)
        if not profile:
            return {}
        out: Dict[str, Any] = {}
        for name, ep in profile.read_paths.items():
            r = self._client.get(ep)
            out[name] = {
                "path": ep,
                "status": r.status,
                "ok": r.status == 200 and bool(r.text.strip()),
                "body": r.text,
                "json": r.json_data,
            }
        return out

    def read_config(self) -> RouterConfigurationSnapshot:
        if not self._authenticated or self._client is None:
            raise RuntimeError("Router session is not authenticated.")
        from app.wifi.router.parser import RouterConfigurationParser

        pages = self.inspect_all_pages()
        radios: Dict[str, RouterWifiRadioConfig] = {}
        parser = RouterConfigurationParser()
        kv_all: Dict[str, Any] = {}
        for pname, pdata in pages.items():
            j = pdata.get("json")
            if isinstance(j, dict):
                flat = {str(k): v for k, v in j.items() if not isinstance(v, (dict, list))}
                for rec in parser.parse_key_values(flat, page_name=pname, section=pname):
                    if not rec.redacted:
                        kv_all[rec.setting_key] = rec.current_value
            body = pdata.get("body") or ""
            if isinstance(body, str) and body.strip():
                for rec in parser.parse_html_inputs(body, page_name=pname, section=pname):
                    if not rec.redacted:
                        kv_all[rec.setting_key] = rec.current_value

        wlan_info = pages.get("wlan", {})
        j = wlan_info.get("json") if isinstance(wlan_info.get("json"), dict) else {}
        if j:
            for band in ("2.4 GHz", "5 GHz", "6 GHz"):
                if band in j and isinstance(j[band], dict):
                    radios[band] = RouterWifiRadioConfig(
                        band=band,
                        enabled=j[band].get("enabled"),
                        ssid=j[band].get("ssid"),
                        channel=str(j[band].get("channel")) if j[band].get("channel") is not None else None,
                        channel_width=(
                            str(j[band].get("channel_width"))
                            if j[band].get("channel_width") is not None
                            else None
                        ),
                    )
        if "2.4 GHz" not in radios and any(k.lower() in kv_all for k in ("ssid", "wl0_ssid", "channel", "wl0_channel")):
            ssid_v = kv_all.get("ssid") or kv_all.get("wl0_ssid")
            ch_v = kv_all.get("channel") or kv_all.get("wl0_channel")
            if ssid_v or ch_v:
                radios["2.4 GHz"] = RouterWifiRadioConfig(
                    band="2.4 GHz",
                    ssid=str(ssid_v) if ssid_v is not None else None,
                    channel=str(ch_v) if ch_v is not None else None,
                )

        def _pick(*names: str) -> Optional[str]:
            lower_map = {str(k).lower(): v for k, v in kv_all.items()}
            for nm in names:
                if nm.lower() in lower_map and lower_map[nm.lower()] not in (None, ""):
                    return str(lower_map[nm.lower()])
            return None

        dns_raw = _pick("dns_servers", "dns", "dns1", "wan_dns")
        dns_list = [d.strip() for d in re.split(r"[,;\s]+", dns_raw or "") if d.strip()] if dns_raw else []

        return RouterConfigurationSnapshot(
            captured_at=utc_now(),
            adapter_id=self.adapter_id,
            hardware_verified=self.hardware_verified,
            vendor=self.vendor_family,
            firmware_version=_pick("firmware", "firmware_version", "sw_version", "version"),
            wan_ip=_pick("wan_ip", "external_ip", "wan_ipaddr"),
            wan_connection_type=_pick("wan_type", "wan_proto", "connection_type"),
            lan_ip=_pick("lan_ip", "lan_ipaddr", "gateway_ip"),
            dhcp_enabled=(
                str(_pick("dhcp_enabled", "dhcp_enable")).lower() in ("1", "true", "on", "enabled")
                if _pick("dhcp_enabled", "dhcp_enable") is not None
                else None
            ),
            dns_servers=dns_list,
            radios=radios,
            raw_backup_blob=json.dumps({k: v.get("json") or v.get("status") for k, v in pages.items()}, ensure_ascii=False),
        )

    def get_connected_devices(self) -> List[ConnectedDeviceRecord]:
        if not self._authenticated or self._client is None:
            return []
        pages = self.inspect_all_pages()
        devices: List[ConnectedDeviceRecord] = []
        seen: set[str] = set()
        mac_re = re.compile(r"([0-9a-fA-F]{2}(?::|-)[0-9a-fA-F]{2}(?:(?::|-)[0-9a-fA-F]{2}){4})")
        ip_re = re.compile(r"\b((?:\d{1,3}\.){3}\d{1,3})\b")
        for pdata in pages.values():
            j = pdata.get("json")
            if isinstance(j, dict):
                for key in ("devices", "hosts", "clients", "dhcp_leases", "leases", "lan_hosts"):
                    items = j.get(key)
                    if isinstance(items, list):
                        for item in items:
                            if not isinstance(item, dict):
                                continue
                            mac = str(item.get("mac") or item.get("mac_address") or "").strip().lower()
                            ip = str(item.get("ip") or item.get("ip_address") or "").strip()
                            if not (mac or ip):
                                continue
                            uid = mac or ip
                            if uid in seen:
                                continue
                            seen.add(uid)
                            devices.append(
                                ConnectedDeviceRecord(
                                    hostname=item.get("hostname") or item.get("name"),
                                    ip_address=ip or None,
                                    mac_address=mac or None,
                                    connection_type=(
                                        str(item.get("type") or item.get("interface") or "unknown").lower()
                                        if str(item.get("type") or item.get("interface") or "unknown").lower() in ("wifi_24", "wifi_5", "wifi_6", "ethernet", "unknown")
                                        else "unknown"
                                    ),
                                    source="router_api",
                                )
                            )
            body = pdata.get("body") or ""
            if isinstance(body, str) and "<tr" in body.lower():
                for row in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.IGNORECASE | re.DOTALL):
                    m_mac = mac_re.search(row)
                    m_ip = ip_re.search(row)
                    if m_mac and m_ip:
                        mac = m_mac.group(1).replace("-", ":").lower()
                        ip = m_ip.group(1)
                        if mac in seen:
                            continue
                        seen.add(mac)
                        devices.append(
                            ConnectedDeviceRecord(
                                ip_address=ip,
                                mac_address=mac,
                                connection_type="unknown",
                                source="router_api",
                            )
                        )
        return devices

    def _write_setting_raw(self, proposal: RouterChangeProposal) -> tuple[bool, str]:
        return False, f"Write actions disabled for unverified {self.vendor_family} firmware."

    def _extract_target_value(self, snapshot: RouterConfigurationSnapshot, proposal: RouterChangeProposal) -> Optional[str]:
        return None
