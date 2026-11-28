"""Unit tests verifying UI redesign, i18n parity, RTL/LTR switching, and router fixes."""

from __future__ import annotations

import os
import pathlib
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.core.models.metrics import OperatingMode
from app.traffic.qos_config import AppQoSConfig
from app.ui import i18n, tokens
from app.ui.main_window import MainWindow
from app.ui.views.about_view import AboutView
from app.ui.views.dashboard_view import compute_genuine_health_score
from app.ui.views.internet_quality_view import InternetQualityView
from app.ui.views.settings_view import SettingsView
from app.ui.widgets.circular_gauge import CircularGauge
from app.ui.widgets.flowchart_widget import InvestigationFlowchartWidget
from app.ui.widgets.qos_visualizer import QoSPolicyMatrixWidget
from app.wifi.router.parser import RouterConfigurationParser


def _ensure_qapp() -> QApplication:
    app = QApplication.instance()
    return app if app is not None else QApplication([])


def test_i18n_keys_parity_and_complete_coverage() -> None:
    """Every tr('...') literal used across app/ui must exist in both ar and en tables."""
    root = pathlib.Path("app/ui")
    pattern = re.compile(r'\btr\(\s*["\']([^"\']+)["\']')
    missing_ar = set()
    missing_en = set()
    for p in root.rglob("*.py"):
        txt = p.read_text(encoding="utf-8", errors="ignore")
        for m in pattern.finditer(txt):
            k = m.group(1)
            if k not in i18n.STRINGS["ar"]:
                missing_ar.add((str(p), k))
            if k not in i18n.STRINGS["en"]:
                missing_en.add((str(p), k))
    assert not missing_ar, f"Missing Arabic keys: {sorted(missing_ar)}"
    assert not missing_en, f"Missing English keys: {sorted(missing_en)}"


def test_router_parser_filters_tr069_js_noise_and_zero_duplicates() -> None:
    html = """
    <input name="x=InternetGatewayDevice.LANDevice.1.LANHostConfigManagement.IPInterface.1" value="0" />
    <input name="frame_egypt" value="0" />
    <input name="ssid_24" value="Home_Fiber" />
    <input name="ssid_24" value="Home_Fiber" />
    <input name="lan_ip" value="192.168.1.1" />
    <script>
      var ssid_5 = "Home_Fiber_5G";
      var frame_egypt = 0;
      var dummy_var = 0;
    </script>
    """
    parsed_items = RouterConfigurationParser.parse_html_inputs(
        html, page_name="wlanbasicsettings.html", section="Wi-Fi"
    )
    parsed = {item.setting_key: item.current_value for item in parsed_items}
    assert "Home_Fiber" in parsed.values() or parsed.get("ssid_24") == "Home_Fiber"
    assert not any("InternetGatewayDevice" in k for k in parsed)
    assert "frame_egypt" not in parsed
    assert "dummy_var" not in parsed

    kv_items = RouterConfigurationParser.parse_key_values(
        {"lan_ip": "192.168.1.1", "frame_egypt": "0", "x=InternetGatewayDevice.LANDevice.1": "0"},
        page_name="dhcp.html",
        section="LAN",
    )
    kv_pairs = {item.setting_key: item.current_value for item in kv_items}
    assert kv_pairs.get("lan_ip") == "192.168.1.1"
    assert "frame_egypt" not in kv_pairs
    assert not any("InternetGatewayDevice" in k for k in kv_pairs)


def test_health_score_calculation_honest_none_without_probes() -> None:
    score, status, _ = compute_genuine_health_score()
    assert score is None
    assert status == tokens.SystemStatus.WAITING

    score_good, status_good, _ = compute_genuine_health_score(
        gw_ms=3.0, ext_ms=18.0, loss_pct=0.0, jitter_ms=2.0, dns_ms=14.0, wifi_pct=88.0
    )
    assert score_good is not None and score_good >= 90
    assert status_good == tokens.SystemStatus.HEALTHY


def test_circular_gauge_and_flowchart_and_qos_matrix_states() -> None:
    _ensure_qapp()
    gauge = CircularGauge(title="Health", unit="%")
    gauge.set_value(None, subtitle="Not measured")
    gauge.set_value(84.0, subtitle="Healthy")

    fc = InvestigationFlowchartWidget()
    fc.update_stage("signal_analysis", state="running", evidence_summary="Scanning WLAN")
    fc.update_stage("signal_analysis", state="completed", evidence_summary="RSSI -48 dBm", details="Channel 44")
    sig_idx = next(i for i, st in enumerate(fc._stages) if st.stage_id == "signal_analysis")
    fc._on_stage_selected(sig_idx)
    assert "RSSI -48 dBm" in fc.lbl_stage_evidence.text() and "Channel 44" in fc.lbl_stage_evidence.text()

    matrix = QoSPolicyMatrixWidget()
    cfg = AppQoSConfig()
    matrix.refresh_from_controller(
        qos_config=cfg,
        active_specs=[],
        os_policies=[],
        meeting_active=True,
        active_apps=["zoom.exe"],
        uplink_mbps=20.0,
    )
    assert matrix.table.rowCount() >= 3


def test_internet_quality_unmeasured_labels_and_settings_validation() -> None:
    _ensure_qapp()
    iq = InternetQualityView()
    assert "غير مُقاس" in iq.card_dl[2].text()
    assert "بانتظار القياس" not in iq.card_dl[2].text()

    sv = SettingsView()
    sv.input_update_source.setText("ftp://invalid-scheme")
    ok, err = sv.validate_inputs()
    assert not ok
    assert err

    sv.input_update_source.setText("https://updates.example.com/version.json")
    ok2, _ = sv.validate_inputs()
    assert ok2

    sv._on_reset_clicked()
    assert sv.mode_combo.currentData() == OperatingMode.AUTO.value


def test_about_view_and_10_section_rtl_ltr_switch() -> None:
    app = _ensure_qapp()
    about = AboutView()
    assert about.badge_elevated is not None

    from unittest.mock import MagicMock
    from app.core.events.bus import EventBus

    app_mock = MagicMock()
    app_mock.traffic_controller = None
    app_mock.orchestrator = None
    app_mock.ctx = MagicMock()
    app_mock.ctx.platform = None
    app_mock.ctx.db = None
    app_mock.ctx.measurements = None
    app_mock.ctx.incidents = None
    app_mock.ctx.event_bus = EventBus()
    app_mock.settings = None

    win = MainWindow(app_mock)
    assert win.stack.count() == 10
    assert len(win.nav_buttons) == 10

    i18n.set_language("en")
    app.processEvents()
    assert app.layoutDirection() == Qt.LeftToRight

    i18n.set_language("ar")
    app.processEvents()
    assert app.layoutDirection() == Qt.RightToLeft
    win.close()


def test_router_parser_preserves_valid_zero_false_states_and_multi_dhcp_instances() -> None:
    """Ensure numeric 0, boolean False, null/empty/unsupported/parse_error, and separate DHCP instances are preserved."""
    from app.wifi.router.models_config import SettingValueState

    payload = {
        "channel": 0,
        "tx_power": "0",
        "dhcp_lease_time_sec": 0,
        "vlan_id": 0,
        "dhcp_enabled": False,
        "upnp_enabled": "0",
        "enblMainUpnp": "0",
        "macFilterMax": "",
        "wan_ip": None,
        "dns_relay": {"value": "Unsupported", "unsupported": True},
        "legacy_field": {"value": "bad", "parse_error": True, "error": "Invalid integer"},
        "InternetGatewayDevice.LANDevice.1.LANHostConfigManagement.DHCPServerEnable": "1",
        "InternetGatewayDevice.LANDevice.1.LANHostConfigManagement.MinAddress": "192.168.1.2",
        "InternetGatewayDevice.LANDevice.1.LANHostConfigManagement.DHCPLeaseTime": "86400",
        "InternetGatewayDevice.LANDevice.2.LANHostConfigManagement.DHCPServerEnable": "0",
        "InternetGatewayDevice.LANDevice.2.LANHostConfigManagement.MinAddress": "192.168.2.10",
        "InternetGatewayDevice.LANDevice.2.LANHostConfigManagement.DHCPLeaseTime": "0",
    }
    records = RouterConfigurationParser.parse_key_values(
        payload, page_name="dhcp2.asp", section="LAN & DHCP"
    )
    by_key_inst = {(r.setting_key, r.instance_id): r for r in records}

    # Numeric zero & boolean false MUST NOT be discarded
    assert by_key_inst[("channel", "")].value_state == SettingValueState.NUMERIC_ZERO
    assert by_key_inst[("channel", "")].typed_value == 0
    assert by_key_inst[("tx_power", "")].value_state == SettingValueState.NUMERIC_ZERO
    assert by_key_inst[("dhcp_lease_time_sec", "")].value_state == SettingValueState.NUMERIC_ZERO
    assert by_key_inst[("vlan_id", "")].value_state == SettingValueState.NUMERIC_ZERO
    assert by_key_inst[("dhcp_enabled", "")].value_state == SettingValueState.BOOLEAN_FALSE
    assert by_key_inst[("dhcp_enabled", "")].typed_value is False
    assert by_key_inst[("upnp_enabled", "")].value_state == SettingValueState.BOOLEAN_FALSE
    assert by_key_inst[("enblMainUpnp", "")].value_state == SettingValueState.BOOLEAN_FALSE

    # Distinct empty, null, unsupported, parse_error states
    assert by_key_inst[("macFilterMax", "")].value_state == SettingValueState.EMPTY_STRING
    assert by_key_inst[("wan_ip", "")].value_state == SettingValueState.NULL
    assert by_key_inst[("dns_relay", "")].value_state == SettingValueState.UNSUPPORTED
    assert by_key_inst[("legacy_field", "")].value_state == SettingValueState.PARSE_ERROR

    # Multiple DHCP instances (LANDevice.1 and LANDevice.2) must BOTH survive parsing & inspection
    assert by_key_inst[("MinAddress", "LANDevice.1")].current_value == "192.168.1.2"
    assert by_key_inst[("MinAddress", "LANDevice.2")].current_value == "192.168.2.10"
    assert by_key_inst[("DHCPServerEnable", "LANDevice.2")].value_state == SettingValueState.BOOLEAN_FALSE
    assert by_key_inst[("DHCPLeaseTime", "LANDevice.2")].value_state == SettingValueState.NUMERIC_ZERO


def test_latency_plot_and_wifi_router_views_runtime_contracts():
    """Regression guard: single-point LatencyPlotCanvas paint, WifiInterfaceTelemetry fields, and RouterManagementView auth contract."""
    import os
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from PySide6.QtWidgets import QApplication
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    qapp = QApplication.instance() or QApplication([])
    from app.wifi.models import (
        RouterAuthResult,
        RouterCapabilities,
        RouterConfigurationSnapshot,
        RouterDiscoveryResult,
        WifiInterfaceTelemetry,
        WlanEventRecord,
    )
    from app.ui.views.wifi_intelligence_view import WifiIntelligenceView
    from app.ui.views.router_management_view import RouterManagementView
    from app.ui.widgets.latency_chart import LatencyPlotCanvas

    # 1. Single-sample LatencyPlotCanvas must render without ZeroDivisionError
    canvas = LatencyPlotCanvas()
    canvas.resize(400, 180)
    canvas.set_data([78.0])
    canvas.grab()
    canvas.close()

    # 2. WifiIntelligenceView consumes real WifiInterfaceTelemetry Pydantic fields
    wv = WifiIntelligenceView(app_core=None)
    tel = WifiInterfaceTelemetry(
        interface_name="Wi-Fi",
        connection_state="connected",
        ssid="Test_5G",
        bssid="AA:BB:CC:DD:EE:FF",
        phy_standard="802.11ax",
        band="5 GHz",
        channel=44,
        rssi_dbm=-55,
        signal_quality_pct=84,
        rx_link_rate_mbps=866,
        tx_link_rate_mbps=866,
        recent_wlan_events=[
            WlanEventRecord(event_id=8001, timestamp=datetime.now(timezone.utc), event_type="connected", message="OK")
        ],
    )
    wv._render_telemetry(tel)
    assert wv.table_metrics.item(0, 1).text().strip("\u2066\u2069") == "Test_5G"
    assert wv.table_wlan_events.rowCount() == 1
    wv.shutdown()
    wv.close()

    # 3. RouterManagementView unpacks 5-tuple cleanly when password is empty & calls RouterAuthCoordinator correctly
    mock_bundle = MagicMock()
    mock_disc = RouterDiscoveryResult(
        gateway_ip="192.168.1.1",
        detected_vendor="Huawei",
        preferred_url="https://192.168.1.1",
        adapter_id="huawei",
        capabilities=RouterCapabilities(adapter_id="huawei", vendor_family="Huawei"),
    )
    mock_bundle.router_auth.load_saved_credentials.return_value = None
    mock_app_core = MagicMock()
    mock_app_core.wifi_bundle = mock_bundle
    rv = RouterManagementView(app_core=mock_app_core)
    rv._discovery = mock_disc
    rv.inp_password.clear()
    rv.show()
    rv.run_router_login_and_read()
    import time
    for _ in range(60):
        qapp.processEvents()
        if rv.btn_login_read.isEnabled():
            break
        time.sleep(0.02)
    qapp.processEvents()
    assert rv.btn_login_read.isEnabled()
    assert not rv.lbl_auth_feedback.isHidden()
    assert rv.lbl_auth_feedback.text()
    rv.shutdown()
    rv.close()

