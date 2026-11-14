"""External Connectivity Probe measuring latency, packet loss, TCP connect, and jitter."""

from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Dict
from app.monitoring.probes.base import BaseProbe
from app.monitoring.models.probe_result import ProbeResult
from app.core.models.metrics import MetricType, ProbeStatus, MeasurementSource
from app.platform.interfaces import IPlatformAdapter


class ExternalConnectivityProbe(BaseProbe):
    """Probes multiple independent WAN targets using dual-channel ICMP and TCP connection."""

    def __init__(
        self,
        platform_adapter: IPlatformAdapter,
        targets: Optional[List[str]] = None,
        interval_sec: float = 3.0,
        timeout_sec: float = 2.0,
    ) -> None:
        super().__init__(
            name="external_probe",
            interval_sec=interval_sec,
            timeout_sec=timeout_sec,
            platform_adapter=platform_adapter,
        )
        self.targets = targets or ["1.1.1.1", "8.8.8.8", "9.9.9.9", "208.67.222.222"]
        # History per target for jitter computation: list of recent latencies
        self._latency_history: Dict[str, List[float]] = {t: [] for t in self.targets}
        self._current_jitter_ms: Dict[str, float] = {t: 0.0 for t in self.targets}

    async def execute(self) -> List[ProbeResult]:
        loop = asyncio.get_running_loop()
        now = datetime.now(timezone.utc)
        results: List[ProbeResult] = []

        # Run probes across targets concurrently
        tasks = [self._probe_single_target(loop, target, now) for target in self.targets]
        target_results = await asyncio.gather(*tasks, return_exceptions=True)

        for res_list in target_results:
            if isinstance(res_list, list):
                results.extend(res_list)

        return results

    async def _probe_single_target(self, loop: asyncio.AbstractEventLoop, target: str, now: datetime) -> List[ProbeResult]:
        results: List[ProbeResult] = []

        # 1. Ping probe
        ping_success, ping_latency = await loop.run_in_executor(
            None, self.platform.ping, target, self.timeout_sec
        )

        # 2. Fallback / Corroborating TCP probe (Port 53 DNS or Port 443 HTTPS)
        # Port 53 on 1.1.1.1, 8.8.8.8, 9.9.9.9 is standard and universally open
        tcp_port = 53
        tcp_success, tcp_latency = await loop.run_in_executor(
            None, self.platform.tcp_connect, target, tcp_port, self.timeout_sec
        )

        # Record TCP probe
        results.append(
            ProbeResult(
                timestamp=now,
                source=MeasurementSource.TCP_CONNECT,
                target=f"{target}:{tcp_port}",
                metric_type=MetricType.EXTERNAL_TCP_CONNECT,
                raw_value=1.0 if tcp_success else 0.0,
                normalized_value=1.0 if tcp_success else 0.0,
                unit="bool",
                status=ProbeStatus.SUCCESS if tcp_success else ProbeStatus.FAILED,
                confidence=1.0,
                latency_ms=tcp_latency if tcp_success else None,
                metadata={"port": tcp_port},
            )
        )

        # Compute effective latency and packet loss
        effective_latency = ping_latency if ping_success else (tcp_latency if tcp_success else 0.0)
        overall_success = ping_success or tcp_success

        if overall_success:
            results.append(
                ProbeResult(
                    timestamp=now,
                    source=MeasurementSource.ICMP_ECHO if ping_success else MeasurementSource.TCP_CONNECT,
                    target=target,
                    metric_type=MetricType.EXTERNAL_LATENCY,
                    raw_value=effective_latency,
                    normalized_value=effective_latency,
                    unit="ms",
                    status=ProbeStatus.SUCCESS,
                    confidence=1.0,
                    latency_ms=effective_latency,
                    metadata={"icmp": ping_success, "tcp": tcp_success},
                )
            )
            results.append(
                ProbeResult(
                    timestamp=now,
                    source=MeasurementSource.ICMP_ECHO if ping_success else MeasurementSource.TCP_CONNECT,
                    target=target,
                    metric_type=MetricType.EXTERNAL_PACKET_LOSS,
                    raw_value=0.0,
                    normalized_value=0.0,
                    unit="ratio",
                    status=ProbeStatus.SUCCESS,
                    confidence=1.0,
                    packet_loss_ratio=0.0,
                )
            )

            # Calculate RFC 3550 Jitter
            history = self._latency_history.setdefault(target, [])
            history.append(effective_latency)
            if len(history) > 20:
                history.pop(0)

            if len(history) >= 2:
                # D(i, j) = |lat_j - lat_i|
                diff = abs(history[-1] - history[-2])
                old_jitter = self._current_jitter_ms.get(target, 0.0)
                # Jitter = Jitter + (diff - Jitter) / 16
                new_jitter = old_jitter + (diff - old_jitter) / 16.0
                self._current_jitter_ms[target] = new_jitter

                results.append(
                    ProbeResult(
                        timestamp=now,
                        source=MeasurementSource.ICMP_ECHO if ping_success else MeasurementSource.TCP_CONNECT,
                        target=target,
                        metric_type=MetricType.JITTER_MS,
                        raw_value=new_jitter,
                        normalized_value=new_jitter,
                        unit="ms",
                        status=ProbeStatus.SUCCESS,
                        confidence=0.95,
                    )
                )
        else:
            # Both ICMP and TCP failed for this target
            results.append(
                ProbeResult(
                    timestamp=now,
                    source=MeasurementSource.ICMP_ECHO,
                    target=target,
                    metric_type=MetricType.EXTERNAL_PACKET_LOSS,
                    raw_value=1.0,
                    normalized_value=1.0,
                    unit="ratio",
                    status=ProbeStatus.FAILED,
                    confidence=0.9,
                    packet_loss_ratio=1.0,
                    error_message=f"Target {target} unreachable via ICMP and TCP",
                )
            )
        return results

    def _handle_timeout(self) -> List[ProbeResult]:
        now = datetime.now(timezone.utc)
        results = []
        for target in self.targets:
            results.append(
                ProbeResult(
                    timestamp=now,
                    source=MeasurementSource.ICMP_ECHO,
                    target=target,
                    metric_type=MetricType.EXTERNAL_PACKET_LOSS,
                    raw_value=1.0,
                    normalized_value=1.0,
                    unit="ratio",
                    status=ProbeStatus.TIMEOUT,
                    confidence=0.8,
                    packet_loss_ratio=1.0,
                    error_message="External connectivity probe execution deadline exceeded",
                )
            )
        return results
