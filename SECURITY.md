# NETGUARD AI — SECURITY ARCHITECTURE & SAFEGUARDS

## 1. Security Philosophy

NETGUARD AI manages critical networking state on desktop operating systems. As such, it operates under strict least-privilege, defensive-engineering, and zero-trust policies:

1. **Local-First Processing**: Telemetry, performance history, and configuration data remain strictly on the host system. No outbound telemetry or cloud dependencies.
2. **Strict Command Allowlisting**: The autonomous engine is prohibited from executing arbitrary commands, shell strings, or unvalidated parameters. All system commands are hardcoded in registered, auditable action definitions.
3. **Privilege Separation**: Actions requiring administrator/root privileges (e.g., DNS reconfiguration, adapter reset) are isolated, strictly audited, and guarded by explicit user authorization policies.
4. **No Deep Packet Content Inspection (No TLS/HTTPS Interception)**: NetGuard does not install root certificates, inspect payload bytes, or intercept encrypted application sessions. It monitors metadata only (packet counts, socket states, round-trip times).
5. **Circuit Breakers & Emergency Stop**: If an automated action produces unexpected performance regression or fails verification, execution is halted, state is rolled back, and a cooldown lock is engaged.
6. **Immutable Audit Trail**: Every executed action (timestamp, trigger, command, parameters, pre-state, post-state, verification result) is logged to the persistent SQLite audit store.

---

## 2. Risk Classification System

| Level | Risk Category | Example Actions | Autonomous Policy |
| :--- | :--- | :--- | :--- |
| **Level 1** | Low Risk / Non-Disruptive | Flush DNS Cache, Re-run diagnostic probe, Validate resolver | Permitted automatically in Autonomous Safe Mode |
| **Level 2** | Controlled / Reversible | Switch DNS to verified healthy resolver, Release/Renew DHCP | Permitted with pre-condition verification and automatic rollback |
| **Level 3** | High Risk / Disruptive | Reset network adapter, Restart network stack service | Strictly prohibited during active meetings/calls; requires explicit policy |

---

## 3. Subprocess & Input Sanitization Rules

- Never pass unvalidated user or network inputs to shell interpreters (`shell=False` mandatory for all `subprocess` invocations).
- Network interface names and IP addresses are parsed and strictly validated using standard library `ipaddress` and regex anchors before being passed to platform APIs.
- Execution timeouts are enforced on all system subprocesses to prevent zombie hangs.

