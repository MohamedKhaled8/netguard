"""Application Identification and Workload Profiling."""

from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class WorkloadCategory(str, Enum):
    CONFERENCING = "conferencing"
    GAMING = "gaming"
    STREAMING = "streaming"
    BROWSING = "browsing"
    DOWNLOAD = "download"
    SYSTEM = "system"
    BACKGROUND = "background"
    UNKNOWN = "unknown"


class ProcessNetworkProfile(BaseModel):
    """Network consumption profile for an active process."""
    model_config = ConfigDict(frozen=True)

    pid: int
    name: str
    category: WorkloadCategory
    priority_level: int = Field(default=3, ge=1, le=5)  # 1 = Highest, 5 = Bulk
    active_socket_count: int = 0
    remote_endpoints: List[str] = Field(default_factory=list)
    is_protected_system_process: bool = False
    is_estimated: bool = True
    estimated_bandwidth_mbps: Optional[float] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ApplicationCatalog:
    """Catalog of known application executables and their traffic profiles."""

    SIGNATURES: Dict[str, tuple[WorkloadCategory, int]] = {
        # Real-time Video / Voice Conferencing (Priority 1)
        "zoom.exe": (WorkloadCategory.CONFERENCING, 1),
        "teams.exe": (WorkloadCategory.CONFERENCING, 1),
        "ms-teams.exe": (WorkloadCategory.CONFERENCING, 1),
        "discord.exe": (WorkloadCategory.CONFERENCING, 1),
        "skype.exe": (WorkloadCategory.CONFERENCING, 1),
        "slack.exe": (WorkloadCategory.CONFERENCING, 2),

        # Online Gaming (Priority 1)
        "valorant.exe": (WorkloadCategory.GAMING, 1),
        "cs2.exe": (WorkloadCategory.GAMING, 1),
        "dota2.exe": (WorkloadCategory.GAMING, 1),
        "leagueclient.exe": (WorkloadCategory.GAMING, 1),
        "overwatch.exe": (WorkloadCategory.GAMING, 1),
        "steam.exe": (WorkloadCategory.GAMING, 2),

        # Streaming Media (Priority 2)
        "spotify.exe": (WorkloadCategory.STREAMING, 2),
        "netflix.exe": (WorkloadCategory.STREAMING, 2),
        "vlc.exe": (WorkloadCategory.STREAMING, 2),

        # Browsers (Priority 3)
        "chrome.exe": (WorkloadCategory.BROWSING, 3),
        "firefox.exe": (WorkloadCategory.BROWSING, 3),
        "msedge.exe": (WorkloadCategory.BROWSING, 3),
        "brave.exe": (WorkloadCategory.BROWSING, 3),

        # Bulk Downloads & Torrenting (Priority 5)
        "qbittorrent.exe": (WorkloadCategory.DOWNLOAD, 5),
        "utorrent.exe": (WorkloadCategory.DOWNLOAD, 5),
        "epicgameslauncher.exe": (WorkloadCategory.DOWNLOAD, 4),
        "idman.exe": (WorkloadCategory.DOWNLOAD, 5),
    }

    PROTECTED_SYSTEM_NAMES = {
        "system",
        "registry",
        "smss.exe",
        "csrss.exe",
        "wininit.exe",
        "services.exe",
        "lsass.exe",
        "svchost.exe",
        "explorer.exe",
        "dwm.exe",
        "spoolsv.exe",
        "netguard.exe",
        "python.exe",
        "pythonw.exe",
    }

    @classmethod
    def classify(cls, process_name: str) -> tuple[WorkloadCategory, int, bool]:
        """Returns (category, priority, is_protected)."""
        lower = process_name.lower()
        if lower in cls.PROTECTED_SYSTEM_NAMES:
            return WorkloadCategory.SYSTEM, 1, True

        match = cls.SIGNATURES.get(lower)
        if match:
            return match[0], match[1], False

        return WorkloadCategory.UNKNOWN, 3, False
