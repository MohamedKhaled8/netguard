"""Unit tests for Phase 4.3: Threading, non-blocking UI operations, and timer overlap capping."""

import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication

# Ensure QApplication exists for widget testing
_app = QApplication.instance() or QApplication([])


def test_ui_tick_timer_overlap_capping():
    """Verify that _on_ui_tick skips execution if a previous tick is still active."""
    from app.ui.main_window import MainWindow

    win = MainWindow.__new__(MainWindow)
    win._is_ui_tick_running = True
    win.app_core = MagicMock()
    win.view_dashboard = MagicMock()
    win.view_diagnosis = MagicMock()
    win.view_history = MagicMock()
    win.view_remediation = MagicMock()

    # Call _on_ui_tick while locked
    win._on_ui_tick()

    # Telemetry should NOT have been updated because tick was skipped
    assert win.view_dashboard.update_telemetry.call_count == 0

    # Unlock and verify execution proceeds
    win._is_ui_tick_running = False
    win.stack = MagicMock()
    win.ticker_counter = 0
    win._refresh_day_strips = MagicMock()
    win._on_ui_tick()
    assert win.view_dashboard.update_telemetry.call_count == 1
    assert win._is_ui_tick_running is False


def test_dns_benchmark_overlap_capping():
    """Verify that _on_run_dns_benchmark skips execution if benchmark is already running."""
    from app.ui.main_window import MainWindow

    win = MainWindow.__new__(MainWindow)
    win._is_benchmarking_dns = True
    win.view_dns = MagicMock()

    win._on_run_dns_benchmark()
    # benchmark_btn should NOT have been modified because benchmark was skipped
    assert win.view_dns.benchmark_btn.setEnabled.call_count == 0
