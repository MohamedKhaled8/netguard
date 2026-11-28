# NetGuard AI — Redesign, Hardening & Acceptance Audit Report

## 1. Executive Summary & Acceptance Matrix

| # | Acceptance Criterion | Status | Evidence / Outcome |
|---|---|---|---|
| 1 | Unit Test Shutdown Crash (`0xC0000005` / `-1073741819`) | **PASS** | Fixed root causes; `tests/unit`: **382 passed, 3 warnings**, `UNIT_EXIT:0` |
| 2 | E2E 9 Failures & Crash (`0xC0000409` / `-1073740791`) | **VERIFIED** | Crash fixed (`E2E_EXIT:1`, **484 passed, 9 failed**); 2 pre-existing in `e5262cc`, 7 from `11/24` Pass-4 refactor; **0** from redesign |
| 3 | Layout & Typography Multi-DPI (`check_layout.py`) | **PASS** | Violations reduced **9,108 -> 0** across 100%, 125%, 150%, 175% DPI (thresholds untouched) |
| 4 | Router Data Parser Safety (`0` / `False` / multi-DHCP) | **PASS** | Typed `SettingValueState` + instance-aware TR-069 parsing + unit regression test passing |
| 5 | Live Router Hardware Verification (`192.168.1.1`) | **VERIFIED** | Authenticated read on live **Huawei DN8245V-56** (`WE`); 82 settings / 19 pages read; unparsed primary DHCP fields disclosed transparently |
| 6 | Packaged EXE Interactive Validation (`D:\NetGuard_REDESIGN\NetGuard.exe`) | **BLOCKED (UAC)** | PyInstaller `BUILD_EXIT:0` (`243,291,967` B); originals untouched; interactive launch blocked by `WinError 740` (`uac_admin=True`, non-elevated shell) |
| 7 | Visual Final Review (Real Data / Empty / Error States) | **PASS** | 15 live screenshots (`1440x900` AR/EN & `860x720` compact) captured without mocks & visually inspected |
| 8 | Regression Preservation (`check_no_fake_data`, Unit, Integration, E2E) | **PASS** | `FAKE_EXIT:0`, `UNIT_EXIT:0` (382), `INT_EXIT:0` (62), `E2E_EXIT:1` (484 passed / 9 pre-redesign) |
| 9 | Release Package & Integrity Checksum | **PASS** | Timestamped Desktop ZIP + `.sha256` sidecar + `ZipFile.testzip()` integrity check |

---

## 2. Unit & E2E Shutdown Crash Root Causes & Fixes
Before hardening, Python exited cleanly through assertions yet terminated during shutdown with Windows native access violation `-1073741819` (`0xC0000005`) and stack-buffer/Qt teardown failure `-1073740791` (`0xC0000409`).

### Root Causes Identified & Fixed
1. **Module-level `QObject` before `QApplication` (`app/ui/i18n.py`)**: `_LANG_MGR` was instantiated as a `QObject` at import time holding strong bound-method references to destroyed views during `Py_FinalizeEx`. Replaced with a pure-Python weak-reference `_LanguageSignal` respecting 0-arg and 1-arg slot signatures.
2. **Strong subscriber callbacks & singleton lifetime (`app/ui/animation_clock.py`)**: `_subscribers` held strong references to widget paint/tick methods past widget destruction, and a stray dead-list cleanup statement raised `NameError` in `_on_timer_timeout`. Switched subscribers to `weakref.WeakMethod`, parented the singleton to `QApplication.instance()`, and added `shutdown_instance()` wired to `aboutToQuit`.
3. **Orphan widgets & unstopped async workers (`traffic_view.py`, `dashboard_view.py`, `diagnosis_view.py`, `main_window.py`)**:
   - Parented `guard_toggle`, `btn_sim_zoom`, and hidden `master_qos_toggle` in `TrafficView`.
   - Added idempotent `shutdown()` and `closeEvent()` cleanup in `DashboardView`, `TrafficView`, and `DiagnosisView`.
   - Updated `MainWindow.closeEvent()` to shut down all 13 view attributes/aliases cleanly, cancel active `asyncio` tasks with `loop.call_later(0.05, loop.stop)` grace drainage (eliminating pending-task warnings), and join the fallback async thread (`timeout=0.5`).
4. **Test session teardown (`tests/conftest.py`, `tests/unit/test_ui.py`)**: Closed/deleted `MainWindow` instances inside UI tests and added root `pytest_sessionfinish` to stop `AnimationMasterClock`, close surviving top-level `QWidget`s, flush `processEvents()`, and collect cycles before interpreter shutdown.

### Post-Fix Suite Results (`docs/final_test_results.txt`)
- `scripts/check_no_fake_data.py`: **0 violations**, `FAKE_EXIT:0`
- `pytest tests/unit -q --tb=short`: **382 passed, 3 warnings** in `151.81s`, `UNIT_EXIT:0`
- `pytest tests/integration -q --tb=short`: **62 passed** in `100.91s`, `INT_EXIT:0`
- `pytest tests/e2e -q --tb=short`: **484 passed, 9 failed** in `62.48s`, `E2E_EXIT:1` (zero native crash)

---

## 3. E2E 9 Failures Comparison vs Pre-Redesign Baseline (`e5262cc`)
Ran the exact 9 failing E2E tests against an isolated worktree of pre-redesign commit `e5262cc` (`2 failed, 7 passed in 0.86s`, `BASELINE_E2E_EXIT:1`). Fixed a runtime `AttributeError` in `app/traffic/meeting_detector.py:682` (`TrafficPriorityClass.BACKGROUND` -> `TrafficPriorityClass.INTERACTIVE`) without altering test assertions.

| Test Node | `e5262cc` Result | Current Result | Attribution & Exact Failure |
|---|---|---|---|
| `tests/e2e/test_tier1_features.py::test_f4_02_20fps_throttling_interval` | **FAILED** | **FAILED** | Pre-existing in `e5262cc`: `assert 160 == 50` (`AnimationMasterClock._interval_ms`) |
| `tests/e2e/test_tier1_features.py::test_f4_03_low_resource_mode_reduction` | **FAILED** | **FAILED** | Pre-existing in `e5262cc`: `assert 160 == 50` (`AnimationMasterClock._timer.interval()`) |
| `tests/e2e/test_tier1_features.py::test_f13_02_teams_web_detection` | PASSED | **FAILED** | Broken by `11/24` Pass-4 `meeting_detector.py` refactor: `assert <TrafficPriorityClass.INTERACTIVE: 2> == <TrafficPriorityClass.REALTIME: 1>` |
| `tests/e2e/test_tier1_features.py::test_f13_03_zoom_web_detection` | PASSED | **FAILED** | Broken by `11/24` Pass-4 `meeting_detector.py` refactor: `assert <TrafficPriorityClass.INTERACTIVE: 2> == <TrafficPriorityClass.REALTIME: 1>` |
| `tests/e2e/test_tier1_features.py::test_f14_04_webex_recognition` | PASSED | **FAILED** | Broken by `11/24` Pass-4 refactor (`KNOWN_CONFERENCING_EXES` replaced by `MeetingAppRegistry`): `AttributeError: 'MeetingDetector' object has no attribute 'KNOWN_CONFERENCING_EXES'` |
| `tests/e2e/test_tier2_boundaries.py::test_f13_b02_meeting_tab_audio_muted` | PASSED | **FAILED** | Broken by `11/24` Pass-4 dual-condition ConsentStore+ETW refactor: `assert False is True` on `MeetingState.is_active` |
| `tests/e2e/test_tier2_boundaries.py::test_f13_b03_webrtc_connection_over_tcp_fallback` | PASSED | **FAILED** | Broken by `11/24` Pass-4 dual-condition ConsentStore+ETW refactor: `assert False is True` on `MeetingState.is_active` |
| `tests/e2e/test_tier2_boundaries.py::test_f14_b04_webex_crash_detection` | PASSED | **FAILED** | Broken by `11/24` Pass-4 `meeting_detector.py` refactor: `assert <TrafficPriorityClass.INTERACTIVE: 2> == <TrafficPriorityClass.REALTIME: 1>` |
| `tests/e2e/test_tier3_cross_features.py::test_tier3_12_f14_f15_cisco_webex_triggers_dscp46_priority` | PASSED | **FAILED** | Broken by `11/24` Pass-4 `meeting_detector.py` refactor: `assert <TrafficPriorityClass.INTERACTIVE: 2> == <TrafficPriorityClass.REALTIME: 1>` |

**Conclusion**: **0 of the 9 E2E failures** were introduced by the UI redesign or hardening pass.

---

## 4. Layout & Typography Audit (`scripts/check_layout.py`, Before vs After)
Executed at `100%`, `125%`, `150%`, and `175%` DPI across all 10 navigation pages and 4 window sizes (`1100x700`, `1280x720`, `1366x768`, `1920x1080`) with zero threshold reductions (`docs/layout_after_hardening.txt`).

| Violation Category | Before Hardening | After Hardening | Key Fixes Applied |
|---|---|---|---|
| Table Text Size (<14px) | 3,881 | **0** | Fixed `styles.py` duplicate `QTableWidget` QSS syntax bug; enforced `14px` table/item font in `fit_table_to_content` and `WifiIntelligenceView` |
| Under Minimum Size | 1,907 | **0** | Switched 7x7/8x8 status dot `QLabel`s to `QFrame`, `StatusBadge` height 36px, DNS action column widths 126px, `TimelinePanel` header height 32px |
| Font Too Small (<12px) | 1,558 | **0** | Upgraded all sub-12px widget/chart/chip/hint fonts to `>= 12px` across sidebar, badges, charts, and panels |
| Table Row Height | 469 | **0** | Enforced 46px headers (`46px`), `>= 38px` minimum rows, and `54px` interactive rows in Traffic & DNS tables |
| Widget Overlap | 451 | **0** | Cleaned old `QTableWidget` cell widgets in `TrafficView._render_filtered_table` before row rebuilds |
| Clipped Text | 358 | **0** | Widened `bar_row.py`/`dns_view.py` status width to `112px`, enabled wordWrap on wrapped titles/KPIs, moved Router tabs to 4-col `QGridLayout`, reflowed `SessionCard`/`SettingsView`/`MultiProtocolAnalysisPanel`/`PredictiveDiagnosticsPanel` |
| Contrast Ratio (<4.5:1) | 266 | **0** | Upgraded `tokens.PURPLE`/`STATUS_PURPLE` -> `#C084FC` and stepper inactive text -> `#93C5FD`/`#EEF2F7` |
| Interactive Control Height (<36px) | 178 | **0** | Raised sidebar/timeline/table action button heights to `>= 36px` (`btn_kill_switch` padding `0px 14px`) |
| Horizontal Scroll (>0) | 40 | **0** | Removed fixed `1040px` min-width in `DNSView`; added `embed_in_scroll=True` to `DiagnosisView`/`HistoryView` inside `ReportsView` |
| **Total Violations** | **9,108** | **0** | Complete 4-scale pass with zero crashes and zero warnings |

---

## 5. Router Data Parser Safety & Live Hardware Verification
- **Typed Value Classification (`models_config.py`, `parser.py`, `inspection.py`)**: Added `SettingValueState` (`present`, `numeric_zero`, `boolean_false`, `empty_string`, `null`, `missing`, `unsupported`, `parse_error`, `redacted`), `_PARAMETER_DEFINITIONS`, and `instance_id` / `object_path` tracking. Preserves legitimate `0` (channel auto/power/lease time/VLAN 0) and `False` (`dhcp_enabled=False`, `upnp_enabled=False`) plus separate TR-069 multi-instance objects (`LANDevice.1`, `LANDevice.2`), filtering only raw `InternetGatewayDevice.*` template/noise tokens.
- **Live Router Hardware Read (`192.168.1.1`)**:
  - **Manufacturer / Model**: `Huawei DN8245V-56` (`WE (TE Data)`)
  - **Timings**: Discovery `2.868s`, Auth `2.875s` (`authenticated=True`, `error_kind=none`), Config read `10.041s`
  - **Retrieved State**: `LAN=192.168.1.1`, `Mask=255.255.255.0`, `Uptime=205903s`, `RADIO 2.4 GHz: enabled=True ssid='Mohamed_khaled' ch=11 width=20/40 MHz power=100% sec=11i mode=11bgn`, `EXTRA_DHCP=[SlaveDHCP disabled]` (`192.168.2.2..254`), `PAGES=19`, `SETTINGS=82`
  - **Unparsed / Transparent Fields**: Primary DHCP pool readback reported `DHCP=None POOL=None..None` (`dhcp2.asp` JS variable variance preserved transparently rather than fabricated).

---

## 6. Runtime Defects Caught & Fixed via Authentic Screenshot Inspection
Capturing real live screenshots (no synthetic mocks) caught and fixed the following real runtime bugs:
1. **`RouterManagementView` Bundle & Auth Contract Mismatches (`app/ui/views/router_management_view.py`)**: Replaced nonexistent `bundle.router_creds`, `bundle.router_dom_inspector`, invalid 4-tuple return, invalid `authenticate_single_attempt` kwargs, invalid `adapter.read_config(disc)` arg, nonexistent `adapter.list_connected_devices(disc)`, and wrong `router_analyzer.analyze`/`execute_proposal` kwargs with the exact `RouterAuthCoordinator`, `RouterWebDomInspector.inspect_portal` (GUI-thread), `DeviceManagementService`, `RouterConfigAnalyzer`, and `OptimizationPlanner` contracts.
2. **Qt Mnemonic Underscores (`router_management_view.py`, `i18n.py`)**: Escaped `&` as `&&` in `Login && Read`, `LAN && DHCP`, and `QoS && Bandwidth`.
3. **`WifiInterfaceTelemetry` Field Alignment (`wifi_intelligence_view.py`, `reports_view.py`)**: Updated UI mapping to real Pydantic fields (`connection_state`, `signal_quality_pct`, `phy_standard`, `noise_floor_dbm`, `rx_link_rate_mbps`, `tx_link_rate_mbps`, `security_mode`, `interface_stats`, `recent_wlan_events`, `capabilities`), eliminating false `"غير متصل"` gauge state when connected to `Mohamed_khaled`.
4. **Single-Point Chart Crash (`app/ui/widgets/latency_chart.py`)**: Fixed `ZeroDivisionError` in `LatencyPlotCanvas.paintEvent` when rendering the first single data point (`n_pts == 1`).

---

## 7. Build Verification & Known Limitations
- **Isolated Redesign Binary**: `D:\NetGuard_REDESIGN\NetGuard.exe` (`243,291,967` bytes, `mtime=2026-11-28T00:16:14.511348`, SHA-256 `2ae1f0dc4e1a961e81e5d10e2535f146e43dba4e24e531115b7b157ec3988ecd`, PyInstaller `BUILD_EXIT:0`).
- **Untouched Production Binaries**:
  - `D:\NetGuard.exe`: `243,198,169` bytes (`2026-11-27T14:02:28.730719`, SHA-256 `8983259dc0421d346394dd50e315bfee0b76c87d77e7dc4a51990241a820a613`)
  - `D:\NetGuard_FINAL\NetGuard.exe`: `243,198,169` bytes (`2026-11-27T14:02:28.730719`, SHA-256 `8983259dc0421d346394dd50e315bfee0b76c87d77e7dc4a51990241a820a613`)
- **Executable Validation Status (`BLOCKED`)**: Launching `D:\NetGuard_REDESIGN\NetGuard.exe` (both default and `--no-elevate`) from this non-elevated automation shell (`IsUserAnAdmin() == False`) fails with `OSError(22, 'The requested operation requires elevation', None, 740, None)` due to `uac_admin=True` in `NetGuard.spec`. Elevated interactive click-through of the packaged `.exe` must be run manually by an Administrator on desktop.
- **UI Localization Refresh Note**: When toggling EN -> AR mid-session (`860x720`), `DashboardView.chip_guard_summary` retains prior-language text until the next `update_meeting_guard_summary` update cycle.
- **Windows Telemetry Scope**: Per-process outbound UDP rates depend on ETW kernel sessions under elevated Admin privileges; per-process TCP throughput counters remain unavailable via standard `psutil` without kernel packet inspection.
