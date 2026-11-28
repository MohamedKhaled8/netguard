"""Section 13 QoS Compatibility Analyzer ensuring safe coexistence between Router QoS/SQM and NetGuard Pass 4."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.wifi.models import BufferbloatDiagnosticsReport, RouterConfigurationSnapshot, SpeedTestReport
from app.wifi.root_cause import DiagnosticFaultCard


class QoSCompatibilityReport(BaseModel):
    compatible: bool = True
    netguard_qos_active: bool = False
    netguard_policies_count: int = 0
    router_qos_enabled: Optional[bool] = None
    router_sqm_enabled: Optional[bool] = None
    router_qos_mode: Optional[str] = None
    coexistence_status_ar: str = ""
    findings: List[DiagnosticFaultCard] = Field(default_factory=list)
    recommendations_ar: List[str] = Field(default_factory=list)


class QoSCompatibilityAnalyzer:
    """Checks router QoS/SQM/WMM alongside NetGuard Pass 4 local Windows QoS policies."""

    def analyze(
        self,
        *,
        qos_summary: Dict[str, Any],
        router_config: Optional[RouterConfigurationSnapshot] = None,
        bufferbloat_report: Optional[BufferbloatDiagnosticsReport] = None,
        speed_report: Optional[SpeedTestReport] = None,
        wmm_disabled: bool = False,
    ) -> QoSCompatibilityReport:
        ng_active = bool(qos_summary.get("master_enabled"))
        ng_count = int(qos_summary.get("active_policies_count") or 0)
        r_qos = router_config.qos_enabled if router_config else None
        r_sqm = router_config.sqm_enabled if router_config else None
        r_mode = router_config.qos_mode if router_config else None

        findings: List[DiagnosticFaultCard] = []
        recs: List[str] = []
        compatible = True

        # 1) Router QoS enabled while WMM is disabled on wireless
        if wmm_disabled and (r_qos or ng_active):
            compatible = False
            findings.append(
                DiagnosticFaultCard(
                    card_id="qos_compat_wmm_off",
                    issue_name="تعارض WMM المعطّل مع أولوية QoS اللاسلكية",
                    location="الراوتر / Wireless WMM",
                    current_setting="WMM Disabled",
                    verified_value_or_state="QoS يحتاج WMM لتفعيل أولوية حزم DSCP عبر الواي فاي",
                    why_problem="تعطيل WMM يلغي طوابير أولوية الوسائط اللاسلكية ويبطئ السرعة رغم تفعيل QoS.",
                    evidence_and_measurements=["WMM معطّل في إعدادات الراوتر."],
                    expected_impact="فقدان أولوية مكالمات الفيديو لاسلكياً.",
                    affected_devices_or_apps=["Zoom / Teams على Wi-Fi"],
                    severity="HIGH",
                    recommended_solution="أعد تفعيل WMM في إعدادات الواي فاي بالراوتر.",
                    can_netguard_execute=False,
                    requires_user_approval=True,
                    rollback_supported=False,
                    action_type="manual_only",
                )
            )

        # 2) NetGuard Pass 4 local QoS active + Bufferbloat severe -> highlight scope honesty
        if ng_active and bufferbloat_report and bufferbloat_report.overall_grade in ("D", "F") and not r_sqm:
            recs.append(
                "سياسة NetGuard QoS (Pass 4) تحمي حركة هذا الكمبيوتر فقط؛ فعّل SQM/QoS في الراوتر لضبط طوابير بقية أجهزة المنزل."
            )

        # 3) Check whether NetGuard QoS upload cap severely throttles tested WAN speed
        ng_cap_kbps = qos_summary.get("upload_cap_kbps")
        wan_up = speed_report.upload_mbps if speed_report else None
        if isinstance(ng_cap_kbps, (int, float)) and isinstance(wan_up, (int, float)) and wan_up > 0:
            if ng_cap_kbps > 0 and (ng_cap_kbps / 1000.0) < wan_up * 0.25:
                recs.append(
                    f"تنبيه: حد الرفع في NetGuard المحلي ({ng_cap_kbps} kbps) أقل من 25% من سرعة الرفع المقاسة ({wan_up} Mbps) — تأكد من ملاءمته لعدم تقييد هذا الجهاز."
                )

        if not recs:
            recs.append(
                "سياسات NetGuard QoS المحلية (Pass 4) متوافقة ولا تتعارض مع إعدادات الراوتر المرصودة."
            )

        status_ar = (
            "متوافق — NetGuard يحمي هذا الجهاز بالـ DSCP/التقييد المحلي بدون تعارض"
            if compatible
            else "تم رصد تعارض يتطلب المراجعة (تحقق من تفعيل WMM وتنسيق QoS)"
        )
        return QoSCompatibilityReport(
            compatible=compatible,
            netguard_qos_active=ng_active,
            netguard_policies_count=ng_count,
            router_qos_enabled=r_qos,
            router_sqm_enabled=r_sqm,
            router_qos_mode=r_mode,
            coexistence_status_ar=status_ar,
            findings=findings,
            recommendations_ar=recs,
        )
