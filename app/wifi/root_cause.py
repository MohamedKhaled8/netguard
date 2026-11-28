"""Section 4 & 12 Root-Cause Analysis Service generating structured 14-field Arabic diagnostic cards."""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.wifi.models import (
    BufferbloatDiagnosticsReport,
    ConnectedDeviceRecord,
    DnsDiagnosticsReport,
    FullChannelAnalysisReport,
    NetworkDiagnosticsReport,
    RouterCapabilities,
    RouterChangeProposal,
    RouterConfigurationSnapshot,
    RouterDiscoveryResult,
    SpeedTestReport,
    WifiInterfaceTelemetry,
)
from app.wifi.router.models_config import RouterConfigurationModel


class CausalChainExplanation(BaseModel):
    """Distinguishes observed symptoms from contributing factors and underlying root causes."""

    symptom: str
    contributing_factors: List[str] = Field(default_factory=list)
    root_cause: str
    chain_summary_ar: str


class DiagnosticFaultCard(BaseModel):
    """Complete 14-field Arabic diagnostic card rendered in the central 'المشكلات والأخطاء' panel."""

    card_id: str
    issue_name: str  # 1. اسم المشكلة
    location: str  # 2. مكان المشكلة
    current_setting: str  # 3. الإعداد الحالي
    verified_value_or_state: str  # 4. القيمة أو الحالة التي تم التحقق منها
    why_problem: str  # 5. سبب اعتبارها مشكلة
    evidence_and_measurements: List[str] = Field(default_factory=list)  # 6. الدليل والقياسات التي تؤكد ذلك
    expected_impact: str  # 7. التأثير المتوقع
    affected_devices_or_apps: List[str] = Field(default_factory=list)  # 8. الأجهزة أو التطبيقات المتأثرة
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"]  # 9. درجة الخطورة
    recommended_solution: str  # 10. الحل المقترح
    can_netguard_execute: bool = False  # 11. هل يستطيع NetGuard تنفيذ الحل؟
    execution_capability_note: str = ""
    requires_user_approval: bool = True  # 12. هل يحتاج الحل إلى موافقة المستخدم؟
    rollback_supported: bool = False  # 13. هل يمكن التراجع عن التعديل؟
    post_execution_verification: str = "لم يتم التنفيذ بعد"  # 14. نتيجة التحقق بعد التنفيذ
    causal_chain: Optional[CausalChainExplanation] = None
    linked_proposal: Optional[RouterChangeProposal] = None
    action_type: Literal["router_change", "local_dns", "local_qos", "manual_only", "info_only"] = "manual_only"


class ApplicationImpactEntry(BaseModel):
    """Section 12 application-level root-cause breakdown."""

    app_category: str
    app_title_ar: str
    status_ar: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "GOOD"]
    root_causes_ar: List[str] = Field(default_factory=list)
    fix_action_ar: str = ""


class RootCauseReport(BaseModel):
    """Unified root-cause report feeding 'المشكلات والأخطاء', NL commands, and optimization planner."""

    fault_cards: List[DiagnosticFaultCard] = Field(default_factory=list)
    app_impacts: List[ApplicationImpactEntry] = Field(default_factory=list)
    primary_root_cause_ar: str = ""
    summary_ar: str = ""


def _dns_issue_detected(dns_report: Optional[DnsDiagnosticsReport]) -> bool:
    if not dns_report:
        return False
    cur = set(dns_report.configured_dns_servers or [])
    if dns_report.router_dns_server:
        cur.add(dns_report.router_dns_server)
    if dns_report.recommended_dns and cur and dns_report.recommended_dns not in cur:
        return True
    for t in dns_report.targets:
        if t.role in ("configured", "router") and t.is_applicable:
            if t.status in ("unreachable", "failed"):
                return True
            if t.median_ms is not None and t.median_ms >= 80.0:
                return True
    return False


TARGET_FIELD_AR: Dict[str, str] = {
    "channel": "القناة اللاسلكية",
    "channel_width": "عرض القناة",
    "radio_5ghz_enabled": "بث نطاق 5 GHz",
    "qos_enabled": "جودة الخدمة SQM / QoS",
    "wmm_enabled": "أولوية الوسائط WMM",
    "security_mode": "تشفير شبكة Wi-Fi",
    "dns_servers": "خوادم DNS",
    "wan_line_snr": "خط اتصال WAN / DSL",
    "dhcp_lease_time": "مدة إيجار DHCP",
    "upnp_enabled": "توجيه المنافذ التلقائي UPnP",
    "firewall_level": "جدار الحماية SPI",
    "tx_power": "طاقة البث اللاسلكي",
    "dhcp_enabled": "خادم DHCP",
}


class RootCauseAnalysisService:
    """Produces comprehensive 14-field Arabic diagnostic cards and application-level root causes."""

    @staticmethod
    def _sev_rank(sev: str) -> int:
        return {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFORMATIONAL": 4}.get(sev, 5)

    def build_report(
        self,
        *,
        discovery: Optional[RouterDiscoveryResult] = None,
        capabilities: Optional[RouterCapabilities] = None,
        config_model: Optional[RouterConfigurationModel] = None,
        router_config: Optional[RouterConfigurationSnapshot] = None,
        telemetry: Optional[WifiInterfaceTelemetry] = None,
        channel_report: Optional[FullChannelAnalysisReport] = None,
        network_report: Optional[NetworkDiagnosticsReport] = None,
        dns_report: Optional[DnsDiagnosticsReport] = None,
        speed_report: Optional[SpeedTestReport] = None,
        bufferbloat_report: Optional[BufferbloatDiagnosticsReport] = None,
        devices: Optional[List[ConnectedDeviceRecord]] = None,
        proposals: Optional[List[RouterChangeProposal]] = None,
        qos_compat_findings: Optional[List[DiagnosticFaultCard]] = None,
    ) -> RootCauseReport:
        cards: List[DiagnosticFaultCard] = []
        snap = router_config or (config_model.snapshot if config_model else None)
        prop_by_cat: Dict[str, List[RouterChangeProposal]] = {}
        for p in proposals or []:
            prop_by_cat.setdefault(p.category, []).append(p)

        # 1) Router Security & TLS/Auth Posture from Discovery
        if discovery is not None:
            if discovery.preferred_url and discovery.preferred_url.startswith("http://"):
                cards.append(
                    DiagnosticFaultCard(
                        card_id="fault_router_http_plain",
                        issue_name="واجهة إدارة الراوتر غير مشفرة (HTTP)",
                        location="الراوتر / إدارة الشبكة المحلية",
                        current_setting=discovery.preferred_url,
                        verified_value_or_state="بروتوكول HTTP بدون تشفير TLS",
                        why_problem="تسجيل الدخول عبر HTTP يرسل كلمة مرور المدير والنص الإداري بدون تشفير داخل الشبكة المحلية.",
                        evidence_and_measurements=[f"الرابط المكتشف: {discovery.preferred_url}"],
                        expected_impact="إمكانية التقاط بيانات إدارة الراوتر من أجهزة محلية أخرى.",
                        affected_devices_or_apps=["واجهة إدارة الراوتر"],
                        severity="MEDIUM",
                        recommended_solution="فعّل HTTPS لإدارة الراوتر المحلية إذا كان الطراز يدعمها.",
                        can_netguard_execute=False,
                        execution_capability_note="لا يعدّل NetGuard منفذ الإدارة تلقائياً لتفادي فقدان الوصول.",
                        requires_user_approval=True,
                        rollback_supported=False,
                        post_execution_verification="فحص تشخيصي إرشادي فقط.",
                        action_type="manual_only",
                    )
                )

            if not (config_model and config_model.capabilities and config_model.capabilities.hardware_verified):
                vendor_lbl = discovery.hardware_vendor or discovery.detected_vendor or "غير معروف"
                isp_lbl = f" (علامة مزود الخدمة: {discovery.isp_brand})" if discovery.isp_brand else ""
                cards.append(
                    DiagnosticFaultCard(
                        card_id="fault_router_unauth",
                        issue_name="لم يتم فحص إعدادات الراوتر الداخلية بعد (يتطلب تسجيل الدخول)",
                        location=f"الراوتر ({discovery.gateway_ip or 'غير محدد'})",
                        current_setting=f"تم التعرف السلبي على: {vendor_lbl} {discovery.detected_model or ''}{isp_lbl}".strip(),
                        verified_value_or_state="الجلسة غير مصادق عليها — القيم الداخلية غير مقروءة بعد",
                        why_problem="بدون تسجيل الدخول ببيانات المدير لا يمكن فحص WAN وDHCP وQoS والجدار الناري أو التحقق من الأخطاء الداخلية.",
                        evidence_and_measurements=[
                            f"المنافذ المتاحة: {discovery.reachable_ports}",
                            f"الأدلة: {', '.join(discovery.detection_evidence[:4]) or 'اكتشاف الشبكة'}",
                        ],
                        expected_impact="تقتصر الرؤية الحالية على قياسات Windows Wi-Fi والإنترنت والجار المحليين فقط.",
                        affected_devices_or_apps=["تغطية تشخيص الراوتر الكامل (32 مجالاً)"],
                        severity="INFORMATIONAL",
                        recommended_solution="أدخل اسم المستخدم وكلمة مرور الراوتر في تبويب 'اتصال الراوتر' واضغط 'محاولة اتصال واحدة وقراءة الإعدادات'.",
                        can_netguard_execute=True,
                        execution_capability_note="بمجرد إدخال بيانات الدخول، يقوم NetGuard بفحص جميع الصفحات تلقائياً.",
                        requires_user_approval=True,
                        rollback_supported=False,
                        post_execution_verification="في انتظار تسجيل الدخول المصادق.",
                        action_type="info_only",
                    )
                )

        # 2) Wi-Fi Signal Strength / Distance & Band
        is_wifi_connected = bool(
            telemetry and str(telemetry.connection_state or "").lower() == "connected"
        )
        if telemetry and is_wifi_connected and telemetry.rssi_dbm is not None:
            if telemetry.rssi_dbm <= -74:
                sev = "CRITICAL" if telemetry.rssi_dbm <= -82 else "HIGH"
                loc_str = f"رابط Wi-Fi ({telemetry.interface_name or 'WLAN'}" + (f" / {telemetry.band}" if telemetry.band else "") + ")"
                cards.append(
                    DiagnosticFaultCard(
                        card_id="fault_weak_wifi_signal",
                        issue_name="ضعف شديد في إشارة Wi-Fi الواصلة للجهاز",
                        location=loc_str,
                        current_setting=f"{telemetry.rssi_dbm} dBm (عرض القناة {telemetry.channel_width_mhz or '؟'} MHz)",
                        verified_value_or_state=f"جودة إشارة {telemetry.signal_quality_pct}% | سرعة ربط TX={telemetry.tx_link_rate_mbps} Mbps",
                        why_problem="عند انخفاض الإشارة تحت -74 dBm ترتفع إعادة إرسال الحزم PHY وتنخفض سرعة التعديل ويزداد التذبذب.",
                        evidence_and_measurements=[
                            f"RSSI المقاس = {telemetry.rssi_dbm} dBm",
                            f"TX/RX Link Rate = {telemetry.tx_link_rate_mbps}/{telemetry.rx_link_rate_mbps} Mbps",
                        ],
                        expected_impact="تقطيع في مكالمات Zoom/Teams، ارتفاع ping في الألعاب، وهبوط مفاجئ في السرعة.",
                        affected_devices_or_apps=["هذا الكمبيوتر", "Zoom / Teams", "الألعاب التفاعلية", "البث عالي الدقة"],
                        severity=sev,
                        recommended_solution="قرّب الجهاز من الراوتر أو انتقل إلى كابل Ethernet أو استخدم نقطة وصول سلكية أقرب.",
                        can_netguard_execute=False,
                        execution_capability_note="المسافة والعوائق الجدارية فيزيائية ولا يمكن إصلاحها برمجياً وحدها.",
                        requires_user_approval=False,
                        rollback_supported=False,
                        post_execution_verification="لم يتم التنفيذ بعد",
                        causal_chain=CausalChainExplanation(
                            symptom="تقطيع الصوت وبطء التصفح",
                            contributing_factors=["جدران أو مسافة بعيدة عن نقطة الوصول", f"عرض نطاق عريض على إشارة {telemetry.rssi_dbm} dBm"],
                            root_cause="ضعف مستوى الإشارة المستلمة (RSSI)",
                            chain_summary_ar=f"المسافة/العوائق → RSSI {telemetry.rssi_dbm} dBm → إعادة إرسال الحزم → ارتفاع التذبذب وهبوط السرعة",
                        ),
                        action_type="manual_only",
                    )
                )

            has_5g = bool(snap and "5 GHz" in snap.radios and snap.radios["5 GHz"].enabled is not False) or bool(
                channel_report
                and "5 GHz" in channel_report.bands
                and any(
                    sc.co_channel_ap_count > 0 or sc.overlapping_ap_count > 0
                    for sc in channel_report.bands["5 GHz"].channel_scores
                )
            )
            if telemetry.band == "2.4 GHz" and has_5g and telemetry.rssi_dbm >= -67:
                cards.append(
                    DiagnosticFaultCard(
                        card_id="fault_wrong_band_24",
                        issue_name="الجهاز متصل بنطاق 2.4 GHz المزدحم رغم توفر 5 GHz",
                        location=f"اتصال Wi-Fi ({telemetry.ssid or 'SSID'})",
                        current_setting=f"2.4 GHz — القناة {telemetry.channel or '؟'}",
                        verified_value_or_state="يتوفر نطاق 5 GHz بإشارة جيدة",
                        why_problem="نطاق 2.4 GHz يملك 3 قنوات غير متداخلة فقط ويتأثر بشبكات الجيران والبلوتوث، مما يرفع زمن الانتظار.",
                        evidence_and_measurements=[
                            f"النطاق الحالي: 2.4 GHz (RSSI {telemetry.rssi_dbm} dBm)",
                            f"سرعة الربط الحالية: {telemetry.tx_link_rate_mbps} Mbps",
                        ],
                        expected_impact="بطء ملحوظ مقارنة بقدرة الخط وارتفاع تذبذب الـ Ping تحت الضغط.",
                        affected_devices_or_apps=["هذا الكمبيوتر", "المكالمات الفيديوية", "الألعاب", "التحميلات"],
                        severity="MEDIUM",
                        recommended_solution="اتصل بشبكة 5 GHz الخاصة بالراوتر أو فعّل Band Steering إذا كانت الإشارة قريبة.",
                        can_netguard_execute=bool(prop_by_cat.get("band_steering")),
                        execution_capability_note="يتطلب ربط الجهاز بشبكة 5 GHz من إعدادات Wi-Fi في Windows أو عبر الراوتر.",
                        requires_user_approval=True,
                        rollback_supported=True,
                        action_type="manual_only",
                    )
                )

        # 3) Channel Congestion & Adjacent Overlap
        if channel_report:
            for band, bres in channel_report.bands.items():
                cur_ch = bres.current_channel
                cur_sc = bres.current_channel_score
                best = bres.recommended_channels[0] if bres.recommended_channels else None
                if cur_ch and cur_sc and (
                    cur_sc.interference_level in ("high", "severe")
                    or (best and best.channel != cur_ch and cur_sc.total_score - best.total_score >= 4.0)
                ):
                    ch_props = [p for p in prop_by_cat.get("wifi_channel", []) if p.band == band]
                    linked = ch_props[0] if ch_props else None
                    can_exec = bool(capabilities and capabilities.supports_channel_write and linked and linked.supported_by_adapter)
                    cards.append(
                        DiagnosticFaultCard(
                            card_id=f"fault_ch_{band.replace(' ', '_')}",
                            issue_name=f"ازدحام القناة اللاسلكية الحالية ({band} — القناة {cur_ch})",
                            location=f"راوتر / راديو {band} — إعداد القناة",
                            current_setting=f"القناة {cur_ch} (نقاط الازدحام {cur_sc.total_score:.1f} — {cur_sc.interference_level})",
                            verified_value_or_state=f"شبكات متداخلة={cur_sc.co_channel_ap_count} نفس القناة + {cur_sc.overlapping_ap_count} مجاورة | أفضل بديل: Ch {best.channel if best else '؟'} ({best.total_score:.1f} نقطة)",
                            why_problem="تشارك نفس القناة أو التداخل الجزئي مع شبكات جيران قوية يجبر بطاقة Wi-Fi على الانتظار (CSMA/CA) قبل الإرسال.",
                            evidence_and_measurements=[
                                cur_sc.formula_notes,
                                best.reason if best else "",
                            ],
                            expected_impact="ارتفاع تذبذب الـ Ping وتقطع الصوت وتباطؤ سرعة النقل اللاسلكي.",
                            affected_devices_or_apps=["جميع الأجهزة اللاسلكية على هذا النطاق", "Zoom / Teams", "الألعاب"],
                            severity="HIGH" if cur_sc.interference_level == "severe" else "MEDIUM",
                            recommended_solution=f"تغيير قناة {band} إلى القناة {best.channel} ثم إعادة قياس الازدحام وزمن الاستجابة." if best else "تغيير القناة لقناة أقل ازدحاماً.",
                            can_netguard_execute=can_exec,
                            execution_capability_note=(
                                "يدعم الراوتر المصادق عليه تغيير القناة مع نسخة احتياطية والتحقق التلقائي."
                                if can_exec
                                else "يتطلب تسجيل دخول مصادق لمحول يدعم كتابة القناة أو تعديله يدوياً في صفحة Wireless بالراوتر."
                            ),
                            requires_user_approval=True,
                            rollback_supported=can_exec,
                            linked_proposal=linked,
                            causal_chain=CausalChainExplanation(
                                symptom="تذبذب التأخير وتباطؤ Wi-Fi رغم قرب المسافة",
                                contributing_factors=[f"{cur_sc.co_channel_ap_count} شبكات على نفس القناة", f"{cur_sc.overlapping_ap_count} شبكات متداخلة جانبياً"],
                                root_cause=f"ازدحام القناة {cur_ch} على نطاق {band}",
                                chain_summary_ar=f"ازدحام القناة {cur_ch} → تصادم وتأخر انتظار الهواء → ارتفاع Jitter وتذبذب السرعة",
                            ),
                            action_type="router_change" if can_exec else "manual_only",
                        )
                    )

        # 4) Bufferbloat / Queue Saturation
        if bufferbloat_report and bufferbloat_report.overall_grade in ("C", "D", "F"):
            ul_d = bufferbloat_report.upload_phase.delta_over_idle_ms if bufferbloat_report.upload_phase else None
            dl_d = bufferbloat_report.download_phase.delta_over_idle_ms if bufferbloat_report.download_phase else None
            idle_ms = bufferbloat_report.idle_phase.avg_ms if bufferbloat_report.idle_phase else None
            sqm_prop = (prop_by_cat.get("qos_sqm") or [None])[0]
            can_exec = bool(capabilities and capabilities.supports_sqm_or_qos_write and sqm_prop)
            cards.append(
                DiagnosticFaultCard(
                    card_id="fault_bufferbloat",
                    issue_name=f"تضخم زمن الاستجابة تحت التحميل (Bufferbloat — التقدير {bufferbloat_report.overall_grade})",
                    location="طوابير الراوتر / وصلة WAN والإنترنت",
                    current_setting=f"تقدير {bufferbloat_report.overall_grade} (SQM في الراوتر: {snap.qos_enabled if snap else 'غير مؤكد'})",
                    verified_value_or_state=f"Idle={idle_ms} ms | زيادة التنزيل=+{dl_d} ms | زيادة الرفع=+{ul_d} ms",
                    why_problem="امتلاء مخازن الراوتر (Queues) أثناء رفع الملفات أو التنزيل يحجز حزم المكالمات والألعاب خلف حزم ضخمة.",
                    evidence_and_measurements=[
                        bufferbloat_report.summary,
                        f"QoS في هذا الجهاز: {'مفعّل' if bufferbloat_report.qos_was_active else 'غير مفعّل'}",
                    ],
                    expected_impact="قفزات Ping عنيفة وتجمد الصوت/الصورة في Zoom عند قيام أي جهاز بتحميل أو رفع ملفات.",
                    affected_devices_or_apps=["Zoom / Teams", "مكالمات الصوت", "الألعاب التفاعلية", "الشبكة المنزلية كاملة"],
                    severity="CRITICAL" if bufferbloat_report.overall_grade == "F" else "HIGH",
                    recommended_solution=(
                        "فعّل SQM (FQ-CoDel/CAKE) أو تحديد سرعة WAN في الراوتر أقل بنسبة 5–10% من السرعة القصوى، "
                        "مع تفعيل حماية NetGuard QoS لهذا الكمبيوتر."
                    ),
                    can_netguard_execute=can_exec,
                    execution_capability_note=(
                        "يستطيع NetGuard تفعيل QoS المحلي لهذا الجهاز فوراً، وتفعيل SQM على الراوتر إذا دعم المحول ذلك."
                    ),
                    requires_user_approval=True,
                    rollback_supported=True,
                    linked_proposal=sqm_prop,
                    causal_chain=CausalChainExplanation(
                        symptom="ارتفاع Ping مفاجئ وتقطيع المكالمات وقت التحميل أو الرفع",
                        contributing_factors=["غياب إدارة الطوابير SQM/FQ-CoDel على وصلة WAN بالراوتر"],
                        root_cause="امتلاء طوابير الإرسال (Bufferbloat)",
                        chain_summary_ar=f"امتلاء الرفع/التنزيل → احتجاز الحزم في الراوتر (+{ul_d or dl_d} ms) → قفزات Ping وتقطيع Zoom",
                    ),
                    action_type="router_change" if can_exec else "local_qos",
                )
            )

        # 5) DNS Diagnostics
        if _dns_issue_detected(dns_report):
            assert dns_report is not None
            dns_prop = (prop_by_cat.get("dns") or [None])[0]
            can_router_dns = bool(capabilities and capabilities.supports_dns_config_write and dns_prop)
            cards.append(
                DiagnosticFaultCard(
                    card_id="fault_dns_slow_or_broken",
                    issue_name="بطء أو تعثر خادم DNS الحالي",
                    location="إعدادات DNS (الراوتر / Windows)",
                    current_setting=", ".join(dns_report.configured_dns_servers) or (dns_report.router_dns_server or "تلقائي"),
                    verified_value_or_state=f"أفضل بديل مقاس: {dns_report.recommended_dns or '1.1.1.1'} ({dns_report.summary})",
                    why_problem="بطء ترجمة أسماء النطاقات يضيف تأخيراً قبل فتح كل صفحة جديدة أو بدء مكالمة جديدة.",
                    evidence_and_measurements=[dns_report.summary],
                    expected_impact="تباطؤ فتح المواقع والتطبيقات عند أول اتصال بالخادم.",
                    affected_devices_or_apps=["المتصفح", "تطبيقات الاجتماعات", "الألعاب", "جميع الأجهزة"],
                    severity="MEDIUM",
                    recommended_solution=f"التبديل إلى خادم DNS الأسرع ({dns_report.recommended_dns or '1.1.1.1'}) عبر الراوتر أو بطاقة الشبكة.",
                    can_netguard_execute=True,
                    execution_capability_note=(
                        "يمكن لـ NetGuard تطبيق DNS على Windows مباشرة أو عبر الراوتر إذا دعمت واجهته التعديل."
                    ),
                    requires_user_approval=True,
                    rollback_supported=True,
                    linked_proposal=dns_prop,
                    action_type="router_change" if can_router_dns else "local_dns",
                )
            )

        # 6) Upstream WAN / Packet Loss / ISP
        if network_report:
            gw_loss = network_report.gateway_ping.packet_loss_pct
            inet_loss = network_report.internet_ping.packet_loss_pct
            inet_status = network_report.internet_ping.status
            if inet_status in ("unreachable", "failed") or inet_loss >= 2.0:
                cards.append(
                    DiagnosticFaultCard(
                        card_id="fault_wan_upstream_loss",
                        issue_name="فقد حزم أو انقطاع في مسار الإنترنت الخارجي (ISP/WAN)",
                        location="خط الإنترنت الخارجي (WAN / المزود)",
                        current_setting=f"فقد البوابة={gw_loss}% | حالة الإنترنت={inet_status}",
                        verified_value_or_state=f"فقد الإنترنت={inet_loss}% | متوسط تأخير الإنترنت={network_report.internet_ping.avg_ms or '؟'} ms",
                        why_problem="وجود فقد حزم خارج الشبكة المنزلية يؤكد مشكلة في خط الـ DSL/الفايبر أو عقدة مزود الخدمة وليس داخل الواي فاي وحده.",
                        evidence_and_measurements=[network_report.diagnosis_summary] + network_report.notes[:2],
                        expected_impact="انقطاعات متكررة، فشل تحميل الصفحات، وتجمد المكالمات والألعاب.",
                        affected_devices_or_apps=["جميع الأجهزة والتطبيقات"],
                        severity="CRITICAL" if inet_status in ("unreachable", "failed") else "HIGH",
                        recommended_solution="تحقق من إحصائيات خط DSL/الفايبر (SNR/CRC) وجودة التوصيل السلكي ثم تواصل مع مزود الخدمة بالدليل المسجل.",
                        can_netguard_execute=False,
                        execution_capability_note="أعطال الخط الخارجي والمزود لا تُصلح برمجياً وتحتاج تدخلاً على الخط.",
                        requires_user_approval=False,
                        rollback_supported=False,
                        action_type="manual_only",
                    )
                )

        # 7) Router Proposals not yet represented
        covered_ids = {c.linked_proposal.proposal_id for c in cards if c.linked_proposal is not None}
        for prop in proposals or []:
            if prop.proposal_id in covered_ids:
                continue
            sev_map = {"high": "HIGH", "medium": "MEDIUM", "low": "LOW"}
            field_ar = TARGET_FIELD_AR.get(prop.target_field, prop.target_field)
            cards.append(
                DiagnosticFaultCard(
                    card_id=f"fault_prop_{prop.proposal_id}",
                    issue_name=prop.title,
                    location=f"الراوتر ({prop.band or prop.category})",
                    current_setting=str(prop.current_value or "غير محدد"),
                    verified_value_or_state=f"المقترح: {prop.proposed_value}",
                    why_problem=prop.reason,
                    evidence_and_measurements=prop.evidence or [prop.reason],
                    expected_impact=prop.expected_impact,
                    affected_devices_or_apps=["الشبكة اللاسلكية والأجهزة المتصلة"],
                    severity=sev_map.get(prop.risk_level, "MEDIUM"),  # type: ignore[arg-type]
                    recommended_solution=f"تعديل «{field_ar}» من ({prop.current_value or 'غير محدد'}) إلى ({prop.proposed_value}).",
                    can_netguard_execute=prop.supported_by_adapter,
                    execution_capability_note=(
                        "قابل للتنفيذ التلقائي عبر المحول المصادق عليه مع تراجع فوري."
                        if prop.supported_by_adapter
                        else "تعديل يدوي موصى به في صفحة الراوتر لأن المحول لا يدعم الكتابة لهذا الإعداد."
                    ),
                    requires_user_approval=True,
                    rollback_supported=prop.supported_by_adapter,
                    linked_proposal=prop,
                    action_type="router_change" if prop.supported_by_adapter else "manual_only",
                )
            )

        if qos_compat_findings:
            cards.extend(qos_compat_findings)

        cards.sort(key=lambda c: self._sev_rank(c.severity))

        app_impacts = self._build_application_impacts(
            telemetry=telemetry,
            channel_report=channel_report,
            network_report=network_report,
            dns_report=dns_report,
            speed_report=speed_report,
            bufferbloat_report=bufferbloat_report,
            devices=devices,
        )

        primary = cards[0].issue_name if cards else "لا توجد أخطاء حرجة مكتشفة في القياسات الحالية."
        summary = (
            f"تم رصد {len(cards)} ملاحظة/مشكلة تشخيصية ({sum(1 for c in cards if c.severity in ('CRITICAL', 'HIGH'))} عالية/حرجة)."
            if cards
            else "لم يتم رصد أخطاء تهيئة أو اختناقات شبكة حرجة في الفحص الأخير."
        )
        return RootCauseReport(
            fault_cards=cards,
            app_impacts=app_impacts,
            primary_root_cause_ar=primary,
            summary_ar=summary,
        )

    @staticmethod
    def _build_application_impacts(
        *,
        telemetry: Optional[WifiInterfaceTelemetry],
        channel_report: Optional[FullChannelAnalysisReport],
        network_report: Optional[NetworkDiagnosticsReport],
        dns_report: Optional[DnsDiagnosticsReport],
        speed_report: Optional[SpeedTestReport],
        bufferbloat_report: Optional[BufferbloatDiagnosticsReport],
        devices: Optional[List[ConnectedDeviceRecord]],
    ) -> List[ApplicationImpactEntry]:
        impacts: List[ApplicationImpactEntry] = []

        bb_bad = bool(bufferbloat_report and bufferbloat_report.overall_grade in ("C", "D", "F"))
        weak_sig = bool(telemetry and telemetry.rssi_dbm is not None and telemetry.rssi_dbm <= -74)
        wrong_24 = bool(telemetry and telemetry.band == "2.4 GHz")
        loss_high = bool(
            network_report
            and (network_report.gateway_ping.packet_loss_pct >= 2.0 or network_report.internet_ping.packet_loss_pct >= 2.0)
        )
        dns_bad = _dns_issue_detected(dns_report)
        ch_bad = bool(
            channel_report
            and any(b.current_channel_score and b.current_channel_score.interference_level in ("high", "severe") for b in channel_report.bands.values())
        )
        dl_mbps = speed_report.download_mbps if speed_report else None
        ul_mbps = speed_report.upload_mbps if speed_report else None
        dev_count = len([d for d in (devices or []) if d.connection_status != "stale"])

        call_causes = []
        if bb_bad:
            call_causes.append("تضخم زمن الانتظار تحت التحميل (Bufferbloat)")
        if weak_sig and telemetry:
            call_causes.append(f"ضعف إشارة الواي فاي ({telemetry.rssi_dbm} dBm)")
        if ch_bad or wrong_24:
            call_causes.append("ازدحام قناة Wi-Fi أو البقاء على 2.4 GHz")
        if loss_high:
            call_causes.append("فقد حزم على المسار أو خط المزود")
        if ul_mbps is not None and ul_mbps < 2.0:
            call_causes.append(f"سرعة الرفع منخفضة ({ul_mbps} Mbps)")
        impacts.append(
            ApplicationImpactEntry(
                app_category="video_calls",
                app_title_ar="مكالمات الفيديو والصوت\n(Zoom / Teams / WhatsApp)",
                status_ar="معرّض للتقطيع والتأخير" if call_causes else "مستقر ومناسب للاجتماعات",
                severity="HIGH" if (bb_bad or loss_high) else ("MEDIUM" if call_causes else "GOOD"),
                root_causes_ar=call_causes or ["زمن الاستجابة وتذبذب الإشارة ضمن النطاق الجيد."],
                fix_action_ar="حماية NetGuard QoS + الانتقال إلى 5 GHz وتخفيف الرفع في الأجهزة الأخرى.",
            )
        )

        game_causes = list(call_causes)
        if network_report and network_report.internet_ping.avg_ms and network_report.internet_ping.avg_ms > 90:
            game_causes.append(f"زمن الوصول الخارجي مرتفع ({network_report.internet_ping.avg_ms:.1f} ms)")
        impacts.append(
            ApplicationImpactEntry(
                app_category="gaming",
                app_title_ar="الألعاب التفاعلية\n(Online Gaming)",
                status_ar="ارتفاع Ping أو Jitter" if game_causes else "استجابة منخفضة ومستقرة",
                severity="HIGH" if (bb_bad or loss_high) else ("MEDIUM" if game_causes else "GOOD"),
                root_causes_ar=game_causes or ["لا يوجد تضخم طوابير أو فقد حزم مؤثر."],
                fix_action_ar="اختيار قناة غير مزدحمة وتفعيل SQM/QoS بالراوتر مع الاتصال السلكي أو 5 GHz.",
            )
        )

        stream_causes = []
        if weak_sig:
            stream_causes.append("ضعف إشارة Wi-Fi يحد سرعة النقل")
        if dl_mbps is not None and dl_mbps < 10.0:
            stream_causes.append(f"سرعة التنزيل الفعلية منخفضة ({dl_mbps} Mbps)")
        if ch_bad:
            stream_causes.append("ازدحام القناة اللاسلكية")
        impacts.append(
            ApplicationImpactEntry(
                app_category="streaming_downloads",
                app_title_ar="البث المرئي والتحميلات الكبيرة\n(Streaming / Downloads)",
                status_ar="انخفاض سرعة أو تباطؤ 4K" if stream_causes else "مناسب للبث عالي الدقة",
                severity="MEDIUM" if stream_causes else "GOOD",
                root_causes_ar=stream_causes or ["سرعة التنزيل وإشارة الراديو كافيتان."],
                fix_action_ar="تحسين القناة اللاسلكية أو استخدام 5 GHz / Ethernet.",
            )
        )

        browse_causes = []
        if dns_bad:
            browse_causes.append("بطء خادم DNS يؤخر بدء فتح المواقع")
        if loss_high:
            browse_causes.append("فقد حزم في المسار الخارجي")
        impacts.append(
            ApplicationImpactEntry(
                app_category="browsing",
                app_title_ar="تصفح الويب\n(Web Browsing)",
                status_ar="تأخر قبل تحميل الصفحات" if browse_causes else "سريع ومستجيب",
                severity="MEDIUM" if browse_causes else "GOOD",
                root_causes_ar=browse_causes or ["استجابة DNS والمسار جيدة."],
                fix_action_ar="تحديث DNS إلى الخادم الأسرع (مثل 1.1.1.1).",
            )
        )

        multi_causes = []
        if dev_count >= 6:
            multi_causes.append(f"عدد الأجهزة النشطة في الشبكة ({dev_count} جهازاً) يرفع التنافس على الهواء وخط WAN")
        if bb_bad:
            multi_causes.append("غياب توزيع عادل للطوابير (SQM) في الراوتر")
        impacts.append(
            ApplicationImpactEntry(
                app_category="multi_user",
                app_title_ar="ضغط عدة مستخدمين على الشبكة المنزلية",
                status_ar="احتمال تزاحم الأجهزة" if multi_causes else "متوازن حالياً",
                severity="MEDIUM" if multi_causes else "GOOD",
                root_causes_ar=multi_causes or ["حمل الأجهزة الحالية ضمن الحدود المستقرة."],
                fix_action_ar="استخدام QoS بالراوتر لتقييد التحميلات على بقية الأجهزة أو جدولة التحديثات.",
            )
        )

        return impacts
