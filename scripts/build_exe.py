"""Build script for NetGuard AI standalone Windows executable.
Generates an elevated, single-file, windowed PyInstaller binary at D:\\NetGuard.exe.
"""

import os
import sys
import shutil
import subprocess

def build():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root_dir)
    print("Project Root:", root_dir)

    final_dir = r"D:\NetGuard_REDESIGN"
    target_exe = os.path.join(final_dir, "NetGuard.exe")

    # 1. Clean existing build in target location if present
    if os.path.exists(target_exe):
        try:
            os.remove(target_exe)
            print(f"Removed previous binary: {target_exe}")
        except Exception as e:
            print(f"Warning removing {target_exe}: {e}")

    # Clean local build artifacts
    for d in ["dist", "build"]:
        shutil.rmtree(os.path.join(root_dir, d), ignore_errors=True)

    pyinstaller = os.path.join(root_dir, ".venv", "Scripts", "pyinstaller.exe")
    if not os.path.exists(pyinstaller):
        pyinstaller = "pyinstaller"

    spec_path = os.path.join(root_dir, "NetGuard.spec")
    if os.path.exists(spec_path):
        cmd = [
            pyinstaller,
            spec_path,
            "--noconfirm",
            "--clean",
        ]
    else:
        cmd = [
            pyinstaller,
            "main.py",
            "--name=NetGuard",
            "--onefile",
            "--windowed",
            "--noconfirm",
            "--clean",
            "--uac-admin",
            "--icon=assets/icon.ico",
            "--add-data=assets;assets",
            "--add-data=config;config",
            "--add-data=app/dns/providers.json;app/dns",
            "--hidden-import=PySide6.QtCore",
            "--hidden-import=PySide6.QtGui",
            "--hidden-import=PySide6.QtWidgets",
            "--hidden-import=PySide6.QtSvg",
            "--hidden-import=PySide6.QtNetwork",
            "--hidden-import=PySide6.QtWebChannel",
            "--hidden-import=PySide6.QtWebEngineCore",
            "--hidden-import=PySide6.QtWebEngineWidgets",
            "--hidden-import=PySide6.QtPrintSupport",
            "--hidden-import=pyqtgraph",
            "--hidden-import=psutil",
            "--hidden-import=dns",
            "--hidden-import=dns.resolver",
            "--hidden-import=dns.asyncresolver",
            "--hidden-import=yaml",
            "--hidden-import=sqlite3",
            "--hidden-import=pydantic",
            "--hidden-import=pydantic_core",
            "--collect-submodules=app",
            "--exclude-module=tools",
            "--exclude-module=tools.publish_update",
        ]

    print("Running PyInstaller with command:", " ".join(cmd))
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print("PyInstaller build failed with code", res.returncode)
        sys.exit(res.returncode)

    dist_exe = os.path.join(root_dir, "dist", "NetGuard.exe")
    if os.path.exists(dist_exe):
        os.makedirs(final_dir, exist_ok=True)
        try:
            shutil.copy2(dist_exe, target_exe)
            print(f"Copied to destination: {target_exe}")
        except Exception as e:
            print(f"Warning copying to {target_exe}: {e}")

        # Clean up local dist and build folders to conserve disk space
        shutil.rmtree(os.path.join(root_dir, "dist"), ignore_errors=True)
        shutil.rmtree(os.path.join(root_dir, "build"), ignore_errors=True)

        if os.path.exists(target_exe):
            size_mb = os.path.getsize(target_exe) / (1024 * 1024)
            print("\n==========================================")
            print("BUILD SUCCEEDED!")
            print(f"Target: {target_exe}")
            print(f"Size: {size_mb:.2f} MB")
            print("==========================================")
        else:
            print(f"ERROR: Target {target_exe} not found after copy!")
            sys.exit(1)
    else:
        print("Build finished, but NetGuard.exe was not found in dist/.")
        sys.exit(1)

if __name__ == "__main__":
    build()
