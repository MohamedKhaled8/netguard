"""Autonomous Remediation and Self-Healing View."""

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


class RemediationView(QWidget):
    """Inspects autonomous action registry, circuit breakers, and verification audit trail."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Overview banner
        banner = QFrame()
        banner.setStyleSheet("background-color: #111625; border: 1px solid #1e2640; border-radius: 8px; padding: 14px;")
        b_layout = QVBoxLayout(banner)

        title = QLabel("AUTONOMOUS SELF-HEALING ENGINE")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #58a6ff;")

        desc = QLabel("Policy-governed recovery: Preconditions -> Execution -> Post-Verification -> Automatic Rollback.")
        desc.setStyleSheet("font-size: 13px; color: #8b949e;")

        b_layout.addWidget(title)
        b_layout.addWidget(desc)
        layout.addWidget(banner)

        # Audit Table
        lbl = QLabel("REMEDIATION AUDIT LOG (IMMUTABLE TRAIL)")
        lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #e6edf3;")
        layout.addWidget(lbl)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Timestamp", "Action ID", "Risk Level", "Status", "Exec Time", "Verification", "Rollback"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

    def update_audit_log(self, records) -> None:
        self.table.setRowCount(0)
        for r in records:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(r.timestamp.strftime("%H:%M:%S")))
            self.table.setItem(row, 1, QTableWidgetItem(r.action_name))
            self.table.setItem(row, 2, QTableWidgetItem(r.risk_level.value.upper()))

            status_item = QTableWidgetItem(r.status.value.upper())
            self.table.setItem(row, 3, status_item)

            self.table.setItem(row, 4, QTableWidgetItem(f"{r.execution_duration_ms:.1f}ms"))
            self.table.setItem(row, 5, QTableWidgetItem(f"{r.verification_duration_ms:.1f}ms"))
            self.table.setItem(row, 6, QTableWidgetItem("YES (Success)" if r.rollback_performed else "NO"))
