"""Organized 11-Category Configuration Center View for NetGuard AI.

Categories:
1. General (Operating Mode & Startup Behavior)
2. Appearance (Compact vs Spacious Density & Theme Tokens)
3. Language (Arabic RTL / English LTR instant toggle)
4. Network Diagnostics (Probing interval & thresholds)
5. Meeting Guard (Hysteresis sensitivity & ETW confirmation)
6. QoS (Upload throttle rate & ActiveStore protection toggles)
7. DNS (Benchmark cooldown, auto-switch, meeting freeze safety)
8. Router Management (Single-attempt lockout guard & HTTP warning policy)
9. Security (DPAPI credential policy & report redaction)
10. Logging (Retention days & database compression/clearing)
11. Advanced & Updates (Remote update feed URL, auto-install, Reset to Defaults)
"""

from __future__ import annotations

from typing import Any, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.models.metrics import OperatingMode
from app.core.updater import (
    UpdateChecker,
    get_auto_install_updates,
    get_configured_update_source,
)
from app.ui import tokens
from app.ui.i18n import get_language, language_manager, set_language, tr
from app.ui.widgets.base_panel import Panel
from app.ui.widgets.buttons import GhostButton, PrimaryButton, SecondaryButton
from app.ui.widgets.toggle import ToggleSwitch
from app.version import __version__


class SettingFormRow(QWidget):
    """Single row: setting title & description paired with right/left control widget."""

    def __init__(self, title: str, desc: str, control_widget: QWidget, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(16)

        info_col = QVBoxLayout()
        info_col.setSpacing(3)
        lbl_t = QLabel(title)
        lbl_t.setFont(tokens.get_sans_font(13, 600))
        lbl_t.setStyleSheet(f"color: {tokens.TEXT}; background: transparent;")
        lbl_t.setWordWrap(True)

        lbl_d = QLabel(desc)
        lbl_d.setFont(tokens.get_sans_font(12, 400))
        lbl_d.setStyleSheet(f"color: {tokens.TEXT_MUTED}; background: transparent;")
        lbl_d.setWordWrap(True)

        info_col.addWidget(lbl_t)
        info_col.addWidget(lbl_d)
        layout.addLayout(info_col, 1)
        layout.addWidget(control_widget)


class SettingsView(QWidget):
    """11-category Configuration Center preserving all settings & updater contracts."""

    language_changed_requested = Signal(str)
    reset_defaults_requested = Signal()

    CATEGORIES = [
        ("general", "عام / General"),
        ("appearance", "المظهر / Appearance"),
        ("language", "اللغة والاتجاه / Language"),
        ("diagnostics", "تشخيص الشبكة / Diagnostics"),
        ("meeting_guard", "حماية الاجتماعات / Meeting Guard"),
        ("qos", "أولوية الشبكة / QoS"),
        ("dns", "محسّن DNS / DNS"),
        ("router", "إدارة الراوتر / Router"),
        ("security", "الأمان والخصوصية / Security"),
        ("logging", "السجلات والتخزين / Logging"),
        ("advanced", "متقدم والتحديثات / Advanced"),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea(self)
        self.scroll = scroll
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {tokens.BG}; border: none; }}")

        container = QWidget()
        outer = QHBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setAlignment(Qt.AlignHCenter)

        holder = QWidget()
        self._content_holder = holder
        holder.setMaximumWidth(tokens.MAX_CONTENT_WIDTH)
        main_col = QVBoxLayout(holder)
        main_col.setContentsMargins(24, 20, 24, 32)
        main_col.setSpacing(16)

        # Header
        hdr = QVBoxLayout()
        hdr.setSpacing(10)
        top_hdr = QHBoxLayout()
        tcol = QVBoxLayout()
        tcol.setSpacing(4)
        self.lbl_title = QLabel(tr("set_title"))
        self.lbl_title.setFont(tokens.get_sans_font(20, 700))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_title.setWordWrap(True)
        self.lbl_sub = QLabel(tr("set_sub"))
        self.lbl_sub.setFont(tokens.get_sans_font(12, 400))
        self.lbl_sub.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_sub.setWordWrap(True)
        tcol.addWidget(self.lbl_title)
        tcol.addWidget(self.lbl_sub)
        top_hdr.addLayout(tcol, 1)
        hdr.addLayout(top_hdr)

        hdr_btns = QHBoxLayout()
        hdr_btns.setSpacing(8)
        self.btn_reset_defaults = GhostButton("استعادة الافتراضي")
        self.btn_reset_defaults.clicked.connect(self._on_reset_clicked)
        self.apply_btn = PrimaryButton("حفظ وتطبيق الإعدادات")
        hdr_btns.addWidget(self.apply_btn)
        hdr_btns.addWidget(self.btn_reset_defaults)
        hdr_btns.addStretch()
        hdr.addLayout(hdr_btns)
        main_col.addLayout(hdr)

        # Validation error strip
        self.lbl_validation_error = QLabel("")
        self.lbl_validation_error.setVisible(False)
        self.lbl_validation_error.setFont(tokens.get_sans_font(12, 600))
        self.lbl_validation_error.setStyleSheet(
            f"color: {tokens.STATUS_BAD}; background-color: {tokens.BAD_SOFT_BG}; border: 1px solid {tokens.BAD_SOFT_BORDER}; border-radius: 6px; padding: 8px 12px;"
        )
        main_col.addWidget(self.lbl_validation_error)

        # Split Sidebar Categories + Category Stack
        body_row = QHBoxLayout()
        body_row.setSpacing(16)

        self.cat_list = QListWidget()
        self.cat_list.setMinimumWidth(210)
        self.cat_list.setMaximumWidth(250)
        self.cat_list.setMinimumHeight(520)
        self.cat_list.setStyleSheet(
            f"""
            QListWidget {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE};
                border-radius: 10px;
                padding: 8px;
            }}
            QListWidget::item {{
                color: {tokens.TEXT_MUTED};
                padding: 10px 12px;
                min-height: 22px;
                border-radius: 6px;
                margin-bottom: 3px;
            }}
            QListWidget::item:selected {{
                background-color: {tokens.ACCENT};
                color: {tokens.ON_ACCENT};
                font-weight: 600;
            }}
            """
        )
        for _cid, cname in self.CATEGORIES:
            self.cat_list.addItem(QListWidgetItem(cname))
        self.cat_list.currentRowChanged.connect(self._on_category_selected)

        self.cat_stack = QStackedWidget()
        body_row.addWidget(self.cat_list)
        body_row.addWidget(self.cat_stack, 1)
        main_col.addLayout(body_row)

        self._build_all_categories()
        self.cat_list.setCurrentRow(0)

        outer.addWidget(holder)
        scroll.setWidget(container)
        root_layout.addWidget(scroll)
        language_manager().language_changed.connect(self.retranslate)

    def _build_all_categories(self) -> None:
        # 0. General
        p0 = Panel(title="1. عام / General", subtitle="وضع التشغيل الافتراضي وسلوك بدء النظام", padding=16)
        self.mode_combo = QComboBox()
        self.mode_combo.setMinimumWidth(240)
        self.mode_combo.addItem("تلقائي آمن / Autonomous Safe", OperatingMode.AUTO.value)
        self.mode_combo.addItem("بموافقتي / Approval Required", OperatingMode.ASK.value)
        self.mode_combo.addItem("مراقبة فقط / Observation Only", OperatingMode.WATCH.value)
        p0.main_layout.addWidget(
            SettingFormRow(
                "وضع التشغيل الرئيسي",
                "يحدد حدود التدخل التلقائي عند رصد مشاكل في الشبكة أو DNS.",
                self.mode_combo,
            )
        )
        self.toggle_minimize_tray = ToggleSwitch(checked=True)
        p0.main_layout.addWidget(
            SettingFormRow("التصغير إلى شريط المهام", "إبقاء مراقبة المكالمات نشطة بالخلفية عند إغلاق النافذة.", self.toggle_minimize_tray)
        )
        # Kept hidden for legacy contract compatibility
        self.toggle_reboot = ToggleSwitch(parent=self)
        self.toggle_reboot.hide()
        self.toggle_notif = ToggleSwitch(parent=self)
        self.toggle_notif.hide()
        p0.main_layout.addStretch()
        self.cat_stack.addWidget(p0)

        # 1. Appearance
        p1 = Panel(title="2. المظهر / Appearance", subtitle="كثافة المعلومات والرسوم المتحركة", padding=16)
        self.combo_density = QComboBox()
        self.combo_density.addItem("قياسي / Balanced Workstation", "balanced")
        self.combo_density.addItem("مضغوط / Compact NOC", "compact")
        self.toggle_animations = ToggleSwitch(checked=tokens.ANIMATIONS_ENABLED)
        p1.main_layout.addWidget(SettingFormRow("كثافة الواجهة", "تخصيص المسافات بين اللوحات والجداول.", self.combo_density))
        p1.main_layout.addWidget(SettingFormRow("الرسوم الحركية", "تفعيل أو تعطيل نبض المؤشرات وتحديثات الرسوم السلسة.", self.toggle_animations))
        p1.main_layout.addStretch()
        self.cat_stack.addWidget(p1)

        # 2. Language
        p2 = Panel(title="3. اللغة والاتجاه / Language & Direction", subtitle="التبديل الفوري بين العربية RTL والإنجليزية LTR", padding=16)
        self.combo_language = QComboBox()
        self.combo_language.addItem("العربية (RTL)", "ar")
        self.combo_language.addItem("English (LTR)", "en")
        self.combo_language.setCurrentIndex(0 if get_language() == "ar" else 1)
        self.combo_language.currentIndexChanged.connect(self._on_lang_combo_changed)
        p2.main_layout.addWidget(SettingFormRow("لغة التطبيق", "يتحول اتجاه النوافذ والقوائم والجداول فوراً دون فقدان البيانات.", self.combo_language))
        p2.main_layout.addStretch()
        self.cat_stack.addWidget(p2)

        # 3. Network Diagnostics
        p3 = Panel(title="4. تشخيص الشبكة / Network Diagnostics", subtitle="فترات قياس الكمون وفقدان الحزم", padding=16)
        self.combo_interval = QComboBox()
        self.combo_interval.addItem("فحص سريع (كل ثانية)", 1.0)
        self.combo_interval.addItem("فحص قياسي (كل 3 ثوانٍ)", 3.0)
        self.combo_interval.addItem("فحص موفر للموارد (كل 5 ثوانٍ)", 5.0)
        p3.main_layout.addWidget(SettingFormRow("معدل فحص المسار", "الفترة الزمنية بين كل دورة فحص للبوابة والإنترنت.", self.combo_interval))

        self.spin_lat_warn = QSpinBox()
        self.spin_lat_warn.setRange(20, 500)
        self.spin_lat_warn.setValue(60)
        self.spin_lat_warn.setSuffix(" ms")
        p3.main_layout.addWidget(SettingFormRow("حد تحذير الكمون", "عتبة الكمون (ms) التي تُطلق التنبيه التشخيصي.", self.spin_lat_warn))
        p3.main_layout.addStretch()
        self.cat_stack.addWidget(p3)

        # 4. Meeting Guard
        p4 = Panel(title="5. حماية الاجتماعات / Meeting Guard", subtitle="ضوابط الكشف والانتقال المستقر (Hysteresis & ETW)", padding=16)
        self.toggle_etw_confirm = ToggleSwitch(checked=True)
        self.toggle_closed_loop_rollback = ToggleSwitch(checked=True)
        p4.main_layout.addWidget(SettingFormRow("تأكيد ETW للوسائط الفعلية", "تأكيد إرسال حزم UDP قبل تفعيل الحماية لتفادي الإنذار الكاذب.", self.toggle_etw_confirm))
        p4.main_layout.addWidget(SettingFormRow("التراجع التلقائي عند تدهور المكالمة", "إزالة QoS فوراً إذا قفز التذبذب أو فقدان الحزم أثناء الحماية.", self.toggle_closed_loop_rollback))
        p4.main_layout.addStretch()
        self.cat_stack.addWidget(p4)

        # 5. QoS
        p5 = Panel(title="6. أولوية الشبكة / QoS Policies", subtitle="تقييد الرفع الخلفي وتقسيم منافذ Teams", padding=16)
        self.spin_throttle_mbps = QSpinBox()
        self.spin_throttle_mbps.setRange(1, 500)
        self.spin_throttle_mbps.setValue(5)
        self.spin_throttle_mbps.setSuffix(" Mbps")
        self.toggle_teams_split_cfg = ToggleSwitch(checked=True)
        p5.main_layout.addWidget(SettingFormRow("سقف رفع التطبيقات الخلفية", "الحد الأقصى لتطبيقات التحديث/السحابة أثناء الاجتماع.", self.spin_throttle_mbps))
        p5.main_layout.addWidget(SettingFormRow("تقسيم منافذ Teams (UDP 3478-3481)", "تمييز حزم الصوت/الفيديو/المشاركة بدقة.", self.toggle_teams_split_cfg))
        p5.main_layout.addStretch()
        self.cat_stack.addWidget(p5)

        # 6. DNS
        p6 = Panel(title="7. محسّن DNS / DNS Settings", subtitle="حماية جلسات المكالمات ومنع التبديل غير الضروري", padding=16)
        self.toggle_dns_freeze_call = ToggleSwitch(checked=True)
        self.toggle_dns_auto_best = ToggleSwitch(checked=True)
        p6.main_layout.addWidget(SettingFormRow("تجميد تغيير DNS أثناء الاجتماع", "منع تبديل الخادم تماماً طوال وجود مكالمة نشطة.", self.toggle_dns_freeze_call))
        p6.main_layout.addWidget(SettingFormRow("التحويل التلقائي للأسرع عند الفجوة الكبيرة", "يتطلب صلاحية الوضع التلقائي وتفوقاً واضحاً مستمراً.", self.toggle_dns_auto_best))
        p6.main_layout.addStretch()
        self.cat_stack.addWidget(p6)

        # 7. Router Management
        p7 = Panel(title="8. إدارة الراوتر / Router Management", subtitle="ضوابط الأمان ومنع قفل صفحة الإدارة", padding=16)
        self.spin_router_timeout = QSpinBox()
        self.spin_router_timeout.setRange(2, 20)
        self.spin_router_timeout.setValue(6)
        self.spin_router_timeout.setSuffix(" s")
        self.toggle_single_attempt_guard = ToggleSwitch(checked=True)
        p7.main_layout.addWidget(SettingFormRow("مهلة طلب الراوتر", "المدة القصوى للانتظار قبل اعتبار الطلب timeout دون احتساب فشل كلمة مرور.", self.spin_router_timeout))
        p7.main_layout.addWidget(SettingFormRow("قيد محاولة المصادقة الواحدة", "منع إعادة المحاولة التلقائية لكلمة المرور لتجنب قفل الراوتر.", self.toggle_single_attempt_guard))
        p7.main_layout.addStretch()
        self.cat_stack.addWidget(p7)

        # 8. Security
        p8 = Panel(title="9. الأمان والخصوصية / Security & Redaction", subtitle="تنقيح التقارير وتشفير الاعتماد المحلي", padding=16)
        self.toggle_redact_exports = ToggleSwitch(checked=True)
        p8.main_layout.addWidget(SettingFormRow("تنقيح الأسرار عند التصدير", "إخفاء كلمات المرور وبيانات Wi-Fi PSK تلقائياً من التقارير المصدّرة.", self.toggle_redact_exports))
        p8.main_layout.addStretch()
        self.cat_stack.addWidget(p8)

        # 9. Logging
        p9 = Panel(title="10. السجلات والتخزين / Logging & Retention", subtitle="فترة الاحتفاظ بقاعدة البيانات المحلية والتنظيف", padding=16)
        self.combo_retention = QComboBox()
        self.combo_retention.addItem("أسبوع واحد (7 أيام)", 7)
        self.combo_retention.addItem("شهر واحد (30 يوماً - افتراضي)", 30)
        self.combo_retention.addItem("شهران (60 يوماً)", 60)
        self.combo_retention.addItem("3 أشهر (90 يوماً)", 90)
        self.btn_clear_history = SecondaryButton("تنظيف وضغط قاعدة البيانات")
        p9.main_layout.addWidget(SettingFormRow("مدة حفظ القياسات والأعطال", "تنظيف السجلات الأقدم تلقائياً لتوفير المساحة.", self.combo_retention))
        p9.main_layout.addWidget(SettingFormRow("صيانة قاعدة البيانات", "تفريغ وضغط ملف السجلات فوراً.", self.btn_clear_history))
        p9.main_layout.addStretch()
        self.cat_stack.addWidget(p9)

        # 10. Advanced & Updates
        p10 = Panel(title="11. متقدم والتحديثات / Advanced & Updates", subtitle="مصدر التحديثات المحلي وتدفق التثبيت الآمن", padding=16)
        self.input_update_source = QLineEdit()
        self.input_update_source.setPlaceholderText(r"\\SERVER\NetGuardUpdates\version.json أو http://192.168.1.x:8765/version.json")
        initial_source = get_configured_update_source()
        if initial_source:
            self.input_update_source.setText(initial_source)
        p10.main_layout.addWidget(SettingFormRow("مصدر التحديثات (LAN / HTTP)", "مسار مجلد شبكي أو رابط HTTP.", self.input_update_source))

        self.toggle_auto_update = ToggleSwitch(parent=self)
        self.toggle_auto_update.setChecked(get_auto_install_updates())
        p10.main_layout.addWidget(SettingFormRow("تثبيت التحديثات تلقائياً", "تحقق عبر SHA-256 ثم التثبيت التلقائي.", self.toggle_auto_update))

        ver_row = QHBoxLayout()
        ver_row.setContentsMargins(14, 8, 14, 8)
        self.lbl_current_version = QLabel(f"v{__version__}")
        self.lbl_current_version.setFont(tokens.get_mono_font(13, 600))
        self.lbl_current_version.setStyleSheet(f"color: {tokens.ACCENT_BRIGHT};")
        self.btn_check_updates = SecondaryButton("التحقق من وجود تحديثات")
        self.btn_check_updates.clicked.connect(self._on_check_updates_clicked)
        self.btn_install_update = PrimaryButton("تنزيل وتثبيت التحديث الآن")
        self.btn_install_update.clicked.connect(self._on_install_update_clicked)
        self.btn_install_update.hide()
        ver_row.addWidget(QLabel("الإصدار الحالي:"))
        ver_row.addWidget(self.lbl_current_version)
        ver_row.addStretch()
        ver_row.addWidget(self.btn_check_updates)
        ver_row.addWidget(self.btn_install_update)
        p10.main_layout.addLayout(ver_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        p10.main_layout.addWidget(self.progress_bar)

        self.lbl_update_status = QLabel("جاهز للتحقق من التحديثات.")
        self.lbl_update_status.setFont(tokens.get_sans_font(12, 400))
        self.lbl_update_status.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_update_status.setWordWrap(True)
        p10.main_layout.addWidget(self.lbl_update_status)
        p10.main_layout.addStretch()
        self.cat_stack.addWidget(p10)

        self.updater = UpdateChecker(parent=self)
        self.updater.update_found.connect(self._on_update_found)
        self.updater.up_to_date.connect(self._on_up_to_date)
        self.updater.check_failed.connect(self._on_update_failed)
        self.updater.download_progress.connect(self._on_download_progress)
        self.updater.download_finished.connect(self._on_download_finished)
        self.updater.download_failed.connect(self._on_download_failed)
        self.updater.install_failed.connect(self._on_install_failed)

    def _on_category_selected(self, row: int) -> None:
        if 0 <= row < self.cat_stack.count():
            self.cat_stack.setCurrentIndex(row)

    def _on_lang_combo_changed(self) -> None:
        lang = str(self.combo_language.currentData() or "ar")
        set_language(lang)
        self.language_changed_requested.emit(lang)

    def _on_reset_clicked(self) -> None:
        self.set_operating_mode(OperatingMode.AUTO)
        self.set_probing_interval(3.0)
        self.set_retention_days(30)
        self.spin_lat_warn.setValue(60)
        self.spin_throttle_mbps.setValue(5)
        self.spin_router_timeout.setValue(6)
        self.lbl_validation_error.setVisible(False)
        self.reset_defaults_requested.emit()

    def validate_inputs(self) -> tuple[bool, str]:
        src = self.input_update_source.text().strip()
        if src and not (src.startswith("http://") or src.startswith("https://") or src.startswith("\\\\")):
            msg = "رابط مصدر التحديثات يجب أن يبدأ بـ http:// أو https:// أو مسار شبكي UNC (\\\\server)."
            self.lbl_validation_error.setText(tokens.bidi_isolate_mixed(msg))
            self.lbl_validation_error.setVisible(True)
            return False, msg
        self.lbl_validation_error.setVisible(False)
        return True, ""

    def retranslate(self) -> None:
        self.lbl_title.setText(tr("set_title"))
        self.lbl_sub.setText(tr("set_sub"))

    def _on_check_updates_clicked(self) -> None:
        src = self.input_update_source.text().strip()
        self.updater.set_source(src)
        self.btn_check_updates.setEnabled(False)
        self.btn_check_updates.setText("جاري الفحص...")
        self.btn_install_update.hide()
        self.progress_bar.hide()
        self.lbl_update_status.setText("جاري التحقق من التحديثات...")
        self.updater.check_for_updates_async()

    def _on_update_found(self, data: dict) -> None:
        new_v = data.get("version", "جديد")
        notes = data.get("changelog") or data.get("release_notes") or "تحسينات على الأداء والاستقرار"
        self.btn_check_updates.setEnabled(True)
        self.btn_check_updates.setText("إعادة الفحص")
        is_auto = self.toggle_auto_update.isChecked()
        if is_auto:
            self.btn_install_update.hide()
            self.lbl_update_status.setText(tokens.bidi_isolate_mixed(f"يتوفر إصدار جديد v{new_v} — جاري التنزيل...\n{notes}"))
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.show()
            self.updater.download_update_async(data)
        else:
            self.btn_install_update.setText(f"تنزيل وتثبيت v{new_v}")
            self.btn_install_update.setEnabled(True)
            self.btn_install_update.show()
            self.lbl_update_status.setText(tokens.bidi_isolate_mixed(f"يتوفر إصدار جديد v{new_v}:\n{notes}"))

    def _on_up_to_date(self, msg: str) -> None:
        self.btn_check_updates.setEnabled(True)
        self.btn_check_updates.setText("التحقق من وجود تحديثات")
        self.btn_install_update.hide()
        self.progress_bar.hide()
        self.lbl_update_status.setText(tokens.bidi_isolate_mixed(msg))
        self.lbl_update_status.setStyleSheet(f"color: {tokens.STATUS_OK};")

    def _on_update_failed(self, err: str) -> None:
        self.btn_check_updates.setEnabled(True)
        self.btn_check_updates.setText("إعادة المحاولة")
        self.lbl_update_status.setText(tokens.bidi_isolate_mixed(err))
        self.lbl_update_status.setStyleSheet(f"color: {tokens.STATUS_WARN};")

    def _on_install_update_clicked(self) -> None:
        self.btn_install_update.setEnabled(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.updater.download_update_async()

    def _on_download_progress(self, done: int, total: int) -> None:
        if total > 0:
            self.progress_bar.setValue(min(100, max(0, int((done / total) * 100))))

    def _on_download_finished(self, staged_path: str) -> None:
        self.progress_bar.setValue(100)
        self.updater.apply_update_and_restart(staged_path)

    def _on_download_failed(self, err: str) -> None:
        self.progress_bar.hide()
        self.btn_install_update.setEnabled(True)
        self.lbl_update_status.setText(tokens.bidi_isolate_mixed(err))

    def _on_install_failed(self, msg: str) -> None:
        self.btn_install_update.setEnabled(True)
        self.lbl_update_status.setText(tokens.bidi_isolate_mixed(msg))

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

    def _sync_content_width(self) -> None:
        if hasattr(self, "scroll") and hasattr(self, "_content_holder"):
            vw = self.scroll.viewport().width()
            if vw > 0:
                self._content_holder.setFixedWidth(min(vw, tokens.MAX_CONTENT_WIDTH))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_content_width()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_content_width()
