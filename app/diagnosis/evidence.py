"""Evidence Accumulator for Statistical Telemetry Aggregation."""

from __future__ import annotations
import statistics
from typing import Dict, List, Optional
from datetime import datetime, timezone
from app.core.models.metrics import Measurement, MetricType, ProbeStatus, Evidence


class EvidenceSummary:
    """Statistical summary of a telemetry stream window."""

    def __init__(self, metric_type: MetricType, samples: List[Measurement]) -> None:
        self.metric_type = metric_type
        self.count = len(samples)
        self.samples = samples

        valid_values = [s.raw_value for s in samples if s.status in (ProbeStatus.SUCCESS, ProbeStatus.DEGRADED)]
        self.valid_count = len(valid_values)
        self.mean = statistics.mean(valid_values) if valid_values else 0.0
        self.median = statistics.median(valid_values) if valid_values else 0.0
        self.min = min(valid_values) if valid_values else 0.0
        self.max = max(valid_values) if valid_values else 0.0
        self.stdev = statistics.stdev(valid_values) if len(valid_values) >= 2 else 0.0

        # Failure & Loss statistics
        failed_count = sum(1 for s in samples if s.status in (ProbeStatus.FAILED, ProbeStatus.TIMEOUT, ProbeStatus.UNREACHABLE))
        self.failure_ratio = (failed_count / self.count) if self.count > 0 else 0.0
        self.latest_status = samples[-1].status if samples else ProbeStatus.UNAVAILABLE
        self.latest_value = samples[-1].raw_value if samples else 0.0


class EvidenceAccumulator:
    """Transforms raw measurement queues into structured statistical evidence."""

    @staticmethod
    def summarize_window(samples: List[Measurement]) -> Optional[EvidenceSummary]:
        if not samples:
            return None
        return EvidenceSummary(metric_type=samples[-1].metric_type, samples=samples)
