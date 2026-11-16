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

from app.ui import tokens
from app.ui.widgets.buttons import PrimaryButton, SecondaryButton
from app.ui.widgets.day_strip import DayStrip
from app.ui.widgets.metric_cell import MetricsStrip, MetricCell
from app.ui.widgets.latency_chart import LatencyChart
from app.ui.widgets.timeline import TimelinePanel
from app.ui.widgets.flow_path import FlowPathPanel
from app.ui.widgets.bar_row import TrafficConsumersPanel, DNSRecommendationPanel
from app.core.models.metrics import MetricType, Diagnosis, ProbableCause, ProbeStatus


class StatusIndicatorDot(QWidget):
    """8px green dot with continuous pulsing ring."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self._pulse_phase = 0.0
        if tokens.ANIMATIONS_ENABLED:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick)
            self._timer.start(50)

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
            ring_col = QColor(tokens.STATUS_OK)
            ring_col.setAlpha(max(0, min(255, ring_alpha)))
            painter.setPen(QPen(ring_col, 1.2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(center_x - ring_radius, center_y - ring_radius, ring_radius * 2, ring_radius * 2)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(tokens.STATUS_OK)))
        painter.drawEllipse(center_x - 4.0, center_y - 4.0, 8.0, 8.0)


class DashboardView(QWidget):
    """Main Dashboard View matching the reference specification."""

    quick_scan_requested = Signal()
    export_report_requested = Signal()

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

        self.btn_scan = PrimaryButton("افحص الآن")
        self.btn_scan.clicked.connect(self._on_scan_clicked)

        buttons_box.addWidget(self.btn_export)
        buttons_box.addWidget(self.btn_scan)
        self.header_row.addLayout(buttons_box)

        self.content_layout.addLayout(self.header_row)

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
            "الاتصال مستقر وقريب من معدلاته المعتادة. رصد NetGuard مشكلة واحدة اليوم وأصلحها تلقائياً خلال 41 ثانية دون تدخل منك."
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

        self.content_layout.addWidget(self.row_a_container)

        # -------------------------------------------------------------
        # 3.5 مسار اتصالك (Full Width Panel)
        # -------------------------------------------------------------
        self.flow_path = FlowPathPanel(self)
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
        QTimer.singleShot(10000, self._on_scan_completed)

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

    def update_network_identity(self, info: Dict[str, Any]) -> None:
        pass

    def update_telemetry(self, obs, last_diag: Optional[Diagnosis]) -> None:
        if obs is None:
            for cell in (self.metrics_strip.cell_latency, self.metrics_strip.cell_jitter, self.metrics_strip.cell_loss):
                cell.update_metric(" — ", footer_text="غير متصل", is_warning=False, samples=[])
            dl_footer = f"غير متصل · آخر فحص: {self._last_speed_test_time}" if self._last_speed_test_time else "غير متصل"
            self.metrics_strip.cell_download.update_metric(" — ", footer_text=dl_footer, is_warning=False, samples=[])
            self.latency_chart.update_telemetry(samples=[], avg_ms=0.0, max_ms=0.0, duration_str="—")
            return

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
            is_warn = lat_val >= 80.0
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
            is_warn = jit_val >= 10.0
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
            is_warn = loss_val > 1.0
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

    def log_autonomous_action(self, title: str, description: str, level: str = "success") -> None:
        now_str = datetime.now().strftime("%H:%M:%S")
        steps = [
            (now_str, "اكتشاف المشكلة", "رصد انحراف أو تذبذب في مسار الاتصال المعتاد."),
            (now_str, "تحديد السبب", description),
            (now_str, "الإصلاح", title),
            (now_str, "النتيجة", "استعادة الاستقرار وانخفاض زمن الاستجابة للمعدلات الطبيعية."),
        ]
        self.timeline_panel.set_event(now_str[:5], steps, is_resolved=(level == "success"))

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
