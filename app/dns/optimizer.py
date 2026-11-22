"""Intelligent DNS Optimizer and Failover Manager."""

from __future__ import annotations
import logging
import time
import uuid
from dataclasses import dataclass
from typing import List, Optional, Any
from app.core.events.bus import EventBus
from app.core.models.metrics import ActionExecutionRecord, ActionExecutionStatus, RiskLevel
from app.dns.benchmark import DNSBenchmark, ResolverScore
from app.platform.interfaces import IPlatformAdapter
from app.remediation.orchestrator import RemediationOrchestrator
from app.remediation.actions.switch_dns import SwitchDNSResolverAction

logger = logging.getLogger("netguard.dns.optimizer")

DEFAULT_MIN_IMPROVEMENT_MS = 1.0

REASON_MESSAGES = {
    "no_candidates": "لا توجد نتائج قياس موثوقة حالياً.",
    "policy_disabled": "التحويل التلقائي لـ DNS موقف من الإعدادات.",
    "meeting": "مكالمة نشطة — تأجيل تغيير DNS حتى تنتهي.",
    "cooldown": "تم تغيير DNS مؤخراً. انتظار فترة الاستقرار قبل تحويل جديد.",
    "not_elevated": "تعذر تغيير DNS: التطبيق يحتاج صلاحيات المدير لتعديل إعداد ويندوز.",
    "already_optimal": "الخادم الحالي هو الأسرع أو مساوٍ له ضمن القياس.",
    "insufficient_gain": "الفرق أقل من 1 مللي ثانية، داخل هامش القياس.",
    "packet_loss": "الخادم الأسرع غير مستقر (فقد استعلامات). لن يتم التحويل.",
    "poor_score": "كل الخوادم المرشحة ضعيفة. الإبقاء على الإعداد الحالي.",
    "apply": "سيتم التحويل إلى الخادم الأسرع بعد التحقق.",
    "os_apply_failed": "ويندوز رفض تغيير DNS. الإعداد الحالي لم يتغير.",
}


@dataclass
class DnsSwitchDecision:
    should_switch: bool
    reason_code: str
    best: Optional[ResolverScore]
    current_ip: Optional[str]
    current_ms: Optional[float]
    gain_ms: float
    message_ar: str


def latency_for_ip(ranked: List[ResolverScore], ip: Optional[str]) -> Optional[float]:
    """Use the same benchmark row as ranking so current vs best is comparable."""
    if not ip:
        return None
    for score in ranked:
        if score.ip == ip:
            ms = score.median_latency_ms or score.mean_latency_ms
            return float(ms) if ms else None
    return None


def select_best_resolver(ranked: List[ResolverScore]) -> Optional[ResolverScore]:
    """First reachable ranked resolver, including the currently active one."""
    for score in ranked:
        if getattr(score, "is_ip_reachable", True) and score.success_rate > 0.0:
            return score
    return ranked[0] if ranked else None


def _is_switch_safe(score: ResolverScore) -> bool:
    return (
        getattr(score, "is_ip_reachable", True)
        and score.success_rate >= 1.0
        and getattr(score, "failure_rate", 0.0) <= 0.0
        and getattr(score, "composite_score", 100.0) >= 40.0
    )


def decide_auto_switch(
    ranked: List[ResolverScore],
    current_servers: List[str],
    *,
    policy_enabled: bool = True,
    meeting_active: bool = False,
    cooldown_remaining: float = 0.0,
    elevated: bool = True,
    min_improvement_ms: float = DEFAULT_MIN_IMPROVEMENT_MS,
    current_ms_fallback: Optional[float] = None,
) -> DnsSwitchDecision:
    """Pure policy: switch only when a safer resolver is meaningfully faster."""
    current_ip = current_servers[0] if current_servers else None
    display_best = select_best_resolver(ranked)

    def _out(should: bool, code: str, best: Optional[ResolverScore], current_ms: Optional[float], gain: float) -> DnsSwitchDecision:
        return DnsSwitchDecision(
            should_switch=should,
            reason_code=code,
            best=best,
            current_ip=current_ip,
            current_ms=current_ms,
            gain_ms=gain,
            message_ar=REASON_MESSAGES.get(code, code),
        )

    if not policy_enabled:
        return _out(False, "policy_disabled", display_best, latency_for_ip(ranked, current_ip), 0.0)
    if meeting_active:
        return _out(False, "meeting", display_best, latency_for_ip(ranked, current_ip), 0.0)
    if cooldown_remaining > 0:
        return _out(False, "cooldown", display_best, latency_for_ip(ranked, current_ip), 0.0)
    if not ranked:
        return _out(False, "no_candidates", None, None, 0.0)
    if not elevated:
        return _out(False, "not_elevated", display_best, latency_for_ip(ranked, current_ip), 0.0)

    current_ms = latency_for_ip(ranked, current_ip)
    if current_ms is None:
        current_ms = current_ms_fallback

    safe = [s for s in ranked if _is_switch_safe(s)]
    if not safe:
        code = "packet_loss" if ranked else "poor_score"
        if ranked and ranked[0].composite_score < 40.0:
            code = "poor_score"
        return _out(False, code, display_best, current_ms, 0.0)

    best = safe[0]
    if current_ip and best.ip == current_ip:
        return _out(False, "already_optimal", best, current_ms, 0.0)

    best_ms = float(best.median_latency_ms or best.mean_latency_ms or 0.0)
    if current_ms is None:
        return _out(False, "insufficient_gain", best, None, 0.0)

    gain = float(current_ms) - best_ms
    if gain < min_improvement_ms:
        code = "already_optimal" if gain <= 0.5 else "insufficient_gain"
        return _out(False, code, best, current_ms, gain)

    return _out(True, "apply", best, current_ms, gain)


class DNSOptimizer:
    """Manages continuous DNS health evaluation, ranking, and autonomous failover."""

    def __init__(
        self,
        platform_adapter: IPlatformAdapter,
        event_bus: EventBus,
        orchestrator: Optional[RemediationOrchestrator] = None,
        settings: Optional[Any] = None,
        cooldown_sec: float = 30.0,
        session_tracker: Optional[Any] = None,
        min_improvement_ms: Optional[float] = None,
    ) -> None:
        self.platform = platform_adapter
        self.event_bus = event_bus
        self.orchestrator = orchestrator
        self.settings = settings
        self.cooldown_sec = cooldown_sec
        self.session_tracker = session_tracker
        self.min_improvement_ms = (
            min_improvement_ms if min_improvement_ms is not None else DEFAULT_MIN_IMPROVEMENT_MS
        )
        self.benchmark = DNSBenchmark()
        self._ranked_cache: List[ResolverScore] = []
        self._last_switch_time: float = 0.0
        self.last_decision: Optional[DnsSwitchDecision] = None

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

    async def auto_optimize_dns(self, ranked: Optional[List[ResolverScore]] = None) -> Optional[ResolverScore]:
        """Checks if current DNS is sub-optimal and switches to the best verified resolver (Item B7)."""
        allow_switch = True
        if self.settings and hasattr(self.settings, "get_policy"):
            allow_switch = bool(self.settings.get_policy("auto_switch_dns", True))
        meeting_active = False
        if self.session_tracker:
            checker = getattr(self.session_tracker, "has_active_meeting", None) or getattr(
                self.session_tracker, "is_critical_meeting_active", None
            )
            if callable(checker):
                meeting_active = bool(checker())

        now = time.monotonic()
        cooldown_remaining = max(0.0, self.cooldown_sec - (now - self._last_switch_time))
        if self._last_switch_time <= 0.0:
            cooldown_remaining = 0.0

        if not allow_switch or meeting_active or cooldown_remaining > 0.0:
            self.last_decision = decide_auto_switch(
                ranked or [],
                [],
                policy_enabled=allow_switch,
                meeting_active=meeting_active,
                cooldown_remaining=cooldown_remaining,
            )
            logger.info("DNS auto-switch skipped (%s): %s", self.last_decision.reason_code, self.last_decision.message_ar)
            return None

        if ranked is None:
            ranked = await self.evaluate_and_rank()
        else:
            self._ranked_cache = list(ranked)

        iface = self.platform.get_primary_interface() or "Wi-Fi"
        current_servers = self.platform.get_interface_dns_servers(iface) or []
        elevated = True
        if hasattr(self.platform, "is_elevated"):
            try:
                elevated = bool(self.platform.is_elevated())
            except Exception:
                elevated = True

        from app.dns.detector import measure_dns_latency, get_provider_ipv6
        current_ip = current_servers[0] if current_servers else None
        fallback_ms = None
        if current_ip and latency_for_ip(ranked or [], current_ip) is None:
            fallback_ms = measure_dns_latency(current_ip)

        decision = decide_auto_switch(
            ranked or [],
            current_servers,
            policy_enabled=True,
            meeting_active=False,
            cooldown_remaining=0.0,
            elevated=elevated,
            min_improvement_ms=self.min_improvement_ms,
            current_ms_fallback=fallback_ms,
        )
        self.last_decision = decision
        if not decision.should_switch or decision.best is None:
            logger.info("DNS auto-switch skipped (%s): %s", decision.reason_code, decision.message_ar)
            return None

        best_resolver = decision.best

        # Check secondary resolver from a different provider for resilience
        second_best = next((r for r in ranked[1:] if r.ip.split(".")[0] != best_resolver.ip.split(".")[0]), ranked[1] if len(ranked) > 1 else None)
        target_ips = [best_resolver.ip]
        if second_best:
            target_ips.append(second_best.ip)

        # Dual-stack IPv6 pairing (Item F6)
        p_v6, s_v6 = get_provider_ipv6(best_resolver.ip)
        all_targets = list(target_ips)
        if p_v6 and p_v6 not in all_targets:
            all_targets.append(p_v6)
        if s_v6 and s_v6 not in all_targets:
            all_targets.append(s_v6)

        logger.info("Optimal resolver set selected (dual-stack): %s", all_targets)

        try:
            if not current_servers or current_servers[0] != best_resolver.ip:
                logger.info("Autonomously applying top-ranked DNS resolver %s on %s...", all_targets, iface)
                ok, msg = self.platform.set_interface_dns_servers(iface, all_targets)
                actual = self.platform.get_interface_dns_servers(iface) or []
                applied = ok and best_resolver.ip in actual
                if not applied:
                    logger.warning("DNS OS apply did not stick (%s). Saw %s", msg, actual)
                    if actual and actual != current_servers:
                        self.platform.set_interface_dns_servers(iface, current_servers)
                    self.last_decision = DnsSwitchDecision(
                        should_switch=False,
                        reason_code="os_apply_failed",
                        best=best_resolver,
                        current_ip=current_servers[0] if current_servers else None,
                        current_ms=decision.current_ms,
                        gain_ms=decision.gain_ms,
                        message_ar=REASON_MESSAGES["os_apply_failed"],
                    )
                    return None
                self.platform.flush_dns_cache()

                # 5. Live query verification immediately post-switch (Item B7)
                verify_ms = measure_dns_latency(target_ips[0], timeout_sec=2.5)
                if verify_ms is None:
                    logger.warning("Post-switch DNS verification failed for %s. Reverting within 3s...", target_ips[0])
                    self.platform.set_interface_dns_servers(iface, current_servers)
                    self.platform.flush_dns_cache()

                    from app.dns.state import DnsStateManager
                    DnsStateManager.get_instance().update(
                        active_servers=current_servers,
                        is_healthy=True,
                    )

                    audit_repo = getattr(self.orchestrator, "audit", None) or getattr(self.orchestrator, "audit_repo", None)
                    if audit_repo:
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
                        audit_repo.save(rec)
                    return None

                self._last_switch_time = time.monotonic()
                from app.dns.state import DnsStateManager
                DnsStateManager.get_instance().update(
                    active_servers=target_ips,
                    detected_provider=best_resolver.name,
                    last_measured_ms=verify_ms,
                    is_healthy=True,
                    last_switch_time=time.time(),
                )

                audit_repo = getattr(self.orchestrator, "audit", None) or getattr(self.orchestrator, "audit_repo", None)
                if audit_repo:
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
                    audit_repo.save(record)

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
