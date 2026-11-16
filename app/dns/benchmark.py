"""DNS Resolver Benchmark and Reliability Scorer."""

from __future__ import annotations
import asyncio
import time
import statistics
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
import dns.resolver


class ResolverScore(BaseModel):
    """Benchmark evaluation result for a DNS resolver."""
    model_config = ConfigDict(frozen=True)

    ip: str
    name: str
    median_latency_ms: float = 0.0
    mean_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    stdev_latency_ms: float = 0.0
    success_rate: float = 1.0
    failure_rate: float = 0.0
    composite_score: float = 0.0
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DNSBenchmark:
    """Benchmarks and ranks candidate DNS resolvers across multiple domains."""

    DEFAULT_RESOLVERS = [
        ("1.1.1.1", "Cloudflare Primary"),
        ("1.0.0.1", "Cloudflare Secondary"),
        ("8.8.8.8", "Google Primary"),
        ("8.8.4.4", "Google Secondary"),
        ("9.9.9.9", "Quad9 Primary"),
        ("208.67.222.222", "OpenDNS Primary"),
    ]

    DEFAULT_DOMAINS = [
        "google.com",
        "cloudflare.com",
        "wikipedia.org",
        "github.com",
    ]

    def __init__(
        self,
        resolvers: Optional[List[tuple[str, str]]] = None,
        domains: Optional[List[str]] = None,
        timeout_sec: float = 2.0,
        rounds: int = 3,
    ) -> None:
        self.resolvers = resolvers or self.DEFAULT_RESOLVERS
        self.domains = domains or self.DEFAULT_DOMAINS
        self.timeout_sec = timeout_sec
        self.rounds = max(1, rounds)

    async def benchmark_resolver(self, ip: str, name: str) -> ResolverScore:
        """Run multiple query rounds against a specific resolver directly and calculate its composite score."""
        loop = asyncio.get_running_loop()

        def _sync_bench():
            res = dns.resolver.Resolver(configure=False)
            res.nameservers = [ip]
            res.lifetime = self.timeout_sec
            res.timeout = self.timeout_sec

            latencies = []
            failures = 0

            for _ in range(self.rounds):
                for domain in self.domains:
                    try:
                        t0 = time.perf_counter()
                        res.resolve(domain, "A")
                        latencies.append((time.perf_counter() - t0) * 1000.0)
                    except Exception:
                        failures += 1

            return latencies, failures

        latencies, failures = await loop.run_in_executor(None, _sync_bench)
        total_queries = len(self.domains) * self.rounds
        failure_rate = (failures / total_queries) if total_queries > 0 else 1.0
        success_rate = (len(latencies) / total_queries) if total_queries > 0 else 0.0

        if latencies:
            median_lat = float(statistics.median(latencies))
            mean_lat = float(statistics.mean(latencies))
            min_lat = float(min(latencies))
            max_lat = float(max(latencies))
            stdev_lat = float(statistics.stdev(latencies)) if len(latencies) >= 2 else 0.0
        else:
            mean_lat = self.timeout_sec * 1000.0
            median_lat = mean_lat
            min_lat = mean_lat
            max_lat = mean_lat
            stdev_lat = 0.0

        # Composite score formula: 100 - (0.35 * MedianLatency) - (250 * FailureRate) - (0.15 * Stdev)
        raw_score = 100.0 - (0.35 * median_lat) - (250.0 * failure_rate) - (0.15 * stdev_lat)
        score = max(0.0, min(100.0, raw_score))

        return ResolverScore(
            ip=ip,
            name=name,
            median_latency_ms=median_lat,
            mean_latency_ms=mean_lat,
            min_latency_ms=min_lat,
            max_latency_ms=max_lat,
            stdev_latency_ms=stdev_lat,
            success_rate=success_rate,
            failure_rate=failure_rate,
            composite_score=score,
        )

    async def rank_all(self) -> List[ResolverScore]:
        """Benchmark all configured resolvers concurrently and return sorted by score descending."""
        tasks = [self.benchmark_resolver(ip, name) for ip, name in self.resolvers]
        scores = await asyncio.gather(*tasks)
        sorted_scores = sorted(scores, key=lambda s: s.composite_score, reverse=True)
        return sorted_scores

    # Compatibility alias
    benchmark_all = rank_all
