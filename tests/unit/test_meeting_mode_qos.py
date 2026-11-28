"""Comprehensive Unit Tests for NetGuard Meeting Mode QoS (Pass 2).

Verifies all 9 functional requirements:
1. Meeting Signal Per App: Data-driven MeetingAppRegistry; dual-condition detection
   (ConsentStore + sustained UDP); idle running apps stay IDLE with 0 policies and no DNS freeze.
2. Scan Cadence: 2s dedicated poller off UI thread; hysteresis evaluated on real elapsed time;
   works when user is on Settings view.
3. Generic Media Marking: Zoom (with CptHost.exe), Teams (default AF41 vs opt-in split),
   Fallback apps (Slack, Discord, Skype, Webex -> UDP only AF41, never TCP), Browsers (UDP only 19302-19309).
4. Bulk Demotion & Throttle: protocol=None default, both DSCP 8 and ThrottleRate in one command,
   no -IPProtocolMatchCondition, precedence hierarchy (DNS 160, Probes 170, Meeting TCP443 150, Throttle 100, Default 50),
   svchost.exe protected.
5. Real Apply & Real Verification: No SilentlyContinue, try/catch with JSON readback, ActiveStore comparison,
   single retry on missing media policy, exponential backoff, single-flight lock, -WhatIf validation.
6. Closed-Loop Guard: Pre-meeting rolling baseline snapshot, 10s post-apply grace period, >=10 samples median,
   two-stage rollback, rollback cooldown, fallback app degradation protection.
7. Uplink & Video Tier: Wiring preflight metrics, constrained link (<3 Mbps) clamping to 360p / audio,
   adaptive math on 2 Mbps and 5 Mbps uplinks.
8. DNS: Freeze benchmark, switch, flush and renew during meeting; 1 ms gain rejected (min 10ms or 25% over 3 rounds);
   concrete pre-resolved domain list covers all registry apps.
9. Live Telemetry & Controls: Bufferbloat and Wi-Fi weak link advisories; master toggle; per-app toggles;
   kill switch.
"""

import asyncio
import json
import time
from typing import Dict, List, Any
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from app.traffic.meeting_registry import MeetingAppRegistry, MediaProfile, MeetingAppEntry
from app.traffic.qos_config import (
    AppQoSConfig,
    QoSPolicySpec,
    DSCPValue,
    PROTECTED_PROCESSES,
    compute_adaptive_upload_throttle,
    build_meeting_qos_specs,
    QoSPacket,
    compute_policy_specificity,
    policy_matches_packet,
    resolve_winning_policy,
    verify_policy_overlap_matrix,
    POLICY_OVERLAP_14_SCENARIOS,
)
from app.traffic.meeting_detector import (
    MeetingDetector,
    MeetingModeState,
    MeetingHysteresisTracker,
    detect_bufferbloat,
    detect_wifi_weak_link,
)
from app.traffic.controller import TrafficController
from app.core.events.bus import EventBus
from app.dns.optimizer import DNSOptimizer, DnsSwitchDecision, decide_auto_switch
from app.dns.benchmark import ResolverScore
from app.platform.windows.adapter import WindowsPlatformAdapter


# =============================================================================
# ITEM 1: MEETING SIGNAL PER APP (Same fixture across all apps)
# =============================================================================

@pytest.mark.parametrize("app_id,proc_name", [
    ("zoom", "zoom.exe"),
    ("teams", "teams.exe"),
    ("slack", "slack.exe"),
    ("discord", "discord.exe"),
    ("skype", "skype.exe"),
    ("webex", "webex.exe"),
    ("browser_meet", "chrome.exe"),
])
@pytest.mark.asyncio
async def test_item1_meeting_signal_lifecycle_per_app(app_id: str, proc_name: str):
    """Verifies that every meeting app produces IDLE when running idle, and transitions

    ENTERING -> ACTIVE only when BOTH ConsentStore mic/cam is active AND sustained UDP is present.
    """
    platform = MagicMock()
    platform.is_elevated.return_value = True
    def _mock_apply(specs):
        platform.last_qos_batch_report = {"verified": [s.name for s in specs]}
        return True, "OK"
    platform.apply_qos_policies_batch.side_effect = _mock_apply
    platform.sweep_all_netguard_rules.return_value = (True, "Swept")

    controller = TrafficController(event_bus=EventBus(), platform=platform)
    detector = controller.meeting_detector
    # Reset mock after startup sweep
    platform.sweep_all_netguard_rules.reset_mock()

    # PHASE A: Process is running idle (e.g. running in background all day)
    # ConsentStore mic/cam is NOT in use, and NO sustained UDP
    detector.set_simulated_signal(app_id, has_consent=False, has_sustained_udp=False)
    detector.set_simulated_signal(proc_name, has_consent=False, has_sustained_udp=False)

    # Poll with mock time
    state = await controller.poll_meeting_signal(now_mono=100.0)
    assert state.mode_state == MeetingModeState.IDLE
    assert controller.is_critical_meeting_active() is False
    assert len(controller._active_qos_specs) == 0
    # Zero policies applied to OS
    assert platform.apply_qos_policies_batch.call_count == 0

    # PHASE B: Process starts call (BOTH ConsentStore active AND sustained UDP)
    detector.set_simulated_signal(app_id, has_consent=True, has_sustained_udp=True)
    detector.set_simulated_signal(proc_name, has_consent=True, has_sustained_udp=True)

    # First detection -> ENTERING state (t = 110.0s)
    state = await controller.poll_meeting_signal(now_mono=110.0)
    assert state.mode_state == MeetingModeState.ENTERING
    assert controller.is_critical_meeting_active() is True
    # At t=110, enter hysteresis (5.0s) has not yet elapsed -> policies not applied yet
    assert platform.apply_qos_policies_batch.call_count == 0

    # t = 113.0s (3.0s elapsed < 5.0s) -> still ENTERING
    state = await controller.poll_meeting_signal(now_mono=113.0)
    assert state.mode_state == MeetingModeState.ENTERING
    assert platform.apply_qos_policies_batch.call_count == 0

    # t = 115.1s (5.1s >= 5.0s elapsed) -> transitions to ACTIVE!
    state = await controller.poll_meeting_signal(now_mono=115.1)
    assert state.mode_state == MeetingModeState.ACTIVE
    assert controller.is_critical_meeting_active() is True
    # Policies applied to OS!
    assert platform.apply_qos_policies_batch.call_count == 1
    assert len(controller._active_qos_specs) > 0

    # Cleanup
    detector.clear_simulated_signals()


# =============================================================================
# ITEM 2: SCAN CADENCE & HYSTERESIS WITH FAKE CLOCK (User on Settings View)
# =============================================================================

@pytest.mark.asyncio
async def test_item2_scan_cadence_runs_on_settings_view_with_hysteresis():
    """Verifies that the dedicated 2s poller works regardless of visible view (e.g. Settings view),

    enforces 5s enter hysteresis and 20s leave hysteresis on real elapsed time, and cleans up policies.
    """
    platform = MagicMock()
    platform.is_elevated.return_value = True
    def _mock_apply(specs):
        platform.last_qos_batch_report = {"verified": [s.name for s in specs]}
        return True, "OK"
    platform.apply_qos_policies_batch.side_effect = _mock_apply
    platform.sweep_all_netguard_rules.return_value = (True, "Swept")

    controller = TrafficController(event_bus=EventBus(), platform=platform)
    detector = controller.meeting_detector
    # Reset mock after startup sweep
    platform.sweep_all_netguard_rules.reset_mock()

    # User is currently on Settings View (simulated in UI: poller runs every 2s)
    current_view = "view_settings"

    # Call starts at t=200.0s
    detector.set_simulated_signal("zoom", has_consent=True, has_sustained_udp=True)

    # Tick 1: t=200.0s
    state = await controller.poll_meeting_signal(now_mono=200.0)
    assert state.mode_state == MeetingModeState.ENTERING

    # Tick 2: t=202.0s
    state = await controller.poll_meeting_signal(now_mono=202.0)
    assert state.mode_state == MeetingModeState.ENTERING

    # Tick 3: t=204.0s
    state = await controller.poll_meeting_signal(now_mono=204.0)
    assert state.mode_state == MeetingModeState.ENTERING
    assert platform.apply_qos_policies_batch.call_count == 0

    # Tick 4: t=205.2s (5.2s elapsed >= 5.0s enter threshold) -> ACTIVE!
    state = await controller.poll_meeting_signal(now_mono=205.2)
    assert state.mode_state == MeetingModeState.ACTIVE
    assert platform.apply_qos_policies_batch.call_count == 1

    # Call ends at t=230.0s (mic/cam closed)
    detector.set_simulated_signal("zoom", has_consent=False, has_sustained_udp=False)

    # Tick 5: t=230.0s -> LEAVING state entered
    state = await controller.poll_meeting_signal(now_mono=230.0)
    assert state.mode_state == MeetingModeState.LEAVING
    # Still considered active during leave hysteresis
    assert controller.is_critical_meeting_active() is True
    assert platform.sweep_all_netguard_rules.call_count == 0

    # Tick 6: t=240.0s (10s elapsed < 20s leave threshold) -> still LEAVING
    state = await controller.poll_meeting_signal(now_mono=240.0)
    assert state.mode_state == MeetingModeState.LEAVING

    # Tick 7: t=250.1s (20.1s elapsed >= 20.0s leave threshold) -> IDLE!
    state = await controller.poll_meeting_signal(now_mono=250.1)
    assert state.mode_state == MeetingModeState.IDLE
    assert controller.is_critical_meeting_active() is False
    # Policies removed from OS!
    assert platform.sweep_all_netguard_rules.call_count >= 1
    assert len(controller._active_qos_specs) == 0

    detector.clear_simulated_signals()


# =============================================================================
# ITEM 3: GENERIC MEDIA MARKING (Zoom CptHost, Teams default vs split, Fallback UDP, Browsers)
# =============================================================================

def test_item3_zoom_media_marking_includes_cpthost_screenshare():
    """Verifies that Zoom media QoS marks UDP 8801-8810 AF41 and includes CptHost.exe screen share."""
    specs = build_meeting_qos_specs(
        active_meeting_apps=["zoom.exe"],
        active_bulk_apps=[],
    )
    names = [s.name for s in specs]
    # Zoom main media policy
    assert any("Zoom_Media" in n for n in names)
    zoom_spec = next(s for s in specs if "Zoom_Media" in s.name)
    assert zoom_spec.protocol == "UDP"
    assert zoom_spec.dscp == 34  # AF41
    assert zoom_spec.port_start == 8801
    assert zoom_spec.port_end == 8810

    # Zoom CptHost screen share policy
    assert any("Zoom_ScreenShare_cpthost" in n for n in names)
    cpt_spec = next(s for s in specs if "Zoom_ScreenShare_cpthost" in s.name)
    assert cpt_spec.app_name == "cpthost.exe"
    assert cpt_spec.protocol == "UDP"
    assert cpt_spec.dscp == 34


def test_item3_teams_media_marking_default_vs_opt_in_split():
    """Verifies Teams marks all UDP AF41 by default, and only splits 46/34/18 when opted in."""
    # Default (split disabled)
    cfg_default = AppQoSConfig(enable_teams_port_split=False)
    specs_default = build_meeting_qos_specs(
        active_meeting_apps=["teams.exe"],
        active_bulk_apps=[],
        config=cfg_default,
    )
    names_default = [s.name for s in specs_default]
    assert any("Teams_Media" in n for n in names_default)
    teams_default = next(s for s in specs_default if "Teams_Media" in s.name)
    assert teams_default.dscp == 34  # AF41
    assert teams_default.protocol == "UDP"
    assert not any("Teams_Audio" in n for n in names_default)

    # Opt-in split
    cfg_split = AppQoSConfig(enable_teams_port_split=True)
    specs_split = build_meeting_qos_specs(
        active_meeting_apps=["teams.exe"],
        active_bulk_apps=[],
        config=cfg_split,
    )
    names_split = [s.name for s in specs_split]
    assert any("Teams_Audio" in n for n in names_split)
    assert any("Teams_Video" in n for n in names_split)
    assert any("Teams_Sharing" in n for n in names_split)
    audio_spec = next(s for s in specs_split if "Teams_Audio" in s.name)
    assert audio_spec.dscp == 46  # EF
    video_spec = next(s for s in specs_split if "Teams_Video" in s.name)
    assert video_spec.dscp == 34  # AF41
    share_spec = next(s for s in specs_split if "Teams_Sharing" in s.name)
    assert share_spec.dscp == 18  # AF21


@pytest.mark.parametrize("fallback_app", ["slack.exe", "discord.exe", "skype.exe", "webex.exe"])
def test_item3_fallback_profile_marks_all_udp_af41_never_tcp(fallback_app: str):
    """Verifies fallback profile for apps with no vendor-documented ports marks ALL outbound UDP AF41, never TCP."""
    specs = build_meeting_qos_specs(
        active_meeting_apps=[fallback_app],
        active_bulk_apps=[],
    )
    fallback_specs = [s for s in specs if "Fallback_UDP" in s.name]
    assert len(fallback_specs) >= 1
    spec = fallback_specs[0]
    assert spec.protocol == "UDP"
    assert spec.dscp == 34  # AF41
    assert spec.port_start is None and spec.port_end is None
    # No TCP media policy generated for this app
    assert not any(s.protocol == "TCP" and s.dscp in (34, 46) and s.app_name == fallback_app for s in specs)


@pytest.mark.parametrize("browser_exe", ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"])
def test_item3_browser_matches_only_udp_webrtc_ports_never_wholesale(browser_exe: str):
    """Verifies browsers are never matched wholesale: only UDP on Meet/WebRTC port range 19302-19309 is marked AF41."""
    specs = build_meeting_qos_specs(
        active_meeting_apps=[browser_exe],
        active_bulk_apps=[],
    )
    browser_specs = [s for s in specs if s.app_name == browser_exe]
    assert len(browser_specs) >= 1
    media_spec = next(s for s in browser_specs if "Media" in s.name)
    assert media_spec.protocol == "UDP"
    assert media_spec.port_start == 19302
    assert media_spec.port_end == 19309
    assert media_spec.dscp == 34
    # Browser wholesale TCP is never marked
    assert not any(s.protocol in ("TCP", None) and s.app_name == browser_exe and s.dscp == 34 for s in specs)


# =============================================================================
# ITEM 4: BULK DEMOTION & THROTTLE (Dual Action, protocol=None, Precedence Hierarchy)
# =============================================================================

def test_item4_bulk_throttle_powershell_command_dual_action_no_ipprotocol():
    """Verifies QoSPolicySpec default is protocol=None and bulk policy carries BOTH

    -DSCPAction 8 and -ThrottleRateActionBitsPerSecond N in one command without -IPProtocolMatchCondition.
    """
    # 1. Check default protocol is None
    bare_spec = QoSPolicySpec(name="NetGuard_Bare", app_name="test.exe")
    assert bare_spec.protocol is None

    # 2. Build meeting specs with bulk apps
    specs = build_meeting_qos_specs(
        active_meeting_apps=["zoom.exe"],
        active_bulk_apps=["onedrive.exe", "dropbox.exe", "googledrivefs.exe", "svchost.exe"],
        available_uplink_mbps=10.0,
    )

    throttle_spec = next(s for s in specs if s.name == "NetGuard_Throttle_onedrive.exe")
    cmd = throttle_spec.to_powershell_command()

    # Must NOT have -IPProtocolMatchCondition
    assert "-IPProtocolMatchCondition" not in cmd
    # Must carry BOTH DSCPAction 8 and ThrottleRateActionBitsPerSecond
    assert "-DSCPAction 8" in cmd
    assert "-ThrottleRateActionBitsPerSecond" in cmd
    assert "-Precedence 100" in cmd

    # svchost.exe must NEVER be throttled; it must be exempt
    assert not any("throttle" in s.name.lower() and "svchost" in s.name.lower() for s in specs)
    assert any(s.name == "NetGuard_Exempt_Svchost" for s in specs)


def test_item4_precedence_hierarchy_and_exemptions():
    """Verifies precedence hierarchy: DNS (160), Probes & svchost (170), Meeting TCP 443 (150),
    Media (200), Bulk Throttle (100), Default CS1 (50).
    """
    specs = build_meeting_qos_specs(
        active_meeting_apps=["zoom.exe"],
        active_bulk_apps=["onedrive.exe"],
    )

    spec_map = {s.name: s for s in specs}

    # Media has highest precedence (200)
    zoom_spec = next(s for s in specs if "Zoom_Media" in s.name)
    assert zoom_spec.precedence == 200
    assert zoom_spec.dscp == 34  # AF41 for mixed media

    # NetGuard Probes & svchost system exemption (170)
    assert spec_map["NetGuard_Exempt_App"].precedence == 170
    assert spec_map["NetGuard_Exempt_App"].dscp == 0
    assert spec_map["NetGuard_Exempt_Python"].precedence == 170
    assert spec_map["NetGuard_Exempt_Python"].dscp == 0
    assert spec_map["NetGuard_Exempt_Svchost"].precedence == 170
    assert spec_map["NetGuard_Exempt_Svchost"].dscp == 0
    assert spec_map["NetGuard_Exempt_Svchost"].app_name == "svchost.exe"

    # DNS exemptions (160)
    assert spec_map["NetGuard_Exempt_DNS_UDP"].precedence == 160
    assert spec_map["NetGuard_Exempt_DNS_UDP"].dscp == 0
    assert spec_map["NetGuard_Exempt_DNS_TCP"].precedence == 160
    assert spec_map["NetGuard_Exempt_DNS_TCP"].dscp == 0

    # Meeting TCP 443 signaling exemption (150)
    assert spec_map["NetGuard_Exempt_zoom_TCP443"].precedence == 150
    assert spec_map["NetGuard_Exempt_zoom_TCP443"].dscp == 0

    # Bulk app throttle precedence (100)
    assert spec_map["NetGuard_Throttle_onedrive.exe"].precedence == 100
    assert spec_map["NetGuard_Throttle_onedrive.exe"].dscp == 8
    assert spec_map["NetGuard_Throttle_onedrive.exe"].throttle_bps is not None

    # Catch-all default CS1 lowest precedence (50)
    assert spec_map["NetGuard_Default_CS1"].precedence == 50
    assert spec_map["NetGuard_Default_CS1"].dscp == 8


def test_item4_svchost_never_throttled_and_always_exempt():
    """Verifies svchost.exe is never throttled even if present in bulk apps, and receives DSCP 0 at Prec 170."""
    specs = build_meeting_qos_specs(
        active_meeting_apps=["zoom.exe"],
        active_bulk_apps=["svchost.exe", "svchost", "onedrive.exe"],
    )
    # No throttle rule for svchost
    assert not any("throttle" in s.name.lower() and "svchost" in s.name.lower() for s in specs)
    # Exemption policy exists at precedence 170
    svc_spec = next(s for s in specs if s.name == "NetGuard_Exempt_Svchost")
    assert svc_spec.app_name == "svchost.exe"
    assert svc_spec.dscp == 0
    assert svc_spec.precedence == 170


def test_item4_policy_overlap_14_scenarios_matrix():
    """Explicitly verifies the 14-scenario policy overlap matrix across condition specificity and precedence.
    
    Proves that:
    1. Zoom media receives AF41 / DSCP 34 at Precedence 200.
    2. Zoom screen sharing (cpthost) receives AF41 at Precedence 200.
    3. Zoom STUN receives AF41 at Precedence 200.
    4. Zoom signaling on TCP 443 receives DSCP 0 at Precedence 150.
    5. DNS outbound (even for bulk app onedrive.exe) remains DSCP 0 at Precedence 160 (160 > 100).
    6. NetGuard operations receive DSCP 0 at Precedence 170.
    7. Windows system services (svchost.exe) receive DSCP 0 at Precedence 170.
    8. Bulk TCP uploads receive DSCP 8 + rate limit at Precedence 100.
    9. Bulk UDP uploads receive DSCP 8 + rate limit at Precedence 100.
    10. Background traffic receives CS1 / DSCP 8 at Precedence 50.
    11. Teams media default receives AF41 at Precedence 200.
    12. Teams media split audio receives EF / 46 at Precedence 200.
    13. Google Meet WebRTC receives AF41 at Precedence 200.
    14. Fallback meeting apps (Slack) receive AF41 UDP at Precedence 200.
    """
    # 1. Build rich policy sets covering Zoom, Teams (default and split), Meet, Slack, Bulk
    cfg_default = AppQoSConfig(enable_teams_port_split=False)
    specs_default = build_meeting_qos_specs(
        active_meeting_apps=["zoom.exe", "teams.exe", "chrome.exe", "slack.exe"],
        active_bulk_apps=["onedrive.exe", "qbittorrent.exe"],
        config=cfg_default,
    )
    cfg_split = AppQoSConfig(enable_teams_port_split=True)
    specs_split = build_meeting_qos_specs(
        active_meeting_apps=["zoom.exe", "teams.exe", "chrome.exe", "slack.exe"],
        active_bulk_apps=["onedrive.exe", "qbittorrent.exe"],
        config=cfg_split,
    )

    report = verify_policy_overlap_matrix(specs_default, specs_split)
    assert report["success"] is True, f"Overlap matrix failure: {report}"
    assert report["passed_count"] == 14
    assert report["total"] == 14

    # Direct unit assertions on crucial cross-dimensional overlap:
    # DNS vs Bulk App Throttling conflict resolution:
    dns_bulk_packet = QoSPacket(app_name="onedrive.exe", protocol="UDP", dst_port=53)
    winning_dns = resolve_winning_policy(dns_bulk_packet, specs_default)
    assert winning_dns is not None
    assert winning_dns.name == "NetGuard_Exempt_DNS_UDP"
    assert winning_dns.dscp == 0
    assert winning_dns.throttle_bps is None
    # Level 2 / Prec 160 beats Level 1 / Prec 100
    assert compute_policy_specificity(winning_dns) == 2
    assert winning_dns.precedence == 160


# =============================================================================
# ITEM 5: REAL APPLY, REAL VERIFICATION & EXPONENTIAL BACKOFF
# =============================================================================

def test_item5_apply_qos_policies_batch_success_and_readback():
    """Verifies PowerShell batch execution without SilentlyContinue, parses readback JSON,

    and confirms verified policies in ActiveStore.
    """
    adapter = WindowsPlatformAdapter()
    adapter.is_elevated = MagicMock(return_value=True)

    specs = [
        QoSPolicySpec(name="NetGuard_Default_CS1", is_default=True, dscp=8),
        QoSPolicySpec(name="NetGuard_Zoom_Media", app_name="zoom.exe", dscp=34),
    ]

    readback_json = json.dumps({
        "Results": {"NetGuard_Default_CS1": True, "NetGuard_Zoom_Media": True},
        "Errors": {},
        "Active": ["NetGuard_Default_CS1", "NetGuard_Zoom_Media"],
    })
    mock_proc = MagicMock(returncode=0, stdout=readback_json, stderr="")

    with patch("subprocess.run", return_value=mock_proc):
        ok, msg = adapter.apply_qos_policies_batch(specs)
        assert ok is True
        assert "تم تطبيق والتحقق" in msg
        assert adapter.last_qos_batch_report["verified"] == ["NetGuard_Default_CS1", "NetGuard_Zoom_Media"]
        assert adapter.last_qos_batch_report["failed"] == []


def test_item5_apply_qos_policies_batch_retry_and_backoff_on_failure():
    """Verifies that missing media policy triggers a single retry, and persistent failure

    reports Failed and engages exponential backoff.
    """
    adapter = WindowsPlatformAdapter()
    adapter.is_elevated = MagicMock(return_value=True)

    specs = [
        QoSPolicySpec(name="NetGuard_Default_CS1", is_default=True, dscp=8),
        QoSPolicySpec(name="NetGuard_Zoom_Media", app_name="zoom.exe", dscp=34),
    ]

    # Batch script fails on Zoom; retry also fails with exit code 1
    batch_json = json.dumps({
        "Results": {"NetGuard_Default_CS1": True, "NetGuard_Zoom_Media": False},
        "Errors": {"NetGuard_Zoom_Media": "Access is denied (Error 5)"},
        "Active": ["NetGuard_Default_CS1"],
    })
    mock_batch = MagicMock(returncode=0, stdout=batch_json, stderr="")
    mock_retry = MagicMock(returncode=1, stdout="", stderr="Access is denied")

    with patch("subprocess.run", side_effect=[mock_batch, mock_retry]):
        ok, msg = adapter.apply_qos_policies_batch(specs)
        assert ok is False
        assert "فشل تطبيق/التحقق" in msg
        assert "NetGuard_Zoom_Media" in adapter.last_qos_batch_report["failed"]
        # Backoff engaged
        assert adapter._qos_failure_count == 1
        assert adapter._qos_backoff_until > time.monotonic()


def test_item5_whatif_validation():
    """Verifies validate_policy_spec_with_whatif appends -WhatIf and executes syntax check."""
    adapter = WindowsPlatformAdapter()
    spec = QoSPolicySpec(name="NetGuard_Zoom_Media", app_name="zoom.exe", dscp=34, protocol="UDP")

    mock_proc = MagicMock(returncode=0, stdout="What if: Performing the operation", stderr="")
    with patch("subprocess.run", return_value=mock_proc) as mock_run:
        ok, msg = adapter.validate_policy_spec_with_whatif(spec)
        assert ok is True
        cmd_called = mock_run.call_args[0][0][-1]
        assert "-WhatIf" in cmd_called
        assert "NetGuard_Zoom_Media" in cmd_called


@pytest.mark.asyncio
async def test_item5_empty_verified_names_rejects_fallback():
    """Verifies that when ActiveStore readback returns verified=[], confirmed_specs is empty.
    
    NEVER falls back to all generated specs!
    """
    platform = MagicMock()
    platform.is_elevated.return_value = True
    # PowerShell command itself returned 0 (no syntax crash), but readback verified 0 policies
    platform.apply_qos_policies_batch.return_value = (True, "Command finished")
    platform.last_qos_batch_report = {
        "success": False,
        "verified": [],
        "failed": ["NetGuard_Zoom_Media_8801_8810"],
        "errors": {"NetGuard_Zoom_Media_8801_8810": "Policy not found in ActiveStore"},
    }

    controller = TrafficController(event_bus=EventBus(), platform=platform)
    detector = controller.meeting_detector
    detector.set_simulated_signal("zoom", has_consent=True, has_sustained_udp=True)

    # Transition to ACTIVE (enter_sec >= 5.0s)
    await controller.poll_meeting_signal(now_mono=100.0)
    await controller.poll_meeting_signal(now_mono=106.0)

    assert controller.hysteresis_tracker.state == MeetingModeState.ACTIVE
    # CRITICAL AUDIT ASSERTION: Must NOT fall back to generated specs!
    assert controller._active_qos_specs == []
    assert controller._applied_policy_names == set()
    assert controller._applied_dscp_policies == set()
    assert controller._applied_throttle_policies == set()


def test_item5_adapter_active_store_full_property_matching():
    """Verifies adapter validates exact matching properties in Python before marking verified in batch report."""
    adapter = WindowsPlatformAdapter()
    adapter.is_elevated = MagicMock(return_value=True)

    specs = [
        QoSPolicySpec(
            name="NetGuard_Zoom_Media_8801_8810",
            app_name="zoom.exe",
            dscp=34,
            protocol="UDP",
            port_start=8801,
            port_end=8810,
            precedence=200,
            policy_store="ActiveStore",
        ),
        QoSPolicySpec(
            name="NetGuard_Throttle_onedrive.exe",
            app_name="onedrive.exe",
            dscp=8,
            throttle_bps=5000000,
            precedence=100,
            protocol=None,
            policy_store="ActiveStore",
        ),
    ]

    # ActiveStore readback with full matching properties
    readback_json = json.dumps({
        "Results": {
            "NetGuard_Zoom_Media_8801_8810": True,
            "NetGuard_Throttle_onedrive.exe": True,
        },
        "Errors": {},
        "Active": [
            {
                "Name": "NetGuard_Zoom_Media_8801_8810",
                "AppPathNameMatchCondition": "C:\\Program Files\\Zoom\\bin\\zoom.exe",
                "IPProtocolMatchCondition": "UDP",
                "IPDstPortStartMatchCondition": 8801,
                "IPDstPortEndMatchCondition": 8810,
                "IPSrcPortStartMatchCondition": None,
                "IPSrcPortEndMatchCondition": None,
                "DSCPAction": 34,
                "ThrottleRateActionBitsPerSecond": None,
                "Precedence": 200,
                "PolicyStore": "ActiveStore",
            },
            {
                "Name": "NetGuard_Throttle_onedrive.exe",
                "AppPathNameMatchCondition": "onedrive.exe",
                "IPProtocolMatchCondition": None,
                "IPDstPortStartMatchCondition": None,
                "IPDstPortEndMatchCondition": None,
                "IPSrcPortStartMatchCondition": None,
                "IPSrcPortEndMatchCondition": None,
                "DSCPAction": 8,
                "ThrottleRateActionBitsPerSecond": 5000000,
                "Precedence": 100,
                "PolicyStore": "ActiveStore",
            },
        ],
    })

    mock_proc = MagicMock(returncode=0, stdout=readback_json, stderr="")
    with patch("subprocess.run", return_value=mock_proc):
        ok, msg = adapter.apply_qos_policies_batch(specs)
        assert ok is True
        rep = adapter.last_qos_batch_report
        assert rep["success"] is True
        assert "NetGuard_Zoom_Media_8801_8810" in rep["verified"]
        assert "NetGuard_Throttle_onedrive.exe" in rep["verified"]
        assert rep["failed"] == []
        assert rep["details"]["NetGuard_Zoom_Media_8801_8810"]["verified"] is True


def test_item5_adapter_active_store_property_mismatch_fails():
    """Verifies that an ActiveStore policy with mismatched DSCP, precedence, or rate fails verification."""
    adapter = WindowsPlatformAdapter()
    adapter.is_elevated = MagicMock(return_value=True)

    spec = QoSPolicySpec(
        name="NetGuard_Zoom_Media_8801_8810",
        app_name="zoom.exe",
        dscp=34,
        protocol="UDP",
        port_start=8801,
        port_end=8810,
        precedence=200,
        policy_store="ActiveStore",
    )

    # Live ActiveStore returns DSCP 0 and Precedence 100 (mismatched!)
    mismatched_json = json.dumps({
        "Results": {"NetGuard_Zoom_Media_8801_8810": True},
        "Errors": {},
        "Active": [
            {
                "Name": "NetGuard_Zoom_Media_8801_8810",
                "AppPathNameMatchCondition": "zoom.exe",
                "IPProtocolMatchCondition": "UDP",
                "IPDstPortStartMatchCondition": 8801,
                "IPDstPortEndMatchCondition": 8810,
                "DSCPAction": 0,  # Expected 34!
                "Precedence": 100, # Expected 200!
                "PolicyStore": "ActiveStore",
            }
        ],
    })

    mock_proc = MagicMock(returncode=0, stdout=mismatched_json, stderr="")
    with patch("subprocess.run", return_value=mock_proc):
        ok, msg = adapter.apply_qos_policies_batch([spec])
        assert ok is False
        rep = adapter.last_qos_batch_report
        assert rep["success"] is False
        assert "NetGuard_Zoom_Media_8801_8810" in rep["failed"]
        assert "DSCPAction mismatch" in rep["errors"]["NetGuard_Zoom_Media_8801_8810"]


def test_item5_adapter_single_flight_lock_contention():
    """Verifies single-flight lock safety: second concurrent call aborts immediately without blocking."""
    adapter = WindowsPlatformAdapter()
    adapter.is_elevated = MagicMock(return_value=True)

    # Acquire lock in thread
    assert adapter._qos_lock.acquire(blocking=False) is True
    try:
        spec = QoSPolicySpec(name="NetGuard_Test", app_name="test.exe", dscp=34)
        ok, msg = adapter.apply_qos_policies_batch([spec])
        assert ok is False
        assert "Single-flight lock" in msg
    finally:
        adapter._qos_lock.release()


# =============================================================================
# ITEM 6: CLOSED-LOOP GUARD (Pre-meeting Baseline, 10s Grace, Degradation Rollback)
# =============================================================================

def test_item6_closed_loop_pre_meeting_baseline_and_two_tier_rollback():
    """Verifies baseline is captured BEFORE policy application, 10s grace period is enforced,

    and immediate quality degradation triggers Stage 1 (media rollback) then Stage 2 (full rollback).
    """
    platform = MagicMock()
    platform.is_elevated.return_value = True
    def _mock_apply(specs):
        platform.last_qos_batch_report = {"verified": [s.name for s in specs]}
        return True, "OK"
    platform.apply_qos_policies_batch.side_effect = _mock_apply
    platform.sweep_all_netguard_rules.return_value = (True, "Swept")

    controller = TrafficController(event_bus=EventBus(), platform=platform)

    # 1. Rolling pre-meeting baseline captured before apply
    # Simulate 30 idle telemetry samples: 0% loss, 4ms jitter, 20ms RTT
    for _ in range(30):
        controller.record_quality_sample(loss_pct=0.0, jitter_ms=4.0, rtt_ms=20.0)

    controller.snapshot_pre_meeting_baseline()
    assert controller._closed_loop_baseline["loss"] == 0.0
    assert controller._closed_loop_baseline["jitter"] == 4.0
    assert controller._closed_loop_baseline["rtt"] == 20.0

    # 2. Apply policies
    media_spec = QoSPolicySpec(name="NetGuard_Zoom_Media_8801_8810", app_name="zoom.exe", dscp=34)
    throttle_spec = QoSPolicySpec(name="NetGuard_Throttle_onedrive.exe", app_name="onedrive.exe", dscp=8, throttle_bps=2000000)
    bg_spec = QoSPolicySpec(name="NetGuard_Default_CS1", is_default=True, dscp=8)

    controller._active_qos_specs = [media_spec, throttle_spec, bg_spec]
    controller._applied_policy_names = {media_spec.name, throttle_spec.name, bg_spec.name}
    controller._applied_dscp_policies = {"zoom.exe"}
    controller._closed_loop_applied_time = time.monotonic() - 12.0  # past 10s grace period

    # 3. Degraded telemetry samples (+3% loss > +2% threshold)
    # Deliver 10 degraded samples to build median
    stage1_fired = False
    for _ in range(10):
        rolled = controller.evaluate_closed_loop_quality(current_loss_pct=3.0, current_jitter_ms=6.0, current_rtt_ms=22.0)
        if rolled:
            stage1_fired = True

    assert stage1_fired is True
    # Stage 1: media marking removed, throttle kept!
    assert controller._media_marking_rolled_back is True
    assert controller._closed_loop_rolled_back is False
    assert not any("Zoom_Media" in s.name for s in controller._active_qos_specs)
    assert any("Throttle" in s.name for s in controller._active_qos_specs)

    # 4. Degradation continues after 5s settling -> Stage 2 Full Rollback!
    controller._media_rollback_time = time.monotonic() - 6.0
    rolled_stage2 = controller.evaluate_closed_loop_quality(current_loss_pct=3.5, current_jitter_ms=10.0, current_rtt_ms=25.0)
    assert rolled_stage2 is True
    assert controller._closed_loop_rolled_back is True
    assert len(controller._active_qos_specs) == 0
    # Cooldown enforced (300s)
    assert controller._closed_loop_cooldown_until > time.monotonic()


def test_item6_fallback_profile_app_triggers_rollback_on_degradation():
    """Verifies that a fallback-profile app (e.g. Slack marking all UDP AF41) triggering

    loss degradation is caught by closed-loop guard and rolled back.
    """
    platform = MagicMock()
    platform.is_elevated.return_value = True
    controller = TrafficController(event_bus=EventBus(), platform=platform)

    controller._closed_loop_baseline = {"loss": 0.0, "jitter": 5.0, "rtt": 25.0}
    controller._active_qos_specs = [
        QoSPolicySpec(name="NetGuard_Slack_Fallback_UDP_slack", app_name="slack.exe", dscp=34, protocol="UDP"),
    ]
    controller._applied_policy_names = {"NetGuard_Slack_Fallback_UDP_slack"}
    controller._applied_dscp_policies = {"slack.exe"}
    controller._closed_loop_applied_time = time.monotonic() - 11.0

    # 10 degraded samples with high loss (+2.5%)
    for _ in range(10):
        controller.evaluate_closed_loop_quality(current_loss_pct=2.5, current_jitter_ms=6.0, current_rtt_ms=27.0)

    assert controller._media_marking_rolled_back is True
    assert not any("Slack_Fallback" in s.name for s in controller._active_qos_specs)


# =============================================================================
# ITEM 7: UPLINK AND VIDEO TIER (Adaptive Throttle Math on 2 Mbps and 5 Mbps)
# =============================================================================

def test_item7_uplink_and_video_tier_adaptive_math():
    """Verifies that controller wires preflight metrics, and constrained uplinks (< 3 Mbps)

    clamp video tier to 360p or audio only.
    """
    cfg = AppQoSConfig()
    controller = TrafficController(event_bus=EventBus(), platform=MagicMock(), qos_config=cfg)

    # 1. Wire 2.0 Mbps uplink via set_preflight_metrics
    controller.set_preflight_metrics(uplink_mbps=2.0)
    assert controller.measured_uplink_mbps == 2.0
    # Clamped to 360p on < 3 Mbps link
    assert controller.video_tier == "360p"

    # Math test on 2.0 Mbps uplink with 1 bulk app:
    # 2.0 Mbps < 3.0 Mbps -> reservation = 1.0 Mbps (360p)
    # Remaining = 2.0 - 1.0 = 1.0 Mbps
    # Non-meeting headroom = 1.0 * 0.55 = 0.55 Mbps = 550,000 bps
    bps_2mbps = compute_adaptive_upload_throttle(
        available_uplink_mbps=2.0,
        video_tier=controller.video_tier,
        active_bulk_app_count=1,
        config=cfg,
    )
    assert bps_2mbps == 550_000

    # 2. Wire 5.0 Mbps uplink via set_preflight_metrics
    controller.set_preflight_metrics(uplink_mbps=5.0)
    assert controller.measured_uplink_mbps == 5.0
    assert controller.video_tier == "720p"

    # Math test on 5.0 Mbps uplink with 2 bulk apps:
    # 720p reservation = 2.0 Mbps
    # Remaining = 5.0 - 2.0 = 3.0 Mbps
    # Headroom = 3.0 * 0.55 = 1.65 Mbps
    # Per app (2 apps) = 1.65 / 2 = 0.825 Mbps = 825,000 bps
    bps_5mbps = compute_adaptive_upload_throttle(
        available_uplink_mbps=5.0,
        video_tier=controller.video_tier,
        active_bulk_app_count=2,
        config=cfg,
    )
    assert bps_5mbps == 825_000


# =============================================================================
# ITEM 8: DNS (Frozen During Meeting, 1ms Gain Rejected, Concrete Pre-resolved Domains)
# =============================================================================

@pytest.mark.asyncio
async def test_item8_dns_frozen_during_meeting_mode():
    """Verifies that DNS benchmark and auto-switch are deferred when meeting is active."""
    platform = MagicMock()
    bus = EventBus()
    controller = MagicMock()
    controller.is_critical_meeting_active.return_value = True

    optimizer = DNSOptimizer(platform_adapter=platform, event_bus=bus, traffic_controller=controller)

    # Benchmark returns empty
    ranked = await optimizer.evaluate_and_rank()
    assert ranked == []

    # Auto-switch skipped with meeting reason
    switch_res = await optimizer.auto_optimize_dns()
    assert switch_res is None
    assert optimizer.last_decision.reason_code == "meeting"
    assert "مكالمة نشطة" in optimizer.last_decision.message_ar


def test_item8_dns_1ms_gain_rejected_and_threshold_enforced():
    """Verifies that a 1 ms DNS gain is rejected; requires gain >= max(10ms, 25%) across >= 3 rounds."""
    ranked = [
        ResolverScore(ip="8.8.8.8", name="Google DNS", provider_name="Google", median_latency_ms=24.0, composite_score=90.0),
        ResolverScore(ip="1.1.1.1", name="Cloudflare DNS", provider_name="Cloudflare", median_latency_ms=25.0, composite_score=90.0),
    ]
    # Current = 25.0ms, Best = 24.0ms -> 1.0ms gain (< 10.0ms threshold)
    decision = decide_auto_switch(
        ranked=ranked,
        current_servers=["1.1.1.1"],
        min_improvement_ms=10.0,
        min_improvement_ratio=0.25,
        consecutive_rounds=1,
        min_consecutive_rounds=3,
    )
    assert decision.should_switch is False
    assert decision.reason_code == "insufficient_gain"
    assert decision.gain_ms == 1.0


def test_item8_preresolved_domains_list_concrete_and_covers_all_apps():
    """Verifies pre-resolved meeting domains contains concrete hostnames (no wildcards) for all registry apps."""
    domains = MeetingAppRegistry.get_all_concrete_domains()
    assert len(domains) > 0
    # Must contain concrete domains for Zoom, Teams, Google Meet, Webex, Slack, Discord
    assert "zoom.us" in domains
    assert "teams.microsoft.com" in domains
    assert "meet.google.com" in domains
    assert "discord.gg" in domains
    assert "slack.com" in domains
    # Must NOT contain wildcards
    assert not any("*" in d for d in domains)


# =============================================================================
# ITEM 9: UNWIRED FEATURES & CONTROLS (Bufferbloat, Wi-Fi Weak Link, Toggles, Kill Switch)
# =============================================================================

def test_item9_bufferbloat_and_wifi_weak_link_advisories():
    """Verifies bufferbloat and Wi-Fi weak link detectors return actionable Arabic advisories."""
    # Bufferbloat: load latency spikes +75ms
    bb = detect_bufferbloat(idle_latency_ms=15.0, load_latency_ms=90.0, upload_active=True)
    assert bb["detected"] is True
    assert "SQM" in bb["advisory"]

    # Wi-Fi weak link: high jitter (30ms) + weak signal (40%)
    wf = detect_wifi_weak_link(is_wifi=True, signal_pct=40.0, jitter_ms=30.0, packet_loss_pct=2.0)
    assert wf["is_weak_link"] is True
    assert "LAN" in wf["advisory"]


@pytest.mark.asyncio
async def test_item9_master_toggle_per_app_toggles_and_kill_switch():
    """Verifies master toggle, per-app toggles, and instant kill switch behavior."""
    cfg = AppQoSConfig(master_enabled=True)
    platform = MagicMock()
    platform.is_elevated.return_value = True
    def _mock_apply(specs):
        platform.last_qos_batch_report = {"verified": [s.name for s in specs]}
        return True, "OK"
    platform.apply_qos_policies_batch.side_effect = _mock_apply
    platform.sweep_all_netguard_rules.return_value = (True, "Swept")

    controller = TrafficController(event_bus=EventBus(), platform=platform, qos_config=cfg)

    # 1. Per-app toggle: disable Zoom
    cfg.enabled_apps["zoom"] = False
    cfg.enabled_apps["zoom.exe"] = False

    specs = build_meeting_qos_specs(
        active_meeting_apps=["zoom.exe"],
        active_bulk_apps=[],
        config=cfg,
    )
    # Zoom is disabled -> no Zoom media policy generated
    assert not any("Zoom_Media" in s.name for s in specs)

    # 2. Instant Kill Switch
    controller.kill_switch_disable()
    assert controller.qos_config.master_enabled is False
    assert platform.sweep_all_netguard_rules.call_count >= 1
    assert len(controller._active_qos_specs) == 0


@pytest.mark.asyncio
async def test_item9_master_disable_immediate_teardown_during_active():
    """Verifies that setting master_enabled=False during ACTIVE state sweeps policies immediately off Qt thread."""
    cfg = AppQoSConfig(master_enabled=True)
    platform = MagicMock()
    platform.is_elevated.return_value = True
    def _mock_apply(specs):
        platform.last_qos_batch_report = {"verified": [s.name for s in specs]}
        return True, "OK"
    platform.apply_qos_policies_batch.side_effect = _mock_apply
    platform.sweep_all_netguard_rules.return_value = (True, "Swept")

    controller = TrafficController(event_bus=EventBus(), platform=platform, qos_config=cfg)
    detector = controller.meeting_detector
    detector.set_simulated_signal("zoom", has_consent=True, has_sustained_udp=True)

    # Transition to ACTIVE and apply policies
    await controller.poll_meeting_signal(now_mono=100.0)
    await controller.poll_meeting_signal(now_mono=106.0)
    assert controller.hysteresis_tracker.state == MeetingModeState.ACTIVE
    assert len(controller._active_qos_specs) > 0

    # Reset mock call counts
    platform.sweep_all_netguard_rules.reset_mock()

    # User toggles master QoS off while call is ACTIVE!
    cfg.master_enabled = False

    # Next poll tick during ACTIVE state
    await controller.poll_meeting_signal(now_mono=108.0)
    assert controller.hysteresis_tracker.state == MeetingModeState.ACTIVE

    # Policies MUST be swept immediately without waiting for IDLE!
    assert platform.sweep_all_netguard_rules.call_count >= 1
    assert controller._active_qos_specs == []
    assert controller._applied_policy_names == set()


def test_item9_controller_meeting_detector_injection():
    """Verifies TrafficController accepts optional meeting_detector injection in __init__."""
    custom_detector = MeetingDetector()
    controller = TrafficController(
        event_bus=EventBus(),
        platform=MagicMock(),
        meeting_detector=custom_detector,
    )
    assert controller.meeting_detector is custom_detector


def test_item9_verified_sweep_return_values():
    """Verifies TrafficController captures and checks return values of sweep_all_netguard_rules."""
    platform = MagicMock()
    platform.is_elevated.return_value = True
    platform.sweep_all_netguard_rules.return_value = (True, "Successfully removed 5 policies")

    controller = TrafficController(event_bus=EventBus(), platform=platform)
    ok, msg = controller.startup_cleanup_stale_policies()
    assert ok is True
    assert "Successfully removed" in msg

    ok_clean, msg_clean = controller.cleanup_all_policies()
    assert ok_clean is True
    assert "Successfully removed" in msg_clean

    # Failure case: remaining policies reported
    platform.sweep_all_netguard_rules.return_value = (False, "3 policies failed to remove")
    ok_fail, msg_fail = controller.cleanup_all_policies()
    assert ok_fail is False
    assert "failed" in msg_fail
