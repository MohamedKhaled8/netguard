"""Tool 1B: UI-Thread Stall Detector, Subprocess & DB Interceptor."""

from __future__ import annotations
import os
import sys
import time
import json
import sqlite3
import threading
import subprocess
import traceback
from pathlib import Path
from typing import Dict, List, Any

_REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

_STALLS: List[Dict[str, Any]] = []
_SUBPROCESS_SPAWNS: List[Dict[str, Any]] = []
_DB_QUERIES: List[Dict[str, Any]] = []
_WATCHDOG_RUNNING = True


class HeartbeatWatchdog(threading.Thread):
    def __init__(self, main_thread_id: int):
        super().__init__(daemon=True)
        self.main_thread_id = main_thread_id
        self.last_heartbeat = time.perf_counter()
        self.lock = threading.Lock()

    def ping(self):
        with self.lock:
            self.last_heartbeat = time.perf_counter()

    def run(self):
        global _WATCHDOG_RUNNING, _STALLS
        while _WATCHDOG_RUNNING:
            time.sleep(0.01)
            now = time.perf_counter()
            with self.lock:
                lateness_ms = (now - self.last_heartbeat) * 1000.0

            if lateness_ms > 50.0:
                frames = sys._current_frames()
                main_frame = frames.get(self.main_thread_id)
                stack_str = "".join(traceback.format_stack(main_frame)) if main_frame else "Unknown"
                _STALLS.append({
                    "timestamp": time.time(),
                    "lateness_ms": round(lateness_ms, 2),
                    "stack": stack_str,
                })
                time.sleep(0.05)


def install_interceptors():
    orig_popen_init = subprocess.Popen.__init__

    def wrapped_popen_init(self, args, *a, **kwargs):
        is_ui = threading.current_thread() == threading.main_thread()
        cmd_str = " ".join(args) if isinstance(args, list) else str(args)
        t0 = time.perf_counter()
        orig_popen_init(self, args, *a, **kwargs)
        dur_ms = (time.perf_counter() - t0) * 1000.0
        _SUBPROCESS_SPAWNS.append({
            "command": cmd_str[:120],
            "is_main_ui_thread": is_ui,
            "duration_ms": round(dur_ms, 2),
            "timestamp": time.time(),
        })

    subprocess.Popen.__init__ = wrapped_popen_init

    orig_connect = sqlite3.connect

    class CursorProxy:
        def __init__(self, cursor):
            object.__setattr__(self, "_cursor", cursor)

        def execute(self, sql, *args, **kwargs):
            is_ui = threading.current_thread() == threading.main_thread()
            t0 = time.perf_counter()
            self._cursor.execute(sql, *args, **kwargs)
            dur_ms = (time.perf_counter() - t0) * 1000.0
            _DB_QUERIES.append({
                "sql": str(sql).strip()[:100],
                "is_main_ui_thread": is_ui,
                "duration_ms": round(dur_ms, 2),
                "timestamp": time.time(),
            })
            return self

        def executemany(self, sql, *args, **kwargs):
            is_ui = threading.current_thread() == threading.main_thread()
            t0 = time.perf_counter()
            self._cursor.executemany(sql, *args, **kwargs)
            dur_ms = (time.perf_counter() - t0) * 1000.0
            _DB_QUERIES.append({
                "sql": str(sql).strip()[:100],
                "is_main_ui_thread": is_ui,
                "duration_ms": round(dur_ms, 2),
                "timestamp": time.time(),
            })
            return self

        def __getattr__(self, name):
            return getattr(self._cursor, name)

        def __setattr__(self, name, value):
            if name == "_cursor":
                object.__setattr__(self, name, value)
            else:
                setattr(self._cursor, name, value)

        def __iter__(self):
            return iter(self._cursor)

    class ConnectionProxy:
        def __init__(self, conn):
            object.__setattr__(self, "_conn", conn)

        def cursor(self, *args, **kwargs):
            cur = self._conn.cursor(*args, **kwargs)
            return CursorProxy(cur)

        def execute(self, sql, *args, **kwargs):
            cur = self.cursor()
            return cur.execute(sql, *args, **kwargs)

        def executemany(self, sql, *args, **kwargs):
            cur = self.cursor()
            return cur.executemany(sql, *args, **kwargs)

        def __enter__(self):
            self._conn.__enter__()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return self._conn.__exit__(exc_type, exc_val, exc_tb)

        def __getattr__(self, name):
            return getattr(self._conn, name)

        def __setattr__(self, name, value):
            if name == "_conn":
                object.__setattr__(self, name, value)
            else:
                setattr(self._conn, name, value)

    def wrapped_connect(*args, **kwargs):
        conn = orig_connect(*args, **kwargs)
        return ConnectionProxy(conn)

    sqlite3.connect = wrapped_connect


def run_benchmark(duration_sec: int = 60, label: str = "live"):
    out_dir = Path("docs/real")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    install_interceptors()
    app = QApplication.instance() or QApplication(sys.argv)

    from app.application import create_application
    from app.ui.main_window import MainWindow

    t0_start = time.perf_counter()
    net_app = create_application()
    win = MainWindow(application=net_app)
    win.show()
    t_shown = (time.perf_counter() - t0_start) * 1000.0

    main_id = threading.main_thread().ident
    watchdog = HeartbeatWatchdog(main_id)
    watchdog.start()

    heartbeat_timer = QTimer()
    heartbeat_timer.timeout.connect(watchdog.ping)
    heartbeat_timer.start(10)

    cycle_timer = QTimer()
    pages = [0, 1, 2, 3, 4, 5, 6]
    state = {"idx": 0}

    def switch_page():
        idx = pages[state["idx"] % len(pages)]
        win._switch_view(idx, win.nav_buttons[idx])
        state["idx"] += 1

    cycle_timer.timeout.connect(switch_page)
    cycle_timer.start(2000)

    end_timer = QTimer()
    end_timer.setSingleShot(True)

    def on_finish():
        global _WATCHDOG_RUNNING
        _WATCHDOG_RUNNING = False
        heartbeat_timer.stop()
        cycle_timer.stop()
        win.close()
        app.quit()

    end_timer.timeout.connect(on_finish)
    end_timer.start(duration_sec * 1000)

    app.exec()

    report = {
        "duration_sec": duration_sec,
        "first_window_shown_ms": round(t_shown, 1),
        "stalls_over_50ms_count": len(_STALLS),
        "stalls_over_100ms_count": len([s for s in _STALLS if s["lateness_ms"] >= 100.0]),
        "max_stall_ms": max([s["lateness_ms"] for s in _STALLS], default=0.0),
        "top_stalls": sorted(_STALLS, key=lambda x: x["lateness_ms"], reverse=True)[:5],
        "subprocess_spawns_total": len(_SUBPROCESS_SPAWNS),
        "subprocess_on_ui_thread": len([p for p in _SUBPROCESS_SPAWNS if p["is_main_ui_thread"]]),
        "database_queries_total": len(_DB_QUERIES),
        "database_queries_on_ui_thread": len([q for q in _DB_QUERIES if q["is_main_ui_thread"]]),
    }

    out_file = out_dir / f"perf_{label}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Performance report saved to {out_file}")


if __name__ == "__main__":
    dur = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    lbl = sys.argv[2] if len(sys.argv) > 2 else "baseline"
    run_benchmark(dur, lbl)
