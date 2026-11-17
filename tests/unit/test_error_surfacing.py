"""Unit tests for error surfacing, probe failure tracking, and non-intrusive UI alerts."""

from __future__ import annotations
import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from app.core.models.metrics import MetricType, ProbeStatus, MeasurementSource
from app.monitoring.models.probe_result import ProbeResult
from app.monitoring.probes.base import BaseProbe
from app.monitoring.schedulers.engine import ObservabilityEngine
from app.core.config.models import ProbingConfig
from app.core.bus import EventBus
from app.storage.repositories.measurement_repo import MeasurementRepository
from PySide6.QtWidgets import QApplication
from app.ui import tokens
from app.ui.views.dashboard_view import DashboardView

_app = QApplication.instance() or QApplication(["-platform", "offscreen"])


class DummyProbe(BaseProbe):
    def __init__(self, name: str = "dummy_probe") -> None:
        super().__init__(
            name=name,
            interval_sec=1.0,
            timeout_sec=1.0,
            platform_adapter=MagicMock(),
        )

    async def execute(self):
        return []


def test_base_probe_timeout_and_error_handling():
    probe = DummyProbe("gateway_probe")
    timeout_res = probe._handle_timeout()
    assert len(timeout_res) == 1
    assert timeout_res[0].status == ProbeStatus.TIMEOUT
    assert timeout_res[0].metric_type == MetricType.GATEWAY_REACHABILITY
    assert "timed out" in timeout_res[0].error_message

    err_res = probe._handle_error(RuntimeError("hardware failure"))
    assert len(err_res) == 1
    assert err_res[0].status == ProbeStatus.FAILED
    assert "hardware failure" in err_res[0].error_message


def test_observability_engine_gateway_persistent_failure():
    mock_platform = MagicMock()
    mock_repo = MagicMock(spec=MeasurementRepository)
    event_bus = EventBus()
    config = ProbingConfig()

    engine = ObservabilityEngine(
        config=config,
        event_bus=event_bus,
        platform_adapter=mock_platform,
        measurement_repo=mock_repo,
    )

    failed_gw_result = [
        ProbeResult(
            timestamp=datetime.now(timezone.utc),
            source=MeasurementSource.ICMP_ECHO,
            target="192.168.1.1",
            metric_type=MetricType.GATEWAY_REACHABILITY,
            raw_value=0.0,
            normalized_value=0.0,
            unit="bool",
            status=ProbeStatus.FAILED,
            confidence=1.0,
            error_message="Gateway unreachable",
        )
    ]

    # Cycle 1 & 2: not persistent yet (threshold = 3)
    engine._update_probe_health("gateway_probe", failed_gw_result)
    assert engine.get_primary_probe_error(threshold=3) is None

    engine._update_probe_health("gateway_probe", failed_gw_result)
    assert engine.get_primary_probe_error(threshold=3) is None

    # Cycle 3: persistent threshold met
    engine._update_probe_health("gateway_probe", failed_gw_result)
    primary_err = engine.get_primary_probe_error(threshold=3)
    assert primary_err is not None
    assert primary_err["code"] == "cannot_reach_gateway"
    assert "تعذر الوصول إلى الراوتر" in primary_err["message"]
    assert engine.get_primary_probe_error_message(threshold=3) == primary_err["message"]

    # Cycle 4: recovered
    success_gw_result = [
        ProbeResult(
            timestamp=datetime.now(timezone.utc),
            source=MeasurementSource.ICMP_ECHO,
            target="192.168.1.1",
            metric_type=MetricType.GATEWAY_REACHABILITY,
            raw_value=1.0,
            normalized_value=1.0,
            unit="bool",
            status=ProbeStatus.SUCCESS,
            confidence=1.0,
        )
    ]
    engine._update_probe_health("gateway_probe", success_gw_result)
    assert engine.get_primary_probe_error(threshold=3) is None
    assert engine.get_primary_probe_error_message(threshold=3) is None


def test_observability_engine_ping_blocked_categorization():
    mock_platform = MagicMock()
    mock_repo = MagicMock(spec=MeasurementRepository)
    engine = ObservabilityEngine(
        config=ProbingConfig(),
        event_bus=EventBus(),
        platform_adapter=mock_platform,
        measurement_repo=mock_repo,
    )

    # Ping failed, but TCP connect succeeded
    ping_blocked_results = [
        ProbeResult(
            timestamp=datetime.now(timezone.utc),
            source=MeasurementSource.ICMP_ECHO,
            target="1.1.1.1",
            metric_type=MetricType.EXTERNAL_LATENCY,
            raw_value=0.0,
            normalized_value=0.0,
            unit="ms",
            status=ProbeStatus.FAILED,
            metadata={"icmp": False, "tcp": True},
        ),
        ProbeResult(
            timestamp=datetime.now(timezone.utc),
            source=MeasurementSource.TCP_CONNECT,
            target="1.1.1.1:53",
            metric_type=MetricType.EXTERNAL_TCP_CONNECT,
            raw_value=1.0,
            normalized_value=1.0,
            unit="bool",
            status=ProbeStatus.SUCCESS,
            metadata={"port": 53},
        ),
    ]

    for _ in range(3):
        engine._update_probe_health("external_probe", ping_blocked_results)

    err = engine.get_primary_probe_error(threshold=3)
    assert err is not None
    assert err["code"] == "ping_blocked"
    assert "حظر بروتوكول البنج" in err["message"]


def test_dashboard_view_probe_alert_bar():
    tokens.ANIMATIONS_ENABLED = False
    view = DashboardView()

    # Initially hidden
    assert view.probe_alert_bar.isHidden()

    # Trigger persistent alert
    view.set_probe_status_alert("حظر بروتوكول البنج (Ping blocked)")
    assert not view.probe_alert_bar.isHidden()
    assert "حظر بروتوكول البنج" in view.lbl_probe_alert_msg.text()
    assert view.status_dot._status_color == tokens.STATUS_WARN

    # Clear alert
    view.set_probe_status_alert(None)
    assert view.probe_alert_bar.isHidden()
    assert view.status_dot._status_color == tokens.STATUS_OK
