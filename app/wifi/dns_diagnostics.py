"""Multi-sample DNS resolution diagnostics respecting NetGuard meeting safety freeze."""

from __future__ import annotations

import asyncio
import statistics
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

import dns.exception
import dns.message
import dns.query
import dns.rcode

from app.dns.detector import identify_provider
from app.wifi.coordinator import DiagnosticCoordinator
from app.wifi.models import DnsDiagnosticsReport, DnsTargetMetrics, utc_now

QueryProbeFn = Callable[[str, str, float], Tuple[bool, Optional[float], str]]


def _default_dns_udp_probe(
    server_ip: str, qname: str, timeout_sec: float = 2.0
) -> Tuple[bool, Optional[float], str]:
    """Send direct UDP DNS query bypassing OS local DNS stub cache."""
    query = dns.message.make_query(qname, "A", want_dnssec=False)
    t0 = time.perf_counter()
    try:
        resp = dns.query.udp(query, server_ip, timeout=timeout_sec)
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        rcode_name = dns.rcode.to_text(resp.rcode())
        return True, elapsed_ms, rcode_name
    except dns.exception.Timeout:
        return False, None, "TIMEOUT"
    except OSError as exc:
        return False, None, f"NET_ERR:{exc.__class__.__name__}"
    except Exception as exc:
        return False, None, f"ERR:{exc.__class__.__name__}"


class DnsDiagnosticsService:
    """Measures configured, router, Cloudflare, and Google DNS servers without auto-modifying OS config."""

    def __init__(
        self,
        *,
        platform: Any = None,
        coordinator: Optional[DiagnosticCoordinator] = None,
        probe_fn: Optional[QueryProbeFn] = None,
    ) -> None:
        self._platform = platform
        self._coordinator = coordinator
        self._probe_fn = probe_fn or _default_dns_udp_probe

    async def _detect_dns_and_gateway(self) -> Tuple[Optional[str], List[str], Optional[str]]:
        iface_name: Optional[str] = None
        dns_list: List[str] = []
        gateway: Optional[str] = None
        if self._platform is None:
            return iface_name, dns_list, gateway

        try:
            if hasattr(self._platform, "get_primary_interface"):
                iface = await self._maybe_await(self._platform.get_primary_interface())
                iface_name = getattr(iface, "name", None) or (
                    iface if isinstance(iface, str) else None
                )
        except Exception:
            pass

        try:
            if hasattr(self._platform, "get_default_gateway"):
                gw = await self._maybe_await(self._platform.get_default_gateway())
                gateway = str(gw).strip() if gw else None
        except Exception:
            pass

        try:
            if hasattr(self._platform, "get_interface_dns_servers"):
                fn = self._platform.get_interface_dns_servers
                try:
                    raw_res = fn(iface_name) if iface_name else fn()
                except TypeError:
                    try:
                        raw_res = fn()
                    except TypeError:
                        raw_res = fn(iface_name or "Wi-Fi")
                raw_dns = await self._maybe_await(raw_res)
                if isinstance(raw_dns, list):
                    dns_list = [str(d).strip() for d in raw_dns if d]
        except Exception:
            pass

        return iface_name, dns_list, gateway

    async def _measure_icmp_baseline(self, server_ip: str, pings: int = 3) -> Optional[float]:
        if self._platform is None or not hasattr(self._platform, "ping"):
            return None
        rtts: List[float] = []
        for _ in range(pings):
            try:
                res = await self._maybe_await(self._platform.ping(server_ip, timeout_sec=0.8))
                if getattr(res, "success", False) and getattr(res, "latency_ms", None) is not None:
                    rtts.append(float(res.latency_ms))
            except Exception:
                pass
        return round(statistics.median(rtts), 2) if rtts else None

    async def run_diagnostics(
        self,
        *,
        samples_per_server: int = 6,
        cache_bypass_base_domain: str = "one.one.one.one",
        timeout_sec: float = 2.0,
    ) -> DnsDiagnosticsReport:
        """Run multi-sample read-only DNS latency measurements with cache-bypass queries."""
        iface_name, configured_dns, gateway_ip = await self._detect_dns_and_gateway()
        meeting_frozen = False
        if self._coordinator is not None:
            meeting_frozen, _ = self._coordinator.is_meeting_active()

        configured_primary = configured_dns[0] if configured_dns else None
        router_dns = gateway_ip if gateway_ip else None

        # Define the 4 required diagnostic roles cleanly
        specs: List[Tuple[str, Optional[str], str, bool, Optional[str]]] = [
            (
                "configured",
                configured_primary,
                f"Configured DNS ({configured_primary or 'None'})",
                bool(configured_primary),
                None if configured_primary else "No DNS server detected on active interface.",
            ),
            (
                "router",
                router_dns,
                f"Router DNS ({router_dns or 'Unavailable'})",
                bool(router_dns),
                (
                    "Same as configured DNS; measured independently as gateway resolver."
                    if router_dns and router_dns == configured_primary
                    else (None if router_dns else "No default gateway detected for router DNS.")
                ),
            ),
            ("cloudflare", "1.1.1.1", "Cloudflare DNS (1.1.1.1)", True, None),
            ("google", "8.8.8.8", "Google DNS (8.8.8.8)", True, None),
        ]

        samples_map: Dict[str, List[float]] = {s[0]: [] for s in specs}
        statuses_map: Dict[str, List[str]] = {s[0]: [] for s in specs}
        counts_map: Dict[str, int] = {s[0]: 0 for s in specs}

        # Interleaved cache-busting rounds ensure identical network time-window fairness
        for round_idx in range(max(3, samples_per_server)):
            token_lbl = f"ng-{round_idx}-{uuid.uuid4().hex[:8]}"
            # Direct UDP to resolver with unique random label avoids OS & resolver positive cache hits.
            qname = f"{token_lbl}.{cache_bypass_base_domain}"
            for role, server_ip, _, applicable, _ in specs:
                if not applicable or not server_ip:
                    continue
                counts_map[role] += 1
                ok, lat_ms, status_txt = await asyncio.to_thread(
                    self._probe_fn, server_ip, qname, timeout_sec
                )
                statuses_map[role].append(status_txt)
                if ok and lat_ms is not None:
                    samples_map[role].append(lat_ms)

        targets: List[DnsTargetMetrics] = []
        for role, server_ip, label, applicable, init_note in specs:
            if not applicable or not server_ip:
                targets.append(
                    DnsTargetMetrics(
                        role=role,  # type: ignore[arg-type]
                        server_ip=None,
                        server_label=label,
                        is_applicable=False,
                        status="not_applicable",
                        note=init_note,
                    )
                )
                continue

            rtts = samples_map[role]
            sent_n = counts_map[role]
            ok_n = len(rtts)
            fail_n = sent_n - ok_n
            icmp_rtt = await self._measure_icmp_baseline(server_ip, pings=3)

            provider = identify_provider(server_ip)
            prov_name = getattr(provider, "name", None) if provider else None

            if ok_n == 0:
                targets.append(
                    DnsTargetMetrics(
                        role=role,  # type: ignore[arg-type]
                        server_ip=server_ip,
                        server_label=label,
                        is_applicable=True,
                        status="unreachable",
                        sample_count=sent_n,
                        successful_samples=0,
                        failed_samples=fail_n,
                        response_statuses=statuses_map[role],
                        icmp_baseline_ms=icmp_rtt,
                        provider_identified=prov_name,
                        note=init_note or "All UDP/53 queries timed out or failed.",
                    )
                )
                continue

            med = round(statistics.median(rtts), 2)
            avg = round(statistics.fmean(rtts), 2)
            stdev = round(statistics.stdev(rtts), 2) if ok_n >= 2 else 0.0
            proc_overhead = (
                round(max(0.0, med - icmp_rtt), 2) if icmp_rtt is not None else None
            )

            targets.append(
                DnsTargetMetrics(
                    role=role,  # type: ignore[arg-type]
                    server_ip=server_ip,
                    server_label=label,
                    is_applicable=True,
                    status="ok",
                    query_mode="direct_udp_uncached_unique_qname",
                    sample_count=sent_n,
                    successful_samples=ok_n,
                    failed_samples=fail_n,
                    min_ms=round(min(rtts), 2),
                    avg_ms=avg,
                    median_ms=med,
                    max_ms=round(max(rtts), 2),
                    stdev_ms=stdev,
                    raw_samples_ms=rtts,
                    response_statuses=statuses_map[role],
                    icmp_baseline_ms=icmp_rtt,
                    estimated_dns_processing_ms=proc_overhead,
                    provider_identified=prov_name,
                    note=init_note,
                )
            )

        # Evaluate recommendation honestly: only crown winner if meaningful & statistically distinct
        healthy = [t for t in targets if t.status == "ok" and t.median_ms is not None and t.failed_samples == 0]
        configured_t = next((t for t in targets if t.role == "configured"), None)
        best_t = min(healthy, key=lambda t: t.median_ms or 9999.0) if healthy else None

        recommended_dns: Optional[str] = None
        confidence = "low"
        summary = "DNS comparison completed."

        if best_t and configured_t and configured_t.status == "ok" and configured_t.median_ms is not None:
            diff_ms = configured_t.median_ms - (best_t.median_ms or 0.0)
            combined_jitter = (configured_t.stdev_ms or 0.0) + (best_t.stdev_ms or 0.0)
            if best_t.server_ip != configured_t.server_ip and diff_ms >= max(8.0, 0.75 * combined_jitter):
                recommended_dns = best_t.server_ip
                confidence = "high" if best_t.sample_count >= 5 and diff_ms >= 12.0 else "medium"
                summary = (
                    f"{best_t.server_label} measured faster than configured DNS "
                    f"({best_t.median_ms} ms vs {configured_t.median_ms} ms median across {best_t.sample_count} samples)."
                )
            else:
                confidence = "medium" if best_t.sample_count >= 5 else "low"
                summary = (
                    f"Configured DNS ({configured_t.server_label}: {configured_t.median_ms} ms median) is "
                    "within measurement variance of public alternatives; no urgent DNS change warranted."
                )
        elif best_t:
            recommended_dns = best_t.server_ip
            confidence = "medium"
            summary = f"Healthy resolver observed: {best_t.server_label} ({best_t.median_ms} ms median)."
        else:
            summary = "All tested DNS servers failed or timed out."

        notes = [
            "Direct UDP/53 queries with unique random subdomains bypassed the Windows local DNS stub cache.",
            "Configured OS DNS settings were NOT modified automatically.",
        ]
        if meeting_frozen:
            notes.append(
                "NetGuard meeting safety freeze is active: DNS cache flush and resolver switches are locked."
            )

        return DnsDiagnosticsReport(
            captured_at=utc_now(),
            interface_name=iface_name,
            configured_dns_servers=configured_dns,
            router_dns_server=router_dns,
            targets=targets,
            cache_bypass_method="Direct UDP/53 wire queries via dnspython (bypass OS cache) using randomized unique subdomain labels per round.",
            recommended_dns=recommended_dns,
            comparison_confidence=confidence,  # type: ignore[arg-type]
            meeting_safety_frozen=meeting_frozen,
            auto_modified_dns=False,
            summary=summary,
            notes=notes,
        )

    @staticmethod
    async def _maybe_await(val: Any) -> Any:
        if asyncio.iscoroutine(val) or hasattr(val, "__await__"):
            return await val
        return val
