"""Unit tests for legacy UI widgets moved to legacy/ (RealTimePlotWidget, StatusCard)."""

import pytest
import os
from PySide6.QtWidgets import QApplication
from legacy.app.ui.widgets.status_card import StatusCard
from legacy.app.ui.widgets.realtime_chart import RealTimePlotWidget


@pytest.fixture(scope="session")
def qapp():
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
