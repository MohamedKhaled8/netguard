"""Diagnostic Center View for NetGuard AI Desktop."""

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
)
from PySide6.QtCore import Qt


class DiagnosisView(QWidget):
    """Deep inspection of root causes, confidence calculations, and differential evidence."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header card
        header = QFrame()
        header.setStyleSheet("background-color: #111625; border: 1px solid #1e2640; border-radius: 8px; padding: 14px;")
        h_layout = QVBoxLayout(header)

        title = QLabel("DIAGNOSTIC & ROOT-CAUSE CENTER")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #58a6ff;")

        self.cause_lbl = QLabel("CURRENT CAUSE: HEALTHY")
        self.cause_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #3fb950; margin-top: 6px;")

        self.explanation_lbl = QLabel("All network telemetry indicators are within normal operating bounds.")
        self.explanation_lbl.setStyleSheet("font-size: 13px; color: #8b949e;")

        self.conf_lbl = QLabel("Confidence: 100.0% | Severity: INFO | Auto-Remediation Authorized: False")
        self.conf_lbl.setStyleSheet("font-size: 11px; color: #8b949e; margin-top: 4px;")

        h_layout.addWidget(title)
        h_layout.addWidget(self.cause_lbl)
        h_layout.addWidget(self.explanation_lbl)
        h_layout.addWidget(self.conf_lbl)
        layout.addWidget(header)

        # Evidence Table
        sec_title = QLabel("EMPIRICAL EVIDENCE ACCUMULATOR")
        sec_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #e6edf3;")
        layout.addWidget(sec_title)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Metric Vector", "Target", "Observed Value", "Threshold", "Condition Evaluation"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("background-color: #111625; border: 1px solid #1e2640; border-radius: 6px;")
        layout.addWidget(self.table)

    def update_diagnosis(self, diagnosis) -> None:
        cause_name = diagnosis.probable_cause.value.replace("_", " ").upper()
        color = "#3fb950" if diagnosis.probable_cause.value == "healthy" else "#f85149"
        self.cause_lbl.setText(f"CURRENT CAUSE: {cause_name}")
        self.cause_lbl.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {color}; margin-top: 6px;")
        self.explanation_lbl.setText(diagnosis.explanation)
        self.conf_lbl.setText(
            f"Confidence: {diagnosis.confidence * 100:.1f}% | "
            f"Severity: {diagnosis.severity.value.upper()} | "
            f"Auto-Remediation Authorized: {diagnosis.auto_remediation_permitted}"
        )

        # Populate evidence
        self.table.setRowCount(0)
        for ev in diagnosis.supporting_evidence:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(ev.metric_type.value))
            self.table.setItem(row, 1, QTableWidgetItem(ev.target))
            self.table.setItem(row, 2, QTableWidgetItem(str(round(ev.observed_value, 2))))
            self.table.setItem(row, 3, QTableWidgetItem(str(round(ev.threshold_value, 2))))
            self.table.setItem(row, 4, QTableWidgetItem(ev.condition))
