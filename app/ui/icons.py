"""Unified crisp vector line icon renderer for NetGuard AI.

Provides consistent 18px / 1.6px-stroke geometric vector icons via QPainter
without emoji, raster screenshots, or decorative AI symbols.
"""

from __future__ import annotations
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


def draw_icon(
    painter: QPainter,
    name: str,
    rect: QRectF,
    color: str | QColor,
    stroke_width: float = 1.6,
) -> None:
    """Draw a clean vector line icon centered inside `rect`."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    col = QColor(color) if isinstance(color, str) else color
    pen = QPen(col, stroke_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    cx = rect.center().x()
    cy = rect.center().y()
    s = min(rect.width(), rect.height())
    r = s * 0.42
    x0, y0 = cx - r, cy - r
    x1, y1 = cx + r, cy + r

    if name in ("dashboard", "home"):
        # 2x2 crisp dashboard grid
        gap = s * 0.09
        bw = (r * 2.0 - gap) / 2.0
        painter.drawRoundedRect(QRectF(x0, y0, bw, bw), 1.8, 1.8)
        painter.drawRoundedRect(QRectF(x0 + bw + gap, y0, bw, bw), 1.8, 1.8)
        painter.drawRoundedRect(QRectF(x0, y0 + bw + gap, bw, bw), 1.8, 1.8)
        painter.drawRoundedRect(QRectF(x0 + bw + gap, y0 + bw + gap, bw, bw), 1.8, 1.8)

    elif name in ("meeting", "meeting_guard", "shield"):
        p = QPainterPath()
        p.moveTo(cx, y0)
        p.lineTo(x1, y0 + r * 0.42)
        p.lineTo(x1, cy + r * 0.15)
        p.quadTo(x1, y1 - r * 0.2, cx, y1)
        p.quadTo(x0, y1 - r * 0.2, x0, cy + r * 0.15)
        p.lineTo(x0, y0 + r * 0.42)
        p.closeSubpath()
        painter.drawPath(p)
        painter.drawLine(QPointF(cx - r * 0.28, cy + r * 0.02), QPointF(cx - r * 0.05, cy + r * 0.25))
        painter.drawLine(QPointF(cx - r * 0.05, cy + r * 0.25), QPointF(cx + r * 0.34, cy - r * 0.18))

    elif name in ("traffic", "activity"):
        p = QPainterPath()
        p.moveTo(x0, cy)
        p.lineTo(cx - r * 0.45, cy)
        p.lineTo(cx - r * 0.18, y0 + r * 0.2)
        p.lineTo(cx + r * 0.18, y1 - r * 0.2)
        p.lineTo(cx + r * 0.45, cy)
        p.lineTo(x1, cy)
        painter.drawPath(p)

    elif name in ("dns", "globe"):
        painter.drawEllipse(QRectF(x0, y0, r * 2, r * 2))
        painter.drawEllipse(QRectF(cx - r * 0.45, y0, r * 0.9, r * 2))
        painter.drawLine(QPointF(x0 + 1.0, cy), QPointF(x1 - 1.0, cy))

    elif name == "wifi":
        for frac in (0.95, 0.62):
            arc_r = r * frac
            arc_rect = QRectF(cx - arc_r, cy + r * 0.45 - arc_r * 1.15, arc_r * 2, arc_r * 2)
            painter.drawArc(arc_rect, 45 * 16, 90 * 16)
        painter.setBrush(col)
        painter.drawEllipse(QPointF(cx, cy + r * 0.55), 1.4, 1.4)

    elif name == "router":
        # Chassis + twin antennas + status LEDs
        body = QRectF(x0, cy + r * 0.05, r * 2, r * 0.72)
        painter.drawRoundedRect(body, 2.2, 2.2)
        painter.drawLine(QPointF(cx - r * 0.48, body.top()), QPointF(cx - r * 0.48, y0 + r * 0.1))
        painter.drawLine(QPointF(cx + r * 0.48, body.top()), QPointF(cx + r * 0.48, y0 + r * 0.1))
        painter.drawPoint(QPointF(cx - r * 0.35, body.center().y()))
        painter.drawPoint(QPointF(cx, body.center().y()))
        painter.drawPoint(QPointF(cx + r * 0.35, body.center().y()))

    elif name in ("quality", "internet_quality", "gauge"):
        arc_rect = QRectF(x0, y0 + r * 0.15, r * 2, r * 2)
        painter.drawArc(arc_rect, 20 * 16, 140 * 16)
        painter.drawLine(QPointF(cx, cy + r * 0.35), QPointF(cx + r * 0.52, cy - r * 0.25))
        painter.setBrush(col)
        painter.drawEllipse(QPointF(cx, cy + r * 0.35), 1.5, 1.5)

    elif name in ("reports", "clock", "file-text"):
        painter.drawRoundedRect(QRectF(x0 + r * 0.15, y0, r * 1.7, r * 2.0), 2.0, 2.0)
        painter.drawLine(QPointF(cx - r * 0.38, cy - r * 0.35), QPointF(cx + r * 0.38, cy - r * 0.35))
        painter.drawLine(QPointF(cx - r * 0.38, cy + r * 0.02), QPointF(cx + r * 0.38, cy + r * 0.02))
        painter.drawLine(QPointF(cx - r * 0.38, cy + r * 0.38), QPointF(cx + r * 0.15, cy + r * 0.38))

    elif name in ("settings", "sliders"):
        for idx, y_off in enumerate((-0.48, 0.0, 0.48)):
            yy = cy + r * y_off
            painter.drawLine(QPointF(x0, yy), QPointF(x1, yy))
            kx = cx + (r * 0.35 if idx % 2 == 0 else -r * 0.35)
            painter.setBrush(col)
            painter.drawEllipse(QPointF(kx, yy), 2.0, 2.0)
            painter.setBrush(Qt.BrushStyle.NoBrush)

    elif name == "about":
        painter.drawEllipse(QRectF(x0, y0, r * 2, r * 2))
        painter.drawLine(QPointF(cx, cy - r * 0.1), QPointF(cx, cy + r * 0.48))
        painter.setBrush(col)
        painter.drawEllipse(QPointF(cx, cy - r * 0.45), 1.1, 1.1)

    elif name == "refresh":
        painter.drawArc(QRectF(x0, y0, r * 2, r * 2), 35 * 16, 285 * 16)
        painter.drawLine(QPointF(x1 - r * 0.35, y0 + r * 0.25), QPointF(x1, y0 + r * 0.35))
        painter.drawLine(QPointF(x1, y0 + r * 0.35), QPointF(x1 - r * 0.08, y0 - r * 0.02))

    elif name == "download":
        painter.drawLine(QPointF(cx, y0), QPointF(cx, cy + r * 0.38))
        painter.drawLine(QPointF(cx - r * 0.35, cy + r * 0.05), QPointF(cx, cy + r * 0.4))
        painter.drawLine(QPointF(cx + r * 0.35, cy + r * 0.05), QPointF(cx, cy + r * 0.4))
        painter.drawLine(QPointF(x0 + r * 0.1, y1 - r * 0.15), QPointF(x1 - r * 0.1, y1 - r * 0.15))

    elif name == "upload":
        painter.drawLine(QPointF(cx, y1 - r * 0.25), QPointF(cx, y0 + r * 0.05))
        painter.drawLine(QPointF(cx - r * 0.35, y0 + r * 0.4), QPointF(cx, y0 + r * 0.05))
        painter.drawLine(QPointF(cx + r * 0.35, y0 + r * 0.4), QPointF(cx, y0 + r * 0.05))
        painter.drawLine(QPointF(x0 + r * 0.1, y1 - r * 0.05), QPointF(x1 - r * 0.1, y1 - r * 0.05))

    elif name == "search":
        painter.drawEllipse(QRectF(x0, y0, r * 1.45, r * 1.45))
        painter.drawLine(QPointF(cx + r * 0.25, cy + r * 0.25), QPointF(x1, y1))

    elif name == "alert":
        p = QPainterPath()
        p.moveTo(cx, y0)
        p.lineTo(x1, y1)
        p.lineTo(x0, y1)
        p.closeSubpath()
        painter.drawPath(p)
        painter.drawLine(QPointF(cx, cy - r * 0.2), QPointF(cx, cy + r * 0.28))
        painter.drawPoint(QPointF(cx, y1 - r * 0.25))

    elif name == "lock":
        painter.drawRoundedRect(QRectF(x0 + r * 0.15, cy - r * 0.05, r * 1.7, r * 1.05), 2.0, 2.0)
        painter.drawArc(QRectF(cx - r * 0.45, y0, r * 0.9, r * 1.1), 0, 180 * 16)

    else:
        painter.drawEllipse(QRectF(x0, y0, r * 2, r * 2))

    painter.restore()


def create_icon(name: str, color: str, size: int = 18) -> QIcon:
    """Create a QIcon rendered cleanly at high DPI."""
    pm = QPixmap(size * 2, size * 2)
    pm.setDevicePixelRatio(2.0)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    draw_icon(p, name, QRectF(0, 0, size, size), color)
    p.end()
    return QIcon(pm)
