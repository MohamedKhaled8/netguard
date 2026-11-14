"""Unit tests for NetGuard AI Stage 0 Foundation."""

import pytest
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from app.core.config.models import AppConfig
from app.core.config.loader import load_config
from app.core.events.bus import EventBus
from app.core.models.metrics import (
    Measurement,
    MetricType,
    ProbeStatus,
    MeasurementSource,
    Diagnosis,
    ProbableCause,
    DiagnosisSeverity,
    Evidence,
    ActionExecutionRecord,
    ActionExecutionStatus,
    RiskLevel,
)
from app.storage.database import DatabaseManager
from app.storage.repositories.measurement_repo import MeasurementRepository
from app.storage.repositories.incident_repo import IncidentRepository
from app.storage.repositories.audit_repo import AuditRepository
from app.platform.factory import get_platform_adapter
from app.bootstrap import bootstrap_application


def test_config_defaults():
    cfg = load_config()
    assert cfg.environment in ("development", "production")
    assert cfg.probing.gateway_interval_sec > 0
    assert "1.1.1.1" in cfg.probing.external_targets
    assert cfg.remediation.mode == "autonomous_safe"


def test_database_and_repositories(tmp_path: Path):
    db_file = tmp_path / "test_netguard.db"
    db_manager = DatabaseManager(db_path=db_file, enable_wal=False)

    meas_repo = MeasurementRepository(db_manager)
    inc_repo = IncidentRepository(db_manager)
    audit_repo = AuditRepository(db_manager)

    # 1. Test Measurement Save & Query
    m = Measurement(
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="192.168.1.1",
        metric_type=MetricType.GATEWAY_LATENCY,
        raw_value=4.2,
        normalized_value=4.2,
        unit="ms",
        status=ProbeStatus.SUCCESS,
        confidence=1.0,
        metadata={"ttl": 64},
    )
    m_id = meas_repo.save(m)
    assert m_id > 0

    latest = meas_repo.get_latest_by_metric(MetricType.GATEWAY_LATENCY, limit=5)
    assert len(latest) == 1
    assert latest[0].raw_value == 4.2
    assert latest[0].target_or_interface == "192.168.1.1"

    # 2. Test Incident Save & Query
    diag = Diagnosis(
        probable_cause=ProbableCause.LOCAL_GATEWAY_HIGH_LATENCY,
        confidence=0.85,
        severity=DiagnosisSeverity.MEDIUM,
        explanation="High ping to gateway detected",
        auto_remediation_permitted=True,
        supporting_evidence=[
            Evidence(
                metric_type=MetricType.GATEWAY_LATENCY,
                target="192.168.1.1",
                observed_value=85.0,
                threshold_value=25.0,
                condition="observed > threshold",
                weight=1.5,
            )
        ],
        recommended_actions=["recheck_gateway"],
    )
    inc_id = inc_repo.save(diag)
    assert inc_id is not None

    incidents = inc_repo.get_recent(limit=5)
    assert len(incidents) == 1
    assert incidents[0].probable_cause == ProbableCause.LOCAL_GATEWAY_HIGH_LATENCY
    assert len(incidents[0].supporting_evidence) == 1

    # 3. Test Audit Record Save & Query
    rec = ActionExecutionRecord(
        action_id="flush_dns",
        action_name="Flush DNS Cache",
        risk_level=RiskLevel.LEVEL_1_LOW,
        status=ActionExecutionStatus.SUCCEEDED,
        execution_duration_ms=12.5,
        verification_duration_ms=150.0,
        rollback_performed=False,
    )
    rec_id = audit_repo.save(rec)
    assert rec_id is not None

    audit_entries = audit_repo.get_recent(limit=5)
    assert len(audit_entries) == 1
    assert audit_entries[0].action_id == "flush_dns"
    assert audit_entries[0].status == ActionExecutionStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_event_bus():
    bus = EventBus()
    received_events = []

    async def on_telemetry(topic: str, payload: dict):
        received_events.append((topic, payload))

    await bus.subscribe("telemetry.*", on_telemetry)

    # Publish matching event
    count = await bus.publish("telemetry.gateway", {"rtt": 5.0})
    assert count == 1
    assert len(received_events) == 1
    assert received_events[0][0] == "telemetry.gateway"
    assert received_events[0][1]["rtt"] == 5.0

    # Publish non-matching event
    count_non = await bus.publish("diagnosis.alert", {"severity": "high"})
    assert count_non == 0
    assert len(received_events) == 1

    # Unsubscribe
    await bus.unsubscribe("telemetry.*", on_telemetry)
    count_after = await bus.publish("telemetry.gateway", {"rtt": 10.0})
    assert count_after == 0


def test_platform_adapter():
    adapter = get_platform_adapter()
    assert adapter is not None
    # Test local loopback TCP connection or ping
    ok, latency = adapter.tcp_connect("127.0.0.1", port=9999, timeout_sec=0.2)
    # Port 9999 may be closed, so ok is bool, latency is float
    assert isinstance(ok, bool)
    assert isinstance(latency, float)


def test_bootstrap():
    ctx = bootstrap_application(in_memory_db=True)
    assert ctx is not None
    assert ctx.config is not None
    assert ctx.platform is not None
    assert ctx.measurements is not None
