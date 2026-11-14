"""Upstream ISP and WAN Degradation Classifier."""

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


class UpstreamISPClassifier(BaseClassifier):
    """Diagnoses upstream ISP / cellular link failures where the local router/gateway is 100% reachable."""

    def evaluate(self, summaries: Dict[MetricType, EvidenceSummary]) -> Optional[Diagnosis]:
        gw_reach = summaries.get(MetricType.GATEWAY_REACHABILITY)
        gw_lat = summaries.get(MetricType.GATEWAY_LATENCY)
        gw_loss = summaries.get(MetricType.GATEWAY_PACKET_LOSS)
        ext_loss = summaries.get(MetricType.EXTERNAL_PACKET_LOSS)
        ext_lat = summaries.get(MetricType.EXTERNAL_LATENCY)

        if not ext_loss and not ext_lat:
            return None

        # Verify gateway health: local gateway must be reachable with low packet loss
        gateway_healthy = (
            (gw_reach and gw_reach.latest_value == 1.0)
            and (not gw_loss or gw_loss.latest_value < 0.20)
            and (not gw_lat or gw_lat.mean < self.thresholds.gateway_latency_critical_ms)
        )

        if not gateway_healthy:
            # If gateway is also failing, the root cause is local link/gateway, not upstream ISP
            return None

        # Check multi-target external packet loss
        # An ISP outage requires multiple independent targets to fail concurrently
        target_losses: Dict[str, float] = {}
        if ext_loss and ext_loss.samples:
            for s in ext_loss.samples:
                target_losses[s.target_or_interface] = s.raw_value

        # Count failing vs healthy external targets
        failing_targets = [t for t, loss in target_losses.items() if loss >= self.thresholds.external_packet_loss_critical]
        total_targets = len(target_losses)

        # If there are multiple targets and only 1 target is failing, it's destination-specific, not ISP outage
        if total_targets > 1 and len(failing_targets) == 1:
            return None

        # Case 1: Severe Upstream Packet Loss / Outage across multiple external targets
        if failing_targets and (len(failing_targets) >= 2 or total_targets <= 1):
            supporting = [
                Evidence(
                    metric_type=MetricType.GATEWAY_REACHABILITY,
                    target="gateway",
                    observed_value=1.0,
                    threshold_value=1.0,
                    condition="gateway_healthy == True",
                    weight=1.2,
                ),
                Evidence(
                    metric_type=MetricType.EXTERNAL_PACKET_LOSS,
                    target="wan_destinations",
                    observed_value=ext_loss.latest_value if ext_loss else 1.0,
                    threshold_value=self.thresholds.external_packet_loss_critical,
                    condition=f"{len(failing_targets)}/{total_targets} external destinations failing",
                    weight=1.5,
                ),
            ]
            return Diagnosis(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                probable_cause=ProbableCause.ISP_UPSTREAM_OUTAGE,
                confidence=0.92,
                severity=DiagnosisSeverity.CRITICAL,
                supporting_evidence=supporting,
                contradictory_evidence=[],
                recommended_actions=["notify_upstream_outage", "inspect_cellular_signal"],
                auto_remediation_permitted=False,  # Cannot locally fix ISP WAN fiber cut or tower outage
                explanation=f"Local gateway is responsive, but {len(failing_targets)}/{total_targets} external destinations show severe packet loss. Upstream ISP or cellular backhaul outage.",
            )

        # Case 2: Severe Upstream Latency Spike
        if ext_lat and ext_lat.mean >= self.thresholds.external_latency_critical_ms:
            supporting = [
                Evidence(
                    metric_type=MetricType.GATEWAY_LATENCY,
                    target="gateway",
                    observed_value=gw_lat.mean if gw_lat else 2.0,
                    threshold_value=self.thresholds.gateway_latency_warning_ms,
                    condition="gateway_latency_normal",
                    weight=1.0,
                ),
                Evidence(
                    metric_type=MetricType.EXTERNAL_LATENCY,
                    target="wan_destinations",
                    observed_value=ext_lat.mean,
                    threshold_value=self.thresholds.external_latency_critical_ms,
                    condition=f"external_latency >= {self.thresholds.external_latency_critical_ms}ms",
                    weight=1.4,
                ),
            ]
            return Diagnosis(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                probable_cause=ProbableCause.ISP_UPSTREAM_HIGH_LATENCY,
                confidence=0.88,
                severity=DiagnosisSeverity.HIGH,
                supporting_evidence=supporting,
                contradictory_evidence=[],
                recommended_actions=["inspect_bufferbloat", "inspect_cellular_signal"],
                auto_remediation_permitted=False,
                explanation=f"Local gateway latency is stable, but external destination latency (mean {ext_lat.mean:.1f}ms) is severely degraded. Upstream congestion.",
            )

        return None
