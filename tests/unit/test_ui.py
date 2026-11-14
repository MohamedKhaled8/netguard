"""Unit tests for NetGuard AI Stage 12 Desktop Interface (PySide6)."""

import pytest
import os
from PySide6.QtWidgets import QApplication
from app.ui.widgets.status_card import StatusCard
from app.ui.widgets.realtime_chart import RealTimePlotWidget
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.diagnosis_view import DiagnosisView
from app.ui.views.remediation_view import RemediationView
from app.ui.views.traffic_view import TrafficView
from app.ui.views.dns_view import DNSView
from app.ui.views.history_view import HistoryView
from app.ui.views.settings_view import SettingsView
from app.ui.main_window import MainWindow
from app.application import create_application


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
