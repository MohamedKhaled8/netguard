"""Metric Cell and Metrics Strip for NetGuard AI.

One container (radius 16, 1px line outline, cells separated by 1px line gaps):
Each cell:
- Top: 13px muted label
- Value row: 38px mono value + 13px muted unit (LTR)
- Sparkline: 32px high, 1.6px line width, status color
- Footer: 7px status dot + 12px muted text
"""

from __future__ import annotations
from typing import List, Optional
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QWidget,
    QGridLayout,
)
from PySide6.QtCore import Qt
from app.ui import tokens
from app.ui.widgets.sparkline import Sparkline


class MetricCell(QFrame):
    """Single metric tile inside the metrics strip."""

    def __init__(
        self,
        title: str,
        initial_val: str = " — ",
        unit: str = "",
        footer_text: str = "بانتظار القياس...",
        status_color: str = tokens.TEXT_MUTED,
        initial_samples: Optional[List[float]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.status_color = status_color
        self.setObjectName("MetricCell")
        self.setMinimumWidth(210)
        self.setFixedHeight(180)

        self.setStyleSheet(f"""
            QFrame#MetricCell {{
                background-color: {tokens.SURFACE};
                border: none;
            }}
            QFrame#MetricCell QLabel {{
                border: none;
                background: transparent;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(6)

        # 1. Muted Label (13px)
        self.title_lbl = QLabel(title)
        self.title_lbl.setFont(tokens.get_sans_font(13, 400))
        self.title_lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        layout.addWidget(self.title_lbl)

        # 2. Value Row (LTR): 38px mono value + 13px muted unit
        val_container = QWidget(self)
        val_container.setLayoutDirection(Qt.LeftToRight)
        val_container.setFixedHeight(48)
        val_row = QHBoxLayout(val_container)
        val_row.setContentsMargins(0, 0, 0, 0)
        val_row.setSpacing(6)
        val_row.setAlignment(Qt.AlignLeft)

        self.val_lbl = QLabel(initial_val)
        self.val_lbl.setFont(tokens.get_mono_font(38, 500))
        self.val_lbl.setStyleSheet(f"color: {tokens.TEXT};")
        self.val_lbl.setFixedHeight(46)

        self.unit_lbl = QLabel(unit)
        self.unit_lbl.setFont(tokens.get_sans_font(13, 400))
        self.unit_lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED}; padding-top: 14px;")

        val_row.addWidget(self.val_lbl)
        val_row.addWidget(self.unit_lbl)
        val_row.addStretch()
        layout.addWidget(val_container)

        # 3. Sparkline (32px high)
        self.sparkline = Sparkline(
            samples=initial_samples if initial_samples is not None else [],
            color=status_color,
            parent=self,
        )
        layout.addWidget(self.sparkline)

        # 4. Footer: 7px status dot + 12px muted text
        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 0, 0, 0)
        footer_row.setSpacing(6)

        self.dot = QLabel()
        self.dot.setFixedSize(7, 7)
        self.dot.setStyleSheet(f"background-color: {status_color}; border-radius: 3.5px;")

        self.footer_lbl = QLabel(footer_text)
        self.footer_lbl.setFont(tokens.get_sans_font(12, 400))
        self.footer_lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED};")

        footer_row.addWidget(self.dot)
        footer_row.addWidget(self.footer_lbl)
        footer_row.addStretch()
        layout.addLayout(footer_row)

    def update_metric(
        self,
        val_str: str,
        footer_text: str = "",
        is_warning: bool = False,
        samples: Optional[List[float]] = None,
        status_color: Optional[str] = None,
    ) -> None:
        self.val_lbl.setText(val_str)
        if footer_text:
            self.footer_lbl.setText(footer_text)

        if status_color:
            color = status_color
        elif is_warning:
            color = tokens.STATUS_WARN
        elif val_str.strip() in ("—", "-"):
            color = tokens.TEXT_MUTED
        else:
            color = tokens.STATUS_OK

        self.status_color = color
        self.dot.setStyleSheet(f"background-color: {color}; border-radius: 3.5px;")
        if samples is not None:
            self.sparkline.set_data(samples, color)
        else:
            self.sparkline.color = color
            self.sparkline.update()


class MetricsStrip(QFrame):
    """The 4-cell Metrics Strip container separated by 1px hairlines."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("MetricsStripContainer")
        self.setStyleSheet(f"""
            QFrame#MetricsStripContainer {{
                background-color: {tokens.LINE};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_PANEL}px;
            }}
            QFrame#MetricsStripContainer QLabel {{
                border: none;
                background: transparent;
            }}
        """)

        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(1, 1, 1, 1)
        self.grid_layout.setSpacing(1)

        # 4 Cells:
        # In RTL: cell 0 (rightmost) is latency, cell 1 is jitter, cell 2 is loss, cell 3 is download
        self.cell_latency = MetricCell(
            title="زمن الاستجابة",
            initial_val=" — ",
            unit="ms",
            footer_text="بانتظار القياس...",
            status_color=tokens.TEXT_MUTED,
            initial_samples=[],
        )

        self.cell_jitter = MetricCell(
            title="التذبذب",
            initial_val=" — ",
            unit="ms",
            footer_text="بانتظار القياس...",
            status_color=tokens.TEXT_MUTED,
            initial_samples=[],
        )

        self.cell_loss = MetricCell(
            title="فقدان الحزم",
            initial_val=" — ",
            unit="%",
            footer_text="بانتظار القياس...",
            status_color=tokens.TEXT_MUTED,
            initial_samples=[],
        )

        self.cell_download = MetricCell(
            title="سرعة التنزيل",
            initial_val=" — ",
            unit="Mbps",
            footer_text="بانتظار القياس...",
            status_color=tokens.TEXT_MUTED,
            initial_samples=[],
        )

        self.cells = [self.cell_latency, self.cell_jitter, self.cell_loss, self.cell_download]
        self._set_4x1_layout()

    def _set_4x1_layout(self) -> None:
        for i, cell in enumerate(self.cells):
            self.grid_layout.addWidget(cell, 0, i)

    def set_responsive_columns(self, cols: int) -> None:
        for cell in self.cells:
            self.grid_layout.removeWidget(cell)

        if cols == 4:
            for i, cell in enumerate(self.cells):
                self.grid_layout.addWidget(cell, 0, i)
        elif cols == 2:
            self.grid_layout.addWidget(self.cell_latency, 0, 0)
            self.grid_layout.addWidget(self.cell_jitter, 0, 1)
            self.grid_layout.addWidget(self.cell_loss, 1, 0)
            self.grid_layout.addWidget(self.cell_download, 1, 1)
        else:
            for i, cell in enumerate(self.cells):
                self.grid_layout.addWidget(cell, i, 0)
