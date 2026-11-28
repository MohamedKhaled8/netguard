"""Custom QPainter circular and semicircular gauges for documented network metrics."""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFontMetricsF, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget
from app.ui import tokens


class CircularGauge(QWidget):
    """Precision circular ring gauge for documented 0-100 scores or unavailable state."""

    def __init__(
        self,
        title: str = "",
        unit: str = "%",
        parent: Optional[QWidget] = None,
        size: int = 128,
        semicircular: bool = False,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._unit = unit
        self._value: Optional[float] = None
        self._max_value: float = 100.0
        self._display_text: Optional[str] = None
        self._subtitle: str = ""
        self._accent_color: str = tokens.STATUS_OK
        self._semicircular = semicircular
        self.setMinimumSize(size, int(size * 0.78) if semicircular else size)
        self.setMaximumSize(size + 36, int((size + 36) * 0.85) if semicircular else size + 36)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def set_value(
        self,
        value: Optional[float],
        *,
        max_value: float = 100.0,
        display_text: Optional[str] = None,
        subtitle: str = "",
        color: Optional[str] = None,
    ) -> None:
        self._value = value
        self._max_value = max(1.0, float(max_value))
        self._display_text = display_text
        self._subtitle = subtitle
        if color:
            self._accent_color = color
        elif value is None:
            self._accent_color = tokens.TEXT_MUTED
        else:
            ratio = value / self._max_value
            if ratio >= 0.75:
                self._accent_color = tokens.STATUS_OK
            elif ratio >= 0.45:
                self._accent_color = tokens.STATUS_WARN
            else:
                self._accent_color = tokens.STATUS_BAD
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        stroke = 8.0

        if self._semicircular:
            diam = min(w - stroke * 2, (h - stroke * 2) * 1.8)
            arc_rect = QRectF((w - diam) / 2.0, stroke + 4.0, diam, diam)
            start_deg = 180
            span_deg = -180
        else:
            diam = min(w, h) - stroke * 2 - 4.0
            arc_rect = QRectF((w - diam) / 2.0, (h - diam) / 2.0, diam, diam)
            start_deg = 225
            span_deg = -270

        # Track arc
        track_pen = QPen(QColor(tokens.BAR_FUTURE), stroke, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(arc_rect, start_deg * 16, span_deg * 16)

        # Active arc (only when measured value exists)
        if self._value is not None:
            frac = max(0.0, min(1.0, float(self._value) / self._max_value))
            val_pen = QPen(QColor(self._accent_color), stroke, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(val_pen)
            painter.drawArc(arc_rect, start_deg * 16, int(span_deg * frac * 16))

        # Center value text
        if self._display_text is not None:
            val_str = self._display_text
        elif self._value is None:
            val_str = "—"
        else:
            num = int(round(self._value)) if float(self._value).is_integer() or self._unit == "%" else f"{self._value:.1f}"
            val_str = f"{num}{self._unit}" if self._unit == "%" else f"{num}"

        painter.setPen(QColor(tokens.TEXT if self._value is not None else tokens.TEXT_MUTED))
        painter.setFont(tokens.get_mono_font(20 if not self._semicircular else 18, 600))
        cy_off = 12.0 if self._semicircular else -6.0
        val_rect = QRectF(arc_rect.left() + 8.0, arc_rect.center().y() + cy_off - 16.0, arc_rect.width() - 16.0, 28.0)
        painter.drawText(val_rect, Qt.AlignmentFlag.AlignCenter, tokens.bidi_isolate(val_str))

        # Subtitle / label below value
        sub_txt = self._subtitle or self._title
        if sub_txt:
            painter.setPen(QColor(tokens.TEXT_SECONDARY))
            painter.setFont(tokens.get_sans_font(12, 500))
            sub_rect = QRectF(4.0, val_rect.bottom() + 2.0, w - 8.0, 20.0)
            fm = QFontMetricsF(painter.font())
            elided = fm.elidedText(sub_txt, Qt.TextElideMode.ElideRight, sub_rect.width())
            painter.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, elided)
