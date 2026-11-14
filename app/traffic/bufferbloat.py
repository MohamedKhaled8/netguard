"""Bufferbloat and Queueing Delay Evaluation Subsystem."""

from __future__ import annotations
import asyncio
from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from app.platform.interfaces import IPlatformAdapter
from app.core.events.bus import EventBus


class BufferbloatGrade(str, Enum):
    A_PLUS = "A+"  # Delta <= 5ms
    A = "A"        # Delta <= 15ms
    B = "B"        # Delta <= 30ms
    C = "C"        # Delta <= 60ms
    D = "D"        # Delta <= 150ms
    F = "F"        # Delta > 150ms


class BufferbloatReport(BaseModel):
    """Detailed queue delay and bufferbloat assessment."""
    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    target: str
    idle_latency_ms: float
    loaded_latency_ms: float
    queue_delay_delta_ms: float
    bloat_factor: float
    grade: BufferbloatGrade
    is_congested: bool
    explanation: str


class BufferbloatEvaluator:
    """Measures queue delay delta under traffic load vs idle baseline."""

    def __init__(self, platform: IPlatformAdapter, event_bus: EventBus) -> None:
        self.platform = platform
        self.event_bus = event_bus

    @staticmethod
    def calculate_grade(delta_ms: float) -> BufferbloatGrade:
        if delta_ms <= 5.0:
            return BufferbloatGrade.A_PLUS
        elif delta_ms <= 15.0:
            return BufferbloatGrade.A
        elif delta_ms <= 30.0:
            return BufferbloatGrade.B
        elif delta_ms <= 60.0:
            return BufferbloatGrade.C
        elif delta_ms <= 150.0:
            return BufferbloatGrade.D
        return BufferbloatGrade.F

    async def evaluate_latency_delta(
        self,
        idle_latency_ms: float,
        loaded_latency_ms: float,
        target: str = "1.1.1.1",
    ) -> BufferbloatReport:
        """Evaluate bufferbloat given idle baseline and loaded latency."""
        delta = max(0.0, loaded_latency_ms - idle_latency_ms)
        bloat_factor = (loaded_latency_ms / idle_latency_ms) if idle_latency_ms > 0 else 1.0
        grade = self.calculate_grade(delta)
        is_congested = delta > 60.0 or bloat_factor > 3.0

        explanation = (
            f"Idle latency: {idle_latency_ms:.1f}ms, Loaded: {loaded_latency_ms:.1f}ms. "
            f"Bufferbloat queue delay delta: +{delta:.1f}ms (Grade {grade.value})."
        )

        report = BufferbloatReport(
            target=target,
            idle_latency_ms=idle_latency_ms,
            loaded_latency_ms=loaded_latency_ms,
            queue_delay_delta_ms=delta,
            bloat_factor=bloat_factor,
            grade=grade,
            is_congested=is_congested,
            explanation=explanation,
        )

        await self.event_bus.publish("bufferbloat.report", report.model_dump(mode="json"))
        return report
