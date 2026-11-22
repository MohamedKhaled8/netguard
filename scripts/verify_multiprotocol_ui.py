"""Offscreen UI verification script for Multi-Protocol Connectivity Analysis."""

import sys
import os
import time

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from app.application import create_application
from app.ui.main_window import MainWindow
from app.diagnosis.traceroute import (
    HopClassification,
    ProbeProtocol,
    EndToEndStatus,
    ProbeResult,
    HopResult,
    TraceRouteReport,
    EndToEndCheckResult,
    MultiProtocolAnalysisReport,
)
from datetime import datetime, timezone


def capture_diagnosis_multiprotocol():
    app = QApplication.instance() or QApplication(sys.argv)
    netguard_app = create_application()
    win = MainWindow(application=netguard_app)
    win.resize(1366, 850)
    win.show()

    # Switch to Diagnosis View (tab index 1)
    win._switch_view(1, win.btn_diag)
    app.processEvents()

    # Create realistic Case 1 MultiProtocolAnalysisReport
    h1 = HopResult(1, ProbeProtocol.ICMP, HopClassification.RESPONDING, "192.168.1.1", None, [ProbeResult(1, 1.2, "192.168.1.1", "TTL_EXPIRED")])
    h2 = HopResult(2, ProbeProtocol.ICMP, HopClassification.PATH_CONTINUES, None, None, [ProbeResult(1, None, None, "TIMEOUT")], reason="حجب استجابات التحكم (Control-Plane ICMP) مع استمرار مرور البيانات للمحطات اللاحقة", subsequent_hops_responded=True)
    h3 = HopResult(3, ProbeProtocol.ICMP, HopClassification.RESPONDING, "10.29.82.189", None, [ProbeResult(1, 9.8, "10.29.82.189", "TTL_EXPIRED")])
    h4 = HopResult(4, ProbeProtocol.ICMP, HopClassification.RESPONDING, "10.37.78.30", None, [ProbeResult(1, 8.4, "10.37.78.30", "TTL_EXPIRED")])
    h5 = HopResult(5, ProbeProtocol.ICMP, HopClassification.RESPONDING, "1.1.1.1", None, [ProbeResult(1, 24.5, "1.1.1.1", "SUCCESS")])

    tr_icmp = TraceRouteReport(ProbeProtocol.ICMP, "1.1.1.1", "1.1.1.1", True, 24.5, 5, [h1, h2, h3, h4, h5], HopClassification.PATH_CONTINUES, "Windows Native IcmpSendEcho", 0.45)
    tr_tcp = TraceRouteReport(ProbeProtocol.TCP, "1.1.1.1", "1.1.1.1", True, 25.1, 5, [h1, h2, h3, h4, h5], HopClassification.PATH_CONTINUES, "Windows Npcap Raw Sniffer Active", 0.52)
    tr_udp = TraceRouteReport(ProbeProtocol.UDP, "1.1.1.1", "1.1.1.1", False, None, 5, [h1, h2, h3, h4, h5], HopClassification.PATH_CONTINUES, "Windows Npcap Raw Sniffer Active", 0.48)

    e2e = [
        EndToEndCheckResult("1.1.1.1", True, 24.2, True, 0.1, True, 200, "TCP 443 OK · HTTPS 200 OK"),
        EndToEndCheckResult("8.8.8.8", True, 27.5, True, 0.1, True, 200, "TCP 443 OK · HTTPS 200 OK"),
        EndToEndCheckResult("google.com", True, 28.1, True, 14.2, True, 200, "DNS OK · TCP 443 OK · HTTPS 200 OK"),
    ]

    report = MultiProtocolAnalysisReport(
        timestamp=datetime.now(timezone.utc),
        target="1.1.1.1",
        target_ip="1.1.1.1",
        icmp_trace=tr_icmp,
        tcp_trace=tr_tcp,
        udp_trace=tr_udp,
        end_to_end_checks=e2e,
        overall_end_to_end_ok=True,
        end_to_end_status=EndToEndStatus.DESTINATION_REACHABLE,
        case_identified="CASE_1",
        hop2_classification=HopClassification.PATH_CONTINUES,
        hop2_ip=None,
        hop2_protocol=ProbeProtocol.ICMP,
        hop2_latency_ms=None,
        hop2_reason="الموجّه يمرر البيانات للمحطات التالية ويحجب حزم استطلاع المسار ICMP Time Exceeded (حماية CoPP)",
        hop2_subsequent_responded=True,
        consolidated_verdict_arabic="المحطة الثانية صامتة مع استمرار تدفق البيانات (Path Continues)",
        technical_details_arabic="المحطة الثانية (Hop 02) لم ترسل استجابة ICMP Time Exceeded مباشرة، ولكن حزم البيانات عبرتها بنجاح ووصلت للمحطة الثالثة وما بعدها. هذا يثبت أن الموجّه يعمل كمعبر تمرير سليم وأن عدم ظهوره ناتج عن قيود حماية المعالج (CoPP) وليس انقطاعاً في الشبكة.",
        driver_summary="ICMP: Windows Native IcmpSendEcho · TCP: Npcap Raw Sniffer · UDP: Npcap Raw Sniffer",
    )

    win.view_diagnosis.update_multi_protocol_analysis(report)
    app.processEvents()
    time.sleep(0.3)

    out_dir = os.path.join(root_dir, "artifacts_screenshots")
    os.makedirs(out_dir, exist_ok=True)

    # 1. Direct grab of MultiProtocolAnalysisPanel
    panel_pix = win.view_diagnosis.multi_protocol_panel.grab()
    panel_path = os.path.join(out_dir, "panel_multi_protocol_direct.png")
    panel_pix.save(panel_path)
    print(f"Captured: {panel_path}")

    # 2. Scroll diagnosis view to show the panel in context
    from PySide6.QtWidgets import QScrollArea
    for sa in win.view_diagnosis.findChildren(QScrollArea):
        sa.verticalScrollBar().setValue(sa.verticalScrollBar().maximum() // 2)
    app.processEvents()
    time.sleep(0.3)

    out_path = os.path.join(out_dir, "diagnosis_multi_protocol_1366.png")
    pix = win.grab()
    pix.save(out_path)
    print(f"Captured: {out_path}")

    # Now switch to dashboard and verify Node 03 (Hop 2 / Provider)
    win._switch_view(0, win.btn_dash)
    app.processEvents()
    # Inject network info with hop2_diag
    info = {
        "iface": "Wi-Fi",
        "gateway": "192.168.1.1",
        "local_ip": "192.168.1.3",
        "ssid": "Home-Fiber",
        "is_wifi": True,
        "signal": "88%",
        "band": "5 GHz",
        "dns": ["1.1.1.1", "1.0.0.1"],
        "isp": {"company": "Telecom Egypt (WE)", "ip": "197.52.12.34"},
        "isp_company": "Telecom Egypt (WE)",
        "isp_gateway_ip": None,
        "isp_gateway_latency_ms": None,
        "hop2_diag": {
            "hop_number": 2,
            "ip": None,
            "latency_ms": None,
            "protocol": "ICMP",
            "classification": "PATH_CONTINUES",
            "reason": "المحطة لا تستجيب لحزم الاستطلاع مع استمرار حركة البيانات",
            "subsequent_responded": True,
            "status": "filtered_passing",
        },
    }
    win.view_dashboard.update_network_identity(info)
    win.view_dashboard.flow_path._select_node(2)
    app.processEvents()
    time.sleep(0.3)

    flow_pix = win.view_dashboard.flow_path.grab()
    flow_path_img = os.path.join(out_dir, "flow_path_hop2_direct.png")
    flow_pix.save(flow_path_img)
    print(f"Captured: {flow_path_img}")

    dash_path = os.path.join(out_dir, "dashboard_hop2_path_continues.png")
    pix_dash = win.grab()
    pix_dash.save(dash_path)
    print(f"Captured: {dash_path}")


if __name__ == "__main__":
    capture_diagnosis_multiprotocol()
