#!/usr/bin/env python3
"""NetGuard Self-Hosted Update Publisher & Server.

Zero external dependencies - Python Standard Library only.
Generates release manifests (version.json), verifies SHA-256 digests,
packages NetGuard.exe, and optionally hosts a local LAN HTTP update server.

Usage:
  # Mode A (Publish to LAN Shared Folder / UNC Path):
  python tools/publish_update.py --exe dist/NetGuard.exe --version 1.3.0 --output-dir "\\\\SERVER\\NetGuardUpdates"

  # Mode B (Host HTTP Update Server on Admin PC):
  python tools/publish_update.py --exe dist/NetGuard.exe --version 1.3.0 --output-dir dist/updates --serve 8765
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import os
import shutil
import socket
import socketserver
import sys
from pathlib import Path
from typing import Optional, Tuple


def get_project_root() -> Path:
    """Resolve repository root directory."""
    return Path(__file__).resolve().parent.parent


def get_current_app_version() -> str:
    """Read __version__ from app/version.py."""
    try:
        ver_file = get_project_root() / "app" / "version.py"
        if ver_file.exists():
            for line in ver_file.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("__version__"):
                    parts = line.split("=")
                    if len(parts) >= 2:
                        return parts[1].strip().strip("\"'")
    except Exception:
        pass
    return "1.2.0"


def find_candidate_exe(user_path: Optional[str] = None) -> Path:
    """Locate target NetGuard.exe binary."""
    if user_path:
        p = Path(user_path).resolve()
        if p.exists() and p.is_file():
            return p
        raise FileNotFoundError(f"Specified executable not found: {user_path}")

    root = get_project_root()
    candidates = [
        root / "dist" / "NetGuard.exe",
        Path(r"E:\NetGuard.exe"),
        root / "NetGuard.exe",
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c.resolve()

    raise FileNotFoundError(
        "Could not find NetGuard.exe in dist/ or project root. "
        "Please build the executable first or specify --exe path/to/NetGuard.exe"
    )


def compute_sha256(file_path: Path) -> Tuple[str, int]:
    """Computes SHA-256 digest and file size in bytes using chunked streaming."""
    hasher = hashlib.sha256()
    total_bytes = 0
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            hasher.update(chunk)
            total_bytes += len(chunk)
    return hasher.hexdigest().lower(), total_bytes


def detect_lan_ips() -> list[str]:
    """Detect LAN IP addresses of the local machine."""
    ips = set()
    # Strategy 1: Outbound route discovery
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            outbound_ip = s.getsockname()[0]
            if outbound_ip and not outbound_ip.startswith("127."):
                ips.add(outbound_ip)
    except Exception:
        pass

    # Strategy 2: Hostname inspection
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127."):
                ips.add(ip)
    except Exception:
        pass

    return sorted(list(ips))


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Silent request handler for production serving."""

    def log_message(self, format: str, *args: object) -> None:
        client_ip = self.client_address[0]
        request_line = args[0] if len(args) > 0 else ""
        status_code = args[1] if len(args) > 1 else ""
        print(f"  [HTTP] {client_ip} -> {request_line} ({status_code})")


def serve_directory(directory: Path, port: int, bind_ip: str = "0.0.0.0") -> None:
    """Serve the published update folder over HTTP."""
    handler = lambda *args, **kwargs: CustomHTTPRequestHandler(*args, directory=str(directory), **kwargs)

    class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        allow_reuse_address = True
        daemon_threads = True

    with ThreadedTCPServer((bind_ip, port), handler) as httpd:
        lan_ips = detect_lan_ips()
        print("\n" + "=" * 70)
        print(" [NETGUARD SELF-HOSTED UPDATE SERVER RUNNING]")
        print("=" * 70)
        print(f" Local Endpoint:   http://127.0.0.1:{port}/version.json")
        for ip in lan_ips:
            print(f" LAN Endpoint:     http://{ip}:{port}/version.json")
        print("\n -> Action Required: Copy the LAN Endpoint above into NetGuard Settings")
        print("    on all target PCs across the network.")
        print("=" * 70)
        print(" Serving live update requests... Press Ctrl+C to terminate.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n Server terminated by admin.")


def publish(
    exe_path: Path,
    version: str,
    output_dir: Path,
    changelog: str = "",
    serve_port: Optional[int] = None,
    bind_ip: str = "0.0.0.0",
) -> Path:
    """Publish executable and generate version.json manifest."""
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    dest_exe = output_dir / exe_path.name
    if dest_exe.resolve() != exe_path.resolve():
        print(f"Copying {exe_path} -> {dest_exe}...")
        shutil.copy2(exe_path, dest_exe)

    print("Computing SHA-256 checksum...")
    sha256_hash, file_size = compute_sha256(dest_exe)
    size_mb = file_size / (1024 * 1024)

    manifest = {
        "version": version,
        "url": dest_exe.name,
        "sha256": sha256_hash,
        "changelog": changelog or f"NetGuard AI Release v{version} - Autonomous Zero-Loss Diagnostics",
    }

    manifest_file = output_dir / "version.json"
    manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "-" * 70)
    print(" [RELEASE MANIFEST PUBLISHED SUCCESSFULLY]")
    print("-" * 70)
    print(f" Target Version:  v{version}")
    print(f" Executable:      {dest_exe.name} ({size_mb:.2f} MB)")
    print(f" SHA-256 Digest:  {sha256_hash}")
    print(f" Manifest File:   {manifest_file}")
    print(f" Output Folder:   {output_dir}")
    print("-" * 70)

    if serve_port is not None:
        serve_directory(output_dir, serve_port, bind_ip)

    return manifest_file


def main() -> None:
    parser = argparse.ArgumentParser(
        description="NetGuard Self-Hosted Release Publisher & Update Server (STDLIB Only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--exe",
        help="Path to NetGuard.exe executable (default: auto-detected from dist/ or project root)",
        default=None,
    )
    parser.add_argument(
        "--version",
        help="Release version string (e.g. 1.3.0). Defaults to app/version.py value",
        default=None,
    )
    parser.add_argument(
        "--changelog",
        help="Changelog or release notes for this update",
        default="",
    )
    parser.add_argument(
        "--output-dir",
        help="Target folder (UNC shared folder e.g. \\\\SERVER\\NetGuardUpdates, or local folder)",
        default="dist/updates",
    )
    parser.add_argument(
        "--serve",
        type=int,
        metavar="PORT",
        nargs="?",
        const=8765,
        default=None,
        help="Start embedded HTTP update server on specified port (default: 8765)",
    )
    parser.add_argument(
        "--bind",
        default="0.0.0.0",
        help="IP address to bind the HTTP server to (default: 0.0.0.0)",
    )

    args = parser.parse_args()

    try:
        exe = find_candidate_exe(args.exe)
        version = args.version or get_current_app_version()
        out_dir = Path(args.output_dir)

        publish(
            exe_path=exe,
            version=version,
            output_dir=out_dir,
            changelog=args.changelog,
            serve_port=args.serve,
            bind_ip=args.bind,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
