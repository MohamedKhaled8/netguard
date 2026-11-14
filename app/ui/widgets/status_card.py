"""Metric KPI Card Widget for NetGuard UI."""

from __future__ import annotations
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import Qt


class StatusCard(QFrame):
    """Reusable card showing metric title, big bold value, unit, and health indicator."""

    def __init__(self, title: str, initial_value: str = "--", unit: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setProperty("class", "Card")
        self.setStyleSheet("""
            QFrame.Card {
                background-color: #111625;
                border: 1px solid #1e2640;
                border-radius: 8px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-size: 11px; color: #8b949e; font-weight: 600; text-transform: uppercase;")

        val_layout = QHBoxLayout()
        val_layout.setSpacing(4)
        self.val_lbl = QLabel(initial_value)
        self.val_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")

        self.unit_lbl = QLabel(unit)
        self.unit_lbl.setStyleSheet("font-size: 12px; color: #8b949e; margin-bottom: 3px;")
        self.unit_lbl.setAlignment(Qt.AlignBottom)

        val_layout.addWidget(self.val_lbl)
        val_layout.addWidget(self.unit_lbl)
        val_layout.addStretch()

        self.subtitle_lbl = QLabel("Monitoring")
        self.subtitle_lbl.setStyleSheet("font-size: 11px; color: #3fb950;")

        layout.addWidget(self.title_lbl)
        layout.addLayout(val_layout)
        layout.addWidget(self.subtitle_lbl)

    def update_metric(self, value_str: str, subtitle: str = "", is_warning: bool = False, is_critical: bool = False) -> None:
        self.val_lbl.setText(value_str)
        if subtitle:
            self.subtitle_lbl.setText(subtitle)

        if is_critical:
            self.val_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #f85149;")
            self.subtitle_lbl.setStyleSheet("font-size: 11px; color: #f85149;")
        elif is_warning:
            self.val_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #e3b341;")
            self.subtitle_lbl.setStyleSheet("font-size: 11px; color: #e3b341;")
        else:
            self.val_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")
            self.subtitle_lbl.setStyleSheet("font-size: 11px; color: #3fb950;")
