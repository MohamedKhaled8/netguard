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
from PySide6.QtCore import Qt, Signal
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
        lbl.setFixedWidth(75)
        layout.addWidget(lbl)

        fill_color = tokens.STATUS_WARN if is_throttled else tokens.ACCENT
        bar = HorizontalProgressBar(height=6, fill_color=fill_color, parent=self)
        bar.set_fraction(fraction)
        layout.addWidget(bar, stretch=1)


class TrafficView(QWidget):
    """Traffic monitoring and meeting session quality view."""

    start_simulated_zoom_requested = Signal()
    close_simulated_zoom_requested = Signal()

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
        self.setStyleSheet(f"background-color: {tokens.BG};")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {tokens.BG}; border: none; }}")

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet(f"background-color: {tokens.BG};")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(
            tokens.PAGE_PADDING_DESKTOP, 28, tokens.PAGE_PADDING_DESKTOP, 36
        )
        self.content_layout.setSpacing(tokens.SECTION_GAP)
        layout = self.content_layout

        # -------------------------------------------------------------
        # 1. Header & Controls
        # -------------------------------------------------------------
        header_panel = Panel(
            title="حركة البيانات وتأمين التطبيقات",
            subtitle="مراقبة استهلاك البرامج للباندويث وحماية مكالمات الفيديو والبث الحي من أي تقطيع",
            parent=self,
        )

        header_col = QVBoxLayout()
        header_col.setSpacing(12)

        self.lbl_subtitle = QLabel(
            "يتم رصد البرامج التي تستنزف سرعة الرفع والتنزيل لضمان استقرار جلسات Zoom و Google Meet دون تأخير."
        )
        self.lbl_subtitle.setFont(tokens.get_sans_font(13, 400))
        self.lbl_subtitle.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_subtitle.setWordWrap(True)
        header_col.addWidget(self.lbl_subtitle)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        # Simulation button hidden in production per non-negotiable principle
        self.btn_sim_zoom = SecondaryButton("محاكاة مكالمة Zoom")
        self.btn_sim_zoom.setToolTip("تم إخفاء زر المحاكاة لضمان عدم إدراج بيانات وهمية في بيئة التشغيل الحقيقية")
        self.btn_sim_zoom.setVisible(False)
        self.btn_sim_zoom.clicked.connect(self._on_sim_zoom_clicked)

        self.btn_refresh = PrimaryButton("فحص البرامج النشطة")
        btn_box.addWidget(self.btn_refresh)
        btn_box.addStretch()

        header_col.addLayout(btn_box)
        header_panel.main_layout.addLayout(header_col)
        layout.addWidget(header_panel)

        # -------------------------------------------------------------
        # 2. Priority Protection & Active Session (Meeting Guard)
        # -------------------------------------------------------------
        self.guard_panel = Panel(
            title="درع مكالمات الفيديو والبث المباشر - Meeting Guard",
            subtitle="مراقبة جلسات مكالمات الفيديو وحماية استقرار الاتصال وتعليق الإجراءات التي تسبب انقطاعاً لحظياً",
            parent=self,
        )

        # Top toggle row
        guard_row = QHBoxLayout()
        guard_row.setSpacing(16)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)

        lbl_row = QHBoxLayout()
        lbl_row.setSpacing(8)
        self.meeting_dot = QLabel()
        self.meeting_dot.setFixedSize(7, 7)
        self.meeting_dot.setStyleSheet(f"background-color: {tokens.TEXT_MUTED}; border-radius: 3.5px;")
        lbl_row.addWidget(self.meeting_dot)

        self.meeting_lbl = QLabel("وضع مكالمات الفيديو: مؤمن (لا توجد مكالمات Zoom / Teams جارية حالياً)")
        self.meeting_lbl.setFont(tokens.get_sans_font(13, 500))
        self.meeting_lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.meeting_lbl.setWordWrap(True)
        lbl_row.addWidget(self.meeting_lbl, stretch=1)

        text_col.addLayout(lbl_row)

        lbl_guard_desc = QLabel("عند تفعيل هذا الخيار، يقوم درع الاجتماعات برصد مكالمات الفيديو وتعليق الإجراءات التي تسبب انقطاعاً لحظياً طوال مدة المكالمة.")
        lbl_guard_desc.setFont(tokens.get_sans_font(12, 400))
        lbl_guard_desc.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        lbl_guard_desc.setWordWrap(True)
        text_col.addWidget(lbl_guard_desc)

        guard_row.addLayout(text_col, stretch=1)

        self.guard_toggle = ToggleSwitch(checked=True, parent=self)
        guard_row.addWidget(self.guard_toggle)

        self.guard_panel.main_layout.addLayout(guard_row)

        # Active Session Container
        self.active_session_container = QWidget()
        self.active_session_layout = QVBoxLayout(self.active_session_container)
        self.active_session_layout.setContentsMargins(0, 10, 0, 0)
        self.active_session_layout.setSpacing(10)
        self.guard_panel.main_layout.addWidget(self.active_session_container)

        layout.addWidget(self.guard_panel)

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
        layout.addWidget(self.reports_panel)

        # Populate initial historical session reports
        self._populate_session_reports()

        # -------------------------------------------------------------
        # 4. Expanded Process Consumers Table
        # -------------------------------------------------------------
        table_panel = Panel(
            title="قائمة البرامج المتصلة بالإنترنت حالياً",
            subtitle="مرتبة حسب عدد الاتصالات النشطة، مع إمكانية تقييد سرعة الرفع الصادر (Outbound Throttle) عبر Windows NetQosPolicy",
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
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent;
                border: none;
                gridline-color: {tokens.LINE};
            }}
            QTableWidget::item {{
                border-bottom: 1px solid {tokens.LINE};
                padding: 8px 10px;
                color: {tokens.TEXT};
            }}
        """)

        table_panel.main_layout.addWidget(self.table)
        layout.addWidget(table_panel)

        self._populate_default_processes()

        scroll.setWidget(self.content_widget)
        root_layout.addWidget(scroll)

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
            self.meeting_dot.setStyleSheet(f"background-color: {tokens.STATUS_OK}; border-radius: 3.5px;")
            self.meeting_lbl.setText("وضع مكالمات الفيديو: نشط ومحمي استباقياً (Zoom / Teams قيد التشغيل حالياً)")
            self.meeting_lbl.setStyleSheet(f"color: {tokens.STATUS_OK};")
            for session in active:
                card = ActiveSessionCard(
                    session=session,
                    on_close_callback=self._close_session_by_name,
                    parent=self.active_session_container,
                )
                self.active_session_layout.addWidget(card)
        else:
            self.meeting_dot.setStyleSheet(f"background-color: {tokens.TEXT_MUTED}; border-radius: 3.5px;")
            self.meeting_lbl.setText("وضع مكالمات الفيديو: مؤمن (لا توجد مكالمات Zoom / Teams جارية حالياً)")
            self.meeting_lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED};")

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
            empty_lbl.setFont(tokens.get_sans_font(13, 400))
            empty_lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED}; padding: 16px 0;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.reports_list_layout.addWidget(empty_lbl)
            return

        for session in completed:
            card = SessionReportCard(session=session, parent=self.reports_list_container)
            self.report_cards.append(card)
            self.reports_list_layout.addWidget(card)

    def _populate_default_processes(self) -> None:
        """Initialize empty process table awaiting user scan."""
        self.table.setRowCount(0)

    def update_profiles(self, profiles: List[Any], conferencing_active: bool = False) -> None:
        """Update live processes from traffic controller."""
        self._last_profiles_cache = list(profiles or [])
        self._refresh_sessions_ui()
        if not profiles:
            self.table.setRowCount(0)
            return

        active_policies = self.platform.get_qos_policies() if self.platform else []
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
        self.table.setRowCount(len(sorted_p))
        max_sockets = max((getattr(p, "active_socket_count", 1) for p in sorted_p), default=1)

        for r, p in enumerate(sorted_p):
            pname = getattr(p, "name", "مجهول")
            pname_lower = pname.lower()
            pid_str = str(getattr(p, "pid", 0))
            sockets_cnt = getattr(p, "active_socket_count", 0)
            cat = str(getattr(p, "category", ""))
            is_conf = "conferencing" in cat.lower() or "critical" in cat.lower()
            is_sys = getattr(p, "is_protected_system_process", False) or pname_lower in ApplicationCatalog.PROTECTED_SYSTEM_NAMES
            tag_text = "أولوية مكالمات" if is_conf else ("نظام أساسي" if is_sys else "طبيعي")

            is_throttled = pname_lower in throttled_apps
            is_dscp = pname_lower in dscp_apps

            # 0. Name
            item_name = QTableWidgetItem(pname)
            item_name.setFont(tokens.get_sans_font(13, 500))
            self.table.setItem(r, 0, item_name)

            # 1. PID
            item_pid = QTableWidgetItem(pid_str)
            item_pid.setFont(tokens.get_mono_font(12, 400))
            self.table.setItem(r, 1, item_pid)

            # 2. Tag Chip
            chip = Chip(tag_text, variant="tag-ok" if is_conf else "ok-soft")
            self.table.setCellWidget(r, 2, chip)

            # 3. Bar & Sockets Cell
            frac = min(1.0, max(0.08, sockets_cnt / max(1, max_sockets)))
            est_mb = getattr(p, "estimated_bandwidth_mbps", None)
            if est_mb and est_mb > 0.05:
                speed_txt = f"{sockets_cnt} · ~{est_mb:.1f}M (تقديري)"
            else:
                speed_txt = f"{sockets_cnt} اتصالات (مقاسة)"
            cell_w = ProcessTableCell(speed_txt, frac, is_throttled=is_throttled)
            self.table.setCellWidget(r, 3, cell_w)

            # 4. Real QoS State Column
            if is_throttled:
                bps = throttled_apps[pname_lower]
                mbps = (bps / 1_000_000.0) if bps else 5.0
                qos_lbl = QLabel(f"مقيد: {mbps:.1f} Mbps (صادر)")
                qos_lbl.setFont(tokens.get_sans_font(12, 500))
                qos_lbl.setStyleSheet(f"color: {tokens.STATUS_WARN};")
            elif is_dscp:
                qos_lbl = QLabel("أولوية DSCP 46 (صادر)")
                qos_lbl.setFont(tokens.get_sans_font(12, 500))
                qos_lbl.setStyleSheet(f"color: {tokens.STATUS_OK};")
            else:
                qos_lbl = QLabel("غير مقيد (افتراضي)")
                qos_lbl.setFont(tokens.get_sans_font(12, 400))
                qos_lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
            qos_lbl.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(r, 4, qos_lbl)

            # 5. QoS Action Button
            if is_sys:
                lbl_prot = QLabel("محمي للنظام")
                lbl_prot.setFont(tokens.get_sans_font(12, 400))
                lbl_prot.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
                lbl_prot.setAlignment(Qt.AlignCenter)
                self.table.setCellWidget(r, 5, lbl_prot)
            elif is_conf:
                btn_dscp = SecondaryButton("إلغاء DSCP" if is_dscp else "أولوية DSCP")
                btn_dscp.setFixedHeight(28)
                btn_dscp.clicked.connect(lambda checked=False, pn=pname, en=not is_dscp: self._on_toggle_dscp(pn, en))
                self.table.setCellWidget(r, 5, btn_dscp)
            else:
                cfg_bps = 5_000_000
                if self.user_settings and hasattr(self.user_settings, "get_qos_upload_throttle_bps"):
                    cfg_bps = self.user_settings.get_qos_upload_throttle_bps()
                cfg_mbps = cfg_bps / 1_000_000.0
                btn_th = SecondaryButton("إلغاء التقييد" if is_throttled else f"تقييد ({cfg_mbps:.0f}M)")
                btn_th.setFixedHeight(28)
                btn_th.clicked.connect(lambda checked=False, pn=pname, en=not is_throttled: self._on_toggle_throttle(pn, en))
                self.table.setCellWidget(r, 5, btn_th)

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
            QTimer.singleShot(0, lambda o=ok, m=msg: self._on_qos_policy_done(o, m))

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
            QTimer.singleShot(0, lambda o=ok, m=msg: self._on_qos_policy_done(o, m))

        import threading
        threading.Thread(target=_worker, daemon=True).start()

    def _on_qos_policy_done(self, ok: bool, msg: str) -> None:
        if not ok:
            QMessageBox.warning(self, "سياسة QoS في ويندوز", msg)
        self.update_profiles(self._last_profiles_cache)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
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
