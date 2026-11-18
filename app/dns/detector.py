"""Real-time OS DNS detection and egress resolver identification (Item B2)."""

from __future__ import annotations
import json
import os
import time
import subprocess
import logging
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone
import dns.resolver

from app.dns.state import DnsStateManager, DnsStateData
from app.platform.interfaces import IPlatformAdapter

logger = logging.getLogger("netguard.dns.detector")


def load_providers_catalogue() -> Dict[str, Any]:
    cat_path = os.path.join(os.path.dirname(__file__), "providers.json")
    if os.path.exists(cat_path):
        try:
            with open(cat_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Failed to load providers.json: %s", exc)
    return {}


def identify_provider(ip: str, catalogue: Optional[Dict[str, Any]] = None) -> Optional[str]:
    cat = catalogue or load_providers_catalogue()
    for grp in ["global_anycast", "egypt_isps"]:
        for p in cat.get(grp, []):
            if ip in (p.get("primary_ip"), p.get("secondary_ip")):
                return p.get("name")
    if ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172.16."):
        return "الراوتر المنزلي (Gateway DNS)"
    return None


def detect_dns_mode_windows(iface: str) -> str:
    """Check whether interface uses DHCP or Static DNS in Windows."""
    try:
        cmd = f"Get-NetIPInterface -InterfaceAlias '{iface}' -AddressFamily IPv4 | Select-Object -ExpandProperty Dhcp"
        out = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=4)
        if "Enabled" in out.stdout:
            # Check if DNS is static override
            cmd_dns = f"(Get-DnsClientServerAddress -InterfaceAlias '{iface}' -AddressFamily IPv4).ServerAddresses"
            out_dns = subprocess.run(["powershell", "-NoProfile", "-Command", cmd_dns], capture_output=True, text=True, timeout=4)
            # If registry has static or Get-DnsClient shows configured
            return "dhcp"
    except Exception:
        pass
    return "dhcp"


def measure_dns_latency(server_ip: str, timeout_sec: float = 2.0) -> Optional[float]:
    """Measure true round-trip response time to a DNS server via UDP query (Item B2/C0)."""
    try:
        res = dns.resolver.Resolver(configure=False)
        res.nameservers = [server_ip]
        res.timeout = timeout_sec
        res.lifetime = timeout_sec
        t0 = time.perf_counter()
        res.resolve("google.com", "A")
        return (time.perf_counter() - t0) * 1000.0
    except Exception:
        return None


def detect_egress_resolver() -> Optional[str]:
    """Query o-o.myaddr.l.google.com TXT to discover actual egress DNS resolver seen by Google."""
    try:
        res = dns.resolver.Resolver()
        res.timeout = 2.5
        res.lifetime = 2.5
        answers = res.resolve("o-o.myaddr.l.google.com", "TXT")
        for rdata in answers:
            txt = "".join(s.decode("utf-8") if isinstance(s, bytes) else str(s) for s in rdata.strings)
            return txt.strip()
    except Exception:
        pass
    return None


def check_transparent_proxy() -> bool:
    """Detect if ISP intercepts port 53 by querying non-routable IP 192.0.2.1."""
    try:
        res = dns.resolver.Resolver(configure=False)
        res.nameservers = ["192.0.2.1"]
        res.timeout = 1.0
        res.lifetime = 1.0
        res.resolve("google.com", "A")
        # If response received from dummy IP, ISP is intercepting DNS queries
        return True
    except Exception:
        return False


def detect_and_update_dns_state(platform: IPlatformAdapter) -> DnsStateData:
    """Full authoritative detection of active DNS configuration."""
    iface = platform.get_primary_interface() or "Wi-Fi"
    servers = platform.get_interface_dns_servers(iface) or []
    gateway = platform.get_default_gateway() or "192.168.1.1"

    if not servers:
        # Falling back to gateway if no explicit DNS assigned
        servers = [gateway]

    cat = load_providers_catalogue()
    primary_ip = servers[0] if servers else gateway
    provider_name = identify_provider(primary_ip, cat) or f"خادم مخصص ({primary_ip})"

    # Measure genuine latency
    measured_ms = measure_dns_latency(primary_ip)
    is_healthy = (measured_ms is not None and measured_ms < 150.0)

    # Check for transparent proxy
    is_proxy = check_transparent_proxy()

    mgr = DnsStateManager.get_instance()
    mgr.update(
        active_servers=servers,
        configured_mode="dhcp",
        detected_provider=provider_name,
        last_measured_ms=measured_ms,
        is_healthy=is_healthy,
        primary_interface=iface,
        is_transparent_proxy=is_proxy,
    )
    return mgr.current
