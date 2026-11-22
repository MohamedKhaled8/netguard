"""Comprehensive Unit & Integration Tests for NetGuard Self-Hosted Auto-Update System."""

import hashlib
import http.server
import json
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Generator
import pytest
from PySide6.QtWidgets import QApplication

from app.core.updater import (
    parse_semver,
    is_version_newer,
    normalize_update_source,
    get_configured_update_source,
    save_configured_update_source,
    get_auto_install_updates,
    save_auto_install_updates,
    cleanup_stale_update_files,
    UpdateChecker,
)
from app.ui.views.settings_view import SettingsView
from tools.publish_update import compute_sha256, publish


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def wait_for_signal(event: threading.Event, qapp: QApplication, timeout: float = 5.0) -> bool:
    """Pump Qt event loop while waiting for cross-thread signal delivery."""
    start = time.time()
    while time.time() - start < timeout:
        qapp.processEvents()
        if event.is_set():
            return True
        time.sleep(0.02)
    return False


def test_semver_parsing_and_comparison():
    assert parse_semver("1.2.0") == (1, 2, 0)
    assert parse_semver("v1.3.1") == (1, 3, 1)
    assert parse_semver("2.0.0-rc1") == (2, 0, 0)
    assert parse_semver("3.4.5+build100") == (3, 4, 5)
    assert parse_semver("invalid") == (0, 0, 0)

    assert is_version_newer("1.3.0", "1.2.0") is True
    assert is_version_newer("1.2.1", "1.2.0") is True
    assert is_version_newer("2.0.0", "1.9.9") is True
    assert is_version_newer("1.2.0", "1.2.0") is False
    assert is_version_newer("1.1.9", "1.2.0") is False


def test_normalize_update_source():
    # Mode B: HTTP / HTTPS
    transport, url = normalize_update_source("http://192.168.1.50:8765")
    assert transport == "http"
    assert url == "http://192.168.1.50:8765/version.json"

    transport, url = normalize_update_source("http://192.168.1.50:8765/")
    assert transport == "http"
    assert url == "http://192.168.1.50:8765/version.json"

    transport, url = normalize_update_source("http://192.168.1.50:8765/version.json")
    assert transport == "http"
    assert url == "http://192.168.1.50:8765/version.json"

    # Mode A: File / UNC Path
    transport, path = normalize_update_source(r"\\SERVER\NetGuardUpdates")
    assert transport == "file"
    assert path.endswith("version.json")
    assert path.startswith(r"\\SERVER\NetGuardUpdates")

    transport, path = normalize_update_source(r"\\SERVER\NetGuardUpdates\version.json")
    assert transport == "file"
    assert path.endswith("version.json")

    transport, path = normalize_update_source("D:/Updates")
    assert transport == "file"
    assert path.endswith("version.json")


def test_update_source_persistence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("NETGUARD_UPDATE_SOURCE", "")
    test_src = r"\\OFFICE_SERVER\Updates\version.json"
    save_configured_update_source(test_src, auto_install=True)
    assert get_configured_update_source() == test_src


def test_auto_install_persistence(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("NETGUARD_AUTO_INSTALL_UPDATES", "")
    save_auto_install_updates(False)
    assert get_auto_install_updates() is False
    save_auto_install_updates(True)
    assert get_auto_install_updates() is True


def test_cleanup_stale_update_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    fake_exe = tmp_path / "NetGuard.exe"
    fake_exe.write_bytes(b"RUNNING_EXE")
    stale_old = tmp_path / "NetGuard.exe.old"
    stale_old.write_bytes(b"OLD_EXE")
    stale_pending = tmp_path / "NetGuard.exe.pending"
    stale_pending.write_bytes(b"PENDING_EXE")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))

    cleanup_stale_update_files()
    assert fake_exe.exists()
    assert not stale_old.exists()
    assert not stale_pending.exists()


def test_defender_safe_direct_rename_logic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify pure Python direct rename swaps running exe to .old and pending to target exe."""
    fake_current = tmp_path / "NetGuard.exe"
    fake_current.write_bytes(b"OLD_VERSION_1_2_0")

    fake_staged = tmp_path / "staged" / "NetGuard_v1_3_0.exe"
    fake_staged.parent.mkdir(parents=True, exist_ok=True)
    fake_staged.write_bytes(b"NEW_VERSION_1_3_0")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_current))

    launched = []
    def fake_popen(cmd, **kwargs):
        launched.append(cmd)
        return None

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(QApplication, "instance", lambda: None)
    monkeypatch.setattr(sys, "exit", lambda code=0: None)

    checker = UpdateChecker()
    success = checker.apply_update_and_restart(str(fake_staged))
    assert success is True

    # Check that NetGuard.exe was directly replaced with new content
    assert fake_current.exists()
    assert fake_current.read_bytes() == b"NEW_VERSION_1_3_0"

    # Check that NetGuard.exe.old was preserved
    old_file = tmp_path / "NetGuard.exe.old"
    assert old_file.exists()
    assert old_file.read_bytes() == b"OLD_VERSION_1_2_0"

    # Check that subprocess was called to launch current_exe
    assert len(launched) == 1
    assert launched[0] == [str(fake_current)]


def test_publisher_tool_and_sha256(tmp_path: Path):
    fake_exe = tmp_path / "NetGuard.exe"
    fake_content = b"MZ-FAKE-WINDOWS-PE-BINARY-FOR-TESTING" * 1024
    fake_exe.write_bytes(fake_content)

    expected_sha = hashlib.sha256(fake_content).hexdigest().lower()
    computed_sha, file_size = compute_sha256(fake_exe)
    assert computed_sha == expected_sha
    assert file_size == len(fake_content)

    out_dir = tmp_path / "published"
    manifest_path = publish(
        exe_path=fake_exe,
        version="1.3.0",
        output_dir=out_dir,
        changelog="Major performance updates",
    )

    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["version"] == "1.3.0"
    assert data["url"] == "NetGuard.exe"
    assert data["sha256"] == expected_sha
    assert data["changelog"] == "Major performance updates"
    assert (out_dir / "NetGuard.exe").exists()


def test_mode_a_unc_local_update_check_and_download(qapp: QApplication, tmp_path: Path):
    """Test Mode A (UNC / Shared Folder) update check and sha256 verified download."""
    fake_exe = tmp_path / "NetGuard.exe"
    fake_content = b"MZ-PROD-UPDATE-BINARY" * 512
    fake_exe.write_bytes(fake_content)
    real_sha = hashlib.sha256(fake_content).hexdigest().lower()

    manifest_file = tmp_path / "version.json"
    manifest = {
        "version": "9.9.9",
        "url": "NetGuard.exe",
        "sha256": real_sha,
        "changelog": "Emergency test update",
    }
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    checker = UpdateChecker(check_url=str(manifest_file))
    found_events = []
    done_event = threading.Event()

    def _on_found(d):
        found_events.append(d)
        done_event.set()

    checker.update_found.connect(_on_found)
    checker.check_for_updates_async()
    assert wait_for_signal(done_event, qapp, timeout=5.0)

    assert len(found_events) > 0
    res = found_events[0]
    assert res["version"] == "9.9.9"
    assert res["transport"] == "file"

    # Download with sha256 verification
    dl_done = threading.Event()
    dl_res = []
    checker.download_finished.connect(lambda path: (dl_res.append(path), dl_done.set()))
    checker.download_update_async(res)
    assert wait_for_signal(dl_done, qapp, timeout=5.0)

    assert len(dl_res) == 1
    assert Path(dl_res[0]).exists()
    assert hashlib.sha256(Path(dl_res[0]).read_bytes()).hexdigest().lower() == real_sha


def test_mode_b_http_update_check_and_download(qapp: QApplication, tmp_path: Path):
    """Test Mode B (Local HTTP Server) update check and download."""
    fake_exe = tmp_path / "NetGuard.exe"
    fake_content = b"MZ-HTTP-UPDATE-BINARY-TEST" * 256
    fake_exe.write_bytes(fake_content)
    real_sha = hashlib.sha256(fake_content).hexdigest().lower()

    manifest_file = tmp_path / "version.json"
    manifest = {
        "version": "9.9.0",
        "url": "NetGuard.exe",
        "sha256": real_sha,
        "changelog": "HTTP Release Test",
    }
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(*args, directory=str(tmp_path), **kwargs)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]

    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    try:
        http_url = f"http://127.0.0.1:{port}/version.json"
        checker = UpdateChecker(check_url=http_url)

        found_event = threading.Event()
        found_data = []
        checker.update_found.connect(lambda d: (found_data.append(d), found_event.set()))
        checker.check_for_updates_async()
        assert wait_for_signal(found_event, qapp, timeout=5.0)

        assert len(found_data) == 1
        assert found_data[0]["version"] == "9.9.0"
        assert found_data[0]["transport"] == "http"
        assert found_data[0]["download_url"] == f"http://127.0.0.1:{port}/NetGuard.exe"

        # Download over HTTP
        dl_event = threading.Event()
        dl_path = []
        checker.download_finished.connect(lambda p: (dl_path.append(p), dl_event.set()))
        checker.download_update_async(found_data[0])
        assert wait_for_signal(dl_event, qapp, timeout=5.0)

        assert len(dl_path) == 1
        assert Path(dl_path[0]).exists()
        assert hashlib.sha256(Path(dl_path[0]).read_bytes()).hexdigest().lower() == real_sha
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_sha256_corruption_rejection(qapp: QApplication, tmp_path: Path):
    """Corrupted binary with mismatched SHA-256 must be rejected and deleted."""
    fake_exe = tmp_path / "NetGuard.exe"
    fake_exe.write_bytes(b"CORRUPTED_OR_TAMPERED_PAYLOAD")

    manifest = {
        "version": "9.9.9",
        "url": "NetGuard.exe",
        "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
        "changelog": "Bad update",
    }
    manifest_file = tmp_path / "version.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    checker = UpdateChecker(check_url=str(manifest_file))
    found_event = threading.Event()
    manifest_box = []
    checker.update_found.connect(lambda d: (manifest_box.append(d), found_event.set()))
    checker.check_for_updates_async()
    assert wait_for_signal(found_event, qapp, timeout=5.0)

    failed_event = threading.Event()
    error_box = []
    checker.download_failed.connect(lambda err: (error_box.append(err), failed_event.set()))
    checker.download_update_async(manifest_box[0])
    assert wait_for_signal(failed_event, qapp, timeout=5.0)

    assert len(error_box) == 1
    assert "SHA-256" in error_box[0]


def test_settings_view_ui_components(qapp: QApplication):
    """Verify SettingsView has update source input, toggle, check button, and install button."""
    view = SettingsView()
    assert hasattr(view, "input_update_source")
    assert hasattr(view, "toggle_auto_update")
    assert hasattr(view, "btn_check_updates")
    assert hasattr(view, "btn_install_update")
    assert hasattr(view, "progress_bar")
    assert hasattr(view, "lbl_update_status")

    # Initial state
    assert view.btn_install_update.isHidden()
    assert view.progress_bar.isHidden()

    # Manual mode (toggle unchecked)
    view.toggle_auto_update.setChecked(False)
    view._on_update_found({"version": "2.0.0", "changelog": "Brand new AI engine"})
    assert not view.btn_install_update.isHidden()
    assert "v2.0.0" in view.btn_install_update.text()
    assert "2.0.0" in view.lbl_update_status.text()

    # Hands-free auto-update mode (toggle checked)
    view.toggle_auto_update.setChecked(True)
    view._on_update_found({"version": "2.1.0", "changelog": "Automatic update"})
    assert view.btn_install_update.isHidden()
    assert "2.1.0" in view.lbl_update_status.text()
