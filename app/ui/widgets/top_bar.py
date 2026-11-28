"""Persistent Top Status Bar for NetGuard AI shell."""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget
from app.ui import icons, i18n, tokens
from app.ui.widgets.status_badge import StatusBadge


class TopStatusBar(QFrame):
    """Compact workstation header displaying active section, real connection/protection states, and actions."""

    refresh_requested = Signal()
    language_toggle_requested = Signal()
    notifications_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("TopStatusBar")
        self.setFixedHeight(56)
        self.setStyleSheet(
            f"""
            QFrame#TopStatusBar {{
                background-color: {tokens.SIDEBAR};
                border: 0px solid transparent;
                border-bottom: 1px solid {tokens.LINE};
            }}
            QFrame#TopStatusBar QLabel {{
                background: transparent;
                border: 0px solid transparent;
            }}
            """
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 8, 20, 8)
        lay.setSpacing(12)

        # Left/Start: Current Section Title & Subtitle (elide gracefully, never squish badges)
        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(1)
        self.lbl_section = QLabel(i18n.tr("nav_dashboard"), self)
        self.lbl_section.setFont(tokens.get_sans_font(15, 700))
        self.lbl_section.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_subtitle = QLabel("", self)
        self.lbl_subtitle.setFont(tokens.get_sans_font(12, 400))
        self.lbl_subtitle.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_subtitle.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.lbl_subtitle.setMaximumWidth(360)
        title_col.addWidget(self.lbl_section)
        title_col.addWidget(self.lbl_subtitle)
        lay.addLayout(title_col, 1)

        # Center/End: Live Status Pills (honest states only)
        self.badge_connection = StatusBadge(
            tokens.SystemStatus.WAITING, i18n.tr("status_waiting"), self
        )
        lay.addWidget(self.badge_connection)

        self.badge_guard = StatusBadge(
            tokens.SystemStatus.ACTIVE, i18n.tr("topbar_guard_ready"), self
        )
        lay.addWidget(self.badge_guard)

        self.badge_bg_op = StatusBadge(
            tokens.SystemStatus.WAITING, i18n.tr("topbar_bg_idle"), self
        )
        self.badge_bg_op.setVisible(False)
        lay.addWidget(self.badge_bg_op)

        self.lbl_last_update = QLabel(i18n.tr("topbar_no_updates"), self)
        self.lbl_last_update.setFont(tokens.get_mono_font(12, 400))
        self.lbl_last_update.setStyleSheet(f"color: {tokens.TEXT_MUTED}; padding: 0px 6px;")
        lay.addWidget(self.lbl_last_update)

        # Notification pill button
        self.btn_notifications = QPushButton("0", self)
        self.btn_notifications.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_notifications.setFixedHeight(36)
        self.btn_notifications.setIcon(icons.create_icon("alert", tokens.TEXT_SECONDARY, 14))
        self.btn_notifications.setFont(tokens.get_mono_font(12, 600))
        self.btn_notifications.setToolTip(i18n.tr("topbar_notifications"))
        self.btn_notifications.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {tokens.SURFACE_INSET};
                color: {tokens.TEXT_SECONDARY};
                border: 1px solid {tokens.LINE};
                border-radius: 6px;
                padding: 0px 10px;
            }}
            QPushButton:hover {{
                background-color: {tokens.SURFACE_HOVER};
                color: {tokens.TEXT};
            }}
            """
        )
        self.btn_notifications.clicked.connect(self.notifications_clicked.emit)
        lay.addWidget(self.btn_notifications)

        # Quick refresh button
        self.btn_refresh = QPushButton("", self)
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setFixedSize(36, 36)
        self.btn_refresh.setIcon(icons.create_icon("refresh", tokens.TEXT_SECONDARY, 15))
        self.btn_refresh.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {tokens.SURFACE_INSET};
                border: 1px solid {tokens.LINE};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {tokens.SURFACE_HOVER};
                border-color: {tokens.LINE_STRONG};
            }}
            """
        )
        self.btn_refresh.clicked.connect(self.refresh_requested.emit)
        lay.addWidget(self.btn_refresh)

        # Language switch button
        self.btn_lang = QPushButton(i18n.tr("lang_toggle"), self)
        self.btn_lang.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lang.setFixedHeight(36)
        self.btn_lang.setFont(tokens.get_sans_font(12, 600))
        self.btn_lang.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {tokens.SURFACE_INSET};
                color: {tokens.TEXT_SECONDARY};
                border: 1px solid {tokens.LINE};
                border-radius: 6px;
                padding: 0px 10px;
            }}
            QPushButton:hover {{
                background-color: {tokens.SURFACE_HOVER};
                color: {tokens.TEXT};
            }}
            """
        )
        self.btn_lang.clicked.connect(self.language_toggle_requested.emit)
        lay.addWidget(self.btn_lang)

    def set_section(self, title: str, subtitle: str = "") -> None:
        self.lbl_section.setText(title)
        short_sub = (subtitle[:52] + "…") if len(subtitle) > 54 else subtitle
        self.lbl_subtitle.setText(short_sub)
        self.lbl_subtitle.setToolTip(subtitle)
        self.lbl_subtitle.setVisible(bool(subtitle) and self.width() >= 1060)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        w = self.width()
        self.lbl_last_update.setVisible(w >= 960)
        self.lbl_subtitle.setVisible(bool(self.lbl_subtitle.text()) and w >= 1060)

    def set_connection_status(self, status: tokens.SystemStatus, label: str) -> None:
        self.badge_connection.set_status(status, label)

    def set_guard_status(self, status: tokens.SystemStatus, label: str) -> None:
        self.badge_guard.set_status(status, label)

    def set_background_operation(self, running: bool, label: str = "") -> None:
        if running and label:
            self.badge_bg_op.set_status(tokens.SystemStatus.RUNNING, label)
            self.badge_bg_op.setVisible(True)
        else:
            self.badge_bg_op.setVisible(False)

    def set_last_update(self, time_text: str) -> None:
        self.lbl_last_update.setText(f"{i18n.tr('topbar_last_update')}: {tokens.bidi_isolate(time_text)}")

    def set_notification_count(self, count: int, has_critical: bool = False) -> None:
        self.btn_notifications.setText(str(max(0, count)))
        col = tokens.STATUS_BAD if has_critical else (tokens.STATUS_WARN if count > 0 else tokens.TEXT_SECONDARY)
        self.btn_notifications.setIcon(icons.create_icon("alert", col, 14))

    def retranslate(self) -> None:
        self.btn_lang.setText(i18n.tr("lang_toggle"))
        self.btn_notifications.setToolTip(i18n.tr("topbar_notifications"))
