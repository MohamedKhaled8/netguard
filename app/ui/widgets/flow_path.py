"""Interactive 5-node Network Flow Path Widget for NetGuard AI.

Panel 'مسار اتصالك':
- 5 Nodes (جهازك, الراوتر, مزود الخدمة, خادم DNS, الإنترنت)
- 4 Connectors with two 6px traveling dots (2.4s linear loop, RTL flow)
- Inset detail box below showing name, description, and 3 stats (الآن, المعتاد, الحالة)
- Full-width container with responsive layout
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QWidget,
    QScrollArea,
)
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal
from app.ui import tokens


class PathNodeButton(QFrame):
    """Single node box (148px wide, 14px padding, 12px radius)."""

    clicked = Signal(int)

    def __init__(
        self,
        index: int,
        index_str: str,
        name: str,
        latency_ms: float,
        status: str = "ok",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PathNodeButton")
        self.index = index
        self.name = name
        self.latency_ms = latency_ms
        self.status = status
        self.is_selected = False

        self.setFixedWidth(148)
        self.setFixedHeight(94)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        # Top row: Mono index "01".."05" + 8px status dot
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        self.lbl_idx = QLabel(index_str)
        self.lbl_idx.setFont(tokens.get_mono_font(11, 400))
        self.lbl_idx.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        top_row.addWidget(self.lbl_idx)

        top_row.addStretch()

        self.dot_widget = QLabel()
        self.dot_widget.setFixedSize(8, 8)
        top_row.addWidget(self.dot_widget)
        layout.addLayout(top_row)

        # Name label (15px bold)
        self.lbl_name = QLabel(name)
        self.lbl_name.setFont(tokens.get_sans_font(15, 600))
        self.lbl_name.setStyleSheet(f"color: {tokens.TEXT};")
        layout.addWidget(self.lbl_name)

        # Latency row (LTR mono 20px + 12px ms)
        lat_container = QWidget(self)
        lat_container.setLayoutDirection(Qt.LeftToRight)
        lat_row = QHBoxLayout(lat_container)
        lat_row.setContentsMargins(0, 0, 0, 0)
        lat_row.setSpacing(4)

        self.lbl_val = QLabel("—")
        self.lbl_val.setFont(tokens.get_mono_font(20, 500))
        self.lbl_val.setStyleSheet(f"color: {tokens.TEXT};")

        self.lbl_unit = QLabel("ms")
        self.lbl_unit.setFont(tokens.get_sans_font(12, 400))
        self.lbl_unit.setStyleSheet(f"color: {tokens.TEXT_MUTED};")

        lat_row.addWidget(self.lbl_val)
        lat_row.addWidget(self.lbl_unit)
        lat_row.addStretch()
        layout.addWidget(lat_container)

        self.update_state(latency_ms, status, self.is_selected)

    def set_selected(self, selected: bool) -> None:
        self.is_selected = selected
        self.update_state(self.latency_ms, self.status, selected)

    def update_state(self, latency_ms: Optional[float], status: str, selected: bool) -> None:
        self.latency_ms = latency_ms
        self.status = status
        self.is_selected = selected
        if latency_ms is not None and latency_ms >= 0:
            self.lbl_val.setText(f"{int(round(latency_ms))}")
            self.lbl_unit.setText("ms")
        else:
            self.lbl_val.setText("—")
            self.lbl_unit.setText("")

        if status == "ok":
            dot_col = tokens.STATUS_OK
        elif status == "warn":
            dot_col = tokens.STATUS_WARN
        elif status in ("bad", "error"):
            dot_col = tokens.STATUS_BAD
        else:
            dot_col = tokens.TEXT_MUTED
        self.dot_widget.setStyleSheet(f"background-color: {dot_col}; border-radius: 4px;")

        if selected:
            self.setStyleSheet(f"""
                QFrame#PathNodeButton {{
                    background-color: {tokens.SURFACE_HOVER};
                    border: 1px solid {tokens.ACCENT};
                    border-radius: {tokens.RADIUS_INNER}px;
                }}
                QFrame#PathNodeButton QLabel {{
                    border: none;
                    background: transparent;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#PathNodeButton {{
                    background-color: {tokens.SURFACE_INSET};
                    border: 1px solid {tokens.LINE};
                    border-radius: {tokens.RADIUS_INNER}px;
                }}
                QFrame#PathNodeButton:hover {{
                    background-color: {tokens.SURFACE_HOVER};
                }}
                QFrame#PathNodeButton QLabel {{
                    border: none;
                    background: transparent;
                }}
            """)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.index)
        super().mousePressEvent(event)


class PathConnector(QWidget):
    """Connector line between two nodes with 2 traveling dots."""

    def __init__(self, dest_status: str = "ok", parent=None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(40)
        self.setFixedHeight(94)
        self.dest_status = dest_status
        self._phase = 0.0  # 0.0 to 1.0

    def set_phase(self, phase: float) -> None:
        self._phase = phase
        self.update()

    def set_dest_status(self, status: str) -> None:
        self.dest_status = status
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = float(self.width())
        mid_y = float(self.height()) / 2.0

        # Base 2px line #2A2E31
        painter.setPen(QPen(QColor(tokens.BAR_FUTURE), 2.0))
        painter.drawLine(QPointF(0.0, mid_y), QPointF(w, mid_y))

        # Two 6px traveling dots moving right-to-left (RTL data flow)
        if self.dest_status == "ok":
            dot_color = QColor(tokens.STATUS_OK)
        elif self.dest_status == "warn":
            dot_color = QColor(tokens.STATUS_WARN)
        elif self.dest_status in ("bad", "error"):
            dot_color = QColor(tokens.STATUS_BAD)
        else:
            dot_color = QColor(tokens.TEXT_MUTED)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(dot_color))

        # Dot 1: phase (from w to 0)
        x1 = w * (1.0 - self._phase)
        painter.drawEllipse(QPointF(x1, mid_y), 3.0, 3.0)

        # Dot 2: half cycle behind
        phase2 = (self._phase + 0.5) % 1.0
        x2 = w * (1.0 - phase2)
        painter.drawEllipse(QPointF(x2, mid_y), 3.0, 3.0)


class FlowPathPanel(QFrame):
    """Complete 'مسار اتصالك' panel with animated flow & details box."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("FlowPathPanel")
        self.setStyleSheet(f"""
            QFrame#FlowPathPanel {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_PANEL}px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header: Title & Subtitle
        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        self.lbl_title = QLabel("مسار اتصالك")
        self.lbl_title.setFont(tokens.get_sans_font(18, 600))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT};")

        self.lbl_sub = QLabel("رحلة بياناتك من جهازك إلى الإنترنت. اضغط على أي نقطة لتفاصيلها.")
        self.lbl_sub.setFont(tokens.get_sans_font(13, 400))
        self.lbl_sub.setStyleSheet(f"color: {tokens.TEXT_MUTED};")

        title_col.addWidget(self.lbl_title)
        title_col.addWidget(self.lbl_sub)
        layout.addLayout(title_col)

        # Horizontally scrollable path container (min-width 760px)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFixedHeight(106)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.path_container = QWidget()
        self.path_container.setMinimumWidth(760)
        path_layout = QHBoxLayout(self.path_container)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(0)

        # 5 Nodes in RTL: 01 جهازك -> 02 الراوتر -> 03 مزود الخدمة -> 04 خادم DNS -> 05 الإنترنت
        self.node_info = [
            {
                "idx": "01",
                "name": "جهازك",
                "latency": None,
                "status": "none",
                "desc": "فحص بطاقة الشبكة وزمن الاستجابة الداخلي للجهاز.",
                "typical": "—",
            },
            {
                "idx": "02",
                "name": "الراوتر",
                "latency": None,
                "status": "none",
                "desc": "الاتصال بالراوتر المنزلي والبوابة الافتراضية.",
                "typical": "—",
            },
            {
                "idx": "03",
                "name": "مزود الخدمة",
                "latency": None,
                "status": "none",
                "desc": "مسار التوصيل بالبنية التحتية لمزود الخدمة (ISP).",
                "typical": "—",
            },
            {
                "idx": "04",
                "name": "خادم DNS",
                "latency": None,
                "status": "none",
                "desc": "خادم تحليل أسماء النطاقات (DNS).",
                "typical": "—",
            },
            {
                "idx": "05",
                "name": "الإنترنت",
                "latency": None,
                "status": "none",
                "desc": "الوصول إلى الخوادم السحابية العالمية.",
                "typical": "—",
            },
        ]

        self.nodes: List[PathNodeButton] = []
        self.connectors: List[PathConnector] = []

        # Build in RTL order: 01 جهازك first (right side), then connector, etc.
        for i, info in enumerate(self.node_info):
            btn = PathNodeButton(i, info["idx"], info["name"], info["latency"], info["status"])
            btn.clicked.connect(self._select_node)
            path_layout.addWidget(btn)
            self.nodes.append(btn)

            if i < len(self.node_info) - 1:
                dest_st = self.node_info[i + 1]["status"]
                conn = PathConnector(dest_status=dest_st)
                path_layout.addWidget(conn, stretch=1)
                self.connectors.append(conn)

        self.scroll.setWidget(self.path_container)
        layout.addWidget(self.scroll)

        # Inset Detail Box (bg #101315, 1px line, radius 12, padding 18x20)
        self.detail_box = QFrame()
        self.detail_box.setObjectName("PathDetailBox")
        self.detail_box.setStyleSheet(f"""
            QFrame#PathDetailBox {{
                background-color: {tokens.SURFACE_INSET};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_INNER}px;
            }}
            QFrame#PathDetailBox QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        detail_layout = QHBoxLayout(self.detail_box)
        detail_layout.setContentsMargins(20, 16, 20, 16)
        detail_layout.setSpacing(24)

        # Right side (RTL start): Name (15px bold) + Description (13px secondary)
        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        self.lbl_detail_name = QLabel("جهازك")
        self.lbl_detail_name.setFont(tokens.get_sans_font(15, 600))
        self.lbl_detail_name.setStyleSheet(f"color: {tokens.TEXT};")

        self.lbl_detail_desc = QLabel("فحص بطاقة الشبكة وزمن الاستجابة الداخلي للجهاز.")
        self.lbl_detail_desc.setFont(tokens.get_sans_font(13, 400))
        self.lbl_detail_desc.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self.lbl_detail_desc.setWordWrap(True)

        info_col.addWidget(self.lbl_detail_name)
        info_col.addWidget(self.lbl_detail_desc)
        detail_layout.addLayout(info_col, stretch=1)

        # Left side (RTL end): 3 stats (الآن, المعتاد, الحالة)
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(24)

        def make_metric_col(title_txt: str) -> Tuple[QWidget, QLabel]:
            w = QWidget()
            col = QVBoxLayout(w)
            col.setContentsMargins(0, 0, 0, 0)
            col.setSpacing(2)
            lbl = QLabel(title_txt)
            lbl.setFont(tokens.get_sans_font(12, 400))
            lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
            val = QLabel("—")
            val.setFont(tokens.get_mono_font(16, 500))
            col.addWidget(lbl)
            col.addWidget(val)
            return w, val

        col_now, self.lbl_now = make_metric_col("الآن")
        col_typ, self.lbl_typ = make_metric_col("المعتاد")
        col_st, self.lbl_st = make_metric_col("الحالة")
        self.lbl_st.setFont(tokens.get_sans_font(13, 500))

        stats_layout.addWidget(col_now)
        stats_layout.addWidget(col_typ)
        stats_layout.addWidget(col_st)
        detail_layout.addLayout(stats_layout)

        layout.addWidget(self.detail_box)

        # Default selection: start with node 0 (جهازك)
        self._select_node(0)

        # Animation timer for connector travelling dots (2.4s linear loop)
        self._flow_phase = 0.0
        if tokens.ANIMATIONS_ENABLED:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._on_flow_tick)
            self._timer.start(33)  # ~30fps

    def _on_flow_tick(self) -> None:
        self._flow_phase = (self._flow_phase + (33.0 / 2400.0)) % 1.0
        for conn in self.connectors:
            conn.set_phase(self._flow_phase)

    def _select_node(self, index: int) -> None:
        for i, n in enumerate(self.nodes):
            n.set_selected(i == index)

        info = self.node_info[index]
        self.lbl_detail_name.setText(info["name"])
        self.lbl_detail_desc.setText(info["desc"])
        if info["latency"] is not None and info["latency"] >= 0:
            self.lbl_now.setText(f"{int(round(info['latency']))} ms")
        else:
            self.lbl_now.setText("—")
        self.lbl_now.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_typ.setText(info.get("typical", "—"))
        self.lbl_typ.setStyleSheet(f"color: {tokens.TEXT_MUTED};")

        st = info.get("status", "none")
        if st == "ok":
            self.lbl_st.setText("سليم")
            self.lbl_st.setStyleSheet(f"color: {tokens.STATUS_OK};")
        elif st == "warn":
            self.lbl_st.setText("يحتاج تحسين")
            self.lbl_st.setStyleSheet(f"color: {tokens.STATUS_WARN};")
        elif st in ("bad", "error"):
            self.lbl_st.setText("خلل / غير متصل")
            self.lbl_st.setStyleSheet(f"color: {tokens.STATUS_BAD};")
        else:
            self.lbl_st.setText("غير متوفر")
            self.lbl_st.setStyleSheet(f"color: {tokens.TEXT_MUTED};")

    def update_node_latency(
        self,
        index: int,
        latency_ms: Optional[float],
        status: Optional[str] = None,
        desc: Optional[str] = None,
    ) -> None:
        if 0 <= index < len(self.node_info):
            self.node_info[index]["latency"] = latency_ms
            if status is not None:
                self.node_info[index]["status"] = status
            if desc is not None:
                self.node_info[index]["desc"] = desc
            if status == "ok" and latency_ms is not None and latency_ms >= 0:
                self.node_info[index]["typical"] = f"{int(round(latency_ms))} ms"
            self.nodes[index].update_state(latency_ms, self.node_info[index]["status"], self.nodes[index].is_selected)
            if index > 0 and (index - 1) < len(self.connectors):
                self.connectors[index - 1].dest_status = self.node_info[index]["status"]
                self.connectors[index - 1].update()
            if self.nodes[index].is_selected:
                self._select_node(index)

    def update_dns_node(self, latency_ms: Optional[float], is_optimal: bool = True, dns_name: str = "Cloudflare") -> None:
        """Dynamically update Node 04 (خادم DNS) based on live benchmark and resolution."""
        if latency_ms is None or latency_ms < 0:
            status = "none"
            desc = "خادم DNS غير متوفر أو تعذر قياس زمن استجابته."
            typical = "—"
        else:
            status = "ok" if is_optimal else "warn"
            desc = (
                f"خادم DNS النشط ({dns_name}) يستجيب بسرعة {latency_ms:.0f} ms. استعلامات المواقع تتم فوراً ودون تأخير."
                if is_optimal
                else f"خادم DNS الحالي أبطأ من المعدل المعتاد ({latency_ms:.0f} ms). قد تتأخر المواقع 1-2 ثانية قبل التحميل."
            )
            typical = f"{int(round(latency_ms))} ms" if is_optimal else "12 ms"
        if len(self.node_info) > 3:
            self.node_info[3]["latency"] = latency_ms
            self.node_info[3]["status"] = status
            self.node_info[3]["desc"] = desc
            self.node_info[3]["typical"] = typical
            self.nodes[3].update_state(latency_ms, status, self.nodes[3].is_selected)
            if len(self.connectors) > 2:
                self.connectors[2].dest_status = status
                self.connectors[2].update()
            if self.nodes[3].is_selected:
                self._select_node(3)
