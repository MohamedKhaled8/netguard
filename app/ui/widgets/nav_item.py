"""Sidebar Navigation Item component for NetGuard AI.

Clean monochrome vector line icon (18px, 1.6px stroke) + text label.
Supports RTL and LTR layout directions, active electric-blue indicator,
and 64px collapsed icon mode with tooltips.
"""

from __future__ import annotations
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QPushButton
from app.ui import icons, tokens


class NavItem(QPushButton):
    """Sidebar navigation item with custom crisp vector line icon."""

    def __init__(self, icon_name: str, label: str, index: int, parent=None) -> None:
        super().__init__(label, parent)
        self.icon_name = icon_name
        self.index = index
        self._original_label = label
        self._is_collapsed = False
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)
        self.setFont(tokens.get_sans_font(13, 500))
        self._update_style()

    def set_label_text(self, label: str) -> None:
        self._original_label = label
        if self._is_collapsed:
            self.setText("")
            self.setToolTip(label)
        else:
            self.setText(label)
            self.setToolTip("")
        self._update_style()

    def set_collapsed(self, collapsed: bool) -> None:
        self._is_collapsed = collapsed
        if collapsed:
            self.setText("")
            self.setToolTip(self._original_label)
            self.setFixedSize(48, 36)
        else:
            self.setText(self._original_label)
            self.setToolTip("")
            self.setFixedHeight(36)
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)
        self._update_style()

    def setChecked(self, checked: bool) -> None:
        super().setChecked(checked)
        self._update_style()
        self.update()

    def _update_style(self) -> None:
        is_rtl = self.layoutDirection() == Qt.LayoutDirection.RightToLeft
        if self._is_collapsed:
            pad_r, pad_l, align = "0px", "0px", "center"
        elif is_rtl:
            pad_r, pad_l, align = "40px", "10px", "right"
        else:
            pad_r, pad_l, align = "10px", "40px", "left"

        border_side = "border-right" if is_rtl else "border-left"
        if self.isChecked():
            self.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {tokens.SURFACE_SELECTED};
                    color: {tokens.TEXT};
                    border: 0px solid transparent;
                    {border_side}: 3px solid {tokens.ACCENT};
                    border-radius: {tokens.RADIUS_BUTTON}px;
                    padding-right: {pad_r};
                    padding-left: {pad_l};
                    text-align: {align};
                    font-size: 13px;
                    font-weight: 600;
                }}
                """
            )
        else:
            self.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: transparent;
                    color: {tokens.TEXT_MUTED};
                    border: 0px solid transparent;
                    border-radius: {tokens.RADIUS_BUTTON}px;
                    padding-right: {pad_r};
                    padding-left: {pad_l};
                    text-align: {align};
                    font-size: 13px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    color: {tokens.TEXT};
                    background-color: {tokens.SURFACE_HOVER};
                }}
                """
            )

    def paintEvent(self, event) -> None:  # type: ignore[override]
        super().paintEvent(event)
        painter = QPainter(self)
        color = tokens.ACCENT_HOVER if self.isChecked() else tokens.TEXT_MUTED
        if self._is_collapsed:
            icon_rect = QRectF((self.width() - 18.0) / 2.0, (self.height() - 18.0) / 2.0, 18.0, 18.0)
        elif self.layoutDirection() == Qt.LayoutDirection.RightToLeft:
            icon_rect = QRectF(self.width() - 30.0, (self.height() - 18.0) / 2.0, 18.0, 18.0)
        else:
            icon_rect = QRectF(12.0, (self.height() - 18.0) / 2.0, 18.0, 18.0)
        icons.draw_icon(painter, self.icon_name, icon_rect, color, stroke_width=1.6)
