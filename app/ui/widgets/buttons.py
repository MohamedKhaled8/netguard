"""Button components for NetGuard AI.

Three standard button tiers: Primary, Secondary, Ghost.
100% token-compliant, 40px height, 10px radius, 13px font, focus ring #7AA2FF.
"""

from __future__ import annotations
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt
from app.ui import tokens


class PrimaryButton(QPushButton):
    """Primary action button with solid accent (ivory) background and dark text."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(40)
        self.setFont(tokens.get_sans_font(13, 600))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {tokens.ACCENT};
                color: {tokens.BG};
                border: 1px solid {tokens.ACCENT};
                border-radius: {tokens.RADIUS_BUTTON}px;
                padding: 0px 16px;
                font-size: 13px;
                font-weight: 600;
                min-width: 104px;
            }}
            QPushButton:hover {{
                background-color: #DCDBCF;
                border-color: #DCDBCF;
            }}
            QPushButton:pressed {{
                background-color: #C8C7BE;
                border-color: #C8C7BE;
            }}
            QPushButton:disabled {{
                background-color: {tokens.BAR_FUTURE};
                color: {tokens.TEXT_MUTED};
                border-color: {tokens.LINE};
            }}
            QPushButton:focus {{
                border: 2px solid {tokens.FOCUS_RING};
            }}
        """)


class SecondaryButton(QPushButton):
    """Secondary button with transparent background, 1px hairline border, and text."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(40)
        self.setFont(tokens.get_sans_font(13, 500))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #C9CCD0;
                border: 1px solid {tokens.LINE_STRONG};
                border-radius: {tokens.RADIUS_BUTTON}px;
                padding: 0px 16px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {tokens.SURFACE_HOVER};
                color: {tokens.TEXT};
                border-color: {tokens.LINE_STRONG};
            }}
            QPushButton:pressed {{
                background-color: {tokens.SURFACE};
            }}
            QPushButton:disabled {{
                color: {tokens.TEXT_MUTED};
                border-color: {tokens.LINE};
            }}
            QPushButton:focus {{
                border: 2px solid {tokens.FOCUS_RING};
            }}
        """)


class GhostButton(QPushButton):
    """Ghost button with transparent background, no border, and muted text."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(40)
        self.setFont(tokens.get_sans_font(13, 500))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {tokens.TEXT_MUTED};
                border: none;
                border-radius: {tokens.RADIUS_BUTTON}px;
                padding: 0px 16px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {tokens.SURFACE_HOVER};
                color: {tokens.TEXT};
            }}
            QPushButton:pressed {{
                background-color: {tokens.SURFACE};
            }}
            QPushButton:focus {{
                border: 2px solid {tokens.FOCUS_RING};
            }}
        """)
