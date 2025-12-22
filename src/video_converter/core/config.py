"""Configuration management system for video converter.

This module provides a centralized configuration system that loads, validates,
and saves user preferences in JSON format. It supports both default and
user-customized settings with environment variable overrides.

SDS Reference: SDS-C01-003
SRS Reference: SRS-102 (Configuration Management)

Example:
    >>> from video_converter.core.config import Config
    >>> config = Config.load()
    >>> print(config.encoding.mode)  # "hardware"
    >>> config.encoding.quality = 50
    >>> config.save()

    >>> # Environment variable override
    >>> # VIDEO_CONVERTER_ENCODING__MODE=software
    >>> config = Config.load()
    >>> print(config.encoding.mode)  # "software"
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from pydantic_settings.sources import JsonConfigSettingsSource

# Default paths
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "video_converter"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"
BUNDLED_DEFAULT_CONFIG = Path(__file__).parent.parent.parent.parent / "config" / "default.json"

# Singleton state (module-level to avoid Pydantic serialization issues)
_config_lock: threading.Lock = threading.Lock()
_config_instance: Config | None = None
_config_path_cache: Path | None = None


class _JsonFileSettingsSource(JsonConfigSettingsSource):
    """Custom JSON settings source that loads from a specified file."""

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        json_file: Path | None = None,
    ) -> None:
        self._json_file = json_file
        super().__init__(settings_cls, json_file=json_file)


class EncodingConfig(BaseModel):
    """Encoding settings for video conversion.

    Attributes:
        mode: Encoding mode - "hardware" (VideoToolbox) or "software" (libx265).
        quality: Quality setting (1-100, higher is better).
        crf: Constant Rate Factor for encoding (18-28, lower is better quality).
        preset: Encoding preset affecting speed vs compression trade-off.
    """

    mode: Literal["hardware", "software"] = "hardware"
    quality: int = Field(default=45, ge=1, le=100)
    crf: int = Field(default=22, ge=18, le=28)
    preset: Literal["fast", "medium", "slow"] = "medium"


class PathsConfig(BaseModel):
    """Path settings for file management.

    Attributes:
        output: Directory for converted output files.
        processed: Directory for successfully processed original files.
        failed: Directory for files that failed conversion.
    """

    output: Path = Path("~/Videos/Converted")
    processed: Path = Path("~/Videos/Processed")
    failed: Path = Path("~/Videos/Failed")

    @field_validator("output", "processed", "failed", mode="before")
    @classmethod
    def expand_path(cls, v: str | Path) -> Path:
        """Expand user home directory in paths.

        Args:
            v: Path value (string or Path).

        Returns:
            Path with ~ expanded to user home directory.
        """
        if isinstance(v, str):
            v = Path(v)
        return v.expanduser()


class AutomationConfig(BaseModel):
    """Automation settings for scheduled conversions.

    Attributes:
        enabled: Whether automation is enabled.
        schedule: Schedule type ("daily", "hourly", etc.).
        time: Time of day to run (HH:MM format).
    """

    enabled: bool = False
    schedule: Literal["hourly", "daily", "weekly"] = "daily"
    time: str = Field(default="03:00", pattern=r"^\d{2}:\d{2}$")


class PhotosConfig(BaseModel):
    """Photos library settings.

    Attributes:
        include_albums: List of album names to include (empty = all).
        exclude_albums: List of album names to exclude.
        download_from_icloud: Whether to download videos from iCloud.
        icloud_timeout: Maximum time to wait for iCloud downloads in seconds.
        skip_cloud_only: Skip videos that are only in iCloud (don't download).
    """

    include_albums: list[str] = Field(default_factory=list)
    exclude_albums: list[str] = Field(default_factory=lambda: ["Screenshots"])
    download_from_icloud: bool = True
    icloud_timeout: int = Field(default=3600, ge=60, le=86400)
    skip_cloud_only: bool = False


class ProcessingConfig(BaseModel):
    """Processing settings for conversion workflow.

    Attributes:
        max_concurrent: Maximum concurrent conversions.
        validate_quality: Whether to validate output quality.
        preserve_original: Whether to preserve original files.
    """

    max_concurrent: int = Field(default=2, ge=1, le=8)
    validate_quality: bool = True
    preserve_original: bool = True


class NotificationConfig(BaseModel):
    """Notification settings.

    Attributes:
        on_complete: Send notification when conversion completes.
        on_error: Send notification on errors.
        daily_summary: Send daily summary notification.
    """

    on_complete: bool = True
    on_error: bool = True
    daily_summary: bool = False


class Config(BaseSettings):
    """Main configuration class for video converter.

    This class manages all configuration settings for the video converter
    application. It supports loading from JSON files, environment variable
    overrides, and runtime modifications.

    Attributes:
        version: Configuration schema version.
        encoding: Encoding settings.
        paths: Path settings.
        automation: Automation settings.
        photos: Photos library settings.
        processing: Processing settings.
        notification: Notification settings.

    Example:
        >>> config = Config.load()
        >>> print(config.encoding.mode)
        'hardware'

        >>> # Modify and save
        >>> config.encoding.quality = 60
        >>> config.save()

        >>> # Environment override (VIDEO_CONVERTER_ENCODING__MODE=software)
        >>> config = Config.load()
        >>> print(config.encoding.mode)
        'software'
    """

    model_config = SettingsConfigDict(
        env_prefix="VIDEO_CONVERTER_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    version: str = "1.0.0"
    encoding: EncodingConfig = Field(default_factory=EncodingConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    automation: AutomationConfig = Field(default_factory=AutomationConfig)
    photos: PhotosConfig = Field(default_factory=PhotosConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    notification: NotificationConfig = Field(default_factory=NotificationConfig)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customize settings sources priority.

        Priority (highest to lowest):
        1. init_settings (direct arguments)
        2. env_settings (environment variables)
        3. JSON file settings
        4. Default values

        This ensures environment variables override JSON file settings.
        """
        # Explicitly mark unused parameters (required by pydantic-settings interface)
        _ = dotenv_settings
        _ = file_secret_settings

        # Find config file
        json_file = cls._find_config_file()

        # Create JSON source if file exists
        json_source = _JsonFileSettingsSource(settings_cls, json_file=json_file)

        return (
            init_settings,
            env_settings,
            json_source,
        )

    @classmethod
    def load(
        cls,
        config_path: Path | None = None,
        *,
        force_reload: bool = False,
    ) -> Config:
        """Load configuration from file.

        Loads configuration from the specified path, or falls back to default
        locations. Environment variables can override loaded values.

        Args:
            config_path: Deprecated. Custom paths are not currently supported.
                        Use environment variables or modify the default files.
            force_reload: Force reload even if already loaded.

        Returns:
            Config: Loaded configuration instance.

        Raises:
            ValueError: If configuration file contains invalid values.

        Example:
            >>> config = Config.load()  # Uses default paths
            >>> # Environment override: VIDEO_CONVERTER_ENCODING__MODE=software
        """
        global _config_instance, _config_path_cache

        # Mark deprecated parameter as unused
        _ = config_path

        with _config_lock:
            if _config_instance is not None and not force_reload:
                return _config_instance

            # Create instance - settings_customise_sources handles JSON loading
            instance = cls()
            _config_path_cache = cls._find_config_file() or DEFAULT_CONFIG_FILE

            _config_instance = instance
            return instance

    @classmethod
    def _find_config_file(cls) -> Path | None:
        """Find the configuration file to load.

        Returns:
            Path to config file, or None if no file exists.
        """
        # Check user config first
        if DEFAULT_CONFIG_FILE.exists():
            return DEFAULT_CONFIG_FILE

        # Fall back to bundled default
        if BUNDLED_DEFAULT_CONFIG.exists():
            return BUNDLED_DEFAULT_CONFIG

        return None

    @classmethod
    def _load_json(cls, path: Path) -> dict[str, object]:
        """Load JSON configuration from file.

        Args:
            path: Path to JSON file.

        Returns:
            Dictionary with configuration data.

        Raises:
            ValueError: If JSON is invalid.
        """
        try:
            with path.open("r", encoding="utf-8") as f:
                data: dict[str, object] = json.load(f)
                return data
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON in configuration file {path}: {e}"
            raise ValueError(msg) from e

    def save(self, config_path: Path | None = None) -> None:
        """Save configuration to file.

        Args:
            config_path: Optional path to save to. Defaults to loaded path.

        Raises:
            IOError: If file cannot be written.

        Example:
            >>> config = Config.load()
            >>> config.encoding.quality = 60
            >>> config.save()
        """
        save_path = config_path or _config_path_cache or DEFAULT_CONFIG_FILE

        # Ensure directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict and save
        config_dict = self.model_dump(mode="json")

        # Convert Path objects to strings for JSON serialization
        if "paths" in config_dict:
            for key, value in config_dict["paths"].items():
                if isinstance(value, Path):
                    config_dict["paths"][key] = str(value)

        with save_path.open("w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
            f.write("\n")

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance.

        This is primarily useful for testing to ensure a clean state.
        """
        global _config_instance, _config_path_cache

        with _config_lock:
            _config_instance = None
            _config_path_cache = None

    @classmethod
    def get_default_config_path(cls) -> Path:
        """Get the default user configuration file path.

        Returns:
            Path to user configuration file.
        """
        return DEFAULT_CONFIG_FILE

    @classmethod
    def get_config_dir(cls) -> Path:
        """Get the configuration directory path.

        Returns:
            Path to configuration directory.
        """
        return DEFAULT_CONFIG_DIR

    def to_dict(self) -> dict[str, object]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration.
        """
        return self.model_dump()


__all__ = [
    "Config",
    "EncodingConfig",
    "PathsConfig",
    "AutomationConfig",
    "PhotosConfig",
    "ProcessingConfig",
    "NotificationConfig",
    "DEFAULT_CONFIG_DIR",
    "DEFAULT_CONFIG_FILE",
]
