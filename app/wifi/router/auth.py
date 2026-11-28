"""Single-attempt router authentication guard preventing lockout loops."""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from app.wifi.models import RouterAuthResult, RouterDiscoveryResult
from app.wifi.router.credentials import (
    SessionCredentialStore,
    WindowsCredentialManagerStore,
    evaluate_transport_security_warning,
    redact_secrets,
    validate_local_router_url,
)


class RouterAuthCoordinator:
    """Enforces single-attempt authentication, lockout tracking, and safe credential persistence."""

    def __init__(
        self,
        *,
        session_store: Optional[SessionCredentialStore] = None,
        win_cred_store: Optional[WindowsCredentialManagerStore] = None,
        allow_loopback: bool = False,
    ) -> None:
        self._session_store = session_store or SessionCredentialStore()
        self._win_cred_store = win_cred_store or WindowsCredentialManagerStore()
        self._allow_loopback = allow_loopback
        self._lock = threading.Lock()
        self._failed_attempts: Dict[str, int] = {}

    def get_failed_attempts(self, gateway_ip: str) -> int:
        with self._lock:
            return self._failed_attempts.get(gateway_ip, 0)

    def authenticate_single_attempt(
        self,
        *,
        adapter: Any,
        discovery: RouterDiscoveryResult,
        base_url: str,
        username: str,
        password: str,
        persist_in_windows_vault: bool = False,
        verify_tls: bool = True,
        user_acknowledged_security_warning: bool = False,
    ) -> RouterAuthResult:
        """Execute exactly one credential check against a verified local gateway URL."""
        _, host, _, is_https = validate_local_router_url(
            base_url,
            expected_gateway_ip=discovery.gateway_ip,
            allow_loopback=self._allow_loopback,
        )
        sec_warn = evaluate_transport_security_warning(
            base_url, discovery.tls_trusted if is_https else None
        )
        if sec_warn and not user_acknowledged_security_warning:
            return RouterAuthResult(
                authenticated=False,
                adapter_id=getattr(adapter, "adapter_id", discovery.adapter_id),
                base_url=base_url,
                used_https=is_https,
                error_kind="security_ack_required",
                security_warning=sec_warn,
                message=(
                    "User acknowledgement of local transport security notice is required before sending credentials."
                ),
            )

        with self._lock:
            prior_fails = self._failed_attempts.get(host, 0)
            if prior_fails >= 3:
                return RouterAuthResult(
                    authenticated=False,
                    adapter_id=getattr(adapter, "adapter_id", discovery.adapter_id),
                    base_url=base_url,
                    used_https=is_https,
                    error_kind="lockout_guard",
                    security_warning=sec_warn,
                    lockout_risk_warning=(
                        "3 prior login failures occurred on this gateway. Further automatic attempts "
                        "are blocked to prevent router admin lockout; verify password in router UI."
                    ),
                    message="Blocked to protect router admin account from lockout.",
                )

        result: RouterAuthResult = adapter.authenticate(
            base_url=base_url,
            username=username,
            password=password,
            verify_tls=verify_tls,
        )
        result.security_warning = result.security_warning or sec_warn

        # Classify network timeouts / unreachable gateways separately from actual credential rejections
        msg_low = (result.message or "").lower()
        if not result.authenticated and result.error_kind == "none":
            if any(k in msg_low for k in ("timed out", "timeout")):
                result.error_kind = "timeout"
            elif any(k in msg_low for k in ("refused", "unreachable", "connection failed", "connection error", "name resolution", "neither")):
                result.error_kind = "unreachable"
            elif "unsupported" in msg_low or "no vendor-specific" in msg_low:
                result.error_kind = "unsupported"
            else:
                result.error_kind = "auth_rejected"

        with self._lock:
            if result.authenticated:
                self._failed_attempts[host] = 0
                target_key = discovery.gateway_ip or host
                self._session_store.save(target_key, username, password)
                if persist_in_windows_vault and self._win_cred_store.is_supported():
                    if self._win_cred_store.save(target_key, username, password):
                        result.credential_storage_mode = "windows_credential_manager"
            elif result.error_kind == "auth_rejected":
                # Only real credential rejections count toward router lockout protection
                fails = self._failed_attempts.get(host, 0) + 1
                self._failed_attempts[host] = fails
                if fails >= 2:
                    result.lockout_risk_warning = (
                        f"Authentication failed ({fails}x). Many ISP routers enforce a cooldown or lockout after 3 failures."
                    )

        # Guarantee sanitized failure messages (never echo password)
        result.message = redact_secrets(result.message, extra_secrets=[password])
        return result

    def load_saved_credentials(self, gateway_ip: str) -> Optional[tuple[str, str]]:
        sess = self._session_store.load(gateway_ip)
        if sess is not None:
            return sess
        return self._win_cred_store.load(gateway_ip)

    def clear_saved_credentials(self, gateway_ip: str) -> None:
        self._session_store.delete(gateway_ip)
        self._win_cred_store.delete(gateway_ip)

    def clear_session_credentials(self, gateway_ip: Optional[str] = None) -> None:
        """Clear volatile in-memory session credentials without altering explicit Windows Vault entries."""
        if gateway_ip:
            self._session_store.delete(gateway_ip)
        else:
            self._session_store.clear()
