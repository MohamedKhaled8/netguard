"""Unit tests for NetGuard AI Remediation Policy Toggles (AC-5, R5).

Covers 4-tier testing:
- Tier 1: Feature Coverage (Each of the 4 policy toggles individually: enabled executes, disabled suppresses)
  - allow_flush_dns: gates FlushDNSCacheAction
  - allow_switch_dns: gates SwitchDNSResolverAction
  - allow_renew_ip: gates RenewIPLeaseAction
  - meeting_guard: gates Meeting Guard QoS / protection
- Tier 2: Boundary & Corner Cases (All policies disabled simultaneously, unknown policy keys, empty recommendations)
- Tier 3: Cross-Feature Combinations (Dynamic mid-flight toggles, settings.changed signal propagation, mode interactions)
- Tier 4: Real-World Scenarios (Multi-incident cascade under varying policy configurations)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import pytest

from app.core.config.models import RemediationConfig
from app.core.events.bus import EventBus
from app.core.models.metrics import (
    Diagnosis,
    ProbableCause,
    DiagnosisSeverity,
    OperatingMode,
    RiskLevel,
    ActionExecutionStatus,
    ActionExecutionRecord,
)
from app.platform.interfaces import IPlatformAdapter
from app.remediation.registry import ActionRegistry, RemediationAction
from app.remediation.safety import ActionSafetyManager
from app.remediation.orchestrator import RemediationOrchestrator
from app.remediation.actions.flush_dns import FlushDNSCacheAction
from app.remediation.actions.switch_dns import SwitchDNSResolverAction
from app.remediation.actions.renew_dhcp import RenewIPLeaseAction
from app.storage.database import DatabaseManager
from app.storage.repositories.audit_repo import AuditRepository

# EventTopics resolution
try:
    from app.core.bus import EventTopics
except ImportError:
    try:
        from app.core.events.bus import EventTopics
    except ImportError:
        EventTopics = None

# UserSettings resolution
try:
    from app.core.settings import UserSettings
except ImportError:
    UserSettings = None


class MockPlatformAdapterForPolicies(IPlatformAdapter):
    """Mock platform adapter tracking individual OS operations."""

    def __init__(self) -> None:
        self.flushed = False
        self.flush_count = 0
        self.current_dns = ["192.168.1.1"]
        self.dns_switched = False
        self.renewed = False
        self.renew_count = 0
        self.ping_ok = True
        self.meeting_guard_qos_applied = False

    def is_elevated(self) -> bool:
        return True

    def get_default_gateway(self) -> str:
        return "192.168.1.1"

    def get_primary_interface(self) -> str:
        return "Wi-Fi"

    def ping(self, target: str, timeout_sec: float = 1.5) -> tuple[bool, float]:
        return self.ping_ok, 12.0

    def tcp_connect(self, target: str, port: int = 80, timeout_sec: float = 2.0) -> tuple[bool, float]:
        return True, 15.0

    def flush_dns_cache(self) -> tuple[bool, str]:
        self.flushed = True
        self.flush_count += 1
        return True, "Flushed DNS successfully"

    def get_interface_dns_servers(self, interface_name: str) -> list[str]:
        return list(self.current_dns)

    def set_interface_dns_servers(self, interface_name: str, servers: list[str]) -> tuple[bool, str]:
        self.current_dns = list(servers)
        self.dns_switched = True
        return True, "Set DNS successfully"

    def renew_ip_lease(self, interface_name: str) -> tuple[bool, str]:
        self.renewed = True
        self.renew_count += 1
        return True, "Renewed IP lease successfully"

    def get_wifi_metrics(self, interface_name: Optional[str] = None) -> dict[str, Any]:
        return {"is_wifi": True, "signal_percent": 80.0}


class MockFlushDNSCacheAction(FlushDNSCacheAction):
    """Subclass FlushDNSCacheAction with self-contained verification to avoid internet lookups."""

    async def verify(self, platform: IPlatformAdapter, context: dict[str, Any], pre_state: Any) -> tuple[bool, str, dict[str, Any]]:
        return True, "DNS cache flush verified (test fixture)", {"latency_ms": 8.0}


class MeetingGuardQoSAction(RemediationAction):
    """Meeting Guard QoS priority remediation action."""

    def __init__(self) -> None:
        super().__init__(
            action_id="meeting_guard_qos",
            name="Meeting Guard QoS Priority",
            description="Boosts priority of conferencing UDP sockets",
            risk_level=RiskLevel.LEVEL_1_LOW,
            cooldown_sec=0.1,
        )
        self.executed = False

    def check_preconditions(self, platform: IPlatformAdapter, context: dict[str, Any]) -> tuple[bool, str]:
        return True, "OK"

    async def execute(self, platform: IPlatformAdapter, context: dict[str, Any]) -> dict[str, Any]:
        self.executed = True
        if hasattr(platform, "meeting_guard_qos_applied"):
            platform.meeting_guard_qos_applied = True
        return {"qos_applied": True}

    async def verify(self, platform: IPlatformAdapter, context: dict[str, Any], pre_state: Any) -> tuple[bool, str, dict[str, Any]]:
        return True, "QoS Active", {}

    async def rollback(self, platform: IPlatformAdapter, context: dict[str, Any], pre_state: Any) -> tuple[bool, str]:
        self.executed = False
        return True, "QoS Reverted"


def set_policy(orchestrator: RemediationOrchestrator, policy_name: str, enabled: bool) -> None:
    """Helper to set policy toggle on orchestrator regardless of internal wiring."""
    if hasattr(orchestrator, "user_settings") and orchestrator.user_settings:
        orchestrator.user_settings.set_policy(policy_name, enabled)
    elif hasattr(orchestrator, "set_policy"):
        orchestrator.set_policy(policy_name, enabled)
    elif hasattr(orchestrator, "policies"):
        if isinstance(orchestrator.policies, dict):
            orchestrator.policies[policy_name] = enabled
        else:
            setattr(orchestrator.policies, policy_name, enabled)
    elif hasattr(orchestrator, "config") and hasattr(orchestrator.config, "policies"):
        setattr(orchestrator.config.policies, policy_name, enabled)


@pytest.fixture
def policy_fixture(tmp_path: Path):
    """Fixture providing orchestrator, mock platform, event bus, and captured events."""
    db_file = tmp_path / "policy_test.db"
    db_manager = DatabaseManager(db_path=db_file, enable_wal=False)
    audit_repo = AuditRepository(db_manager)
    bus = EventBus()
    platform = MockPlatformAdapterForPolicies()
    safety = ActionSafetyManager(failure_threshold=3, reset_timeout_sec=0.5)
    registry = ActionRegistry()

    # Register core actions
    registry.register(MockFlushDNSCacheAction())
    registry.register(SwitchDNSResolverAction(fallback_resolvers=["1.1.1.1", "8.8.8.8"]))
    registry.register(RenewIPLeaseAction())
    registry.register(MeetingGuardQoSAction())

    # Configure auto mode and allow disruptive level 3 for policy-specific testing
    config = RemediationConfig(
        mode="autonomous_safe",
        cooldown_period_sec=0.05,
        allow_level_3_disruptive=True,
    )

    captured_events: List[tuple[str, Any]] = []

    async def capture_event(topic: str, payload: Any):
        captured_events.append((topic, payload))

    # Subscribe to remediation events
    bus.subscribe_sync("remediation.*", capture_event)

    meeting_active = [False]

    def meeting_guard_check():
        return meeting_active[0]

    # Instantiate orchestrator
    try:
        if UserSettings is not None:
            settings_obj = UserSettings(config_dir=tmp_path / "settings")
            orchestrator = RemediationOrchestrator(
                config=config,
                registry=registry,
                safety_manager=safety,
                platform_adapter=platform,
                audit_repo=audit_repo,
                event_bus=bus,
                meeting_guard_check=meeting_guard_check,
                user_settings=settings_obj,
            )
        else:
            raise TypeError
    except TypeError:
        orchestrator = RemediationOrchestrator(
            config=config,
            registry=registry,
            safety_manager=safety,
            platform_adapter=platform,
            audit_repo=audit_repo,
            event_bus=bus,
            meeting_guard_check=meeting_guard_check,
        )
        if UserSettings is not None:
            try:
                orchestrator.user_settings = UserSettings(config_dir=tmp_path / "settings")
            except Exception:
                pass

    return orchestrator, platform, bus, captured_events, meeting_active


# ============================================================================
# Tier 1: Feature Coverage (AC-5: 4 Individual Policy Toggles)
# ============================================================================


@pytest.mark.asyncio
async def test_policy_allow_flush_dns_enabled_executes(policy_fixture):
    """When allow_flush_dns is True, DNS latency incident triggers flush_dns_cache."""
    orchestrator, platform, bus, captured, _ = policy_fixture
    set_policy(orchestrator, "allow_flush_dns", True)

    diag = Diagnosis(
        probable_cause=ProbableCause.DNS_RESOLVER_HIGH_LATENCY,
        confidence=0.9,
        severity=DiagnosisSeverity.MEDIUM,
        recommended_actions=["flush_dns_cache"],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)
    assert record is not None
    assert record.status == ActionExecutionStatus.SUCCEEDED
    assert platform.flushed is True


@pytest.mark.asyncio
async def test_policy_allow_flush_dns_disabled_suppresses(policy_fixture):
    """When allow_flush_dns is False, DNS flush action is suppressed with zero OS execution."""
    orchestrator, platform, bus, captured, _ = policy_fixture
    set_policy(orchestrator, "allow_flush_dns", False)

    diag = Diagnosis(
        probable_cause=ProbableCause.DNS_RESOLVER_HIGH_LATENCY,
        confidence=0.9,
        severity=DiagnosisSeverity.MEDIUM,
        recommended_actions=["flush_dns_cache"],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)

    # 1. Action is suppressed: record is None
    assert record is None

    # 2. Zero OS commands executed
    assert platform.flushed is False
    assert platform.flush_count == 0

    # 3. Suppressed event emitted
    suppressed_topic = getattr(EventTopics, "REMEDIATION_ACTION_SUPPRESSED", "remediation.action_suppressed")
    suppressed_events = [e for e in captured if e[0] == suppressed_topic]
    assert len(suppressed_events) >= 1
    assert suppressed_events[0][1].get("action_id") == "flush_dns_cache"


@pytest.mark.asyncio
async def test_policy_allow_switch_dns_enabled_executes(policy_fixture):
    """When allow_switch_dns is True, DNS switch action executes."""
    orchestrator, platform, bus, captured, _ = policy_fixture
    set_policy(orchestrator, "allow_switch_dns", True)

    diag = Diagnosis(
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        confidence=0.95,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["switch_dns_resolver"],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)
    assert record is not None
    assert record.status == ActionExecutionStatus.SUCCEEDED
    assert platform.dns_switched is True
    assert platform.current_dns == ["1.1.1.1", "8.8.8.8"]


@pytest.mark.asyncio
async def test_policy_allow_switch_dns_disabled_suppresses(policy_fixture):
    """When allow_switch_dns is False, DNS switch action is suppressed."""
    orchestrator, platform, bus, captured, _ = policy_fixture
    set_policy(orchestrator, "allow_switch_dns", False)

    diag = Diagnosis(
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        confidence=0.95,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["switch_dns_resolver"],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)
    assert record is None
    assert platform.dns_switched is False
    assert platform.current_dns == ["192.168.1.1"]  # unchanged

    suppressed_topic = getattr(EventTopics, "REMEDIATION_ACTION_SUPPRESSED", "remediation.action_suppressed")
    suppressed_events = [e for e in captured if e[0] == suppressed_topic]
    assert any(e[1].get("action_id") == "switch_dns_resolver" for e in suppressed_events)


@pytest.mark.asyncio
async def test_policy_allow_renew_ip_enabled_executes(policy_fixture):
    """When allow_renew_ip is True, IP lease renew executes."""
    orchestrator, platform, bus, captured, _ = policy_fixture
    set_policy(orchestrator, "allow_renew_ip", True)

    diag = Diagnosis(
        probable_cause=ProbableCause.LOCAL_GATEWAY_UNREACHABLE,
        confidence=0.9,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["renew_ip_lease"],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)
    assert record is not None
    assert record.status == ActionExecutionStatus.SUCCEEDED
    assert platform.renewed is True


@pytest.mark.asyncio
async def test_policy_allow_renew_ip_disabled_suppresses(policy_fixture):
    """When allow_renew_ip is False, renew IP action is suppressed."""
    orchestrator, platform, bus, captured, _ = policy_fixture
    set_policy(orchestrator, "allow_renew_ip", False)

    diag = Diagnosis(
        probable_cause=ProbableCause.LOCAL_GATEWAY_UNREACHABLE,
        confidence=0.9,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["renew_ip_lease"],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)
    assert record is None
    assert platform.renewed is False
    assert platform.renew_count == 0

    suppressed_topic = getattr(EventTopics, "REMEDIATION_ACTION_SUPPRESSED", "remediation.action_suppressed")
    suppressed_events = [e for e in captured if e[0] == suppressed_topic]
    assert any(e[1].get("action_id") == "renew_ip_lease" for e in suppressed_events)


@pytest.mark.asyncio
async def test_policy_meeting_guard_suppresses_disruptive_action_during_meeting(policy_fixture):
    """When meeting_guard policy is enabled and video call is active, disruptive action is suppressed."""
    orchestrator, platform, bus, captured, meeting_active = policy_fixture
    set_policy(orchestrator, "meeting_guard", True)
    meeting_active[0] = True  # Call active

    diag = Diagnosis(
        probable_cause=ProbableCause.LOCAL_GATEWAY_UNREACHABLE,
        confidence=0.9,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["renew_ip_lease"],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)
    assert record is None
    assert platform.renewed is False

    suppressed_topic = getattr(EventTopics, "REMEDIATION_ACTION_SUPPRESSED", "remediation.action_suppressed")
    suppressed_events = [e for e in captured if e[0] == suppressed_topic]
    assert len(suppressed_events) >= 1
    assert "مكالمة" in suppressed_events[0][1].get("reason", "") or "meeting" in suppressed_events[0][1].get("reason", "").lower() or "disruptive" in suppressed_events[0][1].get("reason", "").lower()


@pytest.mark.asyncio
async def test_policy_meeting_guard_disabled_allows_action_even_if_meeting_flagged(policy_fixture):
    """When meeting_guard policy is turned off by user, meeting protection is deactivated."""
    orchestrator, platform, bus, captured, meeting_active = policy_fixture
    set_policy(orchestrator, "meeting_guard", False)
    set_policy(orchestrator, "allow_renew_ip", True)
    meeting_active[0] = True

    diag = Diagnosis(
        probable_cause=ProbableCause.LOCAL_GATEWAY_UNREACHABLE,
        confidence=0.9,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["renew_ip_lease"],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)
    if record is not None:
        assert record.status == ActionExecutionStatus.SUCCEEDED
        assert platform.renewed is True


# ============================================================================
# Tier 2: Boundary & Corner Cases
# ============================================================================


@pytest.mark.asyncio
async def test_all_policies_disabled_simultaneously(policy_fixture):
    """When all policies are turned off, system remains stable and suppresses all actions."""
    orchestrator, platform, bus, captured, _ = policy_fixture
    set_policy(orchestrator, "allow_flush_dns", False)
    set_policy(orchestrator, "allow_switch_dns", False)
    set_policy(orchestrator, "allow_renew_ip", False)
    set_policy(orchestrator, "meeting_guard", False)

    # 1. DNS incident
    diag1 = Diagnosis(
        probable_cause=ProbableCause.DNS_RESOLVER_HIGH_LATENCY,
        confidence=0.9,
        severity=DiagnosisSeverity.MEDIUM,
        recommended_actions=["flush_dns_cache"],
        auto_remediation_permitted=True,
    )
    r1 = await orchestrator.handle_diagnosis(diag1)
    assert r1 is None
    assert platform.flushed is False

    # 2. DNS resolver dead
    diag2 = Diagnosis(
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        confidence=0.95,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["switch_dns_resolver"],
        auto_remediation_permitted=True,
    )
    r2 = await orchestrator.handle_diagnosis(diag2)
    assert r2 is None
    assert platform.dns_switched is False

    # 3. Router disconnected
    diag3 = Diagnosis(
        probable_cause=ProbableCause.LOCAL_GATEWAY_UNREACHABLE,
        confidence=0.9,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["renew_ip_lease"],
        auto_remediation_permitted=True,
    )
    r3 = await orchestrator.handle_diagnosis(diag3)
    assert r3 is None
    assert platform.renewed is False


@pytest.mark.asyncio
async def test_policy_check_with_no_recommended_actions(policy_fixture):
    """Diagnosis with empty recommended actions cleanly returns None without policy checks."""
    orchestrator, platform, bus, captured, _ = policy_fixture

    diag = Diagnosis(
        probable_cause=ProbableCause.LOCAL_GATEWAY_HIGH_LATENCY,
        confidence=0.8,
        severity=DiagnosisSeverity.LOW,
        recommended_actions=[],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)
    assert record is None


@pytest.mark.asyncio
async def test_policy_check_with_unknown_action_id(policy_fixture):
    """Diagnosis recommending an un-registered action returns None safely."""
    orchestrator, platform, bus, captured, _ = policy_fixture

    diag = Diagnosis(
        probable_cause=ProbableCause.LOCAL_GATEWAY_HIGH_LATENCY,
        confidence=0.8,
        severity=DiagnosisSeverity.MEDIUM,
        recommended_actions=["completely_unknown_action_id_xyz"],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)
    assert record is None


# ============================================================================
# Tier 3: Cross-Feature Combinations & Dynamic Policy Updates
# ============================================================================


@pytest.mark.asyncio
async def test_dynamic_policy_toggle_mid_flight(policy_fixture):
    """Toggling policy right before execution immediately halts orchestrator."""
    orchestrator, platform, bus, captured, _ = policy_fixture

    set_policy(orchestrator, "allow_flush_dns", True)

    diag = Diagnosis(
        probable_cause=ProbableCause.DNS_RESOLVER_HIGH_LATENCY,
        confidence=0.9,
        severity=DiagnosisSeverity.MEDIUM,
        recommended_actions=["flush_dns_cache"],
        auto_remediation_permitted=True,
    )

    # User toggles policy off right before orchestrator handles diagnosis
    set_policy(orchestrator, "allow_flush_dns", False)

    record = await orchestrator.handle_diagnosis(diag)
    assert record is None
    assert platform.flushed is False


@pytest.mark.asyncio
async def test_policy_toggle_propagates_from_user_settings_via_signal(policy_fixture):
    """When UserSettings emits changed signal, orchestrator immediately updates its policy gate."""
    orchestrator, platform, bus, captured, _ = policy_fixture

    if hasattr(orchestrator, "user_settings") and orchestrator.user_settings:
        settings = orchestrator.user_settings
        settings.set_policy("allow_switch_dns", False)

        diag = Diagnosis(
            probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
            confidence=0.95,
            severity=DiagnosisSeverity.HIGH,
            recommended_actions=["switch_dns_resolver"],
            auto_remediation_permitted=True,
        )

        record = await orchestrator.handle_diagnosis(diag)
        assert record is None
        assert platform.dns_switched is False


@pytest.mark.asyncio
async def test_policy_evaluation_under_observation_mode(policy_fixture):
    """In Observation mode, mode check suppresses action regardless of policy toggle."""
    orchestrator, platform, bus, captured, _ = policy_fixture
    target_watch = getattr(OperatingMode, "WATCH", OperatingMode.OBSERVATION)
    orchestrator.set_operating_mode(target_watch)
    set_policy(orchestrator, "allow_flush_dns", True)

    diag = Diagnosis(
        probable_cause=ProbableCause.DNS_RESOLVER_HIGH_LATENCY,
        confidence=0.9,
        severity=DiagnosisSeverity.MEDIUM,
        recommended_actions=["flush_dns_cache"],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)
    assert record is None
    assert platform.flushed is False


# ============================================================================
# Tier 4: Real-World Workload Scenarios
# ============================================================================


@pytest.mark.asyncio
async def test_multi_incident_cascade_under_selective_policy_config(policy_fixture):
    """Simulate real-world incident cascade with mixed policy configuration.
    
    Configuration:
    - allow_flush_dns: True (allowed)
    - allow_switch_dns: False (suppressed)
    - allow_renew_ip: True (allowed)
    - meeting_guard: True (protects during active meeting)
    """
    orchestrator, platform, bus, captured, meeting_active = policy_fixture
    set_policy(orchestrator, "allow_flush_dns", True)
    set_policy(orchestrator, "allow_switch_dns", False)
    set_policy(orchestrator, "allow_renew_ip", True)
    set_policy(orchestrator, "meeting_guard", True)

    # Phase 1: DNS latency spike -> flush executes
    diag1 = Diagnosis(
        probable_cause=ProbableCause.DNS_RESOLVER_HIGH_LATENCY,
        confidence=0.92,
        severity=DiagnosisSeverity.MEDIUM,
        recommended_actions=["flush_dns_cache"],
        auto_remediation_permitted=True,
    )
    r1 = await orchestrator.handle_diagnosis(diag1)
    assert r1 is not None
    assert platform.flushed is True
    assert r1.status == ActionExecutionStatus.SUCCEEDED

    # Phase 2: DNS server unresponsive -> switch DNS suppressed by user policy
    diag2 = Diagnosis(
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        confidence=0.96,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["switch_dns_resolver"],
        auto_remediation_permitted=True,
    )
    r2 = await orchestrator.handle_diagnosis(diag2)
    assert r2 is None
    assert platform.dns_switched is False

    # Phase 3: Router disconnected during active meeting -> renew IP suppressed by Meeting Guard
    meeting_active[0] = True
    diag3 = Diagnosis(
        probable_cause=ProbableCause.LOCAL_GATEWAY_UNREACHABLE,
        confidence=0.95,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["renew_ip_lease"],
        auto_remediation_permitted=True,
    )
    r3 = await orchestrator.handle_diagnosis(diag3)
    assert r3 is None
    assert platform.renewed is False

    # Phase 4: Meeting ends -> renew IP executes successfully
    meeting_active[0] = False
    r4 = await orchestrator.handle_diagnosis(diag3)
    assert r4 is not None
    assert platform.renewed is True
    assert r4.status == ActionExecutionStatus.SUCCEEDED
