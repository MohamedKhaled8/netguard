"""Autonomous Remediation and Self-Healing View.

Inspects action registry, circuit breakers, and verification audit trail,
with immediate manual trigger capabilities.
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


class RemediationView(QWidget):
    """Inspects autonomous action registry, circuit breakers, and verification audit trail."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Overview banner
        banner = QFrame()
        banner.setStyleSheet("background-color: #111625; border: 1px solid #1c253b; border-radius: 10px; padding: 16px;")
        b_layout = QVBoxLayout(banner)
        b_layout.setSpacing(10)

        top_row = QHBoxLayout()
        text_col = QVBoxLayout()
        self.title_lbl = QLabel(tr("rem_banner_title"))
        self.title_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #58a6ff;")

        self.desc_lbl = QLabel(tr("rem_banner_desc"))
        self.desc_lbl.setStyleSheet("font-size: 12px; color: #8b949e;")
        text_col.addWidget(self.title_lbl)
        text_col.addWidget(self.desc_lbl)
        top_row.addLayout(text_col)
        top_row.addStretch()

        self.btn_flush_now = QPushButton(tr("rem_flush_btn"))
        self.btn_flush_now.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                font-weight: 700;
                padding: 8px 16px;
                border-radius: 7px;
                border: none;
            }
            QPushButton:hover { background-color: #2ea043; }
        """)

        self.btn_recheck_now = QPushButton(tr("rem_recheck_btn"))
        self.btn_recheck_now.setStyleSheet("""
            QPushButton {
                background-color: #1c263c;
                color: #c9d1d9;
                font-weight: 600;
                padding: 8px 16px;
                border-radius: 7px;
                border: 1px solid #2a3754;
            }
            QPushButton:hover { background-color: #263350; color: #ffffff; }
        """)

        top_row.addWidget(self.btn_flush_now)
        top_row.addWidget(self.btn_recheck_now)
        b_layout.addLayout(top_row)
        layout.addWidget(banner)

        # Audit Table
        self.lbl_audit = QLabel("سجل عمليات الإصلاح المسجلة (Audit Trail)")
        self.lbl_audit.setStyleSheet("font-size: 14px; font-weight: 700; color: #e6edf3;")
        layout.addWidget(self.lbl_audit)

        self.table = QTableWidget(0, 7)
        self.apply_table_headers()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table, stretch=1)

    def apply_table_headers(self) -> None:
        self.table.setHorizontalHeaderLabels([
            tr("rem_col_time"),
            tr("rem_col_action"),
            tr("rem_col_risk"),
            tr("rem_col_status"),
            tr("rem_col_duration"),
            tr("rem_col_verify"),
            tr("rem_col_rollback"),
        ])

    def apply_language(self) -> None:
        self.title_lbl.setText(tr("rem_banner_title"))
        self.desc_lbl.setText(tr("rem_banner_desc"))
        self.btn_flush_now.setText(tr("rem_flush_btn"))
        self.btn_recheck_now.setText(tr("rem_recheck_btn"))
        self.lbl_audit.setText("سجل عمليات الإصلاح المسجلة (Audit Trail)")
        self.apply_table_headers()

    def update_audit_log(self, records) -> None:
        self.table.setRowCount(0)
        for r in records:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(r.timestamp.strftime("%H:%M:%S")))
            self.table.setItem(row, 1, QTableWidgetItem(r.action_name))
            
            risk_text = "آمن (منخفض)" if "low" in r.risk_level.value else ("محكوم" if "controlled" in r.risk_level.value else "تخريبي")
            self.table.setItem(row, 2, QTableWidgetItem(risk_text))

            status_text = "ناجح ✓" if r.status.value == "success" else ("فشل ✗" if r.status.value == "failed" else r.status.value)
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(Qt.green if r.status.value == "success" else Qt.red)
            self.table.setItem(row, 3, status_item)

            self.table.setItem(row, 4, QTableWidgetItem(f"{r.execution_duration_ms:.1f}ms"))
            self.table.setItem(row, 5, QTableWidgetItem(f"{r.verification_duration_ms:.1f}ms"))
            self.table.setItem(row, 6, QTableWidgetItem("نعم" if r.rollback_performed else "لا"))
