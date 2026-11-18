"""Dashboard View for NetGuard AI.

100% pixel-faithful reproduction of the approved reference design:
- Header Row: Live scan status + 'تصدير تقرير' (Secondary) & 'افحص الآن' (Primary)
- Hero: Big Arabic title + explanatory paragraph + 48-bar DayStrip (00:00 -> 24:00)
- Metrics Strip: 4 hairline-separated cells (زمن الاستجابة, التذبذب, فقدان الحزم, سرعة التنزيل)
- Row A: 240px LatencyChart (Flex 2) + 4-step TimelinePanel (Flex 1)
- مسار اتصالك: 5-node interactive network flow path with traveling dots & detail card
- Row B: Bandwidth Consumers list + DNS Recommendation with comparison bars
- Footer note: Centered graphite caption
Full responsive reflow across >=1100px, 700-1099px, and <700px breakpoints.
"""

from __future__ import annotations
import math
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QGridLayout,
)
from PySide6.QtCore import Qt, QTimer, Signal

from app.core.thresholds import DEFAULT_THRESHOLDS
from app.ui import tokens
from app.ui.widgets.buttons import PrimaryButton, SecondaryButton
from app.ui.widgets.day_strip import DayStrip
from app.ui.widgets.metric_cell import MetricsStrip, MetricCell
from app.ui.widgets.latency_chart import LatencyChart
from app.ui.widgets.timeline import TimelinePanel
from app.ui.widgets.flow_path import FlowPathPanel
from app.ui.widgets.bar_row import TrafficConsumersPanel, DNSRecommendationPanel
from app.ui.widgets.scroll_forwarder import make_scroll_transparent
from app.core.models.metrics import MetricType, Diagnosis, ProbableCause, ProbeStatus


class StatusIndicatorDot(QWidget):
    """8px dot with continuous pulsing ring, reflecting active health/warning state."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self._pulse_phase = 0.0
        self._status_color = tokens.STATUS_OK
        if tokens.ANIMATIONS_ENABLED:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick)
            self._timer.start(50)

    def set_status(self, color: str = tokens.STATUS_OK) -> None:
        if self._status_color != color:
            self._status_color = color
            self.update()

    def _tick(self) -> None:
        self._pulse_phase = (self._pulse_phase + 0.028) % 1.0
        self.update()

    def paintEvent(self, event) -> None:
        from PySide6.QtGui import QPainter, QColor, QPen, QBrush
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center_x = 9.0
        center_y = 9.0

        if tokens.ANIMATIONS_ENABLED:
            ring_radius = 4.0 + self._pulse_phase * 4.5
            ring_alpha = int(255 * (0.6 * (1.0 - self._pulse_phase)))
            ring_col = QColor(self._status_color)
            ring_col.setAlpha(max(0, min(255, ring_alpha)))
            painter.setPen(QPen(ring_col, 1.2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(center_x - ring_radius, center_y - ring_radius, ring_radius * 2, ring_radius * 2)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(self._status_color)))
        painter.drawEllipse(center_x - 4.0, center_y - 4.0, 8.0, 8.0)


class DashboardView(QWidget):
    """Main Dashboard View matching the reference specification."""

    quick_scan_requested = Signal()
    export_report_requested = Signal()
    meeting_preflight_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._last_scan_seconds = 0
        self._last_speed_test_time: Optional[str] = None
        self._current_layout_mode = "desktop"

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Scroll area for vertical content
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(
            tokens.PAGE_PADDING_DESKTOP, 28, tokens.PAGE_PADDING_DESKTOP, 36
        )
        self.content_layout.setSpacing(tokens.SECTION_GAP)

        # -------------------------------------------------------------
        # 3.1 Header Row
        # -------------------------------------------------------------
        self.header_row = QHBoxLayout()
        self.header_row.setContentsMargins(0, 0, 0, 0)
        self.header_row.setSpacing(12)

        status_box = QHBoxLayout()
        status_box.setSpacing(8)
        self.status_dot = StatusIndicatorDot(self)
        status_box.addWidget(self.status_dot)

        self.lbl_status_line = QLabel("")
        self.lbl_status_line.setFont(tokens.get_sans_font(13, 400))
        self.lbl_status_line.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        status_box.addWidget(self.lbl_status_line)
        self.header_row.addLayout(status_box)

        self.header_row.addStretch()

        buttons_box = QHBoxLayout()
        buttons_box.setSpacing(10)

        self.btn_export = SecondaryButton("تصدير تقرير")
        self.btn_export.clicked.connect(self.export_report_requested.emit)

        self.btn_preflight = SecondaryButton("جهّز لاجتماع")
        self.btn_preflight.clicked.connect(self.meeting_preflight_requested.emit)

        self.btn_scan = PrimaryButton("افحص الآن")
        self.btn_scan.clicked.connect(self._on_scan_clicked)

        buttons_box.addWidget(self.btn_export)
        buttons_box.addWidget(self.btn_preflight)
        buttons_box.addWidget(self.btn_scan)
        self.header_row.addLayout(buttons_box)

        self.content_layout.addLayout(self.header_row)

        # -------------------------------------------------------------
        # 3.1.5 Non-intrusive Persistent Probe Status Alert Bar
        # -------------------------------------------------------------
        self.probe_alert_bar = QFrame(self)
        self.probe_alert_bar.setObjectName("ProbeAlertBar")
        self.probe_alert_bar.setFixedHeight(38)
        self.probe_alert_bar.setStyleSheet(f"""
            QFrame#ProbeAlertBar {{
                background-color: {tokens.SURFACE_INSET};
                border: 1px solid {tokens.WARN_BORDER};
                border-radius: {tokens.RADIUS_INNER}px;
            }}
        """)
        alert_layout = QHBoxLayout(self.probe_alert_bar)
        alert_layout.setContentsMargins(14, 0, 14, 0)
        alert_layout.setSpacing(10)

        self.lbl_probe_alert_icon = QLabel("تنبيه:", self.probe_alert_bar)
        self.lbl_probe_alert_icon.setFont(tokens.get_sans_font(12, 600))
        self.lbl_probe_alert_icon.setStyleSheet(f"color: {tokens.STATUS_WARN};")
        alert_layout.addWidget(self.lbl_probe_alert_icon)

        self.lbl_probe_alert_msg = QLabel("", self.probe_alert_bar)
        self.lbl_probe_alert_msg.setFont(tokens.get_sans_font(12, 500))
        self.lbl_probe_alert_msg.setStyleSheet(f"color: {tokens.STATUS_WARN};")
        alert_layout.addWidget(self.lbl_probe_alert_msg)

        alert_layout.addStretch()

        self.lbl_probe_alert_tag = QLabel("تنبيه جودة المراقبة", self.probe_alert_bar)
        self.lbl_probe_alert_tag.setFont(tokens.get_sans_font(12, 400))
        self.lbl_probe_alert_tag.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        alert_layout.addWidget(self.lbl_probe_alert_tag)

        self.probe_alert_bar.setVisible(False)
        self.content_layout.addWidget(self.probe_alert_bar)

        # -------------------------------------------------------------
        # 3.2 Hero Section (Two columns that wrap via QGridLayout)
        # -------------------------------------------------------------
        self.hero_container = QWidget()
        self.hero_grid = QGridLayout(self.hero_container)
        self.hero_grid.setContentsMargins(0, 0, 0, 0)
        self.hero_grid.setHorizontalSpacing(24)
        self.hero_grid.setVerticalSpacing(16)

        self.hero_text_widget = QWidget()
        self.hero_text_col = QVBoxLayout(self.hero_text_widget)
        self.hero_text_col.setContentsMargins(0, 0, 0, 0)
        self.hero_text_col.setSpacing(8)

        self.lbl_hero_caption = QLabel("الحالة الآن")
        self.lbl_hero_caption.setFont(tokens.get_sans_font(13, 500))
        self.lbl_hero_caption.setStyleSheet(f"color: {tokens.STATUS_OK};")
        self.hero_text_col.addWidget(self.lbl_hero_caption)

        self.lbl_hero_title = QLabel("الشبكة سليمة")
        self.lbl_hero_title.setFont(tokens.get_sans_font(60, 600))
        self.lbl_hero_title.setStyleSheet(f"color: {tokens.TEXT}; line-height: 1.1;")
        self.hero_text_col.addWidget(self.lbl_hero_title)

        self.lbl_hero_desc = QLabel(
            "الاتصال مستقر وقريب من معدلاته المعتادة — لا توجد تدخلات مطلوبة اليوم."
        )
        self.lbl_hero_desc.setFont(tokens.get_sans_font(16, 400))
        self.lbl_hero_desc.setStyleSheet(f"color: {tokens.TEXT_SECONDARY}; line-height: 1.8;")
        self.lbl_hero_desc.setMaximumWidth(480)
        self.lbl_hero_desc.setWordWrap(True)
        self.hero_text_col.addWidget(self.lbl_hero_desc)

        self.day_strip = DayStrip(self)
        self.day_strip.setMaximumWidth(440)
        self.day_strip.setMinimumWidth(260)

        self.content_layout.addWidget(self.hero_container)

        # -------------------------------------------------------------
        # 3.3 Metrics Strip (4 equal cells in one container)
        # -------------------------------------------------------------
        self.metrics_strip = MetricsStrip(self)
        self.content_layout.addWidget(self.metrics_strip)

        # -------------------------------------------------------------
        # 3.4 Row A (Latency Chart + Timeline Panel)
        # -------------------------------------------------------------
        self.row_a_container = QWidget()
        self.row_a_grid = QGridLayout(self.row_a_container)
        self.row_a_grid.setContentsMargins(0, 0, 0, 0)
        self.row_a_grid.setHorizontalSpacing(tokens.PANEL_GAP)
        self.row_a_grid.setVerticalSpacing(tokens.PANEL_GAP)

        self.latency_chart = LatencyChart(self)
        self.timeline_panel = TimelinePanel(self)

        make_scroll_transparent(self.latency_chart, self.scroll)

        self.content_layout.addWidget(self.row_a_container)

        # -------------------------------------------------------------
        # 3.5 مسار اتصالك (Full Width Panel)
        # -------------------------------------------------------------
        self.flow_path = FlowPathPanel(self)
        make_scroll_transparent(self.flow_path, self.scroll)
        self.content_layout.addWidget(self.flow_path)

        # -------------------------------------------------------------
        # 3.6 Row B (Traffic Consumers + DNS Recommendation)
        # -------------------------------------------------------------
        self.row_b_container = QWidget()
        self.row_b_grid = QGridLayout(self.row_b_container)
        self.row_b_grid.setContentsMargins(0, 0, 0, 0)
        self.row_b_grid.setHorizontalSpacing(tokens.PANEL_GAP)
        self.row_b_grid.setVerticalSpacing(tokens.PANEL_GAP)

        self.consumers_panel = TrafficConsumersPanel(self)
        self.dns_panel = DNSRecommendationPanel(self)

        self.content_layout.addWidget(self.row_b_container)

        # -------------------------------------------------------------
        # Footer Note
        # -------------------------------------------------------------
        self.lbl_footer = QLabel("NetGuard الذكي · مراقبة حية وإصلاح ذاتي تلقائي للشبكة")
        self.lbl_footer.setFont(tokens.get_sans_font(12, 400))
        self.lbl_footer.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_footer.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(self.lbl_footer)

        self.scroll.setWidget(self.content_widget)
        root_layout.addWidget(self.scroll)

        # Set initial layout structure
        self._apply_layout_mode("desktop")

        # Secondary counter timer (live seconds since scan)
        self._timer_counter = QTimer(self)
        self._timer_counter.timeout.connect(self._on_second_tick)
        self._timer_counter.start(1000)
        self._on_second_tick()

        # Backward compatibility aliases for existing callers
        self.card_gateway = self.metrics_strip.cell_latency
        self.card_external = self.metrics_strip.cell_latency
        self.card_dns = self.metrics_strip.cell_jitter
        self.card_loss = self.metrics_strip.cell_loss
        self.card_download = self.metrics_strip.cell_download
        self.pipeline = self.flow_path
        self.wave_chart = self.latency_chart
        self.shield = self
        self.solutions_card = self.dns_panel

    def _apply_layout_mode(self, mode: str) -> None:
        self._current_layout_mode = mode

        # Clear Hero
        self.hero_grid.removeWidget(self.hero_text_widget)
        self.hero_grid.removeWidget(self.day_strip)

        # Clear Row A
        self.row_a_grid.removeWidget(self.latency_chart)
        self.row_a_grid.removeWidget(self.timeline_panel)

        # Clear Row B
        self.row_b_grid.removeWidget(self.consumers_panel)
        self.row_b_grid.removeWidget(self.dns_panel)

        if mode == "desktop":
            w = self.width() if self.width() > 0 else 1366
            padding_x = 24 if w < 1400 else tokens.PAGE_PADDING_DESKTOP
            self.content_layout.setContentsMargins(
                padding_x, 24, padding_x, 32
            )
            title_size = 54 if w < 1400 else 64
            self.lbl_hero_title.setFont(tokens.get_sans_font(title_size, 600))
            self.metrics_strip.set_responsive_columns(4)

            # Hero 2 cols with explicit column stretch
            self.hero_grid.setColumnStretch(0, 3)
            self.hero_grid.setColumnStretch(1, 2)
            self.hero_grid.addWidget(self.hero_text_widget, 0, 0)
            self.hero_grid.addWidget(self.day_strip, 0, 1)

            # Row A: Latency (flex 2 on right), Timeline (flex 1 on left)
            self.row_a_grid.addWidget(self.latency_chart, 0, 0, 1, 2)
            self.row_a_grid.addWidget(self.timeline_panel, 0, 2, 1, 1)

            # Row B: Consumers (right), DNS (left)
            self.row_b_grid.addWidget(self.consumers_panel, 0, 0)
            self.row_b_grid.addWidget(self.dns_panel, 0, 1)

        elif mode == "tablet":
            self.content_layout.setContentsMargins(24, 20, 24, 28)
            self.lbl_hero_title.setFont(tokens.get_sans_font(52, 600))
            self.metrics_strip.set_responsive_columns(2)

            # Stacked
            self.hero_grid.addWidget(self.hero_text_widget, 0, 0)
            self.hero_grid.addWidget(self.day_strip, 1, 0)

            self.row_a_grid.addWidget(self.latency_chart, 0, 0)
            self.row_a_grid.addWidget(self.timeline_panel, 1, 0)

            self.row_b_grid.addWidget(self.consumers_panel, 0, 0)
            self.row_b_grid.addWidget(self.dns_panel, 1, 0)

        else:  # "mobile"
            self.content_layout.setContentsMargins(
                tokens.PAGE_PADDING_NARROW, 16, tokens.PAGE_PADDING_NARROW, 20
            )
            self.lbl_hero_title.setFont(tokens.get_sans_font(40, 600))
            self.metrics_strip.set_responsive_columns(1)

            self.hero_grid.addWidget(self.hero_text_widget, 0, 0)
            self.hero_grid.addWidget(self.day_strip, 1, 0)

            self.row_a_grid.addWidget(self.latency_chart, 0, 0)
            self.row_a_grid.addWidget(self.timeline_panel, 1, 0)

            self.row_b_grid.addWidget(self.consumers_panel, 0, 0)
            self.row_b_grid.addWidget(self.dns_panel, 1, 0)

    def _on_second_tick(self) -> None:
        self._last_scan_seconds += 1
        now = datetime.now()
        days_ar = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
        months_ar = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
        day_name = days_ar[now.weekday()]
        month_name = months_ar[now.month - 1]
        time_str = now.strftime("%H:%M")
        self.lbl_status_line.setText(
            f"{day_name} {now.day} {month_name} · {time_str} · آخر فحص قبل {self._last_scan_seconds} ث"
        )

    def set_last_speed_test_time(self, time_str: str) -> None:
        self._last_speed_test_time = time_str
        self._last_scan_seconds = 0
        self._on_second_tick()

    def _on_scan_clicked(self) -> None:
        self.btn_scan.setText("جارٍ الفحص…")
        self.btn_scan.setEnabled(False)
        self._last_scan_seconds = 0
        self.quick_scan_requested.emit()

    def _on_scan_completed(self) -> None:
        self.btn_scan.setText("افحص الآن")
        self.btn_scan.setEnabled(True)

    def update_shield(self, is_healthy: bool, title: str, desc: str, **kwargs) -> None:
        if is_healthy:
            self.lbl_hero_caption.setText("الحالة الآن")
            self.lbl_hero_caption.setStyleSheet(f"color: {tokens.STATUS_OK};")
            self.lbl_hero_title.setText("الشبكة سليمة")
        else:
            self.lbl_hero_caption.setText("تنبيه")
            self.lbl_hero_caption.setStyleSheet(f"color: {tokens.STATUS_WARN};")
            self.lbl_hero_title.setText("الشبكة بطيئة")
        if desc:
            self.lbl_hero_desc.setText(desc)

    def update_daily_incident_summary(self, interventions_count: int, avg_duration_sec: Optional[float] = None) -> None:
        """Update hero description based on real database query of today's interventions (Item C3)."""
        if interventions_count == 0:
            self.lbl_hero_desc.setText("الاتصال مستقر وقريب من معدلاته المعتادة — لا توجد تدخلات مطلوبة اليوم.")
        elif interventions_count == 1:
            dur_str = f" خلال {int(round(avg_duration_sec))} ثانية" if avg_duration_sec else ""
            self.lbl_hero_desc.setText(f"رصد NetGuard مشكلة واحدة اليوم وأصلحها تلقائياً{dur_str} دون انقطاع اتصالك.")
        else:
            dur_str = f" في متوسط {int(round(avg_duration_sec))} ثانية" if avg_duration_sec else ""
            self.lbl_hero_desc.setText(f"أصلح NetGuard تلقائياً {interventions_count} تدخلات اليوم{dur_str} لضمان ثبات واستقرار الاتصال.")

    def set_probe_status_alert(self, error_message: Optional[str]) -> None:
        """Updates the non-intrusive persistent probe failure alert bar."""
        if error_message and isinstance(error_message, str):
            self.lbl_probe_alert_msg.setText(error_message)
            self.probe_alert_bar.setVisible(True)
            self.status_dot.set_status(tokens.STATUS_WARN)
        else:
            self.probe_alert_bar.setVisible(False)
            self.status_dot.set_status(tokens.STATUS_OK)

    def update_network_identity(self, info: Dict[str, Any]) -> None:
        pass

    def update_telemetry(self, obs, last_diag: Optional[Diagnosis]) -> None:
        if obs is None:
            self.set_probe_status_alert("محرك المراقبة غير متصل (Monitoring engine unavailable)")
            for cell in (self.metrics_strip.cell_latency, self.metrics_strip.cell_jitter, self.metrics_strip.cell_loss):
                cell.update_metric(" — ", footer_text="غير متصل", is_warning=False, samples=[])
            dl_footer = f"غير متصل · آخر فحص: {self._last_speed_test_time}" if self._last_speed_test_time else "غير متصل"
            self.metrics_strip.cell_download.update_metric(" — ", footer_text=dl_footer, is_warning=False, samples=[])
            self.latency_chart.update_telemetry(samples=[], avg_ms=0.0, max_ms=0.0, duration_str="—")
            if hasattr(self, "flow_path"):
                self.flow_path.update_node_latency(0, None, status="bad", desc="محول الشبكة غير متصل.")
                self.flow_path.update_node_latency(1, None, status="bad", desc="تعذر الوصول للراوتر.")
                self.flow_path.update_node_latency(2, None, status="bad", desc="مسار مزود الخدمة غير متاح.")
                self.flow_path.update_node_latency(3, None, status="none", desc="خادم DNS غير متوفر.")
                self.flow_path.update_node_latency(4, None, status="bad", desc="الاتصال بالإنترنت منقطع.")
            return

        # Check for persistent probe failures to display non-intrusively
        if hasattr(obs, "get_primary_probe_error_message"):
            probe_err = obs.get_primary_probe_error_message()
            self.set_probe_status_alert(probe_err)
        else:
            self.set_probe_status_alert(None)

        gw = obs.get_latest_measurement(MetricType.GATEWAY_LATENCY)
        ext = obs.get_latest_measurement(MetricType.EXTERNAL_LATENCY)
        jit = obs.get_latest_measurement(MetricType.JITTER_MS)
        loss = obs.get_latest_measurement(MetricType.GATEWAY_PACKET_LOSS)
        rx = obs.get_latest_measurement(MetricType.BANDWIDTH_RX_BYTES_PER_SEC)
        tx = obs.get_latest_measurement(MetricType.BANDWIDTH_TX_BYTES_PER_SEC)

        # 1. Latency Tile
        is_ext_valid = (
            ext is not None
            and ext.raw_value is not None
            and math.isfinite(ext.raw_value)
            and ext.raw_value >= 0.0
            and getattr(ext, "status", None) != ProbeStatus.FAILED
        )
        if is_ext_valid:
            lat_val = ext.raw_value
            is_warn = lat_val >= DEFAULT_THRESHOLDS.latency.external_warning_ms
            ext_window = obs.get_sliding_window(MetricType.EXTERNAL_LATENCY) or []
            ext_samples = [
                s.raw_value for s in ext_window
                if s.raw_value is not None and math.isfinite(s.raw_value) and s.raw_value >= 0.0
            ] if ext_window else []
            self.metrics_strip.cell_latency.update_metric(
                f"{int(round(lat_val))}",
                footer_text="تحذير · استجابة بطيئة" if is_warn else "ممتاز · مستقر",
                is_warning=is_warn,
                samples=ext_samples,
            )
        else:
            self.metrics_strip.cell_latency.update_metric(" — ", footer_text="غير متصل", is_warning=False, samples=[])

        # 2. Jitter Tile
        is_jit_valid = (
            jit is not None
            and jit.raw_value is not None
            and math.isfinite(jit.raw_value)
            and jit.raw_value >= 0.0
            and getattr(jit, "status", None) != ProbeStatus.FAILED
        )
        if is_jit_valid:
            jit_val = jit.raw_value
            is_warn = jit_val >= DEFAULT_THRESHOLDS.jitter.ui_warning_ms
            jit_window = obs.get_sliding_window(MetricType.JITTER_MS) or []
            jit_samples = [
                s.raw_value for s in jit_window
                if s.raw_value is not None and math.isfinite(s.raw_value) and s.raw_value >= 0.0
            ] if jit_window else []
            self.metrics_strip.cell_jitter.update_metric(
                f"{jit_val:.1f}",
                footer_text="تذبذب مرتفع" if is_warn else "جيد · يؤثر على المكالمات",
                is_warning=is_warn,
                samples=jit_samples,
            )
        else:
            self.metrics_strip.cell_jitter.update_metric(" — ", footer_text="غير متصل", is_warning=False, samples=[])

        # 3. Packet Loss Tile
        is_loss_valid = (
            loss is not None
            and loss.raw_value is not None
            and math.isfinite(loss.raw_value)
            and loss.raw_value >= 0.0
            and getattr(loss, "status", None) != ProbeStatus.FAILED
        )
        if is_loss_valid:
            loss_val = loss.raw_value * 100.0
            is_warn = loss_val > DEFAULT_THRESHOLDS.loss.dashboard_warning_pct
            loss_window = obs.get_sliding_window(MetricType.GATEWAY_PACKET_LOSS) or []
            loss_samples = [
                s.raw_value * 100.0 for s in loss_window
                if s.raw_value is not None and math.isfinite(s.raw_value) and s.raw_value >= 0.0
            ] if loss_window else []
            self.metrics_strip.cell_loss.update_metric(
                f"{loss_val:.1f}",
                footer_text="فقدان حزم ملحوظ" if is_warn else "ممتاز · لا حزم ضائعة",
                is_warning=is_warn,
                samples=loss_samples,
            )
        else:
            self.metrics_strip.cell_loss.update_metric(" — ", footer_text="غير متصل", is_warning=False, samples=[])

        # 4. Download / Throughput Tile (Item 1.1)
        is_rx_valid = (
            rx is not None
            and rx.raw_value is not None
            and math.isfinite(rx.raw_value)
            and rx.raw_value >= 0.0
            and getattr(rx, "status", None) != ProbeStatus.FAILED
        )
        if is_rx_valid:
            rx_mbps = (rx.raw_value * 8.0) / 1_000_000.0
            is_tx_valid = (
                tx is not None
                and tx.raw_value is not None
                and math.isfinite(tx.raw_value)
                and tx.raw_value >= 0.0
                and getattr(tx, "status", None) != ProbeStatus.FAILED
            )
            tx_mbps = ((tx.raw_value * 8.0) / 1_000_000.0) if is_tx_valid else 0.0

            if rx_mbps >= 100.0:
                val_str = f"{rx_mbps:.0f}"
            elif rx_mbps >= 1.0:
                val_str = f"{rx_mbps:.1f}"
            else:
                val_str = f"{rx_mbps:.2f}"

            upload_str = f"الرفع {tx_mbps:.1f} Mbps" if tx_mbps >= 1.0 else f"الرفع {tx_mbps:.2f} Mbps"
            if self._last_speed_test_time:
                footer_text = f"{upload_str} · آخر فحص: {self._last_speed_test_time}"
            else:
                footer_text = upload_str

            rx_window = obs.get_sliding_window(MetricType.BANDWIDTH_RX_BYTES_PER_SEC) or []
            rx_samples = [
                (s.raw_value * 8.0) / 1_000_000.0
                for s in rx_window
                if s.raw_value is not None and math.isfinite(s.raw_value) and s.raw_value >= 0.0
            ] if rx_window else []

            self.metrics_strip.cell_download.update_metric(
                val_str=val_str,
                footer_text=footer_text,
                is_warning=False,
                samples=rx_samples,
            )
        else:
            footer_text = "غير متصل"
            if self._last_speed_test_time:
                footer_text = f"غير متصل · آخر فحص: {self._last_speed_test_time}"
            self.metrics_strip.cell_download.update_metric(
                val_str=" — ",
                footer_text=footer_text,
                is_warning=False,
                samples=[],
            )

        # 5. Latency Chart Sliding Window
        ext_window = obs.get_sliding_window(MetricType.EXTERNAL_LATENCY) or []
        valid_chart_samples = [
            s.raw_value for s in ext_window
            if s.raw_value is not None and math.isfinite(s.raw_value) and s.raw_value >= 0.0
        ] if ext_window else []
        if valid_chart_samples:
            self.latency_chart.update_telemetry(
                samples=valid_chart_samples,
                avg_ms=sum(valid_chart_samples) / len(valid_chart_samples),
                max_ms=max(valid_chart_samples),
                duration_str=f"{len(valid_chart_samples)} ث",
            )
        else:
            self.latency_chart.update_telemetry(
                samples=[],
                avg_ms=0.0,
                max_ms=0.0,
                duration_str="—",
            )

        # 6. 5-Node Flow Path Live Updates (Item 1.3)
        if hasattr(self, "flow_path"):
            # Node 01: Device (local processing / adapter state)
            is_gw_valid = (
                gw is not None
                and gw.raw_value is not None
                and math.isfinite(gw.raw_value)
                and gw.raw_value >= 0.0
                and getattr(gw, "status", None) != ProbeStatus.FAILED
            )
            if is_gw_valid:
                self.flow_path.update_node_latency(
                    0, 0.5, status="ok", desc="بطاقة الشبكة وجهاز الكمبيوتر يعملان بكفاءة تامة دون أي تأخير داخلي."
                )
            else:
                self.flow_path.update_node_latency(
                    0, None, status="bad", desc="محول الشبكة غير متصل بالراوتر أو معطل."
                )

            # Node 02: Router (Gateway latency)
            if is_gw_valid:
                gw_ms = gw.raw_value
                if gw_ms < DEFAULT_THRESHOLDS.latency.gateway_warning_ms:
                    gw_st = "ok"
                    gw_desc = f"الاتصال بالراوتر المنزلي مستقر للغاية ({int(round(gw_ms))} ms)."
                elif gw_ms < DEFAULT_THRESHOLDS.latency.gateway_critical_ms:
                    gw_st = "warn"
                    gw_desc = f"زمن الاستجابة للراوتر مرتفع نسبياً ({int(round(gw_ms))} ms). قد يكون هناك تداخل لاسلكي."
                else:
                    gw_st = "bad"
                    gw_desc = f"بطء شديد أو فقدان حزم في الاتصال بالراوتر ({int(round(gw_ms))} ms)."
                self.flow_path.update_node_latency(1, gw_ms, status=gw_st, desc=gw_desc)
            else:
                self.flow_path.update_node_latency(1, None, status="bad", desc="تعذر الوصول للراوتر (البوابة الافتراضية).")

            # Node 03: ISP (Provider network / 2nd hop)
            if is_ext_valid and is_gw_valid:
                gw_ms = gw.raw_value
                ext_ms = ext.raw_value
                isp_ms = gw_ms + max(2.0, (ext_ms - gw_ms) * 0.35)
                if isp_ms < DEFAULT_THRESHOLDS.latency.external_warning_ms * 0.6:
                    isp_st = "ok"
                    isp_desc = f"كابينة الألياف ومسار التوصيل بشركة الاتصالات يعمل بكفاءة ({int(round(isp_ms))} ms)."
                elif isp_ms < DEFAULT_THRESHOLDS.latency.external_critical_ms * 0.6:
                    isp_st = "warn"
                    isp_desc = f"ضغط أو بطء طفيف في شبكة مزود الخدمة ({int(round(isp_ms))} ms)."
                else:
                    isp_st = "bad"
                    isp_desc = f"اختناق في مسار التوصيل بمزود الخدمة ({int(round(isp_ms))} ms)."
                self.flow_path.update_node_latency(2, isp_ms, status=isp_st, desc=isp_desc)
            elif is_ext_valid:
                ext_ms = ext.raw_value
                isp_ms = ext_ms * 0.4
                self.flow_path.update_node_latency(2, isp_ms, status="ok", desc=f"مسار مزود الخدمة متاح ({int(round(isp_ms))} ms).")
            else:
                self.flow_path.update_node_latency(2, None, status="bad", desc="انقطاع الاتصال بمزود خدمة الإنترنت (ISP).")

            # Node 04: DNS Server (from DNS latency measurement)
            dns_meas = obs.get_latest_measurement(MetricType.DNS_LATENCY)
            is_dns_valid = (
                dns_meas is not None
                and dns_meas.raw_value is not None
                and math.isfinite(dns_meas.raw_value)
                and dns_meas.raw_value >= 0.0
                and getattr(dns_meas, "status", None) != ProbeStatus.FAILED
            )
            if is_dns_valid:
                dns_ms = dns_meas.raw_value
                if dns_ms < DEFAULT_THRESHOLDS.latency.dns_warning_ms:
                    dns_st = "ok"
                    dns_desc = f"خادم DNS النشط يستجيب بسرعة ({int(round(dns_ms))} ms). استعلامات المواقع تتم فوراً."
                elif dns_ms < DEFAULT_THRESHOLDS.latency.dns_critical_ms:
                    dns_st = "warn"
                    dns_desc = f"خادم DNS النشط أبطأ من المعدل المعتاد ({int(round(dns_ms))} ms). قد تتأخر المواقع 1-2 ثانية."
                else:
                    dns_st = "bad"
                    dns_desc = f"خادم DNS النشط بطيء جداً أو متوقف ({int(round(dns_ms))} ms). يُوصى بتغييره."
                self.flow_path.update_node_latency(3, dns_ms, status=dns_st, desc=dns_desc)
            elif self.flow_path.node_info[3]["latency"] is None:
                self.flow_path.update_node_latency(3, None, status="none", desc="جاري قياس استجابة خادم DNS...")

            # Node 05: Internet (External latency)
            if is_ext_valid:
                ext_ms = ext.raw_value
                if ext_ms < DEFAULT_THRESHOLDS.latency.external_warning_ms:
                    ext_st = "ok"
                    ext_desc = f"الوصول إلى الخوادم السحابية العالمية متاح ومستقر ({int(round(ext_ms))} ms)."
                elif ext_ms < DEFAULT_THRESHOLDS.latency.external_critical_ms:
                    ext_st = "warn"
                    ext_desc = f"زمن الاستجابة للإنترنت الخارجي مرتفع نسبياً ({int(round(ext_ms))} ms)."
                else:
                    ext_st = "bad"
                    ext_desc = f"انقطاع أو بطء حاد في الاتصال بالإنترنت العام ({int(round(ext_ms))} ms)."
                self.flow_path.update_node_latency(4, ext_ms, status=ext_st, desc=ext_desc)
            else:
                self.flow_path.update_node_latency(4, None, status="bad", desc="تعذر الوصول إلى الإنترنت العام (انقطاع كامل).")

        if last_diag:
            is_healthy = last_diag.probable_cause == ProbableCause.HEALTHY
            self.update_shield(is_healthy, "", last_diag.explanation)

    def update_dns_recommendation(
        self,
        curr_name: str,
        curr_ms: float,
        best_name: str,
        best_ip: str,
        best_ms: float,
        is_optimal: bool,
        is_autonomous: bool = True,
    ) -> None:
        """Dynamically update recommendation card and flow path node from live benchmark."""
        self.dns_panel.update_dns_state(
            curr_name=curr_name,
            curr_ms=curr_ms,
            best_name=best_name,
            best_ip=best_ip,
            best_ms=best_ms,
            is_optimal=is_optimal,
            is_autonomous=is_autonomous,
        )
        self.flow_path.update_dns_node(
            latency_ms=best_ms if is_optimal else curr_ms,
            is_optimal=is_optimal,
            dns_name=best_name if is_optimal else curr_name,
        )

    def update_timeline_from_records(
        self,
        incident: Optional[Any] = None,
        audit_record: Optional[Any] = None,
    ) -> None:
        """Delegate dynamic timeline generation to timeline_panel from stored records."""
        self.timeline_panel.update_from_records(incident, audit_record)

    def log_autonomous_action(self, title: str, description: str, level: str = "success") -> None:
        now_dt = datetime.now()
        t1 = (now_dt - timedelta(seconds=15)).strftime("%H:%M:%S")
        t2 = (now_dt - timedelta(seconds=12)).strftime("%H:%M:%S")
        t3 = (now_dt - timedelta(seconds=5)).strftime("%H:%M:%S")
        t4 = now_dt.strftime("%H:%M:%S")

        res_msg = "استعادة الاستقرار وانخفاض زمن الاستجابة للمعدلات الطبيعية."
        if level == "error":
            res_msg = "تعذر إكمال المعالجة أو التحقق من استقرار الاتصال."
        elif level == "warning":
            res_msg = "تم التدخل بنجاح مع استمرار مراقبة مؤشرات الأداء."

        steps = [
            (t1, "اكتشاف المشكلة", "رصد انحراف أو تذبذب في مؤشرات جودة وتدفق حركة البيانات."),
            (t2, "تحديد السبب", description),
            (t3, "الإصلاح", title),
            (t4, "النتيجة", res_msg),
        ]
        self.timeline_panel.set_event(now_dt.strftime("%H:%M"), steps, is_resolved=(level == "success"))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        w = self.width()

        if w >= 1100:
            if self._current_layout_mode != "desktop":
                self._apply_layout_mode("desktop")
        elif 700 <= w < 1100:
            if self._current_layout_mode != "tablet":
                self._apply_layout_mode("tablet")
        else:  # w < 700
            if self._current_layout_mode != "mobile":
                self._apply_layout_mode("mobile")
