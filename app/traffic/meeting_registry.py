"""Authoritative Data-Driven Meeting Application Registry and Media Profiles for NetGuard AI.

Provides a single generic registry for all conferencing applications and browser-based
meetings, defining their executable names, packaged-app identifiers, media profiles,
official vendor documentation citations, and concrete DNS hostnames.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set


@dataclass
class MediaProfile:
    """QoS media profile specifying port ranges, protocol, and DSCP marking actions."""
    has_known_ports: bool = False
    media_port_start: Optional[int] = None
    media_port_end: Optional[int] = None
    media_port: Optional[int] = None
    is_dest_port: bool = True  # True if matching destination port, False if matching client source port
    stun_ports: Optional[Tuple[int, int]] = None
    stun_port: Optional[int] = None
    default_dscp: int = 34     # AF41 (DSCP 34) -> WMM AC_VI (RFC 8325 safe)
    audio_only_dscp: Optional[int] = None  # EF (DSCP 46) only when provably audio-only
    has_stream_split: bool = False
    audio_ports: Optional[Tuple[int, int]] = None
    video_ports: Optional[Tuple[int, int]] = None
    sharing_ports: Optional[Tuple[int, int]] = None
    doc_url: str = ""
    doc_notes: str = ""


@dataclass
class MeetingAppEntry:
    """Registry entry defining an individual meeting application or suite."""
    id: str
    display_name: str
    exe_names: List[str]
    packaged_family_names: List[str] = field(default_factory=list)
    media_profile: MediaProfile = field(default_factory=MediaProfile)
    is_browser: bool = False
    extra_exes: List[str] = field(default_factory=list)  # Secondary helper processes (e.g. CptHost.exe)
    concrete_domains: List[str] = field(default_factory=list)


class MeetingAppRegistry:
    """Data-driven registry containing all supported meeting applications."""

    # 1. Zoom Cloud Meetings
    # CptHost.exe: Zoom's dedicated Windows process for screen sharing / content presentation
    # Port ranges: UDP 8801-8810 (media destination), STUN UDP 3478-3479
    # Docs: Zoom Network Firewall Support KB0060548: https://support.zoom.com/hc/en/article?id=zm_kb&sysparm_article=KB0060548
    ZOOM = MeetingAppEntry(
        id="zoom",
        display_name="Zoom Cloud Meetings",
        exe_names=["zoom.exe"],
        extra_exes=["cpthost.exe"],
        media_profile=MediaProfile(
            has_known_ports=True,
            media_port_start=8801,
            media_port_end=8810,
            is_dest_port=True,
            stun_ports=(3478, 3479),
            default_dscp=34,
            audio_only_dscp=46,
            doc_url="https://support.zoom.com/hc/en/article?id=zm_kb&sysparm_article=KB0060548",
            doc_notes="Zoom UDP 8801-8810 media destination ports, UDP 3478-3479 STUN. CptHost.exe handles screen share.",
        ),
        concrete_domains=[
            "zoom.us",
            "api.zoom.us",
            "us04web.zoom.us",
            "us05web.zoom.us",
            "zoomgov.com",
            "otx.zoom.us",
        ],
    )

    # 2. Microsoft Teams (Classic and New Packaged Teams)
    # Docs: Microsoft Teams QoS in Teams: https://learn.microsoft.com/en-us/microsoftteams/qos-in-teams
    # Note: Tenant admin must configure port ranges for split to work.
    # Default is all Teams UDP media -> AF41 (34).
    TEAMS = MeetingAppEntry(
        id="teams",
        display_name="Microsoft Teams",
        exe_names=["teams.exe", "ms-teams.exe"],
        packaged_family_names=["MicrosoftTeams", "MicrosoftTeams_8wekyb3d8bbwe"],
        media_profile=MediaProfile(
            has_known_ports=True,
            media_port_start=50000,
            media_port_end=50059,
            is_dest_port=False,  # Client source ports configured in Teams client
            stun_ports=(3478, 3481),
            default_dscp=34,
            has_stream_split=True,
            audio_ports=(50000, 50019),
            video_ports=(50020, 50039),
            sharing_ports=(50040, 50059),
            doc_url="https://learn.microsoft.com/en-us/microsoftteams/qos-in-teams",
            doc_notes="Microsoft Teams client ports 50000-50059. Default all UDP media AF41 (34); 46/34/18 split is opt-in.",
        ),
        concrete_domains=[
            "teams.microsoft.com",
            "teams.live.com",
            "statics.teams.cdn.office.net",
            "login.microsoftonline.com",
            "config.edge.skype.com",
        ],
    )

    # 3. Google Meet / WebRTC (Browsers)
    # Docs: Google Workspace Admin Meet Network Requirements: https://support.google.com/a/answer/1279090
    # Media ports: UDP 19302-19309 (destination), STUN UDP 3478
    BROWSERS = MeetingAppEntry(
        id="browsers",
        display_name="Google Meet / WebRTC Call",
        exe_names=["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe", "vivaldi.exe"],
        is_browser=True,
        media_profile=MediaProfile(
            has_known_ports=True,
            media_port_start=19302,
            media_port_end=19309,
            is_dest_port=True,
            stun_port=3478,
            default_dscp=34,
            audio_only_dscp=46,
            doc_url="https://support.google.com/a/answer/1279090",
            doc_notes="Google Meet WebRTC UDP 19302-19309 media destination ports, UDP 3478 STUN.",
        ),
        concrete_domains=[
            "meet.google.com",
            "apis.google.com",
            "connectivitycheck.gstatic.com",
            "clients1.google.com",
        ],
    )

    # 4. Slack (Huddles)
    # Slack vendor documents NO static client UDP port range for Slack Huddles.
    # Fallback profile: marks all outbound UDP of slack.exe AF41 while in a call. Never TCP.
    SLACK = MeetingAppEntry(
        id="slack",
        display_name="Slack Huddle",
        exe_names=["slack.exe"],
        media_profile=MediaProfile(
            has_known_ports=False,
            default_dscp=34,
            doc_url="",
            doc_notes="Vendor documents no static client UDP ports; fallback profile marks all outbound UDP AF41.",
        ),
        concrete_domains=[
            "slack.com",
            "edge.slack.com",
            "app.slack.com",
            "slack-msgs.com",
        ],
    )

    # 5. Discord (Voice & Video)
    # Discord uses WebRTC on dynamic ephemeral ports (no vendor-guaranteed static port range on client).
    # Fallback profile: marks all outbound UDP of discord.exe AF41 while in a call. Never TCP.
    DISCORD = MeetingAppEntry(
        id="discord",
        display_name="Discord",
        exe_names=["discord.exe"],
        media_profile=MediaProfile(
            has_known_ports=False,
            default_dscp=34,
            doc_url="",
            doc_notes="Vendor documents no static client UDP ports; fallback profile marks all outbound UDP AF41.",
        ),
        concrete_domains=[
            "discord.com",
            "discord.gg",
            "gateway.discord.gg",
            "discordapp.com",
            "status.discord.com",
        ],
    )

    # 6. Skype (Standalone and Packaged App)
    # Skype for Windows 10/11 uses dynamic UDP media ports.
    # Fallback profile: marks all outbound UDP of skype.exe / skypeapp.exe AF41 while in a call. Never TCP.
    SKYPE = MeetingAppEntry(
        id="skype",
        display_name="Skype",
        exe_names=["skype.exe", "skypeapp.exe"],
        packaged_family_names=["Microsoft.SkypeApp", "Microsoft.SkypeApp_kzf8qxf38zg5c"],
        media_profile=MediaProfile(
            has_known_ports=False,
            default_dscp=34,
            doc_url="",
            doc_notes="Vendor documents no static client UDP ports; fallback profile marks all outbound UDP AF41.",
        ),
        concrete_domains=[
            "skype.com",
            "api.skype.com",
            "client-s.gateway.messenger.live.com",
        ],
    )

    # 7. Cisco Webex
    # Docs: Cisco Webex Network Requirements: https://help.webex.com/en-us/article/WBX264/Network-Requirements-for-Webex-Services
    # Without centralized enterprise GPO, Webex client ports are dynamic.
    # Fallback profile: marks all outbound UDP of Webex executables AF41 while in a call. Never TCP.
    WEBEX = MeetingAppEntry(
        id="webex",
        display_name="Cisco Webex",
        exe_names=["webexmta.exe", "ciscowebexstart.exe", "webex.exe", "atmgr.exe"],
        media_profile=MediaProfile(
            has_known_ports=False,
            default_dscp=34,
            doc_url="https://help.webex.com/en-us/article/WBX264/Network-Requirements-for-Webex-Services",
            doc_notes="Without enterprise GPO, Webex client UDP ports are dynamic; fallback profile marks all outbound UDP AF41.",
        ),
        concrete_domains=[
            "webex.com",
            "api.webex.com",
            "idbroker.webex.com",
            "clients.webex.com",
        ],
    )

    _REGISTRY: List[MeetingAppEntry] = [
        ZOOM,
        TEAMS,
        BROWSERS,
        SLACK,
        DISCORD,
        SKYPE,
        WEBEX,
    ]

    @classmethod
    def all_entries(cls) -> List[MeetingAppEntry]:
        """Returns all registered meeting application entries."""
        return list(cls._REGISTRY)

    @classmethod
    def get_entry_by_id(cls, app_id: str) -> Optional[MeetingAppEntry]:
        """Find entry by registry ID."""
        for entry in cls._REGISTRY:
            if entry.id.lower() == app_id.lower():
                return entry
        return None

    @classmethod
    def find_entry_for_process(cls, process_name: str) -> Optional[MeetingAppEntry]:
        """Find matching registry entry for a process executable name."""
        proc_lower = process_name.lower()
        for entry in cls._REGISTRY:
            if any(exe.lower() == proc_lower for exe in entry.exe_names):
                return entry
            if any(extra.lower() == proc_lower for extra in entry.extra_exes):
                return entry
        return None

    @classmethod
    def find_entry_for_consent_key(cls, consent_key: str) -> Optional[MeetingAppEntry]:
        """Match a Windows ConsentStore key (NonPackaged path or packaged family name) to an app entry."""
        ck_lower = consent_key.lower()
        # Clean path delimiters and hashes
        clean_name = ck_lower.replace("/", "\\").split("\\")[-1].split("#")[-1]

        for entry in cls._REGISTRY:
            # Check exe names
            if any(exe.lower() in clean_name or clean_name in exe.lower() for exe in entry.exe_names):
                return entry
            # Check packaged family names (e.g. MicrosoftTeams, Microsoft.SkypeApp)
            if any(pkg.lower() in ck_lower for pkg in entry.packaged_family_names):
                return entry
        return None

    @classmethod
    def get_all_concrete_domains(cls) -> List[str]:
        """Returns deduplicated concrete domains across all meeting apps for pre-resolution."""
        domains: List[str] = []
        for entry in cls._REGISTRY:
            for domain in entry.concrete_domains:
                if domain not in domains:
                    domains.append(domain)
        return domains

    @classmethod
    def create_fallback_entry(
        cls,
        app_id: str,
        display_name: Optional[str] = None,
        exe_names: Optional[List[str]] = None,
        default_dscp: int = 34,
    ) -> MeetingAppEntry:
        """Create a generic fallback entry with safe configurable UDP marking (DSCP 34 / AF41) and closed-loop safeguards."""
        clean_id = app_id.lower().replace(".exe", "")
        clean_name = display_name or clean_id.capitalize()
        exes = [e.lower() for e in exe_names] if exe_names else [f"{clean_id}.exe"]
        return MeetingAppEntry(
            id=clean_id,
            display_name=clean_name,
            exe_names=exes,
            media_profile=MediaProfile(
                has_known_ports=False,
                default_dscp=default_dscp,
                doc_notes="Safe fallback UDP profile with closed-loop degradation safeguard",
            ),
        )

    @classmethod
    def register_entry(cls, entry: MeetingAppEntry) -> None:
        """Register a new or dynamic meeting application entry in the registry."""
        for i, existing in enumerate(cls._REGISTRY):
            if existing.id.lower() == entry.id.lower():
                cls._REGISTRY[i] = entry
                return
        cls._REGISTRY.append(entry)

    @classmethod
    def find_or_create_entry(
        cls,
        identifier: str,
        display_name: Optional[str] = None,
        default_dscp: int = 34,
    ) -> MeetingAppEntry:
        """Find existing entry by process name, ID, or consent key, or create a safe fallback entry."""
        entry = (
            cls.find_entry_for_process(identifier)
            or cls.get_entry_by_id(identifier)
            or cls.find_entry_for_consent_key(identifier)
        )
        if entry:
            return entry
        return cls.create_fallback_entry(
            app_id=identifier,
            display_name=display_name,
            default_dscp=default_dscp,
        )

