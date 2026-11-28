"""Interactive Network Topology Map displaying real PC -> Adapter -> Router -> Gateway -> Internet -> Endpoints."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
from app.ui import icons, i18n, tokens


@dataclass
class TopologyNode:
    node_id: str
    title: str
    subtitle: str
    icon_name: str
    status: tokens.SystemStatus
    metric_text: str
    detail_text: str


class _TopologyCanvas(QWidget):
    node_selected = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._nodes: List[TopologyNode] = []
        self._selected_idx: int = 0
        self._node_rects: List[QRectF] = []
        self.setMinimumHeight(148)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_nodes(self, nodes: List[TopologyNode]) -> None:
        self._nodes = list(nodes)
        if self._selected_idx >= len(self._nodes):
            self._selected_idx = 0
        self.update()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            for idx, r in enumerate(self._node_rects):
                if r.contains(pos):
                    self._selected_idx = idx
                    self.node_selected.emit(idx)
                    self.update()
                    break
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        w = float(self.width())
        h = float(self.height())
        self._node_rects = []

        if not self._nodes:
            return

        is_rtl = self.parentWidget() is not None and self.parentWidget().layoutDirection() == Qt.LayoutDirection.RightToLeft
        ordered = list(enumerate(self._nodes))
        if is_rtl:
            ordered = list(reversed(ordered))

        n = len(ordered)
        pad_x = 12.0
        gap = max(16.0, min(40.0, (w - pad_x * 2) * 0.04))
        card_w = max(92.0, (w - pad_x * 2 - gap * (n - 1)) / n)
        card_h = min(124.0, h - 16.0)
        y0 = (h - card_h) / 2.0

        centers: List[QPointF] = []
        rects_by_orig_idx: Dict[int, QRectF] = {}

        for slot_i, (orig_i, node) in enumerate(ordered):
            x0 = pad_x + slot_i * (card_w + gap)
            r = QRectF(x0, y0, card_w, card_h)
            rects_by_orig_idx[orig_i] = r
            centers.append(QPointF(r.center().x(), r.center().y()))

        # Draw real link lines between sequential nodes
        for slot_i in range(len(ordered) - 1):
            p1 = centers[slot_i]
            p2 = centers[slot_i + 1]
            _, n_curr = ordered[slot_i]
            _, n_next = ordered[slot_i + 1]
            bad = tokens.SystemStatus.FAILED in (n_curr.status, n_next.status) or tokens.SystemStatus.NOT_CONNECTED in (n_curr.status, n_next.status)
            unavail = tokens.SystemStatus.UNAVAILABLE in (n_curr.status, n_next.status)
            line_col = tokens.STATUS_BAD if bad else (tokens.LINE_STRONG if unavail else tokens.ACCENT)
            pen_style = Qt.PenStyle.DashLine if unavail else Qt.PenStyle.SolidLine
            painter.setPen(QPen(QColor(line_col), 2.0, pen_style))
            painter.drawLine(QPointF(p1.x() + card_w / 2.0 - 2.0, p1.y()), QPointF(p2.x() - card_w / 2.0 + 2.0, p2.y()))

        # Draw nodes
        for slot_i, (orig_i, node) in enumerate(ordered):
            r = rects_by_orig_idx[orig_i]
            fg, bg, _ = tokens.STATUS_COLOR_MAP.get(node.status.value, (tokens.TEXT_MUTED, tokens.SURFACE_INSET, tokens.LINE))
            selected = orig_i == self._selected_idx
            painter.setPen(QPen(QColor(tokens.ACCENT if selected else tokens.LINE_STRONG), 1.6 if selected else 1.0))
            painter.setBrush(QColor(tokens.SURFACE_SELECTED if selected else tokens.SURFACE_INSET))
            painter.drawRoundedRect(r, 10.0, 10.0)

            # Icon + status dot row
            icons.draw_icon(painter, node.icon_name, QRectF(r.left() + 10.0, r.top() + 10.0, 18.0, 18.0), fg, 1.6)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(fg))
            painter.drawEllipse(QPointF(r.right() - 14.0, r.top() + 19.0), 4.0, 4.0)

            # Title
            painter.setPen(QColor(tokens.TEXT))
            painter.setFont(tokens.get_sans_font(12, 600))
            painter.drawText(QRectF(r.left() + 8.0, r.top() + 34.0, r.width() - 16.0, 20.0), Qt.AlignmentFlag.AlignCenter, node.title)

            # Subtitle
            painter.setPen(QColor(tokens.TEXT_MUTED))
            painter.setFont(tokens.get_sans_font(12, 400))
            painter.drawText(QRectF(r.left() + 6.0, r.top() + 54.0, r.width() - 12.0, 18.0), Qt.AlignmentFlag.AlignCenter, node.subtitle)

            # Metric pill
            painter.setPen(QColor(fg))
            painter.setFont(tokens.get_mono_font(12, 600))
            painter.drawText(QRectF(r.left() + 6.0, r.bottom() - 32.0, r.width() - 12.0, 22.0), Qt.AlignmentFlag.AlignCenter, tokens.bidi_isolate(node.metric_text))

        # Store rects in original index order for click hit-testing
        self._node_rects = [rects_by_orig_idx[i] for i in range(len(self._nodes))]


class NetworkTopologyWidget(QFrame):
    """Interactive topology panel showing real discovered network hops and endpoint telemetry."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("NetworkTopologyWidget")
        self._nodes: List[TopologyNode] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        self.canvas = _TopologyCanvas(self)
        self.canvas.node_selected.connect(self._on_node_selected)
        lay.addWidget(self.canvas)

        self.detail_box = QFrame(self)
        self.detail_box.setStyleSheet(
            f"background-color: {tokens.SURFACE_INSET}; border: 1px solid {tokens.LINE}; border-radius: 8px; padding: 8px 12px;"
        )
        dlay = QHBoxLayout(self.detail_box)
        dlay.setContentsMargins(10, 6, 10, 6)
        self.lbl_detail = QLabel("", self.detail_box)
        self.lbl_detail.setFont(tokens.get_sans_font(12, 400))
        self.lbl_detail.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self.lbl_detail.setWordWrap(True)
        dlay.addWidget(self.lbl_detail)
        lay.addWidget(self.detail_box)

        self.set_topology(
            adapter_name="—",
            adapter_type="—",
            router_label="—",
            gateway_ip="—",
            gateway_ms=None,
            dns_ip="—",
            dns_ms=None,
            internet_ms=None,
            connected_devices_count=None,
            public_ip=None,
        )

    def set_topology(
        self,
        *,
        adapter_name: str,
        adapter_type: str,
        router_label: str,
        gateway_ip: str,
        gateway_ms: Optional[float],
        dns_ip: str,
        dns_ms: Optional[float],
        internet_ms: Optional[float],
        connected_devices_count: Optional[int] = None,
        public_ip: Optional[str] = None,
    ) -> None:
        ar = i18n.get_language() == "ar"
        dev_txt = f" ({connected_devices_count})" if connected_devices_count is not None else ""
        gw_ok = gateway_ms is not None and gateway_ms >= 0
        dns_ok = dns_ms is not None and dns_ms > 0
        inet_ok = internet_ms is not None and internet_ms > 0

        self._nodes = [
            TopologyNode(
                node_id="pc",
                title="الجهاز المحلي" if ar else "Local PC",
                subtitle=adapter_type or ("محول" if ar else "Adapter"),
                icon_name="dashboard",
                status=tokens.SystemStatus.ACTIVE,
                metric_text=adapter_name[:14] if adapter_name and adapter_name != "—" else "Host",
                detail_text=f"المحول النشط: {tokens.bidi_isolate(adapter_name)}" if ar else f"Active adapter: {adapter_name}",
            ),
            TopologyNode(
                node_id="router",
                title=("الراوتر" if ar else "Router") + dev_txt,
                subtitle=router_label[:16] if router_label and router_label != "—" else ("البوابة" if ar else "Gateway"),
                icon_name="router",
                status=tokens.SystemStatus.HEALTHY if gw_ok else (tokens.SystemStatus.WAITING if gateway_ip in ("", "—") else tokens.SystemStatus.WARNING),
                metric_text=f"{gateway_ms:.1f} ms" if gw_ok else (gateway_ip or "—"),
                detail_text=(
                    f"البوابة: {tokens.bidi_isolate(gateway_ip)} | الكمون: {gateway_ms:.1f} ms"
                    if gw_ok else f"البوابة: {tokens.bidi_isolate(gateway_ip)}"
                ) if ar else (
                    f"Gateway {gateway_ip} | RTT {gateway_ms:.1f} ms" if gw_ok else f"Gateway {gateway_ip}"
                ),
            ),
            TopologyNode(
                node_id="dns",
                title="خادم DNS" if ar else "DNS Resolver",
                subtitle=dns_ip or "—",
                icon_name="dns",
                status=tokens.SystemStatus.HEALTHY if dns_ok and dns_ms < 85 else (tokens.SystemStatus.WARNING if dns_ok else tokens.SystemStatus.WAITING),
                metric_text=f"{dns_ms:.0f} ms" if dns_ok else "—",
                detail_text=f"خادم الأسماء النشط: {tokens.bidi_isolate(dns_ip)} ({dns_ms:.1f} ms)" if dns_ok else f"خادم الأسماء: {tokens.bidi_isolate(dns_ip)}",
            ),
            TopologyNode(
                node_id="internet",
                title="الإنترنت" if ar else "Internet",
                subtitle=public_ip or ("مسار WAN" if ar else "WAN Path"),
                icon_name="wifi",
                status=tokens.SystemStatus.HEALTHY if inet_ok and internet_ms < 100 else (tokens.SystemStatus.WARNING if inet_ok else tokens.SystemStatus.NOT_CONNECTED),
                metric_text=f"{internet_ms:.0f} ms" if inet_ok else "—",
                detail_text=(
                    f"الكمون الخارجي: {internet_ms:.1f} ms" + (f" | IP العام: {tokens.bidi_isolate(public_ip)}" if public_ip else "")
                    if inet_ok else ("لم يُقَس المسار الخارجي بعد أو الاتصال منقطع." if ar else "External path not measured or disconnected.")
                ),
            ),
        ]
        self.canvas.set_nodes(self._nodes)
        self._on_node_selected(self.canvas._selected_idx)

    def _on_node_selected(self, idx: int) -> None:
        if 0 <= idx < len(self._nodes):
            self.lbl_detail.setText(tokens.bidi_isolate_mixed(self._nodes[idx].detail_text))
