"""Unit tests for responsive sidebar collapse and layout reflow (L7)."""

import os
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from app.application import create_application
from app.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication(["--platform", "offscreen"])
    return app


def test_sidebar_collapses_to_icon_dock_under_900px(qapp: QApplication):
    """Under 900px, sidebar must collapse to 64px width icon dock with tooltips."""
    net_app = create_application()
    win = MainWindow(application=net_app)
    win.resize(1100, 700)
    win.show()
    qapp.processEvents()

    # Initial desktop state
    assert win.sidebar.width() == 248
    assert win.sidebar.nav_buttons[0].text() != ""

    # Resize below 900px
    win.resize(800, 700)
    qapp.processEvents()

    assert win.sidebar.width() == 64
    assert win.sidebar.nav_buttons[0].text() == ""
    assert win.sidebar.nav_buttons[0].toolTip() != ""

    # Resize back above 900px
    win.resize(1200, 800)
    qapp.processEvents()

    assert win.sidebar.width() == 248
    assert win.sidebar.nav_buttons[0].text() != ""

    win.close()
    win.deleteLater()
    qapp.processEvents()
