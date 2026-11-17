"""Unit tests for NetGuard AI Stage 6 Cellular Network Intelligence."""

import pytest
from app.cellular.models import CellularMetrics, SignalQualityCategory
from app.router.generic import GenericRouterAdapter
from app.router.hilink import HuaweiHiLinkAdapter


def test_cellular_metrics_classification():
    # Excellent signal: RSRP >= -80, SINR >= 20
    q_exc = CellularMetrics.classify_quality(rsrp=-75.0, sinr=22.0)
    assert q_exc == SignalQualityCategory.EXCELLENT

    # Good signal: RSRP >= -90, SINR >= 13
    q_good = CellularMetrics.classify_quality(rsrp=-85.0, sinr=15.0)
    assert q_good == SignalQualityCategory.GOOD

    # Fair signal: RSRP >= -100, SINR >= 0
    q_fair = CellularMetrics.classify_quality(rsrp=-96.0, sinr=5.0)
    assert q_fair == SignalQualityCategory.FAIR

    # Poor signal: RSRP < -100
    q_poor = CellularMetrics.classify_quality(rsrp=-112.0, sinr=-4.0)
    assert q_poor == SignalQualityCategory.POOR


@pytest.mark.asyncio
async def test_generic_router_adapter():
    adapter = GenericRouterAdapter(gateway_ip="192.168.1.1")
    info = await adapter.get_device_info()
    assert info["gateway_ip"] == "192.168.1.1"
    assert "detected_model" in info
