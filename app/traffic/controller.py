"""Application Traffic Monitor and Workload Controller for NetGuard AI.

Implements real Windows QoS policies in ActiveStore:
- Single generic mechanism for all meeting apps via MeetingAppRegistry.
- Dual-condition call detection: ConsentStore active (mic/cam) + sustained outbound UDP.
- Dedicated meeting-signal poller (runs every 2s regardless of visible view).
- Mixed media AF41 (DSCP 34) and Voice EF (DSCP 46) matching strictly UDP media ports.
- Meeting Mode State Machine with Hysteresis (5s enter, 20s leave) measured with real elapsed time.
- Background outbound traffic demotion to CS1 (DSCP 8 -> AC_BK).
- Adaptive upload throttling for bulk cloud uploaders with headroom preservation (TCP & UDP).
- Closed-Loop verification with pre-meeting baseline and automatic two-tier rollback.
- Bufferbloat and Wi-Fi weak link live diagnostics.
- Instant Kill Switch and persistent configuration.
"""

from __future__ import annotations
import asyncio
import collections
import concurrent.futures
import logging
import socket
import statistics
import sys
import time
from typing import Dict, List, Optional, Set, Any, Tuple
import psutil

from app.core.events.bus import EventBus
from app.platform.interfaces import IPlatformAdapter
from app.traffic.applications import ApplicationCatalog, ProcessNetworkProfile, WorkloadCategory
from app.traffic.session_tracker import AppSessionTracker, AppSessionRecord
from app.traffic.meeting_registry import MeetingAppRegistry, MeetingAppEntry
from app.traffic.meeting_detector import (
    MeetingDetector,
    MeetingModeState,
    MeetingHysteresisTracker,
    MeetingState,
    detect_bufferbloat,
    detect_wifi_weak_link,
)
from app.traffic.qos_config import (
    AppQoSConfig,
    QoSPolicySpec,
    DSCPValue,
    PROTECTED_PROCESSES,
    is_netguard_or_protected_process,
    compute_adaptive_upload_throttle,
    build_meeting_qos_specs,
)

logger = logging.getLogger("netguard.traffic.controller")


def preresolve_meeting_domains() -> Dict[str, List[str]]:
    """Pre-resolve meeting domains into Windows OS DNS cache across all registry apps."""
    domains = MeetingAppRegistry.get_all_concrete_domains()
    resolved: Dict[str, List[str]] = {}
    for domain in domains:
        try:
            infos = socket.getaddrinfo(domain, 443, proto=socket.IPPROTO_TCP)
            ips = list({info[4][0] for info in infos})
            resolved[domain] = ips
        except Exception as e:
            logger.debug("Pre-resolve error for %s: %s", domain, e)
    return resolved


class TrafficController:
    """Monitors process network sockets and manages QoS policies."""

    def __init__(
        self,
        event_bus: EventBus,
        platform: Optional[IPlatformAdapter] = None,
        user_settings: Optional[Any] = None,
        qos_config: Optional[AppQoSConfig] = None,
        meeting_detector: Optional[MeetingDetector] = None,
    ) -> None:
        self.event_bus = event_bus
        self.platform = platform
        self.user_settings = user_settings
        self.qos_config = qos_config or AppQoSConfig()
        self.session_tracker = AppSessionTracker()
        self.meeting_detector = meeting_detector or MeetingDetector()
        self.hysteresis_tracker = MeetingHysteresisTracker(enter_sec=5.0, leave_sec=20.0)

        self._last_profiles: Dict[int, ProcessNetworkProfile] = {}
        self._applied_policy_names: Set[str] = set()
        self._applied_dscp_policies: Set[str] = set()
        self._applied_throttle_policies: Set[str] = set()
        self._active_qos_specs: List[QoSPolicySpec] = []
        self._last_net_io: Optional[tuple[float, Any]] = None

        # Closed-loop guard state
        self._closed_loop_baseline: Optional[Dict[str, float]] = None
        self._closed_loop_rollback_enabled: bool = True
        self._closed_loop_applied_time: float = 0.0
        self._closed_loop_rolled_back: bool = False
        self._media_marking_rolled_back: bool = False
        self._media_rollback_time: float = 0.0
        self._closed_loop_rollback_reason: str = ""
        self._closed_loop_cooldown_until: float = 0.0

        # Rolling sample buffers: baseline uses last 30 samples captured while IDLE
        self._loss_history = collections.deque(maxlen=20)
        self._jitter_history = collections.deque(maxlen=20)
        self._rtt_history = collections.deque(maxlen=20)
        self._idle_loss_history = collections.deque(maxlen=30)
        self._idle_jitter_history = collections.deque(maxlen=30)
        self._idle_rtt_history = collections.deque(maxlen=30)

        # Process priority state
        self._process_priority_lowered: bool = False

        # Uplink capacity and video tier tracking for adaptive throttling
        self.measured_uplink_mbps: float = self.qos_config.default_uplink_mbps
        self.video_tier: str = "1080p"

        # Diagnostic advisories
        self.last_bufferbloat_advisory: Dict[str, Any] = {}
        self.last_wifi_advisory: Dict[str, Any] = {}

        # PID-to-process-name cache with 45s TTL
        self._pid_name_cache: Dict[int, tuple[str, float]] = {}
        self._pid_cache_ttl_sec: float = 45.0

        # Remove any stale policies on initial startup
        self.startup_cleanup_stale_policies()

    def set_preflight_metrics(self, uplink_mbps: float, video_tier: Optional[str] = None) -> None:
        """Update measured uplink capacity and video tier from genuine preflight diagnostics."""
        if uplink_mbps > 0:
            self.measured_uplink_mbps = float(uplink_mbps)
            # Automatic adaptive video tier selection based on uplink capacity
            if uplink_mbps < 1.0:
                self.video_tier = "audio_only"
            elif uplink_mbps < 3.0:
                self.video_tier = "360p"
            elif uplink_mbps < 6.0:
                self.video_tier = "720p"
            else:
                self.video_tier = "1080p"
        if video_tier:
            self.video_tier = str(video_tier)
        logger.info("Updated preflight metrics: Uplink=%.1f Mbps, Tier=%s", self.measured_uplink_mbps, self.video_tier)

    def startup_cleanup_stale_policies(self) -> Tuple[bool, str]:
        """Sweep any lingering NetGuard policies on startup from active or persistent stores."""
        if self.platform and hasattr(self.platform, "is_elevated") and self.platform.is_elevated():
            try:
                if hasattr(self.platform, "sweep_all_netguard_rules"):
                    res = self.platform.sweep_all_netguard_rules()
                    if isinstance(res, tuple) and len(res) >= 2:
                        ok, msg = bool(res[0]), str(res[1])
                    elif isinstance(res, bool):
                        ok, msg = res, "Cleaned" if res else "Failed"
                    else:
                        ok, msg = bool(res), str(res)

                    if ok:
                        logger.info("Startup sweep: Cleaned any stale NetGuard QoS policies: %s", msg)
                    else:
                        logger.warning("Startup sweep warning: %s", msg)
                    return ok, msg
                logger.info("Startup sweep: Cleaned any stale NetGuard QoS policies.")
                return True, "Cleaned"
            except Exception as exc:
                logger.debug("Startup sweep error: %s", exc)
                return False, str(exc)
        return True, "No platform or unprivileged"

    def kill_switch_disable(self) -> Tuple[bool, str]:
        """Instant kill switch: immediately remove all NetGuard QoS policies and disable Meeting Mode."""
        self.qos_config.master_enabled = False
        self.cleanup_all_policies()
        logger.warning("Instant Kill Switch triggered: all NetGuard QoS policies removed and Meeting Mode QoS disabled.")
        return True, "تم إيقاف وحذف جميع سياسات QoS فوراً وتعطيل أولوية الاجتماعات."

    def _resolve_process_name(self, pid: int, now_t: float) -> Optional[str]:
        """Resolves process name using TTL-cached PID mapping."""
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

    def _adjust_netguard_process_priority(self, lower: bool) -> None:
        """Adjust NetGuard process priority so it does not compete with real-time video."""
        try:
            p = psutil.Process()
            if lower and not self._process_priority_lowered:
                if hasattr(psutil, "BELOW_NORMAL_PRIORITY_CLASS"):
                    p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                    self._process_priority_lowered = True
                    logger.info("Lowered NetGuard process priority to BELOW_NORMAL during meeting.")
            elif not lower and self._process_priority_lowered:
                if hasattr(psutil, "NORMAL_PRIORITY_CLASS"):
                    p.nice(psutil.NORMAL_PRIORITY_CLASS)
                    self._process_priority_lowered = False
                    logger.info("Restored NetGuard process priority to NORMAL.")
        except Exception as e:
            logger.debug("Failed to adjust process priority: %s", e)

    def snapshot_pre_meeting_baseline(self) -> Optional[Dict[str, float]]:
        """Capture rolling baseline from idle samples before policy application."""
        if len(self._idle_loss_history) >= 5:
            base = {
                "loss": float(statistics.median(self._idle_loss_history)),
                "jitter": float(statistics.median(self._idle_jitter_history)),
                "rtt": float(statistics.median(self._idle_rtt_history)),
            }
            self._closed_loop_baseline = base
            self._closed_loop_rollback_enabled = True
            logger.info("Captured pre-meeting QoS baseline: Loss=%.2f%%, Jitter=%.1fms, RTT=%.1fms",
                        base["loss"], base["jitter"], base["rtt"])
            return base
        else:
            self._closed_loop_baseline = None
            self._closed_loop_rollback_enabled = False
            logger.warning(
                "Pre-meeting baseline unavailable (< 5 valid pre-policy samples collected). "
                "Safe prioritization active; automatic rollback disabled."
            )
            return None

    async def poll_meeting_signal(self, now_mono: Optional[float] = None) -> MeetingState:
        """Dedicated meeting-signal poller that runs every 2s regardless of the visible view.
        
        Executes lightweight ConsentStore and UDP write rate checks off the UI thread.
        Evaluates 5s enter / 20s leave hysteresis and applies/cleans QoS policies accordingly.
        """
        loop = asyncio.get_running_loop()
        now_m = now_mono if now_mono is not None else time.monotonic()

        def _check():
            in_call = self.meeting_detector.detect_in_call_apps(
                now_t=now_m,
                threshold_bytes_per_sec=self.qos_config.min_udp_outbound_bytes_per_sec,
            )
            return in_call

        in_call_apps = await loop.run_in_executor(None, _check)
        raw_meeting_active = len(in_call_apps) > 0

        # Update hysteresis state machine with real elapsed time
        mode_state, state_changed = self.hysteresis_tracker.update(raw_meeting_active, now_m)

        # Synchronize detector's current meeting state with hysteresis tracker
        self.meeting_detector.current.mode_state = mode_state
        self.meeting_detector.current.is_active = (mode_state in (MeetingModeState.ENTERING, MeetingModeState.ACTIVE, MeetingModeState.LEAVING))
        if in_call_apps:
            self.meeting_detector.current.app_name = in_call_apps[0][0].display_name
            self.meeting_detector.current.process_name = in_call_apps[0][1]
            self.meeting_detector.current.pid = in_call_apps[0][2]
        elif mode_state == MeetingModeState.IDLE:
            self.meeting_detector.current.app_name = ""
            self.meeting_detector.current.process_name = ""
            self.meeting_detector.current.pid = 0

        allow_mg = True
        if self.user_settings and hasattr(self.user_settings, "get_policy"):
            allow_mg = self.user_settings.get_policy("meeting_guard", True)

        can_apply_qos = (
            allow_mg
            and self.qos_config.master_enabled
            and self.platform
            and hasattr(self.platform, "is_elevated")
            and self.platform.is_elevated()
        )

        active_meeting_app_ids = [entry.id for entry, _, _ in in_call_apps]
        active_meeting_display_names = [entry.display_name for entry, _, _ in in_call_apps]

        # Act on state transitions
        if mode_state == MeetingModeState.ACTIVE:
            self._adjust_netguard_process_priority(lower=True)

            # Master Disable or unprivileged while ACTIVE: immediate teardown off Qt UI thread
            if not can_apply_qos and (self._active_qos_specs or self._applied_policy_names):
                logger.info("QoS Master Disabled or unprivileged during ACTIVE: sweeping active policies immediately.")
                await loop.run_in_executor(None, self.cleanup_all_policies)

            # Update sessions in tracker
            for entry, proc_name, pid in in_call_apps:
                self.session_tracker.start_or_update_session(
                    app_name=entry.display_name,
                    process_name=proc_name,
                    pid=pid,
                    category="conferencing",
                )

            # Check if policies should be applied (not in rollback cooldown and not already applied)
            if can_apply_qos and not self._active_qos_specs and not self._closed_loop_rolled_back:
                if now_m >= self._closed_loop_cooldown_until:
                    # Pre-meeting baseline snapshot BEFORE apply
                    if self._closed_loop_baseline is None:
                        self.snapshot_pre_meeting_baseline()

                    # Pre-resolve meeting domains
                    loop.run_in_executor(None, preresolve_meeting_domains)

                    # Discover active bulk download/sync apps
                    active_bulk = [
                        p.name for p in self._last_profiles.values()
                        if (p.category == WorkloadCategory.DOWNLOAD
                            or p.name.lower() in ("onedrive.exe", "dropbox.exe", "googledrivesync.exe", "qbittorrent.exe", "steam.exe"))
                        and not p.is_protected_system_process
                        and p.name.lower() not in PROTECTED_PROCESSES
                        and not is_netguard_or_protected_process(p.name, p.pid)
                        and not p.name.lower().startswith("svchost")
                    ]

                    specs = build_meeting_qos_specs(
                        active_meeting_apps=active_meeting_app_ids,
                        active_bulk_apps=active_bulk,
                        available_uplink_mbps=self.measured_uplink_mbps,
                        video_tier=self.video_tier,
                        is_audio_only=False,
                        config=self.qos_config,
                    )

                    if hasattr(self.platform, "apply_qos_policies_batch"):
                        ok, msg = await loop.run_in_executor(None, self.platform.apply_qos_policies_batch, specs)
                        report = getattr(self.platform, "last_qos_batch_report", {})
                        verified_names = set(report.get("verified", []))
                    else:
                        ok = True
                        verified_names = {s.name for s in specs}

                    # Only confirmed policies from ActiveStore readback are retained; NEVER fallback to all specs if verified_names is empty
                    confirmed_specs = [s for s in specs if s.name in verified_names]
                    if confirmed_specs:
                        self._active_qos_specs = confirmed_specs
                        self._applied_policy_names = {s.name for s in confirmed_specs}
                        self._applied_throttle_policies = {s.app_name.lower() for s in confirmed_specs if s.throttle_bps}
                        self._applied_dscp_policies = {s.app_name.lower() for s in confirmed_specs if s.dscp and s.app_name}
                        self._closed_loop_applied_time = now_m
                        logger.info("Meeting Mode ACTIVE: Applied and confirmed %d QoS policies in ActiveStore.", len(confirmed_specs))
                    else:
                        self._active_qos_specs = []
                        self._applied_policy_names = set()
                        self._applied_throttle_policies = set()
                        self._applied_dscp_policies = set()
                        logger.warning("ActiveStore readback confirmed 0 policies. No unverified specs retained.")

        elif mode_state == MeetingModeState.IDLE:
            self._adjust_netguard_process_priority(lower=False)
            if self._active_qos_specs or self._applied_policy_names:
                await loop.run_in_executor(None, self.cleanup_all_policies)
                self._closed_loop_rolled_back = False
                self._media_marking_rolled_back = False
                self._closed_loop_baseline = None
                logger.info("Meeting Mode IDLE: Cleaned up all QoS policies.")

            for active_session in list(self.session_tracker.get_active_sessions()):
                self.session_tracker.close_session(active_session.process_name)

        current_meeting = self.meeting_detector.current
        return current_meeting

    async def scan_active_applications(self) -> List[ProcessNetworkProfile]:
        """Scans active TCP/UDP connections for the UI Traffic table (runs every 30s or on demand)."""
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

            # Check in-call apps from meeting detector
            proc_list = [(pid, self._resolve_process_name(pid, now_t)) for pid in active_pids if self._resolve_process_name(pid, now_t)]
            in_call = self.meeting_detector.detect_in_call_apps(
                running_procs=proc_list,
                now_t=now_t,
                udp_sockets_by_pid=udp_pids,
            )
            in_call_exes = {proc_name.lower() for _, proc_name, _ in in_call}

            grouped_processes: Dict[str, Dict[str, Any]] = {}
            for pid, endpoints in active_pids.items():
                pname = self._resolve_process_name(pid, now_t)
                if not pname:
                    continue

                k = pname.lower()
                if k not in grouped_processes:
                    category, priority, is_protected = ApplicationCatalog.classify(pname)
                    # Conferencing category only if actively in a call!
                    if k in in_call_exes:
                        category = WorkloadCategory.CONFERENCING
                        priority = 1
                    elif category == WorkloadCategory.CONFERENCING:
                        # Idle signed-in meeting app -> demote to background workload
                        category = WorkloadCategory.BACKGROUND
                        priority = 3

                    grouped_processes[k] = {
                        "name": pname,
                        "primary_pid": pid,
                        "pids": [pid],
                        "endpoints": list(endpoints),
                        "category": category,
                        "priority": priority,
                        "is_protected": is_protected,
                        "has_webrtc": (pid in webrtc_pids),
                    }
                else:
                    grouped_processes[k]["pids"].append(pid)
                    grouped_processes[k]["endpoints"].extend(endpoints)
                    if pid in webrtc_pids:
                        grouped_processes[k]["has_webrtc"] = True

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
                    remote_endpoints=data["endpoints"][:5],
                    is_protected_system_process=data["is_protected"],
                    is_estimated=True,
                    estimated_bandwidth_mbps=est_mbps,
                )
                profiles.append(profile)

            return profiles

        profiles = await loop.run_in_executor(None, _scan)
        self._last_profiles = {p.pid: p for p in profiles}

        # Also trigger the meeting signal poller
        await self.poll_meeting_signal()

        mode_state = self.hysteresis_tracker.state
        conferencing_active = (mode_state in (MeetingModeState.ENTERING, MeetingModeState.ACTIVE, MeetingModeState.LEAVING))
        gaming_active = any(p.category == WorkloadCategory.GAMING for p in profiles)

        await self.event_bus.publish("traffic.workload_update", {
            "total_network_processes": len(profiles),
            "conferencing_active": conferencing_active,
            "meeting_mode_state": mode_state.value,
            "gaming_active": gaming_active,
            "profiles": [p.model_dump(mode="json") for p in profiles[:15]],
            "active_sessions": [s.model_dump(mode="json") for s in self.session_tracker.get_active_sessions()],
            "completed_sessions": [s.model_dump(mode="json") for s in self.session_tracker.get_completed_sessions()[:10]],
            "qos_policies_active": len(self._active_qos_specs),
            "closed_loop_rolled_back": self._closed_loop_rolled_back,
            "closed_loop_reason": self._closed_loop_rollback_reason,
            "bufferbloat": self.last_bufferbloat_advisory,
            "wifi_status": self.last_wifi_advisory,
        })

        return profiles

    def record_quality_sample(
        self,
        loss_pct: float,
        jitter_ms: float,
        rtt_ms: float,
        timestamp_mono: Optional[float] = None,
        session_id: Optional[str] = None,
    ) -> bool:
        """Record quality samples into rolling history for pre-meeting baseline and median evaluation.
        
        Validates monotonic timestamps and freshness (<= 10s old). Rejects stale or fabricated samples.
        """
        import math
        now = time.monotonic()
        t_mono = timestamp_mono if timestamp_mono is not None else now
        if (now - t_mono) > 10.0 or (t_mono - now) > 2.0:
            logger.debug("Rejected stale/skewed quality sample: age=%.2fs", now - t_mono)
            return False

        if math.isnan(loss_pct) or math.isnan(jitter_ms) or math.isnan(rtt_ms):
            return False
        if loss_pct < 0.0 or loss_pct > 100.0 or jitter_ms < 0.0 or rtt_ms < 0.0:
            return False

        is_pre_policy = (
            self.hysteresis_tracker.state in (MeetingModeState.IDLE, MeetingModeState.ENTERING)
            and not self._active_qos_specs
        )
        if is_pre_policy:
            self._idle_loss_history.append(float(loss_pct))
            self._idle_jitter_history.append(float(jitter_ms))
            self._idle_rtt_history.append(float(rtt_ms))
        else:
            self._loss_history.append(float(loss_pct))
            self._jitter_history.append(float(jitter_ms))
            self._rtt_history.append(float(rtt_ms))
        return True

    def evaluate_telemetry_advisories(
        self,
        idle_latency_ms: float,
        load_latency_ms: float,
        is_wifi: bool,
        signal_pct: Optional[float] = None,
        jitter_ms: float = 0.0,
        packet_loss_pct: float = 0.0,
    ) -> None:
        """Runs live bufferbloat and Wi-Fi weak link diagnostics and caches advisories."""
        self.last_bufferbloat_advisory = detect_bufferbloat(
            idle_latency_ms=idle_latency_ms,
            load_latency_ms=load_latency_ms,
            upload_active=True,
        )
        self.last_wifi_advisory = detect_wifi_weak_link(
            is_wifi=is_wifi,
            signal_pct=signal_pct,
            jitter_ms=jitter_ms,
            packet_loss_pct=packet_loss_pct,
        )

    def evaluate_closed_loop_quality(
        self,
        current_loss_pct: float,
        current_jitter_ms: float,
        current_rtt_ms: float,
        timestamp_mono: Optional[float] = None,
        session_id: Optional[str] = None,
    ) -> bool:
        """Closed-loop guard: Automatically rolls back QoS policy if quality degrades after application.
        
        Uses medians over >= 10 samples against pre-meeting baseline captured BEFORE policy application.
        Stage 1: Rolls back media-marking policies (DSCP 34/46) first.
        Stage 2: Full rollback of remaining policies if degradation persists.
        Returns True if rollback was triggered.
        """
        import math
        now = time.monotonic()
        t_mono = timestamp_mono if timestamp_mono is not None else now
        if (now - t_mono) > 10.0 or (t_mono - now) > 2.0:
            logger.debug("Rejected stale/skewed closed-loop sample: age=%.2fs", now - t_mono)
            return False

        if math.isnan(current_loss_pct) or math.isnan(current_jitter_ms) or math.isnan(current_rtt_ms):
            return False
        if current_loss_pct < 0.0 or current_loss_pct > 100.0 or current_jitter_ms < 0.0 or current_rtt_ms < 0.0:
            return False

        self._loss_history.append(current_loss_pct)
        self._jitter_history.append(current_jitter_ms)
        self._rtt_history.append(current_rtt_ms)

        if not self._active_qos_specs or self._closed_loop_rolled_back:
            return False

        if not getattr(self, "_closed_loop_rollback_enabled", True):
            return False

        # 10.0 seconds grace period after policy application for socket buffers to stabilize
        if (now - self._closed_loop_applied_time) < 10.0:
            return False

        # If Stage 1 media marking was recently rolled back, allow 5.0s settling time before Stage 2
        if self._media_marking_rolled_back and (now - self._media_rollback_time) < 5.0:
            return False

        # Ensure we have a valid baseline from before apply (never fabricated defaults)
        if self._closed_loop_baseline is None:
            if len(self._idle_loss_history) >= 5:
                self._closed_loop_baseline = {
                    "loss": statistics.median(self._idle_loss_history),
                    "jitter": statistics.median(self._idle_jitter_history),
                    "rtt": statistics.median(self._idle_rtt_history),
                }
                self._closed_loop_rollback_enabled = True
            else:
                self._closed_loop_rollback_enabled = False
                logger.debug("Closed-loop auto-rollback disabled: no valid baseline available.")
                return False

        # Require at least 10 samples post-apply before evaluating medians
        if len(self._loss_history) < 10:
            return False

        loss_median = statistics.median(self._loss_history)
        jitter_median = statistics.median(self._jitter_history)
        rtt_median = statistics.median(self._rtt_history)

        base = self._closed_loop_baseline
        loss_jump = loss_median - base["loss"]
        jitter_jump = jitter_median - base["jitter"]
        rtt_jump = rtt_median - base["rtt"]

        cfg = self.qos_config
        degraded = (
            loss_jump >= cfg.max_acceptable_loss_jump_pct
            or jitter_jump >= cfg.max_acceptable_jitter_jump_ms
            or rtt_jump >= cfg.max_acceptable_rtt_jump_ms
        )

        if degraded:
            sess_name = session_id or "active_meeting"
            # Stage 1: Roll back ONLY media-marking policies first (DSCP 34/46)
            if not self._media_marking_rolled_back:
                logger.warning(
                    "Closed-loop guard STAGE 1 ROLLBACK: Media DSCP degraded network quality. "
                    "Session=%s, Baseline=(Loss=%.2f%%, Jitter=%.1fms, RTT=%.1fms), "
                    "Current=(Loss=%.2f%%, Jitter=%.1fms, RTT=%.1fms), "
                    "Delta=(Loss=+%.2f%%, Jitter=+%.1fms, RTT=+%.1fms), "
                    "Thresholds=(Loss=+%.2f%%, Jitter=+%.1fms, RTT=+%.1fms)",
                    sess_name,
                    base["loss"], base["jitter"], base["rtt"],
                    loss_median, jitter_median, rtt_median,
                    loss_jump, jitter_jump, rtt_jump,
                    cfg.max_acceptable_loss_jump_pct, cfg.max_acceptable_jitter_jump_ms, cfg.max_acceptable_rtt_jump_ms
                )
                media_to_remove = [
                    s for s in list(self._active_qos_specs)
                    if s.precedence == 200 or any(kw in s.name for kw in ("Media", "Audio", "Video", "STUN", "Sharing", "Fallback"))
                ]
                for mp in media_to_remove:
                    if self.platform:
                        self.platform.remove_qos_policy(mp.name, policy_store="ActiveStore")
                    self._applied_policy_names.discard(mp.name)
                    self._applied_dscp_policies.discard(mp.app_name.lower())
                self._active_qos_specs = [s for s in self._active_qos_specs if s not in media_to_remove]
                self._media_marking_rolled_back = True
                self._media_rollback_time = now
                self._closed_loop_rollback_reason = (
                    f"تم التراجع عن علامات أولوية الوسائط (DSCP 34/46) لمكالمات الفيديو بسبب تدهور الاتصال "
                    f"(ارتفاع التذبذب +{jitter_jump:.1f}ms أو فقد الحزم +{loss_jump:.1f}% أو الاستجابة +{rtt_jump:.1f}ms). "
                    f"استمرار تقييد برامج الخلفية للحماية."
                )
                return True

            # Stage 2: Complete rollback of remaining policies if degradation persists
            logger.warning(
                "Closed-loop guard STAGE 2 ROLLBACK: Persistent quality degradation post-QoS. "
                "Session=%s, Baseline=(Loss=%.2f%%, Jitter=%.1fms, RTT=%.1fms), "
                "Current=(Loss=%.2f%%, Jitter=%.1fms, RTT=%.1fms), "
                "Delta=(Loss=+%.2f%%, Jitter=+%.1fms, RTT=+%.1fms), "
                "Thresholds=(Loss=+%.2f%%, Jitter=+%.1fms, RTT=+%.1fms)",
                sess_name,
                base["loss"], base["jitter"], base["rtt"],
                loss_median, jitter_median, rtt_median,
                loss_jump, jitter_jump, rtt_jump,
                cfg.max_acceptable_loss_jump_pct, cfg.max_acceptable_jitter_jump_ms, cfg.max_acceptable_rtt_jump_ms
            )
            self.cleanup_all_policies()
            self._closed_loop_rolled_back = True
            self._closed_loop_rollback_reason = (
                f"تم التراجع تلقائياً عن جميع سياسات QoS: تدهور في جودة الاتصال "
                f"(ارتفاع التذبذب +{jitter_jump:.1f}ms أو فقد الحزم +{loss_jump:.1f}%)"
            )
            self._closed_loop_cooldown_until = now + cfg.rollback_cooldown_seconds
            return True

        return False

        return False

    def is_critical_meeting_active(self) -> bool:
        """Returns True if Meeting Mode is currently in ENTERING, ACTIVE, or LEAVING state."""
        return (
            self.hysteresis_tracker.state in (MeetingModeState.ENTERING, MeetingModeState.ACTIVE, MeetingModeState.LEAVING)
            or self.session_tracker.has_active_conferencing()
        )

    def reconcile_active_policies(self) -> Dict[str, Any]:
        """Watchdog: Reconcile Get-NetQosPolicy against expected NetGuard state and sweep orphans."""
        if not self.platform or not hasattr(self.platform, "is_elevated") or not self.platform.is_elevated():
            return {"status": "unverified", "policies": []}

        try:
            live_policies = self.platform.get_qos_policies(policy_store="ActiveStore")
            live_names = {p.get("name", "") for p in live_policies if p.get("name", "").startswith("NetGuard_")}

            expected_names = set(self._applied_policy_names)
            orphans = live_names - expected_names

            for orphan in orphans:
                logger.info("Watchdog removing orphan QoS policy: %s", orphan)
                self.platform.remove_qos_policy(orphan, policy_store="ActiveStore")

            is_verified = (expected_names.issubset(live_names)) if expected_names else True
            return {
                "status": "verified" if is_verified else "partial",
                "live_count": len(live_names),
                "expected_count": len(expected_names),
                "orphans_cleared": len(orphans),
            }
        except Exception as exc:
            logger.debug("QoS reconciliation error: %s", exc)
            return {"status": "error", "message": str(exc)}

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

    def cleanup_all_policies(self) -> Tuple[bool, str]:
        """Remove all active NetGuard QoS policies (ActiveStore & persistent) on exit or mode change."""
        if not self.platform:
            return True, "No platform configured"
        logger.info("Cleaning up all NetGuard QoS policies...")
        sweep_ok = True
        sweep_msg = "Cleaned"
        if hasattr(self.platform, "sweep_all_netguard_rules") and self.platform.is_elevated():
            res = self.platform.sweep_all_netguard_rules()
            if isinstance(res, tuple) and len(res) >= 2:
                sweep_ok, sweep_msg = bool(res[0]), str(res[1])
            elif isinstance(res, bool):
                sweep_ok, sweep_msg = res, "Cleaned" if res else "Failed"
            else:
                sweep_ok, sweep_msg = bool(res), str(res)

            if sweep_ok:
                logger.info("Cleanup sweep verified: %s", sweep_msg)
            else:
                logger.warning("Cleanup sweep warning: %s", sweep_msg)
        else:
            for p_name in list(self._applied_policy_names):
                try:
                    self.platform.remove_qos_policy(p_name, policy_store="ActiveStore")
                except Exception:
                    pass
        self._applied_policy_names.clear()
        self._applied_dscp_policies.clear()
        self._applied_throttle_policies.clear()
        self._active_qos_specs.clear()
        self._media_marking_rolled_back = False
        self._loss_history.clear()
        self._jitter_history.clear()
        self._rtt_history.clear()
        self._adjust_netguard_process_priority(lower=False)
        return sweep_ok, sweep_msg
