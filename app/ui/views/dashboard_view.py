"""Main Dashboard View for NetGuard AI Desktop."""

from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QGridLayout,
)
from PySide6.QtCore import Qt
from app.ui.widgets.status_card import StatusCard
from app.ui.widgets.realtime_chart import RealTimePlotWidget


class DashboardView(QWidget):
    """Main landing screen giving an instantaneous operational view of the network."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 1. Master Status Banner
        self.banner = QFrame()
        self.banner.setStyleSheet("""
            QFrame {
                background-color: #162438;
                border: 1px solid #1f6feb;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        banner_layout = QHBoxLayout(self.banner)
        banner_layout.setContentsMargins(14, 10, 14, 10)

        status_text_layout = QVBoxLayout()
        self.status_title = QLabel("SYSTEM STATUS: HEALTHY")
        self.status_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #3fb950;")
        self.status_desc = QLabel("Continuous predictive monitoring and autonomous protection active.")
        self.status_desc.setStyleSheet("font-size: 12px; color: #8b949e;")
        status_text_layout.addWidget(self.status_title)
        status_text_layout.addWidget(self.status_desc)

        self.mode_pill = QLabel("AUTONOMOUS SAFE")
        self.mode_pill.setStyleSheet("""
            background-color: #1f2c4c;
            color: #58a6ff;
            font-size: 11px;
            font-weight: bold;
            padding: 6px 12px;
            border-radius: 12px;
        """)

        banner_layout.addLayout(status_text_layout)
        banner_layout.addStretch()
        banner_layout.addWidget(self.mode_pill)

        layout.addWidget(self.banner)

        # 2. KPI Cards Grid
        cards_grid = QGridLayout()
        cards_grid.setSpacing(12)

        self.card_gateway = StatusCard("Gateway Latency", "--", "ms")
        self.card_external = StatusCard("External Latency", "--", "ms")
        self.card_jitter = StatusCard("Jitter Variance", "--", "ms")
        self.card_dns = StatusCard("DNS Resolution", "--", "ms")

        cards_grid.addWidget(self.card_gateway, 0, 0)
        cards_grid.addWidget(self.card_external, 0, 1)
        cards_grid.addWidget(self.card_jitter, 0, 2)
        cards_grid.addWidget(self.card_dns, 0, 3)

        layout.addLayout(cards_grid)

        # 3. Real-time Live Telemetry Chart
        self.chart = RealTimePlotWidget("Live Latency Stream (Last 30 Samples)", "Latency (ms)")
        layout.addWidget(self.chart, stretch=1)

        # 4. QoE Bar / Quick Stats
        qoe_frame = QFrame()
        qoe_frame.setStyleSheet("background-color: #111625; border: 1px solid #1e2640; border-radius: 8px; padding: 10px;")
        qoe_layout = QHBoxLayout(qoe_frame)

        self.qoe_overall = QLabel("Overall QoE: 100/100 (Excellent)")
        self.qoe_overall.setStyleSheet("font-size: 13px; font-weight: bold; color: #3fb950;")
        self.qoe_conf = QLabel("Voice/Video: 100")
        self.qoe_conf.setStyleSheet("font-size: 12px; color: #8b949e;")
        self.qoe_game = QLabel("Gaming: 100")
        self.qoe_game.setStyleSheet("font-size: 12px; color: #8b949e;")
        self.qoe_stream = QLabel("Streaming: 100")
        self.qoe_stream.setStyleSheet("font-size: 12px; color: #8b949e;")

        qoe_layout.addWidget(self.qoe_overall)
        qoe_layout.addStretch()
        qoe_layout.addWidget(self.qoe_conf)
        qoe_layout.addWidget(self.qoe_game)
        qoe_layout.addWidget(self.qoe_stream)

        layout.addWidget(qoe_frame)

    def set_status(self, title: str, desc: str, color: str = "#3fb950") -> None:
        self.status_title.setText(title)
        self.status_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {color};")
        self.status_desc.setText(desc)
