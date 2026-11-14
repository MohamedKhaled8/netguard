# NETGUARD AI — DEVELOPMENT GUIDE

## 1. Development Environment Setup

### Toolchain
- **OS**: Windows 10/11 (Primary Target) or Linux
- **Python**: 3.12+ 64-bit
- **Virtual Environment & Package Manager**: `uv`

### Initial Bootstrap
```powershell
# Clone or open repository
cd "e:\Mt FlutterProject\netguard"

# Sync dependencies
uv sync

# Verify Python environment
uv run python --version
```

---

## 2. Coding Standards & Conventions

1. **Type Annotations**: All core interfaces, functions, and models must include full Python type hints (`mypy` compatible).
2. **Immutability & Data Models**: Use `pydantic.BaseModel` or `@dataclass(frozen=True)` for domain events, measurements, and configurations.
3. **Error Handling**: Custom hierarchy anchored at `NetGuardError`. Catch specific exceptions; never use bare `except: pass`.
4. **Asynchronous Discipline**: Use `asyncio` for non-blocking I/O. Background worker threads must use bounded queues and graceful cancellation via `asyncio.Event` / `threading.Event`.
5. **Logging**: All logs use the structured logging system (`app/core/utilities/logger.py`) emitting timestamp, module, level, and structured metadata.

---

## 3. Running Tests

```powershell
# Run all unit tests
uv run pytest tests/unit -v

# Run with coverage report
uv run pytest --cov=app tests/

# Run integration tests (using mocks and virtual loopbacks)
uv run pytest tests/integration -v
```

---

## 4. Directory Layout

```
app/
├── core/           # Config, logging, events, exceptions, base models
├── monitoring/     # Probes (ICMP, TCP, DNS), collectors (psutil), scheduler
├── diagnosis/      # Multi-vector evidence classifiers, root cause engine
├── remediation/    # Action registry, circuit breakers, rollback, orchestrator
├── prediction/     # Baselines, anomaly detection, forecasting
├── traffic/        # Socket & process bandwidth tracking, QoS
├── dns/            # Intelligent resolver scoring & failover
├── cellular/       # Modem / router metric collector
├── qoe/            # Video, gaming, streaming quality estimators
├── learning/       # Case-based incident memory
├── simulation/     # Digital twin sandbox
├── platform/       # Windows / Linux OS abstraction adapters
├── storage/        # SQLite repositories & migrations
└── ui/             # PySide6 desktop interface
```
