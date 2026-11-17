"""Status and tag chips for NetGuard AI.

Fully rounded or bounded badges used strictly for real state:
- ok-soft (e.g. 'تم حله تلقائياً')
- bad-soft (e.g. 'يحتاج انتباهك', chart incident spike)
- tag-warn (e.g. 'محدود تلقائياً')
- tag-ok (e.g. 'أولوية عالية')
"""

from __future__ import annotations
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from app.ui import tokens


class Chip(QLabel):
    """Status chip badge."""

    def __init__(
        self,
        text: str = "",
        variant: str = "ok-soft",
        parent=None,
        radius: int = 999,
        font_size: int = 12,
    ) -> None:
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.variant = variant
        self.radius = radius
        self.font_size = font_size
        self.setFont(tokens.get_sans_font(font_size, 700))
        self.setMinimumHeight(24)
        self._apply_style()

    def set_variant(self, variant: str, text: str = "") -> None:
        self.variant = variant
        if text:
            self.setText(text)
        self._apply_style()

    def _apply_style(self) -> None:
        if self.variant == "ok-soft":
            bg = tokens.OK_SOFT_BG
            border = tokens.OK_SOFT_BORDER
            color = tokens.OK_SOFT_TEXT
        elif self.variant == "bad-soft":
            bg = tokens.BAD_SOFT_BG
            border = tokens.BAD_SOFT_BORDER
            color = tokens.BAD_SOFT_TEXT
        elif self.variant == "tag-warn":
            bg = tokens.SURFACE_INSET
            border = tokens.WARN_BORDER
            color = tokens.STATUS_WARN
        elif self.variant == "tag-ok":
            bg = tokens.SURFACE_INSET
            border = tokens.OK_SOFT_BORDER
            color = tokens.STATUS_OK
        else:
            bg = tokens.SURFACE_INSET
            border = tokens.LINE
            color = tokens.TEXT_MUTED

        rad = self.radius if self.radius != 999 else 12
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: {rad}px;
                color: {color};
                padding: 3px 12px;
                font-size: {self.font_size}px;
                font-weight: 700;
            }}
        """)
