"""Authoritative network health evaluation with hysteresis and multi-probe agreement (Item C0)."""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone


class HealthStatus(str, Enum):
    GOOD = "good"
    WARNING = "warning"
    CRITICAL = "critical"
    NOT_MEASURED = "not_measured"


class NetworkIssueType(str, Enum):
    NONE = "none"
    LOCAL_GATEWAY_DEGRADED = "local_gateway_degraded"
    INTERNET_OUTAGE = "internet_outage"
    HIGH_JITTER_MEETING_RISK = "high_jitter_meeting_risk"
    PACKET_LOSS_RISK = "packet_loss_risk"
    DNS_DEGRADED = "dns_degraded"
    BUFFERBLOAT_DEGRADED = "bufferbloat_degraded"


@dataclass
class HealthSample:
    """Telemetry data point for network health assessment."""
    gateway_latency_ms: Optional[float] = None
    gateway_loss_pct: float = 0.0
    internet_latency_ms: Optional[float] = None
    internet_loss_pct: float = 0.0
    internet_targets_failed: int = 0
    internet_targets_total: int = 2
    jitter_ms: Optional[float] = None
    dns_latency_ms: Optional[float] = None
    bufferbloat_grade: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class NetworkHealthVerdict:
    """The honest, un-invented assessment of current network health."""
    status: HealthStatus
    primary_issue: NetworkIssueType
    headline: str
    detail: str
    metric_name: Optional[str] = None
    measured_value: Optional[float] = None
    consecutive_degraded_count: int = 0
    consecutive_good_count: int = 0


class HealthEvaluator:
    """Evaluates network health using multi-probe agreement and anti-flapping hysteresis."""

    def __init__(
        self,
        degraded_threshold_samples: int = 2,
        recovery_threshold_samples: int = 3,
    ) -> None:
        self.degraded_threshold = degraded_threshold_samples
        self.recovery_threshold = recovery_threshold_samples
        self._current_status: HealthStatus = HealthStatus.GOOD
        self._consecutive_degraded: int = 0
        self._consecutive_good: int = 0
        self._last_verdict: Optional[NetworkHealthVerdict] = None

    @property
    def current_status(self) -> HealthStatus:
        return self._current_status

    def evaluate(self, sample: HealthSample) -> NetworkHealthVerdict:
        """Evaluate sample and return authoritative verdict."""
        # Check if anything is measured
        is_empty = (
            sample.gateway_latency_ms is None
            and sample.internet_latency_ms is None
            and sample.dns_latency_ms is None
        )
        if is_empty:
            return NetworkHealthVerdict(
                status=HealthStatus.NOT_MEASURED,
                primary_issue=NetworkIssueType.NONE,
                headline="غير مُقاس",
                detail="في انتظار جمع بيانات الفحص الحي للشبكة.",
            )

        # 1. Determine raw health of this specific sample
        raw_status = HealthStatus.GOOD
        issue = NetworkIssueType.NONE
        metric_name: Optional[str] = None
        measured_val: Optional[float] = None
        detail = "جميع المؤشرات والراوتر وخوادم DNS تعمل ضمن الحدود المثالية دون أي تشويش."

        # A. Multi-probe agreement: Internet Outage
        # Requires gateway reachable AND internet probes (>=2 failed targets)
        if (
            sample.gateway_latency_ms is not None
            and sample.internet_targets_failed >= 2
            and sample.internet_targets_failed >= sample.internet_targets_total
        ):
            raw_status = HealthStatus.CRITICAL
            issue = NetworkIssueType.INTERNET_OUTAGE
            metric_name = "Internet Targets Failed"
            measured_val = float(sample.internet_targets_failed)
            detail = "الراوتر المحلي متصل ولكن تعذّر الوصول إلى خوادم الإنترنت العالمية (فشل أكثر من خادم فحص)."

        # B. Local network issue (elevated gateway latency or gateway packet loss)
        elif sample.gateway_loss_pct >= 5.0 or (sample.gateway_latency_ms is not None and sample.gateway_latency_ms > 20.0):
            raw_status = HealthStatus.WARNING if sample.gateway_loss_pct < 15.0 else HealthStatus.CRITICAL
            issue = NetworkIssueType.LOCAL_GATEWAY_DEGRADED
            metric_name = "Gateway Loss" if sample.gateway_loss_pct >= 5.0 else "Gateway Latency"
            measured_val = sample.gateway_loss_pct if sample.gateway_loss_pct >= 5.0 else sample.gateway_latency_ms
            detail = f"تراجع الاتصال بالراوتر المنزلي ({measured_val:.1f}{'%' if sample.gateway_loss_pct >= 5.0 else ' ms'}). يُرجى الاقتراب من الراوتر."

        # C. Meeting risk: Jitter > 30 ms or sustained internet loss > 2%
        elif sample.jitter_ms is not None and sample.jitter_ms > 30.0:
            raw_status = HealthStatus.WARNING
            issue = NetworkIssueType.HIGH_JITTER_MEETING_RISK
            metric_name = "Jitter"
            measured_val = sample.jitter_ms
            detail = f"تذبذب في الاتصال ({sample.jitter_ms:.1f} ms). قد تتأثر جودة الصوت في المكالمات المرئية."

        elif sample.internet_loss_pct > 2.0:
            raw_status = HealthStatus.WARNING
            issue = NetworkIssueType.PACKET_LOSS_RISK
            metric_name = "Internet Loss"
            measured_val = sample.internet_loss_pct
            detail = f"فقدان حزم البيانات بنسبة {sample.internet_loss_pct:.1f}% يتجاوز الحد الموصى به للاجتماعات."

        # D. DNS degraded
        elif sample.dns_latency_ms is not None and sample.dns_latency_ms > 120.0:
            raw_status = HealthStatus.WARNING
            issue = NetworkIssueType.DNS_DEGRADED
            metric_name = "DNS Latency"
            measured_val = sample.dns_latency_ms
            detail = f"خادم DNS بطيء ({sample.dns_latency_ms:.0f} ms). قد يتأخر فتح المواقع والروابط الجديدة."

        # 2. Apply Hysteresis
        if raw_status in (HealthStatus.WARNING, HealthStatus.CRITICAL):
            self._consecutive_good = 0
            self._consecutive_degraded += 1

            if self._current_status == HealthStatus.GOOD:
                # Need at least `degraded_threshold` (2) to transition away from GOOD
                if self._consecutive_degraded < self.degraded_threshold:
                    headline = "الاتصال سليم ومستقر (رصد تذبذب عابر)"
                    verdict = NetworkHealthVerdict(
                        status=HealthStatus.GOOD,
                        primary_issue=NetworkIssueType.NONE,
                        headline=headline,
                        detail="تم رصد تذبذب لحظي عابر، الاتصال لا يزال مستقراً ولم يتأثر.",
                        metric_name=metric_name,
                        measured_value=measured_val,
                        consecutive_degraded_count=self._consecutive_degraded,
                        consecutive_good_count=0,
                    )
                    self._last_verdict = verdict
                    return verdict
                else:
                    self._current_status = raw_status
            else:
                self._current_status = raw_status

            headlines = {
                NetworkIssueType.INTERNET_OUTAGE: "انقطاع الاتصال بالإنترنت العام",
                NetworkIssueType.LOCAL_GATEWAY_DEGRADED: "تراجع جودة الاتصال بالراوتر",
                NetworkIssueType.HIGH_JITTER_MEETING_RISK: "تذبذب عالي قد يؤثر على الاجتماعات",
                NetworkIssueType.PACKET_LOSS_RISK: "فقدان في حزم البيانات",
                NetworkIssueType.DNS_DEGRADED: "بطء في خادم ترجمة العناوين (DNS)",
                NetworkIssueType.NONE: "تحذير بشأن استقرار الشبكة",
            }
            headline = headlines.get(issue, "تحذير بشأن استقرار الشبكة")

        else:  # raw_status == HealthStatus.GOOD
            self._consecutive_degraded = 0
            self._consecutive_good += 1

            if self._current_status in (HealthStatus.WARNING, HealthStatus.CRITICAL):
                # Need at least `recovery_threshold` (3) clean samples to recover
                if self._consecutive_good < self.recovery_threshold:
                    headline = f"جاري استعادة الاستقرار (عينة {self._consecutive_good}/{self.recovery_threshold})"
                    verdict = NetworkHealthVerdict(
                        status=self._current_status,  # remain in warning/critical until 3 good
                        primary_issue=self._last_verdict.primary_issue if self._last_verdict else NetworkIssueType.NONE,
                        headline=headline,
                        detail="الشبكة في طور التعافي، بانتظار تأكيد الاستقرار لعدة ثوانٍ متتالية.",
                        consecutive_degraded_count=0,
                        consecutive_good_count=self._consecutive_good,
                    )
                    return verdict
                else:
                    self._current_status = HealthStatus.GOOD

            headline = "الاتصال سليم ومستقر"

        verdict = NetworkHealthVerdict(
            status=self._current_status,
            primary_issue=issue if self._current_status != HealthStatus.GOOD else NetworkIssueType.NONE,
            headline=headline,
            detail=detail,
            metric_name=metric_name,
            measured_value=measured_val,
            consecutive_degraded_count=self._consecutive_degraded,
            consecutive_good_count=self._consecutive_good,
        )
        self._last_verdict = verdict
        return verdict


def assess_network_health(sample: HealthSample) -> NetworkHealthVerdict:
    """Convenience functional interface for assessing network health on a one-off sample."""
    evaluator = HealthEvaluator(degraded_threshold_samples=1, recovery_threshold_samples=1)
    return evaluator.evaluate(sample)
