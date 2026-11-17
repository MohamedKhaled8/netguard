"""Router Integration Abstraction."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from app.cellular.models import CellularMetrics


class BaseRouterAdapter(ABC):
    """Abstract interface for cellular 4G/5G and broadband router diagnostic APIs."""

    def __init__(self, gateway_ip: str = "192.168.1.1") -> None:
        self.gateway_ip = gateway_ip

    @abstractmethod
    async def detect_model(self) -> Optional[str]:
        """Attempt non-intrusive auto-detection of the router hardware/firmware model."""
        pass

    @abstractmethod
    async def get_cellular_metrics(self) -> Optional[CellularMetrics]:
        """Fetch real-time RF radio metrics (RSRP, RSRQ, SINR, Band, Cell ID) if exposed."""
        pass

    @abstractmethod
    async def get_device_info(self) -> Dict[str, Any]:
        """Retrieve router model, firmware version, and uptime metadata."""
        pass
