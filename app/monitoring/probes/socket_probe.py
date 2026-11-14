"""Active Network Connections and Process Attribution Collector."""

from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List
import psutil
from app.monitoring.probes.base import BaseProbe
from app.monitoring.models.probe_result import ProbeResult
from app.core.models.metrics import MetricType, ProbeStatus, MeasurementSource
from app.platform.interfaces import IPlatformAdapter


class ActiveConnectionCollector(BaseProbe):
    """Scans active sockets and aggregates connection counts per process."""

    def __init__(
        self,
        platform_adapter: IPlatformAdapter,
        interval_sec: float = 5.0,
        timeout_sec: float = 3.0,
    ) -> None:
        super().__init__(
            name="active_connections_collector",
            interval_sec=interval_sec,
            timeout_sec=timeout_sec,
            platform_adapter=platform_adapter,
        )

    async def execute(self) -> List[ProbeResult]:
        loop = asyncio.get_running_loop()
        now = datetime.now(timezone.utc)

        def _scan():
            connections = psutil.net_connections(kind="inet")
            active_established = [c for c in connections if c.status == psutil.CONN_ESTABLISHED]
            process_counts: Dict[str, int] = {}
            for c in active_established:
                if c.pid:
                    try:
                        pname = psutil.Process(c.pid).name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pname = "unknown"
                else:
                    pname = "system"
                process_counts[pname] = process_counts.get(pname, 0) + 1
            return len(active_established), process_counts

        total_active, pcounts = await loop.run_in_executor(None, _scan)

        return [
            ProbeResult(
                timestamp=now,
                source=MeasurementSource.PSUTIL_INTERFACE,
                target="host_sockets",
                metric_type=MetricType.ACTIVE_SOCKET_COUNT,
                raw_value=float(total_active),
                normalized_value=float(total_active),
                unit="count",
                status=ProbeStatus.SUCCESS,
                confidence=1.0,
                metadata={"by_process": pcounts},
            )
        ]
