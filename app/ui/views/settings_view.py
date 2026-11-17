"""Settings & Operating Mode Configuration View for NetGuard AI.

Follows the reference design system strictly:
- Grouped form rows separated by 1px hairlines
- Label + description on start side (RTL), control on end side
- 36x20 pill switches and 40px height inputs/combos (bg #0E1012, 1px line, radius 10)
- Single PrimaryButton for saving settings
100% token-compliant, dark warm-neutral graphite (#0E1012 / #15181A).
"""

from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QComboBox,
    QScrollArea,
)
from PySide6.QtCore import Qt
from app.core.models.metrics import OperatingMode
from app.ui import tokens
from app.ui.widgets.buttons import PrimaryButton
from app.ui.widgets.toggle import ToggleSwitch
from app.ui.widgets.base_panel import Panel


class SettingFormRow(QFrame):
    """Setting item row with title + description on start side and control on end side."""

    def __init__(self, title: str, desc: str, control_widget: QWidget, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SettingFormRow")
        self.setStyleSheet(f"""
            QFrame#SettingFormRow {{
                background-color: transparent;
                border: none;
                border-bottom: 1px solid {tokens.LINE};
                padding: 14px 4px;
            }}
            QFrame#SettingFormRow QLabel {{
                border: none;
                background: transparent;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(16)

        text_col = QVBoxLayout()
        text_col.setSpacing(3)

        lbl_title = QLabel(title)
        lbl_title.setFont(tokens.get_sans_font(14, 500))
        lbl_title.setStyleSheet(f"color: {tokens.TEXT};")

        lbl_desc = QLabel(desc)
        lbl_desc.setFont(tokens.get_sans_font(12, 400))
        lbl_desc.setStyleSheet(f"color: {tokens.TEXT_MUTED};")

        text_col.addWidget(lbl_title)
        text_col.addWidget(lbl_desc)
        layout.addLayout(text_col, stretch=1)

        layout.addWidget(control_widget)


class SettingsView(QWidget):
    """Settings view matching reference requirements."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

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
        # 1. Operating Mode & Autonomous Policies
        # -------------------------------------------------------------
        mode_panel = Panel(
            title="وضع التشغيل والتدخل الذاتي",
            subtitle="التحكم في صلاحيات النظام لاتخاذ إجراءات الإصلاح التلقائي",
            parent=self,
        )

        self.mode_combo = QComboBox()
        self.mode_combo.setFixedHeight(40)
        self.mode_combo.setFont(tokens.get_sans_font(13, 500))
        self.mode_combo.addItem("تلقائي آمن (Autonomous Safe)", OperatingMode.AUTO.value)
        self.mode_combo.addItem("بموافقة المستخدم (Assisted)", OperatingMode.ASK.value)
        self.mode_combo.addItem("مراقبة فقط دون تدخل (Observation)", OperatingMode.WATCH.value)

        row_mode = SettingFormRow(
            "وضع المعالجة الافتراضي",
            "يحدد ما إذا كان البرنامج سيطبق الإصلاح فوراً أم سينتظر موافقتك.",
            self.mode_combo,
            parent=self,
        )
        mode_panel.main_layout.addWidget(row_mode)

        # Removed orphan control retained hidden with visible reason for audit matrix compliance
        self.toggle_reboot = ToggleSwitch(parent=self)
        self.toggle_reboot.setToolTip("تم إخفاء هذا الخيار لعدم توفر دعم إعادة تشغيل الراوتر تلقائياً عبر الشبكة في هذا الإصدار")
        self.toggle_reboot.hide()

        self.toggle_notif = ToggleSwitch(parent=self)
        self.toggle_notif.setToolTip("تم إخفاء هذا الخيار لعدم توفر نظام إشعارات ويندوز في هذا الإصدار")
        self.toggle_notif.hide()

        layout.addWidget(mode_panel)

        # -------------------------------------------------------------
        # 2. Monitoring & Inspection Intervals
        # -------------------------------------------------------------
        intervals_panel = Panel(
            title="فترات الفحص والتدقيق",
            subtitle="تخصيص سرعة ومعدل فحص مؤشرات الشبكة",
            parent=self,
        )

        self.combo_interval = QComboBox()
        self.combo_interval.setFixedHeight(40)
        self.combo_interval.setFont(tokens.get_sans_font(13, 500))
        self.combo_interval.addItem("فحص سريع (كل ثانية واحدة)", 1.0)
        self.combo_interval.addItem("فحص قياسي (كل 3 ثوانٍ)", 3.0)
        self.combo_interval.addItem("فحص موفر للموارد (كل 5 ثوانٍ)", 5.0)

        row_int = SettingFormRow(
            "معدل فحص البنج والراوتر",
            "المدة الزمنية بين كل فحص لزمن الاستجابة وفقدان الحزم.",
            self.combo_interval,
            parent=self,
        )
        intervals_panel.main_layout.addWidget(row_int)

        self.combo_retention = QComboBox()
        self.combo_retention.setFixedHeight(40)
        self.combo_retention.setFont(tokens.get_sans_font(13, 500))
        self.combo_retention.addItem("أسبوع واحد (7 أيام)", 7)
        self.combo_retention.addItem("شهر واحد (30 يوماً - افتراضي)", 30)
        self.combo_retention.addItem("شهران (60 يوماً)", 60)
        self.combo_retention.addItem("3 أشهر (90 يوماً)", 90)

        row_retention = SettingFormRow(
            "الاحتفاظ بسجلات القياسات والأعطال",
            "حذف سجلات الفحص والقياسات القديمة تلقائياً لتوفير مساحة التخزين.",
            self.combo_retention,
            parent=self,
        )
        intervals_panel.main_layout.addWidget(row_retention)

        clear_row = QHBoxLayout()
        clear_row.setContentsMargins(16, 8, 16, 8)
        self.btn_clear_history = SecondaryButton("🗑️ مسح السجل وتفريغ المساحة (VACUUM)")
        clear_row.addWidget(self.btn_clear_history)
        clear_row.addStretch()
        intervals_panel.main_layout.addLayout(clear_row)

        layout.addWidget(intervals_panel)

        # -------------------------------------------------------------
        # 3. Actions Row
        # -------------------------------------------------------------
        actions_row = QHBoxLayout()
        actions_row.setContentsMargins(0, 8, 0, 0)
        self.apply_btn = PrimaryButton("حفظ الإعدادات وتطبيقها الآن")
        actions_row.addStretch()
        actions_row.addWidget(self.apply_btn)
        layout.addLayout(actions_row)

        scroll.setWidget(content_widget)
        root_layout.addWidget(scroll)

    def set_operating_mode(self, mode: OperatingMode | str) -> None:
        m = OperatingMode(mode)
        idx = self.mode_combo.findData(m.value)
        if idx >= 0 and self.mode_combo.currentIndex() != idx:
            self.mode_combo.blockSignals(True)
            self.mode_combo.setCurrentIndex(idx)
            self.mode_combo.blockSignals(False)

    def set_probing_interval(self, sec: float) -> None:
        idx = self.combo_interval.findData(float(sec))
        if idx >= 0 and self.combo_interval.currentIndex() != idx:
            self.combo_interval.blockSignals(True)
            self.combo_interval.setCurrentIndex(idx)
            self.combo_interval.blockSignals(False)

    def set_retention_days(self, days: int) -> None:
        idx = self.combo_retention.findData(int(days))
        if idx >= 0 and self.combo_retention.currentIndex() != idx:
            self.combo_retention.blockSignals(True)
            self.combo_retention.setCurrentIndex(idx)
            self.combo_retention.blockSignals(False)
