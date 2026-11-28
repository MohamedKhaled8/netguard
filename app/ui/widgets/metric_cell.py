"""Metric Cell and Metrics Strip for NetGuard AI.

Four separate cards. Each card:
- 3px status rail (color is never the only cue; the footer repeats the state in text)
- 13px muted label
- Mono value + unit (LTR)
- Sparkline
- Footer: 7px status dot + 12px text
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
        self.setFrameShape(QFrame.NoFrame)
        self.setLineWidth(0)
        self.setMinimumWidth(110)
        self.setStyleSheet(f"""
            QFrame#MetricCell {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_INNER}px;
                outline: none;
            }}
            QFrame#MetricCell QLabel {{
                background: transparent;
                border: 0px solid transparent;
                padding: 0px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(8)

        self.status_rail = QFrame(self)
        self.status_rail.setFixedHeight(3)
        self.status_rail.setStyleSheet(
            f"background-color: {status_color}; border-radius: 2px; border: 0px solid transparent;"
        )
        layout.addWidget(self.status_rail)

        # 1. Muted Label (13px)
        self.title_lbl = QLabel(title)
        self.title_lbl.setFont(tokens.get_sans_font(12, 500))
        self.title_lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        layout.addWidget(self.title_lbl)

        # 2. Value Row (LTR): 22px mono value + 13px muted unit
        val_container = QWidget(self)
        val_container.setAttribute(Qt.WA_TranslucentBackground, True)
        val_container.setStyleSheet("background: transparent; border: 0px solid transparent;")
        val_container.setLayoutDirection(Qt.LeftToRight)
        val_container.setMinimumHeight(34)
        val_row = QHBoxLayout(val_container)
        val_row.setContentsMargins(0, 0, 0, 0)
        val_row.setSpacing(6)
        val_row.setAlignment(Qt.AlignLeft)

        self.val_lbl = QLabel(initial_val)
        self.val_lbl.setFont(tokens.get_mono_font(24, 600))
        self.val_lbl.setStyleSheet(f"color: {tokens.TEXT};")
        self.val_lbl.setMinimumHeight(28)

        self.unit_lbl = QLabel(unit)
        self.unit_lbl.setFont(tokens.get_sans_font(12, 400))
        self.unit_lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED}; padding-top: 6px;")

        val_row.addWidget(self.val_lbl)
        val_row.addWidget(self.unit_lbl)
        val_row.addStretch()
        layout.addWidget(val_container)

        # 3. Sparkline (36px high)
        self.sparkline = Sparkline(
            samples=initial_samples if initial_samples is not None else [],
            color=status_color,
            parent=self,
        )
        self.sparkline.setFixedHeight(36)
        self.sparkline.setAttribute(Qt.WA_TranslucentBackground, True)
        self.sparkline.setStyleSheet("background: transparent; border: 0px solid transparent;")
        layout.addWidget(self.sparkline)

        # 4. Footer: 7px status dot + 12px muted text
        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 0, 0, 0)
        footer_row.setSpacing(6)

        self.dot = QFrame()
        self.dot.setFixedSize(7, 7)
        self.dot.setStyleSheet(f"background-color: {status_color}; border-radius: 3px; border: none;")

        self.footer_lbl = QLabel(footer_text)
        self.footer_lbl.setFont(tokens.get_sans_font(12, 500))
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
        if self.val_lbl.text() != val_str:
            self.val_lbl.setText(val_str)
        if footer_text and self.footer_lbl.text() != footer_text:
            self.footer_lbl.setText(footer_text)

        if status_color:
            color = status_color
        elif is_warning:
            color = tokens.STATUS_WARN
        elif val_str.strip() in ("—", "-"):
            color = tokens.TEXT_MUTED
        else:
            color = tokens.STATUS_OK

        if self.status_color != color:
            self.status_color = color
            self.dot.setStyleSheet(f"background-color: {color}; border-radius: 3.5px;")
            self.status_rail.setStyleSheet(
                f"background-color: {color}; border-radius: 2px; border: 0px solid transparent;"
            )
        if samples is not None:
            self.sparkline.set_data(samples, color)
        else:
            if getattr(self.sparkline, "color", None) != color:
                self.sparkline.color = color
                self.sparkline.update()


class MetricsStrip(QFrame):
    """The 4-cell Metrics Strip container separated by 1px hairlines."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("MetricsStripContainer")
        self.setFrameShape(QFrame.NoFrame)
        self.setLineWidth(0)
        self.setStyleSheet(f"""
            QFrame#MetricsStripContainer {{
                background-color: transparent;
                border: 0px solid transparent;
            }}
            QFrame#MetricsStripContainer QLabel {{
                border: 0px solid transparent;
                background: transparent;
                padding: 0px;
            }}
        """)

        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(12)

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
