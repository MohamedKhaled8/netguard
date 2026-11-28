"""Master Animation Clock for PySide6 Views and Widgets in NetGuard AI.

Provides a centralized, energy-efficient tick source running at ~20 FPS (50ms)
to eliminate uncoordinated high-frequency timers and provide auto-throttling
for low-resource hardware.
"""

from __future__ import annotations

import logging
import weakref
from typing import Any, Callable, List, Optional, Set
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication
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
        self._subscribers: List[Any] = []

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
            app = QApplication.instance()
            cls._instance = AnimationMasterClock(parent=app)
            if app is not None:
                try:
                    app.aboutToQuit.connect(cls.shutdown_instance)
                except Exception:
                    pass
        return cls._instance

    @classmethod
    def shutdown_instance(cls) -> None:
        """Stop timer and release singleton cleanly before QApplication exits."""
        inst = cls._instance
        cls._instance = None
        if inst is not None:
            try:
                inst._timer.stop()
                inst._subscribers.clear()
                inst.deleteLater()
            except RuntimeError:
                pass

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
        """Subscribe a widget tick handler to the master clock without leaking C++ widget lifetime."""
        self.unsubscribe(callback)
        try:
            if hasattr(callback, "__self__") and hasattr(callback, "__func__"):
                self._subscribers.append(weakref.WeakMethod(callback))
            else:
                self._subscribers.append(callback)
        except TypeError:
            self._subscribers.append(callback)
        if not self._timer.isActive() and not self._is_paused and getattr(tokens, "ANIMATIONS_ENABLED", True):
            self.start()

    def unsubscribe(self, callback: Callable[[float], None]) -> None:
        """Unsubscribe a widget tick handler."""
        kept: List[Any] = []
        for entry in self._subscribers:
            cb = entry() if isinstance(entry, weakref.WeakMethod) else entry
            if cb is not None and cb != callback:
                kept.append(entry)
        self._subscribers = kept

    def _on_timer_timeout(self) -> None:
        delta_ms = float(self._timer.interval())
        self.tick.emit(delta_ms)
        alive: List[Any] = []
        callbacks: List[Callable[[float], None]] = []
        for entry in list(self._subscribers):
            if isinstance(entry, weakref.WeakMethod):
                cb = entry()
                if cb is None:
                    continue
                alive.append(entry)
                callbacks.append(cb)
            else:
                alive.append(entry)
                callbacks.append(entry)
        self._subscribers = alive
        for cb in callbacks:
            try:
                cb(delta_ms)
            except (ReferenceError, RuntimeError):
                self.unsubscribe(cb)
            except Exception as exc:
                logger.debug("Subscriber animation callback error: %s", exc)
