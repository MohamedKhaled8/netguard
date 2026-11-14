"""Renew IP Lease Action (Level 2 Controlled Risk)."""

from __future__ import annotations
import asyncio
import time
from typing import Any, Dict, Tuple
from app.core.models.metrics import RiskLevel
from app.platform.interfaces import IPlatformAdapter
from app.remediation.registry import RemediationAction


class RenewIPLeaseAction(RemediationAction):
    """Refreshes DHCP lease and network stack configuration for the active interface."""

    def __init__(self) -> None:
        super().__init__(
            action_id="renew_ip_lease",
            name="Release and Renew IP Lease",
            description="Releases and re-acquires DHCP lease from local gateway/router.",
            risk_level=RiskLevel.LEVEL_2_CONTROLLED,
            supported_os=["win32"],
            timeout_sec=25.0,
            cooldown_sec=90.0,
            max_retries=1,
        )

    def check_preconditions(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Tuple[bool, str]:
        iface = context.get("interface_name") or platform.get_primary_interface()
        if not iface:
            return False, "No active primary network interface detected"
        return True, f"Interface '{iface}' ready for DHCP renewal"

    async def execute(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Any:
        loop = asyncio.get_running_loop()
        iface = context.get("interface_name") or platform.get_primary_interface()

        pre_state = {
            "interface_name": iface,
            "timestamp": time.time(),
        }

        ok, msg = await loop.run_in_executor(None, platform.renew_ip_lease, iface)
        if not ok:
            raise RuntimeError(f"DHCP renewal failed on {iface}: {msg}")
        return pre_state

    async def verify(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str, Dict[str, Any]]:
        # Verification: test gateway ping
        loop = asyncio.get_running_loop()
        gw = platform.get_default_gateway()
        if not gw:
            return False, "No gateway acquired after DHCP renewal", {}

        ok, lat = await loop.run_in_executor(None, platform.ping, gw, 2.0)
        if ok:
            return True, f"Gateway {gw} reachable post-renewal ({lat:.1f}ms)", {"gateway": gw, "latency_ms": lat}
        return False, f"Gateway {gw} unresponsive post-renewal", {"gateway": gw}

    async def rollback(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str]:
        return True, "DHCP renewal state is managed by OS DHCP client; rollback complete"
