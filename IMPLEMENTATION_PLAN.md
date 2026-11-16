# NETGUARD AI — IMPLEMENTATION PLAN

## Phase Overview

The project is structured according to the mandatory sequence set forth in the Master Engineering Directive:

```
Stage 0 (Foundations)
   ↓
Stage 1 (Observability Engine)
   ↓
Stage 2 (Root-Cause Diagnostic Engine)
   ↓
Stage 3 (Autonomous Self-Healing Core)
   ↓
Stage 4 (Predictive Failure Detection)
   ↓
Stage 5 (Intelligent DNS Engine)
   ↓
Stage 6 (Cellular Network Intelligence)
   ↓
Stage 7 (Application-Aware Traffic Intelligence)
   ↓
Stage 8 (Bufferbloat & Congestion Management)
   ↓
Stage 9 (Quality of Experience Engine)
   ↓
Stage 10 (Learning Engine & Network Memory)
   ↓
Stage 11 (Network Digital Twin)
   ↓
Stage 12 (Desktop Application & Modern UI)
```

---

## Detailed Milestones

### Milestone 0: Environment & Core Foundation (Stage 0)
- [x] Environment inspection: Windows 11, Python 3.12, Wi-Fi 192.168.1.3, Gateway 192.168.1.1.
- [x] Packaging and dependency setup with `uv` (`pyproject.toml`).
- [x] Core Config Engine (`app/core/config/` with YAML/Pydantic validation).
- [x] Structured Event Bus (`app/core/events/bus.py`).
- [x] Central Logging & Audit Subsystem (`app/core/utilities/logger.py`).
- [x] SQLite Storage Repository with WAL mode (`app/storage/`).
- [x] Platform Abstraction Layer interfaces (`app/platform/interfaces.py`).
- [x] Foundation unit tests (`tests/unit/test_foundation.py`).

### Milestone 1: Observability Engine (Stage 1)
- [x] ICMP Ping Probe with fallback to TCP SYN/connect.
- [x] Default Gateway Reachability & Latency Probe.
- [x] Multi-Target External Destination Probe (1.1.1.1, 8.8.8.8, 9.9.9.9, OpenDNS, local ISP target).
- [x] DNS Resolution & Latency Probe (A, AAAA, PTR across system and explicit resolvers).
- [x] Network Interface Bandwidth & Packet Stats Collector (`psutil`).
- [x] Sliding-window Jitter & Packet Loss Estimator.
- [x] Asynchronous Probe Scheduler with rate-limiting and jitter dampening.
- [x] Observability unit & mock integration tests (`tests/unit/test_monitoring.py`).

### Milestone 2: Diagnostic & Root-Cause Engine (Stage 2)
- [x] Evidence Vector Accumulator.
- [x] Differential Diagnostic Classifiers:
  - Local Interface / Physical Disconnect.
  - Gateway / Local Router Failure.
  - Upstream ISP / WAN Outage.
  - DNS Server Failure / Slowness.
  - Destination-Specific Blockage.
  - Severe Bufferbloat / Asymmetric Queue Saturation.
- [x] Probabilistic Confidence Scorer.
- [x] Diagnostic engine automated test suite (`tests/unit/test_diagnosis.py`).

### Milestone 3: Autonomous Self-Healing Engine (Stage 3)
- [x] Central Remediation Orchestrator.
- [x] Action Registry with metadata, preconditions, OS support, timeouts.
- [x] Low-Risk Remediation Actions:
  - `Action_FlushDNSCache`: Safe cache flush.
  - `Action_SwitchDNS`: Switch to verified healthy backup resolver.
  - `Action_RestoreDNS`: Rollback DNS to initial configuration.
  - `Action_RenewIPLease`: DHCP release/renew.
- [x] Controlled & Disruptive Recovery Guards.
- [x] Circuit Breakers, Action Locks, and Cooldown Managers.
- [x] Verification Engine (Post-action measurement delta test).
- [x] Automated Rollback Handler.
- [x] Self-Healing integration test suite with synthetic failure injections (`tests/unit/test_remediation.py`).

### Milestone 4-12: Advanced Intelligence & UI
- [x] Stage 4: Dynamic Baselines & Changepoint Anomaly Detection.
- [x] Stage 5: DNS Benchmark & Failover Subsystem.
- [x] Stage 6: Modular Cellular Diagnostic Interface.
- [x] Stage 7: Process Socket Monitor, Traffic Policy Engine & Meeting Guard.
- [x] Stage 8: Idle vs. Loaded Latency & Bufferbloat Evaluator.
- [x] Stage 9: QoE Evaluator (Voice/Video, Gaming, Streaming).
- [x] Stage 10: Local Network Memory (Incident & Resolution store).
- [x] Stage 11: Network Digital Twin (Simulation sandbox).
- [x] Stage 12: PySide6 Desktop GUI with 100% reference design reproduction & responsive reflow.

