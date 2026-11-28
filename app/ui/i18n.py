"""Internationalization (i18n) module for NetGuard AI.

Provides centralized bilingual localization (Arabic RTL & English LTR)
and a reactive LanguageManager signal for live UI switching.
"""

from __future__ import annotations

import inspect
import weakref
from typing import Any, Callable, Dict, List

_CURRENT_LANG = "ar"


class _LanguageSignal:
    """Thread-safe, weak-ref-safe language change dispatcher avoiding module-level C++ QObject lifetime issues."""

    def __init__(self) -> None:
        self._slots: List[Any] = []

    def connect(self, slot: Callable[[str], Any]) -> None:
        self.disconnect(slot)
        try:
            if hasattr(slot, "__self__") and hasattr(slot, "__func__"):
                self._slots.append(weakref.WeakMethod(slot))
            else:
                self._slots.append(slot)
        except TypeError:
            self._slots.append(slot)

    def disconnect(self, slot: Callable[[str], Any] | None = None) -> None:
        if slot is None:
            self._slots.clear()
            return
        kept: List[Any] = []
        for entry in self._slots:
            cb = entry() if isinstance(entry, weakref.WeakMethod) else entry
            if cb is not None and cb != slot:
                kept.append(entry)
        self._slots = kept

    def emit(self, lang: str) -> None:
        alive: List[Any] = []
        callbacks: List[Callable[[str], Any]] = []
        for entry in list(self._slots):
            if isinstance(entry, weakref.WeakMethod):
                cb = entry()
                if cb is None:
                    continue
                alive.append(entry)
                callbacks.append(cb)
            else:
                alive.append(entry)
                callbacks.append(entry)
        self._slots = alive
        for cb in callbacks:
            try:
                sig = inspect.signature(cb)
                params = [
                    p
                    for p in sig.parameters.values()
                    if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.VAR_POSITIONAL)
                ]
                if params:
                    cb(lang)
                else:
                    cb()
            except RuntimeError:
                # Underlying C++ Qt widget already deleted
                pass


class _LanguageManager:
    def __init__(self) -> None:
        self.language_changed = _LanguageSignal()


_LANG_MGR = _LanguageManager()


def get_language() -> str:
    return _CURRENT_LANG


def set_language(lang: str) -> None:
    global _CURRENT_LANG
    norm = "en" if str(lang).lower().startswith("en") else "ar"
    if _CURRENT_LANG != norm:
        _CURRENT_LANG = norm
        _LANG_MGR.language_changed.emit(norm)


def language_manager() -> _LanguageManager:
    return _LANG_MGR


STRINGS: Dict[str, Dict[str, str]] = {
    "ar": {
        "app_title": "NetGuard AI",
        "app_subtitle": "منصة هندسة وإدارة الشبكات لنظام ويندوز",
        "lang_toggle": "English",
        # Navigation (10 canonical sections + legacy aliases)
        "nav_dashboard": "لوحة التحكم",
        "nav_meeting_guard": "حماية الاجتماعات",
        "nav_traffic": "مراقب الشبكة",
        "nav_dns": "محسّن DNS",
        "nav_wifi": "ذكاء الواي فاي",
        "nav_router": "إدارة الراوتر",
        "nav_quality": "جودة الإنترنت",
        "nav_reports": "التقارير والتشخيص",
        "nav_settings": "الإعدادات",
        "nav_about": "حول البرنامج",
        "nav.dashboard": "لوحة التحكم",
        "nav.meeting_guard": "حماية الاجتماعات",
        "nav.traffic": "مراقب الشبكة",
        "nav.dns": "محسّن DNS",
        "nav.wifi_intelligence": "ذكاء الواي فاي",
        "nav.router_management": "إدارة الراوتر",
        "nav.internet_quality": "جودة الإنترنت",
        "nav.reports": "التقارير",
        "nav.settings": "الإعدادات",
        "nav.about": "حول البرنامج",
        # Global Statuses (10 canonical states)
        "status_healthy": "سليم",
        "status_active": "نشط",
        "status_running": "قيد التشغيل",
        "status_warning": "تحذير",
        "status_failed": "فشل",
        "status_unavailable": "غير متاح",
        "status_unsupported": "غير مدعوم",
        "status_not_connected": "غير متصل",
        "status_waiting": "بانتظار القياس",
        "status_verifying": "قيد التحقق",
        "status.healthy": "سليم",
        "status.active": "نشط",
        "status.running": "قيد التشغيل",
        "status.warning": "تحذير",
        "status.failed": "فشل",
        "status.unavailable": "غير متاح",
        "status.unsupported": "غير مدعوم",
        "status.not_connected": "غير متصل",
        "status.waiting": "بانتظار القياس",
        "status.verifying": "قيد التحقق",
        # Top Bar & Modes
        "topbar_net_connected": "متصل بالشبكة",
        "topbar_net_disconnected": "غير متصل بالشبكة",
        "topbar_guard_ready": "درع الاجتماعات: جاهز",
        "topbar_guard_active": "درع الاجتماعات: نشط ومؤمن",
        "topbar_guard_off": "درع الاجتماعات: متوقف",
        "topbar_bg_idle": "الخلفية: خامل",
        "topbar_last_update": "آخر تحديث",
        "topbar_no_updates": "لم يتم التحديث بعد",
        "topbar_notifications": "التنبيهات",
        "mode_label": "وضع التشغيل",
        "mode_auto": "تلقائي آمن",
        "mode_ask": "بموافقتي",
        "mode_watch": "مراقبة فقط",
        "mode_auto_desc": "يكتشف الخلل ويعالجه تلقائياً بأمان مع التحقق والتراجع عند الحاجة.",
        "mode_ask_desc": "يفحص ويقترح التعديلات وينتظر موافقتك قبل تطبيق أي تغيير.",
        "mode_watch_desc": "يراقب ويحلل ويسجل الأدلة دون إجراء أي تعديل على النظام.",
        # Dashboard
        "dash_title": "نظرة عامة على الشبكة",
        "dash_sub": "ملخص فوري لحالة الاتصال، صحة الشبكة المحسوبة، أداء الواي فاي، الحماية، والتوصيات الفعلية",
        "dash.health_gauge": "صحة الشبكة",
        "dash.hero_initializing": "جاري تهيئة القياسات الأولية...",
        "dash.hero_desc_init": "يجمع النظام قياسات البوابة والإنترنت و DNS الفعلية دون عرض قيم تقديرية.",
        "dash.hero_title_healthy": "الشبكة مستقرة وتعمل بكفاءة",
        "dash.hero_title_warning": "تم رصد تذبذب أو بطء جزئي في الشبكة",
        "dash.hero_title_critical": "تم رصد خلل حرج يؤثر على الاتصال",
        "dash.awaiting_probes": "بانتظار اكتمال أول دورة قياس فعلية لحساب مؤشر الصحة.",
        "dash.health_good": "جميع الفحوصات الفعلية ضمن الحدود المستقرة.",
        "dash.health_degraded": "تم رصد مؤشرات تراجع تتطلب المراجعة.",
        "dash.health_critical": "يوجد تدهور حرج في المسار أو فقدان حزم مرتفع.",
        "dash.note_gw_high": "كمون البوابة مرتفع",
        "dash.note_ext_high": "كمون الإنترنت مرتفع",
        "dash.note_packet_loss": "فقدان حزم مرصود",
        "dash.note_dns_slow": "استجابة DNS بطيئة",
        "dash.note_wifi_weak": "إشارة الواي فاي ضعيفة",
        "dash.adapter_pending": "المحول: جاري القراءة...",
        "dash.guard_idle": "درع الاجتماعات: جاهز",
        "dash.guard_protecting": "حماية الاجتماع",
        "dash.no_speed_test": "السرعة: غير مُقاسة بعد",
        "dash.btn_quick_scan": "فحص سريع الآن",
        "dash.scanning": "جاري الفحص...",
        "dash.btn_preflight": "جهّز لاجتماع",
        "dash.btn_export": "تصدير تقرير",
        "dash.live_traffic": "معدل نقل البيانات المباشر (تنزيل / رفع)",
        "dash.guard_panel_title": "حماية الاجتماعات و QoS",
        "dash.guard_panel_sub": "أولوية المكالمات الحية والتحقق من Windows ActiveStore",
        "dash.guard_idle_detail": "لا توجد مكالمة فيديو نشطة حالياً. المراقبة الخلفية في وضع الاستعداد.",
        "dash.guard_active_detail": "التطبيق النشط: {app} · المرحلة: {stage}",
        "dash.qos_pending": "سياسات ActiveStore: بانتظار مكالمة نشطة",
        "dash.qos_verified_count": "السياسات المؤكدة في ActiveStore: {verified} / {total}",
        "dash.wifi_router_title": "الواي فاي والراوتر",
        "dash.wifi_router_sub": "ملخص الربط اللاسلكي وبوابة الشبكة",
        "dash.wifi_quality": "جودة الواي فاي",
        "dash.wifi_unmeasured": "لم تُجمع بيانات الواي فاي بعد — افتح ذكاء الواي فاي للفحص.",
        "dash.router_unconfigured": "الراوتر: غير مقروء بعد (انتقل إلى إدارة الراوتر).",
        "dash.devices_count": "{n} أجهزة متصلة",
        "dash.recs_title": "التوصيات الفعلية",
        "dash.recs_sub": "توصيات مستخلصة من القياسات الحالية فقط",
        "dash.recs_empty": "بانتظار جمع قياسات كافية لتقييم التوصيات.",
        "dash.recs_all_good": "لا توجد إجراءات مطلوبة حالياً — المؤشرات سليمة.",
        "dash.rec_dns": "ينصح بفحص خوادم DNS عبر محسّن DNS لتحسين سرعة الاستعلام.",
        "dash.rec_wifi": "إشارة الواي فاي منخفضة؛ افحص القنوات والتداخل في ذكاء الواي فاي.",
        "dash.rec_loss": "تم رصد فقدان حزم؛ افحص الكابلات أو تداخل الواي فاي.",
        "dash.rec_gw": "استجابة البوابة المحلية مرتفعة؛ افحص الحمل على الراوتر.",
        "dash.open_section": "فتح القسم",
        "dash.local_adapter": "المحول المحلي",
        "dash.router_node": "الراوتر",
        "dash.speed_tested": "آخر اختبار سرعة",
        "dash.speed_ago_sec": "اختبار السرعة: منذ {val} ث",
        "dash.speed_ago_min": "اختبار السرعة: منذ {val} د",
        "dash.interventions": "التدخلات",
        "dash.status_warn": "تنبيه",
        "dash.status_stable": "مستقر",
        "dash.jitter_good": "ممتاز • مثالي للمكالمات",
        "dash.loss_detected": "فقدان مرصود",
        "dash.loss_zero": "ممتاز · لا حزم ضائعة",
        "dash.live_rate_caption": "معدل التنزيل الفعلي الحالي",
        # Meeting Guard
        "mg_title": "مركز تحكم حماية الاجتماعات و QoS",
        "mg_sub": "مراقبة حالة المكالمات الحية، التحقق من سياسات Windows ActiveStore QoS، وتقييد الرفع الخلفي تلقائياً",
        "mg.app_controls": "التحكم في تطبيقات الاجتماعات وأولوية البث",
        "mg.app_controls_sub": "تحديد التطبيقات المحمية وتقسيم منافذ Teams والتحقق من تقييد الخلفية",
        "mg.master_toggle": "تفعيل الحماية الذكية للاجتماعات (Master QoS)",
        "mg.teams_split": "فصل منافذ الوسائط لـ Microsoft Teams (UDP 3478–3481) عن باقي التطبيقات",
        "mg.kill_switch": "إيقاف فوري لجميع سياسات QoS",
        "mg.etw_label": "قياس ETW لحزم الإرسال (UDP Outbound)",
        "mg.dns_freeze": "حالة تجميد تغييرات DNS أثناء المكالمة",
        "mg.sessions_active": "الجلسات النشطة حالياً",
        "mg.sessions_completed": "تقارير المكالمات المنتهية",
        "mg.remediation_title": "وضع التشغيل وأدوات المعالجة التلقائية",
        # Traffic Monitor
        "tm_title": "وحدة تحليل حركة الشبكة المباشرة",
        "tm_sub": "معدلات التنزيل والرفع الفعلية، إجمالي البيانات المنقولة، توزيع البروتوكولات، واتصالات العمليات",
        "tm.dl_card": "معدل التنزيل الفعلي",
        "tm.ul_card": "معدل الرفع الفعلي",
        "tm.total_rx_tx": "إجمالي البيانات المنقولة (RX / TX)",
        "tm.active_conns": "الاتصالات النشطة والبروتوكولات",
        "tm.dl_chart": "تاريخ سرعة التنزيل",
        "tm.ul_chart": "تاريخ سرعة الرفع",
        "tm.search_placeholder": "ابحث باسم العملية أو البروتوكول...",
        "tm.limit_banner": "ملاحظة تقنية: في ويندوز يُقاس إجمالي تدفق الشبكة ومعدلات الواجهة من عدادات NIC، وتُعرض هنا الاتصالات والعمليات الفعلية ومعدل إرسال UDP عبر ETW — ولا يُخلط مطلقاً بين قرص التخزين وحركة الشبكة.",
        # DNS Optimizer
        "dns_title": "محسن ومقارن خوادم DNS",
        "dns_sub": "فحص الخادم الحالي ومقارنة الاستجابة المباشرة دون كاش مع احترام تجميد الاجتماعات",
        # Wi-Fi Intelligence
        "wifi_title": "محطة تحليل الترددات والواي فاي",
        "wifi_sub": "قياسات المحول الحقيقية، تحليل الطيف الترددي، والتقييم الموزون للقنوات",
        # Router Management
        "router_title": "وحدة إدارة وتشخيص الراوتر",
        "router_sub": "فحص وتوحيد إعدادات الراوتر، فحص التغطية، إدارة الأجهزة، وتطبيق التغييرات بموافقة وتحقق",
        "router_tab_overview": "نظرة عامة",
        "router_tab_wifi": "الواي فاي",
        "router_tab_wan": "الإنترنت / WAN",
        "router_tab_lan": "الشبكة المحلية و DHCP",
        "router_tab_devices": "الأجهزة المتصلة",
        "router_tab_qos": "QoS وعرض النطاق",
        "router_tab_diag": "مشاكل الراوتر وكل الإعدادات",
        "router_tab_web": "واجهة الراوتر المباشرة (المتصفح)",
        # Internet Quality
        "iq_title": "مختبر جودة الإنترنت و Bufferbloat",
        "iq_sub": "فصل معدل ربط PHY عن سرعة الإنترنت الفعلية وقياس الكمون تحت الحمل",
        "iq.unmeasured": "غير مُقاس بعد",
        # Reports
        "rep_title": "التقارير ومخطط التحقيق التشخيصي",
        "rep_sub": "مخطط تدفق التحقيق المتسلسل من المسح حتى التحقق، مقارنة قبل/بعد، وتصدير التقارير المنقحة",
        # Settings
        "set_title": "مركز إعدادات النظام",
        "set_sub": "إدارة منظمة لإعدادات الشبكة، الحماية، الواي فاي، الراوتر، اللغة، والتسجيل",
        # About
        "about_title": "حول NetGuard AI",
        "about_sub": "معلومات الإصدار، بنية المنصة، وضمانات الخصوصية والتنفيذ المحلي",
    },
    "en": {
        "app_title": "NetGuard AI",
        "app_subtitle": "Windows Network Intelligence & Administration Platform",
        "lang_toggle": "العربية",
        # Navigation (10 canonical sections + dot aliases)
        "nav_dashboard": "Dashboard",
        "nav_meeting_guard": "Meeting Guard",
        "nav_traffic": "Traffic Monitor",
        "nav_dns": "DNS Optimizer",
        "nav_wifi": "Wi-Fi Intelligence",
        "nav_router": "Router Management",
        "nav_quality": "Internet Quality",
        "nav_reports": "Reports",
        "nav_settings": "Settings",
        "nav_about": "About",
        "nav.dashboard": "Dashboard",
        "nav.meeting_guard": "Meeting Guard",
        "nav.traffic": "Traffic Monitor",
        "nav.dns": "DNS Optimizer",
        "nav.wifi_intelligence": "Wi-Fi Intelligence",
        "nav.router_management": "Router Management",
        "nav.internet_quality": "Internet Quality",
        "nav.reports": "Reports",
        "nav.settings": "Settings",
        "nav.about": "About",
        # Global Statuses
        "status_healthy": "Healthy",
        "status_active": "Active",
        "status_running": "Running",
        "status_warning": "Warning",
        "status_failed": "Failed",
        "status_unavailable": "Unavailable",
        "status_unsupported": "Unsupported",
        "status_not_connected": "Not Connected",
        "status_waiting": "Not Measured",
        "status_verifying": "Verifying",
        "status.healthy": "Healthy",
        "status.active": "Active",
        "status.running": "Running",
        "status.warning": "Warning",
        "status.failed": "Failed",
        "status.unavailable": "Unavailable",
        "status.unsupported": "Unsupported",
        "status.not_connected": "Not Connected",
        "status.waiting": "Not Measured",
        "status.verifying": "Verifying",
        # Top Bar & Modes
        "topbar_net_connected": "Connected",
        "topbar_net_disconnected": "Not Connected",
        "topbar_guard_ready": "Meeting Guard: Ready",
        "topbar_guard_active": "Meeting Guard: Active",
        "topbar_guard_off": "Meeting Guard: Disabled",
        "topbar_bg_idle": "Background: Idle",
        "topbar_last_update": "Last Update",
        "topbar_no_updates": "Not synced yet",
        "topbar_notifications": "Notifications",
        "mode_label": "Operating Mode",
        "mode_auto": "Autonomous Safe",
        "mode_ask": "Approval Required",
        "mode_watch": "Observation Only",
        "mode_auto_desc": "Detects and safely resolves verified faults with readback and rollback.",
        "mode_ask_desc": "Diagnoses issues and waits for your explicit approval before any change.",
        "mode_watch_desc": "Monitors, measures, and logs evidence without modifying system settings.",
        # Dashboard
        "dash_title": "Network Overview",
        "dash_sub": "Real-time network health score, link status, traffic, Meeting Guard, router, and diagnostics",
        "dash.health_gauge": "Network Health",
        "dash.hero_initializing": "Collecting initial probes...",
        "dash.hero_desc_init": "Gathering real gateway, WAN, and DNS latency without fabricated baselines.",
        "dash.hero_title_healthy": "Network is Healthy and Stable",
        "dash.hero_title_warning": "Partial Latency or Signal Degradation",
        "dash.hero_title_critical": "Critical Connectivity Fault Detected",
        "dash.awaiting_probes": "Waiting for first real probe cycle to calculate network health.",
        "dash.health_good": "All live probes are within stable thresholds.",
        "dash.health_degraded": "Degradation indicators require attention.",
        "dash.health_critical": "Severe path degradation or elevated packet loss detected.",
        "dash.note_gw_high": "High gateway latency",
        "dash.note_ext_high": "High internet latency",
        "dash.note_packet_loss": "Packet loss detected",
        "dash.note_dns_slow": "Slow DNS resolution",
        "dash.note_wifi_weak": "Weak Wi-Fi signal",
        "dash.adapter_pending": "Adapter: Detecting...",
        "dash.guard_idle": "Meeting Guard: Ready",
        "dash.guard_protecting": "Protecting Call",
        "dash.no_speed_test": "Speed: Not measured yet",
        "dash.btn_quick_scan": "Run Health Check",
        "dash.scanning": "Scanning...",
        "dash.btn_preflight": "Meeting Pre-Flight",
        "dash.btn_export": "Export Report",
        "dash.live_traffic": "Real-Time Traffic Throughput (Download / Upload)",
        "dash.guard_panel_title": "Meeting Guard & QoS",
        "dash.guard_panel_sub": "Call prioritization and Windows ActiveStore verification",
        "dash.guard_idle_detail": "No active call detected. Background protection is standing by.",
        "dash.guard_active_detail": "Active App: {app} · Lifecycle: {stage}",
        "dash.qos_pending": "ActiveStore Policies: Standing by for active call",
        "dash.qos_verified_count": "Verified in ActiveStore: {verified} / {total}",
        "dash.wifi_router_title": "Wi-Fi & Router Summary",
        "dash.wifi_router_sub": "Wireless link telemetry and gateway summary",
        "dash.wifi_quality": "Wi-Fi Quality",
        "dash.wifi_unmeasured": "No Wi-Fi telemetry collected yet — open Wi-Fi Intelligence to scan.",
        "dash.router_unconfigured": "Router: Not inspected yet (open Router Management).",
        "dash.devices_count": "{n} connected devices",
        "dash.recs_title": "Top Recommendations",
        "dash.recs_sub": "Derived strictly from current real measurements",
        "dash.recs_empty": "Waiting for sufficient probes to evaluate recommendations.",
        "dash.recs_all_good": "No actions needed — all monitored metrics look healthy.",
        "dash.rec_dns": "Run DNS Optimizer benchmark to verify faster local resolution.",
        "dash.rec_wifi": "Wi-Fi signal is degraded; inspect channel interference in Wi-Fi Intelligence.",
        "dash.rec_loss": "Packet loss detected; check local cabling or wireless interference.",
        "dash.rec_gw": "Local gateway RTT is elevated; inspect router load.",
        "dash.open_section": "Open Section",
        "dash.local_adapter": "Local Adapter",
        "dash.router_node": "Router",
        "dash.speed_tested": "Last Speed Test",
        "dash.speed_ago_sec": "Speed test: {val}s ago",
        "dash.speed_ago_min": "Speed test: {val}m ago",
        "dash.interventions": "Interventions",
        "dash.status_warn": "Warning",
        "dash.status_stable": "Stable",
        "dash.jitter_good": "Excellent · Ideal for calls",
        "dash.loss_detected": "Loss detected",
        "dash.loss_zero": "No packet loss",
        "dash.live_rate_caption": "Live NIC download rate",
        # Meeting Guard
        "mg_title": "Meeting Guard & QoS Control Center",
        "mg_sub": "Live call telemetry, Windows ActiveStore QoS policy verification, and adaptive bulk upload control",
        "mg.app_controls": "Protected Meeting Applications & Traffic Controls",
        "mg.app_controls_sub": "Manage monitored call apps, Teams port split, and background upload limits",
        "mg.master_toggle": "Enable Meeting Guard Master Protection (QoS)",
        "mg.teams_split": "Isolate Microsoft Teams Media Ports (UDP 3478–3481)",
        "mg.kill_switch": "Instant QoS Kill Switch",
        "mg.etw_label": "ETW Outbound UDP Telemetry",
        "mg.dns_freeze": "Meeting DNS Protection Freeze",
        "mg.sessions_active": "Active Call Sessions",
        "mg.sessions_completed": "Completed Session Reports",
        "mg.remediation_title": "Operating Mode & Self-Healing Policies",
        # Traffic Monitor
        "tm_title": "Live Traffic Analysis Console",
        "tm_sub": "Real-time download/upload throughput, total transferred bytes, protocols, and process connections",
        "tm.dl_card": "Download Throughput",
        "tm.ul_card": "Upload Throughput",
        "tm.total_rx_tx": "Total Transferred (RX / TX)",
        "tm.active_conns": "Active Sockets & Protocols",
        "tm.dl_chart": "Download Rate History",
        "tm.ul_chart": "Upload Rate History",
        "tm.search_placeholder": "Filter by process name or protocol...",
        "tm.limit_banner": "Engineering Note: On Windows, interface RX/TX bytes come from NIC counters while per-process rows display real active sockets and ETW outbound UDP rates. Disk I/O is never reported as network traffic.",
        # DNS Optimizer
        "dns_title": "DNS Optimizer & Resolver Benchmark",
        "dns_sub": "Active resolver verification, uncached UDP latency comparison, and meeting-safe switching",
        # Wi-Fi Intelligence
        "wifi_title": "Wi-Fi RF Analysis Workstation",
        "wifi_sub": "Windows WLAN telemetry, spectrum occupancy, and weighted channel interference scoring",
        # Router Management
        "router_title": "Router Administration Console",
        "router_sub": "Normalized gateway inspection, Wi-Fi/WAN/LAN configuration, connected clients, and verified edits",
        "router_tab_overview": "Overview",
        "router_tab_wifi": "Wi-Fi",
        "router_tab_wan": "Internet / WAN",
        "router_tab_lan": "LAN && DHCP",
        "router_tab_devices": "Connected Devices",
        "router_tab_qos": "QoS && Bandwidth",
        "router_tab_diag": "Audit && All Settings",
        "router_tab_web": "Live Router Web Portal",
        # Internet Quality
        "iq_title": "Internet Quality & Bufferbloat Workspace",
        "iq_sub": "Separating Wi-Fi PHY rate, LAN throughput, and WAN throughput with loaded-latency analysis",
        "iq.unmeasured": "Not measured",
        # Reports
        "rep_title": "Diagnostic Investigation Flowchart & Reports",
        "rep_sub": "14-stage execution workflow, root-cause evidence, before/after comparison, and redacted export",
        # Settings
        "set_title": "Configuration Center",
        "set_sub": "Organized settings for diagnostics, Meeting Guard, QoS, DNS, router management, and logging",
        # About
        "about_title": "About NetGuard AI",
        "about_sub": "Version, architecture, platform capabilities, and local-only security guarantees",
    },
}


def tr(key: str, lang: str | None = None, **kwargs: Any) -> str:
    """Translate a key in the active (or specified) language with safe English fallback."""
    active = lang or _CURRENT_LANG
    table = STRINGS.get(active, STRINGS["ar"])
    text = table.get(key) or STRINGS["en"].get(key) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
