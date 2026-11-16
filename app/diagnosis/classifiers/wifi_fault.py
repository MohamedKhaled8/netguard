"""Wi-Fi Signal and Physical Link Instability Classifier."""

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


class WifiInstabilityClassifier(BaseClassifier):
    """Diagnoses physical Wi-Fi signal attenuation and poor wireless link rates."""

    def evaluate(self, summaries: Dict[MetricType, EvidenceSummary]) -> Optional[Diagnosis]:
        wifi_sig = summaries.get(MetricType.WIFI_SIGNAL_PERCENT)
        gw_lat = summaries.get(MetricType.GATEWAY_LATENCY)
        gw_loss = summaries.get(MetricType.GATEWAY_PACKET_LOSS)

        if not wifi_sig or wifi_sig.count == 0:
            return None

        # Critical Wi-Fi threshold: signal < critical percent
        wifi_crit = getattr(getattr(self.thresholds, "wifi", None), "signal_critical_pct", 25.0)
        if wifi_sig.latest_value < wifi_crit:
            supporting = [
                Evidence(
                    metric_type=MetricType.WIFI_SIGNAL_PERCENT,
                    target="wifi_link",
                    observed_value=wifi_sig.latest_value,
                    threshold_value=wifi_crit,
                    condition=f"wifi_signal < {wifi_crit}%",
                    weight=1.5,
                )
            ]
            if gw_lat and gw_lat.mean > self.thresholds.gateway_latency_warning_ms:
                supporting.append(
                    Evidence(
                        metric_type=MetricType.GATEWAY_LATENCY,
                        target="gateway",
                        observed_value=gw_lat.mean,
                        threshold_value=self.thresholds.gateway_latency_warning_ms,
                        condition="correlated_gateway_latency_spike",
                        weight=1.2,
                    )
                )

            return Diagnosis(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                probable_cause=ProbableCause.WI_FI_SIGNAL_DEGRADED,
                confidence=0.88,
                severity=DiagnosisSeverity.HIGH,
                supporting_evidence=supporting,
                contradictory_evidence=[],
                recommended_actions=["move_closer_to_router", "switch_to_ethernet", "change_wifi_band"],
                auto_remediation_permitted=False,
                explanation=f"Wi-Fi signal strength is critically degraded ({wifi_sig.latest_value:.0f}%), causing local frame drops and high latency.",
            )

        return None
