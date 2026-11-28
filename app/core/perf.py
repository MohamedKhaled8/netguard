"""Lightweight performance and concurrency instrumentation for NetGuard AI."""

from __future__ import annotations

from collections import deque
from contextlib import contextmanager
import threading
import time
from typing import Any, Deque, Dict, Iterator, List, Optional


class PerfMetricsCollector:
    """Thread-safe collector for UI responsiveness, scan latency, and worker concurrency."""

    _instance: Optional["PerfMetricsCollector"] = None
    _inst_lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._timings: Dict[str, Deque[float]] = {}
        self._counters: Dict[str, int] = {}
        self._active_workers: int = 0
        self._peak_workers: int = 0
        self._ui_stalls_ms: Deque[float] = deque(maxlen=120)
        self._startup_breakdown_ms: Dict[str, float] = {}
        self._nav_switches_ms: Dict[int, Deque[float]] = {}

    @classmethod
    def get_instance(cls) -> "PerfMetricsCollector":
        if cls._instance is None:
            with cls._inst_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def record_startup_phase(self, phase: str, duration_ms: float) -> None:
        with self._lock:
            self._startup_breakdown_ms[phase] = round(max(0.0, float(duration_ms)), 2)

    def record_nav_switch(self, tab_index: int, duration_ms: float) -> None:
        with self._lock:
            dq = self._nav_switches_ms.setdefault(int(tab_index), deque(maxlen=30))
            dq.append(round(max(0.0, float(duration_ms)), 2))

    def record_timing(self, metric: str, duration_ms: float) -> None:
        with self._lock:
            dq = self._timings.setdefault(metric, deque(maxlen=60))
            dq.append(round(max(0.0, float(duration_ms)), 2))

    def increment_counter(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + int(amount)

    def record_ui_stall(self, delta_ms: float) -> None:
        with self._lock:
            self._ui_stalls_ms.append(round(float(delta_ms), 2))

    def worker_started(self) -> int:
        with self._lock:
            self._active_workers += 1
            if self._active_workers > self._peak_workers:
                self._peak_workers = self._active_workers
            self._counters["workers_started"] = self._counters.get("workers_started", 0) + 1
            return self._active_workers

    def worker_finished(self) -> int:
        with self._lock:
            self._active_workers = max(0, self._active_workers - 1)
            return self._active_workers

    @contextmanager
    def measure(self, metric: str) -> Iterator[None]:
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self.record_timing(metric, (time.perf_counter() - t0) * 1000.0)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            timing_summary: Dict[str, Dict[str, Any]] = {}
            for k, dq in self._timings.items():
                vals = list(dq)
                if vals:
                    timing_summary[k] = {
                        "count": len(vals),
                        "last_ms": vals[-1],
                        "avg_ms": round(sum(vals) / len(vals), 2),
                        "max_ms": max(vals),
                    }
            nav_summary: Dict[int, List[float]] = {k: list(v) for k, v in self._nav_switches_ms.items()}
            stalls = list(self._ui_stalls_ms)
            return {
                "startup_ms": dict(self._startup_breakdown_ms),
                "nav_ms": nav_summary,
                "timings": timing_summary,
                "counters": dict(self._counters),
                "active_workers": self._active_workers,
                "peak_workers": self._peak_workers,
                "ui_stalls_over_threshold_ms": stalls,
                "max_ui_stall_ms": max(stalls) if stalls else 0.0,
            }

    def reset(self) -> None:
        with self._lock:
            self._timings.clear()
            self._counters.clear()
            self._ui_stalls_ms.clear()
            self._nav_switches_ms.clear()
            self._active_workers = 0
            self._peak_workers = 0
