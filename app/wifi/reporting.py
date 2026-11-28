"""Before/After diagnostic snapshots, noise/drift comparability checks, SQLite persistence, and redacted exports."""

from __future__ import annotations

import html
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.wifi.models import (
    BeforeAfterComparison,
    BeforeAfterSnapshot,
    BufferbloatDiagnosticsReport,
    DnsDiagnosticsReport,
    FullChannelAnalysisReport,
    MetricDelta,
    NetworkDiagnosticsReport,
    SpeedTestReport,
    UnifiedDiagnosticReport,
    WifiInterfaceTelemetry,
    utc_now,
)
from app.wifi.router.credentials import redact_secrets

SNAPSHOTS_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS wifi_diagnostic_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL,
    created_at TEXT NOT NULL,
    interface_name TEXT,
    ssid TEXT,
    bssid TEXT,
    band TEXT,
    channel INTEGER,
    snapshot_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_wifi_snap_created ON wifi_diagnostic_snapshots(created_at DESC);
"""


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.executescript(SNAPSHOTS_TABLE_DDL)
    conn.commit()


class BeforeAfterReportingService:
    """Captures comparable diagnostic baselines, verifies post-change gains honestly, and exports safely."""

    def __init__(self, db_manager: Any = None) -> None:
        self._db = db_manager
        self._memory_snapshots: List[BeforeAfterSnapshot] = []

    @staticmethod
    def build_snapshot(
        *,
        label: str,
        telemetry: Optional[WifiInterfaceTelemetry] = None,
        network_report: Optional[NetworkDiagnosticsReport] = None,
        dns_report: Optional[DnsDiagnosticsReport] = None,
        speed_report: Optional[SpeedTestReport] = None,
        bufferbloat_report: Optional[BufferbloatDiagnosticsReport] = None,
        channel_report: Optional[FullChannelAnalysisReport] = None,
        qos_active: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BeforeAfterSnapshot:
        """Assemble a normalized comparable snapshot from any subset of diagnostic outputs."""
        dns_med = None
        if dns_report:
            conf = next((t for t in dns_report.targets if t.role == "configured"), None)
            if conf:
                dns_med = conf.median_ms or conf.avg_ms

        ch_score = None
        if channel_report and telemetry and telemetry.band:
            b_res = channel_report.bands.get(telemetry.band)
            if b_res and b_res.current_channel_score:
                ch_score = b_res.current_channel_score.total_score

        return BeforeAfterSnapshot(
            snapshot_id=uuid.uuid4().hex[:12],
            label=label,
            created_at=utc_now(),
            interface_name=telemetry.interface_name if telemetry else None,
            ssid=telemetry.ssid if telemetry else None,
            bssid=telemetry.bssid if telemetry else None,
            band=telemetry.band if telemetry else None,
            channel=telemetry.channel if telemetry else None,
            channel_width_mhz=telemetry.channel_width_mhz if telemetry else None,
            rssi_dbm=telemetry.rssi_dbm if telemetry else None,
            tx_link_rate_mbps=telemetry.tx_link_rate_mbps if telemetry else None,
            gateway_avg_ms=(
                network_report.gateway_ping.avg_ms
                if network_report and network_report.gateway_ping.status == "ok"
                else None
            ),
            gateway_loss_pct=(
                network_report.gateway_ping.packet_loss_pct
                if network_report
                else None
            ),
            internet_avg_ms=(
                network_report.internet_ping.avg_ms
                if network_report and network_report.internet_ping.status == "ok"
                else None
            ),
            internet_loss_pct=(
                network_report.internet_ping.packet_loss_pct
                if network_report
                else None
            ),
            dns_configured_avg_ms=dns_med,
            download_mbps=speed_report.download_mbps if speed_report else None,
            upload_mbps=speed_report.upload_mbps if speed_report else None,
            download_bloat_delta_ms=(
                bufferbloat_report.download_phase.delta_over_idle_ms
                if bufferbloat_report and bufferbloat_report.download_phase
                else None
            ),
            upload_bloat_delta_ms=(
                bufferbloat_report.upload_phase.delta_over_idle_ms
                if bufferbloat_report and bufferbloat_report.upload_phase
                else None
            ),
            bufferbloat_grade=(
                bufferbloat_report.overall_grade if bufferbloat_report else None
            ),
            qos_active=(
                qos_active
                if qos_active is not None
                else (
                    speed_report.qos_active_during_test
                    if speed_report
                    else (bufferbloat_report.qos_was_active if bufferbloat_report else None)
                )
            ),
            channel_score=ch_score,
            metadata=redact_secrets(metadata or {}),
        )

    def save_snapshot(self, snapshot: BeforeAfterSnapshot) -> None:
        self._memory_snapshots.insert(0, snapshot)
        if self._db is None:
            return
        conn = self._db.get_connection()
        _ensure_table(conn)
        conn.execute(
            """
            INSERT OR REPLACE INTO wifi_diagnostic_snapshots
            (snapshot_id, label, created_at, interface_name, ssid, bssid, band, channel, snapshot_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.snapshot_id,
                snapshot.label,
                snapshot.created_at.isoformat(),
                snapshot.interface_name,
                snapshot.ssid,
                snapshot.bssid,
                snapshot.band,
                snapshot.channel,
                snapshot.model_dump_json(),
            ),
        )
        conn.commit()

    def list_snapshots(self, limit: int = 25) -> List[BeforeAfterSnapshot]:
        if self._db is None:
            return self._memory_snapshots[:limit]
        conn = self._db.get_connection()
        _ensure_table(conn)
        rows = conn.execute(
            "SELECT snapshot_json FROM wifi_diagnostic_snapshots ORDER BY created_at DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
        out: List[BeforeAfterSnapshot] = []
        for row in rows:
            try:
                out.append(BeforeAfterSnapshot.model_validate_json(row[0]))
            except Exception:
                continue
        return out

    @staticmethod
    def _eval_kpi(
        name: str,
        before_val: Optional[float],
        after_val: Optional[float],
        unit: str,
        *,
        higher_is_better: bool,
        min_abs_noise: float,
        min_pct_noise: float = 8.0,
    ) -> MetricDelta:
        if before_val is None or after_val is None:
            return MetricDelta(
                metric_name=name,
                before_value=before_val,
                after_value=after_val,
                unit=unit,
                verdict="unavailable",
                note="Missing Before or After measurement.",
            )

        delta = round(after_val - before_val, 2)
        base = abs(before_val) if abs(before_val) > 1e-6 else 1.0
        delta_pct = round((delta / base) * 100.0, 1)

        if abs(delta) < min_abs_noise or abs(delta_pct) < min_pct_noise:
            return MetricDelta(
                metric_name=name,
                before_value=round(before_val, 2),
                after_value=round(after_val, 2),
                unit=unit,
                delta=delta,
                delta_pct=delta_pct,
                verdict="unchanged",
                note=f"Difference within normal measurement noise threshold (+/-{min_abs_noise} {unit} / {min_pct_noise}%).",
            )

        is_good = delta > 0 if higher_is_better else delta < 0
        return MetricDelta(
            metric_name=name,
            before_value=round(before_val, 2),
            after_value=round(after_val, 2),
            unit=unit,
            delta=delta,
            delta_pct=delta_pct,
            verdict="improved" if is_good else "degraded",
            note="",
        )

    def compare(
        self, before: BeforeAfterSnapshot, after: BeforeAfterSnapshot
    ) -> BeforeAfterComparison:
        """Compare Before vs After snapshots checking condition drift and measurement noise."""
        drift_warnings: List[str] = []
        comparable = True

        if before.ssid and after.ssid and before.ssid != after.ssid:
            comparable = False
            drift_warnings.append(f"SSID changed from '{before.ssid}' to '{after.ssid}'.")
        if before.band and after.band and before.band != after.band:
            drift_warnings.append(
                f"Band changed ({before.band} -> {after.band}); throughput/latency differences reflect band change."
            )
        if before.bssid and after.bssid and before.bssid != after.bssid:
            drift_warnings.append(f"BSSID roamed ({before.bssid} -> {after.bssid}).")
        if (
            before.qos_active is not None
            and after.qos_active is not None
            and before.qos_active != after.qos_active
        ):
            comparable = False
            drift_warnings.append(
                f"NetGuard QoS state differed (before={before.qos_active}, after={after.qos_active})."
            )

        deltas: List[MetricDelta] = [
            self._eval_kpi("RSSI Signal", before.rssi_dbm, after.rssi_dbm, "dBm", higher_is_better=True, min_abs_noise=2.5, min_pct_noise=3.0),
            self._eval_kpi("Wi-Fi TX Link Rate", before.tx_link_rate_mbps, after.tx_link_rate_mbps, "Mbps", higher_is_better=True, min_abs_noise=5.0, min_pct_noise=8.0),
            self._eval_kpi("Gateway Latency", before.gateway_avg_ms, after.gateway_avg_ms, "ms", higher_is_better=False, min_abs_noise=2.0, min_pct_noise=10.0),
            self._eval_kpi("Gateway Packet Loss", before.gateway_loss_pct, after.gateway_loss_pct, "%", higher_is_better=False, min_abs_noise=1.0, min_pct_noise=10.0),
            self._eval_kpi("Internet Latency", before.internet_avg_ms, after.internet_avg_ms, "ms", higher_is_better=False, min_abs_noise=3.0, min_pct_noise=10.0),
            self._eval_kpi("Configured DNS Median", before.dns_configured_avg_ms, after.dns_configured_avg_ms, "ms", higher_is_better=False, min_abs_noise=4.0, min_pct_noise=12.0),
            self._eval_kpi("Download Throughput", before.download_mbps, after.download_mbps, "Mbps", higher_is_better=True, min_abs_noise=2.0, min_pct_noise=8.0),
            self._eval_kpi("Upload Throughput", before.upload_mbps, after.upload_mbps, "Mbps", higher_is_better=True, min_abs_noise=1.0, min_pct_noise=8.0),
            self._eval_kpi("Download Bufferbloat Delta", before.download_bloat_delta_ms, after.download_bloat_delta_ms, "ms", higher_is_better=False, min_abs_noise=5.0, min_pct_noise=12.0),
            self._eval_kpi("Upload Bufferbloat Delta", before.upload_bloat_delta_ms, after.upload_bloat_delta_ms, "ms", higher_is_better=False, min_abs_noise=5.0, min_pct_noise=12.0),
            self._eval_kpi("Channel Congestion Score", before.channel_score, after.channel_score, "pts", higher_is_better=False, min_abs_noise=2.0, min_pct_noise=10.0),
        ]

        improved_cnt = sum(1 for d in deltas if d.verdict == "improved")
        degraded_cnt = sum(1 for d in deltas if d.verdict == "degraded")

        if not comparable:
            overall = "inconclusive"
            summary = "Comparison flagged condition drift (SSID or QoS mismatch); gains cannot be isolated cleanly."
        elif improved_cnt > 0 and degraded_cnt == 0:
            overall = "improved"
            summary = f"{improved_cnt} metric(s) improved cleanly beyond noise thresholds with 0 regressions."
        elif degraded_cnt > 0 and improved_cnt == 0:
            overall = "degraded"
            summary = f"{degraded_cnt} metric(s) regressed beyond noise thresholds."
        elif improved_cnt > 0 and degraded_cnt > 0:
            overall = "mixed"
            summary = f"Mixed result: {improved_cnt} metric(s) improved, {degraded_cnt} metric(s) regressed."
        else:
            overall = "inconclusive"
            summary = "All measured differences fall within normal noise thresholds or lack paired Before/After samples."

        return BeforeAfterComparison(
            before=before,
            after=after,
            comparable=comparable,
            condition_drift_warnings=drift_warnings,
            deltas=deltas,
            overall_verdict=overall,  # type: ignore[arg-type]
            summary=summary,
        )

    @staticmethod
    def build_redacted_export_payload(
        *,
        unified_report: Optional[UnifiedDiagnosticReport] = None,
        comparison: Optional[BeforeAfterComparison] = None,
        extra_sections: Optional[Dict[str, Any]] = None,
        extra_secrets: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """Serialize diagnostic reports and strictly strip any credentials/cookies/tokens."""
        raw: Dict[str, Any] = {
            "generated_at": utc_now().isoformat(),
            "tool": "NetGuard AI - Wi-Fi, Network & Router Diagnostics",
        }
        if unified_report is not None:
            raw["unified_diagnosis"] = unified_report.model_dump(mode="json")
        if comparison is not None:
            raw["before_after_comparison"] = comparison.model_dump(mode="json")
        if extra_sections:
            raw["details"] = extra_sections
        return redact_secrets(raw, extra_secrets=extra_secrets)

    def export_json(
        self,
        output_path: Path | str,
        *,
        unified_report: Optional[UnifiedDiagnosticReport] = None,
        comparison: Optional[BeforeAfterComparison] = None,
        extra_sections: Optional[Dict[str, Any]] = None,
        extra_secrets: Optional[Iterable[str]] = None,
    ) -> Path:
        payload = self.build_redacted_export_payload(
            unified_report=unified_report,
            comparison=comparison,
            extra_sections=extra_sections,
            extra_secrets=extra_secrets,
        )
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return out

    def export_html(
        self,
        output_path: Path | str,
        *,
        unified_report: Optional[UnifiedDiagnosticReport] = None,
        comparison: Optional[BeforeAfterComparison] = None,
        extra_sections: Optional[Dict[str, Any]] = None,
        extra_secrets: Optional[Iterable[str]] = None,
    ) -> Path:
        payload = self.build_redacted_export_payload(
            unified_report=unified_report,
            comparison=comparison,
            extra_sections=extra_sections,
            extra_secrets=extra_secrets,
        )
        rows_html = ""
        if comparison:
            for d in comparison.deltas:
                if d.verdict == "unavailable":
                    continue
                rows_html += (
                    f"<tr><td>{html.escape(d.metric_name)}</td>"
                    f"<td>{d.before_value} {html.escape(d.unit)}</td>"
                    f"<td>{d.after_value} {html.escape(d.unit)}</td>"
                    f"<td>{d.delta}</td><td><b>{html.escape(d.verdict)}</b></td></tr>"
                )

        findings_html = ""
        if unified_report:
            for f in unified_report.findings:
                findings_html += (
                    f"<li><b>[{html.escape(f.severity.upper())}] {html.escape(f.title)}</b>: "
                    f"{html.escape(f.summary)}</li>"
                )

        doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>NetGuard AI Diagnostic Report</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;background:#0C0E12;color:#ECEBE6;margin:24px;}}
h1,h2{{color:#FF5701;}}
table{{border-collapse:collapse;width:100%;margin-top:12px;background:#161A1F;}}
th,td{{border:1px solid #2A3138;padding:8px 12px;text-align:left;}}
th{{background:#101318;}}
pre{{background:#101318;padding:12px;border:1px solid #2A3138;overflow:auto;}}
</style>
</head>
<body>
<h1>NetGuard AI - Wi-Fi, Network & Router Report</h1>
<p>Generated: {html.escape(str(payload.get("generated_at", "")))}</p>
<h2>Findings</h2>
<ul>{findings_html or "<li>No major faults flagged.</li>"}</ul>
<h2>Before / After Verification</h2>
<p>{html.escape(comparison.summary if comparison else "No Before/After comparison attached.")}</p>
<table><tr><th>Metric</th><th>Before</th><th>After</th><th>Delta</th><th>Verdict</th></tr>{rows_html}</table>
<h2>Sanitized Telemetry Payload (Secrets Redacted)</h2>
<pre>{html.escape(json.dumps(payload, indent=2, ensure_ascii=False))}</pre>
</body>
</html>"""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(doc, encoding="utf-8")
        return out
