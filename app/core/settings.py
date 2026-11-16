"""User Settings Persistence Layer for NetGuard AI.

Provides JSON file persistence in %APPDATA%/NetGuard/user_settings.json
with cross-platform fallback, schema validation, and PySide6 signals.
"""

from __future__ import annotations
import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator
from PySide6.QtCore import QObject, Signal

from app.core.models.metrics import OperatingMode
from app.core.config.loader import load_config
from app.core.config.models import AppConfig
from app.core.bus import EventBus, EventTopics

logger = logging.getLogger("netguard.core.settings")


class UserSettingsSchema(BaseModel):
    """Pydantic validation schema for persisted user settings."""
    mode: OperatingMode = Field(default=OperatingMode.AUTO)
    probing_interval: float = Field(default=1.0, ge=0.01, le=3600.0)
    retention_days: int = Field(default=30, ge=1, le=3650)
    policies: Dict[str, bool] = Field(
        default_factory=lambda: {
            "allow_flush_dns": True,
            "meeting_guard": True,
            "allow_switch_dns": True,
            "allow_renew_ip": True,
            "auto_flush_dns": True,
            "auto_switch_dns": True,
            "auto_renew_dhcp": True,
            "allow_level_3_disruptive": False,
        }
    )
    threshold_overrides: Dict[str, Any] = Field(default_factory=dict)
    custom: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("mode", mode="before")
    @classmethod
    def parse_mode(cls, v: Any) -> OperatingMode:
        if isinstance(v, OperatingMode):
            return v
        if isinstance(v, str):
            return OperatingMode(v)
        return OperatingMode.AUTO


class UserSettings(QObject):
    """Persistent user settings overlay with schema validation and Qt signals."""

    changed = Signal(str, object)  # (setting_key, new_value)
    mode_changed = Signal(OperatingMode)

    POLICY_ALIASES = {
        "auto_flush_dns": "allow_flush_dns",
        "allow_flush_dns": "auto_flush_dns",
        "auto_switch_dns": "allow_switch_dns",
        "allow_switch_dns": "auto_switch_dns",
        "auto_renew_dhcp": "allow_renew_ip",
        "allow_renew_ip": "auto_renew_dhcp",
    }

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        config_dir: Optional[Path | str] = None,
        user_settings_path: Optional[Path | str] = None,
        config_path: Optional[Path | str] = None,
        event_bus: Optional[EventBus] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.event_bus = event_bus
        self._default_config = config or load_config()
        self.file_path = self._resolve_settings_path(
            custom_path=user_settings_path or config_path,
            custom_dir=config_dir,
        )
        self._data: UserSettingsSchema = self._load()

    @staticmethod
    def _resolve_settings_path(
        custom_path: Optional[Path | str] = None,
        custom_dir: Optional[Path | str] = None,
    ) -> Path:
        if custom_path is not None:
            return Path(custom_path)
        if custom_dir is not None:
            return Path(custom_dir) / "user_settings.json"
        app_data = os.getenv("APPDATA")
        if app_data:
            return Path(app_data) / "NetGuard" / "user_settings.json"
        return Path.home() / ".config" / "NetGuard" / "user_settings.json"

    def _get_defaults(self) -> Dict[str, Any]:
        return {
            "mode": OperatingMode(self._default_config.remediation.mode),
            "probing_interval": float(self._default_config.probing.gateway_interval_sec),
            "retention_days": int(self._default_config.database.retention_days),
            "policies": {
                "allow_flush_dns": True,
                "meeting_guard": True,
                "allow_switch_dns": True,
                "allow_renew_ip": True,
                "auto_flush_dns": True,
                "auto_switch_dns": True,
                "auto_renew_dhcp": True,
                "allow_level_3_disruptive": getattr(self._default_config.remediation, "allow_level_3_disruptive", False),
            },
            "threshold_overrides": {},
            "custom": {},
        }

    def _load(self) -> UserSettingsSchema:
        """Loads settings from disk overlaying default configuration."""
        defaults = self._get_defaults()

        if self.file_path.exists():
            try:
                content = self.file_path.read_text(encoding="utf-8").strip()
                if not content:
                    logger.warning("user_settings.json at %s is empty. Using defaults.", self.file_path)
                    return UserSettingsSchema.model_validate(defaults)
                raw_data = json.loads(content)
                if isinstance(raw_data, dict):
                    merged = dict(defaults)
                    for k, v in raw_data.items():
                        if k == "policies" and isinstance(v, dict):
                            merged_policies = dict(defaults["policies"])
                            merged_policies.update(v)
                            merged["policies"] = merged_policies
                        else:
                            merged[k] = v
                    return UserSettingsSchema.model_validate(merged)
            except Exception as exc:
                logger.warning("Failed to load user settings from %s: %s. Using defaults.", self.file_path, exc)

        return UserSettingsSchema.model_validate(defaults)

    def save(self) -> None:
        """Atomically saves settings to disk."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.file_path.with_suffix(".tmp")
            content = self._data.model_dump_json(indent=2)
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.file_path)
            logger.info("User settings saved successfully to %s", self.file_path)
        except Exception as exc:
            logger.error("Failed to save user settings to %s: %s", self.file_path, exc)
            raise

    # Typed Getters & Setters
    def get_mode(self) -> OperatingMode:
        return self._data.mode

    def set_mode(self, mode: OperatingMode | str) -> None:
        target_mode = OperatingMode(mode)
        if self._data.mode != target_mode:
            self._data.mode = target_mode
            self.save()
            self.mode_changed.emit(target_mode)
            self.changed.emit("mode", target_mode)
            if self.event_bus:
                self.event_bus.publish_sync(EventTopics.MODE_CHANGED, {"mode": target_mode.value})

    def get_policy(self, name: str) -> bool:
        if name in self._data.policies:
            return self._data.policies[name]
        alias = self.POLICY_ALIASES.get(name)
        if alias and alias in self._data.policies:
            return self._data.policies[alias]
        return False

    def set_policy(self, name: str, enabled: bool) -> None:
        val = bool(enabled)
        old_val = self.get_policy(name)
        self._data.policies[name] = val
        alias = self.POLICY_ALIASES.get(name)
        if alias:
            self._data.policies[alias] = val
        if old_val != val or name not in self._data.policies:
            self.save()
            self.changed.emit(f"policy.{name}", val)
            if self.event_bus:
                self.event_bus.publish_sync(EventTopics.SETTINGS_CHANGED, {"policy": name, "enabled": val})

    def get_probing_interval(self) -> float:
        return self._data.probing_interval

    def set_probing_interval(self, sec: float) -> None:
        val = float(sec)
        if val <= 0.0:
            raise ValueError(f"Probing interval must be > 0, got {val}")
        if self._data.probing_interval != val:
            self._data.probing_interval = val
            self.save()
            self.changed.emit("probing_interval", val)
            if self.event_bus:
                self.event_bus.publish_sync(EventTopics.SETTINGS_CHANGED, {"probing_interval": val})

    def get_retention_days(self) -> int:
        return self._data.retention_days

    def set_retention_days(self, days: int) -> None:
        val = int(days)
        if val < 1:
            raise ValueError(f"Retention days must be >= 1, got {val}")
        if self._data.retention_days != val:
            self._data.retention_days = val
            self.save()
            self.changed.emit("retention_days", val)
            if self.event_bus:
                self.event_bus.publish_sync(EventTopics.SETTINGS_CHANGED, {"retention_days": val})

    def get_threshold_overrides(self) -> Dict[str, Any]:
        return dict(self._data.threshold_overrides)

    def set_threshold_override(self, key: str, value: Any) -> None:
        self._data.threshold_overrides[key] = value
        self.save()
        self.changed.emit(f"threshold.{key}", value)
        if self.event_bus:
            self.event_bus.publish_sync(EventTopics.SETTINGS_CHANGED, {"threshold": {key: value}})
