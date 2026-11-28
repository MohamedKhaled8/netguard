# NetGuard AI — Pass 4 Changelog

## Overview
This changelog documents the complete file-by-file changes implemented during Pass 4 Root-Cause Repair and Hardening. All changes adhere to the canonical repository specifications and requirements R1–R5.

---

### 1. `app/traffic/meeting_detector.py`
- **Replaced False UDP Throughput**: Replaced generic process I/O delta (`psutil.Process.io_counters().write_bytes`) with real per-process outbound UDP network send telemetry architecture (`WindowsETWNetworkTelemetry` / `BaseNetworkTelemetryProvider`).
- **Removed Pytest Bypass**: Completely eliminated the production `sys.modules` check that previously simulated artificial throughput when pytest was detected.
- **Fail-Closed Telemetry**: If real per-PID network telemetry is unavailable, the detector fails closed and reports `metric_unavailable` instead of falling back to disk I/O.
- **Bound Socket Guard**: A bound UDP endpoint without active outbound send events is explicitly classified as inactive.
- **Structured Diagnostics**: Added `CandidateEvaluationDiagnostic` emitting PID, process name, matched endpoints, UDP send rate, confidence score, and rejection reasons.

### 2. `app/traffic/meeting_registry.py`
- **Generic Data-Driven Registry**: Formalized profiles for Zoom (`Zoom.exe`, UDP 8801–8810, STUN 3478–3479), Microsoft Teams classic/new (`Teams.exe`, `ms-teams.exe`), Google Meet (browser processes), Slack Huddles (`slack.exe`), Discord (`Discord.exe`), Skype (`Skype.exe`), and Webex (`CiscoCollabHost.exe`).
- **Generic Fallback**: Implemented safe configurable UDP fallback with closed-loop safeguards for unknown or undocumented meeting profiles.

### 3. `app/traffic/qos_config.py`
- **Precedence Hierarchy**: Enforced strict numeric precedence:
  - Precedence 200: Meeting media outbound UDP priority (AF41 / DSCP 34 default for Zoom; EF / DSCP 46 strictly audio-only).
  - Precedence 170: NetGuard self-diagnostic and telemetry exemptions.
  - Precedence 160: DNS exemptions on UDP/TCP port 53.
  - Precedence 150: Meeting signaling on TCP 443 (restricted to meeting executables; no global 443 exemption).
  - Precedence 100: Bulk upload throttling (combining CS1 / DSCP 8 and rate limit).
  - Precedence 50: Background default demotion (CS1 / DSCP 8).
- **Protection Rules**: Explicitly protected `svchost.exe`, critical Windows system services, DNS, and NetGuard from throttling.
- **Settings Serialization**: Added `AppQoSConfig.from_user_settings()` and `to_user_settings()` with backward compatibility.

### 4. `app/platform/windows/adapter.py`
- **ActiveStore Verification**: Replaced swallowed errors with explicit `-ErrorAction Stop` on verification queries.
- **Results Map Consumption**: Parsed command `$results` and `$errors` maps to confirm New-NetQosPolicy execution before readback.
- **Property Matching**: Verified returned policy properties (AppPath, Protocol, Ports, DSCP, ThrottleRate, Precedence, PolicyStore) rather than checking name existence alone.
- **Lock Safety & Exact Cleanup**: Guaranteed `_qos_lock` acquisition on `sweep_all_netguard_rules()`, returning busy if not acquired, and enumerated exact NetGuard policy names for removal without unverified wildcard deletes.

### 5. `app/traffic/controller.py`
- **Spec Fallback Elimination**: Removed unsafe fallback where unverified specs were marked active if `verified_names` was empty; active policy state reflects only confirmed policies.
- **Removal of Fabricated Baselines**: Eliminated default 0.0% loss, 5.0ms jitter, 25.0ms RTT magic fallbacks in `snapshot_pre_meeting_baseline()`.
- **Same-Call Pre-Policy Baseline**: Collected genuine pre-policy samples during `ENTERING` state (5s window). If fewer than 5 valid samples exist, automatic rollback is safely disabled while prioritization continues.
- **Structured Rollback Logging**: Logged exact timestamps, triggering metric, baseline vs current median, threshold, removed policy names, and verification.

### 6. `app/ui/main_window.py`
- **Live Telemetry Wiring**: Connected fresh probe telemetry (freshness <= 10.0s) to `controller.record_quality_sample()`, rejecting stale/missing data without synthetic zero conversion.
- **DNS Meeting Freeze**: Blocked DNS benchmarking, resolver switching, DNS cache flushing, adapter resets, and DHCP renewals while meeting state is `ENTERING`, `ACTIVE`, or `LEAVING`.
- **Preflight UI Accuracy**: Corrected preflight dialog copy to reflect actual executed actions rather than claiming QoS priority was applied when only flushing DNS.

### 7. `app/core/settings.py` & `app/application.py`
- **Settings Hydration**: Hydrated `AppQoSConfig` from `UserSettings` prior to controller and view instantiation.
- **Schema Preservation**: Prevented dictionary coercion to boolean in `UserSettingsSchema` for `qos_enabled_apps`.

### 8. `app/ui/views/traffic_view.py`
- **Kill Switch Reference Fix**: Corrected widget reference from `self.toggle_master` to `self.master_qos_toggle`, added reentrancy guard, and wired `kill_switch_disable()`.

### 9. `app/remediation/orchestrator.py`
- **Safety Interlock**: Added `meeting_guard_check()` enforcing strict freeze on disruptive remediation actions during active meetings.

### 10. `app/traffic/preflight.py`
- **Active Upload Capacity Test**: Implemented bounded duration (<= 3.0s), low overhead (<= 1.5MB), safe HTTPS chunk upload measurement restricted strictly to idle periods. Wired result into `set_preflight_metrics()`.

### 11. `scripts/build_exe.py`
- **Target D:\ Deployment**: Configured primary target output to `D:\NetGuard.exe` and `D:\NetGuard_FINAL\NetGuard.exe` with PyInstaller one-file, windowed, elevated UAC administrator execution (`--uac-admin`).

### 12. `scripts/test_qos_shapes.ps1`
- **Windows QoS Self-Test Script**: Created standalone elevated PowerShell script testing all 4 policy shapes (Media priority, Default demote, Bulk throttle, DNS exemption) in ActiveStore with property verification and guaranteed cleanup (`CLEANUP=PASS`).
