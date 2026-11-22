"""Comprehensive unit & policy tests for DNS Truth (Stage B: B1-B8)."""

import pytest
import os
import json
from unittest.mock import MagicMock, AsyncMock, patch

from app.dns.state import DnsStateManager, DnsStateData
from app.dns.detector import load_providers_catalogue, identify_provider, check_transparent_proxy
from app.dns.benchmark import DNSBenchmark, ResolverScore
from app.dns.optimizer import DNSOptimizer
from app.core.events.bus import EventBus


def test_b1_single_source_of_truth():
    mgr = DnsStateManager.get_instance()
    assert mgr is not None
    mgr._data = DnsStateData()  # Reset for test isolation

    updates = []
    mgr.state_changed.connect(lambda s: updates.append(s))

    mgr.update(active_servers=["1.1.1.1", "1.0.0.1"], detected_provider="Cloudflare", is_healthy=True)
    assert len(updates) >= 1
    current = mgr.current
    assert current.active_servers == ["1.1.1.1", "1.0.0.1"]
    assert current.detected_provider == "Cloudflare"
    assert current.is_healthy is True


def test_b2_provider_identification():
    cat = load_providers_catalogue()
    assert "global_anycast" in cat
    assert "egypt_isps" in cat

    assert identify_provider("1.1.1.1", cat) == "Cloudflare"
    assert identify_provider("8.8.8.8", cat) == "Google Public DNS"
    assert identify_provider("163.121.128.134", cat) == "Telecom Egypt (WE)"
    assert identify_provider("192.168.1.1", cat) == "الراوتر المنزلي (Gateway DNS)"
    assert identify_provider("10.0.0.1", cat) == "الراوتر المنزلي (Gateway DNS)"


def test_b3_catalogue_structure():
    cat = load_providers_catalogue()
    for group in ["global_anycast", "egypt_isps"]:
        for p in cat.get(group, []):
            assert "name" in p
            assert "primary_ip" in p
            assert "secondary_ip" in p


@pytest.mark.asyncio
async def test_b4_benchmark_sorting_and_gating():
    bench = DNSBenchmark(rounds=5)
    assert bench.rounds == 5

    # Explicit metrics on ResolverScore
    scores = [
        ResolverScore(ip="8.8.8.8", name="Google", median_latency_ms=35.0, mean_latency_ms=35.0, success_rate=1.0, failure_rate=0.0, composite_score=75.0),
        ResolverScore(ip="1.1.1.1", name="Cloudflare", median_latency_ms=22.0, mean_latency_ms=22.0, success_rate=1.0, failure_rate=0.0, composite_score=90.0),
        ResolverScore(ip="9.9.9.9", name="Flaky", median_latency_ms=15.0, mean_latency_ms=15.0, success_rate=0.60, failure_rate=0.40, composite_score=30.0),
    ]

    with patch.object(bench, "benchmark_resolver", side_effect=scores):
        with patch("asyncio.gather", new=AsyncMock(return_value=scores)):
            ranked = await bench.rank_all()
            assert ranked[0].name == "Cloudflare"
            assert ranked[1].name == "Google"
            assert ranked[2].name == "Flaky"
            assert os.path.exists("docs/dns_benchmark.md")


@pytest.mark.asyncio
async def test_b7_safe_auto_switch_policy():
    platform = MagicMock()
    platform.get_primary_interface.return_value = "Wi-Fi"
    platform.is_elevated.return_value = True
    dns_state = {"servers": ["192.168.1.1"]}
    platform.get_interface_dns_servers.side_effect = lambda name: list(dns_state["servers"])

    def _set_dns(name, servers):
        dns_state["servers"] = list(servers)
        return True, "OK"

    platform.set_interface_dns_servers.side_effect = _set_dns

    event_bus = EventBus()
    session_tracker = MagicMock()
    session_tracker.has_active_meeting.return_value = False

    optimizer = DNSOptimizer(
        platform_adapter=platform,
        event_bus=event_bus,
        cooldown_sec=900.0,
        session_tracker=session_tracker,
    )

    # 1. Test meeting protection
    session_tracker.has_active_meeting.return_value = True
    res = await optimizer.auto_optimize_dns()
    assert res is None  # Blocked by meeting protection

    session_tracker.has_active_meeting.return_value = False

    # 2. Test hysteresis check (< 15 ms improvement should not switch)
    candidate = ResolverScore(ip="1.1.1.1", name="Cloudflare", median_latency_ms=25.0, mean_latency_ms=25.0, success_rate=1.0, failure_rate=0.0, composite_score=85.0)
    with patch.object(optimizer, "evaluate_and_rank", new=AsyncMock(return_value=[candidate])):
        with patch("app.dns.detector.measure_dns_latency", return_value=25.4):  # Difference is 0.4 ms (< 1 ms)
            res = await optimizer.auto_optimize_dns()
            assert res is None  # Skipped due to hysteresis

    # 3. Test candidate with packet loss rejected
    lossy_candidate = ResolverScore(ip="1.1.1.1", name="Cloudflare", median_latency_ms=10.0, mean_latency_ms=10.0, success_rate=0.80, failure_rate=0.20, composite_score=80.0)
    with patch.object(optimizer, "evaluate_and_rank", new=AsyncMock(return_value=[lossy_candidate])):
        with patch("app.dns.detector.measure_dns_latency", return_value=50.0):
            res = await optimizer.auto_optimize_dns()
            assert res is None  # Skipped due to packet loss > 0%

    # 4. Test post-switch verification failure triggers immediate rollback
    good_candidate = ResolverScore(ip="1.1.1.1", name="Cloudflare", median_latency_ms=10.0, mean_latency_ms=10.0, success_rate=1.0, failure_rate=0.0, composite_score=95.0)
    with patch.object(optimizer, "evaluate_and_rank", new=AsyncMock(return_value=[good_candidate])):
        # Current latency 60ms (gain > 15ms), but post-switch query fails (None)
        with patch("app.dns.detector.measure_dns_latency", side_effect=[60.0, None]):
            res = await optimizer.auto_optimize_dns()
            assert res is None
            # Verified that rollback was called
            assert platform.set_interface_dns_servers.call_count >= 2


def test_f6_dual_stack_ipv4_and_ipv6_pairing():
    import socket
    from app.platform.windows.adapter import WindowsPlatformAdapter
    from app.dns.detector import get_provider_ipv6

    p_v6, s_v6 = get_provider_ipv6("1.1.1.1")
    assert p_v6 == "2606:4700:4700::1111"
    assert s_v6 == "2606:4700:4700::1001"

    p_v6_g, s_v6_g = get_provider_ipv6("8.8.8.8")
    assert p_v6_g == "2001:4860:4860::8888"
    assert s_v6_g == "2001:4860:4860::8844"

    adapter = WindowsPlatformAdapter()
    captured_commands = []
    def mock_run(cmd, *args, **kwargs):
        captured_commands.append(cmd)
        m = MagicMock()
        m.returncode = 0
        m.stdout = "2606:4700:4700::1111\n1.1.1.1"
        m.stderr = ""
        return m

    with patch("subprocess.run", side_effect=mock_run):
        with patch.object(adapter, "is_elevated", return_value=True):
            with patch.object(adapter, "get_interface_dns_servers", return_value=["1.1.1.1", "2606:4700:4700::1111"]):
                ok, msg = adapter.set_dns_servers("Wi-Fi", ["1.1.1.1", "1.0.0.1"])
                assert ok is True
                ps_call = next((c for c in captured_commands if "Set-DnsClientServerAddress" in str(c)), None)
                assert ps_call is not None
                ps_str = " ".join(ps_call)
                assert "1.1.1.1" in ps_str
                assert "2606:4700:4700::1111" in ps_str
                assert "2606:4700:4700::1001" in ps_str


def test_f7_physical_vs_virtual_adapter_filtering():
    import socket
    from app.platform.windows.adapter import WindowsPlatformAdapter

    adapter = WindowsPlatformAdapter()
    assert adapter.is_virtual_adapter("wintun") is True
    assert adapter.is_virtual_adapter("WireGuard Tunnel") is True
    assert adapter.is_virtual_adapter("vEthernet (WSL)") is True
    assert adapter.is_virtual_adapter("TAP-Windows Adapter V9") is True
    assert adapter.is_virtual_adapter("Tailscale") is True
    assert adapter.is_virtual_adapter("Wi-Fi") is False
    assert adapter.is_virtual_adapter("Ethernet") is False

    adapter._cached_interface = None
    mock_addrs = {
        "vEthernet (WSL)": [
            MagicMock(family=socket.AF_INET, address="192.168.1.50", netmask="255.255.255.0")
        ],
        "Wi-Fi": [
            MagicMock(family=socket.AF_INET, address="192.168.1.100", netmask="255.255.255.0")
        ],
    }

    with patch.object(adapter, "get_default_gateway", return_value="192.168.1.1"):
        with patch("psutil.net_if_addrs", return_value=mock_addrs):
            chosen = adapter.get_primary_interface()
            assert chosen == "Wi-Fi"


def test_f8_complete_7_step_dns_workflow_enforcement():
    import socket
    from app.dns.service import DnsService
    platform = MagicMock()
    platform.get_interface_dns_servers.side_effect = [
        ["192.168.1.1"],
        ["1.1.1.1", "1.0.0.1", "2606:4700:4700::1111", "2606:4700:4700::1001"],
    ]
    platform.get_interface_dns_mode.return_value = "static"
    platform.set_interface_dns_servers.return_value = (True, "OK")

    state_mgr = DnsStateManager.get_instance()
    service = DnsService(platform_adapter=platform, state_manager=state_mgr)

    mock_addrinfo = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("142.250.190.46", 80))]
    with patch("socket.getaddrinfo", return_value=mock_addrinfo):
        result = service.apply_dns_servers(
            interface_alias="Wi-Fi",
            primary_v4="1.1.1.1",
            secondary_v4="1.0.0.1",
        )

        assert result.success is True
        assert result.step_reached == 7
        assert result.os_verified is True
        assert result.resolver_tested is True
        assert result.rolled_back is False
        assert "1.1.1.1" in result.applied_servers
        assert "2606:4700:4700::1111" in result.applied_servers
        assert platform.flush_dns_cache.call_count >= 1
        assert state_mgr.current.active_servers == result.applied_servers
        assert state_mgr.current.detected_provider == "Cloudflare"


def test_f8_auto_rollback_on_native_resolver_failure():
    import socket
    from app.dns.service import DnsService
    platform = MagicMock()
    platform.get_interface_dns_servers.side_effect = [
        ["192.168.1.1"],
        ["1.1.1.1", "1.0.0.1"],
    ]
    platform.get_interface_dns_mode.return_value = "dhcp"
    platform.set_interface_dns_servers.return_value = (True, "OK")

    state_mgr = DnsStateManager.get_instance()
    service = DnsService(platform_adapter=platform, state_manager=state_mgr)

    with patch("socket.getaddrinfo", side_effect=socket.gaierror("Name resolution failed")):
        result = service.apply_dns_servers(
            interface_alias="Wi-Fi",
            primary_v4="1.1.1.1",
            secondary_v4="1.0.0.1",
        )

        assert result.success is False
        assert result.rolled_back is True
        assert result.resolver_tested is False
        assert result.step_reached == 6
        assert platform.set_interface_dns_dhcp.call_count == 1
        assert state_mgr.current.configured_mode == "dhcp"


def test_adversarial_dhcp_rollback_with_router_ip_preserves_dhcp():
    """Adversarial Regression Test:
    When an adapter has orig_mode == 'dhcp' and orig_servers == ['192.168.1.1'],
    an auto-rollback triggered by Step 6 socket.getaddrinfo failure MUST call
    set_interface_dns_dhcp() rather than setting static DNS to 192.168.1.1,
    and updates DnsStateManager with configured_mode='dhcp'.
    Also tests that whitespace in primary_v4 is correctly stripped for secondary & v6 pairing.
    """
    import socket
    from app.dns.service import DnsService
    platform = MagicMock()
    platform.get_interface_dns_servers.side_effect = [
        ["192.168.1.1"],
        ["1.1.1.1", "1.0.0.1", "2606:4700:4700::1111", "2606:4700:4700::1001"],
    ]
    platform.get_interface_dns_mode.return_value = "dhcp"
    platform.set_interface_dns_servers.return_value = (True, "OK")
    platform.set_interface_dns_dhcp.return_value = (True, "DHCP Restored")

    state_mgr = DnsStateManager.get_instance()
    service = DnsService(platform_adapter=platform, state_manager=state_mgr)

    with patch("socket.getaddrinfo", side_effect=socket.gaierror(11001, "getaddrinfo failed")):
        res = service.apply_dns_servers("Wi-Fi", " 1.1.1.1 ")

        assert res.success is False
        assert res.rolled_back is True
        assert res.step_reached == 6
        assert platform.set_interface_dns_dhcp.call_count == 1
        assert platform.set_interface_dns_servers.call_count == 1
        assert state_mgr.current.configured_mode == "dhcp"
        assert state_mgr.current.active_servers == ["192.168.1.1"]


@pytest.mark.asyncio
async def test_adversarial_switch_dns_remediation_rollback_dhcp_router_ip():
    """Adversarial Regression Test for SwitchDNSResolverAction:
    Ensures pre-state with DHCP router IP correctly identifies is_dhcp=True
    and triggers set_interface_dns_dhcp on rollback.
    """
    from app.remediation.actions.switch_dns import SwitchDNSResolverAction
    platform = MagicMock()
    platform.get_primary_interface.return_value = "Wi-Fi"
    platform.get_interface_dns_servers.return_value = ["192.168.1.1"]
    platform.get_interface_dns_mode.return_value = "dhcp"
    platform.set_interface_dns_servers.return_value = (True, "OK")
    platform.set_interface_dns_dhcp.return_value = (True, "DHCP Restored")
    platform.flush_dns_cache.return_value = (True, "Flushed")

    action = SwitchDNSResolverAction()
    pre_state = await action.execute(platform, {"target_dns_servers": ["1.1.1.1"]})
    assert pre_state["is_dhcp"] is True

    ok, msg = await action.rollback(platform, {}, pre_state)
    assert ok is True
    assert "DHCP" in msg
    assert platform.set_interface_dns_dhcp.call_count == 1
    assert platform.set_interface_dns_servers.call_count == 1
    assert DnsStateManager.get_instance().current.configured_mode == "dhcp"


def test_f9_diagnosis_view_no_hardcoded_fallback():
    from app.ui.views.diagnosis_view import DiagnosisView
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    view = DiagnosisView()

    obs = MagicMock()
    obs.get_latest_measurement.return_value = None

    state_mgr = DnsStateManager.get_instance()
    state_mgr.update(last_measured_ms=None, active_servers=[])

    view.update_telemetry(obs)

    row2_val = view.table.item(2, 1).text()
    assert row2_val != "45 ms"
    assert row2_val == "—"

    state_mgr.update(last_measured_ms=18.2, detected_provider="Cloudflare", active_servers=["1.1.1.1"])
    view.update_telemetry(obs)

    row2_val_after = view.table.item(2, 1).text()
    assert row2_val_after == "18 ms"
    assert "Cloudflare" in view.row_l4.lbl_desc.text()
    assert "18 ms" in view.row_l4.lbl_metric.text()
