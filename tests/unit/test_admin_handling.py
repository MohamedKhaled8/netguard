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


def test_prompt_restart_as_admin_accepted():
    mock_platform = MagicMock()
    mock_platform.restart_as_administrator.return_value = True

    with patch("PySide6.QtWidgets.QMessageBox.question", return_value=16384), \
         patch("PySide6.QtCore.QCoreApplication.quit"), \
         patch("sys.exit"):  # 16384 == QMessageBox.Yes
        accepted = prompt_restart_as_admin(parent_widget=None, action_name="Test Action", platform=mock_platform)
        assert accepted is True
        mock_platform.restart_as_administrator.assert_called_once()
