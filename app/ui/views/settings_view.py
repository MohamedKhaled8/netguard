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
        self.mode_combo.addItem("تلقائي آمن (Autonomous Safe)", "safe")
        self.mode_combo.addItem("بموافقة المستخدم (Assisted)", "assisted")
        self.mode_combo.addItem("مراقبة فقط دون تدخل (Observation)", "observe")

        row_mode = SettingFormRow(
            "وضع المعالجة الافتراضي",
            "يحدد ما إذا كان البرنامج سيطبق الإصلاح فوراً أم سينتظر موافقتك.",
            self.mode_combo,
            parent=self,
        )
        mode_panel.main_layout.addWidget(row_mode)

        self.toggle_reboot = ToggleSwitch(checked=False, parent=self)
        row_reboot = SettingFormRow(
            "السماح بإعادة تشغيل الراوتر تلقائياً",
            "غير مفعل افتراضياً لتجنب قطع الاتصال عن الأجهزة الأخرى في المنزل.",
            self.toggle_reboot,
            parent=self,
        )
        mode_panel.main_layout.addWidget(row_reboot)

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
        self.combo_interval.addItem("فحص سريع (كل ثانية واحدة)", 1)
        self.combo_interval.addItem("فحص قياسي (كل 3 ثوانٍ)", 3)
        self.combo_interval.addItem("فحص موفر للموارد (كل 5 ثوانٍ)", 5)

        row_int = SettingFormRow(
            "معدل فحص البنج والراوتر",
            "المدة الزمنية بين كل فحص لزمن الاستجابة وفقدان الحزم.",
            self.combo_interval,
            parent=self,
        )
        intervals_panel.main_layout.addWidget(row_int)

        self.toggle_notif = ToggleSwitch(checked=True, parent=self)
        row_notif = SettingFormRow(
            "إشعارات ويندوز عند حل مشكلة",
            "إظهار إشعار فوري عند رصد عطل والانتهاء من إصلاحه بنجاح.",
            self.toggle_notif,
            parent=self,
        )
        intervals_panel.main_layout.addWidget(row_notif)

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
