"""Application Traffic Monitor and Workload Controller."""

from __future__ import annotations
import asyncio
import concurrent.futures
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
        self._applied_throttle_policies: Set[str] = set()
        self._last_net_io: Optional[tuple[float, Any]] = None
        # PID-to-process-name cache with 45s TTL to avoid repeated psutil.Process allocations
        self._pid_name_cache: Dict[int, tuple[str, float]] = {}
        self._pid_cache_ttl_sec: float = 45.0

    def _resolve_process_name(self, pid: int, now_t: float) -> Optional[str]:
        """Resolves process name using TTL-cached PID mapping to avoid re-allocating psutil.Process."""
        cached = self._pid_name_cache.get(pid)
        if cached:
            pname, cached_at = cached
            if now_t - cached_at < self._pid_cache_ttl_sec:
                return pname

        try:
            p = psutil.Process(pid)
            pname = p.name()
            self._pid_name_cache[pid] = (pname, now_t)
            return pname
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            self._pid_name_cache.pop(pid, None)
            return None

    def _prune_pid_cache(self, now_t: float) -> None:
        """Prunes expired entries or dead processes from PID cache."""
        expired = [
            pid for pid, (name, t) in self._pid_name_cache.items()
            if now_t - t >= self._pid_cache_ttl_sec or not psutil.pid_exists(pid)
        ]
        for pid in expired:
            self._pid_name_cache.pop(pid, None)

    async def scan_active_applications(self) -> List[ProcessNetworkProfile]:
        """Scans all active TCP/UDP connections and builds workload profiles."""
        loop = asyncio.get_running_loop()

        def _scan():
            import time
            import socket
            connections = psutil.net_connections(kind="inet")
            active_pids: Dict[int, List[str]] = {}
            udp_pids: set[int] = set()
            webrtc_pids: set[int] = set()
            WEBRTC_PORTS = {3478, 19302, 19303, 19304, 19305, 19306, 19307, 19308, 19309, 8801, 8802, 8803, 8804, 8805}

            for conn in connections:
                if not conn.pid:
                    continue
                if conn.type == socket.SOCK_DGRAM:
                    udp_pids.add(conn.pid)
                    if conn.raddr and (conn.raddr.port in WEBRTC_PORTS or 19302 <= conn.raddr.port <= 19309):
                        webrtc_pids.add(conn.pid)
                    remote_str = f"udp:{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "udp:active"
                    active_pids.setdefault(conn.pid, []).append(remote_str)
                elif conn.status == psutil.CONN_ESTABLISHED:
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
            self._prune_pid_cache(now_t)

            grouped_processes: Dict[str, Dict[str, Any]] = {}
            for pid, endpoints in active_pids.items():
                pname = self._resolve_process_name(pid, now_t)
                if not pname:
                    continue

                k = pname.lower()
                if k not in grouped_processes:
                    category, priority, is_protected = ApplicationCatalog.classify(pname)
                    # Elevate browser only if it is actually in an active UDP WebRTC media session
                    is_active_webrtc = (pid in webrtc_pids)
                    if k in ("chrome.exe", "msedge.exe", "brave.exe", "firefox.exe"):
                        if is_active_webrtc:
                            category = WorkloadCategory.CONFERENCING
                            priority = 1
                    grouped_processes[k] = {
                        "name": pname,
                        "primary_pid": pid,
                        "pids": [pid],
                        "endpoints": list(endpoints),
                        "category": category,
                        "priority": priority,
                        "is_protected": is_protected,
                        "has_webrtc": is_active_webrtc,
                    }
                else:
                    grouped_processes[k]["pids"].append(pid)
                    grouped_processes[k]["endpoints"].extend(endpoints)
                    if pid in webrtc_pids:
                        grouped_processes[k]["has_webrtc"] = True
                        if k in ("chrome.exe", "msedge.exe", "brave.exe", "firefox.exe"):
                            grouped_processes[k]["category"] = WorkloadCategory.CONFERENCING
                            grouped_processes[k]["priority"] = 1

            profiles = []
            for k, data in grouped_processes.items():
                s_cnt = len(data["endpoints"])
                est_mbps = round(total_mbps * (s_cnt / max(1, total_sockets)), 2) if total_sockets > 0 else 0.0
                profile = ProcessNetworkProfile(
                    pid=data["primary_pid"],
                    name=data["name"],
                    category=data["category"],
                    priority_level=data["priority"],
                    active_socket_count=s_cnt,
                    remote_endpoints=data["endpoints"][:5],  # top 5 endpoints
                    is_protected_system_process=data["is_protected"],
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
            p_lower = p.name.lower()
            if p.category == WorkloadCategory.CONFERENCING:
                # Update or track ongoing session
                display_name = p.name
                if "zoom" in p_lower:
                    display_name = "Zoom Cloud Meetings"
                elif "teams" in p_lower:
                    display_name = "Microsoft Teams"
                elif "discord" in p_lower:
                    display_name = "Discord"
                elif "chrome" in p_lower:
                    display_name = "Google Meet"
                elif "msedge" in p_lower:
                    display_name = "Microsoft Edge (Meet)"

                self.session_tracker.start_or_update_session(
                    app_name=display_name,
                    process_name=p.name,
                    pid=p.pid,
                    category=p.category.value,
                )

                # Attempt real Windows DSCP 46 tagging if elevated and policy enabled (Item D3)
                allow_mg = True
                if self.user_settings and hasattr(self.user_settings, "get_policy"):
                    allow_mg = self.user_settings.get_policy("meeting_guard", True)
                if allow_mg and self.platform:
                    if p.name.lower() not in self._applied_dscp_policies and self.platform.is_elevated():
                        is_browser = p.name.lower() in ("chrome.exe", "msedge.exe", "brave.exe", "firefox.exe")
                        proto = "UDP" if is_browser else None
                        ok, msg = self.platform.create_qos_dscp_policy(f"NetGuard_DSCP_{p.name}", p.name, 46, ip_protocol=proto)
                        if ok:
                            self._applied_dscp_policies.add(p.name.lower())
                            logger.info("Applied real Windows DSCP 46 policy for %s (protocol=%s): %s", p.name, proto, msg)

                    # Throttle BULK uploaders to safe 2 Mbps ceiling (Item D3)
                    bulk_candidates = [
                        pr.name for pr in profiles
                        if pr.category == WorkloadCategory.DOWNLOAD or pr.name.lower() in ("onedrive.exe", "dropbox.exe", "qbittorrent.exe", "steam.exe")
                    ]
                    for b_name in bulk_candidates:
                        b_lower = b_name.lower()
                        if b_lower not in self._applied_throttle_policies and self.platform.is_elevated():
                            ok_th, msg_th = self.platform.create_qos_throttle_policy(f"NetGuard_Throttle_{b_name}", b_name, 2_000_000)
                            if ok_th:
                                self._applied_throttle_policies.add(b_lower)
                                logger.info("Applied real Windows QoS upload throttle (2M) for BULK uploader %s: %s", b_name, msg_th)

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

                # If no more conferencing active, remove BULK throttles cleanly (Item D3)
                if not self.session_tracker.has_active_conferencing():
                    for b_lower in list(self._applied_throttle_policies):
                        if self.platform and self.platform.is_elevated():
                            self.platform.remove_qos_policy(f"NetGuard_Throttle_{b_lower}")
                        self._applied_throttle_policies.discard(b_lower)

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

    def cleanup_all_policies(self) -> None:
        """Remove all active NetGuard QoS policies (DSCP and throttle) on shutdown."""
        if not self.platform:
            return
        logger.info("Cleaning up all NetGuard QoS policies...")
        for p_name in list(self._applied_dscp_policies):
            try:
                self.platform.remove_qos_policy(f"NetGuard_DSCP_{p_name}")
            except Exception:
                pass
        for b_name in list(self._applied_throttle_policies):
            try:
                self.platform.remove_qos_policy(f"NetGuard_Throttle_{b_name}")
            except Exception:
                pass
        self._applied_dscp_policies.clear()
        self._applied_throttle_policies.clear()
        if hasattr(self.platform, "sweep_all_netguard_rules") and self.platform.is_elevated():
            self.platform.sweep_all_netguard_rules()
