"""Unit tests for sequential network diag, DNS benchmark, speed, bufferbloat, and coordinator."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, List
from unittest.mock import MagicMock

import pytest

from app.wifi.bufferbloat_diagnostics import BufferbloatDiagnosticsService
from app.wifi.coordinator import (
    ApprovalRequiredError,
    DiagnosticBusyError,
    DiagnosticCoordinator,
    MeetingSafetyFreezeError,
)
from app.wifi.dns_diagnostics import DnsDiagnosticsService
from app.wifi.network_diagnostics import NetworkDiagnosticsService
from app.wifi.speed_test import SpeedTestService


@dataclass
class _PingRes:
    success: bool
    latency_ms: float | None


def _make_fake_platform(*, gateway: str = "192.168.1.1", gw_ms: float = 2.0, inet_ms: float = 28.0) -> Any:
    plat = MagicMock()
    plat.get_primary_interface.return_value = MagicMock(name="Wi-Fi", interface_type="wifi")
    plat.get_primary_interface.return_value.name = "Wi-Fi"
    plat.get_default_gateway.return_value = gateway
    plat.get_interface_dns_servers.return_value = ["192.168.1.1", "8.8.4.4"]

    def _ping(target: str, timeout_sec: float = 1.0):
        if target == gateway:
            return _PingRes(True, gw_ms)
        return _PingRes(True, inet_ms)

    plat.ping.side_effect = _ping
    plat.get_qos_policies.return_value = []
    return plat


def _make_fake_traffic_ctrl(*, in_meeting: bool = False, master_qos: bool = True) -> Any:
    tc = MagicMock()
    tc.is_critical_meeting_active.return_value = in_meeting
    tc.hysteresis_tracker = MagicMock()
    tc.hysteresis_tracker.state = MagicMock()
    tc.hysteresis_tracker.state.name = "ACTIVE" if in_meeting else "IDLE"
    tc.qos_config = MagicMock(master_enabled=master_qos)
    tc._active_qos_specs = {"Zoom": object()} if master_qos else {}

    def _disable():
        tc._active_qos_specs.clear()
        tc.qos_config.master_enabled = False

    def _reconcile():
        tc._active_qos_specs["Zoom"] = object()
        tc.qos_config.master_enabled = True

    tc.kill_switch_disable.side_effect = _disable
    tc.reconcile_active_policies.side_effect = _reconcile
    return tc


@pytest.mark.asyncio
async def test_coordinator_single_flight_and_meeting_safety() -> None:
    tc = _make_fake_traffic_ctrl(in_meeting=True, master_qos=True)
    plat = _make_fake_platform()
    coord = DiagnosticCoordinator(traffic_controller=tc, platform=plat)

    # Intrusive actions MUST fail when meeting is active
    allowed, reason = coord.check_operation_allowed("speed_test")
    assert not allowed and "meeting" in (reason or "").lower()

    allowed_dns_flush, _ = coord.check_operation_allowed("dns_flush")
    assert not allowed_dns_flush

    # Passive reads MUST still work during meetings
    allowed_passive, _ = coord.check_operation_allowed("network_sequence")
    assert allowed_passive

    # Switching meeting off allows exclusive slot + blocks concurrent collision
    tc.is_critical_meeting_active.return_value = False
    tc.hysteresis_tracker.state.name = "IDLE"

    async with coord.async_exclusive("speed_test", "running"):
        with pytest.raises(DiagnosticBusyError):
            async with coord.async_exclusive("bufferbloat_test", "collision"):
                pass

    # Optional idle QoS suspension guard: requires explicit approval and guarantees restore
    with pytest.raises(ApprovalRequiredError):
        await coord.run_with_optional_idle_qos_suspension(
            explicit_user_approval=False, callback=lambda: 12.0
        )

    res, audit = await coord.run_with_optional_idle_qos_suspension(
        explicit_user_approval=True,
        callback=lambda: 15.0,
    )
    assert res == 15.0
    assert audit.suspension_verified is True
    assert audit.post_restore_verified is True
    assert tc.qos_config.master_enabled is True
    assert len(tc._active_qos_specs) == 1


@pytest.mark.asyncio
async def test_sequential_network_diagnostics_ipv6_not_configured_and_silent_hop() -> None:
    plat = _make_fake_platform(gw_ms=3.0, inet_ms=32.0)

    class _FakeTraceEngine:
        async def run_trace(self, target_ip: str, max_hops: int = 5, **_kw):
            hops = [
                MagicMock(hop_number=1, ip_address="192.168.1.1", hostname=None, rtts_ms=[2.1, 2.3], avg_rtt_ms=2.2, loss_pct=0.0),
                MagicMock(hop_number=2, ip_address="*", hostname=None, rtts_ms=[], avg_rtt_ms=None, loss_pct=100.0),
                MagicMock(hop_number=3, ip_address="1.1.1.1", hostname=None, rtts_ms=[31.0, 32.0], avg_rtt_ms=31.5, loss_pct=0.0),
            ]
            return MagicMock(hops=hops)

    svc = NetworkDiagnosticsService(
        platform=plat,
        coordinator=DiagnosticCoordinator(platform=plat),
        traceroute_engine=_FakeTraceEngine(),  # type: ignore[arg-type]
        ipv6_usable_fn=lambda _iface: (False, "No global IPv6 address"),
    )
    report = await svc.run_sequence(packet_count=30, interval_sec=0.0, sample_traffic_sec=0.0)

    assert report.sequence_order == [
        "E_conditions_baseline",
        "A_gateway_icmp_30",
        "B_internet_icmp_30",
        "C_ipv6_check",
        "D_traceroute_5_hop",
    ]
    assert report.gateway_ping.packets_sent == 30
    assert report.internet_ping.packets_sent == 30
    assert report.gateway_ping.completed_at <= report.internet_ping.started_at
    # IPv6 absent must NOT report failure
    assert report.ipv6_ping.status == "not_configured"
    assert report.ipv6_ping.packet_loss_pct == 0.0
    # Hop 2 silent must carry explicit non-loss nuance
    assert report.traceroute is not None
    assert not report.traceroute.hops[1].responded
    assert "not standalone proof of loss" in report.traceroute.hops[1].interpretation.lower()


@pytest.mark.asyncio
async def test_dns_diagnostics_cache_busting_noise_and_no_auto_modify() -> None:
    plat = _make_fake_platform()
    tc = _make_fake_traffic_ctrl(in_meeting=True)
    coord = DiagnosticCoordinator(traffic_controller=tc, platform=plat)

    queries_seen: List[str] = []

    def _probe(server_ip: str, qname: str, timeout: float):
        queries_seen.append(qname)
        lat_map = {"192.168.1.1": 85.0, "1.1.1.1": 18.0, "8.8.8.8": 26.0}
        return True, lat_map.get(server_ip, 30.0), "NXDOMAIN"

    dns_svc = DnsDiagnosticsService(platform=plat, coordinator=coord, probe_fn=_probe)
    rep = await dns_svc.run_diagnostics(samples_per_server=5)

    assert rep.auto_modified_dns is False
    assert rep.meeting_safety_frozen is True
    # Unique qnames across rounds prevent OS cache skew
    assert len(set(queries_seen)) == 5
    cf = next(t for t in rep.targets if t.role == "cloudflare")
    assert cf.sample_count == 5
    assert cf.median_ms == 18.0
    assert rep.recommended_dns == "1.1.1.1"


@pytest.mark.asyncio
async def test_speed_and_bufferbloat_separation_and_qos_isolation() -> None:
    plat = _make_fake_platform(inet_ms=20.0)
    tc = _make_fake_traffic_ctrl(in_meeting=False, master_qos=True)
    coord = DiagnosticCoordinator(traffic_controller=tc, platform=plat)

    tel_mock = MagicMock()
    tel_mock.collect_telemetry = MagicMock(
        return_value=asyncio.Future()
    )
    tel_mock.collect_telemetry.return_value.set_result(
        MagicMock(
            tx_link_rate_mbps=86.7,
            rx_link_rate_mbps=86.7,
            interface_name="Wi-Fi",
            ssid="HomeNet",
            bssid="aa:bb:cc:dd:ee:ff",
            band="5 GHz",
        )
    )

    speed_svc = SpeedTestService(
        coordinator=coord,
        wifi_telemetry=tel_mock,
        download_worker_fn=lambda url, dur, tok: 5_000_000,
        upload_worker_fn=lambda url, sz, dur, tok: 1_250_000,
    )
    sp = await speed_svc.run_speed_test(run_upload=True, streams=2, max_download_sec=0.1, max_upload_sec=0.1)
    assert sp.status == "completed"
    assert sp.wifi_tx_link_rate_mbps == 86.7
    assert sp.local_lan_throughput_mbps is None
    assert sp.download_mbps is not None and sp.download_mbps > 0
    assert sp.upload_mbps is not None and sp.upload_mbps > 0
    assert sp.qos_active_during_test is True

    # Simulate bufferbloat: idle ~20ms, upload spike ~160ms
    ping_phase = {"mode": "idle"}

    def _bloat_ping(target: str, timeout_sec: float = 0.8):
        val = 20.0 if ping_phase["mode"] == "idle" else 160.0
        return _PingRes(True, val)

    plat.ping.side_effect = _bloat_ping

    def _ul_bump(url: str, sz: int, dur: float, tok: Any) -> int:
        ping_phase["mode"] = "upload"
        return 1_000_000

    bb_svc = BufferbloatDiagnosticsService(
        platform=plat,
        coordinator=coord,
        download_worker_fn=lambda url, dur, tok: 2_000_000,
        upload_worker_fn=_ul_bump,
    )
    bb = await bb_svc.run_bufferbloat_test(
        phase_duration_sec=0.25, ping_interval_sec=0.05, cooldown_sec=0.05, include_upload=True
    )
    assert bb.status == "completed"
    assert bb.upload_phase is not None
    assert bb.upload_phase.delta_over_idle_ms is not None and bb.upload_phase.delta_over_idle_ms >= 100.0
    assert bb.upload_bloat_grade in ("C", "D", "F")
