"""Historical Incident Log View.

Historical database view of past network failures, diagnoses, and durations,
presented in clear, accessible language.
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


class HistoryView(QWidget):
    """Historical database view of past network failures, diagnoses, and durations."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        banner = QFrame()
        banner.setStyleSheet("background-color: #111625; border: 1px solid #1c253b; border-radius: 10px; padding: 16px;")
        b_layout = QHBoxLayout(banner)

        text_layout = QVBoxLayout()
        self.title_lbl = QLabel(tr("hist_banner_title"))
        self.title_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #58a6ff;")

        self.desc_lbl = QLabel(tr("hist_banner_desc"))
        self.desc_lbl.setStyleSheet("font-size: 12px; color: #8b949e;")
        text_layout.addWidget(self.title_lbl)
        text_layout.addWidget(self.desc_lbl)
        b_layout.addLayout(text_layout)
        b_layout.addStretch()

        layout.addWidget(banner)

        self.table = QTableWidget(0, 5)
        self.apply_table_headers()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table, stretch=1)

    def apply_table_headers(self) -> None:
        self.table.setHorizontalHeaderLabels([
            tr("hist_col_time"),
            tr("hist_col_cause"),
            tr("hist_col_conf"),
            tr("hist_col_sev"),
            tr("hist_col_desc"),
        ])

    def apply_language(self) -> None:
        self.title_lbl.setText(tr("hist_banner_title"))
        self.desc_lbl.setText(tr("hist_banner_desc"))
        self.apply_table_headers()

    def update_incidents(self, incidents) -> None:
        self.table.setRowCount(0)
        for inc in incidents:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(inc.timestamp.strftime("%Y-%m-%d %H:%M:%S")))
            
            cause_key = f"cause_{inc.probable_cause.value}"
            cause_name = tr(cause_key, inc.probable_cause.value.replace("_", " ").upper())
            self.table.setItem(row, 1, QTableWidgetItem(cause_name))
            
            self.table.setItem(row, 2, QTableWidgetItem(f"{inc.confidence * 100:.1f}%"))
            
            sev_trans = "عادي" if inc.severity.value == "info" else ("متوسط" if inc.severity.value == "warning" else "حرج")
            self.table.setItem(row, 3, QTableWidgetItem(sev_trans))
            self.table.setItem(row, 4, QTableWidgetItem(inc.explanation))
