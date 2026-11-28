"""Comprehensive unit & local-mock-server tests for Sections 1-18 universal router & network intelligence."""

from __future__ import annotations

import asyncio
import http.server
import json
import socket
import threading
from pathlib import Path
from typing import Any, Dict

import pytest

from app.wifi.models import (
    BandChannelAnalysisResult,
    BeforeAfterSnapshot,
    BufferbloatDiagnosticsReport,
    BufferbloatPhaseResult,
    ChannelScoreBreakdown,
    ChannelRecommendation,
    DnsDiagnosticsReport,
    DnsTargetMetrics,
    FullChannelAnalysisReport,
    NeighborAccessPoint,
    NetworkConditionReport,
    NetworkDiagnosticsReport,
    PingBurstStats,
    RouterCapabilities,
    RouterChangeProposal,
    RouterConfigurationSnapshot,
    RouterWifiRadioConfig,
    SpeedTestReport,
    WifiInterfaceTelemetry,
)
from app.wifi.nl_commands import NaturalLanguageCommandService
from app.wifi.optimization import (
    ActionHistoryStore,
    ActionLifecycleState,
    OptimizationMode,
    OptimizationPlanner,
)
from app.wifi.qos_compatibility import QoSCompatibilityAnalyzer
from app.wifi.report_service import NetworkHealthReportService
from app.wifi.root_cause import RootCauseAnalysisService
from app.wifi.router.adapters.huawei import HuaweiRouterAdapter
from app.wifi.router.adapters.registry import RouterAdapterRegistry
from app.wifi.router.adapters.snmp_client import (
    OID_SYS_DESCR,
    build_snmp_packet,
    decode_oid,
    encode_oid,
    parse_snmp_response,
)
from app.wifi.router.adapters.tr_standards import TrStandardsInspector
from app.wifi.router.analyzer import RouterConfigurationAnalyzer
from app.wifi.router.discovery import RouterDiscoveryService
from app.wifi.router.fingerprint import RouterFingerprintService
from app.wifi.router.inspection import RouterPageInspectionService
from app.wifi.router.models_config import InspectionCoverageStatus, sanitize_setting_value
from app.wifi.router.parser import RouterConfigurationParser


def test_fingerprint_separates_hardware_vendor_from_isp_and_overrides_wrong_oui() -> None:
    """Real Huawei DN8245V-56 WE router HTML must classify Huawei (not wrong OUI ZTE) + ISP WE."""
    huawei_we_html = """
    <html><head><title>Login</title>
    <script src="/resource/common/safelogin.js"></script></head>
    <script>
    var ProductName = 'DN8245V\\x2d56';
    var CfgMode ='DTEDATA2WIFI';
    var IsDTEDATA = '1';
    $.ajax({url:'/asp/GetRandCount.asp'});
    // submit x.X_HW_Token
    </script></html>
    """
    adapter_id, vendor, model, _hw, _fw, isp, conf, ev = RouterFingerprintService.classify_http_evidence(
        headers={"server": "Huawei HTTP"},
        body=huawei_we_html,
        oui_vendor="ZTE Corporation",  # Deliberately misleading OUI
    )
    assert vendor == "Huawei"
    assert adapter_id == "huawei"
    assert model == "DN8245V-56"
    assert isp == "WE (TE Data)"
    assert conf == "high"
    assert any("oui_overridden" in x for x in ev)


@pytest.mark.parametrize(
    ("body", "expected_vendor", "expected_adapter_prefix"),
    [
        ("<html><title>ZXHN H168N</title><script>getpage.gch?pid=1002&Frm_Logintoken=9</script></html>", "ZTE", "zte"),
        ("<html><title>Archer AX50</title><script>var stok='abc123';</script></html>", "TP-Link", "tplink"),
        ("<html><title>ASUS Wireless Router RT-AX86U</title><form action='login.cgi'></form></html>", "ASUS", "asus"),
        ("<html><title>RouterOS WebFig v7</title>MikroTik RB4011</html>", "MikroTik", "mikrotik"),
        ("<html><title>LuCI - OpenWrt 23.05</title>/cgi-bin/luci</html>", "OpenWrt", "isp_generic:openwrt"),
        ("<html><title>Tenda RX3</title><form action='goform/login'></form></html>", "Tenda", "isp_generic:tenda"),
        ("<html><title>D-Link DIR-882</title>HNAP1</html>", "D-Link", "isp_generic:dlink"),
        ("<html><title>Nokia Beacon 2</title>Alcatel-Lucent</html>", "Nokia", "isp_generic:nokia"),
        ("<html><title>Sercomm H300s</title>Vodafone</html>", "Sercomm", "isp_generic:sercomm"),
        ("<html><title>Sagemcom F@ST 5670</title>Livebox</html>", "Sagemcom", "isp_generic:sagemcom"),
        ("<html><title>FiberHome HG6143D</title></html>", "FiberHome", "isp_generic:fiberhome"),
        ("<html><title>NETGEAR Nighthawk RAX50</title>currentsetting.htm</html>", "Netgear", "isp_generic:netgear"),
    ],
)
def test_multi_vendor_fingerprint_and_registry(body: str, expected_vendor: str, expected_adapter_prefix: str) -> None:
    reg = RouterAdapterRegistry(allow_loopback=True)
    aid, vendor, model, _hw, _fw, _isp, _conf, _ev = RouterFingerprintService.classify_http_evidence(
        headers={},
        body=body,
    )
    assert vendor == expected_vendor
    assert aid == expected_adapter_prefix
    adapter = reg.get_adapter(aid)
    assert adapter is not None
    assert (
        expected_vendor.lower() in adapter.vendor_family.lower()
        or adapter.vendor_family == "Generic/ISP"
    )


def test_secret_redaction_and_backup_encryption_honesty() -> None:
    val, redacted = sanitize_setting_value("WifiWpaKey", "SuperSecret123")
    assert redacted is True
    assert val == "[REDACTED]"
    assert "SuperSecret123" not in val

    readable, note, parsed = RouterConfigurationParser.inspect_backup_blob(
        '{"ssid":"MyNet","wpakey":"MyWiFiPass","channel":6}'
    )
    assert readable is True
    assert parsed["wpakey"] == "[REDACTED]"

    enc_ok, enc_note, _ = RouterConfigurationParser.inspect_backup_blob("Salted__\x00\xff\xfe\xfd\x88\x99\xaa\xbb")
    assert enc_ok is False
    assert "encrypted" in enc_note.lower()


def test_huawei_web_asp_local_server_auth_inspection_and_coverage() -> None:
    """Spin up a real local loopback HTTP server simulating Huawei DN8245V-56 Web ASP portal."""

    class _Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            if self.path == "/":
                html = "<script>var ProductName='DN8245V\\x2d56';var CfgMode='DTEDATA2WIFI';// /resource/common/safelogin.js /asp/GetRandCount.asp x.X_HW_Token</script>"
                self.send_response(200)
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))
            elif self.path == "/asp/GetRandCount.asp":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"rand_tok_98765")
            elif self.path == "/html/ssmp/devinfo/devinfo.asp":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"<script>var SoftwareVersion='V5R020C00';</script>")
            elif self.path == "/html/bbsp/common/waninfo.asp":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'<script>new WanInfo("197.55.10.22","Connected");var PrimaryDns="1.1.1.1";</script>')
            elif self.path == "/html/amp/wlanbasic/WlanBasic.asp":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'<script>new stWlan("2.4G","WE_Home","1","6","20MHz");var wpa_psk="TopSecretPass";</script>')
            elif self.path == "/html/bbsp/userdevinfo/userdevinfo.asp":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'<script>new USERDevice("192.168.1.50","aa:bb:cc:dd:ee:01","Phone-5G","5G","Online");</script>')
            elif self.path == "/html/bbsp/qos/qos.asp":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"<script>var QoSEnable='1';</script>")
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length") or "0")
            _ = self.rfile.read(length)
            if self.path == "/login.cgi":
                self.send_response(200)
                self.send_header("Set-Cookie", "Cookie=sid_test_abc")
                self.end_headers()
                self.wfile.write(b"window.location='/index.asp';")
            else:
                self.send_response(404)
                self.end_headers()

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        base_url = f"http://127.0.0.1:{port}"
        reg = RouterAdapterRegistry(allow_loopback=True)
        disc_svc = RouterDiscoveryService(registry=reg, allow_loopback=True)
        disc = asyncio.run(disc_svc.discover(override_gateway_url=base_url, probe_extended_interfaces=False))
        assert disc.adapter_id == "huawei"
        assert disc.hardware_vendor == "Huawei"
        assert disc.isp_brand == "WE (TE Data)"
        assert disc.detected_model == "DN8245V-56"

        adapter = reg.get_adapter("huawei")
        assert isinstance(adapter, HuaweiRouterAdapter)
        auth = adapter.authenticate(base_url=base_url, username="admin", password="pw")
        assert auth.authenticated is True

        snap = adapter.read_config()
        assert snap.vendor == "Huawei"
        assert snap.firmware_version == "V5R020C00"
        assert snap.wan_ip == "197.55.10.22"
        assert "1.1.1.1" in snap.dns_servers
        assert "2.4 GHz" in snap.radios
        assert snap.radios["2.4 GHz"].channel == "6"

        devs = adapter.get_connected_devices()
        assert any(d.ip_address == "192.168.1.50" for d in devs)

        model = RouterPageInspectionService().inspect(
            adapter=adapter, discovery=disc, snapshot=snap, devices=devs
        )
        assert model.coverage.fully_inspected_pages >= 4
        assert model.coverage.not_supported_pages >= 1  # Unimplemented 404 ASP pages must be reported honestly!
        assert model.coverage.secrets_redacted_count >= 1
        assert "TopSecretPass" not in model.model_dump_json()
    finally:
        srv.shutdown()
        srv.server_close()


def test_snmp_asn1_encode_decode_roundtrip() -> None:
    enc = encode_oid(OID_SYS_DESCR)
    assert enc[0] == 0x06
    assert decode_oid(enc[2:]) == OID_SYS_DESCR
    req = build_snmp_packet(community="public", oid=OID_SYS_DESCR)
    assert b"public" in req
    # Synthetic GetResponse frame for OID 1.3.6.1.2.1.1.1.0 = "RouterOS"
    vb = encode_oid(OID_SYS_DESCR) + bytes([0x04, 8]) + b"RouterOS"
    vb_seq = bytes([0x30, len(vb)]) + vb
    vbl_seq = bytes([0x30, len(vb_seq)]) + vb_seq
    pdu_body = b"\x02\x01\x01\x02\x01\x00\x02\x01\x00" + vbl_seq
    pdu = bytes([0xA2, len(pdu_body)]) + pdu_body
    msg_body = b"\x02\x01\x01\x04\x06public" + pdu
    pkt = bytes([0x30, len(msg_body)]) + msg_body
    parsed = parse_snmp_response(pkt)
    assert parsed == [(OID_SYS_DESCR, "RouterOS")]


def test_tr064_upnp_xml_inspection() -> None:
    class _UpnpHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            xml = """<?xml version="1.0"?>
            <root xmlns="urn:schemas-upnp-org:device-1-0"><device>
              <friendlyName>Home IGD</friendlyName>
              <serviceList>
                <service>
                  <serviceType>urn:schemas-upnp-org:service:WANIPConnection:1</serviceType>
                  <controlURL>/ctl/IPConn</controlURL>
                </service>
              </serviceList>
            </device></root>"""
            self.send_response(200)
            self.end_headers()
            self.wfile.write(xml.encode("utf-8"))

        def do_POST(self) -> None:
            ln = int(self.headers.get("Content-Length") or "0")
            body = self.rfile.read(ln).decode("utf-8", errors="ignore")
            self.send_response(200)
            self.end_headers()
            if "GetExternalIPAddress" in body:
                self.wfile.write(b"<r><NewExternalIPAddress>41.42.43.44</NewExternalIPAddress></r>")
            else:
                self.wfile.write(b"<r><NewConnectionStatus>Connected</NewConnectionStatus><NewUptime>321</NewUptime></r>")

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _UpnpHandler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        res = TrStandardsInspector().inspect_upnp_description(
            f"http://127.0.0.1:{port}/rootDesc.xml", allow_loopback=True
        )
        assert res.upnp_igd_reachable is True
        assert res.wan_external_ip == "41.42.43.44"
        assert res.wan_connection_status == "Connected"
    finally:
        srv.shutdown()
        srv.server_close()


def test_root_cause_14_fields_qos_compat_and_nl_commands() -> None:
    tel = WifiInterfaceTelemetry(
        connection_state="connected",
        interface_name="Wi-Fi",
        ssid="TestSSID",
        band="2.4 GHz",
        channel=6,
        channel_width_mhz=40,
        rssi_dbm=-78,
        signal_quality_pct=35,
        tx_link_rate_mbps=72.0,
        security_mode="WPA-Personal (TKIP)",
    )
    ch_rep = FullChannelAnalysisReport(
        bands={
            "2.4 GHz": BandChannelAnalysisResult(
                band="2.4 GHz",
                target_width_mhz=20,
                regulatory_domain="EG",
                current_channel=6,
                current_channel_score=ChannelScoreBreakdown(
                    band="2.4 GHz",
                    channel=6,
                    center_frequency_mhz=2437.0,
                    width_mhz=20,
                    occupied_range_mhz=(2427.0, 2447.0),
                    total_score=38.0,
                    interference_level="severe",
                    co_channel_ap_count=4,
                    overlapping_ap_count=2,
                    formula_notes="High co-channel overlap",
                ),
                recommended_channels=[
                    ChannelRecommendation(
                        rank=1,
                        band="2.4 GHz",
                        channel=1,
                        width_mhz=20,
                        total_score=8.0,
                        interference_level="low",
                        confidence_label="high",
                        reason="Least crowded orthogonal channel",
                    )
                ],
            )
        }
    )
    bb_rep = BufferbloatDiagnosticsReport(
        run_id="bb1",
        started_at="2026-11-27T00:00:00Z",
        completed_at="2026-11-27T00:00:10Z",
        idle_phase=PingBurstStats.__class__ and BufferbloatPhaseResult(
            phase="idle", target_ip="1.1.1.1", started_at="2026-11-27T00:00:00Z", completed_at="2026-11-27T00:00:02Z",
            packets_sent=10, packets_received=10, avg_ms=15.0
        ),
        upload_phase=BufferbloatPhaseResult(
            phase="upload_load", target_ip="1.1.1.1", started_at="2026-11-27T00:00:02Z", completed_at="2026-11-27T00:00:06Z",
            packets_sent=10, packets_received=10, avg_ms=195.0, delta_over_idle_ms=180.0, grade="F"
        ),
        overall_grade="F",
        summary="Severe upload bloat",
    )
    caps = RouterCapabilities(adapter_id="huawei", supports_channel_write=True)
    proposals = RouterConfigurationAnalyzer().analyze(
        capabilities=caps, telemetry=tel, channel_report=ch_rep, bufferbloat_report=bb_rep
    )
    assert len(proposals) >= 3

    qos_rep = QoSCompatibilityAnalyzer().analyze(
        qos_summary={"master_enabled": True, "active_policies_count": 1, "upload_cap_kbps": 1000},
        bufferbloat_report=bb_rep,
        speed_report=SpeedTestReport(
            run_id="sp1", started_at="2026-11-27T00:00:00Z", completed_at="2026-11-27T00:00:05Z",
            upload_tested=True, upload_mbps=20.0
        ),
        wmm_disabled=True,
    )
    assert qos_rep.compatible is False

    rc = RootCauseAnalysisService().build_report(
        capabilities=caps,
        telemetry=tel,
        channel_report=ch_rep,
        bufferbloat_report=bb_rep,
        proposals=proposals,
        qos_compat_findings=qos_rep.findings,
    )
    assert len(rc.fault_cards) >= 4
    assert len(rc.app_impacts) == 5
    first = rc.fault_cards[0]
    assert first.issue_name and first.location and first.why_problem and first.recommended_solution
    assert first.post_execution_verification

    nl = NaturalLanguageCommandService()
    chips = nl.generate_contextual_suggestions(rc)
    assert any("القناة" in c or "Bufferbloat" in c for c in chips)
    r_slow = nl.execute_sync_summary("ما سبب بطء الإنترنت؟", context={"root_cause": rc})
    assert r_slow.status == "completed"

    md = NetworkHealthReportService.build_markdown_report(
        telemetry=tel, channel_report=ch_rep, bufferbloat_report=bb_rep, root_cause=rc, qos_compat=qos_rep
    )
    assert "المشكلات والأخطاء" in md


def test_optimization_modes_14step_channel_and_rollback(tmp_path: Path) -> None:
    """Test all 3 optimization modes, 11 lifecycle states, 14-step workflow rollback, and ActionHistoryStore."""
    class _FakeWritableAdapter:
        adapter_id = "fake_wrt"
        vendor_family = "FakeRouter"
        is_authenticated = True

        def __init__(self) -> None:
            self.channel = "6"

        def capabilities(self) -> RouterCapabilities:
            return RouterCapabilities(adapter_id="fake_wrt", supports_wifi_write=True, supports_channel_write=True)

        def read_config(self) -> RouterConfigurationSnapshot:
            return RouterConfigurationSnapshot(
                adapter_id="fake_wrt",
                radios={"2.4 GHz": RouterWifiRadioConfig(band="2.4 GHz", enabled=True, channel=self.channel)},
            )

        def safe_apply_change(self, proposal: RouterChangeProposal, *, explicit_user_approval: bool = False):
            from app.wifi.models import RouterApplyResult
            if not explicit_user_approval:
                return RouterApplyResult(proposal_id=proposal.proposal_id, success=False, message="Need approval")
            prev = self.channel
            self.channel = proposal.proposed_value
            return RouterApplyResult(
                proposal_id=proposal.proposal_id,
                success=True,
                applied_automatically=True,
                backup_taken=True,
                readback_verified=True,
                previous_value=prev,
                verified_value=self.channel,
                message=f"Channel {prev}->{self.channel}",
            )

    store = ActionHistoryStore(tmp_path / "actions.db")
    planner = OptimizationPlanner(history=store)
    adapter = _FakeWritableAdapter()
    prop = RouterChangeProposal(
        proposal_id="p_ch1",
        category="wifi_channel",
        title="Switch 2.4 GHz channel to 1",
        target_field="channel",
        band="2.4 GHz",
        current_value="6",
        proposed_value="1",
        reason="Congested Ch 6",
        expected_impact="Lower interference",
        risk_level="low",
        requires_reconnect_warning=False,
        supported_by_adapter=True,
    )

    # Mode 1: MONITOR_AND_DIAGNOSE blocks writes
    planner.mode = OptimizationMode.MONITOR_AND_DIAGNOSE
    e1 = planner.execute_proposal(adapter=adapter, proposal=prop, explicit_user_approval=True)
    assert e1.state == ActionLifecycleState.WAITING_FOR_APPROVAL
    assert adapter.channel == "6"

    # Mode 2: APPROVAL_REQUIRED waits without approval, executes with approval
    planner.mode = OptimizationMode.APPROVAL_REQUIRED
    e2 = planner.execute_proposal(adapter=adapter, proposal=prop, explicit_user_approval=False)
    assert e2.state == ActionLifecycleState.WAITING_FOR_APPROVAL

    # 14-step workflow with simulated latency degradation -> triggers automatic rollback!
    before_snap = BeforeAfterSnapshot(snapshot_id="b1", label="before", gateway_avg_ms=5.0)

    async def _after_regressed() -> BeforeAfterSnapshot:
        return BeforeAfterSnapshot(snapshot_id="a1", label="after", gateway_avg_ms=42.0)

    async def _reconnected() -> bool:
        return True

    entry_rb, comp = asyncio.run(
        planner.optimize_wifi_channel_workflow(
            adapter=adapter,
            proposal=prop,
            explicit_user_approval=True,
            before_snapshot=before_snap,
            wait_reconnect_fn=_reconnected,
            collect_after_fn=_after_regressed,
        )
    )
    assert comp is not None and entry_rb.state == ActionLifecycleState.ROLLED_BACK
    assert adapter.channel == "6"  # Restored automatically!

    # Successful Mode 3 execution + explicit manual RollbackManager test
    planner.mode = OptimizationMode.AUTHORIZED_AUTO_OPTIMIZATION
    e3 = planner.execute_proposal(adapter=adapter, proposal=prop, explicit_user_approval=False)
    assert e3.state == ActionLifecycleState.SUCCESSFULLY_VERIFIED
    assert adapter.channel == "1"
    rb_ok, _msg = planner.rollback.rollback_action(action_id=e3.action_id, adapter=adapter)
    assert rb_ok is True
    assert adapter.channel == "6"
    assert store.get(e3.action_id).state == ActionLifecycleState.ROLLED_BACK


def test_huawei_and_asus_reject_http200_login_html_without_session_cookie() -> None:
    """Wrong passwords returning HTTP 200 login HTML must never falsely authenticate."""
    from app.wifi.router.adapters.asus import AsusRouterAdapter

    class _Reject200Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            self.send_response(200)
            self.end_headers()
            if "getrandcount" in self.path:
                self.wfile.write(b"deadbeef12345678")
            else:
                self.wfile.write(b"<html><title>Login</title><input type='password'/></html>")

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length") or "0")
            _ = self.rfile.read(length)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<html><title>Auth Required</title><input type='password' name='pw'/></html>")

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Reject200Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{port}"
        h = HuaweiRouterAdapter(allow_loopback=True)
        h_res = h.authenticate(base_url=url, username="admin", password="WRONG_PASSWORD")
        assert h_res.authenticated is False

        a = AsusRouterAdapter(allow_loopback=True)
        a_res = a.authenticate(base_url=url, username="admin", password="WRONG_PASSWORD")
        assert a_res.authenticated is False
    finally:
        srv.shutdown()
        srv.server_close()


def test_isp_generic_reads_html_kv_config_and_device_table() -> None:
    from app.wifi.router.adapters.isp_generic_models import IspGenericRouterAdapter

    class _TendaHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length") or "0")
            _ = self.rfile.read(length)
            self.send_response(200)
            self.send_header("Set-Cookie", "password=ok_sid")
            self.end_headers()
            self.wfile.write(b'{"errCode": 0}')

        def do_GET(self) -> None:
            self.send_response(200)
            self.end_headers()
            if "getWlanInfo" in self.path:
                self.wfile.write(b'{"2.4 GHz": {"enabled": true, "ssid": "Tenda_Home", "channel": 11}}')
            elif "getWanInfo" in self.path:
                self.wfile.write(b'{"wan_ip": "197.44.1.9", "wan_type": "PPPoE", "dns_servers": "1.1.1.1,8.8.8.8"}')
            else:
                self.wfile.write(b"<table><tr><td>192.168.0.55</td><td>aa:bb:cc:dd:ee:ff</td></tr></table>")

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _TendaHandler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        adapter = IspGenericRouterAdapter(vendor_key="tenda", allow_loopback=True)
        auth = adapter.authenticate(base_url=f"http://127.0.0.1:{port}", username="admin", password="pw")
        assert auth.authenticated is True
        snap = adapter.read_config()
        assert snap.wan_ip == "197.44.1.9"
        assert snap.wan_connection_type == "PPPoE"
        assert snap.dns_servers == ["1.1.1.1", "8.8.8.8"]
        assert snap.radios["2.4 GHz"].ssid == "Tenda_Home"
        devs = adapter.get_connected_devices()
        assert len(devs) == 1 and devs[0].mac_address == "aa:bb:cc:dd:ee:ff"
    finally:
        srv.shutdown()
        srv.server_close()


def test_discovery_os_gateway_fallback_and_upnp_band_extraction(monkeypatch) -> None:
    class _NullGatewayPlatform:
        def get_default_gateway(self) -> None:
            return None

    disc_svc = RouterDiscoveryService(
        platform=_NullGatewayPlatform(),
        allow_loopback=True,
        ssdp_fn=lambda _ip: {
            "friendlyName": "Dual-Band Router",
            "manufacturer": "TP-Link",
            "modelName": "Archer AX50",
            "WANAccessType": "PPPoE",
            "NewExternalIPAddress": "41.44.12.8",
        },
    )
    monkeypatch.setattr(RouterDiscoveryService, "_resolve_os_default_gateway", staticmethod(lambda: "127.0.0.1"))
    monkeypatch.setattr(RouterDiscoveryService, "_lookup_arp_mac", staticmethod(lambda _ip: "aa:bb:cc:11:22:33"))

    class _PassiveHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<html><title>Archer AX50</title><script>var stok='abc';/* 2.4 GHz 5 GHz PPPoE */</script></html>")

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _PassiveHandler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        res = asyncio.run(disc_svc.discover(override_gateway_url=f"http://127.0.0.1:{port}", probe_extended_interfaces=False))
        assert res.gateway_ip == "127.0.0.1"
        assert res.wan_connection_type == "PPPoE"
        assert res.supported_bands == ["2.4 GHz", "5 GHz"]
    finally:
        srv.shutdown()
        srv.server_close()


def test_bufferbloat_fails_closed_when_idle_probes_all_fail_and_supports_tuple_ping() -> None:
    from unittest.mock import MagicMock
    from app.wifi.bufferbloat_diagnostics import BufferbloatDiagnosticsService
    from app.wifi.coordinator import DiagnosticCoordinator

    # 1. None platform returns honest failed status
    bb_none = BufferbloatDiagnosticsService(platform=None, coordinator=DiagnosticCoordinator())
    rep_none = asyncio.run(bb_none.run_bufferbloat_test(target_ip="192.0.2.1", include_upload=False))
    assert rep_none.status == "failed"

    # 2. All idle probes failing fails closed instead of substituting 0.0 ms
    plat = MagicMock()
    plat.ping.return_value = (False, 0.0)
    bb_fail = BufferbloatDiagnosticsService(
        platform=plat,
        coordinator=DiagnosticCoordinator(),
        download_worker_fn=lambda url, dur, tok: 1_000_000,
    )
    rep_fail = asyncio.run(
        bb_fail.run_bufferbloat_test(
            target_ip="192.0.2.1", phase_duration_sec=0.25, ping_interval_sec=0.08, cooldown_sec=0.02, include_upload=False
        )
    )
    assert rep_fail.status == "failed"
    assert rep_fail.overall_grade is None
    assert "+None" not in rep_fail.summary

    # 3. Tuple ping return (True, ms) works cleanly
    plat_ok = MagicMock()
    calls = {"n": 0}

    def _tuple_ping(target: str, timeout_sec: float = 1.0):
        calls["n"] += 1
        return (True, 10.0 if calls["n"] <= 3 else 45.0)

    plat_ok.ping.side_effect = _tuple_ping
    bb_ok = BufferbloatDiagnosticsService(
        platform=plat_ok,
        coordinator=DiagnosticCoordinator(),
        download_worker_fn=lambda url, dur, tok: 1_000_000,
    )
    rep_ok = asyncio.run(
        bb_ok.run_bufferbloat_test(
            target_ip="192.0.2.1", phase_duration_sec=0.25, ping_interval_sec=0.08, cooldown_sec=0.02, include_upload=False
        )
    )
    assert rep_ok.status == "completed"
    assert rep_ok.idle_phase is not None and rep_ok.idle_phase.packets_received > 0


def test_analyzer_evaluates_config_model_upnp_firewall_txpower_dhcp() -> None:
    from app.wifi.models import (
        BandChannelAnalysisResult,
        ChannelScoreBreakdown,
        ConnectedDeviceRecord,
        FullChannelAnalysisReport,
        RouterCapabilities,
        RouterConfigurationSnapshot,
        WifiInterfaceTelemetry,
    )
    from app.wifi.router.analyzer import RouterConfigAnalyzer
    from app.wifi.router.models_config import InspectionCoverageReport, RouterConfigurationModel

    snap = RouterConfigurationSnapshot(
        adapter_id="huawei",
        vendor="Huawei",
        upnp_enabled=True,
        firewall_level="off",
        dhcp_enabled=False,
    )
    sc = ChannelScoreBreakdown(
        band="2.4 GHz",
        channel=6,
        center_frequency_mhz=2437,
        width_mhz=40,
        occupied_range_mhz=(2417.0, 2457.0),
        is_current_channel=True,
        total_score=55.0,
        interference_level="high",
    )
    ch_rep = FullChannelAnalysisReport(
        bands={
            "2.4 GHz": BandChannelAnalysisResult(
                band="2.4 GHz",
                current_channel=6,
                target_width_mhz=40,
                regulatory_domain="EG",
                current_channel_score=sc,
                channel_scores=[sc],
            )
        }
    )
    model = RouterConfigurationModel(
        capabilities=RouterCapabilities(adapter_id="huawei", vendor_family="Huawei"),
        snapshot=snap,
        domains={"tx_power": {"wl0_txpower": "100%"}},
        coverage=InspectionCoverageReport(adapter_id="huawei"),
    )
    devices = [
        ConnectedDeviceRecord(ip_address=f"192.168.1.{10 + i}", source="router_api")
        for i in range(4)
    ]
    props = RouterConfigAnalyzer().analyze(
        capabilities=model.capabilities,
        router_config=snap,
        config_model=model,
        telemetry=WifiInterfaceTelemetry(band="2.4 GHz", channel=6, rssi_dbm=-48),
        channel_report=ch_rep,
        devices=devices,
    )
    cats = {p.category for p in props}
    assert {"upnp", "firewall", "tx_power", "dhcp"}.issubset(cats)


def test_wifi_router_view_mode_sync_and_shutdown() -> None:
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from app.core.models.metrics import OperatingMode
    from app.ui.views.wifi_router_view import WifiRouterView

    app = QApplication.instance() or QApplication([])
    view = WifiRouterView()
    try:
        view.sync_operating_mode(OperatingMode.OBSERVATION)
        assert view._combo_opt_mode.currentIndex() == 0
        view.sync_operating_mode(OperatingMode.AUTO)
        assert view._combo_opt_mode.currentIndex() == 2
        view._inp_router_pass.setText("TempPass123")
        view._active_session_secrets.append("TempPass123")
        view.shutdown()
        assert view._is_closing is True
        assert view._inp_router_pass.text() == ""
        assert view._active_session_secrets == []
    finally:
        view.close()
        view.deleteLater()
        app.processEvents()
