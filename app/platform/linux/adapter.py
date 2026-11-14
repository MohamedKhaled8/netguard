"""Linux Platform Adapter for Network Operations."""

from __future__ import annotations
import socket
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple
from app.platform.interfaces import IPlatformAdapter


class LinuxPlatformAdapter(IPlatformAdapter):
    """Linux implementation using iproute2, /proc/net, and native sockets."""

    def is_elevated(self) -> bool:
        try:
            import os
            return os.geteuid() == 0
        except Exception:
            return False

    def get_default_gateway(self) -> Optional[str]:
        try:
            with open("/proc/net/route", "r", encoding="utf-8") as f:
                for line in f.readlines()[1:]:
                    fields = line.strip().split()
                    if len(fields) >= 3 and fields[1] == "00000000":
                        gw_hex = fields[2]
                        # Convert little-endian hex to IP
                        gw_int = int(gw_hex, 16)
                        return socket.inet_ntoa(gw_int.to_bytes(4, byteorder="little"))
        except Exception:
            pass
        return None

    def get_primary_interface(self) -> Optional[str]:
        try:
            proc = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True, timeout=2.0)
            parts = proc.stdout.strip().split()
            if "dev" in parts:
                idx = parts.index("dev")
                if idx + 1 < len(parts):
                    return parts[idx + 1]
        except Exception:
            pass
        return None

    def ping(self, target: str, timeout_sec: float = 1.5) -> Tuple[bool, float]:
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                ["ping", "-c", "1", "-W", str(max(int(timeout_sec), 1)), target],
                capture_output=True,
                text=True,
                timeout=timeout_sec + 0.5,
            )
            duration_ms = (time.perf_counter() - start) * 1000.0
            return proc.returncode == 0, duration_ms
        except Exception:
            return False, 0.0

    def tcp_connect(self, target: str, port: int = 80, timeout_sec: float = 2.0) -> Tuple[bool, float]:
        start = time.perf_counter()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout_sec)
        try:
            sock.connect((target, port))
            return True, (time.perf_counter() - start) * 1000.0
        except Exception:
            return False, 0.0
        finally:
            sock.close()

    def flush_dns_cache(self) -> Tuple[bool, str]:
        # Try systemd-resolved
        try:
            proc = subprocess.run(["resolvectl", "flush-caches"], capture_output=True, text=True, timeout=3.0)
            if proc.returncode == 0:
                return True, "Flushed systemd-resolved cache."
        except Exception:
            pass
        return False, "systemd-resolved not available."

    def get_interface_dns_servers(self, interface_name: str) -> List[str]:
        servers = []
        try:
            with open("/etc/resolv.conf", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("nameserver"):
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            servers.append(parts[1])
        except Exception:
            pass
        return servers

    def set_interface_dns_servers(self, interface_name: str, servers: List[str]) -> Tuple[bool, str]:
        return False, "DNS modification on Linux requires NetworkManager/systemd-resolved privileges."

    def renew_ip_lease(self, interface_name: str) -> Tuple[bool, str]:
        return False, "DHCP renewal on Linux requires dhclient/NetworkManager privileges."

    def get_wifi_metrics(self, interface_name: Optional[str] = None) -> Dict[str, Any]:
        return {"is_wifi": False, "signal_percent": 0.0}
