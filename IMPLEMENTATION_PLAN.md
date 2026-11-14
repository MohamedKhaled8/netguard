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
- [ ] Core Config Engine (`app/core/config/` with YAML/Pydantic validation).
- [ ] Structured Event Bus (`app/core/events/bus.py`).
- [ ] Central Logging & Audit Subsystem (`app/core/utilities/logger.py`).
- [ ] SQLite Storage Repository with WAL mode (`app/storage/`).
- [ ] Platform Abstraction Layer interfaces (`app/platform/interfaces.py`).
- [ ] Foundation unit tests (`tests/unit/test_foundation.py`).

### Milestone 1: Observability Engine (Stage 1)
- [ ] ICMP Ping Probe with fallback to TCP SYN/connect.
- [ ] Default Gateway Reachability & Latency Probe.
- [ ] Multi-Target External Destination Probe (1.1.1.1, 8.8.8.8, 9.9.9.9, OpenDNS, local ISP target).
- [ ] DNS Resolution & Latency Probe (A, AAAA, PTR across system and explicit resolvers).
- [ ] Network Interface Bandwidth & Packet Stats Collector (`psutil`).
- [ ] Sliding-window Jitter & Packet Loss Estimator.
- [ ] Asynchronous Probe Scheduler with rate-limiting and jitter dampening.
- [ ] Observability unit & mock integration tests (`tests/unit/test_monitoring.py`).

### Milestone 2: Diagnostic & Root-Cause Engine (Stage 2)
- [ ] Evidence Vector Accumulator.
- [ ] Differential Diagnostic Classifiers:
  - Local Interface / Physical Disconnect.
  - Gateway / Local Router Failure.
  - Upstream ISP / WAN Outage.
  - DNS Server Failure / Slowness.
  - Destination-Specific Blockage.
  - Severe Bufferbloat / Asymmetric Queue Saturation.
- [ ] Probabilistic Confidence Scorer.
- [ ] Diagnostic engine automated test suite (`tests/unit/test_diagnosis.py`).

### Milestone 3: Autonomous Self-Healing Engine (Stage 3)
- [ ] Central Remediation Orchestrator.
- [ ] Action Registry with metadata, preconditions, OS support, timeouts.
- [ ] Low-Risk Remediation Actions:
  - `Action_FlushDNSCache`: Safe cache flush.
  - `Action_SwitchDNS`: Switch to verified healthy backup resolver.
  - `Action_RestoreDNS`: Rollback DNS to initial configuration.
  - `Action_RenewIPLease`: DHCP release/renew.
- [ ] Controlled & Disruptive Recovery Guards.
- [ ] Circuit Breakers, Action Locks, and Cooldown Managers.
- [ ] Verification Engine (Post-action measurement delta test).
- [ ] Automated Rollback Handler.
- [ ] Self-Healing integration test suite with synthetic failure injections (`tests/unit/test_remediation.py`).

### Milestone 4-12: Advanced Intelligence & UI
- [ ] Stage 4: Dynamic Baselines & Changepoint Anomaly Detection.
- [ ] Stage 5: DNS Benchmark & Failover Subsystem.
- [ ] Stage 6: Modular Cellular Diagnostic Interface.
- [ ] Stage 7: Process Socket Monitor & Traffic Policy Engine.
- [ ] Stage 8: Idle vs. Loaded Latency & Bufferbloat Evaluator.
- [ ] Stage 9: QoE Evaluator (Voice/Video, Gaming, Streaming).
- [ ] Stage 10: Local Network Memory (Incident & Resolution store).
- [ ] Stage 11: Network Digital Twin (Simulation sandbox).
- [ ] Stage 12: PySide6 Desktop GUI with Real-Time PyQtGraph streaming.

