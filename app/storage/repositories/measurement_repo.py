"""Measurement Repository for persisting and querying telemetry samples."""

from __future__ import annotations
import json
from datetime import date, datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
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

    def get_day_slots(
        self,
        target_date: date,
        thresholds: Optional[Any] = None,
        incident_repo: Optional[Any] = None,
    ) -> List[str]:
        """Aggregate 30-minute intervals for target_date across 48 slots.

        Evaluates measurements and incidents against thresholds to return
        a list of 48 states ('healthy', 'slow', 'bad', 'no-data', 'future').
        """
        if thresholds is None:
            try:
                from app.core.thresholds import DEFAULT_THRESHOLDS
                thresholds = DEFAULT_THRESHOLDS
            except Exception:
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
            cur.execute(meas_query, (start_search, end_search, target_date_str))
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
