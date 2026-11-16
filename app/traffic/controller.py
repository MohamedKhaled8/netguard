"""Application Traffic Monitor and Workload Controller."""

from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, Optional
import psutil
from app.core.events.bus import EventBus
from app.traffic.applications import ApplicationCatalog, ProcessNetworkProfile, WorkloadCategory
from app.traffic.session_tracker import AppSessionTracker, AppSessionRecord

logger = logging.getLogger("netguard.traffic.controller")


class TrafficController:
    """Monitors process network sockets and identifies active workloads."""

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self.session_tracker = AppSessionTracker()
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
        current_names = {p.name.lower() for p in profiles}

        for p in profiles:
            if p.category in (WorkloadCategory.CONFERENCING, WorkloadCategory.STREAMING):
                # Update or track ongoing session
                display_name = p.name
                if "zoom" in p.name.lower():
                    display_name = "Zoom Cloud Meetings"
                elif "teams" in p.name.lower():
                    display_name = "Microsoft Teams"
                elif "discord" in p.name.lower():
                    display_name = "Discord"
                elif "chrome" in p.name.lower():
                    display_name = "Google Meet / Live Stream"

                self.session_tracker.start_or_update_session(
                    app_name=display_name,
                    process_name=p.name,
                    pid=p.pid,
                    category=p.category.value,
                )

        # Check for closed sessions
        for active_session in list(self.session_tracker.get_active_sessions()):
            if active_session.process_name.lower() not in current_names:
                # Closed!
                self.session_tracker.close_session(active_session.process_name)

        conferencing_active = (
            any(p.category == WorkloadCategory.CONFERENCING for p in profiles)
            or self.session_tracker.has_active_conferencing()
        )
        gaming_active = any(p.category == WorkloadCategory.GAMING for p in profiles)

        await self.event_bus.publish("traffic.workload_update", {
            "total_network_processes": len(profiles),
            "conferencing_active": conferencing_active,
            "gaming_active": gaming_active,
            "profiles": [p.model_dump(mode="json") for p in profiles[:15]],
            "active_sessions": [s.model_dump(mode="json") for s in self.session_tracker.get_active_sessions()],
            "completed_sessions": [s.model_dump(mode="json") for s in self.session_tracker.get_completed_sessions()[:10]],
        })

        return profiles

    def is_critical_meeting_active(self) -> bool:
        """Safety check: Returns True if Zoom, Teams, or conferencing app has active sockets."""
        return (
            any(p.category == WorkloadCategory.CONFERENCING for p in self._last_profiles.values())
            or self.session_tracker.has_active_conferencing()
        )

    def simulate_start_meeting_session(self, app_name: str = "Zoom Cloud Meetings", proc_name: str = "zoom.exe") -> AppSessionRecord:
        """Helper to simulate launching a protected Zoom session."""
        session = self.session_tracker.start_or_update_session(
            app_name=app_name,
            process_name=proc_name,
            pid=7812,
            category="conferencing",
            avg_bitrate=3.6,
            avg_latency=17.5,
        )
        return session

    def simulate_close_meeting_session(self, proc_name: str = "zoom.exe") -> Optional[AppSessionRecord]:
        """Helper to simulate closing a Zoom session and generating its final report."""
        return self.session_tracker.close_session(proc_name)
