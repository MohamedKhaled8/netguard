"""Autonomous Activity Feed Widget for NetGuard AI.

Provides a live, chronological stream of autonomous actions, self-healing events,
and predictive network verifications in plain human language.
"""

from __future__ import annotations
from typing import List, Dict
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QFrame,
)
from PySide6.QtCore import Qt


class ActivityItemWidget(QFrame):
    """Single event card in the autonomous activity stream."""

    def __init__(self, time_str: str, title: str, description: str, level: str = "success", parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #121927;
                border: 1px solid #1a2538;
                border-radius: 8px;
                padding: 10px;
            }
            QFrame:hover {
                border-color: #263854;
                background-color: #151e2e;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Status Dot
        dot_color = "#2ea043" if level == "success" else ("#e3b341" if level == "warning" else "#388bfd")
        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color: {dot_color}; font-size: 14px;")
        header_layout.addWidget(self.dot)

        # Title
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
        header_layout.addWidget(self.title_lbl)
        header_layout.addStretch()

        # Timestamp
        self.time_lbl = QLabel(time_str)
        self.time_lbl.setStyleSheet("font-size: 11px; color: #7d8590; font-weight: 500;")
        header_layout.addWidget(self.time_lbl)

        layout.addLayout(header_layout)

        # Description
        self.desc_lbl = QLabel(description)
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setStyleSheet("font-size: 12px; color: #9aa7b8; line-height: 1.4; margin-right: 18px;")
        layout.addWidget(self.desc_lbl)


class ActivityFeedWidget(QWidget):
    """Scrolling container of real-time autonomous events and verifications."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        title_row = QHBoxLayout()
        lbl = QLabel("سجل التدخل والذكاء الذاتي اللحظي (Autonomous Activity)")
        lbl.setStyleSheet("font-size: 14px; font-weight: 800; color: #e6edf3;")
        title_row.addWidget(lbl)
        title_row.addStretch()

        live_badge = QLabel("بث حي ومباشر 🟢")
        live_badge.setStyleSheet("font-size: 11px; font-weight: 700; color: #3fb950; background-color: #12241b; border: 1px solid #1a422d; border-radius: 10px; padding: 3px 10px;")
        title_row.addWidget(live_badge)
        main_layout.addLayout(title_row)

        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.item_layout = QVBoxLayout(self.container)
        self.item_layout.setContentsMargins(0, 0, 0, 0)
        self.item_layout.setSpacing(8)
        self.item_layout.addStretch()

        self.scroll.setWidget(self.container)
        main_layout.addWidget(self.scroll)

        self.events: List[ActivityItemWidget] = []

    def add_event(self, time_str: str, title: str, description: str, level: str = "success") -> None:
        """Add a new autonomous event at the top of the feed."""
        item = ActivityItemWidget(time_str, title, description, level=level)
        # Insert before the stretch
        self.item_layout.insertWidget(0, item)
        self.events.insert(0, item)

        # Keep last 25 events
        if len(self.events) > 25:
            oldest = self.events.pop()
            self.item_layout.removeWidget(oldest)
            oldest.deleteLater()
