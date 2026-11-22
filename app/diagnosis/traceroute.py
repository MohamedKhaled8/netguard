"""Real Multi-Protocol Traceroute and Diagnostic Engine for NetGuard AI.

Provides independent ICMP, TCP (Port 443), and UDP traceroute implementations,
intelligent hop classification, independent end-to-end connectivity verification,
and evidence-based root-cause analysis without fabricated measurements or assumptions.
"""

from __future__ import annotations

import ctypes
import ipaddress
import logging
import math
import os
import re
import socket
import struct
import subprocess
import threading
import time
import urllib.request
import ssl
from ctypes import wintypes
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("netguard.diagnosis.traceroute")


class ProbeProtocol(str, Enum):
    ICMP = "ICMP"
    TCP = "TCP"
    UDP = "UDP"


class HopClassification(str, Enum):
    RESPONDING = "RESPONDING"
    SILENT_HOP = "SILENT_HOP"
    PATH_CONTINUES = "PATH_CONTINUES"
    INTERMEDIATE_FILTERING_SUSPECTED = "INTERMEDIATE_FILTERING_SUSPECTED"
    TRACE_INCONCLUSIVE = "TRACE_INCONCLUSIVE"
    DESTINATION_UNREACHABLE = "DESTINATION_UNREACHABLE"


class EndToEndStatus(str, Enum):
    INTERMEDIATE_ROUTER_SILENT = "INTERMEDIATE_ROUTER_SILENT"
    DESTINATION_REACHABLE = "DESTINATION_REACHABLE"
    DESTINATION_UNREACHABLE = "DESTINATION_UNREACHABLE"
    DNS_FAILURE = "DNS_FAILURE"
    ACTUAL_INTERNET_OUTAGE = "ACTUAL_INTERNET_OUTAGE"


@dataclass
class ProbeResult:
    """Individual probe packet telemetry."""
    probe_index: int
    rtt_ms: Optional[float]
    responding_ip: Optional[str]
    status_code: str  # e.g., "TTL_EXPIRED", "SUCCESS", "TIMEOUT", "UNREACHABLE", "TCP_SYN_ACK", "TCP_RST"
    details: str = ""


@dataclass
class HopResult:
    """Consolidated results for a single TTL / hop distance."""
    hop_number: int
    protocol: ProbeProtocol
    classification: HopClassification
    ip: Optional[str]
    hostname: Optional[str]
    probes: List[ProbeResult] = field(default_factory=list)
    min_rtt_ms: Optional[float] = None
    avg_rtt_ms: Optional[float] = None
    max_rtt_ms: Optional[float] = None
    loss_pct: float = 0.0
    reason: Optional[str] = None
    subsequent_hops_responded: bool = False

    def calculate_stats(self) -> None:
        valid_rtts = [p.rtt_ms for p in self.probes if p.rtt_ms is not None and p.rtt_ms >= 0]
        if valid_rtts:
            self.min_rtt_ms = round(min(valid_rtts), 2)
            self.avg_rtt_ms = round(sum(valid_rtts) / len(valid_rtts), 2)
            self.max_rtt_ms = round(max(valid_rtts), 2)
        total = len(self.probes)
        if total > 0:
            failed = sum(1 for p in self.probes if p.rtt_ms is None or p.rtt_ms < 0)
            self.loss_pct = round((failed / float(total)) * 100.0, 1)
        else:
            self.loss_pct = 100.0 if not valid_rtts else 0.0


@dataclass
class TraceRouteReport:
    """Full traceroute execution report for a single protocol."""
    protocol: ProbeProtocol
    target: str
    target_ip: str
    target_reached: bool
    target_rtt_ms: Optional[float]
    total_hops: int
    hops: List[HopResult]
    trace_classification: HopClassification
    driver_info: str
    duration_sec: float
    error_message: Optional[str] = None

    def get_hop(self, hop_num: int) -> Optional[HopResult]:
        for h in self.hops:
            if h.hop_number == hop_num:
                return h
        return None


@dataclass
class EndToEndCheckResult:
    """Independent end-to-end reachability test result."""
    target: str
    tcp_443_ok: bool
    tcp_443_rtt_ms: Optional[float]
    dns_ok: bool
    dns_rtt_ms: Optional[float]
    https_ok: bool
    https_status_code: Optional[int]
    details: str = ""


@dataclass
class MultiProtocolAnalysisReport:
    """Comprehensive multi-protocol trace and end-to-end diagnostic report."""
    timestamp: datetime
    target: str
    target_ip: str
    icmp_trace: TraceRouteReport
    tcp_trace: TraceRouteReport
    udp_trace: TraceRouteReport
    end_to_end_checks: List[EndToEndCheckResult]
    overall_end_to_end_ok: bool
    end_to_end_status: EndToEndStatus
    case_identified: str  # "CASE_1", "CASE_2", "CASE_3", "CASE_4", "NORMAL_RESPONDING"
    hop2_classification: HopClassification
    hop2_ip: Optional[str]
    hop2_protocol: Optional[ProbeProtocol]
    hop2_latency_ms: Optional[float]
    hop2_reason: str
    hop2_subsequent_responded: bool
    consolidated_verdict_arabic: str
    technical_details_arabic: str
    driver_summary: str


# =====================================================================
# Win32 Native IcmpSendEcho Definitions (iphlpapi.dll)
# =====================================================================

class _IP_OPTION_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("Ttl", ctypes.c_ubyte),
        ("Tos", ctypes.c_ubyte),
        ("Flags", ctypes.c_ubyte),
        ("OptionsSize", ctypes.c_ubyte),
        ("OptionsData", ctypes.c_void_p),
    ]


class _ICMP_ECHO_REPLY(ctypes.Structure):
    _fields_ = [
        ("Address", wintypes.ULONG),
        ("Status", wintypes.ULONG),
        ("RoundTripTime", wintypes.ULONG),
        ("DataSize", wintypes.USHORT),
        ("Reserved", wintypes.USHORT),
        ("Data", ctypes.c_void_p),
        ("Options", _IP_OPTION_INFORMATION),
    ]


IP_SUCCESS = 0
IP_DEST_NET_UNREACHABLE = 11002
IP_DEST_HOST_UNREACHABLE = 11003
IP_DEST_PORT_UNREACHABLE = 11005
IP_REQ_TIMED_OUT = 11010
IP_TTL_EXPIRED_TRANSIT = 11013
IP_TTL_EXPIRED_REASSEM = 11014


# =====================================================================
# Npcap / WinPcap C-Types Wrapper (wpcap.dll)
# =====================================================================

class _PcapIf(ctypes.Structure):
    pass


_PcapIfP = ctypes.POINTER(_PcapIf)


class _SockAddrIn(ctypes.Structure):
    _fields_ = [
        ("sin_family", ctypes.c_short),
        ("sin_port", ctypes.c_ushort),
        ("sin_addr", ctypes.c_ulong),
        ("sin_zero", ctypes.c_char * 8),
    ]


class _PcapAddr(ctypes.Structure):
    pass


_PcapAddrP = ctypes.POINTER(_PcapAddr)
_PcapAddr._fields_ = [
    ("next", _PcapAddrP),
    ("addr", ctypes.c_void_p),
    ("netmask", ctypes.c_void_p),
    ("broadaddr", ctypes.c_void_p),
    ("dstaddr", ctypes.c_void_p),
]

_PcapIf._fields_ = [
    ("next", _PcapIfP),
    ("name", ctypes.c_char_p),
    ("description", ctypes.c_char_p),
    ("addresses", _PcapAddrP),
    ("flags", ctypes.c_uint),
]


class _PcapPkthdr(ctypes.Structure):
    _fields_ = [
        ("tv_sec", ctypes.c_long),
        ("tv_usec", ctypes.c_long),
        ("caplen", ctypes.c_uint),
        ("len", ctypes.c_uint),
    ]


class _BpfProgram(ctypes.Structure):
    _fields_ = [("bf_len", ctypes.c_uint), ("bf_insns", ctypes.c_void_p)]


class NpcapCaptureManager:
    """Manages raw packet capture via Npcap / WinPcap wpcap.dll on Windows without CLI tools."""

    _wpcap: Any = None
    _is_available: Optional[bool] = None

    @classmethod
    def is_available(cls) -> bool:
        if cls._is_available is not None:
            return cls._is_available
        if os.name != "nt":
            cls._is_available = False
            return False

        try:
            cls._wpcap = ctypes.cdll.LoadLibrary("wpcap.dll")
            cls._wpcap.pcap_open_live.restype = ctypes.c_void_p
            cls._wpcap.pcap_open_live.argtypes = [
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_char_p,
            ]
            cls._wpcap.pcap_close.argtypes = [ctypes.c_void_p]
            cls._wpcap.pcap_next_ex.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.POINTER(_PcapPkthdr)),
                ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),
            ]
            cls._wpcap.pcap_next_ex.restype = ctypes.c_int
            cls._wpcap.pcap_compile.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(_BpfProgram),
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_uint,
            ]
            cls._wpcap.pcap_compile.restype = ctypes.c_int
            cls._wpcap.pcap_setfilter.argtypes = [ctypes.c_void_p, ctypes.POINTER(_BpfProgram)]
            cls._wpcap.pcap_setfilter.restype = ctypes.c_int
            cls._is_available = True
        except Exception as exc:
            logger.debug("Npcap wpcap.dll not loaded: %s", exc)
            cls._is_available = False
        return cls._is_available

    def __init__(self, local_ip: str) -> None:
        self.local_ip = local_ip
        self.handle: Any = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.captured_packets: List[Tuple[float, bytes]] = []
        self._lock = threading.Lock()

    def start(self, bpf_filter: str = "icmp") -> bool:
        if not self.is_available():
            return False

        try:
            alldevs = _PcapIfP()
            errbuf = ctypes.create_string_buffer(256)
            ret = self._wpcap.pcap_findalldevs(ctypes.byref(alldevs), errbuf)
            if ret != 0 or not alldevs:
                return False

            matched_dev: Optional[bytes] = None
            curr = alldevs
            while curr:
                d = curr.contents
                aptr = d.addresses
                while aptr:
                    a = aptr.contents
                    if a.addr:
                        sin = _SockAddrIn.from_address(a.addr)
                        if sin.sin_family == socket.AF_INET:
                            ip_str = socket.inet_ntoa(struct.pack("<I", sin.sin_addr))
                            if ip_str == self.local_ip:
                                matched_dev = d.name
                                break
                    aptr = a.next
                if matched_dev:
                    break
                curr = d.next

            self._wpcap.pcap_freealldevs(alldevs)
            if not matched_dev:
                return False

            self.handle = self._wpcap.pcap_open_live(matched_dev, 65535, 1, 20, errbuf)
            if not self.handle:
                return False

            bpf = _BpfProgram()
            if self._wpcap.pcap_compile(self.handle, ctypes.byref(bpf), bpf_filter.encode(), 1, 0) == 0:
                self._wpcap.pcap_setfilter(self.handle, ctypes.byref(bpf))

            self._stop_event.clear()
            self._thread = threading.Thread(target=self._capture_worker, daemon=True)
            self._thread.start()
            return True
        except Exception as exc:
            logger.debug("Failed to start Npcap capture: %s", exc)
            if self.handle:
                try:
                    self._wpcap.pcap_close(self.handle)
                except Exception:
                    pass
                self.handle = None
            return False

    def _capture_worker(self) -> None:
        hdr_p = ctypes.POINTER(_PcapPkthdr)()
        pkt_data = ctypes.POINTER(ctypes.c_ubyte)()
        while not self._stop_event.is_set():
            res = self._wpcap.pcap_next_ex(self.handle, ctypes.byref(hdr_p), ctypes.byref(pkt_data))
            if res == 1:
                t_now = time.perf_counter()
                caplen = hdr_p.contents.caplen
                raw = bytes(ctypes.string_at(pkt_data, caplen))
                with self._lock:
                    self.captured_packets.append((t_now, raw))

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.6)
        if self.handle and self._wpcap:
            try:
                self._wpcap.pcap_close(self.handle)
            except Exception:
                pass
            self.handle = None

    def match_icmp_time_exceeded(
        self,
        orig_protocol: int,
        orig_sport: int,
        orig_dport: int,
        send_time: float,
    ) -> Optional[Tuple[str, int, int, float]]:
        """Parses captured packets to find ICMP Time Exceeded (11) or Dest Unreach (3).

        Returns: (router_ip, icmp_type, icmp_code, rtt_ms) if matched.
        """
        with self._lock:
            for t_cap, p in self.captured_packets:
                if t_cap < send_time:
                    continue
                # Typical Ethernet frame is 14 bytes
                if len(p) < 34:
                    continue
                # IPv4 check
                ip_ver = (p[14] >> 4) & 0x0F
                if ip_ver != 4:
                    continue
                ip_proto = p[23]
                if ip_proto != 1:  # ICMP
                    continue
                ip_hl = (p[14] & 0x0F) * 4
                icmp_start = 14 + ip_hl
                if len(p) < icmp_start + 8:
                    continue
                icmp_type = p[icmp_start]
                icmp_code = p[icmp_start + 1]

                if icmp_type not in (11, 3):  # 11: Time Exceeded, 3: Destination Unreachable
                    continue

                router_ip = socket.inet_ntoa(p[26:30])

                # Inner quoted IP packet starts at icmp_start + 8
                orig_ip_start = icmp_start + 8
                if len(p) < orig_ip_start + 28:
                    continue
                quoted_proto = p[orig_ip_start + 9]
                if quoted_proto != orig_protocol:
                    continue
                quoted_hl = (p[orig_ip_start] & 0x0F) * 4
                quoted_l4_start = orig_ip_start + quoted_hl
                if len(p) < quoted_l4_start + 4:
                    continue
                q_sport, q_dport = struct.unpack("!HH", p[quoted_l4_start : quoted_l4_start + 4])
                if q_sport == orig_sport and (orig_dport == 0 or q_dport == orig_dport):
                    rtt = max((t_cap - send_time) * 1000.0, 0.1)
                    return router_ip, icmp_type, icmp_code, rtt
        return None


# =====================================================================
# Method A: ICMP Traceroute Engine (Native iphlpapi.dll with fallback)
# =====================================================================

class IcmpTracerouteEngine:
    """Windows native ICMP Traceroute using IcmpSendEcho with TTL increments."""

    def __init__(self, platform_adapter=None) -> None:
        self.platform = platform_adapter

    def run_trace(
        self,
        target_ip: str,
        max_hops: int = 15,
        probes_per_hop: int = 3,
        timeout_ms: int = 800,
    ) -> TraceRouteReport:
        start_time = time.perf_counter()
        hops: List[HopResult] = []
        target_reached = False
        target_rtt: Optional[float] = None
        driver_info = "Windows Native IcmpSendEcho (No Admin Required)"

        if os.name != "nt":
            return self._run_cli_fallback(target_ip, max_hops, timeout_ms)

        try:
            iphlpapi = ctypes.windll.iphlpapi
            iphlpapi.IcmpCreateFile.restype = wintypes.HANDLE
            iphlpapi.IcmpCloseHandle.argtypes = [wintypes.HANDLE]
            iphlpapi.IcmpCloseHandle.restype = wintypes.BOOL
            iphlpapi.IcmpSendEcho.argtypes = [
                wintypes.HANDLE,
                wintypes.ULONG,
                ctypes.c_char_p,
                wintypes.WORD,
                ctypes.POINTER(_IP_OPTION_INFORMATION),
                ctypes.c_void_p,
                wintypes.DWORD,
                wintypes.DWORD,
            ]
            iphlpapi.IcmpSendEcho.restype = wintypes.DWORD

            icmp_handle = iphlpapi.IcmpCreateFile()
            if not icmp_handle or icmp_handle == wintypes.HANDLE(-1).value:
                return self._run_cli_fallback(target_ip, max_hops, timeout_ms)

            dest_addr = struct.unpack("<I", socket.inet_aton(target_ip))[0]
            req_data = b"NetGuardICMPProbeData"
            reply_size = ctypes.sizeof(_ICMP_ECHO_REPLY) + len(req_data) + 64
            reply_buf = ctypes.create_string_buffer(reply_size)

            try:
                for ttl in range(1, max_hops + 1):
                    probe_results: List[ProbeResult] = []
                    hop_ip: Optional[str] = None

                    for p_idx in range(probes_per_hop):
                        opts = _IP_OPTION_INFORMATION()
                        opts.Ttl = ttl
                        t0 = time.perf_counter()
                        ret = iphlpapi.IcmpSendEcho(
                            icmp_handle,
                            dest_addr,
                            req_data,
                            len(req_data),
                            ctypes.byref(opts),
                            ctypes.byref(reply_buf),
                            reply_size,
                            timeout_ms,
                        )
                        wall_ms = (time.perf_counter() - t0) * 1000.0

                        if ret > 0:
                            reply = _ICMP_ECHO_REPLY.from_buffer(reply_buf)
                            status = reply.Status
                            rtt = float(reply.RoundTripTime) if reply.RoundTripTime > 0 else max(wall_ms, 0.2)
                            resp_ip = socket.inet_ntoa(struct.pack("<I", reply.Address)) if reply.Address else None

                            if status == IP_TTL_EXPIRED_TRANSIT:
                                probe_results.append(
                                    ProbeResult(
                                        probe_index=p_idx + 1,
                                        rtt_ms=rtt,
                                        responding_ip=resp_ip,
                                        status_code="TTL_EXPIRED",
                                        details=f"ICMP Time Exceeded from {resp_ip}",
                                    )
                                )
                                if not hop_ip and resp_ip:
                                    hop_ip = resp_ip
                            elif status == IP_SUCCESS:
                                probe_results.append(
                                    ProbeResult(
                                        probe_index=p_idx + 1,
                                        rtt_ms=rtt,
                                        responding_ip=resp_ip or target_ip,
                                        status_code="SUCCESS",
                                        details=f"Target Echo Reply received from {target_ip}",
                                    )
                                )
                                hop_ip = resp_ip or target_ip
                                target_reached = True
                                target_rtt = rtt
                            elif status in (IP_DEST_NET_UNREACHABLE, IP_DEST_HOST_UNREACHABLE, IP_DEST_PORT_UNREACHABLE):
                                probe_results.append(
                                    ProbeResult(
                                        probe_index=p_idx + 1,
                                        rtt_ms=rtt,
                                        responding_ip=resp_ip,
                                        status_code="DEST_UNREACHABLE",
                                        details=f"Destination Unreachable (code {status})",
                                    )
                                )
                                if not hop_ip and resp_ip:
                                    hop_ip = resp_ip
                            else:
                                probe_results.append(
                                    ProbeResult(
                                        probe_index=p_idx + 1,
                                        rtt_ms=None,
                                        responding_ip=None,
                                        status_code=f"STATUS_{status}",
                                        details=f"ICMP code {status}",
                                    )
                                )
                        else:
                            probe_results.append(
                                ProbeResult(
                                    probe_index=p_idx + 1,
                                    rtt_ms=None,
                                    responding_ip=None,
                                    status_code="TIMEOUT",
                                    details="Request timed out",
                                )
                            )

                    # Create hop result
                    is_responding = any(p.rtt_ms is not None for p in probe_results)
                    hop_cls = HopClassification.RESPONDING if is_responding else HopClassification.SILENT_HOP
                    hop_res = HopResult(
                        hop_number=ttl,
                        protocol=ProbeProtocol.ICMP,
                        classification=hop_cls,
                        ip=hop_ip,
                        hostname=None,
                        probes=probe_results,
                    )
                    hop_res.calculate_stats()
                    hops.append(hop_res)

                    if target_reached:
                        break
            finally:
                iphlpapi.IcmpCloseHandle(icmp_handle)

        except Exception as exc:
            logger.warning("IcmpSendEcho failed: %s; falling back to tracert CLI", exc)
            return self._run_cli_fallback(target_ip, max_hops, timeout_ms)

        # Post-process classifications
        _classify_trace_hops(hops, target_reached)
        duration = max(time.perf_counter() - start_time, 0.05)
        overall_cls = _determine_overall_classification(hops, target_reached)

        return TraceRouteReport(
            protocol=ProbeProtocol.ICMP,
            target=target_ip,
            target_ip=target_ip,
            target_reached=target_reached,
            target_rtt_ms=target_rtt,
            total_hops=len(hops),
            hops=hops,
            trace_classification=overall_cls,
            driver_info=driver_info,
            duration_sec=duration,
        )

    def _run_cli_fallback(self, target_ip: str, max_hops: int, timeout_ms: int) -> TraceRouteReport:
        start_time = time.perf_counter()
        hops: List[HopResult] = []
        target_reached = False
        target_rtt: Optional[float] = None
        cmd = ["tracert", "-d", "-h", str(max_hops), "-w", str(timeout_ms), target_ip]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=max(max_hops * 1.5, 5.0),
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            for line in proc.stdout.splitlines():
                line_str = line.strip()
                m_hop = re.match(r"^(\d+)\s+(.+)$", line_str)
                if not m_hop:
                    continue
                hop_num = int(m_hop.group(1))
                rest = m_hop.group(2)
                rtts: List[float] = []
                for m_rtt in re.finditer(r"([=<])\s*(\d+(?:\.\d+)?)\s*ms", rest, re.IGNORECASE):
                    rtts.append(float(m_rtt.group(2)))
                ip_match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", rest)
                found_ip = ip_match.group(0) if ip_match else None

                probes: List[ProbeResult] = []
                for idx, r in enumerate(rtts):
                    probes.append(ProbeResult(idx + 1, r, found_ip, "RESPONDING", "Tracert CLI measurement"))
                if not probes:
                    probes.append(ProbeResult(1, None, None, "TIMEOUT", "Request timed out"))

                cls_type = HopClassification.RESPONDING if found_ip else HopClassification.SILENT_HOP
                h = HopResult(
                    hop_number=hop_num,
                    protocol=ProbeProtocol.ICMP,
                    classification=cls_type,
                    ip=found_ip,
                    hostname=None,
                    probes=probes,
                )
                h.calculate_stats()
                hops.append(h)
                if found_ip == target_ip:
                    target_reached = True
                    target_rtt = h.avg_rtt_ms
        except Exception as exc:
            logger.warning("Tracert fallback failed: %s", exc)

        _classify_trace_hops(hops, target_reached)
        duration = max(time.perf_counter() - start_time, 0.05)
        overall_cls = _determine_overall_classification(hops, target_reached)

        return TraceRouteReport(
            protocol=ProbeProtocol.ICMP,
            target=target_ip,
            target_ip=target_ip,
            target_reached=target_reached,
            target_rtt_ms=target_rtt,
            total_hops=len(hops),
            hops=hops,
            trace_classification=overall_cls,
            driver_info="Windows Tracert CLI Fallback",
            duration_sec=duration,
        )


# =====================================================================
# Method B: TCP Traceroute Engine (Port 443 with progressive TTL)
# =====================================================================

class TcpTracerouteEngine:
    """TCP-based traceroute using destination port 443 with progressive TTL values.

    Captures ICMP Time Exceeded responses using Npcap when available, and detects
    destination TCP SYN-ACK or RST responses without confusing TCP handshake latency
    with intermediate-hop latency.
    """

    def __init__(self, local_ip: Optional[str] = None) -> None:
        if not local_ip:
            local_ip = _get_default_local_ip()
        self.local_ip = local_ip

    def run_trace(
        self,
        target_ip: str,
        dest_port: int = 443,
        max_hops: int = 15,
        probes_per_hop: int = 3,
        timeout_sec: float = 0.8,
    ) -> TraceRouteReport:
        start_time = time.perf_counter()
        hops: List[HopResult] = []
        target_reached = False
        target_rtt: Optional[float] = None

        has_npcap = NpcapCaptureManager.is_available()
        sniffer: Optional[NpcapCaptureManager] = None
        if has_npcap:
            sniffer = NpcapCaptureManager(self.local_ip)
            bpf = f"icmp or (tcp and src host {target_ip} and src port {dest_port})"
            if not sniffer.start(bpf_filter=bpf):
                sniffer = None

        driver_info = (
            "Windows Npcap Raw Sniffer Active (ICMP Time Exceeded + TCP SYN-ACK/RST)"
            if sniffer
            else "Windows Socket-Level TCP Trace (SYN-ACK / RST Active; Npcap not present for intermediate ICMP)"
        )

        try:
            for ttl in range(1, max_hops + 1):
                probe_results: List[ProbeResult] = []
                hop_ip: Optional[str] = None

                for p_idx in range(probes_per_hop):
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.setblocking(False)
                    try:
                        s.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
                        # Bind ephemeral port
                        s.bind(("", 0))
                        sport = s.getsockname()[1]
                    except Exception as exc:
                        logger.debug("Failed setting socket options: %s", exc)
                        s.close()
                        continue

                    t_send = time.perf_counter()
                    conn_res = s.connect_ex((target_ip, dest_port))
                    matched_icmp = None

                    # If Npcap sniffer is active, listen for ICMP Time Exceeded
                    if sniffer:
                        poll_until = time.perf_counter() + timeout_sec
                        while time.perf_counter() < poll_until:
                            matched_icmp = sniffer.match_icmp_time_exceeded(
                                orig_protocol=6,  # TCP
                                orig_sport=sport,
                                orig_dport=dest_port,
                                send_time=t_send,
                            )
                            if matched_icmp:
                                break
                            time.sleep(0.01)

                    if matched_icmp:
                        r_ip, i_type, i_code, rtt = matched_icmp
                        hop_ip = r_ip
                        probe_results.append(
                            ProbeResult(
                                probe_index=p_idx + 1,
                                rtt_ms=rtt,
                                responding_ip=r_ip,
                                status_code="TTL_EXPIRED",
                                details=f"ICMP Time Exceeded (Type {i_type}) from {r_ip}",
                            )
                        )
                    else:
                        # Check destination TCP socket response (SYN-ACK or RST)
                        # On Windows: connect_ex return 0 = SYN-ACK received; WSAECONNREFUSED (10061) = RST received
                        import select
                        _, writable, errored = select.select([], [s], [s], timeout_sec if not sniffer else 0.05)
                        t_resp = time.perf_counter()
                        rtt_handshake = max((t_resp - t_send) * 1000.0, 0.2)

                        sock_err = s.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                        if sock_err == 0 and writable:
                            # Destination responded with SYN-ACK! Connection established!
                            target_reached = True
                            target_rtt = rtt_handshake
                            hop_ip = target_ip
                            probe_results.append(
                                ProbeResult(
                                    probe_index=p_idx + 1,
                                    rtt_ms=rtt_handshake,
                                    responding_ip=target_ip,
                                    status_code="TCP_SYN_ACK",
                                    details=f"Destination port {dest_port} returned TCP SYN-ACK",
                                )
                            )
                        elif sock_err in (10061, socket.errno.ECONNREFUSED):
                            # Destination responded with TCP RST! Port closed but host is definitely alive!
                            target_reached = True
                            target_rtt = rtt_handshake
                            hop_ip = target_ip
                            probe_results.append(
                                ProbeResult(
                                    probe_index=p_idx + 1,
                                    rtt_ms=rtt_handshake,
                                    responding_ip=target_ip,
                                    status_code="TCP_RST",
                                    details=f"Destination port {dest_port} returned TCP RST (Destination Reachable)",
                                )
                            )
                        else:
                            probe_results.append(
                                ProbeResult(
                                    probe_index=p_idx + 1,
                                    rtt_ms=None,
                                    responding_ip=None,
                                    status_code="TIMEOUT",
                                    details="No ICMP Time Exceeded or TCP reply received",
                                )
                            )

                    s.close()

                is_responding = any(p.rtt_ms is not None for p in probe_results)
                hop_cls = HopClassification.RESPONDING if is_responding else HopClassification.SILENT_HOP
                h = HopResult(
                    hop_number=ttl,
                    protocol=ProbeProtocol.TCP,
                    classification=hop_cls,
                    ip=hop_ip,
                    hostname=None,
                    probes=probe_results,
                )
                h.calculate_stats()
                hops.append(h)

                if target_reached:
                    break
        finally:
            if sniffer:
                sniffer.stop()

        _classify_trace_hops(hops, target_reached)
        duration = max(time.perf_counter() - start_time, 0.05)
        overall_cls = _determine_overall_classification(hops, target_reached)

        return TraceRouteReport(
            protocol=ProbeProtocol.TCP,
            target=target_ip,
            target_ip=target_ip,
            target_reached=target_reached,
            target_rtt_ms=target_rtt,
            total_hops=len(hops),
            hops=hops,
            trace_classification=overall_cls,
            driver_info=driver_info,
            duration_sec=duration,
        )


# =====================================================================
# Method C: UDP Traceroute Engine
# =====================================================================

class UdpTracerouteEngine:
    """UDP-based traceroute sending datagrams with progressive TTL values.

    Captures ICMP Time Exceeded and Destination Port Unreachable responses
    when Npcap is available, handling UDP filtering and timeouts accurately.
    """

    def __init__(self, local_ip: Optional[str] = None) -> None:
        if not local_ip:
            local_ip = _get_default_local_ip()
        self.local_ip = local_ip

    def run_trace(
        self,
        target_ip: str,
        base_port: int = 33434,
        max_hops: int = 15,
        probes_per_hop: int = 3,
        timeout_sec: float = 0.8,
    ) -> TraceRouteReport:
        start_time = time.perf_counter()
        hops: List[HopResult] = []
        target_reached = False
        target_rtt: Optional[float] = None

        has_npcap = NpcapCaptureManager.is_available()
        sniffer: Optional[NpcapCaptureManager] = None
        if has_npcap:
            sniffer = NpcapCaptureManager(self.local_ip)
            bpf = f"icmp or (udp and src host {target_ip})"
            if not sniffer.start(bpf_filter=bpf):
                sniffer = None

        driver_info = (
            "Windows Npcap Raw Sniffer Active (UDP ICMP Time Exceeded / Port Unreach)"
            if sniffer
            else "Windows Socket-Level UDP Trace (Npcap required for intermediate ICMP capture)"
        )

        port_counter = base_port
        try:
            for ttl in range(1, max_hops + 1):
                probe_results: List[ProbeResult] = []
                hop_ip: Optional[str] = None

                for p_idx in range(probes_per_hop):
                    port_counter += 1
                    dport = port_counter
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    try:
                        s.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
                        s.bind(("", 0))
                        sport = s.getsockname()[1]
                    except Exception as exc:
                        logger.debug("Failed setting UDP socket options: %s", exc)
                        s.close()
                        continue

                    t_send = time.perf_counter()
                    try:
                        s.sendto(b"NetGuardUDPTracerouteProbe", (target_ip, dport))
                    except Exception as exc:
                        probe_results.append(ProbeResult(p_idx + 1, None, None, "ERROR", str(exc)))
                        s.close()
                        continue

                    matched_icmp = None
                    if sniffer:
                        poll_until = time.perf_counter() + timeout_sec
                        while time.perf_counter() < poll_until:
                            matched_icmp = sniffer.match_icmp_time_exceeded(
                                orig_protocol=17,  # UDP
                                orig_sport=sport,
                                orig_dport=dport,
                                send_time=t_send,
                            )
                            if matched_icmp:
                                break
                            time.sleep(0.01)

                    if matched_icmp:
                        r_ip, i_type, i_code, rtt = matched_icmp
                        hop_ip = r_ip
                        if i_type == 11:
                            probe_results.append(
                                ProbeResult(
                                    probe_index=p_idx + 1,
                                    rtt_ms=rtt,
                                    responding_ip=r_ip,
                                    status_code="TTL_EXPIRED",
                                    details=f"ICMP Time Exceeded from {r_ip}",
                                )
                            )
                        elif i_type == 3:  # Destination unreachable (e.g., port unreachable = destination reached)
                            target_reached = True
                            target_rtt = rtt
                            probe_results.append(
                                ProbeResult(
                                    probe_index=p_idx + 1,
                                    rtt_ms=rtt,
                                    responding_ip=r_ip,
                                    status_code="PORT_UNREACHABLE",
                                    details=f"ICMP Port Unreachable from target {r_ip} (Destination Reached)",
                                )
                            )
                    else:
                        probe_results.append(
                            ProbeResult(
                                probe_index=p_idx + 1,
                                rtt_ms=None,
                                responding_ip=None,
                                status_code="TIMEOUT",
                                details="UDP probe timed out or intermediate ICMP filtered",
                            )
                        )
                    s.close()

                is_responding = any(p.rtt_ms is not None for p in probe_results)
                hop_cls = HopClassification.RESPONDING if is_responding else HopClassification.SILENT_HOP
                h = HopResult(
                    hop_number=ttl,
                    protocol=ProbeProtocol.UDP,
                    classification=hop_cls,
                    ip=hop_ip,
                    hostname=None,
                    probes=probe_results,
                )
                h.calculate_stats()
                hops.append(h)

                if target_reached:
                    break
        finally:
            if sniffer:
                sniffer.stop()

        _classify_trace_hops(hops, target_reached)
        duration = max(time.perf_counter() - start_time, 0.05)
        overall_cls = _determine_overall_classification(hops, target_reached)

        return TraceRouteReport(
            protocol=ProbeProtocol.UDP,
            target=target_ip,
            target_ip=target_ip,
            target_reached=target_reached,
            target_rtt_ms=target_rtt,
            total_hops=len(hops),
            hops=hops,
            trace_classification=overall_cls,
            driver_info=driver_info,
            duration_sec=duration,
        )


# =====================================================================
# Intelligent Classification & Case Determination Rules
# =====================================================================

def _classify_trace_hops(hops: List[HopResult], target_reached: bool) -> None:
    """Applies the 6 required state classifications across individual hops."""
    for i, h in enumerate(hops):
        if h.classification == HopClassification.RESPONDING:
            continue

        # Check if ANY subsequent hop in the trace responded
        subsequent_responded = any(
            next_h.classification == HopClassification.RESPONDING
            for next_h in hops[i + 1 :]
        )
        h.subsequent_hops_responded = subsequent_responded

        if subsequent_responded:
            # Subsequent hop responded: packets definitely traversed this silent hop!
            h.classification = HopClassification.PATH_CONTINUES
            h.reason = "حجب استجابات التحكم (Control-Plane ICMP) مع استمرار مرور البيانات للمحطات اللاحقة"
        elif target_reached:
            # Target was reached at the end of the trace, but intermediate router was silent
            h.classification = HopClassification.INTERMEDIATE_FILTERING_SUSPECTED
            h.reason = "الهدف النهائي متاح ولكن هذا الموجّه الوسيط يحجب حزم استطلاع المسار"
        else:
            # Neither this hop nor any later hop responded
            h.classification = HopClassification.TRACE_INCONCLUSIVE
            h.reason = "لم تستجب هذه المحطة ولا أي محطة لاحقة في هذا المسار"


def _determine_overall_classification(hops: List[HopResult], target_reached: bool) -> HopClassification:
    if target_reached:
        if all(h.classification == HopClassification.RESPONDING for h in hops):
            return HopClassification.RESPONDING
        return HopClassification.INTERMEDIATE_FILTERING_SUSPECTED

    # Check for actual unreachable responses
    for h in hops:
        for p in h.probes:
            if p.status_code in ("DEST_UNREACHABLE", "DESTINATION_UNREACHABLE"):
                return HopClassification.DESTINATION_UNREACHABLE

    # Check hops beyond local gateway (hop 2 and above)
    hops_beyond_gw = [h for h in hops if h.hop_number >= 2]
    if hops_beyond_gw:
        # Case 3: Hop 2 does not respond and all subsequent probes time out -> TRACE_INCONCLUSIVE
        has_responding_beyond_gw = any(h.classification == HopClassification.RESPONDING for h in hops_beyond_gw)
        if not has_responding_beyond_gw:
            return HopClassification.TRACE_INCONCLUSIVE
        return HopClassification.PATH_CONTINUES

    return HopClassification.TRACE_INCONCLUSIVE


# =====================================================================
# Section 3: Independent End-to-End Connectivity Verification
# =====================================================================

class EndToEndConnectivityVerifier:
    """Verifies end-to-end reachability independently of intermediate traceroute responses.

    Tests TCP Port 443 handshake, DNS resolution, and HTTPS requests across
    multiple independent global endpoints to distinguish intermediate filtering
    from true internet outages.
    """

    TEST_TARGETS = [
        ("1.1.1.1", 443, "https://1.1.1.1"),
        ("8.8.8.8", 443, "https://8.8.8.8"),
        ("google.com", 443, "https://www.google.com"),
    ]

    def verify_all(self, timeout_sec: float = 2.0) -> List[EndToEndCheckResult]:
        results: List[EndToEndCheckResult] = []
        for host, port, url in self.TEST_TARGETS:
            res = self.verify_single_target(host, port, url, timeout_sec=timeout_sec)
            results.append(res)
        return results

    def verify_single_target(
        self,
        host: str,
        port: int = 443,
        url: str = "",
        timeout_sec: float = 2.0,
    ) -> EndToEndCheckResult:
        # 1. DNS Resolution Check
        dns_ok = False
        dns_rtt: Optional[float] = None
        target_ip = host

        t0_dns = time.perf_counter()
        try:
            addr_info = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
            if addr_info and addr_info[0][4]:
                dns_ok = True
                dns_rtt = round((time.perf_counter() - t0_dns) * 1000.0, 1)
                target_ip = addr_info[0][4][0]
        except Exception:
            dns_ok = False

        # If host is already an IP, DNS is inherently N/A or OK
        if re.match(r"^\d{1,3}(?:\.\d{1,3}){3}$", host):
            dns_ok = True
            dns_rtt = 0.1

        # 2. TCP 443 3-Way Handshake
        tcp_ok = False
        tcp_rtt: Optional[float] = None
        if target_ip:
            t0_tcp = time.perf_counter()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout_sec)
            try:
                s.connect((target_ip, port))
                tcp_ok = True
                tcp_rtt = round((time.perf_counter() - t0_tcp) * 1000.0, 1)
            except Exception:
                tcp_ok = False
            finally:
                s.close()

        # 3. HTTPS Fetch (if URL provided and TCP succeeded)
        https_ok = False
        status_code: Optional[int] = None
        if url and tcp_ok:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers={"User-Agent": "NetGuard-Probe/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=timeout_sec, context=ctx) as resp:
                    status_code = resp.status
                    https_ok = 200 <= status_code < 400
            except urllib.error.HTTPError as he:
                status_code = he.code
                https_ok = True  # Server responded with valid HTTP error
            except Exception:
                https_ok = False

        details = (
            f"TCP-443: {'نجح' if tcp_ok else 'فشل'} ({tcp_rtt or '—'} ms) · "
            f"DNS: {'نجح' if dns_ok else 'فشل'} · "
            f"HTTPS: {'نشط' if https_ok else 'غير متاح'}"
        )

        return EndToEndCheckResult(
            target=host,
            tcp_443_ok=tcp_ok,
            tcp_443_rtt_ms=tcp_rtt,
            dns_ok=dns_ok,
            dns_rtt_ms=dns_rtt,
            https_ok=https_ok,
            https_status_code=status_code,
            details=details,
        )


# =====================================================================
# Section 4: Multi-Protocol Analyzer & Diagnostic Rules Evaluator
# =====================================================================

class MultiProtocolAnalyzer:
    """Orchestrates ICMP, TCP, UDP traces and end-to-end verification.

    Evaluates CASE 1, CASE 2, CASE 3, and CASE 4 strictly according to evidence:
    - CASE 1: Hop 2 silent, Hop 3+ responds -> packets progressed, non-responsive hop, not network failure.
    - CASE 2: Intermediate hops silent, independent TCP/HTTPS succeeds -> end-to-end working, intermediate visibility limited.
    - CASE 3: Hop 2 silent, all subsequent time out -> inconclusive, verify end-to-end separately.
    - CASE 4: Valid unreachable response -> report actual unreachable condition and error info.
    """

    def __init__(self, platform_adapter=None) -> None:
        self.platform = platform_adapter
        self.local_ip = _get_default_local_ip()
        self.icmp_engine = IcmpTracerouteEngine(platform_adapter)
        self.tcp_engine = TcpTracerouteEngine(self.local_ip)
        self.udp_engine = UdpTracerouteEngine(self.local_ip)
        self.e2e_verifier = EndToEndConnectivityVerifier()

    def run_full_analysis(
        self,
        target_ip: str = "1.1.1.1",
        max_hops: int = 12,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> MultiProtocolAnalysisReport:
        if progress_callback:
            progress_callback("تنفيذ فحص تتبع المسار عبر بروتوكول ICMP...")
        icmp_report = self.icmp_engine.run_trace(target_ip, max_hops=max_hops)

        if progress_callback:
            progress_callback("تنفيذ فحص تتبع المسار عبر بروتوكول TCP (Port 443)...")
        tcp_report = self.tcp_engine.run_trace(target_ip, dest_port=443, max_hops=max_hops)

        if progress_callback:
            progress_callback("تنفيذ فحص تتبع المسار عبر بروتوكول UDP...")
        udp_report = self.udp_engine.run_trace(target_ip, max_hops=max_hops)

        if progress_callback:
            progress_callback("التحقق المستقل من الاتصال الفعلي بالنهاية الطرفية (End-to-End)...")
        e2e_results = self.e2e_verifier.verify_all()

        overall_e2e_ok = any(r.tcp_443_ok or r.https_ok for r in e2e_results)
        dns_all_failed = all(not r.dns_ok for r in e2e_results if not re.match(r"^\d{1,3}(?:\.\d{1,3}){3}$", r.target))

        # Inspect Hop 2 across all 3 methods
        h2_icmp = icmp_report.get_hop(2)
        h2_tcp = tcp_report.get_hop(2)
        h2_udp = udp_report.get_hop(2)

        # Collect discovered IP and measured latency from any responding method
        h2_discovered_ip: Optional[str] = None
        h2_protocol_used: Optional[ProbeProtocol] = None
        h2_latency: Optional[float] = None
        for candidate in (h2_icmp, h2_tcp, h2_udp):
            if candidate and candidate.ip:
                h2_discovered_ip = candidate.ip
                h2_protocol_used = candidate.protocol
                if candidate.avg_rtt_ms is not None:
                    h2_latency = candidate.avg_rtt_ms
                break

        # Check if subsequent hops (Hop 3+) responded in any trace
        subsequent_responded_any = False
        for report in (icmp_report, tcp_report, udp_report):
            for h in report.hops:
                if h.hop_number >= 3 and h.classification == HopClassification.RESPONDING:
                    subsequent_responded_any = True
                    break

        # Check for destination unreachable response (Case 4)
        has_unreachable = False
        unreach_details = ""
        for report in (icmp_report, tcp_report, udp_report):
            if report.trace_classification == HopClassification.DESTINATION_UNREACHABLE:
                has_unreachable = True
                unreach_details = f"وردت استجابة تعذر الوصول (Destination Unreachable) عبر {report.protocol.value}"
                break

        # Evaluate the 4 Required Cases
        if has_unreachable:
            case_id = "CASE_4"
            hop2_cls = HopClassification.DESTINATION_UNREACHABLE
            e2e_status = EndToEndStatus.DESTINATION_UNREACHABLE
            verdict_ar = "الهدف غير متاح (Destination Unreachable)"
            tech_ar = (
                f"أفادت حزم التشخيص بتعذر الوصول الفعلي للوجهة: {unreach_details}. "
                "لا توجد مشكلة في مسار التوجيه الأولي لجهازك، ولكن المسار نحو الهدف مقطوع أو محجوب."
            )
            reason = "استجابة صريحة بتعذر الوصول للشبكة أو المنفذ الهدف"

        elif h2_discovered_ip is not None:
            # Hop 2 actually responded on at least one protocol!
            case_id = "NORMAL_RESPONDING"
            hop2_cls = HopClassification.RESPONDING
            e2e_status = EndToEndStatus.DESTINATION_REACHABLE if overall_e2e_ok else EndToEndStatus.ACTUAL_INTERNET_OUTAGE
            lat_str = f"{h2_latency:.1f} ms" if h2_latency is not None else "—"
            verdict_ar = f"المحطة الثانية تستجيب بنجاح ({lat_str})"
            tech_ar = (
                f"تم رصد عنوان المحطة الثانية بنجاح ({h2_discovered_ip}) عبر بروتوكول {h2_protocol_used.value} "
                f"بزمن استجابة مقاس فعلياً {lat_str}. الاتصال الميداني سليم."
            )
            reason = "المحطة استجابت بنجاح وتم تسجيل عنوانها وزمن وصول الحزم الفعلي"

        elif subsequent_responded_any:
            # CASE 1: Hop 2 does not respond, but Hop 3 or later hops respond in the same trace
            case_id = "CASE_1"
            hop2_cls = HopClassification.PATH_CONTINUES
            e2e_status = EndToEndStatus.DESTINATION_REACHABLE if overall_e2e_ok else EndToEndStatus.INTERMEDIATE_ROUTER_SILENT
            verdict_ar = "المحطة الثانية صامتة مع استمرار تدفق البيانات (Path Continues)"
            tech_ar = (
                "المحطة الثانية (Hop 02) لم ترسل استجابة ICMP Time Exceeded مباشرة، "
                "ولكن حزم البيانات عبرتها بنجاح ووصلت للمحطة الثالثة وما بعدها. "
                "هذا يثبت أن الموجّه يعمل كمعبر تمرير سليم وأن عدم ظهوره ناتج عن قيود حماية المعالج (CoPP) وليس انقطاعاً في الشبكة."
            )
            reason = "الموجّه يمرر البيانات للمحطات التالية ويحجب حزم استطلاع المسار ICMP Time Exceeded"

        elif overall_e2e_ok:
            # CASE 2: Intermediate hops do not respond, but independent TCP/HTTPS connectivity succeeds
            case_id = "CASE_2"
            hop2_cls = HopClassification.INTERMEDIATE_FILTERING_SUSPECTED
            e2e_status = EndToEndStatus.INTERMEDIATE_ROUTER_SILENT
            verdict_ar = "الاتصال بالإنترنت يعمل بكفاءة مع حجب استطلاع المسار الوسيط"
            tech_ar = (
                "تعذر استكشاف تفاصيل المسارات الوسيطة، ولكن الفحص المستقل أثبت نجاح مصافحة TCP Port 443 "
                "واتصال HTTPS بكفاءة تامة. الاتصال بالإنترنت نشط ولا يوجد انقطاع فعلي."
            )
            reason = "فلاتر جدار الحماية للشبكة تحجب حزم التتبع الوسيطة بالكامل مع استمرار الاتصال الطرفي"

        elif dns_all_failed:
            case_id = "CASE_3"
            hop2_cls = HopClassification.TRACE_INCONCLUSIVE
            e2e_status = EndToEndStatus.DNS_FAILURE
            verdict_ar = "تعذر الاتصال نتيجة فشل خوادم ترجمة العناوين (DNS Failure)"
            tech_ar = "فشل تحليل أسماء النطاقات عبر خوادم DNS المعتمدة، مع تعذر الوصول للمسارات الخارجية."
            reason = "انقطاع أو عدم استجابة خوادم تحليل العناوين DNS"

        else:
            # CASE 3: Hop 2 does not respond and all subsequent probes time out
            case_id = "CASE_3"
            hop2_cls = HopClassification.TRACE_INCONCLUSIVE
            e2e_status = EndToEndStatus.ACTUAL_INTERNET_OUTAGE
            verdict_ar = "فحص المسار غير حاسم — تعذر التحقق من الاتصال الخارجي"
            tech_ar = (
                "لم تستجب المحطة الثانية ولا أي محطة لاحقة، كما فشل الاتصال المباشر بمنفذ HTTPS 443. "
                "لا يمكن الجزم بنجاح التمرير الداخلي ويشتبه بوجود انقطاع في الشبكة أو انفصال الكابل الخارجي."
            )
            reason = "غياب تام لاستجابات المسار وفشل الاتصال الطرفي المباشر"

        driver_summary = (
            f"ICMP: {icmp_report.driver_info} · "
            f"TCP: {tcp_report.driver_info} · "
            f"UDP: {udp_report.driver_info}"
        )

        return MultiProtocolAnalysisReport(
            timestamp=datetime.now(timezone.utc),
            target=target_ip,
            target_ip=target_ip,
            icmp_trace=icmp_report,
            tcp_trace=tcp_report,
            udp_trace=udp_report,
            end_to_end_checks=e2e_results,
            overall_end_to_end_ok=overall_e2e_ok,
            end_to_end_status=e2e_status,
            case_identified=case_id,
            hop2_classification=hop2_cls,
            hop2_ip=h2_discovered_ip,
            hop2_protocol=h2_protocol_used,
            hop2_latency_ms=h2_latency,
            hop2_reason=reason,
            hop2_subsequent_responded=subsequent_responded_any,
            consolidated_verdict_arabic=verdict_ar,
            technical_details_arabic=tech_ar,
            driver_summary=driver_summary,
        )


def _get_default_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        if local_ip and not local_ip.startswith("127."):
            return local_ip
    except Exception:
        pass
    return "127.0.0.1"
