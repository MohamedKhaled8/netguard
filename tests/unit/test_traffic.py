"""Unit tests for NetGuard AI Stage 7 Application-Aware Traffic Intelligence."""

import pytest
from app.traffic.applications import ApplicationCatalog, WorkloadCategory
from app.traffic.controller import TrafficController
from app.core.events.bus import EventBus


def test_application_catalog_classification():
    # Zoom / Teams should be classified as CONFERENCING with Priority 1
    cat, pri, is_sys = ApplicationCatalog.classify("zoom.exe")
    assert cat == WorkloadCategory.CONFERENCING
    assert pri == 1
    assert is_sys is False

    cat_t, pri_t, _ = ApplicationCatalog.classify("teams.exe")
    assert cat_t == WorkloadCategory.CONFERENCING

    # Valorant should be GAMING
    cat_g, pri_g, _ = ApplicationCatalog.classify("valorant.exe")
    assert cat_g == WorkloadCategory.GAMING
    assert pri_g == 1

    # qBittorrent should be DOWNLOAD Priority 5
    cat_d, pri_d, _ = ApplicationCatalog.classify("qbittorrent.exe")
    assert cat_d == WorkloadCategory.DOWNLOAD
    assert pri_d == 5

    # System process must be protected
    cat_s, pri_s, is_sys = ApplicationCatalog.classify("svchost.exe")
    assert cat_s == WorkloadCategory.SYSTEM
    assert is_sys is True


@pytest.mark.asyncio
async def test_traffic_controller_scan():
    bus = EventBus()
    controller = TrafficController(event_bus=bus)
    profiles = await controller.scan_active_applications()
    # On a live computer, profiles may be empty or contain processes
    assert isinstance(profiles, list)


def test_platform_qos_policy_contracts():
    from app.platform.windows.adapter import WindowsPlatformAdapter
    adapter = WindowsPlatformAdapter()
    
    # get_qos_policies must return a list without raising
    policies = adapter.get_qos_policies()
    assert isinstance(policies, list)

    # When not elevated, creating policy must return False and explicit explanation
    if not adapter.is_elevated():
        ok, msg = adapter.create_qos_dscp_policy("Test_DSCP", "zoom.exe", 46)
        assert ok is False
        assert "مسؤول" in msg or "Administrator" in msg

        ok_th, msg_th = adapter.create_qos_throttle_policy("Test_Throttle", "onedrive.exe", 5_000_000)
        assert ok_th is False
        assert "مسؤول" in msg or "Administrator" in msg

        ok_rm, msg_rm = adapter.remove_qos_policy("Test_NonExistent")
        assert ok_rm is False
        assert "مسؤول" in msg or "Administrator" in msg
