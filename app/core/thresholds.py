"""Centralized Network Thresholds and Constants Repository.

Consolidates all latency, loss, jitter, wifi, probing, DNS, and remediation
constants across probes, classifiers, and user interface widgets.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from app.core.config.models import AppConfig


@dataclass
class LatencyThresholds:
    gateway_warning_ms: float = 25.0
    gateway_critical_ms: float = 80.0
    external_warning_ms: float = 80.0
    external_critical_ms: float = 200.0
    dns_warning_ms: float = 100.0
    dns_critical_ms: float = 350.0


@dataclass
class PacketLossThresholds:
    gateway_critical_ratio: float = 0.40
    gateway_healthy_max_ratio: float = 0.20
    gateway_unreachable_ratio: float = 0.50
    external_critical_ratio: float = 0.30
    external_healthy_max_ratio: float = 0.20
    destination_isolated_fail_ratio: float = 0.75
    dns_failure_rate_threshold: float = 0.50
    dashboard_warning_pct: float = 1.0


@dataclass
class JitterThresholds:
    warning_ms: float = 30.0
    critical_ms: float = 80.0
    ui_warning_ms: float = 15.0


@dataclass
class WifiThresholds:
    signal_critical_pct: float = 25.0
    signal_warning_pct: float = 50.0
    link_speed_warning_mbps: float = 54.0


@dataclass
class ProbingIntervals:
    gateway_interval_sec: float = 1.0
    external_interval_sec: float = 3.0
    dns_interval_sec: float = 5.0
    interface_stats_interval_sec: float = 1.0
    wifi_interval_sec: float = 3.0
    active_connections_interval_sec: float = 5.0
    icmp_timeout_sec: float = 1.5
    tcp_timeout_sec: float = 2.0
    dns_timeout_sec: float = 2.0


@dataclass
class DnsSwitchingThresholds:
    min_composite_score: float = 40.0
    switching_hysteresis_ms: float = 8.0
    ui_fast_cutoff_ms: float = 45.0
    ui_warn_cutoff_ms: float = 75.0
    max_acceptable_latency_ms: float = 350.0


@dataclass
class RemediationTiming:
    default_cooldown_sec: float = 60.0
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_reset_timeout_sec: float = 300.0
    verification_duration_sec: float = 5.0
    action_cooldowns: Dict[str, float] = field(default_factory=lambda: {
        "recheck_gateway": 10.0,
        "flush_dns_cache": 15.0,
        "switch_dns_resolver": 45.0,
        "renew_ip_lease": 90.0,
    })
    action_timeouts: Dict[str, float] = field(default_factory=lambda: {
        "recheck_gateway": 4.0,
        "flush_dns_cache": 5.0,
        "switch_dns_resolver": 10.0,
        "renew_ip_lease": 20.0,
    })
    action_max_retries: Dict[str, int] = field(default_factory=lambda: {
        "recheck_gateway": 3,
        "flush_dns_cache": 2,
        "switch_dns_resolver": 2,
        "renew_ip_lease": 1,
    })


class NetworkThresholds:
    """Master repository containing consolidated network thresholds and dynamic overlays."""

    def __init__(
        self,
        latency: Optional[LatencyThresholds] = None,
        loss: Optional[PacketLossThresholds] = None,
        jitter: Optional[JitterThresholds] = None,
        wifi: Optional[WifiThresholds] = None,
        probing: Optional[ProbingIntervals] = None,
        dns: Optional[DnsSwitchingThresholds] = None,
        remediation: Optional[RemediationTiming] = None,
        sliding_window_samples: int = 10,
    ) -> None:
        self.latency = latency or LatencyThresholds()
        self.loss = loss or PacketLossThresholds()
        self.jitter = jitter or JitterThresholds()
        self.wifi = wifi or WifiThresholds()
        self.probing = probing or ProbingIntervals()
        self.dns = dns or DnsSwitchingThresholds()
        self.remediation = remediation or RemediationTiming()
        self.sliding_window_samples = sliding_window_samples

    # Compatibility properties for DiagnosisThresholds consumers
    @property
    def gateway_latency_warning_ms(self) -> float:
        return self.latency.gateway_warning_ms

    @gateway_latency_warning_ms.setter
    def gateway_latency_warning_ms(self, val: float) -> None:
        self.latency.gateway_warning_ms = val

    @property
    def gateway_latency_critical_ms(self) -> float:
        return self.latency.gateway_critical_ms

    @gateway_latency_critical_ms.setter
    def gateway_latency_critical_ms(self, val: float) -> None:
        self.latency.gateway_critical_ms = val

    @property
    def gateway_packet_loss_critical(self) -> float:
        return self.loss.gateway_critical_ratio

    @gateway_packet_loss_critical.setter
    def gateway_packet_loss_critical(self, val: float) -> None:
        self.loss.gateway_critical_ratio = val

    @property
    def external_latency_warning_ms(self) -> float:
        return self.latency.external_warning_ms

    @external_latency_warning_ms.setter
    def external_latency_warning_ms(self, val: float) -> None:
        self.latency.external_warning_ms = val

    @property
    def external_latency_critical_ms(self) -> float:
        return self.latency.external_critical_ms

    @external_latency_critical_ms.setter
    def external_latency_critical_ms(self, val: float) -> None:
        self.latency.external_critical_ms = val

    @property
    def external_packet_loss_critical(self) -> float:
        return self.loss.external_critical_ratio

    @external_packet_loss_critical.setter
    def external_packet_loss_critical(self, val: float) -> None:
        self.loss.external_critical_ratio = val

    @property
    def dns_latency_warning_ms(self) -> float:
        return self.latency.dns_warning_ms

    @dns_latency_warning_ms.setter
    def dns_latency_warning_ms(self, val: float) -> None:
        self.latency.dns_warning_ms = val

    @property
    def dns_latency_critical_ms(self) -> float:
        return self.latency.dns_critical_ms

    @dns_latency_critical_ms.setter
    def dns_latency_critical_ms(self, val: float) -> None:
        self.latency.dns_critical_ms = val

    @property
    def jitter_warning_ms(self) -> float:
        return self.jitter.warning_ms

    @jitter_warning_ms.setter
    def jitter_warning_ms(self, val: float) -> None:
        self.jitter.warning_ms = val

    @property
    def jitter_critical_ms(self) -> float:
        return self.jitter.critical_ms

    @jitter_critical_ms.setter
    def jitter_critical_ms(self, val: float) -> None:
        self.jitter.critical_ms = val

    def apply_overrides(self, overrides: Dict[str, Any]) -> None:
        """Applies nested or direct key overrides dynamically."""
        for key, val in overrides.items():
            if "." in key:
                group, attr = key.split(".", 1)
                sub = getattr(self, group, None)
                if sub is not None and hasattr(sub, attr):
                    setattr(sub, attr, val)
            else:
                applied = False
                for sub in (self.latency, self.loss, self.jitter, self.wifi, self.probing, self.dns, self.remediation):
                    if hasattr(sub, key):
                        setattr(sub, key, val)
                        applied = True
                        break
                if not applied and hasattr(self, key):
                    setattr(self, key, val)

    @classmethod
    def from_config(cls, cfg: AppConfig) -> NetworkThresholds:
        """Builds NetworkThresholds populated from AppConfig."""
        t = cfg.thresholds
        p = cfg.probing
        r = cfg.remediation

        latency = LatencyThresholds(
            gateway_warning_ms=t.gateway_latency_warning_ms,
            gateway_critical_ms=t.gateway_latency_critical_ms,
            external_warning_ms=t.external_latency_warning_ms,
            external_critical_ms=t.external_latency_critical_ms,
            dns_warning_ms=t.dns_latency_warning_ms,
            dns_critical_ms=t.dns_latency_critical_ms,
        )
        loss = PacketLossThresholds(
            gateway_critical_ratio=t.gateway_packet_loss_critical,
            external_critical_ratio=t.external_packet_loss_critical,
        )
        jitter = JitterThresholds(
            warning_ms=t.jitter_warning_ms,
            critical_ms=t.jitter_critical_ms,
        )
        probing = ProbingIntervals(
            gateway_interval_sec=p.gateway_interval_sec,
            external_interval_sec=p.external_interval_sec,
            dns_interval_sec=p.dns_interval_sec,
            interface_stats_interval_sec=p.interface_stats_interval_sec,
            active_connections_interval_sec=p.active_connections_interval_sec,
            icmp_timeout_sec=p.icmp_timeout_sec,
            tcp_timeout_sec=p.tcp_timeout_sec,
            dns_timeout_sec=p.dns_timeout_sec,
        )
        remediation = RemediationTiming(
            default_cooldown_sec=r.cooldown_period_sec,
            circuit_breaker_failure_threshold=r.circuit_breaker_failure_threshold,
            circuit_breaker_reset_timeout_sec=r.circuit_breaker_reset_timeout_sec,
            verification_duration_sec=r.verification_duration_sec,
        )
        return cls(
            latency=latency,
            loss=loss,
            jitter=jitter,
            probing=probing,
            remediation=remediation,
            sliding_window_samples=t.sliding_window_samples,
        )


DEFAULT_THRESHOLDS = NetworkThresholds()
