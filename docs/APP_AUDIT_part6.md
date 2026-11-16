# NetGuard AI — Volume 6: External Commands & Test Suite Audit

> **Audit Target:** NetGuard AI (Windows Autonomous Network Remediation & Telemetry Dashboard)  
> **Document:** Volume 6 of 7 | Sections 8 & 9  
> **Status:** Complete & Verified (READ-ONLY Analysis — Zero Source Changes)  

---

## 8. External Commands, OS Calls and Network Calls

This section catalogues every subprocess invocation, Windows command, netsh/PowerShell call, socket query, and psutil telemetry poll in the repository.

| Command / API Invocation | Location (File:Line) | Invocation Mechanism | Timeout | Output Parsing | Non-Zero Exit & Failure Handling | Admin Elevation? | Blocks UI Thread? | Locale Dependency |
| :--- | :--- | :--- | :---: | :--- | :--- | :---: | :---: | :---: |
| `route print 0.0.0.0` | `app/platform/windows/adapter.py:51` | subprocess.run | 3.0s | Splits stdout lines, finds line starting with 0.0.0.0 0.0.0.0, takes parts[2] as gateway and validates with ipaddress.IPv4Address | Swallows exception, falls back to psutil / cached gateway | **No** | **Yes if called synchronously; adapter calls run_in_executor in background loops, but initial probe blocks caller** | Assumes IPv4 format, splits whitespace. Works across Windows locales |
| `route print 0.0.0.0` | `app/platform/windows/adapter.py:83` | subprocess.run | 3.0s | Splits stdout lines, takes parts[3] as interface IP, matches to psutil.net_if_addrs() | Falls back to first non-loopback interface in psutil.net_if_stats() | **No** | **Yes if called synchronously; fallback exists** | Assumes standard route print columns (first 2 parts == 0.0.0.0) |
| `ping -n 1 -w <timeout_ms> <target>` | `app/platform/windows/adapter.py:124` | subprocess.run | timeout_sec + 1.0s (default 2.5s) | Regex r"time[=<]([0-9]+)ms" on stdout. If matches, returns float; else fallback to wall-clock duration_ms | Returns (False, 0.0). Swallows TimeoutExpired and Exception | **No** | **No in probes (run_in_executor); Yes if called directly on UI thread** | English regex: searches for "time=" or "time<". On Arabic Windows where output may say "الوقت=" or "temps=" it fails regex and falls back to wall-clock time |
| `socket.connect((target, port))` | `app/platform/windows/adapter.py:150` | Python native socket.connect | 2.0s | Measures time.perf_counter() elapsed for 3-way handshake | Catches Exception, returns (False, 0.0), always closes socket in finally | **No** | **No in probes (run_in_executor)** | None (native socket API) |
| `ctypes.windll.dnsapi.DnsFlushResolverCache()` | `app/platform/windows/adapter.py:163` | Win32 Native C API Call | Immediate (non-blocking syscall) | Returns 1 on success | Falls back to PowerShell Clear-DnsClientCache, then ipconfig /flushdns | **No (DnsFlushResolverCache is callable by normal user on Windows 10/11)** | **No (very fast C call, <5ms)** | None (binary API) |
| `powershell -NoProfile -Command Clear-DnsClientCache` | `app/platform/windows/adapter.py:172` | subprocess.run (PowerShell) | 5.0s | Checks returncode == 0 | Falls through to ipconfig /flushdns | **No** | **Slow (PowerShell cold start ~1.5s). Runs inside thread worker** | None |
| `ipconfig /flushdns` | `app/platform/windows/adapter.py:187` | subprocess.run | 5.0s | Checks returncode == 0, returns (True, message) or (False, stderr/stdout) | Returns (False, error) | **No** | **In worker thread** | None (relies on returncode) |
| `ipconfig /flushdns` | `app/ui/main_window.py:730` | subprocess.run | None (unbounded!) | check=True, capture_output=True. Swallows Exception silently (`except Exception: pass`) | Silently ignored! UI still shows "تم تفريغ كاش DNS بنجاح ✓" even if command failed! | **No** | **Runs inside daemon thread (`_worker`), but failure is masked** | None |
| `netsh interface ip show dns name=<interface_name>` | `app/platform/windows/adapter.py:204` | subprocess.run | 5.0s | Regex r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b" on stdout lines to find IP addresses | Returns empty list `[]` | **No** | **In worker thread** | Extracts IPv4 regex, insensitive to label language |
| `netsh interface ip set dns name=<interface_name> source=dhcp` | `app/platform/windows/adapter.py:227` | subprocess.run | 8.0s | Checks returncode == 0 | Returns (False, stderr/stdout) | **Yes (Requires Administrator privileges)** | **In worker thread** | None |
| `netsh interface ip set dns name=<interface_name> static <primary> primary` | `app/platform/windows/adapter.py:242` | subprocess.run | 8.0s | Checks returncode == 0. If failed, inspects stdout/stderr for "elevation", "administrator", "access is denied" | Returns (False, "Requires Administrator privileges...") | **Yes (Requires Administrator privileges)** | **In worker thread** | English string check: If Windows is Arabic ("تم رفض الوصول" / "حقوق المسؤول"), the specific message check fails and returns raw stderr |
| `netsh interface ip add dns name=<interface_name> <secondary> index=<idx>` | `app/platform/windows/adapter.py:257` | subprocess.run | 5.0s | Executes in a loop for subsequent DNS IPs. Ignores returncode! | Return code and errors are completely ignored! Always proceeds to return True! | **Yes (Requires Administrator privileges)** | **In worker thread** | None |
| `ipconfig /renew <interface_name>` | `app/platform/windows/adapter.py:277` | subprocess.run | 12.0s | Checks is_elevated() first. Checks returncode == 0 | Returns (False, stderr or stdout) | **Yes (Requires Administrator privileges)** | **In worker thread** | None |
| `netsh wlan show interfaces` | `app/platform/windows/adapter.py:302` | subprocess.run | 4.0s | Parses line with ":" splitting: "Signal", "SSID", "BSSID", "Receive rate", "Transmit rate" | Swallows exception, returns empty dict with defaults | **No** | **Yes if called synchronously; in probe worker** | CRITICAL LOCALE DEFECT: Looks for English keywords "Signal", "SSID", "Receive rate". On Arabic Windows netsh outputs Arabic keys ("الإشارة", "معدل الاستلام"), so parsing returns 0.0% signal! |
| `netsh wlan show interfaces` | `app/platform/windows/network_info.py:24` | subprocess.check_output | None (unbounded!) | Regex r"^\s*SSID\s*:\s*(.+)$", "Band", "Signal", "Description" | Catches Exception, returns hardcoded fallback dict: Wi-Fi المنزلية, 5 GHz, 85%, راوتر WEA3994B المنزلي | **No** | **In daemon thread in MainWindow._async_inspect_network_environment()** | English keywords: "SSID", "Band", "Signal", "Description". On non-English Windows, regex fails and returns hardcoded fake values! |
| `netsh wlan show profiles` | `app/platform/windows/network_info.py:43` | subprocess.check_output | None (unbounded!) | Regex r"All User Profile\s*:\s*(.+)" to extract saved Wi-Fi profiles | Swallows Exception silently (`except Exception: pass`) | **No** | **In daemon thread** | English regex "All User Profile". On Arabic Windows ("ملف تعريف كل المستخدمين") it finds 0 profiles and defaults to "راوتر WEA3994B المنزلي"! |
| `netsh interface ipv4 show dnsservers <interface_name>` | `app/platform/windows/network_info.py:95` | subprocess.check_output | None (unbounded!) | Regex r"\b(?:\d{1,3}\.){3}\d{1,3}\b" | Falls back to hardcoded `["10.60.66.196"]` | **No** | **In daemon thread** | Regex-based on IP addresses, locale-tolerant |
| `urllib.request.urlopen("https://ipinfo.io/json")` | `app/platform/windows/network_info.py:195` | HTTP GET request (Outbound Network) | 2.5s | json.loads(), extracts org, ip, city. Matches TE-AS, Orange, Vodafone, Etisalat | Falls back to hardcoded: IP 197.52.36.240, Cairo, Orange Egypt / Telecom Egypt | **No** | **In daemon thread; will fail if machine has no internet or blocks ipinfo.io** | None |
| `ctypes.windll.shell32.IsUserAnAdmin()` | `main.py:25, app/main.py:155, app/platform/windows/adapter.py:42` | Win32 Shell32 API | Immediate | Returns non-zero if user token has elevated admin SID | Catches Exception, returns False | **No** | **Immediate syscall** | None |
| `ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, args, None, 1)` | `main.py:35, app/main.py:158, app/platform/windows/adapter.py:33` | Win32 UAC Elevation API | Triggers OS UAC prompt | Return value > 32 indicates success (user clicked Yes on UAC) | Catches Exception, proceeds un-elevated | **Triggers UAC dialog for elevation** | **ShellExecuteW returns immediately; launches new process and current process calls sys.exit(0)** | None |
| `dns.resolver.Resolver().resolve(domain, "A")` | `app/dns/benchmark.py:73, app/monitoring/probes/dns_probe.py:47, app/remediation/actions/flush_dns.py:50, switch_dns.py:73` | UDP/TCP DNS Query (dnspython) | Configured 2.0s - 2.5s | Extracts A record IP strings, measures time delta | Catches dns.exception.DNSException, increments failure counter | **No** | **In thread pool / run_in_executor** | None |
| `psutil.net_connections(kind="inet")` | `app/traffic/controller.py:28` | psutil Windows API call (GetExtendedTcpTable/GetExtendedUdpTable) | Immediate OS table query | Extracts conn.pid, status == CONN_ESTABLISHED, raddr | Catches AccessDenied, NoSuchProcess on individual PIDs | **Partial (non-admin cannot see PIDs for system processes)** | **In run_in_executor** | None |
| `psutil.net_io_counters(pernic=True)` | `app/monitoring/probes/interface_probe.py:44` | psutil Windows API (GetIfTable2) | Immediate | Computes bytes_sent and bytes_recv delta divided by time delta | Catches Exception, records error | **No** | **In probe loop** | None |
| `PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA busy_timeout=5000` | `app/storage/database.py:85-88` | SQLite Database Engine Configuration | 5.0s busy timeout | Executes PRAGMA statements | Raises sqlite3.Error | **No (local file I/O)** | **Initializes on main thread at startup; queries run in worker threads or short transactions** | None |

### 8.1 Critical Vulnerability: Windows Locale Sensitivity (Arabic/French/German Windows)
- **Location:** `app/platform/windows/network.py:88-115`
- **Vulnerable Logic:**
```python
# app/platform/windows/network.py:102-108
signal_match = re.search(r'Signal\s*:\s*(\d+)%', output)
rate_match = re.search(r'Receive rate \(Mbps\)\s*:\s*([\d.]+)', output)
```
- **Failure Impact:** On non-English Windows operating systems (such as Arabic Windows 11 where the header is printed as `الإشارة : 85%`, or French where it is `Signal : 85%`), the regex fails completely. The function returns a default fallback `signal=0%` or raises an unhandled error, corrupting Wi-Fi signal reporting.

---

## 9. Tests Audit

The test suite consists of 14 test files executed via `pytest`. In a clean run, 47 tests pass in 8.27 seconds. However, forensic analysis of the test implementations reveals extensive mock shielding and severe coverage blind spots.

### 9.1 Test File Breakdown & Coverage Evaluation

| Test File | Lines | What it Exercises | Mocking Extent | What is NOT Covered | Reality / Flaw |
| :--- | :---: | :--- | :--- | :--- | :--- |
| `tests/integration/test_live_monitoring.py` | 55 | Real probe engine loop | Minimal (tests live gateway) | Error recovery during interface drop | Flaky if gateway is unreachable |
| `tests/unit/test_bufferbloat.py` | 42 | Grade calculation | None (pure math) | Integration with active dashboard | Pure unit test of math function |
| `tests/unit/test_cellular.py` | 38 | Cellular failover engine | Full (mocks modem) | Production execution | **DEAD SUBSYSTEM:** Not reachable in app |
| `tests/unit/test_diagnosis.py` | 215 | Rule evaluation heuristics | Synthetic measurement inputs | Unhandled exception states | Validates logic on clean dictionaries |
| `tests/unit/test_dns_optimizer.py` | 98 | DNS benchmark sorting | Mocks socket connection | Real adapter DNS rewrite | Mocks `set_dns_server` |
| `tests/unit/test_foundation.py` | 165 | EventBus & models | None (in-memory) | Multi-threaded race conditions | Basic unit test |
| `tests/unit/test_learning_and_twin.py` | 72 | Digital twin simulation | Full simulation | Production execution | **DEAD SUBSYSTEM:** Orphaned code |
| `tests/unit/test_monitoring.py` | 180 | Probes & measurement model | Mocks `subprocess.run` | Parsing on non-English locales | Mocks always return English output |
| `tests/unit/test_prediction.py` | 95 | Latency baseline prediction | Mocks numpy arrays | Production execution | **DEAD SUBSYSTEM:** Orphaned code |
| `tests/unit/test_qoe.py` | 35 | QoE score computation | Synthetic inputs | Production execution | **DEAD SUBSYSTEM:** Orphaned code |
| `tests/unit/test_remediation.py` | 290 | Orchestrator state transitions | Mocks all subprocess execution | Real elevation, UAC, rollback | **Zero actual commands run** |
| `tests/unit/test_session_tracker.py` | 130 | Meeting Guard tracking | Mocks psutil process list | Real QoS DSCP tagging | Asserts dummy boolean returns |
| `tests/unit/test_traffic.py` | 52 | Process table parsing | Mocks psutil counters | Real per-process byte deltas | High-level data parsing test |
| `tests/unit/test_ui.py` | 92 | Widget instantiation | Tests only `assert widget is not None` | User clicks, signals, data refresh | **Non-Proving Test:** Does not test behavior |

### 9.2 Passing Tests That Prove Nothing
1. **UI Instantiation Tests (`tests/unit/test_ui.py:25-85`):**
   - `test_main_window_creation`: Instantiates `MainWindow`, asserts `window.isVisible() is False`, then exits.
   - `test_status_card_creation`: Instantiates `StatusCard` (`app/ui/widgets/status_card.py`), a widget that is **completely dead and unimported** in production.
   - `test_realtime_chart_creation`: Instantiates `RealtimeChart`, another dead widget never used in any active view.
   - **Conclusion:** These tests prove only that Qt widgets can allocate memory in Python without syntax crashes. They test zero signal emissions, zero backend integrations, and zero paint events.
2. **QoS Priority Tests (`tests/unit/test_session_tracker.py:88-115`):**
   - Asserts `tracker.apply_qos_priority('zoom.exe') == True`.
   - As documented in Section 5.5, `apply_qos_priority` is a one-line dummy logging stub that always returns `True`. Passing this test proves nothing regarding real Windows packet prioritization.

### 9.3 Production Code with Zero Test Coverage
The following mission-critical components have **zero automated unit or integration tests**:
1. **`app/platform/windows/network.py`:** `restart_adapter()`, `flush_dns()`, `renew_ip()`, `is_admin()`, `get_wifi_signal()`.
2. **`app/platform/windows/registry.py`:** Registry query functions.
3. **`app/ui/views/dashboard.py`:** Metric tile updates, quick fix button click handlers.
4. **`app/ui/views/diagnosis.py`:** Deep scan simulation click handler.
5. **`app/ui/views/remediation.py`:** Mode change signals and policy toggles.
6. **`app/ui/views/settings.py`:** Settings application, combo box changes, and persistence logic.

---
*End of Volume 6. Continue to [Volume 7: Contradictions, Empirical Runtime Verification & Deliverables](APP_AUDIT_part7.md).*