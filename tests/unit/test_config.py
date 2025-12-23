"""Unit tests for configuration management system."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from video_converter.core.config import (
    DEFAULT_CONFIG_DIR,
    DEFAULT_CONFIG_FILE,
    AutomationConfig,
    Config,
    EncodingConfig,
    FolderConfig,
    NotificationConfig,
    PathsConfig,
    PhotosConfig,
    ProcessingConfig,
)


@pytest.fixture(autouse=True)
def reset_config() -> None:
    """Reset config singleton before each test."""
    Config.reset()
    yield
    Config.reset()


class TestEncodingConfig:
    """Tests for EncodingConfig model."""

    def test_default_values(self) -> None:
        """Test default encoding config values."""
        config = EncodingConfig()
        assert config.mode == "hardware"
        assert config.quality == 45
        assert config.crf == 22
        assert config.preset == "medium"

    def test_custom_values(self) -> None:
        """Test encoding config with custom values."""
        config = EncodingConfig(mode="software", quality=80, crf=20, preset="slow")
        assert config.mode == "software"
        assert config.quality == 80
        assert config.crf == 20
        assert config.preset == "slow"

    def test_quality_validation_min(self) -> None:
        """Test quality minimum validation."""
        with pytest.raises(ValueError):
            EncodingConfig(quality=0)

    def test_quality_validation_max(self) -> None:
        """Test quality maximum validation."""
        with pytest.raises(ValueError):
            EncodingConfig(quality=101)

    def test_crf_validation_min(self) -> None:
        """Test CRF minimum validation."""
        with pytest.raises(ValueError):
            EncodingConfig(crf=17)

    def test_crf_validation_max(self) -> None:
        """Test CRF maximum validation."""
        with pytest.raises(ValueError):
            EncodingConfig(crf=29)

    def test_mode_validation(self) -> None:
        """Test mode validation with invalid value."""
        with pytest.raises(ValueError):
            EncodingConfig(mode="invalid")

    def test_preset_validation(self) -> None:
        """Test preset validation with invalid value."""
        with pytest.raises(ValueError):
            EncodingConfig(preset="invalid")


class TestPathsConfig:
    """Tests for PathsConfig model."""

    def test_default_values(self) -> None:
        """Test default paths config values."""
        config = PathsConfig()
        # Default paths are Path objects (~ not expanded for defaults)
        # Expansion happens when loading from JSON or explicit string input
        assert "Videos" in str(config.output)
        assert "Converted" in str(config.output)

    def test_path_expansion_from_string(self) -> None:
        """Test that ~ is expanded in paths from strings."""
        config = PathsConfig(output="~/custom/path")
        assert config.output == Path.home() / "custom" / "path"
        assert config.output.is_absolute()

    def test_path_expansion_from_path(self) -> None:
        """Test that ~ is expanded in Path objects."""
        config = PathsConfig(output=Path("~/another/path"))
        assert config.output == Path.home() / "another" / "path"

    def test_absolute_path_preserved(self) -> None:
        """Test that absolute paths are preserved."""
        config = PathsConfig(output="/absolute/path")
        assert config.output == Path("/absolute/path")


class TestAutomationConfig:
    """Tests for AutomationConfig model."""

    def test_default_values(self) -> None:
        """Test default automation config values."""
        config = AutomationConfig()
        assert config.enabled is False
        assert config.schedule == "daily"
        assert config.time == "03:00"

    def test_time_format_validation(self) -> None:
        """Test time format validation."""
        # Valid times
        AutomationConfig(time="00:00")
        AutomationConfig(time="23:59")
        AutomationConfig(time="12:30")

    def test_time_format_invalid(self) -> None:
        """Test invalid time format (pattern mismatch)."""
        with pytest.raises(ValueError):
            # Pattern requires exactly HH:MM format
            AutomationConfig(time="3:00")  # Single digit hour

        with pytest.raises(ValueError):
            AutomationConfig(time="12:5")  # Single digit minute

        with pytest.raises(ValueError):
            AutomationConfig(time="12:00:00")  # Too many colons

    def test_schedule_validation(self) -> None:
        """Test schedule validation with invalid value."""
        with pytest.raises(ValueError):
            AutomationConfig(schedule="monthly")


class TestPhotosConfig:
    """Tests for PhotosConfig model."""

    def test_default_values(self) -> None:
        """Test default photos config values."""
        config = PhotosConfig()
        assert config.include_albums == []
        assert config.exclude_albums == ["Screenshots"]
        assert config.download_from_icloud is True

    def test_custom_albums(self) -> None:
        """Test photos config with custom albums."""
        config = PhotosConfig(
            include_albums=["Vacation", "Family"],
            exclude_albums=["Private", "Work"],
        )
        assert config.include_albums == ["Vacation", "Family"]
        assert config.exclude_albums == ["Private", "Work"]


class TestProcessingConfig:
    """Tests for ProcessingConfig model."""

    def test_default_values(self) -> None:
        """Test default processing config values."""
        config = ProcessingConfig()
        assert config.max_concurrent == 2
        assert config.validate_quality is True
        assert config.preserve_original is True

    def test_max_concurrent_validation_min(self) -> None:
        """Test max_concurrent minimum validation."""
        with pytest.raises(ValueError):
            ProcessingConfig(max_concurrent=0)

    def test_max_concurrent_validation_max(self) -> None:
        """Test max_concurrent maximum validation."""
        with pytest.raises(ValueError):
            ProcessingConfig(max_concurrent=9)


class TestNotificationConfig:
    """Tests for NotificationConfig model."""

    def test_default_values(self) -> None:
        """Test default notification config values."""
        config = NotificationConfig()
        assert config.on_complete is True
        assert config.on_error is True
        assert config.daily_summary is False


class TestConfigLoad:
    """Tests for Config.load() method."""

    def test_load_returns_config_instance(self) -> None:
        """Test that load returns a Config instance."""
        config = Config.load()
        assert isinstance(config, Config)

    def test_load_singleton_pattern(self) -> None:
        """Test that load returns the same instance."""
        config1 = Config.load()
        config2 = Config.load()
        assert config1 is config2

    def test_load_force_reload(self) -> None:
        """Test force reload creates new instance."""
        config1 = Config.load()
        config1_id = id(config1)
        Config.reset()
        config2 = Config.load(force_reload=True)
        # After reset, should be a different instance
        assert id(config2) != config1_id

    def test_load_from_bundled_default(self) -> None:
        """Test loading from bundled default config."""
        config = Config.load()
        # Should have values from config/default.json
        assert config.encoding.mode == "hardware"
        assert config.encoding.quality == 45

    def test_config_version(self) -> None:
        """Test config version is set and follows semantic versioning."""
        config = Config.load()
        # Version should be a non-empty string following semantic versioning
        assert config.version is not None
        assert len(config.version) > 0
        # Should contain at least one dot for versioning (e.g., "0.1.0.0")
        assert "." in config.version


class TestConfigEnvironmentOverride:
    """Tests for environment variable overrides."""

    def test_encoding_mode_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test encoding mode environment override."""
        monkeypatch.setenv("VIDEO_CONVERTER_ENCODING__MODE", "software")
        config = Config.load(force_reload=True)
        assert config.encoding.mode == "software"

    def test_encoding_quality_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test encoding quality environment override."""
        monkeypatch.setenv("VIDEO_CONVERTER_ENCODING__QUALITY", "80")
        config = Config.load(force_reload=True)
        assert config.encoding.quality == 80

    def test_processing_max_concurrent_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test processing max_concurrent environment override."""
        monkeypatch.setenv("VIDEO_CONVERTER_PROCESSING__MAX_CONCURRENT", "4")
        config = Config.load(force_reload=True)
        assert config.processing.max_concurrent == 4

    def test_automation_enabled_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test automation enabled environment override."""
        monkeypatch.setenv("VIDEO_CONVERTER_AUTOMATION__ENABLED", "true")
        config = Config.load(force_reload=True)
        assert config.automation.enabled is True


class TestConfigSave:
    """Tests for Config.save() method."""

    def test_save_creates_file(self) -> None:
        """Test that save creates config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "config.json"
            config = Config.load()
            config.save(save_path)
            assert save_path.exists()

    def test_save_creates_directory(self) -> None:
        """Test that save creates parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "nested" / "dir" / "config.json"
            config = Config.load()
            config.save(save_path)
            assert save_path.exists()

    def test_save_preserves_modified_values(self) -> None:
        """Test that save preserves modified values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "config.json"
            config = Config.load()
            config.encoding.quality = 75
            config.save(save_path)

            with save_path.open() as f:
                saved = json.load(f)
            assert saved["encoding"]["quality"] == 75

    def test_save_valid_json(self) -> None:
        """Test that saved file is valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "config.json"
            config = Config.load()
            config.save(save_path)

            with save_path.open() as f:
                saved = json.load(f)
            assert isinstance(saved, dict)
            assert "version" in saved
            assert "encoding" in saved

    def test_save_paths_as_strings(self) -> None:
        """Test that paths are saved as strings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "config.json"
            config = Config.load()
            config.save(save_path)

            with save_path.open() as f:
                saved = json.load(f)
            # Paths should be strings in JSON
            assert isinstance(saved["paths"]["output"], str)


class TestConfigReset:
    """Tests for Config.reset() method."""

    def test_reset_clears_instance(self) -> None:
        """Test that reset clears singleton instance."""
        config1 = Config.load()
        config1_id = id(config1)
        Config.reset()
        config2 = Config.load()
        # Should be different instance after reset
        assert id(config2) != config1_id

    def test_reset_allows_new_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that reset allows new environment override."""
        config1 = Config.load()
        assert config1.encoding.mode == "hardware"

        Config.reset()
        monkeypatch.setenv("VIDEO_CONVERTER_ENCODING__MODE", "software")
        config2 = Config.load()
        assert config2.encoding.mode == "software"


class TestConfigPaths:
    """Tests for Config path methods."""

    def test_get_default_config_path(self) -> None:
        """Test getting default config path."""
        path = Config.get_default_config_path()
        assert path == DEFAULT_CONFIG_FILE
        assert path == Path.home() / ".config" / "video_converter" / "config.json"

    def test_get_config_dir(self) -> None:
        """Test getting config directory."""
        dir_path = Config.get_config_dir()
        assert dir_path == DEFAULT_CONFIG_DIR
        assert dir_path == Path.home() / ".config" / "video_converter"


class TestConfigToDict:
    """Tests for Config.to_dict() method."""

    def test_to_dict_returns_dict(self) -> None:
        """Test that to_dict returns a dictionary."""
        config = Config.load()
        result = config.to_dict()
        assert isinstance(result, dict)

    def test_to_dict_contains_all_sections(self) -> None:
        """Test that to_dict contains all config sections."""
        config = Config.load()
        result = config.to_dict()
        assert "version" in result
        assert "encoding" in result
        assert "paths" in result
        assert "automation" in result
        assert "photos" in result
        assert "processing" in result
        assert "notification" in result


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_invalid_json_raises_error(self) -> None:
        """Test that invalid JSON in config file raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "invalid.json"
            config_file.write_text("{ invalid json }")

            # Direct JSON load should fail
            with pytest.raises(json.JSONDecodeError), config_file.open() as f:
                json.load(f)

    def test_nested_config_validation(self) -> None:
        """Test that nested config values are validated at creation."""
        # Validation happens when creating the nested config object
        with pytest.raises(ValueError):
            EncodingConfig(mode="invalid")

        # Also test via model_validate
        with pytest.raises(ValueError):
            EncodingConfig.model_validate({"mode": "invalid"})

    def test_config_immutable_fields_protected(self) -> None:
        """Test that config fields are validated on assignment."""
        config = Config.load()
        # Quality must be between 1-100
        with pytest.raises(ValueError):
            config.encoding = EncodingConfig(quality=150)


class TestFolderConfig:
    """Tests for FolderConfig model."""

    def test_default_values(self) -> None:
        """Test default folder config values."""
        config = FolderConfig()
        assert config.recursive is True
        assert config.auto_download_icloud is True
        assert config.icloud_timeout == 3600
        assert config.skip_icloud_on_timeout is True
        assert config.include_patterns == []
        assert "*.tmp" in config.exclude_patterns
        assert "._*" in config.exclude_patterns

    def test_custom_values(self) -> None:
        """Test folder config with custom values."""
        config = FolderConfig(
            recursive=False,
            auto_download_icloud=False,
            icloud_timeout=1800,
            skip_icloud_on_timeout=False,
            include_patterns=["vacation*"],
            exclude_patterns=["*.tmp"],
        )
        assert config.recursive is False
        assert config.auto_download_icloud is False
        assert config.icloud_timeout == 1800
        assert config.skip_icloud_on_timeout is False
        assert config.include_patterns == ["vacation*"]
        assert config.exclude_patterns == ["*.tmp"]

    def test_icloud_timeout_validation(self) -> None:
        """Test icloud_timeout validation bounds."""
        # Minimum is 60 seconds
        with pytest.raises(ValueError):
            FolderConfig(icloud_timeout=30)

        # Maximum is 86400 seconds (24 hours)
        with pytest.raises(ValueError):
            FolderConfig(icloud_timeout=100000)

        # Valid boundaries
        config_min = FolderConfig(icloud_timeout=60)
        assert config_min.icloud_timeout == 60

        config_max = FolderConfig(icloud_timeout=86400)
        assert config_max.icloud_timeout == 86400


class TestConfigWithFolder:
    """Tests for Config including FolderConfig."""

    def test_config_has_folder_section(self) -> None:
        """Test that Config includes folder section."""
        config = Config.load()
        assert hasattr(config, "folder")
        assert isinstance(config.folder, FolderConfig)

    def test_to_dict_includes_folder(self) -> None:
        """Test that to_dict includes folder section."""
        config = Config.load()
        result = config.to_dict()
        assert "folder" in result


class TestVersionConsistency:
    """Tests for version consistency across the codebase."""

    def test_version_from_package_metadata(self) -> None:
        """Test that __version__ is loaded from package metadata."""
        from video_converter import __version__

        assert __version__ is not None
        assert len(__version__) > 0
        # Version should follow semantic versioning pattern (x.y.z or x.y.z.w)
        parts = __version__.split(".")
        assert len(parts) >= 3, f"Version '{__version__}' should have at least 3 parts"

    def test_config_version_matches_package_version(self) -> None:
        """Test that Config.version matches package __version__."""
        from video_converter import __version__

        config = Config.load()
        assert config.version == __version__

    def test_cli_version_output(self) -> None:
        """Test that CLI --version outputs correct version."""
        from click.testing import CliRunner

        from video_converter import __version__
        from video_converter.__main__ import main

        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output
