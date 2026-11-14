"""Windows 10/11 Platform Adapter for Network Operations."""

from __future__ import annotations
import ipaddress
import re
import socket
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple, Set
import psutil
from app.platform.interfaces import IPlatformAdapter


class WindowsPlatformAdapter(IPlatformAdapter):
    """Windows-specific implementation using allowlisted system commands and native sockets."""

    def __init__(self) -> None:
        self._cached_gateway: Optional[str] = None
        self._cached_interface: Optional[str] = None

    def is_elevated(self) -> bool:
        """Check whether the current running process has administrator privileges on Windows."""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def get_default_gateway(self) -> Optional[str]:
        """Parse default IPv4 gateway via route print or ipconfig."""
        try:
            # First attempt: route print 0.0.0.0
            proc = subprocess.run(
                ["route", "print", "0.0.0.0"],
                capture_output=True,
                text=True,
                timeout=3.0,
                check=False,
            )
            for line in proc.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                    gateway_candidate = parts[2]
                    try:
                        ipaddress.IPv4Address(gateway_candidate)
                        self._cached_gateway = gateway_candidate
                        return gateway_candidate
                    except ValueError:
                        continue
        except Exception:
            pass

        # Fallback: scan active interfaces in psutil
        try:
            gateways = psutil.net_if_stats()
            # If still nothing, return cached
            return self._cached_gateway
        except Exception:
            return self._cached_gateway

    def get_primary_interface(self) -> Optional[str]:
        """Detect the primary network adapter name currently routing default traffic."""
        try:
            proc = subprocess.run(
                ["route", "print", "0.0.0.0"],
                capture_output=True,
                text=True,
                timeout=3.0,
                check=False,
            )
            interface_ip = None
            for line in proc.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                    interface_ip = parts[3]
                    break

            if interface_ip:
                # Match interface_ip to an adapter name in psutil.net_if_addrs
                for iface_name, addrs in psutil.net_if_addrs().items():
                    for addr in addrs:
                        if addr.family == socket.AF_INET and addr.address == interface_ip:
                            self._cached_interface = iface_name
                            return iface_name
        except Exception:
            pass

        # Fallback to first non-loopback active interface
        for iface_name, stats in psutil.net_if_stats().items():
            if stats.isup and "loopback" not in iface_name.lower():
                self._cached_interface = iface_name
                return iface_name
        return self._cached_interface

    def ping(self, target: str, timeout_sec: float = 1.5) -> Tuple[bool, float]:
        """Execute Windows ping command with single echo and millisecond timeout."""
        # Sanitize target to ensure valid IP or hostname
        if not re.match(r"^[a-zA-Z0-9\.\-_:]+$", target):
            return False, 0.0

        timeout_ms = max(int(timeout_sec * 1000), 100)
        start_time = time.perf_counter()
        try:
            proc = subprocess.run(
                ["ping", "-n", "1", "-w", str(timeout_ms), target],
                capture_output=True,
                text=True,
                timeout=timeout_sec + 1.0,
                check=False,
            )
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            if proc.returncode == 0:
                # Search for time=XXms or time<1ms
                match = re.search(r"time[=<]([0-9]+)ms", proc.stdout, re.IGNORECASE)
                if match:
                    reported_ms = float(match.group(1))
                    return True, reported_ms
                return True, max(duration_ms, 0.1)
            return False, 0.0
        except (subprocess.TimeoutExpired, Exception):
            return False, 0.0

    def tcp_connect(self, target: str, port: int = 80, timeout_sec: float = 2.0) -> Tuple[bool, float]:
        """Attempt socket TCP 3-way handshake to target:port."""
        start_time = time.perf_counter()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout_sec)
        try:
            sock.connect((target, port))
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return True, duration_ms
        except Exception:
            return False, 0.0
        finally:
            sock.close()

    def flush_dns_cache(self) -> Tuple[bool, str]:
        """Flush the DNS Resolver Cache via native Win32 Dnsapi, PowerShell, or ipconfig."""
        # 1. Native Win32 API (Works without requiring elevation)
        try:
            import ctypes
            res = ctypes.windll.dnsapi.DnsFlushResolverCache()
            if res == 1:
                return True, "Successfully flushed the DNS Resolver Cache via Win32 Dnsapi."
        except Exception:
            pass

        # 2. PowerShell Clear-DnsClientCache
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Clear-DnsClientCache"],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
            )
            if proc.returncode == 0:
                return True, "Successfully flushed DNS Cache via PowerShell Clear-DnsClientCache."
        except Exception:
            pass

        # 3. Fallback: ipconfig /flushdns
        try:
            proc = subprocess.run(
                ["ipconfig", "/flushdns"],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
            )
            if proc.returncode == 0:
                return True, "Successfully flushed the DNS Resolver Cache."
            return False, proc.stderr or proc.stdout
        except Exception as exc:
            return False, str(exc)

    def get_interface_dns_servers(self, interface_name: str) -> List[str]:
        """Query configured DNS servers for the specified interface."""
        try:
            proc = subprocess.run(
                ["netsh", "interface", "ip", "show", "dns", f"name={interface_name}"],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
            )
            servers = []
            for line in proc.stdout.splitlines():
                matches = re.findall(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", line)
                for ip in matches:
                    if ip not in servers and not ip.startswith("0."):
                        servers.append(ip)
            return servers
        except Exception:
            return []

    def set_interface_dns_servers(self, interface_name: str, servers: List[str]) -> Tuple[bool, str]:
        """Configure primary and secondary static DNS or DHCP."""
        if not servers:
            # Set to DHCP
            try:
                proc = subprocess.run(
                    ["netsh", "interface", "ip", "set", "dns", f"name={interface_name}", "source=dhcp"],
                    capture_output=True,
                    text=True,
                    timeout=8.0,
                    check=False,
                )
                return proc.returncode == 0, proc.stdout or proc.stderr
            except Exception as exc:
                return False, str(exc)

        # Set primary static DNS
        primary = servers[0]
        try:
            proc = subprocess.run(
                ["netsh", "interface", "ip", "set", "dns", f"name={interface_name}", "static", primary, "primary"],
                capture_output=True,
                text=True,
                timeout=8.0,
                check=False,
            )
            if proc.returncode != 0:
                return False, proc.stderr or proc.stdout

            # Add subsequent servers as index=2, 3...
            for idx, secondary in enumerate(servers[1:], start=2):
                subprocess.run(
                    ["netsh", "interface", "ip", "add", "dns", f"name={interface_name}", secondary, f"index={idx}"],
                    capture_output=True,
                    text=True,
                    timeout=5.0,
                    check=False,
                )
            return True, f"Configured DNS to {', '.join(servers)}"
        except Exception as exc:
            return False, str(exc)

    def renew_ip_lease(self, interface_name: str) -> Tuple[bool, str]:
        """Request DHCP lease refresh for the active interface."""
        if not self.is_elevated():
            return False, "DHCP renewal requires Windows Administrator privileges."

        try:
            # Request renewal without releasing first to preserve current connectivity
            proc = subprocess.run(
                ["ipconfig", "/renew", interface_name],
                capture_output=True,
                text=True,
                timeout=12.0,
                check=False,
            )
            if proc.returncode == 0:
                return True, "DHCP lease renewed successfully."
            return False, proc.stderr or proc.stdout
        except Exception as exc:
            return False, str(exc)

    def get_wifi_metrics(self, interface_name: Optional[str] = None) -> Dict[str, Any]:
        """Parse netsh wlan show interfaces for signal percentage, SSID, and rate."""
        metrics: Dict[str, Any] = {
            "is_wifi": False,
            "signal_percent": 0.0,
            "ssid": None,
            "bssid": None,
            "rx_rate_mbps": 0.0,
            "tx_rate_mbps": 0.0,
        }
        try:
            proc = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                timeout=4.0,
                check=False,
            )
            if proc.returncode == 0:
                metrics["is_wifi"] = True
                for line in proc.stdout.splitlines():
                    line = line.strip()
                    if ":" not in line:
                        continue
                    key, val = [p.strip() for p in line.split(":", 1)]
                    if "Signal" in key:
                        val_num = val.replace("%", "").strip()
                        if val_num.isdigit():
                            metrics["signal_percent"] = float(val_num)
                    elif "SSID" in key and "BSSID" not in key:
                        metrics["ssid"] = val
                    elif "BSSID" in key:
                        metrics["bssid"] = val
                    elif "Receive rate" in key:
                        m = re.search(r"([0-9\.]+)", val)
                        if m:
                            metrics["rx_rate_mbps"] = float(m.group(1))
                    elif "Transmit rate" in key:
                        m = re.search(r"([0-9\.]+)", val)
                        if m:
                            metrics["tx_rate_mbps"] = float(m.group(1))
        except Exception:
            pass
        return metrics
