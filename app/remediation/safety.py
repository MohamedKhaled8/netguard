"""Safety mechanisms: Circuit Breakers, Action Locks, and Cooldowns."""

from __future__ import annotations
import asyncio
import time
import logging
from typing import Dict, Optional
from app.core.exceptions.base import CircuitBreakerOpenError

logger = logging.getLogger("netguard.remediation.safety")


class CircuitBreaker:
    """State machine preventing catastrophic retry loops for an action.
    States: CLOSED (normal), OPEN (tripped/blocked), HALF_OPEN (probing single recovery).
    """

    def __init__(self, failure_threshold: int = 3, reset_timeout_sec: float = 300.0) -> None:
        self.failure_threshold = failure_threshold
        self.reset_timeout_sec = reset_timeout_sec
        self.failure_count = 0
        self.last_failure_time: float = 0.0
        self.state = "CLOSED"

    def can_execute(self) -> bool:
        now = time.monotonic()
        if self.state == "OPEN":
            if now - self.last_failure_time >= self.reset_timeout_sec:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker transitioned to HALF_OPEN after cooldown")
                return True
            return False
        return True

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                "Circuit breaker tripped OPEN (failures: %d >= %d). In cooldown for %.1fs",
                self.failure_count,
                self.failure_threshold,
                self.reset_timeout_sec,
            )


class ActionSafetyManager:
    """Coordinates locks, cooldowns, and circuit breakers across all registered actions."""

    def __init__(self, failure_threshold: int = 3, reset_timeout_sec: float = 300.0) -> None:
        self._execution_lock = asyncio.Lock()
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._last_execution_time: Dict[str, float] = {}
        self.default_failure_threshold = failure_threshold
        self.default_reset_timeout = reset_timeout_sec

    def is_cooling_down(self, action_id: str, cooldown_sec: float) -> bool:
        """Check if action is in cooldown since last execution."""
        now = time.monotonic()
        last_time = self._last_execution_time.get(action_id, 0.0)
        return (now - last_time) < cooldown_sec

    def get_remaining_cooldown(self, action_id: str, cooldown_sec: float) -> float:
        now = time.monotonic()
        last_time = self._last_execution_time.get(action_id, 0.0)
        elapsed = now - last_time
        return max(0.0, cooldown_sec - elapsed)

    def can_execute(self, action_id: str, cooldown_sec: float) -> Tuple[bool, str]:
        # 1. Check circuit breaker
        breaker = self._breakers.setdefault(
            action_id,
            CircuitBreaker(self.default_failure_threshold, self.default_reset_timeout),
        )
        if not breaker.can_execute():
            return False, f"Circuit breaker OPEN for action {action_id} (tripped due to repeated failures)"

        # 2. Check cooldown
        if self.is_cooling_down(action_id, cooldown_sec):
            remaining = self.get_remaining_cooldown(action_id, cooldown_sec)
            return False, f"Action {action_id} is in cooldown ({remaining:.1f}s remaining)"

        return True, "Safe to execute"

    def record_execution_start(self, action_id: str) -> None:
        self._last_execution_time[action_id] = time.monotonic()

    def record_success(self, action_id: str) -> None:
        breaker = self._breakers.get(action_id)
        if breaker:
            breaker.record_success()

    def record_failure(self, action_id: str) -> None:
        breaker = self._breakers.get(action_id)
        if breaker:
            breaker.record_failure()

    @property
    def lock(self) -> asyncio.Lock:
        return self._execution_lock
