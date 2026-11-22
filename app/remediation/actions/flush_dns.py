"""Flush DNS Cache Action (Level 1 Low Risk)."""

from __future__ import annotations
import asyncio
import time
from typing import Any, Dict, Tuple
from app.core.models.metrics import RiskLevel, ActionClassification
from app.platform.interfaces import IPlatformAdapter
from app.remediation.registry import RemediationAction


class FlushDNSCacheAction(RemediationAction):
    """Flushes operating system local DNS resolver cache to clear poisoned or stale records."""

    def __init__(self) -> None:
        super().__init__(
            action_id="flush_dns_cache",
            name="Flush DNS Resolver Cache",
            description="Flushes the OS DNS resolver cache to clear stale or corrupt mappings.",
            risk_level=RiskLevel.LEVEL_1_LOW,
            supported_os=["win32", "linux"],
            timeout_sec=5.0,
            cooldown_sec=15.0,
            max_retries=2,
            action_classification=ActionClassification.CORRECTIVE_ACTION,
        )

    def check_preconditions(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Tuple[bool, str]:
        iface = platform.get_primary_interface()
        if not iface:
            return False, "No active primary network interface detected"
        return True, "Preconditions satisfied"

    async def execute(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Any:
        loop = asyncio.get_running_loop()
        ok, msg = await loop.run_in_executor(None, platform.flush_dns_cache)
        if not ok:
            raise RuntimeError(f"Flush DNS failed: {msg}")
        return {"action": "flush_dns", "executed_at": time.time()}

    async def verify(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str, Dict[str, Any]]:
        # Verification: resolve domain
        import dns.resolver
        loop = asyncio.get_running_loop()

        def _test_resolve():
            res = dns.resolver.Resolver()
            res.lifetime = 2.0
            res.timeout = 2.0
            t0 = time.perf_counter()
            ans = res.resolve("cloudflare.com", "A")
            return (time.perf_counter() - t0) * 1000.0, [r.to_text() for r in ans]

        try:
            latency_ms, ips = await loop.run_in_executor(None, _test_resolve)
            return True, f"DNS cache flush verified (resolution: {latency_ms:.1f}ms)", {"resolved_ips": ips, "latency_ms": latency_ms}
        except Exception as exc:
            return False, f"DNS verification failed post-flush: {exc}", {"error": str(exc)}

    async def rollback(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str]:
        # Flushing cache has no adverse state to roll back
        return True, "No rollback needed for cache flush"
