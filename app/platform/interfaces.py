"""Platform Abstraction Interfaces for Operating System Operations."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Set


class IPlatformAdapter(ABC):
    """Abstract interface defining all OS-specific network stack operations."""

    @abstractmethod
    def is_elevated(self) -> bool:
        """Check whether the current running process has administrator/root privileges."""
        pass

    @abstractmethod
    def get_default_gateway(self) -> Optional[str]:
        """Detect the active default IPv4 gateway address."""
        pass

    @abstractmethod
    def get_primary_interface(self) -> Optional[str]:
        """Detect the primary network adapter name currently routing default traffic."""
        pass

    @abstractmethod
    def ping(self, target: str, timeout_sec: float = 1.5) -> Tuple[bool, float]:
        """Execute an ICMP ping or OS ping probe. Returns (success, latency_ms)."""
        pass

    @abstractmethod
    def tcp_connect(self, target: str, port: int = 80, timeout_sec: float = 2.0) -> Tuple[bool, float]:
        """Attempt TCP 3-way handshake. Returns (success, latency_ms)."""
        pass

    @abstractmethod
    def flush_dns_cache(self) -> Tuple[bool, str]:
        """Flush the operating system's local DNS resolver cache."""
        pass

    @abstractmethod
    def get_interface_dns_servers(self, interface_name: str) -> List[str]:
        """Retrieve the configured DNS server IPs for the specified interface."""
        pass

    @abstractmethod
    def set_interface_dns_servers(self, interface_name: str, servers: List[str]) -> Tuple[bool, str]:
        """Set static or DHCP DNS servers on the specified interface."""
        pass

    @abstractmethod
    def renew_ip_lease(self, interface_name: str) -> Tuple[bool, str]:
        """Release and renew the DHCP lease for the specified interface."""
        pass

    @abstractmethod
    def get_wifi_metrics(self, interface_name: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve Wi-Fi signal strength (%), link speed, and BSSID if connected."""
        pass

    def get_qos_policies(self) -> List[Dict[str, Any]]:
        """Retrieve active Windows QoS policies matching NetGuard configurations."""
        return []

    def create_qos_dscp_policy(self, name: str, app_name: str, dscp_value: int = 46) -> Tuple[bool, str]:
        """Create a Windows QoS policy assigning DSCP priority to outbound packets of an application."""
        return False, "Not implemented on this platform"

    def create_qos_throttle_policy(self, name: str, app_name: str, throttle_bps: int) -> Tuple[bool, str]:
        """Create a Windows QoS policy throttling outbound upload bandwidth for an application."""
        return False, "Not implemented on this platform"

    def remove_qos_policy(self, name: str) -> Tuple[bool, str]:
        """Remove a Windows NetQosPolicy by name."""
        return False, "Not implemented on this platform"

    def restart_as_administrator(self) -> bool:
        """Relaunch the application elevated as Administrator/root."""
        return False
