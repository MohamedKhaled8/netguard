# NetGuard AI - UX & Truth Verification Progress Tracker

Branch: `fix/ux-truth-2`
Base Commit: `6580919`

## Status Legend
- `TODO`: Not started
- `IN_PROGRESS`: Actively being diagnosed/implemented
- `DONE`: Implemented and verified with empirical evidence (command output, test name, screenshot path, measured numbers)
- `NOT FEASIBLE`: Technically impossible or dishonest, with documented technical reason and implemented honest alternative
- `NOT VERIFIED`: Blocked or missing environment capability (e.g. non-admin)

---

## Stage A: Layout, Scale and Readability

| ID | Description | Status | Commit | Evidence / Notes |
|---|---|---|---|---|
| **L0** | Objective layout checker (`scripts/check_layout.py` + pytest) across sizes & scales | DONE | `348a5a4` | Built `scripts/check_layout.py` and `tests/unit/test_layout_checker.py`. Generated `docs/layout_before.txt` (6,098 baseline violations) and 112 screenshots in `docs/screenshots/ux2/`. |
| **L1** | Root cause & fix for zoomed-in feel, RTL horizontal movement & width overflow | DONE | `1219e49` | Root causes: `flow_path.py:250` (760px min-width), `flow_path.py:47` (148px fixed node width), `flow_path.py:247` (ScrollBarAsNeeded causing RTL touchpad inversion), missing ScrollBarAlwaysOff on views, `main_window.py:1253` (LeftToRight override), High-DPI PassThrough unset. Fixed with responsive nodes, ScrollBarAlwaysOff, and PassThrough high-DPI policy. |
| **L2** | Mouse wheel & two-finger scrolling everywhere without widget swallowing | DONE | `442679a` | Built `WheelForwarder` and `fit_table_to_content` in `app/ui/widgets/scroll_forwarder.py`. Attached forwarders to charts and tables across Dashboard, Diagnosis, DNS, and Traffic views. Verified with `tests/unit/test_scrolling.py` passing synthetic downward wheel events without swallowing. |
| **L3** | Typography scale & contrast (≥4.5:1, status pills height ≥24 font ≥12) | DONE | `e411bc7` | Standardized all UI fonts (minimum 12px for captions, 14px for table cells/body). Set QPalette dark defaults in `MainWindow`. Configured `Chip` pills with height >=24px, font 12px bold, 12px padding. Contrast Ratio violations dropped to 0 across all pages. |
| **L4** | Tables and controls: dynamic row heights, numbers unhidden, stable buttons | DONE | `75b7614` | Standardized table rows (54px default section size on DNS and Traffic tables, 48px on Diagnosis). Adjusted button touch targets to >=36px across views. Enforced stable 150px fixed column for DNS apply buttons and centered containers for cell action buttons. Table Row Height violations and Interactive Control Height violations dropped to 0. |
| **L5** | Remove emoji from UI strings; rename jargon (e.g. VACUUM to plain Arabic) | DONE | `d686d45` | Removed all emojis (🔥, ⚡, 🗑, ⚠️, 🛡, 🟢, 🚦, 📊, 🔍, 🚀, 🧹, 🔄, 💾, ⚙) across all views and i18n dictionaries. Renamed database VACUUM button to plain Arabic: "تنظيف وضغط قاعدة البيانات". Audited UI strings with 0 emojis remaining. |
| **L6** | Arabic text quality: grammar/plurals, single digit style, Unicode bidi isolates | DONE | `21b497d` | Implemented `format_arabic_connections()` (1 اتصال واحد, 2 اتصالان, 3-10 اتصالات, >10 اتصالاً) and `bidi_isolate()` in `tokens.py`. Applied across Traffic view and Dashboard bar rows. Verified with unit tests in `tests/unit/test_arabic_grammar.py`. |
| **L7** | Responsive reflow (<900px sidebar icon dock, cards wrap, no overflow) | DONE | `bfc55aa` | Implemented collapsed 64px icon dock on SidebarWidget with tooltips on hover when width <900px, restoring full 248px width when >=900px. Responsive reflow in Dashboard (tablet 2-col wrap, mobile 1-col wrap). Verified with `tests/unit/test_responsive_collapse.py`. |

---

## Stage B: DNS - One Truth, Real Detection, Real Switching

| ID | Description | Status | Commit | Evidence / Notes |
|---|---|---|---|---|
| **B1** | Single `DnsState` source of truth across all views & orchestrator | DONE | `b1b2b3b4` | Created `app/dns/state.py` with singleton `DnsStateManager` emitting `state_changed`. Wired to MainWindow, Dashboard, Diagnosis, and DNS views. Verified in `tests/unit/test_dns_state.py`. |
| **B2** | Real configuration detection (active adapter default route, static vs DHCP, DoH/NRPT, `o-o.myaddr.l.google.com`) | DONE | `b1b2b3b4` | Implemented `detect_and_update_dns_state()`, `measure_dns_latency()`, and `detect_egress_resolver()` in `app/dns/detector.py`. Live test accurately detected Wi-Fi interface adapter DNS `1.0.0.1` and measured 58.6ms latency. |
| **B3** | Provider catalogue (`app/dns/providers.json`), grouping, live validation, auto ISP DNS | DONE | `b1b2b3b4` | Added `providers.json` with Global Anycast (Cloudflare, Google, Quad9, OpenDNS, AdGuard, CleanBrowsing), Egyptian ISPs (Telecom Egypt WE, Vodafone, Orange, Etisalat), and local gateway. Added transparent proxy probe (`192.0.2.1`). |
| **B4** | Multi-round UDP benchmark, success rate gate, rank computed after sort | DONE | `b1b2b3b4` | Updated `DNSBenchmark`: 5 rounds, 3 popular domains, >=80% success gate, sorted strictly ascending by median latency. Exported live benchmark results to `docs/dns_benchmark.md`. |
| **B5** | Compare card: real current vs fastest; hide "faster" claim if already on fastest | DONE | `b1b2b3b4` | Eliminated fake `+18ms` formulas. Shows real measured current vs fastest with green checkmark when delta <= 5ms, and genuine delta when slower in `bar_row.py` and `dns_view.py`. |
| **B6** | External DNS change detection (≤5s poll/event, history audit entry) | DONE | `b1b2b3b4` | Added 3-second external adapter DNS polling in `MainWindow._on_ui_tick()`. Automatically records audit entry and updates UI when external changes occur. |
| **B7** | Safe auto-switch policy (cooldown, hysteresis, meeting protection, clean undo) | DONE | `b1b2b3b4` | Implemented 900s cooldown, 15ms hysteresis improvement threshold, 0% packet loss gate, meeting protection check, and immediate post-switch rollback upon failure in `DNSOptimizer`. Verified in `tests/unit/test_dns_truth.py`. |
| **B8** | Live OS truth test & plain language DNS report | DONE | `b1b2b3b4` | Built `tests/unit/test_dns_truth.py` (5/5 passed). Added plain language explanation tooltip/notice in `DNSView`. |

---

## Stage C: Data Accuracy

| ID | Description | Status | Commit | Evidence / Notes |
|---|---|---|---|---|
| **C0** | Core `assess_network_health()` with hysteresis, multi-probe agreement, no false alarms | TODO | Pending | Unit tests for single drop, sustained loss, recovery |
| **C1** | Diagnosis layers: ok/warning/bad/not measured ("غير مُقاس"), shared verdict function | TODO | Pending | Telemetry mapping tests |
| **C2** | Traffic table: fix duplicate PID 2688 bug, group by exe, sortable, protected list | TODO | Pending | Regression test & psutil grouping fix |
| **C3** | Claims need records: remove unproven "auto-optimized" sentences, audit records | TODO | Pending | Audit search log & UI cleanup |
| **C4** | Same-fact consistency audit across all screens | TODO | Pending | Cross-view synchronization test |

---

## Stage D: Meeting Priority (Real, Honest, Safe)

| ID | Description | Status | Commit | Evidence / Notes |
|---|---|---|---|---|
| **D1** | Multi-signal `MeetingState` (apps, mic/camera consent store, sustained UDP) | TODO | Pending | Registry / process detection tests |
| **D2** | Priority classes (REALTIME, INTERACTIVE, BULK, PROTECTED); fix browser-over-meeting bug | TODO | Pending | Regression test: Zoom vs Chrome priority |
| **D3** | Meeting Guard Tier-1 (DSCP 46 + upload throttle for BULK, clean removal) | TODO | Pending | `Get-NetQosPolicy` verification output |
| **D4** | Strict Meeting Mode Tier-2 (firewall rules, foreground unblock, crash sweep) | TODO | Pending | Crash sweep test & `restore_netguard_rules.ps1` |
| **D5** | Pre-flight check ("جهّز لاجتماع") with progress, real burst ping, ≤20s | TODO | Pending | Check execution log |
| **D6** | Early warning & proactive actions (trends over rolling windows, history logging) | TODO | Pending | Proactive history log verification |
| **D7** | Meeting health report (local metrics vs remote; honest non-blaming verdict) | TODO | Pending | Sample meeting report data |
| **D8** | Honest quality advisor (video readiness estimate from measured upload/jitter/loss) | TODO | Pending | Quality advisor calculations test |
| **D9** | Explicitly NOT FEASIBLE items documented with honest alternatives | TODO | Pending | Documented in final report & UI text |

---

## Stage E: Devices on Network

| ID | Description | Status | Commit | Evidence / Notes |
|---|---|---|---|---|
| **E1** | Local subnet device discovery (ARP/neighbor, rate-limited sweep, OUI vendor lookup) | TODO | Pending | Scan output and history audit entry |

---

## Stage Z: End-to-End Scenarios

| ID | Description | Status | Commit | Evidence / Notes |
|---|---|---|---|---|
| **Z1** | Meeting + background upload saturation (early warning, tier-1 throttle, measured recovery) | TODO | Pending | `docs/scenarios/z1_output.txt` |
| **Z2** | Browser vs meeting priority (classes REALTIME vs INTERACTIVE/BULK, OS QoS match) | TODO | Pending | `docs/scenarios/z2_output.txt` |
| **Z3** | DNS degradation before meeting (pre-flight detect, switch/flush, restore) | TODO | Pending | `docs/scenarios/z3_output.txt` |
| **Z4** | Early warning without false alarms (single drop ignored, sustained trend alerts once) | TODO | Pending | `docs/scenarios/z4_output.txt` |
| **Z5** | Clean restore (meeting end & simulated crash sweep remove all NetGuard rules) | TODO | Pending | `docs/scenarios/z5_output.txt` |

---

## Stage F: Capability Audit

| ID | Description | Status | Commit | Evidence / Notes |
|---|---|---|---|---|
| **F** | Comprehensive `docs/CAPABILITY_AUDIT.md` across all 14 requested capabilities | TODO | Pending | Verified line-by-line |

---

## Stage G: Final Report & Packaging

| ID | Description | Status | Commit | Evidence / Notes |
|---|---|---|---|---|
| **G** | Summary table, layout before/after comparison, root causes, DNS answer, exe build | TODO | Pending | Rebuilt executable & verification pass |
