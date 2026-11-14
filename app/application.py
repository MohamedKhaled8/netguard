"""NetGuard AI Core Application Coordinator."""

from __future__ import annotations
import asyncio
import logging
from typing import Optional
from app.bootstrap import ApplicationContext, bootstrap_application
from app.monitoring.schedulers.engine import ObservabilityEngine
from app.diagnosis.engine import DiagnosisEngine
from app.remediation.registry import ActionRegistry
from app.remediation.safety import ActionSafetyManager
from app.remediation.orchestrator import RemediationOrchestrator
from app.remediation.actions.flush_dns import FlushDNSCacheAction
from app.remediation.actions.switch_dns import SwitchDNSResolverAction
from app.remediation.actions.renew_dhcp import RenewIPLeaseAction
from app.core.models.metrics import Diagnosis, OperatingMode

logger = logging.getLogger("netguard.application")


class NetGuardApplication:
    """Master runtime coordinator binding Observability, Diagnostics, and Autonomous Remediation."""

    def __init__(self, context: ApplicationContext) -> None:
        self.ctx = context
        self.config = context.config

        # 1. Observability Engine
        self.observability = ObservabilityEngine(
            config=self.config.probing,
            event_bus=self.ctx.event_bus,
            platform_adapter=self.ctx.platform,
            measurement_repo=self.ctx.measurements,
            window_size=self.config.thresholds.sliding_window_samples * 2,
        )

        # 2. Diagnosis Engine
        self.diagnosis = DiagnosisEngine(
            thresholds=self.config.thresholds,
            event_bus=self.ctx.event_bus,
            incident_repo=self.ctx.incidents,
        )

        # 3. Remediation Subsystem
        self.action_registry = ActionRegistry()
        self._register_default_actions()

        self.safety_manager = ActionSafetyManager(
            failure_threshold=self.config.remediation.circuit_breaker_failure_threshold,
            reset_timeout_sec=self.config.remediation.circuit_breaker_reset_timeout_sec,
        )

        self.orchestrator = RemediationOrchestrator(
            config=self.config.remediation,
            registry=self.action_registry,
            safety_manager=self.safety_manager,
            platform_adapter=self.ctx.platform,
            audit_repo=self.ctx.audit,
            event_bus=self.ctx.event_bus,
        )

        self._running = False
        self._diagnostic_loop_task: Optional[asyncio.Task] = None

    def _register_default_actions(self) -> None:
        self.action_registry.register(FlushDNSCacheAction())
        self.action_registry.register(
            SwitchDNSResolverAction(fallback_resolvers=self.config.probing.dns_fallback_resolvers)
        )
        self.action_registry.register(RenewIPLeaseAction())

    async def start(self) -> None:
        """Start the autonomous network guardian loops."""
        if self._running:
            return
        self._running = True
        logger.info("Starting NetGuard AI Autonomous System (Mode: %s)...", self.orchestrator.mode.value)

        # Start Observability Probes
        await self.observability.start()

        # Start Continuous Diagnostic & Healing Loop
        self._diagnostic_loop_task = asyncio.create_task(
            self._continuous_evaluation_loop(), name="netguard_eval_loop"
        )
        logger.info("NetGuard AI is now actively guarding the network.")

    async def stop(self) -> None:
        """Gracefully shutdown all monitoring and decision loops."""
        if not self._running:
            return
        self._running = False
        logger.info("Stopping NetGuard AI...")

        if self._diagnostic_loop_task:
            self._diagnostic_loop_task.cancel()
            try:
                await self._diagnostic_loop_task
            except asyncio.CancelledError:
                pass

        await self.observability.stop()
        self.ctx.event_bus.shutdown()
        logger.info("NetGuard AI stopped cleanly.")

    async def step(self) -> Optional[Diagnosis]:
        """Executes a single end-to-end evaluation cycle: Probe -> Diagnose -> Remediate."""
        # 1. Run single sample cycle on all probes
        await self.observability.run_single_cycle()

        # 2. Gather sliding windows
        windows = {m: self.observability.get_sliding_window(m) for m in self.observability._sliding_windows.keys()}

        # 3. Diagnose
        diagnosis = await self.diagnosis.evaluate_windows(windows)

        # 4. Autonomous Remediation if needed
        if diagnosis and diagnosis.auto_remediation_permitted:
            await self.orchestrator.handle_diagnosis(diagnosis)

        return diagnosis

    async def _continuous_evaluation_loop(self) -> None:
        """Periodic background evaluation loop."""
        eval_interval = min(self.config.probing.gateway_interval_sec * 2, 2.0)
        while self._running:
            try:
                await asyncio.sleep(eval_interval)
                windows = {m: self.observability.get_sliding_window(m) for m in self.observability._sliding_windows.keys()}
                diagnosis = await self.diagnosis.evaluate_windows(windows)
                if diagnosis and diagnosis.auto_remediation_permitted:
                    await self.orchestrator.handle_diagnosis(diagnosis)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error in continuous evaluation loop: %s", exc, exc_info=True)


def create_application(config_path: Optional[str] = None) -> NetGuardApplication:
    """Factory helper to bootstrap and instantiate NetGuardApplication."""
    ctx = bootstrap_application(config_path=config_path)
    return NetGuardApplication(ctx)
