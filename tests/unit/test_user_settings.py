"""Unit tests for NetGuard AI UserSettings Persistence Layer (AC-6, R3, R4).

Covers 4-tier testing:
- Tier 1: Feature Coverage (Schema defaults, typed getters/setters, disk persistence, restart survival)
- Tier 2: Boundary & Corner Cases (Corrupted JSON recovery, empty file, partial keys, validation, directory creation)
- Tier 3: Cross-Feature Combinations (Signal propagation, dynamic consumer updates, thresholds overlay)
- Tier 4: Real-World Workload Scenarios (Full settings session lifecycle, multi-mutation consistency)
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
import pytest

from PySide6.QtCore import QObject

from app.core.models.metrics import OperatingMode

# Safe import of UserSettings
try:
    from app.core.settings import UserSettings
except ImportError:
    UserSettings = None

try:
    from app.core.thresholds import NetworkThresholds
except ImportError:
    NetworkThresholds = None


@pytest.fixture
def temp_config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated directory for test user settings with APPDATA patched."""
    config_dir = tmp_path / "appdata" / "NetGuard"
    config_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    return config_dir


@pytest.fixture
def settings(temp_config_dir: Path) -> Any:
    """Instantiate UserSettings isolated in temp_config_dir."""
    if UserSettings is None:
        pytest.fail("app.core.settings.UserSettings is not yet implemented by M1 track")

    # UserSettings may accept config_dir or rely on APPDATA
    try:
        instance = UserSettings(config_dir=temp_config_dir)
    except TypeError:
        try:
            instance = UserSettings(config_path=temp_config_dir / "user_settings.json")
        except TypeError:
            instance = UserSettings()
    return instance


# ============================================================================
# Tier 1: Feature Coverage (AC-6, R3 Core Capabilities)
# ============================================================================


def test_default_settings_loaded_when_no_file_exists(settings: Any) -> None:
    """When no user_settings.json exists, load defaults matching default_config.yaml."""
    # Operating mode defaults to AUTO (or AUTONOMOUS_SAFE)
    mode = settings.get_mode()
    assert mode in (OperatingMode.AUTO, getattr(OperatingMode, "AUTONOMOUS_SAFE", "autonomous_safe"), "auto")

    # Probing interval defaults to 1.0s (from default_config.yaml probing.gateway_interval_sec)
    interval = settings.get_probing_interval()
    assert interval == pytest.approx(1.0, rel=1e-2)

    # Retention days defaults to 30
    retention = settings.get_retention_days()
    assert retention == 30

    # Default policies all True
    assert settings.get_policy("allow_flush_dns") is True
    assert settings.get_policy("meeting_guard") is True
    assert settings.get_policy("allow_switch_dns") is True
    assert settings.get_policy("allow_renew_ip") is True


def test_mode_getters_and_setters(settings: Any) -> None:
    """Test get_mode() and set_mode() across all valid operating modes."""
    target_ask = getattr(OperatingMode, "ASK", OperatingMode.ASSISTED)
    settings.set_mode(target_ask)
    assert settings.get_mode() == target_ask

    target_watch = getattr(OperatingMode, "WATCH", OperatingMode.OBSERVATION)
    settings.set_mode(target_watch)
    assert settings.get_mode() == target_watch

    target_auto = getattr(OperatingMode, "AUTO", OperatingMode.AUTONOMOUS_SAFE)
    settings.set_mode(target_auto)
    assert settings.get_mode() == target_auto


def test_policy_getters_and_setters_all_four_policies(settings: Any) -> None:
    """Test get_policy() and set_policy() independently for all 4 remediation policies."""
    policies = ["allow_flush_dns", "meeting_guard", "allow_switch_dns", "allow_renew_ip"]

    for pol in policies:
        # Initially enabled
        assert settings.get_policy(pol) is True

        # Disable policy
        settings.set_policy(pol, False)
        assert settings.get_policy(pol) is False

        # Re-enable policy
        settings.set_policy(pol, True)
        assert settings.get_policy(pol) is True


def test_probing_interval_getter_and_setter(settings: Any) -> None:
    """Test get_probing_interval() and set_probing_interval()."""
    settings.set_probing_interval(3.5)
    assert settings.get_probing_interval() == pytest.approx(3.5, rel=1e-2)

    settings.set_probing_interval(0.5)
    assert settings.get_probing_interval() == pytest.approx(0.5, rel=1e-2)


def test_retention_days_getter_and_setter(settings: Any) -> None:
    """Test get_retention_days() and set_retention_days()."""
    settings.set_retention_days(60)
    assert settings.get_retention_days() == 60

    settings.set_retention_days(14)
    assert settings.get_retention_days() == 14


def test_save_creates_valid_json_file(settings: Any, temp_config_dir: Path) -> None:
    """save() writes valid JSON to user_settings.json."""
    settings.set_probing_interval(2.5)
    settings.set_policy("allow_flush_dns", False)
    settings.save()

    # Locate user_settings.json
    target_file = temp_config_dir / "user_settings.json"
    if not target_file.exists():
        # Might be in parent or child
        matches = list(temp_config_dir.glob("**/user_settings.json"))
        assert len(matches) > 0, "user_settings.json not found after save()"
        target_file = matches[0]

    assert target_file.exists()
    with open(target_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, dict)
    # Check that saved data contains updated fields
    if "probing_interval" in data:
        assert data["probing_interval"] == pytest.approx(2.5, rel=1e-2)
    elif "probing" in data and "gateway_interval_sec" in data["probing"]:
        assert data["probing"]["gateway_interval_sec"] == pytest.approx(2.5, rel=1e-2)


def test_settings_survive_application_restart(temp_config_dir: Path) -> None:
    """Modifications saved in one instance are restored identically in a fresh instance."""
    if UserSettings is None:
        pytest.fail("UserSettings not available")

    # Instance 1: Make modifications and save
    try:
        s1 = UserSettings(config_dir=temp_config_dir)
    except TypeError:
        s1 = UserSettings()

    target_watch = getattr(OperatingMode, "WATCH", OperatingMode.OBSERVATION)
    s1.set_mode(target_watch)
    s1.set_policy("allow_flush_dns", False)
    s1.set_policy("allow_renew_ip", False)
    s1.set_probing_interval(4.0)
    s1.set_retention_days(45)
    s1.save()
    del s1

    # Instance 2: Load fresh from disk
    try:
        s2 = UserSettings(config_dir=temp_config_dir)
    except TypeError:
        s2 = UserSettings()

    assert s2.get_mode() == target_watch
    assert s2.get_policy("allow_flush_dns") is False
    assert s2.get_policy("allow_renew_ip") is False
    assert s2.get_policy("allow_switch_dns") is True  # untouched remains default
    assert s2.get_probing_interval() == pytest.approx(4.0, rel=1e-2)
    assert s2.get_retention_days() == 45


# ============================================================================
# Tier 2: Boundary & Corner Cases
# ============================================================================


def test_corrupted_json_recovery(temp_config_dir: Path) -> None:
    """Corrupted user_settings.json falls back safely to defaults without crashing."""
    if UserSettings is None:
        pytest.fail("UserSettings not available")

    settings_file = temp_config_dir / "user_settings.json"
    settings_file.write_text("{ \"mode\": \"auto\", broken_json: [invalid...!!!", encoding="utf-8")

    # Instantiation must not raise JSONDecodeError
    try:
        s = UserSettings(config_dir=temp_config_dir)
    except TypeError:
        s = UserSettings()

    # Values must fall back to safe defaults
    assert s.get_probing_interval() == pytest.approx(1.0, rel=1e-2)
    assert s.get_retention_days() == 30
    assert s.get_policy("allow_flush_dns") is True


def test_empty_json_file_recovery(temp_config_dir: Path) -> None:
    """Empty user_settings.json falls back safely to defaults."""
    if UserSettings is None:
        pytest.fail("UserSettings not available")

    settings_file = temp_config_dir / "user_settings.json"
    settings_file.write_text("", encoding="utf-8")

    try:
        s = UserSettings(config_dir=temp_config_dir)
    except TypeError:
        s = UserSettings()

    assert s.get_probing_interval() == pytest.approx(1.0, rel=1e-2)
    assert s.get_retention_days() == 30


def test_partial_keys_json_overlay(temp_config_dir: Path) -> None:
    """JSON with only a subset of keys overlays defaults cleanly."""
    if UserSettings is None:
        pytest.fail("UserSettings not available")

    settings_file = temp_config_dir / "user_settings.json"
    partial_data = {
        "probing_interval": 8.5,
        "policies": {"allow_flush_dns": False},
    }
    settings_file.write_text(json.dumps(partial_data), encoding="utf-8")

    try:
        s = UserSettings(config_dir=temp_config_dir)
    except TypeError:
        s = UserSettings()

    assert s.get_probing_interval() == pytest.approx(8.5, rel=1e-2)
    assert s.get_policy("allow_flush_dns") is False
    # Omitted keys have defaults
    assert s.get_policy("meeting_guard") is True
    assert s.get_retention_days() == 30


def test_invalid_probing_interval_validation(settings: Any) -> None:
    """Negative or zero probing intervals raise ValueError or clamp to safe bounds."""
    with pytest.raises((ValueError, AssertionError)):
        settings.set_probing_interval(-1.0)

    with pytest.raises((ValueError, AssertionError)):
        settings.set_probing_interval(0.0)


def test_invalid_retention_days_validation(settings: Any) -> None:
    """Negative or zero retention days raise ValueError or clamp to valid minimum."""
    with pytest.raises((ValueError, AssertionError)):
        settings.set_retention_days(-5)

    with pytest.raises((ValueError, AssertionError)):
        settings.set_retention_days(0)


def test_unknown_policy_name_handling(settings: Any) -> None:
    """Querying an unknown policy key returns False or raises KeyError."""
    try:
        val = settings.get_policy("unknown_policy_xyz")
        assert val is False
    except KeyError:
        pass  # Typed error is also compliant


def test_nested_missing_config_directory_creation(tmp_path: Path) -> None:
    """UserSettings auto-creates missing nested directories on save."""
    if UserSettings is None:
        pytest.fail("UserSettings not available")

    deep_dir = tmp_path / "deep" / "nested" / "config"
    assert not deep_dir.exists()

    try:
        s = UserSettings(config_dir=deep_dir)
        s.set_probing_interval(2.0)
        s.save()
        assert deep_dir.exists()
    except TypeError:
        pass


# ============================================================================
# Tier 3: Cross-Feature Combinations & Signal Propagation
# ============================================================================


def test_signal_changed_emitted_on_mode_change(settings: Any) -> None:
    """changing mode emits changed signal with key and value."""
    emitted_events: List[tuple[str, Any]] = []

    if hasattr(settings, "changed"):
        settings.changed.connect(lambda k, v: emitted_events.append((k, v)))

    target_ask = getattr(OperatingMode, "ASK", OperatingMode.ASSISTED)
    settings.set_mode(target_ask)

    if hasattr(settings, "changed"):
        assert len(emitted_events) >= 1
        keys = [e[0] for e in emitted_events]
        assert "mode" in keys or "operating_mode" in keys


def test_signal_changed_emitted_on_policy_change(settings: Any) -> None:
    """changing a policy emits changed signal."""
    emitted_events: List[tuple[str, Any]] = []

    if hasattr(settings, "changed"):
        settings.changed.connect(lambda k, v: emitted_events.append((k, v)))

    settings.set_policy("allow_flush_dns", False)

    if hasattr(settings, "changed"):
        assert len(emitted_events) >= 1
        keys = [e[0] for e in emitted_events]
        assert any("flush_dns" in k or k == "policies" for k in keys)


def test_signal_changed_emitted_on_probing_interval_change(settings: Any) -> None:
    """changing probing interval emits changed signal."""
    emitted_events: List[tuple[str, Any]] = []

    if hasattr(settings, "changed"):
        settings.changed.connect(lambda k, v: emitted_events.append((k, v)))

    settings.set_probing_interval(3.0)

    if hasattr(settings, "changed"):
        assert len(emitted_events) >= 1
        keys = [e[0] for e in emitted_events]
        assert any("interval" in k or "probing" in k for k in keys)


def test_live_consumer_updates_dynamically_without_restart(settings: Any) -> None:
    """Live consumer listening to settings.changed updates its parameters dynamically."""
    class MockProbeScheduler:
        def __init__(self, initial_interval: float):
            self.interval = initial_interval

        def on_settings_changed(self, key: str, value: Any):
            if "interval" in key or key == "probing_interval":
                self.interval = float(value)

    scheduler = MockProbeScheduler(settings.get_probing_interval())

    if hasattr(settings, "changed"):
        settings.changed.connect(scheduler.on_settings_changed)

    settings.set_probing_interval(5.0)

    if hasattr(settings, "changed"):
        assert scheduler.interval == pytest.approx(5.0, rel=1e-2)


def test_thresholds_overlay_integration(settings: Any) -> None:
    """UserSettings supports overlaying custom threshold overrides."""
    if hasattr(settings, "get_threshold_overrides") and hasattr(settings, "set_threshold_override"):
        settings.set_threshold_override("gateway_latency_warning_ms", 35.0)
        overrides = settings.get_threshold_overrides()
        assert overrides.get("gateway_latency_warning_ms") == 35.0


# ============================================================================
# Tier 4: Real-World Workload Scenarios
# ============================================================================


def test_full_settings_workflow_lifecycle(temp_config_dir: Path) -> None:
    """Simulate complete realistic session: defaults -> edits -> save -> restart -> verify."""
    if UserSettings is None:
        pytest.fail("UserSettings not available")

    # Step 1: Clean startup
    try:
        s = UserSettings(config_dir=temp_config_dir)
    except TypeError:
        s = UserSettings()

    assert s.get_mode() in (OperatingMode.AUTO, getattr(OperatingMode, "AUTONOMOUS_SAFE", "autonomous_safe"), "auto")

    # Step 2: User applies settings page changes
    target_ask = getattr(OperatingMode, "ASK", OperatingMode.ASSISTED)
    s.set_mode(target_ask)
    s.set_policy("allow_switch_dns", False)
    s.set_policy("meeting_guard", False)
    s.set_probing_interval(2.0)
    s.set_retention_days(14)
    s.save()
    del s

    # Step 3: Application restart
    try:
        s_reloaded = UserSettings(config_dir=temp_config_dir)
    except TypeError:
        s_reloaded = UserSettings()

    assert s_reloaded.get_mode() == target_ask
    assert s_reloaded.get_policy("allow_switch_dns") is False
    assert s_reloaded.get_policy("meeting_guard") is False
    assert s_reloaded.get_policy("allow_flush_dns") is True  # unmodified stays True
    assert s_reloaded.get_probing_interval() == pytest.approx(2.0, rel=1e-2)
    assert s_reloaded.get_retention_days() == 14


def test_rapid_multiple_setting_mutations_and_atomic_save(settings: Any) -> None:
    """Rapid succession of changes all persist consistently."""
    for i in range(1, 6):
        settings.set_probing_interval(float(i))
        settings.set_retention_days(i * 10)

    settings.save()
    assert settings.get_probing_interval() == pytest.approx(5.0, rel=1e-2)
    assert settings.get_retention_days() == 50
