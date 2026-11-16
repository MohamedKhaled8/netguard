"""Historical Incident & Stability Log View for NetGuard AI.

Follows the reference design system strictly:
- 48-bar daily stability strip with day picker (اليوم / السابق / التالي)
- Full event timeline list with cause, remediation, and duration
100% token-compliant, dark warm-neutral graphite (#0E1012 / #15181A).
"""

from __future__ import annotations
from typing import List, Optional, Any
from datetime import date, datetime, timedelta
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
)
from PySide6.QtCore import Qt
from app.ui import tokens
from app.ui.widgets.buttons import SecondaryButton
from app.ui.widgets.chip import Chip
from app.ui.widgets.base_panel import Panel
from app.ui.widgets.day_strip import DayStrip
from app.core.models.metrics import Diagnosis, DiagnosisSeverity, ProbableCause

CAUSE_TITLES_AR: dict[Any, str] = {
    ProbableCause.HEALTHY: "الاتصال مستقر وسليم",
    ProbableCause.LOCAL_INTERFACE_DOWN: "محول الشبكة متوقف",
    ProbableCause.LOCAL_GATEWAY_UNREACHABLE: "تعذر الوصول إلى الراوتر المنزلي",
    ProbableCause.LOCAL_GATEWAY_HIGH_LATENCY: "ارتفاع زمن استجابة الراوتر المنزلي",
    ProbableCause.WI_FI_SIGNAL_DEGRADED: "ضعف إشارة الشبكة اللاسلكية (Wi-Fi)",
    ProbableCause.CELLULAR_SIGNAL_DEGRADED: "ضعف إشارة اتصال الهاتف المحمول",
    ProbableCause.ISP_UPSTREAM_OUTAGE: "انقطاع الاتصال عند مزود الخدمة (ISP)",
    ProbableCause.ISP_UPSTREAM_HIGH_LATENCY: "ارتفاع زمن استجابة كابينة مزود الخدمة",
    ProbableCause.DNS_RESOLVER_UNRESPONSIVE: "خادم DNS غير مستجيب",
    ProbableCause.DNS_RESOLVER_HIGH_LATENCY: "تباطؤ خادم ترجمة العناوين (DNS)",
    ProbableCause.DESTINATION_SPECIFIC_OUTAGE: "تعذر الوصول إلى وجهة محددة",
    ProbableCause.BUFFERBLOAT_UPLOAD: "تكدس الحزم عند الرفع (Bufferbloat)",
    ProbableCause.BUFFERBLOAT_DOWNLOAD: "تكدس الحزم عند التنزيل (Bufferbloat)",
    ProbableCause.BACKGROUND_APP_SATURATION: "استهلاك مفرط للخط من تطبيق بالخلفية",
    ProbableCause.UNKNOWN_ANOMALY: "رصد تذبذب غير معتاد في معايير الشبكة",
}


class HistoryEventItem(QFrame):
    """Single incident entry in the history log."""

    def __init__(
        self,
        time_str: str,
        title: str,
        cause: str,
        action: str,
        duration_str: str,
        is_resolved: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("HistoryEventItem")
        self.setStyleSheet(f"""
            QFrame#HistoryEventItem {{
                background-color: {tokens.SURFACE_INSET};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_INNER}px;
                padding: 12px 16px;
            }}
            QFrame#HistoryEventItem:hover {{
                background-color: {tokens.SURFACE_HOVER};
            }}
            QFrame#HistoryEventItem QLabel {{
                border: none;
                background: transparent;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # Top row: Time + Title + Chip
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        lbl_time = QLabel(time_str)
        lbl_time.setFont(tokens.get_mono_font(12, 400))
        lbl_time.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        top_row.addWidget(lbl_time)

        lbl_title = QLabel(title)
        lbl_title.setFont(tokens.get_sans_font(15, 600))
        lbl_title.setStyleSheet(f"color: {tokens.TEXT};")
        top_row.addWidget(lbl_title)

        top_row.addStretch()

        lbl_dur = QLabel(f"المدة: {duration_str}")
        lbl_dur.setFont(tokens.get_sans_font(12, 400))
        lbl_dur.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        top_row.addWidget(lbl_dur)

        chip = Chip("تم حله تلقائياً" if is_resolved else "يحتاج انتباهك", variant="ok-soft" if is_resolved else "bad-soft")
        top_row.addWidget(chip)
        layout.addLayout(top_row)

        # Cause line
        lbl_cause = QLabel(f"السبب: {cause}")
        lbl_cause.setFont(tokens.get_sans_font(13, 400))
        lbl_cause.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        lbl_cause.setWordWrap(True)
        layout.addWidget(lbl_cause)

        # Action line
        lbl_action = QLabel(f"الإجراء المتخذ: {action}")
        lbl_action.setFont(tokens.get_sans_font(13, 400))
        lbl_action.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        lbl_action.setWordWrap(True)
        layout.addWidget(lbl_action)


class HistoryView(QWidget):
    """Historical stability and incident log view."""

    def __init__(
        self,
        measurement_repo: Optional[Any] = None,
        incident_repo: Optional[Any] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.measurement_repo = measurement_repo
        self.incident_repo = incident_repo
        self.current_date = date.today()

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(
            tokens.PAGE_PADDING_DESKTOP, 28, tokens.PAGE_PADDING_DESKTOP, 36
        )
        layout.setSpacing(tokens.SECTION_GAP)

        # -------------------------------------------------------------
        # 1. 48-Bar Day Strip with Day Picker
        # -------------------------------------------------------------
        strip_panel = Panel(
            title="سجل استقرار اليوم (كل 30 دقيقة)",
            subtitle="مخطط بياني زمني لحالات التباطؤ أو استقرار الاتصال على مدار 24 ساعة",
            parent=self,
        )

        # Day picker buttons
        picker_row = QHBoxLayout()
        self.btn_prev = SecondaryButton("← اليوم السابق")
        self.lbl_day = QLabel("اليوم")
        self.lbl_day.setFont(tokens.get_sans_font(14, 500))
        self.lbl_day.setStyleSheet(f"color: {tokens.TEXT};")
        self.btn_next = SecondaryButton("اليوم التالي →")
        self.btn_next.setEnabled(False)

        picker_row.addWidget(self.btn_prev)
        picker_row.addStretch()
        picker_row.addWidget(self.lbl_day)
        picker_row.addStretch()
        picker_row.addWidget(self.btn_next)
        strip_panel.main_layout.addLayout(picker_row)

        self.btn_prev.clicked.connect(self._on_prev_day)
        self.btn_next.clicked.connect(self._on_next_day)

        self.day_strip = DayStrip(self)
        strip_panel.main_layout.addWidget(self.day_strip)
        layout.addWidget(strip_panel)

        # -------------------------------------------------------------
        # 2. Event Timeline List
        # -------------------------------------------------------------
        self.events_panel = Panel(
            title="الأحداث المسجلة بالتفصيل",
            subtitle="قائمة زمنية بانقطاعات أو تذبذبات الجودة ونتائج المعالجة",
            parent=self,
        )

        self.events_list_layout = QVBoxLayout()
        self.events_list_layout.setSpacing(12)
        self.events_panel.main_layout.addLayout(self.events_list_layout)
        layout.addWidget(self.events_panel)

        scroll.setWidget(content_widget)
        root_layout.addWidget(scroll)

        self._refresh_day()

    def set_repositories(self, measurement_repo: Any, incident_repo: Any) -> None:
        """Bind storage repositories and reload view for current date."""
        self.measurement_repo = measurement_repo
        self.incident_repo = incident_repo
        self._refresh_day()

    def _on_prev_day(self) -> None:
        self.current_date -= timedelta(days=1)
        self._refresh_day()

    def _on_next_day(self) -> None:
        if self.current_date < date.today():
            self.current_date += timedelta(days=1)
            self._refresh_day()

    def _refresh_day(self) -> None:
        """Update day label, navigation buttons, day strip, and incident list."""
        days_ar = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
        months_ar = [
            "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
            "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
        ]

        d = self.current_date
        today = date.today()
        day_name = days_ar[d.weekday()]
        month_name = months_ar[d.month - 1]

        if d == today:
            self.lbl_day.setText(f"اليوم ({day_name} {d.day} {month_name})")
        elif d == today - timedelta(days=1):
            self.lbl_day.setText(f"أمس ({day_name} {d.day} {month_name})")
        else:
            self.lbl_day.setText(f"{day_name} {d.day} {month_name} {d.year}")

        self.btn_next.setEnabled(d < today)

        # Refresh Day Strip
        if self.measurement_repo:
            slots = self.measurement_repo.get_day_slots(self.current_date)
            self.day_strip.set_data(slots)

        # Refresh Incidents
        if self.incident_repo:
            incidents = self.incident_repo.get_by_date(self.current_date)
            self.update_incidents(incidents)
        else:
            self.update_incidents([])

    def update_incidents(self, incidents: List[Any]) -> None:
        """Update incident list from real incident data."""
        while self.events_list_layout.count():
            item = self.events_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not incidents:
            empty_card = QFrame()
            empty_card.setObjectName("EmptyIncidentCard")
            empty_card.setStyleSheet(f"""
                QFrame#EmptyIncidentCard {{
                    background-color: {tokens.SURFACE_INSET};
                    border: 1px dashed {tokens.LINE_STRONG};
                    border-radius: {tokens.RADIUS_INNER}px;
                    padding: 24px;
                }}
            """)
            empty_col = QVBoxLayout(empty_card)
            empty_col.setAlignment(Qt.AlignCenter)
            lbl = QLabel("لا توجد أحداث أو انقطاعات مسجلة لهذا اليوم — كان الاتصال مستقراً")
            lbl.setFont(tokens.get_sans_font(13, 400))
            lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
            lbl.setAlignment(Qt.AlignCenter)
            empty_col.addWidget(lbl)
            self.events_list_layout.addWidget(empty_card)
            return

        for inc in incidents[:30]:
            if hasattr(inc, "timestamp"):
                ts = inc.timestamp
                time_str = ts.astimezone().strftime("%H:%M") if ts.tzinfo else ts.strftime("%H:%M")
            else:
                time_str = "—"

            cause_enum = getattr(inc, "probable_cause", None)
            title = CAUSE_TITLES_AR.get(cause_enum, "رصد عطل في الشبكة")
            cause_str = getattr(inc, "explanation", "") or "تذبذب عابر في معايير الشبكة"
            actions = getattr(inc, "recommended_actions", [])
            if actions:
                action_str = " · ".join(actions)
            elif getattr(inc, "auto_remediation_permitted", False):
                action_str = "تم تفعيل المعالجة التلقائية وحماية الاتصال"
            else:
                action_str = "مراقبة مستمرة لتذبذب الجودة"

            sev = getattr(inc, "severity", None)
            is_resolved = (sev != DiagnosisSeverity.CRITICAL) if sev else True

            item = HistoryEventItem(
                time_str,
                title,
                cause_str,
                action_str,
                "لحظي",
                is_resolved=is_resolved,
            )
            self.events_list_layout.addWidget(item)
