"""Root entry point for NetGuard AI.

Automatically detects and switches to the local virtual environment (.venv)
BEFORE importing any application dependencies.
"""

import os
import sys

# 1. Locate local virtual environment Python
_DIR = os.path.dirname(os.path.abspath(__file__))
_VENV_PYTHON = os.path.join(_DIR, ".venv", "Scripts", "python.exe")

# 2. Re-launch inside .venv if executed with global/unconfigured Python
if os.path.exists(_VENV_PYTHON) and os.path.normcase(sys.executable) != os.path.normcase(_VENV_PYTHON):
    import subprocess
    cmd = [_VENV_PYTHON, os.path.abspath(__file__)] + sys.argv[1:]
    sys.exit(subprocess.call(cmd))

# 3. Import application after venv is confirmed
from app.main import main

if __name__ == "__main__":
    main()
