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
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QGridLayout,
    QSizePolicy,
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
from app.ui.widgets.network_info_strip import NetworkInfoStrip
from app.ui.widgets.scroll_forwarder import make_scroll_transparent
from app.core.models.metrics import MetricType, Diagnosis, ProbableCause, ProbeStatus
from app.dns.state import DnsStateManager
from app.ui.animation_clock import AnimationMasterClock


class StatusIndicatorDot(QWidget):
    """8px dot with continuous pulsing ring, reflecting active health/warning state."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pulse_phase = 0.0
        self._status_color = tokens.STATUS_OK
        self._is_paused = False
        if tokens.ANIMATIONS_ENABLED:
            AnimationMasterClock.get_instance().subscribe(self._tick)

    def set_status(self, color: str = tokens.STATUS_OK) -> None:
        if self._status_color != color:
            self._status_color = color
            self.update()

    def set_paused(self, paused: bool) -> None:
        self._is_paused = paused
        if paused:
            AnimationMasterClock.get_instance().unsubscribe(self._tick)
        else:
            AnimationMasterClock.get_instance().subscribe(self._tick)

    def _tick(self, delta_ms: float = 50.0) -> None:
        if getattr(self, "_is_paused", False):
            return
        clock = AnimationMasterClock.get_instance()
        if clock.is_low_resource_mode:
            return
        increment = 0.028 * (delta_ms / 50.0)
        self._pulse_phase = (self._pulse_phase + increment) % 1.0
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

    def set_animations_paused(self, paused: bool) -> None:
        if hasattr(self, "status_dot") and hasattr(self.status_dot, "set_paused"):
            self.status_dot.set_paused(paused)
        if hasattr(self, "flow_path") and hasattr(self.flow_path, "set_paused"):
            self.flow_path.set_paused(paused)
        if hasattr(self, "latency_chart") and hasattr(self.latency_chart, "set_paused"):
            self.latency_chart.set_paused(paused)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._last_scan_seconds = 0
        self._last_speed_test_time: Optional[str] = None
        self._current_layout_mode = "desktop"

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Scroll area for vertical content with hardware blitting optimization
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.horizontalScrollBar().setEnabled(False)
        self.scroll.horizontalScrollBar().setMaximum(0)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet(f"QScrollArea {{ background-color: {tokens.BG}; border: none; }}")
        self.scroll.viewport().setAutoFillBackground(True)
        self.scroll.viewport().setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.scroll.viewport().setStyleSheet(f"background-color: {tokens.BG};")
        self.scroll.verticalScrollBar().setSingleStep(25)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet(f"background-color: {tokens.BG};")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(
            20, 20, 20, 24
        )
        self.content_layout.setSpacing(16)

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
                background: transparent;
                border: none;
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
        # 3.1.8 Network Information Identity Strip (SSID, ISP, Local/Public IP)
        # -------------------------------------------------------------
        self.network_strip = NetworkInfoStrip(self)
        self.content_layout.addWidget(self.network_strip)

        # -------------------------------------------------------------
        # 3.2 Hero Section (Two columns that wrap via QGridLayout)
        # -------------------------------------------------------------
        self.hero_container = QWidget()
        self.hero_grid = QGridLayout(self.hero_container)
        self.hero_grid.setContentsMargins(0, 0, 0, 0)
        self.hero_grid.setHorizontalSpacing(24)
        self.hero_grid.setVerticalSpacing(16)

        self.hero_text_widget = QWidget()
        self.hero_text_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.hero_text_col = QVBoxLayout(self.hero_text_widget)
        self.hero_text_col.setContentsMargins(0, 0, 0, 0)
        self.hero_text_col.setSpacing(8)

        self.lbl_hero_caption = QLabel("جاري الفحص...")
        self.lbl_hero_caption.setFont(tokens.get_sans_font(12, 500))
        self.lbl_hero_caption.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.hero_text_col.addWidget(self.lbl_hero_caption)

        self.lbl_hero_title = QLabel("جاري تقييم الشبكة...")
        self.lbl_hero_title.setFont(tokens.get_sans_font(28, 600))
        self.lbl_hero_title.setStyleSheet(f"color: {tokens.TEXT}; line-height: 1.2;")
        self.lbl_hero_title.setWordWrap(True)
        self.lbl_hero_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.hero_text_col.addWidget(self.lbl_hero_title)

        self.lbl_hero_desc = QLabel(
            "يتم الآن فحص استجابة الراوتر المحلي، والاتصال بالإنترنت، وخوادم DNS..."
        )
        self.lbl_hero_desc.setFont(tokens.get_sans_font(13, 400))
        self.lbl_hero_desc.setStyleSheet(f"color: {tokens.TEXT_SECONDARY}; line-height: 1.6;")
        self.lbl_hero_desc.setWordWrap(True)
        self.hero_text_col.addWidget(self.lbl_hero_desc)

        self.day_strip = DayStrip(self)

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
        if hasattr(self, "network_strip"):
            self.network_strip.set_responsive_mode(mode)

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
            self.content_layout.setContentsMargins(20, 20, 20, 24)
            self.lbl_hero_title.setFont(tokens.get_sans_font(28, 600))
            self.metrics_strip.set_responsive_columns(4)

            # Status uses the full width. The day strip sits underneath
            # so the title is never squeezed into a clipped fragment.
            self.hero_grid.setColumnStretch(0, 1)
            self.hero_grid.setColumnStretch(1, 0)
            self.hero_grid.addWidget(self.hero_text_widget, 0, 0)
            self.hero_grid.addWidget(self.day_strip, 1, 0)

            # Row A: Latency (flex 3), Timeline (flex 2)
            self.row_a_grid.setColumnStretch(0, 3)
            self.row_a_grid.setColumnStretch(1, 2)
            self.row_a_grid.addWidget(self.latency_chart, 0, 0)
            self.row_a_grid.addWidget(self.timeline_panel, 0, 1)

            # Row B: Consumers (flex 1), DNS (flex 1)
            self.row_b_grid.setColumnStretch(0, 1)
            self.row_b_grid.setColumnStretch(1, 1)
            self.row_b_grid.addWidget(self.consumers_panel, 0, 0)
            self.row_b_grid.addWidget(self.dns_panel, 0, 1)

        elif mode == "tablet":
            self.content_layout.setContentsMargins(16, 16, 16, 20)
            self.lbl_hero_title.setFont(tokens.get_sans_font(24, 600))
            self.metrics_strip.set_responsive_columns(2)

            # Stacked
            self.hero_grid.addWidget(self.hero_text_widget, 0, 0)
            self.hero_grid.addWidget(self.day_strip, 1, 0)

            self.row_a_grid.addWidget(self.latency_chart, 0, 0)
            self.row_a_grid.addWidget(self.timeline_panel, 1, 0)

            self.row_b_grid.addWidget(self.consumers_panel, 0, 0)
            self.row_b_grid.addWidget(self.dns_panel, 1, 0)

        else:  # "mobile"
            self.content_layout.setContentsMargins(12, 12, 12, 16)
            self.lbl_hero_title.setFont(tokens.get_sans_font(18, 600))
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
        scan_ago = "الآن" if self._last_scan_seconds <= 1 else f"قبل {self._last_scan_seconds} ث"
        self.lbl_status_line.setText(
            f"{day_name} {now.day} {month_name} · {time_str} · آخر فحص {scan_ago}"
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

    def update_shield(self, is_healthy: Any, title: str = "", desc: str = "", **kwargs) -> None:
        if is_healthy is True or is_healthy == "healthy":
            self.lbl_hero_caption.setText("الحالة الآن")
            self.lbl_hero_caption.setStyleSheet(f"color: {tokens.STATUS_OK};")
            self.lbl_hero_title.setText(title or "الشبكة سليمة")
            self.status_dot.set_status(tokens.STATUS_OK)
        elif is_healthy == "offline" or is_healthy == "outage":
            self.lbl_hero_caption.setText("انقطاع")
            self.lbl_hero_caption.setStyleSheet(f"color: {tokens.STATUS_BAD};")
            self.lbl_hero_title.setText(title or "انقطاع الاتصال")
            self.status_dot.set_status(tokens.STATUS_BAD)
        elif is_healthy == "inconclusive" or is_healthy == "checking":
            self.lbl_hero_caption.setText("جاري الفحص")
            self.lbl_hero_caption.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
            self.lbl_hero_title.setText(title or "جاري تقييم الشبكة...")
            self.status_dot.set_status(tokens.TEXT_MUTED)
        else:
            self.lbl_hero_caption.setText("تنبيه")
            self.lbl_hero_caption.setStyleSheet(f"color: {tokens.STATUS_WARN};")
            self.lbl_hero_title.setText(title or "الشبكة بطيئة")
            self.status_dot.set_status(tokens.STATUS_WARN)
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
        self._network_info = info
        if hasattr(self, "network_strip"):
            self.network_strip.update_info(info)

        if hasattr(self, "flow_path") and info:
            isp_name = info.get("isp_company") or "مزود الخدمة"
            if "WE" in isp_name or "المصرية" in isp_name:
                isp_node_label = "مزود الخدمة (WE)"
            elif "Orange" in isp_name or "أورنج" in isp_name:
                isp_node_label = "مزود الخدمة (Orange)"
            elif "Vodafone" in isp_name or "فودافون" in isp_name:
                isp_node_label = "مزود الخدمة (Vodafone)"
            elif "Etisalat" in isp_name or "e&" in isp_name:
                isp_node_label = "مزود الخدمة (e&)"
            else:
                isp_node_label = isp_name[:18] if len(isp_name) > 18 else isp_name

            if len(self.flow_path.node_info) > 2:
                self.flow_path.node_info[2]["name"] = isp_node_label
                self.flow_path.nodes[2].lbl_name.setText(isp_node_label)

                hop2_diag = info.get("hop2_diag") or {}
                if hop2_diag:
                    h2_cls = hop2_diag.get("classification")
                    h2_lat = hop2_diag.get("latency_ms")
                    if h2_lat is not None and h2_lat >= 0:
                        st = "ok" if h2_lat < 50.0 else "warn"
                        self.flow_path.update_node_latency(
                            2,
                            h2_lat,
                            status=st,
                            desc=f"المحطة الثانية تستجيب بنجاح ({int(round(h2_lat))} ms) عبر {hop2_diag.get('protocol', 'ICMP')} · {isp_name}.",
                        )
                    elif h2_cls in ("PATH_CONTINUES", "INTERMEDIATE_FILTERING_SUSPECTED"):
                        self.flow_path.update_node_latency(
                            2,
                            None,
                            status="ok",
                            desc=f"المحطة الثانية (Hop 02) لا تستجيب لحزم الاستطلاع المباشرة، مع استمرار حركة البيانات ووصولها للمحطات اللاحقة بنجاح (Path Continues · {isp_name}).",
                        )

    def update_telemetry(self, obs, last_diag: Optional[Diagnosis]) -> None:
        self._last_scan_seconds = 0
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
        ext_loss = obs.get_latest_measurement(MetricType.EXTERNAL_PACKET_LOSS)
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
            if jit_val < 10.0:
                footer_txt = "ممتاز • مثالي للمكالمات"
                is_warn = False
                color = tokens.STATUS_OK
            elif jit_val < 30.0:
                footer_txt = "جيد • مناسب للمكالمات"
                is_warn = False
                color = tokens.STATUS_OK
            elif jit_val <= 50.0:
                footer_txt = "متوسط • قد يؤثر على المكالمات"
                is_warn = True
                color = tokens.STATUS_WARN
            else:
                footer_txt = "مرتفع • يؤثر بشدة على المكالمات"
                is_warn = True
                color = tokens.STATUS_BAD

            jit_window = obs.get_sliding_window(MetricType.JITTER_MS) or []
            jit_samples = [
                s.raw_value for s in jit_window
                if s.raw_value is not None and math.isfinite(s.raw_value) and s.raw_value >= 0.0
            ] if jit_window else []
            self.metrics_strip.cell_jitter.update_metric(
                f"{jit_val:.1f}",
                footer_text=footer_txt,
                is_warning=is_warn,
                samples=jit_samples,
                status_color=color,
            )
        else:
            self.metrics_strip.cell_jitter.update_metric(" — ", footer_text="غير متصل", is_warning=False, samples=[])

        # 3. Packet Loss Tile (Unified WAN + Gateway Sliding Window)
        def _calc_loss(window: List[Any], latest: Optional[Any]) -> Tuple[Optional[float], List[float]]:
            items = list(window) if window else ([latest] if latest is not None else [])
            if not items:
                return None, []
            valid_vals: List[float] = []
            for s in items:
                st = getattr(s, "status", None)
                if st in (ProbeStatus.FAILED, ProbeStatus.TIMEOUT):
                    valid_vals.append(1.0)
                elif s.raw_value is not None and math.isfinite(s.raw_value):
                    if s.raw_value >= 0.0:
                        valid_vals.append(max(0.0, min(1.0, float(s.raw_value))))
            if not valid_vals:
                return None, []
            pct = (sum(valid_vals) / float(len(valid_vals))) * 100.0
            return pct, [v * 100.0 for v in valid_vals]

        ext_loss_win = obs.get_sliding_window(MetricType.EXTERNAL_PACKET_LOSS) or []
        gw_loss_win = obs.get_sliding_window(MetricType.GATEWAY_PACKET_LOSS) or []
        ext_loss_val, ext_loss_samples = _calc_loss(ext_loss_win, ext_loss)
        gw_loss_val, gw_loss_samples = _calc_loss(gw_loss_win, loss)

        if ext_loss_val is not None or gw_loss_val is not None:
            if ext_loss_val is not None and gw_loss_val is not None:
                loss_val = max(ext_loss_val, gw_loss_val)
                loss_samples = ext_loss_samples if ext_loss_val >= gw_loss_val else gw_loss_samples
            elif ext_loss_val is not None:
                loss_val = ext_loss_val
                loss_samples = ext_loss_samples
            else:
                loss_val = gw_loss_val
                loss_samples = gw_loss_samples

            is_warn = loss_val > DEFAULT_THRESHOLDS.loss.dashboard_warning_pct
            if loss_val >= 99.9:
                footer_txt = "انقطاع كامل في الحزم"
            elif is_warn:
                footer_txt = "فقدان حزم ملحوظ"
            else:
                footer_txt = "ممتاز · لا حزم ضائعة"

            self.metrics_strip.cell_loss.update_metric(
                f"{loss_val:.1f}",
                footer_text=footer_txt,
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

            # Node 03: Hop 02 / Next-Hop Provider Network
            net_info = getattr(self, "_network_info", {}) or {}
            isp_name = net_info.get("isp_company") or "مزود الخدمة"
            if "WE" in isp_name or "المصرية" in isp_name:
                isp_node_label = "مزود الخدمة (WE)"
            elif "Orange" in isp_name or "أورنج" in isp_name:
                isp_node_label = "مزود الخدمة (Orange)"
            elif "Vodafone" in isp_name or "فودافون" in isp_name:
                isp_node_label = "مزود الخدمة (Vodafone)"
            elif "Etisalat" in isp_name or "e&" in isp_name:
                isp_node_label = "مزود الخدمة (e&)"
            else:
                isp_node_label = isp_name[:20] if len(isp_name) > 20 else isp_name

            if len(self.flow_path.node_info) > 2 and isp_node_label not in ("مزود الخدمة", "جاري التحقق من مزود الخدمة..."):
                self.flow_path.node_info[2]["name"] = isp_node_label
                self.flow_path.nodes[2].lbl_name.setText(isp_node_label)

            hop2_diag = net_info.get("hop2_diag", {}) or {}
            isp_edge_hop = net_info.get("isp_gateway_ip") or hop2_diag.get("ip")
            h2_cls = hop2_diag.get("classification")
            h2_lat = hop2_diag.get("latency_ms") or net_info.get("isp_gateway_latency_ms")
            if h2_lat is None:
                try:
                    from app.platform.windows.network_info import _cached_hop2_info, _cached_isp_gateway
                    if _cached_hop2_info:
                        h2_lat = _cached_hop2_info.get("latency_ms")
                        h2_cls = h2_cls or _cached_hop2_info.get("classification")
                        isp_edge_hop = isp_edge_hop or _cached_isp_gateway or _cached_hop2_info.get("ip")
                except Exception:
                    pass

            if not is_ext_valid and not is_gw_valid:
                self.flow_path.update_node_latency(
                    2, None, status="bad", desc=f"انقطاع الاتصال بمزود خدمة الإنترنت ({isp_name})."
                )
            elif h2_lat is not None and h2_lat >= 0:
                st = "ok" if h2_lat < 50.0 else "warn"
                h2_proto = hop2_diag.get("protocol", "ICMP")
                self.flow_path.update_node_latency(
                    2,
                    h2_lat,
                    status=st,
                    desc=f"المحطة الثانية ({isp_edge_hop} · {isp_name}) تستجيب بنجاح ({int(round(h2_lat))} ms) عبر بروتوكول {h2_proto}.",
                )
            elif h2_cls in ("PATH_CONTINUES", "INTERMEDIATE_FILTERING_SUSPECTED") or (is_ext_valid and not isp_edge_hop):
                # CASE 1 & CASE 2: Hop 2 silent, but packets progressed and external connectivity is verified!
                self.flow_path.update_node_latency(
                    2,
                    None,
                    status="ok",
                    desc=f"المحطة الثانية (Hop 02) لا تستجيب لحزم الاستطلاع المباشرة، مع استمرار حركة البيانات ووصولها للمحطات اللاحقة بنجاح (Path Continues · {isp_name}).",
                )
            elif is_ext_valid:
                self.flow_path.update_node_latency(
                    2,
                    None,
                    status="ok",
                    desc=f"مسار {isp_name} نشط ويمرر البيانات للمحطات الخارجية، مع حجب استجابات الاستطلاع الوسيطة.",
                )
            else:
                self.flow_path.update_node_latency(
                    2, None, status="bad", desc=f"انقطاع الاتصال أو تعذر الاستجابة في مسار {isp_name}."
                )

            # Node 04: DNS Server (from single source of truth DnsStateManager)
            dns_state = DnsStateManager.get_instance().current
            if dns_state.last_measured_ms is not None and dns_state.last_measured_ms > 0:
                dns_ms = dns_state.last_measured_ms
                dns_name = dns_state.detected_provider or (dns_state.active_servers[0] if dns_state.active_servers else "DNS")
                active_ip = dns_state.active_servers[0] if dns_state.active_servers else ""
                dns_st = "ok" if dns_state.is_healthy else ("warn" if dns_ms < 150.0 else "bad")
                dns_desc = f"خادم DNS المعتمد بجهازك ({dns_name} · {active_ip}) يستجيب بسرعة ({int(round(dns_ms))} ms). ترجمة النطاقات نشطة."
                self.flow_path.update_node_latency(3, dns_ms, status=dns_st, desc=dns_desc)
            else:
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
                    dns_st = "ok" if dns_ms < DEFAULT_THRESHOLDS.latency.dns_warning_ms else "warn"
                    self.flow_path.update_node_latency(3, dns_ms, status=dns_st, desc=f"خادم DNS النشط يستجيب ({int(round(dns_ms))} ms).")
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

        if not is_gw_valid and not is_ext_valid:
            self.update_shield("offline", "تعذر الاتصال بالشبكة", "تعذر الوصول إلى الراوتر المنزلي أو شبكة الإنترنت الخارجية.")
        elif not is_ext_valid:
            self.update_shield("outage", "انقطاع الإنترنت", "الراوتر المنزلي متصل، ولكن تعذر الوصول إلى خوادم الإنترنت العامة.")
        elif last_diag:
            if last_diag.probable_cause == ProbableCause.HEALTHY and is_gw_valid and is_ext_valid:
                self.update_shield("healthy", "الشبكة سليمة", "كافة مؤشرات الشبكة والراوتر وخوادم الإنترنت تعمل ضمن المعدلات الطبيعية الممتازة.")
            elif last_diag.probable_cause in (ProbableCause.UNKNOWN_ANOMALY, None) and (not is_gw_valid or not is_ext_valid):
                self.update_shield("inconclusive", "جاري تدقيق القياسات...", "جاري جمع مؤشرات الشبكة والتحقق الميداني من استجابة المسار.")
            else:
                is_healthy = last_diag.probable_cause in (ProbableCause.HEALTHY, ProbableCause.DESTINATION_SPECIFIC_OUTAGE)
                expl = last_diag.explanation or ""
                title = "الشبكة بطيئة أو متذبذبة"
                if "Default gateway" in expl or "gateway failed" in expl:
                    expl = "تعذر وصول حزم الفحص إلى الراوتر المنزلي. تحقق من كابل الشبكة أو تشغيل الراوتر."
                    title = "انقطاع الاتصال بالراوتر"
                elif "Target" in expl and "is failing" in expl:
                    expl = "أحد خوادم الفحص الخارجية لا يستجيب مؤقتاً، بينما اتصالك العام سليم وبقية الوجهات تعمل بكفاءة."
                    title = "تباطؤ في وجهة خارجية"
                elif "DNS" in expl:
                    expl = "فشل في استعلامات أسماء النطاقات (DNS) بينما الاتصال المباشر متاح. خادم DNS لا يستجيب."
                    title = "خلل في استجابة DNS"
                elif "Upstream" in expl or "ISP" in expl or "مزود الخدمة" in expl:
                    expl = "الراوتر المنزلي متصل، لكن هناك تذبذب أو فقدان حزم في كابينة مزود خدمة الإنترنت (ISP)."
                    title = "تذبذب في شبكة المزود"
                elif "Wi-Fi" in expl or "الواي فاي" in expl:
                    expl = "إشارة الواي فاي ضعيفة جداً مما يسبب بطء الاتصال وتأخير الحزم."
                    title = "إشارة واي فاي ضعيفة"
                elif "normal" in expl or "indicators" in expl or not any('\u0600' <= c <= '\u06FF' for c in expl):
                    expl = "كافة مؤشرات الشبكة والراوتر وخوادم الإنترنت تعمل ضمن المعدلات الطبيعية الممتازة."
                    title = "الشبكة سليمة"
                self.update_shield(is_healthy, title, expl)

    def update_dns_recommendation(
        self,
        curr_name: str,
        curr_ms: Optional[float],
        best_name: str,
        best_ip: str,
        best_ms: float,
        is_optimal: bool,
        is_autonomous: bool = True,
        auto_applied: bool = False,
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
            auto_applied=auto_applied,
        )
        if curr_ms is not None and curr_ms > 0:
            self.flow_path.update_dns_node(
                latency_ms=curr_ms,
                is_optimal=is_optimal,
                dns_name=curr_name,
            )
        else:
            self.flow_path.update_node_latency(3, None, status="none", desc="جاري قياس استجابة خادم DNS...")

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

    def _sync_content_width(self) -> None:
        if hasattr(self, "scroll") and hasattr(self, "content_widget"):
            vw = self.scroll.viewport().width()
            if vw > 0:
                self.content_widget.setFixedWidth(vw)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_content_width()
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
