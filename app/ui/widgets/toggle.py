"""Toggle Switch component for NetGuard AI.

Clean 36x20 pill switch:
- Off: track #2A2E31, knob #ECEBE6 (or #9AA0A6)
- On: track #ECEBE6, knob #0E1012
"""

from __future__ import annotations
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QBrush, QPen
from PySide6.QtCore import Qt, Signal, Property, QPropertyAnimation, QEasingCurve
from app.ui import tokens


class ToggleSwitch(QWidget):
    """36x20 pill toggle switch."""

    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._checked = checked
        self._thumb_position = 1.0 if checked else 0.0
        self.setFixedSize(36, 20)
        self.setCursor(Qt.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"thumb_position", self)
        self._anim.setDuration(120)
        self._anim.setEasingCurve(QEasingCurve.OutQuad)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool) -> None:
        if self._checked != checked:
            self._checked = checked
            if tokens.ANIMATIONS_ENABLED:
                self._anim.stop()
                self._anim.setStartValue(self._thumb_position)
                self._anim.setEndValue(1.0 if checked else 0.0)
                self._anim.start()
            else:
                self._thumb_position = 1.0 if checked else 0.0
                self.update()
            self.toggled.emit(checked)

    def get_thumb_position(self) -> float:
        return self._thumb_position

    def set_thumb_position(self, pos: float) -> None:
        self._thumb_position = pos
        self.update()

    thumb_position = Property(float, get_thumb_position, set_thumb_position)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.setChecked(not self._checked)
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Track colors
        if self._checked:
            track_color = QColor(tokens.ACCENT)
            knob_color = QColor(tokens.BG)
        else:
            track_color = QColor(tokens.BAR_FUTURE)
            knob_color = QColor(tokens.TEXT_SECONDARY)

        # Draw track pill
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(track_color))
        painter.drawRoundedRect(0, 0, 36, 20, 10, 10)

        # Draw knob circle (14px diameter, margin 3px)
        # Thumb pos 0.0 -> x = 3; thumb pos 1.0 -> x = 19
        knob_x = 3.0 + self._thumb_position * 16.0
        knob_y = 3.0
        painter.setBrush(QBrush(knob_color))
        painter.drawEllipse(int(knob_x), int(knob_y), 14, 14)
