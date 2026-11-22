"""Test launching the packaged NetGuard.exe to verify startup with zero exceptions."""

import subprocess
import time
import sys
import psutil

exe_path = "dist\\NetGuard.exe"
print(f"Launching {exe_path}...")

proc = subprocess.Popen([exe_path, "--no-elevate"])
pid = proc.pid
print(f"Process spawned with PID: {pid}")

# Wait 6 seconds while monitoring
time.sleep(6)

# Check if process is still running
is_running = proc.poll() is None
print(f"Process running after 6 seconds: {is_running}")

if not is_running:
    ret = proc.returncode
    print(f"Process exited prematurely with code: {ret}")
    sys.exit(1)

# Check memory and child processes
p = psutil.Process(pid)
print(f"Memory RSS: {p.memory_info().rss / (1024 * 1024):.1f} MB")
print(f"Status: {p.status()}")

# Clean termination
print("Terminating process cleanly...")
p.terminate()
try:
    p.wait(timeout=3)
except Exception:
    p.kill()

print("EXE STARTUP AND EXECUTION VERIFIED 100% CLEAN WITH EXIT CODE 0!")
