"""Tests for the settings manager module.

This module tests the SettingsManager class for persistent settings
storage and retrieval.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


class TestGetDefaultSettings:
    """Tests for get_default_settings function."""

    def test_default_settings_has_encoding(self) -> None:
        """Test that default settings include encoding category."""
        from video_converter.gui.services.settings_manager import get_default_settings

        settings = get_default_settings()
        assert "encoding" in settings
        assert "encoder" in settings["encoding"]
        assert "quality" in settings["encoding"]
        assert "preset" in settings["encoding"]

    def test_default_settings_has_paths(self) -> None:
        """Test that default settings include paths category."""
        from video_converter.gui.services.settings_manager import get_default_settings

        settings = get_default_settings()
        assert "paths" in settings
        assert "output_dir" in settings["paths"]
        assert "naming_pattern" in settings["paths"]

    def test_default_settings_has_automation(self) -> None:
        """Test that default settings include automation category."""
        from video_converter.gui.services.settings_manager import get_default_settings

        settings = get_default_settings()
        assert "automation" in settings
        assert "delete_original" in settings["automation"]
        assert "skip_existing" in settings["automation"]

    def test_default_settings_has_notifications(self) -> None:
        """Test that default settings include notifications category."""
        from video_converter.gui.services.settings_manager import get_default_settings

        settings = get_default_settings()
        assert "notifications" in settings
        assert "notify_complete" in settings["notifications"]
        assert "notify_error" in settings["notifications"]

    def test_default_quality_value(self) -> None:
        """Test default quality value is reasonable."""
        from video_converter.gui.services.settings_manager import get_default_settings

        settings = get_default_settings()
        quality = settings["encoding"]["quality"]
        assert 0 < quality < 51  # Valid CRF range


class TestSettingsManagerCreation:
    """Tests for SettingsManager initialization."""

    def test_manager_creates_successfully(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that SettingsManager creates without errors."""
        from video_converter.gui.services.settings_manager import SettingsManager

        with patch.object(SettingsManager, "_get_settings_path", return_value=tmp_path / "settings.json"):
            manager = SettingsManager()
            assert manager is not None

    def test_manager_has_default_settings(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that manager starts with default settings."""
        from video_converter.gui.services.settings_manager import (
            SettingsManager,
            get_default_settings,
        )

        with patch.object(SettingsManager, "_get_settings_path", return_value=tmp_path / "settings.json"):
            manager = SettingsManager()
            settings = manager.get()
            defaults = get_default_settings()

            assert settings["encoding"] == defaults["encoding"]

    def test_manager_is_not_dirty_initially(
        self, qtbot: QtBot, tmp_path: Path
    ) -> None:
        """Test that manager is not dirty when created."""
        from video_converter.gui.services.settings_manager import SettingsManager

        with patch.object(SettingsManager, "_get_settings_path", return_value=tmp_path / "settings.json"):
            manager = SettingsManager()
            assert manager.is_dirty() is False


class TestSettingsManagerSettingsPath:
    """Tests for settings path handling."""

    def test_settings_path_property(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that settings_path property returns correct path."""
        from video_converter.gui.services.settings_manager import SettingsManager

        expected_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=expected_path):
            manager = SettingsManager()
            assert manager.settings_path == expected_path


class TestSettingsManagerLoad:
    """Tests for loading settings."""

    def test_load_returns_defaults_when_no_file(
        self, qtbot: QtBot, tmp_path: Path
    ) -> None:
        """Test that load returns defaults when file doesn't exist."""
        from video_converter.gui.services.settings_manager import (
            SettingsManager,
            get_default_settings,
        )

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            settings = manager.load()
            defaults = get_default_settings()

            assert settings == defaults

    def test_load_emits_signal(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that load emits settings_loaded signal."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()

            with qtbot.waitSignal(manager.settings_loaded, timeout=1000):
                manager.load()

    def test_load_reads_from_file(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that load reads settings from file."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        custom_settings = {
            "encoding": {"encoder": "Software", "quality": 18, "preset": "slow", "audio": "AAC", "concurrent_jobs": 1},
            "paths": {"output_dir": "/custom", "temp_dir": None, "naming_pattern": "{name}.hevc"},
            "automation": {"delete_original": True, "skip_existing": False, "auto_start": False, "launch_login": True, "background_mode": False},
            "notifications": {"notify_complete": False, "notify_error": False, "play_sound": True},
        }

        settings_path.write_text(json.dumps(custom_settings))

        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            settings = manager.load()

            assert settings["encoding"]["quality"] == 18

    def test_load_handles_invalid_json(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that load handles invalid JSON gracefully."""
        from video_converter.gui.services.settings_manager import (
            SettingsManager,
            get_default_settings,
        )

        settings_path = tmp_path / "settings.json"
        settings_path.write_text("invalid json {{{")

        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            settings = manager.load()
            defaults = get_default_settings()

            assert settings == defaults

    def test_load_merges_with_defaults(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that load merges partial settings with defaults."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        partial_settings = {
            "encoding": {"quality": 20},
        }
        settings_path.write_text(json.dumps(partial_settings))

        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            settings = manager.load()

            # Should have custom quality
            assert settings["encoding"]["quality"] == 20
            # Should still have default preset
            assert "preset" in settings["encoding"]


class TestSettingsManagerSave:
    """Tests for saving settings."""

    def test_save_writes_to_file(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that save writes settings to file."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            result = manager.save()

            assert result is True
            assert settings_path.exists()

    def test_save_emits_signal(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that save emits settings_saved signal."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()

            with qtbot.waitSignal(manager.settings_saved, timeout=1000):
                manager.save()

    def test_save_clears_dirty_flag(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that save clears the dirty flag."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            manager.set_value("encoding", "quality", 15)
            assert manager.is_dirty() is True

            manager.save()
            assert manager.is_dirty() is False

    def test_save_returns_false_on_error(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that save returns False on write error."""
        from video_converter.gui.services.settings_manager import SettingsManager

        # Use a path that doesn't exist and can't be created
        settings_path = tmp_path / "nonexistent" / "subdir" / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            result = manager.save()

            assert result is False


class TestSettingsManagerGet:
    """Tests for getting settings."""

    def test_get_returns_all_settings(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that get() returns all settings."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            settings = manager.get()

            assert "encoding" in settings
            assert "paths" in settings
            assert "automation" in settings
            assert "notifications" in settings

    def test_get_returns_category(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that get(category) returns specific category."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            encoding = manager.get("encoding")

            assert "encoder" in encoding
            assert "quality" in encoding

    def test_get_returns_copy(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that get returns a copy at top level."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            settings1 = manager.get()
            # Modifying the top-level dict shouldn't affect the internal state
            settings1["new_key"] = "new_value"

            settings2 = manager.get()
            assert "new_key" not in settings2

    def test_get_empty_for_invalid_category(
        self, qtbot: QtBot, tmp_path: Path
    ) -> None:
        """Test that get returns empty dict for invalid category."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            result = manager.get("invalid_category")

            assert result == {}


class TestSettingsManagerGetValue:
    """Tests for getting individual values."""

    def test_get_value_returns_value(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that get_value returns the correct value."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            quality = manager.get_value("encoding", "quality")

            assert quality == 28  # Default value

    def test_get_value_returns_default(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that get_value returns default for missing key."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            result = manager.get_value("encoding", "nonexistent", "default_value")

            assert result == "default_value"

    def test_get_value_returns_none_default(
        self, qtbot: QtBot, tmp_path: Path
    ) -> None:
        """Test that get_value returns None by default for missing key."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            result = manager.get_value("encoding", "nonexistent")

            assert result is None


class TestSettingsManagerSet:
    """Tests for setting values."""

    def test_set_updates_settings(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that set() updates settings."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            new_settings = {
                "encoding": {"quality": 15, "preset": "fast"},
            }
            manager.set(new_settings)

            assert manager.get_value("encoding", "quality") == 15

    def test_set_marks_dirty(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that set() marks manager as dirty."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            manager.set({"encoding": {"quality": 10}})

            assert manager.is_dirty() is True

    def test_set_emits_signal(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that set() emits settings_changed signal."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()

            with qtbot.waitSignal(manager.settings_changed, timeout=1000):
                manager.set({"encoding": {"quality": 10}})


class TestSettingsManagerSetValue:
    """Tests for setting individual values."""

    def test_set_value_updates_value(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that set_value updates specific value."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            manager.set_value("encoding", "quality", 20)

            assert manager.get_value("encoding", "quality") == 20

    def test_set_value_creates_category(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that set_value creates category if needed."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            manager.set_value("new_category", "new_key", "new_value")

            assert manager.get_value("new_category", "new_key") == "new_value"

    def test_set_value_marks_dirty(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that set_value marks manager as dirty."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            manager.set_value("encoding", "quality", 25)

            assert manager.is_dirty() is True

    def test_set_value_emits_signal(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that set_value emits settings_changed signal."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()

            with qtbot.waitSignal(manager.settings_changed, timeout=1000):
                manager.set_value("encoding", "quality", 25)


class TestSettingsManagerReset:
    """Tests for resetting settings."""

    def test_reset_restores_defaults(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that reset restores default settings."""
        from video_converter.gui.services.settings_manager import (
            SettingsManager,
            get_default_settings,
        )

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            manager.set_value("encoding", "quality", 10)
            manager.reset()

            defaults = get_default_settings()
            assert manager.get_value("encoding", "quality") == defaults["encoding"]["quality"]

    def test_reset_marks_dirty(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that reset marks manager as dirty."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            manager.reset()

            assert manager.is_dirty() is True

    def test_reset_emits_reset_signal(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that reset emits settings_reset signal."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()

            with qtbot.waitSignal(manager.settings_reset, timeout=1000):
                manager.reset()

    def test_reset_emits_changed_signal(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that reset emits settings_changed signal."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()

            with qtbot.waitSignal(manager.settings_changed, timeout=1000):
                manager.reset()


class TestSettingsManagerApplyToConversion:
    """Tests for applying settings to conversion."""

    def test_apply_adds_encoder(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that apply adds encoder if not specified."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            conversion_settings: dict = {}
            result = manager.apply_to_conversion_settings(conversion_settings)

            assert "encoder" in result

    def test_apply_preserves_existing(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that apply preserves existing settings."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            conversion_settings = {"quality": 15}
            result = manager.apply_to_conversion_settings(conversion_settings)

            assert result["quality"] == 15

    def test_apply_adds_automation_settings(
        self, qtbot: QtBot, tmp_path: Path
    ) -> None:
        """Test that apply adds automation settings."""
        from video_converter.gui.services.settings_manager import SettingsManager

        settings_path = tmp_path / "settings.json"
        with patch.object(SettingsManager, "_get_settings_path", return_value=settings_path):
            manager = SettingsManager()
            conversion_settings: dict = {}
            result = manager.apply_to_conversion_settings(conversion_settings)

            assert "delete_original" in result
            assert "skip_existing" in result
