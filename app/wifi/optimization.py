"""Sections 6, 14, 15, 16 & 17 Central Automated Optimization Engine, Verification, Rollback, and 11-State Action History."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.wifi.coordinator import DiagnosticCoordinator
from app.wifi.models import (
    BeforeAfterComparison,
    BeforeAfterSnapshot,
    FullChannelAnalysisReport,
    MetricDelta,
    NetworkDiagnosticsReport,
    RouterApplyResult,
    RouterChangeProposal,
    RouterConfigurationSnapshot,
    WifiInterfaceTelemetry,
    utc_now,
)
from app.wifi.router.adapters.base import IRouterAdapter
from app.wifi.router.models_config import sanitize_setting_value


class OptimizationMode(str, Enum):
    """Section 15 required automation operating modes."""

    MONITOR_AND_DIAGNOSE = "MONITOR AND DIAGNOSE"
    APPROVAL_REQUIRED = "APPROVAL REQUIRED"
    AUTHORIZED_AUTO_OPTIMIZATION = "AUTHORIZED AUTO-OPTIMIZATION"


class ActionLifecycleState(str, Enum):
    """Section 16 required 11 action/audit lifecycle states."""

    DETECTED = "DETECTED"
    ANALYZING = "ANALYZING"
    RECOMMENDED = "RECOMMENDED"
    WAITING_FOR_APPROVAL = "WAITING FOR APPROVAL"
    APPLYING = "APPLYING"
    VERIFYING = "VERIFYING"
    SUCCESSFULLY_VERIFIED = "SUCCESSFULLY VERIFIED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED BACK"
    UNSUPPORTED = "UNSUPPORTED"
    PARTIALLY_COMPLETED = "PARTIALLY COMPLETED"


class ActionHistoryEntry(BaseModel):
    action_id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    category: str
    title: str
    target_layer: str  # "router" | "windows_local" | "manual"
    reason: str
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    before_summary: str = ""
    after_summary: str = ""
    verification_result: str = ""
    state: ActionLifecycleState = ActionLifecycleState.DETECTED
    mode_used: OptimizationMode = OptimizationMode.APPROVAL_REQUIRED
    rollback_available: bool = False
    proposal_json: Optional[str] = None
    meaningful_improvement: Optional[bool] = None


class ActionHistoryStore:
    """Thread-safe local SQLite store tracking optimization lifecycle and rollback metadata (never stores secrets)."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = Path(db_path or Path("data") / "netguard_wifi_actions.db")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS action_history (
                    action_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    target_layer TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    previous_value TEXT,
                    new_value TEXT,
                    before_summary TEXT,
                    after_summary TEXT,
                    verification_result TEXT,
                    state TEXT NOT NULL,
                    mode_used TEXT NOT NULL,
                    rollback_available INTEGER NOT NULL,
                    proposal_json TEXT,
                    meaningful_improvement INTEGER
                )
                """
            )
            conn.commit()

    def record(self, entry: ActionHistoryEntry) -> ActionHistoryEntry:
        clean_prev, _ = sanitize_setting_value("previous_value", entry.previous_value)
        clean_new, _ = sanitize_setting_value("new_value", entry.new_value)
        now = utc_now()
        entry.updated_at = now
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO action_history (
                    action_id, created_at, updated_at, category, title, target_layer, reason,
                    previous_value, new_value, before_summary, after_summary, verification_result,
                    state, mode_used, rollback_available, proposal_json, meaningful_improvement
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(action_id) DO UPDATE SET
                    updated_at=excluded.updated_at,
                    previous_value=excluded.previous_value,
                    new_value=excluded.new_value,
                    before_summary=excluded.before_summary,
                    after_summary=excluded.after_summary,
                    verification_result=excluded.verification_result,
                    state=excluded.state,
                    mode_used=excluded.mode_used,
                    rollback_available=excluded.rollback_available,
                    proposal_json=excluded.proposal_json,
                    meaningful_improvement=excluded.meaningful_improvement
                """,
                (
                    entry.action_id,
                    entry.created_at.isoformat(),
                    now.isoformat(),
                    entry.category,
                    entry.title,
                    entry.target_layer,
                    entry.reason,
                    clean_prev if entry.previous_value is not None else None,
                    clean_new if entry.new_value is not None else None,
                    entry.before_summary,
                    entry.after_summary,
                    entry.verification_result,
                    entry.state.value,
                    entry.mode_used.value,
                    1 if entry.rollback_available else 0,
                    entry.proposal_json,
                    None if entry.meaningful_improvement is None else (1 if entry.meaningful_improvement else 0),
                ),
            )
            conn.commit()
        return entry

    def list_recent(self, limit: int = 50) -> List[ActionHistoryEntry]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM action_history ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        out: List[ActionHistoryEntry] = []
        for r in rows:
            imp_raw = r["meaningful_improvement"]
            out.append(
                ActionHistoryEntry(
                    action_id=r["action_id"],
                    created_at=datetime.fromisoformat(r["created_at"]),
                    updated_at=datetime.fromisoformat(r["updated_at"]),
                    category=r["category"],
                    title=r["title"],
                    target_layer=r["target_layer"],
                    reason=r["reason"],
                    previous_value=r["previous_value"],
                    new_value=r["new_value"],
                    before_summary=r["before_summary"] or "",
                    after_summary=r["after_summary"] or "",
                    verification_result=r["verification_result"] or "",
                    state=ActionLifecycleState(r["state"]),
                    mode_used=OptimizationMode(r["mode_used"]),
                    rollback_available=bool(r["rollback_available"]),
                    proposal_json=r["proposal_json"],
                    meaningful_improvement=None if imp_raw is None else bool(imp_raw),
                )
            )
        return out

    def get(self, action_id: str) -> Optional[ActionHistoryEntry]:
        with self._connect() as conn:
            r = conn.execute("SELECT * FROM action_history WHERE action_id = ?", (action_id,)).fetchone()
        if r is None:
            return None
        imp_raw = r["meaningful_improvement"]
        return ActionHistoryEntry(
            action_id=r["action_id"],
            created_at=datetime.fromisoformat(r["created_at"]),
            updated_at=datetime.fromisoformat(r["updated_at"]),
            category=r["category"],
            title=r["title"],
            target_layer=r["target_layer"],
            reason=r["reason"],
            previous_value=r["previous_value"],
            new_value=r["new_value"],
            before_summary=r["before_summary"] or "",
            after_summary=r["after_summary"] or "",
            verification_result=r["verification_result"] or "",
            state=ActionLifecycleState(r["state"]),
            mode_used=OptimizationMode(r["mode_used"]),
            rollback_available=bool(r["rollback_available"]),
            proposal_json=r["proposal_json"],
            meaningful_improvement=None if imp_raw is None else bool(imp_raw),
        )


class ConfigurationBackupService:
    """Captures sanitized pre-change router and local baseline snapshots."""

    def __init__(self) -> None:
        self._backups: Dict[str, Dict[str, Any]] = {}

    def save_backup(
        self,
        backup_id: str,
        *,
        proposal: RouterChangeProposal,
        router_snapshot: Optional[RouterConfigurationSnapshot] = None,
    ) -> Dict[str, Any]:
        payload = {
            "backup_id": backup_id,
            "captured_at": utc_now().isoformat(),
            "proposal_id": proposal.proposal_id,
            "category": proposal.category,
            "target_field": proposal.target_field,
            "band": proposal.band,
            "previous_value": sanitize_setting_value(proposal.target_field, proposal.current_value)[0],
            "router_radios": {
                b: {"channel": r.channel, "width": r.channel_width}
                for b, r in (router_snapshot.radios.items() if router_snapshot else {})
            },
            "router_dns": list(router_snapshot.dns_servers) if router_snapshot else [],
            "router_qos_enabled": router_snapshot.qos_enabled if router_snapshot else None,
        }
        self._backups[backup_id] = payload
        return payload

    def get_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        return self._backups.get(backup_id)


class RouterConfigurationWriter:
    """Executes supported router changes safely with explicit approval checks."""

    def apply(
        self,
        *,
        adapter: Optional[IRouterAdapter],
        proposal: RouterChangeProposal,
        explicit_user_approval: bool,
    ) -> RouterApplyResult:
        if adapter is None or not adapter.is_authenticated:
            return RouterApplyResult(
                proposal_id=proposal.proposal_id,
                success=False,
                message="لم يتم المصادقة مع الراوتر أو المحول غير متصل؛ يتعذر الكتابة المباشرة.",
            )
        return adapter.safe_apply_change(proposal, explicit_user_approval=explicit_user_approval)


class ConfigurationVerificationService:
    """Evaluates Before vs After telemetry & network stability to separate real improvements from noise."""

    @staticmethod
    def compare_before_after(
        before: BeforeAfterSnapshot,
        after: BeforeAfterSnapshot,
    ) -> BeforeAfterComparison:
        from app.wifi.reporting import BeforeAfterReportingService

        return BeforeAfterReportingService().compare(before, after)


class RollbackManager:
    """Restores previous router or local configuration from ActionHistoryEntry."""

    def __init__(self, history: ActionHistoryStore, writer: Optional[RouterConfigurationWriter] = None) -> None:
        self._history = history
        self._writer = writer or RouterConfigurationWriter()

    def rollback_action(
        self,
        *,
        action_id: str,
        adapter: Optional[IRouterAdapter] = None,
    ) -> Tuple[bool, str]:
        entry = self._history.get(action_id)
        if entry is None:
            return False, f"لم يتم العثور على سجل الإجراء '{action_id}'."
        if not entry.rollback_available or entry.previous_value is None:
            return False, "لا تتوفر قيمة سابقة قابلة للاسترجاع لهذا الإجراء."
        if entry.target_layer == "router" and entry.proposal_json:
            prop = RouterChangeProposal.model_validate_json(entry.proposal_json)
            rb_prop = prop.model_copy(
                update={
                    "proposed_value": entry.previous_value,
                    "current_value": entry.new_value,
                    "title": f"تراجع: {prop.title}",
                }
            )
            res = self._writer.apply(adapter=adapter, proposal=rb_prop, explicit_user_approval=True)
            if res.success:
                entry.state = ActionLifecycleState.ROLLED_BACK
                entry.rollback_available = False
                entry.verification_result = f"تم التراجع واستعادة القيمة السابقة ({entry.previous_value})."
                self._history.record(entry)
                return True, entry.verification_result
            return False, f"فشل التراجع عبر الراوتر: {res.message}"
        return False, "التراجع التلقائي يتطلب جلسة محول راوتر مصادق عليها."


class OptimizationPlanner:
    """Orchestrates safe auto-optimization, 14-step Wi-Fi channel workflow, 3 modes, and verification."""

    HIGH_RISK_OR_SECURITY_CATEGORIES = frozenset({"security_mode", "firewall", "nat_port_forwarding", "dhcp", "wan"})
    REVERSIBLE_LOW_RISK_CATEGORIES = frozenset({"wifi_channel", "channel_width", "dns"})

    def __init__(
        self,
        *,
        coordinator: Optional[DiagnosticCoordinator] = None,
        history: Optional[ActionHistoryStore] = None,
        backup_service: Optional[ConfigurationBackupService] = None,
        writer: Optional[RouterConfigurationWriter] = None,
        verifier: Optional[ConfigurationVerificationService] = None,
        rollback_manager: Optional[RollbackManager] = None,
        auto_allowed_categories: Optional[set[str]] = None,
    ) -> None:
        self._coordinator = coordinator
        self.history = history or ActionHistoryStore()
        self.backup = backup_service or ConfigurationBackupService()
        self.writer = writer or RouterConfigurationWriter()
        self.verifier = verifier or ConfigurationVerificationService()
        self.rollback = rollback_manager or RollbackManager(self.history, self.writer)
        self.mode: OptimizationMode = OptimizationMode.APPROVAL_REQUIRED
        self.auto_allowed_categories: set[str] = (
            set(auto_allowed_categories)
            if auto_allowed_categories is not None
            else {"wifi_channel", "dns"}
        )

    def evaluate_proposal_policy(
        self,
        proposal: RouterChangeProposal,
        *,
        explicit_user_approval: bool = False,
    ) -> Tuple[bool, str]:
        """Enforce the 3 Operating Modes & safety guardrails."""
        if self.mode == OptimizationMode.MONITOR_AND_DIAGNOSE:
            return False, "الوضع الحالي هو 'المراقبة والتشخيص فقط' (MONITOR AND DIAGNOSE) — يُحظر تنفيذ أي تغييرات."

        if not proposal.supported_by_adapter:
            return False, "الميزة غير مدعومة برمجياً على محول هذا الراوتر."

        if proposal.requires_reconnect_warning and self._coordinator is not None:
            active, reason = self._coordinator.is_meeting_active()
            if active:
                return False, f"محجوب مؤقتاً أثناء الاجتماع النشط لأن التغيير سيفصل Wi-Fi لحظياً: {reason}"

        if self.mode == OptimizationMode.APPROVAL_REQUIRED:
            if not explicit_user_approval:
                return False, "يتطلب موافقة المستخدم الصريحة في وضع APPROVAL REQUIRED."
            return True, "تمت الموافقة الصريحة."

        # AUTHORIZED AUTO-OPTIMIZATION mode: strict bounds still apply
        if proposal.category in self.HIGH_RISK_OR_SECURITY_CATEGORIES or proposal.risk_level == "high":
            if not explicit_user_approval:
                return False, "التغييرات الأمنية أو عالية الخطورة تتطلب تأكيداً صريحاً حتى في وضع التحسين التلقائي."
        if proposal.category not in self.auto_allowed_categories and not explicit_user_approval:
            return False, f"فئة '{proposal.category}' غير مفعّلة للتشغيل التلقائي بدون موافقة."
        return True, "مسموح بالتنفيذ التلقائي الآمن والقابل للتراجع."

    def execute_proposal(
        self,
        *,
        adapter: Optional[IRouterAdapter],
        proposal: RouterChangeProposal,
        explicit_user_approval: bool = False,
    ) -> ActionHistoryEntry:
        action_id = f"act_{uuid.uuid4().hex[:8]}"
        entry = ActionHistoryEntry(
            action_id=action_id,
            category=proposal.category,
            title=proposal.title,
            target_layer="router" if proposal.supported_by_adapter else "manual",
            reason=proposal.reason,
            previous_value=proposal.current_value,
            new_value=proposal.proposed_value,
            state=ActionLifecycleState.DETECTED,
            mode_used=self.mode,
            proposal_json=proposal.model_dump_json(),
        )
        self.history.record(entry)

        if not proposal.supported_by_adapter:
            entry.state = ActionLifecycleState.UNSUPPORTED
            entry.verification_result = "غير مدعوم آلياً في المحول الحالي؛ يلزم التطبيق اليدوي في صفحة الراوتر."
            return self.history.record(entry)

        allowed, policy_msg = self.evaluate_proposal_policy(
            proposal, explicit_user_approval=explicit_user_approval
        )
        if not allowed:
            entry.state = ActionLifecycleState.WAITING_FOR_APPROVAL
            entry.verification_result = policy_msg
            return self.history.record(entry)

        entry.state = ActionLifecycleState.APPLYING
        self.history.record(entry)

        self.backup.save_backup(action_id, proposal=proposal)
        apply_res = self.writer.apply(
            adapter=adapter,
            proposal=proposal,
            explicit_user_approval=True,
        )

        entry.state = ActionLifecycleState.VERIFYING
        self.history.record(entry)

        if apply_res.success and apply_res.readback_verified:
            entry.state = ActionLifecycleState.SUCCESSFULLY_VERIFIED
            entry.rollback_available = True
            entry.verification_result = apply_res.message
        elif apply_res.rolled_back:
            entry.state = ActionLifecycleState.ROLLED_BACK
            entry.rollback_available = False
            entry.verification_result = apply_res.message
        elif apply_res.success:
            entry.state = ActionLifecycleState.PARTIALLY_COMPLETED
            entry.rollback_available = True
            entry.verification_result = apply_res.message
        else:
            entry.state = ActionLifecycleState.FAILED
            entry.rollback_available = False
            entry.verification_result = apply_res.message

        return self.history.record(entry)

    async def optimize_wifi_channel_workflow(
        self,
        *,
        adapter: Optional[IRouterAdapter],
        proposal: RouterChangeProposal,
        explicit_user_approval: bool,
        before_snapshot: Optional[BeforeAfterSnapshot] = None,
        wait_reconnect_fn: Optional[Callable[[], Awaitable[bool]]] = None,
        collect_after_fn: Optional[Callable[[], Awaitable[BeforeAfterSnapshot]]] = None,
        reconnect_timeout_s: float = 15.0,
    ) -> Tuple[ActionHistoryEntry, Optional[BeforeAfterComparison]]:
        """Execute full Section 6 14-step Wi-Fi channel optimization & disconnect recovery workflow."""
        action_id = f"chopt_{uuid.uuid4().hex[:8]}"
        entry = ActionHistoryEntry(
            action_id=action_id,
            category=proposal.category,
            title=proposal.title,
            target_layer="router" if proposal.supported_by_adapter else "manual",
            reason=proposal.reason,
            previous_value=proposal.current_value,
            new_value=proposal.proposed_value,
            before_summary=before_snapshot.label if before_snapshot else "",
            state=ActionLifecycleState.ANALYZING,
            mode_used=self.mode,
            proposal_json=proposal.model_dump_json(),
        )
        self.history.record(entry)

        allowed, policy_msg = self.evaluate_proposal_policy(
            proposal, explicit_user_approval=explicit_user_approval
        )
        if not proposal.supported_by_adapter:
            entry.state = ActionLifecycleState.UNSUPPORTED
            entry.verification_result = policy_msg
            return self.history.record(entry), None
        if not allowed:
            entry.state = ActionLifecycleState.WAITING_FOR_APPROVAL
            entry.verification_result = policy_msg
            return self.history.record(entry), None

        if adapter is None or not adapter.is_authenticated:
            entry.state = ActionLifecycleState.FAILED
            entry.verification_result = "يلزم تسجيل الدخول المصادق للراوتر قبل تغيير القناة."
            return self.history.record(entry), None

        # Step 7: Save backup snapshot
        entry.state = ActionLifecycleState.APPLYING
        self.history.record(entry)
        try:
            pre_cfg = await asyncio.to_thread(adapter.read_config)
        except Exception:
            pre_cfg = None
        self.backup.save_backup(action_id, proposal=proposal, router_snapshot=pre_cfg)

        # Step 8: Apply channel change
        apply_res = await asyncio.to_thread(
            adapter.safe_apply_change,
            proposal,
            explicit_user_approval=True,
        )

        # Step 9-10: Handle temporary Wi-Fi disconnect and wait for reconnection if needed
        if wait_reconnect_fn is not None:
            deadline = time.monotonic() + reconnect_timeout_s
            reconnected = False
            while time.monotonic() < deadline:
                if await wait_reconnect_fn():
                    reconnected = True
                    break
                await asyncio.sleep(0.5)
            if not reconnected:
                entry.state = ActionLifecycleState.PARTIALLY_COMPLETED
                entry.verification_result = (
                    "تم إرسال أمر تغيير القناة ولكن لم يعد اتصال Wi-Fi خلال المهلة المحددة."
                )
                return self.history.record(entry), None

        entry.state = ActionLifecycleState.VERIFYING
        self.history.record(entry)

        if not apply_res.success:
            entry.state = ActionLifecycleState.ROLLED_BACK if apply_res.rolled_back else ActionLifecycleState.FAILED
            entry.verification_result = apply_res.message
            return self.history.record(entry), None

        # Step 11-13: Re-test after change and compare before vs after
        comp: Optional[BeforeAfterComparison] = None
        if before_snapshot is not None and collect_after_fn is not None:
            try:
                after_snap = await collect_after_fn()
                comp = self.verifier.compare_before_after(before_snapshot, after_snap)
                entry.after_summary = comp.summary or comp.overall_verdict
                any_degraded = any(d.verdict == "degraded" for d in comp.deltas)
                any_improved = any(d.verdict == "improved" for d in comp.deltas)
                entry.meaningful_improvement = any_improved and not any_degraded
                if any_degraded and not any_improved and entry.previous_value:
                    # Step 14: Auto-rollback on clear regression
                    rb_prop = proposal.model_copy(update={"proposed_value": entry.previous_value})
                    rb_res = await asyncio.to_thread(
                        adapter.safe_apply_change, rb_prop, explicit_user_approval=True
                    )
                    entry.state = ActionLifecycleState.ROLLED_BACK if rb_res.success else ActionLifecycleState.PARTIALLY_COMPLETED
                    entry.verification_result = f"تراجع تلقائي لعدم تحسن القياسات: {entry.after_summary}"
                    return self.history.record(entry), comp
            except Exception as exc:
                entry.after_summary = f"تعذر القياس البعدي الكامل: {exc}"

        entry.state = ActionLifecycleState.SUCCESSFULLY_VERIFIED
        entry.rollback_available = True
        entry.verification_result = apply_res.message
        return self.history.record(entry), comp
