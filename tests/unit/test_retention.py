"""Unit tests for Phase 4.1 Retention, 1-minute Downsampling, and Database Vacuuming."""

from datetime import datetime, timezone, timedelta, date
from pathlib import Path
import pytest

from app.core.models.metrics import (
    Measurement,
    MetricType,
    ProbeStatus,
    MeasurementSource,
    Diagnosis,
    ProbableCause,
    DiagnosisSeverity,
    ActionExecutionRecord,
    ActionExecutionStatus,
    RiskLevel,
)
from app.storage.database import DatabaseManager
from app.storage.repositories.measurement_repo import MeasurementRepository
from app.storage.repositories.incident_repo import IncidentRepository
from app.storage.repositories.audit_repo import AuditRepository


@pytest.fixture
def test_db(tmp_path: Path):
    db_path = tmp_path / "test_retention.db"
    db_mgr = DatabaseManager(db_path=db_path, enable_wal=False)
    meas_repo = MeasurementRepository(db_mgr)
    inc_repo = IncidentRepository(db_mgr)
    audit_repo = AuditRepository(db_mgr)
    return db_mgr, meas_repo, inc_repo, audit_repo


def test_schema_v2_migration(test_db):
    db_mgr, _, _, _ = test_db
    with db_mgr.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT version FROM schema_version;")
        versions = [row["version"] for row in cur.fetchall()]
        assert 1 in versions
        assert 2 in versions

        # Check measurement_aggregates_1m table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='measurement_aggregates_1m';")
        assert cur.fetchone() is not None


def test_downsampling_and_p95_calculation(test_db):
    _, meas_repo, _, _ = test_db

    # Create 20 measurements in the same 1-minute window with known values 1 to 20
    base_time = datetime(2026, 11, 15, 10, 0, 5, tzinfo=timezone.utc)
    for i in range(1, 21):
        m = Measurement(
            timestamp=base_time + timedelta(seconds=i),
            source=MeasurementSource.ICMP_ECHO,
            target_or_interface="192.168.1.1",
            metric_type=MetricType.GATEWAY_LATENCY,
            raw_value=float(i),
            normalized_value=float(i),
            unit="ms",
            status=ProbeStatus.SUCCESS if i < 20 else ProbeStatus.TIMEOUT,
            confidence=1.0,
        )
        meas_repo.save(m)

    cutoff = datetime(2026, 11, 15, 10, 5, 0, tzinfo=timezone.utc)
    created = meas_repo.downsample_to_aggregates(cutoff_timestamp=cutoff)
    assert created == 1

    # Check the aggregated row in measurement_aggregates_1m
    with meas_repo.db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM measurement_aggregates_1m WHERE metric_type = ?;", (MetricType.GATEWAY_LATENCY.value,))
        row = cur.fetchone()
        assert row is not None
        assert row["sample_count"] == 20
        assert row["min_value"] == 1.0
        assert row["max_value"] == 20.0
        assert abs(row["avg_value"] - 10.5) < 0.01
        # 95th percentile of 1..20 is 19.0
        assert row["p95_value"] == 19.0
        # 1 timeout out of 20 = 0.05 loss rate
        assert abs(row["loss_rate"] - 0.05) < 0.001


def test_prune_raw_samples_and_aggregates(test_db):
    _, meas_repo, inc_repo, audit_repo = test_db

    # Create old measurement (48 hours ago)
    old_time = datetime.now(timezone.utc) - timedelta(hours=48)
    m_old = Measurement(
        timestamp=old_time,
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="192.168.1.1",
        metric_type=MetricType.GATEWAY_LATENCY,
        raw_value=12.5,
        normalized_value=12.5,
        unit="ms",
        status=ProbeStatus.SUCCESS,
        confidence=1.0,
    )
    meas_repo.save(m_old)

    # Create recent measurement (1 hour ago)
    recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
    m_recent = Measurement(
        timestamp=recent_time,
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="192.168.1.1",
        metric_type=MetricType.GATEWAY_LATENCY,
        raw_value=5.0,
        normalized_value=5.0,
        unit="ms",
        status=ProbeStatus.SUCCESS,
        confidence=1.0,
    )
    meas_repo.save(m_recent)

    # Prune raw samples keeping only 24 hours
    deleted_raw = meas_repo.prune_raw_samples(keep_hours=24)
    assert deleted_raw == 1

    # Verify only recent measurement remains in raw measurements table
    remaining_raw = meas_repo.get_recent(limit=10)
    assert len(remaining_raw) == 1
    assert remaining_raw[0].raw_value == 5.0

    # Verify old sample was downsampled into aggregates before deletion!
    with meas_repo.db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM measurement_aggregates_1m;")
        assert cur.fetchone()[0] == 1


def test_get_day_slots_reads_from_aggregates(test_db):
    _, meas_repo, inc_repo, _ = test_db

    target_d = date(2026, 11, 10)
    # Insert aggregate row directly for target_d slot 20 (10:00 AM)
    with meas_repo.db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO measurement_aggregates_1m (
                bucket_start, metric_type, source, target_or_interface,
                sample_count, min_value, avg_value, max_value, p95_value, loss_rate
            ) VALUES (
                '2026-11-10T10:00:00', 'gateway_latency', 'icmp_echo', '192.168.1.1',
                60, 4.0, 5.0, 8.0, 6.0, 0.0
            );
        """)
        conn.commit()

    slots = meas_repo.get_day_slots(target_d)
    assert len(slots) == 48
    # Slot 20 (10:00 AM -> hour 10 * 2 + 0 = 20) should now be 'healthy' from aggregate data!
    assert slots[20] == "healthy"


def test_clear_all_history(test_db):
    _, meas_repo, inc_repo, audit_repo = test_db

    # Add measurement
    m = Measurement(
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="192.168.1.1",
        metric_type=MetricType.GATEWAY_LATENCY,
        raw_value=5.0,
        normalized_value=5.0,
        unit="ms",
        status=ProbeStatus.SUCCESS,
        confidence=1.0,
    )
    meas_repo.save(m)

    # Add incident
    diag = Diagnosis(
        probable_cause=ProbableCause.LOCAL_GATEWAY_HIGH_LATENCY,
        confidence=0.9,
        severity=DiagnosisSeverity.HIGH,
        explanation="Test incident",
        auto_remediation_permitted=False,
    )
    inc_repo.save(diag)

    # Add audit record
    rec = ActionExecutionRecord(
        action_id="flush_dns",
        action_name="Flush DNS",
        risk_level=RiskLevel.LEVEL_1_LOW,
        status=ActionExecutionStatus.SUCCEEDED,
        execution_duration_ms=10.0,
        verification_duration_ms=10.0,
    )
    audit_repo.save(rec)

    # Clear all history
    result = meas_repo.clear_all_history(incident_repo=inc_repo, audit_repo=audit_repo)
    assert result["measurements"] >= 1
    assert result["incidents"] == 1
    assert result["audit"] == 1

    # Verify tables are empty
    assert len(meas_repo.get_recent(limit=10)) == 0
    assert len(inc_repo.get_recent(limit=10)) == 0
    assert len(audit_repo.get_recent(limit=10)) == 0
