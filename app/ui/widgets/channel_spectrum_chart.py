"""Custom QPainter RF channel distribution & frequency overlap visualizer adhering to NetGuard tokens."""

from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFontMetricsF, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.ui import tokens
from app.wifi.channel_analysis import occupied_frequency_range
from app.wifi.models import NeighborAccessPoint


class ChannelSpectrumChart(QWidget):
    """Visualizes neighboring AP spectral footprints, bonded widths, and recommended channels."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(275)
        self.setMaximumHeight(330)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._band: str = "2.4 GHz"
        self._access_points: List[NeighborAccessPoint] = []
        self._current_channel: Optional[int] = None
        self._recommended_channel: Optional[int] = None

    def set_data(
        self,
        *,
        band: str,
        access_points: List[NeighborAccessPoint],
        current_channel: Optional[int] = None,
        recommended_channel: Optional[int] = None,
    ) -> None:
        norm_band = "2.4 GHz" if "2.4" in band else ("5 GHz" if "5" in band else ("6 GHz" if "6" in band else band))
        self._band = norm_band
        def _ap_norm(ap_b: str) -> str:
            if "2.4" in ap_b:
                return "2.4 GHz"
            if "5" in ap_b:
                return "5 GHz"
            if "6" in ap_b:
                return "6 GHz"
            return ap_b
        self._access_points = [ap for ap in access_points if _ap_norm(str(ap.band)) == norm_band]
        self._current_channel = current_channel
        self._recommended_channel = recommended_channel
        self.update()

    def _freq_bounds_and_ticks(self) -> tuple[float, float, List[tuple[int, float]]]:
        if self._band == "2.4 GHz":
            ticks = [(ch, 2407.0 + 5.0 * ch) for ch in (1, 3, 6, 9, 11, 13)]
            return 2395.0, 2495.0, ticks
        if self._band == "5 GHz":
            chs = [36, 44, 52, 60, 100, 108, 116, 124, 132, 140, 149, 157, 165]
            ticks = [(ch, 5000.0 + 5.0 * ch) for ch in chs]
            return 5160.0, 5850.0, ticks
        # 6 GHz PSC overview
        chs = [5, 21, 37, 53, 69, 85, 101, 117, 133, 149]
        ticks = [(ch, 5950.0 + 5.0 * ch) for ch in chs]
        return 5945.0, 6750.0, ticks

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QPen(QColor(tokens.LINE), 1.0))
        painter.setBrush(QColor(tokens.SURFACE_INSET))
        painter.drawRoundedRect(rect, 6.0, 6.0)

        pad_left = 52.0
        pad_right = 22.0
        pad_top = 46.0
        pad_bottom = 48.0
        plot = QRectF(
            rect.left() + pad_left,
            rect.top() + pad_top,
            max(40.0, rect.width() - pad_left - pad_right),
            max(40.0, rect.height() - pad_top - pad_bottom),
        )

        f_min, f_max, ticks = self._freq_bounds_and_ticks()
        span_mhz = max(10.0, f_max - f_min)

        def _x_for_mhz(freq_mhz: float) -> float:
            ratio = (freq_mhz - f_min) / span_mhz
            return plot.left() + max(0.0, min(1.0, ratio)) * plot.width()

        def _y_for_rssi(rssi: Optional[int]) -> float:
            val = -90.0 if rssi is None else max(-95.0, min(-30.0, float(rssi)))
            norm = (val + 95.0) / 65.0
            return plot.bottom() - norm * plot.height()

        # Quiet horizontal dBm grid lines
        painter.setFont(tokens.get_mono_font(12))
        grid_pen = QPen(QColor(tokens.LINE), 1.0, Qt.PenStyle.DotLine)
        for dbm_tick in (-85, -70, -55, -40):
            y = _y_for_rssi(dbm_tick)
            painter.setPen(grid_pen)
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            painter.setPen(QColor(tokens.TEXT_MUTED))
            painter.drawText(
                QRectF(rect.left() + 4.0, y - 10.0, pad_left - 10.0, 20.0),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                tokens.bidi_isolate(f"{dbm_tick}"),
            )

        # Baseline + unclipped channel x ticks (26px high, well within 48px pad_bottom)
        painter.setPen(QPen(QColor(tokens.LINE_STRONG), 1.0))
        painter.drawLine(QPointF(plot.left(), plot.bottom()), QPointF(plot.right(), plot.bottom()))

        painter.setFont(tokens.get_mono_font(12))
        for ch, f_mhz in ticks:
            x = _x_for_mhz(f_mhz)
            painter.setPen(QPen(QColor(tokens.LINE_STRONG), 1.0))
            painter.drawLine(QPointF(x, plot.bottom()), QPointF(x, plot.bottom() + 5.0))
            painter.setPen(QColor(tokens.TEXT_MUTED))
            painter.drawText(
                QRectF(x - 20.0, plot.bottom() + 8.0, 40.0, 24.0),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                str(ch),
            )

        placed_top_badges: List[QRectF] = []

        # Current connected channel subtle marker
        if self._current_channel is not None:
            cur_center, _, _ = occupied_frequency_range(self._band, self._current_channel, 20)
            if f_min <= cur_center <= f_max:
                cx_cur = _x_for_mhz(cur_center)
                painter.setPen(QPen(QColor(tokens.ACCENT), 1.2, Qt.PenStyle.DotLine))
                painter.drawLine(QPointF(cx_cur, plot.top()), QPointF(cx_cur, plot.bottom()))

        # Recommended channel marker
        if self._recommended_channel is not None:
            rec_center, _, _ = occupied_frequency_range(self._band, self._recommended_channel, 20)
            if f_min <= rec_center <= f_max:
                rx = _x_for_mhz(rec_center)
                rec_pen = QPen(QColor(tokens.STATUS_OK), 1.6, Qt.PenStyle.DashLine)
                painter.setPen(rec_pen)
                painter.drawLine(QPointF(rx, plot.top()), QPointF(rx, plot.bottom()))
                lbl_text = tokens.bidi_isolate(f"Best Ch {self._recommended_channel}")
                fm = QFontMetricsF(painter.font())
                bw = fm.horizontalAdvance(lbl_text) + 14.0
                bx = max(plot.left() + 4.0, min(plot.right() - bw - 4.0, rx - bw / 2.0))
                badge_rect = QRectF(bx, rect.top() + 5.0, bw, 20.0)
                painter.setPen(QColor(tokens.STATUS_OK))
                painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, lbl_text)
                placed_top_badges.append(badge_rect.adjusted(-4, -2, 4, 2))

        if not self._access_points:
            painter.setFont(tokens.get_sans_font(12))
            painter.setPen(QColor(tokens.TEXT_MUTED))
            painter.drawText(
                plot,
                Qt.AlignmentFlag.AlignCenter,
                "لا توجد نقاط وصول مرصودة في هذا النطاق.",
            )
            return

        # Draw background AP envelopes first, then connected AP last on top
        ordered_aps = sorted(
            self._access_points,
            key=lambda a: (a.is_connected_ap, a.rssi_dbm if a.rssi_dbm is not None else -100),
        )
        envelope_meta: List[Tuple[NeighborAccessPoint, float, float, float]] = []

        for ap in ordered_aps:
            w = ap.channel_width_mhz or 20
            _, f_lo, f_hi = occupied_frequency_range(
                ap.band,
                ap.channel,
                w,
                secondary_offset=ap.secondary_channel_offset,
                center_seg0_channel=ap.center_freq_seg0_channel,
            )
            x1 = _x_for_mhz(f_lo)
            x2 = _x_for_mhz(f_hi)
            width_px = max(10.0, x2 - x1)
            shoulder = min(width_px * 0.22, 12.0)
            y_top = _y_for_rssi(ap.rssi_dbm)
            y_bot = plot.bottom()

            path = QPainterPath()
            path.moveTo(x1, y_bot)
            path.lineTo(x1 + shoulder, y_top)
            path.lineTo(x1 + width_px - shoulder, y_top)
            path.lineTo(x1 + width_px, y_bot)
            path.closeSubpath()

            if ap.is_connected_ap:
                stroke = QColor(tokens.ACCENT)
                fill = QColor(255, 87, 1, 52)
                pen_w = 2.0
            else:
                stroke = QColor(tokens.FOCUS_RING)
                fill = QColor(122, 162, 255, 28)
                pen_w = 1.2

            painter.setPen(QPen(stroke, pen_w))
            painter.setBrush(fill)
            painter.drawPath(path)
            envelope_meta.append((ap, x1, width_px, y_top))

        # Place de-overlapped AP labels prioritized by connected AP then strongest RSSI (max 6 clear labels)
        label_candidates = sorted(
            envelope_meta,
            key=lambda item: (not item[0].is_connected_ap, -(item[0].rssi_dbm if item[0].rssi_dbm is not None else -100)),
        )
        painter.setFont(tokens.get_sans_font(12))
        fm_lbl = QFontMetricsF(painter.font())
        labels_drawn = 0

        for ap, x1, width_px, y_top in label_candidates:
            if labels_drawn >= 6:
                break
            if not (ap.is_connected_ap or (ap.rssi_dbm is not None and ap.rssi_dbm >= -72)):
                continue
            raw_ssid = ap.ssid.strip() if ap.ssid else "Hidden"
            if raw_ssid == "<مخفي>":
                raw_ssid = "Hidden"
            lbl = (raw_ssid[:14] + "..") if len(raw_ssid) > 16 else raw_ssid
            if ap.is_connected_ap:
                lbl = f"[{lbl}] {ap.channel_width_mhz or 20}MHz"

            text_w = fm_lbl.horizontalAdvance(lbl) + 12.0
            text_h = 20.0
            cx = x1 + width_px * 0.5
            bx = max(plot.left() + 2.0, min(plot.right() - text_w - 2.0, cx - text_w * 0.5))

            # Try candidate Y offsets upward & downward to avoid overlapping any previous pill
            placed_rect: Optional[QRectF] = None
            candidate_ys: List[float] = [
                max(rect.top() + 8.0, y_top - 24.0),
                max(rect.top() + 8.0, y_top - 48.0),
                min(plot.bottom() - 26.0, y_top + 6.0),
                min(plot.bottom() - 26.0, y_top + 30.0),
                max(rect.top() + 8.0, y_top - 72.0),
            ]
            # Also try small horizontal nudges if centered collides
            for cand_y in candidate_ys:
                for dx in (0.0, -45.0, 45.0, -90.0, 90.0):
                    test_x = max(plot.left() + 2.0, min(plot.right() - text_w - 2.0, bx + dx))
                    cand_r = QRectF(test_x, cand_y, text_w, text_h)
                    if not any(cand_r.adjusted(-3, -2, 3, 2).intersects(other) for other in placed_top_badges):
                        placed_rect = cand_r
                        break
                if placed_rect is not None:
                    break

            if placed_rect is None:
                continue

            placed_top_badges.append(placed_rect)
            labels_drawn += 1

            # Draw subtle connector line if pill moved away from trapezoid top center
            anchor_y = placed_rect.bottom() if placed_rect.center().y() < y_top else placed_rect.top()
            if abs(placed_rect.center().x() - cx) > 10.0 or abs(anchor_y - y_top) > 14.0:
                painter.setPen(QPen(QColor(tokens.TEXT_MUTED), 1.0, Qt.PenStyle.DotLine))
                painter.drawLine(QPointF(cx, y_top), QPointF(placed_rect.center().x(), anchor_y))

            # Subtle dark pill backdrop for contrast over overlapping trapezoid edges
            painter.setPen(QPen(QColor(tokens.ACCENT if ap.is_connected_ap else tokens.LINE), 1.0))
            painter.setBrush(QColor(15, 23, 42, 220))
            painter.drawRoundedRect(placed_rect, 4.0, 4.0)

            painter.setPen(QColor(tokens.TEXT if ap.is_connected_ap else tokens.TEXT_SECONDARY))
            painter.drawText(placed_rect, Qt.AlignmentFlag.AlignCenter, lbl)
