"""Decision tests: pick the real fastest DNS and switch only on a meaningful gain."""

from __future__ import annotations

import pytest

from app.dns.benchmark import ResolverScore
from app.dns.optimizer import decide_auto_switch, latency_for_ip, select_best_resolver


def _score(ip: str, name: str, ms: float, success: float = 1.0, composite: float = 90.0) -> ResolverScore:
    return ResolverScore(
        ip=ip,
        name=name,
        median_latency_ms=ms,
        mean_latency_ms=ms,
        min_latency_ms=max(1.0, ms - 2),
        max_latency_ms=ms + 2,
        stdev_latency_ms=1.0,
        success_rate=success,
        failure_rate=round(1.0 - success, 4),
        composite_score=composite,
    )


def test_select_best_keeps_current_if_it_is_fastest():
    ranked = [
        _score("8.8.4.4", "Google Secondary", 18.0),
        _score("1.1.1.1", "Cloudflare", 22.0),
        _score("9.9.9.9", "Quad9", 40.0),
    ]
    best = select_best_resolver(ranked)
    assert best is not None
    assert best.ip == "8.8.4.4"


def test_latency_for_ip_uses_same_benchmark_as_ranking():
    ranked = [
        _score("8.8.4.4", "Google Secondary", 18.0),
        _score("1.1.1.1", "Cloudflare", 22.0),
    ]
    assert latency_for_ip(ranked, "8.8.4.4") == 18.0
    assert latency_for_ip(ranked, "9.9.9.9") is None


def test_no_switch_when_current_is_already_fastest():
    ranked = [
        _score("8.8.4.4", "Google Secondary", 18.0),
        _score("1.1.1.1", "Cloudflare", 22.0),
    ]
    decision = decide_auto_switch(ranked, current_servers=["8.8.4.4"])
    assert decision.should_switch is False
    assert decision.reason_code == "already_optimal"
    assert decision.best is not None
    assert decision.best.ip == "8.8.4.4"


def test_no_switch_when_gain_is_inside_measurement_noise():
    ranked = [
        _score("1.1.1.1", "Cloudflare", 24.7),
        _score("8.8.8.8", "Google", 25.0),
    ]
    decision = decide_auto_switch(ranked, current_servers=["8.8.8.8"])
    assert decision.should_switch is False
    assert decision.reason_code == "already_optimal"
    assert decision.gain_ms == pytest.approx(0.3)


def test_no_switch_when_gain_is_below_10ms_or_25_percent():
    ranked = [
        _score("8.8.8.8", "Google Primary", 56.3),
        _score("8.8.4.4", "Google Secondary", 58.6),
    ]
    # Gain is 2.3 ms (< max(10 ms, 25% of 58.6 = 14.65 ms)) -> Must NOT switch
    decision = decide_auto_switch(ranked, current_servers=["8.8.4.4"])
    assert decision.should_switch is False
    assert decision.reason_code == "insufficient_gain"


def test_switch_when_gain_meets_10ms_and_25_percent():
    ranked = [
        _score("8.8.8.8", "Google Primary", 20.0),
        _score("8.8.4.4", "Google Secondary", 58.6),
    ]
    # Gain is 38.6 ms (>= max(10 ms, 14.65 ms)) -> Switches
    decision = decide_auto_switch(ranked, current_servers=["8.8.4.4"])
    assert decision.should_switch is True
    assert decision.best is not None
    assert decision.best.ip == "8.8.8.8"


def test_switch_when_gain_is_meaningful():
    ranked = [
        _score("1.1.1.1", "Cloudflare", 12.0),
        _score("8.8.8.8", "Google", 40.0),
    ]
    decision = decide_auto_switch(ranked, current_servers=["8.8.8.8"])
    assert decision.should_switch is True
    assert decision.reason_code == "apply"
    assert decision.best is not None
    assert decision.best.ip == "1.1.1.1"
    assert decision.gain_ms == 28.0


def test_skip_lossy_candidate_even_if_faster():
    ranked = [
        _score("1.1.1.1", "Cloudflare", 10.0, success=0.8, composite=70.0),
        _score("8.8.8.8", "Google", 40.0),
    ]
    decision = decide_auto_switch(ranked, current_servers=["8.8.8.8"])
    assert decision.should_switch is False
    # Fastest row is unsafe; the only remaining safe resolver is already active.
    assert decision.reason_code in ("already_optimal", "packet_loss")


def test_skip_when_not_elevated():
    ranked = [
        _score("1.1.1.1", "Cloudflare", 12.0),
        _score("8.8.8.8", "Google", 40.0),
    ]
    decision = decide_auto_switch(ranked, current_servers=["8.8.8.8"], elevated=False)
    assert decision.should_switch is False
    assert decision.reason_code == "not_elevated"
    assert "صلاحيات" in decision.message_ar or "مدير" in decision.message_ar
