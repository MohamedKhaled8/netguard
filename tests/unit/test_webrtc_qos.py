"""Unit tests for WebRTC QoS Prioritization and Cleanup."""

import pytest
import asyncio
from unittest.mock import MagicMock, patch
from collections import namedtuple

from app.traffic.controller import TrafficController
from app.traffic.applications import WorkloadCategory
from app.core.events import EventBus


@pytest.fixture
def mock_platform():
    platform = MagicMock()
    platform.is_elevated.return_value = True
    platform.get_qos_policies.return_value = []
    platform.create_qos_dscp_policy.return_value = (True, "Created")
    platform.create_qos_throttle_policy.return_value = (True, "Created")
    platform.remove_qos_policy.return_value = (True, "Removed")
    return platform


@pytest.mark.asyncio
async def test_webrtc_browser_udp_prioritization(mock_platform):
    event_bus = EventBus()
    controller = TrafficController(event_bus=event_bus, platform=mock_platform)

    Conn = namedtuple("Conn", ["pid", "status", "type", "raddr"])
    Addr = namedtuple("Addr", ["ip", "port"])

    import socket
    # Chrome with a WebRTC UDP connection on port 19302
    fake_connections = [
        Conn(pid=5001, status="NONE", type=socket.SOCK_DGRAM, raddr=Addr(ip="142.250.180.14", port=19302)),
    ]

    with patch("psutil.net_connections", return_value=fake_connections):
        with patch.object(controller, "_resolve_process_name", return_value="chrome.exe"):
            with patch.object(controller.meeting_detector, "check_windows_consent_store", return_value=["microphone:chrome.exe"]):
                controller.meeting_detector.set_simulated_signal("chrome.exe", has_consent=True, has_sustained_udp=True)
                profiles = await controller.scan_active_applications()

    # Verify that chrome.exe was categorized as CONFERENCING
    chrome_profile = next((p for p in profiles if p.name == "chrome.exe"), None)
    assert chrome_profile is not None
    assert chrome_profile.category == WorkloadCategory.CONFERENCING
    assert chrome_profile.priority_level == 1


@pytest.mark.asyncio
async def test_native_zoom_no_protocol_filter(mock_platform):
    event_bus = EventBus()
    controller = TrafficController(event_bus=event_bus, platform=mock_platform)

    Conn = namedtuple("Conn", ["pid", "status", "type", "raddr"])
    Addr = namedtuple("Addr", ["ip", "port"])

    import socket
    fake_connections = [
        Conn(pid=6001, status="ESTABLISHED", type=socket.SOCK_STREAM, raddr=Addr(ip="170.114.10.2", port=443)),
    ]

    # Without ConsentStore mic/cam in use: zoom.exe is merely background/idle
    with patch("psutil.net_connections", return_value=fake_connections):
        with patch.object(controller, "_resolve_process_name", return_value="zoom.exe"):
            with patch.object(controller.meeting_detector, "check_windows_consent_store", return_value=[]):
                controller.meeting_detector.set_simulated_signal("zoom.exe", has_consent=False, has_sustained_udp=False)
                profiles_idle = await controller.scan_active_applications()

    zoom_idle = next((p for p in profiles_idle if p.name == "zoom.exe"), None)
    assert zoom_idle is not None
    assert zoom_idle.category == WorkloadCategory.BACKGROUND

    # With ConsentStore mic in use and UDP media: zoom.exe is confirmed in active call (CONFERENCING)
    fake_active_connections = [
        Conn(pid=99991, status="ESTABLISHED", type=socket.SOCK_STREAM, raddr=Addr(ip="170.114.10.2", port=443)),
        Conn(pid=99991, status="NONE", type=socket.SOCK_DGRAM, raddr=Addr(ip="170.114.10.2", port=8801)),
    ]
    with patch("psutil.net_connections", return_value=fake_active_connections):
        with patch.object(controller, "_resolve_process_name", return_value="zoom.exe"):
            with patch.object(controller.meeting_detector, "check_windows_consent_store", return_value=["microphone:zoom.exe"]):
                controller.meeting_detector.set_simulated_signal("zoom.exe", has_consent=True, has_sustained_udp=True)
                profiles_active = await controller.scan_active_applications()

    zoom_active = next((p for p in profiles_active if p.name == "zoom.exe"), None)
    assert zoom_active is not None
    assert zoom_active.category == WorkloadCategory.CONFERENCING


def test_cleanup_all_policies(mock_platform):
    event_bus = EventBus()
    controller = TrafficController(event_bus=event_bus, platform=mock_platform)
    controller._applied_policy_names.add("NetGuard_Zoom_Media_8801_8810")
    controller._applied_policy_names.add("NetGuard_Meet_Media_chrome.exe_19302")
    controller._applied_policy_names.add("NetGuard_Throttle_onedrive.exe")
    controller._applied_dscp_policies.add("zoom.exe")
    controller._applied_dscp_policies.add("chrome.exe")
    controller._applied_throttle_policies.add("onedrive.exe")

    controller.cleanup_all_policies()

    assert len(controller._applied_dscp_policies) == 0
    assert len(controller._applied_throttle_policies) == 0
    assert len(controller._applied_policy_names) == 0
    assert mock_platform.sweep_all_netguard_rules.call_count >= 1 or mock_platform.remove_qos_policy.call_count >= 1
