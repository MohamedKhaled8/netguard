import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.ui.views.dns_view import DNSView
from app.dns.benchmark import ResolverScore

def render_scroll_offsets():
    app = QApplication.instance() or QApplication(sys.argv)
    view = DNSView()
    view.set_active_dns_info(["192.168.1.1", "8.8.8.8"])
    
    dummy_scores = [
        ResolverScore(ip="8.8.8.8", name="Google Public DNS Primary", mean_latency_ms=45.2, min_latency_ms=42.0, max_latency_ms=51.0, median_latency_ms=44.0, success_rate=1.0, is_active=False),
        ResolverScore(ip="1.1.1.1", name="Cloudflare DNS Primary", mean_latency_ms=52.0, min_latency_ms=48.0, max_latency_ms=60.0, median_latency_ms=50.0, success_rate=1.0, is_active=False),
        ResolverScore(ip="192.168.1.1", name="Router DNS / WE", mean_latency_ms=111.0, min_latency_ms=105.0, max_latency_ms=120.0, median_latency_ms=110.0, success_rate=1.0, is_active=True),
    ]
    view.update_rankings(dummy_scores, active_ms=111.0, active_name="Router DNS / WE", is_optimal=False)
    
    view.resize(1000, 700)
    app.processEvents()
    
    # Grab top
    view.grab().save("artifacts/dns_responsive_test/1000_top.png")
    
    # Scroll down to table
    scroll_area = view.findChild(type(view.layout().itemAt(0).widget()))
    # find QScrollArea
    from PySide6.QtWidgets import QScrollArea
    sa = view.findChild(QScrollArea)
    if sa:
        sa.verticalScrollBar().setValue(350)
        app.processEvents()
        view.grab().save("artifacts/dns_responsive_test/1000_table.png")
        
        sa.verticalScrollBar().setValue(800)
        app.processEvents()
        view.grab().save("artifacts/dns_responsive_test/1000_bottom.png")
        print("Captured scrolled images successfully")

if __name__ == "__main__":
    render_scroll_offsets()
