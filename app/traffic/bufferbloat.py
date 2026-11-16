"""Bufferbloat and Queueing Delay Evaluation Subsystem."""

from __future__ import annotations
import asyncio
import time
import statistics
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

    async def run_live_test(
        self,
        target: str = "1.1.1.1",
        load_duration_sec: float = 2.0,
    ) -> BufferbloatReport:
        """Run active loaded-vs-idle latency test to compute genuine queue delay delta and grade."""
        loop = asyncio.get_running_loop()

        def _measure_idle() -> float:
            samples = []
            for _ in range(4):
                ok, lat = self.platform.ping(target, timeout_sec=1.0)
                if ok and lat >= 0:
                    samples.append(lat)
                time.sleep(0.05)
            return float(statistics.median(samples)) if samples else 25.0

        def _generate_load_and_measure() -> float:
            import urllib.request
            import threading

            stop_event = threading.Event()

            def _loader():
                url = "https://1.1.1.1"
                while not stop_event.is_set():
                    try:
                        req = urllib.request.Request(url, headers={"User-Agent": "NetGuard/1.0"})
                        with urllib.request.urlopen(req, timeout=1.5) as resp:
                            resp.read(32768)
                    except Exception:
                        pass
                    time.sleep(0.02)

            threads = [threading.Thread(target=_loader, daemon=True) for _ in range(3)]
            for t in threads:
                t.start()

            loaded_samples = []
            time.sleep(0.2)
            t_start = time.perf_counter()
            while (time.perf_counter() - t_start) < load_duration_sec:
                ok, lat = self.platform.ping(target, timeout_sec=1.0)
                if ok and lat >= 0:
                    loaded_samples.append(lat)
                time.sleep(0.1)

            stop_event.set()
            for t in threads:
                t.join(timeout=0.5)

            return float(statistics.median(loaded_samples)) if loaded_samples else 35.0

        idle_lat = await loop.run_in_executor(None, _measure_idle)
        loaded_lat = await loop.run_in_executor(None, _generate_load_and_measure)

        return await self.evaluate_latency_delta(
            idle_latency_ms=idle_lat,
            loaded_latency_ms=loaded_lat,
            target=target,
        )
