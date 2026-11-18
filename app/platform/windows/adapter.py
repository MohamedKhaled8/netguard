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

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


class WindowsPlatformAdapter(IPlatformAdapter):
    """Windows-specific implementation using allowlisted system commands and native sockets."""

    supports_auto_elevate: bool = True

    def __init__(self) -> None:
        self._cached_gateway: Optional[str] = None
        self._cached_interface: Optional[str] = None
        self._last_elevation_request_time: float = 0.0

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
        """Detect default IPv4 gateway via PowerShell Get-NetRoute with ConvertTo-Json or route print fallback."""
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
                timeout=4.0,
                check=False,
                creationflags=_NO_WINDOW,
            )
            if proc.returncode == 0 and proc.stdout.strip():
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

        # Secondary fallback: route print 0.0.0.0
        try:
            proc = subprocess.run(
                ["route", "print", "0.0.0.0"],
                capture_output=True,
                text=True,
                timeout=3.0,
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

        return self._cached_gateway

    def get_primary_interface(self) -> Optional[str]:
        """Detect the primary network adapter name currently routing default traffic."""
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Select-Object InterfaceAlias | ConvertTo-Json",
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
                data = json.loads(proc.stdout)
                if isinstance(data, list) and data:
                    data = data[0]
                if isinstance(data, dict) and data.get("InterfaceAlias"):
                    self._cached_interface = data["InterfaceAlias"]
                    return data["InterfaceAlias"]
        except Exception:
            pass

        # Fallback to route print and psutil matching
        try:
            proc = subprocess.run(
                ["route", "print", "0.0.0.0"],
                capture_output=True,
                text=True,
                timeout=3.0,
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
        """Execute Windows ping with single echo and parse latency in a locale-independent manner."""
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
                creationflags=_NO_WINDOW,
            )
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            if proc.returncode == 0:
                stdout_text = proc.stdout
                # 1. Locale-independent per-packet reply line:
                match = re.search(
                    r"([=<])\s*(\d+(?:\.\d+)?)\s*(?:ms|مللي ثانية|مللي|мс|msec)\b",
                    stdout_text,
                    re.IGNORECASE,
                )
                if match:
                    op, val = match.group(1), float(match.group(2))
                    return True, (0.5 if op == "<" and val <= 1.0 else val)

                # 2. Locale-independent summary statistics line:
                match_avg = re.search(r"=\s*(\d+(?:\.\d+)?)\s*(?:ms|مللي ثانية|مللي|мс|msec)?\s*$", stdout_text.strip(), re.MULTILINE)
                if match_avg:
                    return True, float(match_avg.group(1))

                return True, max(duration_ms, 0.1)
            return False, 0.0
        except (subprocess.TimeoutExpired, Exception):
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
        """Query configured DNS servers for the specified interface."""
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"(Get-DnsClientServerAddress -InterfaceAlias '{interface_name}' -AddressFamily IPv4).ServerAddresses",
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
                ips = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
                valid = [ip for ip in ips if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip)]
                if valid:
                    return valid
        except Exception:
            pass

        try:
            proc = subprocess.run(
                ["netsh", "interface", "ip", "show", "dns", f"name={interface_name}"],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
                creationflags=_NO_WINDOW,
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
        """Configure primary and secondary static DNS or DHCP, and verify via Get-DnsClientServerAddress."""
        if not self.is_elevated():
            return False, "Requires Administrator privileges to modify network adapter DNS."

        if not servers:
            # Set to DHCP
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
                    proc = subprocess.run(
                        ["netsh", "interface", "ip", "set", "dns", f"name={interface_name}", "source=dhcp"],
                        capture_output=True,
                        text=True,
                        timeout=8.0,
                        check=False,
                        creationflags=_NO_WINDOW,
                    )
                    if proc.returncode != 0:
                        return False, proc.stderr or proc.stdout

                self.flush_dns_cache()
                return True, f"Configured DNS on {interface_name} to DHCP."
            except Exception as exc:
                return False, str(exc)

        # Set static DNS
        try:
            ps_servers_arg = "@(" + ", ".join(f"'{s}'" for s in servers) + ")"
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
                primary = servers[0]
                proc = subprocess.run(
                    ["netsh", "interface", "ip", "set", "dns", f"name={interface_name}", "static", primary, "primary"],
                    capture_output=True,
                    text=True,
                    timeout=8.0,
                    check=False,
                    creationflags=_NO_WINDOW,
                )
                if proc.returncode != 0:
                    out = (proc.stderr or "") + (proc.stdout or "")
                    return False, out

                for idx, secondary in enumerate(servers[1:], start=2):
                    proc_sec = subprocess.run(
                        ["netsh", "interface", "ip", "add", "dns", f"name={interface_name}", secondary, f"index={idx}"],
                        capture_output=True,
                        text=True,
                        timeout=5.0,
                        check=False,
                        creationflags=_NO_WINDOW,
                    )
                    if proc_sec.returncode != 0:
                        return False, f"Failed to add secondary DNS {secondary}: {proc_sec.stderr or proc_sec.stdout}"

            self.flush_dns_cache()
            actual_servers = self.get_interface_dns_servers(interface_name)
            if any(s in actual_servers for s in servers):
                return True, f"Configured and verified DNS on {interface_name} to {', '.join(servers)}."
            return True, f"Configured DNS on {interface_name} to {', '.join(servers)}."
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
                creationflags=_NO_WINDOW,
            )
            if proc.returncode == 0:
                return True, "DHCP lease renewed successfully."
            return False, proc.stderr or proc.stdout
        except Exception as exc:
            return False, str(exc)

    def get_wifi_metrics(self, interface_name: Optional[str] = None) -> Dict[str, Any]:
        """Parse WLAN interfaces for signal percentage, SSID, and rates in a locale-independent manner."""
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
                creationflags=_NO_WINDOW,
            )
            if proc.returncode == 0:
                metrics["is_wifi"] = True
                rates = []
                for line in proc.stdout.splitlines():
                    line = line.strip()
                    if ":" not in line:
                        continue
                    key, val = [p.strip() for p in line.split(":", 1)]

                    # BSSID (MAC address format in any locale)
                    if re.match(r"^[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}$", val):
                        metrics["bssid"] = val

                    # Signal percentage (% in any locale)
                    m_sig = re.search(r"(\d+)\s*%", val)
                    if m_sig:
                        metrics["signal_percent"] = float(m_sig.group(1))

                    # Throughput rates (MB/s, Mbps, MBit/s, م.ب/ث)
                    m_rate = re.search(r"([0-9\.]+)\s*(?:mbps|mbit/s|mbits/s|م\.ب/ث)?", val, re.I)
                    if m_rate and any(u in key.lower() or u in val.lower() for u in ("rate", "mbps", "mbit", "vitesse", "معدل", "استلام", "إرسال")):
                        try:
                            rates.append(float(m_rate.group(1)))
                        except ValueError:
                            pass

                    # SSID line (contains SSID in key, but not BSSID)
                    if "ssid" in key.lower() and "bssid" not in key.lower():
                        metrics["ssid"] = val

                if len(rates) >= 2:
                    metrics["rx_rate_mbps"] = rates[0]
                    metrics["tx_rate_mbps"] = rates[1]
                elif len(rates) == 1:
                    metrics["rx_rate_mbps"] = rates[0]
                    metrics["tx_rate_mbps"] = rates[0]
        except Exception:
            pass
        return metrics

    def get_qos_policies(self) -> List[Dict[str, Any]]:
        """Query active Windows QoS policies via PowerShell Get-NetQosPolicy."""
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-NetQosPolicy | Select-Object Name, AppPathNameMatchCondition, ThrottleRateActionBitsPerSecond, DSCPAction | ConvertTo-Json -Compress",
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
                    "throttle_bps": item.get("ThrottleRateActionBitsPerSecond"),
                    "dscp_action": item.get("DSCPAction"),
                })
            return policies
        except Exception:
            return []

    def create_qos_dscp_policy(self, name: str, app_name: str, dscp_value: int = 46) -> Tuple[bool, str]:
        """Create a Windows QoS policy assigning DSCP priority to outbound packets of an application."""
        if not self.is_elevated():
            return False, "تتطلب سياسة أولوية البث (DSCP) تشغيل البرنامج كمسؤول (Administrator)."

        existing = [p for p in self.get_qos_policies() if p.get("name") == name]
        if existing:
            return True, f"سياسة أولوية البث '{name}' موجودة ونشطة بالفعل."

        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"New-NetQosPolicy -Name '{name}' -AppPathNameMatchCondition '{app_name}' -DSCPAction {dscp_value}",
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
                verified = any(p.get("name") == name for p in self.get_qos_policies())
                if verified:
                    return True, f"تم تطبيق سياسة أولوية DSCP {dscp_value} لـ {app_name} بنجاح."
                return True, f"تم إصدار أمر سياسة أولوية DSCP {dscp_value}."

            err = (proc.stderr or proc.stdout or "").strip()
            if "already exists" in err.lower():
                return True, f"سياسة QoS '{name}' موجودة بالفعل."
            if "permission" in err.lower() or "denied" in err.lower() or "cim" in err.lower():
                return False, "تم رفض الوصول: يتطلب إنشاء سياسات QoS صلاحيات مسؤول النظام (Administrator)."
            return False, err or f"فشل إنشاء سياسة QoS (كود {proc.returncode})"
        except Exception as exc:
            return False, str(exc)

    def create_qos_throttle_policy(self, name: str, app_name: str, throttle_bps: int) -> Tuple[bool, str]:
        """Create a Windows QoS policy throttling outbound upload bandwidth for an application."""
        if not self.is_elevated():
            return False, "يتطلب تقييد سرعة الرفع (QoS Outbound Throttle) تشغيل البرنامج كمسؤول (Administrator)."

        existing = [p for p in self.get_qos_policies() if p.get("name") == name]
        if existing:
            return True, f"سياسة تقييد سرعة الرفع '{name}' مطبقة ونشطة بالفعل."

        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"New-NetQosPolicy -Name '{name}' -AppPathNameMatchCondition '{app_name}' -ThrottleRateActionBitsPerSecond {throttle_bps}",
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
                verified = any(p.get("name") == name for p in self.get_qos_policies())
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

    def remove_qos_policy(self, name: str) -> Tuple[bool, str]:
        """Remove a Windows NetQosPolicy by name."""
        if not self.is_elevated():
            return False, "يتطلب حذف سياسات QoS تشغيل البرنامج كمسؤول (Administrator)."

        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"Remove-NetQosPolicy -Name '{name}' -Confirm:$false",
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
        """Sweep and remove all NetGuard QoS policies and Firewall rules (Item D4)."""
        if not self.is_elevated():
            return False, "يتطلب تنظيف القواعد صلاحيات مسؤول النظام."
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Remove-NetQosPolicy -Name 'NetGuard_*' -Confirm:$false -ErrorAction SilentlyContinue; "
                "Remove-NetFirewallRule -Name 'NetGuard_*' -ErrorAction SilentlyContinue",
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=8.0, check=False, creationflags=_NO_WINDOW)
            return True, "تم تنظيف كافة قواعد NetGuard بنجاح."
        except Exception as exc:
            return False, str(exc)
