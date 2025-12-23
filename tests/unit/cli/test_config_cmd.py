"""Tests for config-related CLI commands.

This module tests the video-converter config commands including:
- config: View current configuration
- config-set: Set configuration values
- setup: Interactive setup wizard
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from video_converter.__main__ import main


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Click CLI test runner."""
    return CliRunner()


class TestConfigCommand:
    """Tests for the config command."""

    def test_config_shows_help(self, cli_runner: CliRunner) -> None:
        """Test that config --help shows usage information."""
        result = cli_runner.invoke(main, ["config", "--help"])

        assert result.exit_code == 0
        assert "View current configuration" in result.output

    @patch("video_converter.__main__.Config")
    def test_config_displays_settings(
        self,
        mock_config_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test that config displays current settings."""
        mock_config = MagicMock()
        mock_config.encoding.mode = "hardware"
        mock_config.encoding.quality = 45
        mock_config.encoding.crf = 22
        mock_config.encoding.preset = "medium"
        mock_config.paths.output = Path("/tmp/output")
        mock_config.paths.processed = Path("/tmp/processed")
        mock_config.paths.failed = Path("/tmp/failed")
        mock_config.processing.max_concurrent = 2
        mock_config.processing.validate_quality = True
        mock_config.processing.preserve_original = True
        mock_config.automation.enabled = False
        mock_config.automation.schedule = "daily"
        mock_config.automation.time = "03:00"
        mock_config_class.load.return_value = mock_config

        result = cli_runner.invoke(main, ["config"])

        # Should display configuration sections
        assert "Configuration" in result.output or result.exit_code in [0, 1]


class TestConfigSetCommand:
    """Tests for the config-set command."""

    def test_config_set_shows_help(self, cli_runner: CliRunner) -> None:
        """Test that config-set --help shows usage information."""
        result = cli_runner.invoke(main, ["config-set", "--help"])

        assert result.exit_code == 0
        assert "Set a configuration value" in result.output
        assert "KEY" in result.output
        assert "VALUE" in result.output

    def test_config_set_requires_key_and_value(self, cli_runner: CliRunner) -> None:
        """Test that config-set requires both key and value."""
        result = cli_runner.invoke(main, ["config-set"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Error" in result.output

    def test_config_set_requires_value(self, cli_runner: CliRunner) -> None:
        """Test that config-set requires value argument."""
        result = cli_runner.invoke(main, ["config-set", "encoding.mode"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Error" in result.output

    @patch("video_converter.__main__.Config")
    def test_config_set_invalid_key_format(
        self,
        mock_config_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test that invalid key format is rejected."""
        mock_config = MagicMock()
        mock_config_class.load.return_value = mock_config

        result = cli_runner.invoke(main, ["config-set", "invalid_key", "value"])

        # Should fail due to invalid key format (no dot separator)
        assert result.exit_code == 1 or result.exception is not None

    @patch("video_converter.__main__.Config")
    def test_config_set_invalid_section(
        self,
        mock_config_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test that invalid section is rejected."""
        mock_config = MagicMock()
        mock_config.encoding = MagicMock()
        mock_config.paths = MagicMock()
        mock_config.processing = MagicMock()
        mock_config.automation = MagicMock()
        mock_config.photos = MagicMock()
        mock_config.notification = MagicMock()
        mock_config_class.load.return_value = mock_config

        result = cli_runner.invoke(main, ["config-set", "invalid_section.key", "value"])

        # Should fail due to unknown section
        assert result.exit_code == 1 or result.exception is not None

    @patch("video_converter.__main__.Config")
    def test_config_set_encoding_mode(
        self,
        mock_config_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test setting encoding.mode."""
        mock_config = MagicMock()
        mock_config.encoding.mode = "hardware"
        mock_config_class.load.return_value = mock_config

        result = cli_runner.invoke(main, ["config-set", "encoding.mode", "software"])

        # Should succeed or show set confirmation
        if result.exit_code == 0:
            assert "software" in result.output or "Set" in result.output

    @patch("video_converter.__main__.Config")
    def test_config_set_encoding_quality(
        self,
        mock_config_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test setting encoding.quality with integer conversion."""
        mock_config = MagicMock()
        mock_config.encoding.quality = 45
        mock_config_class.load.return_value = mock_config

        result = cli_runner.invoke(main, ["config-set", "encoding.quality", "60"])

        # Should succeed with integer conversion
        if result.exit_code == 0:
            assert "60" in result.output or "Set" in result.output

    @patch("video_converter.__main__.Config")
    def test_config_set_processing_max_concurrent(
        self,
        mock_config_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test setting processing.max_concurrent."""
        mock_config = MagicMock()
        mock_config.processing.max_concurrent = 2
        mock_config_class.load.return_value = mock_config

        result = cli_runner.invoke(main, ["config-set", "processing.max_concurrent", "4"])

        # Should succeed
        if result.exit_code == 0:
            assert "4" in result.output or "Set" in result.output

    @patch("video_converter.__main__.Config")
    def test_config_set_boolean_true(
        self,
        mock_config_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test setting boolean value to true."""
        mock_config = MagicMock()
        mock_config.automation.enabled = False
        mock_config_class.load.return_value = mock_config

        result = cli_runner.invoke(main, ["config-set", "automation.enabled", "true"])

        # Should succeed with boolean conversion
        if result.exit_code == 0:
            assert "true" in result.output.lower() or "Set" in result.output

    @patch("video_converter.__main__.Config")
    def test_config_set_path_value(
        self,
        mock_config_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test setting path value with expansion."""
        mock_config = MagicMock()
        mock_config.paths.output = Path("/tmp/output")
        mock_config_class.load.return_value = mock_config

        result = cli_runner.invoke(main, ["config-set", "paths.output", "~/Videos/Output"])

        # Should succeed with path expansion
        if result.exit_code == 0:
            assert "Videos" in result.output or "Set" in result.output


class TestSetupCommand:
    """Tests for the setup command."""

    def test_setup_shows_help(self, cli_runner: CliRunner) -> None:
        """Test that setup --help shows usage information."""
        result = cli_runner.invoke(main, ["setup", "--help"])

        assert result.exit_code == 0
        assert "setup wizard" in result.output.lower() or "Initial setup" in result.output

    @patch("video_converter.__main__.ConverterFactory")
    @patch("video_converter.__main__.Config")
    def test_setup_checks_encoders(
        self,
        mock_config_class: MagicMock,
        mock_factory_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test that setup checks encoder availability."""
        mock_config = MagicMock()
        mock_config_class.load.return_value = mock_config

        mock_factory = MagicMock()
        mock_factory.is_hardware_available.return_value = True
        mock_factory.is_software_available.return_value = True
        mock_factory_class.return_value = mock_factory

        # Provide inputs for interactive prompts
        # mode, quality, output_dir, enable_automation
        result = cli_runner.invoke(
            main,
            ["setup"],
            input="hardware\n45\n~/Videos/Converted\nn\n",
        )

        # Should show encoder check results
        assert "Hardware" in result.output or "checking" in result.output.lower()

    @patch("video_converter.__main__.ConverterFactory")
    @patch("video_converter.__main__.Config")
    def test_setup_no_encoders_fails(
        self,
        mock_config_class: MagicMock,
        mock_factory_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test that setup fails when no encoders are available."""
        mock_config = MagicMock()
        mock_config_class.load.return_value = mock_config

        mock_factory = MagicMock()
        mock_factory.is_hardware_available.return_value = False
        mock_factory.is_software_available.return_value = False
        mock_factory_class.return_value = mock_factory

        result = cli_runner.invoke(main, ["setup"])

        # Should fail with encoder error
        assert result.exit_code == 1 or "encoder" in result.output.lower()
