# NetGuard AI Runtime Execution Log
Timestamp: 2026-11-16T18:34:30.859416
- Captured screenshot: `01_dashboard_first_load.png` (1366x749)
- Captured screenshot: `02_diagnosis_first_load.png` (1366x749)
- Captured screenshot: `03_remediation_first_load.png` (1366x749)
- Captured screenshot: `04_dns_first_load.png` (1366x749)
- Captured screenshot: `05_traffic_first_load.png` (1366x749)
- Captured screenshot: `06_history_first_load.png` (1366x749)
- Captured screenshot: `07_settings_first_load.png` (1366x749)

## Scenario A: Sidebar Operating Mode Switch
- Initial Orchestrator Mode: autonomous_safe
- Mode after clicking Sidebar 'بموافقتي': assisted
- Settings View ComboBox Text: 'تلقائي آمن (Autonomous Safe)' (Matches: False)
- Remediation View Selected Card Index: [0] (Expected: [1])

## Scenario B: Remediation View Mode Card Click
- Mode after clicking Remediation Card 'مراقبة فقط': assisted
- Did Orchestrator mode change? False (Defect confirmed: Signal not connected)

## Scenario C: Remediation Policies Toggle
- Pol1 toggle checked: False
- Any change in orchestrator or safety policies? None (Defect confirmed: No handler connected)

## Scenario D: 'افحص الآن' (Scan Now) Click
- Button text immediately after click: 'جارٍ الفحص…'
- Connected slots on quick_scan_requested: 0 (Emits into void)

## Scenario E: 'تجديد مسار الاتصال' (Quick Renew IP) Click
- Button text during renewal: 'جاري التجديد...'
- Button text after 1.2s QTimer: 'تم تجديد مسار الاتصال ✓'
- Timeline step 2 text logged: 'تم تأكيد استقرار عنوان IP الداخلي والاتصال عبر تردد 5GHz بنجاح.'

## Scenario F: 'فحص شامل ودقيق الآن' (Deep Diagnosis) Click
- Button text during audit: 'جاري الفحص الشامل...'
- Button text after audit completion: 'جاري الفحص الشامل...'

## Scenario G: History View Day Picker
- Initial Day Label: 'اليوم (الأحد 15 نوفمبر)'
- Day Label after clicking 'اليوم السابق': 'اليوم (الأحد 15 نوفمبر)' (Unchanged, dead control)

## Scenario H: Settings View Apply & Persistence Test
- Orchestrator mode after Settings apply: observation
- Allow level 3 disruptive in config: False (Unchanged: toggle_reboot ignored!)
- Gateway interval in config: 1.0 (Unchanged: combo_interval ignored!)

## Scenario I: Synthetic Network Problem Injection
- Injected Problem Diagnosis: dns_resolver_unresponsive
- Confidence: 0.95
- Recommended Actions: ['flush_dns_cache', 'switch_dns_resolver']
- Auto Remediation Permitted: True
