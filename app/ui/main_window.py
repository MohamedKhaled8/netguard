"""Main Application Window for NetGuard AI Desktop."""

from __future__ import annotations
import asyncio
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QStackedWidget,
    QFrame,
)
from PySide6.QtCore import QTimer, Qt

from app.ui.styles import DARK_THEME_QSS
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.diagnosis_view import DiagnosisView
from app.ui.views.remediation_view import RemediationView
from app.ui.views.traffic_view import TrafficView
from app.ui.views.dns_view import DNSView
from app.ui.views.history_view import HistoryView
from app.ui.views.settings_view import SettingsView
from app.application import NetGuardApplication
from app.core.models.metrics import MetricType


class MainWindow(QMainWindow):
    """NetGuard AI Master Desktop Application Window."""

    def __init__(self, application: NetGuardApplication, parent=None) -> None:
        super().__init__(parent)
        self.app_core = application
        self.setWindowTitle("NetGuard AI — Autonomous Network Intelligence & Self-Healing")
        self.resize(1180, 760)
        self.setStyleSheet(DARK_THEME_QSS)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar Navigation
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 16)
        sidebar_layout.setSpacing(4)

        app_title = QLabel("NETGUARD AI")
        app_title.setObjectName("AppTitle")
        app_sub = QLabel("Autonomous Intelligence")
        app_sub.setObjectName("AppSubtitle")
        sidebar_layout.addWidget(app_title)
        sidebar_layout.addWidget(app_sub)

        # Nav Buttons
        self.nav_buttons = []
        self.btn_dash = self._create_nav_btn("📊 Dashboard", 0, sidebar_layout)
        self.btn_diag = self._create_nav_btn("🔍 Diagnostics", 1, sidebar_layout)
        self.btn_rem = self._create_nav_btn("🛡️ Self-Healing", 2, sidebar_layout)
        self.btn_traffic = self._create_nav_btn("🚦 App Traffic", 3, sidebar_layout)
        self.btn_dns = self._create_nav_btn("🌐 DNS Engine", 4, sidebar_layout)
        self.btn_hist = self._create_nav_btn("📜 Incident History", 5, sidebar_layout)
        self.btn_settings = self._create_nav_btn("⚙️ Settings", 6, sidebar_layout)

        sidebar_layout.addStretch()

        # Version Pill
        ver_lbl = QLabel("v2.0.0-alpha · PySide6")
        ver_lbl.setStyleSheet("font-size: 10px; color: #8b949e; padding-left: 14px;")
        sidebar_layout.addWidget(ver_lbl)

        main_layout.addWidget(sidebar)

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

        main_layout.addWidget(self.stack, stretch=1)

        # Set initial active tab
        self.btn_dash.setChecked(True)

        # UI Refresh Timer (1 second interval)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._on_ui_tick)
        self.refresh_timer.start(1000)

    def _create_nav_btn(self, text: str, index: int, parent_layout: QVBoxLayout) -> QPushButton:
        btn = QPushButton(text)
        btn.setProperty("class", "NavButton")
        btn.setCheckable(True)
        btn.clicked.connect(lambda: self._switch_view(index, btn))
        parent_layout.addWidget(btn)
        self.nav_buttons.append(btn)
        return btn

    def _switch_view(self, index: int, active_btn: QPushButton) -> None:
        self.stack.setCurrentIndex(index)
        for b in self.nav_buttons:
            b.setChecked(b == active_btn)

    def _on_ui_tick(self) -> None:
        """Periodic UI update polling in-memory telemetry and status."""
        obs = self.app_core.observability

        # Update KPI Cards
        gw_sample = obs.get_latest_measurement(MetricType.GATEWAY_LATENCY)
        if gw_sample:
            self.view_dashboard.card_gateway.update_metric(f"{gw_sample.raw_value:.1f}", "Normal" if gw_sample.raw_value < 25.0 else "High Latency")

        ext_sample = obs.get_latest_measurement(MetricType.EXTERNAL_LATENCY)
        if ext_sample:
            self.view_dashboard.card_external.update_metric(f"{ext_sample.raw_value:.1f}", "Healthy" if ext_sample.raw_value < 80.0 else "Elevated Latency")

        jit_sample = obs.get_latest_measurement(MetricType.JITTER_MS)
        if jit_sample:
            self.view_dashboard.card_jitter.update_metric(f"{jit_sample.raw_value:.1f}", "Stable" if jit_sample.raw_value < 20.0 else "Jitter Spike")

        dns_sample = obs.get_latest_measurement(MetricType.DNS_LATENCY)
        if dns_sample:
            self.view_dashboard.card_dns.update_metric(f"{dns_sample.raw_value:.1f}", "Fast" if dns_sample.raw_value < 60.0 else "Degraded")

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
                self.view_dashboard.set_status("SYSTEM STATUS: HEALTHY", "Continuous autonomous network protection active.", "#3fb950")
            else:
                self.view_dashboard.set_status(f"ANOMALY: {last_diag.probable_cause.value.upper()}", last_diag.explanation, "#f85149")
