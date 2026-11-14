"""Redesigned Dashboard View for NetGuard AI Desktop.

Provides a high-craft, intuitive user experience with:
- Prominent master health status banner.
- One-click 'Smart Scan & Quick Fix' CTA.
- 4 Clear KPI cards with micro-copy in plain Arabic.
- Real-time latency & stability chart.
"""

from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QGridLayout,
    QPushButton,
)
from PySide6.QtCore import Qt
from app.ui.widgets.status_card import StatusCard
from app.ui.widgets.realtime_chart import RealTimePlotWidget
from app.ui.i18n import tr


class DashboardView(QWidget):
    """Main landing screen giving an instantaneous operational view of the network."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 1. Master Hero Status Banner
        self.banner = QFrame()
        self.banner.setObjectName("HeroBanner")
        self.banner.setStyleSheet("""
            QFrame#HeroBanner {
                background-color: #121929;
                border: 1px solid #202d45;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        banner_layout = QVBoxLayout(self.banner)
        banner_layout.setContentsMargins(16, 14, 16, 14)
        banner_layout.setSpacing(12)

        # Banner Top Row: Title, Mode Pill
        top_row = QHBoxLayout()
        self.status_title = QLabel(tr("system_healthy"))
        self.status_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #3fb950;")
        top_row.addWidget(self.status_title)
        top_row.addStretch()

        self.mode_pill = QLabel(tr("mode_autonomous"))
        self.mode_pill.setStyleSheet("""
            background-color: #1a2744;
            color: #58a6ff;
            font-size: 11px;
            font-weight: 700;
            padding: 5px 12px;
            border-radius: 10px;
            border: 1px solid #2d4170;
        """)
        top_row.addWidget(self.mode_pill)
        banner_layout.addLayout(top_row)

        # Banner Middle Row: Explanatory description
        self.status_desc = QLabel(tr("system_healthy_desc"))
        self.status_desc.setStyleSheet("font-size: 13px; color: #8b949e; line-height: 1.4;")
        self.status_desc.setWordWrap(True)
        banner_layout.addWidget(self.status_desc)

        # Banner Bottom Row: Quick Action CTAs
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_quick_fix = QPushButton(tr("quick_fix_btn"))
        self.btn_quick_fix.setProperty("class", "HeroActionBtn")
        self.btn_quick_fix.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
                padding: 9px 18px;
                border-radius: 8px;
                border: 1px solid #388bfd;
            }
            QPushButton:hover { background-color: #388bfd; }
            QPushButton:pressed { background-color: #1a56b7; }
        """)

        self.btn_flush_dns = QPushButton(tr("flush_dns_btn"))
        self.btn_flush_dns.setProperty("class", "SecondaryBtn")
        self.btn_flush_dns.setStyleSheet("""
            QPushButton {
                background-color: #1c263c;
                color: #c9d1d9;
                font-size: 12px;
                font-weight: 600;
                padding: 9px 14px;
                border-radius: 8px;
                border: 1px solid #2a3754;
            }
            QPushButton:hover { background-color: #263350; color: #ffffff; }
        """)

        self.btn_recheck_gw = QPushButton(tr("recheck_gw_btn"))
        self.btn_recheck_gw.setProperty("class", "SecondaryBtn")
        self.btn_recheck_gw.setStyleSheet("""
            QPushButton {
                background-color: #1c263c;
                color: #c9d1d9;
                font-size: 12px;
                font-weight: 600;
                padding: 9px 14px;
                border-radius: 8px;
                border: 1px solid #2a3754;
            }
            QPushButton:hover { background-color: #263350; color: #ffffff; }
        """)

        btn_row.addWidget(self.btn_quick_fix)
        btn_row.addWidget(self.btn_flush_dns)
        btn_row.addWidget(self.btn_recheck_gw)
        btn_row.addStretch()

        banner_layout.addLayout(btn_row)
        layout.addWidget(self.banner)

        # 2. 4 Telemetry Metric KPI Cards Grid
        grid = QGridLayout()
        grid.setSpacing(12)

        self.card_gateway = StatusCard(
            title=tr("card_gateway_title"),
            unit="ms",
            desc=tr("card_gateway_desc"),
        )
        self.card_external = StatusCard(
            title=tr("card_external_title"),
            unit="ms",
            desc=tr("card_external_desc"),
        )
        self.card_jitter = StatusCard(
            title=tr("card_jitter_title"),
            unit="ms",
            desc=tr("card_jitter_desc"),
        )
        self.card_dns = StatusCard(
            title=tr("card_dns_title"),
            unit="ms",
            desc=tr("card_dns_desc"),
        )

        grid.addWidget(self.card_gateway, 0, 0)
        grid.addWidget(self.card_external, 0, 1)
        grid.addWidget(self.card_jitter, 1, 0)
        grid.addWidget(self.card_dns, 1, 1)

        layout.addLayout(grid)

        # 3. Real-Time Telemetry Chart
        self.chart = RealTimePlotWidget(title=tr("chart_title"), y_label="ms")
        layout.addWidget(self.chart, stretch=1)

    def apply_language(self) -> None:
        """Refresh all static texts according to current i18n locale."""
        self.mode_pill.setText(tr("mode_autonomous"))
        self.btn_quick_fix.setText(tr("quick_fix_btn"))
        self.btn_flush_dns.setText(tr("flush_dns_btn"))
        self.btn_recheck_gw.setText(tr("recheck_gw_btn"))

        self.card_gateway.set_texts(tr("card_gateway_title"), "ms", tr("card_gateway_desc"))
        self.card_external.set_texts(tr("card_external_title"), "ms", tr("card_external_desc"))
        self.card_jitter.set_texts(tr("card_jitter_title"), "ms", tr("card_jitter_desc"))
        self.card_dns.set_texts(tr("card_dns_title"), "ms", tr("card_dns_desc"))

    def set_status(self, title: str, description: str, color_hex: str = "#3fb950") -> None:
        self.status_title.setText(title)
        self.status_title.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {color_hex};")
        self.status_desc.setText(description)
