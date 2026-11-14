"""Recheck Gateway Connectivity Action (Level 1 Low Risk)."""

from __future__ import annotations
import asyncio
from typing import Any, Dict, Tuple
from app.core.models.metrics import RiskLevel
from app.platform.interfaces import IPlatformAdapter
from app.remediation.registry import RemediationAction


class RecheckGatewayAction(RemediationAction):
    """Executes an immediate multi-sample probe burst to verify whether a gateway drop is transient."""

    def __init__(self) -> None:
        super().__init__(
            action_id="recheck_gateway",
            name="Recheck Gateway Connectivity",
            description="Performs immediate multi-probe verification to distinguish transient packet drops from genuine router outages.",
            risk_level=RiskLevel.LEVEL_1_LOW,
            supported_os=["win32", "linux"],
            timeout_sec=4.0,
            cooldown_sec=10.0,
            max_retries=3,
        )

    def check_preconditions(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Tuple[bool, str]:
        gw = platform.get_default_gateway()
        if not gw:
            return False, "No default gateway configured"
        return True, f"Gateway {gw} configured"

    async def execute(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Any:
        loop = asyncio.get_running_loop()
        gw = platform.get_default_gateway()

        # Multi-sample probe burst (3 pings)
        latencies = []
        for _ in range(3):
            ok, lat = await loop.run_in_executor(None, platform.ping, gw, 1.0)
            if ok:
                latencies.append(lat)
            await asyncio.sleep(0.2)

        return {"gateway": gw, "successful_pings": len(latencies), "latencies": latencies}

    async def verify(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str, Dict[str, Any]]:
        success_count = pre_state.get("successful_pings", 0) if pre_state else 0
        if success_count >= 1:
            return True, f"Gateway verified responsive ({success_count}/3 probe replies)", pre_state
        return False, "Gateway remains unresponsive after probe burst", pre_state or {}

    async def rollback(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str]:
        return True, "No rollback needed for read-only connectivity recheck"
