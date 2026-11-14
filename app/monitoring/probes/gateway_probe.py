"""Default Gateway Reachability and Latency Probe."""

from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import List, Optional
from app.monitoring.probes.base import BaseProbe
from app.monitoring.models.probe_result import ProbeResult
from app.core.models.metrics import MetricType, ProbeStatus, MeasurementSource
from app.platform.interfaces import IPlatformAdapter


class GatewayProbe(BaseProbe):
    """Probes the local default IPv4 gateway for reachability, latency, and packet loss."""

    def __init__(
        self,
        platform_adapter: IPlatformAdapter,
        interval_sec: float = 1.0,
        timeout_sec: float = 1.5,
        target_override: Optional[str] = None,
    ) -> None:
        super().__init__(
            name="gateway_probe",
            interval_sec=interval_sec,
            timeout_sec=timeout_sec,
            platform_adapter=platform_adapter,
        )
        self.target_override = target_override

    async def execute(self) -> List[ProbeResult]:
        gw = self.target_override or self.platform.get_default_gateway()
        now = datetime.now(timezone.utc)

        if not gw:
            return [
                ProbeResult(
                    timestamp=now,
                    source=MeasurementSource.WINDOWS_IPHLP,
                    target="gateway",
                    metric_type=MetricType.GATEWAY_REACHABILITY,
                    raw_value=0.0,
                    normalized_value=0.0,
                    unit="bool",
                    status=ProbeStatus.UNAVAILABLE,
                    confidence=1.0,
                    error_message="No default gateway detected on active interfaces",
                )
            ]

        # Execute ping via executor to keep event loop unblocked
        loop = asyncio.get_running_loop()
        success, latency_ms = await loop.run_in_executor(
            None, self.platform.ping, gw, self.timeout_sec
        )

        results: List[ProbeResult] = []
        if success:
            results.append(
                ProbeResult(
                    timestamp=now,
                    source=MeasurementSource.ICMP_ECHO,
                    target=gw,
                    metric_type=MetricType.GATEWAY_REACHABILITY,
                    raw_value=1.0,
                    normalized_value=1.0,
                    unit="bool",
                    status=ProbeStatus.SUCCESS,
                    confidence=1.0,
                    latency_ms=latency_ms,
                )
            )
            results.append(
                ProbeResult(
                    timestamp=now,
                    source=MeasurementSource.ICMP_ECHO,
                    target=gw,
                    metric_type=MetricType.GATEWAY_LATENCY,
                    raw_value=latency_ms,
                    normalized_value=latency_ms,
                    unit="ms",
                    status=ProbeStatus.SUCCESS,
                    confidence=1.0,
                    latency_ms=latency_ms,
                )
            )
            results.append(
                ProbeResult(
                    timestamp=now,
                    source=MeasurementSource.ICMP_ECHO,
                    target=gw,
                    metric_type=MetricType.GATEWAY_PACKET_LOSS,
                    raw_value=0.0,
                    normalized_value=0.0,
                    unit="ratio",
                    status=ProbeStatus.SUCCESS,
                    confidence=1.0,
                    packet_loss_ratio=0.0,
                )
            )
        else:
            results.append(
                ProbeResult(
                    timestamp=now,
                    source=MeasurementSource.ICMP_ECHO,
                    target=gw,
                    metric_type=MetricType.GATEWAY_REACHABILITY,
                    raw_value=0.0,
                    normalized_value=0.0,
                    unit="bool",
                    status=ProbeStatus.FAILED,
                    confidence=0.9,
                    error_message=f"Gateway {gw} failed to respond to echo probe",
                )
            )
            results.append(
                ProbeResult(
                    timestamp=now,
                    source=MeasurementSource.ICMP_ECHO,
                    target=gw,
                    metric_type=MetricType.GATEWAY_PACKET_LOSS,
                    raw_value=1.0,
                    normalized_value=1.0,
                    unit="ratio",
                    status=ProbeStatus.FAILED,
                    confidence=0.9,
                    packet_loss_ratio=1.0,
                )
            )
        return results

    def _handle_timeout(self) -> List[ProbeResult]:
        gw = self.target_override or self.platform.get_default_gateway() or "unknown"
        now = datetime.now(timezone.utc)
        return [
            ProbeResult(
                timestamp=now,
                source=MeasurementSource.ICMP_ECHO,
                target=gw,
                metric_type=MetricType.GATEWAY_REACHABILITY,
                raw_value=0.0,
                normalized_value=0.0,
                unit="bool",
                status=ProbeStatus.TIMEOUT,
                confidence=0.85,
                error_message="Gateway probe timed out",
            ),
            ProbeResult(
                timestamp=now,
                source=MeasurementSource.ICMP_ECHO,
                target=gw,
                metric_type=MetricType.GATEWAY_PACKET_LOSS,
                raw_value=1.0,
                normalized_value=1.0,
                unit="ratio",
                status=ProbeStatus.TIMEOUT,
                confidence=0.85,
                packet_loss_ratio=1.0,
            ),
        ]
