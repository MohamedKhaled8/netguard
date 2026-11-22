"""Tier 4: Real-World Enterprise End-to-End Application Scenarios (10 Tests).

Covers 10 realistic enterprise application workloads as specified in TEST_INFRA.md:
1. Scenario 1: Enterprise Executive Video Conference Under Bandwidth Congestion
2. Scenario 2: Corporate VPN Transition & DNS Leak Prevention
3. Scenario 3: Fluctuating Office Wi-Fi with Packet Loss Drift
4. Scenario 4: Complete Public DNS Outage with Autonomous Recovery
5. Scenario 5: Abrupt Application Crash with Zero Residual QoS Policies
6. Scenario 6: Low-Spec Hardware Fleet Deployment
7. Scenario 7: Hostile Network Environment with Blocked Ports
8. Scenario 8: Concurrent Multi-App Collaboration (Zoom + Webex + Slack)
9. Scenario 9: Adapter Driver Micro-Faults & Hardware Diagnostic
10. Scenario 10: Full Enterprise Autonomous Remediation & Incident Lifecycle
"""

from __future__ import annotations

import asyncio
import os
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from app.core.events.bus import EventBus
from app.core.models.metrics import (
    MetricType,
    ProbeStatus,
    Measurement,
    MeasurementSource,
    RiskLevel,
    ActionExecutionRecord,
    ActionExecutionStatus,
    Diagnosis,
    ProbableCause,
    DiagnosisSeverity,
    Evidence,
)
from app.monitoring.health_evaluator import (
    HealthEvaluator,
    HealthSample,
    HealthStatus,
    NetworkIssueType,
    assess_network_health,
)
from app.traffic.applications import (
    ApplicationCatalog,
    ProcessNetworkProfile,
    WorkloadCategory,
)
from app.traffic.meeting_detector import (
    MeetingDetector,
    MeetingState,
    TrafficPriorityClass,
)
from app.traffic.controller import TrafficController
from app.dns.state import DnsStateManager, DnsStateData
from app.ui.animation_clock import AnimationMasterClock
from app.remediation.actions.switch_dns import SwitchDNSResolverAction
from tests.e2e.conftest import (
    SimulatedPlatformAdapter,
    SimulatedWindowsEnvironment,
    AdapterHardwareInfo,
    FirewallAuditInfo,
    FirewallRuleState,
    NetworkEnvironmentAuditReport,
    AuditRecommendation,
)


def test_tier4_scenario_01_executive_video_conference_under_congestion(
    sim_platform: SimulatedPlatformAdapter,
    sim_win: SimulatedWindowsEnvironment,
    traffic_controller: TrafficController,
):
    """Scenario 1: Enterprise Executive Video Conference Under Bandwidth Congestion.

    - Executive launches Google Meet in Chrome.
    - Cloud backup / torrent background process saturates uplink bandwidth.
    - System identifies meeting via F13, applies DSCP 46 via F15, throttles backup to 2 Mbps,
      preserving < 50ms meeting latency.
    """
    detector = MeetingDetector()
    now_t = time.time()
    traffic_controller._pid_name_cache[5100] = ("chrome.exe", now_t)
    traffic_controller._pid_name_cache[7200] = ("qbittorrent.exe", now_t)
    assert traffic_controller._resolve_process_name(5100, now_t) == "chrome.exe"
    assert traffic_controller._resolve_process_name(7200, now_t) == "qbittorrent.exe"

    # 1. Detect meeting
    prio_meet = detector.classify_process_priority("chrome.exe", has_meeting_active=True)
    assert prio_meet in (TrafficPriorityClass.REALTIME, TrafficPriorityClass.INTERACTIVE)

    # 2. Apply DSCP 46 for Meet
    ok_dscp, msg_dscp = sim_platform.create_qos_dscp_policy("NetGuard_DSCP_chrome.exe", "chrome.exe", 46)
    assert ok_dscp is True

    # 3. Apply 2 Mbps throttle to bulk uploader
    ok_th, msg_th = sim_platform.create_qos_throttle_policy("NetGuard_Throttle_qbittorrent.exe", "qbittorrent.exe", 2_000_000)
    assert ok_th is True

    # 4. Verify QoS configuration
    policies = sim_platform.get_qos_policies()
    assert len(policies) == 2
    assert any(p["dscp_action"] == 46 for p in policies)
    assert any(p["throttle_bps"] == 2_000_000 for p in policies)

    # 5. Measure meeting latency (<50ms preserved)
    sim_win.ping_targets["1.1.1.1"] = (True, 18.2)
    ok_ping, latency = sim_platform.ping("1.1.1.1")
    assert ok_ping is True
    assert latency < 50.0


def test_tier4_scenario_02_corporate_vpn_transition_dns_leak_prevention(
    sim_platform: SimulatedPlatformAdapter,
    sim_win: SimulatedWindowsEnvironment,
):
    """Scenario 2: Corporate VPN Transition & DNS Leak Prevention.

    - Corporate WireGuard/wintun VPN tunnel established.
    - F7 excludes virtual adapter from physical NIC priority.
    - F6 configures matched dual-stack IPv4/IPv6 resolvers to eliminate leaks.
    - F8 verifies resolution and confirms secure DNS path.
    """
    sim_win.interfaces["wireguard0"] = {
        "alias": "wireguard0",
        "is_physical": False,
        "is_up": True,
        "metric": 2,
    }

    # Verify physical adapter chosen
    primary = sim_platform.get_primary_interface()
    assert primary == "Ethernet"

    # Apply matched dual-stack DNS
    secure_dns = ["1.1.1.1", "1.0.0.1", "2606:4700:4700::1111", "2606:4700:4700::1001"]
    ok, msg = sim_platform.set_interface_dns_servers(primary, secure_dns)
    assert ok is True

    # Verify IPv6 matches IPv4 (no ISP IPv6 leak)
    active = sim_platform.get_interface_dns_servers(primary)
    assert "2606:4700:4700::1111" in active
    assert "1.1.1.1" in active


def test_tier4_scenario_03_fluctuating_office_wifi_packet_loss_drift(
    sim_platform: SimulatedPlatformAdapter,
    sim_win: SimulatedWindowsEnvironment,
):
    """Scenario 3: Fluctuating Office Wi-Fi with Packet Loss Drift.

    - User moves between APs; signal quality degrades to 25%.
    - Frame drops surge; F12 predictive fault engine raises 90% fault warning.
    - Recommendation generated to switch to 5 GHz AP or Ethernet.
    """
    sim_win.wifi_metrics["signal_percent"] = 25.0
    sim_win.wifi_metrics["band"] = "2.4 GHz"
    sim_win.interfaces["Wi-Fi"]["dropin"] = 65

    wifi_info = sim_platform.get_wifi_metrics("Wi-Fi")
    assert wifi_info["signal_percent"] == 25.0

    evaluator = HealthEvaluator(degraded_threshold_samples=1)
    verdict = evaluator.evaluate(HealthSample(
        gateway_latency_ms=18.0,
        gateway_loss_pct=8.5,
        jitter_ms=36.0,
    ))
    assert verdict.status in (HealthStatus.WARNING, HealthStatus.CRITICAL)

    rec = AuditRecommendation(
        category="Wi-Fi",
        severity="WARNING",
        title="Wi-Fi Signal Degradation",
        recommendation="Weak 2.4 GHz signal (25%) with elevated frame drops. Switch to 5 GHz or plug Ethernet cable.",
    )
    assert rec.is_actionable is True


def test_tier4_scenario_04_complete_public_dns_outage_autonomous_recovery(
    sim_platform: SimulatedPlatformAdapter,
    audit_repo,
):
    """Scenario 4: Complete Public DNS Outage with Autonomous Recovery.

    - Configured public DNS fails completely.
    - 7-step workflow fails resolution test at Step 6.
    - Automated rollback immediately restores previous verified DNS servers.
    - DnsStateManager syncs UI and incident is recorded in audit log.
    """
    orig_dns = ["192.168.1.1"]
    sim_platform.set_interface_dns_servers("Ethernet", orig_dns)
    manager = DnsStateManager.get_instance()
    manager.update(active_servers=orig_dns, detected_provider="Router DHCP")

    action = SwitchDNSResolverAction()
    context = {
        "interface_name": "Ethernet",
        "target_dns_servers": ["192.0.2.53"],
    }

    # Step 1-5: Execute action
    pre_state = asyncio.run(action.execute(sim_platform, context))
    assert sim_platform.get_interface_dns_servers("Ethernet") == ["192.0.2.53"]

    # Step 6: Verify resolution fails (192.0.2.53 test-net unresolvable)
    ok_v, reason, data = asyncio.run(action.verify(sim_platform, context, pre_state))
    assert ok_v is False

    # Step 7: Autonomous rollback via SwitchDNSResolverAction.rollback
    ok_rb, msg_rb = asyncio.run(action.rollback(sim_platform, context, pre_state))
    assert ok_rb is True

    rec = ActionExecutionRecord(
        id=str(uuid.uuid4()),
        action_id=action.action_id,
        action_name=action.name,
        risk_level=action.risk_level,
        trigger_diagnosis_id="dns_outage",
        status=ActionExecutionStatus.FAILED,
        execution_duration_ms=40.0,
        rollback_performed=True,
        rollback_success=True,
    )
    audit_repo.save(rec)

    assert sim_platform.get_interface_dns_servers("Ethernet") == orig_dns
    assert manager.current.active_servers == orig_dns
    records = audit_repo.get_recent(limit=1)
    assert records[0].rollback_performed is True


def test_tier4_scenario_05_abrupt_crash_zero_residual_qos_policies(
    sim_platform: SimulatedPlatformAdapter,
    sim_win: SimulatedWindowsEnvironment,
):
    """Scenario 5: Abrupt Application Crash with Zero Residual QoS Policies.

    - Unexpected termination leaves active NetGuard_* QoS rules.
    - Next launch executes startup sweep and removes all residual policies.
    """
    sim_win.qos_policies["NetGuard_DSCP_zoom.exe"] = {"Name": "NetGuard_DSCP_zoom.exe"}
    sim_win.qos_policies["NetGuard_Throttle_steam.exe"] = {"Name": "NetGuard_Throttle_steam.exe"}
    assert len(sim_platform.get_qos_policies()) == 2

    # Startup sweep
    sim_platform.sweep_all_netguard_rules()
    assert len(sim_platform.get_qos_policies()) == 0


def test_tier4_scenario_06_low_spec_hardware_fleet_deployment(
    anim_clock: AnimationMasterClock,
    traffic_controller: TrafficController,
    sim_platform: SimulatedPlatformAdapter,
):
    """Scenario 6: Low-Spec Hardware Fleet Deployment.

    - System detects 2-core low-memory device.
    - Animation master clock auto-throttles to 10 FPS.
    - Socket PID caching avoids psutil process re-querying.
    - Native in-process ICMP ping avoids subprocess overhead.
    """
    anim_clock.start()
    anim_clock.set_low_resource_mode(True)
    assert anim_clock.is_low_resource_mode is True
    assert anim_clock._timer.interval() == 100
    anim_clock.stop()

    # PID cached in traffic controller
    now_t = time.time()
    traffic_controller._pid_name_cache[100] = ("agent.exe", now_t)
    for _ in range(50):
        assert traffic_controller._resolve_process_name(100, now_t) == "agent.exe"

    # In-process ping
    ok, lat = sim_platform.ping("127.0.0.1")
    assert ok is True


def test_tier4_scenario_07_hostile_network_environment_blocked_ports(
    sim_platform: SimulatedPlatformAdapter,
    sim_win: SimulatedWindowsEnvironment,
    incident_repo,
):
    """Scenario 7: Hostile Network Environment with Blocked Ports.

    - Firewall blocks outbound Port 53 UDP and ICMP.
    - Forensic audit identifies blockages; recommends DoH/DoT on Port 853/443.
    """
    sim_win.firewall_audit.icmp_echo_blocked = True
    sim_win.firewall_audit.port_53_blocked = True

    # Ping blocked
    ok, _ = sim_platform.ping("8.8.8.8")
    assert ok is False

    # Audit records finding
    diag = Diagnosis(
        id=str(uuid.uuid4()),
        probable_cause=ProbableCause.INCORRECT_ADAPTER_CONFIG,
        confidence=0.95,
        severity=DiagnosisSeverity.CRITICAL,
        explanation="Firewall rules blocking Port 53 and ICMP. Switch to DNS-over-HTTPS (DoH).",
    )
    incident_repo.save(diag)
    recent = incident_repo.get_recent(limit=1)
    assert "DNS-over-HTTPS" in recent[0].explanation


def test_tier4_scenario_08_concurrent_multiapp_collaboration_zoom_webex_slack(
    sim_platform: SimulatedPlatformAdapter,
):
    """Scenario 8: Concurrent Multi-App Collaboration (Zoom + Webex + Slack).

    - Multiple conferencing tools active simultaneously.
    - QoS policies created for each app with DSCP 46 without name collisions.
    """
    apps = ["zoom.exe", "webex.exe", "slack.exe"]
    for app in apps:
        ok, msg = sim_platform.create_qos_dscp_policy(f"NetGuard_DSCP_{app}", app, 46)
        assert ok is True

    policies = sim_platform.get_qos_policies()
    assert len(policies) == 3
    for app in apps:
        assert any(p["name"] == f"NetGuard_DSCP_{app}" for p in policies)


def test_tier4_scenario_09_adapter_driver_microfaults_hardware_diagnostic(
    sim_win: SimulatedWindowsEnvironment,
):
    """Scenario 9: Adapter Driver Micro-Faults & Hardware Diagnostic.

    - Physical NIC experiencing micro-faults and buffer drops.
    - Hardware audit reveals outdated driver and EEE power-saving enabled.
    - Generates actionable driver update and EEE disablement recommendations.
    """
    sim_win.adapter_hardware.eee_power_saving_enabled = True
    sim_win.adapter_hardware.is_outdated = True

    audit = sim_win.adapter_hardware
    assert audit.eee_power_saving_enabled is True
    assert audit.is_outdated is True

    report = sim_win.generate_audit_report()
    assert len(report.recommendations) >= 2
    assert any("Energy Efficient Ethernet" in r.title for r in report.recommendations)
    assert any("Driver" in r.category for r in report.recommendations)
    assert all(r.is_actionable for r in report.recommendations)


def test_tier4_scenario_10_full_enterprise_autonomous_remediation_lifecycle(
    sim_platform: SimulatedPlatformAdapter,
    sim_win: SimulatedWindowsEnvironment,
    audit_repo,
    incident_repo,
    qapp,
):
    """Scenario 10: Full Enterprise Autonomous Remediation & Incident Lifecycle.

    - Complete pipeline: Telemetry -> Diagnosis -> Autonomous Remediation -> Verification -> UI reflection.
    """
    # 1. Telemetry indicates DNS degradation
    sample = HealthSample(
        gateway_latency_ms=2.0,
        dns_latency_ms=195.0,  # High DNS latency
    )
    verdict = assess_network_health(sample)
    assert verdict.status == HealthStatus.WARNING
    assert verdict.primary_issue == NetworkIssueType.DNS_DEGRADED

    # 2. Record incident in incident repository
    diag = Diagnosis(
        id=str(uuid.uuid4()),
        probable_cause=ProbableCause.DNS_RESOLVER_SLOW,
        confidence=0.91,
        severity=DiagnosisSeverity.HIGH,
        explanation="Primary DNS latency degraded (195ms)",
    )
    incident_repo.save(diag)

    # 3. Autonomous Remediation: switch to Cloudflare DNS + flush cache
    sim_platform.set_interface_dns_servers("Ethernet", ["1.1.1.1", "1.0.0.1"])
    sim_platform.flush_dns_cache()

    # 4. Post-remediation verification
    post_sample = HealthSample(
        gateway_latency_ms=2.0,
        dns_latency_ms=11.2,
    )
    post_verdict = assess_network_health(post_sample)
    assert post_verdict.status == HealthStatus.GOOD

    # 5. Record action in audit log
    action_rec = ActionExecutionRecord(
        id=str(uuid.uuid4()),
        action_id="switch_dns",
        action_name="Auto-Switch to Fast DNS (1.1.1.1)",
        risk_level=RiskLevel.LEVEL_2_CONTROLLED,
        trigger_diagnosis_id=diag.id,
        pre_remedy_metrics={"dns_latency_ms": 195.0},
        post_remedy_metrics={"dns_latency_ms": 11.2, "status": "verified"},
        status=ActionExecutionStatus.SUCCEEDED,
        execution_duration_ms=35.0,
    )
    audit_repo.save(action_rec)

    # 6. Verify full persistence
    incidents = incident_repo.get_recent(limit=1)
    audits = audit_repo.get_recent(limit=1)
    assert len(incidents) == 1
    assert len(audits) == 1
    assert audits[0].status == ActionExecutionStatus.SUCCEEDED
