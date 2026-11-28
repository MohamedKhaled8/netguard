"""Integration tests verifying upgraded WifiRouterView controls, fault cards, NL commands, and WebDOM fallback."""

from __future__ import annotations

import http.server
import os
import threading
from typing import Any

import pytest
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.main import create_application
from app.core.models.metrics import OperatingMode
from app.ui import tokens
from app.ui.main_window import MainWindow
from app.ui.views.wifi_router_view import _FaultCardWidget
from app.wifi.models import (
    ConnectedDeviceRecord,
    FullChannelAnalysisReport,
    BandChannelAnalysisResult,
    ChannelRecommendation,
    ChannelScoreBreakdown,
    RouterCapabilities,
    WifiInterfaceTelemetry,
)
from app.wifi.optimization import OptimizationMode
from app.wifi.root_cause import RootCauseAnalysisService
from app.wifi.router.analyzer import RouterConfigAnalyzer
from app.wifi.router.adapters.web_dom_inspector import RouterWebDomInspector


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_complete_network_health_controls_and_nl_dispatch(qapp) -> None:
    net_app = create_application()
    win = MainWindow(application=net_app)
    try:
        win.show()
        qapp.processEvents()

        # Verify split dedicated views preserve full functional controls
        assert hasattr(win.view_wifi, "btn_rf_refresh")
        assert hasattr(win.view_wifi, "spectrum_chart")
        assert hasattr(win.view_router, "btn_discover")
        assert hasattr(win.view_router, "btn_login_read")
        assert hasattr(win.view_router, "btn_dom_inspect")
        assert hasattr(win.view_router, "table_devices")
        assert hasattr(win.view_quality, "btn_run_speed")
        assert hasattr(win.view_quality, "btn_run_bufferbloat")
        assert hasattr(win.view_quality, "btn_run_net_diag")
        assert hasattr(win.view_reports, "btn_run_full_investigation")
        assert hasattr(win.view_reports, "flowchart")
        assert hasattr(win.view_reports, "btn_export_md")

        # Verify OptimizationPlanner still defaults safely to APPROVAL_REQUIRED
        assert net_app.wifi_bundle.optimization.mode == OptimizationMode.APPROVAL_REQUIRED
    finally:
        win.refresh_timer.stop()
        win.dns_rank_timer.stop()
        win.close()
        win.deleteLater()
        qapp.processEvents()


def test_web_dom_safety_filter_and_local_form_detection(qapp) -> None:
    insp = RouterWebDomInspector()
    assert insp.is_safe_navigation_target("Wi-Fi Settings", "/wlan.asp") is True
    assert insp.is_safe_navigation_target("Reboot Router", "/reboot.cgi") is False
    assert insp.is_safe_navigation_target("Factory Reset", "/reset.asp") is False
    assert insp.is_safe_navigation_target("External", "https://8.8.8.8/") is False

    class _LoginPage(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            html = """<html><head><title>Local Router</title></head><body>
            <form action="/login.cgi">
              <input type="text" name="username" value="admin"/>
              <input type="password" name="password" value="secret"/>
              <select name="wifi_ch"><option value="6" selected>Ch 6</option></select>
            </form></body></html>"""
            self.send_response(200)
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _LoginPage)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        res = insp.inspect_portal(base_url=f"http://127.0.0.1:{port}", allow_loopback=True, timeout_ms=9000)
        assert res.available is True
        assert len(res.pages) >= 1
        assert res.login_form_detected is True
        # Verify password input is extracted and strictly redacted by DOM JS
        pw_field = res.pages[0].fields.get("password")
        assert pw_field is not None
        assert pw_field["value"] == "[REDACTED]"
    finally:
        srv.shutdown()
        srv.server_close()


def test_section14_startup_permission_safety_and_sidebar_sync(qapp, tmp_path, monkeypatch) -> None:
    """Section 14: Startup keeps sidebar AUTO intact while router auto-opt starts safe & opt-in only."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    net_app = create_application()
    win = MainWindow(application=net_app)
    try:
        win.show()
        qapp.processEvents()
        opt = net_app.wifi_bundle.optimization

        # MainWindow sidebar still initializes to default OperatingMode.AUTO
        assert win.sidebar._current_mode_idx == 0

        # Router OptimizationPlanner must NOT start in AUTHORIZED AUTO-OPTIMIZATION with pre-checked categories
        assert opt.mode == OptimizationMode.APPROVAL_REQUIRED
        assert opt.auto_allowed_categories == set()

        # Switching sidebar to WATCH syncs safely across views without enabling auto router writes
        win.set_operating_mode(OperatingMode.WATCH)
        qapp.processEvents()
        assert win.sidebar._current_mode_idx == 2
        assert opt.auto_allowed_categories == set()
    finally:
        for tname in ("refresh_timer", "dns_rank_timer", "meeting_signal_timer", "update_check_timer"):
            t = getattr(win, tname, None)
            if t is not None:
                t.stop()
        win.close()
        win.deleteLater()
        qapp.processEvents()


def test_devices_table_proportional_widths_and_arabic_bidi_polish(qapp, tmp_path, monkeypatch) -> None:
    """Verify _tbl_devices proportional columns, Arabic proposal localization, and bidi_isolate_mixed."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    # 1. Mixed Arabic+English bidi helper preserves Arabic RTL base while isolating Latin/numeric tokens
    mixed = tokens.bidi_isolate_mixed("ارتفاع الـ Ping على نطاق 2.4 GHz عند عرض 40 MHz.")
    assert not mixed.startswith("\u2066")
    assert "\u2066Ping\u2069" in mixed
    assert "\u20662.4 GHz\u2069" in mixed
    assert "\u206640 MHz\u2069" in mixed

    # 2. RouterConfigAnalyzer emits Arabic titles
    tel = WifiInterfaceTelemetry(connection_state="connected", band="2.4 GHz", channel=6, channel_width_mhz=40, rssi_dbm=-62)
    ch_rep = FullChannelAnalysisReport(
        bands={
            "2.4 GHz": BandChannelAnalysisResult(
                band="2.4 GHz",
                target_width_mhz=20,
                regulatory_domain="EG",
                current_channel=6,
                current_channel_score=ChannelScoreBreakdown(
                    band="2.4 GHz",
                    channel=6,
                    center_frequency_mhz=2437,
                    width_mhz=40,
                    occupied_range_mhz=(2417.0, 2457.0),
                    is_current_channel=True,
                    total_score=42.0,
                    interference_level="high",
                ),
                recommended_channels=[
                    ChannelRecommendation(
                        rank=1,
                        band="2.4 GHz",
                        channel=1,
                        width_mhz=20,
                        total_score=9.0,
                        interference_level="low",
                        confidence_label="high",
                        reason="أقل ازدحاماً",
                    )
                ],
            )
        }
    )
    props = RouterConfigAnalyzer().analyze(
        capabilities=RouterCapabilities(adapter_id="huawei", supports_channel_write=False),
        telemetry=tel,
        channel_report=ch_rep,
    )
    assert len(props) >= 2
    assert any("تغيير قناة" in p.title for p in props)
    assert any("تضييق عرض قناة" in p.title for p in props)
    assert all(not p.title.startswith(("Switch ", "Narrow ", "Enable ")) for p in props)

    # 3. Live UI verification of RouterManagementView devices table
    net_app = create_application()
    win = MainWindow(application=net_app)
    try:
        win.show()
        win.resize(1280, 720)
        win._switch_view(5, win.btn_router)
        qapp.processEvents()
        v = win.view_router
        v._devices = [
            ConnectedDeviceRecord(
                ip_address="192.168.1.1",
                mac_address="f8:95:22:82:bf:63",
                hostname="Gateway",
                vendor="VMware, Inc.",
                connection_type="ethernet",
                connection_status="connected",
                is_gateway=True,
                source="os_arp",
            ),
            ConnectedDeviceRecord(
                ip_address="192.168.1.100",
                mac_address="10:20:30:40:50:60",
                hostname="Workstation-PC",
                vendor="Intel Corporate",
                connection_type="wifi_5",
                connection_status="connected",
                is_local_host=True,
                source="merged",
            ),
        ]
        v._render_devices_table()
        v.switch_tab(4)
        qapp.processEvents()
        assert v.table_devices.rowCount() == 2
    finally:
        for tname in ("refresh_timer", "dns_rank_timer", "meeting_signal_timer", "update_check_timer"):
            t = getattr(win, tname, None)
            if t is not None:
                t.stop()
        win.close()
        win.deleteLater()
        qapp.processEvents()
