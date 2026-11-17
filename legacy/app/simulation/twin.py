"""Network Digital Twin for Pre-Execution Policy Simulation."""

from __future__ import annotations
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class SimulationResult(BaseModel):
    """Simulated projection of applying a proposed network action."""
    model_config = ConfigDict(frozen=True)

    is_simulated: bool = True
    action_id: str
    target_metric: str
    projected_baseline: float
    projected_post_action: float
    projected_improvement_pct: float
    risk_of_side_effects: str  # LOW, MEDIUM, HIGH
    confidence: float
    label: str = "SIMULATED_PROJECTION_DO_NOT_TREAT_AS_MEASUREMENT"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NetworkDigitalTwin:
    """Simulates hypothetical policy impacts before physical execution."""

    @staticmethod
    def simulate_dns_switch(
        current_mean_dns_latency: float,
        candidate_resolver_latency: float,
    ) -> SimulationResult:
        """Simulate impact of switching DNS resolvers."""
        delta = current_mean_dns_latency - candidate_resolver_latency
        imp_pct = (delta / current_mean_dns_latency * 100.0) if current_mean_dns_latency > 0 else 0.0

        return SimulationResult(
            action_id="switch_dns_resolver",
            target_metric="dns_latency_ms",
            projected_baseline=current_mean_dns_latency,
            projected_post_action=candidate_resolver_latency,
            projected_improvement_pct=max(0.0, imp_pct),
            risk_of_side_effects="LOW",
            confidence=0.90,
        )

    @staticmethod
    def simulate_background_throttling(
        current_loaded_latency_ms: float,
        estimated_idle_latency_ms: float,
        throttled_bandwidth_ratio: float = 0.5,
    ) -> SimulationResult:
        """Simulate queue delay reduction when throttling aggressive background downloads."""
        queue_delay = max(0.0, current_loaded_latency_ms - estimated_idle_latency_ms)
        projected_reduction = queue_delay * throttled_bandwidth_ratio
        projected_post = estimated_idle_latency_ms + (queue_delay - projected_reduction)
        imp_pct = (projected_reduction / current_loaded_latency_ms * 100.0) if current_loaded_latency_ms > 0 else 0.0

        return SimulationResult(
            action_id="throttle_background_bandwidth",
            target_metric="bufferbloat_queue_delay_ms",
            projected_baseline=current_loaded_latency_ms,
            projected_post_action=projected_post,
            projected_improvement_pct=max(0.0, imp_pct),
            risk_of_side_effects="LOW",
            confidence=0.85,
        )
