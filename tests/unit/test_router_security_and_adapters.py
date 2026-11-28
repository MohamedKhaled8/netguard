"""Unit tests for router security, origin checks, mock adapters, device limits, and reporting."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

import pytest

from app.wifi.device_management import DeviceManagementService
from app.wifi.models import (
    BeforeAfterSnapshot,
    BufferbloatDiagnosticsReport,
    BufferbloatPhaseResult,
    DnsDiagnosticsReport,
    DnsTargetMetrics,
    FaultCategory,
    FullChannelAnalysisReport,
    NetworkConditionReport,
    NetworkDiagnosticsReport,
    PingBurstStats,
    RouterCapabilities,
    RouterChangeProposal,
    RouterDiscoveryResult,
    WifiInterfaceTelemetry,
)
from app.wifi.recommendations import UnifiedDiagnosticAnalyzer
from app.wifi.reporting import BeforeAfterReportingService
from app.wifi.router.adapters.generic_probe import GenericProbeAdapter
from app.wifi.router.adapters.huawei import HuaweiRouterAdapter
from app.wifi.router.adapters.tplink import TpLinkRouterAdapter
from app.wifi.router.adapters.zte import ZteRouterAdapter
from app.wifi.router.auth import RouterAuthCoordinator
from app.wifi.router.credentials import (
    LocalOriginSecurityError,
    SessionCredentialStore,
    evaluate_transport_security_warning,
    redact_secrets,
    validate_local_router_url,
)


class _StatefulRouterMockState:
    def __init__(self, *, reject_readback: bool = False) -> None:
        self.channel_5g = "36"
        self.width_5g = "80 MHz"
        self.reject_readback = reject_readback


def _start_mock_server(state: _StatefulRouterMockState):
    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send_json(self, code: int, obj: Dict[str, Any], headers: Dict[str, str] | None = None) -> None:
            body = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            if headers:
                for k, v in headers.items():
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _send_xml(self, code: int, xml_s: str) -> None:
            body = xml_s.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/xml")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/?_type=loginData&_tag=login_entry":
                self._send_json(200, {"sess_token": "tok123"})
            elif self.path == "/?_type=menuData&_tag=wlan_basic_ad":
                self._send_json(
                    200,
                    {
                        "radio_24": {"enabled": True, "ssid": "ZTE_24", "channel": "6", "channel_width": "20 MHz"},
                        "radio_5": {"enabled": True, "ssid": "ZTE_5G", "channel": state.channel_5g, "channel_width": state.width_5g},
                    },
                )
            elif self.path == "/?_type=menuData&_tag=status_info":
                self._send_json(200, {"model": "ZXHN H188A", "wan_status": "Connected", "dns_servers": ["192.168.1.1"]})
            elif self.path == "/?_type=menuData&_tag=lan_assoc_devs":
                self._send_json(200, {"devices": [{"ip": "192.168.1.25", "mac": "aa:bb:cc:11:22:33", "hostname": "Phone", "connection_type": "wifi_5"}]})
            elif self.path == "/api/webserver/SesTokInfo":
                self._send_xml(200, "<response><SesInfo>SessionID=h1</SesInfo><TokInfo>csrf_abc</TokInfo></response>")
            elif self.path == "/api/wlan/basic-settings":
                self._send_json(200, {"model": "HG631", "5 GHz": {"enabled": True, "channel": state.channel_5g, "channel_width": "80 MHz"}})
            elif self.path == "/api/wlan/host-list":
                self._send_json(200, {"hosts": [{"ip": "192.168.1.30", "mac": "aa:bb:cc:11:22:44", "hostname": "TV"}]})
            elif "/admin/wireless?form=wireless_summary" in self.path:
                self._send_json(200, {"model": "Archer AX50", "5 GHz": {"enabled": True, "channel": state.channel_5g, "channel_width": "80 MHz"}})
            elif "/admin/dhcps?form=client" in self.path:
                self._send_json(200, {"clients": [{"ip": "192.168.1.40", "mac": "aa:bb:cc:11:22:55", "hostname": "Laptop", "rx_limit_kbps": 10000}]})
            else:
                self._send_json(404, {"err": "not found"})

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            if self.path == "/?_type=loginData&_tag=login_entry":
                if "admin_ok" in raw or "Username=admin" in raw and "Password=" in raw:
                    if "badpw" in raw:
                        self._send_json(200, {"loginErrMsg": "Invalid password"})
                    else:
                        self._send_json(200, {"login_need_refresh": True}, {"Set-Cookie": "SID=zte1"})
            elif self.path == "/?_type=menuData&_tag=wlan_basic_apply":
                data = json.loads(raw)
                if not state.reject_readback and data.get("field") == "channel":
                    state.channel_5g = str(data["value"])
                self._send_json(200, {"result": "ok"})
            elif self.path == "/api/user/login":
                self._send_xml(200, "<response>OK</response>")
            elif "/login?form=login" in self.path:
                self._send_json(200, {"success": True, "data": {"stok": "tp_tok_9"}})
            elif "/admin/wireless?form=write" in self.path:
                self._send_json(200, {"success": True})
            else:
                self._send_json(404, {"result": "fail"})

    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    return srv


def test_local_origin_security_and_secret_redaction() -> None:
    # Public targets & unsafe schemes rejected
    with pytest.raises(LocalOriginSecurityError):
        validate_local_router_url("https://8.8.8.8")
    with pytest.raises(LocalOriginSecurityError):
        validate_local_router_url("ftp://192.168.1.1")
    with pytest.raises(LocalOriginSecurityError):
        validate_local_router_url("http://127.0.0.1", allow_loopback=False)

    # RFC1918 allowed & HTTP warning generated
    scheme, host, port, is_https = validate_local_router_url("http://192.168.1.1")
    assert scheme == "http" and host == "192.168.1.1" and port == 80 and not is_https
    assert "unencrypted HTTP" in (evaluate_transport_security_warning("http://192.168.1.1") or "")

    # Secret redaction scrubs nested keys and raw secret strings
    raw = {"password": "SuperSecretPassword!", "nested": {"session_token": "abc", "note": "used SuperSecretPassword! in url http://admin:SuperSecretPassword!@192.168.1.1"}}
    clean = redact_secrets(raw, extra_secrets=["SuperSecretPassword!"])
    serialized = json.dumps(clean)
    assert "SuperSecretPassword!" not in serialized
    assert clean["nested"]["session_token"] == "[REDACTED]"


def test_adapters_auth_readback_verify_and_rollback() -> None:
    state = _StatefulRouterMockState(reject_readback=False)
    srv = _start_mock_server(state)
    base_url = f"http://127.0.0.1:{srv.server_port}"
    try:
        zte = ZteRouterAdapter(allow_loopback=True)
        auth = zte.authenticate(base_url=base_url, username="admin", password="validpw")
        assert auth.authenticated is True
        cfg = zte.read_config()
        assert cfg.model == "ZXHN H188A"
        assert cfg.hardware_verified is False

        # Safe channel write + readback verify succeeds
        prop = RouterChangeProposal(
            proposal_id="p1",
            category="wifi_channel",
            title="Switch 5G",
            target_field="channel",
            band="5 GHz",
            current_value="36",
            proposed_value="44",
            reason="Less congestion",
            expected_impact="Better SNR",
            supported_by_adapter=True,
            requires_manual_apply=False,
        )
        res_ok = zte.safe_apply_change(prop, explicit_user_approval=True)
        assert res_ok.success is True
        assert res_ok.backup_taken is True
        assert res_ok.readback_verified is True
        assert res_ok.verified_value == "44"

        # Now simulate router ignoring write -> automatic rollback!
        state.reject_readback = True
        prop2 = prop.model_copy(update={"current_value": "44", "proposed_value": "149"})
        res_rb = zte.safe_apply_change(prop2, explicit_user_approval=True)
        assert res_rb.success is False
        assert res_rb.readback_verified is False
        assert res_rb.rolled_back is True

        # Huawei & TP-Link adapters authenticate & read connected devices
        hw = HuaweiRouterAdapter(allow_loopback=True)
        assert hw.authenticate(base_url=base_url, username="admin", password="pw").authenticated
        assert len(hw.get_connected_devices()) == 1

        tp = TpLinkRouterAdapter(allow_loopback=True)
        assert tp.authenticate(base_url=base_url, username="admin", password="pw").authenticated
        assert tp.capabilities().supports_per_device_bandwidth is True
        assert len(tp.get_connected_devices()) == 1

        # Generic probe refuses writes cleanly
        gen = GenericProbeAdapter(allow_loopback=True)
        assert gen.safe_apply_change(prop, explicit_user_approval=True).success is False
    finally:
        srv.shutdown()


def test_auth_guard_single_attempt_and_lockout_protection() -> None:
    disc = RouterDiscoveryResult(
        gateway_ip="192.168.1.1",
        preferred_url="http://127.0.0.1:8080",
        capabilities=RouterCapabilities(adapter_id="zte"),
    )

    class _RejectAdapter:
        adapter_id = "zte"

        def authenticate(self, **_kw):
            from app.wifi.models import RouterAuthResult

            return RouterAuthResult(authenticated=False, adapter_id="zte", base_url="", message="badpw failed")

    guard = RouterAuthCoordinator(session_store=SessionCredentialStore(), allow_loopback=True)
    # Without ack of HTTP notice, blocks cleanly before trying password
    r0 = guard.authenticate_single_attempt(
        adapter=_RejectAdapter(),
        discovery=disc,
        base_url="http://127.0.0.1:8080",
        username="admin",
        password="pw",
        user_acknowledged_security_warning=False,
    )
    assert not r0.authenticated and "security notice" in r0.message.lower()

    # 3 failed attempts -> 4th attempt is blocked to prevent router admin lockout
    for _ in range(3):
        guard.authenticate_single_attempt(
            adapter=_RejectAdapter(),
            discovery=disc,
            base_url="http://127.0.0.1:8080",
            username="admin",
            password="bad",
            user_acknowledged_security_warning=True,
        )
    r4 = guard.authenticate_single_attempt(
        adapter=_RejectAdapter(),
        discovery=disc,
        base_url="http://127.0.0.1:8080",
        username="admin",
        password="bad",
        user_acknowledged_security_warning=True,
    )
    assert not r4.authenticated and "lockout" in (r4.lockout_risk_warning or "").lower()


def test_device_management_limitation_and_unified_before_after_exports(tmp_path: Path) -> None:
    from datetime import datetime, timezone

    # Unified analyzer across weak signal, wrong band, bufferbloat, slow DNS, bg upload, ISP issue
    tel = WifiInterfaceTelemetry(rssi_dbm=-78, band="2.4 GHz", channel=1)
    now = datetime.now(timezone.utc)
    net_rep = NetworkDiagnosticsReport(
        run_id="r1",
        started_at=now,
        completed_at=now,
        conditions=NetworkConditionReport(large_transfer_suspected=True, active_interface="Wi-Fi", active_interface_tx_mbps=3.5),
        gateway_ping=PingBurstStats(target="192.168.1.1", status="ok", packets_sent=30, packets_received=30, avg_ms=2.5, packet_loss_pct=0.0),
        internet_ping=PingBurstStats(target="1.1.1.1", status="ok", packets_sent=30, packets_received=27, avg_ms=95.0, packet_loss_pct=10.0),
        ipv6_ping=PingBurstStats(target="2606:4700:4700::1111", status="not_configured"),
    )
    dns_rep = DnsDiagnosticsReport(
        recommended_dns="1.1.1.1",
        targets=[DnsTargetMetrics(role="configured", server_ip="192.168.1.1", server_label="Router DNS", status="ok", sample_count=5, median_ms=110.0)],
    )
    bb_rep = BufferbloatDiagnosticsReport(
        run_id="b1",
        started_at=now,
        completed_at=now,
        overall_grade="D",
        download_phase=BufferbloatPhaseResult(phase="download_load", target_ip="1.1.1.1", started_at=now, completed_at=now, packets_sent=20, packets_received=20, delta_over_idle_ms=180.0, grade="D"),
    )
    unified = UnifiedDiagnosticAnalyzer().analyze(
        telemetry=tel,
        network_report=net_rep,
        dns_report=dns_rep,
        bufferbloat_report=bb_rep,
        channel_report=FullChannelAnalysisReport(),
    )
    cats = {f.category for f in unified.findings}
    assert FaultCategory.WIFI_SIGNAL_DISTANCE in cats
    assert FaultCategory.ROUTER_BUFFERBLOAT in cats
    assert FaultCategory.SLOW_DNS in cats
    assert FaultCategory.LOCAL_BACKGROUND_UPLOAD in cats
    assert FaultCategory.ISP_UPSTREAM_ISSUE in cats

    # Before/After comparison handles drift & noise cleanly + redacts exported files
    rep_svc = BeforeAfterReportingService()
    b_snap = BeforeAfterSnapshot(snapshot_id="s1", label="Before", ssid="NetA", qos_active=True, gateway_avg_ms=18.0, download_bloat_delta_ms=150.0)
    a_snap_noisy = BeforeAfterSnapshot(snapshot_id="s2", label="AfterNoisy", ssid="NetA", qos_active=True, gateway_avg_ms=17.2, download_bloat_delta_ms=148.0)
    comp_noise = rep_svc.compare(b_snap, a_snap_noisy)
    assert comp_noise.overall_verdict == "inconclusive"

    a_snap_good = BeforeAfterSnapshot(snapshot_id="s3", label="AfterFixed", ssid="NetA", qos_active=True, gateway_avg_ms=4.0, download_bloat_delta_ms=18.0)
    comp_good = rep_svc.compare(b_snap, a_snap_good)
    assert comp_good.overall_verdict == "improved"

    json_p = rep_svc.export_json(tmp_path / "r.json", unified_report=unified, comparison=comp_good, extra_sections={"password": "TopSecretValue99"}, extra_secrets=["TopSecretValue99"])
    html_p = rep_svc.export_html(tmp_path / "r.html", unified_report=unified, comparison=comp_good, extra_secrets=["TopSecretValue99"])
    assert "TopSecretValue99" not in json_p.read_text(encoding="utf-8")
    assert "TopSecretValue99" not in html_p.read_text(encoding="utf-8")
