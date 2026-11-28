"""Comprehensive Shared Fixtures and Simulated Windows OS Environment for NetGuard AI E2E Tests.

Provides high-fidelity opaque-box simulation of:
- Win32 ICMP In-Process Pinging (IcmpSendEcho / iphlpapi.dll)
- Win32 WLAN API Metrics (wlanapi.dll / netsh wlan)
- Windows NetQosPolicy Engine (New-NetQosPolicy, Get-NetQosPolicy, Remove-NetQosPolicy)
- Dual-Stack IPv4/IPv6 DNS & Resolver Cache (DnsFlushResolverCache, Set-DnsClientServerAddress)
- CIM / WMI Network Adapter Driver & Hardware (Win32_NetworkAdapter, Get-NetAdapter)
- Windows Firewall Profiles & Rules (NetFirewallRule, NetFirewallProfile)
- CapabilityAccessManager / ConsentStore Registry (microphone, webcam)
- PySide6 Headless Offscreen Application & Event Loop
- SQLite WAL Database & Repository Fixtures
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid
import json
import sqlite3
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal, QTimer

from app.core.events.bus import EventBus
from app.platform.interfaces import IPlatformAdapter
from app.platform.windows.adapter import WindowsPlatformAdapter
from app.storage.database import DatabaseManager
from app.storage.repositories.audit_repo import AuditRepository
from app.storage.repositories.incident_repo import IncidentRepository
from app.storage.repositories.measurement_repo import MeasurementRepository
from app.ui.animation_clock import AnimationMasterClock
from app.traffic.controller import TrafficController
from app.core.models.metrics import (
    MetricType,
    ProbeStatus,
    Measurement,
    MeasurementSource,
    OperatingMode,
    RiskLevel,
    ActionExecutionRecord,
    ActionExecutionStatus,
    Diagnosis,
    ProbableCause,
    DiagnosisSeverity,
    Evidence,
)


# =====================================================================
# Domain Audit & Hardware Contracts (M5 / PROJECT.md / TEST_INFRA.md)
# =====================================================================

@dataclass
class AdapterHardwareInfo:
    """Hardware and driver audit properties for a network adapter."""
    adapter_name: str = "Ethernet"
    interface_description: str = "Intel(R) Ethernet Connection I219-V"
    driver_name: str = "e1d68x64.sys"
    driver_provider: str = "Intel"
    driver_version: str = "12.19.2.55"
    driver_date: str = "2023-08-15"
    link_speed_mbps: int = 1000
    duplex: str = "Full Duplex"
    eee_power_saving_enabled: bool = False
    is_physical: bool = True
    is_outdated: bool = False
    status: str = "Up"


@dataclass
class FirewallRuleState:
    """Firewall rule state for port and protocol auditing."""
    name: str
    direction: str  # Inbound / Outbound
    action: str     # Allow / Block
    protocol: str   # UDP / TCP / ICMPv4 / ANY
    local_port: str = ""
    remote_port: str = ""
    profile: str = "Any"
    enabled: bool = True


@dataclass
class FirewallAuditInfo:
    """Comprehensive firewall configuration audit."""
    domain_profile_enabled: bool = True
    private_profile_enabled: bool = True
    public_profile_enabled: bool = True
    port_53_blocked: bool = False
    port_853_dot_blocked: bool = False
    icmp_echo_blocked: bool = False
    webrtc_blocked: bool = False
    active_rules: List[FirewallRuleState] = field(default_factory=list)
    conflicting_rules: List[str] = field(default_factory=list)


@dataclass
class VpnProxyInfo:
    """Virtual and VPN tunnel presence audit."""
    vpn_active: bool = False
    vpn_adapter_names: List[str] = field(default_factory=list)
    doh_enabled: bool = False
    proxy_server: Optional[str] = None


@dataclass
class AuditRecommendation:
    """Forensic recommendation produced from network audit."""
    category: str
    severity: str
    title: str
    recommendation: str
    is_actionable: bool = True


@dataclass
class NetworkEnvironmentAuditReport:
    """Full forensic audit report covering adapter, firewall, and VPN."""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    adapter_audit: AdapterHardwareInfo = field(default_factory=AdapterHardwareInfo)
    firewall_audit: FirewallAuditInfo = field(default_factory=FirewallAuditInfo)
    vpn_proxy_audit: VpnProxyInfo = field(default_factory=VpnProxyInfo)
    recommendations: List[AuditRecommendation] = field(default_factory=list)


# =====================================================================
# High-Fidelity Simulated Windows OS Environment
# =====================================================================

class SimulatedWindowsEnvironment:
    """In-memory simulation of Windows networking kernel & subsystems."""

    def __init__(self) -> None:
        # General state
        self.is_admin: bool = True
        self.default_gateway: str = "192.168.1.1"
        self.primary_interface: str = "Ethernet"
        self.dns_cache_flushed_count: int = 0
        self.dhcp_renew_count: int = 0

        # Adapters
        self.interfaces: Dict[str, Dict[str, Any]] = {
            "Ethernet": {
                "alias": "Ethernet",
                "is_physical": True,
                "is_up": True,
                "type": "Ethernet",
                "metric": 10,
                "ipv4_dns": ["1.1.1.1", "1.0.0.1"],
                "ipv6_dns": ["2606:4700:4700::1111", "2606:4700:4700::1001"],
                "dns_mode": "static",
                "ipv6_enabled": True,
                "errin": 0,
                "errout": 0,
                "dropin": 0,
                "dropout": 0,
            },
            "Wi-Fi": {
                "alias": "Wi-Fi",
                "is_physical": True,
                "is_up": True,
                "type": "Wireless",
                "metric": 25,
                "ipv4_dns": ["192.168.1.1"],
                "ipv6_dns": [],
                "dns_mode": "dhcp",
                "ipv6_enabled": True,
                "errin": 2,
                "errout": 1,
                "dropin": 5,
                "dropout": 0,
            },
            "wintun": {
                "alias": "wintun",
                "is_physical": False,
                "is_up": True,
                "type": "VPN",
                "metric": 5,
                "ipv4_dns": ["10.0.0.1"],
                "ipv6_dns": [],
                "dns_mode": "static",
                "ipv6_enabled": False,
                "errin": 0,
                "errout": 0,
                "dropin": 0,
                "dropout": 0,
            },
            "vEthernet (Default Switch)": {
                "alias": "vEthernet (Default Switch)",
                "is_physical": False,
                "is_up": True,
                "type": "Virtual",
                "metric": 15,
                "ipv4_dns": [],
                "ipv6_dns": [],
                "dns_mode": "dhcp",
                "ipv6_enabled": False,
                "errin": 0,
                "errout": 0,
                "dropin": 0,
                "dropout": 0,
            },
        }

        # Wi-Fi specifics
        self.wifi_metrics: Dict[str, Any] = {
            "is_wifi": True,
            "signal_percent": 88.0,
            "ssid": "Enterprise_Secure_5G",
            "bssid": "00:1a:2b:3c:4d:5e",
            "rx_rate_mbps": 866.7,
            "tx_rate_mbps": 866.7,
            "band": "5 GHz",
        }

        # QoS Policy Store: name -> {Name, AppPathNameMatchCondition, ThrottleRateActionBitsPerSecond, DSCPAction}
        self.qos_policies: Dict[str, Dict[str, Any]] = {}

        # ConsentStore Registry: capability -> [process_name]
        self.consent_store: Dict[str, List[str]] = {
            "microphone": [],
            "webcam": [],
        }

        # Simulated ICMP targets: target_ip -> (reachable, latency_ms)
        self.ping_targets: Dict[str, Tuple[bool, float]] = {
            "127.0.0.1": (True, 0.4),
            "localhost": (True, 0.4),
            "192.168.1.1": (True, 2.5),
            "8.8.8.8": (True, 14.2),
            "1.1.1.1": (True, 11.8),
            "192.0.2.1": (False, 0.0),  # TEST-NET-1 unreachable
        }

        # Simulated DNS resolution targets: (domain, server) -> (resolved, latency_ms)
        self.dns_resolution_targets: Dict[Tuple[str, str], Tuple[bool, float]] = {
            ("google.com", "1.1.1.1"): (True, 12.0),
            ("google.com", "8.8.8.8"): (True, 14.0),
            ("cloudflare.com", "1.1.1.1"): (True, 10.0),
            ("health.check", "1.1.1.1"): (True, 15.0),
            ("health.check", "192.168.1.1"): (True, 22.0),
        }

        # Hardware & Driver Audit
        self.adapter_hardware = AdapterHardwareInfo(
            adapter_name="Ethernet",
            interface_description="Intel(R) Ethernet Connection (7) I219-V",
            driver_name="e1d68x64.sys",
            driver_provider="Intel",
            driver_version="12.19.2.55",
            driver_date="2023-08-15",
            link_speed_mbps=1000,
            duplex="Full Duplex",
            eee_power_saving_enabled=False,
            is_physical=True,
            is_outdated=False,
            status="Up",
        )

        # Firewall Audit
        self.firewall_audit = FirewallAuditInfo(
            domain_profile_enabled=True,
            private_profile_enabled=True,
            public_profile_enabled=True,
            port_53_blocked=False,
            port_853_dot_blocked=False,
            icmp_echo_blocked=False,
            webrtc_blocked=False,
            active_rules=[
                FirewallRuleState(name="DNS-UDP-Out", direction="Outbound", action="Allow", protocol="UDP", remote_port="53"),
                FirewallRuleState(name="DNS-TCP-Out", direction="Outbound", action="Allow", protocol="TCP", remote_port="53"),
                FirewallRuleState(name="DoT-Out", direction="Outbound", action="Allow", protocol="TCP", remote_port="853"),
                FirewallRuleState(name="ICMPv4-Echo-Out", direction="Outbound", action="Allow", protocol="ICMPv4"),
                FirewallRuleState(name="WebRTC-UDP-Out", direction="Outbound", action="Allow", protocol="UDP", remote_port="3478-3481"),
            ]
        )

        # Connection / Process tracking
        self.active_connections: List[Any] = []
        self.active_processes: Dict[int, str] = {
            4: "System",
            1000: "svchost.exe",
            2000: "explorer.exe",
            5000: "chrome.exe",
            6000: "zoom.exe",
            7000: "qbittorrent.exe",
        }

    def set_active_meeting_app(self, proc_name: str, pid: int = 6000) -> None:
        self.active_processes[pid] = proc_name
        self.consent_store["microphone"].append(proc_name)

    def clear_active_meetings(self) -> None:
        self.consent_store["microphone"].clear()
        self.consent_store["webcam"].clear()

    def generate_audit_report(self) -> NetworkEnvironmentAuditReport:
        """Evaluates hardware and firewall state to produce forensic recommendations."""
        recs = []
        if self.adapter_hardware.is_outdated:
            recs.append(AuditRecommendation(
                category="Driver",
                severity="HIGH",
                title="Outdated Vendor Driver",
                recommendation=f"Upgrade {self.adapter_hardware.interface_description} driver from {self.adapter_hardware.driver_version}.",
                is_actionable=True,
            ))
        if self.adapter_hardware.eee_power_saving_enabled:
            recs.append(AuditRecommendation(
                category="Power Management",
                severity="MEDIUM",
                title="Energy Efficient Ethernet Active",
                recommendation="Disable EEE (Green Ethernet) in NIC Advanced Properties to eliminate packet drop spikes.",
                is_actionable=True,
            ))
        if not self.firewall_audit.domain_profile_enabled:
            recs.append(AuditRecommendation(
                category="Security",
                severity="HIGH",
                title="Firewall Domain Profile Disabled",
                recommendation="Enable Windows Firewall Domain Profile to protect local network.",
                is_actionable=True,
            ))

        # Multi-instance disambiguation
        physical_adapters = [k for k, iface in self.interfaces.items() if iface.get("is_physical")]
        if len(physical_adapters) > 1:
            recs.append(AuditRecommendation(
                category="Adapter",
                severity="INFO",
                title="Multiple Physical Adapters Disambiguated",
                recommendation=f"Disambiguated {len(physical_adapters)} physical adapters: {', '.join(physical_adapters)}.",
                is_actionable=True,
            ))

        # Virtual miniport filtering
        virtual_adapters = [k for k, iface in self.interfaces.items() if not iface.get("is_physical")]
        if virtual_adapters or not self.adapter_hardware.is_physical:
            v_names = list(virtual_adapters)
            if not self.adapter_hardware.is_physical and self.adapter_hardware.adapter_name not in v_names:
                v_names.append(self.adapter_hardware.adapter_name)
            recs.append(AuditRecommendation(
                category="Adapter",
                severity="INFO",
                title="Virtual Miniports Filtered",
                recommendation=f"Filtered {len(v_names)} virtual miniport(s) ({', '.join(v_names)}) from hardware health baseline.",
                is_actionable=True,
            ))

        # Wildcard port rules
        for rule in self.firewall_audit.active_rules:
            if rule.remote_port == "*":
                recs.append(AuditRecommendation(
                    category="Security",
                    severity="MEDIUM",
                    title=f"Wildcard Port Rule Active: {rule.name}",
                    recommendation=f"Restrict wildcard remote port on rule '{rule.name}' to required destination ports.",
                    is_actionable=True,
                ))

        # Conflicting firewall rules
        for conf in self.firewall_audit.conflicting_rules:
            recs.append(AuditRecommendation(
                category="Security",
                severity="HIGH",
                title="Conflicting Firewall Rules Detected",
                recommendation=f"Resolve conflicting rule conflict: {conf}",
                is_actionable=True,
            ))

        # Localized rule names
        for rule in self.firewall_audit.active_rules:
            if any(ord(c) > 127 for c in rule.name):
                recs.append(AuditRecommendation(
                    category="Firewall",
                    severity="LOW",
                    title=f"Localized Firewall Rule Active: {rule.name}",
                    recommendation=f"Verified non-English localized rule name '{rule.name}' handled safely across locales.",
                    is_actionable=True,
                ))

        return NetworkEnvironmentAuditReport(
            adapter_audit=self.adapter_hardware,
            firewall_audit=self.firewall_audit,
            vpn_proxy_audit=VpnProxyInfo(),
            recommendations=recs,
        )


# =====================================================================
# Simulated Windows Platform Adapter implementing IPlatformAdapter
# =====================================================================

class SimulatedPlatformAdapter(IPlatformAdapter):
    """Full-featured platform adapter wired to SimulatedWindowsEnvironment."""

    def __init__(self, env: SimulatedWindowsEnvironment) -> None:
        self.env = env
        self.executed_commands: List[str] = []

    def is_elevated(self) -> bool:
        return self.env.is_admin

    def get_default_gateway(self) -> Optional[str]:
        return self.env.default_gateway

    def get_primary_interface(self) -> Optional[str]:
        # Priority: Physical Ethernet > Physical Wi-Fi > First Physical
        physical_candidates = [
            iface for iface in self.env.interfaces.values()
            if iface.get("is_physical") and iface.get("is_up")
        ]
        if not physical_candidates:
            # Fallback to any active non-loopback interface
            for name, iface in self.env.interfaces.items():
                if iface.get("is_up"):
                    return name
            return "Wi-Fi"

        # Sort by metric / type
        ethernet = next((c["alias"] for c in physical_candidates if "ethernet" in c["alias"].lower() and "v" not in c["alias"].lower()), None)
        if ethernet:
            return ethernet
        wifi = next((c["alias"] for c in physical_candidates if "wi-fi" in c["alias"].lower() or "wlan" in c["alias"].lower()), None)
        if wifi:
            return wifi
        return physical_candidates[0]["alias"]

    def ping(self, target: str, timeout_sec: float = 1.5) -> Tuple[bool, float]:
        self.executed_commands.append(f"ping {target}")
        if not target or not isinstance(target, str):
            return False, 0.0

        # Check firewall block on ICMP
        if self.env.firewall_audit.icmp_echo_blocked:
            return False, 0.0

        if target in self.env.ping_targets:
            ok, lat = self.env.ping_targets[target]
            return ok, lat if ok else 0.0

        # Default fallback: check if standard IP pattern
        import re
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", target):
            if target.startswith("192.0.2.") or target.startswith("198.51.100."):
                return False, 0.0
            return True, 18.5
        elif target == "localhost":
            return True, 0.5
        return False, 0.0

    def tcp_connect(self, target: str, port: int = 80, timeout_sec: float = 2.0) -> Tuple[bool, float]:
        self.executed_commands.append(f"tcp_connect {target}:{port}")
        return True, 15.0

    def flush_dns_cache(self) -> Tuple[bool, str]:
        self.executed_commands.append("flush_dns_cache")
        self.env.dns_cache_flushed_count += 1
        return True, "Successfully flushed the DNS Resolver Cache via Win32 Dnsapi."

    def get_interface_dns_servers(self, interface_name: str) -> List[str]:
        iface = self.env.interfaces.get(interface_name)
        if iface:
            v4 = iface.get("ipv4_dns", [])
            v6 = iface.get("ipv6_dns", [])
            return list(v4) + list(v6)
        return []

    def get_interface_dns_mode(self, interface_name: str) -> str:
        iface = self.env.interfaces.get(interface_name)
        return iface.get("dns_mode", "dhcp") if iface else "dhcp"

    def get_interface_ipv6_dns_mode(self, interface_name: str) -> str:
        iface = self.env.interfaces.get(interface_name)
        return iface.get("dns_mode", "dhcp") if iface else "dhcp"

    def set_interface_dns_servers(self, interface_name: str, servers: List[str]) -> Tuple[bool, str]:
        self.executed_commands.append(f"set_interface_dns_servers {interface_name} {servers}")
        if not self.is_elevated():
            return False, "Requires Administrator privileges to modify network adapter DNS."

        iface = self.env.interfaces.get(interface_name)
        if not iface:
            return False, f"Interface '{interface_name}' not found."

        v4 = [s for s in servers if ":" not in s]
        v6 = [s for s in servers if ":" in s]

        if not servers:
            iface["ipv4_dns"] = []
            iface["ipv6_dns"] = []
            iface["dns_mode"] = "dhcp"
            self.flush_dns_cache()
            return True, f"Configured DNS on {interface_name} to DHCP."

        iface["ipv4_dns"] = list(v4)
        iface["ipv6_dns"] = list(v6)
        iface["dns_mode"] = "static"
        self.flush_dns_cache()
        return True, f"Configured DNS on {interface_name} to {', '.join(servers)}."

    def renew_ip_lease(self, interface_name: str) -> Tuple[bool, str]:
        self.executed_commands.append(f"renew_ip_lease {interface_name}")
        if not self.is_elevated():
            return False, "DHCP renewal requires Windows Administrator privileges."
        self.env.dhcp_renew_count += 1
        return True, f"DHCP lease renewed successfully for {interface_name}."

    def get_wifi_metrics(self, interface_name: Optional[str] = None) -> Dict[str, Any]:
        self.executed_commands.append("get_wifi_metrics")
        # Check if Wi-Fi interface exists and is connected
        wifi_iface = self.env.interfaces.get("Wi-Fi")
        if not wifi_iface or not wifi_iface.get("is_up"):
            return {
                "is_wifi": False,
                "signal_percent": 0.0,
                "ssid": None,
                "bssid": None,
                "rx_rate_mbps": 0.0,
                "tx_rate_mbps": 0.0,
            }
        return dict(self.env.wifi_metrics)

    def get_interface_io_counters(self, interface_name: Optional[str] = None) -> Dict[str, int]:
        """Query adapter statistics and packet error/drop counters."""
        self.executed_commands.append("get_interface_io_counters")
        iface_name = interface_name or self.get_primary_interface() or "Wi-Fi"
        data = self.env.interfaces.get(iface_name, {})
        return {
            "errin": data.get("errin", 0),
            "errout": data.get("errout", 0),
            "dropin": data.get("dropin", 0),
            "dropout": data.get("dropout", 0),
        }

    def get_qos_policies(self, policy_store: str = "ActiveStore") -> List[Dict[str, Any]]:
        self.executed_commands.append("get_qos_policies")
        policies = []
        for name, p in self.env.qos_policies.items():
            policies.append({
                "name": p.get("Name", name),
                "app_name": p.get("AppPathNameMatchCondition", ""),
                "throttle_bps": p.get("ThrottleRateActionBitsPerSecond"),
                "dscp_action": p.get("DSCPAction"),
            })
        return policies

    def create_qos_dscp_policy(self, name: str, app_name: str, dscp_value: int = 46) -> Tuple[bool, str]:
        self.executed_commands.append(f"create_qos_dscp_policy {name} {app_name} {dscp_value}")
        if not self.is_elevated():
            return False, "Access denied: Requires administrator privileges to create QoS policy."

        if name in self.env.qos_policies:
            return True, f"QoS policy '{name}' already exists."

        self.env.qos_policies[name] = {
            "Name": name,
            "AppPathNameMatchCondition": app_name,
            "DSCPAction": dscp_value,
            "ThrottleRateActionBitsPerSecond": None,
        }
        return True, f"Successfully created DSCP {dscp_value} QoS policy for {app_name}."

    def create_qos_throttle_policy(self, name: str, app_name: str, throttle_bps: int) -> Tuple[bool, str]:
        self.executed_commands.append(f"create_qos_throttle_policy {name} {app_name} {throttle_bps}")
        if not self.is_elevated():
            return False, "Access denied: Requires administrator privileges to throttle upload bandwidth."

        if name in self.env.qos_policies:
            return True, f"QoS throttle policy '{name}' already exists."

        self.env.qos_policies[name] = {
            "Name": name,
            "AppPathNameMatchCondition": app_name,
            "DSCPAction": None,
            "ThrottleRateActionBitsPerSecond": throttle_bps,
        }
        mbps = throttle_bps / 1_000_000.0
        return True, f"Successfully throttled upload bandwidth for {app_name} to {mbps:.1f} Mbps."

    def remove_qos_policy(self, name: str, policy_store: str = "ActiveStore") -> Tuple[bool, str]:
        self.executed_commands.append(f"remove_qos_policy {name}")
        if not self.is_elevated():
            return False, "Access denied: Requires administrator privileges to remove QoS policy."

        if name in self.env.qos_policies:
            del self.env.qos_policies[name]
            return True, f"Removed QoS policy '{name}' successfully."
        return True, f"QoS policy '{name}' does not exist."

    def sweep_all_netguard_rules(self) -> Tuple[bool, str]:
        self.executed_commands.append("sweep_all_netguard_rules")
        if not self.is_elevated():
            return False, "Requires administrator privileges to sweep policies."

        keys_to_del = [k for k in self.env.qos_policies if k.startswith("NetGuard_")]
        for k in keys_to_del:
            del self.env.qos_policies[k]
        return True, f"Swept {len(keys_to_del)} residual NetGuard policies."


class Pass4SimulatedPlatformAdapter(SimulatedPlatformAdapter):
    """Extended simulated adapter implementing Pass 4 ActiveStore readback verification and lock safety."""

    def __init__(self, env: SimulatedWindowsEnvironment) -> None:
        super().__init__(env)
        self._qos_lock = threading.Lock()
        self.last_qos_batch_report: Dict[str, Any] = {}
        self.simulate_batch_failure: bool = False
        self.simulate_dscp_mismatch: bool = False
        self.simulate_empty_verified: bool = False
        self.simulate_lingering_policy_on_sweep: bool = False
        self.simulate_lock_contention: bool = False
        self.simulate_readback_failure: Optional[str] = None

    def apply_qos_policies_batch(self, specs: List[Any]) -> Tuple[bool, str]:
        if self.simulate_lock_contention:
            return False, "Single-flight lock contention"
        acquired = self._qos_lock.acquire(blocking=False)
        if not acquired:
            return False, "Single-flight lock contention"
        try:
            if not self.is_elevated():
                return False, "Requires Administrator privileges"

            created: List[str] = []
            verified: List[str] = []
            failed: List[str] = []
            details: Dict[str, Any] = {}

            for spec in specs:
                name = getattr(spec, "name", str(spec))
                if self.simulate_batch_failure or (self.simulate_readback_failure and self.simulate_readback_failure in name):
                    failed.append(name)
                    details[name] = {"created": False, "error": "Simulated ActiveStore error"}
                else:
                    created.append(name)
                    stored_dscp = 0 if self.simulate_dscp_mismatch else getattr(spec, "dscp", None)
                    policy_dict = {
                        "Name": name,
                        "AppPathNameMatchCondition": getattr(spec, "app_name", ""),
                        "IPProtocolMatchCondition": getattr(spec, "protocol", None),
                        "DSCPAction": stored_dscp,
                        "ThrottleRateActionBitsPerSecond": getattr(spec, "throttle_bps", None),
                        "Precedence": getattr(spec, "precedence", None),
                        "PolicyStore": getattr(spec, "policy_store", "ActiveStore"),
                    }
                    self.env.qos_policies[name] = policy_dict

                    # Verification checks matching properties
                    req_dscp = getattr(spec, "dscp", None)
                    if not self.simulate_empty_verified and (req_dscp is None or stored_dscp == req_dscp):
                        verified.append(name)
                    else:
                        failed.append(name)

                    details[name] = {"created": True, "properties": policy_dict}

            self.last_qos_batch_report = {
                "created": created,
                "verified": verified,
                "failed": failed,
                "details": details,
            }
            ok = (len(failed) == 0 and len(verified) == len(specs))
            return ok, f"Batch processed: {len(verified)} verified, {len(failed)} failed"
        finally:
            self._qos_lock.release()

    def sweep_all_netguard_rules(self) -> Tuple[bool, str]:
        acquired = self._qos_lock.acquire(timeout=5.0)
        if not acquired:
            return False, "Single-flight lock timeout"
        try:
            if not self.is_elevated():
                return False, "Requires Administrator privileges"

            keys_to_del = [k for k in self.env.qos_policies if k.startswith("NetGuard_")]
            if self.simulate_lingering_policy_on_sweep and keys_to_del:
                keys_to_del = keys_to_del[:-1]

            for k in keys_to_del:
                del self.env.qos_policies[k]

            remaining = len([k for k in self.env.qos_policies if k.startswith("NetGuard_")])
            if remaining > 0:
                return False, f"{remaining} policies failed to remove"
            return True, f"Cleaned {len(keys_to_del)} policies"
        finally:
            self._qos_lock.release()

    def remove_qos_policy(self, name: str, policy_store: str = "ActiveStore") -> Tuple[bool, str]:
        return super().remove_qos_policy(name)


# =====================================================================
# Pytest Fixtures
# =====================================================================

@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Ensure a headless offscreen QApplication exists for UI and QTest components."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


@pytest.fixture
def sim_win() -> SimulatedWindowsEnvironment:
    """Provide a fresh simulated Windows environment for each test."""
    return SimulatedWindowsEnvironment()


@pytest.fixture
def sim_platform(sim_win: SimulatedWindowsEnvironment) -> SimulatedPlatformAdapter:
    """Provide a simulated Windows platform adapter."""
    return SimulatedPlatformAdapter(sim_win)


@pytest.fixture
def pass4_platform(sim_win: SimulatedWindowsEnvironment) -> Pass4SimulatedPlatformAdapter:
    """Provide an extended Pass 4 platform adapter with batch QoS and readback."""
    return Pass4SimulatedPlatformAdapter(sim_win)


@pytest.fixture
def pass4_adapter(sim_win: SimulatedWindowsEnvironment) -> Pass4SimulatedPlatformAdapter:
    """Alias for pass4_platform."""
    return Pass4SimulatedPlatformAdapter(sim_win)


@pytest.fixture
def anim_clock(qapp) -> AnimationMasterClock:
    """Provide a clean AnimationMasterClock instance with stopped timer for deterministic stepping."""
    clock = AnimationMasterClock(fps=20)
    clock.stop()
    yield clock
    clock.stop()


@pytest.fixture
def traffic_controller(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter) -> TrafficController:
    """Provide a production TrafficController instance with active PID-to-process-name caching."""
    return TrafficController(
        event_bus=event_bus,
        platform=sim_platform,
    )


@pytest.fixture
def pid_cache(traffic_controller: TrafficController) -> TrafficController:
    """Backwards-compatible alias returning TrafficController."""
    return traffic_controller


@pytest.fixture
def event_bus() -> EventBus:
    """Provide an isolated asynchronous EventBus instance."""
    return EventBus()


@pytest.fixture
def temp_db() -> DatabaseManager:
    """Provide an isolated in-memory/tempfile SQLite DatabaseManager with WAL mode enabled."""
    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_file.close()

    db = DatabaseManager(db_path=db_file.name)

    yield db

    try:
        db.close()
    except Exception:
        pass
    try:
        if os.path.exists(db_file.name):
            os.remove(db_file.name)
    except Exception:
        pass


@pytest.fixture
def audit_repo(temp_db: DatabaseManager) -> AuditRepository:
    return AuditRepository(temp_db)


@pytest.fixture
def incident_repo(temp_db: DatabaseManager) -> IncidentRepository:
    return IncidentRepository(temp_db)


@pytest.fixture
def measurement_repo(temp_db: DatabaseManager) -> MeasurementRepository:
    return MeasurementRepository(temp_db)
