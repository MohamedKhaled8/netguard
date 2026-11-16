"""Switch DNS Resolver Action with Automatic Pre-State Rollback (Level 2 Controlled Risk)."""

from __future__ import annotations
import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple
from app.core.models.metrics import RiskLevel
from app.platform.interfaces import IPlatformAdapter
from app.remediation.registry import RemediationAction


class SwitchDNSResolverAction(RemediationAction):
    """Switches primary interface DNS servers to known-good public resolvers with transaction rollback."""

    def __init__(self, fallback_resolvers: Optional[List[str]] = None) -> None:
        super().__init__(
            action_id="switch_dns_resolver",
            name="Switch Interface DNS Resolver",
            description="Replaces unresponsive local or ISP DNS servers with verified public resolvers (1.1.1.1, 8.8.8.8).",
            risk_level=RiskLevel.LEVEL_2_CONTROLLED,
            supported_os=["win32", "linux"],
            timeout_sec=10.0,
            cooldown_sec=45.0,
            max_retries=2,
        )
        self.fallback_resolvers = fallback_resolvers or ["1.1.1.1", "8.8.8.8"]

    def check_preconditions(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Tuple[bool, str]:
        if not platform.is_elevated():
            return False, "Cannot modify interface DNS: Requires Administrator privileges. NetGuard is running in unprivileged user mode."

        iface = context.get("interface_name") or platform.get_primary_interface()
        if not iface:
            return False, "Cannot switch DNS: No primary network adapter detected"
        return True, f"Primary interface '{iface}' detected"

    async def execute(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Any:
        loop = asyncio.get_running_loop()
        iface = context.get("interface_name") or platform.get_primary_interface()
        target_servers = context.get("target_dns_servers") or self.fallback_resolvers

        # 1. Capture current DNS configuration as pre-state snapshot
        original_servers = await loop.run_in_executor(None, platform.get_interface_dns_servers, iface)
        pre_state = {
            "interface_name": iface,
            "original_servers": original_servers,
            "target_servers": target_servers,
            "timestamp": time.time(),
        }

        # 2. Apply target DNS servers
        ok, msg = await loop.run_in_executor(
            None, platform.set_interface_dns_servers, iface, target_servers
        )
        if not ok:
            raise RuntimeError(f"Failed to set DNS servers on {iface}: {msg}")

        # Flush cache to purge old mappings
        await loop.run_in_executor(None, platform.flush_dns_cache)
        return pre_state

    async def verify(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str, Dict[str, Any]]:
        # Verification: execute real query to ensure new DNS actually resolves
        import dns.resolver
        loop = asyncio.get_running_loop()
        test_domain = "google.com"

        def _verify_resolution():
            res = dns.resolver.Resolver()
            res.lifetime = 2.5
            res.timeout = 2.5
            t0 = time.perf_counter()
            ans = res.resolve(test_domain, "A")
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return latency_ms, [r.to_text() for r in ans]

        try:
            latency_ms, ips = await loop.run_in_executor(None, _verify_resolution)
            if latency_ms < 350.0 and len(ips) > 0:
                return True, f"DNS resolution verified on new resolver ({latency_ms:.1f}ms)", {
                    "latency_ms": latency_ms,
                    "resolved_ips": ips,
                }
            return False, f"DNS resolution latency too high ({latency_ms:.1f}ms)", {"latency_ms": latency_ms}
        except Exception as exc:
            return False, f"DNS resolution failed after switch: {exc}", {"error": str(exc)}

    async def rollback(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str]:
        """Restore original DNS configuration from pre_state snapshot."""
        if not pre_state or not isinstance(pre_state, dict):
            return False, "Invalid pre-state snapshot; cannot rollback"

        iface = pre_state.get("interface_name")
        original_servers = pre_state.get("original_servers", [])
        loop = asyncio.get_running_loop()

        ok, msg = await loop.run_in_executor(
            None, platform.set_interface_dns_servers, iface, original_servers
        )
        await loop.run_in_executor(None, platform.flush_dns_cache)

        if ok:
            return True, f"Successfully restored original DNS ({', '.join(original_servers) if original_servers else 'DHCP'})"
        return False, f"Failed to restore original DNS on {iface}: {msg}"
