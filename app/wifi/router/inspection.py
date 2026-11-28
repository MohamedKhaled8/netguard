"""Complete Section 2 Router Page Inspection Service & honest 32-domain coverage reporter."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.wifi.models import (
    ConnectedDeviceRecord,
    MeasurementProvenance,
    RouterCapabilities,
    RouterConfigurationSnapshot,
    RouterDiscoveryResult,
)
from app.wifi.router.adapters.base import IRouterAdapter
from app.wifi.router.adapters.snmp_client import SnmpReadOnlyClient
from app.wifi.router.adapters.tr_standards import TrStandardsInspector
from app.wifi.router.adapters.web_dom_inspector import DomInspectionSessionResult
from app.wifi.router.models_config import (
    ROUTER_CONFIG_DOMAINS,
    InspectionCoverageReport,
    InspectionCoverageStatus,
    RouterConfigurationModel,
    RouterPageInspectionRecord,
    RouterSettingRecord,
)
from app.wifi.router.parser import RouterConfigurationParser


_ADAPTER_PAGE_DOMAIN_HINTS: Dict[str, Tuple[str, str, List[str]]] = {
    "device_info": ("System & Status", "Device Info", ["device_info", "firmware_updates"]),
    "wan_info": ("Internet / WAN", "WAN Connection", ["wan_internet", "ipv4_ipv6"]),
    "wan_status": ("Internet / WAN", "WAN Status", ["wan_internet"]),
    "dsl_stats": ("Internet / WAN", "DSL Line Stats", ["access_line_stats"]),
    "optic_stats": ("Internet / WAN", "Fiber Optical Stats", ["access_line_stats"]),
    "lan_dhcp": ("LAN & DHCP", "DHCP Server", ["lan_ip", "dhcp_server"]),
    "dhcp": ("LAN & DHCP", "DHCP Settings", ["lan_ip", "dhcp_server", "dhcp_leases"]),
    "dhcp_server": ("LAN & DHCP", "DHCP Server", ["lan_ip", "dhcp_server"]),
    "dhcp_leases": ("LAN & DHCP", "DHCP Leases", ["dhcp_leases"]),
    "dns": ("LAN & DNS", "DNS Servers", ["dns"]),
    "dns_config": ("LAN & DNS", "DNS Configuration", ["dns"]),
    "wlan_basic": ("Wireless", "Wi-Fi Settings", ["wifi_24", "wifi_5", "ssid_security", "channel_width"]),
    "wlan_24": ("Wireless", "Wi-Fi 2.4 GHz", ["wifi_24", "ssid_security", "channel_width"]),
    "wlan_5": ("Wireless", "Wi-Fi 5 GHz", ["wifi_5", "ssid_security", "channel_width"]),
    "wlan_info": ("Wireless", "Radio Status", ["tx_power_radio", "wmm"]),
    "wireless": ("Wireless", "Wireless Interfaces", ["wifi_24", "wifi_5", "channel_width", "tx_power_radio"]),
    "wifi": ("Wireless", "Wi-Fi Wave2/AX", ["wifi_24", "wifi_5", "wifi_6", "channel_width"]),
    "wlan_hosts": ("Connected Devices", "Wireless Clients", ["wireless_clients"]),
    "connected_devices": ("Connected Devices", "Client Table", ["wireless_clients", "wired_clients"]),
    "qos": ("Traffic Control & QoS", "QoS", ["qos_priority", "bandwidth_control", "queue_shaping"]),
    "qos_config": ("Traffic Control & QoS", "QoS Configuration", ["qos_priority", "bandwidth_control", "queue_shaping"]),
    "queues": ("Traffic Control & QoS", "Simple Queues / Shaping", ["queue_shaping", "bandwidth_control"]),
    "firewall": ("Security & Firewall", "Firewall", ["firewall", "ipv6_firewall"]),
    "firewall_config": ("Security & Firewall", "Firewall Level", ["firewall"]),
    "firewall_filter": ("Security & Firewall", "Packet Filter", ["firewall", "ipv6_firewall"]),
    "firewall_nat": ("Security & NAT", "NAT Rules", ["nat_port_forwarding"]),
    "upnp": ("Security & UPnP", "UPnP", ["upnp"]),
    "upnp_config": ("Security & UPnP", "UPnP", ["upnp"]),
    "port_mapping": ("Security & NAT", "Port Forwarding", ["nat_port_forwarding"]),
    "mac_filter": ("Security & Access", "MAC Filtering", ["mac_filtering"]),
    "parental_ctrl": ("Security & Access", "Parental Controls", ["parental_controls"]),
    "system_logs": ("System & Logs", "System Logs", ["system_logs"]),
    "logs": ("System & Logs", "Router Logs", ["system_logs"]),
    "backup_cfg": ("Maintenance", "Configuration Backup", ["advanced_stability"]),
}


class RouterPageInspectionService:
    """Executes structured post-auth inspection across ALL accessible pages, menus, APIs, SNMP, and UPnP."""

    def inspect(
        self,
        *,
        adapter: IRouterAdapter,
        discovery: Optional[RouterDiscoveryResult] = None,
        snapshot: Optional[RouterConfigurationSnapshot] = None,
        devices: Optional[List[ConnectedDeviceRecord]] = None,
        dom_result: Optional[DomInspectionSessionResult] = None,
        snmp_snapshot: Optional[Any] = None,
        standards_result: Optional[Any] = None,
    ) -> RouterConfigurationModel:
        caps = adapter.capabilities()
        snap = snapshot
        if snap is None and adapter.is_authenticated:
            snap = adapter.read_config()
        if snap is None:
            snap = RouterConfigurationSnapshot(
                adapter_id=adapter.adapter_id,
                vendor=(discovery.hardware_vendor or discovery.detected_vendor) if discovery else adapter.vendor_family,
                isp_brand=discovery.isp_brand if discovery else None,
                model=discovery.detected_model if discovery else None,
                firmware_version=discovery.firmware_version if discovery else None,
            )

        dev_list = list(devices or [])
        if not dev_list and adapter.is_authenticated and caps.supports_connected_devices_read:
            try:
                dev_list = adapter.get_connected_devices()
            except Exception:
                dev_list = []

        pages: List[RouterPageInspectionRecord] = []
        all_settings: List[RouterSettingRecord] = []
        secrets_redacted = 0
        domains_map: Dict[str, Dict[str, Any]] = {}

        # 1) Core adapter read_config normalized into core domains
        core_settings: List[RouterSettingRecord] = []
        core_kv: Dict[str, Any] = {
            "vendor": snap.vendor,
            "isp_brand": snap.isp_brand,
            "model": snap.model,
            "firmware_version": snap.firmware_version,
            "uptime_seconds": snap.uptime_seconds,
            "wan_status": snap.wan_status,
            "wan_connection_type": snap.wan_connection_type,
            "wan_ip": snap.wan_ip,
            "wan_down_mbps": snap.wan_down_mbps,
            "wan_up_mbps": snap.wan_up_mbps,
            "lan_ip": snap.lan_ip,
            "lan_subnet_mask": snap.lan_subnet_mask,
            "dhcp_enabled": snap.dhcp_enabled,
            "dhcp_pool_start": snap.dhcp_pool_start,
            "dhcp_pool_end": snap.dhcp_pool_end,
            "dhcp_lease_time_sec": snap.dhcp_lease_time_sec,
            "dns_servers": ", ".join(snap.dns_servers) if snap.dns_servers else None,
            "qos_enabled": snap.qos_enabled,
            "qos_mode": snap.qos_mode,
            "sqm_enabled": snap.sqm_enabled,
            "upnp_enabled": snap.upnp_enabled,
            "firewall_level": snap.firewall_level,
            "ipv6_enabled": snap.ipv6_enabled,
            "band_steering_enabled": snap.band_steering_enabled,
            "guest_wifi_enabled": snap.guest_wifi_enabled,
        }
        core_kv = {k: v for k, v in core_kv.items() if v is not None}
        core_settings.extend(
            RouterConfigurationParser.parse_key_values(
                core_kv,
                page_name="Core Adapter Summary",
                section="Adapter API",
                submenu="Status & Core Settings",
                configurable=bool(caps.supports_wifi_write or caps.supports_dns_config_write or caps.supports_sqm_or_qos_write),
                change_supported=bool(caps.supports_channel_write or caps.supports_dns_config_write or caps.supports_sqm_or_qos_write),
                write_method=adapter.adapter_id,
            )
        )
        for band, radio in snap.radios.items():
            dom = "wifi_5" if "5" in band else ("wifi_6" if "6" in band else "wifi_24")
            r_kv = {
                f"{band}.enabled": radio.enabled,
                f"{band}.ssid": radio.ssid,
                f"{band}.channel": radio.channel,
                f"{band}.channel_width": radio.channel_width,
                f"{band}.tx_power": radio.tx_power,
                f"{band}.security_mode": radio.security_mode,
                f"{band}.mode": radio.mode,
                f"{band}.band_steering": radio.band_steering_enabled,
            }
            r_kv = {k: v for k, v in r_kv.items() if v is not None}
            core_settings.extend(
                RouterConfigurationParser.parse_key_values(
                    r_kv,
                    page_name=f"Radio {band}",
                    section="Wireless",
                    submenu=band,
                    default_domain=dom,
                    configurable=True,
                    change_supported=bool(caps.supports_channel_write or caps.supports_width_write),
                    write_method=adapter.adapter_id,
                )
            )
        for inst in snap.extra_sections.get("dhcp_instances", []) if isinstance(snap.extra_sections, dict) else []:
            if not isinstance(inst, dict):
                continue
            inst_tag = str(inst.get("instance") or inst.get("domain") or "DHCPPool").strip()
            d_kv = {
                f"{inst_tag}.dhcp_enabled": inst.get("enabled"),
                f"{inst_tag}.dhcp_pool_start": inst.get("pool_start"),
                f"{inst_tag}.dhcp_pool_end": inst.get("pool_end"),
                f"{inst_tag}.dhcp_lease_time_sec": inst.get("lease_time_sec"),
            }
            core_settings.extend(
                RouterConfigurationParser.parse_key_values(
                    d_kv,
                    page_name="LAN & DHCP Pools",
                    section="LAN & DHCP",
                    submenu=inst_tag,
                    default_domain="dhcp_server",
                )
            )
        if core_settings:
            pages.append(
                RouterPageInspectionRecord(
                    page_id="adapter_core",
                    page_name="Core Router Configuration Summary",
                    section="Authenticated Adapter Read",
                    submenu="Summary",
                    url_or_path=discovery.preferred_url if discovery and discovery.preferred_url else "",
                    domains_covered=sorted({s.domain for s in core_settings}),
                    accessed=adapter.is_authenticated or bool(core_settings),
                    values_extracted=bool(core_settings),
                    coverage_status=InspectionCoverageStatus.FULLY_INSPECTED if adapter.is_authenticated else InspectionCoverageStatus.PARTIALLY_INSPECTED,
                    change_capability=(
                        InspectionCoverageStatus.CONFIGURATION_CHANGE_SUPPORTED
                        if (caps.supports_channel_write or caps.supports_dns_config_write or caps.supports_sqm_or_qos_write)
                        else InspectionCoverageStatus.READ_ONLY
                    ),
                    settings_count=len(core_settings),
                    settings=core_settings,
                )
            )
            all_settings.extend(core_settings)

        # 2) Multi-page inspection across adapter pages if implemented
        raw_pages: Dict[str, Any] = {}
        if hasattr(adapter, "inspect_all_pages") and adapter.is_authenticated:
            try:
                raw_pages = adapter.inspect_all_pages() or {}
            except Exception:
                raw_pages = {}

        system_logs: List[str] = []
        for page_key, payload in raw_pages.items():
            if not isinstance(payload, dict):
                continue
            sec, sub, doms = _ADAPTER_PAGE_DOMAIN_HINTS.get(
                page_key, ("Advanced / Discovered", page_key, ["advanced_stability"])
            )
            ok = bool(payload.get("ok"))
            status_code = payload.get("status")
            path = str(payload.get("path") or "")
            p_settings: List[RouterSettingRecord] = []
            if ok:
                jdata = payload.get("json")
                body = str(payload.get("body") or "")
                if isinstance(jdata, dict):
                    p_settings.extend(
                        RouterConfigurationParser.parse_key_values(
                            jdata,
                            page_name=sub,
                            section=sec,
                            submenu=page_key,
                            default_domain=doms[0],
                        )
                    )
                elif isinstance(jdata, list) and page_key in ("logs", "system_logs"):
                    for row in jdata[:40]:
                        system_logs.append(str(row))
                if body and "<" in body:
                    p_settings.extend(
                        RouterConfigurationParser.parse_html_inputs(
                            body,
                            page_name=sub,
                            section=sec,
                            submenu=page_key,
                            default_domain=doms[0],
                        )
                    )
            cov = (
                InspectionCoverageStatus.FULLY_INSPECTED
                if ok and p_settings
                else (
                    InspectionCoverageStatus.PARTIALLY_INSPECTED
                    if ok
                    else (
                        InspectionCoverageStatus.NOT_SUPPORTED
                        if status_code == 404
                        else InspectionCoverageStatus.NOT_ACCESSIBLE
                    )
                )
            )
            chg = InspectionCoverageStatus.READ_ONLY
            if "channel_width" in doms and caps.supports_channel_write:
                chg = InspectionCoverageStatus.CONFIGURATION_CHANGE_SUPPORTED
            elif "dns" in doms and caps.supports_dns_config_write:
                chg = InspectionCoverageStatus.CONFIGURATION_CHANGE_SUPPORTED
            elif "qos_priority" in doms and caps.supports_sqm_or_qos_write:
                chg = InspectionCoverageStatus.CONFIGURATION_CHANGE_SUPPORTED

            pages.append(
                RouterPageInspectionRecord(
                    page_id=f"page_{page_key}",
                    page_name=sub,
                    section=sec,
                    submenu=page_key,
                    url_or_path=path,
                    domains_covered=doms,
                    accessed=ok,
                    values_extracted=bool(p_settings),
                    coverage_status=cov,
                    change_capability=chg,
                    error_or_reason="" if ok else f"HTTP {status_code or 'error'}: endpoint unavailable or requires interactive DOM session.",
                    settings_count=len(p_settings),
                    settings=p_settings,
                )
            )
            all_settings.extend(p_settings)

        # 3) Web Admin DOM extracted pages (if QtWebEngine inspection ran)
        if dom_result is not None and dom_result.pages:
            for idx, dpage in enumerate(dom_result.pages):
                d_settings = RouterConfigurationParser.parse_key_values(
                    dpage.fields,
                    page_name=dpage.title or f"DOM Page {idx+1}",
                    section=dpage.section or "Web Admin DOM",
                    submenu=dpage.submenu or "",
                    configurable=True,
                    change_supported=False,
                )
                pages.append(
                    RouterPageInspectionRecord(
                        page_id=f"dom_{idx}",
                        page_name=dpage.title or f"Web Page {idx+1}",
                        section=dpage.section or "Web Admin DOM",
                        submenu=dpage.submenu or "",
                        url_or_path=dpage.url,
                        domains_covered=sorted({s.domain for s in d_settings}),
                        accessed=(dpage.error is None),
                        values_extracted=bool(d_settings),
                        coverage_status=(
                            InspectionCoverageStatus.FULLY_INSPECTED
                            if d_settings
                            else InspectionCoverageStatus.PARTIALLY_INSPECTED
                        ),
                        change_capability=InspectionCoverageStatus.READ_ONLY,
                        error_or_reason=dpage.error or "",
                        settings_count=len(d_settings),
                        settings=d_settings,
                    )
                )
                all_settings.extend(d_settings)

        # 4) SNMP & UPnP standards enrichment (read-only)
        if snmp_snapshot is not None and getattr(snmp_snapshot, "reachable", False):
            s_kv = {
                "snmp_sys_descr": snmp_snapshot.sys_descr,
                "snmp_sys_name": snmp_snapshot.sys_name,
                "snmp_interfaces_count": len(snmp_snapshot.interfaces),
            }
            s_kv = {k: v for k, v in s_kv.items() if v is not None}
            s_settings = RouterConfigurationParser.parse_key_values(
                s_kv,
                page_name="SNMPv2c MIB-2",
                section="Standards Protocol",
                submenu="SNMP Read-Only",
                default_domain="device_info",
                provenance=MeasurementProvenance.ROUTER_REPORTED,
            )
            pages.append(
                RouterPageInspectionRecord(
                    page_id="snmp_mib2",
                    page_name="SNMPv2c Read-Only MIB-2",
                    section="Standards Protocol",
                    submenu="UDP/161",
                    domains_covered=["device_info", "access_line_stats"],
                    accessed=True,
                    values_extracted=bool(s_settings),
                    coverage_status=InspectionCoverageStatus.PARTIALLY_INSPECTED,
                    change_capability=InspectionCoverageStatus.READ_ONLY,
                    settings_count=len(s_settings),
                    settings=s_settings,
                )
            )
            all_settings.extend(s_settings)

        if standards_result is not None and getattr(standards_result, "upnp_igd_reachable", False):
            u_kv = {
                "upnp_wan_external_ip": standards_result.wan_external_ip,
                "upnp_wan_status": standards_result.wan_connection_status,
                "upnp_wan_access_type": standards_result.access_type,
                "upnp_wan_down_max_bps": standards_result.wan_down_max_bps,
                "upnp_wan_up_max_bps": standards_result.wan_up_max_bps,
            }
            u_kv = {k: v for k, v in u_kv.items() if v is not None}
            u_settings = RouterConfigurationParser.parse_key_values(
                u_kv,
                page_name="UPnP IGD / TR-064",
                section="Standards Protocol",
                submenu="SOAP",
                default_domain="wan_internet",
            )
            pages.append(
                RouterPageInspectionRecord(
                    page_id="upnp_tr064",
                    page_name="UPnP IGD / TR-064",
                    section="Standards Protocol",
                    submenu="SOAP",
                    domains_covered=["wan_internet", "access_line_stats", "upnp"],
                    accessed=True,
                    values_extracted=bool(u_settings),
                    coverage_status=InspectionCoverageStatus.PARTIALLY_INSPECTED,
                    change_capability=InspectionCoverageStatus.READ_ONLY,
                    settings_count=len(u_settings),
                    settings=u_settings,
                )
            )
            all_settings.extend(u_settings)

        # Deduplicate extracted settings across core & pages while preserving distinct instances (e.g. multiple DHCP pools)
        deduped_settings: List[RouterSettingRecord] = []
        seen_setting_keys: set[tuple[str, str, str]] = set()
        for s in all_settings:
            inst_norm = (getattr(s, "instance_id", "") or "").strip().lower()
            norm_k = (s.domain, s.setting_key.strip().lower(), inst_norm)
            if norm_k in seen_setting_keys:
                continue
            seen_setting_keys.add(norm_k)
            deduped_settings.append(s)
            if s.redacted:
                secrets_redacted += 1
            map_key = f"{s.instance_id}.{s.setting_key}" if inst_norm else s.setting_key
            domains_map.setdefault(s.domain, {})[map_key] = s.current_value
        all_settings = deduped_settings

        domains_inspected = sorted(domains_map.keys())
        domains_missing = [d[0] for d in ROUTER_CONFIG_DOMAINS if d[0] not in domains_map]

        backup_readable, backup_note, _ = RouterConfigurationParser.inspect_backup_blob(snap.raw_backup_blob)

        fully = sum(1 for p in pages if p.coverage_status == InspectionCoverageStatus.FULLY_INSPECTED)
        partial = sum(1 for p in pages if p.coverage_status == InspectionCoverageStatus.PARTIALLY_INSPECTED)
        not_acc = sum(1 for p in pages if p.coverage_status == InspectionCoverageStatus.NOT_ACCESSIBLE)
        not_sup = sum(1 for p in pages if p.coverage_status == InspectionCoverageStatus.NOT_SUPPORTED)
        ro_pages = sum(1 for p in pages if p.change_capability == InspectionCoverageStatus.READ_ONLY)
        chg_pages = sum(1 for p in pages if p.change_capability == InspectionCoverageStatus.CONFIGURATION_CHANGE_SUPPORTED)

        if not adapter.is_authenticated and not all_settings:
            honesty = (
                "لم يتم تسجيل الدخول المصادق للراوتر بعد؛ تم الاعتماد فقط على الاكتشاف السلبي وبروتوكولات القراءة المتاحة "
                "ولا يمكن ادعاء فحص إعدادات الراوتر الداخلية بالكامل."
            )
        elif domains_missing or not_acc or not_sup:
            honesty = (
                f"تم فحص {len(domains_inspected)} من أصل {len(ROUTER_CONFIG_DOMAINS)} مجالاً في الراوتر "
                f"({len(all_settings)} إعداداً). لا تزال {len(domains_missing)} مجالات غير متاحة أو مقيدة بواسطة هذا الموديل/البرنامج الثابت."
            )
        else:
            honesty = (
                f"تم فحص جميع المجالات المدعومة على هذا الراوتر ({len(domains_inspected)}/{len(ROUTER_CONFIG_DOMAINS)} مجالاً، "
                f"{len(all_settings)} إعداداً) مع إخفاء الأسرار وكلمات المرور."
            )

        coverage = InspectionCoverageReport(
            adapter_id=adapter.adapter_id,
            total_pages_discovered=len(pages),
            fully_inspected_pages=fully,
            partially_inspected_pages=partial,
            not_accessible_pages=not_acc,
            not_supported_pages=not_sup,
            read_only_pages=ro_pages,
            change_supported_pages=chg_pages,
            total_settings_extracted=len(all_settings),
            domains_inspected=domains_inspected,
            domains_missing=domains_missing,
            pages=pages,
            backup_export_checked=bool(snap.raw_backup_blob or caps.supports_backup_export),
            backup_readable=backup_readable,
            backup_note=backup_note,
            secrets_redacted_count=secrets_redacted,
            honesty_statement=honesty,
        )

        # Update capabilities strictly from what was verified
        verified_ops: List[str] = []
        unverified_ops: List[str] = []
        if adapter.is_authenticated:
            verified_ops.append("session_auth")
        else:
            unverified_ops.append("session_auth")
        if snap.radios:
            verified_ops.append("read_wifi_radios")
        else:
            unverified_ops.append("read_wifi_radios")
        if dev_list:
            verified_ops.append("read_connected_devices")
        else:
            unverified_ops.append("read_connected_devices")
        if snap.dns_servers:
            verified_ops.append("read_dns")
        if snap.wan_status or snap.wan_ip:
            verified_ops.append("read_wan")
        if snap.qos_enabled is not None:
            verified_ops.append("read_qos")

        updated_caps = caps.model_copy(
            update={
                "hardware_verified": bool(adapter.is_authenticated and (snap.radios or all_settings)),
                "verified_operations": verified_ops,
                "unverified_operations": unverified_ops,
            }
        )

        return RouterConfigurationModel(
            discovery=discovery,
            capabilities=updated_caps,
            snapshot=snap,
            devices=dev_list,
            domains=domains_map,
            settings=all_settings,
            coverage=coverage,
            system_logs=system_logs,
            raw_sections_sanitized=RouterConfigurationParser._redact_dict(snap.extra_sections),
        )
