"""Measurement Repository for persisting and querying telemetry samples."""

from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from app.core.models.metrics import Measurement, MetricType, ProbeStatus, MeasurementSource
from app.storage.database import DatabaseManager


class MeasurementRepository:
    """Handles CRUD queries for network measurements."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    def save(self, m: Measurement) -> int:
        query = """
        INSERT INTO measurements (
            timestamp, source, target_or_interface, metric_type,
            raw_value, normalized_value, unit, status, confidence, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        metadata_str = json.dumps(m.metadata) if m.metadata else None
        ts_str = m.timestamp.isoformat()
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                query,
                (
                    ts_str,
                    m.source.value,
                    m.target_or_interface,
                    m.metric_type.value,
                    m.raw_value,
                    m.normalized_value,
                    m.unit,
                    m.status.value,
                    m.confidence,
                    metadata_str,
                ),
            )
            conn.commit()
            return cur.lastrowid

    def get_latest_by_metric(self, metric_type: MetricType, limit: int = 10) -> List[Measurement]:
        query = """
        SELECT id, timestamp, source, target_or_interface, metric_type,
               raw_value, normalized_value, unit, status, confidence, metadata_json
        FROM measurements
        WHERE metric_type = ?
        ORDER BY id DESC
        LIMIT ?;
        """
        results: List[Measurement] = []
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (metric_type.value, limit))
            for row in cur.fetchall():
                results.append(self._row_to_measurement(row))
        return results

    def get_recent(self, limit: int = 50) -> List[Measurement]:
        query = """
        SELECT id, timestamp, source, target_or_interface, metric_type,
               raw_value, normalized_value, unit, status, confidence, metadata_json
        FROM measurements
        ORDER BY id DESC
        LIMIT ?;
        """
        results: List[Measurement] = []
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (limit,))
            for row in cur.fetchall():
                results.append(self._row_to_measurement(row))
        return results

    def prune_older_than(self, days: int) -> int:
        """Deletes measurements older than specified days, returning count of deleted rows."""
        if days < 1:
            raise ValueError(f"Retention days must be >= 1, got {days}")
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        query = "DELETE FROM measurements WHERE timestamp < ?;"
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (cutoff,))
            conn.commit()
            return cur.rowcount

    @staticmethod
    def _row_to_measurement(row: dict) -> Measurement:
        metadata = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
        return Measurement(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            source=MeasurementSource(row["source"]),
            target_or_interface=row["target_or_interface"],
            metric_type=MetricType(row["metric_type"]),
            raw_value=row["raw_value"],
            normalized_value=row["normalized_value"],
            unit=row["unit"],
            status=ProbeStatus(row["status"]),
            confidence=row["confidence"],
            metadata=metadata,
        )
