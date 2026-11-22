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
    IncidentLifecycleState,
    IncidentResolutionType,
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
        self._current_active_incident_id: Optional[str] = None

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
            # Never report HEALTHY when required measurements are missing or inconclusive
            has_gw = MetricType.GATEWAY_LATENCY in summaries
            has_ext = MetricType.EXTERNAL_LATENCY in summaries
            if not (has_gw and has_ext):
                selected = Diagnosis(
                    id=str(uuid.uuid4()),
                    timestamp=datetime.now(timezone.utc),
                    probable_cause=ProbableCause.UNKNOWN_ANOMALY,
                    confidence=0.5,
                    severity=DiagnosisSeverity.INFO,
                    supporting_evidence=[],
                    contradictory_evidence=[],
                    recommended_actions=[],
                    auto_remediation_permitted=False,
                    explanation="جاري جمع مؤشرات الشبكة والتحقق من استجابة الراوتر وخوادم الإنترنت...",
                )
            else:
                # Evidence-based checks before claiming HEALTHY
                ext_loss = summaries.get(MetricType.EXTERNAL_PACKET_LOSS)
                gw_loss = summaries.get(MetricType.GATEWAY_PACKET_LOSS)
                jit = summaries.get(MetricType.JITTER_MS)
                ext_lat = summaries.get(MetricType.EXTERNAL_LATENCY)
                gw_lat = summaries.get(MetricType.GATEWAY_LATENCY)

                # Check 1: Packet loss in window
                has_loss = (ext_loss and ext_loss.latest_value and ext_loss.latest_value > 0.02) or (gw_loss and gw_loss.latest_value and gw_loss.latest_value > 0.05)
                # Check 2: High jitter in window
                has_high_jitter = (jit and jit.mean and jit.mean >= 20.0)
                # Check 3: Elevated external latency (warning range)
                has_elevated_ext = (ext_lat and ext_lat.mean and ext_lat.mean >= self.thresholds.external_latency_warning_ms)
                # Check 4: Elevated gateway latency (warning range)
                has_elevated_gw = (gw_lat and gw_lat.mean and gw_lat.mean >= self.thresholds.gateway_latency_warning_ms)

                if has_loss:
                    loss_pct = (ext_loss.latest_value * 100.0) if ext_loss and ext_loss.latest_value else 5.0
                    selected = Diagnosis(
                        id=str(uuid.uuid4()),
                        timestamp=datetime.now(timezone.utc),
                        probable_cause=ProbableCause.ISP_UPSTREAM_HIGH_LATENCY,
                        confidence=0.85,
                        severity=DiagnosisSeverity.MEDIUM,
                        supporting_evidence=[],
                        contradictory_evidence=[],
                        recommended_actions=["inspect_bufferbloat"],
                        auto_remediation_permitted=False,
                        explanation=f"تم رصد فقدان في حزم البيانات بنسبة {loss_pct:.1f}%. يوجد تذبذب في استقرار المسار الخارجي لمزود الخدمة.",
                    )
                elif has_high_jitter:
                    selected = Diagnosis(
                        id=str(uuid.uuid4()),
                        timestamp=datetime.now(timezone.utc),
                        probable_cause=ProbableCause.UNKNOWN_ANOMALY,
                        confidence=0.80,
                        severity=DiagnosisSeverity.LOW,
                        supporting_evidence=[],
                        contradictory_evidence=[],
                        recommended_actions=["inspect_bufferbloat"],
                        auto_remediation_permitted=False,
                        explanation=f"رصد تذبذب مرتفع في زمن وصول الحزم (Jitter: {jit.mean:.1f} ms). قد تتأثر المكالمات وتطبيقات البث المباشر.",
                    )
                elif has_elevated_ext:
                    selected = Diagnosis(
                        id=str(uuid.uuid4()),
                        timestamp=datetime.now(timezone.utc),
                        probable_cause=ProbableCause.ISP_UPSTREAM_HIGH_LATENCY,
                        confidence=0.82,
                        severity=DiagnosisSeverity.LOW,
                        supporting_evidence=[],
                        contradictory_evidence=[],
                        recommended_actions=["inspect_bufferbloat"],
                        auto_remediation_permitted=False,
                        explanation=f"ارتفاع زمن الاستجابة الخارجي ({ext_lat.mean:.1f} ms) متجاوزاً المعدل المعتاد ({self.thresholds.external_latency_warning_ms:.0f} ms). تباطؤ في مسار المزود.",
                    )
                elif has_elevated_gw:
                    selected = Diagnosis(
                        id=str(uuid.uuid4()),
                        timestamp=datetime.now(timezone.utc),
                        probable_cause=ProbableCause.LOCAL_GATEWAY_HIGH_LATENCY,
                        confidence=0.85,
                        severity=DiagnosisSeverity.LOW,
                        supporting_evidence=[],
                        contradictory_evidence=[],
                        recommended_actions=["recheck_gateway"],
                        auto_remediation_permitted=True,
                        explanation=f"ارتفاع زمن استجابة الراوتر المنزلي ({gw_lat.mean:.1f} ms). تحقق من الضغط المحلي أو كابل الشبكة.",
                    )
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
                        explanation="كافة مؤشرات الشبكة والراوتر وخوادم الإنترنت تعمل ضمن المعدلات الطبيعية الممتازة.",
                    )

        self._last_diagnosis = selected

        # 4. If non-healthy, persist to incident store via deduplication and broadcast event
        loop = asyncio.get_running_loop()
        if selected.probable_cause != ProbableCause.HEALTHY:
            try:
                inc_id, is_new = await loop.run_in_executor(None, self.repo.save_or_update, selected)
                selected.id = inc_id
                self._current_active_incident_id = inc_id
            except Exception as exc:
                logger.warning("Failed to persist incident: %s", exc)

            await self.event_bus.publish(f"diagnosis.{selected.probable_cause.value}", selected)
            await self.event_bus.publish("diagnosis.incident", selected)
        else:
            # Automatic transition to NATURALLY_RECOVERED when indicators return to normal
            active_id = getattr(self, "_current_active_incident_id", None)
            if active_id:
                try:
                    await loop.run_in_executor(
                        None,
                        self.repo.transition_state,
                        active_id,
                        IncidentLifecycleState.NATURALLY_RECOVERED,
                        IncidentResolutionType.NATURALLY_RECOVERED,
                        None,
                        "استعادت الشبكة استقرارها التلقائي وعادت جميع المؤشرات للمعدلات الطبيعية.",
                    )
                    self._current_active_incident_id = None
                except Exception as exc:
                    logger.debug("Failed to transition recovered incident: %s", exc)

        return selected

    @property
    def last_diagnosis(self) -> Optional[Diagnosis]:
        return self._last_diagnosis
