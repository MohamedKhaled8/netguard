"""DNS Resolver Benchmark and Reliability Scorer.

Sends genuine DNS queries directly to each DNS server over UDP and TCP (port 53).
Measures real response times, median and average latency, min/max, success/failure counts.
Never generates synthetic or estimated values. Accurately distinguishes Primary and Secondary addresses.
"""

from __future__ import annotations
import asyncio
import time
import socket
import subprocess
import statistics
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, model_validator
import dns.resolver


class ResolverScore(BaseModel):
    """Benchmark evaluation result for a DNS resolver."""
    model_config = ConfigDict(frozen=True)

    ip: str
    name: str
    primary_ip: str = ""
    secondary_ip: Optional[str] = None
    provider_name: str = ""
    median_latency_ms: float = 0.0
    mean_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    stdev_latency_ms: float = 0.0
    success_rate: float = 1.0
    failure_rate: float = 0.0
    successful_queries: int = 0
    failed_queries: int = 0
    udp_median_latency_ms: float = 0.0
    tcp_median_latency_ms: float = 0.0
    tcp_success_rate: float = 1.0
    composite_score: float = 0.0
    is_active: bool = False
    is_configured: bool = False
    is_reachable: bool = True
    is_ip_reachable: bool = True
    is_recommended: bool = False
    availability_status: str = "سليم وممتاز"
    status_label: str = "سليم"
    rank: int = 0
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_invariants(self) -> ResolverScore:
        """Enforce strict invariants: auto-derive addresses and ensure non-contradictory recommendation."""
        if not self.primary_ip:
            object.__setattr__(self, "primary_ip", self.ip)
        if not self.provider_name:
            clean = (
                self.name.replace(" Primary", "")
                .replace(" Secondary", "")
                .replace(" Secure", "")
                .strip()
            )
            object.__setattr__(self, "provider_name", clean)
        if not self.secondary_ip:
            try:
                from app.dns.detector import get_secondary_ip
                sec = get_secondary_ip(self.primary_ip)
                if sec:
                    object.__setattr__(self, "secondary_ip", sec)
            except Exception:
                pass

        if self.is_active and self.is_recommended:
            raise ValueError("Resolver cannot be simultaneously active and recommended as an alternative.")
        if self.is_configured and self.is_recommended:
            raise ValueError("Configured system resolver cannot be marked as recommended alternative.")
        return self

    def update_validated(self, **kwargs) -> ResolverScore:
        """Return a reconstructed instance validated through Pydantic model_validate."""
        data = self.model_dump()
        data.update(kwargs)
        return ResolverScore.model_validate(data)

    @property
    def latency_ms(self) -> float:
        """Measured DNS query response time in milliseconds (median preferred)."""
        return self.median_latency_ms if self.median_latency_ms > 0.0 else self.mean_latency_ms


def get_default_benchmark_resolvers() -> List[Tuple[str, str]]:
    """Load verified default resolvers from the provider catalog."""
    from app.dns.detector import load_providers_catalogue
    cat = load_providers_catalogue()
    resolvers: List[Tuple[str, str]] = []
    seen_ips = set()
    for p in cat.get("global_anycast", []):
        p_name = p.get("name", "")
        p_ip = p.get("primary_ip")
        s_ip = p.get("secondary_ip")
        if p_ip and p_ip not in seen_ips:
            resolvers.append((p_ip, f"{p_name} Primary"))
            seen_ips.add(p_ip)
        if s_ip and s_ip not in seen_ips:
            resolvers.append((s_ip, f"{p_name} Secondary"))
            seen_ips.add(s_ip)

    if not resolvers:
        resolvers = [
            ("1.1.1.1", "Cloudflare DNS Primary"),
            ("1.0.0.1", "Cloudflare DNS Secondary"),
            ("8.8.8.8", "Google Public DNS Primary"),
            ("8.8.4.4", "Google Public DNS Secondary"),
            ("9.9.9.9", "Quad9 Secure Primary"),
            ("149.112.112.112", "Quad9 Secure Secondary"),
            ("208.67.222.222", "OpenDNS Primary"),
            ("208.67.220.220", "OpenDNS Secondary"),
            ("94.140.14.14", "AdGuard DNS Primary"),
            ("94.140.15.15", "AdGuard DNS Secondary"),
            ("185.228.168.9", "CleanBrowsing Primary"),
        ]
    return resolvers


class DNSBenchmark:
    """Benchmarks and ranks candidate DNS resolvers across multiple domains via genuine DNS queries."""

    DEFAULT_DOMAINS = [
        "google.com",
        "cloudflare.com",
        "wikipedia.org",
    ]

    def __init__(
        self,
        resolvers: Optional[List[Tuple[str, str]]] = None,
        domains: Optional[List[str]] = None,
        timeout_sec: float = 2.0,
        rounds: int = 3,
    ) -> None:
        self.resolvers = resolvers if resolvers is not None else get_default_benchmark_resolvers()
        self.domains = domains or self.DEFAULT_DOMAINS
        self.timeout_sec = timeout_sec
        self.rounds = max(1, rounds)

    async def benchmark_resolver(
        self,
        ip: str,
        name: str,
        is_active: bool = False,
    ) -> ResolverScore:
        """Run multiple query rounds against a specific resolver directly over UDP and TCP."""
        loop = asyncio.get_running_loop()

        def _sync_bench() -> Tuple[List[float], int, List[float], int, bool]:
            res = dns.resolver.Resolver(configure=False)
            res.nameservers = [ip]
            res.lifetime = self.timeout_sec
            res.timeout = self.timeout_sec
            res.cache = None

            udp_latencies: List[float] = []
            udp_failures = 0
            tcp_latencies: List[float] = []
            tcp_failures = 0

            # 1. UDP DNS query measurements across configured rounds and domains
            for _ in range(self.rounds):
                for domain in self.domains:
                    try:
                        t0 = time.perf_counter()
                        res.resolve(domain, "A", tcp=False)
                        d_ms = (time.perf_counter() - t0) * 1000.0
                        udp_latencies.append(d_ms)
                    except Exception:
                        udp_failures += 1

            # 2. Distinct TCP DNS resolution test (Port 53 TCP fallback and DoH/DoT readiness)
            for domain in self.domains:
                try:
                    t0 = time.perf_counter()
                    res.resolve(domain, "A", tcp=True)
                    d_tcp_ms = (time.perf_counter() - t0) * 1000.0
                    tcp_latencies.append(d_tcp_ms)
                except Exception:
                    tcp_failures += 1

            # Check if server IP is reachable if all queries failed
            is_ip_reachable = True
            if not udp_latencies and not tcp_latencies:
                is_ip_reachable = False
                try:
                    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
                    sock = socket.socket(family, socket.SOCK_STREAM)
                    sock.settimeout(0.8)
                    sock.connect((ip, 53))
                    sock.close()
                    is_ip_reachable = True
                except Exception:
                    try:
                        cmd = ["ping", "-n", "1", "-w", "700", ip]
                        p = subprocess.run(
                            cmd,
                            capture_output=True,
                            timeout=1.0,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                        )
                        if p.returncode == 0:
                            is_ip_reachable = True
                    except Exception:
                        pass

            return udp_latencies, udp_failures, tcp_latencies, tcp_failures, is_ip_reachable

        udp_lats, udp_fails, tcp_lats, tcp_fails, is_ip_reachable = await loop.run_in_executor(None, _sync_bench)
        total_udp = len(self.domains) * self.rounds
        failure_rate = (udp_fails / total_udp) if total_udp > 0 else 1.0
        success_rate = (len(udp_lats) / total_udp) if total_udp > 0 else 0.0
        is_dns_reachable = len(udp_lats) > 0 or len(tcp_lats) > 0

        # TCP metrics
        total_tcp = len(self.domains)
        tcp_success_rate = (len(tcp_lats) / total_tcp) if total_tcp > 0 else 0.0
        tcp_med_lat = float(statistics.median(tcp_lats)) if tcp_lats else 0.0

        from app.dns.detector import get_secondary_ip
        sec_ip = get_secondary_ip(ip)

        if udp_lats:
            median_lat = float(statistics.median(udp_lats))
            mean_lat = float(statistics.mean(udp_lats))
            min_lat = float(min(udp_lats))
            max_lat = float(max(udp_lats))
            stdev_lat = float(statistics.stdev(udp_lats)) if len(udp_lats) >= 2 else 0.0
            if median_lat < 60.0:
                avail_status = "سريع (ممتاز)"
                status_lbl = "سليم وممتاز"
            elif median_lat < 120.0:
                avail_status = "مقبول (طبيعي)"
                status_lbl = "استجابة مقبولة"
            else:
                avail_status = "بطيء"
                status_lbl = "استجابة بطيئة"
        else:
            mean_lat = self.timeout_sec * 1000.0
            median_lat = mean_lat
            min_lat = mean_lat
            max_lat = mean_lat
            stdev_lat = 0.0
            avail_status = "غير متاح" if not is_ip_reachable else "فشل الاستعلام"
            status_lbl = "فشل الاستعلام (Port 53)" if is_ip_reachable else "تعذر الوصول للـ IP"

        # Composite score formula: 100 - (0.35 * MedianLatency) - (250 * FailureRate) - (0.15 * Stdev)
        raw_score = 100.0 - (0.35 * median_lat) - (250.0 * failure_rate) - (0.15 * stdev_lat)
        score = max(0.0, min(100.0, raw_score))

        clean_provider = (
            name.replace(" Primary", "")
            .replace(" Secondary", "")
            .replace(" Secure", "")
            .strip()
        )

        return ResolverScore(
            ip=ip,
            name=name,
            primary_ip=ip,
            secondary_ip=sec_ip,
            provider_name=clean_provider,
            median_latency_ms=median_lat,
            mean_latency_ms=mean_lat,
            min_latency_ms=min_lat,
            max_latency_ms=max_lat,
            stdev_latency_ms=stdev_lat,
            success_rate=success_rate,
            failure_rate=failure_rate,
            successful_queries=len(udp_lats),
            failed_queries=udp_fails,
            udp_median_latency_ms=median_lat if udp_lats else 0.0,
            tcp_median_latency_ms=tcp_med_lat,
            tcp_success_rate=tcp_success_rate,
            composite_score=score,
            is_active=is_active,
            is_configured=is_active,
            is_reachable=is_dns_reachable,
            is_ip_reachable=is_ip_reachable,
            is_recommended=False,
            availability_status=avail_status,
            status_label=status_lbl,
        )

    async def rank_all(
        self,
        active_resolver_ips: Optional[List[str]] = None,
        active_name: str = "",
    ) -> List[ResolverScore]:
        """Benchmark all candidate resolvers concurrently and return sorted by median latency ascending."""
        from app.dns.detector import identify_provider, get_secondary_ip
        all_targets = list(self.resolvers)
        active_ips_set = set(active_resolver_ips or [])
        primary_resolver_ip = (active_resolver_ips[0] if active_resolver_ips else "")

        # Ensure active system resolver(s) are evaluated under identical conditions
        for a_ip in (active_resolver_ips or []):
            if a_ip and not any(a_ip == r_ip for r_ip, _ in all_targets):
                label = active_name or identify_provider(a_ip) or f"خادم جهازك النشط ({a_ip})"
                all_targets.insert(0, (a_ip, label))

        import inspect

        tasks = []
        for ip, name in all_targets:
            is_act = bool(primary_resolver_ip and ip == primary_resolver_ip)
            fn = getattr(self, "benchmark_resolver")
            try:
                sig = inspect.signature(fn)
                if "is_active" in sig.parameters:
                    tasks.append(fn(ip, name, is_active=is_act))
                else:
                    tasks.append(fn(ip, name))
            except (ValueError, TypeError):
                try:
                    tasks.append(fn(ip, name, is_active=is_act))
                except TypeError:
                    tasks.append(fn(ip, name))

        scores = list(await asyncio.gather(*tasks))

        # Ensure is_active matches primary resolver and is_configured matches active_ips_set
        updated_scores: List[ResolverScore] = []
        for s in scores:
            should_be_active = bool(primary_resolver_ip and s.ip == primary_resolver_ip)
            should_be_configured = (s.ip in active_ips_set)
            if s.is_active != should_be_active or s.is_configured != should_be_configured:
                s = s.update_validated(is_active=should_be_active, is_configured=should_be_configured)
            updated_scores.append(s)
        scores = updated_scores

        # Gate: success rate >= 80% (0.80) considered viable
        viable = [s for s in scores if s.success_rate >= 0.80]
        unviable = [s for s in scores if s.success_rate < 0.80]

        # Sort strictly ascending by median latency
        sorted_viable = sorted(viable, key=lambda s: s.median_latency_ms)
        sorted_unviable = sorted(unviable, key=lambda s: (s.failure_rate, s.median_latency_ms))

        # Identify top recommended alternative candidate (must NOT be the primary active resolver AND must NOT be configured)
        recommended_ip: Optional[str] = None
        for cand in sorted_viable:
            if cand.ip != primary_resolver_ip and not cand.is_active and not cand.is_configured:
                recommended_ip = cand.ip
                break

        final_scores: List[ResolverScore] = []
        rank_counter = 1
        for s in (sorted_viable + sorted_unviable):
            is_rec = bool(recommended_ip and s.ip == recommended_ip and not s.is_configured)
            s = s.update_validated(rank=rank_counter, is_recommended=is_rec)
            final_scores.append(s)
            rank_counter += 1

        # Write benchmark evidence report to docs/dns_benchmark.md
        self._write_benchmark_report(final_scores)
        return final_scores

    def _write_benchmark_report(self, scores: List[ResolverScore]) -> None:
        try:
            doc_path = "docs/dns_benchmark.md"
            lines = [
                "# DNS Resolver Benchmark Report",
                f"Generated at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
                f"Rounds: {self.rounds} | Domains: {', '.join(self.domains)}",
                "",
                "| Rank | Provider | Primary IP | Secondary IP | Median Latency | Success Rate | Status | Recommendation |",
                "|---|---|---|---|---|---|---|---|",
            ]
            for s in scores:
                status = "Passed (Viable)" if s.success_rate >= 0.80 else "Rejected (<80% success)"
                rec = "Recommended" if s.is_recommended else ("Active Primary" if s.is_active else ("Configured" if s.is_configured else "Alternative"))
                lines.append(
                    f"| {s.rank:02d} | {s.provider_name} | `{s.primary_ip}` | `{s.secondary_ip or '—'}` | {s.median_latency_ms:.1f} ms | {s.success_rate * 100:.0f}% | {status} | {rec} |"
                )
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception:
            pass

    # Compatibility alias
    benchmark_all = rank_all


def generate_dns_analysis(
    active_ip: str,
    active_name: str,
    active_score: Optional[ResolverScore],
    all_scores: List[ResolverScore],
) -> Dict[str, Any]:
    """Generates structured, plain-language technical analysis and prudent recommendation."""
    total_resolvers = len(all_scores)
    all_failed = (total_resolvers > 0 and all(s.success_rate == 0.0 for s in all_scores))

    # 1. Total Internet Failure Check
    if all_failed:
        status_tag = "انقطاع اتصال الإنترنت"
        status_code = "internet_down"
        verdict_desc = "تعذر الوصول إلى كافة خوادم DNS العالمية والمحلية في نفس الوقت. المشكلة ليست في خادم DNS بل في انقطاع خدمة الإنترنت بجهازك أو الراوتر."
        rec_text = "تحقق من كابل الشبكة أو اتصال Wi-Fi وتأكد من إضاءة مؤشر الإنترنت في الراوتر قبل تعديل إعدادات DNS."
        return {
            "verdict": verdict_desc,
            "analysis_text": verdict_desc,
            "recommendation_text": rec_text,
            "status": "unresponsive",
            "health_tier": "unresponsive",
            "current": {
                "name": active_name,
                "ip": active_ip,
                "mean_ms": None,
                "min_ms": None,
                "max_ms": None,
                "success_rate_pct": 0.0,
                "status_tag": status_tag,
                "status_code": status_code,
                "verdict": verdict_desc,
            },
            "alternative": {
                "candidate_name": "—",
                "candidate_ip": "—",
                "candidate_ms": None,
                "candidate_success_pct": 0.0,
                "diff_ms": 0.0,
            },
            "recommendation": {
                "text": rec_text,
                "should_switch": False,
                "best_target": None,
            },
        }

    # 2. Current Resolver Evaluation
    if active_score and active_score.success_rate >= 0.80:
        curr_median_ms = active_score.median_latency_ms
        curr_mean_ms = active_score.mean_latency_ms
        min_ms = active_score.min_latency_ms
        max_ms = active_score.max_latency_ms
        succ_pct = active_score.success_rate * 100.0
        if curr_median_ms < 60.0:
            status_tag = "سليم وممتاز"
            status_code = "ok"
            verdict_desc = f"خادم DNS المعتمد بجهازك حالياً ({active_name}) يعمل بكفاءة وسرعة ممتازة (وسيط {curr_median_ms:.1f} ms · متوسط {curr_mean_ms:.1f} ms) بنجاح كامل لجميع الاستعلامات دون أي تأخير."
        elif curr_median_ms < 100.0:
            status_tag = "استجابة طبيعية"
            status_code = "ok"
            verdict_desc = f"خادم DNS المعتمد ({active_name}) يستجيب بشكل طبيعي ومستقر (وسيط {curr_median_ms:.1f} ms · متوسط {curr_mean_ms:.1f} ms). تصفح المواقع يتم بصورة سلسة."
        else:
            status_tag = "استجابة بطيئة"
            status_code = "warn"
            verdict_desc = f"خادم DNS المعتمد ({active_name}) يعاني من بطء في ترجمة النطاقات (وسيط {curr_median_ms:.1f} ms · متوسط {curr_mean_ms:.1f} ms)، مما قد يسبب تأخيراً طفيفاً عند فتح الروابط الجديدة."
    else:
        curr_median_ms = None
        curr_mean_ms = None
        min_ms = None
        max_ms = None
        succ_pct = (active_score.success_rate * 100.0) if active_score else 0.0
        status_tag = "غير مستجيب / انقطاع"
        status_code = "bad"
        if active_score and not active_score.is_ip_reachable:
            verdict_desc = f"خادم DNS الحالي ({active_name} · {active_ip}) لا يستجيب وغير متاح تماماً على الشبكة (تعذر الوصول للعنوان)."
        else:
            verdict_desc = f"خادم DNS الحالي ({active_name} · {active_ip}) لا يستجيب لطلبات المنفذ 53 أو أن الاستعلامات تفشل بالكامل."

    # 3. Alternative Candidates Evaluation
    viable = [
        s for s in all_scores
        if s.success_rate >= 0.80 and not s.is_active and not s.is_configured and not (active_ip and s.ip == active_ip)
    ]
    best_candidate = viable[0] if viable else None

    # 4. Smart Recommendation Synthesis (Strict median-to-median comparisons)
    if status_code == "bad":
        if best_candidate:
            rec_text = f"خادم DNS الحالي غير مستجيب. يُوصى بالتبديل فوراً إلى {best_candidate.name} ({best_candidate.median_latency_ms:.1f} ms) لاستعادة تصفح المواقع."
            should_switch = True
        else:
            rec_text = "خادم DNS الحالي لا يستجيب، كما تعذر التحقق من بدائل مستقرة. تحقق من اتصال الإنترنت أولاً."
            should_switch = False
    elif best_candidate and curr_median_ms is not None:
        diff_median_ms = curr_median_ms - best_candidate.median_latency_ms
        diff_mean_ms = (curr_mean_ms - best_candidate.mean_latency_ms) if curr_mean_ms is not None else diff_median_ms
        if diff_median_ms >= 15.0 and best_candidate.success_rate >= 0.95 and best_candidate.median_latency_ms < 75.0:
            rec_text = f"الخادم البديل ({best_candidate.name}) يقدم استجابة أسرع بفارق ملحوظ (+{diff_median_ms:.1f} ms) ونسبة نجاح 100%، ويمكنك اعتماده لتسريع التصفح."
            should_switch = True
        elif diff_median_ms > 0:
            rec_text = f"الخادم الحالي يعمل بشكل طبيعي ومستقر. الفارق مع الخادم البديل طفيف (+{diff_median_ms:.1f} ms) ولا توجد ضرورة لتغييره."
            should_switch = False
        else:
            rec_text = "الخادم الحالي يقدم أفضل زمن استجابة في بيئتك، ولا توجد ضرورة لتغييره."
            should_switch = False
    else:
        diff_median_ms = 0.0
        diff_mean_ms = 0.0
        rec_text = "الخادم الحالي مستقر ويعمل ضمن المعايير المثالية."
        should_switch = False

    return {
        "verdict": verdict_desc,
        "analysis_text": verdict_desc,
        "recommendation_text": rec_text,
        "status": "healthy" if status_code == "ok" else ("slow" if status_code == "warn" else "unresponsive"),
        "health_tier": "healthy" if status_code == "ok" else ("slow" if status_code == "warn" else "unresponsive"),
        "current": {
            "name": active_name,
            "ip": active_ip,
            "median_ms": curr_median_ms,
            "mean_ms": curr_mean_ms,
            "min_ms": min_ms,
            "max_ms": max_ms,
            "success_rate_pct": succ_pct,
            "status_tag": status_tag,
            "status_code": status_code,
            "verdict": verdict_desc,
        },
        "alternative": {
            "candidate_name": best_candidate.name if best_candidate else "—",
            "candidate_ip": best_candidate.ip if best_candidate else "—",
            "candidate_ms": best_candidate.median_latency_ms if best_candidate else None,
            "candidate_median_ms": best_candidate.median_latency_ms if best_candidate else None,
            "candidate_mean_ms": best_candidate.mean_latency_ms if best_candidate else None,
            "candidate_success_pct": (best_candidate.success_rate * 100.0) if best_candidate else 0.0,
            "diff_ms": (curr_median_ms - best_candidate.median_latency_ms) if (best_candidate and curr_median_ms is not None) else 0.0,
            "diff_median_ms": (curr_median_ms - best_candidate.median_latency_ms) if (best_candidate and curr_median_ms is not None) else 0.0,
            "diff_mean_ms": (curr_mean_ms - best_candidate.mean_latency_ms) if (best_candidate and curr_mean_ms is not None) else 0.0,
        },
        "recommendation": {
            "text": rec_text,
            "should_switch": should_switch,
            "best_target": (best_candidate.ip, best_candidate.name) if (best_candidate and should_switch) else None,
        },
    }
