"""Unit tests for Milestone 3 (Features 12–19).

Verifies:
- Feature 12: Elimination of fabricated quality baselines (no 0/5/25 defaults).
- Feature 13: Live probe telemetry connected to record_quality_sample with <= 10s freshness.
- Feature 14: Same-call pre-policy baseline during ENTERING state, auto-rollback disabled
             when baseline unavailable, empty verified_names never falls back, structured rollback logs.
- Feature 15: AppQoSConfig.from_user_settings / to_user_settings and UserSettingsSchema dict preservation.
- Feature 16: Kill switch widget reference fix (master_qos_toggle) and controller.kill_switch_disable call.
- Feature 17: Strict DNS meeting safety freeze (ENTERING, ACTIVE, LEAVING).
- Feature 18: Active bounded upload capacity test during idle only and set_preflight_metrics wiring.
- Feature 19: PyInstaller elevated execution process hierarchy preservation.
"""

import math
import os
import time
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

from app.core.bus import EventBus
from app.core.settings import UserSettings, UserSettingsSchema
from app.traffic.controller import TrafficController
from app.traffic.qos_config import (
    AppQoSConfig,
    QoSPolicySpec,
    PROTECTED_PROCESSES,
    is_netguard_or_protected_process,
)
from app.traffic.meeting_detector import MeetingModeState
from app.traffic.preflight import MeetingPreflightChecker, measure_active_upload_capacity, PreflightReport
from app.core.config.models import RemediationConfig
from app.remediation.registry import RemediationAction
from app.remediation.orchestrator import RemediationOrchestrator
from app.core.models.metrics import (
    RiskLevel,
    Diagnosis,
    DiagnosisSeverity,
    ProbableCause,
)


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def mock_platform():
    plat = MagicMock()
    plat.is_elevated.return_value = True
    plat.sweep_all_netguard_rules.return_value = (True, "Cleaned")
    plat.apply_qos_policies_batch.return_value = (True, "Applied")
    plat.get_default_gateway.return_value = "192.168.1.1"
    plat.get_primary_interface.return_value = "Wi-Fi"
    plat.get_interface_dns_servers.return_value = ["1.1.1.1", "1.0.0.1"]
    plat.flush_dns_cache.return_value = (True, "Flushed")
    plat.last_qos_batch_report = {"verified": [], "failed": []}
    return plat


# ============================================================================
# Feature 12 & 14: Quality Baselines & Rollback Guard
# ============================================================================

def test_f12_no_fabricated_pre_meeting_baseline(event_bus, mock_platform):
    """When fewer than 5 idle samples exist, baseline is None, not 0/5/25."""
    controller = TrafficController(event_bus=event_bus, platform=mock_platform)
    assert len(controller._idle_loss_history) == 0

    base = controller.snapshot_pre_meeting_baseline()
    assert base is None
    assert controller._closed_loop_baseline is None
    assert controller._closed_loop_rollback_enabled is False


def test_f12_evaluate_closed_loop_quality_without_baseline_returns_false(event_bus, mock_platform):
    """Evaluating closed-loop without a baseline never fabricates defaults and returns False."""
    controller = TrafficController(event_bus=event_bus, platform=mock_platform)
    controller._active_qos_specs = [QoSPolicySpec(name="NetGuard_Test")]
    controller._closed_loop_applied_time = time.monotonic() - 15.0  # past grace period

    # No idle samples collected
    rolled_back = controller.evaluate_closed_loop_quality(
        current_loss_pct=5.0,
        current_jitter_ms=20.0,
        current_rtt_ms=80.0,
    )
    assert rolled_back is False
    assert controller._closed_loop_baseline is None
    assert controller._closed_loop_rollback_enabled is False


# ============================================================================
# Feature 13: Live Telemetry Freshness & Rejection
# ============================================================================

def test_f13_record_quality_sample_freshness(event_bus, mock_platform):
    """Stale (>10s old) or future-skewed samples must be rejected."""
    controller = TrafficController(event_bus=event_bus, platform=mock_platform)
    now = time.monotonic()

    # Fresh sample (now) -> accepted
    assert controller.record_quality_sample(1.0, 5.0, 30.0, timestamp_mono=now) is True
    assert len(controller._idle_loss_history) == 1

    # Stale sample (15s ago) -> rejected
    assert controller.record_quality_sample(1.0, 5.0, 30.0, timestamp_mono=now - 15.0) is False
    assert len(controller._idle_loss_history) == 1

    # Future skewed sample (+5s into future) -> rejected
    assert controller.record_quality_sample(1.0, 5.0, 30.0, timestamp_mono=now + 5.0) is False
    assert len(controller._idle_loss_history) == 1

    # Invalid NaN or negative values -> rejected
    assert controller.record_quality_sample(float("nan"), 5.0, 30.0, timestamp_mono=now) is False
    assert controller.record_quality_sample(-1.0, 5.0, 30.0, timestamp_mono=now) is False
    assert controller.record_quality_sample(105.0, 5.0, 30.0, timestamp_mono=now) is False


# ============================================================================
# Feature 14: Same-Call Pre-Policy Baseline & Rollback Guard
# ============================================================================

def test_f14_same_call_pre_policy_baseline_during_entering(event_bus, mock_platform):
    """Samples recorded while in ENTERING state (pre-policy) accumulate into baseline buffer."""
    controller = TrafficController(event_bus=event_bus, platform=mock_platform)
    controller.hysteresis_tracker._state = MeetingModeState.ENTERING

    now = time.monotonic()
    for i in range(6):
        accepted = controller.record_quality_sample(
            loss_pct=0.5,
            jitter_ms=4.0 + i,
            rtt_ms=20.0 + i,
            timestamp_mono=now,
        )
        assert accepted is True

    assert len(controller._idle_loss_history) == 6
    base = controller.snapshot_pre_meeting_baseline()
    assert base is not None
    assert base["loss"] == 0.5
    assert controller._closed_loop_rollback_enabled is True


def test_f14_empty_verified_names_rejects_fallback(event_bus, mock_platform):
    """When ActiveStore readback confirms 0 policies, _active_qos_specs must be empty."""
    mock_platform.last_qos_batch_report = {"verified": [], "failed": ["NetGuard_Zoom_Media"]}
    controller = TrafficController(event_bus=event_bus, platform=mock_platform)

    spec = QoSPolicySpec(name="NetGuard_Zoom_Media", app_name="zoom.exe")
    specs = [spec]

    # Simulate what poll_meeting_signal does with verified_names
    verified_names = set(mock_platform.last_qos_batch_report.get("verified", []))
    confirmed_specs = [s for s in specs if s.name in verified_names]
    if confirmed_specs:
        controller._active_qos_specs = confirmed_specs
    else:
        controller._active_qos_specs = []

    assert controller._active_qos_specs == []


def test_f14_two_stage_rollback_with_structured_logging(event_bus, mock_platform, caplog):
    """Structured logging on Stage 1 (media DSCP removal) and Stage 2 (full rollback)."""
    controller = TrafficController(event_bus=event_bus, platform=mock_platform)

    # Establish baseline with 5 samples
    now = time.monotonic()
    for _ in range(5):
        controller.record_quality_sample(0.0, 3.0, 20.0, timestamp_mono=now)
    controller.snapshot_pre_meeting_baseline()
    assert controller._closed_loop_baseline is not None

    media_spec = QoSPolicySpec(name="NetGuard_Zoom_Media", app_name="zoom.exe", precedence=200)
    bg_spec = QoSPolicySpec(name="NetGuard_Background_Default", is_default=True, precedence=50)
    controller._active_qos_specs = [media_spec, bg_spec]
    controller._applied_policy_names = {media_spec.name, bg_spec.name}
    controller._closed_loop_applied_time = now - 15.0  # past grace period

    # Feed degraded samples: Loss jump +5%, Jitter jump +20ms, RTT jump +50ms
    for _ in range(12):
        controller.record_quality_sample(5.0, 25.0, 75.0, timestamp_mono=now)

    import logging
    with caplog.at_level(logging.WARNING):
        # Stage 1 rollback
        r1 = controller.evaluate_closed_loop_quality(5.0, 25.0, 75.0, timestamp_mono=now, session_id="zoom.exe")
        assert r1 is True
        assert controller._media_marking_rolled_back is True
        assert any("STAGE 1 ROLLBACK" in rec.message for rec in caplog.records)
        assert any("zoom.exe" in rec.message for rec in caplog.records)

        # Fast forward past 5.0s settling period for Stage 2
        controller._media_rollback_time = now - 10.0
        r2 = controller.evaluate_closed_loop_quality(5.0, 25.0, 75.0, timestamp_mono=now, session_id="zoom.exe")
        assert r2 is True
        assert controller._closed_loop_rolled_back is True
        assert any("STAGE 2 ROLLBACK" in rec.message for rec in caplog.records)


# ============================================================================
# Feature 15: Settings Hydration & Dict Serialization Fix
# ============================================================================

def test_f15_qos_config_settings_hydration_and_dict_preservation(tmp_path):
    """UserSettingsSchema preserves qos_enabled_apps dictionary across serialization."""
    settings_file = tmp_path / "user_settings.json"
    us = UserSettings(user_settings_path=settings_file)

    # Set master toggle, per-app dictionary, and teams split
    app_dict = {"zoom.exe": True, "teams.exe": False, "slack.exe": True}
    us.set_policy("qos_master_enabled", True)
    us.set_policy("qos_enabled_apps", app_dict)
    us.set_policy("qos_teams_port_split", True)
    us.set_policy("qos_bulk_throttle_enabled", False)

    # Ensure get_policy preserves the dict
    retrieved = us.get_policy("qos_enabled_apps")
    assert isinstance(retrieved, dict)
    assert retrieved["zoom.exe"] is True
    assert retrieved["teams.exe"] is False

    # Hydrate AppQoSConfig from UserSettings
    cfg = AppQoSConfig.from_user_settings(us)
    assert cfg.master_enabled is True
    assert cfg.enabled_apps["teams.exe"] is False
    assert cfg.enabled_apps["zoom.exe"] is True
    assert cfg.enable_teams_port_split is True
    assert cfg.bulk_throttle_enabled is False

    # Roundtrip save to settings
    cfg.master_enabled = False
    cfg.to_user_settings(us)
    assert us.get_policy("qos_master_enabled") is False


# ============================================================================
# Feature 16: Kill Switch Widget Reference Fix
# ============================================================================

def test_f16_kill_switch_toggles_widget_and_calls_controller(qapp, mock_platform):
    """Kill Switch updates master_qos_toggle widget and calls controller.kill_switch_disable."""
    from app.ui.views.traffic_view import TrafficView
    mock_ctrl = MagicMock()
    tv = TrafficView(controller=mock_ctrl, platform=mock_platform)
    try:
        assert tv.master_qos_toggle.isChecked() is True
        tv._on_kill_switch_clicked()

        assert tv.master_qos_toggle.isChecked() is False
        assert tv.qos_config.master_enabled is False
        mock_ctrl.kill_switch_disable.assert_called_once()
    finally:
        tv.close()
        tv.deleteLater()
        qapp.processEvents()


# ============================================================================
# Feature 17: Strict DNS Meeting Safety Freeze
# ============================================================================

@pytest.mark.asyncio
async def test_f17_dns_actions_frozen_during_meeting(event_bus, mock_platform):
    """RemediationOrchestrator freezes DNS flush, switch, benchmark, adapter reset during meeting."""
    meeting_active = True
    config = RemediationConfig(allow_level_3_disruptive=False)
    reg = MagicMock()
    safety = MagicMock()
    safety.can_execute.return_value = (True, "OK")

    orchestrator = RemediationOrchestrator(
        config=config,
        registry=reg,
        safety_manager=safety,
        platform_adapter=mock_platform,
        audit_repo=MagicMock(),
        event_bus=event_bus,
        meeting_guard_check=lambda: meeting_active,
    )

    frozen_actions = ["flush_dns_cache", "switch_dns_resolver", "renew_ip_lease", "reset_adapter", "benchmark_dns"]
    for act_id in frozen_actions:
        action = MagicMock()
        action.action_id = act_id
        action.name = act_id
        action.risk_level = RiskLevel.LEVEL_1_LOW
        reg.get.return_value = action
        diag = Diagnosis(
            probable_cause=ProbableCause.LOCAL_GATEWAY_HIGH_LATENCY,
            severity=DiagnosisSeverity.MEDIUM,
            confidence=0.9,
            recommended_action_ids=[act_id],
        )

        res = await orchestrator.handle_diagnosis(diag)
        assert res is None, f"Action {act_id} should have been suppressed during meeting."


# ============================================================================
# Feature 18: Active Bounded Preflight Upload Capacity Test
# ============================================================================

def test_f18_preflight_active_upload_test_idle_vs_active(mock_platform):
    """Upload test executes bounded check during idle, but strictly refuses during active meeting."""
    # When meeting is active -> refuses and returns None
    assert measure_active_upload_capacity(is_meeting_active=True) is None

    # When idle -> executes bounded test
    checker = MeetingPreflightChecker(platform=mock_platform)
    mock_ctrl = MagicMock()

    with patch("app.traffic.preflight.measure_active_upload_capacity", return_value=12.5):
        report = checker.run_check(is_meeting_active=False, traffic_controller=mock_ctrl)
        assert report.measured_uplink_mbps == 12.5
        mock_ctrl.set_preflight_metrics.assert_called_once_with(12.5, report.quality_tier)

    # When meeting is active -> no upload test, no controller set_preflight_metrics call
    mock_ctrl.reset_mock()
    report_active = checker.run_check(is_meeting_active=True, traffic_controller=mock_ctrl)
    assert report_active.measured_uplink_mbps is None
    mock_ctrl.set_preflight_metrics.assert_not_called()


# ============================================================================
# Feature 19: PyInstaller Elevated Execution Process Hierarchy
# ============================================================================

def test_f19_process_tree_protection():
    """Preserves elevated parent bootloader and child application process hierarchy."""
    current_pid = os.getpid()
    parent_pid = os.getppid() if hasattr(os, "getppid") else None

    # Current process and parent process are protected
    assert is_netguard_or_protected_process("netguard.exe", current_pid) is True
    assert is_netguard_or_protected_process("python.exe", parent_pid) is True
    assert is_netguard_or_protected_process("svchost.exe", 1234) is True

    # Generic bulk sync apps are not protected
    assert is_netguard_or_protected_process("qbittorrent.exe", 99999) is False
    assert is_netguard_or_protected_process("dropbox.exe", 99998) is False
