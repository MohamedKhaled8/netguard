"""Base router adapter interface, local-only HTTP client, and backup/readback safety helper."""

from __future__ import annotations

import abc
import http.client
import json
import ssl
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from app.wifi.models import (
    ConnectedDeviceRecord,
    RouterApplyResult,
    RouterAuthResult,
    RouterCapabilities,
    RouterChangeProposal,
    RouterConfigurationSnapshot,
    utc_now,
)
from app.wifi.router.credentials import validate_local_router_url


@dataclass
class RouterHttpResponse:
    """HTTP response captured from a local router management interface."""

    status: int
    headers: Dict[str, str] = field(default_factory=dict)
    text: str = ""
    json_data: Any = None


class RouterHttpClient:
    """Session-scoped local-only HTTP/HTTPS client with cookie jar and secret safety."""

    def __init__(
        self,
        base_url: str,
        *,
        verify_tls: bool = True,
        allow_loopback: bool = False,
        timeout_sec: float = 4.0,
    ) -> None:
        scheme, host, port, is_https = validate_local_router_url(
            base_url, allow_loopback=allow_loopback
        )
        self.base_url = base_url.rstrip("/")
        self.scheme = scheme
        self.host = host
        self.port = port
        self.is_https = is_https
        self.verify_tls = verify_tls
        self.allow_loopback = allow_loopback
        self.timeout_sec = timeout_sec
        self.cookies: Dict[str, str] = {}
        self.extra_headers: Dict[str, str] = {}

    def _open_conn(self) -> http.client.HTTPConnection:
        if self.is_https:
            ctx = (
                ssl.create_default_context()
                if self.verify_tls
                else ssl._create_unverified_context()
            )
            return http.client.HTTPSConnection(
                self.host, self.port, timeout=self.timeout_sec, context=ctx
            )
        return http.client.HTTPConnection(self.host, self.port, timeout=self.timeout_sec)

    def _ingest_set_cookies(self, headers_list: List[tuple[str, str]]) -> None:
        for k, v in headers_list:
            if k.lower() == "set-cookie" and "=" in v:
                kv = v.split(";", 1)[0].strip()
                if "=" in kv:
                    ck, cv = kv.split("=", 1)
                    self.cookies[ck.strip()] = cv.strip()

    def request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[bytes | str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> RouterHttpResponse:
        target_path = path if path.startswith("/") else f"/{path}"
        hdrs: Dict[str, str] = {
            "User-Agent": "NetGuardAI-RouterClient/1.0",
            "Host": self.host if self.port in (80, 443) else f"{self.host}:{self.port}",
        }
        hdrs.update(self.extra_headers)
        if self.cookies:
            hdrs["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
        if headers:
            hdrs.update(headers)

        payload: Optional[bytes] = None
        if isinstance(body, str):
            payload = body.encode("utf-8")
        elif isinstance(body, bytes):
            payload = body

        conn = self._open_conn()
        try:
            conn.request(method.upper(), target_path, body=payload, headers=hdrs)
            resp = conn.getresponse()
            raw_hdrs = resp.getheaders()
            self._ingest_set_cookies(raw_hdrs)
            raw_bytes = resp.read(262144)
            text = raw_bytes.decode("utf-8", errors="replace")
            hmap = {k.lower(): v for k, v in raw_hdrs}
            parsed_json: Any = None
            if text.lstrip().startswith(("{", "[")):
                try:
                    parsed_json = json.loads(text)
                except Exception:
                    parsed_json = None
            return RouterHttpResponse(
                status=int(resp.status),
                headers=hmap,
                text=text,
                json_data=parsed_json,
            )
        finally:
            conn.close()

    def get(self, path: str, headers: Optional[Dict[str, str]] = None) -> RouterHttpResponse:
        return self.request("GET", path, headers=headers)

    def post_form(
        self, path: str, form: Dict[str, Any], headers: Optional[Dict[str, str]] = None
    ) -> RouterHttpResponse:
        merged = {"Content-Type": "application/x-www-form-urlencoded"}
        if headers:
            merged.update(headers)
        return self.request("POST", path, body=urllib.parse.urlencode(form), headers=merged)

    def post_json(
        self, path: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None
    ) -> RouterHttpResponse:
        merged = {"Content-Type": "application/json"}
        if headers:
            merged.update(headers)
        return self.request("POST", path, body=json.dumps(payload), headers=merged)


class IRouterAdapter(abc.ABC):
    """Abstract router adapter interface separating discovery, auth, read, and guarded write."""

    adapter_id: str = "base"
    vendor_family: str = "Generic"
    hardware_verified: bool = False

    def __init__(self, *, allow_loopback: bool = False) -> None:
        self._allow_loopback = allow_loopback
        self._client: Optional[RouterHttpClient] = None
        self._authenticated: bool = False
        self._base_url: Optional[str] = None

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    @abc.abstractmethod
    def capabilities(self) -> RouterCapabilities:
        """Return honest capability matrix and known firmware/adapter caveats."""

    @abc.abstractmethod
    def authenticate(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        verify_tls: bool = True,
    ) -> RouterAuthResult:
        """Perform single-attempt authentication and initialize authenticated session."""

    @abc.abstractmethod
    def read_config(self) -> RouterConfigurationSnapshot:
        """Read current WAN/LAN/Wi-Fi/QoS settings from router."""

    @abc.abstractmethod
    def get_connected_devices(self) -> List[ConnectedDeviceRecord]:
        """Read connected LAN/Wi-Fi client list from router if supported."""

    @abc.abstractmethod
    def _write_setting_raw(self, proposal: RouterChangeProposal) -> tuple[bool, str]:
        """Low-level vendor POST implementing a single supported setting change."""

    @abc.abstractmethod
    def _extract_target_value(
        self, snapshot: RouterConfigurationSnapshot, proposal: RouterChangeProposal
    ) -> Optional[str]:
        """Read back the current value corresponding to proposal.target_field from snapshot."""

    def safe_apply_change(
        self,
        proposal: RouterChangeProposal,
        *,
        explicit_user_approval: bool = False,
        verify_readback_fn: Optional[Callable[[], RouterConfigurationSnapshot]] = None,
    ) -> RouterApplyResult:
        """Backup -> verify support -> apply -> readback verify -> rollback on mismatch."""
        if not explicit_user_approval:
            return RouterApplyResult(
                proposal_id=proposal.proposal_id,
                success=False,
                message="Explicit user approval is required before modifying router settings.",
            )

        caps = self.capabilities()
        if not caps.supports_wifi_write and proposal.category in (
            "wifi_channel",
            "channel_width",
            "tx_power",
            "band_steering",
            "security_mode",
        ):
            return RouterApplyResult(
                proposal_id=proposal.proposal_id,
                success=False,
                message=(
                    f"Adapter '{self.adapter_id}' does not support writing {proposal.category}; "
                    "apply this recommendation manually in the router admin panel."
                ),
            )
        if proposal.category == "device_rate_limit" and not caps.supports_per_device_bandwidth:
            return RouterApplyResult(
                proposal_id=proposal.proposal_id,
                success=False,
                message=(
                    f"Adapter '{self.adapter_id}' does not support router per-device rate limits."
                ),
            )
        if proposal.category == "qos_sqm" and not caps.supports_sqm_or_qos_write:
            return RouterApplyResult(
                proposal_id=proposal.proposal_id,
                success=False,
                message=f"Adapter '{self.adapter_id}' does not support SQM/QoS writes.",
            )

        # Step 1: Capture pre-change backup snapshot
        read_fn = verify_readback_fn or self.read_config
        backup_snap = read_fn()
        prev_val = self._extract_target_value(backup_snap, proposal) or proposal.current_value

        # Step 2: Execute write
        try:
            ok, write_msg = self._write_setting_raw(proposal)
        except Exception as exc:
            return RouterApplyResult(
                proposal_id=proposal.proposal_id,
                success=False,
                backup_taken=True,
                previous_value=prev_val,
                message=f"Router write failed safely before verification: {exc}",
            )

        if not ok:
            return RouterApplyResult(
                proposal_id=proposal.proposal_id,
                success=False,
                backup_taken=True,
                previous_value=prev_val,
                message=write_msg,
            )

        # Step 3: Readback verification (allow brief router commit/reconnect settle if first readback lags)
        import time as _time

        def _norm_val(v: Optional[str]) -> str:
            s = str(v or "").strip().lower()
            if s.endswith(" mhz"):
                s = s[:-4].strip()
            if s in ("0", "auto"):
                return "auto"
            if s in ("1", "true", "on", "enabled", "مفعّل"):
                return "true"
            if s in ("false", "off", "disabled", "معطّل"):
                return "false"
            return s

        target_norm = _norm_val(proposal.proposed_value)
        verified_val: Optional[str] = None
        matches = False
        last_read_err: Optional[Exception] = None
        for attempt in range(3):
            if attempt > 0:
                _time.sleep(0.55)
            try:
                post_snap = read_fn()
                verified_val = self._extract_target_value(post_snap, proposal)
                last_read_err = None
                if verified_val is not None and _norm_val(verified_val) == target_norm:
                    matches = True
                    break
            except Exception as exc:
                last_read_err = exc

        if matches:
            return RouterApplyResult(
                proposal_id=proposal.proposal_id,
                success=True,
                applied_automatically=True,
                backup_taken=True,
                readback_verified=True,
                previous_value=prev_val,
                verified_value=verified_val,
                message=f"Verified applied: {proposal.target_field} changed {prev_val} -> {verified_val}.",
            )

        if last_read_err is not None and verified_val is None:
            return RouterApplyResult(
                proposal_id=proposal.proposal_id,
                success=False,
                applied_automatically=True,
                backup_taken=True,
                readback_verified=False,
                previous_value=prev_val,
                message=f"تعذر إعادة قراءة إعدادات الراوتر بعد التعديل للتحقق ({last_read_err}).",
            )

        # Step 4: Rollback automatically on readback mismatch
        rolled_back = False
        if prev_val is not None:
            rollback_prop = proposal.model_copy(update={"proposed_value": prev_val})
            try:
                rb_ok, _ = self._write_setting_raw(rollback_prop)
                rolled_back = bool(rb_ok)
            except Exception:
                rolled_back = False

        return RouterApplyResult(
            proposal_id=proposal.proposal_id,
            success=False,
            applied_automatically=True,
            backup_taken=True,
            readback_verified=False,
            rolled_back=rolled_back,
            previous_value=prev_val,
            verified_value=verified_val,
            message=(
                f"Readback verification failed (expected {proposal.proposed_value}, read '{verified_val}'). "
                + ("Rolled back to previous value." if rolled_back else "Automatic rollback did not confirm; verify router UI.")
            ),
        )
