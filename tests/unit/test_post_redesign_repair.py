"""Post-redesign corrective engineering acceptance tests (Phases 2–13)."""

from __future__ import annotations

import asyncio
import os
import time
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QScrollArea

from app.core.network_state import (
    GlobalNetworkState,
    GlobalNetworkStateStore,
    normalize_network_identity_payload,
)
from app.core.perf import PerfMetricsCollector
from app.core.updater import UpdateChecker
from app.ui import tokens
from app.ui.views.dashboard_view import compute_genuine_health_score
from app.ui.views.meeting_guard_view import MeetingGuardView
from app.ui.views.remediation_view import RemediationView
from app.ui.views.router_management_view import RouterManagementView
from app.ui.views.wifi_intelligence_view import WifiIntelligenceView
from app.ui.widgets.async_bridge import AsyncViewBridge
from app.ui.widgets.channel_spectrum_chart import ChannelSpectrumChart
from app.ui.widgets.flowchart_widget import InvestigationFlowchartWidget
from app.wifi.models import MeasurementProvenance, NeighborAccessPoint
from app.wifi.router.parser import RouterConfigurationParser, is_technical_or_masked_setting


def _ensure_qapp() -> QApplication:
    app = QApplication.instance()
    return app if app is not None else QApplication([])


def test_global_network_state_all_scenarios() -> None:
    """Authoritative 7-layer state never contradicts Wi-Fi telemetry or fakes 97% offline."""
    # 1. Disconnected adapter
    st_off = GlobalNetworkState()
    st_badge_off, lbl_off = st_off.format_status_badge("ar")
    assert st_badge_off == tokens.SystemStatus.NOT_CONNECTED
    assert "غير متصل" in lbl_off
    sc_off, sev_off, _ = st_off.evaluate_diagnostic_status()
    assert sc_off == 0 and sev_off == tokens.SystemStatus.FAILED

    # 2. Connected locally + Internet available + DNS available -> HEALTHY
    st_ok = GlobalNetworkState(
        adapter_connected=True,
        adapter_name="Wi-Fi",
        medium="wifi",
        local_ip="192.168.1.3",
        wifi_associated=True,
        ssid="Mohamed_khaled",
        gateway_ip="192.168.1.1",
        gateway_reachable=True,
        gateway_latency_ms=3.0,
        internet_available=True,
        external_latency_ms=28.0,
        external_packet_loss_pct=0.0,
        jitter_ms=2.0,
        dns_available=True,
        dns_latency_ms=14.0,
        signal_quality_pct=92.0,
    )
    b_ok, lbl_ok = st_ok.format_status_badge("ar")
    assert b_ok == tokens.SystemStatus.HEALTHY
    assert "غير متصل" not in lbl_ok
    sc_ok, sev_ok, _ = st_ok.evaluate_diagnostic_status()
    assert sc_ok is not None and sc_ok >= 90 and sev_ok == tokens.SystemStatus.HEALTHY

    # 3. Connected to Wi-Fi + Gateway reachable + Internet UNREACHABLE -> WARNING + capped score
    st_no_net = GlobalNetworkState(
        adapter_connected=True,
        medium="wifi",
        local_ip="192.168.1.3",
        wifi_associated=True,
        ssid="Mohamed_khaled",
        gateway_ip="192.168.1.1",
        gateway_reachable=True,
        gateway_latency_ms=2.5,
        internet_available=False,
        external_packet_loss_pct=100.0,
        dns_available=False,
    )
    b_nn, lbl_nn = st_no_net.format_status_badge("ar")
    assert b_nn == tokens.SystemStatus.WARNING
    assert "بدون إنترنت" in lbl_nn
    sc_nn, sev_nn, _ = st_no_net.evaluate_diagnostic_status()
    assert sc_nn is not None and sc_nn <= 40 and sev_nn == tokens.SystemStatus.FAILED

    # Also compute_genuine_health_score must never return >= 80 when 100% packet loss
    sc_dash, sev_dash, _ = compute_genuine_health_score(
        gw_ms=2.5, ext_ms=None, loss_pct=100.0, wifi_pct=99.0, internet_available=False
    )
    assert sc_dash is not None and sc_dash <= 40 and sev_dash == tokens.SystemStatus.FAILED

    # 4. Gateway unreachable while Wi-Fi associated -> WARNING / FAILED
    st_no_gw = GlobalNetworkState(
        adapter_connected=True,
        medium="wifi",
        local_ip="192.168.1.3",
        wifi_associated=True,
        ssid="Mohamed_khaled",
        gateway_reachable=False,
    )
    b_ng, lbl_ng = st_no_gw.format_status_badge("ar")
    assert b_ng == tokens.SystemStatus.WARNING and "البوابة" in lbl_ng

    # 5. Incomplete measurements -> score is None (no fabrication)
    st_inc = GlobalNetworkState(
        adapter_connected=True,
        medium="wifi",
        local_ip="192.168.1.3",
        wifi_associated=True,
        gateway_ip="192.168.1.1",
    )
    sc_inc, sev_inc, _ = st_inc.evaluate_diagnostic_status()
    assert sc_inc is None and sev_inc == tokens.SystemStatus.WAITING


def test_normalize_network_identity_iface_and_gateway_keys() -> None:
    """`iface`, `gateway`, `dns` from Windows probe normalize cleanly without 'غير متصل' bug."""
    norm = normalize_network_identity_payload(
        {
            "iface": "Wi-Fi",
            "gateway": "192.168.1.1",
            "local_ip": "192.168.1.3",
            "ssid": "Mohamed_khaled",
            "is_wifi": True,
            "signal": "99%",
            "band": "802.11ac",
            "dns": ["1.1.1.1", "1.0.0.1"],
        }
    )
    assert norm["interface_name"] == "Wi-Fi"
    assert norm["gateway_ip"] == "192.168.1.1"
    assert norm["dns_servers"] == ["1.1.1.1", "1.0.0.1"]

    store = GlobalNetworkStateStore()
    st = store.update_from_network_info(norm)
    assert st.is_local_link_up is True
    badge, lbl = st.format_status_badge("ar")
    assert badge != tokens.SystemStatus.NOT_CONNECTED
    assert "غير متصل" not in lbl


def test_meeting_guard_controls_no_nested_scroll_and_cleanup_readback() -> None:
    _ensure_qapp()

    class _FakePlatform:
        def __init__(self) -> None:
            self.swept = False

        def get_netguard_qos_policies(self):
            return [] if self.swept else [{"name": "NetGuard_Test", "dscp_action": 46}]

        def sweep_all_netguard_rules(self):
            self.swept = True
            return True, "Swept"

    plat = _FakePlatform()
    view = MeetingGuardView(platform=plat)
    # Embedded RemediationView must not wrap in a nested QScrollArea
    inner_scrolls = view.remediation_section.findChildren(QScrollArea)
    assert len(inner_scrolls) == 0

    standalone_rem = RemediationView(embed_in_scroll=False)
    assert len(standalone_rem.findChildren(QScrollArea)) == 1
    standalone_rem.close()

    # Working controls exist & function
    assert hasattr(view, "btn_start_monitor")
    assert hasattr(view, "btn_stop_monitor")
    assert hasattr(view, "btn_calibrate")
    assert hasattr(view, "btn_retry_detect")
    assert hasattr(view, "btn_kill_switch")

    view.start_monitoring()
    assert view.qos_config.master_enabled is True
    view.stop_monitoring()
    assert view._monitoring_paused is True

    # Trigger cleanup and wait briefly for background sweep + readback
    view._on_kill_switch_clicked()
    deadline = time.time() + 2.0
    while not plat.swept and time.time() < deadline:
        QApplication.processEvents()
        time.sleep(0.02)
    assert plat.swept is True
    assert view.qos_config.master_enabled is False
    view.close()


def test_wifi_band_normalization_spectrum_and_snr_separation() -> None:
    _ensure_qapp()
    aps = [
        NeighborAccessPoint(ssid="TestNet5", bssid="AA:BB:CC:DD:EE:01", band="5 GHz", channel=44, center_frequency_mhz=5220, rssi_dbm=-62),
        NeighborAccessPoint(ssid="TestNet24", bssid="AA:BB:CC:DD:EE:02", band="2.4 GHz", channel=6, center_frequency_mhz=2437, rssi_dbm=-55),
    ]
    chart = ChannelSpectrumChart()
    chart.set_data(band="5 GHz", access_points=aps, current_channel=44, recommended_channel=36)
    assert len(chart._access_points) == 1
    assert chart._access_points[0].ssid == "TestNet5"
    # Even unspaced input normalizes safely
    chart.set_data(band="5GHz", access_points=aps)
    assert len(chart._access_points) == 1
    chart.close()

    view = WifiIntelligenceView()
    assert view._selected_band == "5 GHz"
    tel = SimpleNamespace(
        connected=True,
        connection_state="connected",
        ssid="Mohamed_khaled",
        bssid="11:22:33:44:55:66",
        interface_name="Wi-Fi",
        band="5 GHz",
        channel=44,
        rssi_dbm=-62,
        signal_quality_pct=99,
        noise_floor_dbm=None,
        snr_db=None,
        rx_link_rate_mbps=86.7,
        tx_link_rate_mbps=86.7,
        phy_standard="802.11ac",
        events=[],
    )
    view._render_telemetry(tel)
    # SNR must NOT be fabricated when noise_floor_dbm is None
    assert "غير متاح" in view._ap_rssi_snr[1].text()
    # Check metrics table separates Signal Quality % vs RSSI dBm vs Noise Floor vs SNR
    rows_by_name = {
        view.table_metrics.item(r, 0).text(): (
            view.table_metrics.item(r, 1).text(),
            view.table_metrics.item(r, 2).text(),
        )
        for r in range(view.table_metrics.rowCount())
    }
    assert "99" in rows_by_name["Signal Quality (%)"][0]
    assert "-62" in rows_by_name["RSSI (dBm)"][0]
    assert rows_by_name["Noise Floor (dBm)"][1] == "Unavailable"
    assert rows_by_name["SNR (dB)"][1] == "Unavailable"
    view.shutdown()
    view.close()


def test_router_boolean_zero_masked_flag_isolation_and_provenance() -> None:
    _ensure_qapp()
    kv = {
        "wifi_5_enabled": "0",
        "wifi_24_enabled": "1",
        "channel": 0,
        "Wifipasswordmask": "********",
        "Pwdtipsflag": "1",
        "Megacablepwd": "secret",
        "Noappinflag": "0",
        "Pinnote": "note",
        "Pinnumber": "12345678",
        "lan_ip": "192.168.1.1",
    }
    recs = RouterConfigurationParser.parse_key_values(
        kv, page_name="WLAN", section="Wireless", default_domain="wifi_5"
    )
    by_key = {r.setting_key: r for r in recs}

    assert by_key["wifi_5_enabled"].value_state.value == "boolean_false"
    assert RouterManagementView._format_setting_value(by_key["wifi_5_enabled"]) == "معطّل (Disabled)"
    assert RouterManagementView._format_setting_value(by_key["wifi_24_enabled"]) == "مفعّل (Enabled)"
    assert by_key["channel"].value_state.value == "numeric_zero"
    assert "0" in by_key["channel"].current_value

    # Masked / internal UI form flags must be isolated to advanced_technical
    for internal_k in ("Wifipasswordmask", "Pwdtipsflag", "Megacablepwd", "Noappinflag", "Pinnote", "Pinnumber"):
        assert is_technical_or_masked_setting(internal_k) is True
        assert by_key[internal_k].domain == "advanced_technical"

    # Provenance must never render raw "MeasurementProvenance.ROUTER_REPORTED"
    prov_txt = RouterManagementView._format_provenance(MeasurementProvenance.ROUTER_REPORTED)
    assert "MeasurementProvenance" not in prov_txt
    assert prov_txt == "مبلّغ من الراوتر"


def test_reports_flowchart_enforces_prerequisites_against_premature_final_report() -> None:
    _ensure_qapp()
    fc = InvestigationFlowchartWidget()
    fc.update_stage("network_scan", state="completed", evidence_summary="Done")
    fc.update_stage("data_collection", state="completed", evidence_summary="Done")
    # Stage 4 (traffic_analysis), Stage 7 (router_analysis), 9..13 still 'waiting'!
    allowed = fc.update_stage("final_report", state="completed", evidence_summary="Ready")
    assert allowed is False
    assert fc.get_stage_state("final_report") != "completed"
    assert fc.can_finalize_report() is False

    # Now complete or skip all prerequisites 1..13
    for st_id in (
        "signal_analysis",
        "traffic_analysis",
        "latency_analysis",
        "dns_analysis",
        "router_analysis",
        "root_cause",
        "recommendation",
        "user_approval",
        "config_change",
        "verification",
        "before_after",
    ):
        fc.update_stage(st_id, state="completed" if st_id != "config_change" else "skipped", evidence_summary="OK")

    assert fc.can_finalize_report() is True
    allowed_after = fc.update_stage("final_report", state="completed", evidence_summary="Export ready")
    assert allowed_after is True
    assert fc.get_stage_state("final_report") == "completed"
    fc.close()


def test_async_bridge_op_key_dedup_and_updater_fast_unc_fail() -> None:
    _ensure_qapp()
    PerfMetricsCollector.get_instance().reset()
    bridge = AsyncViewBridge(max_workers=2)
    results = []

    async def _slow():
        await asyncio.sleep(0.15)
        return 42

    t1 = bridge.run_coro(_slow, lambda v: results.append(v), op_key="test_dedup", timeout_sec=2.0)
    t2 = bridge.run_coro(_slow, lambda v: results.append(v), op_key="test_dedup", timeout_sec=2.0)
    assert t1 is not None
    assert t2 is None  # Deduplicated!

    deadline = time.time() + 2.0
    while not results and time.time() < deadline:
        QApplication.processEvents()
        time.sleep(0.02)
    assert results == [42]
    snap = PerfMetricsCollector.get_instance().snapshot()
    assert snap["counters"].get("dedup_skip:test_dedup", 0) >= 1
    bridge.shutdown()

    # Updater UNC fast-fail: unreachable UNC host should fail within ~0.6s, not hang SMB for 3-20s
    checker = UpdateChecker(check_url=r"\\192.0.2.254\Updates\version.json")
    failed_msgs = []
    checker.check_failed.connect(lambda m: failed_msgs.append(m))
    t0 = time.perf_counter()
    checker.check_for_updates_async()
    deadline = time.time() + 2.5
    while not failed_msgs and time.time() < deadline:
        QApplication.processEvents()
        time.sleep(0.02)
    elapsed = time.perf_counter() - t0
    assert failed_msgs, "Expected UNC check failure on unreachable TEST-NET host"
    assert elapsed < 1.5, f"UNC fail took too long: {elapsed:.2f}s"


def test_netsh_bssid_parser_and_compact_router_wifi_tables() -> None:
    _ensure_qapp()
    from app.wifi.scanner import parse_netsh_networks_output

    sample_netsh = """
Interface name : Wi-Fi
There are 3 networks currently visible.

SSID 1 : Neighbor24
    Network type            : Infrastructure
    Authentication          : WPA2-Personal
    Encryption              : CCMP
    BSSID 1                 : d4:6b:a6:fa:fa:d0
         Signal             : 60%
         Radio type         : 802.11n
         Band               : 2.4 GHz
         Channel            : 1

SSID 2 : Neighbor5G
    Network type            : Infrastructure
    Authentication          : WPA3-Personal
    Encryption              : CCMP
    BSSID 1                 : 24:79:ef:3a:a3:c1
         Signal             : 84%
         Radio type         : 802.11ax
         Band               : 5 GHz
         Channel            : 36
"""
    entries = parse_netsh_networks_output(sample_netsh)
    assert len(entries) == 2
    assert entries[0].ssid == "Neighbor24" and entries[0].channel == 1 and entries[0].band == "2.4 GHz"
    assert entries[1].ssid == "Neighbor5G" and entries[1].channel == 36 and entries[1].band == "5 GHz"
    assert entries[1].rssi_dbm == -58

    rv = RouterManagementView(app_core=None)
    wv = WifiIntelligenceView(app_core=None)
    try:
        assert hasattr(rv, "btn_connect_router")
        assert rv.btn_login_read is rv.btn_connect_router
        assert rv.chk_security_ack.isChecked() is True
        # Empty router/wifi tables start compact instead of stretching into blank voids
        for tbl in (rv.table_wifi, rv.table_wan, rv.table_lan, rv.table_devices, rv.table_coverage):
            assert tbl.maximumHeight() <= 90
        for tbl in (wv.table_channels, wv.table_metrics, wv.table_bss):
            assert tbl.maximumHeight() <= 90
    finally:
        rv.shutdown()
        wv.shutdown()
        rv.close()
        wv.close()


def test_huawei_dn8245v_full_read_write_and_wifi_plain_summary() -> None:
    """Verify Huawei Web ASP hex unescape + real set.cgi write/readback + plain Egyptian summary."""
    import http.server
    import threading
    from app.wifi.models import RouterChangeProposal
    from app.wifi.router.adapters.huawei import HuaweiRouterAdapter
    from app.wifi.router.adapters.registry import RouterAdapterRegistry

    _ensure_qapp()
    state = {"ch5": "44", "qos": "0", "upnp": "1"}

    class _Srv(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_GET(self):
            if self.path == "/":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"<script>var ProductName='DN8245V\\x2d56';</script>")
            elif self.path in ("/asp/GetRandCount.asp", "/html/ssmp/common/getrand.asp"):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"tok_hw_123")
            elif self.path == "/html/ssmp/devinfo/devinfo.asp":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"<script>var SoftwareVersion='V5R020C10\\x2e1';</script>")
            elif self.path == "/html/amp/wlanbasic/WlanBasic5G.asp":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(
                    f'<script>new stWlanWifi("InternetGatewayDevice.LANDevice.1.WLANConfiguration.5","ath4","1","Mohamed\\x5fkhaled","11ac","{state["ch5"]}","100","EG","0","3");</script>'.encode()
                )
            elif self.path == "/html/bbsp/qos/qos.asp":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(f"<script>var QoSEnable='{state['qos']}';</script>".encode())
            elif self.path == "/html/bbsp/upnp/upnp.asp":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(f"<script>var Enable='{state['upnp']}';</script>".encode())
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or "0")
            body = self.rfile.read(n).decode("utf-8", "replace")
            if self.path == "/login.cgi":
                self.send_response(200)
                self.send_header("Set-Cookie", "Cookie=sid_ok")
                self.end_headers()
                self.wfile.write(b"window.location='/index.asp';")
            elif "/html/amp/wlanbasic/set.cgi" in self.path and "x.Channel=100" in body:
                state["ch5"] = "100"
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
            elif "/html/bbsp/qos/set.cgi" in self.path and "x.Enable=1" in body:
                state["qos"] = "1"
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
            else:
                self.send_response(404)
                self.end_headers()

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Srv)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        url = f"http://127.0.0.1:{srv.server_port}"
        reg = RouterAdapterRegistry(allow_loopback=True)
        ad = reg.get_adapter("huawei")
        assert isinstance(ad, HuaweiRouterAdapter)
        auth = ad.authenticate(base_url=url, username="admin", password="pw")
        assert auth.authenticated is True
        assert ad in reg.list_adapters()
        assert ad.capabilities().supports_channel_write is True

        snap = ad.read_config()
        assert snap.firmware_version == "V5R020C10.1"
        assert snap.radios["5 GHz"].ssid == "Mohamed_khaled"
        assert snap.radios["5 GHz"].channel == "44"

        res = ad.safe_apply_change(
            RouterChangeProposal(
                proposal_id="ch5_100",
                category="wifi_channel",
                title="Switch 5G",
                target_field="channel",
                band="5 GHz",
                current_value="44",
                proposed_value="100",
                reason="Clean channel",
                expected_impact="Less congestion",
                supported_by_adapter=True,
                requires_manual_apply=False,
            ),
            explicit_user_approval=True,
        )
        assert res.success is True and res.readback_verified is True and res.verified_value == "100"

        res_qos = ad.safe_apply_change(
            RouterChangeProposal(
                proposal_id="qos_on",
                category="qos_sqm",
                title="Enable QoS",
                target_field="qos_enabled",
                current_value="معطّل",
                proposed_value="مفعّل",
                reason="Prioritize calls",
                expected_impact="Lower latency",
                supported_by_adapter=True,
                requires_manual_apply=False,
            ),
            explicit_user_approval=True,
        )
        assert res_qos.success is True and state["qos"] == "1"

        assert WifiIntelligenceView._quality_pct_from_penalty(0.0) == 100.0
        assert WifiIntelligenceView._quality_pct_from_penalty(14.0) == 50.0
    finally:
        srv.shutdown()
        srv.server_close()


def test_dialog_buttons_band_switch_and_channel_action_entry_handling(monkeypatch) -> None:
    """Regression proof for dialog button separation, 2.4/5 GHz switching, Huawei HTML response, and ActionHistoryEntry."""
    import http.server
    import threading
    from types import SimpleNamespace
    from PySide6.QtWidgets import QMessageBox
    from app.ui.views.router_management_view import RouterChangePreviewDialog
    from app.ui.views.wifi_intelligence_view import WifiIntelligenceView
    from app.wifi import build_wifi_bundle
    from app.wifi.models import AccessPointScanResult, NeighborAccessPoint, RouterChangeProposal
    from app.wifi.optimization import ActionHistoryEntry, ActionLifecycleState
    from app.wifi.router.adapters.huawei import HuaweiRouterAdapter

    _ensure_qapp()

    # 1. RouterChangePreviewDialog uses distinct Primary/Secondary buttons with zero overlap
    prop = RouterChangeProposal(
        proposal_id="ch_test",
        category="wifi_channel",
        title="نقل قناة الواي فاي (5 GHz) إلى القناة 36",
        target_field="channel",
        band="5 GHz",
        current_value="44",
        proposed_value="36",
        reason="تخفيف التداخل",
        expected_impact="تقليل التقطيع",
        requires_reconnect_warning=True,
        supported_by_adapter=True,
        requires_manual_apply=False,
    )
    dlg = RouterChangePreviewDialog(prop)
    dlg.show()
    QApplication.processEvents()
    assert not dlg.btn_apply.geometry().intersects(dlg.btn_cancel.geometry())
    assert dlg.btn_apply.width() >= 96 and dlg.btn_cancel.width() >= 96
    dlg.close()

    # 2. Huawei set.cgi returning ASP page with 'referrer'/'errMsg' must not false-fail
    state = {"ch5": "44"}

    class _HwHtmlSrv(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_GET(self):
            if self.path == "/":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"<script>var ProductName='DN8245V-56';</script>")
            elif self.path in ("/asp/GetRandCount.asp", "/html/ssmp/common/getrand.asp"):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"tok_hw_xyz")
            elif self.path == "/html/amp/wlanbasic/WlanBasic5G.asp":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(
                    f'<script>new stWlanWifi("InternetGatewayDevice.LANDevice.1.WLANConfiguration.5","ath4","1","Mohamed","11ac","{state["ch5"]}","100","EG","0","3");</script>'.encode()
                )
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"")

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or "0")
            body = self.rfile.read(n).decode("utf-8", "replace")
            if self.path == "/login.cgi":
                self.send_response(200)
                self.send_header("Set-Cookie", "Cookie=sid_ok2")
                self.end_headers()
                self.wfile.write(b"window.location='/index.asp';")
            elif "/html/amp/wlanbasic/set.cgi" in self.path and "x.Channel=36" in body:
                state["ch5"] = "36"
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"<html><script>var errMsg=''; var r = document.referrer;</script></html>")
            else:
                self.send_response(404)
                self.end_headers()

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _HwHtmlSrv)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        hw = HuaweiRouterAdapter(allow_loopback=True)
        assert hw.authenticate(base_url=f"http://127.0.0.1:{srv.server_port}", username="admin", password="pw").authenticated
        res = hw.safe_apply_change(prop, explicit_user_approval=True)
        assert res.success is True and res.verified_value == "36"
    finally:
        srv.shutdown()
        srv.server_close()

    # 3. WifiIntelligenceView handles ActionHistoryEntry (no .success attr) + 2.4 GHz band switching
    bundle = build_wifi_bundle(allow_loopback=True)
    app_core = SimpleNamespace(wifi_bundle=bundle)
    wv = WifiIntelligenceView(app_core=app_core)
    popups = []
    monkeypatch.setattr(QMessageBox, "information", lambda _p, title, text: popups.append((title, text)))
    monkeypatch.setattr(wv, "refresh_wifi_and_rf", lambda **_kw: None)

    aps = [
        NeighborAccessPoint(ssid="N24", bssid="aa:bb:cc:dd:ee:01", band="2.4 GHz", channel=6, center_frequency_mhz=2437, rssi_dbm=-55),
        NeighborAccessPoint(ssid="N5", bssid="aa:bb:cc:dd:ee:02", band="5 GHz", channel=44, center_frequency_mhz=5220, rssi_dbm=-64),
    ]
    scan = AccessPointScanResult(interface_name="Wi-Fi", total_bss_count=2, access_points=aps)
    wv._last_scan = scan
    wv._last_tel = SimpleNamespace(band="5 GHz", channel=44, bssid="aa:bb:cc:dd:ee:02")
    wv._last_ch_report = bundle.channel_analyzer.analyze(scan_result=scan, current_band="5 GHz", current_channel=44)
    wv._on_band_changed(0, "2.4 GHz")
    assert wv._selected_band == "2.4 GHz"
    assert "2.4 GHz" in wv.btn_optimize_channel.text()
    assert wv.spectrum_chart._band == "2.4 GHz"
    assert "2.4 GHz" in wv.lbl_plain_summary.text()

    # Verify ActionHistoryEntry SUCCESSFULLY_VERIFIED is recognized as success
    class _FakeWritableAdapter:
        is_authenticated = True

        def capabilities(self):
            return SimpleNamespace(supports_channel_write=True)

    monkeypatch.setattr(
        bundle.optimization,
        "execute_proposal",
        lambda **_kw: ActionHistoryEntry(
            action_id="act_1",
            category="wifi_channel",
            title="Switch",
            target_layer="router",
            reason="Test",
            state=ActionLifecycleState.SUCCESSFULLY_VERIFIED,
            verification_result="Verified applied",
        ),
    )
    wv._execute_channel_change(
        writable_adapter=_FakeWritableAdapter(),
        band="5 GHz",
        curr_ch=44,
        rec_ch=36,
        q_curr=45.0,
        q_rec=95.0,
        interactive=False,
    )
    import time as _t
    for _ in range(50):
        QApplication.processEvents()
        if wv._last_improvement_note:
            break
        _t.sleep(0.02)
    assert "36" in wv._last_improvement_note
    assert len(popups) == 0

    wv.shutdown()
    wv.close()


def test_huawei_page_onttoken_referer_and_router_all_settings_tab() -> None:
    """Verify Huawei set.cgi uses page-embedded onttoken + matching Referer/Origin, and RouterManagementView shows all settings + web portal tab."""
    import http.server
    import threading
    from app.ui.views.router_management_view import RouterManagementView
    from app.wifi.models import RouterCapabilities, RouterChangeProposal, RouterConfigurationSnapshot, RouterDiscoveryResult
    from app.wifi.router.adapters.huawei import HuaweiRouterAdapter
    from app.wifi.router.models_config import InspectionCoverageReport, RouterConfigurationModel, RouterSettingRecord

    _ensure_qapp()
    captured = {"qos_tok": "", "qos_ref": "", "qos_ori": "", "ch_tok": "", "ch_ref": ""}
    state = {"ch5": "44", "qos": "0"}

    class _StrictHwSrv(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_GET(self):
            if self.path == "/":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"<script>var ProductName='DN8245V-56';</script>")
            elif self.path == "/asp/GetRandCount.asp":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"stale_login_tok")
            elif self.path == "/html/amp/wlanbasic/WlanBasic5G.asp":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(
                    (
                        '<input type="hidden" name="onttoken" id="hwonttoken" value="page_tok_5g_abc123">'
                        f'<script>new stWlanWifi("InternetGatewayDevice.LANDevice.1.WLANConfiguration.5","ath4","1","Mohamed","11ac","{state["ch5"]}","100","EG","0","3");</script>'
                    ).encode()
                )
            elif self.path == "/html/bbsp/qos/qos.asp":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(
                    (
                        '<input type="hidden" name="onttoken" id="hwonttoken" value="page_tok_qos_xyz789">'
                        f"<script>var QoSEnable='{state['qos']}';</script>"
                    ).encode()
                )
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"")

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or "0")
            body = self.rfile.read(n).decode("utf-8", "replace")
            ref = self.headers.get("Referer", "")
            ori = self.headers.get("Origin", "")
            if self.path == "/login.cgi":
                self.send_response(200)
                self.send_header("Set-Cookie", "Cookie=sid_strict")
                self.end_headers()
                self.wfile.write(b"window.location='/index.asp';")
            elif "/html/amp/wlanbasic/set.cgi" in self.path:
                captured["ch_tok"] = body
                captured["ch_ref"] = ref
                if "page_tok_5g_abc123" not in body or "WlanBasic5G.asp" not in ref or not ori:
                    self.send_response(403)
                    self.end_headers()
                    return
                state["ch5"] = "36"
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
            elif "/html/bbsp/qos/set.cgi" in self.path:
                captured["qos_tok"] = body
                captured["qos_ref"] = ref
                captured["qos_ori"] = ori
                if "page_tok_qos_xyz789" not in body or "qos.asp" not in ref or not ori:
                    self.send_response(403)
                    self.end_headers()
                    return
                state["qos"] = "1"
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
            else:
                self.send_response(404)
                self.end_headers()

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _StrictHwSrv)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        hw = HuaweiRouterAdapter(allow_loopback=True)
        assert hw.authenticate(base_url=f"http://127.0.0.1:{srv.server_port}", username="admin", password="pw").authenticated
        res_ch = hw.safe_apply_change(
            RouterChangeProposal(
                proposal_id="ch5", category="wifi_channel", title="Ch36",
                target_field="channel", band="5 GHz", current_value="44", proposed_value="36",
                reason="Test", expected_impact="Test", supported_by_adapter=True,
            ),
            explicit_user_approval=True,
        )
        assert res_ch.success is True
        assert "WlanBasic5G.asp" in captured["ch_ref"]

        res_qos = hw.safe_apply_change(
            RouterChangeProposal(
                proposal_id="qos", category="qos_sqm", title="QoS",
                target_field="qos_enabled", current_value="معطّل", proposed_value="مفعّل",
                reason="Test", expected_impact="Test", supported_by_adapter=True,
            ),
            explicit_user_approval=True,
        )
        assert res_qos.success is True
        assert "qos.asp" in captured["qos_ref"]
        assert captured["qos_ori"].startswith("http://127.0.0.1:")
    finally:
        srv.shutdown()
        srv.server_close()

    rv = RouterManagementView(app_core=None)
    assert rv.tab_stack.count() == 8
    rv._discovery = RouterDiscoveryResult(
        gateway_ip="192.168.1.1",
        preferred_url="https://192.168.1.1",
        adapter_id="huawei",
        capabilities=RouterCapabilities(adapter_id="huawei", vendor_family="Huawei"),
    )
    snap = RouterConfigurationSnapshot(adapter_id="huawei", vendor="Huawei", model="DN8245V-56", firewall_level="high")
    model = RouterConfigurationModel(
        snapshot=snap,
        coverage=InspectionCoverageReport(adapter_id="huawei"),
        settings=[
            RouterSettingRecord(setting_key="firewall_level", setting_label="Firewall", setting_label_ar="جدار الحماية", domain="firewall", current_value="high"),
            RouterSettingRecord(setting_key="port_map_1", setting_label="Port Mapping", setting_label_ar="توجيه المنافذ", domain="nat_port_forwarding", current_value="Enabled"),
        ],
    )
    rv._snapshot = snap
    rv._model = model
    rv._render_all_router_data()
    assert rv.table_all_settings.rowCount() == 2
    rv.switch_tab(7)
    assert rv.tab_stack.currentIndex() == 7
    assert rv.inp_web_url.text() == "https://192.168.1.1"
    rv.shutdown()
    rv.close()


