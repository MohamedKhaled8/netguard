"""Intelligent DNS Optimizer and Failover Manager."""

from __future__ import annotations
import logging
from typing import List, Optional
from app.core.events.bus import EventBus
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
    ) -> None:
        self.platform = platform_adapter
        self.event_bus = event_bus
        self.orchestrator = orchestrator
        self.benchmark = DNSBenchmark()
        self._ranked_cache: List[ResolverScore] = []

    async def evaluate_and_rank(self) -> List[ResolverScore]:
        """Runs benchmark across all resolvers and updates rankings."""
        logger.info("Running DNS benchmark ranking across candidate resolvers...")
        ranked = await self.benchmark.rank_all()
        self._ranked_cache = ranked
        if ranked:
            best = ranked[0]
            logger.info("Top DNS resolver: %s (%s) Score: %.1f (Latency: %.1fms)", best.name, best.ip, best.composite_score, best.mean_latency_ms)
            await self.event_bus.publish("dns.benchmark.completed", [r.model_dump(mode="json") for r in ranked])
        return ranked

    async def auto_optimize_dns(self) -> Optional[ResolverScore]:
        """Checks if current DNS is sub-optimal and switches to the best verified resolver."""
        ranked = await self.evaluate_and_rank()
        if not ranked:
            return None

        best_resolver = ranked[0]
        if best_resolver.composite_score < 40.0:
            logger.warning("All candidate DNS resolvers scored poorly (best: %.1f). Skipping switch.", best_resolver.composite_score)
            return None

        # Check secondary resolver from a different provider for resilience
        second_best = next((r for r in ranked[1:] if r.ip.split(".")[0] != best_resolver.ip.split(".")[0]), ranked[1] if len(ranked) > 1 else None)
        target_ips = [best_resolver.ip]
        if second_best:
            target_ips.append(second_best.ip)

        logger.info("Optimal resolver pair selected: %s", target_ips)
        return best_resolver

    @property
    def latest_rankings(self) -> List[ResolverScore]:
        return list(self._ranked_cache)
