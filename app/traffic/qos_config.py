"""QoS Policy Specifications, Standards, and Adaptive Configuration for NetGuard AI.

Provides authoritative configurations for all meeting apps via MeetingAppRegistry,
with DSCP actions, port ranges, adaptive upload throttling math, exemption policies,
and spec builders aligned with RFC 4594, RFC 8325, and official vendor specifications.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set

from app.traffic.meeting_registry import MeetingAppRegistry, MeetingAppEntry, MediaProfile


# Critical system and NetGuard processes that must NEVER be demoted or throttled
PROTECTED_PROCESSES: Set[str] = {
    "system", "registry", "smss.exe", "csrss.exe", "wininit.exe",
    "services.exe", "lsass.exe", "svchost.exe", "explorer.exe",
    "dwm.exe", "spoolsv.exe", "netguard.exe", "python.exe", "pythonw.exe"
}


def is_netguard_or_protected_process(name: str, pid: Optional[int] = None) -> bool:
    """Check if process name or PID is NetGuard (parent or child) or Windows protected system process.
    
    Preserves elevated parent bootloader and child application process hierarchy under PyInstaller one-file packaging.
    """
    if not name:
        return False
    lower = name.lower()
    if lower in PROTECTED_PROCESSES or lower.startswith("svchost"):
        return True
    try:
        import os
        current_pid = os.getpid()
        parent_pid = os.getppid() if hasattr(os, "getppid") else None
        if pid is not None and (pid == current_pid or pid == parent_pid):
            return True
    except Exception:
        pass
    try:
        import sys
        from pathlib import Path
        if hasattr(sys, "frozen") and sys.executable:
            exe_name = Path(sys.executable).name.lower()
            if lower == exe_name:
                return True
    except Exception:
        pass
    return False


class DSCPValue(IntEnum := int):
    """Standard DSCP priority values aligned with RFC 4594, RFC 8325, and MS/Zoom docs."""
    EF_VOICE = 46      # Expedited Forwarding (Voice, Low-rate Audio only) -> AC_VO
    AF41_VIDEO = 34    # Assured Forwarding 41 (Video conferencing / mixed media) -> AC_VI
    AF21_SHARING = 18  # Assured Forwarding 21 (Screen / App sharing) -> AC_BE
    CS1_BACKGROUND = 8 # Class Selector 1 (Bulk / Background traffic) -> AC_BK
    DEFAULT = 0        # Best Effort (Exemptions / Normal) -> AC_BE


@dataclass
class QoSPolicySpec:
    """Exact specification for a Windows NetQosPolicy."""
    name: str
    app_name: str = ""
    dscp: Optional[int] = DSCPValue.AF41_VIDEO
    protocol: Optional[str] = None  # Explicit protocol requirement: None for bulk/default, "UDP" or "TCP" when specified
    port_start: Optional[int] = None
    port_end: Optional[int] = None
    port: Optional[int] = None
    is_dest_port: bool = True
    is_default: bool = False
    throttle_bps: Optional[int] = None
    precedence: Optional[int] = None
    policy_store: str = "ActiveStore"

    def to_powershell_command(self) -> str:
        """Construct the exact New-NetQosPolicy PowerShell cmdlet."""
        parts = [f"New-NetQosPolicy -Name '{self.name}' -PolicyStore {self.policy_store}"]
        if self.is_default:
            parts.append("-Default")
        elif self.app_name:
            parts.append(f"-AppPathNameMatchCondition '{self.app_name}'")

        if self.protocol:
            parts.append(f"-IPProtocolMatchCondition {self.protocol}")

        if self.port_start is not None and self.port_end is not None:
            if self.is_dest_port:
                parts.append(f"-IPDstPortStartMatchCondition {self.port_start} -IPDstPortEndMatchCondition {self.port_end}")
            else:
                parts.append(f"-IPSrcPortStartMatchCondition {self.port_start} -IPSrcPortEndMatchCondition {self.port_end}")
        elif self.port is not None:
            if self.is_dest_port:
                parts.append(f"-IPDstPortMatchCondition {self.port}")
            else:
                parts.append(f"-IPSrcPortMatchCondition {self.port}")

        # Both DSCPAction and ThrottleRateActionBitsPerSecond may be specified simultaneously without if/elif
        if self.dscp is not None:
            parts.append(f"-DSCPAction {int(self.dscp)}")
        if self.throttle_bps is not None:
            parts.append(f"-ThrottleRateActionBitsPerSecond {int(self.throttle_bps)}")

        if self.precedence is not None:
            parts.append(f"-Precedence {int(self.precedence)}")

        return " ".join(parts)


@dataclass
class AppQoSConfig:
    """Configurable QoS settings for meeting and background applications."""
    # Master and per-app toggles
    master_enabled: bool = True
    enabled_apps: Dict[str, bool] = field(default_factory=lambda: {
        "zoom": True,
        "zoom.exe": True,
        "teams": True,
        "teams.exe": True,
        "ms-teams.exe": True,
        "browsers": True,
        "chrome.exe": True,
        "msedge.exe": True,
        "brave.exe": True,
        "firefox.exe": True,
        "opera.exe": True,
        "vivaldi.exe": True,
        "slack": True,
        "slack.exe": True,
        "discord": True,
        "discord.exe": True,
        "skype": True,
        "skype.exe": True,
        "skypeapp.exe": True,
        "webex": True,
        "webex.exe": True,
        "webexmta.exe": True,
    })

    # Microsoft Teams port split opt-in (default False: all Teams UDP media -> DSCP 34)
    enable_teams_port_split: bool = False
    bulk_throttle_enabled: bool = True

    @property
    def teams_port_split(self) -> bool:
        return self.enable_teams_port_split

    @teams_port_split.setter
    def teams_port_split(self, value: bool) -> None:
        self.enable_teams_port_split = bool(value)

    @classmethod
    def from_user_settings(cls, settings: Any) -> AppQoSConfig:
        """Hydrate AppQoSConfig from UserSettings or dictionary."""
        config = cls()
        if not settings:
            return config
        try:
            if hasattr(settings, "get_policy"):
                master = settings.get_policy("qos_master_enabled", None)
                if master is not None:
                    config.master_enabled = bool(master)
                apps = settings.get_policy("qos_enabled_apps", None)
                if isinstance(apps, dict):
                    config.enabled_apps.update(apps)
                teams_split = settings.get_policy("qos_teams_port_split", None)
                if teams_split is not None:
                    config.enable_teams_port_split = bool(teams_split)
                bulk = settings.get_policy("qos_bulk_throttle_enabled", None)
                if bulk is not None:
                    config.bulk_throttle_enabled = bool(bulk)
            elif isinstance(settings, dict):
                if "qos_master_enabled" in settings:
                    config.master_enabled = bool(settings["qos_master_enabled"])
                if isinstance(settings.get("qos_enabled_apps"), dict):
                    config.enabled_apps.update(settings["qos_enabled_apps"])
                if "qos_teams_port_split" in settings:
                    config.enable_teams_port_split = bool(settings["qos_teams_port_split"])
                if "qos_bulk_throttle_enabled" in settings:
                    config.bulk_throttle_enabled = bool(settings["qos_bulk_throttle_enabled"])
        except Exception as e:
            import logging
            logging.getLogger("netguard.traffic.qos_config").debug("Hydration error: %s", e)
        return config

    def to_user_settings(self, settings: Any) -> None:
        """Persist current AppQoSConfig into UserSettings."""
        if not settings or not hasattr(settings, "set_policy"):
            return
        settings.set_policy("qos_master_enabled", self.master_enabled)
        settings.set_policy("qos_enabled_apps", dict(self.enabled_apps))
        settings.set_policy("qos_teams_port_split", self.enable_teams_port_split)
        settings.set_policy("qos_bulk_throttle_enabled", self.bulk_throttle_enabled)

    # Exemption toggles to prevent demotion of critical flows
    exempt_dns: bool = True
    exempt_netguard_process: bool = True
    exempt_system_services: bool = True
    exempt_meeting_tcp: bool = True

    # DSCP marking actions (user configurable)
    zoom_mixed_dscp: int = DSCPValue.AF41_VIDEO      # 34: mixed video+audio (RFC 8325 safe)
    zoom_audio_only_dscp: int = DSCPValue.EF_VOICE   # 46: only when provably audio-only
    teams_audio_dscp: int = DSCPValue.EF_VOICE       # 46: MS Teams Audio port range (opt-in)
    teams_video_dscp: int = DSCPValue.AF41_VIDEO     # 34: MS Teams Video port range / default
    teams_sharing_dscp: int = DSCPValue.AF21_SHARING # 18: MS Teams App Sharing port range (opt-in)
    meet_media_dscp: int = DSCPValue.AF41_VIDEO      # 34: WebRTC Google Meet media
    background_default_dscp: int = DSCPValue.CS1_BACKGROUND # 8: Background traffic

    # Adaptive upload throttling
    default_uplink_mbps: float = 15.0
    reservation_1080p_mbps: float = 3.5
    reservation_720p_mbps: float = 2.0
    reservation_360p_mbps: float = 1.0
    reservation_audio_mbps: float = 0.3
    non_meeting_headroom_ratio: float = 0.55  # Total non-meeting <= 55% of remainder
    min_throttle_bps_per_app: int = 250_000   # Floor: 250 kbps to prevent socket timeouts

    # Closed-loop guard thresholds
    max_acceptable_jitter_jump_ms: float = 15.0  # +15ms jitter jump
    max_acceptable_loss_jump_pct: float = 2.0    # +2.0% loss jump
    max_acceptable_rtt_jump_ms: float = 40.0     # +40ms RTT jump
    rollback_cooldown_seconds: float = 300.0     # 5-minute cooldown post rollback

    # UDP outbound traffic threshold for meeting signal (bytes/sec)
    min_udp_outbound_bytes_per_sec: float = 2500.0  # 20 kbps floor


def compute_adaptive_upload_throttle(
    available_uplink_mbps: float,
    video_tier: str = "1080p",
    active_bulk_app_count: int = 1,
    config: Optional[AppQoSConfig] = None,
) -> int:
    """Compute per-app upload throttle rate in bits per second (bps) with headroom reservation.
    
    Dynamically scales the reservation for low-bandwidth uplinks (1-2.5 Mbps) to prevent
    strangling non-meeting traffic while reserving adequate capacity for the active meeting.
    """
    cfg = config or AppQoSConfig()
    
    uplink = max(1.0, float(available_uplink_mbps if available_uplink_mbps > 0 else cfg.default_uplink_mbps))

    # Auto-select or clamp video tier on constrained uplinks (< 3 Mbps)
    tier_lower = (video_tier or "").lower()
    if uplink < 1.0 or "audio" in tier_lower:
        reservation = cfg.reservation_audio_mbps
    elif uplink < 3.0 or "360" in tier_lower:
        reservation = cfg.reservation_360p_mbps
    elif uplink < 6.0 or "720" in tier_lower:
        reservation = cfg.reservation_720p_mbps
    else:
        reservation = cfg.reservation_1080p_mbps

    # Dynamically scale reservation on constrained connections (1.0 to 2.5 Mbps)
    if uplink <= 1.5:
        reservation = min(reservation, uplink * 0.60)
    elif uplink <= 2.5:
        reservation = min(reservation, uplink * 0.70)

    remaining = max(0.4, uplink - reservation)
    total_non_meeting_mbps = max(0.25, remaining * cfg.non_meeting_headroom_ratio)

    app_count = max(1, active_bulk_app_count)
    per_app_mbps = total_non_meeting_mbps / app_count
    per_app_bps = int(max(cfg.min_throttle_bps_per_app, per_app_mbps * 1_000_000))
    return per_app_bps


def build_meeting_qos_specs(
    active_meeting_apps: List[str],
    active_bulk_apps: List[str],
    available_uplink_mbps: float = 15.0,
    video_tier: str = "1080p",
    is_audio_only: bool = False,
    config: Optional[AppQoSConfig] = None,
) -> List[QoSPolicySpec]:
    """Build all active QoS policy specs using the generic MeetingAppRegistry mechanism.
    
    Precedence Hierarchy:
    - Precedence 200: Meeting UDP Media (DSCP 34/46)
    - Precedence 170: Protected Operations & System Processes (DSCP 0: NetGuard, Python, svchost.exe)
    - Precedence 160: DNS Outbound Exemption (UDP/TCP 53 -> DSCP 0)
    - Precedence 150: Meeting App TCP 443 Signaling Exemption (TCP 443 -> DSCP 0)
    - Precedence 100: Bulk Application Outbound Throttling (DSCP 8 + ThrottleRate bps, protocol=None)
    - Precedence 50:  Default Background Traffic Demotion (DSCP 8 / CS1 -> AC_BK, protocol=None)
    """
    cfg = config or AppQoSConfig()
    if not cfg.master_enabled:
        return []

    specs: List[QoSPolicySpec] = []

    # 1. Default background traffic demotion to CS1 (DSCP 8 -> AC_BK)
    specs.append(QoSPolicySpec(
        name="NetGuard_Default_CS1",
        is_default=True,
        dscp=cfg.background_default_dscp,
        protocol=None,
        precedence=50,
        policy_store="ActiveStore",
    ))

    # 2. Explicit Exemptions (DSCP 0) to prevent -Default demoting critical flows
    if cfg.exempt_dns:
        # DNS UDP 53
        specs.append(QoSPolicySpec(
            name="NetGuard_Exempt_DNS_UDP",
            app_name="",
            dscp=DSCPValue.DEFAULT,
            protocol="UDP",
            port=53,
            is_dest_port=True,
            precedence=160,
            policy_store="ActiveStore",
        ))
        # DNS TCP 53
        specs.append(QoSPolicySpec(
            name="NetGuard_Exempt_DNS_TCP",
            app_name="",
            dscp=DSCPValue.DEFAULT,
            protocol="TCP",
            port=53,
            is_dest_port=True,
            precedence=160,
            policy_store="ActiveStore",
        ))

    if cfg.exempt_netguard_process:
        # NetGuard application itself and Python runtime
        specs.append(QoSPolicySpec(
            name="NetGuard_Exempt_App",
            app_name="netguard.exe",
            dscp=DSCPValue.DEFAULT,
            protocol=None,
            precedence=170,
            policy_store="ActiveStore",
        ))
        specs.append(QoSPolicySpec(
            name="NetGuard_Exempt_Python",
            app_name="python.exe",
            dscp=DSCPValue.DEFAULT,
            protocol=None,
            precedence=170,
            policy_store="ActiveStore",
        ))

    if cfg.exempt_system_services:
        # Protected Windows system services (svchost.exe: BITS, WinUpdate, DNS client)
        specs.append(QoSPolicySpec(
            name="NetGuard_Exempt_Svchost",
            app_name="svchost.exe",
            dscp=DSCPValue.DEFAULT,
            protocol=None,
            precedence=170,
            policy_store="ActiveStore",
        ))

    # 3. Generic policy generation for every in-call app from MeetingAppRegistry
    # Maps each active meeting identifier to its registered entry
    resolved_entries: List[Tuple[MeetingAppEntry, str]] = []
    seen_entry_ids: Set[str] = set()

    for app in active_meeting_apps:
        app_lower = app.lower()
        # Find entry by exe name or ID
        entry = MeetingAppRegistry.find_entry_for_process(app_lower) or MeetingAppRegistry.get_entry_by_id(app_lower)
        if not entry:
            # Fallback entry for uncataloged meeting app
            entry = MeetingAppEntry(
                id=app_lower.replace(".exe", ""),
                display_name=app,
                exe_names=[app_lower if app_lower.endswith(".exe") else f"{app_lower}.exe"],
                media_profile=MediaProfile(has_known_ports=False, default_dscp=cfg.zoom_mixed_dscp),
            )
        
        # Check enabled_apps toggle
        if not cfg.enabled_apps.get(entry.id, True) and not cfg.enabled_apps.get(app_lower, True):
            continue

        if entry.id not in seen_entry_ids:
            seen_entry_ids.add(entry.id)
            resolved_entries.append((entry, app))

    for entry, triggered_app in resolved_entries:
        app_id = entry.id
        profile = entry.media_profile

        # Target executables: if browser, match only the specific browser exe; otherwise entry exes + extra_exes
        if entry.is_browser:
            browser_exe = triggered_app.lower() if triggered_app.lower().endswith(".exe") else f"{triggered_app.lower()}.exe"
            target_exes = [browser_exe] if browser_exe in entry.exe_names else [entry.exe_names[0]]
        else:
            target_exes = list(entry.exe_names)
            if entry.extra_exes:
                # Include helper processes, e.g. CptHost.exe for Zoom screen share
                for extra in entry.extra_exes:
                    if extra not in target_exes:
                        target_exes.append(extra)

        # Exemption for meeting app TCP 443 signaling & fallback streams
        if cfg.exempt_meeting_tcp:
            for exe in target_exes:
                specs.append(QoSPolicySpec(
                    name=f"NetGuard_Exempt_{exe.replace('.exe', '')}_TCP443",
                    app_name=exe,
                    dscp=DSCPValue.DEFAULT,
                    protocol="TCP",
                    port=443,
                    is_dest_port=True,
                    precedence=150,
                    policy_store="ActiveStore",
                ))

        # Media marking DSCP action: AF41 (34) default for mixed media; EF (46) strictly restricted to verified audio-only
        if is_audio_only and profile.audio_only_dscp:
            target_dscp = profile.audio_only_dscp
        else:
            target_dscp = DSCPValue.AF41_VIDEO if profile.default_dscp == DSCPValue.EF_VOICE else profile.default_dscp

        for exe in target_exes:
            exe_clean = exe.replace(".exe", "")

            if profile.has_known_ports:
                if profile.has_stream_split and cfg.enable_teams_port_split:
                    # Teams opt-in stream split
                    if profile.audio_ports:
                        specs.append(QoSPolicySpec(
                            name=f"NetGuard_Teams_Audio_{exe_clean}_{profile.audio_ports[0]}",
                            app_name=exe,
                            dscp=cfg.teams_audio_dscp,
                            protocol="UDP",
                            port_start=profile.audio_ports[0],
                            port_end=profile.audio_ports[1],
                            is_dest_port=profile.is_dest_port,
                            precedence=200,
                            policy_store="ActiveStore",
                        ))
                    if profile.video_ports:
                        specs.append(QoSPolicySpec(
                            name=f"NetGuard_Teams_Video_{exe_clean}_{profile.video_ports[0]}",
                            app_name=exe,
                            dscp=cfg.teams_video_dscp,
                            protocol="UDP",
                            port_start=profile.video_ports[0],
                            port_end=profile.video_ports[1],
                            is_dest_port=profile.is_dest_port,
                            precedence=200,
                            policy_store="ActiveStore",
                        ))
                    if profile.sharing_ports:
                        specs.append(QoSPolicySpec(
                            name=f"NetGuard_Teams_Sharing_{exe_clean}_{profile.sharing_ports[0]}",
                            app_name=exe,
                            dscp=cfg.teams_sharing_dscp,
                            protocol="UDP",
                            port_start=profile.sharing_ports[0],
                            port_end=profile.sharing_ports[1],
                            is_dest_port=profile.is_dest_port,
                            precedence=200,
                            policy_store="ActiveStore",
                        ))
                else:
                    # Known port range (Zoom 8801-8810, Teams default 50000-50059, Meet 19302-19309)
                    if profile.media_port_start is not None and profile.media_port_end is not None:
                        # Use canonical naming for Zoom and others
                        prefix = "Zoom" if "zoom" in app_id else ("Meet" if entry.is_browser else app_id.capitalize())
                        if exe_clean.lower() == "cpthost":
                            policy_name = f"NetGuard_Zoom_ScreenShare_cpthost_{profile.media_port_start}_{profile.media_port_end}"
                        elif entry.is_browser:
                            policy_name = f"NetGuard_Meet_Media_{exe_clean}_{profile.media_port_start}"
                        elif exe_clean.lower() != entry.exe_names[0].replace(".exe", "").lower():
                            policy_name = f"NetGuard_{prefix}_{exe_clean}_Media_{profile.media_port_start}_{profile.media_port_end}"
                        else:
                            policy_name = f"NetGuard_{prefix}_Media_{profile.media_port_start}_{profile.media_port_end}"

                        specs.append(QoSPolicySpec(
                            name=policy_name,
                            app_name=exe,
                            dscp=target_dscp,
                            protocol="UDP",
                            port_start=profile.media_port_start,
                            port_end=profile.media_port_end,
                            is_dest_port=profile.is_dest_port,
                            precedence=200,
                            policy_store="ActiveStore",
                        ))

                # STUN / TURN port specs
                if profile.stun_ports:
                    prefix = "Zoom" if "zoom" in app_id else app_id.capitalize()
                    specs.append(QoSPolicySpec(
                        name=f"NetGuard_{prefix}_STUN_{profile.stun_ports[0]}_{profile.stun_ports[1]}",
                        app_name=exe,
                        dscp=target_dscp,
                        protocol="UDP",
                        port_start=profile.stun_ports[0],
                        port_end=profile.stun_ports[1],
                        is_dest_port=True,
                        precedence=200,
                        policy_store="ActiveStore",
                    ))
                elif profile.stun_port:
                    specs.append(QoSPolicySpec(
                        name=f"NetGuard_Meet_STUN_{exe_clean}_{profile.stun_port}",
                        app_name=exe,
                        dscp=target_dscp,
                        protocol="UDP",
                        port=profile.stun_port,
                        is_dest_port=True,
                        precedence=200,
                        policy_store="ActiveStore",
                    ))
            else:
                # Fallback profile for apps with no known ports (Slack, Discord, Skype, Webex):
                # Marks ALL outbound UDP of that app AF41, NEVER TCP!
                specs.append(QoSPolicySpec(
                    name=f"NetGuard_{app_id.capitalize()}_Fallback_UDP_{exe_clean}",
                    app_name=exe,
                    dscp=target_dscp,
                    protocol="UDP",
                    precedence=200,
                    policy_store="ActiveStore",
                ))

    # 4. Adaptive upload throttle for bulk sync and download applications
    # Absolute safety rule: svchost.exe and protected system exes must NEVER be throttled
    safe_bulk_apps = [
        b for b in active_bulk_apps
        if b.lower() not in PROTECTED_PROCESSES and not b.lower().startswith("svchost")
    ]

    if safe_bulk_apps:
        per_app_throttle = compute_adaptive_upload_throttle(
            available_uplink_mbps=available_uplink_mbps,
            video_tier=video_tier,
            active_bulk_app_count=len(safe_bulk_apps),
            config=cfg,
        )
        for bulk_app in safe_bulk_apps:
            # Bulk policies must carry BOTH DSCPAction 8 AND ThrottleRateActionBitsPerSecond
            # and MUST have protocol=None (no -IPProtocolMatchCondition) so TCP sync is throttled!
            specs.append(QoSPolicySpec(
                name=f"NetGuard_Throttle_{bulk_app}",
                app_name=bulk_app,
                dscp=cfg.background_default_dscp,
                throttle_bps=per_app_throttle,
                protocol=None,
                precedence=100,
                policy_store="ActiveStore",
            ))

    return specs


# =============================================================================
# WINDOWS QOS CONDITION SPECIFICITY & CONFLICT RESOLUTION SIMULATION
# =============================================================================

@dataclass
class QoSPacket:
    """Represents a simulated outbound network packet for QoS policy matching."""
    app_name: str
    protocol: str  # "TCP" or "UDP"
    src_port: int = 0
    dst_port: int = 0


def compute_policy_specificity(spec: QoSPolicySpec) -> int:
    """Computes Windows QoS condition specificity level (0 to 3).
    
    Level 3: AppPathName + IPProtocol + Port/Range (e.g. zoom.exe + UDP + 8801-8810)
    Level 2: AppPathName + IPProtocol OR Protocol + Port/Range (e.g. slack.exe + UDP, OR UDP + 53)
    Level 1: AppPathName only (e.g. onedrive.exe, netguard.exe, svchost.exe)
    Level 0: -Default catch-all (matches all outbound packets)
    """
    if spec.is_default:
        return 0
    has_app = bool(spec.app_name)
    has_proto = bool(spec.protocol)
    has_port = (spec.port is not None) or (spec.port_start is not None and spec.port_end is not None)

    if has_app and has_proto and has_port:
        return 3
    if (has_app and has_proto) or (has_proto and has_port) or (has_app and has_port):
        return 2
    if has_app:
        return 1
    return 0


def policy_matches_packet(spec: QoSPolicySpec, packet: QoSPacket) -> bool:
    """Checks whether a QoSPolicySpec condition matches a given packet."""
    if spec.is_default:
        return True

    pkt_app = (packet.app_name or "").lower()
    pkt_proto = (packet.protocol or "").upper()
    pkt_src = packet.src_port
    pkt_dst = packet.dst_port

    if spec.app_name:
        spec_app = spec.app_name.lower()
        if not (pkt_app == spec_app or pkt_app.endswith(f"\\{spec_app}") or pkt_app.endswith(f"/{spec_app}")):
            return False

    if spec.protocol:
        if spec.protocol.upper() != pkt_proto:
            return False

    if spec.port_start is not None and spec.port_end is not None:
        port_to_check = pkt_dst if spec.is_dest_port else pkt_src
        if not (spec.port_start <= port_to_check <= spec.port_end):
            return False
    elif spec.port is not None:
        port_to_check = pkt_dst if spec.is_dest_port else pkt_src
        if port_to_check != spec.port:
            return False

    return True


def resolve_winning_policy(packet: QoSPacket, specs: List[QoSPolicySpec]) -> Optional[QoSPolicySpec]:
    """Simulates Windows NetQos kernel arbitration across matching condition specificity and precedence.
    
    Windows QoS resolves conflicts by:
    1. Condition Specificity: More specific match condition dominates (Level 3 > Level 2 > Level 1 > Level 0).
    2. Numeric Precedence: When matching policies cross dimensions or share specificity, higher Precedence wins.
    """
    matching = [s for s in specs if policy_matches_packet(s, packet)]
    if not matching:
        return None

    # Sort matching candidates: highest specificity first, then highest numeric precedence
    matching.sort(key=lambda s: (compute_policy_specificity(s), s.precedence or 0), reverse=True)
    return matching[0]


# 14 Canonical Verification Scenarios defined in R2
POLICY_OVERLAP_14_SCENARIOS = [
    {
        "id": 1,
        "name": "Zoom Outbound Media",
        "packet": QoSPacket(app_name="zoom.exe", protocol="UDP", dst_port=8801),
        "expected_name_contains": "Zoom_Media",
        "expected_dscp": 34,
        "expected_throttle": False,
    },
    {
        "id": 2,
        "name": "Zoom Screen Sharing",
        "packet": QoSPacket(app_name="cpthost.exe", protocol="UDP", dst_port=8805),
        "expected_name_contains": "Zoom_ScreenShare_cpthost",
        "expected_dscp": 34,
        "expected_throttle": False,
    },
    {
        "id": 3,
        "name": "Zoom STUN/TURN",
        "packet": QoSPacket(app_name="zoom.exe", protocol="UDP", dst_port=3478),
        "expected_name_contains": "Zoom_STUN",
        "expected_dscp": 34,
        "expected_throttle": False,
    },
    {
        "id": 4,
        "name": "Zoom Signaling / TLS",
        "packet": QoSPacket(app_name="zoom.exe", protocol="TCP", dst_port=443),
        "expected_name_contains": "Exempt_zoom_TCP443",
        "expected_dscp": 0,
        "expected_throttle": False,
    },
    {
        "id": 5,
        "name": "DNS Outbound (Bulk App)",
        "packet": QoSPacket(app_name="onedrive.exe", protocol="UDP", dst_port=53),
        "expected_name_contains": "Exempt_DNS_UDP",
        "expected_dscp": 0,
        "expected_throttle": False,
    },
    {
        "id": 6,
        "name": "NetGuard Probes & Telemetry",
        "packet": QoSPacket(app_name="netguard.exe", protocol="TCP", dst_port=80),
        "expected_name_contains": "Exempt_App",
        "expected_dscp": 0,
        "expected_throttle": False,
    },
    {
        "id": 7,
        "name": "Windows System Services",
        "packet": QoSPacket(app_name="svchost.exe", protocol="TCP", dst_port=443),
        "expected_name_contains": "Exempt_Svchost",
        "expected_dscp": 0,
        "expected_throttle": False,
    },
    {
        "id": 8,
        "name": "Bulk Upload / Sync (TCP)",
        "packet": QoSPacket(app_name="onedrive.exe", protocol="TCP", dst_port=443),
        "expected_name_contains": "Throttle_onedrive",
        "expected_dscp": 8,
        "expected_throttle": True,
    },
    {
        "id": 9,
        "name": "Bulk Upload / Sync (UDP)",
        "packet": QoSPacket(app_name="qbittorrent.exe", protocol="UDP", dst_port=6881),
        "expected_name_contains": "Throttle_qbittorrent",
        "expected_dscp": 8,
        "expected_throttle": True,
    },
    {
        "id": 10,
        "name": "General Background Traffic",
        "packet": QoSPacket(app_name="notepad.exe", protocol="TCP", dst_port=80),
        "expected_name_contains": "Default_CS1",
        "expected_dscp": 8,
        "expected_throttle": False,
    },
    {
        "id": 11,
        "name": "Teams Media (Default Mode)",
        "packet": QoSPacket(app_name="teams.exe", protocol="UDP", src_port=50010, dst_port=3478),
        "expected_name_contains": "Teams_Media",
        "expected_dscp": 34,
        "expected_throttle": False,
    },
    {
        "id": 12,
        "name": "Teams Media (Port Split Mode)",
        "packet": QoSPacket(app_name="teams.exe", protocol="UDP", src_port=50010, dst_port=3478),
        "expected_name_contains": "Teams_Audio",
        "expected_dscp": 46,
        "expected_throttle": False,
    },
    {
        "id": 13,
        "name": "Google Meet WebRTC Media",
        "packet": QoSPacket(app_name="chrome.exe", protocol="UDP", dst_port=19302),
        "expected_name_contains": "Meet_Media_chrome",
        "expected_dscp": 34,
        "expected_throttle": False,
    },
    {
        "id": 14,
        "name": "Fallback Meeting Apps",
        "packet": QoSPacket(app_name="slack.exe", protocol="UDP", dst_port=12345),
        "expected_name_contains": "Slack_Fallback_UDP",
        "expected_dscp": 34,
        "expected_throttle": False,
    },
]


def verify_policy_overlap_matrix(
    specs: Optional[List[QoSPolicySpec]] = None,
    specs_split: Optional[List[QoSPolicySpec]] = None,
) -> Dict[str, Any]:
    """Evaluates policies against the 14 scenarios and returns structured verification report.
    
    If specs is omitted, automatically constructs canonical policy sets for both
    Teams default mode (AF41) and Teams opt-in port split mode (EF audio, AF41 video, AF21 sharing).
    """
    if specs is None:
        specs_default = build_meeting_qos_specs(
            active_meeting_apps=["zoom.exe", "teams.exe", "chrome.exe", "slack.exe"],
            active_bulk_apps=["onedrive.exe", "qbittorrent.exe"],
            config=AppQoSConfig(enable_teams_port_split=False),
        )
    else:
        specs_default = specs

    if specs_split is None:
        specs_split_mode = build_meeting_qos_specs(
            active_meeting_apps=["zoom.exe", "teams.exe", "chrome.exe", "slack.exe"],
            active_bulk_apps=["onedrive.exe", "qbittorrent.exe"],
            config=AppQoSConfig(enable_teams_port_split=True),
        )
    else:
        specs_split_mode = specs_split

    results = []
    all_passed = True

    for sc in POLICY_OVERLAP_14_SCENARIOS:
        pkt = sc["packet"]
        # Scenario 12 specifically tests Teams Port Split Mode policies
        active_specs = specs_split_mode if sc["id"] == 12 else specs_default
        winner = resolve_winning_policy(pkt, active_specs)
        if not winner:
            passed = False
            details = "No matching policy found"
        else:
            name_ok = sc["expected_name_contains"] in winner.name
            dscp_ok = (winner.dscp == sc["expected_dscp"])
            throttle_ok = bool(winner.throttle_bps) == sc["expected_throttle"]
            passed = name_ok and dscp_ok and throttle_ok
            details = (
                f"Winner: {winner.name} (DSCP={winner.dscp}, Throttle={bool(winner.throttle_bps)}, "
                f"Prec={winner.precedence}, SpecLevel={compute_policy_specificity(winner)})"
            )

        if not passed:
            all_passed = False

        results.append({
            "id": sc["id"],
            "name": sc["name"],
            "packet": f"{pkt.app_name} {pkt.protocol} src={pkt.src_port} dst={pkt.dst_port}",
            "passed": passed,
            "details": details,
        })

    return {
        "success": all_passed,
        "total": len(POLICY_OVERLAP_14_SCENARIOS),
        "passed_count": sum(1 for r in results if r["passed"]),
        "scenarios": results,
    }

