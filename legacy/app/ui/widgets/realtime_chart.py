"""RealTimePlotWidget backwards-compatibility wrapper for NetGuard UI.

100% token-compliant, dark warm-neutral graphite (#0E1012 / #15181A).
No glowing blue, no neon.
"""

from __future__ import annotations
from typing import List
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from app.ui import tokens
from app.ui.widgets.sparkline import Sparkline


class RealTimePlotWidget(QWidget):
    """Token-compliant real-time telemetry line plot."""

    def __init__(self, title: str, y_label: str = "ms", parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.title_lbl = QLabel(title)
        self.title_lbl.setFont(tokens.get_sans_font(13, 500))
        self.title_lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        layout.addWidget(self.title_lbl)

        self.sparkline = Sparkline(samples=[20.0] * 24, color=tokens.ACCENT, parent=self)
        self.sparkline.setFixedHeight(48)
        layout.addWidget(self.sparkline)

    def update_data(self, y_values: List[float]) -> None:
        """Update curve with latest telemetry samples."""
        if not y_values:
            return
        self.sparkline.set_data(y_values, color=tokens.ACCENT)
