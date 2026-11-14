"""NetGuard AI Command Line and Main Application Entry Point."""

from __future__ import annotations
import argparse
import asyncio
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
    from PySide6.QtWidgets import QApplication
    from app.ui.main_window import MainWindow

    qt_app = QApplication(sys.argv)
    window = MainWindow(application=app)
    window.show()

    # Start core background loop in a separate worker thread or async runner
    loop = asyncio.new_event_loop()

    def _run_async_loop() -> None:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(app.start())
        loop.run_forever()

    import threading
    t = threading.Thread(target=_run_async_loop, daemon=True)
    t.start()

    exit_code = qt_app.exec()
    try:
        loop.call_soon_threadsafe(loop.stop)
    except Exception:
        pass
    sys.exit(exit_code)


def main() -> None:
    args = parse_args()
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
