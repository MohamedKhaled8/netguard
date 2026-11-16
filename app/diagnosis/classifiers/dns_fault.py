"""DNS Health and Responsiveness Classifier."""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional
from app.core.models.metrics import (
    Diagnosis,
    ProbableCause,
    DiagnosisSeverity,
    Evidence,
    MetricType,
)
from app.diagnosis.classifiers.base import BaseClassifier
from app.diagnosis.evidence import EvidenceSummary


class DNSHealthClassifier(BaseClassifier):
    """Diagnoses DNS resolver failure and resolution slowness when direct IP connectivity is intact."""

    def evaluate(self, summaries: Dict[MetricType, EvidenceSummary]) -> Optional[Diagnosis]:
        dns_success = summaries.get(MetricType.DNS_SUCCESS_RATE)
        dns_lat = summaries.get(MetricType.DNS_LATENCY)
        ext_loss = summaries.get(MetricType.EXTERNAL_PACKET_LOSS)
        gw_reach = summaries.get(MetricType.GATEWAY_REACHABILITY)

        if not dns_success and not dns_lat:
            return None

        # Check if direct IP connectivity is available (Gateway and External are reachable)
        ext_healthy_max = getattr(getattr(self.thresholds, "loss", None), "external_healthy_max_ratio", 0.20)
        dns_fail_thresh = getattr(getattr(self.thresholds, "loss", None), "dns_failure_rate_threshold", 0.50)
        gateway_healthy = gw_reach and gw_reach.latest_value == 1.0
        external_ip_healthy = ext_loss and ext_loss.latest_value <= ext_healthy_max

        # Case 1: Total DNS Resolution Failure
        if dns_success and dns_success.latest_value < dns_fail_thresh:
            # If external IP is healthy, we have high confidence this is purely a DNS problem!
            confidence = 0.95 if (gateway_healthy and external_ip_healthy) else 0.70
            severity = DiagnosisSeverity.HIGH

            supporting = [
                Evidence(
                    metric_type=MetricType.DNS_SUCCESS_RATE,
                    target="dns_resolver",
                    observed_value=dns_success.latest_value,
                    threshold_value=dns_fail_thresh,
                    condition=f"dns_success_rate < {dns_fail_thresh}",
                    weight=1.5,
                )
            ]
            contradictory = []
            if not external_ip_healthy:
                contradictory.append(
                    Evidence(
                        metric_type=MetricType.EXTERNAL_PACKET_LOSS,
                        target="wan_ip",
                        observed_value=ext_loss.latest_value if ext_loss else 1.0,
                        threshold_value=ext_healthy_max,
                        condition="external_ip_loss_high (possible general outage)",
                        weight=1.0,
                    )
                )

            return Diagnosis(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
                confidence=confidence,
                severity=severity,
                supporting_evidence=supporting,
                contradictory_evidence=contradictory,
                recommended_actions=["flush_dns_cache", "switch_dns_resolver"],
                auto_remediation_permitted=True if confidence >= 0.85 else False,
                explanation="DNS queries are failing while direct IP connectivity is intact. Resolver is unresponsive.",
            )

        # Case 2: Slow DNS Resolution
        if dns_lat and dns_lat.mean >= self.thresholds.dns_latency_critical_ms:
            ev = Evidence(
                metric_type=MetricType.DNS_LATENCY,
                target="dns_resolver",
                observed_value=dns_lat.mean,
                threshold_value=self.thresholds.dns_latency_critical_ms,
                condition=f"dns_latency >= {self.thresholds.dns_latency_critical_ms}ms",
                weight=1.2,
            )
            return Diagnosis(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                probable_cause=ProbableCause.DNS_RESOLVER_HIGH_LATENCY,
                confidence=0.85,
                severity=DiagnosisSeverity.MEDIUM,
                supporting_evidence=[ev],
                contradictory_evidence=[],
                recommended_actions=["switch_dns_resolver"],
                auto_remediation_permitted=True,
                explanation=f"DNS query latency (mean {dns_lat.mean:.1f}ms) is severely degraded.",
            )

        return None
