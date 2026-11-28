"""Single-flight diagnostic coordinator and NetGuard meeting/QoS safety guard."""

from __future__ import annotations

import asyncio
import inspect
import threading
import uuid
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Iterator, Optional

from app.wifi.models import utc_now


class DiagnosticCancelledError(RuntimeError):
    """Raised when an active diagnostic operation is cancelled cooperatively."""


class DiagnosticBusyError(RuntimeError):
    """Raised when an exclusive diagnostic operation is already in flight."""


class MeetingSafetyFreezeError(RuntimeError):
    """Raised when an intrusive diagnostic or network mutation is blocked by active meeting protection."""


class ApprovalRequiredError(RuntimeError):
    """Raised when a mutating or QoS-suspending operation lacks explicit user approval."""


class CancellationToken:
    """Thread-safe cooperative cancellation flag shared across async and threaded probes."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self._reason: Optional[str] = None

    def cancel(self, reason: str = "Cancelled by user") -> None:
        self._reason = reason
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    @property
    def reason(self) -> Optional[str]:
        return self._reason

    def raise_if_cancelled(self) -> None:
        if self._event.is_set():
            raise DiagnosticCancelledError(self._reason or "Diagnostic cancelled.")

    def wait(self, timeout: float) -> bool:
        return self._event.wait(timeout)


@dataclass
class ActiveOperationInfo:
    """Live metadata about the currently running exclusive diagnostic."""

    operation_id: str
    operation_type: str
    description: str
    started_at: datetime = field(default_factory=utc_now)
    progress_pct: float = 0.0
    stage_label: str = "starting"
    cancel_requested: bool = False


@dataclass
class QosSnapshotState:
    """Observed NetGuard QoS configuration and Windows policy store state."""

    master_enabled: Optional[bool]
    active_spec_count: int
    os_policy_count: int
    os_policy_names: list[str]
    verified_source: str


@dataclass
class QosSuspendAudit:
    """Verification record for explicit-approval idle QoS comparison."""

    approved_by_user: bool
    pre_snapshot: QosSnapshotState
    suspended_snapshot: Optional[QosSnapshotState] = None
    post_restore_snapshot: Optional[QosSnapshotState] = None
    suspension_verified: bool = False
    post_restore_verified: bool = False
    restore_error: Optional[str] = None
    summary: str = ""


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


class DiagnosticCoordinator:
    """Prevents concurrent throughput/baseline collisions and enforces NetGuard meeting safety."""

    EXCLUSIVE_MEETING_FROZEN_OPS = {
        "speed_test",
        "bufferbloat_test",
        "active_wlan_scan",
        "dns_flush",
        "dns_change",
        "dhcp_renew",
        "adapter_reset",
        "qos_suspend_compare",
        "router_wifi_apply",
    }

    def __init__(
        self,
        traffic_controller: Any = None,
        platform: Any = None,
        event_bus: Any = None,
    ) -> None:
        self._traffic_controller = traffic_controller
        self._platform = platform
        self._event_bus = event_bus
        self._state_lock = threading.RLock()
        self._exclusive_lock = threading.Lock()
        self._active_op: Optional[ActiveOperationInfo] = None
        self._active_token: Optional[CancellationToken] = None

    def bind(
        self,
        *,
        traffic_controller: Any = None,
        platform: Any = None,
        event_bus: Any = None,
    ) -> None:
        """Attach runtime services after partial construction."""
        if traffic_controller is not None:
            self._traffic_controller = traffic_controller
        if platform is not None:
            self._platform = platform
        if event_bus is not None:
            self._event_bus = event_bus

    def is_busy(self) -> bool:
        with self._state_lock:
            return self._active_op is not None

    def get_active_operation(self) -> Optional[ActiveOperationInfo]:
        with self._state_lock:
            if self._active_op is None:
                return None
            return ActiveOperationInfo(
                operation_id=self._active_op.operation_id,
                operation_type=self._active_op.operation_type,
                description=self._active_op.description,
                started_at=self._active_op.started_at,
                progress_pct=self._active_op.progress_pct,
                stage_label=self._active_op.stage_label,
                cancel_requested=self._active_op.cancel_requested,
            )

    def update_progress(self, progress_pct: float, stage_label: str) -> None:
        with self._state_lock:
            if self._active_op is not None:
                self._active_op.progress_pct = max(0.0, min(100.0, float(progress_pct)))
                self._active_op.stage_label = stage_label

    def request_cancel(self, reason: str = "Cancelled by user") -> bool:
        with self._state_lock:
            if self._active_op is None or self._active_token is None:
                return False
            self._active_op.cancel_requested = True
            self._active_token.cancel(reason)
            return True

    def is_meeting_active(self) -> tuple[bool, str]:
        """Inspect NetGuard TrafficController and hysteresis/session state for active or transitional calls."""
        tc = self._traffic_controller
        if tc is None:
            return False, "No TrafficController attached; no active meeting state reported."

        try:
            critical_fn = getattr(tc, "is_critical_meeting_active", None)
            if callable(critical_fn) and bool(critical_fn()):
                hyst = getattr(tc, "hysteresis_tracker", None)
                state = getattr(hyst, "state", None)
                state_name = getattr(state, "name", str(state)) if state is not None else "ACTIVE"
                return True, (
                    f"NetGuard meeting protection is active (state={state_name}). "
                    "Intrusive throughput, bufferbloat, active RF scans, or network changes are blocked."
                )

            hyst = getattr(tc, "hysteresis_tracker", None)
            if hyst is not None:
                state = getattr(hyst, "state", None)
                state_name = getattr(state, "name", str(state)) if state is not None else ""
                if state_name.upper() in {"ENTERING", "ACTIVE", "LEAVING"}:
                    return True, (
                        f"NetGuard meeting hysteresis is in transitional/active state ({state_name})."
                    )
        except Exception as exc:
            # Fail conservative if meeting check itself errors? Report clearly without crashing passive UI.
            return True, f"Meeting state check failed conservatively: {exc}"

        return False, "No active or transitional conferencing session detected."

    def check_operation_allowed(
        self,
        operation_type: str,
        *,
        force_allow_passive_during_meeting: bool = False,
    ) -> tuple[bool, Optional[str]]:
        """Validate single-flight availability and meeting safety rules before starting an op."""
        if (
            not force_allow_passive_during_meeting
            and operation_type in self.EXCLUSIVE_MEETING_FROZEN_OPS
        ):
            active, reason = self.is_meeting_active()
            if active:
                return False, reason

        with self._state_lock:
            if self._active_op is not None:
                return False, (
                    f"Another diagnostic is already running ({self._active_op.operation_type}: "
                    f"{self._active_op.description}). Wait for it to finish or cancel it first."
                )
        return True, None

    def get_qos_status_summary(self) -> Dict[str, Any]:
        """Summarize active NetGuard QoS configuration for speed/bufferbloat context."""
        tc = self._traffic_controller
        if tc is None:
            return {
                "master_enabled": False,
                "active_policies_count": 0,
                "summary": "TrafficController not attached.",
            }

        qos_cfg = getattr(tc, "qos_config", None)
        master_enabled = bool(getattr(qos_cfg, "master_enabled", False)) if qos_cfg else False
        specs = getattr(tc, "_active_qos_specs", {}) or {}
        spec_count = len(specs) if isinstance(specs, dict) else 0
        summary = (
            f"NetGuard QoS enabled ({spec_count} active Windows QoS specs)"
            if master_enabled
            else "NetGuard QoS disabled"
        )
        return {
            "master_enabled": master_enabled,
            "active_policies_count": spec_count,
            "summary": summary,
        }

    def _begin_exclusive(
        self, operation_type: str, description: str
    ) -> tuple[ActiveOperationInfo, CancellationToken]:
        allowed, reason = self.check_operation_allowed(operation_type)
        if not allowed:
            if reason and "meeting" in reason.lower():
                raise MeetingSafetyFreezeError(reason)
            raise DiagnosticBusyError(reason or "Diagnostic coordinator is busy.")

        acquired = self._exclusive_lock.acquire(blocking=False)
        if not acquired:
            raise DiagnosticBusyError("Another exclusive diagnostic is already executing.")

        try:
            with self._state_lock:
                if self._active_op is not None:
                    raise DiagnosticBusyError(
                        f"Diagnostic {self._active_op.operation_type} is already active."
                    )
                token = CancellationToken()
                info = ActiveOperationInfo(
                    operation_id=uuid.uuid4().hex[:12],
                    operation_type=operation_type,
                    description=description,
                )
                self._active_op = info
                self._active_token = token
                return info, token
        except Exception:
            self._exclusive_lock.release()
            raise

    def _end_exclusive(self, operation_id: str) -> None:
        try:
            with self._state_lock:
                if self._active_op and self._active_op.operation_id == operation_id:
                    self._active_op = None
                    self._active_token = None
        finally:
            if self._exclusive_lock.locked():
                self._exclusive_lock.release()

    @contextmanager
    def sync_exclusive(
        self, operation_type: str, description: str
    ) -> Iterator[CancellationToken]:
        """Acquire exclusive diagnostic slot for synchronous/worker-thread execution."""
        info, token = self._begin_exclusive(operation_type, description)
        try:
            yield token
        finally:
            self._end_exclusive(info.operation_id)

    @asynccontextmanager
    async def async_exclusive(
        self, operation_type: str, description: str
    ):
        """Acquire exclusive diagnostic slot for asyncio execution."""
        info, token = self._begin_exclusive(operation_type, description)
        try:
            yield token
        finally:
            self._end_exclusive(info.operation_id)

    def _read_qos_snapshot_sync(self) -> QosSnapshotState:
        tc = self._traffic_controller
        qos_cfg = getattr(tc, "qos_config", None) if tc else None
        master_enabled = bool(getattr(qos_cfg, "master_enabled", False)) if qos_cfg else None
        specs = getattr(tc, "_active_qos_specs", {}) if tc else {}
        spec_count = len(specs) if isinstance(specs, dict) else 0

        policy_names: list[str] = []
        os_count = spec_count
        source = "traffic_controller_cache"
        plat = self._platform or (getattr(tc, "platform", None) if tc else None)
        if plat is not None and hasattr(plat, "get_qos_policies"):
            try:
                policies = plat.get_qos_policies("ActiveStore")
                if not inspect.isawaitable(policies) and isinstance(policies, list):
                    os_count = len(policies)
                    policy_names = [
                        str(getattr(p, "name", p)) for p in policies[:20]
                    ]
                    source = "windows_active_store"
            except Exception:
                pass

        return QosSnapshotState(
            master_enabled=master_enabled,
            active_spec_count=spec_count,
            os_policy_count=os_count,
            os_policy_names=policy_names,
            verified_source=source,
        )

    async def _read_qos_snapshot_async(self) -> QosSnapshotState:
        tc = self._traffic_controller
        qos_cfg = getattr(tc, "qos_config", None) if tc else None
        master_enabled = bool(getattr(qos_cfg, "master_enabled", False)) if qos_cfg else None
        specs = getattr(tc, "_active_qos_specs", {}) if tc else {}
        spec_count = len(specs) if isinstance(specs, dict) else 0

        policy_names: list[str] = []
        os_count = spec_count
        source = "traffic_controller_cache"
        plat = self._platform or (getattr(tc, "platform", None) if tc else None)
        if plat is not None and hasattr(plat, "get_qos_policies"):
            try:
                policies = await _maybe_await(plat.get_qos_policies("ActiveStore"))
                if isinstance(policies, list):
                    os_count = len(policies)
                    policy_names = [
                        str(getattr(p, "name", p)) for p in policies[:20]
                    ]
                    source = "windows_active_store"
            except Exception:
                pass

        return QosSnapshotState(
            master_enabled=master_enabled,
            active_spec_count=spec_count,
            os_policy_count=os_count,
            os_policy_names=policy_names,
            verified_source=source,
        )

    async def run_with_optional_idle_qos_suspension(
        self,
        *,
        explicit_user_approval: bool,
        callback: Callable[[], Awaitable[Any] | Any],
    ) -> tuple[Any, QosSuspendAudit]:
        """Safely run an idle-only comparison with NetGuard QoS paused and guaranteed restore."""
        if not explicit_user_approval:
            raise ApprovalRequiredError(
                "Explicit user confirmation is required before temporarily suspending NetGuard QoS."
            )

        meeting_active, meeting_reason = self.is_meeting_active()
        if meeting_active:
            raise MeetingSafetyFreezeError(meeting_reason)

        tc = self._traffic_controller
        if tc is None:
            raise RuntimeError("TrafficController is unavailable for QoS state inspection.")

        pre_snapshot = await self._read_qos_snapshot_async()
        qos_cfg = getattr(tc, "qos_config", None)
        original_master = bool(getattr(qos_cfg, "master_enabled", False)) if qos_cfg else False

        audit = QosSuspendAudit(
            approved_by_user=True,
            pre_snapshot=pre_snapshot,
        )

        result: Any = None
        try:
            # Suspend QoS cleanly using TrafficController mechanisms.
            if hasattr(tc, "kill_switch_disable"):
                await _maybe_await(tc.kill_switch_disable())
            elif hasattr(tc, "cleanup_all_policies"):
                await _maybe_await(tc.cleanup_all_policies())
            if qos_cfg is not None:
                qos_cfg.master_enabled = False

            suspended_snap = await self._read_qos_snapshot_async()
            audit.suspended_snapshot = suspended_snap
            audit.suspension_verified = (
                not bool(suspended_snap.master_enabled)
                and suspended_snap.active_spec_count == 0
                and (
                    suspended_snap.verified_source != "windows_active_store"
                    or suspended_snap.os_policy_count == 0
                )
            )

            result = await _maybe_await(callback())
        finally:
            try:
                if qos_cfg is not None:
                    qos_cfg.master_enabled = original_master
                if original_master and hasattr(tc, "reconcile_active_policies"):
                    await _maybe_await(tc.reconcile_active_policies())
                post_snap = await self._read_qos_snapshot_async()
                audit.post_restore_snapshot = post_snap
                audit.post_restore_verified = (
                    bool(post_snap.master_enabled) == original_master
                    and post_snap.active_spec_count >= pre_snapshot.active_spec_count
                )
            except Exception as exc:
                audit.restore_error = str(exc)
                audit.post_restore_verified = False

        if audit.restore_error:
            audit.summary = f"QoS restore encountered an error: {audit.restore_error}"
        elif audit.post_restore_verified:
            audit.summary = (
                "QoS paused for idle test and verified restored to pre-test configuration."
            )
        else:
            audit.summary = (
                "QoS comparison finished; post-restore policy counts differed from baseline snapshot."
            )

        return result, audit
