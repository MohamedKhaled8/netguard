"""Typed Pydantic contracts for the Wi-Fi, Network, and Router Diagnostics section."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class MeasurementProvenance(str, Enum):
    """Distinguishes directly measured OS/network data from inferred or router data."""

    MEASURED = "measured"
    INFERRED = "inferred"
    ROUTER_REPORTED = "router_reported"
    UNAVAILABLE = "unavailable"


class MetricValue(BaseModel):
    """Explicit metric wrapper carrying value, unit, and provenance."""

    value: Any = None
    unit: str = ""
    provenance: MeasurementProvenance = MeasurementProvenance.UNAVAILABLE
    source: str = ""
    reason: Optional[str] = None


class WlanEventRecord(BaseModel):
    """Connection, disconnection, roaming, or WLAN AutoConfig operational event."""

    event_id: int
    timestamp: datetime
    event_type: Literal[
        "connected",
        "disconnected",
        "roam",
        "association",
        "auth",
        "scan",
        "other",
    ] = "other"
    interface_name: Optional[str] = None
    ssid: Optional[str] = None
    bssid: Optional[str] = None
    reason_code: Optional[str] = None
    message: str = ""
    source: str = "wlan_autoconfig_log"


class RoamingEventRecord(BaseModel):
    """Recorded BSSID or band transition event."""

    timestamp: datetime
    ssid: Optional[str] = None
    from_bssid: Optional[str] = None
    to_bssid: Optional[str] = None
    from_channel: Optional[int] = None
    to_channel: Optional[int] = None
    from_band: Optional[str] = None
    to_band: Optional[str] = None
    from_rssi_dbm: Optional[int] = None
    to_rssi_dbm: Optional[int] = None
    source: str = "session_tracker"


class AdapterCapabilities(BaseModel):
    """Wireless adapter hardware and driver capabilities."""

    interface_name: str
    adapter_description: Optional[str] = None
    driver_version: Optional[str] = None
    driver_date: Optional[str] = None
    driver_provider: Optional[str] = None
    supported_phys: List[str] = Field(default_factory=list)
    supported_bands: List[str] = Field(default_factory=list)
    max_channel_width_mhz: Optional[int] = None
    max_spatial_streams: Optional[int] = None
    supports_6ghz: Optional[bool] = None
    supports_wifi6: Optional[bool] = None
    supports_wifi7: Optional[bool] = None
    roaming_aggressiveness: Optional[str] = None
    preferred_band: Optional[str] = None
    channel_width_24_setting: Optional[str] = None
    channel_width_5_setting: Optional[str] = None
    regulatory_domain: Optional[str] = None
    source_details: Dict[str, str] = Field(default_factory=dict)


class InterfaceStatsSnapshot(BaseModel):
    """Packet and frame error counters from NDIS / Native Wifi."""

    rx_bytes: Optional[int] = None
    tx_bytes: Optional[int] = None
    rx_packets: Optional[int] = None
    tx_packets: Optional[int] = None
    rx_errors: Optional[int] = None
    tx_errors: Optional[int] = None
    rx_discards: Optional[int] = None
    tx_discards: Optional[int] = None
    phy_tx_failed_count: Optional[int] = None
    phy_retry_count: Optional[int] = None
    phy_multiple_retry_count: Optional[int] = None
    phy_fcs_error_count: Optional[int] = None
    provenance: MeasurementProvenance = MeasurementProvenance.UNAVAILABLE
    source: str = ""


class WifiInterfaceTelemetry(BaseModel):
    """Complete Wi-Fi link and RF telemetry snapshot for the active Windows adapter."""

    captured_at: datetime = Field(default_factory=utc_now)
    interface_name: Optional[str] = None
    interface_guid: Optional[str] = None
    adapter_description: Optional[str] = None
    connection_state: str = "disconnected"
    ssid: Optional[str] = None
    bssid: Optional[str] = None
    phy_standard: Optional[str] = None
    phy_provenance: MeasurementProvenance = MeasurementProvenance.UNAVAILABLE
    band: Optional[str] = None
    channel: Optional[int] = None
    channel_frequency_mhz: Optional[int] = None
    channel_width_mhz: Optional[int] = None
    channel_width_provenance: MeasurementProvenance = MeasurementProvenance.UNAVAILABLE
    channel_width_note: Optional[str] = None
    rssi_dbm: Optional[int] = None
    rssi_provenance: MeasurementProvenance = MeasurementProvenance.UNAVAILABLE
    signal_quality_pct: Optional[int] = None
    signal_quality_provenance: MeasurementProvenance = MeasurementProvenance.UNAVAILABLE
    noise_floor_dbm: Optional[float] = None
    noise_floor_provenance: MeasurementProvenance = MeasurementProvenance.UNAVAILABLE
    noise_floor_reason: str = (
        "Windows WLAN APIs and this wireless driver do not expose an actual RF noise floor in dBm."
    )
    snr_db: Optional[float] = None
    snr_provenance: MeasurementProvenance = MeasurementProvenance.UNAVAILABLE
    snr_reason: str = (
        "SNR cannot be computed because noise floor is not reported by the wireless driver."
    )
    tx_link_rate_mbps: Optional[float] = None
    rx_link_rate_mbps: Optional[float] = None
    link_rate_provenance: MeasurementProvenance = MeasurementProvenance.UNAVAILABLE
    mcs_index: Optional[int] = None
    mcs_provenance: MeasurementProvenance = MeasurementProvenance.UNAVAILABLE
    mcs_reason: str = (
        "Current per-packet MCS index is not exposed via standard Windows Native Wifi APIs."
    )
    spatial_streams: Optional[int] = None
    spatial_streams_provenance: MeasurementProvenance = MeasurementProvenance.UNAVAILABLE
    spatial_streams_reason: str = (
        "Active spatial stream count is unavailable unless inferred from AP IEs or link capabilities."
    )
    security_mode: Optional[str] = None
    qbss_channel_utilization_pct: Optional[float] = None
    qbss_station_count: Optional[int] = None
    interface_stats: Optional[InterfaceStatsSnapshot] = None
    capabilities: Optional[AdapterCapabilities] = None
    recent_wlan_events: List[WlanEventRecord] = Field(default_factory=list)
    roaming_events: List[RoamingEventRecord] = Field(default_factory=list)
    measurement_notes: List[str] = Field(default_factory=list)


class NeighborAccessPoint(BaseModel):
    """Detected nearby BSSID with RF and 802.11 Information Element attributes."""

    ssid: str = ""
    is_hidden: bool = False
    bssid: str
    band: str
    channel: int
    center_frequency_mhz: int
    channel_width_mhz: Optional[int] = None
    channel_width_provenance: MeasurementProvenance = MeasurementProvenance.UNAVAILABLE
    secondary_channel_offset: Optional[int] = None
    center_freq_seg0_channel: Optional[int] = None
    rssi_dbm: Optional[int] = None
    signal_quality_pct: Optional[int] = None
    security_mode: Optional[str] = None
    phy_standard: Optional[str] = None
    supported_phys: List[str] = Field(default_factory=list)
    max_spatial_streams: Optional[int] = None
    in_reg_domain: Optional[bool] = None
    country_code: Optional[str] = None
    qbss_utilization_pct: Optional[float] = None
    qbss_station_count: Optional[int] = None
    is_connected_ap: bool = False
    last_seen_timestamp: Optional[int] = None


class AccessPointScanResult(BaseModel):
    """Neighboring Wi-Fi BSS scan output grouped by band and channel."""

    captured_at: datetime = Field(default_factory=utc_now)
    interface_name: Optional[str] = None
    scan_mode: Literal["cached_bss_list", "active_wlan_scan", "netsh_fallback"] = (
        "cached_bss_list"
    )
    active_scan_deferred_reason: Optional[str] = None
    regulatory_domain: str = "EG"
    total_bss_count: int = 0
    access_points: List[NeighborAccessPoint] = Field(default_factory=list)
    grouped_by_band_channel: Dict[str, Dict[int, List[NeighborAccessPoint]]] = Field(
        default_factory=dict
    )
    scan_notes: List[str] = Field(default_factory=list)


class ChannelScoreBreakdown(BaseModel):
    """Transparent, component-by-component channel congestion estimate."""

    band: str
    channel: int
    center_frequency_mhz: int
    width_mhz: int
    occupied_range_mhz: Tuple[float, float]
    is_dfs: bool = False
    is_reg_permitted: bool = True
    is_adapter_supported: bool = True
    is_current_channel: bool = False
    total_score: float
    interference_level: Literal["low", "moderate", "high", "severe"]
    co_channel_ap_count: int = 0
    overlapping_ap_count: int = 0
    co_channel_contribution: float = 0.0
    adjacent_overlap_contribution: float = 0.0
    width_penalty: float = 0.0
    dfs_caution_penalty: float = 0.0
    strong_interferers: List[Dict[str, Any]] = Field(default_factory=list)
    data_confidence: float = 0.0
    confidence_label: Literal["low", "medium", "high"] = "medium"
    formula_notes: str = ""


class ChannelRecommendation(BaseModel):
    """Actionable channel recommendation with full rationale and limitations."""

    rank: int
    band: str
    channel: int
    width_mhz: int
    total_score: float
    interference_level: Literal["low", "moderate", "high", "severe"]
    is_current_channel: bool = False
    is_dfs: bool = False
    strong_interfering_aps: List[Dict[str, Any]] = Field(default_factory=list)
    co_channel_contribution: float = 0.0
    adjacent_overlap_contribution: float = 0.0
    channel_width_impact: float = 0.0
    data_confidence: float = 0.0
    confidence_label: Literal["low", "medium", "high"] = "medium"
    reason: str
    advantages: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class BandChannelAnalysisResult(BaseModel):
    """Per-band RF scoring output distinguishing scan estimate from RF utilization."""

    band: str
    target_width_mhz: int
    regulatory_domain: str
    current_channel: Optional[int] = None
    current_channel_score: Optional[ChannelScoreBreakdown] = None
    estimated_notice: str = (
        "Scores estimate neighboring beacon congestion and spectral overlap from Wi-Fi scan data; "
        "they do not measure hidden non-Wi-Fi interference or live airtime duty cycle unless QBSS load is advertised."
    )
    channel_scores: List[ChannelScoreBreakdown] = Field(default_factory=list)
    recommended_channels: List[ChannelRecommendation] = Field(default_factory=list)
    data_confidence: float = 0.0
    scan_completeness_notes: List[str] = Field(default_factory=list)


class FullChannelAnalysisReport(BaseModel):
    """Combined multi-band channel analysis output."""

    captured_at: datetime = Field(default_factory=utc_now)
    regulatory_domain: str = "EG"
    bands: Dict[str, BandChannelAnalysisResult] = Field(default_factory=dict)
    overall_summary: str = ""


class PingBurstStats(BaseModel):
    """ICMP burst statistics for gateway, IPv4 public, or IPv6 public targets."""

    target: str
    address_family: Literal["ipv4", "ipv6"] = "ipv4"
    status: Literal[
        "ok",
        "not_configured",
        "unreachable",
        "failed",
        "skipped",
        "cancelled",
    ] = "ok"
    packets_sent: int = 0
    packets_received: int = 0
    packet_loss_pct: float = 0.0
    avg_ms: Optional[float] = None
    min_ms: Optional[float] = None
    max_ms: Optional[float] = None
    jitter_ms: Optional[float] = None
    p95_ms: Optional[float] = None
    rtts_ms: List[float] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    note: Optional[str] = None


class TracerouteHopSummary(BaseModel):
    """Single hop within a controlled 5-hop diagnostic trace."""

    hop_number: int
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    rtts_ms: List[float] = Field(default_factory=list)
    avg_ms: Optional[float] = None
    loss_pct: float = 0.0
    responded: bool = False
    interpretation: str = ""


class TracerouteDiagnosticResult(BaseModel):
    """Controlled multi-hop diagnostic trace result."""

    target: str
    max_hops: int = 5
    status: Literal["ok", "failed", "cancelled", "skipped"] = "ok"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    hops: List[TracerouteHopSummary] = Field(default_factory=list)
    interpretation_note: str = (
        "Non-responsive intermediate hops alone may indicate ICMP rate-limiting and are not proof of packet loss."
    )


class NetworkConditionReport(BaseModel):
    """Environment conditions detected prior to running sequential latency probes."""

    captured_at: datetime = Field(default_factory=utc_now)
    active_interface: Optional[str] = None
    interface_type: Optional[str] = None
    default_gateway: Optional[str] = None
    gateway_changed: bool = False
    previous_gateway: Optional[str] = None
    vpn_active: bool = False
    vpn_interfaces: List[str] = Field(default_factory=list)
    proxy_enabled: bool = False
    proxy_server: Optional[str] = None
    recent_disconnect_count: int = 0
    recent_roam_count: int = 0
    interface_rx_errors: int = 0
    interface_tx_errors: int = 0
    interface_rx_discards: int = 0
    competing_throughput_mbps: Optional[float] = None
    large_transfer_suspected: bool = False
    active_interface_rx_mbps: Optional[float] = None
    active_interface_tx_mbps: Optional[float] = None
    meeting_active: bool = False
    warnings: List[str] = Field(default_factory=list)


class NetworkDiagnosticsReport(BaseModel):
    """Sequential baseline internet and local-network diagnostic sequence."""

    run_id: str
    started_at: datetime
    completed_at: datetime
    sequence_order: List[str] = Field(default_factory=list)
    conditions: NetworkConditionReport
    gateway_ping: PingBurstStats
    internet_ping: PingBurstStats
    ipv6_ping: PingBurstStats
    traceroute: Optional[TracerouteDiagnosticResult] = None
    diagnosis_summary: str = ""
    notes: List[str] = Field(default_factory=list)


class DnsTargetMetrics(BaseModel):
    """Multi-sample DNS resolution latency and reliability measurements."""

    role: Literal["configured", "router", "cloudflare", "google"]
    server_ip: Optional[str] = None
    server_label: str
    is_applicable: bool = True
    status: Literal["ok", "not_applicable", "unreachable", "failed", "cancelled"] = "ok"
    query_mode: str = "cache_bypassed_multi_sample"
    sample_count: int = 0
    successful_samples: int = 0
    failed_samples: int = 0
    min_ms: Optional[float] = None
    avg_ms: Optional[float] = None
    median_ms: Optional[float] = None
    max_ms: Optional[float] = None
    stdev_ms: Optional[float] = None
    raw_samples_ms: List[float] = Field(default_factory=list)
    response_statuses: List[str] = Field(default_factory=list)
    icmp_baseline_ms: Optional[float] = None
    estimated_dns_processing_ms: Optional[float] = None
    provider_identified: Optional[str] = None
    note: Optional[str] = None


class DnsDiagnosticsReport(BaseModel):
    """Comparative DNS benchmark distinguishing resolver overhead from general RTT."""

    captured_at: datetime = Field(default_factory=utc_now)
    interface_name: Optional[str] = None
    configured_dns_servers: List[str] = Field(default_factory=list)
    router_dns_server: Optional[str] = None
    targets: List[DnsTargetMetrics] = Field(default_factory=list)
    cache_bypass_method: str = ""
    recommended_dns: Optional[str] = None
    comparison_confidence: Literal["low", "medium", "high"] = "medium"
    meeting_safety_frozen: bool = False
    auto_modified_dns: bool = False
    summary: str = ""
    notes: List[str] = Field(default_factory=list)


class SpeedTestReport(BaseModel):
    """Throughput test clearly separating Wi-Fi PHY rate, LAN throughput, and Internet speed."""

    run_id: str
    started_at: datetime
    completed_at: datetime
    status: Literal[
        "completed",
        "partial",
        "blocked_meeting",
        "blocked_busy",
        "cancelled",
        "failed",
    ] = "completed"
    server_name: str = ""
    server_url: str = ""
    wifi_tx_link_rate_mbps: Optional[float] = None
    wifi_rx_link_rate_mbps: Optional[float] = None
    local_lan_throughput_mbps: Optional[float] = None
    local_lan_note: str = (
        "Local LAN throughput requires a local iperf3/LAN endpoint and is not inferred from Wi-Fi link rate."
    )
    download_mbps: Optional[float] = None
    download_duration_sec: Optional[float] = None
    download_bytes: int = 0
    upload_tested: bool = False
    upload_mbps: Optional[float] = None
    upload_duration_sec: Optional[float] = None
    upload_bytes: int = 0
    qos_active_during_test: bool = False
    qos_policies_count: int = 0
    qos_summary: str = ""
    interface_name: Optional[str] = None
    ssid: Optional[str] = None
    bssid: Optional[str] = None
    band: Optional[str] = None
    idle_latency_ms: Optional[float] = None
    loaded_download_latency_ms: Optional[float] = None
    loaded_upload_latency_ms: Optional[float] = None
    jitter_ms: Optional[float] = None
    packet_loss_pct: Optional[float] = None
    method_used: str = ""
    failure_reason: Optional[str] = None
    router_wan_down_mbps: Optional[float] = None
    router_wan_up_mbps: Optional[float] = None
    notes: List[str] = Field(default_factory=list)


class BufferbloatPhaseResult(BaseModel):
    """Latency and packet-loss behavior during idle, download, upload, or combined load."""

    phase: Literal["idle", "download_load", "upload_load", "combined_load"]
    target_ip: str
    started_at: datetime
    completed_at: datetime
    packets_sent: int
    packets_received: int
    packet_loss_pct: float = 0.0
    avg_ms: Optional[float] = None
    min_ms: Optional[float] = None
    p95_ms: Optional[float] = None
    max_ms: Optional[float] = None
    jitter_ms: Optional[float] = None
    delta_over_idle_ms: Optional[float] = None
    grade: Optional[str] = None
    throughput_mbps: Optional[float] = None


class BufferbloatDiagnosticsReport(BaseModel):
    """Sequential idle/download/upload/combined bufferbloat evaluation."""

    run_id: str
    started_at: datetime
    completed_at: datetime
    status: Literal[
        "completed",
        "partial",
        "blocked_meeting",
        "blocked_busy",
        "cancelled",
        "failed",
    ] = "completed"
    target_ip: str = "1.1.1.1"
    idle_phase: Optional[BufferbloatPhaseResult] = None
    download_phase: Optional[BufferbloatPhaseResult] = None
    upload_phase: Optional[BufferbloatPhaseResult] = None
    combined_phase: Optional[BufferbloatPhaseResult] = None
    download_bloat_grade: Optional[str] = None
    upload_bloat_grade: Optional[str] = None
    overall_grade: Optional[str] = None
    qos_was_active: bool = False
    qos_policies_count: int = 0
    idle_qos_comparison_run: bool = False
    idle_qos_pre_post_verified: Optional[bool] = None
    idle_qos_comparison_summary: Optional[str] = None
    summary: str = ""
    notes: List[str] = Field(default_factory=list)


class RouterCapabilities(BaseModel):
    """Honest capability matrix exposed by the active router adapter."""

    adapter_id: str
    vendor_family: str = "Generic"
    hardware_verified: bool = False
    supports_session_auth: bool = False
    supports_wifi_read: bool = False
    supports_wifi_write: bool = False
    supports_channel_write: bool = False
    supports_width_write: bool = False
    supports_tx_power_write: bool = False
    supports_connected_devices_read: bool = False
    supports_per_device_bandwidth: bool = False
    supports_sqm_or_qos_read: bool = False
    supports_sqm_or_qos_write: bool = False
    supports_dns_config_read: bool = False
    supports_dns_config_write: bool = False
    supports_backup_export: bool = False
    supports_wan_read: bool = False
    supports_lan_dhcp_read: bool = False
    supports_firewall_nat_read: bool = False
    supports_logs_read: bool = False
    supports_diagnostics_run: bool = False
    supports_restore_backup: bool = False
    supports_web_dom_inspection: bool = False
    supports_tr069_or_usp: bool = False
    supports_snmp_read: bool = False
    supports_snmp_write: bool = False
    verified_operations: List[str] = Field(default_factory=list)
    unverified_operations: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class RouterDiscoveryResult(BaseModel):
    """Passive gateway discovery, reachable management URLs, and adapter selection."""

    discovered_at: datetime = Field(default_factory=utc_now)
    gateway_ip: Optional[str] = None
    gateway_mac: Optional[str] = None
    gateway_vendor_oui: Optional[str] = None
    management_urls: List[str] = Field(default_factory=list)
    reachable_ports: List[int] = Field(default_factory=list)
    preferred_url: Optional[str] = None
    is_https: bool = False
    tls_trusted: Optional[bool] = None
    security_warning: Optional[str] = None
    detected_vendor: Optional[str] = None
    hardware_vendor: Optional[str] = None
    detected_model: Optional[str] = None
    hardware_revision: Optional[str] = None
    firmware_version: Optional[str] = None
    isp_brand: Optional[str] = None
    wan_connection_type: Optional[str] = None
    lan_subnet: Optional[str] = None
    supported_bands: List[str] = Field(default_factory=list)
    adapter_id: str = "generic_probe"
    detection_confidence: str = "low"
    detection_evidence: List[str] = Field(default_factory=list)
    available_interfaces: List[Dict[str, Any]] = Field(default_factory=list)
    snmp_sys_descr: Optional[str] = None
    web_dom_available: bool = False
    upnp_igd_available: bool = False
    upnp_device_friendly_name: Optional[str] = None
    upnp_external_ip: Optional[str] = None
    capabilities: RouterCapabilities
    notes: List[str] = Field(default_factory=list)


class RouterAuthResult(BaseModel):
    """Outcome of a single, non-brute-force router authentication attempt."""

    authenticated: bool
    adapter_id: str
    base_url: str
    used_https: bool = False
    error_kind: Literal["none", "auth_rejected", "timeout", "unreachable", "security_ack_required", "lockout_guard", "unsupported"] = "none"
    security_warning: Optional[str] = None
    lockout_risk_warning: Optional[str] = None
    message: str = ""
    credential_storage_mode: Literal["session", "windows_credential_manager"] = "session"


class RouterWifiRadioConfig(BaseModel):
    """Router wireless radio settings reported by the router adapter."""

    band: str
    enabled: Optional[bool] = None
    ssid: Optional[str] = None
    channel: Optional[str] = None
    channel_width: Optional[str] = None
    tx_power: Optional[str] = None
    security_mode: Optional[str] = None
    mode: Optional[str] = None
    band_steering_enabled: Optional[bool] = None


class RouterConfigurationSnapshot(BaseModel):
    """Read-only router state extracted via the authenticated or UPnP adapter."""

    captured_at: datetime = Field(default_factory=utc_now)
    adapter_id: str
    hardware_verified: bool = False
    vendor: Optional[str] = None
    isp_brand: Optional[str] = None
    model: Optional[str] = None
    hardware_revision: Optional[str] = None
    firmware_version: Optional[str] = None
    wan_status: Optional[str] = None
    wan_connection_type: Optional[str] = None
    wan_ip: Optional[str] = None
    wan_down_mbps: Optional[float] = None
    wan_up_mbps: Optional[float] = None
    wan_line_stats: Dict[str, Any] = Field(default_factory=dict)
    lan_ip: Optional[str] = None
    lan_subnet_mask: Optional[str] = None
    dhcp_pool_start: Optional[str] = None
    dhcp_pool_end: Optional[str] = None
    dhcp_lease_time_sec: Optional[int] = None
    uptime_seconds: Optional[int] = None
    dns_servers: List[str] = Field(default_factory=list)
    dhcp_enabled: Optional[bool] = None
    radios: Dict[str, RouterWifiRadioConfig] = Field(default_factory=dict)
    qos_enabled: Optional[bool] = None
    qos_mode: Optional[str] = None
    sqm_available: bool = False
    sqm_enabled: Optional[bool] = None
    upnp_enabled: Optional[bool] = None
    firewall_level: Optional[str] = None
    firewall_ipv6_enabled: Optional[bool] = None
    nat_enabled: Optional[bool] = None
    ipv6_enabled: Optional[bool] = None
    band_steering_enabled: Optional[bool] = None
    guest_wifi_enabled: Optional[bool] = None
    mac_filtering_enabled: Optional[bool] = None
    parental_controls_enabled: Optional[bool] = None
    tr069_enabled: Optional[bool] = None
    snmp_enabled: Optional[bool] = None
    extra_sections: Dict[str, Any] = Field(default_factory=dict)
    raw_backup_blob: Optional[str] = None
    provenance: MeasurementProvenance = MeasurementProvenance.ROUTER_REPORTED
    notes: List[str] = Field(default_factory=list)


class ConnectedDeviceRecord(BaseModel):
    """Client device discovered from Windows ARP/Neighbor table and/or router API."""

    ip_address: Optional[str] = None
    ipv6_addresses: List[str] = Field(default_factory=list)
    mac_address: Optional[str] = None
    hostname: Optional[str] = None
    vendor: Optional[str] = None
    connection_type: Literal["wifi_24", "wifi_5", "wifi_6", "ethernet", "unknown"] = (
        "unknown"
    )
    connection_status: Literal["connected", "stale", "offline", "unknown"] = "unknown"
    last_seen: Optional[datetime] = None
    radio_band: Optional[str] = None
    ssid: Optional[str] = None
    rssi_dbm: Optional[int] = None
    link_rate_mbps: Optional[float] = None
    tx_rate_mbps: Optional[float] = None
    rx_rate_mbps: Optional[float] = None
    bytes_rx: Optional[int] = None
    bytes_tx: Optional[int] = None
    rx_limit_kbps: Optional[int] = None
    tx_limit_kbps: Optional[int] = None
    priority_level: Optional[str] = None
    bandwidth_schedule: Optional[str] = None
    bandwidth_profile: Optional[str] = None
    is_local_host: bool = False
    is_gateway: bool = False
    source: Literal["os_arp", "router_api", "merged"] = "os_arp"
    discovery_sources: List[str] = Field(default_factory=list)
    router_metadata: Dict[str, Any] = Field(default_factory=dict)
    supports_rate_limit: bool = False
    notes: List[str] = Field(default_factory=list)

    @field_validator("connection_type", mode="before")
    @classmethod
    def _normalize_connection_type(cls, value: Any) -> str:
        raw = str(value or "unknown").strip().lower()
        if raw in ("wifi_24", "wifi_5", "wifi_6", "ethernet", "unknown"):
            return raw
        if any(k in raw for k in ("6e", "6g", "6 ghz", "802.11ax 6", "wifi6")):
            return "wifi_6"
        if any(k in raw for k in ("5g", "5 ghz", "5.0", "wifi5", "wireless 5")):
            return "wifi_5"
        if any(k in raw for k in ("2.4", "24g", "2g", "wifi2", "wlan", "wi-fi", "wifi", "wireless")):
            return "wifi_24"
        if any(k in raw for k in ("eth", "lan", "wired", "cable")):
            return "ethernet"
        return "unknown"


class RouterChangeProposal(BaseModel):
    """Staged router configuration change requiring explicit user approval."""

    proposal_id: str
    category: Literal[
        "wifi_channel",
        "channel_width",
        "tx_power",
        "band_steering",
        "security_mode",
        "dns",
        "qos_sqm",
        "device_rate_limit",
        "dhcp",
        "wan",
        "firewall",
        "upnp",
        "wmm",
        "roaming",
        "ipv6",
        "other",
    ]
    title: str
    target_field: str
    band: Optional[str] = None
    target_ip: Optional[str] = None
    target_mac: Optional[str] = None
    current_value: Optional[str] = None
    proposed_value: str
    reason: str
    expected_impact: str
    risk_level: Literal["low", "medium", "high"] = "low"
    requires_reconnect_warning: bool = False
    supported_by_adapter: bool = False
    requires_manual_apply: bool = True
    evidence: List[str] = Field(default_factory=list)


class RouterApplyResult(BaseModel):
    """Outcome of applying a router change with backup and readback verification."""

    proposal_id: str
    success: bool
    applied_automatically: bool = False
    backup_taken: bool = False
    readback_verified: Optional[bool] = None
    rolled_back: bool = False
    previous_value: Optional[str] = None
    verified_value: Optional[str] = None
    message: str
    timestamp: datetime = Field(default_factory=utc_now)


class FaultCategory(str, Enum):
    """Required diagnostic fault categories for cross-layer ranking."""

    WIFI_SIGNAL_DISTANCE = "weak_wifi_signal_or_distance"
    WIFI_CHANNEL_CONGESTION = "wifi_channel_congestion"
    WRONG_BAND = "wrong_band_24_instead_of_5"
    ROUTER_BUFFERBLOAT = "router_bufferbloat"
    SLOW_DNS = "slow_or_poor_dns"
    LOCAL_BACKGROUND_UPLOAD = "local_background_upload_or_device"
    ISP_UPSTREAM_ISSUE = "isp_or_upstream_issue"
    WINDOWS_OR_DRIVER = "windows_driver_or_adapter_issue"


class UnifiedFinding(BaseModel):
    """Single diagnosed bottleneck backed by observed evidence."""

    finding_id: str
    category: FaultCategory
    severity: Literal["critical", "high", "medium", "low", "info"]
    confidence: float
    title: str
    summary: str
    evidence: List[str] = Field(default_factory=list)
    provenance: MeasurementProvenance = MeasurementProvenance.MEASURED


class UnifiedRecommendation(BaseModel):
    """Actionable fix ranked by impact and grouped by scope."""

    recommendation_id: str
    priority: int
    scope: Literal["local_quick", "router_config", "isp_or_hardware"]
    title: str
    action_summary: str
    expected_gain: str
    risk_level: Literal["low", "medium", "high"] = "low"
    auto_applicable: bool = False
    requires_approval: bool = True
    related_categories: List[FaultCategory] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class UnifiedDiagnosticReport(BaseModel):
    """Combined cross-layer diagnosis and prioritized action plan."""

    captured_at: datetime = Field(default_factory=utc_now)
    findings: List[UnifiedFinding] = Field(default_factory=list)
    recommendations: List[UnifiedRecommendation] = Field(default_factory=list)
    executive_summary: str = ""


class BeforeAfterSnapshot(BaseModel):
    """Comparable diagnostic snapshot persisted before or after network/router changes."""

    snapshot_id: str
    label: str
    created_at: datetime = Field(default_factory=utc_now)
    interface_name: Optional[str] = None
    ssid: Optional[str] = None
    bssid: Optional[str] = None
    band: Optional[str] = None
    channel: Optional[int] = None
    channel_width_mhz: Optional[int] = None
    rssi_dbm: Optional[int] = None
    tx_link_rate_mbps: Optional[float] = None
    gateway_avg_ms: Optional[float] = None
    gateway_loss_pct: Optional[float] = None
    internet_avg_ms: Optional[float] = None
    internet_loss_pct: Optional[float] = None
    dns_configured_avg_ms: Optional[float] = None
    download_mbps: Optional[float] = None
    upload_mbps: Optional[float] = None
    download_bloat_delta_ms: Optional[float] = None
    upload_bloat_delta_ms: Optional[float] = None
    bufferbloat_grade: Optional[str] = None
    qos_active: Optional[bool] = None
    channel_score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MetricDelta(BaseModel):
    """Comparison of a single KPI between Before and After snapshots."""

    metric_name: str
    before_value: Optional[float] = None
    after_value: Optional[float] = None
    unit: str = ""
    delta: Optional[float] = None
    delta_pct: Optional[float] = None
    verdict: Literal[
        "improved",
        "degraded",
        "inconclusive",
        "unchanged",
        "unavailable",
    ] = "unavailable"
    note: str = ""


class BeforeAfterComparison(BaseModel):
    """Honest Before/After verification highlighting drift and noise thresholds."""

    before: BeforeAfterSnapshot
    after: BeforeAfterSnapshot
    comparable: bool = True
    condition_drift_warnings: List[str] = Field(default_factory=list)
    deltas: List[MetricDelta] = Field(default_factory=list)
    overall_verdict: Literal["improved", "mixed", "inconclusive", "degraded"] = (
        "inconclusive"
    )
    summary: str = ""
