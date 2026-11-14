"""Intelligent DNS Benchmark and Resolver Ranking View."""

from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
)


class DNSView(QWidget):
    """Displays real-time DNS resolver benchmark comparisons and optimization controls."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        banner = QFrame()
        banner.setStyleSheet("background-color: #111625; border: 1px solid #1e2640; border-radius: 8px; padding: 14px;")
        b_layout = QHBoxLayout(banner)

        text_layout = QVBoxLayout()
        title = QLabel("INTELLIGENT DNS RESOLVER ENGINE")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #58a6ff;")
        desc = QLabel("Continuous benchmark across Cloudflare, Google, Quad9, and OpenDNS.")
        desc.setStyleSheet("font-size: 13px; color: #8b949e;")
        text_layout.addWidget(title)
        text_layout.addWidget(desc)

        self.benchmark_btn = QPushButton("Run Benchmark")
        self.benchmark_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #2ea043; }
        """)

        b_layout.addLayout(text_layout)
        b_layout.addStretch()
        b_layout.addWidget(self.benchmark_btn)
        layout.addWidget(banner)

        lbl = QLabel("RESOLVER RELIABILITY RANKING")
        lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #e6edf3;")
        layout.addWidget(lbl)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Rank", "Resolver Name", "IP Address", "Mean Latency", "Failure Rate", "Composite Score"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

    def update_rankings(self, scores) -> None:
        self.table.setRowCount(0)
        for idx, s in enumerate(scores, start=1):
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(f"#{idx}"))
            self.table.setItem(row, 1, QTableWidgetItem(s.name))
            self.table.setItem(row, 2, QTableWidgetItem(s.ip))
            self.table.setItem(row, 3, QTableWidgetItem(f"{s.mean_latency_ms:.1f}ms"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{s.failure_rate * 100:.1f}%"))

            score_item = QTableWidgetItem(f"{s.composite_score:.1f} / 100")
            self.table.setItem(row, 5, score_item)
