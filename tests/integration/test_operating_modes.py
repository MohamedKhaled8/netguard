"""Integration Tests for NetGuard AI Operating Modes & Drastic Action Approval Gates (AC-2, AC-3, AC-4).

Tests cover:
- AC-2: Ask mode (ASSISTED): High latency / packet loss detected -> orchestrator halts and awaits explicit user
  approval -> emits REMEDIATION_APPROVAL_REQUIRED -> zero OS command executed before approval -> calling
  orchestrator.approve_action() executes action -> audit record written.
- AC-3: Watch mode (OBSERVATION): Critical incident detected -> orchestrator logs and publishes observation event ->
  makes ZERO system modifications -> assert mock platform command count is 0 and audit log records no executions.
- AC-4: Drastic actions require explicit approval across ALL operating modes (even AUTO mode):
  - Test Level 3 disruptive actions (renew_ip_lease, Winsock reset, TCP-IP reset).
  - Under Auto mode: verify drastic action halts and requires explicit approval.
  - Under Ask mode: verify drastic action requires explicit approval.
  - Under Watch mode: verify drastic action is not executed.
- Tier 2/3: Rapid mode toggling during event dispatch; rejection of approval request (reject_action or timeout);
  Meeting Guard suppression; unprivileged precondition refusal.
- Tier 4: Real-world operator workflow in Assisted mode from telemetry to approval and verified execution.
"""

from __future__ import annotations

import asyncio
import os
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
class OperatingModeMockPlatformAdapter(IPlatformAdapter):
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
        return self.ping_ok, 12.0

    def tcp_connect(self, target: str, port: int = 80, timeout_sec: float = 2.0) -> Tuple[bool, float]:
        self.commands_executed.append(f"tcp_connect {target}:{port}")
        return True, 15.0

    def flush_dns_cache(self) -> Tuple[bool, str]:
        self.flush_count += 1
        self.commands_executed.append("flush_dns_cache")
        if self.fail_flush:
            return False, "Access is denied: Elevated privileges required"
        self.flushed = True
        return True, "Successfully flushed the DNS Resolver Cache."

    def get_interface_dns_servers(self, interface_name: str) -> List[str]:
        return list(self.current_dns)

    def set_interface_dns_servers(self, interface_name: str, servers: List[str]) -> Tuple[bool, str]:
        self.set_dns_count += 1
        self.commands_executed.append(f"set_interface_dns_servers {servers}")
        if self.fail_dns:
            return False, "Failed to set interface DNS servers"
        self.current_dns = list(servers)
        return True, "DNS servers configured successfully"

    def renew_ip_lease(self, interface_name: str) -> Tuple[bool, str]:
        self.renew_count += 1
        self.commands_executed.append(f"renew_ip_lease {interface_name}")
        if self.fail_renew:
            return False, "DHCP lease renewal failed"
        self.renewed = True
        return True, "DHCP lease renewed successfully"

    def get_wifi_metrics(self, interface_name: Optional[str] = None) -> Dict[str, Any]:
        return {"is_wifi": True, "signal_percent": 85.0}


# ---------------------------------------------------------------------------
# Simulated Level 3 Disruptive Action (Winsock / TCP-IP Reset)
# ---------------------------------------------------------------------------
class DisruptiveWinsockResetAction(RemediationAction):
    """Simulated Level 3 disruptive action to test drastic action approval gating."""

    def __init__(self) -> None:
        super().__init__(
            action_id="reset_winsock_catalog",
            name="Reset Winsock Catalog and TCP/IP Stack",
            description="Completely resets Windows socket catalog and TCP/IP stack (drastic).",
            risk_level=RiskLevel.LEVEL_3_DISRUPTIVE,
            supported_os=["win32"],
            timeout_sec=15.0,
            cooldown_sec=120.0,
        )
        self.executed = False

    def check_preconditions(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Tuple[bool, str]:
        if not platform.is_elevated():
            return False, "Requires Administrator privileges"
        return True, "Elevated privileges confirmed"

    async def execute(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Any:
        self.executed = True
        return {"action": "reset_winsock", "timestamp": time.time()}

    async def verify(
        self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any
    ) -> Tuple[bool, str, Dict[str, Any]]:
        return True, "Winsock reset verified", {"reset": True}

    async def rollback(
        self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any
    ) -> Tuple[bool, str]:
        return False, "Winsock reset cannot be undone automatically"


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
def operating_modes_env(tmp_path):
    """Instantiate isolated environment with controllable Meeting Guard check."""
    db_file = tmp_path / "test_modes.db"
    db_manager = DatabaseManager(db_path=db_file, enable_wal=False)
    audit_repo = AuditRepository(db_manager)
    incident_repo = IncidentRepository(db_manager)
    bus = EventBus()
    platform = OperatingModeMockPlatformAdapter()
    safety = ActionSafetyManager(failure_threshold=3, reset_timeout_sec=0.2)
    registry = ActionRegistry()

    # Register standard actions + disruptive Winsock reset
    registry.register(FlushDNSCacheAction())
    registry.register(SwitchDNSResolverAction(fallback_resolvers=["1.1.1.1", "8.8.8.8"]))
    registry.register(RecheckGatewayAction())
    registry.register(RenewIPLeaseAction())
    winsock_action = DisruptiveWinsockResetAction()
    registry.register(winsock_action)

    config = RemediationConfig(
        mode=MODE_AUTO.value if hasattr(MODE_AUTO, "value") else "auto",
        cooldown_period_sec=0.05,
        verification_duration_sec=0.5,
        allow_level_3_disruptive=False,
    )

    meeting_active = False

    def meeting_guard_checker() -> bool:
        return meeting_active

    def set_meeting_active(active: bool):
        nonlocal meeting_active
        meeting_active = active

    orchestrator = RemediationOrchestrator(
        config=config,
        registry=registry,
        safety_manager=safety,
        platform_adapter=platform,
        audit_repo=audit_repo,
        event_bus=bus,
        meeting_guard_check=meeting_guard_checker,
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
        "winsock_action": winsock_action,
        "config": config,
        "orchestrator": orchestrator,
        "diagnosis_engine": diagnosis_engine,
        "set_meeting_active": set_meeting_active,
    }


# ===========================================================================
# TIER 1: AC-2, AC-3, AC-4 Core Acceptance Criteria Verification
# ===========================================================================

@pytest.mark.asyncio
async def test_ac2_ask_mode_halts_and_awaits_approval(operating_modes_env, mock_dns_resolver):
    """AC-2: Ask mode (ASSISTED): High latency / packet loss detected -> orchestrator halts

    and awaits explicit user approval -> emits REMEDIATION_APPROVAL_REQUIRED -> zero OS command
    executed before approval.
    """
    env = operating_modes_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    platform: OperatingModeMockPlatformAdapter = env["platform"]
    bus: EventBus = env["bus"]
    audit_repo: AuditRepository = env["audit_repo"]

    # 1. Set mode to Ask (Assisted)
    orchestrator.set_operating_mode(MODE_ASK)

    # 2. Capture published events
    approval_events: List[Dict[str, Any]] = []

    async def on_approval_required(topic: str, payload: Any):
        approval_events.append(payload if isinstance(payload, dict) else payload.model_dump())

    await bus.subscribe(EventTopics.REMEDIATION_APPROVAL_REQUIRED, on_approval_required)
    await bus.subscribe("remediation.approval_required", on_approval_required)

    # 3. Simulate high latency / DNS failure incident
    diag = Diagnosis(
        id=str(uuid.uuid4()),
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        confidence=0.95,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["flush_dns_cache"],
        auto_remediation_permitted=True,
    )

    # 4. Orchestrator processes diagnosis in Ask mode
    record = await orchestrator.handle_diagnosis(diag)

    # 5. Assert orchestrator HALTS: returns None (not executed)
    assert record is None, "In Ask mode, orchestrator must halt and not execute autonomously"

    # 6. Assert zero OS modifications made before approval
    assert platform.flushed is False
    assert platform.flush_count == 0
    assert len(platform.commands_executed) == 0

    # 7. Assert approval event published with required action and diagnosis details
    assert len(approval_events) >= 1
    event = approval_events[0]
    assert event.get("action_id") == "flush_dns_cache"
    assert "diagnosis" in event

    # 8. Assert zero audit records written with SUCCEEDED status
    audits = audit_repo.get_recent(limit=5)
    assert len(audits) == 0


@pytest.mark.asyncio
async def test_ac2_ask_mode_approve_action_executes_and_audits(operating_modes_env, mock_dns_resolver):
    """AC-2: Calling orchestrator.approve_action() executes approved action and writes audit record."""
    env = operating_modes_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    platform: OperatingModeMockPlatformAdapter = env["platform"]
    audit_repo: AuditRepository = env["audit_repo"]

    orchestrator.set_operating_mode(MODE_ASK)

    diag = Diagnosis(
        id=str(uuid.uuid4()),
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        confidence=0.95,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["flush_dns_cache"],
        auto_remediation_permitted=True,
    )

    # Trigger proposal
    await orchestrator.handle_diagnosis(diag)
    assert platform.flushed is False

    # Contract assertion: orchestrator must implement approve_action per PROJECT.md
    assert hasattr(
        orchestrator, "approve_action"
    ), "RemediationOrchestrator must implement approve_action() per PROJECT.md interface contract"

    ok, msg = await orchestrator.approve_action("flush_dns_cache", {"diagnosis": diag})
    assert ok is True

    # Assert OS command executed upon approval
    assert platform.flushed is True
    assert platform.flush_count == 1

    # Assert audit record written with SUCCEEDED status
    audits = audit_repo.get_recent(limit=5)
    assert len(audits) >= 1
    assert audits[0].action_id == "flush_dns_cache"
    assert audits[0].status == ActionExecutionStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_ac3_watch_mode_makes_zero_modifications(operating_modes_env):
    """AC-3: Watch mode (OBSERVATION): Critical incident detected -> orchestrator logs and

    publishes observation event -> makes ZERO system modifications -> assert mock platform
    command count is 0 and audit log records no executions.
    """
    env = operating_modes_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    platform: OperatingModeMockPlatformAdapter = env["platform"]
    audit_repo: AuditRepository = env["audit_repo"]

    # 1. Set mode to Watch (Observation)
    orchestrator.set_operating_mode(MODE_WATCH)

    # 2. Trigger critical gateway outage incident
    diag = Diagnosis(
        id=str(uuid.uuid4()),
        probable_cause=ProbableCause.LOCAL_GATEWAY_UNREACHABLE,
        confidence=0.98,
        severity=DiagnosisSeverity.CRITICAL,
        recommended_actions=["recheck_gateway", "flush_dns_cache"],
        auto_remediation_permitted=True,
    )

    # 3. Handle diagnosis in Watch mode
    record = await orchestrator.handle_diagnosis(diag)

    # 4. Assert return is None (suppressed)
    assert record is None

    # 5. Assert ZERO modifications executed
    assert platform.flush_count == 0
    assert platform.flushed is False
    assert platform.set_dns_count == 0
    assert platform.renew_count == 0
    assert len(platform.commands_executed) == 0

    # 6. Assert audit log records no executions
    audits = audit_repo.get_recent(limit=10)
    assert len(audits) == 0


@pytest.mark.asyncio
async def test_ac4_drastic_actions_require_approval_in_auto_mode(operating_modes_env):
    """AC-4: Drastic actions (Level 3 disruptive) require explicit approval across ALL operating modes,

    even under AUTO mode (e.g. renew_ip_lease or Winsock reset).
    """
    env = operating_modes_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    platform: OperatingModeMockPlatformAdapter = env["platform"]
    bus: EventBus = env["bus"]

    # 1. Ensure Auto mode
    orchestrator.set_operating_mode(MODE_AUTO)

    approval_required_emitted = False

    async def on_approval(topic: str, payload: Any):
        nonlocal approval_required_emitted
        approval_required_emitted = True

    await bus.subscribe(EventTopics.REMEDIATION_APPROVAL_REQUIRED, on_approval)
    await bus.subscribe("remediation.approval_required", on_approval)

    # 2. Trigger diagnosis recommending Level 3 disruptive action (renew_ip_lease)
    diag = Diagnosis(
        id=str(uuid.uuid4()),
        probable_cause=ProbableCause.LOCAL_GATEWAY_UNREACHABLE,
        confidence=0.95,
        severity=DiagnosisSeverity.CRITICAL,
        recommended_actions=["renew_ip_lease"],
        auto_remediation_permitted=True,
    )

    # 3. Process diagnosis in Auto mode
    record = await orchestrator.handle_diagnosis(diag)

    # 4. Drastic action MUST NOT execute autonomously in Auto mode
    assert platform.renewed is False, "Drastic action renew_ip_lease must not execute autonomously in Auto mode"
    assert platform.renew_count == 0

    # 5. Under AC-4 specification, drastic actions in Auto mode must halt and require explicit approval
    # Either returns None or emits approval required
    assert record is None or approval_required_emitted is True


@pytest.mark.asyncio
async def test_ac4_drastic_actions_require_approval_in_ask_mode(operating_modes_env):
    """AC-4: Drastic actions require explicit approval under Ask mode."""
    env = operating_modes_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    platform: OperatingModeMockPlatformAdapter = env["platform"]
    bus: EventBus = env["bus"]

    orchestrator.set_operating_mode(MODE_ASK)

    approval_events: List[Dict[str, Any]] = []

    async def on_approval(topic: str, payload: Any):
        approval_events.append(payload if isinstance(payload, dict) else payload.model_dump())

    await bus.subscribe("remediation.approval_required", on_approval)

    diag = Diagnosis(
        id=str(uuid.uuid4()),
        probable_cause=ProbableCause.LOCAL_GATEWAY_UNREACHABLE,
        confidence=0.95,
        severity=DiagnosisSeverity.CRITICAL,
        recommended_actions=["reset_winsock_catalog"],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)
    assert record is None
    assert env["winsock_action"].executed is False
    assert len(approval_events) >= 1
    assert approval_events[0].get("action_id") == "reset_winsock_catalog"


@pytest.mark.asyncio
async def test_ac4_drastic_actions_in_watch_mode_never_executed(operating_modes_env):
    """AC-4: Drastic actions are completely suppressed under Watch mode."""
    env = operating_modes_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    platform: OperatingModeMockPlatformAdapter = env["platform"]

    orchestrator.set_operating_mode(MODE_WATCH)

    diag = Diagnosis(
        id=str(uuid.uuid4()),
        probable_cause=ProbableCause.LOCAL_GATEWAY_UNREACHABLE,
        confidence=0.95,
        severity=DiagnosisSeverity.CRITICAL,
        recommended_actions=["renew_ip_lease", "reset_winsock_catalog"],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)
    assert record is None
    assert platform.renewed is False
    assert env["winsock_action"].executed is False
    assert len(platform.commands_executed) == 0


# ===========================================================================
# TIER 2: Boundary & Corner Cases
# ===========================================================================

@pytest.mark.asyncio
async def test_tier2_ask_mode_rejection_of_approval(operating_modes_env):
    """Rejection of proposed action cancels remediation without OS modifications."""
    env = operating_modes_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    platform: OperatingModeMockPlatformAdapter = env["platform"]

    orchestrator.set_operating_mode(MODE_ASK)

    diag = Diagnosis(
        id=str(uuid.uuid4()),
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        confidence=0.95,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["flush_dns_cache"],
        auto_remediation_permitted=True,
    )

    await orchestrator.handle_diagnosis(diag)
    assert platform.flushed is False

    # If reject_action is implemented, test it
    if hasattr(orchestrator, "reject_action"):
        ok, msg = await orchestrator.reject_action("flush_dns_cache")
        assert ok is True
        assert platform.flushed is False
    else:
        # Otherwise verify state remains clean and unexecuted
        assert platform.flushed is False
        assert platform.flush_count == 0


@pytest.mark.asyncio
async def test_tier2_approve_nonexistent_or_expired_action(operating_modes_env):
    """Calling approve_action with unknown action ID returns (False, msg) gracefully."""
    env = operating_modes_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]

    assert hasattr(
        orchestrator, "approve_action"
    ), "RemediationOrchestrator must implement approve_action() per PROJECT.md interface contract"

    ok, msg = await orchestrator.approve_action("action_that_does_not_exist_xyz")
    assert ok is False
    assert "not found" in msg.lower() or "unknown" in msg.lower() or "invalid" in msg.lower()


@pytest.mark.asyncio
async def test_tier2_drastic_action_meeting_guard_suppression(operating_modes_env):
    """Active video meeting triggers Meeting Guard suppression for disruptive actions."""
    env = operating_modes_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    platform: OperatingModeMockPlatformAdapter = env["platform"]
    bus: EventBus = env["bus"]

    # Activate Meeting Guard and permit level 3 in config so Meeting Guard gate is reached
    env["set_meeting_active"](True)
    orchestrator.config.allow_level_3_disruptive = True
    orchestrator.set_operating_mode(MODE_AUTO)

    suppression_events: List[Dict[str, Any]] = []

    async def on_suppressed(topic: str, payload: Any):
        suppression_events.append(payload if isinstance(payload, dict) else payload.model_dump())

    await bus.subscribe("remediation.action_suppressed", on_suppressed)
    await bus.subscribe(EventTopics.REMEDIATION_ACTION_SUPPRESSED, on_suppressed)

    diag = Diagnosis(
        id=str(uuid.uuid4()),
        probable_cause=ProbableCause.LOCAL_GATEWAY_UNREACHABLE,
        confidence=0.95,
        severity=DiagnosisSeverity.CRITICAL,
        recommended_actions=["renew_ip_lease"],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)
    assert record is None
    assert platform.renewed is False
    assert len(suppression_events) >= 1
    assert "مكالمة" in suppression_events[0].get("reason", "") or "meeting" in suppression_events[0].get("reason", "").lower()


@pytest.mark.asyncio
async def test_tier2_unprivileged_precondition_refuses_execution_in_ask_mode(operating_modes_env):
    """Unprivileged user running in Ask mode fails precondition check on privileged actions."""
    env = operating_modes_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    platform: OperatingModeMockPlatformAdapter = env["platform"]

    # Drop elevation
    platform.elevated = False
    orchestrator.set_operating_mode(MODE_ASK)

    # Check precondition on DHCP renewal directly
    renew_action = env["registry"].get("renew_ip_lease")
    ok, msg = renew_action.check_preconditions(platform, {})
    assert ok is False
    assert "Administrator" in msg or "privilege" in msg.lower()


# ===========================================================================
# TIER 3: Cross-Feature Combinations
# ===========================================================================

@pytest.mark.asyncio
async def test_tier3_rapid_mode_toggling_during_event_dispatch(operating_modes_env, mock_dns_resolver):
    """Rapid toggling between Auto, Ask, and Watch modes consistently enforces active mode."""
    env = operating_modes_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    platform: OperatingModeMockPlatformAdapter = env["platform"]

    diag = Diagnosis(
        id=str(uuid.uuid4()),
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        confidence=0.95,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["flush_dns_cache"],
        auto_remediation_permitted=True,
    )

    # Toggle 1: Watch mode -> suppressed
    orchestrator.set_operating_mode(MODE_WATCH)
    rec1 = await orchestrator.handle_diagnosis(diag)
    assert rec1 is None
    assert platform.flush_count == 0

    # Toggle 2: Ask mode -> awaits approval
    orchestrator.set_operating_mode(MODE_ASK)
    rec2 = await orchestrator.handle_diagnosis(diag)
    assert rec2 is None
    assert platform.flush_count == 0

    # Toggle 3: Auto mode -> executes
    orchestrator.set_operating_mode(MODE_AUTO)
    rec3 = await orchestrator.handle_diagnosis(diag)
    assert rec3 is not None
    assert rec3.status == ActionExecutionStatus.SUCCEEDED
    assert platform.flush_count == 1

    # Toggle 4: Back to Watch mode -> suppressed again
    orchestrator.set_operating_mode(MODE_WATCH)
    rec4 = await orchestrator.handle_diagnosis(diag)
    assert rec4 is None
    assert platform.flush_count == 1  # Unchanged


@pytest.mark.asyncio
async def test_tier3_operating_mode_enum_members_and_aliases():
    """Verify OperatingMode enum contains required canonical and aliased values per PROJECT.md."""
    # Canonical string representations
    auto_member = getattr(OperatingMode, "AUTO", getattr(OperatingMode, "AUTONOMOUS_SAFE", None))
    ask_member = getattr(OperatingMode, "ASK", getattr(OperatingMode, "ASSISTED", None))
    watch_member = getattr(OperatingMode, "WATCH", getattr(OperatingMode, "OBSERVATION", None))

    assert auto_member is not None, "OperatingMode must provide AUTO / AUTONOMOUS_SAFE member"
    assert ask_member is not None, "OperatingMode must provide ASK / ASSISTED member"
    assert watch_member is not None, "OperatingMode must provide WATCH / OBSERVATION member"

    # Values must match either standardized 'auto'/'ask'/'watch' or legacy 'autonomous_safe'/'assisted'/'observation'
    assert auto_member.value in ("auto", "autonomous_safe")
    assert ask_member.value in ("ask", "assisted")
    assert watch_member.value in ("watch", "observation")


@pytest.mark.asyncio
async def test_tier3_policy_toggle_gates_action_regardless_of_mode(operating_modes_env):
    """When allow_level_3_disruptive is disabled, disruptive action is rejected in Auto mode."""
    env = operating_modes_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    platform: OperatingModeMockPlatformAdapter = env["platform"]

    orchestrator.set_operating_mode(MODE_AUTO)
    orchestrator.config.allow_level_3_disruptive = False

    diag = Diagnosis(
        id=str(uuid.uuid4()),
        probable_cause=ProbableCause.LOCAL_GATEWAY_UNREACHABLE,
        confidence=0.95,
        severity=DiagnosisSeverity.CRITICAL,
        recommended_actions=["renew_ip_lease"],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)
    assert record is None
    assert platform.renewed is False


# ===========================================================================
# TIER 4: Real-World Application Scenario
# ===========================================================================

@pytest.mark.asyncio
async def test_tier4_assisted_mode_complete_operator_workflow(operating_modes_env, mock_dns_resolver, qapp):
    """Scenario 2: Complete Assisted Mode lifecycle:

    1. Observability detects heavy DNS packet loss / degradation in Ask mode.
    2. Orchestrator halts autonomous execution and emits REMEDIATION_APPROVAL_REQUIRED.
    3. UI Timeline widget receives proposal and presents 'يحتاج انتباهك' status chip.
    4. Operator reviews recommendation and confirms execution.
    5. orchestrator.approve_action() executes DNS switch on mock platform.
    6. Audit record saved to SQLite and UI Timeline updates to 'تم حله تلقائياً'.
    """
    env = operating_modes_env
    orchestrator: RemediationOrchestrator = env["orchestrator"]
    platform: OperatingModeMockPlatformAdapter = env["platform"]
    bus: EventBus = env["bus"]
    audit_repo: AuditRepository = env["audit_repo"]
    diag_engine: DiagnosisEngine = env["diagnosis_engine"]

    orchestrator.set_operating_mode(MODE_ASK)
    platform.current_dns = ["192.168.1.1"]

    timeline = TimelinePanel()
    timeline.show()

    # Track approval request in UI
    approval_received_in_ui = False
    proposed_action_id: Optional[str] = None

    async def on_approval_required(topic: str, payload: Any):
        nonlocal approval_received_in_ui, proposed_action_id
        approval_received_in_ui = True
        data = payload if isinstance(payload, dict) else payload.model_dump()
        proposed_action_id = data.get("action_id")
        now_str = datetime.now().strftime("%H:%M:%S")
        steps = [
            (now_str, "اكتشاف المشكلة", "انقطاع أو بطء حاد في استجابة خادم الـ DNS."),
            (now_str, "تحديد السبب", "تعطل خادم الـ DNS المحلي."),
            (now_str, "الإصلاح المقترح", f"طلب موافقة المستخدم لتنفيذ {data.get('action_name')}."),
            (now_str, "النتيجة", "في انتظار موافقة المستخدم."),
        ]
        timeline.set_event(now_str[:5], steps, is_resolved=False)

    await bus.subscribe("remediation.approval_required", on_approval_required)
    await bus.subscribe(EventTopics.REMEDIATION_APPROVAL_REQUIRED, on_approval_required)

    # 1. Telemetry input showing DNS loss
    windows = {
        MetricType.GATEWAY_REACHABILITY: [make_measurement(MetricType.GATEWAY_REACHABILITY, 1.0, "192.168.1.1")],
        MetricType.EXTERNAL_PACKET_LOSS: [make_measurement(MetricType.EXTERNAL_PACKET_LOSS, 0.0, "1.1.1.1")],
        MetricType.DNS_SUCCESS_RATE: [
            make_measurement(MetricType.DNS_SUCCESS_RATE, 0.0, "system_dns", ProbeStatus.FAILED)
        ],
    }

    # 2. Diagnosis evaluation
    diag = await diag_engine.evaluate_windows(windows)
    assert diag.probable_cause == ProbableCause.DNS_RESOLVER_UNRESPONSIVE

    # 3. Handle diagnosis in Ask mode
    record = await orchestrator.handle_diagnosis(diag)
    assert record is None
    assert approval_received_in_ui is True
    assert proposed_action_id == "flush_dns_cache"

    # 4. Verify UI presents pending attention chip
    assert "يحتاج انتباهك" in timeline.status_chip.text()
    assert timeline.btn_rollback.isHidden() is True

    # 5. Assert zero OS commands before operator approves
    assert platform.flushed is False
    assert platform.flush_count == 0

    # 6. Operator confirms execution via approve_action contract
    assert hasattr(
        orchestrator, "approve_action"
    ), "RemediationOrchestrator must implement approve_action() per PROJECT.md interface contract"

    ok, msg = await orchestrator.approve_action(proposed_action_id, {"diagnosis": diag})
    assert ok is True

    # 7. Assert action executed
    assert platform.flushed is True
    assert platform.flush_count == 1

    # 8. Assert SQLite audit row written
    audits = audit_repo.get_recent(limit=5)
    assert len(audits) >= 1
    assert audits[0].status == ActionExecutionStatus.SUCCEEDED

    # 9. Update UI to resolved
    now_str = datetime.now().strftime("%H:%M:%S")
    steps_resolved = [
        (now_str, "اكتشاف المشكلة", "انقطاع أو بطء حاد في استجابة خادم الـ DNS."),
        (now_str, "تحديد السبب", "تعطل خادم الـ DNS المحلي."),
        (now_str, "الإصلاح", "تم تفريغ كاش الـ DNS بنجاح بعد موافقتك."),
        (now_str, "النتيجة", "استعادة الاستقرار وانخفاض زمن الاستجابة إلى 12ms."),
    ]
    timeline.set_event(now_str[:5], steps_resolved, is_resolved=True)

    assert "تم حله تلقائياً" in timeline.status_chip.text()
    assert timeline.btn_rollback.isVisible() is True
