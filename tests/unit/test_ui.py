"""Unit tests for NetGuard AI Stage 12 Desktop Interface (PySide6)."""

import pytest
import os
import math
from datetime import datetime, timezone
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication
from app.ui import tokens
from app.ui.widgets.status_card import StatusCard
from app.ui.widgets.realtime_chart import RealTimePlotWidget
from app.ui.widgets.metric_cell import MetricCell, MetricsStrip
from app.ui.widgets.sparkline import Sparkline
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.diagnosis_view import DiagnosisView
from app.ui.views.remediation_view import RemediationView
from app.ui.views.traffic_view import TrafficView
from app.ui.views.dns_view import DNSView
from app.ui.views.history_view import HistoryView
from app.ui.views.settings_view import SettingsView
from app.ui.main_window import MainWindow
from app.application import create_application
from app.core.models.metrics import MetricType, Measurement, MeasurementSource, ProbeStatus


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

    # Check default completed session reports
    assert traffic_view.reports_list_layout.count() >= 3

    # Toggle simulated Zoom call
    traffic_view._on_sim_zoom_clicked()
    assert traffic_view.active_session_layout.count() == 1
    assert "نشط" in traffic_view.meeting_lbl.text()

    # Close simulated Zoom call
    traffic_view._on_sim_zoom_clicked()
    assert traffic_view.active_session_layout.count() == 0
    assert traffic_view.reports_list_layout.count() >= 4

    # Test expanding report card
    report_card = traffic_view.reports_list_layout.itemAt(0).widget()
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


