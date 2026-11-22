"""Visual verification script for Row A: LatencyChart and TimelinePanel."""

from __future__ import annotations
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt

from app.ui import tokens
from app.ui.widgets.latency_chart import LatencyChart
from app.ui.widgets.timeline import TimelinePanel
from app.core.models.metrics import (
    Diagnosis,
    ProbableCause,
    DiagnosisSeverity,
    Evidence,
    MetricType,
    ActionExecutionRecord,
    ActionExecutionStatus,
    RiskLevel,
)


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    out_dir = Path("artifacts_screenshots")
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Test LatencyChart alone (Idle & Populated)
    w_chart = QWidget()
    w_chart.setStyleSheet(f"background-color: {tokens.BG};")
    l_chart = QVBoxLayout(w_chart)
    l_chart.setContentsMargins(16, 16, 16, 16)
    chart = LatencyChart()
    l_chart.addWidget(chart)
    w_chart.resize(650, 320)
    w_chart.show()
    w_chart.grab().save(str(out_dir / "verify_latency_chart_idle.png"))

    # Populated chart
    samples = [28.0, 31.0, 29.5, 30.2, 45.0, 182.0, 85.0, 32.0, 29.0, 28.5, 30.0, 29.2, 28.8, 30.1, 29.5]
    chart.update_telemetry(samples, avg_ms=29.0, max_ms=182.0, duration_str="41 ث")
    w_chart.grab().save(str(out_dir / "verify_latency_chart_populated.png"))

    # 2. Test TimelinePanel alone (Idle & Populated)
    w_time = QWidget()
    w_time.setStyleSheet(f"background-color: {tokens.BG};")
    l_time = QVBoxLayout(w_time)
    l_time.setContentsMargins(16, 16, 16, 16)
    timeline = TimelinePanel()
    l_time.addWidget(timeline)
    w_time.resize(500, 320)
    w_time.show()
    w_time.grab().save(str(out_dir / "verify_timeline_idle.png"))

    # Populated timeline with incident & audit
    t_inc = datetime.now(timezone.utc)
    t_aud = datetime.now(timezone.utc)
    incident = Diagnosis(
        probable_cause=ProbableCause.DESTINATION_SPECIFIC_OUTAGE,
        confidence=0.90,
        severity=DiagnosisSeverity.HIGH,
        supporting_evidence=[
            Evidence(
                metric_type=MetricType.GATEWAY_PACKET_LOSS,
                target="gateway",
                observed_value=1.0,
                threshold_value=0.3,
                condition=">",
            )
        ],
        explanation="انقطاع أو بطء خاص بالوجهة المستهدفة.",
        recommended_actions=["Flush DNS Resolver Cache"],
    )
    incident.timestamp = t_inc

    record = ActionExecutionRecord(
        id="act-test-01",
        action_id="flush_dns_cache",
        action_name="Flush DNS Resolver Cache",
        risk_level=RiskLevel.LEVEL_1_LOW,
        trigger_diagnosis_id="inc-test-01",
        pre_remedy_metrics={"loss_pct": 1.0},
        post_remedy_metrics={"rtt_ms": 28.0},
        status=ActionExecutionStatus.SUCCEEDED,
        execution_duration_ms=60.0,
        verification_duration_ms=40.0,
    )
    record.timestamp = t_aud
    timeline.update_from_records(incident, record)
    w_time.grab().save(str(out_dir / "verify_timeline_event.png"))

    # 3. Test Row A Container side by side (3:2 ratio)
    row_container = QWidget()
    row_container.setStyleSheet(f"background-color: {tokens.BG};")
    row_layout = QHBoxLayout(row_container)
    row_layout.setContentsMargins(20, 16, 20, 16)
    row_layout.setSpacing(16)

    chart_box = LatencyChart()
    chart_box.update_telemetry(samples, avg_ms=29.0, max_ms=182.0, duration_str="41 ث")

    timeline_box = TimelinePanel()
    timeline_box.update_from_records(incident, record)

    row_layout.addWidget(chart_box, 3)
    row_layout.addWidget(timeline_box, 2)

    row_container.resize(1100, 360)
    row_container.show()
    row_container.grab().save(str(out_dir / "verify_row_a_side_by_side.png"))

    print("Screenshots saved successfully to artifacts_screenshots/")


if __name__ == "__main__":
    main()
