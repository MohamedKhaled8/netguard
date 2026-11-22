"""Comprehensive tests for NetGuard Production Hardening, Meeting Shield & 4-Case Fault Attribution."""

import pytest
import math
from datetime import datetime, timezone
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication, QHeaderView, QLabel
from PySide6.QtCore import Qt

from app.ui import tokens
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.traffic_view import TrafficView
from app.ui.views.dns_view import DNSView
from app.ui.widgets.multi_protocol_panel import MultiProtocolAnalysisPanel
from app.traffic.meeting_detector import MeetingDetector, MeetingShield
from app.traffic.session_tracker import AppSessionTracker
from app.core.models.metrics import MetricType, Measurement, ProbeStatus, MeasurementSource


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app


def test_part1_jitter_arabic_labels_and_thresholds(qapp):
    """Verify Jitter thresholds & Arabic labels accurately match release specifications."""
    view = DashboardView()
    obs = MagicMock()

    now = datetime.now(timezone.utc)
    # 1. < 10 ms (e.g. 0.1 ms & 2.6 ms) -> "ممتاز • مثالي للمكالمات" (green, is_warning=False)
    for sample_val in (0.1, 2.6, 9.9):
        jit_meas = Measurement(
            timestamp=now,
            source=MeasurementSource.ICMP_ECHO,
            target_or_interface="8.8.8.8",
            metric_type=MetricType.JITTER_MS,
            raw_value=sample_val,
            normalized_value=sample_val,
            unit="ms",
            status=ProbeStatus.SUCCESS,
        )
        obs.get_latest_measurement.side_effect = lambda mt: jit_meas if mt == MetricType.JITTER_MS else None
        obs.get_sliding_window.return_value = [jit_meas]
        view.update_telemetry(obs, None)
        assert view.metrics_strip.cell_jitter.footer_lbl.text() == "ممتاز • مثالي للمكالمات"
        assert view.metrics_strip.cell_jitter.dot.styleSheet() == f"background-color: {tokens.STATUS_OK}; border-radius: 3.5px;"

    # 2. 10 ms - 29.9 ms -> "جيد • مناسب للمكالمات" (green, is_warning=False)
    for sample_val in (10.0, 18.5, 29.9):
        jit_meas = Measurement(
            timestamp=now,
            source=MeasurementSource.ICMP_ECHO,
            target_or_interface="8.8.8.8",
            metric_type=MetricType.JITTER_MS,
            raw_value=sample_val,
            normalized_value=sample_val,
            unit="ms",
            status=ProbeStatus.SUCCESS,
        )
        obs.get_latest_measurement.side_effect = lambda mt: jit_meas if mt == MetricType.JITTER_MS else None
        obs.get_sliding_window.return_value = [jit_meas]
        view.update_telemetry(obs, None)
        assert view.metrics_strip.cell_jitter.footer_lbl.text() == "جيد • مناسب للمكالمات"
        assert view.metrics_strip.cell_jitter.dot.styleSheet() == f"background-color: {tokens.STATUS_OK}; border-radius: 3.5px;"

    # 3. 30 ms - 50 ms -> "متوسط • قد يؤثر على المكالمات" (amber/warning)
    for sample_val in (30.0, 42.0, 50.0):
        jit_meas = Measurement(
            timestamp=now,
            source=MeasurementSource.ICMP_ECHO,
            target_or_interface="8.8.8.8",
            metric_type=MetricType.JITTER_MS,
            raw_value=sample_val,
            normalized_value=sample_val,
            unit="ms",
            status=ProbeStatus.SUCCESS,
        )
        obs.get_latest_measurement.side_effect = lambda mt: jit_meas if mt == MetricType.JITTER_MS else None
        obs.get_sliding_window.return_value = [jit_meas]
        view.update_telemetry(obs, None)
        assert view.metrics_strip.cell_jitter.footer_lbl.text() == "متوسط • قد يؤثر على المكالمات"
        assert view.metrics_strip.cell_jitter.dot.styleSheet() == f"background-color: {tokens.STATUS_WARN}; border-radius: 3.5px;"

    # 4. > 50 ms -> "مرتفع • يؤثر بشدة على المكالمات" (red/critical)
    for sample_val in (50.1, 75.0, 120.0):
        jit_meas = Measurement(
            timestamp=now,
            source=MeasurementSource.ICMP_ECHO,
            target_or_interface="8.8.8.8",
            metric_type=MetricType.JITTER_MS,
            raw_value=sample_val,
            normalized_value=sample_val,
            unit="ms",
            status=ProbeStatus.SUCCESS,
        )
        obs.get_latest_measurement.side_effect = lambda mt: jit_meas if mt == MetricType.JITTER_MS else None
        obs.get_sliding_window.return_value = [jit_meas]
        view.update_telemetry(obs, None)
        assert view.metrics_strip.cell_jitter.footer_lbl.text() == "مرتفع • يؤثر بشدة على المكالمات"
        assert view.metrics_strip.cell_jitter.dot.styleSheet() == f"background-color: {tokens.STATUS_BAD}; border-radius: 3.5px;"


def test_part1_qos_table_resize_modes_and_meeting_priority(qapp):
    """Verify QoS table columns use clean resize modes and protect meeting apps."""
    tv = TrafficView()

    # Column resize modes
    hdr = tv.table.horizontalHeader()
    assert hdr.sectionResizeMode(0) == QHeaderView.Stretch  # Process Name
    assert hdr.sectionResizeMode(1) == QHeaderView.ResizeToContents  # PID
    assert hdr.sectionResizeMode(2) == QHeaderView.ResizeToContents  # Status
    assert hdr.sectionResizeMode(3) == QHeaderView.ResizeToContents  # Active Count
    assert hdr.sectionResizeMode(4) == QHeaderView.Stretch  # QoS Status
    assert hdr.sectionResizeMode(5) == QHeaderView.ResizeToContents  # QoS Action

    # Populate dummy processes including Zoom, OBS, and a regular app
    class DummyProc:
        def __init__(self, name, pid, sockets, mbps, cat):
            self.name = name
            self.pid = pid
            self.active_socket_count = sockets
            self.estimated_bandwidth_mbps = mbps
            self.category = cat
            self.is_protected_system_process = False

    procs = [
        DummyProc("zoom.exe", 1001, 15, 3.2, "conferencing"),
        DummyProc("obs64.exe", 1002, 8, 4.5, "streaming"),
        DummyProc("chrome.exe", 1003, 20, 0.5, "interactive"),
    ]

    tv.update_profiles(procs)
    assert tv.table.rowCount() == 3

    # Zoom and OBS must have "أولوية قصوى (اجتماع/تسجيل)"
    item_tag_0 = tv.table.cellWidget(0, 2).findChild(QLabel).text()
    assert "أولوية قصوى" in item_tag_0

    # In Col 5, meeting/recording app must show protected and NEVER a throttle button
    widget_col5_0 = tv.table.cellWidget(0, 5)
    assert "محمي" in widget_col5_0.text()


def test_part1_multi_protocol_panel_clean_arabic_title(qapp):
    """Verify MultiProtocolAnalysisPanel has clean Arabic title and Bidi isolated subtitle."""
    panel = MultiProtocolAnalysisPanel()
    assert panel.lbl_title.text() == "تحليل الاتصال متعدد البروتوكولات"
    assert "\u2066ICMP\u2069" in panel.lbl_subtitle.text()
    assert "\u2066TCP (443)\u2069" in panel.lbl_subtitle.text()
    assert "\u2066UDP\u2069" in panel.lbl_subtitle.text()


def test_part1_dns_view_table_elision_and_bidi(qapp):
    """Verify DNS benchmark table disables elision and isolates text."""
    dv = DNSView()
    assert dv.table.textElideMode() == Qt.ElideNone
    assert dv.table.columnWidth(2) >= 140
    assert dv.table.columnWidth(3) >= 140
    assert dv.table.columnWidth(4) >= 160


def test_part2_meeting_shield_4_case_fault_attribution():
    """Verify 4-Case Fault Attribution accurately identifies VPN, Hog, Gateway, and ISP."""
    shield = MeetingShield()

    class DummyProc:
        def __init__(self, name, mbps):
            self.name = name
            self.estimated_bandwidth_mbps = mbps
            self.is_protected_system_process = False

    # Case A: Active VPN Interference
    procs_vpn = [
        DummyProc("zoom.exe", 3.0),
        DummyProc("urban-vpn-service.exe", 0.2),
    ]
    alert_a = shield.evaluate_telemetry(
        is_meeting_active=True,
        meeting_app_name="Zoom Cloud Meetings",
        meeting_process_name="zoom.exe",
        wan_latency_ms=130.0,
        active_processes=procs_vpn,
        force_ignore_cooldown=True,
    )
    assert alert_a is not None
    assert alert_a["case"] == "A"
    assert "VPN" in alert_a["message"]
    assert "urban-vpn-service.exe" in alert_a["message"]

    # Case B: Local Bandwidth Hog
    shield.reset_cooldown()
    procs_hog = [
        DummyProc("zoom.exe", 3.0),
        DummyProc("steam.exe", 12.5),
    ]
    alert_b = shield.evaluate_telemetry(
        is_meeting_active=True,
        meeting_app_name="Zoom Cloud Meetings",
        meeting_process_name="zoom.exe",
        wan_latency_ms=135.0,
        active_processes=procs_hog,
        force_ignore_cooldown=True,
    )
    assert alert_b is not None
    assert alert_b["case"] == "B"
    assert "steam.exe" in alert_b["message"]
    assert "يستهلك سرعة الإنترنت" in alert_b["message"]

    # Case C: User's Wi-Fi / Router (Gateway loss or high latency)
    shield.reset_cooldown()
    alert_c = shield.evaluate_telemetry(
        is_meeting_active=True,
        meeting_app_name="Zoom Cloud Meetings",
        meeting_process_name="zoom.exe",
        gateway_latency_ms=35.0,
        gateway_loss_ratio=0.1,
        wan_latency_ms=140.0,
        force_ignore_cooldown=True,
    )
    assert alert_c is not None
    assert alert_c["case"] == "C"
    assert "الواي فاي أو الراوتر" in alert_c["message"]

    # Case D: User's ISP / WAN degradation (Gateway is clean <10ms, but WAN is degraded)
    shield.reset_cooldown()
    alert_d = shield.evaluate_telemetry(
        is_meeting_active=True,
        meeting_app_name="Zoom Cloud Meetings",
        meeting_process_name="zoom.exe",
        gateway_latency_ms=2.1,
        gateway_loss_ratio=0.0,
        wan_latency_ms=145.0,
        wan_loss_ratio=0.05,
        jitter_ms=30.0,
        force_ignore_cooldown=True,
    )
    assert alert_d is not None
    assert alert_d["case"] == "D"
    assert "مزود الخدمة" in alert_d["message"]
    assert "التطبيق والنظام يعملان بشكل سليم" in alert_d["message"]


def test_part2_meeting_shield_rate_limit_cooldown():
    """Verify MeetingShield suppresses spam and honors 60s cooldown."""
    shield = MeetingShield()
    shield.COOLDOWN_SECONDS = 60.0

    # First trigger emits alert
    alert1 = shield.evaluate_telemetry(
        is_meeting_active=True,
        meeting_app_name="Zoom",
        meeting_process_name="zoom.exe",
        gateway_latency_ms=2.0,
        wan_latency_ms=150.0,
        force_ignore_cooldown=False,
    )
    assert alert1 is not None

    # Immediate second call within 60s returns None (suppressed)
    alert2 = shield.evaluate_telemetry(
        is_meeting_active=True,
        meeting_app_name="Zoom",
        meeting_process_name="zoom.exe",
        gateway_latency_ms=2.0,
        wan_latency_ms=155.0,
        force_ignore_cooldown=False,
    )
    assert alert2 is None


def test_part3_packet_loss_climb_on_probe_timeout(qapp):
    """Verify displayed packet loss climbs from 0.0% up to 100.0% on timeouts/disconnects."""
    view = DashboardView()
    obs = MagicMock()

    now = datetime.now(timezone.utc)
    # 1. Healthy: 0.0% loss
    loss_meas_0 = Measurement(
        timestamp=now,
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="8.8.8.8",
        metric_type=MetricType.EXTERNAL_PACKET_LOSS,
        raw_value=0.0,
        normalized_value=0.0,
        unit="ratio",
        status=ProbeStatus.SUCCESS,
    )
    obs.get_latest_measurement.side_effect = lambda mt: loss_meas_0 if mt in (MetricType.EXTERNAL_PACKET_LOSS, MetricType.GATEWAY_PACKET_LOSS) else None
    obs.get_sliding_window.return_value = [loss_meas_0] * 10
    view.update_telemetry(obs, None)
    assert view.metrics_strip.cell_loss.val_lbl.text() == "0.0"
    assert view.metrics_strip.cell_loss.footer_lbl.text() == "ممتاز · لا حزم ضائعة"

    # 2. Timeout/Failure: 100.0% loss
    loss_meas_100 = Measurement(
        timestamp=now,
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="8.8.8.8",
        metric_type=MetricType.EXTERNAL_PACKET_LOSS,
        raw_value=1.0,
        normalized_value=1.0,
        unit="ratio",
        status=ProbeStatus.FAILED,
    )
    obs.get_latest_measurement.side_effect = lambda mt: loss_meas_100 if mt in (MetricType.EXTERNAL_PACKET_LOSS, MetricType.GATEWAY_PACKET_LOSS) else None
    obs.get_sliding_window.return_value = [loss_meas_100] * 10
    view.update_telemetry(obs, None)
    assert view.metrics_strip.cell_loss.val_lbl.text() == "100.0"
    assert view.metrics_strip.cell_loss.footer_lbl.text() == "انقطاع كامل في الحزم"


def test_part4_build_excludes_tools_module():
    """Verify NetGuard.spec and scripts/build_exe.py exclude tools/publish_update.py."""
    from pathlib import Path
    spec_path = Path("NetGuard.spec")
    assert spec_path.exists()
    spec_content = spec_path.read_text(encoding="utf-8")
    assert "'tools'" in spec_content or '"tools"' in spec_content

    build_py = Path("scripts/build_exe.py").read_text(encoding="utf-8")
    assert "--exclude-module=tools" in build_py
