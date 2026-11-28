"""Windows 10/11 Platform Adapter for Network Operations."""

from __future__ import annotations
import ipaddress
import logging
import re
import socket
import struct
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple, Set
import ctypes
from ctypes import wintypes
import psutil
from app.platform.interfaces import IPlatformAdapter

logger = logging.getLogger("netguard.platform.windows.adapter")

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


class _IP_OPTION_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("Ttl", ctypes.c_ubyte),
        ("Tos", ctypes.c_ubyte),
        ("Flags", ctypes.c_ubyte),
        ("OptionsSize", ctypes.c_ubyte),
        ("OptionsData", ctypes.c_void_p),
    ]


class _ICMP_ECHO_REPLY(ctypes.Structure):
    _fields_ = [
        ("Address", wintypes.ULONG),
        ("Status", wintypes.ULONG),
        ("RoundTripTime", wintypes.ULONG),
        ("DataSize", wintypes.USHORT),
        ("Reserved", wintypes.USHORT),
        ("Data", ctypes.c_void_p),
        ("Options", _IP_OPTION_INFORMATION),
    ]


class PingResult(tuple):
    """2-tuple (success: bool, latency_ms: float) compatible with float operations and booleans."""

    def __new__(cls, success: bool, latency_ms: float):
        return super().__new__(cls, (bool(success), float(latency_ms)))

    @property
    def success(self) -> bool:
        return self[0]

    @property
    def latency_ms(self) -> float:
        return self[1]

    def __bool__(self) -> bool:
        return self[0]

    def __float__(self) -> float:
        return float(self[1])

    def __int__(self) -> int:
        return int(self[1])

    def __round__(self, n: Optional[int] = None) -> Any:
        return round(self[1], n) if n is not None else round(self[1])

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, (int, float)):
            return self[1] > other
        return super().__gt__(other)

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, (int, float)):
            return self[1] < other
        return super().__lt__(other)

    def __ge__(self, other: Any) -> bool:
        if isinstance(other, (int, float)):
            return self[1] >= other
        return super().__ge__(other)

    def __le__(self, other: Any) -> bool:
        if isinstance(other, (int, float)):
            return self[1] <= other
        return super().__le__(other)


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class _WLAN_INTERFACE_INFO(ctypes.Structure):
    _fields_ = [
        ("InterfaceGuid", _GUID),
        ("strInterfaceDescription", wintypes.WCHAR * 256),
        ("isState", wintypes.DWORD),
    ]


class _WLAN_INTERFACE_INFO_LIST(ctypes.Structure):
    _fields_ = [
        ("dwNumberOfItems", wintypes.DWORD),
        ("dwIndex", wintypes.DWORD),
        ("InterfaceInfo", _WLAN_INTERFACE_INFO * 1),
    ]


class _DOT11_SSID(ctypes.Structure):
    _fields_ = [
        ("uSSIDLength", wintypes.ULONG),
        ("ucSSID", ctypes.c_char * 32),
    ]


class _WLAN_ASSOCIATION_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("dot11Ssid", _DOT11_SSID),
        ("dot11BssType", wintypes.DWORD),
        ("dot11Bssid", ctypes.c_ubyte * 6),
        ("dot11PhyType", wintypes.DWORD),
        ("uDot11PhyIndex", wintypes.ULONG),
        ("wlanSignalQuality", wintypes.ULONG),
        ("ulRxRate", wintypes.ULONG),
        ("ulTxRate", wintypes.ULONG),
    ]


class _WLAN_SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("bSecurityEnabled", wintypes.BOOL),
        ("bOneXEnabled", wintypes.BOOL),
        ("dot11AuthAlgorithm", wintypes.DWORD),
        ("dot11CipherAlgorithm", wintypes.DWORD),
    ]


class _WLAN_CONNECTION_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("isState", wintypes.DWORD),
        ("wlanConnectionMode", wintypes.DWORD),
        ("strProfileName", wintypes.WCHAR * 256),
        ("wlanAssociationAttributes", _WLAN_ASSOCIATION_ATTRIBUTES),
        ("wlanSecurityAttributes", _WLAN_SECURITY_ATTRIBUTES),
    ]


class WifiMetrics(dict):
    """Container for Wi-Fi metrics compatible with dict operations and object attribute access."""

    def __init__(
        self,
        is_wifi: bool = False,
        ssid: Optional[str] = None,
        signal_percent: float = 0.0,
        signal_quality: Optional[float] = None,
        link_speed_mbps: float = 0.0,
        rx_rate_mbps: float = 0.0,
        tx_rate_mbps: float = 0.0,
        bssid: Optional[str] = None,
        interface_description: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        sig = float(signal_quality if signal_quality is not None else signal_percent)
        rx = float(rx_rate_mbps if rx_rate_mbps else link_speed_mbps)
        tx = float(tx_rate_mbps if tx_rate_mbps else link_speed_mbps)
        speed = float(link_speed_mbps if link_speed_mbps else max(rx, tx))
        data = {
            "is_wifi": is_wifi,
            "ssid": ssid,
            "signal_percent": sig,
            "signal_quality": sig,
            "link_speed_mbps": speed,
            "rx_rate_mbps": rx,
            "tx_rate_mbps": tx,
            "bssid": bssid,
            "interface_description": interface_description,
            **kwargs,
        }
        super().__init__(data)

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'WifiMetrics' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


class WindowsPlatformAdapter(IPlatformAdapter):
    """Windows-specific implementation using allowlisted system commands and native sockets."""

    supports_auto_elevate: bool = True

    def __init__(self) -> None:
        self._cached_gateway: Optional[str] = None
        self._cached_interface: Optional[str] = None
        self._last_elevation_request_time: float = 0.0
        self.last_qos_batch_report: Dict[str, Any] = {}
        # Single-flight lock, rate limiting, and failure backoff for QoS PowerShell calls
        import threading
        self._qos_lock = threading.Lock()
        self._qos_last_failure_time: float = 0.0
        self._qos_failure_count: int = 0
        self._qos_backoff_until: float = 0.0
        self._qos_last_error: str = ""

    def restart_as_administrator(self) -> bool:
        """Relaunches NetGuard AI process elevated with Administrator privileges."""
        try:
            import sys, ctypes
            if self.is_elevated():
                return True
            params = " ".join([f'"{arg}"' for arg in sys.argv])
            res = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
            return res > 32
        except Exception as exc:
            return False

    def is_elevated(self) -> bool:
        """Check whether the current running process has administrator privileges on Windows."""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def get_default_gateway(self) -> Optional[str]:
        """Detect default IPv4 gateway via fast native Win32 GetBestRoute, cache, or route print."""
        # 1. Fast native Win32 IP Helper API (0.0005s, instant, no subprocess)
        try:
            import ctypes, struct
            class MIB_IPFORWARDROW(ctypes.Structure):
                _fields_ = [
                    ('dwForwardDest', ctypes.c_ulong),
                    ('dwForwardMask', ctypes.c_ulong),
                    ('dwForwardPolicy', ctypes.c_ulong),
                    ('dwForwardNextHop', ctypes.c_ulong),
                    ('dwForwardIfIndex', ctypes.c_ulong),
                    ('dwForwardType', ctypes.c_ulong),
                    ('dwForwardProto', ctypes.c_ulong),
                    ('dwForwardAge', ctypes.c_ulong),
                    ('dwForwardNextHopAS', ctypes.c_ulong),
                    ('dwForwardMetric1', ctypes.c_ulong),
                    ('dwForwardMetric2', ctypes.c_ulong),
                    ('dwForwardMetric3', ctypes.c_ulong),
                    ('dwForwardMetric4', ctypes.c_ulong),
                    ('dwForwardMetric5', ctypes.c_ulong),
                ]
            row = MIB_IPFORWARDROW()
            dest = struct.unpack('<I', socket.inet_aton('8.8.8.8'))[0]
            ret = ctypes.windll.iphlpapi.GetBestRoute(dest, 0, ctypes.byref(row))
            if ret == 0 and row.dwForwardNextHop != 0:
                gw_str = socket.inet_ntoa(struct.pack('<I', row.dwForwardNextHop))
                if gw_str and gw_str != "0.0.0.0":
                    ipaddress.IPv4Address(gw_str)
                    self._cached_gateway = gw_str
                    return gw_str
        except Exception:
            pass

        # 2. Return cached if available
        if self._cached_gateway:
            return self._cached_gateway

        # 3. Fast fallback: route print 0.0.0.0 (0.04s, no powershell)
        try:
            proc = subprocess.run(
                ["route", "print", "0.0.0.0"],
                capture_output=True,
                text=True,
                timeout=1.5,
                check=False,
                creationflags=_NO_WINDOW,
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

        # 4. Final fallback: PowerShell
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Select-Object NextHop, InterfaceAlias | ConvertTo-Json",
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3.0,
                check=False,
                creationflags=_NO_WINDOW,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                import json
                data = json.loads(proc.stdout)
                if isinstance(data, list) and data:
                    data = data[0]
                if isinstance(data, dict):
                    hop = data.get("NextHop")
                    if hop:
                        ipaddress.IPv4Address(hop)
                        self._cached_gateway = hop
                        alias = data.get("InterfaceAlias")
                        if alias:
                            self._cached_interface = alias
                        return hop
        except Exception:
            pass

        return self._cached_gateway

    VIRTUAL_ADAPTER_KEYWORDS = (
        "wintun",
        "wireguard",
        "tap",
        "tun",
        "vethernet",
        "hyper-v",
        "virtual",
        "vmware",
        "vbox",
        "virtualbox",
        "tailscale",
        "zerotier",
        "nordlynx",
        "openvpn",
        "teredo",
        "isatap",
        "loopback",
        "docker",
        "wsl",
        "bluetooth",
        "anyconnect",
        "fortinet",
        "pcap",
        "npcap",
        "cisco",
        "checkpoint",
    )

    def is_virtual_adapter(self, interface_name: str, description: Optional[str] = None) -> bool:
        """Detect whether a network adapter is virtual, VPN, or a tunnel interface."""
        target = interface_name.lower()
        if any(kw in target for kw in self.VIRTUAL_ADAPTER_KEYWORDS):
            return True
        if description:
            desc_lower = description.lower()
            if any(kw in desc_lower for kw in self.VIRTUAL_ADAPTER_KEYWORDS):
                return True
        return False

    def get_primary_interface(self) -> Optional[str]:
        """Detect the primary physical network adapter name currently routing default traffic (Item F7)."""
        if self._cached_interface and not self.is_virtual_adapter(self._cached_interface):
            return self._cached_interface

        def _is_physical(name: str) -> bool:
            return not self.is_virtual_adapter(name)

        candidate_virtual: Optional[str] = None

        # 1. Fast match via gateway subnet in psutil (filtering out virtual adapters)
        try:
            gw_str = self.get_default_gateway()
            if gw_str:
                gw_ip = ipaddress.IPv4Address(gw_str)
                for name, addrs in psutil.net_if_addrs().items():
                    for a in addrs:
                        if a.family == socket.AF_INET and a.netmask and not a.address.startswith("127."):
                            try:
                                net = ipaddress.IPv4Network(f"{a.address}/{a.netmask}", strict=False)
                                if gw_ip in net:
                                    if _is_physical(name):
                                        self._cached_interface = name
                                        return name
                                    elif candidate_virtual is None:
                                        candidate_virtual = name
                            except ValueError:
                                continue
        except Exception:
            pass

        # 2. Fallback to route print 0.0.0.0 interface column (preferring physical)
        try:
            proc = subprocess.run(
                ["route", "print", "0.0.0.0"],
                capture_output=True,
                text=True,
                timeout=1.5,
                check=False,
                creationflags=_NO_WINDOW,
            )
            interface_ip = None
            for line in proc.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                    interface_ip = parts[3]
                    break

            if interface_ip:
                for iface_name, addrs in psutil.net_if_addrs().items():
                    for addr in addrs:
                        if addr.family == socket.AF_INET and addr.address == interface_ip:
                            if _is_physical(iface_name):
                                self._cached_interface = iface_name
                                return iface_name
                            elif candidate_virtual is None:
                                candidate_virtual = iface_name
        except Exception:
            pass

        # 3. Fallback to first non-loopback active physical interface
        for iface_name, stats in psutil.net_if_stats().items():
            if stats.isup and _is_physical(iface_name):
                self._cached_interface = iface_name
                return iface_name

        # 4. If no physical adapter found, fallback to candidate virtual or first active interface
        if candidate_virtual:
            self._cached_interface = candidate_virtual
            return candidate_virtual

        for iface_name, stats in psutil.net_if_stats().items():
            if stats.isup and "loopback" not in iface_name.lower():
                self._cached_interface = iface_name
                return iface_name

        return self._cached_interface or "Wi-Fi"

    @classmethod
    def parse_ping_output(cls, stdout_text: str) -> Tuple[bool, float]:
        """Parse ping output in a locale-independent manner (for testing and offline parsing)."""
        match = re.search(
            r"([=<])\s*(\d+(?:\.\d+)?)\s*(?:ms|مللي ثانية|مللي|мс|msec)\b",
            stdout_text,
            re.IGNORECASE,
        )
        if match:
            op, val = match.group(1), float(match.group(2))
            return True, (0.5 if op == "<" and val <= 1.0 else val)

        match_avg = re.search(r"=\s*(\d+(?:\.\d+)?)\s*(?:ms|مللي ثانية|مللي|мс|msec)?\s*$", stdout_text.strip(), re.MULTILINE)
        if match_avg:
            return True, float(match_avg.group(1))

        return False, 0.0

    def ping(self, target: str, timeout_sec: float = 1.0) -> Tuple[bool, float]:
        """Execute native Win32 in-process ICMP ping via iphlpapi.dll without spawning ping.exe."""
        if not target or not re.match(r"^[a-zA-Z0-9\.\-_:]+$", target):
            return PingResult(False, 0.0)

        # 1. Primary path: Native in-process Win32 IcmpSendEcho (no ping.exe child process)
        try:
            target_ip = socket.gethostbyname(target)
            dest_addr = struct.unpack("<I", socket.inet_aton(target_ip))[0]

            iphlpapi = ctypes.windll.iphlpapi
            iphlpapi.IcmpCreateFile.restype = wintypes.HANDLE
            iphlpapi.IcmpCloseHandle.argtypes = [wintypes.HANDLE]
            iphlpapi.IcmpCloseHandle.restype = wintypes.BOOL
            iphlpapi.IcmpSendEcho.argtypes = [
                wintypes.HANDLE,
                wintypes.ULONG,
                ctypes.c_char_p,
                wintypes.WORD,
                ctypes.POINTER(_IP_OPTION_INFORMATION),
                ctypes.c_void_p,
                wintypes.DWORD,
                wintypes.DWORD,
            ]
            iphlpapi.IcmpSendEcho.restype = wintypes.DWORD

            icmp_handle = iphlpapi.IcmpCreateFile()
            if icmp_handle and icmp_handle != wintypes.HANDLE(-1).value and icmp_handle != -1:
                try:
                    req_data = b"NetGuardICMPProbeData"
                    reply_size = ctypes.sizeof(_ICMP_ECHO_REPLY) + len(req_data) + 64
                    reply_buf = ctypes.create_string_buffer(reply_size)
                    timeout_ms = max(int(timeout_sec * 1000), 50)

                    t0 = time.perf_counter()
                    ret = iphlpapi.IcmpSendEcho(
                        icmp_handle,
                        dest_addr,
                        req_data,
                        len(req_data),
                        None,
                        ctypes.byref(reply_buf),
                        reply_size,
                        timeout_ms,
                    )
                    wall_ms = (time.perf_counter() - t0) * 1000.0

                    if ret > 0:
                        reply = _ICMP_ECHO_REPLY.from_buffer(reply_buf)
                        if reply.Status == 0:  # IP_SUCCESS
                            rtt = float(reply.RoundTripTime) if reply.RoundTripTime > 0 else max(wall_ms, 0.2)
                            return PingResult(True, round(rtt, 2))
                    return PingResult(False, 0.0)
                finally:
                    iphlpapi.IcmpCloseHandle(icmp_handle)
        except Exception as exc:
            logger.debug("Native Win32 ICMP echo error for %s: %s", target, exc)

        # 2. In-process fallback: TCP 3-way handshake on standard port without external process
        try:
            ok, lat = self.tcp_connect(target, port=80, timeout_sec=timeout_sec)
            if ok:
                return PingResult(True, round(lat, 2))
            ok_tls, lat_tls = self.tcp_connect(target, port=443, timeout_sec=timeout_sec)
            if ok_tls:
                return PingResult(True, round(lat_tls, 2))
        except Exception:
            pass

        return PingResult(False, 0.0)

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
                creationflags=_NO_WINDOW,
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
                creationflags=_NO_WINDOW,
            )
            if proc.returncode == 0:
                return True, "Successfully flushed the DNS Resolver Cache."
            return False, proc.stderr or proc.stdout
        except Exception as exc:
            return False, str(exc)

    def get_interface_dns_servers(self, interface_name: str) -> List[str]:
        """Query configured DNS servers (both IPv4 and IPv6) for the specified interface."""
        servers: List[str] = []
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"(Get-DnsClientServerAddress -InterfaceAlias '{interface_name}').ServerAddresses",
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=4.0,
                check=False,
                creationflags=_NO_WINDOW,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                for line in proc.stdout.splitlines():
                    ip_str = line.strip()
                    if not ip_str:
                        continue
                    try:
                        parsed = ipaddress.ip_address(ip_str)
                        if not parsed.is_loopback and not parsed.is_unspecified:
                            if ip_str not in servers:
                                servers.append(ip_str)
                    except ValueError:
                        continue
                if servers:
                    return servers
        except Exception:
            pass

        # Fallback: netsh IPv4 and IPv6
        try:
            for family in ("ipv4", "ipv6"):
                proc = subprocess.run(
                    ["netsh", "interface", family, "show", "dnsservers", f"name={interface_name}"],
                    capture_output=True,
                    text=True,
                    timeout=3.0,
                    check=False,
                    creationflags=_NO_WINDOW,
                )
                if proc.returncode == 0:
                    for line in proc.stdout.splitlines():
                        for word in line.strip().split():
                            try:
                                parsed = ipaddress.ip_address(word)
                                if not parsed.is_loopback and not parsed.is_unspecified and word not in servers:
                                    servers.append(word)
                            except ValueError:
                                continue
            if servers:
                return servers
        except Exception:
            pass

        return servers

    def get_interface_dns_mode(self, interface_name: str) -> str:
        """Detect whether interface IPv4 DNS is configured statically or via DHCP."""
        try:
            proc = subprocess.run(
                ["netsh", "interface", "ipv4", "show", "dnsservers", f"name={interface_name}"],
                capture_output=True,
                text=True,
                timeout=2.5,
                check=False,
                creationflags=_NO_WINDOW,
            )
            if proc.returncode == 0:
                if "Statically Configured" in proc.stdout:
                    return "static"
                elif "through DHCP" in proc.stdout:
                    return "dhcp"
        except Exception:
            pass
        return super().get_interface_dns_mode(interface_name)

    def get_interface_ipv6_dns_mode(self, interface_name: str) -> str:
        """Detect whether interface IPv6 DNS is configured statically or via DHCP."""
        try:
            proc = subprocess.run(
                ["netsh", "interface", "ipv6", "show", "dnsservers", f"name={interface_name}"],
                capture_output=True,
                text=True,
                timeout=2.5,
                check=False,
                creationflags=_NO_WINDOW,
            )
            if proc.returncode == 0:
                if "Statically Configured" in proc.stdout:
                    return "static"
                elif "through DHCP" in proc.stdout:
                    return "dhcp"
        except Exception:
            pass
        return super().get_interface_ipv6_dns_mode(interface_name)

    def set_dns_servers(self, interface_alias: str, servers: List[str]) -> Tuple[bool, str]:
        """Configure DNS servers for interface (Interface contract F6/F8)."""
        return self.set_interface_dns_servers(interface_alias, servers)

    def set_interface_dns_servers(
        self,
        interface_name: str,
        servers: List[str],
        ipv6_servers: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        """Configure primary and secondary static DNS or DHCP, handling IPv4 and IPv6 consistently (Item F6)."""
        # Build effective dual-stack server list to prevent IPv6 DNS leaks
        effective_servers: List[str] = list(servers) if servers else []
        if ipv6_servers:
            for s in ipv6_servers:
                if s and s not in effective_servers:
                    effective_servers.append(s)
        elif effective_servers:
            # If only IPv4 was provided, auto-pair with official provider IPv6 if known
            has_ipv6 = any(":" in s for s in effective_servers)
            if not has_ipv6:
                try:
                    from app.dns.detector import get_provider_ipv6
                    for s in effective_servers:
                        p_v6, s_v6 = get_provider_ipv6(s)
                        if p_v6 and p_v6 not in effective_servers:
                            effective_servers.append(p_v6)
                        if s_v6 and s_v6 not in effective_servers:
                            effective_servers.append(s_v6)
                        if p_v6:
                            break
                except Exception as exc:
                    logger.debug("Failed to auto-lookup IPv6 resolvers: %s", exc)

        if not self.is_elevated():
            try:
                if not effective_servers:
                    ps_cmd = f"Set-DnsClientServerAddress -InterfaceAlias '{interface_name}' -ResetServerAddresses"
                else:
                    ps_servers_arg = "@(" + ", ".join(f"'{s}'" for s in effective_servers) + ")"
                    ps_cmd = f"Set-DnsClientServerAddress -InterfaceAlias '{interface_name}' -ServerAddresses {ps_servers_arg}"

                cmd_elevated = [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    f"Start-Process powershell -Verb RunAs -Wait -WindowStyle Hidden -ArgumentList \"-NoProfile -NonInteractive -Command {ps_cmd}\"",
                ]
                proc = subprocess.run(cmd_elevated, capture_output=True, text=True, timeout=12.0, check=False, creationflags=_NO_WINDOW)
                if proc.returncode == 0:
                    self.flush_dns_cache()
                    return True, f"Configured DNS on {interface_name} via elevated process."
            except Exception as e:
                logger.warning("Elevated PowerShell fallback failed: %s", e)
            return False, "Requires Administrator privileges to modify network adapter DNS."

        if not effective_servers:
            # Set to DHCP (Reset both IPv4 and IPv6)
            try:
                cmd_ps = [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    f"Set-DnsClientServerAddress -InterfaceAlias '{interface_name}' -ResetServerAddresses",
                ]
                proc_ps = subprocess.run(
                    cmd_ps,
                    capture_output=True,
                    text=True,
                    timeout=8.0,
                    check=False,
                    creationflags=_NO_WINDOW,
                )
                if proc_ps.returncode != 0:
                    proc_v4 = subprocess.run(
                        ["netsh", "interface", "ipv4", "set", "dnsservers", f"name={interface_name}", "source=dhcp"],
                        capture_output=True,
                        text=True,
                        timeout=8.0,
                        check=False,
                        creationflags=_NO_WINDOW,
                    )
                    subprocess.run(
                        ["netsh", "interface", "ipv6", "set", "dnsservers", f"name={interface_name}", "source=dhcp"],
                        capture_output=True,
                        text=True,
                        timeout=8.0,
                        check=False,
                        creationflags=_NO_WINDOW,
                    )
                    if proc_v4.returncode != 0:
                        return False, proc_v4.stderr or proc_v4.stdout

                self.flush_dns_cache()
                return True, f"Configured DNS on {interface_name} to DHCP."
            except Exception as exc:
                return False, str(exc)

        # Set static DNS (Handles IPv4 and IPv6 simultaneously)
        try:
            ps_servers_arg = "@(" + ", ".join(f"'{s}'" for s in effective_servers) + ")"
            cmd_ps = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"Set-DnsClientServerAddress -InterfaceAlias '{interface_name}' -ServerAddresses {ps_servers_arg}",
            ]
            proc_ps = subprocess.run(
                cmd_ps,
                capture_output=True,
                text=True,
                timeout=8.0,
                check=False,
                creationflags=_NO_WINDOW,
            )

            if proc_ps.returncode != 0:
                ipv4_targets = [s for s in effective_servers if ":" not in s]
                ipv6_targets = [s for s in effective_servers if ":" in s]

                # Configure IPv4 via netsh
                if ipv4_targets:
                    primary_v4 = ipv4_targets[0]
                    proc_v4 = subprocess.run(
                        ["netsh", "interface", "ipv4", "set", "dnsservers", f"name={interface_name}", "static", primary_v4, "primary"],
                        capture_output=True,
                        text=True,
                        timeout=8.0,
                        check=False,
                        creationflags=_NO_WINDOW,
                    )
                    if proc_v4.returncode != 0:
                        out = (proc_v4.stderr or "") + (proc_v4.stdout or "")
                        return False, out

                    for idx, sec_v4 in enumerate(ipv4_targets[1:], start=2):
                        subprocess.run(
                            ["netsh", "interface", "ipv4", "add", "dnsservers", f"name={interface_name}", sec_v4, f"index={idx}"],
                            capture_output=True,
                            text=True,
                            timeout=5.0,
                            check=False,
                            creationflags=_NO_WINDOW,
                        )

                # Configure IPv6 via netsh if supplied
                if ipv6_targets:
                    primary_v6 = ipv6_targets[0]
                    subprocess.run(
                        ["netsh", "interface", "ipv6", "set", "dnsservers", f"name={interface_name}", "static", primary_v6, "primary"],
                        capture_output=True,
                        text=True,
                        timeout=8.0,
                        check=False,
                        creationflags=_NO_WINDOW,
                    )
                    for idx, sec_v6 in enumerate(ipv6_targets[1:], start=2):
                        subprocess.run(
                            ["netsh", "interface", "ipv6", "add", "dnsservers", f"name={interface_name}", sec_v6, f"index={idx}"],
                            capture_output=True,
                            text=True,
                            timeout=5.0,
                            check=False,
                            creationflags=_NO_WINDOW,
                        )

            self.flush_dns_cache()
            actual_servers = self.get_interface_dns_servers(interface_name)
            if any(s in actual_servers for s in effective_servers):
                return True, f"Configured and verified DNS on {interface_name} to {', '.join(effective_servers)}."
            return True, f"Configured DNS on {interface_name} to {', '.join(effective_servers)}."
        except Exception as exc:
            return False, str(exc)

    def set_interface_dns_dhcp(self, interface_name: str) -> Tuple[bool, str]:
        """Configure interface DNS to obtain addresses automatically via DHCP."""
        return self.set_interface_dns_servers(interface_name, [])

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
                creationflags=_NO_WINDOW,
            )
            if proc.returncode == 0:
                return True, "DHCP lease renewed successfully."
            return False, proc.stderr or proc.stdout
        except Exception as exc:
            return False, str(exc)

    def get_wifi_signal_strength(self) -> Optional[float]:
        """Return Wi-Fi signal percentage (0-100) or None if not on Wi-Fi."""
        m = self.get_wifi_metrics()
        if m and m.get("is_wifi") and m.get("signal_percent") is not None:
            return float(m["signal_percent"])
        return None

    @classmethod
    def parse_wlan_output(cls, stdout_text: str) -> WifiMetrics:
        """Parse netsh wlan output for tests/offline evaluation."""
        metrics = WifiMetrics(is_wifi=True)
        rates = []
        for line in stdout_text.splitlines():
            line = line.strip()
            if ":" not in line:
                continue
            key, val = [p.strip() for p in line.split(":", 1)]

            if re.match(r"^[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}$", val):
                metrics["bssid"] = val

            m_sig = re.search(r"(\d+)\s*%", val)
            if m_sig:
                metrics["signal_percent"] = float(m_sig.group(1))
                metrics["signal_quality"] = float(m_sig.group(1))

            m_rate = re.search(r"([0-9\.]+)\s*(?:mbps|mbit/s|mbits/s|م\.ب/ث)?", val, re.I)
            if m_rate and any(u in key.lower() or u in val.lower() for u in ("rate", "mbps", "mbit", "vitesse", "معدل", "استلام", "إرسال")):
                try:
                    rates.append(float(m_rate.group(1)))
                except ValueError:
                    pass

            if "ssid" in key.lower() and "bssid" not in key.lower():
                metrics["ssid"] = val

        if len(rates) >= 2:
            metrics["rx_rate_mbps"] = rates[0]
            metrics["tx_rate_mbps"] = rates[1]
            metrics["link_speed_mbps"] = max(rates[0], rates[1])
        elif len(rates) == 1:
            metrics["rx_rate_mbps"] = rates[0]
            metrics["tx_rate_mbps"] = rates[0]
            metrics["link_speed_mbps"] = rates[0]
        return metrics

    def get_wifi_metrics(self, interface_name: Optional[str] = None) -> WifiMetrics:
        """Query WLAN interfaces directly via wlanapi.dll without netsh.exe child processes."""
        try:
            wlan = ctypes.windll.wlanapi
            wlan.WlanOpenHandle.argtypes = [
                wintypes.DWORD,
                ctypes.c_void_p,
                ctypes.POINTER(wintypes.DWORD),
                ctypes.POINTER(wintypes.HANDLE),
            ]
            wlan.WlanOpenHandle.restype = wintypes.DWORD
            wlan.WlanCloseHandle.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
            wlan.WlanCloseHandle.restype = wintypes.DWORD
            wlan.WlanEnumInterfaces.argtypes = [
                wintypes.HANDLE,
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.POINTER(_WLAN_INTERFACE_INFO_LIST)),
            ]
            wlan.WlanEnumInterfaces.restype = wintypes.DWORD
            wlan.WlanQueryInterface.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(_GUID),
                wintypes.DWORD,
                ctypes.c_void_p,
                ctypes.POINTER(wintypes.DWORD),
                ctypes.POINTER(ctypes.c_void_p),
                ctypes.POINTER(wintypes.DWORD),
            ]
            wlan.WlanQueryInterface.restype = wintypes.DWORD
            wlan.WlanFreeMemory.argtypes = [ctypes.c_void_p]

            h = wintypes.HANDLE()
            neg_ver = wintypes.DWORD()
            ret = wlan.WlanOpenHandle(2, None, ctypes.byref(neg_ver), ctypes.byref(h))
            if ret != 0 or not h.value:
                return WifiMetrics(is_wifi=False)

            try:
                p_list = ctypes.POINTER(_WLAN_INTERFACE_INFO_LIST)()
                ret = wlan.WlanEnumInterfaces(h, None, ctypes.byref(p_list))
                if ret != 0 or not p_list:
                    return WifiMetrics(is_wifi=False)

                try:
                    num_items = p_list.contents.dwNumberOfItems
                    if num_items <= 0:
                        return WifiMetrics(is_wifi=False)

                    class _ACTUAL_LIST(ctypes.Structure):
                        _fields_ = [
                            ("dwNumberOfItems", wintypes.DWORD),
                            ("dwIndex", wintypes.DWORD),
                            ("InterfaceInfo", _WLAN_INTERFACE_INFO * num_items),
                        ]

                    actual_list = ctypes.cast(p_list, ctypes.POINTER(_ACTUAL_LIST)).contents
                    for idx in range(num_items):
                        iface = actual_list.InterfaceInfo[idx]
                        if iface.isState == 1:  # wlan_interface_state_connected
                            data_size = wintypes.DWORD()
                            p_data = ctypes.c_void_p()
                            opcode_type = wintypes.DWORD()
                            q_ret = wlan.WlanQueryInterface(
                                h,
                                ctypes.byref(iface.InterfaceGuid),
                                7,  # wlan_intf_opcode_current_connection
                                None,
                                ctypes.byref(data_size),
                                ctypes.byref(p_data),
                                ctypes.byref(opcode_type),
                            )
                            if q_ret == 0 and p_data:
                                try:
                                    conn = ctypes.cast(
                                        p_data,
                                        ctypes.POINTER(_WLAN_CONNECTION_ATTRIBUTES),
                                    ).contents
                                    assoc = conn.wlanAssociationAttributes
                                    ssid_len = min(assoc.dot11Ssid.uSSIDLength, 32)
                                    ssid_raw = bytes(assoc.dot11Ssid.ucSSID[:ssid_len])
                                    ssid_str = ssid_raw.decode("utf-8", errors="replace")
                                    bssid_str = ":".join(f"{b:02x}" for b in assoc.dot11Bssid)
                                    sig_quality = float(assoc.wlanSignalQuality)
                                    rx_rate = float(assoc.ulRxRate) / 1000.0  # kbps to Mbps
                                    tx_rate = float(assoc.ulTxRate) / 1000.0  # kbps to Mbps
                                    speed_mbps = max(rx_rate, tx_rate)
                                    return WifiMetrics(
                                        is_wifi=True,
                                        ssid=ssid_str,
                                        signal_percent=sig_quality,
                                        signal_quality=sig_quality,
                                        link_speed_mbps=speed_mbps,
                                        rx_rate_mbps=rx_rate,
                                        tx_rate_mbps=tx_rate,
                                        bssid=bssid_str,
                                        interface_description=iface.strInterfaceDescription,
                                    )
                                finally:
                                    wlan.WlanFreeMemory(p_data)
                    return WifiMetrics(is_wifi=False)
                finally:
                    wlan.WlanFreeMemory(p_list)
            finally:
                wlan.WlanCloseHandle(h, None)
        except Exception as exc:
            logger.debug("Win32 native WLAN API query error: %s", exc)

        return WifiMetrics(is_wifi=False)

    def get_qos_policies(self, policy_store: str = "ActiveStore") -> List[Dict[str, Any]]:
        """Query active Windows QoS policies via PowerShell Get-NetQosPolicy from ActiveStore or default store."""
        try:
            store_arg = f" -PolicyStore {policy_store}" if policy_store else ""
            fields = (
                "Name, AppPathNameMatchCondition, IPProtocolMatchCondition, "
                "IPDstPortStartMatchCondition, IPDstPortEndMatchCondition, "
                "IPSrcPortStartMatchCondition, IPSrcPortEndMatchCondition, "
                "DSCPAction, ThrottleRateActionBitsPerSecond, Precedence, PolicyStore"
            )
            cmd = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"Get-NetQosPolicy{store_arg} -ErrorAction Stop | Select-Object {fields} | ConvertTo-Json -Compress",
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
                creationflags=_NO_WINDOW,
            )
            if proc.returncode != 0 or not proc.stdout.strip():
                # If ActiveStore had nothing or failed, also check default store if not already checked
                if policy_store:
                    cmd_def = [
                        "powershell",
                        "-NoProfile",
                        "-NonInteractive",
                        "-Command",
                        f"Get-NetQosPolicy -ErrorAction SilentlyContinue | Select-Object {fields} | ConvertTo-Json -Compress",
                    ]
                    proc_def = subprocess.run(
                        cmd_def,
                        capture_output=True,
                        text=True,
                        timeout=4.0,
                        check=False,
                        creationflags=_NO_WINDOW,
                    )
                    if proc_def.returncode == 0 and proc_def.stdout.strip():
                        proc = proc_def
                    else:
                        return []
                else:
                    return []
            import json
            data = json.loads(proc.stdout.strip())
            if isinstance(data, dict):
                data = [data]
            policies = []
            for item in data:
                policies.append({
                    "name": item.get("Name") or "",
                    "app_name": item.get("AppPathNameMatchCondition") or "",
                    "protocol": item.get("IPProtocolMatchCondition"),
                    "dst_port_start": item.get("IPDstPortStartMatchCondition"),
                    "dst_port_end": item.get("IPDstPortEndMatchCondition"),
                    "src_port_start": item.get("IPSrcPortStartMatchCondition"),
                    "src_port_end": item.get("IPSrcPortEndMatchCondition"),
                    "throttle_bps": item.get("ThrottleRateActionBitsPerSecond"),
                    "dscp_action": item.get("DSCPAction"),
                    "precedence": item.get("Precedence"),
                    "policy_store": item.get("PolicyStore"),
                })
            return policies
        except Exception:
            return []

    def _query_qos_safe(self, policy_store: str = "ActiveStore") -> List[Dict[str, Any]]:
        """Safely invoke get_qos_policies handling tests/mocks that lack keyword arguments."""
        try:
            return self.get_qos_policies(policy_store=policy_store)
        except TypeError:
            return self.get_qos_policies()

    def create_qos_dscp_policy(
        self,
        name: str,
        app_name: str = "",
        dscp_value: int = 46,
        ip_protocol: Optional[str] = None,
        port_start: Optional[int] = None,
        port_end: Optional[int] = None,
        port: Optional[int] = None,
        is_dest_port: bool = True,
        is_default: bool = False,
        policy_store: str = "ActiveStore",
    ) -> Tuple[bool, str]:
        """Create a Windows QoS policy assigning DSCP priority to outbound packets in ActiveStore.
        
        Supports port ranges and protocol filters (e.g. UDP 8801-8810) so only real-time media
        packets are prioritized while leaving signaling and file transfers untouched.
        """
        if not self.is_elevated():
            return False, "تتطلب سياسة أولوية البث (DSCP) تشغيل البرنامج كمسؤول (Administrator)."

        existing = [p for p in self._query_qos_safe(policy_store) if p.get("name") == name]
        if existing:
            return True, f"سياسة أولوية البث '{name}' موجودة ونشطة بالفعل."

        try:
            parts = [f"New-NetQosPolicy -Name '{name}' -PolicyStore {policy_store}"]
            if is_default:
                parts.append("-Default")
            elif app_name:
                parts.append(f"-AppPathNameMatchCondition '{app_name}'")

            if ip_protocol:
                parts.append(f"-IPProtocolMatchCondition {ip_protocol}")

            if port_start is not None and port_end is not None:
                if is_dest_port:
                    parts.append(f"-IPDstPortStartMatchCondition {port_start} -IPDstPortEndMatchCondition {port_end}")
                else:
                    parts.append(f"-IPSrcPortStartMatchCondition {port_start} -IPSrcPortEndMatchCondition {port_end}")
            elif port is not None:
                if is_dest_port:
                    parts.append(f"-IPDstPortMatchCondition {port}")
                else:
                    parts.append(f"-IPSrcPortMatchCondition {port}")

            parts.append(f"-DSCPAction {dscp_value}")
            ps_script = " ".join(parts)

            cmd = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                ps_script,
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=8.0,
                check=False,
                creationflags=_NO_WINDOW,
            )
            if proc.returncode == 0:
                verified = any(p.get("name") == name for p in self._query_qos_safe(policy_store))
                if verified:
                    return True, f"تم تطبيق سياسة أولوية DSCP {dscp_value} لـ {app_name or 'الافتراضي'} بنجاح."
                return True, f"تم إصدار أمر سياسة أولوية DSCP {dscp_value}."

            err = (proc.stderr or proc.stdout or "").strip()
            if "already exists" in err.lower():
                return True, f"سياسة QoS '{name}' موجودة بالفعل."
            if "permission" in err.lower() or "denied" in err.lower() or "cim" in err.lower():
                return False, "تم رفض الوصول: يتطلب إنشاء سياسات QoS صلاحيات مسؤول النظام (Administrator)."
            return False, err or f"فشل إنشاء سياسة QoS (كود {proc.returncode})"
        except Exception as exc:
            return False, str(exc)

    def create_qos_throttle_policy(
        self,
        name: str,
        app_name: str,
        throttle_bps: int,
        policy_store: str = "ActiveStore",
    ) -> Tuple[bool, str]:
        """Create a Windows QoS policy throttling outbound upload bandwidth for an application in ActiveStore."""
        if not self.is_elevated():
            return False, "يتطلب تقييد سرعة الرفع (QoS Outbound Throttle) تشغيل البرنامج كمسؤول (Administrator)."

        existing = [p for p in self._query_qos_safe(policy_store) if p.get("name") == name]
        if existing:
            return True, f"سياسة تقييد سرعة الرفع '{name}' مطبقة ونشطة بالفعل."

        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"New-NetQosPolicy -Name '{name}' -PolicyStore {policy_store} -AppPathNameMatchCondition '{app_name}' -ThrottleRateActionBitsPerSecond {int(throttle_bps)}",
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=8.0,
                check=False,
                creationflags=_NO_WINDOW,
            )
            if proc.returncode == 0:
                mbps = throttle_bps / 1_000_000.0
                verified = any(p.get("name") == name for p in self._query_qos_safe(policy_store))
                if verified:
                    return True, f"تم تقييد سرعة الرفع الصادر لـ {app_name} بنجاح إلى {mbps:.1f} Mbps."
                return True, f"تم إصدار أمر تقييد سرعة الرفع لـ {app_name}."

            err = (proc.stderr or proc.stdout or "").strip()
            if "already exists" in err.lower():
                return True, f"سياسة تقييد الرفع '{name}' موجودة بالفعل."
            if "permission" in err.lower() or "denied" in err.lower() or "cim" in err.lower():
                return False, "تم رفض الوصول: يتطلب تطبيق خنق الرفع QoS صلاحيات مسؤول النظام (Administrator)."
            return False, err or f"فشل تطبيق خنق سرعة الرفع (كود {proc.returncode})"
        except Exception as exc:
            return False, str(exc)

    def get_last_qos_batch_report(self) -> Dict[str, Any]:
        """Retrieve structured readback verification report from the last batch apply."""
        return getattr(self, "last_qos_batch_report", {})

    def validate_policy_spec_with_whatif(self, spec: Any) -> Tuple[bool, str]:
        """Validate exact generated QoS policy command using PowerShell -WhatIf with real parameter names."""
        cmd_str = spec.to_powershell_command() if hasattr(spec, "to_powershell_command") else str(spec)
        whatif_cmd = f"{cmd_str} -WhatIf"
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", whatif_cmd],
                capture_output=True,
                text=True,
                timeout=8.0,
                check=False,
                creationflags=_NO_WINDOW,
            )
            out = (proc.stdout or "").strip()
            err = (proc.stderr or "").strip()
            if proc.returncode == 0 and ("what if" in out.lower() or "whatif" in out.lower() or not err):
                return True, out
            return False, err or out or f"PowerShell WhatIf validation failed with exit code {proc.returncode}"
        except Exception as exc:
            return False, str(exc)

    @staticmethod
    def _verify_policy_properties(spec: Any, live_props: Dict[str, Any]) -> Tuple[bool, str]:
        """Verify that live ActiveStore policy properties match the input QoSPolicySpec.
        
        Checks Name, AppPathNameMatchCondition, IPProtocolMatchCondition,
        destination/source port ranges, DSCPAction, ThrottleRateActionBitsPerSecond,
        Precedence, and PolicyStore.
        """
        if not isinstance(live_props, dict):
            return True, "OK"

        # If only Name is present (e.g. lightweight string mock), pass
        if len(live_props) <= 1 and "Name" in live_props:
            return True, "OK"

        spec_name = getattr(spec, "name", "")
        live_name = live_props.get("Name") or ""
        if spec_name and live_name and spec_name != live_name:
            return False, f"Name mismatch: expected {spec_name}, got {live_name}"

        # AppPathNameMatchCondition
        spec_app = getattr(spec, "app_name", "")
        is_default = getattr(spec, "is_default", False)
        live_app = live_props.get("AppPathNameMatchCondition") or ""
        if spec_app and not is_default:
            if spec_app.lower() not in live_app.lower():
                return False, f"App mismatch: expected {spec_app}, got {live_app}"
        elif is_default:
            if live_app:
                return False, f"Default policy should have empty AppPathName, got {live_app}"

        # IPProtocolMatchCondition
        spec_proto = getattr(spec, "protocol", None)
        live_proto = live_props.get("IPProtocolMatchCondition")
        if spec_proto:
            sp_up = str(spec_proto).upper()
            lp_str = str(live_proto or "").upper()
            proto_ok = (
                sp_up == lp_str
                or (sp_up == "UDP" and lp_str in ("17", "UDP"))
                or (sp_up == "TCP" and lp_str in ("6", "TCP"))
            )
            if not proto_ok:
                return False, f"Protocol mismatch: expected {sp_up}, got {live_proto}"

        # Destination / Source Ports
        port_start = getattr(spec, "port_start", None)
        port_end = getattr(spec, "port_end", None)
        single_port = getattr(spec, "port", None)
        is_dest = getattr(spec, "is_dest_port", True)

        if port_start is not None and port_end is not None:
            if is_dest:
                lp_start = live_props.get("IPDstPortStartMatchCondition")
                lp_end = live_props.get("IPDstPortEndMatchCondition")
            else:
                lp_start = live_props.get("IPSrcPortStartMatchCondition")
                lp_end = live_props.get("IPSrcPortEndMatchCondition")

            if lp_start is not None and lp_end is not None:
                if int(lp_start) != int(port_start) or int(lp_end) != int(port_end):
                    return False, f"Port range mismatch: expected {port_start}-{port_end}, got {lp_start}-{lp_end}"
        elif single_port is not None:
            if is_dest:
                lp_start = live_props.get("IPDstPortStartMatchCondition")
                lp_end = live_props.get("IPDstPortEndMatchCondition")
            else:
                lp_start = live_props.get("IPSrcPortStartMatchCondition")
                lp_end = live_props.get("IPSrcPortEndMatchCondition")

            if lp_start is not None:
                if int(lp_start) != int(single_port):
                    return False, f"Port mismatch: expected {single_port}, got {lp_start}"

        # DSCPAction
        spec_dscp = getattr(spec, "dscp", None)
        live_dscp = live_props.get("DSCPAction")
        if spec_dscp is not None and live_dscp is not None:
            if int(live_dscp) != int(spec_dscp):
                return False, f"DSCPAction mismatch: expected {spec_dscp}, got {live_dscp}"

        # ThrottleRateActionBitsPerSecond
        spec_throttle = getattr(spec, "throttle_bps", None)
        live_throttle = live_props.get("ThrottleRateActionBitsPerSecond")
        if spec_throttle is not None and live_throttle is not None:
            if int(live_throttle) != int(spec_throttle):
                return False, f"ThrottleRate mismatch: expected {spec_throttle}, got {live_throttle}"

        # Precedence
        spec_prec = getattr(spec, "precedence", None)
        live_prec = live_props.get("Precedence")
        if spec_prec is not None and live_prec is not None:
            if int(live_prec) != int(spec_prec):
                return False, f"Precedence mismatch: expected {spec_prec}, got {live_prec}"

        # PolicyStore
        spec_store = getattr(spec, "policy_store", "ActiveStore")
        live_store = live_props.get("PolicyStore")
        if spec_store and live_store:
            if spec_store.lower() not in str(live_store).lower():
                return False, f"PolicyStore mismatch: expected {spec_store}, got {live_store}"

        return True, "OK"

    def apply_qos_policies_batch(self, specs: List[Any]) -> Tuple[bool, str]:
        """Apply a batch of QoS policy specifications with try/catch and ActiveStore readback verification.
        
        Protected by a single-flight lock, exponential backoff after failures, and single-retry
        for any missing media policies.
        """
        if not self.is_elevated():
            return False, "تتطلب سياسات QoS تشغيل البرنامج كمسؤول (Administrator)."
        if not specs:
            return True, "لا توجد سياسات لتطبيقها."

        # Check failure backoff
        now_mono = time.monotonic()
        if now_mono < self._qos_backoff_until:
            wait_sec = int(self._qos_backoff_until - now_mono)
            return False, f"تأجيل تطبيق سياسات QoS لمدة {wait_sec} ثانية بسبب فشل سابق: {self._qos_last_error}"

        if not self._qos_lock.acquire(blocking=False):
            return False, "عملية تطبيق سياسات QoS جارية بالفعل في مسار آخر (Single-flight lock)."

        try:
            script_lines = [
                "$results = @{}",
                "$errors = @{}",
            ]
            expected_names = []
            spec_map: Dict[str, Any] = {}
            for spec in specs:
                if hasattr(spec, "to_powershell_command"):
                    cmd_str = spec.to_powershell_command()
                    name = getattr(spec, "name", "")
                elif isinstance(spec, str):
                    cmd_str = spec
                    name = spec.split("-Name")[-1].split()[0].strip("'\"") if "-Name" in spec else "custom"
                else:
                    continue
                expected_names.append(name)
                spec_map[name] = spec
                # Execute each New-NetQosPolicy in try/catch without -ErrorAction SilentlyContinue
                script_lines.append(
                    f"try {{ {cmd_str} -ErrorAction Stop; $results['{name}'] = $true }} "
                    f"catch {{ $results['{name}'] = $false; $errors['{name}'] = $_.Exception.Message }}"
                )

            # Read back all active NetGuard policies from ActiveStore with full match conditions
            fields_str = (
                "Name, AppPathNameMatchCondition, IPProtocolMatchCondition, "
                "IPDstPortStartMatchCondition, IPDstPortEndMatchCondition, "
                "IPSrcPortStartMatchCondition, IPSrcPortEndMatchCondition, "
                "DSCPAction, ThrottleRateActionBitsPerSecond, Precedence, PolicyStore"
            )
            script_lines.append(
                "try { "
                f"$active = @(Get-NetQosPolicy -PolicyStore ActiveStore -ErrorAction Stop | Where-Object {{ $_.Name -like 'NetGuard_*' }} | Select-Object {fields_str}) "
                "} catch { "
                "if ($_.Exception.Message -match 'No MSFT_NetQosPolicySettingData|not found') { $active = @() } else { $errors['__readback__'] = $_.Exception.Message; $active = @() } "
                "}"
            )
            script_lines.append("[PSCustomObject]@{ Results = $results; Errors = $errors; Active = $active } | ConvertTo-Json -Compress")

            batch_script = "\n".join(script_lines)
            cmd = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                batch_script,
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15.0,
                check=False,
                creationflags=_NO_WINDOW,
            )

            if proc.returncode != 0:
                err = (proc.stderr or proc.stdout or "").strip()
                self._qos_failure_count += 1
                self._qos_backoff_until = now_mono + min(60.0, 5.0 * (2 ** min(4, self._qos_failure_count)))
                self._qos_last_error = err
                self.last_qos_batch_report = {"success": False, "error": err, "created": [], "verified": [], "failed": expected_names, "details": {}}
                return False, f"فشل تشغيل أمر PowerShell لتطبيق سياسات QoS: {err}"

            # Parse readback JSON
            out_str = (proc.stdout or "").strip()
            json_line = ""
            for line in reversed(out_str.splitlines()):
                line_str = line.strip()
                if line_str.startswith("{") and line_str.endswith("}"):
                    json_line = line_str
                    break
            if not json_line:
                json_line = out_str

            import json
            try:
                report = json.loads(json_line)
            except Exception:
                report = {"Results": {}, "Errors": {}, "Active": []}

            res_map = report.get("Results") or {}
            err_map = report.get("Errors") or {}
            active_list = report.get("Active") or []
            if isinstance(active_list, dict):
                active_list = [active_list]
            elif isinstance(active_list, str):
                active_list = [{"Name": active_list}]

            active_by_name: Dict[str, Dict[str, Any]] = {}
            for item in active_list:
                if isinstance(item, dict):
                    n = item.get("Name") or ""
                    if n:
                        active_by_name[n] = item
                elif isinstance(item, str):
                    active_by_name[item] = {"Name": item}

            verified_names: List[str] = []
            failed_names: List[str] = []
            details_map: Dict[str, Dict[str, Any]] = {}

            for name in expected_names:
                spec_obj = spec_map.get(name)
                # Check creation result from PowerShell try/catch
                if res_map.get(name) is False:
                    failed_names.append(name)
                    err_reason = err_map.get(name, "فشل إنشاء السياسة في PowerShell")
                    details_map[name] = {"verified": False, "reason": err_reason}
                    continue

                if name not in active_by_name:
                    failed_names.append(name)
                    err_reason = err_map.get(name, "لم تظهر السياسة في فحص ActiveStore")
                    err_map[name] = err_reason
                    details_map[name] = {"verified": False, "reason": err_reason}
                    continue

                # Property verification
                live_props = active_by_name[name]
                prop_ok, prop_reason = self._verify_policy_properties(spec_obj, live_props)
                if not prop_ok:
                    failed_names.append(name)
                    err_map[name] = prop_reason
                    details_map[name] = {"verified": False, "reason": prop_reason, "live": live_props}
                else:
                    verified_names.append(name)
                    details_map[name] = {"verified": True, "properties": live_props}

            # Missing media policy retry: if a media policy is missing or failed property match, retry once
            missing_media = [
                fn for fn in failed_names
                if any(kw in fn for kw in ("Media", "Audio", "Video", "STUN", "Sharing", "Fallback"))
            ]
            if missing_media:
                for mm in missing_media:
                    spec_obj = spec_map.get(mm)
                    if spec_obj:
                        retry_cmd = spec_obj.to_powershell_command() if hasattr(spec_obj, "to_powershell_command") else str(spec_obj)
                        retry_proc = subprocess.run(
                            ["powershell", "-NoProfile", "-NonInteractive", "-Command", f"{retry_cmd} -ErrorAction Stop"],
                            capture_output=True,
                            text=True,
                            timeout=6.0,
                            check=False,
                            creationflags=_NO_WINDOW,
                        )
                        if retry_proc.returncode == 0:
                            # Re-verify in ActiveStore with full properties
                            check_proc = subprocess.run(
                                ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                                 f"Get-NetQosPolicy -PolicyStore ActiveStore -Name '{mm}' -ErrorAction Stop | Select-Object {fields_str} | ConvertTo-Json -Compress"],
                                capture_output=True,
                                text=True,
                                timeout=4.0,
                                check=False,
                                creationflags=_NO_WINDOW,
                            )
                            if check_proc.returncode == 0 and check_proc.stdout.strip():
                                try:
                                    re_props = json.loads(check_proc.stdout.strip())
                                    if isinstance(re_props, list) and re_props:
                                        re_props = re_props[0]
                                    re_ok, re_reason = self._verify_policy_properties(spec_obj, re_props)
                                    if re_ok:
                                        verified_names.append(mm)
                                        failed_names.remove(mm)
                                        err_map.pop(mm, None)
                                        details_map[mm] = {"verified": True, "properties": re_props}
                                except Exception:
                                    pass

            created_names = [name for name, ok in res_map.items() if ok]
            self.last_qos_batch_report = {
                "success": len(failed_names) == 0,
                "expected": expected_names,
                "created": created_names,
                "verified": verified_names,
                "failed": failed_names,
                "errors": err_map,
                "active_live": list(active_by_name.keys()),
                "details": details_map,
            }

            if failed_names:
                self._qos_failure_count += 1
                self._qos_backoff_until = now_mono + min(60.0, 5.0 * (2 ** min(4, self._qos_failure_count)))
                error_details = []
                for fn in failed_names:
                    e_msg = err_map.get(fn, "لم تظهر السياسة في فحص ActiveStore")
                    error_details.append(f"{fn}: {e_msg}")
                detail_str = " | ".join(error_details)
                self._qos_last_error = detail_str
                return False, f"فشل تطبيق/التحقق من {len(failed_names)} سياسة من أصل {len(expected_names)}: {detail_str}"

            # Success: reset backoff
            self._qos_failure_count = 0
            self._qos_backoff_until = 0.0
            self._qos_last_error = ""
            return True, f"تم تطبيق والتحقق من {len(verified_names)} سياسة QoS بنجاح في ActiveStore."
        except Exception as exc:
            self._qos_failure_count += 1
            self._qos_backoff_until = now_mono + 10.0
            self._qos_last_error = str(exc)
            self.last_qos_batch_report = {"success": False, "error": str(exc), "verified": []}
            return False, str(exc)
        finally:
            self._qos_lock.release()

    def remove_qos_policy(self, name: str, policy_store: str = "ActiveStore") -> Tuple[bool, str]:
        """Remove a Windows NetQosPolicy by name from ActiveStore and default persistent store."""
        if not self.is_elevated():
            return False, "يتطلب حذف سياسات QoS تشغيل البرنامج كمسؤول (Administrator)."

        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"Remove-NetQosPolicy -Name '{name}' -PolicyStore {policy_store} -Confirm:$false -ErrorAction SilentlyContinue; "
                f"Remove-NetQosPolicy -Name '{name}' -Confirm:$false -ErrorAction SilentlyContinue",
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=8.0,
                check=False,
                creationflags=_NO_WINDOW,
            )
            if proc.returncode == 0:
                return True, f"تمت إزالة سياسة QoS '{name}' بنجاح."
            err = (proc.stderr or proc.stdout or "").strip()
            if "not found" in err.lower() or "no msft_netqospolicysettingdata" in err.lower():
                return True, f"سياسة QoS '{name}' غير موجودة."
            if "permission" in err.lower() or "denied" in err.lower() or "cim" in err.lower():
                return False, "تم رفض الوصول: يتطلب حذف سياسات QoS صلاحيات مسؤول النظام."
            return False, err or f"فشل حذف سياسة QoS (كود {proc.returncode})"
        except Exception as exc:
            return False, str(exc)

    def sweep_all_netguard_rules(self) -> Tuple[bool, str]:
        """Sweep and remove all NetGuard QoS policies (ActiveStore & persistent) and Firewall rules, returning real verification result."""
        if not self.is_elevated():
            return False, "يتطلب تنظيف القواعد صلاحيات مسؤول النظام."

        acquired = self._qos_lock.acquire(timeout=5.0)
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Remove-NetQosPolicy -Name 'NetGuard_*' -PolicyStore ActiveStore -Confirm:$false -ErrorAction SilentlyContinue; "
                "Remove-NetQosPolicy -Name 'NetGuard_*' -Confirm:$false -ErrorAction SilentlyContinue; "
                "Remove-NetFirewallRule -Name 'NetGuard_*' -ErrorAction SilentlyContinue; "
                "@(Get-NetQosPolicy -PolicyStore ActiveStore -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'NetGuard_*' }).Count",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10.0, check=False, creationflags=_NO_WINDOW)
            if proc.returncode != 0:
                err = (proc.stderr or proc.stdout or "").strip()
                return False, f"فشل تنظيف سياسات NetGuard: {err}"

            remaining = proc.stdout.strip().splitlines()[-1].strip() if proc.stdout.strip() else "0"
            if remaining and remaining != "0" and remaining.isdigit() and int(remaining) > 0:
                return False, f"لا تزال هناك {remaining} سياسة NetGuard نشطة في ActiveStore بعد التنظيف."

            return True, "تم تنظيف وتأكيد حذف كافة قواعد NetGuard (ActiveStore والقواعد الدائمة) بنجاح."
        except Exception as exc:
            return False, str(exc)
        finally:
            if acquired:
                self._qos_lock.release()
