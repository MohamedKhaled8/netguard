"""Unified cross-layer bottleneck ranking engine across all 8 diagnostic fault domains."""

from __future__ import annotations

from typing import List, Optional

from app.wifi.models import (
    AccessPointScanResult,
    BufferbloatDiagnosticsReport,
    DnsDiagnosticsReport,
    FaultCategory,
    FullChannelAnalysisReport,
    MeasurementProvenance,
    NetworkDiagnosticsReport,
    RouterConfigurationSnapshot,
    SpeedTestReport,
    UnifiedDiagnosticReport,
    UnifiedFinding,
    UnifiedRecommendation,
    WifiInterfaceTelemetry,
    utc_now,
)


class UnifiedDiagnosticAnalyzer:
    """Combines RF, network baseline, DNS, throughput, bufferbloat, and router telemetry cleanly."""

    def analyze(
        self,
        *,
        telemetry: Optional[WifiInterfaceTelemetry] = None,
        scan_result: Optional[AccessPointScanResult] = None,
        channel_report: Optional[FullChannelAnalysisReport] = None,
        network_report: Optional[NetworkDiagnosticsReport] = None,
        dns_report: Optional[DnsDiagnosticsReport] = None,
        speed_report: Optional[SpeedTestReport] = None,
        bufferbloat_report: Optional[BufferbloatDiagnosticsReport] = None,
        router_config: Optional[RouterConfigurationSnapshot] = None,
    ) -> UnifiedDiagnosticReport:
        """Diagnose primary bottlenecks without fabricating unsupported claims."""
        findings: List[UnifiedFinding] = []
        recommendations: List[UnifiedRecommendation] = []

        # 1. Weak Wi-Fi signal or distance
        if telemetry and telemetry.rssi_dbm is not None and telemetry.rssi_dbm <= -72:
            sev = "critical" if telemetry.rssi_dbm <= -80 else "high"
            ev = [f"Measured RSSI={telemetry.rssi_dbm} dBm"]
            if telemetry.tx_link_rate_mbps is not None:
                ev.append(f"TX link rate={telemetry.tx_link_rate_mbps} Mbps")
            findings.append(
                UnifiedFinding(
                    finding_id="f_weak_signal",
                    category=FaultCategory.WIFI_SIGNAL_DISTANCE,
                    severity=sev,  # type: ignore[arg-type]
                    confidence=0.92,
                    title="Weak Wi-Fi signal strength",
                    summary=(
                        f"Signal is {telemetry.rssi_dbm} dBm ({telemetry.signal_quality_pct}% quality), "
                        "forcing lower modulation rates and higher packet retries."
                    ),
                    evidence=ev,
                    provenance=MeasurementProvenance.MEASURED,
                )
            )
            recommendations.append(
                UnifiedRecommendation(
                    recommendation_id="r_signal_placement",
                    priority=10,
                    scope="isp_or_hardware",
                    title="Reduce distance/obstructions or add Ethernet / wired mesh AP",
                    action_summary=(
                        "Move PC closer to router, elevate router away from thick walls/metal cabinets, "
                        "or connect via Ethernet cable / wired access point."
                    ),
                    expected_gain="Raises RSSI above -67 dBm, stabilizing PHY rate and latency.",
                    related_categories=[FaultCategory.WIFI_SIGNAL_DISTANCE],
                )
            )

        # 2. Wrong band (stuck on 2.4 GHz when 5 GHz is available & cleaner)
        if telemetry and telemetry.band == "2.4 GHz":
            caps_5g = bool(telemetry.capabilities and "5 GHz" in telemetry.capabilities.supported_bands)
            has_same_ssid_5g = bool(
                scan_result
                and telemetry.ssid
                and any(
                    ap.band == "5 GHz"
                    and ap.ssid == telemetry.ssid
                    and (ap.rssi_dbm or -100) >= -75
                    for ap in scan_result.access_points
                )
            )
            if caps_5g and (has_same_ssid_5g or (telemetry.rssi_dbm and telemetry.rssi_dbm >= -65)):
                findings.append(
                    UnifiedFinding(
                        finding_id="f_wrong_band",
                        category=FaultCategory.WRONG_BAND,
                        severity="high" if has_same_ssid_5g else "medium",
                        confidence=0.88 if has_same_ssid_5g else 0.7,
                        title="Connected to 2.4 GHz instead of 5 GHz",
                        summary=(
                            f"Adapter supports 5 GHz and RSSI is {telemetry.rssi_dbm} dBm, yet connection is on 2.4 GHz "
                            "(more crowded channels and narrow bandwidth)."
                        ),
                        evidence=[
                            f"Current band={telemetry.band}, Channel={telemetry.channel}",
                            f"Same-SSID 5 GHz BSSID nearby={has_same_ssid_5g}",
                        ],
                        provenance=MeasurementProvenance.MEASURED,
                    )
                )
                recommendations.append(
                    UnifiedRecommendation(
                        recommendation_id="r_prefer_5g",
                        priority=15,
                        scope="local_quick",
                        title="Connect to the 5 GHz SSID / Prefer 5 GHz band in adapter settings",
                        action_summary=(
                            "Switch to the router's 5 GHz Wi-Fi network (or disable band steering / split SSIDs) "
                            "when in medium/close range."
                        ),
                        expected_gain="Significantly lower neighboring AP interference and higher real throughput.",
                        related_categories=[FaultCategory.WRONG_BAND],
                    )
                )

        # 3. Wi-Fi channel congestion
        if channel_report and telemetry and telemetry.band and telemetry.channel:
            band_res = channel_report.bands.get(telemetry.band)
            if band_res and band_res.current_channel_score and band_res.recommended_channels:
                cur = band_res.current_channel_score
                best = band_res.recommended_channels[0]
                gain = cur.total_score - best.total_score
                if cur.interference_level in ("high", "severe") or gain >= 5.0:
                    findings.append(
                        UnifiedFinding(
                            finding_id="f_channel_congestion",
                            category=FaultCategory.WIFI_CHANNEL_CONGESTION,
                            severity="high" if cur.interference_level == "severe" else "medium",
                            confidence=cur.data_confidence,
                            title=f"Wi-Fi channel congestion on {telemetry.band} Ch {cur.channel}",
                            summary=(
                                f"Estimated congestion score on Ch {cur.channel} is {cur.total_score:.1f} [{cur.interference_level}]; "
                                f"Ch {best.channel} scores {best.total_score:.1f} [{best.interference_level}]."
                            ),
                            evidence=[cur.formula_notes, best.reason],
                            provenance=MeasurementProvenance.INFERRED,
                        )
                    )
                    recommendations.append(
                        UnifiedRecommendation(
                            recommendation_id="r_switch_channel",
                            priority=20,
                            scope="router_config",
                            title=f"Change router {telemetry.band} channel to Ch {best.channel}",
                            action_summary=(
                                f"Set {telemetry.band} primary channel to {best.channel} ({best.width_mhz} MHz) on the router."
                            ),
                            expected_gain=f"Reduces estimated neighbor overlap/contention by {gain:.1f} points.",
                            related_categories=[FaultCategory.WIFI_CHANNEL_CONGESTION],
                            limitations=best.limitations,
                        )
                    )

        # 4. Router bufferbloat
        if bufferbloat_report and bufferbloat_report.overall_grade in ("C", "D", "F"):
            dl_d = (
                bufferbloat_report.download_phase.delta_over_idle_ms
                if bufferbloat_report.download_phase
                else None
            )
            ul_d = (
                bufferbloat_report.upload_phase.delta_over_idle_ms
                if bufferbloat_report.upload_phase
                else None
            )
            sev = "critical" if bufferbloat_report.overall_grade in ("D", "F") else "medium"
            findings.append(
                UnifiedFinding(
                    finding_id="f_bufferbloat",
                    category=FaultCategory.ROUTER_BUFFERBLOAT,
                    severity=sev,  # type: ignore[arg-type]
                    confidence=0.9,
                    title=f"Router/WAN Bufferbloat (Grade {bufferbloat_report.overall_grade})",
                    summary=(
                        f"Latency jumped under load (DL +{dl_d} ms, UL +{ul_d} ms above idle baseline)."
                    ),
                    evidence=[bufferbloat_report.summary],
                    provenance=MeasurementProvenance.MEASURED,
                )
            )
            recommendations.append(
                UnifiedRecommendation(
                    recommendation_id="r_bufferbloat_qos",
                    priority=12,
                    scope="router_config",
                    title="Enable NetGuard PC QoS + Router SQM / Upload Shaping",
                    action_summary=(
                        "Keep NetGuard Smart QoS enabled for conferencing traffic on this PC, and enable "
                        "SQM/QoS with ~85-90% WAN bandwidth cap on the router if supported."
                    ),
                    expected_gain="Prevents bulk downloads/uploads from stalling voice and video packets.",
                    related_categories=[FaultCategory.ROUTER_BUFFERBLOAT],
                )
            )

        # 5. Slow or unreliable DNS
        if dns_report:
            conf_t = next((t for t in dns_report.targets if t.role == "configured"), None)
            if conf_t and (conf_t.status != "ok" or (conf_t.median_ms and conf_t.median_ms > 70.0) or dns_report.recommended_dns):
                findings.append(
                    UnifiedFinding(
                        finding_id="f_slow_dns",
                        category=FaultCategory.SLOW_DNS,
                        severity="medium" if conf_t.status == "ok" else "high",
                        confidence=0.85 if conf_t.sample_count >= 5 else 0.6,
                        title="Elevated DNS lookup latency or failures",
                        summary=dns_report.summary,
                        evidence=[
                            f"{conf_t.server_label}: median={conf_t.median_ms} ms, failed={conf_t.failed_samples}/{conf_t.sample_count}"
                        ],
                        provenance=MeasurementProvenance.MEASURED,
                    )
                )
                if dns_report.recommended_dns:
                    recommendations.append(
                        UnifiedRecommendation(
                            recommendation_id="r_switch_dns",
                            priority=30,
                            scope="local_quick",
                            title=f"Switch DNS resolver to {dns_report.recommended_dns} (outside meetings)",
                            action_summary=(
                                f"Apply {dns_report.recommended_dns} via NetGuard DNS section or router DHCP "
                                "when no video call is active."
                            ),
                            expected_gain="Cuts uncached DNS setup time for new connections.",
                            related_categories=[FaultCategory.SLOW_DNS],
                        )
                    )

        # 6. Local background upload / competing device activity
        if network_report and network_report.conditions.large_transfer_suspected:
            cond = network_report.conditions
            findings.append(
                UnifiedFinding(
                    finding_id="f_local_bg",
                    category=FaultCategory.LOCAL_BACKGROUND_UPLOAD,
                    severity="high" if (cond.active_interface_tx_mbps or 0.0) >= 2.0 else "medium",
                    confidence=0.85,
                    title="Heavy competing local network transfer detected",
                    summary=(
                        f"Measured baseline background throughput on {cond.active_interface}: "
                        f"DL {cond.active_interface_rx_mbps} Mbps / UL {cond.active_interface_tx_mbps} Mbps."
                    ),
                    evidence=cond.warnings,
                    provenance=MeasurementProvenance.MEASURED,
                )
            )
            recommendations.append(
                UnifiedRecommendation(
                    recommendation_id="r_pause_bg",
                    priority=8,
                    scope="local_quick",
                    title="Pause background uploads, cloud sync, or OS updates",
                    action_summary=(
                        "Pause OneDrive/Google Drive uploads, Windows Update, or torrent downloads during calls and re-test."
                    ),
                    expected_gain="Immediately frees upload queue headroom and reduces jitter.",
                    related_categories=[FaultCategory.LOCAL_BACKGROUND_UPLOAD],
                )
            )

        # 7. ISP or upstream path fault (clean gateway, degraded internet)
        if network_report:
            gw = network_report.gateway_ping
            inet = network_report.internet_ping
            if gw.status == "ok" and inet.status in ("ok", "unreachable"):
                gw_clean = gw.packet_loss_pct < 1.5 and (gw.avg_ms or 0.0) < 15.0
                inet_bad = (
                    inet.status == "unreachable"
                    or inet.packet_loss_pct >= 2.5
                    or (inet.avg_ms is not None and (inet.avg_ms - (gw.avg_ms or 0.0)) > 95.0)
                )
                if gw_clean and inet_bad:
                    findings.append(
                        UnifiedFinding(
                            finding_id="f_isp_upstream",
                            category=FaultCategory.ISP_UPSTREAM_ISSUE,
                            severity="high" if inet.packet_loss_pct >= 5.0 else "medium",
                            confidence=0.88,
                            title="Upstream ISP path degradation (local Wi-Fi/gateway is clean)",
                            summary=(
                                f"Gateway avg {gw.avg_ms} ms ({gw.packet_loss_pct}% loss), whereas "
                                f"public target {inet.target} showed {inet.avg_ms} ms ({inet.packet_loss_pct}% loss)."
                            ),
                            evidence=[
                                f"Gateway={gw.avg_ms} ms / {gw.packet_loss_pct}% loss",
                                f"Public={inet.avg_ms} ms / {inet.packet_loss_pct}% loss",
                            ],
                            provenance=MeasurementProvenance.MEASURED,
                        )
                    )
                    recommendations.append(
                        UnifiedRecommendation(
                            recommendation_id="r_isp_line_check",
                            priority=40,
                            scope="isp_or_hardware",
                            title="Inspect ISP DSL/Fiber line stats or contact ISP with Before/After report",
                            action_summary=(
                                "Because local gateway latency and loss are clean, attach this sequential test "
                                "and 5-hop trace when troubleshooting WAN/ISP routing or modem SNR."
                            ),
                            expected_gain="Targets ISP line attenuation/routing instead of tweaking Wi-Fi unnecessarily.",
                            related_categories=[FaultCategory.ISP_UPSTREAM_ISSUE],
                        )
                    )

        # 8. Windows OS / wireless driver / disconnect-roam churn
        if telemetry:
            disconnects = sum(
                1 for e in telemetry.recent_wlan_events if e.event_type == "disconnected"
            )
            stats = telemetry.interface_stats
            err_sum = ((stats.rx_errors or 0) + (stats.tx_errors or 0)) if stats else 0
            if disconnects >= 2 or err_sum >= 50 or len(telemetry.roaming_events) >= 2:
                findings.append(
                    UnifiedFinding(
                        finding_id="f_windows_driver",
                        category=FaultCategory.WINDOWS_OR_DRIVER,
                        severity="medium",
                        confidence=0.8,
                        title="Windows WLAN disconnects, roaming churn, or adapter packet errors",
                        summary=(
                            f"Observed {disconnects} recent WLAN disconnect log event(s), "
                            f"{len(telemetry.roaming_events)} session roam(s), and {err_sum} adapter packet errors."
                        ),
                        evidence=[
                            f"Adapter={telemetry.adapter_description}",
                            f"Driver={telemetry.capabilities.driver_version if telemetry.capabilities else 'unknown'}",
                        ],
                        provenance=MeasurementProvenance.MEASURED,
                    )
                )
                recommendations.append(
                    UnifiedRecommendation(
                        recommendation_id="r_driver_roam",
                        priority=25,
                        scope="local_quick",
                        title="Review Windows Wi-Fi driver version and Roaming Aggressiveness",
                        action_summary=(
                            "Update wireless driver if outdated, disable USB/PCIe Wi-Fi power saving on AC power, "
                            "and lower Roaming Aggressiveness if frequent unwanted BSSID switches occur."
                        ),
                        expected_gain="Stabilizes association and reduces multi-second roaming dropouts.",
                        related_categories=[FaultCategory.WINDOWS_OR_DRIVER],
                    )
                )

        # Sort findings by severity, recommendations by priority ascending
        sev_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        findings.sort(key=lambda f: (sev_rank.get(f.severity, 9), -f.confidence))
        recommendations.sort(key=lambda r: r.priority)

        if not findings:
            exec_summary = (
                "No severe Wi-Fi, local gateway, DNS, or bufferbloat bottleneck detected across collected metrics."
            )
        else:
            top = findings[0]
            exec_summary = f"Primary detected issue: {top.title} ({top.severity}, confidence {int(top.confidence * 100)}%)."

        return UnifiedDiagnosticReport(
            captured_at=utc_now(),
            findings=findings,
            recommendations=recommendations,
            executive_summary=exec_summary,
        )
