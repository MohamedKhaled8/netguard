"""Shared background asyncio coroutine runner for PySide6 views."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
from typing import Any, Callable, Dict, Optional, Set
import uuid

from PySide6.QtCore import QObject, Signal

from app.core.perf import PerfMetricsCollector


class AsyncViewBridge(QObject):
    """Safely executes async coroutines in a bounded worker pool with dedup & timeouts."""

    finished = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self, parent: Optional[QObject] = None, max_workers: int = 4) -> None:
        super().__init__(parent)
        self._callbacks: Dict[str, tuple[Callable[[Any], None], Optional[Callable[[str], None]], Optional[str]]] = {}
        self._active_op_keys: Set[str] = set()
        self._is_shutting_down = False
        self._executor = ThreadPoolExecutor(
            max_workers=max(1, int(max_workers)),
            thread_name_prefix="NetGuardViewAsync",
        )
        self.finished.connect(self._on_finished)
        self.failed.connect(self._on_failed)

    def is_busy(self, op_key: str) -> bool:
        return op_key in self._active_op_keys

    def run_coro(
        self,
        coro_factory: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_error: Optional[Callable[[str], None]] = None,
        *,
        op_key: Optional[str] = None,
        timeout_sec: Optional[float] = 25.0,
    ) -> Optional[str]:
        if self._is_shutting_down:
            return None
        perf = PerfMetricsCollector.get_instance()
        if op_key and op_key in self._active_op_keys:
            perf.increment_counter(f"dedup_skip:{op_key}")
            return None

        task_id = uuid.uuid4().hex
        if op_key:
            self._active_op_keys.add(op_key)
        self._callbacks[task_id] = (on_success, on_error, op_key)
        perf.worker_started()

        def _worker() -> None:
            t0 = time.perf_counter()
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                coro = coro_factory()
                if timeout_sec is not None and timeout_sec > 0:
                    res = loop.run_until_complete(asyncio.wait_for(coro, timeout=float(timeout_sec)))
                else:
                    res = loop.run_until_complete(coro)
                if not self._is_shutting_down:
                    self.finished.emit(task_id, res)
            except asyncio.TimeoutError:
                if not self._is_shutting_down:
                    self.failed.emit(task_id, f"Operation timed out after {timeout_sec:.1f}s")
            except Exception as exc:
                if not self._is_shutting_down:
                    self.failed.emit(task_id, str(exc))
            finally:
                if op_key:
                    perf.record_timing(op_key, (time.perf_counter() - t0) * 1000.0)
                perf.worker_finished()
                try:
                    loop.close()
                except Exception:
                    pass

        try:
            self._executor.submit(_worker)
        except RuntimeError:
            self._callbacks.pop(task_id, None)
            if op_key:
                self._active_op_keys.discard(op_key)
            perf.worker_finished()
            return None
        return task_id

    def _on_finished(self, task_id: str, result: Any) -> None:
        entry = self._callbacks.pop(task_id, None)
        if entry:
            on_ok, _on_err, op_key = entry
            if op_key:
                self._active_op_keys.discard(op_key)
            if not self._is_shutting_down and on_ok:
                on_ok(result)

    def _on_failed(self, task_id: str, err: str) -> None:
        entry = self._callbacks.pop(task_id, None)
        if entry:
            _on_ok, on_err, op_key = entry
            if op_key:
                self._active_op_keys.discard(op_key)
            if not self._is_shutting_down and on_err:
                on_err(err)

    def shutdown(self) -> None:
        self._is_shutting_down = True
        self._callbacks.clear()
        self._active_op_keys.clear()
        try:
            self._executor.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            self._executor.shutdown(wait=False)
        except Exception:
            pass

