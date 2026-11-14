"""Base Diagnostic Classifier defining rule evaluation and confidence scoring."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from app.core.config.models import DiagnosisThresholds
from app.core.models.metrics import Diagnosis, MetricType, Measurement
from app.diagnosis.evidence import EvidenceSummary


class BaseClassifier(ABC):
    """Abstract diagnostic classifier."""

    def __init__(self, thresholds: DiagnosisThresholds) -> None:
        self.thresholds = thresholds

    @abstractmethod
    def evaluate(self, summaries: Dict[MetricType, EvidenceSummary]) -> Optional[Diagnosis]:
        """Evaluate evidence summaries across all metrics and return a Diagnosis if an anomaly matches."""
        pass
