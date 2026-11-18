"""Unit tests for Network Health Evaluator (Item C0)."""

import pytest
from app.monitoring.health_evaluator import (
    HealthEvaluator,
    HealthSample,
    HealthStatus,
    NetworkIssueType,
    assess_network_health,
)


def test_single_probe_drop_ignored_by_hysteresis():
    """Single degraded spike must not cause a warning status (Item C0)."""
    evaluator = HealthEvaluator(degraded_threshold_samples=2, recovery_threshold_samples=3)

    # Initial clean sample
    v1 = evaluator.evaluate(HealthSample(gateway_latency_ms=2.0, internet_latency_ms=25.0, jitter_ms=3.0))
    assert v1.status == HealthStatus.GOOD

    # Single spike (loss 5.0%)
    v2 = evaluator.evaluate(HealthSample(gateway_latency_ms=2.0, internet_loss_pct=5.0, jitter_ms=35.0))
    assert v2.status == HealthStatus.GOOD
    assert "رصد تذبذب عابر" in v2.headline

    # Next sample returns to clean
    v3 = evaluator.evaluate(HealthSample(gateway_latency_ms=2.0, internet_latency_ms=25.0, jitter_ms=3.0))
    assert v3.status == HealthStatus.GOOD


def test_sustained_loss_transitions_to_warning():
    """Sustained degraded conditions must transition to warning on 2nd sample (Item C0)."""
    evaluator = HealthEvaluator(degraded_threshold_samples=2, recovery_threshold_samples=3)

    # Clean sample 1
    evaluator.evaluate(HealthSample(gateway_latency_ms=2.0, internet_latency_ms=25.0, jitter_ms=3.0))

    # Degraded sample 1 (jitter 45ms)
    v1 = evaluator.evaluate(HealthSample(gateway_latency_ms=2.0, jitter_ms=45.0))
    assert v1.status == HealthStatus.GOOD

    # Degraded sample 2 (sustained jitter) -> status transitions to WARNING!
    v2 = evaluator.evaluate(HealthSample(gateway_latency_ms=2.0, jitter_ms=48.0))
    assert v2.status == HealthStatus.WARNING
    assert v2.primary_issue == NetworkIssueType.HIGH_JITTER_MEETING_RISK


def test_recovery_requires_three_consecutive_clean_samples():
    """Recovery from warning back to good requires 3 consecutive clean samples (Item C0)."""
    evaluator = HealthEvaluator(degraded_threshold_samples=2, recovery_threshold_samples=3)

    # Trigger WARNING
    evaluator.evaluate(HealthSample(gateway_latency_ms=2.0, jitter_ms=40.0))
    evaluator.evaluate(HealthSample(gateway_latency_ms=2.0, jitter_ms=40.0))
    assert evaluator.current_status == HealthStatus.WARNING

    # Clean sample 1 -> still warning (recovering 1/3)
    r1 = evaluator.evaluate(HealthSample(gateway_latency_ms=2.0, jitter_ms=4.0))
    assert r1.status == HealthStatus.WARNING
    assert "1/3" in r1.headline

    # Clean sample 2 -> still warning (recovering 2/3)
    r2 = evaluator.evaluate(HealthSample(gateway_latency_ms=2.0, jitter_ms=4.0))
    assert r2.status == HealthStatus.WARNING
    assert "2/3" in r2.headline

    # Clean sample 3 -> RECOVERED to GOOD!
    r3 = evaluator.evaluate(HealthSample(gateway_latency_ms=2.0, jitter_ms=4.0))
    assert r3.status == HealthStatus.GOOD
    assert r3.headline == "الاتصال سليم ومستقر"


def test_multi_probe_internet_outage_agreement():
    """Internet outage requires gateway reachable AND >=2 failed internet targets (Item C0)."""
    evaluator = HealthEvaluator(degraded_threshold_samples=1, recovery_threshold_samples=1)

    # Single failed target does not trigger internet outage
    v_single = evaluator.evaluate(HealthSample(
        gateway_latency_ms=1.5,
        internet_targets_failed=1,
        internet_targets_total=2,
    ))
    assert v_single.primary_issue != NetworkIssueType.INTERNET_OUTAGE

    # Two failed targets with reachable gateway triggers outage
    v_outage = evaluator.evaluate(HealthSample(
        gateway_latency_ms=1.5,
        internet_targets_failed=2,
        internet_targets_total=2,
    ))
    assert v_outage.status == HealthStatus.CRITICAL
    assert v_outage.primary_issue == NetworkIssueType.INTERNET_OUTAGE
