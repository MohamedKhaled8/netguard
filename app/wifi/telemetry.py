"""Real Windows Wi-Fi telemetry, 802.11 IE parser, statistics, capabilities, and roam tracking."""

from __future__ import annotations

import asyncio
import ctypes
import json
import re
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Tuple

from app.wifi.models import (
    AdapterCapabilities,
    InterfaceStatsSnapshot,
    MeasurementProvenance,
    RoamingEventRecord,
    WifiInterfaceTelemetry,
    WlanEventRecord,
    utc_now,
)

# ---------------------------------------------------------------------------
# Constants and IEEE 802.11 mappings
# ---------------------------------------------------------------------------

DOT11_PHY_TYPE_MAP: Dict[int, str] = {
    1: "802.11fhss",
    2: "802.11dsss",
    3: "802.11ir",
    4: "802.11a",
    5: "802.11b",
    6: "802.11g",
    7: "802.11n",
    8: "802.11ac",
    9: "802.11ad",
    10: "802.11ax",
    11: "802.11be",
}

DOT11_AUTH_ALGO_MAP: Dict[int, str] = {
    1: "Open",
    2: "Shared Key",
    3: "WPA-Enterprise",
    4: "WPA-PSK",
    5: "WPA-None",
    6: "WPA2-Enterprise",
    7: "WPA2-PSK",
    8: "WPA3-Enterprise-192",
    9: "WPA3-SAE",
    10: "OWE",
    11: "WPA3-Enterprise",
}

DOT11_CIPHER_ALGO_MAP: Dict[int, str] = {
    0: "None",
    1: "WEP-40",
    2: "TKIP",
    4: "AES-CCMP",
    5: "WEP-104",
    6: "BIP",
    8: "GCMP",
    9: "GCMP-256",
    10: "CCMP-256",
}

WLAN_INTERFACE_STATE_MAP: Dict[int, str] = {
    0: "not_ready",
    1: "connected",
    2: "ad_hoc_formed",
    3: "disconnecting",
    4: "disconnected",
    5: "associating",
    6: "discovering",
    7: "authenticating",
}

WLAN_OPCODE_RADIO_STATE = 0x4
WLAN_OPCODE_CURRENT_CONNECTION = 0x7
WLAN_OPCODE_CHANNEL_NUMBER = 0x8
WLAN_OPCODE_STATISTICS = 0x10000101
WLAN_OPCODE_RSSI = 0x10000102


def _subprocess_kwargs() -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {}
    if sys.platform == "win32":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        kwargs["startupinfo"] = si
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return kwargs


def freq_khz_to_band_and_channel(freq_khz: int) -> Tuple[str, int, int]:
    """Convert 802.11 center frequency in kHz to (band_label, channel, freq_mhz)."""
    if freq_khz <= 0:
        return "unknown", 0, 0
    freq_mhz = int(round(freq_khz / 1000.0))
    return freq_mhz_to_band_and_channel(freq_mhz)


def freq_mhz_to_band_and_channel(freq_mhz: int) -> Tuple[str, int, int]:
    """Convert 802.11 center frequency in MHz to (band_label, channel, freq_mhz)."""
    if 2400 <= freq_mhz <= 2500:
        if freq_mhz == 2484:
            return "2.4 GHz", 14, freq_mhz
        channel = int(round((freq_mhz - 2407) / 5.0))
        return "2.4 GHz", max(1, channel), freq_mhz
    if 5150 <= freq_mhz <= 5925:
        channel = int(round((freq_mhz - 5000) / 5.0))
        return "5 GHz", channel, freq_mhz
    if 5925 < freq_mhz <= 7125:
        if freq_mhz == 5935:
            return "6 GHz", 2, freq_mhz
        channel = int(round((freq_mhz - 5950) / 5.0))
        return "6 GHz", channel, freq_mhz
    return "unknown", 0, freq_mhz


def channel_to_center_freq_mhz(band: str, channel: int) -> int:
    """Convert (band, channel) to IEEE 802.11 center frequency in MHz."""
    if band == "2.4 GHz":
        return 2484 if channel == 14 else 2407 + 5 * channel
    if band == "5 GHz":
        return 5000 + 5 * channel
    if band == "6 GHz":
        return 5935 if channel == 2 else 5950 + 5 * channel
    return 0


def format_bssid(raw_bytes: bytes | Any) -> str:
    """Format 6-byte MAC address to canonical lowercase colon-delimited hex."""
    return ":".join(f"{int(b):02x}" for b in bytes(raw_bytes)[:6])


# ---------------------------------------------------------------------------
# 802.11 Information Element Parser (Pure Python, Hardware/Packet Accurate)
# ---------------------------------------------------------------------------


@dataclass
class Parsed80211IEs:
    """Decoded fields extracted from raw 802.11 management frame Information Elements."""

    ssid: Optional[str] = None
    is_hidden_ssid: bool = False
    country_code: Optional[str] = None
    qbss_station_count: Optional[int] = None
    qbss_utilization_pct: Optional[float] = None
    ht_present: bool = False
    ht_40_capable: bool = False
    ht_primary_channel: Optional[int] = None
    ht_secondary_offset: Optional[int] = None  # 0=none, 1=above, 3=below
    ht_sta_width_any: Optional[bool] = None
    ht_max_streams: Optional[int] = None
    vht_present: bool = False
    vht_max_width_mhz: Optional[int] = None
    vht_op_channel_width: Optional[int] = None
    vht_center_seg0: Optional[int] = None
    vht_center_seg1: Optional[int] = None
    vht_max_streams: Optional[int] = None
    he_present: bool = False
    he_6ghz_op_width_mhz: Optional[int] = None
    eht_present: bool = False
    eht_320_present: bool = False
    security_mode: Optional[str] = None
    inferred_width_mhz: Optional[int] = None
    inferred_phy_standard: Optional[str] = None
    max_spatial_streams: Optional[int] = None


def _count_ht_streams(mcs_bytes: bytes) -> Optional[int]:
    if len(mcs_bytes) < 4:
        return None
    streams = 0
    for idx in range(4):
        if mcs_bytes[idx] != 0:
            streams = idx + 1
    return streams or None


def _count_vht_streams(rx_mcs_map_le: int) -> Optional[int]:
    streams = 0
    for idx in range(8):
        code = (rx_mcs_map_le >> (idx * 2)) & 0x03
        if code != 0x03:
            streams = idx + 1
    return streams or None


def _decode_rsn_akm(payload: bytes) -> Optional[str]:
    """Decode WPA2/WPA3 suite names from RSN IE 48 when present."""
    if len(payload) < 8:
        return "WPA2"
    pos = 2  # version
    pos += 4  # group cipher
    if pos + 2 > len(payload):
        return "WPA2"
    pairwise_count = int.from_bytes(payload[pos : pos + 2], "little")
    pos += 2 + pairwise_count * 4
    if pos + 2 > len(payload):
        return "WPA2"
    akm_count = int.from_bytes(payload[pos : pos + 2], "little")
    pos += 2
    akm_types: List[int] = []
    for _ in range(akm_count):
        if pos + 4 > len(payload):
            break
        oui = payload[pos : pos + 3]
        suite_type = payload[pos + 3]
        if oui == b"\x00\x0f\xac":
            akm_types.append(suite_type)
        pos += 4
    has_sae = any(t in (8, 9, 24) for t in akm_types)
    has_psk = any(t in (2, 4, 6) for t in akm_types)
    has_ent = any(t in (1, 3, 5, 11, 12, 13) for t in akm_types)
    if has_sae and has_psk:
        return "WPA2/WPA3-PSK"
    if has_sae:
        return "WPA3-SAE"
    if 18 in akm_types:
        return "OWE"
    if has_ent:
        return "WPA2/WPA3-Enterprise"
    if has_psk:
        return "WPA2-PSK"
    return "WPA2"


def parse_80211_ies(raw_ies: bytes, *, band_hint: str = "") -> Parsed80211IEs:
    """Parse raw 802.11 management Information Elements conservatively."""
    parsed = Parsed80211IEs()
    if not raw_ies:
        return parsed

    has_wpa1 = False
    rsn_security: Optional[str] = None
    n = len(raw_ies)
    pos = 0
    while pos + 2 <= n:
        ie_id = raw_ies[pos]
        ie_len = raw_ies[pos + 1]
        pos += 2
        if pos + ie_len > n:
            break
        payload = raw_ies[pos : pos + ie_len]
        pos += ie_len

        if ie_id == 0:  # SSID
            if ie_len == 0 or all(b == 0 for b in payload):
                parsed.ssid = ""
                parsed.is_hidden_ssid = True
            else:
                parsed.ssid = payload.decode("utf-8", errors="replace").rstrip("\x00")
                parsed.is_hidden_ssid = len(parsed.ssid) == 0

        elif ie_id == 7 and ie_len >= 3:  # Country
            cc = payload[:2].decode("ascii", errors="ignore").strip()
            if cc.isalpha() and len(cc) == 2:
                parsed.country_code = cc.upper()

        elif ie_id == 11 and ie_len >= 5:  # BSS Load (QBSS)
            parsed.qbss_station_count = int.from_bytes(payload[0:2], "little")
            util_raw = payload[2]
            parsed.qbss_utilization_pct = round((util_raw / 255.0) * 100.0, 1)

        elif ie_id == 45 and ie_len >= 19:  # HT Capabilities
            parsed.ht_present = True
            ht_cap_info = int.from_bytes(payload[0:2], "little")
            parsed.ht_40_capable = bool((ht_cap_info >> 1) & 0x01)
            parsed.ht_max_streams = _count_ht_streams(payload[3:19])

        elif ie_id == 61 and ie_len >= 2:  # HT Operation
            parsed.ht_present = True
            parsed.ht_primary_channel = payload[0]
            info1 = payload[1]
            parsed.ht_secondary_offset = info1 & 0x03
            parsed.ht_sta_width_any = bool((info1 >> 2) & 0x01)

        elif ie_id == 48:  # RSN
            rsn_security = _decode_rsn_akm(payload)

        elif ie_id == 191 and ie_len >= 12:  # VHT Capabilities
            parsed.vht_present = True
            vht_cap = int.from_bytes(payload[0:4], "little")
            supp_width = (vht_cap >> 2) & 0x03
            parsed.vht_max_width_mhz = 160 if supp_width in (1, 2) else 80
            rx_mcs = int.from_bytes(payload[4:6], "little")
            parsed.vht_max_streams = _count_vht_streams(rx_mcs)

        elif ie_id == 192 and ie_len >= 3:  # VHT Operation
            parsed.vht_present = True
            parsed.vht_op_channel_width = payload[0]
            parsed.vht_center_seg0 = payload[1]
            parsed.vht_center_seg1 = payload[2]

        elif ie_id == 221 and ie_len >= 4:  # Vendor specific
            if payload[:4] == b"\x00\x50\xf2\x01":
                has_wpa1 = True

        elif ie_id == 255 and ie_len >= 1:  # Extension Element
            ext_id = payload[0]
            ext_payload = payload[1:]
            if ext_id == 35:  # HE Capabilities
                parsed.he_present = True
            elif ext_id == 36 and len(ext_payload) >= 6:  # HE Operation
                parsed.he_present = True
                he_op_params = int.from_bytes(ext_payload[0:3], "little")
                has_6g_info = bool((he_op_params >> 17) & 0x01)
                if has_6g_info and len(ext_payload) >= 8:
                    # 6 GHz Operation Information follows VHT Op Info (optional) & Co-Hosted BSSID
                    vht_info_present = bool((he_op_params >> 14) & 0x01)
                    co_hosted = bool((he_op_params >> 15) & 0x01)
                    offset_6g = 3 + 1 + 2 + (3 if vht_info_present else 0) + (1 if co_hosted else 0)
                    if len(ext_payload) >= offset_6g + 2:
                        control_6g = ext_payload[offset_6g + 1]
                        w_code = control_6g & 0x03
                        parsed.he_6ghz_op_width_mhz = {0: 20, 1: 40, 2: 80, 3: 160}.get(w_code)
            elif ext_id in (106, 108):  # EHT Operation / EHT Capabilities
                parsed.eht_present = True
                if ext_id == 106 and len(ext_payload) >= 4:
                    # EHT Op Info width field bits 0..2 == 4 denotes 320 MHz
                    op_params = ext_payload[0]
                    if (op_params & 0x01) and len(ext_payload) >= 6:
                        eht_ctrl = ext_payload[5]
                        if (eht_ctrl & 0x07) == 4:
                            parsed.eht_320_present = True

    # Determine operating channel width from IEs without inventing data
    width_mhz: Optional[int] = None
    if parsed.eht_320_present:
        width_mhz = 320
    elif parsed.he_6ghz_op_width_mhz is not None:
        width_mhz = parsed.he_6ghz_op_width_mhz
    elif parsed.vht_present and parsed.vht_op_channel_width is not None:
        v_w = parsed.vht_op_channel_width
        seg0 = parsed.vht_center_seg0 or 0
        seg1 = parsed.vht_center_seg1 or 0
        if v_w == 2 or (v_w == 1 and seg1 > 0 and seg0 > 0 and abs(seg1 - seg0) == 8):
            width_mhz = 160
        elif v_w in (1, 3):
            width_mhz = 80
        elif v_w == 0:
            if parsed.ht_secondary_offset in (1, 3) and parsed.ht_sta_width_any:
                width_mhz = 40
            elif parsed.ht_present:
                width_mhz = 20
    elif parsed.ht_present:
        if parsed.ht_secondary_offset in (1, 3) and (
            parsed.ht_sta_width_any is None or parsed.ht_sta_width_any
        ):
            width_mhz = 40
        elif parsed.ht_secondary_offset == 0 or parsed.ht_sta_width_any is False:
            width_mhz = 20
        elif parsed.ht_40_capable:
            width_mhz = 40
        else:
            width_mhz = 20
    parsed.inferred_width_mhz = width_mhz

    if parsed.eht_present:
        parsed.inferred_phy_standard = "802.11be"
    elif parsed.he_present:
        parsed.inferred_phy_standard = "802.11ax"
    elif parsed.vht_present:
        parsed.inferred_phy_standard = "802.11ac"
    elif parsed.ht_present:
        parsed.inferred_phy_standard = "802.11n"

    streams_candidates = [
        s for s in (parsed.vht_max_streams, parsed.ht_max_streams) if s is not None
    ]
    if streams_candidates:
        parsed.max_spatial_streams = max(streams_candidates)

    if rsn_security and has_wpa1:
        parsed.security_mode = f"WPA/{rsn_security}"
    elif rsn_security:
        parsed.security_mode = rsn_security
    elif has_wpa1:
        parsed.security_mode = "WPA-PSK"

    return parsed


# ---------------------------------------------------------------------------
# Native Windows wlanapi.dll Structures (x64-verified)
# ---------------------------------------------------------------------------


if sys.platform == "win32":

    class _GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", ctypes.c_uint32),
            ("Data2", ctypes.c_uint16),
            ("Data3", ctypes.c_uint16),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    class _DOT11_SSID(ctypes.Structure):
        _fields_ = [("uSSIDLength", ctypes.c_uint32), ("ucSSID", ctypes.c_ubyte * 32)]

    class _WLAN_INTERFACE_INFO(ctypes.Structure):
        _fields_ = [
            ("InterfaceGuid", _GUID),
            ("strInterfaceDescription", ctypes.c_wchar * 256),
            ("isState", ctypes.c_uint32),
        ]

    class _WLAN_INTERFACE_INFO_LIST(ctypes.Structure):
        _fields_ = [
            ("dwNumberOfItems", ctypes.c_uint32),
            ("dwIndex", ctypes.c_uint32),
            ("InterfaceInfo", _WLAN_INTERFACE_INFO * 1),
        ]

    class _WLAN_ASSOCIATION_ATTRIBUTES(ctypes.Structure):
        _fields_ = [
            ("dot11Ssid", _DOT11_SSID),
            ("dot11BssType", ctypes.c_uint32),
            ("dot11Bssid", ctypes.c_ubyte * 6),
            ("dot11PhyType", ctypes.c_uint32),
            ("uDot11PhyIndex", ctypes.c_uint32),
            ("wlanSignalQuality", ctypes.c_uint32),
            ("ulRxRate", ctypes.c_uint32),
            ("ulTxRate", ctypes.c_uint32),
        ]

    class _WLAN_SECURITY_ATTRIBUTES(ctypes.Structure):
        _fields_ = [
            ("bSecurityEnabled", ctypes.c_int32),
            ("bOneXEnabled", ctypes.c_int32),
            ("dot11AuthAlgorithm", ctypes.c_uint32),
            ("dot11CipherAlgorithm", ctypes.c_uint32),
        ]

    class _WLAN_CONNECTION_ATTRIBUTES(ctypes.Structure):
        _fields_ = [
            ("isState", ctypes.c_uint32),
            ("wlanConnectionMode", ctypes.c_uint32),
            ("strProfileName", ctypes.c_wchar * 256),
            ("wlanAssociationAttributes", _WLAN_ASSOCIATION_ATTRIBUTES),
            ("wlanSecurityAttributes", _WLAN_SECURITY_ATTRIBUTES),
        ]

    class _WLAN_RATE_SET(ctypes.Structure):
        _fields_ = [
            ("uRateSetLength", ctypes.c_uint32),
            ("usRateSet", ctypes.c_uint16 * 126),
        ]

    class _WLAN_BSS_ENTRY(ctypes.Structure):
        _fields_ = [
            ("dot11Ssid", _DOT11_SSID),
            ("uPhyId", ctypes.c_uint32),
            ("dot11Bssid", ctypes.c_ubyte * 6),
            ("dot11BssType", ctypes.c_uint32),
            ("dot11BssPhyType", ctypes.c_uint32),
            ("lRssi", ctypes.c_int32),
            ("uLinkQuality", ctypes.c_uint32),
            ("bInRegDomain", ctypes.c_ubyte),
            ("usBeaconPeriod", ctypes.c_uint16),
            ("ullTimestamp", ctypes.c_uint64),
            ("ullHostTimestamp", ctypes.c_uint64),
            ("usCapabilityInformation", ctypes.c_uint16),
            ("ulChCenterFrequency", ctypes.c_uint32),
            ("wlanRateSet", _WLAN_RATE_SET),
            ("ulIeOffset", ctypes.c_uint32),
            ("ulIeSize", ctypes.c_uint32),
        ]

    class _WLAN_BSS_LIST(ctypes.Structure):
        _fields_ = [
            ("dwTotalSize", ctypes.c_uint32),
            ("dwNumberOfItems", ctypes.c_uint32),
            ("wlanBssEntries", _WLAN_BSS_ENTRY * 1),
        ]

    class _WLAN_INTERFACE_CAPABILITY(ctypes.Structure):
        _fields_ = [
            ("interfaceType", ctypes.c_uint32),
            ("bDot11DSupported", ctypes.c_int32),
            ("dwMaxDesiredSsidListSize", ctypes.c_uint32),
            ("dwMaxDesiredBssidListSize", ctypes.c_uint32),
            ("dwNumberOfSupportedPhys", ctypes.c_uint32),
            ("dot11PhyTypes", ctypes.c_uint32 * 64),
        ]

    class _WLAN_MAC_FRAME_STATISTICS(ctypes.Structure):
        _fields_ = [
            ("ullTransmittedFrameCount", ctypes.c_uint64),
            ("ullReceivedFrameCount", ctypes.c_uint64),
            ("ullWEPExcludedCount", ctypes.c_uint64),
            ("ullTKIPLocalMICFailures", ctypes.c_uint64),
            ("ullTKIPReplays", ctypes.c_uint64),
            ("ullTKIPICVErrorCount", ctypes.c_uint64),
            ("ullCCMPReplays", ctypes.c_uint64),
            ("ullCCMPDecryptErrors", ctypes.c_uint64),
            ("ullWEPUndecryptableCount", ctypes.c_uint64),
            ("ullWEPICVErrorCount", ctypes.c_uint64),
            ("ullDecryptSuccessCount", ctypes.c_uint64),
            ("ullDecryptFailureCount", ctypes.c_uint64),
        ]

    class _WLAN_PHY_FRAME_STATISTICS(ctypes.Structure):
        _fields_ = [
            ("ullTransmittedFrameCount", ctypes.c_uint64),
            ("ullMulticastTransmittedFrameCount", ctypes.c_uint64),
            ("ullFailedCount", ctypes.c_uint64),
            ("ullRetryCount", ctypes.c_uint64),
            ("ullMultipleRetryCount", ctypes.c_uint64),
            ("ullMaxTXLifetimeExceededCount", ctypes.c_uint64),
            ("ullTransmittedFragmentCount", ctypes.c_uint64),
            ("ullRTSSuccessCount", ctypes.c_uint64),
            ("ullRTSFailureCount", ctypes.c_uint64),
            ("ullACKFailureCount", ctypes.c_uint64),
            ("ullReceivedFrameCount", ctypes.c_uint64),
            ("ullMulticastReceivedFrameCount", ctypes.c_uint64),
            ("ullPromiscuousReceivedFrameCount", ctypes.c_uint64),
            ("ullMaxRXLifetimeExceededCount", ctypes.c_uint64),
            ("ullFrameDuplicateCount", ctypes.c_uint64),
            ("ullReceivedFragmentCount", ctypes.c_uint64),
            ("ullPromiscuousReceivedFragmentCount", ctypes.c_uint64),
            ("ullFCSErrorCount", ctypes.c_uint64),
        ]

    class _WLAN_STATISTICS(ctypes.Structure):
        _fields_ = [
            ("ullFourWayHandshakeFailures", ctypes.c_uint64),
            ("ullTKIPCounterMeasuresInvoked", ctypes.c_uint64),
            ("ullReserved", ctypes.c_uint64),
            ("MacUcastCounters", _WLAN_MAC_FRAME_STATISTICS),
            ("MacMcastCounters", _WLAN_MAC_FRAME_STATISTICS),
            ("dwNumberOfPhys", ctypes.c_uint32),
            ("PhyCounters", _WLAN_PHY_FRAME_STATISTICS * 1),
        ]


@dataclass
class RawNativeWlanBss:
    """In-memory decoded BSS entry before conversion to public models."""

    ssid: str
    is_hidden: bool
    bssid: str
    band: str
    channel: int
    center_frequency_mhz: int
    rssi_dbm: int
    signal_quality_pct: int
    phy_standard: Optional[str]
    in_reg_domain: bool
    last_seen_timestamp: int
    parsed_ies: Parsed80211IEs


@dataclass
class NativeWlanSnapshot:
    """Aggregate low-level data retrieved in a single wlanapi.dll session."""

    interface_description: Optional[str] = None
    interface_guid: Optional[str] = None
    connection_state: str = "disconnected"
    ssid: Optional[str] = None
    bssid: Optional[str] = None
    phy_standard: Optional[str] = None
    signal_quality_pct: Optional[int] = None
    rssi_dbm: Optional[int] = None
    rx_rate_mbps: Optional[float] = None
    tx_rate_mbps: Optional[float] = None
    channel: Optional[int] = None
    channel_frequency_mhz: Optional[int] = None
    band: Optional[str] = None
    security_mode: Optional[str] = None
    supported_phys: List[str] = field(default_factory=list)
    supported_bands: List[str] = field(default_factory=list)
    phy_tx_failed_count: Optional[int] = None
    phy_retry_count: Optional[int] = None
    phy_multiple_retry_count: Optional[int] = None
    phy_fcs_error_count: Optional[int] = None
    bss_entries: List[RawNativeWlanBss] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


def _guid_to_str(guid: Any) -> str:
    d4 = bytes(guid.Data4)
    return (
        f"{{{guid.Data1:08x}-{guid.Data2:04x}-{guid.Data3:04x}-"
        f"{d4[:2].hex()}-{d4[2:].hex()}}}"
    )


def _decode_bss_entries_from_ptr(blist_ptr: Any) -> List[RawNativeWlanBss]:
    items: List[RawNativeWlanBss] = []
    if not blist_ptr:
        return items
    blist = blist_ptr.contents
    count = int(blist.dwNumberOfItems)
    base_addr = ctypes.cast(blist_ptr, ctypes.c_void_p).value
    if not base_addr:
        return items
    entries_start = base_addr + 8
    entry_size = ctypes.sizeof(_WLAN_BSS_ENTRY)

    for idx in range(count):
        ep = entries_start + idx * entry_size
        entry = _WLAN_BSS_ENTRY.from_address(ep)
        ssid_len = min(int(entry.dot11Ssid.uSSIDLength), 32)
        raw_ssid = bytes(entry.dot11Ssid.ucSSID[:ssid_len])
        is_hidden = ssid_len == 0 or all(b == 0 for b in raw_ssid)
        ssid = "" if is_hidden else raw_ssid.decode("utf-8", errors="replace").rstrip("\x00")
        bssid = format_bssid(entry.dot11Bssid)
        band, channel, freq_mhz = freq_khz_to_band_and_channel(int(entry.ulChCenterFrequency))
        phy_std = DOT11_PHY_TYPE_MAP.get(int(entry.dot11BssPhyType))

        ie_bytes = b""
        if entry.ulIeSize > 0 and entry.ulIeOffset >= entry_size:
            ie_bytes = ctypes.string_at(ep + entry.ulIeOffset, int(entry.ulIeSize))
        parsed_ies = parse_80211_ies(ie_bytes, band_hint=band)
        if not ssid and parsed_ies.ssid:
            ssid = parsed_ies.ssid
            is_hidden = parsed_ies.is_hidden_ssid
        if parsed_ies.inferred_phy_standard:
            # Prefer highest advertised standard if IE indicates 802.11ax/be
            phy_order = {"802.11b": 1, "802.11g": 2, "802.11a": 2, "802.11n": 3, "802.11ac": 4, "802.11ax": 5, "802.11be": 6}
            if phy_order.get(parsed_ies.inferred_phy_standard, 0) > phy_order.get(phy_std or "", 0):
                phy_std = parsed_ies.inferred_phy_standard

        items.append(
            RawNativeWlanBss(
                ssid=ssid,
                is_hidden=is_hidden,
                bssid=bssid,
                band=band,
                channel=channel,
                center_frequency_mhz=freq_mhz,
                rssi_dbm=int(entry.lRssi),
                signal_quality_pct=int(entry.uLinkQuality),
                phy_standard=phy_std,
                in_reg_domain=bool(entry.bInRegDomain),
                last_seen_timestamp=int(entry.ullHostTimestamp),
                parsed_ies=parsed_ies,
            )
        )
    return items


def query_native_wlan(trigger_active_scan: bool = False) -> NativeWlanSnapshot:
    """Query native Windows wlanapi.dll for connection attributes, capabilities, stats, and BSS list."""
    snap = NativeWlanSnapshot()
    if sys.platform != "win32":
        snap.notes.append("Native Windows wlanapi.dll is only supported on win32.")
        return snap

    try:
        # Use a dedicated WinDLL instance so WindowsPlatformAdapter's argtypes on ctypes.windll.wlanapi never collide.
        wlanapi = ctypes.WinDLL("wlanapi")
    except Exception as exc:
        snap.notes.append(f"Failed to load wlanapi.dll: {exc}")
        return snap

    negotiated = ctypes.c_uint32()
    handle = ctypes.c_void_p()
    rc = wlanapi.WlanOpenHandle(2, None, ctypes.byref(negotiated), ctypes.byref(handle))
    if rc != 0 or not handle.value:
        snap.notes.append(f"WlanOpenHandle failed with Win32 error {rc}.")
        return snap

    plist = ctypes.POINTER(_WLAN_INTERFACE_INFO_LIST)()
    try:
        rc = wlanapi.WlanEnumInterfaces(handle, None, ctypes.byref(plist))
        if rc != 0 or not plist or plist.contents.dwNumberOfItems == 0:
            snap.notes.append("No active Windows WLAN interfaces reported.")
            return snap

        # Choose connected interface first, else first interface.
        iface_count = int(plist.contents.dwNumberOfItems)
        list_base = ctypes.cast(plist, ctypes.c_void_p).value + 8
        chosen_iface = _WLAN_INTERFACE_INFO.from_address(list_base)
        for idx in range(iface_count):
            candidate = _WLAN_INTERFACE_INFO.from_address(
                list_base + idx * ctypes.sizeof(_WLAN_INTERFACE_INFO)
            )
            if int(candidate.isState) == 1:
                chosen_iface = candidate
                break

        guid = chosen_iface.InterfaceGuid
        snap.interface_description = chosen_iface.strInterfaceDescription.strip()
        snap.interface_guid = _guid_to_str(guid)
        snap.connection_state = WLAN_INTERFACE_STATE_MAP.get(
            int(chosen_iface.isState), f"state_{chosen_iface.isState}"
        )

        # Optional trigger scan when explicitly requested (caller enforces meeting safety)
        if trigger_active_scan:
            scan_rc = wlanapi.WlanScan(handle, ctypes.byref(guid), None, None, None)
            if scan_rc != 0:
                snap.notes.append(f"WlanScan returned Win32 code {scan_rc}; using cached BSS table.")
            else:
                # Windows WlanScan completes asynchronously; wait briefly for fresh 2.4/5 GHz BSS entries.
                time.sleep(1.25)

        # 1. Interface capabilities
        cap_ptr = ctypes.POINTER(_WLAN_INTERFACE_CAPABILITY)()
        if wlanapi.WlanGetInterfaceCapability(handle, ctypes.byref(guid), None, ctypes.byref(cap_ptr)) == 0 and cap_ptr:
            try:
                cap = cap_ptr.contents
                n_phys = min(int(cap.dwNumberOfSupportedPhys), 64)
                phys: List[str] = []
                for idx in range(n_phys):
                    code = int(cap.dot11PhyTypes[idx])
                    phys.append(DOT11_PHY_TYPE_MAP.get(code, f"phy_{code}"))
                snap.supported_phys = phys
                bands: List[str] = []
                if any(p in phys for p in ("802.11b", "802.11g", "802.11n", "802.11ax", "802.11be")):
                    bands.append("2.4 GHz")
                if any(p in phys for p in ("802.11a", "802.11n", "802.11ac", "802.11ax", "802.11be")):
                    bands.append("5 GHz")
                if any(p in phys for p in ("802.11ax", "802.11be")):
                    # Note: 6 GHz depends on card/OS; verified via BSS or driver properties.
                    pass
                snap.supported_bands = bands
            finally:
                wlanapi.WlanFreeMemory(cap_ptr)

        # 2. Current Connection Attributes
        sz = ctypes.c_uint32()
        ptr = ctypes.c_void_p()
        if (
            wlanapi.WlanQueryInterface(
                handle,
                ctypes.byref(guid),
                WLAN_OPCODE_CURRENT_CONNECTION,
                None,
                ctypes.byref(sz),
                ctypes.byref(ptr),
                None,
            )
            == 0
            and ptr.value
        ):
            try:
                if sz.value >= ctypes.sizeof(_WLAN_CONNECTION_ATTRIBUTES):
                    conn = _WLAN_CONNECTION_ATTRIBUTES.from_address(ptr.value)
                    snap.connection_state = WLAN_INTERFACE_STATE_MAP.get(
                        int(conn.isState), snap.connection_state
                    )
                    assoc = conn.wlanAssociationAttributes
                    ssid_len = min(int(assoc.dot11Ssid.uSSIDLength), 32)
                    snap.ssid = bytes(assoc.dot11Ssid.ucSSID[:ssid_len]).decode(
                        "utf-8", errors="replace"
                    )
                    snap.bssid = format_bssid(assoc.dot11Bssid)
                    snap.phy_standard = DOT11_PHY_TYPE_MAP.get(int(assoc.dot11PhyType))
                    snap.signal_quality_pct = int(assoc.wlanSignalQuality)
                    if assoc.ulRxRate > 0:
                        snap.rx_rate_mbps = round(assoc.ulRxRate / 1000.0, 1)
                    if assoc.ulTxRate > 0:
                        snap.tx_rate_mbps = round(assoc.ulTxRate / 1000.0, 1)
                    sec = conn.wlanSecurityAttributes
                    if sec.bSecurityEnabled:
                        auth_s = DOT11_AUTH_ALGO_MAP.get(int(sec.dot11AuthAlgorithm), "Unknown")
                        ciph_s = DOT11_CIPHER_ALGO_MAP.get(int(sec.dot11CipherAlgorithm), "Unknown")
                        snap.security_mode = f"{auth_s} ({ciph_s})"
                    else:
                        snap.security_mode = "Open"
            finally:
                wlanapi.WlanFreeMemory(ptr)

        # 3. Direct Channel Number
        sz = ctypes.c_uint32()
        ptr = ctypes.c_void_p()
        if (
            wlanapi.WlanQueryInterface(
                handle,
                ctypes.byref(guid),
                WLAN_OPCODE_CHANNEL_NUMBER,
                None,
                ctypes.byref(sz),
                ctypes.byref(ptr),
                None,
            )
            == 0
            and ptr.value
        ):
            try:
                snap.channel = int(ctypes.c_uint32.from_address(ptr.value).value)
            finally:
                wlanapi.WlanFreeMemory(ptr)

        # 4. Direct RSSI (dBm)
        sz = ctypes.c_uint32()
        ptr = ctypes.c_void_p()
        if (
            wlanapi.WlanQueryInterface(
                handle,
                ctypes.byref(guid),
                WLAN_OPCODE_RSSI,
                None,
                ctypes.byref(sz),
                ctypes.byref(ptr),
                None,
            )
            == 0
            and ptr.value
        ):
            try:
                snap.rssi_dbm = int(ctypes.c_int32.from_address(ptr.value).value)
            finally:
                wlanapi.WlanFreeMemory(ptr)

        # 5. PHY Statistics
        sz = ctypes.c_uint32()
        ptr = ctypes.c_void_p()
        if (
            wlanapi.WlanQueryInterface(
                handle,
                ctypes.byref(guid),
                WLAN_OPCODE_STATISTICS,
                None,
                ctypes.byref(sz),
                ctypes.byref(ptr),
                None,
            )
            == 0
            and ptr.value
        ):
            try:
                header_offset = ctypes.sizeof(_WLAN_STATISTICS) - ctypes.sizeof(
                    _WLAN_PHY_FRAME_STATISTICS
                )
                if sz.value >= header_offset:
                    stats_base = _WLAN_STATISTICS.from_address(ptr.value)
                    n_phys = int(stats_base.dwNumberOfPhys)
                    phy_sz = ctypes.sizeof(_WLAN_PHY_FRAME_STATISTICS)
                    failed = retry = multi_retry = fcs = 0
                    found_phy = False
                    for idx in range(n_phys):
                        offset = header_offset + idx * phy_sz
                        if offset + phy_sz <= sz.value:
                            found_phy = True
                            pstat = _WLAN_PHY_FRAME_STATISTICS.from_address(ptr.value + offset)
                            failed += int(pstat.ullFailedCount)
                            retry += int(pstat.ullRetryCount)
                            multi_retry += int(pstat.ullMultipleRetryCount)
                            fcs += int(pstat.ullFCSErrorCount)
                    if found_phy:
                        snap.phy_tx_failed_count = failed
                        snap.phy_retry_count = retry
                        snap.phy_multiple_retry_count = multi_retry
                        snap.phy_fcs_error_count = fcs
            finally:
                wlanapi.WlanFreeMemory(ptr)

        # 6. Full BSS list across all bands/channels visible to driver
        blist_ptr = ctypes.POINTER(_WLAN_BSS_LIST)()
        if (
            wlanapi.WlanGetNetworkBssList(
                handle,
                ctypes.byref(guid),
                None,
                3,  # dot11_BSS_type_any
                False,
                None,
                ctypes.byref(blist_ptr),
            )
            == 0
            and blist_ptr
        ):
            try:
                snap.bss_entries = _decode_bss_entries_from_ptr(blist_ptr)
                if snap.bssid:
                    for bss in snap.bss_entries:
                        if bss.bssid == snap.bssid:
                            snap.channel_frequency_mhz = bss.center_frequency_mhz
                            snap.band = bss.band
                            if snap.channel is None and bss.channel:
                                snap.channel = bss.channel
                            if snap.rssi_dbm is None:
                                snap.rssi_dbm = bss.rssi_dbm
                            break
            finally:
                wlanapi.WlanFreeMemory(blist_ptr)

        if snap.band is None and snap.channel is not None:
            if 1 <= snap.channel <= 14:
                snap.band = "2.4 GHz"
            elif snap.channel >= 32:
                snap.band = "5 GHz"
            if snap.channel_frequency_mhz is None and snap.band:
                snap.channel_frequency_mhz = channel_to_center_freq_mhz(snap.band, snap.channel)

    finally:
        if plist:
            wlanapi.WlanFreeMemory(plist)
        wlanapi.WlanCloseHandle(handle, None)

    return snap


# ---------------------------------------------------------------------------
# Roaming & Windows Operational Event Log Parsers
# ---------------------------------------------------------------------------


class WifiRoamTracker:
    """In-session observer recording BSSID/band/channel roaming transitions."""

    def __init__(self, max_events: int = 50) -> None:
        self._lock = threading.Lock()
        self._events: Deque[RoamingEventRecord] = deque(maxlen=max_events)
        self._last_ssid: Optional[str] = None
        self._last_bssid: Optional[str] = None
        self._last_channel: Optional[int] = None
        self._last_band: Optional[str] = None
        self._last_rssi: Optional[int] = None

    def observe(
        self,
        *,
        ssid: Optional[str],
        bssid: Optional[str],
        channel: Optional[int],
        band: Optional[str],
        rssi_dbm: Optional[int],
    ) -> Optional[RoamingEventRecord]:
        with self._lock:
            roam_evt: Optional[RoamingEventRecord] = None
            if (
                self._last_bssid
                and bssid
                and self._last_bssid != bssid
                and (ssid == self._last_ssid or not ssid or not self._last_ssid)
            ):
                roam_evt = RoamingEventRecord(
                    timestamp=utc_now(),
                    ssid=ssid or self._last_ssid,
                    from_bssid=self._last_bssid,
                    to_bssid=bssid,
                    from_channel=self._last_channel,
                    to_channel=channel,
                    from_band=self._last_band,
                    to_band=band,
                    from_rssi_dbm=self._last_rssi,
                    to_rssi_dbm=rssi_dbm,
                    source="session_tracker",
                )
                self._events.appendleft(roam_evt)

            if bssid:
                self._last_ssid = ssid
                self._last_bssid = bssid
                self._last_channel = channel
                self._last_band = band
                self._last_rssi = rssi_dbm
            return roam_evt

    def get_events(self) -> List[RoamingEventRecord]:
        with self._lock:
            return list(self._events)


def parse_wlan_event_xml(xml_text: str) -> List[WlanEventRecord]:
    """Parse wevtutil XML stream from Microsoft-Windows-WLAN-AutoConfig/Operational."""
    if not xml_text or not xml_text.strip():
        return []
    wrapped = f"<Events>{xml_text}</Events>"
    try:
        root = ET.fromstring(wrapped)
    except ET.ParseError:
        return []

    records: List[WlanEventRecord] = []
    ns = "{http://schemas.microsoft.com/win/2004/08/events/event}"

    def _find_child(parent: ET.Element, *tags: str) -> Optional[ET.Element]:
        for tag in tags:
            found = parent.find(tag)
            if found is not None:
                return found
        return None

    for ev in root.findall(f"{ns}Event") + root.findall("Event"):
        sys_el = _find_child(ev, f"{ns}System", "System")
        if sys_el is None:
            continue
        eid_el = _find_child(sys_el, f"{ns}EventID", "EventID")
        tc_el = _find_child(sys_el, f"{ns}TimeCreated", "TimeCreated")
        if eid_el is None or eid_el.text is None:
            continue
        try:
            event_id = int(eid_el.text.strip())
        except ValueError:
            continue

        ts_raw = tc_el.attrib.get("SystemTime", "") if tc_el is not None else ""
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except Exception:
            ts = utc_now()

        data_map: Dict[str, str] = {}
        ev_data = _find_child(ev, f"{ns}EventData", "EventData")
        if ev_data is not None:
            for item in ev_data.findall(f"{ns}Data") + ev_data.findall("Data"):
                name = item.attrib.get("Name")
                if name:
                    data_map[name] = (item.text or "").strip()

        ev_type_map: Dict[int, str] = {
            8001: "connected",
            8002: "disconnected",
            8003: "disconnected",
            8000: "association",
            11000: "association",
            11001: "association",
            11005: "auth",
            11010: "scan",
            12011: "connected",
            12012: "disconnected",
            12013: "disconnected",
        }
        ev_type = ev_type_map.get(event_id, "other")
        if "roam" in data_map.get("ConnectionMode", "").lower():
            ev_type = "roam"

        reason = data_map.get("ReasonCode") or data_map.get("FailureReason") or data_map.get("Reason")
        ssid = data_map.get("SSID") or None
        bssid = data_map.get("BSSID") or data_map.get("PeerMacAddress") or None
        iface = data_map.get("InterfaceName") or data_map.get("InterfaceGuid") or None
        msg_parts = [f"Event {event_id}"]
        if ssid:
            msg_parts.append(f"SSID={ssid}")
        if bssid:
            msg_parts.append(f"BSSID={bssid}")
        if reason:
            msg_parts.append(f"Reason={reason}")

        records.append(
            WlanEventRecord(
                event_id=event_id,
                timestamp=ts,
                event_type=ev_type,  # type: ignore[arg-type]
                interface_name=iface,
                ssid=ssid,
                bssid=bssid,
                reason_code=reason,
                message=" | ".join(msg_parts),
                source="Microsoft-Windows-WLAN-AutoConfig/Operational",
            )
        )
    return records


def query_wlan_operational_events(max_events: int = 25) -> List[WlanEventRecord]:
    """Query recent WLAN connection, disconnection, and roaming operational logs."""
    if sys.platform != "win32":
        return []
    xpath = (
        "*[System[(EventID=8000 or EventID=8001 or EventID=8002 or EventID=8003 "
        "or EventID=11000 or EventID=11001 or EventID=11005 or EventID=12011 "
        "or EventID=12012 or EventID=12013)]]"
    )
    cmd = [
        "wevtutil.exe",
        "qe",
        "Microsoft-Windows-WLAN-AutoConfig/Operational",
        f"/q:{xpath}",
        f"/c:{int(max_events)}",
        "/rd:true",
        "/f:xml",
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
            **_subprocess_kwargs(),
        )
        if proc.returncode == 0 and proc.stdout:
            return parse_wlan_event_xml(proc.stdout)
    except Exception:
        pass
    return []


def _query_adapter_driver_and_stats_ps(adapter_desc: Optional[str]) -> Dict[str, Any]:
    """Fetch Windows NDIS interface name, driver metadata, stats, and advanced settings."""
    if sys.platform != "win32":
        return {}
    ps_script = (
        "$a = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and ($_.InterfaceDescription -match 'Wireless|Wi-Fi|802\\.11' -or $_.PhysicalMediaType -match '802\\.11') } | Select-Object -First 1 Name, InterfaceDescription, DriverVersion, DriverDate, DriverProvider, MacAddress, LinkSpeed; "
        "if (-not $a) { $a = Get-NetAdapter | Where-Object { $_.Name -match 'Wi-Fi|WLAN' } | Select-Object -First 1 Name, InterfaceDescription, DriverVersion, DriverDate, DriverProvider, MacAddress, LinkSpeed }; "
        "$stats = $null; $adv = @(); "
        "if ($a) { "
        "  $stats = Get-NetAdapterStatistics -Name $a.Name -ErrorAction SilentlyContinue | Select-Object ReceivedBytes, SentBytes, ReceivedUnicastPackets, SentUnicastPackets, ReceivedPacketErrors, OutboundPacketErrors, ReceivedDiscardedPackets, OutboundDiscardedPackets; "
        "  $adv = Get-NetAdapterAdvancedProperty -Name $a.Name -ErrorAction SilentlyContinue | Where-Object { $_.RegistryKeyword -match 'ChannelWidth|Roam|WirelessMode|PreferredBand|IEEE11nMode' } | Select-Object RegistryKeyword, DisplayName, DisplayValue "
        "}; "
        "[PSCustomObject]@{ adapter = $a; stats = $stats; advanced = @($adv) } | ConvertTo-Json -Depth 4"
    )
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            **_subprocess_kwargs(),
        )
        if proc.returncode == 0 and proc.stdout.strip():
            data = json.loads(proc.stdout)
            return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}


def _query_netsh_driver_lines() -> Dict[str, Any]:
    """Read driver vendor/version/radio types from netsh wlan show drivers."""
    if sys.platform != "win32":
        return {}
    try:
        proc = subprocess.run(
            ["netsh", "wlan", "show", "drivers"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
            **_subprocess_kwargs(),
        )
        if proc.returncode != 0 or not proc.stdout:
            return {}
        info: Dict[str, Any] = {}
        for line in proc.stdout.splitlines():
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            kl = k.strip().lower()
            val = v.strip()
            if "interface name" in kl:
                info["interface_name"] = val
            elif kl == "vendor":
                info["vendor"] = val
            elif kl == "provider":
                info["provider"] = val
            elif kl == "version":
                info["version"] = val
            elif kl == "date":
                info["date"] = val
            elif "radio types supported" in kl:
                info["radio_types"] = val.split()
        return info
    except Exception:
        return {}


class WifiTelemetryService:
    """Collects verified Windows Wi-Fi telemetry without fabricating unsupported metrics."""

    def __init__(self, roam_tracker: Optional[WifiRoamTracker] = None) -> None:
        self._roam_tracker = roam_tracker or WifiRoamTracker()
        self._last_native: Optional[NativeWlanSnapshot] = None

    @property
    def roam_tracker(self) -> WifiRoamTracker:
        return self._roam_tracker

    def collect_telemetry_sync(
        self,
        *,
        include_events: bool = True,
        include_ps_driver_stats: bool = True,
        trigger_active_scan: bool = False,
    ) -> WifiInterfaceTelemetry:
        """Collect complete real-time Wi-Fi telemetry synchronously."""
        native = query_native_wlan(trigger_active_scan=trigger_active_scan)
        self._last_native = native

        ps_data = (
            _query_adapter_driver_and_stats_ps(native.interface_description)
            if include_ps_driver_stats
            else {}
        )
        netsh_drv = _query_netsh_driver_lines() if include_ps_driver_stats else {}
        adapter_info = ps_data.get("adapter") or {}
        if isinstance(adapter_info, list):
            adapter_info = adapter_info[0] if adapter_info else {}
        ps_stats = ps_data.get("stats") or {}
        ps_adv = ps_data.get("advanced") or []
        if isinstance(ps_adv, dict):
            ps_adv = [ps_adv]

        iface_name = (
            adapter_info.get("Name")
            or netsh_drv.get("interface_name")
            or ("Wi-Fi" if native.interface_description else None)
        )
        adapter_desc = native.interface_description or adapter_info.get("InterfaceDescription")

        adv_map: Dict[str, str] = {}
        for item in ps_adv:
            if isinstance(item, dict) and item.get("RegistryKeyword"):
                adv_map[str(item["RegistryKeyword"])] = str(item.get("DisplayValue", ""))

        # Inspect connected AP raw 802.11 IEs if available in BSS table
        connected_bss: Optional[RawNativeWlanBss] = None
        if native.bssid:
            for bss in native.bss_entries:
                if bss.bssid == native.bssid:
                    connected_bss = bss
                    break

        notes = list(native.notes)

        # Channel width: use AP 802.11 Operation IE if visible, never invent
        channel_width: Optional[int] = None
        width_prov = MeasurementProvenance.UNAVAILABLE
        width_note = (
            "Windows Native Wifi API does not directly return active modulation channel width; "
            "channel width is unavailable without connected BSS 802.11 Information Elements."
        )
        if connected_bss and connected_bss.parsed_ies.inferred_width_mhz:
            channel_width = connected_bss.parsed_ies.inferred_width_mhz
            width_prov = MeasurementProvenance.INFERRED
            width_note = (
                f"Determined from connected AP 802.11 HT/VHT/HE Operation IE ({channel_width} MHz)."
            )

        # PHY provenance
        phy_std = native.phy_standard
        phy_prov = (
            MeasurementProvenance.MEASURED
            if phy_std is not None
            else MeasurementProvenance.UNAVAILABLE
        )

        # RSSI & signal quality provenance
        rssi_prov = (
            MeasurementProvenance.MEASURED
            if native.rssi_dbm is not None
            else MeasurementProvenance.UNAVAILABLE
        )
        sig_prov = (
            MeasurementProvenance.MEASURED
            if native.signal_quality_pct is not None
            else MeasurementProvenance.UNAVAILABLE
        )
        rate_prov = (
            MeasurementProvenance.MEASURED
            if (native.tx_rate_mbps is not None or native.rx_rate_mbps is not None)
            else MeasurementProvenance.UNAVAILABLE
        )

        # Spatial streams & MCS: never invent per-packet MCS
        max_streams = (
            connected_bss.parsed_ies.max_spatial_streams if connected_bss else None
        )
        streams_prov = (
            MeasurementProvenance.INFERRED
            if max_streams is not None
            else MeasurementProvenance.UNAVAILABLE
        )
        streams_reason = (
            f"Max AP spatial capability ({max_streams}x{max_streams} SS) inferred from connected AP 802.11 HT/VHT IEs; live per-packet active stream count is not exposed by Windows wlanapi.dll."
            if max_streams is not None
            else "Windows wlanapi.dll and this adapter driver do not expose active spatial streams."
        )

        # Capabilities
        supported_phys = list(native.supported_phys)
        if netsh_drv.get("radio_types"):
            for r in netsh_drv["radio_types"]:
                if r not in supported_phys:
                    supported_phys.append(r)

        supported_bands = list(native.supported_bands)
        if any(b.band == "6 GHz" for b in native.bss_entries) and "6 GHz" not in supported_bands:
            supported_bands.append("6 GHz")

        country_domain = next(
            (b.parsed_ies.country_code for b in native.bss_entries if b.parsed_ies.country_code),
            None,
        )

        capabilities = (
            AdapterCapabilities(
                interface_name=iface_name or "Wi-Fi",
                adapter_description=adapter_desc,
                driver_version=(
                    str(adapter_info.get("DriverVersion") or netsh_drv.get("version") or "")
                    or None
                ),
                driver_date=(
                    str(adapter_info.get("DriverDate") or netsh_drv.get("date") or "") or None
                ),
                driver_provider=(
                    str(adapter_info.get("DriverProvider") or netsh_drv.get("provider") or "")
                    or None
                ),
                supported_phys=supported_phys,
                supported_bands=supported_bands,
                max_channel_width_mhz=(
                    connected_bss.parsed_ies.vht_max_width_mhz
                    if connected_bss and connected_bss.parsed_ies.vht_max_width_mhz
                    else (80 if "802.11ac" in supported_phys else (40 if "802.11n" in supported_phys else 20))
                ),
                max_spatial_streams=max_streams,
                supports_6ghz=("6 GHz" in supported_bands),
                supports_wifi6=any("ax" in p.lower() for p in supported_phys),
                supports_wifi7=any("be" in p.lower() for p in supported_phys),
                roaming_aggressiveness=adv_map.get("RoamAggressiveness"),
                preferred_band=adv_map.get("RoamingPreferredBandType"),
                channel_width_24_setting=adv_map.get("ChannelWidth24"),
                channel_width_5_setting=adv_map.get("ChannelWidth52"),
                regulatory_domain=country_domain,
                source_details={
                    "phy_list": "wlanapi.WlanGetInterfaceCapability",
                    "driver_stats": "PowerShell Get-NetAdapter / netsh wlan show drivers",
                    "advanced_props": "Get-NetAdapterAdvancedProperty",
                },
            )
            if (iface_name or adapter_desc)
            else None
        )

        # Stats
        rx_packets = None
        tx_packets = None
        if ps_stats.get("ReceivedUnicastPackets") is not None:
            rx_packets = int(ps_stats.get("ReceivedUnicastPackets") or 0)
        if ps_stats.get("SentUnicastPackets") is not None:
            tx_packets = int(ps_stats.get("SentUnicastPackets") or 0)

        has_any_stats = bool(ps_stats) or native.phy_tx_failed_count is not None
        iface_stats = InterfaceStatsSnapshot(
            rx_bytes=int(ps_stats["ReceivedBytes"]) if ps_stats.get("ReceivedBytes") is not None else None,
            tx_bytes=int(ps_stats["SentBytes"]) if ps_stats.get("SentBytes") is not None else None,
            rx_packets=rx_packets,
            tx_packets=tx_packets,
            rx_errors=(
                int(ps_stats["ReceivedPacketErrors"])
                if ps_stats.get("ReceivedPacketErrors") is not None
                else None
            ),
            tx_errors=(
                int(ps_stats["OutboundPacketErrors"])
                if ps_stats.get("OutboundPacketErrors") is not None
                else None
            ),
            rx_discards=(
                int(ps_stats["ReceivedDiscardedPackets"])
                if ps_stats.get("ReceivedDiscardedPackets") is not None
                else None
            ),
            tx_discards=(
                int(ps_stats["OutboundDiscardedPackets"])
                if ps_stats.get("OutboundDiscardedPackets") is not None
                else None
            ),
            phy_tx_failed_count=native.phy_tx_failed_count,
            phy_retry_count=native.phy_retry_count,
            phy_multiple_retry_count=native.phy_multiple_retry_count,
            phy_fcs_error_count=native.phy_fcs_error_count,
            provenance=(
                MeasurementProvenance.MEASURED
                if has_any_stats
                else MeasurementProvenance.UNAVAILABLE
            ),
            source="Get-NetAdapterStatistics + wlanapi.WLAN_STATISTICS",
        )

        # Observe BSSID roam
        self._roam_tracker.observe(
            ssid=native.ssid,
            bssid=native.bssid,
            channel=native.channel,
            band=native.band,
            rssi_dbm=native.rssi_dbm,
        )

        wlan_events = query_wlan_operational_events() if include_events else []

        return WifiInterfaceTelemetry(
            captured_at=utc_now(),
            interface_name=iface_name,
            interface_guid=native.interface_guid,
            adapter_description=adapter_desc,
            connection_state=native.connection_state,
            ssid=native.ssid,
            bssid=native.bssid,
            phy_standard=phy_std,
            phy_provenance=phy_prov,
            band=native.band,
            channel=native.channel,
            channel_frequency_mhz=native.channel_frequency_mhz,
            channel_width_mhz=channel_width,
            channel_width_provenance=width_prov,
            channel_width_note=width_note,
            rssi_dbm=native.rssi_dbm,
            rssi_provenance=rssi_prov,
            signal_quality_pct=native.signal_quality_pct,
            signal_quality_provenance=sig_prov,
            noise_floor_dbm=None,
            noise_floor_provenance=MeasurementProvenance.UNAVAILABLE,
            noise_floor_reason=(
                "Unsupported: Windows Native Wifi (wlanapi.dll) and standard NDIS APIs do not "
                "report an RF noise floor measurement in dBm. Noise floor is never derived from RSSI."
            ),
            snr_db=None,
            snr_provenance=MeasurementProvenance.UNAVAILABLE,
            snr_reason=(
                "Unavailable: SNR in dB requires a genuine driver noise floor measurement in dBm."
            ),
            tx_link_rate_mbps=native.tx_rate_mbps,
            rx_link_rate_mbps=native.rx_rate_mbps,
            link_rate_provenance=rate_prov,
            mcs_index=None,
            mcs_provenance=MeasurementProvenance.UNAVAILABLE,
            mcs_reason=(
                "Unsupported: Windows wlanapi.dll exposes TX/RX link rates in kbps but does not "
                "expose the live MCS index used per frame."
            ),
            spatial_streams=max_streams,
            spatial_streams_provenance=streams_prov,
            spatial_streams_reason=streams_reason,
            security_mode=(
                connected_bss.parsed_ies.security_mode
                if connected_bss and connected_bss.parsed_ies.security_mode
                else native.security_mode
            ),
            qbss_channel_utilization_pct=(
                connected_bss.parsed_ies.qbss_utilization_pct if connected_bss else None
            ),
            qbss_station_count=(
                connected_bss.parsed_ies.qbss_station_count if connected_bss else None
            ),
            interface_stats=iface_stats,
            capabilities=capabilities,
            recent_wlan_events=wlan_events,
            roaming_events=self._roam_tracker.get_events(),
            measurement_notes=notes,
        )

    def get_last_native_snapshot(self) -> Optional[NativeWlanSnapshot]:
        return self._last_native

    async def collect_telemetry(
        self,
        *,
        include_events: bool = True,
        include_ps_driver_stats: bool = True,
        trigger_active_scan: bool = False,
    ) -> WifiInterfaceTelemetry:
        return await asyncio.to_thread(
            self.collect_telemetry_sync,
            include_events=include_events,
            include_ps_driver_stats=include_ps_driver_stats,
            trigger_active_scan=trigger_active_scan,
        )
