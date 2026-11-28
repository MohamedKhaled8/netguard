"""Structured Section 2 models for complete 32-area router inspection, coverage reporting, and secret redaction."""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.wifi.models import (
    ConnectedDeviceRecord,
    MeasurementProvenance,
    RouterCapabilities,
    RouterConfigurationSnapshot,
    RouterDiscoveryResult,
    utc_now,
)


class InspectionCoverageStatus(str, Enum):
    """Explicit honesty states required by Section 2 coverage reporting."""

    FULLY_INSPECTED = "FULLY INSPECTED"
    PARTIALLY_INSPECTED = "PARTIALLY INSPECTED"
    NOT_ACCESSIBLE = "NOT ACCESSIBLE"
    NOT_SUPPORTED = "NOT SUPPORTED"
    READ_ONLY = "READ-ONLY"
    CONFIGURATION_CHANGE_SUPPORTED = "CONFIGURATION CHANGE SUPPORTED"


ROUTER_CONFIG_DOMAINS: tuple[tuple[str, str, str], ...] = (
    ("device_info", "Device information & system status", "معلومات الجهاز وحالة النظام"),
    ("wan_internet", "WAN & Internet configuration", "إعدادات الاتصال بالإنترنت (WAN)"),
    ("access_line_stats", "DSL / Fiber / Ethernet WAN line stats", "إحصائيات خط الاتصال (DSL / فايبر / إيثرنت)"),
    ("lan_ip", "LAN & IP addressing", "إعدادات الشبكة المحلية (LAN) وعناوين IP"),
    ("dhcp_server", "DHCP server & address pools", "خادم DHCP ونطاق توزيع العناوين"),
    ("dhcp_leases", "DHCP leases & reservations", "عناوين DHCP المحجوزة والمخصصة"),
    ("ipv4_ipv6", "IPv4 & IPv6 configuration", "إعدادات IPv4 و IPv6"),
    ("dns", "DNS & DNS forwarding", "خوادم الأسماء (DNS) وإعادة التوجيه"),
    ("wifi_24", "Wi-Fi 2.4 GHz configuration", "إعدادات واي فاي 2.4 GHz"),
    ("wifi_5", "Wi-Fi 5 GHz configuration", "إعدادات واي فاي 5 GHz"),
    ("wifi_6", "Wi-Fi 6 GHz configuration", "إعدادات واي فاي 6 GHz"),
    ("ssid_security", "SSIDs & security configuration", "أسماء الشبكات (SSID) والتشفير والأمان"),
    ("channel_width", "Channel selection & channel width", "القنوات وعرض القناة اللاسلكية"),
    ("tx_power_radio", "Transmit power & radio parameters", "قوة البث ومعاملات الراديو"),
    ("band_steering_roaming", "Band steering & roaming options", "توجيه النطاق (Band Steering) والتجوال"),
    ("guest_wifi", "Guest network configuration", "شبكة الضيوف (Guest Wi-Fi)"),
    ("wireless_clients", "Connected wireless clients", "الأجهزة المتصلة لاسلكياً"),
    ("wired_clients", "Connected wired clients", "الأجهزة المتصلة سلكياً"),
    ("qos_priority", "QoS & traffic prioritization", "جودة الخدمة (QoS) وترتيب الأولويات"),
    ("bandwidth_control", "Bandwidth control & per-device limits", "التحكم في السرعة والحدود لكل جهاز"),
    ("queue_shaping", "Queue management & traffic shaping", "إدارة الطوابير وتشكيل الحركة (SQM)"),
    ("wmm", "WMM & wireless QoS settings", "إعدادات WMM اللاسلكية"),
    ("firewall", "Firewall & security settings", "جدار الحماية والأمان"),
    ("nat_port_forwarding", "NAT & port forwarding", "ترجمة العناوين (NAT) وتوجيه المنافذ"),
    ("upnp", "UPnP configuration", "إعدادات UPnP"),
    ("ipv6_firewall", "IPv6 firewall & routing", "جدار حماية وتوجيه IPv6"),
    ("parental_controls", "Parental controls & access restrictions", "الرقابة الأبوية وقيود الوصول"),
    ("mac_filtering", "MAC filtering & access control", "تصفية عناوين MAC والتحكم في الوصول"),
    ("vpn_proxy", "VPN & proxy settings", "إعدادات VPN والوكيل"),
    ("system_logs", "System logs & connection events", "سجلات النظام وأحداث الاتصال"),
    ("firmware_updates", "Firmware & update information", "البرنامج الثابت (Firmware) والتحديثات"),
    ("advanced_stability", "Advanced performance & stability settings", "إعدادات متقدمة للأداء والاستقرار"),
)

SECRET_KEY_PATTERNS = re.compile(
    r"(pass|pwd|psk|wepkey|wpakey|secret|private[_-]?key|token|cookie|session[_-]?id|"
    r"auth[_-]?key|shared[_-]?key|pin|wps[_-]?pin|adminpassword|keypassphrase|preshared)",
    re.IGNORECASE,
)


def is_secret_setting_name(key: str) -> bool:
    return bool(SECRET_KEY_PATTERNS.search(key or ""))


def sanitize_setting_value(key: str, value: Any) -> tuple[str, bool]:
    """Never retain raw passwords, Wi-Fi PSKs, private keys, or session cookies."""
    if is_secret_setting_name(key):
        return "[REDACTED]", True
    text = "" if value is None else str(value)
    if len(text) > 512:
        text = text[:509] + "..."
    # Also redact obvious inline bearer/cookie patterns
    if re.search(r"(sessionid|sysauth|stok|x_hw_token)\s*=\s*[A-Za-z0-9\-_]{8,}", text, re.I):
        return "[REDACTED_TOKEN]", True
    return text, False


class SettingValueState(str, Enum):
    """Explicit value classification distinguishing legitimate zero/false from missing/error states."""

    PRESENT = "present"
    NUMERIC_ZERO = "numeric_zero"
    BOOLEAN_FALSE = "boolean_false"
    EMPTY_STRING = "empty_string"
    NULL = "null"
    MISSING = "missing"
    UNSUPPORTED = "unsupported"
    PARSE_ERROR = "parse_error"
    REDACTED = "redacted"


class RouterSettingRecord(BaseModel):
    """Single setting extracted from a router configuration interface or DOM."""

    setting_key: str
    setting_label: str
    setting_label_ar: str = ""
    domain: str
    section: str = ""
    submenu: str = ""
    page_name: str = ""
    current_value: str = ""
    typed_value: Any = None
    value_state: SettingValueState = SettingValueState.PRESENT
    instance_id: str = ""
    object_path: str = ""
    redacted: bool = False
    meaning: str = ""
    configurable: bool = False
    change_supported: bool = False
    write_method: Optional[str] = None
    suboptimal_hint: Optional[str] = None
    provenance: MeasurementProvenance = MeasurementProvenance.ROUTER_REPORTED


class RouterPageInspectionRecord(BaseModel):
    """Per-page/section/submenu inspection ledger."""

    page_id: str
    page_name: str
    section: str
    submenu: str = ""
    url_or_path: str = ""
    domains_covered: List[str] = Field(default_factory=list)
    accessed: bool = False
    values_extracted: bool = False
    coverage_status: InspectionCoverageStatus = InspectionCoverageStatus.NOT_ACCESSIBLE
    change_capability: InspectionCoverageStatus = InspectionCoverageStatus.READ_ONLY
    error_or_reason: str = ""
    settings_count: int = 0
    settings: List[RouterSettingRecord] = Field(default_factory=list)


class InspectionCoverageReport(BaseModel):
    """Truthful coverage accounting across pages, submenus, and the 32 config domains."""

    inspected_at: datetime = Field(default_factory=utc_now)
    adapter_id: str
    total_pages_discovered: int = 0
    fully_inspected_pages: int = 0
    partially_inspected_pages: int = 0
    not_accessible_pages: int = 0
    not_supported_pages: int = 0
    read_only_pages: int = 0
    change_supported_pages: int = 0
    total_settings_extracted: int = 0
    domains_inspected: List[str] = Field(default_factory=list)
    domains_missing: List[str] = Field(default_factory=list)
    pages: List[RouterPageInspectionRecord] = Field(default_factory=list)
    backup_export_checked: bool = False
    backup_readable: bool = False
    backup_note: str = ""
    secrets_redacted_count: int = 0
    honesty_statement: str = ""


class RouterConfigurationModel(BaseModel):
    """Normalized configuration model uniting all 32 router domains, pages, and coverage."""

    captured_at: datetime = Field(default_factory=utc_now)
    discovery: Optional[RouterDiscoveryResult] = None
    capabilities: Optional[RouterCapabilities] = None
    snapshot: RouterConfigurationSnapshot
    devices: List[ConnectedDeviceRecord] = Field(default_factory=list)
    domains: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    settings: List[RouterSettingRecord] = Field(default_factory=list)
    coverage: InspectionCoverageReport
    system_logs: List[str] = Field(default_factory=list)
    raw_sections_sanitized: Dict[str, Any] = Field(default_factory=dict)
