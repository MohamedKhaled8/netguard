"""Incident 4-step Timeline Widget for NetGuard AI.

Panel 'ما الذي حدث بالضبط؟':
- Top-end status chip ('تم حله تلقائياً' / 'يحتاج انتباهك')
- 4-step vertical timeline on a 1px rail (#2C3033)
  1. اكتشاف المشكلة (bad #FF6B5E)
  2. تحديد السبب (warn #F5B942)
  3. الإصلاح (accent #ECEBE6)
  4. النتيجة (ok #5FD38D)
- Footer action buttons: 'عرض الأدلة' (Secondary) and 'تراجع عن الإصلاح' (Ghost)
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QWidget,
)
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from app.ui import tokens
from app.ui.widgets.chip import Chip
from app.ui.widgets.buttons import SecondaryButton, GhostButton


class TimelineStepWidget(QWidget):
    """Single step row showing mono time, bold title, and explanation."""

    def __init__(self, time_str: str, title: str, desc: str, dot_color: str, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(3)

        self.lbl_time = QLabel(time_str)
        self.lbl_time.setFont(tokens.get_mono_font(12, 400))
        self.lbl_time.setStyleSheet(f"color: {tokens.TEXT_MUTED};")

        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(tokens.get_sans_font(15, 600))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT};")

        self.lbl_desc = QLabel(desc)
        self.lbl_desc.setFont(tokens.get_sans_font(13, 400))
        self.lbl_desc.setStyleSheet(f"color: {tokens.TEXT_SECONDARY}; line-height: 1.6;")
        self.lbl_desc.setWordWrap(True)

        layout.addWidget(self.lbl_time)
        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_desc)


class TimelineCanvas(QWidget):
    """Paints the 10px dots and 1px vertical rail for 4 steps."""

    def __init__(self, colors: List[str], step_widgets: List[QWidget], parent=None) -> None:
        super().__init__(parent)
        self.colors = colors
        self.step_widgets = step_widgets
        self.setFixedWidth(20)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if not self.step_widgets:
            return

        centers = []
        for w in self.step_widgets:
            y = w.y() + 8.0  # Align with time label
            centers.append(y)

        # Draw 1px rail from first center to last center
        if len(centers) >= 2:
            painter.setPen(QPen(QColor(tokens.LINE_STRONG), 1.0))
            painter.drawLine(QPointF(10.0, centers[0]), QPointF(10.0, centers[-1]))

        # Draw 10px solid dots
        painter.setPen(Qt.NoPen)
        for i, y in enumerate(centers):
            color = QColor(self.colors[i] if i < len(self.colors) else tokens.ACCENT)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(10.0, y), 5.0, 5.0)


class TimelinePanel(QFrame):
    """Complete 'ما الذي حدث بالضبط؟' panel."""

    view_evidence_requested = Signal()
    rollback_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TimelinePanel")
        self.setStyleSheet(f"""
            QFrame#TimelinePanel {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_PANEL}px;
            }}
            QFrame#TimelinePanel QLabel {{
                border: none;
                background: transparent;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header: Title + Subtitle on Right, Chip on Left
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        self.lbl_title = QLabel("ما الذي حدث بالضبط؟")
        self.lbl_title.setFont(tokens.get_sans_font(18, 600))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT};")

        self.lbl_sub = QLabel("آخر حدث · اليوم 15:32")
        self.lbl_sub.setFont(tokens.get_sans_font(13, 400))
        self.lbl_sub.setStyleSheet(f"color: {tokens.TEXT_MUTED};")

        title_col.addWidget(self.lbl_title)
        title_col.addWidget(self.lbl_sub)
        header_row.addLayout(title_col)

        header_row.addStretch()

        self.status_chip = Chip("تم حله تلقائياً", variant="ok-soft")
        header_row.addWidget(self.status_chip)
        layout.addLayout(header_row)

        # 4 Steps container
        self.steps_container = QWidget()
        steps_layout = QHBoxLayout(self.steps_container)
        steps_layout.setContentsMargins(0, 4, 0, 4)
        steps_layout.setSpacing(12)

        self.content_col = QVBoxLayout()
        self.content_col.setContentsMargins(0, 0, 0, 0)
        self.content_col.setSpacing(10)

        # Default real-data-like steps matching reference
        self.step_data = [
            ("15:32:04", "اكتشاف المشكلة", "ارتفع زمن الاستجابة إلى 182ms بينما المعتاد 22ms، واستمر أكثر من 5 ثوانٍ.", tokens.STATUS_BAD),
            ("15:32:09", "تحديد السبب", "جهازك والراوتر سليمان. تحديث Windows كان يستهلك كامل سرعة الرفع، فتكدست الحزم عند الراوتر.", tokens.STATUS_WARN),
            ("15:32:21", "الإصلاح", "خفضنا أولوية التحديث وحددنا سرعته بـ 40% من الخط. لم ينقطع أي اتصال، واجتماع Teams لم يتأثر.", tokens.ACCENT),
            ("15:32:45", "النتيجة", "عاد زمن الاستجابة إلى 24ms. تم الحل خلال 41 ثانية دون تدخل منك.", tokens.STATUS_OK),
        ]

        self.step_widgets: List[TimelineStepWidget] = []
        for t, title, desc, c in self.step_data:
            w = TimelineStepWidget(t, title, desc, c)
            self.step_widgets.append(w)
            self.content_col.addWidget(w)

        colors = [s[3] for s in self.step_data]
        self.rail_canvas = TimelineCanvas(colors, self.step_widgets)

        steps_layout.addWidget(self.rail_canvas)
        steps_layout.addLayout(self.content_col)
        layout.addWidget(self.steps_container)

        # Footer Buttons
        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 8, 0, 0)
        footer_row.setSpacing(10)

        self.btn_evidence = SecondaryButton("عرض الأدلة")
        self.btn_evidence.clicked.connect(self.view_evidence_requested.emit)

        self.btn_rollback = GhostButton("تراجع عن الإصلاح")
        self.btn_rollback.clicked.connect(self.rollback_requested.emit)

        footer_row.addWidget(self.btn_evidence)
        footer_row.addWidget(self.btn_rollback)
        footer_row.addStretch()

        layout.addLayout(footer_row)

    def set_event(
        self,
        time_str: str,
        steps: List[Tuple[str, str, str]],
        is_resolved: bool = True,
    ) -> None:
        """Update timeline with real audit/remediation event."""
        self.lbl_sub.setText(f"آخر حدث · اليوم {time_str}")
        if is_resolved:
            self.status_chip.set_variant("ok-soft", "تم حله تلقائياً")
            self.btn_rollback.setVisible(True)
        else:
            self.status_chip.set_variant("bad-soft", "يحتاج انتباهك")
            self.btn_rollback.setVisible(False)

        if len(steps) == 4:
            colors = [tokens.STATUS_BAD, tokens.STATUS_WARN, tokens.ACCENT, tokens.STATUS_OK]
            for i, (t, title, desc) in enumerate(steps):
                self.step_widgets[i].lbl_time.setText(t)
                self.step_widgets[i].lbl_title.setText(title)
                self.step_widgets[i].lbl_desc.setText(desc)
            self.rail_canvas.update()
