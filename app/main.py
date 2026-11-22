"""NetGuard AI Command Line and Main Application Entry Point."""

from __future__ import annotations
import argparse
import asyncio
import os
import signal
import sys
from app.application import create_application
from app.core.models.metrics import OperatingMode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="netguard",
        description="NetGuard AI - Autonomous Predictive Network Intelligence & Self-Healing Platform",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="gui",
        choices=["guard", "monitor", "diagnose", "actions", "gui"],
        help="Command to execute (default: gui)",
    )
    parser.add_argument(
        "--mode",
        choices=["observation", "assisted", "autonomous_safe"],
        default=None,
        help="Override operating mode",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--no-elevate",
        action="store_true",
        help="Do not attempt UAC administrator elevation",
    )
    return parser.parse_args()


async def run_guard(app, mode: str | None = None) -> None:
    if mode:
        app.orchestrator.set_operating_mode(OperatingMode(mode))

    print("=" * 70)
    print(" NETGUARD AI — AUTONOMOUS PREDICTIVE NETWORK GUARDIAN")
    print(f" Mode: {app.orchestrator.mode.value.upper()}")
    print(f" Active Interface: {app.ctx.platform.get_primary_interface()}")
    print(f" Default Gateway:  {app.ctx.platform.get_default_gateway()}")
    print(" Press Ctrl+C to stop.")
    print("=" * 70)

    await app.start()
    stop_event = asyncio.Event()

    def _sig_handler():
        print("\nShutdown signal received. Exiting gracefully...")
        stop_event.set()

    # Handle Ctrl+C
    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _sig_handler)
            except NotImplementedError:
                # Windows signal handling fallback
                pass
    except Exception:
        pass

    try:
        while not stop_event.is_set():
            await asyncio.sleep(0.5)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nShutdown requested.")
    finally:
        await app.stop()


async def run_diagnose(app) -> None:
    print("Running comprehensive network health audit...")
    diag = await app.step()
    print("=" * 70)
    print(f"DIAGNOSIS:   {diag.probable_cause.value.upper()}")
    print(f"CONFIDENCE:  {diag.confidence * 100:.1f}%")
    print(f"SEVERITY:    {diag.severity.value.upper()}")
    print(f"EXPLANATION: {diag.explanation}")
    if diag.supporting_evidence:
        print("\nSUPPORTING EVIDENCE:")
        for ev in diag.supporting_evidence:
            print(f"  * {ev.metric_type.value}: observed={ev.observed_value} (condition: {ev.condition})")
    if diag.recommended_actions:
        print(f"\nRECOMMENDED ACTIONS: {', '.join(diag.recommended_actions)}")
        print(f"AUTO-REMEDIATION AUTHORIZED: {diag.auto_remediation_permitted}")
    print("=" * 70)


def list_actions(app) -> None:
    print("=" * 70)
    print(" REGISTERED NETGUARD REMEDIATION ACTIONS")
    print("=" * 70)
    for act in app.action_registry.list_actions():
        print(f"• ID:          {act.action_id}")
        print(f"  Name:        {act.name}")
        print(f"  Risk Level:  {act.risk_level.value}")
        print(f"  Cooldown:    {act.cooldown_sec}s | Timeout: {act.timeout_sec}s")
        print(f"  Description: {act.description}")
        print("-" * 70)


def run_gui(app) -> None:
    import os
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"

    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("netguard.ai.sentinel.v1")
        except Exception:
            pass

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from app.ui.main_window import MainWindow

    # Enforce PassThrough rounding policy and high-performance attributes BEFORE creating QApplication
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_CompressHighFrequencyEvents, True)
    QApplication.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings, True)
    qt_app = QApplication(sys.argv)

    # Attach clean global excepthook for UI runtime
    def _ui_excepthook(cls, exception, traceback):
        import logging
        logging.getLogger("netguard.crash").critical("Uncaught GUI exception", exc_info=(cls, exception, traceback))
        sys.__excepthook__(cls, exception, traceback)

    sys.excepthook = _ui_excepthook

    from PySide6.QtGui import QIcon
    icon_candidates = [
        os.path.join(getattr(sys, "_MEIPASS", ""), "assets", "icon.ico"),
        os.path.join(getattr(sys, "_MEIPASS", ""), "assets", "icon.png"),
        os.path.join(os.path.dirname(__file__), "..", "assets", "icon.ico"),
        os.path.join(os.path.dirname(__file__), "..", "assets", "icon.png"),
        "assets/icon.ico",
        "assets/icon.png",
    ]
    for c in icon_candidates:
        if c and os.path.exists(c):
            icon = QIcon(c)
            qt_app.setWindowIcon(icon)
            break

    def _cleanup_qos_on_exit() -> None:
        try:
            if hasattr(app, "traffic_controller") and app.traffic_controller:
                app.traffic_controller.cleanup_all_policies()
        except Exception:
            pass

    qt_app.aboutToQuit.connect(_cleanup_qos_on_exit)

    window = MainWindow(application=app)
    if not window.windowIcon().isNull():
        pass
    elif 'icon' in locals():
        window.setWindowIcon(icon)
    window.show()

    # Start core background loop in a separate worker thread or async runner
    loop = asyncio.new_event_loop()
    app.async_loop = loop

    def _run_async_loop() -> None:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(app.start())
        loop.run_forever()

    import threading
    t = threading.Thread(target=_run_async_loop, daemon=True)
    t.start()

    exit_code = qt_app.exec()

    # Perform clean synchronous shutdown of all background loops and threads
    try:
        from app.ui.animation_clock import AnimationMasterClock
        AnimationMasterClock.get_instance().stop()
    except Exception:
        pass

    try:
        if loop.is_running():
            stop_future = asyncio.run_coroutine_threadsafe(app.stop(), loop)
            try:
                stop_future.result(timeout=2.0)
            except Exception:
                pass
            loop.call_soon_threadsafe(loop.stop)
    except Exception:
        pass

    try:
        t.join(timeout=2.0)
    except Exception:
        pass

    # Clean up Qt objects explicitly before exit
    try:
        window.close()
        del window
    except Exception:
        pass
    try:
        qt_app.quit()
        del qt_app
    except Exception:
        pass

    # Flush and close all logging handlers to release file locks
    import logging
    logging.shutdown()

    # Force garbage collection to release any lingering file/DLL/socket handles
    import gc
    gc.collect()

    if getattr(sys, "frozen", False):
        import os
        os._exit(exit_code)
    else:
        sys.exit(exit_code)


def main() -> None:
    args = parse_args()

    # Enforce Administrator mode on Windows startup (Unprivileged mode is prohibited)
    if (
        sys.platform == "win32"
        and "--no-elevate" not in sys.argv
        and ("pytest" not in sys.modules or os.environ.get("NETGUARD_TEST_ELEVATION"))
    ):
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            script = sys.argv[0]
            cmd_args = " ".join([f'"{a}"' for a in sys.argv[1:] if a != "--no-elevate"])
            try:
                ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {cmd_args}', None, 1)
                if ret > 32:
                    sys.exit(0)
                else:
                    try:
                        ctypes.windll.user32.MessageBoxW(
                            0,
                            "يتطلب تشغيل NetGuard AI صلاحيات مسؤول نظام Windows (Run as Administrator) مسبقاً لإدارة وتأمين محولات الشبكة وتطبيق المعالجة الذاتية.\n\nتم إلغاء طلب الصلاحيات، ولا يمكن تشغيل التطبيق في وضع المستخدم العادي. سيتم الإغلاق الآن.",
                            "صلاحيات المسؤول مطلوبة | NetGuard AI",
                            0x10 | 0x0,
                        )
                    except Exception:
                        print("ERROR: NetGuard AI requires Administrator privileges to run.", file=sys.stderr)
                    sys.exit(1)
            except Exception as exc:
                print(f"ERROR: Failed to elevate privileges: {exc}", file=sys.stderr)
                sys.exit(1)

    app = create_application(config_path=args.config)

    if args.command == "actions":
        list_actions(app)
    elif args.command == "diagnose":
        asyncio.run(run_diagnose(app))
    elif args.command == "gui":
        run_gui(app)
    elif args.command in ("guard", "monitor"):
        try:
            asyncio.run(run_guard(app, mode=args.mode))
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
