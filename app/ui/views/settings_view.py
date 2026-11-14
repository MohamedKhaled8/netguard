"""Settings and Operating Mode Configuration View."""

from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QPushButton,
)


class SettingsView(QWidget):
    """Configuration interface for autonomous mode, probe intervals, and thresholds."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        banner = QFrame()
        banner.setStyleSheet("background-color: #111625; border: 1px solid #1e2640; border-radius: 8px; padding: 14px;")
        b_layout = QVBoxLayout(banner)

        title = QLabel("SYSTEM CONFIGURATION & POLICIES")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #58a6ff;")

        desc = QLabel("Configure autonomous self-healing modes, probe pacing, and diagnostic thresholds.")
        desc.setStyleSheet("font-size: 13px; color: #8b949e;")

        b_layout.addWidget(title)
        b_layout.addWidget(desc)
        layout.addWidget(banner)

        form_frame = QFrame()
        form_frame.setStyleSheet("background-color: #111625; border: 1px solid #1e2640; border-radius: 8px; padding: 16px;")
        form_layout = QFormLayout(form_frame)
        form_layout.setSpacing(12)

        # Mode selector
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["autonomous_safe", "assisted", "observation"])
        form_layout.addRow(QLabel("Operating Mode:"), self.mode_combo)

        # Gateway interval
        self.gw_interval_spin = QDoubleSpinBox()
        self.gw_interval_spin.setRange(0.5, 30.0)
        self.gw_interval_spin.setValue(1.0)
        self.gw_interval_spin.setSuffix(" sec")
        form_layout.addRow(QLabel("Gateway Probe Interval:"), self.gw_interval_spin)

        # External interval
        self.ext_interval_spin = QDoubleSpinBox()
        self.ext_interval_spin.setRange(1.0, 60.0)
        self.ext_interval_spin.setValue(3.0)
        self.ext_interval_spin.setSuffix(" sec")
        form_layout.addRow(QLabel("External Probe Interval:"), self.ext_interval_spin)

        # DNS interval
        self.dns_interval_spin = QDoubleSpinBox()
        self.dns_interval_spin.setRange(1.0, 120.0)
        self.dns_interval_spin.setValue(5.0)
        self.dns_interval_spin.setSuffix(" sec")
        form_layout.addRow(QLabel("DNS Probe Interval:"), self.dns_interval_spin)

        self.apply_btn = QPushButton("Save & Apply Settings")
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: #ffffff;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #388bfd; }
        """)
        form_layout.addRow(QLabel(""), self.apply_btn)

        layout.addWidget(form_frame)
        layout.addStretch()
