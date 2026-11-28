"""Redesigned Network Engineering Overview Dashboard for NetGuard AI.

Presents genuine real-time network health, performance telemetry, live traffic
throughput, interactive hop topology, Meeting Guard/QoS state, Wi-Fi & Router
summary, DNS health, actionable recommendations, and recent diagnostic events.
"""

from __future__ import annotations

from datetime import datetime
import math
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.models.metrics import Diagnosis, DiagnosisSeverity, MetricType, ProbableCause
from app.core.network_state import GlobalNetworkStateStore, normalize_network_identity_payload
from app.core.thresholds import DEFAULT_THRESHOLDS
from app.ui import tokens
from app.ui.animation_clock import AnimationMasterClock
from app.ui.i18n import get_language, language_manager, tr
from app.ui.icons import create_icon
from app.ui.widgets.bar_row import DNSRecommendationPanel, TrafficConsumersPanel
from app.ui.widgets.base_panel import Panel
from app.ui.widgets.buttons import GhostButton, PrimaryButton, SecondaryButton
from app.ui.widgets.chip import Chip
from app.ui.widgets.circular_gauge import CircularGauge
from app.ui.widgets.day_strip import DayStrip
from app.ui.widgets.flow_path import FlowPathPanel
from app.ui.widgets.latency_chart import LatencyChart
from app.ui.widgets.metric_cell import MetricsStrip
from app.ui.widgets.network_info_strip import NetworkInfoStrip
from app.ui.widgets.status_badge import StatusBadge
from app.ui.widgets.timeline import TimelinePanel
from app.ui.widgets.topology_widget import NetworkTopologyWidget
from app.ui.widgets.traffic_chart import TrafficThroughputChart


def compute_genuine_health_score(
    *,
    gw_ms: Optional[float] = None,
    ext_ms: Optional[float] = None,
    loss_pct: Optional[float] = None,
    jitter_ms: Optional[float] = None,
    dns_ms: Optional[float] = None,
    wifi_pct: Optional[float] = None,
    internet_available: Optional[bool] = None,
    gateway_reachable: Optional[bool] = None,
) -> Tuple[Optional[int], str, str]:
    """Compute a documented, deterministic network health score (0-100).

    Returns ``(score_or_none, status_enum, reason_summary)``.
    Never invents a default high score when no real probes exist or internet is unreachable.
    """
    if gw_ms is None and ext_ms is None and dns_ms is None and wifi_pct is None:
        if gateway_reachable is False:
            return 20, tokens.SystemStatus.FAILED, tr("dash.note_gw_high")
        if internet_available is False:
            return 35, tokens.SystemStatus.FAILED, tr("dash.note_ext_high")
        return None, tokens.SystemStatus.WAITING, tr("dash.awaiting_probes")

    if gateway_reachable is False:
        return 25, tokens.SystemStatus.FAILED, tr("dash.note_gw_high")

    if internet_available is False or (loss_pct is not None and loss_pct >= 99.0):
        return 35, tokens.SystemStatus.FAILED, tr("dash.note_packet_loss")

    score = 100.0
    notes: List[str] = []

    if gw_ms is not None and gw_ms > 15.0:
        penalty = min(22.0, (gw_ms - 15.0) * 0.5)
        score -= penalty
        if gw_ms >= 35.0:
            notes.append(tr("dash.note_gw_high"))

    if ext_ms is not None:
        warn_ms = float(DEFAULT_THRESHOLDS.latency.external_warning_ms)
        if ext_ms > warn_ms:
            penalty = min(30.0, (ext_ms - warn_ms) * 0.25)
            score -= penalty
            notes.append(tr("dash.note_ext_high"))

    if loss_pct is not None and loss_pct > 0.0:
        penalty = min(45.0, loss_pct * 9.0)
        score -= penalty
        notes.append(tr("dash.note_packet_loss"))

    if jitter_ms is not None and jitter_ms > 15.0:
        penalty = min(15.0, (jitter_ms - 15.0) * 0.5)
        score -= penalty

    if dns_ms is not None and dns_ms > 45.0:
        penalty = min(14.0, (dns_ms - 45.0) * 0.12)
        score -= penalty
        if dns_ms >= 80.0:
            notes.append(tr("dash.note_dns_slow"))

    if wifi_pct is not None and wifi_pct < 60.0:
        penalty = min(18.0, (60.0 - wifi_pct) * 0.45)
        score -= penalty
        notes.append(tr("dash.note_wifi_weak"))

    final = max(0, min(100, int(round(score))))
    if final >= 80:
        status = tokens.SystemStatus.HEALTHY
        summary = tr("dash.health_good")
    elif final >= 55:
        status = tokens.SystemStatus.WARNING
        summary = " · ".join(notes[:2]) if notes else tr("dash.health_degraded")
    else:
        status = tokens.SystemStatus.FAILED
        summary = " · ".join(notes[:2]) if notes else tr("dash.health_critical")
    return final, status, summary


class StatusIndicatorDot(QWidget):
    """Pulsing live connection dot."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.color_str = tokens.STATUS_OK
        self._status_color = self.color_str
        self._phase = 0.0
        self._paused = False
        if tokens.ANIMATIONS_ENABLED:
            AnimationMasterClock.get_instance().subscribe(self._tick)

    def set_status(self, color: str = tokens.STATUS_OK) -> None:
        if self.color_str != color or self._status_color != color:
            self.color_str = color
            self._status_color = color
            self.update()

    def set_paused(self, paused: bool) -> None:
        self._paused = paused
        if paused:
            AnimationMasterClock.get_instance().unsubscribe(self._tick)
        else:
            AnimationMasterClock.get_instance().subscribe(self._tick)

    def _tick(self, delta_ms: float = 50.0) -> None:
        if self._paused or AnimationMasterClock.get_instance().is_low_resource_mode:
            return
        self._phase = (self._phase + 0.04 * (delta_ms / 50.0)) % 1.0
        self.update()

    def paintEvent(self, event) -> None:
        from PySide6.QtGui import QBrush, QColor, QPainter, QPen

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        c = QColor(self.color_str)
        ring = QColor(self.color_str)
        ring.setAlpha(int(120 * (1.0 - self._phase)))
        painter.setPen(QPen(ring, 1.2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(self.rect().center(), 4.5 + self._phase * 3.5, 4.5 + self._phase * 3.5)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(c))
        painter.drawEllipse(self.rect().center(), 4.5, 4.5)


class DashboardView(QWidget):
    """Redesigned Dashboard Overview."""

    quick_scan_requested = Signal()
    meeting_preflight_requested = Signal()
    export_report_requested = Signal()
    navigate_requested = Signal(int)

    def set_animations_paused(self, paused: bool) -> None:
        if hasattr(self, "latency_chart"):
            self.latency_chart.set_paused(paused)
        if hasattr(self, "flow_path"):
            self.flow_path.set_paused(paused)
        if hasattr(self, "hero_dot"):
            self.hero_dot.set_paused(paused)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._outer_v = QVBoxLayout(self)
        self._outer_v.setContentsMargins(0, 0, 0, 0)
        self._outer_v.setSpacing(0)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self._outer_v.addWidget(self.scroll)

        self._last_speed_test_time: Optional[str] = None
        self._last_speed_test_dt: Optional[datetime] = None
        self._last_obs: Any = None
        self._last_diag: Optional[Diagnosis] = None
        self._last_net_info: Dict[str, Any] = {}
        self._network_info: Dict[str, Any] = {}
        self._last_dns_ms: Optional[float] = None
        self._last_dns_ip: str = "—"
        self._last_dns_name: str = "—"
        self._last_gw_ms: Optional[float] = None
        self._last_ext_ms: Optional[float] = None
        self._last_wifi_pct: Optional[float] = None
        self._last_connected_devices: Optional[int] = None
        self._layout_mode: str = "desktop"

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self.container_widget = container

        outer_layout = QHBoxLayout(container)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setAlignment(Qt.AlignHCenter)

        self.content_holder = QWidget()
        self.content_holder.setMaximumWidth(tokens.MAX_CONTENT_WIDTH)
        self.content_holder.setStyleSheet("background: transparent;")

        self.root_layout = QVBoxLayout(self.content_holder)
        self.root_layout.setContentsMargins(24, 20, 24, 32)
        self.root_layout.setSpacing(16)

        outer_layout.addWidget(self.content_holder)
        self.scroll.setWidget(container)

        # ------------------------------------------------------------------
        # 1. Hero Overview Panel (Health Gauge + Live Network Summary + Actions)
        # ------------------------------------------------------------------
        hero_card = QFrame()
        hero_card.setObjectName("DashHeroCard")
        hero_card.setStyleSheet(
            f"""
            QFrame#DashHeroCard {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_PANEL}px;
            }}
            """
        )
        # Make hero responsive so collapsed 820px view wraps hero controls gracefully
        self.hero_lay = QHBoxLayout(hero_card)
        self.hero_lay.setContentsMargins(20, 16, 20, 16)
        self.hero_lay.setSpacing(16)
        hero_lay = self.hero_lay

        self.health_gauge = CircularGauge(
            title=tr("dash.health_gauge"),
            unit="%",
            size=122,
            semicircular=False,
        )
        self.health_gauge.set_value(None, subtitle=tr("status.waiting"))
        hero_lay.addWidget(self.health_gauge, alignment=Qt.AlignVCenter)

        hero_mid = QVBoxLayout()
        hero_mid.setSpacing(6)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        self.hero_dot = StatusIndicatorDot()
        self.status_dot = self.hero_dot
        self.hero_dot.set_status(tokens.TEXT_MUTED)
        self.lbl_hero_title = QLabel(tr("dash.hero_initializing"))
        self.lbl_hero_title.setFont(tokens.get_sans_font(20, 700))
        self.lbl_hero_title.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_hero_title.setWordWrap(True)

        self.badge_hero_status = StatusBadge(tokens.SystemStatus.WAITING, tr("status.waiting"))
        title_row.addWidget(self.hero_dot)
        title_row.addWidget(self.lbl_hero_title, 1)
        title_row.addWidget(self.badge_hero_status)
        hero_mid.addLayout(title_row)

        self.lbl_hero_desc = QLabel(tr("dash.hero_desc_init"))
        self.lbl_hero_desc.setFont(tokens.get_sans_font(13, 400))
        self.lbl_hero_desc.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_hero_desc.setWordWrap(True)
        hero_mid.addWidget(self.lbl_hero_desc)

        self.probe_alert_banner = QFrame()
        self.probe_alert_bar = self.probe_alert_banner
        self.probe_alert_banner.setVisible(False)
        self.probe_alert_banner.setStyleSheet(
            f"background-color: {tokens.WARN_SOFT_BG}; border: 1px solid {tokens.WARN_BORDER}; border-radius: 6px;"
        )
        alert_lay = QHBoxLayout(self.probe_alert_banner)
        alert_lay.setContentsMargins(10, 6, 10, 6)
        self.lbl_probe_alert = QLabel("")
        self.lbl_probe_alert_msg = self.lbl_probe_alert
        self.lbl_probe_alert.setFont(tokens.get_sans_font(12, 500))
        self.lbl_probe_alert.setStyleSheet(f"color: {tokens.STATUS_WARN}; border: none; background: transparent;")
        self.lbl_probe_alert.setWordWrap(True)
        alert_lay.addWidget(self.lbl_probe_alert)
        hero_mid.addWidget(self.probe_alert_banner)

        meta_chips_row = QHBoxLayout()
        meta_chips_row.setSpacing(8)
        self.chip_conn_summary = Chip(tr("dash.adapter_pending"), variant="neutral", font_size=12)
        self.chip_guard_summary = Chip(tr("dash.guard_idle"), variant="info", font_size=12)
        self.chip_speed_timestamp = Chip(tr("dash.no_speed_test"), variant="neutral", font_size=12)
        meta_chips_row.addWidget(self.chip_conn_summary)
        meta_chips_row.addWidget(self.chip_guard_summary)
        meta_chips_row.addWidget(self.chip_speed_timestamp)
        meta_chips_row.addStretch()
        hero_mid.addLayout(meta_chips_row)

        hero_lay.addLayout(hero_mid, 1)

        actions_col = QVBoxLayout()
        actions_col.setSpacing(8)
        self.btn_scan = PrimaryButton(tr("dash.btn_quick_scan"))
        self.btn_scan.setIcon(create_icon("internet_quality", tokens.ON_ACCENT, 15))
        self.btn_scan.clicked.connect(self._on_scan_clicked)

        self.btn_preflight = SecondaryButton(tr("dash.btn_preflight"))
        self.btn_preflight.setIcon(create_icon("meeting_guard", tokens.TEXT, 15))
        self.btn_preflight.clicked.connect(self.meeting_preflight_requested.emit)

        self.btn_export = GhostButton(tr("dash.btn_export"))
        self.btn_export.setIcon(create_icon("reports", tokens.TEXT_MUTED, 15))
        self.btn_export.clicked.connect(self.export_report_requested.emit)

        actions_col.addWidget(self.btn_scan)
        actions_col.addWidget(self.btn_preflight)
        actions_col.addWidget(self.btn_export)
        hero_lay.addLayout(actions_col)
        self.root_layout.addWidget(hero_card)

        # ------------------------------------------------------------------
        # 2. Primary Telemetry Metrics Strip
        # ------------------------------------------------------------------
        self.metrics_strip = MetricsStrip()
        self.root_layout.addWidget(self.metrics_strip)

        # ------------------------------------------------------------------
        # 3. Real-Time Charts & Live Network Topology
        # ------------------------------------------------------------------
        self.charts_grid = QGridLayout()
        self.charts_grid.setSpacing(14)

        self.latency_chart = LatencyChart()
        self.traffic_chart = TrafficThroughputChart(title=tr("dash.live_traffic"))
        self.topology_widget = NetworkTopologyWidget()

        self.charts_grid.addWidget(self.latency_chart, 0, 0)
        self.charts_grid.addWidget(self.traffic_chart, 0, 1)
        self.root_layout.addLayout(self.charts_grid)
        self.root_layout.addWidget(self.topology_widget)

        # Keep FlowPathPanel hidden/syncable for legacy MainWindow/test compatibility
        self.flow_path = FlowPathPanel()
        self.flow_path.setVisible(False)
        self.root_layout.addWidget(self.flow_path)

        # ------------------------------------------------------------------
        # 4. Operational Domain Summaries (Meeting/QoS, Wi-Fi/Router, DNS/Recs)
        # ------------------------------------------------------------------
        self.summary_grid = QGridLayout()
        self.summary_grid.setSpacing(14)

        # 4a. Meeting Guard & QoS Summary
        self.panel_guard = Panel(
            title=tr("dash.guard_panel_title"),
            subtitle=tr("dash.guard_panel_sub"),
            padding=18,
        )
        self.btn_goto_guard = GhostButton(tr("dash.open_section"))
        self.btn_goto_guard.clicked.connect(lambda: self.navigate_requested.emit(1))
        self.panel_guard.set_header_widget(self.btn_goto_guard)

        self.badge_guard_card = StatusBadge(tokens.SystemStatus.WAITING, tr("status.waiting"))
        self.lbl_guard_details = QLabel(tr("dash.guard_idle_detail"))
        self.lbl_guard_details.setFont(tokens.get_sans_font(12, 400))
        self.lbl_guard_details.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_guard_details.setWordWrap(True)
        self.lbl_qos_rules_summary = QLabel(tr("dash.qos_pending"))
        self.lbl_qos_rules_summary.setFont(tokens.get_mono_font(12, 500))
        self.lbl_qos_rules_summary.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_qos_rules_summary.setWordWrap(True)

        self.panel_guard.main_layout.addWidget(self.badge_guard_card, alignment=Qt.AlignLeft)
        self.panel_guard.main_layout.addWidget(self.lbl_guard_details)
        self.panel_guard.main_layout.addWidget(self.lbl_qos_rules_summary)
        self.panel_guard.main_layout.addStretch()

        # 4b. Wi-Fi & Router Summary
        self.panel_wifi_router = Panel(
            title=tr("dash.wifi_router_title"),
            subtitle=tr("dash.wifi_router_sub"),
            padding=18,
        )
        wifi_btn_row = QHBoxLayout()
        self.btn_goto_wifi = GhostButton(tr("nav.wifi_intelligence"))
        self.btn_goto_wifi.clicked.connect(lambda: self.navigate_requested.emit(4))
        self.btn_goto_router = GhostButton(tr("nav.router_management"))
        self.btn_goto_router.clicked.connect(lambda: self.navigate_requested.emit(5))
        wifi_btn_row.addWidget(self.btn_goto_wifi)
        wifi_btn_row.addWidget(self.btn_goto_router)
        wr_btn_wrap = QWidget()
        wr_btn_wrap.setLayout(wifi_btn_row)
        self.panel_wifi_router.set_header_widget(wr_btn_wrap)

        wr_body = QHBoxLayout()
        wr_body.setSpacing(14)
        self.wifi_mini_gauge = CircularGauge(
            title=tr("dash.wifi_quality"),
            unit="%",
            size=96,
            semicircular=True,
        )
        self.wifi_mini_gauge.set_value(None, subtitle=tr("status.unavailable"))
        wr_body.addWidget(self.wifi_mini_gauge)

        wr_lines = QVBoxLayout()
        wr_lines.setSpacing(4)
        self.lbl_wifi_summary = QLabel(tr("dash.wifi_unmeasured"))
        self.lbl_wifi_summary.setFont(tokens.get_sans_font(12, 500))
        self.lbl_wifi_summary.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_wifi_summary.setWordWrap(True)
        self.lbl_router_summary = QLabel(tr("dash.router_unconfigured"))
        self.lbl_router_summary.setFont(tokens.get_sans_font(12, 400))
        self.lbl_router_summary.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_router_summary.setWordWrap(True)
        wr_lines.addWidget(self.lbl_wifi_summary)
        wr_lines.addWidget(self.lbl_router_summary)
        wr_lines.addStretch()
        wr_body.addLayout(wr_lines, 1)
        self.panel_wifi_router.main_layout.addLayout(wr_body)

        # 4c. Recommendations Card
        self.panel_recs = Panel(
            title=tr("dash.recs_title"),
            subtitle=tr("dash.recs_sub"),
            padding=18,
        )
        self.lbl_recs_body = QLabel(tr("dash.recs_empty"))
        self.lbl_recs_body.setFont(tokens.get_sans_font(12, 400))
        self.lbl_recs_body.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_recs_body.setWordWrap(True)
        self.panel_recs.main_layout.addWidget(self.lbl_recs_body)
        self.panel_recs.main_layout.addStretch()

        self.summary_grid.addWidget(self.panel_guard, 0, 0)
        self.summary_grid.addWidget(self.panel_wifi_router, 0, 1)
        self.summary_grid.addWidget(self.panel_recs, 0, 2)
        self.root_layout.addLayout(self.summary_grid)

        # ------------------------------------------------------------------
        # 5. Consumers + DNS Panel + Diagnostic Timeline + Day Strip
        # ------------------------------------------------------------------
        self.bottom_grid = QGridLayout()
        self.bottom_grid.setSpacing(14)

        self.consumers_panel = TrafficConsumersPanel()
        self.dns_panel = DNSRecommendationPanel()
        self.bottom_grid.addWidget(self.consumers_panel, 0, 0)
        self.bottom_grid.addWidget(self.dns_panel, 0, 1)
        self.root_layout.addLayout(self.bottom_grid)

        self.timeline_panel = TimelinePanel()
        self.root_layout.addWidget(self.timeline_panel)

        self.day_strip = DayStrip()
        self.root_layout.addWidget(self.day_strip)

        self.network_strip = NetworkInfoStrip()
        self.root_layout.addWidget(self.network_strip)

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(5000)
        self._tick_timer.timeout.connect(self._on_second_tick)
        self._tick_timer.start()

        language_manager().language_changed.connect(self.retranslate)

    def retranslate(self) -> None:
        self.btn_scan.setText(tr("dash.btn_quick_scan"))
        self.btn_preflight.setText(tr("dash.btn_preflight"))
        self.btn_export.setText(tr("dash.btn_export"))
        self.panel_guard.set_titles(tr("dash.guard_panel_title"), tr("dash.guard_panel_sub"))
        self.panel_wifi_router.set_titles(tr("dash.wifi_router_title"), tr("dash.wifi_router_sub"))
        self.panel_recs.set_titles(tr("dash.recs_title"), tr("dash.recs_sub"))
        self.btn_goto_guard.setText(tr("dash.open_section"))
        self.btn_goto_wifi.setText(tr("nav.wifi_intelligence"))
        self.btn_goto_router.setText(tr("nav.router_management"))
        is_en = get_language() == "en"
        if hasattr(self, "metrics_strip"):
            self.metrics_strip.cell_latency.title_lbl.setText("Latency" if is_en else "زمن الاستجابة")
            self.metrics_strip.cell_jitter.title_lbl.setText("Jitter" if is_en else "التذبذب")
            self.metrics_strip.cell_loss.title_lbl.setText("Packet Loss" if is_en else "فقدان الحزم")
            self.metrics_strip.cell_download.title_lbl.setText("Download Rate" if is_en else "سرعة التنزيل")
        if hasattr(self, "latency_chart"):
            self.latency_chart.lbl_title.setText("Latency" if is_en else "زمن الاستجابة")
            self.latency_chart.lbl_sub.setText(
                "Round-trip internet latency. Lower is better."
                if is_en
                else "الوقت اللازم لوصول بياناتك إلى الإنترنت والعودة. الأقل أفضل."
            )
            self.latency_chart.canvas.update()
        if hasattr(self, "traffic_chart"):
            self.traffic_chart.lbl_title.setText(tr("dash.live_traffic"))
        if self._last_obs is not None:
            self.update_telemetry(self._last_obs, self._last_diag)
        else:
            self.lbl_hero_title.setText(tr("dash.hero_initializing"))
            self.lbl_hero_desc.setText(tr("dash.hero_desc_init"))
            self.badge_hero_status.set_status(tokens.SystemStatus.WAITING, tr("status.waiting"))
            self.health_gauge.set_value(None, subtitle=tr("status.waiting"))

    def _on_second_tick(self) -> None:
        if not self.isVisible():
            return
        if self._last_speed_test_dt:
            elapsed = max(0, int((datetime.now() - self._last_speed_test_dt).total_seconds()))
            if elapsed < 60:
                txt = tr("dash.speed_ago_sec", val=elapsed)
            else:
                txt = tr("dash.speed_ago_min", val=elapsed // 60)
            self.chip_speed_timestamp.setText(txt)

    def set_last_speed_test_time(self, time_str: str) -> None:
        self._last_speed_test_time = str(time_str)
        self._last_speed_test_dt = datetime.now()
        self.chip_speed_timestamp.setText(tokens.bidi_isolate_mixed(f"آخر فحص: {time_str}"))
        self.chip_speed_timestamp.set_variant("ok-soft")
        self.metrics_strip.cell_download.footer_lbl.setText(f"آخر فحص: {time_str}")

    def _on_scan_clicked(self) -> None:
        self.btn_scan.setText(tr("dash.scanning"))
        self.btn_scan.setEnabled(False)
        self.quick_scan_requested.emit()

    def _on_scan_completed(self) -> None:
        self.btn_scan.setText(tr("dash.btn_quick_scan"))
        self.btn_scan.setEnabled(True)

    def update_shield(self, is_healthy: Any, title: str = "", desc: str = "", **kwargs) -> None:
        if is_healthy is True:
            self.badge_hero_status.set_status(tokens.SystemStatus.HEALTHY, tr("status.healthy"))
            self.hero_dot.set_status(tokens.STATUS_OK)
        elif is_healthy is False:
            self.badge_hero_status.set_status(tokens.SystemStatus.FAILED, tr("status.failed"))
            self.hero_dot.set_status(tokens.STATUS_BAD)
        else:
            self.badge_hero_status.set_status(tokens.SystemStatus.WARNING, tr("status.warning"))
            self.hero_dot.set_status(tokens.STATUS_WARN)
        if title:
            self.lbl_hero_title.setText(title)
        if desc:
            self.lbl_hero_desc.setText(desc)

    def update_daily_incident_summary(self, interventions_count: int, avg_duration_sec: Optional[float] = None) -> None:
        if interventions_count > 0:
            dur = f"{avg_duration_sec:.1f}s" if avg_duration_sec else "—"
            self.chip_guard_summary.setText(
                tokens.bidi_isolate_mixed(f"{tr('dash.interventions')}: {interventions_count} ({dur})")
            )

    def set_probe_status_alert(self, error_message: Optional[str]) -> None:
        has_err = bool(error_message and error_message.strip())
        self.probe_alert_banner.setVisible(has_err)
        if has_err:
            self.lbl_probe_alert.setText(tokens.bidi_isolate_mixed(error_message or ""))
            self.hero_dot.set_status(tokens.STATUS_WARN)
        else:
            self.hero_dot.set_status(tokens.STATUS_OK)

    def update_network_identity(self, info: Dict[str, Any]) -> None:
        norm = normalize_network_identity_payload(info)
        self._last_net_info = norm
        self._network_info = self._last_net_info
        self.network_strip.update_info(self._last_net_info)

        adapter = str(norm.get("interface_name") or norm.get("iface") or "—")
        conn_type = str(norm.get("connection_type") or norm.get("medium") or "")
        gw_ip = str(norm.get("gateway_ip") or norm.get("gateway") or "—")
        ssid = str(norm.get("ssid") or "")
        if ssid.lower() in ("غير متصل", "—", "-"):
            ssid = ""
        label_parts: List[str] = []
        seen_lp: set[str] = set()
        for p in (conn_type, ssid, adapter):
            if p and p != "—" and p.strip().lower() not in seen_lp:
                seen_lp.add(p.strip().lower())
                label_parts.append(p)
        summary_txt = " · ".join(label_parts) if label_parts else tr("dash.adapter_pending")
        self.chip_conn_summary.setText(tokens.bidi_isolate_mixed(summary_txt))

        dns_servers = norm.get("dns_servers") or []
        if dns_servers:
            self._last_dns_ip = str(dns_servers[0])

        self._refresh_topology_widget(gw_ip=gw_ip or "—", info=norm)

    def update_wifi_and_router_summary(
        self,
        *,
        ssid: Optional[str] = None,
        band: Optional[str] = None,
        channel: Optional[int] = None,
        rssi_dbm: Optional[int] = None,
        wifi_quality_pct: Optional[float] = None,
        router_model: Optional[str] = None,
        router_ip: Optional[str] = None,
        connected_devices_count: Optional[int] = None,
    ) -> None:
        """Update real Wi-Fi & Router card metrics without fabricating unknown data."""
        self._last_wifi_pct = wifi_quality_pct
        self._last_connected_devices = connected_devices_count

        if wifi_quality_pct is not None:
            color = (
                tokens.STATUS_OK
                if wifi_quality_pct >= 70
                else (tokens.STATUS_WARN if wifi_quality_pct >= 45 else tokens.STATUS_BAD)
            )
            self.wifi_mini_gauge.set_value(
                wifi_quality_pct,
                subtitle=f"{rssi_dbm} dBm" if rssi_dbm is not None else tr("status.active"),
                color=color,
            )
            wifi_bits = [b for b in (ssid, band, f"CH {channel}" if channel else None) if b]
            self.lbl_wifi_summary.setText(
                tokens.bidi_isolate_mixed(" · ".join(wifi_bits) if wifi_bits else tr("status.active"))
            )
        else:
            self.wifi_mini_gauge.set_value(None, subtitle=tr("status.unavailable"))

        if router_model or router_ip:
            dev_part = (
                f" · {tr('dash.devices_count', n=connected_devices_count)}"
                if connected_devices_count is not None
                else ""
            )
            r_txt = f"{router_model or tr('nav.router_management')} ({router_ip or '—'}){dev_part}"
            self.lbl_router_summary.setText(tokens.bidi_isolate_mixed(r_txt))

        self._refresh_topology_widget(
            gw_ip=router_ip or str(self._last_net_info.get("gateway_ip") or "—"),
            info=self._last_net_info,
        )

    def update_meeting_guard_summary(
        self,
        *,
        meeting_active: bool,
        app_name: Optional[str] = None,
        verified_rules: int = 0,
        configured_rules: int = 0,
        lifecycle_stage: str = "idle",
    ) -> None:
        if meeting_active:
            self.badge_guard_card.set_status(tokens.SystemStatus.ACTIVE, tr("status.active"))
            self.chip_guard_summary.setText(
                tokens.bidi_isolate_mixed(f"{tr('dash.guard_protecting')}: {app_name or 'Meeting'}")
            )
            self.chip_guard_summary.set_variant("ok-soft")
            self.lbl_guard_details.setText(
                tokens.bidi_isolate_mixed(
                    tr("dash.guard_active_detail", app=app_name or "Meeting", stage=lifecycle_stage)
                )
            )
        else:
            self.badge_guard_card.set_status(tokens.SystemStatus.RUNNING, tr("status.running"))
            self.chip_guard_summary.setText(tr("dash.guard_idle"))
            self.chip_guard_summary.set_variant("info")
            self.lbl_guard_details.setText(tr("dash.guard_idle_detail"))

        if configured_rules > 0:
            self.lbl_qos_rules_summary.setText(
                tokens.bidi_isolate_mixed(
                    tr("dash.qos_verified_count", verified=verified_rules, total=configured_rules)
                )
            )
        else:
            self.lbl_qos_rules_summary.setText(tr("dash.qos_pending"))

    def _refresh_topology_widget(self, *, gw_ip: str, info: Dict[str, Any]) -> None:
        adapter_name = str(info.get("interface_name") or info.get("adapter_name") or tr("dash.local_adapter"))
        conn_type = str(info.get("connection_type") or info.get("medium") or "LAN/Wi-Fi")
        router_label = str(info.get("router_model") or tr("dash.router_node"))
        public_ip = info.get("public_ip")
        self.topology_widget.set_topology(
            adapter_name=adapter_name,
            adapter_type=conn_type,
            router_label=router_label,
            gateway_ip=gw_ip,
            gateway_ms=self._last_gw_ms,
            dns_ip=self._last_dns_ip,
            dns_ms=self._last_dns_ms,
            internet_ms=self._last_ext_ms,
            connected_devices_count=self._last_connected_devices,
            public_ip=str(public_ip) if public_ip else None,
        )

    @staticmethod
    def _safe_sliding_window(obs: Any, mt: MetricType, count: int = 20) -> List[Any]:
        if obs is None or not hasattr(obs, "get_sliding_window"):
            return []
        try:
            return list(obs.get_sliding_window(mt, count) or [])
        except TypeError:
            try:
                return list(obs.get_sliding_window(mt) or [])[-count:]
            except Exception:
                return []

    @staticmethod
    def _valid_num(val: Any) -> Optional[float]:
        if val is None:
            return None
        try:
            f = float(val)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(f) or f < 0.0:
            return None
        return f

    def update_telemetry(self, obs, last_diag: Optional[Diagnosis]) -> None:
        self._last_obs = obs
        self._last_diag = last_diag

        if obs is None:
            dl_footer = f"آخر فحص: {self._last_speed_test_time}" if self._last_speed_test_time else "غير متصل"
            self.metrics_strip.cell_latency.update_metric(" — ", "غير متصل", samples=[], status_color=tokens.TEXT_MUTED)
            self.metrics_strip.cell_jitter.update_metric(" — ", "غير متصل", samples=[], status_color=tokens.TEXT_MUTED)
            self.metrics_strip.cell_loss.update_metric(" — ", "غير متصل", samples=[], status_color=tokens.TEXT_MUTED)
            self.metrics_strip.cell_download.update_metric(" — ", dl_footer, samples=[], status_color=tokens.TEXT_MUTED)
            self.traffic_chart.set_series([], [], [])
            self.latency_chart.update_telemetry([])
            self.health_gauge.set_value(None, subtitle=tr("status.waiting"))
            return

        err_msg = None
        if hasattr(obs, "get_primary_probe_error_message"):
            err_msg = obs.get_primary_probe_error_message()
        self.set_probe_status_alert(err_msg)

        # Latest metrics (guarding NaN/negative values strictly)
        m_ext = obs.get_latest_measurement(MetricType.EXTERNAL_LATENCY)
        m_gw = obs.get_latest_measurement(MetricType.GATEWAY_LATENCY)
        m_jitter = obs.get_latest_measurement(MetricType.JITTER_MS)
        m_loss = obs.get_latest_measurement(MetricType.EXTERNAL_PACKET_LOSS)
        if m_loss is None:
            m_loss = obs.get_latest_measurement(MetricType.GATEWAY_PACKET_LOSS)
        m_dns = obs.get_latest_measurement(MetricType.DNS_LATENCY)
        m_wifi = obs.get_latest_measurement(MetricType.WIFI_SIGNAL_PERCENT)
        m_rx = obs.get_latest_measurement(MetricType.BANDWIDTH_RX_BYTES_PER_SEC)
        m_tx = obs.get_latest_measurement(MetricType.BANDWIDTH_TX_BYTES_PER_SEC)

        ext_val = self._valid_num(getattr(m_ext, "normalized_value", None))
        gw_val = self._valid_num(getattr(m_gw, "normalized_value", None))
        jit_val = self._valid_num(getattr(m_jitter, "normalized_value", None))
        loss_val = self._valid_num(getattr(m_loss, "normalized_value", None))
        dns_val = self._valid_num(getattr(m_dns, "normalized_value", None))
        wifi_raw = self._valid_num(getattr(m_wifi, "normalized_value", None))
        wifi_val = wifi_raw if wifi_raw is not None else self._last_wifi_pct
        rx_bps = self._valid_num(getattr(m_rx, "normalized_value", None))
        tx_bps = self._valid_num(getattr(m_tx, "normalized_value", None))

        self._last_gw_ms = gw_val
        self._last_ext_ms = ext_val
        if dns_val is not None:
            self._last_dns_ms = dns_val
        if wifi_val is not None:
            self._last_wifi_pct = wifi_val

        # Metric Strip updates
        ext_window = self._safe_sliding_window(obs, MetricType.EXTERNAL_LATENCY, 20)
        ext_samples = [v for v in (self._valid_num(getattr(m, "normalized_value", None)) for m in ext_window) if v is not None]
        if ext_val is not None:
            is_warn = ext_val >= float(DEFAULT_THRESHOLDS.latency.external_warning_ms)
            self.metrics_strip.cell_latency.update_metric(
                f"{ext_val:.0f}",
                tr("dash.status_warn") if is_warn else tr("dash.status_stable"),
                is_warning=is_warn,
                samples=ext_samples,
            )
        else:
            self.metrics_strip.cell_latency.update_metric(" — ", "غير متصل", samples=[], status_color=tokens.TEXT_MUTED)

        jit_window = self._safe_sliding_window(obs, MetricType.JITTER_MS, 20)
        jit_samples = [v for v in (self._valid_num(getattr(m, "normalized_value", None)) for m in jit_window) if v is not None]
        if jit_val is not None:
            if jit_val < 10.0:
                jit_footer, jit_col, jit_warn = tr("dash.jitter_good"), tokens.STATUS_OK, False
            elif jit_val < 30.0:
                jit_footer, jit_col, jit_warn = "جيد • مناسب للمكالمات", tokens.STATUS_OK, False
            elif jit_val <= 50.0:
                jit_footer, jit_col, jit_warn = "متوسط • قد يؤثر على المكالمات", tokens.STATUS_WARN, True
            else:
                jit_footer, jit_col, jit_warn = "مرتفع • يؤثر بشدة على المكالمات", tokens.STATUS_BAD, True
            self.metrics_strip.cell_jitter.update_metric(
                f"{jit_val:.1f}",
                jit_footer,
                is_warning=jit_warn,
                samples=jit_samples,
                status_color=jit_col,
            )
        else:
            self.metrics_strip.cell_jitter.update_metric(" — ", "غير متصل", samples=[], status_color=tokens.TEXT_MUTED)

        loss_window = self._safe_sliding_window(obs, MetricType.EXTERNAL_PACKET_LOSS, 20)
        if not loss_window:
            loss_window = self._safe_sliding_window(obs, MetricType.GATEWAY_PACKET_LOSS, 20)
        loss_unit = str(getattr(m_loss, "unit", "") or "").lower()
        loss_pct = (loss_val * 100.0) if (loss_val is not None and loss_unit == "ratio") else loss_val
        loss_samples = [
            (v * 100.0 if str(getattr(m, "unit", "") or "").lower() == "ratio" else v)
            for m in loss_window
            for v in (self._valid_num(getattr(m, "normalized_value", None)),)
            if v is not None
        ]
        if loss_pct is not None:
            is_warn = loss_pct > 0.5
            if loss_pct >= 99.9:
                loss_footer = "انقطاع كامل في الحزم"
                loss_col = tokens.STATUS_BAD
            elif is_warn:
                loss_footer = tr("dash.loss_detected")
                loss_col = tokens.STATUS_BAD if loss_pct >= 5.0 else tokens.STATUS_WARN
            else:
                loss_footer = tr("dash.loss_zero")
                loss_col = tokens.STATUS_OK
            self.metrics_strip.cell_loss.update_metric(
                f"{loss_pct:.1f}",
                loss_footer,
                is_warning=is_warn,
                samples=loss_samples,
                status_color=loss_col,
            )
        else:
            self.metrics_strip.cell_loss.update_metric(" — ", "غير متصل", samples=[], status_color=tokens.TEXT_MUTED)

        # Download & Upload throughput windows
        rx_win = self._safe_sliding_window(obs, MetricType.BANDWIDTH_RX_BYTES_PER_SEC, 40)
        tx_win = self._safe_sliding_window(obs, MetricType.BANDWIDTH_TX_BYTES_PER_SEC, 40)
        dl_mbps_list = [round(v * 8.0 / 1_000_000.0, 2) for v in (self._valid_num(getattr(m, "normalized_value", None)) for m in rx_win) if v is not None]
        ul_mbps_list = [round(v * 8.0 / 1_000_000.0, 2) for v in (self._valid_num(getattr(m, "normalized_value", None)) for m in tx_win) if v is not None]
        ts_list = [m.timestamp.strftime("%H:%M:%S") for m in rx_win if getattr(m, "timestamp", None)]
        self.traffic_chart.set_series(dl_mbps_list, ul_mbps_list, ts_list)

        if rx_bps is not None:
            latest_dl = rx_bps * 8.0 / 1_000_000.0
            latest_ul = (tx_bps * 8.0 / 1_000_000.0) if tx_bps is not None else None
            dl_txt = f"{latest_dl:.0f}" if latest_dl >= 10.0 else f"{latest_dl:.1f}"
            ul_txt = f"{latest_ul:.1f}" if (latest_ul is not None and latest_ul > 0.0) else f"{0.0:.2f}"
            footer_dl = f"الرفع {ul_txt} Mbps"
            if self._last_speed_test_time:
                footer_dl = f"{footer_dl} · آخر فحص: {self._last_speed_test_time}"
            dl_samples = dl_mbps_list[-20:] if dl_mbps_list else [round(latest_dl, 2)]
            self.metrics_strip.cell_download.update_metric(
                dl_txt,
                footer_dl,
                samples=dl_samples,
                status_color=tokens.SECONDARY_CYAN,
            )
        else:
            dl_footer = f"آخر فحص: {self._last_speed_test_time}" if self._last_speed_test_time else "غير متصل"
            self.metrics_strip.cell_download.update_metric(" — ", dl_footer, samples=[], status_color=tokens.TEXT_MUTED)

        # Latency chart
        lat_win = self._safe_sliding_window(obs, MetricType.EXTERNAL_LATENCY, 60)
        lat_vals = [v for v in (self._valid_num(getattr(m, "normalized_value", None)) for m in lat_win) if v is not None]
        if lat_vals:
            avg_ms = sum(lat_vals) / len(lat_vals)
            max_ms = max(lat_vals)
            self.latency_chart.update_telemetry(lat_vals, avg_ms=avg_ms, max_ms=max_ms, duration_str="—")
        else:
            self.latency_chart.update_telemetry([])

        # Flow path sync
        self.flow_path.update_node_latency(1, gw_val, "warn" if (gw_val or 0) >= 35 else "ok")
        self.flow_path.update_node_latency(2, ext_val, "warn" if (ext_val or 0) >= 80 else "ok")
        if dns_val is not None:
            self.flow_path.update_node_latency(3, dns_val, "warn" if dns_val >= 80 else "ok")

        # Update global authoritative multi-layer network state from measured probes
        gw_loss_m = obs.get_latest_measurement(MetricType.GATEWAY_PACKET_LOSS)
        gw_loss_raw = self._valid_num(getattr(gw_loss_m, "normalized_value", None))
        gw_loss_pct = (
            (gw_loss_raw * 100.0)
            if (gw_loss_raw is not None and str(getattr(gw_loss_m, "unit", "") or "").lower() == "ratio")
            else gw_loss_raw
        )
        ext_loss_m = obs.get_latest_measurement(MetricType.EXTERNAL_PACKET_LOSS)
        ext_loss_raw = self._valid_num(getattr(ext_loss_m, "normalized_value", None))
        ext_loss_pct = (
            (ext_loss_raw * 100.0)
            if (ext_loss_raw is not None and str(getattr(ext_loss_m, "unit", "") or "").lower() == "ratio")
            else ext_loss_raw
        )
        g_state = GlobalNetworkStateStore.get_instance().update_from_measurements(
            gw_ms=gw_val,
            gw_loss_pct=gw_loss_pct,
            ext_ms=ext_val,
            ext_loss_pct=ext_loss_pct,
            jitter_ms=jit_val,
            dns_ms=dns_val,
            probe_error=err_msg,
        )

        # Health Score calculation using normalized loss % and internet/gateway availability
        score, health_status, summary_text = compute_genuine_health_score(
            gw_ms=gw_val,
            ext_ms=ext_val,
            loss_pct=loss_pct,
            jitter_ms=jit_val,
            dns_ms=dns_val,
            wifi_pct=wifi_val,
            internet_available=g_state.internet_available,
            gateway_reachable=g_state.gateway_reachable,
        )
        status_key = f"status.{health_status.value if hasattr(health_status, 'value') else health_status}"
        self.health_gauge.set_value(score, subtitle=tr(status_key) if score is not None else tr("status.waiting"))
        self.badge_hero_status.set_status(health_status, tr(status_key))

        if health_status == tokens.SystemStatus.HEALTHY:
            self.hero_dot.set_status(tokens.STATUS_OK)
            self.lbl_hero_title.setText(tr("dash.hero_title_healthy"))
        elif health_status == tokens.SystemStatus.WARNING:
            self.hero_dot.set_status(tokens.STATUS_WARN)
            self.lbl_hero_title.setText(tr("dash.hero_title_warning"))
        elif health_status == tokens.SystemStatus.FAILED:
            self.hero_dot.set_status(tokens.STATUS_BAD)
            self.lbl_hero_title.setText(tr("dash.hero_title_critical"))
        else:
            self.hero_dot.set_status(tokens.TEXT_MUTED)
            self.lbl_hero_title.setText(tr("dash.hero_initializing"))

        self.lbl_hero_desc.setText(summary_text)
        self._update_recommendations_from_diag(last_diag, gw_val=gw_val, ext_val=ext_val, loss_val=loss_pct, dns_val=dns_val, wifi_val=wifi_val)

        gw_ip = str(self._last_net_info.get("gateway_ip") or self._last_net_info.get("gateway") or self._last_net_info.get("default_gateway") or "—")
        self._refresh_topology_widget(gw_ip=gw_ip, info=self._last_net_info)

    def _update_recommendations_from_diag(
        self,
        diag: Optional[Diagnosis],
        *,
        gw_val: Optional[float],
        ext_val: Optional[float],
        loss_val: Optional[float],
        dns_val: Optional[float],
        wifi_val: Optional[float],
    ) -> None:
        recs: List[str] = []
        if diag and diag.recommended_actions:
            for act in diag.recommended_actions[:3]:
                recs.append(f"• {act}")
        if dns_val is not None and dns_val >= 80.0:
            recs.append(f"• {tr('dash.rec_dns')}")
        if wifi_val is not None and wifi_val < 55.0:
            recs.append(f"• {tr('dash.rec_wifi')}")
        if loss_val is not None and loss_val >= 2.0:
            recs.append(f"• {tr('dash.rec_loss')}")
        if gw_val is not None and gw_val >= 35.0:
            recs.append(f"• {tr('dash.rec_gw')}")

        if recs:
            self.lbl_recs_body.setText(tokens.bidi_isolate_mixed("\n".join(recs[:4])))
            self.lbl_recs_body.setStyleSheet(f"color: {tokens.STATUS_WARN};")
        elif ext_val is not None:
            self.lbl_recs_body.setText(tr("dash.recs_all_good"))
            self.lbl_recs_body.setStyleSheet(f"color: {tokens.STATUS_OK};")
        else:
            self.lbl_recs_body.setText(tr("dash.recs_empty"))
            self.lbl_recs_body.setStyleSheet(f"color: {tokens.TEXT_MUTED};")

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
        self._last_dns_name = curr_name or "—"
        if best_ip:
            self._last_dns_ip = best_ip if auto_applied else self._last_dns_ip
        if curr_ms is not None:
            self._last_dns_ms = curr_ms
        self.dns_panel.update_dns_state(
            curr_name,
            curr_ms,
            best_name,
            best_ip,
            best_ms,
            is_optimal,
            is_autonomous=is_autonomous,
            auto_applied=auto_applied,
        )
        self.flow_path.update_dns_node(curr_ms, is_optimal=is_optimal, dns_name=curr_name)

    def update_timeline_from_records(self, incident: Optional[Any] = None, audit_record: Optional[Any] = None) -> None:
        self.timeline_panel.update_from_records(incident, audit_record)

    def log_autonomous_action(self, title: str, description: str, level: str = "success") -> None:
        now_s = datetime.now().strftime("%H:%M")
        self.timeline_panel.set_event(
            now_s,
            [(now_s, title, description)],
            is_resolved=(level in ("success", "ok", "info")),
        )

    def _apply_layout_mode(self, mode: str) -> None:
        if mode == self._layout_mode:
            return
        self._layout_mode = mode

        # Re-grid charts, summary cards, and bottom panels
        for grid in (self.charts_grid, self.summary_grid, self.bottom_grid):
            while grid.count():
                grid.takeAt(0)

        if mode == "desktop":
            self.metrics_strip.set_responsive_columns(4)
            self.network_strip.set_responsive_mode("desktop")
            self.charts_grid.addWidget(self.latency_chart, 0, 0)
            self.charts_grid.addWidget(self.traffic_chart, 0, 1)
            self.summary_grid.addWidget(self.panel_guard, 0, 0)
            self.summary_grid.addWidget(self.panel_wifi_router, 0, 1)
            self.summary_grid.addWidget(self.panel_recs, 0, 2)
            self.bottom_grid.addWidget(self.consumers_panel, 0, 0)
            self.bottom_grid.addWidget(self.dns_panel, 0, 1)
        elif mode == "compact":
            self.metrics_strip.set_responsive_columns(2)
            self.network_strip.set_responsive_mode("compact")
            self.charts_grid.addWidget(self.latency_chart, 0, 0)
            self.charts_grid.addWidget(self.traffic_chart, 1, 0)
            self.summary_grid.addWidget(self.panel_guard, 0, 0)
            self.summary_grid.addWidget(self.panel_wifi_router, 1, 0)
            self.summary_grid.addWidget(self.panel_recs, 2, 0)
            self.bottom_grid.addWidget(self.consumers_panel, 0, 0)
            self.bottom_grid.addWidget(self.dns_panel, 1, 0)
        else:
            self.metrics_strip.set_responsive_columns(1)
            self.network_strip.set_responsive_mode("mobile")
            self.charts_grid.addWidget(self.latency_chart, 0, 0)
            self.charts_grid.addWidget(self.traffic_chart, 1, 0)
            self.summary_grid.addWidget(self.panel_guard, 0, 0)
            self.summary_grid.addWidget(self.panel_wifi_router, 1, 0)
            self.summary_grid.addWidget(self.panel_recs, 2, 0)
            self.bottom_grid.addWidget(self.consumers_panel, 0, 0)
            self.bottom_grid.addWidget(self.dns_panel, 1, 0)

    def _sync_content_width(self) -> None:
        vw = self.scroll.viewport().width()
        if vw > 0:
            self.content_holder.setFixedWidth(min(vw, tokens.MAX_CONTENT_WIDTH))
            mode = "desktop" if vw >= 960 else ("compact" if vw >= 560 else "mobile")
            self._apply_layout_mode(mode)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_content_width()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_content_width()

    def shutdown(self) -> None:
        """Stop timers and detach singleton clock/i18n observers cleanly."""
        if hasattr(self, "_tick_timer") and self._tick_timer.isActive():
            self._tick_timer.stop()
        try:
            language_manager().language_changed.disconnect(self.retranslate)
        except Exception:
            pass
        if hasattr(self, "hero_dot") and hasattr(self.hero_dot, "set_paused"):
            self.hero_dot.set_paused(True)
        if hasattr(self, "latency_chart") and hasattr(self.latency_chart, "canvas"):
            try:
                self.latency_chart.canvas.set_paused(True)
            except Exception:
                pass
        if hasattr(self, "flow_path") and hasattr(self.flow_path, "canvas"):
            try:
                AnimationMasterClock.get_instance().unsubscribe(self.flow_path.canvas._on_flow_tick)
            except Exception:
                pass

    def closeEvent(self, event) -> None:
        self.shutdown()
        super().closeEvent(event)
