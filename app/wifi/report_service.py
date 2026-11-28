"""Section 20 & Credential-Safe Unified Network Health & Router Audit Report Generator."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.wifi.models import (
    BufferbloatDiagnosticsReport,
    ConnectedDeviceRecord,
    DnsDiagnosticsReport,
    FullChannelAnalysisReport,
    NetworkDiagnosticsReport,
    RouterDiscoveryResult,
    SpeedTestReport,
    WifiInterfaceTelemetry,
    utc_now,
)
from app.wifi.optimization import ActionHistoryEntry
from app.wifi.qos_compatibility import QoSCompatibilityReport
from app.wifi.root_cause import RootCauseReport
from app.wifi.router.models_config import RouterConfigurationModel, sanitize_setting_value


class NetworkHealthReportService:
    """Produces sanitized Markdown and JSON reports excluding ALL passwords, PSKs, tokens, and cookies."""

    @staticmethod
    def build_markdown_report(
        *,
        discovery: Optional[RouterDiscoveryResult] = None,
        config_model: Optional[RouterConfigurationModel] = None,
        telemetry: Optional[WifiInterfaceTelemetry] = None,
        channel_report: Optional[FullChannelAnalysisReport] = None,
        network_report: Optional[NetworkDiagnosticsReport] = None,
        dns_report: Optional[DnsDiagnosticsReport] = None,
        speed_report: Optional[SpeedTestReport] = None,
        bufferbloat_report: Optional[BufferbloatDiagnosticsReport] = None,
        devices: Optional[List[ConnectedDeviceRecord]] = None,
        root_cause: Optional[RootCauseReport] = None,
        qos_compat: Optional[QoSCompatibilityReport] = None,
        history: Optional[List[ActionHistoryEntry]] = None,
    ) -> str:
        lines: List[str] = [
            f"# تقرير صحة الشبكة والراوتر — NetGuard AI ({utc_now().strftime('%Y-%m-%d %H:%M UTC')})",
            "",
            "> **ملاحظة أمان:** تم حجب جميع كلمات المرور ومفاتيح Wi-Fi ورموز الجلسات من هذا التقرير.",
            "",
        ]

        if discovery:
            lines.extend([
                "## 1. هوية الراوتر والاكتشاف",
                f"- بوابة الشبكة: `{discovery.gateway_ip}` | MAC: `{discovery.gateway_mac}`",
                f"- المصنّع الفعلي للعتاد: `{discovery.hardware_vendor or discovery.detected_vendor or 'غير معروف'}` | الطراز: `{discovery.detected_model or 'غير محدد'}`",
                f"- علامة مزود الخدمة (ISP): `{discovery.isp_brand or 'غير محدد'}` | المحول المستخدم: `{discovery.adapter_id}`",
                f"- المنافذ المفتوحة: `{discovery.reachable_ports}` | ثقة التعرف: `{discovery.detection_confidence}`",
                "",
            ])

        if config_model and config_model.coverage:
            cov = config_model.coverage
            lines.extend([
                "## 2. تغطية فحص الراوتر (32 مجالاً)",
                f"- {cov.honesty_statement}",
                f"- صفحات مفحوصة بالكامل: {cov.fully_inspected_pages} | جزئياً: {cov.partially_inspected_pages} | غير متاحة/غير مدعومة: {cov.not_accessible_pages + cov.not_supported_pages}",
                f"- عدد الأسرار المحجوبة: {cov.secrets_redacted_count}",
                "",
            ])

        if root_cause and root_cause.fault_cards:
            lines.append("## 3. المشكلات والأخطاء التشخيصية")
            for idx, card in enumerate(root_cause.fault_cards, 1):
                lines.extend([
                    f"### {idx}. [{card.severity}] {card.issue_name}",
                    f"- **مكان المشكلة:** {card.location}",
                    f"- **الإعداد الحالي:** {card.current_setting}",
                    f"- **الحالة المتحققة:** {card.verified_value_or_state}",
                    f"- **السبب:** {card.why_problem}",
                    f"- **التأثير المتوقع:** {card.expected_impact}",
                    f"- **الحل المقترح:** {card.recommended_solution}",
                    f"- **إمكانية التنفيذ في NetGuard:** {'نعم' if card.can_netguard_execute else 'لا'} — {card.execution_capability_note}",
                    f"- **حالة التحقق بعد التنفيذ:** {card.post_execution_verification}",
                    "",
                ])

        if telemetry:
            lines.extend([
                "## 4. قياسات Wi-Fi المحلية",
                f"- الشبكة: `{telemetry.ssid}` ({telemetry.band}) | القناة: `{telemetry.channel}` | العرض: `{telemetry.channel_width_mhz} MHz`",
                f"- RSSI: `{telemetry.rssi_dbm} dBm` | TX/RX PHY: `{telemetry.tx_link_rate_mbps}/{telemetry.rx_link_rate_mbps} Mbps`",
                "",
            ])

        if speed_report:
            lines.extend([
                "## 5. اختبار سرعة الإنترنت",
                f"- الحالة: `{speed_report.status}` | الخادم: `{speed_report.server_name}`",
                f"- التنزيل: `{speed_report.download_mbps} Mbps` | الرفع: `{speed_report.upload_mbps} Mbps`",
                f"- Idle Ping: `{speed_report.idle_latency_ms} ms` | Jitter: `{speed_report.jitter_ms} ms`",
                "",
            ])

        if bufferbloat_report:
            lines.extend([
                "## 6. اختبار Bufferbloat",
                f"- التقدير الكلي: `{bufferbloat_report.overall_grade}` — {bufferbloat_report.summary}",
                "",
            ])

        if qos_compat:
            lines.extend([
                "## 7. توافق QoS بين الراوتر وNetGuard (Pass 4)",
                f"- {qos_compat.coexistence_status_ar}",
                "",
            ])

        if devices is not None:
            lines.extend([
                f"## 8. الأجهزة المتصلة ({len(devices)})",
                *[
                    f"- `{d.ip_address or '—'}` | `{d.mac_address or '—'}` | `{d.hostname or d.vendor or 'جهاز'}` | `{d.connection_status}`"
                    for d in devices[:30]
                ],
                "",
            ])

        if history:
            lines.append("## 9. سجل التعديلات والتحقق")
            for h in history[:20]:
                prev, _ = sanitize_setting_value("prev", h.previous_value)
                nv, _ = sanitize_setting_value("new", h.new_value)
                lines.append(f"- [{h.state.value}] {h.title} ({prev} -> {nv}) — {h.verification_result}")

        return "\n".join(lines)

    @staticmethod
    def build_sanitized_json(payload: Dict[str, Any]) -> str:
        """Dump structured diagnostic bundle after ensuring secret keys are redacted."""
        def _clean(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {
                    k: _clean(v) if isinstance(v, (dict, list)) else sanitize_setting_value(str(k), v)[0]
                    for k, v in obj.items()
                }
            if isinstance(obj, list):
                return [_clean(i) for i in obj]
            return obj

        return json.dumps(_clean(payload), ensure_ascii=False, indent=2, default=str)
