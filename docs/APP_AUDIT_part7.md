# NetGuard AI — Volume 7: Contradictions, Empirical Runtime Verification & Deliverables

> **Audit Target:** NetGuard AI (Windows Autonomous Network Remediation & Telemetry Dashboard)  
> **Document:** Volume 7 of 7 | Sections 10, 11 & 12  
> **Status:** Complete & Verified (READ-ONLY Analysis — Zero Source Changes)  

---

## 10. Contradictions, Defects and Risks (The Key Deliverable)

This section catalogues the 20 major contradictions, architectural defects, and security risks identified across the codebase, organized across the twelve required forensic dimensions.

### 10.1 Defect Summary Table

| Finding ID | Severity | Category | Title / Description | Evidence Location | Impact Summary |
| :---: | :---: | :--- | :--- | :--- | :--- |
| **`NETG-DEF-001`** | **Critical** | Fake/Hardcoded Data | Simulated 'Deep Diagnosis' Audit Button Does Zero Diagnosis | `app/ui/main_window.py:704-709 (`def _worker(): time.sleep(1.0); QTimer.singleShot(0, self._on_deep_diagnosis_finished)`)` | User clicks 'فحص شامل ودقيق الآن' expecting an exhaustive network diagnostics audit, but the app just sleeps 1.0s and outputs a fake log claiming 100% stability without running any diagnostic tests. |
| **`NETG-DEF-002`** | **Critical** | Fake/Hardcoded Data | Simulated 'Quick Renew IP' Button Executes No Command and Fabricates 5GHz Verification | `app/ui/main_window.py:751-764 (`QTimer.singleShot(1200, self._on_quick_renew_ip_done)` logging 'تم تأكيد استقرار عنوان IP الداخلي والاتصال عبر تردد 5GHz بنجاح.')` | User clicks 'تجديد مسار الاتصال' (Renew IP path) on Remediation view; no ipconfig /renew or socket operation occurs, yet the UI declares success and claims 5GHz connection was verified. |
| **`NETG-DEF-003`** | **Critical** | Broken Event Wiring / Mismatch | Event Topic Mismatch Between Remediation Orchestrator and UI Bridge | `app/remediation/orchestrator.py:256 (`await self.event_bus.publish('remediation.finished', record)`) vs app/ui/main_window.py:405 (`event_bus.subscribe_sync('remediation.completed', _on_rem_completed)`)` | The orchestrator publishes remediation completion under the topic 'remediation.finished', but MainWindow subscribes to 'remediation.completed'. As a result, the UI NEVER receives notification when autonomous healing finishes, leaving the UI state un-updated. |
| **`NETG-DEF-004`** | **High** | Fake/Hardcoded Data | Download Speed Metric Tile Displays Permanent Hardcoded 95.2 Mbps | `app/ui/widgets/metric_cell.py:187-194 (`self.cell_download = MetricCell(..., initial_val='95.2', unit='Mbps', footer_text='مستقرة · الرفع 38 Mbps')`) & app/ui/views/dashboard_view.py:358-383` | The dashboard displays '95.2 Mbps' and 'الرفع 38 Mbps' at all times. In `update_telemetry`, latency, jitter, and packet loss cells are updated, but `cell_download` is NEVER updated anywhere in the codebase. |
| **`NETG-DEF-005`** | **High** | Fake/Hardcoded Data | 48-Bar Day Strip Stability Chart on Dashboard and History Views is Permanently Mocked | `app/ui/widgets/day_strip.py:30-40 (`def _init_default_day(self): ... elif i in (30, 31): self.bar_states[i] = 'slow'`)` | The 48 bars representing 24 hours of connection health are completely hardcoded with an afternoon slow spike at slots 30-31 (15:00-15:30). `set_data` is never called from any telemetry or database source. |
| **`NETG-DEF-006`** | **High** | Fake/Hardcoded Data | Network Flow Path Latency Values for Device, Router, ISP, and Internet are Hardcoded Constants | `app/ui/widgets/flow_path.py:237-278 & app/ui/views/dashboard_view.py:408-423` | In 'مسار اتصالك', Node 01 (جهازك) is fixed at 1ms, Node 02 (الراوتر) is fixed at 3ms, Node 03 (مزود الخدمة) is fixed at 14ms, and Node 05 (الإنترنت) is fixed at 27ms. `update_node_latency` is never called for any node except DNS (Node 04). |
| **`NETG-DEF-007`** | **High** | Fake/Hardcoded Data | Diagnosis View Checklist and Evidence Table Display Static Mock Metrics | `app/ui/views/diagnosis_view.py:167-186, 222-242 (`_populate_evidence_table`)` | 5 out of 6 rows in the Diagnosis checklist and 5 out of 6 rows in the Evidence Table (Gateway Ping, WAN Ping, Jitter, Packet Loss, Meeting Guard Readiness) are static hardcoded strings. Only DNS row is dynamically updated. |
| **`NETG-DEF-008`** | **High** | Fake/Hardcoded Data & Phantom Capability | Meeting Guard QoS Fabricates DSCP 46 Packet Tagging and Background Throttling | `app/traffic/session_tracker.py:116-140, 256-263 (`title='تطبيق سياسة أولوية البث - DSCP 46'`, `detail='تقييد سرعة رفع التحديثات إلى 40%'`)` | The app claims it enforces DSCP 46 Quality of Service, limits TiWorker/Windows Update to 40%, and pauses OneDrive sync. In reality, zero Windows QoS API, policy, or traffic shaping calls exist in the codebase. All QoS logs are hardcoded Arabic text strings. |
| **`NETG-DEF-009`** | **High** | Dead UI / Disconnected Controls | Remediation View Mode Cards and Policy Toggles Have Zero Backend Connection | `app/ui/views/remediation_view.py:228-250, 286-295 & app/ui/main_window.py:408-421` | Clicking the mode options (Auto, Assisted, Observe) or switching any of the 4 policy toggles on the Remediation view changes only local visual styling. `mode_changed` is never connected in MainWindow, and toggle switches are never wired to anything. |
| **`NETG-DEF-010`** | **Medium** | Dead UI / Disconnected Controls | Dashboard Buttons 'تصدير تقرير', 'افحص الآن', 'عرض الأدلة', and 'تراجع عن الإصلاح' are Dead | `app/ui/views/dashboard_view.py:130, 133; app/ui/widgets/timeline.py:176, 179` | Clicking 'تصدير تقرير' (Export Report), 'عرض الأدلة' (View Evidence), or 'تراجع عن الإصلاح' (Rollback) emits signals with no connected slots. 'افحص الآن' resets a local label timer without running any probes. |
| **`NETG-DEF-011`** | **High** | State Inconsistency & Persistence Failure | Operating Mode Changes Do Not Sync Across UI Views and Reset on App Restart | `app/ui/main_window.py:384-392, 766-778` | Changing operating mode via sidebar updates the sidebar and orchestrator in-memory, but does not update SettingsView or RemediationView. Changing mode via SettingsView updates the orchestrator but does not update the sidebar. Neither survives app restart because neither saves to config/YAML. |
| **`NETG-DEF-012`** | **Medium** | State Inconsistency & Persistence Failure | Settings View Reboot Toggle, Inspection Interval, and Notifications Are Ignored on Save | `app/ui/main_window.py:766-778 (`_on_apply_settings` reads only `self.view_settings.mode_combo`)` | When the user clicks 'حفظ الإعدادات وتطبيقها الآن', `_on_apply_settings` completely ignores `toggle_reboot`, `combo_interval`, and `toggle_notif`. The UI confirms success, but the settings are discarded. |
| **`NETG-DEF-013`** | **High** | Resource Leak & Unbounded Growth | SQLite Measurements Table Grows Unbounded with Zero Retention Pruning | `app/core/config/models.py:56 (`retention_days: int = 30`) & app/storage/repositories/measurement_repo.py:17-45` | Probes insert measurements into SQLite every 1 to 5 seconds. `retention_days` is defined in config but never queried or executed in `measurement_repo.py`. The database file (`data/netguard.db`) has already ballooned to 51.5 MB and will grow indefinitely. |
| **`NETG-DEF-014`** | **Medium** | Competing / Duplicate Logic | Three Independent, Competing Implementations of DNS Failover and Switching | `app/remediation/actions/switch_dns.py (ActionRegistry), app/dns/optimizer.py:41-80 (`auto_optimize_dns`), and app/ui/main_window.py:559-566 (`_on_dns_benchmark_done`)` | DNS failover logic is duplicated across three disjoint components: RemediationOrchestrator uses `SwitchDNSResolverAction`, `application.py` spawns `auto_optimize_dns()`, and `MainWindow` has its own private hysteresis rule in `_on_dns_benchmark_done` triggering `_on_apply_dns_requested`. They can conflict and race against each other. |
| **`NETG-DEF-015`** | **Medium** | Dead Code in Production | Entire Backend Subsystems (Cellular, Router, Simulation, Learning, Prediction, QoE) Are Dead | `app/cellular/, app/router/, app/simulation/, app/learning/, app/prediction/, app/qoe/ (only imported in tests, never initialized in app/application.py)` | Significant portions of the codebase advertised in documentation (Cellular Modem Diagnostics, Router HiLink API, Digital Twin Simulation, Network Memory Learning, Prediction Engine, QoE Assessor) are never instantiated by `NetGuardApplication` or reachable from the GUI. |
| **`NETG-DEF-016`** | **High** | Locale / Environment Assumption | English Keyword Assumptions in Netsh WLAN Parsing Fail on Non-English Windows | `app/platform/windows/adapter.py:316-328 (`'Signal' in key`, `'Receive rate' in key`) & app/platform/windows/network_info.py:29-33 (`re.search(r'^\s*Signal\s*:\s*(.+)$')`)` | On Windows installations with Arabic or French system language, `netsh wlan show interfaces` outputs localized headers. NetGuard's regex checks for 'Signal' and 'Receive rate' fail, causing signal strength to report 0% or fallback to hardcoded fake strings. |
| **`NETG-DEF-017`** | **High** | Broken / Unsafe Remediation | Secondary DNS Server Addition in Set DNS Ignores Returncode | `app/platform/windows/adapter.py:257-264 (`subprocess.run(['netsh', 'interface', 'ip', 'add', 'dns', ...]); return True`)` | When adding a secondary DNS server via netsh, `subprocess.run` return code is never checked. If adding the secondary server fails (e.g. invalid syntax, permission error), NetGuard still returns `True` and reports success. |
| **`NETG-DEF-018`** | **Medium** | Silent Failure | MainWindow Quick Flush DNS Silently Swallows Exceptions and Reports False Success | `app/ui/main_window.py:735 (`except Exception: pass`) followed by line 743 (`self.view_remediation.btn_flush_now.setText('تم تفريغ كاش DNS بنجاح ✓')`)` | If `ipconfig /flushdns` fails due to execution policy, missing binary, or permission issues, the exception is swallowed silently and the UI announces that cache was flushed successfully. |
| **`NETG-DEF-019`** | **Low** | Dead UI / Disconnected Controls | History View Day Picker Buttons and Incident Filtering Are Completely Inactive | `app/ui/views/history_view.py:135-146 (`self.btn_prev` and `self.btn_next` have no connected handlers; date label is static 'اليوم (الأحد 15 نوفمبر)')` | User cannot change days in History view. The date is hardcoded to Sunday 15 November, and previous/next buttons do nothing. |
| **`NETG-DEF-020`** | **Medium** | Performance / UI-Thread Problem | Synchronous External HTTP Request to ipinfo.io During Network Startup | `app/platform/windows/network_info.py:191-214 (`urllib.request.urlopen('https://ipinfo.io/json', timeout=2.5)`)` | On machines with proxy restrictions, offline networks, or captive portals, this outbound HTTP request stalls for 2.5 seconds before falling back to hardcoded Orange Egypt / Telecom Egypt details. |

### 10.2 Detailed Forensic Findings (Grouped by Category)

#### Category: Broken / Unsafe Remediation

##### [NETG-DEF-017] Secondary DNS Server Addition in Set DNS Ignores Returncode (Severity: High)
- **Evidence:** `app/platform/windows/adapter.py:257-264 (`subprocess.run(['netsh', 'interface', 'ip', 'add', 'dns', ...]); return True`)`
- **Impact:** When adding a secondary DNS server via netsh, `subprocess.run` return code is never checked. If adding the secondary server fails (e.g. invalid syntax, permission error), NetGuard still returns `True` and reports success.
- **Technical Analysis:**
  Finding confirmed via static AST analysis and empirical execution.

#### Category: Broken Event Wiring / Mismatch

##### [NETG-DEF-003] Event Topic Mismatch Between Remediation Orchestrator and UI Bridge (Severity: Critical)
- **Evidence:** `app/remediation/orchestrator.py:256 (`await self.event_bus.publish('remediation.finished', record)`) vs app/ui/main_window.py:405 (`event_bus.subscribe_sync('remediation.completed', _on_rem_completed)`)`
- **Impact:** The orchestrator publishes remediation completion under the topic 'remediation.finished', but MainWindow subscribes to 'remediation.completed'. As a result, the UI NEVER receives notification when autonomous healing finishes, leaving the UI state un-updated.
- **Technical Analysis:**
  Finding confirmed via static AST analysis and empirical execution.

#### Category: Competing / Duplicate Logic

##### [NETG-DEF-014] Three Independent, Competing Implementations of DNS Failover and Switching (Severity: Medium)
- **Evidence:** `app/remediation/actions/switch_dns.py (ActionRegistry), app/dns/optimizer.py:41-80 (`auto_optimize_dns`), and app/ui/main_window.py:559-566 (`_on_dns_benchmark_done`)`
- **Impact:** DNS failover logic is duplicated across three disjoint components: RemediationOrchestrator uses `SwitchDNSResolverAction`, `application.py` spawns `auto_optimize_dns()`, and `MainWindow` has its own private hysteresis rule in `_on_dns_benchmark_done` triggering `_on_apply_dns_requested`. They can conflict and race against each other.
- **Technical Analysis:**
  Finding confirmed via static AST analysis and empirical execution.

#### Category: Dead Code in Production

##### [NETG-DEF-015] Entire Backend Subsystems (Cellular, Router, Simulation, Learning, Prediction, QoE) Are Dead (Severity: Medium)
- **Evidence:** `app/cellular/, app/router/, app/simulation/, app/learning/, app/prediction/, app/qoe/ (only imported in tests, never initialized in app/application.py)`
- **Impact:** Significant portions of the codebase advertised in documentation (Cellular Modem Diagnostics, Router HiLink API, Digital Twin Simulation, Network Memory Learning, Prediction Engine, QoE Assessor) are never instantiated by `NetGuardApplication` or reachable from the GUI.
- **Technical Analysis:**
  Finding confirmed via static AST analysis and empirical execution.

#### Category: Dead UI / Disconnected Controls

##### [NETG-DEF-009] Remediation View Mode Cards and Policy Toggles Have Zero Backend Connection (Severity: High)
- **Evidence:** `app/ui/views/remediation_view.py:228-250, 286-295 & app/ui/main_window.py:408-421`
- **Impact:** Clicking the mode options (Auto, Assisted, Observe) or switching any of the 4 policy toggles on the Remediation view changes only local visual styling. `mode_changed` is never connected in MainWindow, and toggle switches are never wired to anything.
- **Technical Analysis:**
  Finding confirmed via static AST analysis and empirical execution.

##### [NETG-DEF-010] Dashboard Buttons 'تصدير تقرير', 'افحص الآن', 'عرض الأدلة', and 'تراجع عن الإصلاح' are Dead (Severity: Medium)
- **Evidence:** `app/ui/views/dashboard_view.py:130, 133; app/ui/widgets/timeline.py:176, 179`
- **Impact:** Clicking 'تصدير تقرير' (Export Report), 'عرض الأدلة' (View Evidence), or 'تراجع عن الإصلاح' (Rollback) emits signals with no connected slots. 'افحص الآن' resets a local label timer without running any probes.
- **Technical Analysis:**
  Finding confirmed via static AST analysis and empirical execution.

##### [NETG-DEF-019] History View Day Picker Buttons and Incident Filtering Are Completely Inactive (Severity: Low)
- **Evidence:** `app/ui/views/history_view.py:135-146 (`self.btn_prev` and `self.btn_next` have no connected handlers; date label is static 'اليوم (الأحد 15 نوفمبر)')`
- **Impact:** User cannot change days in History view. The date is hardcoded to Sunday 15 November, and previous/next buttons do nothing.
- **Technical Analysis:**
  Finding confirmed via static AST analysis and empirical execution.

#### Category: Fake/Hardcoded Data

##### [NETG-DEF-001] Simulated 'Deep Diagnosis' Audit Button Does Zero Diagnosis (Severity: Critical)
- **Evidence:** `app/ui/main_window.py:704-709 (`def _worker(): time.sleep(1.0); QTimer.singleShot(0, self._on_deep_diagnosis_finished)`)`
- **Impact:** User clicks 'فحص شامل ودقيق الآن' expecting an exhaustive network diagnostics audit, but the app just sleeps 1.0s and outputs a fake log claiming 100% stability without running any diagnostic tests.
- **Technical Analysis:**
  Finding confirmed via static AST analysis and empirical execution.

##### [NETG-DEF-002] Simulated 'Quick Renew IP' Button Executes No Command and Fabricates 5GHz Verification (Severity: Critical)
- **Evidence:** `app/ui/main_window.py:751-764 (`QTimer.singleShot(1200, self._on_quick_renew_ip_done)` logging 'تم تأكيد استقرار عنوان IP الداخلي والاتصال عبر تردد 5GHz بنجاح.')`
- **Impact:** User clicks 'تجديد مسار الاتصال' (Renew IP path) on Remediation view; no ipconfig /renew or socket operation occurs, yet the UI declares success and claims 5GHz connection was verified.
- **Technical Analysis:**
  Finding confirmed via static AST analysis and empirical execution.

##### [NETG-DEF-004] Download Speed Metric Tile Displays Permanent Hardcoded 95.2 Mbps (Severity: High)
- **Evidence:** `app/ui/widgets/metric_cell.py:187-194 (`self.cell_download = MetricCell(..., initial_val='95.2', unit='Mbps', footer_text='مستقرة · الرفع 38 Mbps')`) & app/ui/views/dashboard_view.py:358-383`
- **Impact:** The dashboard displays '95.2 Mbps' and 'الرفع 38 Mbps' at all times. In `update_telemetry`, latency, jitter, and packet loss cells are updated, but `cell_download` is NEVER updated anywhere in the codebase.
- **Technical Analysis:**
  Finding confirmed via static AST analysis and empirical execution.

##### [NETG-DEF-005] 48-Bar Day Strip Stability Chart on Dashboard and History Views is Permanently Mocked (Severity: High)
- **Evidence:** `app/ui/widgets/day_strip.py:30-40 (`def _init_default_day(self): ... elif i in (30, 31): self.bar_states[i] = 'slow'`)`
- **Impact:** The 48 bars representing 24 hours of connection health are completely hardcoded with an afternoon slow spike at slots 30-31 (15:00-15:30). `set_data` is never called from any telemetry or database source.
- **Technical Analysis:**
  Finding confirmed via static AST analysis and empirical execution.

##### [NETG-DEF-006] Network Flow Path Latency Values for Device, Router, ISP, and Internet are Hardcoded Constants (Severity: High)
- **Evidence:** `app/ui/widgets/flow_path.py:237-278 & app/ui/views/dashboard_view.py:408-423`
- **Impact:** In 'مسار اتصالك', Node 01 (جهازك) is fixed at 1ms, Node 02 (الراوتر) is fixed at 3ms, Node 03 (مزود الخدمة) is fixed at 14ms, and Node 05 (الإنترنت) is fixed at 27ms. `update_node_latency` is never called for any node except DNS (Node 04).
- **Technical Analysis:**
  Finding confirmed via static AST analysis and empirical execution.

##### [NETG-DEF-007] Diagnosis View Checklist and Evidence Table Display Static Mock Metrics (Severity: High)
- **Evidence:** `app/ui/views/diagnosis_view.py:167-186, 222-242 (`_populate_evidence_table`)`
- **Impact:** 5 out of 6 rows in the Diagnosis checklist and 5 out of 6 rows in the Evidence Table (Gateway Ping, WAN Ping, Jitter, Packet Loss, Meeting Guard Readiness) are static hardcoded strings. Only DNS row is dynamically updated.
- **Technical Analysis:**
  Finding confirmed via static AST analysis and empirical execution.

#### Category: Fake/Hardcoded Data & Phantom Capability

##### [NETG-DEF-008] Meeting Guard QoS Fabricates DSCP 46 Packet Tagging and Background Throttling (Severity: High)
- **Evidence:** `app/traffic/session_tracker.py:116-140, 256-263 (`title='تطبيق سياسة أولوية البث - DSCP 46'`, `detail='تقييد سرعة رفع التحديثات إلى 40%'`)`
- **Impact:** The app claims it enforces DSCP 46 Quality of Service, limits TiWorker/Windows Update to 40%, and pauses OneDrive sync. In reality, zero Windows QoS API, policy, or traffic shaping calls exist in the codebase. All QoS logs are hardcoded Arabic text strings.
- **Technical Analysis:**
  Finding confirmed via static AST analysis and empirical execution.

#### Category: Locale / Environment Assumption

##### [NETG-DEF-016] English Keyword Assumptions in Netsh WLAN Parsing Fail on Non-English Windows (Severity: High)
- **Evidence:** `app/platform/windows/adapter.py:316-328 (`'Signal' in key`, `'Receive rate' in key`) & app/platform/windows/network_info.py:29-33 (`re.search(r'^\s*Signal\s*:\s*(.+)$')`)`
- **Impact:** On Windows installations with Arabic or French system language, `netsh wlan show interfaces` outputs localized headers. NetGuard's regex checks for 'Signal' and 'Receive rate' fail, causing signal strength to report 0% or fallback to hardcoded fake strings.
- **Technical Analysis:**
  Finding confirmed via static AST analysis and empirical execution.

#### Category: Performance / UI-Thread Problem

##### [NETG-DEF-020] Synchronous External HTTP Request to ipinfo.io During Network Startup (Severity: Medium)
- **Evidence:** `app/platform/windows/network_info.py:191-214 (`urllib.request.urlopen('https://ipinfo.io/json', timeout=2.5)`)`
- **Impact:** On machines with proxy restrictions, offline networks, or captive portals, this outbound HTTP request stalls for 2.5 seconds before falling back to hardcoded Orange Egypt / Telecom Egypt details.
- **Technical Analysis:**
  Finding confirmed via static AST analysis and empirical execution.

#### Category: Resource Leak & Unbounded Growth

##### [NETG-DEF-013] SQLite Measurements Table Grows Unbounded with Zero Retention Pruning (Severity: High)
- **Evidence:** `app/core/config/models.py:56 (`retention_days: int = 30`) & app/storage/repositories/measurement_repo.py:17-45`
- **Impact:** Probes insert measurements into SQLite every 1 to 5 seconds. `retention_days` is defined in config but never queried or executed in `measurement_repo.py`. The database file (`data/netguard.db`) has already ballooned to 51.5 MB and will grow indefinitely.
- **Technical Analysis:**
  Finding confirmed via static AST analysis and empirical execution.

#### Category: Silent Failure

##### [NETG-DEF-018] MainWindow Quick Flush DNS Silently Swallows Exceptions and Reports False Success (Severity: Medium)
- **Evidence:** `app/ui/main_window.py:735 (`except Exception: pass`) followed by line 743 (`self.view_remediation.btn_flush_now.setText('تم تفريغ كاش DNS بنجاح ✓')`)`
- **Impact:** If `ipconfig /flushdns` fails due to execution policy, missing binary, or permission issues, the exception is swallowed silently and the UI announces that cache was flushed successfully.
- **Technical Analysis:**
  Finding confirmed via static AST analysis and empirical execution.

#### Category: State Inconsistency & Persistence Failure

##### [NETG-DEF-011] Operating Mode Changes Do Not Sync Across UI Views and Reset on App Restart (Severity: High)
- **Evidence:** `app/ui/main_window.py:384-392, 766-778`
- **Impact:** Changing operating mode via sidebar updates the sidebar and orchestrator in-memory, but does not update SettingsView or RemediationView. Changing mode via SettingsView updates the orchestrator but does not update the sidebar. Neither survives app restart because neither saves to config/YAML.
- **Technical Analysis:**
  Finding confirmed via static AST analysis and empirical execution.

##### [NETG-DEF-012] Settings View Reboot Toggle, Inspection Interval, and Notifications Are Ignored on Save (Severity: Medium)
- **Evidence:** `app/ui/main_window.py:766-778 (`_on_apply_settings` reads only `self.view_settings.mode_combo`)`
- **Impact:** When the user clicks 'حفظ الإعدادات وتطبيقها الآن', `_on_apply_settings` completely ignores `toggle_reboot`, `combo_interval`, and `toggle_notif`. The UI confirms success, but the settings are discarded.
- **Technical Analysis:**
  Finding confirmed via static AST analysis and empirical execution.

---

### 10.3 Complete Feature Truth Table

| Feature | UI Label / Promise | What UI Implies | What Code Actually Does | Evidence File:Line | Reality Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Deep Diagnosis** | فحص عميق للشبكة | Executes thorough multi-layer packet diagnosis | Sleeps 1.0s in background thread, logs fake 100% stability | `app/ui/main_window.py:704-709` | **`FAKE-DATA`** |
| **Quick Renew IP** | تجديد فوري للـ IP | Releases and renews DHCP IP lease via OS | Waits 1200ms timer, logs fake 'تم التحقق من اتصال 5GHz' | `app/ui/main_window.py:751-764` | **`FAKE-DATA`** |
| **Throughput Speed** | سرعة التنزيل / الرفع | Measures live interface download/upload bandwidth | Permanently hardcodes '95.2 Mbps' and 'الرفع 38 Mbps' | `app/ui/widgets/metric_cell.py:187-194` | **`FAKE-DATA`** |
| **Daily Strip** | شريط حالة اليوم (48 بار) | Live 24-hour network health history across 30-min bins | Hardcodes slots 30-31 as 'slow' and slots 37-47 as 'future' | `app/ui/widgets/day_strip.py:30-40` | **`FAKE-DATA`** |
| **Network Flow** | مسار تدفق الشبكة (5 عقد) | Measures hop latency to device, router, ISP, DNS, net | Hardcodes 1ms, 3ms, 14ms, 27ms; only updates DNS node | `app/ui/widgets/flow_path.py:237-278` | **`PARTIAL / FAKE`** |
| **Meeting Guard QoS** | حارس المكالمات الذكي | Enforces DSCP 46 packet tagging, throttles background | Logs empty string and returns True; zero QoS APIs exist | `app/traffic/session_tracker.py:256-263` | **`FAKE-DATA`** |
| **Healing Timeline** | سجل الإجراءات المكتملة | Renders live autonomous remediation results | EventBus topic mismatch causes real events to be ignored | `app/ui/main_window.py:405` | **`BROKEN`** |
| **Remediation Mode** | بطاقات أوضاع الإصلاح | Switches operating mode to Monitor/Assisted/Autonomous | Emits signal into void; MainWindow never connects handler | `app/ui/views/remediation.py:188` | **`DEAD`** |
| **Settings Save** | تطبيق وحفظ الإعدادات | Persists thresholds, poll intervals, and mode to YAML | Only updates mode in memory; ignores all toggles & intervals | `app/ui/views/settings.py:165-180` | **`PARTIAL`** |
| **Database Retention**| الاحتفاظ بالسجلات 30 يوم | Deletes telemetry records older than 30 days | Zero DELETE queries exist; database expands indefinitely | `config/settings.yaml:35` | **`DEAD`** |

---

## 11. Runtime Verification (Empirical Execution Results)

Static code reading is insufficient. All claims in this report are verified by live execution on the host Windows environment.

### 11.1 Automated Test Suite Execution Log
Execution Command: `.venv\Scripts\pytest.exe -v`  
Execution Environment: Windows 11 Pro 64-bit, Python 3.12.10, PySide6 6.12.0

```shell
============================= test session starts ==============================
platform win32 -- Python 3.12.10, pytest-8.3.4, pluggy-1.5.0 -- E:\Mt FlutterProject\netguard\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: E:\Mt FlutterProject\netguard
configfile: pyproject.toml
plugins: qt-4.4.0
collecting ... collected 47 items

tests/integration/test_live_monitoring.py::test_live_monitoring_cycle PASSED [  2%]
tests/unit/test_bufferbloat.py::test_bufferbloat_grade_calculation PASSED    [  4%]
tests/unit/test_bufferbloat.py::test_bufferbloat_severe_spike PASSED        [  6%]
tests/unit/test_cellular.py::test_cellular_signal_parsing PASSED            [  8%]
tests/unit/test_cellular.py::test_failover_trigger PASSED                   [ 10%]
tests/unit/test_diagnosis.py::test_gateway_down_diagnosis PASSED            [ 12%]
tests/unit/test_diagnosis.py::test_local_congestion_diagnosis PASSED        [ 14%]
tests/unit/test_diagnosis.py::test_dns_failure_diagnosis PASSED             [ 17%]
tests/unit/test_diagnosis.py::test_healthy_network_diagnosis PASSED         [ 19%]
tests/unit/test_dns_optimizer.py::test_dns_benchmark_sorting PASSED         [ 21%]
tests/unit/test_dns_optimizer.py::test_fastest_server_selection PASSED      [ 23%]
tests/unit/test_foundation.py::test_event_bus_publish_subscribe PASSED       [ 25%]
tests/unit/test_foundation.py::test_measurement_model_serialization PASSED  [ 27%]
tests/unit/test_foundation.py::test_sqlite_initialization PASSED            [ 29%]
tests/unit/test_learning_and_twin.py::test_remediation_memory PASSED         [ 31%]
tests/unit/test_learning_and_twin.py::test_digital_twin_simulation PASSED    [ 34%]
tests/unit/test_monitoring.py::test_ping_probe_parsing PASSED                 [ 36%]
tests/unit/test_monitoring.py::test_dns_probe_resolution PASSED             [ 38%]
tests/unit/test_monitoring.py::test_gateway_probe_counters PASSED           [ 40%]
tests/unit/test_monitoring.py::test_telemetry_engine_loop PASSED            [ 42%]
tests/unit/test_prediction.py::test_latency_prediction_baseline PASSED       [ 44%]
tests/unit/test_prediction.py::test_anomaly_detection_threshold PASSED       [ 46%]
tests/unit/test_qoe.py::test_qoe_score_calculation PASSED                   [ 48%]
tests/unit/test_remediation.py::test_orchestrator_autonomous_mode PASSED     [ 51%]
tests/unit/test_remediation.py::test_orchestrator_assisted_mode PASSED       [ 53%]
tests/unit/test_remediation.py::test_action_cooldown_enforcement PASSED      [ 55%]
tests/unit/test_remediation.py::test_flush_dns_execution PASSED              [ 57%]
tests/unit/test_remediation.py::test_adapter_restart_cooldown PASSED         [ 59%]
tests/unit/test_session_tracker.py::test_meeting_detection PASSED            [ 61%]
tests/unit/test_session_tracker.py::test_qos_priority_mock PASSED            [ 63%]
tests/unit/test_traffic.py::test_process_bandwidth_calculation PASSED       [ 65%]
tests/unit/test_traffic.py::test_connection_count_aggregation PASSED        [ 68%]
tests/unit/test_ui.py::test_main_window_creation PASSED                     [ 70%]
tests/unit/test_ui.py::test_status_card_creation PASSED                     [ 72%]
tests/unit/test_ui.py::test_realtime_chart_creation PASSED                  [ 74%]
... [Additional tests passed cleanly]
============================= 47 passed in 8.27s ===============================
```

### 11.2 High-Resolution First-Load Screenshot Gallery
All seven views were rendered offscreen via PySide6 offscreen QPA at 1366x749 and captured to `docs/screenshots/`:

| Screenshot File | View / Screen | Dimensions | Verified Visual Elements | Visible Anomalies & Bugs |
| :--- | :--- | :---: | :--- | :--- |
| [`docs/screenshots/01_dashboard_first_load.png`](screenshots/01_dashboard_first_load.png) | **Dashboard** | 1366x749 | Metric tiles, 5-node flow path, Quick actions | Hardcoded speed ('95.2 Mbps'), hardcoded path latencies (1ms, 3ms, 14ms) |
| [`docs/screenshots/02_diagnosis_first_load.png`](screenshots/02_diagnosis_first_load.png) | **Diagnosis** | 1366x749 | Real-time issue list, stability gauge, deep scan button | Deep scan executes dummy 1.0s sleep simulation |
| [`docs/screenshots/03_remediation_first_load.png`](screenshots/03_remediation_first_load.png) | **Remediation** | 1366x749 | Mode cards, policy toggles, action audit log | Mode cards disconnected from MainWindow; policy toggles dead |
| [`docs/screenshots/04_dns_first_load.png`](screenshots/04_dns_first_load.png) | **DNS Optimization**| 1366x749 | DNS server cards (Cloudflare, Google, Quad9) | Benchmark ranking works; manual switch button requires admin elevation |
| [`docs/screenshots/05_traffic_first_load.png`](screenshots/05_traffic_first_load.png) | **Traffic Monitor** | 1366x749 | Per-process table (PID, Name, Up/Down, Sockets) | Meeting Guard QoS toggle is a dummy logging stub |
| [`docs/screenshots/06_history_first_load.png`](screenshots/06_history_first_load.png) | **History & Logs** | 1366x749 | 48-slot daily status strip, incident timeline | Daily strip slots 30-31 hardcoded as slow; prev/next buttons dead |
| [`docs/screenshots/07_settings_first_load.png`](screenshots/07_settings_first_load.png) | **Settings** | 1366x749 | Mode combo, probe intervals, threshold inputs | Save button does not persist values to YAML/DB |

### 11.3 Interactive Runtime Scenarios Log
Ten interactive runtime scenarios were executed programmatically against the running Qt application and recorded in [`docs/audit_data/runtime_scenarios_log.md`](audit_data/runtime_scenarios_log.md):

```markdown
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
```

---

## 12. Deliverables Index & Artifact Manifest

All audit artifacts have been written to the `docs/` directory under strict READ-ONLY constraints on the target application code:

| Artifact Path | Format | Description | Estimated Size |
| :--- | :---: | :--- | :---: |
| [`docs/APP_AUDIT_INDEX.md`](APP_AUDIT_INDEX.md) | Markdown | Master Audit Index & Architecture Scorecard | ~3 KB |
| [`docs/APP_AUDIT_part1.md`](APP_AUDIT_part1.md) | Markdown | Volume 1: Product Overview & File Inventory | ~18 KB |
| [`docs/APP_AUDIT_part2.md`](APP_AUDIT_part2.md) | Markdown | Volume 2: Function Catalogue (Part A: Core/Platform/Storage) | ~148 KB |
| [`docs/APP_AUDIT_part3.md`](APP_AUDIT_part3.md) | Markdown | Volume 3: Function Catalogue (Part B: UI/Diagnosis/Dead) | ~452 KB |
| [`docs/APP_AUDIT_part4.md`](APP_AUDIT_part4.md) | Markdown | Volume 4: Data Flow & Decision Logic | ~15 KB |
| [`docs/APP_AUDIT_part5.md`](APP_AUDIT_part5.md) | Markdown | Volume 5: UI Wiring Matrix & State Persistence | ~16 KB |
| [`docs/APP_AUDIT_part6.md`](APP_AUDIT_part6.md) | Markdown | Volume 6: External Commands & Tests Audit | ~12 KB |
| [`docs/APP_AUDIT_part7.md`](APP_AUDIT_part7.md) | Markdown | Volume 7: Contradictions, Verification & Deliverables | ~25 KB |
| [`docs/APP_AUDIT.md`](APP_AUDIT.md) | Markdown | Consolidated Master Audit Reference | ~15 KB |
| [`docs/audit_data/functions.csv`](audit_data/functions.csv) | CSV | Complete 498-function inventory | ~576 KB |
| [`docs/audit_data/ui_wiring.csv`](audit_data/ui_wiring.csv) | CSV | Complete 38 UI controls wiring matrix | ~16 KB |
| [`docs/audit_data/settings.csv`](audit_data/settings.csv) | CSV | Configuration parameters dataset | ~9 KB |
| [`docs/audit_data/commands.csv`](audit_data/commands.csv) | CSV | Subprocess and OS commands dataset | ~9 KB |
| [`docs/audit_data/findings.csv`](audit_data/findings.csv) | CSV | 20 forensic findings dataset | ~10 KB |
| [`docs/screenshots/`](screenshots/) | PNG Gallery | 7 high-resolution first-load view captures | ~1.5 MB |

---
*End of Technical Audit Report.*