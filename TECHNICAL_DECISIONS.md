# NETGUARD AI — TECHNICAL DECISIONS LOG

## ADR-001: Technology Stack Selection
- **Context**: Need high-performance networking probes, cross-platform extensibility (Windows 10/11 initial, Linux future), rapid iteration, and responsive desktop UI.
- **Decision**: Python 3.12+ with `uv` package manager; `PySide6` (Qt 6) for desktop GUI; `pyqtgraph` for 60fps real-time metric plotting; `asyncio` for asynchronous probing; `sqlite3` for local persistence; `psutil` + native OS platform adapters for system interactions.
- **Consequences**: Fast startup, zero compilation overhead for core logic, clean type-checked codebase, high-performance UI rendering via Qt C++ bindings.

## ADR-002: Evidence-Based Probabilistic Diagnosis vs. Raw ML
- **Context**: Autonomous recovery requires explainable, deterministic decisions. Premature complex neural models lead to unpredictable actions on critical network adapters.
- **Decision**: Implement Stage 2 using an evidence-accumulator rule and Bayesian/probabilistic classifier. Machine learning models (Stage 4) are layered on top only for time-series forecasting and anomaly baselines once sufficient real telemetry is collected.
- **Consequences**: 100% auditable decisions, zero black-box hallucinations, full compliance with safety constraints.

## ADR-003: Transaction-Like Action Execution with Rollback
- **Context**: Network repairs (such as changing DNS servers) can leave the system in a disconnected state if the target resolver fails or is unreachable.
- **Decision**: All remediation actions must implement pre-snapshot state capture, execution, empirical post-verification, and an explicit rollback function. If post-verification fails or times out, rollback executes immediately.
- **Consequences**: Elimination of permanent misconfiguration caused by failed self-healing actions.

## ADR-004: Dual-Channel Network Observability (ICMP + TCP Connect)
- **Context**: Many corporate or cellular ISP firewalls deprioritize or block ICMP Echo Requests, causing false "Internet Down" reports.
- **Decision**: Implement ICMP probing alongside TCP SYN/Connect probes to port 80/443 on reliable targets (Cloudflare, Google, Quad9).
- **Consequences**: Prevents false positive outage diagnoses on networks that drop ICMP.

