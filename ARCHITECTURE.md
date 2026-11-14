# NETGUARD AI — SYSTEM ARCHITECTURE

## 1. Architectural Principles

NETGUARD AI is structured around six core design principles:

1. **Strict Separation of Concerns**: Monitoring only observes; Diagnostics only reasons and assesses; Remediation only acts under policy; Models only learn and predict.
2. **Empirical Grounding**: No metric is simulated; unavailable data is marked `STATUS_UNAVAILABLE`. Diagnoses require multi-point corroborating evidence.
3. **Fail-Safe & Reversible Operations**: Any autonomous action must be non-destructive by default, verified via post-execution telemetry, and automatically rolled back if performance degrades.
4. **Local-First & Privacy-Preserving**: No telemetry leaks outside the local system. No deep packet content or credential inspection.
5. **Asynchronous Non-Blocking Execution**: Real-time probes and heavy analyses run in dedicated asynchronous workers or threads, keeping UI and monitoring isolated from lockups.
6. **Platform Abstraction**: OS-specific operations (Windows WMI/Netsh/IPHelper vs. Linux iproute2/sysfs/ethtool) are strictly isolated behind platform abstraction interfaces.

---

## 2. Component Diagram

```
+-------------------------------------------------------------------------+
|                              Application Core                            |
|  [Event Bus]  [Configuration]  [Structured Logger]  [SQLite Store]      |
+-------------------------------------------------------------------------+
       |                                                 ^
       v                                                 |
+-------------------------------------------------------------------------+
|                    Stage 1: Observability Engine                        |
|  - GatewayReachabilityProbe (ICMP/ARP)                                  |
|  - ExternalConnectivityProbe (Multi-target ICMP/TCP)                    |
|  - DNSLatencyProbe (dnspython resolution timing)                       |
|  - InterfaceStatsCollector (psutil network counters)                    |
|  - ThroughputEstimator (Sliding window rate)                            |
|  - ActiveConnectionCollector (Socket & process attribution)             |
+-------------------------------------------------------------------------+
       | Telemetry Stream
       v
+-------------------------------------------------------------------------+
|                    Stage 2: Root Cause Diagnostic Engine                |
|  - Evidence Accumulator                                                 |
|  - Diagnostic Classifiers:                                              |
|      * LocalHostFaultClassifier                                         |
|      * GatewayUnreachableClassifier                                     |
|      * UpstreamISPOutageClassifier                                      |
|      * DNSDegradationClassifier                                         |
|      * DestinationSpecificClassifier                                    |
|      * BufferbloatCongestionClassifier                                  |
|  - Confidence & Severity Scorer                                         |
+-------------------------------------------------------------------------+
       | Diagnosis (with evidence & confidence)
       v
+-------------------------------------------------------------------------+
|                    Stage 3: Autonomous Self-Healing Engine               |
|  - Action Registry (preconditions, OS gates, rollback handlers)         |
|  - Remediation Policy Engine (Observation / Assisted / Autonomous)      |
|  - Circuit Breakers & Cooldown Locks                                    |
|  - Transaction Executor & Rollback Manager                              |
|  - Verification Engine (Delta-comparison vs baseline)                   |
+-------------------------------------------------------------------------+
       | Status & Metrics
       v
+-------------------------------------------------------------------------+
|                  Stage 4-11: Advanced Intelligence Layers               |
|  - Time-series Baselines & Change-Point Anomaly Detector                |
|  - Intelligent DNS Optimizer                                            |
|  - Cellular Diagnostics Subsystem                                       |
|  - Quality of Experience (QoE) Engine                                   |
|  - Network Memory & Case-Based Experience Store                          |
+-------------------------------------------------------------------------+
       | State Signals
       v
+-------------------------------------------------------------------------+
|                    Stage 12: Desktop Presentation (PySide6)             |
|  - Dark Mode Modern Ergonomics                                          |
|  - PyQtGraph High-Frame-Rate Telemetry Viewers                          |
|  - Incident Timeline & Action Audit Log Viewers                         |
+-------------------------------------------------------------------------+
```

---

## 3. Data Flow and Event Model

1. **Probe Tick**: `Scheduler` triggers asynchronous probe jobs according to configured intervals (e.g. 1s for gateway, 3s for external, 10s for DNS).
2. **Telemetry Normalization**: Probes produce `Measurement` objects (Timestamp, Target, MetricType, RawValue, NormalizedValue, Status, Confidence).
3. **Event Publication**: Normalized measurements publish to `EventBus` topic `telemetry.*` and persist to SQLite repository.
4. **Diagnostic Evaluation**: `DiagnosisEngine` evaluates sliding window of measurements across multiple vectors.
5. **Incident Generation**: If an anomaly is identified with confidence exceeding threshold, an `Incident` is generated with `ProbableCause`, `EvidenceVector`, `Severity`, and `CandidateActions`.
6. **Remediation Execution**: If system is in `AutonomousSafeMode`, `RemediationOrchestrator` validates action preconditions, checks circuit breakers, executes recovery action, runs post-verification probe, and commits or rolls back.

---

## 4. Platform Abstraction Layer (PAL)

All OS-specific interactions reside under `app/platform/`:
- `IPlatformAdapter` interface:
  - `get_default_gateway() -> Optional[GatewayInfo]`
  - `get_interface_metrics() -> List[InterfaceMetric]`
  - `flush_dns_cache() -> ExecutionResult`
  - `set_dns_servers(interface_name, servers) -> ExecutionResult`
  - `reset_adapter(interface_name) -> ExecutionResult`
  - `get_wifi_metrics() -> Optional[WifiMetrics]`
  - `get_active_sockets() -> List[SocketProcessInfo]`
- `WindowsPlatformAdapter`: Uses `ctypes`, `subprocess` (strictly allowlisted PowerShell/Netsh commands with sanitized parameters), and `wmi`/IPHelper APIs.
- `LinuxPlatformAdapter`: Uses `/proc/net`, `/sys/class/net`, and `ip` commands.

---

## 5. Storage Architecture

SQLite database located at `data/netguard.db` with WAL (Write-Ahead Logging) mode enabled:
- `measurements`: Raw telemetry samples.
- `incidents`: Diagnosed issues and root causes.
- `actions_audit`: Record of all automated or manual remediation actions taken, pre/post metrics, and rollback status.
- `baselines`: Metric distributions across time-of-day / day-of-week buckets.
- `dns_benchmarks`: Resolver latency, jitter, and error rates.

