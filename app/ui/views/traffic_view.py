"""Application Traffic, Meeting Guard & App Session Reports View for NetGuard AI.

Follows the reference design system strictly:
- Active meeting/streaming sessions with live duration and real-time QoS protection
- Expandable Post-Session Quality Reports detailing start/end times, problems detected,
  and autonomous solutions applied to ensure zero-stutter video & audio.
- Priority protection toggle row for video calls (Meeting Guard)
- Expanded list of all processes with sortable column headers & live-updating bars
- 100% token-compliant, dark warm-neutral graphite (#0E1012 / #15181A).
"""

from __future__ import annotations
from typing import List, Any, Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QScrollArea,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QTimer
from app.ui import tokens
from app.ui.widgets.buttons import PrimaryButton, SecondaryButton
from app.ui.widgets.chip import Chip
from app.ui.widgets.toggle import ToggleSwitch
from app.ui.widgets.base_panel import Panel
from app.ui.widgets.bar_row import HorizontalProgressBar
from app.ui.widgets.session_card import ActiveSessionCard, SessionReportCard
from app.traffic.session_tracker import AppSessionTracker, AppSessionRecord
from app.traffic.applications import ApplicationCatalog
from app.platform.interfaces import IPlatformAdapter
from app.platform.windows.adapter import WindowsPlatformAdapter
from app.ui.widgets.scroll_forwarder import make_scroll_transparent, fit_table_to_content


class ProcessTableCell(QWidget):
    """Table cell rendering mono speed and proportional 6px bar."""

    def __init__(self, speed_str: str, fraction: float, is_throttled: bool = False, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(12)

        lbl = QLabel(speed_str)
        lbl.setFont(tokens.get_mono_font(13, 500))
        lbl.setStyleSheet(f"color: {tokens.TEXT};")
        lbl.setMinimumWidth(180)
        lbl.setWordWrap(False)
        layout.addWidget(lbl)

        fill_color = tokens.STATUS_WARN if is_throttled else tokens.ACCENT
        bar = HorizontalProgressBar(height=6, fill_color=fill_color, parent=self)
        bar.set_fraction(fraction)
        layout.addWidget(bar, stretch=1)


class TrafficView(QWidget):
    """Traffic monitoring and meeting session quality view."""

    start_simulated_zoom_requested = Signal()
    close_simulated_zoom_requested = Signal()
    qos_policy_done = Signal(bool, str)

    def __init__(
        self,
        session_tracker: Optional[AppSessionTracker] = None,
        platform: Optional[IPlatformAdapter] = None,
        user_settings: Optional[Any] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.session_tracker = session_tracker or AppSessionTracker()
        self.platform = platform or WindowsPlatformAdapter()
        self.user_settings = user_settings
        self._last_profiles_cache: List[Any] = []
        self.report_cards: List[SessionReportCard] = []
        self.btn_sim_zoom = SecondaryButton("محاكاة مكالمة Zoom")
        self.btn_sim_zoom.setVisible(False)
        self.btn_sim_zoom.clicked.connect(self._on_sim_zoom_clicked)
        self.qos_policy_done.connect(self._on_qos_policy_done)
        self.setStyleSheet(f"background-color: {tokens.BG};")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
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
            tokens.PAGE_PADDING_DESKTOP, 28, tokens.PAGE_PADDING_DESKTOP, 36
        )
        self.content_layout.setSpacing(tokens.SECTION_GAP)
        layout = self.content_layout

        # -------------------------------------------------------------
        # 1. Unified Clean Header & Meeting Guard Control Bar
        # -------------------------------------------------------------
        self.header_panel = Panel(
            title="حركة البيانات وتأمين التطبيقات",
            subtitle="مراقبة استهلاك البرامج للباندويث وحماية جودة المكالمات والبث المباشر استباقياً من أي تقطيع",
            parent=self,
        )

        header_top = QHBoxLayout()
        header_top.setSpacing(16)

        # Right side: Meeting Guard toggle & status
        guard_box = QHBoxLayout()
        guard_box.setSpacing(10)

        self.meeting_dot = QLabel()
        self.meeting_dot.setFixedSize(8, 8)
        self.meeting_dot.setStyleSheet(f"background-color: {tokens.TEXT_MUTED}; border-radius: 4px;")
        guard_box.addWidget(self.meeting_dot)

        self.meeting_lbl = QLabel("درع مكالمات الفيديو: مؤمن (في وضع الاستعداد)")
        self.meeting_lbl.setFont(tokens.get_sans_font(13, 500))
        self.meeting_lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        guard_box.addWidget(self.meeting_lbl)

        self.guard_toggle = ToggleSwitch(checked=True, parent=self)
        guard_box.addWidget(self.guard_toggle)
        header_top.addLayout(guard_box)

        header_top.addStretch()

        # Left side: Action button
        self.btn_refresh = PrimaryButton("فحص البرامج النشطة")
        self.btn_refresh.setFixedHeight(36)
        header_top.addWidget(self.btn_refresh)

        self.header_panel.main_layout.addLayout(header_top)

        # Active Meeting Session Container (Dynamic: expands only when a meeting is active)
        self.active_session_container = QWidget()
        self.active_session_layout = QVBoxLayout(self.active_session_container)
        self.active_session_layout.setContentsMargins(0, 12, 0, 0)
        self.active_session_layout.setSpacing(10)
        self.active_session_container.setVisible(False)
        self.header_panel.main_layout.addWidget(self.active_session_container)

        layout.addWidget(self.header_panel)

        # -------------------------------------------------------------
        # 2. Expanded Process Consumers Table
        # -------------------------------------------------------------
        table_panel = Panel(
            title="قائمة البرامج المتصلة بالإنترنت حالياً",
            subtitle="مرتبة حسب الاتصالات النشطة، مع إمكانية تقييد سرعة الرفع الصادر (Outbound Throttle) عبر Windows NetQosPolicy",
            parent=self,
        )

        self.table = QTableWidget(0, 6)
        self.table.setMinimumHeight(320)
        self.table.setHorizontalHeaderLabels([
            "البرنامج",
            "معرف PID",
            "الحالة / الفئة",
            "الاتصالات النشطة (تقديري)",
            "حالة سرعة الرفع (QoS)",
            "إجراء QoS",
        ])
        self.table.horizontalHeader().setMinimumSectionSize(60)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(56)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.setSortingEnabled(True)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent;
                border: none;
            }}
            QHeaderView::section {{
                background-color: {tokens.SURFACE_INSET};
                color: {tokens.TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 600;
                border: none;
                border-bottom: 1px solid {tokens.LINE};
                padding: 10px 12px;
                text-align: right;
            }}
            QTableWidget::item {{
                border: none;
                border-bottom: 1px solid {tokens.LINE};
                padding: 8px 12px;
                color: {tokens.TEXT};
            }}
            QTableWidget::item:hover {{
                background-color: {tokens.SURFACE_HOVER};
            }}
            QTableWidget::item:selected {{
                background-color: {tokens.SURFACE_SELECTED};
                color: {tokens.TEXT};
            }}
        """)

        table_panel.main_layout.addWidget(self.table)
        layout.addWidget(table_panel)

        # -------------------------------------------------------------
        # 3. Completed App Sessions & Post-Session Quality Reports
        # -------------------------------------------------------------
        self.reports_panel = Panel(
            title="سجل جلسات البرامج وتقارير جودة البث - Session Reports",
            subtitle="حساب مدة كل تطبيق تم فتحه وإغلاقه، والمشاكل التي حلها NetGuard لضمان أعلى جودة بدون تقطيع",
            parent=self,
        )
        self.reports_list_container = QWidget()
        self.reports_list_layout = QVBoxLayout(self.reports_list_container)
        self.reports_list_layout.setContentsMargins(0, 0, 0, 0)
        self.reports_list_layout.setSpacing(12)
        self.reports_panel.main_layout.addWidget(self.reports_list_container)
        self.reports_panel.setVisible(False)
        layout.addWidget(self.reports_panel)

        make_scroll_transparent(self.table, self.scroll)

        self._populate_default_processes()
        self._populate_session_reports()

        self.scroll.setWidget(self.content_widget)
        root_layout.addWidget(self.scroll)

    def _on_sim_zoom_clicked(self) -> None:
        """Toggle a simulated Zoom meeting session to demonstrate real-time tracking & reports."""
        active = self.session_tracker.get_active_sessions()
        zoom_active = any("zoom" in s.process_name.lower() for s in active)

        if zoom_active:
            # End zoom
            closed = self.session_tracker.close_session("zoom.exe")
            self.btn_sim_zoom.setText("محاكاة مكالمة Zoom")
            self._refresh_sessions_ui()
        else:
            # Start zoom
            self.session_tracker.start_or_update_session(
                app_name="Zoom Cloud Meetings",
                process_name="zoom.exe",
                pid=7812,
                category="conferencing",
                avg_bitrate=3.4,
                avg_latency=17.5,
            )
            self.btn_sim_zoom.setText("إنهاء مكالمة Zoom")
            self._refresh_sessions_ui()

    def _close_session_by_name(self, proc_name: str) -> None:
        """Callback from ActiveSessionCard to end a session and produce a report."""
        self.session_tracker.close_session(proc_name)
        if hasattr(self, "btn_sim_zoom") and "zoom" in proc_name.lower():
            self.btn_sim_zoom.setText("محاكاة مكالمة Zoom")
        self._refresh_sessions_ui()

    def _refresh_sessions_ui(self) -> None:
        """Re-render active session cards and completed reports list."""
        # 1. Clear active container
        while self.active_session_layout.count():
            item = self.active_session_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        active = self.session_tracker.get_active_sessions()
        if active:
            self.meeting_dot.setStyleSheet(f"background-color: {tokens.STATUS_OK}; border-radius: 4px;")
            self.meeting_lbl.setText("درع مكالمات الفيديو: نشط ومحمي استباقياً (Zoom / Teams / Meet قيد التشغيل حالياً)")
            self.meeting_lbl.setStyleSheet(f"color: {tokens.STATUS_OK};")
            self.active_session_container.setVisible(True)
            for session in active:
                card = ActiveSessionCard(
                    session=session,
                    on_close_callback=self._close_session_by_name,
                    parent=self.active_session_container,
                )
                self.active_session_layout.addWidget(card)
        else:
            self.meeting_dot.setStyleSheet(f"background-color: {tokens.TEXT_MUTED}; border-radius: 4px;")
            self.meeting_lbl.setText("درع مكالمات الفيديو: مؤمن (في وضع الاستعداد)")
            self.meeting_lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
            self.active_session_container.setVisible(False)

        # 2. Re-populate completed reports
        self._populate_session_reports()

    def _populate_session_reports(self) -> None:
        """Render all completed session reports."""
        self.report_cards: List[SessionReportCard] = []
        while self.reports_list_layout.count():
            item = self.reports_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        completed = self.session_tracker.get_completed_sessions()
        if not completed:
            empty_lbl = QLabel("لا توجد جلسات مكالمات سابقة مسجلة — ستظهر التقارير تلقائياً بعد إنهاء أي اجتماع (Zoom, Teams, Meet).")
            empty_lbl.setFont(tokens.get_sans_font(14, 400))
            empty_lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED}; padding: 16px 0;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setWordWrap(True)
            self.reports_list_layout.addWidget(empty_lbl)
            self.reports_panel.setVisible(False)
            return

        self.reports_panel.setVisible(True)
        for session in completed:
            card = SessionReportCard(session=session, parent=self.reports_list_container)
            self.report_cards.append(card)
            self.reports_list_layout.addWidget(card)

    def _populate_default_processes(self) -> None:
        """Initialize empty process table awaiting user scan."""
        self.table.setRowCount(0)

    def update_profiles(
        self,
        profiles: List[Any],
        conferencing_active: bool = False,
        qos_policies: Optional[List[Any]] = None,
    ) -> None:
        """Update live processes from traffic controller."""
        self._last_profiles_cache = list(profiles or [])
        self._refresh_sessions_ui()
        if not profiles:
            self.table.setRowCount(0)
            self._profile_sig = None
            self._qos_sig = None
            return

        active_policies = list(qos_policies) if qos_policies is not None else []
        throttled_apps = {
            (p.get("app_name") or "").lower(): p.get("throttle_bps")
            for p in active_policies
            if p.get("throttle_bps")
        }
        dscp_apps = {
            (p.get("app_name") or "").lower(): p.get("dscp_action")
            for p in active_policies
            if p.get("dscp_action") == 46
        }

        sorted_p = sorted(profiles, key=lambda p: getattr(p, "active_socket_count", 0), reverse=True)[:25]
        profile_sig = tuple(
            (
                getattr(p, "name", ""),
                getattr(p, "pid", 0),
                getattr(p, "active_socket_count", 0),
                round(float(getattr(p, "estimated_bandwidth_mbps", 0) or 0), 1),
                str(getattr(p, "category", "")),
                bool(getattr(p, "is_protected_system_process", False)),
            )
            for p in sorted_p
        )
        qos_sig = tuple(sorted(
            (name, throttled_apps.get(name), dscp_apps.get(name))
            for name in set(throttled_apps) | set(dscp_apps)
        ))
        if profile_sig == getattr(self, "_profile_sig", None) and qos_sig == getattr(self, "_qos_sig", None):
            return
        self._profile_sig = profile_sig
        self._qos_sig = qos_sig
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(sorted_p))
        max_sockets = max((getattr(p, "active_socket_count", 1) for p in sorted_p), default=1)

        for r, p in enumerate(sorted_p):
            self.table.setRowHeight(r, 56)
            pname = getattr(p, "name", "مجهول")
            pname_lower = pname.lower()
            pid_str = str(getattr(p, "pid", 0))
            sockets_cnt = getattr(p, "active_socket_count", 0)
            cat = str(getattr(p, "category", ""))
            is_conf = (
                "conferencing" in cat.lower()
                or "critical" in cat.lower()
                or pname_lower in (
                    "zoom.exe", "teams.exe", "ms-teams.exe", "obs64.exe", "obs32.exe",
                    "webex.exe", "ciscowebexstart.exe", "webexmta.exe", "slack.exe", "discord.exe"
                )
            )
            is_sys = getattr(p, "is_protected_system_process", False) or pname_lower in ApplicationCatalog.PROTECTED_SYSTEM_NAMES
            tag_text = "أولوية قصوى (اجتماع/تسجيل)" if is_conf else ("نظام أساسي" if is_sys else "طبيعي")

            is_throttled = pname_lower in throttled_apps
            is_dscp = pname_lower in dscp_apps

            # 0. Name
            item_name = QTableWidgetItem(pname)
            item_name.setFont(tokens.get_sans_font(14, 500))
            item_name.setToolTip(pname)
            self.table.setItem(r, 0, item_name)

            # 1. PID
            item_pid = QTableWidgetItem(pid_str)
            item_pid.setFont(tokens.get_mono_font(14, 400))
            self.table.setItem(r, 1, item_pid)

            # 2. Tag Chip (Centered pill container)
            chip = Chip(tag_text, variant="tag-ok" if is_conf else "ok-soft")
            chip_box = QWidget()
            chip_layout = QHBoxLayout(chip_box)
            chip_layout.setContentsMargins(4, 2, 4, 2)
            chip_layout.setAlignment(Qt.AlignCenter)
            chip_layout.addWidget(chip)
            self.table.setCellWidget(r, 2, chip_box)

            # 3. Bar & Sockets Cell
            frac = min(1.0, max(0.08, sockets_cnt / max(1, max_sockets)))
            est_mb = getattr(p, "estimated_bandwidth_mbps", None)
            conn_txt = tokens.format_arabic_connections(sockets_cnt)
            if est_mb and est_mb > 0.05:
                speed_txt = f"{conn_txt} · {tokens.bidi_isolate(f'~{est_mb:.1f}M')} (تقديري)"
            else:
                speed_txt = f"{conn_txt} (مقاسة)"
            cell_w = ProcessTableCell(speed_txt, frac, is_throttled=is_throttled)
            self.table.setCellWidget(r, 3, cell_w)

            # 4. Real QoS State Column
            if is_throttled:
                bps = throttled_apps[pname_lower]
                mbps = (bps / 1_000_000.0) if bps else 5.0
                qos_lbl = QLabel(f"مقيد: {tokens.bidi_isolate(f'{mbps:.1f} Mbps')} (صادر)")
                qos_lbl.setFont(tokens.get_sans_font(14, 500))
                qos_lbl.setStyleSheet(f"color: {tokens.STATUS_WARN};")
            elif is_dscp:
                qos_lbl = QLabel(f"أولوية {tokens.bidi_isolate('DSCP 46')} (صادر)")
                qos_lbl.setFont(tokens.get_sans_font(14, 500))
                qos_lbl.setStyleSheet(f"color: {tokens.STATUS_OK};")
            else:
                qos_lbl = QLabel("غير مقيد (افتراضي)")
                qos_lbl.setFont(tokens.get_sans_font(14, 400))
                qos_lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
            qos_lbl.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(r, 4, qos_lbl)

            # 5. QoS Action Button
            if is_sys:
                lbl_prot = QLabel("عملية نظام محمية")
                lbl_prot.setFont(tokens.get_sans_font(13, 400))
                lbl_prot.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
                lbl_prot.setAlignment(Qt.AlignCenter)
                lbl_prot.setToolTip("عملية نظام محمية — لا يمكن تقييدها أو إيقافها لضمان استقرار نظام التشغيل")
                self.table.setCellWidget(r, 5, lbl_prot)
            elif is_conf:
                lbl_prot = QLabel("محمي (أولوية قصوى)")
                lbl_prot.setFont(tokens.get_sans_font(13, 600))
                lbl_prot.setStyleSheet(f"color: {tokens.STATUS_OK}; padding: 4px 8px;")
                lbl_prot.setAlignment(Qt.AlignCenter)
                lbl_prot.setToolTip("تطبيق اجتماع/تسجيل محمي بأولوية قصوى — لا يتم تقييده مطلقاً للحفاظ على جودة الصوت والفيديو")
                self.table.setCellWidget(r, 5, lbl_prot)
            else:
                cfg_bps = 5_000_000
                if self.user_settings and hasattr(self.user_settings, "get_qos_upload_throttle_bps"):
                    cfg_bps = self.user_settings.get_qos_upload_throttle_bps()
                cfg_mbps = cfg_bps / 1_000_000.0
                btn_th = SecondaryButton("إلغاء التقييد" if is_throttled else f"تقييد ({tokens.bidi_isolate(f'{cfg_mbps:.0f}M')})")
                btn_th.setFixedHeight(34)
                btn_th.setMinimumWidth(125)
                btn_th.setStyleSheet(f"""
                    QPushButton {{
                        padding: 4px 12px;
                        font-size: 12px;
                        font-weight: 500;
                    }}
                """)
                btn_th.clicked.connect(lambda checked=False, pn=pname, en=not is_throttled: self._on_toggle_throttle(pn, en))
                btn_box = QWidget()
                btn_layout = QHBoxLayout(btn_box)
                btn_layout.setContentsMargins(6, 4, 6, 4)
                btn_layout.setAlignment(Qt.AlignCenter)
                btn_layout.addWidget(btn_th)
                self.table.setCellWidget(r, 5, btn_box)
                self.table.setCellWidget(r, 5, btn_box)

        self.table.setSortingEnabled(True)
        fit_table_to_content(self.table)

    def _on_toggle_throttle(self, pname: str, enable: bool) -> None:
        """Create or remove Windows NetQosPolicy upload throttle for executable asynchronously."""
        from app.platform.admin import require_admin, prompt_restart_as_admin
        ok_admin, reason = require_admin(f"تقييد سرعة الرفع لـ {pname}", self.platform)
        if not ok_admin:
            prompt_restart_as_admin(self, f"تقييد سرعة الرفع الصادر لـ {pname}", self.platform)
            return

        policy_name = f"NetGuard_Throttle_{pname}"
        throttle_bps = 5_000_000
        if self.user_settings and hasattr(self.user_settings, "get_qos_upload_throttle_bps"):
            throttle_bps = self.user_settings.get_qos_upload_throttle_bps()

        def _worker():
            if enable:
                ok, msg = self.platform.create_qos_throttle_policy(policy_name, pname, throttle_bps)
            else:
                ok, msg = self.platform.remove_qos_policy(policy_name)
            self.qos_policy_done.emit(ok, msg)

        import threading
        threading.Thread(target=_worker, daemon=True).start()

    def _on_toggle_dscp(self, pname: str, enable: bool) -> None:
        """Create or remove Windows NetQosPolicy DSCP 46 tagging for executable asynchronously."""
        from app.platform.admin import require_admin, prompt_restart_as_admin
        ok_admin, reason = require_admin(f"تحديد أولوية DSCP 46 لـ {pname}", self.platform)
        if not ok_admin:
            prompt_restart_as_admin(self, f"تحديد أولوية DSCP 46 لـ {pname}", self.platform)
            return

        policy_name = f"NetGuard_DSCP_{pname}"

        def _worker():
            if enable:
                ok, msg = self.platform.create_qos_dscp_policy(policy_name, pname, 46)
            else:
                ok, msg = self.platform.remove_qos_policy(policy_name)
            self.qos_policy_done.emit(ok, msg)

        import threading
        threading.Thread(target=_worker, daemon=True).start()

    def _on_qos_policy_done(self, ok: bool, msg: str) -> None:
        if not ok:
            QMessageBox.warning(self, "سياسة QoS في ويندوز", msg)
        self.update_profiles(self._last_profiles_cache)

    def _sync_content_width(self) -> None:
        if hasattr(self, "scroll") and hasattr(self, "content_widget"):
            vw = self.scroll.viewport().width()
            if vw > 0:
                self.content_widget.setFixedWidth(vw)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_content_width()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_content_width()
        w = self.width()
        if w < 700:
            self.content_layout.setContentsMargins(
                tokens.PAGE_PADDING_NARROW, 16, tokens.PAGE_PADDING_NARROW, 24
            )
            self.table.setColumnHidden(1, True)
            self.table.setColumnHidden(4, True)
        else:
            self.content_layout.setContentsMargins(
                tokens.PAGE_PADDING_DESKTOP, 28, tokens.PAGE_PADDING_DESKTOP, 36
            )
            self.table.setColumnHidden(1, False)
            self.table.setColumnHidden(4, False)
