"""48-bar daily stability strip widget for NetGuard AI.

One bar per 30 minutes (00:00 -> 24:00 strictly LTR).
Bars differ by height and color across 5 canonical states:
- Healthy: 44px #5FD38D
- Slow: 26px #F5B942
- Bad: 40px #FF6B5E
- No-Data: 9px #2C3033
- Future: 11px #2A2E31
Interactive hover tooltips and integrated 5-point mono time axis.
"""

from __future__ import annotations
from typing import List, Dict, Any
from datetime import datetime
from PySide6.QtWidgets import QFrame, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolTip
from PySide6.QtGui import QPainter, QColor, QBrush, QFont
from PySide6.QtCore import Qt, QPoint, QRectF
from app.ui import tokens


class DayStripCanvas(QWidget):
    """Custom canvas painting the 48 vertical bars and LTR time axis."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.bar_states: List[str] = ["no-data"] * 48
        self._init_default_day()
        # Removed setMinimumWidth/MaximumWidth for responsive wrapping in dashboard grid

    def _init_default_day(self) -> None:
        now = datetime.now()
        current_slot = min(47, (now.hour * 60 + now.minute) // 30)
        for i in range(48):
            if i > current_slot:
                self.bar_states[i] = "future"
            else:
                self.bar_states[i] = "no-data"

    def set_data(self, states: List[str]) -> None:
        if states:
            self.bar_states = list(states)[:48]
            while len(self.bar_states) < 48:
                self.bar_states.append("future")
            self.update()

    def _get_slot_rect(self, index: int, total_width: float) -> QRectF:
        gap = max(1.5, min(2.5, total_width / 200.0))
        n = 48
        bar_w = max(2.0, (total_width - (n - 1) * gap) / n)
        x = index * (bar_w + gap)
        h = 44.0

        state = self.bar_states[index]
        if state == "healthy":
            bar_h = 44.0
        elif state == "slow":
            bar_h = 26.0
        elif state == "bad":
            bar_h = 40.0
        elif state == "no-data":
            bar_h = 9.0
        elif state == "future":
            bar_h = 11.0
        else:
            bar_h = 9.0

        y = h - bar_h
        return QRectF(x, y, bar_w, bar_h)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setLayoutDirection(Qt.LeftToRight)

        w = float(self.width())
        # 1. Draw 48 Bars (strictly LTR: index 0 at left x=0, index 47 at right)
        for i, state in enumerate(self.bar_states):
            rect = self._get_slot_rect(i, w)
            if state == "healthy":
                color = QColor(tokens.STATUS_OK)
            elif state == "slow":
                color = QColor(tokens.STATUS_WARN)
            elif state == "bad":
                color = QColor(tokens.STATUS_BAD)
            elif state == "no-data":
                color = QColor(tokens.LINE_STRONG)
            elif state == "future":
                color = QColor(tokens.BAR_FUTURE)
            else:
                color = QColor(tokens.LINE_STRONG)

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(rect, 2.0, 2.0)

        # 2. Draw Bottom Mono Time Axis (strictly LTR: 00:00 -> 24:00)
        painter.setFont(tokens.get_mono_font(12, 400))
        painter.setPen(QColor(tokens.TEXT_MUTED))

        axis_points = [
            (0.0, "00:00"),
            (0.25, "06:00"),
            (0.50, "12:00"),
            (0.75, "18:00"),
            (1.0, "24:00"),
        ]
        label_y = 50.0
        for frac, txt in axis_points:
            x_pos = frac * w
            rect = QRectF(max(0.0, min(w - 56.0, x_pos - 28.0)), label_y, 56.0, 18.0)
            painter.drawText(rect, Qt.AlignCenter | Qt.AlignVCenter, txt)

    def mouseMoveEvent(self, event) -> None:
        pos_x = event.position().x()
        w = float(self.width())
        gap = max(1.5, min(2.5, w / 200.0))
        n = 48
        bar_w = max(2.0, (w - (n - 1) * gap) / n)
        slot_w = bar_w + gap

        index = int(pos_x // slot_w)
        if 0 <= index < 48:
            hour = (index * 30) // 60
            minute = (index * 30) % 60
            time_str = f"{hour:02d}:{minute:02d}"
            state = self.bar_states[index]
            status_desc = {
                "healthy": "سليم",
                "slow": "تباطؤ",
                "bad": "عطل / حرج",
                "no-data": "لا توجد بيانات",
                "future": "لم يحن بعد",
            }.get(state, "لا توجد بيانات")

            tip_text = f"{time_str} — {status_desc}"
            QToolTip.showText(event.globalPosition().toPoint(), tip_text, self)
        super().mouseMoveEvent(event)


class DayStrip(QWidget):
    """Complete 48-bar widget with top caption and legend."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(260)
        self.setMaximumWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Top header row: "اليوم، كل 30 دقيقة" on right, legend on left
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        lbl_caption = QLabel("اليوم، كل 30 دقيقة")
        lbl_caption.setFont(tokens.get_sans_font(12, 400))
        lbl_caption.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        top_row.addWidget(lbl_caption)

        top_row.addStretch()

        # Legend items
        legend_layout = QHBoxLayout()
        legend_layout.setSpacing(12)

        def make_legend(color: str, label_text: str) -> QWidget:
            w = QWidget()
            h_layout = QHBoxLayout(w)
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(6)
            dot = QFrame()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
            txt = QLabel(label_text)
            txt.setFont(tokens.get_sans_font(12, 400))
            txt.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
            h_layout.addWidget(dot)
            h_layout.addWidget(txt)
            return w

        legend_layout.addWidget(make_legend(tokens.STATUS_OK, "سليم"))
        legend_layout.addWidget(make_legend(tokens.STATUS_WARN, "تباطؤ"))
        legend_layout.addWidget(make_legend(tokens.STATUS_BAD, "انقطاع"))
        top_row.addLayout(legend_layout)

        layout.addLayout(top_row)

        # 48-bar Canvas with integrated LTR axis
        self.canvas = DayStripCanvas(self)
        layout.addWidget(self.canvas)

    def set_data(self, states: List[str]) -> None:
        self.canvas.set_data(states)
