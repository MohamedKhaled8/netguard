"""Interface Statistics and Throughput Collector."""

from __future__ import annotations
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import psutil
from app.monitoring.probes.base import BaseProbe
from app.monitoring.models.probe_result import ProbeResult
from app.core.models.metrics import MetricType, ProbeStatus, MeasurementSource
from app.platform.interfaces import IPlatformAdapter


class InterfaceStatsCollector(BaseProbe):
    """Monitors bytes received/transmitted per second and packet errors across interfaces."""

    def __init__(
        self,
        platform_adapter: IPlatformAdapter,
        target_interface: Optional[str] = None,
        interval_sec: float = 1.0,
        timeout_sec: float = 1.0,
    ) -> None:
        super().__init__(
            name="interface_stats_collector",
            interval_sec=interval_sec,
            timeout_sec=timeout_sec,
            platform_adapter=platform_adapter,
        )
        self.target_interface = target_interface
        self._last_snapshot: Optional[Dict[str, Any]] = None
        self._last_snapshot_time: Optional[float] = None

    async def execute(self) -> List[ProbeResult]:
        loop = asyncio.get_running_loop()
        now = datetime.now(timezone.utc)
        curr_time = time.monotonic()

        # Capture psutil counters in executor
        counters = await loop.run_in_executor(None, psutil.net_io_counters, True)

        active_iface = self.target_interface or self.platform.get_primary_interface()
        if not active_iface or active_iface not in counters:
            # Fallback to total sum across all non-loopback
            active_iface = next(
                (k for k in counters.keys() if "loopback" not in k.lower()), None
            )

        if not active_iface or active_iface not in counters:
            return []

        c = counters[active_iface]
        results: List[ProbeResult] = []

        if self._last_snapshot and self._last_snapshot_time and active_iface in self._last_snapshot:
            prev_c = self._last_snapshot[active_iface]
            delta_t = max(curr_time - self._last_snapshot_time, 0.001)

            rx_bytes_sec = max((c.bytes_recv - prev_c.bytes_recv) / delta_t, 0.0)
            tx_bytes_sec = max((c.bytes_sent - prev_c.bytes_sent) / delta_t, 0.0)

            results.append(
                ProbeResult(
                    timestamp=now,
                    source=MeasurementSource.PSUTIL_INTERFACE,
                    target=active_iface,
                    metric_type=MetricType.BANDWIDTH_RX_BYTES_PER_SEC,
                    raw_value=rx_bytes_sec,
                    normalized_value=rx_bytes_sec,
                    unit="bytes/sec",
                    status=ProbeStatus.SUCCESS,
                    confidence=1.0,
                    metadata={"bytes_total": c.bytes_recv, "packets_recv": c.packets_recv},
                )
            )
            results.append(
                ProbeResult(
                    timestamp=now,
                    source=MeasurementSource.PSUTIL_INTERFACE,
                    target=active_iface,
                    metric_type=MetricType.BANDWIDTH_TX_BYTES_PER_SEC,
                    raw_value=tx_bytes_sec,
                    normalized_value=tx_bytes_sec,
                    unit="bytes/sec",
                    status=ProbeStatus.SUCCESS,
                    confidence=1.0,
                    metadata={"bytes_total": c.bytes_sent, "packets_sent": c.packets_sent},
                )
            )

        # Update snapshots
        self._last_snapshot = counters
        self._last_snapshot_time = curr_time
        return results
