"""Custom Latency Chart Widget for NetGuard AI.

Precision custom QPainter chart:
- Left Y mono labels (0, 50, 100, 200)
- 50ms dashed threshold with label 'حد الجودة 50ms'
- 5 bottom mono time labels
- Accent line (1.8px) with 6% flat fill
- Incident spike redrawn in #FF6B5E (2.6px) with vertical line and clamped badge
- Live dot with continuously pulsing ring
- 3 summary stats underneath separated by 1px hairline
"""

from __future__ import annotations
import math
import time
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QPainterPath,
    QFontMetrics,
)
from PySide6.QtCore import (
    Qt,
    QRectF,
    QPointF,
    QTimer,
    Property,
    QPropertyAnimation,
    QEasingCurve,
)
from app.ui import tokens


class LatencyPlotCanvas(QWidget):
    """QPainter canvas for the latency time series."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(240)
        self.samples: List[float] = []
        self.timestamps: List[str] = []
        self.incident_index: Optional[int] = 38
        self.incident_time_str: str = "15:32"
        self._reveal_progress = 1.0
        self._pulse_phase = 0.0

        self._init_default_data()

        if tokens.ANIMATIONS_ENABLED:
            self._pulse_timer = QTimer(self)
            self._pulse_timer.timeout.connect(self._on_pulse_tick)
            self._pulse_timer.start(50)

    def get_reveal_progress(self) -> float:
        return self._reveal_progress

    def set_reveal_progress(self, val: float) -> None:
        self._reveal_progress = val
        self.update()

    reveal_progress = Property(float, get_reveal_progress, set_reveal_progress)

    def _on_pulse_tick(self) -> None:
        self._pulse_phase = (self._pulse_phase + 0.028) % 1.0
        self.update()

    def _init_default_data(self) -> None:
        data = []
        n = 60
        now = datetime.now()
        times = []
        spike_idx = 38
        self.incident_index = spike_idx

        for i in range(n):
            dt = now - timedelta(minutes=(n - 1 - i))
            times.append(dt.strftime("%H:%M"))

            if i < spike_idx - 3:
                val = 22.0 + 3.0 * math.sin(i * 0.4)
            elif i == spike_idx - 2:
                val = 45.0
            elif i == spike_idx - 1:
                val = 110.0
            elif i == spike_idx:
                val = 182.0  # Peak
                self.incident_time_str = "15:32"
            elif i == spike_idx + 1:
                val = 90.0
            elif i == spike_idx + 2:
                val = 40.0
            else:
                val = 24.0 + 2.5 * math.cos(i * 0.3)
            data.append(val)

        self.samples = data
        self.timestamps = times

    def set_data(self, samples: List[float], incident_idx: Optional[int] = None) -> None:
        if samples and len(samples) >= 15:
            self.samples = list(samples)
            if incident_idx is not None:
                self.incident_index = incident_idx
            else:
                max_v = max(self.samples)
                if max_v >= 60.0:
                    self.incident_index = self.samples.index(max_v)
                else:
                    self.incident_index = None
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        if w < 100 or not self.samples:
            return

        pad_left = 38.0
        pad_right = 24.0
        pad_top = 40.0
        pad_bottom = 28.0

        plot_w = w - pad_left - pad_right
        plot_h = h - pad_top - pad_bottom

        # -------------------------------------------------------------
        # 1. Y Axis Labels & Grid
        # -------------------------------------------------------------
        y_max = 200.0
        y_ticks = [0.0, 50.0, 100.0, 200.0]

        painter.setFont(tokens.get_mono_font(11, 400))
        painter.setPen(QPen(QColor(tokens.TEXT_MUTED)))

        for val in y_ticks:
            y_pos = pad_top + plot_h - (val / y_max) * plot_h
            painter.drawText(
                QRectF(0, y_pos - 8, pad_left - 8, 16),
                Qt.AlignRight | Qt.AlignVCenter,
                f"{int(val)}",
            )

        # Bottom axis line
        bottom_y = pad_top + plot_h
        painter.setPen(QPen(QColor(tokens.LINE_STRONG), 1.0))
        painter.drawLine(QPointF(pad_left, bottom_y), QPointF(pad_left + plot_w, bottom_y))

        # 50ms Quality Threshold (Dashed)
        y_thresh = pad_top + plot_h - (50.0 / y_max) * plot_h
        dash_pen = QPen(QColor(tokens.LINE_THRESHOLD), 1.0, Qt.DashLine)
        painter.setPen(dash_pen)
        painter.drawLine(QPointF(pad_left, y_thresh), QPointF(pad_left + plot_w, y_thresh))

        # Label for 50ms threshold
        painter.setFont(tokens.get_sans_font(11, 400))
        painter.setPen(QPen(QColor(tokens.TEXT_MUTED)))
        painter.drawText(
            QRectF(pad_left + plot_w - 110, y_thresh - 16, 110, 14),
            Qt.AlignRight | Qt.AlignVCenter,
            "حد الجودة 50ms",
        )

        # -------------------------------------------------------------
        # 2. X Axis (5 Mono Time Labels)
        # -------------------------------------------------------------
        painter.setFont(tokens.get_mono_font(11, 400))
        painter.setPen(QPen(QColor(tokens.TEXT_MUTED)))
        num_ticks = 5
        n_pts = len(self.samples)

        for i in range(num_ticks):
            frac = i / (num_ticks - 1)
            x_pos = pad_left + frac * plot_w
            idx = int(round(frac * (n_pts - 1)))
            time_txt = self.timestamps[idx] if idx < len(self.timestamps) else "16:00"
            painter.drawText(
                QRectF(x_pos - 25, bottom_y + 6, 50, 16),
                Qt.AlignCenter,
                time_txt,
            )

        # -------------------------------------------------------------
        # 3. Time Series Curve & Fill
        # -------------------------------------------------------------
        points: List[QPointF] = []
        for i, val in enumerate(self.samples):
            x = pad_left + (i / (n_pts - 1)) * plot_w
            clamped_val = min(y_max, max(0.0, val))
            y = pad_top + plot_h - (clamped_val / y_max) * plot_h
            points.append(QPointF(x, y))

        max_allowed_x = pad_left + plot_w * self._reveal_progress
        visible_points = [p for p in points if p.x() <= max_allowed_x]

        if len(visible_points) >= 2:
            fill_path = QPainterPath()
            fill_path.moveTo(visible_points[0].x(), bottom_y)
            for p in visible_points:
                fill_path.lineTo(p)
            fill_path.lineTo(visible_points[-1].x(), bottom_y)
            fill_path.closeSubpath()

            fill_color = QColor(tokens.ACCENT)
            fill_color.setAlpha(int(255 * 0.06))
            painter.fillPath(fill_path, QBrush(fill_color))

            line_path = QPainterPath()
            line_path.moveTo(visible_points[0])
            for p in visible_points[1:]:
                line_path.lineTo(p)

            line_pen = QPen(QColor(tokens.ACCENT), 1.8)
            line_pen.setCapStyle(Qt.RoundCap)
            line_pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(line_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(line_path)

        # -------------------------------------------------------------
        # 4. Incident Highlight
        # -------------------------------------------------------------
        if self.incident_index is not None and 0 <= self.incident_index < len(points):
            inc_pt = points[self.incident_index]
            if inc_pt.x() <= max_allowed_x:
                v_color = QColor(tokens.STATUS_BAD)
                v_color.setAlpha(128)
                painter.setPen(QPen(v_color, 1.0))
                painter.drawLine(QPointF(inc_pt.x(), pad_top), QPointF(inc_pt.x(), bottom_y))

                start_i = max(0, self.incident_index - 3)
                end_i = min(len(points) - 1, self.incident_index + 3)
                bad_path = QPainterPath()
                bad_path.moveTo(points[start_i])
                for j in range(start_i + 1, end_i + 1):
                    bad_path.lineTo(points[j])

                bad_pen = QPen(QColor(tokens.STATUS_BAD), 2.6)
                bad_pen.setCapStyle(Qt.RoundCap)
                bad_pen.setJoinStyle(Qt.RoundJoin)
                painter.setPen(bad_pen)
                painter.drawPath(bad_path)

                # Incident Chip badge: "15:32 · ارتفاع التأخير"
                chip_txt = f"{self.incident_time_str} · ارتفاع التأخير"
                painter.setFont(tokens.get_sans_font(12, 500))
                chip_w = 130.0
                chip_h = 24.0
                chip_x = max(pad_left, min(w - pad_right - chip_w, inc_pt.x() - chip_w / 2))
                chip_y = max(6.0, inc_pt.y() - chip_h - 10.0)

                chip_rect = QRectF(chip_x, chip_y, chip_w, chip_h)
                painter.setPen(QPen(QColor(tokens.BAD_SOFT_BORDER), 1.0))
                painter.setBrush(QBrush(QColor(tokens.BAD_SOFT_BG)))
                painter.drawRoundedRect(chip_rect, 8.0, 8.0)

                painter.setPen(QPen(QColor(tokens.BAD_SOFT_TEXT)))
                painter.drawText(chip_rect, Qt.AlignCenter, chip_txt)

        # -------------------------------------------------------------
        # 5. Live Dot & Pulsing Ring
        # -------------------------------------------------------------
        if points and self._reveal_progress >= 0.95:
            last_pt = points[-1]
            if tokens.ANIMATIONS_ENABLED:
                ring_radius = 5.0 + self._pulse_phase * 11.0
                ring_alpha = int(255 * (0.6 * (1.0 - self._pulse_phase)))
                ring_color = QColor(tokens.ACCENT)
                ring_color.setAlpha(max(0, min(255, ring_alpha)))
                painter.setPen(QPen(ring_color, 1.2))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(last_pt, ring_radius, ring_radius)

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(tokens.ACCENT)))
            painter.drawEllipse(last_pt, 5.0, 5.0)


class LatencyChart(QFrame):
    """Complete Latency Chart Panel Widget with Range Switch & Stats Footer."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("LatencyChartPanel")
        self.setStyleSheet(f"""
            QFrame#LatencyChartPanel {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_PANEL}px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        self.lbl_title = QLabel("زمن الاستجابة")
        self.lbl_title.setFont(tokens.get_sans_font(18, 600))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT};")

        self.lbl_sub = QLabel("الوقت اللازم لوصول بياناتك إلى الإنترنت والعودة. الأقل أفضل.")
        self.lbl_sub.setFont(tokens.get_sans_font(13, 400))
        self.lbl_sub.setStyleSheet(f"color: {tokens.TEXT_MUTED};")

        title_col.addWidget(self.lbl_title)
        title_col.addWidget(self.lbl_sub)
        header_row.addLayout(title_col)

        header_row.addStretch()

        from app.ui.widgets.segmented import SegmentedControl
        self.range_switch = SegmentedControl(["60 دقيقة", "6 ساعات", "24 ساعة"], initial_index=0)
        self.range_switch.current_changed.connect(self._on_range_changed)
        header_row.addWidget(self.range_switch)

        layout.addLayout(header_row)

        self.canvas = LatencyPlotCanvas(self)
        layout.addWidget(self.canvas)

        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet(f"background-color: {tokens.LINE}; border: none; max-height: 1px;")
        layout.addWidget(div)

        stats_row = QHBoxLayout()
        stats_row.setContentsMargins(10, 4, 10, 4)

        def make_stat_col(label_txt: str, val_txt: str, val_color: str = tokens.TEXT) -> Tuple[QWidget, QLabel]:
            col_w = QWidget()
            col_l = QVBoxLayout(col_w)
            col_l.setContentsMargins(0, 0, 0, 0)
            col_l.setSpacing(2)
            col_l.setAlignment(Qt.AlignCenter)

            lbl = QLabel(label_txt)
            lbl.setFont(tokens.get_sans_font(12, 400))
            lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
            lbl.setAlignment(Qt.AlignCenter)

            val_lbl = QLabel(val_txt)
            val_lbl.setFont(tokens.get_mono_font(20, 500))
            val_lbl.setStyleSheet(f"color: {val_color};")
            val_lbl.setAlignment(Qt.AlignCenter)

            col_l.addWidget(lbl)
            col_l.addWidget(val_lbl)
            return col_w, val_lbl

        col_avg, self.lbl_avg = make_stat_col("المتوسط", "ms 29", tokens.TEXT)
        col_max, self.lbl_max = make_stat_col("أعلى قيمة", "ms 182", tokens.BAD_SOFT_TEXT)
        col_dur, self.lbl_dur = make_stat_col("مدة المشكلة", "41 ث", tokens.TEXT)

        stats_row.addWidget(col_avg)
        stats_row.addWidget(col_max)
        stats_row.addWidget(col_dur)
        layout.addLayout(stats_row)

    def _on_range_changed(self, idx: int, label: str) -> None:
        self.canvas.set_data(self.canvas.samples)

    def update_telemetry(self, samples: List[float], avg_ms: float = 29.0, max_ms: float = 182.0, duration_str: str = "41 ث") -> None:
        if samples and len(samples) >= 15:
            self.canvas.set_data(samples)
            self.lbl_avg.setText(f"ms {avg_ms:.0f}")
            self.lbl_max.setText(f"ms {max_ms:.0f}")
            self.lbl_dur.setText(duration_str)
