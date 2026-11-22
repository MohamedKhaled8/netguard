"""Master Animation Clock for PySide6 Views and Widgets in NetGuard AI.

Provides a centralized, energy-efficient tick source running at ~20 FPS (50ms)
to eliminate uncoordinated high-frequency timers and provide auto-throttling
for low-resource hardware.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, Set
from PySide6.QtCore import QObject, QTimer, Signal
from app.ui import tokens

logger = logging.getLogger("netguard.ui.animation_clock")


class AnimationMasterClock(QObject):
    """Centralized Master Animation Clock running at ~20 FPS (50ms interval).

    Consolidates disparate high-frequency animation timers into a single unified
    clock with dynamic throttling and low-resource mode support.
    """

    tick = Signal(float)  # Emits elapsed ms since last tick
    mode_changed = Signal(bool)  # Emits True when low resource mode is enabled

    _instance: Optional[AnimationMasterClock] = None

    def __init__(self, fps: int = 20, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._target_fps = fps
        # Energy-efficient throttling: 160ms interval (~6 FPS) to protect low-end CPUs
        self._interval_ms = 160
        self._low_resource_mode = False
        self._is_paused = False
        self._subscribers: Set[Callable[[float], None]] = set()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer_timeout)

        # Initialize state based on UI tokens
        if getattr(tokens, "LOW_RESOURCE_MODE", False):
            self.set_low_resource_mode(True)
        elif getattr(tokens, "ANIMATIONS_ENABLED", True):
            self.start()

    @classmethod
    def get_instance(cls) -> AnimationMasterClock:
        """Singleton accessor for the UI process."""
        if cls._instance is None:
            cls._instance = AnimationMasterClock()
        return cls._instance

    @property
    def is_running(self) -> bool:
        return self._timer.isActive()

    @property
    def is_low_resource_mode(self) -> bool:
        return self._low_resource_mode

    def start(self) -> None:
        if not getattr(tokens, "ANIMATIONS_ENABLED", False):
            self._timer.stop()
            return
        if not self._is_paused:
            interval = 100 if self._low_resource_mode else self._interval_ms
            self._timer.start(interval)

    def stop(self) -> None:
        self._timer.stop()

    def pause(self) -> None:
        self._is_paused = True
        self._timer.stop()

    def resume(self) -> None:
        self._is_paused = False
        self.start()

    def set_low_resource_mode(self, enabled: bool) -> None:
        """Toggle low-resource mode. Drops framerate to conserve CPU."""
        self._low_resource_mode = enabled
        logger.info("Animation Master Clock low-resource mode set to: %s", enabled)
        target_interval = 100 if enabled else self._interval_ms
        self._timer.setInterval(target_interval)
        if getattr(tokens, "ANIMATIONS_ENABLED", True) and not self._is_paused:
            if not self._timer.isActive():
                self._timer.start(target_interval)
        self.mode_changed.emit(enabled)

    def set_fps(self, fps: int) -> None:
        """Adjust base animation framerate."""
        self._target_fps = max(1, min(60, fps))
        self._interval_ms = 1000 // self._target_fps
        if self._timer.isActive() and not self._low_resource_mode:
            self._timer.setInterval(self._interval_ms)

    def subscribe(self, callback: Callable[[float], None]) -> None:
        """Subscribe a widget tick handler to the master clock."""
        self._subscribers.add(callback)
        if not self._timer.isActive() and not self._is_paused and getattr(tokens, "ANIMATIONS_ENABLED", True):
            self.start()

    def unsubscribe(self, callback: Callable[[float], None]) -> None:
        """Unsubscribe a widget tick handler."""
        self._subscribers.discard(callback)

    def _on_timer_timeout(self) -> None:
        delta_ms = float(self._timer.interval())
        self.tick.emit(delta_ms)
        dead = []
        for cb in list(self._subscribers):
            try:
                cb(delta_ms)
            except (ReferenceError, RuntimeError):
                dead.append(cb)
            except Exception as exc:
                logger.debug("Subscriber animation callback error: %s", exc)
        for d in dead:
            self._subscribers.discard(d)
