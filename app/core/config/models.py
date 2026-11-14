"""Configuration Models for NetGuard AI."""

from __future__ import annotations
from typing import List, Dict, Any
from pydantic import BaseModel, Field


class ProbingConfig(BaseModel):
    gateway_interval_sec: float = Field(default=1.0, ge=0.1)
    external_interval_sec: float = Field(default=3.0, ge=0.1)
    dns_interval_sec: float = Field(default=5.0, ge=0.1)
    interface_stats_interval_sec: float = Field(default=1.0, ge=0.1)
    active_connections_interval_sec: float = Field(default=5.0, ge=0.1)
    icmp_timeout_sec: float = Field(default=1.5, gt=0.1)
    tcp_timeout_sec: float = Field(default=2.0, gt=0.1)
    dns_timeout_sec: float = Field(default=2.0, gt=0.1)
    max_concurrent_probes: int = Field(default=10, ge=1, le=50)
    external_targets: List[str] = Field(
        default_factory=lambda: ["1.1.1.1", "8.8.8.8", "9.9.9.9", "208.67.222.222"]
    )
    dns_test_domains: List[str] = Field(
        default_factory=lambda: ["google.com", "cloudflare.com", "microsoft.com", "apple.com"]
    )
    dns_fallback_resolvers: List[str] = Field(
        default_factory=lambda: ["1.1.1.1", "8.8.8.8", "9.9.9.9"]
    )


class DiagnosisThresholds(BaseModel):
    gateway_latency_warning_ms: float = Field(default=25.0, gt=1.0)
    gateway_latency_critical_ms: float = Field(default=80.0, gt=5.0)
    gateway_packet_loss_critical: float = Field(default=0.40, ge=0.0, le=1.0)
    external_latency_warning_ms: float = Field(default=80.0, gt=5.0)
    external_latency_critical_ms: float = Field(default=200.0, gt=10.0)
    external_packet_loss_critical: float = Field(default=0.30, ge=0.0, le=1.0)
    dns_latency_warning_ms: float = Field(default=100.0, gt=5.0)
    dns_latency_critical_ms: float = Field(default=350.0, gt=10.0)
    jitter_warning_ms: float = Field(default=30.0, gt=1.0)
    jitter_critical_ms: float = Field(default=80.0, gt=5.0)
    sliding_window_samples: int = Field(default=10, ge=3, le=100)


class RemediationConfig(BaseModel):
    mode: str = Field(default="autonomous_safe")
    max_retries_per_action: int = Field(default=2, ge=1, le=5)
    cooldown_period_sec: float = Field(default=60.0, ge=0.0)
    circuit_breaker_failure_threshold: int = Field(default=3, ge=1, le=10)
    circuit_breaker_reset_timeout_sec: float = Field(default=300.0, ge=0.1)
    verification_duration_sec: float = Field(default=5.0, ge=0.1)
    allow_level_3_disruptive: bool = False


class DatabaseConfig(BaseModel):
    db_path: str = "data/netguard.db"
    enable_wal: bool = True
    retention_days: int = 30


class LoggingConfig(BaseModel):
    level: str = "INFO"
    log_dir: str = "logs"
    log_to_console: bool = True
    log_to_file: bool = True


class AppConfig(BaseModel):
    environment: str = "development"
    probing: ProbingConfig = Field(default_factory=ProbingConfig)
    thresholds: DiagnosisThresholds = Field(default_factory=DiagnosisThresholds)
    remediation: RemediationConfig = Field(default_factory=RemediationConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
