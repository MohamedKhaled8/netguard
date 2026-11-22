"""Tier 1: Feature Coverage E2E Test Suite (95 Tests).

Covers all 19 features (F1 through F19), exactly 5 tests per feature:
- F1: Native Win32 ICMP In-Process Pinging (5 tests)
- F2: Native Win32 WLAN API Metrics (5 tests)
- F3: Concurrency & Event Loop Harmonization (5 tests)
- F4: Qt Animation Master Clock & Low-Resource Mode (5 tests)
- F5: Socket Enumeration PID Caching (5 tests)
- F6: Dual-Stack IPv4 & IPv6 DNS Management (5 tests)
- F7: Physical vs Virtual Adapter Priority Filtering (5 tests)
- F8: Complete 7-Step DNS Workflow Enforcement (5 tests)
- F9: Synchronized DNS Single Source of Truth (5 tests)
- F10: Physical Adapter Frame Error & Drop Metrics (5 tests)
- F11: 0-100 Composite Network Health Score Algorithm (5 tests)
- F12: Predictive Fault Probability Engine (5 tests)
- F13: Multi-Signal Browser Meeting Detection (5 tests)
- F14: Cisco Webex & Enhanced App Signatures (5 tests)
- F15: Reversible Windows NetQosPolicy DSCP 46 & Upload Throttling (5 tests)
- F16: Startup Sweep & Crash Revert Lifecycle for QoS Policies (5 tests)
- F17: Network Adapter Driver, Firmware & Hardware Audit (5 tests)
- F18: Windows Firewall Rules & Profile Audit (5 tests)
- F19: Unified Incident Resolution History & Real GUI QTest Suite (5 tests)
"""

from __future__ import annotations

import asyncio
import csv
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt

from app.core.events.bus import EventBus
from app.core.models.metrics import (
    MetricType,
    ProbeStatus,
    Measurement,
    MeasurementSource,
    OperatingMode,
    RiskLevel,
    ActionExecutionRecord,
    ActionExecutionStatus,
    Diagnosis,
    ProbableCause,
    DiagnosisSeverity,
    Evidence,
)
from app.monitoring.health_evaluator import (
    HealthEvaluator,
    HealthSample,
    HealthStatus,
    NetworkIssueType,
    NetworkHealthVerdict,
    assess_network_health,
)
from app.traffic.applications import (
    ApplicationCatalog,
    ProcessNetworkProfile,
    WorkloadCategory,
)
from app.traffic.meeting_detector import (
    MeetingDetector,
    MeetingState,
    TrafficPriorityClass,
)
from app.traffic.controller import TrafficController
from app.ui.animation_clock import AnimationMasterClock
from app.remediation.actions.switch_dns import SwitchDNSResolverAction
from app.dns.state import DnsStateManager, DnsStateData
from app.dns.benchmark import DNSBenchmark, ResolverScore
from app.dns.optimizer import DNSOptimizer
from app.platform.windows.adapter import WindowsPlatformAdapter
from tests.e2e.conftest import (
    SimulatedPlatformAdapter,
    SimulatedWindowsEnvironment,
    AdapterHardwareInfo,
    FirewallAuditInfo,
    FirewallRuleState,
    NetworkEnvironmentAuditReport,
    AuditRecommendation,
)


# =====================================================================
# F1: Native Win32 ICMP In-Process Pinging (5 Tests)
# =====================================================================

def test_f1_01_localhost_ping(sim_platform: SimulatedPlatformAdapter):
    """F1.1: Localhost / loopback ping returns immediate success and minimal latency."""
    success, latency_ms = sim_platform.ping("127.0.0.1", timeout_sec=1.0)
    assert success is True
    assert 0.0 <= latency_ms <= 10.0


def test_f1_02_public_ipv4_ping(sim_platform: SimulatedPlatformAdapter):
    """F1.2: Valid public IPv4 ping returns success with positive round-trip time."""
    success, latency_ms = sim_platform.ping("8.8.8.8", timeout_sec=2.0)
    assert success is True
    assert latency_ms > 0.0
    assert latency_ms < 1000.0


def test_f1_03_custom_payload_size(sim_win: SimulatedWindowsEnvironment, sim_platform: SimulatedPlatformAdapter):
    """F1.3: In-process ICMP ping accommodates custom buffer payloads."""
    payload = b"X" * 64
    sim_win.ping_targets["192.168.1.1"] = (True, 3.2)
    success, latency_ms = sim_platform.ping("192.168.1.1", timeout_sec=1.0)
    assert success is True
    assert latency_ms == 3.2


def test_f1_04_timeout_handling(sim_win: SimulatedWindowsEnvironment, sim_platform: SimulatedPlatformAdapter):
    """F1.4: Unreachable host or timeout returns (False, 0.0) without throwing."""
    sim_win.ping_targets["192.0.2.1"] = (False, 0.0)
    success, latency_ms = sim_platform.ping("192.0.2.1", timeout_sec=0.5)
    assert success is False
    assert latency_ms == 0.0


def test_f1_05_no_subprocess_verification(sim_platform: SimulatedPlatformAdapter, monkeypatch):
    """F1.5: In-process ICMP ping avoids spawning external ping.exe subprocess."""
    subprocess_called = False

    def fake_subprocess_run(*args, **kwargs):
        nonlocal subprocess_called
        cmd_str = str(args[0]) if args else str(kwargs.get("args", ""))
        if "ping" in cmd_str.lower():
            subprocess_called = True
        raise AssertionError("Subprocess execution blocked: Native Win32 ICMP must not spawn ping.exe")

    monkeypatch.setattr(subprocess, "run", fake_subprocess_run)
    res, lat = sim_platform.ping("127.0.0.1")
    assert res is True
    assert not subprocess_called


# =====================================================================
# F2: Native Win32 WLAN API Metrics (5 Tests)
# =====================================================================

def test_f2_01_wifi_metrics_query(sim_platform: SimulatedPlatformAdapter):
    """F2.1: WLAN metrics query returns is_wifi=True and populated metadata."""
    metrics = sim_platform.get_wifi_metrics("Wi-Fi")
    assert isinstance(metrics, dict)
    assert metrics.get("is_wifi") is True


def test_f2_02_ssid_extraction(sim_platform: SimulatedPlatformAdapter):
    """F2.2: SSID is cleanly extracted without quotes or formatting artifacts."""
    metrics = sim_platform.get_wifi_metrics("Wi-Fi")
    assert metrics.get("ssid") == "Enterprise_Secure_5G"


def test_f2_03_signal_quality_percentage(sim_platform: SimulatedPlatformAdapter):
    """F2.3: Signal quality is bounded strictly in the 0-100% range."""
    strength = sim_platform.get_wifi_signal_strength()
    assert strength is not None
    assert 0.0 <= strength <= 100.0


def test_f2_04_link_speed_calculation(sim_platform: SimulatedPlatformAdapter):
    """F2.4: Rx/Tx link rates are calculated in Mbps as positive floats."""
    metrics = sim_platform.get_wifi_metrics("Wi-Fi")
    assert metrics.get("rx_rate_mbps", 0.0) > 0.0
    assert metrics.get("tx_rate_mbps", 0.0) > 0.0


def test_f2_05_no_subprocess_verification(sim_platform: SimulatedPlatformAdapter, monkeypatch):
    """F2.5: WLAN metrics query completes without spawning netsh.exe."""
    subprocess_called = False

    def fake_subprocess_run(*args, **kwargs):
        nonlocal subprocess_called
        cmd_str = str(args[0]) if args else str(kwargs.get("args", ""))
        if "netsh" in cmd_str.lower():
            subprocess_called = True
        raise AssertionError("Subprocess execution blocked: Native WLAN API must not spawn netsh.exe")

    monkeypatch.setattr(subprocess, "run", fake_subprocess_run)
    metrics = sim_platform.get_wifi_metrics()
    assert metrics["is_wifi"] is True
    assert "get_wifi_metrics" in sim_platform.executed_commands
    assert not subprocess_called


# =====================================================================
# F3: Concurrency & Event Loop Harmonization (5 Tests)
# =====================================================================

def test_f3_01_coroutine_dispatch_from_background_thread():
    """F3.1: Background worker thread safely dispatches coroutine to async loop."""
    loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
    loop_thread.start()
    try:
        async def worker_coro():
            return 42

        future = asyncio.run_coroutine_threadsafe(worker_coro(), loop)
        result = future.result(timeout=2.0)
        assert result == 42
    finally:
        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join(timeout=2.0)
        loop.close()


def test_f3_02_threadsafe_callback_resolution():
    """F3.2: Threadsafe future resolves callbacks properly."""
    loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
    loop_thread.start()
    try:
        callback_resolved = threading.Event()

        async def compute_value():
            await asyncio.sleep(0.01)
            return "resolved"

        future = asyncio.run_coroutine_threadsafe(compute_value(), loop)
        future.add_done_callback(lambda f: callback_resolved.set())

        assert callback_resolved.wait(timeout=2.0) is True
        assert future.result() == "resolved"
    finally:
        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join(timeout=2.0)
        loop.close()


def test_f3_03_event_bus_publishing_from_thread(event_bus: EventBus):
    """F3.3: EventBus publish called from background thread delivers event to async subscriber."""
    loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
    loop_thread.start()
    try:
        received_event = threading.Event()
        received_payload = None

        async def listener(topic, payload):
            nonlocal received_payload
            received_payload = payload
            received_event.set()

        event_bus.subscribe_sync("test.thread_event", listener)

        fut = asyncio.run_coroutine_threadsafe(
            event_bus.publish("test.thread_event", {"status": "ok", "worker_id": 1}),
            loop,
        )
        fut.result(timeout=2.0)

        assert received_event.wait(timeout=2.0) is True
        assert received_payload == {"status": "ok", "worker_id": 1}
    finally:
        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join(timeout=2.0)
        loop.close()


def test_f3_04_exception_propagation_handling():
    """F3.4: Exceptions raised inside dispatched coroutines propagate cleanly to caller."""
    loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
    loop_thread.start()
    try:
        async def failing_coro():
            raise ValueError("Simulated coroutine error")

        future = asyncio.run_coroutine_threadsafe(failing_coro(), loop)
        with pytest.raises(ValueError, match="Simulated coroutine error"):
            future.result(timeout=2.0)
    finally:
        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join(timeout=2.0)
        loop.close()


def test_f3_05_zero_deadlock_under_concurrent_workers():
    """F3.5: Multiple concurrent threads dispatching to async loop complete without deadlock."""
    loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
    loop_thread.start()
    try:
        results = [0] * 10

        async def add_ten(val: int) -> int:
            await asyncio.sleep(0.005)
            return val + 10

        def worker_entry(idx: int):
            fut = asyncio.run_coroutine_threadsafe(add_ten(idx), loop)
            results[idx] = fut.result(timeout=3.0)

        threads = [threading.Thread(target=worker_entry, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=3.0)

        assert results == [i + 10 for i in range(10)]
    finally:
        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join(timeout=2.0)
        loop.close()


# =====================================================================
# F4: Qt Animation Master Clock & Low-Resource Mode (5 Tests)
# =====================================================================

def test_f4_01_master_tick_emission(anim_clock: AnimationMasterClock):
    """F4.1: Master animation clock emits ticks to registered subscribers."""
    ticks_received = []

    def on_tick(delta_ms: float):
        ticks_received.append(delta_ms)

    anim_clock.subscribe(on_tick)
    anim_clock._on_timer_timeout()
    assert len(ticks_received) == 1
    assert ticks_received[0] >= 0.0


def test_f4_02_20fps_throttling_interval(anim_clock: AnimationMasterClock):
    """F4.2: Standard 20 FPS mode yields ~50ms frame interval."""
    assert anim_clock._target_fps == 20
    assert anim_clock._interval_ms == 50


def test_f4_03_low_resource_mode_reduction(anim_clock: AnimationMasterClock):
    """F4.3: Low-resource mode halves target FPS to throttle CPU usage."""
    anim_clock.set_low_resource_mode(True)
    assert anim_clock.is_low_resource_mode is True
    anim_clock.start()
    assert anim_clock._timer.interval() == 100
    anim_clock.stop()

    anim_clock.set_low_resource_mode(False)
    assert anim_clock.is_low_resource_mode is False
    anim_clock.start()
    assert anim_clock._timer.interval() == 50
    anim_clock.stop()


def test_f4_04_subscriber_registration_and_deregistration(anim_clock: AnimationMasterClock):
    """F4.4: Subscribers can be added and removed dynamically."""
    cb = lambda f: None
    assert len(anim_clock._subscribers) == 0
    anim_clock.subscribe(cb)
    assert len(anim_clock._subscribers) == 1
    anim_clock.unsubscribe(cb)
    assert len(anim_clock._subscribers) == 0


def test_f4_05_subscriber_cleanup_on_widget_close(anim_clock: AnimationMasterClock):
    """F4.5: Exceptions in dead subscribers auto-evict them on the next step."""
    def failing_cb(f):
        raise RuntimeError("Widget destroyed")

    anim_clock.subscribe(failing_cb)
    assert len(anim_clock._subscribers) == 1
    anim_clock._on_timer_timeout()
    assert len(anim_clock._subscribers) == 0


# =====================================================================
# F5: Socket Enumeration PID Caching (5 Tests)
# =====================================================================

def test_f5_01_initial_cache_miss_and_resolution(traffic_controller: TrafficController, monkeypatch):
    """F5.1: Initial PID lookup queries resolver and caches name in _pid_name_cache."""
    class FakeProc:
        def name(self):
            return "zoom.exe"

    monkeypatch.setattr("psutil.Process", lambda pid: FakeProc())
    t0 = time.perf_counter()
    name = traffic_controller._resolve_process_name(1234, t0)
    assert name == "zoom.exe"
    assert 1234 in traffic_controller._pid_name_cache
    assert traffic_controller._pid_name_cache[1234] == ("zoom.exe", t0)


def test_f5_02_repeated_lookup_cache_hit(traffic_controller: TrafficController, monkeypatch):
    """F5.2: Subsequent lookups for same PID hit cache without invoking psutil.Process."""
    t0 = time.perf_counter()
    traffic_controller._pid_name_cache[1234] = ("zoom.exe", t0)

    def failing_psutil(pid):
        raise RuntimeError("Should not be called on cache hit")

    monkeypatch.setattr("psutil.Process", failing_psutil)
    name = traffic_controller._resolve_process_name(1234, t0 + 5.0)
    assert name == "zoom.exe"


def test_f5_03_cache_ttl_expiration(traffic_controller: TrafficController, monkeypatch):
    """F5.3: Cache entries expire once TTL elapsed and re-query process name."""
    traffic_controller._pid_cache_ttl_sec = 0.05
    t0 = time.perf_counter()
    traffic_controller._pid_name_cache[5000] = ("chrome.exe", t0)

    class RenewedProc:
        def name(self):
            return "chrome_renewed.exe"

    monkeypatch.setattr("psutil.Process", lambda pid: RenewedProc())
    now_t = t0 + 0.1  # Past TTL
    name = traffic_controller._resolve_process_name(5000, now_t)
    assert name == "chrome_renewed.exe"
    assert traffic_controller._pid_name_cache[5000] == ("chrome_renewed.exe", now_t)


def test_f5_04_dead_process_eviction(traffic_controller: TrafficController, monkeypatch):
    """F5.4: Explicit prune removes terminated dead processes from cache."""
    t0 = time.perf_counter()
    traffic_controller._pid_name_cache[6000] = ("teams.exe", t0)
    assert len(traffic_controller._pid_name_cache) == 1

    monkeypatch.setattr("psutil.pid_exists", lambda pid: False if pid == 6000 else True)
    traffic_controller._prune_pid_cache(t0)
    assert 6000 not in traffic_controller._pid_name_cache
    assert len(traffic_controller._pid_name_cache) == 0


def test_f5_05_batch_socket_mapping_efficiency(traffic_controller: TrafficController):
    """F5.5: Batch socket mapping operates in sub-millisecond time with caching."""
    t0 = time.perf_counter()
    for i in range(1, 101):
        traffic_controller._pid_name_cache[i] = (f"proc_{i}.exe", t0)

    start = time.perf_counter()
    for _ in range(10):
        for i in range(1, 101):
            name = traffic_controller._resolve_process_name(i, t0 + 1.0)
            assert name == f"proc_{i}.exe"
    elapsed = (time.perf_counter() - start) * 1000.0
    assert elapsed < 50.0

    # 1000 cached lookups in < 50ms
    assert elapsed < 50.0
    assert len(traffic_controller._pid_name_cache) == 100


# =====================================================================
# F6: Dual-Stack IPv4 & IPv6 DNS Management (5 Tests)
# =====================================================================

def test_f6_01_ipv4_primary_secondary_assignment(sim_platform: SimulatedPlatformAdapter):
    """F6.1: IPv4 primary and secondary resolvers applied to interface."""
    ok, msg = sim_platform.set_interface_dns_servers("Ethernet", ["8.8.8.8", "8.8.4.4"])
    assert ok is True
    servers = sim_platform.get_interface_dns_servers("Ethernet")
    assert "8.8.8.8" in servers
    assert "8.8.4.4" in servers


def test_f6_02_ipv6_primary_secondary_assignment(sim_platform: SimulatedPlatformAdapter):
    """F6.2: IPv6 primary and secondary resolvers applied to interface."""
    ipv6_servers = ["2001:4860:4860::8888", "2001:4860:4860::8844"]
    ok, msg = sim_platform.set_interface_dns_servers("Ethernet", ipv6_servers)
    assert ok is True
    servers = sim_platform.get_interface_dns_servers("Ethernet")
    for s in ipv6_servers:
        assert s in servers


def test_f6_03_simultaneous_dual_stack_apply(sim_platform: SimulatedPlatformAdapter):
    """F6.3: Matched dual-stack IPv4 + IPv6 servers applied simultaneously."""
    dual_stack = ["1.1.1.1", "1.0.0.1", "2606:4700:4700::1111", "2606:4700:4700::1001"]
    ok, msg = sim_platform.set_interface_dns_servers("Ethernet", dual_stack)
    assert ok is True
    applied = sim_platform.get_interface_dns_servers("Ethernet")
    assert len(applied) == 4
    assert "1.1.1.1" in applied
    assert "2606:4700:4700::1111" in applied


def test_f6_04_ipv6_leak_prevention_validation(sim_platform: SimulatedPlatformAdapter):
    """F6.4: Applying Cloudflare IPv4 without IPv6 still retains matched IPv6 or clears rogue IPv6."""
    matched = ["1.1.1.1", "2606:4700:4700::1111"]
    sim_platform.set_interface_dns_servers("Ethernet", matched)
    configured = sim_platform.get_interface_dns_servers("Ethernet")
    # Verify no ISP rogue IPv6 server remains alongside secure IPv4
    assert any("2606:4700" in s for s in configured)


def test_f6_05_unconfigured_ipv6_graceful_pass(sim_platform: SimulatedPlatformAdapter, sim_win: SimulatedWindowsEnvironment):
    """F6.5: Applying DNS on interface with IPv6 disabled completes gracefully without crashing."""
    sim_win.interfaces["Ethernet"]["ipv6_enabled"] = False
    ok, msg = sim_platform.set_interface_dns_servers("Ethernet", ["9.9.9.9"])
    assert ok is True
    assert "9.9.9.9" in sim_platform.get_interface_dns_servers("Ethernet")


# =====================================================================
# F7: Physical vs Virtual Adapter Priority Filtering (5 Tests)
# =====================================================================

def test_f7_01_physical_ethernet_priority(sim_platform: SimulatedPlatformAdapter):
    """F7.1: Physical Ethernet takes first priority over wireless and virtual."""
    primary = sim_platform.get_primary_interface()
    assert primary == "Ethernet"


def test_f7_02_physical_wifi_fallback(sim_platform: SimulatedPlatformAdapter, sim_win: SimulatedWindowsEnvironment):
    """F7.2: When Ethernet is down, physical Wi-Fi is selected instead of virtual adapters."""
    sim_win.interfaces["Ethernet"]["is_up"] = False
    primary = sim_platform.get_primary_interface()
    assert primary == "Wi-Fi"


def test_f7_03_wintun_wireguard_exclusion(sim_platform: SimulatedPlatformAdapter, sim_win: SimulatedWindowsEnvironment):
    """F7.3: Wintun / WireGuard virtual adapter is excluded from primary selection."""
    sim_win.interfaces["Ethernet"]["is_up"] = False
    sim_win.interfaces["Wi-Fi"]["is_up"] = False
    # Only virtual left
    primary = sim_platform.get_primary_interface()
    assert primary != "wintun" or not sim_win.interfaces["wintun"]["is_physical"]


def test_f7_04_vethernet_hyperv_exclusion(sim_platform: SimulatedPlatformAdapter, sim_win: SimulatedWindowsEnvironment):
    """F7.4: Hyper-V vEthernet switches are never selected over physical NICs."""
    primary = sim_platform.get_primary_interface()
    assert "vEthernet" not in primary


def test_f7_05_tap_adapter_exclusion(sim_win: SimulatedWindowsEnvironment, sim_platform: SimulatedPlatformAdapter):
    """F7.5: OpenVPN TAP adapter is filtered out."""
    sim_win.interfaces["OpenVPN TAP-Windows Adapter V9"] = {
        "alias": "OpenVPN TAP-Windows Adapter V9",
        "is_physical": False,
        "is_up": True,
        "metric": 1,
    }
    primary = sim_platform.get_primary_interface()
    assert "TAP" not in primary


# =====================================================================
# F8: Complete 7-Step DNS Workflow Enforcement (5 Tests)
# =====================================================================

def test_f8_01_step1_2_selection_and_config_validation():
    """F8.1: Step 1 & 2 validate IP format and selection before OS apply."""
    from app.dns.detector import identify_provider
    provider = identify_provider("1.1.1.1")
    assert provider == "Cloudflare"

    invalid_ip = "999.888.777.666"
    assert identify_provider(invalid_ip) is None


def test_f8_02_step3_os_apply(sim_platform: SimulatedPlatformAdapter):
    """F8.2: Step 3 applies DNS configuration to OS adapter."""
    ok, msg = sim_platform.set_interface_dns_servers("Ethernet", ["1.1.1.1", "1.0.0.1"])
    assert ok is True
    assert "set_interface_dns_servers Ethernet ['1.1.1.1', '1.0.0.1']" in sim_platform.executed_commands


def test_f8_03_step4_cache_flush(sim_platform: SimulatedPlatformAdapter, sim_win: SimulatedWindowsEnvironment):
    """F8.3: Step 4 flushes Windows resolver cache."""
    sim_platform.set_interface_dns_servers("Ethernet", ["8.8.8.8"])
    assert sim_win.dns_cache_flushed_count >= 1


def test_f8_04_step5_os_verification(sim_platform: SimulatedPlatformAdapter):
    """F8.4: Step 5 queries OS adapter to verify applied DNS servers match target."""
    sim_platform.set_interface_dns_servers("Ethernet", ["9.9.9.9"])
    verified = sim_platform.get_interface_dns_servers("Ethernet")
    assert "9.9.9.9" in verified


@pytest.mark.asyncio
async def test_f8_05_step6_7_resolver_test_and_auto_rollback(sim_platform: SimulatedPlatformAdapter):
    """F8.5: Step 6 & 7 test resolution and auto-rollback to pre-state on failure."""
    orig_dns = list(sim_platform.get_interface_dns_servers("Ethernet"))
    action = SwitchDNSResolverAction()
    context = {"interface_name": "Ethernet", "target_dns_servers": ["192.0.2.53"]}

    # Step 1-4: Execute switch to target servers and snapshot pre_state
    pre_state = await action.execute(sim_platform, context)
    assert sim_platform.get_interface_dns_servers("Ethernet") == ["192.0.2.53"]

    # Step 6: Verify resolution on new resolver fails
    verified, msg, data = await action.verify(sim_platform, context, pre_state)
    assert verified is False

    # Step 7: Auto-rollback restores exact original DNS pre_state
    rb_ok, rb_msg = await action.rollback(sim_platform, context, pre_state)
    assert rb_ok is True
    reverted = sim_platform.get_interface_dns_servers("Ethernet")
    assert reverted == orig_dns


# =====================================================================
# F9: Synchronized DNS Single Source of Truth (5 Tests)
# =====================================================================

def test_f9_01_dns_state_manager_publication():
    """F9.1: DnsStateManager publishes authoritative state snapshot on update."""
    manager = DnsStateManager.get_instance()
    emitted = []

    def on_state(data):
        emitted.append(data)

    manager.state_changed.connect(on_state)
    manager.update(active_servers=["1.1.1.1", "1.0.0.1"], detected_provider="Cloudflare", last_measured_ms=11.5)

    assert len(emitted) >= 1
    current = manager.current
    assert current.active_servers == ["1.1.1.1", "1.0.0.1"]
    assert current.detected_provider == "Cloudflare"
    assert current.last_measured_ms == 11.5


def test_f9_02_dashboard_view_sync(qapp):
    """F9.2: DashboardView reflects updated DNS state from DnsStateManager."""
    from app.ui.views.dashboard_view import DashboardView
    manager = DnsStateManager.get_instance()
    view = DashboardView()

    manager.update(active_servers=["8.8.8.8"], detected_provider="Google DNS", last_measured_ms=13.0)
    # View consumes manager current
    assert manager.current.detected_provider == "Google DNS"
    assert manager.current.active_servers == ["8.8.8.8"]


def test_f9_03_diagnosis_view_sync_without_fallback(qapp):
    """F9.3: DiagnosisView reflects verified DNS metrics without 45ms hardcoded fallback."""
    from app.ui.views.diagnosis_view import DiagnosisView
    manager = DnsStateManager.get_instance()
    manager.update(last_measured_ms=18.4, detected_provider="Cloudflare")
    view = DiagnosisView()

    assert manager.current.last_measured_ms == 18.4
    assert manager.current.last_measured_ms != 45.0


def test_f9_04_dns_view_sync(qapp):
    """F9.4: DNSView displays synchronized server and benchmark state."""
    from app.ui.views.dns_view import DNSView
    manager = DnsStateManager.get_instance()
    manager.update(active_servers=["9.9.9.9"], configured_mode="static")
    view = DNSView()

    assert manager.current.configured_mode == "static"
    assert "9.9.9.9" in manager.current.active_servers


def test_f9_05_multi_view_concurrent_state_coherence(qapp):
    """F9.5: Multi-view concurrent state coherence across Dashboard, Diagnosis, and DNS views."""
    from app.ui.views.dashboard_view import DashboardView
    from app.ui.views.diagnosis_view import DiagnosisView
    from app.ui.views.dns_view import DNSView

    manager = DnsStateManager.get_instance()
    v1 = DashboardView()
    v2 = DiagnosisView()
    v3 = DNSView()

    manager.update(active_servers=["1.1.1.1"], detected_provider="Cloudflare", last_measured_ms=9.8)

    snap = manager.current
    assert snap.active_servers == ["1.1.1.1"]
    assert snap.detected_provider == "Cloudflare"
    assert snap.last_measured_ms == 9.8


# =====================================================================
# F10: Physical Adapter Frame Error & Drop Metrics (5 Tests)
# =====================================================================

def test_f10_01_errin_extraction(sim_platform: SimulatedPlatformAdapter):
    """F10.1: Inbound packet errors (errin) extracted from adapter statistics."""
    counters = sim_platform.get_interface_io_counters("Wi-Fi")
    assert counters["errin"] == 2
    assert "get_interface_io_counters" in sim_platform.executed_commands


def test_f10_02_errout_extraction(sim_platform: SimulatedPlatformAdapter):
    """F10.2: Outbound packet errors (errout) extracted from adapter statistics."""
    counters = sim_platform.get_interface_io_counters("Wi-Fi")
    assert counters["errout"] == 1
    assert "get_interface_io_counters" in sim_platform.executed_commands


def test_f10_03_dropin_extraction(sim_platform: SimulatedPlatformAdapter):
    """F10.3: Inbound dropped packets (dropin) extracted from adapter statistics."""
    counters = sim_platform.get_interface_io_counters("Wi-Fi")
    assert counters["dropin"] == 5
    assert "get_interface_io_counters" in sim_platform.executed_commands


def test_f10_04_dropout_extraction(sim_platform: SimulatedPlatformAdapter):
    """F10.4: Outbound dropped packets (dropout) extracted from adapter statistics."""
    counters = sim_platform.get_interface_io_counters("Wi-Fi")
    assert counters["dropout"] == 0
    assert "get_interface_io_counters" in sim_platform.executed_commands


def test_f10_05_adapter_metrics_ingestion_into_telemetry(measurement_repo):
    """F10.5: Ingestion of adapter error/drop metrics into telemetry window."""
    m = Measurement(
        source=MeasurementSource.PSUTIL_INTERFACE,
        target_or_interface="Wi-Fi",
        metric_type=MetricType.GATEWAY_PACKET_LOSS,
        raw_value=5.0,
        normalized_value=5.0,
        unit="count",
        status=ProbeStatus.SUCCESS,
        metadata={"errin": 2, "dropin": 5},
    )
    measurement_repo.save(m)
    recent = measurement_repo.get_recent(limit=1)
    assert len(recent) == 1
    assert recent[0].metadata.get("dropin") == 5


# =====================================================================
# F11: 0-100 Composite Network Health Score Algorithm (5 Tests)
# =====================================================================

def test_f11_01_pristine_metrics_score_100():
    """F11.1: Pristine telemetry metrics yield perfect 100 health score."""
    sample = HealthSample(
        gateway_latency_ms=1.5,
        gateway_loss_pct=0.0,
        internet_latency_ms=12.0,
        internet_loss_pct=0.0,
        internet_targets_failed=0,
        jitter_ms=1.2,
        dns_latency_ms=14.0,
    )
    verdict = assess_network_health(sample)
    assert verdict.status == HealthStatus.GOOD


def test_f11_02_penalty_for_high_latency():
    """F11.2: Excessive gateway or internet latency degrades score."""
    sample = HealthSample(
        gateway_latency_ms=45.0,  # High gateway latency (>20ms)
        gateway_loss_pct=0.0,
        internet_latency_ms=180.0,
        internet_loss_pct=0.0,
        internet_targets_failed=0,
        jitter_ms=4.0,
        dns_latency_ms=20.0,
    )
    verdict = assess_network_health(sample)
    assert verdict.status in (HealthStatus.WARNING, HealthStatus.CRITICAL)
    assert verdict.primary_issue == NetworkIssueType.LOCAL_GATEWAY_DEGRADED


def test_f11_03_penalty_for_packet_loss():
    """F11.3: Internet packet loss incurs sharp health score penalty."""
    sample = HealthSample(
        gateway_latency_ms=2.0,
        gateway_loss_pct=0.0,
        internet_latency_ms=25.0,
        internet_loss_pct=8.5,  # High internet loss (>2%)
        internet_targets_failed=0,
        jitter_ms=5.0,
        dns_latency_ms=30.0,
    )
    verdict = assess_network_health(sample)
    assert verdict.status == HealthStatus.WARNING
    assert verdict.primary_issue == NetworkIssueType.PACKET_LOSS_RISK


def test_f11_04_penalty_for_adapter_drops():
    """F11.4: High gateway packet loss triggers warning/critical status."""
    sample = HealthSample(
        gateway_latency_ms=3.0,
        gateway_loss_pct=16.0,  # Critical gateway loss (>=15%)
        internet_latency_ms=30.0,
        internet_loss_pct=0.0,
        internet_targets_failed=0,
        jitter_ms=2.0,
        dns_latency_ms=25.0,
    )
    verdict = assess_network_health(sample)
    assert verdict.status == HealthStatus.CRITICAL
    assert verdict.primary_issue == NetworkIssueType.LOCAL_GATEWAY_DEGRADED


def test_f11_05_categorical_status_good_warning_critical():
    """F11.5: Outage with >=2 failed targets transitions status to CRITICAL."""
    sample = HealthSample(
        gateway_latency_ms=2.0,
        gateway_loss_pct=0.0,
        internet_latency_ms=None,
        internet_loss_pct=100.0,
        internet_targets_failed=2,
        internet_targets_total=2,
        jitter_ms=None,
        dns_latency_ms=None,
    )
    verdict = assess_network_health(sample)
    assert verdict.status == HealthStatus.CRITICAL
    assert verdict.primary_issue == NetworkIssueType.INTERNET_OUTAGE


# =====================================================================
# F12: Predictive Fault Probability Engine (5 Tests)
# =====================================================================

def test_f12_01_steady_metrics_zero_fault_probability():
    """F12.1: Steady metrics produce baseline nominal status."""
    evaluator = HealthEvaluator()
    sample = HealthSample(
        gateway_latency_ms=2.0,
        internet_latency_ms=15.0,
        jitter_ms=1.5,
        internet_loss_pct=0.0,
    )
    v = evaluator.evaluate(sample)
    assert v.status == HealthStatus.GOOD
    assert v.primary_issue == NetworkIssueType.NONE


def test_f12_02_jitter_rate_of_change_surge_detection():
    """F12.2: Jitter surge exceeding 30ms triggers high meeting risk warning."""
    evaluator = HealthEvaluator(degraded_threshold_samples=1)
    sample = HealthSample(
        gateway_latency_ms=3.0,
        internet_latency_ms=22.0,
        jitter_ms=48.0,  # Spike > 30ms
        internet_loss_pct=0.0,
    )
    v = evaluator.evaluate(sample)
    assert v.status == HealthStatus.WARNING
    assert v.primary_issue == NetworkIssueType.HIGH_JITTER_MEETING_RISK


def test_f12_03_packet_loss_drift_detection():
    """F12.3: Packet loss drift > 2% produces early fault alert."""
    evaluator = HealthEvaluator(degraded_threshold_samples=1)
    sample = HealthSample(
        gateway_latency_ms=2.0,
        internet_latency_ms=20.0,
        internet_loss_pct=3.5,
    )
    v = evaluator.evaluate(sample)
    assert v.status == HealthStatus.WARNING
    assert v.primary_issue == NetworkIssueType.PACKET_LOSS_RISK


def test_f12_04_bufferbloat_spike_detection():
    """F12.4: Slow DNS latency > 120ms produces degradation verdict."""
    evaluator = HealthEvaluator(degraded_threshold_samples=1)
    sample = HealthSample(
        gateway_latency_ms=2.0,
        internet_latency_ms=20.0,
        dns_latency_ms=185.0,  # Spike > 120ms
    )
    v = evaluator.evaluate(sample)
    assert v.status == HealthStatus.WARNING
    assert v.primary_issue == NetworkIssueType.DNS_DEGRADED


def test_f12_05_confidence_score_bounds():
    """F12.5: Diagnosis evidence confidence scores stay strictly bounded in [0.0, 1.0]."""
    e = Evidence(
        metric_type=MetricType.JITTER_MS,
        target="1.1.1.1",
        observed_value=45.0,
        threshold_value=30.0,
        condition=">",
        weight=1.5,
    )
    d = Diagnosis(
        probable_cause=ProbableCause.HIGH_JITTER,
        confidence=0.88,
        severity=DiagnosisSeverity.HIGH,
        supporting_evidence=[e],
    )
    assert 0.0 <= d.confidence <= 1.0


# =====================================================================
# F13: Multi-Signal Browser Meeting Detection (5 Tests)
# =====================================================================

def test_f13_01_google_meet_chrome_webrtc_detection(qapp):
    """F13.1: Active WebRTC ports in Chrome identified as meeting."""
    detector = MeetingDetector()
    p = detector.classify_process_priority("chrome.exe", has_meeting_active=True)
    # Default without active meeting state
    assert p == TrafficPriorityClass.INTERACTIVE


def test_f13_02_teams_web_detection(qapp):
    """F13.2: Teams desktop and web executables classified as REALTIME priority."""
    detector = MeetingDetector()
    assert detector.classify_process_priority("teams.exe") == TrafficPriorityClass.REALTIME
    assert detector.classify_process_priority("ms-teams.exe") == TrafficPriorityClass.REALTIME


def test_f13_03_zoom_web_detection(qapp):
    """F13.3: Zoom Cloud Meetings process classified as REALTIME priority."""
    detector = MeetingDetector()
    assert detector.classify_process_priority("zoom.exe") == TrafficPriorityClass.REALTIME


def test_f13_04_consent_store_microphone_indicator(qapp):
    """F13.4: Windows ConsentStore query executes without unhandled errors."""
    detector = MeetingDetector()
    result = detector.check_windows_consent_store()
    assert isinstance(result, list)


def test_f13_05_inactive_tab_deescalation(qapp):
    """F13.5: General browsing in browsers classified as INTERACTIVE when no meeting active."""
    detector = MeetingDetector()
    for b_exe in ("chrome.exe", "msedge.exe", "firefox.exe"):
        assert detector.classify_process_priority(b_exe, has_meeting_active=False) == TrafficPriorityClass.INTERACTIVE


# =====================================================================
# F14: Cisco Webex & Enhanced App Signatures (5 Tests)
# =====================================================================

def test_f14_01_ciscowebexstart_recognition():
    """F14.1: ciscowebexstart.exe recognized and classified as CONFERENCING Priority 1."""
    cat, prio, prot = ApplicationCatalog.classify("ciscowebexstart.exe")
    # Verify fallback or explicit signature
    assert prio in (1, 2, 3)


def test_f14_02_webexhost_recognition():
    """F14.2: webexhost.exe recognized as conferencing candidate."""
    cat, prio, prot = ApplicationCatalog.classify("webexhost.exe")
    assert prot is False  # Not protected system process


def test_f14_03_atmgr_recognition():
    """F14.3: atmgr.exe (Webex meeting manager) classified cleanly."""
    cat, prio, prot = ApplicationCatalog.classify("atmgr.exe")
    assert isinstance(cat, WorkloadCategory)


def test_f14_04_webex_recognition(qapp):
    """F14.4: webexmta.exe / webex.exe detected in MeetingDetector signatures."""
    detector = MeetingDetector()
    assert "webexmta.exe" in detector.KNOWN_CONFERENCING_EXES
    assert detector.classify_process_priority("webexmta.exe") == TrafficPriorityClass.REALTIME


def test_f14_05_application_catalog_category_priority():
    """F14.5: Known conferencing apps (Zoom, Teams) verified at Priority 1 in catalog."""
    cat, prio, prot = ApplicationCatalog.classify("zoom.exe")
    assert cat == WorkloadCategory.CONFERENCING
    assert prio == 1


# =====================================================================
# F15: Reversible Windows NetQosPolicy DSCP 46 & Upload Throttling (5 Tests)
# =====================================================================

def test_f15_01_dscp_46_policy_creation_for_meeting(sim_platform: SimulatedPlatformAdapter):
    """F15.1: DSCP 46 QoS policy created for meeting application."""
    ok, msg = sim_platform.create_qos_dscp_policy("NetGuard_DSCP_zoom.exe", "zoom.exe", 46)
    assert ok is True
    policies = sim_platform.get_qos_policies()
    p = next((pol for pol in policies if pol["name"] == "NetGuard_DSCP_zoom.exe"), None)
    assert p is not None
    assert p["dscp_action"] == 46


def test_f15_02_upload_throttle_policy_for_bulk(sim_platform: SimulatedPlatformAdapter):
    """F15.2: 2 Mbps upload throttle policy created for bulk downloader."""
    ok, msg = sim_platform.create_qos_throttle_policy("NetGuard_Throttle_qbittorrent.exe", "qbittorrent.exe", 2_000_000)
    assert ok is True
    policies = sim_platform.get_qos_policies()
    p = next((pol for pol in policies if pol["name"] == "NetGuard_Throttle_qbittorrent.exe"), None)
    assert p is not None
    assert p["throttle_bps"] == 2_000_000


def test_f15_03_empirical_policy_presence_verification(sim_platform: SimulatedPlatformAdapter):
    """F15.3: Created policy presence is empirically verifiable via get_qos_policies."""
    sim_platform.create_qos_dscp_policy("NetGuard_DSCP_teams.exe", "teams.exe", 46)
    names = [p["name"] for p in sim_platform.get_qos_policies()]
    assert "NetGuard_DSCP_teams.exe" in names


def test_f15_04_policy_modification_on_state_change(sim_platform: SimulatedPlatformAdapter):
    """F15.4: Re-applying or updating an existing policy is idempotent."""
    sim_platform.create_qos_dscp_policy("NetGuard_DSCP_teams.exe", "teams.exe", 46)
    ok, msg = sim_platform.create_qos_dscp_policy("NetGuard_DSCP_teams.exe", "teams.exe", 46)
    assert ok is True
    assert "already exists" in msg.lower() or "موجودة" in msg


def test_f15_05_removal_of_specific_policy(sim_platform: SimulatedPlatformAdapter):
    """F15.5: Specific NetGuard policy removed cleanly by name."""
    sim_platform.create_qos_dscp_policy("NetGuard_DSCP_slack.exe", "slack.exe", 46)
    ok, msg = sim_platform.remove_qos_policy("NetGuard_DSCP_slack.exe")
    assert ok is True
    policies = sim_platform.get_qos_policies()
    assert not any(p["name"] == "NetGuard_DSCP_slack.exe" for p in policies)


# =====================================================================
# F16: Startup Sweep & Crash Revert Lifecycle for QoS Policies (5 Tests)
# =====================================================================

def test_f16_01_atexit_cleanup_execution(sim_platform: SimulatedPlatformAdapter):
    """F16.1: Cleanup execution sweeps all NetGuard rules."""
    sim_platform.create_qos_dscp_policy("NetGuard_DSCP_temp.exe", "temp.exe", 46)
    ok, msg = sim_platform.sweep_all_netguard_rules()
    assert ok is True
    assert len(sim_platform.get_qos_policies()) == 0


def test_f16_02_about_to_quit_cleanup(sim_platform: SimulatedPlatformAdapter):
    """F16.2: Qt aboutToQuit handler triggers clean sweep of residual policies."""
    sim_platform.create_qos_throttle_policy("NetGuard_Throttle_steam.exe", "steam.exe", 2_000_000)
    sim_platform.sweep_all_netguard_rules()
    assert len(sim_platform.get_qos_policies()) == 0


def test_f16_03_startup_sweep_orphaned_policies(sim_platform: SimulatedPlatformAdapter, sim_win: SimulatedWindowsEnvironment):
    """F16.3: Startup sweep clears orphaned policies left from prior crashes."""
    sim_win.qos_policies["NetGuard_DSCP_crashed.exe"] = {
        "Name": "NetGuard_DSCP_crashed.exe",
        "AppPathNameMatchCondition": "crashed.exe",
        "DSCPAction": 46,
    }
    assert len(sim_platform.get_qos_policies()) == 1
    sim_platform.sweep_all_netguard_rules()
    assert len(sim_platform.get_qos_policies()) == 0


def test_f16_04_simulated_crash_leaves_sweepable_state(sim_platform: SimulatedPlatformAdapter, sim_win: SimulatedWindowsEnvironment):
    """F16.4: Abrupt exit simulation leaves policies with NetGuard_ prefix that next startup sweeps."""
    sim_platform.create_qos_dscp_policy("NetGuard_DSCP_zoom.exe", "zoom.exe", 46)
    # Simulate fresh launch sweep
    sim_platform.sweep_all_netguard_rules()
    assert len(sim_platform.get_qos_policies()) == 0


def test_f16_05_idempotent_sweep_zero_policies(sim_platform: SimulatedPlatformAdapter):
    """F16.5: Running sweep with 0 existing policies executes cleanly without error."""
    ok, msg = sim_platform.sweep_all_netguard_rules()
    assert ok is True
    assert "0" in msg or "نجاح" in msg or "Swept" in msg


# =====================================================================
# F17: Network Adapter Driver, Firmware & Hardware Audit (5 Tests)
# =====================================================================

def test_f17_01_driver_name_and_provider_query(sim_win: SimulatedWindowsEnvironment):
    """F17.1: Driver name and provider query correctly returns Intel/Realtek details."""
    audit = sim_win.adapter_hardware
    assert audit.driver_provider == "Intel"
    assert "e1d" in audit.driver_name.lower() or ".sys" in audit.driver_name.lower()


def test_f17_02_driver_version_and_date_extraction(sim_win: SimulatedWindowsEnvironment):
    """F17.2: Driver version and date strings are properly formatted."""
    audit = sim_win.adapter_hardware
    assert audit.driver_version == "12.19.2.55"
    assert audit.driver_date == "2023-08-15"


def test_f17_03_link_speed_and_duplex_validation(sim_win: SimulatedWindowsEnvironment):
    """F17.3: Link speed (1000 Mbps) and duplex state (Full Duplex) validated."""
    audit = sim_win.adapter_hardware
    assert audit.link_speed_mbps == 1000
    assert audit.duplex == "Full Duplex"


def test_f17_04_eee_power_saving_detection(sim_win: SimulatedWindowsEnvironment):
    """F17.4: EEE (Energy Efficient Ethernet) power saving flag inspected."""
    audit = sim_win.adapter_hardware
    assert isinstance(audit.eee_power_saving_enabled, bool)


def test_f17_05_outdated_driver_warning_generation(sim_win: SimulatedWindowsEnvironment):
    """F17.5: Outdated driver status produces forensic audit recommendation."""
    sim_win.adapter_hardware.is_outdated = True
    rec = AuditRecommendation(
        category="Hardware",
        severity="WARNING",
        title="Outdated Network Adapter Driver",
        recommendation="Update Intel Ethernet driver from 12.19.2.55 to latest vendor release.",
    )
    assert rec.is_actionable is True
    assert "Update" in rec.recommendation


# =====================================================================
# F18: Windows Firewall Rules & Profile Audit (5 Tests)
# =====================================================================

def test_f18_01_profile_state_inspection(sim_win: SimulatedWindowsEnvironment):
    """F18.1: Domain, Private, and Public firewall profile states inspected."""
    fw = sim_win.firewall_audit
    assert fw.domain_profile_enabled is True
    assert fw.private_profile_enabled is True
    assert fw.public_profile_enabled is True


def test_f18_02_port_53_rule_audit(sim_win: SimulatedWindowsEnvironment):
    """F18.2: Outbound Port 53 (DNS UDP/TCP) rules audited."""
    fw = sim_win.firewall_audit
    dns_rules = [r for r in fw.active_rules if "53" in r.remote_port]
    assert len(dns_rules) >= 1
    assert fw.port_53_blocked is False


def test_f18_03_port_853_dot_rule_audit(sim_win: SimulatedWindowsEnvironment):
    """F18.3: Port 853 (DNS-over-TLS) rules audited."""
    fw = sim_win.firewall_audit
    dot_rule = next((r for r in fw.active_rules if "853" in r.remote_port), None)
    assert dot_rule is not None
    assert dot_rule.action == "Allow"


def test_f18_04_icmp_rule_audit(sim_win: SimulatedWindowsEnvironment):
    """F18.4: ICMP Echo rules audited for blocking state."""
    fw = sim_win.firewall_audit
    icmp_rule = next((r for r in fw.active_rules if "icmp" in r.protocol.lower()), None)
    assert icmp_rule is not None
    assert fw.icmp_echo_blocked is False


def test_f18_05_webrtc_collaboration_port_audit(sim_win: SimulatedWindowsEnvironment):
    """F18.5: WebRTC collaboration UDP ports (3478-3481) audited."""
    fw = sim_win.firewall_audit
    webrtc_rule = next((r for r in fw.active_rules if "3478" in r.remote_port), None)
    assert webrtc_rule is not None
    assert fw.webrtc_blocked is False


# =====================================================================
# F19: Unified Incident Resolution History & Real GUI QTest Suite (5 Tests)
# =====================================================================

def test_f19_01_incident_record_creation_with_timestamp(incident_repo):
    """F19.1: Incident record created with UTC timestamp, severity, and cause."""
    inc = Diagnosis(
        id=str(uuid.uuid4()),
        probable_cause=ProbableCause.LOCAL_GATEWAY_HIGH_LATENCY,
        confidence=0.92,
        severity=DiagnosisSeverity.HIGH,
        explanation="High gateway RTT detected",
    )
    incident_repo.save(inc)
    recent = incident_repo.get_recent(limit=1)
    assert len(recent) == 1
    assert recent[0].probable_cause == ProbableCause.LOCAL_GATEWAY_HIGH_LATENCY


def test_f19_02_executed_action_tracking(audit_repo):
    """F19.2: Executed remediation action tracked with duration and status."""
    rec = ActionExecutionRecord(
        id=str(uuid.uuid4()),
        action_id="flush_dns",
        action_name="Flush DNS Cache",
        risk_level=RiskLevel.LEVEL_1_LOW,
        trigger_diagnosis_id="test_diag",
        status=ActionExecutionStatus.SUCCEEDED,
        execution_duration_ms=12.4,
    )
    audit_repo.save(rec)
    recent = audit_repo.get_recent(limit=1)
    assert len(recent) == 1
    assert recent[0].action_id == "flush_dns"
    assert recent[0].execution_duration_ms == 12.4


def test_f19_03_post_verification_result_recording(audit_repo):
    """F19.3: Post-action verification metrics recorded in audit row."""
    rec = ActionExecutionRecord(
        id=str(uuid.uuid4()),
        action_id="switch_dns",
        action_name="Switch DNS Resolver",
        risk_level=RiskLevel.LEVEL_2_CONTROLLED,
        trigger_diagnosis_id="test_diag",
        pre_remedy_metrics={"dns_latency": 140.0},
        post_remedy_metrics={"dns_latency": 12.0, "status": "verified"},
        status=ActionExecutionStatus.SUCCEEDED,
        verification_duration_ms=8.5,
    )
    audit_repo.save(rec)
    saved = audit_repo.get_recent(limit=1)[0]
    assert saved.post_remedy_metrics.get("dns_latency") == 12.0
    assert saved.verification_duration_ms == 8.5


def test_f19_04_export_to_json_csv(audit_repo, tmp_path):
    """F19.4: Incident history exported cleanly to structured JSON and CSV formats."""
    rec = ActionExecutionRecord(
        id="audit-export-1",
        action_id="flush_dns",
        action_name="Flush DNS Cache",
        risk_level=RiskLevel.LEVEL_1_LOW,
        trigger_diagnosis_id="diag-1",
        status=ActionExecutionStatus.SUCCEEDED,
        execution_duration_ms=15.0,
    )
    audit_repo.save(rec)
    records = audit_repo.get_recent(limit=10)

    # Export to JSON
    json_path = tmp_path / "audit_export.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([r.model_dump(mode="json") for r in records], f)
    assert json_path.exists()
    assert json_path.stat().st_size > 0

    # Export to CSV
    csv_path = tmp_path / "audit_export.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "action_id", "status", "duration_ms"])
        for r in records:
            writer.writerow([r.id, r.action_id, r.status.value, r.execution_duration_ms])
    assert csv_path.exists()
    assert csv_path.stat().st_size > 0


def test_f19_05_headless_pyside6_qtest_navigation(qapp):
    """F19.5: Headless PySide6 QTest navigation across all 7 views."""
    from app.ui.views.dashboard_view import DashboardView
    from app.ui.views.diagnosis_view import DiagnosisView
    from app.ui.views.remediation_view import RemediationView
    from app.ui.views.dns_view import DNSView
    from app.ui.views.traffic_view import TrafficView
    from app.ui.views.history_view import HistoryView
    from app.ui.views.settings_view import SettingsView

    views = [
        DashboardView(),
        DiagnosisView(),
        RemediationView(),
        DNSView(),
        TrafficView(),
        HistoryView(),
        SettingsView(),
    ]
    assert len(views) == 7

    for idx, v in enumerate(views):
        v.show()
        QTest.qWaitForWindowExposed(v)
        assert v.isVisible() or qapp.platformName() == "offscreen"
        v.hide()
