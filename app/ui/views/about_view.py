"""About & System Architecture view for NetGuard AI."""

from __future__ import annotations
from typing import Any, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from app.ui import i18n, tokens
from app.ui.widgets.base_panel import Panel
from app.ui.widgets.status_badge import StatusBadge
from app.version import __version__ as APP_VERSION


class AboutView(QWidget):
    """Clean workstation About page detailing version, active capabilities, and privacy guarantees."""

    def __init__(self, app_core: Any = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.app_core = app_core
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(tokens.PAGE_PADDING_DESKTOP, 24, tokens.PAGE_PADDING_DESKTOP, 32)
        lay.setSpacing(tokens.SECTION_GAP)

        # Header Panel
        hdr_panel = Panel(
            title=f"NetGuard AI  v{APP_VERSION}",
            subtitle=i18n.tr("about_sub"),
            parent=self,
        )
        grid = QGridLayout()
        grid.setSpacing(12)

        facts = [
            ("الإصدار / Version", tokens.bidi_isolate(APP_VERSION)),
            ("بيئة التشغيل / Runtime", tokens.bidi_isolate("Python 3.12 · PySide6")),
            ("محرك المراقبة", "Windows ETW + psutil + Native Wifi wlanapi + ActiveStore QoS"),
            ("تخزين الاعتماد", "الذاكرة المؤقتة للجلسة أو Windows Credential Manager (محلي فقط)"),
        ]
        for idx, (k, v) in enumerate(facts):
            box = QFrame(self)
            box.setStyleSheet(
                f"background-color: {tokens.SURFACE_INSET}; border: 1px solid {tokens.LINE}; border-radius: 8px;"
            )
            bl = QVBoxLayout(box)
            bl.setContentsMargins(14, 10, 14, 10)
            bl.setSpacing(4)
            kl = QLabel(k, box)
            kl.setFont(tokens.get_sans_font(12, 600))
            kl.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
            vl = QLabel(tokens.bidi_isolate_mixed(v), box)
            vl.setFont(tokens.get_mono_font(13, 500))
            vl.setStyleSheet(f"color: {tokens.TEXT};")
            vl.setWordWrap(True)
            bl.addWidget(kl)
            bl.addWidget(vl)
            grid.addWidget(box, idx // 2, idx % 2)
        hdr_panel.main_layout.addLayout(grid)
        lay.addWidget(hdr_panel)

        # Security & Truthfulness Guarantees
        sec_panel = Panel(
            title="الضمانات الهندسية والأمنية",
            subtitle="التزام صارم بالقياس الحقيقي وعدم إرسال أي بيانات أو أسرار خارج الشبكة المحلية",
            parent=self,
        )
        guarantees = [
            "جميع قياسات الكمون والواي فاي والراوتر وحركة البيانات حقيقية ومأخوذة مباشرة من واجهات نظام التشغيل أو الراوتر المحلي.",
            "لا يتم تخمين كلمات مرور الراوتر أو تجاوز المصادقة أو تخطي التشفير؛ كل محاولة دخول واحدة لحماية الراوتر من القفل.",
            "تُحجب كلمات المرور ومفاتيح Wi-Fi ورموز الجلسات تلقائياً من جميع التقارير المصدّرة وسجلات التشخيص.",
            "لا تُغيّر إعدادات DNS أو تُجرى اختبارات السرعة الكثيفة أثناء المكالمات النشطة حمايةً لاستقرار الاجتماعات.",
        ]
        for g in guarantees:
            row = QLabel(f"•  {g}", self)
            row.setFont(tokens.get_sans_font(13, 400))
            row.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
            row.setWordWrap(True)
            sec_panel.main_layout.addWidget(row)
        lay.addWidget(sec_panel)

        # Runtime Status Panel
        rt_panel = Panel(title="حالة الوحدات الفرعية الحالية", parent=self)
        self.lbl_runtime_info = QLabel("جاهز.", self)
        self.lbl_runtime_info.setFont(tokens.get_sans_font(13, 400))
        self.lbl_runtime_info.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self.lbl_runtime_info.setWordWrap(True)
        rt_panel.main_layout.addWidget(self.lbl_runtime_info)
        self.badge_elevated = StatusBadge(tokens.SystemStatus.WAITING, "جاري فحص الصلاحيات", self)
        rt_panel.main_layout.addWidget(self.badge_elevated)
        lay.addWidget(rt_panel)

        lay.addStretch(1)
        scroll.setWidget(container)
        root.addWidget(scroll)
        self.refresh_runtime_status()

    def refresh_runtime_status(self) -> None:
        plat = getattr(getattr(self.app_core, "ctx", None), "platform", None) if self.app_core else None
        elevated = bool(plat and hasattr(plat, "is_elevated") and plat.is_elevated())
        if elevated:
            self.badge_elevated.set_status(tokens.SystemStatus.ACTIVE, "صلاحيات مسؤول Windows مفعّلة (Elevated)")
        else:
            self.badge_elevated.set_status(tokens.SystemStatus.WARNING, "يعمل بصلاحيات مستخدم عادية (بعض ميزات QoS تتطلب مسؤول)")
        self.lbl_runtime_info.setText(
            "الخدمات النشطة: ObservabilityEngine · DiagnosisEngine · TrafficController (ETW/QoS) · DNSOptimizer · WifiDiagnosticsBundle"
        )
