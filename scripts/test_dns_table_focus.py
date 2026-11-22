import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.ui.views.dns_view import DNSView
from app.dns.benchmark import ResolverScore

def render_table_focus():
    app = QApplication.instance() or QApplication(sys.argv)
    view = DNSView()
    view.set_active_dns_info(["192.168.1.1", "8.8.8.8"])
    
    dummy_scores = [
        ResolverScore(ip="8.8.8.8", name="Google Public DNS", mean_latency_ms=44.0, min_latency_ms=42.0, max_latency_ms=51.0, median_latency_ms=44.0, success_rate=1.0, is_active=False),
        ResolverScore(ip="1.1.1.1", name="Cloudflare DNS", mean_latency_ms=50.0, min_latency_ms=48.0, max_latency_ms=60.0, median_latency_ms=50.0, success_rate=1.0, is_active=False),
        ResolverScore(ip="192.168.1.1", name="Router DNS / WE", mean_latency_ms=111.0, min_latency_ms=105.0, max_latency_ms=120.0, median_latency_ms=110.0, success_rate=1.0, is_active=True),
    ]
    view.update_rankings(dummy_scores, active_ms=111.0, active_name="Router DNS / WE", is_optimal=False)
    
    from PySide6.QtWidgets import QScrollArea
    sa = view.findChild(QScrollArea)
    
    for w in [1200, 950, 750, 480]:
        view.resize(w, 800)
        app.processEvents()
        sa.ensureWidgetVisible(view.table)
        app.processEvents()
        view.table.grab().save(f"artifacts/dns_responsive_test/table_{w}.png")
        print(f"Captured table at width {w}")

if __name__ == "__main__":
    render_table_focus()
