"""Live Network Traffic Analysis Console for NetGuard AI.

Provides:
- Real-time Download (cyan) & Upload (purple) rates + Total RX/TX transferred bytes (psutil NIC counters)
- Time-range selector (Live, 15m, 1h) and separate Download & Upload throughput charts
- Active TCP/UDP protocol distribution & top remote destinations (real psutil sockets)
- Explicit statement of Windows per-process attribution limitations (zero disk I/O confusion)
- Searchable, category-filterable, sortable process traffic & QoS controls table
- Full backward compatibility for MainWindow and TrafficView test contracts
"""

from __future__ import annotations

import threading
import time
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

import psutil
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.platform.interfaces import IPlatformAdapter
from app.platform.windows.adapter import WindowsPlatformAdapter
from app.traffic.applications import WorkloadCategory
from app.traffic.controller import TrafficController
from app.traffic.meeting_registry import MeetingAppRegistry
from app.traffic.qos_config import AppQoSConfig
from app.traffic.session_tracker import AppSessionTracker
from app.ui import tokens
from app.ui.i18n import language_manager, tr
from app.ui.widgets.scroll_forwarder import fit_table_to_content
from app.ui.widgets.bar_row import HorizontalProgressBar
from app.ui.widgets.base_panel import Panel
from app.ui.widgets.buttons import GhostButton, PrimaryButton, SecondaryButton
from app.ui.widgets.chip import Chip
from app.ui.widgets.segmented import SegmentedControl
from app.ui.widgets.status_badge import StatusBadge
from app.ui.widgets.toggle import ToggleSwitch
from app.ui.widgets.traffic_chart import TrafficThroughputChart


def _fmt_bytes(num_bytes: int) -> str:
    val = float(max(0, num_bytes))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if val < 1024.0 or unit == "TB":
            return f"{val:.1f} {unit}" if unit != "B" else f"{int(val)} B"
        val /= 1024.0
    return f"{val:.1f} TB"


class ProcessTableCell(QWidget):
    """Progress + rate/UDP speed cell."""

    def __init__(self, speed_str: str, fraction: float, is_throttled: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        self.lbl = QLabel(tokens.bidi_isolate_mixed(speed_str))
        self.lbl.setFont(tokens.get_mono_font(12, 600))
        color = tokens.STATUS_WARN if is_throttled else tokens.SECONDARY_PURPLE
        self.lbl.setStyleSheet(f"color: {color}; background: transparent; border: none;")

        self.bar = HorizontalProgressBar(height=4, fill_color=color)
        self.bar.set_fraction(max(0.0, min(1.0, fraction)), color)
        layout.addWidget(self.lbl)
        layout.addWidget(self.bar)

    def sizeHint(self):
        from PySide6.QtCore import QSize

        return QSize(130, 44)


class TrafficView(QWidget):
    """NOC-style Live Traffic Analysis Console."""

    qos_policy_done = Signal(bool, str)
    refresh_requested = Signal()

    def __init__(
        self,
        session_tracker: Optional[AppSessionTracker] = None,
        platform: Optional[IPlatformAdapter] = None,
        user_settings: Optional[Any] = None,
        qos_config: Optional[AppQoSConfig] = None,
        parent=None,
        controller: Optional[TrafficController] = None,
    ) -> None:
        super().__init__(parent)
        self.session_tracker = session_tracker or AppSessionTracker()
        self.platform = platform or WindowsPlatformAdapter()
        self.user_settings = user_settings
        self.qos_config = qos_config or (
            AppQoSConfig.from_user_settings(user_settings) if user_settings else AppQoSConfig()
        )
        self.controller = controller
        self._last_profiles_cache: List[Any] = []
        self._last_qos_policies_cache: List[Dict[str, Any]] = []
        self._last_conferencing_active: bool = False
        self._in_kill_switch = False

        # Live NIC throughput history buffers (up to 360 samples)
        self._prev_io: Optional[Tuple[int, int, float]] = None
        self._dl_hist: List[float] = []
        self._ul_hist: List[float] = []
        self._ts_hist: List[str] = []
        self._range_points: int = 30

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet(f"QScrollArea {{ background-color: {tokens.BG}; border: none; }}")
        self.scroll.verticalScrollBar().setSingleStep(25)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(24, 20, 24, 32)
        self.content_layout.setSpacing(16)

        # ------------------------------------------------------------------
        # 1. Header & Attribution Scope Banner
        # ------------------------------------------------------------------
        hdr = QHBoxLayout()
        hdr.setSpacing(12)
        t_col = QVBoxLayout()
        t_col.setSpacing(4)
        self.lbl_title = QLabel(tr("tm_title"))
        self.lbl_title.setFont(tokens.get_sans_font(20, 700))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_sub = QLabel(tr("tm_sub"))
        self.lbl_sub.setFont(tokens.get_sans_font(12, 400))
        self.lbl_sub.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_sub.setWordWrap(True)
        t_col.addWidget(self.lbl_title)
        t_col.addWidget(self.lbl_sub)
        hdr.addLayout(t_col, 1)

        self.range_switch = SegmentedControl(["Live", "15m", "1h"], initial_index=0)
        self.range_switch.current_changed.connect(self._on_range_changed)
        hdr.addWidget(self.range_switch)

        # Keep compatibility controls used by MainWindow / tests (owned by self, never orphan top-level widgets)
        self.guard_toggle = ToggleSwitch(checked=True, parent=self)
        self.btn_refresh = PrimaryButton("تحديث / Refresh")
        self.btn_refresh.clicked.connect(self._on_manual_refresh)
        self.btn_sim_zoom = GhostButton("فحص حالة الـ QoS", parent=self)
        self.btn_sim_zoom.clicked.connect(self._on_sim_zoom_clicked)
        self.btn_sim_zoom.setVisible(False)

        hdr.addWidget(self.btn_refresh)
        self.content_layout.addLayout(hdr)

        # Attribution limitation disclosure banner
        limit_box = QFrame()
        limit_box.setStyleSheet(
            f"background-color: {tokens.INFO_SOFT_BG}; border: 1px solid {tokens.INFO_BORDER}; border-radius: 8px;"
        )
        lb_lay = QHBoxLayout(limit_box)
        lb_lay.setContentsMargins(14, 8, 14, 8)
        self.lbl_limit = QLabel(tr("tm.limit_banner"))
        self.lbl_limit.setFont(tokens.get_sans_font(12, 400))
        self.lbl_limit.setStyleSheet(f"color: {tokens.TEXT_SECONDARY}; border: none; background: transparent;")
        self.lbl_limit.setWordWrap(True)
        lb_lay.addWidget(self.lbl_limit)
        self.content_layout.addWidget(limit_box)

        # Compatibility status badge + guard row
        compat_row = QHBoxLayout()
        compat_row.setSpacing(10)
        self.master_qos_toggle = ToggleSwitch(checked=bool(self.qos_config.master_enabled), parent=self)
        self.master_qos_toggle.setVisible(False)
        self.master_qos_toggle.toggled.connect(self._on_master_qos_toggled)
        lbl_guard = QLabel("الحماية الفورية للاجتماعات / Auto Guard")
        lbl_guard.setFont(tokens.get_sans_font(12, 500))
        lbl_guard.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        lbl_guard.setWordWrap(True)
        self.qos_status_badge = QLabel("في وضع الاستعداد (0 سياسة مطبقة)")
        self.qos_status_badge.setFont(tokens.get_sans_font(12, 600))
        self.qos_status_badge.setWordWrap(True)
        self.qos_status_badge.setStyleSheet(
            f"color: {tokens.TEXT_MUTED}; background: {tokens.SURFACE_INSET}; border: 1px solid {tokens.LINE}; border-radius: 6px; padding: 4px 10px;"
        )
        compat_row.addWidget(self.guard_toggle)
        compat_row.addWidget(lbl_guard, 1)
        self.meeting_lbl = QLabel("في وضع الاستعداد")
        self.meeting_lbl.setFont(tokens.get_sans_font(12, 600))
        self.meeting_lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        compat_row.addWidget(self.meeting_lbl)
        compat_row.addWidget(self.qos_status_badge, 1)
        self.btn_kill_switch = PrimaryButton(tr("mg.kill_switch"))
        self.btn_kill_switch.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {tokens.STATUS_BAD};
                color: #FFFFFF;
                border: 1px solid {tokens.BAD_SOFT_BORDER};
                border-radius: 8px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: #DC2626; }}
            """
        )
        self.btn_kill_switch.clicked.connect(self._on_kill_switch_clicked)
        compat_row.addWidget(self.btn_kill_switch)
        self.content_layout.addLayout(compat_row)

        # Compatibility session containers (synced with AppSessionTracker)
        self._compat_sessions_box = QWidget(self)
        self._compat_sessions_box.setVisible(False)
        compat_v = QVBoxLayout(self._compat_sessions_box)
        self.active_session_layout = QVBoxLayout()
        self.reports_list_layout = QVBoxLayout()
        self.report_cards: List[Any] = []
        self._empty_reports_lbl = QLabel("لا توجد جلسات منتهية بعد")
        self.reports_list_layout.addWidget(self._empty_reports_lbl)
        compat_v.addLayout(self.active_session_layout)
        compat_v.addLayout(self.reports_list_layout)
        self.content_layout.addWidget(self._compat_sessions_box)

        # ------------------------------------------------------------------
        # 2. Live Summary Strip (Download Rate, Upload Rate, RX/TX Totals, Sockets)
        # ------------------------------------------------------------------
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(12)
        self.kpi_dl = self._make_stat_tile(tr("tm.dl_card"), "— Mbps", tokens.SECONDARY_CYAN)
        self.kpi_ul = self._make_stat_tile(tr("tm.ul_card"), "— Mbps", tokens.SECONDARY_PURPLE)
        self.kpi_totals = self._make_stat_tile(tr("tm.total_rx_tx"), "—", tokens.ACCENT_BRIGHT)
        self.kpi_conns = self._make_stat_tile(tr("tm.active_conns"), "—", tokens.STATUS_OK)
        kpi_grid.addWidget(self.kpi_dl[0], 0, 0)
        kpi_grid.addWidget(self.kpi_ul[0], 0, 1)
        kpi_grid.addWidget(self.kpi_totals[0], 0, 2)
        kpi_grid.addWidget(self.kpi_conns[0], 0, 3)
        self.content_layout.addLayout(kpi_grid)

        # ------------------------------------------------------------------
        # 3. Separate Download & Upload Real-Time Charts
        # ------------------------------------------------------------------
        charts_row = QGridLayout()
        charts_row.setSpacing(14)
        self.dl_chart = TrafficThroughputChart(
            title=tr("tm.dl_chart"),
            show_download=True,
            show_upload=False,
            min_height=165,
        )
        self.ul_chart = TrafficThroughputChart(
            title=tr("tm.ul_chart"),
            show_download=False,
            show_upload=True,
            min_height=165,
        )
        charts_row.addWidget(self.dl_chart, 0, 0)
        charts_row.addWidget(self.ul_chart, 0, 1)
        self.content_layout.addLayout(charts_row)

        # ------------------------------------------------------------------
        # 4. Protocol Distribution & Top Connection Destinations
        # ------------------------------------------------------------------
        self.panel_proto = Panel(
            title="توزيع البروتوكولات والوجهات النشطة / Protocols & Destinations",
            subtitle="بيانات مستخرجة مباشرة من اتصالات الشبكة الفعلية على النظام",
            padding=16,
        )
        self.panel_proto.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.panel_proto.setMinimumHeight(250)
        proto_cols = QGridLayout()
        proto_cols.setSpacing(10)
        self.lbl_proto_summary = QLabel("—")
        self.lbl_proto_summary.setFont(tokens.get_mono_font(12, 500))
        self.lbl_proto_summary.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_proto_summary.setWordWrap(True)
        self.lbl_proto_summary.setMinimumHeight(28)
        self.lbl_proto_summary.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.lbl_dest_summary = QLabel("—")
        self.lbl_dest_summary.setFont(tokens.get_mono_font(12, 400))
        self.lbl_dest_summary.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_dest_summary.setWordWrap(True)
        self.lbl_dest_summary.setMinimumHeight(58)
        self.lbl_dest_summary.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        proto_cols.addWidget(self.lbl_proto_summary, 0, 0)
        proto_cols.addWidget(self.lbl_dest_summary, 1, 0)
        self.panel_proto.main_layout.addLayout(proto_cols)
        self.content_layout.addWidget(self.panel_proto)

        # ------------------------------------------------------------------
        # 5. Searchable & Sortable Live Process Table
        # ------------------------------------------------------------------
        proc_panel = Panel(
            title="العمليات والاتصالات النشطة / Active Processes & Sockets",
            subtitle="فرز وتصفية التطبيقات مع إمكانية تطبيق أولوية DSCP أو تقييد الرفع",
            padding=18,
        )

        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("tm.search_placeholder"))
        self.search_input.textChanged.connect(lambda _: self._render_filtered_table())

        self.cat_filter = QComboBox()
        self.cat_filter.addItems(["الكل / All", "مكالمات / Conferencing", "متصفح / Browser", "تحديثات / Updates", "سحابي / Sync"])
        self.cat_filter.currentIndexChanged.connect(lambda _: self._render_filtered_table())

        filter_row.addWidget(self.search_input, 2)
        filter_row.addWidget(self.cat_filter, 1)
        proc_panel.main_layout.addLayout(filter_row)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            [
                "التطبيق / العملية",
                "الفئة",
                "الاتصالات / معدل UDP",
                "حالة الأولوية (QoS)",
                "التحكم بالرفع",
                "الإجراءات",
            ]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(54)
        self.table.horizontalHeader().setMinimumHeight(46)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in (1, 2, 3, 5):
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        proc_panel.main_layout.addWidget(self.table)
        self.content_layout.addWidget(proc_panel)

        self.scroll.setWidget(self.content_widget)
        outer.addWidget(self.scroll)

        self.qos_policy_done.connect(self._on_qos_policy_done)
        language_manager().language_changed.connect(self.retranslate)
        self.sample_live_counters()

    @staticmethod
    def _make_stat_tile(title: str, val: str, accent: str) -> Tuple[QFrame, QLabel]:
        card = QFrame()
        card.setStyleSheet(
            f"""
            QFrame {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE};
                border-top: 3px solid {accent};
                border-radius: 10px;
            }}
            """
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 10, 14, 12)
        lay.setSpacing(4)
        t = QLabel(title)
        t.setFont(tokens.get_sans_font(12, 500))
        t.setStyleSheet(f"color: {tokens.TEXT_MUTED}; border: none; background: transparent;")
        t.setWordWrap(True)
        v = QLabel(val)
        v.setFont(tokens.get_mono_font(14, 700))
        v.setStyleSheet(f"color: {tokens.TEXT}; border: none; background: transparent;")
        v.setWordWrap(False)
        lay.addWidget(t)
        lay.addWidget(v)
        return card, v

    def retranslate(self) -> None:
        self.lbl_title.setText(tr("tm_title"))
        self.lbl_sub.setText(tr("tm_sub"))
        self.lbl_limit.setText(tr("tm.limit_banner"))
        self.search_input.setPlaceholderText(tr("tm.search_placeholder"))

    def _on_range_changed(self, idx: int, label: str) -> None:
        self._range_points = {0: 30, 1: 120, 2: 360}.get(idx, 30)
        self._update_charts()

    def _on_manual_refresh(self) -> None:
        self.sample_live_counters()
        self.refresh_requested.emit()

    def sample_live_counters(self) -> None:
        """Read authentic NIC RX/TX counters and TCP/UDP socket counts from Windows via psutil."""
        try:
            io = psutil.net_io_counters()
            now = time.monotonic()
            ts_str = time.strftime("%H:%M:%S")
            if io:
                rx, tx = int(io.bytes_recv), int(io.bytes_sent)
                self.kpi_totals[1].setText(tokens.bidi_isolate(f"↓ {_fmt_bytes(rx)}  |  ↑ {_fmt_bytes(tx)}"))
                if self._prev_io is not None:
                    prev_rx, prev_tx, prev_t = self._prev_io
                    dt = max(0.2, now - prev_t)
                    dl_mbps = max(0.0, (rx - prev_rx) * 8.0 / dt / 1_000_000.0)
                    ul_mbps = max(0.0, (tx - prev_tx) * 8.0 / dt / 1_000_000.0)
                    self.kpi_dl[1].setText(tokens.bidi_isolate(f"{dl_mbps:.2f} Mbps"))
                    self.kpi_ul[1].setText(tokens.bidi_isolate(f"{ul_mbps:.2f} Mbps"))
                    self._dl_hist.append(dl_mbps)
                    self._ul_hist.append(ul_mbps)
                    self._ts_hist.append(ts_str)
                    self._dl_hist = self._dl_hist[-360:]
                    self._ul_hist = self._ul_hist[-360:]
                    self._ts_hist = self._ts_hist[-360:]
                    self._update_charts()
                self._prev_io = (rx, tx, now)
        except Exception:
            pass

        try:
            conns = psutil.net_connections(kind="inet")
            tcp_est = sum(1 for c in conns if getattr(c, "type", None) and int(c.type) == 1 and str(c.status) == "ESTABLISHED")
            udp_cnt = sum(1 for c in conns if getattr(c, "type", None) and int(c.type) == 2)
            self.kpi_conns[1].setText(tokens.bidi_isolate(f"TCP: {tcp_est}  |  UDP: {udp_cnt}"))
            self.lbl_proto_summary.setText(
                tokens.bidi_isolate(f"Established TCP: {tcp_est} sockets  ·  Bound UDP: {udp_cnt} sockets  ·  Total INET: {len(conns)}")
            )
            remotes = Counter()
            for c in conns:
                if getattr(c, "raddr", None) and getattr(c.raddr, "ip", None):
                    remotes[f"{c.raddr.ip}:{c.raddr.port}"] += 1
            if remotes:
                top_str = "  |  ".join(f"{ep} ({cnt})" for ep, cnt in remotes.most_common(5))
                self.lbl_dest_summary.setText(tokens.bidi_isolate(f"Top Active Endpoints: {top_str}"))
            else:
                self.lbl_dest_summary.setText("No established remote endpoints currently active.")
        except Exception:
            self.lbl_dest_summary.setText("Socket inspection requires standard desktop permissions.")

    def _update_charts(self) -> None:
        n = self._range_points
        self.dl_chart.set_series(self._dl_hist[-n:], [], self._ts_hist[-n:])
        self.ul_chart.set_series([], self._ul_hist[-n:], self._ts_hist[-n:])

    def _on_sim_zoom_clicked(self) -> None:
        active = self.session_tracker.get_active_sessions()
        if any("zoom" in (getattr(s, "process_name", "") or "").lower() for s in active):
            self.session_tracker.close_session("zoom.exe")
        else:
            self.session_tracker.start_or_update_session(
                app_name="Zoom Cloud Meetings",
                process_name="zoom.exe",
                pid=99999,
                category=WorkloadCategory.CONFERENCING,
                avg_bitrate=0.0,
                avg_latency=0.0,
            )
        self._refresh_sessions_ui()

    def _refresh_sessions_ui(self) -> None:
        from app.ui.widgets.session_card import ActiveSessionCard, SessionReportCard

        while self.active_session_layout.count():
            it = self.active_session_layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        active = self.session_tracker.get_active_sessions()
        for s in active:
            self.active_session_layout.addWidget(ActiveSessionCard(s, parent=self))

        if active:
            label = getattr(active[0], "app_title", None) or getattr(active[0], "app_name", "Zoom")
            self.meeting_lbl.setText(f"اجتماع نشط: {label}")
            self.btn_sim_zoom.setText("إنهاء مكالمة Zoom")
        else:
            self.meeting_lbl.setText("في وضع الاستعداد")
            self.btn_sim_zoom.setText("محاكاة مكالمة Zoom")

        while self.reports_list_layout.count():
            it = self.reports_list_layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self.report_cards = []
        completed = self.session_tracker.get_completed_sessions()
        if not completed:
            lbl = QLabel("لا توجد جلسات منتهية بعد")
            self.reports_list_layout.addWidget(lbl)
        else:
            for s in completed:
                card = SessionReportCard(s, parent=self)
                self.report_cards.append(card)
                self.reports_list_layout.addWidget(card)

    def _populate_default_processes(self) -> None:
        self.table.setRowCount(0)

    def update_profiles(
        self,
        profiles: List[Any],
        conferencing_active: bool = False,
        qos_policies: Optional[List[Any]] = None,
    ) -> None:
        self._last_profiles_cache = list(profiles or [])
        self._last_conferencing_active = conferencing_active
        if qos_policies is not None:
            self._last_qos_policies_cache = list(qos_policies)
        self.sample_live_counters()
        self._render_filtered_table()

    def _render_filtered_table(self) -> None:
        profiles = self._last_profiles_cache
        query = self.search_input.text().strip().lower() if hasattr(self, "search_input") else ""
        cat_idx = self.cat_filter.currentIndex() if hasattr(self, "cat_filter") else 0

        filtered: List[Any] = []
        for p in profiles:
            pname = str(getattr(p, "process_name", None) or getattr(p, "name", "") or "").lower()
            cat_str = str(getattr(p, "category", "") or "").lower()
            if query and query not in pname and query not in cat_str:
                continue
            if cat_idx == 1 and "conferenc" not in cat_str:
                continue
            elif cat_idx == 2 and "browser" not in cat_str:
                continue
            elif cat_idx == 3 and "update" not in cat_str and "download" not in cat_str:
                continue
            elif cat_idx == 4 and "sync" not in cat_str and "cloud" not in cat_str:
                continue
            filtered.append(p)

        self.table.setSortingEnabled(False)
        for old_r in range(self.table.rowCount()):
            for old_c in (2, 4, 5):
                old_w = self.table.cellWidget(old_r, old_c)
                if old_w is not None:
                    self.table.removeCellWidget(old_r, old_c)
                    old_w.setParent(None)
                    old_w.deleteLater()
        self.table.clearContents()
        self.table.setRowCount(len(filtered))

        max_rate = max(
            [float(getattr(p, "outbound_udp_kbps", None) or getattr(p, "estimated_bandwidth_mbps", 0.0) or 0.0) for p in filtered] + [100.0]
        )
        policy_names = {str(pol.get("Name", "")).lower() for pol in self._last_qos_policies_cache if isinstance(pol, dict)}

        for r, p in enumerate(filtered):
            pname = str(getattr(p, "process_name", None) or getattr(p, "name", "unknown"))
            cat = str(getattr(p, "category", "Other"))
            conns = int(getattr(p, "active_connections", None) or getattr(p, "active_socket_count", 0) or 0)
            udp_kbps = float(getattr(p, "outbound_udp_kbps", 0.0) or 0.0)
            is_meeting_or_stream = (
                "conferenc" in cat.lower()
                or "stream" in cat.lower()
                or MeetingAppRegistry.find_entry_for_process(pname) is not None
            )

            it_name = QTableWidgetItem(tokens.bidi_isolate(pname))
            it_name.setFont(tokens.get_mono_font(14, 600))
            self.table.setItem(r, 0, it_name)

            it_cat = QTableWidgetItem(str(getattr(p, "pid", cat)))
            it_cat.setFont(tokens.get_mono_font(14, 400))
            self.table.setItem(r, 1, it_cat)

            tag_text = "أولوية قصوى" if is_meeting_or_stream else f"{conns} · UDP {udp_kbps:.1f}"
            tag_lbl = QLabel(tokens.bidi_isolate_mixed(tag_text))
            tag_lbl.setFont(tokens.get_sans_font(12, 600 if is_meeting_or_stream else 500))
            tag_lbl.setWordWrap(True)
            tag_lbl.setStyleSheet(
                f"color: {tokens.STATUS_OK if is_meeting_or_stream else tokens.TEXT_SECONDARY}; padding: 2px 6px; background: transparent;"
            )
            tag_wrap = QWidget()
            twl = QHBoxLayout(tag_wrap)
            twl.setContentsMargins(4, 2, 4, 2)
            twl.addWidget(tag_lbl)
            self.table.setCellWidget(r, 2, tag_wrap)

            has_dscp = f"netguard_dscp_{pname}".lower() in policy_names or any(
                pname.lower() in n and "dscp" in n for n in policy_names
            )
            has_throttle = f"netguard_throttle_{pname}".lower() in policy_names or any(
                pname.lower() in n and "throttle" in n for n in policy_names
            )
            qos_txt = "DSCP مؤمن" if (has_dscp or is_meeting_or_stream) else ("تقييد رفع" if has_throttle else "افتراضي")
            it_qos = QTableWidgetItem(qos_txt)
            it_qos.setFont(tokens.get_sans_font(14, 500))
            self.table.setItem(r, 3, it_qos)

            rate_str = f"{conns} sockets" if udp_kbps <= 0 else f"{udp_kbps:.1f} KB/s"
            cell = ProcessTableCell(rate_str, udp_kbps / max_rate if max_rate > 0 else 0.0, is_throttled=has_throttle)
            self.table.setCellWidget(r, 4, cell)

            if is_meeting_or_stream or getattr(p, "is_protected_system_process", False):
                prot_lbl = QLabel("محمي (أولوية)")
                prot_lbl.setFont(tokens.get_sans_font(12, 600))
                prot_lbl.setStyleSheet(f"color: {tokens.STATUS_OK}; background: transparent; padding: 2px 6px;")
                prot_lbl.setAlignment(Qt.AlignCenter)
                self.table.setCellWidget(r, 5, prot_lbl)
            else:
                btn_th = SecondaryButton("إلغاء التقييد" if has_throttle else "تقييد الرفع")
                btn_th.clicked.connect(lambda _=False, pn=pname, en=not has_throttle: self._on_toggle_throttle(pn, en))
                self.table.setCellWidget(r, 5, btn_th)
            self.table.setRowHeight(r, 54)

        self.table.doItemsLayout()
        self.table.updateGeometries()
        fit_table_to_content(self.table)

    def _on_toggle_throttle(self, pname: str, enable: bool) -> None:
        from app.platform.admin import prompt_restart_as_admin, require_admin

        ok_admin, _ = require_admin(f"Throttle {pname}", self.platform)
        if not ok_admin:
            prompt_restart_as_admin(self, f"Throttle upload for {pname}", self.platform)
            return

        policy_name = f"NetGuard_Throttle_{pname}"
        throttle_bps = 5_000_000
        if self.user_settings and hasattr(self.user_settings, "get_qos_upload_throttle_bps"):
            throttle_bps = self.user_settings.get_qos_upload_throttle_bps()

        def _worker() -> None:
            if enable:
                ok, msg = self.platform.create_qos_throttle_policy(policy_name, pname, throttle_bps)
            else:
                ok, msg = self.platform.remove_qos_policy(policy_name)
            self.qos_policy_done.emit(ok, msg)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_toggle_dscp(self, pname: str, enable: bool) -> None:
        from app.platform.admin import prompt_restart_as_admin, require_admin

        ok_admin, _ = require_admin(f"DSCP priority {pname}", self.platform)
        if not ok_admin:
            prompt_restart_as_admin(self, f"DSCP priority for {pname}", self.platform)
            return

        policy_name = f"NetGuard_DSCP_{pname}"
        is_mixed = any(k in pname.lower() for k in ("zoom", "chrome", "msedge", "brave", "firefox"))
        dscp_val = 34 if is_mixed else 46
        proto = "UDP" if is_mixed else None

        def _worker() -> None:
            if enable:
                ok, msg = self.platform.create_qos_dscp_policy(
                    name=policy_name,
                    app_name=pname,
                    dscp_value=dscp_val,
                    ip_protocol=proto,
                    policy_store="ActiveStore",
                )
            else:
                ok, msg = self.platform.remove_qos_policy(policy_name, policy_store="ActiveStore")
            self.qos_policy_done.emit(ok, msg)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_qos_policy_done(self, ok: bool, msg: str) -> None:
        if not ok and self.isVisible():
            QMessageBox.warning(self, "QoS ActiveStore", msg)
        self.update_profiles(self._last_profiles_cache)

    def _on_master_qos_toggled(self, checked: bool) -> None:
        self.qos_config.master_enabled = checked
        if self.user_settings and hasattr(self.user_settings, "set_policy"):
            self.user_settings.set_policy("qos_master_enabled", checked)

    def _on_kill_switch_clicked(self) -> None:
        if self._in_kill_switch:
            return
        self._in_kill_switch = True
        try:
            self.qos_config.master_enabled = False
            self.master_qos_toggle.setChecked(False)
            if self.user_settings and hasattr(self.user_settings, "set_policy"):
                self.user_settings.set_policy("qos_master_enabled", False)
            if self.controller and hasattr(self.controller, "kill_switch_disable"):
                self.controller.kill_switch_disable()

            def _worker() -> None:
                ok, msg = (
                    self.platform.sweep_all_netguard_rules()
                    if (self.platform and hasattr(self.platform, "sweep_all_netguard_rules"))
                    else (True, "Swept")
                )
                self.qos_policy_done.emit(ok, msg)

            threading.Thread(target=_worker, daemon=True).start()
        finally:
            self._in_kill_switch = False

    def set_qos_status_badge(
        self,
        is_active: bool,
        verified: bool = True,
        confirmed_count: int = 0,
        error_msg: str = "",
        rolled_back: bool = False,
        rollback_reason: str = "",
    ) -> None:
        if rolled_back:
            self.qos_status_badge.setText("تم التراجع تلقائياً (تدهور الجودة)")
            self.qos_status_badge.setStyleSheet(
                f"color: {tokens.STATUS_WARN}; background: {tokens.WARN_SOFT_BG}; border: 1px solid {tokens.WARN_BORDER}; border-radius: 6px; padding: 4px 10px;"
            )
            self.qos_status_badge.setToolTip(rollback_reason)
        elif is_active:
            if verified and confirmed_count > 0:
                self.qos_status_badge.setText(f"مطبقة ومؤكدة ({confirmed_count} سياسة في ActiveStore)")
                self.qos_status_badge.setStyleSheet(
                    f"color: {tokens.STATUS_OK}; background: {tokens.OK_SOFT_BG}; border: 1px solid {tokens.OK_SOFT_BORDER}; border-radius: 6px; padding: 4px 10px;"
                )
            elif verified:
                self.qos_status_badge.setText("مطبقة ومؤكدة في ActiveStore")
                self.qos_status_badge.setStyleSheet(
                    f"color: {tokens.STATUS_OK}; background: {tokens.OK_SOFT_BG}; border: 1px solid {tokens.OK_SOFT_BORDER}; border-radius: 6px; padding: 4px 10px;"
                )
            else:
                self.qos_status_badge.setText("فشل التحقق من تطبيق السياسات")
                self.qos_status_badge.setStyleSheet(
                    f"color: {tokens.STATUS_BAD}; background: {tokens.BAD_SOFT_BG}; border: 1px solid {tokens.BAD_SOFT_BORDER}; border-radius: 6px; padding: 4px 10px;"
                )
        else:
            self.qos_status_badge.setText("في وضع الاستعداد (0 سياسة مطبقة)")
            self.qos_status_badge.setStyleSheet(
                f"color: {tokens.TEXT_MUTED}; background: {tokens.SURFACE_INSET}; border: 1px solid {tokens.LINE}; border-radius: 6px; padding: 4px 10px;"
            )

    def _sync_content_width(self) -> None:
        if hasattr(self, "scroll") and hasattr(self, "content_widget"):
            vw = self.scroll.viewport().width()
            if vw > 0:
                self.content_widget.setFixedWidth(min(vw, tokens.MAX_CONTENT_WIDTH))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_content_width()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_content_width()

    def shutdown(self) -> None:
        try:
            language_manager().language_changed.disconnect(self.retranslate)
        except Exception:
            pass
        for card in list(getattr(self, "report_cards", [])):
            if hasattr(card, "_timer") and card._timer.isActive():
                card._timer.stop()

    def closeEvent(self, event) -> None:
        self.shutdown()
        super().closeEvent(event)
