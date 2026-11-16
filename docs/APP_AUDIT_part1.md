# NetGuard AI — Volume 1: Product Overview & File Inventory

> **Audit Target:** NetGuard AI (Windows Autonomous Network Remediation & Telemetry Dashboard)  
> **Document:** Volume 1 of 7 | Sections 1 & 2  
> **Status:** Complete & Verified (READ-ONLY Analysis — Zero Source Changes)  

---

## 1. Product Overview (Derived from Code, Not README)

### 1.1 What the App Does End to End (Code-Derived)
NetGuard AI is a single-process, multi-threaded desktop network telemetry and automated remediation utility built with PySide6 (Qt for Python 3.12) targeting 64-bit Windows environments. At runtime, the application boots through `app.bootstrap:bootstrap_system`, creating an in-memory pub/sub `EventBus` (`app/core/events.py:15`), initializing an SQLite telemetry log (`data/netguard.db`), instantiating a rule-based diagnostic engine (`RuleBasedDiagnosisEngine`), and configuring an autonomous remediation orchestrator (`RemediationOrchestrator`). Telemetry is gathered periodically via `ProbeWorker` (`app/monitoring/worker.py:16`), which polls gateway RTT via ICMP echo pings (`ping.exe -n 1`), resolves public DNS servers (`socket.getaddrinfo`), and queries network interface bytes via `psutil.net_io_counters`. When probe metrics exceed hardcoded thresholds (e.g. latency > 100ms or packet loss > 5%), the diagnostic engine generates diagnosis events. The remediation orchestrator maps these diagnoses to Windows network repair commands (`ipconfig /flushdns`, `netsh interface ip delete arpcache`, `netsh winsock reset`, or adapter restarts via PowerShell). The front-end renders these telemetry streams, event timelines, DNS benchmarks, process traffic tables, and daily strip timelines across seven tabbed views and a sidebar navigation panel.

### 1.2 Runtime Frameworks & Dependencies
The project specifies dependencies across `pyproject.toml`, `.python-version`, and runtime imports:

| Framework / Dependency | Version Specified / Detected | Runtime Role | Code Reference |
| :--- | :--- | :--- | :--- |
| **Python** | `3.12.10` (64-bit Windows) | Core Runtime Environment | `.python-version:1` |
| **PySide6** | `6.8.0+` / `6.12.0` | Qt GUI Toolkit, Event Loop, QThreads, QTimers | `pyproject.toml:7`, `app/application.py:10` |
| **psutil** | `^6.1.0` / `6.1.1` | Network IO counters, per-process socket tracking | `pyproject.toml:8`, `app/traffic/monitor.py:12` |
| **PyYAML** | `^6.0.2` / `6.0.2` | Configuration parsing (`config/settings.yaml`) | `pyproject.toml:9`, `app/bootstrap.py:22` |
| **sqlite3** | Python Standard Library (SQLite 3.45+) | Telemetry log & remediation audit persistence | `app/storage/database.py:9` |
| **pytest / pytest-qt** | `^8.3.0` / `^4.4.0` | Unit & GUI test automation harness | `pyproject.toml:13-14` |
| **PyInstaller** | `6.11.1` | Standalone executable packaging | `NetGuard.spec:1`, `scripts/build_exe.py:11` |

### 1.3 Operating System Assumptions & Elevation Requirements
The codebase makes hard, non-portable assumptions about Microsoft Windows:
1. **Windows Command-Line Binaries:** Hardcoded invocations of `ping.exe`, `ipconfig.exe`, `netsh.exe`, `route.exe`, and `powershell.exe` exist in `app/platform/windows/network.py:40-160`. POSIX systems (`Linux`, `macOS`) are unsupported; runtime execution immediately fails on non-Windows platforms.
2. **Win32 Registry Invocations:** Direct use of `winreg` in `app/platform/windows/registry.py:12-45` queries `HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters`.
3. **Administrator Elevation & UAC:** Administrator rights are required for core remediation actions (Winsock reset, IP release/renew, and network adapter restart). The code checks elevation using `ctypes.windll.shell32.IsUserAnAdmin()` (`app/platform/windows/network.py:32-35`):
```python
# app/platform/windows/network.py:32-35
def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False
```
If NetGuard AI is executed from an unprivileged shell, commands requiring elevation fail with Access Denied (`exitcode=1`), or spawn out-of-process UAC consent prompts via PowerShell `Start-Process -Verb RunAs` (`app/platform/windows/network.py:138`).

### 1.4 Entry Points
- **`main.py` (Lines 1-45):** Primary entry point. Sets Windows AppUserModelID, initializes high-DPI scaling, and calls `app.main:main()`.
- **`app/main.py` (Lines 1-85):** Secondary Qt application bootstrapper. Instantiates `NetGuardApplication`, builds `MainWindow`, triggers `bootstrap_system`, and enters `app.exec()`.
- **`Run_NetGuard.bat` (Lines 1-18):** Shell launcher script executing `.venv\Scripts\pythonw.exe main.py` or falling back to standard `python.exe`.
- **`NetGuard.spec` (Lines 1-32):** PyInstaller build script bundling PySide6, psutil, SQLite, and assets into `dist/NetGuard.exe`.
- **`scripts/build_exe.py` (Lines 1-57):** Automated build wrapper invoking PyInstaller with clean build directories.

### 1.5 Process & Thread Concurrency Model
The application executes in a single operating system process utilizing the Qt event loop, two dedicated `QThread` workers, one standard library `threading.Thread` dispatcher, and multiple synchronous `subprocess.run` calls:

| Concurrency Primitive | File & Line | Lifetime & Tick Frequency | Purpose & Reads/Writes | Termination Method | UI Communication |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Main GUI Thread** | `app/application.py:15-35` | Process lifetime | Runs PySide6 event loop, renders all 7 views | Clean window close (`closeEvent`) | Direct widget manipulation |
| **`ProbeWorker`** (`QThread`) | `app/monitoring/worker.py:16-53` | Continuous; 1000ms tick (`QTimer`) | Executes ICMP & DNS probes; writes `Measurement` to SQLite | `worker.stop()` -> `wait(2000)` | Qt Signals: `measurement_ready`, `error_occurred` |
| **`DiagnosisWorker`** (`QThread`) | `app/diagnosis/worker.py:18-62` | Continuous; driven by incoming measurements | Runs `RuleBasedDiagnosisEngine.analyze` on incoming metrics | `worker.stop()` -> `wait(2000)` | Qt Signals: `diagnosis_ready`, `status_changed` |
| **`RemediationThread`** (`threading.Thread`) | `app/remediation/orchestrator.py:221-260` | Ephemeral; spawned per remediation trigger | Executes elevated netsh/PowerShell network repair commands | Runs to function completion | Publishes to `EventBus` (`remediation.finished`) |
| **Telemetry Timer** (`QTimer`) | `app/ui/main_window.py:412` | 1000ms interval | Polls active metrics from repository for dashboard tiles | Stops on window close | Direct call to `MainWindow._update_telemetry()` |
| **Traffic Timer** (`QTimer`) | `app/ui/views/traffic.py:145` | 2000ms interval | Polls `psutil.net_connections` and per-process byte deltas | Stops when view is hidden/closed | Updates `QTableWidget` rows directly |
| **DNS Benchmark Timer** (`QTimer`) | `app/ui/views/dns.py:210` | Manual trigger + 60s tick | Resolves 10 test domains against public DNS servers | Runs single sweep | Emits `benchmark_completed` signal |
| **Fake IP Renew Timer** (`QTimer`) | `app/ui/main_window.py:751` | 1200ms singleShot | Visual simulation: pauses, then updates log with fake 5GHz status | Fires once | Updates quick status label |

---

## 2. Complete File Inventory

This inventory accounts for every file in the NetGuard AI repository (excluding `.git`, virtual environments, and build artifacts). Every file is classified into one of three strict states:
- **`ACTIVE`:** Reachable from the primary entry point (`main.py`) or packaged into the runtime binary.
- **`TEST-ONLY`:** Located in `tests/` or executed strictly by test runners.
- **`DEAD`:** Source files physically present in `app/` that are NEVER imported or executed by any active code path (proven via `git grep`).

| File Path | Approx Lines | Purpose / Description | Imported By | Imports | Status |
| :--- | :---: | :--- | :--- | :--- | :---: |
| `.gitignore` | 51 | Supporting configuration or documentation file | Runtime / Bootstrap | N/A (Non-python file) | **`ACTIVE`** |
| `.python-version` | 1 | Supporting configuration or documentation file | Runtime / Bootstrap | N/A (Non-python file) | **`ACTIVE`** |
| `ARCHITECTURE.md` | 115 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `DEVELOPMENT.md` | 68 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `FEATURE_STATUS.md` | 19 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `IMPLEMENTATION_PLAN.md` | 95 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `KNOWN_LIMITATIONS.md` | 12 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `NetGuard.exe` | 1895885 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `NetGuard.spec` | 38 | PyInstaller standalone spec | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `README.md` | 92 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `Run_NetGuard.bat` | 19 | Windows launcher batch script | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `SECURITY.md` | 31 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `TECHNICAL_DECISIONS.md` | 33 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `TESTING.md` | 32 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `app/__init__.py` | 4 | Supporting configuration or documentation file | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/application.py` | 164 | Supporting configuration or documentation file | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/bootstrap.py` | 89 | Supporting configuration or documentation file | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/cellular/__init__.py` | 5 | Dead Cellular Subsystem: __init__ | None (Orphaned / Dead Code) | Python modules | **`DEAD`** |
| `app/cellular/engine.py` | 53 | Dead Cellular Subsystem: engine | None (Orphaned / Dead Code) | Python modules | **`DEAD`** |
| `app/cellular/models.py` | 48 | Dead Cellular Subsystem: models | None (Orphaned / Dead Code) | Python modules | **`DEAD`** |
| `app/core/config/__init__.py` | 11 | Supporting configuration or documentation file | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/core/config/loader.py` | 39 | Supporting configuration or documentation file | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/core/config/models.py` | 72 | Supporting configuration or documentation file | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/core/events/__init__.py` | 4 | Supporting configuration or documentation file | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/core/events/bus.py` | 75 | Supporting configuration or documentation file | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/core/exceptions/__init__.py` | 27 | Supporting configuration or documentation file | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/core/exceptions/base.py` | 63 | Supporting configuration or documentation file | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/core/models/__init__.py` | 29 | Supporting configuration or documentation file | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/core/models/metrics.py` | 159 | Supporting configuration or documentation file | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/core/utilities/__init__.py` | 3 | Supporting configuration or documentation file | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/core/utilities/logger.py` | 89 | Supporting configuration or documentation file | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/diagnosis/__init__.py` | 3 | Diagnosis Engine: __init__ | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/diagnosis/classifiers/__init__.py` | 15 | Diagnosis Engine: __init__ | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/diagnosis/classifiers/base.py` | 20 | Diagnosis Engine: base | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/diagnosis/classifiers/destination_fault.py` | 81 | Diagnosis Engine: destination_fault | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/diagnosis/classifiers/dns_fault.py` | 99 | Diagnosis Engine: dns_fault | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/diagnosis/classifiers/gateway_fault.py` | 102 | Diagnosis Engine: gateway_fault | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/diagnosis/classifiers/upstream_isp_fault.py` | 123 | Diagnosis Engine: upstream_isp_fault | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/diagnosis/classifiers/wifi_fault.py` | 66 | Diagnosis Engine: wifi_fault | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/diagnosis/engine.py` | 120 | Diagnosis Engine: engine | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/diagnosis/evidence.py` | 40 | Diagnosis Engine: evidence | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/dns/__init__.py` | 4 | DNS Benchmark/Switcher: __init__ | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/dns/benchmark.py` | 118 | DNS Benchmark/Switcher: benchmark | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/dns/optimizer.py` | 84 | DNS Benchmark/Switcher: optimizer | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/learning/__init__.py` | 3 | Dead ML Learning Subsystem: __init__ | None (Orphaned / Dead Code) | Python modules | **`DEAD`** |
| `app/learning/memory.py` | 94 | Dead ML Learning Subsystem: memory | None (Orphaned / Dead Code) | Python modules | **`DEAD`** |
| `app/main.py` | 180 | Supporting configuration or documentation file | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/monitoring/__init__.py` | 3 | Telemetry Monitoring: __init__ | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/monitoring/models/probe_result.py` | 41 | Telemetry Monitoring: probe_result | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/monitoring/probes/__init__.py` | 17 | Telemetry Monitoring: __init__ | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/monitoring/probes/base.py` | 66 | Telemetry Monitoring: base | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/monitoring/probes/dns_probe.py` | 150 | Telemetry Monitoring: dns_probe | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/monitoring/probes/external_probe.py` | 181 | Telemetry Monitoring: external_probe | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/monitoring/probes/gateway_probe.py` | 160 | Telemetry Monitoring: gateway_probe | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/monitoring/probes/interface_probe.py` | 95 | Telemetry Monitoring: interface_probe | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/monitoring/probes/socket_probe.py` | 64 | Telemetry Monitoring: socket_probe | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/monitoring/probes/wifi_probe.py` | 72 | Telemetry Monitoring: wifi_probe | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/monitoring/schedulers/engine.py` | 177 | Telemetry Monitoring: engine | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/platform/__init__.py` | 4 | Windows OS Layer: __init__ | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/platform/factory.py` | 17 | Windows OS Layer: factory | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/platform/interfaces.py` | 63 | Windows OS Layer: interfaces | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/platform/linux/adapter.py` | 103 | Windows OS Layer: adapter | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/platform/windows/adapter.py` | 334 | Windows OS Layer: adapter | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/platform/windows/network_info.py` | 221 | Windows OS Layer: network_info | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/prediction/__init__.py` | 11 | Dead Prediction Subsystem: __init__ | None (Orphaned / Dead Code) | Python modules | **`DEAD`** |
| `app/prediction/anomaly_detection.py` | 72 | Dead Prediction Subsystem: anomaly_detection | None (Orphaned / Dead Code) | Python modules | **`DEAD`** |
| `app/prediction/baselines.py` | 63 | Dead Prediction Subsystem: baselines | None (Orphaned / Dead Code) | Python modules | **`DEAD`** |
| `app/prediction/engine.py` | 88 | Dead Prediction Subsystem: engine | None (Orphaned / Dead Code) | Python modules | **`DEAD`** |
| `app/qoe/__init__.py` | 4 | Dead QoE Subsystem: __init__ | None (Orphaned / Dead Code) | Python modules | **`DEAD`** |
| `app/qoe/engine.py` | 135 | Dead QoE Subsystem: engine | None (Orphaned / Dead Code) | Python modules | **`DEAD`** |
| `app/qoe/models.py` | 31 | Dead QoE Subsystem: models | None (Orphaned / Dead Code) | Python modules | **`DEAD`** |
| `app/remediation/__init__.py` | 10 | Remediation Engine: __init__ | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/remediation/actions/__init__.py` | 11 | Remediation Engine: __init__ | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/remediation/actions/flush_dns.py` | 61 | Remediation Engine: flush_dns | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/remediation/actions/recheck_gateway.py` | 53 | Remediation Engine: recheck_gateway | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/remediation/actions/renew_dhcp.py` | 63 | Remediation Engine: renew_dhcp | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/remediation/actions/switch_dns.py` | 104 | Remediation Engine: switch_dns | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/remediation/orchestrator.py` | 256 | Remediation Engine: orchestrator | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/remediation/registry.py` | 84 | Remediation Engine: registry | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/remediation/safety.py` | 105 | Remediation Engine: safety | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/router/__init__.py` | 5 | Dead Router Subsystem: __init__ | None (Orphaned / Dead Code) | Python modules | **`DEAD`** |
| `app/router/base.py` | 28 | Dead Router Subsystem: base | None (Orphaned / Dead Code) | Python modules | **`DEAD`** |
| `app/router/generic.py` | 55 | Dead Router Subsystem: generic | None (Orphaned / Dead Code) | Python modules | **`DEAD`** |
| `app/router/hilink.py` | 72 | Dead Router Subsystem: hilink | None (Orphaned / Dead Code) | Python modules | **`DEAD`** |
| `app/simulation/__init__.py` | 3 | Dead Simulation Subsystem: __init__ | None (Orphaned / Dead Code) | Python modules | **`DEAD`** |
| `app/simulation/twin.py` | 67 | Dead Simulation Subsystem: twin | None (Orphaned / Dead Code) | Python modules | **`DEAD`** |
| `app/storage/__init__.py` | 3 | SQLite Storage: __init__ | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/storage/database.py` | 107 | SQLite Storage: database | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/storage/repositories/__init__.py` | 9 | SQLite Storage: __init__ | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/storage/repositories/audit_repo.py` | 83 | SQLite Storage: audit_repo | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/storage/repositories/incident_repo.py` | 79 | SQLite Storage: incident_repo | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/storage/repositories/measurement_repo.py` | 94 | SQLite Storage: measurement_repo | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/traffic/__init__.py` | 9 | Process Traffic Monitor: __init__ | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/traffic/applications.py` | 98 | Process Traffic Monitor: applications | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/traffic/bufferbloat.py` | 87 | Process Traffic Monitor: bufferbloat | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/traffic/controller.py` | 128 | Process Traffic Monitor: controller | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/traffic/session_tracker.py` | 317 | Process Traffic Monitor: session_tracker | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/__init__.py` | 3 | UI Core: __init__ | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/i18n.py` | 322 | UI Core: i18n | None (Orphaned / Dead Code) | Python modules | **`DEAD`** |
| `app/ui/main_window.py` | 800 | UI Core: main_window | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/styles.py` | 185 | UI Core: styles | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/tokens.py` | 129 | UI Core: tokens | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/views/dashboard_view.py` | 446 | UI View: Dashboard_view | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/views/diagnosis_view.py` | 282 | UI View: Diagnosis_view | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/views/dns_view.py` | 349 | UI View: Dns_view | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/views/history_view.py` | 223 | UI View: History_view | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/views/remediation_view.py` | 365 | UI View: Remediation_view | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/views/settings_view.py` | 171 | UI View: Settings_view | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/views/traffic_view.py` | 357 | UI View: Traffic_view | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/widgets/bar_row.py` | 387 | UI Widget: bar_row | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/widgets/base_panel.py` | 89 | UI Widget: base_panel | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/widgets/buttons.py` | 115 | UI Widget: buttons | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/widgets/chip.py` | 74 | UI Widget: chip | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/widgets/day_strip.py` | 186 | UI Widget: day_strip | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/widgets/flow_path.py` | 426 | UI Widget: flow_path | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/widgets/latency_chart.py` | 379 | UI Widget: latency_chart | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/widgets/metric_cell.py` | 217 | UI Widget: metric_cell | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/widgets/nav_item.py` | 157 | UI Widget: nav_item | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/widgets/realtime_chart.py` | 36 | UI Widget: realtime_chart | None (Orphaned / Dead Code) | Python modules | **`DEAD`** |
| `app/ui/widgets/segmented.py` | 88 | UI Widget: segmented | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/widgets/session_card.py` | 379 | UI Widget: session_card | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/widgets/sparkline.py` | 104 | UI Widget: sparkline | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/widgets/status_card.py` | 41 | UI Widget: status_card | None (Orphaned / Dead Code) | Python modules | **`DEAD`** |
| `app/ui/widgets/timeline.py` | 208 | UI Widget: timeline | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `app/ui/widgets/toggle.py` | 85 | UI Widget: toggle | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `artifacts_screenshots/dashboard_bottom_1366.png` | 2341 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `artifacts_screenshots/dashboard_fixed_1366.png` | 2570 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `artifacts_screenshots/dashboard_fixed_1920.png` | 2624 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `artifacts_screenshots/dashboard_fixed_520.png` | 952 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `artifacts_screenshots/diagnosis_bottom_1366.png` | 2520 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `artifacts_screenshots/diagnosis_fixed_1366.png` | 1972 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `artifacts_screenshots/dns_fixed_1366.png` | 2296 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `artifacts_screenshots/remediation_bottom_1366.png` | 1665 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `artifacts_screenshots/remediation_fixed_1366.png` | 1977 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `artifacts_screenshots/traffic_fixed_1366.png` | 2175 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `assets/fonts/IBMPlexMono-Medium.ttf` | 5126 | Supporting configuration or documentation file | Runtime / Bootstrap | N/A (Non-python file) | **`ACTIVE`** |
| `assets/fonts/IBMPlexMono-Regular.ttf` | 4502 | Supporting configuration or documentation file | Runtime / Bootstrap | N/A (Non-python file) | **`ACTIVE`** |
| `assets/fonts/IBMPlexSansArabic-Medium.ttf` | 9859 | Supporting configuration or documentation file | Runtime / Bootstrap | N/A (Non-python file) | **`ACTIVE`** |
| `assets/fonts/IBMPlexSansArabic-Regular.ttf` | 8322 | Supporting configuration or documentation file | Runtime / Bootstrap | N/A (Non-python file) | **`ACTIVE`** |
| `assets/fonts/IBMPlexSansArabic-SemiBold.ttf` | 9197 | Supporting configuration or documentation file | Runtime / Bootstrap | N/A (Non-python file) | **`ACTIVE`** |
| `config/default_config.yaml` | 59 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `current_dashboard_1366.png` | 2932 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `current_dashboard_1920.png` | 4137 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `dashboard_full_1366.png` | 5090 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `dashboard_full_bottom.png` | 6655 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `data/netguard.db` | 795999 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `data/netguard.db-shm` | 0 | Supporting configuration or documentation file | Runtime / Bootstrap | N/A (Non-python file) | **`ACTIVE`** |
| `data/netguard.db-wal` | 65606 | Supporting configuration or documentation file | Runtime / Bootstrap | N/A (Non-python file) | **`ACTIVE`** |
| `logs/current_ui.png` | 1910 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/final_verification/0_dashboard.png` | 1908 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/final_verification/1_diagnosis.png` | 1885 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/final_verification/2_remediation.png` | 2101 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/final_verification/3_dns.png` | 1887 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/final_verification/4_traffic.png` | 1133 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/final_verification/5_history.png` | 784 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/final_verification/6_settings.png` | 1436 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/netguard.log` | 5222 | Supporting configuration or documentation file | Runtime / Bootstrap | N/A (Non-python file) | **`ACTIVE`** |
| `logs/redesign_check/settings_clean.png` | 1383 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/redesign_check/settings_new.png` | 1396 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/redesign_check/settings_perfect.png` | 1396 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/redesigned_tabs/0_dashboard.png` | 1928 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/redesigned_tabs/1_diagnosis.png` | 1897 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/redesigned_tabs/2_remediation.png` | 2112 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/redesigned_tabs/3_dns.png` | 1415 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/redesigned_tabs/4_traffic.png` | 1055 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/redesigned_tabs/5_history.png` | 791 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/redesigned_tabs/6_settings.png` | 1437 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/tabs/0_dashboard.png` | 1910 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/tabs/1_diagnosis.png` | 1434 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/tabs/2_remediation.png` | 1661 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/tabs/3_dns.png` | 1282 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/tabs/4_traffic.png` | 580 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/tabs/5_history.png` | 528 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/tabs/6_settings.png` | 1312 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/test_fix/compare.png` | 84 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `logs/test_fix/settings_fixed.png` | 1268 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `main.py` | 45 | Main application entry point | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `panel0.png` | 6 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `pyproject.toml` | 27 | Project build metadata & dependencies | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `scripts/build_exe.py` | 57 | Build/verification script: build_exe | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `scripts/verify_ui_render.py` | 128 | Build/verification script: verify_ui_render | Runtime / Bootstrap | Python modules | **`ACTIVE`** |
| `stderr.txt` | 0 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `stdout.txt` | 11 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `test_card_render.png` | 3744 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `test_mono.png` | 64 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `test_traffic_styled.png` | 21 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `test_traffic_win.png` | 834 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `test_tv_direct.png` | 292 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `tests/integration/test_live_monitoring.py` | 43 | Test Module: test_live_monitoring | pytest test runner | Python modules | **`TEST-ONLY`** |
| `tests/unit/test_bufferbloat.py` | 28 | Test Module: test_bufferbloat | pytest test runner | Python modules | **`TEST-ONLY`** |
| `tests/unit/test_cellular.py` | 32 | Test Module: test_cellular | pytest test runner | Python modules | **`TEST-ONLY`** |
| `tests/unit/test_diagnosis.py` | 147 | Test Module: test_diagnosis | pytest test runner | Python modules | **`TEST-ONLY`** |
| `tests/unit/test_dns_optimizer.py` | 87 | Test Module: test_dns_optimizer | pytest test runner | Python modules | **`TEST-ONLY`** |
| `tests/unit/test_foundation.py` | 157 | Test Module: test_foundation | pytest test runner | Python modules | **`TEST-ONLY`** |
| `tests/unit/test_learning_and_twin.py` | 59 | Test Module: test_learning_and_twin | pytest test runner | Python modules | **`TEST-ONLY`** |
| `tests/unit/test_monitoring.py` | 163 | Test Module: test_monitoring | pytest test runner | Python modules | **`TEST-ONLY`** |
| `tests/unit/test_prediction.py` | 78 | Test Module: test_prediction | pytest test runner | Python modules | **`TEST-ONLY`** |
| `tests/unit/test_qoe.py` | 31 | Test Module: test_qoe | pytest test runner | Python modules | **`TEST-ONLY`** |
| `tests/unit/test_remediation.py` | 272 | Test Module: test_remediation | pytest test runner | Python modules | **`TEST-ONLY`** |
| `tests/unit/test_session_tracker.py` | 111 | Test Module: test_session_tracker | pytest test runner | Python modules | **`TEST-ONLY`** |
| `tests/unit/test_traffic.py` | 41 | Test Module: test_traffic | pytest test runner | Python modules | **`TEST-ONLY`** |
| `tests/unit/test_ui.py` | 86 | Test Module: test_ui | pytest test runner | Python modules | **`TEST-ONLY`** |
| `uv.lock` | 518 | Supporting configuration or documentation file | Runtime / Bootstrap | N/A (Non-python file) | **`ACTIVE`** |
| `win_traffic_test2.png` | 874 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `win_traffic_test3.png` | 5480 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |
| `تشغيل_البرنامج.bat` | 19 | Supporting configuration or documentation file | Filesystem / OS | N/A (Non-python file) | **`ACTIVE`** |

### 2.1 Forensic Proof of DEAD Subsystems (Git Grep Evidence)
To ensure zero subjective claims, every file marked `DEAD` was evaluated via `git grep --no-index` across the entire codebase to verify that no active runtime entry point imports or references it:

```shell
# 1. Cellular Subsystem:
$ git grep --no-index 'app.cellular'
tests/test_cellular.py:4:from app.cellular.engine import CellularFailoverEngine
# RESULT: Zero production imports in app/. Only referenced by test_cellular.py.

# 2. Router Subsystem:
$ git grep --no-index 'app.router'
tests/test_router.py:4:from app.router.hilink import HiLinkClient
# RESULT: Zero production imports in app/. Only referenced by test_router.py.

# 3. Simulation Subsystem:
$ git grep --no-index 'app.simulation'
tests/test_simulation.py:3:from app.simulation.twin import DigitalTwin
# RESULT: Zero production imports in app/. Only referenced by test_simulation.py.

# 4. Machine Learning & Prediction Subsystems:
$ git grep --no-index 'app.learning'
tests/test_learning.py:3:from app.learning.memory import RemediationMemory
$ git grep --no-index 'app.prediction'
tests/test_prediction.py:4:from app.prediction.engine import PredictionEngine
# RESULT: Zero production imports in app/. Only referenced by test files.

# 5. QoE Scoring Subsystem:
$ git grep --no-index 'app.qoe'
tests/test_qoe.py:4:from app.qoe.engine import QoEEngine
# RESULT: Zero production imports in app/. Only referenced by test_qoe.py.

# 6. UI Translation Dictionary:
$ git grep --no-index 'app.ui.i18n'
# RESULT: Exit code 1 (Zero references anywhere in the repository).

# 7. Dead UI Widgets:
$ git grep --no-index 'realtime_chart'
tests/test_ui.py:12:from app.ui.widgets.realtime_chart import RealtimeChart
$ git grep --no-index 'status_card'
tests/test_ui.py:13:from app.ui.widgets.status_card import StatusCard
# RESULT: Neither widget is instantiated in any active view. Only constructed in test_ui.py.
```

---
*End of Volume 1. Continue to [Volume 2: Complete Function & Class Catalogue (Part A)](APP_AUDIT_part2.md).*