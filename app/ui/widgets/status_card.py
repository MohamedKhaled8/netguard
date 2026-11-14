"""Metric KPI Card Widget for NetGuard UI with explanatory micro-copy."""

from __future__ import annotations
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import Qt


class StatusCard(QFrame):
    """Reusable card showing metric title, bold value, unit, status tag, and explanatory tooltip."""

    def __init__(self, title: str, initial_value: str = "--", unit: str = "", desc: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setProperty("class", "Card")
        self.setStyleSheet("""
            QFrame.Card {
                background-color: #111625;
                border: 1px solid #1c253b;
                border-radius: 10px;
                padding: 8px;
            }
            QFrame.Card:hover {
                border-color: #2b3956;
                background-color: #131a2c;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(6)

        # Header Title
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-size: 13px; color: #8b949e; font-weight: 700;")
        layout.addWidget(self.title_lbl)

        # Value & Unit Row
        val_layout = QHBoxLayout()
        val_layout.setSpacing(6)
        self.val_lbl = QLabel(initial_value)
        self.val_lbl.setStyleSheet("font-size: 28px; font-weight: 800; color: #ffffff;")

        self.unit_lbl = QLabel(unit)
        self.unit_lbl.setStyleSheet("font-size: 12px; color: #58a6ff; font-weight: 600; margin-bottom: 4px;")
        self.unit_lbl.setAlignment(Qt.AlignBottom)

        val_layout.addWidget(self.val_lbl)
        val_layout.addWidget(self.unit_lbl)
        val_layout.addStretch()
        layout.addLayout(val_layout)

        # Status Tag / Quality
        self.status_pill = QLabel("نشط")
        self.status_pill.setStyleSheet("""
            font-size: 11px;
            font-weight: 700;
            color: #3fb950;
            background-color: #152720;
            border: 1px solid #1f4732;
            border-radius: 6px;
            padding: 3px 8px;
            max-width: 140px;
        """)
        layout.addWidget(self.status_pill)

        # Explanatory microcopy
        self.desc_lbl = QLabel(desc)
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setStyleSheet("font-size: 11px; color: #7d8590; margin-top: 4px; line-height: 1.4;")
        layout.addWidget(self.desc_lbl)

    def set_texts(self, title: str, unit: str, desc: str) -> None:
        self.title_lbl.setText(title)
        self.unit_lbl.setText(unit)
        self.desc_lbl.setText(desc)

    def update_metric(self, value_str: str, subtitle: str = "", is_warning: bool = False, is_critical: bool = False) -> None:
        self.val_lbl.setText(value_str)
        if subtitle:
            self.status_pill.setText(subtitle)

        if is_critical:
            self.val_lbl.setStyleSheet("font-size: 28px; font-weight: 800; color: #f85149;")
            self.status_pill.setStyleSheet("""
                font-size: 11px; font-weight: 700; color: #f85149;
                background-color: #2c1a1f; border: 1px solid #5a2027;
                border-radius: 6px; padding: 3px 8px;
            """)
        elif is_warning:
            self.val_lbl.setStyleSheet("font-size: 28px; font-weight: 800; color: #e3b341;")
            self.status_pill.setStyleSheet("""
                font-size: 11px; font-weight: 700; color: #e3b341;
                background-color: #2b2518; border: 1px solid #57461c;
                border-radius: 6px; padding: 3px 8px;
            """)
        else:
            self.val_lbl.setStyleSheet("font-size: 28px; font-weight: 800; color: #ffffff;")
            self.status_pill.setStyleSheet("""
                font-size: 11px; font-weight: 700; color: #3fb950;
                background-color: #152720; border: 1px solid #1f4732;
                border-radius: 6px; padding: 3px 8px;
            """)
