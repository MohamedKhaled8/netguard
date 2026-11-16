"""Unit tests for Centralized Network Thresholds (R4)."""

import pytest
from app.core.thresholds import NetworkThresholds, DEFAULT_THRESHOLDS
from app.core.config.loader import load_config
from app.diagnosis.classifiers.gateway_fault import GatewayHealthClassifier
from app.diagnosis.classifiers.dns_fault import DNSHealthClassifier
from app.diagnosis.classifiers.wifi_fault import WifiInstabilityClassifier


def test_thresholds_defaults():
    t = NetworkThresholds()
    assert t.latency.gateway_warning_ms == 25.0
    assert t.latency.gateway_critical_ms == 80.0
    assert t.loss.gateway_critical_ratio == 0.40
    assert t.jitter.warning_ms == 30.0
    assert t.wifi.signal_critical_pct == 25.0
    assert t.dns.switching_hysteresis_ms == 8.0
    assert t.remediation.action_cooldowns["switch_dns_resolver"] == 45.0


def test_thresholds_compatibility_properties():
    t = NetworkThresholds()
    # Ensure backward-compatible properties match DiagnosisThresholds
    assert t.gateway_latency_warning_ms == 25.0
    assert t.gateway_latency_critical_ms == 80.0
    assert t.gateway_packet_loss_critical == 0.40
    assert t.external_latency_warning_ms == 80.0
    assert t.external_latency_critical_ms == 200.0
    assert t.external_packet_loss_critical == 0.30
    assert t.dns_latency_warning_ms == 100.0
    assert t.dns_latency_critical_ms == 350.0
    assert t.jitter_warning_ms == 30.0
    assert t.jitter_critical_ms == 80.0

    # Test property setters
    t.gateway_latency_warning_ms = 35.0
    assert t.latency.gateway_warning_ms == 35.0
    assert t.gateway_latency_warning_ms == 35.0


def test_thresholds_apply_overrides():
    t = NetworkThresholds()
    t.apply_overrides({
        "latency.gateway_critical_ms": 110.0,
        "wifi.signal_critical_pct": 35.0,
        "dns.switching_hysteresis_ms": 12.0,
    })
    assert t.latency.gateway_critical_ms == 110.0
    assert t.gateway_latency_critical_ms == 110.0
    assert t.wifi.signal_critical_pct == 35.0
    assert t.dns.switching_hysteresis_ms == 12.0


def test_classifiers_accept_network_thresholds():
    t = NetworkThresholds()
    gw_classifier = GatewayHealthClassifier(t)
    dns_classifier = DNSHealthClassifier(t)
    wifi_classifier = WifiInstabilityClassifier(t)

    assert gw_classifier.thresholds.gateway_latency_critical_ms == 80.0
    assert dns_classifier.thresholds.dns_latency_critical_ms == 350.0
    assert wifi_classifier.thresholds is not None


def test_thresholds_from_config():
    cfg = load_config()
    t = NetworkThresholds.from_config(cfg)
    assert t.latency.gateway_critical_ms == cfg.thresholds.gateway_latency_critical_ms
    assert t.loss.gateway_critical_ratio == cfg.thresholds.gateway_packet_loss_critical
    assert t.probing.gateway_interval_sec == cfg.probing.gateway_interval_sec
    assert t.remediation.default_cooldown_sec == cfg.remediation.cooldown_period_sec
