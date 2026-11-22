"""Generate a professional, modern, expressive cyber-shield logo for NetGuard AI.

Renders a high-resolution, anti-aliased, multi-facet security shield with
neural network telemetry pathways and glowing core, exporting both
assets/icon.png (512x512) and assets/icon.ico (multi-resolution).
"""

import os
import sys
from PySide6.QtGui import (
    QImage,
    QPainter,
    QPainterPath,
    QColor,
    QLinearGradient,
    QRadialGradient,
    QPen,
    QBrush,
    QFont,
)
from PySide6.QtCore import Qt, QPointF, QRectF


def draw_shield_logo(size: int = 512) -> QImage:
    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)

    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)

    scale = size / 512.0

    # Center and bounds
    cx = 256.0 * scale
    cy = 256.0 * scale

    # Outer Shield Path (sleek aerodynamic facets)
    shield_path = QPainterPath()
    shield_path.moveTo(256.0 * scale, 34.0 * scale)
    shield_path.cubicTo(340.0 * scale, 34.0 * scale, 430.0 * scale, 68.0 * scale, 442.0 * scale, 120.0 * scale)
    shield_path.cubicTo(452.0 * scale, 240.0 * scale, 410.0 * scale, 360.0 * scale, 256.0 * scale, 474.0 * scale)
    shield_path.cubicTo(102.0 * scale, 360.0 * scale, 60.0 * scale, 240.0 * scale, 70.0 * scale, 120.0 * scale)
    shield_path.cubicTo(82.0 * scale, 68.0 * scale, 172.0 * scale, 34.0 * scale, 256.0 * scale, 34.0 * scale)
    shield_path.closeSubpath()

    # Outer Ambient Glow
    glow_grad = QRadialGradient(cx, cy, 240.0 * scale)
    glow_grad.setColorAt(0.0, QColor(0, 245, 160, 45))
    glow_grad.setColorAt(0.7, QColor(0, 217, 245, 20))
    glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(glow_grad))
    p.drawEllipse(QRectF(16 * scale, 16 * scale, 480 * scale, 480 * scale))

    # Outer Titanium Bezel
    bezel_grad = QLinearGradient(0, 30 * scale, 512 * scale, 480 * scale)
    bezel_grad.setColorAt(0.0, QColor(36, 44, 54))
    bezel_grad.setColorAt(0.5, QColor(18, 22, 28))
    bezel_grad.setColorAt(1.0, QColor(10, 13, 17))
    p.setBrush(QBrush(bezel_grad))
    p.setPen(QPen(QColor(40, 52, 66), 2 * scale))
    p.drawPath(shield_path)

    # Outer Luminous Rim Stroke
    rim_pen = QPen()
    rim_pen.setWidthF(4.0 * scale)
    rim_grad = QLinearGradient(70 * scale, 34 * scale, 442 * scale, 474 * scale)
    rim_grad.setColorAt(0.0, QColor(0, 245, 160, 240))    # Emerald cyber green
    rim_grad.setColorAt(0.35, QColor(0, 217, 245, 230))   # Electric cyan
    rim_grad.setColorAt(0.75, QColor(122, 162, 255, 220))  # Cobalt blue
    rim_grad.setColorAt(1.0, QColor(255, 107, 0, 240))    # Amber orange
    rim_pen.setBrush(rim_grad)
    p.setPen(rim_pen)
    p.setBrush(Qt.NoBrush)
    p.drawPath(shield_path)

    # Inner Shield Plate (Inset 22px)
    inner_path = QPainterPath()
    inner_path.moveTo(256.0 * scale, 58.0 * scale)
    inner_path.cubicTo(332.0 * scale, 58.0 * scale, 410.0 * scale, 88.0 * scale, 420.0 * scale, 134.0 * scale)
    inner_path.cubicTo(430.0 * scale, 235.0 * scale, 392.0 * scale, 345.0 * scale, 256.0 * scale, 446.0 * scale)
    inner_path.cubicTo(120.0 * scale, 345.0 * scale, 82.0 * scale, 235.0 * scale, 92.0 * scale, 134.0 * scale)
    inner_path.cubicTo(102.0 * scale, 88.0 * scale, 180.0 * scale, 58.0 * scale, 256.0 * scale, 58.0 * scale)
    inner_path.closeSubpath()

    inner_plate_grad = QLinearGradient(0, 60 * scale, 0, 450 * scale)
    inner_plate_grad.setColorAt(0.0, QColor(22, 28, 36))
    inner_plate_grad.setColorAt(0.6, QColor(14, 17, 22))
    inner_plate_grad.setColorAt(1.0, QColor(8, 10, 13))
    p.setPen(QPen(QColor(0, 245, 160, 60), 1.5 * scale))
    p.setBrush(QBrush(inner_plate_grad))
    p.drawPath(inner_path)

    # High-Tech Grid / Circuit Pattern in Inner Plate
    grid_pen = QPen(QColor(0, 217, 245, 25), 1.0 * scale)
    p.setPen(grid_pen)
    for y_offset in range(120, 400, 36):
        p.drawLine(QPointF(120 * scale, y_offset * scale), QPointF(392 * scale, y_offset * scale))
    for x_offset in range(140, 380, 48):
        p.drawLine(QPointF(x_offset * scale, 100 * scale), QPointF(x_offset * scale, 400 * scale))

    # Network Constellation Nodes & Connection Rays
    # Nodes: Top (Primary DNS/Gateway), Center (AI Engine Core), Left (Inbound Traffic), Right (Outbound), Bottom (Endpoint)
    node_top = QPointF(256 * scale, 130 * scale)
    node_center = QPointF(256 * scale, 245 * scale)
    node_left = QPointF(160 * scale, 275 * scale)
    node_right = QPointF(352 * scale, 275 * scale)
    node_bottom = QPointF(256 * scale, 380 * scale)

    # Telemetry connection beams
    beam_pen = QPen()
    beam_pen.setWidthF(3.0 * scale)
    beam_grad = QLinearGradient(node_top.x(), node_top.y(), node_bottom.x(), node_bottom.y())
    beam_grad.setColorAt(0.0, QColor(0, 245, 160, 220))
    beam_grad.setColorAt(0.5, QColor(0, 217, 245, 240))
    beam_grad.setColorAt(1.0, QColor(255, 107, 0, 220))
    beam_pen.setBrush(beam_grad)
    p.setPen(beam_pen)

    # Connecting lines
    p.drawLine(node_top, node_center)
    p.drawLine(node_center, node_left)
    p.drawLine(node_center, node_right)
    p.drawLine(node_left, node_bottom)
    p.drawLine(node_right, node_bottom)
    p.drawLine(node_left, node_right)

    # Inner Glow Behind Center Core
    core_glow = QRadialGradient(node_center.x(), node_center.y(), 65 * scale)
    core_glow.setColorAt(0.0, QColor(0, 245, 160, 180))
    core_glow.setColorAt(0.4, QColor(0, 217, 245, 100))
    core_glow.setColorAt(1.0, QColor(0, 0, 0, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(core_glow))
    p.drawEllipse(QRectF(node_center.x() - 65 * scale, node_center.y() - 65 * scale, 130 * scale, 130 * scale))

    # Center Hexagonal AI Processor Shield
    hex_path = QPainterPath()
    hr = 38.0 * scale
    import math
    for i in range(6):
        angle_deg = 60 * i - 30
        rad = math.radians(angle_deg)
        hx = node_center.x() + hr * math.cos(rad)
        hy = node_center.y() + hr * math.sin(rad)
        if i == 0:
            hex_path.moveTo(hx, hy)
        else:
            hex_path.lineTo(hx, hy)
    hex_path.closeSubpath()

    hex_grad = QLinearGradient(node_center.x() - hr, node_center.y() - hr, node_center.x() + hr, node_center.y() + hr)
    hex_grad.setColorAt(0.0, QColor(20, 28, 38))
    hex_grad.setColorAt(1.0, QColor(10, 15, 22))
    p.setBrush(QBrush(hex_grad))
    p.setPen(QPen(QColor(0, 245, 160, 255), 3.0 * scale))
    p.drawPath(hex_path)

    # Center Emblem: Dynamic Lightning Bolt / Shield Pulse (Speed & Defense)
    bolt_path = QPainterPath()
    bx = node_center.x()
    by = node_center.y()
    bolt_path.moveTo(bx + 4 * scale, by - 24 * scale)
    bolt_path.lineTo(bx - 14 * scale, by - 2 * scale)
    bolt_path.lineTo(bx - 2 * scale, by - 2 * scale)
    bolt_path.lineTo(bx - 6 * scale, by + 24 * scale)
    bolt_path.lineTo(bx + 14 * scale, by + 2 * scale)
    bolt_path.lineTo(bx + 2 * scale, by + 2 * scale)
    bolt_path.closeSubpath()

    bolt_grad = QLinearGradient(bx, by - 24 * scale, bx, by + 24 * scale)
    bolt_grad.setColorAt(0.0, QColor(255, 255, 255))
    bolt_grad.setColorAt(0.4, QColor(0, 245, 160))
    bolt_grad.setColorAt(1.0, QColor(0, 217, 245))
    p.setBrush(QBrush(bolt_grad))
    p.setPen(QPen(QColor(255, 255, 255, 200), 1.0 * scale))
    p.drawPath(bolt_path)

    # Satellite Telemetry Nodes (Spheres with layered highlights)
    def draw_node(pt: QPointF, r: float, primary_col: QColor, accent_col: QColor):
        # Outer ring
        p.setPen(QPen(accent_col, 2.0 * scale))
        p.setBrush(QBrush(QColor(15, 20, 28)))
        p.drawEllipse(QRectF(pt.x() - r * scale, pt.y() - r * scale, 2 * r * scale, 2 * r * scale))

        # Glowing core
        core_r = r * 0.55 * scale
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(primary_col))
        p.drawEllipse(QRectF(pt.x() - core_r, pt.y() - core_r, 2 * core_r, 2 * core_r))

        # Specular glint
        glint_r = core_r * 0.35
        p.setBrush(QBrush(QColor(255, 255, 255, 220)))
        p.drawEllipse(QRectF(pt.x() - core_r * 0.5, pt.y() - core_r * 0.5, glint_r * 2, glint_r * 2))

    draw_node(node_top, 16.0, QColor(0, 245, 160), QColor(0, 245, 160, 200))
    draw_node(node_left, 14.0, QColor(0, 217, 245), QColor(0, 217, 245, 190))
    draw_node(node_right, 14.0, QColor(0, 217, 245), QColor(0, 217, 245, 190))
    draw_node(node_bottom, 15.0, QColor(255, 107, 0), QColor(255, 107, 0, 200))

    p.end()
    return image


def generate_assets():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(root_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    png_path = os.path.join(assets_dir, "icon.png")
    ico_path = os.path.join(assets_dir, "icon.ico")

    # Render master 512x512 PNG
    master_img = draw_shield_logo(512)
    master_img.save(png_path, "PNG")
    print(f"Master PNG saved: {png_path} ({os.path.getsize(png_path)} bytes)")

    # Render 256x256 image for ICO
    ico_img = draw_shield_logo(256)
    ico_img.save(ico_path, "ICO")
    print(f"Windows ICO saved: {ico_path} ({os.path.getsize(ico_path)} bytes)")


if __name__ == "__main__":
    generate_assets()
