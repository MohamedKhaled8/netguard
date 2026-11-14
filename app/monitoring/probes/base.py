"""Base Probe definition with rate limiting, timeouts, and error handling."""

from __future__ import annotations
import asyncio
import time
import logging
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime, timezone
from app.monitoring.models.probe_result import ProbeResult
from app.platform.interfaces import IPlatformAdapter

logger = logging.getLogger("netguard.monitoring")


class BaseProbe(ABC):
    """Abstract base class for all network observability probes."""

    def __init__(
        self,
        name: str,
        interval_sec: float,
        timeout_sec: float,
        platform_adapter: IPlatformAdapter,
        retry_count: int = 1,
        min_interval_sec: float = 0.2,
    ) -> None:
        self.name = name
        self.interval_sec = interval_sec
        self.timeout_sec = timeout_sec
        self.platform = platform_adapter
        self.retry_count = retry_count
        self.min_interval_sec = min_interval_sec
        self._last_run_time: float = 0.0
        self._lock = asyncio.Lock()

    async def run(self) -> List[ProbeResult]:
        """Executes probe with rate limiting, timeout deadline, and error shielding."""
        async with self._lock:
            now = time.monotonic()
            if now - self._last_run_time < self.min_interval_sec:
                logger.debug("Probe %s rate-limited (elapsed: %.3fs)", self.name, now - self._last_run_time)
                return []
            self._last_run_time = now

        try:
            return await asyncio.wait_for(self.execute(), timeout=self.timeout_sec)
        except asyncio.TimeoutError:
            logger.warning("Probe %s exceeded timeout of %.2fs", self.name, self.timeout_sec)
            return self._handle_timeout()
        except Exception as exc:
            logger.error("Probe %s failed with exception: %s", self.name, exc, exc_info=True)
            return self._handle_error(exc)

    @abstractmethod
    async def execute(self) -> List[ProbeResult]:
        """Implementation logic of the probe."""
        pass

    def _handle_timeout(self) -> List[ProbeResult]:
        """Fallback results when probe times out."""
        return []

    def _handle_error(self, exc: Exception) -> List[ProbeResult]:
        """Fallback results when probe raises unhandled exception."""
        return []
