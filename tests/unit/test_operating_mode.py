"""Unit tests for OperatingMode and Single Source of Truth Synchronization (R2)."""

import pytest
import asyncio
from typing import Any, List
from PySide6.QtWidgets import QApplication

from app.core.models.metrics import (
    OperatingMode,
    RiskLevel,
    Diagnosis,
    ProbableCause,
    DiagnosisSeverity,
    ActionExecutionStatus,
)
from app.core.bus import EventBus, EventTopics
from app.core.config.models import RemediationConfig
from app.remediation.orchestrator import RemediationOrchestrator
from app.remediation.registry import ActionRegistry
from app.remediation.safety import ActionSafetyManager
from app.storage.database import DatabaseManager
from app.storage.repositories.audit_repo import AuditRepository
from tests.unit.test_remediation import ControllableAction, MockPlatformAdapterForRemediation


@pytest.fixture(scope="session")
def qapp():
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


# Suite 1: Enum Contract and Backward Compatibility
def test_operating_mode_canonical_and_aliases():
    assert OperatingMode.AUTO.value == "auto"
    assert OperatingMode.ASK.value == "ask"
    assert OperatingMode.WATCH.value == "watch"
    assert OperatingMode.AUTONOMOUS_SAFE == OperatingMode.AUTO
    assert OperatingMode.ASSISTED == OperatingMode.ASK
    assert OperatingMode.OBSERVATION == OperatingMode.WATCH


def test_operating_mode_string_parsing():
    assert OperatingMode("auto") == OperatingMode.AUTO
    assert OperatingMode("autonomous_safe") == OperatingMode.AUTO
    assert OperatingMode("autonomous") == OperatingMode.AUTO
    assert OperatingMode("safe") == OperatingMode.AUTO
    assert OperatingMode("ask") == OperatingMode.ASK
    assert OperatingMode("assisted") == OperatingMode.ASK
    assert OperatingMode("watch") == OperatingMode.WATCH
    assert OperatingMode("observation") == OperatingMode.WATCH
    assert OperatingMode("observe") == OperatingMode.WATCH
    assert OperatingMode("AUTO") == OperatingMode.AUTO
    assert OperatingMode("  Assisted  ") == OperatingMode.ASK


# Suite 2: Drastic Actions Approval Gate across all modes
@pytest.mark.asyncio
async def test_drastic_action_requires_approval_across_all_modes(tmp_path):
    bus = EventBus()
    db_manager = DatabaseManager(db_path=tmp_path / "rem_test.db", enable_wal=False)
    audit_repo = AuditRepository(db_manager)
    platform = MockPlatformAdapterForRemediation()
    safety = ActionSafetyManager(failure_threshold=3, reset_timeout_sec=0.5)
    registry = ActionRegistry()
    config = RemediationConfig(mode="auto", cooldown_period_sec=0.01)

    orchestrator = RemediationOrchestrator(
        config=config,
        registry=registry,
        safety_manager=safety,
        platform_adapter=platform,
        audit_repo=audit_repo,
        event_bus=bus,
    )

    drastic_action = ControllableAction(action_id="renew_ip_lease")
    drastic_action.risk_level = RiskLevel.LEVEL_3_DISRUPTIVE
    registry.register(drastic_action)

    approval_events = []
    bus.subscribe_sync(EventTopics.REMEDIATION_APPROVAL_REQUIRED, lambda t, d: approval_events.append(d))

    diag = Diagnosis(
        probable_cause=ProbableCause.LOCAL_GATEWAY_UNREACHABLE,
        confidence=0.9,
        severity=DiagnosisSeverity.CRITICAL,
        recommended_actions=["renew_ip_lease"],
    )

    # 1. AUTO mode: Must NOT execute automatically, must request approval
    orchestrator.set_operating_mode(OperatingMode.AUTO)
    record = await orchestrator.handle_diagnosis(diag)
    assert record is None
    assert drastic_action.executed is False
    assert len(approval_events) == 1
    assert approval_events[0]["action_id"] == "renew_ip_lease"

    # 2. Approve action explicitly
    ok, msg = await orchestrator.approve_action("renew_ip_lease")
    assert ok is True
    assert drastic_action.executed is True

    # 3. ASK mode: Must halt and request approval
    drastic_action.executed = False
    orchestrator.set_operating_mode(OperatingMode.ASK)
    record = await orchestrator.handle_diagnosis(diag)
    assert record is None
    assert drastic_action.executed is False
    assert len(approval_events) == 2

    # Reject action
    ok, msg = await orchestrator.reject_action("renew_ip_lease")
    assert ok is True
    assert drastic_action.executed is False

    # 4. WATCH mode: Zero system modifications
    drastic_action.executed = False
    orchestrator.set_operating_mode(OperatingMode.WATCH)
    record = await orchestrator.handle_diagnosis(diag)
    assert record is None
    assert drastic_action.executed is False


# Suite 3: Cross-view synchronization in UI
def test_cross_view_mode_synchronization(qapp):
    from app.ui.views.remediation_view import RemediationView
    from app.ui.views.settings_view import SettingsView
    from app.ui.main_window import SidebarWidget

    sidebar = SidebarWidget()
    rem_view = RemediationView()
    settings_view = SettingsView()

    # Initial state
    sidebar.set_operating_mode(OperatingMode.AUTO)
    rem_view.set_operating_mode(OperatingMode.AUTO)
    settings_view.set_operating_mode(OperatingMode.AUTO)

    assert sidebar._current_mode_idx == 0
    assert rem_view._current_mode_idx == 0
    assert settings_view.mode_combo.currentData() == "auto"

    # Switch to ASK
    sidebar.set_operating_mode(OperatingMode.ASK)
    rem_view.set_operating_mode(OperatingMode.ASK)
    settings_view.set_operating_mode(OperatingMode.ASK)

    assert sidebar._current_mode_idx == 1
    assert rem_view._current_mode_idx == 1
    assert settings_view.mode_combo.currentData() == "ask"

    # Switch to WATCH
    sidebar.set_operating_mode(OperatingMode.WATCH)
    rem_view.set_operating_mode(OperatingMode.WATCH)
    settings_view.set_operating_mode(OperatingMode.WATCH)

    assert sidebar._current_mode_idx == 2
    assert rem_view._current_mode_idx == 2
    assert settings_view.mode_combo.currentData() == "watch"
