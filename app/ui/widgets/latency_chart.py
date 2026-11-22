"""Custom Latency Chart Widget for NetGuard AI.

Precision custom QPainter chart:
- Left Y mono labels (0, 50, 100, 200)
- Reference dashed threshold with label 'حد الاستقرار المرجعي'
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
from app.ui.animation_clock import AnimationMasterClock


class LatencyPlotCanvas(QWidget):
    """QPainter canvas for the latency time series."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        from PySide6.QtWidgets import QSizePolicy
        self.setMinimumHeight(130)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.samples: List[float] = []
        self.timestamps: List[str] = []
        self.range_minutes: int = 60
        self.incident_index: Optional[int] = None
        self.incident_time_str: str = "—"
        self._reveal_progress = 1.0
        self._pulse_phase = 0.0

        self._init_default_data()

        self._is_paused = False
        if tokens.ANIMATIONS_ENABLED:
            AnimationMasterClock.get_instance().subscribe(self._on_pulse_tick)

    def set_paused(self, paused: bool) -> None:
        self._is_paused = paused
        if paused:
            AnimationMasterClock.get_instance().unsubscribe(self._on_pulse_tick)
        else:
            AnimationMasterClock.get_instance().subscribe(self._on_pulse_tick)

    def get_reveal_progress(self) -> float:
        return self._reveal_progress

    def set_reveal_progress(self, val: float) -> None:
        self._reveal_progress = val
        self.update()

    reveal_progress = Property(float, get_reveal_progress, set_reveal_progress)

    def _on_pulse_tick(self, delta_ms: float = 50.0) -> None:
        if getattr(self, "_is_paused", False):
            return
        clock = AnimationMasterClock.get_instance()
        if clock.is_low_resource_mode:
            return
        # Skip repaints when idle/static (no incident marker to pulse)
        if self.incident_index is None:
            return
        increment = 0.028 * (delta_ms / 50.0)
        self._pulse_phase = (self._pulse_phase + increment) % 1.0
        self.update()

    def _init_default_data(self) -> None:
        self.samples = []
        self.timestamps = []
        self.incident_index = None
        self.incident_time_str = "—"

    def set_data(self, samples: List[float], incident_idx: Optional[int] = None) -> None:
        if samples:
            self.samples = list(samples)[-60:]
            if incident_idx is not None:
                self.incident_index = incident_idx
            else:
                max_v = max(self.samples)
                if max_v >= 60.0:
                    self.incident_index = self.samples.index(max_v)
                else:
                    self.incident_index = None
        else:
            self.samples = []
            self.incident_index = None
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        if w < 100 or not self.samples:
            painter.setFont(tokens.get_sans_font(13, 400))
            painter.setPen(QPen(QColor(tokens.TEXT_MUTED)))
            painter.drawText(self.rect(), Qt.AlignCenter, "في انتظار تسجيل قياسات حقيقية…")
            return

        pad_left = 42.0
        pad_right = 24.0
        pad_top = 18.0
        pad_bottom = 20.0

        plot_w = w - pad_left - pad_right
        plot_h = h - pad_top - pad_bottom

        # -------------------------------------------------------------
        # 1. Y Axis Labels & Grid
        # -------------------------------------------------------------
        y_max = 200.0
        y_ticks = [0.0, 50.0, 100.0, 200.0]

        painter.setFont(tokens.get_mono_font(12, 400))
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

        # Label for threshold: subtle pill badge on the far right without colliding with wave
        painter.setFont(tokens.get_sans_font(10, 500))
        pill_rect = QRectF(pad_left + plot_w - 110, y_thresh - 17, 105, 15)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(tokens.SURFACE_INSET)))
        painter.drawRoundedRect(pill_rect, 3, 3)
        painter.setPen(QPen(QColor(tokens.TEXT_MUTED)))
        ref_ms = int(DEFAULT_THRESHOLDS.latency.external_warning_ms)
        painter.drawText(pill_rect, Qt.AlignCenter, f"حد مرجعي: {ref_ms} ms")

        # -------------------------------------------------------------
        # 2. X Axis (5 Mono Time Labels)
        # -------------------------------------------------------------
        painter.setFont(tokens.get_mono_font(12, 400))
        painter.setPen(QPen(QColor(tokens.TEXT_MUTED)))
        num_ticks = 5
        n_pts = len(self.samples)
        now = datetime.now()
        range_min = getattr(self, "range_minutes", 60)

        for i in range(num_ticks):
            frac = i / (num_ticks - 1)
            x_pos = pad_left + frac * plot_w
            idx = int(round(frac * (n_pts - 1)))
            if self.timestamps and idx < len(self.timestamps) and self.timestamps[idx]:
                time_txt = self.timestamps[idx]
            else:
                tick_dt = now - timedelta(minutes=int(round((1.0 - frac) * range_min)))
                time_txt = tick_dt.strftime("%H:%M")
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
                if self.incident_time_str and self.incident_time_str != "—":
                    chip_txt = f"{self.incident_time_str} · ارتفاع التأخير"
                else:
                    chip_txt = "ارتفاع التأخير"
                painter.setFont(tokens.get_sans_font(12, 500))
                chip_w = 130.0 if chip_txt != "ارتفاع التأخير" else 100.0
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

    def set_paused(self, paused: bool) -> None:
        if hasattr(self, "canvas") and hasattr(self.canvas, "set_paused"):
            self.canvas.set_paused(paused)
        elif hasattr(self, "_pulse_timer"):
            if paused and self._pulse_timer.isActive():
                self._pulse_timer.stop()
            elif not paused and not self._pulse_timer.isActive():
                self._pulse_timer.start(50)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("LatencyChartPanel")
        from PySide6.QtWidgets import QSizePolicy
        self.setMinimumHeight(375)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(f"""
            QFrame#LatencyChartPanel {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_PANEL}px;
            }}
            QFrame#LatencyChartPanel QLabel {{
                background: transparent;
                border: 0px solid transparent;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.lbl_title = QLabel("زمن الاستجابة")
        self.lbl_title.setFont(tokens.get_sans_font(16, 600))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT};")

        self.lbl_sub = QLabel("الوقت اللازم لوصول بياناتك إلى الإنترنت والعودة. الأقل أفضل.")
        self.lbl_sub.setFont(tokens.get_sans_font(12, 400))
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
        div.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border: none; max-height: 1px;")
        layout.addWidget(div)

        stats_row = QHBoxLayout()
        stats_row.setContentsMargins(0, 6, 0, 2)
        stats_row.setSpacing(10)

        def make_stat_col(label_txt: str, val_txt: str, val_color: str = tokens.TEXT) -> Tuple[QFrame, QLabel]:
            box = QFrame()
            box.setObjectName("LatencyStatBox")
            box.setFixedHeight(54)
            box.setStyleSheet("""
                QFrame#LatencyStatBox {
                    background: transparent;
                    border: 0px solid transparent;
                }
                QFrame#LatencyStatBox QLabel {
                    background: transparent;
                    border: 0px solid transparent;
                }
            """)
            col_l = QVBoxLayout(box)
            col_l.setContentsMargins(8, 6, 8, 6)
            col_l.setSpacing(2)
            col_l.setAlignment(Qt.AlignCenter)

            lbl = QLabel(label_txt)
            lbl.setFont(tokens.get_sans_font(11, 400))
            lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED}; border: none; background: transparent;")
            lbl.setAlignment(Qt.AlignCenter)

            val_lbl = QLabel(val_txt)
            val_lbl.setFont(tokens.get_mono_font(18, 600))
            val_lbl.setStyleSheet(f"color: {val_color}; border: none; background: transparent;")
            val_lbl.setAlignment(Qt.AlignCenter)

            col_l.addWidget(lbl)
            col_l.addWidget(val_lbl)
            return box, val_lbl

        col_avg, self.lbl_avg = make_stat_col("المتوسط", "—", tokens.TEXT)
        col_max, self.lbl_max = make_stat_col("أعلى قيمة", "—", tokens.TEXT)
        col_dur, self.lbl_dur = make_stat_col("مدة المشكلة", "—", tokens.TEXT)

        stats_row.addWidget(col_avg)
        stats_row.addWidget(col_max)
        stats_row.addWidget(col_dur)
        layout.addLayout(stats_row)

    def _on_range_changed(self, idx: int, label: str) -> None:
        ranges = [60, 360, 1440]
        self.canvas.range_minutes = ranges[idx] if idx < len(ranges) else 60
        self.canvas.set_data(self.canvas.samples)

    def update_telemetry(self, samples: List[float], avg_ms: float = 0.0, max_ms: float = 0.0, duration_str: str = "—") -> None:
        if samples:
            self.canvas.set_data(samples)
            self.lbl_avg.setText(f"{avg_ms:.0f} ms")
            self.lbl_max.setText(f"{max_ms:.0f} ms")
            self.lbl_dur.setText(duration_str)
        else:
            self.canvas.set_data([])
            self.lbl_avg.setText("—")
            self.lbl_max.setText("—")
            self.lbl_dur.setText("—")
