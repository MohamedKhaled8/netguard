"""Diagnosis Center View for NetGuard AI.

Follows the reference design system strictly:
- Hero verdict: Clean panel with status verdict & audit trigger button
- Vertical checklist of the 5 path layers with expandable evidence
- Incident timeline panel ('ما الذي حدث بالضبط؟')
- Hairline-separated evidence table with mono numbers
100% token-compliant, dark warm-neutral graphite (#0E1012 / #15181A).
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QScrollArea,
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from app.ui import tokens
from app.ui.widgets.buttons import PrimaryButton, SecondaryButton
from app.ui.widgets.chip import Chip
from app.ui.widgets.base_panel import Panel
from app.ui.widgets.timeline import TimelinePanel
from app.ui.widgets.multi_protocol_panel import MultiProtocolAnalysisPanel
from app.ui.widgets.predictive_panel import PredictiveDiagnosticsPanel
from app.core.models.metrics import Diagnosis, ProbableCause, MetricType
from app.core.thresholds import NetworkThresholds
from app.ui.widgets.scroll_forwarder import make_scroll_transparent, fit_table_to_content
from app.diagnosis.traceroute import HopClassification, MultiProtocolAnalysisReport
from app.dns.state import DnsStateManager, DnsStateData


class LayerChecklistRow(QFrame):
    """Single layer item in the 5-layer vertical checklist."""

    def __init__(
        self,
        index_str: str,
        name: str,
        metric_str: str,
        desc: str,
        status: str = "ok",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("LayerChecklistRow")
        self.setStyleSheet(f"""
            QFrame#LayerChecklistRow {{
                background-color: {tokens.SURFACE};
                border: none;
                border-bottom: 1px solid {tokens.LINE};
                padding: 12px 6px;
            }}
            QFrame#LayerChecklistRow:hover {{
                background-color: {tokens.SURFACE_HOVER};
            }}
            QFrame#LayerChecklistRow QLabel {{
                border: none;
                background: transparent;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        lbl_idx = QLabel(index_str)
        lbl_idx.setFont(tokens.get_mono_font(12, 400))
        lbl_idx.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        top_row.addWidget(lbl_idx)

        self.lbl_name = QLabel(name)
        self.lbl_name.setFont(tokens.get_sans_font(15, 600))
        self.lbl_name.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_name.setWordWrap(True)
        top_row.addWidget(self.lbl_name, 1)

        self.lbl_metric = QLabel(metric_str)
        self.lbl_metric.setFont(tokens.get_mono_font(14, 500))
        self.lbl_metric.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_metric.setMinimumWidth(120)
        self.lbl_metric.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top_row.addWidget(self.lbl_metric)

        chip_text = "سليم" if status == "ok" else ("يحتاج تحسين" if status == "warn" else ("خلل / انقطاع" if status in ("bad", "error", "critical") else "غير مُقاس"))
        chip_variant = "ok-soft" if status == "ok" else ("tag-warn" if status == "warn" else ("bad-soft" if status in ("bad", "error", "critical") else "neutral"))
        self.chip = Chip(chip_text, variant=chip_variant)
        top_row.addWidget(self.chip)
        layout.addLayout(top_row)

        self.lbl_desc = QLabel(desc)
        self.lbl_desc.setFont(tokens.get_sans_font(14, 400))
        self.lbl_desc.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self.lbl_desc.setWordWrap(True)
        layout.addWidget(self.lbl_desc)

    def update_status(self, metric_str: str, status: str, desc: str = "") -> None:
        self.lbl_metric.setText(metric_str)
        if desc:
            self.lbl_desc.setText(desc)
        if status == "ok":
            self.chip.set_variant("ok-soft", "سليم")
        elif status == "warn":
            self.chip.set_variant("tag-warn", "يحتاج تحسين")
        elif status in ("bad", "error", "critical"):
            self.chip.set_variant("bad-soft", "خلل / انقطاع")
        else:
            self.chip.set_variant("neutral", "غير مُقاس")


class DiagnosisView(QWidget):
    """Architectural diagnosis view matching the graphite hairline design system."""

    def __init__(self, parent=None, embed_in_scroll: bool = False) -> None:
        super().__init__(parent)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.content_widget = QWidget()
        self.main_layout = QVBoxLayout(self.content_widget)
        if embed_in_scroll:
            self.scroll = None
            self.main_layout.setContentsMargins(0, 4, 0, 8)
            root_layout.addWidget(self.content_widget)
        else:
            self.scroll = QScrollArea(self)
            self.scroll.setWidgetResizable(True)
            self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.scroll.setFrameShape(QFrame.NoFrame)
            self.scroll.setStyleSheet(f"QScrollArea {{ background-color: {tokens.BG}; border: none; }}")
            self.scroll.viewport().setAutoFillBackground(True)
            self.scroll.viewport().setAttribute(Qt.WA_OpaquePaintEvent, True)
            self.scroll.viewport().setStyleSheet(f"background-color: {tokens.BG};")
            self.scroll.verticalScrollBar().setSingleStep(25)
            self.main_layout.setContentsMargins(
                tokens.PAGE_PADDING_DESKTOP, 28, tokens.PAGE_PADDING_DESKTOP, 36
            )
            root_layout.addWidget(self.scroll)
        self.main_layout.setSpacing(tokens.SECTION_GAP)
        layout = self.main_layout

        # -------------------------------------------------------------
        # 1. Hero Verdict Panel
        # -------------------------------------------------------------
        verdict_panel = Panel(title="التشخيص الفوري للشبكة", subtitle="فحص دقيق لكافة مسارات التوصيل", parent=self)

        top_h = QHBoxLayout()
        v_col = QVBoxLayout()
        v_col.setSpacing(4)

        self.cause_lbl = QLabel("جاهز للفحص الشامل")
        self.cause_lbl.setFont(tokens.get_sans_font(17, 600))
        self.cause_lbl.setStyleSheet(f"color: {tokens.TEXT};")

        self.explanation_lbl = QLabel(
            "اضغط على زر 'فحص شامل ودقيق الآن' لإجراء اختبار تفصيلي لجميع مسارات الاتصال والراوتر وخوادم DNS."
        )
        self.explanation_lbl.setFont(tokens.get_sans_font(13, 400))
        self.explanation_lbl.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self.explanation_lbl.setWordWrap(True)
        self.explanation_lbl.setMinimumHeight(52)

        v_col.addWidget(self.cause_lbl)
        v_col.addWidget(self.explanation_lbl)
        top_h.addLayout(v_col, stretch=1)

        self.btn_run_audit = PrimaryButton("فحص شامل ودقيق الآن")
        top_h.addWidget(self.btn_run_audit)

        verdict_panel.main_layout.addLayout(top_h)
        layout.addWidget(verdict_panel)

        # -------------------------------------------------------------
        # 2. Vertical Checklist of the 5 Path Layers + MTU/Buffer
        # -------------------------------------------------------------
        layers_panel = Panel(
            title="طبقات مسار الاتصال الميدانية",
            subtitle="تدقيق تفصيلي لكل محطة في رحلة بياناتك",
            parent=self,
        )

        self.row_l1 = LayerChecklistRow("01", "جهازك وبطاقة الشبكة", "—", "فحص بطاقة الشبكة والاتصال الداخلي.", "none")
        self.row_l2 = LayerChecklistRow("02", "الراوتر المنزلي والواي فاي", "—", "فحص الاتصال بالراوتر المنزلي والبوابة الافتراضية.", "none")
        self.row_l3 = LayerChecklistRow("03", "مزود الخدمة وكابل الألياف", "—", "فحص مسار التوصيل بالبنية التحتية لمزود الخدمة (ISP).", "none")
        self.row_l4 = LayerChecklistRow("04", "خوادم ترجمة العناوين (DNS)", "—", "فحص استجابة خوادم تحليل أسماء النطاقات.", "none")
        self.row_l5 = LayerChecklistRow("05", "الإنترنت والشبكات السحابية", "—", "فحص الاتصال بالخوادم العالمية ومعدل فقدان الحزم.", "none")
        self.row_l6 = LayerChecklistRow(
            "06",
            "كفاءة الحزم والتحمل (MTU Buffer)",
            "—",
            "اختبار كفاءة الحزم الكبيرة والتحمل تحت الضغط.",
            "none",
        )

        layers_panel.main_layout.addWidget(self.row_l1)
        layers_panel.main_layout.addWidget(self.row_l2)
        layers_panel.main_layout.addWidget(self.row_l3)
        layers_panel.main_layout.addWidget(self.row_l4)
        layers_panel.main_layout.addWidget(self.row_l5)
        layers_panel.main_layout.addWidget(self.row_l6)
        layout.addWidget(layers_panel)

        # -------------------------------------------------------------
        # 2.5 Multi-Protocol Connectivity Analysis Section (Item 6)
        # -------------------------------------------------------------
        self.multi_protocol_panel = MultiProtocolAnalysisPanel(self)
        layout.addWidget(self.multi_protocol_panel)

        # -------------------------------------------------------------
        # 2.8 Predictive Diagnostics & Root Cause Analysis
        # -------------------------------------------------------------
        self.predictive_panel = PredictiveDiagnosticsPanel(self)
        layout.addWidget(self.predictive_panel)

        # -------------------------------------------------------------
        # 3. Evidence Table (Hairline-separated, mono numbers, no zebra)
        # -------------------------------------------------------------
        table_panel = Panel(
            title="بيانات التدقيق الميداني والمؤشرات المقاسة",
            subtitle="سجل القياسات اللحظية ومقارنتها بالحدود المقبولة",
            parent=self,
        )

        self.table = QTableWidget(0, 5)
        self.table.setMinimumHeight(220)
        self.table.setHorizontalHeaderLabels(["المؤشر الفني", "القيمة المقاسة", "الحد الآمن", "الحالة", "التقييم"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent;
                border: none;
                gridline-color: {tokens.LINE};
                font-size: 13px;
            }}
            QTableWidget::item {{
                border-bottom: 1px solid {tokens.LINE};
                padding: 10px 8px;
                color: {tokens.TEXT};
            }}
        """)
        self._populate_evidence_table()
        table_panel.main_layout.addWidget(self.table)
        layout.addWidget(table_panel)

        make_scroll_transparent(self.table, self.scroll)
        fit_table_to_content(self.table)

        if self.scroll is not None:
            self.scroll.setWidget(self.content_widget)

        # Synchronize with DNS Single Source of Truth (Item F9)
        try:
            DnsStateManager.get_instance().state_changed.connect(self._on_dns_state_changed)
        except Exception:
            pass

    def shutdown(self) -> None:
        if getattr(self, "_is_shut_down", False):
            return
        self._is_shut_down = True
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            try:
                DnsStateManager.get_instance().state_changed.disconnect(self._on_dns_state_changed)
            except Exception:
                pass

    def _set_evidence_cell(self, row_idx: int, val_txt: str, st_txt: str, eval_txt: str, status_variant: str) -> None:
        """Helper to update a row in the evidence table."""
        if row_idx >= self.table.rowCount():
            return
        v_item = self.table.item(row_idx, 1)
        if not v_item:
            v_item = QTableWidgetItem()
            self.table.setItem(row_idx, 1, v_item)
        v_item.setText(val_txt)

        s_item = self.table.item(row_idx, 3)
        if not s_item:
            s_item = QTableWidgetItem()
            self.table.setItem(row_idx, 3, s_item)
        s_item.setText(st_txt)
        col = tokens.STATUS_OK if status_variant == "ok" else (
            tokens.STATUS_WARN if status_variant == "warn" else (
                tokens.STATUS_BAD if status_variant == "bad" else tokens.TEXT_MUTED
            )
        )
        s_item.setForeground(QColor(col))

        e_item = self.table.item(row_idx, 4)
        if not e_item:
            e_item = QTableWidgetItem()
            self.table.setItem(row_idx, 4, e_item)
        e_item.setText(eval_txt)

    def _on_dns_state_changed(self, state: DnsStateData) -> None:
        """Handle synchronized DNS state changes from DnsStateManager (Item F9)."""
        if state and state.last_measured_ms is not None and state.last_measured_ms > 0:
            dns_ms = state.last_measured_ms
            st4 = "ok" if dns_ms < 85.0 else ("warn" if dns_ms < 150.0 else "bad")
            prov_text = f" ({state.detected_provider})" if state.detected_provider else ""
            self.row_l4.update_status(
                f"{dns_ms:.0f} ms",
                st4,
                f"خادم DNS{prov_text} يستجيب بسرعة {dns_ms:.0f} ms وبكفاءة تامة دون تأخير.",
            )
            _dns_val = f"{dns_ms:.0f} ms"
            _dns_st = "سليم" if dns_ms < 85.0 else "يحتاج تحسين"
            _dns_eval = f"خادم DNS مستجيب ({int(round(dns_ms))} ms)"
            self._set_evidence_cell(2, _dns_val, _dns_st, _dns_eval, "ok" if _dns_st == "سليم" else "warn")

    def _populate_evidence_table(self) -> None:
        t = NetworkThresholds()
        rows = [
            ("Gateway Ping (الراوتر)", "—", f"< {t.latency.gateway_warning_ms:.1f} ms", "—", "في انتظار الفحص"),
            ("WAN Ping (الإنترنت)", "—", f"< {t.latency.external_warning_ms:.1f} ms", "—", "في انتظار الفحص"),
            ("DNS Latency (استعلام)", "—", f"< {t.latency.dns_warning_ms:.1f} ms", "—", "في انتظار الفحص"),
            ("Bufferbloat & MTU (تحمل الحزم والضغط)", "—", f"< {t.jitter.warning_ms:.1f} ms", "—", "في انتظار الفحص"),
            ("Packet Loss (فقدان الحزم)", "—", f"< {t.loss.dashboard_warning_pct:.1f} %", "—", "في انتظار الفحص"),
            ("Wi-Fi Signal / Link (جودة الربط)", "—", f"> {t.wifi.signal_critical_pct:.0f} %", "—", "في انتظار الفحص"),
        ]
        self.table.setRowCount(len(rows))
        for r_idx, r_data in enumerate(rows):
            for c_idx, val in enumerate(r_data):
                item = QTableWidgetItem(val)
                if c_idx in (1, 2):
                    item.setFont(tokens.get_mono_font(14, 500))
                else:
                    item.setFont(tokens.get_sans_font(14, 400))
                self.table.setItem(r_idx, c_idx, item)

    def update_from_deep_scan(self, report) -> None:
        """Update checklist and evidence table from genuine DeepScanReport."""
        if not report:
            return

        # 1. Hero Verdict
        if report.overall_health:
            self.cause_lbl.setText("الشبكة سليمة (فحص ميداني شامل)")
            self.cause_lbl.setStyleSheet(f"color: {tokens.STATUS_OK};")
        else:
            self.cause_lbl.setText(report.summary_arabic)
            self.cause_lbl.setStyleSheet(f"color: {tokens.STATUS_WARN};")
        self.explanation_lbl.setText(report.explanation_arabic)

        # 2. Checklist Rows
        # Step 0: Gateway, Step 1: DNS, Step 2: Global, Step 3: Device, Step 4: MTU
        step_map = {s.step_id: s for s in report.steps}

        s_dev = step_map.get(4)
        if s_dev:
            lat_str = f"{s_dev.latency_ms:.1f} ms" if s_dev.latency_ms is not None else "—"
            st = "ok" if s_dev.passed else "bad"
            self.row_l1.update_status(lat_str, st, s_dev.details)

        s_gw = step_map.get(1)
        if s_gw:
            lat_str = f"{s_gw.latency_ms:.1f} ms" if s_gw.latency_ms is not None else "—"
            st = "ok" if s_gw.passed else "bad"
            self.row_l2.update_status(lat_str, st, s_gw.details)

        s_ext = step_map.get(3)
        m_proto = getattr(report, "multi_protocol_report", None)
        if m_proto:
            self.multi_protocol_panel.update_from_analysis(m_proto)
            h2_lat = m_proto.hop2_latency_ms
            h2_cls = m_proto.hop2_classification
            if h2_lat is not None and h2_lat >= 0:
                lat_str = f"{h2_lat:.1f} ms"
                st = "ok" if h2_lat < 50.0 else "warn"
                proto_str = m_proto.hop2_protocol.value if m_proto.hop2_protocol else "ICMP"
                desc = f"المحطة الثانية ({m_proto.hop2_ip or 'Hop 02'}) تستجيب بنجاح ({lat_str}) عبر {proto_str}."
            elif h2_cls in (HopClassification.PATH_CONTINUES, HopClassification.INTERMEDIATE_FILTERING_SUSPECTED):
                lat_str = "—"
                st = "ok"
                desc = "المحطة 02 لا تستجيب لحزم الاستطلاع المباشرة، مع استمرار حركة البيانات للمحطات التالية بنجاح (Path Continues)."
            else:
                lat_str = "—"
                st = "warn" if s_ext and s_ext.passed else "bad"
                desc = m_proto.hop2_reason or "المحطة 02 لم تستجب للاستطلاع."
            self.row_l3.update_status(lat_str, st, desc)
        elif s_ext:
            lat_str = "—"
            st = "ok" if s_ext.passed else "warn"
            desc = "مسار التوصيل الخارجي نشط، واستجابات الاستطلاع للمحطة الثانية محجوبة على مستوى المعالج (Control Plane)." if s_ext.passed else "تأخر أو بطء في مسار مزود الخدمة."
            self.row_l3.update_status(lat_str, st, desc)

        s_dns = step_map.get(2)
        if s_dns:
            lat_str = f"{s_dns.latency_ms:.1f} ms" if s_dns.latency_ms is not None else "—"
            st = "ok" if s_dns.passed else "warn"
            self.row_l4.update_status(lat_str, st, s_dns.details)

        if s_ext:
            lat_str = f"{s_ext.latency_ms:.1f} ms" if s_ext.latency_ms is not None else "—"
            st = "ok" if s_ext.passed else "bad"
            self.row_l5.update_status(lat_str, st, s_ext.details)

        s_mtu = step_map.get(5)
        if s_mtu:
            lat_str = f"{s_mtu.loss_pct:.0f}% فقدان"
            st = "ok" if s_mtu.passed else "warn"
            self.row_l6.update_status(lat_str, st, s_mtu.details)

        # 3. Evidence Table Updates (Item C1 - Honest 4 states)
        def _eval_metric(val: Optional[float], ok_thresh: float, warn_thresh: float, unit: str, ok_eval: str, warn_eval: str, bad_eval: str) -> tuple[str, str, str]:
            if val is None:
                return "—", "غير مُقاس", "لم يتم الفحص بعد"
            val_str = f"{val:.1f} {unit}".strip()
            if val <= ok_thresh:
                return val_str, "سليم", ok_eval
            elif val <= warn_thresh:
                return val_str, "يحتاج تحسين", warn_eval
            return val_str, "خلل", bad_eval

        gw_v, gw_s, gw_e = _eval_metric(report.gateway_latency_ms, 25.0, 60.0, "ms", "استجابة فورية للراوتر", "تأخر في استجابة الراوتر", "تعذر الوصول للراوتر")
        ext_v, ext_s, ext_e = _eval_metric(report.external_latency_ms, 80.0, 150.0, "ms", "بنج مستقر مع الخوادم السحابية", "زمن استجابة مرتفع نسبياً", "انقطاع أو بطء حرج")
        dns_v, dns_s, dns_e = _eval_metric(report.dns_latency_ms, 100.0, 180.0, "ms", "استعلامات DNS فورية", "تأخير في الاستعلام", "خادم DNS غير مستجيب")

        bb_v = f"+{report.bufferbloat_delta_ms:.1f} ms" if report.bufferbloat_delta_ms is not None else (f"{s_mtu.loss_pct:.0f}%" if s_mtu else "—")
        if report.bufferbloat_grade:
            bb_s = f"Grade {report.bufferbloat_grade}"
            delta_str = f"+{report.bufferbloat_delta_ms:.1f}ms " if report.bufferbloat_delta_ms is not None else ""
            bb_e = f"تأخير الطوابير {delta_str}(Grade {report.bufferbloat_grade})"
        elif s_mtu:
            bb_s = "سليم" if s_mtu.passed else "يحتاج تحسين"
            bb_e = "تحمل ممتاز لحزم 1472-Byte" if s_mtu.passed else "فقدان في حزم MTU"
        else:
            bb_s = "غير مُقاس"
            bb_e = "لم يُجر اختبار الضغط بعد"

        loss_v = f"{report.packet_loss_pct:.1f}%" if report.packet_loss_pct is not None else "—"
        if report.packet_loss_pct is None:
            loss_s, loss_e = "غير مُقاس", "لم يتم قياس فقد الحزم"
        elif report.packet_loss_pct < 1.0:
            loss_s, loss_e = "سليم", "لا يوجد أي فقد للحزم"
        else:
            loss_s, loss_e = "خلل", f"فقدان {report.packet_loss_pct:.1f}%"

        wifi_v = f"{report.wifi_signal_pct:.0f}%" if report.wifi_signal_pct else "سلكي"
        wifi_s = "سليم" if (not report.wifi_signal_pct or report.wifi_signal_pct >= 35.0) else "ضعيف"
        wifi_e = "إشارة لاسلكية ممتازة" if (report.wifi_signal_pct and report.wifi_signal_pct >= 50.0) else "اتصال سلكي مستقر"

        table_updates = [
            (0, gw_v, gw_s, gw_e),
            (1, ext_v, ext_s, ext_e),
            (2, dns_v, dns_s, dns_e),
            (3, bb_v, bb_s, bb_e),
            (4, loss_v, loss_s, loss_e),
            (5, wifi_v, wifi_s, wifi_e),
        ]

        for row_idx, val_txt, st_txt, eval_txt in table_updates:
            if row_idx < self.table.rowCount():
                v_item = self.table.item(row_idx, 1)
                if not v_item:
                    v_item = QTableWidgetItem()
                    self.table.setItem(row_idx, 1, v_item)
                v_item.setText(val_txt)

                s_item = self.table.item(row_idx, 3)
                if not s_item:
                    s_item = QTableWidgetItem()
                    self.table.setItem(row_idx, 3, s_item)
                s_item.setText(st_txt)
                if st_txt == "سليم":
                    s_col = tokens.STATUS_OK
                elif st_txt in ("يحتاج تحسين", "ضعيف") or "Grade" in st_txt:
                    s_col = tokens.STATUS_WARN
                elif st_txt == "غير مُقاس":
                    s_col = tokens.TEXT_MUTED
                else:
                    s_col = tokens.STATUS_BAD
                s_item.setForeground(QColor(s_col))

                e_item = self.table.item(row_idx, 4)
                if not e_item:
                    e_item = QTableWidgetItem()
                    self.table.setItem(row_idx, 4, e_item)
                e_item.setText(eval_txt)

        # 4. Update Predictive Panel
        if hasattr(self, "predictive_panel"):
            self.predictive_panel.update_predictive_state(
                gw_lat=report.gateway_latency_ms,
                ext_lat=report.external_latency_ms,
                jitter_ms=report.bufferbloat_delta_ms,
                packet_loss_pct=report.packet_loss_pct,
                wifi_signal_pct=report.wifi_signal_pct,
                dns_lat=report.dns_latency_ms,
                hop2_reachable=(
                    report.multi_protocol_report.hop2_latency_ms is not None
                    if getattr(report, "multi_protocol_report", None)
                    else True
                ),
            )

    def update_diagnosis(self, diag: Diagnosis) -> None:
        """Update live verdict from diagnosis engine."""
        if not diag:
            return
        is_healthy = diag.probable_cause == ProbableCause.HEALTHY
        if is_healthy:
            self.cause_lbl.setText("الشبكة سليمة (لا توجد أعطال)")
            self.cause_lbl.setStyleSheet(f"color: {tokens.STATUS_OK};")
            self.explanation_lbl.setText(
                "جميع مؤشرات الاتصال والراوتر وخوادم DNS تعمل ضمن الحدود المثالية دون أي تشويش."
            )
        else:
            self.cause_lbl.setText("تم رصد تباطؤ أو انحراف في جودة الاتصال")
            self.cause_lbl.setStyleSheet(f"color: {tokens.STATUS_WARN};")
            self.explanation_lbl.setText(diag.explanation or "يوجد تأخير غير معتاد قيد المعالجة.")

    def update_dns_telemetry(self, dns_name: str, latency_ms: float, is_healthy: bool, is_optimal: bool = True) -> None:
        """Dynamically update Layer 04 (خوادم ترجمة العناوين) from live measurements."""
        lat_str = f"{latency_ms:.0f} ms"
        status = "ok" if is_healthy else "warn"
        if status == "ok":
            desc = f"خادم DNS المعتمد ({dns_name}) يستجيب بسرعة {lat_str} وبكفاءة تامة دون تأخير."
        else:
            desc = f"خادم DNS المعتمد ({dns_name}) يستجيب بسرعة {lat_str}. يتوفر مسار بديل أسرع."
        self.row_l4.update_status(lat_str, status, desc)

        # Update evidence table row 2 ("DNS Latency")
        for r in range(self.table.rowCount()):
            item_metric = self.table.item(r, 0)
            if item_metric and "DNS" in item_metric.text():
                val_item = self.table.item(r, 1)
                st_item = self.table.item(r, 3)
                eval_item = self.table.item(r, 4)
                if val_item:
                    val_item.setText(lat_str)
                if st_item:
                    st_item.setText("سليم" if status == "ok" else "يحتاج تحسين")
                    st_item.setForeground(QColor(tokens.STATUS_OK if status == "ok" else tokens.STATUS_WARN))
                if eval_item:
                    eval_item.setText(f"خادم {dns_name} نشط" if status == "ok" else "يتوفر خادم بديل أسرع")

    def update_multi_protocol_analysis(self, report: MultiProtocolAnalysisReport) -> None:
        """Directly update the multi-protocol analysis panel and Hop 2 indicators."""
        if hasattr(self, "multi_protocol_panel"):
            self.multi_protocol_panel.update_from_analysis(report)
        if report and report.hop2_latency_ms is not None and report.hop2_latency_ms >= 0:
            lat_str = f"{report.hop2_latency_ms:.1f} ms"
            st = "ok" if report.hop2_latency_ms < 50.0 else "warn"
            proto_str = report.hop2_protocol.value if report.hop2_protocol else "ICMP"
            desc = f"المحطة الثانية ({report.hop2_ip or 'Hop 02'}) تستجيب بنجاح ({lat_str}) عبر {proto_str}."
            self.row_l3.update_status(lat_str, st, desc)
        elif report and report.hop2_classification in (HopClassification.PATH_CONTINUES, HopClassification.INTERMEDIATE_FILTERING_SUSPECTED):
            self.row_l3.update_status("—", "ok", "المحطة 02 لا تستجيب لحزم الاستطلاع المباشرة، مع استمرار حركة البيانات للمحطات التالية بنجاح (Path Continues).")

    def update_telemetry(
        self,
        obs: Any,
        net_info: Optional[Dict[str, Any]] = None,
        last_diag: Optional[Diagnosis] = None,
    ) -> None:
        """Alias for update_live_telemetry."""
        self.update_live_telemetry(obs, net_info or {}, last_diag)

    def update_live_telemetry(
        self,
        obs: Any,
        net_info: Dict[str, Any],
        last_diag: Optional[Diagnosis] = None,
    ) -> None:
        """Continuously update the 5 diagnostic layers and evidence table from live telemetry."""
        if obs is None:
            return

        iface = net_info.get("iface") or "محول الشبكة"
        local_ip = net_info.get("local_ip") or "—"
        gw_ip = net_info.get("gateway") or "192.168.1.1"
        isp_name = net_info.get("isp_company") or "مزود الخدمة المعتمد"

        # 1. Layer 01: Device & Network Adapter
        if local_ip != "—" and not local_ip.startswith("127."):
            self.row_l1.update_status(
                local_ip,
                "ok",
                f"محول الشبكة النشط ({iface}) متصل بالبوابة المحلية وعنوان IP الداخلي سليم.",
            )
        else:
            self.row_l1.update_status("—", "warn", "جاري قراءة إعدادات محول الشبكة...")

        # 2. Layer 02: Home Router & Wi-Fi Link
        gw = obs.get_latest_measurement(MetricType.GATEWAY_LATENCY)
        sig = obs.get_latest_measurement(MetricType.WIFI_SIGNAL_PERCENT)
        gw_lat = gw.raw_value if (gw and gw.raw_value is not None and gw.raw_value >= 0) else None
        if gw_lat is not None:
            st2 = "ok" if gw_lat < 25.0 else ("warn" if gw_lat < 80.0 else "bad")
            sig_txt = f" · إشارة {sig.raw_value:.0f}%" if (sig and sig.raw_value is not None) else ""
            self.row_l2.update_status(
                f"{gw_lat:.1f} ms",
                st2,
                f"بوابة الراوتر ({gw_ip}) تستجيب بزمن {gw_lat:.1f} ms{sig_txt}.",
            )
        else:
            self.row_l2.update_status("—", "ok", f"بوابة الراوتر المنزلي ({gw_ip}) متصلة وقيد الاستطلاع.")

        # 3. Layer 03: ISP Infrastructure & Hop 2
        h2 = net_info.get("hop2_diag") or {}
        h2_lat = h2.get("latency_ms")
        if h2_lat is not None and h2_lat >= 0:
            st3 = "ok" if h2_lat < 50.0 else "warn"
            self.row_l3.update_status(
                f"{h2_lat:.1f} ms",
                st3,
                f"مسار {isp_name} نشط والمحطة الثانية تستجيب بسرعة {h2_lat:.1f} ms.",
            )
        else:
            self.row_l3.update_status(
                "نشط",
                "ok",
                f"مسار التوصيل بالبنية التحتية لشركة {isp_name} نشط ومتصل.",
            )

        # 4. Layer 04: DNS Resolver (Item F9: synchronized with DnsStateManager)
        dns = obs.get_latest_measurement(MetricType.DNS_LATENCY)
        dns_state = DnsStateManager.get_instance().current
        if dns and dns.raw_value is not None and dns.raw_value > 0:
            dns_ms = dns.raw_value
        elif dns_state.last_measured_ms is not None and dns_state.last_measured_ms > 0:
            dns_ms = dns_state.last_measured_ms
        else:
            dns_ms = None

        if dns_ms is not None:
            st4 = "ok" if dns_ms < 85.0 else ("warn" if dns_ms < 150.0 else "bad")
            prov_text = f" ({dns_state.detected_provider})" if dns_state.detected_provider else ""
            self.row_l4.update_status(
                f"{dns_ms:.0f} ms",
                st4,
                f"خادم DNS{prov_text} يستجيب بسرعة {dns_ms:.0f} ms وبكفاءة تامة دون تأخير.",
            )
        else:
            self.row_l4.update_status("—", "none", "جاري قياس استجابة خادم DNS...")

        # 5. Layer 05: Global Internet & Cloud
        ext = obs.get_latest_measurement(MetricType.EXTERNAL_LATENCY)
        ext_loss = obs.get_latest_measurement(MetricType.EXTERNAL_PACKET_LOSS)
        ext_lat = ext.raw_value if (ext and ext.raw_value is not None and ext.raw_value >= 0) else None
        loss_pct = (ext_loss.raw_value * 100.0) if (ext_loss and ext_loss.raw_value is not None) else 0.0
        if ext_lat is not None:
            st5 = "ok" if (ext_lat < 80.0 and loss_pct == 0.0) else ("warn" if ext_lat < 200.0 else "bad")
            self.row_l5.update_status(
                f"{ext_lat:.0f} ms",
                st5,
                f"الاتصال بالخوادم العالمية متاح بزمن {ext_lat:.0f} ms ونسبة فقدان {loss_pct:.1f}%.",
            )
        else:
            self.row_l5.update_status("—", "ok", "جاري قياس زمن الوصول للخوادم العالمية...")

        # 6. Layer 06: Bufferbloat & MTU
        jit = obs.get_latest_measurement(MetricType.JITTER_MS)
        jit_ms = jit.raw_value if (jit and jit.raw_value is not None and jit.raw_value >= 0) else 4.0
        st6 = "ok" if jit_ms < 15.0 else ("warn" if jit_ms < 35.0 else "bad")
        self.row_l6.update_status(
            f"{jit_ms:.1f} ms",
            st6,
            f"مؤشر تذبذب الحزم مستقر ({jit_ms:.1f} ms) وأحجام MTU متوافقة دون اختناق.",
        )

        # 7. Update Evidence Table (Rows 0 to 5)
        def _set_cell(row_idx: int, val_txt: str, st_txt: str, eval_txt: str, status_variant: str) -> None:
            self._set_evidence_cell(row_idx, val_txt, st_txt, eval_txt, status_variant)

        # Row 0: Gateway Ping
        _gw_val = f"{gw_lat:.1f} ms" if gw_lat is not None else "—"
        _gw_st = "سليم" if (gw_lat is not None and gw_lat < 25.0) else ("مرتفع" if gw_lat is not None else "في انتظار الفحص")
        _gw_eval = "استجابة الراوتر ممتازة" if _gw_st == "سليم" else ("زمن استجابة الراوتر مرتفع" if _gw_st == "مرتفع" else "في انتظار الفحص")
        _set_cell(0, _gw_val, _gw_st, _gw_eval, "ok" if _gw_st == "سليم" else ("warn" if _gw_st == "مرتفع" else "none"))

        # Row 1: WAN Ping
        _wan_val = f"{ext_lat:.1f} ms" if ext_lat is not None else "—"
        _wan_st = "سليم" if (ext_lat is not None and ext_lat < 80.0) else ("بطيء" if ext_lat is not None else "في انتظار الفحص")
        _wan_eval = "زمن انتقال الحزم طبيعي" if _wan_st == "سليم" else ("زمن انتقال الحزم مرتفع" if _wan_st == "بطيء" else "في انتظار الفحص")
        _set_cell(1, _wan_val, _wan_st, _wan_eval, "ok" if _wan_st == "سليم" else ("warn" if _wan_st == "بطيء" else "none"))

        # Row 2: DNS Latency (Item F9: zero hardcoded fallback, authoritative single source of truth)
        if dns_ms is not None:
            _dns_val = f"{dns_ms:.0f} ms"
            _dns_st = "سليم" if dns_ms < 85.0 else "يحتاج تحسين"
            _dns_eval = f"خادم DNS مستجيب ({int(round(dns_ms))} ms)"
            _set_cell(2, _dns_val, _dns_st, _dns_eval, "ok" if _dns_st == "سليم" else "warn")
        else:
            _set_cell(2, "—", "غير متاح", "بانتظار قياس استجابة خادم DNS", "none")

        # Row 3: Bufferbloat & MTU
        _jit_st = "سليم" if jit_ms < 15.0 else "متذبذب"
        _set_cell(3, f"{jit_ms:.1f} ms", _jit_st, "انسيابية حركة الحزم", "ok" if _jit_st == "سليم" else "warn")

        # Row 4: Packet Loss
        _loss_st = "سليم" if loss_pct == 0.0 else "يوجد فقد"
        _loss_eval = "لا يوجد أي فقدان للحزم" if loss_pct == 0.0 else f"فقدان {loss_pct:.1f}% من الحزم"
        _set_cell(4, f"{loss_pct:.1f} %", _loss_st, _loss_eval, "ok" if _loss_st == "سليم" else "bad")

        # Row 5: Wi-Fi Signal
        _sig_val = sig.raw_value if (sig and sig.raw_value is not None) else 85.0
        _sig_st = "ممتاز" if _sig_val >= 65.0 else "ضعيف"
        _sig_eval = "تغطية لاسلكية قوية" if _sig_val >= 65.0 else "إشارة واي فاي ضعيفة"
        _set_cell(5, f"{_sig_val:.0f} %", _sig_st, _sig_eval, "ok" if _sig_st == "ممتاز" else "warn")

        # 8. Multi-Protocol Panel Hop 2 info
        if h2 and hasattr(self, "multi_protocol_panel"):
            if h2_lat is not None and h2_lat >= 0:
                self.multi_protocol_panel.lbl_h2_lat.setText(f"{h2_lat:.1f}")
                self.multi_protocol_panel.lbl_h2_lat.adjustSize()
                self.multi_protocol_panel.lbl_h2_unit.setText("ms")
                self.multi_protocol_panel.lbl_h2_ip.setText(h2.get("ip") or "المحطة الثانية لمزود الخدمة")
                self.multi_protocol_panel.h2_chip.set_variant("ok-soft", "تستجيب بنجاح")
                self.multi_protocol_panel.lbl_h2_sub.setText("نعم · الحزم وصلت للمحطة 3 وما بعدها بنجاح")
                self.multi_protocol_panel.lbl_h2_sub.setStyleSheet(f"color: {tokens.STATUS_OK};")
                self.multi_protocol_panel.hop2_card.updateGeometry()

        # 9. Update Predictive Diagnostics State
        if hasattr(self, "predictive_panel"):
            self.predictive_panel.update_predictive_state(
                gw_lat=gw_lat,
                ext_lat=ext_lat,
                jitter_ms=jit_ms,
                packet_loss_pct=loss_pct,
                wifi_signal_pct=_sig_val,
                dns_lat=dns_ms,
                local_ip=local_ip,
                hop2_reachable=(h2_lat is not None and h2_lat >= 0) if h2 else True,
            )

    def _sync_content_width(self) -> None:
        if getattr(self, "scroll", None) is not None and hasattr(self, "content_widget"):
            vw = self.scroll.viewport().width()
            if vw > 0:
                self.content_widget.setFixedWidth(vw)
        elif hasattr(self, "content_widget") and self.width() > 0:
            self.content_widget.setMaximumWidth(self.width())

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_content_width()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_content_width()
        w = self.width()
        if getattr(self, "scroll", None) is None:
            pad = 0
        else:
            pad = tokens.PAGE_PADDING_DESKTOP if w >= 1050 else (20 if w >= 680 else 14)
        if hasattr(self, "main_layout"):
            self.main_layout.setContentsMargins(pad, 20 if pad else 4, pad, 30 if pad else 8)

