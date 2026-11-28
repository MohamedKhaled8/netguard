"""Unit tests for 802.11 IE decoding, non-fabricated Wi-Fi telemetry, and RF channel scoring."""

from __future__ import annotations

from app.wifi.channel_analysis import (
    ChannelAnalysisEngine,
    occupied_frequency_range,
    signal_interference_weight,
)
from app.wifi.models import (
    AccessPointScanResult,
    AdapterCapabilities,
    MeasurementProvenance,
    NeighborAccessPoint,
)
from app.wifi.telemetry import (
    WifiRoamTracker,
    parse_80211_ies,
    parse_wlan_event_xml,
)


def _ie(ie_id: int, payload: bytes) -> bytes:
    return bytes([ie_id, len(payload)]) + payload


def test_parse_80211_ies_ht_vht_160_qbss_rsn() -> None:
    # Build realistic beacon IE bundle: SSID + Country EG + QBSS + HT Cap + HT Op + VHT Cap + VHT Op 160MHz + RSN
    ssid_ie = _ie(0, b"HomeNet_5G")
    country_ie = _ie(7, b"EG \x24\x04\x17")
    # QBSS: 4 stations, 128/255 (~50.2%) utilization
    qbss_ie = _ie(11, (4).to_bytes(2, "little") + bytes([128]) + (0).to_bytes(2, "little"))
    # HT Cap: bit 1=1 (40 MHz), MCS bytes 0..1 non-zero -> 2 streams
    ht_cap_payload = (0x0002).to_bytes(2, "little") + b"\x00" + bytes([0xFF, 0xFF] + [0] * 14) + b"\x00" * 7
    ht_cap_ie = _ie(45, ht_cap_payload[:26])
    # HT Op: primary 36, offset=1 (above), sta_width_any=1
    ht_op_ie = _ie(61, bytes([36, 0x05]) + b"\x00" * 20)
    # VHT Cap: supp width=1 (160 MHz), 2 streams supported (0xFFFA -> SS1=2, SS2=2, SS3..8=3)
    vht_cap_payload = (0x00000004).to_bytes(4, "little") + (0xFFFA).to_bytes(2, "little") + b"\x00" * 6
    vht_cap_ie = _ie(191, vht_cap_payload)
    # VHT Op: ch_width=1, seg0=42, seg1=50 -> abs(50-42)==8 => 160 MHz!
    vht_op_ie = _ie(192, bytes([1, 42, 50, 0, 0]))
    # RSN: WPA2 + SAE (AKM 2 & 8)
    rsn_payload = (
        (1).to_bytes(2, "little")
        + b"\x00\x0f\xac\x04"
        + (1).to_bytes(2, "little")
        + b"\x00\x0f\xac\x04"
        + (2).to_bytes(2, "little")
        + b"\x00\x0f\xac\x02\x00\x0f\xac\x08"
    )
    rsn_ie = _ie(48, rsn_payload)

    parsed = parse_80211_ies(
        ssid_ie + country_ie + qbss_ie + ht_cap_ie + ht_op_ie + vht_cap_ie + vht_op_ie + rsn_ie
    )
    assert parsed.ssid == "HomeNet_5G"
    assert not parsed.is_hidden_ssid
    assert parsed.country_code == "EG"
    assert parsed.qbss_station_count == 4
    assert parsed.qbss_utilization_pct is not None and 49.0 <= parsed.qbss_utilization_pct <= 51.0
    assert parsed.inferred_width_mhz == 160
    assert parsed.inferred_phy_standard == "802.11ac"
    assert parsed.max_spatial_streams == 2
    assert parsed.security_mode == "WPA2/WPA3-PSK"


def test_roam_tracker_and_wlan_xml_parser() -> None:
    tracker = WifiRoamTracker()
    assert tracker.observe(ssid="Corp", bssid="aa:bb:cc:00:00:01", channel=36, band="5 GHz", rssi_dbm=-62) is None
    # Same BSSID -> no roam event
    assert tracker.observe(ssid="Corp", bssid="aa:bb:cc:00:00:01", channel=36, band="5 GHz", rssi_dbm=-63) is None
    # BSSID switch -> recorded roam event
    roam = tracker.observe(ssid="Corp", bssid="aa:bb:cc:00:00:02", channel=149, band="5 GHz", rssi_dbm=-55)
    assert roam is not None
    assert roam.from_bssid == "aa:bb:cc:00:00:01"
    assert roam.to_bssid == "aa:bb:cc:00:00:02"

    xml_sample = """
    <Event xmlns='http://schemas.microsoft.com/win/2004/08/events/event'>
      <System><EventID>8002</EventID><TimeCreated SystemTime='2026-11-26T10:15:00.000Z'/></System>
      <EventData>
        <Data Name='InterfaceName'>Wi-Fi</Data>
        <Data Name='SSID'>TestNet</Data>
        <Data Name='BSSID'>11:22:33:44:55:66</Data>
        <Data Name='ReasonCode'>0x0003</Data>
      </EventData>
    </Event>
    """
    events = parse_wlan_event_xml(xml_sample)
    assert len(events) == 1
    assert events[0].event_type == "disconnected"
    assert events[0].ssid == "TestNet"
    assert events[0].reason_code == "0x0003"


def test_occupied_frequency_overlap_and_strong_signal_vs_ap_count() -> None:
    # 2.4 GHz Ch 1 [2401..2423], Ch 3 [2411..2433] -> real frequency overlap; Ch 6 [2426..2448] -> non-overlapping
    _, l1, h1 = occupied_frequency_range("2.4 GHz", 1, 20)
    _, l3, h3 = occupied_frequency_range("2.4 GHz", 3, 20)
    _, l6, h6 = occupied_frequency_range("2.4 GHz", 6, 20)
    assert min(h1, h3) - max(l1, l3) > 10.0  # Ch 1 and Ch 3 collide significantly
    assert min(h1, h6) - max(l1, l6) <= 0.0   # Ch 1 and Ch 6 do not overlap main passband

    # Signal weight monotonicity & dominance over distant beacons
    assert signal_interference_weight(-45) > 5 * signal_interference_weight(-90)

    # Channel 1 has ONLY 1 VERY STRONG neighbor (-44 dBm); Channel 11 has 4 VERY WEAK distant neighbors (-90 dBm)
    aps = [
        NeighborAccessPoint(
            ssid="LoudNextDoor",
            bssid="00:11:22:33:44:01",
            band="2.4 GHz",
            channel=1,
            center_frequency_mhz=2412,
            channel_width_mhz=20,
            rssi_dbm=-44,
        ),
    ] + [
        NeighborAccessPoint(
            ssid=f"Distant_{i}",
            bssid=f"00:11:22:33:55:0{i}",
            band="2.4 GHz",
            channel=11,
            center_frequency_mhz=2462,
            channel_width_mhz=20,
            rssi_dbm=-90,
        )
        for i in range(4)
    ]

    scan = AccessPointScanResult(regulatory_domain="EG", total_bss_count=len(aps), access_points=aps)
    engine = ChannelAnalysisEngine()
    res = engine.analyze_band(band="2.4 GHz", scan_result=scan, target_width_mhz=20)

    sc_ch1 = next(s for s in res.channel_scores if s.channel == 1)
    sc_ch6 = next(s for s in res.channel_scores if s.channel == 6)
    sc_ch11 = next(s for s in res.channel_scores if s.channel == 11)

    # CRITICAL REQUIREMENT: fewer but strong overlapping APs score WORSE than many distant weak APs
    assert sc_ch1.total_score > sc_ch11.total_score
    assert sc_ch6.total_score < sc_ch1.total_score
    assert res.recommended_channels[0].channel in (6, 11, 13)
    assert res.recommended_channels[0].channel != 1
    assert "do not measure" in res.estimated_notice.lower()


def test_5ghz_wider_bonded_spectrum_and_own_bssid_exclusion() -> None:
    own_bssid = "f8:95:22:82:bf:78"
    aps = [
        # User's own router on Ch 36 (80 MHz block 36..48) -> must NOT count against Ch 44!
        NeighborAccessPoint(
            ssid="MyNet",
            bssid=own_bssid,
            band="5 GHz",
            channel=36,
            center_frequency_mhz=5180,
            channel_width_mhz=80,
            rssi_dbm=-42,
            is_connected_ap=True,
        ),
        # Neighbor AP sitting on Ch 40 with 20 MHz overlaps our 80 MHz block (36..48) without sharing same primary channel!
        NeighborAccessPoint(
            ssid="Neighbor20MHzInBlock",
            bssid="aa:bb:cc:dd:ee:02",
            band="5 GHz",
            channel=40,
            center_frequency_mhz=5200,
            channel_width_mhz=20,
            rssi_dbm=-55,
        ),
    ]
    scan = AccessPointScanResult(regulatory_domain="US", total_bss_count=len(aps), access_points=aps)
    caps = AdapterCapabilities(
        interface_name="Wi-Fi",
        supported_bands=["2.4 GHz", "5 GHz"],
        max_channel_width_mhz=80,
        regulatory_domain="US",
    )
    res = ChannelAnalysisEngine().analyze_band(
        band="5 GHz",
        scan_result=scan,
        target_width_mhz=80,
        current_channel=44,
        connected_bssid=own_bssid,
        adapter_caps=caps,
    )

    sc_44 = next(s for s in res.channel_scores if s.channel == 44)
    sc_149 = next(s for s in res.channel_scores if s.channel == 149)
    # Ch 44 has overlap from Neighbor80MHz on Ch 40; Ch 149 (non-DFS UNII-3) is totally clear!
    assert sc_44.adjacent_overlap_contribution > 5.0
    assert sc_44.co_channel_ap_count == 0  # Own AP on Ch 36 excluded, neighbor is on Ch 40
    assert sc_149.total_score < sc_44.total_score
    assert res.recommended_channels[0].channel == 149


def test_telemetry_service_never_invents_noise_floor_or_snr() -> None:
    from app.wifi.telemetry import WifiTelemetryService

    svc = WifiTelemetryService()
    tel = svc.collect_telemetry_sync(include_events=False, include_ps_driver_stats=False)
    # Regardless of host Wi-Fi connection state, noise_floor & SNR MUST remain None unless genuinely provided
    assert tel.noise_floor_dbm is None
    assert tel.noise_floor_provenance == MeasurementProvenance.UNAVAILABLE
    assert "rssi" in tel.noise_floor_reason.lower()
    assert tel.snr_db is None
    assert tel.snr_provenance == MeasurementProvenance.UNAVAILABLE
    assert tel.mcs_index is None
    assert tel.mcs_provenance == MeasurementProvenance.UNAVAILABLE
