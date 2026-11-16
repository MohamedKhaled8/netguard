"""Minimal Sparkline Widget for NetGuard AI.

32px high, 1.6px line, status color, last 24 samples.
Draws in with a left-to-right reveal animation on first show (1.6s ease-out).
"""

from __future__ import annotations
from typing import List, Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath
from PySide6.QtCore import Qt, Property, QPropertyAnimation, QEasingCurve
from app.ui import tokens


class Sparkline(QWidget):
    """32px high metric sparkline with reveal animation."""

    def __init__(
        self,
        samples: Optional[List[float]] = None,
        color: str = tokens.STATUS_OK,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.samples: List[float] = list(samples)[-24:] if samples is not None else []
        self.color = color
        self.setFixedHeight(32)
        self._reveal_progress = 1.0

    def get_reveal_progress(self) -> float:
        return self._reveal_progress

    def set_reveal_progress(self, val: float) -> None:
        self._reveal_progress = val
        self.update()

    reveal_progress = Property(float, get_reveal_progress, set_reveal_progress)

    def set_data(self, samples: Optional[List[float]], color: Optional[str] = None) -> None:
        if samples is not None:
            self.samples = list(samples)[-24:]
        if color:
            self.color = color
        self.update()

    def paintEvent(self, event) -> None:
        if not self.samples:
            return

        w = float(self.width())
        h = float(self.height())
        n = len(self.samples)

        if n == 1:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            pen = QPen(QColor(self.color), 1.6)
            painter.setPen(pen)
            painter.drawLine(0, int(h / 2), int(w), int(h / 2))
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setLayoutDirection(Qt.LeftToRight)

        min_val = min(self.samples)
        max_val = max(self.samples)
        val_range = max_val - min_val
        if val_range < 0.001:
            val_range = 2.0
            min_val -= 1.0

        pad_top = 4.0
        pad_bottom = 4.0
        usable_h = h - pad_top - pad_bottom

        max_x = w * self._reveal_progress
        if max_x <= 0:
            return

        path = QPainterPath()
        points = []
        for i, val in enumerate(self.samples):
            x = (i / (n - 1)) * w
            norm = (val - min_val) / val_range
            y = h - pad_bottom - (norm * usable_h)
            points.append((x, y))

        started = False
        for x, y in points:
            if x <= max_x:
                if not started:
                    path.moveTo(x, y)
                    started = True
                else:
                    path.lineTo(x, y)
            else:
                if points and started:
                    prev_x, prev_y = points[points.index((x, y)) - 1]
                    ratio = (max_x - prev_x) / (x - prev_x) if (x - prev_x) > 0 else 0
                    interp_y = prev_y + ratio * (y - prev_y)
                    path.lineTo(max_x, interp_y)
                break

        pen = QPen(QColor(self.color), 1.6)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
