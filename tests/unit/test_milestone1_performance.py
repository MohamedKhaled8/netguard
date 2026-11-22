"""Comprehensive Unit Tests for Milestone 1: Performance, Win32 Native APIs & Threading."""

import asyncio
import os
import time
import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication

from app.platform.windows.adapter import (
    WindowsPlatformAdapter,
    WifiMetrics,
    PingResult,
)
from app.ui.animation_clock import AnimationMasterClock
from app.ui import tokens
from app.traffic.controller import TrafficController
from app.core.events.bus import EventBus
from app.application import create_application
from app.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# =====================================================================
# F1: Native Win32 ICMP In-Process Pinging Tests
# =====================================================================

def test_ping_result_interface_contracts():
    """Verify PingResult behaves as a 2-tuple, float, and boolean."""
    res_ok = PingResult(True, 15.4)
    assert res_ok.success is True
    assert res_ok.latency_ms == 15.4
    assert bool(res_ok) is True
    assert float(res_ok) == 15.4
    assert int(res_ok) == 15
    assert res_ok > 10.0
    assert res_ok >= 15.4
    assert res_ok < 20.0
    assert res_ok <= 15.4
    assert round(res_ok, 1) == 15.4

    # Tuple unpacking
    ok, lat = res_ok
    assert ok is True
    assert lat == 15.4

    res_fail = PingResult(False, 0.0)
    assert res_fail.success is False
    assert res_fail.latency_ms == 0.0
    assert bool(res_fail) is False
    ok_f, lat_f = res_fail
    assert ok_f is False
    assert lat_f == 0.0


def test_windows_adapter_native_icmp_live():
    """Verify WindowsPlatformAdapter.ping uses in-process Win32 API without ping.exe."""
    adapter = WindowsPlatformAdapter()

    # Ping localhost
    res = adapter.ping("127.0.0.1", timeout_sec=1.0)
    assert isinstance(res, PingResult)
    assert res.success is True
    assert res.latency_ms >= 0.0

    # Ping invalid host returns failure without crashing
    res_inv = adapter.ping("invalid.hostname.unresolvable.local", timeout_sec=0.5)
    assert res_inv.success is False
    assert res_inv.latency_ms == 0.0


def test_zero_ping_subprocess_in_adapter():
    """Forensic verification: WindowsPlatformAdapter must not spawn ping.exe."""
    adapter = WindowsPlatformAdapter()
    with patch("subprocess.run") as mock_run:
        adapter.ping("127.0.0.1", timeout_sec=0.8)
        # Ensure subprocess.run was never called with "ping"
        for call_args in mock_run.call_args_list:
            cmd = call_args[0][0]
            assert "ping" not in cmd


# =====================================================================
# F2: Native Win32 WLAN API Metrics Tests
# =====================================================================

def test_wifi_metrics_hybrid_interface():
    """Verify WifiMetrics supports dict operations and object attribute access."""
    metrics = WifiMetrics(
        is_wifi=True,
        ssid="Office_WLAN",
        signal_quality=85.0,
        link_speed_mbps=300.0,
        rx_rate_mbps=150.0,
        tx_rate_mbps=300.0,
        bssid="12:34:56:78:9a:bc",
    )

    # Object attribute access
    assert metrics.is_wifi is True
    assert metrics.ssid == "Office_WLAN"
    assert metrics.signal_quality == 85.0
    assert metrics.signal_percent == 85.0
    assert metrics.link_speed_mbps == 300.0
    assert metrics.rx_rate_mbps == 150.0
    assert metrics.tx_rate_mbps == 300.0
    assert metrics.bssid == "12:34:56:78:9a:bc"

    # Dict item and get access
    assert metrics["is_wifi"] is True
    assert metrics["ssid"] == "Office_WLAN"
    assert metrics.get("signal_percent") == 85.0
    assert "link_speed_mbps" in metrics

    # Disconnected state
    disconnected = WifiMetrics(is_wifi=False)
    assert disconnected.is_wifi is False
    assert disconnected["is_wifi"] is False


def test_windows_adapter_wifi_metrics_query():
    """Verify WindowsPlatformAdapter.get_wifi_metrics queries native WLAN API without netsh.exe."""
    adapter = WindowsPlatformAdapter()

    with patch("subprocess.run") as mock_run:
        metrics = adapter.get_wifi_metrics()
        # Verify return type contract
        assert isinstance(metrics, WifiMetrics)
        assert isinstance(metrics, dict)
        assert "is_wifi" in metrics

        # Ensure netsh wlan show interfaces was never spawned
        for call_args in mock_run.call_args_list:
            cmd = call_args[0][0]
            if isinstance(cmd, list):
                assert not (len(cmd) >= 2 and cmd[0] == "netsh" and cmd[1] == "wlan")


# =====================================================================
# F3: Concurrency & Event Loop Harmonization Tests
# =====================================================================

def test_main_window_centralized_event_loop(qapp):
    """Verify MainWindow dispatches async coroutines safely to its centralized loop."""
    net_app = create_application()
    win = MainWindow(application=net_app)

    loop = win.async_loop
    assert loop is not None
    assert loop.is_running()

    # Dispatch a background coroutine
    done_payload = []

    async def _sample_coro():
        await asyncio.sleep(0.01)
        return "loop_harmonized_success"

    def _on_done(future):
        done_payload.append(future.result())

    fut = win.dispatch_coroutine(_sample_coro(), on_done=_on_done)
    res = fut.result(timeout=2.0)
    assert res == "loop_harmonized_success"

    win.close()


# =====================================================================
# F4: Qt Animation Master Clock & Low-Resource Mode Tests
# =====================================================================

def test_animation_master_clock_singleton_and_throttling(qapp):
    """Verify AnimationMasterClock manages subscribers and toggles low-resource mode."""
    clock = AnimationMasterClock.get_instance()
    assert clock is not None
    if tokens.ANIMATIONS_ENABLED and not clock.is_running:
        clock.start()
    assert clock.is_running or not tokens.ANIMATIONS_ENABLED

    ticks_received = []

    def _subscriber(dt: float):
        ticks_received.append(dt)

    clock.subscribe(_subscriber)
    assert _subscriber in clock._subscribers

    # Test framerate adjustment
    clock.set_fps(25)
    assert clock._target_fps == 25
    assert clock._interval_ms == 40

    # Test low-resource mode auto-throttling
    mode_events = []
    clock.mode_changed.connect(lambda mode: mode_events.append(mode))

    clock.set_low_resource_mode(True)
    assert clock.is_low_resource_mode is True
    assert mode_events[-1] is True
    assert clock._timer.interval() == 100  # 10 FPS during low resource mode

    clock.set_low_resource_mode(False)
    assert clock.is_low_resource_mode is False
    assert mode_events[-1] is False
    assert clock._timer.interval() == 40  # Restored

    clock.unsubscribe(_subscriber)
    assert _subscriber not in clock._subscribers


# =====================================================================
# F5: Socket Enumeration PID Caching Tests
# =====================================================================

def test_traffic_controller_pid_caching():
    """Verify TrafficController caches PID to process name mappings with TTL."""
    bus = EventBus()
    controller = TrafficController(event_bus=bus)

    assert hasattr(controller, "_pid_name_cache")
    assert isinstance(controller._pid_name_cache, dict)

    curr_pid = os.getpid()
    t0 = time.perf_counter()

    # First lookup: cache miss, queries psutil and populates cache
    name1 = controller._resolve_process_name(curr_pid, t0)
    assert name1 is not None
    assert curr_pid in controller._pid_name_cache
    assert controller._pid_name_cache[curr_pid][0] == name1

    # Second lookup: cache hit (should return same name without re-querying psutil)
    with patch("psutil.Process") as mock_proc:
        name2 = controller._resolve_process_name(curr_pid, t0 + 5.0)
        assert name2 == name1
        mock_proc.assert_not_called()

    # Lookup after TTL expiration: should re-query psutil
    with patch("psutil.Process") as mock_proc:
        mock_instance = MagicMock()
        mock_instance.name.return_value = "refreshed_process.exe"
        mock_proc.return_value = mock_instance

        name3 = controller._resolve_process_name(curr_pid, t0 + controller._pid_cache_ttl_sec + 1.0)
        assert name3 == "refreshed_process.exe"
        mock_proc.assert_called_once_with(curr_pid)

    # Cache pruning: test expired entries are evicted
    fake_pid = 99999999
    controller._pid_name_cache[fake_pid] = ("dead.exe", t0 - 100.0)
    controller._prune_pid_cache(t0)
    assert fake_pid not in controller._pid_name_cache
