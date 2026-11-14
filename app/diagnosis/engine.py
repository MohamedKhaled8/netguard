"""Root Cause Diagnosis Engine coordinating multi-vector evidence classifiers."""

from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid
from app.core.config.models import DiagnosisThresholds
from app.core.events.bus import EventBus
from app.core.models.metrics import (
    Diagnosis,
    ProbableCause,
    DiagnosisSeverity,
    MetricType,
    Measurement,
)
from app.diagnosis.evidence import EvidenceAccumulator, EvidenceSummary
from app.diagnosis.classifiers.base import BaseClassifier
from app.diagnosis.classifiers.gateway_fault import GatewayHealthClassifier
from app.diagnosis.classifiers.dns_fault import DNSHealthClassifier
from app.diagnosis.classifiers.upstream_isp_fault import UpstreamISPClassifier
from app.diagnosis.classifiers.destination_fault import DestinationSpecificClassifier
from app.diagnosis.classifiers.wifi_fault import WifiInstabilityClassifier
from app.storage.repositories.incident_repo import IncidentRepository

logger = logging.getLogger("netguard.diagnosis.engine")


class DiagnosisEngine:
    """Consumes telemetry streams, calculates differential evidence, and identifies probable causes."""

    def __init__(
        self,
        thresholds: DiagnosisThresholds,
        event_bus: EventBus,
        incident_repo: IncidentRepository,
    ) -> None:
        self.thresholds = thresholds
        self.event_bus = event_bus
        self.repo = incident_repo
        self.classifiers: List[BaseClassifier] = [
            GatewayHealthClassifier(thresholds),
            DNSHealthClassifier(thresholds),
            UpstreamISPClassifier(thresholds),
            DestinationSpecificClassifier(thresholds),
            WifiInstabilityClassifier(thresholds),
        ]
        self._last_diagnosis: Optional[Diagnosis] = None

    def register_classifier(self, classifier: BaseClassifier) -> None:
        """Allow registering additional or experimental classifiers."""
        self.classifiers.append(classifier)

    async def evaluate_windows(self, windows: Dict[MetricType, List[Measurement]]) -> Diagnosis:
        """Evaluate sliding window measurements across all metrics."""
        # 1. Summarize evidence
        summaries: Dict[MetricType, EvidenceSummary] = {}
        for metric, samples in windows.items():
            summary = EvidenceAccumulator.summarize_window(samples)
            if summary:
                summaries[metric] = summary

        # 2. Evaluate all classifiers
        candidate_diagnoses: List[Diagnosis] = []
        for classifier in self.classifiers:
            try:
                diag = classifier.evaluate(summaries)
                if diag:
                    candidate_diagnoses.append(diag)
            except Exception as exc:
                logger.error("Error running classifier %s: %s", classifier.__class__.__name__, exc, exc_info=True)

        # 3. Select most critical and confident diagnosis
        if candidate_diagnoses:
            # Sort by severity weight and confidence
            severity_order = {
                DiagnosisSeverity.CRITICAL: 4,
                DiagnosisSeverity.HIGH: 3,
                DiagnosisSeverity.MEDIUM: 2,
                DiagnosisSeverity.LOW: 1,
                DiagnosisSeverity.INFO: 0,
            }
            candidate_diagnoses.sort(
                key=lambda d: (severity_order.get(d.severity, 0), d.confidence),
                reverse=True,
            )
            selected = candidate_diagnoses[0]
        else:
            selected = Diagnosis(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                probable_cause=ProbableCause.HEALTHY,
                confidence=1.0,
                severity=DiagnosisSeverity.INFO,
                supporting_evidence=[],
                contradictory_evidence=[],
                recommended_actions=[],
                auto_remediation_permitted=False,
                explanation="All network indicators are within normal operating bounds.",
            )

        self._last_diagnosis = selected

        # 4. If non-healthy, persist to incident store and broadcast event
        if selected.probable_cause != ProbableCause.HEALTHY:
            loop = asyncio.get_running_loop()
            try:
                await loop.run_in_executor(None, self.repo.save, selected)
            except Exception as exc:
                logger.warning("Failed to persist incident: %s", exc)

            await self.event_bus.publish(f"diagnosis.{selected.probable_cause.value}", selected)
            await self.event_bus.publish("diagnosis.incident", selected)

        return selected

    @property
    def last_diagnosis(self) -> Optional[Diagnosis]:
        return self._last_diagnosis
