"""Unit tests for Meeting Session Tracking, Real-Time Protection & Post-Session Reports."""

import pytest
from datetime import datetime, timezone, timedelta
from app.traffic.session_tracker import AppSessionTracker, AppSessionRecord
from app.traffic.controller import TrafficController
from app.core.events.bus import EventBus
from app.remediation.orchestrator import RemediationOrchestrator
from app.remediation.registry import ActionRegistry
from app.remediation.safety import ActionSafetyManager
from app.remediation.actions.renew_dhcp import RenewIPLeaseAction
from app.core.models.metrics import Diagnosis, ProbableCause, DiagnosisSeverity
from app.core.config.models import RemediationConfig
from unittest.mock import MagicMock


def test_session_tracker_lifecycle():
    tracker = AppSessionTracker()

    # Initial history starts empty with no fabricated sessions
    completed = tracker.get_completed_sessions()
    assert len(completed) == 0

    # Start a new session
    session = tracker.start_or_update_session(
        app_name="Zoom Cloud Meetings",
        process_name="zoom.exe",
        pid=1234,
        category="conferencing",
        avg_bitrate=3.5,
        avg_latency=16.0,
    )
    assert session.is_active is True
    assert tracker.has_active_conferencing() is True
    assert len(tracker.get_active_sessions()) == 1

    # Add a preventive action
    tracker.add_preventive_action(
        process_name="zoom.exe",
        title="كبح تحميلات التحديثات",
        detail="تقييد استهلاك الباندويث بنسبة 50%",
        impact="منع أي تذبذب في الصوت والصورة",
    )
    active = tracker.get_active_sessions()[0]
    assert len(active.preventive_actions) >= 2

    # Close session
    closed = tracker.close_session("zoom.exe")
    assert closed is not None
    assert closed.is_active is False
    assert closed.end_time is not None
    assert tracker.has_active_conferencing() is False
    assert len(tracker.get_active_sessions()) == 0

    # Ensure closed session is at top of completed list
    assert tracker.get_completed_sessions()[0].session_id == closed.session_id


def test_traffic_controller_meeting_simulation():
    event_bus = EventBus()
    controller = TrafficController(event_bus=event_bus)

    assert controller.is_critical_meeting_active() is False

    # Simulate start meeting
    controller.simulate_start_meeting_session(app_name="Zoom Cloud Meetings", proc_name="zoom.exe")
    assert controller.is_critical_meeting_active() is True
    assert len(controller.session_tracker.get_active_sessions()) == 1

    # Simulate close meeting
    closed = controller.simulate_close_meeting_session("zoom.exe")
    assert closed is not None
    assert controller.is_critical_meeting_active() is False


@pytest.mark.asyncio
async def test_remediation_orchestrator_suppresses_disruptive_during_meeting():
    event_bus = EventBus()
    registry = ActionRegistry()
    registry.register(RenewIPLeaseAction())

    safety = ActionSafetyManager()
    platform = MagicMock()
    platform.get_primary_interface.return_value = "Wi-Fi"
    audit = MagicMock()

    config = RemediationConfig(mode="autonomous_safe", allow_level_3_disruptive=True)

    # When meeting guard check returns True (Zoom call is running)
    orchestrator = RemediationOrchestrator(
        config=config,
        registry=registry,
        safety_manager=safety,
        platform_adapter=platform,
        audit_repo=audit,
        event_bus=event_bus,
        meeting_guard_check=lambda: True,
    )

    diagnosis = Diagnosis(
        probable_cause=ProbableCause.LOCAL_GATEWAY_UNREACHABLE,
        severity=DiagnosisSeverity.CRITICAL,
        confidence=0.95,
        recommended_actions=["renew_ip_lease"],  # Level 3 disruptive
    )

    # Should be suppressed to protect the live call
    record = await orchestrator.handle_diagnosis(diagnosis)
    assert record is None
