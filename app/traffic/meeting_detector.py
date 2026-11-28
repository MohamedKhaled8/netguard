"""Authoritative Multi-Signal Meeting Detector, QoS Priority Classes, and Quality Advisor (Stage D).

Enforces strict dual-condition meeting call detection:
An app is 'in a call' only when BOTH conditions are met for that app:
1) Windows ConsentStore shows microphone or camera actively in use by that app (LastUsedTimeStop == 0)
   (handles NonPackaged path keys and packaged family names, e.g. new Teams, Skype, and browsers).
2) Sustained outbound UDP from that app's processes above a configurable threshold
   (per-PID bytes/s from process IO write deltas + active UDP endpoints).

Apps merely running or signed in (idle Teams, Slack, Discord, Skype, Webex, Zoom) produce
state IDLE, 0 policies, and no DNS freeze.
"""

from __future__ import annotations
import sys
import os
import time
import logging
import threading
import collections
from enum import Enum, IntEnum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple, Set
from PySide6.QtCore import QObject, Signal
import psutil

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes
else:
    ctypes = None
    wintypes = None

from app.traffic.meeting_registry import MeetingAppRegistry, MeetingAppEntry

logger = logging.getLogger("netguard.traffic.meeting_detector")


PROTECTED_PROCESSES = {
    "svchost.exe",
    "system",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "netguard.exe",
    "python.exe",
}


class MeetingModeState(str, Enum):
    """Hysteresis state for meeting mode lifecycle."""
    IDLE = "idle"
    ENTERING = "entering"  # Detected, confirming stability for 5s
    ACTIVE = "active"      # Confirmed active meeting mode
    LEAVING = "leaving"    # Signal absent, waiting 20s before tearing down


class MeetingHysteresisTracker:
    """Manages entrance (5s) and exit (20s) hysteresis for stable Meeting Mode measured by real elapsed time."""

    ENTER_THRESHOLD_SEC: float = 5.0
    LEAVE_THRESHOLD_SEC: float = 20.0

    def __init__(self, enter_sec: float = 5.0, leave_sec: float = 20.0) -> None:
        self.enter_threshold = enter_sec
        self.leave_threshold = leave_sec
        self._state: MeetingModeState = MeetingModeState.IDLE
        self._first_seen_time: Optional[float] = None
        self._leave_start_time: Optional[float] = None

    @property
    def state(self) -> MeetingModeState:
        return self._state

    def update(self, raw_active: bool, now_mono: float) -> Tuple[MeetingModeState, bool]:
        """Update tracker with raw signal at current monotonic time.
        
        Returns (current_state, state_changed).
        """
        old_state = self._state

        if raw_active:
            if self._state == MeetingModeState.IDLE:
                self._state = MeetingModeState.ENTERING
                self._first_seen_time = now_mono
                self._leave_start_time = None
            elif self._state == MeetingModeState.ENTERING:
                if self._first_seen_time is not None and (now_mono - self._first_seen_time) >= self.enter_threshold:
                    self._state = MeetingModeState.ACTIVE
            elif self._state == MeetingModeState.LEAVING:
                # Signal restored before 20s timeout expired -> resume active
                self._state = MeetingModeState.ACTIVE
                self._leave_start_time = None
            elif self._state == MeetingModeState.ACTIVE:
                self._leave_start_time = None
        else:
            if self._state == MeetingModeState.ENTERING:
                # Transient blip (< 5s) -> abort to idle without ever creating policies
                self._state = MeetingModeState.IDLE
                self._first_seen_time = None
                self._leave_start_time = None
            elif self._state == MeetingModeState.ACTIVE:
                self._state = MeetingModeState.LEAVING
                self._leave_start_time = now_mono
            elif self._state == MeetingModeState.LEAVING:
                if self._leave_start_time is not None and (now_mono - self._leave_start_time) >= self.leave_threshold:
                    self._state = MeetingModeState.IDLE
                    self._first_seen_time = None
                    self._leave_start_time = None

        changed = (self._state != old_state)
        return self._state, changed

    def reset(self) -> None:
        self._state = MeetingModeState.IDLE
        self._first_seen_time = None
        self._leave_start_time = None


class TrafficPriorityClass(IntEnum):
    """Network priority class hierarchy."""
    REALTIME = 1     # Active video/voice meetings in call
    INTERACTIVE = 2  # Active foreground app, general browsing, DNS queries
    BULK = 3         # Background downloads, cloud sync (OneDrive, torrents, Steam)
    PROTECTED = 4    # OS critical services (svchost, System, lsass) - NEVER touch


@dataclass
class MeetingState:
    """Multi-signal observable meeting status."""
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
    is_audio_only: bool = False
    mode_state: MeetingModeState = MeetingModeState.IDLE
    udp_send_bytes_per_sec: float = 0.0
    endpoints: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class CandidateEvaluationDiagnostic:
    """Structured per-cycle diagnostic record for a candidate meeting application/process."""
    pid: int
    process_name: str
    app_id: str
    endpoints: List[str] = field(default_factory=list)
    udp_bytes_per_sec: float = 0.0
    consent_active: bool = False
    confidence: float = 0.0
    is_detected: bool = False
    rejection_reason: Optional[str] = None


class BaseNetworkTelemetryProvider:
    """Abstract interface for per-process network telemetry providers."""

    def is_available(self) -> bool:
        """Whether real per-PID network telemetry is currently active and available."""
        return False

    def get_outbound_udp_rate(self, pids: List[int], now_t: float) -> Tuple[float, List[str]]:
        """Return (outbound_udp_bytes_per_sec, endpoints) for given PIDs."""
        return 0.0, []

    def get_process_udp_endpoints(self, pid: int) -> List[str]:
        """Return list of known UDP endpoints for a PID."""
        return []

    def close(self) -> None:
        """Release underlying system resources."""
        pass


if sys.platform == "win32" and ctypes:
    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_byte * 8),
        ]

    class WNODE_HEADER(ctypes.Structure):
        _fields_ = [
            ("BufferSize", wintypes.ULONG),
            ("ProviderId", wintypes.ULONG),
            ("HistoricalContext", ctypes.c_uint64),
            ("TimeStamp", wintypes.LARGE_INTEGER),
            ("Guid", GUID),
            ("ClientContext", wintypes.ULONG),
            ("Flags", wintypes.ULONG),
        ]

    class EVENT_TRACE_PROPERTIES(ctypes.Structure):
        _fields_ = [
            ("Wnode", WNODE_HEADER),
            ("BufferSize", wintypes.ULONG),
            ("MinimumBuffers", wintypes.ULONG),
            ("MaximumBuffers", wintypes.ULONG),
            ("MaximumFileSize", wintypes.ULONG),
            ("LogFileMode", wintypes.ULONG),
            ("FlushTimer", wintypes.ULONG),
            ("EnableFlags", wintypes.ULONG),
            ("AgeLimit", wintypes.LONG),
            ("NumberOfBuffers", wintypes.ULONG),
            ("FreeBuffers", wintypes.ULONG),
            ("EventsLost", wintypes.ULONG),
            ("BuffersWritten", wintypes.ULONG),
            ("LogBuffersLost", wintypes.ULONG),
            ("RealTimeBuffersLost", wintypes.ULONG),
            ("LoggerThreadId", wintypes.HANDLE),
            ("LogFileNameOffset", wintypes.ULONG),
            ("LoggerNameOffset", wintypes.ULONG),
        ]

    class EVENT_DESCRIPTOR(ctypes.Structure):
        _fields_ = [
            ("Id", wintypes.USHORT),
            ("Version", ctypes.c_ubyte),
            ("Channel", ctypes.c_ubyte),
            ("Level", ctypes.c_ubyte),
            ("Opcode", ctypes.c_ubyte),
            ("Task", wintypes.USHORT),
            ("Keyword", ctypes.c_uint64),
        ]

    class EVENT_HEADER(ctypes.Structure):
        _fields_ = [
            ("Size", wintypes.USHORT),
            ("HeaderType", wintypes.USHORT),
            ("Flags", wintypes.USHORT),
            ("EventProperty", wintypes.USHORT),
            ("ThreadId", wintypes.ULONG),
            ("ProcessId", wintypes.ULONG),
            ("TimeStamp", wintypes.LARGE_INTEGER),
            ("ProviderId", GUID),
            ("EventDescriptor", EVENT_DESCRIPTOR),
            ("ProcessorTime", ctypes.c_uint64),
            ("ActivityId", GUID),
        ]

    class ETW_BUFFER_CONTEXT(ctypes.Structure):
        _fields_ = [
            ("ProcessorNumber", ctypes.c_ubyte),
            ("Alignment", ctypes.c_ubyte),
            ("LoggerId", wintypes.USHORT),
        ]

    class EVENT_HEADER_EXTENDED_DATA_ITEM(ctypes.Structure):
        _fields_ = [
            ("Reserved1", wintypes.USHORT),
            ("ExtType", wintypes.USHORT),
            ("Linkage", ctypes.c_ubyte),
            ("Reserved2", ctypes.c_ubyte),
            ("DataSize", wintypes.USHORT),
            ("DataPtr", ctypes.c_uint64),
        ]

    class EVENT_RECORD(ctypes.Structure):
        pass

    PEVENT_RECORD = ctypes.POINTER(EVENT_RECORD)
    PEVENT_RECORD_CALLBACK = ctypes.WINFUNCTYPE(None, PEVENT_RECORD)

    EVENT_RECORD._fields_ = [
        ("EventHeader", EVENT_HEADER),
        ("BufferContext", ETW_BUFFER_CONTEXT),
        ("ExtendedDataCount", wintypes.USHORT),
        ("UserDataLength", wintypes.USHORT),
        ("ExtendedData", ctypes.POINTER(EVENT_HEADER_EXTENDED_DATA_ITEM)),
        ("UserData", ctypes.c_void_p),
        ("UserContext", ctypes.c_void_p),
    ]

    class TIME_ZONE_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("Bias", wintypes.LONG),
            ("StandardName", wintypes.WCHAR * 32),
            ("StandardDate", ctypes.c_byte * 16),
            ("StandardBias", wintypes.LONG),
            ("DaylightName", wintypes.WCHAR * 32),
            ("DaylightDate", ctypes.c_byte * 16),
            ("DaylightBias", wintypes.LONG),
        ]

    class TRACE_LOGFILE_HEADER(ctypes.Structure):
        _fields_ = [
            ("BufferSize", wintypes.ULONG),
            ("Version", wintypes.ULONG),
            ("ProviderVersion", wintypes.ULONG),
            ("NumberOfProcessors", wintypes.ULONG),
            ("EndTime", wintypes.LARGE_INTEGER),
            ("TimerResolution", wintypes.ULONG),
            ("MaximumFileSize", wintypes.ULONG),
            ("LogFileMode", wintypes.ULONG),
            ("BuffersWritten", wintypes.ULONG),
            ("StartBuffers", wintypes.ULONG),
            ("PointerSize", wintypes.ULONG),
            ("EventsLost", wintypes.ULONG),
            ("CpuSpeedInMHz", wintypes.ULONG),
            ("LoggerName", wintypes.LPWSTR),
            ("LogFileName", wintypes.LPWSTR),
            ("TimeZone", TIME_ZONE_INFORMATION),
            ("BootTime", wintypes.LARGE_INTEGER),
            ("StartTime", wintypes.LARGE_INTEGER),
            ("EventsLost2", wintypes.ULONG),
            ("Reserved", wintypes.ULONG),
        ]

    class EVENT_TRACE_LOGFILEW(ctypes.Structure):
        _fields_ = [
            ("LogFileName", wintypes.LPWSTR),
            ("LoggerName", wintypes.LPWSTR),
            ("CurrentTime", ctypes.c_int64),
            ("BuffersRead", wintypes.ULONG),
            ("ProcessTraceMode", wintypes.ULONG),
            ("CurrentEvent", EVENT_RECORD),
            ("LogfileHeader", TRACE_LOGFILE_HEADER),
            ("BufferCallback", ctypes.c_void_p),
            ("BufferSize", wintypes.ULONG),
            ("Filled", wintypes.ULONG),
            ("EventsLost", wintypes.ULONG),
            ("EventRecordCallback", PEVENT_RECORD_CALLBACK),
            ("IsKernelTrace", wintypes.ULONG),
            ("Context", ctypes.c_void_p),
        ]


class WindowsETWNetworkTelemetry(BaseNetworkTelemetryProvider):
    """Windows ETW provider measuring real per-process outbound UDP network send events.
    
    Traces:
    - Microsoft-Windows-Kernel-Network {7DD42A49-5329-4832-8DFD-43D979153A88} Event 42 (UdpSend)
    - Microsoft-Windows-TCPIP {2F07E2E4-90E0-4E27-9DA8-3250482B1212} Event 1058 (UdpSendDatagrams)
    
    Fail-Closed Policy:
    If running without administrative privileges or on unsupported platforms,
    sets is_available() -> False and returns 0.0 bytes/sec. Never falls back to disk I/O.
    """

    SESSION_NAME: str = "NetGuard_Network_ETW"

    def __init__(self) -> None:
        self._available: bool = False
        self._lock = threading.Lock()
        # pid -> deque of (monotonic_timestamp, byte_count)
        self._pid_events: Dict[int, collections.deque] = collections.defaultdict(collections.deque)
        # pid -> set of observed endpoint strings
        self._pid_endpoints: Dict[int, Set[str]] = collections.defaultdict(set)
        self._session_handle = None
        self._trace_handle = None
        self._worker_thread: Optional[threading.Thread] = None
        self._running: bool = False
        self._c_callback = None

        if sys.platform == "win32" and ctypes:
            self._start_tracing()
        else:
            logger.debug("Windows ETW telemetry unavailable: platform is not win32.")

    def is_available(self) -> bool:
        return self._available

    def _start_tracing(self) -> None:
        try:
            # Administrative privilege verification
            try:
                is_admin = (ctypes.windll.shell32.IsUserAnAdmin() != 0)
            except Exception:
                is_admin = False

            if not is_admin:
                logger.debug("Windows ETW telemetry unavailable: process is not elevated. Failing closed.")
                self._available = False
                return

            advapi32 = ctypes.windll.advapi32
            TRACEHANDLE = ctypes.c_uint64

            advapi32.StartTraceW.argtypes = [ctypes.POINTER(TRACEHANDLE), wintypes.LPCWSTR, ctypes.c_void_p]
            advapi32.StartTraceW.restype = wintypes.ULONG
            advapi32.ControlTraceW.argtypes = [TRACEHANDLE, wintypes.LPCWSTR, ctypes.c_void_p, wintypes.ULONG]
            advapi32.ControlTraceW.restype = wintypes.ULONG
            advapi32.CloseTrace.argtypes = [TRACEHANDLE]
            advapi32.CloseTrace.restype = wintypes.ULONG
            advapi32.EnableTraceEx2.argtypes = [
                TRACEHANDLE,
                ctypes.POINTER(GUID),
                wintypes.ULONG,
                ctypes.c_ubyte,
                ctypes.c_uint64,
                ctypes.c_uint64,
                wintypes.ULONG,
                ctypes.c_void_p,
            ]
            advapi32.EnableTraceEx2.restype = wintypes.ULONG
            advapi32.OpenTraceW.argtypes = [ctypes.c_void_p]
            advapi32.OpenTraceW.restype = TRACEHANDLE
            advapi32.ProcessTrace.argtypes = [ctypes.POINTER(TRACEHANDLE), wintypes.ULONG, ctypes.c_void_p, ctypes.c_void_p]
            advapi32.ProcessTrace.restype = wintypes.ULONG

            buf_size = ctypes.sizeof(EVENT_TRACE_PROPERTIES) + 1024
            buf = ctypes.create_string_buffer(buf_size)
            props = ctypes.cast(buf, ctypes.POINTER(EVENT_TRACE_PROPERTIES)).contents
            props.Wnode.BufferSize = buf_size
            props.Wnode.Flags = 0x00020000  # WNODE_FLAG_TRACED_GUID
            props.LogFileMode = 0x00000100  # EVENT_TRACE_REAL_TIME_MODE
            props.LoggerNameOffset = ctypes.sizeof(EVENT_TRACE_PROPERTIES)

            # Clean any stale prior session
            advapi32.ControlTraceW(0, self.SESSION_NAME, ctypes.byref(props), 1)  # EVENT_TRACE_CONTROL_STOP = 1

            sess_handle = TRACEHANDLE()
            res = advapi32.StartTraceW(ctypes.byref(sess_handle), self.SESSION_NAME, ctypes.byref(props))
            if res != 0:
                logger.warning("Windows ETW StartTraceW failed (code %d). Failing closed.", res)
                self._available = False
                return

            self._session_handle = sess_handle

            # Enable Microsoft-Windows-Kernel-Network: {7DD42A49-5329-4832-8DFD-43D979153A88}
            knet_guid = GUID(0x7DD42A49, 0x5329, 0x4832, (ctypes.c_byte * 8)(0x8D, 0xFD, 0x43, 0xD9, 0x79, 0x15, 0x3A, 0x88))
            advapi32.EnableTraceEx2(sess_handle, ctypes.byref(knet_guid), 1, 4, 0, 0, 0, None)

            # Enable Microsoft-Windows-TCPIP: {2F07E2E4-90E0-4E27-9DA8-3250482B1212}
            tcpip_guid = GUID(0x2F07E2E4, 0x90E0, 0x4E27, (ctypes.c_byte * 8)(0x9D, 0xA8, 0x32, 0x50, 0x48, 0x2B, 0x12, 0x12))
            advapi32.EnableTraceEx2(sess_handle, ctypes.byref(tcpip_guid), 1, 4, 0, 0, 0, None)

            self._c_callback = PEVENT_RECORD_CALLBACK(self._on_event_record)
            logfile = EVENT_TRACE_LOGFILEW()
            logfile.LoggerName = self.SESSION_NAME
            logfile.ProcessTraceMode = 0x00000100 | 0x10000000  # REAL_TIME | EVENT_RECORD
            logfile.EventRecordCallback = self._c_callback

            tr_handle = advapi32.OpenTraceW(ctypes.byref(logfile))
            if tr_handle == 0 or tr_handle == 0xFFFFFFFFFFFFFFFF:
                logger.warning("Windows ETW OpenTraceW returned invalid handle. Failing closed.")
                advapi32.ControlTraceW(sess_handle, self.SESSION_NAME, ctypes.byref(props), 1)
                self._available = False
                return

            self._trace_handle = tr_handle
            self._running = True
            self._available = True

            def _worker():
                try:
                    handle_arr = (TRACEHANDLE * 1)(tr_handle)
                    advapi32.ProcessTrace(handle_arr, 1, None, None)
                except Exception as ex:
                    logger.debug("ETW ProcessTrace loop terminated: %s", ex)

            self._worker_thread = threading.Thread(target=_worker, daemon=True, name="NetGuard_ETW_Worker")
            self._worker_thread.start()
            logger.info("Windows ETW real-time network telemetry active.")
        except Exception as e:
            logger.warning("Exception initializing Windows ETW telemetry: %s. Failing closed.", e)
            self._available = False

    def _on_event_record(self, record_ptr: Any) -> None:
        try:
            if not record_ptr:
                return
            record = record_ptr.contents
            pid = int(record.EventHeader.ProcessId)
            if pid <= 4:
                return

            event_id = int(record.EventHeader.EventDescriptor.Id)
            # Event 42: Kernel-Network UdpSend; Event 1058: TCPIP UdpSendDatagrams
            if event_id in (42, 1058) or event_id == 0:
                data_len = int(record.UserDataLength)
                byte_count = max(32, data_len)
                if record.UserData and data_len >= 4:
                    try:
                        val = ctypes.c_uint32.from_address(record.UserData).value
                        if 0 < val <= 65535:
                            byte_count = val
                    except Exception:
                        pass

                now_m = time.monotonic()
                with self._lock:
                    q = self._pid_events[pid]
                    q.append((now_m, byte_count))
        except Exception:
            pass

    def get_outbound_udp_rate(self, pids: List[int], now_t: float) -> Tuple[float, List[str]]:
        if not self._available or not pids:
            return 0.0, []

        cutoff = now_t - 2.0
        total_bytes = 0
        all_endpoints: List[str] = []

        with self._lock:
            for pid in pids:
                q = self._pid_events.get(pid)
                if q:
                    while q and q[0][0] < cutoff:
                        q.popleft()
                    total_bytes += sum(b for _, b in q)
                if pid in self._pid_endpoints:
                    all_endpoints.extend(self._pid_endpoints[pid])

        for pid in pids:
            all_endpoints.extend(self.get_process_udp_endpoints(pid))

        rate = total_bytes / 2.0
        return rate, list(dict.fromkeys(all_endpoints))

    def get_process_udp_endpoints(self, pid: int) -> List[str]:
        endpoints: List[str] = []
        try:
            for conn in psutil.net_connections(kind="udp"):
                if conn.pid == pid:
                    if conn.raddr:
                        endpoints.append(f"{conn.raddr.ip}:{conn.raddr.port}")
                    elif conn.laddr:
                        endpoints.append(f"0.0.0.0:{conn.laddr.port}")
        except Exception:
            pass

        with self._lock:
            if pid in self._pid_endpoints:
                endpoints.extend(self._pid_endpoints[pid])

        return list(dict.fromkeys(endpoints))

    def close(self) -> None:
        self._running = False
        self._available = False
        try:
            if sys.platform == "win32" and ctypes:
                advapi32 = ctypes.windll.advapi32
                if self._trace_handle:
                    advapi32.CloseTrace(self._trace_handle)
                    self._trace_handle = None
                if self._session_handle:
                    buf_size = ctypes.sizeof(EVENT_TRACE_PROPERTIES) + 1024
                    buf = ctypes.create_string_buffer(buf_size)
                    props = ctypes.cast(buf, ctypes.POINTER(EVENT_TRACE_PROPERTIES)).contents
                    props.Wnode.BufferSize = buf_size
                    props.LoggerNameOffset = ctypes.sizeof(EVENT_TRACE_PROPERTIES)
                    advapi32.ControlTraceW(self._session_handle, self.SESSION_NAME, ctypes.byref(props), 1)
                    self._session_handle = None
        except Exception as e:
            logger.debug("ETW teardown notice: %s", e)


class MockNetworkTelemetryProvider(BaseNetworkTelemetryProvider):
    """Mock telemetry provider for deterministic unit testing without Windows privileges."""

    def __init__(self, available: bool = True) -> None:
        self._available: bool = available
        self._pid_rates: Dict[int, float] = {}
        self._pid_endpoints: Dict[int, List[str]] = {}

    def is_available(self) -> bool:
        return self._available

    def set_available(self, available: bool) -> None:
        self._available = available

    def set_pid_rate(self, pid: int, rate_bytes_per_sec: float, endpoints: Optional[List[str]] = None) -> None:
        self._pid_rates[pid] = float(rate_bytes_per_sec)
        if endpoints is not None:
            self._pid_endpoints[pid] = list(endpoints)

    def get_outbound_udp_rate(self, pids: List[int], now_t: float) -> Tuple[float, List[str]]:
        if not self._available:
            return 0.0, []
        total_rate = sum(self._pid_rates.get(pid, 0.0) for pid in pids)
        eps: List[str] = []
        for pid in pids:
            if pid in self._pid_endpoints:
                eps.extend(self._pid_endpoints[pid])
            else:
                eps.extend(self.get_process_udp_endpoints(pid))
        return total_rate, list(dict.fromkeys(eps))

    def get_process_udp_endpoints(self, pid: int) -> List[str]:
        if pid in self._pid_endpoints:
            return list(self._pid_endpoints[pid])
        eps: List[str] = []
        try:
            for conn in psutil.net_connections(kind="udp"):
                if conn.pid == pid:
                    if conn.raddr:
                        eps.append(f"{conn.raddr.ip}:{conn.raddr.port}")
                    elif conn.laddr:
                        eps.append(f"0.0.0.0:{conn.laddr.port}")
        except Exception:
            pass
        return list(dict.fromkeys(eps))


class MeetingDetector(QObject):
    """Detects active meetings using strict dual-condition per-app correlation."""

    state_changed = Signal(object)  # Emits MeetingState

    COMMON_VPN_KEYWORDS = [
        "urban-vpn", "openvpn", "wireguard", "nordvpn", "protonvpn",
        "warp-svc", "warp.exe", "tailscale", "cloudflared", "windscribe",
        "expressvpn", "surfshark", "mullvad", "zerotier"
    ]

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

    def __init__(
        self,
        parent: Optional[QObject] = None,
        telemetry_provider: Optional[BaseNetworkTelemetryProvider] = None,
    ) -> None:
        super().__init__(parent)
        self._current_state = MeetingState()
        self._meeting_start_time: Optional[datetime] = None
        # Test simulation override: app_id_or_exe -> {"consent": bool, "udp_active": bool, "rate": float, "endpoints": list}
        self._simulated_signals: Dict[str, Dict[str, Any]] = {}
        # Structured per-cycle diagnostics
        self._last_diagnostics: List[CandidateEvaluationDiagnostic] = []
        # Telemetry provider: Genuine Windows ETW provider or injected mock
        self.telemetry_provider: BaseNetworkTelemetryProvider = (
            telemetry_provider if telemetry_provider is not None else WindowsETWNetworkTelemetry()
        )

    @property
    def current(self) -> MeetingState:
        return self._current_state

    def get_last_diagnostics(self) -> List[CandidateEvaluationDiagnostic]:
        """Returns structured diagnostic records from the most recent evaluation cycle."""
        return list(self._last_diagnostics)

    @property
    def last_cycle_diagnostics(self) -> List[CandidateEvaluationDiagnostic]:
        """Property alias for get_last_diagnostics()."""
        return list(self._last_diagnostics)

    def classify_process_priority(
        self,
        process_name: str,
        has_meeting_active: bool = False,
    ) -> TrafficPriorityClass:
        """Classify process priority relative to meeting mode."""
        p_clean = process_name.lower()
        if p_clean in PROTECTED_PROCESSES or p_clean.startswith("svchost"):
            return TrafficPriorityClass.PROTECTED
        if has_meeting_active and (self._current_state.is_active or self.current.is_active):
            active_proc = (self._current_state.process_name or self.current.process_name).lower()
            if p_clean == active_proc:
                return TrafficPriorityClass.REALTIME
        if p_clean in ("chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"):
            return TrafficPriorityClass.INTERACTIVE
        if p_clean in ("onedrive.exe", "dropbox.exe", "googledrivefs.exe"):
            return TrafficPriorityClass.BULK
        return TrafficPriorityClass.INTERACTIVE

    def set_simulated_signal(
        self,
        app_id_or_exe: str,
        has_consent: bool,
        has_sustained_udp: bool,
        rate: Optional[float] = None,
        endpoints: Optional[List[str]] = None,
    ) -> None:
        """Inject simulation overrides for deterministic unit testing."""
        default_rate = 50_000.0 if has_sustained_udp else 0.0
        default_endpoints = ["144.195.27.125:8801"] if has_sustained_udp else []
        self._simulated_signals[app_id_or_exe.lower()] = {
            "consent": bool(has_consent),
            "udp_active": bool(has_sustained_udp),
            "rate": float(rate if rate is not None else default_rate),
            "endpoints": list(endpoints if endpoints is not None else default_endpoints),
        }

    def clear_simulated_signals(self) -> None:
        """Clear all test simulation overrides."""
        self._simulated_signals.clear()

    def check_windows_consent_store_detailed(self) -> Dict[str, Dict[str, Any]]:
        """Check Windows CapabilityAccessManager ConsentStore for mic/webcam.
        
        Returns a mapping of normalized identifiers to their active status:
        {
            "zoom.exe": {"cap": "microphone", "is_active": True},
            "MicrosoftTeams_8wekyb3d8bbwe": {"cap": "webcam", "is_active": True},
            ...
        }
        """
        active_map: Dict[str, Dict[str, Any]] = {}
        if sys.platform != "win32":
            return active_map

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
                                                    # LastUsedTimeStop == 0 means actively capturing right now
                                                    if stop == 0:
                                                        app_clean = app_k.replace("/", "\\").split("\\")[-1].split("#")[-1].lower()
                                                        active_map[app_clean] = {"cap": cap, "is_active": True, "raw": app_k}
                                                except OSError:
                                                    pass
                                except OSError:
                                    pass
                            else:
                                # Packaged app family keys (e.g. MicrosoftTeams, Microsoft.SkypeApp)
                                with winreg.OpenKey(root_key, sub_name) as ak:
                                    try:
                                        stop, _ = winreg.QueryValueEx(ak, "LastUsedTimeStop")
                                        if stop == 0:
                                            active_map[sub_name.lower()] = {"cap": cap, "is_active": True, "raw": sub_name}
                                    except OSError:
                                        pass
                except OSError:
                    pass
        except Exception:
            pass

        return active_map

    def check_windows_consent_store(self) -> List[str]:
        """Legacy helper returning active capability strings (e.g. 'microphone:zoom.exe')."""
        detailed = self.check_windows_consent_store_detailed()
        return [f"{info['cap']}:{k}" for k, info in detailed.items()]

    def is_app_active_in_consent(
        self,
        entry: MeetingAppEntry,
        consent_map: Dict[str, Dict[str, Any]],
        specific_exe: Optional[str] = None,
    ) -> bool:
        """Determines whether a registry entry is currently capturing audio/video in ConsentStore."""
        # 1. Check test simulation override if present
        sim = self._simulated_signals.get(entry.id.lower())
        if sim is not None:
            return sim["consent"]
        if specific_exe:
            sim_exe = self._simulated_signals.get(specific_exe.lower())
            if sim_exe is not None:
                return sim_exe["consent"]

        # 2. Check live ConsentStore map
        if entry.is_browser and specific_exe:
            b_clean = specific_exe.lower()
            return any(b_clean in k or k in b_clean for k in consent_map)

        # Check exe names
        for exe in entry.exe_names:
            e_clean = exe.lower()
            if any(e_clean in k or k in e_clean for k in consent_map):
                return True

        # Check packaged app family names
        for pkg in entry.packaged_family_names:
            p_clean = pkg.lower()
            if any(p_clean in k for k in consent_map):
                return True

        return False

    def check_process_sustained_outbound_udp(
        self,
        pids: List[int],
        now_t: float,
        threshold_bytes_per_sec: float = 2500.0,
        udp_sockets_by_pid: Optional[Set[int]] = None,
        sim_override_key: Optional[str] = None,
    ) -> Tuple[bool, float]:
        """Verifies sustained outbound UDP traffic from process PIDs above threshold.
        
        Measurement Source: Real per-process outbound UDP network send measurement
        from telemetry_provider (Windows ETW Kernel-Network / TCPIP UDP send events).
        
        Fail-Closed: If telemetry_provider is unavailable (non-elevated, unsupported OS),
        returns (False, 0.0). NEVER falls back to generic disk I/O.
        """
        if sim_override_key:
            sim = self._simulated_signals.get(sim_override_key.lower())
            if sim is not None:
                rate = float(sim.get("rate", 50_000.0 if sim["udp_active"] else 0.0))
                return bool(sim["udp_active"]), rate

        if not pids:
            return False, 0.0

        if not self.telemetry_provider.is_available():
            # Fail closed when real telemetry is unavailable; never fall back to disk I/O
            return False, 0.0

        rate, _ = self.telemetry_provider.get_outbound_udp_rate(pids, now_t)
        is_sustained = (rate >= threshold_bytes_per_sec)
        return is_sustained, rate

    def detect_in_call_apps(
        self,
        running_procs: Optional[List[Tuple[int, str]]] = None,
        now_t: Optional[float] = None,
        threshold_bytes_per_sec: float = 2500.0,
        udp_sockets_by_pid: Optional[Set[int]] = None,
    ) -> List[Tuple[MeetingAppEntry, str, int]]:
        """Identifies all meeting applications currently in an active call.
        
        Returns a list of (entry, process_name, pid).
        An app is in a call ONLY when BOTH:
        (a) ConsentStore has active mic/webcam session for that app, AND
        (b) Sustained outbound UDP from that app's processes above threshold.
        """
        now = now_t if now_t is not None else time.monotonic()
        consent_map = self.check_windows_consent_store_detailed()

        # If running_procs not passed, discover via psutil
        if running_procs is None:
            running_procs = []
            for p in psutil.process_iter(["pid", "name"]):
                try:
                    pname = p.info["name"] or ""
                    if pname:
                        running_procs.append((p.info["pid"], pname))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        # Group running PIDs by lowercase executable name
        procs_by_name: Dict[str, List[int]] = {}
        for pid, name in running_procs:
            procs_by_name.setdefault(name.lower(), []).append(pid)

        # Legacy check_windows_consent_store mock compatibility
        try:
            legacy = self.check_windows_consent_store()
            if isinstance(legacy, list):
                for item in legacy:
                    if isinstance(item, str) and ":" in item:
                        cap, target = item.split(":", 1)
                        consent_map[target.lower()] = {"cap": cap, "is_active": True}
        except Exception:
            pass

        # Pre-scan UDP sockets across system
        if udp_sockets_by_pid is None:
            udp_pids: Set[int] = set()
            try:
                for conn in psutil.net_connections(kind="udp"):
                    if conn.pid:
                        udp_pids.add(conn.pid)
            except Exception:
                pass
        else:
            udp_pids = set(udp_sockets_by_pid)

        in_call_apps: List[Tuple[MeetingAppEntry, str, int]] = []
        self._last_diagnostics.clear()

        # Build candidates: (entry, proc_name, pids)
        candidates: List[Tuple[MeetingAppEntry, str, List[int]]] = []
        evaluated_exes: Set[str] = set()

        # 1. Cataloged entries
        for entry in MeetingAppRegistry.all_entries():
            if entry.is_browser:
                for b_exe in entry.exe_names:
                    pids = procs_by_name.get(b_exe.lower(), [])
                    has_sim = (b_exe.lower() in self._simulated_signals or entry.id.lower() in self._simulated_signals)
                    if not pids and not has_sim:
                        continue
                    candidates.append((entry, b_exe, pids))
                    evaluated_exes.add(b_exe.lower())
            else:
                matched_pids: List[int] = []
                matched_exe = entry.exe_names[0]
                for exe in entry.exe_names:
                    pids = procs_by_name.get(exe.lower(), [])
                    if pids:
                        matched_pids.extend(pids)
                        matched_exe = exe
                if entry.extra_exes:
                    for extra in entry.extra_exes:
                        extra_pids = procs_by_name.get(extra.lower(), [])
                        if extra_pids:
                            matched_pids.extend(extra_pids)

                has_sim = (entry.id.lower() in self._simulated_signals or matched_exe.lower() in self._simulated_signals)
                if not matched_pids and not has_sim:
                    continue
                candidates.append((entry, matched_exe, matched_pids))
                evaluated_exes.add(matched_exe.lower())
                for exe in entry.exe_names:
                    evaluated_exes.add(exe.lower())

        # 2. Uncataloged applications discovered active in ConsentStore
        for raw_app in consent_map:
            clean_exe = raw_app.lower()
            if clean_exe in evaluated_exes:
                continue
            if clean_exe in PROTECTED_PROCESSES or clean_exe in self.PROTECTED_SYSTEM_EXES or clean_exe in self.BULK_DOWNLOAD_EXES:
                continue
            pids = procs_by_name.get(clean_exe, [])
            has_sim = (clean_exe in self._simulated_signals)
            if not pids and not has_sim:
                continue
            fallback_entry = MeetingAppRegistry.find_or_create_entry(clean_exe)
            candidates.append((fallback_entry, clean_exe, pids))
            evaluated_exes.add(clean_exe)

        # Evaluate each candidate and build CandidateEvaluationDiagnostic
        for entry, proc_name, pids in candidates:
            sim = self._simulated_signals.get(entry.id.lower()) or self._simulated_signals.get(proc_name.lower())

            # A. Consent Check
            if sim is not None:
                has_consent = bool(sim["consent"])
            else:
                has_consent = self.is_app_active_in_consent(entry, consent_map, specific_exe=proc_name)

            # B. Outbound UDP Rate & Endpoints Check
            rate = 0.0
            endpoints: List[str] = []
            telemetry_available = True

            if sim is not None:
                rate = float(sim.get("rate", 50_000.0 if sim["udp_active"] else 0.0))
                endpoints = list(sim.get("endpoints", ["144.195.27.125:8801"] if sim["udp_active"] else []))
                udp_ok = bool(sim["udp_active"])
                has_udp_socket = bool(udp_ok or (pids and any(p in udp_pids for p in pids)))
            else:
                telemetry_available = self.telemetry_provider.is_available()
                has_udp_socket = bool(pids and any(p in udp_pids for p in pids))
                if not telemetry_available:
                    rate = 0.0
                    udp_ok = False
                    if pids:
                        endpoints = self.telemetry_provider.get_process_udp_endpoints(pids[0])
                else:
                    rate, etw_endpoints = self.telemetry_provider.get_outbound_udp_rate(pids, now)
                    socket_endpoints: List[str] = []
                    for p in pids:
                        socket_endpoints.extend(self.telemetry_provider.get_process_udp_endpoints(p))
                    endpoints = list(dict.fromkeys(etw_endpoints + socket_endpoints))
                    udp_ok = (has_udp_socket or bool(endpoints)) and (rate >= threshold_bytes_per_sec)

            # C. Meeting Call Detected?
            is_detected = bool(has_consent and udp_ok)

            # D. Rejection Reason
            rejection_reason = None
            if not is_detected:
                if not has_consent:
                    rejection_reason = "no_microphone_or_camera_consent"
                elif not telemetry_available:
                    rejection_reason = "telemetry_unavailable"
                elif not has_udp_socket and not endpoints:
                    rejection_reason = "no_udp_socket"
                elif not udp_ok or rate < threshold_bytes_per_sec:
                    rejection_reason = f"insufficient_udp_send_rate: {rate:.1f} < {threshold_bytes_per_sec:.1f} B/s"

            # E. Confidence Calculation
            if is_detected:
                conf = 0.85
                if entry.media_profile and entry.media_profile.has_known_ports:
                    port_matched = False
                    for ep in endpoints:
                        try:
                            ep_port = int(ep.split(":")[-1])
                            if (entry.media_profile.media_port_start and entry.media_profile.media_port_end
                                and entry.media_profile.media_port_start <= ep_port <= entry.media_profile.media_port_end):
                                port_matched = True
                                break
                        except Exception:
                            pass
                    if port_matched:
                        conf += 0.10
                if rate >= threshold_bytes_per_sec * 2.0:
                    conf += 0.05
                confidence = min(1.0, round(conf, 2))
            else:
                if has_consent:
                    confidence = 0.30
                elif udp_ok:
                    confidence = 0.20
                else:
                    confidence = 0.0

            prim_pid = pids[0] if pids else 1000
            diag = CandidateEvaluationDiagnostic(
                pid=prim_pid,
                process_name=proc_name,
                app_id=entry.id,
                endpoints=endpoints,
                udp_bytes_per_sec=rate,
                consent_active=has_consent,
                confidence=confidence,
                is_detected=is_detected,
                rejection_reason=rejection_reason,
            )
            self._last_diagnostics.append(diag)

            if is_detected:
                in_call_apps.append((entry, proc_name, prim_pid))

        # Synchronize current state metrics with winning detection
        if in_call_apps:
            winning_entry, winning_proc, winning_pid = in_call_apps[0]
            winning_diag = next((d for d in self._last_diagnostics if d.pid == winning_pid and d.app_id == winning_entry.id), None)
            if winning_diag:
                self._current_state.udp_send_bytes_per_sec = winning_diag.udp_bytes_per_sec
                self._current_state.endpoints = list(winning_diag.endpoints)
                self._current_state.confidence = winning_diag.confidence
        else:
            self._current_state.udp_send_bytes_per_sec = 0.0
            self._current_state.endpoints = []
            self._current_state.confidence = 0.0

        return in_call_apps

    def detect_meeting(
        self,
        running_procs: Optional[List[Tuple[int, str]]] = None,
        now_t: Optional[float] = None,
        threshold_bytes_per_sec: float = 2500.0,
        udp_sockets_by_pid: Optional[Set[int]] = None,
    ) -> MeetingState:
        """Correlate multi-signals and produce MeetingState."""
        in_call = self.detect_in_call_apps(
            running_procs=running_procs,
            now_t=now_t,
            threshold_bytes_per_sec=threshold_bytes_per_sec,
            udp_sockets_by_pid=udp_sockets_by_pid,
        )
        is_active = len(in_call) > 0
        signals: List[str] = []
        active_app_name = ""
        process_name = ""
        pid = 0
        app_type = "app"
        udp_rate = 0.0
        endpoints: List[str] = []
        confidence = 0.0

        if is_active:
            entry, active_exe, prim_pid = in_call[0]
            active_app_name = entry.display_name
            process_name = active_exe
            pid = prim_pid
            app_type = "browser" if entry.is_browser else "app"
            signals.append(f"consent:{process_name}")
            signals.append(f"udp_sustained:{process_name}")
            signals.append(f"app_id:{entry.id}")

            winning_diag = next((d for d in self._last_diagnostics if d.pid == prim_pid and d.app_id == entry.id), None)
            if winning_diag:
                udp_rate = winning_diag.udp_bytes_per_sec
                endpoints = list(winning_diag.endpoints)
                confidence = winning_diag.confidence

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
            udp_send_bytes_per_sec=udp_rate,
            endpoints=endpoints,
            confidence=confidence,
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
    """Honest video meeting quality advisor calculation."""
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


def detect_bufferbloat(
    idle_latency_ms: float,
    load_latency_ms: float,
    upload_active: bool = True,
    threshold_spike_ms: float = 50.0,
) -> Dict[str, Any]:
    """Detect bufferbloat (latency spike under upload load) and return honest advisory."""
    spike = max(0.0, load_latency_ms - idle_latency_ms) if (load_latency_ms > 0 and idle_latency_ms > 0) else 0.0
    detected = upload_active and (spike >= threshold_spike_ms or (load_latency_ms > 120.0 and spike >= 35.0))
    return {
        "detected": detected,
        "spike_ms": round(spike, 1),
        "headline": "تنبيه اختناق الراوتر (Bufferbloat)" if detected else "استقرار الطوابير سليم",
        "advisory": (
            "تم رصد ارتفاع كبير في زمن الاستجابة أثناء الرفع (Bufferbloat). "
            "لا يمكن للكمبيوتر إصلاح حركة البيانات الواردة أو المشتركة بمفرده — "
            "يُنصح بتفعيل إدارة الطوابير الذكية (SQM / Smart Queue Management مثل CAKE أو FQ-CoDel) في إعدادات الراوتر."
        ) if detected else "زمن الاستجابة مستقر أثناء عمليات الرفع.",
    }


def detect_wifi_weak_link(
    is_wifi: bool,
    signal_pct: Optional[float] = None,
    jitter_ms: float = 0.0,
    packet_loss_pct: float = 0.0,
) -> Dict[str, Any]:
    """Analyze if Wi-Fi / WMM medium contention is the primary quality bottleneck."""
    if not is_wifi:
        return {
            "is_wifi": False,
            "is_weak_link": False,
            "headline": "اتصال سلكي مستقر (Ethernet)",
            "advisory": "الاتصال السلكي يوفر أقل تذبذب ممكن وحصانة كاملة من تداخل الترددات اللاسلكية.",
        }

    reasons = []
    if signal_pct is not None and signal_pct < 60.0:
        reasons.append(f"ضعف إشارة الواي فاي ({signal_pct:.0f}%)")
    if jitter_ms > 20.0:
        reasons.append(f"تذبذب وصول الحزم اللاسلكية ({jitter_ms:.1f} ms)")
    if packet_loss_pct > 1.0:
        reasons.append(f"فقدان الحزم ({packet_loss_pct:.1f}%)")

    is_weak = len(reasons) > 0
    return {
        "is_wifi": True,
        "is_weak_link": is_weak,
        "signal_pct": signal_pct,
        "headline": "شبكة Wi-Fi تشهد تذبذباً" if is_weak else "إشارة Wi-Fi مستقرة",
        "advisory": (
            f"تنبيه: { ' و '.join(reasons) }. قنوات Wi-Fi المشتركة وتنافس WMM قد تؤدي لتقطيع الفيديو — "
            "يُنصح بالاقتراب من الراوتر أو التوصيل بكابل LAN مباشر لأفضل تجربة مكالمات."
        ) if is_weak else "جودة الإشارة اللاسلكية كافية لمكالمات الفيديو المستقرة.",
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
    """Generate honest post-meeting health report without blaming local network falsely."""
    mins = int(duration_seconds // 60)
    dur_str = f"{mins} دقيقة" if mins > 0 else f"{int(duration_seconds)} ثانية"

    if packet_loss_pct < 0.5 and avg_jitter_ms < 15.0:
        verdict = "مكالمة ممتازة — لم تحدث أي انقطاعات صوتية أو مرئية."
        verdict_type = "ok"
    elif local_gateway_latency_ms < 10.0:
        verdict = f"حدث تقطيع طفيف — المشكلة من خوادم {app_name} أو الطرف الآخر، شبكتك المحلية كانت سليمة تماماً (استجابة الراوتر {local_gateway_latency_ms:.1f} ms)."
        verdict_type = "external_issue"
    else:
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


class MeetingShield(QObject):
    """Proactive early warning shield & 4-case fault attribution for active meetings."""

    early_warning_triggered = Signal(dict)

    COOLDOWN_SECONDS = 60.0
    COMMON_VPN_KEYWORDS = [
        "urban-vpn", "openvpn", "wireguard", "nordvpn", "protonvpn",
        "warp-svc", "warp.exe", "tailscale", "cloudflared", "windscribe",
        "expressvpn", "surfshark", "mullvad", "zerotier"
    ]

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._last_alert_time: float = 0.0
        self._last_alert_case: Optional[str] = None
        self._last_wan_latency: float = 0.0

    def reset_cooldown(self) -> None:
        self._last_alert_time = 0.0
        self._last_alert_case = None

    def evaluate_telemetry(
        self,
        is_meeting_active: bool,
        meeting_app_name: str = "",
        meeting_process_name: str = "",
        gateway_latency_ms: float = 0.0,
        gateway_loss_ratio: float = 0.0,
        wan_latency_ms: float = 0.0,
        wan_loss_ratio: float = 0.0,
        jitter_ms: float = 0.0,
        active_processes: Optional[List[Any]] = None,
        active_vpn_name: Optional[str] = None,
        force_ignore_cooldown: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Evaluates early instability BEFORE drop and attributes fault across 4 cases."""
        if not is_meeting_active:
            self._last_wan_latency = wan_latency_ms
            return None

        jump_ms = (wan_latency_ms - self._last_wan_latency) if self._last_wan_latency > 0 else 0.0
        self._last_wan_latency = wan_latency_ms

        has_latency_spike = wan_latency_ms > 120.0 or jump_ms > 60.0
        has_jitter_spike = jitter_ms > 25.0
        has_packet_loss = wan_loss_ratio >= 0.02 or gateway_loss_ratio > 0.0

        vpn_detected = active_vpn_name
        if not vpn_detected and active_processes:
            for p in active_processes:
                pname = getattr(p, "name", "").lower()
                for v_kw in self.COMMON_VPN_KEYWORDS:
                    if v_kw in pname:
                        vpn_detected = getattr(p, "name", pname)
                        break
                if vpn_detected:
                    break

        hog_app = None
        hog_bandwidth = 0.0
        if active_processes:
            meeting_lower = meeting_process_name.lower()
            for p in active_processes:
                pname = getattr(p, "name", "")
                pname_lower = pname.lower()
                if pname_lower == meeting_lower or getattr(p, "is_protected_system_process", False):
                    continue
                est_mb = float(getattr(p, "estimated_bandwidth_mbps", 0.0) or 0.0)
                if est_mb >= 5.0 and est_mb > hog_bandwidth:
                    hog_app = pname
                    hog_bandwidth = est_mb

        alert_case = None
        message = ""
        culprit = ""

        if vpn_detected:
            alert_case = "A"
            culprit = vpn_detected
            message = f"تنبيه مبكر: يوجد برنامج VPN نشط على جهازك ({vpn_detected}) وقد يسبب بطء أو فصل المكالمة — يُنصح بإيقافه أثناء المكالمة."
        elif hog_app and (has_latency_spike or has_jitter_spike or has_packet_loss or hog_bandwidth >= 8.0):
            alert_case = "B"
            culprit = hog_app
            message = f"تنبيه قبل الانقطاع: برنامج ({hog_app}) يستهلك سرعة الإنترنت حالياً مما قد يسبب تقطع المكالمة."
        elif (gateway_loss_ratio > 0.0 or gateway_latency_ms > 20.0) and (has_latency_spike or has_jitter_spike or has_packet_loss):
            alert_case = "C"
            culprit = "الراوتر / شبكة الواي فاي المحلية"
            message = "تنبيه مبكر: عدم استقرار في شبكة الواي فاي أو الراوتر — يُنصح بالاقتراب من الراوتر أو التوصيل بكابل LAN."
        elif (gateway_latency_ms <= 15.0 and gateway_loss_ratio == 0.0) and (has_latency_spike or has_jitter_spike or has_packet_loss):
            alert_case = "D"
            culprit = "مزود الخدمة (ISP)"
            message = "تنبيه مبكر: خط الإنترنت المحلي لديك (مزود الخدمة) يعاني من تذبذب/فقدان حزم حالياً وقد يتأثر الاجتماع — التطبيق والنظام يعملان بشكل سليم والمشكلة من اتصال الإنترنت لديك."

        if not alert_case:
            return None

        now_ts = time.time()
        if not force_ignore_cooldown:
            if (now_ts - self._last_alert_time) < self.COOLDOWN_SECONDS and self._last_alert_case == alert_case:
                return None

        self._last_alert_time = now_ts
        self._last_alert_case = alert_case

        alert_dict = {
            "case": alert_case,
            "message": message,
            "culprit": culprit,
            "timestamp": now_ts,
            "meeting_app": meeting_app_name,
        }
        self.early_warning_triggered.emit(alert_dict)
        return alert_dict
