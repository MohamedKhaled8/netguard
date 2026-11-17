"""Unit tests for NetGuard AI Stage 10 Learning Engine & Stage 11 Digital Twin."""

import pytest
from app.learning.memory import NetworkMemory
from app.core.models.metrics import ProbableCause
from app.simulation.twin import NetworkDigitalTwin


def test_network_memory_contextual_matching():
    mem = NetworkMemory()

    # Record historical incident: DNS unresponsive resolved by switch_dns_resolver
    mem.record_case(
        case_id="case-101",
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        feature_vector={"dns_latency": 350.0, "ext_latency": 25.0},
        action_id="switch_dns_resolver",
        was_successful=True,
        improvement_delta_ms=325.0,
    )

    # Failed attempt with flush_dns on high latency
    mem.record_case(
        case_id="case-102",
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        feature_vector={"dns_latency": 350.0, "ext_latency": 25.0},
        action_id="flush_dns_cache",
        was_successful=False,
        improvement_delta_ms=0.0,
    )

    # When querying similar context, switch_dns_resolver must be selected
    best_act, conf = mem.find_best_action_for_context(
        probable_cause=ProbableCause.DNS_RESOLVER_UNRESPONSIVE,
        current_features={"dns_latency": 340.0, "ext_latency": 24.0},
    )

    assert best_act == "switch_dns_resolver"
    assert conf > 0.60


def test_digital_twin_simulation():
    # Simulate DNS switch from 120ms to 18ms
    sim_dns = NetworkDigitalTwin.simulate_dns_switch(
        current_mean_dns_latency=120.0,
        candidate_resolver_latency=18.0,
    )
    assert sim_dns.is_simulated is True
    assert sim_dns.projected_improvement_pct > 80.0
    assert "SIMULATED_PROJECTION" in sim_dns.label

    # Simulate background download throttling under bufferbloat
    sim_throttle = NetworkDigitalTwin.simulate_background_throttling(
        current_loaded_latency_ms=180.0,
        estimated_idle_latency_ms=20.0,
        throttled_bandwidth_ratio=0.6,
    )
    assert sim_throttle.is_simulated is True
    assert sim_throttle.projected_post_action < 180.0
