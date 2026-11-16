"""Asynchronous in-memory topic-based Event Bus."""

from __future__ import annotations
import asyncio
import fnmatch
import logging
from typing import Any, Callable, Coroutine, Dict, List, Set
from pydantic import BaseModel

logger = logging.getLogger("netguard.events")

SubscriberCallback = Callable[[str, Any], Coroutine[Any, Any, None]]


class EventTopics:
    """Centralized topic constants and wildcards for NetGuard EventBus."""

    # Telemetry
    TELEMETRY_PREFIX: str = "telemetry."
    TELEMETRY_ALL: str = "telemetry.*"

    # Diagnosis
    DIAGNOSIS_PREFIX: str = "diagnosis."
    DIAGNOSIS_INCIDENT: str = "diagnosis.incident"
    DIAGNOSIS_ALL: str = "diagnosis.*"

    # Remediation
    REMEDIATION_PREFIX: str = "remediation."
    REMEDIATION_STARTED: str = "remediation.started"
    REMEDIATION_COMPLETED: str = "remediation.completed"
    REMEDIATION_APPROVAL_REQUIRED: str = "remediation.approval_required"
    REMEDIATION_ACTION_SUPPRESSED: str = "remediation.action_suppressed"
    REMEDIATION_ROLLBACK_STARTED: str = "remediation.rollback.started"
    REMEDIATION_ROLLBACK_COMPLETED: str = "remediation.rollback.completed"

    # DNS
    DNS_BENCHMARK_COMPLETED: str = "dns.benchmark.completed"
    DNS_SWITCHED: str = "dns.switched"

    # Traffic & Diagnostics
    TRAFFIC_WORKLOAD_UPDATE: str = "traffic.workload_update"
    BUFFERBLOAT_REPORT: str = "bufferbloat.report"
    CELLULAR_METRICS: str = "cellular.metrics"
    PREDICTION_WARNING: str = "prediction.warning"
    PREDICTION_PREFIX: str = "prediction.warning."

    # System & Configuration State
    MODE_CHANGED: str = "mode.changed"
    SETTINGS_CHANGED: str = "settings.changed"

    @classmethod
    def all_topics(cls) -> List[str]:
        """Return all defined topic strings and patterns."""
        return [
            v for k, v in cls.__dict__.items()
            if isinstance(v, str) and not k.startswith("_")
        ]


class EventBus:
    """Thread-safe and async-safe pub/sub event bus supporting glob topic patterns."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, Set[SubscriberCallback]] = {}
        self._lock = asyncio.Lock()
        self._running = True

    async def subscribe(self, topic_pattern: str, callback: SubscriberCallback) -> None:
        """Subscribe a coroutine callback to a topic pattern (e.g. 'telemetry.*')."""
        async with self._lock:
            if topic_pattern not in self._subscribers:
                self._subscribers[topic_pattern] = set()
            self._subscribers[topic_pattern].add(callback)
            logger.debug("Subscribed %s to pattern '%s'", callback.__name__, topic_pattern)

    def subscribe_sync(self, topic_pattern: str, callback: SubscriberCallback) -> None:
        """Synchronous subscription registration for non-async callers (e.g. UI widgets)."""
        if topic_pattern not in self._subscribers:
            self._subscribers[topic_pattern] = set()
        self._subscribers[topic_pattern].add(callback)

    async def unsubscribe(self, topic_pattern: str, callback: SubscriberCallback) -> None:
        """Unsubscribe a callback from a topic pattern."""
        async with self._lock:
            if topic_pattern in self._subscribers:
                self._subscribers[topic_pattern].discard(callback)
                if not self._subscribers[topic_pattern]:
                    del self._subscribers[topic_pattern]

    async def publish(self, topic: str, payload: Any) -> int:
        """Publish an event to all matching topic subscribers concurrently."""
        if not self._running:
            return 0

        matching_callbacks: List[SubscriberCallback] = []
        async with self._lock:
            for pattern, callbacks in self._subscribers.items():
                if fnmatch.fnmatch(topic, pattern):
                    matching_callbacks.extend(callbacks)

        if not matching_callbacks:
            return 0

        # Execute all matching subscriber callbacks safely
        tasks = []
        for cb in matching_callbacks:
            tasks.append(self._safe_dispatch(cb, topic, payload))
        await asyncio.gather(*tasks, return_exceptions=True)
        return len(matching_callbacks)

    def publish_sync(self, topic: str, payload: Any) -> None:
        """Synchronous publish dispatch for non-async callers (e.g. Qt slots/signals)."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.publish(topic, payload))
        except RuntimeError:
            try:
                asyncio.run(self.publish(topic, payload))
            except Exception as exc:
                logger.error("Error in publish_sync on topic %s: %s", topic, exc)

    async def _safe_dispatch(self, callback: SubscriberCallback, topic: str, payload: Any) -> None:
        try:
            await callback(topic, payload)
        except Exception as exc:
            logger.error("Error in event subscriber %s on topic %s: %s", callback.__name__, topic, exc, exc_info=True)

    def shutdown(self) -> None:
        """Stop accepting new events and clear subscribers."""
        self._running = False
        self._subscribers.clear()
