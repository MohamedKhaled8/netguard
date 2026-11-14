"""Gateway Health and Reachability Classifier."""

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
    ProbeStatus,
)
from app.diagnosis.classifiers.base import BaseClassifier
from app.diagnosis.evidence import EvidenceSummary


class GatewayHealthClassifier(BaseClassifier):
    """Diagnoses local gateway unreachability and severe latency degradation."""

    def evaluate(self, summaries: Dict[MetricType, EvidenceSummary]) -> Optional[Diagnosis]:
        gw_reach = summaries.get(MetricType.GATEWAY_REACHABILITY)
        gw_lat = summaries.get(MetricType.GATEWAY_LATENCY)
        gw_loss = summaries.get(MetricType.GATEWAY_PACKET_LOSS)

        if not gw_reach and not gw_lat and not gw_loss:
            return None

        # 1. Total Gateway Unreachability
        # Require sustained failure (failure ratio >= threshold or multiple failures)
        is_sustained_loss = (
            (gw_reach and gw_reach.failure_ratio >= 0.50)
            or (gw_loss and gw_loss.failure_ratio >= self.thresholds.gateway_packet_loss_critical)
            or (gw_reach and gw_reach.latest_value == 0.0 and gw_reach.count == 1)
        )
        if is_sustained_loss:
            ev_list = []
            if gw_reach:
                ev_list.append(
                    Evidence(
                        metric_type=MetricType.GATEWAY_REACHABILITY,
                        target="gateway",
                        observed_value=gw_reach.latest_value,
                        threshold_value=1.0,
                        condition="gateway_reachability == 0",
                        weight=1.5,
                    )
                )
            if gw_loss:
                ev_list.append(
                    Evidence(
                        metric_type=MetricType.GATEWAY_PACKET_LOSS,
                        target="gateway",
                        observed_value=gw_loss.latest_value,
                        threshold_value=self.thresholds.gateway_packet_loss_critical,
                        condition=f"packet_loss >= {self.thresholds.gateway_packet_loss_critical}",
                        weight=1.5,
                    )
                )

            # Check if external is also down
            ext_loss = summaries.get(MetricType.EXTERNAL_PACKET_LOSS)
            confidence = 0.95 if (ext_loss and ext_loss.latest_value >= 0.5) else 0.85

            return Diagnosis(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                probable_cause=ProbableCause.LOCAL_GATEWAY_UNREACHABLE,
                confidence=confidence,
                severity=DiagnosisSeverity.CRITICAL,
                supporting_evidence=ev_list,
                contradictory_evidence=[],
                recommended_actions=["recheck_gateway"],
                auto_remediation_permitted=True,
                explanation="Default gateway failed to respond to echo probes. Local link or router is offline.",
            )

        # 2. High Gateway Latency
        if gw_lat and gw_lat.mean >= self.thresholds.gateway_latency_critical_ms:
            ev = Evidence(
                metric_type=MetricType.GATEWAY_LATENCY,
                target="gateway",
                observed_value=gw_lat.mean,
                threshold_value=self.thresholds.gateway_latency_critical_ms,
                condition=f"mean_latency >= {self.thresholds.gateway_latency_critical_ms}ms",
                weight=1.2,
            )
            return Diagnosis(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                probable_cause=ProbableCause.LOCAL_GATEWAY_HIGH_LATENCY,
                confidence=0.85,
                severity=DiagnosisSeverity.HIGH,
                supporting_evidence=[ev],
                contradictory_evidence=[],
                recommended_actions=["inspect_wifi_interference", "check_local_link"],
                auto_remediation_permitted=False,
                explanation=f"Gateway round-trip latency (mean {gw_lat.mean:.1f}ms) exceeds critical threshold.",
            )

        return None
