"""Central Remediation Orchestrator executing the 11-step autonomous self-healing lifecycle."""

from __future__ import annotations
import asyncio
import time
import uuid
import logging
from typing import Any, Dict, Optional, Callable
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
    ) -> None:
        self.config = config
        self.registry = registry
        self.safety = safety_manager
        self.platform = platform_adapter
        self.audit = audit_repo
        self.event_bus = event_bus
        self.meeting_guard_check = meeting_guard_check
        self.mode = OperatingMode(config.mode)

    def set_operating_mode(self, mode: OperatingMode) -> None:
        """Switch operating mode (Observation, Assisted, Autonomous Safe)."""
        logger.info("Switching operating mode from %s to %s", self.mode.value, mode.value)
        self.mode = mode

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
        if self.mode == OperatingMode.OBSERVATION:
            logger.info("Observation Mode: action '%s' recommended but execution suppressed", selected_action.action_id)
            return None

        if self.mode == OperatingMode.ASSISTED:
            logger.info("Assisted Mode: action '%s' awaiting user approval", selected_action.action_id)
            await self.event_bus.publish(EventTopics.REMEDIATION_APPROVAL_REQUIRED, {
                "diagnosis": diagnosis.model_dump(mode="json"),
                "action_id": selected_action.action_id,
                "action_name": selected_action.name,
                "risk_level": selected_action.risk_level.value,
            })
            return None

        # Autonomous Safe Mode: Verify Risk Policy
        if selected_action.risk_level == RiskLevel.LEVEL_3_DISRUPTIVE and not self.config.allow_level_3_disruptive:
            logger.warning("Disruptive action '%s' blocked by safety policy (allow_level_3_disruptive=False)", selected_action.action_id)
            return None

        # Meeting Guard Safety Gate: Never drop active streaming/conferencing sockets
        if self.meeting_guard_check and self.meeting_guard_check():
            if selected_action.risk_level == RiskLevel.LEVEL_3_DISRUPTIVE:
                logger.warning(
                    "Meeting Guard Safety: Disruptive action '%s' blocked to protect active Zoom/Meet call",
                    selected_action.action_id,
                )
                await self.event_bus.publish(EventTopics.REMEDIATION_ACTION_SUPPRESSED, {
                    "action_id": selected_action.action_id,
                    "reason": "حماية مكالمة الفيديو النشطة: تم تأجيل الإجراء المربك لضمان عدم انقطاع البث والصوت.",
                })
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
