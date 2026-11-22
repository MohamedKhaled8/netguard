"""Live empirical integration tests for NetGuard DNS subsystem on Windows."""

import pytest
import asyncio
from app.dns.benchmark import DNSBenchmark
from app.platform.windows.adapter import WindowsPlatformAdapter


@pytest.mark.asyncio
async def test_live_dns_benchmark_execution():
    """Verify live DNS benchmark sends genuine queries and records real latencies."""
    adapter = WindowsPlatformAdapter()
    iface = adapter.get_primary_interface()
    active_servers = adapter.get_interface_dns_servers(iface)

    bench = DNSBenchmark(rounds=2, timeout_sec=2.0)
    scores = await bench.rank_all(active_resolver_ips=active_servers)

    assert len(scores) >= 5, "Expected at least 5 benchmarked resolvers"
    for s in scores:
        assert s.name, "Resolver must have a valid name"
        assert s.ip, "Resolver must have a valid IP"
        # Since network is connected, at least major resolvers should succeed
        if s.ip in ("1.1.1.1", "8.8.8.8"):
            assert s.success_rate >= 0.50, f"Expected {s.name} ({s.ip}) to have positive success rate"
            assert s.median_latency_ms > 0.0, f"Expected positive latency for {s.name}"
            assert s.min_latency_ms <= s.median_latency_ms <= s.max_latency_ms

    # Verify active resolver is tagged
    if active_servers:
        active_found = any(s.is_active for s in scores)
        assert active_found, f"Active resolver {active_servers[0]} must be tagged as is_active=True"
