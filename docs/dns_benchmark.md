# DNS Resolver Benchmark Report
Generated at: 2026-11-22 14:27:29 UTC
Rounds: 1 | Domains: google.com, cloudflare.com, wikipedia.org

| Rank | Provider | Primary IP | Secondary IP | Median Latency | Success Rate | Status | Recommendation |
|---|---|---|---|---|---|---|---|
| 01 | Google Public DNS | `8.8.8.8` | `8.8.4.4` | 55.9 ms | 100% | Passed (Viable) | Active Primary |
| 02 | Google Public DNS | `8.8.4.4` | `8.8.8.8` | 59.3 ms | 100% | Passed (Viable) | Recommended |
| 03 | CleanBrowsing | `185.228.168.9` | `185.228.169.9` | 66.5 ms | 100% | Passed (Viable) | Alternative |
| 04 | OpenDNS (Cisco) | `208.67.222.222` | `208.67.220.220` | 67.7 ms | 100% | Passed (Viable) | Configured |
| 05 | OpenDNS (Cisco) | `208.67.220.220` | `208.67.222.222` | 69.2 ms | 100% | Passed (Viable) | Alternative |
| 06 | Quad9 | `9.9.9.9` | `149.112.112.112` | 70.2 ms | 100% | Passed (Viable) | Alternative |
| 07 | Quad9 | `149.112.112.112` | `9.9.9.9` | 70.3 ms | 100% | Passed (Viable) | Alternative |
| 08 | Cloudflare | `1.1.1.1` | `1.0.0.1` | 71.1 ms | 100% | Passed (Viable) | Alternative |
| 09 | AdGuard DNS | `94.140.14.14` | `94.140.15.15` | 79.1 ms | 100% | Passed (Viable) | Alternative |
| 10 | Cloudflare | `1.0.0.1` | `1.1.1.1` | 80.9 ms | 100% | Passed (Viable) | Alternative |
| 11 | CleanBrowsing | `185.228.169.9` | `185.228.168.9` | 83.4 ms | 100% | Passed (Viable) | Alternative |
| 12 | Control D | `76.76.2.0` | `76.76.10.0` | 85.9 ms | 100% | Passed (Viable) | Alternative |
| 13 | AdGuard DNS | `94.140.15.15` | `94.140.14.14` | 88.0 ms | 100% | Passed (Viable) | Alternative |
| 14 | Control D | `76.76.10.0` | `76.76.2.0` | 83.4 ms | 67% | Rejected (<80% success) | Alternative |
| 15 | Google Public DNS | `2001:4860:4860::8844` | `2001:4860:4860::8888` | 1000.0 ms | 0% | Rejected (<80% success) | Configured |
| 16 | Google Public DNS | `2001:4860:4860::8888` | `2001:4860:4860::8844` | 1000.0 ms | 0% | Rejected (<80% success) | Configured |
