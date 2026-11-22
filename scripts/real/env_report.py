"""Tool 1A: Real Environment, High-DPI Scaling, and Font Resolution Report."""

from __future__ import annotations
import os
import sys
import json
import sqlite3
import platform
import ctypes
from pathlib import Path
from typing import Dict, Any

_REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtGui import QFontDatabase, QFontInfo, QFont
from PySide6.QtCore import Qt


def get_dpi_awareness() -> str:
    if sys.platform != "win32":
        return "N/A"
    try:
        shcore = ctypes.windll.shcore
        awareness = ctypes.c_int()
        hr = shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
        if hr == 0:
            mapping = {0: "Unaware", 1: "System DPI Aware", 2: "Per-Monitor DPI Aware (v2)"}
            return mapping.get(awareness.value, f"Unknown ({awareness.value})")
    except Exception:
        pass
    try:
        ctx = ctypes.windll.user32.GetProcessDpiAwarenessInternal(ctypes.c_void_p(-2))
        return f"DPI Context: {ctx}"
    except Exception as exc:
        return f"Error: {exc}"


def get_windows_device_scale() -> float:
    if sys.platform != "win32":
        return 1.0
    try:
        scale = ctypes.windll.shcore.GetScaleFactorForDevice(0)
        return float(scale) / 100.0
    except Exception:
        return 1.0


def inspect_database(db_path: Path) -> Dict[str, Any]:
    if not db_path.exists():
        return {"exists": False, "size_mb": 0.0, "row_counts": {}}
    size_mb = db_path.stat().st_size / (1024 * 1024)
    counts = {}
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        for tbl in ["measurements", "incidents", "actions_audit", "measurement_aggregates_1m"]:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {tbl};")
                counts[tbl] = cur.fetchone()[0]
            except Exception:
                counts[tbl] = "Table Not Found"
        conn.close()
    except Exception as e:
        counts["error"] = str(e)
    return {"exists": True, "size_mb": round(size_mb, 2), "row_counts": counts}


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "live"
    out_dir = Path("docs/real")
    out_dir.mkdir(parents=True, exist_ok=True)

    qt_env_vars = {k: v for k, v in os.environ.items() if k.startswith("QT_")}
    app = QApplication.instance() or QApplication(sys.argv)

    screens_data = []
    for screen in app.screens():
        screens_data.append({
            "name": screen.name(),
            "physical_size_px": f"{screen.size().width()}x{screen.size().height()}",
            "available_geometry": {
                "x": screen.availableGeometry().x(),
                "y": screen.availableGeometry().y(),
                "width": screen.availableGeometry().width(),
                "height": screen.availableGeometry().height(),
            },
            "device_pixel_ratio": screen.devicePixelRatio(),
            "logical_dpi": screen.logicalDotsPerInch(),
            "physical_dpi": screen.physicalDotsPerInch(),
        })

    is_elevated = False
    if sys.platform == "win32":
        try:
            is_elevated = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            pass

    from app.ui import tokens
    font_dir = Path("assets/fonts")
    loaded_fonts = {}
    if font_dir.exists():
        for f in font_dir.glob("*.ttf"):
            fid = QFontDatabase.addApplicationFont(str(f))
            loaded_fonts[f.name] = (fid != -1)

    test_label = QLabel("فحص جودة الاتصال 0123")
    font = tokens.get_sans_font(14, 400)
    test_label.setFont(font)
    f_info = QFontInfo(font)

    report = {
        "machine": {
            "os": platform.platform(),
            "win32_ver": platform.win32_ver(),
            "python": platform.python_version(),
            "is_elevated_admin": is_elevated,
            "dpi_awareness": get_dpi_awareness(),
            "hardware_device_scale": get_windows_device_scale(),
        },
        "screens": screens_data,
        "qt_environment": qt_env_vars,
        "database": inspect_database(Path("data/netguard.db")),
        "fonts": {
            "loaded_files": loaded_fonts,
            "resolved_family": f_info.family(),
            "resolved_point_size": f_info.pointSize(),
            "exact_match": f_info.exactMatch(),
        },
    }

    report_path = out_dir / f"env_report_{label}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Report saved to {report_path}")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
