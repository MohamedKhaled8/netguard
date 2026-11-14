# NETGUARD AI

**Autonomous Predictive Network Intelligence & Self-Healing Desktop Platform**

Version: 2.0.0-alpha  
Target Environment: Windows 10/11 (with modular Linux architecture), Cellular 4G/5G, Broadband

---

## 1. Overview

NETGUARD AI is an autonomous network management, real-time observability, predictive diagnostics, and self-healing system. It continuously monitors physical and logical network characteristics, detects anomalies and degradation, pinpoints root causes, and executes safe, verified, policy-governed corrective actions without requiring constant user intervention.

### Core Capabilities
- **Multi-Vector Real-Time Observability**: Continuous probe engines for default gateway, multi-target ICMP/TCP reachability, DNS query timing/resolution, jitter, packet loss, bandwidth consumption, and cellular link indicators.
- **Root-Cause Diagnostic Engine**: Evidence-based probabilistic classifier distinguishing local host/NIC issues, Wi-Fi drops, router/gateway failures, cellular uplink congestion/signal fade, ISP outages, DNS resolver degradation, and destination-specific blockages.
- **Autonomous Remediation Orchestrator**: Policy-governed action registry with safety locks, cooldowns, transaction-like execution, post-remedy verification, and automated rollback upon regression.
- **Predictive Analytics & Baseline Modeling**: Time-series trend analysis, change-point detection, and statistical anomaly detection forecasting degradation before total failure.
- **Local-First & High-Security Operation**: Strict allowlist of safe commands, zero arbitrary command execution, no HTTPS interception, and local storage.

---

## 2. System Architecture

NETGUARD AI follows a modular, decoupled architecture:

```
[ Probes & Collectors ] ---> [ Observability Engine ]
                                     |
                                     v
                           [ Diagnostic Engine ] <---> [ Baseline & Predictive Models ]
                                     |
                                     v
                        [ Remediation Orchestrator ]
                         /           |            \
                   [Safety Locks] [Actions]  [Rollback/Verification]
                         \           |            /
                          v          v           v
                          [ Network Subsystems ]
                        (DNS, Adapter, QoS, Routes)
```

---

## 3. Mandatory Implementation Sequence

- [x] **Stage 0**: Environment & Project Foundation (Logging, Configuration, SQLite Storage, Event Bus, Core Abstractions)
- [ ] **Stage 1**: Real Network Observability Engine (Real probes, multi-target sampling, asynchronous collectors)
- [ ] **Stage 2**: Root-Cause Diagnostic Engine (Multi-evidence classification, confidence scoring)
- [ ] **Stage 3**: Autonomous Self-Healing Engine (Policy execution, verification, rollback, safety breakers)
- [ ] **Stage 4**: Predictive Failure Detection (Baselines, anomaly detection, early warning)
- [ ] **Stage 5**: Intelligent DNS Engine (Benchmark, continuous latency/reliability scoring, failover)
- [ ] **Stage 6**: Cellular Network Intelligence (Modem metrics, RSRP/RSRQ/SINR monitoring)
- [ ] **Stage 7**: Application-Aware Traffic Intelligence (Process-level socket bandwidth tracking)
- [ ] **Stage 8**: Bufferbloat & Congestion Management (Loaded vs. idle latency, queue health)
- [ ] **Stage 9**: Quality of Experience (QoE) Engine (Voice/Video, Gaming, Streaming scoring)
- [ ] **Stage 10**: Learning Engine & Network Memory (Case-based historical reasoning)
- [ ] **Stage 11**: Network Digital Twin (Simulation sandbox)
- [ ] **Stage 12**: Professional Desktop Interface (PySide6, PyQtGraph real-time charts)

---

## 4. Quick Start

### Prerequisites
- Python 3.12+
- `uv` package manager

### Installation
```powershell
# Sync virtual environment & dependencies
uv sync

# Run tests
uv run pytest -v

# Run NetGuard CLI / Core Engine
uv run python -m app.main
```

---

## 5. Documentation Map
- [Architecture Specifications](ARCHITECTURE.md)
- [Implementation Plan](IMPLEMENTATION_PLAN.md)
- [Development Guide](DEVELOPMENT.md)
- [Security Model & Safeguards](SECURITY.md)
- [Testing & Quality Gates](TESTING.md)
- [Technical Decisions Log](TECHNICAL_DECISIONS.md)
- [Known Limitations](KNOWN_LIMITATIONS.md)
- [Feature Status](FEATURE_STATUS.md)

