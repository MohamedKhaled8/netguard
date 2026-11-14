"""Application Traffic and Active Socket View.

Monitors running application processes, socket counts, and workload priorities,
protecting active video calls (Zoom, Teams) from disruptive interference.
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


class TrafficView(QWidget):
    """Monitors running application processes, socket counts, and workload priorities."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        banner = QFrame()
        banner.setStyleSheet("background-color: #111625; border: 1px solid #1c253b; border-radius: 10px; padding: 16px;")
        b_layout = QVBoxLayout(banner)
        b_layout.setSpacing(10)

        top_row = QHBoxLayout()
        text_layout = QVBoxLayout()
        self.title_lbl = QLabel(tr("traffic_banner_title"))
        self.title_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #58a6ff;")

        self.meeting_lbl = QLabel(tr("traffic_meeting_none"))
        self.meeting_lbl.setStyleSheet("font-size: 13px; color: #3fb950; font-weight: 700; margin-top: 4px;")
        text_layout.addWidget(self.title_lbl)
        text_layout.addWidget(self.meeting_lbl)
        top_row.addLayout(text_layout)
        top_row.addStretch()

        self.btn_refresh = QPushButton(tr("traffic_scan_btn"))
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: #ffffff;
                font-weight: 700;
                padding: 9px 18px;
                border-radius: 8px;
                border: 1px solid #388bfd;
            }
            QPushButton:hover { background-color: #388bfd; }
        """)
        top_row.addWidget(self.btn_refresh)
        b_layout.addLayout(top_row)
        layout.addWidget(banner)

        self.sec_lbl = QLabel("البرامج والعمليات المتصلة بالإنترنت حالياً")
        self.sec_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #e6edf3;")
        layout.addWidget(self.sec_lbl)

        self.table = QTableWidget(0, 5)
        self.apply_table_headers()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table, stretch=1)

    def apply_table_headers(self) -> None:
        self.table.setHorizontalHeaderLabels([
            tr("traffic_col_pid"),
            tr("traffic_col_name"),
            tr("traffic_col_cat"),
            tr("traffic_col_prio"),
            tr("traffic_col_sockets"),
        ])

    def apply_language(self) -> None:
        self.title_lbl.setText(tr("traffic_banner_title"))
        self.meeting_lbl.setText(tr("traffic_meeting_none"))
        self.btn_refresh.setText(tr("traffic_scan_btn"))
        self.sec_lbl.setText("البرامج والعمليات المتصلة بالإنترنت حالياً")
        self.apply_table_headers()

    def update_profiles(self, profiles, conferencing_active: bool = False) -> None:
        if conferencing_active:
            self.meeting_lbl.setText(tr("traffic_meeting_active"))
            self.meeting_lbl.setStyleSheet("font-size: 13px; color: #e3b341; font-weight: 700; margin-top: 4px;")
        else:
            self.meeting_lbl.setText(tr("traffic_meeting_none"))
            self.meeting_lbl.setStyleSheet("font-size: 13px; color: #3fb950; font-weight: 700; margin-top: 4px;")

        self.table.setRowCount(0)
        for p in profiles:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(p.pid)))
            self.table.setItem(row, 1, QTableWidgetItem(p.name))
            self.table.setItem(row, 2, QTableWidgetItem(p.category.value if hasattr(p.category, "value") else str(p.category)))
            self.table.setItem(row, 3, QTableWidgetItem(str(p.priority_level) if hasattr(p, "priority_level") else "عادي"))
            self.table.setItem(row, 4, QTableWidgetItem(str(len(p.active_sockets) if hasattr(p, "active_sockets") else p.open_sockets)))
