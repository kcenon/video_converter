"""Settings manager for the Video Converter GUI.

This module provides persistent settings management with JSON file storage,
automatic loading on startup, and change notifications.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


def get_default_settings() -> dict[str, Any]:
    """Get default settings for the application.

    Returns:
        Dictionary containing default settings for all categories.
    """
    return {
        "encoding": {
            "encoder": "Auto (Prefer Hardware)",
            "quality": 28,
            "preset": "medium",
            "audio": "Copy (No re-encode)",
            "concurrent_jobs": 2,
        },
        "paths": {
            "output_dir": None,
            "temp_dir": None,
            "naming_pattern": "{name}_hevc.{ext}",
        },
        "automation": {
            "delete_original": False,
            "skip_existing": True,
            "auto_start": True,
            "launch_login": False,
            "background_mode": True,
        },
        "notifications": {
            "notify_complete": True,
            "notify_error": True,
            "play_sound": False,
        },
    }


class SettingsManager(QObject):
    """Manager for application settings persistence.

    Handles loading and saving settings to a JSON file in the user's
    application support directory. Provides signals for settings changes.

    Signals:
        settings_changed: Emitted when settings are modified.
        settings_loaded: Emitted when settings are loaded from disk.
        settings_saved: Emitted when settings are saved to disk.
        settings_reset: Emitted when settings are reset to defaults.

    Attributes:
        settings_path: Path to the settings JSON file.
    """

    settings_changed = Signal(dict)
    settings_loaded = Signal(dict)
    settings_saved = Signal()
    settings_reset = Signal()

    # Application identifier for settings directory
    APP_NAME = "VideoConverter"
    SETTINGS_FILENAME = "settings.json"

    def __init__(self, parent: QObject | None = None) -> None:
        """Initialize the settings manager.

        Args:
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._settings: dict[str, Any] = get_default_settings()
        self._settings_path = self._get_settings_path()
        self._dirty = False

    def _get_settings_path(self) -> Path:
        """Get the path to the settings file.

        Creates the settings directory if it doesn't exist.

        Returns:
            Path to the settings JSON file.
        """
        # Use macOS Application Support directory
        app_support = Path.home() / "Library" / "Application Support"
        settings_dir = app_support / self.APP_NAME

        # Create directory if needed
        settings_dir.mkdir(parents=True, exist_ok=True)

        return settings_dir / self.SETTINGS_FILENAME

    @property
    def settings_path(self) -> Path:
        """Get the current settings file path.

        Returns:
            Path to the settings JSON file.
        """
        return self._settings_path

    def load(self) -> dict[str, Any]:
        """Load settings from the JSON file.

        If the file doesn't exist or is invalid, returns default settings.

        Returns:
            Dictionary containing the loaded settings.
        """
        if not self._settings_path.exists():
            logger.info("No settings file found, using defaults")
            self._settings = get_default_settings()
            self.settings_loaded.emit(self._settings)
            return self._settings

        try:
            with self._settings_path.open("r", encoding="utf-8") as f:
                loaded = json.load(f)

            # Merge with defaults to handle new settings
            self._settings = self._merge_with_defaults(loaded)
            self._dirty = False

            logger.info(f"Settings loaded from {self._settings_path}")
            self.settings_loaded.emit(self._settings)

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid settings file, using defaults: {e}")
            self._settings = get_default_settings()
            self.settings_loaded.emit(self._settings)

        except OSError as e:
            logger.warning(f"Could not read settings file: {e}")
            self._settings = get_default_settings()
            self.settings_loaded.emit(self._settings)

        return self._settings

    def save(self) -> bool:
        """Save current settings to the JSON file.

        Returns:
            True if saved successfully, False otherwise.
        """
        try:
            with self._settings_path.open("w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)

            self._dirty = False
            logger.info(f"Settings saved to {self._settings_path}")
            self.settings_saved.emit()
            return True

        except OSError as e:
            logger.error(f"Could not save settings: {e}")
            return False

    def get(self, category: str | None = None) -> dict[str, Any]:
        """Get settings, optionally filtered by category.

        Args:
            category: Optional category name (encoding, paths, automation,
                     notifications). If None, returns all settings.

        Returns:
            Dictionary containing the requested settings.
        """
        if category is None:
            return self._settings.copy()

        return self._settings.get(category, {}).copy()

    def get_value(self, category: str, key: str, default: Any = None) -> Any:
        """Get a specific setting value.

        Args:
            category: Settings category name.
            key: Setting key within the category.
            default: Default value if not found.

        Returns:
            The setting value or default.
        """
        return self._settings.get(category, {}).get(key, default)

    def set(self, settings: dict[str, Any]) -> None:
        """Set all settings from a dictionary.

        Args:
            settings: Dictionary containing settings to apply.
        """
        self._settings = self._merge_with_defaults(settings)
        self._dirty = True
        self.settings_changed.emit(self._settings)

    def set_value(self, category: str, key: str, value: Any) -> None:
        """Set a specific setting value.

        Args:
            category: Settings category name.
            key: Setting key within the category.
            value: Value to set.
        """
        if category not in self._settings:
            self._settings[category] = {}

        self._settings[category][key] = value
        self._dirty = True
        self.settings_changed.emit(self._settings)

    def reset(self) -> dict[str, Any]:
        """Reset all settings to defaults.

        Returns:
            Dictionary containing the default settings.
        """
        self._settings = get_default_settings()
        self._dirty = True
        self.settings_reset.emit()
        self.settings_changed.emit(self._settings)
        return self._settings

    def is_dirty(self) -> bool:
        """Check if settings have been modified since last save.

        Returns:
            True if settings have unsaved changes.
        """
        return self._dirty

    def _merge_with_defaults(self, loaded: dict[str, Any]) -> dict[str, Any]:
        """Merge loaded settings with defaults for missing keys.

        This ensures new settings added in updates are included.

        Args:
            loaded: Dictionary of loaded settings.

        Returns:
            Merged settings dictionary.
        """
        defaults = get_default_settings()
        result: dict[str, Any] = {}

        for category, default_values in defaults.items():
            if category in loaded and isinstance(loaded[category], dict):
                # Merge category with defaults
                result[category] = {**default_values, **loaded[category]}
            else:
                # Use defaults for missing categories
                result[category] = default_values

        return result

    def apply_to_conversion_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        """Apply stored settings to conversion settings.

        Merges the stored settings with any provided conversion settings,
        useful when starting a conversion.

        Args:
            settings: Conversion settings dictionary to enhance.

        Returns:
            Enhanced settings dictionary.
        """
        encoding = self._settings.get("encoding", {})
        paths = self._settings.get("paths", {})
        automation = self._settings.get("automation", {})

        # Apply encoding settings if not already specified
        if "encoder" not in settings:
            settings["encoder"] = encoding.get("encoder", "Auto (Prefer Hardware)")
        if "quality" not in settings:
            settings["quality"] = encoding.get("quality", 28)
        if "preset" not in settings:
            settings["preset"] = encoding.get("preset", "medium")
        if "audio" not in settings:
            settings["audio"] = encoding.get("audio", "Copy (No re-encode)")

        # Apply path settings
        if "output_dir" not in settings and paths.get("output_dir"):
            settings["output_dir"] = paths["output_dir"]

        # Apply automation settings
        settings["delete_original"] = automation.get("delete_original", False)
        settings["skip_existing"] = automation.get("skip_existing", True)

        return settings
