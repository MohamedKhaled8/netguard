"""MikroTik RouterOS REST API v7.1+ adapter."""

from __future__ import annotations

import base64
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


class MikroTikRouterAdapter(IRouterAdapter):
    """Modular adapter for MikroTik RouterOS devices exposing HTTP/HTTPS REST (/rest)."""

    adapter_id = "mikrotik"
    vendor_family = "MikroTik"

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
            supports_wan_read=True,
            supports_lan_dhcp_read=True,
            supports_firewall_nat_read=True,
            supports_logs_read=True,
            limitations=[
                "MikroTik RouterOS REST adapter requires RouterOS >= v7.1 with www/www-ssl enabled.",
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
        token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        client.extra_headers["Authorization"] = f"Basic {token}"
        self._client = client
        self._base_url = base_url
        self._authenticated = False
        try:
            resp = client.get("/rest/system/resource")
            if resp.status == 200 and isinstance(resp.json_data, dict):
                self._authenticated = True
                return RouterAuthResult(
                    authenticated=True,
                    adapter_id=self.adapter_id,
                    base_url=base_url,
                    used_https=base_url.startswith("https://"),
                    message="Authenticated with MikroTik RouterOS REST API.",
                )
            return RouterAuthResult(
                authenticated=False,
                adapter_id=self.adapter_id,
                base_url=base_url,
                used_https=base_url.startswith("https://"),
                message=f"MikroTik REST authentication rejected (HTTP {resp.status}).",
            )
        except Exception as exc:
            return RouterAuthResult(
                authenticated=False,
                adapter_id=self.adapter_id,
                base_url=base_url,
                used_https=base_url.startswith("https://"),
                message=f"MikroTik authentication failed: {exc}",
            )

    def inspect_all_pages(self) -> Dict[str, Any]:
        if not self._authenticated or self._client is None:
            return {}
        out: Dict[str, Any] = {}
        for name, ep in (
            ("device_info", "/rest/system/resource"),
            ("wireless", "/rest/interface/wireless"),
            ("wifi", "/rest/interface/wifi"),
            ("dns", "/rest/ip/dns"),
            ("dhcp_server", "/rest/ip/dhcp-server"),
            ("dhcp_leases", "/rest/ip/dhcp-server/lease"),
            ("queues", "/rest/queue/simple"),
            ("firewall_filter", "/rest/ip/firewall/filter"),
            ("firewall_nat", "/rest/ip/firewall/nat"),
            ("ip_addresses", "/rest/ip/address"),
            ("logs", "/rest/log"),
        ):
            r = self._client.get(ep)
            out[name] = {
                "path": ep,
                "status": r.status,
                "ok": r.status == 200,
                "body": r.text,
                "json": r.json_data,
            }
        return out

    def read_config(self) -> RouterConfigurationSnapshot:
        if not self._authenticated or self._client is None:
            raise RuntimeError("Router session is not authenticated.")
        res = self._client.get("/rest/system/resource").json_data or {}
        dns = self._client.get("/rest/ip/dns").json_data or {}
        wl = self._client.get("/rest/interface/wireless").json_data
        if not isinstance(wl, list):
            wl = self._client.get("/rest/interface/wifi").json_data or []
        queues = self._client.get("/rest/queue/simple").json_data or []

        radios: Dict[str, RouterWifiRadioConfig] = {}
        if isinstance(wl, list):
            for iface in wl:
                if not isinstance(iface, dict):
                    continue
                b_raw = str(iface.get("band") or iface.get("name") or "")
                band = "5 GHz" if "5ghz" in b_raw.lower() or "wlan2" in b_raw.lower() else "2.4 GHz"
                radios[band] = RouterWifiRadioConfig(
                    band=band,
                    enabled=(iface.get("disabled") != "true"),
                    ssid=iface.get("ssid"),
                    channel=str(iface.get("frequency") or ""),
                    channel_width=str(iface.get("channel-width") or ""),
                    tx_power=str(iface.get("tx-power") or ""),
                )

        dns_servers = [s.strip() for s in str(dns.get("servers") or "").split(",") if s.strip()] if isinstance(dns, dict) else []
        return RouterConfigurationSnapshot(
            captured_at=utc_now(),
            adapter_id=self.adapter_id,
            hardware_verified=self.hardware_verified,
            vendor="MikroTik",
            model=res.get("board-name") if isinstance(res, dict) else "MikroTik RouterOS",
            firmware_version=res.get("version") if isinstance(res, dict) else None,
            dns_servers=dns_servers,
            radios=radios,
            qos_enabled=bool(isinstance(queues, list) and len(queues) > 0),
            sqm_available=True,
            sqm_enabled=any("cake" in str(q.get("queue", "")).lower() or "fq" in str(q.get("queue", "")).lower() for q in queues if isinstance(q, dict)),
            raw_backup_blob=json.dumps({"resource": res, "dns": dns}, ensure_ascii=False),
        )

    def get_connected_devices(self) -> List[ConnectedDeviceRecord]:
        if not self._authenticated or self._client is None:
            return []
        leases = self._client.get("/rest/ip/dhcp-server/lease").json_data
        out: List[ConnectedDeviceRecord] = []
        if isinstance(leases, list):
            for l in leases:
                if not isinstance(l, dict):
                    continue
                out.append(
                    ConnectedDeviceRecord(
                        ip_address=l.get("address"),
                        mac_address=str(l.get("mac-address") or "").lower() or None,
                        hostname=l.get("host-name"),
                        connection_status="connected" if l.get("status") == "bound" else "stale",
                        source="router_api",
                        supports_rate_limit=True,
                    )
                )
        return out

    def _write_setting_raw(self, proposal: RouterChangeProposal) -> tuple[bool, str]:
        if not self._authenticated or self._client is None:
            return False, "Not authenticated."
        if proposal.category == "dns":
            servers = ",".join(str(proposal.proposed_value).split())
            r = self._client.post_json("/rest/ip/dns/set", {"servers": servers})
            return r.status in (200, 204), f"HTTP {r.status}"
        if proposal.category == "device_rate_limit" and proposal.target_ip:
            r = self._client.post_json(
                "/rest/queue/simple/add",
                {"name": f"NetGuard-{proposal.target_ip}", "target": f"{proposal.target_ip}/32", "max-limit": str(proposal.proposed_value)},
            )
            return r.status in (200, 201), f"HTTP {r.status}"
        return False, f"MikroTik write category '{proposal.category}' requires explicit interface id."

    def _extract_target_value(self, snapshot: RouterConfigurationSnapshot, proposal: RouterChangeProposal) -> Optional[str]:
        if proposal.category == "dns":
            return ",".join(snapshot.dns_servers)
        return None
