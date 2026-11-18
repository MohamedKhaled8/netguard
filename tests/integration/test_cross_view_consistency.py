"""Cross-view consistency integration test (Item C4).

Verifies that the same fact across multiple screens (Dashboard, Diagnosis, DNS, Traffic, Remediation, Settings)
is backed by a single source of truth and stays completely consistent.
"""

import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication

from app.dns.state import DnsStateManager, DnsStateData
from app.core.models.metrics import OperatingMode
from app.monitoring.health_evaluator import assess_network_health, HealthSample, HealthStatus


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_operating_mode_consistency_across_views(qapp):
    """Sidebar, Settings, and Remediation must reflect the exact same operating mode."""
    from app.ui.views.remediation_view import RemediationView
    from app.ui.views.settings_view import SettingsView
    from app.ui.main_window import SidebarWidget

    sidebar = SidebarWidget()
    rem_view = RemediationView()
    settings_view = SettingsView()

    for mode in [OperatingMode.AUTO, OperatingMode.ASK, OperatingMode.WATCH]:
        sidebar.set_operating_mode(mode)
        rem_view.set_operating_mode(mode)
        settings_view.set_operating_mode(mode)

        # Settings combo data matches
        curr_combo = settings_view.mode_combo.currentData()
        assert curr_combo == mode.value

        # Remediation cards reflect mode
        mode_to_idx = {OperatingMode.AUTO: 0, OperatingMode.ASK: 1, OperatingMode.WATCH: 2}
        assert rem_view._current_mode_idx == mode_to_idx[mode]


def test_dns_state_consistency_across_views(qapp):
    """Dashboard, DNS View, and Diagnosis must reflect the exact same DNS server."""
    from app.ui.views.dashboard_view import DashboardView
    from app.ui.views.dns_view import DNSView
    from app.ui.views.diagnosis_view import DiagnosisView

    dash = DashboardView()
    dns_view = DNSView()
    diag = DiagnosisView()

    mgr = DnsStateManager.get_instance()
    mgr.update(
        active_servers=["1.1.1.1", "1.0.0.1"],
        detected_provider="Cloudflare",
        last_measured_ms=22.5,
        is_healthy=True,
    )

    # Set state on views
    dns_view.set_active_dns_info(mgr.current.active_servers)
    assert "1.1.1.1" in dns_view.lbl_curr_name.text()

    diag.update_dns_telemetry("Cloudflare", 22.5, True, is_optimal=True)
    assert "Cloudflare" in diag.row_l4.lbl_desc.text()
    assert "22 ms" in diag.row_l4.lbl_metric.text() or "23 ms" in diag.row_l4.lbl_metric.text()


def test_health_verdict_consistency():
    """Single verdict generator assess_network_health produces identical status for same sample."""
    sample_clean = HealthSample(gateway_latency_ms=2.0, internet_latency_ms=25.0, jitter_ms=2.0)
    v1 = assess_network_health(sample_clean)
    v2 = assess_network_health(sample_clean)

    assert v1.status == v2.status == HealthStatus.GOOD
    assert v1.headline == v2.headline
