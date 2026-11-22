"""Measurement Repository for persisting and querying telemetry samples."""

from __future__ import annotations
import json
import threading
import time
from datetime import date, datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from app.core.models.metrics import Measurement, MetricType, ProbeStatus, MeasurementSource
from app.storage.database import DatabaseManager


class MeasurementRepository:
    """Handles CRUD queries for network measurements."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager
        self._batch_queue: List[Measurement] = []
        self._batch_lock = threading.Lock()
        self._last_flush = time.time()

    def save(self, m: Measurement) -> int:
        with self._batch_lock:
            self._batch_queue.append(m)
            self._counter = getattr(self, "_counter", 0) + 1
            assigned_id = self._counter
            should_flush = len(self._batch_queue) >= 15 or (time.time() - self._last_flush) >= 2.0

        if should_flush:
            self.flush()
        return assigned_id

    def flush(self) -> None:
        with self._batch_lock:
            if not self._batch_queue:
                return
            to_save = list(self._batch_queue)
            self._batch_queue.clear()
            self._last_flush = time.time()

        query = """
        INSERT INTO measurements (
            timestamp, source, target_or_interface, metric_type,
            raw_value, normalized_value, unit, status, confidence, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        rows = [
            (
                m.timestamp.isoformat(),
                m.source.value,
                m.target_or_interface,
                m.metric_type.value,
                m.raw_value,
                m.normalized_value,
                m.unit,
                m.status.value,
                m.confidence,
                json.dumps(m.metadata) if m.metadata else None,
            )
            for m in to_save
        ]
        with self.db.get_connection() as conn:
            conn.executemany(query, rows)
            conn.commit()

    def get_latest_by_metric(self, metric_type: MetricType, limit: int = 10) -> List[Measurement]:
        self.flush()
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
        self.flush()
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

    def downsample_to_aggregates(self, cutoff_timestamp: Optional[datetime] = None) -> int:
        """Downsample 1-second raw measurements into 1-minute aggregates (min/avg/max/p95, loss_rate)."""
        self.flush()
        if cutoff_timestamp is None:
            cutoff_timestamp = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        cutoff_str = cutoff_timestamp.isoformat()

        query = """
        WITH ranked AS (
            SELECT 
                strftime('%Y-%m-%dT%H:%M:00', timestamp) AS bucket_start,
                metric_type, source, target_or_interface,
                raw_value, status,
                ROW_NUMBER() OVER (
                    PARTITION BY strftime('%Y-%m-%dT%H:%M:00', timestamp), metric_type, source, target_or_interface 
                    ORDER BY raw_value
                ) as rn,
                COUNT(*) OVER (
                    PARTITION BY strftime('%Y-%m-%dT%H:%M:00', timestamp), metric_type, source, target_or_interface
                ) as total_cnt
            FROM measurements
            WHERE timestamp < ?
        )
        INSERT OR REPLACE INTO measurement_aggregates_1m (
            bucket_start, metric_type, source, target_or_interface,
            sample_count, min_value, avg_value, max_value, p95_value, loss_rate
        )
        SELECT 
            bucket_start, metric_type, source, target_or_interface,
            total_cnt,
            MIN(raw_value),
            AVG(raw_value),
            MAX(raw_value),
            MAX(CASE WHEN rn = MAX(1, CAST(ROUND(total_cnt * 0.95) AS INT)) THEN raw_value END),
            AVG(CASE WHEN lower(status) != 'success' THEN 1.0 ELSE 0.0 END)
        FROM ranked
        GROUP BY bucket_start, metric_type, source, target_or_interface;
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (cutoff_str,))
            cur.execute("SELECT changes();")
            row = cur.fetchone()
            changes = int(row[0]) if row and row[0] is not None else 0
            conn.commit()
            return changes

    def prune_raw_samples(self, keep_hours: int = 24) -> int:
        """Downsample raw measurements older than keep_hours then deletes them."""
        if keep_hours < 1:
            raise ValueError(f"keep_hours must be >= 1, got {keep_hours}")
        cutoff_dt = datetime.now(timezone.utc) - timedelta(hours=keep_hours)
        cutoff_str = cutoff_dt.isoformat()

        # Ensure raw samples are aggregated before deletion
        self.downsample_to_aggregates(cutoff_timestamp=cutoff_dt)

        query = "DELETE FROM measurements WHERE timestamp < ?;"
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (cutoff_str,))
            cur.execute("SELECT changes();")
            row = cur.fetchone()
            changes = int(row[0]) if row and row[0] is not None else 0
            conn.commit()
            return changes

    def prune_aggregates(self, retention_days: int = 30) -> int:
        """Deletes 1-minute aggregates older than retention_days."""
        if retention_days < 1:
            raise ValueError(f"retention_days must be >= 1, got {retention_days}")
        cutoff_str = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
        query = "DELETE FROM measurement_aggregates_1m WHERE bucket_start < ?;"
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (cutoff_str,))
            cur.execute("SELECT changes();")
            row = cur.fetchone()
            changes = int(row[0]) if row and row[0] is not None else 0
            conn.commit()
            return changes

    def prune_older_than(self, days: int) -> int:
        """Deletes measurements and aggregates older than specified days, returning count of deleted raw rows."""
        if days < 1:
            raise ValueError(f"Retention days must be >= 1, got {days}")
        self.prune_aggregates(retention_days=days)
        return self.prune_raw_samples(keep_hours=min(24, days * 24))

    def prune_all(
        self,
        raw_hours: int = 24,
        retention_days: int = 30,
        incident_repo: Optional[Any] = None,
        audit_repo: Optional[Any] = None,
        vacuum_after: bool = False,
    ) -> Dict[str, int]:
        """Prunes raw measurements, downsampled aggregates, incidents, and audit logs according to retention settings."""
        aggregates_created = self.downsample_to_aggregates()
        raw_pruned = self.prune_raw_samples(keep_hours=raw_hours)
        aggregates_pruned = self.prune_aggregates(retention_days=retention_days)

        incidents_pruned = 0
        if incident_repo and hasattr(incident_repo, "prune_older_than"):
            incidents_pruned = incident_repo.prune_older_than(days=retention_days)

        audit_pruned = 0
        if audit_repo and hasattr(audit_repo, "prune_older_than"):
            audit_pruned = audit_repo.prune_older_than(days=retention_days)

        if vacuum_after and hasattr(self.db, "vacuum"):
            self.db.vacuum()

        return {
            "aggregates_created": aggregates_created,
            "raw_pruned": raw_pruned,
            "aggregates_pruned": aggregates_pruned,
            "incidents_pruned": incidents_pruned,
            "audit_pruned": audit_pruned,
        }

    def clear_all_history(
        self,
        incident_repo: Optional[Any] = None,
        audit_repo: Optional[Any] = None,
    ) -> Dict[str, int]:
        """Purge all measurements, aggregates, incidents, and audit records, reclaiming disk space with VACUUM."""
        self.flush()
        deleted_raw = 0
        deleted_aggs = 0
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM measurements;")
            deleted_raw = cur.rowcount
            cur.execute("DELETE FROM measurement_aggregates_1m;")
            deleted_aggs = cur.rowcount
            conn.commit()

        deleted_inc = incident_repo.clear_all() if incident_repo and hasattr(incident_repo, "clear_all") else 0
        deleted_audit = audit_repo.clear_all() if audit_repo and hasattr(audit_repo, "clear_all") else 0

        if hasattr(self.db, "vacuum"):
            self.db.vacuum()

        return {
            "measurements": deleted_raw,
            "aggregates": deleted_aggs,
            "incidents": deleted_inc,
            "audit": deleted_audit,
        }

    def get_day_slots(
        self,
        target_date: date,
        thresholds: Optional[Any] = None,
        incident_repo: Optional[Any] = None,
    ) -> List[str]:
        """Aggregate 30-minute intervals for target_date across 48 slots.

        Reads from 1-minute aggregates (downsampled history) and recent raw samples,
        evaluating metrics and incidents against thresholds to return
        a list of 48 states ('healthy', 'slow', 'bad', 'no-data', 'future').
        """
        self.flush()
        if thresholds is None:
            try:
                from app.core.thresholds import DEFAULT_THRESHOLDS
                thresholds = DEFAULT_THRESHOLDS
            except Exception as exc:
                logger.warning("Failed to load DEFAULT_THRESHOLDS in get_day_slots: %s", exc)
                thresholds = None

        today = date.today()
        now = datetime.now()
        current_slot = (
            min(47, (now.hour * 60 + now.minute) // 30)
            if target_date == today
            else (47 if target_date < today else -1)
        )

        slots: List[str] = ["no-data"] * 48
        for i in range(48):
            if target_date > today or (target_date == today and i > current_slot):
                slots[i] = "future"

        start_local = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0).astimezone()
        end_local = start_local + timedelta(days=1)
        start_search = (start_local - timedelta(days=1)).isoformat()[:10]
        end_search = (end_local + timedelta(days=1)).isoformat()[:10] + "T23:59:59"
        target_date_str = target_date.isoformat()

        slot_metrics: Dict[int, Dict[str, Dict[str, float]]] = {}
        slot_incidents: Dict[int, Dict[str, int]] = {}

        agg_query = """
        SELECT 
            cast(strftime('%H', case when bucket_start like '%+%' or bucket_start like '%Z' then datetime(bucket_start, 'localtime') else datetime(bucket_start) end) as integer) * 2 
            + (cast(strftime('%M', case when bucket_start like '%+%' or bucket_start like '%Z' then datetime(bucket_start, 'localtime') else datetime(bucket_start) end) as integer) / 30) AS slot,
            metric_type,
            avg(avg_value) as avg_val,
            max(max_value) as max_val,
            min(min_value) as min_val,
            sum(sample_count) as sample_count
        FROM measurement_aggregates_1m
        WHERE bucket_start >= ? AND bucket_start <= ?
          AND strftime('%Y-%m-%d', case when bucket_start like '%+%' or bucket_start like '%Z' then datetime(bucket_start, 'localtime') else datetime(bucket_start) end) = ?
        GROUP BY slot, metric_type;
        """

        meas_query = """
        SELECT 
            cast(strftime('%H', case when timestamp like '%+%' or timestamp like '%Z' then datetime(timestamp, 'localtime') else datetime(timestamp) end) as integer) * 2 
            + (cast(strftime('%M', case when timestamp like '%+%' or timestamp like '%Z' then datetime(timestamp, 'localtime') else datetime(timestamp) end) as integer) / 30) AS slot,
            metric_type,
            avg(raw_value) as avg_val,
            max(raw_value) as max_val,
            min(raw_value) as min_val,
            count(*) as sample_count
        FROM measurements
        WHERE timestamp >= ? AND timestamp <= ?
          AND strftime('%Y-%m-%d', case when timestamp like '%+%' or timestamp like '%Z' then datetime(timestamp, 'localtime') else datetime(timestamp) end) = ?
          AND substr(timestamp, 1, 16) || ':00' NOT IN (
              SELECT bucket_start FROM measurement_aggregates_1m 
              WHERE bucket_start >= ? AND bucket_start <= ?
          )
        GROUP BY slot, metric_type;
        """

        inc_query = """
        SELECT 
            cast(strftime('%H', case when timestamp like '%+%' or timestamp like '%Z' then datetime(timestamp, 'localtime') else datetime(timestamp) end) as integer) * 2 
            + (cast(strftime('%M', case when timestamp like '%+%' or timestamp like '%Z' then datetime(timestamp, 'localtime') else datetime(timestamp) end) as integer) / 30) AS slot,
            severity,
            count(*) as cnt
        FROM incidents
        WHERE timestamp >= ? AND timestamp <= ?
          AND strftime('%Y-%m-%d', case when timestamp like '%+%' or timestamp like '%Z' then datetime(timestamp, 'localtime') else datetime(timestamp) end) = ?
        GROUP BY slot, severity;
        """

        with self.db.get_connection() as conn:
            cur = conn.cursor()
            # 1. Query 1-minute aggregates
            cur.execute(agg_query, (start_search, end_search, target_date_str))
            for row in cur.fetchall():
                slot = int(row["slot"])
                if slot not in slot_metrics:
                    slot_metrics[slot] = {}
                slot_metrics[slot][row["metric_type"]] = {
                    "avg": float(row["avg_val"]) if row["avg_val"] is not None else 0.0,
                    "max": float(row["max_val"]) if row["max_val"] is not None else 0.0,
                    "min": float(row["min_val"]) if row["min_val"] is not None else 0.0,
                    "count": int(row["sample_count"]),
                }

            # 2. Query any unaggregated recent measurements
            cur.execute(meas_query, (start_search, end_search, target_date_str, start_search, end_search))
            for row in cur.fetchall():
                slot = int(row["slot"])
                if slot not in slot_metrics:
                    slot_metrics[slot] = {}
                mtype = row["metric_type"]
                cnt = int(row["sample_count"])
                avg_v = float(row["avg_val"]) if row["avg_val"] is not None else 0.0
                max_v = float(row["max_val"]) if row["max_val"] is not None else 0.0
                min_v = float(row["min_val"]) if row["min_val"] is not None else 0.0
                if mtype in slot_metrics[slot]:
                    curr = slot_metrics[slot][mtype]
                    total_cnt = curr["count"] + cnt
                    curr["avg"] = ((curr["avg"] * curr["count"]) + (avg_v * cnt)) / max(1, total_cnt)
                    curr["max"] = max(curr["max"], max_v)
                    curr["min"] = min(curr["min"], min_v)
                    curr["count"] = total_cnt
                else:
                    slot_metrics[slot][mtype] = {
                        "avg": avg_v,
                        "max": max_v,
                        "min": min_v,
                        "count": cnt,
                    }

            # 3. Query Incidents
            cur.execute(inc_query, (start_search, end_search, target_date_str))
            for row in cur.fetchall():
                slot = int(row["slot"])
                if slot not in slot_incidents:
                    slot_incidents[slot] = {}
                sev = str(row["severity"]).lower()
                slot_incidents[slot][sev] = int(row["cnt"])

        # Centralized Thresholds
        gw_loss_crit = getattr(thresholds, "gateway_packet_loss_critical", 0.40)
        ext_loss_crit = getattr(thresholds, "external_packet_loss_critical", 0.30)
        gw_lat_crit = getattr(thresholds, "gateway_latency_critical_ms", 80.0)
        ext_lat_crit = getattr(thresholds, "external_latency_critical_ms", 200.0)

        gw_lat_warn = getattr(thresholds, "gateway_latency_warning_ms", 25.0)
        ext_lat_warn = getattr(thresholds, "external_latency_warning_ms", 80.0)
        dns_lat_warn = getattr(thresholds, "dns_latency_warning_ms", 100.0)
        jit_warn = getattr(thresholds, "jitter_warning_ms", 30.0)

        for i in range(48):
            if slots[i] == "future":
                continue

            metrics = slot_metrics.get(i, {})
            incidents = slot_incidents.get(i, {})

            total_meas = sum(m["count"] for m in metrics.values())
            total_inc = sum(incidents.values())

            if total_meas == 0 and total_inc == 0:
                slots[i] = "no-data"
                continue

            # 1. Bad State: Critical/high incident, severe loss, reachability failure, or critical latency
            has_crit_inc = any(sev in ("critical", "high") for sev in incidents.keys())
            gw_loss_max = metrics.get("gateway_packet_loss", {}).get("max", 0.0)
            ext_loss_max = metrics.get("external_packet_loss", {}).get("max", 0.0)
            gw_reach_min = metrics.get("gateway_reachability", {}).get("min", 1.0)
            ext_tcp_min = metrics.get("external_tcp_connect", {}).get("min", 1.0)
            gw_lat_max = metrics.get("gateway_latency", {}).get("max", 0.0)
            ext_lat_max = metrics.get("external_latency", {}).get("max", 0.0)

            is_bad = (
                has_crit_inc
                or gw_loss_max >= gw_loss_crit
                or ext_loss_max >= ext_loss_crit
                or (gw_reach_min == 0.0 and "gateway_reachability" in metrics)
                or (ext_tcp_min == 0.0 and "external_tcp_connect" in metrics)
                or gw_lat_max >= gw_lat_crit
                or ext_lat_max >= ext_lat_crit
            )

            if is_bad:
                slots[i] = "bad"
                continue

            # 2. Slow State: Warning incident, elevated latency, elevated jitter, or any packet loss
            has_warn_inc = any(sev in ("medium", "warning", "low") for sev in incidents.keys())
            gw_lat_avg = metrics.get("gateway_latency", {}).get("avg", 0.0)
            ext_lat_avg = metrics.get("external_latency", {}).get("avg", 0.0)
            dns_lat_avg = metrics.get("dns_latency", {}).get("avg", 0.0)
            jit_avg = metrics.get("jitter_ms", {}).get("avg", 0.0)

            is_slow = (
                has_warn_inc
                or gw_lat_avg >= gw_lat_warn
                or ext_lat_avg >= ext_lat_warn
                or dns_lat_avg >= dns_lat_warn
                or jit_avg >= jit_warn
                or gw_loss_max > 0.0
                or ext_loss_max > 0.0
            )

            if is_slow:
                slots[i] = "slow"
                continue

            # 3. Healthy State
            slots[i] = "healthy"

        return slots

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
