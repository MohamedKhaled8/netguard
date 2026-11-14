"""Bespoke Master Connection Shield Widget.

Inspired by Cloudflare WARP, Linear, and modern Dribbble desktop clients:
- Tactile central shield with subtle radial aura.
- Live status state (Protected Emerald / Caution Amber / Incident Coral).
- Breathing glow ring with hardware-accelerated QPainter antialiasing.
"""

from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QFont
from PySide6.QtCore import Qt, QRectF


class MasterShieldWidget(QFrame):
    """Bespoke central connection shield displaying live protection state."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #0c101a;
                border: 1px solid #161f30;
                border-radius: 14px;
            }
        """)
        self.setMinimumHeight(210)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(24)

        # 1. Left: Glowing Canvas Orb
        self.orb_canvas = _ShieldCanvas(self)
        self.orb_canvas.setFixedSize(160, 160)
        main_layout.addWidget(self.orb_canvas)

        # 2. Right: Information & Autonomous Status
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)

        self.status_badge = QLabel("● الحماية الذاتية التلقائية: نشطة ومفعلة")
        self.status_badge.setStyleSheet("""
            font-size: 11px;
            font-weight: 700;
            color: #00e599;
            background-color: #0d221a;
            border: 1px solid #14402e;
            border-radius: 8px;
            padding: 4px 10px;
            max-width: 250px;
        """)
        info_layout.addWidget(self.status_badge)

        self.title_lbl = QLabel("اتصالك بالإنترنت محمي ومستقر تماماً")
        self.title_lbl.setStyleSheet("font-size: 20px; font-weight: 800; color: #ffffff; letter-spacing: -0.3px;")
        info_layout.addWidget(self.title_lbl)

        self.desc_lbl = QLabel(
            "يعمل NetGuard AI في الخلفية بمراقبة حزم البيانات والراوتر وخوادم DNS ذاتياً، "
            "ويتدخل فوراً لمعالجة أي بطء أو تذبذب بدون الحاجة لأي مجهود يدوي منك."
        )
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setStyleSheet("font-size: 12px; color: #8b949e; line-height: 1.5;")
        info_layout.addWidget(self.desc_lbl)

        # Live telemetry pill strip
        pill_row = QHBoxLayout()
        pill_row.setSpacing(10)

        self.pill_gw = self._create_pill("الراوتر", "1.2 ms", "#00e599")
        self.pill_ping = self._create_pill("البنج", "24.0 ms", "#00d2ff")
        self.pill_dns = self._create_pill("الـ DNS", "Cloudflare", "#58a6ff")
        self.pill_loss = self._create_pill("فقد الحزم", "0.0%", "#00e599")

        pill_row.addWidget(self.pill_gw)
        pill_row.addWidget(self.pill_ping)
        pill_row.addWidget(self.pill_dns)
        pill_row.addWidget(self.pill_loss)
        pill_row.addStretch()

        info_layout.addLayout(pill_row)
        main_layout.addLayout(info_layout, stretch=1)

    def _create_pill(self, label: str, val: str, color_hex: str) -> QFrame:
        p = QFrame()
        p.setStyleSheet("""
            QFrame {
                background-color: #121826;
                border: 1px solid #1c263c;
                border-radius: 6px;
                padding: 4px 8px;
            }
        """)
        pl = QHBoxLayout(p)
        pl.setContentsMargins(6, 3, 6, 3)
        pl.setSpacing(6)

        t = QLabel(label + ":")
        t.setStyleSheet("font-size: 11px; color: #7d8590; font-weight: 600;")
        v = QLabel(val)
        v.setObjectName("Val")
        v.setStyleSheet(f"font-size: 11px; color: {color_hex}; font-weight: 700;")

        pl.addWidget(t)
        pl.addWidget(v)
        return p

    def update_shield(self, is_healthy: bool, title: str, desc: str, gw_val: str, ping_val: str, dns_val: str) -> None:
        color = "#00e599" if is_healthy else "#e3b341"
        self.orb_canvas.set_color(color)
        self.title_lbl.setText(title)
        self.desc_lbl.setText(desc)

        if is_healthy:
            self.status_badge.setText("● الحماية الذاتية التلقائية: نشطة ومفعلة")
            self.status_badge.setStyleSheet("""
                font-size: 11px; font-weight: 700; color: #00e599;
                background-color: #0d221a; border: 1px solid #14402e;
                border-radius: 8px; padding: 4px 10px; max-width: 250px;
            """)
        else:
            self.status_badge.setText("● جاري التدخل الذاتي لمعالجة العطل")
            self.status_badge.setStyleSheet("""
                font-size: 11px; font-weight: 700; color: #e3b341;
                background-color: #241d0e; border: 1px solid #4a3a18;
                border-radius: 8px; padding: 4px 10px; max-width: 250px;
            """)

        # Update Pills
        v_gw = self.pill_gw.findChild(QLabel, "Val")
        if v_gw: v_gw.setText(gw_val)

        v_ping = self.pill_ping.findChild(QLabel, "Val")
        if v_ping: v_ping.setText(ping_val)

        v_dns = self.pill_dns.findChild(QLabel, "Val")
        if v_dns: v_dns.setText(dns_val)


class _ShieldCanvas(QWidget):
    """Custom painted glowing shield with radial aura."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.color_hex = "#00e599"

    def set_color(self, hex_val: str) -> None:
        self.color_hex = hex_val
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        cx = w / 2.0
        cy = h / 2.0

        accent = QColor(self.color_hex)

        # 1. Outer Soft Radial Glow
        glow = QRadialGradient(cx, cy, 70.0)
        glow.setColorAt(0.0, QColor(accent.red(), accent.green(), accent.blue(), 45))
        glow.setColorAt(1.0, QColor(accent.red(), accent.green(), accent.blue(), 0))
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(cx - 70, cy - 70, 140, 140))

        # 2. Outer Ring
        ring_pen = QPen(QColor(accent.red(), accent.green(), accent.blue(), 80), 2.0)
        painter.setPen(ring_pen)
        painter.setBrush(QColor("#0f1624"))
        painter.drawEllipse(QRectF(cx - 50, cy - 50, 100, 100))

        # 3. Inner Center Disc
        painter.setPen(QPen(accent, 2.5))
        painter.setBrush(QColor(accent.red(), accent.green(), accent.blue(), 25))
        painter.drawEllipse(QRectF(cx - 36, cy - 36, 72, 72))

        # 4. Shield / Check Icon in center
        painter.setPen(QColor("#ffffff"))
        f = QFont("Segoe UI", 20, QFont.Bold)
        painter.setFont(f)
        painter.drawText(QRectF(cx - 36, cy - 36, 72, 72), Qt.AlignCenter, "✓")
