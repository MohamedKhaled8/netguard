"""Network Information Strip widget for NetGuard AI.

Restores core network environment identity:
- Network Name (SSID)
- Internet Service Provider (ISP)
- Local IPv4 Address
- Public IPv4 Address
Styled with hairline borders, graphite dark surfaces, and responsive reflow.
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QWidget,
    QGridLayout,
)
from PySide6.QtCore import Qt
from app.ui import tokens


class NetworkInfoCell(QFrame):
    """Single cell inside the NetworkInfoStrip."""

    def __init__(
        self,
        title: str,
        initial_val: str = "—",
        initial_sub: str = "جاري الكشف...",
        is_mono: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.is_mono = is_mono
        self.setObjectName("NetworkInfoCell")
        self.setStyleSheet(f"""
            QFrame#NetworkInfoCell {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_INNER}px;
            }}
            QFrame#NetworkInfoCell QLabel {{
                border: 0px solid transparent;
                background: transparent;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        # Title (12px muted)
        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(tokens.get_sans_font(12, 500))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_title.setWordWrap(True)
        layout.addWidget(self.lbl_title)

        # Value
        self.lbl_val = QLabel(initial_val)
        if is_mono:
            self.lbl_val.setFont(tokens.get_mono_font(15, 600))
        else:
            self.lbl_val.setFont(tokens.get_sans_font(15, 600))
        self.lbl_val.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_val.setWordWrap(True)
        self.lbl_val.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.lbl_val)

        # Subtitle / Details (12px secondary)
        self.lbl_sub = QLabel(initial_sub)
        self.lbl_sub.setFont(tokens.get_sans_font(12, 400))
        self.lbl_sub.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self.lbl_sub.setWordWrap(True)
        layout.addWidget(self.lbl_sub)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setMinimumHeight(96)

    def set_data(self, val: str, sub: str = "", status_color: Optional[str] = None) -> None:
        self.lbl_val.setText(val or "—")
        if sub:
            self.lbl_sub.setText(sub)
        if status_color:
            self.lbl_val.setStyleSheet(f"color: {status_color};")
        else:
            self.lbl_val.setStyleSheet(f"color: {tokens.TEXT};")
        self.updateGeometry()
        if self.parentWidget() is not None:
            self.parentWidget().updateGeometry()


class NetworkInfoStrip(QFrame):
    """Container holding 4 hairline-separated network identity tiles."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("NetworkInfoStrip")
        self.setStyleSheet(f"""
            QFrame#NetworkInfoStrip {{
                background-color: transparent;
                border: 0px solid transparent;
            }}
        """)

        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)

        # 4 Cells
        self.cell_ssid = NetworkInfoCell("اسم الشبكة", "—", "جاري فحص الشبكة...")
        self.cell_isp = NetworkInfoCell("مزود الإنترنت", "—", "جاري فحص المزود...")
        self.cell_local_ip = NetworkInfoCell("عنوان IP الداخلي", "—", "محلي على الشبكة", is_mono=True)
        self.cell_public_ip = NetworkInfoCell("عنوان IP الخارجي", "—", "الظاهر على الإنترنت", is_mono=True)

        self._apply_layout(mode="desktop")

    def _apply_layout(self, mode: str = "desktop") -> None:
        # Clear layout items
        for i in reversed(range(self.grid.count())):
            item = self.grid.itemAt(i)
            if item and item.widget():
                self.grid.removeWidget(item.widget())

        if mode == "desktop":
            # 1 row x 4 cols
            self.grid.addWidget(self.cell_ssid, 0, 0)
            self.grid.addWidget(self.cell_isp, 0, 1)
            self.grid.addWidget(self.cell_local_ip, 0, 2)
            self.grid.addWidget(self.cell_public_ip, 0, 3)
            for c in range(4):
                self.grid.setColumnStretch(c, 1)
        elif mode == "tablet":
            # 2 rows x 2 cols
            self.grid.addWidget(self.cell_ssid, 0, 0)
            self.grid.addWidget(self.cell_isp, 0, 1)
            self.grid.addWidget(self.cell_local_ip, 1, 0)
            self.grid.addWidget(self.cell_public_ip, 1, 1)
            self.grid.setColumnStretch(0, 1)
            self.grid.setColumnStretch(1, 1)
        else:
            # 4 rows x 1 col
            self.grid.addWidget(self.cell_ssid, 0, 0)
            self.grid.addWidget(self.cell_isp, 1, 0)
            self.grid.addWidget(self.cell_local_ip, 2, 0)
            self.grid.addWidget(self.cell_public_ip, 3, 0)
            self.grid.setColumnStretch(0, 1)

    def update_info(self, info: Dict[str, Any]) -> None:
        """Update network identity information from live system probe output."""
        if not info:
            return

        # 1. SSID / Connection Name
        ssid = info.get("ssid") or "غير متصل"
        is_wifi = info.get("is_wifi", True)
        signal = info.get("signal", "—")
        band = info.get("band", "—")
        wifi_data = info.get("wifi")
        wifi_dict = wifi_data if isinstance(wifi_data, dict) else {}
        adapter = wifi_dict.get("adapter", "")

        if is_wifi and ssid not in ("غير متصل", "—"):
            sig_str = f"إشارة {signal}" if signal != "—" else ""
            band_str = f"نطاق {band}" if band != "—" else ""
            details = " · ".join(filter(None, [sig_str, band_str])) or "اتصال لاسلكي"
            self.cell_ssid.set_data(ssid, details, status_color=tokens.STATUS_OK)
        elif not is_wifi:
            self.cell_ssid.set_data(ssid, adapter or "محول الشبكة السلكي", status_color=tokens.TEXT)
        else:
            self.cell_ssid.set_data("غير متصل", "محول الشبكة معطل أو غير متصل", status_color=tokens.STATUS_BAD)

        # 2. ISP Provider
        isp_data = info.get("isp")
        isp_dict = isp_data if isinstance(isp_data, dict) else {}
        if isinstance(isp_data, str) and isp_data:
            isp_name = isp_data
        else:
            isp_name = info.get("isp_company") or isp_dict.get("company") or "غير متوفر"

        city = isp_dict.get("city") or ""
        if isp_name and "غير متصل" not in isp_name and "غير متوفر" not in isp_name:
            sub = f"مزود الخدمة الفعلي · {city}" if city and city != "—" else "مزود الخدمة الفعلي المعتمد"
            self.cell_isp.set_data(isp_name, sub, status_color=tokens.TEXT)
        else:
            self.cell_isp.set_data("غير متوفر", "تعذر الاتصال بمزود الخدمة (غير متصل)", status_color=tokens.STATUS_BAD)

        # 3. Local IP
        local_ip = info.get("local_ip") or "—"
        if local_ip != "—" and not local_ip.startswith("127."):
            gw = info.get("gateway") or "—"
            self.cell_local_ip.set_data(local_ip, f"بوابة الراوتر: {gw}", status_color=tokens.TEXT)
        else:
            self.cell_local_ip.set_data("—", "غير معين (لا يوجد عنوان محلي)", status_color=tokens.TEXT_MUTED)

        # 4. Public IP
        public_ip = info.get("public_ip") or isp_dict.get("ip") or "—"
        if public_ip != "—":
            self.cell_public_ip.set_data(public_ip, "عنوانك الفعلي على الإنترنت", status_color=tokens.TEXT)
        else:
            self.cell_public_ip.set_data("—", "غير متصل بالإنترنت الخارجي", status_color=tokens.TEXT_MUTED)

    def set_responsive_mode(self, mode: str) -> None:
        self._apply_layout(mode)
