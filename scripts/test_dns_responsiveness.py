import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.ui.views.dns_view import DNSView

def render_resolutions():
    app = QApplication.instance() or QApplication(sys.argv)
    
    view = DNSView()
    view.set_active_dns_info(["192.168.1.1", "8.8.8.8"])
    
    from app.dns.benchmark import ResolverScore
    dummy_scores = [
        ResolverScore(ip="8.8.8.8", name="Google Public DNS Primary", mean_latency_ms=45.2, min_latency_ms=42.0, max_latency_ms=51.0, median_latency_ms=44.0, success_rate=1.0, is_active=False),
        ResolverScore(ip="1.1.1.1", name="Cloudflare DNS Primary", mean_latency_ms=52.0, min_latency_ms=48.0, max_latency_ms=60.0, median_latency_ms=50.0, success_rate=1.0, is_active=False),
        ResolverScore(ip="192.168.1.1", name="Router DNS / WE", mean_latency_ms=111.0, min_latency_ms=105.0, max_latency_ms=120.0, median_latency_ms=110.0, success_rate=1.0, is_active=True),
    ]
    view.update_rankings(dummy_scores, active_ms=111.0, active_name="Router DNS / WE", is_optimal=False)
    
    os.makedirs("artifacts/dns_responsive_test", exist_ok=True)
    
    sizes = [
        (1440, 900, "1440_desktop"),
        (1024, 768, "1024_laptop"),
        (800, 600, "800_compact"),
        (500, 800, "500_narrow")
    ]
    
    for w, h, name in sizes:
        view.resize(w, h)
        app.processEvents()
        view.grab().save(f"artifacts/dns_responsive_test/{name}.png")
        print(f"Captured {name} ({w}x{h})")

if __name__ == "__main__":
    render_resolutions()
