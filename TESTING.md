# NETGUARD AI — TESTING STRATEGY & QUALITY GATES

## 1. Test Strategy Overview

NetGuard AI follows a strict empirical verification strategy. No claims of completion or correctness are accepted without passing unit and integration tests.

Because networking code interacts with external hardware and operating system state, our testing architecture enforces:
1. **Isolated Unit Tests**: All platform APIs, subprocess calls, and network sockets are mockable through interfaces (`IPlatformAdapter`, `IProbeEngine`).
2. **Deterministic Network Simulation**: Inject synthetic packet loss, high jitter, DNS timeouts, and gateway unreachability into the telemetry stream to verify diagnostic and self-healing logic without disrupting the host machine.
3. **Integration Verification**: Verify that the entire loop (`Probe -> Anomaly -> Diagnosis -> Remediation -> Verification -> Rollback`) operates deterministically.

---

## 2. Test Matrix

| Test Suite | Purpose | Execution Command |
| :--- | :--- | :--- |
| `tests/unit/test_foundation.py` | Config loading, Event bus, SQLite storage, Logger | `uv run pytest tests/unit/test_foundation.py` |
| `tests/unit/test_monitoring.py` | Probes, rate limiting, metric normalization | `uv run pytest tests/unit/test_monitoring.py` |
| `tests/unit/test_diagnosis.py` | Root-cause classification under simulated faults | `uv run pytest tests/unit/test_diagnosis.py` |
| `tests/unit/test_remediation.py` | Action registry, verification, rollback, breakers | `uv run pytest tests/unit/test_remediation.py` |
| `tests/unit/test_platform.py` | Platform abstraction adapters (Windows & Linux) | `uv run pytest tests/unit/test_platform.py` |

---

## 3. Mandatory Quality Gates

- **Gate 0 (Foundation)**: All configuration classes parse valid & invalid YAML; SQLite creates WAL database and runs migrations; EventBus dispatches typed events; tests exit 0.
- **Gate 1 (Monitoring)**: Live and mocked probes generate valid `Measurement` instances; probe rate-limiter prevents network flooding; gateway and internet targets are measured independently.
- **Gate 2 (Diagnosis)**: Classifiers accurately identify simulated DNS failures, gateway unreachability, and upstream ISP outages with confidence > 0.80; ambiguous conditions produce uncertainty scores rather than false certainty.
- **Gate 3 (Self-Healing)**: Low-risk actions execute and verify; synthetic regression triggers automatic rollback; repeated failures trip circuit breakers.
