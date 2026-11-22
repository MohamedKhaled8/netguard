"""Sidebar Navigation Item component for NetGuard AI.

Clean monochrome line icon (18px, 1.6px stroke) + text label.
Active: raised surface, text #ECEBE6, 3px accent edge, radius 10px.
Inactive: transparent, text #9AA0A6. Hover: text #ECEBE6.
Strictly zero emoji, zero colored/filled icons.
"""

from __future__ import annotations
from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath
from PySide6.QtCore import Qt, QPointF, QRectF
from app.ui import tokens


class NavItem(QPushButton):
    """Sidebar navigation item with custom monochrome line icon."""

    def __init__(self, icon_name: str, label: str, index: int, parent=None) -> None:
        super().__init__(label, parent)
        self.icon_name = icon_name
        self.index = index
        self._original_label = label
        self._is_collapsed = False
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)
        self.setFont(tokens.get_sans_font(14, 500))
        self._update_style()

    def set_collapsed(self, collapsed: bool) -> None:
        self._is_collapsed = collapsed
        if collapsed:
            self.setText("")
            self.setToolTip(self._original_label)
            self.setFixedSize(48, 44)
        else:
            self.setText(self._original_label)
            self.setToolTip("")
            self.setFixedHeight(44)
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)
        self._update_style()

    def setChecked(self, checked: bool) -> None:
        super().setChecked(checked)
        self._update_style()
        self.update()

    def _update_style(self) -> None:
        pad_r = "0px" if self._is_collapsed else "42px"
        pad_l = "0px" if self._is_collapsed else "12px"
        align = "center" if self._is_collapsed else "right"
        if self.isChecked():
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {tokens.SURFACE_SELECTED};
                    color: {tokens.TEXT};
                    border: none;
                    border-right: 3px solid {tokens.ACCENT};
                    border-radius: {tokens.RADIUS_BUTTON}px;
                    padding-right: {pad_r};
                    padding-left: {pad_l};
                    text-align: {align};
                    font-size: 14px;
                    font-weight: 500;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {tokens.TEXT_MUTED};
                    border: none;
                    border-radius: {tokens.RADIUS_BUTTON}px;
                    padding-right: {pad_r};
                    padding-left: {pad_l};
                    text-align: {align};
                    font-size: 14px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    color: {tokens.TEXT};
                    background-color: {tokens.SURFACE_HOVER};
                }}
            """)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Icon color matches text state
        if self.isChecked():
            icon_color = QColor(tokens.TEXT)
        else:
            icon_color = QColor(tokens.TEXT if self.underMouse() else tokens.TEXT_MUTED)

        pen = QPen(icon_color, 1.6)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        # In RTL, icon is placed at the right side of the button
        w = float(self.width())
        h = float(self.height())
        icon_cx = w - 24.0
        icon_cy = h / 2.0
        s = 8.0  # half-size

        path = QPainterPath()

        if self.icon_name == "home":
            # House
            path.moveTo(icon_cx - s, icon_cy + 2)
            path.lineTo(icon_cx, icon_cy - s + 1)
            path.lineTo(icon_cx + s, icon_cy + 2)
            path.moveTo(icon_cx - s + 2, icon_cy + 1)
            path.lineTo(icon_cx - s + 2, icon_cy + s)
            path.lineTo(icon_cx + s - 2, icon_cy + s)
            path.lineTo(icon_cx + s - 2, icon_cy + 1)

        elif self.icon_name == "activity":
            # Pulse
            path.moveTo(icon_cx - s, icon_cy)
            path.lineTo(icon_cx - 3, icon_cy)
            path.lineTo(icon_cx - 1, icon_cy - s + 2)
            path.lineTo(icon_cx + 2, icon_cy + s - 2)
            path.lineTo(icon_cx + 4, icon_cy)
            path.lineTo(icon_cx + s, icon_cy)

        elif self.icon_name == "shield":
            # Shield
            path.moveTo(icon_cx, icon_cy - s)
            path.lineTo(icon_cx + s - 1, icon_cy - s + 3)
            path.lineTo(icon_cx + s - 2, icon_cy + 2)
            path.quadTo(icon_cx, icon_cy + s + 1, icon_cx, icon_cy + s + 1)
            path.quadTo(icon_cx - s + 2, icon_cy + 2, icon_cx - s + 1, icon_cy - s + 3)
            path.closeSubpath()

        elif self.icon_name == "globe":
            # Globe
            painter.drawEllipse(QPointF(icon_cx, icon_cy), s - 1, s - 1)
            painter.drawLine(QPointF(icon_cx - s + 1, icon_cy), QPointF(icon_cx + s - 1, icon_cy))
            painter.drawEllipse(QPointF(icon_cx, icon_cy), (s - 1) / 2.0, s - 1)
            return

        elif self.icon_name == "traffic":
            # Up-Down arrows
            # Up arrow (left)
            painter.drawLine(QPointF(icon_cx - 3, icon_cy + s - 2), QPointF(icon_cx - 3, icon_cy - s + 2))
            painter.drawLine(QPointF(icon_cx - 6, icon_cy - s + 5), QPointF(icon_cx - 3, icon_cy - s + 2))
            painter.drawLine(QPointF(icon_cx, icon_cy - s + 5), QPointF(icon_cx - 3, icon_cy - s + 2))
            # Down arrow (right)
            painter.drawLine(QPointF(icon_cx + 4, icon_cy - s + 2), QPointF(icon_cx + 4, icon_cy + s - 2))
            painter.drawLine(QPointF(icon_cx + 1, icon_cy + s - 5), QPointF(icon_cx + 4, icon_cy + s - 2))
            painter.drawLine(QPointF(icon_cx + 7, icon_cy + s - 5), QPointF(icon_cx + 4, icon_cy + s - 2))
            return

        elif self.icon_name == "clock":
            # Clock
            painter.drawEllipse(QPointF(icon_cx, icon_cy), s - 1, s - 1)
            painter.drawLine(QPointF(icon_cx, icon_cy), QPointF(icon_cx, icon_cy - s + 3))
            painter.drawLine(QPointF(icon_cx, icon_cy), QPointF(icon_cx + s - 3, icon_cy))
            return

        elif self.icon_name == "sliders":
            # Sliders
            painter.drawLine(QPointF(icon_cx - s, icon_cy - 4), QPointF(icon_cx + s, icon_cy - 4))
            painter.drawLine(QPointF(icon_cx - s, icon_cy + 4), QPointF(icon_cx + s, icon_cy + 4))
            # Thumbs
            painter.drawLine(QPointF(icon_cx - 2, icon_cy - 7), QPointF(icon_cx - 2, icon_cy - 1))
            painter.drawLine(QPointF(icon_cx + 3, icon_cy + 1), QPointF(icon_cx + 3, icon_cy + 7))
            return

        painter.drawPath(path)
