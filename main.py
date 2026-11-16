"""Root entry point for NetGuard AI.

Automatically detects and switches to the local virtual environment (.venv)
BEFORE importing any application dependencies.
"""

import os
import sys

# 1. Locate local virtual environment Python
_DIR = os.path.dirname(os.path.abspath(__file__))
_VENV_PYTHON = os.path.join(_DIR, ".venv", "Scripts", "python.exe")
_IS_FROZEN = getattr(sys, "frozen", False)

# 2. Re-launch inside .venv if executed with global/unconfigured Python (not when packaged as .exe)
if not _IS_FROZEN and os.path.exists(_VENV_PYTHON) and os.path.normcase(sys.executable) != os.path.normcase(_VENV_PYTHON):
    import subprocess
    cmd = [_VENV_PYTHON, os.path.abspath(__file__)] + sys.argv[1:]
    sys.exit(subprocess.call(cmd))

# 3. Auto-elevate to Administrator mode on Windows startup
if sys.platform == "win32" and "--no-elevate" not in sys.argv and "pytest" not in sys.modules:
    import ctypes
    try:
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
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, args, None, 1)
            if ret > 32:
                sys.exit(0)
    except Exception:
        pass

# 4. Import application after venv and elevation are confirmed
from app.main import main

if __name__ == "__main__":
    main()
