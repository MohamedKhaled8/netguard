"""Real-time OS DNS detection and egress resolver identification (Item B2)."""

from __future__ import annotations
import json
import os
import sys
import time
import socket
import subprocess
import logging
import statistics
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
import dns.resolver

from app.dns.state import DnsStateManager, DnsStateData
from app.platform.interfaces import IPlatformAdapter

logger = logging.getLogger("netguard.dns.detector")


@dataclass
class DnsDetailedMeasurement:
    """Detailed result of genuine multi-attempt DNS Query measurements."""
    server_ip: str
    provider_name: str
    is_valid_query: bool
    mean_latency_ms: Optional[float] = None
    min_latency_ms: Optional[float] = None
    max_latency_ms: Optional[float] = None
    median_latency_ms: Optional[float] = None
    success_rate: float = 0.0
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    is_ip_reachable: bool = True
    status_summary: str = ""
    error_message: Optional[str] = None


def load_providers_catalogue() -> Dict[str, Any]:
    cat_path = os.path.join(os.path.dirname(__file__), "providers.json")
    if not os.path.exists(cat_path) and getattr(sys, "frozen", False):
        cat_path = os.path.join(getattr(sys, "_MEIPASS", ""), "app", "dns", "providers.json")
    if os.path.exists(cat_path):
        try:
            with open(cat_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Failed to load providers.json: %s", exc)
    return {}


def identify_provider(ip: str, catalogue: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Accurately identify DNS provider by IPv4 or IPv6 address without guessing."""
    if not ip:
        return None
    cat = catalogue or load_providers_catalogue()
    for grp in ["global_anycast", "egypt_isps"]:
        for p in cat.get(grp, []):
            if ip in (
                p.get("primary_ip"),
                p.get("secondary_ip"),
                p.get("primary_ipv6"),
                p.get("secondary_ipv6"),
            ):
                return p.get("name")
    if ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172.16."):
        return "الراوتر المنزلي (Gateway DNS)"
    if ip.lower().startswith("fe80:"):
        return "الراوتر المنزلي (Gateway IPv6)"
    return None


def get_secondary_ip(ip: str, catalogue: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Retrieve corresponding secondary DNS IP for a given primary IP (or vice-versa)."""
    if not ip:
        return None
    cat = catalogue or load_providers_catalogue()
    for grp in ["global_anycast", "egypt_isps"]:
        for p in cat.get(grp, []):
            p_ip = p.get("primary_ip")
            s_ip = p.get("secondary_ip")
            p_ipv6 = p.get("primary_ipv6")
            s_ipv6 = p.get("secondary_ipv6")
            if ip == p_ip and s_ip:
                return s_ip
            if ip == s_ip and p_ip:
                return p_ip
            if ip == p_ipv6 and s_ipv6:
                return s_ipv6
            if ip == s_ipv6 and p_ipv6:
                return p_ipv6
    return None


def get_provider_details(ip_or_name: str, catalogue: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Retrieve full provider record from catalogue matching name, primary/secondary IPv4, or IPv6."""
    if not ip_or_name:
        return None
    cat = catalogue or load_providers_catalogue()
    target = ip_or_name.strip()
    for grp in ["global_anycast", "egypt_isps"]:
        for p in cat.get(grp, []):
            if (
                target.lower() == p.get("name", "").lower()
                or target == p.get("primary_ip")
                or target == p.get("secondary_ip")
                or target == p.get("primary_ipv6")
                or target == p.get("secondary_ipv6")
            ):
                return p
    return None


def get_provider_ipv6(ip_or_name: str, catalogue: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], Optional[str]]:
    """Retrieve official (primary_ipv6, secondary_ipv6) pair for a provider IP or name."""
    details = get_provider_details(ip_or_name, catalogue)
    if details:
        return details.get("primary_ipv6"), details.get("secondary_ipv6")
    return None, None


def detect_dns_mode_windows(iface: str) -> str:
    """Check whether interface uses DHCP or Static DNS in Windows via netsh."""
    try:
        proc = subprocess.run(
            ["netsh", "interface", "ipv4", "show", "dnsservers", iface],
            capture_output=True,
            text=True,
            timeout=2.5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if proc.returncode == 0:
            if "Statically Configured" in proc.stdout:
                return "static"
            elif "through DHCP" in proc.stdout:
                return "dhcp"
    except Exception:
        pass
    return "dhcp"


def measure_dns_resolver_deep(
    server_ip: str,
    rounds: int = 3,
    timeout_sec: float = 2.0,
    domains: Optional[List[str]] = None,
) -> DnsDetailedMeasurement:
    """Perform genuine multi-attempt DNS query benchmark across standard domains.
    
    Distinguishes actual DNS Query resolution on port 53 from raw IP reachability.
    Calculates average, min, max, and success rate without synthetic values.
    """
    cat = load_providers_catalogue()
    provider_name = identify_provider(server_ip, cat) or f"خادم مخصص ({server_ip})"
    test_domains = domains or ["google.com", "cloudflare.com", "wikipedia.org"]

    res = dns.resolver.Resolver(configure=False)
    res.nameservers = [server_ip]
    res.timeout = timeout_sec
    res.lifetime = timeout_sec
    res.cache = None

    latencies: List[float] = []
    failures = 0
    total_queries = max(1, rounds) * len(test_domains)

    last_error: Optional[str] = None
    for _ in range(max(1, rounds)):
        for domain in test_domains:
            t0 = time.perf_counter()
            try:
                res.resolve(domain, "A")
                d_ms = (time.perf_counter() - t0) * 1000.0
                latencies.append(d_ms)
            except Exception as exc:
                failures += 1
                last_error = str(exc)

    successful = len(latencies)
    success_rate = (successful / total_queries) if total_queries > 0 else 0.0

    if latencies:
        mean_ms = float(statistics.mean(latencies))
        min_ms = float(min(latencies))
        max_ms = float(max(latencies))
        med_ms = float(statistics.median(latencies))
        is_valid = True
        if mean_ms <= 60.0:
            summary = "استجابة ممتازة وفورية لطلبات DNS"
        elif mean_ms <= 120.0:
            summary = "استجابة مقبولة وطبيعية"
        else:
            summary = "استجابة بطيئة نسبياً لترجمة النطاقات"
        is_ip_reachable = True
    else:
        mean_ms = None
        min_ms = None
        max_ms = None
        med_ms = None
        is_valid = False

        # Check if the server IP itself is reachable (ping/socket) to distinguish port 53 drop from offline IP
        is_ip_reachable = False
        try:
            sock = socket.socket(socket.AF_INET if ":" not in server_ip else socket.AF_INET6, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            sock.connect((server_ip, 53))
            sock.close()
            is_ip_reachable = True
        except Exception:
            try:
                proc = subprocess.run(
                    ["ping", "-n", "1", "-w", "700", server_ip],
                    capture_output=True,
                    timeout=1.2,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if proc.returncode == 0:
                    is_ip_reachable = True
            except Exception:
                pass

        if is_ip_reachable:
            summary = "عنوان IP متاح لكن خادم DNS لا يستجيب لطلبات المنفذ 53 (Timeout)"
        else:
            summary = "تعذر الوصول إلى عنوان خادم DNS تماماً (انقطاع الاتصال)"

    return DnsDetailedMeasurement(
        server_ip=server_ip,
        provider_name=provider_name,
        is_valid_query=is_valid,
        mean_latency_ms=mean_ms,
        min_latency_ms=min_ms,
        max_latency_ms=max_ms,
        median_latency_ms=med_ms,
        success_rate=success_rate,
        total_queries=total_queries,
        successful_queries=successful,
        failed_queries=failures,
        is_ip_reachable=is_ip_reachable,
        status_summary=summary,
        error_message=last_error,
    )


def measure_dns_latency(server_ip: str, timeout_sec: float = 2.0) -> Optional[float]:
    """Measure genuine round-trip response time to a DNS server via UDP query (Item B2/C0)."""
    stats = measure_dns_resolver_deep(server_ip, rounds=2, timeout_sec=timeout_sec)
    if stats.is_valid_query and stats.median_latency_ms is not None:
        return stats.median_latency_ms
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

    # Measure genuine latency across multiple queries
    stats = measure_dns_resolver_deep(primary_ip, rounds=2, timeout_sec=2.0)
    measured_ms = stats.median_latency_ms if stats.is_valid_query else None
    is_healthy = (stats.is_valid_query and measured_ms is not None and measured_ms < 150.0 and stats.success_rate >= 0.8)

    # Check for transparent proxy & egress resolver
    is_proxy = check_transparent_proxy()
    egress_ip = detect_egress_resolver()

    # Detect real DHCP vs Static mode
    configured_mode = "dhcp"
    if hasattr(platform, "get_interface_dns_mode"):
        configured_mode = platform.get_interface_dns_mode(iface)
    elif os.name == "nt":
        configured_mode = detect_dns_mode_windows(iface)

    mgr = DnsStateManager.get_instance()
    mgr.update(
        active_servers=servers,
        configured_mode=configured_mode,
        detected_provider=provider_name,
        last_measured_ms=measured_ms,
        min_latency_ms=stats.min_latency_ms,
        max_latency_ms=stats.max_latency_ms,
        mean_latency_ms=stats.mean_latency_ms,
        query_success_rate=stats.success_rate,
        status_summary=stats.status_summary,
        is_healthy=is_healthy,
        primary_interface=iface,
        is_transparent_proxy=is_proxy,
        egress_resolver=egress_ip,
    )
    return mgr.current
