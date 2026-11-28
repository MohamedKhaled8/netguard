"""Frequency-based Wi-Fi channel interference and selection scoring engine."""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from app.wifi.models import (
    AccessPointScanResult,
    AdapterCapabilities,
    BandChannelAnalysisResult,
    ChannelRecommendation,
    ChannelScoreBreakdown,
    FullChannelAnalysisReport,
    NeighborAccessPoint,
    RouterConfigurationSnapshot,
    utc_now,
)
from app.wifi.telemetry import channel_to_center_freq_mhz

# Regulatory channel sets (legal baseline tables)
REG_CHANNELS_24: Dict[str, List[int]] = {
    "US": list(range(1, 12)),
    "EG": list(range(1, 14)),
    "EU": list(range(1, 14)),
    "JP": list(range(1, 15)),
    "WORLD": list(range(1, 14)),
}

REG_5GHZ_NON_DFS: Dict[str, List[int]] = {
    "US": [36, 40, 44, 48, 149, 153, 157, 161, 165],
    "EG": [36, 40, 44, 48],
    "EU": [36, 40, 44, 48],
    "JP": [36, 40, 44, 48],
    "WORLD": [36, 40, 44, 48, 149, 153, 157, 161, 165],
}

REG_5GHZ_DFS: Dict[str, List[int]] = {
    "US": [52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 144],
    "EG": [52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140],
    "EU": [52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140],
    "JP": [52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 144],
    "WORLD": [52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 144],
}

# 5 GHz IEEE bonded channel blocks (primary channels -> center frequency MHz)
_5G_40MHZ_GROUPS: List[Tuple[List[int], float]] = [
    ([36, 40], 5190.0),
    ([44, 48], 5230.0),
    ([52, 56], 5270.0),
    ([60, 64], 5310.0),
    ([100, 104], 5510.0),
    ([108, 112], 5550.0),
    ([116, 120], 5590.0),
    ([124, 128], 5630.0),
    ([132, 136], 5670.0),
    ([140, 144], 5710.0),
    ([149, 153], 5755.0),
    ([157, 161], 5795.0),
]

_5G_80MHZ_GROUPS: List[Tuple[List[int], float]] = [
    ([36, 40, 44, 48], 5210.0),
    ([52, 56, 60, 64], 5290.0),
    ([100, 104, 108, 112], 5530.0),
    ([116, 120, 124, 128], 5610.0),
    ([132, 136, 140, 144], 5690.0),
    ([149, 153, 157, 161], 5775.0),
]

_5G_160MHZ_GROUPS: List[Tuple[List[int], float]] = [
    ([36, 40, 44, 48, 52, 56, 60, 64], 5250.0),
    ([100, 104, 108, 112, 116, 120, 124, 128], 5570.0),
]

# 6 GHz PSC (Preferred Scanning Channels) for clean discovery & primary baseline
_6G_PSC_CHANNELS: List[int] = [5, 21, 37, 53, 69, 85, 101, 117, 133, 149, 165, 181, 197, 213]


def occupied_frequency_range(
    band: str,
    channel: int,
    width_mhz: int,
    *,
    secondary_offset: Optional[int] = None,
    center_seg0_channel: Optional[int] = None,
) -> Tuple[float, float, float]:
    """Return (occupied_center_mhz, low_mhz, high_mhz) accounting for bonded blocks and offsets."""
    prim_center = float(channel_to_center_freq_mhz(band, channel))
    effective_width = max(20, width_mhz)
    if band == "2.4 GHz":
        # 2.4 GHz occupied passband is ~22 MHz for DSSS/CCK or 20 MHz OFDM, 40 MHz when bonded.
        passband = 22.0 if effective_width <= 20 else 40.0
        center = prim_center
        if effective_width >= 40:
            if secondary_offset == 1:
                center = prim_center + 10.0
            elif secondary_offset == 3:
                center = prim_center - 10.0
            elif channel <= 5:
                center = prim_center + 10.0
            elif channel >= 9:
                center = prim_center - 10.0
        return center, center - passband / 2.0, center + passband / 2.0

    if band == "5 GHz":
        if center_seg0_channel and center_seg0_channel > 0 and effective_width >= 80:
            center = float(channel_to_center_freq_mhz("5 GHz", center_seg0_channel))
            return center, center - effective_width / 2.0, center + effective_width / 2.0
        groups = (
            _5G_160MHZ_GROUPS
            if effective_width >= 160
            else (_5G_80MHZ_GROUPS if effective_width == 80 else _5G_40MHZ_GROUPS)
        )
        if effective_width >= 40:
            for grp_channels, grp_center in groups:
                if channel in grp_channels:
                    return grp_center, grp_center - effective_width / 2.0, grp_center + effective_width / 2.0
            if effective_width == 40 and secondary_offset in (1, 3):
                shift = 10.0 if secondary_offset == 1 else -10.0
                center = prim_center + shift
                return center, center - 20.0, center + 20.0
        return prim_center, prim_center - 10.0, prim_center + 10.0

    if band == "6 GHz":
        if center_seg0_channel and center_seg0_channel > 0:
            center = float(channel_to_center_freq_mhz("6 GHz", center_seg0_channel))
        else:
            block_size = max(1, effective_width // 5)
            idx = max(0, (channel - 1) // block_size)
            center_ch = 1 + idx * block_size + (block_size // 2 - 2 if block_size > 4 else 0)
            center = float(channel_to_center_freq_mhz("6 GHz", center_ch)) if effective_width > 20 else prim_center
        return center, center - effective_width / 2.0, center + effective_width / 2.0

    return prim_center, prim_center - effective_width / 2.0, prim_center + effective_width / 2.0


def signal_interference_weight(rssi_dbm: Optional[int]) -> float:
    """Non-linear RF signal weight: strong nearby APs vastly outweigh distant weak APs."""
    if rssi_dbm is None:
        return 1.5  # conservative unknown weak/moderate fallback
    clamped = max(-95.0, min(-25.0, float(rssi_dbm)))
    if clamped <= -92.0:
        return 0.15
    normalized = (clamped + 95.0) / 10.0  # 0.3 .. 7.0
    return round(math.pow(normalized, 1.75), 3)


def _classify_interference(score: float) -> str:
    if score < 8.0:
        return "low"
    if score < 22.0:
        return "moderate"
    if score < 45.0:
        return "high"
    return "severe"


class ChannelAnalysisEngine:
    """Frequency-overlap RF interference and channel recommendation calculator."""

    @staticmethod
    def _permitted_channels_for_band(
        band: str,
        reg_domain: str,
        observed_aps: List[NeighborAccessPoint],
    ) -> Tuple[List[int], List[int]]:
        """Return (all_permitted_channels, dfs_channels) for regulatory domain + observed cues."""
        dom = reg_domain.upper()
        if dom not in REG_CHANNELS_24:
            dom = "EU" if dom in {"GB", "DE", "FR", "IT", "ES", "NL", "AE", "SA"} else "WORLD"

        if band == "2.4 GHz":
            return list(REG_CHANNELS_24.get(dom, REG_CHANNELS_24["EG"])), []

        if band == "5 GHz":
            non_dfs = list(REG_5GHZ_NON_DFS.get(dom, REG_5GHZ_NON_DFS["EG"]))
            dfs = list(REG_5GHZ_DFS.get(dom, REG_5GHZ_DFS["EG"]))
            # If nearby APs in this country advertize valid in_reg_domain UNII-3 channels (149..165), include them.
            for ap in observed_aps:
                if (
                    ap.band == "5 GHz"
                    and ap.in_reg_domain is True
                    and ap.channel in (149, 153, 157, 161, 165)
                    and ap.channel not in non_dfs
                ):
                    non_dfs.append(ap.channel)
            all_ch = sorted(set(non_dfs + dfs))
            return all_ch, sorted(set(dfs))

        if band == "6 GHz":
            return list(_6G_PSC_CHANNELS), []

        return [], []

    @staticmethod
    def _width_supports_channel(band: str, channel: int, width_mhz: int) -> bool:
        if band == "2.4 GHz":
            if width_mhz <= 20:
                return True
            if width_mhz == 40:
                return channel in list(range(1, 14))
            return False
        if band == "5 GHz":
            if width_mhz <= 20:
                return True
            if width_mhz == 40:
                return any(channel in g[0] for g in _5G_40MHZ_GROUPS)
            if width_mhz == 80:
                return any(channel in g[0] for g in _5G_80MHZ_GROUPS)
            if width_mhz == 160:
                return any(channel in g[0] for g in _5G_160MHZ_GROUPS)
            return False
        if band == "6 GHz":
            return width_mhz in (20, 40, 80, 160)
        return False

    def score_channel(
        self,
        *,
        band: str,
        channel: int,
        width_mhz: int,
        target_width_mhz: Optional[int] = None,
        regulatory_domain: str,
        is_dfs: bool,
        is_reg_permitted: bool,
        is_adapter_supported: bool,
        current_channel: Optional[int],
        connected_bssid: Optional[str],
        band_aps: List[NeighborAccessPoint],
        data_confidence: float,
    ) -> ChannelScoreBreakdown:
        """Compute inspectable interference breakdown for a candidate (band, channel, width)."""
        cand_center, cand_lo, cand_hi = occupied_frequency_range(band, channel, width_mhz)
        cand_width = max(20.0, cand_hi - cand_lo)

        co_contrib = 0.0
        adj_contrib = 0.0
        co_count = 0
        overlap_count = 0
        strong_interferers: List[Dict[str, object]] = []

        for ap in band_aps:
            if connected_bssid and ap.bssid.lower() == connected_bssid.lower():
                continue

            ap_width = ap.channel_width_mhz or 20
            ap_center, ap_lo, ap_hi = occupied_frequency_range(
                ap.band,
                ap.channel,
                ap_width,
                secondary_offset=ap.secondary_channel_offset,
                center_seg0_channel=ap.center_freq_seg0_channel,
            )

            overlap_mhz = max(0.0, min(cand_hi, ap_hi) - max(cand_lo, ap_lo))
            skirt_mhz = max(0.0, min(cand_hi + 2.5, ap_hi + 2.5) - max(cand_lo - 2.5, ap_lo - 2.5))
            if overlap_mhz <= 0.0 and skirt_mhz <= 0.0:
                continue

            w_sig = signal_interference_weight(ap.rssi_dbm)
            qbss_boost = 1.0
            if ap.qbss_utilization_pct is not None:
                qbss_boost = 0.75 + (ap.qbss_utilization_pct / 50.0)

            same_primary = ap.channel == channel or abs(ap_center - cand_center) < 1.0
            if same_primary and overlap_mhz > 0:
                co_count += 1
                overlap_count += 1
                contrib = round(w_sig * qbss_boost * 1.0, 2)
                co_contrib += contrib
                kind = "co_channel"
                frac = 1.0
            elif overlap_mhz > 0:
                overlap_count += 1
                min_span = max(20.0, min(cand_width, max(20.0, ap_hi - ap_lo)))
                frac = min(1.0, overlap_mhz / min_span)
                # On 2.4 GHz, partial overlap breaks CSMA/CA coordination (OBSS interference).
                obss_mult = 1.25 if (band == "2.4 GHz" and frac < 0.99) else 0.90
                contrib = round(w_sig * frac * obss_mult * qbss_boost, 2)
                adj_contrib += contrib
                kind = "overlapping"
            else:
                # Immediately adjacent spectral mask rolloff
                frac = round((skirt_mhz / 5.0) * 0.12, 3)
                contrib = round(w_sig * frac * qbss_boost, 2)
                adj_contrib += contrib
                kind = "adjacent_skirt"

            if contrib >= 1.5 or (ap.rssi_dbm is not None and ap.rssi_dbm >= -75):
                strong_interferers.append(
                    {
                        "ssid": ap.ssid or "<hidden>",
                        "bssid": ap.bssid,
                        "channel": ap.channel,
                        "width_mhz": ap.channel_width_mhz,
                        "rssi_dbm": ap.rssi_dbm,
                        "type": kind,
                        "overlap_fraction": round(frac, 2),
                        "contribution": contrib,
                    }
                )

        # Width tradeoffs (spectral footprint, OBSS risk, and bandwidth shortfall vs target width)
        req_w = target_width_mhz or width_mhz
        if band == "2.4 GHz":
            width_penalty = 14.0 if width_mhz >= 40 else 0.0
        elif band == "5 GHz":
            width_penalty = {20: 0.0, 40: 1.5, 80: 4.0, 160: 10.0}.get(width_mhz, 2.0)
            if width_mhz < req_w:
                width_penalty += 6.0  # Channel cannot bond to requested 80/40 MHz bandwidth
        else:
            width_penalty = {20: 0.0, 40: 0.5, 80: 1.5, 160: 4.0}.get(width_mhz, 2.0)
            if width_mhz < req_w:
                width_penalty += 4.0

        dfs_penalty = 5.0 if is_dfs else 0.0
        reg_penalty = 0.0 if is_reg_permitted else 100.0
        cap_penalty = 0.0 if is_adapter_supported else 100.0

        total = round(
            co_contrib + adj_contrib + width_penalty + dfs_penalty + reg_penalty + cap_penalty,
            2,
        )

        strong_interferers.sort(key=lambda item: float(item["contribution"]), reverse=True)
        conf_label = (
            "high" if data_confidence >= 0.75 else ("medium" if data_confidence >= 0.45 else "low")
        )

        formula_notes = (
            f"total={total:.2f} = co({co_contrib:.2f}) + adj({adj_contrib:.2f}) "
            f"+ width({width_penalty:.1f}) + dfs({dfs_penalty:.1f})"
        )

        return ChannelScoreBreakdown(
            band=band,
            channel=channel,
            center_frequency_mhz=int(round(cand_center)),
            width_mhz=width_mhz,
            occupied_range_mhz=(round(cand_lo, 1), round(cand_hi, 1)),
            is_dfs=is_dfs,
            is_reg_permitted=is_reg_permitted,
            is_adapter_supported=is_adapter_supported,
            is_current_channel=(current_channel == channel),
            total_score=total,
            interference_level=_classify_interference(total),  # type: ignore[arg-type]
            co_channel_ap_count=co_count,
            overlapping_ap_count=overlap_count,
            co_channel_contribution=round(co_contrib, 2),
            adjacent_overlap_contribution=round(adj_contrib, 2),
            width_penalty=width_penalty,
            dfs_caution_penalty=dfs_penalty,
            strong_interferers=strong_interferers[:6],
            data_confidence=round(data_confidence, 2),
            confidence_label=conf_label,  # type: ignore[arg-type]
            formula_notes=formula_notes,
        )

    def analyze_band(
        self,
        *,
        band: str,
        scan_result: AccessPointScanResult,
        target_width_mhz: Optional[int] = None,
        current_channel: Optional[int] = None,
        connected_bssid: Optional[str] = None,
        adapter_caps: Optional[AdapterCapabilities] = None,
        router_config: Optional[RouterConfigurationSnapshot] = None,
    ) -> BandChannelAnalysisResult:
        """Score every permitted channel in one band and synthesize top recommendations."""
        reg_domain = scan_result.regulatory_domain or "EG"
        if adapter_caps and adapter_caps.regulatory_domain:
            reg_domain = adapter_caps.regulatory_domain

        # Default target channel width safely
        width_mhz = target_width_mhz
        if width_mhz is None:
            if band == "2.4 GHz":
                width_mhz = 20
            elif band == "5 GHz":
                width_mhz = 80 if (not adapter_caps or (adapter_caps.max_channel_width_mhz or 80) >= 80) else 40
            else:
                width_mhz = 80

        if adapter_caps and adapter_caps.max_channel_width_mhz:
            width_mhz = min(width_mhz, adapter_caps.max_channel_width_mhz)

        band_aps = [ap for ap in scan_result.access_points if ap.band == band]

        # Assess scan data confidence honestly
        width_known_ratio = (
            sum(1 for ap in band_aps if ap.channel_width_mhz is not None) / len(band_aps)
            if band_aps
            else 0.5
        )
        country_known = any(ap.country_code for ap in scan_result.access_points)
        qbss_ratio = (
            sum(1 for ap in band_aps if ap.qbss_utilization_pct is not None) / len(band_aps)
            if band_aps
            else 0.0
        )
        active_boost = 0.15 if scan_result.scan_mode == "active_wlan_scan" else 0.05
        confidence = min(
            0.95,
            0.40 + 0.25 * width_known_ratio + (0.15 if country_known else 0.0) + 0.10 * qbss_ratio + active_boost,
        )
        if scan_result.total_bss_count == 0:
            confidence = 0.2

        permitted, dfs_channels = self._permitted_channels_for_band(
            band, reg_domain, scan_result.access_points
        )

        adapter_band_ok = True
        if adapter_caps and adapter_caps.supported_bands and band not in adapter_caps.supported_bands:
            adapter_band_ok = False

        scores: List[ChannelScoreBreakdown] = []
        for ch in permitted:
            eff_w = width_mhz
            if not self._width_supports_channel(band, ch, eff_w):
                # Channel doesn't support full width (e.g. Ch 165 only 20 MHz); evaluate at highest valid width.
                if self._width_supports_channel(band, ch, 40):
                    eff_w = 40
                else:
                    eff_w = 20

            is_dfs = ch in dfs_channels
            sc = self.score_channel(
                band=band,
                channel=ch,
                width_mhz=eff_w,
                target_width_mhz=width_mhz,
                regulatory_domain=reg_domain,
                is_dfs=is_dfs,
                is_reg_permitted=True,
                is_adapter_supported=adapter_band_ok,
                current_channel=current_channel,
                connected_bssid=connected_bssid,
                band_aps=band_aps,
                data_confidence=confidence,
            )
            scores.append(sc)

        # Rank scores ascending (lower congestion estimate is better).
        # On 2.4 GHz, strongly prefer orthogonal primary channels {1, 6, 11} when ranking recommendations
        # unless a massive score advantage proves otherwise, while still showing all channels transparently.
        def _rank_key(item: ChannelScoreBreakdown) -> Tuple[float, float, int]:
            non_orthog_bias = (
                2.5 if (band == "2.4 GHz" and item.channel not in (1, 6, 11, 13)) else 0.0
            )
            return (item.total_score + non_orthog_bias, item.co_channel_contribution, item.channel)

        ranked = sorted(scores, key=_rank_key)
        current_score = next((s for s in scores if s.channel == current_channel), None)

        recommendations: List[ChannelRecommendation] = []
        seen_bonded_centers: set[int] = set()
        for sc in ranked:
            # Avoid duplicating the same 80 MHz block four times in top recommendations
            if band == "5 GHz" and sc.width_mhz >= 80 and sc.center_frequency_mhz in seen_bonded_centers:
                continue
            seen_bonded_centers.add(sc.center_frequency_mhz)

            rank_idx = len(recommendations) + 1
            advantages: List[str] = []
            limitations: List[str] = []

            if sc.co_channel_ap_count == 0 and sc.adjacent_overlap_contribution < 2.0:
                advantages.append("Minimal co-channel and adjacent spectral overlap observed in scan.")
            elif sc.co_channel_ap_count == 0:
                advantages.append("No same-channel neighboring AP detected.")
            if current_score and sc.total_score + 3.0 < current_score.total_score:
                advantages.append(
                    f"Lower estimated interference than current channel {current_channel} "
                    f"({sc.total_score:.1f} vs {current_score.total_score:.1f})."
                )
            if band == "2.4 GHz" and sc.channel in (1, 6, 11):
                advantages.append("Non-overlapping standard 20 MHz channel preserves 2.4 GHz orthogonality.")
            if not sc.is_dfs and band == "5 GHz":
                advantages.append("Non-DFS channel avoids radar CAC delays and unexpected channel jumps.")

            if sc.is_dfs:
                limitations.append(
                    "DFS channel: requires 60s radar check on startup and may vacate automatically if radar is detected."
                )
            if sc.strong_interferers:
                top_ap = sc.strong_interferers[0]
                limitations.append(
                    f"Affected by neighbor '{top_ap['ssid']}' (Ch {top_ap['channel']}, {top_ap['rssi_dbm']} dBm)."
                )
            if sc.width_mhz < width_mhz:
                limitations.append(
                    f"Channel {sc.channel} limits bandwidth to {sc.width_mhz} MHz instead of {width_mhz} MHz."
                )
            if router_config and router_config.vendor:
                limitations.append(
                    f"Verify {router_config.vendor} router UI permits channel {sc.channel} in region {reg_domain}."
                )
            limitations.append(
                "Based on scan-visible beacon interference; hidden non-Wi-Fi noise is not directly measurable."
            )

            reason = (
                f"Channel {sc.channel} ({sc.width_mhz} MHz) achieved score {sc.total_score:.1f} "
                f"[{sc.interference_level}] with co-channel {sc.co_channel_contribution:.1f} and "
                f"overlap {sc.adjacent_overlap_contribution:.1f}."
            )

            recommendations.append(
                ChannelRecommendation(
                    rank=rank_idx,
                    band=band,
                    channel=sc.channel,
                    width_mhz=sc.width_mhz,
                    total_score=sc.total_score,
                    interference_level=sc.interference_level,
                    is_current_channel=sc.is_current_channel,
                    is_dfs=sc.is_dfs,
                    strong_interfering_aps=sc.strong_interferers,
                    co_channel_contribution=sc.co_channel_contribution,
                    adjacent_overlap_contribution=sc.adjacent_overlap_contribution,
                    channel_width_impact=sc.width_penalty,
                    data_confidence=sc.data_confidence,
                    confidence_label=sc.confidence_label,
                    reason=reason,
                    advantages=advantages,
                    limitations=limitations,
                )
            )
            if len(recommendations) >= 4:
                break

        completeness_notes = [
            f"Regulatory table applied: {reg_domain} ({len(permitted)} channels evaluated).",
            f"Scan mode: {scan_result.scan_mode}; {len(band_aps)} BSSIDs observed in {band}.",
            f"Channel width IE coverage: {int(width_known_ratio * 100)}% of detected {band} BSSIDs.",
        ]
        if qbss_ratio == 0.0 and band_aps:
            completeness_notes.append(
                "Neighbor APs did not advertise QBSS Load (IE 11); congestion estimate weights RSSI + spectral overlap."
            )

        return BandChannelAnalysisResult(
            band=band,
            target_width_mhz=width_mhz,
            regulatory_domain=reg_domain,
            current_channel=current_channel,
            current_channel_score=current_score,
            channel_scores=scores,
            recommended_channels=recommendations,
            data_confidence=round(confidence, 2),
            scan_completeness_notes=completeness_notes,
        )

    def analyze(
        self,
        *,
        scan_result: AccessPointScanResult,
        current_band: Optional[str] = None,
        current_channel: Optional[int] = None,
        connected_bssid: Optional[str] = None,
        adapter_caps: Optional[AdapterCapabilities] = None,
        router_config: Optional[RouterConfigurationSnapshot] = None,
    ) -> FullChannelAnalysisReport:
        """Analyze 2.4 GHz, 5 GHz (and 6 GHz when supported/visible) uniformly."""
        bands_to_eval = ["2.4 GHz", "5 GHz"]
        if (
            (adapter_caps and adapter_caps.supports_6ghz)
            or any(ap.band == "6 GHz" for ap in scan_result.access_points)
            or current_band == "6 GHz"
        ):
            bands_to_eval.append("6 GHz")

        band_results: Dict[str, BandChannelAnalysisResult] = {}
        for band in bands_to_eval:
            ch_for_band = current_channel if current_band == band else None
            band_results[band] = self.analyze_band(
                band=band,
                scan_result=scan_result,
                current_channel=ch_for_band,
                connected_bssid=connected_bssid,
                adapter_caps=adapter_caps,
                router_config=router_config,
            )

        summary_parts: List[str] = []
        for band, res in band_results.items():
            if res.recommended_channels:
                best = res.recommended_channels[0]
                summary_parts.append(
                    f"{band}: best Ch {best.channel} ({best.width_mhz} MHz, score {best.total_score:.1f} {best.interference_level})"
                )

        return FullChannelAnalysisReport(
            captured_at=utc_now(),
            regulatory_domain=scan_result.regulatory_domain,
            bands=band_results,
            overall_summary="; ".join(summary_parts) or "No channels analyzed.",
        )
