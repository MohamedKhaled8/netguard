"""Settings and Operating Mode Configuration View.

Configuration interface for autonomous mode, language preference, probe intervals, and thresholds.
"""

from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QPushButton,
)
from PySide6.QtCore import Qt
from app.ui.i18n import tr, get_language, set_language


class SettingsView(QWidget):
    """Configuration interface for autonomous mode, probe intervals, and thresholds."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        banner = QFrame()
        banner.setStyleSheet("background-color: #111625; border: 1px solid #1c253b; border-radius: 10px; padding: 16px;")
        b_layout = QVBoxLayout(banner)

        self.title_lbl = QLabel(tr("set_banner_title"))
        self.title_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #58a6ff;")

        self.desc_lbl = QLabel(tr("set_banner_desc"))
        self.desc_lbl.setStyleSheet("font-size: 12px; color: #8b949e;")

        b_layout.addWidget(self.title_lbl)
        b_layout.addWidget(self.desc_lbl)
        layout.addWidget(banner)

        form_frame = QFrame()
        form_frame.setStyleSheet("background-color: #111625; border: 1px solid #1c253b; border-radius: 10px; padding: 18px;")
        self.form_layout = QFormLayout(form_frame)
        self.form_layout.setSpacing(14)

        # 1. Language selector
        self.lbl_lang = QLabel(tr("set_lang_label"))
        self.lbl_lang.setStyleSheet("font-weight: 700; color: #e6edf3;")
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("العربية (Arabic)", "ar")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.setCurrentIndex(0 if get_language() == "ar" else 1)
        self.form_layout.addRow(self.lbl_lang, self.lang_combo)

        # 2. Operating mode selector
        self.lbl_mode = QLabel(tr("set_mode_label"))
        self.lbl_mode.setStyleSheet("font-weight: 700; color: #e6edf3;")
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("حماية ذاتية آمنة (إصلاح ذكي تلقائي)", "autonomous_safe")
        self.mode_combo.addItem("وضع المساعد (طلب الإذن أولاً)", "assisted")
        self.mode_combo.addItem("وضع المراقبة فقط (بدون أي تعديلات)", "observation")
        self.form_layout.addRow(self.lbl_mode, self.mode_combo)

        # 3. Gateway interval
        self.lbl_gw = QLabel("معدل فحص الراوتر:")
        self.gw_interval_spin = QDoubleSpinBox()
        self.gw_interval_spin.setRange(0.5, 30.0)
        self.gw_interval_spin.setValue(1.0)
        self.gw_interval_spin.setSuffix(" ثانية")
        self.form_layout.addRow(self.lbl_gw, self.gw_interval_spin)

        # 4. External interval
        self.lbl_ext = QLabel("معدل فحص الإنترنت العام:")
        self.ext_interval_spin = QDoubleSpinBox()
        self.ext_interval_spin.setRange(1.0, 60.0)
        self.ext_interval_spin.setValue(3.0)
        self.ext_interval_spin.setSuffix(" ثواني")
        self.form_layout.addRow(self.lbl_ext, self.ext_interval_spin)

        # 5. DNS interval
        self.lbl_dns = QLabel("معدل فحص خوادم DNS:")
        self.dns_interval_spin = QDoubleSpinBox()
        self.dns_interval_spin.setRange(1.0, 120.0)
        self.dns_interval_spin.setValue(5.0)
        self.dns_interval_spin.setSuffix(" ثواني")
        self.form_layout.addRow(self.lbl_dns, self.dns_interval_spin)

        # Save Button
        self.apply_btn = QPushButton(tr("set_save_btn"))
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: #ffffff;
                font-weight: 700;
                padding: 10px 20px;
                border-radius: 8px;
                border: 1px solid #388bfd;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #388bfd; }
        """)
        self.form_layout.addRow(QLabel(""), self.apply_btn)

        layout.addWidget(form_frame)
        layout.addStretch()

    def apply_language(self) -> None:
        self.title_lbl.setText(tr("set_banner_title"))
        self.desc_lbl.setText(tr("set_banner_desc"))
        self.lbl_lang.setText(tr("set_lang_label"))
        self.lbl_mode.setText(tr("set_mode_label"))
        self.apply_btn.setText(tr("set_save_btn"))
        if get_language() == "ar":
            self.lbl_gw.setText("معدل فحص الراوتر:")
            self.lbl_ext.setText("معدل فحص الإنترنت العام:")
            self.lbl_dns.setText("معدل فحص خوادم DNS:")
            self.gw_interval_spin.setSuffix(" ثانية")
            self.ext_interval_spin.setSuffix(" ثواني")
            self.dns_interval_spin.setSuffix(" ثواني")
        else:
            self.lbl_gw.setText("Gateway Probe Interval:")
            self.lbl_ext.setText("External Probe Interval:")
            self.lbl_dns.setText("DNS Probe Interval:")
            self.gw_interval_spin.setSuffix(" sec")
            self.ext_interval_spin.setSuffix(" sec")
            self.dns_interval_spin.setSuffix(" sec")
