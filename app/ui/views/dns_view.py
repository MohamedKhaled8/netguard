"""Intelligent DNS Benchmark and Resolver Ranking View.

Displays real-time DNS resolver benchmark comparisons and optimization controls
with plain-language guidance on DNS speed and reliability.
"""

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
from PySide6.QtCore import Qt
from app.ui.i18n import tr


class DNSView(QWidget):
    """Displays real-time DNS resolver benchmark comparisons and optimization controls."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        banner = QFrame()
        banner.setStyleSheet("background-color: #111625; border: 1px solid #1c253b; border-radius: 10px; padding: 16px;")
        b_layout = QHBoxLayout(banner)

        text_layout = QVBoxLayout()
        self.title_lbl = QLabel(tr("dns_banner_title"))
        self.title_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #58a6ff;")

        self.desc_lbl = QLabel(tr("dns_banner_desc"))
        self.desc_lbl.setStyleSheet("font-size: 12px; color: #8b949e;")
        text_layout.addWidget(self.title_lbl)
        text_layout.addWidget(self.desc_lbl)

        self.benchmark_btn = QPushButton(tr("dns_bench_btn"))
        self.benchmark_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                font-weight: 700;
                padding: 10px 20px;
                border-radius: 8px;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #2ea043; }
            QPushButton:pressed { background-color: #1a6f2b; }
        """)

        b_layout.addLayout(text_layout)
        b_layout.addStretch()
        b_layout.addWidget(self.benchmark_btn)
        layout.addWidget(banner)

        # Recommendation badge
        self.recom_lbl = QLabel("الخوادم الجاهزة للاختبار: Cloudflare (1.1.1.1) · Google (8.8.8.8) · Quad9 (9.9.9.9) · OpenDNS")
        self.recom_lbl.setStyleSheet("font-size: 12px; color: #58a6ff; font-weight: 600; padding: 4px 2px;")
        layout.addWidget(self.recom_lbl)

        self.table = QTableWidget(0, 6)
        self.apply_table_headers()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table, stretch=1)

    def apply_table_headers(self) -> None:
        self.table.setHorizontalHeaderLabels([
            tr("dns_col_rank"),
            tr("dns_col_name"),
            tr("dns_col_ip"),
            tr("dns_col_latency"),
            tr("dns_col_fail"),
            tr("dns_col_score"),
        ])

    def apply_language(self) -> None:
        self.title_lbl.setText(tr("dns_banner_title"))
        self.desc_lbl.setText(tr("dns_banner_desc"))
        self.benchmark_btn.setText(tr("dns_bench_btn"))
        self.apply_table_headers()

    def update_rankings(self, scores) -> None:
        self.table.setRowCount(0)
        for idx, s in enumerate(scores, start=1):
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            rank_item = QTableWidgetItem(f"#{idx}")
            rank_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, rank_item)

            self.table.setItem(row, 1, QTableWidgetItem(s.name))
            self.table.setItem(row, 2, QTableWidgetItem(s.ip))
            self.table.setItem(row, 3, QTableWidgetItem(f"{s.mean_latency_ms:.1f} ms"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{s.failure_rate * 100:.1f}%"))

            score_val = f"{s.composite_score:.1f} / 100"
            score_item = QTableWidgetItem(score_val)
            if s.composite_score >= 80.0:
                score_item.setForeground(Qt.green)
            elif s.composite_score >= 50.0:
                score_item.setForeground(Qt.yellow)
            else:
                score_item.setForeground(Qt.red)
            self.table.setItem(row, 5, score_item)

        if scores:
            best = scores[0]
            self.recom_lbl.setText(f"الخادم الأسرع حالياً: {best.name} ({best.ip}) بمتوسط سرعة استجابة {best.mean_latency_ms:.1f}ms 🟢")
            self.recom_lbl.setStyleSheet("font-size: 13px; color: #3fb950; font-weight: 700; padding: 4px 2px;")
