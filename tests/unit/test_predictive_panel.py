"""Unit tests for PredictiveDiagnosticsPanel and Root-Cause Isolation."""

import pytest
from PySide6.QtWidgets import QApplication
import sys

from app.ui.widgets.predictive_panel import (
    PredictiveDiagnosticsPanel,
    MetricKpiCard,
    RootCauseStationItem,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def test_predictive_panel_initial_state(qapp):
    panel = PredictiveDiagnosticsPanel()
    assert panel.kpi_health.lbl_val.text() == "100"
    assert panel.kpi_stability.lbl_val.text() == "98.5"
    assert panel.kpi_fault_risk.lbl_val.text() == "3"
    assert "كافة المحطات تعمل بانتظام" in panel.chip_isolated_verdict.text()


def test_predictive_panel_healthy_telemetry(qapp):
    panel = PredictiveDiagnosticsPanel()
    panel.update_predictive_state(
        gw_lat=2.5,
        ext_lat=30.0,
        jitter_ms=1.5,
        packet_loss_pct=0.0,
        wifi_signal_pct=88.0,
        dns_lat=18.0,
        local_ip="192.168.1.15",
        hop2_reachable=True,
    )
    health = float(panel.kpi_health.lbl_val.text())
    assert health >= 90.0
    fault_risk = float(panel.kpi_fault_risk.lbl_val.text())
    assert fault_risk <= 15.0
    assert "سليم" in panel.st_gateway.chip.text()
    assert "سليم" in panel.st_dns.chip.text()
    assert "كافة المحطات تعمل بانتظام" in panel.chip_isolated_verdict.text()


def test_predictive_panel_gateway_bottleneck_isolation(qapp):
    panel = PredictiveDiagnosticsPanel()
    panel.update_predictive_state(
        gw_lat=65.0,
        ext_lat=85.0,
        jitter_ms=8.0,
        packet_loss_pct=0.0,
        wifi_signal_pct=75.0,
        dns_lat=25.0,
        local_ip="192.168.1.15",
        hop2_reachable=True,
    )
    assert panel.st_gateway.chip.text() == "خلل معزول"
    assert "بوابة الراوتر" in panel.chip_isolated_verdict.text()
    assert "أعد تشغيل الراوتر" in panel.lbl_act_text.text()


def test_predictive_panel_dns_bottleneck_isolation(qapp):
    panel = PredictiveDiagnosticsPanel()
    panel.update_predictive_state(
        gw_lat=3.0,
        ext_lat=35.0,
        jitter_ms=2.0,
        packet_loss_pct=0.0,
        wifi_signal_pct=80.0,
        dns_lat=195.0,
        local_ip="192.168.1.15",
        hop2_reachable=True,
    )
    assert panel.st_dns.chip.text() == "خلل معزول"
    assert "DNS" in panel.chip_isolated_verdict.text()
    assert "بدّل إلى خادم DNS أسرع" in panel.lbl_act_text.text()


def test_predictive_panel_wifi_degradation_isolation(qapp):
    panel = PredictiveDiagnosticsPanel()
    panel.update_predictive_state(
        gw_lat=48.0,
        ext_lat=70.0,
        jitter_ms=18.0,
        packet_loss_pct=0.0,
        wifi_signal_pct=25.0,
        dns_lat=30.0,
        local_ip="192.168.1.15",
        hop2_reachable=True,
    )
    assert panel.st_wifi.chip.text() == "خلل معزول"
    assert "الربط اللاسلكي" in panel.chip_isolated_verdict.text()


def test_predictive_panel_fault_probability_derivative(qapp):
    panel = PredictiveDiagnosticsPanel()
    # Feed rising latency trend to test derivative risk
    for lat in [30.0, 45.0, 60.0, 85.0, 110.0]:
        panel.update_predictive_state(
            gw_lat=3.0,
            ext_lat=lat,
            jitter_ms=5.0,
            packet_loss_pct=0.0,
            wifi_signal_pct=80.0,
            dns_lat=25.0,
        )
    fault_risk = float(panel.kpi_fault_risk.lbl_val.text())
    assert fault_risk > 15.0  # Risk elevated due to upward latency derivative
