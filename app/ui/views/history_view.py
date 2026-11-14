"""Historical Incident Log View."""

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


class HistoryView(QWidget):
    """Historical database view of past network failures, diagnoses, and durations."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        banner = QFrame()
        banner.setStyleSheet("background-color: #111625; border: 1px solid #1e2640; border-radius: 8px; padding: 14px;")
        b_layout = QVBoxLayout(banner)

        title = QLabel("NETWORK INCIDENT HISTORY")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #58a6ff;")

        desc = QLabel("Persistent audit log of all detected network anomalies, outages, and degraded states.")
        desc.setStyleSheet("font-size: 13px; color: #8b949e;")

        b_layout.addWidget(title)
        b_layout.addWidget(desc)
        layout.addWidget(banner)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Probable Cause", "Confidence", "Severity", "Explanation"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

    def update_incidents(self, incidents) -> None:
        self.table.setRowCount(0)
        for inc in incidents:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(inc.timestamp.strftime("%Y-%m-%d %H:%M:%S")))
            self.table.setItem(row, 1, QTableWidgetItem(inc.probable_cause.value.upper()))
            self.table.setItem(row, 2, QTableWidgetItem(f"{inc.confidence * 100:.1f}%"))
            self.table.setItem(row, 3, QTableWidgetItem(inc.severity.value.upper()))
            self.table.setItem(row, 4, QTableWidgetItem(inc.explanation))
