"""DNS Resolution and Latency Probe using dnspython."""

from __future__ import annotations
import asyncio
import time
from datetime import datetime, timezone
from typing import List, Optional
import dns.resolver
from app.monitoring.probes.base import BaseProbe
from app.monitoring.models.probe_result import ProbeResult
from app.core.models.metrics import MetricType, ProbeStatus, MeasurementSource
from app.platform.interfaces import IPlatformAdapter


class DNSResolutionProbe(BaseProbe):
    """Measures DNS query latency, resolution success, and server responsiveness."""

    def __init__(
        self,
        platform_adapter: IPlatformAdapter,
        domains: Optional[List[str]] = None,
        custom_resolver_ip: Optional[str] = None,
        interval_sec: float = 5.0,
        timeout_sec: float = 2.0,
    ) -> None:
        super().__init__(
            name="dns_probe",
            interval_sec=interval_sec,
            timeout_sec=timeout_sec,
            platform_adapter=platform_adapter,
        )
        self.domains = domains or ["google.com", "cloudflare.com", "microsoft.com", "apple.com"]
        self.custom_resolver_ip = custom_resolver_ip

    async def execute(self) -> List[ProbeResult]:
        loop = asyncio.get_running_loop()
        now = datetime.now(timezone.utc)
        results: List[ProbeResult] = []

        tasks = [self._resolve_domain(loop, domain, now) for domain in self.domains]
        domain_results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_queries = 0
        total_latency = 0.0

        for r_list in domain_results:
            if isinstance(r_list, list):
                for res in r_list:
                    results.append(res)
                    if res.metric_type == MetricType.DNS_LATENCY and res.status == ProbeStatus.SUCCESS:
                        successful_queries += 1
                        total_latency += res.raw_value

        # Aggregate DNS success rate
        success_rate = (successful_queries / len(self.domains)) if self.domains else 0.0
        results.append(
            ProbeResult(
                timestamp=now,
                source=MeasurementSource.DNS_QUERY,
                target=self.custom_resolver_ip or "system_dns",
                metric_type=MetricType.DNS_SUCCESS_RATE,
                raw_value=success_rate,
                normalized_value=success_rate,
                unit="ratio",
                status=ProbeStatus.SUCCESS if success_rate > 0.5 else ProbeStatus.FAILED,
                confidence=1.0,
                metadata={"total_domains": len(self.domains), "successful": successful_queries},
            )
        )
        return results

    async def _resolve_domain(self, loop: asyncio.AbstractEventLoop, domain: str, now: datetime) -> List[ProbeResult]:
        resolver = dns.resolver.Resolver()
        resolver.lifetime = self.timeout_sec
        resolver.timeout = self.timeout_sec

        if self.custom_resolver_ip:
            resolver.nameservers = [self.custom_resolver_ip]

        def _sync_query():
            t0 = time.perf_counter()
            answers = resolver.resolve(domain, "A")
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            resolved_ips = [rdata.to_text() for rdata in answers]
            return elapsed_ms, resolved_ips

        try:
            latency_ms, ips = await loop.run_in_executor(None, _sync_query)
            return [
                ProbeResult(
                    timestamp=now,
                    source=MeasurementSource.DNS_QUERY,
                    target=domain,
                    metric_type=MetricType.DNS_LATENCY,
                    raw_value=latency_ms,
                    normalized_value=latency_ms,
                    unit="ms",
                    status=ProbeStatus.SUCCESS,
                    confidence=1.0,
                    latency_ms=latency_ms,
                    metadata={"resolved_ips": ips, "resolver": self.custom_resolver_ip or "default"},
                )
            ]
        except (dns.resolver.Timeout, dns.resolver.NoNameservers) as exc:
            return [
                ProbeResult(
                    timestamp=now,
                    source=MeasurementSource.DNS_QUERY,
                    target=domain,
                    metric_type=MetricType.DNS_LATENCY,
                    raw_value=self.timeout_sec * 1000.0,
                    normalized_value=self.timeout_sec * 1000.0,
                    unit="ms",
                    status=ProbeStatus.TIMEOUT,
                    confidence=0.9,
                    error_message=str(exc),
                )
            ]
        except Exception as exc:
            return [
                ProbeResult(
                    timestamp=now,
                    source=MeasurementSource.DNS_QUERY,
                    target=domain,
                    metric_type=MetricType.DNS_LATENCY,
                    raw_value=0.0,
                    normalized_value=0.0,
                    unit="ms",
                    status=ProbeStatus.FAILED,
                    confidence=0.9,
                    error_message=str(exc),
                )
            ]

    def _handle_timeout(self) -> List[ProbeResult]:
        now = datetime.now(timezone.utc)
        return [
            ProbeResult(
                timestamp=now,
                source=MeasurementSource.DNS_QUERY,
                target=self.custom_resolver_ip or "system_dns",
                metric_type=MetricType.DNS_SUCCESS_RATE,
                raw_value=0.0,
                normalized_value=0.0,
                unit="ratio",
                status=ProbeStatus.TIMEOUT,
                confidence=0.9,
                error_message="DNS probe deadline exceeded",
            )
        ]
