"""Core Domain Models for Telemetry, Diagnostics, and Remediation."""

from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class MetricType(str, Enum):
    GATEWAY_LATENCY = "gateway_latency"
    GATEWAY_PACKET_LOSS = "gateway_packet_loss"
    GATEWAY_REACHABILITY = "gateway_reachability"
    EXTERNAL_LATENCY = "external_latency"
    EXTERNAL_PACKET_LOSS = "external_packet_loss"
    EXTERNAL_TCP_CONNECT = "external_tcp_connect"
    DNS_LATENCY = "dns_latency"
    DNS_SUCCESS_RATE = "dns_success_rate"
    BANDWIDTH_RX_BYTES_PER_SEC = "bandwidth_rx_bytes_sec"
    BANDWIDTH_TX_BYTES_PER_SEC = "bandwidth_tx_bytes_sec"
    JITTER_MS = "jitter_ms"
    WIFI_SIGNAL_PERCENT = "wifi_signal_percent"
    WIFI_LINK_SPEED_MBPS = "wifi_link_speed_mbps"
    CELLULAR_RSRP = "cellular_rsrp"
    CELLULAR_RSRQ = "cellular_rsrq"
    CELLULAR_SINR = "cellular_sinr"
    BUFFERBLOAT_BLOAT_FACTOR = "bufferbloat_factor"
    ACTIVE_SOCKET_COUNT = "active_socket_count"


class ProbeStatus(str, Enum):
    SUCCESS = "success"
    DEGRADED = "degraded"
    FAILED = "failed"
    TIMEOUT = "timeout"
    UNREACHABLE = "unreachable"
    SKIPPED = "skipped"
    UNAVAILABLE = "unavailable"


class MeasurementSource(str, Enum):
    ICMP_ECHO = "icmp_echo"
    TCP_CONNECT = "tcp_connect"
    DNS_QUERY = "dns_query"
    PSUTIL_INTERFACE = "psutil_interface"
    WINDOWS_IPHLP = "windows_iphlp"
    WINDOWS_NETSH = "windows_netsh"
    LINUX_SYSFS = "linux_sysfs"
    ROUTER_API = "router_api"
    SYNTHETIC_TEST = "synthetic_test"


class Measurement(BaseModel):
    """Normalized observation emitted by any monitoring probe."""
    id: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: MeasurementSource
    target_or_interface: str
    metric_type: MetricType
    raw_value: float
    normalized_value: float
    unit: str
    status: ProbeStatus
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class ProbableCause(str, Enum):
    HEALTHY = "healthy"
    LOCAL_INTERFACE_DOWN = "local_interface_down"
    LOCAL_GATEWAY_UNREACHABLE = "local_gateway_unreachable"
    LOCAL_GATEWAY_HIGH_LATENCY = "local_gateway_high_latency"
    WI_FI_SIGNAL_DEGRADED = "wi_fi_signal_degraded"
    CELLULAR_SIGNAL_DEGRADED = "cellular_signal_degraded"
    ISP_UPSTREAM_OUTAGE = "isp_upstream_outage"
    ISP_UPSTREAM_HIGH_LATENCY = "isp_upstream_high_latency"
    DNS_RESOLVER_UNRESPONSIVE = "dns_resolver_unresponsive"
    DNS_RESOLVER_HIGH_LATENCY = "dns_resolver_high_latency"
    DESTINATION_SPECIFIC_OUTAGE = "destination_specific_outage"
    BUFFERBLOAT_UPLOAD = "bufferbloat_upload_congestion"
    BUFFERBLOAT_DOWNLOAD = "bufferbloat_download_congestion"
    BACKGROUND_APP_SATURATION = "background_app_saturation"
    UNKNOWN_ANOMALY = "unknown_anomaly"


class DiagnosisSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Evidence(BaseModel):
    """An individual empirical piece of data supporting or refuting a diagnosis."""
    metric_type: MetricType
    target: str
    observed_value: float
    threshold_value: float
    condition: str
    weight: float = Field(default=1.0, ge=0.0, le=2.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Diagnosis(BaseModel):
    """Root-cause assessment synthesized from multi-vector evidence."""
    id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    probable_cause: ProbableCause
    confidence: float = Field(ge=0.0, le=1.0)
    severity: DiagnosisSeverity
    supporting_evidence: List[Evidence] = Field(default_factory=list)
    contradictory_evidence: List[Evidence] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    auto_remediation_permitted: bool = False
    explanation: str = ""


class RiskLevel(str, Enum):
    LEVEL_1_LOW = "level_1_low"
    LEVEL_2_CONTROLLED = "level_2_controlled"
    LEVEL_3_DISRUPTIVE = "level_3_disruptive"


class OperatingMode(str, Enum):
    """Network remediation operational authority levels."""
    AUTO = "auto"
    ASK = "ask"
    WATCH = "watch"

    # Backward compatibility aliases
    AUTONOMOUS_SAFE = "auto"
    ASSISTED = "ask"
    OBSERVATION = "watch"

    @classmethod
    def _missing_(cls, value: object) -> Optional[OperatingMode]:
        """Resolve legacy string values and case-insensitive aliases."""
        if isinstance(value, str):
            norm = value.lower().strip()
            aliases = {
                "autonomous_safe": cls.AUTO,
                "autonomous": cls.AUTO,
                "safe": cls.AUTO,
                "auto": cls.AUTO,
                "assisted": cls.ASK,
                "ask": cls.ASK,
                "observation": cls.WATCH,
                "observe": cls.WATCH,
                "watch": cls.WATCH,
            }
            if norm in aliases:
                return aliases[norm]
        return super()._missing_(value)


class ActionExecutionStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    TIMED_OUT = "timed_out"
    REJECTED_BREAKER_OPEN = "rejected_breaker_open"


class ActionExecutionRecord(BaseModel):
    """Immutable audit entry for every remediation action executed."""
    id: Optional[str] = None
    action_id: str
    action_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    risk_level: RiskLevel
    trigger_diagnosis_id: Optional[str] = None
    pre_remedy_metrics: Dict[str, Any] = Field(default_factory=dict)
    post_remedy_metrics: Dict[str, Any] = Field(default_factory=dict)
    status: ActionExecutionStatus
    execution_duration_ms: float = 0.0
    verification_duration_ms: float = 0.0
    error_message: Optional[str] = None
    rollback_performed: bool = False
    rollback_success: Optional[bool] = None
