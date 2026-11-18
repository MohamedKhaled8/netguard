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
    ]

    def __init__(
        self,
        resolvers: Optional[List[tuple[str, str]]] = None,
        domains: Optional[List[str]] = None,
        timeout_sec: float = 2.0,
        rounds: int = 5,
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
        """Benchmark all configured resolvers concurrently and return sorted by median latency ascending."""
        tasks = [self.benchmark_resolver(ip, name) for ip, name in self.resolvers]
        scores = await asyncio.gather(*tasks)

        # Gate: success rate >= 80% (0.80)
        viable = [s for s in scores if s.success_rate >= 0.80]
        unviable = [s for s in scores if s.success_rate < 0.80]

        # Sort strictly ascending by median latency
        sorted_viable = sorted(viable, key=lambda s: s.median_latency_ms)
        sorted_unviable = sorted(unviable, key=lambda s: (s.failure_rate, s.median_latency_ms))
        sorted_scores = sorted_viable + sorted_unviable

        # Write benchmark evidence report to docs/dns_benchmark.md
        self._write_benchmark_report(sorted_scores)
        return sorted_scores

    def _write_benchmark_report(self, scores: List[ResolverScore]) -> None:
        try:
            doc_path = "docs/dns_benchmark.md"
            lines = [
                "# DNS Resolver Benchmark Report (Item B4)",
                f"Generated at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
                f"Rounds: {self.rounds} | Domains: {', '.join(self.domains)}",
                "",
                "| Rank | Resolver Name | IP Address | Median Latency | Mean Latency | Success Rate | Status |",
                "|---|---|---|---|---|---|---|",
            ]
            for idx, s in enumerate(scores):
                status = "Passed (Viable)" if s.success_rate >= 0.80 else "Rejected (<80% success)"
                lines.append(
                    f"| {idx + 1:02d} | {s.name} | `{s.ip}` | {s.median_latency_ms:.1f} ms | {s.mean_latency_ms:.1f} ms | {s.success_rate * 100:.0f}% | {status} |"
                )
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception:
            pass

    # Compatibility alias
    benchmark_all = rank_all
