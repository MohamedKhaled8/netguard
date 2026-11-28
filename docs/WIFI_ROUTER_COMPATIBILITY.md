# Wi-Fi, Network, and Router Compatibility & Limitation Matrix

This document accurately records which diagnostic capabilities are verified against the live Windows host hardware versus which router management flows require physical router credentials or vendor hardware verification.

## 1. Windows Host Wireless Telemetry & Scanning

| Capability | API / Mechanism | Measurement Type | Verification Status | Notes / Honest Limits |
| :--- | :--- | :--- | :--- | :--- |
| Connected Interface, Adapter, SSID, BSSID, PHY, TX/RX Rate, RSSI, Signal Quality | `wlanapi.dll` (`WlanEnumInterfaces`, `WlanQueryInterface`) | Direct Measured | **Verified** on host (`Intel(R) Dual Band Wireless-AC 3160`) | Live Win32 API calls tested on host |
| Channel Width (`20/40/80/160/320 MHz`), Max Spatial Streams, QBSS Load, Country Code | Raw 802.11 IEs (`WlanGetNetworkBssList`, IEs `0, 7, 11, 45, 48, 61, 191, 192, 255`) | Inferred from AP BSS IE | **Verified** on host (`16` live BSSIDs) | Windows `wlanapi` does not directly report per-frame active width; read from connected BSS IEs when visible |
| Neighboring AP Discovery (`SSID, BSSID, Band, Channel, RSSI, Width, Security, PHY`) | `WlanGetNetworkBssList` + safe `WlanScan` | Measured / IE-decoded | **Verified** on host | Active `WlanScan` automatically deferred during active/transitional NetGuard meetings |
| Interface Packet Errors, Discards & PHY Retry/FCS Counters | `Get-NetAdapterStatistics` + `WLAN_STATISTICS` (`0x10000101`) | Direct Measured | **Verified** on host | Combines NDIS stats and Native Wifi PHY counters |
| Connection / Disconnection / Roaming Events | `wevtutil` (`Microsoft-Windows-WLAN-AutoConfig/Operational`) + `WifiRoamTracker` | Direct Measured | **Verified** on host | Tracks both OS operational log and in-session BSSID changes |
| Adapter Capabilities & Advanced Settings | `WlanGetInterfaceCapability` + `Get-NetAdapterAdvancedProperty` | Direct Measured | **Verified** on host | Captures supported PHYs, roaming aggressiveness, and width settings |
| **RF Noise Floor (dBm) & SNR (dB)** | Driver-dependent NDIS / `wlanapi` | Unsupported on standard drivers | **Explicitly Unavailable** | **Never derived from RSSI.** Reported as unavailable with exact explanation unless driver exposes real dBm noise |
| **Per-Frame MCS Index** | Driver-dependent | Unsupported in user-mode `wlanapi` | **Explicitly Unavailable** | Not invented when driver/OS omits it |

## 2. Sequential Internet, DNS, Speed & Bufferbloat Diagnostics

| Feature | Execution Behavior | Safety / Coexistence Rules | Status |
| :--- | :--- | :--- | :--- |
| Baseline Network Conditions | VPN, Windows Proxy, Interface, Gateway change, competing traffic deltas, errors | Non-blocking, non-mutating | **Verified** |
| Sequential Gateway & Public ICMP (`30 + 30`), IPv6, 5-Hop Trace | Single-flight `DiagnosticCoordinator`; IPv6 skipped (`not_configured`) when unroutable; silent `*` hops not auto-flagged as packet loss | Never overlaps throughput tests | **Verified** |
| Multi-Sample DNS Diagnostics | Direct `dnspython` UDP/53 (`cache=None`) across Configured, Router, `1.1.1.1`, `8.8.8.8` with unique cache-busting qnames + ICMP baseline separation | Auto DNS modification permanently disabled; cache flush locked during active calls | **Verified** |
| Speed Test | Multi-stream HTTPS download + opt-in upload; explicitly separates Wi-Fi PHY rate vs Local LAN (`unavailable` without local server) vs Internet DL/UL | Blocked during active/transitional NetGuard calls | **Verified** |
| Bufferbloat Test | Sequential Idle -> Download Load -> Cooldown Drain -> Upload Load -> Optional Combined Load | Explicit confirmation required before optional idle QoS suspension; pre/post readback verification & guaranteed restore | **Verified** |

## 3. Router Adapters & Connected Devices

| Adapter ID | Target Family | Supported Capabilities | Credential Storage | Physical Hardware Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| `zte` | ZTE ZXHN home gateways | Session auth, Wi-Fi/WAN/DNS/QoS read, connected devices read, guarded channel/width writes with backup + readback verify + rollback | Session-only (default) or Windows Credential Manager (`CredWriteW`) | **Software-implemented & tested against local mock server (`hardware_verified=False`)**; blocked from full real-router test without user admin password |
| `huawei` | Huawei HG/AX HiLink routers | `SesTokInfo` auth, Wi-Fi/host-list read, guarded writes with backup + readback verify + rollback | Session-only or Windows Credential Manager | **Software-implemented & mock-tested (`hardware_verified=False`)** |
| `tplink` | TP-Link Archer/Router portals | `stok` JSON auth, Wi-Fi/clients/QoS read, guarded writes & per-device rate limits where firmware supports | Session-only or Windows Credential Manager | **Software-implemented & mock-tested (`hardware_verified=False`)** |
| `generic_probe` | Any gateway / UPnP IGD router | Passive HTTP/HTTPS fingerprinting + read-only UPnP IGD status; strictly read-only | None required | **Verified passively against host gateway (`192.168.1.1`, OUI ZTE)** |

### Important Limitations
- **Per-device bandwidth throttling** cannot be enforced from the local Windows host for external household devices. When the router adapter is unauthenticated or lacks bandwidth-control API support, NetGuard explicitly declares it unsupported and guides users toward NetGuard local per-app QoS or manual router QoS/SQM setup.
- **Transport security**: Local routers using HTTP (`http://192.168.1.1`) or self-signed HTTPS display an explicit security warning requiring user acknowledgement prior to sending credentials. All exported JSON/HTML reports strip secrets via `redact_secrets`.
