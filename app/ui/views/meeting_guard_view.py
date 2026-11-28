"""Meeting Guard & QoS Protection Control Center View for NetGuard AI.

Presents:
- Meeting detection status, active media processes, and ETW UDP send telemetry
- 6-stage Meeting Lifecycle Stepper (Idle -> Detecting -> Calibrating -> Active -> Leaving -> Restored)
- Real QoS Policy Matrix generated from AppQoSConfig + Windows ActiveStore readback verification
- Per-app controls, Teams port split, background upload throttle info, DNS freeze & Rollback state
- Embedded Operating Mode + Autonomous Remediation Policies (replaces standalone RemediationView nav clutter while preserving full RemediationView compatibility)
"""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.platform.interfaces import IPlatformAdapter
from app.traffic.controller import TrafficController
from app.traffic.meeting_registry import MeetingAppRegistry
from app.traffic.qos_config import AppQoSConfig
from app.traffic.session_tracker import AppSessionTracker
from app.ui import tokens
from app.ui.i18n import language_manager, tr
from app.ui.icons import create_icon
from app.ui.views.remediation_view import RemediationView
from app.ui.widgets.base_panel import Panel
from app.ui.widgets.buttons import GhostButton, PrimaryButton, SecondaryButton
from app.ui.widgets.chip import Chip
from app.ui.widgets.qos_visualizer import MeetingLifecycleStepper, QoSPolicyMatrixWidget
from app.ui.widgets.session_card import ActiveSessionCard, SessionReportCard
from app.ui.widgets.status_badge import StatusBadge
from app.ui.widgets.toggle import ToggleSwitch


class MeetingGuardView(QScrollArea):
    """Meeting Guard & QoS Protection Control Center."""

    preflight_requested = Signal()
    kill_switch_triggered = Signal()
    qos_policy_done = Signal(bool, str)

    def __init__(
        self,
        *,
        session_tracker: Optional[AppSessionTracker] = None,
        platform: Optional[IPlatformAdapter] = None,
        user_settings: Optional[Any] = None,
        qos_config: Optional[AppQoSConfig] = None,
        controller: Optional[TrafficController] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("background: transparent; border: none;")

        self.session_tracker = session_tracker or AppSessionTracker()
        self.platform = platform
        self.user_settings = user_settings
        self.qos_config = qos_config or (
            AppQoSConfig.from_user_settings(user_settings) if user_settings else AppQoSConfig()
        )
        self.controller = controller
        self._in_kill_switch = False
        self._last_profiles: List[Any] = []
        self._last_os_policies: List[Dict[str, Any]] = []
        self._rolled_back = False
        self._rollback_reason = ""

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        outer = QHBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setAlignment(Qt.AlignHCenter)

        self.content_holder = QWidget()
        self.content_holder.setMaximumWidth(tokens.MAX_CONTENT_WIDTH)
        self.content_holder.setStyleSheet("background: transparent;")
        self.root_layout = QVBoxLayout(self.content_holder)
        self.root_layout.setContentsMargins(24, 20, 24, 32)
        self.root_layout.setSpacing(16)
        outer.addWidget(self.content_holder)
        self.setWidget(container)

        # ------------------------------------------------------------------
        # 1. Control Center Header (Live Call State + Master Toggle + Kill Switch)
        # ------------------------------------------------------------------
        hdr_card = QFrame()
        hdr_card.setObjectName("MeetingGuardHeader")
        hdr_card.setStyleSheet(
            f"""
            QFrame#MeetingGuardHeader {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_PANEL}px;
            }}
            """
        )
        hdr_lay = QVBoxLayout(hdr_card)
        hdr_lay.setContentsMargins(20, 16, 20, 16)
        hdr_lay.setSpacing(12)

        top_row = QVBoxLayout()
        top_row.setSpacing(8)
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        self.lbl_title = QLabel(tr("mg_title"))
        self.lbl_title.setFont(tokens.get_sans_font(20, 700))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_title.setWordWrap(True)
        self.lbl_sub = QLabel(tr("mg_sub"))
        self.lbl_sub.setFont(tokens.get_sans_font(12, 400))
        self.lbl_sub.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_sub.setWordWrap(True)
        title_col.addWidget(self.lbl_title)
        title_col.addWidget(self.lbl_sub)
        top_row.addLayout(title_col)

        badges_row = QHBoxLayout()
        badges_row.setSpacing(8)
        self.badge_call_state = StatusBadge(tokens.SystemStatus.WAITING, tr("status.waiting"))
        self.badge_qos_verify = StatusBadge(tokens.SystemStatus.WAITING, tr("dash.qos_pending"))
        badges_row.addWidget(self.badge_call_state)
        badges_row.addWidget(self.badge_qos_verify)
        badges_row.addStretch()
        top_row.addLayout(badges_row)
        hdr_lay.addLayout(top_row)

        # Telemetry KPI strip inside header (2x2 clean grid prevents clipping at 1100px)
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(10)
        self._kpi_app = self._make_mini_kpi("التطبيق المكتشف", "—")
        self._kpi_process = self._make_mini_kpi("عملية الوسائط", "—")
        self._kpi_etw = self._make_mini_kpi(tr("mg.etw_label"), "—")
        self._kpi_dns_freeze = self._make_mini_kpi(tr("mg.dns_freeze"), "غير مجمّد")
        kpi_grid.addWidget(self._kpi_app[0], 0, 0)
        kpi_grid.addWidget(self._kpi_process[0], 0, 1)
        kpi_grid.addWidget(self._kpi_etw[0], 1, 0)
        kpi_grid.addWidget(self._kpi_dns_freeze[0], 1, 1)
        hdr_lay.addLayout(kpi_grid)

        # Action & Master Switch bar
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)

        master_wrap = QHBoxLayout()
        master_wrap.setSpacing(8)
        self.master_qos_toggle = ToggleSwitch(checked=bool(self.qos_config.master_enabled))
        self.master_qos_toggle.toggled.connect(self._on_master_toggled)
        self.lbl_master_toggle = QLabel(tr("mg.master_toggle"))
        self.lbl_master_toggle.setFont(tokens.get_sans_font(12, 600))
        self.lbl_master_toggle.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_master_toggle.setWordWrap(True)
        master_wrap.addWidget(self.master_qos_toggle)
        master_wrap.addWidget(self.lbl_master_toggle, 1)
        ctrl_row.addLayout(master_wrap, 1)

        self.btn_start_monitor = PrimaryButton("بدء المراقبة والحماية")
        self.btn_start_monitor.clicked.connect(self.start_monitoring)

        self.btn_stop_monitor = SecondaryButton("إيقاف المراقبة")
        self.btn_stop_monitor.clicked.connect(self.stop_monitoring)

        self.btn_calibrate = SecondaryButton("معايرة وتجهيز للاجتماع")
        self.btn_calibrate.setIcon(create_icon("internet_quality", tokens.TEXT, 14))
        self.btn_calibrate.clicked.connect(self.calibrate_network_for_meeting)
        # Keep backwards-compatible attribute alias `btn_preflight`
        self.btn_preflight = self.btn_calibrate

        self.btn_retry_detect = SecondaryButton("إعادة محاولة الرصد")
        self.btn_retry_detect.clicked.connect(self.retry_meeting_detection)

        self.btn_reconcile = SecondaryButton("فحص ActiveStore")
        self.btn_reconcile.clicked.connect(lambda: self.refresh_policy_matrix(fetch_activestore=True))

        self.btn_kill_switch = PrimaryButton(tr("mg.kill_switch"))
        self.btn_kill_switch.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {tokens.STATUS_BAD};
                color: #FFFFFF;
                border: 1px solid {tokens.BAD_SOFT_BORDER};
                border-radius: 8px;
                padding: 0px 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: #DC2626; }}
            """
        )
        self.btn_kill_switch.clicked.connect(self._on_kill_switch_clicked)

        actions_wrap = QGridLayout()
        actions_wrap.setSpacing(8)
        actions_wrap.addWidget(self.btn_start_monitor, 0, 0)
        actions_wrap.addWidget(self.btn_stop_monitor, 0, 1)
        actions_wrap.addWidget(self.btn_calibrate, 1, 0)
        actions_wrap.addWidget(self.btn_retry_detect, 1, 1)
        actions_wrap.addWidget(self.btn_reconcile, 2, 0)
        actions_wrap.addWidget(self.btn_kill_switch, 2, 1)

        hdr_lay.addLayout(ctrl_row)
        hdr_lay.addLayout(actions_wrap)

        self.lbl_op_feedback = QLabel("")
        self.lbl_op_feedback.setFont(tokens.get_sans_font(12, 500))
        self.lbl_op_feedback.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self.lbl_op_feedback.setWordWrap(True)
        self.lbl_op_feedback.setVisible(False)
        hdr_lay.addWidget(self.lbl_op_feedback)
        self.root_layout.addWidget(hdr_card)

        # Rollback warning strip (hidden unless rollback occurred)
        self.rollback_banner = QFrame()
        self.rollback_banner.setVisible(False)
        self.rollback_banner.setStyleSheet(
            f"background-color: {tokens.WARN_SOFT_BG}; border: 1px solid {tokens.WARN_BORDER}; border-radius: 8px;"
        )
        rb_lay = QHBoxLayout(self.rollback_banner)
        rb_lay.setContentsMargins(14, 8, 14, 8)
        self.lbl_rollback_msg = QLabel("")
        self.lbl_rollback_msg.setFont(tokens.get_sans_font(12, 600))
        self.lbl_rollback_msg.setStyleSheet(f"color: {tokens.STATUS_WARN}; border: none; background: transparent;")
        self.lbl_rollback_msg.setWordWrap(True)
        rb_lay.addWidget(self.lbl_rollback_msg)
        self.root_layout.addWidget(self.rollback_banner)

        # ------------------------------------------------------------------
        # 2. Meeting Lifecycle Visualization (6 Real Stages)
        # ------------------------------------------------------------------
        self.lifecycle_stepper = MeetingLifecycleStepper()
        self.root_layout.addWidget(self.lifecycle_stepper)

        # ------------------------------------------------------------------
        # 3. Live QoS Traffic Classes Matrix (Driven by Config + ActiveStore)
        # ------------------------------------------------------------------
        self.qos_matrix = QoSPolicyMatrixWidget()
        self.root_layout.addWidget(self.qos_matrix)

        # ------------------------------------------------------------------
        # 4. Per-App Protection + Background Throttling + Active Sessions
        # ------------------------------------------------------------------
        split_row = QGridLayout()
        split_row.setSpacing(14)

        self.panel_apps = Panel(
            title=tr("mg.app_controls"),
            subtitle=tr("mg.app_controls_sub"),
            padding=18,
        )
        self.app_toggles: Dict[str, ToggleSwitch] = {}
        apps_grid = QGridLayout()
        apps_grid.setSpacing(10)
        entries = MeetingAppRegistry.all_entries()
        for idx, entry in enumerate(entries):
            row_w = QFrame()
            row_w.setStyleSheet(
                f"background-color: {tokens.SURFACE_INSET}; border: 1px solid {tokens.LINE}; border-radius: 8px;"
            )
            rl = QHBoxLayout(row_w)
            rl.setContentsMargins(10, 8, 10, 8)
            rl.setSpacing(8)
            enabled = bool(self.qos_config.enabled_apps.get(entry.id, True))
            sw = ToggleSwitch(checked=enabled)
            sw.toggled.connect(lambda ch, aid=entry.id: self._on_app_toggled(aid, ch))
            self.app_toggles[entry.id] = sw
            lbl = QLabel(entry.display_name)
            lbl.setFont(tokens.get_sans_font(12, 600))
            lbl.setStyleSheet(f"color: {tokens.TEXT}; border: none; background: transparent;")
            lbl.setWordWrap(True)
            dscp_val = entry.media_profile.default_dscp if getattr(entry, "media_profile", None) else 34
            dscp_chip = Chip(f"DSCP {dscp_val}", variant="info", font_size=12)
            rl.addWidget(sw)
            rl.addWidget(lbl, 1)
            rl.addWidget(dscp_chip)
            apps_grid.addWidget(row_w, idx // 2, idx % 2)
        self.panel_apps.main_layout.addLayout(apps_grid)

        teams_row = QHBoxLayout()
        teams_row.setSpacing(8)
        self.teams_split_toggle = ToggleSwitch(checked=bool(self.qos_config.enable_teams_port_split))
        self.teams_split_toggle.toggled.connect(self._on_teams_split_toggled)
        self.lbl_teams_split = QLabel(tr("mg.teams_split"))
        self.lbl_teams_split.setFont(tokens.get_sans_font(12, 500))
        self.lbl_teams_split.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_teams_split.setWordWrap(True)
        teams_row.addWidget(self.teams_split_toggle)
        teams_row.addWidget(self.lbl_teams_split, 1)
        self.panel_apps.main_layout.addLayout(teams_row)

        self.lbl_throttle_summary = QLabel("")
        self.lbl_throttle_summary.setFont(tokens.get_mono_font(12, 500))
        self.lbl_throttle_summary.setStyleSheet(f"color: {tokens.SECONDARY_PURPLE};")
        self._update_throttle_label()
        self.panel_apps.main_layout.addWidget(self.lbl_throttle_summary)

        # Active & completed sessions card
        self.panel_sessions = Panel(
            title=tr("mg.sessions_active"),
            subtitle=tr("mg.sessions_completed"),
            padding=18,
        )
        self.sessions_box = QVBoxLayout()
        self.sessions_box.setSpacing(8)
        self.lbl_no_sessions = QLabel(tr("dash.guard_idle_detail"))
        self.lbl_no_sessions.setFont(tokens.get_sans_font(12, 400))
        self.lbl_no_sessions.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_no_sessions.setWordWrap(True)
        self.sessions_box.addWidget(self.lbl_no_sessions)
        self.panel_sessions.main_layout.addLayout(self.sessions_box)
        self.panel_sessions.main_layout.addStretch()

        split_row.addWidget(self.panel_apps, 0, 0)
        split_row.addWidget(self.panel_sessions, 0, 1)
        self.root_layout.addLayout(split_row)

        # ------------------------------------------------------------------
        # 5. Embedded Operating Mode & Autonomous Remediation Policies
        #    Embedded without nested QScrollArea so content & caps never clip.
        # ------------------------------------------------------------------
        self.remediation_section = RemediationView(parent=self, embed_in_scroll=True)
        self.root_layout.addWidget(self.remediation_section)

        self.qos_policy_done.connect(self._on_qos_done)
        language_manager().language_changed.connect(self.retranslate)
        self.refresh_policy_matrix()

    @staticmethod
    def _make_mini_kpi(title: str, initial: str) -> tuple[QFrame, QLabel]:
        box = QFrame()
        box.setStyleSheet(
            f"background-color: {tokens.SURFACE_INSET}; border: 1px solid {tokens.LINE}; border-radius: 8px;"
        )
        lay = QVBoxLayout(box)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(3)
        t = QLabel(title)
        t.setFont(tokens.get_sans_font(12, 500))
        t.setStyleSheet(f"color: {tokens.TEXT_MUTED}; border: none; background: transparent;")
        t.setWordWrap(True)
        v = QLabel(initial)
        v.setFont(tokens.get_mono_font(13, 600))
        v.setStyleSheet(f"color: {tokens.TEXT}; border: none; background: transparent;")
        v.setWordWrap(True)
        lay.addWidget(t)
        lay.addWidget(v)
        return box, v

    def _update_throttle_label(self) -> None:
        bps = self.qos_config.min_throttle_bps_per_app
        if self.user_settings and hasattr(self.user_settings, "get_qos_upload_throttle_bps"):
            try:
                bps = int(self.user_settings.get_qos_upload_throttle_bps())
            except Exception:
                pass
        mbps = bps / 1_000_000.0
        state_txt = "Enabled" if self.qos_config.bulk_throttle_enabled else "Disabled"
        self.lbl_throttle_summary.setText(
            tokens.bidi_isolate_mixed(f"Bulk Upload Cap: {mbps:.1f} Mbps ({state_txt}) · Headroom Reserve: {int(self.qos_config.non_meeting_headroom_ratio * 100)}%")
        )

    def retranslate(self) -> None:
        self.lbl_title.setText(tr("mg_title"))
        self.lbl_sub.setText(tr("mg_sub"))
        self.lbl_master_toggle.setText(tr("mg.master_toggle"))
        self.btn_preflight.setText(tr("dash.btn_preflight"))
        self.btn_kill_switch.setText(tr("mg.kill_switch"))
        self.panel_apps.set_titles(tr("mg.app_controls"), tr("mg.app_controls_sub"))
        self.lbl_teams_split.setText(tr("mg.teams_split"))
        self.panel_sessions.set_titles(tr("mg.sessions_active"), tr("mg.sessions_completed"))
        self.refresh_policy_matrix()

    def _on_master_toggled(self, checked: bool) -> None:
        self.qos_config.master_enabled = checked
        if self.user_settings and hasattr(self.user_settings, "set_policy"):
            self.user_settings.set_policy("qos_master_enabled", checked)
        if not checked and not self._in_kill_switch:
            self._on_kill_switch_clicked()
        else:
            self.refresh_policy_matrix()

    def _on_app_toggled(self, app_id: str, checked: bool) -> None:
        self.qos_config.enabled_apps[app_id] = checked
        entry = MeetingAppRegistry.get_entry_by_id(app_id)
        if entry:
            for exe in list(entry.exe_names) + list(entry.extra_exes):
                self.qos_config.enabled_apps[exe.lower()] = checked
        if self.user_settings and hasattr(self.user_settings, "set_policy"):
            self.user_settings.set_policy("qos_enabled_apps", self.qos_config.enabled_apps)
        self.refresh_policy_matrix()

    def _on_teams_split_toggled(self, checked: bool) -> None:
        self.qos_config.enable_teams_port_split = checked
        if self.user_settings and hasattr(self.user_settings, "set_policy"):
            self.user_settings.set_policy("qos_teams_port_split", checked)
        self.refresh_policy_matrix()

    def _set_feedback(self, msg: str, color: str = tokens.TEXT_SECONDARY) -> None:
        self.lbl_op_feedback.setText(tokens.bidi_isolate_mixed(msg))
        self.lbl_op_feedback.setStyleSheet(f"color: {color};")
        self.lbl_op_feedback.setVisible(bool(msg))

    def start_monitoring(self) -> None:
        self._monitoring_paused = False
        self.qos_config.master_enabled = True
        self.master_qos_toggle.setChecked(True)
        if self.user_settings and hasattr(self.user_settings, "set_policy"):
            self.user_settings.set_policy("qos_master_enabled", True)
        self.badge_call_state.set_status(tokens.SystemStatus.RUNNING, "يراقب الاجتماعات")
        self.lifecycle_stepper.set_stage(
            "detecting",
            "تم تشغيل مراقبة الاجتماعات — يتم الآن فحص عمليات الصوت والفيديو ونشاط UDP."
        )
        self._set_feedback("بدأت المراقبة والحماية التلقائية — يتم التحقق من مخزن ActiveStore.", tokens.STATUS_OK)
        self.retry_meeting_detection()

    def stop_monitoring(self) -> None:
        self._monitoring_paused = True
        self.badge_call_state.set_status(tokens.SystemStatus.WAITING, "المراقبة متوقفة")
        self.lifecycle_stepper.set_stage(
            "idle",
            "تم إيقاف المراقبة يدوياً — يمكنك إعادة تشغيلها في أي وقت بالضغط على «بدء المراقبة والحماية»."
        )
        self._set_feedback("تم إيقاف مراقبة الاجتماعات مؤقتاً (القواعد المسبقة بالخلفية معطّلة).", tokens.STATUS_WARN)

    def calibrate_network_for_meeting(self) -> None:
        self.lifecycle_stepper.set_stage(
            "calibrating",
            "جاري معايرة مسار الاتصال وفحص استقرار البوابة وزمن الاستجابة قبل الاجتماع..."
        )
        self._set_feedback("جاري إجراء فحص وتجهيز ما قبل الاجتماع...", tokens.STATUS_INFO)
        self.preflight_requested.emit()
        self.refresh_policy_matrix()

    def retry_meeting_detection(self) -> None:
        self._set_feedback("جاري إعادة فحص عمليات المكالمات و ETW وقواعد ActiveStore...", tokens.STATUS_INFO)
        self.refresh_policy_matrix(fetch_activestore=True)
        if self.controller and hasattr(self.controller, "is_critical_meeting_active"):
            active = bool(self.controller.is_critical_meeting_active())
            if active:
                self._set_feedback("تم رصد اجتماع نشط وتحديث مصفوفة QoS من ActiveStore.", tokens.STATUS_OK)
            else:
                self._set_feedback("اكتمل الفحص: لا توجد مكالمة فيديو أو صوت نشطة حالياً — الدرع في وضع الاستعداد.", tokens.TEXT_SECONDARY)

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
            self.kill_switch_triggered.emit()
            self._set_feedback("جاري تنظيف جميع سياسات NetGuard QoS وإعادة التحقق من Windows ActiveStore...", tokens.STATUS_WARN)

            def _worker() -> None:
                ok, msg = (
                    self.platform.sweep_all_netguard_rules()
                    if (self.platform and hasattr(self.platform, "sweep_all_netguard_rules"))
                    else (True, "Swept")
                )
                # Mandatory post-cleanup ActiveStore readback verification
                remaining = []
                if self.platform and hasattr(self.platform, "get_netguard_qos_policies"):
                    try:
                        remaining = list(self.platform.get_netguard_qos_policies() or [])
                    except Exception:
                        remaining = []
                self._last_os_policies = remaining
                if ok and len(remaining) > 0:
                    ok = False
                    msg = f"تبقى {len(remaining)} سياسة في ActiveStore بعد التنظيف — يلزم صلاحيات مسؤول."
                elif ok:
                    msg = f"تم تنظيف كافة السياسات بنجاح (القراءة المرتدة: 0 قواعد متبقية في ActiveStore)."
                self.qos_policy_done.emit(ok, msg)

            threading.Thread(target=_worker, daemon=True, name="QosCleanupVerifyWorker").start()
        finally:
            self._in_kill_switch = False

    def _on_qos_done(self, ok: bool, msg: str) -> None:
        if msg:
            self._set_feedback(msg, tokens.STATUS_OK if ok else tokens.STATUS_BAD)
        if not ok and msg and self.isVisible():
            QMessageBox.warning(self, "QoS ActiveStore", msg)
        self.refresh_policy_matrix(fetch_activestore=False)

    def refresh_policy_matrix(self, *, fetch_activestore: bool = False) -> None:
        """Build real QoSPolicyMatrixWidget rows without blocking the Qt UI thread on PowerShell."""
        active_specs = []
        os_policies: List[Dict[str, Any]] = list(self._last_os_policies)
        active_apps: List[str] = []
        meeting_active = False

        if self.controller is not None:
            meeting_active = bool(getattr(self.controller, "meeting_active", False))
            active_specs = list(getattr(self.controller, "_active_qos_specs", []) or [])

        if fetch_activestore and not getattr(self, "_is_fetching_activestore", False):
            self._is_fetching_activestore = True

            def _fetch_bg() -> None:
                fetched_policies: List[Dict[str, Any]] = []
                try:
                    if self.controller is not None:
                        recon = self.controller.reconcile_active_policies()
                        if isinstance(recon, dict):
                            fetched_policies = list(recon.get("os_policies", []) or [])
                    if not fetched_policies and self.platform and hasattr(self.platform, "get_netguard_qos_policies"):
                        fetched_policies = list(self.platform.get_netguard_qos_policies() or [])
                except Exception:
                    fetched_policies = []
                finally:
                    self._last_os_policies = fetched_policies
                    self._is_fetching_activestore = False
                    self.qos_policy_done.emit(True, "")

            threading.Thread(target=_fetch_bg, daemon=True, name="ActiveStoreMatrixPoll").start()

        for sess in self.session_tracker.get_active_sessions():
            if getattr(sess, "category", None) and "conferencing" in str(sess.category).lower():
                active_apps.append(sess.process_name)
                meeting_active = True

        self.qos_matrix.refresh_from_controller(
            qos_config=self.qos_config,
            active_specs=active_specs,
            os_policies=os_policies,
            meeting_active=meeting_active,
            active_apps=active_apps,
            uplink_mbps=self.qos_config.default_uplink_mbps,
        )

    def update_live_state(
        self,
        *,
        profiles: List[Any],
        conferencing_active: bool = False,
        qos_policies: Optional[List[Dict[str, Any]]] = None,
        verified: bool = False,
        confirmed_count: int = 0,
        error_msg: str = "",
        rolled_back: bool = False,
        rollback_reason: str = "",
    ) -> None:
        """Synchronize Meeting Guard dashboard cards, lifecycle stepper, and ActiveStore matrix."""
        self._last_profiles = list(profiles or [])
        if qos_policies is not None:
            self._last_os_policies = list(qos_policies)
        self._rolled_back = rolled_back
        self._rollback_reason = rollback_reason

        self._update_throttle_label()

        # 1. Active media processes + ETW telemetry
        media_procs: List[str] = []
        udp_total_kbps = 0.0
        for p in self._last_profiles:
            cat = str(getattr(p, "category", ""))
            name = str(getattr(p, "process_name", ""))
            if "conferencing" in cat.lower() or MeetingAppRegistry.find_entry_for_process(name):
                media_procs.append(name)
            udp_total_kbps += float(getattr(p, "outbound_udp_kbps", 0.0) or 0.0)

        active_sessions = self.session_tracker.get_active_sessions()
        completed_sessions = self.session_tracker.get_completed_sessions()

        first_sess_name = (
            getattr(active_sessions[0], "app_title", None) or getattr(active_sessions[0], "app_name", None)
            if active_sessions
            else None
        )
        app_name = first_sess_name or (media_procs[0] if media_procs else "—")
        self._kpi_app[1].setText(tokens.bidi_isolate_mixed(str(app_name)))
        self._kpi_process[1].setText(
            tokens.bidi_isolate_mixed(", ".join(media_procs[:3]) if media_procs else "—")
        )
        if udp_total_kbps > 0:
            self._kpi_etw[1].setText(tokens.bidi_isolate(f"{udp_total_kbps:.1f} KB/s"))
        else:
            etw_status = "ETW غير نشط" if conferencing_active else "غير متاح (بانتظار مكالمة)"
            self._kpi_etw[1].setText(etw_status)

        # DNS Freeze status
        if conferencing_active:
            self._kpi_dns_freeze[1].setText("مجمّد لحماية المكالمة / Frozen (Meeting Safe)")
            self._kpi_dns_freeze[1].setStyleSheet(f"color: {tokens.STATUS_WARN}; border: none; background: transparent;")
        else:
            self._kpi_dns_freeze[1].setText("مسموح / Unlocked")
            self._kpi_dns_freeze[1].setStyleSheet(f"color: {tokens.STATUS_OK}; border: none; background: transparent;")

        # Rollback strip
        self.rollback_banner.setVisible(rolled_back)
        if rolled_back:
            self.lbl_rollback_msg.setText(
                tokens.bidi_isolate_mixed(rollback_reason or "تم التراجع التلقائي عن QoS لحماية استقرار المكالمة.")
            )

        # Call & ActiveStore badges
        if rolled_back:
            self.badge_call_state.set_status(tokens.SystemStatus.WARNING, tr("status.warning"))
            self.badge_qos_verify.set_status(tokens.SystemStatus.WARNING, "Rolled Back")
            self.lifecycle_stepper.set_stage("restored", rollback_reason or "Auto-rollback triggered")
        elif conferencing_active:
            self.badge_call_state.set_status(tokens.SystemStatus.ACTIVE, tr("status.active"))
            if verified and confirmed_count > 0:
                self.badge_qos_verify.set_status(
                    tokens.SystemStatus.HEALTHY,
                    tokens.bidi_isolate_mixed(f"ActiveStore: {confirmed_count}"),
                )
                self.lifecycle_stepper.set_stage("active", f"{confirmed_count} ActiveStore policies verified")
            elif self.qos_config.master_enabled:
                self.badge_qos_verify.set_status(tokens.SystemStatus.VERIFYING, tr("status.verifying"))
                self.lifecycle_stepper.set_stage("calibrating", error_msg or "Verifying Windows ActiveStore readback")
            else:
                self.badge_qos_verify.set_status(tokens.SystemStatus.WAITING, "QoS Disabled")
                self.lifecycle_stepper.set_stage("detecting", "Meeting detected (Master QoS disabled)")
        else:
            self.badge_call_state.set_status(tokens.SystemStatus.RUNNING, tr("status.running"))
            self.badge_qos_verify.set_status(tokens.SystemStatus.WAITING, "0 ActiveStore rules")
            stage = "restored" if completed_sessions else "idle"
            self.lifecycle_stepper.set_stage(stage)

        # Sessions list
        while self.sessions_box.count():
            it = self.sessions_box.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        if not active_sessions and not completed_sessions:
            lbl = QLabel(tr("dash.guard_idle_detail"))
            lbl.setFont(tokens.get_sans_font(12, 400))
            lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
            lbl.setWordWrap(True)
            self.sessions_box.addWidget(lbl)
        else:
            for s in active_sessions[:3]:
                self.sessions_box.addWidget(ActiveSessionCard(s, parent=self))
            for s in completed_sessions[:3]:
                self.sessions_box.addWidget(SessionReportCard(s, parent=self))

        self.refresh_policy_matrix()

    def _sync_content_width(self) -> None:
        vw = self.viewport().width()
        if vw > 0:
            self.content_holder.setFixedWidth(min(vw, tokens.MAX_CONTENT_WIDTH))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_content_width()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_content_width()
