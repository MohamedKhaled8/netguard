"""Centralized Administrator / Elevation Enforcement & Relaunch Helpers for NetGuard AI."""

from __future__ import annotations
import sys
import logging
from typing import Optional, Tuple
from app.platform.interfaces import IPlatformAdapter

logger = logging.getLogger("netguard.platform.admin")


def require_admin(
    action_name: str,
    platform: Optional[IPlatformAdapter] = None,
) -> Tuple[bool, str]:
    """Central elevation check helper.

    Args:
        action_name: Human-readable name of the action requiring elevation.
        platform: Optional platform adapter instance.

    Returns:
        (is_elevated, reason_if_not)
    """
    if platform is None:
        try:
            from app.platform.factory import get_platform_adapter
            platform = get_platform_adapter()
        except Exception:
            return False, "Platform adapter not initialized."

    if platform.is_elevated():
        return True, ""

    reason = (
        f"يتطلب إجراء '{action_name}' صلاحيات مسؤول لنظام Windows (Administrator). "
        "يُرجى تشغيل البرنامج كمسؤول لتطبيق هذا الإجراء."
    )
    return False, reason


def prompt_restart_as_admin(
    parent_widget=None,
    action_name: str = "",
    platform: Optional[IPlatformAdapter] = None,
) -> bool:
    """Show a visible prompt asking user to restart the application as administrator.

    If accepted, relaunches elevated via Windows UAC and exits current process.
    """
    from PySide6.QtWidgets import QMessageBox
    from PySide6.QtCore import QCoreApplication

    if platform is None:
        from app.platform.factory import get_platform_adapter
        platform = get_platform_adapter()

    title = "صلاحيات مسؤول مطلوبة (Administrator Required)"
    msg = (
        f"يتطلب إجراء '{action_name or 'هذا الخيار'}' صلاحيات مسؤول لنظام Windows.\n\n"
        "هل ترغب في إعادة تشغيل NetGuard AI الآن بصلاحيات مسؤول (Run as Administrator) لتفعيل كافة الميزات؟"
    )

    reply = QMessageBox.question(
        parent_widget,
        title,
        msg,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes,
    )

    if reply == QMessageBox.Yes:
        logger.info("User requested elevation restart for action: %s", action_name)
        ok = platform.restart_as_administrator()
        if ok:
            QCoreApplication.quit()
            sys.exit(0)
            return True
        else:
            QMessageBox.critical(
                parent_widget,
                "فشل التشغيل كمسؤول",
                "تعذر طلب صلاحيات المسؤول من نظام التشغيل Windows.",
            )
    return False
