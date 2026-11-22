"""Root entry point for NetGuard AI.

Automatically detects and switches to the local virtual environment (.venv)
BEFORE importing any application dependencies.
"""

import os
import sys

# Configure High-DPI pass-through scaling before any Qt module is imported
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"

# Explicitly register Windows Application User Model ID for Taskbar icon grouping
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("NetGuard.AI.Network.Security.v1")
    except Exception:
        pass

# 1. Locate local virtual environment Python
_DIR = os.path.dirname(os.path.abspath(__file__))
_VENV_PYTHON = os.path.join(_DIR, ".venv", "Scripts", "python.exe")
_IS_FROZEN = getattr(sys, "frozen", False)

# 2. Re-launch inside .venv if executed with global/unconfigured Python (not when packaged as .exe)
if not _IS_FROZEN and os.path.exists(_VENV_PYTHON) and os.path.normcase(sys.executable) != os.path.normcase(_VENV_PYTHON):
    import subprocess
    cmd = [_VENV_PYTHON, os.path.abspath(__file__)] + sys.argv[1:]
    sys.exit(subprocess.call(cmd))

# 3. Enforce Administrator mode on Windows startup (Bans unprivileged user mode)
if (
    sys.platform == "win32"
    and "--no-elevate" not in sys.argv
    and "pytest" not in sys.modules
    and not os.environ.get("PYTEST_CURRENT_TEST")
):
    import ctypes
    if not ctypes.windll.shell32.IsUserAnAdmin():
        if _IS_FROZEN:
            executable = sys.executable
            args = " ".join([f'"{a}"' for a in sys.argv[1:] if a != "--no-elevate"])
        else:
            executable = _VENV_PYTHON if os.path.exists(_VENV_PYTHON) else sys.executable
            script = os.path.abspath(__file__)
            args = f'"{script}"'
            if len(sys.argv) > 1:
                args += " " + " ".join([f'"{a}"' for a in sys.argv[1:] if a != "--no-elevate"])

        try:
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, args, _DIR, 1)
            if ret > 32:
                # Successfully spawned elevated child process; terminate unelevated parent
                sys.exit(0)
            else:
                # User declined UAC or elevation failed - unprivileged mode is prohibited
                try:
                    ctypes.windll.user32.MessageBoxW(
                        0,
                        "يتطلب تشغيل NetGuard AI صلاحيات مسؤول نظام Windows (Run as Administrator) مسبقاً لإدارة وتأمين محولات الشبكة وتطبيق المعالجة الذاتية.\n\nتم إلغاء طلب الصلاحيات، ولا يمكن تشغيل التطبيق في وضع المستخدم العادي. سيتم الإغلاق الآن.",
                        "صلاحيات المسؤول مطلوبة | NetGuard AI",
                        0x10 | 0x0,
                    )
                except Exception:
                    pass
                sys.exit(1)
        except Exception as exc:
            try:
                ctypes.windll.user32.MessageBoxW(
                    0,
                    f"تعذر الحصول على صلاحيات المسؤول:\n{exc}\n\nيُرجى تشغيل البرنامج بالنقر بالزر الأيمن واختيار 'تشغيل كمسؤول' (Run as administrator).",
                    "خطأ في الصلاحيات | NetGuard AI",
                    0x10 | 0x0,
                )
            except Exception:
                pass
            sys.exit(1)

# 4. Silent Crash Protection & Global Exception Hook
def _global_excepthook(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    import logging
    logger = logging.getLogger("netguard.crash")
    logger.critical("Uncaught top-level exception:", exc_info=(exc_type, exc_value, exc_traceback))
    try:
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                "حدث استثناء غير متوقع في النظام. تم تسجيل تفاصيل الحادثة بأمان في سجلات البرنامج لحماية الاستقرار.",
                "NetGuard AI - تنبيه فني",
                0x10 | 0x0,
            )
    except Exception:
        pass

sys.excepthook = _global_excepthook

# 5. Windows Named Mutex Single-Instance Guard (Bans Duplicate Process DB Locks)
_SINGLE_INSTANCE_MUTEX = None
if (
    sys.platform == "win32"
    and "pytest" not in sys.modules
    and not os.environ.get("PYTEST_CURRENT_TEST")
):
    try:
        import ctypes
        ERROR_ALREADY_EXISTS = 183
        _SINGLE_INSTANCE_MUTEX = ctypes.windll.kernel32.CreateMutexW(
            None, False, "Local\\NetGuard_SingleInstance_Mutex_v1"
        )
        if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            try:
                ctypes.windll.user32.MessageBoxW(
                    0,
                    "تطبيق NetGuard AI يعمل بالفعل في الخلفية أو شريط المهام.",
                    "NetGuard AI",
                    0x40 | 0x0,
                )
            except Exception:
                pass
            sys.exit(0)
    except Exception:
        pass

# 6. Import application after venv, elevation, and single-instance mutex are confirmed
from app.main import main

if __name__ == "__main__":
    main()
