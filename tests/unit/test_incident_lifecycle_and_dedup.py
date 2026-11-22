"""Unit tests for complete Incident Lifecycle Management, Deduplication, and Recovery."""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from app.core.models.metrics import (
    Diagnosis,
    ProbableCause,
    DiagnosisSeverity,
    IncidentLifecycleState,
    IncidentResolutionType,
    ActionClassification,
    ActionExecutionRecord,
    ActionExecutionStatus,
    RiskLevel,
    Evidence,
    MetricType,
)
from app.storage.database import DatabaseManager
from app.storage.repositories.incident_repo import IncidentRepository
from app.storage.repositories.audit_repo import AuditRepository


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_lifecycle.db"
    return DatabaseManager(db_path=db_file)


@pytest.fixture
def inc_repo(temp_db):
    return IncidentRepository(temp_db)


@pytest.fixture
def audit_repo(temp_db):
    return AuditRepository(temp_db)


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app


def test_incident_deduplication_and_occurrence_count(inc_repo):
    """Test that recurring diagnoses with identical cause & component correlate into 1 row."""
    diag1 = Diagnosis(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        probable_cause=ProbableCause.ISP_UPSTREAM_HIGH_LATENCY,
        confidence=0.88,
        severity=DiagnosisSeverity.MEDIUM,
        explanation="First detection of ISP upstream delay",
        supporting_evidence=[
            Evidence(metric_type=MetricType.EXTERNAL_LATENCY, target="external", observed_value=95.0, threshold_value=50.0, condition=">")
        ],
        affected_component="isp_gateway",
    )

    inc_id1, is_new1 = inc_repo.save_or_update(diag1)
    assert is_new1 is True
    assert inc_id1 == diag1.id

    # Second occurrence 10 seconds later
    diag2 = Diagnosis(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc) + timedelta(seconds=10),
        probable_cause=ProbableCause.ISP_UPSTREAM_HIGH_LATENCY,
        confidence=0.91,
        severity=DiagnosisSeverity.HIGH,
        explanation="Second observation of ISP upstream delay",
        supporting_evidence=[
            Evidence(metric_type=MetricType.EXTERNAL_LATENCY, target="external", observed_value=110.0, threshold_value=50.0, condition=">")
        ],
        affected_component="isp_gateway",
    )

    inc_id2, is_new2 = inc_repo.save_or_update(diag2)
    assert is_new2 is False
    assert inc_id2 == inc_id1  # Reused existing incident record

    # Verify database state
    stored = inc_repo.get_by_id(inc_id1)
    assert stored is not None
    assert stored.occurrence_count == 2
    assert stored.confidence == 0.91
    assert stored.severity == DiagnosisSeverity.HIGH


def test_incident_state_transitions(inc_repo):
    """Test valid state transitions across full incident lifecycle."""
    diag = Diagnosis(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        probable_cause=ProbableCause.LOCAL_GATEWAY_HIGH_LATENCY,
        confidence=0.85,
        severity=DiagnosisSeverity.MEDIUM,
        explanation="High latency on local router",
        affected_component="router_gateway",
    )
    inc_id, _ = inc_repo.save_or_update(diag)

    # 1. Transition to REMEDIATING
    ok = inc_repo.transition_state(inc_id, IncidentLifecycleState.REMEDIATING)
    assert ok is True
    assert inc_repo.get_by_id(inc_id).status == IncidentLifecycleState.REMEDIATING

    # 2. Transition to VERIFYING_RECOVERY
    ok = inc_repo.transition_state(inc_id, IncidentLifecycleState.VERIFYING_RECOVERY)
    assert ok is True
    assert inc_repo.get_by_id(inc_id).status == IncidentLifecycleState.VERIFYING_RECOVERY

    # 3. Transition to RESOLVED with action record
    action_rec_id = str(uuid.uuid4())
    ok = inc_repo.transition_state(
        inc_id,
        IncidentLifecycleState.RESOLVED,
        resolution_type=IncidentResolutionType.AUTOMATICALLY_REPAIRED,
        action_record_id=action_rec_id,
        notes="Rechecked gateway connectivity successfully",
    )
    assert ok is True
    resolved = inc_repo.get_by_id(inc_id)
    assert resolved.status == IncidentLifecycleState.RESOLVED
    assert resolved.resolution_type == IncidentResolutionType.AUTOMATICALLY_REPAIRED
    assert resolved.action_record_id == action_rec_id
    assert resolved.resolved_at is not None


def test_natural_recovery_transition(inc_repo):
    """Test that natural recovery correctly records NATURAL_RECOVERY resolution type."""
    diag = Diagnosis(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        probable_cause=ProbableCause.UNKNOWN_ANOMALY,
        confidence=0.75,
        severity=DiagnosisSeverity.LOW,
        explanation="Transient network fluctuation",
        affected_component="network",
    )
    inc_id, _ = inc_repo.save_or_update(diag)

    ok = inc_repo.transition_state(
        inc_id,
        IncidentLifecycleState.NATURALLY_RECOVERED,
        resolution_type=IncidentResolutionType.NATURALLY_RECOVERED,
        notes="Indicators returned to healthy bounds without intervention",
    )
    assert ok is True
    rec = inc_repo.get_by_id(inc_id)
    assert rec.status == IncidentLifecycleState.NATURALLY_RECOVERED
    assert rec.resolution_type == IncidentResolutionType.NATURALLY_RECOVERED


def test_action_audit_with_classification(audit_repo):
    """Test persisting and querying action execution records with classification."""
    rec = ActionExecutionRecord(
        id=str(uuid.uuid4()),
        action_id="switch_dns_resolver",
        action_name="Switch Interface DNS Resolver",
        risk_level=RiskLevel.LEVEL_2_CONTROLLED,
        status=ActionExecutionStatus.SUCCEEDED,
        action_classification=ActionClassification.CONFIGURATION_CHANGE,
    )
    audit_repo.save(rec)

    recent = audit_repo.get_recent(limit=5)
    assert len(recent) == 1
    assert recent[0].action_id == "switch_dns_resolver"
    assert recent[0].action_classification == ActionClassification.CONFIGURATION_CHANGE


def test_diagnosis_view_table_updates_in_place(qapp):
    """Test that repeated table updates in DiagnosisView modify items in-place without Qt ownership errors."""
    from app.ui.views.diagnosis_view import DiagnosisView
    from app.diagnosis.deep_scan import DeepScanReport, DeepScanStepResult

    view = DiagnosisView()
    assert view.table.rowCount() == 6

    # 1. Update from deep scan 3 times sequentially
    steps = [
        DeepScanStepResult(step_id=1, name="Gateway", passed=True, latency_ms=1.2, loss_pct=0.0, details="Gateway ping 1.2ms"),
        DeepScanStepResult(step_id=2, name="DNS", passed=True, latency_ms=22.0, loss_pct=0.0, details="DNS latency 22ms"),
        DeepScanStepResult(step_id=3, name="External", passed=True, latency_ms=45.0, loss_pct=0.0, details="External 45ms"),
        DeepScanStepResult(step_id=4, name="Device", passed=True, latency_ms=0.5, loss_pct=0.0, details="Adapter healthy"),
        DeepScanStepResult(step_id=5, name="MTU", passed=True, latency_ms=4.0, loss_pct=0.0, details="MTU bufferbloat 4ms"),
    ]
    rep = DeepScanReport(
        timestamp=datetime.now(),
        duration_sec=3.5,
        overall_health=True,
        steps=steps,
        gateway_latency_ms=1.2,
        dns_latency_ms=22.0,
        external_latency_ms=45.0,
        packet_loss_pct=0.0,
        wifi_signal_pct=85.0,
        summary_arabic="الشبكة سليمة",
        explanation_arabic="كافة الطبقات الميدانية تعمل بكفاءة تامة.",
        bufferbloat_grade="A",
    )
    for _ in range(3):
        view.update_from_deep_scan(rep)
        assert view.table.item(0, 1).text() == "1.2 ms"
        assert view.table.item(1, 1).text() == "45.0 ms"
        assert view.table.item(2, 1).text() == "22.0 ms"


def test_dns_view_comparison_bars_honesty_when_candidate_faster(qapp):
    """Test that when candidate is faster (e.g. 48ms vs 52.9ms), current server is NOT falsely labeled fastest."""
    from app.ui.views.dns_view import DNSView
    from app.dns.benchmark import ResolverScore

    view = DNSView()
    scores = [
        ResolverScore(name="Google Public DNS Secondary", ip="8.8.4.4", mean_latency_ms=48.0, median_latency_ms=48.0, success_rate=1.0, composite_score=95.0),
        ResolverScore(name="Cloudflare", ip="1.1.1.1", mean_latency_ms=51.4, median_latency_ms=52.9, success_rate=1.0, composite_score=92.0),
    ]

    view.update_rankings(
        scores=scores,
        active_ms=52.9,
        active_name="Cloudflare",
        is_optimal=False,
    )

    # 1. Current server must NOT claim to be fastest
    curr_text = view.lbl_curr_name.text()
    assert "الأسرع حالياً" not in curr_text
    assert "أبطأ" in curr_text

    fast_text = view.lbl_fast_name.text()
    assert "هيتم التحويل" in fast_text
    assert "8.8.4.4" in fast_text
    assert "لا حاجة للتغيير" not in fast_text


def test_history_view_deduplicates_and_translates_actions(qapp):
    """Test that 4 consecutive jitter incidents collapse into 1 card with Arabic action translation."""
    from app.ui.views.history_view import HistoryView

    now = datetime.now()
    incidents = [
        Diagnosis(
            probable_cause=ProbableCause.UNKNOWN_ANOMALY,
            timestamp=now,
            confidence=0.8,
            severity=DiagnosisSeverity.LOW,
            explanation="رصد تذبذب مرتفع في زمن وصول الحزم (Jitter: 48.8 ms).",
            recommended_actions=["inspect_bufferbloat"],
            affected_component="network",
        ),
        Diagnosis(
            probable_cause=ProbableCause.UNKNOWN_ANOMALY,
            timestamp=now + timedelta(seconds=15),
            confidence=0.8,
            severity=DiagnosisSeverity.LOW,
            explanation="رصد تذبذب مرتفع في زمن وصول الحزم (Jitter: 48.8 ms).",
            recommended_actions=["inspect_bufferbloat"],
            affected_component="network",
        ),
        Diagnosis(
            probable_cause=ProbableCause.UNKNOWN_ANOMALY,
            timestamp=now + timedelta(seconds=30),
            confidence=0.8,
            severity=DiagnosisSeverity.LOW,
            explanation="رصد تذبذب مرتفع في زمن وصول الحزم (Jitter: 52.1 ms).",
            recommended_actions=["inspect_bufferbloat"],
            affected_component="network",
        ),
        Diagnosis(
            probable_cause=ProbableCause.UNKNOWN_ANOMALY,
            timestamp=now + timedelta(seconds=45),
            confidence=0.8,
            severity=DiagnosisSeverity.LOW,
            explanation="رصد تذبذب مرتفع في زمن وصول الحزم (Jitter: 52.1 ms).",
            recommended_actions=["inspect_bufferbloat"],
            affected_component="network",
        ),
    ]

    view = HistoryView()
    view.update_incidents(incidents)

    # 4 incidents collapsed into exactly 1 card
    assert view.events_list_layout.count() == 1
    card = view.events_list_layout.itemAt(0).widget()
    from PySide6.QtWidgets import QLabel
    card_text = " ".join([lbl.text() for lbl in card.findChildren(QLabel)])

    assert "تكرر 4 مرات" in card_text
    assert "inspect_bufferbloat" not in card_text
    assert "تدقيق طوابير حزم الراوتر والضغط المحلي" in card_text


def test_multi_dns_primary_vs_secondary_isolation(qapp):
    """Test that when multiple DNS servers (1.1.1.1, 8.8.8.8, 9.9.9.9) are configured:
    1. Primary (1.1.1.1) is matched for active latency and marked as primary active.
    2. Secondary (8.8.8.8) is marked as registered fallback and NOT active.
    3. The two bars display honest distinct latencies (54.1 ms vs 44.7 ms).
    4. Only exactly one server in the table has 'معتمد حالياً ✓'.
    """
    from app.ui.views.dns_view import DNSView
    from app.dns.benchmark import ResolverScore
    from PySide6.QtWidgets import QPushButton

    view = DNSView()
    # Configure 3 DNS servers on the adapter (just like user's Windows adapter)
    view.set_active_dns_info(["1.1.1.1", "8.8.8.8", "9.9.9.9"])

    scores = [
        ResolverScore(name="Google Public DNS Primary", ip="8.8.8.8", mean_latency_ms=44.7, median_latency_ms=44.7, success_rate=1.0, composite_score=98.0),
        ResolverScore(name="Google Public DNS Secondary", ip="8.8.4.4", mean_latency_ms=47.7, median_latency_ms=47.7, success_rate=1.0, composite_score=95.0),
        ResolverScore(name="Cloudflare Primary", ip="1.1.1.1", mean_latency_ms=54.1, median_latency_ms=54.1, success_rate=1.0, composite_score=90.0),
        ResolverScore(name="Quad9 Secure Primary", ip="9.9.9.9", mean_latency_ms=61.6, median_latency_ms=61.6, success_rate=1.0, composite_score=85.0),
    ]

    view.update_rankings(
        scores=scores,
        active_ms=54.1,
        active_name="Cloudflare",
        is_optimal=False,
    )

    # Comparison bars verification
    assert view.lbl_curr_ms.text() == "54.1 ms"  # Cloudflare's own latency
    assert view.lbl_fast_ms.text() == "44.7 ms"  # Google's latency (fastest alternative)
    assert view.lbl_curr_ms.text() != view.lbl_fast_ms.text()  # MUST NOT be equal!

    # Table rows verification
    table = view.table
    assert table.rowCount() == 4

    # Row 0: Google (8.8.8.8) - registered fallback
    assert "8.8.8.8" in table.item(0, 2).text()
    assert "احتياطي مسجل" in table.item(0, 6).text()
    btn_0 = table.cellWidget(0, 7).findChild(QPushButton)
    assert btn_0.text() == "عيّن كأساسي"
    assert btn_0.isEnabled() is True

    # Row 2: Cloudflare (1.1.1.1) - primary active
    assert "1.1.1.1" in table.item(2, 2).text()
    assert "الأساسي المعتمد" in table.item(2, 6).text()
    btn_2 = table.cellWidget(2, 7).findChild(QPushButton)
    assert btn_2.text() == "معتمد حالياً ✓"
    assert btn_2.isEnabled() is False

    # Row 3: Quad9 (9.9.9.9) - registered fallback
    assert "9.9.9.9" in table.item(3, 2).text()
    assert "احتياطي مسجل" in table.item(3, 6).text()
    btn_3 = table.cellWidget(3, 7).findChild(QPushButton)
    assert btn_3.text() == "عيّن كأساسي"
    assert btn_3.isEnabled() is True

    # Exactly one button across the table has "معتمد حالياً ✓"
    active_buttons = [
        table.cellWidget(r, 7).findChild(QPushButton).text()
        for r in range(table.rowCount())
        if "معتمد حالياً" in table.cellWidget(r, 7).findChild(QPushButton).text()
    ]
    assert len(active_buttons) == 1


def test_autonomous_instant_dns_switching_and_dashboard_card(qapp):
    """Test that in Autonomous mode:
    1. If candidate is faster (56 ms vs 45 ms), auto_applied card shows 'تم الإصلاح الذاتي تلقائياً ✓'.
    2. Button is 'تراجع عن التغيير', NEVER 'طبّق التغيير الآن'.
    3. When candidate is faster and autonomous mode is active, it NEVER asks user to manually apply.
    """
    from app.ui.widgets.bar_row import DNSRecommendationPanel

    panel = DNSRecommendationPanel()

    # 1. When auto_applied=True (autonomous instant repair applied)
    panel.update_dns_state(
        curr_name="Cloudflare",
        curr_ms=56.0,
        best_name="Google Public DNS",
        best_ip="8.8.4.4",
        best_ms=45.0,
        is_optimal=True,
        is_autonomous=True,
        auto_applied=True,
    )

    assert "تم الإصلاح الذاتي" in panel.lbl_tag.text()
    assert panel.btn_action.text() == "تراجع عن التغيير"
    assert panel.btn_action.isEnabled() is True
    assert "طبّق التغيير" not in panel.btn_action.text()
    assert "معالجة ذاتية متاحة" not in panel.lbl_tag.text()

    # 2. When candidate is optimal (e.g. diff <= 5 ms)
    panel.update_dns_state(
        curr_name="Google Public DNS",
        curr_ms=45.0,
        best_name="Google Public DNS Secondary",
        best_ip="8.8.4.4",
        best_ms=43.0,
        is_optimal=True,
        is_autonomous=True,
    )
    assert "مستقر وسريع" in panel.lbl_tag.text()
    assert panel.btn_action.text() == "معتمد حالياً ✓"
    assert panel.btn_action.isEnabled() is False

    # 3. When in Manual mode (is_autonomous=False) and not optimal
    panel.update_dns_state(
        curr_name="Cloudflare",
        curr_ms=56.0,
        best_name="Google Public DNS",
        best_ip="8.8.4.4",
        best_ms=45.0,
        is_optimal=False,
        is_autonomous=False,
    )
    assert panel.lbl_tag.text() == "توصية بتحسين DNS"
    assert panel.btn_action.text() == "طبّق التغيير الآن"
    assert panel.btn_action.isEnabled() is True



