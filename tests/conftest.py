"""Root pytest session cleanup ensuring PySide6 C++ widgets and singletons tear down before Py_FinalizeEx."""

from __future__ import annotations

import gc
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def pytest_sessionfinish(session, exitstatus) -> None:
    """Cleanly close top-level Qt widgets, stop master clock timers, and flush deleteLater before interpreter exit."""
    try:
        from PySide6.QtWidgets import QApplication
    except Exception:
        return

    app = QApplication.instance()
    if app is None:
        return

    try:
        from app.ui.animation_clock import AnimationMasterClock

        AnimationMasterClock.shutdown_instance()
    except Exception:
        pass

    try:
        for w in list(app.topLevelWidgets()):
            try:
                if hasattr(w, "shutdown"):
                    w.shutdown()
            except Exception:
                pass
            try:
                w.close()
                w.deleteLater()
            except Exception:
                pass
        app.processEvents()
        app.processEvents()
        gc.collect()
        app.processEvents()
    except Exception:
        pass
