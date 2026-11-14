"""Cellular Network Intelligence Engine."""

from __future__ import annotations
import logging
from typing import List, Optional
from app.core.events.bus import EventBus
from app.cellular.models import CellularMetrics
from app.router.base import BaseRouterAdapter
from app.router.generic import GenericRouterAdapter
from app.router.hilink import HuaweiHiLinkAdapter

logger = logging.getLogger("netguard.cellular.engine")


class CellularDiagnosticsEngine:
    """Manages cellular radio signal polling and model-specific adapter discovery."""

    def __init__(self, gateway_ip: str, event_bus: EventBus) -> None:
        self.gateway_ip = gateway_ip
        self.event_bus = event_bus
        self.adapter: BaseRouterAdapter = GenericRouterAdapter(gateway_ip)
        self._history: List[CellularMetrics] = []

    async def auto_discover_adapter(self) -> BaseRouterAdapter:
        """Tries known router adapters before falling back to generic."""
        hilink = HuaweiHiLinkAdapter(self.gateway_ip)
        model = await hilink.detect_model()
        if model:
            logger.info("Auto-detected router adapter: %s", model)
            self.adapter = hilink
            return hilink

        # Generic probe
        generic = GenericRouterAdapter(self.gateway_ip)
        model = await generic.detect_model()
        logger.info("Using router adapter: %s (%s)", model or "Generic Gateway", self.gateway_ip)
        self.adapter = generic
        return generic

    async def poll_metrics(self) -> Optional[CellularMetrics]:
        """Poll cellular RF metrics and broadcast on event bus."""
        metrics = await self.adapter.get_cellular_metrics()
        if metrics:
            self._history.append(metrics)
            if len(self._history) > 100:
                self._history.pop(0)
            await self.event_bus.publish("cellular.metrics", metrics.model_dump(mode="json"))
        return metrics

    @property
    def latest_metrics(self) -> Optional[CellularMetrics]:
        return self._history[-1] if self._history else None
