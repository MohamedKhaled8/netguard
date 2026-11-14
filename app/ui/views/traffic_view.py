"""Application Traffic and Active Socket View."""

from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)


class TrafficView(QWidget):
    """Monitors running application processes, socket counts, and workload priorities."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        banner = QFrame()
        banner.setStyleSheet("background-color: #111625; border: 1px solid #1e2640; border-radius: 8px; padding: 14px;")
        b_layout = QVBoxLayout(banner)

        title = QLabel("APPLICATION-AWARE TRAFFIC INTELLIGENCE")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #58a6ff;")

        self.meeting_lbl = QLabel("Active Meeting Detection: None (No Zoom / Teams active)")
        self.meeting_lbl.setStyleSheet("font-size: 13px; color: #3fb950; font-weight: bold; margin-top: 4px;")

        b_layout.addWidget(title)
        b_layout.addWidget(self.meeting_lbl)
        layout.addWidget(banner)

        lbl = QLabel("ACTIVE NETWORK PROCESSES & SOCKETS")
        lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #e6edf3;")
        layout.addWidget(lbl)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["PID", "Process Name", "Category", "Priority", "Sockets"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

    def update_profiles(self, profiles, conferencing_active: bool = False) -> None:
        if conferencing_active:
            self.meeting_lbl.setText("Active Meeting Detected (Zoom/Teams) - High-Risk Recovery Actions Locked")
            self.meeting_lbl.setStyleSheet("font-size: 13px; color: #e3b341; font-weight: bold; margin-top: 4px;")
        else:
            self.meeting_lbl.setText("Active Meeting Detection: None (Standard Operations)")
            self.meeting_lbl.setStyleSheet("font-size: 13px; color: #3fb950; font-weight: bold; margin-top: 4px;")

        self.table.setRowCount(0)
        for p in profiles:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(p.pid)))
            self.table.setItem(row, 1, QTableWidgetItem(p.name))
            self.table.setItem(row, 2, QTableWidgetItem(p.category.value.upper()))
            self.table.setItem(row, 3, QTableWidgetItem(f"Priority {p.priority_level}"))
            self.table.setItem(row, 4, QTableWidgetItem(str(p.active_socket_count)))
