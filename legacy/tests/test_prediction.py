"""Unit tests for NetGuard AI Stage 4 Predictive Failure Detection."""

import pytest
from app.core.events.bus import EventBus
from app.core.models.metrics import MetricType, Measurement, MeasurementSource, ProbeStatus
from app.prediction.baselines import BaselineManager
from app.prediction.anomaly_detection import AnomalyDetector, TrendAnalysis
from app.prediction.engine import PredictionEngine
from datetime import datetime, timezone


def make_meas(m_type: MetricType, val: float) -> Measurement:
    return Measurement(
        timestamp=datetime.now(timezone.utc),
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="target",
        metric_type=m_type,
        raw_value=val,
        normalized_value=val,
        unit="ms",
        status=ProbeStatus.SUCCESS,
        confidence=1.0,
    )


def test_baseline_manager():
    mgr = BaselineManager(min_samples=10)
    # Generate 20 stable samples around 15.0ms
    stable_samples = [15.0 + (i % 3) for i in range(20)]
    baseline = mgr.update_baseline(MetricType.GATEWAY_LATENCY, stable_samples)

    assert baseline is not None
    assert 15.0 <= baseline.mean <= 17.0
    assert baseline.upper_threshold_zscore_3 > baseline.mean


def test_anomaly_detection_zscore():
    mgr = BaselineManager(min_samples=10)
    stable_samples = [10.0, 10.5, 9.8, 10.2, 10.1, 9.9, 10.3, 10.0, 10.2, 9.7, 10.1, 10.0]
    mgr.update_baseline(MetricType.GATEWAY_LATENCY, stable_samples)

    detector = AnomalyDetector(mgr)

    # Normal sample
    is_ano, score, _ = detector.evaluate_anomaly(MetricType.GATEWAY_LATENCY, stable_samples + [10.2])
    assert is_ano is False

    # Outlier spike (85ms vs baseline 10ms)
    is_ano, score, reason = detector.evaluate_anomaly(MetricType.GATEWAY_LATENCY, stable_samples + [85.0])
    assert is_ano is True
    assert score >= 0.70
    assert "Statistical anomaly" in reason


def test_trend_slope_detection():
    # Progressively rising values: 10, 14, 18, 22, 26, 30...
    rising = [10.0 + (i * 4.0) for i in range(10)]
    slope = TrendAnalysis.calculate_slope(rising)
    assert slope == pytest.approx(4.0, rel=1e-2)


@pytest.mark.asyncio
async def test_prediction_engine_warning():
    bus = EventBus()
    engine = PredictionEngine(event_bus=bus, min_samples_for_baseline=10)

    # 15 baseline samples followed by a massive rising trend
    samples = [make_meas(MetricType.GATEWAY_LATENCY, 12.0) for _ in range(12)]
    samples.extend([
        make_meas(MetricType.GATEWAY_LATENCY, 25.0),
        make_meas(MetricType.GATEWAY_LATENCY, 45.0),
        make_meas(MetricType.GATEWAY_LATENCY, 75.0),
    ])

    warnings = await engine.evaluate_streams({MetricType.GATEWAY_LATENCY: samples})
    assert len(warnings) >= 1
    assert warnings[0].predicted_failure_type == "gateway_latency_spike"
    assert warnings[0].horizon_sec > 0
