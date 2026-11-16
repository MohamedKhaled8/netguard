"""Autonomous Remediation & Self-Healing View for NetGuard AI.

Follows the reference design system strictly:
- Large 3-option mode selector with detailed descriptions
- Policy list with toggle rows (title + one-line description)
- Self-healing quick tools (Flush DNS, Renew IP)
- Audit ledger as hairline rows (time · cause · action · result chip)
100% token-compliant, dark warm-neutral graphite (#0E1012 / #15181A).
"""

from __future__ import annotations
from typing import List, Optional
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from app.core.models.metrics import OperatingMode
from app.ui import tokens
from app.ui.widgets.buttons import PrimaryButton, SecondaryButton
from app.ui.widgets.chip import Chip
from app.ui.widgets.toggle import ToggleSwitch
from app.ui.widgets.base_panel import Panel


class ModeOptionCard(QFrame):
    """Large selectable mode card for Remediation view."""

    clicked = Signal(int)

    def __init__(self, index: int, title: str, desc: str, is_selected: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("ModeOptionCard")
        self.index = index
        self.is_selected = is_selected
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.dot = QLabel()
        self.dot.setFixedSize(8, 8)
        top_row.addWidget(self.dot)

        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(tokens.get_sans_font(15, 600))
        top_row.addWidget(self.lbl_title)
        top_row.addStretch()
        layout.addLayout(top_row)

        self.lbl_desc = QLabel(desc)
        self.lbl_desc.setFont(tokens.get_sans_font(13, 400))
        self.lbl_desc.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self.lbl_desc.setWordWrap(True)
        layout.addWidget(self.lbl_desc)

        self.set_selected(is_selected)

    def set_selected(self, selected: bool) -> None:
        self.is_selected = selected
        if selected:
            self.dot.setStyleSheet(f"background-color: {tokens.ACCENT}; border-radius: 4px;")
            self.setStyleSheet(f"""
                QFrame#ModeOptionCard {{
                    background-color: {tokens.SURFACE_HOVER};
                    border: 1px solid {tokens.LINE_THRESHOLD};
                    border-radius: {tokens.RADIUS_INNER}px;
                }}
                QFrame#ModeOptionCard QLabel {{
                    border: none;
                    background: transparent;
                }}
            """)
        else:
            self.dot.setStyleSheet(f"background-color: {tokens.LINE_THRESHOLD}; border-radius: 4px;")
            self.setStyleSheet(f"""
                QFrame#ModeOptionCard {{
                    background-color: {tokens.SURFACE_INSET};
                    border: 1px solid {tokens.LINE};
                    border-radius: {tokens.RADIUS_INNER}px;
                }}
                QFrame#ModeOptionCard:hover {{
                    background-color: {tokens.SURFACE_HOVER};
                }}
                QFrame#ModeOptionCard QLabel {{
                    border: none;
                    background: transparent;
                }}
            """)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.index)
        super().mousePressEvent(event)


class PolicyToggleRow(QFrame):
    """Single policy row with label, description, and toggle switch."""

    def __init__(self, title: str, desc: str, checked: bool = True, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("PolicyToggleRow")
        self.setStyleSheet(f"""
            QFrame#PolicyToggleRow {{
                background-color: transparent;
                border: none;
                border-bottom: 1px solid {tokens.LINE};
                padding: 12px 4px;
            }}
            QFrame#PolicyToggleRow QLabel {{
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

        self.toggle = ToggleSwitch(checked=checked, parent=self)
        layout.addWidget(self.toggle)


class AuditEventRow(QFrame):
    """Collapsed 1-row event in the remediation ledger: time · cause · action · result chip."""

    def __init__(self, time_str: str, cause_str: str, action_str: str, is_success: bool = True, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("AuditEventRow")
        self.setStyleSheet(f"""
            QFrame#AuditEventRow {{
                background-color: transparent;
                border: none;
                border-bottom: 1px solid {tokens.LINE};
                padding: 10px 4px;
            }}
            QFrame#AuditEventRow:hover {{
                background-color: {tokens.SURFACE_HOVER};
            }}
            QFrame#AuditEventRow QLabel {{
                border: none;
                background: transparent;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(16)

        lbl_time = QLabel(time_str)
        lbl_time.setFont(tokens.get_mono_font(12, 400))
        lbl_time.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        lbl_time.setFixedWidth(70)
        layout.addWidget(lbl_time)

        lbl_cause = QLabel(cause_str)
        lbl_cause.setFont(tokens.get_sans_font(13, 500))
        lbl_cause.setStyleSheet(f"color: {tokens.TEXT};")
        layout.addWidget(lbl_cause, stretch=2)

        lbl_action = QLabel(action_str)
        lbl_action.setFont(tokens.get_sans_font(13, 400))
        lbl_action.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        layout.addWidget(lbl_action, stretch=3)

        chip = Chip("ناجح ومؤمن" if is_success else "فشل", variant="ok-soft" if is_success else "bad-soft")
        layout.addWidget(chip)


class RemediationView(QWidget):
    """Autonomous Remediation View matching reference requirements."""

    mode_changed = Signal(object)

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
        # 1. Mode Selector (3 options, larger with visible descriptions)
        # -------------------------------------------------------------
        mode_panel = Panel(
            title="وضع المعالجة والإصلاح التلقائي",
            subtitle="حدد درجة التدخل الذاتي المسموحة للنظام",
            parent=self,
        )

        modes_layout = QHBoxLayout()
        modes_layout.setSpacing(12)

        self.mode_auto = ModeOptionCard(
            0,
            "تلقائي (مستحسن)",
            "يكتشف المشكلة ويصلحها فوراً ثم يسجل ما فعله بالتفصيل دون مقاطعة عملك.",
            is_selected=True,
        )
        self.mode_assisted = ModeOptionCard(
            1,
            "بموافقتي",
            "يقترح الإصلاح المناسب عند حدوث مشكلة وينتظر موافقتك قبل أي تغيير في النظام.",
            is_selected=False,
        )
        self.mode_observe = ModeOptionCard(
            2,
            "مراقبة فقط",
            "يراقب ويسجل مؤشرات الشبكة دون إجراء أي تغيير على إعدادات جهازك.",
            is_selected=False,
        )

        self.mode_cards = [self.mode_auto, self.mode_assisted, self.mode_observe]
        for card in self.mode_cards:
            card.clicked.connect(self._select_mode)
            modes_layout.addWidget(card)

        mode_panel.main_layout.addLayout(modes_layout)
        layout.addWidget(mode_panel)

        # -------------------------------------------------------------
        # 2. Quick Self-Healing Tools
        # -------------------------------------------------------------
        tools_panel = Panel(
            title="أدوات الاستشفاء السريع",
            subtitle="إجراءات يدوية فورية لحل مشاكل الاتصال المتكررة بضغطة واحدة",
            parent=self,
        )

        tools_row = QHBoxLayout()
        tools_row.setSpacing(12)

        self.btn_flush_now = SecondaryButton("تنظيف كاش DNS")
        self.btn_renew_ip = SecondaryButton("تجديد مسار الاتصال")

        tools_row.addWidget(self.btn_flush_now)
        tools_row.addWidget(self.btn_renew_ip)
        tools_row.addStretch()

        tools_panel.main_layout.addLayout(tools_row)
        layout.addWidget(tools_panel)

        # -------------------------------------------------------------
        # 3. Policy List (Toggle rows)
        # -------------------------------------------------------------
        policy_panel = Panel(
            title="سياسات المعالجة الذاتية الفعالة",
            subtitle="تخصيص قواعد وتدخلات النظام عند رصد تذبذب الاتصال",
            parent=self,
        )

        self.pol1 = PolicyToggleRow("تفريغ كاش DNS التلقائي", "إفراغ العناوين المعلقة فوراً عند رصد أخطاء DNS_PROBE", checked=True)
        self.pol2 = PolicyToggleRow("تأمين أولوية مكالمات الفيديو (Meeting Guard)", "خفض سرعة تحديثات الخلفية لحماية مكالمات Zoom / Teams", checked=True)
        self.pol3 = PolicyToggleRow("التحويل التلقائي لأسرع خادم DNS", "تطبيق أسرع خادم بنشمارك عالمي عند تباطؤ مزود الخدمة", checked=True)
        self.pol4 = PolicyToggleRow("تجديد IP تلقائياً عند انقطاع الراوتر", "طلب عنوان شبكة جديد تلقائياً عند تعليق بطاقة Wi-Fi", checked=True)

        policy_panel.main_layout.addWidget(self.pol1)
        policy_panel.main_layout.addWidget(self.pol2)
        policy_panel.main_layout.addWidget(self.pol3)
        policy_panel.main_layout.addWidget(self.pol4)
        layout.addWidget(policy_panel)

        # -------------------------------------------------------------
        # 4. Audit Ledger (Collapsed 1-row timeline events)
        # -------------------------------------------------------------
        self.ledger_panel = Panel(
            title="سجل التدخلات والإصلاحات المعتمدة",
            subtitle="أرشيف موثق لجميع الإجراءات التي تمت لحماية استقرار اتصالك",
            parent=self,
        )

        self.events_layout = QVBoxLayout()
        self.events_layout.setSpacing(0)

        # Default sample events
        self.events_layout.addWidget(AuditEventRow("15:32:45", "تكدس حزم عند الراوتر (Bufferbloat)", "تحديد سرعة Windows Update بـ 40% من الخط", is_success=True))
        self.events_layout.addWidget(AuditEventRow("14:15:10", "بطء استجابة خادم DNS المحلي", "تفريغ كاش DNS والتبديل إلى Cloudflare 1.1.1.1", is_success=True))
        self.events_layout.addWidget(AuditEventRow("11:04:22", "انقطاع عابر في إشارة الواي فاي", "تجديد اتصال بطاقة الشبكة مع الراوتر المنزلي", is_success=True))

        self.ledger_panel.main_layout.addLayout(self.events_layout)
        layout.addWidget(self.ledger_panel)

        scroll.setWidget(content_widget)
        root_layout.addWidget(scroll)

    def set_operating_mode(self, mode: OperatingMode | str | int) -> None:
        if isinstance(mode, int):
            idx = mode
        else:
            target = OperatingMode(mode)
            mode_to_idx = {OperatingMode.AUTO: 0, OperatingMode.ASK: 1, OperatingMode.WATCH: 2}
            idx = mode_to_idx.get(target, 0)
        if getattr(self, "_current_mode_idx", None) == idx:
            return
        self._current_mode_idx = idx
        for i, card in enumerate(self.mode_cards):
            card.set_selected(i == idx)

    def _select_mode(self, idx: int) -> None:
        idx_to_mode = {0: OperatingMode.AUTO, 1: OperatingMode.ASK, 2: OperatingMode.WATCH}
        mode = idx_to_mode.get(idx, OperatingMode.AUTO)
        self.set_operating_mode(mode)
        self.mode_changed.emit(mode)

    def update_audit_log(self, audit_records: List[Any]) -> None:
        """Update audit ledger from real database records with authentic timestamps."""
        if not audit_records:
            return
        # Clear previous rows
        while self.events_layout.count():
            item = self.events_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for rec in audit_records[:10]:
            ts = getattr(rec, "timestamp", None)
            if isinstance(ts, datetime):
                local_dt = ts.astimezone() if ts.tzinfo else ts
                time_str = local_dt.strftime("%H:%M:%S")
            elif isinstance(ts, str):
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    time_str = dt.astimezone().strftime("%H:%M:%S")
                except Exception:
                    time_str = ts[:8]
            else:
                time_str = "--:--:--"

            name = getattr(rec, "action_name", "إجراء صيانة")
            trigger = str(getattr(rec, "trigger_diagnosis_id", "") or "")
            if trigger == "autonomous_optimizer":
                cause_str = "تحسين استباقي لمسار DNS"
            elif trigger == "meeting_guard":
                cause_str = "حماية جودة مكالمات الفيديو"
            elif "bufferbloat" in trigger.lower():
                cause_str = "تكدس حزم عند الراوتر"
            elif trigger:
                cause_str = "تدخل استشفاء تلقائي"
            else:
                cause_str = "صيانة مسار الاتصال"

            status_obj = getattr(rec, "status", None)
            is_ok = "SUCCEEDED" in str(status_obj).upper() if status_obj else True
            row = AuditEventRow(time_str, cause_str, name, is_success=is_ok)
            self.events_layout.addWidget(row)
