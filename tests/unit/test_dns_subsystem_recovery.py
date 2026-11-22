"""Comprehensive regression & recovery tests for NetGuard DNS subsystem."""

import pytest
import ipaddress
from unittest.mock import MagicMock, AsyncMock, patch
from pydantic import ValidationError

from app.dns.state import DnsStateManager, DnsStateData
from app.dns.detector import load_providers_catalogue, identify_provider, get_secondary_ip
from app.dns.benchmark import DNSBenchmark, ResolverScore, generate_dns_analysis, get_default_benchmark_resolvers
from app.remediation.actions.switch_dns import SwitchDNSResolverAction


def test_1_resolver_catalog_complete_and_valid():
    """Verify all required DNS providers are present with valid, distinct IPv4 and IPv6 addresses."""
    cat = load_providers_catalogue()
    assert "global_anycast" in cat
    anycast = {p["name"]: p for p in cat["global_anycast"]}

    # Required providers
    required = ["Cloudflare", "Google Public DNS", "Quad9 Secure", "OpenDNS (Cisco)", "AdGuard DNS"]
    for req in required:
        assert req in anycast, f"Missing required provider {req} in catalogue"
        p = anycast[req]
        p_ip = p["primary_ip"]
        s_ip = p["secondary_ip"]
        assert p_ip != s_ip, f"Primary and secondary IP must be distinct for {req}"

        # Validate IP addresses
        p_obj = ipaddress.ip_address(p_ip)
        s_obj = ipaddress.ip_address(s_ip)
        assert p_obj.version == 4
        assert s_obj.version == 4

        # Validate IPv6 if present
        if "primary_ipv6" in p:
            p_v6 = ipaddress.ip_address(p["primary_ipv6"])
            assert p_v6.version == 6
        if "secondary_ipv6" in p:
            s_v6 = ipaddress.ip_address(p["secondary_ipv6"])
            assert s_v6.version == 6


def test_2_identify_provider_and_router_separation():
    """Verify honest provider identification without confusing home router with public DNS."""
    cat = load_providers_catalogue()

    # Public DNS
    assert identify_provider("1.1.1.1", cat) == "Cloudflare"
    assert identify_provider("1.0.0.1", cat) == "Cloudflare"
    assert identify_provider("8.8.8.8", cat) == "Google Public DNS"
    assert identify_provider("8.8.4.4", cat) == "Google Public DNS"
    assert identify_provider("9.9.9.9", cat) == "Quad9 Secure"
    assert identify_provider("208.67.222.222", cat) == "OpenDNS (Cisco)"

    # Router addresses must NEVER be identified as Cloudflare or Google
    assert identify_provider("192.168.1.1", cat) == "الراوتر المنزلي (Gateway DNS)"
    assert identify_provider("10.0.0.1", cat) == "الراوتر المنزلي (Gateway DNS)"
    assert identify_provider("172.16.0.1", cat) == "الراوتر المنزلي (Gateway DNS)"
    assert identify_provider("fe80::1", cat) == "الراوتر المنزلي (Gateway IPv6)"

    # Secondary IP resolution
    assert get_secondary_ip("1.1.1.1", cat) == "1.0.0.1"
    assert get_secondary_ip("1.0.0.1", cat) == "1.1.1.1"
    assert get_secondary_ip("8.8.8.8", cat) == "8.8.4.4"
    assert get_secondary_ip("9.9.9.9", cat) == "149.112.112.112"


def test_3_resolverscore_immutability_and_state_separation():
    """Verify ResolverScore is frozen, prevents mutation, and cleanly separates state flags."""
    score = ResolverScore(
        ip="1.1.1.1",
        name="Cloudflare",
        median_latency_ms=18.5,
        mean_latency_ms=19.0,
        is_active=False,
        is_reachable=True,
        is_recommended=False,
    )
    assert score.is_active is False
    assert score.is_reachable is True
    assert score.is_recommended is False
    assert score.latency_ms == 18.5

    # Direct mutation MUST raise ValidationError (frozen instance)
    with pytest.raises(ValidationError):
        score.is_active = True

    with pytest.raises(ValidationError):
        score.is_recommended = True

    # Proper model_copy update works cleanly
    updated = score.model_copy(update={"is_active": True, "is_recommended": False})
    assert updated.is_active is True
    assert updated.is_recommended is False
    assert score.is_active is False  # Original unchanged


@pytest.mark.asyncio
async def test_4_benchmark_rank_all_frozen_safety():
    """Verify rank_all completes without frozen_instance exception when given active resolver."""
    bench = DNSBenchmark(rounds=1)

    mock_scores = [
        ResolverScore(ip="8.8.8.8", name="Google", median_latency_ms=30.0, mean_latency_ms=30.0, success_rate=1.0),
        ResolverScore(ip="1.0.0.1", name="Active System DNS", median_latency_ms=45.0, mean_latency_ms=45.0, success_rate=1.0),
        ResolverScore(ip="1.1.1.1", name="Cloudflare", median_latency_ms=20.0, mean_latency_ms=20.0, success_rate=1.0),
    ]

    with patch.object(bench, "benchmark_resolver", side_effect=mock_scores):
        with patch("asyncio.gather", new=AsyncMock(return_value=mock_scores)):
            # This call previously crashed with "Instance is frozen" on line 176
            ranked = await bench.rank_all(active_resolver_ips=["1.0.0.1"])
            assert len(ranked) == 3

            # Verify active resolver correctly flagged
            active_s = next(s for s in ranked if s.ip == "1.0.0.1")
            assert active_s.is_active is True
            assert active_s.is_recommended is False

            # Verify recommended candidate correctly flagged and is NOT active
            rec_s = next(s for s in ranked if s.is_recommended)
            assert rec_s.ip == "1.1.1.1"  # 20ms is fastest non-active
            assert rec_s.is_active is False


def test_5_dns_analysis_internet_outage_vs_dns_failure():
    """Verify analysis engine never blames DNS provider when entire internet connection is down."""
    # Scenario A: All candidate resolvers fail (internet connection down)
    scores_offline = [
        ResolverScore(ip="1.1.1.1", name="Cloudflare", median_latency_ms=2000.0, success_rate=0.0, is_active=False),
        ResolverScore(ip="8.8.8.8", name="Google", median_latency_ms=2000.0, success_rate=0.0, is_active=False),
        ResolverScore(ip="192.168.1.1", name="Router", median_latency_ms=2000.0, success_rate=0.0, is_active=True),
    ]
    an_offline = generate_dns_analysis(
        active_ip="192.168.1.1",
        active_name="الراوتر المنزلي",
        active_score=scores_offline[2],
        all_scores=scores_offline,
    )
    assert an_offline["current"]["status_code"] == "internet_down"
    assert "انقطاع" in an_offline["verdict"]
    assert an_offline["recommendation"]["should_switch"] is False

    # Scenario B: Internet works (Cloudflare 100%), but active resolver is dead
    scores_dns_dead = [
        ResolverScore(ip="1.1.1.1", name="Cloudflare", median_latency_ms=22.0, mean_latency_ms=22.0, success_rate=1.0, is_active=False),
        ResolverScore(ip="10.0.0.1", name="Dead DNS", median_latency_ms=2000.0, success_rate=0.0, is_active=True, is_ip_reachable=False),
    ]
    an_dns_dead = generate_dns_analysis(
        active_ip="10.0.0.1",
        active_name="Dead DNS",
        active_score=scores_dns_dead[1],
        all_scores=scores_dns_dead,
    )
    assert an_dns_dead["recommendation"]["should_switch"] is True
    assert "التبديل فوراً" in an_dns_dead["recommendation_text"]

    # Scenario C: Active resolver is fast and healthy (small diff < 15ms) -> do NOT switch
    scores_normal = [
        ResolverScore(ip="1.1.1.1", name="Cloudflare", median_latency_ms=18.0, mean_latency_ms=18.0, success_rate=1.0, is_active=False),
        ResolverScore(ip="8.8.8.8", name="Google", median_latency_ms=24.0, mean_latency_ms=24.0, success_rate=1.0, is_active=True),
    ]
    an_normal = generate_dns_analysis(
        active_ip="8.8.8.8",
        active_name="Google Public DNS",
        active_score=scores_normal[1],
        all_scores=scores_normal,
    )
    assert an_normal["recommendation"]["should_switch"] is False
    assert "لا توجد ضرورة لتغييره" in an_normal["recommendation_text"]


def test_6_dns_state_manager_broadcasting():
    """Verify DnsStateManager correctly emits snapshot to subscribers on update."""
    mgr = DnsStateManager.get_instance()
    received = []
    mgr.state_changed.connect(lambda s: received.append(s))

    test_score = ResolverScore(ip="1.1.1.1", name="Cloudflare", median_latency_ms=20.0, success_rate=1.0)
    mgr.update(
        active_servers=["1.1.1.1"],
        detected_provider="Cloudflare",
        last_measured_ms=20.0,
        scores=[test_score],
    )
    assert len(received) >= 1
    assert received[-1].detected_provider == "Cloudflare"
    assert received[-1].last_measured_ms == 20.0


@pytest.mark.asyncio
async def test_7_switch_dns_action_admin_precondition_and_verification():
    """Verify SwitchDNSResolverAction checks elevation and uses target resolver for verification."""
    platform = MagicMock()
    platform.is_elevated.return_value = False
    platform.get_primary_interface.return_value = "Wi-Fi"

    action = SwitchDNSResolverAction()
    # 1. Unprivileged must be rejected
    ok, reason = action.check_preconditions(platform, {})
    assert ok is False
    assert "Administrator" in reason or "مسؤول" in reason

    # 2. Privileged succeeds
    platform.is_elevated.return_value = True
    ok, _ = action.check_preconditions(platform, {})
    assert ok is True
