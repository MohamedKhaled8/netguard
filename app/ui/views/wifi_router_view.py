"""Integrated Wi-Fi, Network, Speed/Bufferbloat, Router, and Reporting UI section."""

from __future__ import annotations

import asyncio
import threading
import uuid
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QEvent, QObject, QSize, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui import tokens
from app.ui.widgets.base_panel import Panel
from app.ui.widgets.buttons import PrimaryButton, SecondaryButton
from app.ui.widgets.channel_spectrum_chart import ChannelSpectrumChart
from app.ui.widgets.chip import Chip
from app.ui.widgets.metric_cell import MetricCell
from app.ui.widgets.scroll_forwarder import fit_table_to_content, make_scroll_transparent
from app.wifi import WifiDiagnosticsBundle, build_wifi_bundle
from app.wifi.models import (
    AccessPointScanResult,
    BeforeAfterComparison,
    BeforeAfterSnapshot,
    BufferbloatDiagnosticsReport,
    ConnectedDeviceRecord,
    DnsDiagnosticsReport,
    FaultCategory,
    FullChannelAnalysisReport,
    MeasurementProvenance,
    NetworkDiagnosticsReport,
    RouterAuthResult,
    RouterChangeProposal,
    RouterConfigurationSnapshot,
    RouterDiscoveryResult,
    SpeedTestReport,
    UnifiedDiagnosticReport,
    WifiInterfaceTelemetry,
)
from app.wifi.optimization import (
    ActionHistoryEntry,
    ActionLifecycleState,
    OptimizationMode,
)
from app.wifi.qos_compatibility import QoSCompatibilityReport
from app.wifi.root_cause import DiagnosticFaultCard, RootCauseReport
from app.wifi.router.models_config import RouterConfigurationModel

PROVENANCE_LABELS_AR: Dict[MeasurementProvenance, str] = {
    MeasurementProvenance.MEASURED: "مُقاس فعلياً",
    MeasurementProvenance.INFERRED: "مستنتج من حزم الإشارة",
    MeasurementProvenance.ROUTER_REPORTED: "من الراوتر",
    MeasurementProvenance.UNAVAILABLE: "غير مدعوم / غير متاح",
}

FAULT_CATEGORY_AR: Dict[FaultCategory, str] = {
    FaultCategory.WIFI_SIGNAL_DISTANCE: "ضعف إشارة الواي فاي أو المسافة",
    FaultCategory.WIFI_CHANNEL_CONGESTION: "ازدحام قناة الواي فاي وتداخل التردد",
    FaultCategory.WRONG_BAND: "نطاق غير مثالي (الربط على تردد مزدحم)",
    FaultCategory.ROUTER_BUFFERBLOAT: "تضخم صفوف الانتظار Bufferbloat",
    FaultCategory.SLOW_DNS: "بطء أو تعثر خادم DNS",
    FaultCategory.LOCAL_BACKGROUND_UPLOAD: "حركة رفع أو تنزيل محلية منافسة",
    FaultCategory.ISP_UPSTREAM_ISSUE: "خلل في المسار الخارجي لمزود الخدمة ISP",
    FaultCategory.WINDOWS_OR_DRIVER: "انقطاعات أو أخطاء محول/تعريف ويندوز",
}

INTERFERENCE_LEVEL_AR: Dict[str, str] = {
    "low": "منخفض",
    "moderate": "متوسط",
    "high": "مرتفع",
    "severe": "حرج",
}

CONFIDENCE_AR: Dict[str, str] = {
    "high": "ثقة عالية",
    "medium": "ثقة متوسطة",
    "low": "ثقة محدودة",
}

SCOPE_AR: Dict[str, str] = {
    "local_quick": "إجراء سريع على الجهاز",
    "router_config": "إعدادات الراوتر",
    "isp_or_hardware": "العتاد أو مزود الخدمة",
}

SEVERITY_AR: Dict[str, str] = {
    "critical": "حرج",
    "high": "مرتفع",
    "medium": "متوسط",
    "low": "منخفض",
    "info": "معلومة",
}

VERDICT_AR: Dict[str, str] = {
    "improved": "تحسّن فعلي",
    "degraded": "تراجع",
    "inconclusive": "ضمن هامش التذبذب / غير حاسم",
    "unchanged": "دون تغير ملموس",
    "mixed": "نتيجة مختلطة",
    "unavailable": "غير متاح",
}

CONN_TYPE_AR: Dict[str, str] = {
    "wifi_24": "واي فاي 2.4 GHz",
    "wifi_5": "واي فاي 5 GHz",
    "wifi_6": "واي فاي 6",
    "ethernet": "سلكي Ethernet",
    "unknown": "غير محدد (ARP)",
}

BA_METRIC_AR: Dict[str, str] = {
    "RSSI Signal": "شدة إشارة الواي فاي (RSSI)",
    "Wi-Fi TX Link Rate": "معدل ربط الواي فاي (TX)",
    "Gateway Latency": "كمون البوابة المحلية",
    "Gateway Packet Loss": "فقد حزم البوابة",
    "Internet Latency": "كمون الإنترنت العام",
    "Configured DNS Median": "وسيط استجابة DNS",
    "Download Throughput": "سرعة التنزيل الفعلية",
    "Upload Throughput": "سرعة الرفع الفعلية",
    "Download Bufferbloat Delta": "زيادة الكمون تحت التنزيل",
    "Upload Bufferbloat Delta": "زيادة الكمون تحت الرفع",
    "Channel Congestion Score": "مؤشر ازدحام القناة",
}

REC_AR: Dict[str, tuple[str, str]] = {
    "r_signal_placement": (
        "تقريب الجهاز أو تقليل العوائق أو استخدام كابل شبكة",
        "يرفع قوة الإشارة ويستقر معدل الربط والكمون.",
    ),
    "r_prefer_5g": (
        "الاتصال بشبكة 5 GHz وتفضيلها في إعدادات المحول",
        "يقلل تداخل الشبكات المجاورة ويرفع السرعة الفعلية.",
    ),
    "r_switch_channel": (
        "تغيير قناة الواي فاي على الراوتر إلى القناة الأقل ازدحاماً",
        "يخفض التداخل المتبادل ويزيد ثبات المكالمات.",
    ),
    "r_bufferbloat_qos": (
        "إبقاء NetGuard QoS مفعّلاً وتفعيل SQM/QoS في الراوتر",
        "يمنع التنزيل والرفع الكثيف من خنق المكالمات.",
    ),
    "r_switch_dns": (
        "استخدام خادم DNS الأسرع خارج أوقات الاجتماعات",
        "يسرّع فتح النطاقات الجديدة عند الحاجة دون مساس بالمكالمات.",
    ),
    "r_pause_bg": (
        "إيقاف التنزيلات أو المزامنة السحابية الثقيلة مؤقتاً",
        "يفرغ خط الرفع فوراً ويخفض التذبذب.",
    ),
    "r_isp_line_check": (
        "فحص خط مزود الخدمة ISP مع إرفاق التقرير المتسلسل",
        "الراوتر المحلي سليم والخلل مرجّح من المسار الخارجي.",
    ),
    "r_driver_roam": (
        "مراجعة تعريف الواي فاي وتقليل حساسية التجوال",
        "يقلل الانقطاعات المفاجئة وتبديل البث غير الضروري.",
    ),
}


class _AsyncResultBridge(QObject):
    """Thread-safe signal bridge delivering background asyncio results to Qt main thread."""

    task_finished = Signal(str, object)
    task_failed = Signal(str, str)


def _bi(text: Any) -> str:
    return tokens.bidi_isolate(str(text))


def _bm(text: Any) -> str:
    return tokens.bidi_isolate_mixed(text)


def _wrap_cell_button(btn: QPushButton) -> QWidget:
    holder = QWidget()
    holder.setStyleSheet("background: transparent; border: 0px solid transparent;")
    lay = QHBoxLayout(holder)
    lay.setContentsMargins(6, 4, 6, 4)
    lay.setSpacing(0)
    lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.addWidget(btn)
    return holder


def _format_opt_num(value: Optional[float], unit: str = "", decimals: int = 1) -> str:
    if value is None:
        return "غير متاح"
    num_str = f"{value:.{decimals}f}" if isinstance(value, float) else str(value)
    if unit == "%":
        return _bi(f"{num_str}%")
    joined = f"{num_str} {unit}".strip() if unit else num_str
    return _bi(joined)


def _make_item(
    text: str,
    *,
    mono: bool = False,
    align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignRight,
) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setFont(tokens.get_mono_font(14) if mono else tokens.get_sans_font(14))
    item.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
    item.setToolTip(text)
    return item


def _apply_proportional_columns(table: QTableWidget, widths: Dict[int, int]) -> None:
    """Set explicit proportional base widths with Stretch on the wide description column."""
    hdr = table.horizontalHeader()
    hdr.setStretchLastSection(False)
    for col in range(table.columnCount()):
        if col in widths:
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            table.setColumnWidth(col, widths[col])
        else:
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
    table.setProperty("_prop_widths", dict(widths))
    table.setTextElideMode(Qt.TextElideMode.ElideNone)
    table.setWordWrap(True)


class _WeightedTableResizeFilter(QObject):
    """Keeps weighted table columns synced to exact table viewport width on every real resize."""

    def __init__(self, table: QTableWidget) -> None:
        super().__init__(table)
        self._table = table

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Resize and self._table.isVisible():
            vp = self._table.viewport()
            if vp is not None and vp.width() > 200:
                _sync_weighted_table_columns(self._table, vp.width())
                self._table.doItemsLayout()
                self._table.resizeRowsToContents()
                has_btn = any(
                    self._table.cellWidget(r, c) is not None
                    for r in range(self._table.rowCount())
                    for c in range(self._table.columnCount())
                )
                min_rh = 52 if has_btn else 42
                for r in range(self._table.rowCount()):
                    if self._table.rowHeight(r) < min_rh:
                        self._table.setRowHeight(r, min_rh)
                fit_table_to_content(self._table, max_rows_before_scroll=14)
        return super().eventFilter(watched, event)


def _apply_weighted_columns(
    table: QTableWidget,
    weights: List[float],
    *,
    min_widths: Optional[Dict[int, int]] = None,
    max_widths: Optional[Dict[int, int]] = None,
) -> None:
    """Distribute table width proportionally across all columns within configured min/max bounds."""
    hdr = table.horizontalHeader()
    hdr.setMinimumSectionSize(48)
    hdr.setStretchLastSection(False)
    for col in range(table.columnCount()):
        hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
    table.setProperty("_prop_weights", list(weights))
    table.setProperty("_prop_min_widths", dict(min_widths or {}))
    table.setProperty("_prop_max_widths", dict(max_widths or {}))
    table.setTextElideMode(Qt.TextElideMode.ElideNone)
    table.setWordWrap(True)
    if table.viewport() is not None and not table.property("_weighted_filter_installed"):
        table.viewport().installEventFilter(_WeightedTableResizeFilter(table))
        table.setProperty("_weighted_filter_installed", True)
    _sync_weighted_table_columns(table, max(740, table.viewport().width()))


def _sync_weighted_table_columns(table: QTableWidget, avail_width: int) -> None:
    weights = list(table.property("_prop_weights") or [])
    if not weights or len(weights) != table.columnCount():
        return
    mins: Dict[int, int] = {int(k): int(v) for k, v in (table.property("_prop_min_widths") or {}).items()}
    maxs: Dict[int, int] = {int(k): int(v) for k, v in (table.property("_prop_max_widths") or {}).items()}
    n = len(weights)
    w_avail = max(420, int(avail_width))
    min_sum = sum(mins.get(c, 60) for c in range(n))
    if min_sum >= w_avail:
        scale = w_avail / max(1, min_sum)
        widths = [max(48, int(mins.get(c, 60) * scale)) for c in range(n)]
    else:
        widths = [mins.get(c, 60) for c in range(n)]
        rem = w_avail - sum(widths)
        active = [c for c in range(n) if c not in maxs or widths[c] < maxs[c]]
        while rem > 0 and active:
            w_tot = sum(weights[c] for c in active) or float(len(active))
            progressed = False
            next_active: List[int] = []
            for c in active:
                share = int(rem * (weights[c] / w_tot))
                cap = maxs[c] - widths[c] if c in maxs else share
                add = min(share, cap) if c in maxs else share
                if add > 0:
                    widths[c] += add
                    progressed = True
                if c not in maxs or widths[c] < maxs[c]:
                    next_active.append(c)
            rem = w_avail - sum(widths)
            if not progressed:
                # Give leftover pixels to unconstrained columns
                unconstrained = [c for c in active if c not in maxs] or active
                for idx, c in enumerate(unconstrained):
                    if rem <= 0:
                        break
                    widths[c] += 1
                    rem -= 1
                break
            active = next_active
    diff = w_avail - sum(widths)
    if diff != 0:
        target_col = next((c for c in range(n - 1, -1, -1) if c not in maxs), n - 1)
        widths[target_col] = max(48, widths[target_col] + diff)
    for c, cw in enumerate(widths):
        table.setColumnWidth(c, cw)


def _style_table(table: QTableWidget, row_height: int = 44) -> None:
    table.setFont(tokens.get_sans_font(14))
    table.setAlternatingRowColors(False)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(row_height)
    table.horizontalHeader().setMinimumHeight(44)
    table.horizontalHeader().setStretchLastSection(True)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.setShowGrid(True)
    table.setStyleSheet(
        f"""
        QTableWidget {{
            background-color: {tokens.SURFACE_INSET};
            color: {tokens.TEXT};
            border: 1px solid {tokens.LINE};
            border-radius: 6px;
            gridline-color: {tokens.LINE};
        }}
        QTableWidget::item {{
            padding: 6px 8px;
        }}
        QHeaderView::section {{
            background-color: {tokens.SURFACE};
            color: {tokens.TEXT_SECONDARY};
            border: none;
            border-bottom: 1px solid {tokens.LINE};
            padding: 8px 8px;
            font-weight: 600;
        }}
        """
    )


class _SubTabButton(QPushButton):
    """Exclusive sub-navigation tab with crisp active accent state and zero stale focus ring."""

    def __init__(self, text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMinimumHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(tokens.get_sans_font(13, 600))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setToolTip(text)
        self.toggled.connect(self._apply_style)
        self._apply_style(False)

    def _apply_style(self, checked: bool) -> None:
        if checked:
            self.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {tokens.ACCENT};
                    color: {tokens.ON_ACCENT};
                    border: 1px solid {tokens.ACCENT};
                    border-radius: 8px;
                    padding: 6px 10px;
                    font-weight: 600;
                }}
                """
            )
        else:
            self.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {tokens.SURFACE_INSET};
                    color: {tokens.TEXT_SECONDARY};
                    border: 1px solid {tokens.LINE};
                    border-radius: 8px;
                    padding: 6px 10px;
                }}
                QPushButton:hover {{
                    background-color: {tokens.SURFACE_HOVER};
                    color: {tokens.TEXT};
                }}
                """
            )


class _AutoHeightStackedWidget(QStackedWidget):
    """QStackedWidget tracking only the current page height so short tabs never inherit taller tabs."""

    def sizeHint(self) -> QSize:
        cur = self.currentWidget()
        if cur is not None:
            return cur.sizeHint()
        return super().sizeHint()

    def minimumSizeHint(self) -> QSize:
        cur = self.currentWidget()
        if cur is not None:
            return cur.minimumSizeHint()
        return super().minimumSizeHint()


class _FaultCardWidget(QFrame):
    """Expandable 14-field Arabic diagnostic card for the central 'المشكلات والأخطاء' panel."""

    def __init__(
        self,
        card: DiagnosticFaultCard,
        on_execute: Optional[Callable[[DiagnosticFaultCard], None]] = None,
        on_toggle: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.card = card
        self._expanded = False

        sev_colors = {
            "CRITICAL": tokens.STATUS_BAD,
            "HIGH": tokens.STATUS_BAD,
            "MEDIUM": tokens.STATUS_WARN,
            "LOW": tokens.ACCENT,
            "INFORMATIONAL": tokens.TEXT_MUTED,
        }
        sev_ar = {
            "CRITICAL": "حرج",
            "HIGH": "مرتفع",
            "MEDIUM": "متوسط",
            "LOW": "منخفض",
            "INFORMATIONAL": "معلومة",
        }
        accent_c = sev_colors.get(card.severity, tokens.LINE)

        self.setObjectName("faultCard")
        self.setStyleSheet(
            f"#faultCard {{ background-color: {tokens.SURFACE_INSET}; border: 1px solid {tokens.LINE}; "
            f"border-right: 4px solid {accent_c}; border-radius: 8px; }}"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)

        hdr = QHBoxLayout()
        hdr.setSpacing(10)

        badge = QLabel(f"{sev_ar.get(card.severity, card.severity)} ({card.severity})")
        badge.setFont(tokens.get_sans_font(12, 600))
        badge.setStyleSheet(
            f"color: {accent_c}; background-color: {tokens.SURFACE}; border: 1px solid {accent_c}; "
            f"border-radius: 5px; padding: 3px 8px;"
        )
        badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        hdr.addWidget(badge)

        title_lbl = QLabel(_bm(card.issue_name))
        title_lbl.setFont(tokens.get_sans_font(14, 600))
        title_lbl.setStyleSheet(f"color: {tokens.TEXT}; background: transparent;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignVCenter)
        title_lbl.setWordWrap(True)
        hdr.addWidget(title_lbl, stretch=1)

        self._btn_toggle = SecondaryButton("عرض التفاصيل (14 حقلاً)")
        self._btn_toggle.setMinimumHeight(36)
        self._btn_toggle.clicked.connect(lambda: self._toggle_details(on_toggle))
        hdr.addWidget(self._btn_toggle)

        if card.can_netguard_execute and card.action_type in ("router_change", "local_dns", "local_qos") and on_execute is not None:
            btn_act = PrimaryButton("تنفيذ الحل بموافقة")
            btn_act.setMinimumHeight(36)
            btn_act.clicked.connect(lambda _c=False, crd=card: on_execute(crd))
            hdr.addWidget(btn_act)

        root.addLayout(hdr)

        quick = QLabel(
            _bm(f"المكان: {card.location}  |  الحالي: {card.current_setting}  |  الحل: {card.recommended_solution}")
        )
        quick.setFont(tokens.get_sans_font(12))
        quick.setStyleSheet(f"color: {tokens.TEXT_SECONDARY}; background: transparent;")
        quick.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignVCenter)
        quick.setWordWrap(True)
        root.addWidget(quick)

        if card.causal_chain is not None:
            chain_lbl = QLabel(_bm(f"سلسلة السببية: {card.causal_chain.chain_summary_ar}"))
            chain_lbl.setFont(tokens.get_sans_font(12))
            chain_lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED}; background: transparent;")
            chain_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignVCenter)
            chain_lbl.setWordWrap(True)
            root.addWidget(chain_lbl)

        self._details_widget = QWidget()
        self._details_widget.setVisible(False)
        dlay = QGridLayout(self._details_widget)
        dlay.setContentsMargins(0, 6, 0, 2)
        dlay.setSpacing(6)

        rows_14 = [
            ("1. اسم المشكلة", card.issue_name),
            ("2. مكان المشكلة", card.location),
            ("3. الإعداد الحالي", card.current_setting),
            ("4. القيمة/الحالة المتحققة", card.verified_value_or_state),
            ("5. سبب اعتبارها مشكلة", card.why_problem),
            ("6. الدليل والقياسات", " • ".join(e for e in card.evidence_and_measurements if e) or "—"),
            ("7. التأثير المتوقع", card.expected_impact),
            ("8. الأجهزة/التطبيقات المتأثرة", "، ".join(card.affected_devices_or_apps) or "—"),
            ("9. درجة الخطورة", f"{sev_ar.get(card.severity, card.severity)} ({card.severity})"),
            ("10. الحل المقترح", card.recommended_solution),
            ("11. هل يستطيع NetGuard التنفيذ؟", f"{'نعم' if card.can_netguard_execute else 'لا'} — {card.execution_capability_note}"),
            ("12. هل يحتاج موافقة المستخدم؟", "نعم" if card.requires_user_approval else "لا (تشخيصي/مرجعي)"),
            ("13. هل يمكن التراجع؟", "نعم (مدعوم)" if card.rollback_supported else "غير مدعوم / تعديل يدوي"),
            ("14. نتيجة التحقق بعد التنفيذ", card.post_execution_verification),
        ]
        for r_idx, (k_txt, v_txt) in enumerate(rows_14):
            kl = QLabel(_bm(k_txt))
            kl.setFont(tokens.get_sans_font(12, 600))
            kl.setStyleSheet(f"color: {tokens.TEXT_MUTED}; background: transparent;")
            kl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignTop)
            kl.setWordWrap(True)
            vl = QLabel(_bm(v_txt))
            vl.setFont(tokens.get_sans_font(12))
            vl.setStyleSheet(f"color: {tokens.TEXT}; background: transparent;")
            vl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignTop)
            vl.setWordWrap(True)
            dlay.addWidget(kl, r_idx, 0)
            dlay.addWidget(vl, r_idx, 1)
        dlay.setColumnStretch(0, 1)
        dlay.setColumnStretch(1, 3)
        root.addWidget(self._details_widget)

    def _toggle_details(self, on_toggle: Optional[Callable[[], None]]) -> None:
        self._expanded = not self._expanded
        self._details_widget.setVisible(self._expanded)
        self._btn_toggle.setText("إخفاء التفاصيل" if self._expanded else "عرض التفاصيل (14 حقلاً)")
        if on_toggle:
            QTimer.singleShot(0, on_toggle)


class WifiRouterView(QWidget):
    """Complete Wi-Fi RF, Sequential Network, DNS, Speed/Bufferbloat, Router, and Report section."""

    apply_local_dns_requested = Signal(str, str, str)

    def __init__(self, app_core: Any = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.app_core = app_core
        self.bundle: WifiDiagnosticsBundle = build_wifi_bundle(app_core)
        self._is_closing = False

        self._bridge = _AsyncResultBridge(self)
        self._bridge.task_finished.connect(self._on_task_finished)
        self._bridge.task_failed.connect(self._on_task_failed)
        self._active_threads: List[threading.Thread] = []
        self._task_callbacks: Dict[str, tuple[Callable[[Any], None], Optional[Callable[[str], None]]]] = {}

        # Live state cache
        self._telemetry: Optional[WifiInterfaceTelemetry] = None
        self._scan_result: Optional[AccessPointScanResult] = None
        self._channel_report: Optional[FullChannelAnalysisReport] = None
        self._network_report: Optional[NetworkDiagnosticsReport] = None
        self._dns_report: Optional[DnsDiagnosticsReport] = None
        self._speed_report: Optional[SpeedTestReport] = None
        self._bufferbloat_report: Optional[BufferbloatDiagnosticsReport] = None
        self._discovery: Optional[RouterDiscoveryResult] = None
        self._auth_result: Optional[RouterAuthResult] = None
        self._router_config: Optional[RouterConfigurationSnapshot] = None
        self._config_model: Optional[RouterConfigurationModel] = None
        self._router_proposals: List[RouterChangeProposal] = []
        self._connected_devices: List[ConnectedDeviceRecord] = []
        self._unified_report: Optional[UnifiedDiagnosticReport] = None
        self._root_cause: Optional[RootCauseReport] = None
        self._qos_compat: Optional[QoSCompatibilityReport] = None
        self._before_after: Optional[BeforeAfterComparison] = None
        self._snapshots: List[BeforeAfterSnapshot] = []
        self._active_session_secrets: List[str] = []
        self._sub_pages: List[QWidget] = []
        self._nl_quick_buttons: List[QPushButton] = []

        self._build_ui()
        self._load_saved_snapshots()
        self._refresh_nl_chips()
        self._refresh_action_history_table()

    # ------------------------------------------------------------------
    # Full-width Section Panel Builder & Clean Empty-State Helper
    # ------------------------------------------------------------------

    @staticmethod
    def _make_section_panel(
        title: str,
        subtitle: str = "",
        header_action: Optional[QWidget] = None,
    ) -> Panel:
        """Build a full-width header inside Panel without triggering Panel's 40%-width squeeze."""
        panel = Panel(padding=20)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)
        hdr.setSpacing(12)

        t_col = QVBoxLayout()
        t_col.setSpacing(4)
        lbl_t = QLabel(title)
        lbl_t.setFont(tokens.get_sans_font(15, 600))
        lbl_t.setStyleSheet(f"color: {tokens.TEXT}; background: transparent;")
        lbl_t.setWordWrap(True)
        t_col.addWidget(lbl_t)

        if subtitle:
            lbl_s = QLabel(subtitle)
            lbl_s.setFont(tokens.get_sans_font(12))
            lbl_s.setStyleSheet(f"color: {tokens.TEXT_MUTED}; background: transparent;")
            lbl_s.setWordWrap(True)
            t_col.addWidget(lbl_s)

        hdr.addLayout(t_col, stretch=1)
        if header_action is not None:
            hdr.addWidget(header_action)
        panel.main_layout.addLayout(hdr)
        return panel

    @staticmethod
    def _make_empty_placeholder(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(tokens.get_sans_font(13))
        lbl.setStyleSheet(
            f"color: {tokens.TEXT_MUTED}; background-color: {tokens.SURFACE_INSET}; "
            f"border: 1px dashed {tokens.LINE}; border-radius: 6px; padding: 14px;"
        )
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl

    def _toggle_table_visibility(
        self,
        table: QTableWidget,
        empty_lbl: Optional[QLabel],
        has_rows: bool,
        *,
        max_rows: int = 14,
    ) -> None:
        if empty_lbl is not None:
            empty_lbl.setVisible(not has_rows)
        table.setVisible(has_rows)
        if has_rows:
            if table.property("_prop_weights"):
                vp_w = table.viewport().width() if table.viewport() is not None else 0
                target_w = max(480, self.sub_stack.width() or (self._container.width() - 48) or 860)
                _sync_weighted_table_columns(table, vp_w if vp_w > 200 else max(420, target_w - 42))
            table.resizeRowsToContents()
            fit_table_to_content(table, max_rows_before_scroll=max_rows)
            table.updateGeometry()
        self._sync_sub_stack_height()
        QTimer.singleShot(0, self._sync_sub_stack_height)

    def _sync_sub_stack_height(self) -> None:
        page = self.sub_stack.currentWidget()
        if page is None:
            return
        target_w = max(480, self.sub_stack.width() or (self._container.width() - 48) or 860)
        table_avail_w = max(420, target_w - 46)
        for tbl in page.findChildren(QTableWidget):
            if tbl.isVisible():
                if tbl.property("_prop_weights"):
                    vp_w = tbl.viewport().width() if tbl.viewport() is not None else 0
                    use_w = vp_w if (vp_w > 200 and abs(vp_w - table_avail_w) <= 80) else min(vp_w, table_avail_w) if vp_w > 200 else table_avail_w
                    _sync_weighted_table_columns(tbl, use_w)
                else:
                    prop_w = tbl.property("_prop_widths") or {}
                    for c_idx, c_w in prop_w.items():
                        tbl.setColumnWidth(int(c_idx), int(c_w))
            if tbl.isVisible() and tbl.rowCount() > 0:
                tbl.resizeRowsToContents()
                has_btn = any(
                    tbl.cellWidget(r, c) is not None
                    for r in range(tbl.rowCount())
                    for c in range(tbl.columnCount())
                )
                min_rh = 52 if has_btn else 42
                for r in range(tbl.rowCount()):
                    if tbl.rowHeight(r) < min_rh:
                        tbl.setRowHeight(r, min_rh)
                fit_table_to_content(tbl, max_rows_before_scroll=14)
                tbl.updateGeometry()
        for pnl in page.findChildren(Panel):
            pnl_lay = pnl.layout()
            if pnl_lay is not None:
                pnl_lay.invalidate()
                pnl_lay.activate()
            pnl.updateGeometry()
        lay = page.layout()
        if lay is not None:
            lay.invalidate()
            lay.activate()
        if lay is not None and lay.hasHeightForWidth():
            h = lay.totalHeightForWidth(target_w)
        else:
            h = page.heightForWidth(target_w) if page.hasHeightForWidth() else -1
        if h <= 0:
            h = lay.sizeHint().height() if lay is not None else page.sizeHint().height()
        self.sub_stack.setFixedHeight(max(220, h + 10))
        self.sub_stack.updateGeometry()
        self._container.adjustSize()
        if self._layout is not None:
            self._layout.activate()

    # ------------------------------------------------------------------
    # Async execution & scrolling viewport safety
    # ------------------------------------------------------------------

    def _run_bg_coro(
        self,
        label: str,
        coro_factory: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        if getattr(self, "_is_closing", False):
            return
        task_id = f"{label}_{uuid.uuid4().hex[:8]}"
        self._task_callbacks[task_id] = (on_success, on_error)
        self._lbl_active_status.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self._lbl_active_status.setText(f"قيد التنفيذ الآن: {label}...")
        self._btn_cancel_op.setEnabled(True)

        def _worker() -> None:
            try:
                res = asyncio.run(coro_factory())
                if getattr(self, "_is_closing", False):
                    return
                try:
                    self._bridge.task_finished.emit(task_id, res)
                except RuntimeError:
                    pass
            except Exception as exc:
                if getattr(self, "_is_closing", False):
                    return
                try:
                    self._bridge.task_failed.emit(task_id, str(exc))
                except RuntimeError:
                    pass

        t = threading.Thread(target=_worker, daemon=True, name=f"ng-wifi-{label}")
        self._active_threads = [th for th in self._active_threads if th.is_alive()]
        self._active_threads.append(t)
        t.start()

    def _on_task_finished(self, task_id: str, result: Any) -> None:
        cbs = self._task_callbacks.pop(task_id, None)
        if getattr(self, "_is_closing", False):
            return
        self._lbl_active_status.setStyleSheet(f"color: {tokens.STATUS_OK};")
        self._lbl_active_status.setText("اكتمل الفحص بنجاح — القيم المعروضة مأخوذة مباشرة من قياسات النظام.")
        if cbs is None:
            return
        on_ok, _ = cbs
        on_ok(result)
        self._refresh_unified_overview_banner()

    def _on_task_failed(self, task_id: str, error_text: str) -> None:
        cbs = self._task_callbacks.pop(task_id, None)
        if getattr(self, "_is_closing", False):
            return
        first_line = next((ln.strip() for ln in str(error_text).splitlines() if ln.strip()), str(error_text))
        if len(first_line) > 160:
            first_line = first_line[:157] + "..."
        self._lbl_active_status.setStyleSheet(f"color: {tokens.STATUS_BAD};")
        self._lbl_active_status.setText(f"تعذر إكمال الفحص: {_bi(first_line)}")
        if cbs and cbs[1]:
            cbs[1](error_text)

    def shutdown(self) -> None:
        """Stop background workers, clear volatile credentials, and prevent late Qt UI emissions."""
        if getattr(self, "_is_closing", False):
            return
        self._is_closing = True
        self._task_callbacks.clear()
        try:
            self._bridge.blockSignals(True)
        except Exception:
            pass
        try:
            self.bundle.coordinator.cancel_active()
        except Exception:
            pass
        try:
            self.bundle.router_auth.clear_session_credentials()
        except Exception:
            pass
        self._active_session_secrets.clear()
        if hasattr(self, "_inp_router_pass"):
            self._inp_router_pass.clear()
        for sig, slot in (
            (self._bridge.task_finished, self._on_task_finished),
            (self._bridge.task_failed, self._on_task_failed),
        ):
            try:
                sig.disconnect(slot)
            except (RuntimeError, TypeError):
                pass

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.shutdown()
        super().closeEvent(event)

    def _sync_content_width(self) -> None:
        if hasattr(self, "_scroll") and hasattr(self, "_container"):
            vw = self._scroll.viewport().width()
            if vw > 0:
                self._container.setMinimumWidth(vw)
                self._container.setMaximumWidth(vw)
            if hasattr(self, "sub_stack"):
                self._sync_sub_stack_height()
                QTimer.singleShot(0, self._sync_sub_stack_height)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if (
            hasattr(self, "_scroll")
            and watched is self._scroll.viewport()
            and event.type() in (QEvent.Type.Resize, QEvent.Type.Show)
        ):
            self._sync_content_width()
        return super().eventFilter(watched, event)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._sync_content_width()
        if self._telemetry is None:
            self.refresh_wifi_and_rf()

    # ------------------------------------------------------------------
    # Top Shell & 8 Sub-Navigation Areas
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.viewport().installEventFilter(self)

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(24, 20, 24, 24)
        self._layout.setSpacing(14)

        # Page header
        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(12)
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        lbl_title = QLabel("إدارة الواي فاي والشبكة والراوتر")
        lbl_title.setFont(tokens.get_sans_font(22, 700))
        lbl_title.setStyleSheet(f"color: {tokens.TEXT};")
        lbl_sub = QLabel(
            f"تشخيص فعلي لرابط الواي فاي والترددات، المسار التسلسلي للإنترنت و {_bi('DNS')}، اختبار السرعة و {_bi('Bufferbloat')}، والاتصال المحلي بالراوتر."
        )
        lbl_sub.setFont(tokens.get_sans_font(13))
        lbl_sub.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        lbl_sub.setWordWrap(True)
        title_col.addWidget(lbl_title)
        title_col.addWidget(lbl_sub)
        hdr_row.addLayout(title_col, stretch=1)

        self._chip_meeting_guard = Chip("حماية الاجتماعات: غير نشط", "muted")
        self._chip_meeting_guard.setMinimumHeight(34)
        self._chip_meeting_guard.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        hdr_row.addWidget(self._chip_meeting_guard, alignment=Qt.AlignmentFlag.AlignTop)
        self._layout.addLayout(hdr_row)

        # Coordinator Status & 8 Exclusive Sub-Tabs Panel
        nav_panel = Panel(padding=16)
        nav_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        status_bar = QHBoxLayout()
        status_bar.setSpacing(10)
        self._lbl_active_status = QLabel("جاهز. جاري انتظار أول قراءة أو أمر تشغيل.")
        self._lbl_active_status.setFont(tokens.get_sans_font(13))
        self._lbl_active_status.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self._lbl_active_status.setWordWrap(True)
        status_bar.addWidget(self._lbl_active_status, stretch=1)

        self._btn_cancel_op = SecondaryButton("إلغاء العملية الجارية")
        self._btn_cancel_op.setMinimumHeight(36)
        self._btn_cancel_op.clicked.connect(self._handle_cancel_active)
        status_bar.addWidget(self._btn_cancel_op)
        nav_panel.main_layout.addLayout(status_bar)

        tab_grid = QGridLayout()
        tab_grid.setSpacing(8)
        tab_titles = [
            "1. نظرة عامة",
            f"2. الواي فاي و {_bi('RF')}",
            "3. تشخيص الإنترنت",
            f"4. تشخيص {_bi('DNS')}",
            f"5. السرعة و {_bi('Bufferbloat')}",
            "6. اتصال الراوتر",
            "7. الأجهزة المتصلة",
            "8. التوصيات والتقارير",
        ]
        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)
        self.sub_tab_buttons: List[_SubTabButton] = []
        for idx, t_label in enumerate(tab_titles):
            btn = _SubTabButton(t_label)
            self._tab_group.addButton(btn, idx)
            btn.clicked.connect(lambda _chk, i=idx: self.switch_subtab(i))
            self.sub_tab_buttons.append(btn)
            tab_grid.addWidget(btn, idx // 4, idx % 4)
        nav_panel.main_layout.addLayout(tab_grid)
        self._layout.addWidget(nav_panel)

        self.sub_stack = _AutoHeightStackedWidget()
        self.sub_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        builders = [
            self._build_tab_overview,
            self._build_tab_wifi_rf,
            self._build_tab_internet,
            self._build_tab_dns,
            self._build_tab_speed_bufferbloat,
            self._build_tab_router,
            self._build_tab_devices,
            self._build_tab_reports,
        ]
        for bfn in builders:
            page = bfn()
            self._sub_pages.append(page)
            self.sub_stack.addWidget(page)

        self._layout.addWidget(self.sub_stack)
        self._layout.addStretch(1)

        self._scroll.setWidget(self._container)
        root.addWidget(self._scroll)

        self.switch_subtab(0)

    def switch_subtab(self, index: int) -> None:
        self.sub_stack.setCurrentIndex(index)
        for i, page in enumerate(self._sub_pages):
            if i == index:
                page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            else:
                page.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        for i, b in enumerate(self.sub_tab_buttons):
            b.blockSignals(True)
            b.setChecked(i == index)
            b._apply_style(i == index)
            b.blockSignals(False)
        self._sync_sub_stack_height()
        self._scroll.verticalScrollBar().setValue(0)
        QTimer.singleShot(0, self._sync_sub_stack_height)

    def _handle_cancel_active(self) -> None:
        cancelled = self.bundle.coordinator.request_cancel("Cancelled by user from UI")
        if cancelled:
            self._lbl_active_status.setStyleSheet(f"color: {tokens.STATUS_WARN};")
            self._lbl_active_status.setText("تم إرسال طلب الإلغاء بأمان...")
        else:
            self._lbl_active_status.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
            self._lbl_active_status.setText("لا توجد عملية حصرية نشطة لإلغائها حالياً.")

    def _refresh_unified_overview_banner(self) -> None:
        m_active, m_reason = self.bundle.coordinator.is_meeting_active()
        if m_active:
            self._chip_meeting_guard.set_variant("tag-warn", "حماية الاجتماعات: نشط (مجمّد)")
            self._chip_meeting_guard.setToolTip(m_reason)
        else:
            self._chip_meeting_guard.set_variant("muted", "حماية الاجتماعات: غير نشط")
            self._chip_meeting_guard.setToolTip(m_reason)

    # ------------------------------------------------------------------
    # Tab 0: Network Overview
    # ------------------------------------------------------------------

    def _build_tab_overview(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        action_panel = self._make_section_panel(
            "ملخص صحة الشبكة والعمليات السريعة",
            "يعرض أحدث القيم المقاسة فعلياً فقط؛ القيم غير المدعومة من العتاد لا تُقدَّر عشوائياً.",
        )

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self._btn_ov_refresh_wifi = PrimaryButton("تحديث قياسات الواي فاي")
        self._btn_ov_refresh_wifi.setMinimumHeight(38)
        self._btn_ov_refresh_wifi.clicked.connect(self.refresh_wifi_and_rf)

        self._btn_ov_full_scan = PrimaryButton("فحص شامل لصحة الشبكة والراوتر")
        self._btn_ov_full_scan.setMinimumHeight(38)
        self._btn_ov_full_scan.clicked.connect(self.run_full_network_health_scan)

        self._btn_ov_run_seq = SecondaryButton("تشخيص الإنترنت المتسلسل")
        self._btn_ov_run_seq.setMinimumHeight(38)
        self._btn_ov_run_seq.clicked.connect(self.run_internet_sequence)

        self._btn_ov_save_snap = SecondaryButton("حفظ لقطة أساسية")
        self._btn_ov_save_snap.setMinimumHeight(38)
        self._btn_ov_save_snap.clicked.connect(lambda: self._capture_snapshot("قبل التغيير"))

        btn_row.addWidget(self._btn_ov_full_scan)
        btn_row.addWidget(self._btn_ov_refresh_wifi)
        btn_row.addWidget(self._btn_ov_run_seq)
        btn_row.addWidget(self._btn_ov_save_snap)
        btn_row.addStretch(1)
        action_panel.main_layout.addLayout(btn_row)

        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(10)
        self._cell_ov_conn = MetricCell("الشبكة المتصلة", "—", unit="")
        self._cell_ov_band = MetricCell("النطاق والقناة", "—", unit="")
        self._cell_ov_rssi = MetricCell(f"إشارة {_bi('RSSI')}", "—", unit="dBm")
        self._cell_ov_gw = MetricCell("متوسط البوابة", "—", unit="ms")
        self._cell_ov_inet = MetricCell("متوسط الإنترنت", "—", unit="ms")
        self._cell_ov_bloat = MetricCell(f"درجة {_bi('Bufferbloat')}", "—", unit="")

        for idx, c in enumerate(
            [
                self._cell_ov_conn,
                self._cell_ov_band,
                self._cell_ov_rssi,
                self._cell_ov_gw,
                self._cell_ov_inet,
                self._cell_ov_bloat,
            ]
        ):
            kpi_grid.addWidget(c, idx // 2, idx % 2)
        action_panel.main_layout.addLayout(kpi_grid)

        self._lbl_ov_summary = QLabel(
            "بانتظار إكمال أول قراءة للواي فاي والراديو لعرض ملخص التشخيص الموحد."
        )
        self._lbl_ov_summary.setFont(tokens.get_sans_font(13))
        self._lbl_ov_summary.setStyleSheet(
            f"color: {tokens.TEXT_SECONDARY}; background-color: {tokens.SURFACE_INSET}; "
            f"border: 1px solid {tokens.LINE}; border-radius: 6px; padding: 10px 12px;"
        )
        self._lbl_ov_summary.setWordWrap(True)
        action_panel.main_layout.addWidget(self._lbl_ov_summary)

        lay.addWidget(action_panel)

        # Natural Language Command Bar (Section 5)
        nl_panel = self._make_section_panel(
            "أوامر الشبكة الذكية (اللغة الطبيعية)",
            "اطرح سؤالاً أو اطلب فحصاً أو تغييراً موثقاً؛ يوجّهك النظام إلى التنفيذ الفعلي أو يوضح السبب والمحددات.",
        )
        nl_row = QHBoxLayout()
        nl_row.setSpacing(8)
        self._inp_nl_cmd = QLineEdit()
        self._inp_nl_cmd.setMinimumHeight(38)
        self._inp_nl_cmd.setFont(tokens.get_sans_font(13))
        self._inp_nl_cmd.setPlaceholderText("مثال: ما سبب بطء الإنترنت؟ أو افحص الراوتر بالكامل أو راجع القنوات")
        self._inp_nl_cmd.returnPressed.connect(self.run_nl_command)

        self._btn_nl_run = PrimaryButton("تنفيذ الأمر")
        self._btn_nl_run.setMinimumHeight(38)
        self._btn_nl_run.clicked.connect(self.run_nl_command)

        nl_row.addWidget(self._inp_nl_cmd, stretch=1)
        nl_row.addWidget(self._btn_nl_run)
        nl_panel.main_layout.addLayout(nl_row)

        self._nl_chips_host = QWidget()
        self._nl_chips_layout = QGridLayout(self._nl_chips_host)
        self._nl_chips_layout.setContentsMargins(0, 2, 0, 2)
        self._nl_chips_layout.setSpacing(6)
        nl_panel.main_layout.addWidget(self._nl_chips_host)

        self._lbl_nl_answer = QLabel("اكتب أمراً أو اختر أحد الاقتراحات المرتبطة بحالة شبكتك الحالية.")
        self._lbl_nl_answer.setFont(tokens.get_sans_font(13))
        self._lbl_nl_answer.setStyleSheet(
            f"color: {tokens.TEXT_SECONDARY}; background-color: {tokens.SURFACE_INSET}; "
            f"border: 1px solid {tokens.LINE}; border-radius: 6px; padding: 10px 12px;"
        )
        self._lbl_nl_answer.setWordWrap(True)
        nl_panel.main_layout.addWidget(self._lbl_nl_answer)
        lay.addWidget(nl_panel)

        # Central Dedicated Section: "المشكلات والأخطاء" (Sections 4 & 12)
        self._faults_panel = self._make_section_panel(
            "المشكلات والأخطاء",
            "تشخيص سببي موثق بالأدلة والقياسات الفعلية مع توضيح الـ 14 حقلاً وإمكانية التنفيذ والتراجع لكل خطأ.",
        )
        self._lbl_faults_summary = QLabel("شغّل الفحص لعرض المشكلات والأخطاء المصنفة حسب الخطورة.")
        self._lbl_faults_summary.setFont(tokens.get_sans_font(13, 600))
        self._lbl_faults_summary.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self._lbl_faults_summary.setWordWrap(True)
        self._faults_panel.main_layout.addWidget(self._lbl_faults_summary)

        self._faults_cards_host = QWidget()
        self._faults_cards_layout = QVBoxLayout(self._faults_cards_host)
        self._faults_cards_layout.setContentsMargins(0, 0, 0, 0)
        self._faults_cards_layout.setSpacing(10)
        self._faults_panel.main_layout.addWidget(self._faults_cards_host)

        self._tbl_app_impacts = QTableWidget(0, 4)
        self._tbl_app_impacts.setHorizontalHeaderLabels(
            ["التطبيق / النشاط", "الحالة المتوقعة", "الأسباب الجذرية", "التوجيه الموصى به"]
        )
        _style_table(self._tbl_app_impacts, row_height=46)
        _apply_weighted_columns(
            self._tbl_app_impacts,
            [0.24, 0.16, 0.28, 0.32],
            min_widths={0: 195, 1: 125, 2: 205, 3: 225},
        )
        make_scroll_transparent(self._tbl_app_impacts, self._scroll)
        self._tbl_app_impacts.setVisible(False)
        self._faults_panel.main_layout.addWidget(self._tbl_app_impacts)
        lay.addWidget(self._faults_panel)

        lay.addStretch(1)
        return w

    # ------------------------------------------------------------------
    # Tab 1: Wi-Fi & RF Analysis (All 16 metrics + AP scan + Chart + Scoring)
    # ------------------------------------------------------------------

    def _build_tab_wifi_rf(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        rf_btns_host = QWidget()
        rf_btns = QHBoxLayout(rf_btns_host)
        rf_btns.setContentsMargins(0, 0, 0, 0)
        rf_btns.setSpacing(8)
        self._btn_rf_refresh = PrimaryButton("تحديث قياسات الواي فاي وتحليل القنوات")
        self._btn_rf_refresh.setMinimumHeight(38)
        self._btn_rf_refresh.clicked.connect(self.refresh_wifi_and_rf)
        self._btn_rf_optimize_channel = SecondaryButton("تحسين القناة تلقائياً (بموافقة)")
        self._btn_rf_optimize_channel.setMinimumHeight(38)
        self._btn_rf_optimize_channel.clicked.connect(self._run_channel_optimization_workflow)
        rf_btns.addWidget(self._btn_rf_refresh)
        rf_btns.addWidget(self._btn_rf_optimize_channel)

        ctrl_panel = self._make_section_panel(
            "قياسات رابط الواي فاي ومعاملات الراديو الفعلية (16 مؤشراً)",
            "تُفرَّق المؤشرات بين ما هو مُقاس فعلياً من نظام التشغيل وما هو مستنتج من حزم البث أو غير مدعوم من التعريف.",
            header_action=rf_btns_host,
        )

        self._chk_active_scan = QCheckBox(
            f"طلب مسح {_bi('WlanScan')} نشط لتحديث قائمة القنوات (يُؤجَّل تلقائياً أثناء الاجتماعات)"
        )
        self._chk_active_scan.setMinimumHeight(36)
        self._chk_active_scan.setFont(tokens.get_sans_font(13))
        self._chk_active_scan.setStyleSheet(f"color: {tokens.TEXT};")
        ctrl_panel.main_layout.addWidget(self._chk_active_scan)

        self._empty_wifi_metrics = self._make_empty_placeholder(
            "جاري القراءة من محول الواي فاي في ويندوز أو اضغط زر التحديث أعلاه."
        )
        ctrl_panel.main_layout.addWidget(self._empty_wifi_metrics)

        self._tbl_wifi_metrics = QTableWidget(0, 4)
        self._tbl_wifi_metrics.setHorizontalHeaderLabels(
            ["المؤشر", "القيمة", "مصدر القياس", "ملاحظة التوثيق / السبب"]
        )
        _style_table(self._tbl_wifi_metrics, row_height=44)
        _apply_proportional_columns(self._tbl_wifi_metrics, {0: 195, 1: 275, 2: 155})
        make_scroll_transparent(self._tbl_wifi_metrics, self._scroll)
        self._tbl_wifi_metrics.setVisible(False)
        ctrl_panel.main_layout.addWidget(self._tbl_wifi_metrics)
        lay.addWidget(ctrl_panel)

        # Nearby AP Spectrum + Channel Analysis Scoring Engine
        band_box = QWidget()
        band_row = QHBoxLayout(band_box)
        band_row.setContentsMargins(0, 0, 0, 0)
        band_row.setSpacing(8)
        lbl_band = QLabel("النطاق:")
        lbl_band.setFont(tokens.get_sans_font(13))
        lbl_band.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self._combo_band = QComboBox()
        self._combo_band.setMinimumHeight(36)
        self._combo_band.setMinimumWidth(130)
        self._combo_band.setFont(tokens.get_mono_font(13))
        for b_val in ("2.4 GHz", "5 GHz", "6 GHz"):
            self._combo_band.addItem(_bi(b_val), b_val)
        self._combo_band.currentIndexChanged.connect(
            lambda _idx: self._render_channel_band_views(
                self._combo_band.currentData() or "2.4 GHz"
            )
        )
        band_row.addWidget(lbl_band)
        band_row.addWidget(self._combo_band)

        rf_panel = self._make_section_panel(
            "توزيع القنوات والشبكات المجاورة + محرك التقييم الترددي للقنوات",
            "يعتمد الترتيب على التداخل الفعلي للترددات ووزن شدة الإشارة وعرض القناة، وليس عدد الشبكات فقط.",
            header_action=band_box,
        )

        self._lbl_rf_notice = QLabel(
            f"ملاحظة علمية: درجة القناة تقدّر الازدحام الترددي من إشارات البث المرصودة، ولا تقيس الضوضاء غير اللاسلكية المخفية ما لم يعلن الراوتر {_bi('QBSS Load')}."
        )
        self._lbl_rf_notice.setFont(tokens.get_sans_font(12))
        self._lbl_rf_notice.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self._lbl_rf_notice.setWordWrap(True)
        rf_panel.main_layout.addWidget(self._lbl_rf_notice)

        self._spectrum_chart = ChannelSpectrumChart()
        rf_panel.main_layout.addWidget(self._spectrum_chart)

        self._empty_ch_scores = self._make_empty_placeholder(
            "ستظهر درجات تقييم القنوات القانونية وتوصيات القناة الأفضل هنا بعد المسح."
        )
        rf_panel.main_layout.addWidget(self._empty_ch_scores)

        self._tbl_ch_scores = QTableWidget(0, 8)
        self._tbl_ch_scores.setHorizontalHeaderLabels(
            [
                "القناة",
                "العرض",
                "الدرجة",
                "المستوى",
                "نفس القناة",
                "متجاور",
                "الثقة",
                "الشبكات المؤثرة والمحددات",
            ]
        )
        _style_table(self._tbl_ch_scores, row_height=44)
        _apply_proportional_columns(
            self._tbl_ch_scores,
            {0: 120, 1: 78, 2: 68, 3: 78, 4: 86, 5: 76, 6: 122},
        )
        make_scroll_transparent(self._tbl_ch_scores, self._scroll)
        self._tbl_ch_scores.setVisible(False)
        rf_panel.main_layout.addWidget(self._tbl_ch_scores)

        lbl_aps = QLabel("نقاط الوصول المجاورة المرصودة في النطاق المحدد:")
        lbl_aps.setFont(tokens.get_sans_font(13, 600))
        lbl_aps.setStyleSheet(f"color: {tokens.TEXT};")
        rf_panel.main_layout.addWidget(lbl_aps)

        self._empty_aps = self._make_empty_placeholder("لا توجد شبكات مجاورة معروضة بعد.")
        rf_panel.main_layout.addWidget(self._empty_aps)

        self._tbl_aps = QTableWidget(0, 7)
        self._tbl_aps.setHorizontalHeaderLabels(
            [_bi("SSID"), _bi("BSSID"), "النطاق", "القناة", "العرض", _bi("RSSI"), "الأمان / المعيار"]
        )
        _style_table(self._tbl_aps, row_height=40)
        _apply_proportional_columns(
            self._tbl_aps,
            {0: 155, 1: 210, 2: 76, 3: 56, 4: 86, 5: 105},
        )
        self._tbl_aps.setWordWrap(False)
        self._tbl_aps.setTextElideMode(Qt.TextElideMode.ElideRight)
        make_scroll_transparent(self._tbl_aps, self._scroll)
        self._tbl_aps.setVisible(False)
        rf_panel.main_layout.addWidget(self._tbl_aps)
        lay.addWidget(rf_panel)

        ev_panel = self._make_section_panel(
            f"سجل أحداث الاتصال والتجوال {_bi('WLAN-AutoConfig')}",
            "يعرض أحداث الارتباط والانفصال وتبديل نقاط الوصول داخل الجلسة وسجل ويندوز.",
        )
        self._empty_events = self._make_empty_placeholder("لا توجد أحداث واي فاي محمّلة بعد.")
        ev_panel.main_layout.addWidget(self._empty_events)

        self._tbl_wlan_events = QTableWidget(0, 5)
        self._tbl_wlan_events.setHorizontalHeaderLabels(
            ["الوقت", "النوع", _bi("Event ID"), f"{_bi('SSID')} / {_bi('BSSID')}", "التفاصيل"]
        )
        _style_table(self._tbl_wlan_events, row_height=40)
        make_scroll_transparent(self._tbl_wlan_events, self._scroll)
        self._tbl_wlan_events.setVisible(False)
        ev_panel.main_layout.addWidget(self._tbl_wlan_events)
        lay.addWidget(ev_panel)

        lay.addStretch(1)
        return w

    # ------------------------------------------------------------------
    # Tab 2: Sequential Internet Diagnostics
    # ------------------------------------------------------------------

    def _build_tab_internet(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        self._btn_net_diag = PrimaryButton("تشغيل التشخيص المتسلسل للإنترنت")
        self._btn_net_diag.setMinimumHeight(38)
        self._btn_net_diag.clicked.connect(self.run_internet_sequence)

        p = self._make_section_panel(
            "التشخيص التسلسلي للإنترنت والمسار",
            f"ينفذ بالترتيب بدون تزامن مع السرعة: ظروف الشبكة ← 30 حزمة بوابة ← 30 حزمة إنترنت ← فحص {_bi('IPv6')} ← تتبع 5 قفزات.",
            header_action=self._btn_net_diag,
        )

        self._lbl_net_cond = QLabel(
            f"اضغط زر التشغيل لفحص وجود {_bi('VPN')} أو بروكسي، تغير البوابة، أخطاء الواجهة، وحركة الخلفية ثم تنفيذ الحزم بالتسلسل."
        )
        self._lbl_net_cond.setFont(tokens.get_sans_font(13))
        self._lbl_net_cond.setStyleSheet(
            f"color: {tokens.TEXT_SECONDARY}; background-color: {tokens.SURFACE_INSET}; "
            f"border: 1px solid {tokens.LINE}; border-radius: 6px; padding: 10px 12px;"
        )
        self._lbl_net_cond.setWordWrap(True)
        p.main_layout.addWidget(self._lbl_net_cond)

        self._empty_net_pings = self._make_empty_placeholder(
            "لم يُنفَّذ قياس الحزم المتسلسل بعد."
        )
        p.main_layout.addWidget(self._empty_net_pings)

        self._tbl_net_pings = QTableWidget(0, 7)
        self._tbl_net_pings.setHorizontalHeaderLabels(
            ["الهدف", "الحالة", "المُستلَم", "الفقد", "المتوسط", "أدنى / أعلى", "التذبذب"]
        )
        _style_table(self._tbl_net_pings, row_height=42)
        _apply_proportional_columns(
            self._tbl_net_pings,
            {0: 215, 1: 135, 2: 85, 3: 75, 4: 95, 5: 135},
        )
        make_scroll_transparent(self._tbl_net_pings, self._scroll)
        self._tbl_net_pings.setVisible(False)
        p.main_layout.addWidget(self._tbl_net_pings)

        lbl_tr = QLabel(
            f"تتبع المسار التشخيصي (5 قفزات): عدم رد قفزة وسيطة وحدها قد يكون تقييد {_bi('ICMP')} على الموجه وليس دليل فقدان."
        )
        lbl_tr.setFont(tokens.get_sans_font(13))
        lbl_tr.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        lbl_tr.setWordWrap(True)
        p.main_layout.addWidget(lbl_tr)

        self._empty_trace = self._make_empty_placeholder("ستظهر القفزات الخمس هنا بعد اكتمال التشخيص المتسلسل.")
        p.main_layout.addWidget(self._empty_trace)

        self._tbl_trace = QTableWidget(0, 5)
        self._tbl_trace.setHorizontalHeaderLabels(
            ["القفزة", f"عنوان {_bi('IP')}", "متوسط الكمون", "الفقد", "التفسير"]
        )
        _style_table(self._tbl_trace, row_height=42)
        _apply_proportional_columns(
            self._tbl_trace,
            {0: 65, 1: 170, 2: 120, 3: 80},
        )
        make_scroll_transparent(self._tbl_trace, self._scroll)
        self._tbl_trace.setVisible(False)
        p.main_layout.addWidget(self._tbl_trace)

        lay.addWidget(p)
        lay.addStretch(1)
        return w

    # ------------------------------------------------------------------
    # Tab 3: DNS Diagnostics
    # ------------------------------------------------------------------

    def _build_tab_dns(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        self._btn_dns_diag = PrimaryButton(f"تشغيل مقارنة {_bi('DNS')}")
        self._btn_dns_diag.setMinimumHeight(38)
        self._btn_dns_diag.clicked.connect(self.run_dns_diagnostics)

        p = self._make_section_panel(
            f"قياس خوادم {_bi('DNS')} متعدد العينات",
            f"يقيس الخادم المضبوط، خادم الراوتر، {_bi('1.1.1.1')}، و {_bi('8.8.8.8')} باستعلامات {_bi('UDP')} مباشرة تتجاوز الكاش المحلي ودون تغيير إعداداتك تلقائياً.",
            header_action=self._btn_dns_diag,
        )

        self._lbl_dns_summary = QLabel(
            f"اضغط زر المقارنة لقياس زمن استجابة {_bi('DNS')} الفعلي وفصله عن زمن وصول الشبكة ({_bi('ICMP')})."
        )
        self._lbl_dns_summary.setFont(tokens.get_sans_font(13))
        self._lbl_dns_summary.setStyleSheet(
            f"color: {tokens.TEXT_SECONDARY}; background-color: {tokens.SURFACE_INSET}; "
            f"border: 1px solid {tokens.LINE}; border-radius: 6px; padding: 10px 12px;"
        )
        self._lbl_dns_summary.setWordWrap(True)
        p.main_layout.addWidget(self._lbl_dns_summary)

        self._empty_dns = self._make_empty_placeholder(f"لم تُنفَّذ مقارنة خوادم {_bi('DNS')} بعد.")
        p.main_layout.addWidget(self._empty_dns)

        self._tbl_dns = QTableWidget(0, 7)
        self._tbl_dns.setHorizontalHeaderLabels(
            [
                "الخادم",
                "الحالة",
                "العينات",
                "الوسيط",
                "أدنى / أعلى",
                f"التفاوت {_bi('Stdev')}",
                f"الشبكة / معالجة {_bi('DNS')}",
            ]
        )
        _style_table(self._tbl_dns, row_height=42)
        _apply_proportional_columns(
            self._tbl_dns,
            {0: 215, 1: 82, 2: 72, 3: 88, 4: 132, 5: 90},
        )
        make_scroll_transparent(self._tbl_dns, self._scroll)
        self._tbl_dns.setVisible(False)
        p.main_layout.addWidget(self._tbl_dns)

        lay.addWidget(p)
        lay.addStretch(1)
        return w

    # ------------------------------------------------------------------
    # Tab 4: Speed & Bufferbloat Testing
    # ------------------------------------------------------------------

    def _build_tab_speed_bufferbloat(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        self._btn_run_speed = PrimaryButton("تشغيل اختبار السرعة الفعلي")
        self._btn_run_speed.setMinimumHeight(38)
        self._btn_run_speed.clicked.connect(self.run_speed_test)

        sp_panel = self._make_section_panel(
            "اختبار السرعة الحقيقي والفصل بين معدل الرابط وسرعة الإنترنت",
            f"معدل ربط الواي فاي ({_bi('PHY')}) ليس سرعة الإنترنت؛ ويظل خيار الرفع تحت تحكمك لتوفير الباقة.",
            header_action=self._btn_run_speed,
        )

        self._chk_speed_upload = QCheckBox(f"تضمين قياس الرفع {_bi('Upload')} (يستهلك باقة إضافية)")
        self._chk_speed_upload.setMinimumHeight(36)
        self._chk_speed_upload.setFont(tokens.get_sans_font(13))
        self._chk_speed_upload.setStyleSheet(f"color: {tokens.TEXT};")
        sp_panel.main_layout.addWidget(self._chk_speed_upload)

        rate_grid = QGridLayout()
        rate_grid.setSpacing(10)
        self._cell_sp_phy = MetricCell(f"معدل ربط الواي فاي ({_bi('PHY')})", "—", unit="Mbps")
        self._cell_sp_lan = MetricCell(
            f"سرعة الشبكة المحلية ({_bi('LAN')})",
            "غير متاح",
            unit="",
            status_color=tokens.TEXT_MUTED,
        )
        self._cell_sp_dl = MetricCell("سرعة التنزيل الفعلية", "—", unit="Mbps")
        self._cell_sp_ul = MetricCell("سرعة الرفع الفعلية", "—", unit="Mbps")
        self._cell_sp_idle_ping = MetricCell("زمن الاستجابة بالخمول", "—", unit="ms")
        self._cell_sp_loaded_ping = MetricCell("الاستجابة تحت الحمل", "—", unit="ms")
        self._cell_sp_wan_sync = MetricCell(f"خط {_bi('WAN')} بالراوتر", "غير مقروء", unit="")
        rate_grid.addWidget(self._cell_sp_phy, 0, 0)
        rate_grid.addWidget(self._cell_sp_lan, 0, 1)
        rate_grid.addWidget(self._cell_sp_dl, 1, 0)
        rate_grid.addWidget(self._cell_sp_ul, 1, 1)
        rate_grid.addWidget(self._cell_sp_idle_ping, 2, 0)
        rate_grid.addWidget(self._cell_sp_loaded_ping, 2, 1)
        rate_grid.addWidget(self._cell_sp_wan_sync, 3, 0, 1, 2)
        sp_panel.main_layout.addLayout(rate_grid)

        self._lbl_speed_notes = QLabel(
            f"ملاحظة: قياس سرعة الشبكة المحلية {_bi('LAN')} يتطلب خادم {_bi('iperf3')} محلي ولا يُخمن من سرعة رابط الواي فاي."
        )
        self._lbl_speed_notes.setFont(tokens.get_sans_font(13))
        self._lbl_speed_notes.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self._lbl_speed_notes.setWordWrap(True)
        sp_panel.main_layout.addWidget(self._lbl_speed_notes)
        lay.addWidget(sp_panel)

        self._btn_run_bb = PrimaryButton(f"تشغيل اختبار {_bi('Bufferbloat')}")
        self._btn_run_bb.setMinimumHeight(38)
        self._btn_run_bb.clicked.connect(self.run_bufferbloat_test)

        bb_panel = self._make_section_panel(
            f"تشخيص {_bi('Bufferbloat')} المتسلسل تحت الحمل",
            "يقيس الكمون في الخمول ثم تحت حمل التنزيل ثم بعد فترة تفريغ ثم تحت حمل الرفع بشكل منفصل.",
            header_action=self._btn_run_bb,
        )

        self._chk_bb_combined = QCheckBox("تضمين مرحلة الحمل المزدوج (تنزيل + رفع معاً)")
        self._chk_bb_combined.setMinimumHeight(36)
        self._chk_bb_combined.setFont(tokens.get_sans_font(13))
        self._chk_bb_combined.setStyleSheet(f"color: {tokens.TEXT};")

        self._chk_bb_qos_compare = QCheckBox(
            f"مقارنة الخمول بدون {_bi('NetGuard QoS')} (تتطلب تأكيداً صريحاً وخارج الاجتماعات فقط)"
        )
        self._chk_bb_qos_compare.setMinimumHeight(36)
        self._chk_bb_qos_compare.setFont(tokens.get_sans_font(13))
        self._chk_bb_qos_compare.setStyleSheet(f"color: {tokens.TEXT};")

        bb_panel.main_layout.addWidget(self._chk_bb_combined)
        bb_panel.main_layout.addWidget(self._chk_bb_qos_compare)

        self._lbl_bb_summary = QLabel(f"لم يتم تشغيل اختبار {_bi('Bufferbloat')} بعد.")
        self._lbl_bb_summary.setFont(tokens.get_sans_font(13))
        self._lbl_bb_summary.setStyleSheet(
            f"color: {tokens.TEXT_SECONDARY}; background-color: {tokens.SURFACE_INSET}; "
            f"border: 1px solid {tokens.LINE}; border-radius: 6px; padding: 10px 12px;"
        )
        self._lbl_bb_summary.setWordWrap(True)
        bb_panel.main_layout.addWidget(self._lbl_bb_summary)

        self._empty_bb = self._make_empty_placeholder(f"ستظهر نتائج مراحل {_bi('Bufferbloat')} وتقييم كل مرحلة هنا.")
        bb_panel.main_layout.addWidget(self._empty_bb)

        self._tbl_bb_phases = QTableWidget(0, 7)
        self._tbl_bb_phases.setHorizontalHeaderLabels(
            ["المرحلة", "الكمون المتوسط", _bi("P95"), "الزيادة عن الخمول", "التذبذب", "الفقد", "التقييم"]
        )
        _style_table(self._tbl_bb_phases, row_height=42)
        _apply_proportional_columns(
            self._tbl_bb_phases,
            {0: 195, 1: 112, 2: 112, 3: 118, 4: 112, 5: 78},
        )
        make_scroll_transparent(self._tbl_bb_phases, self._scroll)
        self._tbl_bb_phases.setVisible(False)
        bb_panel.main_layout.addWidget(self._tbl_bb_phases)
        lay.addWidget(bb_panel)

        lay.addStretch(1)
        return w

    # ------------------------------------------------------------------
    # Tab 5: Router Connection & Configuration
    # ------------------------------------------------------------------

    def _build_tab_router(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        self._btn_router_discover = PrimaryButton("اكتشاف البوابة وبروتوكولات الراوتر")
        self._btn_router_discover.setMinimumHeight(38)
        self._btn_router_discover.clicked.connect(self.run_router_discovery)

        disc_panel = self._make_section_panel(
            "اكتشاف الراوتر المحلي والمحولات المتوافقة",
            "فحص سلبي آمن للبوابة المحلية فقط بدون تخمين كلمات مرور افتراضية.",
            header_action=self._btn_router_discover,
        )

        self._lbl_router_disc = QLabel(
            "اضغط زر الاكتشاف لقراءة البوابة، عنوان الماك، المنافذ المحلية المتاحة، ونوع المحول المقترح."
        )
        self._lbl_router_disc.setFont(tokens.get_sans_font(13))
        self._lbl_router_disc.setStyleSheet(
            f"color: {tokens.TEXT_SECONDARY}; background-color: {tokens.SURFACE_INSET}; "
            f"border: 1px solid {tokens.LINE}; border-radius: 6px; padding: 10px 12px;"
        )
        self._lbl_router_disc.setWordWrap(True)
        disc_panel.main_layout.addWidget(self._lbl_router_disc)
        lay.addWidget(disc_panel)

        auth_panel = self._make_section_panel(
            "تسجيل الدخول المحلي الآمن للراوتر",
            f"محاولة واحدة فقط في كل طلب لحماية حساب الراوتر من القفل، مع خيار التخزين المؤقت أو {_bi('Windows Credential Manager')}.",
        )
        form_grid = QGridLayout()
        form_grid.setSpacing(10)

        self._inp_router_url = QLineEdit()
        self._inp_router_url.setMinimumHeight(38)
        self._inp_router_url.setPlaceholderText("http://192.168.1.1")
        self._inp_router_url.setFont(tokens.get_mono_font(13))

        self._inp_router_user = QLineEdit("admin")
        self._inp_router_user.setMinimumHeight(38)
        self._inp_router_user.setFont(tokens.get_sans_font(13))

        self._inp_router_pass = QLineEdit()
        self._inp_router_pass.setMinimumHeight(38)
        self._inp_router_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._inp_router_pass.setPlaceholderText("كلمة مرور مسؤول الراوتر")
        self._inp_router_pass.setFont(tokens.get_sans_font(13))

        self._combo_cred_mode = QComboBox()
        self._combo_cred_mode.setMinimumHeight(38)
        self._combo_cred_mode.setFont(tokens.get_sans_font(13))
        self._combo_cred_mode.addItems(
            ["حفظ في الجلسة الحالية فقط (الذاكرة)", f"حفظ في {_bi('Windows Credential Manager')}"]
        )

        form_grid.addWidget(QLabel("عنوان الراوتر المحلي:"), 0, 0)
        form_grid.addWidget(self._inp_router_url, 0, 1)
        form_grid.addWidget(QLabel("اسم المستخدم:"), 1, 0)
        form_grid.addWidget(self._inp_router_user, 1, 1)
        form_grid.addWidget(QLabel("كلمة المرور:"), 2, 0)
        form_grid.addWidget(self._inp_router_pass, 2, 1)
        form_grid.addWidget(QLabel("تخزين الاعتماد:"), 3, 0)
        form_grid.addWidget(self._combo_cred_mode, 3, 1)
        auth_panel.main_layout.addLayout(form_grid)

        self._chk_ack_transport_sec = QCheckBox(
            f"أفهم تنبيه الأمان عند استخدام {_bi('HTTP')} غير المشفر أو شهادة محلية على الشبكة المنزلية"
        )
        self._chk_ack_transport_sec.setMinimumHeight(38)
        self._chk_ack_transport_sec.setFont(tokens.get_sans_font(13))
        self._chk_ack_transport_sec.setStyleSheet(f"color: {tokens.TEXT};")
        auth_panel.main_layout.addWidget(self._chk_ack_transport_sec)

        auth_btns = QHBoxLayout()
        auth_btns.setSpacing(10)
        self._btn_router_login = PrimaryButton("محاولة اتصال واحدة وقراءة الإعدادات")
        self._btn_router_login.setMinimumHeight(38)
        self._btn_router_login.clicked.connect(self.run_router_login_and_read)

        self._btn_router_dom_inspect = SecondaryButton(f"فحص {_bi('DOM')} بمتصفح داخلي")
        self._btn_router_dom_inspect.setMinimumHeight(38)
        self._btn_router_dom_inspect.clicked.connect(self.run_router_dom_inspection)

        self._btn_router_forget = SecondaryButton("مسح بيانات الاعتماد المحفوظة")
        self._btn_router_forget.setMinimumHeight(38)
        self._btn_router_forget.clicked.connect(self._clear_router_creds)

        auth_btns.addWidget(self._btn_router_login)
        auth_btns.addWidget(self._btn_router_dom_inspect)
        auth_btns.addWidget(self._btn_router_forget)
        auth_btns.addStretch(1)
        auth_panel.main_layout.addLayout(auth_btns)

        self._lbl_router_auth_status = QLabel("غير مسجل الدخول في لوحة الراوتر حالياً.")
        self._lbl_router_auth_status.setFont(tokens.get_sans_font(13))
        self._lbl_router_auth_status.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self._lbl_router_auth_status.setWordWrap(True)
        auth_panel.main_layout.addWidget(self._lbl_router_auth_status)
        lay.addWidget(auth_panel)

        cfg_panel = self._make_section_panel(
            "إعدادات الراوتر المقروءة والمقترحات الآمنة",
            "كل تعديل مدعوم يعرض نسخة احتياطية وتأكيداً صريحاً مع قراءة مرتدة والتراجع تلقائياً عند الفشل.",
        )

        self._empty_router_cfg = self._make_empty_placeholder("لم تُقرأ إعدادات الراوتر بعد (تتطلب اتصالاً مصادقاً).")
        cfg_panel.main_layout.addWidget(self._empty_router_cfg)

        self._tbl_router_config = QTableWidget(0, 3)
        self._tbl_router_config.setHorizontalHeaderLabels(["البند", "القيمة الحالية", "المصدر / الملاحظة"])
        _style_table(self._tbl_router_config, row_height=40)
        _apply_proportional_columns(self._tbl_router_config, {0: 185, 2: 140})
        make_scroll_transparent(self._tbl_router_config, self._scroll)
        self._tbl_router_config.setVisible(False)
        cfg_panel.main_layout.addWidget(self._tbl_router_config)

        self._empty_router_props = self._make_empty_placeholder("ستظهر التوصيات المرحلية للراوتر هنا بعد الفحص والاكتشاف.")
        cfg_panel.main_layout.addWidget(self._empty_router_props)

        self._tbl_router_proposals = QTableWidget(0, 6)
        self._tbl_router_proposals.setHorizontalHeaderLabels(
            ["المقترح", "الحالي", "المقترح الجديد", "المخاطرة / الانقطاع", "التطبيق التلقائي", "إجراء"]
        )
        _style_table(self._tbl_router_proposals, row_height=52)
        _apply_weighted_columns(
            self._tbl_router_proposals,
            [0.32, 0.10, 0.12, 0.22, 0.12, 0.12],
            min_widths={0: 175, 1: 84, 2: 96, 3: 170, 4: 108, 5: 118},
            max_widths={1: 145, 2: 170, 4: 155, 5: 145},
        )
        make_scroll_transparent(self._tbl_router_proposals, self._scroll)
        self._tbl_router_proposals.setVisible(False)
        cfg_panel.main_layout.addWidget(self._tbl_router_proposals)
        lay.addWidget(cfg_panel)

        # Router Operating Mode & 32-Domain Page Inspection Coverage Panel (Sections 2 & 15)
        cov_panel = self._make_section_panel(
            "وضع التشغيل الآلي وتقرير تغطية فحص الراوتر (32 مجالاً)",
            "يفصل بين الصفحات المفحوصة بالكامل والجزئية وغير المتاحة دون ادعاء تغطية وهمية، ويتحكم في أذونات التعديل الآلي.",
        )
        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)
        mode_lbl = QLabel("وضع التحسين:")
        mode_lbl.setFont(tokens.get_sans_font(13, 600))
        self._combo_opt_mode = QComboBox()
        self._combo_opt_mode.setMinimumHeight(38)
        self._combo_opt_mode.setFont(tokens.get_sans_font(12))
        self._combo_opt_mode.addItems([
            f"مراقبة وتشخيص فقط ({_bi('MONITOR AND DIAGNOSE')})",
            f"يتطلب موافقة لكل تعديل ({_bi('APPROVAL REQUIRED')})",
            f"تحسين تلقائي مفوض ({_bi('AUTHORIZED AUTO-OPTIMIZATION')})",
        ])
        self._combo_opt_mode.setCurrentIndex(1)
        self._combo_opt_mode.currentIndexChanged.connect(self._on_opt_mode_changed)

        self._chk_auto_ch = QCheckBox("السماح التلقائي لتغيير القناة")
        self._chk_auto_ch.setMinimumHeight(36)
        self._chk_auto_ch.setChecked(False)
        self._chk_auto_dns = QCheckBox(f"السماح التلقائي لتحديث {_bi('DNS')}")
        self._chk_auto_dns.setMinimumHeight(36)
        self._chk_auto_dns.setChecked(False)
        self._chk_auto_ch.toggled.connect(self._on_opt_mode_changed)
        self._chk_auto_dns.toggled.connect(self._on_opt_mode_changed)
        self._on_opt_mode_changed()

        mode_row.addWidget(mode_lbl)
        mode_row.addWidget(self._combo_opt_mode, stretch=1)
        mode_row.addWidget(self._chk_auto_ch)
        mode_row.addWidget(self._chk_auto_dns)
        cov_panel.main_layout.addLayout(mode_row)

        self._lbl_router_coverage = QLabel("لم يكتمل فحص صفحات الراوتر المصادق عليه بعد.")
        self._lbl_router_coverage.setFont(tokens.get_sans_font(13))
        self._lbl_router_coverage.setStyleSheet(
            f"color: {tokens.TEXT_SECONDARY}; background-color: {tokens.SURFACE_INSET}; "
            f"border: 1px solid {tokens.LINE}; border-radius: 6px; padding: 10px 12px;"
        )
        self._lbl_router_coverage.setWordWrap(True)
        cov_panel.main_layout.addWidget(self._lbl_router_coverage)

        self._empty_router_pages = self._make_empty_placeholder("ستظهر تفاصيل تغطية صفحات وأقسام الراوتر (FULLY INSPECTED / NOT ACCESSIBLE) هنا بعد الفحص.")
        cov_panel.main_layout.addWidget(self._empty_router_pages)

        self._tbl_router_pages = QTableWidget(0, 5)
        self._tbl_router_pages.setHorizontalHeaderLabels(
            ["الصفحة / القسم", "الوصول والاستخراج", "حالة التغطية", "إمكانية التغيير", "عدد الإعدادات / السبب"]
        )
        _style_table(self._tbl_router_pages, row_height=42)
        _apply_proportional_columns(self._tbl_router_pages, {0: 175, 1: 115, 2: 145, 3: 150})
        make_scroll_transparent(self._tbl_router_pages, self._scroll)
        self._tbl_router_pages.setVisible(False)
        cov_panel.main_layout.addWidget(self._tbl_router_pages)
        lay.addWidget(cov_panel)

        lay.addStretch(1)
        return w

    # ------------------------------------------------------------------
    # Tab 6: Connected Devices & Bandwidth Management
    # ------------------------------------------------------------------

    def _build_tab_devices(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        dev_hdr_host = QWidget()
        dev_hdr = QHBoxLayout(dev_hdr_host)
        dev_hdr.setContentsMargins(0, 0, 0, 0)
        dev_hdr.setSpacing(8)
        self._btn_refresh_devs = PrimaryButton("تحديث قائمة الأجهزة")
        self._btn_refresh_devs.setMinimumHeight(38)
        self._btn_refresh_devs.clicked.connect(self.refresh_connected_devices)
        self._btn_limit_selected_device = SecondaryButton("تقييد سرعة الجهاز المحدد")
        self._btn_limit_selected_device.setMinimumHeight(38)
        self._btn_limit_selected_device.clicked.connect(self._handle_limit_device_clicked)
        dev_hdr.addWidget(self._btn_refresh_devs)
        dev_hdr.addWidget(self._btn_limit_selected_device)

        p = self._make_section_panel(
            "الأجهزة المتصلة على الشبكة وإدارة النطاق",
            f"يدمج {_bi('Get-NetNeighbor')} و {_bi('ARP')} المحليين في ويندوز مع قائمة أجهزة الراوتر ويميز بين المتصل حالياً والمخزن مؤقتاً.",
            header_action=dev_hdr_host,
        )

        self._lbl_devices_limitation = QLabel(
            f"ملاحظة الصدق التقني: تقييد سرعة جهاز آخر على الشبكة لا يتم عبر نظام ويندوز، ولا يتاح إلا عبر محول راوتر يدعم {_bi('Bandwidth Control')} فعلياً."
        )
        self._lbl_devices_limitation.setFont(tokens.get_sans_font(13))
        self._lbl_devices_limitation.setStyleSheet(
            f"color: {tokens.TEXT_SECONDARY}; background-color: {tokens.SURFACE_INSET}; "
            f"border: 1px solid {tokens.LINE}; border-radius: 6px; padding: 10px 12px;"
        )
        self._lbl_devices_limitation.setWordWrap(True)
        p.main_layout.addWidget(self._lbl_devices_limitation)

        self._empty_devs = self._make_empty_placeholder("اضغط «تحديث قائمة الأجهزة» لقراءة الأجهزة النشطة على الشبكة.")
        p.main_layout.addWidget(self._empty_devs)

        self._tbl_devices = QTableWidget(0, 6)
        self._tbl_devices.setHorizontalHeaderLabels(
            [_bi("IP"), _bi("MAC"), "الشركة المصنعة", "النوع والحالة", "المصدر", "تفاصيل / إشارة"]
        )
        _style_table(self._tbl_devices, row_height=44)
        _apply_weighted_columns(
            self._tbl_devices,
            [0.16, 0.16, 0.17, 0.20, 0.15, 0.16],
            min_widths={0: 158, 1: 202, 2: 92, 3: 102, 4: 90, 5: 110},
            max_widths={0: 210, 1: 230},
        )
        make_scroll_transparent(self._tbl_devices, self._scroll)
        self._tbl_devices.setVisible(False)
        p.main_layout.addWidget(self._tbl_devices)
        lay.addWidget(p)

        lay.addStretch(1)
        return w

    # ------------------------------------------------------------------
    # Tab 7: Unified Recommendations & Before/After Reports
    # ------------------------------------------------------------------

    def _build_tab_reports(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        self._btn_build_unified = PrimaryButton("تحديث التحليل الموحد")
        self._btn_build_unified.setMinimumHeight(38)
        self._btn_build_unified.clicked.connect(self.recompute_unified_recommendations)

        rec_panel = self._make_section_panel(
            "النتائج المصنفة وخطة التوصيات المتكاملة",
            f"يربط قراءات الواي فاي و {_bi('RF')} والإنترنت و {_bi('DNS')} و {_bi('Bufferbloat')} لترتيب الأسباب الجذرية.",
            header_action=self._btn_build_unified,
        )

        self._lbl_unified_exec = QLabel(
            "بانتظار تشغيل الفحص الفعلي — لم تُجمع قياسات كافية بعد لتقييم الأعطال."
        )
        self._lbl_unified_exec.setFont(tokens.get_sans_font(13, 600))
        self._lbl_unified_exec.setStyleSheet(
            f"color: {tokens.TEXT}; background-color: {tokens.SURFACE_INSET}; "
            f"border: 1px solid {tokens.LINE}; border-radius: 6px; padding: 10px 12px;"
        )
        self._lbl_unified_exec.setWordWrap(True)
        rec_panel.main_layout.addWidget(self._lbl_unified_exec)

        self._empty_findings = self._make_empty_placeholder("لم تُسجل ملاحظات أو أعطال بعد.")
        rec_panel.main_layout.addWidget(self._empty_findings)

        self._tbl_findings = QTableWidget(0, 4)
        self._tbl_findings.setHorizontalHeaderLabels(["الفئة", "الشدة", "الثقة", "الدليل والتوصيف"])
        _style_table(self._tbl_findings, row_height=44)
        _apply_proportional_columns(self._tbl_findings, {0: 215, 1: 90, 2: 75})
        make_scroll_transparent(self._tbl_findings, self._scroll)
        self._tbl_findings.setVisible(False)
        rec_panel.main_layout.addWidget(self._tbl_findings)

        self._empty_recs = self._make_empty_placeholder("ستظهر خطة الإجراءات المرتبة بالأولوية هنا بعد التحليل.")
        rec_panel.main_layout.addWidget(self._empty_recs)

        self._tbl_recs = QTableWidget(0, 4)
        self._tbl_recs.setHorizontalHeaderLabels(["الأولوية", "النطاق", "التوصية", "الأثر المتوقع والمحددات"])
        _style_table(self._tbl_recs, row_height=44)
        _apply_proportional_columns(self._tbl_recs, {0: 80, 1: 155, 2: 260})
        make_scroll_transparent(self._tbl_recs, self._scroll)
        self._tbl_recs.setVisible(False)
        rec_panel.main_layout.addWidget(self._tbl_recs)
        lay.addWidget(rec_panel)

        ba_panel = self._make_section_panel(
            "لقطات قبل / بعد التغيير والتصدير الآمن",
            "يقارن اللقطات مع فحص تغير الظروف واستبعاد الفروق البسيطة الواقعة ضمن الضوضاء، مع تنقيح كلمات المرور عند التصدير.",
        )

        snap_actions = QHBoxLayout()
        snap_actions.setSpacing(10)
        self._btn_snap_before = SecondaryButton("حفظ لقطة جديدة (قبل/بعد)")
        self._btn_snap_before.setMinimumHeight(38)
        self._btn_snap_before.clicked.connect(lambda: self._capture_snapshot("لقطة تشخيصية"))
        self._btn_compare_ba = PrimaryButton("مقارنة اللقطتين")
        self._btn_compare_ba.setMinimumHeight(38)
        self._btn_compare_ba.clicked.connect(self._compare_selected_snapshots)
        snap_actions.addWidget(self._btn_snap_before)
        snap_actions.addWidget(self._btn_compare_ba)
        snap_actions.addStretch(1)
        ba_panel.main_layout.addLayout(snap_actions)

        snap_row = QHBoxLayout()
        snap_row.setSpacing(8)
        self._combo_before = QComboBox()
        self._combo_before.setMinimumHeight(38)
        self._combo_before.setFont(tokens.get_sans_font(12))
        self._combo_after = QComboBox()
        self._combo_after.setMinimumHeight(38)
        self._combo_after.setFont(tokens.get_sans_font(12))
        snap_row.addWidget(self._combo_before, stretch=1)
        snap_row.addWidget(self._combo_after, stretch=1)
        ba_panel.main_layout.addLayout(snap_row)

        self._lbl_ba_summary = QLabel("احفظ لقطتين على الأقل للمقارنة مع فحص تغير الظروف والضوضاء الإحصائية.")
        self._lbl_ba_summary.setFont(tokens.get_sans_font(13))
        self._lbl_ba_summary.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self._lbl_ba_summary.setWordWrap(True)
        ba_panel.main_layout.addWidget(self._lbl_ba_summary)

        self._empty_ba = self._make_empty_placeholder("ستظهر فروقات الأداء قبل وبعد التغيير هنا عند تنفيذ المقارنة.")
        ba_panel.main_layout.addWidget(self._empty_ba)

        self._tbl_ba = QTableWidget(0, 5)
        self._tbl_ba.setHorizontalHeaderLabels(["المؤشر", "قبل", "بعد", "الفرق", "الحكم الموثق"])
        _style_table(self._tbl_ba, row_height=42)
        _apply_proportional_columns(self._tbl_ba, {0: 250, 1: 125, 2: 125, 3: 115})
        make_scroll_transparent(self._tbl_ba, self._scroll)
        self._tbl_ba.setVisible(False)
        ba_panel.main_layout.addWidget(self._tbl_ba)

        exp_row = QHBoxLayout()
        exp_row.setSpacing(10)
        self._btn_export_json = SecondaryButton(f"تصدير {_bi('JSON')} منقّح (بدون أسرار)")
        self._btn_export_json.setMinimumHeight(38)
        self._btn_export_json.clicked.connect(lambda: self._export_report("json"))

        self._btn_export_html = SecondaryButton(f"تصدير {_bi('HTML')} منقّح للطباعة")
        self._btn_export_html.setMinimumHeight(38)
        self._btn_export_html.clicked.connect(lambda: self._export_report("html"))

        self._btn_export_md = SecondaryButton(f"تصدير {_bi('Markdown')} تشخيصي")
        self._btn_export_md.setMinimumHeight(38)
        self._btn_export_md.clicked.connect(lambda: self._export_report("md"))

        exp_row.addWidget(self._btn_export_json)
        exp_row.addWidget(self._btn_export_html)
        exp_row.addWidget(self._btn_export_md)
        exp_row.addStretch(1)
        ba_panel.main_layout.addLayout(exp_row)
        lay.addWidget(ba_panel)

        # Dedicated Activity & Automation Action History (11 Lifecycle States + Rollback)
        self._btn_refresh_history = SecondaryButton("تحديث سجل الإجراءات")
        self._btn_refresh_history.setMinimumHeight(38)
        self._btn_refresh_history.clicked.connect(self._refresh_action_history_table)
        hist_panel = self._make_section_panel(
            "سجل الأنشطة والتحسينات والتراجع",
            "يوثق كل التغييرات والحالات الإحدى عشرة من الاكتشاف وحتى التحقق أو التراجع دون حفظ أي أسرار.",
            header_action=self._btn_refresh_history,
        )
        self._empty_history = self._make_empty_placeholder("لم تُنفَّذ تعديلات أو طلبات تغيير بعد في السجل.")
        hist_panel.main_layout.addWidget(self._empty_history)

        self._tbl_action_history = QTableWidget(0, 6)
        self._tbl_action_history.setHorizontalHeaderLabels(
            ["الوقت", "الإجراء", "قبل ← بعد", "الحالة", "نتيجة التحقق", "تراجع"]
        )
        _style_table(self._tbl_action_history, row_height=46)
        _apply_proportional_columns(self._tbl_action_history, {0: 100, 1: 170, 2: 120, 3: 120, 5: 90})
        make_scroll_transparent(self._tbl_action_history, self._scroll)
        self._tbl_action_history.setVisible(False)
        hist_panel.main_layout.addWidget(self._tbl_action_history)
        lay.addWidget(hist_panel)

        lay.addStretch(1)
        return w

    # ------------------------------------------------------------------
    # Action Handlers & Live Renderers (100% Real Data + Arabic UI Copy)
    # ------------------------------------------------------------------

    def refresh_wifi_and_rf(self) -> None:
        active_scan = self._chk_active_scan.isChecked()

        async def _job():
            tel = await self.bundle.telemetry.collect_telemetry(
                include_events=True, include_ps_driver_stats=True, trigger_active_scan=False
            )
            scan = await self.bundle.scanner.scan(request_active_scan=active_scan)
            ch_rep = self.bundle.channel_analyzer.analyze(
                scan_result=scan,
                current_band=tel.band,
                current_channel=tel.channel,
                connected_bssid=tel.bssid,
                adapter_caps=tel.capabilities,
                router_config=self._router_config,
            )
            return tel, scan, ch_rep

        def _done(payload: Any) -> None:
            tel, scan, ch_rep = payload
            self._telemetry = tel
            self._scan_result = scan
            self._channel_report = ch_rep
            self._render_wifi_telemetry(tel)
            if tel.band in ("2.4 GHz", "5 GHz", "6 GHz"):
                idx = self._combo_band.findData(tel.band)
                if idx >= 0:
                    self._combo_band.setCurrentIndex(idx)
            self._render_channel_band_views(self._combo_band.currentData() or "2.4 GHz")
            self._render_wlan_events(tel)
            self._update_overview_kpis()
            self.recompute_unified_recommendations()

        self._run_bg_coro("قراءة الواي فاي وتحليل القنوات", _job, _done)

    def _render_wifi_telemetry(self, tel: WifiInterfaceTelemetry) -> None:
        caps = tel.capabilities
        st = tel.interface_stats
        state_ar = "متصل" if tel.connection_state == "connected" else tel.connection_state
        rows = [
            (
                "اسم المحول والواجهة",
                f"{_bi(tel.interface_name or '—')} | {_bi(tel.adapter_description or '—')}",
                PROVENANCE_LABELS_AR[MeasurementProvenance.MEASURED],
                f"حالة الارتباط: {state_ar}",
            ),
            (
                f"اسم الشبكة {_bi('SSID')}",
                _bi(tel.ssid) if tel.ssid else "غير متصل",
                PROVENANCE_LABELS_AR[MeasurementProvenance.MEASURED],
                "",
            ),
            (
                f"عنوان نقطة الوصول {_bi('BSSID')}",
                _bi(tel.bssid or "—"),
                PROVENANCE_LABELS_AR[MeasurementProvenance.MEASURED],
                "",
            ),
            (
                f"معيار {_bi('PHY')}",
                _bi(tel.phy_standard or "غير متاح"),
                PROVENANCE_LABELS_AR[tel.phy_provenance],
                "",
            ),
            (
                "النطاق الترددي الفعال",
                _bi(tel.band or "غير متاح"),
                PROVENANCE_LABELS_AR[MeasurementProvenance.MEASURED],
                "",
            ),
            (
                "القناة والتردد المركزي",
                _bi(f"Ch {tel.channel} ({tel.channel_frequency_mhz} MHz)") if tel.channel else "—",
                PROVENANCE_LABELS_AR[MeasurementProvenance.MEASURED],
                "",
            ),
            (
                "عرض القناة",
                _format_opt_num(tel.channel_width_mhz, "MHz", 0),
                PROVENANCE_LABELS_AR[tel.channel_width_provenance],
                "مستخلص من حزم البث الإدارية 802.11 للنقطة المتصلة" if tel.channel_width_mhz else "غير مكشوف في الحزم",
            ),
            (
                f"شدة الإشارة {_bi('RSSI')}",
                _format_opt_num(tel.rssi_dbm, "dBm", 0),
                PROVENANCE_LABELS_AR[tel.rssi_provenance],
                "",
            ),
            (
                "نسبة جودة الإشارة",
                _format_opt_num(tel.signal_quality_pct, "%", 0),
                PROVENANCE_LABELS_AR[tel.signal_quality_provenance],
                "",
            ),
            (
                f"ضوضاء الخلفية ({_bi('Noise Floor')})",
                _format_opt_num(tel.noise_floor_dbm, "dBm"),
                PROVENANCE_LABELS_AR[tel.noise_floor_provenance],
                "لا يكشف تعريف ويندوز قياس ضوضاء حقيقياً بـ dBm ولا يتم استنتاجه من RSSI",
            ),
            (
                f"نسبة الإشارة للضوضاء ({_bi('SNR')})",
                _format_opt_num(tel.snr_db, "dB"),
                PROVENANCE_LABELS_AR[tel.snr_provenance],
                "غير متاح لأن حساب SNR يتطلب قياس ضوضاء حقيقي غير متوفر من التعريف",
            ),
            (
                f"معدل الربط {_bi('TX / RX')}",
                f"{_bi('TX')} {_format_opt_num(tel.tx_link_rate_mbps, 'Mbps')} / {_bi('RX')} {_format_opt_num(tel.rx_link_rate_mbps, 'Mbps')}",
                PROVENANCE_LABELS_AR[tel.link_rate_provenance],
                "سرعة الطبقة الفيزيائية للواي فاي وليست سرعة الإنترنت",
            ),
            (
                f"فهرس {_bi('MCS')}",
                str(tel.mcs_index) if tel.mcs_index is not None else "غير مدعوم",
                PROVENANCE_LABELS_AR[tel.mcs_provenance],
                "واجهة wlanapi لا تكشف فهرس MCS لكل حزمة لحظياً",
            ),
            (
                f"التدفقات المكانية ({_bi('Spatial Streams')})",
                str(tel.spatial_streams) if tel.spatial_streams is not None else "غير متاح",
                PROVENANCE_LABELS_AR[tel.spatial_streams_provenance],
                "أقصى عدد تدفقات يدعمه الراوتر وفق حزم 802.11" if tel.spatial_streams else "غير مكشوف",
            ),
            (
                "إحصاءات وأخطاء الواجهة",
                _bi(
                    f"RX Err={st.rx_errors}, TX Err={st.tx_errors}, Retries={st.phy_retry_count}, FCS Err={st.phy_fcs_error_count}"
                )
                if st
                else "غير متاح",
                PROVENANCE_LABELS_AR[st.provenance if st else MeasurementProvenance.UNAVAILABLE],
                _bi(st.source) if st else "",
            ),
            (
                "قدرات المحول ومعلومات التعريف",
                _bi(
                    f"Driver={caps.driver_version if caps else '—'} | PHYs={', '.join(caps.supported_phys) if caps else '—'} | Roam={caps.roaming_aggressiveness if caps else '—'}"
                ),
                PROVENANCE_LABELS_AR[MeasurementProvenance.MEASURED],
                f"النطاق التنظيمي المرصود: {_bi(caps.regulatory_domain if caps and caps.regulatory_domain else 'افتراضي')}",
            ),
        ]

        self._tbl_wifi_metrics.setRowCount(len(rows))
        for r_idx, (k, v, p_lbl, note) in enumerate(rows):
            self._tbl_wifi_metrics.setItem(r_idx, 0, _make_item(k))
            self._tbl_wifi_metrics.setItem(r_idx, 1, _make_item(v, mono=True))
            self._tbl_wifi_metrics.setItem(r_idx, 2, _make_item(p_lbl))
            self._tbl_wifi_metrics.setItem(r_idx, 3, _make_item(note))
        self._tbl_wifi_metrics.resizeRowsToContents()
        self._toggle_table_visibility(
            self._tbl_wifi_metrics, self._empty_wifi_metrics, len(rows) > 0, max_rows=18
        )

    def _render_channel_band_views(self, band: str) -> None:
        scan = self._scan_result
        rep = self._channel_report
        if scan is None or rep is None:
            return
        b_res = rep.bands.get(band)
        best_ch = b_res.recommended_channels[0].channel if (b_res and b_res.recommended_channels) else None
        cur_ch = b_res.current_channel if b_res else None
        self._spectrum_chart.set_data(
            band=band,
            access_points=scan.access_points,
            current_channel=cur_ch,
            recommended_channel=best_ch,
        )

        if b_res:
            best_hint = ""
            if b_res.recommended_channels:
                top_r = b_res.recommended_channels[0]
                best_hint = (
                    f"أفضل قناة مرشحة في {_bi(band)}: {_bi(f'Ch {top_r.channel} ({top_r.width_mhz} MHz)')} "
                    f"بدرجة {_bi(f'{top_r.total_score:.1f}')} ({INTERFERENCE_LEVEL_AR.get(top_r.interference_level, top_r.interference_level)})."
                )
            self._lbl_rf_notice.setText(
                f"{best_hint} | جدول تنظيمي: {_bi(b_res.regulatory_domain)} | "
                f"عدد نقاط الوصول المرصودة: {len([a for a in scan.access_points if a.band == band])} "
                f"(تقدير مبني على مسح الشبكات لا على قياس طيفي مباشر ما لم يُعلن QBSS Load)."
            )
            scores = b_res.channel_scores
            self._tbl_ch_scores.setRowCount(len(scores))
            for i, sc in enumerate(scores):
                tag = _bi(f"Ch {sc.channel}") + (" (الحالية)" if sc.is_current_channel else "") + (" [DFS]" if sc.is_dfs else "")
                top_str = "، ".join(
                    f"{_bi(x['ssid'])} ({_bi('Ch ' + str(x['channel']) + ' ' + str(x['rssi_dbm']) + ' dBm')})"
                    for x in sc.strong_interferers[:2]
                )
                lvl_ar = INTERFERENCE_LEVEL_AR.get(sc.interference_level, sc.interference_level)
                conf_ar = CONFIDENCE_AR.get(sc.confidence_label, sc.confidence_label)
                self._tbl_ch_scores.setItem(i, 0, _make_item(tag, mono=True))
                self._tbl_ch_scores.setItem(i, 1, _make_item(_bi(f"{sc.width_mhz} MHz"), mono=True))
                self._tbl_ch_scores.setItem(i, 2, _make_item(_bi(f"{sc.total_score:.1f}"), mono=True))
                self._tbl_ch_scores.setItem(i, 3, _make_item(lvl_ar))
                self._tbl_ch_scores.setItem(i, 4, _make_item(_bi(f"{sc.co_channel_contribution:.1f} ({sc.co_channel_ap_count})"), mono=True))
                self._tbl_ch_scores.setItem(i, 5, _make_item(_bi(f"{sc.adjacent_overlap_contribution:.1f}"), mono=True))
                self._tbl_ch_scores.setItem(i, 6, _make_item(f"{conf_ar} ({_bi(f'{int(sc.data_confidence * 100)}%')})"))
                self._tbl_ch_scores.setItem(i, 7, _make_item(top_str or "لا يوجد تداخل قوي مرصود"))
            self._tbl_ch_scores.resizeRowsToContents()
            self._toggle_table_visibility(
                self._tbl_ch_scores, self._empty_ch_scores, len(scores) > 0, max_rows=14
            )

        band_aps = [ap for ap in scan.access_points if ap.band == band]
        self._tbl_aps.setRowCount(len(band_aps))
        for i, ap in enumerate(band_aps):
            self._tbl_aps.setItem(i, 0, _make_item("<مخفي>" if ap.is_hidden else _bi(ap.ssid)))
            self._tbl_aps.setItem(i, 1, _make_item(_bi(ap.bssid) + (" (متصل)" if ap.is_connected_ap else ""), mono=True))
            self._tbl_aps.setItem(i, 2, _make_item(_bi(ap.band)))
            self._tbl_aps.setItem(i, 3, _make_item(_bi(str(ap.channel)), mono=True))
            self._tbl_aps.setItem(i, 4, _make_item(_format_opt_num(ap.channel_width_mhz, "MHz", 0), mono=True))
            self._tbl_aps.setItem(i, 5, _make_item(_format_opt_num(ap.rssi_dbm, "dBm", 0), mono=True))
            self._tbl_aps.setItem(i, 6, _make_item(_bi(f"{ap.security_mode or '—'} | {ap.phy_standard or '—'}")))
        self._toggle_table_visibility(
            self._tbl_aps, self._empty_aps, len(band_aps) > 0, max_rows=14
        )

    def _render_wlan_events(self, tel: WifiInterfaceTelemetry) -> None:
        combined: List[tuple[str, str, str, str, str]] = []
        ev_type_ar = {
            "connected": "اتصال",
            "disconnected": "انفصال",
            "roam": "تجوال",
            "association": "ارتباط",
            "auth": "مصادقة",
            "scan": "مسح",
            "other": "أخرى",
        }
        for rm in tel.roaming_events:
            combined.append(
                (
                    _bi(rm.timestamp.strftime("%H:%M:%S")),
                    "تجوال داخل الجلسة",
                    "Roam",
                    _bi(f"{rm.from_bssid} -> {rm.to_bssid}"),
                    _bi(f"Ch {rm.from_channel} -> {rm.to_channel}"),
                )
            )
        for ev in tel.recent_wlan_events[:15]:
            combined.append(
                (
                    _bi(ev.timestamp.strftime("%m-%d %H:%M:%S")),
                    ev_type_ar.get(ev.event_type, ev.event_type),
                    _bi(str(ev.event_id)),
                    _bi(f"{ev.ssid or ''} {ev.bssid or ''}".strip()),
                    _bi(ev.message),
                )
            )
        self._tbl_wlan_events.setRowCount(len(combined))
        for i, row in enumerate(combined):
            for col_i, val in enumerate(row):
                self._tbl_wlan_events.setItem(i, col_i, _make_item(val, mono=(col_i in (0, 2, 3))))
        self._toggle_table_visibility(
            self._tbl_wlan_events, self._empty_events, len(combined) > 0, max_rows=10
        )

    def run_internet_sequence(self) -> None:
        def _done(rep: NetworkDiagnosticsReport) -> None:
            self._network_report = rep
            c = rep.conditions
            gw_ok = rep.gateway_ping.status == "ok"
            in_ok = rep.internet_ping.status == "ok"
            if gw_ok and in_ok:
                summary_ar = (
                    f"البوابة {_format_opt_num(rep.gateway_ping.avg_ms, 'ms')} (فقد {_bi(f'{rep.gateway_ping.packet_loss_pct:.1f}%')}) | "
                    f"الإنترنت {_format_opt_num(rep.internet_ping.avg_ms, 'ms')} (فقد {_bi(f'{rep.internet_ping.packet_loss_pct:.1f}%')})"
                )
            else:
                summary_ar = f"حالة البوابة: {_bi(rep.gateway_ping.status)} | الإنترنت: {_bi(rep.internet_ping.status)}"

            cond_txt = (
                f"الواجهة النشطة: {_bi(c.active_interface or '—')} | البوابة: {_bi(c.default_gateway or '—')} "
                f"(تغير البوابة: {'نعم' if c.gateway_changed else 'لا'}) | "
                f"{_bi('VPN')}: {'مفعّل' if c.vpn_active else 'لا'} | "
                f"بروكسي: {'نعم' if c.proxy_enabled else 'لا'} | "
                f"حركة خلفية: {_format_opt_num(c.competing_throughput_mbps, 'Mbps')} | {summary_ar}"
            )
            ar_notes: List[str] = []
            if c.vpn_active:
                ar_notes.append(f"اتصال VPN نشط ({_bi(', '.join(c.vpn_interfaces))})")
            if c.proxy_enabled:
                ar_notes.append(f"وكيل بروكسي مفعّل ({_bi(c.proxy_server or '')})")
            if c.gateway_changed:
                ar_notes.append(f"تغير عنوان البوابة من {_bi(c.previous_gateway)} إلى {_bi(c.default_gateway)}")
            if c.large_transfer_suspected:
                ar_notes.append(
                    f"نشاط خلفية مرتفع على الواجهة (تنزيل {_format_opt_num(c.active_interface_rx_mbps, 'Mbps')}، رفع {_format_opt_num(c.active_interface_tx_mbps, 'Mbps')})"
                )
            if c.recent_disconnect_count > 0:
                ar_notes.append(f"رُصد {c.recent_disconnect_count} حدث انقطاع حديث في سجل ويندوز")
            if c.interface_rx_errors > 0 or c.interface_tx_errors > 0:
                ar_notes.append(f"أخطاء حزم على الواجهة (RX={c.interface_rx_errors}, TX={c.interface_tx_errors})")
            if ar_notes:
                cond_txt += " | ملاحظات: " + "؛ ".join(ar_notes)
            self._lbl_net_cond.setText(cond_txt)

            status_ar = {
                "ok": "سليم",
                "not_configured": "غير مفعّل (ليس فشلاً)",
                "unreachable": "غير قابل للوصول",
                "failed": "فشل",
                "skipped": "تم تخطيه",
                "cancelled": "ملغى",
            }
            bursts = [rep.gateway_ping, rep.internet_ping, rep.ipv6_ping]
            self._tbl_net_pings.setRowCount(len(bursts))
            for i, b in enumerate(bursts):
                self._tbl_net_pings.setItem(i, 0, _make_item(_bi(f"{b.target} ({b.address_family.upper()})"), mono=True))
                self._tbl_net_pings.setItem(i, 1, _make_item(status_ar.get(b.status, b.status)))
                self._tbl_net_pings.setItem(i, 2, _make_item(_bi(f"{b.packets_received}/{b.packets_sent}"), mono=True))
                self._tbl_net_pings.setItem(i, 3, _make_item(_bi(f"{b.packet_loss_pct:.1f}%"), mono=True))
                self._tbl_net_pings.setItem(i, 4, _make_item(_format_opt_num(b.avg_ms, "ms"), mono=True))
                min_max = f"{_format_opt_num(b.min_ms)} / {_format_opt_num(b.max_ms)}"
                self._tbl_net_pings.setItem(i, 5, _make_item(min_max, mono=True))
                self._tbl_net_pings.setItem(i, 6, _make_item(_format_opt_num(b.jitter_ms, "ms"), mono=True))
            self._tbl_net_pings.resizeRowsToContents()
            self._toggle_table_visibility(
                self._tbl_net_pings, self._empty_net_pings, len(bursts) > 0, max_rows=6
            )

            hops = rep.traceroute.hops if rep.traceroute else []
            self._tbl_trace.setRowCount(len(hops))
            for i, h in enumerate(hops):
                interp_ar = (
                    f"استجاب ({_format_opt_num(h.avg_ms, 'ms')})"
                    if h.responded
                    else "لا يوجد رد ICMP (غالباً تقييد جدار ناري أو معدل رد وليس دليل فقدان)"
                )
                self._tbl_trace.setItem(i, 0, _make_item(_bi(str(h.hop_number)), mono=True))
                self._tbl_trace.setItem(i, 1, _make_item(_bi(h.ip_address or "*"), mono=True))
                self._tbl_trace.setItem(i, 2, _make_item(_format_opt_num(h.avg_ms, "ms"), mono=True))
                self._tbl_trace.setItem(i, 3, _make_item(_bi(f"{h.loss_pct:.1f}%"), mono=True))
                self._tbl_trace.setItem(i, 4, _make_item(interp_ar))
            self._toggle_table_visibility(
                self._tbl_trace, self._empty_trace, len(hops) > 0, max_rows=8
            )
            self._update_overview_kpis()
            self.recompute_unified_recommendations()

        self._run_bg_coro(
            "التشخيص المتسلسل للإنترنت",
            lambda: self.bundle.network_diag.run_sequence(),
            _done,
        )

    def run_dns_diagnostics(self) -> None:
        role_ar = {
            "configured": "المضبوط حالياً",
            "router": "خادم الراوتر",
            "cloudflare": "Cloudflare",
            "google": "Google",
        }

        def _done(rep: DnsDiagnosticsReport) -> None:
            self._dns_report = rep
            rec_txt = (
                f"الخادم الأسرع الموصى به: {_bi(rep.recommended_dns)}."
                if rep.recommended_dns
                else "الأداء ضمن هامش التذبذب الطبيعي بين الخوادم؛ لا حاجة ملحة لتغيير DNS."
            )
            freeze_txt = (
                " | حماية الاجتماعات نشطة: مسح الكاش والتبديل مقفلان."
                if rep.meeting_safety_frozen
                else " | لم يتم تعديل إعدادات DNS تلقائياً."
            )
            self._lbl_dns_summary.setText(rec_txt + freeze_txt)
            self._tbl_dns.setRowCount(len(rep.targets))
            for i, t in enumerate(rep.targets):
                rng = f"{_format_opt_num(t.min_ms)} - {_format_opt_num(t.max_ms)}" if t.min_ms is not None else "—"
                ic_s = f"{t.icmp_baseline_ms:.1f}" if t.icmp_baseline_ms is not None else "—"
                pr_s = f"{t.estimated_dns_processing_ms:.1f}" if t.estimated_dns_processing_ms is not None else "—"
                overhead = _bi(f"ICMP {ic_s} ms | DNS {pr_s} ms")
                lbl_ar = f"{role_ar.get(t.role, t.role)} ({_bi(t.server_ip or 'غير متاح')})"
                st_ar = "يعمل" if t.status == "ok" else ("غير منطبق" if t.status == "not_applicable" else "تعذر")
                self._tbl_dns.setItem(i, 0, _make_item(lbl_ar, mono=True))
                self._tbl_dns.setItem(i, 1, _make_item(st_ar))
                self._tbl_dns.setItem(i, 2, _make_item(_bi(f"{t.successful_samples}/{t.sample_count}"), mono=True))
                self._tbl_dns.setItem(i, 3, _make_item(_format_opt_num(t.median_ms, "ms"), mono=True))
                self._tbl_dns.setItem(i, 4, _make_item(rng, mono=True))
                self._tbl_dns.setItem(i, 5, _make_item(_format_opt_num(t.stdev_ms, "ms"), mono=True))
                self._tbl_dns.setItem(i, 6, _make_item(overhead, mono=True))
            self._tbl_dns.resizeRowsToContents()
            self._toggle_table_visibility(
                self._tbl_dns, self._empty_dns, len(rep.targets) > 0, max_rows=6
            )
            self.recompute_unified_recommendations()

        self._run_bg_coro(
            f"تشخيص {_bi('DNS')} متعدد العينات",
            lambda: self.bundle.dns_diag.run_diagnostics(),
            _done,
        )

    def run_speed_test(self) -> None:
        run_ul = self._chk_speed_upload.isChecked()

        def _done(rep: SpeedTestReport) -> None:
            self._speed_report = rep
            self._cell_sp_phy.update_metric(
                f"{_format_opt_num(rep.wifi_tx_link_rate_mbps)} / {_format_opt_num(rep.wifi_rx_link_rate_mbps)}",
                footer_text=f"{_bi(rep.band or '')} {_bi(rep.ssid or '')}".strip(),
            )
            self._cell_sp_lan.update_metric(
                "غير متاح",
                footer_text=f"يتطلب خادم {_bi('LAN')} محلي",
                status_color=tokens.TEXT_MUTED,
            )
            self._cell_sp_dl.unit_lbl.setVisible(rep.download_mbps is not None)
            self._cell_sp_dl.update_metric(
                _format_opt_num(rep.download_mbps),
                footer_text=f"المدة: {_format_opt_num(rep.download_duration_sec, 's')}",
            )
            qos_ar = "QoS مفعّل أثناء الاختبار" if rep.qos_active_during_test else "QoS متوقف أثناء الاختبار"
            self._cell_sp_ul.unit_lbl.setVisible(bool(rep.upload_tested and rep.upload_mbps is not None))
            if rep.upload_tested:
                self._cell_sp_ul.update_metric(
                    _format_opt_num(rep.upload_mbps),
                    footer_text=qos_ar,
                )
            else:
                self._cell_sp_ul.update_metric(
                    "تخطّي",
                    footer_text=f"تم تخطي الرفع حسب رغبتك • {qos_ar}",
                    status_color=tokens.TEXT_MUTED,
                )
            self._cell_sp_idle_ping.unit_lbl.setVisible(rep.idle_latency_ms is not None)
            self._cell_sp_idle_ping.update_metric(
                _format_opt_num(rep.idle_latency_ms),
                footer_text=f"التذبذب: {_format_opt_num(rep.jitter_ms, 'ms')} | الفقد: {_format_opt_num(rep.packet_loss_pct, '%')}",
            )
            loaded_val = rep.loaded_upload_latency_ms or rep.loaded_download_latency_ms
            self._cell_sp_loaded_ping.unit_lbl.setVisible(loaded_val is not None)
            self._cell_sp_loaded_ping.update_metric(
                _format_opt_num(loaded_val),
                footer_text=f"تنزيل: {_format_opt_num(rep.loaded_download_latency_ms, 'ms')} | رفع: {_format_opt_num(rep.loaded_upload_latency_ms, 'ms')}",
            )
            if rep.router_wan_down_mbps is not None:
                self._cell_sp_wan_sync.update_metric(
                    _bi(f"{rep.router_wan_down_mbps} / {rep.router_wan_up_mbps or '—'} Mbps"),
                    footer_text="مقروء مباشرة من خط WAN بالراوتر",
                )
            else:
                self._cell_sp_wan_sync.update_metric(
                    "غير مقروء",
                    footer_text="سجّل دخول الراوتر لقراءة سرعة الخط الحقيقية",
                    status_color=tokens.TEXT_MUTED,
                )

            self._reflow_metric_cells(
                self._cell_sp_phy,
                self._cell_sp_lan,
                self._cell_sp_dl,
                self._cell_sp_ul,
                self._cell_sp_idle_ping,
                self._cell_sp_loaded_ping,
                self._cell_sp_wan_sync,
            )
            self._sync_sub_stack_height()
            st_map = {
                "completed": "مكتمل",
                "blocked_meeting": "محظور أثناء مكالمة فيديو نشطة",
                "blocked_busy": "مشغول باختبار آخر قيد التشغيل",
                "cancelled": "ملغى",
                "failed": "تعذر القياس",
            }
            fail_s = f" | السبب: {_bi(rep.failure_reason)}" if rep.failure_reason and rep.status != "completed" else ""
            self._lbl_speed_notes.setText(
                f"الحالة: {st_map.get(rep.status, rep.status)} | الخادم: {_bi(rep.server_name)} | {qos_ar}{fail_s}"
            )
            self._update_overview_kpis()
            self.recompute_unified_recommendations()

        wan_dn = self._router_config.wan_down_mbps if self._router_config else None
        wan_up = self._router_config.wan_up_mbps if self._router_config else None
        self._run_bg_coro(
            "اختبار سرعة الإنترنت الفعلي",
            lambda: self.bundle.speed_test.run_speed_test(
                run_upload=run_ul,
                router_wan_down_mbps=wan_dn,
                router_wan_up_mbps=wan_up,
            ),
            _done,
        )

    def run_bufferbloat_test(self) -> None:
        include_combined = self._chk_bb_combined.isChecked()
        compare_qos = self._chk_bb_qos_compare.isChecked()
        explicit_approval = False
        if compare_qos:
            ans = QMessageBox.question(
                self,
                "تأكيد إيقاف QoS المؤقت للمقارنة",
                "هل تؤكد إيقاف قواعد NetGuard QoS مؤقتاً أثناء مرحلة الخمول فقط (خارج أي اجتماع) مع استعادتها والتحقق منها تلقائياً بعد المقارنة؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                compare_qos = False
            else:
                explicit_approval = True

        phase_ar = {
            "idle": "الخمول (المرجع)",
            "download_load": "تحت حمل التنزيل",
            "upload_load": "تحت حمل الرفع",
            "combined_load": "حمل مزدوج (تنزيل + رفع)",
        }

        def _done(rep: BufferbloatDiagnosticsReport) -> None:
            self._bufferbloat_report = rep
            if rep.status == "blocked_meeting":
                self._lbl_bb_summary.setText("تم منع اختبار Bufferbloat لحماية مكالمة الفيديو النشطة.")
            elif rep.status == "completed":
                self._lbl_bb_summary.setText(
                    f"الدرجة الكلية: {_bi(rep.overall_grade or '—')} | "
                    f"التنزيل: {_bi(rep.download_bloat_grade or '—')} | "
                    f"الرفع: {_bi(rep.upload_bloat_grade or '—')}"
                )
            else:
                self._lbl_bb_summary.setText(f"الحالة: {rep.status}")

            phases = [
                ph
                for ph in (rep.idle_phase, rep.download_phase, rep.upload_phase, rep.combined_phase)
                if ph is not None
            ]
            self._tbl_bb_phases.setRowCount(len(phases))
            for i, ph in enumerate(phases):
                self._tbl_bb_phases.setItem(i, 0, _make_item(phase_ar.get(ph.phase, ph.phase)))
                self._tbl_bb_phases.setItem(i, 1, _make_item(_format_opt_num(ph.avg_ms, "ms"), mono=True))
                self._tbl_bb_phases.setItem(i, 2, _make_item(_format_opt_num(ph.p95_ms, "ms"), mono=True))
                self._tbl_bb_phases.setItem(i, 3, _make_item(_format_opt_num(ph.delta_over_idle_ms, "ms"), mono=True))
                self._tbl_bb_phases.setItem(i, 4, _make_item(_format_opt_num(ph.jitter_ms, "ms"), mono=True))
                self._tbl_bb_phases.setItem(i, 5, _make_item(_bi(f"{ph.packet_loss_pct:.1f}%"), mono=True))
                self._tbl_bb_phases.setItem(i, 6, _make_item(_bi(ph.grade) if ph.grade else "المرجع"))
            self._tbl_bb_phases.resizeRowsToContents()
            self._toggle_table_visibility(
                self._tbl_bb_phases, self._empty_bb, len(phases) > 0, max_rows=6
            )
            self._update_overview_kpis()
            self.recompute_unified_recommendations()

        self._run_bg_coro(
            f"اختبار {_bi('Bufferbloat')} المتسلسل",
            lambda: self.bundle.bufferbloat.run_bufferbloat_test(
                include_upload=True,
                include_combined=include_combined,
                compare_idle_without_qos=compare_qos,
                explicit_qos_suspend_approval=explicit_approval,
            ),
            _done,
        )

    def run_router_discovery(self) -> None:
        override = self._inp_router_url.text().strip() or None

        def _done(res: RouterDiscoveryResult) -> None:
            self._discovery = res
            if res.preferred_url and not self._inp_router_url.text().strip():
                self._inp_router_url.setText(res.preferred_url)
            hw_tag = "تم التحقق الفعلي على عتاد حقيقي" if res.capabilities.hardware_verified else "اكتشاف سلبي آمن (بانتظار المصادقة)"
            hw_vendor = res.hardware_vendor or res.detected_vendor or "—"
            isp_txt = f" | علامة المزود: {_bi(res.isp_brand)}" if res.isp_brand else ""
            open_ifaces = [
                iface.get("interface_type", "")
                for iface in (res.available_interfaces or [])
                if iface.get("reachable")
            ]
            if_str = ", ".join(open_ifaces) if open_ifaces else ", ".join(str(p) for p in res.reachable_ports)
            msg = (
                f"البوابة: {_bi(res.gateway_ip or '—')} ({_bi('MAC')} {_bi(res.gateway_mac or '—')} | الشبكة {_bi(res.lan_subnet or '—')}) | "
                f"المصنّع الفعلي: {_bi(hw_vendor)} {_bi(res.detected_model or '')}{isp_txt} | "
                f"المحول: {_bi(res.adapter_id)} [ثقة: {res.detection_confidence} | {hw_tag}] | "
                f"الواجهات المتاحة: {_bi(if_str or '—')}"
            )
            if res.security_warning:
                msg += " | تنبيه أمان: البوابة تستخدم HTTP غير مشفر على الشبكة المحلية."
            self._lbl_router_disc.setText(msg)
            self._render_router_config_and_proposals()
            self.recompute_unified_recommendations()

        self._run_bg_coro(
            "اكتشاف الراوتر المحلي",
            lambda: self.bundle.router_discovery.discover(override_gateway_url=override),
            _done,
        )

    def run_router_login_and_read(self) -> None:
        url = self._inp_router_url.text().strip()
        user = self._inp_router_user.text().strip()
        pw = self._inp_router_pass.text()
        if pw and pw not in self._active_session_secrets:
            self._active_session_secrets.append(pw)
        persist_vault = self._combo_cred_mode.currentIndex() == 1
        ack_sec = self._chk_ack_transport_sec.isChecked()

        async def _job():
            disc = self._discovery or await self.bundle.router_discovery.discover(
                override_gateway_url=url or None
            )
            self._discovery = disc
            target_url = url or disc.preferred_url or ""
            if not target_url:
                raise RuntimeError("لم يتم تحديد عنوان إدارة محلي للراوتر.")
            adapter = self.bundle.router_registry.get_adapter(disc.adapter_id)
            auth = self.bundle.router_auth.authenticate_single_attempt(
                adapter=adapter,
                discovery=disc,
                base_url=target_url,
                username=user,
                password=pw,
                persist_in_windows_vault=persist_vault,
                verify_tls=False if (disc.is_https and disc.tls_trusted is False and ack_sec) else True,
                user_acknowledged_security_warning=ack_sec,
            )
            cfg = None
            devs: List[ConnectedDeviceRecord] = []
            cfg_model = None
            if auth.authenticated:
                cfg = adapter.read_config()
                devs = adapter.get_connected_devices()
                cfg_model = self.bundle.router_inspector.inspect(
                    adapter=adapter,
                    discovery=disc,
                    snapshot=cfg,
                    devices=devs,
                )
            return disc, auth, cfg, devs, cfg_model

        def _done(payload: Any) -> None:
            disc, auth, cfg, _devs, cfg_model = payload
            self._discovery = disc
            self._auth_result = auth
            self._router_config = cfg
            self._config_model = cfg_model
            if auth.authenticated:
                status_txt = f"تم تسجيل الدخول إلى الراوتر ({_bi(auth.adapter_id)}) بنجاح وقراءة الإعدادات."
            else:
                raw_msg = auth.message or ""
                if "acknowledgement" in raw_msg.lower():
                    msg_ar = "يجب الموافقة على مربع تنبيه الأمان أولاً قبل إرسال كلمة مرور الراوتر."
                elif "lockout" in raw_msg.lower():
                    msg_ar = "تم إيقاف المحاولات التلقائية مؤقتاً لحماية حساب الراوتر من القفل بعد 3 محاولات فاشلة."
                elif "invalid" in raw_msg.lower() or "rejected" in raw_msg.lower():
                    msg_ar = "بيانات الدخول مرفوضة من لوحة الراوتر؛ تأكد من اسم المستخدم وكلمة المرور دون تكرار المحاولة."
                elif "blocked non-local" in raw_msg.lower():
                    msg_ar = "عنوان الراوتر محظور لأنه خارج عناوين الشبكة المحلية الآمنة."
                else:
                    msg_ar = _bi(raw_msg)
                status_txt = f"لم تكتمل المصادقة: {msg_ar}"
            if auth.lockout_risk_warning:
                status_txt += " | تحذير قفل: تكرر الفشل قد يفعّل تأخيراً زمنياً في الراوتر."
            self._lbl_router_auth_status.setStyleSheet(
                f"color: {tokens.STATUS_OK if auth.authenticated else tokens.STATUS_BAD};"
            )
            self._lbl_router_auth_status.setText(status_txt)
            # Clear volatile password input after single login attempt; preserve Windows Vault only if chosen
            self._inp_router_pass.clear()
            if not persist_vault:
                self._active_session_secrets.clear()
            self._render_router_config_and_proposals()
            self._render_router_coverage_report()
            self.refresh_connected_devices()
            self.recompute_unified_recommendations()

        self._run_bg_coro("مصادقة الراوتر وقراءة الإعدادات", _job, _done)

    def _clear_router_creds(self) -> None:
        gw = self._discovery.gateway_ip if self._discovery else None
        if gw:
            self.bundle.router_auth.clear_saved_credentials(gw)
        else:
            self.bundle.router_auth.clear_session_credentials()
        self._inp_router_pass.clear()
        self._active_session_secrets.clear()
        self._lbl_router_auth_status.setText("تم مسح بيانات الاعتماد من الذاكرة ومخزن Windows.")

    def _render_router_config_and_proposals(self) -> None:
        cfg = self._router_config
        cfg_rows: List[tuple[str, str, str]] = []
        if cfg:
            cfg_rows.extend(
                [
                    ("الموديل والإصدار", _bi(f"{cfg.vendor or ''} {cfg.model or ''} (FW: {cfg.firmware_version or '—'})"), _bi(cfg.adapter_id)),
                    (f"حالة {_bi('WAN')}", _bi(f"{cfg.wan_status or '—'} | IP: {cfg.wan_ip or '—'}"), "من الراوتر"),
                    (f"خوادم {_bi('DNS')} بالراوتر", _bi(", ".join(cfg.dns_servers) or "—"), "من الراوتر"),
                    (_bi("QoS / SQM"), _bi(f"QoS={cfg.qos_enabled}, SQM={cfg.sqm_enabled} (متاح={cfg.sqm_available})"), "من الراوتر"),
                ]
            )
            for b_key, radio in cfg.radios.items():
                cfg_rows.append(
                    (
                        f"راديو {_bi(b_key)}",
                        _bi(f"SSID={radio.ssid or '—'} | Ch={radio.channel or '—'} | Width={radio.channel_width or '—'} | Sec={radio.security_mode or '—'}"),
                        "من الراوتر",
                    )
                )
        if self._config_model and self._config_model.settings:
            for rec in self._config_model.settings:
                val_txt = "[REDACTED]" if rec.redacted else str(rec.current_value if rec.current_value is not None else "—")
                flags = []
                if rec.change_supported:
                    flags.append("قابل للتعديل")
                elif rec.configurable:
                    flags.append("تعديل يدوي بالراوتر")
                else:
                    flags.append("قراءة فقط")
                if rec.suboptimal_hint:
                    flags.append(f"ملاحظة: {rec.suboptimal_hint}")
                note_txt = f"{rec.page_name} | {rec.meaning} ({' — '.join(flags)})"
                cfg_rows.append(
                    (
                        _bm(f"[{rec.domain}] {rec.setting_label_ar or rec.setting_label}"),
                        _bm(val_txt),
                        _bm(note_txt),
                    )
                )
        self._tbl_router_config.setRowCount(len(cfg_rows))
        for i, row in enumerate(cfg_rows):
            for c, val in enumerate(row):
                self._tbl_router_config.setItem(i, c, _make_item(val, mono=(c == 1)))
        self._tbl_router_config.resizeRowsToContents()
        self._toggle_table_visibility(
            self._tbl_router_config, self._empty_router_cfg, len(cfg_rows) > 0, max_rows=14
        )

        caps = (
            self._discovery.capabilities
            if self._discovery
            else self.bundle.router_registry.get_adapter("generic_probe").capabilities()
        )
        props = self.bundle.router_analyzer.analyze(
            capabilities=caps,
            router_config=cfg,
            config_model=self._config_model,
            telemetry=self._telemetry,
            channel_report=self._channel_report,
            dns_report=self._dns_report,
            bufferbloat_report=self._bufferbloat_report,
            network_report=self._network_report,
            devices=self._connected_devices,
        )
        self._router_proposals = props
        self._tbl_router_proposals.setRowCount(len(props))
        for i, pr in enumerate(props):
            self._tbl_router_proposals.setItem(i, 0, _make_item(_bm(pr.title)))
            self._tbl_router_proposals.setItem(i, 1, _make_item(_bm(pr.current_value or "—"), mono=True))
            self._tbl_router_proposals.setItem(i, 2, _make_item(_bm(pr.proposed_value), mono=True))
            warn_s = _bm(
                f"{SEVERITY_AR.get(pr.risk_level, pr.risk_level)} | "
                f"{'يعيد ربط الواي فاي لحظياً' if pr.requires_reconnect_warning else 'دون فصل الواي فاي'}"
            )
            self._tbl_router_proposals.setItem(i, 3, _make_item(warn_s))
            self._tbl_router_proposals.setItem(i, 4, _make_item("نعم" if pr.supported_by_adapter else "تعديل يدوي فقط"))

            btn = SecondaryButton("تطبيق بموافقة" if pr.supported_by_adapter else "دليل يدوي")
            btn.setMinimumHeight(36)
            btn.clicked.connect(lambda _c, prop=pr: self._handle_router_proposal_action(prop))
            self._tbl_router_proposals.setCellWidget(i, 5, _wrap_cell_button(btn))
        self._tbl_router_proposals.resizeRowsToContents()
        self._toggle_table_visibility(
            self._tbl_router_proposals, self._empty_router_props, len(props) > 0, max_rows=10
        )

    def _handle_router_proposal_action(self, proposal: RouterChangeProposal) -> None:
        if not proposal.supported_by_adapter:
            QMessageBox.information(
                self,
                "تعديل يدوي في لوحة الراوتر",
                f"{proposal.title}\n\nالسبب: {proposal.reason}\n\nالأثر المتوقع: {proposal.expected_impact}\n\nالمحول الحالي لا يدعم الكتابة التلقائية لهذا الخيار بأمان؛ نفّذه من صفحة الراوتر.",
            )
            return

        ans = QMessageBox.question(
            self,
            "تأكيد تعديل إعداد الراوتر",
            f"سيتم أخذ نسخة احتياطية قبل تطبيق:\n{proposal.title}\n({proposal.current_value} -> {proposal.proposed_value})\n\n"
            + ("تحذير: قد ينفصل الواي فاي بضع ثوانٍ عند التغيير.\n" if proposal.requires_reconnect_warning else "")
            + "سيتم التحقق بالقراءة المرتدة والتراجع تلقائياً عند الفشل. هل توافق؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return

        adapter = (
            self.bundle.router_registry.get_adapter(self._discovery.adapter_id)
            if self._discovery
            else None
        )
        entry = self.bundle.optimization.execute_proposal(
            adapter=adapter, proposal=proposal, explicit_user_approval=True
        )
        self._refresh_action_history_table()
        QMessageBox.information(self, "نتيجة التعديل والتحقق", f"[{entry.state.value}] {entry.verification_result}")

    def refresh_connected_devices(self) -> None:
        adapter = (
            self.bundle.router_registry.get_adapter(self._discovery.adapter_id)
            if self._discovery
            else None
        )
        gw = self._discovery.gateway_ip if self._discovery else None
        gw_vendor = (
            (self._discovery.hardware_vendor or self._discovery.detected_vendor)
            if self._discovery
            else None
        )

        def _done(payload: Any) -> None:
            devs, _supported, note = payload
            self._render_connected_devices(devs, note=note)
            self.recompute_unified_recommendations()

        self._run_bg_coro(
            "تحديث الأجهزة المتصلة",
            lambda: self.bundle.device_manager.list_connected_devices(
                adapter=adapter, gateway_ip=gw, gateway_vendor_override=gw_vendor
            ),
            _done,
        )

    def _render_connected_devices(
        self,
        devs: List[ConnectedDeviceRecord],
        *,
        note: Optional[str] = None,
    ) -> None:
        self._connected_devices = devs
        if note:
            self._lbl_devices_limitation.setText(_bm(note))
        src_ar = {"os_arp": "جدول ARP / Neighbor", "router_api": "الراوتر", "merged": "مدمج (النظام + الراوتر)"}
        st_ar = {"connected": "متصل الآن", "stale": "مخزن قديم (Stale)", "offline": "غير نشط", "unknown": "غير محدد"}
        self._tbl_devices.setRowCount(len(devs))
        for i, d in enumerate(devs):
            conn_lbl = CONN_TYPE_AR.get(d.connection_type, _bi(d.connection_type))
            status_lbl = st_ar.get(d.connection_status, d.connection_status)
            if d.is_gateway:
                role_str = f"البوابة ({status_lbl})"
            elif d.is_local_host:
                role_str = f"هذا الجهاز ({conn_lbl} | {status_lbl})"
            else:
                role_str = f"{conn_lbl} | {status_lbl}"
            ip_txt = d.ip_address or (d.ipv6_addresses[0] if d.ipv6_addresses else "—")
            det_parts: List[str] = []
            if d.hostname:
                det_parts.append(str(d.hostname))
            if d.rssi_dbm is not None:
                det_parts.append(f"{d.rssi_dbm} dBm")
            if d.link_rate_mbps is not None:
                det_parts.append(f"{d.link_rate_mbps:.0f} Mbps")
            if d.rx_limit_kbps or d.tx_limit_kbps:
                det_parts.append(f"Cap {d.rx_limit_kbps or '-'}/{d.tx_limit_kbps or '-'}k")
            self._tbl_devices.setItem(i, 0, _make_item(_bi(ip_txt), mono=True))
            self._tbl_devices.setItem(i, 1, _make_item(_bi(d.mac_address or "—"), mono=True))
            self._tbl_devices.setItem(i, 2, _make_item(_bm(d.vendor or "غير معروف")))
            self._tbl_devices.setItem(i, 3, _make_item(_bm(role_str)))
            self._tbl_devices.setItem(i, 4, _make_item(_bm(src_ar.get(d.source, d.source))))
            self._tbl_devices.setItem(i, 5, _make_item(_bm(" | ".join(det_parts) or "—")))
        self._tbl_devices.resizeRowsToContents()
        self._toggle_table_visibility(
            self._tbl_devices, self._empty_devs, len(devs) > 0, max_rows=14
        )

    def recompute_unified_recommendations(self) -> None:
        has_any_data = any(
            x is not None
            for x in (
                self._telemetry,
                self._scan_result,
                self._network_report,
                self._dns_report,
                self._speed_report,
                self._bufferbloat_report,
            )
        )
        if not has_any_data:
            self._unified_report = None
            self._lbl_unified_exec.setText(
                "بانتظار تشغيل الفحص الفعلي — لم تُجمع قياسات بعد لتقييم الأعطال."
            )
            self._lbl_ov_summary.setText(
                "بانتظار إكمال أول قراءة للواي فاي والراديو لعرض ملخص التشخيص الموحد."
            )
            self._toggle_table_visibility(self._tbl_findings, self._empty_findings, False)
            self._toggle_table_visibility(self._tbl_recs, self._empty_recs, False)
            if self._discovery is not None or self._config_model is not None or self._connected_devices:
                self._compute_and_render_root_cause()
            return

        rep = self.bundle.recommender.analyze(
            telemetry=self._telemetry,
            scan_result=self._scan_result,
            channel_report=self._channel_report,
            network_report=self._network_report,
            dns_report=self._dns_report,
            speed_report=self._speed_report,
            bufferbloat_report=self._bufferbloat_report,
            router_config=self._router_config,
        )
        self._unified_report = rep

        if not rep.findings:
            exec_ar = "لم يظهر اختناق حرج في القياسات المجمّعة حتى الآن (لتحليل أعمق نفّذ فحص الإنترنت و Bufferbloat)."
        else:
            top = rep.findings[0]
            top_cat = FAULT_CATEGORY_AR.get(top.category, top.category.value)
            exec_ar = (
                f"العامل الأعلى تأثيراً: {top_cat} — مستوى الخطورة: "
                f"{SEVERITY_AR.get(top.severity, top.severity)} (ثقة {_bi(f'{int(top.confidence * 100)}%')})."
            )
        self._lbl_unified_exec.setText(exec_ar)
        self._lbl_ov_summary.setText(exec_ar)

        self._tbl_findings.setRowCount(len(rep.findings))
        FINDING_PREFIX_AR: Dict[str, str] = {
            "f_weak_signal": "إشارة واي فاي ضعيفة تؤثر على ثبات الربط",
            "f_wrong_band": "الاتصال على نطاق مزدحم مع توفر نطاق أنظف",
            "f_channel_congestion": "ازدحام على القناة اللاسلكية الحالية",
            "f_bufferbloat": "ارتفاع الكمون تحت ضغط التنزيل/الرفع",
            "f_slow_dns": "بطء أو تعثر في استجابة خادم DNS",
            "f_local_bg": "رصد حركة تنزيل/رفع خلفية منافسة أثناء القياس",
            "f_isp_upstream": "البوابة المحلية سليمة والخلل في المسار الخارجي لمزود الخدمة",
            "f_windows_driver": "انقطاعات متكررة أو تجوال/أخطاء مسجلة في تعريف ويندوز",
        }
        for i, f in enumerate(rep.findings):
            cat_ar = FAULT_CATEGORY_AR.get(f.category, f.category.value)
            sev_ar = SEVERITY_AR.get(f.severity, f.severity)
            desc_ar = FINDING_PREFIX_AR.get(f.finding_id, _bi(f.summary))
            if f.finding_id == "f_windows_driver" and self._telemetry:
                drv = (self._telemetry.capabilities.driver_version if self._telemetry.capabilities else None) or "—"
                adp = self._telemetry.adapter_description or "—"
                desc_ar = f"{desc_ar} — المحول: {_bi(adp)} (تعريف {_bi(drv)})"
            elif f.finding_id == "f_local_bg" and self._network_report:
                c_bl = self._network_report.conditions
                desc_ar = (
                    f"{desc_ar} — حركة الخلفية المقاسة: "
                    f"تنزيل {_format_opt_num(c_bl.active_interface_rx_mbps, 'Mbps')} / "
                    f"رفع {_format_opt_num(c_bl.active_interface_tx_mbps, 'Mbps')}"
                )
            elif f.finding_id == "f_bufferbloat" and self._bufferbloat_report:
                bb = self._bufferbloat_report
                dl_d = _format_opt_num(bb.download_phase.delta_over_idle_ms, "ms") if bb.download_phase else "—"
                ul_d = _format_opt_num(bb.upload_phase.delta_over_idle_ms, "ms") if bb.upload_phase else "—"
                desc_ar = f"{desc_ar} — الدرجة الكلية: {_bi(bb.overall_grade or '—')} (تنزيل +{dl_d}، رفع +{ul_d})"
            elif f.evidence:
                desc_ar = f"{desc_ar} ({_bi(f.evidence[0])})"
            self._tbl_findings.setItem(i, 0, _make_item(cat_ar))
            self._tbl_findings.setItem(i, 1, _make_item(sev_ar))
            self._tbl_findings.setItem(i, 2, _make_item(_bi(f"{int(f.confidence * 100)}%"), mono=True))
            self._tbl_findings.setItem(i, 3, _make_item(desc_ar))
        self._tbl_findings.resizeRowsToContents()
        self._toggle_table_visibility(
            self._tbl_findings, self._empty_findings, len(rep.findings) > 0, max_rows=10
        )

        self._tbl_recs.setRowCount(len(rep.recommendations))
        for i, rec in enumerate(rep.recommendations):
            cat_lbls = "، ".join(FAULT_CATEGORY_AR.get(c, c.value) for c in rec.related_categories)
            rec_title, rec_gain = REC_AR.get(rec.recommendation_id, (_bi(rec.title), _bi(rec.expected_gain)))
            self._tbl_recs.setItem(i, 0, _make_item(_bi(str(rec.priority)), mono=True))
            self._tbl_recs.setItem(i, 1, _make_item(SCOPE_AR.get(rec.scope, rec.scope)))
            self._tbl_recs.setItem(i, 2, _make_item(rec_title))
            self._tbl_recs.setItem(i, 3, _make_item(f"يعالج: {cat_lbls} | {rec_gain}"))
        self._tbl_recs.resizeRowsToContents()
        self._toggle_table_visibility(
            self._tbl_recs, self._empty_recs, len(rep.recommendations) > 0, max_rows=10
        )
        self._compute_and_render_root_cause()

    @staticmethod
    def _reflow_metric_cells(*cells: MetricCell) -> None:
        for cell in cells:
            cell.val_lbl.adjustSize()
            cell.val_lbl.updateGeometry()
            parent = cell.val_lbl.parentWidget()
            if parent is not None and parent.layout() is not None:
                parent.layout().activate()
            if cell.layout() is not None:
                cell.layout().activate()
            cell.updateGeometry()

    def _update_overview_kpis(self) -> None:
        if self._telemetry:
            t = self._telemetry
            self._cell_ov_conn.update_metric(_bi(t.ssid) if t.ssid else "غير متصل", footer_text=_bi(t.phy_standard or ""))
            self._cell_ov_band.update_metric(
                _bi(f"{t.band or '—'} / Ch {t.channel or '—'}"),
                footer_text=_format_opt_num(t.channel_width_mhz, "MHz", 0),
            )
            self._cell_ov_rssi.update_metric(
                _bi(str(t.rssi_dbm)) if t.rssi_dbm is not None else "—",
                footer_text=f"جودة: {_format_opt_num(t.signal_quality_pct, '%', 0)}",
            )
        if self._network_report:
            nr = self._network_report
            self._cell_ov_gw.update_metric(
                _bi(f"{nr.gateway_ping.avg_ms:.1f}") if nr.gateway_ping.avg_ms is not None else "—",
                footer_text=f"فقد {_bi(f'{nr.gateway_ping.packet_loss_pct:.1f}%')}",
            )
            self._cell_ov_inet.update_metric(
                _bi(f"{nr.internet_ping.avg_ms:.1f}") if nr.internet_ping.avg_ms is not None else "—",
                footer_text=f"فقد {_bi(f'{nr.internet_ping.packet_loss_pct:.1f}%')}",
            )
        if self._bufferbloat_report:
            bb = self._bufferbloat_report
            self._cell_ov_bloat.update_metric(
                _bi(bb.overall_grade or "—"), footer_text=f"{_bi('DL')} {_bi(bb.download_bloat_grade or '—')}"
            )
        self._reflow_metric_cells(
            self._cell_ov_conn,
            self._cell_ov_band,
            self._cell_ov_rssi,
            self._cell_ov_gw,
            self._cell_ov_inet,
            self._cell_ov_bloat,
        )

    def _capture_snapshot(self, label: str) -> None:
        qos_sum = self.bundle.coordinator.get_qos_status_summary()
        snap = self.bundle.reporting.build_snapshot(
            label=f"{label} ({len(self._snapshots) + 1})",
            telemetry=self._telemetry,
            network_report=self._network_report,
            dns_report=self._dns_report,
            speed_report=self._speed_report,
            bufferbloat_report=self._bufferbloat_report,
            channel_report=self._channel_report,
            qos_active=bool(qos_sum["master_enabled"]),
        )
        self.bundle.reporting.save_snapshot(snap)
        self._load_saved_snapshots()
        self._lbl_active_status.setStyleSheet(f"color: {tokens.STATUS_OK};")
        self._lbl_active_status.setText(f"تم حفظ اللقطة '{snap.label}' في قاعدة البيانات المحلية.")

    def _load_saved_snapshots(self) -> None:
        self._snapshots = self.bundle.reporting.list_snapshots(limit=25)
        self._combo_before.clear()
        self._combo_after.clear()
        for s in self._snapshots:
            ch_disp = f"Ch {s.channel or '—'}"
            txt = f"{s.label} — {_bi(s.created_at.strftime('%m-%d %H:%M'))} ({_bi(ch_disp)})"
            self._combo_before.addItem(txt, s.snapshot_id)
            self._combo_after.addItem(txt, s.snapshot_id)
        if len(self._snapshots) >= 2:
            self._combo_before.setCurrentIndex(1)
            self._combo_after.setCurrentIndex(0)

    def _compare_selected_snapshots(self) -> None:
        idx_b = self._combo_before.currentIndex()
        idx_a = self._combo_after.currentIndex()
        if idx_b < 0 or idx_a < 0 or idx_b >= len(self._snapshots) or idx_a >= len(self._snapshots):
            self._lbl_ba_summary.setText("احفظ لقطتين على الأقل للمقارنة.")
            return
        comp = self.bundle.reporting.compare(self._snapshots[idx_b], self._snapshots[idx_a])
        self._before_after = comp
        verdict_ar = VERDICT_AR.get(comp.overall_verdict, comp.overall_verdict)
        drift_txt = " | ".join(_bi(w) for w in comp.condition_drift_warnings)
        self._lbl_ba_summary.setText(
            f"الحكم الموثق: {verdict_ar} — مقارنة قياسات حقيقية فقط"
            + (f" | تحذير تغير الظروف: {drift_txt}" if drift_txt else "")
        )
        rows = [d for d in comp.deltas if d.verdict != "unavailable"]
        self._tbl_ba.setRowCount(len(rows))
        for i, d in enumerate(rows):
            m_name = BA_METRIC_AR.get(d.metric_name, _bi(d.metric_name))
            self._tbl_ba.setItem(i, 0, _make_item(m_name))
            self._tbl_ba.setItem(i, 1, _make_item(_bi(f"{d.before_value} {d.unit}"), mono=True))
            self._tbl_ba.setItem(i, 2, _make_item(_bi(f"{d.after_value} {d.unit}"), mono=True))
            self._tbl_ba.setItem(i, 3, _make_item(_bi(f"{d.delta} {d.unit}"), mono=True))
            self._tbl_ba.setItem(i, 4, _make_item(VERDICT_AR.get(d.verdict, d.verdict)))
        self._tbl_ba.resizeRowsToContents()
        self._toggle_table_visibility(
            self._tbl_ba, self._empty_ba, len(rows) > 0, max_rows=12
        )

    def _export_report(self, fmt: str) -> None:
        ext = "json" if fmt == "json" else ("md" if fmt == "md" else "html")
        path, _ = QFileDialog.getSaveFileName(
            self, f"حفظ التقرير ({ext.upper()})", f"netguard_wifi_report.{ext}", f"*.{ext}"
        )
        if not path:
            return
        extra = {
            "telemetry": self._telemetry.model_dump(mode="json") if self._telemetry else None,
            "network_diagnostics": self._network_report.model_dump(mode="json") if self._network_report else None,
            "dns_diagnostics": self._dns_report.model_dump(mode="json") if self._dns_report else None,
            "speed_test": self._speed_report.model_dump(mode="json") if self._speed_report else None,
            "bufferbloat": self._bufferbloat_report.model_dump(mode="json") if self._bufferbloat_report else None,
        }
        if fmt == "json":
            self.bundle.reporting.export_json(
                path,
                unified_report=self._unified_report,
                comparison=self._before_after,
                extra_sections=extra,
                extra_secrets=self._active_session_secrets,
            )
        elif fmt == "md":
            md_txt = self.bundle.report_service.build_markdown_report(
                discovery=self._discovery,
                config_model=self._config_model,
                telemetry=self._telemetry,
                channel_report=self._channel_report,
                network_report=self._network_report,
                dns_report=self._dns_report,
                speed_report=self._speed_report,
                bufferbloat_report=self._bufferbloat_report,
                devices=self._connected_devices,
                root_cause=self._root_cause,
                qos_compat=self._qos_compat,
                history=self.bundle.optimization.history.list_recent(25),
            )
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(md_txt)
        else:
            self.bundle.reporting.export_html(
                path,
                unified_report=self._unified_report,
                comparison=self._before_after,
                extra_sections=extra,
                extra_secrets=self._active_session_secrets,
            )
        self._lbl_active_status.setStyleSheet(f"color: {tokens.STATUS_OK};")
        self._lbl_active_status.setText(f"تم تصدير التقرير المنقّح بنجاح إلى: {_bi(path)}")

    # ------------------------------------------------------------------
    # Unified Root-Cause Cards ('المشكلات والأخطاء'), NL Commands, Modes & History
    # ------------------------------------------------------------------

    def _compute_and_render_root_cause(self) -> None:
        qos_sum = self.bundle.coordinator.get_qos_status_summary()
        self._qos_compat = self.bundle.qos_compat.analyze(
            qos_summary=qos_sum,
            router_config=self._router_config,
            bufferbloat_report=self._bufferbloat_report,
            speed_report=self._speed_report,
        )
        caps = (
            self._config_model.capabilities
            if self._config_model and self._config_model.capabilities
            else (
                self._discovery.capabilities
                if self._discovery
                else self.bundle.router_registry.get_adapter("generic_probe").capabilities()
            )
        )
        props = self._router_proposals or self.bundle.router_analyzer.analyze(
            capabilities=caps,
            router_config=self._router_config,
            config_model=self._config_model,
            telemetry=self._telemetry,
            channel_report=self._channel_report,
            dns_report=self._dns_report,
            bufferbloat_report=self._bufferbloat_report,
            network_report=self._network_report,
            devices=self._connected_devices,
        )
        self._root_cause = self.bundle.root_cause.build_report(
            discovery=self._discovery,
            capabilities=caps,
            config_model=self._config_model,
            router_config=self._router_config,
            telemetry=self._telemetry,
            channel_report=self._channel_report,
            network_report=self._network_report,
            dns_report=self._dns_report,
            speed_report=self._speed_report,
            bufferbloat_report=self._bufferbloat_report,
            devices=self._connected_devices,
            proposals=props,
            qos_compat_findings=self._qos_compat.findings,
        )
        self._render_root_cause_faults()
        self._refresh_nl_chips()

    def _render_root_cause_faults(self) -> None:
        while self._faults_cards_layout.count():
            item = self._faults_cards_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

        rc = self._root_cause
        if rc is None:
            self._lbl_faults_summary.setText("شغّل الفحص لعرض المشكلات والأخطاء المصنفة حسب الخطورة.")
            self._tbl_app_impacts.setVisible(False)
            return

        self._lbl_faults_summary.setText(_bm(f"{rc.summary_ar} — {rc.primary_root_cause_ar}"))
        for card in rc.fault_cards[:12]:
            cw = _FaultCardWidget(
                card,
                on_execute=self._execute_fault_card_action,
                on_toggle=self._sync_sub_stack_height,
            )
            self._faults_cards_layout.addWidget(cw)

        self._tbl_app_impacts.setRowCount(len(rc.app_impacts))
        for i, imp in enumerate(rc.app_impacts):
            self._tbl_app_impacts.setItem(i, 0, _make_item(_bm(imp.app_title_ar)))
            self._tbl_app_impacts.setItem(i, 1, _make_item(_bm(imp.status_ar)))
            self._tbl_app_impacts.setItem(i, 2, _make_item(_bm(" • ".join(imp.root_causes_ar))))
            self._tbl_app_impacts.setItem(i, 3, _make_item(_bm(imp.fix_action_ar)))
        self._tbl_app_impacts.resizeRowsToContents()
        self._tbl_app_impacts.setVisible(bool(rc.app_impacts))
        if rc.app_impacts:
            self._toggle_table_visibility(
                self._tbl_app_impacts,
                None,
                True,
                max_rows=8,
            )
        QTimer.singleShot(0, self._sync_sub_stack_height)

    def _execute_fault_card_action(self, card: DiagnosticFaultCard) -> None:
        if card.linked_proposal is not None and card.can_netguard_execute:
            self._handle_router_proposal_action(card.linked_proposal)
            return
        if card.action_type == "local_dns":
            dns_target = (self._dns_report.recommended_dns if self._dns_report else None) or "1.1.1.1"
            secondary = "1.0.0.1" if dns_target == "1.1.1.1" else ("8.8.4.4" if dns_target == "8.8.8.8" else "1.1.1.1")
            ans = QMessageBox.question(
                self,
                "تنفيذ تحويل DNS المحلي على ويندوز",
                f"هل توافق على تطبيق خادم DNS المقاس الأسرع ({dns_target} / {secondary}) على محول الشبكة النشط عبر NetGuard الآن؟\n"
                "(يُرفض التعديل تلقائياً إذا كان هناك اجتماع فيديو حرج قيد التشغيل).",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if ans == QMessageBox.StandardButton.Yes:
                self.apply_local_dns_requested.emit(dns_target, secondary, f"NetGuard Best ({dns_target})")
        elif card.action_type == "local_qos":
            QMessageBox.information(
                self,
                "أولوية QoS وتخفيف Bufferbloat",
                f"{card.execution_capability_note}\n\n"
                "تعمل حماية NetGuard QoS المحلية على تأمين المكالمات تلقائياً عند انعقاد الاجتماعات، "
                "ويمكنك ضبط سقف سرعة التطبيقات المزدحمة من تبويب (حركة البيانات).",
            )
        else:
            QMessageBox.information(self, card.issue_name, f"{card.execution_capability_note}\n\nالحل: {card.recommended_solution}")

    def _refresh_nl_chips(self) -> None:
        while self._nl_chips_layout.count():
            it = self._nl_chips_layout.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._nl_quick_buttons.clear()
        suggestions = self.bundle.nl_commands.generate_contextual_suggestions(self._root_cause)[:6]
        for idx, cmd_txt in enumerate(suggestions):
            b = SecondaryButton(cmd_txt)
            b.setMinimumHeight(36)
            b.clicked.connect(lambda _c=False, t=cmd_txt: self.run_nl_command(t))
            self._nl_quick_buttons.append(b)
            self._nl_chips_layout.addWidget(b, idx // 3, idx % 3)

    def run_nl_command(self, preset_text: Optional[str] = None) -> None:
        text = preset_text if isinstance(preset_text, str) and preset_text.strip() else self._inp_nl_cmd.text().strip()
        if not text:
            return
        if preset_text:
            self._inp_nl_cmd.setText(text)
        ctx = {
            "root_cause": self._root_cause,
            "telemetry": self._telemetry,
            "config_model": self._config_model,
            "capabilities": self._config_model.capabilities if self._config_model else (self._discovery.capabilities if self._discovery else None),
            "authenticated": bool(self._auth_result and self._auth_result.authenticated),
            "dns_report": self._dns_report,
            "bufferbloat_report": self._bufferbloat_report,
            "channel_report": self._channel_report,
            "devices": self._connected_devices,
            "qos_compat": self._qos_compat,
            "history": self.bundle.optimization.history.list_recent(10),
            "comparison": self._before_after,
        }
        resp = self.bundle.nl_commands.execute_sync_summary(text, context=ctx)
        self._lbl_nl_answer.setText(resp.answer_ar)
        if resp.triggered_action == "run_full_scan":
            self.run_full_network_health_scan()
        elif resp.triggered_action == "scan_rf":
            self.refresh_wifi_and_rf()
        elif resp.triggered_action == "run_dns":
            self.run_dns_diagnostics()
        elif resp.triggered_action == "run_bufferbloat":
            self.run_bufferbloat_test()
        elif resp.triggered_action == "discover_router":
            self.run_router_discovery()
            self.switch_subtab(5)
        elif resp.triggered_action == "refresh_devices":
            self.refresh_connected_devices()
            self.switch_subtab(6)
        elif resp.triggered_action == "propose_channel_change":
            self._run_channel_optimization_workflow()
        elif resp.triggered_action == "undo_last_action":
            cands = [h for h in self.bundle.optimization.history.list_recent(10) if h.rollback_available]
            if cands:
                self._rollback_history_action(cands[0].action_id)

    def run_full_network_health_scan(self) -> None:
        async def _job():
            tel = await self.bundle.telemetry.collect_telemetry(
                include_events=True, include_ps_driver_stats=True, trigger_active_scan=False
            )
            scan = await self.bundle.scanner.scan(request_active_scan=False)
            ch_rep = self.bundle.channel_analyzer.analyze(
                scan_result=scan,
                current_band=tel.band,
                current_channel=tel.channel,
                connected_bssid=tel.bssid,
                adapter_caps=tel.capabilities,
                router_config=self._router_config,
            )
            disc = await self.bundle.router_discovery.discover(
                override_gateway_url=self._inp_router_url.text().strip() or None
            )
            net_rep = await self.bundle.network_diag.run_sequence()
            dns_rep = await self.bundle.dns_diag.run_diagnostics()
            return tel, scan, ch_rep, disc, net_rep, dns_rep

        def _done(payload: Any) -> None:
            tel, scan, ch_rep, disc, net_rep, dns_rep = payload
            self._telemetry = tel
            self._scan_result = scan
            self._channel_report = ch_rep
            self._discovery = disc
            self._network_report = net_rep
            self._dns_report = dns_rep
            if disc.preferred_url and not self._inp_router_url.text().strip():
                self._inp_router_url.setText(disc.preferred_url)
            self._render_wifi_telemetry(tel)
            self._update_overview_kpis()
            self._render_router_config_and_proposals()
            self.recompute_unified_recommendations()

        self._run_bg_coro("فحص صحة الشبكة والراوتر الشامل", _job, _done)

    def _run_channel_optimization_workflow(self) -> None:
        props = [p for p in self._router_proposals if p.category == "wifi_channel"]
        if not props and self._channel_report:
            caps = (
                self._discovery.capabilities
                if self._discovery
                else self.bundle.router_registry.get_adapter("generic_probe").capabilities()
            )
            props = [
                p
                for p in self.bundle.router_analyzer.analyze(
                    capabilities=caps,
                    router_config=self._router_config,
                    telemetry=self._telemetry,
                    channel_report=self._channel_report,
                )
                if p.category == "wifi_channel"
            ]
        if not props:
            QMessageBox.information(self, "تحسين القناة", "القناة الحالية مثالية ولا تتطلب تغييراً، أو لم يُجرَ مسح القنوات بعد.")
            return
        prop = props[0]
        if not prop.supported_by_adapter or not (self._auth_result and self._auth_result.authenticated):
            QMessageBox.information(
                self,
                "توجيه تغيير القناة",
                f"أفضل إجراء مقترح: {prop.title}\n({prop.reason})\n\n"
                "للتنفيذ التلقائي عبر NetGuard، يجب تسجيل الدخول بحساب المدير على محول راوتر يدعم تعديل القناة.",
            )
            return

        ans = QMessageBox.question(
            self,
            "تأكيد تحسين القناة اللاسلكية",
            f"سيتم تنفيذ خطوات تحسين القناة الـ 14:\n{prop.title}\n"
            f"({prop.current_value} -> {prop.proposed_value})\n\n"
            "• حفظ نسخة احتياطية قبل التعديل\n"
            "• انتظار إعادة اتصال Wi-Fi تلقائياً\n"
            "• التحقق بالقراءة المرتدة والقياس البعدي أو التراجع الفوري عند الفشل\n\nهل توافق؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return

        adapter = self.bundle.router_registry.get_adapter(self._discovery.adapter_id) if self._discovery else None
        before_snap = BeforeAfterSnapshot(
            snapshot_id=f"pre_{uuid.uuid4().hex[:8]}",
            label="قبل تغيير القناة",
            rssi_dbm=self._telemetry.rssi_dbm if self._telemetry else None,
            tx_link_rate_mbps=self._telemetry.tx_link_rate_mbps if self._telemetry else None,
            gateway_avg_ms=self._network_report.gateway_ping.avg_ms if self._network_report else None,
        )

        async def _job():
            target_ssid = self._telemetry.ssid if self._telemetry else None

            async def _wait_reconnect() -> bool:
                # Poll Wi-Fi telemetry until connection re-stabilizes or timeout window expires
                for _ in range(10):
                    await asyncio.sleep(1.0)
                    try:
                        t_poll = await self.bundle.telemetry.collect_telemetry(include_events=False)
                        if t_poll.connection_state == "connected" and (
                            not target_ssid or t_poll.ssid == target_ssid
                        ):
                            return True
                    except Exception:
                        pass
                return False

            async def _collect_after() -> BeforeAfterSnapshot:
                t2 = await self.bundle.telemetry.collect_telemetry(include_events=False)
                return BeforeAfterSnapshot(
                    snapshot_id=f"post_{uuid.uuid4().hex[:8]}",
                    label="بعد تغيير القناة",
                    rssi_dbm=t2.rssi_dbm,
                    tx_link_rate_mbps=t2.tx_link_rate_mbps,
                )

            return await self.bundle.optimization.optimize_wifi_channel_workflow(
                adapter=adapter,
                proposal=prop,
                explicit_user_approval=True,
                before_snapshot=before_snap,
                wait_reconnect_fn=_wait_reconnect,
                collect_after_fn=_collect_after,
            )

        def _done(res_tuple: Any) -> None:
            entry, _comp = res_tuple
            self._refresh_action_history_table()
            QMessageBox.information(self, "نتيجة تحسين القناة", f"[{entry.state.value}] {entry.verification_result}")
            self.refresh_wifi_and_rf()

        self._run_bg_coro("تنفيذ والتحقق من تغيير القناة اللاسلكية", _job, _done)

    def run_router_dom_inspection(self) -> None:
        target_url = self._inp_router_url.text().strip() or (self._discovery.preferred_url if self._discovery else "")
        if not target_url:
            QMessageBox.information(self, "فحص DOM", "شغّل الاكتشاف أو أدخل عنوان الراوتر المحلي أولاً.")
            return
        user = self._inp_router_user.text().strip() or None
        pw = self._inp_router_pass.text() or None
        if pw and pw not in self._active_session_secrets:
            self._active_session_secrets.append(pw)
        allow_lb = bool(self._discovery is None or "127.0.0.1" in target_url)
        dom_res = self.bundle.dom_inspector.inspect_portal(
            base_url=target_url,
            username=user,
            password=pw,
            allow_loopback=allow_lb,
            max_pages=6,
        )
        adapter_id = self._discovery.adapter_id if self._discovery else "generic_probe"
        adapter = self.bundle.router_registry.get_adapter(adapter_id)
        self._config_model = self.bundle.router_inspector.inspect(
            adapter=adapter,
            discovery=self._discovery,
            snapshot=self._router_config,
            devices=self._connected_devices,
            dom_result=dom_res,
        )
        self._render_router_coverage_report()
        self.recompute_unified_recommendations()
        self._lbl_active_status.setText(
            f"اكتمل فحص DOM: تم فحص {len(dom_res.pages)} صفحة، نموذج دخول={'موجود' if dom_res.login_form_detected else 'غير ظاهر'}."
        )

    def _render_router_coverage_report(self) -> None:
        cm = self._config_model
        if cm is None:
            self._lbl_router_coverage.setText("لم يكتمل فحص صفحات الراوتر المصادق عليه بعد.")
            self._toggle_table_visibility(self._tbl_router_pages, self._empty_router_pages, False)
            return
        cov = cm.coverage
        self._lbl_router_coverage.setText(
            f"{cov.honesty_statement} | نسخ احتياطي: {cov.backup_note or 'غير متاح'}"
        )
        self._tbl_router_pages.setRowCount(len(cov.pages))
        for i, p in enumerate(cov.pages):
            name_s = f"{p.section} / {p.page_name}"
            acc_s = f"وصول: {'نعم' if p.accessed else 'لا'} | قيم: {'نعم' if p.values_extracted else 'لا'}"
            self._tbl_router_pages.setItem(i, 0, _make_item(_bm(name_s)))
            self._tbl_router_pages.setItem(i, 1, _make_item(acc_s))
            self._tbl_router_pages.setItem(i, 2, _make_item(_bi(p.coverage_status.value), mono=True))
            self._tbl_router_pages.setItem(i, 3, _make_item(_bi(p.change_capability.value)))
            self._tbl_router_pages.setItem(
                i, 4, _make_item(_bm(p.error_or_reason or f"{p.settings_count} إعداداً"))
            )
        self._tbl_router_pages.resizeRowsToContents()
        self._toggle_table_visibility(
            self._tbl_router_pages, self._empty_router_pages, len(cov.pages) > 0, max_rows=10
        )

    def sync_operating_mode(self, op_mode: Any, *, allow_auto_router: bool = True) -> None:
        """Synchronize NetGuard's main OperatingMode with the Wi-Fi & Router OptimizationMode selector."""
        mode_val = getattr(op_mode, "value", str(op_mode)).lower()
        target_idx = 1
        if "watch" in mode_val or "observ" in mode_val or "monitor" in mode_val:
            target_idx = 0
        elif "ask" in mode_val or "assist" in mode_val:
            target_idx = 1
        elif "auto" in mode_val:
            target_idx = 2 if allow_auto_router else 1
        if self._combo_opt_mode.currentIndex() != target_idx:
            self._combo_opt_mode.setCurrentIndex(target_idx)
        else:
            self._on_opt_mode_changed()

    def _on_opt_mode_changed(self) -> None:
        idx = self._combo_opt_mode.currentIndex()
        mode_map = {
            0: OptimizationMode.MONITOR_AND_DIAGNOSE,
            1: OptimizationMode.APPROVAL_REQUIRED,
            2: OptimizationMode.AUTHORIZED_AUTO_OPTIMIZATION,
        }
        self.bundle.optimization.mode = mode_map.get(idx, OptimizationMode.APPROVAL_REQUIRED)
        allowed: set[str] = set()
        if self._chk_auto_ch.isChecked():
            allowed.add("wifi_channel")
            allowed.add("channel_width")
        if self._chk_auto_dns.isChecked():
            allowed.add("dns")
        self.bundle.optimization.auto_allowed_categories = allowed

    def _handle_limit_device_clicked(self) -> None:
        row = self._tbl_devices.currentRow()
        if row < 0 or row >= len(self._connected_devices):
            QMessageBox.information(self, "تقييد جهاز", "اختر جهازاً من الجدول أولاً.")
            return
        dev = self._connected_devices[row]
        adapter = (
            self.bundle.router_registry.get_adapter(self._discovery.adapter_id)
            if self._discovery
            else None
        )
        if not (adapter and adapter.capabilities().supports_per_device_bandwidth and adapter.is_authenticated):
            res = self.bundle.device_manager.set_device_bandwidth_limit(
                adapter=adapter,
                device=dev,
                rx_limit_kbps=5000,
                tx_limit_kbps=1500,
                explicit_user_approval=False,
            )
            QMessageBox.information(self, "حدود التحكم في نطاق الجهاز", res.message)
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("تقييد سرعة الجهاز عبر الراوتر")
        dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        form = QFormLayout(dlg)
        sp_dl = QSpinBox(dlg)
        sp_dl.setRange(128, 1_000_000)
        sp_dl.setValue(dev.rx_limit_kbps or 10_000)
        sp_dl.setSuffix(" Kbps")
        sp_ul = QSpinBox(dlg)
        sp_ul.setRange(128, 500_000)
        sp_ul.setValue(dev.tx_limit_kbps or 3_000)
        sp_ul.setSuffix(" Kbps")
        form.addRow(QLabel(f"الجهاز: {dev.hostname or dev.ip_address or dev.mac_address}"), QLabel(""))
        form.addRow("حد التنزيل الأقصى (DL):", sp_dl)
        form.addRow("حد الرفع الأقصى (UL):", sp_ul)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            dlg,
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        res = self.bundle.device_manager.set_device_bandwidth_limit(
            adapter=adapter,
            device=dev,
            rx_limit_kbps=int(sp_dl.value()),
            tx_limit_kbps=int(sp_ul.value()),
            explicit_user_approval=True,
        )
        QMessageBox.information(self, "حالة التحكم في نطاق الجهاز", res.message)

    def _refresh_action_history_table(self) -> None:
        entries = self.bundle.optimization.history.list_recent(30)
        self._tbl_action_history.setRowCount(len(entries))
        for i, h in enumerate(entries):
            t_s = h.created_at.strftime("%m-%d %H:%M")
            val_s = f"{h.previous_value or '—'} -> {h.new_value or '—'}"
            self._tbl_action_history.setItem(i, 0, _make_item(_bi(t_s), mono=True))
            self._tbl_action_history.setItem(i, 1, _make_item(_bm(h.title)))
            self._tbl_action_history.setItem(i, 2, _make_item(_bi(val_s), mono=True))
            self._tbl_action_history.setItem(i, 3, _make_item(_bi(h.state.value), mono=True))
            self._tbl_action_history.setItem(i, 4, _make_item(_bm(h.verification_result or "—")))
            if h.rollback_available:
                btn_rb = SecondaryButton("تراجع")
                btn_rb.setMinimumHeight(36)
                btn_rb.clicked.connect(lambda _c=False, aid=h.action_id: self._rollback_history_action(aid))
                self._tbl_action_history.setCellWidget(i, 5, _wrap_cell_button(btn_rb))
            else:
                self._tbl_action_history.setItem(i, 5, _make_item("—"))
        self._tbl_action_history.resizeRowsToContents()
        self._toggle_table_visibility(
            self._tbl_action_history, self._empty_history, len(entries) > 0, max_rows=10
        )

    def _rollback_history_action(self, action_id: str) -> None:
        adapter = (
            self.bundle.router_registry.get_adapter(self._discovery.adapter_id)
            if self._discovery
            else None
        )
        ok, msg = self.bundle.optimization.rollback.rollback_action(
            action_id=action_id, adapter=adapter
        )
        self._refresh_action_history_table()
        QMessageBox.information(self, "نتيجة التراجع" if ok else "تعذر التراجع", msg)
