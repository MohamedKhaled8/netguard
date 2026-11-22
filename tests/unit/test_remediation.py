"""Unit tests for NetGuard AI Stage 3 Autonomous Self-Healing Engine."""

import pytest
import asyncio
from datetime import datetime, timezone
from app.core.config.models import RemediationConfig
from app.core.events.bus import EventBus
from app.core.models.metrics import (
    Diagnosis,
    ProbableCause,
    DiagnosisSeverity,
    OperatingMode,
    RiskLevel,
    ActionExecutionStatus,
)
from app.platform.interfaces import IPlatformAdapter
from app.remediation.registry import ActionRegistry, RemediationAction
from app.remediation.safety import ActionSafetyManager, CircuitBreaker
from app.remediation.orchestrator import RemediationOrchestrator
from app.remediation.actions.flush_dns import FlushDNSCacheAction
from app.remediation.actions.switch_dns import SwitchDNSResolverAction
from app.remediation.actions.renew_dhcp import RenewIPLeaseAction
from app.storage.database import DatabaseManager
from app.storage.repositories.audit_repo import AuditRepository


class MockPlatformAdapterForRemediation(IPlatformAdapter):
    def __init__(self):
        self.flushed = False
        self.current_dns = ["192.168.1.1"]
        self.dns_mode: str = "static"
        self.renewed = False
        self.ping_ok = True

    def is_elevated(self):
        return True

    def get_default_gateway(self):
        return "192.168.1.1"

    def get_primary_interface(self):
        return "Wi-Fi"

    def ping(self, target: str, timeout_sec: float = 1.5):
        return self.ping_ok, 12.0

    def tcp_connect(self, target: str, port: int = 80, timeout_sec: float = 2.0):
        return True, 15.0

    def flush_dns_cache(self):
        self.flushed = True
        return True, "Flushed"

    def get_interface_dns_servers(self, interface_name: str):
        return list(self.current_dns)

    def get_interface_dns_mode(self, interface_name: str) -> str:
        return getattr(self, "dns_mode", "static" if self.current_dns else "dhcp")

    def set_interface_dns_servers(self, interface_name: str, servers):
        self.current_dns = list(servers)
        return True, "OK"

    def renew_ip_lease(self, interface_name: str):
        self.renewed = True
        return True, "Renewed"

    def get_wifi_metrics(self, interface_name=None):
        return {"is_wifi": True, "signal_percent": 80.0}


class ControllableAction(RemediationAction):
    """Test action with controllable execute, verify, and rollback behaviors."""

    def __init__(self, action_id="test_action", fail_verify=False, fail_execute=False):
        super().__init__(
            action_id=action_id,
            name="Controllable Test Action",
            description="Used for unit testing lifecycle",
            risk_level=RiskLevel.LEVEL_1_LOW,
            cooldown_sec=0.1,
        )
        self.fail_verify = fail_verify
        self.fail_execute = fail_execute
        self.executed = False
        self.verified = False
        self.rolled_back = False

    def check_preconditions(self, platform, context):
        return True, "OK"

    async def execute(self, platform, context):
        self.executed = True
        if self.fail_execute:
            raise RuntimeError("Forced execution failure")
        return {"previous_val": 42}

    async def verify(self, platform, context, pre_state):
        self.verified = True
        if self.fail_verify:
            return False, "Verification forced to fail", {}
        return True, "Verified OK", {"latency_ms": 10.0}

    async def rollback(self, platform, context, pre_state):
        self.rolled_back = True
        return True, "Rollback OK"


@pytest.fixture
def remediation_setup(tmp_path):
    db_file = tmp_path / "rem_test.db"
    db_manager = DatabaseManager(db_path=db_file, enable_wal=False)
    audit_repo = AuditRepository(db_manager)
    bus = EventBus()
    platform = MockPlatformAdapterForRemediation()
    safety = ActionSafetyManager(failure_threshold=3, reset_timeout_sec=0.5)
    registry = ActionRegistry()
    config = RemediationConfig(mode="autonomous_safe", cooldown_period_sec=0.1)

    orchestrator = RemediationOrchestrator(
        config=config,
        registry=registry,
        safety_manager=safety,
        platform_adapter=platform,
        audit_repo=audit_repo,
        event_bus=bus,
    )
    return orchestrator, registry, safety, platform, audit_repo, bus


@pytest.mark.asyncio
async def test_successful_action_lifecycle(remediation_setup):
    orchestrator, registry, safety, platform, audit_repo, bus = remediation_setup
    action = ControllableAction(action_id="test_action", fail_verify=False)
    registry.register(action)

    diag = Diagnosis(
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        confidence=0.95,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["test_action"],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)
    assert record is not None
    assert record.status == ActionExecutionStatus.SUCCEEDED
    assert action.executed is True
    assert action.verified is True
    assert action.rolled_back is False
    assert record.rollback_performed is False

    # Check persistence
    audits = audit_repo.get_recent(limit=5)
    assert len(audits) == 1
    assert audits[0].status == ActionExecutionStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_verification_failure_triggers_rollback(remediation_setup):
    orchestrator, registry, safety, platform, audit_repo, bus = remediation_setup
    action = ControllableAction(action_id="failing_action", fail_verify=True)
    registry.register(action)

    diag = Diagnosis(
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        confidence=0.95,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["failing_action"],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)
    assert record is not None
    assert record.status == ActionExecutionStatus.ROLLED_BACK
    assert action.executed is True
    assert action.verified is True
    assert action.rolled_back is True
    assert record.rollback_performed is True
    assert record.rollback_success is True


@pytest.mark.asyncio
async def test_circuit_breaker_prevents_retry_loop(remediation_setup):
    orchestrator, registry, safety, platform, audit_repo, bus = remediation_setup
    action = ControllableAction(action_id="bad_action", fail_verify=True)
    action.cooldown_sec = 0.0  # disable cooldown to test circuit breaker directly
    registry.register(action)

    diag = Diagnosis(
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        confidence=0.95,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["bad_action"],
        auto_remediation_permitted=True,
    )

    # 3 failures will trip the breaker (threshold = 3)
    await orchestrator.handle_diagnosis(diag)
    await orchestrator.handle_diagnosis(diag)
    await orchestrator.handle_diagnosis(diag)

    # 4th call should be blocked by circuit breaker
    record4 = await orchestrator.handle_diagnosis(diag)
    assert record4 is None  # Blocked before execution


@pytest.mark.asyncio
async def test_observation_mode_suppresses_execution(remediation_setup):
    orchestrator, registry, safety, platform, audit_repo, bus = remediation_setup
    orchestrator.set_operating_mode(OperatingMode.OBSERVATION)
    action = ControllableAction(action_id="suppressed_action")
    registry.register(action)

    diag = Diagnosis(
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        confidence=0.95,
        severity=DiagnosisSeverity.HIGH,
        recommended_actions=["suppressed_action"],
        auto_remediation_permitted=True,
    )

    record = await orchestrator.handle_diagnosis(diag)
    assert record is None
    assert action.executed is False


@pytest.mark.asyncio
async def test_switch_dns_action_and_rollback(tmp_path):
    platform = MockPlatformAdapterForRemediation()
    platform.current_dns = ["192.168.1.1"]  # original DNS
    action = SwitchDNSResolverAction(fallback_resolvers=["1.1.1.1", "8.8.8.8"])

    # 1. Execute
    pre_state = await action.execute(platform, {})
    assert pre_state["original_servers"] == ["192.168.1.1"]
    assert platform.current_dns == ["1.1.1.1", "8.8.8.8"]
    assert platform.flushed is True

    # 2. Rollback
    ok, msg = await action.rollback(platform, {}, pre_state)
    assert ok is True
    assert platform.current_dns == ["192.168.1.1"]  # Original restored!


@pytest.mark.asyncio
async def test_switch_dns_action_and_rollback_dhcp(tmp_path):
    platform = MockPlatformAdapterForRemediation()
    platform.current_dns = ["192.168.1.1"]
    platform.dns_mode = "dhcp"
    action = SwitchDNSResolverAction(fallback_resolvers=["1.1.1.1", "8.8.8.8"])

    # 1. Execute
    pre_state = await action.execute(platform, {})
    assert pre_state["original_servers"] == ["192.168.1.1"]
    assert pre_state["is_dhcp"] is True
    assert platform.current_dns == ["1.1.1.1", "8.8.8.8"]
    assert platform.flushed is True

    # 2. Rollback
    ok, msg = await action.rollback(platform, {}, pre_state)
    assert ok is True
    assert platform.current_dns == []  # Rolled back to DHCP!


@pytest.mark.asyncio
async def test_unprivileged_precondition_refusal():
    class UnprivilegedPlatform(MockPlatformAdapterForRemediation):
        def is_elevated(self):
            return False

    platform = UnprivilegedPlatform()
    dns_action = SwitchDNSResolverAction()
    dhcp_action = RenewIPLeaseAction()

    # Preconditions must fail when unprivileged
    ok_dns, msg_dns = dns_action.check_preconditions(platform, {})
    assert ok_dns is False
    assert "Administrator privileges" in msg_dns

    ok_dhcp, msg_dhcp = dhcp_action.check_preconditions(platform, {})
    assert ok_dhcp is False
    assert "Administrator privileges" in msg_dhcp


@pytest.mark.asyncio
async def test_recheck_gateway_action():
    from app.remediation.actions.recheck_gateway import RecheckGatewayAction
    platform = MockPlatformAdapterForRemediation()
    action = RecheckGatewayAction()

    pre_state = await action.execute(platform, {})
    assert pre_state["successful_pings"] == 3

    ok, msg, _ = await action.verify(platform, {}, pre_state)
    assert ok is True
