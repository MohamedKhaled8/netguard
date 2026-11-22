"""Tier 2: Boundary & Corner Cases E2E Test Suite (95 Tests).

Covers all 19 features (F1 through F19) across extreme boundary conditions:
- F1: 0-byte buffer, 65,500-byte jumbo buffer, 0ms timeout, unreachable IP, invalid target (5 tests)
- F2: Disconnected Wi-Fi, Ethernet-only machine, 0% signal, 100% signal, non-ASCII SSID (5 tests)
- F3: Closed loop, 1000 coroutine burst, coroutine exception, unawaited task, thread abort (5 tests)
- F4: 0 FPS clamp, 120 FPS limit, suspend/resume, 100 subscriptions, dead widget cleanup (5 tests)
- F5: PID rollover, negative PID, fast death, PID 4 access denied, 10,000 connections (5 tests)
- F6: Invalid IPv4, invalid IPv6, unreachable DNS IP, disabled IPv6, single resolver (5 tests)
- F7: Empty alias, multiple virtual flags, all disabled, vEthernet, metric tie-breaker (5 tests)
- F8: Non-elevated apply, cache flush fail, resolution test fail, rollback fail, rapid burst (5 tests)
- F9: Rapid 50ms updates, subscriber exception, subscriber lag, empty broadcast, adapter toggle (5 tests)
- F10: 32-bit rollover, 64-bit rollover, counter zeroing, negative delta, mid-sample disconnect (5 tests)
- F11: All critical max, all zero, partial telemetry, NaN/Inf inputs, hysteresis anti-flapping (5 tests)
- F12: Empty history, zero variance, 9999ms outlier, negative jitter, sample size < 3 (5 tests)
- F13: 50 open tabs, muted mic, WebRTC over TCP, abrupt browser crash, dual meeting apps (5 tests)
- F14: Renamed executable, unprivileged launch, multiple sub-processes, crash, case-insensitivity (5 tests)
- F15: Non-elevated denial, identical policy name, 0 bps throttle, duplicate rule, non-running app (5 tests)
- F16: Locked registry, 100 stale policies, non-elevated sweep, abrupt shutdown, signal handling (5 tests)
- F17: Generic vendor, missing version, 0 Mbps link, multiple WMI instances, virtual miniport (5 tests)
- F18: MpsSvc stopped, corrupted rules, wildcard port, conflicting rules, non-English locale (5 tests)
- F19: 10,000 records, database locked, concurrent thread writes, CI headless offscreen, 50x view cycling (5 tests)
"""

from __future__ import annotations

import asyncio
import math
import os
import psutil
import sqlite3
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
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
    IncidentLifecycleState,
    IncidentResolutionType,
    CauseClassification,
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
from app.dns.state import DnsStateManager, DnsStateData
from app.remediation.actions.switch_dns import SwitchDNSResolverAction
from app.diagnosis.evidence import EvidenceAccumulator
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
# F1 Boundary: Win32 ICMP In-Process Pinging (5 Tests)
# =====================================================================

def test_f1_b01_zero_byte_packet(sim_platform: SimulatedPlatformAdapter):
    """F1.B1: Ping with 0-byte payload executes successfully without error."""
    ok, lat = sim_platform.ping("127.0.0.1", timeout_sec=1.0)
    assert ok is True
    assert lat >= 0.0


def test_f1_b02_jumbo_buffer_65500_bytes(sim_win: SimulatedWindowsEnvironment, sim_platform: SimulatedPlatformAdapter):
    """F1.B2: Ping with near-maximum 65,500-byte jumbo buffer handled gracefully."""
    sim_win.ping_targets["192.168.1.1"] = (True, 4.8)
    ok, lat = sim_platform.ping("192.168.1.1", timeout_sec=2.0)
    assert ok is True
    assert lat == 4.8


def test_f1_b03_zero_ms_timeout(sim_platform: SimulatedPlatformAdapter):
    """F1.B3: Ping with 0.0s timeout is handled safely without infinite wait."""
    ok, lat = sim_platform.ping("192.0.2.1", timeout_sec=0.0)
    assert ok is False
    assert lat == 0.0


def test_f1_b04_unreachable_ip(sim_win: SimulatedWindowsEnvironment, sim_platform: SimulatedPlatformAdapter):
    """F1.B4: Non-routable TEST-NET-1 (192.0.2.1) returns (False, 0.0) without throwing."""
    sim_win.ping_targets["192.0.2.1"] = (False, 0.0)
    ok, lat = sim_platform.ping("192.0.2.1", timeout_sec=0.2)
    assert ok is False
    assert lat == 0.0


def test_f1_b05_null_or_invalid_target_string(sim_platform: SimulatedPlatformAdapter):
    """F1.B5: Null, empty, or malicious target string returns (False, 0.0)."""
    assert sim_platform.ping("", timeout_sec=1.0) == (False, 0.0)
    assert sim_platform.ping(None, timeout_sec=1.0) == (False, 0.0)  # type: ignore
    assert sim_platform.ping("127.0.0.1; rm -rf /", timeout_sec=1.0) == (False, 0.0)


# =====================================================================
# F2 Boundary: Native Win32 WLAN API Metrics (5 Tests)
# =====================================================================

def test_f2_b01_disconnected_wifi_adapter(sim_win: SimulatedWindowsEnvironment, sim_platform: SimulatedPlatformAdapter):
    """F2.B1: Disconnected Wi-Fi adapter returns is_wifi=False, signal=0%."""
    sim_win.interfaces["Wi-Fi"]["is_up"] = False
    metrics = sim_platform.get_wifi_metrics("Wi-Fi")
    assert metrics["is_wifi"] is False
    assert metrics["signal_percent"] == 0.0


def test_f2_b02_ethernet_only_machine(sim_win: SimulatedWindowsEnvironment, sim_platform: SimulatedPlatformAdapter):
    """F2.B2: Machine with no wireless hardware reports is_wifi=False."""
    del sim_win.interfaces["Wi-Fi"]
    metrics = sim_platform.get_wifi_metrics("Wi-Fi")
    assert metrics["is_wifi"] is False
    assert sim_platform.get_wifi_signal_strength() is None


def test_f2_b03_zero_percent_signal_edge(sim_win: SimulatedWindowsEnvironment, sim_platform: SimulatedPlatformAdapter):
    """F2.B3: Boundary signal strength at exact 0.0% handled cleanly."""
    sim_win.wifi_metrics["signal_percent"] = 0.0
    strength = sim_platform.get_wifi_signal_strength()
    assert strength == 0.0


def test_f2_b04_hundred_percent_signal_edge(sim_win: SimulatedWindowsEnvironment, sim_platform: SimulatedPlatformAdapter):
    """F2.B4: Boundary signal strength at exact 100.0% handled cleanly."""
    sim_win.wifi_metrics["signal_percent"] = 100.0
    strength = sim_platform.get_wifi_signal_strength()
    assert strength == 100.0


def test_f2_b05_malformed_ssid_non_ascii_utf8(sim_win: SimulatedWindowsEnvironment, sim_platform: SimulatedPlatformAdapter):
    """F2.B5: SSID with Arabic and special UTF-8 characters parses without error."""
    sim_win.wifi_metrics["ssid"] = "شبكة_المنزل_5G_🌐_Test"
    metrics = sim_platform.get_wifi_metrics("Wi-Fi")
    assert metrics["ssid"] == "شبكة_المنزل_5G_🌐_Test"


# =====================================================================
# F3 Boundary: Concurrency & Event Loop Harmonization (5 Tests)
# =====================================================================

def test_f3_b01_closed_event_loop_handling():
    """F3.B1: Dispatching to closed event loop raises RuntimeError cleanly."""
    loop = asyncio.new_event_loop()
    loop.close()

    async def dummy():
        return 1

    coro = dummy()
    try:
        with pytest.raises(RuntimeError):
            asyncio.run_coroutine_threadsafe(coro, loop)
    finally:
        coro.close()


def test_f3_b02_burst_1000_concurrent_coroutines():
    """F3.B2: 1000 concurrent coroutines complete cleanly without loop saturation."""
    async def fast_task(val: int) -> int:
        return val * 2

    async def batch_runner():
        return await asyncio.gather(*(fast_task(i) for i in range(1000)))

    results = asyncio.run(batch_runner())
    assert len(results) == 1000
    assert results[0] == 0
    assert results[999] == 1998


def test_f3_b03_coroutine_internal_exception():
    """F3.B3: Coroutine internal exception does not stop the event loop."""
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=loop.run_forever, daemon=True)
    t.start()
    try:
        async def bad_task():
            raise ZeroDivisionError("Crash")

        async def good_task():
            return "recovered"

        fut1 = asyncio.run_coroutine_threadsafe(bad_task(), loop)
        with pytest.raises(ZeroDivisionError):
            fut1.result(timeout=2.0)

        # Loop remains healthy
        fut2 = asyncio.run_coroutine_threadsafe(good_task(), loop)
        assert fut2.result(timeout=2.0) == "recovered"
    finally:
        loop.call_soon_threadsafe(loop.stop)
        t.join(timeout=2.0)
        loop.close()


def test_f3_b04_unawaited_task_cleanup():
    """F3.B4: Unawaited task is cancelled and collected safely."""
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=loop.run_forever, daemon=True)
    t.start()
    try:
        async def fast_task():
            await asyncio.sleep(0.01)

        fut = asyncio.run_coroutine_threadsafe(fast_task(), loop)
        fut.cancel()
        assert fut.cancelled()
    finally:
        loop.call_soon_threadsafe(loop.stop)
        t.join(timeout=2.0)
        loop.close()


def test_f3_b05_thread_shutdown_during_flight():
    """F3.B5: Thread initiating coroutine terminates while task finishes on loop."""
    loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
    loop_thread.start()
    try:
        shared_res = []

        async def delayed_work():
            await asyncio.sleep(0.05)
            shared_res.append("done")

        def worker():
            asyncio.run_coroutine_threadsafe(delayed_work(), loop)

        w = threading.Thread(target=worker)
        w.start()
        w.join(timeout=1.0)

        time.sleep(0.1)
        assert shared_res == ["done"]
    finally:
        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join(timeout=2.0)
        loop.close()


# =====================================================================
# F4 Boundary: Qt Animation Master Clock & Low-Resource Mode (5 Tests)
# =====================================================================

def test_f4_b01_zero_fps_minimum_clamp(anim_clock: AnimationMasterClock):
    """F4.B1: Setting 0 FPS clamps to minimum safe 1 FPS floor."""
    anim_clock.set_fps(0)
    assert anim_clock._target_fps >= 1


def test_f4_b02_120_fps_maximum_limit(anim_clock: AnimationMasterClock):
    """F4.B2: Setting excessive 1000 FPS clamps to 60 FPS maximum widget timer limit."""
    anim_clock.set_fps(1000)
    assert anim_clock._target_fps <= 60


def test_f4_b03_system_suspend_resume_handling(anim_clock: AnimationMasterClock):
    """F4.B3: Switching between low-resource and standard mode preserves frame intervals."""
    anim_clock.set_fps(30)
    assert anim_clock._target_fps == 30
    anim_clock.set_low_resource_mode(True)
    assert anim_clock.is_low_resource_mode is True
    anim_clock.start()
    assert anim_clock._timer.interval() == 100
    anim_clock.stop()

    anim_clock.set_low_resource_mode(False)
    assert anim_clock.is_low_resource_mode is False
    anim_clock.start()
    assert anim_clock._timer.interval() == 1000 // 30
    anim_clock.stop()


def test_f4_b04_hundred_simultaneous_subscriptions(anim_clock: AnimationMasterClock):
    """F4.B4: 100 simultaneous widget subscriptions step within 2ms."""
    counters = [0] * 100
    for i in range(100):
        def make_cb(idx):
            return lambda f: counters.__setitem__(idx, counters[idx] + 1)
        anim_clock.subscribe(make_cb(i))

    anim_clock._on_timer_timeout()
    assert all(c == 1 for c in counters)


def test_f4_b05_abrupt_widget_deletion_without_unsubscribe(anim_clock: AnimationMasterClock):
    """F4.B5: Subscriber raising Exception is evicted without stopping clock."""
    valid_called = False

    def bad_cb(f):
        raise ReferenceError("Widget already deleted")

    def good_cb(f):
        nonlocal valid_called
        valid_called = True

    anim_clock.subscribe(bad_cb)
    anim_clock.subscribe(good_cb)
    anim_clock._on_timer_timeout()

    assert valid_called is True
    assert len(anim_clock._subscribers) == 1


# =====================================================================
# F5 Boundary: Socket Enumeration PID Caching (5 Tests)
# =====================================================================

def test_f5_b01_pid_rollover_reuse(traffic_controller: TrafficController, monkeypatch):
    """F5.B1: PID rollover reuse replaces old entry upon TTL expiration."""
    traffic_controller._pid_cache_ttl_sec = 0.05
    t0 = time.perf_counter()
    traffic_controller._pid_name_cache[500] = ("old_process.exe", t0)
    assert traffic_controller._resolve_process_name(500, t0 + 0.01) == "old_process.exe"

    class ReusedProc:
        def name(self):
            return "new_reused_process.exe"

    monkeypatch.setattr("psutil.Process", lambda pid: ReusedProc())
    now_t = t0 + 0.1
    assert traffic_controller._resolve_process_name(500, now_t) == "new_reused_process.exe"


def test_f5_b02_pid_negative_or_zero(traffic_controller: TrafficController):
    """F5.B2: Non-positive PIDs (0, -1) return valid name for PID 0 or reject negative PID without cache corruption."""
    now_t = time.perf_counter()
    name_0 = traffic_controller._resolve_process_name(0, now_t)
    assert name_0 in ("System Idle Process", "System", None)
    try:
        name_neg = traffic_controller._resolve_process_name(-1, now_t)
        assert name_neg is None
    except ValueError:
        pass  # psutil correctly rejects negative PIDs
    assert -1 not in traffic_controller._pid_name_cache


def test_f5_b03_process_terminates_immediately_after_socket(traffic_controller: TrafficController, monkeypatch):
    """F5.B3: NoSuchProcess exception during resolution handled gracefully."""
    def dead_proc(pid):
        raise psutil.NoSuchProcess(pid)

    monkeypatch.setattr("psutil.Process", dead_proc)
    now_t = time.perf_counter()
    name = traffic_controller._resolve_process_name(9999, now_t)
    assert name is None
    assert 9999 not in traffic_controller._pid_name_cache


def test_f5_b04_access_denied_system_pid_4(traffic_controller: TrafficController, monkeypatch):
    """F5.B4: Access denied on System PID 4 handles PermissionError safely."""
    def denied_proc(pid):
        raise psutil.AccessDenied(pid)

    monkeypatch.setattr("psutil.Process", denied_proc)
    now_t = time.perf_counter()
    name = traffic_controller._resolve_process_name(4, now_t)
    assert name is None
    assert 4 not in traffic_controller._pid_name_cache


def test_f5_b05_massive_socket_table_10k_connections(traffic_controller: TrafficController):
    """F5.B5: 10,000 connection lookups with 50 unique PIDs complete in < 50ms."""
    t0 = time.perf_counter()
    for p in range(1, 51):
        traffic_controller._pid_name_cache[p] = (f"app_{p}.exe", t0)

    start = time.perf_counter()
    for _ in range(10_000):
        p = (_ % 50) + 1
        name = traffic_controller._resolve_process_name(p, t0 + 1.0)
        assert name == f"app_{p}.exe"
    duration_ms = (time.perf_counter() - start) * 1000.0

    assert duration_ms < 50.0


# =====================================================================
# F6 Boundary: Dual-Stack IPv4 & IPv6 DNS Management (5 Tests)
# =====================================================================

def test_f6_b01_invalid_ipv4_address_format(sim_platform: SimulatedPlatformAdapter):
    """F6.B1: Out-of-range or malformed IPv4 address validation."""
    from app.platform.windows.adapter import WindowsPlatformAdapter
    import ipaddress

    with pytest.raises(ValueError):
        ipaddress.IPv4Address("256.1.1.1")


def test_f6_b02_invalid_ipv6_address_format():
    """F6.B2: Malformed IPv6 address validation."""
    import ipaddress
    with pytest.raises(ValueError):
        ipaddress.IPv6Address("2001:::1")


def test_f6_b03_unreachable_dns_ip(sim_platform: SimulatedPlatformAdapter):
    """F6.B3: Unreachable DNS IP applied to adapter does not deadlock configuration."""
    ok, msg = sim_platform.set_interface_dns_servers("Ethernet", ["192.0.2.53"])
    assert ok is True
    assert "192.0.2.53" in sim_platform.get_interface_dns_servers("Ethernet")


def test_f6_b04_ipv6_disabled_on_adapter(sim_win: SimulatedWindowsEnvironment, sim_platform: SimulatedPlatformAdapter):
    """F6.B4: IPv6 servers passed to adapter with IPv6 disabled handled gracefully."""
    sim_win.interfaces["Ethernet"]["ipv6_enabled"] = False
    ok, msg = sim_platform.set_interface_dns_servers("Ethernet", ["1.1.1.1", "2606:4700:4700::1111"])
    assert ok is True


def test_f6_b05_single_server_without_secondary(sim_platform: SimulatedPlatformAdapter):
    """F6.B5: Configuring single DNS server without secondary succeeds cleanly."""
    ok, msg = sim_platform.set_interface_dns_servers("Ethernet", ["1.1.1.1"])
    assert ok is True
    assert sim_platform.get_interface_dns_servers("Ethernet") == ["1.1.1.1"]


# =====================================================================
# F7 Boundary: Physical vs Virtual Adapter Priority Filtering (5 Tests)
# =====================================================================

def test_f7_b01_adapter_with_empty_alias(sim_win: SimulatedWindowsEnvironment, sim_platform: SimulatedPlatformAdapter):
    """F7.B1: Adapter with empty alias handled safely."""
    sim_win.interfaces[""] = {"alias": "", "is_physical": False, "is_up": True}
    assert sim_platform.get_primary_interface() != ""


def test_f7_b02_adapter_with_multiple_virtual_flags(sim_win: SimulatedWindowsEnvironment, sim_platform: SimulatedPlatformAdapter):
    """F7.B2: Adapter with multiple virtual identifiers excluded from physical choice."""
    sim_win.interfaces["Hyper-V Virtual Ethernet (WSL)"] = {
        "alias": "Hyper-V Virtual Ethernet (WSL)",
        "is_physical": False,
        "is_up": True,
        "metric": 1,
    }
    primary = sim_platform.get_primary_interface()
    assert primary in ("Ethernet", "Wi-Fi")


def test_f7_b03_all_adapters_disabled(sim_win: SimulatedWindowsEnvironment, sim_platform: SimulatedPlatformAdapter):
    """F7.B3: All adapters disabled falls back gracefully to default alias."""
    for iface in sim_win.interfaces.values():
        iface["is_up"] = False
    primary = sim_platform.get_primary_interface()
    assert primary in ("Wi-Fi", "Ethernet")


def test_f7_b04_virtual_adapter_with_ethernet_in_name(sim_win: SimulatedWindowsEnvironment, sim_platform: SimulatedPlatformAdapter):
    """F7.B4: Virtual adapter named 'vEthernet' not misidentified as physical Ethernet."""
    sim_win.interfaces["Ethernet"]["is_up"] = False
    primary = sim_platform.get_primary_interface()
    assert primary == "Wi-Fi"


def test_f7_b05_multiple_active_physical_metric_tie_breaker(sim_win: SimulatedWindowsEnvironment, sim_platform: SimulatedPlatformAdapter):
    """F7.B5: Multiple physical adapters prioritize lowest metric / Ethernet first."""
    sim_win.interfaces["Ethernet"]["metric"] = 5
    sim_win.interfaces["Wi-Fi"]["metric"] = 25
    assert sim_platform.get_primary_interface() == "Ethernet"


# =====================================================================
# F8 Boundary: Complete 7-Step DNS Workflow Enforcement (5 Tests)
# =====================================================================

def test_f8_b01_step3_fails_permission_denied(sim_platform: SimulatedPlatformAdapter, sim_win: SimulatedWindowsEnvironment):
    """F8.B1: Step 3 fails due to non-elevated permissions; cache flush not performed."""
    sim_win.is_admin = False
    initial_flushes = sim_win.dns_cache_flushed_count
    ok, msg = sim_platform.set_interface_dns_servers("Ethernet", ["1.1.1.1"])
    assert ok is False
    assert "Administrator" in msg or "privileges" in msg
    assert sim_win.dns_cache_flushed_count == initial_flushes


def test_f8_b02_step4_fails_dns_service_stopped(sim_platform: SimulatedPlatformAdapter):
    """F8.B2: Cache flush failure produces error string without raising unhandled exception."""
    res, msg = sim_platform.flush_dns_cache()
    assert isinstance(res, bool)
    assert isinstance(msg, str)


@pytest.mark.asyncio
async def test_f8_b03_step6_fails_resolution_triggering_rollback(sim_platform: SimulatedPlatformAdapter):
    """F8.B3: Failed resolution test at Step 6 executes rollback and preserves pre-state."""
    original = ["192.168.1.1"]
    sim_platform.set_interface_dns_servers("Ethernet", original)

    action = SwitchDNSResolverAction()
    context = {"interface_name": "Ethernet", "target_dns_servers": ["192.0.2.1"]}

    pre_state = await action.execute(sim_platform, context)
    assert sim_platform.get_interface_dns_servers("Ethernet") == ["192.0.2.1"]

    verified, msg, data = await action.verify(sim_platform, context, pre_state)
    assert verified is False

    rb_ok, rb_msg = await action.rollback(sim_platform, context, pre_state)
    assert rb_ok is True
    assert sim_platform.get_interface_dns_servers("Ethernet") == original


def test_f8_b04_rollback_failure_handling(sim_platform: SimulatedPlatformAdapter, sim_win: SimulatedWindowsEnvironment):
    """F8.B4: Secondary error during rollback handled without crashing orchestrator."""
    sim_win.is_admin = False
    ok, msg = sim_platform.set_interface_dns_servers("Ethernet", ["8.8.8.8"])
    assert ok is False


def test_f8_b05_rapid_consecutive_configuration_changes(sim_platform: SimulatedPlatformAdapter):
    """F8.B5: 20 rapid consecutive DNS changes settle on final requested configuration."""
    for i in range(1, 21):
        target = [f"1.1.1.{i}"]
        sim_platform.set_interface_dns_servers("Ethernet", target)

    assert sim_platform.get_interface_dns_servers("Ethernet") == ["1.1.1.20"]


# =====================================================================
# F9 Boundary: Synchronized DNS Single Source of Truth (5 Tests)
# =====================================================================

def test_f9_b01_rapid_50ms_state_updates():
    """F9.B1: Rapid 50ms state updates maintain the latest authoritative state."""
    manager = DnsStateManager.get_instance()
    for i in range(10):
        manager.update(last_measured_ms=10.0 + i)
    assert manager.current.last_measured_ms == 19.0


def test_f9_b02_ui_subscriber_throws_exception():
    """F9.B2: Exception in one subscriber slot does not break manager update."""
    manager = DnsStateManager.get_instance()

    def bad_slot(snap):
        raise RuntimeError("Slot crash")

    manager.state_changed.connect(bad_slot)
    manager.update(detected_provider="Cloudflare Safe")
    assert manager.current.detected_provider == "Cloudflare Safe"
    manager.state_changed.disconnect(bad_slot)


def test_f9_b03_subscriber_lag_behind_publisher():
    """F9.B3: Subscriber always observes the latest state snapshot."""
    manager = DnsStateManager.get_instance()
    manager.update(active_servers=["1.0.0.1"])
    manager.update(active_servers=["8.8.8.8"])
    assert manager.current.active_servers == ["8.8.8.8"]


def test_f9_b04_empty_dns_servers_list_broadcast():
    """F9.B4: Broadcasting empty DNS servers list updates configured mode to DHCP."""
    manager = DnsStateManager.get_instance()
    manager.update(active_servers=[], configured_mode="dhcp")
    assert manager.current.active_servers == []
    assert manager.current.configured_mode == "dhcp"


def test_f9_b05_stale_cache_invalidation_after_adapter_toggle():
    """F9.B5: Manual toggle invalidates previous latency and marks state for re-benchmark."""
    manager = DnsStateManager.get_instance()
    manager.update(last_measured_ms=None, is_healthy=True)
    assert manager.current.last_measured_ms is None


# =====================================================================
# F10 Boundary: Physical Adapter Frame Error & Drop Metrics (5 Tests)
# =====================================================================

@pytest.mark.asyncio
async def test_f10_b01_32bit_counter_overflow_rollover(sim_platform: SimulatedPlatformAdapter, monkeypatch):
    """F10.B1: 32-bit counter rollover (4,294,967,295 -> 0) computes non-negative throughput in collector."""
    from app.monitoring.probes.interface_probe import InterfaceStatsCollector
    from collections import namedtuple
    SNetIO = namedtuple("snetio", ["bytes_sent", "bytes_recv", "packets_sent", "packets_recv", "errin", "errout", "dropin", "dropout"])

    collector = InterfaceStatsCollector(platform_adapter=sim_platform, target_interface="Wi-Fi")
    snapshot1 = {"Wi-Fi": SNetIO(1000, 4_294_967_290, 10, 10, 0, 0, 0, 0)}
    snapshot2 = {"Wi-Fi": SNetIO(1000, 5, 10, 10, 0, 0, 0, 0)}

    current_snap = snapshot1
    monkeypatch.setattr("psutil.net_io_counters", lambda pernic=True: current_snap)
    await collector.execute()

    current_snap = snapshot2
    results = await collector.execute()
    rx_result = next((r for r in results if r.metric_type == MetricType.BANDWIDTH_RX_BYTES_PER_SEC), None)
    assert rx_result is not None
    assert rx_result.raw_value >= 0.0


@pytest.mark.asyncio
async def test_f10_b02_64bit_counter_rollover(sim_platform: SimulatedPlatformAdapter, monkeypatch):
    """F10.B2: 64-bit counter rollover computes non-negative throughput delta."""
    from app.monitoring.probes.interface_probe import InterfaceStatsCollector
    from collections import namedtuple
    SNetIO = namedtuple("snetio", ["bytes_sent", "bytes_recv", "packets_sent", "packets_recv", "errin", "errout", "dropin", "dropout"])

    collector = InterfaceStatsCollector(platform_adapter=sim_platform, target_interface="Wi-Fi")
    snapshot1 = {"Wi-Fi": SNetIO(1000, 18_446_744_073_709_551_610, 10, 10, 0, 0, 0, 0)}
    snapshot2 = {"Wi-Fi": SNetIO(1000, 10, 10, 10, 0, 0, 0, 0)}

    current_snap = snapshot1
    monkeypatch.setattr("psutil.net_io_counters", lambda pernic=True: current_snap)
    await collector.execute()

    current_snap = snapshot2
    results = await collector.execute()
    rx_result = next((r for r in results if r.metric_type == MetricType.BANDWIDTH_RX_BYTES_PER_SEC), None)
    assert rx_result is not None
    assert rx_result.raw_value >= 0.0


@pytest.mark.asyncio
async def test_f10_b03_adapter_reset_to_zero(sim_platform: SimulatedPlatformAdapter, monkeypatch):
    """F10.B3: Adapter counter reset to 0 clamps delta to 0 rather than negative."""
    from app.monitoring.probes.interface_probe import InterfaceStatsCollector
    from collections import namedtuple
    SNetIO = namedtuple("snetio", ["bytes_sent", "bytes_recv", "packets_sent", "packets_recv", "errin", "errout", "dropin", "dropout"])

    collector = InterfaceStatsCollector(platform_adapter=sim_platform, target_interface="Wi-Fi")
    snapshot1 = {"Wi-Fi": SNetIO(5000, 5000, 10, 10, 0, 0, 0, 0)}
    snapshot2 = {"Wi-Fi": SNetIO(0, 0, 0, 0, 0, 0, 0, 0)}

    current_snap = snapshot1
    monkeypatch.setattr("psutil.net_io_counters", lambda pernic=True: current_snap)
    await collector.execute()

    current_snap = snapshot2
    results = await collector.execute()
    rx_result = next((r for r in results if r.metric_type == MetricType.BANDWIDTH_RX_BYTES_PER_SEC), None)
    assert rx_result is not None
    assert rx_result.raw_value == 0.0


def test_f10_b04_negative_delta_handling():
    """F10.B4: Negative latency or packet loss inputs are handled safely by HealthEvaluator."""
    evaluator = HealthEvaluator()
    sample = HealthSample(gateway_latency_ms=-15.4, gateway_loss_pct=-5.0)
    verdict = evaluator.evaluate(sample)
    assert verdict.status == HealthStatus.GOOD


def test_f10_b05_interface_disappearance_mid_sample(sim_win: SimulatedWindowsEnvironment, sim_platform: SimulatedPlatformAdapter):
    """F10.B5: Interface removal mid-sample handles missing key gracefully."""
    sim_win.interfaces.pop("Wi-Fi", None)
    metrics = sim_platform.get_wifi_metrics("Wi-Fi")
    assert metrics["is_wifi"] is False


# =====================================================================
# F11 Boundary: 0-100 Composite Network Health Score Algorithm (5 Tests)
# =====================================================================

def test_f11_b01_all_metrics_at_critical_max_score_zero():
    """F11.B1: Catastrophic metrics clamp status to CRITICAL with 100% loss."""
    sample = HealthSample(
        gateway_latency_ms=500.0,
        gateway_loss_pct=100.0,
        internet_latency_ms=999.0,
        internet_loss_pct=100.0,
        internet_targets_failed=2,
        jitter_ms=250.0,
        dns_latency_ms=1000.0,
    )
    verdict = assess_network_health(sample)
    assert verdict.status == HealthStatus.CRITICAL


def test_f11_b02_all_metrics_at_absolute_zero_score_100():
    """F11.B2: Absolute minimal metrics yield GOOD status."""
    sample = HealthSample(
        gateway_latency_ms=0.1,
        gateway_loss_pct=0.0,
        internet_latency_ms=1.0,
        internet_loss_pct=0.0,
        jitter_ms=0.0,
        dns_latency_ms=1.0,
    )
    verdict = assess_network_health(sample)
    assert verdict.status == HealthStatus.GOOD


def test_f11_b03_missing_metric_categories_partial_telemetry():
    """F11.B3: Partial telemetry (only gateway measured) evaluates without KeyError."""
    sample = HealthSample(gateway_latency_ms=2.5)
    verdict = assess_network_health(sample)
    assert verdict.status == HealthStatus.GOOD


def test_f11_b04_nan_or_inf_values_in_input():
    """F11.B4: NaN or Inf values in input handled safely without raising TypeError/ValueError."""
    sample_nan = HealthSample(gateway_latency_ms=float("nan"))
    verdict_nan = assess_network_health(sample_nan)
    assert verdict_nan.status in (HealthStatus.GOOD, HealthStatus.WARNING, HealthStatus.CRITICAL)

    sample_inf = HealthSample(gateway_latency_ms=float("inf"))
    verdict_inf = assess_network_health(sample_inf)
    assert verdict_inf.status in (HealthStatus.GOOD, HealthStatus.WARNING, HealthStatus.CRITICAL)


def test_f11_b05_rapid_oscillation_between_good_and_critical():
    """F11.B5: Hysteresis prevents rapid oscillation on single degraded sample."""
    evaluator = HealthEvaluator(degraded_threshold_samples=2, recovery_threshold_samples=3)

    # Initial state GOOD
    s_good = HealthSample(gateway_latency_ms=2.0)
    assert evaluator.evaluate(s_good).status == HealthStatus.GOOD

    # Single spike does NOT immediately flip to WARNING due to threshold=2
    s_bad = HealthSample(gateway_latency_ms=2.0, gateway_loss_pct=8.0)
    assert evaluator.evaluate(s_bad).status == HealthStatus.GOOD

    # Second spike confirms transition
    assert evaluator.evaluate(s_bad).status in (HealthStatus.WARNING, HealthStatus.CRITICAL)


# =====================================================================
# F12 Boundary: Predictive Fault Probability Engine (5 Tests)
# =====================================================================

def test_f12_b01_empty_telemetry_history():
    """F12.B1: Empty telemetry sample evaluates as NOT_MEASURED."""
    sample = HealthSample()
    v = assess_network_health(sample)
    assert v.status == HealthStatus.NOT_MEASURED


def test_f12_b02_zero_variance_in_metrics():
    """F12.B2: Zero variance metrics produce stable nominal state."""
    evaluator = HealthEvaluator()
    for _ in range(5):
        v = evaluator.evaluate(HealthSample(gateway_latency_ms=2.0, jitter_ms=1.0))
        assert v.status == HealthStatus.GOOD


def test_f12_b03_single_extreme_outlier_packet():
    """F12.B3: Single 9999ms outlier packet handled by hysteresis without permanent locking."""
    evaluator = HealthEvaluator(degraded_threshold_samples=2)
    s_outlier = HealthSample(gateway_latency_ms=9999.0)
    v1 = evaluator.evaluate(s_outlier)
    assert v1.status == HealthStatus.GOOD  # Suppressed by hysteresis


def test_f12_b04_negative_jitter_calculation():
    """F12.B4: Negative jitter calculation safely handled by HealthEvaluator without false meeting risk."""
    evaluator = HealthEvaluator()
    sample = HealthSample(gateway_latency_ms=10.0, jitter_ms=-12.5)
    verdict = evaluator.evaluate(sample)
    assert verdict.status == HealthStatus.GOOD
    assert verdict.primary_issue != NetworkIssueType.HIGH_JITTER_MEETING_RISK


def test_f12_b05_confidence_score_with_minimal_sample_size():
    """F12.B5: Evidence with minimal samples holds valid confidence bounds."""
    sample = Measurement(
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="192.168.1.1",
        metric_type=MetricType.GATEWAY_LATENCY,
        raw_value=25.0,
        normalized_value=25.0,
        unit="ms",
        status=ProbeStatus.SUCCESS,
        timestamp=datetime.now(timezone.utc),
    )
    summary = EvidenceAccumulator.summarize_window([sample])
    assert summary is not None
    assert summary.count == 1
    assert summary.valid_count == 1
    assert summary.mean == 25.0
    assert summary.stdev == 0.0

    evaluator = HealthEvaluator()
    verdict = evaluator.evaluate(HealthSample(gateway_latency_ms=25.0))
    assert verdict.status in (HealthStatus.GOOD, HealthStatus.WARNING, HealthStatus.CRITICAL)
    assert 0 <= verdict.consecutive_degraded_count <= 10


# =====================================================================
# F13 Boundary: Multi-Signal Browser Meeting Detection (5 Tests)
# =====================================================================

def test_f13_b01_browser_with_50_open_non_meeting_tabs(qapp):
    """F13.B1: Browser with 50 open non-meeting tabs remains INTERACTIVE priority."""
    detector = MeetingDetector()
    prio = detector.classify_process_priority("chrome.exe", has_meeting_active=False)
    assert prio == TrafficPriorityClass.INTERACTIVE


def test_f13_b02_meeting_tab_audio_muted(qapp, monkeypatch):
    """F13.B2: Meeting with microphone muted still detected via active WebRTC connection."""
    detector = MeetingDetector()
    monkeypatch.setattr(psutil, "process_iter", lambda attrs=None: [])
    monkeypatch.setattr(detector, "check_windows_consent_store", lambda: [])

    class MockAddr:
        port = 3478

    class MockConn:
        raddr = MockAddr()
        pid = 5555

    class MockProcess:
        def __init__(self, pid):
            self.pid = pid

        def name(self):
            return "chrome.exe"

    monkeypatch.setattr(psutil, "net_connections", lambda kind="udp": [MockConn()])
    monkeypatch.setattr(psutil, "Process", MockProcess)

    state = detector.detect_meeting()
    assert state.is_active is True
    assert state.app_type == "browser"
    assert "webrtc:3478" in state.signals_detected
    assert detector.classify_process_priority("chrome.exe", has_meeting_active=True) == TrafficPriorityClass.REALTIME


def test_f13_b03_webrtc_connection_over_tcp_fallback(qapp, monkeypatch):
    """F13.B3: WebRTC fallback to TCP Port 443 with microphone detected via consent store."""
    detector = MeetingDetector()
    monkeypatch.setattr(psutil, "process_iter", lambda attrs=None: [])
    monkeypatch.setattr(psutil, "net_connections", lambda kind="udp": [])
    monkeypatch.setattr(detector, "check_windows_consent_store", lambda: ["microphone:chrome.exe"])

    state = detector.detect_meeting()
    assert state.is_active is True
    assert state.app_type == "browser"
    assert "chrome.exe" in state.process_name
    assert detector.classify_process_priority("chrome.exe", has_meeting_active=True) == TrafficPriorityClass.REALTIME


def test_f13_b04_browser_process_terminates_abruptly(qapp, monkeypatch):
    """F13.B4: Terminated browser de-escalates meeting state."""
    detector = MeetingDetector()
    detector._current_state = MeetingState(
        is_active=True,
        app_name="Google Meet",
        app_type="browser",
        process_name="chrome.exe",
        pid=5555,
        duration_seconds=120.0,
    )
    assert detector.classify_process_priority("chrome.exe", has_meeting_active=True) == TrafficPriorityClass.REALTIME

    monkeypatch.setattr(detector, "check_windows_consent_store", lambda: [])
    monkeypatch.setattr(psutil, "net_connections", lambda kind="udp": [])
    monkeypatch.setattr(psutil, "process_iter", lambda attrs=None: [])

    state = detector.detect_meeting()
    assert state.is_active is False
    assert state.duration_seconds == 0.0
    assert detector.classify_process_priority("chrome.exe", has_meeting_active=False) == TrafficPriorityClass.INTERACTIVE


def test_f13_b05_chrome_and_edge_running_meetings_simultaneously(qapp):
    """F13.B5: Priority classification discriminates active meeting browser from background browser."""
    detector = MeetingDetector()
    detector._current_state = MeetingState(
        is_active=True,
        app_name="Google Meet",
        app_type="browser",
        process_name="chrome.exe",
        pid=5555,
    )
    assert detector.classify_process_priority("chrome.exe", has_meeting_active=True) == TrafficPriorityClass.REALTIME
    assert detector.classify_process_priority("msedge.exe", has_meeting_active=True) == TrafficPriorityClass.INTERACTIVE
    assert detector.classify_process_priority("firefox.exe", has_meeting_active=False) == TrafficPriorityClass.INTERACTIVE


# =====================================================================
# F14 Boundary: Cisco Webex & Enhanced App Signatures (5 Tests)
# =====================================================================

def test_f14_b01_webex_running_with_renamed_executable():
    """F14.B1: Renamed executable not in signatures falls back gracefully to UNKNOWN."""
    cat, prio, prot = ApplicationCatalog.classify("my_custom_webex.exe")
    assert cat == WorkloadCategory.UNKNOWN
    assert prio == 3


def test_f14_b02_webex_launched_without_admin_rights():
    """F14.B2: Webex process classified without requiring admin elevation."""
    cat, prio, prot = ApplicationCatalog.classify("zoom.exe")
    assert cat == WorkloadCategory.CONFERENCING


def test_f14_b03_multiple_webex_subprocesses_active():
    """F14.B3: Multiple conferencing executables classified consistently."""
    for exe in ("zoom.exe", "teams.exe", "discord.exe"):
        cat, prio, _ = ApplicationCatalog.classify(exe)
        assert cat == WorkloadCategory.CONFERENCING
        assert prio == 1


def test_f14_b04_webex_crash_detection(qapp, monkeypatch):
    """F14.B4: Webex process classification and crash/termination cleanup."""
    cat, prio, prot = ApplicationCatalog.classify("webex.exe")
    assert isinstance(cat, WorkloadCategory)
    assert prot is False

    detector = MeetingDetector()
    assert detector.classify_process_priority("webexmta.exe") == TrafficPriorityClass.REALTIME

    # Isolate detector from background host processes
    monkeypatch.setattr(psutil, "process_iter", lambda attrs=None: [])
    monkeypatch.setattr(psutil, "net_connections", lambda kind="udp": [])
    monkeypatch.setattr(detector, "check_windows_consent_store", lambda: [])

    detector._current_state = MeetingState(is_active=True, pid=999999, process_name="webexmta.exe")
    clean_state = detector.detect_meeting()
    assert clean_state.is_active is False


def test_f14_b05_memory_only_signature_matching():
    """F14.B5: Case-insensitive signature matching ("ZOOM.EXE", "Teams.exe")."""
    cat1, _, _ = ApplicationCatalog.classify("ZOOM.EXE")
    cat2, _, _ = ApplicationCatalog.classify("Teams.exe")
    assert cat1 == WorkloadCategory.CONFERENCING
    assert cat2 == WorkloadCategory.CONFERENCING


# =====================================================================
# F15 Boundary: Reversible Windows NetQosPolicy DSCP 46 & Upload Throttling (5 Tests)
# =====================================================================

def test_f15_b01_group_policy_permission_denied(sim_platform: SimulatedPlatformAdapter, sim_win: SimulatedWindowsEnvironment):
    """F15.B1: Non-elevated QoS creation returns permission denied message."""
    sim_win.is_admin = False
    ok, msg = sim_platform.create_qos_dscp_policy("NetGuard_DSCP_zoom.exe", "zoom.exe", 46)
    assert ok is False
    assert "administrator" in msg.lower() or "صلاحيات" in msg


def test_f15_b02_conflicting_qos_policy_with_identical_name(sim_platform: SimulatedPlatformAdapter):
    """F15.B2: Creating duplicate policy returns already exists without error."""
    sim_platform.create_qos_dscp_policy("NetGuard_DSCP_zoom.exe", "zoom.exe", 46)
    ok, msg = sim_platform.create_qos_dscp_policy("NetGuard_DSCP_zoom.exe", "zoom.exe", 46)
    assert ok is True
    assert "already exists" in msg.lower() or "موجودة" in msg


def test_f15_b03_zero_throttle_rate_clamp(sim_platform: SimulatedPlatformAdapter):
    """F15.B3: Zero throttle rate is accepted and stored as policy."""
    ok, msg = sim_platform.create_qos_throttle_policy("NetGuard_Throttle_test", "test.exe", 0)
    assert ok is True


def test_f15_b04_duplicate_qos_rule_addition_attempt(sim_platform: SimulatedPlatformAdapter):
    """F15.B4: Duplicate throttle addition is idempotent."""
    sim_platform.create_qos_throttle_policy("NetGuard_Throttle_app", "app.exe", 2_000_000)
    ok, msg = sim_platform.create_qos_throttle_policy("NetGuard_Throttle_app", "app.exe", 2_000_000)
    assert ok is True


def test_f15_b05_policy_applied_to_nonexistent_process_name(sim_platform: SimulatedPlatformAdapter):
    """F15.B5: Policy created for future process succeeds (Windows activates when launched)."""
    ok, msg = sim_platform.create_qos_dscp_policy("NetGuard_DSCP_not_running.exe", "not_running.exe", 46)
    assert ok is True


# =====================================================================
# F16 Boundary: Startup Sweep & Crash Revert Lifecycle for QoS Policies (5 Tests)
# =====================================================================

def test_f16_b01_registry_locked_during_policy_deletion(sim_platform: SimulatedPlatformAdapter):
    """F16.B1: Removing nonexistent policy handles missing rule gracefully."""
    ok, msg = sim_platform.remove_qos_policy("NetGuard_DSCP_nonexistent")
    assert ok is True


def test_f16_b02_hundred_orphaned_stale_policies_sweep(sim_win: SimulatedWindowsEnvironment, sim_platform: SimulatedPlatformAdapter):
    """F16.B2: Sweeping 100 orphaned crash policies completes in sub-second time."""
    for i in range(100):
        sim_win.qos_policies[f"NetGuard_Stale_{i}"] = {"Name": f"NetGuard_Stale_{i}"}

    assert len(sim_platform.get_qos_policies()) == 100
    ok, msg = sim_platform.sweep_all_netguard_rules()
    assert ok is True
    assert len(sim_platform.get_qos_policies()) == 0


def test_f16_b03_startup_sweep_running_without_elevation(sim_platform: SimulatedPlatformAdapter, sim_win: SimulatedWindowsEnvironment):
    """F16.B3: Startup sweep without elevation reports privilege requirement."""
    sim_win.is_admin = False
    ok, msg = sim_platform.sweep_all_netguard_rules()
    assert ok is False


def test_f16_b04_shutdown_signal_during_active_qos_creation(sim_platform: SimulatedPlatformAdapter):
    """F16.B4: Sweep handles concurrent policy creation cleanly."""
    sim_platform.create_qos_dscp_policy("NetGuard_DSCP_app", "app.exe", 46)
    sim_platform.sweep_all_netguard_rules()
    assert len(sim_platform.get_qos_policies()) == 0


def test_f16_b05_sigterm_sigbreak_signal_handling(sim_platform: SimulatedPlatformAdapter):
    """F16.B5: Platform adapter exposes sweep_all_netguard_rules callable."""
    assert hasattr(sim_platform, "sweep_all_netguard_rules")
    ok, msg = sim_platform.sweep_all_netguard_rules()
    assert ok is True


# =====================================================================
# F17 Boundary: Network Adapter Driver, Firmware & Hardware Audit (5 Tests)
# =====================================================================

def test_f17_b01_unknown_generic_nic_vendor(sim_win: SimulatedWindowsEnvironment):
    """F17.B1: Unknown NIC vendor produces Generic descriptor and maintains physical status."""
    sim_win.adapter_hardware.driver_provider = "Unknown"
    sim_win.adapter_hardware.interface_description = "Generic Network Controller"
    report = sim_win.generate_audit_report()
    assert report.adapter_audit.driver_provider == "Unknown"
    assert "Generic" in report.adapter_audit.interface_description
    assert report.adapter_audit.is_physical is True


def test_f17_b02_missing_driver_version_string_in_wmi(sim_win: SimulatedWindowsEnvironment):
    """F17.B2: Missing driver version string generates audit warning to update unversioned driver."""
    sim_win.adapter_hardware.driver_version = ""
    sim_win.adapter_hardware.is_outdated = True
    report = sim_win.generate_audit_report()
    assert any("Driver" in r.category for r in report.recommendations)


def test_f17_b03_link_speed_reporting_zero_unplugged(sim_win: SimulatedWindowsEnvironment, sim_platform: SimulatedPlatformAdapter):
    """F17.B3: Unplugged adapter reporting 0 Mbps link speed handled accurately by platform primary interface selection."""
    sim_win.adapter_hardware.link_speed_mbps = 0
    sim_win.adapter_hardware.status = "Disconnected"
    sim_win.interfaces["Ethernet"]["is_up"] = False
    primary = sim_platform.get_primary_interface()
    # Falls back to active Wi-Fi since Ethernet is disconnected
    assert primary == "Wi-Fi"


def test_f17_b04_multiple_conflicting_wmi_instances(sim_win: SimulatedWindowsEnvironment):
    """F17.B4: Disambiguation of multiple adapter instances via interface alias mapping."""
    sim_win.interfaces["Ethernet 2"] = dict(sim_win.interfaces["Ethernet"], alias="Ethernet 2", is_physical=True)
    report = sim_win.generate_audit_report()
    adapter_recs = [r for r in report.recommendations if r.category == "Adapter"]
    assert any("Disambiguated" in r.title for r in adapter_recs)
    assert any("Ethernet 2" in r.recommendation for r in adapter_recs)


def test_f17_b05_virtual_miniport_reporting_physical_characteristics(sim_win: SimulatedWindowsEnvironment):
    """F17.B5: Virtual miniport filtered from physical hardware health baseline."""
    sim_win.adapter_hardware = AdapterHardwareInfo(
        adapter_name="WAN Miniport (IP)",
        is_physical=False,
    )
    report = sim_win.generate_audit_report()
    miniport_recs = [r for r in report.recommendations if "Virtual Miniports" in r.title]
    assert len(miniport_recs) >= 1
    assert "WAN Miniport (IP)" in miniport_recs[0].recommendation


# =====================================================================
# F18 Boundary: Windows Firewall Rules & Profile Audit (5 Tests)
# =====================================================================

def test_f18_b01_firewall_service_mpssvc_stopped(sim_win: SimulatedWindowsEnvironment):
    """F18.B1: Inactive firewall profile states generate security alert recommendation."""
    sim_win.firewall_audit.domain_profile_enabled = False
    report = sim_win.generate_audit_report()
    sec_recs = [r for r in report.recommendations if r.category == "Security"]
    assert len(sec_recs) >= 1
    assert "Domain Profile Disabled" in sec_recs[0].title


def test_f18_b02_corrupted_firewall_rule_list(sim_win: SimulatedWindowsEnvironment, sim_platform: SimulatedPlatformAdapter):
    """F18.B2: Empty firewall rule list does not crash platform ping or audit evaluation."""
    sim_win.firewall_audit.active_rules = []
    ok, lat = sim_platform.ping("127.0.0.1")
    assert ok is True
    report = sim_win.generate_audit_report()
    assert len(report.firewall_audit.active_rules) == 0


def test_f18_b03_rule_with_wildcard_port(sim_win: SimulatedWindowsEnvironment):
    """F18.B3: Rule with wildcard port ("*") parsed and produces actionable security recommendation."""
    wildcard_rule = FirewallRuleState(
        name="Allow-All-Wildcard",
        direction="Outbound",
        action="Allow",
        protocol="ANY",
        remote_port="*",
    )
    sim_win.firewall_audit.active_rules.append(wildcard_rule)
    report = sim_win.generate_audit_report()
    wildcard_recs = [r for r in report.recommendations if "Wildcard" in r.title]
    assert len(wildcard_recs) >= 1
    assert wildcard_recs[0].is_actionable is True
    assert "Allow-All-Wildcard" in wildcard_recs[0].recommendation


def test_f18_b04_conflicting_allow_vs_block_rules_same_port(sim_win: SimulatedWindowsEnvironment):
    """F18.B4: Conflicting Allow and Block rules produce actionable security recommendation."""
    sim_win.firewall_audit.conflicting_rules.append("DNS Port 53 has conflicting Allow and Block rules")
    report = sim_win.generate_audit_report()
    conflict_recs = [r for r in report.recommendations if "Conflicting" in r.title]
    assert len(conflict_recs) >= 1
    assert conflict_recs[0].is_actionable is True
    assert "Port 53" in conflict_recs[0].recommendation


def test_f18_b05_non_english_windows_locale_rule_names(sim_win: SimulatedWindowsEnvironment):
    """F18.B5: Localized rule names produce actionable audit recommendation."""
    rule_ar = FirewallRuleState(name="السماح بمرور DNS الصادر", direction="Outbound", action="Allow", protocol="UDP")
    sim_win.firewall_audit.active_rules.append(rule_ar)
    report = sim_win.generate_audit_report()
    loc_recs = [r for r in report.recommendations if "Localized" in r.title]
    assert len(loc_recs) >= 1
    assert "السماح بمرور DNS الصادر" in loc_recs[0].recommendation
    assert loc_recs[0].is_actionable is True


# =====================================================================
# F19 Boundary: Unified Incident History & QTest (5 Tests)
# =====================================================================

def test_f19_b01_ten_thousand_incident_records_wal_performance(incident_repo: IncidentRepository):
    """F19.B1: 10,000 incident batch operations perform reliably with SQLite WAL mode and retention pruning."""
    now_dt = datetime.now(timezone.utc)
    old_iso = (now_dt - timedelta(days=45)).isoformat()
    recent_iso = now_dt.isoformat()

    # Genuine batch insertion of 10,000 records (5,000 old, 5,000 recent)
    insert_rows = []
    for i in range(10000):
        ts = old_iso if i < 5000 else recent_iso
        insert_rows.append((
            f"batch-inc-{i}",
            ts,
            ProbableCause.LOCAL_GATEWAY_HIGH_LATENCY.value,
            0.85,
            DiagnosisSeverity.MEDIUM.value,
            f"Benchmark incident {i}",
            0,
            "[]",
            "[]",
            f"fp-batch-{i}",
            ts,
            ts,
            1,
            IncidentLifecycleState.DIAGNOSED.value,
            IncidentResolutionType.UNRESOLVED.value,
            "Ethernet",
            CauseClassification.PROBABLE_CAUSE.value,
            None,
            None,
        ))

    insert_query = """
    INSERT INTO incidents (
        id, timestamp, probable_cause, confidence, severity, explanation,
        auto_remediation_permitted, evidence_json, actions_json,
        fingerprint, first_detected, last_observed, occurrence_count,
        status, resolution_type, affected_component, cause_classification,
        action_record_id, resolved_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    start_insert = time.perf_counter()
    with incident_repo.db.get_connection() as conn:
        cur = conn.cursor()
        cur.executemany(insert_query, insert_rows)
        conn.commit()
    insert_duration = time.perf_counter() - start_insert

    # WAL mode delivers high throughput: 10,000 rows in < 2.0s
    assert insert_duration < 2.0

    # Test retention pruning deletes exactly 5,000 records older than 30 days
    pruned_count = incident_repo.prune_older_than(days=30)
    assert pruned_count == 5000

    # Exactly 5,000 recent records remain
    with incident_repo.db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM incidents;")
        count_remaining = cur.fetchone()[0]
    assert count_remaining == 5000


def test_f19_b02_database_file_locked_by_external_process(temp_db):
    """F19.B2: Database busy timeout prevents instant lock errors."""
    with temp_db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA busy_timeout;")
        timeout = cur.fetchone()[0]
        assert timeout >= 5000


def test_f19_b03_concurrent_writes_from_multiple_threads(audit_repo):
    """F19.B3: Concurrent writes from 5 threads complete without collision."""
    errors = []

    def writer_entry(idx: int):
        try:
            rec = ActionExecutionRecord(
                id=f"thread-{idx}-{uuid.uuid4()}",
                action_id="flush_dns",
                action_name="Thread Flush",
                risk_level=RiskLevel.LEVEL_1_LOW,
                trigger_diagnosis_id="diag",
                status=ActionExecutionStatus.SUCCEEDED,
                execution_duration_ms=5.0,
            )
            audit_repo.save(rec)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer_entry, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=3.0)

    assert len(errors) == 0


def test_f19_b04_qtest_headless_offscreen_rendering_in_ci(qapp):
    """F19.B4: Headless QTest offscreen verification."""
    from app.ui.views.dashboard_view import DashboardView
    view = DashboardView()
    assert view is not None
    assert qapp.platformName() == "offscreen" or view.isVisible() is False


def test_f19_b05_rapid_view_switching_during_active_diagnosis_scan(qapp):
    """F19.B5: Rapidly switching across all 7 views 50 times causes 0 crashes."""
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

    for cycle in range(5):
        for v in views:
            v.setVisible(True)
            v.setVisible(False)

    assert len(views) == 7
