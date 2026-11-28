# NetGuard AI — Pass 4 Test Results

## 1. Test Environment Summary
- **Operating System**: Windows 11 Enterprise (Build 26300.0)
- **Python**: 3.12.10 (64-bit)
- **Virtual Environment**: `E:\Mt FlutterProject\netguard\.venv`
- **Pytest**: 9.2.2 / Pluggy 1.5.0
- **PyInstaller**: 6.22.3 (contrib hooks 2026.10)
- **Target Executable**: `D:\NetGuard.exe`

---

## 2. Unit and Regression Test Suites

### A. Core Pass 4 Regression Suites (Command Executed)
```powershell
& "e:\Mt FlutterProject\netguard\.venv\Scripts\pytest.exe" tests/unit/test_meeting_detector.py tests/unit/test_meeting_mode_qos.py tests/unit/test_m3_closed_loop_settings.py -v
```
**Result**: `59 passed in 60.41s`
- `tests/unit/test_meeting_detector.py` (43 passed):
  - Per-PID outbound UDP telemetry calculation verified.
  - Absence of send events with high process I/O disk writes verified as NOT in call.
  - Bound UDP sockets without active send events verified as NOT in call.
  - Removal of `pytest in sys.modules` synthetic bypass verified.
  - Generic `MeetingAppRegistry` profiles (Zoom, Teams, Meet, Slack, Discord, Skype, Webex) verified.
  - Fail-closed telemetry behavior verified.
  - Cycle diagnostic emission verified.
- `tests/unit/test_meeting_mode_qos.py` (5 passed):
  - Precedence hierarchy (200, 170, 160, 150, 100, 50) verified.
  - 14-scenario policy conflict and specificity matrix verified.
  - `svchost.exe` exemption verified.
  - ActiveStore readback property matching verified.
- `tests/unit/test_m3_closed_loop_settings.py` (11 passed):
  - Removal of fabricated 0/5/25 default baselines verified.
  - Telemetry freshness check (<= 10.0s) verified.
  - Stale/missing telemetry rejection verified.
  - Settings hydration from `UserSettings` verified.
  - Kill Switch widget wiring and `kill_switch_disable()` verified.
  - Active upload capacity test bounded execution verified.

### B. E2E Acceptance Test Suites
- `tests/e2e/test_e2e_pass4_tier1.py`: 115 tests covering all 23 core features across M1–M4.
- `tests/e2e/test_e2e_pass4_tier2.py`: 115 tests covering boundaries, rate clamps, and fault injection.
- `tests/e2e/test_e2e_pass4_tier3.py`: 38 tests covering cross-feature interactions and state transitions.
- `tests/e2e/test_e2e_pass4_tier4.py`: 5 tests covering empirical user trace replays (IDE Idle, IDE Call, EXE Call, EXE Idle).
- **Total E2E Tests**: 273 tests compiled and validated.

---

## 3. Windows Native QoS Self-Test

### Command
```powershell
powershell -ExecutionPolicy Bypass -File scripts/test_qos_shapes.ps1
```
### Verified Shapes & Output
- **Shape 1 (Media Outbound Priority)**: `Zoom.exe` UDP 8801-8810, DSCP 34, Precedence 200 -> Verified in ActiveStore.
- **Shape 2 (Background Demotion)**: Default DSCP 8, Precedence 50 -> Verified in ActiveStore.
- **Shape 3 (Bulk Upload Throttle)**: TCP, DSCP 8, ThrottleRate 5000000 bps, Precedence 100 -> Verified in ActiveStore.
- **Shape 4 (DNS Exemption)**: UDP port 53, DSCP 0, Precedence 160 -> Verified in ActiveStore.
- **Cleanup Status**: `CLEANUP=PASS` (All temporary test policies removed and verified absent from ActiveStore).
