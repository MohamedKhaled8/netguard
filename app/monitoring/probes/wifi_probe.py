"""Wi-Fi Signal and Link Quality Collector."""

from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import List, Optional
from app.monitoring.probes.base import BaseProbe
from app.monitoring.models.probe_result import ProbeResult
from app.core.models.metrics import MetricType, ProbeStatus, MeasurementSource
from app.platform.interfaces import IPlatformAdapter


class WifiMetricsCollector(BaseProbe):
    """Monitors Wi-Fi signal percentage and link speed via platform adapter."""

    def __init__(
        self,
        platform_adapter: IPlatformAdapter,
        interval_sec: float = 3.0,
        timeout_sec: float = 2.0,
    ) -> None:
        super().__init__(
            name="wifi_metrics_collector",
            interval_sec=interval_sec,
            timeout_sec=timeout_sec,
            platform_adapter=platform_adapter,
        )

    async def execute(self) -> List[ProbeResult]:
        loop = asyncio.get_running_loop()
        now = datetime.now(timezone.utc)

        info = await loop.run_in_executor(None, self.platform.get_wifi_metrics)
        if not info.get("is_wifi"):
            return []

        results: List[ProbeResult] = []
        signal_pct = float(info.get("signal_percent", 0.0))
        rx_mbps = float(info.get("rx_rate_mbps", 0.0))

        results.append(
            ProbeResult(
                timestamp=now,
                source=MeasurementSource.WINDOWS_NETSH,
                target=info.get("ssid") or "wifi",
                metric_type=MetricType.WIFI_SIGNAL_PERCENT,
                raw_value=signal_pct,
                normalized_value=signal_pct,
                unit="percent",
                status=ProbeStatus.SUCCESS if signal_pct > 15.0 else ProbeStatus.DEGRADED,
                confidence=1.0,
                metadata={"bssid": info.get("bssid"), "ssid": info.get("ssid")},
            )
        )

        if rx_mbps > 0.0:
            results.append(
                ProbeResult(
                    timestamp=now,
                    source=MeasurementSource.WINDOWS_NETSH,
                    target=info.get("ssid") or "wifi",
                    metric_type=MetricType.WIFI_LINK_SPEED_MBPS,
                    raw_value=rx_mbps,
                    normalized_value=rx_mbps,
                    unit="mbps",
                    status=ProbeStatus.SUCCESS,
                    confidence=1.0,
                    metadata={"tx_rate_mbps": info.get("tx_rate_mbps")},
                )
            )

        return results
