"""Tool 1D: Multi-Scale Physical & Logical Geometry Violation Checker."""

from __future__ import annotations
import sys
from pathlib import Path
from typing import List, Dict, Any

_REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from PySide6.QtWidgets import QApplication, QScrollArea


def inspect_geometry_violations(scale: float, label: str):
    out_dir = Path("docs/real") / f"screens_{label}"
    out_dir.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance() or QApplication(sys.argv)
    from app.application import create_application
    from app.ui.main_window import MainWindow

    net_app = create_application()
    win = MainWindow(application=net_app)
    win.show()
    QApplication.processEvents()

    screen = app.primaryScreen()
    avail = screen.availableGeometry()
    frame = win.frameGeometry()

    violations: List[Dict[str, Any]] = []

    if frame.width() > avail.width() or frame.height() > avail.height():
        violations.append({
            "type": "WINDOW_OVERFLOW",
            "detail": f"Window size {frame.width()}x{frame.height()} exceeds available screen {avail.width()}x{avail.height()}",
        })

    min_size = win.minimumSize()
    if min_size.width() > 960 or min_size.height() > 600:
        violations.append({
            "type": "MIN_SIZE_EXCEEDED",
            "detail": f"Minimum size is {min_size.width()}x{min_size.height()}, expected <= 960x600",
        })

    for page_idx in range(win.stack.count()):
        win.stack.setCurrentIndex(page_idx)
        QApplication.processEvents()
        view = win.stack.widget(page_idx)

        for child in view.findChildren(QScrollArea):
            h_bar = child.horizontalScrollBar()
            if h_bar and h_bar.maximum() > 0:
                violations.append({
                    "type": "HORIZONTAL_SCROLL_OVERFLOW",
                    "view_index": page_idx,
                    "widget": child.objectName() or "QScrollArea",
                    "max_scroll": h_bar.maximum(),
                })

        pix = screen.grabWindow(win.winId())
        pix.save(str(out_dir / f"view_{page_idx}_scale_{scale}.png"))

    win.close()
    return violations


if __name__ == "__main__":
    scale_factor = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    label_tag = sys.argv[2] if len(sys.argv) > 2 else "baseline"
    viols = inspect_geometry_violations(scale_factor, label_tag)
    print(f"Scale {scale_factor}: {len(viols)} violations.")
    for v in viols:
        print(f"  - [{v['type']}] {v.get('detail') or v}")
