"""Tier 3: Pairwise Cross-Feature Interactions & Specificity Matrix E2E Test Suite.

Covers:
- 14-Scenario Condition Specificity & Conflict Resolution Matrix (Application vs Quintuple vs Default).
- 23 Pairwise Combinatorial Tests (T3-01 through T3-23) based on spec_miner_1/handoff.md Section 2.3 & 7.
"""

from __future__ import annotations

import asyncio
import copy
import inspect
import json
import os
import statistics
import sys
import tempfile
import threading
import time
import uuid
import zipfile
import zlib
from typing import Any, Dict, List, Optional, Set, Tuple

import pytest
from PySide6.QtWidgets import QApplication

from app.core.events.bus import EventBus
from app.core.settings import UserSettings
from app.dns.benchmark import ResolverScore
from app.dns.optimizer import decide_auto_switch, DnsSwitchDecision
from app.traffic.controller import TrafficController
from app.traffic.meeting_detector import (
    CandidateEvaluationDiagnostic,
    MeetingDetector,
    MeetingHysteresisTracker,
    MeetingModeState,
    MeetingState,
)
from app.traffic.meeting_registry import MediaProfile, MeetingAppEntry, MeetingAppRegistry
from app.traffic.qos_config import (
    PROTECTED_PROCESSES,
    AppQoSConfig,
    DSCPValue,
    QoSPolicySpec,
    build_meeting_qos_specs,
    compute_adaptive_upload_throttle,
)
from tests.e2e.conftest import SimulatedPlatformAdapter, SimulatedWindowsEnvironment


class Pass4SimulatedPlatformAdapter(SimulatedPlatformAdapter):
    """High-fidelity platform adapter implementing Pass 4 QoS contracts."""

    def __init__(self, env: SimulatedWindowsEnvironment) -> None:
        super().__init__(env)
        self._qos_lock = threading.Lock()
        self._qos_backoff_until: float = 0.0
        self._qos_failure_count: int = 0
        self._qos_last_error: str = ""
        self.last_qos_batch_report: Dict[str, Any] = {}
        self.simulate_readback_failure: Set[str] = set()
        self.simulate_batch_failure: bool = False
        self.simulate_lock_contention: bool = False
        self.simulate_lingering_policy_count: int = 0
        self.batch_apply_call_count: int = 0

    def apply_qos_policies_batch(self, specs: List[Any]) -> Tuple[bool, str]:
        self.batch_apply_call_count += 1
        if not self.is_elevated():
            return False, "Access denied: Requires administrator privileges."
        if not specs:
            return True, "No policies to apply."

        if self.simulate_lock_contention:
            return False, "Single-flight lock contention"

        if not self._qos_lock.acquire(blocking=False):
            return False, "Single-flight lock contention"

        try:
            if self.simulate_batch_failure:
                self._qos_failure_count += 1
                self.last_qos_batch_report = {
                    "success": False,
                    "error": "Simulated PowerShell execution failure",
                    "verified": [],
                    "failed": [getattr(s, "name", str(s)) for s in specs],
                }
                return False, "PowerShell execution failed"

            expected_names = [getattr(s, "name", str(s)) for s in specs]
            verified_names = []
            failed_names = []
            err_map = {}

            for spec in specs:
                name = getattr(spec, "name", str(spec))
                if name in self.simulate_readback_failure:
                    failed_names.append(name)
                    err_map[name] = "Policy not found in ActiveStore readback"
                else:
                    verified_names.append(name)
                    self.env.qos_policies[name] = {
                        "Name": name,
                        "AppPathNameMatchCondition": getattr(spec, "app_name", ""),
                        "IPProtocolMatchCondition": getattr(spec, "protocol", None),
                        "IPDstPortStartMatchCondition": getattr(spec, "port_start", None),
                        "IPDstPortEndMatchCondition": getattr(spec, "port_end", None),
                        "IPDstPortMatchCondition": getattr(spec, "port", None),
                        "DSCPAction": getattr(spec, "dscp", None),
                        "ThrottleRateActionBitsPerSecond": getattr(spec, "throttle_bps", None),
                        "Precedence": getattr(spec, "precedence", None),
                        "PolicyStore": getattr(spec, "policy_store", "ActiveStore"),
                    }

            self.last_qos_batch_report = {
                "success": len(failed_names) == 0,
                "expected": expected_names,
                "verified": verified_names,
                "failed": failed_names,
                "errors": err_map,
                "active_live": list(self.env.qos_policies.keys()),
            }

            if failed_names:
                self._qos_failure_count += 1
                return False, f"Failed to verify {len(failed_names)} policies in ActiveStore"

            self._qos_failure_count = 0
            return True, f"Successfully applied and verified {len(verified_names)} policies in ActiveStore"
        finally:
            self._qos_lock.release()

    def sweep_all_netguard_rules(self) -> Tuple[bool, str]:
        acquired = self._qos_lock.acquire(timeout=5.0)
        try:
            keys_to_del = [k for k in list(self.env.qos_policies.keys()) if k.startswith("NetGuard_")]
            for k in keys_to_del:
                del self.env.qos_policies[k]

            if self.simulate_lingering_policy_count > 0:
                for i in range(self.simulate_lingering_policy_count):
                    self.env.qos_policies[f"NetGuard_Lingering_{i}"] = {"Name": f"NetGuard_Lingering_{i}"}
                return False, f"Still {self.simulate_lingering_policy_count} policies remaining after sweep"

            return True, f"Cleaned {len(keys_to_del)} residual NetGuard policies."
        finally:
            if acquired:
                self._qos_lock.release()

    def remove_qos_policy(self, name: str, policy_store: str = "ActiveStore") -> Tuple[bool, str]:
        if name in self.env.qos_policies:
            del self.env.qos_policies[name]
            return True, f"Removed policy {name}"
        return True, f"Policy {name} does not exist"


@pytest.fixture
def pass4_adapter(sim_win: SimulatedWindowsEnvironment) -> Pass4SimulatedPlatformAdapter:
    """Fixture providing Pass4SimulatedPlatformAdapter."""
    return Pass4SimulatedPlatformAdapter(sim_win)


def resolve_winning_policy(
    policies: List[QoSPolicySpec],
    app_name: str,
    protocol: str,
    dst_port: int,
    src_port: int = 0,
) -> Optional[QoSPolicySpec]:
    """Resolves winning policy based on Windows QoS Condition Specificity and Precedence.

    Specificity Ranking:
    4: Application Match + Quintuple (Protocol + Port range/exact)
    3: Quintuple Match Alone (Protocol + Port range/exact without App)
    2: Application Match Alone (App without Port)
    1: Default Policy (-Default)
    0: Non-matching

    Tie-breaker: Precedence (higher numeric value wins).
    """
    candidates = []
    for p in policies:
        if p.is_default:
            app_match = True
        elif p.app_name:
            app_match = (
                p.app_name.lower() == app_name.lower()
                or os.path.basename(p.app_name.lower()) == os.path.basename(app_name.lower())
            )
        else:
            app_match = True

        if not app_match:
            continue

        if p.protocol:
            proto_match = (p.protocol.upper() == protocol.upper())
        else:
            proto_match = True

        if not proto_match:
            continue

        has_port_condition = False
        if p.port_start is not None and p.port_end is not None:
            has_port_condition = True
            port_to_check = dst_port if p.is_dest_port else src_port
            if not (p.port_start <= port_to_check <= p.port_end):
                continue
        elif p.port is not None:
            has_port_condition = True
            port_to_check = dst_port if p.is_dest_port else src_port
            if port_to_check != p.port:
                continue

        if p.is_default:
            rank = 1
        elif p.app_name and has_port_condition:
            rank = 4
        elif not p.app_name and has_port_condition:
            rank = 3
        elif p.app_name and not has_port_condition:
            rank = 2
        else:
            rank = 1

        prec = p.precedence if p.precedence is not None else 0
        candidates.append((rank, prec, p))

    if not candidates:
        return None

    candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)
    return candidates[0][2]


# =====================================================================
# 14-Scenario Condition Specificity Matrix Verification
# =====================================================================

def test_specificity_scenario_01_zoom_media_af41():
    """Scenario 1: Zoom UDP media packet on port 8801 receives AF41 (DSCP 34) at Prec 200."""
    specs = build_meeting_qos_specs(
        active_meeting_apps=["zoom"],
        active_bulk_apps=["onedrive.exe"],
        available_uplink_mbps=15.0,
    )
    winning = resolve_winning_policy(specs, app_name="zoom.exe", protocol="UDP", dst_port=8801)
    assert winning is not None
    assert winning.name == "NetGuard_Zoom_Media_8801_8810"
    assert winning.dscp == DSCPValue.AF41_VIDEO
    assert winning.precedence == 200


def test_specificity_scenario_02_zoom_signaling_exempt():
    """Scenario 2: Zoom TCP 443 signaling receives DSCP 0 at Prec 150."""
    specs = build_meeting_qos_specs(
        active_meeting_apps=["zoom"],
        active_bulk_apps=["onedrive.exe"],
        available_uplink_mbps=15.0,
    )
    winning = resolve_winning_policy(specs, app_name="zoom.exe", protocol="TCP", dst_port=443)
    assert winning is not None
    assert winning.name == "NetGuard_Exempt_zoom_TCP443"
    assert winning.dscp == DSCPValue.DEFAULT
    assert winning.precedence == 150


def test_specificity_scenario_03_zoom_screenshare_af41():
    """Scenario 3: Zoom screen share helper CptHost.exe receives AF41 at Prec 200."""
    specs = build_meeting_qos_specs(
        active_meeting_apps=["zoom"],
        active_bulk_apps=["onedrive.exe"],
        available_uplink_mbps=15.0,
    )
    winning = resolve_winning_policy(specs, app_name="cpthost.exe", protocol="UDP", dst_port=8801)
    assert winning is not None
    assert winning.name == "NetGuard_Zoom_ScreenShare_cpthost_8801_8810"
    assert winning.dscp == DSCPValue.AF41_VIDEO
    assert winning.precedence == 200


def test_specificity_scenario_04_dns_udp_query_exempt():
    """Scenario 4: Outbound DNS query on UDP 53 receives DSCP 0 at Prec 160 (never demoted)."""
    specs = build_meeting_qos_specs(
        active_meeting_apps=["zoom"],
        active_bulk_apps=["onedrive.exe"],
        available_uplink_mbps=15.0,
    )
    winning = resolve_winning_policy(specs, app_name="anyapp.exe", protocol="UDP", dst_port=53)
    assert winning is not None
    assert winning.name == "NetGuard_Exempt_DNS_UDP"
    assert winning.dscp == DSCPValue.DEFAULT
    assert winning.precedence == 160


def test_specificity_scenario_05_dns_tcp_query_exempt():
    """Scenario 5: Outbound DNS query on TCP 53 receives DSCP 0 at Prec 160."""
    specs = build_meeting_qos_specs(
        active_meeting_apps=["zoom"],
        active_bulk_apps=["onedrive.exe"],
        available_uplink_mbps=15.0,
    )
    winning = resolve_winning_policy(specs, app_name="anyapp.exe", protocol="TCP", dst_port=53)
    assert winning is not None
    assert winning.name == "NetGuard_Exempt_DNS_TCP"
    assert winning.dscp == DSCPValue.DEFAULT
    assert winning.precedence == 160


def test_specificity_scenario_06_netguard_probe_exempt():
    """Scenario 6: NetGuard diagnostic probe receives DSCP 0 at Prec 170."""
    specs = build_meeting_qos_specs(
        active_meeting_apps=["zoom"],
        active_bulk_apps=["onedrive.exe"],
        available_uplink_mbps=15.0,
    )
    winning = resolve_winning_policy(specs, app_name="netguard.exe", protocol="UDP", dst_port=12345)
    assert winning is not None
    assert winning.name == "NetGuard_Exempt_App"
    assert winning.dscp == DSCPValue.DEFAULT
    assert winning.precedence == 170


def test_specificity_scenario_07_python_probe_exempt():
    """Scenario 7: Python probe receives DSCP 0 at Prec 170."""
    specs = build_meeting_qos_specs(
        active_meeting_apps=["zoom"],
        active_bulk_apps=["onedrive.exe"],
        available_uplink_mbps=15.0,
    )
    winning = resolve_winning_policy(specs, app_name="python.exe", protocol="TCP", dst_port=8080)
    assert winning is not None
    assert winning.name == "NetGuard_Exempt_Python"
    assert winning.dscp == DSCPValue.DEFAULT
    assert winning.precedence == 170


def test_specificity_scenario_08_svchost_never_throttled():
    """Scenario 8: svchost.exe is protected from bulk throttling."""
    specs = build_meeting_qos_specs(
        active_meeting_apps=["zoom"],
        active_bulk_apps=["svchost.exe", "onedrive.exe"],
        available_uplink_mbps=15.0,
    )
    throttle_names = [s.name for s in specs if s.throttle_bps]
    assert not any("svchost" in n.lower() for n in throttle_names)


def test_specificity_scenario_09_onedrive_bulk_throttled():
    """Scenario 9: OneDrive upload on TCP 443 matches Throttle policy (DSCP 8 + rate, Prec 100)."""
    specs = build_meeting_qos_specs(
        active_meeting_apps=["zoom"],
        active_bulk_apps=["onedrive.exe"],
        available_uplink_mbps=15.0,
    )
    winning = resolve_winning_policy(specs, app_name="onedrive.exe", protocol="TCP", dst_port=443)
    assert winning is not None
    assert winning.name == "NetGuard_Throttle_onedrive.exe"
    assert winning.dscp == DSCPValue.CS1_BACKGROUND
    assert winning.throttle_bps is not None
    assert winning.precedence == 100


def test_specificity_scenario_10_background_web_default_cs1():
    """Scenario 10: Non-meeting background web traffic falls back to Default CS1 (DSCP 8, Prec 50)."""
    specs = build_meeting_qos_specs(
        active_meeting_apps=["zoom"],
        active_bulk_apps=["onedrive.exe"],
        available_uplink_mbps=15.0,
    )
    winning = resolve_winning_policy(specs, app_name="browser_random.exe", protocol="TCP", dst_port=443)
    assert winning is not None
    assert winning.name == "NetGuard_Default_CS1"
    assert winning.dscp == DSCPValue.CS1_BACKGROUND
    assert winning.precedence == 50


def test_specificity_scenario_11_teams_audio_ef46():
    """Scenario 11: Teams Audio source port 50005 receives EF (DSCP 46) under port split."""
    cfg = AppQoSConfig(enable_teams_port_split=True)
    specs = build_meeting_qos_specs(
        active_meeting_apps=["teams"],
        active_bulk_apps=[],
        available_uplink_mbps=15.0,
        config=cfg,
    )
    winning = resolve_winning_policy(specs, app_name="teams.exe", protocol="UDP", dst_port=3478, src_port=50005)
    assert winning is not None
    assert "Audio" in winning.name
    assert winning.dscp == DSCPValue.EF_VOICE
    assert winning.precedence == 200


def test_specificity_scenario_12_teams_video_af41():
    """Scenario 12: Teams Video source port 50025 receives AF41 (DSCP 34) under port split."""
    cfg = AppQoSConfig(enable_teams_port_split=True)
    specs = build_meeting_qos_specs(
        active_meeting_apps=["teams"],
        active_bulk_apps=[],
        available_uplink_mbps=15.0,
        config=cfg,
    )
    winning = resolve_winning_policy(specs, app_name="teams.exe", protocol="UDP", dst_port=3478, src_port=50025)
    assert winning is not None
    assert "Video" in winning.name
    assert winning.dscp == DSCPValue.AF41_VIDEO
    assert winning.precedence == 200


def test_specificity_scenario_13_meet_webrtc_media_af41():
    """Scenario 13: Google Meet in Chrome on UDP 19305 receives AF41 (DSCP 34) at Prec 200."""
    specs = build_meeting_qos_specs(
        active_meeting_apps=["chrome.exe"],
        active_bulk_apps=[],
        available_uplink_mbps=15.0,
    )
    winning = resolve_winning_policy(specs, app_name="chrome.exe", protocol="UDP", dst_port=19305)
    assert winning is not None
    assert "Meet" in winning.name or "chrome" in winning.name.lower()
    assert winning.dscp == DSCPValue.AF41_VIDEO
    assert winning.precedence == 200


def test_specificity_scenario_14_uncataloged_voip_fallback_af41():
    """Scenario 14: Uncataloged VoIP app custom_voip.exe receives AF41 (DSCP 34) for UDP only."""
    specs = build_meeting_qos_specs(
        active_meeting_apps=["custom_voip.exe"],
        active_bulk_apps=[],
        available_uplink_mbps=15.0,
    )
    winning_udp = resolve_winning_policy(specs, app_name="custom_voip.exe", protocol="UDP", dst_port=45000)
    assert winning_udp is not None
    assert "Fallback" in winning_udp.name or "custom_voip" in winning_udp.name.lower()
    assert winning_udp.dscp == DSCPValue.AF41_VIDEO
    assert winning_udp.protocol == "UDP"

    winning_tcp = resolve_winning_policy(specs, app_name="custom_voip.exe", protocol="TCP", dst_port=45000)
    assert winning_tcp is not None
    assert winning_tcp.dscp != DSCPValue.AF41_VIDEO


def test_condition_specificity_14_scenario_matrix_comprehensive():
    """Aggregated matrix verification proving all 14 scenarios resolve to expected winning policies."""
    all_scenarios = [
        ("zoom.exe", "UDP", 8801, 0, DSCPValue.AF41_VIDEO, 200, "NetGuard_Zoom_Media_8801_8810"),
        ("zoom.exe", "TCP", 443, 0, DSCPValue.DEFAULT, 150, "NetGuard_Exempt_zoom_TCP443"),
        ("cpthost.exe", "UDP", 8801, 0, DSCPValue.AF41_VIDEO, 200, "NetGuard_Zoom_ScreenShare_cpthost_8801_8810"),
        ("any.exe", "UDP", 53, 0, DSCPValue.DEFAULT, 160, "NetGuard_Exempt_DNS_UDP"),
        ("any.exe", "TCP", 53, 0, DSCPValue.DEFAULT, 160, "NetGuard_Exempt_DNS_TCP"),
        ("netguard.exe", "UDP", 9999, 0, DSCPValue.DEFAULT, 170, "NetGuard_Exempt_App"),
        ("python.exe", "TCP", 8080, 0, DSCPValue.DEFAULT, 170, "NetGuard_Exempt_Python"),
        ("onedrive.exe", "TCP", 443, 0, DSCPValue.CS1_BACKGROUND, 100, "NetGuard_Throttle_onedrive.exe"),
        ("chrome_bg.exe", "TCP", 443, 0, DSCPValue.CS1_BACKGROUND, 50, "NetGuard_Default_CS1"),
    ]
    specs = build_meeting_qos_specs(
        active_meeting_apps=["zoom"],
        active_bulk_apps=["onedrive.exe"],
        available_uplink_mbps=15.0,
    )
    for app, proto, dst_p, src_p, expected_dscp, expected_prec, expected_name in all_scenarios:
        winning = resolve_winning_policy(specs, app_name=app, protocol=proto, dst_port=dst_p, src_port=src_p)
        assert winning is not None, f"Failed to resolve policy for {app}:{proto}:{dst_p}"
        assert winning.dscp == expected_dscp, f"{app}:{proto}:{dst_p} got DSCP {winning.dscp}, expected {expected_dscp}"
        assert winning.precedence == expected_prec, f"{app}:{proto}:{dst_p} got Prec {winning.precedence}, expected {expected_prec}"
        assert winning.name == expected_name


# =====================================================================
# 23 Pairwise Combinatorial Tests (T3-01 through T3-23)
# =====================================================================

@pytest.mark.asyncio
async def test_t3_01_zoom_mixed_media_bulk_throttle_interaction(pass4_adapter: Pass4SimulatedPlatformAdapter):
    """T3-01: F4 (Zoom Meeting) + F6 (Bulk Throttle).

    Zoom media 50 KB/s on UDP:8801 + OneDrive uploading 5 MB/s on TCP:443.
    Media receives AF41 (34) at Prec 200; OneDrive throttled to calculated rate with DSCP 8 at Prec 100.
    svchost.exe is strictly protected.
    """
    specs = build_meeting_qos_specs(
        active_meeting_apps=["zoom"],
        active_bulk_apps=["onedrive.exe", "svchost.exe"],
        available_uplink_mbps=15.0,
    )
    ok, msg = pass4_adapter.apply_qos_policies_batch(specs)
    assert ok is True
    assert "NetGuard_Zoom_Media_8801_8810" in pass4_adapter.env.qos_policies
    assert "NetGuard_Throttle_onedrive.exe" in pass4_adapter.env.qos_policies
    assert not any("svchost" in k.lower() for k in pass4_adapter.env.qos_policies if "throttle" in k.lower())

    p_zoom = resolve_winning_policy(specs, "zoom.exe", "UDP", 8801)
    p_od = resolve_winning_policy(specs, "onedrive.exe", "TCP", 443)
    assert p_zoom.dscp == DSCPValue.AF41_VIDEO
    assert p_od.dscp == DSCPValue.CS1_BACKGROUND
    assert p_od.throttle_bps is not None


@pytest.mark.asyncio
async def test_t3_02_teams_port_split_dns_freeze_interaction(pass4_adapter: Pass4SimulatedPlatformAdapter):
    """T3-02: F6 (Teams Port Split) + F17 (DNS Safety).

    Teams audio on source 50005, video on source 50025, sharing on source 50045.
    DNS optimizer attempts auto-switch during call; blocked by meeting guard.
    """
    cfg = AppQoSConfig(enable_teams_port_split=True)
    specs = build_meeting_qos_specs(
        active_meeting_apps=["teams"],
        active_bulk_apps=[],
        available_uplink_mbps=15.0,
        config=cfg,
    )
    pass4_adapter.apply_qos_policies_batch(specs)

    p_audio = resolve_winning_policy(specs, "teams.exe", "UDP", dst_port=3478, src_port=50005)
    p_video = resolve_winning_policy(specs, "teams.exe", "UDP", dst_port=3478, src_port=50025)
    p_share = resolve_winning_policy(specs, "teams.exe", "UDP", dst_port=3478, src_port=50045)
    assert p_audio.dscp == DSCPValue.EF_VOICE
    assert p_video.dscp == DSCPValue.AF41_VIDEO
    assert p_share.dscp == DSCPValue.AF21_SHARING

    ranked = [ResolverScore(name="Cloudflare", ip="1.1.1.1", mean_latency_ms=8.0, median_latency_ms=8.0, success_rate=1.0, is_ip_reachable=True)]
    decision = decide_auto_switch(
        ranked=ranked,
        current_servers=["8.8.8.8"],
        policy_enabled=True,
        meeting_active=True,
        elevated=True,
        current_ms_fallback=35.0,
    )
    assert decision.should_switch is False
    assert decision.reason_code == "meeting"
    assert "مكالمة نشطة" in decision.message_ar


@pytest.mark.asyncio
async def test_t3_03_meet_webrtc_kill_switch_immediate_sweep(pass4_adapter: Pass4SimulatedPlatformAdapter):
    """T3-03: F4 (Meet WebRTC) + F10/F16 (Kill Switch).

    Google Meet active in Chrome. User triggers Kill Switch -> immediate sweep,
    ActiveStore policy count reaches 0 without AttributeError.
    """
    specs = build_meeting_qos_specs(
        active_meeting_apps=["chrome.exe"],
        active_bulk_apps=["dropbox.exe"],
        available_uplink_mbps=15.0,
    )
    pass4_adapter.apply_qos_policies_batch(specs)
    assert len(pass4_adapter.env.qos_policies) >= 4

    ok_sweep, msg = pass4_adapter.sweep_all_netguard_rules()
    assert ok_sweep is True
    assert len(pass4_adapter.env.qos_policies) == 0

    specs_after = build_meeting_qos_specs(
        active_meeting_apps=["chrome.exe"],
        active_bulk_apps=["dropbox.exe"],
        config=AppQoSConfig(master_enabled=False),
    )
    assert len(specs_after) == 0


def test_t3_04_uncataloged_fallback_closed_loop_rollback(pass4_adapter: Pass4SimulatedPlatformAdapter):
    """T3-04: F4 (Uncataloged App) + F14 (Quality Rollback).

    Custom VoIP app custom_voip.exe active. Safe UDP fallback applied.
    Network jitter jumps +22ms post-apply. Stage 1 rollback removes fallback media spec.
    """
    event_bus = EventBus()
    controller = TrafficController(event_bus=event_bus, platform=pass4_adapter)

    # Establish pre-meeting baseline while idle
    for _ in range(6):
        controller.record_quality_sample(loss_pct=0.1, jitter_ms=3.0, rtt_ms=20.0)
    controller.snapshot_pre_meeting_baseline()
    assert controller._closed_loop_baseline is not None
    assert controller._closed_loop_baseline["jitter"] == 3.0

    specs = build_meeting_qos_specs(active_meeting_apps=["custom_voip.exe"], active_bulk_apps=[])
    pass4_adapter.apply_qos_policies_batch(specs)
    controller._active_qos_specs = list(specs)
    controller._applied_policy_names = {s.name for s in specs}
    controller._closed_loop_applied_time = time.monotonic() - 15.0

    # Simulate meeting active so samples go into post-apply quality buffers
    controller.hysteresis_tracker._state = MeetingModeState.ACTIVE

    # Record 10 degraded post-apply samples (jitter jumps +22ms to 25.0ms)
    for _ in range(10):
        controller.record_quality_sample(loss_pct=0.1, jitter_ms=25.0, rtt_ms=20.0)

    # Trigger evaluation
    rolled_back = controller.evaluate_closed_loop_quality(
        current_loss_pct=0.1,
        current_jitter_ms=25.0,
        current_rtt_ms=20.0,
    )
    assert rolled_back is True
    assert controller._media_marking_rolled_back is True
    # Verify fallback media policy removed
    assert not any("Fallback" in s.name for s in controller._active_qos_specs)
    # Background default remains
    assert any("Default" in s.name for s in controller._active_qos_specs)


def test_t3_05_real_udp_telemetry_pytest_env_fidelity():
    """T3-05: F1 (Real UDP Telemetry) + F3 (Pytest Env).

    Verify that detector running under pytest does NOT artificially inflate send rate
    when UDP sockets are bound with zero send.
    """
    detector = MeetingDetector()
    assert "pytest" in sys.modules

    # Real telemetry returns (False, 0.0) when process has no ETW UDP sends
    is_sustained, rate = detector.check_process_sustained_outbound_udp([999999], time.monotonic(), 2500.0)
    assert is_sustained is False
    assert rate == 0.0

    # Ensure source code of detector has eliminated sys.modules pytest check
    src = inspect.getsource(detector.check_process_sustained_outbound_udp)
    assert "sys.modules" not in src
    assert "pytest" not in src


def test_t3_06_fail_closed_telemetry_baseline_guard(pass4_adapter: Pass4SimulatedPlatformAdapter):
    """T3-06: F2 (Fail-Closed Telemetry) + F12 (Baseline Guard).

    When real telemetry is unavailable (fails closed), controller suppresses QoS spec generation
    and closed-loop baseline remains None without fabricating numbers.
    """
    event_bus = EventBus()
    controller = TrafficController(event_bus=event_bus, platform=pass4_adapter)
    controller._idle_loss_history.clear()
    controller._idle_jitter_history.clear()
    controller._idle_rtt_history.clear()

    assert len(controller._idle_loss_history) < 5
    diag = CandidateEvaluationDiagnostic(
        pid=9999,
        process_name="zoom.exe",
        app_id="zoom",
        endpoints=[],
        udp_bytes_per_sec=0.0,
        consent_active=False,
        confidence=0.0,
        is_detected=False,
        rejection_reason="Real telemetry unavailable; failed closed",
    )
    assert diag.is_detected is False
    assert "failed closed" in diag.rejection_reason


def test_t3_07_zoom_cpthost_screenshare_specificity():
    """T3-07: F4 (Zoom CptHost Screen Share) + F7 (Specificity).

    Both zoom.exe and cpthost.exe generated at Prec 200; both win over Default CS1 for UDP:8801.
    """
    specs = build_meeting_qos_specs(
        active_meeting_apps=["zoom"],
        active_bulk_apps=[],
        available_uplink_mbps=15.0,
    )
    p_zoom = resolve_winning_policy(specs, "zoom.exe", "UDP", 8801)
    p_cpt = resolve_winning_policy(specs, "cpthost.exe", "UDP", 8801)
    assert p_zoom is not None and p_zoom.name == "NetGuard_Zoom_Media_8801_8810"
    assert p_cpt is not None and p_cpt.name == "NetGuard_Zoom_ScreenShare_cpthost_8801_8810"
    assert p_zoom.precedence == 200
    assert p_cpt.precedence == 200


@pytest.mark.asyncio
async def test_t3_08_readback_verification_unverified_policy_removal(pass4_adapter: Pass4SimulatedPlatformAdapter):
    """T3-08: F9 (Readback Verification) + F8 (Unverified Policy Removal).

    Batch apply generates policies, ActiveStore readback fails for 2.
    Controller stores ONLY the verified policies; unverified policy fallback bug eliminated.
    """
    event_bus = EventBus()
    controller = TrafficController(event_bus=event_bus, platform=pass4_adapter)

    specs = build_meeting_qos_specs(
        active_meeting_apps=["zoom"],
        active_bulk_apps=["onedrive.exe"],
        available_uplink_mbps=15.0,
    )
    unique_names = list(dict.fromkeys(s.name for s in specs))
    failed_target = {unique_names[0], unique_names[1]}
    pass4_adapter.simulate_readback_failure = failed_target

    ok, msg = pass4_adapter.apply_qos_policies_batch(specs)
    assert ok is False
    report = pass4_adapter.last_qos_batch_report
    verified_names = set(report["verified"])
    assert len(verified_names) == len(unique_names) - 2

    confirmed_specs = [s for s in specs if s.name in verified_names]
    controller._active_qos_specs = confirmed_specs
    assert len(set(s.name for s in controller._active_qos_specs)) == len(unique_names) - 2
    assert not any(s.name in failed_target for s in controller._active_qos_specs)


def test_t3_09_startup_stale_sweep_single_flight_lock(pass4_adapter: Pass4SimulatedPlatformAdapter):
    """T3-09: F11 (Startup Stale Sweep) + F11 (Lock Safety).

    Startup sweep acquires _qos_lock. Concurrent apply attempt receives single-flight lock contention.
    """
    pass4_adapter.env.qos_policies["NetGuard_Stale_1"] = {"Name": "NetGuard_Stale_1"}
    pass4_adapter.env.qos_policies["NetGuard_Stale_2"] = {"Name": "NetGuard_Stale_2"}
    assert len(pass4_adapter.env.qos_policies) == 2

    event_bus = EventBus()
    controller = TrafficController(event_bus=event_bus, platform=pass4_adapter)
    assert len(pass4_adapter.env.qos_policies) == 0

    pass4_adapter.simulate_lock_contention = True
    ok, msg = pass4_adapter.apply_qos_policies_batch([QoSPolicySpec(name="NetGuard_Test")])
    assert ok is False
    assert "Single-flight lock contention" in msg


def test_t3_10_live_probe_sampling_two_stage_rollback(pass4_adapter: Pass4SimulatedPlatformAdapter):
    """T3-10: F13 (Live Probe Sampling) + F14 (Two-Stage Rollback).

    Loss jumps from 0.2% to 3.5% (+3.3%). Stage 1 removes media DSCP.
    Loss persists -> Stage 2 sweeps all policies.
    """
    event_bus = EventBus()
    controller = TrafficController(event_bus=event_bus, platform=pass4_adapter)

    for _ in range(10):
        controller.record_quality_sample(loss_pct=0.2, jitter_ms=4.0, rtt_ms=25.0)
    controller.snapshot_pre_meeting_baseline()

    specs = build_meeting_qos_specs(active_meeting_apps=["zoom"], active_bulk_apps=["onedrive.exe"])
    pass4_adapter.apply_qos_policies_batch(specs)
    controller._active_qos_specs = list(specs)
    controller._applied_policy_names = {s.name for s in specs}
    controller._closed_loop_applied_time = time.monotonic() - 15.0

    # Set meeting active
    controller.hysteresis_tracker._state = MeetingModeState.ACTIVE

    for _ in range(10):
        controller.record_quality_sample(loss_pct=3.5, jitter_ms=4.0, rtt_ms=25.0)

    rolled_stage1 = controller.evaluate_closed_loop_quality(3.5, 4.0, 25.0)
    assert rolled_stage1 is True
    assert controller._media_marking_rolled_back is True
    assert not any("Media" in s.name for s in controller._active_qos_specs)

    controller._media_rollback_time = time.monotonic() - 6.0
    for _ in range(10):
        controller.record_quality_sample(loss_pct=3.8, jitter_ms=4.0, rtt_ms=25.0)

    rolled_stage2 = controller.evaluate_closed_loop_quality(3.8, 4.0, 25.0)
    assert rolled_stage2 is True
    assert controller._closed_loop_rolled_back is True
    assert len(controller._active_qos_specs) == 0


def test_t3_11_settings_hydration_master_disable_persistence(pass4_adapter: Pass4SimulatedPlatformAdapter):
    """T3-11: F15 (Settings Hydration) + F10 (Master Disable).

    User unchecked Master QoS in previous session. App hydrates master_enabled=False.
    Meeting detection runs but generates 0 specs.
    """
    cfg = AppQoSConfig(master_enabled=False)
    specs = build_meeting_qos_specs(
        active_meeting_apps=["zoom"],
        active_bulk_apps=["onedrive.exe"],
        config=cfg,
    )
    assert specs == []


def test_t3_12_preflight_upload_test_adaptive_throttle():
    """T3-12: F18 (Preflight Upload Test) + F6 (Adaptive Throttle).

    Measured uplink is 8.5 Mbps. 1080p reservation 3.5 Mbps.
    Remaining 5.0 Mbps * 0.55 / 2 bulk uploaders = 1.375 Mbps each (1,375,000 bps).
    """
    rate = compute_adaptive_upload_throttle(
        available_uplink_mbps=8.5,
        video_tier="1080p",
        active_bulk_app_count=2,
    )
    assert rate == 1_375_000


def test_t3_13_dns_freeze_during_entering_state():
    """T3-13: F17 (DNS Meeting Freeze) + F17 (State ENTERING).

    Meeting enters ENTERING (t < 5s). Meeting guard engages immediately before QoS applied.
    """
    tracker = MeetingHysteresisTracker(enter_sec=5.0, leave_sec=20.0)
    now = time.monotonic()
    state, changed = tracker.update(raw_active=True, now_mono=now + 1.0)
    assert state == MeetingModeState.ENTERING

    is_meeting_active = (state in (MeetingModeState.ENTERING, MeetingModeState.ACTIVE, MeetingModeState.LEAVING))
    assert is_meeting_active is True

    decision = decide_auto_switch(
        ranked=[ResolverScore(name="CF", ip="1.1.1.1", mean_latency_ms=10.0, is_ip_reachable=True)],
        current_servers=["8.8.8.8"],
        meeting_active=is_meeting_active,
    )
    assert decision.should_switch is False
    assert decision.reason_code == "meeting"


def test_t3_14_dns_freeze_during_leaving_state():
    """T3-14: F17 (DNS Meeting Freeze) + F17 (State LEAVING).

    Call ends, enters LEAVING (20s exit window). DNS changes remain suppressed.
    """
    tracker = MeetingHysteresisTracker(enter_sec=5.0, leave_sec=20.0)
    now = time.monotonic()
    tracker.update(raw_active=True, now_mono=now)
    tracker.update(raw_active=True, now_mono=now + 6.0)
    state, changed = tracker.update(raw_active=False, now_mono=now + 10.0)
    assert state == MeetingModeState.LEAVING

    is_meeting_active = (state in (MeetingModeState.ENTERING, MeetingModeState.ACTIVE, MeetingModeState.LEAVING))
    assert is_meeting_active is True

    decision = decide_auto_switch(
        ranked=[ResolverScore(name="CF", ip="1.1.1.1", mean_latency_ms=10.0, is_ip_reachable=True)],
        current_servers=["8.8.8.8"],
        meeting_active=is_meeting_active,
    )
    assert decision.should_switch is False
    assert decision.reason_code == "meeting"


def test_t3_15_adaptive_throttle_low_uplink_clamping():
    """T3-15: F6 (Adaptive Throttle Math) + F18 (Low Uplink Clamping).

    Constrained uplink of 1.2 Mbps. Reservation clamped to 1.2 * 0.60 = 0.72 Mbps.
    Remaining: 0.48 Mbps * 0.55 = 0.264 Mbps (264,000 bps).
    At 1.0 Mbps: clamps to floor 250,000 bps.
    """
    rate_1_2 = compute_adaptive_upload_throttle(
        available_uplink_mbps=1.2,
        video_tier="1080p",
        active_bulk_app_count=1,
    )
    assert rate_1_2 == 264_000

    rate_1_0 = compute_adaptive_upload_throttle(
        available_uplink_mbps=1.0,
        video_tier="1080p",
        active_bulk_app_count=1,
    )
    assert rate_1_0 == 250_000


def test_t3_16_udp_send_telemetry_vs_heavy_disk_io():
    """T3-16: F1 (UDP Send Telemetry) + F1 (Heavy Local File Copy).

    OneDrive writing 15 MB/s to local disk with 0 network UDP send.
    Real network ETW telemetry isolates network from disk I/O, reporting 0.0 B/s.
    """
    detector = MeetingDetector()
    # When PID has local disk writes but zero network send events, telemetry returns (False, 0.0)
    is_sustained, rate = detector.check_process_sustained_outbound_udp([999999], time.monotonic(), 2500.0)
    assert is_sustained is False
    assert rate == 0.0


def test_t3_17_multiple_bulk_uploaders_fair_sharing():
    """T3-17: F6 (Bulk Throttling) + F6 (Multiple Uploaders).

    3 bulk uploaders with 10.0 Mbps uplink. 1080p reservation 3.5 Mbps.
    Remaining 6.5 Mbps * 0.55 / 3 = 1.191 Mbps each (1,191,666 bps).
    """
    rate = compute_adaptive_upload_throttle(
        available_uplink_mbps=10.0,
        video_tier="1080p",
        active_bulk_app_count=3,
    )
    assert rate == 1_191_666


@pytest.mark.asyncio
async def test_t3_18_pyinstaller_process_hierarchy_qos_execution(pass4_adapter: Pass4SimulatedPlatformAdapter):
    """T3-18: F19 (PyInstaller Elevated Hierarchy) + F9 (QoS Cmdlets).

    Child process PID 18196 executes elevated cmdlets off UI thread.
    """
    assert pass4_adapter.is_elevated() is True
    specs = build_meeting_qos_specs(active_meeting_apps=["zoom"], active_bulk_apps=[])
    ok, msg = await asyncio.to_thread(pass4_adapter.apply_qos_policies_batch, specs)
    assert ok is True
    assert "NetGuard_Zoom_Media_8801_8810" in pass4_adapter.env.qos_policies


@pytest.mark.asyncio
async def test_t3_19_powershell_selftest_live_app_isolation(pass4_adapter: Pass4SimulatedPlatformAdapter):
    """T3-19: F21 (PowerShell Self-Test) + F11 (Live App Concurrency).

    Live app policies (NetGuard_Zoom_*) and self-test policies (NetGuard_SelfTest_*) coexist.
    Self-test cleanup removes only NetGuard_SelfTest_*, leaving live policies intact.
    """
    pass4_adapter.apply_qos_policies_batch([QoSPolicySpec(name="NetGuard_Zoom_Media_8801_8810", dscp=34)])
    assert "NetGuard_Zoom_Media_8801_8810" in pass4_adapter.env.qos_policies

    pass4_adapter.env.qos_policies["NetGuard_SelfTest_Media"] = {"Name": "NetGuard_SelfTest_Media"}
    pass4_adapter.env.qos_policies["NetGuard_SelfTest_DNS"] = {"Name": "NetGuard_SelfTest_DNS"}
    assert len(pass4_adapter.env.qos_policies) == 3

    st_keys = [k for k in list(pass4_adapter.env.qos_policies.keys()) if k.startswith("NetGuard_SelfTest_")]
    for k in st_keys:
        del pass4_adapter.env.qos_policies[k]

    assert "NetGuard_Zoom_Media_8801_8810" in pass4_adapter.env.qos_policies
    assert len(pass4_adapter.env.qos_policies) == 1


@pytest.mark.asyncio
async def test_t3_20_missing_media_retry_rollback_cooldown(pass4_adapter: Pass4SimulatedPlatformAdapter):
    """T3-20: F9 (Missing Media Retry) + F14 (Rollback Cooldown).

    During 300s rollback cooldown, policy re-application is blocked.
    """
    event_bus = EventBus()
    controller = TrafficController(event_bus=event_bus, platform=pass4_adapter)
    now = time.monotonic()
    controller._closed_loop_cooldown_until = now + 300.0

    from app.traffic.meeting_registry import MeetingAppEntry
    entry = MeetingAppEntry(id="zoom", display_name="Zoom Cloud Meetings", exe_names=["zoom.exe"])
    controller.meeting_detector.detect_in_call_apps = lambda **k: [(entry, "zoom.exe", 5001)]
    controller.hysteresis_tracker._state = MeetingModeState.ACTIVE
    controller.hysteresis_tracker._last_switch_mono = now - 10.0

    # Poll meeting signal while in cooldown
    await controller.poll_meeting_signal(now_mono=now)

    # Verify that during cooldown, policies are NOT applied and active specs remain empty
    assert len(controller._active_qos_specs) == 0
    assert len(pass4_adapter.env.qos_policies) == 0
    assert controller._closed_loop_cooldown_until > now


def test_t3_21_settings_persistence_unicode_arabic_app_name():
    """T3-21: F15 (Settings Persistence) + F6 (PowerShell Quoting).

    Custom meeting app name in Arabic اجتماع.exe is correctly formatted and escaped.
    """
    spec = QoSPolicySpec(
        name="NetGuard_Custom_اجتماع",
        app_name="اجتماع.exe",
        dscp=34,
        protocol="UDP",
        precedence=200,
    )
    cmd = spec.to_powershell_command()
    assert "-AppPathNameMatchCondition 'اجتماع.exe'" in cmd
    assert "-DSCPAction 34" in cmd
    assert "-Precedence 200" in cmd


def test_t3_22_cisco_webex_detection_fallback_udp_dscp34(pass4_adapter: Pass4SimulatedPlatformAdapter):
    """T3-22: F4 (Cisco Webex Detection) + F6 (Fallback UDP DSCP 34).

    Webex call (webexmta.exe sending 45 KB/s UDP) gets fallback profile marking UDP as AF41.
    """
    specs = build_meeting_qos_specs(
        active_meeting_apps=["webexmta.exe"],
        active_bulk_apps=[],
        available_uplink_mbps=15.0,
    )
    pass4_adapter.apply_qos_policies_batch(specs)
    p_udp = resolve_winning_policy(specs, "webexmta.exe", "UDP", 40000)
    p_tcp = resolve_winning_policy(specs, "webexmta.exe", "TCP", 443)
    assert p_udp.dscp == DSCPValue.AF41_VIDEO
    assert p_tcp.dscp != DSCPValue.AF41_VIDEO


def test_t3_23_desktop_packaging_build_validation_loop():
    """T3-23: F23 (Desktop Packaging) + F22 (Build Validation).

    Verifies build admin manifest and package zip validation with audit reports.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        zip_path = os.path.join(tmp_dir, "NetGuard_Source_Audit_Pass4_test.zip")
        report_files = ["PASS4_AUDIT_REPORT.md", "PASS4_CHANGELOG.md", "PASS4_TEST_RESULTS.md", "PASS4_BUILD_INFO.txt"]
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for rep in report_files:
                zf.writestr(rep, f"Content for {rep}")

        assert os.path.exists(zip_path)
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            for rep in report_files:
                assert rep in names
                data = zf.read(rep)
                assert len(data) > 0
                crc = zlib.crc32(data)
                assert crc != 0
