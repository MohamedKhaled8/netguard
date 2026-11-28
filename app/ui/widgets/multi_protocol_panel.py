"""Multi-Protocol Connectivity Analysis Widget for NetGuard AI.

Provides comprehensive visual representation of:
- Hop 2 In-Depth Inspection Card (number, status, IP, protocol, latency, reason, subsequent hops)
- Three-Protocol Comparison Grid (ICMP vs TCP 443 vs UDP)
- Independent End-to-End Verification (TCP 443, DNS, HTTPS, multi-target comparison)
- Consolidated Evidence Verdict (Case 1, 2, 3, 4 rules with honest, technical Arabic explanation)
- Windows Compatibility & Driver Status (Npcap detection, Win32 IcmpSendEcho)

Adheres strictly to NetGuard AI's design tokens and dark warm-neutral graphite theme.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

from app.ui import tokens
from app.ui.widgets.chip import Chip
from app.ui.widgets.base_panel import Panel
from app.diagnosis.traceroute import (
    HopClassification,
    ProbeProtocol,
    MultiProtocolAnalysisReport,
    TraceRouteReport,
    EndToEndCheckResult,
)


class MultiProtocolAnalysisPanel(Panel):
    """Panel dedicated to Multi-Protocol Traceroute & Connectivity Analysis."""

    def __init__(self, parent=None) -> None:
        super().__init__(
            title="تحليل الاتصال متعدد البروتوكولات",
            subtitle="فحص ميداني مستقل للمسارات عبر \u2066ICMP\u2069 و \u2066TCP (443)\u2069 و \u2066UDP\u2069 مع التحقق الطرفي المباشر",
            parent=parent,
        )
        self.setObjectName("MultiProtocolAnalysisPanel")
        if hasattr(self, "lbl_title") and self.lbl_title:
            self.lbl_title.setStyleSheet(f"color: {tokens.TEXT}; background: transparent; padding-top: 4px; line-height: 1.4;")

        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 4, 0, 4)
        container_layout.setSpacing(16)

        # -------------------------------------------------------------
        # 1. Hop 2 In-Depth Inspection Card
        # -------------------------------------------------------------
        self.hop2_card = QFrame()
        self.hop2_card.setObjectName("Hop2Card")
        self.hop2_card.setStyleSheet(f"""
            QFrame#Hop2Card {{
                background-color: {tokens.SURFACE_INSET};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_INNER}px;
                padding: 16px;
            }}
            QFrame#Hop2Card QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        hop2_layout = QVBoxLayout(self.hop2_card)
        hop2_layout.setContentsMargins(14, 12, 14, 12)
        hop2_layout.setSpacing(10)

        # Header: Hop 02 Title + Status Chip + Protocol
        h2_header = QHBoxLayout()
        h2_header.setSpacing(10)

        self.lbl_h2_badge = QLabel("المحطة الثانية · Hop 02")
        self.lbl_h2_badge.setFont(tokens.get_sans_font(15, 600))
        self.lbl_h2_badge.setStyleSheet(f"color: {tokens.TEXT};")
        h2_header.addWidget(self.lbl_h2_badge)

        self.h2_chip = Chip("في انتظار الفحص", variant="neutral")
        h2_header.addWidget(self.h2_chip)

        self.h2_proto_chip = Chip("Multi-Probe", variant="neutral")
        h2_header.addWidget(self.h2_proto_chip)

        h2_header.addStretch(1)

        self.lbl_h2_lat = QLabel("—")
        self.lbl_h2_lat.setFont(tokens.get_mono_font(18, 600))
        self.lbl_h2_lat.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_h2_lat.setMinimumWidth(80)
        self.lbl_h2_lat.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h2_header.addWidget(self.lbl_h2_lat)

        self.lbl_h2_unit = QLabel("ms")
        self.lbl_h2_unit.setFont(tokens.get_sans_font(13, 400))
        self.lbl_h2_unit.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        h2_header.addWidget(self.lbl_h2_unit)

        hop2_layout.addLayout(h2_header)

        # Hop 2 Metrics Grid (IP, Subsequent Responded, Classification, Reason)
        h2_grid = QGridLayout()
        h2_grid.setContentsMargins(0, 4, 0, 0)
        h2_grid.setHorizontalSpacing(16)
        h2_grid.setVerticalSpacing(8)

        # Cell 1: Discovered IP
        lbl_ip_title = QLabel("العنوان المرصود (IP):")
        lbl_ip_title.setFont(tokens.get_sans_font(13, 500))
        lbl_ip_title.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_h2_ip = QLabel("—")
        self.lbl_h2_ip.setFont(tokens.get_mono_font(14, 500))
        self.lbl_h2_ip.setStyleSheet(f"color: {tokens.TEXT};")
        self.lbl_h2_ip.setWordWrap(True)
        h2_grid.addWidget(lbl_ip_title, 0, 0)
        h2_grid.addWidget(self.lbl_h2_ip, 0, 1, 1, 3)

        # Cell 2: Subsequent Hops
        lbl_sub_title = QLabel("استجابة المحطات اللاحقة (Hop 3+):")
        lbl_sub_title.setFont(tokens.get_sans_font(13, 500))
        lbl_sub_title.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_h2_sub = QLabel("—")
        self.lbl_h2_sub.setFont(tokens.get_sans_font(13, 400))
        self.lbl_h2_sub.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self.lbl_h2_sub.setWordWrap(True)
        h2_grid.addWidget(lbl_sub_title, 1, 0)
        h2_grid.addWidget(self.lbl_h2_sub, 1, 1, 1, 3)

        # Cell 3: Reason for missing response
        lbl_reason_title = QLabel("تشخيص حالة المحطة:")
        lbl_reason_title.setFont(tokens.get_sans_font(13, 500))
        lbl_reason_title.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        self.lbl_h2_reason = QLabel("اضغط على فحص شامل ودقيق لتشغيل محرك استكشاف المسارات المتعددة.")
        self.lbl_h2_reason.setFont(tokens.get_sans_font(13, 400))
        self.lbl_h2_reason.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        self.lbl_h2_reason.setWordWrap(True)
        h2_grid.addWidget(lbl_reason_title, 2, 0)
        h2_grid.addWidget(self.lbl_h2_reason, 2, 1, 1, 3)

        hop2_layout.addLayout(h2_grid)
        container_layout.addWidget(self.hop2_card)

        # -------------------------------------------------------------
        # 2. Three-Protocol Trace Comparison Grid (ICMP vs TCP 443 vs UDP)
        # -------------------------------------------------------------
        self.proto_grid_container = QWidget()
        proto_layout = QHBoxLayout(self.proto_grid_container)
        proto_layout.setContentsMargins(0, 0, 0, 0)
        proto_layout.setSpacing(12)

        self.card_icmp = self._create_proto_subcard("ICMP Trace", "Windows Native (IcmpSendEcho)")
        self.card_tcp = self._create_proto_subcard("TCP Trace (Port 443)", "SYN-ACK / RST / Time Exceeded")
        self.card_udp = self._create_proto_subcard("UDP Trace", "Time Exceeded / Port Unreachable")

        proto_layout.addWidget(self.card_icmp)
        proto_layout.addWidget(self.card_tcp)
        proto_layout.addWidget(self.card_udp)
        container_layout.addWidget(self.proto_grid_container)

        # -------------------------------------------------------------
        # 3. Independent End-to-End Connectivity Verification
        # -------------------------------------------------------------
        self.e2e_frame = QFrame()
        self.e2e_frame.setObjectName("E2EFrame")
        self.e2e_frame.setStyleSheet(f"""
            QFrame#E2EFrame {{
                background-color: {tokens.SURFACE_INSET};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_INNER}px;
                padding: 12px 16px;
            }}
            QFrame#E2EFrame QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        e2e_layout = QVBoxLayout(self.e2e_frame)
        e2e_layout.setContentsMargins(12, 10, 12, 10)
        e2e_layout.setSpacing(8)

        lbl_e2e_heading = QLabel("التحقق المستقل من الاتصال الفعلي بالنهاية الطرفية (End-to-End Verification)")
        lbl_e2e_heading.setFont(tokens.get_sans_font(14, 600))
        lbl_e2e_heading.setStyleSheet(f"color: {tokens.TEXT};")
        e2e_layout.addWidget(lbl_e2e_heading)

        e2e_chips_row = QHBoxLayout()
        e2e_chips_row.setSpacing(10)

        self.chip_e2e_tcp = Chip("TCP-443: —", variant="neutral")
        self.chip_e2e_dns = Chip("DNS Resolver: —", variant="neutral")
        self.chip_e2e_https = Chip("HTTPS Request: —", variant="neutral")
        self.chip_e2e_multi = Chip("Multi-Target: —", variant="neutral")

        e2e_chips_row.addWidget(self.chip_e2e_tcp)
        e2e_chips_row.addWidget(self.chip_e2e_dns)
        e2e_chips_row.addWidget(self.chip_e2e_https)
        e2e_chips_row.addWidget(self.chip_e2e_multi)
        e2e_chips_row.addStretch()

        e2e_layout.addLayout(e2e_chips_row)
        container_layout.addWidget(self.e2e_frame)

        # -------------------------------------------------------------
        # 4. Consolidated Evidence Verdict & Rule Identification
        # -------------------------------------------------------------
        self.verdict_frame = QFrame()
        self.verdict_frame.setObjectName("VerdictFrame")
        self.verdict_frame.setStyleSheet(f"""
            QFrame#VerdictFrame {{
                background-color: {tokens.SURFACE_HOVER};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_INNER}px;
                padding: 14px 16px;
            }}
            QFrame#VerdictFrame QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        verdict_layout = QVBoxLayout(self.verdict_frame)
        verdict_layout.setContentsMargins(12, 10, 12, 10)
        verdict_layout.setSpacing(6)

        v_top = QHBoxLayout()
        self.lbl_case_badge = Chip("التشخيص الموحد", variant="neutral")
        v_top.addWidget(self.lbl_case_badge)

        self.lbl_verdict_title = QLabel("في انتظار الفحص التشخيصي الميداني")
        self.lbl_verdict_title.setFont(tokens.get_sans_font(15, 600))
        self.lbl_verdict_title.setStyleSheet(f"color: {tokens.TEXT};")
        v_top.addWidget(self.lbl_verdict_title, stretch=1)
        verdict_layout.addLayout(v_top)

        self.lbl_verdict_body = QLabel(
            "يقوم المحرك بفحص 3 بروتوكولات مستقلة وتطبيق قواعد التشخيص المعتمدة دولياً "
            "دون افتراض مسميات لمكونات الشبكة ودون إخفاء أي محطة وسيطة."
        )
        self.lbl_verdict_body.setFont(tokens.get_sans_font(13, 400))
        self.lbl_verdict_body.setStyleSheet(f"color: {tokens.TEXT_SECONDARY}; line-height: 1.6;")
        self.lbl_verdict_body.setWordWrap(True)
        verdict_layout.addWidget(self.lbl_verdict_body)

        # Driver / Compatibility Footer
        self.lbl_driver_info = QLabel("Windows Native Driver: Win32 IcmpSendEcho Active · Npcap Sniffer Ready")
        self.lbl_driver_info.setFont(tokens.get_mono_font(12, 400))
        self.lbl_driver_info.setStyleSheet(f"color: {tokens.TEXT_MUTED}; padding-top: 4px;")
        verdict_layout.addWidget(self.lbl_driver_info)

        container_layout.addWidget(self.verdict_frame)

        self.main_layout.addLayout(container_layout)

    def _create_proto_subcard(self, title: str, subtitle: str) -> QFrame:
        card = QFrame()
        card.setObjectName("ProtoSubCard")
        card.setMinimumHeight(140)
        card.setStyleSheet(f"""
            QFrame#ProtoSubCard {{
                background-color: {tokens.SURFACE_INSET};
                border: 1px solid {tokens.LINE};
                border-radius: {tokens.RADIUS_INNER}px;
            }}
            QFrame#ProtoSubCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(4)

        t_lbl = QLabel(title)
        t_lbl.setFont(tokens.get_sans_font(14, 600))
        t_lbl.setStyleSheet(f"color: {tokens.TEXT};")
        t_lbl.setWordWrap(True)
        l.addWidget(t_lbl)

        sub_lbl = QLabel(subtitle)
        sub_lbl.setFont(tokens.get_sans_font(12, 400))
        sub_lbl.setStyleSheet(f"color: {tokens.TEXT_MUTED};")
        sub_lbl.setWordWrap(True)
        l.addWidget(sub_lbl)

        row_stat = QHBoxLayout()
        val_lbl = QLabel("—")
        val_lbl.setObjectName("ProtoVal")
        val_lbl.setFont(tokens.get_mono_font(15, 600))
        val_lbl.setStyleSheet(f"color: {tokens.TEXT};")
        row_stat.addWidget(val_lbl)

        chip = Chip("لم يُقاس", variant="neutral")
        chip.setObjectName("ProtoChip")
        row_stat.addWidget(chip)
        row_stat.addStretch()
        l.addLayout(row_stat)

        detail_lbl = QLabel("في انتظار الفحص")
        detail_lbl.setObjectName("ProtoDetail")
        detail_lbl.setFont(tokens.get_sans_font(12, 400))
        detail_lbl.setStyleSheet(f"color: {tokens.TEXT_SECONDARY};")
        detail_lbl.setWordWrap(True)
        l.addWidget(detail_lbl)

        return card

    def update_from_analysis(self, report: MultiProtocolAnalysisReport) -> None:
        """Populate the UI with genuine real-time diagnostic results."""
        if not report:
            return

        # 1. Hop 2 Card
        h2_cls = report.hop2_classification
        if h2_cls == HopClassification.RESPONDING:
            self.h2_chip.set_variant("ok-soft", "تستجيب بنجاح")
        elif h2_cls == HopClassification.PATH_CONTINUES:
            self.h2_chip.set_variant("tag-warn", "البيانات تمر (Path Continues)")
        elif h2_cls == HopClassification.INTERMEDIATE_FILTERING_SUSPECTED:
            self.h2_chip.set_variant("tag-warn", "حجب استطلاع وسيط")
        elif h2_cls == HopClassification.DESTINATION_UNREACHABLE:
            self.h2_chip.set_variant("bad-soft", "تعذر الوصول للوجهة")
        else:
            self.h2_chip.set_variant("neutral", "غير حاسم")

        if report.hop2_protocol:
            self.h2_proto_chip.set_variant("neutral", report.hop2_protocol.value)

        if report.hop2_latency_ms is not None and report.hop2_latency_ms >= 0:
            self.lbl_h2_lat.setText(f"{report.hop2_latency_ms:.1f}")
            self.lbl_h2_unit.setText("ms")
        else:
            self.lbl_h2_lat.setText("—")
            self.lbl_h2_unit.setText("")

        self.lbl_h2_ip.setText(report.hop2_ip or "غير معلن (لم تستجب المحطة برمجياً)")

        if report.hop2_subsequent_responded:
            self.lbl_h2_sub.setText("نعم · الحزم وصلت للمحطة 3 وما بعدها بنجاح")
            self.lbl_h2_sub.setStyleSheet(f"color: {tokens.STATUS_OK};")
        else:
            self.lbl_h2_sub.setText("لا · لا توجد استجابة من المحطات التالية")
            self.lbl_h2_sub.setStyleSheet(f"color: {tokens.TEXT_MUTED};")

        self.lbl_h2_reason.setText(report.hop2_reason)

        # 2. Three-Protocol Comparison Subcards
        def _update_card(card: QFrame, tr: TraceRouteReport) -> None:
            val_lbl = card.findChild(QLabel, "ProtoVal")
            chip = card.findChild(Chip, "ProtoChip")
            detail_lbl = card.findChild(QLabel, "ProtoDetail")

            rtt_str = f"{tr.target_rtt_ms:.1f} ms" if tr.target_rtt_ms is not None else "—"
            if val_lbl:
                val_lbl.setText(rtt_str)

            if chip:
                if tr.target_reached:
                    chip.set_variant("ok-soft", "الهدف متاح")
                elif tr.trace_classification == HopClassification.DESTINATION_UNREACHABLE:
                    chip.set_variant("bad-soft", "تعذر الوصول")
                elif tr.trace_classification in (HopClassification.PATH_CONTINUES, HopClassification.INTERMEDIATE_FILTERING_SUSPECTED):
                    chip.set_variant("tag-warn", "المسار نشط")
                else:
                    chip.set_variant("neutral", "غير حاسم")

            if detail_lbl:
                h2 = tr.get_hop(2)
                h2_ar_map = {
                    HopClassification.RESPONDING: "استجابة مباشرة",
                    HopClassification.PATH_CONTINUES: "استمرار تدفق البيانات",
                    HopClassification.SILENT_HOP: "صامتة",
                    HopClassification.INTERMEDIATE_FILTERING_SUSPECTED: "حجب الاستطلاع الوسيط",
                    HopClassification.TRACE_INCONCLUSIVE: "فحص غير حاسم",
                    HopClassification.DESTINATION_UNREACHABLE: "تعذر الوصول للهدف",
                }
                h2_state = f"Hop 2: {h2_ar_map.get(h2.classification, h2.classification.value)}" if h2 else "Hop 2: غير مقاس"
                detail_lbl.setText(f"{tr.total_hops} محطات · {h2_state}")

        _update_card(self.card_icmp, report.icmp_trace)
        _update_card(self.card_tcp, report.tcp_trace)
        _update_card(self.card_udp, report.udp_trace)

        # 3. Independent End-to-End Verification Chips
        e2e = report.end_to_end_checks
        tcp_ok = any(r.tcp_443_ok for r in e2e)
        dns_ok = any(r.dns_ok for r in e2e)
        https_ok = any(r.https_ok for r in e2e)

        tcp_rtt = next((r.tcp_443_rtt_ms for r in e2e if r.tcp_443_rtt_ms is not None), None)
        rtt_txt = f" ({tcp_rtt:.1f} ms)" if tcp_rtt else ""

        self.chip_e2e_tcp.set_variant("ok-soft" if tcp_ok else "bad-soft", f"TCP-443: {'نجح' if tcp_ok else 'فشل'}{rtt_txt}")
        self.chip_e2e_dns.set_variant("ok-soft" if dns_ok else "bad-soft", f"DNS: {'سليم' if dns_ok else 'فشل'}")
        self.chip_e2e_https.set_variant("ok-soft" if https_ok else "bad-soft", f"HTTPS: {'نشط' if https_ok else 'تعذر'}")
        self.chip_e2e_multi.set_variant("ok-soft" if report.overall_end_to_end_ok else "bad-soft", f"نهاية طرفية: {len(e2e)} خوادم تم فحصها")

        # 4. Consolidated Evidence Verdict & Case Badge
        case_map = {
            "CASE_1": ("Case 1: Path Continues", "tag-warn"),
            "CASE_2": ("Case 2: Filtering Suspected", "tag-warn"),
            "CASE_3": ("Case 3: Inconclusive", "bad-soft"),
            "CASE_4": ("Case 4: Destination Unreachable", "bad-soft"),
            "NORMAL_RESPONDING": ("استجابة كاملة", "ok-soft"),
        }
        badge_txt, badge_var = case_map.get(report.case_identified, ("تحليل الأدلة", "neutral"))
        self.lbl_case_badge.set_variant(badge_var, badge_txt)

        self.lbl_verdict_title.setText(report.consolidated_verdict_arabic)
        if report.overall_end_to_end_ok or report.case_identified in ("CASE_1", "NORMAL_RESPONDING"):
            self.lbl_verdict_title.setStyleSheet(f"color: {tokens.STATUS_OK};")
        else:
            self.lbl_verdict_title.setStyleSheet(f"color: {tokens.STATUS_WARN};")

        self.lbl_verdict_body.setText(report.technical_details_arabic)
        self.lbl_driver_info.setText(report.driver_summary)
