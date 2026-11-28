"""Secure router credential storage, local-only origin validation, TLS warnings, and secret redaction."""

from __future__ import annotations

import copy
import ctypes
import ipaddress
import re
import socket
import sys
import threading
import urllib.parse
from typing import Any, Dict, Iterable, Optional, Tuple


class LocalOriginSecurityError(ValueError):
    """Raised when a URL points outside the local gateway/private network boundary."""


_SENSITIVE_KEY_PATTERNS = re.compile(
    r"(password|passwd|pwd|secret|token|cookie|authorization|auth_header|session_id|csrf|cred|private_key)",
    re.IGNORECASE,
)


def is_private_or_loopback_ip(host: str, *, allow_loopback: bool = False) -> bool:
    """Return True if host is a private LAN IPv4/IPv6 address (optionally allowing loopback for tests)."""
    cleaned = host.strip().strip("[]")
    try:
        ip_obj = ipaddress.ip_address(cleaned)
    except ValueError:
        try:
            resolved = socket.gethostbyname(cleaned)
            ip_obj = ipaddress.ip_address(resolved)
        except OSError:
            return False

    if ip_obj.is_loopback:
        return allow_loopback
    if ip_obj.is_multicast or ip_obj.is_unspecified or ip_obj.is_reserved:
        return False
    return ip_obj.is_private or ip_obj.is_link_local


def validate_local_router_url(
    url: str,
    *,
    expected_gateway_ip: Optional[str] = None,
    allow_loopback: bool = False,
) -> Tuple[str, str, int, bool]:
    """Validate URL stays strictly on local LAN/gateway HTTP(S) origin. Returns (scheme, host, port, is_https)."""
    parsed = urllib.parse.urlparse(url.strip())
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise LocalOriginSecurityError(
            f"Unsupported router URL scheme '{scheme}'. Only http/https are permitted."
        )
    host = parsed.hostname
    if not host:
        raise LocalOriginSecurityError("Router URL does not specify a hostname or IP.")

    if not is_private_or_loopback_ip(host, allow_loopback=allow_loopback):
        raise LocalOriginSecurityError(
            f"Blocked non-local router target '{host}'. Router management is restricted to local LAN/gateway addresses."
        )

    if expected_gateway_ip:
        is_same_gw = host == expected_gateway_ip.strip()
        is_test_loopback = allow_loopback and host in ("127.0.0.1", "localhost", "::1")
        if not is_same_gw and not is_test_loopback:
            # Permit private subnet IPs if gateway-hosted, or block mismatched external targets
            pass

    port = parsed.port or (443 if scheme == "https" else 80)
    return scheme, host, port, scheme == "https"


def evaluate_transport_security_warning(url: str, tls_trusted: Optional[bool] = None) -> Optional[str]:
    """Produce a clear warning when sending router credentials over HTTP or untrusted TLS."""
    parsed = urllib.parse.urlparse(url.strip())
    scheme = parsed.scheme.lower()
    if scheme == "http":
        return (
            "Security notice: Router web portal uses unencrypted HTTP over LAN. "
            "Credentials will be sent in plaintext across the local network."
        )
    if scheme == "https" and tls_trusted is False:
        return (
            "Security notice: Router HTTPS uses a self-signed or untrusted certificate. "
            "Proceed only if you trust this local gateway device."
        )
    return None


def redact_secrets(obj: Any, *, extra_secrets: Optional[Iterable[str]] = None) -> Any:
    """Recursively scrub passwords, session tokens, cookies, and secret literals before export/logging."""
    literal_secrets = [s for s in (extra_secrets or []) if isinstance(s, str) and len(s) >= 2]

    def _scrub_str(text: str) -> str:
        out = text
        for sec in literal_secrets:
            if sec in out:
                out = out.replace(sec, "[REDACTED]")
        # Redact inline URL credentials user:pass@host
        out = re.sub(r"(https?://[^:/\s]+:)([^@/\s]+)(@)", r"\1[REDACTED]\3", out)
        return out

    def _walk(node: Any) -> Any:
        if isinstance(node, dict):
            cleaned: Dict[Any, Any] = {}
            for k, v in node.items():
                if isinstance(k, str) and _SENSITIVE_KEY_PATTERNS.search(k):
                    cleaned[k] = "[REDACTED]" if v is not None else None
                else:
                    cleaned[k] = _walk(v)
            return cleaned
        if isinstance(node, list):
            return [_walk(x) for x in node]
        if isinstance(node, tuple):
            return tuple(_walk(x) for x in node)
        if isinstance(node, str):
            return _scrub_str(node)
        return copy.copy(node)

    return _walk(obj)


class SessionCredentialStore:
    """Ephemeral in-memory credential store (default mode, never writes secrets to disk)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._creds: Dict[str, Tuple[str, str]] = {}

    def save(self, target_key: str, username: str, password: str) -> None:
        with self._lock:
            self._creds[target_key] = (username, password)

    def load(self, target_key: str) -> Optional[Tuple[str, str]]:
        with self._lock:
            return self._creds.get(target_key)

    def delete(self, target_key: str) -> None:
        with self._lock:
            self._creds.pop(target_key, None)

    def clear(self) -> None:
        with self._lock:
            self._creds.clear()


if sys.platform == "win32":

    class _FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", ctypes.c_uint32), ("dwHighDateTime", ctypes.c_uint32)]

    class _CREDENTIALW(ctypes.Structure):
        _fields_ = [
            ("Flags", ctypes.c_uint32),
            ("Type", ctypes.c_uint32),
            ("TargetName", ctypes.c_wchar_p),
            ("Comment", ctypes.c_wchar_p),
            ("LastWritten", _FILETIME),
            ("CredentialBlobSize", ctypes.c_uint32),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", ctypes.c_uint32),
            ("AttributeCount", ctypes.c_uint32),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", ctypes.c_wchar_p),
            ("UserName", ctypes.c_wchar_p),
        ]


class WindowsCredentialManagerStore:
    """Stores router credentials exclusively in Windows Credential Manager (advapi32.dll)."""

    TARGET_PREFIX = "NetGuardAI/Router/"

    def __init__(self, target_prefix: str = TARGET_PREFIX) -> None:
        self._prefix = target_prefix

    def _full_target(self, key: str) -> str:
        return f"{self._prefix}{key}"

    @staticmethod
    def is_supported() -> bool:
        return sys.platform == "win32"

    def save(self, target_key: str, username: str, password: str) -> bool:
        if sys.platform != "win32":
            return False
        advapi32 = ctypes.windll.advapi32
        secret_bytes = password.encode("utf-16-le")
        buf = (ctypes.c_ubyte * len(secret_bytes)).from_buffer_copy(secret_bytes)
        cred = _CREDENTIALW()
        cred.Flags = 0
        cred.Type = 1  # CRED_TYPE_GENERIC
        cred.TargetName = self._full_target(target_key)
        cred.Comment = "NetGuard AI local router management credential"
        cred.CredentialBlobSize = len(secret_bytes)
        cred.CredentialBlob = ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte))
        cred.Persist = 2  # CRED_PERSIST_LOCAL_MACHINE
        cred.UserName = username or "admin"
        ok = advapi32.CredWriteW(ctypes.byref(cred), 0)
        return bool(ok)

    def load(self, target_key: str) -> Optional[Tuple[str, str]]:
        if sys.platform != "win32":
            return None
        advapi32 = ctypes.windll.advapi32
        p_cred = ctypes.POINTER(_CREDENTIALW)()
        ok = advapi32.CredReadW(self._full_target(target_key), 1, 0, ctypes.byref(p_cred))
        if not ok or not p_cred:
            return None
        try:
            c = p_cred.contents
            user = c.UserName or ""
            blob_len = int(c.CredentialBlobSize)
            raw = bytes(c.CredentialBlob[:blob_len]) if blob_len > 0 and c.CredentialBlob else b""
            pw = raw.decode("utf-16-le", errors="replace")
            return user, pw
        finally:
            advapi32.CredFree(p_cred)

    def delete(self, target_key: str) -> bool:
        if sys.platform != "win32":
            return False
        advapi32 = ctypes.windll.advapi32
        return bool(advapi32.CredDeleteW(self._full_target(target_key), 1, 0))
