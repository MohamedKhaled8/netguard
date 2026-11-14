"""Main Application Window for NetGuard AI Desktop.

Redesigned according to ui-ux-pro-max and universal engineering directives:
- Full native Arabic & English localization with instantaneous RTL/LTR layout toggle.
- Intuitive, crystal-clear user experience with zero confusing jargon.
- One-click 'Smart Scan & Quick Fix' CTA.
- Fully wired, robust background workers for DNS Benchmarking, Diagnostics, and Process Traffic.
"""

from __future__ import annotations
import asyncio
import threading
from typing import Optional, List
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QStackedWidget,
    QFrame,
    QApplication,
)
from PySide6.QtCore import QTimer, Qt

from app.ui.styles import DARK_THEME_QSS
from app.ui.i18n import tr, get_language, set_language
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.diagnosis_view import DiagnosisView
from app.ui.views.remediation_view import RemediationView
from app.ui.views.traffic_view import TrafficView
from app.ui.views.dns_view import DNSView
from app.ui.views.history_view import HistoryView
from app.ui.views.settings_view import SettingsView
from app.application import NetGuardApplication
from app.core.models.metrics import MetricType, OperatingMode
from app.traffic.controller import TrafficController


class MainWindow(QMainWindow):
    """NetGuard AI Master Desktop Application Window."""

    def __init__(self, application: NetGuardApplication, parent=None) -> None:
        super().__init__(parent)
        self.app_core = application
        self.traffic_controller = TrafficController(event_bus=application.ctx.event_bus)

        # Set initial default language to Arabic
        set_language("ar")
        if QApplication.instance():
            QApplication.instance().setLayoutDirection(Qt.RightToLeft)

        self.setWindowTitle("NetGuard AI — الحارس الذكي للشبكة والإنترنت")
        self.resize(1200, 780)
        self.setStyleSheet(DARK_THEME_QSS)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        self.main_layout = QHBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. Sidebar Navigation
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 16)
        self.sidebar_layout.setSpacing(4)

        # App Title & Subtitle
        self.app_title = QLabel(tr("app_title"))
        self.app_title.setObjectName("AppTitle")
        self.app_sub = QLabel(tr("app_subtitle"))
        self.app_sub.setObjectName("AppSubtitle")
        self.app_sub.setWordWrap(True)
        self.sidebar_layout.addWidget(self.app_title)
        self.sidebar_layout.addWidget(self.app_sub)

        # Language Toggle Pill in Sidebar
        lang_row = QHBoxLayout()
        lang_row.setContentsMargins(12, 0, 12, 10)
        self.btn_lang = QPushButton(tr("lang_toggle"))
        self.btn_lang.setObjectName("LangToggleBtn")
        self.btn_lang.clicked.connect(self._toggle_language)
        lang_row.addWidget(self.btn_lang)
        self.sidebar_layout.addLayout(lang_row)

        # Nav Buttons
        self.nav_buttons: List[QPushButton] = []
        self.btn_dash = self._create_nav_btn(tr("nav_dashboard"), 0)
        self.btn_diag = self._create_nav_btn(tr("nav_diagnostics"), 1)
        self.btn_rem = self._create_nav_btn(tr("nav_healing"), 2)
        self.btn_traffic = self._create_nav_btn(tr("nav_traffic"), 3)
        self.btn_dns = self._create_nav_btn(tr("nav_dns"), 4)
        self.btn_hist = self._create_nav_btn(tr("nav_history"), 5)
        self.btn_settings = self._create_nav_btn(tr("nav_settings"), 6)

        self.sidebar_layout.addStretch()

        # Version & Status Pill
        self.ver_lbl = QLabel(tr("version"))
        self.ver_lbl.setStyleSheet("font-size: 11px; color: #8b949e; padding: 0px 14px;")
        self.sidebar_layout.addWidget(self.ver_lbl)

        self.main_layout.addWidget(self.sidebar)

        # 2. Multi-View Stack
        self.stack = QStackedWidget()
        self.view_dashboard = DashboardView()
        self.view_diagnosis = DiagnosisView()
        self.view_remediation = RemediationView()
        self.view_traffic = TrafficView()
        self.view_dns = DNSView()
        self.view_history = HistoryView()
        self.view_settings = SettingsView()

        self.stack.addWidget(self.view_dashboard)
        self.stack.addWidget(self.view_diagnosis)
        self.stack.addWidget(self.view_remediation)
        self.stack.addWidget(self.view_traffic)
        self.stack.addWidget(self.view_dns)
        self.stack.addWidget(self.view_history)
        self.stack.addWidget(self.view_settings)

        self.main_layout.addWidget(self.stack, stretch=1)

        # Set initial active tab
        self.btn_dash.setChecked(True)

        # Wire Action Buttons across views
        self._wire_actions()

        # UI Refresh Timer (1 second interval)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._on_ui_tick)
        self.refresh_timer.start(1000)

    def _create_nav_btn(self, text: str, index: int) -> QPushButton:
        btn = QPushButton(text)
        btn.setProperty("class", "NavButton")
        btn.setCheckable(True)
        btn.clicked.connect(lambda: self._switch_view(index, btn))
        self.sidebar_layout.addWidget(btn)
        self.nav_buttons.append(btn)
        return btn

    def _switch_view(self, index: int, active_btn: QPushButton) -> None:
        self.stack.setCurrentIndex(index)
        for b in self.nav_buttons:
            b.setChecked(b == active_btn)

        # On switching to traffic view, perform an instant background scan
        if index == 3:
            self._on_scan_traffic()

    def _wire_actions(self) -> None:
        """Wire all interactive action buttons to their corresponding handlers."""
        # Dashboard Actions
        self.view_dashboard.btn_quick_fix.clicked.connect(self._on_quick_fix)
        self.view_dashboard.btn_flush_dns.clicked.connect(self._on_flush_dns)
        self.view_dashboard.btn_recheck_gw.clicked.connect(self._on_recheck_gw)

        # Diagnosis Actions
        self.view_diagnosis.btn_run_audit.clicked.connect(self._on_run_full_audit)

        # Remediation Actions
        self.view_remediation.btn_flush_now.clicked.connect(self._on_flush_dns)
        self.view_remediation.btn_recheck_now.clicked.connect(self._on_recheck_gw)

        # DNS Actions
        self.view_dns.benchmark_btn.clicked.connect(self._on_run_dns_benchmark)

        # Traffic Actions
        self.view_traffic.btn_refresh.clicked.connect(self._on_scan_traffic)

        # Settings Actions
        self.view_settings.apply_btn.clicked.connect(self._on_apply_settings)
        self.view_settings.lang_combo.currentIndexChanged.connect(self._on_settings_lang_changed)

    def _toggle_language(self) -> None:
        """Toggle between Arabic and English."""
        new_lang = "en" if get_language() == "ar" else "ar"
        self._set_app_language(new_lang)

    def _on_settings_lang_changed(self, index: int) -> None:
        lang_code = self.view_settings.lang_combo.itemData(index)
        if lang_code and lang_code != get_language():
            self._set_app_language(lang_code)

    def _set_app_language(self, lang: str) -> None:
        set_language(lang)
        is_ar = (lang == "ar")
        if QApplication.instance():
            QApplication.instance().setLayoutDirection(Qt.RightToLeft if is_ar else Qt.LeftToRight)

        # Update Sidebar texts
        self.app_title.setText(tr("app_title"))
        self.app_sub.setText(tr("app_subtitle"))
        self.btn_lang.setText(tr("lang_toggle"))
        self.ver_lbl.setText(tr("version"))

        # Update Nav buttons
        nav_keys = [
            "nav_dashboard", "nav_diagnostics", "nav_healing",
            "nav_traffic", "nav_dns", "nav_history", "nav_settings",
        ]
        for btn, key in zip(self.nav_buttons, nav_keys):
            btn.setText(tr(key))

        # Update All Subviews
        self.view_dashboard.apply_language()
        self.view_diagnosis.apply_language()
        self.view_remediation.apply_language()
        self.view_traffic.apply_language()
        self.view_dns.apply_language()
        self.view_history.apply_language()
        self.view_settings.apply_language()

    # -------------------------------------------------------------------------
    # Quick Fix & Instant Diagnostic Actions
    # -------------------------------------------------------------------------

    def _on_quick_fix(self) -> None:
        """One-click smart scan & fix: Audits network, flushes DNS, and refreshes state."""
        self.view_dashboard.btn_quick_fix.setEnabled(False)
        self.view_dashboard.btn_quick_fix.setText(tr("quick_fix_running"))

        def _worker():
            # 1. Step diagnostic evaluation
            asyncio.run(self.app_core.step())
            # 2. Flush DNS cache via native Win32 API
            self.app_core.ctx.platform.flush_dns_cache()
            # 3. Trigger immediate probe samples
            loop = asyncio.new_event_loop()
            for probe_name in ("gateway_probe", "external_probe", "dns_probe"):
                probe = self.app_core.observability.probes.get(probe_name)
                if probe:
                    try:
                        loop.run_until_complete(probe.measure())
                    except Exception:
                        pass
            loop.close()
            QTimer.singleShot(0, self._on_quick_fix_done)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_quick_fix_done(self) -> None:
        self.view_dashboard.btn_quick_fix.setEnabled(True)
        self.view_dashboard.btn_quick_fix.setText(tr("quick_fix_btn"))
        self.view_dashboard.set_status(
            "تم فحص الشبكة وإصلاح المسارات بنجاح! 🟢" if get_language() == "ar" else "Network Audited & Optimized! 🟢",
            tr("quick_fix_success"),
            "#3fb950",
        )

    def _on_flush_dns(self) -> None:
        """Flush DNS cache immediately."""
        self.app_core.ctx.platform.flush_dns_cache()
        self.view_dashboard.set_status(
            "تم تنظيف كاش الـ DNS بنجاح 🟢" if get_language() == "ar" else "DNS Cache Flushed Successfully 🟢",
            tr("flush_dns_success"),
            "#3fb950",
        )

    def _on_recheck_gw(self) -> None:
        """Recheck gateway connection."""
        def _worker():
            probe = self.app_core.observability.probes.get("gateway_probe")
            if probe:
                asyncio.run(probe.measure())
            QTimer.singleShot(0, lambda: self.view_dashboard.set_status(
                "تم فحص الراوتر بنجاح 🟢" if get_language() == "ar" else "Gateway Checked Successfully 🟢",
                tr("recheck_gw_success"),
                "#3fb950",
            ))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_run_full_audit(self) -> None:
        """Run full comprehensive network audit."""
        self.view_diagnosis.btn_run_audit.setEnabled(False)
        self.view_diagnosis.btn_run_audit.setText(tr("diag_running"))

        def _worker():
            diag = asyncio.run(self.app_core.step())
            QTimer.singleShot(0, lambda: self._on_full_audit_done(diag))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_full_audit_done(self, diag) -> None:
        self.view_diagnosis.btn_run_audit.setEnabled(True)
        self.view_diagnosis.btn_run_audit.setText(tr("diag_run_btn"))
        self.view_diagnosis.update_diagnosis(diag)

    # -------------------------------------------------------------------------
    # DNS Benchmark Worker
    # -------------------------------------------------------------------------

    def _on_run_dns_benchmark(self) -> None:
        self.view_dns.benchmark_btn.setEnabled(False)
        self.view_dns.benchmark_btn.setText(tr("dns_bench_running"))

        def _worker():
            from app.dns.benchmark import DNSBenchmark
            bench = DNSBenchmark()
            scores = asyncio.run(bench.rank_all())
            QTimer.singleShot(0, lambda: self._on_dns_benchmark_done(scores))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_dns_benchmark_done(self, scores) -> None:
        self.view_dns.update_rankings(scores)
        self.view_dns.benchmark_btn.setEnabled(True)
        self.view_dns.benchmark_btn.setText(tr("dns_bench_btn"))

    # -------------------------------------------------------------------------
    # Traffic Scanner Worker
    # -------------------------------------------------------------------------

    def _on_scan_traffic(self) -> None:
        self.view_traffic.btn_refresh.setEnabled(False)
        self.view_traffic.btn_refresh.setText("جاري الفحص..." if get_language() == "ar" else "Scanning...")

        def _worker():
            profiles = asyncio.run(self.traffic_controller.scan_active_applications())
            is_conf = self.traffic_controller.is_critical_meeting_active()
            QTimer.singleShot(0, lambda: self._on_scan_traffic_done(profiles, is_conf))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_scan_traffic_done(self, profiles, is_conferencing: bool) -> None:
        self.view_traffic.btn_refresh.setEnabled(True)
        self.view_traffic.btn_refresh.setText(tr("traffic_scan_btn"))
        self.view_traffic.update_profiles(profiles, conferencing_active=is_conferencing)

    # -------------------------------------------------------------------------
    # Settings Handler
    # -------------------------------------------------------------------------

    def _on_apply_settings(self) -> None:
        mode_data = self.view_settings.mode_combo.currentData() or self.view_settings.mode_combo.currentText()
        if "safe" in mode_data:
            mode_val = OperatingMode.AUTONOMOUS_SAFE
        elif "assisted" in mode_data:
            mode_val = OperatingMode.ASSISTED
        else:
            mode_val = OperatingMode.OBSERVATION

        self.app_core.orchestrator.set_operating_mode(mode_val)
        self.view_dashboard.mode_pill.setText(tr(f"mode_{mode_val.value.split('_')[0]}", mode_val.value.upper()))
        
        self.view_settings.apply_btn.setText(tr("set_saved_success"))
        QTimer.singleShot(2000, lambda: self.view_settings.apply_btn.setText(tr("set_save_btn")))

    # -------------------------------------------------------------------------
    # Periodic UI Telemetry Tick (1 second)
    # -------------------------------------------------------------------------

    def _on_ui_tick(self) -> None:
        """Periodic UI update polling in-memory telemetry and status."""
        obs = self.app_core.observability

        # Update KPI Cards
        gw_sample = obs.get_latest_measurement(MetricType.GATEWAY_LATENCY)
        if gw_sample:
            is_high = gw_sample.raw_value >= 25.0
            stat_text = tr("stat_high_latency") if is_high else tr("stat_normal")
            self.view_dashboard.card_gateway.update_metric(
                f"{gw_sample.raw_value:.1f}", stat_text, is_warning=is_high
            )

        ext_sample = obs.get_latest_measurement(MetricType.EXTERNAL_LATENCY)
        if ext_sample:
            is_high = ext_sample.raw_value >= 80.0
            stat_text = tr("stat_high_latency") if is_high else tr("stat_normal")
            self.view_dashboard.card_external.update_metric(
                f"{ext_sample.raw_value:.1f}", stat_text, is_warning=is_high
            )

        jit_sample = obs.get_latest_measurement(MetricType.JITTER_MS)
        if jit_sample:
            is_unstable = jit_sample.raw_value >= 20.0
            stat_text = tr("stat_unstable") if is_unstable else tr("stat_stable")
            self.view_dashboard.card_jitter.update_metric(
                f"{jit_sample.raw_value:.1f}", stat_text, is_warning=is_unstable
            )

        dns_sample = obs.get_latest_measurement(MetricType.DNS_LATENCY)
        if dns_sample:
            is_slow = dns_sample.raw_value >= 60.0
            stat_text = tr("stat_degraded") if is_slow else tr("stat_fast")
            self.view_dashboard.card_dns.update_metric(
                f"{dns_sample.raw_value:.1f}", stat_text, is_warning=is_slow
            )

        # Update Live Chart
        ext_window = obs.get_sliding_window(MetricType.EXTERNAL_LATENCY)
        if ext_window:
            y_vals = [s.raw_value for s in ext_window]
            self.view_dashboard.chart.update_data(y_vals)

        # Update Diagnostic View
        last_diag = self.app_core.diagnosis.last_diagnosis
        if last_diag:
            self.view_diagnosis.update_diagnosis(last_diag)
            if last_diag.probable_cause.value == "healthy":
                self.view_dashboard.set_status(tr("system_healthy"), tr("system_healthy_desc"), "#3fb950")
            else:
                cause_key = f"cause_{last_diag.probable_cause.value}"
                cause_translated = tr(cause_key, last_diag.probable_cause.value.upper())
                self.view_dashboard.set_status(f"تنبيه: {cause_translated}", last_diag.explanation, "#f85149")

        # Update Remediation view audit records
        if self.stack.currentWidget() == self.view_remediation:
            audit_records = self.app_core.ctx.audit.get_recent(limit=30)
            self.view_remediation.update_audit_log(audit_records)

        # Update Incident History view
        if self.stack.currentWidget() == self.view_history:
            incidents = self.app_core.ctx.incidents.get_recent(limit=30)
            self.view_history.update_incidents(incidents)
