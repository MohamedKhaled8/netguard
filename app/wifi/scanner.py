"""Nearby Wi-Fi Access Point scanner using Windows Native Wifi BSS lists and 802.11 IEs."""

from __future__ import annotations

import asyncio
import re
import subprocess
import sys
from collections import defaultdict
from typing import Dict, List, Optional

from app.wifi.coordinator import DiagnosticCoordinator
from app.wifi.models import (
    AccessPointScanResult,
    MeasurementProvenance,
    NeighborAccessPoint,
    utc_now,
)
from app.wifi.telemetry import (
    Parsed80211IEs,
    RawNativeWlanBss,
    channel_to_center_freq_mhz,
    query_native_wlan,
)


def parse_netsh_networks_output(output: str) -> List[RawNativeWlanBss]:
    """Parse `netsh wlan show networks mode=bssid` output into RawNativeWlanBss entries."""
    entries: List[RawNativeWlanBss] = []
    if not output:
        return entries

    cur_ssid = ""
    cur_hidden = False
    cur_auth: Optional[str] = None
    cur_cipher: Optional[str] = None
    cur_bss: Optional[Dict[str, str]] = None

    def _flush_bss() -> None:
        nonlocal cur_bss
        if not cur_bss or not cur_bss.get("bssid"):
            cur_bss = None
            return
        bssid = cur_bss["bssid"].strip().lower()
        pct_str = cur_bss.get("signal_pct", "")
        try:
            pct = int(pct_str)
        except ValueError:
            pct = 0
        rssi = int(round((pct / 2.0) - 100.0)) if pct > 0 else -95
        try:
            ch = int(cur_bss.get("channel", "0"))
        except ValueError:
            ch = 0
        band = cur_bss.get("band", "").strip()
        if not band and ch > 0:
            band = "2.4 GHz" if ch <= 14 else "5 GHz"
        freq_mhz = channel_to_center_freq_mhz(band, ch) if (band and ch > 0) else 0
        phy = cur_bss.get("radio_type", "").strip() or None
        sec = cur_auth
        if cur_auth and cur_cipher:
            sec = f"{cur_auth} ({cur_cipher})"
        ies = Parsed80211IEs(
            ssid=cur_ssid or None,
            is_hidden_ssid=cur_hidden,
            security_mode=sec,
            inferred_phy_standard=phy,
        )
        entries.append(
            RawNativeWlanBss(
                ssid=cur_ssid,
                is_hidden=cur_hidden,
                bssid=bssid,
                band=band or "unknown",
                channel=ch,
                center_frequency_mhz=freq_mhz,
                rssi_dbm=rssi,
                signal_quality_pct=pct,
                phy_standard=phy,
                in_reg_domain=True,
                last_seen_timestamp=0,
                parsed_ies=ies,
            )
        )
        cur_bss = None

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m_ssid = re.match(r"^SSID\s+\d+\s*:\s*(.*)$", line, re.IGNORECASE)
        if m_ssid:
            _flush_bss()
            cur_ssid = m_ssid.group(1).strip()
            cur_hidden = cur_ssid == ""
            cur_auth = None
            cur_cipher = None
            continue
        m_auth = re.match(r"^Authentication\s*:\s*(.+)$", line, re.IGNORECASE)
        if m_auth and cur_bss is None:
            cur_auth = m_auth.group(1).strip()
            continue
        m_enc = re.match(r"^Encryption\s*:\s*(.+)$", line, re.IGNORECASE)
        if m_enc and cur_bss is None:
            cur_cipher = m_enc.group(1).strip()
            continue
        m_bssid = re.match(r"^BSSID\s+\d+\s*:\s*([0-9a-fA-F:]{17})$", line, re.IGNORECASE)
        if m_bssid:
            _flush_bss()
            cur_bss = {"bssid": m_bssid.group(1).strip().lower()}
            continue
        if cur_bss is not None:
            if m_sig := re.match(r"^Signal\s*:\s*(\d+)%", line, re.IGNORECASE):
                cur_bss["signal_pct"] = m_sig.group(1)
            elif m_rad := re.match(r"^Radio type\s*:\s*(.+)$", line, re.IGNORECASE):
                cur_bss["radio_type"] = m_rad.group(1).strip()
            elif m_band := re.match(r"^Band\s*:\s*(.+)$", line, re.IGNORECASE):
                cur_bss["band"] = m_band.group(1).strip()
            elif m_ch := re.match(r"^Channel\s*:\s*(\d+)", line, re.IGNORECASE):
                cur_bss["channel"] = m_ch.group(1)

    _flush_bss()
    return entries


def _query_netsh_bss_entries() -> List[RawNativeWlanBss]:
    if sys.platform != "win32":
        return []
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        proc = subprocess.run(
            ["netsh", "wlan", "show", "networks", "mode=bssid"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3.0,
            startupinfo=si,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if proc.returncode == 0 and proc.stdout:
            return parse_netsh_networks_output(proc.stdout)
    except Exception:
        pass
    return []


def _country_to_reg_domain(country_code: Optional[str]) -> str:
    if not country_code:
        return "EG"
    cc = country_code.upper()
    if cc in {"US", "CA", "MX", "PR"}:
        return "US"
    if cc == "JP":
        return "JP"
    return cc


class AccessPointScanner:
    """Enumerates neighboring access points across bands and channels safely."""

    def __init__(self, coordinator: Optional[DiagnosticCoordinator] = None) -> None:
        self._coordinator = coordinator

    @staticmethod
    def build_scan_result_from_bss_list(
        bss_entries: List[RawNativeWlanBss],
        *,
        interface_name: Optional[str] = None,
        connected_bssid: Optional[str] = None,
        scan_mode: str = "cached_bss_list",
        deferred_reason: Optional[str] = None,
        extra_notes: Optional[List[str]] = None,
    ) -> AccessPointScanResult:
        """Convert raw native BSS entries into grouped NeighborAccessPoint structures."""
        aps: List[NeighborAccessPoint] = []
        grouped: Dict[str, Dict[int, List[NeighborAccessPoint]]] = defaultdict(
            lambda: defaultdict(list)
        )
        detected_countries: List[str] = []

        for bss in bss_entries:
            ies = bss.parsed_ies
            if ies.country_code:
                detected_countries.append(ies.country_code)

            width = ies.inferred_width_mhz
            width_prov = (
                MeasurementProvenance.INFERRED
                if width is not None
                else MeasurementProvenance.UNAVAILABLE
            )
            is_connected = bool(connected_bssid and bss.bssid == connected_bssid)

            ap = NeighborAccessPoint(
                ssid=bss.ssid,
                is_hidden=bss.is_hidden,
                bssid=bss.bssid,
                band=bss.band,
                channel=bss.channel,
                center_frequency_mhz=bss.center_frequency_mhz,
                channel_width_mhz=width,
                channel_width_provenance=width_prov,
                secondary_channel_offset=ies.ht_secondary_offset,
                center_freq_seg0_channel=ies.vht_center_seg0,
                rssi_dbm=bss.rssi_dbm,
                signal_quality_pct=bss.signal_quality_pct,
                security_mode=ies.security_mode,
                phy_standard=bss.phy_standard,
                supported_phys=[p for p in [bss.phy_standard] if p],
                max_spatial_streams=ies.max_spatial_streams,
                in_reg_domain=bss.in_reg_domain,
                country_code=ies.country_code,
                qbss_utilization_pct=ies.qbss_utilization_pct,
                qbss_station_count=ies.qbss_station_count,
                is_connected_ap=is_connected,
                last_seen_timestamp=bss.last_seen_timestamp,
            )
            aps.append(ap)
            if ap.band != "unknown" and ap.channel > 0:
                grouped[ap.band][ap.channel].append(ap)

        # Sort APs strongest-first (less negative dBm first)
        aps.sort(key=lambda a: a.rssi_dbm if a.rssi_dbm is not None else -120, reverse=True)
        grouped_sorted: Dict[str, Dict[int, List[NeighborAccessPoint]]] = {}
        for band in ("2.4 GHz", "5 GHz", "6 GHz"):
            if band in grouped:
                grouped_sorted[band] = {
                    ch: sorted(
                        ch_aps,
                        key=lambda a: a.rssi_dbm if a.rssi_dbm is not None else -120,
                        reverse=True,
                    )
                    for ch, ch_aps in sorted(grouped[band].items())
                }

        reg_domain = _country_to_reg_domain(detected_countries[0] if detected_countries else None)
        notes = list(extra_notes or [])
        if deferred_reason:
            notes.append(deferred_reason)
        if not aps:
            notes.append(
                "No neighboring BSS entries were returned by Windows WLAN cache. Location permission or adapter scan may be needed."
            )

        return AccessPointScanResult(
            captured_at=utc_now(),
            interface_name=interface_name,
            scan_mode=scan_mode,  # type: ignore[arg-type]
            active_scan_deferred_reason=deferred_reason,
            regulatory_domain=reg_domain,
            total_bss_count=len(aps),
            access_points=aps,
            grouped_by_band_channel=grouped_sorted,
            scan_notes=notes,
        )

    def scan_sync(self, *, request_active_scan: bool = False) -> AccessPointScanResult:
        """Scan nearby APs; active WlanScan is skipped/deferred during meetings or heavy tests."""
        deferred_reason: Optional[str] = None
        do_active = request_active_scan
        scan_mode = "active_wlan_scan" if request_active_scan else "cached_bss_list"

        if request_active_scan and self._coordinator is not None:
            allowed, reason = self._coordinator.check_operation_allowed("active_wlan_scan")
            if not allowed:
                do_active = False
                scan_mode = "cached_bss_list"
                deferred_reason = (
                    f"Active WlanScan deferred to protect live session ({reason}); using cached BSS table."
                )

        native = query_native_wlan(trigger_active_scan=do_active)
        merged_bss = list(native.bss_entries)
        # Merge additional BSSIDs visible to Windows WLAN AutoConfig (`netsh wlan show networks mode=bssid`)
        # Only when running against the real Windows collector (keep unit-test monkeypatches isolated).
        if sys.platform == "win32" and getattr(query_native_wlan, "__module__", "") == "app.wifi.telemetry":
            netsh_bss = _query_netsh_bss_entries()
            if netsh_bss:
                by_bssid = {b.bssid.lower(): b for b in merged_bss if b.bssid}
                for nb in netsh_bss:
                    key = nb.bssid.lower()
                    if key in by_bssid:
                        existing = by_bssid[key]
                        if (not existing.ssid or existing.is_hidden) and nb.ssid:
                            existing.ssid = nb.ssid
                            existing.is_hidden = False
                        if existing.band == "unknown" and nb.band != "unknown":
                            existing.band = nb.band
                        if existing.channel <= 0 and nb.channel > 0:
                            existing.channel = nb.channel
                            existing.center_frequency_mhz = nb.center_frequency_mhz
                    else:
                        merged_bss.append(nb)
                        by_bssid[key] = nb

        return self.build_scan_result_from_bss_list(
            merged_bss,
            interface_name=native.interface_description,
            connected_bssid=native.bssid,
            scan_mode=scan_mode,
            deferred_reason=deferred_reason,
            extra_notes=native.notes,
        )

    async def scan(self, *, request_active_scan: bool = False) -> AccessPointScanResult:
        return await asyncio.to_thread(self.scan_sync, request_active_scan=request_active_scan)
