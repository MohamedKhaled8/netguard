"""Unit tests for Timeline dynamic narrative generation from real incident and audit records."""

import pytest
import sys
from datetime import datetime, timezone, timedelta
from PySide6.QtWidgets import QApplication

from app.ui.widgets.timeline import TimelinePanel
from app.core.models.metrics import (
    Diagnosis,
    ProbableCause,
    DiagnosisSeverity,
    Evidence,
    MetricType,
    ActionExecutionRecord,
    ActionExecutionStatus,
    RiskLevel,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_timeline_default_idle_state(qapp):
    """Initial timeline starts in clean idle state without fake story strings."""
    timeline = TimelinePanel()
    timeline.show()
    assert "لا توجد أحداث" in timeline.lbl_sub.text()
    assert "النظام مستقر" in timeline.status_chip.text()
    assert timeline.btn_rollback.isVisible() is True
    assert timeline.btn_evidence.isEnabled() is False

    # All timestamps must be placeholder '—', not fake historical clocks
    for step in timeline.step_widgets:
        assert step.lbl_time.text() == "—"


def test_timeline_update_from_records_success(qapp):
    """Timeline dynamically synthesizes all 4 steps from real incident and audit records."""
    t_inc = datetime(2026, 11, 17, 10, 15, 30, tzinfo=timezone.utc)
    t_aud = datetime(2026, 11, 17, 10, 15, 45, tzinfo=timezone.utc)

    incident = Diagnosis(
        probable_cause=ProbableCause.BUFFERBLOAT_UPLOAD,
        confidence=0.92,
        severity=DiagnosisSeverity.HIGH,
        supporting_evidence=[
            Evidence(
                metric_type=MetricType.GATEWAY_LATENCY,
                target="gateway",
                observed_value=145.2,
                threshold_value=45.0,
                condition=">",
            )
        ],
        explanation="تكدس الحزم عند الراوتر.",
        recommended_actions=["تفعيل NetQoS لتقييد الرفع"],
    )
    incident.timestamp = t_inc

    record = ActionExecutionRecord(
        id="act-test-01",
        action_id="qos_throttle_background",
        action_name="تقييد العمليات الخلفية",
        risk_level=RiskLevel.LEVEL_2_CONTROLLED,
        trigger_diagnosis_id="inc-test-01",
        pre_remedy_metrics={"rtt_ms": 145.2},
        post_remedy_metrics={"rtt_ms": 28.4},
        status=ActionExecutionStatus.SUCCEEDED,
        execution_duration_ms=450.0,
        verification_duration_ms=250.0,
    )
    record.timestamp = t_aud

    timeline = TimelinePanel()
    timeline.show()
    timeline.update_from_records(incident, record)

    # Header & Chip
    assert "تم حله تلقائياً" in timeline.status_chip.text()
    assert timeline.btn_rollback.isVisible() is True
    assert timeline.btn_evidence.isEnabled() is True

    # Step 1: Detect with real measured numbers
    s1 = timeline.step_widgets[0]
    assert s1.lbl_title.text() == "اكتشاف المشكلة"
    assert "145.2ms" in s1.lbl_desc.text()
    assert "45.0ms" in s1.lbl_desc.text()

    # Step 2: Cause with real cause text and confidence
    s2 = timeline.step_widgets[1]
    assert s2.lbl_title.text() == "تحديد السبب"
    assert "Bufferbloat" in s2.lbl_desc.text()
    assert "92%" in s2.lbl_desc.text()

    # Step 3: Fix with real action name
    s3 = timeline.step_widgets[2]
    assert s3.lbl_title.text() == "الإصلاح"
    assert "تقييد العمليات الخلفية" in s3.lbl_desc.text()
    assert "NetQoS" in s3.lbl_desc.text()

    # Step 4: Result with real duration and post-remedy metric
    s4 = timeline.step_widgets[3]
    assert s4.lbl_title.text() == "النتيجة"
    assert "28.4ms" in s4.lbl_desc.text()
    assert "0.7 ثانية" in s4.lbl_desc.text()


def test_timeline_update_from_incident_only(qapp):
    """When incident exists without completed remediation, timeline prompts user action."""
    t_inc = datetime(2026, 11, 17, 14, 20, 10, tzinfo=timezone.utc)
    incident = Diagnosis(
        probable_cause=ProbableCause.DNS_RESOLVER_HIGH_LATENCY,
        confidence=0.85,
        severity=DiagnosisSeverity.MEDIUM,
        supporting_evidence=[
            Evidence(
                metric_type=MetricType.DNS_LATENCY,
                target="resolver",
                observed_value=185.0,
                threshold_value=50.0,
                condition=">",
            )
        ],
        explanation="بطء شديد في استجابة خادم DNS الحالي.",
        recommended_actions=["التحويل إلى Cloudflare DNS"],
    )
    incident.timestamp = t_inc

    timeline = TimelinePanel()
    timeline.show()
    timeline.update_from_records(incident, None)

    assert "يحتاج انتباهك" in timeline.status_chip.text()
    assert timeline.btn_rollback.isVisible() is True
    assert timeline.btn_evidence.isEnabled() is True
    assert "185.0ms" in timeline.step_widgets[0].lbl_desc.text()
    assert "DNS" in timeline.step_widgets[1].lbl_desc.text()
    assert "Cloudflare DNS" in timeline.step_widgets[2].lbl_desc.text()
    assert "في انتظار" in timeline.step_widgets[3].lbl_desc.text()


def test_timeline_reset_to_idle(qapp):
    """Calling update_from_records(None, None) resets to idle state."""
    timeline = TimelinePanel()
    timeline.show()
    timeline.update_from_records(None, None)
    assert "لا توجد أحداث" in timeline.lbl_sub.text()
    assert "النظام مستقر" in timeline.status_chip.text()
    assert timeline.btn_rollback.isVisible() is True
    assert timeline.btn_evidence.isEnabled() is False
