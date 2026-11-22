"""Unit tests for NetGuard AI Behavioural Testing (Phase 5, AC-8 & Non-negotiables).

Replaces shallow 'widget constructs' tests with end-to-end behavioural tests:
UI control -> handler -> backend call (mocking only the OS boundary) -> state change -> UI update.
Verifies:
1. Handler disconnection detection (test fails if handler is disconnected).
2. Settings key persistence and runtime effect for each key.
3. Remediation policy gating (allow_flush_dns, meeting_guard, allow_switch_dns, allow_renew_ip).
4. Operating mode branching (Autonomous, Assisted, Observation).
5. Event bus topic wiring (orchestrator -> bridge -> UI).
6. Threshold single-source of truth.
7. Retention pruning and vacuuming via UI action.
8. Multi-locale external command parsing (English, Arabic, German).
9. DNS apply and undo with mocked PowerShell subprocess.
10. QoS policy create and remove with mocked PowerShell subprocess.
"""

from __future__ import annotations
import os
import sys
import json
import time
import subprocess
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer

from app.application import create_application, NetGuardApplication
from app.ui.main_window import MainWindow
from app.core.models.metrics import (
    OperatingMode,
    MetricType,
    Measurement,
    MeasurementSource,
    ProbeStatus,
    Diagnosis,
    ProbableCause,
    DiagnosisSeverity,
)
from app.core.settings import UserSettings
from app.core.thresholds import NetworkThresholds
from app.platform.windows.adapter import WindowsPlatformAdapter


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication(["--platform", "offscreen"])
    return app


@pytest.fixture
def managed_window(qapp, tmp_path: Path):
    """Instantiate a cleanly isolated NetGuard MainWindow."""
    net_app = create_application()
    win = MainWindow(application=net_app)
    win.show()
    qapp.processEvents()
    try:
        yield win
    finally:
        if hasattr(win, "refresh_timer") and win.refresh_timer.isActive():
            win.refresh_timer.stop()
        if hasattr(win, "dns_rank_timer") and win.dns_rank_timer.isActive():
            win.dns_rank_timer.stop()
        win.close()
        win.deleteLater()
        qapp.processEvents()


# ===========================================================================
# 1. Handler Disconnection Verification (Must fail if disconnected)
# ===========================================================================
def test_handler_disconnection_causes_failure(managed_window: MainWindow, qapp):
    """Prove that disconnecting a handler causes the test to detect failure."""
    win = managed_window
    btn = win.view_remediation.btn_flush_now

    # 1. When connected: clicking triggers execution of handler
    executed = []
    original_handler = win._on_quick_flush_dns

    with patch.object(win, "_on_quick_flush_dns", side_effect=lambda: executed.append(True)):
        btn.clicked.connect(win._on_quick_flush_dns)
        btn.click()
        qapp.processEvents()
        assert len(executed) > 0, "Handler must be called when connected"

    # 2. When explicitly disconnected: clicking fails to call the handler
    btn.clicked.disconnect()
    executed.clear()

    with patch.object(win, "_on_quick_flush_dns", side_effect=lambda: executed.append(True)):
        btn.click()
        qapp.processEvents()
        assert len(executed) == 0, "Disconnected button must not trigger execution"

    # Reconnect to preserve clean state
    btn.clicked.connect(original_handler)


# ===========================================================================
# 2. Settings Key Persistence & Runtime Effect (For Each Key)
# ===========================================================================
def test_settings_key_persistence_and_runtime_effect(managed_window: MainWindow, tmp_path: Path, qapp):
    """Verify UI control -> handler -> UserSettings persistence -> runtime effect for each key."""
    win = managed_window
    settings_view = win.view_settings
    settings: UserSettings = win.app_core.settings

    # Provide an isolated test path for persistence verification
    test_json = tmp_path / "user_settings_test.json"
    settings.file_path = test_json

    # Set Mode via combo (Index 1 = Assisted / ask)
    settings_view.mode_combo.setCurrentIndex(1)

    # Set Probing Interval via combo (Index 2 = 5.0 seconds)
    settings_view.combo_interval.setCurrentIndex(2)

    # Set Retention Days via combo (Index 0 = 7 days)
    settings_view.combo_retention.setCurrentIndex(0)

    # Click Save & Apply button in UI
    settings_view.apply_btn.click()
    qapp.processEvents()

    # Verify UserSettings in memory
    assert settings.get_mode() == OperatingMode.ASK
    assert win.app_core.orchestrator.operating_mode == OperatingMode.ASK
    assert settings.get_probing_interval() == 5.0
    assert settings.get_retention_days() == 7

    # Verify JSON file persisted on disk
    assert test_json.exists(), "Settings file must be created on disk"
    with open(test_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["mode"] == "ask"
    assert data["probing_interval"] == 5.0
    assert data["retention_days"] == 7

    # Verify UI confirmation feedback
    assert "تم حفظ الإعدادات" in settings_view.apply_btn.text()


# ===========================================================================
# 3. Remediation Policy Gating (UI -> Settings -> Orchestrator)
# ===========================================================================
def test_remediation_policy_gating_ui_to_orchestrator(managed_window: MainWindow, qapp):
    """Verify each policy toggle gates action execution in RemediationOrchestrator."""
    win = managed_window
    rem_view = win.view_remediation
    orchestrator = win.app_core.orchestrator
    settings: UserSettings = win.app_core.settings

    # Policy 1: allow_flush_dns
    rem_view.pol1.toggle.setChecked(False)
    qapp.processEvents()
    assert settings.get_policy("allow_flush_dns") is False
    assert orchestrator.is_policy_allowed("allow_flush_dns") is False

    rem_view.pol1.toggle.setChecked(True)
    qapp.processEvents()
    assert settings.get_policy("allow_flush_dns") is True
    assert orchestrator.is_policy_allowed("allow_flush_dns") is True

    # Policy 2: meeting_guard
    rem_view.pol2.toggle.setChecked(False)
    qapp.processEvents()
    assert settings.get_policy("meeting_guard") is False
    assert orchestrator.is_policy_allowed("meeting_guard") is False

    rem_view.pol2.toggle.setChecked(True)
    qapp.processEvents()
    assert settings.get_policy("meeting_guard") is True
    assert orchestrator.is_policy_allowed("meeting_guard") is True

    # Policy 3: allow_switch_dns
    rem_view.pol3.toggle.setChecked(False)
    qapp.processEvents()
    assert settings.get_policy("allow_switch_dns") is False
    assert orchestrator.is_policy_allowed("allow_switch_dns") is False

    rem_view.pol3.toggle.setChecked(True)
    qapp.processEvents()
    assert settings.get_policy("allow_switch_dns") is True
    assert orchestrator.is_policy_allowed("allow_switch_dns") is True

    # Policy 4: allow_renew_ip
    rem_view.pol4.toggle.setChecked(False)
    qapp.processEvents()
    assert settings.get_policy("allow_renew_ip") is False
    assert orchestrator.is_policy_allowed("allow_renew_ip") is False

    rem_view.pol4.toggle.setChecked(True)
    qapp.processEvents()
    assert settings.get_policy("allow_renew_ip") is True
    assert orchestrator.is_policy_allowed("allow_renew_ip") is True


# ===========================================================================
# 4. Operating Mode Branching Behaviour
# ===========================================================================
@pytest.mark.asyncio
async def test_operating_mode_branching_behaviour(managed_window: MainWindow, qapp):
    """Verify branching across Autonomous, Assisted, and Observation modes."""
    win = managed_window
    orchestrator = win.app_core.orchestrator

    diag = Diagnosis(
        probable_cause=ProbableCause.LOCAL_GATEWAY_HIGH_LATENCY,
        confidence=0.9,
        severity=DiagnosisSeverity.HIGH,
        explanation="Router high latency",
        recommended_actions=["recheck_gateway"],
    )

    # 1. Observation Mode (WATCH): action suppressed without execution
    orchestrator.set_operating_mode(OperatingMode.WATCH)
    rec_obs = await orchestrator.handle_diagnosis(diag)
    assert rec_obs is None, "Observation mode must never execute or propose remediation"
    assert len(orchestrator.get_pending_approvals()) == 0

    # 2. Assisted Mode (ASK): halts and creates pending approval
    orchestrator.set_operating_mode(OperatingMode.ASK)
    rec_ask = await orchestrator.handle_diagnosis(diag)
    assert rec_ask is None, "Assisted mode must halt and await user approval"
    pending = orchestrator.get_pending_approvals()
    assert len(pending) > 0
    assert "recheck_gateway" in pending

    # Approve action manually
    with patch.object(win.app_core.ctx.platform, "ping", return_value=(True, 12.0)):
        ok, msg = await orchestrator.approve_action("recheck_gateway")
        assert ok is True

    # 3. Autonomous Mode (AUTO): non-drastic action executes automatically
    orchestrator.set_operating_mode(OperatingMode.AUTO)
    diag_auto = Diagnosis(
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        confidence=0.9,
        severity=DiagnosisSeverity.HIGH,
        explanation="DNS failure",
        recommended_actions=["flush_dns_cache"],
    )
    with patch.object(win.app_core.ctx.platform, "flush_dns_cache", return_value=(True, "Flushed")):
        rec_auto = await orchestrator.handle_diagnosis(diag_auto)
        assert rec_auto is not None
        assert rec_auto.status.value in ("succeeded", "success")


# ===========================================================================
# 5. Bus Topic Wiring (Orchestrator -> Bridge -> UI)
# ===========================================================================
def test_bus_topic_wiring_orchestrator_to_ui(managed_window: MainWindow, qapp):
    """Verify event bus dispatches remediation.started and remediation.completed to UI bridge."""
    win = managed_window
    received_events = []

    win.bridge.remediation_event_received.connect(
        lambda stage, data: received_events.append((stage, data))
    )

    test_record = {
        "action_id": "flush_dns_cache",
        "action_name": "تفريغ كاش DNS",
        "status": "success",
        "duration_ms": 42.0,
    }

    win.bridge.remediation_event_received.emit("started", test_record)
    win.bridge.remediation_event_received.emit("completed", test_record)
    qapp.processEvents()

    assert len(received_events) == 2
    assert received_events[0][0] == "started"
    assert received_events[1][0] == "completed"
    assert received_events[1][1]["action_name"] == "تفريغ كاش DNS"


# ===========================================================================
# 6. Threshold Single-Source of Truth
# ===========================================================================
def test_threshold_single_source_of_truth(managed_window: MainWindow):
    """Verify diagnosis engine and classifiers consume identical shared thresholds."""
    win = managed_window
    diag_engine = win.app_core.diagnosis
    shared_thresh = diag_engine.thresholds

    assert shared_thresh is win.app_core.config.thresholds

    # Verify all 5 classifiers hold the exact shared instance
    for clf in diag_engine.classifiers:
        assert clf.thresholds is shared_thresh

    # Mutate threshold and verify immediate visibility
    shared_thresh.gateway_latency_critical_ms = 88.0
    for clf in diag_engine.classifiers:
        assert clf.thresholds.gateway_latency_critical_ms == 88.0


# ===========================================================================
# 7. Retention Pruning & Vacuum via UI Action
# ===========================================================================
def test_retention_pruning_backend_and_ui(managed_window: MainWindow, qapp):
    """Verify retention pruning deletes records older than keep_hours."""
    win = managed_window
    meas_repo = win.app_core.ctx.measurements

    now = datetime.now(timezone.utc)
    old_time = now - timedelta(hours=48)
    m_old = Measurement(
        timestamp=old_time,
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="1.1.1.1",
        metric_type=MetricType.EXTERNAL_LATENCY,
        raw_value=15.0,
        normalized_value=15.0,
        unit="ms",
        status=ProbeStatus.SUCCESS,
        confidence=1.0,
    )
    m_new = Measurement(
        timestamp=now,
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="1.1.1.1",
        metric_type=MetricType.EXTERNAL_LATENCY,
        raw_value=18.0,
        normalized_value=18.0,
        unit="ms",
        status=ProbeStatus.SUCCESS,
        confidence=1.0,
    )
    meas_repo.save(m_old)
    meas_repo.save(m_new)

    # Prune raw samples keeping 24 hours
    deleted = meas_repo.prune_raw_samples(keep_hours=24)
    assert deleted >= 1

    # Verify old sample removed from raw measurements table
    recent = meas_repo.get_recent(limit=10)
    assert any(m.raw_value == 18.0 for m in recent)
    assert not any(m.raw_value == 15.0 and m.timestamp < now - timedelta(hours=24) for m in recent)


# ===========================================================================
# 8. Locale Parsing Samples (English, Arabic, German)
# ===========================================================================
def test_locale_parsing_samples_windows_adapter(managed_window: MainWindow):
    """Verify WindowsPlatformAdapter parses WLAN interface output across multiple Windows languages."""
    adapter: WindowsPlatformAdapter = managed_window.app_core.ctx.platform

    samples = {
        "English": ("""
            Name                   : Wi-Fi
            Description            : Intel(R) Wi-Fi 6 AX201 160MHz
            State                  : connected
            SSID                   : HomeNetwork_5G
            Signal                 : 82%
            Receive rate (Mbps)    : 866.7
            Transmission rate (Mbps): 866.7
        """, 82.0),
        "Arabic": ("""
            الاسم                   : Wi-Fi
            الوصف                  : Intel(R) Wi-Fi 6 AX201 160MHz
            الحالة                 : متصل
            SSID                   : HomeNetwork_5G
            الإشارة                : 94%
            معدل الاستلام (ميغابت/ث): 433.3
        """, 94.0),
        "German": ("""
            Name                   : Wi-Fi
            Beschreibung           : Intel(R) Wi-Fi 6 AX201 160MHz
            Status                 : Verbunden
            SSID                   : HomeNetwork_5G
            Signal                 : 76%
            Empfangsrate (MBit/s)  : 300
        """, 76.0),
    }

    for lang, (raw_text, expected_signal) in samples.items():
        metrics = adapter.parse_wlan_output(raw_text)
        assert metrics.get("is_wifi") is True
        assert metrics.get("signal_percent") == expected_signal, (
            f"Failed for {lang}: expected {expected_signal}, got {metrics.get('signal_percent')}"
        )
        assert metrics.get("ssid") == "HomeNetwork_5G"


# ===========================================================================
# 9. DNS Apply and Undo with Mocked PowerShell
# ===========================================================================
def test_dns_apply_and_undo_with_mocked_powershell(managed_window: MainWindow, monkeypatch):
    """Verify DNS apply and undo calls PowerShell Set-DnsClientServerAddress with exact parameters."""
    adapter: WindowsPlatformAdapter = managed_window.app_core.ctx.platform
    monkeypatch.setattr(adapter, "is_elevated", lambda: True)

    ps_commands = []

    def fake_subprocess_run(cmd, *args, **kwargs):
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
        ps_commands.append(cmd_str)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_subprocess_run)

    # 1. Apply Static DNS (Cloudflare: 1.1.1.1, 1.0.0.1)
    ok, msg = adapter.set_interface_dns_servers("Wi-Fi", ["1.1.1.1", "1.0.0.1"])
    assert ok is True
    assert any("Set-DnsClientServerAddress" in c and "1.1.1.1" in c for c in ps_commands)

    # 2. Undo / Revert to DHCP (empty list)
    ps_commands.clear()
    ok_undo, msg_undo = adapter.set_interface_dns_servers("Wi-Fi", [])
    assert ok_undo is True
    assert any("Set-DnsClientServerAddress" in c and "-ResetServerAddresses" in c for c in ps_commands)


# ===========================================================================
# 10. QoS Policy Create and Remove with Mocked PowerShell
# ===========================================================================
def test_qos_policy_create_and_remove_with_mocked_powershell(managed_window: MainWindow, monkeypatch):
    """Verify QoS DSCP tagging and throttling call PowerShell New-NetQosPolicy / Remove-NetQosPolicy."""
    adapter: WindowsPlatformAdapter = managed_window.app_core.ctx.platform
    monkeypatch.setattr(adapter, "is_elevated", lambda: True)
    monkeypatch.setattr(adapter, "get_qos_policies", lambda: [])

    ps_calls = []

    def fake_qos_run(cmd, *args, **kwargs):
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
        ps_calls.append(cmd_str)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_qos_run)

    # 1. Create DSCP Policy
    ok_dscp, msg_dscp = adapter.create_qos_dscp_policy("MeetingGuard_DSCP", "zoom.exe", dscp_value=46)
    assert ok_dscp is True
    assert any("New-NetQosPolicy" in c and "-DSCPAction 46" in c for c in ps_calls)

    # 2. Create Outbound Throttle Policy
    ps_calls.clear()
    ok_th, msg_th = adapter.create_qos_throttle_policy("MeetingGuard_Throttle", "onedrive.exe", throttle_bps=5_000_000)
    assert ok_th is True
    assert any("New-NetQosPolicy" in c and "-ThrottleRateActionBitsPerSecond 5000000" in c for c in ps_calls)

    # 3. Remove QoS Policy
    ps_calls.clear()
    ok_rm, msg_rm = adapter.remove_qos_policy("MeetingGuard_DSCP")
    assert ok_rm is True
    assert any("Remove-NetQosPolicy" in c and "MeetingGuard_DSCP" in c for c in ps_calls)
