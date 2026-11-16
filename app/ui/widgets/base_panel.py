"""Base Panel component for NetGuard AI.

Clean flat graphite surface (#15181A), 1px hairline border (#25292C), 16px radius, 24px padding.
Optional entrance animation: subtle 8px rise + fade-in (600ms ease) when enabled.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QWidget,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint
from app.ui import tokens


class Panel(QFrame):
    """Universal flat container panel."""

    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        header_widget: Optional[QWidget] = None,
        parent: Optional[QWidget] = None,
        padding: int = 24,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("BasePanel")
        self.padding = padding
        self._animated_already = False

        self.setStyleSheet(f"""
            QFrame#BasePanel {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_PANEL}px;
            }}
        """)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(padding, padding, padding, padding)
        self.main_layout.setSpacing(16)

        # Header area (only if title or header_widget provided)
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(12)

        # Title & Subtitle column (RTL right)
        self.title_col = QVBoxLayout()
        self.title_col.setSpacing(4)

        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(tokens.get_sans_font(18, 600))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT}; background: transparent;")
        self.lbl_title.setWordWrap(False)
        self.title_col.addWidget(self.lbl_title)

        if subtitle:
            self.lbl_subtitle = QLabel(subtitle)
            self.lbl_subtitle.setFont(tokens.get_sans_font(13, 400))
            self.lbl_subtitle.setStyleSheet(f"color: {tokens.TEXT_MUTED}; background: transparent;")
            self.lbl_subtitle.setWordWrap(True)
            self.title_col.addWidget(self.lbl_subtitle)
        else:
            self.lbl_subtitle = None

        self.header_layout.addLayout(self.title_col)
        self.header_layout.addStretch()

        if header_widget is not None:
            self.header_layout.addWidget(header_widget)

        if title or header_widget is not None:
            self.main_layout.addLayout(self.header_layout)

    def set_header_widget(self, widget: QWidget) -> None:
        """Dynamically add or replace a header widget."""
        self.header_layout.addWidget(widget)

    def set_titles(self, title: str, subtitle: str = "") -> None:
        self.lbl_title.setText(title)
        if self.lbl_subtitle:
            self.lbl_subtitle.setText(subtitle)
