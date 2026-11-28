"""Segmented Control component for NetGuard AI.

Track: #0E1012 with 1px hairline #25292C, 4px padding, 10px radius.
Selected: bg #25292C, text #ECEBE6, 8px radius.
Unselected: transparent, text #9AA0A6.
"""

from __future__ import annotations
from typing import List
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, Signal
from app.ui import tokens


class SegmentedControl(QFrame):
    """Segmented switch button group."""

    current_changed = Signal(int, str)

    def __init__(self, options: List[str], initial_index: int = 0, parent=None) -> None:
        super().__init__(parent)
        self.options = options
        self.selected_index = initial_index
        self.buttons: List[QPushButton] = []

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {tokens.RANGE_TRACK};
                border: 1px solid {tokens.LINE};
                border-radius: 10px;
            }}
        """)
        self.setFixedHeight(46)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        for i, opt in enumerate(options):
            btn = QPushButton(tokens.bidi_isolate(opt))
            btn.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            btn.setFont(tokens.get_sans_font(13, 500))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(36)
            btn.clicked.connect(lambda checked=False, idx=i: self._on_button_clicked(idx))
            layout.addWidget(btn)
            self.buttons.append(btn)

        self._update_styles()

    def _on_button_clicked(self, idx: int) -> None:
        if self.selected_index != idx:
            self.selected_index = idx
            self._update_styles()
            self.current_changed.emit(idx, self.options[idx])

    def set_selected_index(self, idx: int) -> None:
        if 0 <= idx < len(self.options) and self.selected_index != idx:
            self.selected_index = idx
            self._update_styles()

    def _update_styles(self) -> None:
        for i, btn in enumerate(self.buttons):
            if i == self.selected_index:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {tokens.LINE};
                        color: {tokens.TEXT};
                        border: none;
                        border-radius: 7px;
                        padding: 0px 10px;
                        font-weight: 500;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {tokens.TEXT_MUTED};
                        border: none;
                        border-radius: 7px;
                        padding: 0px 10px;
                        font-weight: 500;
                    }}
                    QPushButton:hover {{
                        color: {tokens.TEXT};
                        background-color: {tokens.SURFACE_HOVER};
                    }}
                """)
