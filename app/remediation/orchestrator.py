"""Central Remediation Orchestrator executing the 11-step autonomous self-healing lifecycle."""

from __future__ import annotations
import asyncio
import time
import uuid
import logging
from typing import Any, Dict, Optional, Callable, Tuple
from datetime import datetime, timezone

from app.core.config.models import RemediationConfig
from app.core.bus import EventBus, EventTopics
from app.core.models.metrics import (
    Diagnosis,
    DiagnosisSeverity,
    ProbableCause,
    OperatingMode,
    RiskLevel,
    ActionExecutionRecord,
    ActionExecutionStatus,
)
from app.platform.interfaces import IPlatformAdapter
from app.remediation.registry import ActionRegistry, RemediationAction
from app.remediation.safety import ActionSafetyManager
from app.storage.repositories.audit_repo import AuditRepository

logger = logging.getLogger("netguard.remediation.orchestrator")


class RemediationOrchestrator:
    """Policy-governed decision orchestrator managing recovery actions, verifications, and rollbacks."""

    def __init__(
        self,
        config: RemediationConfig,
        registry: ActionRegistry,
        safety_manager: ActionSafetyManager,
        platform_adapter: IPlatformAdapter,
        audit_repo: AuditRepository,
        event_bus: EventBus,
        meeting_guard_check: Optional[Callable[[], bool]] = None,
        user_settings: Optional[Any] = None,
    ) -> None:
        self.config = config
        self.registry = registry
        self.safety = safety_manager
        self.platform = platform_adapter
        self.audit = audit_repo
        self.event_bus = event_bus
        self.meeting_guard_check = meeting_guard_check
        self.user_settings = user_settings
        self._policies: Dict[str, bool] = {}
        self.mode = OperatingMode(config.mode)
        self._pending_approvals: Dict[str, Dict[str, Any]] = {}
        if self.event_bus:
            self.event_bus.subscribe_sync(EventTopics.MODE_CHANGED, self._on_mode_changed_event)
            self.event_bus.subscribe_sync(EventTopics.SETTINGS_CHANGED, self._on_settings_changed_event)

    DRASTIC_ACTION_IDS = {
        "reset_winsock",
        "reset_tcpip",
        "restart_adapter",
        "reset_winsock_catalog",
    }

    ACTION_TO_POLICY_MAP = {
        "flush_dns_cache": "allow_flush_dns",
        "switch_dns_resolver": "allow_switch_dns",
        "renew_ip_lease": "allow_renew_ip",
        "meeting_guard_qos": "meeting_guard",
    }

    async def _on_mode_changed_event(self, topic: str, data: Any) -> None:
        mode_val = data.get("mode") if isinstance(data, dict) else str(data)
        self.set_operating_mode(OperatingMode(mode_val))

    async def _on_settings_changed_event(self, topic: str, data: Any) -> None:
        if isinstance(data, dict):
            if "policy" in data and "enabled" in data:
                self.set_policy(data["policy"], data["enabled"])

    def set_policy(self, name: str, enabled: bool) -> None:
        """Update policy toggle."""
        self._policies[name] = bool(enabled)
        if self.user_settings:
            self.user_settings.set_policy(name, enabled)

    def set_operating_mode(self, mode: OperatingMode | str) -> None:
        """Switch operating mode (Observation, Assisted, Autonomous Safe)."""
        new_mode = OperatingMode(mode)
        if getattr(self, "mode", None) == new_mode:
            return
        logger.info("Switching operating mode from %s to %s", getattr(self.mode, "value", self.mode), new_mode.value)
        self.mode = new_mode

    async def handle_diagnosis(self, diagnosis: Diagnosis) -> Optional[ActionExecutionRecord]:
        """Entry point for the 11-step remediation lifecycle."""
        # 1-4: Observe, Detect, Diagnose, Estimate Confidence
        if diagnosis.probable_cause == ProbableCause.HEALTHY:
            return None

        if not diagnosis.recommended_actions:
            logger.info("Diagnosis '%s' has no recommended actions", diagnosis.probable_cause.value)
            return None

        # 5: Select Action
        selected_action: Optional[RemediationAction] = None
        for action_id in diagnosis.recommended_actions:
            candidate = self.registry.get(action_id)
            if candidate:
                # Prioritize lower risk levels
                if not selected_action or candidate.risk_level.value < selected_action.risk_level.value:
                    selected_action = candidate

        if not selected_action:
            logger.warning("No registered action found matching: %s", diagnosis.recommended_actions)
            return None

        # 6: Check Safety & Policy Authorization
        # Policy Toggles Gate
        policy_key = self.ACTION_TO_POLICY_MAP.get(selected_action.action_id)
        if policy_key is not None:
            policy_enabled = True
            if self.user_settings:
                policy_enabled = self.user_settings.get_policy(policy_key)
            elif policy_key in self._policies:
                policy_enabled = self._policies[policy_key]

            if not policy_enabled:
                logger.info("Action '%s' suppressed by policy toggle '%s'=False", selected_action.action_id, policy_key)
                await self.event_bus.publish(
                    EventTopics.REMEDIATION_ACTION_SUPPRESSED,
                    {"action_id": selected_action.action_id, "reason": f"Policy '{policy_key}' is disabled"},
                )
                return None

        # Meeting Guard Safety Gate: Never drop active streaming/conferencing sockets
        if self.meeting_guard_check and self.meeting_guard_check():
            if selected_action.risk_level == RiskLevel.LEVEL_3_DISRUPTIVE or selected_action.action_id in self.DRASTIC_ACTION_IDS:
                logger.warning(
                    "Meeting Guard Safety: Disruptive action '%s' blocked to protect active Zoom/Meet call",
                    selected_action.action_id,
                )
                await self.event_bus.publish(EventTopics.REMEDIATION_ACTION_SUPPRESSED, {
                    "action_id": selected_action.action_id,
                    "reason": "حماية مكالمة الفيديو النشطة: تم تأجيل الإجراء المربك لضمان عدم انقطاع البث والصوت.",
                })
                return None

        is_drastic = (
            selected_action.action_id in self.DRASTIC_ACTION_IDS
            or (selected_action.risk_level == RiskLevel.LEVEL_3_DISRUPTIVE and not self.config.allow_level_3_disruptive)
        )
        if is_drastic:
            logger.warning("Drastic action '%s' intercepted; requires explicit user approval in all modes", selected_action.action_id)
            self._pending_approvals[selected_action.action_id] = {
                "action": selected_action,
                "diagnosis": diagnosis,
                "context": {"diagnosis": diagnosis, "interface_name": self.platform.get_primary_interface()},
                "timestamp": time.time(),
            }
            await self.event_bus.publish(
                EventTopics.REMEDIATION_APPROVAL_REQUIRED,
                {
                    "diagnosis": diagnosis.model_dump(mode="json"),
                    "action_id": selected_action.action_id,
                    "action_name": selected_action.name,
                    "risk_level": selected_action.risk_level.value,
                    "reason": "Drastic network action requires explicit user authorization",
                },
            )
            return None

        if self.mode == OperatingMode.WATCH:
            logger.info("Watch Mode: action '%s' suppressed (zero system modifications)", selected_action.action_id)
            await self.event_bus.publish(
                EventTopics.REMEDIATION_ACTION_SUPPRESSED,
                {"action_id": selected_action.action_id, "reason": "Watch mode active (read-only)"},
            )
            return None

        if self.mode == OperatingMode.ASK:
            logger.info("Assisted Mode: action '%s' awaiting user approval", selected_action.action_id)
            self._pending_approvals[selected_action.action_id] = {
                "action": selected_action,
                "diagnosis": diagnosis,
                "context": {"diagnosis": diagnosis, "interface_name": self.platform.get_primary_interface()},
                "timestamp": time.time(),
            }
            await self.event_bus.publish(EventTopics.REMEDIATION_APPROVAL_REQUIRED, {
                "diagnosis": diagnosis.model_dump(mode="json"),
                "action_id": selected_action.action_id,
                "action_name": selected_action.name,
                "risk_level": selected_action.risk_level.value,
                "reason": "Ask mode requires user authorization before modification",
            })
            return None

        # Autonomous Safe Mode: Verify Risk Policy
        if selected_action.risk_level == RiskLevel.LEVEL_3_DISRUPTIVE and not self.config.allow_level_3_disruptive:
            logger.warning("Disruptive action '%s' blocked by safety policy (allow_level_3_disruptive=False)", selected_action.action_id)
            return None

        # Check OS support
        if not selected_action.is_os_supported():
            logger.error("Action '%s' not supported on this operating system", selected_action.action_id)
            return None

        # Check Preconditions
        context = {"diagnosis": diagnosis, "interface_name": self.platform.get_primary_interface()}
        precond_ok, precond_msg = selected_action.check_preconditions(self.platform, context)
        if not precond_ok:
            logger.warning("Precondition failed for action '%s': %s", selected_action.action_id, precond_msg)
            return None

        # Check Circuit Breakers & Cooldowns
        can_run, safety_msg = self.safety.can_execute(selected_action.action_id, selected_action.cooldown_sec)
        if not can_run:
            logger.warning("Safety gate blocked action '%s': %s", selected_action.action_id, safety_msg)
            return None

        # Acquire execution lock (ensures serialization of network mutations)
        async with self.safety.lock:
            # Re-verify safety under lock
            can_run, safety_msg = self.safety.can_execute(selected_action.action_id, selected_action.cooldown_sec)
            if not can_run:
                return None

            return await self._execute_and_verify(selected_action, context, diagnosis)

    async def _execute_and_verify(
        self,
        action: RemediationAction,
        context: Dict[str, Any],
        diagnosis: Diagnosis,
    ) -> ActionExecutionRecord:
        """Executes action, conducts post-verification, and executes rollback if needed."""
        self.safety.record_execution_start(action.action_id)
        exec_start = time.perf_counter()
        pre_state = None
        error_msg = None
        post_metrics = {}
        status = ActionExecutionStatus.EXECUTING
        rollback_performed = False
        rollback_success = None

        logger.info("Executing recovery action: %s (%s)", action.name, action.action_id)
        await self.event_bus.publish(
            EventTopics.REMEDIATION_STARTED,
            {
                "action_id": action.action_id,
                "name": action.name,
                "action_name": action.name,
            },
        )

        # 7: EXECUTE
        try:
            pre_state = await asyncio.wait_for(
                action.execute(self.platform, context),
                timeout=action.timeout_sec,
            )
            exec_duration_ms = (time.perf_counter() - exec_start) * 1000.0
            status = ActionExecutionStatus.VERIFYING
        except Exception as exc:
            exec_duration_ms = (time.perf_counter() - exec_start) * 1000.0
            error_msg = f"Execution failed: {exc}"
            logger.error("Action %s failed execution: %s", action.action_id, exc, exc_info=True)
            self.safety.record_failure(action.action_id)
            status = ActionExecutionStatus.FAILED

            record = ActionExecutionRecord(
                id=str(uuid.uuid4()),
                action_id=action.action_id,
                action_name=action.name,
                risk_level=action.risk_level,
                trigger_diagnosis_id=diagnosis.id,
                pre_remedy_metrics={"pre_state": pre_state},
                post_remedy_metrics={},
                status=status,
                execution_duration_ms=exec_duration_ms,
                verification_duration_ms=0.0,
                error_message=error_msg,
                rollback_performed=False,
            )
            await self._record_and_publish(record)
            return record

        # 8: VERIFY
        verify_start = time.perf_counter()
        verify_ok = False
        verify_msg = ""
        try:
            verify_ok, verify_msg, post_metrics = await asyncio.wait_for(
                action.verify(self.platform, context, pre_state),
                timeout=self.config.verification_duration_sec + 2.0,
            )
        except Exception as exc:
            verify_ok = False
            verify_msg = f"Verification error: {exc}"

        verify_duration_ms = (time.perf_counter() - verify_start) * 1000.0

        # 9: ACCEPT OR ROLLBACK
        if verify_ok:
            status = ActionExecutionStatus.SUCCEEDED
            self.safety.record_success(action.action_id)
            logger.info("Action %s SUCCEEDED and VERIFIED: %s", action.action_id, verify_msg)
        else:
            logger.warning("Action %s FAILED post-verification: %s. Initiating ROLLBACK...", action.action_id, verify_msg)
            self.safety.record_failure(action.action_id)
            error_msg = f"Verification failed: {verify_msg}"

            # Rollback
            rollback_performed = True
            try:
                rb_ok, rb_msg = await action.rollback(self.platform, context, pre_state)
                rollback_success = rb_ok
                status = ActionExecutionStatus.ROLLED_BACK if rb_ok else ActionExecutionStatus.FAILED
                logger.info("Rollback result for %s: %s (%s)", action.action_id, rb_ok, rb_msg)
            except Exception as exc:
                rollback_success = False
                status = ActionExecutionStatus.FAILED
                error_msg += f" | Rollback exception: {exc}"
                logger.error("Critical: Rollback failed for %s: %s", action.action_id, exc, exc_info=True)

        # 10: RECORD
        record = ActionExecutionRecord(
            id=str(uuid.uuid4()),
            action_id=action.action_id,
            action_name=action.name,
            risk_level=action.risk_level,
            trigger_diagnosis_id=diagnosis.id,
            pre_remedy_metrics={"pre_state": pre_state},
            post_remedy_metrics=post_metrics,
            status=status,
            execution_duration_ms=exec_duration_ms,
            verification_duration_ms=verify_duration_ms,
            error_message=error_msg,
            rollback_performed=rollback_performed,
            rollback_success=rollback_success,
        )

        await self._record_and_publish(record)
        return record

    async def _record_and_publish(self, record: ActionExecutionRecord) -> None:
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self.audit.save, record)
        except Exception as exc:
            logger.warning("Failed to persist action audit log: %s", exc)

        payload = record.model_dump(mode="json")
        payload["name"] = record.action_name
        await self.event_bus.publish(EventTopics.REMEDIATION_COMPLETED, payload)

    async def approve_action(self, action_id: str, context: Optional[dict] = None) -> Tuple[bool, str]:
        """Execute held or proposed action upon explicit user authorization."""
        action = self.registry.get(action_id)
        if not action:
            return False, f"Action '{action_id}' not found in registry"

        pending = self._pending_approvals.pop(action_id, {})
        diag = (context or {}).get("diagnosis") or pending.get("diagnosis") or Diagnosis(
            probable_cause=ProbableCause.UNKNOWN_ANOMALY,
            confidence=1.0,
            severity=DiagnosisSeverity.HIGH,
            explanation="Manual user approval execution",
        )
        exec_context = context or pending.get("context") or {
            "diagnosis": diag,
            "interface_name": self.platform.get_primary_interface(),
        }

        if not action.is_os_supported():
            return False, f"Action '{action_id}' not supported on this OS"

        precond_ok, precond_msg = action.check_preconditions(self.platform, exec_context)
        if not precond_ok:
            return False, f"Precondition failed: {precond_msg}"

        async with self.safety.lock:
            can_run, safety_msg = self.safety.can_execute(action.action_id, action.cooldown_sec)
            if not can_run:
                return False, f"Safety gate blocked execution: {safety_msg}"

            record = await self._execute_and_verify(action, exec_context, diag)

        if record.status == ActionExecutionStatus.SUCCEEDED:
            return True, f"Action '{action.name}' completed successfully"
        return False, record.error_message or f"Action failed with status: {record.status.value}"

    async def reject_action(self, action_id: str) -> Tuple[bool, str]:
        """Reject and dismiss a held action."""
        self._pending_approvals.pop(action_id, None)
        await self.event_bus.publish(
            EventTopics.REMEDIATION_ACTION_SUPPRESSED,
            {"action_id": action_id, "reason": "User rejected proposed action"},
        )
        return True, f"Action '{action_id}' rejected"

    async def rollback_action(self, action_record_id: Optional[str] = None) -> Tuple[bool, str]:
        """Roll back a previous remediation action, restoring prior system state."""
        record: Optional[ActionExecutionRecord] = None
        if action_record_id is not None:
            if hasattr(self.audit, "get_by_id"):
                record = self.audit.get_by_id(action_record_id)
            if not record and hasattr(self.audit, "get_recent"):
                for r in self.audit.get_recent(limit=50):
                    if r.id == action_record_id:
                        record = r
                        break
            if not record:
                return False, f"Action record '{action_record_id}' not found in audit log"
        else:
            # Find latest reversible action that succeeded and has not been rolled back
            if hasattr(self.audit, "get_recent"):
                for r in self.audit.get_recent(limit=50):
                    if r.status == ActionExecutionStatus.SUCCEEDED and not r.rollback_performed:
                        record = r
                        break
            if not record:
                return False, "No prior actions found to rollback"

        action = self.registry.get(record.action_id)
        if not action:
            return False, f"Action '{record.action_id}' not found in registry"

        pre_state = (record.pre_remedy_metrics or {}).get("pre_state") if isinstance(record.pre_remedy_metrics, dict) else None
        context = {
            "interface_name": self.platform.get_primary_interface(),
            "action_record_id": record.id,
        }

        try:
            rb_ok, rb_msg = await action.rollback(self.platform, context, pre_state)
            if hasattr(self.audit, "update_rollback"):
                self.audit.update_rollback(record.id, rb_ok, None if rb_ok else rb_msg)

            await self.event_bus.publish(
                EventTopics.REMEDIATION_ROLLBACK_COMPLETED,
                {
                    "action_record_id": record.id,
                    "action_id": record.action_id,
                    "success": rb_ok,
                    "message": rb_msg,
                },
            )
            return rb_ok, rb_msg
        except Exception as exc:
            err = f"Rollback failed with exception: {exc}"
            logger.error(err, exc_info=True)
            if hasattr(self.audit, "update_rollback"):
                self.audit.update_rollback(record.id, False, err)
            return False, err
