"""Application Traffic Monitor and Workload Controller."""

from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, Optional, Set
import psutil
from app.core.events.bus import EventBus
from app.platform.interfaces import IPlatformAdapter
from app.traffic.applications import ApplicationCatalog, ProcessNetworkProfile, WorkloadCategory
from app.traffic.session_tracker import AppSessionTracker, AppSessionRecord

logger = logging.getLogger("netguard.traffic.controller")


class TrafficController:
    """Monitors process network sockets and identifies active workloads."""

    def __init__(
        self,
        event_bus: EventBus,
        platform: Optional[IPlatformAdapter] = None,
        user_settings: Optional[Any] = None,
    ) -> None:
        self.event_bus = event_bus
        self.platform = platform
        self.user_settings = user_settings
        self.session_tracker = AppSessionTracker()
        self._last_profiles: Dict[int, ProcessNetworkProfile] = {}
        self._applied_dscp_policies: Set[str] = set()
        self._last_net_io: Optional[tuple[float, Any]] = None

    async def scan_active_applications(self) -> List[ProcessNetworkProfile]:
        """Scans all active TCP/UDP connections and builds workload profiles."""
        loop = asyncio.get_running_loop()

        def _scan():
            import time
            connections = psutil.net_connections(kind="inet")
            active_pids: Dict[int, List[str]] = {}

            for conn in connections:
                if conn.pid and conn.status == psutil.CONN_ESTABLISHED:
                    remote_str = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "listening"
                    active_pids.setdefault(conn.pid, []).append(remote_str)

            total_sockets = sum(len(eps) for eps in active_pids.values())
            now_t = time.perf_counter()
            io_now = psutil.net_io_counters()
            total_mbps = 0.0
            if self._last_net_io:
                prev_t, prev_io = self._last_net_io
                dt = max(0.1, now_t - prev_t)
                delta_bytes = (io_now.bytes_recv + io_now.bytes_sent) - (prev_io.bytes_recv + prev_io.bytes_sent)
                if delta_bytes >= 0:
                    total_mbps = (delta_bytes * 8.0) / (dt * 1_000_000.0)
            self._last_net_io = (now_t, io_now)

            profiles = []
            for pid, endpoints in active_pids.items():
                try:
                    p = psutil.Process(pid)
                    pname = p.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

                category, priority, is_protected = ApplicationCatalog.classify(pname)
                s_cnt = len(endpoints)
                est_mbps = round(total_mbps * (s_cnt / max(1, total_sockets)), 2) if total_sockets > 0 else 0.0
                profile = ProcessNetworkProfile(
                    pid=pid,
                    name=pname,
                    category=category,
                    priority_level=priority,
                    active_socket_count=s_cnt,
                    remote_endpoints=endpoints[:5],  # top 5 endpoints
                    is_protected_system_process=is_protected,
                    is_estimated=True,
                    estimated_bandwidth_mbps=est_mbps,
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

                # Attempt real Windows DSCP 46 tagging if elevated and policy enabled
                allow_mg = True
                if self.user_settings and hasattr(self.user_settings, "get_policy"):
                    allow_mg = self.user_settings.get_policy("meeting_guard", True)
                if allow_mg and self.platform and p.name.lower() not in self._applied_dscp_policies:
                    if self.platform.is_elevated():
                        ok, msg = self.platform.create_qos_dscp_policy(f"NetGuard_DSCP_{p.name}", p.name, 46)
                        if ok:
                            self._applied_dscp_policies.add(p.name.lower())
                            logger.info("Applied real Windows DSCP 46 policy for %s: %s", p.name, msg)

        # Check for closed sessions
        for active_session in list(self.session_tracker.get_active_sessions()):
            if active_session.process_name.lower() not in current_names:
                # Closed!
                self.session_tracker.close_session(active_session.process_name)
                p_lower = active_session.process_name.lower()
                if p_lower in self._applied_dscp_policies:
                    if self.platform and self.platform.is_elevated():
                        self.platform.remove_qos_policy(f"NetGuard_DSCP_{active_session.process_name}")
                    self._applied_dscp_policies.discard(p_lower)

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
