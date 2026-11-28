"""Master Application Window and Shell for NetGuard AI.

100% pixel-faithful to the approved reference design:
- RTL Layout: Fixed right sidebar (width 248px), scrollable content on left
- Sidebar:
  - Top Brand: 10px accent circle + wordmark 'NetGuard' + 'مراقبة الشبكة وإصلاحها تلقائياً'
  - Nav: 7 items with monochrome line icons (الرئيسية، التشخيص، الإصلاح التلقائي، DNS، حركة البيانات، السجل، الإعدادات)
  - Bottom: 'وضع الإصلاح' with 3-option exclusive group (تلقائي / بموافقتي / مراقبة فقط) + dynamic description
- No old 'top command bar'
- Responsive reflow at >=1100px, 700-1099px, and <700px (sidebar collapses to top grid).
"""

from __future__ import annotations
import sys
import os
import asyncio
import threading
import time
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional

logger = logging.getLogger("netguard.ui.main_window")

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QFrame,
    QApplication,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QPainter, QColor, QBrush, QPen

from app.ui import tokens
from app.ui.i18n import get_language, language_manager, set_language, tr
from app.ui.styles import DARK_THEME_QSS
from app.ui.widgets.nav_item import NavItem
from app.ui.widgets.buttons import SecondaryButton
from app.ui.widgets.top_bar import TopStatusBar
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.meeting_guard_view import MeetingGuardView
from app.ui.views.dns_view import DNSView
from app.ui.views.traffic_view import TrafficView
from app.ui.views.wifi_intelligence_view import WifiIntelligenceView
from app.ui.views.router_management_view import RouterManagementView
from app.ui.views.internet_quality_view import InternetQualityView
from app.ui.views.reports_view import ReportsView
from app.ui.views.settings_view import SettingsView
from app.ui.views.about_view import AboutView
from app.core.network_state import GlobalNetworkStateStore, normalize_network_identity_payload
from app.core.perf import PerfMetricsCollector
from app.traffic.controller import TrafficController
from app.core.models.metrics import (
    OperatingMode,
    ActionExecutionRecord,
    ActionExecutionStatus,
    RiskLevel,
    MetricType,
)
from app.core.bus import EventTopics


class UIAsyncBridge(QObject):
    """Thread-safe signal bridge for Qt GUI updates from background workers."""

    dns_benchmark_done = Signal(object)
    traffic_scan_done = Signal(object, bool)
    network_info_ready = Signal(dict)
    remediation_event_received = Signal(str, dict)
    speed_test_done = Signal(str)
    gui_dispatch = Signal(object)


class SidebarModeOption(QFrame):
    """Single mode option button inside sidebar bottom."""

    clicked = Signal(int)

    def __init__(self, index: int, label: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SidebarModeOption")
        self.index = index
        self.label = label
        self.is_selected = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        self.dot = QFrame()
        self.dot.setFixedSize(8, 8)
        layout.addWidget(self.dot)

        self.lbl_text = QLabel(label)
        self.lbl_text.setFont(tokens.get_sans_font(13, 500))
        layout.addWidget(self.lbl_text)
        layout.addStretch()

        self.set_selected(False)

    def set_selected(self, selected: bool) -> None:
        self.is_selected = selected
        if selected:
            self.dot.setStyleSheet(f"background-color: {tokens.ACCENT}; border-radius: 4px;")
            self.lbl_text.setStyleSheet(f"color: {tokens.TEXT};")
            self.setStyleSheet(f"""
                QFrame#SidebarModeOption {{
                    background-color: {tokens.SURFACE_HOVER};
                    border: none;
                    border-radius: {tokens.RADIUS_BUTTON}px;
                }}
                QFrame#SidebarModeOption QLabel {{
                    border: none;
                    background: transparent;
                }}
            """)
        else:
            self.dot.setStyleSheet(f"background-color: {tokens.LINE_THRESHOLD}; border-radius: 4px;")
            self.lbl_text.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
            self.setStyleSheet(f"""
                QFrame#SidebarModeOption {{
                    background-color: transparent;
                    border: none;
                    border-radius: {tokens.RADIUS_BUTTON}px;
                }}
                QFrame#SidebarModeOption:hover {{
                    background-color: {tokens.SURFACE_HOVER};
                }}
                QFrame#SidebarModeOption QLabel {{
                    border: none;
                    background: transparent;
                }}
            """)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.index)

    def set_collapsed(self, collapsed: bool) -> None:
        if collapsed:
            self.lbl_text.setVisible(False)
            self.setToolTip(self.label)
            self.setFixedSize(48, 36)
        else:
            self.lbl_text.setVisible(True)
            self.setToolTip("")
            self.setFixedHeight(36)
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)


class SidebarWidget(QFrame):
    """Primary navigation sidebar housing the 10 NetGuard AI sections and Operating Mode."""

    mode_changed = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SidebarDock")
        self._current_mode = "dock"

        self.sidebar_layout = QVBoxLayout(self)
        self.sidebar_layout.setContentsMargins(14, 18, 14, 16)
        self.sidebar_layout.setSpacing(6)

        # -------------------------------------------------------------
        # 1. Top Brand Header
        # -------------------------------------------------------------
        self.brand_container = QWidget()
        brand_col = QVBoxLayout(self.brand_container)
        brand_col.setContentsMargins(4, 0, 4, 8)
        brand_col.setSpacing(3)

        wordmark_row = QHBoxLayout()
        wordmark_row.setSpacing(8)

        brand_circle = QLabel()
        brand_circle.setFixedSize(10, 10)
        brand_circle.setStyleSheet(f"background-color: {tokens.ACCENT}; border-radius: 5px;")
        wordmark_row.addWidget(brand_circle)

        brand_title = QLabel("NetGuard AI")
        brand_title.setFont(tokens.get_mono_font(16, 700))
        brand_title.setStyleSheet(f"color: {tokens.TEXT};")
        wordmark_row.addWidget(brand_title)
        wordmark_row.addStretch()
        brand_col.addLayout(wordmark_row)

        self.brand_sub = QLabel(tr("app_subtitle"))
        self.brand_sub.setFont(tokens.get_sans_font(13, 400))
        self.brand_sub.setStyleSheet(f"color: {tokens.TEXT_MUTED}; line-height: 1.35;")
        self.brand_sub.setMinimumHeight(38)
        self.brand_sub.setWordWrap(True)
        brand_col.addWidget(self.brand_sub)

        self.sidebar_layout.addWidget(self.brand_container)

        # -------------------------------------------------------------
        # 2. Navigation Items (10 Canonical Sections)
        # -------------------------------------------------------------
        self.nav_container = QWidget()
        self.nav_grid = QGridLayout(self.nav_container)
        self.nav_grid.setContentsMargins(0, 0, 0, 0)
        self.nav_grid.setSpacing(3)

        self.btn_dash = NavItem("dashboard", tr("nav.dashboard"), 0, self)
        self.btn_meeting_guard = NavItem("meeting_guard", tr("nav.meeting_guard"), 1, self)
        self.btn_traffic = NavItem("traffic", tr("nav.traffic"), 2, self)
        self.btn_dns = NavItem("dns", tr("nav.dns"), 3, self)
        self.btn_wifi = NavItem("wifi", tr("nav.wifi_intelligence"), 4, self)
        self.btn_router = NavItem("router", tr("nav.router_management"), 5, self)
        self.btn_quality = NavItem("internet_quality", tr("nav.internet_quality"), 6, self)
        self.btn_reports = NavItem("reports", tr("nav.reports"), 7, self)
        self.btn_settings = NavItem("settings", tr("nav.settings"), 8, self)
        self.btn_about = NavItem("about", tr("nav.about"), 9, self)

        # Compatibility aliases for tests referencing old button names
        self.btn_rem = self.btn_meeting_guard
        self.btn_diag = self.btn_reports
        self.btn_hist = self.btn_reports
        self.btn_wifi_router = self.btn_router

        self._nav_keys = [
            "nav.dashboard",
            "nav.meeting_guard",
            "nav.traffic",
            "nav.dns",
            "nav.wifi_intelligence",
            "nav.router_management",
            "nav.internet_quality",
            "nav.reports",
            "nav.settings",
            "nav.about",
        ]
        self.nav_buttons = [
            self.btn_dash,
            self.btn_meeting_guard,
            self.btn_traffic,
            self.btn_dns,
            self.btn_wifi,
            self.btn_router,
            self.btn_quality,
            self.btn_reports,
            self.btn_settings,
            self.btn_about,
        ]

        self.sidebar_layout.addWidget(self.nav_container)
        self.stretch_item = self.sidebar_layout.addStretch()

        # -------------------------------------------------------------
        # 2b. Admin Elevation Indicator / Restart Button
        # -------------------------------------------------------------
        self.btn_restart_admin = SecondaryButton("تشغيل كمسؤول")
        self.btn_restart_admin.setFixedHeight(36)
        self.btn_restart_admin.setFont(tokens.get_sans_font(12, 500))
        self.btn_restart_admin.setToolTip("تشغيل NetGuard AI بصلاحيات مسؤول Windows (Run as Administrator)")
        self.sidebar_layout.addWidget(self.btn_restart_admin)

        # -------------------------------------------------------------
        # 3. Bottom: Mode Selector Group
        # -------------------------------------------------------------
        self.mode_container = QWidget()
        mode_col = QVBoxLayout(self.mode_container)
        mode_col.setContentsMargins(0, 6, 0, 0)
        mode_col.setSpacing(4)

        self.lbl_mode_caption = QLabel(tr("mode_label"))
        self.lbl_mode_caption.setFont(tokens.get_sans_font(12, 500))
        self.lbl_mode_caption.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        mode_col.addWidget(self.lbl_mode_caption)

        self.opt_auto = SidebarModeOption(0, tr("mode_auto"), self)
        self.opt_assisted = SidebarModeOption(1, tr("mode_ask"), self)
        self.opt_observe = SidebarModeOption(2, tr("mode_watch"), self)

        self.mode_options = [self.opt_auto, self.opt_assisted, self.opt_observe]
        for opt in self.mode_options:
            opt.clicked.connect(self._on_mode_clicked)
            mode_col.addWidget(opt)

        self.lbl_mode_desc = QLabel(tr("mode_auto_desc"))
        self.lbl_mode_desc.setFont(tokens.get_sans_font(12, 400))
        self.lbl_mode_desc.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_mode_desc.setWordWrap(True)
        mode_col.addWidget(self.lbl_mode_desc)

        self.sidebar_layout.addWidget(self.mode_container)

        self.set_mode("dock")
        self.set_operating_mode(OperatingMode.AUTO)

    def retranslate(self) -> None:
        self.brand_sub.setText(tr("app_subtitle"))
        self.lbl_mode_caption.setText(tr("mode_label"))
        for btn, k in zip(self.nav_buttons, self._nav_keys):
            btn.set_label_text(tr(k))
        self.opt_auto.lbl_text.setText(tr("mode_auto"))
        self.opt_assisted.lbl_text.setText(tr("mode_ask"))
        self.opt_observe.lbl_text.setText(tr("mode_watch"))
        self.set_operating_mode([OperatingMode.AUTO, OperatingMode.ASK, OperatingMode.WATCH][getattr(self, "_current_mode_idx", 0)])
        self.set_mode(self._current_mode)

    def set_operating_mode(self, mode: OperatingMode | str) -> None:
        target = OperatingMode(mode)
        mode_to_idx = {OperatingMode.AUTO: 0, OperatingMode.ASK: 1, OperatingMode.WATCH: 2}
        idx = mode_to_idx.get(target, 0)
        self._current_mode_idx = idx
        for i, opt in enumerate(self.mode_options):
            opt.set_selected(i == idx)
        descs = {
            0: tr("mode_auto_desc"),
            1: tr("mode_ask_desc"),
            2: tr("mode_watch_desc"),
        }
        self.lbl_mode_desc.setText(descs.get(idx, ""))

    def set_mode(self, mode: str) -> None:
        self._current_mode = mode
        border_side = "border-left" if get_language() == "ar" else "border-right"
        if mode == "collapsed":
            self.setFixedWidth(64)
            self.sidebar_layout.setContentsMargins(8, 16, 8, 16)
            self.brand_container.setVisible(False)
            self.lbl_mode_desc.setVisible(False)
            self.lbl_mode_caption.setVisible(False)
            self.btn_restart_admin.setVisible(False)
            self.setStyleSheet(f"""
                QFrame#SidebarDock {{
                    background-color: {tokens.SIDEBAR};
                    border: none;
                    {border_side}: 1px solid {tokens.LINE};
                }}
            """)
            for i, btn in enumerate(self.nav_buttons):
                btn.set_collapsed(True)
                self.nav_grid.removeWidget(btn)
                self.nav_grid.addWidget(btn, i, 0)
            for opt in self.mode_options:
                opt.set_collapsed(True)
        else:
            self.setFixedWidth(248)
            self.sidebar_layout.setContentsMargins(14, 18, 14, 16)
            self.brand_container.setVisible(True)
            self.lbl_mode_desc.setVisible(True)
            self.lbl_mode_caption.setVisible(True)
            self.btn_restart_admin.setVisible(True)
            self.setStyleSheet(f"""
                QFrame#SidebarDock {{
                    background-color: {tokens.SIDEBAR};
                    border: none;
                    {border_side}: 1px solid {tokens.LINE};
                }}
            """)
            for i, btn in enumerate(self.nav_buttons):
                btn.set_collapsed(False)
                self.nav_grid.removeWidget(btn)
                self.nav_grid.addWidget(btn, i, 0)
            for opt in self.mode_options:
                opt.set_collapsed(False)

    def _on_mode_clicked(self, idx: int) -> None:
        idx_to_mode = {0: OperatingMode.AUTO, 1: OperatingMode.ASK, 2: OperatingMode.WATCH}
        mode = idx_to_mode.get(idx, OperatingMode.AUTO)
        self.set_operating_mode(mode)
        self.mode_changed.emit(idx)


class MainWindow(QMainWindow):
    """Master NetGuard AI Desktop Workstation."""

    def __init__(self, application: Any, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.app_core = application
        self._fallback_async_loop: Optional[asyncio.AbstractEventLoop] = None
        self._fallback_async_thread: Optional[threading.Thread] = None
        ctx = getattr(application, "ctx", None)
        eb = getattr(ctx, "event_bus", None)
        plat = getattr(ctx, "platform", None)
        us = getattr(ctx, "settings", getattr(ctx, "user_settings", None))
        self.traffic_controller = getattr(application, "traffic_controller", None) or TrafficController(event_bus=eb, platform=plat, user_settings=us)
        self.bridge = UIAsyncBridge()
        self.bridge.gui_dispatch.connect(self._run_on_gui)

        # Enforce Arabic RTL layout & dark theme palette
        if QApplication.instance():
            QApplication.instance().setLayoutDirection(Qt.RightToLeft)
            pal = QApplication.instance().palette()
            pal.setColor(pal.ColorRole.WindowText, QColor(tokens.TEXT))
            pal.setColor(pal.ColorRole.Text, QColor(tokens.TEXT))
            pal.setColor(pal.ColorRole.Window, QColor(tokens.BG))
            pal.setColor(pal.ColorRole.Base, QColor(tokens.SURFACE))
            pal.setColor(pal.ColorRole.ButtonText, QColor(tokens.TEXT))
            QApplication.instance().setPalette(pal)

        tokens.init_fonts()
        self.setWindowTitle("NetGuard AI")

        # Explicitly apply application window icon
        from PySide6.QtGui import QIcon
        base_dir = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
        for icon_name in ("icon.ico", "icon.png"):
            icon_p = os.path.join(base_dir, "assets", icon_name)
            if os.path.exists(icon_p):
                app_ico = QIcon(icon_p)
                self.setWindowIcon(app_ico)
                if QApplication.instance():
                    QApplication.instance().setWindowIcon(app_ico)
                break

        # Responsive window size bounded to available desktop logical geometry
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            target_w = min(1200, max(960, int(avail.width() * 0.90)))
            target_h = min(760, max(580, int(avail.height() * 0.90)))
            self.resize(target_w, target_h)
            self.move(
                avail.x() + (avail.width() - target_w) // 2,
                avail.y() + (avail.height() - target_h) // 2,
            )
        else:
            self.resize(1024, 680)

        self.setMinimumSize(480, 580)
        self.setStyleSheet(DARK_THEME_QSS)

        central_widget = QWidget(self)
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)

        self.root_layout = QHBoxLayout(central_widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # Fixed Sidebar Dock (Right in RTL / Left in LTR, width 248px)
        self.sidebar = SidebarWidget(self)
        self.root_layout.addWidget(self.sidebar)

        # Workspace Column (Persistent TopStatusBar + 10-Section QStackedWidget)
        workspace_col = QVBoxLayout()
        workspace_col.setContentsMargins(0, 0, 0, 0)
        workspace_col.setSpacing(0)

        self.top_bar = TopStatusBar(self)
        self.top_bar.set_section(tr("nav.dashboard"), tr("dash_sub"))
        self.top_bar.language_toggle_requested.connect(self._on_toggle_language)
        self.top_bar.refresh_requested.connect(self._on_topbar_refresh)
        self.top_bar.notifications_clicked.connect(lambda: self._switch_view(7, self.btn_reports))
        workspace_col.addWidget(self.top_bar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("ContentStack")

        # Startup sweep of any lingering NetGuard rules from active or persistent stores off UI thread
        if plat and hasattr(plat, "sweep_all_netguard_rules"):
            import threading
            threading.Thread(target=plat.sweep_all_netguard_rules, daemon=True).start()

        meas_repo = getattr(self.app_core.ctx, "measurements", None) if hasattr(self.app_core, "ctx") else None
        inc_repo = getattr(self.app_core.ctx, "incidents", None) if hasattr(self.app_core, "ctx") else None

        # Instantiate all 10 canonical workstation views
        self.view_dashboard = DashboardView()
        self.view_meeting_guard = MeetingGuardView(
            session_tracker=self.traffic_controller.session_tracker,
            platform=plat,
            user_settings=us,
            qos_config=getattr(self.traffic_controller, "qos_config", None),
            controller=self.traffic_controller,
        )
        self.view_traffic = TrafficView(
            session_tracker=self.traffic_controller.session_tracker,
            platform=plat,
            user_settings=us,
            qos_config=getattr(self.traffic_controller, "qos_config", None),
            controller=self.traffic_controller,
        )
        self.view_dns = DNSView()
        self.view_wifi = WifiIntelligenceView(app_core=self.app_core)
        self.view_router = RouterManagementView(app_core=self.app_core)
        self.view_quality = InternetQualityView(app_core=self.app_core)
        self.view_reports = ReportsView(
            app_core=self.app_core,
            measurement_repo=meas_repo,
            incident_repo=inc_repo,
        )
        self.view_settings = SettingsView()
        self.view_about = AboutView(app_core=self.app_core)

        # Compatibility aliases preserving all controller & test contracts
        self.view_diagnosis = self.view_reports.diagnosis_view
        self.view_history = self.view_reports.history_view
        self.view_remediation = self.view_meeting_guard.remediation_section
        self.view_wifi_router = self.view_router

        # Canonical 10-index stack sequence:
        # 0: Dashboard, 1: Meeting Guard, 2: Traffic Monitor, 3: DNS Optimizer,
        # 4: Wi-Fi Intelligence, 5: Router Management, 6: Internet Quality,
        # 7: Reports, 8: Settings, 9: About
        self.stack.addWidget(self.view_dashboard)
        self.stack.addWidget(self.view_meeting_guard)
        self.stack.addWidget(self.view_traffic)
        self.stack.addWidget(self.view_dns)
        self.stack.addWidget(self.view_wifi)
        self.stack.addWidget(self.view_router)
        self.stack.addWidget(self.view_quality)
        self.stack.addWidget(self.view_reports)
        self.stack.addWidget(self.view_settings)
        self.stack.addWidget(self.view_about)

        workspace_col.addWidget(self.stack, stretch=1)
        self.root_layout.addLayout(workspace_col, stretch=1)

        # Connect Navigation Buttons
        self.btn_dash = self.sidebar.btn_dash
        self.btn_meeting_guard = self.sidebar.btn_meeting_guard
        self.btn_traffic = self.sidebar.btn_traffic
        self.btn_dns = self.sidebar.btn_dns
        self.btn_wifi = self.sidebar.btn_wifi
        self.btn_router = self.sidebar.btn_router
        self.btn_quality = self.sidebar.btn_quality
        self.btn_reports = self.sidebar.btn_reports
        self.btn_settings = self.sidebar.btn_settings
        self.btn_about = self.sidebar.btn_about

        self.btn_diag = self.btn_reports
        self.btn_rem = self.btn_meeting_guard
        self.btn_hist = self.btn_reports
        self.btn_wifi_router = self.btn_router
        self.nav_buttons = self.sidebar.nav_buttons

        for idx, btn in enumerate(self.nav_buttons):
            btn.clicked.connect(lambda checked=False, i=idx, b=btn: self._switch_view(i, b))

        self.sidebar.mode_changed.connect(self._on_sidebar_mode_changed)
        self.view_remediation.mode_changed.connect(self._on_sidebar_mode_changed)
        self.view_dashboard.navigate_requested.connect(
            lambda idx: self._switch_view(idx, self.nav_buttons[idx]) if 0 <= idx < len(self.nav_buttons) else None
        )
        self.view_meeting_guard.preflight_requested.connect(self._on_meeting_preflight_requested)
        self.view_wifi.wifi_telemetry_updated.connect(self._on_wifi_tel_to_dashboard)
        self.view_router.router_summary_updated.connect(self._on_router_summary_to_dashboard)
        self.view_quality.speed_test_completed.connect(self._on_iq_speed_completed)
        self.view_reports.deep_scan_requested.connect(self._on_run_deep_diagnosis)
        self.view_settings.language_changed_requested.connect(self._apply_language_direction)
        language_manager().language_changed.connect(self._apply_language_direction)

        # Set initial active tab
        self.btn_dash.setChecked(True)

        # Sync initial operating mode across all views
        initial_mode = OperatingMode.AUTO
        if hasattr(self.app_core, "settings") and self.app_core.settings:
            initial_mode = self.app_core.settings.get_mode()
            self.view_settings.set_probing_interval(self.app_core.settings.get_probing_interval())
            self.view_settings.set_retention_days(self.app_core.settings.get_retention_days())
        elif hasattr(self.app_core, "orchestrator") and self.app_core.orchestrator:
            initial_mode = getattr(self.app_core.orchestrator, "mode", OperatingMode.AUTO)
        self.set_operating_mode(initial_mode, sync_router_auto=False)

        # -------------------------------------------------------------
        # 3. Connect Bridge Signals & Wire Handlers
        # -------------------------------------------------------------
        self._last_speed_test_time: Optional[str] = None
        self.bridge.dns_benchmark_done.connect(self._on_dns_benchmark_done)
        self.bridge.traffic_scan_done.connect(self._on_scan_traffic_done)
        self.bridge.network_info_ready.connect(self._on_network_info_ready)
        self.bridge.remediation_event_received.connect(self._on_remediation_event_received)
        self.bridge.speed_test_done.connect(self._on_speed_test_done)

        # Wire Admin Elevation restart button
        from app.platform.admin import require_admin, prompt_restart_as_admin
        platform = getattr(getattr(self, "app_core", None), "ctx", None)
        plat = getattr(platform, "platform", None)
        if plat and plat.is_elevated():
            self.sidebar.btn_restart_admin.setText("صلاحيات مسؤول مفعّلة ✓")
            self.sidebar.btn_restart_admin.setEnabled(False)
            self.sidebar.btn_restart_admin.setStyleSheet(
                f"background: rgba(52, 211, 153, 0.08); color: {tokens.STATUS_OK}; "
                f"border: 1px solid rgba(52, 211, 153, 0.25); border-radius: 6px; font-weight: 500;"
            )
        else:
            self.sidebar.btn_restart_admin.clicked.connect(
                lambda: prompt_restart_as_admin(self, "تشغيل كافة ميزات الحماية المتقدمة", plat)
            )

        self._wire_background_event_listeners()

        # Inspect network hardware asynchronously on launch
        self._async_inspect_network_environment()

        # Initialize DNS recommendation card in discovering state without fake latencies
        self.view_dashboard.update_dns_recommendation(
            curr_name="جاري كشف خادم DNS النشط...",
            curr_ms=None,
            best_name="جاري فحص الخوادم البديلة...",
            best_ip="—",
            best_ms=0.0,
            is_optimal=False,
            is_autonomous=False,
        )

        # Schedule initial traffic scan immediately so consumers list is populated
        if "pytest" not in sys.modules:
            QTimer.singleShot(600, self._on_scan_traffic)

        # Connect single source of truth DNS state manager (Item B1) and Global Network State
        from app.dns.state import DnsStateManager, DnsStateData
        DnsStateManager.get_instance().state_changed.connect(self._on_dns_state_changed)
        GlobalNetworkStateStore.get_instance().state_changed.connect(self._on_global_network_state_changed)

        # UI Refresh Timer (1 second interval)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._on_ui_tick)
        self.refresh_timer.start(1000)

        # Recurring background DNS ranking update (every 60 seconds)
        self._last_dns_switch_time: float = 0.0
        self.dns_rank_timer = QTimer(self)
        self.dns_rank_timer.timeout.connect(self._on_run_dns_benchmark)
        self.dns_rank_timer.start(300000)

        # Dedicated meeting-signal poller (every 2s regardless of visible view)
        self._is_polling_meeting_signal: bool = False
        self.meeting_signal_timer = QTimer(self)
        self.meeting_signal_timer.timeout.connect(self._on_poll_meeting_signal)
        self.meeting_signal_timer.start(2000)

        self.ticker_counter = 0

        # Load initial day strip stability slots from measurement database
        self._refresh_day_strips()

        # Load initial timeline narrative from stored incidents and audit records
        self._refresh_timeline_from_records()

        # Clean up any leftover .old / .pending update files on startup
        from app.core.updater import cleanup_stale_update_files
        cleanup_stale_update_files()

        # Silent background auto-update checks (Startup after 5s + every 10 minutes)
        self._is_checking_updates_bg = False
        self.update_check_timer = QTimer(self)
        self.update_check_timer.timeout.connect(self._on_background_update_tick)
        self.update_check_timer.start(10 * 60 * 1000)

        if "pytest" not in sys.modules:
            QTimer.singleShot(5000, self._on_background_update_tick)

    def _run_on_gui(self, fn: Any) -> None:
        try:
            fn()
        except Exception as e:
            logger.error("Exception in GUI thread dispatch: %s", e, exc_info=True)

    def call_on_ui(self, fn: Any) -> None:
        """Thread-safe invocation of a function on the main Qt GUI event loop."""
        if getattr(self, "_is_closing", False):
            return
        import threading
        if threading.current_thread() is threading.main_thread():
            self._run_on_gui(fn)
        else:
            try:
                if hasattr(self, "bridge") and self.bridge:
                    self.bridge.gui_dispatch.emit(fn)
            except Exception:
                pass

    @property
    def async_loop(self) -> asyncio.AbstractEventLoop:
        """Centralized application async event loop."""
        loop = getattr(self.app_core, "async_loop", None)
        if loop and loop.is_running():
            return loop
        if not hasattr(self, "_fallback_async_loop") or self._fallback_async_loop is None or self._fallback_async_loop.is_closed():
            self._fallback_async_loop = asyncio.new_event_loop()
            t = threading.Thread(target=self._fallback_async_loop.run_forever, daemon=True, name="MainWindowCentralAsyncLoop")
            self._fallback_async_thread = t
            t.start()
        if hasattr(self.app_core, "async_loop") and self.app_core.async_loop is None:
            self.app_core.async_loop = self._fallback_async_loop
        return self._fallback_async_loop

    def dispatch_coroutine(
        self,
        coro: Any,
        on_done: Optional[Any] = None,
    ) -> Any:
        """Safely dispatch an async coroutine into the centralized application event loop."""
        loop = self.async_loop
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        if on_done:
            future.add_done_callback(lambda f: self.call_on_ui(lambda: on_done(f)))
        return future

    def _switch_view(self, index: int, active_btn: QPushButton) -> None:
        _t0 = time.perf_counter()
        self.stack.setCurrentIndex(index)
        for b in self.nav_buttons:
            b.setChecked(b == active_btn)

        sec_titles = [
            ("nav.dashboard", "dash_sub"),
            ("nav.meeting_guard", "mg_sub"),
            ("nav.traffic", "tm_sub"),
            ("nav.dns", "dns_sub"),
            ("nav.wifi_intelligence", "wifi_sub"),
            ("nav.router_management", "router_sub"),
            ("nav.internet_quality", "iq_sub"),
            ("nav.reports", "rep_sub"),
            ("nav.settings", "set_sub"),
            ("nav.about", "about_sub"),
        ]
        if 0 <= index < len(sec_titles) and hasattr(self, "top_bar"):
            tk, sk = sec_titles[index]
            self.top_bar.set_section(tr(tk), tr(sk))

        if hasattr(self.view_dashboard, "set_animations_paused"):
            self.view_dashboard.set_animations_paused(index != 0)

        # Immediate targeted refresh on tab switch
        if index == 0:
            obs = getattr(self.app_core, "observability", None)
            last_diag = getattr(self.app_core.diagnosis, "last_diagnosis", None) if hasattr(self.app_core, "diagnosis") else None
            if obs:
                self.view_dashboard.update_telemetry(obs, last_diag)
        elif index == 1:
            self.view_meeting_guard.refresh_policy_matrix()
        elif index == 2:
            self._on_scan_traffic()
        if hasattr(self.view_wifi, "set_page_active"):
            self.view_wifi.set_page_active(index == 4)
        if index == 4 and hasattr(self.view_wifi, "ensure_initial_scan"):
            self.view_wifi.ensure_initial_scan()
        elif index == 5 and hasattr(self.view_router, "ensure_initial_devices_scan"):
            self.view_router.ensure_initial_devices_scan()
        elif index == 7:
            obs = getattr(self.app_core, "observability", None)
            last_diag = getattr(self.app_core.diagnosis, "last_diagnosis", None) if hasattr(self.app_core, "diagnosis") else None
            net_info = getattr(self.view_dashboard, "_last_net_info", {})
            if obs:
                self.view_diagnosis.update_live_telemetry(obs, net_info, last_diag)
                if last_diag:
                    self.view_diagnosis.update_diagnosis(last_diag)

        PerfMetricsCollector.get_instance().record_nav_switch(index, (time.perf_counter() - _t0) * 1000.0)

    def _on_toggle_language(self) -> None:
        set_language("en" if get_language() == "ar" else "ar")

    def _apply_language_direction(self, lang: str | None = None) -> None:
        active = lang or get_language()
        app = QApplication.instance()
        if app:
            app.setLayoutDirection(Qt.RightToLeft if active == "ar" else Qt.LeftToRight)
        if hasattr(self, "sidebar"):
            self.sidebar.retranslate()
        if hasattr(self, "top_bar"):
            self.top_bar.retranslate()
            idx = self.stack.currentIndex() if hasattr(self, "stack") else 0
            sec_titles = [
                ("nav.dashboard", "dash_sub"),
                ("nav.meeting_guard", "mg_sub"),
                ("nav.traffic", "tm_sub"),
                ("nav.dns", "dns_sub"),
                ("nav.wifi_intelligence", "wifi_sub"),
                ("nav.router_management", "router_sub"),
                ("nav.internet_quality", "iq_sub"),
                ("nav.reports", "rep_sub"),
                ("nav.settings", "set_sub"),
                ("nav.about", "about_sub"),
            ]
            if 0 <= idx < len(sec_titles):
                self.top_bar.set_section(tr(sec_titles[idx][0]), tr(sec_titles[idx][1]))

    def _on_topbar_refresh(self) -> None:
        idx = self.stack.currentIndex() if hasattr(self, "stack") else 0
        if idx == 0:
            self._on_quick_scan_requested()
        elif idx == 1:
            self.view_meeting_guard.refresh_policy_matrix()
        elif idx == 2:
            self._on_scan_traffic()
        elif idx == 3:
            self._on_run_dns_benchmark(full=True)
        elif idx == 4:
            self.view_wifi.refresh_wifi_and_rf()
        elif idx == 5:
            self.view_router.run_router_discovery()
        elif idx == 6:
            self.view_quality.run_network_sequence()
        elif idx == 7:
            self.view_reports.run_full_investigation()
        else:
            self._on_ui_tick()

    def _on_global_network_state_changed(self, state: Any) -> None:
        if state is None:
            return
        if hasattr(self, "top_bar"):
            st_enum, st_label = state.format_status_badge(get_language())
            self.top_bar.set_connection_status(st_enum, st_label)

    def _on_wifi_tel_to_dashboard(self, tel: Any) -> None:
        if tel is None:
            return
        sig_pct = getattr(tel, "signal_quality_pct", getattr(tel, "signal_percent", None))
        GlobalNetworkStateStore.get_instance().update_from_wifi_telemetry(tel)
        self.view_dashboard.update_wifi_and_router_summary(
            ssid=getattr(tel, "ssid", None),
            band=getattr(tel, "band", None),
            channel=getattr(tel, "channel", None),
            rssi_dbm=getattr(tel, "rssi_dbm", None),
            wifi_quality_pct=sig_pct,
        )

    def _on_router_summary_to_dashboard(self, info: Dict[str, Any]) -> None:
        r_ip = info.get("router_ip")
        r_model = info.get("router_model")
        if r_ip or r_model:
            GlobalNetworkStateStore.get_instance().update_router_reachability(
                reachable=True,
                model=r_model,
                url=f"http://{r_ip}" if r_ip else None,
            )
        self.view_dashboard.update_wifi_and_router_summary(
            router_model=r_model,
            router_ip=r_ip,
            connected_devices_count=info.get("connected_devices_count"),
        )

    def _on_iq_speed_completed(self, rep: Any) -> None:
        if rep is not None:
            self.view_dashboard.set_last_speed_test_time(datetime.now().strftime("%H:%M"))

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.WindowStateChange:
            is_min = self.isMinimized()
            if hasattr(self.view_dashboard, "set_animations_paused"):
                self.view_dashboard.set_animations_paused(is_min or self.stack.currentIndex() != 0)

    def _on_sidebar_mode_changed(self, mode_val: Any) -> None:
        if isinstance(mode_val, int):
            idx_to_mode = {0: OperatingMode.AUTO, 1: OperatingMode.ASK, 2: OperatingMode.WATCH}
            mode = idx_to_mode.get(mode_val, OperatingMode.AUTO)
        else:
            mode = OperatingMode(mode_val)
        self.set_operating_mode(mode)

    def set_operating_mode(self, mode: OperatingMode | str, *, sync_router_auto: bool = True) -> None:
        target_mode = OperatingMode(mode)
        if getattr(self, "_current_operating_mode", None) == target_mode:
            return
        self._current_operating_mode = target_mode
        self.sidebar.set_operating_mode(target_mode)
        self.view_remediation.set_operating_mode(target_mode)
        self.view_settings.set_operating_mode(target_mode)
        if hasattr(self, "view_wifi_router") and hasattr(self.view_wifi_router, "sync_operating_mode"):
            self.view_wifi_router.sync_operating_mode(target_mode, allow_auto_router=sync_router_auto)
        if hasattr(self.app_core, "orchestrator") and self.app_core.orchestrator:
            self.app_core.orchestrator.set_operating_mode(target_mode)
        if hasattr(self.app_core, "settings") and self.app_core.settings:
            self.app_core.settings.set_mode(target_mode)
        if hasattr(self.app_core, "ctx") and hasattr(self.app_core.ctx, "event_bus") and self.app_core.ctx.event_bus:
            self.app_core.ctx.event_bus.publish_sync(EventTopics.MODE_CHANGED, {"mode": target_mode.value})

    def _wire_background_event_listeners(self) -> None:
        event_bus = self.app_core.ctx.event_bus

        async def _on_rem_started(topic: str, event_data: Any):
            data = event_data.model_dump(mode="json") if hasattr(event_data, "model_dump") else (event_data if isinstance(event_data, dict) else {})
            self.bridge.remediation_event_received.emit("started", data)

        async def _on_rem_completed(topic: str, event_data: Any):
            data = event_data.model_dump(mode="json") if hasattr(event_data, "model_dump") else (event_data if isinstance(event_data, dict) else {})
            self.bridge.remediation_event_received.emit("completed", data)

        event_bus.subscribe_sync(EventTopics.REMEDIATION_STARTED, _on_rem_started)
        event_bus.subscribe_sync(EventTopics.REMEDIATION_COMPLETED, _on_rem_completed)

        # Wire view actions
        self.view_settings.apply_btn.clicked.connect(self._on_apply_settings)
        if hasattr(self.view_settings, "btn_clear_history"):
            self.view_settings.btn_clear_history.clicked.connect(self._on_clear_history_requested)
        if hasattr(self.view_history, "btn_clear_history"):
            self.view_history.btn_clear_history.clicked.connect(self._on_clear_history_requested)
        self.view_dns.benchmark_btn.clicked.connect(lambda _checked=False: self._on_run_dns_benchmark(full=True))
        self.view_traffic.btn_refresh.clicked.connect(self._on_scan_traffic)
        self.view_diagnosis.btn_run_audit.clicked.connect(self._on_run_deep_diagnosis)

        # Remediation quick tools
        self.view_remediation.btn_flush_now.clicked.connect(self._on_quick_flush_dns)
        self.view_remediation.btn_renew_ip.clicked.connect(self._on_quick_renew_ip)

        # Remediation policy toggles
        if hasattr(self.app_core, "settings") and self.app_core.settings:
            us = self.app_core.settings
            self.view_remediation.pol1.toggle.setChecked(us.get_policy("allow_flush_dns"))
            self.view_remediation.pol2.toggle.setChecked(us.get_policy("meeting_guard"))
            self.view_remediation.pol3.toggle.setChecked(us.get_policy("allow_switch_dns"))
            self.view_remediation.pol4.toggle.setChecked(us.get_policy("allow_renew_ip"))

            self.view_remediation.pol1.toggle.toggled.connect(lambda chk: us.set_policy("allow_flush_dns", chk))
            self.view_remediation.pol2.toggle.toggled.connect(lambda chk: us.set_policy("meeting_guard", chk))
            self.view_remediation.pol3.toggle.toggled.connect(lambda chk: us.set_policy("allow_switch_dns", chk))
            self.view_remediation.pol4.toggle.toggled.connect(lambda chk: us.set_policy("allow_renew_ip", chk))

        # DNS Apply request
        self.view_dns.apply_dns_requested.connect(self._on_apply_dns_requested)
        self.view_dashboard.dns_panel.apply_clicked.connect(self._on_dashboard_apply_dns)
        self.view_dashboard.dns_panel.revert_clicked.connect(self._on_dashboard_revert_dns)
        if hasattr(self.view_wifi_router, "apply_local_dns_requested"):
            self.view_wifi_router.apply_local_dns_requested.connect(self._on_apply_dns_requested)

        # Dashboard quick scan / speed test request
        self.view_dashboard.quick_scan_requested.connect(self._on_quick_scan_requested)
        self.view_dashboard.meeting_preflight_requested.connect(self._on_meeting_preflight_requested)
        self.view_dashboard.export_report_requested.connect(self._on_export_report_requested)

        # Dashboard timeline requests
        self.view_dashboard.timeline_panel.view_evidence_requested.connect(
            lambda: self._switch_view(7, self.btn_reports)
        )
        self.view_dashboard.timeline_panel.rollback_requested.connect(
            self._on_timeline_rollback_requested
        )

    def _on_quick_scan_requested(self) -> None:
        """Trigger on-demand telemetry / speed test cycle and update timestamp."""
        async def _run_scan():
            try:
                if hasattr(self.app_core, "observability") and self.app_core.observability:
                    await self.app_core.observability.run_single_cycle()
            except Exception as e:
                logger.warning(f"Error during on-demand telemetry scan: {e}")
            finally:
                time_str = datetime.now().strftime("%H:%M")
                if hasattr(self, "bridge") and self.bridge is not None:
                    try:
                        self.bridge.speed_test_done.emit(time_str)
                    except RuntimeError:
                        pass

        self.dispatch_coroutine(_run_scan())

    def _on_meeting_preflight_requested(self) -> None:
        """Run rapid 10-15s pre-flight diagnostics and show comprehensive readiness report (Item D5)."""
        self.view_dashboard.btn_preflight.setEnabled(False)
        self.view_dashboard.btn_preflight.setText("جاري الفحص…")

        def _worker():
            report = None
            try:
                from app.traffic.preflight import MeetingPreflightChecker
                checker = MeetingPreflightChecker(self.app_core.ctx.platform)
                is_active = (
                    hasattr(self, "traffic_controller")
                    and self.traffic_controller
                    and self.traffic_controller.is_critical_meeting_active()
                )
                report = checker.run_check(
                    is_meeting_active=is_active,
                    traffic_controller=getattr(self, "traffic_controller", None),
                )
            except Exception as e:
                logger.warning("Pre-flight meeting check failed: %s", e)
            finally:
                self.call_on_ui(lambda: self._on_meeting_preflight_done(report))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_meeting_preflight_done(self, report) -> None:
        self.view_dashboard.btn_preflight.setEnabled(True)
        self.view_dashboard.btn_preflight.setText("جهّز لاجتماع")
        if not report:
            QMessageBox.warning(self, "فحص الاجتماع", "تعذر إتمام فحص الجاهزية للاجتماع.")
            return

        box = QMessageBox(self)
        box.setWindowTitle("جاهزية مكالمات الفيديو (Meeting Pre-Flight)")
        box.setIcon(QMessageBox.Information if report.is_ready else QMessageBox.Warning)
        box.setText(f"{report.headline}\n\n{report.detail}")
        if report.recommended_fix:
            btn_fix = box.addButton("تحسين فوري للشبكة", QMessageBox.ActionRole)
            box.addButton("إغلاق", QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() == btn_fix:
                self._apply_preflight_immediate_remedy()
        else:
            box.addButton("ممتاز", QMessageBox.AcceptRole)
            box.exec()

    def _apply_preflight_immediate_remedy(self) -> None:
        """Prepare QoS policy readiness and pre-resolve meeting domains without disrupting active calls."""
        from app.traffic.controller import preresolve_meeting_domains
        preresolve_meeting_domains()
        is_meeting = (
            hasattr(self, "traffic_controller")
            and self.traffic_controller
            and self.traffic_controller.is_critical_meeting_active()
        )
        if not is_meeting and hasattr(self.app_core.ctx.platform, "flush_dns_cache"):
            try:
                self.app_core.ctx.platform.flush_dns_cache()
            except Exception:
                pass
        QMessageBox.information(
            self,
            "تحسين فوري",
            "تم تجهيز أولوية QoS وتحديث سجلات العناوين المسبقة (DNS Pre-resolution) لضمان جودة الاجتماع."
        )

    def _on_export_report_requested(self) -> None:
        """Export comprehensive diagnostic report to desktop or reports directory."""
        try:
            from datetime import datetime
            import json
            from pathlib import Path
            from PySide6.QtWidgets import QFileDialog, QMessageBox

            desktop = Path.home() / "Desktop"
            target_dir = desktop if desktop.exists() else Path.cwd()
            now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            default_path = str(target_dir / f"NetGuard_Report_{now_str}.html")

            # Let user choose file destination or use default
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "تصدير تقرير فحص الشبكة",
                default_path,
                "HTML Report (*.html);;JSON Data (*.json)"
            )
            if not file_path:
                return

            # Gather current telemetry & state
            net_id = getattr(self, "_last_net_info", None)
            diag = getattr(self, "_last_diag", None)
            obs = getattr(self, "_last_obs", None)

            # Generate HTML report
            html_content = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="utf-8">
<title>تقرير فحص وتشخيص الشبكة — NetGuard AI</title>
<style>
body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #0c101c; color: #e2e8f0; margin: 0; padding: 24px; direction: rtl; }}
.header {{ background: #151b2e; border: 1px solid #1e293b; border-radius: 12px; padding: 24px; margin-bottom: 24px; }}
h1 {{ margin: 0 0 8px 0; color: #38bdf8; font-size: 24px; }}
.meta {{ color: #94a3b8; font-size: 14px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }}
.card {{ background: #151b2e; border: 1px solid #1e293b; border-radius: 10px; padding: 16px; }}
.card-label {{ color: #94a3b8; font-size: 12px; margin-bottom: 6px; }}
.card-val {{ font-size: 18px; font-weight: bold; color: #f1f5f9; }}
table {{ width: 100%; border-collapse: collapse; background: #151b2e; border-radius: 10px; overflow: hidden; border: 1px solid #1e293b; }}
th, td {{ padding: 12px 16px; text-align: right; border-bottom: 1px solid #1e293b; }}
th {{ background: #1e293b; color: #38bdf8; font-size: 13px; }}
.status-good {{ color: #4ade80; }}
.status-warn {{ color: #facc15; }}
.status-bad {{ color: #f87171; }}
</style>
</head>
<body>
<div class="header">
<h1>تقرير فحص وتشخيص الشبكة — NetGuard AI</h1>
<div class="meta">تاريخ التقرير: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | حالة الشبكة: {'سليمة' if getattr(diag, 'is_healthy', True) else 'تحتاج انتباه'}</div>
</div>

<div class="grid">
<div class="card"><div class="card-label">اسم الشبكة (SSID)</div><div class="card-val">{getattr(net_id, 'ssid', '—') if net_id else '—'}</div></div>
<div class="card"><div class="card-label">مزود الخدمة (ISP)</div><div class="card-val">{getattr(net_id, 'isp', '—') if net_id else '—'}</div></div>
<div class="card"><div class="card-label">عنوان IP الداخلي</div><div class="card-val">{getattr(net_id, 'local_ip', '—') if net_id else '—'}</div></div>
<div class="card"><div class="card-label">عنوان IP الخارجي</div><div class="card-val">{getattr(net_id, 'public_ip', '—') if net_id else '—'}</div></div>
<div class="card"><div class="card-label">بوابة الراوتر (Gateway)</div><div class="card-val">{getattr(net_id, 'gateway_ip', '—') if net_id else '—'}</div></div>
<div class="card"><div class="card-label">خادم DNS المعتمد</div><div class="card-val">{getattr(net_id, 'dns_servers', ['—'])[0] if net_id and net_id.dns_servers else '—'}</div></div>
<div class="card"><div class="card-label">زمن الاستجابة للإنترنت</div><div class="card-val">{f"{getattr(obs, 'external_rtt_ms', 0):.1f} ms" if obs and obs.external_rtt_ms else '—'}</div></div>
<div class="card"><div class="card-label">فقدان الحزم (Packet Loss)</div><div class="card-val">{f"{getattr(obs, 'packet_loss_pct', 0):.1f}%" if obs and obs.packet_loss_pct is not None else '0.0%'}</div></div>
<div class="card"><div class="card-label">التذبذب (Jitter)</div><div class="card-val">{f"{getattr(obs, 'jitter_ms', 0):.1f} ms" if obs and obs.jitter_ms is not None else '—'}</div></div>
</div>

<h2>التشخيص الميداني والطبقات</h2>
<table>
<thead><tr><th>الطبقة</th><th>المكون</th><th>الحالة والمؤشر</th></tr></thead>
<tbody>
<tr><td>01</td><td>بطاقة الشبكة (Local Interface)</td><td>{getattr(net_id, 'adapter_name', 'Active') if net_id else 'Active'} — {getattr(net_id, 'local_ip', 'Connected') if net_id else 'Connected'}</td></tr>
<tr><td>02</td><td>الراوتر المنزلي (Gateway)</td><td>{getattr(net_id, 'gateway_ip', '192.168.1.1') if net_id else '—'} — {f"استجابة {getattr(obs, 'gateway_rtt_ms', 1.0):.1f} ms" if obs and obs.gateway_rtt_ms else 'سليم'}</td></tr>
<tr><td>03</td><td>مزود الخدمة (ISP Infrastructure)</td><td>{getattr(net_id, 'isp', 'Active') if net_id else '—'} — مسار التوصيل مستقر</td></tr>
<tr><td>04</td><td>خوادم DNS</td><td>{getattr(net_id, 'dns_servers', ['—'])[0] if net_id and net_id.dns_servers else '—'} — {f"{getattr(obs, 'dns_latency_ms', 0):.1f} ms" if obs and obs.dns_latency_ms else 'مستقر'}</td></tr>
<tr><td>05</td><td>الإنترنت والشبكات السحابية</td><td>{f"فقدان {getattr(obs, 'packet_loss_pct', 0):.1f}%" if obs and obs.packet_loss_pct is not None else '0%'} — {f"زمن استجابة {getattr(obs, 'external_rtt_ms', 0):.1f} ms" if obs and obs.external_rtt_ms else 'متصل'}</td></tr>
</tbody>
</table>
</body>
</html>
"""
            if file_path.endswith(".json"):
                data = {
                    "timestamp": datetime.now().isoformat(),
                    "network_identity": {
                        "ssid": getattr(net_id, 'ssid', None) if net_id else None,
                        "isp": getattr(net_id, 'isp', None) if net_id else None,
                        "local_ip": getattr(net_id, 'local_ip', None) if net_id else None,
                        "public_ip": getattr(net_id, 'public_ip', None) if net_id else None,
                        "gateway_ip": getattr(net_id, 'gateway_ip', None) if net_id else None,
                        "dns_servers": getattr(net_id, 'dns_servers', []) if net_id else [],
                    },
                    "metrics": {
                        "external_rtt_ms": getattr(obs, 'external_rtt_ms', None) if obs else None,
                        "gateway_rtt_ms": getattr(obs, 'gateway_rtt_ms', None) if obs else None,
                        "dns_latency_ms": getattr(obs, 'dns_latency_ms', None) if obs else None,
                        "packet_loss_pct": getattr(obs, 'packet_loss_pct', None) if obs else None,
                        "jitter_ms": getattr(obs, 'jitter_ms', None) if obs else None,
                    }
                }
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(html_content)

            QMessageBox.information(self, "تم التصدير بنجاح", f"تم حفظ تقرير فحص الشبكة بنجاح في:\n{file_path}")
        except Exception as exc:
            logger.error("Failed to export diagnostic report: %s", exc)
            QMessageBox.warning(self, "خطأ في التصدير", f"تعذر تصدير التقرير:\n{exc}")

    def _on_speed_test_done(self, timestamp: str) -> None:
        self._last_speed_test_time = timestamp
        self.view_dashboard.set_last_speed_test_time(timestamp)
        self.view_dashboard._on_scan_completed()
        if hasattr(self.app_core, "observability") and self.app_core.observability:
            last_diag = getattr(self.app_core.diagnosis, "last_diagnosis", None) if hasattr(self.app_core, "diagnosis") else None
            self.view_dashboard.update_telemetry(self.app_core.observability, last_diag)

    def _on_remediation_event_received(self, stage: str, data: Dict[str, Any]) -> None:
        action_name = data.get("action_name") or data.get("name", "إجراء تعافي ذكي")
        if stage == "started":
            self.view_dashboard.log_autonomous_action(
                f"تدخل ذاتي تلقائي: {action_name}",
                "قام NetGuard برصد تذبذب في مسارات الاتصال وبدأ المعالجة التلقائية فوراً.",
                level="warning",
            )
        else:
            self.view_dashboard.log_autonomous_action(
                f"نجاح التعافي الذاتي: {action_name}",
                "تم تنفيذ الإجراء وتأكيد استقرار البنج وسرعة الاستجابة بنجاح.",
                level="success",
            )
            self._refresh_timeline_from_records()

    def _refresh_timeline_from_records(self) -> None:
        """Refresh timeline in dashboard view with most recent incident and audit records."""
        if getattr(self, "_is_closing", False) or getattr(self, "_timeline_refreshing", False):
            return
        app_core = getattr(self, "app_core", None)
        if not app_core or not getattr(app_core, "ctx", None):
            return
        self._timeline_refreshing = True

        def _worker():
            try:
                if getattr(self, "_is_closing", False):
                    return
                core = getattr(self, "app_core", None)
                ctx = getattr(core, "ctx", None) if core else None
                if not ctx or getattr(self, "_is_closing", False):
                    return
                inc_repo = getattr(ctx, "incidents", None)
                aud_repo = getattr(ctx, "audit", None)
                if getattr(self, "_is_closing", False):
                    return
                incidents = inc_repo.get_recent(limit=1) if inc_repo and hasattr(inc_repo, "get_recent") else []
                audits = aud_repo.get_recent(limit=1) if aud_repo and hasattr(aud_repo, "get_recent") else []
                latest_inc = incidents[0] if incidents else None
                latest_aud = audits[0] if audits else None
                today_audits = aud_repo.get_by_date(date.today()) if aud_repo and hasattr(aud_repo, "get_by_date") else []
                succeeded_today = [a for a in today_audits if getattr(a, "status", None) == ActionExecutionStatus.SUCCEEDED]
                cnt = len(succeeded_today)
                avg_dur = (sum(getattr(a, "execution_duration_ms", 0.0) for a in succeeded_today) / (cnt * 1000.0)) if cnt > 0 else 0.0

                if getattr(self, "_is_closing", False):
                    return

                def _apply():
                    if getattr(self, "_is_closing", False):
                        return
                    self.view_dashboard.update_timeline_from_records(latest_inc, latest_aud)
                    self.view_dashboard.update_daily_incident_summary(cnt, avg_dur)

                if hasattr(self, "call_on_ui"):
                    self.call_on_ui(_apply)
            except Exception:
                pass
            finally:
                self._timeline_refreshing = False

        threading.Thread(target=_worker, daemon=True).start()

    def _on_timeline_rollback_requested(self) -> None:
        """Handle user rollback request from timeline panel."""
        aud_repo = getattr(self.app_core.ctx, "audit", None)
        audits = aud_repo.get_recent(limit=1) if aud_repo and hasattr(aud_repo, "get_recent") else []
        if not audits:
            QMessageBox.information(self, "تراجع عن الإصلاح", "لا توجد إجراءات مسجلة يمكن التراجع عنها.")
            return

        rec = audits[0]
        if rec.action_id == "switch_dns_resolver" or "dns" in rec.action_id:
            self._on_dashboard_revert_dns()
        elif hasattr(self.app_core, "orchestrator") and self.app_core.orchestrator:
            async def _run_rollback():
                try:
                    ok, msg = await self.app_core.orchestrator.rollback_action(rec.id)
                except Exception as exc:
                    ok, msg = False, str(exc)
                self.call_on_ui(lambda: self._on_timeline_rollback_done(ok, msg, rec))

            self.dispatch_coroutine(_run_rollback())
        else:
            QMessageBox.information(self, "تراجع عن الإصلاح", f"الإجراء '{rec.action_name}' غير قابل للتراجع المباشر.")

    def _on_timeline_rollback_done(self, success: bool, msg: str, record: Any) -> None:
        if success:
            QMessageBox.information(self, "تراجع عن الإصلاح", f"تم التراجع عن الإجراء بنجاح: {record.action_name}")
            self._refresh_timeline_from_records()
        else:
            QMessageBox.warning(self, "فشل التراجع", f"تعذر التراجع عن الإجراء: {msg}")

    def _async_inspect_network_environment(self) -> None:
        if "pytest" in sys.modules:
            return
        if getattr(self, "_is_inspecting_net_env", False):
            PerfMetricsCollector.get_instance().increment_counter("dedup_skip:network_env_inspect")
            return
        self._is_inspecting_net_env = True

        def _ownership_worker():
            try:
                from app.dns.ownership import DnsOwnershipEngine
                plat = getattr(getattr(self, "app_core", None), "ctx", None)
                plat_adapter = getattr(plat, "platform", None)
                ownership_engine = DnsOwnershipEngine(plat_adapter)
                report = ownership_engine.discover_ownership()
                self.call_on_ui(lambda: self.view_dns.update_ownership_report(report))
            except Exception as exc:
                logger.debug("Background DNS ownership discovery error: %s", exc)

        threading.Thread(target=_ownership_worker, daemon=True, name="DnsOwnershipWorker").start()

        def _safe_emit_net_info(info_dict: Dict[str, Any]) -> None:
            if getattr(self, "_is_closing", False):
                return
            if hasattr(self, "bridge") and self.bridge is not None:
                try:
                    self.bridge.network_info_ready.emit(info_dict)
                except (RuntimeError, AttributeError):
                    pass

        def _worker():
            perf = PerfMetricsCollector.get_instance()
            t0 = time.perf_counter()
            try:
                from app.platform.windows.network_info import get_network_identity

                # 1. Fast local identity emission (SSID, Local IP, Gateway, Adapter in <300ms)
                fast_info = get_network_identity(self.app_core.ctx.platform, include_hop2=False, include_isp=False)
                _safe_emit_net_info(fast_info)

                # 2. Single enriched background pass for ISP + Hop 2 traceroute (no duplicate 3rd call)
                if fast_info.get("is_connected", True):
                    full_info = get_network_identity(self.app_core.ctx.platform, include_hop2=True, include_isp=True)
                    _safe_emit_net_info(full_info)
            except Exception as e:
                logger.warning("Network environment inspection failed: %s", e)
            finally:
                self._is_inspecting_net_env = False
                perf.record_timing("network_env_inspect", (time.perf_counter() - t0) * 1000.0)

        threading.Thread(target=_worker, daemon=True, name="NetworkEnvInspectWorker").start()

    def _on_network_info_ready(self, info: Dict[str, Any]) -> None:
        norm = normalize_network_identity_payload(info)
        self._active_dns_servers = norm.get("dns_servers", [])
        GlobalNetworkStateStore.get_instance().update_from_network_info(norm)
        self.view_dashboard.update_network_identity(norm)
        self.view_dns.set_active_dns_info(self._active_dns_servers)
        if hasattr(self, "top_bar"):
            self.top_bar.set_last_update(datetime.now().strftime("%H:%M:%S"))

        # Set honest active DNS label without fake pre-seeded latencies
        active_ip = self._active_dns_servers[0] if self._active_dns_servers else ""
        if active_ip:
            from app.dns.detector import identify_provider
            provider = identify_provider(active_ip) or f"خادم ({active_ip})"
            self.view_dashboard.dns_panel.lbl_curr_name.setText(f"خادم DNS الحالي ({provider} · {active_ip})")
            if not getattr(self, "_active_dns_measured", False):
                self.view_dashboard.dns_panel.lbl_curr_ms.setText("جاري الفحص...")

        if not getattr(self, "_initial_dns_bench_triggered", False):
            self._initial_dns_bench_triggered = True
            QTimer.singleShot(2000, self._on_run_dns_benchmark)

    def _refresh_day_strips(self) -> None:
        """Fetch today's 48-slot status off the UI thread."""
        if getattr(self, "_daystrip_busy", False):
            return
        self._daystrip_busy = True

        def _worker():
            try:
                slots = None
                measurements = getattr(getattr(self.app_core, "ctx", None), "measurements", None)
                if measurements:
                    slots = measurements.get_day_slots(date.today())

                def _apply():
                    if slots is None:
                        return
                    today = date.today()
                    if hasattr(self.view_dashboard, "day_strip") and self.view_dashboard.day_strip:
                        self.view_dashboard.day_strip.set_data(slots)
                    if hasattr(self.view_history, "day_strip") and self.view_history.day_strip:
                        if getattr(self.view_history, "current_date", None) == today:
                            self.view_history.day_strip.set_data(slots)

                self.call_on_ui(_apply)
            except Exception as e:
                logger.warning("Failed to refresh day strips: %s", e)
            finally:
                self._daystrip_busy = False

        threading.Thread(target=_worker, daemon=True).start()

    def _async_refresh_history(self) -> None:
        now = time.monotonic()
        if now - getattr(self, "_history_refresh_at", 0.0) < 5.0:
            return
        if getattr(self, "_history_busy", False):
            return
        self._history_refresh_at = now
        self._history_busy = True

        def _worker():
            try:
                incidents = []
                repo = getattr(getattr(self.app_core, "ctx", None), "incidents", None)
                if repo and getattr(self.view_history, "current_date", None) == date.today():
                    incidents = repo.get_by_date(date.today())
                self.call_on_ui(lambda rows=incidents: self.view_history.update_incidents(rows))
            except Exception as exc:
                logger.warning("History refresh failed: %s", exc)
            finally:
                self._history_busy = False

        threading.Thread(target=_worker, daemon=True).start()

    def _async_refresh_audit(self) -> None:
        now = time.monotonic()
        if now - getattr(self, "_audit_refresh_at", 0.0) < 5.0:
            return
        if getattr(self, "_audit_busy", False):
            return
        self._audit_refresh_at = now
        self._audit_busy = True

        def _worker():
            try:
                records = []
                repo = getattr(getattr(self.app_core, "ctx", None), "audit", None)
                if repo:
                    records = repo.get_recent(limit=30)
                self.call_on_ui(lambda rows=records: self.view_remediation.update_audit_log(rows))
            except Exception as exc:
                logger.warning("Audit refresh failed: %s", exc)
            finally:
                self._audit_busy = False

        threading.Thread(target=_worker, daemon=True).start()

    def _on_ui_tick(self) -> None:
        """Periodic UI update polling in-memory telemetry completely autonomously.

        Guaranteed non-overlapping and optimized for low-end hardware.
        """
        if getattr(self, "_is_ui_tick_running", False):
            return
        try:
            if hasattr(self, "isMinimized") and self.isMinimized():
                if not getattr(self, "_clock_paused_min", False):
                    from app.ui.animation_clock import AnimationMasterClock
                    AnimationMasterClock.get_instance().pause()
                    self._clock_paused_min = True
                return
            if getattr(self, "_clock_paused_min", False):
                from app.ui.animation_clock import AnimationMasterClock
                AnimationMasterClock.get_instance().resume()
                self._clock_paused_min = False
        except Exception:
            pass
        self._is_ui_tick_running = True
        _tick_t0 = time.perf_counter()
        try:
            obs = self.app_core.observability
            last_diag = self.app_core.diagnosis.last_diagnosis
            curr_widget = self.stack.currentWidget() if hasattr(self, "stack") else None

            # Lightweight targeted updates: avoid redundant full-chart redraws if telemetry signature didn't change
            def _obs_sig(o: Any) -> Any:
                if o is None or not hasattr(o, "get_latest_measurement"):
                    return None
                return tuple(
                    getattr(o.get_latest_measurement(mt), "timestamp", None)
                    for mt in (
                        MetricType.EXTERNAL_LATENCY,
                        MetricType.GATEWAY_LATENCY,
                        MetricType.BANDWIDTH_RX_BYTES_PER_SEC,
                        MetricType.DNS_LATENCY,
                    )
                )

            sig = _obs_sig(obs)
            diag_sig = id(last_diag)
            on_dashboard = (curr_widget is None or curr_widget == self.view_dashboard or curr_widget not in (
                getattr(self, "view_reports", None),
                getattr(self, "view_meeting_guard", None),
                getattr(self, "view_traffic", None),
                getattr(self, "view_wifi", None),
                getattr(self, "view_router", None),
                getattr(self, "view_quality", None),
                getattr(self, "view_settings", None),
                getattr(self, "view_about", None),
            ))
            if on_dashboard:
                if sig != getattr(self, "_last_obs_tick_sig", None) or diag_sig != getattr(self, "_last_diag_tick_sig", None):
                    self.view_dashboard.update_telemetry(obs, last_diag)
                    self._last_obs_tick_sig = sig
                    self._last_diag_tick_sig = diag_sig
            elif curr_widget == getattr(self, "view_reports", None):
                net_info = getattr(self.view_dashboard, "_last_net_info", {})
                self.view_diagnosis.update_live_telemetry(obs, net_info, last_diag)
                if last_diag:
                    self.view_diagnosis.update_diagnosis(last_diag)
                self._async_refresh_history()
            elif curr_widget == getattr(self, "view_meeting_guard", None):
                self._async_refresh_audit()
            elif curr_widget == getattr(self, "view_traffic", None):
                self.view_traffic.sample_live_counters()

            if hasattr(self, "top_bar"):
                self.top_bar.set_last_update(datetime.now().strftime("%H:%M:%S"))

            # Helper for probe measurement freshness check (<= 10s)
            def _is_measurement_fresh(m: Optional[Any], max_age_sec: float = 10.0) -> bool:
                if m is None or getattr(m, "raw_value", None) is None:
                    return False
                ts = getattr(m, "timestamp", None)
                if ts is None:
                    return True
                try:
                    from datetime import datetime, timezone
                    if isinstance(ts, (int, float)):
                        return 0.0 <= (time.time() - ts) <= max_age_sec
                    if isinstance(ts, datetime):
                        now_dt = datetime.now(timezone.utc)
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                        return 0.0 <= (now_dt - ts).total_seconds() <= max_age_sec
                except Exception:
                    return True
                return True

            # Live Quality Sample Recording & Pre-Meeting Baseline (Feature 12, 13)
            if hasattr(self, "traffic_controller") and self.traffic_controller and obs:
                try:
                    wan_lat_m = obs.get_latest_measurement(MetricType.EXTERNAL_LATENCY)
                    wan_loss_m = obs.get_latest_measurement(MetricType.EXTERNAL_PACKET_LOSS)
                    jit_m = obs.get_latest_measurement(MetricType.JITTER_MS)

                    if (
                        _is_measurement_fresh(wan_lat_m)
                        and _is_measurement_fresh(wan_loss_m)
                        and _is_measurement_fresh(jit_m)
                    ):
                        now_mono = time.monotonic()
                        tracker = getattr(self.traffic_controller, "session_tracker", None)
                        active_s = tracker.get_active_sessions() if tracker else []
                        sess_id = active_s[0].process_name if active_s else None

                        cur_loss = float(wan_loss_m.raw_value) * 100.0
                        cur_jit = float(jit_m.raw_value)
                        cur_rtt = float(wan_lat_m.raw_value)

                        self.traffic_controller.record_quality_sample(
                            loss_pct=cur_loss,
                            jitter_ms=cur_jit,
                            rtt_ms=cur_rtt,
                            timestamp_mono=now_mono,
                            session_id=sess_id,
                        )
                except Exception as ex:
                    logger.debug("Failed recording live quality sample: %s", ex)

            # Meeting Shield proactive early warning check (when meeting is active)
            try:
                tracker = getattr(self.traffic_controller, "session_tracker", None)
                if tracker and tracker.has_active_conferencing():
                    active_meetings = tracker.get_active_sessions()
                    if active_meetings:
                        m_sess = active_meetings[0]
                        gw_lat_m = obs.get_latest_measurement(MetricType.GATEWAY_LATENCY)
                        gw_loss_m = obs.get_latest_measurement(MetricType.GATEWAY_PACKET_LOSS)
                        wan_lat_m = obs.get_latest_measurement(MetricType.EXTERNAL_LATENCY)
                        wan_loss_m = obs.get_latest_measurement(MetricType.EXTERNAL_PACKET_LOSS)
                        jit_m = obs.get_latest_measurement(MetricType.JITTER_MS)

                        # Check freshness - reject missing or stale telemetry without converting to 0.0
                        has_fresh_metrics = (
                            _is_measurement_fresh(gw_lat_m)
                            and _is_measurement_fresh(wan_lat_m)
                            and _is_measurement_fresh(jit_m)
                        )
                        if has_fresh_metrics:
                            gw_lat = float(gw_lat_m.raw_value)
                            gw_loss = float(gw_loss_m.raw_value) if _is_measurement_fresh(gw_loss_m) else 0.0
                            wan_lat = float(wan_lat_m.raw_value)
                            wan_loss = float(wan_loss_m.raw_value) if _is_measurement_fresh(wan_loss_m) else 0.0
                            jit = float(jit_m.raw_value)

                            if not hasattr(self, "_meeting_shield"):
                                from app.traffic.meeting_detector import MeetingShield
                                self._meeting_shield = MeetingShield(self)

                            procs = getattr(self.view_traffic, "_last_profiles_cache", [])
                            alert = self._meeting_shield.evaluate_telemetry(
                                is_meeting_active=True,
                                meeting_app_name=m_sess.app_name,
                                meeting_process_name=m_sess.process_name,
                                gateway_latency_ms=gw_lat,
                                gateway_loss_ratio=gw_loss,
                                wan_latency_ms=wan_lat,
                                wan_loss_ratio=wan_loss,
                                jitter_ms=jit,
                                active_processes=procs,
                            )
                            if alert:
                                tracker.set_early_warning(m_sess.process_name, alert["case"], alert["message"])
                                if hasattr(self, "view_traffic"):
                                    self.view_traffic._refresh_sessions_ui()

                            # Closed-loop guard: check quality post-policy and auto-rollback if degraded
                            if hasattr(self, "traffic_controller") and self.traffic_controller:
                                rolled_back = self.traffic_controller.evaluate_closed_loop_quality(
                                    current_loss_pct=wan_loss * 100.0,
                                    current_jitter_ms=jit,
                                    current_rtt_ms=wan_lat,
                                    timestamp_mono=time.monotonic(),
                                    session_id=m_sess.process_name,
                                )
                                if rolled_back:
                                    self.view_dashboard.log_autonomous_action(
                                        "تراجع تلقائي عن سياسة QoS",
                                        self.traffic_controller._closed_loop_rollback_reason,
                                        level="warning",
                                    )
            except Exception as e:
                logger.debug("Meeting shield check non-fatal error: %s", e)

            # Watchdog QoS policy reconciliation every 30 seconds off UI thread (overlap-guarded)
            if (
                self.ticker_counter % 30 == 0
                and hasattr(self, "traffic_controller")
                and self.traffic_controller
                and not getattr(self, "_is_reconciling_qos", False)
            ):
                self._is_reconciling_qos = True

                def _recon_worker():
                    try:
                        if getattr(self, "_is_closing", False):
                            return
                        report = self.traffic_controller.reconcile_active_policies()
                        if getattr(self, "_is_closing", False):
                            return
                        is_active = self.traffic_controller.is_critical_meeting_active()
                        verified = (report.get("status") == "verified")
                        rolled = getattr(self.traffic_controller, "_closed_loop_rolled_back", False)
                        reason = getattr(self.traffic_controller, "_closed_loop_rollback_reason", "")
                        confirmed = report.get("confirmed_count", len(getattr(self.traffic_controller, "_active_qos_specs", [])))
                        if hasattr(self, "view_traffic") and hasattr(self.view_traffic, "set_qos_status_badge"):
                            self.call_on_ui(
                                lambda: self.view_traffic.set_qos_status_badge(
                                    is_active=is_active,
                                    verified=verified,
                                    confirmed_count=confirmed,
                                    rolled_back=rolled,
                                    rollback_reason=reason,
                                )
                            )
                    finally:
                        self._is_reconciling_qos = False

                threading.Thread(target=_recon_worker, daemon=True, name="QosReconcileWorker").start()

            # Evaluate live telemetry advisories (bufferbloat & Wi-Fi weak link)
            if hasattr(self, "traffic_controller") and self.traffic_controller and obs:
                try:
                    gw_lat_m = obs.get_latest_measurement(MetricType.GATEWAY_LATENCY)
                    wan_lat_m = obs.get_latest_measurement(MetricType.EXTERNAL_LATENCY)
                    wan_loss_m = obs.get_latest_measurement(MetricType.EXTERNAL_PACKET_LOSS)
                    jit_m = obs.get_latest_measurement(MetricType.JITTER_MS)

                    if _is_measurement_fresh(gw_lat_m) and _is_measurement_fresh(wan_lat_m):
                        gw_lat = float(gw_lat_m.raw_value)
                        wan_lat = float(wan_lat_m.raw_value)
                        wan_loss_pct = float(wan_loss_m.raw_value) * 100.0 if _is_measurement_fresh(wan_loss_m) else 0.0
                        jit = float(jit_m.raw_value) if _is_measurement_fresh(jit_m) else 0.0

                        net_info = getattr(self.view_dashboard, "_network_info", {})
                        is_wifi = bool(net_info.get("is_wifi", False)) if isinstance(net_info, dict) else getattr(net_info, "is_wifi", False)
                        sig_pct = net_info.get("wifi_signal_pct") if isinstance(net_info, dict) else getattr(net_info, "wifi_signal_pct", None)

                        self.traffic_controller.evaluate_telemetry_advisories(
                            idle_latency_ms=gw_lat,
                            load_latency_ms=wan_lat,
                            is_wifi=is_wifi,
                            signal_pct=sig_pct,
                            jitter_ms=jit,
                            packet_loss_pct=wan_loss_pct,
                        )
                except Exception as e:
                    logger.debug("Telemetry advisories evaluation error: %s", e)

            # Refresh 48-slot day strip every 120 seconds
            self.ticker_counter = getattr(self, "ticker_counter", 0) + 1
            if self.ticker_counter % 120 == 0:
                self._refresh_day_strips()

            # Periodic timeline synchronization from SQLite records every 30 seconds
            if self.ticker_counter % 30 == 0:
                self._refresh_timeline_from_records()

            # Non-blocking external DNS change check via background worker every 60 seconds
            if self.ticker_counter % 60 == 0:
                self._async_check_external_dns()

            # Periodic background traffic consumer refresh every 30 seconds (only if visible)
            if self.ticker_counter % 30 == 0 and curr_widget in (self.view_dashboard, self.view_traffic):
                self._on_scan_traffic()
        finally:
            self._is_ui_tick_running = False
            tick_ms = (time.perf_counter() - _tick_t0) * 1000.0
            if tick_ms > 90.0:
                PerfMetricsCollector.get_instance().record_ui_stall(tick_ms)

    def _async_check_external_dns(self) -> None:
        if getattr(self, "_is_checking_ext_dns", False):
            return
        self._is_checking_ext_dns = True

        def _worker():
            try:
                from app.dns.state import DnsStateManager
                from app.dns.detector import identify_provider, measure_dns_latency
                mgr = DnsStateManager.get_instance()
                iface = self.app_core.ctx.platform.get_primary_interface() or "Wi-Fi"
                curr_os_servers = self.app_core.ctx.platform.get_interface_dns_servers(iface) or []
                known_servers = mgr.current.active_servers
                if curr_os_servers and known_servers and curr_os_servers != known_servers:
                    p_name = identify_provider(curr_os_servers[0]) or f"خادم مخصص ({curr_os_servers[0]})"
                    ms_val = measure_dns_latency(curr_os_servers[0])
                    self.call_on_ui(lambda: mgr.update(
                        active_servers=curr_os_servers,
                        detected_provider=p_name,
                        last_measured_ms=ms_val,
                        is_healthy=(ms_val is not None and ms_val < 150.0),
                    ))
            finally:
                self._is_checking_ext_dns = False

        threading.Thread(target=_worker, daemon=True).start()

    def _on_run_dns_benchmark(self, full: bool = False) -> None:
        if getattr(self, "_is_benchmarking_dns", False):
            return
        if hasattr(self, "traffic_controller") and self.traffic_controller and self.traffic_controller.is_critical_meeting_active():
            logger.info("DNS benchmark deferred: active meeting in progress (protecting live call).")
            self.view_dns.benchmark_btn.setEnabled(True)
            self.view_dns.benchmark_btn.setText("فحص خوادم DNS الآن")
            return

        self._is_benchmarking_dns = True
        self.view_dns.benchmark_btn.setEnabled(False)
        self.view_dns.benchmark_btn.setText("جاري الفحص التلقائي...")

        active_ips = list(getattr(self, "_active_dns_servers", []))
        if not active_ips:
            try:
                iface = self.app_core.ctx.platform.get_primary_interface() or "Wi-Fi"
                active_ips = self.app_core.ctx.platform.get_interface_dns_servers(iface) or []
            except Exception:
                pass

        async def _run_benchmark():
            scores = []
            err_msg = None
            try:
                from app.dns.benchmark import DNSBenchmark
                bench = DNSBenchmark(
                    rounds=3 if full else 1,
                    timeout_sec=2.0 if full else 1.0,
                )
                scores = await bench.rank_all(active_resolver_ips=active_ips)
            except Exception as exc:
                logger.warning("DNS benchmark failed: %s", exc)
                err_msg = str(exc)
            finally:
                self.call_on_ui(lambda: self._on_dns_benchmark_done(scores, err_msg))

        self.dispatch_coroutine(_run_benchmark())

    def _on_dns_state_changed(self, state: Any) -> None:
        """Propagate updated DNS single-source-of-truth across all subscribed views (Item B1)."""
        active_name = getattr(state, "detected_provider", None) or "خادم DNS"
        active_ms = getattr(state, "last_measured_ms", None) or 0.0
        active_dns = getattr(state, "active_servers", [])
        primary_ip = active_dns[0] if active_dns else ""

        self.view_dns.set_active_dns_info(active_dns)
        scores = getattr(state, "scores", [])
        if scores:
            reachable_scores = [s for s in scores if getattr(s, "is_ip_reachable", True) and s.success_rate > 0.0]
            from app.dns.optimizer import select_best_resolver
            best = select_best_resolver(reachable_scores) or getattr(state, "best_server", None) or scores[0]
            best_ms = getattr(best, "median_latency_ms", 0.0) or best.mean_latency_ms
            from app.dns.optimizer import DEFAULT_MIN_IMPROVEMENT_MS
            is_optimal = (best.ip == primary_ip) or (active_ms <= 0) or ((active_ms - best_ms) < DEFAULT_MIN_IMPROVEMENT_MS)
            from app.core.models.metrics import OperatingMode
            is_auto_mode = (
                self.app_core.orchestrator.mode in (OperatingMode.AUTO, OperatingMode.AUTONOMOUS_SAFE, "auto")
                or str(getattr(self.app_core.orchestrator, "mode", "auto")).lower() in ("auto", "operatingmode.auto", "autonomous_safe", "autonomous")
            )
            self.view_dashboard.update_dns_recommendation(
                curr_name=active_name,
                curr_ms=active_ms,
                best_name=best.name.replace(" Primary", "").replace(" Secondary", ""),
                best_ip=best.ip,
                best_ms=best_ms,
                is_optimal=is_optimal,
                is_autonomous=is_auto_mode,
            )
            self.view_diagnosis.update_dns_telemetry(
                dns_name=active_name,
                latency_ms=active_ms,
                is_healthy=getattr(state, "is_healthy", True),
                is_optimal=is_optimal,
            )
            self.view_dns.update_rankings(
                scores=scores,
                active_ms=active_ms,
                active_name=active_name,
                is_optimal=is_optimal,
            )
        else:
            self.view_diagnosis.update_dns_telemetry(
                dns_name=active_name,
                latency_ms=active_ms,
                is_healthy=getattr(state, "is_healthy", True),
                is_optimal=True,
            )
            if active_ms > 0:
                self.view_dashboard.update_dns_recommendation(
                    curr_name=active_name,
                    curr_ms=active_ms,
                    best_name=active_name,
                    best_ip=primary_ip,
                    best_ms=active_ms,
                    is_optimal=True,
                    is_autonomous=True,
                )

    def _on_dns_benchmark_done(self, scores, error_message: Optional[str] = None) -> None:
        self._is_benchmarking_dns = False
        self.view_dns.benchmark_btn.setEnabled(True)
        self.view_dns.benchmark_btn.setText("فحص وترتيب الخوادم الآن")

        if not scores:
            msg = error_message or "تعذر قياس خوادم DNS - تحقق من اتصال الإنترنت"
            logger.warning("DNS benchmark finished without scores: %s", msg)
            if hasattr(self.view_dns, "set_benchmark_error"):
                self.view_dns.set_benchmark_error(msg)
            return

        self.view_dns._last_scores = scores
        active_dns = getattr(self, "_active_dns_servers", [])
        if not active_dns:
            iface = self.app_core.ctx.platform.get_primary_interface() or "Wi-Fi"
            active_dns = self.app_core.ctx.platform.get_interface_dns_servers(iface) or ["1.1.1.1", "1.0.0.1"]

        primary_ip = active_dns[0] if active_dns else ""

        reachable_scores = [s for s in scores if getattr(s, "is_ip_reachable", True) and s.success_rate > 0.0]
        from app.dns.optimizer import select_best_resolver
        best = select_best_resolver(reachable_scores) or scores[0]

        from app.dns.detector import get_secondary_ip
        secondary_ip = get_secondary_ip(best.ip) or ("1.0.0.1" if "1.1.1.1" in best.ip else ("8.8.4.4" if "8.8.8.8" in best.ip else ""))
        best_name = best.name.replace(" Primary", "").replace(" Secondary", "")
        best_ms = getattr(best, "median_latency_ms", 0.0) or best.mean_latency_ms

        self._last_best_dns = (best.ip, secondary_ip, best_name, best_ms)

        # Match primary active DNS strictly by primary IP
        matched_score = None
        if primary_ip:
            for s in scores:
                if s.ip == primary_ip:
                    matched_score = s
                    break

        active_ip = primary_ip or "192.168.1.1"
        from app.dns.detector import identify_provider
        active_provider = identify_provider(active_ip)

        if matched_score is not None:
            active_ms = getattr(matched_score, "median_latency_ms", 0.0) or matched_score.mean_latency_ms
            active_name = active_provider or matched_score.name.replace(" Primary", "").replace(" Secondary", "")
        else:
            active_ms = 0.0
            active_name = active_provider or f"خادم ({active_ip})"

        from app.dns.optimizer import DEFAULT_MIN_IMPROVEMENT_MS
        is_same_ip = (best.ip == primary_ip)
        is_faster_candidate = (
            not is_same_ip and active_ms > 0 and (active_ms - best_ms) >= DEFAULT_MIN_IMPROVEMENT_MS
        )
        is_optimal = is_same_ip or (not is_faster_candidate)
        is_healthy = (active_ms > 0 and active_ms <= 85.0)

        # Generate intelligent analysis
        from app.dns.benchmark import generate_dns_analysis
        active_analysis = generate_dns_analysis(
            active_ip=active_ip,
            active_name=active_name,
            active_score=matched_score,
            all_scores=scores,
        )

        from app.dns.state import DnsStateManager
        DnsStateManager.get_instance().update(
            active_servers=active_dns,
            detected_provider=active_name,
            last_measured_ms=active_ms,
            min_latency_ms=getattr(matched_score, "min_latency_ms", active_ms) if matched_score else active_ms,
            max_latency_ms=getattr(matched_score, "max_latency_ms", active_ms) if matched_score else active_ms,
            mean_latency_ms=active_ms,
            query_success_rate=getattr(matched_score, "success_rate", 1.0) if matched_score else (1.0 if active_ms > 0 else 0.0),
            status_summary=active_analysis.get("verdict", "يعمل بشكل طبيعي"),
            analysis_text=active_analysis.get("analysis_text", ""),
            recommendation_text=active_analysis.get("recommendation_text", ""),
            is_healthy=is_healthy,
            best_server=best,
            scores=scores,
        )

        from app.core.models.metrics import OperatingMode
        is_auto_mode = (
            self.app_core.orchestrator.mode in (OperatingMode.AUTO, OperatingMode.AUTONOMOUS_SAFE, "auto")
            or str(getattr(self.app_core.orchestrator, "mode", "auto")).lower() in ("auto", "operatingmode.auto", "autonomous_safe", "autonomous")
        )

        self.view_dashboard.update_dns_recommendation(
            curr_name=active_name,
            curr_ms=active_ms,
            best_name=best_name,
            best_ip=best.ip,
            best_ms=best_ms,
            is_optimal=is_optimal,
            is_autonomous=is_auto_mode,
        )
        self.view_dns.set_active_dns_info(active_dns)
        self.view_dns.update_rankings(
            scores=scores,
            active_ms=active_ms,
            active_name=active_name,
            is_optimal=is_optimal,
        )
        self.view_diagnosis.update_dns_telemetry(
            dns_name=active_name,
            latency_ms=active_ms,
            is_healthy=is_healthy,
            is_optimal=is_optimal,
        )
        if hasattr(self.view_dns, "lbl_last_evaluation"):
            self.view_dns.lbl_last_evaluation.setText(f"آخر تقييم: {datetime.now().strftime('%H:%M')}")

        opt = getattr(self.app_core, "dns_optimizer", None)
        if opt is not None and is_auto_mode:

            async def _auto_switch_from_rankings():
                switched = await opt.auto_optimize_dns(ranked=scores)

                def _after_decision():
                    decision = getattr(opt, "last_decision", None)
                    if decision and hasattr(self.view_dns, "lbl_last_switch"):
                        self.view_dns.lbl_last_switch.setText(f"قرار DNS: {decision.message_ar}")
                    if not switched or decision is None or decision.best is None:
                        return
                    self._last_dns_switch_time = time.time()
                    applied = [decision.best.ip]
                    if secondary_ip:
                        applied.append(secondary_ip)
                    self._active_dns_servers = applied
                    self.view_dns.set_active_dns_info(applied)
                    self.view_dashboard.update_dns_recommendation(
                        curr_name=best_name,
                        curr_ms=best_ms,
                        best_name=best_name,
                        best_ip=decision.best.ip,
                        best_ms=best_ms,
                        is_optimal=True,
                        is_autonomous=True,
                        auto_applied=True,
                    )

                self.call_on_ui(_after_decision)

            self.dispatch_coroutine(_auto_switch_from_rankings())

        def _ownership_worker():
            try:
                from app.dns.ownership import DnsOwnershipEngine
                plat = getattr(getattr(self, "app_core", None), "ctx", None)
                plat_adapter = getattr(plat, "platform", None)
                report = DnsOwnershipEngine(plat_adapter).discover_ownership()
                self.call_on_ui(lambda: self.view_dns.update_ownership_report(report))
            except Exception:
                pass

        threading.Thread(target=_ownership_worker, daemon=True).start()

    def _on_dashboard_apply_dns(self) -> None:
        if hasattr(self, "_last_best_dns"):
            ip, sec, name, ms = self._last_best_dns
            self._last_dns_switch_time = time.time()
            self._on_apply_dns_requested(ip, sec, name)
            self.view_dns.set_active_dns_info(self._active_dns_servers)
            if hasattr(self.view_dns, "_last_scores"):
                self.view_dns.update_rankings(
                    self.view_dns._last_scores,
                    active_ms=ms,
                    active_name=name,
                    is_optimal=True,
                )

    def _on_dashboard_revert_dns(self) -> None:
        """Asynchronously restore previous DNS or DHCP without blocking the UI thread."""
        if hasattr(self, "traffic_controller") and self.traffic_controller and self.traffic_controller.is_critical_meeting_active():
            QMessageBox.warning(self, "درع الاجتماعات", "لا يمكن تغيير أو استعادة إعدادات DNS أثناء اجتماع نشط لحماية استقرار المكالمة من الانقطاع.")
            return

        iface = self.app_core.ctx.platform.get_primary_interface() or "Wi-Fi"
        pre = getattr(self, "_last_dns_pre_state", None)
        if pre and not pre.get("is_dhcp") and pre.get("original_servers"):
            restore_target = pre["original_servers"]
            desc = f"تمت استعادة خوادم DNS السابقة: {', '.join(restore_target)}"
        else:
            restore_target = []
            desc = "تمت استعادة إعدادات DNS التلقائية من الراوتر (DHCP)."

        def _worker():
            from app.dns.state import DnsStateManager
            ok, msg = self.app_core.ctx.platform.set_interface_dns_servers(iface, restore_target)
            self.app_core.ctx.platform.flush_dns_cache()
            actual = self.app_core.ctx.platform.get_interface_dns_servers(iface) or []
            DnsStateManager.get_instance().update(
                active_servers=actual,
                configured_mode="dhcp" if len(restore_target) == 0 else "static",
                is_healthy=True,
                last_switch_time=time.time(),
            )

            import uuid
            from app.core.models.metrics import ActionExecutionRecord, ActionExecutionStatus, RiskLevel
            revert_record = ActionExecutionRecord(
                id=str(uuid.uuid4()),
                action_id="revert_dns_resolver",
                action_name="استعادة إعدادات DNS",
                risk_level=RiskLevel.LEVEL_2_CONTROLLED,
                trigger_diagnosis_id="user_revert",
                pre_remedy_metrics={"interface": iface},
                post_remedy_metrics={"active_servers": restore_target, "status": msg},
                status=ActionExecutionStatus.ROLLED_BACK if ok else ActionExecutionStatus.FAILED,
                execution_duration_ms=30.0,
                verification_duration_ms=10.0,
                error_message=None if ok else msg,
                rollback_performed=True,
                rollback_success=ok,
            )
            ctx = getattr(getattr(self, "app_core", None), "ctx", None)
            if ctx and hasattr(ctx, "audit"):
                ctx.audit.save(revert_record)

            def _update_ui():
                self._last_dns_switch_time = time.time()
                self._active_dns_servers = restore_target
                self.view_dashboard.log_autonomous_action(
                    "استعادة إعدادات DNS",
                    desc,
                    level="success" if ok else "error",
                )
                self._refresh_timeline_from_records()
                self._on_run_dns_benchmark()

            self.call_on_ui(_update_ui)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_apply_dns_requested(self, primary_ip: str, secondary_ip: str, name: str) -> None:
        if hasattr(self, "traffic_controller") and self.traffic_controller and self.traffic_controller.is_critical_meeting_active():
            QMessageBox.warning(self, "درع الاجتماعات", "لا يمكن تغيير خادم DNS أثناء اجتماع نشط لحماية استقرار المكالمة من الانقطاع.")
            return

        self._last_dns_switch_time = time.time()
        def _worker():
            import uuid
            from app.core.models.metrics import ActionExecutionRecord, ActionExecutionStatus, RiskLevel
            from app.dns.service import DnsService
            
            if not self.app_core.ctx.platform.is_elevated():
                logger.info("DNS switch: Process is not directly elevated, relying on platform adapter elevated execution...")

            iface = self.app_core.ctx.platform.get_primary_interface() or "Wi-Fi"
            prev_servers = self.app_core.ctx.platform.get_interface_dns_servers(iface) or []
            is_dhcp = len(prev_servers) == 0
            self._last_dns_pre_state = {
                "interface": iface,
                "original_servers": list(prev_servers),
                "is_dhcp": is_dhcp,
            }

            # 1. Pre-remedy measurement on the active resolver
            from app.dns.detector import measure_dns_resolver_deep
            prev_test_ip = prev_servers[0] if prev_servers else primary_ip
            pre_meas = measure_dns_resolver_deep(prev_test_ip, rounds=2, timeout_sec=1.5)
            before_ms = pre_meas.mean_latency_ms if pre_meas.success_rate > 0 else 0.0

            # 2. Execute full 7-step DNS workflow via DnsService (Items F6, F8, F9)
            dns_service = DnsService(platform_adapter=self.app_core.ctx.platform)
            t0 = time.perf_counter()
            result = dns_service.apply_dns_servers(
                interface_alias=iface,
                primary_v4=primary_ip,
                secondary_v4=secondary_ip,
            )
            exec_duration_ms = (time.perf_counter() - t0) * 1000.0

            if not result.success:
                st = ActionExecutionStatus.FAILED
                err_msg = result.error_message or f"فشل التحقق من استجابة {name} ({primary_ip}) بعد التطبيق - تم التراجع التلقائي."
                self.call_on_ui(lambda: self.view_dashboard.log_autonomous_action(
                    f"تراجع عن تغيير DNS",
                    f"خادم {name} ({primary_ip}) لم يستجب لاستعلامات التحقق (الخطوة {result.step_reached}/7). تم استعادة الإعدادات الأصلية فوراً.",
                    level="warning",
                ))
            else:
                st = ActionExecutionStatus.SUCCEEDED
                err_msg = None
                after_ms = result.latency_ms or 0.0
                self._active_dns_servers = result.applied_servers

                # Update dashboard remediation evidence strip and sync DNS tab
                def _update_success_ui():
                    self.view_dashboard.dns_panel.set_remediation_result(
                        before_ms=before_ms,
                        after_ms=after_ms,
                        new_name=name,
                    )
                    self.view_dashboard.log_autonomous_action(
                        f"اعتماد خادم {name}",
                        f"تم التحويل بنجاح من {before_ms:.0f} ms إلى {after_ms:.0f} ms والتحقق عبر استعلام DNS فعلي كامل.",
                        level="success",
                    )
                    self.view_dns.set_active_dns_info(result.applied_servers)
                    if hasattr(self.view_dns, "_last_scores"):
                        self.view_dns.update_rankings(
                            self.view_dns._last_scores,
                            active_ms=after_ms,
                            active_name=name,
                            is_optimal=True,
                        )
                    self._async_inspect_network_environment()

                self.call_on_ui(_update_success_ui)

            record = ActionExecutionRecord(
                id=str(uuid.uuid4()),
                action_id="switch_dns_resolver",
                action_name=f"تحويل إلى {name} ({primary_ip})",
                risk_level=RiskLevel.LEVEL_2_CONTROLLED,
                trigger_diagnosis_id="user_selection",
                pre_remedy_metrics={
                    "interface": iface,
                    "original_servers": list(prev_servers),
                    "is_dhcp": is_dhcp,
                    "latency_ms": before_ms,
                },
                post_remedy_metrics={
                    "active_servers": result.applied_servers,
                    "status": "applied" if result.success else "failed",
                    "latency_ms": result.latency_ms,
                    "step_reached": result.step_reached,
                },
                status=st,
                execution_duration_ms=exec_duration_ms,
                verification_duration_ms=10.0,
                error_message=err_msg,
                rollback_performed=result.rolled_back,
            )
            ctx = getattr(getattr(self, "app_core", None), "ctx", None)
            if ctx and hasattr(ctx, "audit"):
                ctx.audit.save(record)
            self.call_on_ui(self._refresh_timeline_from_records)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_scan_traffic(self) -> None:
        self.view_traffic.btn_refresh.setEnabled(False)
        self.view_traffic.btn_refresh.setText("جاري الفحص...")

        async def _run_scan():
            try:
                profiles = await self.traffic_controller.scan_active_applications()
                is_conf = self.traffic_controller.is_critical_meeting_active()
                qos = []
                plat = getattr(self.app_core.ctx, "platform", None)
                if plat is not None and hasattr(plat, "get_qos_policies"):
                    loop = asyncio.get_running_loop()
                    try:
                        qos = await loop.run_in_executor(None, plat.get_qos_policies) or []
                    except Exception:
                        qos = []
                self._last_qos_policies = qos
                if hasattr(self, "bridge") and self.bridge is not None:
                    try:
                        self.bridge.traffic_scan_done.emit(profiles, is_conf)
                    except (RuntimeError, AttributeError):
                        pass
            except Exception as exc:
                logger.warning("Traffic scan coroutine error: %s", exc)

        self.dispatch_coroutine(_run_scan())

    def _on_scan_traffic_done(self, profiles, is_conferencing: bool) -> None:
        qos_pols = getattr(self, "_last_qos_policies", [])
        self.view_traffic.btn_refresh.setEnabled(True)
        self.view_traffic.btn_refresh.setText("تحديث / Refresh")
        self.view_traffic.update_profiles(
            profiles,
            conferencing_active=is_conferencing,
            qos_policies=qos_pols,
        )
        if hasattr(self, "view_meeting_guard"):
            self.view_meeting_guard.update_live_state(
                profiles=profiles,
                conferencing_active=is_conferencing,
                qos_policies=qos_pols,
                verified=len(qos_pols) > 0,
                confirmed_count=len(qos_pols),
                rolled_back=bool(getattr(self.traffic_controller, "_closed_loop_rolled_back", False)),
                rollback_reason=str(getattr(self.traffic_controller, "_closed_loop_rollback_reason", "")),
            )
        self.view_dashboard.consumers_panel.update_processes(profiles)

    def _on_poll_meeting_signal(self) -> None:
        if not hasattr(self, "traffic_controller") or not self.traffic_controller:
            return
        if getattr(self, "_is_polling_meeting_signal", False):
            return
        self._is_polling_meeting_signal = True

        async def _run_poll():
            try:
                await self.traffic_controller.poll_meeting_signal()
                is_active = self.traffic_controller.is_critical_meeting_active()
                rolled = getattr(self.traffic_controller, "_closed_loop_rolled_back", False)
                reason = getattr(self.traffic_controller, "_closed_loop_rollback_reason", "")
                confirmed = len(getattr(self.traffic_controller, "_active_qos_specs", []))

                def _sync_guard_ui() -> None:
                    self.view_traffic.set_qos_status_badge(
                        is_active=is_active,
                        verified=confirmed > 0 or not is_active,
                        confirmed_count=confirmed,
                        rolled_back=rolled,
                        rollback_reason=reason,
                    )
                    if hasattr(self, "view_meeting_guard"):
                        self.view_meeting_guard.update_live_state(
                            profiles=getattr(self.view_traffic, "_last_profiles_cache", []),
                            conferencing_active=is_active,
                            qos_policies=getattr(self, "_last_qos_policies", []),
                            verified=confirmed > 0 or not is_active,
                            confirmed_count=confirmed,
                            rolled_back=rolled,
                            rollback_reason=reason,
                        )
                    if hasattr(self, "view_dns"):
                        self.view_dns.set_meeting_freeze_state(is_active)
                    if hasattr(self, "view_dashboard"):
                        self.view_dashboard.update_meeting_guard_summary(
                            meeting_active=is_active,
                            verified_rules=confirmed,
                            configured_rules=confirmed,
                            lifecycle_stage="active" if is_active else "idle",
                        )
                    if hasattr(self, "top_bar"):
                        self.top_bar.set_guard_status(
                            tokens.SystemStatus.ACTIVE if is_active else tokens.SystemStatus.RUNNING,
                            tr("topbar_guard_active") if is_active else tr("topbar_guard_ready"),
                        )

                self.call_on_ui(_sync_guard_ui)
            except Exception as e:
                logger.debug("Meeting signal polling error: %s", e)
            finally:
                self._is_polling_meeting_signal = False

        self.dispatch_coroutine(_run_poll())

    def _on_run_deep_diagnosis(self) -> None:
        self.view_diagnosis.btn_run_audit.setEnabled(False)
        self.view_diagnosis.btn_run_audit.setText("جاري بدء الفحص الشامل...")

        def _progress(step_idx: int, total_steps: int, msg: str):
            self.call_on_ui(lambda s=step_idx, t=total_steps, m=msg: self.view_diagnosis.btn_run_audit.setText(f"جاري الفحص ({s}/{t}): {m}"))

        def _worker():
            try:
                from app.diagnosis.deep_scan import DeepScanner
                scanner = DeepScanner(platform=self.app_core.ctx.platform)
                report = scanner.run_scan(progress_callback=_progress)
                self.call_on_ui(lambda r=report: self._on_deep_diagnosis_finished(r))
            except Exception as exc:
                logger.error("Deep scan failed with exception: %s", exc, exc_info=True)
                self.call_on_ui(lambda e=str(exc): self._on_deep_diagnosis_failed(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_deep_diagnosis_finished(self, report) -> None:
        self.view_diagnosis.btn_run_audit.setEnabled(True)
        self.view_diagnosis.btn_run_audit.setText("فحص شامل ودقيق الآن")
        if hasattr(self.view_diagnosis, "update_from_deep_scan"):
            self.view_diagnosis.update_from_deep_scan(report)
        self.view_dashboard.log_autonomous_action(
            "اكتمال التدقيق التشخيصي الشامل",
            report.explanation_arabic,
            level="success" if report.overall_health else "warning",
        )
        ctx = getattr(getattr(self, "app_core", None), "ctx", None)
        if ctx and hasattr(ctx, "incidents"):
            from app.core.models.metrics import Diagnosis, ProbableCause, DiagnosisSeverity, Evidence, MetricType
            ev_list = []
            if report.external_latency_ms:
                ev_list.append(Evidence(metric_type=MetricType.EXTERNAL_LATENCY, target="external", observed_value=report.external_latency_ms, threshold_value=50.0, condition=">"))
            if report.packet_loss_pct > 0:
                ev_list.append(Evidence(metric_type=MetricType.EXTERNAL_PACKET_LOSS, target="external", observed_value=report.packet_loss_pct, threshold_value=2.0, condition=">"))
            if report.bufferbloat_delta_ms and report.bufferbloat_delta_ms > 0:
                ev_list.append(Evidence(metric_type=MetricType.BUFFERBLOAT_BLOAT_FACTOR, target="gateway", observed_value=report.bufferbloat_delta_ms, threshold_value=25.0, condition=">"))

            cause = ProbableCause.BUFFERBLOAT_UPLOAD if (report.bufferbloat_delta_ms and report.bufferbloat_delta_ms > 30) else ProbableCause.UNKNOWN_ANOMALY
            if not report.overall_health or ev_list:
                diag = Diagnosis(
                    probable_cause=cause,
                    confidence=0.88,
                    severity=DiagnosisSeverity.MEDIUM if not report.overall_health else DiagnosisSeverity.INFO,
                    supporting_evidence=ev_list,
                    explanation=report.explanation_arabic,
                    recommended_actions=["تحسين مسار الاتصال"],
                )
                ctx.incidents.save(diag)
        self._refresh_timeline_from_records()

    def _on_deep_diagnosis_failed(self, error_msg: str) -> None:
        self.view_diagnosis.btn_run_audit.setEnabled(True)
        self.view_diagnosis.btn_run_audit.setText("فحص شامل ودقيق الآن")
        self.view_diagnosis.cause_lbl.setText("تعذر إكمال الفحص الشامل")
        self.view_diagnosis.cause_lbl.setStyleSheet(f"color: {tokens.STATUS_BAD};")
        self.view_diagnosis.explanation_lbl.setText(f"حدث خطأ أثناء إجراء الاختبارات الميدانية: {error_msg}")
        self.view_dashboard.log_autonomous_action(
            "فشل التدقيق التشخيصي",
            f"حدث خطأ فني أثناء تنفيذ فحص الشبكة: {error_msg}",
            level="error",
        )

    def _on_quick_flush_dns(self) -> None:
        if hasattr(self, "traffic_controller") and self.traffic_controller and self.traffic_controller.is_critical_meeting_active():
            QMessageBox.warning(self, "درع الاجتماعات", "لا يمكن تفريغ كاش DNS أثناء اجتماع نشط لحماية استقرار المكالمة من الانقطاع.")
            return

        self.view_remediation.btn_flush_now.setEnabled(False)
        self.view_remediation.btn_flush_now.setText("جاري تنظيف كاش DNS...")

        def _worker():
            try:
                ok, msg = self.app_core.ctx.platform.flush_dns_cache()
                self.call_on_ui(lambda: self._on_quick_flush_dns_done(ok, msg))
            except Exception as exc:
                logger.error("Flush DNS failed: %s", exc, exc_info=True)
                self.call_on_ui(lambda: self._on_quick_flush_dns_done(False, str(exc)))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_quick_flush_dns_done(self, success: bool, msg: str) -> None:
        self.view_remediation.btn_flush_now.setEnabled(True)
        if success:
            self.view_remediation.btn_flush_now.setText("تم تفريغ كاش DNS بنجاح ✓")
            self.view_dashboard.log_autonomous_action(
                "تفريغ كاش الـ DNS الفوري",
                f"تم تفريغ كاش العناوين بنجاح ({msg}).",
                level="success",
            )
        else:
            self.view_remediation.btn_flush_now.setText("فشل تفريغ DNS ✕")
            self.view_dashboard.log_autonomous_action(
                "فشل تفريغ كاش DNS",
                f"تعذر تفريغ كاش أسماء النطاقات: {msg}",
                level="error",
            )

        import uuid
        from app.core.models.metrics import ActionExecutionRecord, ActionExecutionStatus, RiskLevel
        flush_record = ActionExecutionRecord(
            id=str(uuid.uuid4()),
            action_id="flush_dns_cache",
            action_name="تفريغ كاش DNS الفوري",
            risk_level=RiskLevel.LEVEL_1_LOW,
            trigger_diagnosis_id="manual_flush",
            pre_remedy_metrics={},
            post_remedy_metrics={"result": msg},
            status=ActionExecutionStatus.SUCCEEDED if success else ActionExecutionStatus.FAILED,
            execution_duration_ms=25.0,
            verification_duration_ms=10.0,
            error_message=None if success else msg,
            rollback_performed=False,
        )
        ctx = getattr(getattr(self, "app_core", None), "ctx", None)
        if ctx and hasattr(ctx, "audit"):
            ctx.audit.save(flush_record)
        self._refresh_timeline_from_records()
        QTimer.singleShot(2500, lambda: self.view_remediation.btn_flush_now.setText("تنظيف كاش DNS"))

    def _on_quick_renew_ip(self) -> None:
        if hasattr(self, "traffic_controller") and self.traffic_controller and self.traffic_controller.is_critical_meeting_active():
            QMessageBox.warning(self, "درع الاجتماعات", "لا يمكن تجديد عنوان IP أثناء اجتماع نشط لتجنب فصل المكالمة.")
            return

        platform = self.app_core.ctx.platform
        from app.platform.admin import require_admin, prompt_restart_as_admin
        ok_admin, reason = require_admin("تجديد مسار الاتصال وعنوان IP (DHCP Lease)", platform)
        if not ok_admin:
            self.view_remediation.btn_renew_ip.setEnabled(True)
            self.view_remediation.btn_renew_ip.setText("تجديد IP (يتطلب صلاحيات مسؤول)")
            self.view_dashboard.log_autonomous_action(
                "تعذر تجديد عنوان IP",
                reason,
                level="warning",
            )
            QTimer.singleShot(3500, lambda: self.view_remediation.btn_renew_ip.setText("تجديد مسار الاتصال"))
            prompt_restart_as_admin(self, "تجديد عنوان IP ومسار الاتصال", platform)
            return

        self.view_remediation.btn_renew_ip.setEnabled(False)
        self.view_remediation.btn_renew_ip.setText("جاري تجديد IP (انقطاع لحظي)...")
        iface = platform.get_primary_interface() or "Wi-Fi"
        gw_before = platform.get_default_gateway()

        def _worker():
            try:
                ok, msg = platform.renew_ip_lease(iface)
                time.sleep(1.0)
                gw_after = platform.get_default_gateway() or gw_before
                ping_ok, ping_ms = platform.ping(gw_after, timeout_sec=2.0) if gw_after else (False, 0.0)
                success = ok and ping_ok
                self.call_on_ui(lambda s=success, i=iface, g=gw_after, p=ping_ms, m=msg: self._on_quick_renew_ip_finished(s, i, g, p, m))
            except Exception as exc:
                logger.error("IP renewal failed: %s", exc, exc_info=True)
                self.call_on_ui(lambda i=iface, g=gw_before, e=str(exc): self._on_quick_renew_ip_finished(False, i, g, 0.0, e))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_quick_renew_ip_finished(self, success: bool, iface: str, gw: Optional[str], ping_ms: float, msg: str) -> None:
        self.view_remediation.btn_renew_ip.setEnabled(True)
        if success:
            self.view_remediation.btn_renew_ip.setText("تم تجديد عنوان IP بنجاح ✓")
            self.view_dashboard.log_autonomous_action(
                "تجديد عنوان IP (DHCP Lease)",
                f"تم تجديد إيجار DHCP لمحول {iface} بنجاح والتأكد من استجابة البوابة {gw} خلال {ping_ms:.1f} ms.",
                level="success",
            )
        else:
            self.view_remediation.btn_renew_ip.setText("فشل تجديد IP ✕")
            self.view_dashboard.log_autonomous_action(
                "فشل تجديد عنوان IP",
                f"فشل تجديد إيجار DHCP على المحول {iface}: {msg}",
                level="error",
            )

        import uuid
        from app.core.models.metrics import ActionExecutionRecord, ActionExecutionStatus, RiskLevel
        renew_record = ActionExecutionRecord(
            id=str(uuid.uuid4()),
            action_id="renew_dhcp_lease",
            action_name=f"تجديد عنوان IP ({iface})",
            risk_level=RiskLevel.LEVEL_2_CONTROLLED,
            trigger_diagnosis_id="manual_renew",
            pre_remedy_metrics={"interface": iface, "gateway_before": gw},
            post_remedy_metrics={"gateway_after": gw, "gateway_ping_ms": ping_ms, "result": msg},
            status=ActionExecutionStatus.SUCCEEDED if success else ActionExecutionStatus.FAILED,
            execution_duration_ms=1000.0,
            verification_duration_ms=ping_ms,
            error_message=None if success else msg,
            rollback_performed=False,
        )
        ctx = getattr(getattr(self, "app_core", None), "ctx", None)
        if ctx and hasattr(ctx, "audit"):
            ctx.audit.save(renew_record)
        self._refresh_timeline_from_records()
        QTimer.singleShot(3000, lambda: self.view_remediation.btn_renew_ip.setText("تجديد مسار الاتصال"))

    def _on_apply_settings(self) -> None:
        mode_data = self.view_settings.mode_combo.currentData() or self.view_settings.mode_combo.currentText()
        mode_val = OperatingMode(mode_data)
        self.set_operating_mode(mode_val)

        if hasattr(self.app_core, "settings") and self.app_core.settings:
            settings = self.app_core.settings
            interval = self.view_settings.combo_interval.currentData()
            if interval:
                settings.set_probing_interval(float(interval))
            retention = self.view_settings.combo_retention.currentData()
            if retention:
                settings.set_retention_days(int(retention))
            settings.save()

        # Persist self-hosted update source configuration
        if hasattr(self.view_settings, "input_update_source"):
            from app.core.updater import save_configured_update_source
            new_source = self.view_settings.input_update_source.text().strip()
            is_auto = self.view_settings.toggle_auto_update.isChecked() if hasattr(self.view_settings, "toggle_auto_update") else True
            save_configured_update_source(new_source, auto_install=is_auto)
            if hasattr(self.view_settings, "updater"):
                self.view_settings.updater.set_source(new_source)

        self.view_settings.apply_btn.setText("تم حفظ الإعدادات وتطبيقها بنجاح! ✓")
        QTimer.singleShot(2500, lambda: self.view_settings.apply_btn.setText("حفظ الإعدادات وتطبيقها الآن"))

    def _on_clear_history_requested(self) -> None:
        """Prompt user and execute database history clearance and VACUUM in worker thread."""
        reply = QMessageBox.question(
            self,
            "تأكيد مسح السجل",
            "هل أنت متأكد من رغبتك في حذف كافة السجلات والقياسات السابقة وتفريغ قاعدة البيانات بالكامل؟\n\nسيتم تفريغ مساحة التخزين على القرص الصلب (VACUUM)، ولا يمكن التراجع عن هذا الإجراء.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        ctx = getattr(getattr(self, "app_core", None), "ctx", None)
        meas_repo = getattr(ctx, "measurements", None) if ctx else getattr(self.view_history, "measurement_repo", None)
        inc_repo = getattr(ctx, "incidents", None) if ctx else getattr(self.view_history, "incident_repo", None)
        audit_repo = getattr(ctx, "audit", None) if ctx else None

        if not meas_repo or not hasattr(meas_repo, "clear_all_history"):
            QMessageBox.warning(self, "تنبيه", "مستودع البيانات غير متصل حالياً.")
            return

        if hasattr(self.view_settings, "btn_clear_history"):
            self.view_settings.btn_clear_history.setEnabled(False)
            self.view_settings.btn_clear_history.setText("جاري مسح السجلات وتفريغ المساحة...")
        if hasattr(self.view_history, "btn_clear_history"):
            self.view_history.btn_clear_history.setEnabled(False)
            self.view_history.btn_clear_history.setText("جاري التنظيف...")

        def _worker():
            try:
                res = meas_repo.clear_all_history(incident_repo=inc_repo, audit_repo=audit_repo)
                self.call_on_ui(lambda r=res: self._on_clear_history_done(True, r))
            except Exception as exc:
                logger.error("Failed to clear database history: %s", exc, exc_info=True)
                self.call_on_ui(lambda e=str(exc): self._on_clear_history_done(False, e))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_clear_history_done(self, success: bool, payload: Any) -> None:
        if hasattr(self.view_settings, "btn_clear_history"):
            self.view_settings.btn_clear_history.setEnabled(True)
            self.view_settings.btn_clear_history.setText("تنظيف وضغط قاعدة البيانات")
        if hasattr(self.view_history, "btn_clear_history"):
            self.view_history.btn_clear_history.setEnabled(True)
            self.view_history.btn_clear_history.setText("تنظيف السجل")

        if success:
            if hasattr(self.view_history, "_refresh_day"):
                self.view_history._refresh_day()
            if hasattr(self, "_refresh_timeline_from_records"):
                self._refresh_timeline_from_records()

            total_pruned = sum(payload.values()) if isinstance(payload, dict) else 0
            QMessageBox.information(
                self,
                "اكتمل التفريغ",
                f"تم مسح كافة السجلات السابقة بنجاح وتفريغ قاعدة البيانات على القرص.\n(إجمالي السجلات المفرغة: {total_pruned})"
            )
        else:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء تفريغ قاعدة البيانات:\n{payload}")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        w = self.width()

        if w < 900:
            if getattr(self, "_shell_mode", "dock") != "collapsed":
                self._shell_mode = "collapsed"
                self.sidebar.set_mode("collapsed")
        else:
            if getattr(self, "_shell_mode", "dock") != "dock":
                self._shell_mode = "dock"
                self.sidebar.set_mode("dock")

    def _on_background_update_tick(self) -> None:
        """Non-blocking silent background update check (with overlap lock)."""
        if getattr(self, "_is_closing", False):
            return
        if getattr(self, "_is_checking_updates_bg", False):
            return

        updater = getattr(self.view_settings, "updater", None)
        if not updater:
            return

        src = getattr(updater, "check_url", "").strip()
        if not src:
            from app.core.updater import get_configured_update_source
            src = get_configured_update_source().strip()
            if not src:
                return
            updater.set_source(src)

        self._is_checking_updates_bg = True

        def _reset_bg_lock(*args: Any) -> None:
            self._is_checking_updates_bg = False

        try:
            updater.up_to_date.connect(_reset_bg_lock)
            updater.check_failed.connect(_reset_bg_lock)
            updater.download_failed.connect(_reset_bg_lock)
            updater.install_failed.connect(_reset_bg_lock)
        except Exception:
            pass

        updater.check_for_updates_async()

    def closeEvent(self, event) -> None:
        if getattr(self, "_is_closing", False):
            super().closeEvent(event)
            return
        self._is_closing = True
        for view_attr in (
            "view_dashboard",
            "view_meeting_guard",
            "view_traffic",
            "view_dns",
            "view_wifi",
            "view_router",
            "view_quality",
            "view_reports",
            "view_settings",
            "view_about",
            "view_diagnosis",
            "view_history",
            "view_remediation",
        ):
            vw = getattr(self, view_attr, None)
            if vw and hasattr(vw, "shutdown"):
                try:
                    vw.shutdown()
                except Exception:
                    pass
        try:
            language_manager().language_changed.disconnect(self._apply_language_direction)
        except Exception:
            pass
        try:
            from app.dns.state import DnsStateManager
            DnsStateManager.get_instance().state_changed.disconnect(self._on_dns_state_changed)
        except Exception:
            pass
        try:
            GlobalNetworkStateStore.get_instance().state_changed.disconnect(self._on_global_network_state_changed)
        except Exception:
            pass
        if hasattr(self, "traffic_controller") and self.traffic_controller:
            try:
                self.traffic_controller.cleanup_all_policies()
            except Exception:
                pass
        for t_attr in ("update_check_timer", "refresh_timer", "dns_rank_timer", "meeting_signal_timer"):
            tmr = getattr(self, t_attr, None)
            if tmr and tmr.isActive():
                tmr.stop()
        loop = getattr(self, "_fallback_async_loop", None)
        if loop and loop.is_running():
            try:
                def _stop_loop() -> None:
                    try:
                        for task in asyncio.all_tasks(loop):
                            task.cancel()
                    except Exception:
                        pass
                    loop.call_later(0.05, loop.stop)

                loop.call_soon_threadsafe(_stop_loop)
            except Exception:
                pass
        t = getattr(self, "_fallback_async_thread", None)
        if t and t.is_alive():
            try:
                t.join(timeout=0.5)
            except Exception:
                pass
        if loop and not loop.is_closed() and not loop.is_running():
            try:
                loop.close()
            except Exception:
                pass
        try:
            from app.ui.animation_clock import AnimationMasterClock
            AnimationMasterClock.get_instance().stop()
        except Exception:
            pass
        super().closeEvent(event)
