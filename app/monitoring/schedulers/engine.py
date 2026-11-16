"""Observability Engine and Asynchronous Probe Scheduler."""

from __future__ import annotations
import asyncio
import logging
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional
from app.core.config.models import ProbingConfig
from app.core.bus import EventBus, EventTopics
from app.core.models.metrics import Measurement, MetricType
from app.monitoring.models.probe_result import ProbeResult
from app.monitoring.probes.base import BaseProbe
from app.monitoring.probes.gateway_probe import GatewayProbe
from app.monitoring.probes.external_probe import ExternalConnectivityProbe
from app.monitoring.probes.dns_probe import DNSResolutionProbe
from app.monitoring.probes.interface_probe import InterfaceStatsCollector
from app.monitoring.probes.wifi_probe import WifiMetricsCollector
from app.monitoring.probes.socket_probe import ActiveConnectionCollector
from app.platform.interfaces import IPlatformAdapter
from app.storage.repositories.measurement_repo import MeasurementRepository

logger = logging.getLogger("netguard.monitoring.engine")


class ObservabilityEngine:
    """Coordinates asynchronous probes, normalizes metrics, persists data, and streams to bus."""

    def __init__(
        self,
        config: ProbingConfig,
        event_bus: EventBus,
        platform_adapter: IPlatformAdapter,
        measurement_repo: MeasurementRepository,
        window_size: int = 30,
    ) -> None:
        self.config = config
        self.event_bus = event_bus
        self.platform = platform_adapter
        self.repo = measurement_repo
        self.window_size = window_size

        self._probes: List[BaseProbe] = []
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._sliding_windows: Dict[MetricType, deque[Measurement]] = {
            m: deque(maxlen=window_size) for m in MetricType
        }
        self._lock = asyncio.Lock()

        self._initialize_probes()

    def _initialize_probes(self) -> None:
        """Instantiate configured probes."""
        self._probes = [
            GatewayProbe(
                platform_adapter=self.platform,
                interval_sec=self.config.gateway_interval_sec,
                timeout_sec=self.config.icmp_timeout_sec,
            ),
            ExternalConnectivityProbe(
                platform_adapter=self.platform,
                targets=self.config.external_targets,
                interval_sec=self.config.external_interval_sec,
                timeout_sec=self.config.tcp_timeout_sec,
            ),
            DNSResolutionProbe(
                platform_adapter=self.platform,
                domains=self.config.dns_test_domains,
                interval_sec=self.config.dns_interval_sec,
                timeout_sec=self.config.dns_timeout_sec,
            ),
            InterfaceStatsCollector(
                platform_adapter=self.platform,
                interval_sec=self.config.interface_stats_interval_sec,
            ),
            WifiMetricsCollector(
                platform_adapter=self.platform,
                interval_sec=3.0,
            ),
            ActiveConnectionCollector(
                platform_adapter=self.platform,
                interval_sec=self.config.active_connections_interval_sec,
            ),
        ]

    def register_probe(self, probe: BaseProbe) -> None:
        """Register custom probe (e.g. for mock testing or cellular modem)."""
        self._probes.append(probe)

    async def start(self) -> None:
        """Start asynchronous probing loops for all registered probes."""
        if self._running:
            return
        self._running = True
        logger.info("Starting Observability Engine with %d probes...", len(self._probes))

        for probe in self._probes:
            task = asyncio.create_task(self._probe_worker(probe), name=f"worker_{probe.name}")
            self._tasks.append(task)

    async def stop(self) -> None:
        """Gracefully stop all probe workers."""
        if not self._running:
            return
        self._running = False
        logger.info("Stopping Observability Engine workers...")

        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("Observability Engine stopped cleanly.")

    async def run_single_cycle(self) -> List[Measurement]:
        """Runs one sample cycle of all registered probes immediately (useful for testing or on-demand)."""
        all_measurements: List[Measurement] = []
        tasks = [probe.run() for probe in self._probes]
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

        for results in results_lists:
            if isinstance(results, list):
                for pr in results:
                    m = pr.to_measurement()
                    await self._record_measurement(m)
                    all_measurements.append(m)
        return all_measurements

    async def _probe_worker(self, probe: BaseProbe) -> None:
        """Infinite loop worker for an individual probe with interval pacing."""
        while self._running:
            try:
                results = await probe.run()
                for pr in results:
                    m = pr.to_measurement()
                    await self._record_measurement(m)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error in probe worker %s: %s", probe.name, exc, exc_info=True)

            try:
                await asyncio.sleep(probe.interval_sec)
            except asyncio.CancelledError:
                break

    async def _record_measurement(self, m: Measurement) -> None:
        """Buffers measurement in sliding window, persists to SQLite, and broadcasts to event bus."""
        async with self._lock:
            # Store in sliding window
            if m.metric_type not in self._sliding_windows:
                self._sliding_windows[m.metric_type] = deque(maxlen=self.window_size)
            self._sliding_windows[m.metric_type].append(m)

        # Persist to database asynchronously (via thread executor to prevent blocking async loop)
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self.repo.save, m)
        except Exception as exc:
            logger.warning("Failed to persist measurement %s: %s", m.metric_type.value, exc)

        # Publish event
        topic = f"{EventTopics.TELEMETRY_PREFIX}{m.metric_type.value}"
        await self.event_bus.publish(topic, m)

    def get_sliding_window(self, metric_type: MetricType) -> List[Measurement]:
        """Returns a snapshot of the most recent measurements for the given metric."""
        if metric_type in self._sliding_windows:
            return list(self._sliding_windows[metric_type])
        return []

    def get_latest_measurement(self, metric_type: MetricType) -> Optional[Measurement]:
        """Returns the single most recent measurement for the given metric."""
        window = self._sliding_windows.get(metric_type)
        if window and len(window) > 0:
            return window[-1]
        return None
