"""Integration tests validating live telemetry collection on Windows host."""

import pytest
from app.platform.factory import get_platform_adapter
from app.monitoring.probes.gateway_probe import GatewayProbe
from app.monitoring.probes.external_probe import ExternalConnectivityProbe
from app.monitoring.probes.dns_probe import DNSResolutionProbe
from app.monitoring.probes.interface_probe import InterfaceStatsCollector


@pytest.mark.asyncio
async def test_live_gateway_and_external_probes():
    adapter = get_platform_adapter()
    gw = adapter.get_default_gateway()
    iface = adapter.get_primary_interface()

    assert gw is not None, "Host must have default gateway detected"
    assert iface is not None, "Host must have primary network adapter detected"

    # Test Live Gateway Probe
    gw_probe = GatewayProbe(platform_adapter=adapter, interval_sec=1.0, timeout_sec=1.5)
    gw_results = await gw_probe.run()
    assert len(gw_results) >= 2, "Gateway probe must return reachability and packet loss"

    # Test Live External Probe (Cloudflare & Google DNS)
    ext_probe = ExternalConnectivityProbe(
        platform_adapter=adapter,
        targets=["1.1.1.1", "8.8.8.8"],
        interval_sec=2.0,
        timeout_sec=2.0,
    )
    ext_results = await ext_probe.run()
    assert len(ext_results) > 0, "External probe must produce measurements"

    # Test Live DNS Probe
    dns_probe = DNSResolutionProbe(
        platform_adapter=adapter,
        domains=["google.com", "cloudflare.com"],
        interval_sec=2.0,
        timeout_sec=2.0,
    )
    dns_results = await dns_probe.run()
    assert len(dns_results) > 0, "DNS probe must resolve test domains"
