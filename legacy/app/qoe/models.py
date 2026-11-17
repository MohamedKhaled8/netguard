"""Quality of Experience (QoE) Domain Models."""

from __future__ import annotations
from typing import Dict, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class QoECategoryScore(BaseModel):
    """QoE score for a specific application category."""
    model_config = ConfigDict(frozen=True)

    score: float = Field(ge=0.0, le=100.0)
    rating: str  # Excellent (90-100), Good (75-89), Fair (50-74), Poor (<50)
    primary_limiting_factor: str


class QoEAssessment(BaseModel):
    """Transparent Quality of Experience scorecard across multiple user workloads."""
    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    overall_score: float = Field(ge=0.0, le=100.0)
    overall_rating: str
    conferencing: QoECategoryScore
    gaming: QoECategoryScore
    streaming: QoECategoryScore
    browsing: QoECategoryScore
    downloads: QoECategoryScore
    bottlenecks: List[str] = Field(default_factory=list)
    measured_inputs: Dict[str, float] = Field(default_factory=dict)
