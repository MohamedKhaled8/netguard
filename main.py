"""Root entry point forwarding to app.main with automatic virtual environment handling."""

import os
import sys


def _run() -> None:
    # Auto-redirect to local .venv if launched via global unconfigured python
    project_root = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(project_root, ".venv", "Scripts", "python.exe")
    if os.path.exists(venv_python) and os.path.normcase(sys.executable) != os.path.normcase(venv_python):
        import subprocess
        args = [venv_python, __file__] + sys.argv[1:]
        sys.exit(subprocess.call(args))

    from app.main import main
    main()


if __name__ == "__main__":
    _run()
