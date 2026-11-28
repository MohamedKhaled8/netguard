"""Interactive 14-Stage Diagnostic Investigation Flowchart widget."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFontMetricsF, QPainter, QPen
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget
from app.ui import i18n, tokens

StageState = Literal["completed", "running", "waiting", "failed", "skipped", "awaiting_approval"]

STAGE_PREREQUISITES: Dict[str, tuple[str, ...]] = {
    "network_scan": (),
    "data_collection": ("network_scan",),
    "signal_analysis": ("data_collection",),
    "traffic_analysis": ("data_collection",),
    "latency_analysis": ("data_collection",),
    "dns_analysis": ("data_collection",),
    "router_analysis": ("data_collection",),
    "root_cause": ("signal_analysis", "latency_analysis", "dns_analysis"),
    "recommendation": ("root_cause",),
    "user_approval": ("recommendation",),
    "config_change": ("user_approval",),
    "verification": ("config_change",),
    "before_after": ("verification",),
    "final_report": (
        "network_scan",
        "data_collection",
        "signal_analysis",
        "traffic_analysis",
        "latency_analysis",
        "dns_analysis",
        "router_analysis",
        "root_cause",
        "recommendation",
        "user_approval",
        "config_change",
        "verification",
        "before_after",
    ),
}


@dataclass
class FlowchartStage:
    stage_id: str
    step_num: int
    title_ar: str
    title_en: str
    state: StageState = "waiting"
    evidence_summary: str = ""
    details: str = ""


DEFAULT_FLOWCHART_STAGES: tuple[tuple[str, str, str], ...] = (
    ("network_scan", "\u200F1. مسح الشبكة", "1. Network Scan"),
    ("data_collection", "\u200F2. جمع البيانات", "2. Data Collection"),
    ("signal_analysis", "\u200F3. تحليل الإشارة", "3. Signal Analysis"),
    ("traffic_analysis", "\u200F4. تحليل الحركة", "4. Traffic Analysis"),
    ("latency_analysis", "\u200F5. تحليل الكمون", "5. Latency Analysis"),
    ("dns_analysis", "\u200F6. تحليل DNS", "6. DNS Analysis"),
    ("router_analysis", "\u200F7. تحليل الراوتر", "7. Router Config"),
    ("root_cause", "\u200F8. تحديد السبب", "8. Root Cause"),
    ("recommendation", "\u200F9. التوصيات", "9. Recommendation"),
    ("user_approval", "\u200F10. موافقة المستخدم", "10. User Approval"),
    ("config_change", "\u200F11. تنفيذ التعديل", "11. Config Change"),
    ("verification", "\u200F12. التحقق المرتد", "12. Verification"),
    ("before_after", "\u200F13. مقارنة قبل/بعد", "13. Before / After"),
    ("final_report", "\u200F14. التقرير النهائي", "14. Final Report"),
)


class _FlowchartCanvas(QWidget):
    stage_clicked = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._stages: List[FlowchartStage] = []
        self._rects: List[QRectF] = []
        self._selected: int = 0
        self.setMinimumHeight(250)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_stages(self, stages: List[FlowchartStage]) -> None:
        self._stages = list(stages)
        self.update()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            for idx, r in enumerate(self._rects):
                if r.contains(pos):
                    self._selected = idx
                    self.stage_clicked.emit(idx)
                    self.update()
                    break
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        self._rects = []
        if not self._stages:
            return

        w = float(self.width())
        cols = 5 if w >= 760 else 3
        rows = (len(self._stages) + cols - 1) // cols
        pad_x, pad_y = 10.0, 12.0
        gap_x, gap_y = 18.0, 22.0
        box_w = max(110.0, (w - pad_x * 2 - gap_x * (cols - 1)) / cols)
        box_h = 58.0
        needed_h = int(pad_y * 2 + rows * box_h + max(0, rows - 1) * gap_y)
        if self.minimumHeight() != needed_h:
            self.setMinimumHeight(needed_h)

        is_ar = i18n.get_language() == "ar"
        state_styles: Dict[str, tuple[str, str, str]] = {
            "completed": (tokens.STATUS_OK, tokens.OK_SOFT_BG, "مكتمل" if is_ar else "Completed"),
            "running": (tokens.STATUS_INFO, tokens.INFO_SOFT_BG, "جاري" if is_ar else "Running"),
            "waiting": (tokens.TEXT_MUTED, tokens.SURFACE_INSET, "منتظر" if is_ar else "Waiting"),
            "failed": (tokens.STATUS_BAD, tokens.BAD_SOFT_BG, "فشل" if is_ar else "Failed"),
            "skipped": (tokens.STATUS_WARN, tokens.WARN_SOFT_BG, "تم تخطيه" if is_ar else "Skipped"),
            "awaiting_approval": (tokens.STATUS_WARN, tokens.WARN_SOFT_BG, "بانتظار الموافقة" if is_ar else "Awaiting Approval"),
        }

        coords: List[QRectF] = []
        for idx, _st in enumerate(self._stages):
            r_idx = idx // cols
            c_idx = idx % cols
            if is_ar:
                c_idx = (cols - 1) - c_idx
            x0 = pad_x + c_idx * (box_w + gap_x)
            y0 = pad_y + r_idx * (box_h + gap_y)
            coords.append(QRectF(x0, y0, box_w, box_h))

        # Draw connectors between sequential stages
        for idx in range(len(coords) - 1):
            r1 = coords[idx]
            r2 = coords[idx + 1]
            st_curr = self._stages[idx].state
            col = tokens.STATUS_OK if st_curr == "completed" else tokens.LINE_STRONG
            painter.setPen(QPen(QColor(col), 1.6))
            if (idx // cols) == ((idx + 1) // cols):
                # Same row horizontal connector
                if r1.center().x() < r2.center().x():
                    painter.drawLine(QPointF(r1.right(), r1.center().y()), QPointF(r2.left(), r2.center().y()))
                else:
                    painter.drawLine(QPointF(r1.left(), r1.center().y()), QPointF(r2.right(), r2.center().y()))
            else:
                # Row wrap elbow connector
                mid_y = (r1.bottom() + r2.top()) / 2.0
                painter.drawLine(QPointF(r1.center().x(), r1.bottom()), QPointF(r1.center().x(), mid_y))
                painter.drawLine(QPointF(r1.center().x(), mid_y), QPointF(r2.center().x(), mid_y))
                painter.drawLine(QPointF(r2.center().x(), mid_y), QPointF(r2.center().x(), r2.top()))

        # Draw stage boxes
        for idx, stage in enumerate(self._stages):
            r = coords[idx]
            fg, bg, st_lbl = state_styles.get(stage.state, (tokens.TEXT_MUTED, tokens.SURFACE_INSET, stage.state))
            sel = idx == self._selected
            painter.setPen(QPen(QColor(tokens.ACCENT if sel else fg), 1.8 if sel else 1.1))
            painter.setBrush(QColor(bg))
            painter.drawRoundedRect(r, 8.0, 8.0)

            title = stage.title_ar if is_ar else stage.title_en
            painter.setPen(QColor(tokens.TEXT))
            painter.setFont(tokens.get_sans_font(12, 600))
            fm = QFontMetricsF(painter.font())
            t_rect = QRectF(r.left() + 8.0, r.top() + 7.0, r.width() - 16.0, 20.0)
            painter.drawText(t_rect, Qt.AlignmentFlag.AlignCenter, fm.elidedText(title, Qt.TextElideMode.ElideRight, t_rect.width()))

            painter.setPen(QColor(fg))
            painter.setFont(tokens.get_sans_font(12, 600))
            painter.drawText(QRectF(r.left() + 8.0, r.bottom() - 24.0, r.width() - 16.0, 18.0), Qt.AlignmentFlag.AlignCenter, st_lbl)

        self._rects = coords


class InvestigationFlowchartWidget(QFrame):
    """Complete 14-stage diagnostic investigation flowchart with click-to-inspect evidence panel."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._stages: List[FlowchartStage] = [
            FlowchartStage(sid, idx + 1, ar, en, state="waiting", evidence_summary="", details="")
            for idx, (sid, ar, en) in enumerate(DEFAULT_FLOWCHART_STAGES)
        ]

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        self.canvas = _FlowchartCanvas(self)
        self.canvas.stage_clicked.connect(self._on_stage_selected)
        self.canvas.set_stages(self._stages)
        lay.addWidget(self.canvas)

        self.evidence_box = QFrame(self)
        self.evidence_box.setStyleSheet(
            f"background-color: {tokens.SURFACE_INSET}; border: 1px solid {tokens.LINE}; border-radius: 8px; padding: 10px 12px;"
        )
        elay = QVBoxLayout(self.evidence_box)
        elay.setContentsMargins(10, 8, 10, 8)
        elay.setSpacing(4)
        self.lbl_stage_title = QLabel("", self.evidence_box)
        self.lbl_stage_title.setFont(tokens.get_sans_font(13, 600))
        self.lbl_stage_title.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_stage_evidence = QLabel("", self.evidence_box)
        self.lbl_stage_evidence.setFont(tokens.get_sans_font(12, 400))
        self.lbl_stage_evidence.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self.lbl_stage_evidence.setWordWrap(True)
        elay.addWidget(self.lbl_stage_title)
        elay.addWidget(self.lbl_stage_evidence)
        lay.addWidget(self.evidence_box)

        self._on_stage_selected(0)

    def get_stage_state(self, stage_id: str) -> Optional[StageState]:
        for st in self._stages:
            if st.stage_id == stage_id:
                return st.state
        return None

    def missing_prerequisites(self, stage_id: str) -> List[str]:
        reqs = STAGE_PREREQUISITES.get(stage_id, ())
        by_id = {st.stage_id: st.state for st in self._stages}
        terminal_ok = ("completed", "skipped")
        return [rid for rid in reqs if by_id.get(rid) not in terminal_ok]

    def can_finalize_report(self) -> bool:
        return len(self.missing_prerequisites("final_report")) == 0

    def update_stage(
        self,
        stage_id: str,
        *,
        state: StageState,
        evidence_summary: str = "",
        details: str = "",
    ) -> bool:
        # Enforce strict dependency invariant: Final Report cannot become 'completed' while upstream stages remain unfinished.
        if stage_id == "final_report" and state == "completed":
            missing = self.missing_prerequisites("final_report")
            if missing:
                state = "waiting"
                evidence_summary = f"بانتظار استكمال المراحل: {', '.join(missing[:4])}"
                details = f"Cannot mark Final Report completed; unfinished prerequisites: {', '.join(missing)}"

        for st in self._stages:
            if st.stage_id == stage_id:
                st.state = state
                if evidence_summary:
                    st.evidence_summary = evidence_summary
                if details:
                    st.details = details
                break
        self.canvas.set_stages(self._stages)
        self._on_stage_selected(self.canvas._selected)
        return True if stage_id != "final_report" or state == "completed" else False

    def set_stages(self, stages: List[FlowchartStage]) -> None:
        self._stages = list(stages)
        self.canvas.set_stages(self._stages)
        self._on_stage_selected(self.canvas._selected)

    def _on_stage_selected(self, idx: int) -> None:
        if not (0 <= idx < len(self._stages)):
            return
        st = self._stages[idx]
        is_ar = i18n.get_language() == "ar"
        title = st.title_ar if is_ar else st.title_en
        self.lbl_stage_title.setText(f"{title} — [{st.state.upper()}]")
        if st.details or st.evidence_summary:
            txt = f"{st.evidence_summary}\n{st.details}".strip()
        else:
            txt = (
                "لم تُنفذ هذه المرحلة بعد — اضغط تشغيل الفحص الشامل أو الفحص المختص لتعبئة الأدلة."
                if is_ar
                else "Stage has not been executed yet — run the corresponding diagnostic step to inspect evidence."
            )
        self.lbl_stage_evidence.setText(tokens.bidi_isolate_mixed(txt))
