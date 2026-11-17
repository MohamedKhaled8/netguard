"""Dynamic Baselines Manager computing statistical normal ranges across metric streams."""

from __future__ import annotations
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from app.core.models.metrics import MetricType


class MetricBaseline(BaseModel):
    """Statistical baseline distribution for a specific metric."""
    model_config = ConfigDict(frozen=True)

    metric_type: MetricType
    sample_count: int
    mean: float
    std_dev: float
    median: float
    iqr: float
    q25: float
    q75: float
    upper_threshold_zscore_3: float
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BaselineManager:
    """Computes and maintains historical dynamic baselines."""

    def __init__(self, min_samples: int = 15) -> None:
        self.min_samples = min_samples
        self._baselines: Dict[MetricType, MetricBaseline] = {}

    def update_baseline(self, metric_type: MetricType, values: List[float]) -> Optional[MetricBaseline]:
        """Update metric baseline distribution from a sequence of raw observations."""
        if len(values) < self.min_samples:
            return None

        arr = np.array(values, dtype=float)
        mean_val = float(np.mean(arr))
        std_val = float(np.std(arr))
        median_val = float(np.median(arr))
        q25 = float(np.percentile(arr, 25))
        q75 = float(np.percentile(arr, 75))
        iqr = max(q75 - q25, 0.001)

        baseline = MetricBaseline(
            metric_type=metric_type,
            sample_count=len(values),
            mean=mean_val,
            std_dev=std_val,
            median=median_val,
            iqr=iqr,
            q25=q25,
            q75=q75,
            upper_threshold_zscore_3=mean_val + (3.0 * std_val),
            updated_at=datetime.now(timezone.utc),
        )
        self._baselines[metric_type] = baseline
        return baseline

    def get_baseline(self, metric_type: MetricType) -> Optional[MetricBaseline]:
        return self._baselines.get(metric_type)
