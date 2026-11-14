"""Application Traffic Monitor and Workload Controller."""

from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, Optional
import psutil
from app.core.events.bus import EventBus
from app.traffic.applications import ApplicationCatalog, ProcessNetworkProfile, WorkloadCategory

logger = logging.getLogger("netguard.traffic.controller")


class TrafficController:
    """Monitors process network sockets and identifies active workloads."""

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self._last_profiles: Dict[int, ProcessNetworkProfile] = {}

    async def scan_active_applications(self) -> List[ProcessNetworkProfile]:
        """Scans all active TCP/UDP connections and builds workload profiles."""
        loop = asyncio.get_running_loop()

        def _scan():
            connections = psutil.net_connections(kind="inet")
            active_pids: Dict[int, List[str]] = {}

            for conn in connections:
                if conn.pid and conn.status == psutil.CONN_ESTABLISHED:
                    remote_str = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "listening"
                    active_pids.setdefault(conn.pid, []).append(remote_str)

            profiles = []
            for pid, endpoints in active_pids.items():
                try:
                    p = psutil.Process(pid)
                    pname = p.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

                category, priority, is_protected = ApplicationCatalog.classify(pname)
                profile = ProcessNetworkProfile(
                    pid=pid,
                    name=pname,
                    category=category,
                    priority_level=priority,
                    active_socket_count=len(endpoints),
                    remote_endpoints=endpoints[:5],  # top 5 endpoints
                    is_protected_system_process=is_protected,
                )
                profiles.append(profile)

            return profiles

        profiles = await loop.run_in_executor(None, _scan)
        self._last_profiles = {p.pid: p for p in profiles}

        # Check if conferencing is active (Zoom, Teams)
        conferencing_active = any(p.category == WorkloadCategory.CONFERENCING for p in profiles)
        gaming_active = any(p.category == WorkloadCategory.GAMING for p in profiles)

        await self.event_bus.publish("traffic.workload_update", {
            "total_network_processes": len(profiles),
            "conferencing_active": conferencing_active,
            "gaming_active": gaming_active,
            "profiles": [p.model_dump(mode="json") for p in profiles[:15]],
        })

        return profiles

    def is_critical_meeting_active(self) -> bool:
        """Safety check: Returns True if Zoom, Teams, or conferencing app has active sockets."""
        return any(p.category == WorkloadCategory.CONFERENCING for p in self._last_profiles.values())
