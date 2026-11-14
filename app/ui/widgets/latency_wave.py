"""Cinematic Real-Time Latency Wave Widget.

High-end Dribbble / Linear-inspired telemetry visualization:
- Smooth antialiased cubic bezier curve.
- Glowing vertical gradient fill (Cyan / Emerald -> transparent).
- Real-time latency statistics (Current, Min, Max, Jitter).
- Borderless dark glass aesthetic with subtle horizontal reference lines.
"""

from __future__ import annotations
from typing import List
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QLinearGradient, QFont
from PySide6.QtCore import Qt, QPointF


class LatencyWaveWidget(QFrame):
    """High-craft real-time latency wave visualization."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #0c101a;
                border: 1px solid #161f30;
                border-radius: 12px;
            }
        """)
        self.setMinimumHeight(170)

        self._samples: List[float] = [24.0] * 30
        self._current_val: float = 24.0
        self._min_val: float = 20.0
        self._max_val: float = 28.0
        self._jitter_val: float = 1.2

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 12)
        main_layout.setSpacing(6)

        # Header Row: Title & Stats
        header = QHBoxLayout()
        title_lbl = QLabel("موجة استقرار الاتصال اللحظية (Live Latency Wave)")
        title_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #8b949e;")
        header.addWidget(title_lbl)
        header.addStretch()

        self.stats_lbl = QLabel("الحالي: 24.0ms · الأدنى: 20ms · التذبذب: 1.2ms")
        self.stats_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #00e599;")
        header.addWidget(self.stats_lbl)
        main_layout.addLayout(header)

        # Wave canvas placeholder (we paint in paintEvent)
        self.canvas = _WaveCanvas(self)
        main_layout.addWidget(self.canvas, stretch=1)

    def update_samples(self, samples: List[float], jitter: float = 1.2) -> None:
        if not samples:
            return
        self._samples = samples[-40:]  # last 40 samples
        self._current_val = samples[-1]
        self._min_val = min(self._samples)
        self._max_val = max(self._samples)
        self._jitter_val = jitter

        stat_color = "#00e599" if self._current_val < 50.0 else ("#e3b341" if self._current_val < 90.0 else "#f85149")
        self.stats_lbl.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {stat_color};")
        self.stats_lbl.setText(
            f"البنج اللحظي: {self._current_val:.1f}ms  ·  الأدنى: {self._min_val:.0f}ms  ·  الأقصى: {self._max_val:.0f}ms  ·  التذبذب: {self._jitter_val:.1f}ms"
        )
        self.canvas.set_data(self._samples)


class _WaveCanvas(QWidget):
    """Drawing area for the smooth cubic wave."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.samples: List[float] = [24.0] * 30

    def set_data(self, samples: List[float]) -> None:
        self.samples = samples
        self.update()

    def paintEvent(self, event) -> None:
        if not self.samples:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())

        # Determine scale bounds
        min_y = max(0.0, min(self.samples) * 0.8)
        max_y = max(min_y + 10.0, max(self.samples) * 1.2)
        range_y = max(1.0, max_y - min_y)

        # 1. Subtle horizontal grid lines
        grid_pen = QPen(QColor(255, 255, 255, 12), 1.0, Qt.DashLine)
        painter.setPen(grid_pen)
        for ratio in (0.25, 0.5, 0.75):
            y_pos = h * ratio
            painter.drawLine(QPointF(0, y_pos), QPointF(w, y_pos))

        # Calculate coordinates
        n = len(self.samples)
        step_x = w / float(max(1, n - 1))
        points: List[QPointF] = []
        for i, val in enumerate(self.samples):
            px = i * step_x
            normalized = (val - min_y) / range_y
            py = h - (normalized * (h - 16.0) + 8.0)
            points.append(QPointF(px, py))

        if len(points) < 2:
            return

        # 2. Build smooth cubic path
        path = QPainterPath()
        path.moveTo(points[0])

        for i in range(len(points) - 1):
            p0 = points[i]
            p1 = points[i + 1]
            ctrl1 = QPointF(p0.x() + (p1.x() - p0.x()) / 2.0, p0.y())
            ctrl2 = QPointF(p0.x() + (p1.x() - p0.x()) / 2.0, p1.y())
            path.cubicTo(ctrl1, ctrl2, p1)

        # 3. Fill Gradient under the curve
        fill_path = QPainterPath(path)
        fill_path.lineTo(w, h)
        fill_path.lineTo(0, h)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QColor(0, 229, 153, 50))  # Emerald top
        grad.setColorAt(1.0, QColor(0, 229, 153, 0))   # Fade to bottom
        painter.fillPath(fill_path, QBrush(grad))

        # 4. Stroke Curve
        curve_pen = QPen(QColor("#00e599"), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(curve_pen)
        painter.drawPath(path)

        # 5. Glowing End Dot
        last_pt = points[-1]
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 229, 153, 70))
        painter.drawEllipse(last_pt, 6, 6)
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(last_pt, 3, 3)
