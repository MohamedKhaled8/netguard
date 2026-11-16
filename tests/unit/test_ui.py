"""Unit tests for NetGuard AI Stage 12 Desktop Interface (PySide6)."""

import pytest
import os
import math
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtGui import QImage, QPainter
from app.ui import tokens
from app.ui.widgets.status_card import StatusCard
from app.ui.widgets.realtime_chart import RealTimePlotWidget
from app.ui.widgets.metric_cell import MetricCell, MetricsStrip
from app.ui.widgets.sparkline import Sparkline
from app.ui.widgets.day_strip import DayStrip, DayStripCanvas
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.diagnosis_view import DiagnosisView
from app.ui.views.remediation_view import RemediationView
from app.ui.views.traffic_view import TrafficView
from app.ui.views.dns_view import DNSView
from app.ui.views.history_view import HistoryView
from app.ui.views.settings_view import SettingsView
from app.ui.main_window import MainWindow
from app.application import create_application
from app.core.models.metrics import (
    MetricType,
    Measurement,
    MeasurementSource,
    ProbeStatus,
    Diagnosis,
    ProbableCause,
    DiagnosisSeverity,
)
from app.storage.database import DatabaseManager
from app.storage.repositories.measurement_repo import MeasurementRepository
from app.storage.repositories.incident_repo import IncidentRepository


@pytest.fixture(scope="session")
def qapp():
    # Run in offscreen / headless mode for unit test automation
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_status_card(qapp):
    card = StatusCard("Test Metric", "15.0", "ms")
    assert card.title_lbl.text() == "Test Metric"
    assert card.val_lbl.text() == "15.0"
    card.update_metric("45.0", "Warning", is_warning=True)
    assert card.val_lbl.text() == "45.0"


def test_realtime_chart(qapp):
    chart = RealTimePlotWidget("Test Plot")
    chart.update_data([10.0, 12.5, 14.0, 18.0])
    assert chart is not None


def test_all_views_and_main_window(qapp):
    net_app = create_application()
    win = MainWindow(application=net_app)
    assert win is not None
    assert win.stack.count() == 7

    # Trigger UI tick
    win._on_ui_tick()

    # Switch views
    win._switch_view(1, win.btn_diag)
    assert win.stack.currentIndex() == 1
    win._switch_view(0, win.btn_dash)
    assert win.stack.currentIndex() == 0


def test_traffic_view_and_session_cards(qapp):
    traffic_view = TrafficView()
    assert traffic_view is not None

    # Initial state starts honest and empty
    assert len(traffic_view.report_cards) == 0
    assert traffic_view.reports_list_layout.count() >= 1

    # Toggle simulated Zoom call
    traffic_view._on_sim_zoom_clicked()
    assert traffic_view.active_session_layout.count() == 1
    assert "نشط" in traffic_view.meeting_lbl.text()

    # Close simulated Zoom call
    traffic_view._on_sim_zoom_clicked()
    assert traffic_view.active_session_layout.count() == 0
    assert len(traffic_view.report_cards) == 1

    # Test expanding report card
    report_card = traffic_view.report_cards[0]
    assert report_card.is_expanded is False
    assert report_card.detail_container.isHidden() is True
    report_card._toggle_expand()
    assert report_card.is_expanded is True
    assert report_card.detail_container.isHidden() is False
    report_card._toggle_expand()
    assert report_card.is_expanded is False
    assert report_card.detail_container.isHidden() is True


def test_metrics_strip_initial_state(qapp):
    strip = MetricsStrip()
    assert strip.cell_download.val_lbl.text() == " — "
    assert strip.cell_latency.val_lbl.text() == " — "
    assert strip.cell_jitter.val_lbl.text() == " — "
    assert strip.cell_loss.val_lbl.text() == " — "

    assert strip.cell_download.sparkline.samples == []
    assert strip.cell_latency.sparkline.samples == []
    assert strip.cell_jitter.sparkline.samples == []
    assert strip.cell_loss.sparkline.samples == []

    assert strip.cell_download.footer_lbl.text() == "بانتظار القياس..."
    assert strip.cell_latency.footer_lbl.text() == "بانتظار القياس..."


def test_sparkline_empty_and_graceful(qapp):
    spark = Sparkline()
    assert spark.samples == []

    # Updating with empty or None
    spark.set_data([])
    assert spark.samples == []

    # Updating with samples
    spark.set_data([10.0, 20.0, 30.0])
    assert spark.samples == [10.0, 20.0, 30.0]

    # Truncates to last 24
    spark.set_data([float(i) for i in range(30)])
    assert len(spark.samples) == 24
    assert spark.samples[0] == 6.0


def test_dashboard_telemetry_disconnected_state(qapp):
    view = DashboardView()
    view.update_telemetry(None, None)

    assert view.metrics_strip.cell_download.val_lbl.text() == " — "
    assert "غير متصل" in view.metrics_strip.cell_download.footer_lbl.text()
    assert view.metrics_strip.cell_download.sparkline.samples == []

    assert view.metrics_strip.cell_latency.val_lbl.text() == " — "
    assert "غير متصل" in view.metrics_strip.cell_latency.footer_lbl.text()
    assert view.metrics_strip.cell_latency.sparkline.samples == []


def test_dashboard_telemetry_live_bandwidth_conversion(qapp):
    view = DashboardView()

    mock_obs = MagicMock()
    now = datetime.now(timezone.utc)

    # 12,500,000 bytes/sec * 8 / 1e6 = 100.0 Mbps download
    rx_m = Measurement(
        source=MeasurementSource.PSUTIL_INTERFACE,
        target_or_interface="Ethernet",
        metric_type=MetricType.BANDWIDTH_RX_BYTES_PER_SEC,
        raw_value=12_500_000.0,
        normalized_value=12_500_000.0,
        unit="bytes/sec",
        status=ProbeStatus.SUCCESS,
        timestamp=now,
    )
    # 3,125,000 bytes/sec * 8 / 1e6 = 25.0 Mbps upload
    tx_m = Measurement(
        source=MeasurementSource.PSUTIL_INTERFACE,
        target_or_interface="Ethernet",
        metric_type=MetricType.BANDWIDTH_TX_BYTES_PER_SEC,
        raw_value=3_125_000.0,
        normalized_value=3_125_000.0,
        unit="bytes/sec",
        status=ProbeStatus.SUCCESS,
        timestamp=now,
    )
    ext_m = Measurement(
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="1.1.1.1",
        metric_type=MetricType.EXTERNAL_LATENCY,
        raw_value=18.4,
        normalized_value=18.4,
        unit="ms",
        status=ProbeStatus.SUCCESS,
        timestamp=now,
    )
    jit_m = Measurement(
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="1.1.1.1",
        metric_type=MetricType.JITTER_MS,
        raw_value=2.1,
        normalized_value=2.1,
        unit="ms",
        status=ProbeStatus.SUCCESS,
        timestamp=now,
    )
    loss_m = Measurement(
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="192.168.1.1",
        metric_type=MetricType.GATEWAY_PACKET_LOSS,
        raw_value=0.0,
        normalized_value=0.0,
        unit="ratio",
        status=ProbeStatus.SUCCESS,
        timestamp=now,
    )

    def get_latest(mt):
        return {
            MetricType.BANDWIDTH_RX_BYTES_PER_SEC: rx_m,
            MetricType.BANDWIDTH_TX_BYTES_PER_SEC: tx_m,
            MetricType.EXTERNAL_LATENCY: ext_m,
            MetricType.JITTER_MS: jit_m,
            MetricType.GATEWAY_PACKET_LOSS: loss_m,
        }.get(mt)

    def get_window(mt):
        m = get_latest(mt)
        return [m] if m else []

    mock_obs.get_latest_measurement.side_effect = get_latest
    mock_obs.get_sliding_window.side_effect = get_window

    view.update_telemetry(mock_obs, None)

    # Validate throughput tile formatting & conversion
    assert view.metrics_strip.cell_download.val_lbl.text() == "100"
    assert "الرفع 25.0 Mbps" in view.metrics_strip.cell_download.footer_lbl.text()
    assert view.metrics_strip.cell_download.sparkline.samples == [100.0]

    # Validate other tiles
    assert view.metrics_strip.cell_latency.val_lbl.text() == "18"
    assert view.metrics_strip.cell_jitter.val_lbl.text() == "2.1"
    assert view.metrics_strip.cell_loss.val_lbl.text() == "0.0"


def test_dashboard_telemetry_speed_test_timestamp(qapp):
    view = DashboardView()
    view.set_last_speed_test_time("17:45")

    # When disconnected
    view.update_telemetry(None, None)
    assert "آخر فحص: 17:45" in view.metrics_strip.cell_download.footer_lbl.text()


def test_speed_test_scan_signal_and_window_integration(qapp):
    net_app = create_application()
    win = MainWindow(application=net_app)

    assert win._last_speed_test_time is None
    win._on_speed_test_done("18:00")
    assert win._last_speed_test_time == "18:00"
    assert win.view_dashboard._last_speed_test_time == "18:00"
    assert "آخر فحص: 18:00" in win.view_dashboard.metrics_strip.cell_download.footer_lbl.text()


def test_dashboard_telemetry_negative_bandwidth(qapp):
    view = DashboardView()
    now = datetime.now(timezone.utc)
    mock_obs = MagicMock()

    # Negative RX bandwidth measurement
    neg_rx = Measurement(
        source=MeasurementSource.PSUTIL_INTERFACE,
        target_or_interface="Ethernet",
        metric_type=MetricType.BANDWIDTH_RX_BYTES_PER_SEC,
        raw_value=-500.0,
        normalized_value=-500.0,
        unit="bytes/sec",
        status=ProbeStatus.SUCCESS,
        timestamp=now,
    )
    mock_obs.get_latest_measurement.side_effect = lambda mt: neg_rx if mt == MetricType.BANDWIDTH_RX_BYTES_PER_SEC else None
    mock_obs.get_sliding_window.return_value = []

    view.update_telemetry(mock_obs, None)

    # Negative RX must show " — ", not "-0.00"
    assert view.metrics_strip.cell_download.val_lbl.text() == " — "
    assert "غير متصل" in view.metrics_strip.cell_download.footer_lbl.text()
    assert view.metrics_strip.cell_download.sparkline.samples == []
    assert view.metrics_strip.cell_download.status_color == tokens.TEXT_MUTED

    # Test negative TX with valid RX
    valid_rx = Measurement(
        source=MeasurementSource.PSUTIL_INTERFACE,
        target_or_interface="Ethernet",
        metric_type=MetricType.BANDWIDTH_RX_BYTES_PER_SEC,
        raw_value=12_500_000.0,
        normalized_value=12_500_000.0,
        unit="bytes/sec",
        status=ProbeStatus.SUCCESS,
        timestamp=now,
    )
    neg_tx = Measurement(
        source=MeasurementSource.PSUTIL_INTERFACE,
        target_or_interface="Ethernet",
        metric_type=MetricType.BANDWIDTH_TX_BYTES_PER_SEC,
        raw_value=-1000.0,
        normalized_value=-1000.0,
        unit="bytes/sec",
        status=ProbeStatus.SUCCESS,
        timestamp=now,
    )

    def get_latest_with_neg_tx(mt):
        if mt == MetricType.BANDWIDTH_RX_BYTES_PER_SEC:
            return valid_rx
        if mt == MetricType.BANDWIDTH_TX_BYTES_PER_SEC:
            return neg_tx
        return None

    mock_obs.get_latest_measurement.side_effect = get_latest_with_neg_tx
    view.update_telemetry(mock_obs, None)

    assert view.metrics_strip.cell_download.val_lbl.text() == "100"
    # Negative TX must fallback to 0.0, not display negative Mbps
    assert "الرفع 0.00 Mbps" in view.metrics_strip.cell_download.footer_lbl.text()


def test_dashboard_telemetry_nan_bandwidth(qapp):
    view = DashboardView()
    now = datetime.now(timezone.utc)
    mock_obs = MagicMock()

    # NaN RX bandwidth measurement
    nan_rx = Measurement(
        source=MeasurementSource.PSUTIL_INTERFACE,
        target_or_interface="Ethernet",
        metric_type=MetricType.BANDWIDTH_RX_BYTES_PER_SEC,
        raw_value=float("nan"),
        normalized_value=float("nan"),
        unit="bytes/sec",
        status=ProbeStatus.SUCCESS,
        timestamp=now,
    )
    mock_obs.get_latest_measurement.side_effect = lambda mt: nan_rx if mt == MetricType.BANDWIDTH_RX_BYTES_PER_SEC else None
    mock_obs.get_sliding_window.return_value = []

    view.update_telemetry(mock_obs, None)

    # NaN RX must show " — ", not "nan"
    assert view.metrics_strip.cell_download.val_lbl.text() == " — "
    assert "غير متصل" in view.metrics_strip.cell_download.footer_lbl.text()
    assert view.metrics_strip.cell_download.sparkline.samples == []
    # Status dot must be muted, not STATUS_OK (green)
    assert view.metrics_strip.cell_download.status_color == tokens.TEXT_MUTED

    # Test NaN TX with valid RX
    valid_rx = Measurement(
        source=MeasurementSource.PSUTIL_INTERFACE,
        target_or_interface="Ethernet",
        metric_type=MetricType.BANDWIDTH_RX_BYTES_PER_SEC,
        raw_value=12_500_000.0,
        normalized_value=12_500_000.0,
        unit="bytes/sec",
        status=ProbeStatus.SUCCESS,
        timestamp=now,
    )
    nan_tx = Measurement(
        source=MeasurementSource.PSUTIL_INTERFACE,
        target_or_interface="Ethernet",
        metric_type=MetricType.BANDWIDTH_TX_BYTES_PER_SEC,
        raw_value=float("nan"),
        normalized_value=float("nan"),
        unit="bytes/sec",
        status=ProbeStatus.SUCCESS,
        timestamp=now,
    )

    def get_latest_with_nan_tx(mt):
        if mt == MetricType.BANDWIDTH_RX_BYTES_PER_SEC:
            return valid_rx
        if mt == MetricType.BANDWIDTH_TX_BYTES_PER_SEC:
            return nan_tx
        return None

    mock_obs.get_latest_measurement.side_effect = get_latest_with_nan_tx
    view.update_telemetry(mock_obs, None)

    assert view.metrics_strip.cell_download.val_lbl.text() == "100"
    assert "الرفع 0.00 Mbps" in view.metrics_strip.cell_download.footer_lbl.text()


def test_dashboard_telemetry_nan_and_negative_latency_jitter_loss(qapp):
    view = DashboardView()
    now = datetime.now(timezone.utc)
    mock_obs = MagicMock()

    # NaN latency, jitter, loss
    nan_lat = Measurement(
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="1.1.1.1",
        metric_type=MetricType.EXTERNAL_LATENCY,
        raw_value=float("nan"),
        normalized_value=float("nan"),
        unit="ms",
        status=ProbeStatus.SUCCESS,
        timestamp=now,
    )
    nan_jit = Measurement(
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="1.1.1.1",
        metric_type=MetricType.JITTER_MS,
        raw_value=float("nan"),
        normalized_value=float("nan"),
        unit="ms",
        status=ProbeStatus.SUCCESS,
        timestamp=now,
    )
    nan_loss = Measurement(
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="192.168.1.1",
        metric_type=MetricType.GATEWAY_PACKET_LOSS,
        raw_value=float("nan"),
        normalized_value=float("nan"),
        unit="ratio",
        status=ProbeStatus.SUCCESS,
        timestamp=now,
    )

    def get_latest_nan(mt):
        return {
            MetricType.EXTERNAL_LATENCY: nan_lat,
            MetricType.JITTER_MS: nan_jit,
            MetricType.GATEWAY_PACKET_LOSS: nan_loss,
        }.get(mt)

    mock_obs.get_latest_measurement.side_effect = get_latest_nan
    # Sliding window with NaN values
    mock_obs.get_sliding_window.side_effect = lambda mt: [nan_lat] if mt == MetricType.EXTERNAL_LATENCY else []

    # Must execute cleanly without ValueError (cannot convert float NaN to integer)
    view.update_telemetry(mock_obs, None)

    assert view.metrics_strip.cell_latency.val_lbl.text() == " — "
    assert "غير متصل" in view.metrics_strip.cell_latency.footer_lbl.text()
    assert view.metrics_strip.cell_latency.sparkline.samples == []

    assert view.metrics_strip.cell_jitter.val_lbl.text() == " — "
    assert "غير متصل" in view.metrics_strip.cell_jitter.footer_lbl.text()
    assert view.metrics_strip.cell_jitter.sparkline.samples == []

    assert view.metrics_strip.cell_loss.val_lbl.text() == " — "
    assert "غير متصل" in view.metrics_strip.cell_loss.footer_lbl.text()
    assert view.metrics_strip.cell_loss.sparkline.samples == []

    # Test negative latency, jitter, loss
    neg_lat = Measurement(
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="1.1.1.1",
        metric_type=MetricType.EXTERNAL_LATENCY,
        raw_value=-25.0,
        normalized_value=-25.0,
        unit="ms",
        status=ProbeStatus.SUCCESS,
        timestamp=now,
    )
    neg_jit = Measurement(
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="1.1.1.1",
        metric_type=MetricType.JITTER_MS,
        raw_value=-5.0,
        normalized_value=-5.0,
        unit="ms",
        status=ProbeStatus.SUCCESS,
        timestamp=now,
    )
    neg_loss = Measurement(
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="192.168.1.1",
        metric_type=MetricType.GATEWAY_PACKET_LOSS,
        raw_value=-0.1,
        normalized_value=-0.1,
        unit="ratio",
        status=ProbeStatus.SUCCESS,
        timestamp=now,
    )

    def get_latest_neg(mt):
        return {
            MetricType.EXTERNAL_LATENCY: neg_lat,
            MetricType.JITTER_MS: neg_jit,
            MetricType.GATEWAY_PACKET_LOSS: neg_loss,
        }.get(mt)

    mock_obs.get_latest_measurement.side_effect = get_latest_neg
    view.update_telemetry(mock_obs, None)

    assert view.metrics_strip.cell_latency.val_lbl.text() == " — "
    assert view.metrics_strip.cell_jitter.val_lbl.text() == " — "
    assert view.metrics_strip.cell_loss.val_lbl.text() == " — "

    # Test infinite values (math.isinf)
    inf_lat = Measurement(
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="1.1.1.1",
        metric_type=MetricType.EXTERNAL_LATENCY,
        raw_value=float("inf"),
        normalized_value=float("inf"),
        unit="ms",
        status=ProbeStatus.SUCCESS,
        timestamp=now,
    )
    mock_obs.get_latest_measurement.side_effect = lambda mt: inf_lat if mt == MetricType.EXTERNAL_LATENCY else None
    view.update_telemetry(mock_obs, None)
    assert view.metrics_strip.cell_latency.val_lbl.text() == " — "


def test_day_strip_canvas_no_hardcoded_slow_spikes(qapp):
    """Verify DayStripCanvas initializes without fabricated slow spikes at slots 30-31."""
    canvas = DayStripCanvas()
    now = datetime.now()
    current_slot = min(47, (now.hour * 60 + now.minute) // 30)

    # Slots 30 and 31 must NOT be hardcoded to 'slow'
    assert len(canvas.bar_states) == 48
    if current_slot < 30:
        assert canvas.bar_states[30] == "future"
        assert canvas.bar_states[31] == "future"
    else:
        assert canvas.bar_states[30] == "no-data"
        assert canvas.bar_states[31] == "no-data"

    for i in range(48):
        if i > current_slot:
            assert canvas.bar_states[i] == "future"
        else:
            assert canvas.bar_states[i] == "no-data"


def test_day_strip_canvas_5_states(qapp):
    """Verify all 5 bar states return correct heights and paint cleanly."""
    canvas = DayStripCanvas()
    canvas.resize(480, 68)

    sample_states = ["healthy", "slow", "bad", "no-data", "future"] * 9 + ["healthy"] * 3
    canvas.set_data(sample_states)
    assert len(canvas.bar_states) == 48

    # Check heights according to canonical spec
    rect_healthy = canvas._get_slot_rect(0, 480.0)
    assert rect_healthy.height() == 44.0

    rect_slow = canvas._get_slot_rect(1, 480.0)
    assert rect_slow.height() == 26.0

    rect_bad = canvas._get_slot_rect(2, 480.0)
    assert rect_bad.height() == 40.0

    rect_nodata = canvas._get_slot_rect(3, 480.0)
    assert rect_nodata.height() == 9.0

    rect_future = canvas._get_slot_rect(4, 480.0)
    assert rect_future.height() == 11.0

    # Verify offscreen paint does not throw
    img = QImage(480, 68, QImage.Format_ARGB32)
    canvas.render(img)
    assert not img.isNull()


def test_day_strip_legend_elements(qapp):
    """Verify DayStrip legend contains healthy, slow, and outage indicators."""
    strip = DayStrip()
    labels = strip.findChildren(QLabel)
    label_texts = [lbl.text() for lbl in labels]

    assert "سليم" in label_texts
    assert "تباطؤ" in label_texts
    assert "انقطاع" in label_texts


def test_measurement_repo_get_day_slots(tmp_path: Path):
    """Verify get_day_slots generates 48 slots reflecting measurement and incident data."""
    db_file = tmp_path / "test_day_slots.db"
    db_manager = DatabaseManager(db_path=db_file, enable_wal=False)
    meas_repo = MeasurementRepository(db_manager)
    inc_repo = IncidentRepository(db_manager)

    today = date.today()
    slots = meas_repo.get_day_slots(today)
    assert len(slots) == 48

    now = datetime.now()
    current_slot = min(47, (now.hour * 60 + now.minute) // 30)

    # Future slots check
    for s in range(current_slot + 1, 48):
        assert slots[s] == "future"

    # Insert a healthy sample in slot 0 (00:15 local)
    t0 = datetime(today.year, today.month, today.day, 0, 15, 0).astimezone()
    m_healthy = Measurement(
        timestamp=t0,
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="192.168.1.1",
        metric_type=MetricType.GATEWAY_LATENCY,
        raw_value=8.0,
        normalized_value=8.0,
        unit="ms",
        status=ProbeStatus.SUCCESS,
        confidence=1.0,
    )
    meas_repo.save(m_healthy)

    # Insert a slow sample in slot 1 (00:45 local: gateway_latency > 25.0ms)
    t1 = datetime(today.year, today.month, today.day, 0, 45, 0).astimezone()
    m_slow = Measurement(
        timestamp=t1,
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="192.168.1.1",
        metric_type=MetricType.GATEWAY_LATENCY,
        raw_value=45.0,
        normalized_value=45.0,
        unit="ms",
        status=ProbeStatus.SUCCESS,
        confidence=1.0,
    )
    meas_repo.save(m_slow)

    # Insert a bad sample in slot 2 (01:15 local: packet_loss > 0.40)
    t2 = datetime(today.year, today.month, today.day, 1, 15, 0).astimezone()
    m_bad = Measurement(
        timestamp=t2,
        source=MeasurementSource.ICMP_ECHO,
        target_or_interface="192.168.1.1",
        metric_type=MetricType.GATEWAY_PACKET_LOSS,
        raw_value=0.60,
        normalized_value=0.60,
        unit="ratio",
        status=ProbeStatus.DEGRADED,
        confidence=1.0,
    )
    meas_repo.save(m_bad)

    # Insert a critical incident in slot 3 (01:45 local)
    t3 = datetime(today.year, today.month, today.day, 1, 45, 0).astimezone()
    diag = Diagnosis(
        timestamp=t3,
        probable_cause=ProbableCause.LOCAL_GATEWAY_UNREACHABLE,
        confidence=0.95,
        severity=DiagnosisSeverity.CRITICAL,
        explanation="الراوتر غير مستجيب نهائياً",
    )
    inc_repo.save(diag)

    slots_updated = meas_repo.get_day_slots(today)
    if current_slot >= 0:
        assert slots_updated[0] == "healthy"
    if current_slot >= 1:
        assert slots_updated[1] == "slow"
    if current_slot >= 2:
        assert slots_updated[2] == "bad"
    if current_slot >= 3:
        assert slots_updated[3] == "bad"

    # Test query for a historical day (all slots non-future)
    yesterday = today - timedelta(days=1)
    slots_yesterday = meas_repo.get_day_slots(yesterday)
    assert len(slots_yesterday) == 48
    assert all(s in ("no-data", "healthy", "slow", "bad") for s in slots_yesterday)
    assert "future" not in slots_yesterday


def test_history_view_date_navigation(qapp, tmp_path: Path):
    """Verify HistoryView day navigation, Arabic label formatting, and slot reload."""
    db_file = tmp_path / "test_hist_nav.db"
    db_manager = DatabaseManager(db_path=db_file, enable_wal=False)
    meas_repo = MeasurementRepository(db_manager)
    inc_repo = IncidentRepository(db_manager)

    view = HistoryView(measurement_repo=meas_repo, incident_repo=inc_repo)
    today = date.today()
    assert view.current_date == today
    assert view.btn_next.isEnabled() is False
    assert "اليوم" in view.lbl_day.text()

    # Click Previous Day
    view.btn_prev.click()
    assert view.current_date == today - timedelta(days=1)
    assert view.btn_next.isEnabled() is True
    assert "أمس" in view.lbl_day.text()

    # Click Previous Day again
    view.btn_prev.click()
    assert view.current_date == today - timedelta(days=2)
    assert view.btn_next.isEnabled() is True

    # Click Next Day
    view.btn_next.click()
    assert view.current_date == today - timedelta(days=1)
    assert view.btn_next.isEnabled() is True
    assert "أمس" in view.lbl_day.text()

    # Click Next Day back to today
    view.btn_next.click()
    assert view.current_date == today
    assert view.btn_next.isEnabled() is False
    assert "اليوم" in view.lbl_day.text()


def test_history_view_incident_display_and_empty_state(qapp, tmp_path: Path):
    """Verify HistoryView displays real incident cards or truthful empty state."""
    db_file = tmp_path / "test_hist_empty.db"
    db_manager = DatabaseManager(db_path=db_file, enable_wal=False)
    meas_repo = MeasurementRepository(db_manager)
    inc_repo = IncidentRepository(db_manager)

    view = HistoryView(measurement_repo=meas_repo, incident_repo=inc_repo)

    # With 0 incidents, empty state must appear
    assert view.events_list_layout.count() == 1
    card = view.events_list_layout.itemAt(0).widget()
    labels = card.findChildren(QLabel)
    assert any("لا توجد أحداث" in lbl.text() for lbl in labels)

    # Save real incident for today
    diag = Diagnosis(
        timestamp=datetime.now(timezone.utc),
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        confidence=0.88,
        severity=DiagnosisSeverity.HIGH,
        explanation="خادم Cloudflare 1.1.1.1 لم يستجب",
        recommended_actions=["التحويل إلى خادم Google DNS 8.8.8.8"],
    )
    inc_repo.save(diag)

    # Refresh
    view._refresh_day()
    assert view.events_list_layout.count() >= 1
    event_card = view.events_list_layout.itemAt(0).widget()
    event_labels = [lbl.text() for lbl in event_card.findChildren(QLabel)]
    assert any("DNS" in txt for txt in event_labels)
    assert any("Cloudflare" in txt for txt in event_labels)


