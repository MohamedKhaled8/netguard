"""Incident Repository for persisting, correlating, and lifecycle-tracking diagnostic assessments."""

from __future__ import annotations
import json
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Tuple, Any
from app.core.models.metrics import (
    Diagnosis,
    ProbableCause,
    DiagnosisSeverity,
    Evidence,
    MetricType,
    IncidentLifecycleState,
    IncidentResolutionType,
    CauseClassification,
)
from app.storage.database import DatabaseManager


class IncidentRepository:
    """Handles CRUD, correlation, deduplication, and lifecycle transitions for diagnostic incidents."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    @staticmethod
    def compute_fingerprint(diagnosis: Diagnosis) -> str:
        """Derive deterministic fingerprint for correlating recurring or ongoing incidents (Item 4)."""
        comp = diagnosis.affected_component or "network"
        return f"{diagnosis.probable_cause.value}:{comp}"

    def save(self, diagnosis: Diagnosis) -> str:
        """Save diagnosis, automatically correlating ongoing incidents to prevent duplicates (Item 4 & 12)."""
        inc_id, _ = self.save_or_update(diagnosis)
        return inc_id

    def save_or_update(
        self,
        diagnosis: Diagnosis,
        correlation_window_sec: float = 300.0,
    ) -> Tuple[str, bool]:
        """Correlate ongoing incidents within window, updating evidence & counts or inserting new row."""
        fingerprint = diagnosis.fingerprint or self.compute_fingerprint(diagnosis)
        diagnosis.fingerprint = fingerprint

        now_dt = diagnosis.timestamp or datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        cutoff_iso = (now_dt - timedelta(seconds=correlation_window_sec)).isoformat()

        # 1. Search for active ongoing incident with matching fingerprint within window
        unresolved_statuses = (
            IncidentLifecycleState.DETECTED.value,
            IncidentLifecycleState.INVESTIGATING.value,
            IncidentLifecycleState.DIAGNOSED.value,
            IncidentLifecycleState.AWAITING_APPROVAL.value,
            IncidentLifecycleState.REMEDIATING.value,
            IncidentLifecycleState.VERIFYING_RECOVERY.value,
            IncidentLifecycleState.UNRESOLVED.value,
        )
        placeholders = ",".join("?" for _ in unresolved_statuses)

        find_query = f"""
        SELECT id, first_detected, last_observed, occurrence_count, status
        FROM incidents
        WHERE fingerprint = ?
          AND (last_observed >= ? OR timestamp >= ?)
          AND status IN ({placeholders})
        ORDER BY last_observed DESC
        LIMIT 1;
        """
        params = [fingerprint, cutoff_iso, cutoff_iso] + list(unresolved_statuses)

        evidence_dicts = [e.model_dump(mode="json") for e in diagnosis.supporting_evidence]
        ev_json = json.dumps(evidence_dicts)
        actions_json = json.dumps(diagnosis.recommended_actions)

        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(find_query, params)
            existing = cur.fetchone()

            if existing:
                # Update existing ongoing incident
                inc_id = existing["id"]
                new_count = (existing["occurrence_count"] or 1) + 1
                update_query = """
                UPDATE incidents
                SET last_observed = ?,
                    occurrence_count = ?,
                    confidence = MAX(confidence, ?),
                    severity = ?,
                    explanation = ?,
                    evidence_json = ?,
                    actions_json = ?
                WHERE id = ?;
                """
                cur.execute(
                    update_query,
                    (
                        now_iso,
                        new_count,
                        diagnosis.confidence,
                        diagnosis.severity.value,
                        diagnosis.explanation,
                        ev_json,
                        actions_json,
                        inc_id,
                    ),
                )
                conn.commit()
                diagnosis.id = inc_id
                diagnosis.occurrence_count = new_count
                return inc_id, False

            # Insert new incident
            inc_id = diagnosis.id or str(uuid.uuid4())
            diagnosis.id = inc_id
            if "first_detected" not in getattr(diagnosis, "model_fields_set", set()) and diagnosis.timestamp:
                first_detected_iso = diagnosis.timestamp.isoformat()
            else:
                first_detected_iso = (diagnosis.first_detected or diagnosis.timestamp or now_dt).isoformat()

            if "last_observed" not in getattr(diagnosis, "model_fields_set", set()) and diagnosis.timestamp:
                last_observed_iso = diagnosis.timestamp.isoformat()
            else:
                last_observed_iso = (diagnosis.last_observed or diagnosis.timestamp or now_dt).isoformat()

            insert_query = """
            INSERT INTO incidents (
                id, timestamp, probable_cause, confidence, severity, explanation,
                auto_remediation_permitted, evidence_json, actions_json,
                fingerprint, first_detected, last_observed, occurrence_count,
                status, resolution_type, affected_component, cause_classification,
                action_record_id, resolved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """
            cur.execute(
                insert_query,
                (
                    inc_id,
                    first_detected_iso,
                    diagnosis.probable_cause.value,
                    diagnosis.confidence,
                    diagnosis.severity.value,
                    diagnosis.explanation,
                    1 if diagnosis.auto_remediation_permitted else 0,
                    ev_json,
                    actions_json,
                    fingerprint,
                    first_detected_iso,
                    last_observed_iso,
                    diagnosis.occurrence_count or 1,
                    diagnosis.status.value,
                    diagnosis.resolution_type.value,
                    diagnosis.affected_component or "network",
                    diagnosis.cause_classification.value,
                    diagnosis.action_record_id,
                    diagnosis.resolved_at.isoformat() if diagnosis.resolved_at else None,
                ),
            )
            conn.commit()
            return inc_id, True

    def transition_state(
        self,
        incident_id: str,
        new_state: IncidentLifecycleState,
        resolution_type: Optional[IncidentResolutionType] = None,
        action_record_id: Optional[str] = None,
        notes: str = "",
    ) -> bool:
        """Enforces valid incident lifecycle state transitions without skipping verification (Item 3)."""
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT status, resolution_type FROM incidents WHERE id = ?;", (incident_id,))
            row = cur.fetchone()
            if not row:
                return False

            now_iso = datetime.now(timezone.utc).isoformat()
            resolved_at = now_iso if new_state in (
                IncidentLifecycleState.RESOLVED,
                IncidentLifecycleState.NATURALLY_RECOVERED,
                IncidentLifecycleState.CLOSED,
            ) else None

            upd_query = """
            UPDATE incidents
            SET status = ?,
                resolution_type = COALESCE(?, resolution_type),
                action_record_id = COALESCE(?, action_record_id),
                resolved_at = COALESCE(?, resolved_at),
                last_observed = ?
            WHERE id = ?;
            """
            res_val = resolution_type.value if resolution_type else None
            cur.execute(upd_query, (new_state.value, res_val, action_record_id, resolved_at, now_iso, incident_id))
            conn.commit()
            return cur.rowcount > 0

    def get_by_id(self, incident_id: str) -> Optional[Diagnosis]:
        """Fetch single incident by unique ID."""
        query = """
        SELECT id, timestamp, probable_cause, confidence, severity, explanation,
               auto_remediation_permitted, evidence_json, actions_json,
               fingerprint, first_detected, last_observed, occurrence_count,
               status, resolution_type, affected_component, cause_classification,
               action_record_id, resolved_at
        FROM incidents
        WHERE id = ?;
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (incident_id,))
            row = cur.fetchone()
            if row:
                return self._row_to_diagnosis(row)
        return None

    def get_recent(self, limit: int = 20) -> List[Diagnosis]:
        query = """
        SELECT id, timestamp, probable_cause, confidence, severity, explanation,
               auto_remediation_permitted, evidence_json, actions_json,
               fingerprint, first_detected, last_observed, occurrence_count,
               status, resolution_type, affected_component, cause_classification,
               action_record_id, resolved_at
        FROM incidents
        ORDER BY last_observed DESC, timestamp DESC
        LIMIT ?;
        """
        results: List[Diagnosis] = []
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (limit,))
            for row in cur.fetchall():
                results.append(self._row_to_diagnosis(row))
        return results

    def get_by_date(self, target_date: date) -> List[Diagnosis]:
        """Queries incidents occurring on a specific date in local time."""
        start_local = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0).astimezone()
        end_local = start_local + timedelta(days=1)
        start_search = (start_local - timedelta(days=1)).isoformat()[:10]
        end_search = (end_local + timedelta(days=1)).isoformat()[:10] + "T23:59:59"
        target_date_str = target_date.isoformat()

        query = """
        SELECT id, timestamp, probable_cause, confidence, severity, explanation,
               auto_remediation_permitted, evidence_json, actions_json,
               fingerprint, first_detected, last_observed, occurrence_count,
               status, resolution_type, affected_component, cause_classification,
               action_record_id, resolved_at
        FROM incidents
        WHERE timestamp >= ? AND timestamp <= ?
          AND strftime('%Y-%m-%d', case when timestamp like '%+%' or timestamp like '%Z' then datetime(timestamp, 'localtime') else datetime(timestamp) end) = ?
        ORDER BY last_observed DESC, timestamp DESC;
        """
        results: List[Diagnosis] = []
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (start_search, end_search, target_date_str))
            for row in cur.fetchall():
                results.append(self._row_to_diagnosis(row))
        return results

    def _row_to_diagnosis(self, row: Any) -> Diagnosis:
        """Map SQLite row to validated Diagnosis object with lifecycle metadata."""
        ev_list = []
        if row["evidence_json"]:
            try:
                for item in json.loads(row["evidence_json"]):
                    item["metric_type"] = MetricType(item["metric_type"])
                    item["timestamp"] = datetime.fromisoformat(item["timestamp"])
                    ev_list.append(Evidence(**item))
            except Exception:
                pass

        actions = []
        if row["actions_json"]:
            try:
                actions = json.loads(row["actions_json"])
            except Exception:
                pass

        # Parse cause safely
        cause_val = row["probable_cause"]
        try:
            cause_enum = ProbableCause(cause_val)
        except ValueError:
            cause_enum = ProbableCause.UNKNOWN_ANOMALY

        # Parse status safely
        st_val = row["status"] if "status" in row.keys() and row["status"] else "diagnosed"
        try:
            st_enum = IncidentLifecycleState(st_val)
        except ValueError:
            st_enum = IncidentLifecycleState.DIAGNOSED

        # Parse resolution_type safely
        res_val = row["resolution_type"] if "resolution_type" in row.keys() and row["resolution_type"] else "diagnosed_only"
        try:
            res_enum = IncidentResolutionType(res_val)
        except ValueError:
            res_enum = IncidentResolutionType.DIAGNOSED_ONLY

        # Parse cause_classification safely
        cc_val = row["cause_classification"] if "cause_classification" in row.keys() and row["cause_classification"] else "probable_cause"
        try:
            cc_enum = CauseClassification(cc_val)
        except ValueError:
            cc_enum = CauseClassification.PROBABLE_CAUSE

        first_det = datetime.fromisoformat(row["first_detected"]) if ("first_detected" in row.keys() and row["first_detected"]) else datetime.fromisoformat(row["timestamp"])
        last_obs = datetime.fromisoformat(row["last_observed"]) if ("last_observed" in row.keys() and row["last_observed"]) else datetime.fromisoformat(row["timestamp"])
        res_at = datetime.fromisoformat(row["resolved_at"]) if ("resolved_at" in row.keys() and row["resolved_at"]) else None

        return Diagnosis(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            probable_cause=cause_enum,
            confidence=row["confidence"],
            severity=DiagnosisSeverity(row["severity"]),
            explanation=row["explanation"] or "",
            auto_remediation_permitted=bool(row["auto_remediation_permitted"]),
            supporting_evidence=ev_list,
            recommended_actions=actions,
            fingerprint=row["fingerprint"] if "fingerprint" in row.keys() and row["fingerprint"] else f"{cause_val}:network",
            first_detected=first_det,
            last_observed=last_obs,
            occurrence_count=row["occurrence_count"] if ("occurrence_count" in row.keys() and row["occurrence_count"]) else 1,
            status=st_enum,
            resolution_type=res_enum,
            affected_component=row["affected_component"] if "affected_component" in row.keys() and row["affected_component"] else "network",
            cause_classification=cc_enum,
            action_record_id=row["action_record_id"] if "action_record_id" in row.keys() else None,
            resolved_at=res_at,
        )

    def prune_older_than(self, days: int) -> int:
        """Delete incidents older than specified retention days."""
        if days < 1:
            raise ValueError(f"Retention days must be >= 1, got {days}")
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM incidents WHERE timestamp < ?;", (cutoff,))
            conn.commit()
            return cur.rowcount

    def clear_all(self) -> int:
        """Clear all stored incidents."""
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM incidents;")
            conn.commit()

    def prune_older_than(self, days: int) -> int:
        """Delete incidents older than specified retention days."""
        if days < 1:
            raise ValueError(f"Retention days must be >= 1, got {days}")
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM incidents WHERE timestamp < ?;", (cutoff,))
            conn.commit()
            return cur.rowcount

    def clear_all(self) -> int:
        """Clear all stored incidents."""
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM incidents;")
            conn.commit()
            return cur.rowcount
