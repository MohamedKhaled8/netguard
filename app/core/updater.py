"""Automated Self-Hosted Update Checker and Release Synchronization for NetGuard AI.

Provides remote version checking, update notifications, integrity verification (SHA-256),
and in-place Windows executable deployment supporting:
  - Mode A: LAN Shared Folders / UNC Paths (e.g. \\\\SERVER\\NetGuardUpdates\\version.json)
  - Mode B: Direct Local HTTP Server (e.g. http://192.168.x.x:8765/version.json)

Zero batch scripts - Defender-safe pure Python direct filesystem renaming.
Zero external packages - Python Standard Library only.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from app.core.config.loader import get_app_data_dir
from app.version import __version__, DEFAULT_UPDATE_SOURCE, UPDATE_CHECK_URL

logger = logging.getLogger("netguard.updater")


def parse_semver(v_str: str) -> Tuple[int, int, int]:
    """Parse semver string like '1.2.0', 'v1.3.1', or '2.0.0-rc1' into (1, 2, 0)."""
    clean = v_str.lstrip("v").strip()
    clean = clean.split("-")[0].split("+")[0].strip()
    parts = clean.split(".")
    try:
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return (major, minor, patch)
    except Exception:
        return (0, 0, 0)


def is_version_newer(remote_v: str, local_v: str = __version__) -> bool:
    """Returns True if remote_v is strictly newer than local_v."""
    return parse_semver(remote_v) > parse_semver(local_v)


def get_configured_update_source() -> str:
    """Retrieve the configured update source from persistent storage or environment."""
    env_val = os.environ.get("NETGUARD_UPDATE_SOURCE", "").strip()
    if env_val:
        return env_val

    try:
        cfg_file = get_app_data_dir() / "update_config.json"
        if cfg_file.exists():
            data = json.loads(cfg_file.read_text(encoding="utf-8"))
            src = data.get("update_source", "").strip()
            if src:
                return src
    except Exception as exc:
        logger.debug("Failed to read update_config.json: %s", exc)

    try:
        app_data = os.getenv("APPDATA")
        if app_data:
            settings_path = Path(app_data) / "NetGuard" / "user_settings.json"
            if settings_path.exists():
                data = json.loads(settings_path.read_text(encoding="utf-8"))
                src = (data.get("update_source") or data.get("custom", {}).get("update_source", "")).strip()
                if src:
                    return src
    except Exception as exc:
        logger.debug("Failed to read user_settings.json for update_source: %s", exc)

    return DEFAULT_UPDATE_SOURCE or UPDATE_CHECK_URL


def save_configured_update_source(source: str, auto_install: Optional[bool] = None) -> None:
    """Persist the configured update source to local storage without rebuilding binary."""
    clean_src = str(source).strip()

    try:
        data_dir = get_app_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        cfg_file = data_dir / "update_config.json"
        cfg: Dict[str, Any] = {}
        if cfg_file.exists():
            try:
                cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
            except Exception:
                cfg = {}
        cfg["update_source"] = clean_src
        if auto_install is not None:
            cfg["auto_install_updates"] = bool(auto_install)
        cfg_file.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        logger.info("Saved update configuration to %s", cfg_file)
    except Exception as exc:
        logger.warning("Failed to save update_config.json: %s", exc)

    try:
        app_data = os.getenv("APPDATA")
        if app_data:
            settings_dir = Path(app_data) / "NetGuard"
            settings_dir.mkdir(parents=True, exist_ok=True)
            settings_path = settings_dir / "user_settings.json"
            data: Dict[str, Any] = {}
            if settings_path.exists():
                try:
                    data = json.loads(settings_path.read_text(encoding="utf-8"))
                except Exception:
                    data = {}
            if "custom" not in data or not isinstance(data["custom"], dict):
                data["custom"] = {}
            data["custom"]["update_source"] = clean_src
            data["update_source"] = clean_src
            if auto_install is not None:
                data["custom"]["auto_install_updates"] = bool(auto_install)
                data["auto_install_updates"] = bool(auto_install)
            settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.debug("Could not write to user_settings.json: %s", exc)


def get_auto_install_updates() -> bool:
    """Retrieve auto_install_updates preference (default True)."""
    env_val = os.environ.get("NETGUARD_AUTO_INSTALL_UPDATES", "").strip().lower()
    if env_val in ("1", "true", "yes"):
        return True
    elif env_val in ("0", "false", "no"):
        return False

    try:
        cfg_file = get_app_data_dir() / "update_config.json"
        if cfg_file.exists():
            data = json.loads(cfg_file.read_text(encoding="utf-8"))
            if "auto_install_updates" in data:
                return bool(data["auto_install_updates"])
    except Exception:
        pass

    try:
        app_data = os.getenv("APPDATA")
        if app_data:
            settings_path = Path(app_data) / "NetGuard" / "user_settings.json"
            if settings_path.exists():
                data = json.loads(settings_path.read_text(encoding="utf-8"))
                val = data.get("auto_install_updates")
                if val is None:
                    val = data.get("custom", {}).get("auto_install_updates")
                if val is not None:
                    return bool(val)
    except Exception:
        pass

    return True


def save_auto_install_updates(enabled: bool) -> None:
    """Persist auto_install_updates preference."""
    val = bool(enabled)
    try:
        data_dir = get_app_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        cfg_file = data_dir / "update_config.json"
        cfg: Dict[str, Any] = {}
        if cfg_file.exists():
            try:
                cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
            except Exception:
                cfg = {}
        cfg["auto_install_updates"] = val
        cfg_file.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("Failed saving auto_install_updates to update_config.json: %s", exc)

    try:
        app_data = os.getenv("APPDATA")
        if app_data:
            settings_path = Path(app_data) / "NetGuard" / "user_settings.json"
            if settings_path.exists():
                data = json.loads(settings_path.read_text(encoding="utf-8"))
                if "custom" not in data or not isinstance(data["custom"], dict):
                    data["custom"] = {}
                data["custom"]["auto_install_updates"] = val
                data["auto_install_updates"] = val
                settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def cleanup_stale_update_files() -> None:
    """Silently cleans up leftover .old and .pending files from previous updates on startup."""
    try:
        if getattr(sys, "frozen", False):
            current_exe = Path(sys.executable).resolve()
            exe_dir = current_exe.parent
            stem = current_exe.stem
            for suffix in (".exe.old", ".exe.pending", ".old", ".pending"):
                stale_path = exe_dir / f"{stem}{suffix}"
                if stale_path.exists():
                    try:
                        stale_path.unlink(missing_ok=True)
                        logger.info("Cleaned up stale update file: %s", stale_path)
                    except Exception as e:
                        logger.debug("Could not unlink %s: %s", stale_path, e)

        updates_dir = get_app_data_dir() / "updates"
        if updates_dir.exists():
            for f in updates_dir.glob("*.download"):
                try:
                    f.unlink(missing_ok=True)
                except Exception:
                    pass
    except Exception as exc:
        logger.debug("cleanup_stale_update_files ignored error: %s", exc)


def normalize_update_source(source: str) -> Tuple[str, str]:
    """Analyze and normalize update source string.

    Returns:
        (transport, normalized_manifest_target)
        where transport is 'http' or 'file'.
    """
    s = source.strip()
    if s.lower().startswith("http://") or s.lower().startswith("https://"):
        parsed = urllib.parse.urlparse(s)
        path = parsed.path
        if not path or path.endswith("/"):
            path = (path or "") + "version.json"
        elif not path.endswith(".json"):
            path = path + "/version.json"
        normalized = urllib.parse.urlunparse((
            parsed.scheme,
            parsed.netloc,
            path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
        return ("http", normalized)

    # File or UNC Path
    clean_path = s
    if clean_path.lower().startswith("file:///"):
        clean_path = clean_path[8:]
    elif clean_path.lower().startswith("file://"):
        clean_path = clean_path[7:]

    # Normalize Windows backslashes if UNC path
    if clean_path.startswith("//"):
        clean_path = "\\\\" + clean_path[2:].replace("/", "\\")

    p = Path(clean_path)
    if clean_path.endswith((".json", ".JSON")):
        normalized = str(p)
    else:
        normalized = str(p / "version.json")
    return ("file", normalized)


class UpdateChecker(QObject):
    """Production-ready Self-Hosted Update Service for NetGuard AI.

    Handles checking, downloading, SHA-256 verifying, and direct in-place replacement.
    """

    update_found = Signal(dict)           # {version, url, sha256, changelog, download_url, transport}
    up_to_date = Signal(str)              # Current version status message
    check_failed = Signal(str)            # Error description
    download_progress = Signal(int, int)  # (bytes_downloaded, total_bytes)
    download_finished = Signal(str)       # Path to verified staging executable
    download_failed = Signal(str)         # Failure message
    install_started = Signal()            # Replacement underway
    install_failed = Signal(str)          # Replacement failure message

    def __init__(self, check_url: Optional[str] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.check_url = (check_url if check_url is not None else get_configured_update_source()).strip()
        self._is_checking = False
        self._is_downloading = False
        self._current_manifest: Optional[Dict[str, Any]] = None

    def set_source(self, source: str) -> None:
        """Update active update source URL or UNC path."""
        self.check_url = source.strip()

    def check_for_updates_async(self) -> None:
        """Triggers asynchronous background update verification against the self-hosted source."""
        if self._is_checking:
            return
        self._is_checking = True

        def _worker() -> None:
            try:
                active_src = self.check_url.strip() or get_configured_update_source().strip()
                if not active_src:
                    self.check_failed.emit(
                        "لم يتم تحديد مسار أو رابط مصدر التحديثات الذاتي بعد.\n"
                        "يرجى إدخال مسار المجلد الشبكي (UNC) أو رابط خادم HTTP في حقل الإعدادات أعلاه."
                    )
                    return

                transport, manifest_loc = normalize_update_source(active_src)
                logger.info("Checking for updates via [%s] at: %s", transport, manifest_loc)

                manifest_data: Dict[str, Any] = {}

                if transport == "http":
                    req = urllib.request.Request(
                        manifest_loc,
                        headers={"User-Agent": f"NetGuardAI/{__version__} (Windows NT 10.0)"}
                    )
                    with urllib.request.urlopen(req, timeout=5.0) as resp:
                        if resp.status != 200:
                            raise RuntimeError(f"HTTP error {resp.status}: {resp.reason}")
                        content = resp.read().decode("utf-8")
                        manifest_data = json.loads(content)
                else:
                    if manifest_loc.startswith("\\\\"):
                        unc_host = manifest_loc.lstrip("\\").split("\\", 1)[0]
                        if unc_host:
                            # Wrap getaddrinfo + connect in a bounded daemon thread because Windows NetBIOS/LLMNR blocks past socket timeouts.
                            reach_err: List[Optional[Exception]] = [None]
                            done_ev = threading.Event()

                            def _probe_unc() -> None:
                                try:
                                    import socket
                                    with socket.create_connection((unc_host, 445), timeout=0.45):
                                        pass
                                except Exception as ex:
                                    reach_err[0] = ex
                                finally:
                                    done_ev.set()

                            threading.Thread(target=_probe_unc, daemon=True, name="UncReachProbe").start()
                            if not done_ev.wait(timeout=0.55):
                                raise FileNotFoundError(
                                    f"انتهت مهلة التحقق من خادم التحديثات الشبكي ({unc_host}) خلال 0.55s"
                                )
                            if reach_err[0] is not None:
                                raise FileNotFoundError(
                                    f"خادم التحديثات الشبكي ({unc_host}) غير متصل حالياً: {reach_err[0]}"
                                )
                    if not os.path.exists(manifest_loc):
                        raise FileNotFoundError(f"تعذر العثور على ملف الإصدار: {manifest_loc}")
                    with open(manifest_loc, "r", encoding="utf-8") as f:
                        manifest_data = json.load(f)

                remote_ver = str(manifest_data.get("version", "")).strip()
                raw_url = str(manifest_data.get("url", "NetGuard.exe")).strip()
                expected_sha = str(manifest_data.get("sha256", "")).strip()

                if not remote_ver:
                    raise ValueError("الملف المستلم version.json لا يحتوي على حقل version صالح.")

                # Resolve download target location
                if raw_url.lower().startswith("http://") or raw_url.lower().startswith("https://"):
                    resolved_url = raw_url
                elif raw_url.startswith(("\\\\", "//")) or (len(raw_url) > 1 and raw_url[1] == ":"):
                    resolved_url = raw_url
                else:
                    if transport == "http":
                        resolved_url = urllib.parse.urljoin(manifest_loc, raw_url)
                    else:
                        resolved_url = str(Path(manifest_loc).parent / raw_url)

                manifest_data["download_url"] = resolved_url
                manifest_data["transport"] = transport
                manifest_data["sha256"] = expected_sha
                manifest_data["manifest_source"] = active_src
                self._current_manifest = manifest_data

                if is_version_newer(remote_ver, __version__):
                    logger.info("New update discovered: %s (Current: %s)", remote_ver, __version__)
                    self.update_found.emit(manifest_data)
                else:
                    logger.info("Application is up to date (current: %s, remote: %s)", __version__, remote_ver)
                    self.up_to_date.emit(f"أنت تستخدم أحدث إصدار v{__version__} بنجاح.")

            except urllib.error.URLError as err:
                msg = f"تعذر الاتصال بخادم التحديثات ({active_src}): {err.reason}"
                logger.warning(msg)
                self.check_failed.emit(msg)
            except FileNotFoundError as fnf:
                msg = f"مسار التحديثات الشبكي غير متاح أو غير موجود: {fnf}"
                logger.warning(msg)
                self.check_failed.emit(msg)
            except Exception as exc:
                msg = f"خطأ أثناء التحقق من التحديثات: {exc}"
                logger.warning(msg)
                self.check_failed.emit(msg)
            finally:
                self._is_checking = False

        threading.Thread(target=_worker, daemon=True, name="UpdateCheckerThread").start()

    def download_update_async(self, manifest: Optional[Dict[str, Any]] = None) -> None:
        """Download new binary package and verify SHA-256 integrity."""
        if self._is_downloading:
            return
        self._is_downloading = True

        target_manifest = manifest or self._current_manifest
        if not target_manifest:
            self.download_failed.emit("بيانات التحديث غير متوفرة لبدء التنزيل.")
            self._is_downloading = False
            return

        def _worker() -> None:
            partial_path: Optional[Path] = None
            try:
                download_url = target_manifest["download_url"]
                transport = target_manifest.get("transport", "http")
                remote_ver = target_manifest.get("version", "new")
                expected_sha = target_manifest.get("sha256", "").strip().lower()

                dest_dir = get_app_data_dir() / "updates"
                dest_dir.mkdir(parents=True, exist_ok=True)

                staged_exe = dest_dir / f"NetGuard_v{remote_ver}.exe"
                partial_path = staged_exe.with_suffix(".download")

                if partial_path.exists():
                    partial_path.unlink(missing_ok=True)

                hasher = sha256()
                bytes_downloaded = 0
                chunk_size = 65536  # 64 KB

                logger.info("Starting download of update %s from %s", remote_ver, download_url)

                if transport == "http" or download_url.lower().startswith(("http://", "https://")):
                    req = urllib.request.Request(
                        download_url,
                        headers={"User-Agent": f"NetGuardAI/{__version__} (Windows NT 10.0)"}
                    )
                    with urllib.request.urlopen(req, timeout=30.0) as resp:
                        total_bytes = int(resp.headers.get("Content-Length", 0))
                        with open(partial_path, "wb") as f_out:
                            while True:
                                chunk = resp.read(chunk_size)
                                if not chunk:
                                    break
                                f_out.write(chunk)
                                hasher.update(chunk)
                                bytes_downloaded += len(chunk)
                                self.download_progress.emit(bytes_downloaded, total_bytes)
                else:
                    source_path = Path(download_url)
                    if not source_path.exists():
                        raise FileNotFoundError(f"حزمة التحديث التنفيذية غير موجودة في المسار: {source_path}")
                    total_bytes = source_path.stat().st_size
                    with open(source_path, "rb") as f_in, open(partial_path, "wb") as f_out:
                        while True:
                            chunk = f_in.read(chunk_size)
                            if not chunk:
                                break
                            f_out.write(chunk)
                            hasher.update(chunk)
                            bytes_downloaded += len(chunk)
                            self.download_progress.emit(bytes_downloaded, total_bytes)

                # SHA-256 Integrity Verification
                computed_sha = hasher.hexdigest().lower()
                if expected_sha and computed_sha != expected_sha:
                    if partial_path.exists():
                        partial_path.unlink(missing_ok=True)
                    err_msg = (
                        f"فشل التحقق من أمان الحزمة: رمز SHA-256 غير مطابق!\n\n"
                        f"المتوقع: {expected_sha}\n"
                        f"المحسوب: {computed_sha}\n\n"
                        f"تم إلغاء التحديث تلقائياً لحماية النظام من أي تلف أو تلاعب."
                    )
                    logger.error(err_msg)
                    self.download_failed.emit(err_msg)
                    return

                # Finalize staging
                if staged_exe.exists():
                    staged_exe.unlink(missing_ok=True)
                os.replace(partial_path, staged_exe)

                logger.info("Update downloaded and verified successfully: %s (SHA-256: %s)", staged_exe, computed_sha)
                self.download_finished.emit(str(staged_exe))

            except Exception as exc:
                if partial_path and partial_path.exists():
                    try:
                        partial_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                msg = f"فشل تنزيل ملف التحديث: {exc}"
                logger.warning(msg)
                self.download_failed.emit(msg)
            finally:
                self._is_downloading = False

        threading.Thread(target=_worker, daemon=True, name="UpdateDownloadThread").start()

    def apply_update_and_restart(self, new_exe_path: str) -> bool:
        """Executes Defender-safe direct filesystem replacement and restarts NetGuard AI.

        Zero batch scripts - pure Python direct rename:
          1. Guard against non-frozen dev mode (never rename python.exe).
          2. Stage verified binary to NetGuard.exe.pending.
          3. Remove any stale NetGuard.exe.old.
          4. Rename running NetGuard.exe -> NetGuard.exe.old (permitted by Windows NTFS).
          5. Rename NetGuard.exe.pending -> NetGuard.exe.
          6. Roll back (NetGuard.exe.old -> NetGuard.exe) if step 5 fails.
          7. Launch new NetGuard.exe via detached subprocess and quit.
        """
        try:
            self.install_started.emit()
            is_frozen = getattr(sys, "frozen", False)
            staged_path = Path(new_exe_path).resolve()

            if not staged_path.exists():
                raise FileNotFoundError(f"ملف التحديث المجهز غير موجود: {staged_path}")

            # Guard against dev mode: never rename python.exe
            if not is_frozen:
                info_msg = (
                    f"نمط التطوير المباشر:\n"
                    f"تم تنزيل الحزمة والتحقق من سلامة التجزئة بنجاح ({staged_path.name}).\n"
                    f"ميزة الاستبدال المباشر للـ EXE وإعادة التشغيل تعمل عند تشغيل حزمة NetGuard.exe المجمعة."
                )
                logger.info("Development environment detected. Not renaming python.exe. Staged at: %s", staged_path)
                self.install_failed.emit(info_msg)
                return True

            current_exe = Path(sys.executable).resolve()
            exe_dir = current_exe.parent
            stem = current_exe.stem

            old_exe = exe_dir / f"{stem}.exe.old"
            pending_exe = exe_dir / f"{stem}.exe.pending"

            # 1. Stage to pending file on the same drive/directory for atomic rename
            if staged_path != pending_exe:
                if pending_exe.exists():
                    pending_exe.unlink(missing_ok=True)
                shutil.copy2(staged_path, pending_exe)

            # 2. Clean up any stale old backup
            if old_exe.exists():
                try:
                    old_exe.unlink(missing_ok=True)
                except Exception as e:
                    logger.warning("Could not delete stale %s: %s", old_exe, e)

            # 3. Rename running executable -> old_exe (allowed by Windows NTFS)
            logger.info("Renaming running executable: %s -> %s", current_exe, old_exe)
            os.replace(current_exe, old_exe)

            # 4. Rename pending -> current_exe
            try:
                logger.info("Promoting pending update: %s -> %s", pending_exe, current_exe)
                os.replace(pending_exe, current_exe)
            except Exception as rename_err:
                logger.critical("Failed to promote pending exe: %s. Initiating rollback...", rename_err)
                try:
                    os.replace(old_exe, current_exe)
                    logger.info("Rollback successful. Restored running version.")
                except Exception as rb_err:
                    logger.critical("CRITICAL: Rollback failed: %s", rb_err)
                raise rename_err

            # 5. Launch newly replaced executable detached (Defender-safe, pure Python, zero .bat)
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

            logger.info("Launching updated binary: %s", current_exe)
            subprocess.Popen(
                [str(current_exe)],
                creationflags=creationflags,
                close_fds=True,
            )

            # 6. Clean application exit
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.quit()
            else:
                sys.exit(0)
            return True

        except Exception as exc:
            err = f"تعذر تنفيذ استبدال الملف المباشر وإعادة التشغيل: {exc}"
            logger.error(err)
            self.install_failed.emit(err)
            return False
