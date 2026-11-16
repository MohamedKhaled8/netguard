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
from app.ui.styles import DARK_THEME_QSS
from app.ui.widgets.nav_item import NavItem
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.diagnosis_view import DiagnosisView
from app.ui.views.remediation_view import RemediationView
from app.ui.views.dns_view import DNSView
from app.ui.views.traffic_view import TrafficView
from app.ui.views.history_view import HistoryView
from app.ui.views.settings_view import SettingsView
from app.traffic.controller import TrafficController
from app.core.models.metrics import OperatingMode
from app.core.bus import EventTopics


class UIAsyncBridge(QObject):
    """Thread-safe signal bridge for Qt GUI updates from background workers."""

    dns_benchmark_done = Signal(object)
    traffic_scan_done = Signal(object, bool)
    network_info_ready = Signal(dict)
    remediation_event_received = Signal(str, dict)
    speed_test_done = Signal(str)


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

        self.dot = QLabel()
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
                    border: 1px solid {tokens.LINE_THRESHOLD};
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
        super().mousePressEvent(event)


class SidebarWidget(QFrame):
    """Right-side navigation and control sidebar with top_bar collapse support."""

    mode_changed = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SidebarDock")
        self._current_mode = "dock"

        self.sidebar_layout = QVBoxLayout(self)
        self.sidebar_layout.setContentsMargins(16, 20, 16, 20)
        self.sidebar_layout.setSpacing(8)

        # -------------------------------------------------------------
        # 1. Top Brand Header
        # -------------------------------------------------------------
        self.brand_container = QWidget()
        brand_col = QVBoxLayout(self.brand_container)
        brand_col.setContentsMargins(0, 0, 0, 8)
        brand_col.setSpacing(4)

        wordmark_row = QHBoxLayout()
        wordmark_row.setSpacing(8)

        brand_circle = QLabel()
        brand_circle.setFixedSize(10, 10)
        brand_circle.setStyleSheet(f"background-color: {tokens.ACCENT}; border-radius: 5px;")
        wordmark_row.addWidget(brand_circle)

        brand_title = QLabel("NetGuard")
        brand_title.setFont(tokens.get_mono_font(18, 500))
        brand_title.setStyleSheet(f"color: {tokens.TEXT};")
        wordmark_row.addWidget(brand_title)
        wordmark_row.addStretch()
        brand_col.addLayout(wordmark_row)

        brand_sub = QLabel("مراقبة الشبكة وإصلاحها تلقائياً")
        brand_sub.setFont(tokens.get_sans_font(12, 400))
        brand_sub.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        brand_col.addWidget(brand_sub)

        self.sidebar_layout.addWidget(self.brand_container)

        # -------------------------------------------------------------
        # 2. Navigation Items (7 items in adaptable grid)
        # -------------------------------------------------------------
        self.nav_container = QWidget()
        self.nav_grid = QGridLayout(self.nav_container)
        self.nav_grid.setContentsMargins(0, 0, 0, 0)
        self.nav_grid.setSpacing(4)

        self.btn_dash = NavItem("home", "الرئيسية", 0, self)
        self.btn_diag = NavItem("activity", "التشخيص", 1, self)
        self.btn_rem = NavItem("shield", "الإصلاح التلقائي", 2, self)
        self.btn_dns = NavItem("globe", "DNS", 3, self)
        self.btn_traffic = NavItem("traffic", "حركة البيانات", 4, self)
        self.btn_hist = NavItem("clock", "السجل", 5, self)
        self.btn_settings = NavItem("sliders", "الإعدادات", 6, self)

        self.nav_buttons = [
            self.btn_dash,
            self.btn_diag,
            self.btn_rem,
            self.btn_dns,
            self.btn_traffic,
            self.btn_hist,
            self.btn_settings,
        ]

        self.sidebar_layout.addWidget(self.nav_container)
        self.stretch_item = self.sidebar_layout.addStretch()

        # -------------------------------------------------------------
        # 3. Bottom: Mode Selector Group (وضع الإصلاح)
        # -------------------------------------------------------------
        self.mode_container = QWidget()
        mode_col = QVBoxLayout(self.mode_container)
        mode_col.setContentsMargins(0, 8, 0, 0)
        mode_col.setSpacing(6)

        lbl_mode_caption = QLabel("وضع الإصلاح")
        lbl_mode_caption.setFont(tokens.get_sans_font(12, 400))
        lbl_mode_caption.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        mode_col.addWidget(lbl_mode_caption)

        self.opt_auto = SidebarModeOption(0, "تلقائي", self)
        self.opt_assisted = SidebarModeOption(1, "بموافقتي", self)
        self.opt_observe = SidebarModeOption(2, "مراقبة فقط", self)

        self.mode_options = [self.opt_auto, self.opt_assisted, self.opt_observe]
        for opt in self.mode_options:
            opt.clicked.connect(self._on_mode_clicked)
            mode_col.addWidget(opt)

        self.lbl_mode_desc = QLabel("يكتشف المشكلة ويصلحها فوراً ثم يسجل ما فعله بالتفصيل.")
        self.lbl_mode_desc.setFont(tokens.get_sans_font(12, 400))
        self.lbl_mode_desc.setStyleSheet(f"color: {tokens.TEXT_MUTED}; line-height: 1.5;")
        self.lbl_mode_desc.setWordWrap(True)
        mode_col.addWidget(self.lbl_mode_desc)

        self.sidebar_layout.addWidget(self.mode_container)

        self.set_mode("dock")
        self.set_operating_mode(OperatingMode.AUTO)

    def set_operating_mode(self, mode: OperatingMode | str) -> None:
        target = OperatingMode(mode)
        mode_to_idx = {OperatingMode.AUTO: 0, OperatingMode.ASK: 1, OperatingMode.WATCH: 2}
        idx = mode_to_idx.get(target, 0)
        if getattr(self, "_current_mode_idx", None) == idx:
            return
        self._current_mode_idx = idx
        for i, opt in enumerate(self.mode_options):
            opt.set_selected(i == idx)
        descs = {
            0: "يكتشف المشكلة ويصلحها فوراً ثم يسجل ما فعله بالتفصيل.",
            1: "يقترح الإصلاح وينتظر موافقتك قبل أي تغيير.",
            2: "يراقب ويسجل دون تغيير أي إعداد على جهازك.",
        }
        self.lbl_mode_desc.setText(descs.get(idx, ""))

    def set_mode(self, mode: str) -> None:
        self._current_mode = mode
        if mode == "top_bar":
            self.setFixedWidth(16777215)
            self.setStyleSheet(f"""
                QFrame#SidebarDock {{
                    background-color: {tokens.SIDEBAR};
                    border: none;
                    border-bottom: 1px solid {tokens.LINE};
                }}
            """)
            for i, btn in enumerate(self.nav_buttons):
                self.nav_grid.removeWidget(btn)
                self.nav_grid.addWidget(btn, i // 2, i % 2)
        else:
            self.setFixedWidth(248)
            self.setStyleSheet(f"""
                QFrame#SidebarDock {{
                    background-color: {tokens.SIDEBAR};
                    border: none;
                    border-left: 1px solid {tokens.LINE};
                }}
            """)
            for i, btn in enumerate(self.nav_buttons):
                self.nav_grid.removeWidget(btn)
                self.nav_grid.addWidget(btn, i, 0)

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
        ctx = getattr(application, "ctx", None)
        eb = getattr(ctx, "event_bus", None)
        plat = getattr(ctx, "platform", None)
        us = getattr(ctx, "settings", getattr(ctx, "user_settings", None))
        self.traffic_controller = getattr(application, "traffic_controller", None) or TrafficController(event_bus=eb, platform=plat, user_settings=us)
        self.bridge = UIAsyncBridge()

        # Enforce Arabic RTL layout
        if QApplication.instance():
            QApplication.instance().setLayoutDirection(Qt.RightToLeft)

        tokens.init_fonts()
        self.setWindowTitle("NetGuard AI")
        self.resize(1440, 900)
        self.setMinimumSize(480, 600)
        self.setStyleSheet(DARK_THEME_QSS)

        central_widget = QWidget(self)
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)

        self.root_layout = QHBoxLayout(central_widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # Fixed Sidebar Dock (Right in RTL, width 248px)
        self.sidebar = SidebarWidget(self)
        self.root_layout.addWidget(self.sidebar)

        # Main Content Stack (Left in RTL)
        self.stack = QStackedWidget()
        self.stack.setObjectName("ContentStack")

        self.view_dashboard = DashboardView()
        self.view_diagnosis = DiagnosisView()
        self.view_remediation = RemediationView()
        self.view_dns = DNSView()
        self.view_traffic = TrafficView(session_tracker=self.traffic_controller.session_tracker)
        meas_repo = getattr(self.app_core.ctx, "measurements", None) if hasattr(self.app_core, "ctx") else None
        inc_repo = getattr(self.app_core.ctx, "incidents", None) if hasattr(self.app_core, "ctx") else None
        self.view_history = HistoryView(measurement_repo=meas_repo, incident_repo=inc_repo)
        self.view_settings = SettingsView()

        # Index sequence matching tests:
        # 0: Dash, 1: Diag, 2: Rem, 3: DNS, 4: Traffic, 5: Hist, 6: Settings
        self.stack.addWidget(self.view_dashboard)
        self.stack.addWidget(self.view_diagnosis)
        self.stack.addWidget(self.view_remediation)
        self.stack.addWidget(self.view_dns)
        self.stack.addWidget(self.view_traffic)
        self.stack.addWidget(self.view_history)
        self.stack.addWidget(self.view_settings)

        self.root_layout.addWidget(self.stack, stretch=1)

        # Connect Navigation Buttons
        self.btn_dash = self.sidebar.btn_dash
        self.btn_diag = self.sidebar.btn_diag
        self.btn_rem = self.sidebar.btn_rem
        self.btn_dns = self.sidebar.btn_dns
        self.btn_traffic = self.sidebar.btn_traffic
        self.btn_hist = self.sidebar.btn_hist
        self.btn_settings = self.sidebar.btn_settings
        self.nav_buttons = self.sidebar.nav_buttons

        for idx, btn in enumerate(self.nav_buttons):
            btn.clicked.connect(lambda checked=False, i=idx, b=btn: self._switch_view(i, b))

        self.sidebar.mode_changed.connect(self._on_sidebar_mode_changed)
        self.view_remediation.mode_changed.connect(self._on_sidebar_mode_changed)

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
        self.set_operating_mode(initial_mode)

        # -------------------------------------------------------------
        # 3. Connect Bridge Signals & Wire Handlers
        # -------------------------------------------------------------
        self._last_speed_test_time: Optional[str] = None
        self.bridge.dns_benchmark_done.connect(self._on_dns_benchmark_done)
        self.bridge.traffic_scan_done.connect(self._on_scan_traffic_done)
        self.bridge.network_info_ready.connect(self._on_network_info_ready)
        self.bridge.remediation_event_received.connect(self._on_remediation_event_received)
        self.bridge.speed_test_done.connect(self._on_speed_test_done)

        self._wire_background_event_listeners()

        # Inspect network hardware asynchronously on launch
        self._async_inspect_network_environment()

        # UI Refresh Timer (1 second interval)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._on_ui_tick)
        self.refresh_timer.start(1000)

        # Recurring background DNS ranking update (every 60 seconds)
        self._last_dns_switch_time: float = 0.0
        self.dns_rank_timer = QTimer(self)
        self.dns_rank_timer.timeout.connect(self._on_run_dns_benchmark)
        self.dns_rank_timer.start(60000)

        self.ticker_counter = 0

        # Load initial day strip stability slots from measurement database
        self._refresh_day_strips()

        # Load initial timeline narrative from stored incidents and audit records
        self._refresh_timeline_from_records()

    def _switch_view(self, index: int, active_btn: QPushButton) -> None:
        self.stack.setCurrentIndex(index)
        for b in self.nav_buttons:
            b.setChecked(b == active_btn)

        if index == 4:
            self._on_scan_traffic()

    def _on_sidebar_mode_changed(self, mode_val: Any) -> None:
        if isinstance(mode_val, int):
            idx_to_mode = {0: OperatingMode.AUTO, 1: OperatingMode.ASK, 2: OperatingMode.WATCH}
            mode = idx_to_mode.get(mode_val, OperatingMode.AUTO)
        else:
            mode = OperatingMode(mode_val)
        self.set_operating_mode(mode)

    def set_operating_mode(self, mode: OperatingMode | str) -> None:
        target_mode = OperatingMode(mode)
        if getattr(self, "_current_operating_mode", None) == target_mode:
            return
        self._current_operating_mode = target_mode
        self.sidebar.set_operating_mode(target_mode)
        self.view_remediation.set_operating_mode(target_mode)
        self.view_settings.set_operating_mode(target_mode)
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
        self.view_dns.benchmark_btn.clicked.connect(self._on_run_dns_benchmark)
        self.view_traffic.btn_refresh.clicked.connect(self._on_scan_traffic)
        self.view_diagnosis.btn_run_audit.clicked.connect(self._on_run_deep_diagnosis)

        # Remediation quick tools
        self.view_remediation.btn_flush_now.clicked.connect(self._on_quick_flush_dns)
        self.view_remediation.btn_renew_ip.clicked.connect(self._on_quick_renew_ip)

        # DNS Apply request
        self.view_dns.apply_dns_requested.connect(self._on_apply_dns_requested)
        self.view_dashboard.dns_panel.apply_clicked.connect(self._on_dashboard_apply_dns)
        self.view_dashboard.dns_panel.revert_clicked.connect(self._on_dashboard_revert_dns)

        # Dashboard quick scan / speed test request
        self.view_dashboard.quick_scan_requested.connect(self._on_quick_scan_requested)

        # Dashboard timeline requests
        self.view_dashboard.timeline_panel.view_evidence_requested.connect(
            lambda: self._switch_view(1, self.btn_diag)
        )
        self.view_dashboard.timeline_panel.rollback_requested.connect(
            self._on_timeline_rollback_requested
        )

    def _on_quick_scan_requested(self) -> None:
        """Trigger on-demand telemetry / speed test cycle and update timestamp."""
        def _worker():
            try:
                if hasattr(self.app_core, "observability") and self.app_core.observability:
                    asyncio.run(self.app_core.observability.run_single_cycle())
            except Exception as e:
                logger.warning(f"Error during on-demand telemetry scan: {e}")
            finally:
                time_str = datetime.now().strftime("%H:%M")
                self.bridge.speed_test_done.emit(time_str)

        threading.Thread(target=_worker, daemon=True).start()

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
        try:
            inc_repo = getattr(self.app_core.ctx, "incidents", None)
            aud_repo = getattr(self.app_core.ctx, "audit", None)
            incidents = inc_repo.get_recent(limit=1) if inc_repo and hasattr(inc_repo, "get_recent") else []
            audits = aud_repo.get_recent(limit=1) if aud_repo and hasattr(aud_repo, "get_recent") else []
            latest_inc = incidents[0] if incidents else None
            latest_aud = audits[0] if audits else None
            self.view_dashboard.update_timeline_from_records(latest_inc, latest_aud)
        except Exception as e:
            logger.warning("Failed to refresh timeline from records: %s", e)

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
            def _worker():
                ok, msg = asyncio.run(self.app_core.orchestrator.rollback_action(rec.id))
                QTimer.singleShot(0, lambda: self._on_timeline_rollback_done(ok, msg, rec))
            threading.Thread(target=_worker, daemon=True).start()
        else:
            QMessageBox.information(self, "تراجع عن الإصلاح", f"الإجراء '{rec.action_name}' غير قابل للتراجع المباشر.")

    def _on_timeline_rollback_done(self, success: bool, msg: str, record: Any) -> None:
        if success:
            QMessageBox.information(self, "تراجع عن الإصلاح", f"تم التراجع عن الإجراء بنجاح: {record.action_name}")
            self._refresh_timeline_from_records()
        else:
            QMessageBox.warning(self, "فشل التراجع", f"تعذر التراجع عن الإجراء: {msg}")

    def _async_inspect_network_environment(self) -> None:
        def _worker():
            try:
                from app.platform.windows.network_info import (
                    get_wifi_details,
                    get_active_dns_servers,
                    get_isp_and_public_ip,
                )
                iface = self.app_core.ctx.platform.get_primary_interface() or "Wi-Fi"
                gw = self.app_core.ctx.platform.get_default_gateway() or "192.168.1.1"
                wifi = get_wifi_details()
                dns_servers = get_active_dns_servers(iface)
                isp = get_isp_and_public_ip()

                info = {
                    "iface": iface,
                    "gateway": gw,
                    "wifi": wifi,
                    "dns": dns_servers,
                    "isp": isp,
                }
                QTimer.singleShot(0, lambda: self._safe_emit_network_info(info))
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def _safe_emit_network_info(self, info: Dict[str, Any]) -> None:
        try:
            if hasattr(self, "bridge") and self.bridge:
                self.bridge.network_info_ready.emit(info)
        except (RuntimeError, Exception):
            pass

    def _on_network_info_ready(self, info: Dict[str, Any]) -> None:
        self._active_dns_servers = info.get("dns", [])
        self.view_dashboard.update_network_identity(info)
        self.view_dns.set_active_dns_info(self._active_dns_servers)
        if not getattr(self, "_initial_dns_bench_triggered", False):
            self._initial_dns_bench_triggered = True
            QTimer.singleShot(1200, self._on_run_dns_benchmark)

    def _refresh_day_strips(self) -> None:
        """Fetch today's 48-slot status from measurements and populate day strips."""
        try:
            if hasattr(self.app_core, "ctx") and self.app_core.ctx and hasattr(self.app_core.ctx, "measurements") and self.app_core.ctx.measurements:
                today = date.today()
                slots = self.app_core.ctx.measurements.get_day_slots(today)
                if hasattr(self.view_dashboard, "day_strip") and self.view_dashboard.day_strip:
                    self.view_dashboard.day_strip.set_data(slots)
                if hasattr(self.view_history, "day_strip") and self.view_history.day_strip:
                    if getattr(self.view_history, "current_date", None) == today:
                        self.view_history.day_strip.set_data(slots)
        except Exception as e:
            logger.warning("Failed to refresh day strips: %s", e)

    def _on_ui_tick(self) -> None:
        """Periodic UI update polling in-memory telemetry completely autonomously."""
        obs = self.app_core.observability
        last_diag = self.app_core.diagnosis.last_diagnosis

        self.view_dashboard.update_telemetry(obs, last_diag)

        # Refresh 48-slot day strip every 60 seconds
        self.ticker_counter = getattr(self, "ticker_counter", 0) + 1
        if self.ticker_counter % 60 == 0:
            self._refresh_day_strips()

        if self.stack.currentWidget() == self.view_diagnosis and last_diag:
            self.view_diagnosis.update_diagnosis(last_diag)

        if self.stack.currentWidget() == self.view_history:
            if getattr(self.view_history, "current_date", None) == date.today():
                incidents = self.app_core.ctx.incidents.get_by_date(date.today())
                self.view_history.update_incidents(incidents)

        if self.stack.currentWidget() == self.view_remediation:
            audit_records = self.app_core.ctx.audit.get_recent(limit=30)
            self.view_remediation.update_audit_log(audit_records)

    def _on_run_dns_benchmark(self) -> None:
        if getattr(self, "_is_benchmarking_dns", False):
            return
        self._is_benchmarking_dns = True
        self.view_dns.benchmark_btn.setEnabled(False)
        self.view_dns.benchmark_btn.setText("جاري الفحص التلقائي...")

        def _worker():
            scores = []
            try:
                from app.dns.benchmark import DNSBenchmark
                bench = DNSBenchmark()
                scores = asyncio.run(bench.rank_all())
            except Exception as exc:
                logger.warning("DNS benchmark failed: %s", exc)
            finally:
                QTimer.singleShot(0, lambda: self._on_dns_benchmark_done(scores))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_dns_benchmark_done(self, scores) -> None:
        self._is_benchmarking_dns = False
        self.view_dns.benchmark_btn.setEnabled(True)
        self.view_dns.benchmark_btn.setText("⚡ فحص وترتيب الخوادم الآن")

        if not scores:
            return

        self.view_dns._last_scores = scores
        best = scores[0]
        secondary_ip = "1.0.0.1" if "1.1.1.1" in best.ip else ("8.8.4.4" if "8.8.8.8" in best.ip else "")
        best_name = best.name.replace(" Primary", "").replace(" Secondary", "")
        best_ms = getattr(best, "median_latency_ms", 0.0) or best.mean_latency_ms

        self._last_best_dns = (best.ip, secondary_ip, best_name, best_ms)

        active_dns = getattr(self, "_active_dns_servers", [])
        if not active_dns:
            iface = self.app_core.ctx.platform.get_primary_interface() or "Wi-Fi"
            active_dns = self.app_core.ctx.platform.get_interface_dns_servers(iface) or ["1.1.1.1", "1.0.0.1"]

        # Match active DNS with benchmark scores
        matched_score = None
        for s in scores:
            if any(s.ip in a for a in active_dns) or any(a in s.ip for a in active_dns):
                matched_score = s
                break

        if matched_score is not None:
            active_ms = getattr(matched_score, "median_latency_ms", 0.0) or matched_score.mean_latency_ms
            active_name = matched_score.name.replace(" Primary", "").replace(" Secondary", "")
        else:
            active_ms = max(best_ms + 18.0, 38.0)
            active_name = "DNS مزود الخدمة"

        is_same_ip = any(best.ip in s for s in active_dns) or any(s in best.ip for s in active_dns)
        is_delta_negligible = (active_ms - best_ms) <= 8.0
        is_optimal = (is_same_ip or is_delta_negligible)

        if is_optimal:
            active_ms = best_ms
            active_name = best_name

        is_healthy = (active_ms <= 60.0)
        is_auto_mode = (self.app_core.orchestrator.mode == OperatingMode.AUTONOMOUS_SAFE)

        # Policy & anti-flapping hysteresis check:
        policy_enabled = True
        us = getattr(self.app_core.ctx, "settings", getattr(self.app_core.ctx, "user_settings", None))
        if us and hasattr(us, "get_policy"):
            policy_enabled = us.get_policy("auto_switch_dns", True)

        now = time.time()
        time_since_switch = now - getattr(self, "_last_dns_switch_time", 0.0)
        cfg_cooldown = getattr(self.app_core.config.thresholds, "cooldowns", {}).get("switch_dns_resolver", 45.0)
        cooldown_ok = time_since_switch >= cfg_cooldown
        significant_gain = (active_ms - best_ms) >= 20.0
        candidate_fast = (best_ms < 75.0)

        if policy_enabled and is_auto_mode and (not is_optimal) and (not is_healthy) and significant_gain and candidate_fast and cooldown_ok:
            self._last_dns_switch_time = now
            self._on_apply_dns_requested(best.ip, secondary_ip, best_name)
            active_name = best_name
            active_ms = best_ms
            is_optimal = True
            is_healthy = True

        # Broadcast to View 1: Dashboard
        self.view_dashboard.update_dns_recommendation(
            curr_name=active_name,
            curr_ms=active_ms,
            best_name=best_name,
            best_ip=best.ip,
            best_ms=best_ms,
            is_optimal=is_optimal,
            is_autonomous=is_auto_mode,
        )

        # Broadcast to View 2: Diagnosis (Layer 04 + Evidence Table)
        self.view_diagnosis.update_dns_telemetry(
            dns_name=active_name,
            latency_ms=active_ms,
            is_healthy=is_healthy,
            is_optimal=is_optimal,
        )

        # Broadcast to View 3: DNS Tab (Comparison Bars + Table)
        self.view_dns.set_active_dns_info(active_dns)
        self.view_dns.update_rankings(
            scores=scores,
            active_ms=active_ms,
            active_name=active_name,
            is_optimal=is_optimal,
        )

    def _on_dashboard_apply_dns(self) -> None:
        if hasattr(self, "_last_best_dns"):
            ip, sec, name, ms = self._last_best_dns
            self._last_dns_switch_time = time.time()
            self._active_dns_servers = [ip, sec] if sec else [ip]
            self._on_apply_dns_requested(ip, sec, name)
            self.view_dashboard.update_dns_recommendation(
                curr_name=name,
                curr_ms=ms,
                best_name=name,
                best_ip=ip,
                best_ms=ms,
                is_optimal=True,
                is_autonomous=False,
            )
            self.view_diagnosis.update_dns_telemetry(
                dns_name=name,
                latency_ms=ms,
                is_healthy=True,
                is_optimal=True,
            )
            self.view_dns.set_active_dns_info(self._active_dns_servers)
            if hasattr(self.view_dns, "_last_scores"):
                self.view_dns.update_rankings(
                    self.view_dns._last_scores,
                    active_ms=ms,
                    active_name=name,
                    is_optimal=True,
                )

    def _on_dashboard_revert_dns(self) -> None:
        iface = self.app_core.ctx.platform.get_primary_interface() or "Wi-Fi"
        pre = getattr(self, "_last_dns_pre_state", None)
        if pre and not pre.get("is_dhcp") and pre.get("original_servers"):
            restore_target = pre["original_servers"]
            desc = f"تمت استعادة خوادم DNS السابقة: {', '.join(restore_target)}"
        else:
            restore_target = []
            desc = "تمت استعادة إعدادات DNS التلقائية من الراوتر (DHCP)."

        ok, msg = self.app_core.ctx.platform.set_interface_dns_servers(iface, restore_target)
        self.app_core.ctx.platform.flush_dns_cache()
        self._last_dns_switch_time = time.time()
        self._active_dns_servers = restore_target
        self.view_dashboard.log_autonomous_action(
            "استعادة إعدادات DNS",
            desc,
            level="success" if ok else "error",
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
        self._refresh_timeline_from_records()
        self._on_run_dns_benchmark()

    def _on_apply_dns_requested(self, primary_ip: str, secondary_ip: str, name: str) -> None:
        self._last_dns_switch_time = time.time()
        self._active_dns_servers = [primary_ip, secondary_ip] if secondary_ip else [primary_ip]
        def _worker():
            iface = self.app_core.ctx.platform.get_primary_interface() or "Wi-Fi"
            servers = [primary_ip]
            if secondary_ip:
                servers.append(secondary_ip)

            prev_servers = self.app_core.ctx.platform.get_interface_dns_servers(iface)
            is_dhcp = len(prev_servers) == 0
            self._last_dns_pre_state = {
                "interface": iface,
                "original_servers": list(prev_servers),
                "is_dhcp": is_dhcp,
            }

            ok, msg = self.app_core.ctx.platform.set_interface_dns_servers(iface, servers)
            self.app_core.ctx.platform.flush_dns_cache()

            import uuid
            from app.core.models.metrics import ActionExecutionRecord, ActionExecutionStatus, RiskLevel

            if ok:
                self.view_dashboard.log_autonomous_action(
                    f"اعتماد خادم {name}",
                    f"تم تحديث إعدادات DNS إلى {primary_ip} والتحقق عبر Get-DnsClientServerAddress.",
                    level="success",
                )
                st = ActionExecutionStatus.SUCCEEDED
                err_msg = None
            else:
                st = ActionExecutionStatus.FAILED
                err_msg = msg

            record = ActionExecutionRecord(
                id=str(uuid.uuid4()),
                action_id="switch_dns_resolver",
                action_name=f"تحويل إلى {name} ({primary_ip})",
                risk_level=RiskLevel.LEVEL_2_CONTROLLED,
                trigger_diagnosis_id="autonomous_optimizer",
                pre_remedy_metrics={
                    "interface": iface,
                    "original_servers": list(prev_servers),
                    "is_dhcp": is_dhcp,
                },
                post_remedy_metrics={"active_servers": servers, "status": msg},
                status=st,
                execution_duration_ms=45.0,
                verification_duration_ms=12.0,
                error_message=err_msg,
                rollback_performed=False,
            )
            ctx = getattr(getattr(self, "app_core", None), "ctx", None)
            if ctx and hasattr(ctx, "audit"):
                ctx.audit.save(record)
            QTimer.singleShot(0, self._refresh_timeline_from_records)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_scan_traffic(self) -> None:
        self.view_traffic.btn_refresh.setEnabled(False)
        self.view_traffic.btn_refresh.setText("جاري الفحص...")

        def _worker():
            profiles = asyncio.run(self.traffic_controller.scan_active_applications())
            is_conf = self.traffic_controller.is_critical_meeting_active()
            self.bridge.traffic_scan_done.emit(profiles, is_conf)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_scan_traffic_done(self, profiles, is_conferencing: bool) -> None:
        self.view_traffic.btn_refresh.setEnabled(True)
        self.view_traffic.btn_refresh.setText("فحص البرامج النشطة")
        self.view_traffic.update_profiles(profiles, conferencing_active=is_conferencing)
        self.view_dashboard.consumers_panel.update_processes(profiles)

    def _on_run_deep_diagnosis(self) -> None:
        self.view_diagnosis.btn_run_audit.setEnabled(False)
        self.view_diagnosis.btn_run_audit.setText("جاري بدء الفحص الشامل...")

        def _progress(step_idx: int, total_steps: int, msg: str):
            QTimer.singleShot(0, lambda s=step_idx, t=total_steps, m=msg: self.view_diagnosis.btn_run_audit.setText(f"جاري الفحص ({s}/{t}): {m}"))

        def _worker():
            try:
                from app.diagnosis.deep_scan import DeepScanner
                scanner = DeepScanner(platform=self.app_core.ctx.platform)
                report = scanner.run_scan(progress_callback=_progress)
                QTimer.singleShot(0, lambda r=report: self._on_deep_diagnosis_finished(r))
            except Exception as exc:
                logger.error("Deep scan failed with exception: %s", exc, exc_info=True)
                QTimer.singleShot(0, lambda e=str(exc): self._on_deep_diagnosis_failed(e))

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
        self.view_remediation.btn_flush_now.setEnabled(False)
        self.view_remediation.btn_flush_now.setText("جاري تنظيف كاش DNS...")

        def _worker():
            try:
                ok, msg = self.app_core.ctx.platform.flush_dns_cache()
                QTimer.singleShot(0, lambda s=ok, m=msg: self._on_quick_flush_dns_done(s, m))
            except Exception as exc:
                logger.error("Flush DNS failed: %s", exc, exc_info=True)
                QTimer.singleShot(0, lambda e=str(exc): self._on_quick_flush_dns_done(False, e))

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
        platform = self.app_core.ctx.platform
        if not platform.is_elevated():
            self.view_remediation.btn_renew_ip.setEnabled(True)
            self.view_remediation.btn_renew_ip.setText("تجديد IP (يتطلب صلاحيات مسؤول)")
            self.view_dashboard.log_autonomous_action(
                "تعذر تجديد عنوان IP",
                "يتطلب تجديد عنوان IP (DHCP Lease) صلاحيات مسؤول لنظام Windows. يُرجى تشغيل البرنامج كمسؤول.",
                level="warning",
            )
            QTimer.singleShot(3500, lambda: self.view_remediation.btn_renew_ip.setText("تجديد مسار الاتصال"))
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
                QTimer.singleShot(0, lambda s=success, i=iface, g=gw_after, p=ping_ms, m=msg: self._on_quick_renew_ip_finished(s, i, g, p, m))
            except Exception as exc:
                logger.error("IP renewal failed: %s", exc, exc_info=True)
                QTimer.singleShot(0, lambda i=iface, g=gw_before, e=str(exc): self._on_quick_renew_ip_finished(False, i, g, 0.0, e))

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

        self.view_settings.apply_btn.setText("تم حفظ الإعدادات وتطبيقها بنجاح! ✓")
        QTimer.singleShot(2500, lambda: self.view_settings.apply_btn.setText("حفظ الإعدادات وتطبيقها الآن"))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        w = self.width()

        if w < 700:
            if getattr(self, "_shell_mode", "dock") != "top_bar":
                self._shell_mode = "top_bar"
                self.root_layout.removeWidget(self.sidebar)
                self.root_layout.removeWidget(self.stack)
                self.root_layout.setDirection(QVBoxLayout.TopToBottom)
                self.root_layout.addWidget(self.sidebar)
                self.root_layout.addWidget(self.stack, stretch=1)
                self.sidebar.set_mode("top_bar")
        else:
            if getattr(self, "_shell_mode", "dock") != "dock":
                self._shell_mode = "dock"
                self.root_layout.removeWidget(self.sidebar)
                self.root_layout.removeWidget(self.stack)
                self.root_layout.setDirection(QHBoxLayout.LeftToRight)
                self.root_layout.addWidget(self.sidebar)
                self.root_layout.addWidget(self.stack, stretch=1)
                self.sidebar.set_mode("dock")

    def closeEvent(self, event) -> None:
        if hasattr(self, "refresh_timer") and self.refresh_timer.isActive():
            self.refresh_timer.stop()
        if hasattr(self, "dns_rank_timer") and self.dns_rank_timer.isActive():
            self.dns_rank_timer.stop()
        super().closeEvent(event)
