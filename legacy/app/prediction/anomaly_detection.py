"""Statistical Anomaly and Trend Change-Point Detector."""

from __future__ import annotations
import numpy as np
from typing import Dict, List, Optional, Tuple
from app.core.models.metrics import MetricType
from app.prediction.baselines import BaselineManager, MetricBaseline


class TrendAnalysis:
    """Calculates linear drift rate (slope) and volatility over time."""

    @staticmethod
    def calculate_slope(values: List[float]) -> float:
        """Computes rate of change per sample (slope m in y = mx + c)."""
        if len(values) < 3:
            return 0.0
        n = len(values)
        x = np.arange(n)
        y = np.array(values)
        # Linear regression slope: cov(x, y) / var(x)
        slope, _ = np.polyfit(x, y, 1)
        return float(slope)


class AnomalyDetector:
    """Evaluates telemetry values against historical baselines and trend slopes."""

    def __init__(self, baseline_manager: BaselineManager) -> None:
        self.baselines = baseline_manager

    def evaluate_anomaly(self, metric_type: MetricType, recent_values: List[float]) -> Tuple[bool, float, str]:
        """Returns (is_anomaly, anomaly_score, explanation)."""
        if not recent_values:
            return False, 0.0, "No data"

        current_val = recent_values[-1]
        baseline = self.baselines.get_baseline(metric_type)

        # 1. Slope / Trend check
        slope = TrendAnalysis.calculate_slope(recent_values[-10:])

        if not baseline:
            # Cold start without baseline: check pure slope velocity
            if slope > 5.0:
                return True, 0.75, f"Rapid upward trend detected (slope: +{slope:.2f} per tick)"
            return False, 0.0, "Normal (insufficient baseline)"

        # 2. Z-Score analysis against baseline
        if baseline.std_dev > 0.001:
            z_score = (current_val - baseline.mean) / baseline.std_dev
        else:
            z_score = 0.0

        # Outlier fence via IQR
        is_iqr_outlier = current_val > (baseline.q75 + 2.0 * baseline.iqr)

        if z_score >= 3.0 or is_iqr_outlier:
            return (
                True,
                min(0.95, 0.70 + (z_score / 10.0)),
                f"Statistical anomaly: current {current_val:.1f} vs baseline mean {baseline.mean:.1f} (z-score: {z_score:.2f})",
            )

        if slope > 2.5 and z_score > 1.5:
            return (
                True,
                0.80,
                f"Progressive degradation: slope +{slope:.2f}/tick with z-score {z_score:.2f}",
            )

        return False, 0.0, "Within expected statistical distribution"
