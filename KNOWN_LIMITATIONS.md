# NETGUARD AI — KNOWN LIMITATIONS

## 1. Operating System & Permissions
- **Windows Administrator Rights**: Actions that reconfigure network adapters (such as setting DNS or renewing IP leases via Netsh/WMI) require administrator privileges. In unprivileged user mode, NetGuard runs in Read-Only Observability & Diagnostic mode and flags corrective actions as requiring elevation.
- **Raw Socket Privileges**: Direct ICMP raw sockets on Windows require Administrator or `SO_BINDTODEVICE` capabilities. NetGuard gracefully uses native `Windows IcmpSendEcho` API via `iphlpapi.dll` and fallback TCP connection probes to avoid raw socket permission issues.

## 2. Hardware & Router Specifics
- **Cellular Router API Diversity**: Different 4G/5G cellular routers (Huawei, ZTE, Netgear, TP-Link) expose heterogeneous management interfaces (HiLink XML, REST, Telnet, or no external API). Stage 6 provides a generic adapter interface; initial deployment uses host-level metrics until router model auto-detection is completed.

## 3. Network Environment
- **Captive Portals**: Hotspots or public cellular portals intercepting all TCP/DNS traffic may require user interaction and cannot be autonomously bypassed.

