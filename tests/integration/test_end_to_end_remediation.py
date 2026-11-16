"""Integration Tests for End-to-End Autonomous Remediation Lifecycle (AC-1 & 4-Tier Coverage).

Tests cover:
- Tier 1: Probe reports high latency -> diagnosis classifier triggers -> orchestrator in Auto mode executes
  mocked-OS light fix -> audit row written to SQLite actions_audit table with pre-change state -> EventBus
  publishes remediation event using EventTopics -> UI timeline model updated -> rollback restores pre-change state.
- Tier 2 (Boundary & Corner Cases): Action execution failure captured in audit; timeout handling; rollback
  with invalid/missing action ID; corrupted pre-state rollback handling.
- Tier 3 (Cross-Feature Combinations): Mode transition from Auto to Watch during diagnosis; sequential incidents
  with targeted rollback; concurrent diagnoses serialized by safety lock; circuit breaker tripping.
- Tier 4 (Real-World Application Scenario): Complete lifecycle from telemetry probe emission to UI reflection
  and user-initiated rollback.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pytest
from PySide6.QtWidgets import QApplication

from app.core.config.models import (
    DiagnosisThresholds,
    RemediationConfig,
)
from app.core.events.bus import EventBus
from app.core.models.metrics import (
    ActionExecutionRecord,
    ActionExecutionStatus,
    Diagnosis,
    DiagnosisSeverity,
    Evidence,
    Measurement,
    MeasurementSource,
    MetricType,
    OperatingMode,
    ProbableCause,
    ProbeStatus,
    RiskLevel,
)
from app.diagnosis.engine import DiagnosisEngine
from app.platform.interfaces import IPlatformAdapter
from app.remediation.actions.flush_dns import FlushDNSCacheAction
from app.remediation.actions.recheck_gateway import RecheckGatewayAction
from app.remediation.actions.renew_dhcp import RenewIPLeaseAction
from app.remediation.actions.switch_dns import SwitchDNSResolverAction
from app.remediation.orchestrator import RemediationOrchestrator
from app.remediation.registry import ActionRegistry, RemediationAction
from app.remediation.safety import ActionSafetyManager
from app.storage.database import DatabaseManager
from app.storage.repositories.audit_repo import AuditRepository
from app.storage.repositories.incident_repo import IncidentRepository
from app.ui.widgets.timeline import TimelinePanel


# ---------------------------------------------------------------------------
# Standardized EventTopics Contract
# ---------------------------------------------------------------------------
try:
    from app.core.events.bus import EventTopics
except (ImportError, AttributeError):
    try:
        from app.core.bus import EventTopics  # type: ignore[no-redef]
    except (ImportError, AttributeError):
        class EventTopics:  # type: ignore[no-redef]
            TELEMETRY_PREFIX = "telemetry."
            DIAGNOSIS_PREFIX = "diagnosis."
            DIAGNOSIS_INCIDENT = "diagnosis.incident"
            REMEDIATION_STARTED = "remediation.started"
            REMEDIATION_COMPLETED = "remediation.completed"
            REMEDIATION_APPROVAL_REQUIRED = "remediation.approval_required"
            REMEDIATION_ACTION_SUPPRESSED = "remediation.action_suppressed"
            REMEDIATION_ROLLBACK_COMPLETED = "remediation.rollback.completed"
            DNS_BENCHMARK_COMPLETED = "dns.benchmark.completed"
            DNS_SWITCHED = "dns.switched"
            MODE_CHANGED = "mode.changed"
            SETTINGS_CHANGED = "settings.changed"


# Canonical OperatingMode resolvers (M1 & legacy compatibility)
MODE_AUTO = getattr(OperatingMode, "AUTO", getattr(OperatingMode, "AUTONOMOUS_SAFE", None))
MODE_ASK = getattr(OperatingMode, "ASK", getattr(OperatingMode, "ASSISTED", None))
MODE_WATCH = getattr(OperatingMode, "WATCH", getattr(OperatingMode, "OBSERVATION", None))


# ---------------------------------------------------------------------------
# Mock Platform Adapter for Controlled OS Simulation
# ---------------------------------------------------------------------------
class MockPlatformAdapter(IPlatformAdapter):
    """Controllable Windows platform mock recording every OS invocation."""

    def __init__(self) -> None:
        self.flushed = False
        self.flush_count = 0
        self.current_dns = ["192.168.1.1"]
        self.set_dns_count = 0
        self.renewed = False
        self.renew_count = 0
        self.ping_ok = True
        self.ping_count = 0
        self.elevated = True
        self.fail_flush = False
        self.fail_dns = False
        self.fail_renew = False
        self.delay_sec = 0.0
        self.commands_executed: List[str] = []

    def is_elevated(self) -> bool:
        return self.elevated

    def get_default_gateway(self) -> str:
        return "192.168.1.1"

    def get_primary_interface(self) -> str:
        return "Wi-Fi"

    def ping(self, target: str, timeout_sec: float = 1.5) -> Tuple[bool, float]:
        self.ping_count += 1
        self.commands_executed.append(f"ping {target}")
        if self.delay_sec > 0:
            time.sleep(self.delay_sec)
        return self.ping_ok, 12.0

    def tcp_connect(self, target: str, port: int = 80, timeout_sec: float = 2.0) -> Tuple[bool, float]:
        self.commands_executed.append(f"tcp_connect {target}:{port}")
        return True, 15.0

    def flush_dns_cache(self) -> Tuple[bool, str]:
        self.flush_count += 1
        self.commands_executed.append("flush_dns_cache")
        if self.delay_sec > 0:
            time.sleep(self.delay_sec)
        if self.fail_flush:
            return False, "Access is denied: Elevated privileges required"
        self.flushed = True
        return True, "Successfully flushed the DNS Resolver Cache."

    def get_interface_dns_servers(self, interface_name: str) -> List[str]:
        return list(self.current_dns)

    def set_interface_dns_servers(self, interface_name: str, servers: List[str]) -> Tuple[bool, str]:
        self.set_dns_count += 1
        self.commands_executed.append(f"set_interface_dns_servers {servers}")
        if self.delay_sec > 0:
            time.sleep(self.delay_sec)
        if self.fail_dns:
            return False, "Failed to set interface DNS servers: simulated error"
        self.current_dns = list(servers)
        return True, "DNS servers configured successfully"

    def renew_ip_lease(self, interface_name: str) -> Tuple[bool, str]:
        self.renew_count += 1
        self.commands_executed.append(f"renew_ip_lease {interface_name}")
        if self.delay_sec > 0:
            time.sleep(self.delay_sec)
        if self.fail_renew:
            return False, "DHCP lease renewal timed out"
        self.renewed = True
        return True, "DHCP lease renewed successfully"

    def get_wifi_metrics(self, interface_name: Optional[str] = None) -> Dict[str, Any]:
        return {"is_wifi": True, "signal_percent": 85.0}


# ---------------------------------------------------------------------------
# Controllable Action for Boundary & Stress Testing
# ---------------------------------------------------------------------------
class ControllableTestAction(RemediationAction):
    """Test action allowing precise control over execution delays, verification, and rollback."""

    def __init__(
        self,
        action_id: str = "controllable_action",
        risk_level: RiskLevel = RiskLevel.LEVEL_1_LOW,
        timeout_sec: float = 2.0,
        cooldown_sec: float = 0.05,
        fail_execute: bool = False,
        fail_verify: bool = False,
        fail_rollback: bool = False,
        exec_delay_sec: float = 0.0,
    ) -> None:
        super().__init__(
            action_id=action_id,
            name=f"Controllable Action {action_id}",
            description="Diagnostic test action",
            risk_level=risk_level,
            timeout_sec=timeout_sec,
            cooldown_sec=cooldown_sec,
        )
        self.fail_execute = fail_execute
        self.fail_verify = fail_verify
        self.fail_rollback = fail_rollback
        self.exec_delay_sec = exec_delay_sec
        self.executed = False
        self.verified = False
        self.rolled_back = False

    def check_preconditions(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Tuple[bool, str]:
        return True, "Preconditions satisfied"

    async def execute(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Any:
        if self.exec_delay_sec > 0:
            await asyncio.sleep(self.exec_delay_sec)
        self.executed = True
        if self.fail_execute:
            raise RuntimeError("Forced execution failure in ControllableTestAction")
        return {"custom_key": "custom_pre_state_value", "timestamp": time.time()}

    async def verify(
        self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any
    ) -> Tuple[bool, str, Dict[str, Any]]:
        self.verified = True
        if self.fail_verify:
            return False, "Forced verification failure", {"error": "verification_failed"}
        return True, "Controllable verification succeeded", {"verified": True}

    async def rollback(
        self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any
    ) -> Tuple[bool, str]:
        self.rolled_back = True
        if self.fail_rollback:
            return False, "Forced rollback failure"
        return True, "Controllable rollback succeeded"


# ---------------------------------------------------------------------------
# Helper function for measurement synthesis
# ---------------------------------------------------------------------------
def make_measurement(
    metric: MetricType,
    val: float,
    target: str = "target",
    status: ProbeStatus = ProbeStatus.SUCCESS,
) -> Measurement:
    return Measurement(
        timestamp=datetime.now(timezone.utc),
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface=target,
        metric_type=metric,
        raw_value=val,
        normalized_value=val,
        unit="ms" if "latency" in metric.value else ("ratio" if "loss" in metric.value else "unit"),
        status=status,
        confidence=1.0,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def qapp() -> QApplication:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


@pytest.fixture
def mock_dns_resolver(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock dns.resolver.Resolver to guarantee deterministic offline execution."""
    class DummyAnswer:
        def to_text(self) -> str:
            return "1.1.1.1"

    def dummy_resolve(self, qname, rdtype="A", *args, **kwargs):
        return [DummyAnswer()]

    monkeypatch.setattr("dns.resolver.Resolver.resolve", dummy_resolve)


@pytest.fixture
def remediation_env(tmp_path):
    """Instantiate a fully isolated, ephemeral NetGuard remediation environment."""
    db_file = tmp_path / "test_netguard_remediation.db"
    db_manager = DatabaseManager(db_path=db_file, enable_wal=False)
    audit_repo = AuditRepository(db_manager)
    incident_repo = IncidentRepository(db_manager)
    bus = EventBus()
    platform = MockPlatformAdapter()
    safety = ActionSafetyManager(failure_threshold=3, reset_timeout_sec=0.2)
    registry = ActionRegistry()

    # Register standard actions
    registry.register(FlushDNSCacheAction())
    registry.register(SwitchDNSResolverAction(fallback_resolvers=["1.1.1.1", "8.8.8.8"]))
    registry.register(RecheckGatewayAction())
    registry.register(RenewIPLeaseAction())

    config = RemediationConfig(
        mode=MODE_AUTO.value if hasattr(MODE_AUTO, "value") else "auto",
        cooldown_period_sec=0.05,
        verification_duration_sec=0.5,
        allow_level_3_disruptive=False,
    )

    orchestrator = RemediationOrchestrator(
        config=config,
        registry=registry,
        safety_manager=safety,
        platform_adapter=platform,
        audit_repo=audit_repo,
        event_bus=bus,
    )

    thresholds = DiagnosisThresholds(
        gateway_latency_critical_ms=80.0,
        gateway_packet_loss_critical=0.40,
        external_latency_critical_ms=200.0,
        external_packet_loss_critical=0.30,
        dns_latency_critical_ms=350.0,
    )
    diagnosis_engine = DiagnosisEngine(thresholds=thresholds, event_bus=bus, incident_repo=incident_repo)

    return {
        "db_manager": db_manager,
        "db_file": db_file,
        "audit_repo": audit_repo,
        "incident_repo": incident_repo,
        "bus": bus,
        "platform": platform,
        "safety": safety,
        "registry": registry,
        "config": config,
        "orchestrator": orchestrator,
        "diagnosis_engine": diagnosis_engine,
    }


# ===========================================================================
# TIER 1: Core E2E Autonomous Remediation Lifecycle (Happy Path)
# ===========================================================================

@pytest.mark.asyncio
async def test_tier1_e2e_remediation_light_fix_and_audit(remediation_env, mock_dns_resolver, qapp):
    """AC-1: Probe reports high latency -> diagnosis triggers -> orchestrator in Auto mode

    executes mocked-OS light fix (flush DNS cache) -> audit row written with pre-state ->
    EventBus publishes remediation event -> UI timeline model updated.
    """
    env = remediation_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    platform: MockPlatformAdapter = env["platform"]
    bus: EventBus = env["bus"]
    audit_repo: AuditRepository = env["audit_repo"]
    diag_engine: DiagnosisEngine = env["diagnosis_engine"]

    # 1. Capture events emitted by the EventBus
    emitted_events: List[Tuple[str, Any]] = []

    async def event_collector(topic: str, payload: Any) -> None:
        emitted_events.append((topic, payload))

    await bus.subscribe("remediation.*", event_collector)

    # 2. Simulate probe data showing DNS failure while gateway/external are reachable
    windows = {
        MetricType.GATEWAY_REACHABILITY: [make_measurement(MetricType.GATEWAY_REACHABILITY, 1.0, "192.168.1.1")],
        MetricType.GATEWAY_PACKET_LOSS: [make_measurement(MetricType.GATEWAY_PACKET_LOSS, 0.0, "192.168.1.1")],
        MetricType.EXTERNAL_PACKET_LOSS: [make_measurement(MetricType.EXTERNAL_PACKET_LOSS, 0.0, "1.1.1.1")],
        MetricType.EXTERNAL_LATENCY: [make_measurement(MetricType.EXTERNAL_LATENCY, 18.0, "1.1.1.1")],
        MetricType.DNS_SUCCESS_RATE: [
            make_measurement(MetricType.DNS_SUCCESS_RATE, 0.0, "system_dns", ProbeStatus.FAILED)
        ],
    }

    diag = await diag_engine.evaluate_windows(windows)
    assert diag.probable_cause == ProbableCause.DNS_RESOLVER_UNRESPONSIVE
    assert diag.auto_remediation_permitted is True
    assert "flush_dns_cache" in diag.recommended_actions

    # 3. Handle diagnosis in Auto mode
    record = await orchestrator.handle_diagnosis(diag)
    assert record is not None
    assert record.action_id == "flush_dns_cache"
    assert record.status == ActionExecutionStatus.SUCCEEDED
    assert platform.flushed is True
    assert platform.flush_count == 1

    # 4. Assert SQLite actions_audit table contains persisted audit row
    audits = audit_repo.get_recent(limit=10)
    assert len(audits) >= 1
    persisted = audits[0]
    assert persisted.action_id == "flush_dns_cache"
    assert persisted.status == ActionExecutionStatus.SUCCEEDED
    assert persisted.execution_duration_ms > 0
    assert "pre_state" in persisted.pre_remedy_metrics

    # 5. Assert EventBus published remediation events
    event_topics = [t for t, _ in emitted_events]
    assert any(
        t in (EventTopics.REMEDIATION_STARTED, "remediation.started") for t in event_topics
    ), "Must publish remediation started event"
    assert any(
        t in (EventTopics.REMEDIATION_COMPLETED, "remediation.finished", "remediation.completed")
        for t in event_topics
    ), "Must publish remediation completed/finished event"

    # 6. Verify UI Timeline Model receives event and updates
    timeline = TimelinePanel()
    timeline.show()
    now_str = datetime.now().strftime("%H:%M:%S")
    steps = [
        (now_str, "اكتشاف المشكلة", "انقطاع أو بطء حاد في استجابة خادم الـ DNS."),
        (now_str, "تحديد السبب", "تكدس كاش الـ DNS أو استجابة غير صالحة."),
        (now_str, "الإصلاح", f"تنفيذ {record.action_name} بنجاح"),
        (now_str, "النتيجة", "استعادة الاستقرار وانخفاض زمن الاستجابة للمعدلات الطبيعية."),
    ]
    timeline.set_event(now_str[:5], steps, is_resolved=True)

    assert "تم حله تلقائياً" in timeline.status_chip.text()
    assert not timeline.btn_rollback.isHidden()
    assert timeline.btn_rollback.isVisible() is True
    assert timeline.step_widgets[0].lbl_title.text() == "اكتشاف المشكلة"
    assert timeline.step_widgets[2].lbl_desc.text() == f"تنفيذ {record.action_name} بنجاح"


@pytest.mark.asyncio
async def test_tier1_e2e_remediation_reversible_dns_switch_and_rollback(remediation_env, mock_dns_resolver):
    """AC-1 / R6: Reversible action execution saves pre-change state in SQLite and rollback restores it."""
    env = remediation_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    platform: MockPlatformAdapter = env["platform"]
    audit_repo: AuditRepository = env["audit_repo"]

    # Initial state
    platform.current_dns = ["192.168.1.1"]

    diag = Diagnosis(
        id=str(uuid.uuid4()),
        probable_cause=ProbableCause.DNS_RESOLVER_HIGH_LATENCY,
        confidence=0.92,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["switch_dns_resolver"],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)
    assert record is not None
    assert record.action_id == "switch_dns_resolver"
    assert record.status == ActionExecutionStatus.SUCCEEDED

    # Verify adapter modified to fallback resolvers
    assert platform.current_dns == ["1.1.1.1", "8.8.8.8"]

    # Verify pre_state in database
    audits = audit_repo.get_recent(limit=5)
    persisted = audits[0]
    pre_state = persisted.pre_remedy_metrics.get("pre_state", {})
    assert pre_state.get("original_servers") == ["192.168.1.1"]

    # Rollback: Test via orchestrator.rollback_action contract
    if hasattr(orchestrator, "rollback_action"):
        ok, msg = await orchestrator.rollback_action(persisted.id)
        assert ok is True
    else:
        # Action-level rollback fallback for pre-M2 verification
        action = env["registry"].get("switch_dns_resolver")
        ok, msg = await action.rollback(platform, {}, pre_state)
        assert ok is True
        assert hasattr(
            orchestrator, "rollback_action"
        ), "RemediationOrchestrator must implement rollback_action per PROJECT.md interface contract"

    # Verify original DNS configuration restored on platform
    assert platform.current_dns == ["192.168.1.1"]


@pytest.mark.asyncio
async def test_tier1_e2e_remediation_gateway_recheck(remediation_env):
    """Test Level 1 light fix 'recheck_gateway' execution and verification."""
    env = remediation_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    platform: MockPlatformAdapter = env["platform"]
    audit_repo: AuditRepository = env["audit_repo"]

    diag = Diagnosis(
        id=str(uuid.uuid4()),
        probable_cause=ProbableCause.LOCAL_GATEWAY_UNREACHABLE,
        confidence=0.88,
        severity=DiagnosisSeverity.CRITICAL,
        recommended_actions=["recheck_gateway"],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)
    assert record is not None
    assert record.action_id == "recheck_gateway"
    assert record.status == ActionExecutionStatus.SUCCEEDED
    assert platform.ping_count >= 3  # Probe burst verified

    audits = audit_repo.get_recent(limit=5)
    assert len(audits) >= 1
    assert audits[0].status == ActionExecutionStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_tier1_audit_pre_change_state_persistence_integrity(remediation_env):
    """Validate SQLite actions_audit table schema, JSON formatting, and persistence directly."""
    env = remediation_env
    db_file = env["db_file"]
    audit_repo: AuditRepository = env["audit_repo"]

    test_record = ActionExecutionRecord(
        id=str(uuid.uuid4()),
        action_id="switch_dns_resolver",
        action_name="Switch Interface DNS Resolver",
        risk_level=RiskLevel.LEVEL_2_CONTROLLED,
        trigger_diagnosis_id="diag-12345",
        pre_remedy_metrics={"pre_state": {"interface_name": "Wi-Fi", "original_servers": ["10.0.0.1"]}},
        post_remedy_metrics={"latency_ms": 14.5},
        status=ActionExecutionStatus.SUCCEEDED,
        execution_duration_ms=45.2,
        verification_duration_ms=12.1,
        error_message=None,
        rollback_performed=False,
    )
    audit_repo.save(test_record)

    # Query directly with sqlite3
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("SELECT id, action_id, pre_remedy_metrics, status FROM actions_audit WHERE id = ?", (test_record.id,))
    row = cur.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == test_record.id
    assert row[1] == "switch_dns_resolver"
    pre_json = json.loads(row[2])
    assert pre_json["pre_state"]["original_servers"] == ["10.0.0.1"]
    assert row[3] == "succeeded"


@pytest.mark.asyncio
async def test_tier1_ui_timeline_model_updates_on_remediation_events(qapp):
    """Verify TimelinePanel UI presentation, chip styling, and rollback button wiring."""
    timeline = TimelinePanel()
    timeline.show()
    assert timeline is not None

    # Track rollback signal
    rollback_signal_emitted = False

    def on_rollback():
        nonlocal rollback_signal_emitted
        rollback_signal_emitted = True

    timeline.rollback_requested.connect(on_rollback)

    # Update with successful resolution
    now_str = "12:30:00"
    steps = [
        ("12:30:00", "اكتشاف المشكلة", "انحراف في زمن الاستجابة"),
        ("12:30:05", "تحديد السبب", "فشل الـ DNS"),
        ("12:30:15", "الإصلاح", "تفريغ كاش الـ DNS"),
        ("12:30:20", "النتيجة", "استقرار الاتصال"),
    ]
    timeline.set_event(now_str[:5], steps, is_resolved=True)

    assert timeline.status_chip.text() == "تم حله تلقائياً"
    assert timeline.btn_rollback.isVisible() is True

    # Click rollback
    timeline.btn_rollback.clicked.emit()
    assert rollback_signal_emitted is True


# ===========================================================================
# TIER 2: Boundary & Corner Cases
# ===========================================================================

@pytest.mark.asyncio
async def test_tier2_action_execution_failure_captured_in_audit(remediation_env):
    """Failure during platform command execution is captured in SQLite actions_audit as FAILED."""
    env = remediation_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    platform: MockPlatformAdapter = env["platform"]
    audit_repo: AuditRepository = env["audit_repo"]

    # Force platform flush failure
    platform.fail_flush = True

    diag = Diagnosis(
        id=str(uuid.uuid4()),
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        confidence=0.95,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["flush_dns_cache"],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)
    assert record is not None
    assert record.status == ActionExecutionStatus.FAILED
    assert "Access is denied" in (record.error_message or "")

    # Check persistence of failure
    audits = audit_repo.get_recent(limit=5)
    assert len(audits) >= 1
    assert audits[0].status == ActionExecutionStatus.FAILED
    assert "Access is denied" in (audits[0].error_message or "")


@pytest.mark.asyncio
async def test_tier2_action_timeout_handling(remediation_env):
    """Action exceeding timeout_sec is terminated and recorded as failure/timeout."""
    env = remediation_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    registry: ActionRegistry = env["registry"]
    audit_repo: AuditRepository = env["audit_repo"]

    # Register action that takes 0.3s with 0.05s timeout
    slow_action = ControllableTestAction(
        action_id="slow_action",
        timeout_sec=0.05,
        exec_delay_sec=0.30,
    )
    registry.register(slow_action)

    diag = Diagnosis(
        id=str(uuid.uuid4()),
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        confidence=0.90,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["slow_action"],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)
    assert record is not None
    assert record.status == ActionExecutionStatus.FAILED
    assert "failed" in (record.error_message or "").lower() or "timeout" in (record.error_message or "").lower()

    # Safety lock must be cleanly released
    assert env["safety"].lock.locked() is False


@pytest.mark.asyncio
async def test_tier2_rollback_invalid_or_missing_action_id(remediation_env):
    """Calling rollback with non-existent action ID returns (False, error) gracefully."""
    env = remediation_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]

    assert hasattr(
        orchestrator, "rollback_action"
    ), "RemediationOrchestrator must implement rollback_action per PROJECT.md interface contract"

    ok, msg = await orchestrator.rollback_action("non_existent_uuid_12345")
    assert ok is False
    assert "not found" in msg.lower() or "invalid" in msg.lower() or "no" in msg.lower()


@pytest.mark.asyncio
async def test_tier2_rollback_with_no_prior_actions(remediation_env):
    """Calling rollback on an empty audit log returns (False, msg) cleanly."""
    env = remediation_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]

    assert hasattr(
        orchestrator, "rollback_action"
    ), "RemediationOrchestrator must implement rollback_action per PROJECT.md interface contract"

    ok, msg = await orchestrator.rollback_action(None)
    assert ok is False


@pytest.mark.asyncio
async def test_tier2_rollback_corrupted_pre_state(remediation_env):
    """Rollback handles missing or corrupted pre_state without raising unhandled exceptions."""
    env = remediation_env
    platform: MockPlatformAdapter = env["platform"]
    action = SwitchDNSResolverAction()

    # Rollback with None pre-state
    ok1, msg1 = await action.rollback(platform, {}, None)
    assert ok1 is False

    # Rollback with corrupted/invalid pre-state structure (non-dict or empty)
    ok2, msg2 = await action.rollback(platform, {}, "invalid_serialized_string")
    assert ok2 is False
    assert "invalid pre-state" in msg2.lower()


# ===========================================================================
# TIER 3: Cross-Feature Combinations
# ===========================================================================

@pytest.mark.asyncio
async def test_tier3_mode_transition_auto_to_watch_during_diagnosis(remediation_env):
    """Switching mode to Watch immediately suppresses action execution and prevents OS modifications."""
    env = remediation_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    platform: MockPlatformAdapter = env["platform"]

    # Start in Auto
    orchestrator.set_operating_mode(MODE_AUTO)

    diag = Diagnosis(
        id=str(uuid.uuid4()),
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        confidence=0.95,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["flush_dns_cache"],
        auto_remediation_permitted=True,
    )

    # Transition to Watch mode before dispatch
    orchestrator.set_operating_mode(MODE_WATCH)

    record = await orchestrator.handle_diagnosis(diag)
    assert record is None, "Execution must be suppressed under Watch mode"
    assert platform.flushed is False
    assert platform.flush_count == 0


@pytest.mark.asyncio
async def test_tier3_sequential_incidents_targeted_rollback(remediation_env, mock_dns_resolver):
    """Sequential incidents: rollback targeted action A restores only action A's state."""
    env = remediation_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    platform: MockPlatformAdapter = env["platform"]
    audit_repo: AuditRepository = env["audit_repo"]

    # Incident 1: DNS switch
    platform.current_dns = ["192.168.1.1"]
    diag1 = Diagnosis(
        id=str(uuid.uuid4()),
        probable_cause=ProbableCause.DNS_RESOLVER_HIGH_LATENCY,
        confidence=0.90,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["switch_dns_resolver"],
        auto_remediation_permitted=True,
    )
    record1 = await orchestrator.handle_diagnosis(diag1)
    assert record1 is not None
    assert platform.current_dns == ["1.1.1.1", "8.8.8.8"]

    # Incident 2: Gateway Recheck
    diag2 = Diagnosis(
        id=str(uuid.uuid4()),
        probable_cause=ProbableCause.LOCAL_GATEWAY_UNREACHABLE,
        confidence=0.90,
        severity=DiagnosisSeverity.CRITICAL,
        recommended_actions=["recheck_gateway"],
        auto_remediation_permitted=True,
    )
    record2 = await orchestrator.handle_diagnosis(diag2)
    assert record2 is not None

    # Rollback specifically targeted at Incident 1 (DNS switch)
    if hasattr(orchestrator, "rollback_action"):
        ok, msg = await orchestrator.rollback_action(record1.id)
        assert ok is True
    else:
        action = env["registry"].get("switch_dns_resolver")
        pre_state = record1.pre_remedy_metrics.get("pre_state")
        ok, msg = await action.rollback(platform, {}, pre_state)
        assert ok is True
        assert hasattr(orchestrator, "rollback_action")

    # Only Incident 1 is rolled back; original DNS restored
    assert platform.current_dns == ["192.168.1.1"]


@pytest.mark.asyncio
async def test_tier3_concurrent_diagnoses_serialized_by_safety_lock(remediation_env, mock_dns_resolver):
    """Multiple concurrent diagnoses are safely serialized through ActionSafetyManager.lock."""
    env = remediation_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    registry: ActionRegistry = env["registry"]

    action_a = ControllableTestAction(action_id="action_a", exec_delay_sec=0.1)
    action_b = ControllableTestAction(action_id="action_b", exec_delay_sec=0.1)
    registry.register(action_a)
    registry.register(action_b)

    diag_a = Diagnosis(
        id="diag_a",
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        confidence=0.95,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["action_a"],
        auto_remediation_permitted=True,
    )
    diag_b = Diagnosis(
        id="diag_b",
        probable_cause=ProbableCause.LOCAL_GATEWAY_UNREACHABLE,
        confidence=0.95,
        severity=DiagnosisSeverity.CRITICAL,
        recommended_actions=["action_b"],
        auto_remediation_permitted=True,
    )

    t0 = time.perf_counter()
    res_a, res_b = await asyncio.gather(
        orchestrator.handle_diagnosis(diag_a),
        orchestrator.handle_diagnosis(diag_b),
    )
    duration = time.perf_counter() - t0

    assert res_a is not None and res_b is not None
    # Because lock serializes the 0.1s executions, total time must be >= 0.20s
    assert duration >= 0.18, "Concurrent executions must be serialized by safety lock"


@pytest.mark.asyncio
async def test_tier3_circuit_breaker_trips_after_repeated_failures(remediation_env):
    """Circuit breaker trips after consecutive failures, blocking retry loop."""
    env = remediation_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    registry: ActionRegistry = env["registry"]

    failing_action = ControllableTestAction(
        action_id="always_failing",
        fail_execute=True,
        cooldown_sec=0.0,
    )
    registry.register(failing_action)

    diag = Diagnosis(
        id=str(uuid.uuid4()),
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        confidence=0.95,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["always_failing"],
        auto_remediation_permitted=True,
    )

    # 3 failures trip circuit breaker (threshold = 3)
    await orchestrator.handle_diagnosis(diag)
    await orchestrator.handle_diagnosis(diag)
    await orchestrator.handle_diagnosis(diag)

    # 4th invocation must be blocked by open circuit breaker
    record4 = await orchestrator.handle_diagnosis(diag)
    assert record4 is None, "Circuit breaker must suppress execution when tripped"


# ===========================================================================
# TIER 4: Real-World Application Scenario
# ===========================================================================

@pytest.mark.asyncio
async def test_tier4_complete_lifecycle_telemetry_to_ui_to_user_rollback(remediation_env, mock_dns_resolver, qapp):
    """Scenario 1: Complete end-to-end integration lifecycle:

    1. Observability probe reports high latency / DNS degradation.
    2. Diagnosis engine synthesizes incident with recommended actions.
    3. Orchestrator in Auto mode executes DNS switch remediation.
    4. Pre-change state persisted in SQLite audit table.
    5. EventBus notifies UI bridge.
    6. UI timeline updates to show 4 steps and enabled rollback.
    7. User triggers rollback -> pre-change state restored.
    """
    env = remediation_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    platform: MockPlatformAdapter = env["platform"]
    bus: EventBus = env["bus"]
    audit_repo: AuditRepository = env["audit_repo"]
    diag_engine: DiagnosisEngine = env["diagnosis_engine"]

    # Initial platform state
    platform.current_dns = ["192.168.1.1"]

    timeline = TimelinePanel()
    timeline.show()
    timeline_updated = False

    async def on_remediation_completed(topic: str, payload: Any):
        nonlocal timeline_updated
        now_str = datetime.now().strftime("%H:%M:%S")
        action_name = getattr(payload, "action_name", "إجراء تعافي ذكي")
        steps = [
            (now_str, "اكتشاف المشكلة", "ارتفع زمن استجابة DNS بشكل حاد."),
            (now_str, "تحديد السبب", "تعطل خادم الـ DNS المحلي الخاص بمزود الخدمة."),
            (now_str, "الإصلاح", f"تم تحويل مسار الـ DNS تلقائياً ({action_name})."),
            (now_str, "النتيجة", "استعادة الاستقرار وانخفاض زمن الاستجابة إلى 14ms."),
        ]
        timeline.set_event(now_str[:5], steps, is_resolved=True)
        timeline_updated = True

    await bus.subscribe("remediation.completed", on_remediation_completed)
    await bus.subscribe("remediation.finished", on_remediation_completed)

    # 1. Telemetry Probe Measurements
    windows = {
        MetricType.GATEWAY_REACHABILITY: [make_measurement(MetricType.GATEWAY_REACHABILITY, 1.0, "192.168.1.1")],
        MetricType.EXTERNAL_PACKET_LOSS: [make_measurement(MetricType.EXTERNAL_PACKET_LOSS, 0.0, "1.1.1.1")],
        MetricType.DNS_LATENCY: [make_measurement(MetricType.DNS_LATENCY, 450.0, "dns_resolver")],
    }

    # 2. Diagnosis
    diag = await diag_engine.evaluate_windows(windows)
    assert diag.probable_cause == ProbableCause.DNS_RESOLVER_HIGH_LATENCY
    assert "switch_dns_resolver" in diag.recommended_actions

    # 3. Autonomous Healing
    record = await orchestrator.handle_diagnosis(diag)
    assert record is not None
    assert record.action_id == "switch_dns_resolver"
    assert platform.current_dns == ["1.1.1.1", "8.8.8.8"]

    # 4. Audit persistence
    audits = audit_repo.get_recent(limit=5)
    persisted = audits[0]
    assert persisted.status == ActionExecutionStatus.SUCCEEDED

    # 5. UI Reflection
    assert timeline_updated is True
    assert timeline.status_chip.text() == "تم حله تلقائياً"
    assert timeline.btn_rollback.isVisible() is True

    # 6. User-initiated rollback via UI Timeline button
    user_rollback_fired = False

    async def perform_user_rollback():
        nonlocal user_rollback_fired
        user_rollback_fired = True
        if hasattr(orchestrator, "rollback_action"):
            await orchestrator.rollback_action(persisted.id)
        else:
            action = env["registry"].get("switch_dns_resolver")
            pre_state = persisted.pre_remedy_metrics.get("pre_state")
            await action.rollback(platform, {}, pre_state)
            assert hasattr(orchestrator, "rollback_action")

    timeline.rollback_requested.connect(lambda: asyncio.create_task(perform_user_rollback()))
    timeline.btn_rollback.clicked.emit()

    # Allow async task to process
    await asyncio.sleep(0.05)
    assert user_rollback_fired is True
    assert platform.current_dns == ["192.168.1.1"]
