"""Configuration file loader with fallback defaults."""

from __future__ import annotations
import os
from pathlib import Path
from typing import Optional
import yaml
from app.core.config.models import AppConfig
from app.core.exceptions.base import ConfigurationError


def load_config(config_path: Optional[Path | str] = None) -> AppConfig:
    """Loads configuration from YAML file or returns validated defaults."""
    if config_path is None:
        # Check standard paths
        candidates = [
            Path("config/default_config.yaml"),
            Path("config/config.yaml"),
            Path("netguard.yaml"),
        ]
        for candidate in candidates:
            if candidate.exists():
                config_path = candidate
                break

    if config_path and Path(config_path).exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return AppConfig(**data)
        except Exception as exc:
            raise ConfigurationError(f"Failed to parse configuration file {config_path}: {exc}") from exc

    # Default configuration
    return AppConfig()

