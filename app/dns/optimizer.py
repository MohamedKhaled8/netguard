"""Intelligent DNS Optimizer and Failover Manager."""

from __future__ import annotations
import logging
import time
import uuid
from typing import List, Optional, Any
from app.core.events.bus import EventBus
from app.core.models.metrics import ActionExecutionRecord, ActionExecutionStatus, RiskLevel
from app.dns.benchmark import DNSBenchmark, ResolverScore
from app.platform.interfaces import IPlatformAdapter
from app.remediation.orchestrator import RemediationOrchestrator
from app.remediation.actions.switch_dns import SwitchDNSResolverAction

logger = logging.getLogger("netguard.dns.optimizer")


class DNSOptimizer:
    """Manages continuous DNS health evaluation, ranking, and autonomous failover."""

    def __init__(
        self,
        platform_adapter: IPlatformAdapter,
        event_bus: EventBus,
        orchestrator: Optional[RemediationOrchestrator] = None,
        settings: Optional[Any] = None,
        cooldown_sec: float = 900.0,
        session_tracker: Optional[Any] = None,
    ) -> None:
        self.platform = platform_adapter
        self.event_bus = event_bus
        self.orchestrator = orchestrator
        self.settings = settings
        self.cooldown_sec = cooldown_sec
        self.session_tracker = session_tracker
        self.benchmark = DNSBenchmark()
        self._ranked_cache: List[ResolverScore] = []
        self._last_switch_time: float = 0.0

    async def evaluate_and_rank(self) -> List[ResolverScore]:
        """Runs benchmark across all resolvers directly and updates rankings."""
        logger.info("Running DNS benchmark ranking across candidate resolvers...")
        ranked = await self.benchmark.rank_all()
        self._ranked_cache = ranked
        if ranked:
            best = ranked[0]
            logger.info("Top DNS resolver: %s (%s) Score: %.1f (Median: %.1fms)", best.name, best.ip, best.composite_score, best.median_latency_ms)
            await self.event_bus.publish("dns.benchmark.completed", [r.model_dump(mode="json") for r in ranked])
        return ranked

    async def auto_optimize_dns(self) -> Optional[ResolverScore]:
        """Checks if current DNS is sub-optimal and switches to the best verified resolver (Item B7)."""
        allow_switch = True
        if self.settings and hasattr(self.settings, "get_policy"):
            allow_switch = self.settings.get_policy("auto_switch_dns", True)
        if not allow_switch:
            logger.info("DNS auto-switch suppressed by user settings policy (auto_switch_dns=False)")
            return None

        # 1. Meeting protection policy (Item B7 / Stage D)
        if hasattr(self, "session_tracker") and self.session_tracker:
            if hasattr(self.session_tracker, "has_active_meeting") and self.session_tracker.has_active_meeting():
                logger.info("Meeting is active. Suppressing DNS auto-switch (meeting protection policy).")
                return None

        # 2. Cooldown policy: at least 15 minutes (900s) between switches
        now = time.time()
        if (now - self._last_switch_time) < self.cooldown_sec:
            logger.info("DNS auto-switch cooldown active (%.1fs remaining). Skipping.", self.cooldown_sec - (now - self._last_switch_time))
            return None

        ranked = await self.evaluate_and_rank()
        if not ranked:
            return None

        best_resolver = ranked[0]
        if best_resolver.composite_score < 40.0:
            logger.warning("All candidate DNS resolvers scored poorly (best: %.1f). Skipping switch.", best_resolver.composite_score)
            return None

        # 3. Candidate packet loss gate: must have 0% packet loss (Item B7)
        if getattr(best_resolver, "failure_rate", 0.0) > 0.0 or getattr(best_resolver, "success_rate", 1.0) < 1.0:
            logger.warning("Candidate DNS resolver %s has packet loss (>0%%). Skipping switch for safety.", best_resolver.name)
            return None

        iface = self.platform.get_primary_interface() or "Wi-Fi"
        current_servers = self.platform.get_interface_dns_servers(iface) or []

        # 4. Hysteresis threshold: only switch if improvement is at least 15 ms (Item B7)
        from app.dns.detector import measure_dns_latency
        curr_ip = current_servers[0] if current_servers else (self.platform.get_default_gateway() or "192.168.1.1")
        curr_ms = measure_dns_latency(curr_ip)
        if curr_ms is not None:
            diff_ms = curr_ms - best_resolver.median_latency_ms
            if diff_ms < 15.0:
                logger.info("DNS improvement delta is %.1f ms (< 15.0 ms hysteresis threshold). Skipping switch.", diff_ms)
                return None

        # Check secondary resolver from a different provider for resilience
        second_best = next((r for r in ranked[1:] if r.ip.split(".")[0] != best_resolver.ip.split(".")[0]), ranked[1] if len(ranked) > 1 else None)
        target_ips = [best_resolver.ip]
        if second_best:
            target_ips.append(second_best.ip)

        logger.info("Optimal resolver pair selected: %s", target_ips)

        try:
            if not current_servers or current_servers[0] != best_resolver.ip:
                logger.info("Autonomously applying top-ranked DNS resolver %s on %s...", target_ips, iface)
                ok, msg = self.platform.set_interface_dns_servers(iface, target_ips)
                self.platform.flush_dns_cache()

                # 5. Live query verification immediately post-switch (Item B7)
                verify_ms = measure_dns_latency(target_ips[0], timeout_sec=2.5)
                if verify_ms is None:
                    logger.warning("Post-switch DNS verification failed for %s. Reverting within 3s...", target_ips[0])
                    self.platform.set_interface_dns_servers(iface, current_servers)
                    self.platform.flush_dns_cache()

                    if self.orchestrator and hasattr(self.orchestrator, "audit_repo"):
                        rec = ActionExecutionRecord(
                            id=str(uuid.uuid4()),
                            action_id="switch_dns_failed_rollback",
                            action_name=f"فشل التحقق من {best_resolver.name} — تم التراجع فوراً",
                            risk_level=RiskLevel.LEVEL_2_CONTROLLED,
                            trigger_diagnosis_id="autonomous_optimizer",
                            pre_remedy_metrics={"interface": iface, "target_servers": target_ips},
                            post_remedy_metrics={"reverted_to": current_servers},
                            status=ActionExecutionStatus.FAILED,
                            execution_duration_ms=50.0,
                            verification_duration_ms=10.0,
                            error_message="Verification query timed out; reverted to prior configuration.",
                            rollback_performed=True,
                        )
                        self.orchestrator.audit_repo.save(rec)
                    return None

                self._last_switch_time = time.time()
                from app.dns.state import DnsStateManager
                DnsStateManager.get_instance().update(
                    active_servers=target_ips,
                    detected_provider=best_resolver.name,
                    last_measured_ms=verify_ms,
                    is_healthy=True,
                    last_switch_time=self._last_switch_time,
                )

                if self.orchestrator and hasattr(self.orchestrator, "audit_repo"):
                    record = ActionExecutionRecord(
                        id=str(uuid.uuid4()),
                        action_id="switch_dns_resolver",
                        action_name=f"تحويل تلقائي إلى {best_resolver.name} ({best_resolver.ip})",
                        risk_level=RiskLevel.LEVEL_2_CONTROLLED,
                        trigger_diagnosis_id="autonomous_optimizer",
                        pre_remedy_metrics={
                            "interface": iface,
                            "original_servers": list(current_servers),
                            "is_dhcp": len(current_servers) == 0,
                        },
                        post_remedy_metrics={"active_servers": target_ips, "status": msg, "verified_ms": verify_ms},
                        status=ActionExecutionStatus.SUCCEEDED if ok else ActionExecutionStatus.FAILED,
                        execution_duration_ms=45.0,
                        verification_duration_ms=12.0,
                        error_message=None if ok else msg,
                        rollback_performed=False,
                    )
                    self.orchestrator.audit_repo.save(record)

                await self.event_bus.publish("dns.switched", {
                    "interface": iface,
                    "previous_servers": current_servers,
                    "target_servers": target_ips,
                    "provider": best_resolver.name,
                    "latency_ms": verify_ms,
                    "status": "applied" if ok else "failed",
                    "message": msg,
                })
        except Exception as exc:
            logger.error("Failed to autonomously switch DNS: %s", exc)

        return best_resolver

    @property
    def latest_rankings(self) -> List[ResolverScore]:
        return list(self._ranked_cache)
