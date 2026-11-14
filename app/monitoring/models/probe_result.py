"""Probe execution result models."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.core.models.metrics import MetricType, ProbeStatus, MeasurementSource, Measurement


class ProbeResult(BaseModel):
    """Encapsulates the raw and normalized outcome of a probe run."""
    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: MeasurementSource
    target: str
    metric_type: MetricType
    raw_value: float
    normalized_value: float
    unit: str
    status: ProbeStatus
    confidence: float = 1.0
    latency_ms: Optional[float] = None
    packet_loss_ratio: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_measurement(self) -> Measurement:
        """Convert probe outcome to standard stored telemetry Measurement."""
        return Measurement(
            timestamp=self.timestamp,
            source=self.source,
            target_or_interface=self.target,
            metric_type=self.metric_type,
            raw_value=self.raw_value,
            normalized_value=self.normalized_value,
            unit=self.unit,
            status=self.status,
            confidence=self.confidence,
            metadata=self.metadata,
        )
