"""Unit tests for Phase 4.4: Centralized Admin Elevation Enforcement."""

import pytest
from unittest.mock import MagicMock, patch
from app.platform.admin import require_admin, prompt_restart_as_admin
from app.remediation.actions.renew_dhcp import RenewIPLeaseAction
from app.remediation.actions.switch_dns import SwitchDNSResolverAction


def test_require_admin_helper():
    mock_platform = MagicMock()
    mock_platform.is_elevated.return_value = True

    ok, reason = require_admin("Test Action", mock_platform)
    assert ok is True
    assert reason == ""

    mock_platform.is_elevated.return_value = False
    ok, reason = require_admin("Test Action", mock_platform)
    assert ok is False
    assert "يتطلب إجراء 'Test Action' صلاحيات مسؤول" in reason


def test_remediation_actions_use_require_admin():
    mock_platform = MagicMock()
    mock_platform.is_elevated.return_value = False

    action_renew = RenewIPLeaseAction()
    ok_renew, reason_renew = action_renew.check_preconditions(mock_platform, {})
    assert ok_renew is False
    assert "صلاحيات مسؤول" in reason_renew

    action_dns = SwitchDNSResolverAction()
    ok_dns, reason_dns = action_dns.check_preconditions(mock_platform, {})
    assert ok_dns is False
    assert "صلاحيات مسؤول" in reason_dns


def test_prompt_restart_as_admin_accepted(monkeypatch):
    monkeypatch.setenv("ALLOW_TEST_QMESSAGEBOX", "1")
    mock_platform = MagicMock()
    mock_platform.restart_as_administrator.return_value = True

    with patch("PySide6.QtWidgets.QMessageBox.question", return_value=16384), \
         patch("PySide6.QtCore.QCoreApplication.quit"), \
         patch("sys.exit"):  # 16384 == QMessageBox.Yes
        accepted = prompt_restart_as_admin(parent_widget=None, action_name="Test Action", platform=mock_platform)
        assert accepted is True
        mock_platform.restart_as_administrator.assert_called_once()


def test_main_elevation_enforces_admin_exit_on_refusal(monkeypatch):
    """Verify that unprivileged user mode is strictly banned and exits if elevation is refused."""
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setattr("sys.argv", ["main.py"])
    monkeypatch.setenv("NETGUARD_TEST_ELEVATION", "1")
    
    mock_shell32 = MagicMock()
    mock_shell32.IsUserAnAdmin.return_value = 0  # Non-admin
    mock_shell32.ShellExecuteW.return_value = 5  # Elevation refused / cancelled (<= 32)
    
    mock_user32 = MagicMock()
    
    with patch("ctypes.windll", MagicMock(shell32=mock_shell32, user32=mock_user32)):
        from app.main import main
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        mock_shell32.ShellExecuteW.assert_called_once()
        mock_user32.MessageBoxW.assert_called_once()

