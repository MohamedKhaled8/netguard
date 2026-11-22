"""Single source of truth for DNS state across NetGuard AI.

Authoritative centralized state holding real Windows network configuration,
real DNS query measurements, recommended DNS, applied DNS, and lifecycle states:
Idle, Testing, Comparing, Applying, Verifying, Success, Failed.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Literal, Any
from PySide6.QtCore import QObject, Signal

from app.dns.benchmark import ResolverScore

DNSLifecycleState = Literal["idle", "testing", "comparing", "applying", "verifying", "success", "failed"]


@dataclass
class DnsStateData:
    """Immutable snapshot of the active DNS configuration, benchmark results, and lifecycle state."""

    # 1. Configured Windows DNS
    active_servers: List[str] = field(default_factory=list)
    primary_dns: Optional[str] = None
    secondary_dns: Optional[str] = None
    configured_mode: Literal["dhcp", "static", "doh"] = "dhcp"
    detected_provider: Optional[str] = None
    primary_interface: str = "Wi-Fi"

    # 2. Genuine DNS Performance Measurements
    last_measured_ms: Optional[float] = None
    last_measured_timestamp: Optional[datetime] = None
    min_latency_ms: Optional[float] = None
    max_latency_ms: Optional[float] = None
    mean_latency_ms: Optional[float] = None
    query_success_rate: float = 1.0
    successful_queries_count: int = 0
    failed_queries_count: int = 0
    is_healthy: bool = True
    status_summary: str = ""
    analysis_text: str = ""
    recommendation_text: str = ""

    # 3. Recommended DNS Configuration
    recommended_server: Optional[ResolverScore] = None
    best_server: Optional[ResolverScore] = None  # Backward-compatibility alias
    recommended_primary_dns: Optional[str] = None
    recommended_secondary_dns: Optional[str] = None
    recommended_provider: Optional[str] = None
    recommended_latency_ms: Optional[float] = None
    is_recommended_different: bool = False
    measured_improvement_ms: float = 0.0

    # 4. Applied DNS Configuration & Restoration Snapshot
    applied_servers: List[str] = field(default_factory=list)
    applied_provider: Optional[str] = None
    last_switch_time: Optional[float] = None
    last_changed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    previous_servers: List[str] = field(default_factory=list)
    can_restore: bool = False

    # 5. Full Provider Ranking Table
    scores: List[ResolverScore] = field(default_factory=list)

    # 6. Global Lifecycle & Operation State
    lifecycle_state: DNSLifecycleState = "idle"
    is_benchmarking: bool = False
    status_message: str = ""
    last_error: Optional[str] = None

    # 7. Network / Routing Intelligence
    is_transparent_proxy: bool = False
    egress_resolver: Optional[str] = None

    def __post_init__(self) -> None:
        # Auto-derive primary and secondary DNS from active_servers if omitted
        if self.active_servers:
            if not self.primary_dns and len(self.active_servers) >= 1:
                self.primary_dns = self.active_servers[0]
            if not self.secondary_dns and len(self.active_servers) >= 2:
                self.secondary_dns = self.active_servers[1]

        # Keep best_server and recommended_server synchronized
        if self.recommended_server and not self.best_server:
            self.best_server = self.recommended_server
        elif self.best_server and not self.recommended_server:
            self.recommended_server = self.best_server

        # Synchronize recommended primary and secondary DNS
        if self.recommended_server:
            if not self.recommended_primary_dns:
                self.recommended_primary_dns = getattr(self.recommended_server, "primary_ip", self.recommended_server.ip)
            if not self.recommended_secondary_dns:
                self.recommended_secondary_dns = getattr(self.recommended_server, "secondary_ip", None)
            if not self.recommended_provider:
                self.recommended_provider = getattr(self.recommended_server, "provider_name", self.recommended_server.name)
            if self.recommended_latency_ms is None:
                self.recommended_latency_ms = self.recommended_server.latency_ms

        if self.lifecycle_state == "testing":
            self.is_benchmarking = True
        elif self.lifecycle_state in ("idle", "success", "failed"):
            self.is_benchmarking = False


class DnsStateManager(QObject):
    """Singleton observable manager holding the authoritative DnsState across all pages."""

    state_changed = Signal(object)  # Emits DnsStateData snapshot

    _instance: Optional[DnsStateManager] = None

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._data = DnsStateData()

    @classmethod
    def get_instance(cls) -> DnsStateManager:
        if cls._instance is None:
            cls._instance = DnsStateManager()
        return cls._instance

    @property
    def current(self) -> DnsStateData:
        return self._data

    def update(self, **kwargs) -> None:
        """Update state fields and broadcast changes to all subscribed views."""
        updated = False
        new_dict = self._data.__dict__.copy()

        # Handle active_servers updating primary and secondary
        if "active_servers" in kwargs:
            srvs = kwargs["active_servers"]
            if srvs:
                if "primary_dns" not in kwargs:
                    kwargs["primary_dns"] = srvs[0]
                if "secondary_dns" not in kwargs:
                    kwargs["secondary_dns"] = srvs[1] if len(srvs) >= 2 else None
            else:
                if "primary_dns" not in kwargs:
                    kwargs["primary_dns"] = None
                if "secondary_dns" not in kwargs:
                    kwargs["secondary_dns"] = None

        # Synchronize best_server and recommended_server
        if "best_server" in kwargs and "recommended_server" not in kwargs:
            kwargs["recommended_server"] = kwargs["best_server"]
        elif "recommended_server" in kwargs and "best_server" not in kwargs:
            kwargs["best_server"] = kwargs["recommended_server"]

        for k, v in kwargs.items():
            if k in new_dict and new_dict[k] != v:
                new_dict[k] = v
                updated = True
            elif k not in new_dict:
                new_dict[k] = v
                updated = True

        if updated:
            self._data = DnsStateData(**new_dict)
            self.state_changed.emit(self._data)
