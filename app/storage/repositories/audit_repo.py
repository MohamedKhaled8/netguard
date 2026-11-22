"""Audit Repository for persisting and querying remediation action history."""

from __future__ import annotations
import json
import uuid
from datetime import datetime, date, timedelta
from typing import List, Optional
from app.core.models.metrics import ActionExecutionRecord, ActionExecutionStatus, RiskLevel, ActionClassification
from app.storage.database import DatabaseManager


class AuditRepository:
    """Handles CRUD queries for remediation audit trails."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    def save(self, record: ActionExecutionRecord) -> str:
        rec_id = record.id or str(uuid.uuid4())
        cls_val = getattr(record, "action_classification", ActionClassification.CORRECTIVE_ACTION)
        cls_str = cls_val.value if hasattr(cls_val, "value") else str(cls_val)
        query = """
        INSERT INTO actions_audit (
            id, action_id, action_name, timestamp, risk_level, trigger_diagnosis_id,
            pre_remedy_metrics, post_remedy_metrics, status, execution_duration_ms,
            verification_duration_ms, error_message, rollback_performed, rollback_success,
            action_classification
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
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
                    cls_str,
                ),
            )
            conn.commit()
            return rec_id

    def _row_to_record(self, row: Any) -> ActionExecutionRecord:
        cls_val = ActionClassification.CORRECTIVE_ACTION
        try:
            if "action_classification" in row.keys() and row["action_classification"]:
                cls_val = ActionClassification(row["action_classification"])
        except Exception:
            pass
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
            action_classification=cls_val,
        )

    def get_recent(self, limit: int = 50) -> List[ActionExecutionRecord]:
        query = """
        SELECT id, action_id, action_name, timestamp, risk_level, trigger_diagnosis_id,
               pre_remedy_metrics, post_remedy_metrics, status, execution_duration_ms,
               verification_duration_ms, error_message, rollback_performed, rollback_success,
               action_classification
        FROM actions_audit
        ORDER BY timestamp DESC
        LIMIT ?;
        """
        results: List[ActionExecutionRecord] = []
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (limit,))
            for row in cur.fetchall():
                results.append(self._row_to_record(row))
        return results

    def get_by_date(self, target_date: date) -> List[ActionExecutionRecord]:
        """Queries actions occurring on a specific date in local time."""
        start_local = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0).astimezone()
        end_local = start_local + timedelta(days=1)
        start_search = (start_local - timedelta(days=1)).isoformat()[:10]
        end_search = (end_local + timedelta(days=1)).isoformat()[:10] + "T23:59:59"
        target_date_str = target_date.isoformat()

        query = """
        SELECT id, action_id, action_name, timestamp, risk_level, trigger_diagnosis_id,
               pre_remedy_metrics, post_remedy_metrics, status, execution_duration_ms,
               verification_duration_ms, error_message, rollback_performed, rollback_success,
               action_classification
        FROM actions_audit
        WHERE timestamp >= ? AND timestamp <= ?
          AND strftime('%Y-%m-%d', case when timestamp like '%+%' or timestamp like '%Z' then datetime(timestamp, 'localtime') else datetime(timestamp) end) = ?
        ORDER BY timestamp DESC;
        """
        results: List[ActionExecutionRecord] = []
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (start_search, end_search, target_date_str))
            for row in cur.fetchall():
                results.append(self._row_to_record(row))
        return results

    def get_by_id(self, record_id: str) -> Optional[ActionExecutionRecord]:
        query = """
        SELECT id, action_id, action_name, timestamp, risk_level, trigger_diagnosis_id,
               pre_remedy_metrics, post_remedy_metrics, status, execution_duration_ms,
               verification_duration_ms, error_message, rollback_performed, rollback_success,
               action_classification
        FROM actions_audit
        WHERE id = ?;
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (record_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_record(row)

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

    def prune_older_than(self, days: int) -> int:
        """Delete audit records older than specified retention days."""
        if days < 1:
            raise ValueError(f"Retention days must be >= 1, got {days}")
        from datetime import timezone, timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM actions_audit WHERE timestamp < ?;", (cutoff,))
            conn.commit()
            return cur.rowcount

    def clear_all(self) -> int:
        """Clear all stored audit records."""
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM actions_audit;")
            conn.commit()
            return cur.rowcount
