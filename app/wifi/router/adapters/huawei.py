"""Huawei router adapter supporting BOTH HiLink XML/JSON APIs and ONT/HG/DN Web ASP portals."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import time as _time
import urllib.parse
import xml.etree.ElementTree as ET
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


def _unescape_hw_js(text: str) -> str:
    """Decode Huawei ASP JavaScript hex escapes like \\x2e ('.'), \\x2d ('-'), \\x3a (':')."""
    if not text or "\\x" not in text:
        return text or ""
    return re.sub(r"\\x([0-9a-fA-F]{2})", lambda hx: chr(int(hx.group(1), 16)), text)


def _extract_js_tuples(text: str, fn_names: Tuple[str, ...]) -> List[List[str]]:
    """Parse Huawei ASP JS constructor calls like `new stWlan("Domain", "SSID1", ...);`."""
    rows: List[List[str]] = []
    if not text:
        return rows
    text = _unescape_hw_js(text)
    pattern = re.compile(
        r"new\s+(?:" + "|".join(re.escape(f) for f in fn_names) + r")\s*\(([^;]{0,4096})\)",
        re.IGNORECASE | re.DOTALL,
    )
    for m in pattern.finditer(text):
        arg_blob = m.group(1)
        args = re.findall(r'"([^"]*)"|\'([^\']*)\'|(-?\d+(?:\.\d+)?|true|false|null)', arg_blob)
        flat: List[str] = []
        for g1, g2, g3 in args:
            val = g1 or g2 or g3
            val = re.sub(r"\\x([0-9a-fA-F]{2})", lambda hx: chr(int(hx.group(1), 16)), val)
            flat.append(val)
        if flat:
            rows.append(flat)
    return rows


class HuaweiRouterAdapter(IRouterAdapter):
    """Modular Huawei adapter supporting HiLink SesTokInfo and ONT/DN/HG Web ASP portals."""

    adapter_id = "huawei"
    vendor_family = "Huawei"

    def __init__(self, *, allow_loopback: bool = False) -> None:
        super().__init__(allow_loopback=allow_loopback)
        self._csrf_token: str = ""
        self._mode: str = "hilink"  # "hilink" or "web_asp"
        self._isp_brand: Optional[str] = None
        self._model_hint: Optional[str] = None
        self._pages_cache: Optional[Dict[str, Any]] = None
        self._pages_cache_at: float = 0.0
        self._wlan_24_domain: str = "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1"
        self._wlan_5_domain: str = "InternetGatewayDevice.LANDevice.1.WLANConfiguration.5"

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
            supports_per_device_bandwidth=False,
            supports_sqm_or_qos_read=True,
            supports_sqm_or_qos_write=True,
            supports_dns_config_read=True,
            supports_dns_config_write=True,
            supports_backup_export=True,
            supports_wan_read=(self._mode == "web_asp"),
            supports_lan_dhcp_read=(self._mode == "web_asp"),
            supports_firewall_nat_read=(self._mode == "web_asp"),
            supports_logs_read=(self._mode == "web_asp"),
            supports_diagnostics_run=True,
            limitations=[
                "Writes enforce pre-change snapshot + readback validation and automatic rollback if rejected.",
                "Huawei Web ASP writes authenticate each change with a fresh X_HW_Token before POST set.cgi.",
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
        import socket as _socket
        client = RouterHttpClient(
            base_url, verify_tls=verify_tls, allow_loopback=self._allow_loopback, timeout_sec=3.0
        )
        self._client = client
        self._base_url = base_url
        self._authenticated = False
        self._pages_cache = None
        self._pages_cache_at = 0.0

        try:
            # 1) Fast probe for HiLink XML endpoint (1.5s cap so Web ASP routers don't stall)
            probe_client = RouterHttpClient(
                base_url, verify_tls=verify_tls, allow_loopback=self._allow_loopback, timeout_sec=1.5
            )
            try:
                tok_resp = probe_client.get("/api/webserver/SesTokInfo")
            except (TimeoutError, _socket.timeout):
                tok_resp = None
            if tok_resp is not None and tok_resp.status == 200 and ("<TokInfo>" in tok_resp.text or isinstance(tok_resp.json_data, dict)):
                self._mode = "hilink"
                return self._auth_hilink(client, base_url, username, password, tok_resp)

            # 2) Probe Web ASP portal (/ + /asp/GetRandCount.asp)
            root_resp = client.get("/")
            body_l = root_resp.text.lower()
            if "dtedata" in body_l:
                self._isp_brand = "WE (TE Data)"
            m_prod = re.search(r"var\s+ProductName\s*=\s*['\"]([^'\"]+)['\"]", root_resp.text, re.I)
            if m_prod:
                self._model_hint = re.sub(r"\\x([0-9a-fA-F]{2})", lambda hx: chr(int(hx.group(1), 16)), m_prod.group(1)).strip()

            rand_resp = client.get("/asp/GetRandCount.asp")
            if rand_resp.status == 200 and rand_resp.text.strip():
                self._mode = "web_asp"
                return self._auth_web_asp(client, base_url, username, password, root_resp.text, rand_resp.text)

            tok_status = tok_resp.status if tok_resp is not None else "timeout"
            return RouterAuthResult(
                authenticated=False,
                adapter_id=self.adapter_id,
                base_url=base_url,
                used_https=base_url.startswith("https://"),
                error_kind="unsupported",
                message=f"Neither Huawei SesTokInfo nor /asp/GetRandCount.asp responded (HTTP {tok_status}/{rand_resp.status}).",
            )
        except (TimeoutError, _socket.timeout) as exc:
            return RouterAuthResult(
                authenticated=False,
                adapter_id=self.adapter_id,
                base_url=base_url,
                used_https=base_url.startswith("https://"),
                error_kind="timeout",
                message=f"Router request timed out while connecting to {base_url}: {exc}",
            )
        except OSError as exc:
            return RouterAuthResult(
                authenticated=False,
                adapter_id=self.adapter_id,
                base_url=base_url,
                used_https=base_url.startswith("https://"),
                error_kind="unreachable",
                message=f"Router connection failed ({base_url}): {exc}",
            )
        except Exception as exc:
            return RouterAuthResult(
                authenticated=False,
                adapter_id=self.adapter_id,
                base_url=base_url,
                used_https=base_url.startswith("https://"),
                error_kind="auth_rejected",
                message=f"Huawei authentication error: {exc}",
            )

    def _auth_hilink(
        self,
        client: RouterHttpClient,
        base_url: str,
        username: str,
        password: str,
        tok_resp: Any,
    ) -> RouterAuthResult:
        tok_info = ""
        ses_info = ""
        if "<TokInfo>" in tok_resp.text:
            root = ET.fromstring(tok_resp.text)
            tok_el = root.find("TokInfo")
            ses_el = root.find("SesInfo")
            tok_info = (tok_el.text or "").strip() if tok_el is not None else ""
            ses_info = (ses_el.text or "").strip() if ses_el is not None else ""
        elif isinstance(tok_resp.json_data, dict):
            tok_info = str(tok_resp.json_data.get("TokInfo", ""))
            ses_info = str(tok_resp.json_data.get("SesInfo", ""))

        if ses_info and "=" in ses_info:
            k, v = ses_info.split("=", 1)
            client.cookies[k.strip()] = v.strip()
        self._csrf_token = tok_info

        pw_b64 = base64.b64encode(hashlib.sha256(password.encode("utf-8")).hexdigest().encode("utf-8")).decode("ascii")
        digest = base64.b64encode(
            hashlib.sha256(f"{username}{pw_b64}{tok_info}".encode("utf-8")).hexdigest().encode("utf-8")
        ).decode("ascii")

        xml_body = (
            f"<request><Username>{username}</Username><Password>{digest}</Password>"
            "<password_type>4</password_type></request>"
        )
        login_resp = client.request(
            "POST",
            "/api/user/login",
            body=xml_body,
            headers={
                "Content-Type": "application/xml",
                "__RequestVerificationToken": tok_info,
            },
        )
        ok = login_resp.status == 200 and "<response>OK</response>" in login_resp.text
        if not ok and isinstance(login_resp.json_data, dict):
            ok = login_resp.json_data.get("result") == "ok"

        if ok:
            self._authenticated = True
            return RouterAuthResult(
                authenticated=True,
                adapter_id=self.adapter_id,
                base_url=base_url,
                used_https=base_url.startswith("https://"),
                message="Authenticated with Huawei SesTokInfo endpoint.",
            )
        return RouterAuthResult(
            authenticated=False,
            adapter_id=self.adapter_id,
            base_url=base_url,
            used_https=base_url.startswith("https://"),
            message=f"Huawei authentication rejected (HTTP {login_resp.status}).",
        )

    def _auth_web_asp(
        self,
        client: RouterHttpClient,
        base_url: str,
        username: str,
        password: str,
        root_html: str,
        rand_token: str,
    ) -> RouterAuthResult:
        # Clean UTF-8 BOM and whitespace from GetRandCount.asp
        token_val = rand_token.lstrip("\ufeff").strip()
        self._csrf_token = token_val
        client.cookies.setdefault("Cookie", "body:Language:english:id=-1")
        pre_cookies = dict(client.cookies)

        # Huawei ONT ASP encodes PassWord in base64 for /login.cgi (safelogin.js base64encode)
        encoded_pw = base64.b64encode(password.encode("utf-8")).decode("ascii")
        login_resp = client.post_form(
            "/login.cgi",
            {
                "UserName": username,
                "PassWord": encoded_pw,
                "Language": "english",
                "x.X_HW_Token": token_val,
            },
            headers={"Referer": f"{base_url}/"},
        )
        loc = (login_resp.headers.get("location") or "").lower()
        set_cookie_hdr = (login_resp.headers.get("set-cookie") or "").lower()
        body_low = login_resp.text.lower()
        cookie_updated = bool(
            set_cookie_hdr
            and "id=-1" not in set_cookie_hdr
            or any(client.cookies.get(k) != pre_cookies.get(k) for k in client.cookies)
            or "sid" in {k.lower() for k in client.cookies}
        )
        has_login_form = (
            'type="password"' in body_low
            or "type='password'" in body_low
            or "auth required" in body_low
        )
        rejected = (
            "login.asp" in loc
            or "err" in loc
            or ("password" in body_low and "invalid" in body_low)
            or "var fail" in body_low
            or ("safelogin.js" in body_low and "/html/" not in body_low)
            or (has_login_form and not cookie_updated and "index" not in loc)
        )
        redirected_home = (
            "index" in loc
            or "main" in loc
            or ("window.location" in body_low and ("index" in body_low or "main" in body_low) and "login" not in body_low)
        )
        ok = login_resp.status in (200, 302, 303) and (cookie_updated or redirected_home) and not rejected
        if ok:
            self._authenticated = True
            return RouterAuthResult(
                authenticated=True,
                adapter_id=self.adapter_id,
                base_url=base_url,
                used_https=base_url.startswith("https://"),
                message="Authenticated with Huawei Web ASP (/login.cgi + X_HW_Token).",
            )
        return RouterAuthResult(
            authenticated=False,
            adapter_id=self.adapter_id,
            base_url=base_url,
            used_https=base_url.startswith("https://"),
            message=f"Huawei Web ASP authentication rejected (HTTP {login_resp.status}).",
        )

    def inspect_all_pages(self, *, force_refresh: bool = False) -> Dict[str, Any]:
        """Collect all accessible ASP/API pages with bounded concurrency and short-lived session cache."""
        import time as _time
        from concurrent.futures import ThreadPoolExecutor

        if not self._authenticated or self._client is None:
            return {}
        now_m = _time.monotonic()
        if not force_refresh and self._pages_cache is not None and (now_m - self._pages_cache_at) < 6.0:
            return self._pages_cache

        if self._mode == "hilink":
            endpoints = (
                ("device_info", "/api/device/information"),
                ("wan_status", "/api/monitoring/status"),
                ("wlan_basic", "/api/wlan/basic-settings"),
                ("wlan_hosts", "/api/wlan/host-list"),
                ("dhcp", "/api/dhcp/settings"),
                ("dns", "/api/net/dns"),
                ("qos", "/api/qos/settings"),
                ("firewall", "/api/security/firewall-switch"),
                ("upnp", "/api/security/upnp"),
            )
            def _fetch_hi(item: Tuple[str, str]) -> Tuple[str, Dict[str, Any]]:
                name, ep = item
                c = RouterHttpClient(
                    self._client.base_url,
                    verify_tls=self._client.verify_tls,
                    allow_loopback=self._allow_loopback,
                    timeout_sec=2.0,
                )
                c.cookies.update(self._client.cookies)
                c.extra_headers.update(self._client.extra_headers)
                try:
                    r = c.get(ep)
                    return name, {
                        "path": ep,
                        "status": r.status,
                        "ok": r.status == 200 and bool(r.text.strip()),
                        "body": r.text,
                        "json": r.json_data,
                    }
                except Exception as exc:
                    return name, {"path": ep, "status": 0, "ok": False, "body": "", "json": None, "error": str(exc)}

            with ThreadPoolExecutor(max_workers=4) as pool:
                pages = dict(pool.map(_fetch_hi, endpoints))
            self._pages_cache = pages
            self._pages_cache_at = _time.monotonic()
            return pages

        asp_pages = (
            ("device_info", "/html/ssmp/devinfo/devinfo.asp"),
            ("wan_info", "/html/bbsp/common/waninfo.asp"),
            ("dsl_stats", "/html/amp/dslinfo/dslinfo.asp"),
            ("optic_stats", "/html/amp/opticinfo/opticinfo.asp"),
            ("lan_dhcp", "/html/bbsp/dhcpservercfg/dhcp2.asp"),
            ("dns_config", "/html/bbsp/dnsconfiguration/dnshosts.asp"),
            ("wlan_24", "/html/amp/wlanbasic/WlanBasic.asp"),
            ("wlan_5", "/html/amp/wlanbasic/WlanBasic5G.asp"),
            ("wlan_info", "/html/amp/wlaninfo/wlaninfo.asp"),
            ("connected_devices", "/html/bbsp/userdevinfo/userdevinfo.asp"),
            ("qos_config", "/html/bbsp/qos/qos.asp"),
            ("firewall_config", "/html/bbsp/firewalllevel/firewalllevel.asp"),
            ("upnp_config", "/html/bbsp/upnp/upnp.asp"),
            ("port_mapping", "/html/bbsp/portmapping/portmapping.asp"),
            ("mac_filter", "/html/bbsp/macfilter/macfilter.asp"),
            ("parental_ctrl", "/html/bbsp/parentalctrl/parentalctrl.asp"),
            ("system_logs", "/html/ssmp/userlog/logview.asp"),
            ("backup_cfg", "/html/ssmp/cfgfile/cfgfile.asp"),
        )
        def _fetch_asp(item: Tuple[str, str]) -> Tuple[str, Dict[str, Any]]:
            name, ep = item
            c = RouterHttpClient(
                self._client.base_url,
                verify_tls=self._client.verify_tls,
                allow_loopback=self._allow_loopback,
                timeout_sec=2.5,
            )
            c.cookies.update(self._client.cookies)
            c.extra_headers.update(self._client.extra_headers)
            try:
                r = c.get(ep)
                return name, {
                    "path": ep,
                    "status": r.status,
                    "ok": r.status == 200 and len(r.text.strip()) > 32 and "safelogin.js" not in r.text.lower(),
                    "body": r.text,
                    "json": r.json_data,
                }
            except Exception as exc:
                return name, {"path": ep, "status": 0, "ok": False, "body": "", "json": None, "error": str(exc)}

        with ThreadPoolExecutor(max_workers=6) as pool:
            out = dict(pool.map(_fetch_asp, asp_pages))
        self._pages_cache = out
        self._pages_cache_at = _time.monotonic()
        return out

    def read_config(self) -> RouterConfigurationSnapshot:
        if not self._authenticated or self._client is None:
            raise RuntimeError("Router session is not authenticated.")
        if self._mode == "hilink":
            wlan_resp = self._client.get("/api/wlan/basic-settings")
            j = wlan_resp.json_data if isinstance(wlan_resp.json_data, dict) else {}
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
                        security_mode=obj.get("security_mode"),
                    )
            return RouterConfigurationSnapshot(
                captured_at=utc_now(),
                adapter_id=self.adapter_id,
                hardware_verified=self.hardware_verified,
                vendor="Huawei",
                isp_brand=self._isp_brand,
                model=j.get("model") or self._model_hint or "Huawei Gateway",
                firmware_version=j.get("firmware_version"),
                wan_status=j.get("wan_status"),
                wan_ip=j.get("wan_ip"),
                dns_servers=list(j.get("dns_servers", [])),
                radios=radios,
                qos_enabled=j.get("qos_enabled"),
                raw_backup_blob=json.dumps(j, ensure_ascii=False),
            )

        # Web ASP read across core ASP pages
        pages = self.inspect_all_pages()
        radios = {}
        dns_list: List[str] = []
        wan_status = None
        wan_ip = None
        qos_enabled = None
        fw_ver = None
        uptime_seconds: Optional[int] = None
        model = self._model_hint or "Huawei ONT/Gateway"

        dev_body = _unescape_hw_js(pages.get("device_info", {}).get("body", ""))
        m_sw = re.search(r"SoftwareVersion[^=]*=\s*['\"]([^'\"]+)['\"]", dev_body, re.I)
        if not m_sw:
            m_sw = re.search(r"(?:Software\s*Version|Soft\s*Version|إصدار\s*البرنامج)\s*[:<][^>]*>\s*(?:<td[^>]*>\s*)?([A-Za-z0-9_.\-]+V\d+R\d+[^<\s]*|[V\d][A-Za-z0-9_.\-]{5,})", dev_body, re.I)
        if m_sw:
            fw_ver = m_sw.group(1).strip()

        wlan_24_body = _unescape_hw_js(pages.get("wlan_24", {}).get("body", ""))
        wlan_5_body = _unescape_hw_js(pages.get("wlan_5", {}).get("body", ""))
        wlan_info_body = _unescape_hw_js(pages.get("wlan_info", {}).get("body", ""))
        wlan_text = wlan_24_body + "\n" + wlan_5_body + "\n" + wlan_info_body

        m_up = re.search(r"\bdev_uptime\s*[:=]\s*['\"]?(\d+)['\"]?", wlan_text + "\n" + dev_body, re.I)
        if m_up:
            uptime_seconds = int(m_up.group(1))

        # 1) Prefer full stWlanWifi(domain, name, enable, ssid, mode, channel, power, country, autoCh, width)
        width_map = {"0": "20 MHz", "1": "20/40 MHz", "2": "40 MHz", "3": "80 MHz", "4": "160 MHz"}
        wlan_wifi_rows = _extract_js_tuples(wlan_text, ("stWlanWifi",))
        for row in wlan_wifi_rows:
            if len(row) < 6:
                continue
            dom_raw = row[0].strip()
            dom_low = dom_raw.lower()
            iface_low = row[1].lower()
            band = "5 GHz" if ("5g" in dom_low or "ath4" in iface_low or "11a" in row[4].lower() or "11ac" in row[4].lower() or ".5" in dom_low) else "2.4 GHz"
            if dom_raw.startswith("InternetGatewayDevice."):
                if band == "5 GHz":
                    self._wlan_5_domain = dom_raw
                else:
                    self._wlan_24_domain = dom_raw
            if band not in radios:
                ch_val = "0" if (len(row) > 8 and row[8] == "1") else row[5]
                raw_w = row[9] if len(row) > 9 else ""
                radios[band] = RouterWifiRadioConfig(
                    band=band,
                    enabled=row[2].lower() in ("1", "true", "enable"),
                    ssid=row[3],
                    mode=row[4],
                    channel=ch_val,
                    tx_power=f"{row[6]}%" if len(row) > 6 and row[6].isdigit() else None,
                    channel_width=width_map.get(raw_w, raw_w or None),
                )

        # 2) Enrich security mode / fallback via stWlan / stWlanInfo tuples
        wlan_rows = _extract_js_tuples(wlan_text, ("stWlan", "stWlanInfo"))
        for row in wlan_rows:
            dom_raw = row[0].strip() if row else ""
            dom_low = dom_raw.lower()
            # Distinguish real DN8245V-56 stWlan(domain, enable, iface, ssid, BeaconType, ...) vs legacy unit mocks
            if len(row) >= 5 and row[1] in ("0", "1", "true", "false") and row[2].startswith(("ath", "wl", "ra")):
                band = "5 GHz" if ("5g" in dom_low or "ath4" in row[2].lower() or ".5" in dom_low) else "2.4 GHz"
                if dom_raw.startswith("InternetGatewayDevice."):
                    if band == "5 GHz":
                        self._wlan_5_domain = dom_raw
                    else:
                        self._wlan_24_domain = dom_raw
                if band not in radios:
                    radios[band] = RouterWifiRadioConfig(
                        band=band,
                        enabled=row[1].lower() in ("1", "true"),
                        ssid=row[3],
                        security_mode=row[4],
                    )
                elif not radios[band].security_mode:
                    radios[band].security_mode = row[4]
            else:
                band = "5 GHz" if any("5g" in c.lower() or "11a" in c.lower() for c in row) else "2.4 GHz"
                if band not in radios and len(row) >= 4:
                    radios[band] = RouterWifiRadioConfig(
                        band=band,
                        enabled=(row[2] in ("1", "true", "Enable")) if len(row) > 2 else None,
                        ssid=row[1] if len(row) > 1 else None,
                        channel=row[3] if len(row) > 3 else None,
                        channel_width=row[4] if len(row) > 4 else None,
                    )

        wan_body = _unescape_hw_js(pages.get("wan_info", {}).get("body", ""))
        wan_conn_type = None
        if len(wan_body.strip()) < 64 or ("WanInfo" not in wan_body and "WanPPP" not in wan_body and "WanIP" not in wan_body):
            try:
                alt_wan = self._client.get("/html/bbsp/common/wan_list_info.asp")
                if alt_wan.status == 200 and len(alt_wan.text.strip()) > 32:
                    wan_body += "\n" + _unescape_hw_js(alt_wan.text)
            except Exception:
                pass
        wan_rows = _extract_js_tuples(wan_body, ("WanInfo", "WanIP", "WanPPP", "stWan", "WanIPInfo", "WanPPPInfo"))
        for w in wan_rows:
            for item in w:
                if re.match(r"^\d+\.\d+\.\d+\.\d+$", item) and not item.startswith(("255.", "0.", "192.168.", "127.")):
                    if not wan_ip:
                        wan_ip = item
                il = item.lower()
                if il in ("connected", "up", "disconnected", "connecting") and wan_status is None:
                    wan_status = item
                if any(k in il for k in ("pppoe", "ip_routed", "bridge", "dhcp")) and wan_conn_type is None:
                    wan_conn_type = item
        if not wan_ip:
            m_wip = re.search(r"(?:IPv4IPAddress|ExternalIPAddress|WanIP)\s*[:=]\s*['\"](\d+\.\d+\.\d+\.\d+)['\"]", wan_body, re.I)
            if m_wip and not m_wip.group(1).startswith(("0.", "255.")):
                wan_ip = m_wip.group(1)
        if not wan_status:
            m_wst = re.search(r"(?:ConnectionStatus|Status)\s*[:=]\s*['\"](Connected|Up|Disconnected|Connecting)['\"]", wan_body, re.I)
            if m_wst:
                wan_status = m_wst.group(1)

        dns_body = _unescape_hw_js(pages.get("dns_config", {}).get("body", ""))
        dns_matches = re.findall(r"(?:PrimaryDns|SecondaryDns|DNSServers|IPv4DNSOverrideSwitch|X_HW_DNS)\s*[:=]\s*['\"]([^'\"]+)['\"]", wan_body + "\n" + dns_body, re.I)
        for dm in dns_matches:
            for part in re.split(r"[,\s]+", dm):
                if re.match(r"^\d+\.\d+\.\d+\.\d+$", part) and part != "0.0.0.0" and part not in dns_list:
                    dns_list.append(part)
        # Also catch DNS IPs embedded in WAN tuple columns
        if not dns_list and wan_rows:
            for w in wan_rows:
                for item in w:
                    for part in re.split(r"[,\s]+", item):
                        if re.match(r"^\d+\.\d+\.\d+\.\d+$", part) and part != wan_ip and not part.startswith(("255.", "0.", "192.168.")) and part not in dns_list:
                            dns_list.append(part)

        qos_body = _unescape_hw_js(pages.get("qos_config", {}).get("body", ""))
        qos_mode = None
        if "QoSEnable" in qos_body or "QueueManagement" in qos_body or "QoS" in qos_body:
            m_qe = re.search(r"QoSEnable\s*[:=]\s*['\"]?(1|0|true|false)['\"]?", qos_body, re.I)
            if m_qe:
                qos_enabled = m_qe.group(1).lower() in ("1", "true")
            elif pages.get("qos_config", {}).get("ok"):
                qos_enabled = bool(re.search(r"\b(?:Enable|QoSEnable)\s*[:=]\s*['\"]?(?:1|true)", qos_body, re.I))
            m_qm = re.search(r"(?:QoSMode|Mode|ClassificationEnable)\s*[:=]\s*['\"]([^'\"]+)['\"]", qos_body, re.I)
            if m_qm:
                qos_mode = m_qm.group(1).strip()

        upnp_body = _unescape_hw_js(pages.get("upnp_config", {}).get("body", ""))
        upnp_enabled = None
        m_upnp = re.search(r"(?:Enable|UpnpEnable)\s*[:=]\s*['\"]?(1|0|true|false)['\"]?", upnp_body, re.I)
        if m_upnp:
            upnp_enabled = m_upnp.group(1).lower() in ("1", "true")

        fw_body = _unescape_hw_js(pages.get("firewall_config", {}).get("body", ""))
        firewall_level = None
        m_fw = re.search(r"(?:Level|FirewallLevel|SecurityLevel)\s*[:=]\s*['\"]([^'\"]+)['\"]", fw_body, re.I)
        if m_fw:
            firewall_level = m_fw.group(1).strip().lower()

        # Parse LAN & DHCP fields + multi-instance DHCP pools cleanly from dhcp2.asp
        lan_body = re.sub(r"\\x([0-9a-fA-F]{2})", lambda hx: chr(int(hx.group(1), 16)), pages.get("lan_dhcp", {}).get("body", ""))
        lan_ip = None
        lan_mask = None
        dhcp_enabled = None
        dhcp_start = None
        dhcp_end = None
        dhcp_lease = None
        extra_sections: Dict[str, Any] = {}
        if lan_body:
            ip_rows = _extract_js_tuples(lan_body, ("stipaddr",))
            for r in ip_rows:
                if len(r) >= 4 and re.match(r"^\d+\.\d+\.\d+\.\d+$", r[2]):
                    if lan_ip is None:
                        lan_ip = r[2]
                        lan_mask = r[3]
            if not lan_ip:
                m_lip = re.search(r"(?:ethIpAddress|IPInterfaceIPAddress|LanIp)\s*[:=]\s*['\"](\d+\.\d+\.\d+\.\d+)['\"]", lan_body, re.I)
                if m_lip:
                    lan_ip = m_lip.group(1)
            if not lan_mask:
                m_mask = re.search(r"(?:ethSubnetMask|IPInterfaceSubnetMask|SubnetMask)\s*[:=]\s*['\"](\d+\.\d+\.\d+\.\d+)['\"]", lan_body, re.I)
                if m_mask:
                    lan_mask = m_mask.group(1)

            dhcp_rows = _extract_js_tuples(lan_body, ("dhcpcnst", "dhcpcnst1"))
            dhcp_instances: List[Dict[str, Any]] = []
            seen_dhcp_domains: set[tuple[str, str, str]] = set()
            for idx, dr in enumerate(dhcp_rows):
                if len(dr) >= 5:
                    sig = (dr[0], dr[1], dr[2])
                    if sig in seen_dhcp_domains:
                        continue
                    seen_dhcp_domains.add(sig)
                    inst_name = "SlaveDHCP" if "slv" in dr[0].lower() else f"PrimaryDHCP_{len(dhcp_instances) + 1}"
                    inst_obj = {
                        "instance": inst_name,
                        "domain": dr[0],
                        "pool_start": dr[1],
                        "pool_end": dr[2],
                        "lease_time_sec": int(dr[3]) if dr[3].isdigit() else None,
                        "enabled": dr[4].lower() in ("1", "true"),
                    }
                    dhcp_instances.append(inst_obj)
                    if "slv" not in dr[0].lower() and dhcp_start is None:
                        dhcp_start, dhcp_end = dr[1], dr[2]
                        dhcp_lease = inst_obj["lease_time_sec"]
                        dhcp_enabled = inst_obj["enabled"]

            m_dh = re.search(r"(?:DHCPServerEnable|DhcpEnable)\s*[:=]\s*['\"]?(1|0|true|false)['\"]?", lan_body, re.I)
            if dhcp_enabled is None and m_dh:
                dhcp_enabled = m_dh.group(1).lower() in ("1", "true")
            m_ms = re.search(r"(?:MinAddress|StartIp|startIpStr)\s*[:=]\s*['\"](\d+\.\d+\.\d+\.\d+)['\"]", lan_body, re.I)
            if not dhcp_start and m_ms:
                dhcp_start = m_ms.group(1)
            m_me = re.search(r"(?:MaxAddress|EndIp|endIpStr)\s*[:=]\s*['\"](\d+\.\d+\.\d+\.\d+)['\"]", lan_body, re.I)
            if not dhcp_end and m_me:
                dhcp_end = m_me.group(1)
            m_lt = re.search(r"(?:DHCPLeaseTime|LeaseTime|MainLeasedTime)\s*[:=]\s*['\"]?(\d+)['\"]?", lan_body, re.I)
            if dhcp_lease is None and m_lt:
                dhcp_lease = int(m_lt.group(1))
            if dhcp_enabled is None and dhcp_start and dhcp_end:
                dhcp_enabled = True
            if dhcp_start and dhcp_end and not any(d.get("instance", "").startswith("PrimaryDHCP") for d in dhcp_instances):
                dhcp_instances.insert(
                    0,
                    {
                        "instance": "PrimaryDHCP",
                        "domain": "InternetGatewayDevice.LANDevice.1.LANHostConfigManagement",
                        "pool_start": dhcp_start,
                        "pool_end": dhcp_end,
                        "lease_time_sec": dhcp_lease,
                        "enabled": bool(dhcp_enabled),
                    },
                )
            if dhcp_instances:
                extra_sections["dhcp_instances"] = dhcp_instances

        # Parse DSL line stats when available
        dsl_body = _unescape_hw_js(pages.get("dsl_stats", {}).get("body", ""))
        wan_down_mbps = None
        wan_up_mbps = None
        wan_line_stats: Dict[str, Any] = {}
        if dsl_body:
            m_dn = re.search(r"(?:DownstreamCurrRate|LineDownRate)\s*[:=]\s*['\"]?(\d+)['\"]?", dsl_body, re.I)
            m_up = re.search(r"(?:UpstreamCurrRate|LineUpRate)\s*[:=]\s*['\"]?(\d+)['\"]?", dsl_body, re.I)
            if m_dn:
                wan_down_mbps = round(int(m_dn.group(1)) / 1000.0, 2)
            if m_up:
                wan_up_mbps = round(int(m_up.group(1)) / 1000.0, 2)
            m_snr = re.search(r"(?:DownstreamNoiseMargin|SNRMarginDown)\s*[:=]\s*['\"]?([\d.]+)['\"]?", dsl_body, re.I)
            if m_snr:
                wan_line_stats["downstream_snr_db"] = float(m_snr.group(1))

        return RouterConfigurationSnapshot(
            captured_at=utc_now(),
            adapter_id=self.adapter_id,
            hardware_verified=self.hardware_verified,
            vendor="Huawei",
            isp_brand=self._isp_brand,
            model=model,
            firmware_version=fw_ver,
            uptime_seconds=uptime_seconds,
            wan_status=wan_status,
            wan_connection_type=wan_conn_type,
            wan_ip=wan_ip,
            wan_down_mbps=wan_down_mbps,
            wan_up_mbps=wan_up_mbps,
            wan_line_stats=wan_line_stats,
            lan_ip=lan_ip,
            lan_subnet_mask=lan_mask,
            dhcp_enabled=dhcp_enabled,
            dhcp_pool_start=dhcp_start,
            dhcp_pool_end=dhcp_end,
            dhcp_lease_time_sec=dhcp_lease,
            dns_servers=dns_list,
            radios=radios,
            qos_enabled=qos_enabled,
            qos_mode=qos_mode,
            upnp_enabled=upnp_enabled,
            firewall_level=firewall_level,
            extra_sections=extra_sections,
        )

    def get_connected_devices(self) -> List[ConnectedDeviceRecord]:
        if not self._authenticated or self._client is None:
            return []
        if self._mode == "hilink":
            resp = self._client.get("/api/wlan/host-list")
            j = resp.json_data if isinstance(resp.json_data, dict) else {}
            out: List[ConnectedDeviceRecord] = []
            for h in j.get("hosts", []):
                if isinstance(h, dict):
                    out.append(
                        ConnectedDeviceRecord(
                            ip_address=h.get("ip"),
                            mac_address=h.get("mac"),
                            hostname=h.get("hostname"),
                            connection_type=h.get("connection_type", "unknown"),
                            connection_status="connected",
                            rssi_dbm=h.get("rssi"),
                            source="router_api",
                        )
                    )
            return out

        cached_dev_page = self._pages_cache.get("connected_devices") if (
            self._pages_cache and (_time.monotonic() - self._pages_cache_at) < 25.0
        ) else None
        raw_text = ""
        if isinstance(cached_dev_page, dict) and cached_dev_page.get("ok") and cached_dev_page.get("body"):
            raw_text = _unescape_hw_js(str(cached_dev_page.get("body") or ""))
        else:
            resp = self._client.get("/html/bbsp/userdevinfo/userdevinfo.asp")
            raw_text = _unescape_hw_js(resp.text)
        rows = _extract_js_tuples(raw_text, ("USERDevice", "USERDeviceNew", "UserDevinfo", "UserDev", "LanDevInfo"))
        if not rows:
            try:
                alt_dev = self._client.get("/html/bbsp/common/GetLanUserDevInfo.asp")
                if alt_dev.status == 200 and alt_dev.text:
                    raw_text = _unescape_hw_js(alt_dev.text)
                    rows = _extract_js_tuples(raw_text, ("USERDevice", "USERDeviceNew", "UserDevinfo", "UserDev", "LanDevInfo"))
            except Exception:
                pass
        out = []
        seen_keys: set[str] = set()
        for r in rows:
            ip = next((x for x in r if re.match(r"^\d+\.\d+\.\d+\.\d+$", x)), None)
            mac = next((x for x in r if re.match(r"^[0-9a-fA-F]{2}(?:[:-][0-9a-fA-F]{2}){5}$", x)), None)
            mac_n = mac.replace("-", ":").lower() if mac else None
            # Prefer real device hostname (not Domain paths or status tokens)
            host = next(
                (
                    x
                    for x in r
                    if x
                    and x != ip
                    and x != mac
                    and not x.isdigit()
                    and not x.startswith(("InternetGatewayDevice.", "br0", "LAN", "SSID", "ath"))
                    and x.lower() not in ("online", "offline", "active", "inactive", "eth", "wifi", "static", "dhcp", "auto", "connected")
                    and len(x) <= 64
                ),
                None,
            )
            key = mac_n or ip or ""
            if (ip or mac_n) and key not in seen_keys:
                seen_keys.add(key)
                out.append(
                    ConnectedDeviceRecord(
                        ip_address=ip,
                        mac_address=mac_n,
                        hostname=host,
                        connection_type="ethernet" if any("lan" in x.lower() or "eth" in x.lower() for x in r) else ("wifi_5" if any("5g" in x.lower() or "ath4" in x.lower() for x in r) else ("wifi_24" if any("ssid" in x.lower() or "wlan" in x.lower() or "wifi" in x.lower() for x in r) else "unknown")),
                        connection_status="connected" if any(x.lower() in ("online", "1", "active", "connected") for x in r) else "unknown",
                        source="router_api",
                    )
                )
        return out

    @staticmethod
    def _extract_ont_token(html: str) -> Optional[str]:
        if not html:
            return None
        patterns = (
            r'name\s*=\s*["\']onttoken["\'][^>]*value\s*=\s*["\']([A-Za-z0-9_.\-]{8,128})["\']',
            r'id\s*=\s*["\']hwonttoken["\'][^>]*value\s*=\s*["\']([A-Za-z0-9_.\-]{8,128})["\']',
            r'value\s*=\s*["\']([A-Za-z0-9_.\-]{8,128})["\'][^>]*name\s*=\s*["\']onttoken["\']',
            r'(?:onttoken|x_hw_token)\s*[:=]\s*["\']([A-Za-z0-9_.\-]{8,128})["\']',
            r'GetToken\s*\(\s*["\']([A-Za-z0-9_.\-]{8,128})["\']',
        )
        for pat in patterns:
            m = re.search(pat, html, re.I)
            if m:
                return m.group(1).strip()
        return None

    def _fetch_hw_token(self, page_path: Optional[str] = None, *, skip_page: bool = False) -> str:
        """Obtain a fresh Huawei X_HW_Token / onttoken before authenticated set.cgi POST."""
        if self._client is None:
            return self._csrf_token
        if page_path and not skip_page:
            try:
                rp = self._client.get(page_path)
                if rp.status == 200 and rp.text:
                    page_tok = self._extract_ont_token(rp.text)
                    if page_tok:
                        self._csrf_token = page_tok
                        return page_tok
            except Exception:
                pass
        for ep in (
            "/html/ssmp/common/getRandString.asp",
            "/html/ssmp/common/GetRandString.asp",
            "/html/ssmp/common/getrand.asp",
            "/asp/GetRandCount.asp",
        ):
            try:
                r = self._client.get(ep)
                raw = (r.text or "").lstrip("\ufeff").strip()
                if r.status == 200 and raw:
                    if "<" not in raw and len(raw) <= 128:
                        m_q = re.search(r"['\"]([A-Za-z0-9_.\-]{8,128})['\"]", raw)
                        tok = m_q.group(1) if m_q else raw
                        self._csrf_token = tok
                        return tok
                    embedded = self._extract_ont_token(raw)
                    if embedded:
                        self._csrf_token = embedded
                        return embedded
            except Exception:
                pass
        return self._csrf_token

    def _write_setting_raw(self, proposal: RouterChangeProposal) -> tuple[bool, str]:
        if not self._authenticated or self._client is None:
            return False, "Not authenticated."
        if self._mode == "hilink":
            resp = self._client.post_json(
                "/api/wlan/basic-settings",
                {"band": proposal.band, "field": proposal.target_field, "value": proposal.proposed_value},
                headers={"__RequestVerificationToken": self._csrf_token},
            )
            j = resp.json_data if isinstance(resp.json_data, dict) else {}
            ok = resp.status == 200 and (j.get("result") == "ok" or "<response>OK</response>" in resp.text)
            self._pages_cache = None
            return ok, f"HTTP {resp.status}"

        # Huawei Web ASP (DN8245V-56 / HG8145V5) authenticated set.cgi with page-scoped onttoken + Origin/Referer
        fld = (proposal.target_field or "").strip().lower()
        val = str(proposal.proposed_value or "").strip()
        is_5g = bool(proposal.band and "5" in str(proposal.band))
        wlan_dom = self._wlan_5_domain if is_5g else self._wlan_24_domain
        req_page = "html/amp/wlanbasic/WlanBasic5G.asp" if is_5g else "html/amp/wlanbasic/WlanBasic.asp"

        post_path = ""
        form: Dict[str, str] = {}
        if fld == "channel":
            post_path = f"/html/amp/wlanbasic/set.cgi?x={wlan_dom}&RequestFile={req_page}"
            auto_val = "1" if val.lower() in ("0", "auto") else "0"
            form["x.AutoChannelEnable"] = auto_val
            if auto_val == "0":
                form["x.Channel"] = val
        elif fld == "channel_width":
            w_rev = {"20 mhz": "0", "20/40 mhz": "1", "40 mhz": "2", "80 mhz": "3", "160 mhz": "4"}
            w_code = w_rev.get(val.lower(), val.replace("MHz", "").strip())
            post_path = f"/html/amp/wlanbasic/set.cgi?x={wlan_dom}&RequestFile={req_page}"
            form["x.X_HW_HT20"] = w_code
        elif fld == "tx_power":
            post_path = f"/html/amp/wlanbasic/set.cgi?x={wlan_dom}&RequestFile={req_page}"
            form["x.TransmitPower"] = val.replace("%", "").strip()
        elif fld == "ssid":
            post_path = f"/html/amp/wlanbasic/set.cgi?x={wlan_dom}&RequestFile={req_page}"
            form["x.SSID"] = val
        elif fld in ("enabled", "radio_enabled", "radio_5ghz_enabled"):
            post_path = f"/html/amp/wlanbasic/set.cgi?x={wlan_dom}&RequestFile={req_page}"
            form["x.Enable"] = "1" if val.lower() in ("1", "true", "on", "مفعّل", "enabled") else "0"
        elif fld in ("qos_enabled",):
            req_page = "html/bbsp/qos/qos.asp"
            post_path = f"/html/bbsp/qos/set.cgi?x=InternetGatewayDevice.QueueManagement&RequestFile={req_page}"
            form["x.Enable"] = "1" if val.lower() in ("1", "true", "on", "مفعّل", "enabled") else "0"
        elif fld in ("upnp_enabled",):
            req_page = "html/bbsp/upnp/upnp.asp"
            post_path = f"/html/bbsp/upnp/set.cgi?x=InternetGatewayDevice.Services.X_HW_UPnP&RequestFile={req_page}"
            form["x.Enable"] = "1" if val.lower() in ("1", "true", "on", "مفعّل", "enabled") else "0"
        elif fld in ("dhcp_enabled", "dhcp_pool_start", "dhcp_pool_end"):
            req_page = "html/bbsp/dhcpservercfg/dhcp2.asp"
            post_path = f"/html/bbsp/dhcpservercfg/set.cgi?x=InternetGatewayDevice.LANDevice.1.LANHostConfigManagement&RequestFile={req_page}"
            if fld == "dhcp_enabled":
                form["x.DHCPServerEnable"] = "1" if val.lower() in ("1", "true", "on", "مفعّل", "enabled") else "0"
            elif fld == "dhcp_pool_start":
                form["x.MinAddress"] = val
            else:
                form["x.MaxAddress"] = val
        elif fld in ("dns_servers",):
            req_page = "html/bbsp/dhcpservercfg/dhcp2.asp"
            post_path = f"/html/bbsp/dhcpservercfg/set.cgi?x=InternetGatewayDevice.LANDevice.1.LANHostConfigManagement&RequestFile={req_page}"
            form["x.DNSServers"] = val
        else:
            return False, f"Huawei Web ASP change for '{fld}' is not mapped cleanly yet."

        tok = self._fetch_hw_token(f"/{req_page}")
        form["x.X_HW_Token"] = tok
        post_headers = {
            "Referer": f"{self._client.base_url}/{req_page}",
            "Origin": self._client.base_url,
        }
        resp = self._client.post_form(post_path, form, headers=post_headers)
        if resp.status == 403:
            alt_tok = self._fetch_hw_token(f"/{req_page}", skip_page=True)
            if alt_tok and alt_tok != tok:
                form["x.X_HW_Token"] = alt_tok
                resp = self._client.post_form(post_path, form, headers=post_headers)

        self._pages_cache = None
        body_low = (resp.text or "").lower()
        has_hw_err = bool(
            re.search(r"(?:errcode|errorcode)\s*[:=]\s*['\"]?(?!0\b)[a-z0-9_]+", body_low)
            or re.search(r"(?:var\s+fail\b|alert\s*\(.*?(?:fail|error|invalid)|login\.asp)", body_low)
        )
        ok = resp.status in (200, 302, 303) and "safelogin.js" not in body_low and not has_hw_err
        if resp.status == 403:
            return (
                False,
                "HTTP 403: الراوتر رفض التعديل التلقائي (حساب محدود أو حماية جلسة إضافية) — يمكنك التعديل مباشرة من تبويب (واجهة الراوتر المباشرة / المتصفح) بالبرنامج.",
            )
        return ok, f"HTTP {resp.status}"

    def _extract_target_value(
        self, snapshot: RouterConfigurationSnapshot, proposal: RouterChangeProposal
    ) -> Optional[str]:
        fld = (proposal.target_field or "").strip().lower()
        if proposal.band and proposal.band in snapshot.radios:
            r = snapshot.radios[proposal.band]
            if fld == "channel":
                return r.channel
            if fld == "channel_width":
                return r.channel_width
            if fld == "tx_power":
                return r.tx_power
            if fld == "ssid":
                return r.ssid
            if fld in ("enabled", "radio_enabled", "radio_5ghz_enabled"):
                return "مفعّل" if r.enabled else "معطّل"
        if fld == "qos_enabled" and snapshot.qos_enabled is not None:
            return "مفعّل" if snapshot.qos_enabled else "معطّل"
        if fld == "upnp_enabled" and snapshot.upnp_enabled is not None:
            return "مفعّل" if snapshot.upnp_enabled else "معطّل"
        if fld == "dhcp_enabled" and snapshot.dhcp_enabled is not None:
            return "مفعّل" if snapshot.dhcp_enabled else "معطّل"
        if fld == "dhcp_pool_start":
            return snapshot.dhcp_pool_start
        if fld == "dhcp_pool_end":
            return snapshot.dhcp_pool_end
        if fld == "dns_servers" and snapshot.dns_servers:
            return ", ".join(snapshot.dns_servers)
        return None
