"""SQLite Database Manager for NetGuard AI with WAL support and Schema Migrations."""

from __future__ import annotations
import os
import sqlite3
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger("netguard.storage")

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    source TEXT NOT NULL,
    target_or_interface TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    raw_value REAL NOT NULL,
    normalized_value REAL NOT NULL,
    unit TEXT NOT NULL,
    status TEXT NOT NULL,
    confidence REAL NOT NULL,
    metadata_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_measurements_ts ON measurements(timestamp);
CREATE INDEX IF NOT EXISTS idx_measurements_metric ON measurements(metric_type);
CREATE INDEX IF NOT EXISTS idx_measurements_target ON measurements(target_or_interface);

CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    probable_cause TEXT NOT NULL,
    confidence REAL NOT NULL,
    severity TEXT NOT NULL,
    explanation TEXT,
    auto_remediation_permitted INTEGER NOT NULL,
    evidence_json TEXT,
    actions_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_incidents_ts ON incidents(timestamp);
CREATE INDEX IF NOT EXISTS idx_incidents_cause ON incidents(probable_cause);

CREATE TABLE IF NOT EXISTS actions_audit (
    id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL,
    action_name TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    trigger_diagnosis_id TEXT,
    pre_remedy_metrics TEXT,
    post_remedy_metrics TEXT,
    status TEXT NOT NULL,
    execution_duration_ms REAL NOT NULL,
    verification_duration_ms REAL NOT NULL,
    error_message TEXT,
    rollback_performed INTEGER NOT NULL,
    rollback_success INTEGER
);

CREATE INDEX IF NOT EXISTS idx_actions_ts ON actions_audit(timestamp);
CREATE INDEX IF NOT EXISTS idx_actions_id ON actions_audit(action_id);
"""

SCHEMA_V2 = """
CREATE TABLE IF NOT EXISTS measurement_aggregates_1m (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bucket_start TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    source TEXT NOT NULL,
    target_or_interface TEXT NOT NULL,
    sample_count INTEGER NOT NULL,
    min_value REAL NOT NULL,
    avg_value REAL NOT NULL,
    max_value REAL NOT NULL,
    p95_value REAL NOT NULL,
    loss_rate REAL NOT NULL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bucket_start, metric_type, source, target_or_interface)
);

CREATE INDEX IF NOT EXISTS idx_aggregates_bucket ON measurement_aggregates_1m(bucket_start);
CREATE INDEX IF NOT EXISTS idx_aggregates_metric ON measurement_aggregates_1m(metric_type);
CREATE INDEX IF NOT EXISTS idx_aggregates_target ON measurement_aggregates_1m(target_or_interface);
"""


class DatabaseManager:
    """Manages SQLite connection lifecycle, PRAGMAs, and transactions."""

    def __init__(self, db_path: str | Path = "data/netguard.db", enable_wal: bool = True) -> None:
        self.db_path = Path(db_path)
        self.enable_wal = enable_wal
        self._init_storage()

    def _init_storage(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.get_connection() as conn:
            if self.enable_wal and str(self.db_path) != ":memory:":
                conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.execute("PRAGMA busy_timeout=5000;")
            self._apply_migrations(conn)

    def _apply_migrations(self, conn: sqlite3.Connection) -> None:
        conn.executescript(SCHEMA_V1)
        cur = conn.cursor()
        cur.execute("SELECT MAX(version) FROM schema_version;")
        row = cur.fetchone()
        current_version = row[0] if row and row[0] is not None else 0

        if current_version < 1:
            conn.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (1);")
            conn.commit()
            current_version = 1
            logger.info("Database schema initialized to version 1 at %s", self.db_path)

        if current_version < 2:
            conn.executescript(SCHEMA_V2)
            conn.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (2);")
            conn.commit()
            logger.info("Database schema migrated to version 2 (aggregates) at %s", self.db_path)

        if current_version < 3:
            cols = [
                ("fingerprint", "TEXT DEFAULT ''"),
                ("first_detected", "TEXT"),
                ("last_observed", "TEXT"),
                ("occurrence_count", "INTEGER DEFAULT 1"),
                ("status", "TEXT DEFAULT 'diagnosed'"),
                ("resolution_type", "TEXT DEFAULT 'diagnosed_only'"),
                ("affected_component", "TEXT DEFAULT 'network'"),
                ("cause_classification", "TEXT DEFAULT 'probable_cause'"),
                ("action_record_id", "TEXT"),
                ("resolved_at", "TEXT"),
            ]
            for col_name, col_def in cols:
                try:
                    conn.execute(f"ALTER TABLE incidents ADD COLUMN {col_name} {col_def};")
                except sqlite3.OperationalError:
                    pass
            try:
                conn.execute("ALTER TABLE actions_audit ADD COLUMN action_classification TEXT DEFAULT 'corrective_action';")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_fingerprint ON incidents(fingerprint);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);")
            except Exception:
                pass
            conn.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (3);")
            conn.commit()
            logger.info("Database schema migrated to version 3 (unified incident lifecycle) at %s", self.db_path)

    def vacuum(self) -> None:
        """Run VACUUM to reclaim free space from pruned rows in autocommit mode."""
        if str(self.db_path) == ":memory:":
            return
        conn = sqlite3.connect(str(self.db_path), timeout=30.0, isolation_level=None)
        try:
            conn.execute("VACUUM;")
            logger.info("Database VACUUM completed successfully on %s", self.db_path)
        except Exception as exc:
            logger.warning("Database VACUUM failed on %s: %s", self.db_path, exc)
        finally:
            conn.close()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=10.0,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        return conn
