"""Capture pixel-faithful screenshots of NetGuard AI at multiple resolutions to verify UI fixes."""

import sys
import os
import time

# Ensure project root is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from PySide6.QtWidgets import QApplication, QScrollArea
from PySide6.QtCore import Qt, QTimer
from app.application import create_application
from app.ui.main_window import MainWindow

def capture_ui():
    app = QApplication.instance() or QApplication(sys.argv)
    netguard_app = create_application()

    win = MainWindow(application=netguard_app)
    win.show()

    output_dir = os.path.join(root_dir, "artifacts_screenshots")
    os.makedirs(output_dir, exist_ok=True)

    # Inject realistic synchronized DNS benchmark telemetry
    from app.dns.benchmark import ResolverScore
    from datetime import datetime, timezone
    now_ts = datetime.now(timezone.utc)
    mock_scores = [
        ResolverScore(ip="1.1.1.1", name="Cloudflare Primary", mean_latency_ms=18.4, min_latency_ms=16.0, max_latency_ms=21.0, stdev_latency_ms=1.2, failure_rate=0.0, composite_score=98.0, evaluated_at=now_ts),
        ResolverScore(ip="8.8.8.8", name="Google Primary", mean_latency_ms=24.2, min_latency_ms=22.0, max_latency_ms=27.0, stdev_latency_ms=1.5, failure_rate=0.0, composite_score=94.0, evaluated_at=now_ts),
        ResolverScore(ip="9.9.9.9", name="Quad9 Primary", mean_latency_ms=31.8, min_latency_ms=29.0, max_latency_ms=35.0, stdev_latency_ms=2.1, failure_rate=0.0, composite_score=89.0, evaluated_at=now_ts),
        ResolverScore(ip="1.0.0.1", name="Cloudflare Secondary", mean_latency_ms=19.1, min_latency_ms=17.0, max_latency_ms=22.0, stdev_latency_ms=1.3, failure_rate=0.0, composite_score=97.0, evaluated_at=now_ts),
        ResolverScore(ip="208.67.222.222", name="OpenDNS Home", mean_latency_ms=42.5, min_latency_ms=39.0, max_latency_ms=47.0, stdev_latency_ms=3.0, failure_rate=0.0, composite_score=82.0, evaluated_at=now_ts),
    ]
    win._active_dns_servers = ["1.1.1.1", "1.0.0.1"]
    win._on_dns_benchmark_done(mock_scores)

    # Allow layout and initial events to settle
    app.processEvents()
    time.sleep(0.5)

    resolutions = [
        ("dashboard_fixed_1366.png", 1366, 768),
        ("dashboard_fixed_1920.png", 1920, 1080),
        ("dashboard_fixed_520.png", 520, 900),
    ]

    for name, w, h in resolutions:
        win.resize(w, h)
        app.processEvents()
        time.sleep(0.3)
        pix = win.grab()
        path = os.path.join(output_dir, name)
        pix.save(path)
        print(f"Saved: {path} ({w}x{h})")

    # Also capture Diagnosis, Remediation, Traffic views at 1366x768
    win.resize(1366, 768)
    app.processEvents()

    # Dashboard bottom (scroll down)
    win._switch_view(0, win.nav_buttons[0])
    app.processEvents()
    s_dash = win.view_dashboard.findChild(QScrollArea)
    if s_dash:
        s_dash.verticalScrollBar().setValue(s_dash.verticalScrollBar().maximum())
        app.processEvents()
        time.sleep(0.2)
        win.grab().save(os.path.join(output_dir, "dashboard_bottom_1366.png"))

    # Diagnosis view (index 1) - top & bottom
    win._switch_view(1, win.nav_buttons[1])
    app.processEvents()
    time.sleep(0.2)
    win.grab().save(os.path.join(output_dir, "diagnosis_fixed_1366.png"))
    s_diag = win.view_diagnosis.findChild(QScrollArea)
    if s_diag:
        s_diag.verticalScrollBar().setValue(s_diag.verticalScrollBar().maximum())
        app.processEvents()
        time.sleep(0.2)
        win.grab().save(os.path.join(output_dir, "diagnosis_bottom_1366.png"))

    # Remediation view (index 2) - top & bottom
    win._switch_view(2, win.nav_buttons[2])
    records = netguard_app.ctx.audit.get_recent(limit=30)
    win.view_remediation.update_audit_log(records)
    app.processEvents()
    time.sleep(0.2)
    win.grab().save(os.path.join(output_dir, "remediation_fixed_1366.png"))
    s_rem = win.view_remediation.findChild(QScrollArea)
    if s_rem:
        s_rem.verticalScrollBar().setValue(s_rem.verticalScrollBar().maximum())
        app.processEvents()
        time.sleep(0.2)
        win.grab().save(os.path.join(output_dir, "remediation_bottom_1366.png"))

    # DNS View (index 3)
    win._switch_view(3, win.nav_buttons[3])
    app.processEvents()
    time.sleep(0.2)
    win.grab().save(os.path.join(output_dir, "dns_fixed_1366.png"))

    # Traffic Sessions view (index 4)
    win._switch_view(4, win.nav_buttons[4])
    app.processEvents()
    time.sleep(0.2)
    win.grab().save(os.path.join(output_dir, "traffic_fixed_1366.png"))

    # Copy all screenshots to the artifact screenshots folder as well
    artifact_screenshots_dir = r"C:\Users\Mohamed Khaled\.gemini\antigravity\brain\777990f1-edc2-4a75-9bf8-d05a7ab80764\screenshots"
    import shutil
    for fname in os.listdir(output_dir):
        if fname.endswith(".png"):
            src = os.path.join(output_dir, fname)
            dst = os.path.join(artifact_screenshots_dir, fname)
            try:
                shutil.copy2(src, dst)
            except Exception:
                pass

    print("All verification screenshots captured successfully.")
    win.close()

if __name__ == "__main__":
    capture_ui()
