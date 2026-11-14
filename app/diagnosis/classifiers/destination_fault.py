"""Destination-Specific Blockage / Outage Classifier."""

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


class DestinationSpecificClassifier(BaseClassifier):
    """Detects when an individual remote endpoint fails while general internet connectivity remains normal."""

    def evaluate(self, summaries: Dict[MetricType, EvidenceSummary]) -> Optional[Diagnosis]:
        ext_loss = summaries.get(MetricType.EXTERNAL_PACKET_LOSS)
        if not ext_loss or ext_loss.count < 2:
            return None

        # Group samples by target
        target_statuses: Dict[str, List[ProbeStatus]] = {}
        for s in ext_loss.samples:
            target_statuses.setdefault(s.target_or_interface, []).append(s.status)

        if len(target_statuses) < 2:
            return None

        failing_targets = []
        healthy_targets = []

        for target, statuses in target_statuses.items():
            fail_count = sum(1 for st in statuses if st in (ProbeStatus.FAILED, ProbeStatus.TIMEOUT))
            if fail_count / len(statuses) >= 0.75:
                failing_targets.append(target)
            else:
                healthy_targets.append(target)

        # Isolated failure: only 1 target fails, while other independent targets are healthy
        if len(failing_targets) == 1 and len(healthy_targets) >= 1:
            bad_target = failing_targets[0]
            supporting = [
                Evidence(
                    metric_type=MetricType.EXTERNAL_PACKET_LOSS,
                    target=bad_target,
                    observed_value=1.0,
                    threshold_value=self.thresholds.external_packet_loss_critical,
                    condition="target_packet_loss_high",
                    weight=1.5,
                )
            ]
            contradictory = [
                Evidence(
                    metric_type=MetricType.EXTERNAL_PACKET_LOSS,
                    target="other_destinations",
                    observed_value=0.0,
                    threshold_value=self.thresholds.external_packet_loss_critical,
                    condition=f"{len(healthy_targets)} other external targets are 100% reachable",
                    weight=1.2,
                )
            ]
            return Diagnosis(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                probable_cause=ProbableCause.DESTINATION_SPECIFIC_OUTAGE,
                confidence=0.90,
                severity=DiagnosisSeverity.LOW,
                supporting_evidence=supporting,
                contradictory_evidence=contradictory,
                recommended_actions=["check_remote_endpoint_status"],
                auto_remediation_permitted=False,
                explanation=f"Target {bad_target} is failing, but all other destinations are healthy. Problem is isolated to remote server or routing to that specific destination.",
            )

        return None
