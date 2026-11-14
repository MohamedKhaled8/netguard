"""Unit tests for NetGuard AI Stage 1 Observability Engine."""

import pytest
import asyncio
from unittest.mock import MagicMock
from datetime import datetime, timezone
from app.core.config.models import ProbingConfig
from app.core.events.bus import EventBus
from app.core.models.metrics import MetricType, ProbeStatus, MeasurementSource, Measurement
from app.storage.database import DatabaseManager
from app.storage.repositories.measurement_repo import MeasurementRepository
from app.platform.interfaces import IPlatformAdapter
from app.monitoring.probes.gateway_probe import GatewayProbe
from app.monitoring.probes.external_probe import ExternalConnectivityProbe
from app.monitoring.probes.dns_probe import DNSResolutionProbe
from app.monitoring.probes.interface_probe import InterfaceStatsCollector
from app.monitoring.schedulers.engine import ObservabilityEngine


class MockPlatformAdapter(IPlatformAdapter):
    """Mock platform adapter providing deterministic probe responses."""

    def __init__(self, ping_ok=True, ping_lat=12.0, tcp_ok=True, tcp_lat=15.0):
        self.ping_ok = ping_ok
        self.ping_lat = ping_lat
        self.tcp_ok = tcp_ok
        self.tcp_lat = tcp_lat

    def get_default_gateway(self):
        return "192.168.1.1"

    def get_primary_interface(self):
        return "Wi-Fi"

    def ping(self, target: str, timeout_sec: float = 1.5):
        return self.ping_ok, self.ping_lat

    def tcp_connect(self, target: str, port: int = 80, timeout_sec: float = 2.0):
        return self.tcp_ok, self.tcp_lat

    def flush_dns_cache(self):
        return True, "Flushed"

    def get_interface_dns_servers(self, interface_name: str):
        return ["1.1.1.1", "8.8.8.8"]

    def set_interface_dns_servers(self, interface_name: str, servers):
        return True, "OK"

    def renew_ip_lease(self, interface_name: str):
        return True, "Renewed"

    def get_wifi_metrics(self, interface_name=None):
        return {
            "is_wifi": True,
            "signal_percent": 88.0,
            "ssid": "TestRouter_5G",
            "bssid": "00:11:22:33:44:55",
            "rx_rate_mbps": 433.0,
            "tx_rate_mbps": 433.0,
        }


@pytest.mark.asyncio
async def test_gateway_probe_healthy():
    platform = MockPlatformAdapter(ping_ok=True, ping_lat=5.2)
    probe = GatewayProbe(platform_adapter=platform, interval_sec=1.0, timeout_sec=1.0)
    results = await probe.run()

    assert len(results) == 3
    reach = next(r for r in results if r.metric_type == MetricType.GATEWAY_REACHABILITY)
    assert reach.status == ProbeStatus.SUCCESS
    assert reach.raw_value == 1.0

    lat = next(r for r in results if r.metric_type == MetricType.GATEWAY_LATENCY)
    assert lat.raw_value == 5.2

    loss = next(r for r in results if r.metric_type == MetricType.GATEWAY_PACKET_LOSS)
    assert loss.raw_value == 0.0


@pytest.mark.asyncio
async def test_gateway_probe_unreachable():
    platform = MockPlatformAdapter(ping_ok=False, ping_lat=0.0)
    probe = GatewayProbe(platform_adapter=platform, interval_sec=1.0, timeout_sec=1.0)
    results = await probe.run()

    reach = next(r for r in results if r.metric_type == MetricType.GATEWAY_REACHABILITY)
    assert reach.status == ProbeStatus.FAILED
    assert reach.raw_value == 0.0

    loss = next(r for r in results if r.metric_type == MetricType.GATEWAY_PACKET_LOSS)
    assert loss.raw_value == 1.0


@pytest.mark.asyncio
async def test_external_probe_dual_channel():
    platform = MockPlatformAdapter(ping_ok=True, ping_lat=22.0, tcp_ok=True, tcp_lat=25.0)
    probe = ExternalConnectivityProbe(
        platform_adapter=platform,
        targets=["1.1.1.1"],
        interval_sec=1.0,
        timeout_sec=1.0,
    )
    probe.min_interval_sec = 0.0  # disable rate-limit for immediate test cycle
    # Run twice to test jitter calculation
    res1 = await probe.run()
    assert len(res1) >= 3

    platform.ping_lat = 45.0  # simulate jitter
    res2 = await probe.run()

    jitter_res = next((r for r in res2 if r.metric_type == MetricType.JITTER_MS), None)
    assert jitter_res is not None
    assert jitter_res.raw_value > 0.0


@pytest.mark.asyncio
async def test_observability_engine_cycle(tmp_path):
    db_file = tmp_path / "obs_test.db"
    db_manager = DatabaseManager(db_path=db_file, enable_wal=False)
    repo = MeasurementRepository(db_manager)
    bus = EventBus()
    platform = MockPlatformAdapter()

    cfg = ProbingConfig(
        gateway_interval_sec=0.5,
        external_interval_sec=0.5,
        dns_interval_sec=0.5,
        external_targets=["1.1.1.1"],
        dns_test_domains=["google.com"],
    )

    engine = ObservabilityEngine(
        config=cfg,
        event_bus=bus,
        platform_adapter=platform,
        measurement_repo=repo,
        window_size=10,
    )

    received_events = []
    async def capture_event(topic: str, payload: Measurement):
        received_events.append((topic, payload))

    await bus.subscribe("telemetry.*", capture_event)

    # Run single cycle
    measurements = await engine.run_single_cycle()
    assert len(measurements) > 0
    assert len(received_events) == len(measurements)

    # Check sliding window
    gw_lat_window = engine.get_sliding_window(MetricType.GATEWAY_LATENCY)
    assert len(gw_lat_window) >= 1
    assert gw_lat_window[-1].raw_value == 12.0

    # Verify database persistence
    recent_in_db = repo.get_recent(limit=50)
    assert len(recent_in_db) == len(measurements)
