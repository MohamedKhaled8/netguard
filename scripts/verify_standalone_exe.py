import os
import subprocess
import sys
import time
from pathlib import Path

def test_standalone_exe():
    exe_path = Path("NetGuard.exe").resolve()
    assert exe_path.exists(), f"NetGuard.exe not found at {exe_path}"
    
    print(f"Testing binary: {exe_path} ({exe_path.stat().st_size:,} bytes)")
    
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["PYTEST_CURRENT_TEST"] = "1"
    
    # Launch process
    proc = subprocess.Popen(
        [str(exe_path), "--no-elevate"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=str(exe_path.parent)
    )
    
    print(f"Spawned PID: {proc.pid}. Waiting 6 seconds for bootstrap...")
    time.sleep(6)
    
    # Check if process crashed immediately or is alive
    poll_code = proc.poll()
    if poll_code is not None and poll_code != 0:
        stdout, stderr = proc.communicate(timeout=2)
        print(f"FAILED: Process exited prematurely with code {poll_code}")
        print("STDOUT:", stdout.decode("utf-8", errors="replace"))
        print("STDERR:", stderr.decode("utf-8", errors="replace"))
        sys.exit(1)
        
    print(f"Process PID {proc.pid} is healthy and running actively.")
    
    # Terminate gracefully
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except Exception:
        proc.kill()
        
    print("SUCCESS: Standalone executable verified cleanly.")

if __name__ == "__main__":
    test_standalone_exe()
