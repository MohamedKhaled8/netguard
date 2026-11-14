"""Unit tests for NetGuard AI Stage 5 Intelligent DNS Engine."""

import pytest
from app.dns.benchmark import DNSBenchmark, ResolverScore
from app.dns.optimizer import DNSOptimizer
from app.core.events.bus import EventBus
from app.platform.interfaces import IPlatformAdapter


class MockDNSPlatform(IPlatformAdapter):
    def get_default_gateway(self): return "192.168.1.1"
    def get_primary_interface(self): return "Wi-Fi"
    def ping(self, t, s=1.5): return True, 10.0
    def tcp_connect(self, t, p=80, s=2.0): return True, 10.0
    def flush_dns_cache(self): return True, "Flushed"
    def get_interface_dns_servers(self, name): return ["192.168.1.1"]
    def set_interface_dns_servers(self, name, s): return True, "OK"
    def renew_ip_lease(self, name): return True, "OK"
    def get_wifi_metrics(self, name=None): return {}


def test_resolver_score_calculation():
    score = ResolverScore(
        ip="1.1.1.1",
        name="Cloudflare",
        mean_latency_ms=14.2,
        min_latency_ms=12.0,
        max_latency_ms=18.0,
        stdev_latency_ms=1.5,
        failure_rate=0.0,
        composite_score=94.5,
    )
    assert score.composite_score > 90.0
    assert score.ip == "1.1.1.1"


@pytest.mark.asyncio
async def test_dns_benchmark_ranking(monkeypatch):
    # Mock benchmark_resolver to avoid external network dependencies in unit test
    bench = DNSBenchmark()

    async def mock_bench(ip, name):
        latency_map = {
            "1.1.1.1": 12.0,
            "8.8.8.8": 22.0,
            "9.9.9.9": 45.0,
            "208.67.222.222": 65.0,
        }
        lat = latency_map.get(ip, 30.0)
        return ResolverScore(
            ip=ip,
            name=name,
            mean_latency_ms=lat,
            min_latency_ms=lat - 2,
            max_latency_ms=lat + 2,
            stdev_latency_ms=1.0,
            failure_rate=0.0,
            composite_score=100.0 - (0.35 * lat),
        )

    monkeypatch.setattr(bench, "benchmark_resolver", mock_bench)

    ranked = await bench.rank_all()
    assert len(ranked) >= 4
    # 1.1.1.1 should be ranked #1 because it has the lowest latency (12ms)
    assert ranked[0].ip == "1.1.1.1"
    assert ranked[0].composite_score > ranked[-1].composite_score


@pytest.mark.asyncio
async def test_dns_optimizer_selection(monkeypatch):
    platform = MockDNSPlatform()
    bus = EventBus()
    optimizer = DNSOptimizer(platform_adapter=platform, event_bus=bus)

    async def mock_rank_all():
        return [
            ResolverScore(ip="1.1.1.1", name="Cloudflare", mean_latency_ms=10.0, min_latency_ms=8.0, max_latency_ms=12.0, stdev_latency_ms=1.0, failure_rate=0.0, composite_score=96.0),
            ResolverScore(ip="8.8.8.8", name="Google", mean_latency_ms=20.0, min_latency_ms=18.0, max_latency_ms=22.0, stdev_latency_ms=1.0, failure_rate=0.0, composite_score=92.0),
        ]

    monkeypatch.setattr(optimizer.benchmark, "rank_all", mock_rank_all)

    best = await optimizer.auto_optimize_dns()
    assert best is not None
    assert best.ip == "1.1.1.1"
