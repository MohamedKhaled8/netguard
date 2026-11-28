"""Button components for NetGuard AI.

Three standard button tiers: Primary (Electric Blue), Secondary (Hairline), Ghost.
"""

from __future__ import annotations
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt
from app.ui import tokens


class PrimaryButton(QPushButton):
    """Primary action button with electric blue fill and high-contrast white label."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(38)
        self.setFont(tokens.get_sans_font(13, 600))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {tokens.ACCENT};
                color: {tokens.ON_ACCENT};
                border: 1px solid {tokens.ACCENT};
                border-radius: {tokens.RADIUS_BUTTON}px;
                padding: 0px 16px;
                font-size: 13px;
                font-weight: 600;
                min-width: 96px;
            }}
            QPushButton:hover {{
                background-color: {tokens.ACCENT_HOVER};
                border-color: {tokens.ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {tokens.ACCENT_PRESSED};
                border-color: {tokens.ACCENT_PRESSED};
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
    """Secondary button with inset navy fill, hairline border, and crisp text."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(38)
        self.setFont(tokens.get_sans_font(13, 500))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {tokens.SURFACE_INSET};
                color: {tokens.TEXT_SECONDARY};
                border: 1px solid {tokens.LINE_STRONG};
                border-radius: {tokens.RADIUS_BUTTON}px;
                padding: 0px 14px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {tokens.SURFACE_HOVER};
                color: {tokens.TEXT};
                border-color: {tokens.LINE_THRESHOLD};
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
    """Ghost button with transparent background and muted text."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)
        self.setFont(tokens.get_sans_font(13, 500))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {tokens.TEXT_MUTED};
                border: 0px solid transparent;
                border-radius: {tokens.RADIUS_BUTTON}px;
                padding: 0px 12px;
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
