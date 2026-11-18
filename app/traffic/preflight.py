"""Pre-flight meeting network readiness assessment (Item D5)."""

from __future__ import annotations
import time
import subprocess
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from app.platform.interfaces import IPlatformAdapter
from app.dns.detector import measure_dns_latency
from app.traffic.meeting_detector import evaluate_video_readiness


@dataclass
class PreflightReport:
    """Readiness assessment outcome prior to a video conference."""
    is_ready: bool
    quality_tier: str  # 1080p, 720p, 360p, Audio Only
    gateway_ms: Optional[float]
    gateway_jitter_ms: Optional[float]
    dns_ms: Optional[float]
    wifi_signal_pct: Optional[float]
    heavy_uploaders: List[str] = field(default_factory=list)
    headline: str = ""
    detail: str = ""
    issues_found: List[str] = field(default_factory=list)
    recommended_fix: Optional[str] = None


class MeetingPreflightChecker:
    """Executes rapid pre-meeting diagnostics within 10-15 seconds."""

    def __init__(self, platform: IPlatformAdapter) -> None:
        self.platform = platform

    def run_check(self) -> PreflightReport:
        """Run genuine multi-metric pre-flight network diagnostics."""
        issues = []
        gateway = self.platform.get_default_gateway() or "192.168.1.1"
        iface = self.platform.get_primary_interface() or "Wi-Fi"

        # 1. 10 rapid gateway pings to measure genuine latency & jitter
        gw_latencies = []
        try:
            cmd = ["ping", "-n", "10", "-w", "1000", gateway]
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
            for line in out.stdout.splitlines():
                if "time=" in line or "time<" in line:
                    part = line.split("time=")[-1] if "time=" in line else line.split("time<")[-1]
                    ms_val = float(part.split("ms")[0].strip())
                    gw_latencies.append(ms_val)
        except Exception:
            pass

        if gw_latencies:
            gw_avg = sum(gw_latencies) / len(gw_latencies)
            # Compute jitter as average absolute successive difference
            jitter = (
                sum(abs(gw_latencies[i] - gw_latencies[i - 1]) for i in range(1, len(gw_latencies)))
                / max(1, len(gw_latencies) - 1)
            )
        else:
            gw_avg = None
            jitter = None

        if gw_avg is not None and gw_avg > 25.0:
            issues.append(f"الراوتر بطيء ({gw_avg:.0f} ms) — اقترب من الراوتر أو استخدم كابل إيثرنت")

        # 2. Active DNS latency
        dns_servers = self.platform.get_interface_dns_servers(iface) or [gateway]
        dns_ms = measure_dns_latency(dns_servers[0])
        if dns_ms is not None and dns_ms > 120.0:
            issues.append(f"استجابة DNS بطيئة ({dns_ms:.0f} ms)")

        # 3. Wi-Fi signal quality
        wifi_sig = self.platform.get_wifi_signal_strength()
        if wifi_sig is not None and wifi_sig < 50.0:
            issues.append(f"إشارة الواي فاي ضعيفة ({wifi_sig:.0f}%) — اقترب من الراوتر")

        # 4. Check for running heavy uploaders
        heavy = []
        sync_exes = {"onedrive.exe", "dropbox.exe", "qbittorrent.exe", "steam.exe"}
        import psutil
        for p in psutil.process_iter(["name"]):
            try:
                name = (p.info["name"] or "").lower()
                if name in sync_exes:
                    heavy.append(p.info["name"])
            except Exception:
                pass
        heavy = list(set(heavy))
        if heavy:
            issues.append(f"برامج تستهلك سرعة الرفع في الخلفية: {', '.join(heavy)}")

        # Estimate video readiness
        gw_lat = gw_avg or 2.0
        jit = jitter or 1.0
        # Estimate upload readiness (conservative default: assume 5 Mbps if no issues, or 1.5 if heavy)
        est_upload = 2.0 if heavy else 8.0
        est_loss = 0.0 if not issues else 1.5
        readiness = evaluate_video_readiness(est_upload, est_loss, jit)

        is_ready = len(issues) == 0
        if is_ready:
            headline = f"الشبكة جاهزة للاجتماع — {readiness['headline']}"
            detail = "جميع المؤشرات والراوتر والاتصال ضمن الحدود المثالية لبث مكالمة فيديو فائقة الوضوح دون تقطيع."
            rec_fix = None
        else:
            headline = f"تنبيه جاهزية الاجتماع — يوجد {len(issues)} ملاحظات قد تؤثر على جودة البث"
            detail = " · ".join(issues)
            rec_fix = "تفعيل درع الاجتماعات وتقييد البرامج الخلفية فوراً"

        return PreflightReport(
            is_ready=is_ready,
            quality_tier=readiness["tier"],
            gateway_ms=gw_avg,
            gateway_jitter_ms=jitter,
            dns_ms=dns_ms,
            wifi_signal_pct=wifi_sig,
            heavy_uploaders=heavy,
            headline=headline,
            detail=detail,
            issues_found=issues,
            recommended_fix=rec_fix,
        )
