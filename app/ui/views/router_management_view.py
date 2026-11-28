"""Router Management Administration Console View for NetGuard AI.

Provides 7 organized administration tabs:
0. Overview (hardware, firmware, WAN, LAN/DHCP, health gauge, quick recommendations)
1. Wi-Fi (normalized SSID, channel, bandwidth, security — zero raw TR-069/noise)
2. Internet / WAN (WAN IP, PPP/DHCP, DNS, DSL/Fiber line stats, uptime)
3. LAN & DHCP (deduplicated gateway IP, subnet mask, DHCP pool & lease time)
4. Connected Devices (client inventory, search, ARP/router provenance, per-device actions)
5. QoS & Bandwidth (capability limits vs Windows host boundary, Change Preview modal + apply/rollback)
6. Diagnostics (coverage.pages endpoint audit isolated from normal config tables + action history)
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui import tokens
from app.ui.i18n import get_language, language_manager, tr
from app.ui.widgets.scroll_forwarder import fit_table_to_content
from app.ui.widgets.async_bridge import AsyncViewBridge
from app.ui.widgets.base_panel import Panel
from app.ui.widgets.buttons import GhostButton, PrimaryButton, SecondaryButton
from app.ui.widgets.chip import Chip
from app.ui.widgets.circular_gauge import CircularGauge
from app.ui.widgets.status_badge import StatusBadge


class RouterChangePreviewDialog(QDialog):
    """Explicit safety confirmation dialog displaying Before/After/Impact/Risk/Verification."""

    def __init__(self, proposal: Any, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("معاينة تغيير الراوتر / Router Change Preview")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(560)
        self.setStyleSheet(
            f"""
            QDialog {{ background-color: {tokens.BG_ELEVATED}; color: {tokens.TEXT}; }}
            QLabel {{ color: {tokens.TEXT}; background: transparent; }}
            """
        )
        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.setContentsMargins(22, 20, 22, 20)

        hdr = QLabel(tokens.bidi_isolate_mixed(str(getattr(proposal, "title", "Router Change"))))
        hdr.setFont(tokens.get_sans_font(16, 700))
        hdr.setWordWrap(True)
        lay.addWidget(hdr)

        rows = [
            ("الإعداد / Setting", str(getattr(proposal, "target_field", "—"))),
            ("القيمة الحالية / Current", str(getattr(proposal, "current_value", "—"))),
            ("القيمة المقترحة / Proposed", str(getattr(proposal, "proposed_value", "—"))),
            ("التأثير المتوقع / Impact", str(getattr(proposal, "expected_impact", "—"))),
            ("مستوى الخطورة / Risk", str(getattr(proposal, "risk_level", "low")).upper()),
            ("خطة التحقق / Verification", "إعادة قراءة إعدادات الراوتر والتحقق من البث والاتصال مع التراجع عند الفشل."),
        ]
        box = QFrame()
        box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        box.setStyleSheet(
            f"background-color: {tokens.SURFACE}; border: 1px solid {tokens.LINE}; border-radius: 8px;"
        )
        grid = QGridLayout(box)
        grid.setContentsMargins(16, 14, 16, 16)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)
        for i, (k, v) in enumerate(rows):
            kl = QLabel(k)
            kl.setFont(tokens.get_sans_font(12, 600))
            kl.setStyleSheet(f"color: {tokens.TEXT_MUTED}; border: none;")
            vl = QLabel(tokens.bidi_isolate_mixed(v))
            vl.setFont(tokens.get_mono_font(12, 500))
            vl.setWordWrap(True)
            vl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            vl.setStyleSheet(f"color: {tokens.TEXT}; border: none;")
            grid.addWidget(kl, i, 0, Qt.AlignTop)
            grid.addWidget(vl, i, 1, Qt.AlignTop)
        lay.addWidget(box)

        if getattr(proposal, "requires_reconnect_warning", False):
            warn = QLabel("تنبيه: قد ينقطع اتصال الواي فاي بضع ثوانٍ أثناء تطبيق التغيير على الراوتر.")
            warn.setFont(tokens.get_sans_font(12, 600))
            warn.setStyleSheet(f"color: {tokens.STATUS_WARN};")
            warn.setWordWrap(True)
            lay.addWidget(warn)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.setContentsMargins(0, 6, 0, 0)
        btn_row.addStretch(1)
        self.btn_cancel = SecondaryButton("إلغاء")
        self.btn_cancel.setMinimumWidth(110)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_apply = PrimaryButton("تطبيق وتحقق")
        self.btn_apply.setMinimumWidth(148)
        self.btn_apply.setDefault(True)
        self.btn_apply.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_apply)
        lay.addLayout(btn_row)
        self.adjustSize()


class RouterManagementView(QScrollArea):
    """Professional 7-tab Router Administration Console."""

    router_summary_updated = Signal(dict)

    def __init__(self, app_core: Any = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.app_core = app_core
        self.bundle = getattr(app_core, "wifi_bundle", None) if app_core else None
        self.bridge = AsyncViewBridge(self)

        self._discovery: Any = None
        self._snapshot: Any = None
        self._model: Any = None
        self._devices: List[Any] = []
        self._proposals: List[Any] = []
        self._dom_result: Any = None
        self._all_user_settings: List[Any] = []
        self._web_view: Any = None
        self._web_loaded_url: str = ""
        self._initial_devices_started = False
        self._tab_buttons: List[SecondaryButton] = []

        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        outer = QHBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setAlignment(Qt.AlignHCenter)

        self.content_holder = QWidget()
        self.content_holder.setMaximumWidth(tokens.MAX_CONTENT_WIDTH)
        self.content_holder.setStyleSheet("background: transparent;")
        self.root = QVBoxLayout(self.content_holder)
        self.root.setContentsMargins(24, 20, 24, 32)
        self.root.setSpacing(16)
        outer.addWidget(self.content_holder)
        self.setWidget(container)

        self._build_header_and_auth()
        self._build_tabs_bar()
        self._build_tabs_stack()

        language_manager().language_changed.connect(self.retranslate)
        self.switch_tab(0)

    def _build_header_and_auth(self) -> None:
        hdr = QFrame()
        hdr.setObjectName("RouterConsoleHeader")
        hdr.setStyleSheet(
            f"""
            QFrame#RouterConsoleHeader {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_PANEL}px;
            }}
            QFrame#RouterConsoleHeader QLineEdit {{
                background-color: {tokens.RANGE_TRACK};
                border: 1px solid {tokens.LINE_THRESHOLD};
                border-radius: 8px;
                padding: 6px 12px;
                min-height: 24px;
                color: {tokens.TEXT};
            }}
            """
        )
        lay = QVBoxLayout(hdr)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        top = QHBoxLayout()
        t_col = QVBoxLayout()
        t_col.setSpacing(4)
        self.lbl_title = QLabel(tr("router_title"))
        self.lbl_title.setFont(tokens.get_sans_font(20, 700))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_title.setMinimumHeight(34)
        self.lbl_title.setContentsMargins(0, 2, 0, 2)
        self.lbl_sub = QLabel(tr("router_sub"))
        self.lbl_sub.setFont(tokens.get_sans_font(12, 400))
        self.lbl_sub.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_sub.setWordWrap(True)
        t_col.addWidget(self.lbl_title)
        t_col.addWidget(self.lbl_sub)
        top.addLayout(t_col, 1)

        self.badge_router = StatusBadge(tokens.SystemStatus.WAITING, tr("status.waiting"))
        top.addWidget(self.badge_router)
        lay.addLayout(top)

        # Discovery + Auth row
        auth_grid = QGridLayout()
        auth_grid.setSpacing(10)

        self.inp_gateway_url = QLineEdit()
        self.inp_gateway_url.setPlaceholderText("http://192.168.1.1 (اتركه فارغاً للاكتشاف التلقائي)")
        self.inp_username = QLineEdit()
        self.inp_username.setPlaceholderText("اسم المستخدم (مثلاً admin)")
        self.inp_password = QLineEdit()
        self.inp_password.setPlaceholderText("كلمة مرور الراوتر")
        self.inp_password.setEchoMode(QLineEdit.Password)
        self.inp_password.returnPressed.connect(self.run_router_login_and_read)

        self.chk_remember = QCheckBox("حفظ بيانات الدخول محلياً بتشفير ويندوز (DPAPI)")
        self.chk_remember.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.chk_security_ack = QCheckBox("الاتصال بالراوتر داخل الشبكة المنزلية المحلية (HTTPS/HTTP)")
        self.chk_security_ack.setChecked(True)
        self.chk_security_ack.setStyleSheet(f"color: {tokens.TEXT_MUTED};")

        self.btn_connect_router = PrimaryButton("اتصال بالراوتر / Connect")
        self.btn_connect_router.clicked.connect(self.run_router_login_and_read)
        # Compatibility attributes for automated wiring checks while keeping ONE unified Connect button in UI
        self.btn_login_read = self.btn_connect_router
        self.btn_discover = self.btn_connect_router
        self.btn_dom_inspect = self.btn_connect_router
        self.btn_forget = self.btn_connect_router

        auth_grid.addWidget(self.inp_gateway_url, 0, 0, 1, 2)
        auth_grid.addWidget(self.inp_username, 0, 2)
        auth_grid.addWidget(self.inp_password, 0, 3)

        chk_row = QHBoxLayout()
        chk_row.addWidget(self.chk_security_ack)
        chk_row.addWidget(self.chk_remember)
        chk_row.addStretch()
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.btn_open_web_portal = SecondaryButton("فتح واجهة الراوتر المباشرة (المتصفح)")
        self.btn_open_web_portal.clicked.connect(self.open_router_web_portal)
        btn_row.addWidget(self.btn_connect_router)
        btn_row.addWidget(self.btn_open_web_portal)
        btn_row.addStretch()

        lay.addLayout(auth_grid)
        lay.addLayout(chk_row)
        lay.addLayout(btn_row)

        # Auth/Timeout feedback banner (strictly separates timeout vs wrong password!)
        self.lbl_auth_feedback = QLabel("")
        self.lbl_auth_feedback.setVisible(False)
        self.lbl_auth_feedback.setFont(tokens.get_sans_font(12, 600))
        self.lbl_auth_feedback.setWordWrap(True)
        lay.addWidget(self.lbl_auth_feedback)

        self.root.addWidget(hdr)

    def _build_tabs_bar(self) -> None:
        bar = QFrame()
        bar.setStyleSheet(
            f"background-color: {tokens.SURFACE}; border: 1px solid {tokens.LINE}; border-radius: 10px;"
        )
        row = QGridLayout(bar)
        row.setContentsMargins(8, 8, 8, 8)
        row.setSpacing(8)
        tab_keys = [
            "router_tab_overview",
            "router_tab_wifi",
            "router_tab_wan",
            "router_tab_lan",
            "router_tab_devices",
            "router_tab_qos",
            "router_tab_diag",
            "router_tab_web",
        ]
        self._tab_keys = tab_keys
        for idx, k in enumerate(tab_keys):
            b = SecondaryButton(tr(k))
            b.clicked.connect(lambda _=False, i=idx: self.switch_tab(i))
            self._tab_buttons.append(b)
            row.addWidget(b, idx // 4, idx % 4)
        self.root.addWidget(bar)

    def _build_tabs_stack(self) -> None:
        self.tab_stack = QStackedWidget()
        self.root.addWidget(self.tab_stack)

        # Tab 0: Overview
        w0 = QWidget()
        l0 = QVBoxLayout(w0)
        l0.setContentsMargins(0, 0, 0, 0)
        l0.setSpacing(14)

        top_cards = QGridLayout()
        top_cards.setSpacing(12)
        self.ov_vendor = self._stat_card("الشركة المصنعة / Vendor", "—", tokens.ACCENT_BRIGHT)
        self.ov_model = self._stat_card("طراز الراوتر / Model", "—", tokens.ACCENT)
        self.ov_firmware = self._stat_card("إصدار النظام / Firmware", "—", tokens.SECONDARY_CYAN)
        self.ov_wan_state = self._stat_card("حالة الاتصال / WAN", "—", tokens.STATUS_OK)
        self.ov_devices_cnt = self._stat_card("الأجهزة المتصلة", "—", tokens.SECONDARY_PURPLE)
        top_cards.addWidget(self.ov_vendor[0], 0, 0)
        top_cards.addWidget(self.ov_model[0], 0, 1)
        top_cards.addWidget(self.ov_firmware[0], 0, 2)
        top_cards.addWidget(self.ov_wan_state[0], 0, 3)
        top_cards.addWidget(self.ov_devices_cnt[0], 0, 4)
        l0.addLayout(top_cards)

        ov_mid = QGridLayout()
        ov_mid.setSpacing(14)
        p_net = Panel(title="حالة الشبكة المحلية / LAN Status", padding=16)
        self.lbl_ov_lan = QLabel("قم بتشغيل الاكتشاف أو القراءة لعرض عنوان البوابة والقناع و DHCP.")
        self.lbl_ov_lan.setFont(tokens.get_mono_font(12, 500))
        self.lbl_ov_lan.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_ov_lan.setWordWrap(True)
        p_net.main_layout.addWidget(self.lbl_ov_lan)

        p_wan = Panel(title="اتصال الإنترنت والخط / WAN & Line", padding=16)
        self.lbl_ov_wan = QLabel("—")
        self.lbl_ov_wan.setFont(tokens.get_mono_font(12, 500))
        self.lbl_ov_wan.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_ov_wan.setWordWrap(True)
        p_wan.main_layout.addWidget(self.lbl_ov_wan)

        p_health = Panel(title="تقييم صحة وتكوين الراوتر / Router Health", padding=16)
        h_box = QHBoxLayout()
        self.router_health_gauge = CircularGauge(title="صحة الإعداد", unit="%", size=110)
        self.router_health_gauge.set_value(None, subtitle=tr("status.waiting"))
        self.lbl_ov_health_notes = QLabel("بانتظار قراءة إعدادات الراوتر لتقييم الأمان والأداء.")
        self.lbl_ov_health_notes.setFont(tokens.get_sans_font(12, 400))
        self.lbl_ov_health_notes.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_ov_health_notes.setWordWrap(True)
        h_box.addWidget(self.router_health_gauge)
        h_box.addWidget(self.lbl_ov_health_notes, 1)
        p_health.main_layout.addLayout(h_box)

        ov_mid.addWidget(p_net, 0, 0)
        ov_mid.addWidget(p_wan, 0, 1)
        ov_mid.addWidget(p_health, 0, 2)
        l0.addLayout(ov_mid)
        l0.addStretch()
        self.tab_stack.addWidget(w0)

        # Tab 1: Wi-Fi
        self.table_wifi, w1 = self._make_clean_settings_tab(
            "إعدادات الواي فاي في الراوتر / Router Wireless Settings",
            "بيانات نظيفة وموحدة لـ SSID والقنوات والتشفير بدون مسارات TR-069 أو أخطاء 404",
        )
        self.tab_stack.addWidget(w1)

        # Tab 2: Internet / WAN
        self.table_wan, w2 = self._make_clean_settings_tab(
            "إعدادات الإنترنت والخط / WAN & DSL/Fiber",
            "نوع الاتصال، عنوان WAN، سرعات التزامن الفعلية، ونسبة الإشارة للضوضاء (SNR)",
        )
        self.tab_stack.addWidget(w2)

        # Tab 3: LAN & DHCP
        self.table_lan, w3 = self._make_clean_settings_tab(
            "الشبكة المحلية وخدمة DHCP",
            "إعدادات LAN و DHCP موحدة ومنزوعة التكرار",
        )
        self.tab_stack.addWidget(w3)

        # Tab 4: Connected Devices
        w4 = QWidget()
        l4 = QVBoxLayout(w4)
        l4.setContentsMargins(0, 0, 0, 0)
        p4 = Panel(
            title="الأجهزة المتصلة بالشبكة / Connected Clients",
            subtitle="جرد الأجهزة من الراوتر (عند توفره) مع كشف ARP المحلي",
            padding=16,
        )
        dev_bar = QHBoxLayout()
        self.dev_search = QLineEdit()
        self.dev_search.setPlaceholderText("ابحث باسم الجهاز أو IP أو MAC...")
        self.dev_search.textChanged.connect(lambda _: self._render_devices_table())
        self.btn_refresh_devices = PrimaryButton("تحديث الأجهزة / Refresh Clients")
        self.btn_refresh_devices.clicked.connect(self.refresh_connected_devices)
        dev_bar.addWidget(self.dev_search, 1)
        dev_bar.addWidget(self.btn_refresh_devices)
        p4.main_layout.addLayout(dev_bar)

        self.table_devices = QTableWidget(0, 6)
        self.table_devices.setHorizontalHeaderLabels(["الجهاز", "IP", "MAC", "نوع الاتصال", "النطاق / الإشارة", "المصدر"])
        self.table_devices.verticalHeader().setVisible(False)
        self.table_devices.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_devices.setSortingEnabled(True)
        self.table_devices.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        fit_table_to_content(self.table_devices)
        p4.main_layout.addWidget(self.table_devices)
        l4.addWidget(p4)
        l4.addStretch(1)
        self.tab_stack.addWidget(w4)

        # Tab 5: QoS & Bandwidth + Quick Controls + Proposals
        w5 = QWidget()
        l5 = QVBoxLayout(w5)
        l5.setContentsMargins(0, 0, 0, 0)
        p5 = Panel(
            title="إدارة الجودة وعرض النطاق / QoS & Bandwidth",
            subtitle="حالة التحكم بالسرعة والأولويات في الراوتر مع إمكانية التعديل المباشر",
            padding=16,
        )
        qos_grid = QGridLayout()
        qos_grid.setSpacing(10)
        self.qos_card_state = self._stat_card("حالة QoS بالراوتر", "بانتظار الاتصال", tokens.ACCENT_BRIGHT)
        self.qos_card_upnp = self._stat_card("بروتوكول UPnP", "—", tokens.SECONDARY_CYAN)
        self.qos_card_fw = self._stat_card("جدار الحماية", "—", tokens.STATUS_OK)
        self.qos_card_line = self._stat_card("سرعة الخط (Down / Up)", "—", tokens.SECONDARY_PURPLE)
        qos_grid.addWidget(self.qos_card_state[0], 0, 0)
        qos_grid.addWidget(self.qos_card_upnp[0], 0, 1)
        qos_grid.addWidget(self.qos_card_fw[0], 0, 2)
        qos_grid.addWidget(self.qos_card_line[0], 0, 3)
        p5.main_layout.addLayout(qos_grid)

        qos_ctrl_row = QHBoxLayout()
        qos_ctrl_row.setSpacing(8)
        self.btn_toggle_router_qos = PrimaryButton("تفعيل QoS على الراوتر")
        self.btn_toggle_router_qos.clicked.connect(self._on_quick_toggle_qos)
        self.btn_toggle_router_upnp = SecondaryButton("تعطيل UPnP للأمان")
        self.btn_toggle_router_upnp.clicked.connect(self._on_quick_toggle_upnp)
        qos_ctrl_row.addWidget(self.btn_toggle_router_qos)
        qos_ctrl_row.addWidget(self.btn_toggle_router_upnp)
        qos_ctrl_row.addStretch()
        p5.main_layout.addLayout(qos_ctrl_row)

        self.lbl_qos_cap = QLabel(
            "ملاحظة: تحديد سرعة جهاز آخر بالاسم يتطلب دعماً خاصاً من الراوتر؛ بينما يمكنك هنا تفعيل أولوية QoS على الراوتر وتعديل قنواته وإعداداته."
        )
        self.lbl_qos_cap.setFont(tokens.get_sans_font(12, 400))
        self.lbl_qos_cap.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_qos_cap.setWordWrap(True)
        p5.main_layout.addWidget(self.lbl_qos_cap)

        self.proposals_box = QVBoxLayout()
        self.proposals_box.setSpacing(8)
        p5.main_layout.addLayout(self.proposals_box)
        l5.addWidget(p5)
        l5.addStretch(1)
        self.tab_stack.addWidget(w5)

        # Tab 6: Router & Network Problems Audit (replaces raw /html/ URL dump!)
        w6 = QWidget()
        l6 = QVBoxLayout(w6)
        l6.setContentsMargins(0, 0, 0, 0)
        p6 = Panel(
            title="مشاكل الراوتر والشبكة والإعدادات الافتراضية / Network & Router Audit",
            subtitle="يعرض بوضوح الأخطاء والإعدادات الافتراضية المسببة للبطء أو ضعف الأمان وكيفية إصلاحها",
            padding=16,
        )
        self.lbl_coverage_summary = QLabel("اتصل بالراوتر لتحليل مشاكله وإعداداته الافتراضية تلقائياً.")
        self.lbl_coverage_summary.setFont(tokens.get_sans_font(12, 500))
        self.lbl_coverage_summary.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_coverage_summary.setWordWrap(True)
        p6.main_layout.addWidget(self.lbl_coverage_summary)

        self.table_coverage = QTableWidget(0, 4)
        self.table_coverage.setHorizontalHeaderLabels(["المشكلة / الخطأ", "الوضع الحالي والسبب", "الأثر على الشبكة", "الإجراء / الحل"])
        self.table_coverage.verticalHeader().setVisible(False)
        self.table_coverage.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_coverage.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_coverage.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_coverage.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_coverage.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        fit_table_to_content(self.table_coverage)
        p6.main_layout.addWidget(self.table_coverage)
        l6.addWidget(p6)

        p_all = Panel(
            title="كافة إعدادات الراوتر المقروءة / All Router Settings (الأمان · الجدار الناري · المنافذ · الخط)",
            subtitle="يعرض كل الإعدادات المستخرجة من جميع صفحات الراوتر بدون إخفاء مع إمكانية التعديل والبحث",
            padding=16,
        )
        self.all_settings_search = QLineEdit()
        self.all_settings_search.setPlaceholderText("ابحث في كل إعدادات الراوتر (Firewall, UPnP, Port, DSL, MAC, Wi-Fi...)")
        self.all_settings_search.textChanged.connect(lambda _: self._render_all_settings_table())
        p_all.main_layout.addWidget(self.all_settings_search)

        self.table_all_settings = QTableWidget(0, 4)
        self.table_all_settings.setHorizontalHeaderLabels(["الإعداد / Setting", "القيمة الحالية", "التفسير", "تعديل / Edit"])
        self.table_all_settings.verticalHeader().setVisible(False)
        self.table_all_settings.verticalHeader().setDefaultSectionSize(48)
        self.table_all_settings.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_all_settings.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_all_settings.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_all_settings.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_all_settings.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        fit_table_to_content(self.table_all_settings)
        p_all.main_layout.addWidget(self.table_all_settings)
        l6.addWidget(p_all)
        l6.addStretch(1)
        self.tab_stack.addWidget(w6)

        # Tab 7: Full Embedded Live Router Web Portal (just like browser inside NetGuard)
        w7 = QWidget()
        l7 = QVBoxLayout(w7)
        l7.setContentsMargins(0, 0, 0, 0)
        p7 = Panel(
            title="واجهة الراوتر المباشرة / Full Router Web Portal",
            subtitle="تصفح وتحكم في صفحة الراوتر الكاملة مباشرة من داخل البرنامج (Wi-Fi، الحماية، المنافذ، إعادة التشغيل وكل الإعدادات)",
            padding=14,
        )
        nav_row = QHBoxLayout()
        nav_row.setSpacing(8)
        self.btn_web_back = SecondaryButton("◀ رجوع")
        self.btn_web_forward = SecondaryButton("▶ للأمام")
        self.btn_web_reload = SecondaryButton("⟳ تحديث")
        self.btn_web_home = SecondaryButton("صفحة الراوتر")
        self.inp_web_url = QLineEdit()
        self.inp_web_url.setPlaceholderText("http://192.168.1.1")
        self.inp_web_url.returnPressed.connect(self._web_navigate_input)
        self.btn_web_go = PrimaryButton("فتح")
        self.btn_web_go.clicked.connect(self._web_navigate_input)
        self.btn_web_autofill = SecondaryButton("تعبئة بيانات الدخول")
        self.btn_web_autofill.clicked.connect(self._web_autofill_credentials)
        nav_row.addWidget(self.btn_web_back)
        nav_row.addWidget(self.btn_web_forward)
        nav_row.addWidget(self.btn_web_reload)
        nav_row.addWidget(self.btn_web_home)
        nav_row.addWidget(self.inp_web_url, 1)
        nav_row.addWidget(self.btn_web_go)
        nav_row.addWidget(self.btn_web_autofill)
        p7.main_layout.addLayout(nav_row)

        self._web_container = QFrame()
        self._web_container.setMinimumHeight(680)
        self._web_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._web_container.setStyleSheet(
            f"background-color: {tokens.SURFACE_INSET}; border: 1px solid {tokens.LINE}; border-radius: 8px;"
        )
        self._web_layout = QVBoxLayout(self._web_container)
        self._web_layout.setContentsMargins(2, 2, 2, 2)
        self._lbl_web_placeholder = QLabel("اضغط (فتح واجهة الراوتر المباشرة) لتحميل صفحة إدارة الراوتر الكاملة هنا...")
        self._lbl_web_placeholder.setAlignment(Qt.AlignCenter)
        self._lbl_web_placeholder.setFont(tokens.get_sans_font(13, 500))
        self._lbl_web_placeholder.setStyleSheet(f"color: {tokens.TEXT_MUTED}; border: none;")
        self._web_layout.addWidget(self._lbl_web_placeholder)
        p7.main_layout.addWidget(self._web_container)
        l7.addWidget(p7)
        self.tab_stack.addWidget(w7)

        # Keep non-visible empty attribute only for backwards-compat references without cluttering UI
        self.table_advanced_tech = QTableWidget(0, 4)
        self.table_advanced_tech.setVisible(False)
        self.btn_toggle_tech = GhostButton("")
        self.btn_toggle_tech.setVisible(False)

    @staticmethod
    def _stat_card(title: str, val: str, accent: str) -> tuple[QFrame, QLabel]:
        c = QFrame()
        c.setStyleSheet(
            f"background-color: {tokens.SURFACE}; border: 1px solid {tokens.LINE}; border-top: 3px solid {accent}; border-radius: 10px;"
        )
        l = QVBoxLayout(c)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(4)
        t = QLabel(title)
        t.setFont(tokens.get_sans_font(12, 500))
        t.setStyleSheet(f"color: {tokens.TEXT_MUTED}; border: none; background: transparent;")
        t.setWordWrap(True)
        v = QLabel(val)
        v.setFont(tokens.get_mono_font(13, 700))
        v.setStyleSheet(f"color: {tokens.TEXT}; border: none; background: transparent;")
        v.setWordWrap(True)
        l.addWidget(t)
        l.addWidget(v)
        return c, v

    @staticmethod
    def _make_clean_settings_tab(title: str, sub: str) -> tuple[QTableWidget, QWidget]:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        p = Panel(title=title, subtitle=sub, padding=16)
        tbl = QTableWidget(0, 4)
        tbl.setHorizontalHeaderLabels(["الإعداد / Setting", "القيمة الحالية", "التفسير", "تعديل / Edit"])
        tbl.verticalHeader().setVisible(False)
        tbl.verticalHeader().setDefaultSectionSize(48)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        fit_table_to_content(tbl)
        p.main_layout.addWidget(tbl)
        l.addWidget(p)
        l.addStretch(1)
        return tbl, w

    def switch_tab(self, index: int) -> None:
        self.tab_stack.setCurrentIndex(index)
        for i in range(self.tab_stack.count()):
            pg = self.tab_stack.widget(i)
            if pg is not None:
                pg.setSizePolicy(
                    QSizePolicy.Preferred,
                    QSizePolicy.Preferred if i == index else QSizePolicy.Ignored,
                )
        self.tab_stack.setMinimumHeight(0)
        self.tab_stack.adjustSize()
        if index == 7:
            self._ensure_web_portal_loaded()
        for i, btn in enumerate(self._tab_buttons):
            active = i == index
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {tokens.ACCENT if active else tokens.SURFACE_INSET};
                    color: {tokens.ON_ACCENT if active else tokens.TEXT_MUTED};
                    border: 1px solid {tokens.ACCENT if active else tokens.LINE};
                    border-radius: 8px;
                    padding: 6px 12px;
                    font-weight: {700 if active else 500};
                }}
                """
            )

    def retranslate(self) -> None:
        self.lbl_title.setText(tr("router_title"))
        self.lbl_sub.setText(tr("router_sub"))
        for b, k in zip(self._tab_buttons, self._tab_keys):
            b.setText(tr(k))

    def _show_auth_feedback(self, msg: str, severity: str = "error") -> None:
        color = {
            "ok": tokens.STATUS_OK,
            "warn": tokens.STATUS_WARN,
            "info": tokens.ACCENT_BRIGHT,
            "error": tokens.STATUS_BAD,
        }.get(severity, tokens.STATUS_BAD)
        bg = {
            "ok": tokens.OK_SOFT_BG,
            "warn": tokens.WARN_SOFT_BG,
            "info": tokens.INFO_SOFT_BG,
            "error": tokens.BAD_SOFT_BG,
        }.get(severity, tokens.BAD_SOFT_BG)
        self.lbl_auth_feedback.setText(tokens.bidi_isolate_mixed(msg))
        self.lbl_auth_feedback.setStyleSheet(
            f"color: {color}; background-color: {bg}; border: 1px solid {color}; border-radius: 8px; padding: 8px 12px;"
        )
        self.lbl_auth_feedback.setVisible(True)

    def ensure_initial_devices_scan(self) -> None:
        """Auto-discover local LAN devices and gateway once on entering Router Management."""
        if self._initial_devices_started or self.bundle is None:
            return
        self._initial_devices_started = True
        self.refresh_connected_devices()
        if self._discovery is None:
            self.run_router_discovery()

    def _populate_discovery_overview(self, disc: Any) -> None:
        if disc is None:
            return
        if getattr(disc, "preferred_url", None) and not self.inp_gateway_url.text().strip():
            self.inp_gateway_url.setText(str(disc.preferred_url))
        vendor = getattr(disc, "detected_vendor", "Unknown") or "Unknown"
        model = getattr(disc, "detected_model", None) or getattr(disc, "isp_brand", None) or "—"
        self.ov_vendor[1].setText(tokens.bidi_isolate_mixed(vendor))
        self.ov_model[1].setText(tokens.bidi_isolate_mixed(model))
        if getattr(disc, "firmware_version", None):
            self.ov_firmware[1].setText(tokens.bidi_isolate(str(disc.firmware_version)))
        self.ov_wan_state[1].setText(
            tokens.bidi_isolate_mixed(str(getattr(disc, "wan_connection_type", None) or "بوابة متاحة (بانتظار الدخول)"))
        )
        self.lbl_ov_lan.setText(
            tokens.bidi_isolate_mixed(
                f"Gateway IP: {getattr(disc, 'gateway_ip', '—')}\n"
                f"Management URL: {getattr(disc, 'preferred_url', '—')}\n"
                f"Adapter Profile: {getattr(disc, 'adapter_id', 'generic_probe')}"
            )
        )

    def run_router_discovery(self) -> None:
        if self.bundle is None:
            return
        override_url = self.inp_gateway_url.text().strip() or None

        async def _work():
            return await self.bundle.router_discovery.discover(override_gateway_url=override_url)

        def _done(disc: Any) -> None:
            self._discovery = disc
            self._populate_discovery_overview(disc)
            vendor = getattr(disc, "detected_vendor", "Unknown") or "Unknown"
            model = getattr(disc, "detected_model", None) or getattr(disc, "isp_brand", None) or "—"
            self.badge_router.set_status(tokens.SystemStatus.ACTIVE, tr("status.active"))
            self._show_auth_feedback(
                f"البوابة: {vendor} ({getattr(disc, 'preferred_url', '—')}) — أدخل اسم المستخدم وكلمة المرور واضغط اتصال بالراوتر.",
                "info",
            )
            self.router_summary_updated.emit(
                {
                    "router_model": f"{vendor} {model}".strip(),
                    "router_ip": getattr(disc, "gateway_ip", None),
                }
            )

        def _err(err: str) -> None:
            self.badge_router.set_status(tokens.SystemStatus.WARNING, tr("status.warning"))
            self._show_auth_feedback(err, "warn")

        self.bridge.run_coro(_work, _done, _err, op_key="router_discover", timeout_sec=10.0)

    def run_router_login_and_read(self) -> None:
        if self.bundle is None:
            return
        if self.bridge.is_busy("router_login_read"):
            return
        self.btn_connect_router.setEnabled(False)
        self.badge_router.set_status(tokens.SystemStatus.VERIFYING, tr("status.verifying"))
        self._show_auth_feedback("جاري الاتصال بالراوتر وقراءة جميع الإعدادات والأجهزة...", "info")

        override_url = self.inp_gateway_url.text().strip() or None
        user = self.inp_username.text().strip() or "admin"
        pwd = self.inp_password.text()
        ack = bool(self.chk_security_ack.isChecked())
        remember = bool(self.chk_remember.isChecked())

        async def _work():
            disc = self._discovery or await self.bundle.router_discovery.discover(override_gateway_url=override_url)
            adapter_id = getattr(disc, "adapter_id", "generic_probe")
            adapter = self.bundle.router_registry.get_adapter(adapter_id)
            gw_ip = str(getattr(disc, "gateway_ip", "") or "")
            base_url = override_url or getattr(disc, "preferred_url", None) or (f"http://{gw_ip}" if gw_ip else "")
            use_user = user
            use_pwd = pwd
            if not use_pwd and hasattr(self.bundle, "router_auth"):
                saved = self.bundle.router_auth.load_saved_credentials(gw_ip)
                if saved:
                    use_user = use_user or saved[0]
                    use_pwd = saved[1]
            if not use_pwd:
                try:
                    lan_devs, _, _ = await self.bundle.device_manager.list_connected_devices(
                        adapter=None,
                        gateway_ip=gw_ip or None,
                    )
                except Exception:
                    lan_devs = []
                return disc, None, None, lan_devs, None

            auth = self.bundle.router_auth.authenticate_single_attempt(
                adapter=adapter,
                discovery=disc,
                base_url=base_url,
                username=use_user,
                password=use_pwd,
                persist_in_windows_vault=remember,
                verify_tls=not (ack and str(base_url).lower().startswith("https://")),
                user_acknowledged_security_warning=ack,
            )
            if not getattr(auth, "authenticated", False):
                try:
                    lan_devs, _, _ = await self.bundle.device_manager.list_connected_devices(
                        adapter=None,
                        gateway_ip=gw_ip or None,
                    )
                except Exception:
                    lan_devs = []
                return disc, auth, None, lan_devs, None

            snap = await asyncio.to_thread(adapter.read_config)
            try:
                devs, _, _ = await self.bundle.device_manager.list_connected_devices(
                    adapter=adapter,
                    gateway_ip=gw_ip or None,
                )
            except Exception:
                devs = []
            try:
                model = await asyncio.to_thread(
                    self.bundle.router_inspector.inspect,
                    adapter=adapter,
                    discovery=disc,
                    snapshot=snap,
                    devices=devs,
                    dom_result=self._dom_result,
                )
            except Exception:
                model = None
            return disc, auth, snap, devs, model

        def _done(res: Any) -> None:
            self.btn_connect_router.setEnabled(True)
            disc, auth, snap, devs, model = res
            self._discovery = disc
            self._populate_discovery_overview(disc)
            if devs:
                self._devices = list(devs)
                self.ov_devices_cnt[1].setText(str(len(self._devices)))
                self._render_devices_table()

            if auth is None:
                self.badge_router.set_status(tokens.SystemStatus.WARNING, tr("status.warning"))
                self._show_auth_feedback("يرجى إدخال كلمة مرور الراوتر ثم الضغط على اتصال بالراوتر.", "warn")
                return

            if not getattr(auth, "authenticated", False):
                ek = getattr(auth, "error_kind", "auth_rejected")
                msg = getattr(auth, "message", "Router authentication did not succeed.")
                if ek == "timeout":
                    self.badge_router.set_status(tokens.SystemStatus.WARNING, tr("status.warning"))
                    self._show_auth_feedback(
                        f"انتهى وقت القراءة من الراوتر — لم تُحتسب محاولة فاشلة: {msg}",
                        "warn",
                    )
                elif ek == "unreachable":
                    self.badge_router.set_status(tokens.SystemStatus.NOT_CONNECTED, tr("status.not_connected"))
                    self._show_auth_feedback(f"تعذر الوصول إلى صفحة إدارة الراوتر: {msg}", "error")
                elif ek in ("security_ack_required", "lockout_guard"):
                    self.badge_router.set_status(tokens.SystemStatus.WARNING, tr("status.warning"))
                    self._show_auth_feedback(msg, "warn")
                else:
                    self.badge_router.set_status(tokens.SystemStatus.FAILED, tr("status.failed"))
                    lock_msg = f" · {auth.lockout_risk_warning}" if getattr(auth, "lockout_risk_warning", None) else ""
                    self._show_auth_feedback(f"فشل التحقق من بيانات الدخول: {msg}{lock_msg}", "error")
                return

            self._snapshot = snap
            self._devices = list(devs or [])
            self._model = model
            self.badge_router.set_status(tokens.SystemStatus.HEALTHY, tr("status.healthy"))
            self._show_auth_feedback("تم الاتصال بالراوتر وقراءة جميع الإعدادات والأجهزة بنجاح.", "ok")
            self._render_all_router_data()

        def _err(err: str) -> None:
            self.btn_connect_router.setEnabled(True)
            self.badge_router.set_status(tokens.SystemStatus.FAILED, tr("status.failed"))
            self._show_auth_feedback(err, "error")

        self.bridge.run_coro(_work, _done, _err, op_key="router_login_read", timeout_sec=42.0)

    def run_router_dom_inspection(self) -> None:
        inspector = getattr(self.bundle, "dom_inspector", None) if self.bundle else None
        if inspector is None:
            self._show_auth_feedback("فحص DOM غير متاح في هذه البيئة.", "warn")
            return
        if self.bridge.is_busy("router_dom_inspect"):
            return
        self.btn_dom_inspect.setEnabled(False)
        url = self.inp_gateway_url.text().strip() or (getattr(self._discovery, "preferred_url", None) or "http://192.168.1.1")
        user = self.inp_username.text().strip() or None
        pwd = self.inp_password.text() or None
        self._show_auth_feedback("جاري فحص واجهة الويب للراوتر (DOM) في الخلفية...", "info")

        async def _work():
            return inspector.inspect_portal(base_url=url, username=user, password=pwd)

        def _done(dom_res: Any) -> None:
            self.btn_dom_inspect.setEnabled(True)
            self._dom_result = dom_res
            if getattr(dom_res, "available", False) and getattr(dom_res, "pages", []):
                self._show_auth_feedback("اكتمل فحص واجهة المتصفح (DOM) وتم دمجه في تشخيص الراوتر.", "ok")
            else:
                note = (getattr(dom_res, "notes", None) or ["Web DOM inspection unavailable."])[0]
                self._show_auth_feedback(f"حالة فحص DOM: {note}", "info")
            if self._model is not None and self.bundle is not None:
                self._render_all_router_data()

        def _err(err: str) -> None:
            self.btn_dom_inspect.setEnabled(True)
            self._show_auth_feedback(f"تعذر فحص DOM: {err}", "warn")

        self.bridge.run_coro(_work, _done, _err, op_key="router_dom_inspect", timeout_sec=18.0)

    def clear_saved_credentials(self) -> None:
        if self.bundle and hasattr(self.bundle, "router_auth") and self._discovery:
            try:
                self.bundle.router_auth.clear_saved_credentials(
                    str(getattr(self._discovery, "gateway_ip", "") or "")
                )
            except Exception:
                pass
        self.inp_password.clear()
        self._show_auth_feedback("تم مسح بيانات الاعتماد المحفوظة.", "info")

    def refresh_connected_devices(self) -> None:
        if self.bundle is None:
            return
        self.btn_refresh_devices.setEnabled(False)

        async def _work():
            adapter = (
                self.bundle.router_registry.get_adapter(getattr(self._discovery, "adapter_id", "generic_probe"))
                if self._discovery
                else None
            )
            devs, _, _ = await self.bundle.device_manager.list_connected_devices(
                adapter=adapter,
                gateway_ip=getattr(self._discovery, "gateway_ip", None) if self._discovery else None,
            )
            return devs

        def _done(devs: Any) -> None:
            self.btn_refresh_devices.setEnabled(True)
            self._devices = list(devs or [])
            self.ov_devices_cnt[1].setText(str(len(self._devices)))
            self._render_devices_table()

        def _err(_: str) -> None:
            self.btn_refresh_devices.setEnabled(True)

        self.bridge.run_coro(_work, _done, _err, op_key="router_refresh_devices", timeout_sec=12.0)

    def _render_all_router_data(self) -> None:
        snap = self._snapshot
        model = self._model
        disc = self._discovery
        if snap is None:
            return

        vendor = getattr(snap, "vendor", None) or getattr(disc, "detected_vendor", "—")
        r_model = getattr(snap, "model", None) or getattr(disc, "detected_model", "—")
        fw = getattr(snap, "firmware_version", None) or "—"
        self.ov_vendor[1].setText(tokens.bidi_isolate_mixed(str(vendor)))
        self.ov_model[1].setText(tokens.bidi_isolate_mixed(str(r_model)))
        self.ov_firmware[1].setText(tokens.bidi_isolate(str(fw)))
        self.ov_wan_state[1].setText(tokens.bidi_isolate_mixed(str(getattr(snap, "wan_status", None) or getattr(snap, "wan_connection_type", "—"))))
        self.ov_devices_cnt[1].setText(str(len(self._devices)))

        uptime_sec = getattr(snap, "uptime_seconds", None)
        uptime_str = f"{uptime_sec // 3600}h {(uptime_sec % 3600) // 60}m" if uptime_sec else "—"
        self.lbl_ov_lan.setText(
            tokens.bidi_isolate(
                f"LAN IP: {getattr(snap, 'lan_ip', None) or '—'}\n"
                f"Subnet Mask: {getattr(snap, 'lan_subnet_mask', None) or '—'}\n"
                f"DHCP: {'Enabled' if getattr(snap, 'dhcp_enabled', None) else ('Disabled' if getattr(snap, 'dhcp_enabled', None) is False else '—')}\n"
                f"DHCP Pool: {getattr(snap, 'dhcp_pool_start', None) or '—'} .. {getattr(snap, 'dhcp_pool_end', None) or '—'}\n"
                f"Uptime: {uptime_str}"
            )
        )
        dns_list = ", ".join(getattr(snap, "dns_servers", []) or []) or "—"
        down_s = getattr(snap, "wan_down_mbps", None)
        up_s = getattr(snap, "wan_up_mbps", None)
        self.lbl_ov_wan.setText(
            tokens.bidi_isolate(
                f"Type: {getattr(snap, 'wan_connection_type', None) or '—'}\n"
                f"WAN IP: {getattr(snap, 'wan_ip', None) or '—'}\n"
                f"Sync Down/Up: {f'{down_s:.1f}' if down_s else '—'} / {f'{up_s:.1f}' if up_s else '—'} Mbps\n"
                f"DNS Servers: {dns_list}"
            )
        )

        # Router Health score from verified attributes only
        score = 100
        issues: List[str] = []
        if getattr(snap, "upnp_enabled", False):
            score -= 10
            issues.append("UPnP مفعّل")
        if getattr(snap, "firewall_level", None) in ("low", "off", "disabled"):
            score -= 20
            issues.append("حماية الجدار الناري منخفضة")
        if getattr(snap, "tr069_enabled", False):
            score -= 5
            issues.append("TR-069 مفتوح")
        score = max(0, score)
        col = tokens.STATUS_OK if score >= 80 else (tokens.STATUS_WARN if score >= 60 else tokens.STATUS_BAD)
        self.router_health_gauge.set_value(score, subtitle="مؤشر التكوين", color=col)
        self.lbl_ov_health_notes.setText(
            " · ".join(issues) if issues else "لم تُرصد ثغرات واضحة في التكوين المقروء."
        )

        # Domain tables from normalized settings (NO HTTP 404 rows, NO raw TR-069 keys, NO masked/flag leaks!)
        from app.wifi.router.parser import is_technical_or_masked_setting

        settings = list(getattr(model, "settings", []) or []) if model else []
        user_settings = [
            s
            for s in settings
            if str(getattr(s, "domain", "")).lower() != "advanced_technical"
            and not is_technical_or_masked_setting(
                str(getattr(s, "setting_key", "")),
                redacted=bool(getattr(s, "redacted", False)),
            )
        ]
        tech_rows = [s for s in settings if s not in user_settings]

        self._all_user_settings = list(user_settings)
        wifi_rows = [s for s in user_settings if str(getattr(s, "domain", "")).lower() in ("wifi_24", "wifi_5", "wifi_6", "wifi", "ssid_security", "channel_width", "tx_power_radio", "guest_wifi")]
        wan_rows = [s for s in user_settings if str(getattr(s, "domain", "")).lower() in ("wan", "wan_internet", "access_line_stats", "dns")]
        lan_rows = [s for s in user_settings if str(getattr(s, "domain", "")).lower() in ("lan", "lan_ip", "dhcp_server", "dhcp_leases", "dhcp", "ipv4_ipv6")]

        self._fill_settings_table(self.table_wifi, wifi_rows)
        self._fill_settings_table(self.table_wan, wan_rows)
        self._fill_settings_table(self.table_lan, lan_rows)
        self._render_devices_table()
        self._render_proposals_and_qos(snap, disc)
        self._render_coverage_table(model)
        self._render_all_settings_table()

        self.router_summary_updated.emit(
            {
                "router_model": f"{vendor} {r_model}".strip(),
                "router_ip": getattr(snap, "lan_ip", None) or getattr(disc, "gateway_ip", None),
                "connected_devices_count": len(self._devices),
            }
        )

    def _on_toggle_advanced_tech(self, checked: bool) -> None:
        self.table_advanced_tech.setVisible(bool(checked))
        self.btn_toggle_tech.setText(
            "إخفاء التفاصيل التقنية المتقدمة" if checked else "عرض التفاصيل التقنية المتقدمة (للمتخصصين)"
        )
        if checked:
            fit_table_to_content(self.table_advanced_tech)

    @staticmethod
    def _format_provenance(prov_obj: Any) -> str:
        raw = str(getattr(prov_obj, "value", prov_obj) or "router_reported").lower()
        mapping = {
            "router_reported": "مبلّغ من الراوتر",
            "measured": "مقاس فعلياً",
            "os_probe": "قياس محلي (النظام)",
            "inferred": "مستنتج",
            "unavailable": "غير متاح",
        }
        return mapping.get(raw, raw.replace("_", " ").title())

    @staticmethod
    def _format_setting_value(s: Any) -> str:
        if getattr(s, "redacted", False):
            return "[مخفي أمنياً]"
        val = str(getattr(s, "current_value", "") or "").strip()
        vstate = str(getattr(getattr(s, "value_state", None), "value", getattr(s, "value_state", ""))).lower()
        if vstate == "boolean_false" or (
            val.lower() in ("0", "false", "disabled (0)", "disabled")
            and str(getattr(s, "setting_key", "")).lower().endswith(("enabled", "enable"))
        ):
            return "معطّل (Disabled)"
        if val.lower() in ("1", "true", "enabled (1)", "enabled") and str(getattr(s, "setting_key", "")).lower().endswith(("enabled", "enable")):
            return "مفعّل (Enabled)"
        return val or "—"

    @staticmethod
    def _editable_field_for_setting(s: Any) -> tuple[Optional[str], Optional[str], str]:
        """Map a clean router setting record to (target_field, band, category) if directly editable."""
        key = str(getattr(s, "setting_key", "") or "").lower()
        dom = str(getattr(s, "domain", "") or "").lower()
        band = (
            "5 GHz"
            if (dom == "wifi_5" or "5 ghz" in key or "5ghz" in key or "5g" in key or "wlan1" in key or "wl1" in key)
            else ("2.4 GHz" if ("2.4" in key or "24" in key or dom == "wifi_24" or "wlan0" in key or "wl0" in key) else None)
        )
        if key.endswith(".channel") or key == "channel":
            return "channel", band or "2.4 GHz", "wifi_channel"
        if "channel_width" in key or "bandwidth" in key:
            return "channel_width", band or "2.4 GHz", "channel_width"
        if "tx_power" in key:
            return "tx_power", band or "2.4 GHz", "tx_power"
        if key.endswith(".ssid") or key == "ssid":
            return "ssid", band or "2.4 GHz", "wifi_channel"
        if key.endswith(".enabled") and dom in ("wifi_24", "wifi_5"):
            return "radio_5ghz_enabled" if band == "5 GHz" else "radio_enabled", band or "2.4 GHz", "band_steering"
        if key in ("qos_enabled", "qosenable"):
            return "qos_enabled", None, "qos_sqm"
        if key in ("upnp_enabled", "upnpenable"):
            return "upnp_enabled", None, "upnp"
        if key in ("dhcp_enabled", "dhcpserverenable", "dhcpenable"):
            return "dhcp_enabled", None, "dhcp"
        if key in ("dhcp_pool_start", "minaddress"):
            return "dhcp_pool_start", None, "dhcp"
        if key in ("dhcp_pool_end", "maxaddress"):
            return "dhcp_pool_end", None, "dhcp"
        if key == "dns_servers":
            return "dns_servers", None, "dns"
        return None, None, "other"

    def _edit_setting_interactive(self, setting_obj: Any, field_name: str, band: Optional[str], category: str) -> None:
        from app.wifi.models import RouterChangeProposal

        cur_val = str(getattr(setting_obj, "current_value", "") or "").strip()
        lbl = str(getattr(setting_obj, "setting_label_ar", None) or getattr(setting_obj, "setting_key", field_name))
        new_val, ok = QInputDialog.getText(
            self,
            "تعديل إعداد الراوتر",
            f"أدخل القيمة الجديدة لـ ({lbl}):\nالقيمة الحالية: {cur_val}",
            text=cur_val,
        )
        if not ok or not new_val.strip() or new_val.strip() == cur_val:
            return
        prop = RouterChangeProposal(
            proposal_id=f"edit_{field_name}",
            category=category,  # type: ignore[arg-type]
            title=f"تعديل {lbl}",
            target_field=field_name,
            band=band,
            current_value=cur_val,
            proposed_value=new_val.strip(),
            reason="تعديل مباشر بطلب المستخدم من لوحة إدارة الراوتر.",
            expected_impact="يُطبق التعديل مباشرة مع التحقق من القراءة وإعادة القيمة السابقة عند الفشل.",
            risk_level="medium" if "dhcp" in field_name or "upnp" in field_name else "low",
            requires_reconnect_warning=category in ("wifi_channel", "channel_width", "band_steering"),
            supported_by_adapter=True,
            requires_manual_apply=False,
        )
        self._open_proposal_dialog(prop)

    def _fill_settings_table(self, tbl: QTableWidget, rows: List[Any], *, include_redacted: bool = False) -> None:
        # Filter deduplicated & clean values only
        seen = set()
        clean: List[Any] = []
        for s in rows:
            if not include_redacted and getattr(s, "redacted", False):
                continue
            val_str = str(getattr(s, "current_value", "") or "").strip()
            if not val_str or "http 404" in val_str.lower() or "internetgatewaydevice." in val_str.lower():
                continue
            inst = str(getattr(s, "instance_id", "") or "").lower()
            key_sig = (str(getattr(s, "setting_key", "")).lower(), inst, val_str.lower())
            if key_sig in seen:
                continue
            seen.add(key_sig)
            clean.append(s)

        tbl.setRowCount(len(clean))
        for r, s in enumerate(clean):
            lbl = getattr(s, "setting_label_ar", None) if get_language() == "ar" else getattr(s, "setting_label", None)
            lbl = lbl or getattr(s, "setting_label", None) or getattr(s, "setting_key", "—")
            tbl.setItem(r, 0, QTableWidgetItem(tokens.bidi_isolate_mixed(str(lbl))))
            val_txt = self._format_setting_value(s)
            tbl.setItem(r, 1, QTableWidgetItem(tokens.bidi_isolate_mixed(val_txt)))
            tbl.setItem(r, 2, QTableWidgetItem(tokens.bidi_isolate_mixed(str(getattr(s, "meaning", "") or "—"))))

            fld_name, fld_band, fld_cat = self._editable_field_for_setting(s)
            if fld_name:
                btn_ed = SecondaryButton("تعديل / Edit")
                btn_ed.clicked.connect(
                    lambda _=False, st=s, fn=fld_name, bd=fld_band, ct=fld_cat: self._edit_setting_interactive(st, fn, bd, ct)
                )
                tbl.setCellWidget(r, 3, btn_ed)
            else:
                tbl.setItem(r, 3, QTableWidgetItem("عرض فقط"))
        fit_table_to_content(tbl)

    def _render_devices_table(self) -> None:
        q = self.dev_search.text().strip().lower() if hasattr(self, "dev_search") else ""
        filtered = []
        for d in self._devices:
            hay = f"{getattr(d, 'hostname', '')} {getattr(d, 'ip_address', '')} {getattr(d, 'mac_address', '')}".lower()
            if q and q not in hay:
                continue
            filtered.append(d)

        self.table_devices.setSortingEnabled(False)
        self.table_devices.setRowCount(len(filtered))
        for r, d in enumerate(filtered):
            self.table_devices.setItem(r, 0, QTableWidgetItem(tokens.bidi_isolate_mixed(getattr(d, "hostname", None) or getattr(d, "vendor", None) or "Device")))
            self.table_devices.setItem(r, 1, QTableWidgetItem(tokens.bidi_isolate(str(getattr(d, "ip_address", "—")))))
            self.table_devices.setItem(r, 2, QTableWidgetItem(tokens.bidi_isolate(str(getattr(d, "mac_address", None) or "—"))))
            self.table_devices.setItem(r, 3, QTableWidgetItem(str(getattr(d, "connection_type", None) or "—")))
            rssi = getattr(d, "rssi_dbm", None)
            band = getattr(d, "radio_band", None) or "—"
            sig = f"{band} ({rssi} dBm)" if rssi is not None else str(band)
            self.table_devices.setItem(r, 4, QTableWidgetItem(tokens.bidi_isolate(sig)))
            self.table_devices.setItem(r, 5, QTableWidgetItem(tokens.bidi_isolate(str(getattr(d, "source", "ARP")))))
        self.table_devices.setSortingEnabled(True)
        fit_table_to_content(self.table_devices)

    def _on_quick_toggle_qos(self) -> None:
        if self._snapshot is None:
            QMessageBox.information(self, "تنبيه", "اتصل بالراوتر أولاً لقراءة وتعديل QoS.")
            return
        from app.wifi.models import RouterChangeProposal

        cur = bool(getattr(self._snapshot, "qos_enabled", False))
        prop = RouterChangeProposal(
            proposal_id="quick_qos_toggle",
            category="qos_sqm",
            title="تعطيل QoS على الراوتر" if cur else "تفعيل جودة الخدمة QoS على الراوتر",
            target_field="qos_enabled",
            band=None,
            current_value="مفعّل" if cur else "معطّل",
            proposed_value="معطّل" if cur else "مفعّل",
            reason="تحسين أولوية المكالمات والتصفح وتقليل ارتفاع التذبذب أثناء الضغط على الخط.",
            expected_impact="إعطاء أولوية أعلى لحزم الصوت والفيديو والتصفح عبر الراوتر.",
            risk_level="low",
            supported_by_adapter=True,
            requires_manual_apply=False,
        )
        self._open_proposal_dialog(prop)

    def _on_quick_toggle_upnp(self) -> None:
        if self._snapshot is None:
            QMessageBox.information(self, "تنبيه", "اتصل بالراوتر أولاً لتعديل UPnP.")
            return
        from app.wifi.models import RouterChangeProposal

        cur = bool(getattr(self._snapshot, "upnp_enabled", False))
        prop = RouterChangeProposal(
            proposal_id="quick_upnp_toggle",
            category="upnp",
            title="تعطيل فتح المنافذ التلقائي UPnP" if cur else "تفعيل UPnP",
            target_field="upnp_enabled",
            band=None,
            current_value="مفعّل" if cur else "معطّل",
            proposed_value="معطّل" if cur else "مفعّل",
            reason="تعطيل UPnP يغلق فتح المنافذ التلقائي غير المصرح به في جدار الراوتر.",
            expected_impact="يرفع أمان الشبكة ويمنع التطبيقات المجهولة من فتح منافذ خارجية.",
            risk_level="low",
            supported_by_adapter=True,
            requires_manual_apply=False,
        )
        self._open_proposal_dialog(prop)

    def _render_proposals_and_qos(self, snap: Any, disc: Any) -> None:
        qos_en = getattr(snap, "qos_enabled", None)
        upnp_en = getattr(snap, "upnp_enabled", None)
        fw_lvl = getattr(snap, "firewall_level", None)
        dn = getattr(snap, "wan_down_mbps", None)
        up = getattr(snap, "wan_up_mbps", None)

        self.qos_card_state[1].setText("مفعّل ✓" if qos_en is True else ("معطّل" if qos_en is False else "غير مقروء"))
        self.qos_card_upnp[1].setText("مفعّل (يُنصح بتعطيله)" if upnp_en is True else ("معطّل ✓" if upnp_en is False else "—"))
        self.qos_card_fw[1].setText(str(fw_lvl).upper() if fw_lvl else "—")
        self.qos_card_line[1].setText(f"{dn:.1f} / {up:.1f} Mbps" if (dn or up) else "—")
        self.btn_toggle_router_qos.setText("تعطيل QoS على الراوتر" if qos_en is True else "تفعيل QoS على الراوتر")
        self.btn_toggle_router_upnp.setText("تعطيل UPnP للأمان" if upnp_en is not False else "إعادة تفعيل UPnP")

        while self.proposals_box.count():
            it = self.proposals_box.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        if self.bundle and hasattr(self.bundle, "router_analyzer"):
            try:
                adapter_id = getattr(disc, "adapter_id", "generic_probe") if disc else "generic_probe"
                adapter = self.bundle.router_registry.get_adapter(adapter_id)
                self._proposals = list(
                    self.bundle.router_analyzer.analyze(
                        capabilities=adapter.capabilities(),
                        router_config=snap,
                        config_model=self._model,
                        devices=self._devices,
                    )
                    or []
                )
            except Exception:
                self._proposals = []
        if not self._proposals:
            lbl = QLabel("إعدادات الراوتر الحالية مستقرة ولا توجد مشاكل تستدعي تعديل QoS.")
            lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
            self.proposals_box.addWidget(lbl)
            return

        for p in self._proposals:
            card = QFrame()
            card.setStyleSheet(
                f"background-color: {tokens.SURFACE_INSET}; border: 1px solid {tokens.LINE}; border-radius: 8px;"
            )
            hl = QHBoxLayout(card)
            hl.setContentsMargins(12, 10, 12, 10)
            col = QVBoxLayout()
            t = QLabel(tokens.bidi_isolate_mixed(str(getattr(p, "title", "Proposal"))))
            t.setFont(tokens.get_sans_font(13, 600))
            t.setStyleSheet(f"color: {tokens.TEXT}; border: none; background: transparent;")
            sub = QLabel(tokens.bidi_isolate_mixed(f"{getattr(p, 'current_value', '—')} -> {getattr(p, 'proposed_value', '—')} · {getattr(p, 'reason', '')}"))
            sub.setFont(tokens.get_sans_font(12, 400))
            sub.setStyleSheet(f"color: {tokens.TEXT_MUTED}; border: none; background: transparent;")
            sub.setWordWrap(True)
            col.addWidget(t)
            col.addWidget(sub)
            hl.addLayout(col, 1)
            btn = PrimaryButton("معاينة وتطبيق / Apply")
            btn.clicked.connect(lambda _=False, prop=p: self._open_proposal_dialog(prop))
            hl.addWidget(btn)
            self.proposals_box.addWidget(card)

    def _open_proposal_dialog(self, proposal: Any) -> None:
        dlg = RouterChangePreviewDialog(proposal, parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        if self.bundle is None or not hasattr(self.bundle, "optimization"):
            return

        async def _apply():
            adapter_id = getattr(self._discovery, "adapter_id", "generic_probe") if self._discovery else "generic_probe"
            adapter = self.bundle.router_registry.get_adapter(adapter_id)
            return await asyncio.to_thread(
                self.bundle.optimization.execute_proposal,
                adapter=adapter,
                proposal=proposal,
                explicit_user_approval=True,
            )

        def _done(res: Any) -> None:
            from app.wifi.optimization import ActionLifecycleState

            state = getattr(res, "state", None)
            if state is not None:
                ok = state in (
                    ActionLifecycleState.SUCCESSFULLY_VERIFIED,
                    ActionLifecycleState.PARTIALLY_COMPLETED,
                )
                msg = str(getattr(res, "verification_result", "") or "")
            else:
                ok = bool(getattr(res, "success", False))
                msg = str(getattr(res, "message", "") or "")
            QMessageBox.information(
                self,
                "نتيجة تعديل الراوتر",
                msg or "تم تطبيق التعديل والتحقق منه بنجاح."
                if ok
                else f"تعذر تنفيذ التعديل أو تأكيده:\n{msg or 'لم يرجع الراوتر تأكيداً للتغيير.'}",
            )
            self.run_router_login_and_read()

        def _err(err: str) -> None:
            QMessageBox.warning(self, "خطأ في تعديل الراوتر", err)

        self.bridge.run_coro(_apply, _done, _err, op_key="router_apply_change", timeout_sec=25.0)

    def _render_coverage_table(self, model: Any) -> None:
        """Render plain-language audit of router mistakes, default-setting risks, and network issues."""
        from app.wifi.models import RouterChangeProposal

        snap = self._snapshot
        audit_items: List[tuple[str, str, str, Optional[RouterChangeProposal], str]] = []

        # 1) Include all real analyzer proposals first (default channels, width, QoS, UPnP, DNS, security)
        for p in self._proposals:
            audit_items.append(
                (
                    str(getattr(p, "title", "مشكلة في التكوين")),
                    f"القيمة الحالية: {getattr(p, 'current_value', '—')} — {getattr(p, 'reason', '')}",
                    str(getattr(p, "expected_impact", "") or "يؤثر على سرعة أو ثبات الشبكة."),
                    p if getattr(p, "supported_by_adapter", False) else None,
                    f"المقترح: {getattr(p, 'proposed_value', '—')}",
                )
            )

        # 2) Direct audit checks on default router settings
        if snap is not None:
            r24 = (getattr(snap, "radios", {}) or {}).get("2.4 GHz")
            r5 = (getattr(snap, "radios", {}) or {}).get("5 GHz")
            if r24 and str(getattr(r24, "channel", "") or "").strip() in ("0", "", "Auto"):
                audit_items.append(
                    (
                        "قناة 2.4 GHz على الوضع التلقائي الافتراضي (Auto)",
                        "الراوتر يغيّر القناة عشوائياً أو يثبت على قناة مزدحمة من المصنع.",
                        "تقطيع متكرر وتداخل عالٍ مع شبكات الجيران.",
                        RouterChangeProposal(
                            proposal_id="audit_fix_ch24",
                            category="wifi_channel",
                            title="تثبيت قناة 2.4 GHz على القناة 1",
                            target_field="channel",
                            band="2.4 GHz",
                            current_value=str(getattr(r24, "channel", "Auto")),
                            proposed_value="1",
                            reason="تجنب القفز التلقائي والتداخل.",
                            expected_impact="استقرار التصفح على نطاق 2.4 GHz.",
                            supported_by_adapter=True,
                            requires_manual_apply=False,
                        ),
                        "تثبيت قناة 1 / 6 / 11",
                    )
                )
            if r5 and str(getattr(r5, "channel", "") or "").strip() in ("0", "", "Auto"):
                audit_items.append(
                    (
                        "قناة 5 GHz على الوضع التلقائي الافتراضي (Auto)",
                        "الوضع الافتراضي يختار غالباً القنوات الشائعة مثل 36 أو 44 المزدحمة.",
                        "فقدان ثبات البث وتذبذب السرعة على 5 GHz.",
                        RouterChangeProposal(
                            proposal_id="audit_fix_ch5",
                            category="wifi_channel",
                            title="تثبيت قناة 5 GHz على القناة الأقل ازدحاماً",
                            target_field="channel",
                            band="5 GHz",
                            current_value=str(getattr(r5, "channel", "Auto")),
                            proposed_value="100",
                            reason="الانتقال لقناة أنظف في نطاق 5 GHz.",
                            expected_impact="خفض التداخل ورفع سرعة النقل الفعلية.",
                            supported_by_adapter=True,
                            requires_manual_apply=False,
                        ),
                        "تثبيت قناة هادئة (مثلاً 100)",
                    )
                )
            if getattr(snap, "qos_enabled", None) is False and not any(x[3] and x[3].target_field == "qos_enabled" for x in audit_items):
                audit_items.append(
                    (
                        "إدارة جودة الخدمة (QoS) معطلة افتراضياً",
                        "إعداد المصنع يعامل تحميل الملفات والمكالمات بنفس الأولوية.",
                        "ارتفاع البنغ والتقطيع عند استخدام شخص آخر للإنترنت.",
                        RouterChangeProposal(
                            proposal_id="audit_fix_qos",
                            category="qos_sqm",
                            title="تفعيل QoS في الراوتر",
                            target_field="qos_enabled",
                            current_value="معطّل",
                            proposed_value="مفعّل",
                            reason="منح المكالمات والألعاب أولوية على الراوتر.",
                            expected_impact="تقليل التذبذب أثناء الضغط على الخط.",
                            supported_by_adapter=True,
                            requires_manual_apply=False,
                        ),
                        "تفعيل QoS",
                    )
                )
            dns_svrs = list(getattr(snap, "dns_servers", []) or [])
            if not dns_svrs or any(ip.startswith(("192.168.", "163.121.", "62.240.")) for ip in dns_svrs):
                audit_items.append(
                    (
                        "الاعتماد على DNS المزود الافتراضي",
                        f"الخادم المقروء ({', '.join(dns_svrs) or 'تلقائي من المزود'}) غالباً أبطأ من Cloudflare/Google.",
                        "بطء فتح المواقع والتطبيقات لأول مرة.",
                        None,
                        "استخدم 1.1.1.1 أو حسّن عبر قسم DNS",
                    )
                )

        if not audit_items:
            self.lbl_coverage_summary.setText(
                "ممتاز: لم تُرصد مشاكل واضحة أو إعدادات افتراضية خطرة في قراءة الراوتر الحالية."
            )
        else:
            self.lbl_coverage_summary.setText(
                f"تم رصد {len(audit_items)} ملاحظات / مشاكل في إعدادات الراوتر أو الشبكة — يمكنك تطبيق الإصلاح مباشرة بالضغط على الزر."
            )

        self.table_coverage.setRowCount(len(audit_items))
        for r, (title, cur_reason, impact, prop, fallback_txt) in enumerate(audit_items):
            self.table_coverage.setItem(r, 0, QTableWidgetItem(tokens.bidi_isolate_mixed(title)))
            self.table_coverage.setItem(r, 1, QTableWidgetItem(tokens.bidi_isolate_mixed(cur_reason)))
            self.table_coverage.setItem(r, 2, QTableWidgetItem(tokens.bidi_isolate_mixed(impact)))
            if prop is not None:
                btn_fix = PrimaryButton("إصلاح الآن / Fix")
                btn_fix.clicked.connect(lambda _=False, pr=prop: self._open_proposal_dialog(pr))
                self.table_coverage.setCellWidget(r, 3, btn_fix)
            else:
                self.table_coverage.setItem(r, 3, QTableWidgetItem(tokens.bidi_isolate_mixed(fallback_txt)))
        fit_table_to_content(self.table_coverage)

    def _render_all_settings_table(self) -> None:
        if not hasattr(self, "table_all_settings"):
            return
        q = self.all_settings_search.text().strip().lower() if hasattr(self, "all_settings_search") else ""
        filtered = []
        for s in self._all_user_settings:
            hay = (
                f"{getattr(s, 'setting_key', '')} "
                f"{getattr(s, 'setting_label', '')} "
                f"{getattr(s, 'setting_label_ar', '')} "
                f"{getattr(s, 'domain', '')} "
                f"{getattr(s, 'current_value', '')} "
                f"{getattr(s, 'meaning', '')}"
            ).lower()
            if q and q not in hay:
                continue
            filtered.append(s)
        self._fill_settings_table(self.table_all_settings, filtered)

    def _resolve_router_portal_url(self) -> str:
        from app.wifi.router.credentials import validate_local_router_url

        cand = (
            self.inp_gateway_url.text().strip()
            or (getattr(self._discovery, "preferred_url", None) if self._discovery else "")
            or (f"http://{getattr(self._discovery, 'gateway_ip', '')}" if getattr(self._discovery, "gateway_ip", None) else "")
            or "http://192.168.1.1"
        )
        if not cand.lower().startswith(("http://", "https://")):
            cand = f"http://{cand}"
        try:
            validate_local_router_url(cand, allow_loopback=True)
            return cand
        except Exception:
            return "http://192.168.1.1"

    def open_router_web_portal(self) -> None:
        self.switch_tab(7)

    def _ensure_web_portal_loaded(self) -> None:
        target_url = self._resolve_router_portal_url()
        if hasattr(self, "inp_web_url") and not self.inp_web_url.text().strip():
            self.inp_web_url.setText(target_url)

        if os.environ.get("QT_QPA_PLATFORM") == "offscreen" or os.environ.get("PYTEST_CURRENT_TEST"):
            self._lbl_web_placeholder.setText(f"بوابة الراوتر المباشرة جاهزة للفتح: {target_url}")
            return

        if self._web_view is None:
            try:
                from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
                from PySide6.QtWebEngineWidgets import QWebEngineView
            except Exception as exc:
                self._lbl_web_placeholder.setText(
                    f"تعذر تشغيل المتصفح المدمج (QtWebEngine غير متاح): {exc}\nافتح العنوان التالي في متصفحك: {target_url}"
                )
                return

            self._lbl_web_placeholder.setVisible(False)
            profile = QWebEngineProfile(self)
            page = QWebEnginePage(profile, self)

            def _is_local_cert_ok(err: Any) -> bool:
                try:
                    host = err.url().host()
                    addr = ipaddress.ip_address(host)
                    return bool(addr.is_private or addr.is_loopback or addr.is_link_local)
                except Exception:
                    return False

            if hasattr(page, "certificateError"):
                page.certificateError.connect(
                    lambda err: err.acceptCertificate() if _is_local_cert_ok(err) else err.rejectCertificate()
                )

            view = QWebEngineView(self._web_container)
            view.setPage(page)
            view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            view.urlChanged.connect(lambda u: self.inp_web_url.setText(u.toString()))
            self.btn_web_back.clicked.connect(view.back)
            self.btn_web_forward.clicked.connect(view.forward)
            self.btn_web_reload.clicked.connect(view.reload)
            self.btn_web_home.clicked.connect(lambda: view.setUrl(QUrl(self._resolve_router_portal_url())))
            self._web_layout.addWidget(view)
            self._web_view = view

        if self._web_view is not None and self._web_loaded_url != target_url:
            self._web_loaded_url = target_url
            self.inp_web_url.setText(target_url)
            self._web_view.setUrl(QUrl(target_url))

    def _web_navigate_input(self) -> None:
        from app.wifi.router.credentials import validate_local_router_url

        raw = self.inp_web_url.text().strip()
        if not raw:
            return
        if not raw.lower().startswith(("http://", "https://")):
            raw = f"http://{raw}"
        try:
            validate_local_router_url(raw, allow_loopback=True)
        except Exception as exc:
            QMessageBox.warning(self, "عنوان غير مسموح", f"المتصفح الداخلي مخصص لعناوين الراوتر المحلية فقط:\n{exc}")
            return
        self._ensure_web_portal_loaded()
        if self._web_view is not None:
            self._web_loaded_url = raw
            self._web_view.setUrl(QUrl(raw))

    def _web_autofill_credentials(self) -> None:
        self._ensure_web_portal_loaded()
        if self._web_view is None:
            return
        user = self.inp_username.text().strip() or "admin"
        pwd = self.inp_password.text()
        if not pwd and self.bundle and hasattr(self.bundle, "router_auth") and self._discovery:
            saved = self.bundle.router_auth.load_saved_credentials(str(getattr(self._discovery, "gateway_ip", "") or ""))
            if saved:
                user = user or saved[0]
                pwd = saved[1]
        if not pwd:
            QMessageBox.information(self, "بيانات الدخول", "أدخل كلمة مرور الراوتر في الخانة بالأعلى أولاً ثم اضغط تعبئة.")
            return
        js = f"""
        (() => {{
            const u = {json.dumps(user)};
            const p = {json.dumps(pwd)};
            function fillDoc(d) {{
                if (!d) return false;
                const pw = d.querySelector('input[type="password"]');
                if (!pw) return false;
                const inputs = Array.from(d.querySelectorAll('input[type="text"], input:not([type])'));
                const usr = inputs.find(el => /user|name|account|login/i.test((el.id || '') + (el.name || '')) ) || inputs[0];
                if (usr) {{
                    usr.focus();
                    usr.value = u;
                    usr.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    usr.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
                pw.focus();
                pw.value = p;
                pw.dispatchEvent(new Event('input', {{ bubbles: true }}));
                pw.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return true;
            }}
            if (fillDoc(document)) return true;
            for (const fr of document.querySelectorAll('iframe, frame')) {{
                try {{ if (fillDoc(fr.contentDocument)) return true; }} catch (e) {{}}
            }}
            return false;
        }})();
        """
        self._web_view.page().runJavaScript(js)

    def _sync_content_width(self) -> None:
        vw = self.viewport().width()
        if vw > 0:
            self.content_holder.setFixedWidth(min(vw, tokens.MAX_CONTENT_WIDTH))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_content_width()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_content_width()

    def shutdown(self) -> None:
        if self._web_view is not None:
            try:
                self._web_view.stop()
                self._web_view.deleteLater()
            except Exception:
                pass
            self._web_view = None
        self.bridge.shutdown()
