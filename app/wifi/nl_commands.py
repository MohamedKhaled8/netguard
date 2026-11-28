"""Section 5 Interactive Natural-Language Network & Router Command Service."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from app.wifi.root_cause import RootCauseReport


@dataclass
class CommandExecutionResponse:
    command_text: str
    matched_intent: str
    status: str  # "completed", "unsupported", "requires_approval", "needs_auth", "info"
    answer_ar: str
    evidence: List[str] = field(default_factory=list)
    triggered_action: Optional[str] = None
    suggested_followups: List[str] = field(default_factory=list)


class NaturalLanguageCommandService:
    """Interprets Arabic/English network commands and invokes verified inspection/diagnosis/control workflows."""

    DEFAULT_COMMANDS: List[str] = [
        "افحص الراوتر بالكامل",
        "ما سبب بطء الإنترنت؟",
        "هل توجد مشكلة في القناة اللاسلكية؟",
        "اختر أفضل قناة وغير الإعداد تلقائياً",
        "راجع إعدادات QoS وقلل الـ Ping أثناء Zoom",
        "ما سبب Bufferbloat؟",
        "راجع DNS وهل يوجد DNS أفضل؟",
        "من متصل بالشبكة الآن؟",
        "راجع إعدادات 5 GHz",
        "قارن قبل وبعد التحسين",
        "تراجع عن آخر تعديل",
    ]

    def generate_contextual_suggestions(self, rc_report: Optional[RootCauseReport]) -> List[str]:
        """Build dynamic command suggestions directly from live detected faults (no dead/static placeholders)."""
        suggestions: List[str] = []
        if rc_report and rc_report.fault_cards:
            for c in rc_report.fault_cards:
                cid = c.card_id
                if "unauth" in cid:
                    suggestions.append("افحص الراوتر بالكامل")
                elif cid.startswith("fault_ch_"):
                    suggestions.append("اختر أفضل قناة وغير الإعداد تلقائياً")
                    suggestions.append("هل توجد مشكلة في القناة اللاسلكية؟")
                elif "bufferbloat" in cid:
                    suggestions.append("ما سبب Bufferbloat؟")
                    suggestions.append("راجع إعدادات QoS وقلل الـ Ping أثناء Zoom")
                elif "dns" in cid:
                    suggestions.append("راجع DNS وهل يوجد DNS أفضل؟")
                elif "wrong_band" in cid:
                    suggestions.append("راجع إعدادات 5 GHz")
        for fallback in self.DEFAULT_COMMANDS:
            if fallback not in suggestions and len(suggestions) < 7:
                suggestions.append(fallback)
        return suggestions[:7]

    @staticmethod
    def classify_intent(text: str) -> str:
        low = (text or "").strip().lower()
        if any(k in low for k in ("تراجع", "undo", "rollback", "استرجع", "ارجع")):
            return "undo_last"
        if any(k in low for k in ("قبل وبعد", "قارن", "compare", "before", "after")):
            return "compare_before_after"
        if any(k in low for k in ("حدد سرعة", "تقييد", "limit", "cap", "throttle", "سرعة جهاز")):
            return "limit_device"
        if any(k in low for k in ("غير الإعداد", "اختر أفضل قناة", "غير القناة", "change channel", "best channel", "تحسين القناة")):
            return "optimize_channel"
        if any(k in low for k in ("القناة", "ازدحام", "channel", "congestion", "تداخل")):
            return "check_channel"
        if any(k in low for k in ("افحص الراوتر", "فحص الراوتر", "inspect router", "صفحات الراوتر", "كامل")):
            return "inspect_router"
        if any(k in low for k in ("bufferbloat", "تضخم", "امتلاء")):
            return "check_bufferbloat"
        if any(k in low for k in ("qos", "zoom", "ping", "مكالم", "بينج", "ألعاب")):
            return "review_qos_zoom"
        if any(k in low for k in ("dns", "دي ان اس")):
            return "review_dns"
        if any(k in low for k in ("متصل", "الأجهزة", "devices", "clients", "مين متصل", "من متصل")):
            return "list_devices"
        if any(k in low for k in ("5 ghz", "5ghz", "5 جيجا", "واي فاي 5")):
            return "review_5ghz"
        if any(k in low for k in ("بطء", "بطيء", "slow", "سبب", "مشكل", "أخطاء")):
            return "diagnose_slow_internet"
        return "diagnose_slow_internet"

    def execute_sync_summary(
        self,
        command_text: str,
        *,
        context: Dict[str, Any],
    ) -> CommandExecutionResponse:
        """Interpret and respond immediately using latest verified telemetry/model/report, triggering hooks when provided."""
        intent = self.classify_intent(command_text)
        rc: Optional[RootCauseReport] = context.get("root_cause")
        tel = context.get("telemetry")
        router_model = context.get("config_model")
        router_caps = context.get("capabilities")
        dns_rep = context.get("dns_report")
        bb_rep = context.get("bufferbloat_report")
        ch_rep = context.get("channel_report")
        devices = context.get("devices") or []
        history = context.get("history") or []
        comparison = context.get("comparison")

        if intent == "inspect_router":
            if router_model and router_model.coverage:
                cov = router_model.coverage
                return CommandExecutionResponse(
                    command_text=command_text,
                    matched_intent=intent,
                    status="completed",
                    answer_ar=cov.honesty_statement,
                    evidence=[
                        f"صفحات مفحوصة بالكامل: {cov.fully_inspected_pages}",
                        f"صفحات جزئية: {cov.partially_inspected_pages}",
                        f"غير متاحة/غير مدعومة: {cov.not_accessible_pages + cov.not_supported_pages}",
                        f"إجمالي الإعدادات المستخرجة: {cov.total_settings_extracted}",
                    ],
                    triggered_action="open_router_inspection",
                    suggested_followups=self.generate_contextual_suggestions(rc),
                )
            return CommandExecutionResponse(
                command_text=command_text,
                matched_intent=intent,
                status="needs_auth",
                answer_ar="لم تُسجّل جلسة فحص مصادق عليها للراوتر بعد. افتح تبويب 'الراوتر وتغطية الفحص' وأدخل اسم المستخدم وكلمة المرور لبدء الفحص الكامل.",
                triggered_action="discover_router",
                suggested_followups=["ما سبب بطء الإنترنت؟", "من متصل بالشبكة الآن؟"],
            )

        if intent == "diagnose_slow_internet":
            if rc and rc.fault_cards:
                top = rc.fault_cards[:3]
                bullets = [f"• [{c.severity}] {c.issue_name}: {c.why_problem}" for c in top]
                return CommandExecutionResponse(
                    command_text=command_text,
                    matched_intent=intent,
                    status="completed",
                    answer_ar=f"{rc.summary_ar}\n" + "\n".join(bullets),
                    evidence=[ev for c in top for ev in c.evidence_and_measurements[:1]],
                    suggested_followups=self.generate_contextual_suggestions(rc),
                )
            return CommandExecutionResponse(
                command_text=command_text,
                matched_intent=intent,
                status="info",
                answer_ar="لا توجد قياسات كافية بعد أو لا توجد أخطاء حرجة مرصودة. شغّل الفحص الشامل لتحليل الإشارة، القنوات، DNS، وBufferbloat.",
                triggered_action="run_full_scan",
            )

        if intent in ("check_channel", "optimize_channel"):
            if ch_rep and ch_rep.bands:
                band_key = tel.band if (tel and tel.band in ch_rep.bands) else next(iter(ch_rep.bands))
                bres = ch_rep.bands[band_key]
                cur = bres.current_channel
                sc = bres.current_channel_score
                best = bres.recommended_channels[0] if bres.recommended_channels else None
                can_write = bool(router_caps and router_caps.supports_channel_write and context.get("authenticated"))
                ans = (
                    f"النطاق {band_key}: القناة الحالية {cur or 'غير محددة'} "
                    + (f"(الازدحام: {sc.total_score:.1f} — {sc.interference_level}). " if sc else ". ")
                    + (f"أفضل قناة مقترحة: {best.channel} ({best.total_score:.1f} نقطة). " if best else "")
                )
                if intent == "optimize_channel":
                    if can_write and best and cur != best.channel:
                        return CommandExecutionResponse(
                            command_text=command_text,
                            matched_intent=intent,
                            status="requires_approval",
                            answer_ar=ans + "المحول يدعم التعديل التلقائي مع نسخة احتياطية؛ جاري تجهيز التعديل بموافقتك.",
                            triggered_action="propose_channel_change",
                            suggested_followups=["قارن قبل وبعد التحسين", "تراجع عن آخر تعديل"],
                        )
                    return CommandExecutionResponse(
                        command_text=command_text,
                        matched_intent=intent,
                        status="unsupported",
                        answer_ar=ans + "التغيير التلقائي يتطلب تسجيل دخول مصادق على محول يدعم كتابة القناة. يمكنك تغييرها يدوياً إلى القناة المقترحة في صفحة Wireless بالراوتر.",
                    )
                return CommandExecutionResponse(
                    command_text=command_text,
                    matched_intent=intent,
                    status="completed",
                    answer_ar=ans,
                    triggered_action="scan_rf",
                )
            return CommandExecutionResponse(
                command_text=command_text,
                matched_intent=intent,
                status="info",
                answer_ar="لم يتم تشغيل مسح القنوات اللاسلكية بعد. اضغط 'مسح وتحديث القنوات' في تبويب الشبكة اللاسلكية.",
                triggered_action="scan_rf",
            )

        if intent == "check_bufferbloat":
            if bb_rep:
                return CommandExecutionResponse(
                    command_text=command_text,
                    matched_intent=intent,
                    status="completed",
                    answer_ar=f"تقدير Bufferbloat الحالي: {bb_rep.overall_grade or 'غير محدد'}. {bb_rep.summary}",
                    evidence=bb_rep.notes,
                    triggered_action="run_bufferbloat",
                )
            return CommandExecutionResponse(
                command_text=command_text,
                matched_intent=intent,
                status="info",
                answer_ar="اضغط 'بدء اختبار Bufferbloat' في تبويب السرعة وBufferbloat لقياس تضخم الـ Ping تحت التحميل.",
                triggered_action="run_bufferbloat",
            )

        if intent == "review_qos_zoom":
            qos_info = context.get("qos_compat")
            if qos_info:
                return CommandExecutionResponse(
                    command_text=command_text,
                    matched_intent=intent,
                    status="completed",
                    answer_ar=f"حالة التوافق: {qos_info.coexistence_status_ar}. " + " ".join(qos_info.recommendations_ar),
                    triggered_action="review_qos",
                )
            return CommandExecutionResponse(
                command_text=command_text,
                matched_intent=intent,
                status="info",
                answer_ar="يمكنك تفعيل حماية QoS المحلية لـ Zoom في NetGuard لحماية حزم هذا الكمبيوتر، وتفعيل SQM/QoS في الراوتر لضبط بقية الأجهزة.",
                triggered_action="run_bufferbloat",
            )

        if intent == "review_dns":
            if dns_rep:
                return CommandExecutionResponse(
                    command_text=command_text,
                    matched_intent=intent,
                    status="completed",
                    answer_ar=f"نتيجة DNS: {dns_rep.summary} (الموصى به: {dns_rep.recommended_dns or 'الحالي جيد'}).",
                    triggered_action="run_dns",
                )
            return CommandExecutionResponse(
                command_text=command_text,
                matched_intent=intent,
                status="info",
                answer_ar="اضغط 'اختبار DNS' لقياس سرعة الخادم الحالي مقارنةً بـ 1.1.1.1 و 9.9.9.9 و 8.8.8.8.",
                triggered_action="run_dns",
            )

        if intent == "list_devices":
            active = [d for d in devices if d.connection_status != "stale"]
            return CommandExecutionResponse(
                command_text=command_text,
                matched_intent=intent,
                status="completed",
                answer_ar=f"تم رصد {len(devices)} جهازاً ({len(active)} نشط حالياً). راجع تبويب 'الأجهزة المتصلة والتحكم'.",
                triggered_action="refresh_devices",
            )

        if intent == "limit_device":
            can_bw = bool(router_caps and router_caps.supports_per_device_bandwidth and context.get("authenticated"))
            if not can_bw:
                return CommandExecutionResponse(
                    command_text=command_text,
                    matched_intent=intent,
                    status="unsupported",
                    answer_ar=(
                        "تحديد سرعة أجهزة أخرى عبر NetGuard غير متاح على هذا الراوتر حالياً (يتطلب تسجيل دخول مصادق لمحول يدعم Bandwidth Control بالراوتر). "
                        "سياسات NetGuard QoS في Windows تحكم هذا الكمبيوتر فقط."
                    ),
                )
            return CommandExecutionResponse(
                command_text=command_text,
                matched_intent=intent,
                status="requires_approval",
                answer_ar="الراوتر يدعم تحديد سرعة الأجهزة؛ اختر الجهاز والحد المطلوب من تبويب 'الأجهزة المتصلة والتحكم'.",
                triggered_action="open_devices_tab",
            )

        if intent == "review_5ghz":
            has_5 = bool(router_model and "5 GHz" in router_model.snapshot.radios)
            r5 = router_model.snapshot.radios["5 GHz"] if has_5 else None
            if r5:
                return CommandExecutionResponse(
                    command_text=command_text,
                    matched_intent=intent,
                    status="completed",
                    answer_ar=f"راديو 5 GHz بالراوتر: مفعّل={r5.enabled} | SSID={r5.ssid} | القناة={r5.channel} | العرض={r5.channel_width}.",
                )
            return CommandExecutionResponse(
                command_text=command_text,
                matched_intent=intent,
                status="info",
                answer_ar=(
                    f"الجهاز متصل حالياً بنطاق {tel.band if tel else 'غير محدد'}. "
                    + ("يمكن فحص وجود شبكات 5 GHz في جدول نقاط الوصول وتفحص إعدادات 5 GHz بعد تسجيل الدخول بالراوتر." if not has_5 else "")
                ),
                triggered_action="scan_rf",
            )

        if intent == "compare_before_after":
            if comparison:
                return CommandExecutionResponse(
                    command_text=command_text,
                    matched_intent=intent,
                    status="completed",
                    answer_ar=f"المقارنة الأخيرة ({comparison.before.label} -> {comparison.after.label}): {comparison.overall_verdict} — {comparison.summary}",
                )
            return CommandExecutionResponse(
                command_text=command_text,
                matched_intent=intent,
                status="info",
                answer_ar="لا توجد لقطة مقارنة قبل/بعد محفوظة بعد. احفظ لقطة 'قبل التغيير' ثم التقط لقطة 'بعد التغيير' من تبويب السجل واللقطات.",
                triggered_action="open_history_tab",
            )

        if intent == "undo_last":
            rb_candidates = [h for h in history if h.rollback_available]
            if not rb_candidates:
                return CommandExecutionResponse(
                    command_text=command_text,
                    matched_intent=intent,
                    status="info",
                    answer_ar="لا توجد تعديلات سابقة مسجلة قابلة للتراجع الآلي في السجل الحالي.",
                )
            return CommandExecutionResponse(
                command_text=command_text,
                matched_intent=intent,
                status="requires_approval",
                answer_ar=f"آخر تعديل قابل للتراجع: '{rb_candidates[0].title}'. سيتم تنفيذ التراجع واستعادة '{rb_candidates[0].previous_value}'.",
                triggered_action="undo_last_action",
            )

        return CommandExecutionResponse(
            command_text=command_text,
            matched_intent="unknown",
            status="info",
            answer_ar="اختر أحد الأوامر المقترحة أو اكتب سؤالك عن البطء أو القناة أو الراوتر أو الـ Bufferbloat.",
            suggested_followups=self.DEFAULT_COMMANDS[:6],
        )
