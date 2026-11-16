"""Audit Repository for persisting and querying remediation action history."""

from __future__ import annotations
import json
import uuid
from datetime import datetime
from typing import List, Optional
from app.core.models.metrics import ActionExecutionRecord, ActionExecutionStatus, RiskLevel
from app.storage.database import DatabaseManager


class AuditRepository:
    """Handles CRUD queries for remediation audit trails."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    def save(self, record: ActionExecutionRecord) -> str:
        rec_id = record.id or str(uuid.uuid4())
        query = """
        INSERT INTO actions_audit (
            id, action_id, action_name, timestamp, risk_level, trigger_diagnosis_id,
            pre_remedy_metrics, post_remedy_metrics, status, execution_duration_ms,
            verification_duration_ms, error_message, rollback_performed, rollback_success
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                query,
                (
                    rec_id,
                    record.action_id,
                    record.action_name,
                    record.timestamp.isoformat(),
                    record.risk_level.value,
                    record.trigger_diagnosis_id,
                    json.dumps(record.pre_remedy_metrics),
                    json.dumps(record.post_remedy_metrics),
                    record.status.value,
                    record.execution_duration_ms,
                    record.verification_duration_ms,
                    record.error_message,
                    1 if record.rollback_performed else 0,
                    1 if record.rollback_success else (0 if record.rollback_success is False else None),
                ),
            )
            conn.commit()
            return rec_id

    def get_recent(self, limit: int = 50) -> List[ActionExecutionRecord]:
        query = """
        SELECT id, action_id, action_name, timestamp, risk_level, trigger_diagnosis_id,
               pre_remedy_metrics, post_remedy_metrics, status, execution_duration_ms,
               verification_duration_ms, error_message, rollback_performed, rollback_success
        FROM actions_audit
        ORDER BY timestamp DESC
        LIMIT ?;
        """
        results: List[ActionExecutionRecord] = []
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (limit,))
            for row in cur.fetchall():
                results.append(
                    ActionExecutionRecord(
                        id=row["id"],
                        action_id=row["action_id"],
                        action_name=row["action_name"],
                        timestamp=datetime.fromisoformat(row["timestamp"]),
                        risk_level=RiskLevel(row["risk_level"]),
                        trigger_diagnosis_id=row["trigger_diagnosis_id"],
                        pre_remedy_metrics=json.loads(row["pre_remedy_metrics"] or "{}"),
                        post_remedy_metrics=json.loads(row["post_remedy_metrics"] or "{}"),
                        status=ActionExecutionStatus(row["status"]),
                        execution_duration_ms=row["execution_duration_ms"],
                        verification_duration_ms=row["verification_duration_ms"],
                        error_message=row["error_message"],
                        rollback_performed=bool(row["rollback_performed"]),
                        rollback_success=bool(row["rollback_success"]) if row["rollback_success"] is not None else None,
                    )
                )
        return results

    def get_by_id(self, record_id: str) -> Optional[ActionExecutionRecord]:
        query = """
        SELECT id, action_id, action_name, timestamp, risk_level, trigger_diagnosis_id,
               pre_remedy_metrics, post_remedy_metrics, status, execution_duration_ms,
               verification_duration_ms, error_message, rollback_performed, rollback_success
        FROM actions_audit
        WHERE id = ?;
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (record_id,))
            row = cur.fetchone()
            if not row:
                return None
            return ActionExecutionRecord(
                id=row["id"],
                action_id=row["action_id"],
                action_name=row["action_name"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                risk_level=RiskLevel(row["risk_level"]),
                trigger_diagnosis_id=row["trigger_diagnosis_id"],
                pre_remedy_metrics=json.loads(row["pre_remedy_metrics"] or "{}"),
                post_remedy_metrics=json.loads(row["post_remedy_metrics"] or "{}"),
                status=ActionExecutionStatus(row["status"]),
                execution_duration_ms=row["execution_duration_ms"],
                verification_duration_ms=row["verification_duration_ms"],
                error_message=row["error_message"],
                rollback_performed=bool(row["rollback_performed"]),
                rollback_success=bool(row["rollback_success"]) if row["rollback_success"] is not None else None,
            )

    def update_rollback(
        self,
        record_id: str,
        rollback_success: bool,
        error_message: Optional[str] = None,
    ) -> bool:
        query = """
        UPDATE actions_audit
        SET rollback_performed = 1,
            rollback_success = ?,
            status = ?,
            error_message = COALESCE(?, error_message)
        WHERE id = ?;
        """
        status = ActionExecutionStatus.ROLLED_BACK if rollback_success else ActionExecutionStatus.FAILED
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (1 if rollback_success else 0, status.value, error_message, record_id))
            conn.commit()
            return cur.rowcount > 0
