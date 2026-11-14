"""Custom High-Craft Health Radar & Autonomous Gauge Widget.

Follows unslop and ui-ux-pro-max standards:
- Bespoke central hero visual using hardware-accelerated QPainter.
- Concentrates visual richness into a single polished element.
- Displays live health score, pulsating status beacon, and autonomous telemetry summary.
"""

from __future__ import annotations
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QBrush
from PySide6.QtCore import Qt, QRectF


class HealthRadarWidget(QWidget):
    """Bespoke circular connection health radar and autonomous status gauge."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(220, 220)
        self.setMaximumHeight(250)

        self.health_score: int = 99
        self.status_title: str = "الشبكة محمية ومستقرة"
        self.status_subtitle: str = "المراقبة التنبؤية نشطة · الإصلاح الذاتي التلقائي مفعل"
        self.color_hex: str = "#2ea043"  # Emerald Green

    def set_health(self, score: int, title: str, subtitle: str, color_hex: str = "#2ea043") -> None:
        self.health_score = max(0, min(100, score))
        self.status_title = title
        self.status_subtitle = subtitle
        self.color_hex = color_hex
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        width = self.width()
        height = self.height()
        center_x = width / 2.0
        center_y = height / 2.0 - 15.0
        radius = min(width, height) / 2.0 - 32.0

        rect = QRectF(center_x - radius, center_y - radius, radius * 2.0, radius * 2.0)

        # 1. Subtle Background Track
        track_pen = QPen(QColor("#162033"), 8.0, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(rect, 0, 360 * 16)

        # 2. Active Health Arc
        accent_color = QColor(self.color_hex)
        arc_pen = QPen(accent_color, 8.0, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(arc_pen)
        
        # 360 degrees * 16 (Qt angle units)
        span_angle = int((self.health_score / 100.0) * 360.0 * 16.0)
        start_angle = 90 * 16  # start from top
        painter.drawArc(rect, start_angle, -span_angle)

        # 3. Inner Center Text: Health Score
        painter.setPen(QColor("#ffffff"))
        score_font = QFont("Segoe UI", 32, QFont.Bold)
        painter.setFont(score_font)
        score_text = f"{self.health_score}%"
        painter.drawText(
            QRectF(center_x - radius, center_y - 28, radius * 2.0, 42),
            Qt.AlignCenter,
            score_text,
        )

        # Label under score
        painter.setPen(QColor("#8b949e"))
        lbl_font = QFont("Segoe UI", 11, QFont.DemiBold)
        painter.setFont(lbl_font)
        painter.drawText(
            QRectF(center_x - radius, center_y + 14, radius * 2.0, 20),
            Qt.AlignCenter,
            "مستوى استقرار الاتصال",
        )

        # 4. Status Title & Subtitle Below the Gauge
        title_font = QFont("Segoe UI", 13, QFont.Bold)
        painter.setFont(title_font)
        painter.setPen(accent_color)
        painter.drawText(
            QRectF(10, center_y + radius + 10, width - 20, 24),
            Qt.AlignCenter,
            self.status_title,
        )

        sub_font = QFont("Segoe UI", 11, QFont.Normal)
        painter.setFont(sub_font)
        painter.setPen(QColor("#7d8590"))
        painter.drawText(
            QRectF(10, center_y + radius + 32, width - 20, 20),
            Qt.AlignCenter,
            self.status_subtitle,
        )
