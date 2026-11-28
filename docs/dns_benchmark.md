# DNS Resolver Benchmark Report
Generated at: 2026-11-28 12:12:12 UTC
Rounds: 1 | Domains: google.com, cloudflare.com, wikipedia.org

| Rank | Provider | Primary IP | Secondary IP | Median Latency | Success Rate | Status | Recommendation |
|---|---|---|---|---|---|---|---|
| 01 | Google Public DNS | `8.8.8.8` | `8.8.4.4` | 67.8 ms | 100% | Passed (Viable) | Active Primary |
| 02 | Cloudflare | `1.1.1.1` | `1.0.0.1` | 73.2 ms | 100% | Passed (Viable) | Recommended |
| 03 | Quad9 | `149.112.112.112` | `9.9.9.9` | 75.4 ms | 100% | Passed (Viable) | Alternative |
| 04 | AdGuard DNS | `94.140.14.14` | `94.140.15.15` | 81.5 ms | 100% | Passed (Viable) | Alternative |
| 05 | Google Public DNS | `8.8.4.4` | `8.8.8.8` | 82.5 ms | 100% | Passed (Viable) | Configured |
| 06 | Cloudflare | `1.0.0.1` | `1.1.1.1` | 84.3 ms | 100% | Passed (Viable) | Alternative |
| 07 | OpenDNS (Cisco) | `208.67.222.222` | `208.67.220.220` | 85.5 ms | 100% | Passed (Viable) | Alternative |
| 08 | OpenDNS (Cisco) | `208.67.220.220` | `208.67.222.222` | 91.9 ms | 100% | Passed (Viable) | Alternative |
| 09 | Quad9 | `9.9.9.9` | `149.112.112.112` | 122.4 ms | 100% | Passed (Viable) | Alternative |
| 10 | AdGuard DNS | `94.140.15.15` | `94.140.14.14` | 130.6 ms | 100% | Passed (Viable) | Alternative |
| 11 | Control D | `76.76.10.0` | `76.76.2.0` | 143.7 ms | 100% | Passed (Viable) | Alternative |
| 12 | Control D | `76.76.2.0` | `76.76.10.0` | 169.8 ms | 100% | Passed (Viable) | Alternative |
| 13 | CleanBrowsing | `185.228.168.9` | `185.228.169.9` | 173.5 ms | 100% | Passed (Viable) | Alternative |
| 14 | CleanBrowsing | `185.228.169.9` | `185.228.168.9` | 243.3 ms | 33% | Rejected (<80% success) | Alternative |
| 15 | Google Public DNS | `2001:4860:4860::8844` | `2001:4860:4860::8888` | 1000.0 ms | 0% | Rejected (<80% success) | Configured |
| 16 | Google Public DNS | `2001:4860:4860::8888` | `2001:4860:4860::8844` | 1000.0 ms | 0% | Rejected (<80% success) | Configured |
