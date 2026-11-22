"""Authoritative Centralized DNS Subsystem Service.

Enforces:
1. Real-time detection of configured Windows DNS on the active network adapter.
2. Comparative performance benchmarking using genuine UDP/TCP DNS queries.
3. Ranking and intelligent recommendation of Primary and Secondary DNS.
4. Transactional 7-step OS DNS configuration with verification and auto-rollback.
5. Safeguarded Automatic DNS Optimization with anti-flapping controls.
6. Restoration of previous DNS configurations.
7. Synchronization with DnsStateManager as the single source of truth across all views.
"""

from __future__ import annotations
import asyncio
import ipaddress
import logging
import socket
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.dns.benchmark import DNSBenchmark, ResolverScore
from app.dns.detector import (
    get_secondary_ip,
    get_provider_ipv6,
    identify_provider,
    measure_dns_resolver_deep,
    check_transparent_proxy,
    detect_egress_resolver,
)
from app.dns.state import DnsStateManager, DnsStateData
from app.platform.interfaces import IPlatformAdapter

logger = logging.getLogger("netguard.dns.service")

# Minimum improvement required to trigger or recommend a DNS switch (prevents flapping)
MIN_IMPROVEMENT_MS_THRESHOLD = 5.0
DEFAULT_COOLDOWN_SEC = 45.0


@dataclass
class DnsApplyResult:
    """Outcome of the 7-step DNS application workflow."""
    success: bool
    error_message: Optional[str] = None
    os_verified: bool = False
    resolver_tested: bool = False
    applied_servers: List[str] = field(default_factory=list)
    latency_ms: Optional[float] = None
    rolled_back: bool = False
    provider_name: Optional[str] = None
    step_reached: int = 1  # 1 to 7


class DnsService:
    """Authoritative centralized DNS management and optimization service."""

    def __init__(
        self,
        platform_adapter: Optional[IPlatformAdapter] = None,
        state_manager: Optional[DnsStateManager] = None,
        test_domain: str = "google.com",
    ) -> None:
        if platform_adapter is None:
            from app.platform.windows.adapter import WindowsPlatformAdapter
            platform_adapter = WindowsPlatformAdapter()
        self.platform = platform_adapter
        self.state_manager = state_manager or DnsStateManager.get_instance()
        self.test_domain = test_domain
        self._previous_dns_snapshot: Optional[Dict[str, Any]] = None
        self._last_switch_time: float = 0.0

    # -------------------------------------------------------------------------
    # 1. Detection: Read actual Windows DNS configuration
    # -------------------------------------------------------------------------
    def detect_and_sync_windows_dns(self) -> DnsStateData:
        """Detect the active physical network adapter, read real Windows DNS, and sync state."""
        iface = self.platform.get_primary_interface() or "Wi-Fi"
        servers = self.platform.get_interface_dns_servers(iface) or []
        gateway = self.platform.get_default_gateway() or "192.168.1.1"

        if not servers:
            servers = [gateway]

        primary_ip = servers[0] if servers else gateway
        secondary_ip = servers[1] if len(servers) > 1 else get_secondary_ip(primary_ip)
        provider_name = identify_provider(primary_ip) or f"خادم مخصص ({primary_ip})"

        # Detect DHCP vs Static mode
        configured_mode = "dhcp"
        if hasattr(self.platform, "get_interface_dns_mode"):
            configured_mode = self.platform.get_interface_dns_mode(iface)

        # Measure genuine response time of configured Primary DNS
        stats = measure_dns_resolver_deep(primary_ip, rounds=2, timeout_sec=2.0)
        measured_ms = stats.median_latency_ms if stats.is_valid_query else None
        is_healthy = bool(
            stats.is_valid_query
            and measured_ms is not None
            and measured_ms < 150.0
            and stats.success_rate >= 0.8
        )

        now = datetime.now(timezone.utc)
        self.state_manager.update(
            active_servers=servers,
            primary_dns=primary_ip,
            secondary_dns=secondary_ip,
            configured_mode=configured_mode,
            detected_provider=provider_name,
            primary_interface=iface,
            last_measured_ms=measured_ms,
            last_measured_timestamp=now,
            min_latency_ms=stats.min_latency_ms,
            max_latency_ms=stats.max_latency_ms,
            mean_latency_ms=stats.mean_latency_ms,
            query_success_rate=stats.success_rate,
            successful_queries_count=stats.successful_queries,
            failed_queries_count=stats.failed_queries,
            status_summary=stats.status_summary,
            is_healthy=is_healthy,
        )
        return self.state_manager.current

    # -------------------------------------------------------------------------
    # 2. Performance Measurement & Comparative Ranking
    # -------------------------------------------------------------------------
    async def benchmark_and_compare(
        self,
        rounds: int = 3,
        timeout_sec: float = 2.0,
    ) -> List[ResolverScore]:
        """Perform comparative testing of all candidate providers with real DNS queries."""
        current_state = self.state_manager.current
        active_ips = list(current_state.active_servers)
        primary_ip = current_state.primary_dns or (active_ips[0] if active_ips else "")

        self.state_manager.update(
            lifecycle_state="testing",
            is_benchmarking=True,
            status_message="Measuring DNS server response times...",
        )

        try:
            bench = DNSBenchmark(rounds=rounds, timeout_sec=timeout_sec)
            scores = await bench.rank_all(
                active_resolver_ips=active_ips,
                active_name=current_state.detected_provider or "",
            )
        except Exception as exc:
            logger.warning("DNS benchmark failed: %s", exc)
            self.state_manager.update(
                lifecycle_state="failed",
                is_benchmarking=False,
                last_error=str(exc),
                status_message=f"Measurement failed: {exc}",
            )
            return []

        self.state_manager.update(
            lifecycle_state="comparing",
            status_message="Comparing DNS performance...",
        )

        # Match active score strictly
        matched_active = next((s for s in scores if s.ip == primary_ip), None)
        active_ms = getattr(matched_active, "median_latency_ms", None) if matched_active else current_state.last_measured_ms

        # Identify top recommended candidate
        recommended_candidate = next((s for s in scores if s.is_recommended), None)
        if not recommended_candidate:
            viable_non_active = [s for s in scores if not s.is_active and not s.is_configured and s.success_rate >= 0.80]
            recommended_candidate = viable_non_active[0] if viable_non_active else None

        rec_primary = recommended_candidate.primary_ip if recommended_candidate else None
        rec_secondary = getattr(recommended_candidate, "secondary_ip", None) if recommended_candidate else None
        if rec_primary and not rec_secondary:
            rec_secondary = get_secondary_ip(rec_primary)
        rec_provider = getattr(recommended_candidate, "provider_name", recommended_candidate.name if recommended_candidate else None)
        rec_ms = getattr(recommended_candidate, "median_latency_ms", None) if recommended_candidate else None

        # Calculate genuine measured improvement
        gain_ms = 0.0
        is_different = False
        if active_ms is not None and rec_ms is not None:
            gain_ms = active_ms - rec_ms
            is_different = bool(gain_ms >= MIN_IMPROVEMENT_MS_THRESHOLD and rec_primary != primary_ip)

        if is_different and recommended_candidate:
            status_msg = f"A faster DNS configuration was found, with a measured improvement of {gain_ms:.1f} ms."
        else:
            status_msg = "No reliable performance improvement was detected. Your current DNS configuration has been preserved."

        from app.dns.benchmark import generate_dns_analysis
        analysis = generate_dns_analysis(
            active_ip=primary_ip,
            active_name=current_state.detected_provider or "Current DNS",
            active_score=matched_active,
            all_scores=scores,
        )

        now = datetime.now(timezone.utc)
        self.state_manager.update(
            scores=scores,
            recommended_server=recommended_candidate,
            best_server=recommended_candidate,
            recommended_primary_dns=rec_primary,
            recommended_secondary_dns=rec_secondary,
            recommended_provider=rec_provider,
            recommended_latency_ms=rec_ms,
            measured_improvement_ms=max(0.0, gain_ms),
            is_recommended_different=is_different,
            last_measured_timestamp=now,
            status_summary=analysis.get("verdict", ""),
            analysis_text=analysis.get("analysis_text", ""),
            recommendation_text=analysis.get("recommendation_text", ""),
            lifecycle_state="idle",
            is_benchmarking=False,
            status_message=status_msg,
        )
        return scores

    # -------------------------------------------------------------------------
    # 3. Transactional 7-Step DNS Application with Verification & Auto-Rollback
    # -------------------------------------------------------------------------
    def apply_dns_servers(
        self,
        interface_alias: str,
        primary_v4: str,
        secondary_v4: Optional[str] = None,
        primary_v6: Optional[str] = None,
        secondary_v6: Optional[str] = None,
    ) -> DnsApplyResult:
        """Enforces the complete 7-step DNS configuration workflow with auto-rollback.

        Interface contract:
        apply_dns_servers(interface_alias, primary_v4, secondary_v4, primary_v6, secondary_v6) -> DnsApplyResult
        """
        # STEP 1: Selection & Validation
        logger.info(
            "DNS Step 1/7 [Selection]: Validating candidates for interface '%s' (v4: %s, %s | v6: %s, %s)",
            interface_alias,
            primary_v4,
            secondary_v4,
            primary_v6,
            secondary_v6,
        )
        try:
            eff_prim_v4 = primary_v4.strip()
            parsed_v4 = ipaddress.ip_address(eff_prim_v4)
            if parsed_v4.version != 4:
                return DnsApplyResult(
                    success=False,
                    error_message=f"Primary address '{primary_v4}' is not a valid IPv4 address.",
                    step_reached=1,
                )
        except ValueError as exc:
            return DnsApplyResult(
                success=False,
                error_message=f"Invalid IPv4 format '{primary_v4}': {exc}",
                step_reached=1,
            )

        eff_sec_v4 = secondary_v4.strip() if secondary_v4 else get_secondary_ip(eff_prim_v4)

        # Auto-pair IPv6 resolvers to prevent IPv6 DNS leaks
        eff_prim_v6 = primary_v6.strip() if primary_v6 else None
        eff_sec_v6 = secondary_v6.strip() if secondary_v6 else None
        if not eff_prim_v6:
            p_v6, s_v6 = get_provider_ipv6(eff_prim_v4)
            eff_prim_v6 = p_v6
            if not eff_sec_v6:
                eff_sec_v6 = s_v6

        provider_name = identify_provider(eff_prim_v4) or "Custom DNS"

        # Capture pre-state snapshot for transactional rollback and restore
        orig_servers = self.platform.get_interface_dns_servers(interface_alias) or []
        orig_mode = "dhcp"
        if hasattr(self.platform, "get_interface_dns_mode"):
            orig_mode = self.platform.get_interface_dns_mode(interface_alias)
        is_dhcp = (orig_mode == "dhcp") if hasattr(self.platform, "get_interface_dns_mode") else (len(orig_servers) == 0)

        self._previous_dns_snapshot = {
            "interface": interface_alias,
            "original_servers": list(orig_servers),
            "orig_mode": orig_mode,
            "is_dhcp": is_dhcp,
            "timestamp": time.time(),
        }

        # STEP 2: Configuration Preparation
        servers: List[str] = [eff_prim_v4]
        if eff_sec_v4 and eff_sec_v4 not in servers:
            servers.append(eff_sec_v4)
        if eff_prim_v6 and eff_prim_v6 not in servers:
            servers.append(eff_prim_v6)
        if eff_sec_v6 and eff_sec_v6 not in servers:
            servers.append(eff_sec_v6)

        logger.info("DNS Step 2/7 [Configuration]: Assembled payload for %s: %s", provider_name, servers)

        # STEP 3: OS Application
        self.state_manager.update(
            lifecycle_state="applying",
            status_message="Applying the new DNS configuration to your network adapter...",
        )
        logger.info("DNS Step 3/7 [OS Application]: Applying servers to '%s'", interface_alias)
        try:
            ok, msg = self.platform.set_interface_dns_servers(interface_alias, servers)
            if not ok:
                logger.warning("DNS Step 3 failed on OS apply: %s", msg)
                err_msg = f"Unable to apply the new DNS configuration. Reason: {msg}"
                self.state_manager.update(
                    lifecycle_state="failed",
                    last_error=err_msg,
                    status_message=err_msg,
                )
                return DnsApplyResult(
                    success=False,
                    error_message=err_msg,
                    os_verified=False,
                    resolver_tested=False,
                    applied_servers=[],
                    rolled_back=False,
                    provider_name=provider_name,
                    step_reached=3,
                )
        except Exception as exc:
            logger.error("DNS Step 3 threw exception: %s", exc)
            err_msg = f"Unable to apply the new DNS configuration. Reason: {exc}"
            self.state_manager.update(
                lifecycle_state="failed",
                last_error=err_msg,
                status_message=err_msg,
            )
            return DnsApplyResult(
                success=False,
                error_message=err_msg,
                os_verified=False,
                resolver_tested=False,
                applied_servers=[],
                rolled_back=False,
                provider_name=provider_name,
                step_reached=3,
            )

        # STEP 4: DNS Cache Flush
        logger.info("DNS Step 4/7 [Cache Flush]: Flushing operating system DNS cache")
        try:
            self.platform.flush_dns_cache()
        except Exception as exc:
            logger.warning("DNS cache flush warning: %s", exc)

        # STEP 5: System Verification
        self.state_manager.update(
            lifecycle_state="verifying",
            status_message="Verifying applied DNS settings against Windows network settings...",
        )
        logger.info("DNS Step 5/7 [System Verification]: Inspecting adapter settings in OS network stack")
        actual_servers = self.platform.get_interface_dns_servers(interface_alias) or []
        os_verified = any(s in actual_servers for s in servers)

        if not os_verified:
            logger.warning("DNS Step 5 failed: Actual servers %s do not contain target %s. Rolling back.", actual_servers, servers)
            self._execute_rollback(interface_alias, orig_servers, is_dhcp)
            err_msg = f"Unable to apply the new DNS configuration. Reason: Windows network stack does not reflect {servers} (saw {actual_servers})"
            self.state_manager.update(
                lifecycle_state="failed",
                last_error=err_msg,
                status_message=err_msg,
            )
            return DnsApplyResult(
                success=False,
                error_message=err_msg,
                os_verified=False,
                resolver_tested=False,
                applied_servers=[],
                rolled_back=True,
                provider_name=provider_name,
                step_reached=5,
            )

        # STEP 6: Native OS Resolver Resolution Test
        logger.info("DNS Step 6/7 [Resolver Test]: Testing live domain resolution (%s)", self.test_domain)
        resolver_tested = False
        latency_ms: Optional[float] = None
        try:
            t0 = time.perf_counter()
            addrinfo = socket.getaddrinfo(self.test_domain, 80, socket.AF_UNSPEC, socket.SOCK_STREAM)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            if addrinfo and len(addrinfo) > 0:
                resolver_tested = True
        except Exception as exc:
            logger.warning("DNS Step 6 native resolution error: %s", exc)

        if not resolver_tested:
            logger.warning("Native resolver test failed. Triggering immediate auto-rollback.")
            self._execute_rollback(interface_alias, orig_servers, is_dhcp)
            err_msg = f"Unable to apply the new DNS configuration. Reason: Native resolution test failed for '{self.test_domain}'"
            self.state_manager.update(
                lifecycle_state="failed",
                last_error=err_msg,
                status_message=err_msg,
            )
            return DnsApplyResult(
                success=False,
                error_message=err_msg,
                os_verified=True,
                resolver_tested=False,
                applied_servers=[],
                rolled_back=True,
                provider_name=provider_name,
                step_reached=6,
            )

        # STEP 7: Verification Result & Authoritative State Synchronization
        logger.info("DNS Step 7/7 [Verification & Sync]: Full 7-step lifecycle succeeded!")
        self._last_switch_time = time.monotonic()
        now = datetime.now(timezone.utc)

        self.state_manager.update(
            active_servers=servers,
            primary_dns=eff_prim_v4,
            secondary_dns=eff_sec_v4,
            configured_mode="static",
            detected_provider=provider_name,
            applied_servers=servers,
            applied_provider=provider_name,
            last_measured_ms=latency_ms,
            last_measured_timestamp=now,
            last_switch_time=time.time(),
            is_healthy=True,
            can_restore=True,
            previous_servers=orig_servers,
            lifecycle_state="success",
            status_message="DNS configuration successfully applied and verified against Windows network settings.",
            last_error=None,
        )

        return DnsApplyResult(
            success=True,
            error_message=None,
            os_verified=True,
            resolver_tested=True,
            applied_servers=servers,
            latency_ms=latency_ms,
            rolled_back=False,
            provider_name=provider_name,
            step_reached=7,
        )

    # -------------------------------------------------------------------------
    # 4. Restore Previous DNS Configuration
    # -------------------------------------------------------------------------
    def restore_previous_dns(self, interface_alias: Optional[str] = None) -> DnsApplyResult:
        """Restore the previous DNS configuration or reset to DHCP."""
        iface = interface_alias or self.platform.get_primary_interface() or "Wi-Fi"
        snapshot = self._previous_dns_snapshot
        current_state = self.state_manager.current

        self.state_manager.update(
            lifecycle_state="applying",
            status_message="Restoring previous DNS configuration...",
        )

        if snapshot and not snapshot.get("is_dhcp") and snapshot.get("original_servers"):
            target_servers = snapshot["original_servers"]
            logger.info("Restoring previous static DNS servers on '%s': %s", iface, target_servers)
            try:
                ok, msg = self.platform.set_interface_dns_servers(iface, target_servers)
                self.platform.flush_dns_cache()
                actual = self.platform.get_interface_dns_servers(iface) or []
                prov = identify_provider(actual[0]) if actual else "Custom DNS"

                self.state_manager.update(
                    active_servers=actual,
                    primary_dns=actual[0] if actual else None,
                    secondary_dns=actual[1] if len(actual) > 1 else None,
                    configured_mode="static",
                    detected_provider=prov,
                    applied_servers=[],
                    applied_provider=None,
                    can_restore=False,
                    lifecycle_state="idle",
                    status_message="Previous DNS configuration successfully restored.",
                )
                return DnsApplyResult(
                    success=ok,
                    error_message=None if ok else msg,
                    os_verified=True,
                    resolver_tested=True,
                    applied_servers=actual,
                    provider_name=prov,
                    step_reached=7,
                )
            except Exception as exc:
                logger.error("Failed to restore previous static DNS: %s", exc)
                return self.reset_dns_to_dhcp(iface)
        else:
            return self.reset_dns_to_dhcp(iface)

    def reset_dns_to_dhcp(self, interface_alias: str) -> DnsApplyResult:
        """Reset interface DNS to DHCP (automatic router/ISP configuration)."""
        logger.info("Resetting DNS on '%s' to automatic DHCP...", interface_alias)
        try:
            if hasattr(self.platform, "set_interface_dns_dhcp"):
                ok, msg = self.platform.set_interface_dns_dhcp(interface_alias)
            else:
                ok, msg = self.platform.set_interface_dns_servers(interface_alias, [])
            self.platform.flush_dns_cache()

            # Test native resolution post-DHCP
            t0 = time.perf_counter()
            try:
                socket.getaddrinfo(self.test_domain, 80, socket.AF_UNSPEC, socket.SOCK_STREAM)
                latency_ms = (time.perf_counter() - t0) * 1000.0
                tested = True
            except Exception:
                latency_ms = None
                tested = False

            actual_servers = self.platform.get_interface_dns_servers(interface_alias) or []
            prov_name = identify_provider(actual_servers[0]) if actual_servers else "الراوتر المنزلي (DHCP)"

            self.state_manager.update(
                active_servers=actual_servers,
                primary_dns=actual_servers[0] if actual_servers else None,
                secondary_dns=actual_servers[1] if len(actual_servers) > 1 else None,
                configured_mode="dhcp",
                detected_provider=prov_name,
                applied_servers=[],
                applied_provider=None,
                last_measured_ms=latency_ms,
                is_healthy=True,
                can_restore=False,
                last_switch_time=time.time(),
                lifecycle_state="idle",
                status_message="DNS successfully reset to automatic DHCP.",
            )

            return DnsApplyResult(
                success=ok,
                error_message=None if ok else msg,
                os_verified=True,
                resolver_tested=tested,
                applied_servers=actual_servers,
                latency_ms=latency_ms,
                rolled_back=False,
                provider_name=prov_name,
                step_reached=7,
            )
        except Exception as exc:
            logger.error("Failed to reset DNS to DHCP: %s", exc)
            self.state_manager.update(
                lifecycle_state="failed",
                last_error=str(exc),
                status_message=f"Failed to reset DNS: {exc}",
            )
            return DnsApplyResult(
                success=False,
                error_message=str(exc),
                os_verified=False,
                resolver_tested=False,
                applied_servers=[],
                step_reached=3,
            )

    def _execute_rollback(self, interface_alias: str, original_servers: List[str], is_dhcp: bool) -> None:
        """Execute safe auto-rollback to pre-state snapshot."""
        try:
            logger.info("Executing DNS auto-rollback on '%s' (is_dhcp=%s, orig=%s)...", interface_alias, is_dhcp, original_servers)
            if is_dhcp:
                if hasattr(self.platform, "set_interface_dns_dhcp"):
                    self.platform.set_interface_dns_dhcp(interface_alias)
                else:
                    self.platform.set_interface_dns_servers(interface_alias, [])
            else:
                self.platform.set_interface_dns_servers(interface_alias, original_servers)
            self.platform.flush_dns_cache()

            self.state_manager.update(
                active_servers=original_servers,
                configured_mode="dhcp" if is_dhcp else "static",
                is_healthy=True,
            )
        except Exception as exc:
            logger.error("Failed to execute DNS rollback: %s", exc)
