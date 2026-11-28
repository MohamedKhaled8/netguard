"""Wi-Fi Intelligence — Wireless RF Analysis Workstation View for NetGuard AI.

Features:
- Connected AP overview card + Semicircular Wi-Fi Quality CircularGauge
- 16-metric telemetry table with explicit provenance (Measured / Inferred / Unavailable)
- Channel Spectrum Chart across 2.4 GHz, 5 GHz, and 6 GHz bands
- Weighted channel interference scoring table & one-click safe optimization
- RSSI time-series trend chart (real collected readings only)
- Searchable nearby BSS list & Windows WLAN AutoConfig event log
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui import tokens
from app.ui.i18n import language_manager, tr
from app.ui.widgets.scroll_forwarder import fit_table_to_content
from app.ui.widgets.async_bridge import AsyncViewBridge
from app.ui.widgets.base_panel import Panel
from app.ui.widgets.buttons import PrimaryButton, SecondaryButton
from app.ui.widgets.channel_spectrum_chart import ChannelSpectrumChart
from app.ui.widgets.circular_gauge import CircularGauge
from app.ui.widgets.latency_chart import LatencyPlotCanvas
from app.ui.widgets.segmented import SegmentedControl
from app.ui.widgets.status_badge import StatusBadge


class WifiIntelligenceView(QScrollArea):
    """Wireless RF Analysis Workstation."""

    wifi_telemetry_updated = Signal(object)

    def __init__(self, app_core: Any = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.app_core = app_core
        self.bundle = getattr(app_core, "wifi_bundle", None) if app_core else None
        self.bridge = AsyncViewBridge(self)

        self._last_tel: Any = None
        self._last_scan: Any = None
        self._last_ch_report: Any = None
        self._selected_band = "5 GHz"
        self._user_picked_band = False
        self._scan_state = "not_started"
        self._initial_scan_started = False
        self._page_active = False
        self._rssi_history: List[float] = []
        self._rssi_timestamps: List[str] = []
        self._last_auto_opt_at: Dict[str, float] = {}
        self._last_improvement_note: str = ""

        self._auto_timer = QTimer(self)
        self._auto_timer.setInterval(30_000)
        self._auto_timer.timeout.connect(self._on_auto_timer_tick)

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

        # ------------------------------------------------------------------
        # 1. Header & Connected AP Workstation Summary
        # ------------------------------------------------------------------
        hdr_card = QFrame()
        hdr_card.setObjectName("WifiHdrCard")
        hdr_card.setStyleSheet(
            f"""
            QFrame#WifiHdrCard {{
                background-color: {tokens.SURFACE};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_PANEL}px;
            }}
            """
        )
        hdr_outer = QVBoxLayout(hdr_card)
        hdr_outer.setContentsMargins(20, 16, 20, 16)
        hdr_outer.setSpacing(14)

        hdr_lay = QHBoxLayout()
        hdr_lay.setSpacing(20)

        self.wifi_gauge = CircularGauge(
            title=tr("dash.wifi_quality"),
            unit="%",
            size=122,
            semicircular=True,
        )
        self.wifi_gauge.set_value(None, subtitle=tr("status.waiting"))
        hdr_lay.addWidget(self.wifi_gauge)

        info_col = QVBoxLayout()
        info_col.setSpacing(6)
        title_row = QHBoxLayout()
        self.lbl_title = QLabel(tr("wifi_title"))
        self.lbl_title.setFont(tokens.get_sans_font(20, 700))
        self.lbl_title.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_title.setWordWrap(True)
        self.badge_wifi = StatusBadge(tokens.SystemStatus.WAITING, tr("status.waiting"))
        title_row.addWidget(self.lbl_title, 1)
        title_row.addWidget(self.badge_wifi)
        info_col.addLayout(title_row)

        self.lbl_sub = QLabel(tr("wifi_sub"))
        self.lbl_sub.setFont(tokens.get_sans_font(12, 400))
        self.lbl_sub.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_sub.setWordWrap(True)
        info_col.addWidget(self.lbl_sub)

        ap_grid = QGridLayout()
        ap_grid.setSpacing(10)
        self._ap_ssid = self._mini_cell("SSID", "—")
        self._ap_band_ch = self._mini_cell("النطاق والقناة", "—")
        self._ap_rssi_snr = self._mini_cell("RSSI / SNR", "—")
        self._ap_phy = self._mini_cell("معدل الربط (PHY)", "—")
        ap_grid.addWidget(self._ap_ssid[0], 0, 0)
        ap_grid.addWidget(self._ap_band_ch[0], 0, 1)
        ap_grid.addWidget(self._ap_rssi_snr[0], 1, 0)
        ap_grid.addWidget(self._ap_phy[0], 1, 1)
        info_col.addLayout(ap_grid)
        hdr_lay.addLayout(info_col, 1)
        hdr_outer.addLayout(hdr_lay)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        self.btn_rf_refresh = PrimaryButton("فحص الواي فاي والقنوات")
        self.btn_rf_refresh.clicked.connect(lambda: self.refresh_wifi_and_rf(force_active_scan=True))
        self.btn_optimize_channel = SecondaryButton(tokens.bidi_isolate_mixed(f"تحليل وتحسين قناة {self._selected_band}"))
        self.btn_optimize_channel.clicked.connect(self.analyze_and_optimize_channel)
        self.chk_auto_scan = QCheckBox("تحديث تلقائي كل 30ث")
        self.chk_auto_scan.setChecked(True)
        self.chk_auto_scan.setStyleSheet(f"color: {tokens.TEXT_MUTED}; font-size: 12px;")
        self.chk_auto_scan.toggled.connect(self._sync_auto_timer)
        self.chk_auto_optimize = QCheckBox("تغيير القناة تلقائياً عند الازدحام")
        self.chk_auto_optimize.setChecked(False)
        self.chk_auto_optimize.setStyleSheet(f"color: {tokens.TEXT_MUTED}; font-size: 12px;")
        btn_row.addWidget(self.btn_rf_refresh)
        btn_row.addWidget(self.btn_optimize_channel)
        btn_row.addWidget(self.chk_auto_scan)
        btn_row.addWidget(self.chk_auto_optimize)
        btn_row.addStretch(1)
        hdr_outer.addLayout(btn_row)
        self.root.addWidget(hdr_card)

        # Plain-language Egyptian Arabic status & improvement summary banner
        summary_box = QFrame()
        summary_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        summary_box.setStyleSheet(
            f"background-color: {tokens.INFO_SOFT_BG}; border: 1px solid {tokens.INFO_BORDER}; border-radius: 10px;"
        )
        self._summary_box = summary_box
        s_lay = QVBoxLayout(summary_box)
        s_lay.setContentsMargins(14, 12, 14, 12)
        s_lay.setSpacing(6)
        self.lbl_plain_title = QLabel("الوضع الحالي للواي فاي (بالعامية)")
        self.lbl_plain_title.setFont(tokens.get_sans_font(13, 700))
        self.lbl_plain_title.setStyleSheet(f"color: {tokens.ACCENT_BRIGHT}; border: none; background: transparent;")
        self.lbl_plain_summary = QLabel("جاري فحص الشبكات المحيطة عشان نحددلك أنسب قناة تقلل التقطيع...")
        self.lbl_plain_summary.setFont(tokens.get_sans_font(12, 500))
        self.lbl_plain_summary.setStyleSheet(f"color: {tokens.TEXT}; border: none; background: transparent;")
        self.lbl_plain_summary.setWordWrap(True)
        self.lbl_plain_summary.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        s_lay.addWidget(self.lbl_plain_title)
        s_lay.addWidget(self.lbl_plain_summary)
        self.root.addWidget(summary_box)

        # ------------------------------------------------------------------
        # 2. Spectrum Analyzer & RSSI Trend Row
        # ------------------------------------------------------------------
        band_bar = QHBoxLayout()
        band_bar.setSpacing(10)
        lbl_b = QLabel("النطاق الترددي / Band:")
        lbl_b.setFont(tokens.get_sans_font(13, 600))
        lbl_b.setStyleSheet(f"color: {tokens.TEXT};")
        self.band_switch = SegmentedControl(["2.4 GHz", "5 GHz", "6 GHz"], initial_index=1)
        self.band_switch.current_changed.connect(self._on_band_changed)
        band_bar.addWidget(lbl_b)
        band_bar.addWidget(self.band_switch)
        self.lbl_ch_rec = QLabel("لم يبدأ المسح الترددي بعد — اضغط فحص الواي فاي.")
        self.lbl_ch_rec.setFont(tokens.get_sans_font(12, 500))
        self.lbl_ch_rec.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_ch_rec.setWordWrap(True)
        band_bar.addWidget(self.lbl_ch_rec, 1)
        self.root.addLayout(band_bar)

        spec_panel = Panel(
            title="محلل الطيف الترددي / Channel Spectrum",
            subtitle="توزيع الشبكات المجاورة وقوة إشارتها عبر القنوات",
            padding=18,
        )
        scan_status_row = QHBoxLayout()
        self.badge_scan_state = StatusBadge(tokens.SystemStatus.WAITING, "لم يبدأ المسح")
        self.lbl_scan_status_detail = QLabel("في انتظار فحص الشبكات.")
        self.lbl_scan_status_detail.setFont(tokens.get_sans_font(12, 400))
        self.lbl_scan_status_detail.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_scan_status_detail.setWordWrap(True)
        self.btn_retry_scan = SecondaryButton("إعادة المسح")
        self.btn_retry_scan.clicked.connect(lambda: self.refresh_wifi_and_rf(force_active_scan=True))
        self.btn_retry_scan.setVisible(False)
        scan_status_row.addWidget(self.badge_scan_state)
        scan_status_row.addWidget(self.lbl_scan_status_detail, 1)
        scan_status_row.addWidget(self.btn_retry_scan)
        spec_panel.main_layout.addLayout(scan_status_row)

        self.spectrum_chart = ChannelSpectrumChart()
        self.spectrum_chart.setMinimumHeight(210)
        self.spectrum_chart.set_data(band=self._selected_band, access_points=[])
        spec_panel.main_layout.addWidget(self.spectrum_chart)
        self.root.addWidget(spec_panel)

        # Channel scoring + RSSI trend side-by-side
        mid_row = QGridLayout()
        mid_row.setSpacing(14)

        ch_panel = Panel(
            title="تقييم القنوات / Channel Scores",
            subtitle="الدرجة الأعلى = تداخل أقل",
            padding=16,
        )
        self.table_channels = QTableWidget(0, 4)
        self.table_channels.setHorizontalHeaderLabels(["القناة", "التقييم", "تداخل مجاور/مشترك", "التوصية"])
        self.table_channels.verticalHeader().setVisible(False)
        self.table_channels.verticalHeader().setDefaultSectionSize(42)
        self.table_channels.horizontalHeader().setMinimumHeight(46)
        self.table_channels.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_channels.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        fit_table_to_content(self.table_channels)
        ch_panel.main_layout.addWidget(self.table_channels)

        rssi_panel = Panel(
            title="استقرار إشارة RSSI / Signal Trend",
            subtitle="قوة الإشارة اللحظية (%)",
            padding=16,
        )
        self.rssi_canvas = LatencyPlotCanvas()
        self.rssi_canvas.setMinimumHeight(175)
        rssi_panel.main_layout.addWidget(self.rssi_canvas)

        mid_row.addWidget(ch_panel, 0, 0)
        mid_row.addWidget(rssi_panel, 0, 1)
        self.root.addLayout(mid_row)

        # ------------------------------------------------------------------
        # 3. 16-Metric WLAN Telemetry & Provenance Table
        # ------------------------------------------------------------------
        metrics_panel = Panel(
            title="مقاييس الواي فاي التفصيلية / WLAN Telemetry",
            subtitle="قياسات مباشرة من محوّل الشبكة",
            padding=18,
        )
        self.table_metrics = QTableWidget(0, 4)
        self.table_metrics.setHorizontalHeaderLabels(["المقياس", "القيمة", "المصدر والموثوقية", "الملاحظة"])
        self.table_metrics.verticalHeader().setVisible(False)
        self.table_metrics.verticalHeader().setDefaultSectionSize(42)
        self.table_metrics.horizontalHeader().setMinimumHeight(46)
        self.table_metrics.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_metrics.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_metrics.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_metrics.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_metrics.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        fit_table_to_content(self.table_metrics)
        metrics_panel.main_layout.addWidget(self.table_metrics)
        self.root.addWidget(metrics_panel)

        # ------------------------------------------------------------------
        # 4. Searchable Nearby BSS Networks + WLAN AutoConfig Events
        # ------------------------------------------------------------------
        bss_panel = Panel(
            title="الشبكات المجاورة / Nearby Networks",
            subtitle="الشبكات المرصودة فعلياً حولك",
            padding=18,
        )
        self.bss_search = QLineEdit()
        self.bss_search.setPlaceholderText("ابحث باسم الشبكة (SSID) أو BSSID أو القناة...")
        self.bss_search.textChanged.connect(lambda _: self._render_bss_table())
        bss_panel.main_layout.addWidget(self.bss_search)

        self.table_bss = QTableWidget(0, 6)
        self.table_bss.setHorizontalHeaderLabels(["SSID", "BSSID", "النطاق", "القناة", "RSSI", "الأمان / العرض"])
        self.table_bss.verticalHeader().setVisible(False)
        self.table_bss.verticalHeader().setDefaultSectionSize(42)
        self.table_bss.horizontalHeader().setMinimumHeight(46)
        self.table_bss.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_bss.setSortingEnabled(True)
        self.table_bss.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        fit_table_to_content(self.table_bss)
        bss_panel.main_layout.addWidget(self.table_bss)

        self.table_wlan_events = QTableWidget(0, 4)
        self.table_wlan_events.setHorizontalHeaderLabels(["الوقت", "Event ID", "النوع", "التفاصيل"])
        self.table_wlan_events.verticalHeader().setVisible(False)
        self.table_wlan_events.verticalHeader().setDefaultSectionSize(42)
        self.table_wlan_events.horizontalHeader().setMinimumHeight(46)
        self.table_wlan_events.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_wlan_events.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        fit_table_to_content(self.table_wlan_events)
        bss_panel.main_layout.addWidget(self.table_wlan_events)
        self.root.addWidget(bss_panel)

        language_manager().language_changed.connect(self.retranslate)

    @staticmethod
    def _mini_cell(label: str, initial: str) -> tuple[QFrame, QLabel]:
        card = QFrame()
        card.setStyleSheet(
            f"background-color: {tokens.SURFACE_INSET}; border: 1px solid {tokens.LINE}; border-radius: 8px;"
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(2)
        t = QLabel(label)
        t.setFont(tokens.get_sans_font(12, 500))
        t.setStyleSheet(f"color: {tokens.TEXT_MUTED}; border: none; background: transparent;")
        t.setWordWrap(True)
        v = QLabel(initial)
        v.setFont(tokens.get_mono_font(12, 600))
        v.setStyleSheet(f"color: {tokens.TEXT}; border: none; background: transparent;")
        v.setWordWrap(True)
        lay.addWidget(t)
        lay.addWidget(v)
        return card, v

    def retranslate(self) -> None:
        self.lbl_title.setText(tr("wifi_title"))
        self.lbl_sub.setText(tr("wifi_sub"))

    @staticmethod
    def _normalize_band(band: Any) -> str:
        s = str(band or "").strip()
        if "2.4" in s:
            return "2.4 GHz"
        if "6" in s:
            return "6 GHz"
        if "5" in s:
            return "5 GHz"
        return s or "5 GHz"

    @staticmethod
    def _quality_pct_from_penalty(penalty_score: Any) -> float:
        """Convert ChannelAnalysisEngine congestion penalty (0=clean) to intuitive 0..100 quality."""
        try:
            pen = max(0.0, float(penalty_score))
        except (TypeError, ValueError):
            return 0.0
        return round(max(5.0, min(100.0, 100.0 / (1.0 + pen / 14.0))), 1)

    def set_page_active(self, active: bool) -> None:
        self._page_active = bool(active)
        self._sync_auto_timer()

    def _sync_auto_timer(self) -> None:
        if self._page_active and hasattr(self, "chk_auto_scan") and self.chk_auto_scan.isChecked():
            if not self._auto_timer.isActive():
                self._auto_timer.start()
        elif self._auto_timer.isActive():
            self._auto_timer.stop()

    def _on_auto_timer_tick(self) -> None:
        if not self._page_active or self.bundle is None or self.bridge.is_busy("wifi_rf_scan"):
            return
        self.refresh_wifi_and_rf(force_active_scan=True)

    def _get_writable_router_adapter(self) -> Any:
        if self.bundle is None or not hasattr(self.bundle, "router_registry"):
            return None
        adapters = (
            self.bundle.router_registry.list_adapters()
            if hasattr(self.bundle.router_registry, "list_adapters")
            else []
        )
        for ad in adapters:
            try:
                if getattr(ad, "is_authenticated", False) and ad.capabilities().supports_channel_write:
                    return ad
            except Exception:
                continue
        return None

    def ensure_initial_scan(self) -> None:
        """Auto-run non-blocking cached/active Wi-Fi scan on first user visit."""
        self.set_page_active(True)
        if self._initial_scan_started or self.bundle is None:
            return
        self._initial_scan_started = True
        self.refresh_wifi_and_rf(force_active_scan=True)

    def _set_plain_summary(self, text: str) -> None:
        self.lbl_plain_summary.setText(tokens.bidi_isolate_mixed(text))
        avail_w = max(320, self.lbl_plain_summary.width() or (self.content_holder.width() - 76))
        h = self.lbl_plain_summary.heightForWidth(avail_w)
        if h > 0:
            self.lbl_plain_summary.setMinimumHeight(h + 4)
        self.lbl_plain_summary.updateGeometry()
        if hasattr(self, "_summary_box"):
            self._summary_box.updateGeometry()
            self._summary_box.adjustSize()
        self.content_holder.adjustSize()

    def _sync_band_button_label(self) -> None:
        if hasattr(self, "btn_optimize_channel"):
            self.btn_optimize_channel.setText(tokens.bidi_isolate_mixed(f"تحليل وتحسين قناة {self._selected_band}"))

    def _on_band_changed(self, idx: int, _label: str) -> None:
        self._user_picked_band = True
        self._selected_band = {0: "2.4 GHz", 1: "5 GHz", 2: "6 GHz"}.get(idx, "5 GHz")
        self._sync_band_button_label()
        self._render_band_views()

    def _execute_channel_change(
        self,
        *,
        writable_adapter: Any,
        band: str,
        curr_ch: Optional[int],
        rec_ch: int,
        q_curr: Optional[float],
        q_rec: float,
        interactive: bool,
    ) -> None:
        from app.wifi.models import RouterChangeProposal
        from app.ui.views.router_management_view import RouterChangePreviewDialog

        prop = RouterChangeProposal(
            proposal_id=f"ch_opt_{band}_{rec_ch}",
            category="wifi_channel",
            title=f"نقل قناة الواي فاي ({band}) إلى القناة {rec_ch}",
            target_field="channel",
            band=band,
            current_value=str(curr_ch or "Auto"),
            proposed_value=str(rec_ch),
            reason="تخفيف التداخل مع شبكات الجيران بناءً على المسح الفعلي للطيف الترددي",
            expected_impact="تقليل التقطيع وثبات السرعة واستجابة أفضل للمكالمات",
            risk_level="low",
            requires_reconnect_warning=True,
            supported_by_adapter=True,
            requires_manual_apply=False,
        )
        if interactive:
            dlg = RouterChangePreviewDialog(prop, parent=self)
            if dlg.exec() != QDialog.Accepted:
                return

        def _apply_done(res: Any) -> None:
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

            if ok:
                q_txt = f"من {q_curr:.0f}/100 إلى {q_rec:.0f}/100" if q_curr is not None else f"إلى جودة {q_rec:.0f}/100"
                self._last_improvement_note = (
                    f"تم تغيير قناة {band} على الراوتر فعلياً من قناة {curr_ch or 'Auto'} لقناة {rec_ch}! "
                    f"التداخل قل وجودة القناة اتحسنت {q_txt} عشان الشبكة تبقى أسرع وأثبت."
                )
                self.lbl_plain_summary.setText(tokens.bidi_isolate_mixed(self._last_improvement_note))
                if interactive:
                    QMessageBox.information(self, "تم تحسين القناة ✓", self._last_improvement_note)
            elif interactive:
                reason_txt = msg or "لم يرجع الراوتر تأكيداً بتثبيت القناة الجديدة (تحقق من وضع التشغيل أو صلاحيات الراوتر)."
                QMessageBox.information(self, "تعذر تغيير القناة", f"لم يتم تأكيد التغيير على الراوتر:\n{reason_txt}")
            self.refresh_wifi_and_rf(force_active_scan=True)

        async def _apply_work():
            return await asyncio.to_thread(
                self.bundle.optimization.execute_proposal,
                adapter=writable_adapter,
                proposal=prop,
                explicit_user_approval=True,
            )

        self.bridge.run_coro(
            _apply_work,
            _apply_done,
            lambda err: QMessageBox.warning(self, "خطأ في تعديل الراوتر", err) if interactive else None,
            op_key="wifi_apply_channel",
            timeout_sec=25.0,
        )

    def analyze_and_optimize_channel(self) -> None:
        """Evaluate channel congestion on selected band and execute or guide optimization honestly."""
        if self._last_ch_report is None:
            self.refresh_wifi_and_rf(force_active_scan=True)
            return
        self._render_band_views()
        band = self._normalize_band(self._selected_band)
        bands_dict = getattr(self._last_ch_report, "bands", None) or {}
        band_rep = bands_dict.get(band)
        if band_rep is None:
            attr_map = {"2.4 GHz": "band_24", "5 GHz": "band_5", "6 GHz": "band_6"}
            band_rep = getattr(self._last_ch_report, attr_map.get(band, ""), None)

        recs = list(getattr(band_rep, "recommended_channels", []) or []) if band_rep else []
        candidates = list(getattr(band_rep, "channel_scores", None) or getattr(band_rep, "candidates", []) or []) if band_rep else []
        rec_ch = getattr(recs[0], "channel", None) if recs else getattr(band_rep, "recommended_channel", None)
        curr_ch = (
            getattr(self._last_tel, "channel", None)
            if (self._last_tel and self._normalize_band(getattr(self._last_tel, "band", "")) == band)
            else None
        )
        if rec_ch is None:
            self._set_scan_status("completed_limited", f"لا توجد بيانات كافية لاختيار قناة في نطاق {band}.")
            return

        cur_score_obj = next((c for c in candidates if getattr(c, "channel", None) == curr_ch), None)
        rec_score_obj = next((c for c in candidates if getattr(c, "channel", None) == rec_ch), None)
        q_cur = self._quality_pct_from_penalty(getattr(cur_score_obj, "total_score", getattr(cur_score_obj, "score", 0.0))) if cur_score_obj else None
        q_rec = self._quality_pct_from_penalty(getattr(rec_score_obj, "total_score", getattr(rec_score_obj, "score", 0.0))) if rec_score_obj else 95.0

        if curr_ch == rec_ch or (q_cur is not None and (q_rec - q_cur) < 3.0):
            msg = f"تمام جداً: شبكتك على ({band}) شغالة حالياً على قناة ممتازة (CH {curr_ch}) بجودة {q_cur or q_rec:.0f}/100 ومش محتاجة تغيير."
            self.lbl_ch_rec.setText(tokens.bidi_isolate_mixed(msg))
            self.lbl_plain_summary.setText(tokens.bidi_isolate_mixed(msg))
            QMessageBox.information(self, "تحليل القناة / Channel Analysis", msg)
            return

        writable_adapter = self._get_writable_router_adapter()
        if writable_adapter is not None and hasattr(self.bundle, "optimization"):
            self._execute_channel_change(
                writable_adapter=writable_adapter,
                band=band,
                curr_ch=curr_ch,
                rec_ch=int(rec_ch),
                q_curr=q_cur,
                q_rec=q_rec,
                interactive=True,
            )
            return

        plain_hint = (
            f"شبكتك على ({band}) حالياً على قناة {curr_ch or '—'} "
            + (f"(جودة {q_cur:.0f}/100) " if q_cur is not None else "")
            + f"والأفضل تنقل على قناة {rec_ch} (جودة {q_rec:.0f}/100) عشان التداخل يقل.\n\n"
            "للتغيير المباشر من البرنامج: افتح تبويب (إدارة الراوتر)، اكتب كلمة مرور الراوتر واضغط (اتصال بالراوتر)، وبعدها التعديل هيتطبق تلقائياً من هنا."
        )
        self.lbl_ch_rec.setText(tokens.bidi_isolate_mixed(f"{band}: الأفضل النقل إلى CH {rec_ch} (جودة {q_rec:.0f}/100)"))
        self.lbl_plain_summary.setText(tokens.bidi_isolate_mixed(plain_hint.splitlines()[0]))
        QMessageBox.information(self, "توصية تحسين القناة", plain_hint)

    def _set_scan_status(self, state: str, detail: str = "") -> None:
        self._scan_state = state
        status_map = {
            "not_started": (tokens.SystemStatus.WAITING, "لم يبدأ المسح"),
            "scanning": (tokens.SystemStatus.RUNNING, "جاري المسح..."),
            "completed": (tokens.SystemStatus.HEALTHY, "اكتمل المسح"),
            "completed_limited": (tokens.SystemStatus.WARNING, "اكتمل بمحددات"),
            "failed": (tokens.SystemStatus.FAILED, "فشل المسح"),
            "cancelled": (tokens.SystemStatus.WAITING, "تم الإلغاء"),
        }
        st_enum, st_lbl = status_map.get(state, (tokens.SystemStatus.WAITING, state))
        self.badge_scan_state.set_status(st_enum, st_lbl)
        if detail:
            self.lbl_scan_status_detail.setText(tokens.bidi_isolate_mixed(detail))
        show_retry = state in ("failed", "completed_limited") or (
            state == "completed" and not (getattr(self._last_scan, "access_points", None) or [])
        )
        self.btn_retry_scan.setVisible(bool(show_retry))

    def refresh_wifi_and_rf(self, *, force_active_scan: bool = True) -> None:
        if self.bundle is None:
            self._set_scan_status("failed", "وحدة تحليل الواي فاي غير متاحة في هذا الوضع.")
            return
        if self.bridge.is_busy("wifi_rf_scan"):
            return
        self.btn_rf_refresh.setEnabled(False)
        self.btn_retry_scan.setEnabled(False)
        self.badge_wifi.set_status(tokens.SystemStatus.RUNNING, tr("status.running"))
        self._set_scan_status("scanning", "جاري جمع قياسات نقطة الاتصال ومسح الشبكات المجاورة...")

        async def _work():
            scan = await self.bundle.scanner.scan(request_active_scan=bool(force_active_scan))
            tel = await self.bundle.telemetry.collect_telemetry(
                include_events=False,
                include_ps_driver_stats=False,
                trigger_active_scan=False,
            )
            ch_rep = self.bundle.channel_analyzer.analyze(
                scan_result=scan,
                current_band=self._normalize_band(getattr(tel, "band", None)),
                current_channel=getattr(tel, "channel", None),
                connected_bssid=getattr(tel, "bssid", None),
                adapter_caps=getattr(tel, "capabilities", getattr(tel, "adapter_capabilities", None)),
            )
            return tel, scan, ch_rep

        def _done(res: Any) -> None:
            self.btn_rf_refresh.setEnabled(True)
            self.btn_retry_scan.setEnabled(True)
            tel, scan, ch_rep = res
            self._last_tel = tel
            self._last_scan = scan
            self._last_ch_report = ch_rep
            self._initial_scan_started = True
            aps = list(getattr(scan, "access_points", []) or [])
            scan_notes = list(getattr(scan, "scan_notes", []) or [])
            if getattr(scan, "error", None):
                self._set_scan_status("failed", str(scan.error))
            elif scan_notes:
                self._set_scan_status(
                    "completed_limited",
                    f"تم رصد {len(aps)} نقطة وصول · ملاحظة: {'; '.join(scan_notes[:2])}",
                )
            elif not aps:
                self._set_scan_status(
                    "completed_limited",
                    "لم ترصد واجهة Windows نقاط وصول مجاورة (قد يكون الموقع الجغرافي مغلقاً أو البث مقيداً).",
                )
            else:
                self._set_scan_status("completed", f"تم رصد {len(aps)} نقطة وصول مجاورة حقيقية بنجاح.")
            self._render_telemetry(tel)
            self._render_band_views()
            self._render_bss_table()
            self.wifi_telemetry_updated.emit(tel)

        def _err(msg: str) -> None:
            self.btn_rf_refresh.setEnabled(True)
            self.btn_retry_scan.setEnabled(True)
            self.badge_wifi.set_status(tokens.SystemStatus.FAILED, tr("status.failed"))
            self._set_scan_status("failed", msg)
            self.lbl_ch_rec.setText(tokens.bidi_isolate_mixed(msg))

        self.bridge.run_coro(_work, _done, _err, op_key="wifi_rf_scan", timeout_sec=18.0)

    def _render_telemetry(self, tel: Any) -> None:
        if tel is None:
            return
        conn_state = str(getattr(tel, "connection_state", "") or "").lower()
        connected = bool(getattr(tel, "connected", False)) or conn_state == "connected" or bool(getattr(tel, "ssid", None))
        rssi = getattr(tel, "rssi_dbm", None)
        raw_sig_pct = getattr(tel, "signal_quality_pct", getattr(tel, "signal_percent", None))
        sig_pct = float(raw_sig_pct) if raw_sig_pct is not None else None
        noise_dbm = getattr(tel, "noise_floor_dbm", getattr(tel, "noise_dbm", None))
        snr = getattr(tel, "snr_db", None)
        # Never invent SNR if Noise Floor is unavailable
        if noise_dbm is None:
            snr = None
        elif snr is None and rssi is not None:
            snr = int(round(float(rssi) - float(noise_dbm)))

        if connected and sig_pct is not None:
            col = tokens.STATUS_OK if sig_pct >= 70 else (tokens.STATUS_WARN if sig_pct >= 45 else tokens.STATUS_BAD)
            self.wifi_gauge.set_value(float(sig_pct), subtitle=f"RSSI: {rssi} dBm" if rssi is not None else tr("status.active"), color=col)
            self.badge_wifi.set_status(tokens.SystemStatus.HEALTHY if sig_pct >= 65 else tokens.SystemStatus.WARNING, tr("status.active"))
        elif connected:
            self.wifi_gauge.set_value(None, subtitle=f"RSSI: {rssi} dBm" if rssi is not None else str(getattr(tel, "ssid", None) or tr("status.active")))
            self.badge_wifi.set_status(tokens.SystemStatus.RUNNING, tr("status.active"))
        else:
            self.wifi_gauge.set_value(None, subtitle=tr("status.not_connected"))
            self.badge_wifi.set_status(tokens.SystemStatus.NOT_CONNECTED, tr("status.not_connected"))

        self._ap_ssid[1].setText(tokens.bidi_isolate_mixed(str(getattr(tel, "ssid", None) or "—")))
        raw_band = getattr(tel, "band", None)
        band = self._normalize_band(raw_band) if raw_band else "—"
        if raw_band and not self._user_picked_band and band in ("2.4 GHz", "5 GHz", "6 GHz"):
            band_idx = {"2.4 GHz": 0, "5 GHz": 1, "6 GHz": 2}[band]
            if self._selected_band != band:
                self._selected_band = band
                self.band_switch.set_selected_index(band_idx)
                self._sync_band_button_label()
        ch = getattr(tel, "channel", None)
        self._ap_band_ch[1].setText(tokens.bidi_isolate(f"{band} · CH {ch or '—'}"))
        rssi_part = f"RSSI: {rssi} dBm" if rssi is not None else "RSSI: —"
        snr_part = f"SNR: {snr} dB" if snr is not None else "SNR: غير متاح"
        self._ap_rssi_snr[1].setText(tokens.bidi_isolate_mixed(f"{rssi_part} · {snr_part}"))
        rx_r = getattr(tel, "rx_link_rate_mbps", getattr(tel, "rx_rate_mbps", None))
        tx_r = getattr(tel, "tx_link_rate_mbps", getattr(tel, "tx_rate_mbps", None))
        self._ap_phy[1].setText(tokens.bidi_isolate(f"{rx_r or '—'} / {tx_r or '—'} Mbps"))

        if sig_pct is not None:
            self._rssi_history.append(float(sig_pct))
            self._rssi_timestamps.append(datetime.now().strftime("%H:%M:%S"))
            self._rssi_history = self._rssi_history[-60:]
            self._rssi_timestamps = self._rssi_timestamps[-60:]
            self.rssi_canvas.timestamps = list(self._rssi_timestamps)
            self.rssi_canvas.set_data(self._rssi_history)

        # Build 16-metric table with explicit provenance & strictly separated RF units
        radio_std = getattr(tel, "phy_standard", getattr(tel, "radio_type", None))
        sec_mode = getattr(tel, "security_mode", None)
        if not sec_mode and (getattr(tel, "authentication", None) or getattr(tel, "cipher", None)):
            sec_mode = f"{getattr(tel, 'authentication', None) or '—'} / {getattr(tel, 'cipher', None) or '—'}"
        stats_obj = getattr(tel, "interface_stats", None)
        retries = getattr(tel, "tx_retries", None)
        if retries is None and stats_obj is not None:
            retries = getattr(stats_obj, "phy_retry_count", None)
            if retries is None:
                retries = getattr(stats_obj, "tx_errors", None)
        events = list(getattr(tel, "recent_wlan_events", None) or getattr(tel, "events", None) or [])

        metrics_rows = [
            ("SSID", getattr(tel, "ssid", None), "Measured", "Windows WLAN Interface"),
            ("BSSID", getattr(tel, "bssid", None), "Measured", "Connected AP Radio MAC"),
            ("Interface Name", getattr(tel, "interface_name", None), "Measured", "Active Adapter"),
            ("Standard / Radio", radio_std, "Measured", "802.11 PHY Mode"),
            ("Band", getattr(tel, "band", None), "Measured", "RF Spectrum"),
            ("Channel", getattr(tel, "channel", None), "Measured", "Operating Center Channel"),
            ("Channel Width (MHz)", getattr(tel, "channel_width_mhz", None), "Inferred" if getattr(tel, "channel_width_mhz", None) else "Unavailable", "IE / Driver Capabilities"),
            ("Signal Quality (%)", raw_sig_pct, "Measured" if raw_sig_pct is not None else "Unavailable", "Windows WLAN API % (0–100)"),
            ("RSSI (dBm)", rssi, "Measured" if rssi is not None else "Unavailable", "Received Signal Strength (dBm)"),
            ("Noise Floor (dBm)", noise_dbm, "Measured" if noise_dbm is not None else "Unavailable", "Adapter Noise Floor (dBm)"),
            ("SNR (dB)", snr, "Inferred" if snr is not None else "Unavailable", "Computed only when Noise Floor is measured"),
            ("PHY Receive Rate (Mbps)", rx_r, "Measured", "Negotiated Link Rate (not ISP throughput)"),
            ("PHY Transmit Rate (Mbps)", tx_r, "Measured", "Negotiated Uplink PHY"),
            ("Security Mode", sec_mode, "Measured" if sec_mode else "Unavailable", "WLAN Security"),
            ("Retries / Packet Errors", retries, "Measured" if retries is not None else "Unavailable", "NDIS / Driver Stats"),
            ("Roaming Events", len(events), "Measured", "Microsoft-Windows-WLAN-AutoConfig"),
        ]
        self.table_metrics.setRowCount(len(metrics_rows))
        for r, (name, val, prov, note) in enumerate(metrics_rows):
            v_str = str(val) if val is not None and str(val) != "" else tr("status.unavailable")
            p_actual = "Unavailable" if val is None or str(val) == "" else prov
            self.table_metrics.setItem(r, 0, QTableWidgetItem(name))
            self.table_metrics.setItem(r, 1, QTableWidgetItem(tokens.bidi_isolate_mixed(v_str)))
            p_item = QTableWidgetItem(p_actual)
            p_item.setForeground(
                Qt.GlobalColor.green if p_actual == "Measured" else (Qt.GlobalColor.yellow if p_actual == "Inferred" else Qt.GlobalColor.gray)
            )
            self.table_metrics.setItem(r, 2, p_item)
            self.table_metrics.setItem(r, 3, QTableWidgetItem(note))
        fit_table_to_content(self.table_metrics)

        self.table_wlan_events.setRowCount(len(events[:20]))
        f14 = tokens.get_sans_font(14, 400)
        for r, ev in enumerate(events[:20]):
            for col_i, txt_val in enumerate((
                tokens.bidi_isolate(str(getattr(ev, "timestamp", "—"))),
                tokens.bidi_isolate(str(getattr(ev, "event_id", "—"))),
                str(getattr(ev, "event_type", getattr(ev, "level", getattr(ev, "category", "Info")))),
                tokens.bidi_isolate_mixed(str(getattr(ev, "message", ""))),
            )):
                cell_it = QTableWidgetItem(txt_val)
                cell_it.setFont(f14)
                self.table_wlan_events.setItem(r, col_i, cell_it)
        fit_table_to_content(self.table_wlan_events)

    def _render_band_views(self) -> None:
        if not self._last_scan or not self._last_ch_report:
            return
        band = self._normalize_band(self._selected_band)
        aps = [
            ap
            for ap in (getattr(self._last_scan, "access_points", []) or [])
            if self._normalize_band(getattr(ap, "band", "")) == band
        ]
        rec_ch = None
        curr_ch = (
            getattr(self._last_tel, "channel", None)
            if (self._last_tel and self._normalize_band(getattr(self._last_tel, "band", "")) == band)
            else None
        )

        bands_dict = getattr(self._last_ch_report, "bands", None) or {}
        band_rep = bands_dict.get(band)
        if band_rep is None:
            attr_map = {"2.4 GHz": "band_24", "5 GHz": "band_5", "6 GHz": "band_6"}
            band_rep = getattr(self._last_ch_report, attr_map.get(band, ""), None)

        candidates = list(
            getattr(band_rep, "channel_scores", None) or getattr(band_rep, "candidates", []) or []
        ) if band_rep else []
        recs = list(getattr(band_rep, "recommended_channels", []) or []) if band_rep else []
        if recs:
            rec_ch = getattr(recs[0], "channel", None)
            reason = getattr(recs[0], "reason", "")
        elif band_rep is not None:
            rec_ch = getattr(band_rep, "recommended_channel", None)
            reason = getattr(band_rep, "recommendation_reason", "")
        else:
            rec_ch = curr_ch
            reason = "لم ترصد نقاط وصول إضافية في هذا النطاق."

        cur_obj = next((c for c in candidates if getattr(c, "channel", None) == curr_ch), None)
        rec_obj = next((c for c in candidates if getattr(c, "channel", None) == rec_ch), None)
        q_cur = self._quality_pct_from_penalty(getattr(cur_obj, "total_score", getattr(cur_obj, "score", 0.0))) if cur_obj else None
        q_rec = self._quality_pct_from_penalty(getattr(rec_obj, "total_score", getattr(rec_obj, "score", 0.0))) if rec_obj else 95.0
        co_cur = getattr(cur_obj, "co_channel_ap_count", 0) if cur_obj else 0

        if self._last_improvement_note:
            self._set_plain_summary(self._last_improvement_note)
        elif curr_ch is not None and rec_ch is not None:
            if curr_ch == rec_ch or (q_cur is not None and (q_rec - q_cur) < 3.0):
                self._set_plain_summary(
                    f"شبكتك على ({band}) شغالة حالياً على قناة ممتازة (CH {curr_ch}) بجودة {q_cur or q_rec:.0f}/100 ومفيش داعي تغيّرها. (تقدر تبدّل بين 2.4 GHz و 5 GHz من الأزرار تحت)"
                )
            else:
                self._set_plain_summary(
                    f"شبكتك دلوقتي على ({band}) قناة {curr_ch} (معاها {co_cur} شبكة في نفس القناة، جودة {q_cur or 70:.0f}/100) "
                    f"— الأفضل تنقل على قناة {rec_ch} (جودة {q_rec:.0f}/100) عشان التقطيع يقل والنت يثبت."
                )
        elif rec_ch is not None:
            self._set_plain_summary(
                f"تحليل نطاق ({band}): تم رصد {len(aps)} شبكة مجاورة، وأنسب قناة هادئة حالياً هي CH {rec_ch} (جودة {q_rec:.0f}/100). اضغط (تحليل وتحسين قناة {band}) لتطبيقها."
            )

        if rec_ch is not None or band_rep is not None:
            self.lbl_ch_rec.setText(
                tokens.bidi_isolate_mixed(
                    f"{band}: القناة المقترحة CH {rec_ch or curr_ch or '—'} (جودة {q_rec:.0f}/100)"
                )
            )

        self.spectrum_chart.set_data(
            band=band,
            access_points=aps,
            current_channel=curr_ch,
            recommended_channel=rec_ch,
        )

        self.table_channels.setRowCount(len(candidates))
        for r, c in enumerate(candidates):
            ch_num = getattr(c, "channel", "—")
            raw_pen = getattr(c, "total_score", getattr(c, "score", 0.0))
            qual_pct = self._quality_pct_from_penalty(raw_pen)
            co = getattr(c, "co_channel_ap_count", getattr(c, "co_channel_aps", 0))
            adj = getattr(c, "overlapping_ap_count", getattr(c, "adjacent_aps", 0))
            is_best = ch_num == rec_ch
            self.table_channels.setItem(r, 0, QTableWidgetItem(tokens.bidi_isolate(f"CH {ch_num}")))
            self.table_channels.setItem(r, 1, QTableWidgetItem(tokens.bidi_isolate(f"{qual_pct:.0f} / 100")))
            self.table_channels.setItem(r, 2, QTableWidgetItem(tokens.bidi_isolate(f"مشترك: {co} · مجاور: {adj}")))
            self.table_channels.setItem(r, 3, QTableWidgetItem("مقترحة ★" if is_best else "متاحة"))
        fit_table_to_content(self.table_channels)

        # Optional automatic router channel optimization (only if user opted in, idle from calls, >=10pt gain, cooldown elapsed)
        if (
            hasattr(self, "chk_auto_optimize")
            and self.chk_auto_optimize.isChecked()
            and curr_ch is not None
            and rec_ch is not None
            and int(rec_ch) != int(curr_ch)
            and q_cur is not None
            and (q_rec - q_cur) >= 10.0
        ):
            now_m = time.monotonic()
            if (now_m - self._last_auto_opt_at.get(band, 0.0)) >= 120.0:
                writable = self._get_writable_router_adapter()
                if writable is not None and hasattr(self.bundle, "optimization"):
                    self._last_auto_opt_at[band] = now_m
                    self._execute_channel_change(
                        writable_adapter=writable,
                        band=band,
                        curr_ch=int(curr_ch),
                        rec_ch=int(rec_ch),
                        q_curr=q_cur,
                        q_rec=q_rec,
                        interactive=False,
                    )

    def _render_bss_table(self) -> None:
        if not self._last_scan:
            return
        q = self.bss_search.text().strip().lower()
        aps = list(getattr(self._last_scan, "access_points", []) or [])
        filtered = []
        for ap in aps:
            ssid = str(getattr(ap, "ssid", "") or "")
            bssid = str(getattr(ap, "bssid", "") or "")
            ch = str(getattr(ap, "channel", "") or "")
            if q and q not in ssid.lower() and q not in bssid.lower() and q not in ch:
                continue
            filtered.append(ap)

        self.table_bss.setSortingEnabled(False)
        self.table_bss.setRowCount(len(filtered))
        for r, ap in enumerate(filtered):
            self.table_bss.setItem(r, 0, QTableWidgetItem(tokens.bidi_isolate_mixed(getattr(ap, "ssid", "") or "<Hidden>")))
            self.table_bss.setItem(r, 1, QTableWidgetItem(tokens.bidi_isolate(getattr(ap, "bssid", "") or "—")))
            self.table_bss.setItem(r, 2, QTableWidgetItem(tokens.bidi_isolate(getattr(ap, "band", "") or "—")))
            self.table_bss.setItem(r, 3, QTableWidgetItem(tokens.bidi_isolate(str(getattr(ap, "channel", "—")))))
            rssi = getattr(ap, "rssi_dbm", None)
            self.table_bss.setItem(r, 4, QTableWidgetItem(tokens.bidi_isolate(f"{rssi} dBm" if rssi is not None else "—")))
            sec = f"{getattr(ap, 'security', '—')} · {getattr(ap, 'channel_width_mhz', '—')} MHz"
            self.table_bss.setItem(r, 5, QTableWidgetItem(tokens.bidi_isolate(sec)))
        self.table_bss.setSortingEnabled(True)
        fit_table_to_content(self.table_bss)

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
        if hasattr(self, "_auto_timer"):
            self._auto_timer.stop()
        self.bridge.shutdown()
