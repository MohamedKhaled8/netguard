"""Unit tests for NetGuard AI Stage 9 Quality of Experience (QoE) Engine."""

import pytest
from app.qoe.engine import QoEEngine
from app.core.events.bus import EventBus


def test_qoe_calculation_healthy():
    bus = EventBus()
    qoe = QoEEngine(event_bus=bus)

    # Ideal conditions: 12ms latency, 1.5ms jitter, 0% loss, 18ms DNS
    res = qoe.calculate_qoe(latency_ms=12.0, jitter_ms=1.5, packet_loss_ratio=0.0, dns_latency_ms=18.0)

    assert res.overall_score >= 95.0
    assert res.overall_rating == "Excellent"
    assert res.conferencing.score >= 95.0
    assert res.gaming.score >= 95.0
    assert len(res.bottlenecks) == 0


def test_qoe_calculation_degraded():
    bus = EventBus()
    qoe = QoEEngine(event_bus=bus)

    # Degraded jitter (65ms) and DNS latency (250ms)
    res = qoe.calculate_qoe(latency_ms=45.0, jitter_ms=65.0, packet_loss_ratio=0.03, dns_latency_ms=250.0)

    assert res.overall_score < 70.0
    assert res.conferencing.score < 60.0  # Conferencing heavily degraded by 65ms jitter
    assert len(res.bottlenecks) >= 1
