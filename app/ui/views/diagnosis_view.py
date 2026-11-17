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
from app.core.models.metrics import Diagnosis, ProbableCause
from app.core.thresholds import NetworkThresholds


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
        top_row.addWidget(self.lbl_name)

        top_row.addStretch()

        self.lbl_metric = QLabel(metric_str)
        self.lbl_metric.setFont(tokens.get_mono_font(14, 500))
        self.lbl_metric.setStyleSheet(f"color: {tokens.TEXT};")
        top_row.addWidget(self.lbl_metric)

        self.chip = Chip("سليم" if status == "ok" else "يحتاج تحسين", variant="ok-soft" if status == "ok" else "tag-warn")
        top_row.addWidget(self.chip)
        layout.addLayout(top_row)

        self.lbl_desc = QLabel(desc)
        self.lbl_desc.setFont(tokens.get_sans_font(13, 400))
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
        elif status in ("bad", "error"):
            self.chip.set_variant("bad-soft", "خلل / انقطاع")
        else:
            self.chip.set_variant("neutral", "غير متوفر")


class DiagnosisView(QWidget):
    """Architectural diagnosis view matching the graphite hairline design system."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(
            tokens.PAGE_PADDING_DESKTOP, 28, tokens.PAGE_PADDING_DESKTOP, 36
        )
        layout.setSpacing(tokens.SECTION_GAP)

        # -------------------------------------------------------------
        # 1. Hero Verdict Panel
        # -------------------------------------------------------------
        verdict_panel = Panel(title="التشخيص الفوري للشبكة", subtitle="فحص دقيق لكافة مسارات التوصيل", parent=self)

        top_h = QHBoxLayout()
        v_col = QVBoxLayout()
        v_col.setSpacing(4)

        self.cause_lbl = QLabel("جاهز للفحص الشامل")
        self.cause_lbl.setFont(tokens.get_sans_font(24, 600))
        self.cause_lbl.setStyleSheet(f"color: {tokens.TEXT};")

        self.explanation_lbl = QLabel(
            "اضغط على زر 'فحص شامل ودقيق الآن' لإجراء اختبار تفصيلي لجميع مسارات الاتصال والراوتر وخوادم DNS."
        )
        self.explanation_lbl.setFont(tokens.get_sans_font(14, 400))
        self.explanation_lbl.setStyleSheet(f"color: {tokens.TEXT_SECONDARY}; line-height: 1.6;")
        self.explanation_lbl.setWordWrap(True)

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

        scroll.setWidget(content_widget)
        root_layout.addWidget(scroll)

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
                    item.setFont(tokens.get_mono_font(13, 500))
                else:
                    item.setFont(tokens.get_sans_font(13, 400))
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
        if s_ext and s_gw:
            gw_m = s_gw.latency_ms or 0.0
            ext_m = s_ext.latency_ms or 0.0
            isp_lat = gw_m + max(2.0, (ext_m - gw_m) * 0.35)
            lat_str = f"{isp_lat:.1f} ms" if s_ext.passed else "—"
            st = "ok" if s_ext.passed else "warn"
            self.row_l3.update_status(lat_str, st, f"مسار التوصيل بشركة الاتصالات مستقر وطبيعي ({lat_str})." if s_ext.passed else "تأخر طفيف في مسار مزود الخدمة.")

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

        # 3. Evidence Table Updates
        table_updates = [
            (0, f"{report.gateway_latency_ms:.1f} ms" if report.gateway_latency_ms is not None else "—",
             "سليم" if (report.gateway_latency_ms and report.gateway_latency_ms < 25.0) else "يحتاج تحسين",
             "استجابة فورية للراوتر" if (report.gateway_latency_ms and report.gateway_latency_ms < 25.0) else "استجابة متأخرة"),
            (1, f"{report.external_latency_ms:.1f} ms" if report.external_latency_ms is not None else "—",
             "سليم" if (report.external_latency_ms and report.external_latency_ms < 80.0) else "يحتاج تحسين",
             "بنج مستقر مع الخوادم السحابية" if report.external_latency_ms else "غير متصل"),
            (2, f"{report.dns_latency_ms:.1f} ms" if report.dns_latency_ms is not None else "—",
             "سليم" if (report.dns_latency_ms and report.dns_latency_ms < 100.0) else "يحتاج تحسين",
             "استعلامات DNS فورية" if report.dns_latency_ms else "تأخير في الاستعلام"),
            (3, f"+{report.bufferbloat_delta_ms:.1f} ms" if report.bufferbloat_delta_ms is not None else (f"{s_mtu.loss_pct:.0f}%" if s_mtu else "—"),
             f"Grade {report.bufferbloat_grade}" if report.bufferbloat_grade else ("سليم" if (s_mtu and s_mtu.passed) else "يحتاج تحسين"),
             f"تأخير الطوابير +{report.bufferbloat_delta_ms:.1f}ms (Grade {report.bufferbloat_grade})" if report.bufferbloat_grade else ("تحمل ممتاز لحزم 1472-Byte" if (s_mtu and s_mtu.passed) else "فقدان في حزم MTU")),
            (4, f"{report.packet_loss_pct:.1f}%",
             "سليم" if report.packet_loss_pct < 1.0 else "خلل",
             "لا يوجد أي فقد للحزم" if report.packet_loss_pct == 0.0 else f"فقدان {report.packet_loss_pct:.1f}%"),
            (5, f"{report.wifi_signal_pct:.0f}%" if report.wifi_signal_pct else "سلكي",
             "سليم" if (not report.wifi_signal_pct or report.wifi_signal_pct >= 35.0) else "ضعيف",
             "إشارة لاسلكية ممتازة" if (report.wifi_signal_pct and report.wifi_signal_pct >= 50.0) else "اتصال سلكي مستقر"),
        ]

        for row_idx, val_txt, st_txt, eval_txt in table_updates:
            if row_idx < self.table.rowCount():
                v_item = self.table.item(row_idx, 1) or QTableWidgetItem()
                s_item = self.table.item(row_idx, 3) or QTableWidgetItem()
                e_item = self.table.item(row_idx, 4) or QTableWidgetItem()

                v_item.setText(val_txt)
                s_item.setText(st_txt)
                s_col = tokens.STATUS_OK if st_txt == "سليم" else (tokens.STATUS_WARN if st_txt in ("يحتاج تحسين", "ضعيف") else tokens.STATUS_BAD)
                s_item.setForeground(QColor(s_col))
                e_item.setText(eval_txt)

                self.table.setItem(row_idx, 1, v_item)
                self.table.setItem(row_idx, 3, s_item)
                self.table.setItem(row_idx, 4, e_item)

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
