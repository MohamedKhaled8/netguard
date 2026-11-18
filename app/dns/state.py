"""Single source of truth for DNS state across NetGuard AI (Item B1)."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Literal
from PySide6.QtCore import QObject, Signal

from app.dns.benchmark import ResolverScore


@dataclass
class DnsStateData:
    """Immutable snapshot of the active DNS configuration and benchmark state."""
    active_servers: List[str] = field(default_factory=list)
    configured_mode: Literal["dhcp", "static", "doh"] = "dhcp"
    detected_provider: Optional[str] = None
    last_measured_ms: Optional[float] = None
    is_healthy: bool = True
    last_changed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    best_server: Optional[ResolverScore] = None
    scores: List[ResolverScore] = field(default_factory=list)
    primary_interface: str = "Wi-Fi"
    is_benchmarking: bool = False
    last_switch_time: Optional[float] = None
    is_transparent_proxy: bool = False
    egress_resolver: Optional[str] = None


class DnsStateManager(QObject):
    """Singleton observable manager holding the authoritative DnsState."""

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
        for k, v in kwargs.items():
            if k in new_dict and new_dict[k] != v:
                new_dict[k] = v
                updated = True
        if updated:
            self._data = DnsStateData(**new_dict)
            self.state_changed.emit(self._data)
