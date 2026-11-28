"""Global standardized status badge implementing NetGuard's 10 canonical states."""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QWidget
from app.ui import tokens


class StatusBadge(QFrame):
    """Consistent status indicator badge across the entire NetGuard AI shell and views."""

    def __init__(
        self,
        status: tokens.SystemStatus | str = tokens.SystemStatus.WAITING,
        label: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("GlobalStatusBadge")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(36)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 4, 10, 4)
        lay.setSpacing(6)

        self.dot = QFrame(self)
        self.dot.setFixedSize(7, 7)
        lay.addWidget(self.dot)

        self.lbl = QLabel(label, self)
        self.lbl.setFont(tokens.get_sans_font(12, 600))
        self.lbl.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        lay.addWidget(self.lbl)

        self._status = tokens.SystemStatus.WAITING.value
        self.set_status(status, label or None)

    def set_status(self, status: tokens.SystemStatus | str, label: Optional[str] = None) -> None:
        val = status.value if isinstance(status, tokens.SystemStatus) else str(status).lower()
        self._status = val
        fg, bg, border = tokens.STATUS_COLOR_MAP.get(
            val, (tokens.TEXT_MUTED, tokens.SURFACE_INSET, tokens.LINE)
        )
        if label is not None:
            self.lbl.setText(label)
        self.dot.setStyleSheet(f"background-color: {fg}; border-radius: 3px; border: 0px solid transparent;")
        self.lbl.setStyleSheet(f"color: {fg}; background: transparent; border: 0px solid transparent;")
        self.setStyleSheet(
            f"""
            QFrame#GlobalStatusBadge {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 18px;
            }}
            """
        )
        self.lbl.adjustSize()
        self.adjustSize()
        self.updateGeometry()
