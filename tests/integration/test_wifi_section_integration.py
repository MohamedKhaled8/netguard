"""Integration tests for WifiRouterView navigation, SQLite persistence, and live Windows read-only probes."""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.core.events.bus import EventBus
from app.storage.database import DatabaseManager
from app.ui.main_window import MainWindow
from app.wifi.models import BeforeAfterSnapshot
from app.wifi.reporting import BeforeAfterReportingService


@pytest.fixture(scope="module")
def _qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_mainwindow_mounts_wifi_router_and_all_10_sections(_qapp) -> None:
    app_mock = MagicMock()
    app_mock.traffic_controller = None
    app_mock.orchestrator = None
    app_mock.ctx = MagicMock()
    app_mock.ctx.platform = None
    app_mock.ctx.db = None
    app_mock.ctx.measurements = None
    app_mock.ctx.incidents = None
    app_mock.ctx.event_bus = EventBus()
    app_mock.settings = None

    win = MainWindow(app_mock)
    assert win.stack.count() == 10

    win.btn_wifi.click()
    assert win.stack.currentWidget() is win.view_wifi

    win.btn_router.click()
    assert win.stack.currentWidget() is win.view_router
    for sub_idx in range(7):
        win.view_router.switch_tab(sub_idx)
        assert win.view_router.tab_stack.currentIndex() == sub_idx

    win.btn_quality.click()
    assert win.stack.currentWidget() is win.view_quality

    win.btn_reports.click()
    assert win.stack.currentWidget() is win.view_reports

    win.btn_about.click()
    assert win.stack.currentWidget() is win.view_about
    win.close()


def test_sqlite_wifi_snapshot_persistence(tmp_path) -> None:
    db = DatabaseManager(db_path=str(tmp_path / "wifi_test.db"))
    svc = BeforeAfterReportingService(db_manager=db)
    snap = BeforeAfterSnapshot(
        snapshot_id="snap_1",
        label="Baseline",
        ssid="Office",
        band="5 GHz",
        channel=44,
        gateway_avg_ms=4.5,
    )
    svc.save_snapshot(snap)
    loaded = svc.list_snapshots()
    assert len(loaded) == 1
    assert loaded[0].snapshot_id == "snap_1"
    assert loaded[0].channel == 44
    db.get_connection().close()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only live adapter smoke check")
@pytest.mark.asyncio
async def test_live_windows_readonly_wifi_and_arp_smoke() -> None:
    from app.application import create_application

    net_app = create_application()
    b = net_app.wifi_bundle
    tel = await b.telemetry.collect_telemetry(
        include_events=True, include_ps_driver_stats=True, trigger_active_scan=False
    )
    # Must never fabricate noise/SNR/MCS regardless of whether Wi-Fi is currently associated
    assert tel.noise_floor_dbm is None
    assert tel.snr_db is None
    assert tel.mcs_index is None

    scan = await b.scanner.scan(request_active_scan=False)
    ch = b.channel_analyzer.analyze(
        scan_result=scan,
        current_band=tel.band,
        current_channel=tel.channel,
        connected_bssid=tel.bssid,
        adapter_caps=tel.capabilities,
    )
    disc = await b.router_discovery.discover()
    devs, rlimit_ok, _ = await b.device_manager.list_connected_devices(gateway_ip=disc.gateway_ip)
    assert disc.capabilities.hardware_verified is False
    assert isinstance(devs, list)
    assert rlimit_ok is False
    assert b.recommender.analyze(telemetry=tel, scan_result=scan, channel_report=ch) is not None
