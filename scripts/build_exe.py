"""Build script for NetGuard AI standalone Windows executable."""

import os
import sys
import shutil
import subprocess

def build():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root_dir)
    print("Project Root:", root_dir)

    pyinstaller = os.path.join(root_dir, ".venv", "Scripts", "pyinstaller.exe")
    if not os.path.exists(pyinstaller):
        pyinstaller = "pyinstaller"

    cmd = [
        pyinstaller,
        "main.py",
        "--name=NetGuard",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--add-data=assets;assets",
        "--add-data=config;config",
        "--add-data=app/dns/providers.json;app/dns",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=PySide6.QtSvg",
        "--hidden-import=pyqtgraph",
        "--hidden-import=psutil",
        "--hidden-import=dns",
        "--hidden-import=yaml",
        "--hidden-import=sqlite3",
    ]

    print("Running command:", " ".join(cmd))
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print("PyInstaller build failed with code", res.returncode)
        sys.exit(res.returncode)

    dist_exe = os.path.join(root_dir, "dist", "NetGuard.exe")
    root_exe = os.path.join(root_dir, "NetGuard.exe")
    if os.path.exists(dist_exe):
        shutil.copy2(dist_exe, root_exe)
        print("\n==========================================")
        print("BUILD SUCCEEDED (Single-File Standalone)!")
        print("Root Executable:", root_exe)
        print("Dist Executable:", dist_exe)
        print("==========================================")
    else:
        print("Build finished, but NetGuard.exe was not found at expected location.")

if __name__ == "__main__":
    build()
