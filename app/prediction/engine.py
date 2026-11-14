"""Predictive Failure Detection Engine forecasting network degradation."""

from __future__ import annotations
import uuid
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

from app.core.events.bus import EventBus
from app.core.models.metrics import MetricType, Measurement, DiagnosisSeverity
from app.prediction.baselines import BaselineManager
from app.prediction.anomaly_detection import AnomalyDetector

logger = logging.getLogger("netguard.prediction.engine")


class PredictionWarning(BaseModel):
    """Early failure prediction warning."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    predicted_failure_type: str
    target: str
    confidence: float
    severity: DiagnosisSeverity
    horizon_sec: float
    evidence: str
    suggested_action: str


class PredictionEngine:
    """Monitors telemetry trends, updates dynamic baselines, and produces early warnings."""

    def __init__(self, event_bus: EventBus, min_samples_for_baseline: int = 15) -> None:
        self.event_bus = event_bus
        self.baselines = BaselineManager(min_samples=min_samples_for_baseline)
        self.detector = AnomalyDetector(self.baselines)
        self._recent_predictions: List[PredictionWarning] = []

    async def evaluate_streams(self, windows: Dict[MetricType, List[Measurement]]) -> List[PredictionWarning]:
        warnings: List[PredictionWarning] = []

        # Update baselines and evaluate key predictive indicators
        predictive_metrics = [
            (MetricType.GATEWAY_LATENCY, "gateway_latency_spike", "inspect_local_link", 15.0),
            (MetricType.EXTERNAL_LATENCY, "upstream_congestion_spike", "prepare_traffic_shaping", 30.0),
            (MetricType.JITTER_MS, "connection_instability", "inspect_wifi_or_cellular", 20.0),
            (MetricType.DNS_LATENCY, "dns_resolver_degradation", "prepare_dns_failover", 45.0),
        ]

        for metric_type, failure_type, suggested_action, horizon in predictive_metrics:
            samples = windows.get(metric_type, [])
            if not samples:
                continue

            raw_values = [s.raw_value for s in samples]
            # Maintain dynamic baseline
            self.baselines.update_baseline(metric_type, raw_values)

            # Detect trend anomaly
            is_anomaly, score, reason = self.detector.evaluate_anomaly(metric_type, raw_values)
            if is_anomaly and score >= 0.70:
                target_str = samples[-1].target_or_interface
                warning = PredictionWarning(
                    predicted_failure_type=failure_type,
                    target=target_str,
                    confidence=score,
                    severity=DiagnosisSeverity.MEDIUM if score < 0.85 else DiagnosisSeverity.HIGH,
                    horizon_sec=horizon,
                    evidence=reason,
                    suggested_action=suggested_action,
                )
                warnings.append(warning)
                self._recent_predictions.append(warning)
                if len(self._recent_predictions) > 50:
                    self._recent_predictions.pop(0)

                await self.event_bus.publish(f"prediction.warning.{failure_type}", warning)
                await self.event_bus.publish("prediction.warning", warning)
                logger.info("Prediction warning: %s on %s (confidence: %.2f)", failure_type, target_str, score)

        return warnings

    @property
    def recent_warnings(self) -> List[PredictionWarning]:
        return list(self._recent_predictions)
