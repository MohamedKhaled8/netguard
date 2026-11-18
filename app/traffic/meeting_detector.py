"""Authoritative Multi-Signal Meeting Detector, QoS Priority Classes, and Quality Advisor (Stage D)."""

from __future__ import annotations
import sys
import os
import time
from enum import IntEnum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from PySide6.QtCore import QObject, Signal
import psutil


class TrafficPriorityClass(IntEnum):
    """Network priority class hierarchy (Item D2)."""
    REALTIME = 1     # Active video/voice meetings (Zoom, WebRTC)
    INTERACTIVE = 2  # Active foreground app, general browsing, DNS queries
    BULK = 3         # Background downloads, cloud sync (OneDrive, torrents, Steam)
    PROTECTED = 4    # OS critical services (svchost, System, lsass) - NEVER touch


@dataclass
class MeetingState:
    """Multi-signal observable meeting status (Item D1)."""
    is_active: bool = False
    app_name: str = ""
    app_type: str = "app"  # "app" | "browser"
    process_name: str = ""
    pid: int = 0
    started_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    audio_quality: str = "ممتاز"
    video_quality: str = "1080p Full HD"
    signals_detected: List[str] = field(default_factory=list)


class MeetingDetector(QObject):
    """Detects active video/voice meetings using multi-signal correlation (Item D1)."""

    state_changed = Signal(object)  # Emits MeetingState

    KNOWN_CONFERENCING_EXES = {
        "zoom.exe": "Zoom Cloud Meetings",
        "teams.exe": "Microsoft Teams",
        "ms-teams.exe": "Microsoft Teams",
        "webexmta.exe": "Cisco Webex",
        "slack.exe": "Slack Huddle",
        "discord.exe": "Discord",
    }

    BROWSER_EXES = {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"}

    BULK_DOWNLOAD_EXES = {
        "onedrive.exe", "dropbox.exe", "googledrivesync.exe",
        "qbittorrent.exe", "utorrent.exe", "steam.exe",
        "epicgameslauncher.exe", "idman.exe", "battle.net.exe"
    }

    PROTECTED_SYSTEM_EXES = {
        "system", "registry", "smss.exe", "csrss.exe", "wininit.exe",
        "services.exe", "lsass.exe", "svchost.exe", "explorer.exe",
        "dwm.exe", "spoolsv.exe", "netguard.exe", "python.exe", "pythonw.exe"
    }

    WEBRTC_PORTS = {3478, 19302, 19303, 19304, 19305, 19306, 19307, 19308, 19309}

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._current_state = MeetingState()
        self._meeting_start_time: Optional[datetime] = None

    @property
    def current(self) -> MeetingState:
        return self._current_state

    def classify_process_priority(self, process_name: str, has_meeting_active: bool = False) -> TrafficPriorityClass:
        """Assign honest priority class based on process role (Item D2)."""
        lower = process_name.lower()
        if lower in self.PROTECTED_SYSTEM_EXES:
            return TrafficPriorityClass.PROTECTED

        if lower in self.KNOWN_CONFERENCING_EXES:
            return TrafficPriorityClass.REALTIME

        if lower in self.BULK_DOWNLOAD_EXES:
            return TrafficPriorityClass.BULK

        # Browsers: if WebRTC active or general browsing, never outranks meeting!
        if lower in self.BROWSER_EXES:
            if has_meeting_active and self._current_state.app_type == "browser" and self._current_state.process_name.lower() == lower:
                return TrafficPriorityClass.REALTIME
            return TrafficPriorityClass.INTERACTIVE

        return TrafficPriorityClass.INTERACTIVE

    def check_windows_consent_store(self) -> List[str]:
        """Check Windows CapabilityAccessManager for actively running mic/webcam sessions."""
        active = []
        if sys.platform != "win32":
            return active
        try:
            import winreg
            for cap in ["microphone", "webcam"]:
                root_path = f"Software\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\{cap}"
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, root_path) as root_key:
                        n_sub, _, _ = winreg.QueryInfoKey(root_key)
                        for i in range(n_sub):
                            sub_name = winreg.EnumKey(root_key, i)
                            if sub_name == "NonPackaged":
                                try:
                                    with winreg.OpenKey(root_key, "NonPackaged") as np_key:
                                        n2, _, _ = winreg.QueryInfoKey(np_key)
                                        for j in range(n2):
                                            app_k = winreg.EnumKey(np_key, j)
                                            with winreg.OpenKey(np_key, app_k) as ak:
                                                try:
                                                    stop, _ = winreg.QueryValueEx(ak, "LastUsedTimeStop")
                                                    if stop == 0:
                                                        app_clean = app_k.split("#")[-1].split("\\")[-1]
                                                        active.append(f"{cap}:{app_clean}")
                                                except OSError:
                                                    pass
                                except OSError:
                                    pass
                            else:
                                with winreg.OpenKey(root_key, sub_name) as ak:
                                    try:
                                        stop, _ = winreg.QueryValueEx(ak, "LastUsedTimeStop")
                                        if stop == 0:
                                            active.append(f"{cap}:{sub_name}")
                                    except OSError:
                                        pass
                except OSError:
                    pass
        except Exception:
            pass
        return active

    def detect_meeting(self) -> MeetingState:
        """Correlate process, consent store, and WebRTC sockets to detect meetings."""
        signals = []
        active_app_name = ""
        process_name = ""
        pid = 0
        app_type = "app"

        # Signal 1: Known conferencing processes
        for p in psutil.process_iter(["pid", "name"]):
            try:
                pname = p.info["name"] or ""
                pname_lower = pname.lower()
                if pname_lower in self.KNOWN_CONFERENCING_EXES:
                    signals.append(f"process:{pname_lower}")
                    active_app_name = self.KNOWN_CONFERENCING_EXES[pname_lower]
                    process_name = pname
                    pid = p.info["pid"]
                    app_type = "app"
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Signal 2: Microphone or Webcam actively in use in Windows
        consent_signals = self.check_windows_consent_store()
        signals.extend(consent_signals)

        # Signal 3: WebRTC UDP streams in browsers if standalone app not found
        if not active_app_name:
            try:
                for conn in psutil.net_connections(kind="udp"):
                    if conn.raddr and conn.raddr.port in self.WEBRTC_PORTS:
                        try:
                            proc = psutil.Process(conn.pid) if conn.pid else None
                            if proc and proc.name().lower() in self.BROWSER_EXES:
                                signals.append(f"webrtc:{conn.raddr.port}")
                                active_app_name = "Google Meet / Browser Call"
                                process_name = proc.name()
                                pid = proc.pid
                                app_type = "browser"
                                break
                        except Exception:
                            pass
            except Exception:
                pass

        # If microphone is active for a browser, recognize as WebRTC call
        if not active_app_name:
            for s in consent_signals:
                for b_exe in self.BROWSER_EXES:
                    if b_exe in s.lower():
                        active_app_name = "Google Meet / Teams Web"
                        process_name = b_exe
                        app_type = "browser"
                        break

        is_active = bool(active_app_name)
        now = datetime.now(timezone.utc)

        if is_active:
            if not self._current_state.is_active or self._meeting_start_time is None:
                self._meeting_start_time = now
            duration = (now - self._meeting_start_time).total_seconds()
        else:
            self._meeting_start_time = None
            duration = 0.0

        new_state = MeetingState(
            is_active=is_active,
            app_name=active_app_name,
            app_type=app_type,
            process_name=process_name,
            pid=pid,
            started_at=self._meeting_start_time,
            duration_seconds=duration,
            signals_detected=signals,
        )

        if (
            new_state.is_active != self._current_state.is_active
            or new_state.app_name != self._current_state.app_name
        ):
            self._current_state = new_state
            self.state_changed.emit(new_state)
        else:
            self._current_state = new_state

        return self._current_state


def evaluate_video_readiness(
    upload_mbps: float,
    packet_loss_pct: float,
    jitter_ms: float,
) -> Dict[str, Any]:
    """Honest video meeting quality advisor calculation (Item D8)."""
    # 1080p: upload >= 3.0, loss < 1%, jitter < 20
    # 720p: upload >= 1.5, loss < 2%, jitter < 30
    # 360p: upload >= 0.8, loss < 3%, jitter < 40
    # Audio: upload >= 0.1, loss < 5%, jitter < 60

    if upload_mbps >= 3.0 and packet_loss_pct < 1.0 and jitter_ms < 20.0:
        return {
            "tier": "1080p Full HD",
            "is_hd": True,
            "limiting_metric": None,
            "headline": "الشبكة جاهزة لبث 1080p Full HD",
            "detail": "سرعة الرفع وفقدان الحزم والتذبذب ضمن أفضل المعايير العالمية لمكالمات الفيديو.",
        }

    if upload_mbps >= 1.5 and packet_loss_pct < 2.0 and jitter_ms < 30.0:
        limiting = "سرعة الرفع" if upload_mbps < 3.0 else ("فقد الحزم" if packet_loss_pct >= 1.0 else "التذبذب")
        return {
            "tier": "720p HD",
            "is_hd": True,
            "limiting_metric": limiting,
            "headline": f"جاهز لبث 720p HD — العائق لـ 1080p: {limiting} ({upload_mbps:.1f} Mbps)",
            "detail": "جودة ممتازة لمكالمات العمل والاجتماعات دون أي تقطيع.",
        }

    if upload_mbps >= 0.8 and packet_loss_pct < 3.0 and jitter_ms < 40.0:
        limiting = "سرعة الرفع" if upload_mbps < 1.5 else ("فقد الحزم" if packet_loss_pct >= 2.0 else "التذبذب")
        return {
            "tier": "360p SD",
            "is_hd": False,
            "limiting_metric": limiting,
            "headline": f"جاهز لبث 360p SD — العائق لـ HD: {limiting}",
            "detail": "جودة مقبولة. يُنصح بإغلاق الكاميرا أو تقييد التحميلات في حال بطء الصوت.",
        }

    return {
        "tier": "Audio Only",
        "is_hd": False,
        "limiting_metric": "ضعف الاتصال العام",
        "headline": "مكالمة صوتية فقط (Audio Only)",
        "detail": "ظروف الشبكة الحالية لا تسمح ببث فيديو مستقر. أغلق الكاميرا للحفاظ على استمرار الصوت.",
    }


def generate_post_session_report(
    app_name: str,
    duration_seconds: float,
    avg_latency_ms: float,
    max_latency_ms: float,
    avg_jitter_ms: float,
    packet_loss_pct: float,
    local_gateway_latency_ms: float,
    disruptions_prevented: int = 1,
) -> Dict[str, Any]:
    """Generate honest post-meeting health report without blaming local network falsely (Item D7)."""
    mins = int(duration_seconds // 60)
    dur_str = f"{mins} دقيقة" if mins > 0 else f"{int(duration_seconds)} ثانية"

    # Honest verdict logic:
    if packet_loss_pct < 0.5 and avg_jitter_ms < 15.0:
        verdict = "مكالمة ممتازة — لم تحدث أي انقطاعات صوتية أو مرئية."
        verdict_type = "ok"
    elif local_gateway_latency_ms < 10.0:
        # Local router was completely fine! Blame is remote or cloud!
        verdict = f"حدث تقطيع طفيف — المشكلة من خوادم {app_name} أو الطرف الآخر، شبكتك المحلية كانت سليمة تماماً (استجابة الراوتر {local_gateway_latency_ms:.1f} ms)."
        verdict_type = "external_issue"
    else:
        # Local issue
        verdict = f"حدث تقطيع — السبب: تراجع جودة الاتصال المحلي بالراوتر (استجابة الراوتر {local_gateway_latency_ms:.1f} ms)."
        verdict_type = "local_issue"

    return {
        "app_name": app_name,
        "duration_str": dur_str,
        "avg_latency_ms": avg_latency_ms,
        "max_latency_ms": max_latency_ms,
        "avg_jitter_ms": avg_jitter_ms,
        "packet_loss_pct": packet_loss_pct,
        "local_gateway_ms": local_gateway_latency_ms,
        "disruptions_prevented": disruptions_prevented,
        "verdict": verdict,
        "verdict_type": verdict_type,
    }
