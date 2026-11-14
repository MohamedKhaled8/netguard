"""Incident Repository for persisting and querying diagnostic assessments."""

from __future__ import annotations
import json
import uuid
from datetime import datetime
from typing import List, Optional
from app.core.models.metrics import Diagnosis, ProbableCause, DiagnosisSeverity, Evidence, MetricType
from app.storage.database import DatabaseManager


class IncidentRepository:
    """Handles CRUD queries for diagnostic incidents."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    def save(self, diagnosis: Diagnosis) -> str:
        inc_id = diagnosis.id or str(uuid.uuid4())
        query = """
        INSERT INTO incidents (
            id, timestamp, probable_cause, confidence, severity, explanation,
            auto_remediation_permitted, evidence_json, actions_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        evidence_dicts = [e.model_dump(mode="json") for e in diagnosis.supporting_evidence]
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                query,
                (
                    inc_id,
                    diagnosis.timestamp.isoformat(),
                    diagnosis.probable_cause.value,
                    diagnosis.confidence,
                    diagnosis.severity.value,
                    diagnosis.explanation,
                    1 if diagnosis.auto_remediation_permitted else 0,
                    json.dumps(evidence_dicts),
                    json.dumps(diagnosis.recommended_actions),
                ),
            )
            conn.commit()
            return inc_id

    def get_recent(self, limit: int = 20) -> List[Diagnosis]:
        query = """
        SELECT id, timestamp, probable_cause, confidence, severity, explanation,
               auto_remediation_permitted, evidence_json, actions_json
        FROM incidents
        ORDER BY timestamp DESC
        LIMIT ?;
        """
        results: List[Diagnosis] = []
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (limit,))
            for row in cur.fetchall():
                ev_list = []
                if row["evidence_json"]:
                    for item in json.loads(row["evidence_json"]):
                        item["metric_type"] = MetricType(item["metric_type"])
                        item["timestamp"] = datetime.fromisoformat(item["timestamp"])
                        ev_list.append(Evidence(**item))
                actions = json.loads(row["actions_json"]) if row["actions_json"] else []
                results.append(
                    Diagnosis(
                        id=row["id"],
                        timestamp=datetime.fromisoformat(row["timestamp"]),
                        probable_cause=ProbableCause(row["probable_cause"]),
                        confidence=row["confidence"],
                        severity=DiagnosisSeverity(row["severity"]),
                        explanation=row["explanation"] or "",
                        auto_remediation_permitted=bool(row["auto_remediation_permitted"]),
                        supporting_evidence=ev_list,
                        recommended_actions=actions,
                    )
                )
        return results
