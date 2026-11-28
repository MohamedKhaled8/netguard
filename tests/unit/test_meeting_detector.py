"""Comprehensive Unit Tests for Real UDP Network Send Telemetry and Meeting Detection (Milestone 1).

Covers:
1. Process I/O disk writes alone with 0 outbound UDP sends do NOT trigger meeting detection.
2. Bound UDP sockets with 0 sent bytes do NOT trigger meeting detection.
3. Detector behaves identically with and without pytest in sys.modules (no artificial bypass).
4. Structured diagnostics are populated per cycle (PID, endpoints, rates, confidence, rejection reasons).
5. Fail-closed when real telemetry is unavailable (never falls back to disk I/O).
6. Data-driven generic support via MeetingAppRegistry with safe UDP fallback for unknown apps.
7. Verification of all 7 cataloged meeting apps and dynamic registration.
"""

from __future__ import annotations
import sys
import time
from typing import Dict, List, Any
from unittest.mock import MagicMock, patch

import pytest

from app.traffic.meeting_registry import MeetingAppRegistry, MediaProfile, MeetingAppEntry
from app.traffic.meeting_detector import (
    MeetingDetector,
    MeetingState,
    CandidateEvaluationDiagnostic,
    BaseNetworkTelemetryProvider,
    MockNetworkTelemetryProvider,
    WindowsETWNetworkTelemetry,
    MeetingModeState,
)


# =============================================================================
# 1. HEAVY DISK WRITES DO NOT TRIGGER DETECTION
# =============================================================================

def test_heavy_disk_writes_with_zero_udp_does_not_trigger():
    """Verify that heavy process disk writes alone with 0 outbound UDP sends NEVER trigger meeting detection."""
    mock_telemetry = MockNetworkTelemetryProvider(available=True)
    # Process 4500 is sending 0 UDP bytes
    mock_telemetry.set_pid_rate(4500, rate_bytes_per_sec=0.0, endpoints=["127.0.0.1:8801"])

    detector = MeetingDetector(telemetry_provider=mock_telemetry)

    # Consent is active for zoom.exe
    with patch.object(detector, "check_windows_consent_store_detailed", return_value={"zoom.exe": {"cap": "microphone", "is_active": True}}):
        running = [(4500, "zoom.exe")]
        # Bound UDP socket present
        udp_sockets = {4500}

        in_call = detector.detect_in_call_apps(
            running_procs=running,
            now_t=100.0,
            threshold_bytes_per_sec=2500.0,
            udp_sockets_by_pid=udp_sockets,
        )

        assert len(in_call) == 0, "Meeting must NOT be detected when outbound UDP send rate is 0"

        state = detector.detect_meeting(
            running_procs=running,
            now_t=100.0,
            threshold_bytes_per_sec=2500.0,
            udp_sockets_by_pid=udp_sockets,
        )
        assert state.is_active is False
        assert state.udp_send_bytes_per_sec == 0.0

        # Check structured diagnostic
        diags = detector.get_last_diagnostics()
        assert len(diags) >= 1
        zoom_diag = next(d for d in diags if d.process_name == "zoom.exe")
        assert zoom_diag.is_detected is False
        assert zoom_diag.consent_active is True
        assert zoom_diag.udp_bytes_per_sec == 0.0
        assert zoom_diag.rejection_reason is not None
        assert "insufficient_udp_send_rate" in zoom_diag.rejection_reason


# =============================================================================
# 2. BOUND UDP SOCKETS WITH ZERO SENT BYTES DO NOT TRIGGER DETECTION
# =============================================================================

def test_bound_udp_socket_with_zero_sent_bytes_does_not_trigger():
    """Verify that open/bound UDP sockets with zero actual sent bytes do NOT trigger meeting detection."""
    mock_telemetry = MockNetworkTelemetryProvider(available=True)
    mock_telemetry.set_pid_rate(5200, rate_bytes_per_sec=0.0)

    detector = MeetingDetector(telemetry_provider=mock_telemetry)

    # Consent active for teams.exe
    with patch.object(detector, "check_windows_consent_store_detailed", return_value={"teams.exe": {"cap": "webcam", "is_active": True}}):
        running = [(5200, "teams.exe")]
        udp_sockets = {5200}  # Socket bound

        in_call = detector.detect_in_call_apps(
            running_procs=running,
            now_t=100.0,
            threshold_bytes_per_sec=2500.0,
            udp_sockets_by_pid=udp_sockets,
        )

        assert len(in_call) == 0
        diags = detector.get_last_diagnostics()
        teams_diag = next(d for d in diags if d.process_name == "teams.exe")
        assert teams_diag.is_detected is False
        assert "insufficient_udp_send_rate" in teams_diag.rejection_reason


# =============================================================================
# 3. IDENTICAL BEHAVIOR WITH AND WITHOUT PYTEST IN SYS.MODULES
# =============================================================================

def test_identical_behavior_with_and_without_pytest_in_sys_modules():
    """Verify that detector executes identical logic regardless of whether pytest is imported."""
    mock_telemetry = MockNetworkTelemetryProvider(available=True)
    detector = MeetingDetector(telemetry_provider=mock_telemetry)

    consent_map = {"zoom.exe": {"cap": "microphone", "is_active": True}}
    running = [(6001, "zoom.exe")]
    udp_sockets = {6001}

    # Case A: Outbound UDP rate is 0.0
    mock_telemetry.set_pid_rate(6001, rate_bytes_per_sec=0.0)

    # Run with pytest in sys.modules
    assert "pytest" in sys.modules
    with patch.object(detector, "check_windows_consent_store_detailed", return_value=consent_map):
        res_with_pytest = detector.detect_in_call_apps(running_procs=running, now_t=100.0, udp_sockets_by_pid=udp_sockets)
        diag_with_pytest = detector.get_last_diagnostics()

    # Run without pytest in sys.modules (temporarily remove)
    pytest_mod = sys.modules.pop("pytest", None)
    try:
        assert "pytest" not in sys.modules
        with patch.object(detector, "check_windows_consent_store_detailed", return_value=consent_map):
            res_without_pytest = detector.detect_in_call_apps(running_procs=running, now_t=100.0, udp_sockets_by_pid=udp_sockets)
            diag_without_pytest = detector.get_last_diagnostics()
    finally:
        if pytest_mod is not None:
            sys.modules["pytest"] = pytest_mod

    assert len(res_with_pytest) == len(res_without_pytest) == 0
    assert diag_with_pytest[0].is_detected == diag_without_pytest[0].is_detected is False
    assert diag_with_pytest[0].udp_bytes_per_sec == diag_without_pytest[0].udp_bytes_per_sec == 0.0

    # Case B: Outbound UDP rate is 30,000.0 (active call)
    mock_telemetry.set_pid_rate(6001, rate_bytes_per_sec=30000.0, endpoints=["144.195.27.125:8801"])

    with patch.object(detector, "check_windows_consent_store_detailed", return_value=consent_map):
        active_with_pytest = detector.detect_in_call_apps(running_procs=running, now_t=101.0, udp_sockets_by_pid=udp_sockets)

    pytest_mod = sys.modules.pop("pytest", None)
    try:
        with patch.object(detector, "check_windows_consent_store_detailed", return_value=consent_map):
            active_without_pytest = detector.detect_in_call_apps(running_procs=running, now_t=101.0, udp_sockets_by_pid=udp_sockets)
    finally:
        if pytest_mod is not None:
            sys.modules["pytest"] = pytest_mod

    assert len(active_with_pytest) == len(active_without_pytest) == 1
    assert active_with_pytest[0][1] == active_without_pytest[0][1] == "zoom.exe"


# =============================================================================
# 4. STRUCTURED PER-CYCLE DIAGNOSTICS
# =============================================================================

def test_structured_diagnostics_populated_correctly():
    """Verify structured diagnostics include PID, process, app ID, endpoints, UDP rates, confidence, rejection reasons."""
    mock_telemetry = MockNetworkTelemetryProvider(available=True)
    # Zoom: active mic and high UDP sends on media port 8801
    mock_telemetry.set_pid_rate(1001, rate_bytes_per_sec=40000.0, endpoints=["144.195.27.125:8801"])
    # Teams: active mic, but 0 UDP sends
    mock_telemetry.set_pid_rate(1002, rate_bytes_per_sec=0.0, endpoints=["0.0.0.0:50000"])
    # Slack: high UDP sends, but NO mic/cam consent
    mock_telemetry.set_pid_rate(1003, rate_bytes_per_sec=15000.0, endpoints=["52.1.2.3:443"])

    detector = MeetingDetector(telemetry_provider=mock_telemetry)

    consent_map = {
        "zoom.exe": {"cap": "microphone", "is_active": True},
        "teams.exe": {"cap": "microphone", "is_active": True},
    }

    running = [
        (1001, "zoom.exe"),
        (1002, "teams.exe"),
        (1003, "slack.exe"),
    ]
    udp_sockets = {1001, 1002, 1003}

    with patch.object(detector, "check_windows_consent_store_detailed", return_value=consent_map):
        in_call = detector.detect_in_call_apps(running_procs=running, now_t=100.0, udp_sockets_by_pid=udp_sockets)
        state = detector.detect_meeting(running_procs=running, now_t=100.0, udp_sockets_by_pid=udp_sockets)

    assert len(in_call) == 1
    assert in_call[0][1] == "zoom.exe"

    diags = detector.get_last_diagnostics()
    assert len(diags) == 3

    diag_map = {d.process_name: d for d in diags}

    # Verify Zoom diagnostic
    z = diag_map["zoom.exe"]
    assert z.pid == 1001
    assert z.app_id == "zoom"
    assert z.is_detected is True
    assert z.consent_active is True
    assert z.udp_bytes_per_sec == 40000.0
    assert "144.195.27.125:8801" in z.endpoints
    assert z.confidence >= 0.90  # Known port bonus + high rate bonus
    assert z.rejection_reason is None

    # Verify Teams diagnostic
    t = diag_map["teams.exe"]
    assert t.pid == 1002
    assert t.app_id == "teams"
    assert t.is_detected is False
    assert t.consent_active is True
    assert t.udp_bytes_per_sec == 0.0
    assert "insufficient_udp_send_rate" in t.rejection_reason

    # Verify Slack diagnostic
    s = diag_map["slack.exe"]
    assert s.pid == 1003
    assert s.app_id == "slack"
    assert s.is_detected is False
    assert s.consent_active is False
    assert s.rejection_reason == "no_microphone_or_camera_consent"

    # Verify MeetingState synchronization
    assert state.is_active is True
    assert state.process_name == "zoom.exe"
    assert state.udp_send_bytes_per_sec == 40000.0
    assert "144.195.27.125:8801" in state.endpoints
    assert state.confidence == z.confidence



# =============================================================================
# 5. FAIL CLOSED WHEN TELEMETRY UNAVAILABLE
# =============================================================================

def test_fail_closed_when_telemetry_unavailable():
    """Verify that when real telemetry is unavailable (non-admin/unsupported), detector fails closed."""
    # Telemetry unavailable
    mock_telemetry = MockNetworkTelemetryProvider(available=False)
    detector = MeetingDetector(telemetry_provider=mock_telemetry)

    # Even with active consent and running zoom process
    consent_map = {"zoom.exe": {"cap": "microphone", "is_active": True}}
    running = [(1001, "zoom.exe")]
    udp_sockets = {1001}

    with patch.object(detector, "check_windows_consent_store_detailed", return_value=consent_map):
        in_call = detector.detect_in_call_apps(running_procs=running, now_t=100.0, udp_sockets_by_pid=udp_sockets)

    assert len(in_call) == 0, "Must fail closed when telemetry is unavailable"
    diags = detector.get_last_diagnostics()
    assert len(diags) == 1
    assert diags[0].is_detected is False
    assert diags[0].udp_bytes_per_sec == 0.0
    assert diags[0].rejection_reason == "telemetry_unavailable"

    # Also test check_process_sustained_outbound_udp directly
    sustained, rate = detector.check_process_sustained_outbound_udp(pids=[1001], now_t=100.0)
    assert sustained is False
    assert rate == 0.0


# =============================================================================
# 6. DATA-DRIVEN GENERIC FALLBACK FOR UNKNOWN MEETING APPS
# =============================================================================

def test_data_driven_generic_fallback_for_unknown_meeting_app():
    """Verify that unknown meeting applications are detected via ConsentStore with safe UDP fallback."""
    mock_telemetry = MockNetworkTelemetryProvider(available=True)
    # Unknown VoIP app: anycall.exe sending sustained UDP
    mock_telemetry.set_pid_rate(7777, rate_bytes_per_sec=32000.0, endpoints=["198.51.100.50:5004"])

    detector = MeetingDetector(telemetry_provider=mock_telemetry)

    # Consent store shows anycall.exe actively capturing audio
    consent_map = {"anycall.exe": {"cap": "microphone", "is_active": True}}
    running = [(7777, "anycall.exe")]
    udp_sockets = {7777}

    with patch.object(detector, "check_windows_consent_store_detailed", return_value=consent_map):
        in_call = detector.detect_in_call_apps(running_procs=running, now_t=100.0, udp_sockets_by_pid=udp_sockets)

    assert len(in_call) == 1
    entry, exe_name, pid = in_call[0]
    assert exe_name == "anycall.exe"
    assert pid == 7777
    assert entry.id == "anycall"
    assert entry.media_profile.has_known_ports is False
    assert entry.media_profile.default_dscp == 34  # Safe AF41 fallback

    diags = detector.get_last_diagnostics()
    assert len(diags) == 1
    d = diags[0]
    assert d.is_detected is True
    assert d.app_id == "anycall"
    assert d.udp_bytes_per_sec == 32000.0
    assert "198.51.100.50:5004" in d.endpoints


# =============================================================================
# 7. REGISTRY ENTRIES & FALLBACK CREATION
# =============================================================================

def test_meeting_app_registry_catalog_and_fallback_helpers():
    """Verify MeetingAppRegistry contains all 7 cataloged apps and provides fallback factories."""
    entries = MeetingAppRegistry.all_entries()
    entry_ids = {e.id for e in entries}

    expected_ids = {"zoom", "teams", "browsers", "slack", "discord", "skype", "webex"}
    assert expected_ids.issubset(entry_ids)

    # Check fallback creation helper
    fallback = MeetingAppRegistry.create_fallback_entry("custom_app", display_name="Custom App", default_dscp=34)
    assert fallback.id == "custom_app"
    assert fallback.display_name == "Custom App"
    assert fallback.media_profile.has_known_ports is False
    assert fallback.media_profile.default_dscp == 34

    # Check find_or_create_entry helper
    found = MeetingAppRegistry.find_or_create_entry("zoom.exe")
    assert found.id == "zoom"

    created = MeetingAppRegistry.find_or_create_entry("brand_new_meeting.exe")
    assert created.id == "brand_new_meeting"
    assert created.media_profile.default_dscp == 34


# =============================================================================
# 8. ETW PROVIDER CLASS AND ROBUST LIFECYCLE
# =============================================================================

def test_etw_provider_safe_instantiation_and_lifecycle():
    """Verify WindowsETWNetworkTelemetry can be safely instantiated and closed."""
    etw = WindowsETWNetworkTelemetry()
    # In non-elevated environment, available should be False (failing closed)
    if sys.platform == "win32":
        # Check endpoints discovery without throwing
        endpoints = etw.get_process_udp_endpoints(1)
        assert isinstance(endpoints, list)

        rate, eps = etw.get_outbound_udp_rate([1], time.monotonic())
        if not etw.is_available():
            assert rate == 0.0

    # Ensure clean close
    etw.close()
    assert etw.is_available() is False
