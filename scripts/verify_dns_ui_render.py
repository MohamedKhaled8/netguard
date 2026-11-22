"""Verify DNSView rendering, table rows, comparison bars, and active identity card."""

import sys
import os
sys.path.insert(0, os.path.abspath("."))

from PySide6.QtWidgets import QApplication
from app.ui.views.dns_view import DNSView
from app.ui.widgets.base_panel import Panel
from app.dns.benchmark import DNSBenchmark, ResolverScore


def main():
    app = QApplication.instance() or QApplication(sys.argv)

    view = DNSView()
    view.resize(1200, 1600)
    view.show()

    # Step 1: Initial state verification (Catalog rows visible even before benchmark)
    assert view.table.rowCount() >= 6, f"Expected at least 6 initial rows, got {view.table.rowCount()}"
    app.processEvents()
    view.grab().save("dns_view_initial.png")

    # Step 2: Live benchmark data injection
    scores = [
        ResolverScore(ip="8.8.4.4", name="Google Public DNS Secondary", median_latency_ms=18.2, mean_latency_ms=18.5, min_latency_ms=16.0, max_latency_ms=22.0, success_rate=1.0, is_active=False, is_recommended=True),
        ResolverScore(ip="1.1.1.1", name="Cloudflare DNS Primary", median_latency_ms=22.4, mean_latency_ms=22.8, min_latency_ms=20.0, max_latency_ms=25.0, success_rate=1.0, is_active=False, is_recommended=False),
        ResolverScore(ip="1.0.0.1", name="Cloudflare DNS Secondary", median_latency_ms=24.1, mean_latency_ms=24.5, min_latency_ms=21.0, max_latency_ms=28.0, success_rate=1.0, is_active=True, is_recommended=False),
        ResolverScore(ip="9.9.9.9", name="Quad9 Secure Primary", median_latency_ms=32.0, mean_latency_ms=32.5, min_latency_ms=28.0, max_latency_ms=36.0, success_rate=1.0, is_active=False, is_recommended=False),
        ResolverScore(ip="208.67.222.222", name="OpenDNS (Cisco) Primary", median_latency_ms=38.6, mean_latency_ms=39.0, min_latency_ms=35.0, max_latency_ms=44.0, success_rate=1.0, is_active=False, is_recommended=False),
    ]

    view.set_active_dns_info(["1.0.0.1", "fe80::1"])
    view.update_rankings(scores, active_ms=24.1, active_name="Cloudflare DNS Secondary", is_optimal=True)

    app.processEvents()
    view.grab().save("dns_view_populated.png")
    # Grab the panel containing the table to see authentic panel background
    for child in view.content_widget.findChildren(Panel):
        if hasattr(child, "lbl_title") and "جدول" in child.lbl_title.text():
            child.grab().save("dns_table_panel_snapshot.png")

    print(f"VERIFIED: Table row count: {view.table.rowCount()}")
    print(f"Active Provider Label: {view.lbl_active_provider.text()}")
    print(f"Active IP Label: {view.lbl_active_ip.text()}")
    print(f"Active Latency Label: {view.lbl_active_ms_stat.text()}")
    print(f"Fastest Label: {view.lbl_fast_name.text()}")
    print(f"Analysis Verdict: {view.lbl_curr_analysis.text()[:60]}...")
    print(f"Smart Rec: {view.lbl_smart_rec.text()[:60]}...")


if __name__ == "__main__":
    main()
