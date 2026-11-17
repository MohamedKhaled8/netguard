import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSize
from app.application import create_application
from app.ui.main_window import MainWindow

OUTPUT_DIR = Path("artifacts_screenshots/phase5")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VIEWS = [
    (0, "dashboard"),
    (1, "diagnosis"),
    (2, "remediation"),
    (3, "dns"),
    (4, "traffic"),
    (5, "history"),
    (6, "settings"),
]


def capture_all_views(state_prefix: str, window: MainWindow, app: QApplication):
    window.resize(1366, 768)
    window.show()
    app.processEvents()
    time.sleep(0.5)
    app.processEvents()

    for idx, name in VIEWS:
        window.stack.setCurrentIndex(idx)
        app.processEvents()
        time.sleep(0.2)
        app.processEvents()

        pixmap = window.grab()
        target_path = OUTPUT_DIR / f"{state_prefix}_{idx}_{name}.png"
        pixmap.save(str(target_path), "PNG")
        print(f"Captured: {target_path} ({pixmap.width()}x{pixmap.height()})")


def run():
    app = QApplication.instance() or QApplication(sys.argv)
    app_core = create_application()

    # 1. Connected state capture
    print("--- Capturing Connected State ---")
    win_connected = MainWindow(app_core)
    capture_all_views("connected", win_connected, app)
    win_connected.close()
    app.processEvents()

    # 2. Adapter-Disabled / Disconnected state capture
    print("--- Capturing Adapter-Disabled State ---")
    win_disabled = MainWindow(app_core)
    # Simulate disabled adapter telemetry and status
    win_disabled.view_dashboard.update_shield(
        is_healthy=False,
        title="محول الشبكة معطل",
        desc="تم فصل أو تعطيل بطاقة الشبكة (Wi-Fi). لا يتوفر اتصال بالإنترنت أو بالراوتر المحلي.",
    )
    win_disabled.view_dashboard.set_probe_status_alert("تعذر الوصول إلى محول الشبكة: البطاقة مفصولة أو معطلة.")
    capture_all_views("disabled", win_disabled, app)
    win_disabled.close()
    app.processEvents()
    print("All screenshots captured successfully.")


if __name__ == "__main__":
    run()
