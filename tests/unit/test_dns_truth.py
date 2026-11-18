"""Comprehensive unit & policy tests for DNS Truth (Stage B: B1-B8)."""

import pytest
import os
import json
from unittest.mock import MagicMock, AsyncMock, patch

from app.dns.state import DnsStateManager, DnsStateData
from app.dns.detector import load_providers_catalogue, identify_provider, check_transparent_proxy
from app.dns.benchmark import DNSBenchmark, ResolverScore
from app.dns.optimizer import DNSOptimizer
from app.core.events.bus import EventBus


def test_b1_single_source_of_truth():
    mgr = DnsStateManager.get_instance()
    assert mgr is not None

    updates = []
    mgr.state_changed.connect(lambda s: updates.append(s))

    mgr.update(active_servers=["1.1.1.1", "1.0.0.1"], detected_provider="Cloudflare", is_healthy=True)
    assert len(updates) >= 1
    current = mgr.current
    assert current.active_servers == ["1.1.1.1", "1.0.0.1"]
    assert current.detected_provider == "Cloudflare"
    assert current.is_healthy is True


def test_b2_provider_identification():
    cat = load_providers_catalogue()
    assert "global_anycast" in cat
    assert "egypt_isps" in cat

    assert identify_provider("1.1.1.1", cat) == "Cloudflare"
    assert identify_provider("8.8.8.8", cat) == "Google Public DNS"
    assert identify_provider("163.121.128.134", cat) == "Telecom Egypt (WE)"
    assert identify_provider("192.168.1.1", cat) == "الراوتر المنزلي (Gateway DNS)"
    assert identify_provider("10.0.0.1", cat) == "الراوتر المنزلي (Gateway DNS)"


def test_b3_catalogue_structure():
    cat = load_providers_catalogue()
    for group in ["global_anycast", "egypt_isps"]:
        for p in cat.get(group, []):
            assert "name" in p
            assert "primary_ip" in p
            assert "secondary_ip" in p


@pytest.mark.asyncio
async def test_b4_benchmark_sorting_and_gating():
    bench = DNSBenchmark(rounds=5)
    assert bench.rounds == 5

    # Explicit metrics on ResolverScore
    scores = [
        ResolverScore(ip="8.8.8.8", name="Google", median_latency_ms=35.0, mean_latency_ms=35.0, success_rate=1.0, failure_rate=0.0, composite_score=75.0),
        ResolverScore(ip="1.1.1.1", name="Cloudflare", median_latency_ms=22.0, mean_latency_ms=22.0, success_rate=1.0, failure_rate=0.0, composite_score=90.0),
        ResolverScore(ip="9.9.9.9", name="Flaky", median_latency_ms=15.0, mean_latency_ms=15.0, success_rate=0.60, failure_rate=0.40, composite_score=30.0),
    ]

    with patch.object(bench, "benchmark_resolver", side_effect=scores):
        with patch("asyncio.gather", new=AsyncMock(return_value=scores)):
            ranked = await bench.rank_all()
            assert ranked[0].name == "Cloudflare"
            assert ranked[1].name == "Google"
            assert ranked[2].name == "Flaky"
            assert os.path.exists("docs/dns_benchmark.md")


@pytest.mark.asyncio
async def test_b7_safe_auto_switch_policy():
    platform = MagicMock()
    platform.get_primary_interface.return_value = "Wi-Fi"
    platform.get_interface_dns_servers.return_value = ["192.168.1.1"]
    platform.set_interface_dns_servers.return_value = (True, "OK")

    event_bus = EventBus()
    session_tracker = MagicMock()
    session_tracker.has_active_meeting.return_value = False

    optimizer = DNSOptimizer(
        platform_adapter=platform,
        event_bus=event_bus,
        cooldown_sec=900.0,
        session_tracker=session_tracker,
    )

    # 1. Test meeting protection
    session_tracker.has_active_meeting.return_value = True
    res = await optimizer.auto_optimize_dns()
    assert res is None  # Blocked by meeting protection

    session_tracker.has_active_meeting.return_value = False

    # 2. Test hysteresis check (< 15 ms improvement should not switch)
    candidate = ResolverScore(ip="1.1.1.1", name="Cloudflare", median_latency_ms=25.0, mean_latency_ms=25.0, success_rate=1.0, failure_rate=0.0, composite_score=85.0)
    with patch.object(optimizer, "evaluate_and_rank", new=AsyncMock(return_value=[candidate])):
        with patch("app.dns.detector.measure_dns_latency", return_value=30.0):  # Difference is 5 ms (< 15 ms)
            res = await optimizer.auto_optimize_dns()
            assert res is None  # Skipped due to hysteresis

    # 3. Test candidate with packet loss rejected
    lossy_candidate = ResolverScore(ip="1.1.1.1", name="Cloudflare", median_latency_ms=10.0, mean_latency_ms=10.0, success_rate=0.80, failure_rate=0.20, composite_score=80.0)
    with patch.object(optimizer, "evaluate_and_rank", new=AsyncMock(return_value=[lossy_candidate])):
        with patch("app.dns.detector.measure_dns_latency", return_value=50.0):
            res = await optimizer.auto_optimize_dns()
            assert res is None  # Skipped due to packet loss > 0%

    # 4. Test post-switch verification failure triggers immediate rollback
    good_candidate = ResolverScore(ip="1.1.1.1", name="Cloudflare", median_latency_ms=10.0, mean_latency_ms=10.0, success_rate=1.0, failure_rate=0.0, composite_score=95.0)
    with patch.object(optimizer, "evaluate_and_rank", new=AsyncMock(return_value=[good_candidate])):
        # Current latency 60ms (gain > 15ms), but post-switch query fails (None)
        with patch("app.dns.detector.measure_dns_latency", side_effect=[60.0, None]):
            res = await optimizer.auto_optimize_dns()
            assert res is None
            # Verified that rollback was called
            assert platform.set_interface_dns_servers.call_count >= 2
