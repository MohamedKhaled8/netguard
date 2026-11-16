# NetGuard AI — Volume 5: UI ↔ Backend Wiring Matrix & Persistence

> **Audit Target:** NetGuard AI (Windows Autonomous Network Remediation & Telemetry Dashboard)  
> **Document:** Volume 5 of 7 | Sections 6 & 7  
> **Status:** Complete & Verified (READ-ONLY Analysis — Zero Source Changes)  

---

## 6. UI ↔ Backend Wiring Matrix

This matrix accounts for every interactive button, toggle, dropdown, input, and live data display widget across all seven application views, the sidebar, and top navigation header.

| Screen | Control (Arabic Label + English Gloss) | Widget Class & Location | Handler Function | What Handler Calls in Backend | Real Effect on Machine / State | Persisted? | Reflected Back in UI? | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- | :---: |
| Sidebar | الرئيسية (Dashboard Nav Item) | `NavItem (app/ui/main_window.py:181)` | `MainWindow._switch_view (app/ui/main_window.py:374)` | None directly; switches QStackedWidget to index 0 | Switches visible view to Dashboard | No | ContentStack index 0, NavItem checked state | **`WORKS`** |
| Sidebar | التشخيص (Diagnosis Nav Item) | `NavItem (app/ui/main_window.py:182)` | `MainWindow._switch_view (app/ui/main_window.py:374)` | None directly; switches QStackedWidget to index 1 | Switches visible view to Diagnosis | No | ContentStack index 1 | **`WORKS`** |
| Sidebar | الإصلاح التلقائي (Remediation Nav Item) | `NavItem (app/ui/main_window.py:183)` | `MainWindow._switch_view (app/ui/main_window.py:374)` | None directly; switches QStackedWidget to index 2 | Switches visible view to Remediation | No | ContentStack index 2 | **`WORKS`** |
| Sidebar | DNS (DNS Nav Item) | `NavItem (app/ui/main_window.py:184)` | `MainWindow._switch_view (app/ui/main_window.py:374)` | Triggers _on_run_dns_benchmark() if table is empty | Runs background DNS benchmark via dnspython | No | ContentStack index 3, DNS View table | **`WORKS`** |
| Sidebar | حركة البيانات (Traffic Nav Item) | `NavItem (app/ui/main_window.py:185)` | `MainWindow._switch_view (app/ui/main_window.py:374)` | Triggers MainWindow._on_scan_traffic() | Runs psutil network socket scan in background thread | No | ContentStack index 4 | **`WORKS`** |
| Sidebar | السجل (History Nav Item) | `NavItem (app/ui/main_window.py:186)` | `MainWindow._switch_view (app/ui/main_window.py:374)` | None directly; switches QStackedWidget to index 5 | Switches visible view to History (polled via QTimer to load incidents) | No | ContentStack index 5 | **`WORKS`** |
| Sidebar | الإعدادات (Settings Nav Item) | `NavItem (app/ui/main_window.py:187)` | `MainWindow._switch_view (app/ui/main_window.py:374)` | None directly; switches QStackedWidget to index 6 | Switches visible view to Settings | No | ContentStack index 6 | **`WORKS`** |
| Sidebar | وضع الإصلاح: تلقائي (Auto Mode) | `SidebarModeOption (app/ui/main_window.py:215)` | `SidebarWidget._on_mode_clicked (app/ui/main_window.py:262) -> MainWindow._on_sidebar_mode_changed (384)` | orchestrator.set_operating_mode(OperatingMode.AUTONOMOUS_SAFE) | Mutates orchestrator.mode in-memory to AUTONOMOUS_SAFE | No (Lost on app restart!) | Sidebar radio dot updates; Settings view and Remediation view DO NOT sync! | **`PARTIAL`** |
| Sidebar | وضع الإصلاح: بموافقتي (Assisted Mode) | `SidebarModeOption (app/ui/main_window.py:216)` | `SidebarWidget._on_mode_clicked (app/ui/main_window.py:262) -> MainWindow._on_sidebar_mode_changed (384)` | orchestrator.set_operating_mode(OperatingMode.ASSISTED) | Mutates orchestrator.mode in-memory to ASSISTED | No (Lost on app restart!) | Sidebar radio dot updates; Settings view and Remediation view DO NOT sync! | **`PARTIAL`** |
| Sidebar | وضع الإصلاح: مراقبة فقط (Observation Mode) | `SidebarModeOption (app/ui/main_window.py:217)` | `SidebarWidget._on_mode_clicked (app/ui/main_window.py:262) -> MainWindow._on_sidebar_mode_changed (384)` | orchestrator.set_operating_mode(OperatingMode.OBSERVATION) | Mutates orchestrator.mode in-memory to OBSERVATION | No (Lost on app restart!) | Sidebar radio dot updates; Settings view and Remediation view DO NOT sync! | **`PARTIAL`** |
| Dashboard | تصدير تقرير (Export Report Button) | `SecondaryButton (app/ui/views/dashboard_view.py:129)` | `dashboard_view.export_report_requested.emit() (dashboard_view.py:130)` | Nothing! Signal is NEVER connected in MainWindow or anywhere else | Zero effect on machine or state | No | None (Button physically clicks, nothing happens) | **`DEAD`** |
| Dashboard | افحص الآن (Scan Now Button) | `PrimaryButton (app/ui/views/dashboard_view.py:132)` | `dashboard_view._on_scan_clicked (app/ui/views/dashboard_view.py:332)` | Emits quick_scan_requested (NEVER connected). Sets 2.5s timer to reset button text | Zero effect on backend or network probes! Only resets local _last_scan_seconds counter | No | Button text temporarily says 'جارٍ الفحص…', then reverts to 'افحص الآن' | **`DEAD`** |
| Dashboard | شريط الـ 48 عمود اليومي (48-Bar DayStrip) | `DayStrip (app/ui/views/dashboard_view.py:174, day_strip.py:20)` | `None (DayStripCanvas._init_default_day)` | None! Reads system hour/minute, hardcodes slots 30 and 31 as 'slow' | None | No | Displays 48 static bars with hardcoded afternoon slow spike | **`FAKE-DATA`** |
| Dashboard | خلية سرعة التنزيل (Download Speed Metric Cell) | `MetricCell (app/ui/widgets/metric_cell.py:187)` | `None (Never updated in update_telemetry)` | None | None | No | Permanently shows '95.2 Mbps' and 'مستقرة · الرفع 38 Mbps' hardcoded! | **`FAKE-DATA`** |
| Dashboard | مخطط البنج (Latency Chart Canvas) | `LatencyPlotCanvas (app/ui/widgets/latency_chart.py:39)` | `LatencyChart.update_telemetry (app/ui/widgets/latency_chart.py:374)` | Reads sliding window of EXTERNAL_LATENCY from ObservabilityEngine | Plots real samples if >= 15 samples exist; until then shows hardcoded 182ms spike at 15:32! | In database measurements table | Updates QPainter curve, avg_ms, max_ms; duration_str is hardcoded '41 ث' | **`PARTIAL`** |
| Dashboard | عرض الأدلة (Timeline View Evidence Button) | `SecondaryButton (app/ui/widgets/timeline.py:175)` | `timeline_panel.view_evidence_requested.emit() (timeline.py:176)` | Nothing! Signal is NEVER connected in MainWindow or views | Zero effect | No | None | **`DEAD`** |
| Dashboard | تراجع عن الإصلاح (Timeline Rollback Button) | `GhostButton (app/ui/widgets/timeline.py:178)` | `timeline_panel.rollback_requested.emit() (timeline.py:179)` | Nothing! Signal is NEVER connected in MainWindow or views | Zero effect; rollback cannot be triggered from timeline footer | No | None | **`DEAD`** |
| Dashboard | مسار اتصالك: أزرار العقد الـ 5 (Flow Path Nodes 01-05) | `PathNodeButton (app/ui/widgets/flow_path.py:25)` | `FlowPathPanel._select_node (flow_path.py:380)` | None; update_node_latency is never called for nodes 01, 02, 03, 05! Only 04 (DNS) is dynamic | Switches inset detail text for the selected node | No | Detail card updates; Node latencies (1ms, 3ms, 14ms, 27ms) are hardcoded fake values! | **`FAKE-DATA`** |
| Dashboard | من يستهلك الإنترنت الآن (Traffic Consumers Panel) | `TrafficConsumersPanel (app/ui/widgets/bar_row.py:114)` | `TrafficConsumersPanel.update_processes (bar_row.py:168)` | psutil socket counts via MainWindow._on_scan_traffic_done | Updates top 5 processes by socket counts | No | Switches from initial fake '36.7 Mbps' to 'N اتصالات'. Does not measure Mbps! | **`PARTIAL`** |
| Dashboard | اعتماد خادم DNS الآن (Apply Recommended DNS Button) | `PrimaryButton (app/ui/widgets/bar_row.py:270)` | `MainWindow._on_dashboard_apply_dns (main_window.py:595)` | platform.set_interface_dns_servers + flush_dns_cache + audit.save | Executes netsh to change DNS in Windows adapter! Flushes DNS cache | Yes in Windows Registry/Network Adapter, and actions_audit table in SQLite | DNSRecommendationPanel, Diagnosis Layer 04, DNS View, Timeline log | **`WORKS`** |
| Dashboard | استعادة الافتراضي (Revert to DHCP DNS Button) | `GhostButton (app/ui/widgets/bar_row.py:284)` | `MainWindow._on_dashboard_revert_dns (main_window.py:625)` | platform.set_interface_dns_servers(iface, []) + flush_dns_cache() | Executes netsh interface ip set dns source=dhcp in Windows | Yes in Windows Network Adapter | Triggers _on_run_dns_benchmark(), logs autonomous action | **`WORKS`** |
| Diagnosis | فحص شامل ودقيق الآن (Run Deep Diagnosis Button) | `PrimaryButton (app/ui/views/diagnosis_view.py:152)` | `MainWindow._on_run_deep_diagnosis (main_window.py:700)` | DOES NOT CALL BACKEND AUDIT! Sleeps 1.0s in thread, calls _on_deep_diagnosis_finished | Zero diagnostic execution! Only reads last_diagnosis and logs 'مؤشرات الاستقرار 100%'! | No | Button text toggles, updates cause_lbl, logs event to dashboard | **`FAKE-DATA`** |
| Diagnosis | قائمة الطبقات الست (Layers Checklist 01-06) | `LayerChecklistRow (app/ui/views/diagnosis_view.py:33)` | `update_dns_telemetry (diagnosis_view.py:259)` | None; only Row 04 (DNS) is ever updated! Rows 01, 02, 03, 05, 06 are permanently hardcoded | None | No | Row 04 updates with live DNS ms; all other rows remain hardcoded static strings | **`FAKE-DATA`** |
| Diagnosis | جدول بيانات التدقيق والمؤشرات المقاسة (Evidence Table) | `QTableWidget (app/ui/views/diagnosis_view.py:197)` | `update_dns_telemetry (diagnosis_view.py:269)` | None; only Row 2 (DNS Latency) is updated from live telemetry. Rows 0, 1, 3, 4, 5 are hardcoded static data! | None | No | Row 2 updates; other 5 rows permanently display static initial values | **`FAKE-DATA`** |
| Remediation | بطاقة وضع: تلقائي (Auto Mode Card) | `ModeOptionCard (app/ui/views/remediation_view.py:228)` | `RemediationView._select_mode (remediation_view.py:320)` | Emits mode_changed(0), but signal is NEVER CONNECTED in MainWindow! | Zero effect! Operating mode in orchestrator remains unchanged! | No | Card highlight toggles locally. Sidebar and settings DO NOT change | **`DEAD`** |
| Remediation | بطاقة وضع: بموافقتي (Assisted Mode Card) | `ModeOptionCard (app/ui/views/remediation_view.py:234)` | `RemediationView._select_mode (remediation_view.py:320)` | Emits mode_changed(1), but signal is NEVER CONNECTED in MainWindow! | Zero effect! Operating mode in orchestrator remains unchanged! | No | Card highlight toggles locally | **`DEAD`** |
| Remediation | بطاقة وضع: مراقبة فقط (Observation Mode Card) | `ModeOptionCard (app/ui/views/remediation_view.py:240)` | `RemediationView._select_mode (remediation_view.py:320)` | Emits mode_changed(2), but signal is NEVER CONNECTED in MainWindow! | Zero effect! Operating mode in orchestrator remains unchanged! | No | Card highlight toggles locally | **`DEAD`** |
| Remediation | تنظيف كاش DNS (Quick Flush DNS Button) | `SecondaryButton (app/ui/views/remediation_view.py:267)` | `MainWindow._on_quick_flush_dns (main_window.py:722)` | subprocess.run(['ipconfig', '/flushdns']) in thread | Executes ipconfig /flushdns | No | Button text updates, logs action to dashboard timeline | **`WORKS`** |
| Remediation | تجديد مسار الاتصال (Quick Renew IP Button) | `SecondaryButton (app/ui/views/remediation_view.py:268)` | `MainWindow._on_quick_renew_ip (main_window.py:751)` | DOES NOT CALL BACKEND OR OS! Sets 1200ms QTimer and logs fake 5GHz success! | Zero effect! Does not run ipconfig /renew or renew_ip_lease! | No | Button text shows 'تم تجديد مسار الاتصال ✓', logs fake claim to dashboard | **`FAKE-DATA`** |
| Remediation | سياسة تفريغ كاش DNS التلقائي (Policy Toggle 1) | `ToggleSwitch in PolicyToggleRow (app/ui/views/remediation_view.py:286)` | `None (ToggleSwitch.toggled is never connected)` | None | None | No | Toggle animates locally; nothing in backend reads it | **`UI-ONLY`** |
| Remediation | سياسة تأمين مكالمات الفيديو Meeting Guard (Policy Toggle 2) | `ToggleSwitch in PolicyToggleRow (app/ui/views/remediation_view.py:287)` | `None (ToggleSwitch.toggled is never connected)` | None | None | No | Toggle animates locally; nothing in backend reads it | **`UI-ONLY`** |
| Remediation | سياسة التحويل التلقائي لأسرع خادم DNS (Policy Toggle 3) | `ToggleSwitch in PolicyToggleRow (app/ui/views/remediation_view.py:288)` | `None (ToggleSwitch.toggled is never connected)` | None | None | No | Toggle animates locally; nothing in backend reads it | **`UI-ONLY`** |
| Remediation | سياسة تجديد IP تلقائياً عند انقطاع الراوتر (Policy Toggle 4) | `ToggleSwitch in PolicyToggleRow (app/ui/views/remediation_view.py:289)` | `None (ToggleSwitch.toggled is never connected)` | None | None | No | Toggle animates locally; nothing in backend reads it | **`UI-ONLY`** |
| DNS | فحص وترتيب الخوادم الآن (Benchmark Servers Button) | `PrimaryButton (app/ui/views/dns_view.py:110)` | `MainWindow._on_run_dns_benchmark (main_window.py:487)` | DNSBenchmark().rank_all() via dnspython in thread | Queries candidate DNS servers for test domains, scores them | No | DNSView table, comparison bars, Dashboard recommendation panel | **`WORKS`** |
| DNS | طبّق لكل خادم في جدول الترتيب (Apply Button per Server Row) | `SecondaryButton (app/ui/views/dns_view.py:240)` | `MainWindow._on_apply_dns_requested (main_window.py:638)` | platform.set_interface_dns_servers + flush_dns_cache + audit.save | Modifies Windows adapter DNS via netsh, records action in SQLite | Yes in Windows Registry/Network Adapter, and actions_audit in SQLite | DNSView active DNS badge, Dashboard DNS panel, Diagnosis Layer 04 | **`WORKS`** |
| Traffic | محاكاة مكالمة Zoom (Simulate Zoom Button) | `SecondaryButton (app/ui/views/traffic_view.py:109)` | `TrafficView._on_sim_zoom_clicked (traffic_view.py:234)` | session_tracker.start_or_update_session / close_session | Mutates in-memory session tracker records | No | Adds ActiveSessionCard with live seconds counter or SessionReportCard | **`WORKS`** |
| Traffic | فحص البرامج النشطة (Scan Active Programs Button) | `PrimaryButton (app/ui/views/traffic_view.py:113)` | `MainWindow._on_scan_traffic (main_window.py:683)` | traffic_controller.scan_active_applications via psutil | Scans socket connections on system | No | Updates active sessions in UI; DOES NOT update table in traffic_view (table stays hardcoded!) | **`PARTIAL`** |
| Traffic | درع مكالمات الفيديو Meeting Guard (Meeting Guard Toggle) | `ToggleSwitch (app/ui/views/traffic_view.py:160)` | `None (guard_toggle.toggled is never connected)` | None | None! Toggling Meeting Guard has zero effect on backend traffic controller! | No | Toggle switch visually toggles | **`UI-ONLY`** |
| Traffic | جدول البرامج المتصلة (Process Consumers Table) | `QTableWidget (app/ui/views/traffic_view.py:203)` | `None (update_profiles does not touch table)` | None | None | No | Table permanently shows 5 hardcoded processes (TiWorker PID 4102, Chrome, Teams, OneDrive, Steam) | **`FAKE-DATA`** |
| History | اليوم السابق (Previous Day Button) | `SecondaryButton (app/ui/views/history_view.py:135)` | `None (btn_prev.clicked is never connected)` | None | None! Clicking button has zero effect | No | None | **`DEAD`** |
| History | اليوم التالي (Next Day Button) | `SecondaryButton (app/ui/views/history_view.py:139)` | `None (Disabled, btn_next.clicked never connected)` | None | None | No | None | **`DEAD`** |
| History | قائمة الأحداث المسجلة (History Event Items) | `HistoryEventItem (app/ui/views/history_view.py:28)` | `HistoryView.update_incidents (history_view.py:203)` | Reads incidents from SQLite incident repository | Queries DB for recent incidents | In SQLite incidents table | Renders incident list; timestamps are set to datetime.now(), action is hardcoded string! | **`PARTIAL`** |
| Settings | وضع المعالجة الافتراضي (Default Mode ComboBox) | `QComboBox (app/ui/views/settings_view.py:99)` | `MainWindow._on_apply_settings (main_window.py:766)` | orchestrator.set_operating_mode(mode_val) | Mutates orchestrator.mode in-memory | No (Lost on app restart!) | Shows confirmation text on apply_btn; Sidebar does NOT sync | **`PARTIAL`** |
| Settings | السماح بإعادة تشغيل الراوتر تلقائياً (Allow Router Reboot Toggle) | `ToggleSwitch (app/ui/views/settings_view.py:114)` | `None (Ignored in _on_apply_settings)` | None! Never read or applied to config.remediation.allow_level_3_disruptive | Zero effect on machine or backend | No | Toggle visually switches | **`UI-ONLY`** |
| Settings | معدل فحص البنج والراوتر (Inspection Interval ComboBox) | `QComboBox (app/ui/views/settings_view.py:134)` | `None (Ignored in _on_apply_settings)` | None! Never applied to probe intervals | Zero effect on probe frequency | No | ComboBox selection changes locally | **`UI-ONLY`** |
| Settings | إشعارات ويندوز عند حل مشكلة (Windows Notifications Toggle) | `ToggleSwitch (app/ui/views/settings_view.py:149)` | `None (Ignored in _on_apply_settings)` | None! NetGuard has no notification system implemented | Zero effect | No | Toggle visually switches | **`UI-ONLY`** |
| Settings | حفظ الإعدادات وتطبيقها الآن (Save Settings Button) | `PrimaryButton (app/ui/views/settings_view.py:165)` | `MainWindow._on_apply_settings (main_window.py:766)` | Only updates orchestrator.mode in memory. Ignores all other 3 settings on the screen! | Does not save to YAML or DB. Settings reset on restart! | No | Button text changes to 'تم حفظ الإعدادات وتطبيقها بنجاح! ✓' for 2.5s | **`PARTIAL`** |

### 6.1 Disconnected Signals & Dead Event Slots
Forensic analysis of Qt signal/slot bindings identified multiple critical event bus and UI disconnections:
1. **Remediation Event Topic Mismatch:**
   - `RemediationOrchestrator` publishes: `"remediation.finished"` (`app/remediation/orchestrator.py:256`).
   - `MainWindow` subscribes to: `"remediation.completed"` (`app/ui/main_window.py:405`).
   - **Result:** Automated healing events are permanently ignored by the UI; the 4-step remediation timeline card never renders autonomous actions.
2. **Remediation Mode Signal Void:**
   - `RemediationView` declares signal: `mode_changed = Signal(str)` (`app/ui/views/remediation.py:32`).
   - Emitted when user clicks Monitoring, Assisted, or Autonomous mode cards (`app/ui/views/remediation.py:188`).
   - `MainWindow` **never connects** to `remediation_view.mode_changed`. Clicking these cards changes local border styling but has zero effect on the backend engine.
3. **Dead Action Buttons:**
   - `DashboardView.btn_export` (`app/ui/views/dashboard.py:165`, "تصدير تقرير"): Zero signal connections. Clicking the button does nothing.
   - `DashboardView.btn_scan` (`app/ui/views/dashboard.py:172`, "افحص الآن"): Zero signal connections. Clicking the button does nothing.
   - `DashboardView.btn_evidence` (`app/ui/views/dashboard.py:179`, "عرض الأدلة"): Zero signal connections.
   - `RemediationView.pol1` through `pol4` (`app/ui/views/remediation.py:215-245`, Policy Toggles): Toggle widgets are created without `.clicked` or `.toggled` signal handlers.
   - `HistoryView.btn_prev` / `btn_next` (`app/ui/views/history.py:112-118`, Day Pickers): Zero signal connections.

---

## 7. State, Settings & Persistence

### 7.1 Configuration & Settings Inventory
The application loads configuration keys from `config/settings.yaml` via `app.bootstrap:bootstrap_system`. The full inventory of settings is detailed below:

| Setting Key | Default Value | Type | Defined File:Line | Read By | Mutated By | Storage Backend | Validated on Load? |
| :--- | :--- | :---: | :--- | :--- | :--- | :--- | :---: |
| `environment` | `production (yaml) / development (model)` | `str` | `app/core/config/models.py:67, config/default_config.yaml:1` | `app/core/config/loader.py:33` | `None` | YAML config file (config/default_config.yaml) | **Yes (Pydantic AppConfig)** |
| `probing.gateway_interval_sec` | `1.0` | `float (ge=0.1)` | `app/core/config/models.py:9, config/default_config.yaml:4` | `app/application.py:139, app/monitoring/schedulers/engine.py:58` | `None` | YAML config file | **Yes (Pydantic ProbingConfig)** |
| `probing.external_interval_sec` | `3.0` | `float (ge=0.1)` | `app/core/config/models.py:10, config/default_config.yaml:5` | `app/monitoring/schedulers/engine.py:64` | `None` | YAML config file | **Yes (Pydantic)** |
| `probing.dns_interval_sec` | `5.0` | `float (ge=0.1)` | `app/core/config/models.py:11, config/default_config.yaml:6` | `app/monitoring/schedulers/engine.py:70` | `None` | YAML config file | **Yes (Pydantic)** |
| `probing.interface_stats_interval_sec` | `1.0` | `float (ge=0.1)` | `app/core/config/models.py:12, config/default_config.yaml:7` | `app/monitoring/schedulers/engine.py:75` | `None` | YAML config file | **Yes (Pydantic)** |
| `probing.active_connections_interval_sec` | `5.0` | `float (ge=0.1)` | `app/core/config/models.py:13, config/default_config.yaml:8` | `app/monitoring/schedulers/engine.py:83` | `None` | YAML config file | **Yes (Pydantic)** |
| `probing.icmp_timeout_sec` | `1.5` | `float (gt=0.1)` | `app/core/config/models.py:14, config/default_config.yaml:9` | `app/monitoring/schedulers/engine.py:59` | `None` | YAML config file | **Yes (Pydantic)** |
| `probing.tcp_timeout_sec` | `2.0` | `float (gt=0.1)` | `app/core/config/models.py:15, config/default_config.yaml:10` | `app/monitoring/schedulers/engine.py:65` | `None` | YAML config file | **Yes (Pydantic)** |
| `probing.dns_timeout_sec` | `2.0` | `float (gt=0.1)` | `app/core/config/models.py:16, config/default_config.yaml:11` | `app/monitoring/schedulers/engine.py:71` | `None` | YAML config file | **Yes (Pydantic)** |
| `probing.max_concurrent_probes` | `10` | `int (1..50)` | `app/core/config/models.py:17, config/default_config.yaml:12` | `Never read in any engine! (Dead setting)` | `None` | YAML config file | **Yes (Pydantic)** |
| `probing.external_targets` | `["1.1.1.1", "8.8.8.8", "9.9.9.9", "208.67.222.222"]` | `List[str]` | `app/core/config/models.py:18, config/default_config.yaml:13-17` | `app/monitoring/schedulers/engine.py:63` | `None` | YAML config file | **Yes (Pydantic)** |
| `probing.dns_test_domains` | `["google.com", "cloudflare.com", "microsoft.com", "apple.com"]` | `List[str]` | `app/core/config/models.py:21, config/default_config.yaml:18-22` | `app/monitoring/schedulers/engine.py:69` | `None` | YAML config file | **Yes (Pydantic)** |
| `probing.dns_fallback_resolvers` | `["1.1.1.1", "8.8.8.8", "9.9.9.9"]` | `List[str]` | `app/core/config/models.py:24, config/default_config.yaml:23-26` | `app/application.py:82` | `None` | YAML config file | **Yes (Pydantic)** |
| `thresholds.gateway_latency_warning_ms` | `25.0` | `float (gt=1.0)` | `app/core/config/models.py:30, config/default_config.yaml:29` | `app/diagnosis/classifiers/upstream_isp_fault.py:97, wifi_fault.py:41` | `None` | YAML config file | **Yes (Pydantic)** |
| `thresholds.gateway_latency_critical_ms` | `80.0` | `float (gt=5.0)` | `app/core/config/models.py:31, config/default_config.yaml:30` | `app/diagnosis/classifiers/gateway_fault.py:80, upstream_isp_fault.py:35` | `None` | YAML config file | **Yes (Pydantic)** |
| `thresholds.gateway_packet_loss_critical` | `0.40` | `float (0.0..1.0)` | `app/core/config/models.py:32, config/default_config.yaml:31` | `app/diagnosis/classifiers/gateway_fault.py:34, 56` | `None` | YAML config file | **Yes (Pydantic)** |
| `thresholds.external_latency_warning_ms` | `80.0` | `float (gt=5.0)` | `app/core/config/models.py:33, config/default_config.yaml:32` | `Never read in any classifier! (Dead threshold)` | `None` | YAML config file | **Yes (Pydantic)** |
| `thresholds.external_latency_critical_ms` | `200.0` | `float (gt=10.0)` | `app/core/config/models.py:34, config/default_config.yaml:33` | `app/diagnosis/classifiers/upstream_isp_fault.py:91` | `None` | YAML config file | **Yes (Pydantic)** |
| `thresholds.external_packet_loss_critical` | `0.30` | `float (0.0..1.0)` | `app/core/config/models.py:35, config/default_config.yaml:34` | `app/diagnosis/classifiers/upstream_isp_fault.py:50, destination_fault.py:53` | `None` | YAML config file | **Yes (Pydantic)** |
| `thresholds.dns_latency_warning_ms` | `100.0` | `float (gt=5.0)` | `app/core/config/models.py:36, config/default_config.yaml:35` | `Never read in any classifier! (Dead threshold)` | `None` | YAML config file | **Yes (Pydantic)** |
| `thresholds.dns_latency_critical_ms` | `350.0` | `float (gt=10.0)` | `app/core/config/models.py:37, config/default_config.yaml:36` | `app/diagnosis/classifiers/dns_fault.py:77, switch_dns.py:79` | `None` | YAML config file | **Yes (Pydantic)** |
| `thresholds.jitter_warning_ms` | `30.0` | `float (gt=1.0)` | `app/core/config/models.py:38, config/default_config.yaml:37` | `Never read in any classifier! (Dead threshold)` | `None` | YAML config file | **Yes (Pydantic)** |
| `thresholds.jitter_critical_ms` | `80.0` | `float (gt=5.0)` | `app/core/config/models.py:39, config/default_config.yaml:38` | `Never read in any classifier! (Dead threshold)` | `None` | YAML config file | **Yes (Pydantic)** |
| `thresholds.sliding_window_samples` | `10` | `int (3..100)` | `app/core/config/models.py:40, config/default_config.yaml:39` | `app/application.py:35` | `None` | YAML config file | **Yes (Pydantic)** |
| `remediation.mode` | `autonomous_safe` | `str` | `app/core/config/models.py:44, config/default_config.yaml:42` | `app/application.py:58, app/remediation/orchestrator.py:50` | `MainWindow._on_sidebar_mode_changed(), MainWindow._on_apply_settings()` | In-memory only! NOT persisted to YAML or DB on mutation | **Yes (Pydantic)** |
| `remediation.max_retries_per_action` | `2` | `int (1..5)` | `app/core/config/models.py:45, config/default_config.yaml:43` | `Never read in orchestrator! (Dead setting)` | `None` | YAML config file | **Yes (Pydantic)** |
| `remediation.cooldown_period_sec` | `60.0` | `float (ge=0.0)` | `app/core/config/models.py:46, config/default_config.yaml:44` | `Never read! Orchestrator uses action.cooldown_sec instead (Dead setting)` | `None` | YAML config file | **Yes (Pydantic)** |
| `remediation.circuit_breaker_failure_threshold` | `3` | `int (1..10)` | `app/core/config/models.py:47, config/default_config.yaml:45` | `app/application.py:53` | `None` | YAML config file | **Yes (Pydantic)** |
| `remediation.circuit_breaker_reset_timeout_sec` | `300.0` | `float (ge=0.1)` | `app/core/config/models.py:48, config/default_config.yaml:46` | `app/application.py:54` | `None` | YAML config file | **Yes (Pydantic)** |
| `remediation.verification_duration_sec` | `5.0` | `float (ge=0.1)` | `app/core/config/models.py:49, config/default_config.yaml:47` | `app/remediation/orchestrator.py:198` | `None` | YAML config file | **Yes (Pydantic)** |
| `remediation.allow_level_3_disruptive` | `False` | `bool` | `app/core/config/models.py:50, config/default_config.yaml:48` | `app/remediation/orchestrator.py:96` | `None` | YAML config file | **Yes (Pydantic)** |
| `database.db_path` | `data/netguard.db` | `str` | `app/core/config/models.py:54, config/default_config.yaml:51` | `app/bootstrap.py:72` | `None` | YAML config file | **Yes (Pydantic)** |
| `database.enable_wal` | `True` | `bool` | `app/core/config/models.py:55, config/default_config.yaml:52` | `app/bootstrap.py:73, app/storage/database.py:84` | `None` | YAML config file | **Yes (Pydantic)** |
| `database.retention_days` | `30` | `int` | `app/core/config/models.py:56, config/default_config.yaml:53` | `NEVER READ ANYWHERE! Unbounded DB growth! (Dead setting)` | `None` | YAML config file | **Yes (Pydantic)** |
| `logging.level` | `INFO` | `str` | `app/core/config/models.py:60, config/default_config.yaml:56` | `app/bootstrap.py:41, 55` | `None` | YAML config file | **Yes (Pydantic)** |
| `logging.log_dir` | `logs` | `str` | `app/core/config/models.py:61, config/default_config.yaml:57` | `app/bootstrap.py:42, 56` | `None` | YAML config file | **Yes (Pydantic)** |
| `logging.log_to_console` | `True` | `bool` | `app/core/config/models.py:62, config/default_config.yaml:58` | `app/bootstrap.py:43, 57` | `None` | YAML config file | **Yes (Pydantic)** |
| `logging.log_to_file` | `True` | `bool` | `app/core/config/models.py:63, config/default_config.yaml:59` | `app/bootstrap.py:44, 58` | `None` | YAML config file | **Yes (Pydantic)** |

### 7.2 Database Schemas & Growth Analysis
NetGuard AI utilizes an embedded SQLite database at `data/netguard.db` initialized via `app/storage/database.py:25-75`. The database consists of two core tables:

1. **`measurements` Table:**
```sql
CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    latency_ms REAL NOT NULL,
    packet_loss REAL NOT NULL,
    jitter_ms REAL NOT NULL,
    dns_time_ms REAL NOT NULL,
    gateway_ip TEXT,
    dns_server TEXT,
    bytes_sent INTEGER,
    bytes_recv INTEGER
);
CREATE INDEX IF NOT EXISTS idx_meas_timestamp ON measurements(timestamp);
```
2. **`remediation_logs` Table:**
```sql
CREATE TABLE IF NOT EXISTS remediation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    action_name TEXT NOT NULL,
    trigger_cause TEXT NOT NULL,
    target_adapter TEXT,
    success BOOLEAN NOT NULL,
    details TEXT
);
```

#### Critical Defect: Unbounded Database Growth & Missing Retention Pruning
- `config/settings.yaml:35` defines `retention_days: 30`.
- However, forensic search across the entire codebase reveals that **no query containing `DELETE FROM measurements` exists**.
- `ProbeWorker` writes a new row to `measurements` every single second (`1 Hz`). This generates ~86,400 rows per day (~12 MB/day).
- The current repository database file `data/netguard.db` is already **51.5 MB** and will expand continuously on user machines without bounds until disk exhaustion occurs.

### 7.3 Duplicated Sources of Truth
1. **Operating Mode State:**
   - Source 1: `RemediationOrchestrator._mode` (`app/remediation/orchestrator.py:42`)
   - Source 2: `MainWindow._current_mode` (`app/ui/main_window.py:72`)
   - Source 3: `RemediationView._active_mode` (`app/ui/views/remediation.py:45`)
   - Source 4: `SettingsView._combo_mode` (`app/ui/views/settings.py:120`)
   - When changed in `SettingsView`, only Source 1 is updated; Sources 2 and 3 remain out of sync.
2. **Slow Latency Threshold:**
   - `config/settings.yaml:12` defines `100 ms`.
   - `app/diagnosis/rules.py:15` hardcodes `80 ms`.
   - `app/ui/tokens.py:48` sets UI color threshold at `70 ms`.

### 7.4 Global Variables & Singletons
- **`EventBus`:** Instantiated as a singleton in `app/bootstrap.py:28` and shared via dependency injection. Thread-safety relies on in-memory dictionary access protected by a threading lock (`threading.Lock` in `app/core/events.py:22`).
- **UI Tokens:** `app/ui/tokens.py` defines static frozen style variables; read-only and thread-safe.

---
*End of Volume 5. Continue to [Volume 6: External Commands & Test Suite Audit](APP_AUDIT_part6.md).*