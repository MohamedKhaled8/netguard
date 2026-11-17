"""Unit tests for the Objective Layout & Typography Checker (L0)."""

import os
import sys
import pytest

from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtGui import QColor

from scripts.check_layout import (
    calculate_luminance,
    calculate_contrast,
    LayoutChecker,
    Violation,
)
from app.application import create_application
from app.ui.main_window import MainWindow


def test_wcag_luminance_and_contrast_calculations():
    """Verify luminance and contrast formula against known WCAG values."""
    white = QColor("#FFFFFF")
    black = QColor("#000000")

    # Black vs White contrast must be 21:1
    contrast = calculate_contrast(white, black)
    assert abs(contrast - 21.0) < 0.1

    # Identical colors must be 1:1
    assert abs(calculate_contrast(white, white) - 1.0) < 0.01

    # Text #ECEBE6 on Surface #15181A should be well above 4.5:1
    text_color = QColor("#ECEBE6")
    surface_color = QColor("#15181A")
    ratio = calculate_contrast(text_color, surface_color)
    assert ratio >= 4.5


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication(["--platform", "offscreen"])
    return app


def test_layout_checker_populates_and_checks_window(qapp: QApplication):
    """LayoutChecker must be able to inspect MainWindow offscreen."""
    net_app = create_application()
    win = MainWindow(application=net_app)
    win.show()
    qapp.processEvents()

    checker = LayoutChecker(scale=1.0)
    # Check that populate mock data succeeds
    checker.populate_mock_data(win)

    # Verify that checker traverses views and produces violations on current unpatched layout
    violations = checker.check_all_pages(win)
    assert isinstance(violations, list)
    assert len(violations) > 0  # Confirms baseline defects exist before fixes

    win.close()
    win.deleteLater()
    qapp.processEvents()
