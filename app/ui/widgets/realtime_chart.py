"""Real-time Telemetry Chart Widget powered by PyQtGraph."""

from __future__ import annotations
from typing import List
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class RealTimePlotWidget(QWidget):
    """High-performance real-time telemetry line plot."""

    def __init__(self, title: str, y_label: str = "ms", parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #e6edf3;")
        layout.addWidget(title_lbl)

        # Configure pyqtgraph plot
        pg.setConfigOption("background", "#111625")
        pg.setConfigOption("foreground", "#8b949e")
        pg.setConfigOption("antialias", True)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.15)
        self.plot_widget.setLabel("left", y_label, color="#8b949e")
        self.plot_widget.setLabel("bottom", "Samples", color="#8b949e")

        # Custom curve pen with sleek glow styling
        self.curve = self.plot_widget.plot(
            pen=pg.mkPen(color="#58a6ff", width=2.0),
            brush=pg.mkBrush(color=(88, 166, 255, 30)),
            fillLevel=0.0,
        )

        layout.addWidget(self.plot_widget)

    def update_data(self, y_values: List[float]) -> None:
        """Update live curve with latest sliding window data."""
        if not y_values:
            self.curve.setData([])
            return
        x = list(range(len(y_values)))
        self.curve.setData(x, y_values)
