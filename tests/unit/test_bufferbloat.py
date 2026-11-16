"""Unit tests for NetGuard AI Stage 8 Bufferbloat Management."""

import pytest
from app.traffic.bufferbloat import BufferbloatEvaluator, BufferbloatGrade
from app.core.events.bus import EventBus
from app.platform.factory import get_platform_adapter


def test_bufferbloat_grading():
    assert BufferbloatEvaluator.calculate_grade(3.0) == BufferbloatGrade.A_PLUS
    assert BufferbloatEvaluator.calculate_grade(12.0) == BufferbloatGrade.A
    assert BufferbloatEvaluator.calculate_grade(25.0) == BufferbloatGrade.B
    assert BufferbloatEvaluator.calculate_grade(55.0) == BufferbloatGrade.C
    assert BufferbloatEvaluator.calculate_grade(110.0) == BufferbloatGrade.D
    assert BufferbloatEvaluator.calculate_grade(220.0) == BufferbloatGrade.F


@pytest.mark.asyncio
async def test_bufferbloat_evaluation_report():
    platform = get_platform_adapter()
    bus = EventBus()
    evaluator = BufferbloatEvaluator(platform=platform, event_bus=bus)

    # Idle = 15ms, Loaded = 125ms -> Delta = 110ms (Grade D)
    report = await evaluator.evaluate_latency_delta(idle_latency_ms=15.0, loaded_latency_ms=125.0)
    assert report.grade == BufferbloatGrade.D
    assert report.queue_delay_delta_ms == 110.0
    assert report.is_congested is True


@pytest.mark.asyncio
async def test_bufferbloat_live_test(monkeypatch):
    from unittest.mock import MagicMock
    platform = MagicMock()
    platform.ping.side_effect = [
        (True, 15.0), (True, 15.0), (True, 16.0), (True, 14.0),
        (True, 25.0), (True, 26.0), (True, 24.0), (True, 25.0),
    ]
    bus = EventBus()
    evaluator = BufferbloatEvaluator(platform=platform, event_bus=bus)

    report = await evaluator.run_live_test(target="1.1.1.1", load_duration_sec=0.2)
    assert report.grade in (BufferbloatGrade.A, BufferbloatGrade.A_PLUS, BufferbloatGrade.B)
    assert report.idle_latency_ms > 0
    assert report.loaded_latency_ms > 0
    assert report.queue_delay_delta_ms >= 0
