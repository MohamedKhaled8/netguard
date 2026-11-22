import pytest
from app.dns.detector import DnsDetailedMeasurement
from app.dns.benchmark import generate_dns_analysis, ResolverScore


def test_generate_dns_analysis_active_healthy():
    score = ResolverScore(
        name="Cloudflare DNS Secondary",
        ip="1.0.0.1",
        mean_latency_ms=45.0,
        median_latency_ms=44.0,
        min_latency_ms=38.0,
        max_latency_ms=50.0,
        jitter_ms=6.0,
        success_rate=1.0,
        is_active=True,
        is_ip_reachable=True,
    )
    analysis = generate_dns_analysis(
        active_ip="1.0.0.1",
        active_name="Cloudflare",
        active_score=score,
        all_scores=[score],
    )
    assert analysis["health_tier"] == "healthy"
    assert "يعمل بكفاءة وسرعة ممتازة" in analysis["verdict"]
    assert "الخادم الحالي مستقر" in analysis["recommendation_text"]


def test_generate_dns_analysis_active_slow():
    active_score = ResolverScore(
        name="Local ISP DNS",
        ip="192.168.1.1",
        mean_latency_ms=120.0,
        median_latency_ms=115.0,
        min_latency_ms=90.0,
        max_latency_ms=140.0,
        jitter_ms=25.0,
        success_rate=1.0,
        is_active=True,
        is_ip_reachable=True,
    )
    fast_score = ResolverScore(
        name="Cloudflare DNS",
        ip="1.1.1.1",
        mean_latency_ms=25.0,
        median_latency_ms=24.0,
        min_latency_ms=20.0,
        max_latency_ms=28.0,
        jitter_ms=4.0,
        success_rate=1.0,
        is_active=False,
        is_ip_reachable=True,
    )
    analysis = generate_dns_analysis(
        active_ip="192.168.1.1",
        active_name="Telecom Egypt DNS",
        active_score=active_score,
        all_scores=[fast_score, active_score],
    )
    assert analysis["health_tier"] == "slow"
    assert "يعاني من بطء" in analysis["verdict"]
    assert "الخادم البديل" in analysis["recommendation_text"]
    assert "Cloudflare DNS" in analysis["recommendation_text"]


def test_generate_dns_analysis_active_unresponsive():
    unresponsive_score = ResolverScore(
        name="Failing DNS",
        ip="10.0.0.1",
        mean_latency_ms=2000.0,
        median_latency_ms=2000.0,
        min_latency_ms=2000.0,
        max_latency_ms=2000.0,
        jitter_ms=0.0,
        success_rate=0.0,
        is_active=True,
        is_ip_reachable=False,
    )
    fast_score = ResolverScore(
        name="Cloudflare DNS",
        ip="1.1.1.1",
        mean_latency_ms=25.0,
        median_latency_ms=24.0,
        min_latency_ms=20.0,
        max_latency_ms=28.0,
        jitter_ms=4.0,
        success_rate=1.0,
        is_active=False,
        is_ip_reachable=True,
    )
    analysis = generate_dns_analysis(
        active_ip="10.0.0.1",
        active_name="Offline Resolver",
        active_score=unresponsive_score,
        all_scores=[fast_score, unresponsive_score],
    )
    assert analysis["health_tier"] == "unresponsive"
    assert "لا يستجيب" in analysis["verdict"]
    assert "يُوصى بالتبديل فوراً" in analysis["recommendation_text"]
