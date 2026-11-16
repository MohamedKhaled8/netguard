"""Internationalization (i18n) module for NetGuard AI.

Provides bilingual translations (Arabic & English) with plain-language explanations
for network metrics, diagnostics, and remediation actions.
"""

from __future__ import annotations
from typing import Dict, Any, List

STRINGS: Dict[str, Dict[str, str]] = {
    "ar": {
        # App Header & Navigation
        "app_title": "NETGUARD AI",
        "app_subtitle": "نظام مراقبة وإدارة استقرار الشبكة",
        "version": "الإصدار 2.0.0 · PySide6",
        "lang_toggle": "🌐 English",
        "nav_dashboard": "📊 لوحة التحكم",
        "nav_diagnostics": "🔍 تشخيص الأعطال",
        "nav_healing": "🛡️ الإصلاح الذاتي",
        "nav_traffic": "🚦 استهلاك البرامج",
        "nav_dns": "🌐 خوادم DNS السريعة",
        "nav_history": "📜 سجل المشاكل",
        "nav_settings": "⚙️ الإعدادات",

        # Dashboard View
        "system_healthy": "حالة الشبكة: ممتازة ومستقرة 🟢",
        "system_healthy_desc": "نظام الحماية الذكي يراقب جودة واستقرار اتصالك بالإنترنت لحظياً.",
        "system_anomaly": "تنبيه: تم رصد مشكلة في الشبكة ⚠️",
        "mode_autonomous": "حماية ذاتية نشطة",
        "mode_assisted": "وضع الإشعار اليدوي",
        "mode_observation": "وضع المراقبة فقط",
        
        # Quick Fix Actions
        "quick_fix_btn": "🚀 فحص ذكي وإصلاح سريع",
        "quick_fix_running": "جاري الفحص وإصلاح المسارات...",
        "quick_fix_success": "تم فحص الشبكة وتحديث مسارات الاتصال وتفريغ الكاش بنجاح! 🟢",
        "flush_dns_btn": "🧹 تنظيف كاش DNS",
        "flush_dns_success": "تم تفريغ كاش الـ DNS بنجاح وتسريع التصفح!",
        "recheck_gw_btn": "🔄 إعادة فحص الراوتر",
        "recheck_gw_success": "تم فحص الراوتر بنجاح والاتصال مستقر.",

        # KPI Cards
        "card_gateway_title": "اتصال الراوتر (Gateway)",
        "card_gateway_desc": "يقيس جودة اتصال جهازك بالراوتر المنزلي عبر الواي فاي أو الكابل.",
        "card_external_title": "سرعة استجابة الإنترنت (Ping)",
        "card_external_desc": "يقيس سرعة الوصول للمواقع العالمية وسيرفرات الألعاب والتصفح.",
        "card_jitter_title": "استقرار الخط (Jitter)",
        "card_jitter_desc": "يقيس مدى ثبات الاتصال (مهم جداً للمكالمات الصوتية والفيديو بدون تقطيع).",
        "card_dns_title": "سرعة فتح المواقع (DNS)",
        "card_dns_desc": "يقيس زمن استجابة خوادم العناوين لتصفح المواقع بدون تأخير.",

        # KPI Statuses
        "stat_normal": "ممتاز ومستقر",
        "stat_high_latency": "بطء في الاستجابة",
        "stat_stable": "ثابت ومثالي",
        "stat_unstable": "تذبذب ملحوظ",
        "stat_fast": "سريع جداً",
        "stat_degraded": "تصفح متثاقل",

        # Chart
        "chart_title": "مخطط البنج واستقرار الاتصال لحظة بلحظة (Ping Telemetry)",

        # Diagnostics View
        "diag_banner_title": "مركز التشخيص الذاتي المتقدم",
        "diag_banner_desc": "يقوم الذكاء الاصطناعي بتحليل مسارات الشبكة وعزل سبب أي بطء أو انقطاع.",
        "diag_run_btn": "🔍 إجراء فحص شامل الآن",
        "diag_running": "جاري الفحص الشامل للشبكة...",
        "diag_cause_label": "السبب المحتمل:",
        "diag_confidence_label": "دقة التشخيص:",
        "diag_severity_label": "مستوى الخطورة:",
        "diag_explanation_label": "التفسير بالتفصيل:",
        "diag_evidence_title": "الأدلة والبيانات الميدانية:",
        "diag_actions_title": "الإجراءات الموصى بها:",

        # Diagnostic Causes Translations
        "cause_healthy": "الشبكة تعمل بكفاءة تامة (لا توجد أعطال)",
        "cause_local_gateway_unreachable": "فقدان الاتصال بالراوتر المنزلي (تأكد من الواي فاي أو الكابل)",
        "cause_local_gateway_high_latency": "بطء أو تشويش في الاتصال بين جهازك والراوتر",
        "cause_dns_failure": "تعطل خادم DNS المعتمد (المتصفح لا يفتح أسماء المواقع)",
        "cause_dns_high_latency": "خادم DNS الحالي بطيء جداً في الرد",
        "cause_upstream_isp_loss": "انقطاع أو عطل عام لدى شركة الإنترنت (مزود الخدمة)",
        "cause_destination_specific_failure": "المشكلة في موقع محدد وليست من خط الإنترنت الخاص بك",
        "cause_wifi_degradation": "ضعف إشارة الواي فاي أو تداخل قنوات الاتصال",

        # Remediation View
        "rem_banner_title": "سجل الحماية والإصلاح التلقائي",
        "rem_banner_desc": "إجراءات تعافي آمنة ومدروسة لحل مشاكل الاتصال بدون تدخل يدوي.",
        "rem_flush_btn": "🧹 تفريغ كاش الـ DNS الآن",
        "rem_recheck_btn": "🔄 إعادة فحص الراوتر",
        "rem_col_time": "الوقت",
        "rem_col_action": "الإجراء المنفذ",
        "rem_col_risk": "مستوى الخطورة",
        "rem_col_status": "الحالة",
        "rem_col_duration": "زمن التنفيذ",
        "rem_col_verify": "التحقق",
        "rem_col_rollback": "التراجع التلقائي",

        # DNS View
        "dns_banner_title": "محرك فحص واختيار أسرع DNS",
        "dns_banner_desc": "مقارنة حية ومباشرة بين خوادم Cloudflare و Google و Quad9 لاختيار الأسرع لك.",
        "dns_bench_btn": "⚡ فحص وترتيب الخوادم الآن",
        "dns_bench_running": "جاري الفحص الدقيق للخوادم...",
        "dns_col_rank": "الترتيب",
        "dns_col_name": "اسم الخادم",
        "dns_col_ip": "عنوان IP",
        "dns_col_latency": "متوسط السرعة (البنج)",
        "dns_col_fail": "نسبة الخطأ",
        "dns_col_score": "التقييم العام",

        # Traffic View
        "traffic_banner_title": "مراقبة استهلاك البرامج للإنترنت",
        "traffic_meeting_none": "وضع الاجتماعات: متوقف (لا توجد مكالمات Zoom / Teams جارية)",
        "traffic_meeting_active": "وضع الاجتماعات: نشط 🟢 (يتم تأمين الأولوية لمكالمتك ومنع التقطيع)",
        "traffic_scan_btn": "🔄 فحص البرامج النشطة",
        "traffic_col_pid": "PID",
        "traffic_col_name": "اسم البرنامج",
        "traffic_col_cat": "التصنيف",
        "traffic_col_prio": "الأولوية",
        "traffic_col_sockets": "الاتصالات المفتوحة",

        # History View
        "hist_banner_title": "سجل الأعطال والمشاكل السابقة",
        "hist_banner_desc": "سجل دائم للأعطال ومعدل التكرار لقياس استقرار الخدمة مع مزود الإنترنت.",
        "hist_clear_btn": "🗑️ تنظيف السجل",
        "hist_col_time": "التوقيت",
        "hist_col_cause": "المشكلة المرصودة",
        "hist_col_conf": "الدقة",
        "hist_col_sev": "الخطورة",
        "hist_col_desc": "التفاصيل والنتيجة",

        # Settings View
        "set_banner_title": "إعدادات النظام وسياسات الحماية",
        "set_banner_desc": "تخصيص لغة البرنامج، وضع الحماية التلقائي، ومعدل تكرار الفحوصات.",
        "set_lang_label": "لغة واجهة البرنامج:",
        "set_mode_label": "وضع الحماية الذاتية:",
        "set_mode_opt_safe": "حماية ذاتية آمنة (إصلاح تلقائي ذكي)",
        "set_mode_opt_assisted": "وضع المساعد (طلب الإذن قبل الإصلاح)",
        "set_mode_opt_obs": "مراقبة وإشعار فقط (بدون أي تعديل)",
        "set_save_btn": "💾 حفظ الإعدادات وتطبيقها",
        "set_saved_success": "تم حفظ الإعدادات وتطبيقها بنجاح!",
    },
    "en": {
        # App Header & Navigation
        "app_title": "NETGUARD AI",
        "app_subtitle": "Autonomous Network Intelligence",
        "version": "v2.0.0 · PySide6",
        "lang_toggle": "🌐 العربية",
        "nav_dashboard": "📊 Dashboard",
        "nav_diagnostics": "🔍 Diagnostics",
        "nav_healing": "🛡️ Self-Healing",
        "nav_traffic": "🚦 App Traffic",
        "nav_dns": "🌐 DNS Engine",
        "nav_history": "📜 Incident History",
        "nav_settings": "⚙️ Settings",

        # Dashboard View
        "system_healthy": "SYSTEM STATUS: HEALTHY 🟢",
        "system_healthy_desc": "Continuous predictive monitoring and autonomous protection active.",
        "system_anomaly": "WARNING: NETWORK ANOMALY DETECTED ⚠️",
        "mode_autonomous": "AUTONOMOUS SAFE",
        "mode_assisted": "ASSISTED MODE",
        "mode_observation": "OBSERVATION ONLY",
        
        # Quick Fix Actions
        "quick_fix_btn": "🚀 Smart Scan & Quick Fix",
        "quick_fix_running": "Scanning and refreshing network paths...",
        "quick_fix_success": "Network audited, DNS cache flushed, and routes optimized! 🟢",
        "flush_dns_btn": "🧹 Flush DNS Cache",
        "flush_dns_success": "DNS cache cleared successfully for faster browsing!",
        "recheck_gw_btn": "🔄 Recheck Gateway",
        "recheck_gw_success": "Gateway link re-verified and fully stable.",

        # KPI Cards
        "card_gateway_title": "Gateway Connection",
        "card_gateway_desc": "Measures connection latency to your home router over Wi-Fi or Ethernet.",
        "card_external_title": "Internet Latency (Ping)",
        "card_external_desc": "Measures round-trip response to global internet servers and games.",
        "card_jitter_title": "Connection Stability (Jitter)",
        "card_jitter_desc": "Measures latency variation (crucial for smooth voice & video calls).",
        "card_dns_title": "Domain Resolution (DNS)",
        "card_dns_desc": "Measures speed of looking up website domains without delay.",

        # KPI Statuses
        "stat_normal": "Optimal",
        "stat_high_latency": "Elevated Latency",
        "stat_stable": "Stable & Steady",
        "stat_unstable": "Jitter Spike",
        "stat_fast": "Lightning Fast",
        "stat_degraded": "Degraded Response",

        # Chart
        "chart_title": "Real-Time Latency & Stability Chart (Ping Telemetry)",

        # Diagnostics View
        "diag_banner_title": "Advanced Network Diagnostics",
        "diag_banner_desc": "AI multi-probe correlation isolating the exact root cause of latency or outages.",
        "diag_run_btn": "🔍 Run Full Audit Now",
        "diag_running": "Running comprehensive network audit...",
        "diag_cause_label": "Probable Cause:",
        "diag_confidence_label": "Confidence:",
        "diag_severity_label": "Severity:",
        "diag_explanation_label": "Detailed Explanation:",
        "diag_evidence_title": "Supporting Telemetry Evidence:",
        "diag_actions_title": "Recommended Recovery Actions:",

        # Diagnostic Causes Translations
        "cause_healthy": "Network is healthy with optimal connectivity",
        "cause_local_gateway_unreachable": "Local router gateway is unreachable (check Wi-Fi / cable)",
        "cause_local_gateway_high_latency": "High local latency between host and router",
        "cause_dns_failure": "Configured DNS resolver failed to answer queries",
        "cause_dns_high_latency": "DNS resolver is responding slowly",
        "cause_upstream_isp_loss": "Upstream ISP packet loss or infrastructure outage",
        "cause_destination_specific_failure": "Target-specific issue (your connection is fine)",
        "cause_wifi_degradation": "Wi-Fi signal degradation or channel interference",

        # Remediation View
        "rem_banner_title": "Autonomous Self-Healing Engine",
        "rem_banner_desc": "Policy-governed recovery with pre-validation and automatic rollback.",
        "rem_flush_btn": "🧹 Flush DNS Cache Now",
        "rem_recheck_btn": "🔄 Recheck Gateway",
        "rem_col_time": "Timestamp",
        "rem_col_action": "Action Name",
        "rem_col_risk": "Risk Level",
        "rem_col_status": "Status",
        "rem_col_duration": "Exec Time",
        "rem_col_verify": "Verification",
        "rem_col_rollback": "Rollback",

        # DNS View
        "dns_banner_title": "Intelligent DNS Resolver Engine",
        "dns_banner_desc": "Continuous benchmark across Cloudflare, Google, Quad9, and OpenDNS.",
        "dns_bench_btn": "⚡ Run Resolver Benchmark",
        "dns_bench_running": "Benchmarking resolvers...",
        "dns_col_rank": "Rank",
        "dns_col_name": "Resolver Name",
        "dns_col_ip": "IP Address",
        "dns_col_latency": "Mean Latency",
        "dns_col_fail": "Failure Rate",
        "dns_col_score": "Composite Score",

        # Traffic View
        "traffic_banner_title": "Application-Aware Traffic Intelligence",
        "traffic_meeting_none": "Active Meeting Detection: None (Standard Operations)",
        "traffic_meeting_active": "Active Meeting Detected (Zoom/Teams) - High-Risk Actions Locked",
        "traffic_scan_btn": "🔄 Refresh Process List",
        "traffic_col_pid": "PID",
        "traffic_col_name": "Process Name",
        "traffic_col_cat": "Category",
        "traffic_col_prio": "Priority",
        "traffic_col_sockets": "Active Sockets",

        # History View
        "hist_banner_title": "Network Incident History",
        "hist_banner_desc": "Persistent audit log of all detected network anomalies, outages, and degraded states.",
        "hist_clear_btn": "🗑️ Clear History",
        "hist_col_time": "Timestamp",
        "hist_col_cause": "Probable Cause",
        "hist_col_conf": "Confidence",
        "hist_col_sev": "Severity",
        "hist_col_desc": "Explanation",

        # Settings View
        "set_banner_title": "System Configuration & Policies",
        "set_banner_desc": "Configure language, autonomous self-healing modes, and probe thresholds.",
        "set_lang_label": "User Interface Language:",
        "set_mode_label": "Self-Healing Mode:",
        "set_mode_opt_safe": "Autonomous Safe (Smart Auto-Remediation)",
        "set_mode_opt_assisted": "Assisted (Prompt before changing settings)",
        "set_mode_opt_obs": "Observation Only (Monitor & alert without changes)",
        "set_save_btn": "💾 Save & Apply Settings",
        "set_saved_success": "Settings saved and applied successfully!",
    }
}

_current_lang = "ar"


def set_language(lang: str) -> None:
    global _current_lang
    if lang in STRINGS:
        _current_lang = lang


def get_language() -> str:
    return _current_lang


def tr(key: str, default: str = "") -> str:
    """Retrieve localized string for the active language."""
    return STRINGS.get(_current_lang, {}).get(key, default or key)


def get_friendly_diagnosis_explanation(cause_val: str, raw_explanation: str = "") -> str:
    """Converts internal diagnostic explanations into crisp, natural Arabic."""
    cause_str = cause_val.lower() if isinstance(cause_val, str) else str(cause_val).lower()

    if "healthy" in cause_str:
        return "الشبكة مستقرة وتعمل بكفاءة تامة دون أي تذبذب أو بطء."
    elif "upstream" in cause_str or "isp" in cause_str:
        return "تذبذب مؤقت في شبكة مزود الخدمة (WE / Orange). الاتصال بالراوتر ممتاز، والمشكلة بالخط الخارجي."
    elif "gateway_unreachable" in cause_str or "unreachable" in cause_str:
        return "انقطع الاتصال بالراوتر المحلي. يرجى التحقق من تشغيل الراوتر أو اتصال الكابل."
    elif "gateway_high_latency" in cause_str or "gateway" in cause_str and "latency" in cause_str:
        return "تذبذب بين جهازك والراوتر. ينصح بالاقتراب أو استخدام شبكة 5GHz لتقليل التداخل."
    elif "unresponsive" in cause_str or "dns_failure" in cause_str:
        return "خادم DNS لا يستجيب. يقوم النظام بالتحويل التلقائي لأسرع خادم مستقر (Google / Cloudflare)."
    elif "dns" in cause_str and "latency" in cause_str:
        return "خادم DNS الحالي بطيء الاستجابة. ينصح باعتماد خادم أسرع لتسريع فتح الروابط."
    elif "wi_fi" in cause_str or "wifi" in cause_str:
        return "إشارة الواي فاي ضعيفة أو توجد عوائق لاسلكية تؤثر على ثبات البنج."
    elif "bufferbloat" in cause_str:
        return "ارتفاع البنج بسبب ضغط تحميل أو رفع ملفات على الشبكة في نفس الوقت."
    elif "background_app" in cause_str:
        return "تطبيق في الخلفية يستهلك جزءاً كبيراً من سرعة الاتصال."
    elif "destination" in cause_str:
        return "الإنترنت يعمل لديك بشكل طبيعي، والمشكلة مؤقتة في السيرفر الخارجي المستهدف."

    if raw_explanation and any(w in raw_explanation.lower() for w in ["gateway", "packet loss", "upstream", "isp"]):
        return "تذبذب في خط مزود الخدمة الخارجي (Upstream). الاتصال بالراوتر سليم، وتتم المراقبة تلقائياً."

    return raw_explanation or "يراقب النظام مسارات الشبكة ويعالج أي اختناق تلقائياً."

