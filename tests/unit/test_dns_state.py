"""Unit tests for DNS state manager (Item B1)."""

import pytest
from app.dns.state import DnsStateManager, DnsStateData


def test_dns_state_singleton_and_emission():
    mgr = DnsStateManager.get_instance()
    assert mgr is not None

    received = []
    mgr.state_changed.connect(lambda s: received.append(s))

    mgr.update(active_servers=["8.8.8.8", "8.8.4.4"], detected_provider="Google DNS", is_healthy=True)

    assert len(received) == 1
    state: DnsStateData = received[0]
    assert state.active_servers == ["8.8.8.8", "8.8.4.4"]
    assert state.detected_provider == "Google DNS"
    assert state.is_healthy is True
