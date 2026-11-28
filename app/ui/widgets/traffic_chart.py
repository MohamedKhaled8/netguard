"""Real-time dual-series Download (cyan) and Upload (purple) network traffic chart."""

from __future__ import annotations
from typing import List, Optional
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
from app.ui import i18n, tokens


class DualTrafficCanvas(QWidget):
    """QPainter canvas drawing smooth download & upload Mbps series with zero invented data."""

    def __init__(
        self,
        *,
        show_download: bool = True,
        show_upload: bool = True,
        min_height: int = 160,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._show_dl = show_download
        self._show_ul = show_upload
        self._dl_samples: List[float] = []
        self._ul_samples: List[float] = []
        self._timestamps: List[str] = []
        self.setMinimumHeight(min_height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_series(
        self,
        download_mbps: List[float],
        upload_mbps: List[float],
        timestamps: Optional[List[str]] = None,
    ) -> None:
        self._dl_samples = [max(0.0, float(v)) for v in (download_mbps or [])][-120:]
        self._ul_samples = [max(0.0, float(v)) for v in (upload_mbps or [])][-120:]
        self._timestamps = list(timestamps or [])[-120:]
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QPen(QColor(tokens.LINE), 1.0))
        painter.setBrush(QColor(tokens.SURFACE_INSET))
        painter.drawRoundedRect(rect, 8.0, 8.0)

        has_data = (self._show_dl and len(self._dl_samples) >= 2) or (self._show_ul and len(self._ul_samples) >= 2)
        if not has_data:
            painter.setPen(QColor(tokens.TEXT_MUTED))
            painter.setFont(tokens.get_sans_font(12, 400))
            msg = "في انتظار عينات حركة البيانات الفعلية..." if i18n.get_language() == "ar" else "Waiting for real interface throughput samples..."
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, msg)
            return

        pad_l, pad_r, pad_t, pad_b = 54.0, 16.0, 16.0, 26.0
        plot = QRectF(
            rect.left() + pad_l,
            rect.top() + pad_t,
            max(40.0, rect.width() - pad_l - pad_r),
            max(40.0, rect.height() - pad_t - pad_b),
        )

        combined: List[float] = []
        if self._show_dl:
            combined.extend(self._dl_samples)
        if self._show_ul:
            combined.extend(self._ul_samples)
        peak = max(combined, default=1.0)
        y_max = max(1.0, peak * 1.18)

        # Horizontal grid & Y labels
        painter.setFont(tokens.get_mono_font(12, 400))
        for step in range(4):
            frac = step / 3.0
            y = plot.bottom() - frac * plot.height()
            painter.setPen(QPen(QColor(tokens.LINE), 1.0, Qt.PenStyle.DotLine))
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            val = y_max * frac
            lbl = f"{val:.1f}" if y_max < 10 else f"{int(round(val))}"
            painter.setPen(QColor(tokens.TEXT_MUTED))
            painter.drawText(
                QRectF(rect.left() + 4.0, y - 8.0, pad_l - 10.0, 16.0),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                lbl,
            )

        def _draw_series(values: List[float], color_hex: str) -> None:
            if len(values) < 2:
                return
            n = len(values)
            pts = []
            for idx, v in enumerate(values):
                x = plot.left() + (idx / max(1, n - 1)) * plot.width()
                y = plot.bottom() - min(1.0, max(0.0, v / y_max)) * plot.height()
                pts.append(QPointF(x, y))

            line_path = QPainterPath(pts[0])
            for pt in pts[1:]:
                line_path.lineTo(pt)

            fill_path = QPainterPath(line_path)
            fill_path.lineTo(QPointF(pts[-1].x(), plot.bottom()))
            fill_path.lineTo(QPointF(pts[0].x(), plot.bottom()))
            fill_path.closeSubpath()

            col = QColor(color_hex)
            grad = QLinearGradient(plot.topLeft(), plot.bottomLeft())
            c_top = QColor(col)
            c_top.setAlpha(60)
            c_bot = QColor(col)
            c_bot.setAlpha(4)
            grad.setColorAt(0.0, c_top)
            grad.setColorAt(1.0, c_bot)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(grad)
            painter.drawPath(fill_path)

            painter.setPen(QPen(col, 2.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(line_path)

        if self._show_dl:
            _draw_series(self._dl_samples, tokens.CYAN)
        if self._show_ul:
            _draw_series(self._ul_samples, tokens.PURPLE)

        # X-axis timestamps (first, middle, last)
        if self._timestamps:
            painter.setPen(QColor(tokens.TEXT_MUTED))
            painter.setFont(tokens.get_mono_font(12, 400))
            indices = sorted({0, len(self._timestamps) // 2, len(self._timestamps) - 1})
            for idx in indices:
                x = plot.left() + (idx / max(1, len(self._timestamps) - 1)) * plot.width()
                painter.drawText(
                    QRectF(x - 28.0, plot.bottom() + 4.0, 56.0, 16.0),
                    Qt.AlignmentFlag.AlignCenter,
                    self._timestamps[idx],
                )


class TrafficThroughputChart(QFrame):
    """Panel-ready real-time throughput chart with Download (cyan) and Upload (purple) stats."""

    def __init__(
        self,
        title: str = "",
        *,
        show_download: bool = True,
        show_upload: bool = True,
        min_height: int = 160,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        from PySide6.QtWidgets import QSizePolicy
        self._show_dl = show_download
        self._show_ul = show_upload
        self.setObjectName("TrafficChartCard")
        self.setStyleSheet(
            f"""
            QFrame#TrafficChartCard {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_PANEL}px;
            }}
            """
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        hdr = QVBoxLayout()
        hdr.setSpacing(4)
        self.lbl_title = QLabel(title, self)
        self.lbl_title.setFont(tokens.get_sans_font(14, 600))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT}; border: none; background: transparent;")
        self.lbl_title.setWordWrap(True)
        hdr.addWidget(self.lbl_title)

        self.lbl_stats = QLabel("—", self)
        self.lbl_stats.setFont(tokens.get_mono_font(12, 600))
        self.lbl_stats.setStyleSheet(f"color: {tokens.TEXT_SECONDARY}; border: none; background: transparent;")
        hdr.addWidget(self.lbl_stats)
        lay.addLayout(hdr)

        self.canvas = DualTrafficCanvas(
            show_download=show_download,
            show_upload=show_upload,
            min_height=min_height,
            parent=self,
        )
        lay.addWidget(self.canvas)

    def set_series(
        self,
        download_mbps: List[float],
        upload_mbps: List[float],
        timestamps: Optional[List[str]] = None,
    ) -> None:
        self.canvas.set_series(download_mbps, upload_mbps, timestamps)
        parts = []
        if self._show_dl and download_mbps:
            dl_now = download_mbps[-1]
            dl_peak = max(download_mbps)
            parts.append(f"DL {dl_now:.2f} (Peak {dl_peak:.2f})")
        if self._show_ul and upload_mbps:
            ul_now = upload_mbps[-1]
            ul_peak = max(upload_mbps)
            parts.append(f"UL {ul_now:.2f} (Peak {ul_peak:.2f})")
        self.lbl_stats.setText(tokens.bidi_isolate(" | ".join(parts) + " Mbps") if parts else "—")
