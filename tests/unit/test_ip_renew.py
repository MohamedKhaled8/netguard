"""Unit tests for quick actions (IP renewal & DNS flush) truth verification."""

import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication
import sys

from app.platform.interfaces import IPlatformAdapter


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_quick_renew_ip_non_elevated(qapp):
    """When user is not elevated, renew IP must refuse with visible warning and not pretend success."""
    from app.ui.main_window import MainWindow

    mock_platform = MagicMock(spec=IPlatformAdapter)
    mock_platform.is_elevated.return_value = False
    mock_platform.get_primary_interface.return_value = "Wi-Fi"
    mock_platform.get_default_gateway.return_value = "192.168.1.1"

    mock_app_core = MagicMock()
    mock_app_core.ctx.platform = mock_platform

    with patch.object(MainWindow, "__init__", lambda self, *args, **kwargs: None):
        win = MainWindow()
        win.app_core = mock_app_core
        win.view_remediation = MagicMock()
        win.view_dashboard = MagicMock()

        win._on_quick_renew_ip()

        # Must not call renew_ip_lease
        mock_platform.renew_ip_lease.assert_not_called()
        # Must set warning text on button
        win.view_remediation.btn_renew_ip.setText.assert_called_with("تجديد IP (يتطلب صلاحيات مسؤول)")
        # Must log warning
        win.view_dashboard.log_autonomous_action.assert_called_once()
        args, kwargs = win.view_dashboard.log_autonomous_action.call_args
        assert kwargs.get("level") == "warning"
        assert "صلاحيات مسؤول" in args[1]


def test_quick_renew_ip_finished_success(qapp):
    """When renew IP succeeds and gateway responds, UI updates with success state."""
    from app.ui.main_window import MainWindow

    with patch.object(MainWindow, "__init__", lambda self, *args, **kwargs: None):
        win = MainWindow()
        win.view_remediation = MagicMock()
        win.view_dashboard = MagicMock()

        win._on_quick_renew_ip_finished(True, "Wi-Fi", "192.168.1.1", 3.5, "DHCP lease renewed successfully.")

        win.view_remediation.btn_renew_ip.setText.assert_called_with("تم تجديد عنوان IP بنجاح ✓")
        win.view_dashboard.log_autonomous_action.assert_called_once()
        args, kwargs = win.view_dashboard.log_autonomous_action.call_args
        assert kwargs.get("level") == "success"
        assert "3.5 ms" in args[1]


def test_quick_renew_ip_finished_failure(qapp):
    """When renew IP fails, UI surfaces the error honestly."""
    from app.ui.main_window import MainWindow

    with patch.object(MainWindow, "__init__", lambda self, *args, **kwargs: None):
        win = MainWindow()
        win.view_remediation = MagicMock()
        win.view_dashboard = MagicMock()

        win._on_quick_renew_ip_finished(False, "Wi-Fi", "192.168.1.1", 0.0, "Access denied")

        win.view_remediation.btn_renew_ip.setText.assert_called_with("فشل تجديد IP ✕")
        win.view_dashboard.log_autonomous_action.assert_called_once()
        args, kwargs = win.view_dashboard.log_autonomous_action.call_args
        assert kwargs.get("level") == "error"
        assert "Access denied" in args[1]
