"""Unit tests for Meeting Priority, QoS hierarchy, and Quality Advisor (Stage D)."""

import pytest
from unittest.mock import MagicMock, patch

from app.traffic.meeting_detector import (
    MeetingDetector,
    MeetingState,
    TrafficPriorityClass,
    evaluate_video_readiness,
    generate_post_session_report,
)
from app.traffic.preflight import MeetingPreflightChecker, PreflightReport


def test_d2_priority_class_hierarchy():
    """Browsing must NEVER outrank an active meeting (Item D2)."""
    detector = MeetingDetector()

    # When Zoom is active:
    detector._current_state = MeetingState(is_active=True, app_name="Zoom", process_name="zoom.exe")

    p_zoom = detector.classify_process_priority("zoom.exe", has_meeting_active=True)
    p_chrome = detector.classify_process_priority("chrome.exe", has_meeting_active=True)
    p_onedrive = detector.classify_process_priority("onedrive.exe", has_meeting_active=True)
    p_svchost = detector.classify_process_priority("svchost.exe", has_meeting_active=True)

    # Assert priority hierarchy: REALTIME (1) < INTERACTIVE (2) < BULK (3)
    # Notice: lower number means higher priority in IntEnum!
    assert p_zoom == TrafficPriorityClass.REALTIME
    assert p_chrome == TrafficPriorityClass.INTERACTIVE
    assert p_onedrive == TrafficPriorityClass.BULK
    assert p_svchost == TrafficPriorityClass.PROTECTED

    # Zoom outranks Chrome!
    assert p_zoom < p_chrome
    # Chrome outranks background upload (OneDrive)!
    assert p_chrome < p_onedrive


def test_d8_video_quality_advisor():
    """Video readiness evaluation must calculate honest tier with limiting metric (Item D8)."""
    # 1. 1080p Full HD condition
    r_1080 = evaluate_video_readiness(upload_mbps=4.5, packet_loss_pct=0.0, jitter_ms=5.0)
    assert r_1080["tier"] == "1080p Full HD"
    assert r_1080["is_hd"] is True
    assert r_1080["limiting_metric"] is None

    # 2. 720p HD limited by upload speed (e.g. 2.1 Mbps)
    r_720 = evaluate_video_readiness(upload_mbps=2.1, packet_loss_pct=0.2, jitter_ms=8.0)
    assert r_720["tier"] == "720p HD"
    assert r_720["limiting_metric"] == "سرعة الرفع"
    assert "2.1 Mbps" in r_720["headline"]

    # 3. 360p SD limited by jitter or upload
    r_360 = evaluate_video_readiness(upload_mbps=1.0, packet_loss_pct=1.5, jitter_ms=35.0)
    assert r_360["tier"] == "360p SD"
    assert r_360["is_hd"] is False

    # 4. Audio-only condition
    r_audio = evaluate_video_readiness(upload_mbps=0.3, packet_loss_pct=6.0, jitter_ms=75.0)
    assert r_audio["tier"] == "Audio Only"
    assert "مكالمة صوتية فقط" in r_audio["headline"]


def test_d7_honest_post_session_report():
    """Post-meeting report must never blame local network when router was clean (Item D7)."""
    # Case 1: Excellent call
    rep_ok = generate_post_session_report(
        app_name="Zoom",
        duration_seconds=1800.0,
        avg_latency_ms=18.0,
        max_latency_ms=25.0,
        avg_jitter_ms=2.0,
        packet_loss_pct=0.0,
        local_gateway_latency_ms=1.5,
    )
    assert rep_ok["verdict_type"] == "ok"
    assert "مكالمة ممتازة" in rep_ok["verdict"]

    # Case 2: Stutter occurred, but local router latency was 2.0 ms (clean) -> blame is external!
    rep_ext = generate_post_session_report(
        app_name="Microsoft Teams",
        duration_seconds=1200.0,
        avg_latency_ms=95.0,
        max_latency_ms=180.0,
        avg_jitter_ms=25.0,
        packet_loss_pct=1.2,
        local_gateway_latency_ms=2.0,
    )
    assert rep_ext["verdict_type"] == "external_issue"
    assert "المشكلة من خوادم Microsoft Teams أو الطرف الآخر" in rep_ext["verdict"]
    assert "شبكتك المحلية كانت سليمة تماماً" in rep_ext["verdict"]

    # Case 3: Local router degraded (45 ms) -> blame is local!
    rep_loc = generate_post_session_report(
        app_name="Zoom",
        duration_seconds=900.0,
        avg_latency_ms=85.0,
        max_latency_ms=140.0,
        avg_jitter_ms=22.0,
        packet_loss_pct=2.0,
        local_gateway_latency_ms=45.0,
    )
    assert rep_loc["verdict_type"] == "local_issue"
    assert "تراجع جودة الاتصال المحلي بالراوتر" in rep_loc["verdict"]


def test_d5_preflight_check():
    """Pre-flight check evaluates gateway, DNS, Wi-Fi, and background uploaders (Item D5)."""
    platform = MagicMock()
    platform.get_default_gateway.return_value = "192.168.1.1"
    platform.get_primary_interface.return_value = "Wi-Fi"
    platform.get_interface_dns_servers.return_value = ["1.1.1.1"]
    platform.get_wifi_signal_strength.return_value = 85.0

    checker = MeetingPreflightChecker(platform)

    with patch("subprocess.run") as mock_ping:
        mock_ping.return_value.stdout = "Reply from 192.168.1.1: bytes=32 time=2ms TTL=64\n" * 10
        with patch("app.traffic.preflight.measure_dns_latency", return_value=25.0):
            with patch("psutil.process_iter", return_value=[]):
                report: PreflightReport = checker.run_check()
                assert report.is_ready is True
                assert "الشبكة جاهزة للاجتماع" in report.headline
                assert report.quality_tier == "1080p Full HD"
