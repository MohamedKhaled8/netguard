"""Multi-vendor configuration parser normalizing JSON, XML, JS constructor tables, HTML DOM, SNMP, and backups."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

from app.wifi.models import MeasurementProvenance, RouterConfigurationSnapshot, RouterWifiRadioConfig
from app.wifi.router.models_config import (
    ROUTER_CONFIG_DOMAINS,
    RouterSettingRecord,
    SettingValueState,
    sanitize_setting_value,
)


_SETTING_DOMAIN_MAP: Tuple[Tuple[re.Pattern[str], str, str, str], ...] = (
    (re.compile(r"(productname|hardware|serial|uptime|model|cpu|mem|macaddress|devinfo)", re.I), "device_info", "معلومات الجهاز", "يحدد هوية الراوتر ومواصفات العتاد والجاهزية."),
    (re.compile(r"(softwareversion|firmware|fwver|build|update)", re.I), "firmware_updates", "إصدار البرنامج الثابت", "نسخة النظام التشغيلي والتحديثات الأمنية للراوتر."),
    (re.compile(r"(wan_?ip|wan_?status|pppoe|wanconn|defaultgateway|nat_?type|connectiontype|wan_?down|wan_?up)", re.I), "wan_internet", "إعدادات اتصال الإنترنت (WAN)", "يحدد نوع الاتصال بالمزود وحالة خط الإنترنت الخارجي."),
    (re.compile(r"(snr|attenuation|linedown|lineup|dsl|vdsl|adsl|optic|rxpower|txpower|fec|crc)", re.I), "access_line_stats", "إحصائيات خط الاتصال", "قياسات جودة الخط الفعلي (SNR، التوهين، وسرعة المزامنة القصوى)."),
    (re.compile(r"(lan_?ip|lan_?subnet|subnet|netmask|br0)", re.I), "lan_ip", "إعدادات الشبكة المحلية (LAN)", "عنوان الراوتر الداخلي وقناع الشبكة المحلية."),
    (re.compile(r"(dhcp_?enable|dhcp_?pool|start_?ip|end_?ip|leasetime|dhcp_?lease_time|dhcpserver)", re.I), "dhcp_server", "إعدادات خادم DHCP", "توزيع عناوين IP التلقائي ونطاق العناوين ومدة الإيجار."),
    (re.compile(r"(static.*lease|reserv|dhcplease)", re.I), "dhcp_leases", "حجوزات DHCP", "العناوين الثابتة المحجوزة للأجهزة عبر عنوان MAC."),
    (re.compile(r"(ipv6|slaac|radvd|dhcpv6|pd_)", re.I), "ipv4_ipv6", "إعدادات IPv4 و IPv6", "تفعيل أو تعطيل بروتوكول IPv6 وتوزيع بادئاته."),
    (re.compile(r"(dns|nameserver|dnsrelay|dnsforward)", re.I), "dns", "إعدادات خوادم DNS", "خوادم ترجمة أسماء النطاقات التي يعتمدها الراوتر أو يوزعها للعملاء."),
    (re.compile(r"(wlan0|wl0|2\.4|24g)", re.I), "wifi_24", "إعدادات واي فاي 2.4 GHz", "تحكم بث الشبكة اللاسلكية على تردد 2.4 GHz."),
    (re.compile(r"(wlan1|wl1|5g|5\.0)", re.I), "wifi_5", "إعدادات واي فاي 5 GHz", "تحكم بث الشبكة اللاسلكية على تردد 5 GHz."),
    (re.compile(r"(6g|wifi6e|6_?ghz)", re.I), "wifi_6", "إعدادات واي فاي 6 GHz", "تحكم نطاق 6 GHz إذا كان العتاد يدعم Wi-Fi 6E/7."),
    (re.compile(r"(ssid|beacon|security|wpa|encryption|authmode|cipher|wps)", re.I), "ssid_security", "اسم الشبكة والتشفير", "اسم الواي فاي وبروتوكول التشفير والحماية."),
    (re.compile(r"(channel|bandwidth|width|htmode|bw|chanspec)", re.I), "channel_width", "القناة وعرض النطاق", "تحديد رقم القناة اللاسلكية وعرض النطاق (20/40/80/160 MHz)."),
    (re.compile(r"(tx_?power|powerlevel|country|regdomain|dtim|rts|frag)", re.I), "tx_power_radio", "قوة البث ومعاملات الراديو", "نسبة طاقة الإرسال اللاسلكي ومعاملات البث والتنظيم."),
    (re.compile(r"(band_?steering|smart_?connect|roaming|802\.11k|802\.11v|802\.11r)", re.I), "band_steering_roaming", "توجيه النطاق والتجوال", "نقل الأجهزة تلقائياً بين 2.4 و 5 GHz وخيارات التجوال."),
    (re.compile(r"(guest|visitor)", re.I), "guest_wifi", "شبكة الضيوف", "تفعيل شبكة منفصلة للضيوف وعزلها عن الشبكة المحلية."),
    (re.compile(r"(qos|dscp|priority|diffserv)", re.I), "qos_priority", "جودة الخدمة (QoS)", "ترتيب أولوية حزم البيانات والمكالمات والألعاب."),
    (re.compile(r"(bandwidth_?limit|rate_?limit|max_?limit|traffic_?ctrl)", re.I), "bandwidth_control", "التحكم في السرعة", "تحديد سرعات الرفع والتنزيل للأجهزة."),
    (re.compile(r"(sqm|fq_codel|cake|queue|shaping|htb)", re.I), "queue_shaping", "إدارة الطوابير (SQM)", "خوارزميات منع امتلاء المخازن (Bufferbloat)."),
    (re.compile(r"(wmm|apsd|edca)", re.I), "wmm", "إعدادات WMM", "ترتيب أولوية الوسائط المتعددة لاسلكياً حسب IEEE 802.11e."),
    (re.compile(r"(firewall|spi|dos|alg|dmz)", re.I), "firewall", "جدار الحماية", "مستوى الفحص الأمني وحماية المنافذ."),
    (re.compile(r"(nat|port_?forward|port_?mapping|virtual_?server)", re.I), "nat_port_forwarding", "NAT وتوجيه المنافذ", "تحويل المنافذ وإعدادات NAT و DMZ."),
    (re.compile(r"(upnp)", re.I), "upnp", "بروتوكول UPnP", "السماح للتطبيقات بفتح المنافذ تلقائياً داخل الشبكة."),
    (re.compile(r"(ipv6.*firewall|v6.*filter)", re.I), "ipv6_firewall", "جدار حماية IPv6", "قواعد السماح والمنع لحركة IPv6."),
    (re.compile(r"(parental|time_?limit|url_?filter|schedule)", re.I), "parental_controls", "الرقابة الأبوية", "حظر المواقع أو جدولة أوقات الاتصال."),
    (re.compile(r"(mac_?filter|acl|whitelist|blacklist)", re.I), "mac_filtering", "تصفية MAC", "تقييد الاتصال بعناوين أجهزة محددة."),
    (re.compile(r"(vpn|pptp|l2tp|wireguard|openvpn|proxy|ipsec)", re.I), "vpn_proxy", "إعدادات VPN والوكيل", "بوابات VPN أو الوكيل على مستوى الراوتر."),
    (re.compile(r"(log|syslog|event)", re.I), "system_logs", "سجلات النظام", "سجل أخطاء الخط وانقطاعات الاتصال والأحداث الأمنية."),
)

DOMAIN_LABEL_AR = {d[0]: d[2] for d in ROUTER_CONFIG_DOMAINS}

_FRIENDLY_SETTING_LABELS: Dict[str, Tuple[str, str]] = {
    "vendor": ("Manufacturer", "الشركة المصنّعة"),
    "isp_brand": ("ISP Profile", "مزود الخدمة"),
    "model": ("Router Model", "طراز الراوتر"),
    "firmware_version": ("Firmware Version", "إصدار البرنامج الثابت"),
    "uptime_seconds": ("System Uptime", "مدة التشغيل المتواصل"),
    "wan_status": ("WAN Status", "حالة اتصال الإنترنت"),
    "wan_connection_type": ("WAN Connection Type", "نوع اتصال الإنترنت"),
    "wan_ip": ("WAN IP Address", "عنوان IP الخارجي"),
    "wan_down_mbps": ("WAN Downstream Rate", "سرعة المزامنة للتنزيل"),
    "wan_up_mbps": ("WAN Upstream Rate", "سرعة المزامنة للرفع"),
    "lan_ip": ("LAN IP Address", "عنوان الشبكة المحلية (LAN)"),
    "lan_subnet_mask": ("Subnet Mask", "قناع الشبكة الفرعية"),
    "dhcp_enabled": ("DHCP Server", "حالة خادم DHCP"),
    "dhcp_pool_start": ("DHCP Start IP", "بداية نطاق DHCP"),
    "dhcp_pool_end": ("DHCP End IP", "نهاية نطاق DHCP"),
    "dhcp_lease_time_sec": ("DHCP Lease Time", "مدة إيجار DHCP"),
    "dns_servers": ("DNS Servers", "خوادم DNS"),
    "qos_enabled": ("Router QoS", "حالة جودة الخدمة (QoS)"),
    "qos_mode": ("QoS Mode", "وضع جودة الخدمة"),
    "sqm_enabled": ("SQM / Smart Queue", "إدارة الطوابير الذكية (SQM)"),
    "upnp_enabled": ("UPnP", "بروتوكول UPnP"),
    "firewall_level": ("Firewall Level", "مستوى جدار الحماية"),
    "ipv6_enabled": ("IPv6", "بروتوكول IPv6"),
    "band_steering_enabled": ("Band Steering", "توجيه النطاق التلقائي"),
    "guest_wifi_enabled": ("Guest Wi-Fi", "شبكة الضيوف"),
}

_TR069_OR_NOISE_KEY_RE = re.compile(
    r"^(?:x=|frame_|cur[A-Z]|page|tab|menu|idx$|len$|html|href|src$|url$|img|title$|"
    r"language$|lang$|style$|class$|onclick|cfgmode$|isdtedata$|var_|tmp_|ret$|flag$|err)",
    re.IGNORECASE,
)

# Typed parameter registry: (type_name, default_domain, en_label, ar_label, zero_label_or_none)
_PARAMETER_DEFINITIONS: Dict[str, Tuple[str, str, str, str, Optional[str]]] = {
    "channel": ("int", "channel_width", "Channel", "القناة", "0 (Auto)"),
    "tx_power": ("int", "tx_power_radio", "TX Power", "طاقة البث", "0%"),
    "dhcp_enabled": ("bool", "dhcp_server", "DHCP Server", "حالة خادم DHCP", None),
    "dhcpserverenable": ("bool", "dhcp_server", "DHCP Server", "حالة خادم DHCP", None),
    "dhcpenable": ("bool", "dhcp_server", "DHCP Server", "حالة خادم DHCP", None),
    "dhcp_lease_time_sec": ("int", "dhcp_server", "DHCP Lease Time", "مدة إيجار DHCP", "0 (Infinite / Manual)"),
    "dhcpleasetime": ("int", "dhcp_server", "DHCP Lease Time", "مدة إيجار DHCP", "0 (Infinite / Manual)"),
    "leasetime": ("int", "dhcp_server", "DHCP Lease Time", "مدة إيجار DHCP", "0 (Infinite / Manual)"),
    "minaddress": ("ip", "dhcp_server", "DHCP Start IP", "بداية نطاق DHCP", None),
    "maxaddress": ("ip", "dhcp_server", "DHCP End IP", "نهاية نطاق DHCP", None),
    "subnetmask": ("ip", "lan_ip", "Subnet Mask", "قناع الشبكة الفرعية", None),
    "ipinterfaceipaddress": ("ip", "lan_ip", "LAN IP Address", "عنوان الشبكة المحلية (LAN)", None),
    "dnsservers": ("str", "dns", "DNS Servers", "خوادم DNS", None),
    "dns_servers": ("str", "dns", "DNS Servers", "خوادم DNS", None),
    "upnp_enabled": ("bool", "upnp", "UPnP", "بروتوكول UPnP", None),
    "enblmainupnp": ("bool", "upnp", "Main UPnP", "حالة UPnP الرئيسي", None),
    "enblslvupnp": ("bool", "upnp", "Slave UPnP", "حالة UPnP الفرعي", None),
    "qos_enabled": ("bool", "qos_priority", "Router QoS", "حالة جودة الخدمة (QoS)", None),
    "qosenable": ("bool", "qos_priority", "Router QoS", "حالة جودة الخدمة (QoS)", None),
    "sqm_enabled": ("bool", "queue_shaping", "SQM / Smart Queue", "إدارة الطوابير الذكية (SQM)", None),
    "ipv6_enabled": ("bool", "ipv4_ipv6", "IPv6", "بروتوكول IPv6", None),
    "band_steering_enabled": ("bool", "band_steering_roaming", "Band Steering", "توجيه النطاق التلقائي", None),
    "guest_wifi_enabled": ("bool", "guest_wifi", "Guest Wi-Fi", "شبكة الضيوف", None),
    "vlan_id": ("int", "wan_internet", "VLAN ID", "معرف VLAN", "0 (Untagged)"),
    "vlanid": ("int", "wan_internet", "VLAN ID", "معرف VLAN", "0 (Untagged)"),
    "mtu": ("int", "wan_internet", "WAN MTU", "حجم وحدة النقل القصوى (MTU)", "0 (Auto)"),
    "wan_down_mbps": ("float", "wan_internet", "WAN Downstream Rate", "سرعة المزامنة للتنزيل", "0 Mbps"),
    "wan_up_mbps": ("float", "wan_internet", "WAN Upstream Rate", "سرعة المزامنة للرفع", "0 Mbps"),
    "crc_errors": ("int", "access_line_stats", "CRC Errors", "أخطاء CRC", "0"),
    "fec_errors": ("int", "access_line_stats", "FEC Errors", "أخطاء FEC", "0"),
    "uptime_seconds": ("int", "device_info", "System Uptime", "مدة التشغيل المتواصل", "0s"),
    "specmacfilternum": ("int", "mac_filtering", "Max MAC Filter Entries", "الحد الأقصى لتصفية MAC", "0"),
    "userandkey": ("bool", "advanced_stability", "Use Random Backup Key", "استخدام مفتاح عشوائي", None),
    "enablesavekey": ("bool", "advanced_stability", "Save Backup Key", "حفظ مفتاح النسخ الاحتياطي", None),
    "uselastkey": ("bool", "advanced_stability", "Use Last Backup Key", "استخدام آخر مفتاح", None),
    "hidekey": ("bool", "advanced_stability", "Hide Backup Key", "إخفاء مفتاح النسخ", None),
    "enabled": ("bool", "wifi_24", "Radio Enabled", "تفعيل البث اللاسلكي", None),
    "wifi_24_enabled": ("bool", "wifi_24", "2.4 GHz Radio Enabled", "تفعيل بث 2.4 GHz", None),
    "wifi_5_enabled": ("bool", "wifi_5", "5 GHz Radio Enabled", "تفعيل بث 5 GHz", None),
    "wifi_6_enabled": ("bool", "wifi_6", "6 GHz Radio Enabled", "تفعيل بث 6 GHz", None),
    "wlanenable": ("bool", "wifi_24", "WLAN Radio Enabled", "تفعيل الواي فاي", None),
    "radioenable": ("bool", "wifi_24", "Radio Enabled", "تفعيل الراديو", None),
    "wpsenable": ("bool", "ssid_security", "WPS Enabled", "تفعيل WPS", None),
}

_INTERNAL_FORM_OR_SECRET_FLAG_RE = re.compile(
    r"^(?:wifipasswordmask|pwdtipsflag|megacablepwd|noappinflag|pinnote|pinnumber|"
    r".*password.*|.*psk.*|.*wepkey.*|.*passphrase.*|.*tipsflag.*|.*pwdflag.*)$",
    re.IGNORECASE,
)


def is_technical_or_masked_setting(key: str, *, redacted: bool = False) -> bool:
    """Return True for masked credentials or vendor internal HTML form flags."""
    if redacted:
        return True
    k = (key or "").strip()
    leaf = k.split(".")[-1] if "." in k else k
    return bool(_INTERNAL_FORM_OR_SECRET_FLAG_RE.search(k) or _INTERNAL_FORM_OR_SECRET_FLAG_RE.search(leaf))

_TR069_CONTAINER_PREFIXES = ("InternetGatewayDevice.", "Device.", "X_HW_", "X_TP_", "X_ZTE_")


def _extract_tr069_leaf_and_instance(raw_key: str) -> Tuple[str, str, str]:
    """Return (display_key, instance_id, object_path). Preserves multi-instance TR-069 objects."""
    k = (raw_key or "").strip()
    if k.lower().startswith("x="):
        return k, "", ""
    if any(p in k for p in _TR069_CONTAINER_PREFIXES):
        parts = [p for p in k.split(".") if p]
        if len(parts) >= 2:
            leaf = parts[-1]
            inst_tokens: List[str] = []
            for i, seg in enumerate(parts[:-1]):
                if seg.isdigit() and i > 0:
                    inst_tokens.append(f"{parts[i - 1]}.{seg}")
            inst_id = "/".join(inst_tokens)
            return leaf, inst_id, k
    # Bracket/dot indexed non-TR069 object key e.g. "dhcp_pool[1].start_ip" or "LANDevice.2.minaddress"
    m_inst = re.match(r"^([A-Za-z0-9_.\-]+(?:\.\d+|\[\d+\]))\.([A-Za-z0-9_]+)$", k)
    if m_inst and not re.match(r"^(?:2\.4|5|6)\s*GHz$", m_inst.group(1), re.I):
        return m_inst.group(2), m_inst.group(1), k
    return k, "", ""


def _is_raw_tr069_or_noise(key: str, val_str: str) -> bool:
    """Filter UI template noise and raw path stubs while keeping valid zero/false/multi-instance parameters."""
    k = (key or "").strip()
    v = (val_str or "").strip()
    if not k or len(k) <= 1:
        return True
    # Raw `x=...` DOM anchor keys or values that ARE literal TR-069 object path strings (not parameter values)
    if k.lower().startswith("x="):
        return True
    if v.startswith(("InternetGatewayDevice.", "Device.", "x=", "frame_", "/html/", "/asp/", "javascript:")):
        return True
    if _TR069_OR_NOISE_KEY_RE.search(k):
        return True
    # Raw unmapped TR-069 container key with empty/no leaf parameter
    if any(p in k for p in _TR069_CONTAINER_PREFIXES):
        leaf, _, _ = _extract_tr069_leaf_and_instance(k)
        leaf_low = leaf.lower()
        if leaf.isdigit() or leaf_low not in _PARAMETER_DEFINITIONS and not any(
            pat.search(leaf) for pat, _, _, _ in _SETTING_DOMAIN_MAP
        ):
            return True
    return False


def classify_setting_value(
    key: str,
    raw_val: Any,
    *,
    clean_val: str,
    is_redacted: bool = False,
) -> Tuple[SettingValueState, Any, str]:
    """Classify setting value cleanly without ever discarding valid numeric zero or boolean false."""
    if is_redacted:
        return SettingValueState.REDACTED, None, clean_val

    leaf_key, _, _ = _extract_tr069_leaf_and_instance(key)
    pdef = _PARAMETER_DEFINITIONS.get(leaf_key.lower()) or _PARAMETER_DEFINITIONS.get(key.strip().lower())
    if pdef is None and "." in key:
        sub_leaf = key.strip().lower().split(".")[-1]
        pdef = _PARAMETER_DEFINITIONS.get(sub_leaf)
    ptype = pdef[0] if pdef else ("bool" if leaf_key.lower().endswith(("enabled", "enable")) else None)

    if isinstance(raw_val, dict):
        if raw_val.get("parse_error") or raw_val.get("error"):
            return SettingValueState.PARSE_ERROR, None, str(raw_val.get("error") or clean_val or "Parse error")
        if raw_val.get("unsupported") is True:
            return SettingValueState.UNSUPPORTED, None, str(raw_val.get("value") or "Unsupported")
        if raw_val.get("missing") is True:
            return SettingValueState.MISSING, None, ""
        raw_val = raw_val.get("value", "")

    if raw_val is None:
        return SettingValueState.NULL, None, "null"

    s = str(raw_val).strip()
    s_low = s.lower()

    if s_low in ("unsupported", "not supported", "not_supported"):
        return SettingValueState.UNSUPPORTED, None, s
    if s_low in ("parse_error", "error", "invalid_parse"):
        return SettingValueState.PARSE_ERROR, None, s
    if s_low == "missing":
        return SettingValueState.MISSING, None, ""
    if s_low == "null":
        return SettingValueState.NULL, None, "null"
    if s == "":
        return SettingValueState.EMPTY_STRING, "", ""

    if isinstance(raw_val, bool):
        if raw_val is False:
            return SettingValueState.BOOLEAN_FALSE, False, "False"
        return SettingValueState.PRESENT, True, "True"

    if ptype == "bool":
        if s_low in ("false", "0", "off", "disable", "disabled", "no"):
            return SettingValueState.BOOLEAN_FALSE, False, "Disabled (0)" if s == "0" else s
        if s_low in ("true", "1", "on", "enable", "enabled", "yes"):
            return SettingValueState.PRESENT, True, "Enabled (1)" if s == "1" else s

    if isinstance(raw_val, (int, float)) and not isinstance(raw_val, bool):
        if raw_val == 0:
            disp = pdef[4] if (pdef and pdef[4]) else clean_val
            return SettingValueState.NUMERIC_ZERO, 0 if isinstance(raw_val, int) else 0.0, disp
        return SettingValueState.PRESENT, raw_val, clean_val

    if re.fullmatch(r"-?\d+(?:\.\d+)?", s):
        num: Any = int(s) if "." not in s else float(s)
        if num == 0:
            disp = pdef[4] if (pdef and pdef[4]) else s
            return SettingValueState.NUMERIC_ZERO, num, disp
        return SettingValueState.PRESENT, num, s

    if s_low == "false":
        return SettingValueState.BOOLEAN_FALSE, False, clean_val

    return SettingValueState.PRESENT, raw_val, clean_val


def _humanize_key(key: str) -> Tuple[str, str]:
    """Return (english_label, arabic_label) without exposing raw parameter paths."""
    k_low = key.strip().lower()
    if k_low in _FRIENDLY_SETTING_LABELS:
        return _FRIENDLY_SETTING_LABELS[k_low]
    # Handle band-prefixed radio keys like "2.4 GHz.channel"
    if "." in key:
        prefix, sub = key.split(".", 1)
        sub_map = {
            "enabled": (f"{prefix} Radio Enabled", f"حالة بث {prefix}"),
            "ssid": (f"{prefix} SSID", f"اسم شبكة {prefix}"),
            "channel": (f"{prefix} Channel", f"قناة {prefix}"),
            "channel_width": (f"{prefix} Channel Width", f"عرض قناة {prefix}"),
            "tx_power": (f"{prefix} TX Power", f"طاقة بث {prefix}"),
            "security_mode": (f"{prefix} Security", f"أمان وتشفير {prefix}"),
            "mode": (f"{prefix} Wireless Mode", f"وضع بث {prefix}"),
            "band_steering": (f"{prefix} Band Steering", f"توجيه النطاق {prefix}"),
        }
        if sub.lower() in sub_map:
            return sub_map[sub.lower()]
    cleaned = re.sub(r"[_\-.]+", " ", key).strip().title()
    return cleaned, cleaned


class RouterConfigurationParser:
    """Extracts structured, secret-redacted settings from heterogeneous router formats."""

    @staticmethod
    def classify_setting(key: str, fallback_domain: str = "advanced_stability") -> Tuple[str, str, str]:
        """Return (domain_id, label_ar, meaning_ar)."""
        _, friendly_ar = _humanize_key(key)
        for pat, dom, label_ar, meaning in _SETTING_DOMAIN_MAP:
            if pat.search(key or ""):
                # Prefer specific friendly Arabic label when available rather than generic domain header
                use_lbl = friendly_ar if key.strip().lower() in _FRIENDLY_SETTING_LABELS or "." in key else label_ar
                return dom, use_lbl, meaning
        return fallback_domain, friendly_ar or DOMAIN_LABEL_AR.get(fallback_domain, key), "إعداد مستخرج من صفحة إدارة الراوتر."

    @classmethod
    def parse_key_values(
        cls,
        kv: Dict[str, Any],
        *,
        page_name: str,
        section: str,
        submenu: str = "",
        default_domain: str = "advanced_stability",
        configurable: bool = False,
        change_supported: bool = False,
        write_method: Optional[str] = None,
        provenance: MeasurementProvenance = MeasurementProvenance.ROUTER_REPORTED,
    ) -> List[RouterSettingRecord]:
        records: List[RouterSettingRecord] = []
        seen_keys: set[tuple[str, str]] = set()
        for raw_key, raw_val in (kv or {}).items():
            key = str(raw_key).strip()
            if not key:
                continue
            val = raw_val.get("value") if isinstance(raw_val, dict) and "value" in raw_val else raw_val
            clean_val, is_redacted = sanitize_setting_value(key, val)
            if not is_redacted and _is_raw_tr069_or_noise(key, clean_val):
                continue
            disp_key, inst_id, obj_path = _extract_tr069_leaf_and_instance(key)
            dedup_id = (disp_key.lower(), inst_id.lower())
            if dedup_id in seen_keys:
                continue
            seen_keys.add(dedup_id)

            vstate, typed_v, display_val = classify_setting_value(
                key,
                raw_val,
                clean_val=clean_val,
                is_redacted=is_redacted,
            )
            dom, lbl_ar, meaning = cls.classify_setting(disp_key, fallback_domain=default_domain)
            if is_technical_or_masked_setting(disp_key, redacted=is_redacted):
                dom = "advanced_technical"
            lbl_en, _ = _humanize_key(disp_key)
            if inst_id:
                lbl_en = f"{lbl_en} ({inst_id})"
                lbl_ar = f"{lbl_ar} ({inst_id})"
            disabled = bool(raw_val.get("disabled")) if isinstance(raw_val, dict) else False
            records.append(
                RouterSettingRecord(
                    setting_key=disp_key,
                    setting_label=lbl_en,
                    setting_label_ar=lbl_ar,
                    domain=dom,
                    section=section,
                    submenu=submenu,
                    page_name=page_name,
                    current_value=display_val,
                    typed_value=typed_v,
                    value_state=vstate,
                    instance_id=inst_id,
                    object_path=obj_path,
                    redacted=is_redacted,
                    meaning=meaning,
                    configurable=configurable and not disabled and not is_redacted and vstate != SettingValueState.UNSUPPORTED,
                    change_supported=change_supported and not is_redacted and vstate != SettingValueState.UNSUPPORTED,
                    write_method=write_method if change_supported else None,
                    provenance=provenance,
                )
            )
        return records

    @classmethod
    def parse_html_inputs(
        cls,
        html: str,
        *,
        page_name: str,
        section: str,
        submenu: str = "",
        default_domain: str = "advanced_stability",
    ) -> List[RouterSettingRecord]:
        """Extract saved input/select/JS variable values from static HTML when JS DOM isn't needed."""
        extracted: Dict[str, Any] = {}
        if not html:
            return []

        # JS variable assignments: var X = 'val'; (only meaningful router config names, never raw TR-069 or loop indices)
        for m in re.finditer(r"\bvar\s+([A-Za-z_][A-Za-z0-9_]{2,48})\s*=\s*['\"]([^'\"]{0,200})['\"]\s*;", html):
            k, v = m.group(1), m.group(2)
            v = re.sub(r"\\x([0-9a-fA-F]{2})", lambda hx: chr(int(hx.group(1), 16)), v)
            if _is_raw_tr069_or_noise(k, v):
                continue
            # Keep only keys that match a real router setting domain or secret redaction check
            matched_domain = any(pat.search(k) for pat, _, _, _ in _SETTING_DOMAIN_MAP)
            if not matched_domain and not sanitize_setting_value(k, v)[1]:
                continue
            extracted[k] = v

        # HTML inputs
        for m in re.finditer(
            r"<input\b([^>]{1,300})>",
            html,
            re.IGNORECASE | re.DOTALL,
        ):
            attrs = m.group(1)
            t_m = re.search(r"\btype\s*=\s*['\"]?([a-zA-Z]+)", attrs, re.I)
            itype = (t_m.group(1) if t_m else "text").lower()
            if itype in ("button", "submit", "hidden", "image"):
                continue
            n_m = re.search(r"\b(?:name|id)\s*=\s*['\"]([^'\"]+)['\"]", attrs, re.I)
            if not n_m:
                continue
            name = n_m.group(1)
            if itype == "password":
                extracted[name] = "[REDACTED]"
            elif itype in ("checkbox", "radio"):
                checked = bool(re.search(r"\bchecked\b", attrs, re.I))
                if itype == "checkbox" or checked:
                    extracted[name] = checked
            else:
                v_m = re.search(r"\bvalue\s*=\s*['\"]([^'\"]*)['\"]", attrs, re.I)
                if v_m and not _is_raw_tr069_or_noise(name, v_m.group(1)):
                    extracted[name] = v_m.group(1)

        # HTML select with selected option
        for m in re.finditer(
            r"<select\b([^>]{1,200})>(.*?)</select>",
            html,
            re.IGNORECASE | re.DOTALL,
        ):
            attrs, inner = m.group(1), m.group(2)
            n_m = re.search(r"\b(?:name|id)\s*=\s*['\"]([^'\"]+)['\"]", attrs, re.I)
            if not n_m:
                continue
            opt_m = re.search(r"<option[^>]*selected[^>]*value\s*=\s*['\"]([^'\"]*)['\"][^>]*>([^<]*)</option>", inner, re.I)
            if not opt_m:
                opt_m = re.search(r"<option[^>]*selected[^>]*>([^<]*)</option>", inner, re.I)
            if opt_m and not _is_raw_tr069_or_noise(n_m.group(1), opt_m.group(1).strip()):
                extracted[n_m.group(1)] = opt_m.group(1).strip()

        return cls.parse_key_values(
            extracted,
            page_name=page_name,
            section=section,
            submenu=submenu,
            default_domain=default_domain,
            configurable=bool(re.search(r"<form\b", html, re.I)),
            change_supported=False,
        )

    @classmethod
    def inspect_backup_blob(cls, raw_blob: Optional[str]) -> Tuple[bool, str, Dict[str, Any]]:
        """Safely classify whether an exported router backup is readable JSON/XML/INI or encrypted/opaque."""
        if not raw_blob or not raw_blob.strip():
            return False, "No backup file or configuration export was returned by the router.", {}

        stripped = raw_blob.strip()
        if stripped.startswith("{"):
            try:
                parsed = json.loads(stripped)
                return True, "Configuration export is readable JSON (secrets redacted in inspection output).", cls._redact_dict(parsed)
            except Exception:
                pass
        if stripped.startswith("<"):
            try:
                root = ET.fromstring(stripped)
                flat: Dict[str, Any] = {}
                for el in root.iter():
                    tag = el.tag.split("}", 1)[-1]
                    if el.text and el.text.strip():
                        clean, _ = sanitize_setting_value(tag, el.text.strip())
                        flat[tag] = clean
                return True, f"Configuration export is readable XML ({len(flat)} nodes extracted, secrets redacted).", flat
            except Exception:
                pass

        # Binary / encrypted ISP backup header detection (never attempt decryption bypass)
        non_ascii_ratio = sum(1 for ch in stripped[:512] if ord(ch) > 127 or ord(ch) < 9) / max(1, min(512, len(stripped)))
        if non_ascii_ratio > 0.15 or any(sig in stripped[:64] for sig in ("Salted__", "HUAWEI", "ZTECFG", "BIN")):
            return False, "Router backup export appears encrypted/binary by vendor firmware; NetGuard will not bypass encryption.", {}

        return True, "Plain-text configuration export parsed with secret redaction.", {"raw_preview_length": len(stripped)}

    @classmethod
    def _redact_dict(cls, obj: Any) -> Any:
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    out[k] = cls._redact_dict(v)
                else:
                    clean, _ = sanitize_setting_value(str(k), v)
                    out[k] = clean
            return out
        if isinstance(obj, list):
            return [cls._redact_dict(i) for i in obj]
        return obj
