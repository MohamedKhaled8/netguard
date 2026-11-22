"""Configuration file loader with fallback defaults."""

from __future__ import annotations
import os
from pathlib import Path
from typing import Optional
import yaml
from app.core.config.models import AppConfig
from app.core.exceptions.base import ConfigurationError


def get_app_root() -> Path:
    """Returns canonical project/application root directory."""
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent.parent


def get_app_data_dir() -> Path:
    """Returns dedicated data directory for NetGuard AI.

    Stores all databases and logs in D:\\NetGuard (or root drive if D: unavailable)
    completely separated from Windows user AppData.
    """
    import sys
    if sys.platform == "win32":
        if os.path.exists("D:\\"):
            d = Path("D:/NetGuard")
        else:
            drive = os.path.splitdrive(sys.executable)[0] or "C:"
            d = Path(f"{drive}/NetGuard")
    elif sys.platform == "darwin":
        d = Path.home() / "Library" / "Application Support" / "NetGuard"
    else:
        d = Path.home() / ".local" / "share" / "netguard"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_config(config_path: Optional[Path | str] = None) -> AppConfig:
    """Loads configuration from YAML file or returns validated defaults."""
    app_root = get_app_root()
    if config_path is None:
        import sys
        base = Path(sys._MEIPASS) if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS") else app_root
        # Check standard paths
        candidates = [
            base / "config" / "default_config.yaml",
            app_root / "config" / "default_config.yaml",
            app_root / "config" / "config.yaml",
            app_root / "netguard.yaml",
            Path("config/default_config.yaml"),
            Path("config/config.yaml"),
        ]
        for candidate in candidates:
            if candidate.exists():
                config_path = candidate
                break

    cfg: AppConfig
    if config_path and Path(config_path).exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            cfg = AppConfig(**data)
        except Exception as exc:
            raise ConfigurationError(f"Failed to parse configuration file {config_path}: {exc}") from exc
    else:
        # Default configuration
        cfg = AppConfig()

    # Separate application binary from runtime database & logs to keep folder completely clean
    import sys
    is_frozen = getattr(sys, "frozen", False)
    storage_root = get_app_data_dir() if is_frozen else app_root

    # Canonicalize relative database and logging paths
    if cfg.database and cfg.database.db_path and not os.path.isabs(cfg.database.db_path):
        cfg.database.db_path = str(storage_root / cfg.database.db_path)
    if cfg.logging and cfg.logging.log_dir and not os.path.isabs(cfg.logging.log_dir):
        cfg.logging.log_dir = str(storage_root / cfg.logging.log_dir)

    # Ensure target directories exist
    try:
        os.makedirs(os.path.dirname(cfg.database.db_path), exist_ok=True)
        os.makedirs(cfg.logging.log_dir, exist_ok=True)
    except Exception:
        pass

    return cfg

