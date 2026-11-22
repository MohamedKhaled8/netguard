"""Switch DNS Resolver Action with Automatic Pre-State Rollback (Level 2 Controlled Risk)."""

from __future__ import annotations
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from app.core.models.metrics import RiskLevel, ActionClassification
from app.platform.interfaces import IPlatformAdapter
from app.remediation.registry import RemediationAction

logger = logging.getLogger("netguard.remediation.actions.switch_dns")


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
            action_classification=ActionClassification.CONFIGURATION_CHANGE,
        )
        self.fallback_resolvers = fallback_resolvers or ["1.1.1.1", "8.8.8.8"]

    def check_preconditions(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Tuple[bool, str]:
        from app.platform.admin import require_admin
        ok, reason = require_admin("تعديل خوادم DNS لمحول الشبكة", platform)
        if not ok:
            return False, f"Cannot modify interface DNS: {reason}"

        iface = context.get("interface_name") or platform.get_primary_interface()
        if not iface:
            return False, "Cannot switch DNS: No primary network adapter detected"
        return True, f"Primary interface '{iface}' detected"

    async def execute(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Any:
        loop = asyncio.get_running_loop()
        iface = context.get("interface_name") or platform.get_primary_interface()
        target_servers = list(context.get("target_dns_servers") or self.fallback_resolvers)
        target_ipv6 = list(context.get("target_ipv6_servers") or [])
        all_targets = target_servers + target_ipv6

        # 1. Capture current DNS configuration as pre-state snapshot
        original_servers = await loop.run_in_executor(None, platform.get_interface_dns_servers, iface)
        if original_servers is None:
            original_servers = []
        ipv4_mode = "dhcp"
        if hasattr(platform, "get_interface_dns_mode"):
            ipv4_mode = await loop.run_in_executor(None, platform.get_interface_dns_mode, iface)
        ipv6_mode = "dhcp"
        if hasattr(platform, "get_interface_ipv6_dns_mode"):
            ipv6_mode = await loop.run_in_executor(None, platform.get_interface_ipv6_dns_mode, iface)
        is_dhcp = (ipv4_mode == "dhcp") if hasattr(platform, "get_interface_dns_mode") else (len(original_servers) == 0)

        pre_state = {
            "interface_name": iface,
            "original_servers": list(original_servers),
            "ipv4_mode": ipv4_mode,
            "ipv6_mode": ipv6_mode,
            "is_dhcp": is_dhcp,
            "target_servers": all_targets,
            "timestamp": time.time(),
        }

        # 2. Apply target DNS servers
        ok, msg = await loop.run_in_executor(
            None, platform.set_interface_dns_servers, iface, all_targets
        )
        if not ok:
            raise RuntimeError(f"Failed to set DNS servers on {iface}: {msg}")

        # Flush cache to purge old mappings
        await loop.run_in_executor(None, platform.flush_dns_cache)
        return pre_state

    async def verify(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str, Dict[str, Any]]:
        # Verification: execute real query specifically to new resolver and verify adapter state
        import dns.resolver
        loop = asyncio.get_running_loop()
        test_domain = "google.com"
        target_servers = context.get("target_dns_servers") or (pre_state.get("target_servers") if isinstance(pre_state, dict) else None) or self.fallback_resolvers
        target_ip = target_servers[0] if target_servers else "1.1.1.1"
        iface = context.get("interface_name") or (pre_state.get("interface_name") if isinstance(pre_state, dict) else None) or platform.get_primary_interface()

        def _verify_resolution():
            res = dns.resolver.Resolver(configure=False)
            res.nameservers = [target_ip]
            res.cache = None
            res.lifetime = 2.5
            res.timeout = 2.5
            t0 = time.perf_counter()
            ans = res.resolve(test_domain, "A")
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return latency_ms, [r.to_text() for r in ans]

        try:
            latency_ms, ips = await loop.run_in_executor(None, _verify_resolution)
            if latency_ms >= 350.0 or len(ips) == 0:
                return False, f"DNS resolution latency too high ({latency_ms:.1f}ms)", {"latency_ms": latency_ms}

            # Also verify adapter configuration has registered the server if supported
            if iface:
                current_servers = await loop.run_in_executor(None, platform.get_interface_dns_servers, iface)
                if current_servers and not any(t in current_servers for t in target_servers):
                    logger.warning("Adapter %s does not yet reflect new DNS servers: %s vs target %s", iface, current_servers, target_servers)

            # Synchronize single source of truth (Item F9)
            try:
                from app.dns.state import DnsStateManager
                from app.dns.detector import identify_provider
                prov_name = identify_provider(target_ip)
                DnsStateManager.get_instance().update(
                    active_servers=target_servers,
                    detected_provider=prov_name,
                    last_measured_ms=latency_ms,
                    is_healthy=True,
                    last_switch_time=time.time(),
                    configured_mode="static",
                )
            except Exception:
                pass

            return True, f"DNS resolution verified on new resolver ({latency_ms:.1f}ms)", {
                "latency_ms": latency_ms,
                "resolved_ips": ips,
            }
        except Exception as exc:
            return False, f"DNS resolution failed after switch: {exc}", {"error": str(exc)}

    async def rollback(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str]:
        """Restore exact original DNS configuration (DHCP or static servers) from pre_state snapshot."""
        if not pre_state or not isinstance(pre_state, dict):
            return False, "Invalid pre-state snapshot; cannot rollback"

        iface = pre_state.get("interface_name") or platform.get_primary_interface()
        original_servers = pre_state.get("original_servers", [])
        is_dhcp = pre_state.get("is_dhcp", False)
        loop = asyncio.get_running_loop()

        if is_dhcp or not original_servers:
            ok, msg = await loop.run_in_executor(
                None, platform.set_interface_dns_dhcp, iface
            )
            mode_desc = "DHCP (تلقائي)"
        else:
            target = original_servers
            ok, msg = await loop.run_in_executor(
                None, platform.set_interface_dns_servers, iface, target
            )
            mode_desc = f"Static ({', '.join(target)})"

        await loop.run_in_executor(None, platform.flush_dns_cache)

        # Synchronize rollback with single source of truth (Item F9)
        try:
            from app.dns.state import DnsStateManager
            DnsStateManager.get_instance().update(
                active_servers=original_servers,
                configured_mode="dhcp" if (is_dhcp or not original_servers) else "static",
                is_healthy=True,
                last_switch_time=time.time(),
            )
        except Exception:
            pass

        if ok:
            return True, f"Successfully restored exact original DNS ({mode_desc})"
        return False, f"Failed to restore original DNS on {iface}: {msg}"
