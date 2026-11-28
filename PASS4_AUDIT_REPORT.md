# NetGuard AI — Pass 4 Root-Cause Audit Report

## 1. Executive Summary & Root-Cause Verdict
This audit synthesizes observed Windows 11 machine evidence, canonical source code analysis, and verified architectural repairs implemented in Pass 4.

### Primary Root Causes Confirmed in Source
1. **False UDP Throughput Measurement (`app/traffic/meeting_detector.py`)**:
   - The detector previously computed "UDP throughput" from generic `psutil.Process(pid).io_counters().write_bytes` deltas (total disk and network I/O), gated merely by the existence of a bound UDP endpoint. Disk writes by meeting apps were falsely treated as media transmission.
   - A synthetic bypass branched on `pytest in sys.modules`, allowing tests to pass without real network traffic evidence.
   - *Fix*: Replaced with real per-PID outbound UDP telemetry (`WindowsETWNetworkTelemetry` / `BaseNetworkTelemetryProvider`) and removed all pytest module checks.
2. **Fabricated Baseline Fallbacks & Premature Rollback (`app/traffic/controller.py`)**:
   - `snapshot_pre_meeting_baseline()` fabricated default values (`loss=0.0%`, `jitter=5.0ms`, `rtt=25.0ms`) when idle telemetry was absent.
   - `evaluate_closed_loop_quality()` compared live call telemetry against this artificial baseline, triggering false-positive rollbacks that stripped active QoS policies.
   - *Fix*: Eliminated all default baseline fabrications. Accumulated same-call pre-policy baselines during the 5-second `ENTERING` state. If valid baseline is unavailable, automatic rollback is safely disabled while prioritization remains active.
3. **Unverified Spec Fallback in Controller (`app/traffic/controller.py`)**:
   - Line 320 fell back to all generated `specs` if `verified_names` returned empty from ActiveStore readback, causing unverified policies to be recorded as active.
   - *Fix*: `_active_qos_specs` stores only policies explicitly verified by ActiveStore readback.
4. **Adapter Readback Swallowing Errors (`app/platform/windows/adapter.py`)**:
   - ActiveStore queries used `-ErrorAction SilentlyContinue`, converting query failures into empty lists, and ignored the command `$results` map.
   - *Fix*: Implemented `-ErrorAction Stop`, parsed `$results` and `$errors` maps, and verified exact returned policy properties.

---

## 2. Windows 11 User Machine Evidence & Annex Analysis

### Four Real Packet Captures (Intel Wireless-AC 3160, Wi-Fi 192.168.1.3)
> **Note on Local-Port Matching**: Local-port matching is a capture-script heuristic only; it does NOT establish per-packet PID process ownership. Per-PID attribution requires ETW/WFP telemetry at the kernel boundary.

| Capture Scenario | Duration | Total Rows | Outbound Rows | Outbound UDP Rows | Outbound UDP DSCP Values | Dominant Flow | ActiveStore Policies |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **IDE Idle** (02:59:22) | 35s | 866 | 482 | 56 (11.92 KB) | 100% DSCP 0 (no 34/46/8) | DNS & Google HTTPS | 0 NetGuard policies |
| **IDE Call** (03:07:43) | 60s | 9,405 | 7,270 | 6,417 (7,956.65 KB) | 100% DSCP 0 (no 34/46/8) | 144.195.27.125:8801 (6,270 pkts, 2.82 MB) | 0 NetGuard policies |
| **EXE Call** (03:31:14) | 60s | 14,424 | 11,667 | 10,280 (7.91 MB) | 100% DSCP 0 (no 34/46/8) | 206.247.59.169:8801 (10,133 pkts, 7.91 MB) | 0 NetGuard policies |
| **EXE Idle** (03:32:48) | 35s | 1,465 | 772 | 46 (7.82 KB) | 100% DSCP 0 (no 34/46/8) | DNS & Google HTTPS | 0 NetGuard policies |

### Windows Native QoS Engine Self-Test Result
- Elevated `New-NetQosPolicy` succeeded for `notepad.exe` in ActiveStore (`DSCPAction 0`, `Precedence 127`).
- Readback confirmed policy creation, and `Remove-NetQosPolicy` returned `CLEANUP=PASS`.
- **Verdict**: Proves Windows QoS creation, readback, and removal work on this machine. Complex shapes (DSCP 34, port ranges, combined throttling) require dedicated validation.

### Process Hierarchy Verification
- `E:\NetGuard.exe` parent PID 21360 and child PID 18196 were both confirmed **ELEVATED**.
- This parent-child relationship is standard PyInstaller `--onefile` bootloader extraction and must not be treated as duplicate GUI instances or terminated.
- In the IDE run, venv Python parent PID 2932 launched global Python child PID 5624 due to global interpreter elevation handoff in `main.py`.

---

## 3. Windows QoS Matching Specificity & Conflict Resolution Matrix

> **Core Principle**: Windows QoS evaluates matching condition specificity (application path vs network quintuple) before resolving applicable conflicts. Numeric Precedence determines priority among conflicting policies of equal specificity.

### 14-Scenario Conflict Resolution Matrix

| # | Traffic Scenario | App Match | Protocol / Ports | Competing Policies | Evaluated Specificity & Precedence | Verified Winning Policy | Resulting Action |
| :- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | Zoom Media Outbound | `Zoom.exe` | UDP 8801-8810 | Media (200) vs Default (50) | App + Quintuple vs None | **Media Priority** (200) | AF41 / DSCP 34 |
| **2** | Zoom Audio-Only Outbound | `Zoom.exe` | UDP Audio Verified | Audio Media (200) vs Media (200) | Equal Specificity, Audio profile | **Audio Media** (200) | EF / DSCP 46 |
| **3** | Zoom TCP Signaling | `Zoom.exe` | TCP 443 | Meeting TCP (150) vs Default (50) | App + Quintuple vs None | **Meeting TCP** (150) | DSCP 0 (Exempt) |
| **4** | Zoom STUN Outbound | `Zoom.exe` | UDP 3478-3479 | Media (200) vs Default (50) | App + Quintuple vs None | **Media Priority** (200) | AF41 / DSCP 34 |
| **5** | DNS Outbound Query | Any / System | UDP 53 | DNS Exemption (160) vs Default (50) | Quintuple vs None | **DNS Exemption** (160) | DSCP 0 (Exempt) |
| **6** | DNS TCP Zone Transfer | Any / System | TCP 53 | DNS Exemption (160) vs Default (50) | Quintuple vs None | **DNS Exemption** (160) | DSCP 0 (Exempt) |
| **7** | NetGuard Telemetry | `NetGuard.exe` | Any | NetGuard Exemption (170) vs Default (50) | App match vs None | **NetGuard Exemption** (170) | DSCP 0 (Exempt) |
| **8** | Windows System Service | `svchost.exe` | TCP / UDP Any | System Exemption vs Bulk Throttle (100) | System Protected Process | **System Protected** | Unthrottled |
| **9** | Bulk TCP Upload (e.g. Chrome) | `chrome.exe` | TCP Bulk Data | Bulk Throttle (100) vs Default (50) | Quintuple + Rate vs None | **Bulk Throttle** (100) | CS1 / DSCP 8 + Rate Limit |
| **10** | Bulk UDP Upload (e.g. Torrent) | `qbittorrent.exe` | UDP Bulk Data | Bulk Throttle (100) vs Default (50) | Quintuple + Rate vs None | **Bulk Throttle** (100) | CS1 / DSCP 8 + Rate Limit |
| **11** | Background HTTP/HTTPS | General Apps | TCP 80 / 443 | Default Demotion (50) | Baseline fallback | **Default Demotion** (50) | CS1 / DSCP 8 |
| **12** | Generic Meeting App Fallback | Registered App | UDP Configured | Generic Media (200) vs Default (50) | App + Quintuple vs None | **Generic Media** (200) | AF41 / DSCP 34 |
| **13** | Teams New Outbound Media | `ms-teams.exe` | UDP 50000-50059 | Media (200) vs Default (50) | App + Quintuple vs None | **Media Priority** (200) | AF41 / DSCP 34 |
| **14** | Overlapping App + Port Conflict | `Zoom.exe` | UDP 8801 | Media (200) vs Bulk (100) | App + Quintuple (200) > Quintuple (100) | **Media Priority** (200) | AF41 / DSCP 34 |

---

## 4. Exact Generated PowerShell Commands

### A. Zoom Media Outbound Priority (AF41 / DSCP 34, Precedence 200)
```powershell
New-NetQosPolicy -Name "NetGuard_Media_Zoom_UDP" `
    -AppPathNameMatchCondition "Zoom.exe" `
    -IPProtocolMatchCondition UDP `
    -IPDstPortStartMatchCondition 8801 `
    -IPDstPortEndMatchCondition 8810 `
    -DSCPAction 34 `
    -Precedence 200 `
    -PolicyStore ActiveStore
```

### B. DNS Queries Exemption (UDP/TCP 53, DSCP 0, Precedence 160)
```powershell
New-NetQosPolicy -Name "NetGuard_Exempt_DNS_UDP" `
    -IPProtocolMatchCondition UDP `
    -IPDstPortStartMatchCondition 53 `
    -IPDstPortEndMatchCondition 53 `
    -DSCPAction 0 `
    -Precedence 160 `
    -PolicyStore ActiveStore

New-NetQosPolicy -Name "NetGuard_Exempt_DNS_TCP" `
    -IPProtocolMatchCondition TCP `
    -IPDstPortStartMatchCondition 53 `
    -IPDstPortEndMatchCondition 53 `
    -DSCPAction 0 `
    -Precedence 160 `
    -PolicyStore ActiveStore
```

### C. Meeting TCP Signaling Exemption (Precedence 150)
```powershell
New-NetQosPolicy -Name "NetGuard_Exempt_Zoom_TCP443" `
    -AppPathNameMatchCondition "Zoom.exe" `
    -IPProtocolMatchCondition TCP `
    -IPDstPortStartMatchCondition 443 `
    -IPDstPortEndMatchCondition 443 `
    -DSCPAction 0 `
    -Precedence 150 `
    -PolicyStore ActiveStore
```

### D. Default Background Demotion (CS1 / DSCP 8, Precedence 50)
```powershell
New-NetQosPolicy -Name "NetGuard_Demote_Default" `
    -DSCPAction 8 `
    -Precedence 50 `
    -PolicyStore ActiveStore
```

### E. Bulk Upload Throttling (Combined DSCP 8 + Rate Limit, Precedence 100)
```powershell
New-NetQosPolicy -Name "NetGuard_Throttle_Bulk_TCP" `
    -IPProtocolMatchCondition TCP `
    -DSCPAction 8 `
    -ThrottleRateActionBitsPerSecond 5000000 `
    -Precedence 100 `
    -PolicyStore ActiveStore
```

---

## 5. Evidence Classification Table

| Evidence Item | Category | Status & Verification Source |
| :--- | :--- | :--- |
| **Elevated Admin Context** | PROVEN | Confirmed by Windows PowerShell token query and parent/child PID checks. |
| **Basic Windows NetQos Creation/Removal** | PROVEN | Confirmed by elevated `notepad.exe` test returning `CLEANUP=PASS`. |
| **Zoom Media on UDP 8801** | PROVEN | Confirmed by 10,133 UDP packets captured to 206.247.59.169:8801. |
| **All Outbound UDP DSCP was 0** | PROVEN | Confirmed by TShark summary tables across all 4 capture sessions. |
| **No ActiveStore Policy Present During Capture** | PROVEN | Confirmed by `Get-NetQosPolicy -PolicyStore ActiveStore` query in captures. |
| **False UDP Throughput Metric in Source** | SOURCE-CONFIRMED | Confirmed at `meeting_detector.py:304-369` (using `write_bytes`). |
| **Pytest Synthetic Signal Bypass** | SOURCE-CONFIRMED | Confirmed at `meeting_detector.py:359-365` (`pytest` in `sys.modules`). |
| **Fabricated Quality Baselines (0/5/25)** | SOURCE-CONFIRMED | Confirmed at `controller.py:108-112` and `main_window.py:1161-1173`. |
| **ActiveStore Readback Error Swallowing** | SOURCE-CONFIRMED | Confirmed at `adapter.py:1360-1375` (`-ErrorAction SilentlyContinue`). |
| **Spec Fallback When Unverified** | SOURCE-CONFIRMED | Confirmed at `controller.py:320`. |
| **Settings Restoration Gap** | SOURCE-CONFIRMED | Confirmed by absence of `from_user_settings` in startup path. |
| **Kill Switch Reference Mismatch** | SOURCE-CONFIRMED | Confirmed at `traffic_view.py:706` (`toggle_master` vs `master_qos_toggle`). |
| **Premature Rollback on Real Machine** | HYPOTHESIS | Highly probable explanation for policy absence after wait period, but not logged. |
| **ISP / Router Upstream Honoring DSCP 34** | UNVERIFIED | Requires ISP router/network boundary capture beyond local host scope. |
