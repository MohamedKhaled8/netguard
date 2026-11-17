"""Case-Based Network Memory and Historical Intelligence."""

from __future__ import annotations
import math
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from app.core.models.metrics import ProbableCause, ActionExecutionRecord

logger = logging.getLogger("netguard.learning.memory")


class IncidentResolutionCase(BaseModel):
    """Case record capturing an incident, applied remedy, and verification outcome."""
    model_config = ConfigDict(frozen=True)

    case_id: str
    probable_cause: ProbableCause
    feature_vector: Dict[str, float]  # normalized metrics: latency, loss, jitter, etc.
    action_id: str
    was_successful: bool
    improvement_delta_ms: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NetworkMemory:
    """Historical case base for learning effective remediation actions from experience."""

    def __init__(self) -> None:
        self._cases: List[IncidentResolutionCase] = []

    def record_case(
        self,
        case_id: str,
        probable_cause: ProbableCause,
        feature_vector: Dict[str, float],
        action_id: str,
        was_successful: bool,
        improvement_delta_ms: float,
    ) -> None:
        case = IncidentResolutionCase(
            case_id=case_id,
            probable_cause=probable_cause,
            feature_vector=feature_vector,
            action_id=action_id,
            was_successful=was_successful,
            improvement_delta_ms=improvement_delta_ms,
        )
        self._cases.append(case)
        logger.info(
            "Recorded historical resolution case %s: %s -> %s (success=%s)",
            case_id,
            probable_cause.value,
            action_id,
            was_successful,
        )

    def find_best_action_for_context(
        self,
        probable_cause: ProbableCause,
        current_features: Dict[str, float],
    ) -> Optional[Tuple[str, float]]:
        """Finds most successful action for matching contextual incidents. Returns (action_id, confidence)."""
        matching_cases = [c for c in self._cases if c.probable_cause == probable_cause]
        if not matching_cases:
            return None

        action_scores: Dict[str, List[float]] = {}
        for case in matching_cases:
            # Normalized relative distance across features
            dist_sq = 0.0
            for k, val in current_features.items():
                case_val = case.feature_vector.get(k, val)
                norm_denom = max(abs(val), abs(case_val), 1.0)
                rel_diff = abs(val - case_val) / norm_denom
                dist_sq += rel_diff ** 2
            similarity = 1.0 / (1.0 + math.sqrt(dist_sq))

            weight = similarity if case.was_successful else -similarity * 1.5
            action_scores.setdefault(case.action_id, []).append(weight)

        best_action = None
        best_score = -999.0
        for act, weights in action_scores.items():
            mean_score = sum(weights) / len(weights)
            if mean_score > best_score:
                best_score = mean_score
                best_action = act

        if best_action and best_score > 0:
            confidence = min(0.98, 0.50 + (best_score * 0.50))
            return best_action, confidence
        return None
