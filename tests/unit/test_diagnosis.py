"""Unit tests for NetGuard AI Stage 2 Root Cause Diagnosis Engine."""

import pytest
from datetime import datetime, timezone
from app.core.config.models import DiagnosisThresholds
from app.core.events.bus import EventBus
from app.core.models.metrics import (
    Measurement,
    MetricType,
    ProbeStatus,
    MeasurementSource,
    ProbableCause,
    DiagnosisSeverity,
)
from app.storage.database import DatabaseManager
from app.storage.repositories.incident_repo import IncidentRepository
from app.diagnosis.engine import DiagnosisEngine


def make_measurement(metric: MetricType, val: float, target: str = "target", status: ProbeStatus = ProbeStatus.SUCCESS) -> Measurement:
    return Measurement(
        timestamp=datetime.now(timezone.utc),
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface=target,
        metric_type=metric,
        raw_value=val,
        normalized_value=val,
        unit="unit",
        status=status,
        confidence=1.0,
    )


@pytest.fixture
def diagnosis_setup(tmp_path):
    db_file = tmp_path / "diag_test.db"
    db_manager = DatabaseManager(db_path=db_file, enable_wal=False)
    repo = IncidentRepository(db_manager)
    bus = EventBus()
    thresholds = DiagnosisThresholds(
        gateway_latency_critical_ms=80.0,
        gateway_packet_loss_critical=0.40,
        external_latency_critical_ms=200.0,
        external_packet_loss_critical=0.30,
        dns_latency_critical_ms=350.0,
    )
    engine = DiagnosisEngine(thresholds=thresholds, event_bus=bus, incident_repo=repo)
    return engine, bus, repo


@pytest.mark.asyncio
async def test_diagnosis_gateway_unreachable(diagnosis_setup):
    engine, bus, repo = diagnosis_setup
    windows = {
        MetricType.GATEWAY_REACHABILITY: [make_measurement(MetricType.GATEWAY_REACHABILITY, 0.0, "192.168.1.1", ProbeStatus.FAILED)],
        MetricType.GATEWAY_PACKET_LOSS: [make_measurement(MetricType.GATEWAY_PACKET_LOSS, 1.0, "192.168.1.1", ProbeStatus.FAILED)],
        MetricType.EXTERNAL_PACKET_LOSS: [make_measurement(MetricType.EXTERNAL_PACKET_LOSS, 1.0, "1.1.1.1", ProbeStatus.FAILED)],
    }
    diag = await engine.evaluate_windows(windows)
    assert diag.probable_cause == ProbableCause.LOCAL_GATEWAY_UNREACHABLE
    assert diag.confidence >= 0.85
    assert diag.severity == DiagnosisSeverity.CRITICAL
    assert len(diag.supporting_evidence) >= 1


@pytest.mark.asyncio
async def test_diagnosis_upstream_isp_outage(diagnosis_setup):
    engine, bus, repo = diagnosis_setup
    # Local Gateway is 100% fine (0 loss, 4ms latency)
    # BUT External targets show 100% loss!
    windows = {
        MetricType.GATEWAY_REACHABILITY: [make_measurement(MetricType.GATEWAY_REACHABILITY, 1.0, "192.168.1.1")],
        MetricType.GATEWAY_LATENCY: [make_measurement(MetricType.GATEWAY_LATENCY, 4.0, "192.168.1.1")],
        MetricType.GATEWAY_PACKET_LOSS: [make_measurement(MetricType.GATEWAY_PACKET_LOSS, 0.0, "192.168.1.1")],
        MetricType.EXTERNAL_PACKET_LOSS: [
            make_measurement(MetricType.EXTERNAL_PACKET_LOSS, 1.0, "1.1.1.1", ProbeStatus.FAILED),
            make_measurement(MetricType.EXTERNAL_PACKET_LOSS, 1.0, "8.8.8.8", ProbeStatus.FAILED),
        ],
    }
    diag = await engine.evaluate_windows(windows)
    assert diag.probable_cause == ProbableCause.ISP_UPSTREAM_OUTAGE
    assert diag.confidence >= 0.90
    assert diag.severity == DiagnosisSeverity.CRITICAL


@pytest.mark.asyncio
async def test_diagnosis_dns_unresponsive(diagnosis_setup):
    engine, bus, repo = diagnosis_setup
    # Gateway is healthy, External IP ping is healthy (0% loss, 20ms)
    # BUT DNS query success rate is 0.0!
    windows = {
        MetricType.GATEWAY_REACHABILITY: [make_measurement(MetricType.GATEWAY_REACHABILITY, 1.0, "192.168.1.1")],
        MetricType.GATEWAY_PACKET_LOSS: [make_measurement(MetricType.GATEWAY_PACKET_LOSS, 0.0, "192.168.1.1")],
        MetricType.EXTERNAL_PACKET_LOSS: [make_measurement(MetricType.EXTERNAL_PACKET_LOSS, 0.0, "1.1.1.1")],
        MetricType.EXTERNAL_LATENCY: [make_measurement(MetricType.EXTERNAL_LATENCY, 25.0, "1.1.1.1")],
        MetricType.DNS_SUCCESS_RATE: [make_measurement(MetricType.DNS_SUCCESS_RATE, 0.0, "system_dns", ProbeStatus.FAILED)],
    }
    diag = await engine.evaluate_windows(windows)
    assert diag.probable_cause == ProbableCause.DNS_RESOLVER_UNRESPONSIVE
    assert diag.confidence >= 0.90
    assert diag.auto_remediation_permitted is True
    assert "switch_dns_resolver" in diag.recommended_actions


@pytest.mark.asyncio
async def test_diagnosis_destination_specific_outage(diagnosis_setup):
    engine, bus, repo = diagnosis_setup
    # Gateway is healthy, 8.8.8.8 and 9.9.9.9 are healthy, but bad-host.com has 100% loss
    windows = {
        MetricType.GATEWAY_REACHABILITY: [make_measurement(MetricType.GATEWAY_REACHABILITY, 1.0, "192.168.1.1")],
        MetricType.EXTERNAL_PACKET_LOSS: [
            make_measurement(MetricType.EXTERNAL_PACKET_LOSS, 0.0, "8.8.8.8", ProbeStatus.SUCCESS),
            make_measurement(MetricType.EXTERNAL_PACKET_LOSS, 0.0, "9.9.9.9", ProbeStatus.SUCCESS),
            make_measurement(MetricType.EXTERNAL_PACKET_LOSS, 1.0, "bad-host.com", ProbeStatus.FAILED),
            make_measurement(MetricType.EXTERNAL_PACKET_LOSS, 1.0, "bad-host.com", ProbeStatus.FAILED),
        ],
    }
    diag = await engine.evaluate_windows(windows)
    assert diag.probable_cause == ProbableCause.DESTINATION_SPECIFIC_OUTAGE
    assert diag.auto_remediation_permitted is False  # Cannot repair third-party remote server


@pytest.mark.asyncio
async def test_diagnosis_wifi_degraded(diagnosis_setup):
    engine, bus, repo = diagnosis_setup
    windows = {
        MetricType.WIFI_SIGNAL_PERCENT: [make_measurement(MetricType.WIFI_SIGNAL_PERCENT, 12.0, "wifi_link", ProbeStatus.DEGRADED)],
        MetricType.GATEWAY_LATENCY: [make_measurement(MetricType.GATEWAY_LATENCY, 45.0, "192.168.1.1")],
    }
    diag = await engine.evaluate_windows(windows)
    assert diag.probable_cause == ProbableCause.WI_FI_SIGNAL_DEGRADED
    assert diag.confidence >= 0.80


@pytest.mark.asyncio
async def test_diagnosis_healthy(diagnosis_setup):
    engine, bus, repo = diagnosis_setup
    windows = {
        MetricType.GATEWAY_REACHABILITY: [make_measurement(MetricType.GATEWAY_REACHABILITY, 1.0, "192.168.1.1")],
        MetricType.GATEWAY_LATENCY: [make_measurement(MetricType.GATEWAY_LATENCY, 3.5, "192.168.1.1")],
        MetricType.EXTERNAL_LATENCY: [make_measurement(MetricType.EXTERNAL_LATENCY, 22.0, "1.1.1.1")],
        MetricType.EXTERNAL_PACKET_LOSS: [make_measurement(MetricType.EXTERNAL_PACKET_LOSS, 0.0, "1.1.1.1")],
        MetricType.DNS_SUCCESS_RATE: [make_measurement(MetricType.DNS_SUCCESS_RATE, 1.0, "system_dns")],
    }
    diag = await engine.evaluate_windows(windows)
    assert diag.probable_cause == ProbableCause.HEALTHY
    assert diag.confidence == 1.0
