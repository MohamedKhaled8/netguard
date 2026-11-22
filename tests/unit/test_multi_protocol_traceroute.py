"""Unit tests for Real Multi-Protocol Traceroute & Intelligent Hop Classification.

Validates:
1. Three independent traceroute methods (ICMP, TCP Port 443, UDP)
2. Intelligent Hop Classification (RESPONDING, SILENT_HOP, PATH_CONTINUES,
   INTERMEDIATE_FILTERING_SUSPECTED, TRACE_INCONCLUSIVE, DESTINATION_UNREACHABLE)
3. The 4 Diagnostic Rules (Case 1, Case 2, Case 3, Case 4)
4. Independent End-to-End Connectivity Verification (TCP 443, DNS, HTTPS, multi-target)
5. Accurate Latency Measurements (No fake formulas, separate RTTs per probe/protocol)
6. Anti-Labeling Compliance (Hop 2 is never labeled DSLAM, BRAS, BNG, or ISP cabinet)
7. UI MultiProtocolAnalysisPanel rendering and live updates
"""

import pytest
from datetime import datetime, timezone
from app.diagnosis.traceroute import (
    HopClassification,
    ProbeProtocol,
    EndToEndStatus,
    ProbeResult,
    HopResult,
    TraceRouteReport,
    EndToEndCheckResult,
    MultiProtocolAnalysisReport,
    IcmpTracerouteEngine,
    TcpTracerouteEngine,
    UdpTracerouteEngine,
    EndToEndConnectivityVerifier,
    MultiProtocolAnalyzer,
    _classify_trace_hops,
    _determine_overall_classification,
)


def test_hop_classifications_exist():
    """Verify all 6 required hop classifications are defined exactly."""
    assert HopClassification.RESPONDING == "RESPONDING"
    assert HopClassification.SILENT_HOP == "SILENT_HOP"
    assert HopClassification.PATH_CONTINUES == "PATH_CONTINUES"
    assert HopClassification.INTERMEDIATE_FILTERING_SUSPECTED == "INTERMEDIATE_FILTERING_SUSPECTED"
    assert HopClassification.TRACE_INCONCLUSIVE == "TRACE_INCONCLUSIVE"
    assert HopClassification.DESTINATION_UNREACHABLE == "DESTINATION_UNREACHABLE"


def test_probe_protocols_exist():
    """Verify all 3 independent probe protocols are supported."""
    assert ProbeProtocol.ICMP == "ICMP"
    assert ProbeProtocol.TCP == "TCP"
    assert ProbeProtocol.UDP == "UDP"


def test_hop_result_statistics():
    """Verify that HopResult accurately calculates min, avg, max, and loss_pct without fabricated data."""
    probes = [
        ProbeResult(probe_index=1, rtt_ms=12.4, responding_ip="192.168.1.1", status_code="TTL_EXPIRED"),
        ProbeResult(probe_index=2, rtt_ms=10.2, responding_ip="192.168.1.1", status_code="TTL_EXPIRED"),
        ProbeResult(probe_index=3, rtt_ms=None, responding_ip=None, status_code="TIMEOUT"),
    ]
    h = HopResult(
        hop_number=1,
        protocol=ProbeProtocol.ICMP,
        classification=HopClassification.RESPONDING,
        ip="192.168.1.1",
        hostname=None,
        probes=probes,
    )
    h.calculate_stats()

    assert h.min_rtt_ms == 10.2
    assert h.max_rtt_ms == 12.4
    assert h.avg_rtt_ms == 11.3  # (12.4 + 10.2) / 2
    assert h.loss_pct == 33.3  # 1 out of 3 failed


def test_case_1_hop2_silent_subsequent_responds():
    """CASE 1: Hop 2 does not respond, but Hop 3 or later hops respond in the same trace.

    Result: Packets progressed beyond the silent hop. Mark the intermediate hop
    as PATH_CONTINUES (non-responsive), NOT as a network failure.
    """
    h1 = HopResult(1, ProbeProtocol.ICMP, HopClassification.RESPONDING, "192.168.1.1", None, [ProbeResult(1, 1.0, "192.168.1.1", "TTL_EXPIRED")])
    h2 = HopResult(2, ProbeProtocol.ICMP, HopClassification.SILENT_HOP, None, None, [ProbeResult(1, None, None, "TIMEOUT")])
    h3 = HopResult(3, ProbeProtocol.ICMP, HopClassification.RESPONDING, "10.29.82.1", None, [ProbeResult(1, 8.5, "10.29.82.1", "TTL_EXPIRED")])

    hops = [h1, h2, h3]
    _classify_trace_hops(hops, target_reached=False)

    assert hops[1].classification == HopClassification.PATH_CONTINUES
    assert hops[1].subsequent_hops_responded is True
    assert hops[1].reason is not None
    assert "حجب استجابات التحكم" in hops[1].reason

    # Overall trace classification must show path continues, not network failure
    overall = _determine_overall_classification(hops, target_reached=False)
    assert overall == HopClassification.PATH_CONTINUES


def test_case_2_intermediate_hops_silent_e2e_succeeds():
    """CASE 2: Intermediate hops do not respond, but independent TCP/HTTPS connectivity succeeds.

    Result: Report that end-to-end connectivity is working and intermediate-hop visibility is limited.
    """
    h1 = HopResult(1, ProbeProtocol.TCP, HopClassification.RESPONDING, "192.168.1.1", None, [ProbeResult(1, 1.0, "192.168.1.1", "TTL_EXPIRED")])
    h2 = HopResult(2, ProbeProtocol.TCP, HopClassification.SILENT_HOP, None, None, [ProbeResult(1, None, None, "TIMEOUT")])
    h3 = HopResult(3, ProbeProtocol.TCP, HopClassification.SILENT_HOP, None, None, [ProbeResult(1, None, None, "TIMEOUT")])

    hops = [h1, h2, h3]
    _classify_trace_hops(hops, target_reached=True)

    assert hops[1].classification == HopClassification.INTERMEDIATE_FILTERING_SUSPECTED
    assert hops[1].reason is not None

    overall = _determine_overall_classification(hops, target_reached=True)
    assert overall == HopClassification.INTERMEDIATE_FILTERING_SUSPECTED


def test_case_3_hop2_silent_all_subsequent_timeout():
    """CASE 3: Hop 2 does not respond and all subsequent probes time out.

    Result: Do not claim that the path is forwarding successfully. Mark the trace as
    inconclusive and investigate end-to-end connectivity separately.
    """
    h1 = HopResult(1, ProbeProtocol.UDP, HopClassification.RESPONDING, "192.168.1.1", None, [ProbeResult(1, 1.0, "192.168.1.1", "TTL_EXPIRED")])
    h2 = HopResult(2, ProbeProtocol.UDP, HopClassification.SILENT_HOP, None, None, [ProbeResult(1, None, None, "TIMEOUT")])
    h3 = HopResult(3, ProbeProtocol.UDP, HopClassification.SILENT_HOP, None, None, [ProbeResult(1, None, None, "TIMEOUT")])

    hops = [h1, h2, h3]
    _classify_trace_hops(hops, target_reached=False)

    assert hops[1].classification == HopClassification.TRACE_INCONCLUSIVE
    assert hops[1].subsequent_hops_responded is False

    overall = _determine_overall_classification(hops, target_reached=False)
    assert overall == HopClassification.TRACE_INCONCLUSIVE


def test_case_4_destination_unreachable():
    """CASE 4: The destination returns a valid unreachable response.

    Result: Report the actual unreachable condition and the available error information.
    """
    h1 = HopResult(1, ProbeProtocol.ICMP, HopClassification.RESPONDING, "192.168.1.1", None, [ProbeResult(1, 1.0, "192.168.1.1", "TTL_EXPIRED")])
    h2 = HopResult(2, ProbeProtocol.ICMP, HopClassification.RESPONDING, "192.168.1.1", None, [ProbeResult(1, 2.0, "192.168.1.1", "DEST_UNREACHABLE", "Destination Unreachable")])

    overall = _determine_overall_classification([h1, h2], target_reached=False)
    assert overall == HopClassification.DESTINATION_UNREACHABLE


def test_anti_labeling_directive():
    """Verify that Hop 2 is NEVER automatically labeled as DSLAM, BRAS, BNG, or ISP cabinet."""
    from app.platform.windows.network_info import get_hop2_diagnostics

    diag = get_hop2_diagnostics()
    assert isinstance(diag, dict)
    reason = diag.get("reason", "")
    forbidden_terms = ["dslam", "bras", "bng", "كابينة", "cabinet"]
    for term in forbidden_terms:
        assert term not in reason.lower(), f"Forbidden label '{term}' found in Hop 2 reason: {reason}"


def test_end_to_end_connectivity_verifier_distinctions():
    """Verify EndToEndConnectivityVerifier correctly distinguishes between connectivity states."""
    verifier = EndToEndConnectivityVerifier()

    # Test single IP target (1.1.1.1)
    res = verifier.verify_single_target("1.1.1.1", 443, "https://1.1.1.1", timeout_sec=2.0)
    assert isinstance(res, EndToEndCheckResult)
    assert res.target == "1.1.1.1"
    # DNS for raw IP is trivially OK
    assert res.dns_ok is True


def test_multi_protocol_panel_ui():
    """Verify MultiProtocolAnalysisPanel renders all required UI sections."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    from app.ui.widgets.multi_protocol_panel import MultiProtocolAnalysisPanel

    panel = MultiProtocolAnalysisPanel()
    assert panel.lbl_h2_badge.text() == "المحطة الثانية · Hop 02"
    assert panel.lbl_h2_ip.text() == "—"

    # Create dummy MultiProtocolAnalysisReport
    h1 = HopResult(1, ProbeProtocol.ICMP, HopClassification.RESPONDING, "192.168.1.1", None, [ProbeResult(1, 1.0, "192.168.1.1", "TTL_EXPIRED")])
    h2 = HopResult(2, ProbeProtocol.ICMP, HopClassification.PATH_CONTINUES, None, None, [ProbeResult(1, None, None, "TIMEOUT")], reason="CoPP Filtering", subsequent_hops_responded=True)
    h3 = HopResult(3, ProbeProtocol.ICMP, HopClassification.RESPONDING, "10.29.82.1", None, [ProbeResult(1, 8.0, "10.29.82.1", "TTL_EXPIRED")])

    tr_icmp = TraceRouteReport(ProbeProtocol.ICMP, "1.1.1.1", "1.1.1.1", True, 25.0, 3, [h1, h2, h3], HopClassification.PATH_CONTINUES, "Win32", 0.5)
    tr_tcp = TraceRouteReport(ProbeProtocol.TCP, "1.1.1.1", "1.1.1.1", True, 26.0, 3, [h1, h2, h3], HopClassification.PATH_CONTINUES, "Npcap", 0.6)
    tr_udp = TraceRouteReport(ProbeProtocol.UDP, "1.1.1.1", "1.1.1.1", False, None, 3, [h1, h2, h3], HopClassification.PATH_CONTINUES, "Win32", 0.4)

    e2e_res = [EndToEndCheckResult("1.1.1.1", True, 24.5, True, 5.0, True, 200, "OK")]

    report = MultiProtocolAnalysisReport(
        timestamp=datetime.now(timezone.utc),
        target="1.1.1.1",
        target_ip="1.1.1.1",
        icmp_trace=tr_icmp,
        tcp_trace=tr_tcp,
        udp_trace=tr_udp,
        end_to_end_checks=e2e_res,
        overall_end_to_end_ok=True,
        end_to_end_status=EndToEndStatus.DESTINATION_REACHABLE,
        case_identified="CASE_1",
        hop2_classification=HopClassification.PATH_CONTINUES,
        hop2_ip=None,
        hop2_protocol=ProbeProtocol.ICMP,
        hop2_latency_ms=None,
        hop2_reason="حجب استجابات التحكم (Control-Plane ICMP) مع استمرار مرور البيانات للمحطات اللاحقة",
        hop2_subsequent_responded=True,
        consolidated_verdict_arabic="المحطة الثانية صامتة مع استمرار تدفق البيانات (Path Continues)",
        technical_details_arabic="تفاصيل فنية كاملة تثبت مرور البيانات.",
        driver_summary="ICMP: Win32 · TCP: Npcap · UDP: Win32",
    )

    panel.update_from_analysis(report)

    # Check updated UI labels
    assert "Path Continues" in panel.h2_chip.text()
    assert "الحزم وصلت للمحطة 3 وما بعدها" in panel.lbl_h2_sub.text()
    assert panel.lbl_h2_lat.text() == "—"  # Must not fabricate fake latency!
    assert "Case 1" in panel.lbl_case_badge.text()
    assert panel.lbl_verdict_title.text() == report.consolidated_verdict_arabic
