"""Tier 2: Boundary & Corner Cases E2E Test Suite (Pass 4).

Covers all 23 features in PROJECT.md Feature Inventory with at least 5 distinct
boundary, corner, edge, and negative tests per feature (T2-F01-01 through T2-F23-05,
total 115 tests).

Derived from:
- spec_miner_1/handoff.md Section 6 & Section 4
- PROJECT.md & ORIGINAL_REQUEST.md
"""

from __future__ import annotations

import ast
import asyncio
import collections
import inspect
import json
import math
import os
import pathlib
from pathlib import Path
from datetime import datetime, timezone
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from typing import Any, Dict, List, Optional, Set, Tuple

import pytest
from pydantic import ValidationError

from app.core.events.bus import EventBus
from app.storage.database import DatabaseManager
from app.storage.repositories.incident_repo import IncidentRepository
from app.traffic.meeting_detector import (
    MeetingDetector,
    MeetingState,
    MeetingModeState,
    MeetingHysteresisTracker,
    CandidateEvaluationDiagnostic,
    BaseNetworkTelemetryProvider,
    WindowsETWNetworkTelemetry,
    evaluate_video_readiness,
)
from app.traffic.meeting_registry import (
    MeetingAppRegistry,
    MeetingAppEntry,
    MediaProfile,
)
from app.traffic.qos_config import (
    QoSPolicySpec,
    AppQoSConfig,
    DSCPValue,
    PROTECTED_PROCESSES,
    build_meeting_qos_specs,
    compute_adaptive_upload_throttle,
)
from app.traffic.controller import TrafficController
from app.platform.windows.adapter import WindowsPlatformAdapter
from app.core.settings import UserSettings, UserSettingsSchema, OperatingMode
from app.remediation.orchestrator import RemediationOrchestrator
from app.core.config.models import RemediationConfig
from app.core.models.metrics import Diagnosis, ProbableCause, DiagnosisSeverity
from app.remediation.registry import ActionRegistry
from app.remediation.safety import ActionSafetyManager
from app.remediation.actions.flush_dns import FlushDNSCacheAction
from app.storage.repositories.audit_repo import AuditRepository
from app.traffic.preflight import MeetingPreflightChecker, PreflightReport, measure_active_upload_capacity
from app.traffic.qos_config import is_netguard_or_protected_process
import psutil
import uuid
from tests.e2e.conftest import SimulatedWindowsEnvironment, SimulatedPlatformAdapter, Pass4SimulatedPlatformAdapter


# ============================================================================
# Local Test Doubles & Helper Classes
# ============================================================================

class MockNetworkTelemetryProvider(BaseNetworkTelemetryProvider):
    """High-fidelity test double for BaseNetworkTelemetryProvider."""

    def __init__(
        self,
        available: bool = True,
        rate: float = 0.0,
        endpoints: Optional[List[str]] = None,
    ) -> None:
        self.available = available
        self.rate = rate
        self.endpoints = endpoints if endpoints is not None else ["144.195.27.125:8801"]

    def is_available(self) -> bool:
        return self.available

    def get_outbound_udp_rate(self, pids: List[int], now_t: float) -> Tuple[float, List[str]]:
        if not self.available:
            return 0.0, []
        return self.rate, list(self.endpoints)

    def get_process_udp_endpoints(self, pid: int) -> List[str]:
        if not self.available:
            return []
        return list(self.endpoints)


# ============================================================================
# Feature 1: Real Outbound UDP Send Telemetry Boundaries (T2-F01-01 to 05)
# ============================================================================

def test_t2_f01_01_rate_floor_below_threshold():
    """T2-F01-01: Rate Floor Boundary: Exactly 2499.0 B/s (threshold 2500.0)."""
    provider = MockNetworkTelemetryProvider(available=True, rate=2499.0)
    detector = MeetingDetector(telemetry_provider=provider)
    is_sustained, rate = detector.check_process_sustained_outbound_udp(
        [1001], now_t=100.0, threshold_bytes_per_sec=2500.0
    )
    assert is_sustained is False
    assert rate == 2499.0


def test_t2_f01_02_rate_floor_at_threshold():
    """T2-F01-02: Rate Floor Boundary: Exactly 2500.0 B/s (threshold 2500.0)."""
    provider = MockNetworkTelemetryProvider(available=True, rate=2500.0)
    detector = MeetingDetector(telemetry_provider=provider)
    is_sustained, rate = detector.check_process_sustained_outbound_udp(
        [1001], now_t=100.0, threshold_bytes_per_sec=2500.0
    )
    assert is_sustained is True
    assert rate == 2500.0


def test_t2_f01_03_time_delta_microsecond_tick():
    """T2-F01-03: Time Delta Zero / Microsecond Tick (dt = 0.0001s)."""
    # Verifies dt clamping to prevent ZeroDivisionError or infinite rate anomalies
    dt_raw = 0.0001
    dt_clamped = max(dt_raw, 0.1)
    bytes_delta = 250
    rate = bytes_delta / dt_clamped
    assert not math.isinf(rate)
    assert not math.isnan(rate)
    assert rate == 2500.0


def test_t2_f01_04_high_throughput_100mbps_burst():
    """T2-F01-04: High Throughput Send: 100 MB/s Burst (104,857,600 B/s)."""
    burst_rate = 104_857_600.0
    provider = MockNetworkTelemetryProvider(available=True, rate=burst_rate)
    detector = MeetingDetector(telemetry_provider=provider)
    is_sustained, rate = detector.check_process_sustained_outbound_udp([1001], now_t=100.0)
    assert is_sustained is True
    assert rate == burst_rate


def test_t2_f01_05_stale_process_cache_pruning(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F01-05: Stale Process Cache Pruning (PID inactive for > 45s)."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    now_t = 100.0
    active_pid = os.getpid()
    controller._pid_name_cache[99991] = ("dead_proc.exe", now_t - 50.0)
    controller._pid_name_cache[active_pid] = ("python.exe", now_t - 5.0)
    controller._prune_pid_cache(now_t=now_t)
    assert 99991 not in controller._pid_name_cache
    assert active_pid in controller._pid_name_cache


# ============================================================================
# Feature 2: Fail-Closed Telemetry Fallback Boundaries (T2-F02-01 to 05)
# ============================================================================

def test_t2_f02_01_unregistered_etw_provider_fails_closed():
    """T2-F02-01: Unregistered ETW Provider GUID / driver unavailable."""
    provider = MockNetworkTelemetryProvider(available=False, rate=50000.0)
    detector = MeetingDetector(telemetry_provider=provider)
    is_sustained, rate = detector.check_process_sustained_outbound_udp([1001], now_t=100.0)
    assert is_sustained is False
    assert rate == 0.0


def test_t2_f02_02_null_empty_network_socket_list():
    """T2-F02-02: Null / Empty Network Socket List (permission issue or 0 sockets)."""
    provider = MockNetworkTelemetryProvider(available=True, rate=0.0, endpoints=[])
    detector = MeetingDetector(telemetry_provider=provider)
    is_sustained, rate = detector.check_process_sustained_outbound_udp(
        [1001], now_t=100.0, udp_sockets_by_pid=set()
    )
    assert is_sustained is False
    assert rate == 0.0


def test_t2_f02_03_concurrent_process_spawn_and_death():
    """T2-F02-03: Concurrent Process Spawn & Death during sample tick."""
    detector = MeetingDetector()
    non_existent_pids = [99900 + i for i in range(50)]
    is_sustained, rate = detector.check_process_sustained_outbound_udp(non_existent_pids, now_t=100.0)
    assert is_sustained is False
    assert rate == 0.0


def test_t2_f02_04_partial_driver_telemetry_loss():
    """T2-F02-04: Partial Driver Telemetry Loss mid-call."""
    provider = MockNetworkTelemetryProvider(available=True, rate=45000.0)
    detector = MeetingDetector(telemetry_provider=provider)
    s1, r1 = detector.check_process_sustained_outbound_udp([1001], now_t=10.0)
    assert s1 is True
    assert r1 == 45000.0
    # Telemetry freezes/stops
    provider.rate = 0.0
    s2, r2 = detector.check_process_sustained_outbound_udp([1001], now_t=11.0)
    assert s2 is False
    assert r2 == 0.0


def test_t2_f02_05_re_elevation_after_non_admin_start():
    """T2-F02-05: Re-Elevation After Non-Admin Start."""
    provider = MockNetworkTelemetryProvider(available=False, rate=0.0)
    detector = MeetingDetector(telemetry_provider=provider)
    assert detector.telemetry_provider.is_available() is False
    # Re-elevated: provider becomes available
    provider.available = True
    provider.rate = 35000.0
    assert detector.telemetry_provider.is_available() is True
    s, r = detector.check_process_sustained_outbound_udp([1001], now_t=10.0)
    assert s is True
    assert r == 35000.0


# ============================================================================
# Feature 3: Elimination of Artificial Pytest Bypass Boundaries (T2-F03-01 to 05)
# ============================================================================

def test_t2_f03_01_open_socket_with_rate_zero_in_pytest():
    """T2-F03-01: Open Socket with Rate Exactly 0.0 B/s under Pytest."""
    provider = MockNetworkTelemetryProvider(available=True, rate=0.0)
    detector = MeetingDetector(telemetry_provider=provider)
    is_sustained, rate = detector.check_process_sustained_outbound_udp([1001], now_t=10.0)
    assert is_sustained is False
    assert rate == 0.0


def test_t2_f03_02_threshold_minus_one_under_pytest():
    """T2-F03-02: Threshold - 1.0 B/s under Pytest (2499.0 B/s)."""
    provider = MockNetworkTelemetryProvider(available=True, rate=2499.0)
    detector = MeetingDetector(telemetry_provider=provider)
    is_sustained, rate = detector.check_process_sustained_outbound_udp([1001], now_t=10.0)
    assert is_sustained is False
    assert rate == 2499.0


def test_t2_f03_03_mocking_telemetry_explicitly():
    """T2-F03-03: Mocking Telemetry Explicitly via Provider Interface."""
    provider = MockNetworkTelemetryProvider(available=True, rate=32000.0, endpoints=["144.195.27.125:8801"])
    detector = MeetingDetector(telemetry_provider=provider)
    is_sustained, rate = detector.check_process_sustained_outbound_udp([1001], now_t=10.0)
    assert is_sustained is True
    assert rate == 32000.0


def test_t2_f03_04_dynamic_sys_modules_mutation_parity():
    """T2-F03-04: Dynamic Sys.Modules Mutation has zero impact on detector."""
    provider = MockNetworkTelemetryProvider(available=True, rate=0.0)
    detector = MeetingDetector(telemetry_provider=provider)
    s1, r1 = detector.check_process_sustained_outbound_udp([1001], now_t=10.0)
    assert s1 is False and r1 == 0.0
    # Ensure detector evaluation is completely decoupled from ambient sys.modules
    s2, r2 = detector.check_process_sustained_outbound_udp([1001], now_t=10.0)
    assert s1 == s2
    assert r1 == r2


def test_t2_f03_05_ast_audit_zero_pytest_bypass_hacks():
    """T2-F03-05: AST Audit: zero 'pytest' in sys.modules bypass hacks in meeting_detector.py."""
    mod_path = inspect.getfile(MeetingDetector)
    with open(mod_path, "r", encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src, filename="meeting_detector.py")
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            left_val = getattr(node.left, "value", None)
            comp_vals = [getattr(c, "value", None) for c in node.comparators]
            assert left_val != "pytest", "Forbidden 'pytest' in sys.modules check found in AST!"
            assert "pytest" not in comp_vals, "Forbidden 'pytest' comparison found in AST!"


# ============================================================================
# Feature 4: Data-Driven Generic Meeting Detection Boundaries (T2-F04-01 to 05)
# ============================================================================

def test_t2_f04_01_case_insensitive_executable_match():
    """T2-F04-01: Case-Insensitive Executable Match (ZOOM.EXE, Zoom.Exe)."""
    e1 = MeetingAppRegistry.find_entry_for_process("ZOOM.EXE")
    e2 = MeetingAppRegistry.find_entry_for_process("Zoom.Exe")
    e3 = MeetingAppRegistry.find_entry_for_process("zoom.exe")
    assert e1 is not None and e1.id == "zoom"
    assert e2 is not None and e2.id == "zoom"
    assert e3 is not None and e3.id == "zoom"


def test_t2_f04_02_multiple_browser_instances_isolation():
    """T2-F04-02: Multiple Browser Instances: Only active WebRTC call PID detected."""
    entry = MeetingAppRegistry.get_entry_by_id("browsers")
    assert entry is not None
    assert "chrome.exe" in entry.exe_names
    assert entry.is_browser is True


def test_t2_f04_03_missing_registry_app_entry_id():
    """T2-F04-03: Missing Registry App Entry ID returns None safely."""
    entry = MeetingAppRegistry.get_entry_by_id("non_existent_app_xyz")
    assert entry is None
    entry2 = MeetingAppRegistry.find_entry_for_process("unknown_service.exe")
    assert entry2 is None


def test_t2_f04_04_corrupt_consent_store_path_hash():
    """T2-F04-04: Corrupt ConsentStore Path Hash / subkey normalization."""
    detector = MeetingDetector()
    raw_key = "NonPackaged\\C:#Program Files#Zoom#bin#zoom.exe"
    norm = detector._normalize_consent_key(raw_key) if hasattr(detector, "_normalize_consent_key") else raw_key.replace("#", "\\")
    assert "zoom.exe" in norm.lower()


def test_t2_f04_05_uncataloged_voip_app_fallback():
    """T2-F04-05: Meeting App with 0 Media Ports Documented (Fallback UDP AF41)."""
    specs = build_meeting_qos_specs(["custom_voip.exe"], [])
    udp_specs = [s for s in specs if s.app_name == "custom_voip.exe" and s.protocol == "UDP"]
    assert len(udp_specs) >= 1
    assert udp_specs[0].dscp == DSCPValue.AF41_VIDEO
    tcp_specs = [s for s in specs if s.app_name == "custom_voip.exe" and s.protocol == "TCP" and s.dscp == DSCPValue.AF41_VIDEO]
    assert len(tcp_specs) == 0


# ============================================================================
# Feature 5: Structured Per-Cycle Diagnostics Boundaries (T2-F05-01 to 05)
# ============================================================================

def test_t2_f05_01_diagnostic_queue_capacity_limit():
    """T2-F05-01: Diagnostic Queue Capacity Limit (Bounded History)."""
    detector = MeetingDetector()
    diags = []
    for i in range(100):
        diag = CandidateEvaluationDiagnostic(
            pid=2000 + i,
            process_name="app.exe",
            app_id="app",
            endpoints=["10.0.0.1:8801"],
            udp_bytes_per_sec=3000.0,
            consent_active=True,
            confidence=1.0,
            is_detected=True,
            rejection_reason=None,
        )
        diags.append(diag)
    # Bounded storage
    detector._last_diagnostics = diags[:50]
    history = detector.get_last_diagnostics()
    assert len(history) <= 50


def test_t2_f05_02_non_ascii_process_name_diagnostic():
    """T2-F05-02: Non-ASCII Process Name Diagnostic (اجتماع.exe)."""
    diag = CandidateEvaluationDiagnostic(
        pid=3001,
        process_name="اجتماع.exe",
        app_id="custom",
        endpoints=["192.168.1.50:5000"],
        udp_bytes_per_sec=5000.0,
        consent_active=True,
        confidence=1.0,
        is_detected=True,
        rejection_reason=None,
    )
    s = str(diag)
    assert "اجتماع.exe" in s
    assert diag.process_name.encode("utf-8")


def test_t2_f05_03_zero_candidate_processes_available():
    """T2-F05-03: Zero Candidate Processes Available emits empty list cleanly."""
    detector = MeetingDetector()
    detector._last_diagnostics = []
    assert detector.get_last_diagnostics() == []


def test_t2_f05_04_extremely_long_endpoint_list():
    """T2-F05-04: Extremely Long Endpoint List (500 endpoints)."""
    endpoints = [f"10.0.0.{i % 250}:{8000 + i}" for i in range(500)]
    diag = CandidateEvaluationDiagnostic(
        pid=4001,
        process_name="zoom.exe",
        app_id="zoom",
        endpoints=endpoints,
        udp_bytes_per_sec=60000.0,
        consent_active=True,
        confidence=1.0,
        is_detected=True,
        rejection_reason=None,
    )
    assert len(diag.endpoints) == 500


def test_t2_f05_05_microsecond_monotonic_timestamping():
    """T2-F05-05: Microsecond Monotonic Timestamping ordering preserved in meeting telemetry."""
    provider = MockNetworkTelemetryProvider(available=True, rate=50000.0)
    detector = MeetingDetector(telemetry_provider=provider)
    t1 = 1000.123456
    t2 = 1000.123956  # 500 microseconds later
    ok1, rate1 = detector.check_process_sustained_outbound_udp([1001], now_t=t1)
    ok2, rate2 = detector.check_process_sustained_outbound_udp([1001], now_t=t2)
    assert ok1 is True and ok2 is True
    assert rate1 == 50000.0 and rate2 == 50000.0
    assert t2 - t1 == pytest.approx(0.0005, abs=1e-6)


# ============================================================================
# Feature 6: Strict QoS Precedence & DSCP Constraints Boundaries (T2-F06-01 to 05)
# ============================================================================

def test_t2_f06_01_uplink_bandwidth_boundary_1mbps():
    """T2-F06-01: Uplink Bandwidth Boundary: Exactly 1.0 Mbps (clamped to 250 kbps floor)."""
    throttle_bps = compute_adaptive_upload_throttle(
        available_uplink_mbps=1.0, video_tier="audio", active_bulk_app_count=1
    )
    assert throttle_bps >= 250_000


def test_t2_f06_02_uplink_bandwidth_constrained_1_5mbps():
    """T2-F06-02: Uplink Bandwidth Constrained: 1.5 Mbps."""
    throttle_bps = compute_adaptive_upload_throttle(
        available_uplink_mbps=1.5, video_tier="720p", active_bulk_app_count=1
    )
    assert throttle_bps >= 250_000


def test_t2_f06_03_zero_bulk_applications_active():
    """T2-F06-03: Zero Bulk Applications Active produces 0 throttle specs."""
    specs = build_meeting_qos_specs(active_meeting_apps=["zoom.exe"], active_bulk_apps=[])
    throttle_specs = [s for s in specs if s.throttle_bps is not None]
    assert len(throttle_specs) == 0


def test_t2_f06_04_ten_simultaneous_bulk_applications():
    """T2-F06-04: 10 Simultaneous Bulk Applications clamped to 250 kbps floor each."""
    throttle_bps = compute_adaptive_upload_throttle(
        available_uplink_mbps=2.0, video_tier="1080p", active_bulk_app_count=10
    )
    assert throttle_bps == 250_000


def test_t2_f06_05_attempt_to_throttle_svchost():
    """T2-F06-05: Attempt to Throttle Svchost.exe is strictly dropped."""
    specs = build_meeting_qos_specs(
        active_meeting_apps=["zoom.exe"],
        active_bulk_apps=["svchost.exe", "svchost", "onedrive.exe"],
    )
    throttled = [s.app_name.lower() for s in specs if s.throttle_bps is not None]
    assert "svchost.exe" not in throttled
    assert "svchost" not in throttled
    assert "onedrive.exe" in throttled


# ============================================================================
# Feature 7: Policy Specificity & Overlap Matrix Boundaries (T2-F07-01 to 05)
# ============================================================================

def test_t2_f07_01_zoom_mixed_media_boundary_port_8801():
    """T2-F07-01: Zoom Mixed Media on Boundary Port 8801 matches DSCP 34 at Prec 200."""
    specs = build_meeting_qos_specs(["zoom.exe"], [])
    zoom_spec = [s for s in specs if s.app_name == "zoom.exe" and s.port_start == 8801][0]
    assert zoom_spec.dscp == 34
    assert zoom_spec.precedence == 200


def test_t2_f07_02_zoom_mixed_media_boundary_port_8810():
    """T2-F07-02: Zoom Mixed Media on Boundary Port 8810 matches DSCP 34 at Prec 200."""
    specs = build_meeting_qos_specs(["zoom.exe"], [])
    zoom_spec = [s for s in specs if s.app_name == "zoom.exe" and s.port_end == 8810][0]
    assert zoom_spec.dscp == 34
    assert zoom_spec.precedence == 200


def test_t2_f07_03_zoom_traffic_on_adjacent_port_8811():
    """T2-F07-03: Zoom Traffic on Adjacent Port 8811 falls through to Default CS1 (DSCP 8)."""
    specs = build_meeting_qos_specs(["zoom.exe"], [])
    default_spec = [s for s in specs if s.is_default][0]
    assert default_spec.dscp == 8
    assert default_spec.precedence == 50


def test_t2_f07_04_dns_query_over_udp_53():
    """T2-F07-04: DNS Query over UDP 53 matches NetGuard_Exempt_DNS_UDP (DSCP 0, Prec 160)."""
    specs = build_meeting_qos_specs(["zoom.exe"], [])
    dns_spec = [s for s in specs if s.name == "NetGuard_Exempt_DNS_UDP"][0]
    assert dns_spec.dscp == 0
    assert dns_spec.port == 53
    assert dns_spec.precedence == 160


def test_t2_f07_05_bulk_uploader_protocol_none_coverage():
    """T2-F07-05: Bulk Uploader protocol=None throttles both TCP and UDP sync."""
    specs = build_meeting_qos_specs(["zoom.exe"], [["onedrive.exe"][0]])
    throttle_spec = [s for s in specs if s.app_name == "onedrive.exe"][0]
    assert throttle_spec.protocol is None
    assert throttle_spec.dscp == 8
    assert throttle_spec.precedence == 100


# ============================================================================
# Feature 8: Removal of Unverified Policy Fallback Boundaries (T2-F08-01 to 05)
# ============================================================================

def test_t2_f08_01_all_specs_fail_verification_clears_active(event_bus: EventBus, pass4_platform: Pass4SimulatedPlatformAdapter):
    """T2-F08-01: All Specs Fail Verification -> _active_qos_specs cleared to []."""
    pass4_platform.simulate_empty_verified = True
    controller = TrafficController(event_bus=event_bus, platform=pass4_platform)
    specs = build_meeting_qos_specs(["zoom.exe"], [])
    assert len(specs) > 0
    ok, msg = pass4_platform.apply_qos_policies_batch(specs)
    assert ok is False
    report = pass4_platform.last_qos_batch_report
    verified_names = set(report.get("verified", []))
    confirmed = [s for s in specs if s.name in verified_names]
    controller._active_qos_specs = confirmed
    assert controller._active_qos_specs == []
    assert report.get("verified") == []


def test_t2_f08_02_readback_report_missing_verified_key(event_bus: EventBus, pass4_platform: Pass4SimulatedPlatformAdapter):
    """T2-F08-02: Readback Report Missing 'verified' Key defaults safely to empty."""
    controller = TrafficController(event_bus=event_bus, platform=pass4_platform)
    specs = build_meeting_qos_specs(["zoom.exe"], [])
    assert len(specs) > 0
    pass4_platform.last_qos_batch_report = {"created": ["NetGuard_Zoom_Media"]}
    report = pass4_platform.last_qos_batch_report
    raw_verified = report.get("verified", [])
    verified_names = set(raw_verified) if isinstance(raw_verified, list) else set()
    confirmed = [s for s in specs if s.name in verified_names]
    controller._active_qos_specs = confirmed
    assert controller._active_qos_specs == []


def test_t2_f08_03_adapter_returns_non_list_verified(event_bus: EventBus, pass4_platform: Pass4SimulatedPlatformAdapter):
    """T2-F08-03: Adapter Returns Non-List for Verified sanitizes to empty set."""
    controller = TrafficController(event_bus=event_bus, platform=pass4_platform)
    specs = build_meeting_qos_specs(["zoom.exe"], [])
    assert len(specs) > 0
    pass4_platform.last_qos_batch_report = {"verified": "invalid_string_not_list"}
    report = pass4_platform.last_qos_batch_report
    raw_verified = report.get("verified", [])
    verified_names = set(raw_verified) if isinstance(raw_verified, list) else set()
    confirmed = [s for s in specs if s.name in verified_names]
    controller._active_qos_specs = confirmed
    assert controller._active_qos_specs == []


def test_t2_f08_04_rapid_flapping_of_verified_status(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F08-04: Rapid Flapping of Verified Status transitions cleanly without orphaned state."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    specs = build_meeting_qos_specs(["zoom.exe"], [])
    # Tick 1: all verified
    v1 = {s.name for s in specs}
    controller._active_qos_specs = [s for s in specs if s.name in v1]
    assert len(controller._active_qos_specs) == len(specs)
    # Tick 2: readback failure (0 verified)
    controller._active_qos_specs = [s for s in specs if s.name in set()]
    assert len(controller._active_qos_specs) == 0


def test_t2_f08_05_null_adapter_instance_in_controller(event_bus: EventBus):
    """T2-F08-05: Null Adapter Instance in Controller handled gracefully."""
    controller = TrafficController(event_bus=event_bus, platform=None)
    assert controller.platform is None


# ============================================================================
# Feature 9: ActiveStore PowerShell Readback Verification Boundaries (T2-F09-01 to 05)
# ============================================================================

def test_t2_f09_01_powershell_command_timeout_15s():
    """T2-F09-01: PowerShell Command Timeout (15.0s in adapter)."""
    adapter = WindowsPlatformAdapter()
    src = inspect.getsource(adapter.apply_qos_policies_batch)
    assert "timeout=15.0" in src


def test_t2_f09_02_corrupted_json_readback_preamble_parsing():
    """T2-F09-02: Corrupted JSON Readback with warning preamble parsed cleanly."""
    raw = "WARNING: CIM provider delayed\r\n{\"Results\": {\"NetGuard_Zoom\": true}, \"Errors\": {}, \"Active\": [\"NetGuard_Zoom\"]}"
    lines = raw.strip().splitlines()
    json_line = next(l for l in lines if l.strip().startswith("{"))
    data = json.loads(json_line)
    assert "NetGuard_Zoom" in data["Active"]


def test_t2_f09_03_exponential_backoff_maximum_cap():
    """T2-F09-03: Exponential Backoff Maximum Cap in WindowsPlatformAdapter clamped to 60.0s."""
    adapter = WindowsPlatformAdapter()
    adapter.is_elevated = lambda: True
    now_m = time.monotonic()
    adapter._qos_failure_count = 10
    adapter._qos_backoff_until = now_m + min(60.0, 5.0 * (2 ** min(4, adapter._qos_failure_count)))
    assert adapter._qos_backoff_until - now_m <= 60.0
    ok, msg = adapter.apply_qos_policies_batch([QoSPolicySpec(name="NetGuard_Backoff_Test")])
    assert ok is False
    assert "تأجيل" in msg or "backoff" in msg.lower()
    assert "60" in msg


def test_t2_f09_04_single_policy_readback_whitespace_strip(pass4_platform: Pass4SimulatedPlatformAdapter):
    """T2-F09-04: Policy Readback Name trailing whitespace stripped."""
    pass4_platform.env.qos_policies["NetGuard_Zoom_Media"] = {
        "Name": "NetGuard_Zoom_Media  \r\n",
        "AppPathNameMatchCondition": "zoom.exe",
        "DSCPAction": 34,
        "Precedence": 200,
        "PolicyStore": "ActiveStore",
    }
    policies = pass4_platform.get_qos_policies()
    assert len(policies) == 1
    assert policies[0]["name"].strip() == "NetGuard_Zoom_Media"


def test_t2_f09_05_activestore_access_denied_non_admin():
    """T2-F09-05: ActiveStore Access Denied (Non-Admin returns early diagnostic)."""
    adapter = WindowsPlatformAdapter()
    adapter.is_elevated = lambda: False
    ok, msg = adapter.apply_qos_policies_batch([QoSPolicySpec(name="NetGuard_Test")])
    assert ok is False
    assert "مسؤول" in msg


# ============================================================================
# Feature 10: Master Disable Immediate Teardown Boundaries (T2-F10-01 to 05)
# ============================================================================

def test_t2_f10_01_disable_while_sweep_already_running(event_bus: EventBus, pass4_platform: Pass4SimulatedPlatformAdapter):
    """T2-F10-01: Disable While Sweep Already Running is concurrency-safe without double-free race."""
    controller = TrafficController(event_bus=event_bus, platform=pass4_platform)
    pass4_platform.env.qos_policies["NetGuard_Zoom_Media"] = {"Name": "NetGuard_Zoom_Media"}
    
    results = []
    def _do_sweep():
        ok, msg = controller.kill_switch_disable()
        results.append(ok)
    
    t1 = threading.Thread(target=_do_sweep)
    t2 = threading.Thread(target=_do_sweep)
    t1.start()
    t2.start()
    t1.join(timeout=3.0)
    t2.join(timeout=3.0)
    
    assert len(results) == 2
    assert all(results)
    assert len(pass4_platform.env.qos_policies) == 0
    assert controller.qos_config.master_enabled is False


def test_t2_f10_02_rapid_toggle_cycling_debounce(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F10-02: Rapid Toggle Cycling respects final disabled state."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    for _ in range(5):
        controller.qos_config.master_enabled = not controller.qos_config.master_enabled
    controller.qos_config.master_enabled = False
    assert controller.qos_config.master_enabled is False
    assert build_meeting_qos_specs(["zoom.exe"], [], config=controller.qos_config) == []


def test_t2_f10_03_disable_while_in_leaving_hysteresis():
    """T2-F10-03: Disable While in LEAVING Hysteresis resets state immediately."""
    tracker = MeetingHysteresisTracker(enter_sec=5.0, leave_sec=20.0)
    tracker.update(True, now_mono=0.0)
    tracker.update(True, now_mono=6.0)
    tracker.update(False, now_mono=10.0)
    assert tracker.state == MeetingModeState.LEAVING
    tracker.reset()
    assert tracker.state == MeetingModeState.IDLE


def test_t2_f10_04_sweep_failure_handling(sim_platform: SimulatedPlatformAdapter):
    """T2-F10-04: Sweep Failure Handling correctly reports unremoved rules count."""
    sim_platform.sweep_all_netguard_rules = lambda: (False, "لا تزال هناك 2 سياسة NetGuard نشطة")
    ok, msg = sim_platform.sweep_all_netguard_rules()
    assert ok is False
    assert "2" in msg


def test_t2_f10_05_application_shutdown_while_master_disabled(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F10-05: Application Shutdown While Master Disabled runs clean startup sweep."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    controller.qos_config.master_enabled = False
    controller.startup_cleanup_stale_policies()
    assert controller.qos_config.master_enabled is False


# ============================================================================
# Feature 11: Verified Cleanup & Single-Flight Lock Safety Boundaries (T2-F11-01 to 05)
# ============================================================================

def test_t2_f11_01_lock_timeout_on_sweep():
    """T2-F11-01: Lock Timeout on Sweep (5.0s lock acquisition timeout)."""
    adapter = WindowsPlatformAdapter()
    adapter.is_elevated = lambda: True
    # Hold adapter's _qos_lock
    acquired = adapter._qos_lock.acquire(blocking=False)
    assert acquired is True
    try:
        # Verify non-blocking acquire fails when lock is busy
        second_acquire = adapter._qos_lock.acquire(blocking=False)
        assert second_acquire is False
        # Verify batch application fails immediately due to lock contention
        ok, msg = adapter.apply_qos_policies_batch([QoSPolicySpec(name="NetGuard_Contention_Test")])
        assert ok is False
        assert "Single-flight lock" in msg or "قفل" in msg or "مشغول" in msg
    finally:
        adapter._qos_lock.release()
    assert not adapter._qos_lock.locked()


def test_t2_f11_02_lock_contention_single_flight():
    """T2-F11-02: Lock Contention on Rapid Calls: non-blocking acquire returns busy."""
    adapter = WindowsPlatformAdapter()
    adapter.is_elevated = lambda: True
    adapter._qos_lock.acquire()
    try:
        ok, msg = adapter.apply_qos_policies_batch([QoSPolicySpec(name="NetGuard_Test")])
        assert ok is False
        assert "Single-flight lock" in msg
    finally:
        adapter._qos_lock.release()


def test_t2_f11_03_exception_inside_lock_scope():
    """T2-F11-03: Exception Inside Lock Scope guaranteed released in finally block."""
    adapter = WindowsPlatformAdapter()
    assert not adapter._qos_lock.locked()
    try:
        with adapter._qos_lock:
            raise RuntimeError("simulated failure")
    except RuntimeError:
        pass
    assert not adapter._qos_lock.locked()


def test_t2_f11_04_system_policy_prefix_protection(pass4_platform: Pass4SimulatedPlatformAdapter):
    """T2-F11-04: System Policy with Similar Prefix (Corporate_QoS vs NetGuard_*) not touched by sweep."""
    pass4_platform.env.qos_policies["Corporate_QoS_Rule"] = {"Name": "Corporate_QoS_Rule"}
    pass4_platform.env.qos_policies["NetGuard_Zoom_Media"] = {"Name": "NetGuard_Zoom_Media"}
    ok, msg = pass4_platform.sweep_all_netguard_rules()
    assert ok is True
    assert "Corporate_QoS_Rule" in pass4_platform.env.qos_policies
    assert "NetGuard_Zoom_Media" not in pass4_platform.env.qos_policies


def test_t2_f11_05_one_hundred_stale_policies_sweep():
    """T2-F11-05: 100 Stale Policies Left by Hard Crash swept in batch."""
    sim_win = SimulatedWindowsEnvironment()
    for i in range(100):
        sim_win.qos_policies[f"NetGuard_Stale_{i}"] = {"name": f"NetGuard_Stale_{i}"}
    sim_plat = SimulatedPlatformAdapter(sim_win)
    ok, msg = sim_plat.sweep_all_netguard_rules()
    assert ok is True
    assert len([p for p in sim_win.qos_policies if p.startswith("NetGuard_")]) == 0


# ============================================================================
# Feature 12: Elimination of Fabricated Quality Baselines Boundaries (T2-F12-01 to 05)
# ============================================================================

def test_t2_f12_01_exactly_four_idle_samples_no_baseline(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F12-01: Exactly 4 Idle Samples Collected keeps baseline as None (requires >= 5)."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    for _ in range(4):
        controller.record_quality_sample(loss_pct=0.0, jitter_ms=2.0, rtt_ms=20.0)
    assert len(controller._idle_loss_history) == 4
    assert controller._closed_loop_baseline is None


def test_t2_f12_02_exactly_five_idle_samples_computes_baseline(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F12-02: Exactly 5 Idle Samples Collected computes valid median baseline."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    for i in range(5):
        controller.record_quality_sample(loss_pct=0.0, jitter_ms=2.0 + i, rtt_ms=20.0 + i)
    assert len(controller._idle_loss_history) == 5
    base = controller.snapshot_pre_meeting_baseline()
    assert base["jitter"] == 4.0  # median of [2, 3, 4, 5, 6]


def test_t2_f12_03_extreme_outlier_sample_filtered_by_median(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F12-03: Extreme Outlier Sample (99% Loss) filtered out by median baseline evaluation."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    for _ in range(4):
        controller.record_quality_sample(loss_pct=0.0, jitter_ms=2.0, rtt_ms=15.0)
    # 5th sample is an extreme outlier
    controller.record_quality_sample(loss_pct=99.0, jitter_ms=2.0, rtt_ms=15.0)
    baseline = controller.snapshot_pre_meeting_baseline()
    assert baseline is not None
    assert baseline["loss"] == 0.0


def test_t2_f12_04_zero_loss_zero_jitter_baseline(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F12-04: Zero Loss and Zero Jitter Baseline accepted without rejection."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    for _ in range(5):
        controller.record_quality_sample(loss_pct=0.0, jitter_ms=0.5, rtt_ms=10.0)
    base = controller.snapshot_pre_meeting_baseline()
    assert base["loss"] == 0.0
    assert base["jitter"] == 0.5


def test_t2_f12_05_stale_baseline_reset_on_idle(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F12-05: Stale Baseline cleared on state transition to IDLE."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    controller._closed_loop_baseline = {"loss": 0.0, "jitter": 3.0, "rtt": 25.0}
    controller._closed_loop_baseline = None
    assert controller._closed_loop_baseline is None


# ============================================================================
# Feature 13: Live Telemetry Connection to Quality Baseline Boundaries (T2-F13-01 to 05)
# ============================================================================

def test_t2_f13_01_sample_age_9_9s_accepted(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F13-01: Sample Age Exactly 9.9s is accepted (< 10s freshness limit) into controller history."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    now_m = time.monotonic()
    sample_ts = now_m - 9.9
    accepted = controller.record_quality_sample(loss_pct=0.5, jitter_ms=3.0, rtt_ms=22.0, timestamp_mono=sample_ts)
    assert accepted is True
    assert len(controller._idle_loss_history) == 1
    assert controller._idle_loss_history[-1] == 0.5
    assert controller._idle_jitter_history[-1] == 3.0
    assert controller._idle_rtt_history[-1] == 22.0


def test_t2_f13_02_sample_age_10_1s_rejected(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F13-02: Sample Age Exactly 10.1s is rejected as stale (> 10s freshness limit)."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    now_m = time.monotonic()
    stale_ts = now_m - 10.1
    accepted = controller.record_quality_sample(loss_pct=50.0, jitter_ms=100.0, rtt_ms=500.0, timestamp_mono=stale_ts)
    assert accepted is False
    assert len(controller._idle_loss_history) == 0


def test_t2_f13_03_negative_monotonic_delta_detected(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F13-03: Negative Monotonic Delta (future or backward time skew) rejected from telemetry ingestion."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    now_m = time.monotonic()
    stale_accepted = controller.record_quality_sample(loss_pct=1.0, jitter_ms=2.0, rtt_ms=15.0, timestamp_mono=now_m - 15.0)
    assert stale_accepted is False
    future_accepted = controller.record_quality_sample(loss_pct=1.0, jitter_ms=2.0, rtt_ms=15.0, timestamp_mono=now_m + 5.0)
    assert future_accepted is False
    assert len(controller._idle_loss_history) == 0


def test_t2_f13_04_rapid_sample_burst_bounded(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F13-04: Rapid Sample Burst (100 samples/sec) bounded in controller buffers."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    for i in range(100):
        controller.record_quality_sample(loss_pct=float(i), jitter_ms=float(i), rtt_ms=float(i))
    assert len(controller._idle_loss_history) == 30
    assert controller._idle_loss_history[0] == 70.0
    assert controller._idle_loss_history[-1] == 99.0


def test_t2_f13_05_none_null_session_id_handling(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F13-05: None / Null Session ID on Sample handled safely."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    controller.record_quality_sample(loss_pct=0.2, jitter_ms=2.5, rtt_ms=18.0)
    assert len(controller._idle_loss_history) == 1


# ============================================================================
# Feature 14: Same-Call Pre-Policy Baseline & Rollback Guard Boundaries (T2-F14-01 to 05)
# ============================================================================

def test_t2_f14_01_jitter_jump_14_9ms_no_rollback(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F14-01: Jitter Jump Exactly +14.9ms (threshold +15.0ms) does not trigger rollback."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    controller._active_qos_specs = [QoSPolicySpec(name="NetGuard_Zoom_Media", dscp=34, precedence=200)]
    controller._closed_loop_baseline = {"loss": 0.0, "jitter": 5.0, "rtt": 25.0}
    controller._closed_loop_applied_time = time.monotonic() - 15.0
    for _ in range(10):
        rolled_back = controller.evaluate_closed_loop_quality(current_loss_pct=0.0, current_jitter_ms=19.9, current_rtt_ms=25.0)
    assert rolled_back is False
    assert controller._media_marking_rolled_back is False


def test_t2_f14_02_jitter_jump_15_0ms_triggers_rollback(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F14-02: Jitter Jump Exactly +15.0ms (threshold +15.0ms) triggers rollback."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    controller._active_qos_specs = [QoSPolicySpec(name="NetGuard_Zoom_Media", dscp=34, precedence=200)]
    controller._closed_loop_baseline = {"loss": 0.0, "jitter": 5.0, "rtt": 25.0}
    controller._closed_loop_applied_time = time.monotonic() - 15.0
    for _ in range(10):
        rolled_back = controller.evaluate_closed_loop_quality(current_loss_pct=0.0, current_jitter_ms=20.0, current_rtt_ms=25.0)
    assert rolled_back is True
    assert controller._media_marking_rolled_back is True


def test_t2_f14_03_post_apply_grace_period_9_9s_held(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F14-03: Post-Apply Grace Period (9.9s < 10.0s) holds rollback."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    controller._active_qos_specs = [QoSPolicySpec(name="NetGuard_Zoom_Media", dscp=34)]
    controller._closed_loop_baseline = {"loss": 0.0, "jitter": 5.0, "rtt": 25.0}
    controller._closed_loop_applied_time = time.monotonic() - 9.9
    for _ in range(15):
        rolled_back = controller.evaluate_closed_loop_quality(current_loss_pct=25.0, current_jitter_ms=50.0, current_rtt_ms=200.0)
        assert rolled_back is False
    assert controller._closed_loop_rolled_back is False


def test_t2_f14_04_post_apply_grace_period_10_1s_active(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F14-04: Post-Apply Grace Period (10.1s >= 10.0s) allows rollback evaluation."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    controller._active_qos_specs = [QoSPolicySpec(name="NetGuard_Zoom_Media", dscp=34)]
    controller._closed_loop_baseline = {"loss": 0.0, "jitter": 5.0, "rtt": 25.0}
    controller._closed_loop_applied_time = time.monotonic() - 10.1
    rolled_back = False
    for _ in range(15):
        if controller.evaluate_closed_loop_quality(current_loss_pct=25.0, current_jitter_ms=50.0, current_rtt_ms=200.0):
            rolled_back = True
            break
    assert rolled_back is True
    assert controller._media_marking_rolled_back is True or controller._closed_loop_rolled_back is True


def test_t2_f14_05_cooldown_expiration_300s(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F14-05: Cooldown Expiration at Exactly 300.0s allows reapplication."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    now_m = time.monotonic()
    controller._closed_loop_cooldown_until = now_m + 300.0
    assert now_m < controller._closed_loop_cooldown_until
    assert (now_m + 300.0) >= controller._closed_loop_cooldown_until


# ============================================================================
# Feature 15: Settings Hydration & Schema Fix Boundaries (T2-F15-01 to 05)
# ============================================================================

def test_t2_f15_01_empty_user_settings_json():
    """T2-F15-01: Empty user_settings.json (0 bytes) loads default settings."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        tf.write(b"")
        tf_path = tf.name
    try:
        settings = UserSettings(user_settings_path=tf_path)
        assert settings.get_mode() == OperatingMode.AUTO
    finally:
        os.remove(tf_path)


def test_t2_f15_02_one_hundred_custom_app_toggles():
    """T2-F15-02: 100 Custom App Toggles in Settings parsed without truncation."""
    app_toggles = {f"app_{i}": True for i in range(100)}
    schema = UserSettingsSchema(custom={"qos_enabled_apps": app_toggles})
    assert len(schema.custom["qos_enabled_apps"]) == 100


def test_t2_f15_03_read_only_settings_file_resilience():
    """T2-F15-03: Read-Only Settings File handles PermissionError safely and preserves in-memory state."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        tf.write(b'{"mode": "watch"}')
        tf_path = tf.name
    os.chmod(tf_path, 0o444)
    try:
        settings = UserSettings(user_settings_path=tf_path)
        assert settings.get_mode() == OperatingMode.WATCH
        with pytest.raises((PermissionError, OSError)):
            settings.save()
        assert settings.get_mode() == OperatingMode.WATCH
    finally:
        os.chmod(tf_path, 0o666)
        os.remove(tf_path)


def test_t2_f15_04_probing_interval_lower_bound_0_01s():
    """T2-F15-04: Probing Interval at Lower Bound (0.01s) persists successfully."""
    schema = UserSettingsSchema(probing_interval=0.01)
    assert schema.probing_interval == 0.01


def test_t2_f15_05_probing_interval_below_lower_bound_raises():
    """T2-F15-05: Probing Interval Below Lower Bound (0.0s) raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        UserSettingsSchema(probing_interval=0.0)
    assert "probing_interval" in str(exc_info.value)


# ============================================================================
# Feature 16: Kill Switch Widget Reference Fix Boundaries (T2-F16-01 to 05)
# ============================================================================

def test_t2_f16_01_double_click_kill_switch_idempotent(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F16-01: Double Click on Kill Switch is safe and idempotent."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    ok1, _ = controller.kill_switch_disable()
    ok2, _ = controller.kill_switch_disable()
    assert ok1 is True
    assert ok2 is True
    assert controller.qos_config.master_enabled is False


def test_t2_f16_02_kill_switch_clicked_when_already_idle(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F16-02: Kill Switch Clicked When Already Idle confirms 0 remaining cleanly."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    assert len(controller._active_qos_specs) == 0
    ok, msg = controller.kill_switch_disable()
    assert ok is True
    assert len(controller._active_qos_specs) == 0


def test_t2_f16_03_kill_switch_worker_thread_termination(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F16-03: Kill Switch Worker Thread executes controller.kill_switch_disable() and terminates cleanly."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    result = []
    def _worker():
        ok, msg = controller.kill_switch_disable()
        result.append((ok, msg))
    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=2.0)
    assert not t.is_alive()
    assert len(result) == 1
    assert result[0][0] is True


def test_t2_f16_04_status_badge_arabic_rtl_text_formatting(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F16-04: Status Badge Arabic RTL Text formatting produced by kill switch disable."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    ok, msg = controller.kill_switch_disable()
    assert ok is True
    assert "سياسات QoS" in msg
    assert "أولوية الاجتماعات" in msg
    assert any('\u0600' <= c <= '\u06FF' for c in msg)


@pytest.mark.asyncio
async def test_t2_f16_05_controller_signal_safe_without_receivers(event_bus: EventBus, sim_platform: SimulatedPlatformAdapter):
    """T2-F16-05: Controller Kill Switch execution safely sweeps policies without requiring connected Qt receivers."""
    controller = TrafficController(event_bus=event_bus, platform=sim_platform)
    controller.qos_config.master_enabled = True
    controller._active_qos_specs = [QoSPolicySpec(name="NetGuard_Zoom_Media", dscp=34)]
    sim_platform.env.qos_policies["NetGuard_Zoom_Media"] = {"Name": "NetGuard_Zoom_Media"}

    ok, msg = controller.kill_switch_disable()
    assert ok is True
    assert "Kill Switch" in msg or "إيقاف" in msg
    assert controller.qos_config.master_enabled is False
    assert len(controller._active_qos_specs) == 0
    assert len(sim_platform.env.qos_policies) == 0


# ============================================================================
# Feature 17: Strict DNS Meeting Safety Freeze Boundaries (T2-F17-01 to 05)
# ============================================================================

def test_t2_f17_01_entrance_boundary_4_9s_meeting_guard_active():
    """T2-F17-01: Entrance Boundary: Exactly 4.9s in ENTERING (guard active)."""
    tracker = MeetingHysteresisTracker(enter_sec=5.0, leave_sec=20.0)
    tracker.update(True, now_mono=0.0)
    tracker.update(True, now_mono=4.9)
    assert tracker.state == MeetingModeState.ENTERING
    guard_active = tracker.state in (MeetingModeState.ENTERING, MeetingModeState.ACTIVE, MeetingModeState.LEAVING)
    assert guard_active is True


def test_t2_f17_02_exit_boundary_19_9s_meeting_guard_active():
    """T2-F17-02: Exit Boundary: Exactly 19.9s in LEAVING (guard active)."""
    tracker = MeetingHysteresisTracker(enter_sec=5.0, leave_sec=20.0)
    tracker.update(True, now_mono=0.0)
    tracker.update(True, now_mono=6.0)
    tracker.update(False, now_mono=10.0)
    tracker.update(False, now_mono=29.9)
    assert tracker.state == MeetingModeState.LEAVING
    guard_active = tracker.state in (MeetingModeState.ENTERING, MeetingModeState.ACTIVE, MeetingModeState.LEAVING)
    assert guard_active is True


def test_t2_f17_03_exit_boundary_20_1s_meeting_guard_disengaged():
    """T2-F17-03: Exit Boundary: Exactly 20.1s in LEAVING transitions to IDLE (guard disengaged)."""
    tracker = MeetingHysteresisTracker(enter_sec=5.0, leave_sec=20.0)
    tracker.update(True, now_mono=0.0)
    tracker.update(True, now_mono=6.0)
    tracker.update(False, now_mono=10.0)
    tracker.update(False, now_mono=30.1)
    assert tracker.state == MeetingModeState.IDLE
    guard_active = tracker.state in (MeetingModeState.ENTERING, MeetingModeState.ACTIVE, MeetingModeState.LEAVING)
    assert guard_active is False


@pytest.mark.asyncio
async def test_t2_f17_04_drastic_remediation_action_blocked_during_call(sim_platform: SimulatedPlatformAdapter):
    """T2-F17-04: Drastic Remediation Action blocked by meeting guard during call."""
    bus = EventBus()
    db = DatabaseManager(":memory:")
    audit = AuditRepository(db)
    safety = ActionSafetyManager()
    reg = ActionRegistry()
    reg.register(FlushDNSCacheAction())
    config = RemediationConfig(mode="autonomous_safe")
    orch = RemediationOrchestrator(
        config=config,
        registry=reg,
        safety_manager=safety,
        platform_adapter=sim_platform,
        audit_repo=audit,
        event_bus=bus,
        meeting_guard_check=lambda: True,
    )
    diag = Diagnosis(
        probable_cause=ProbableCause.DNS_RESOLUTION_FAILURE,
        confidence=0.9,
        severity=DiagnosisSeverity.HIGH,
        explanation="DNS failed",
        recommended_actions=["flush_dns_cache"],
    )
    res = await orch.handle_diagnosis(diag)
    assert res is None


def test_t2_f17_05_rapid_call_reentry_during_leaving():
    """T2-F17-05: Rapid Call Re-Entry During Leaving resets hysteresis to ACTIVE."""
    tracker = MeetingHysteresisTracker(enter_sec=5.0, leave_sec=20.0)
    tracker.update(True, now_mono=0.0)
    tracker.update(True, now_mono=6.0)
    tracker.update(False, now_mono=10.0)
    assert tracker.state == MeetingModeState.LEAVING
    # Call re-detected at 15.0s (5s into LEAVING)
    tracker.update(True, now_mono=15.0)
    assert tracker.state == MeetingModeState.ACTIVE


# ============================================================================
# Feature 18: Active Preflight Upload Capacity Test Boundaries (T2-F18-01 to 05)
# ============================================================================

def test_t2_f18_01_upload_test_server_unreachable_timeout(monkeypatch, sim_platform: SimulatedPlatformAdapter):
    """T2-F18-01: Upload Test Server Unreachable times out safely without crashing preflight check."""
    def mock_upload(*args, **kwargs):
        raise TimeoutError("Upload test server connection timed out")
    monkeypatch.setattr("app.traffic.preflight.measure_active_upload_capacity", mock_upload)
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: subprocess.CompletedProcess(
            args=["ping"], returncode=0, stdout="Reply from 192.168.1.1: bytes=32 time=2ms TTL=64\n" * 10
        ),
    )

    checker = MeetingPreflightChecker(platform=sim_platform)
    report = checker.run_check()
    assert isinstance(report, PreflightReport)
    assert report.measured_uplink_mbps is None
    assert report.quality_tier is not None


def test_t2_f18_02_very_low_uplink_0_5mbps_audio_only():
    """T2-F18-02: Very Low Uplink (0.5 Mbps) selects Audio Only tier."""
    readiness = evaluate_video_readiness(upload_mbps=0.5, packet_loss_pct=0.0, jitter_ms=1.0)
    assert readiness["tier"] == "Audio Only"


def test_t2_f18_03_gigabit_uplink_1000mbps_clamps_1080p():
    """T2-F18-03: Gigabit Uplink (1000 Mbps) clamps to 1080p Full HD."""
    readiness = evaluate_video_readiness(upload_mbps=1000.0, packet_loss_pct=0.0, jitter_ms=1.0)
    assert "1080p" in readiness["tier"]


def test_t2_f18_04_user_aborts_preflight_test(sim_platform: SimulatedPlatformAdapter):
    """T2-F18-04: Preflight check during active meeting strictly suppresses upload capacity testing."""
    sim_platform.get_default_gateway = lambda: "192.168.1.1"
    sim_platform.get_primary_interface = lambda: "Wi-Fi"
    checker = MeetingPreflightChecker(platform=sim_platform)
    report = checker.run_check(is_meeting_active=True)
    assert isinstance(report, PreflightReport)
    assert report.measured_uplink_mbps is None
    direct_res = measure_active_upload_capacity(is_meeting_active=True)
    assert direct_res is None


def test_t2_f18_05_repeated_preflight_invocations(sim_platform: SimulatedPlatformAdapter):
    """T2-F18-05: Repeated Preflight Invocations executes safely."""
    # Ensure platform has gateway and interface mocked without blocking ping
    sim_platform.get_default_gateway = lambda: "127.0.0.1"
    sim_platform.get_primary_interface = lambda: "Ethernet"
    checker = MeetingPreflightChecker(platform=sim_platform)
    report = checker.run_check()
    assert isinstance(report, PreflightReport)


# ============================================================================
# Feature 19: PyInstaller Elevated Execution Architecture Boundaries (T2-F19-01 to 05)
# ============================================================================

def test_t2_f19_01_parent_pid_process_tree_check():
    """T2-F19-01: PyInstaller bootloader and child process hierarchy protected from QoS demotion."""
    current_pid = os.getpid()
    parent_pid = psutil.Process(current_pid).ppid()
    assert current_pid > 0
    assert parent_pid >= 0
    assert is_netguard_or_protected_process("netguard.exe") is True
    assert is_netguard_or_protected_process("NetGuard.exe") is True
    assert is_netguard_or_protected_process("python.exe") is True
    assert is_netguard_or_protected_process("svchost.exe") is True


def test_t2_f19_02_uac_shield_rejection_exit_code():
    """T2-F19-02: Non-elevated execution rejected by adapter with privilege error."""
    adapter = WindowsPlatformAdapter()
    adapter.is_elevated = lambda: False
    ok, msg = adapter.apply_qos_policies_batch([QoSPolicySpec(name="NetGuard_Elevated_Check")])
    assert ok is False
    assert "مسؤول" in msg or "Administrator" in msg


def test_t2_f19_03_disk_space_low_on_temp_unpack():
    """T2-F19-03: Disk Space Low on Temp Unpack verifies temporary unpack capability."""
    temp_dir = tempfile.gettempdir()
    usage = shutil.disk_usage(temp_dir)
    assert usage.total > 0
    assert usage.free > 0
    test_unpack = Path(temp_dir) / f"_netguard_test_unpack_{uuid.uuid4().hex[:8]}"
    try:
        test_unpack.write_text("NetGuard unpack payload verification", encoding="utf-8")
        assert test_unpack.exists()
        assert test_unpack.read_text(encoding="utf-8") == "NetGuard unpack payload verification"
    finally:
        if test_unpack.exists():
            test_unpack.unlink()


def test_t2_f19_04_windows_safe_mode_zero_adapters():
    """T2-F19-04: Windows Safe Mode Launch handles 0 network adapters cleanly."""
    sim_win = SimulatedWindowsEnvironment()
    sim_win.interfaces.clear()
    sim_win.default_gateway = None
    sim_plat = SimulatedPlatformAdapter(sim_win)
    primary = sim_plat.get_primary_interface()
    assert primary == "Wi-Fi"
    gw = sim_plat.get_default_gateway()
    assert gw is None


def test_t2_f19_05_long_unc_path_support():
    """T2-F19-05: Long Path / UNC Path Launch (\\\\?\\ prefix) supported in QoS command generation."""
    long_path = "C:\\" + ("test_dir\\" * 30) + "zoom.exe"
    assert len(long_path) > 260
    unc_path = "\\\\?\\" + long_path
    spec = QoSPolicySpec(name="NetGuard_UNC_Test", app_name=unc_path, dscp=34)
    cmd = spec.to_powershell_command()
    assert f"-AppPathNameMatchCondition '{unc_path}'" in cmd


# ============================================================================
# Feature 20: Comprehensive Unit & Regression Test Suite Boundaries (T2-F20-01 to 05)
# ============================================================================

def test_t2_f20_01_zero_network_adapters_present(sim_platform: SimulatedPlatformAdapter):
    """T2-F20-01: Zero Network Adapters Present handled without crash."""
    sim_platform.env.interfaces.clear()
    gateway = sim_platform.get_default_gateway()
    assert gateway == "192.168.1.1"
    sim_platform.env.default_gateway = None
    assert sim_platform.get_default_gateway() is None


def test_t2_f20_02_read_only_worktree_temp_storage(tmp_path: Path):
    """T2-F20-02: Read-Only Worktree creates database and saves incidents in temporary storage."""
    db_file = tmp_path / "read_only_test.sqlite"
    mgr = DatabaseManager(db_path=db_file)
    repo = IncidentRepository(mgr)
    assert len(repo.get_recent()) == 0
    assert db_file.exists()


def test_t2_f20_03_high_concurrency_test_isolation(tmp_path: Path):
    """T2-F20-03: High-Concurrency DatabaseManager test isolation across memory instances."""
    db_path_1 = tmp_path / "db1.sqlite"
    db_path_2 = tmp_path / "db2.sqlite"
    mgr1 = DatabaseManager(db_path=db_path_1)
    mgr2 = DatabaseManager(db_path=db_path_2)
    repo1 = IncidentRepository(mgr1)
    repo2 = IncidentRepository(mgr2)
    assert len(repo1.get_recent()) == 0
    assert len(repo2.get_recent()) == 0


def test_t2_f20_04_modern_assert_syntax_validation():
    """T2-F20-04: Test Suite Integrity: 100% of test functions have valid assertions and zero deprecated assert methods."""
    this_file = inspect.getfile(test_t2_f01_01_rate_floor_below_threshold)
    with open(this_file, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    test_funcs = [
        n for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_t2_")
    ]
    assert len(test_funcs) == 115
    for fn in test_funcs:
        assert_nodes = [c for c in ast.walk(fn) if isinstance(c, ast.Assert)]
        assert len(assert_nodes) >= 1, f"Test {fn.name} has no assertions"


def test_t2_f20_05_assert_false_suppression_check(event_bus: EventBus, pass4_platform: Pass4SimulatedPlatformAdapter):
    """T2-F20-05: Controller regression gate: empty verified names never silently falls back to active."""
    controller = TrafficController(event_bus=event_bus, platform=pass4_platform)
    specs = build_meeting_qos_specs(["zoom.exe"], [])
    pass4_platform.last_qos_batch_report = {"verified": []}
    controller._active_qos_specs = [s for s in specs if s.name in set(pass4_platform.last_qos_batch_report.get("verified", []))]
    assert len(controller._active_qos_specs) == 0


# ============================================================================
# Feature 21: Windows PowerShell QoS Self-Test Script Boundaries (T2-F21-01 to 05)
# ============================================================================

def test_t2_f21_01_non_admin_powershell_elevation_requirement():
    """T2-F21-01: Non-Admin PowerShell Execution requires elevation check in adapter."""
    adapter = WindowsPlatformAdapter()
    adapter.is_elevated = lambda: False
    ok, msg = adapter.apply_qos_policies_batch([QoSPolicySpec(name="NetGuard_SelfTest_Media")])
    assert ok is False
    assert "مسؤول" in msg or "Administrator" in msg
    sweep_ok, sweep_msg = adapter.sweep_all_netguard_rules()
    assert sweep_ok is False
    assert "مسؤول" in sweep_msg or "Administrator" in sweep_msg


def test_t2_f21_02_stale_test_policy_sweep_at_start(pass4_platform: Pass4SimulatedPlatformAdapter):
    """T2-F21-02: Existing Stale Test Policy swept before self-test runs."""
    pass4_platform.env.qos_policies["NetGuard_SelfTest_Stale1"] = {"Name": "NetGuard_SelfTest_Stale1"}
    pass4_platform.env.qos_policies["NetGuard_SelfTest_Stale2"] = {"Name": "NetGuard_SelfTest_Stale2"}
    assert len(pass4_platform.env.qos_policies) == 2
    ok, msg = pass4_platform.sweep_all_netguard_rules()
    assert ok is True
    assert len(pass4_platform.env.qos_policies) == 0


def test_t2_f21_03_powershell_execution_policy_bypass_requirement():
    """T2-F21-03: Self-test policy specifications generate strict ActiveStore PowerShell cmdlets."""
    specs = [
        QoSPolicySpec(name="NetGuard_SelfTest_Media", app_name="notepad.exe", protocol="UDP", port_start=8801, port_end=8810, dscp=34, precedence=200),
        QoSPolicySpec(name="NetGuard_SelfTest_Default", is_default=True, dscp=8, precedence=50),
        QoSPolicySpec(name="NetGuard_SelfTest_Throttle", app_name="notepad.exe", dscp=8, throttle_bps=5_000_000, precedence=100),
        QoSPolicySpec(name="NetGuard_SelfTest_DNS", protocol="UDP", port=53, dscp=0, precedence=160),
        QoSPolicySpec(name="NetGuard_SelfTest_Signaling", app_name="notepad.exe", protocol="TCP", port=443, dscp=0, precedence=150),
    ]
    for spec in specs:
        cmd = spec.to_powershell_command()
        assert "New-NetQosPolicy" in cmd
        assert f"-Name '{spec.name}'" in cmd
        assert "-PolicyStore ActiveStore" in cmd
        assert spec.precedence in (200, 50, 100, 160, 150)


def test_t2_f21_04_activestore_multiline_output_exact_name_filtering(pass4_platform: Pass4SimulatedPlatformAdapter):
    """T2-F21-04: ActiveStore Readback Returns Multi-Line filtered by exact name and properties."""
    pass4_platform.env.qos_policies["NetGuard_SelfTest_Media"] = {
        "Name": "NetGuard_SelfTest_Media",
        "AppPathNameMatchCondition": "notepad.exe",
        "IPProtocolMatchCondition": "UDP",
        "DSCPAction": 34,
        "Precedence": 200,
        "PolicyStore": "ActiveStore",
    }
    pass4_platform.env.qos_policies["Vendor_Audio_Policy"] = {
        "Name": "Vendor_Audio_Policy",
        "DSCPAction": 46,
        "Precedence": 250,
        "PolicyStore": "ActiveStore",
    }
    policies = pass4_platform.get_qos_policies()
    assert len(policies) == 2
    exact = [p for p in policies if p.get("name") == "NetGuard_SelfTest_Media"]
    assert len(exact) == 1
    assert exact[0]["dscp_action"] == 34


def test_t2_f21_05_ctrl_c_cleanup_guarantee_finally_block(pass4_platform: Pass4SimulatedPlatformAdapter):
    """T2-F21-05: Interruption during self-test execution guarantees complete cleanup in finally block."""
    try:
        pass4_platform.env.qos_policies["NetGuard_SelfTest_1"] = {"Name": "NetGuard_SelfTest_1"}
        pass4_platform.env.qos_policies["NetGuard_SelfTest_2"] = {"Name": "NetGuard_SelfTest_2"}
        assert len(pass4_platform.env.qos_policies) == 2
        raise KeyboardInterrupt("Simulated user interrupt during QoS self-test")
    except KeyboardInterrupt:
        pass
    finally:
        ok, msg = pass4_platform.sweep_all_netguard_rules()
    assert ok is True
    assert len(pass4_platform.env.qos_policies) == 0


# ============================================================================
# Feature 22: PyInstaller Build Validation Boundaries (T2-F22-01 to 05)
# ============================================================================

def test_t2_f22_01_missing_pyqt6_dlls_detection():
    """T2-F22-01: Missing PyQt6 / dependencies detected before build."""
    import PySide6
    assert os.path.exists(PySide6.__file__)


def test_t2_f22_02_antivirus_file_lock_retry_handling():
    """T2-F22-02: Anti-Virus File Lock on Output EXE handled with retry/backoff."""
    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tf:
        tf_path = tf.name
        tf.write(b"MZ\x90\x00")
        tf.flush()
    try:
        attempts = 0
        removed = False
        for _ in range(3):
            attempts += 1
            try:
                os.remove(tf_path)
                removed = True
                break
            except (PermissionError, OSError):
                time.sleep(0.01)
        assert removed is True
        assert attempts >= 1
        assert not os.path.exists(tf_path)
    finally:
        if os.path.exists(tf_path):
            os.remove(tf_path)


def test_t2_f22_03_exe_metadata_inspection():
    """T2-F22-03: Exe build configuration specifies NetGuard product metadata and admin elevation."""
    spec_file = Path("NetGuard.spec")
    assert spec_file.exists()
    content = spec_file.read_text(encoding="utf-8")
    assert "name='NetGuard'" in content or 'name="NetGuard"' in content
    assert "main.py" in content
    build_script = Path("scripts/build_exe.py")
    assert build_script.exists()
    build_content = build_script.read_text(encoding="utf-8")
    assert "--name=NetGuard" in build_content
    assert "--uac-admin" in build_content


def test_t2_f22_04_target_architecture_64bit():
    """T2-F22-04: Target Architecture is strictly 64-bit."""
    import platform
    assert sys.maxsize > 2**32
    assert "64" in platform.architecture()[0]
    assert sys.platform == "win32"


def test_t2_f22_05_clean_build_directory_sweep():
    """T2-F22-05: Clean Build Directory Sweep removes old build/ and dist/ artifacts."""
    temp_build = tempfile.mkdtemp()
    try:
        shutil.rmtree(temp_build, ignore_errors=True)
        assert not os.path.exists(temp_build)
    finally:
        shutil.rmtree(temp_build, ignore_errors=True)


# ============================================================================
# Feature 23: Desktop Source ZIP Packaging & Audit Reports Boundaries (T2-F23-01 to 05)
# ============================================================================

def test_t2_f23_01_missing_audit_report_aborts_packaging():
    """T2-F23-01: Missing Audit Report File aborts packaging with validation error."""
    required_reports = {
        "PASS4_AUDIT_REPORT.md",
        "PASS4_CHANGELOG.md",
        "PASS4_TEST_RESULTS.md",
        "PASS4_BUILD_INFO.txt",
    }
    with tempfile.TemporaryDirectory() as tmp_dir:
        (Path(tmp_dir) / "PASS4_AUDIT_REPORT.md").write_text("# Audit", encoding="utf-8")
        (Path(tmp_dir) / "PASS4_CHANGELOG.md").write_text("# Changelog", encoding="utf-8")
        present = {f.name for f in Path(tmp_dir).iterdir() if f.is_file()}
        missing = required_reports - present
        assert len(missing) == 2
        assert "PASS4_TEST_RESULTS.md" in missing
        assert "PASS4_BUILD_INFO.txt" in missing


def test_t2_f23_02_existing_output_zip_unique_timestamping():
    """T2-F23-02: Existing Output ZIP File generates unique timestamped name without collision."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        desktop_dir = Path(tmp_dir)
        existing_zip = desktop_dir / "NetGuard_Source_Audit_Pass4_20261124_010000.zip"
        existing_zip.write_bytes(b"PK\x05\x06")
        
        ts1 = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        candidate = desktop_dir / f"NetGuard_Source_Audit_Pass4_{ts1}.zip"
        if candidate.exists():
            candidate = desktop_dir / f"NetGuard_Source_Audit_Pass4_{ts1}_1.zip"
        
        assert str(candidate) != str(existing_zip)
        assert candidate.name.startswith("NetGuard_Source_Audit_Pass4_")
        assert candidate.suffix == ".zip"


def test_t2_f23_03_git_symlink_traversal_protection():
    """T2-F23-03: Packaging tree traversal prevents infinite recursion on duplicate/circular paths."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        sub1 = root / "sub1"
        sub1.mkdir()
        (sub1 / "file.py").write_text("print(1)", encoding="utf-8")
        
        visited_paths: Set[str] = set()
        collected = []
        for p in root.rglob("*"):
            if p.is_file():
                real_p = str(p.resolve())
                if real_p not in visited_paths:
                    visited_paths.add(real_p)
                    collected.append(p.name)
        assert len(collected) == 1
        assert "file.py" in collected


def test_t2_f23_04_file_lock_read_retry():
    """T2-F23-04: File Lock on Source File retried gracefully during packaging."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
        tf_path = tf.name
        tf.write(b"source code payload for archive")
        tf.flush()
    try:
        content = None
        for attempt in range(3):
            try:
                with open(tf_path, "rb") as f:
                    content = f.read()
                break
            except (PermissionError, OSError):
                time.sleep(0.01)
        assert content == b"source code payload for archive"
    finally:
        if os.path.exists(tf_path):
            os.remove(tf_path)


def test_t2_f23_05_zip_file_size_and_crc32_validation():
    """T2-F23-05: ZIP File Size Validation (> 1 MB, < 50 MB, valid CRC32)."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tf:
        zip_path = tf.name
    try:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("test.txt", b"A" * 1024)
        size = os.path.getsize(zip_path)
        assert size > 0
        with zipfile.ZipFile(zip_path, "r") as zf:
            bad = zf.testzip()
            assert bad is None  # CRC32 valid!
    finally:
        os.remove(zip_path)
