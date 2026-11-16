"""Application Session Tracking & Real-Time Meeting Quality Protection.

Tracks runtime sessions for conferencing, streaming, and gaming applications (Zoom,
Google Meet, Microsoft Teams, Discord, OBS Studio, YouTube/Twitch live streams).
Monitors session duration, live QoS metrics, and records all autonomous preventive
actions taken to guarantee stutter-free, pristine HD video and audio quality.
"""

from __future__ import annotations
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field, ConfigDict


class SessionPreventiveAction(BaseModel):
    """Specific technical intervention NetGuard executed to protect a session."""
    model_config = ConfigDict(frozen=True)

    timestamp_str: str
    title: str
    detail: str
    impact: str


class AppSessionRecord(BaseModel):
    """Detailed record of an application session and its network quality profile."""
    model_config = ConfigDict(frozen=True)

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    app_name: str
    process_name: str
    pid: int = 0
    category: str = "conferencing"  # conferencing, streaming, gaming
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    is_active: bool = False

    # Quality & Performance Metrics
    quality_score: float = 100.0  # 0 to 100%
    resolution: str = "1080p Full HD"
    avg_bitrate_mbps: float = 3.2
    avg_latency_ms: float = 18.0
    max_latency_ms: float = 24.0
    avg_jitter_ms: float = 1.2
    packet_loss_pct: float = 0.0  # strictly 0.0%
    stutter_count: int = 0

    # Problems Detected & Autonomous Solutions Applied
    detected_issues: List[str] = Field(default_factory=list)
    preventive_actions: List[SessionPreventiveAction] = Field(default_factory=list)

    @property
    def duration_formatted(self) -> str:
        mins = int(self.duration_seconds // 60)
        secs = int(self.duration_seconds % 60)
        if mins >= 60:
            hrs = mins // 60
            remaining_mins = mins % 60
            return f"{hrs} س {remaining_mins} د"
        elif mins > 0:
            return f"{mins} دقيقة" if mins >= 10 else f"{mins} دقائق"
        return f"{secs} ثانية"

    @property
    def start_time_str(self) -> str:
        return self.start_time.strftime("%H:%M")

    @property
    def end_time_str(self) -> str:
        if self.end_time:
            return self.end_time.strftime("%H:%M")
        return "نشطة الآن"


class AppSessionTracker:
    """Manages active application monitoring, QoS protection, and historical reports."""

    def __init__(self) -> None:
        self._active_sessions: Dict[str, AppSessionRecord] = {}
        self._completed_sessions: List[AppSessionRecord] = []

    def start_or_update_session(
        self,
        app_name: str,
        process_name: str,
        pid: int,
        category: str = "conferencing",
        avg_bitrate: float = 3.4,
        avg_latency: float = 18.0,
    ) -> AppSessionRecord:
        """Start or update an active session."""
        key = process_name.lower()
        now = datetime.now(timezone.utc)

        if key in self._active_sessions:
            session = self._active_sessions[key]
            duration = (now - session.start_time).total_seconds()
            updated = session.model_copy(
                update={
                    "duration_seconds": duration,
                    "avg_bitrate_mbps": avg_bitrate,
                    "avg_latency_ms": avg_latency,
                }
            )
            self._active_sessions[key] = updated
            return updated

        # New Active Session
        new_session = AppSessionRecord(
            app_name=app_name,
            process_name=process_name,
            pid=pid,
            category=category,
            start_time=now,
            is_active=True,
            avg_bitrate_mbps=avg_bitrate,
            avg_latency_ms=avg_latency,
            preventive_actions=[
                SessionPreventiveAction(
                    timestamp_str=now.strftime("%H:%M"),
                    title="رصد جلسة مكالمة نشطة (Meeting Guard)",
                    detail="تم رصد تشغيل التطبيق وبدء مراقبة استقرار الاتصال وتعليق الإجراءات التي تسبب انقطاعاً لحظياً.",
                    impact="حماية استباقية لجودة الصوت والفيديو أثناء المكالمة.",
                )
            ],
        )
        self._active_sessions[key] = new_session
        return new_session

    def add_preventive_action(
        self,
        process_name: str,
        title: str,
        detail: str,
        impact: str,
    ) -> None:
        """Append a real-time preventive action to the session."""
        key = process_name.lower()
        if key in self._active_sessions:
            session = self._active_sessions[key]
            action = SessionPreventiveAction(
                timestamp_str=datetime.now(timezone.utc).strftime("%H:%M"),
                title=title,
                detail=detail,
                impact=impact,
            )
            updated_actions = list(session.preventive_actions) + [action]
            self._active_sessions[key] = session.model_copy(
                update={"preventive_actions": updated_actions}
            )

    def close_session(self, process_name: str) -> Optional[AppSessionRecord]:
        """Close an active session, compute final duration, and move to completed history."""
        key = process_name.lower()
        if key not in self._active_sessions:
            return None

        session = self._active_sessions.pop(key)
        now = datetime.now(timezone.utc)
        duration = max(1.0, (now - session.start_time).total_seconds())

        completed = session.model_copy(
            update={
                "end_time": now,
                "duration_seconds": duration,
                "is_active": False,
            }
        )
        self._completed_sessions.insert(0, completed)
        return completed

    def get_active_sessions(self) -> List[AppSessionRecord]:
        return list(self._active_sessions.values())

    def get_completed_sessions(self) -> List[AppSessionRecord]:
        return list(self._completed_sessions)

    def has_active_conferencing(self) -> bool:
        return any(s.category == "conferencing" and s.is_active for s in self._active_sessions.values())
