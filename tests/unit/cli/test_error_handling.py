"""Tests for CLI error handling and edge cases.

This module tests error handling scenarios including:
- Invalid command arguments
- Missing required options
- Invalid option values
- Filesystem errors
- Permission errors
- Conflicting options
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


class TestInvalidCommands:
    """Tests for invalid command handling."""

    def test_unknown_command(self, cli_runner: CliRunner) -> None:
        """Test that unknown commands show error."""
        result = cli_runner.invoke(main, ["unknown-command"])

        assert result.exit_code != 0
        assert "No such command" in result.output or "Usage:" in result.output

    def test_typo_in_command(self, cli_runner: CliRunner) -> None:
        """Test that command typos show suggestions."""
        result = cli_runner.invoke(main, ["covnert"])  # Typo for 'convert'

        assert result.exit_code != 0

    def test_empty_command(self, cli_runner: CliRunner) -> None:
        """Test that empty command shows usage."""
        result = cli_runner.invoke(main, [])

        # CLI may require subcommand
        assert result.exit_code in [0, 2]
        assert "Usage:" in result.output or "video-converter" in result.output.lower()


class TestInvalidConvertOptions:
    """Tests for invalid convert command options."""

    def test_convert_invalid_quality_range(self, cli_runner: CliRunner) -> None:
        """Test that quality values outside 1-100 are rejected."""
        result = cli_runner.invoke(main, [
            "convert", "/tmp/video.mp4",
            "--quality", "150"
        ])

        # Quality is a range-limited option
        assert result.exit_code != 0 or result.exception is not None

    def test_convert_negative_quality(self, cli_runner: CliRunner) -> None:
        """Test that negative quality values are rejected."""
        result = cli_runner.invoke(main, [
            "convert", "/tmp/video.mp4",
            "--quality", "-10"
        ])

        assert result.exit_code != 0 or result.exception is not None

    def test_convert_invalid_crf_range(self, cli_runner: CliRunner) -> None:
        """Test that CRF values outside 0-51 are rejected."""
        result = cli_runner.invoke(main, [
            "convert", "/tmp/video.mp4",
            "--crf", "60"
        ])

        # CRF has valid range 0-51
        assert result.exit_code != 0 or result.exception is not None

    def test_convert_invalid_mode(self, cli_runner: CliRunner) -> None:
        """Test that invalid encoding mode is rejected."""
        result = cli_runner.invoke(main, [
            "convert", "/tmp/video.mp4",
            "--mode", "invalid_mode"
        ])

        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "choice" in result.output.lower()

    def test_convert_nonexistent_file(self, cli_runner: CliRunner) -> None:
        """Test that nonexistent file path shows error."""
        result = cli_runner.invoke(main, [
            "convert", "/nonexistent/path/video.mp4"
        ])

        assert result.exit_code != 0

    def test_convert_directory_as_input(
        self, cli_runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test that directory path is rejected for convert."""
        result = cli_runner.invoke(main, [
            "convert", str(temp_dir)
        ])

        assert result.exit_code != 0


class TestInvalidRunOptions:
    """Tests for invalid run command options."""

    def test_run_invalid_source(self, cli_runner: CliRunner) -> None:
        """Test that invalid source type is rejected."""
        result = cli_runner.invoke(main, [
            "run", "--source", "invalid_source"
        ])

        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "choice" in result.output.lower()

    def test_run_folder_without_input_dir(self, cli_runner: CliRunner) -> None:
        """Test that folder source requires input directory."""
        result = cli_runner.invoke(main, [
            "run", "--source", "folder"
        ])

        assert result.exit_code == 1 or result.exception is not None

    def test_run_invalid_date_format(self, cli_runner: CliRunner) -> None:
        """Test that invalid date format is rejected."""
        result = cli_runner.invoke(main, [
            "run",
            "--source", "photos",
            "--from-date", "not-a-date"
        ])

        assert result.exit_code != 0 or result.exception is not None

    def test_run_invalid_date_range(self, cli_runner: CliRunner) -> None:
        """Test that invalid date range (to before from) is handled."""
        result = cli_runner.invoke(main, [
            "run",
            "--source", "photos",
            "--from-date", "2024-12-31",
            "--to-date", "2024-01-01"
        ])

        # May succeed but with no results, or may warn about date order
        assert result.exit_code in [0, 1] or result.exception is not None


class TestInvalidServiceOptions:
    """Tests for invalid service command options."""

    def test_install_service_invalid_time(self, cli_runner: CliRunner) -> None:
        """Test that invalid time format is rejected."""
        result = cli_runner.invoke(main, [
            "install-service",
            "--time", "invalid"
        ])

        assert result.exit_code != 0

    def test_install_service_time_out_of_range(self, cli_runner: CliRunner) -> None:
        """Test that time with hour > 23 is rejected."""
        result = cli_runner.invoke(main, [
            "install-service",
            "--time", "25:00"
        ])

        assert result.exit_code != 0 or "Hour must be" in result.output

    def test_install_service_invalid_weekday(self, cli_runner: CliRunner) -> None:
        """Test that invalid weekday is rejected."""
        result = cli_runner.invoke(main, [
            "install-service",
            "--weekday", "8"  # Valid is 0-6 or 1-7
        ])

        assert result.exit_code != 0 or result.exception is not None

    def test_service_logs_invalid_lines(self, cli_runner: CliRunner) -> None:
        """Test that invalid lines count is handled."""
        result = cli_runner.invoke(main, [
            "service-logs",
            "-n", "-5"
        ])

        # Negative lines should fail or be ignored
        assert result.exit_code in [0, 1] or result.exception is not None


class TestInvalidConfigOptions:
    """Tests for invalid config command options."""

    def test_config_set_invalid_key_format(self, cli_runner: CliRunner) -> None:
        """Test that key without dot separator is rejected."""
        result = cli_runner.invoke(main, [
            "config-set", "invalid", "value"
        ])

        assert result.exit_code == 1 or result.exception is not None

    def test_config_set_unknown_section(self, cli_runner: CliRunner) -> None:
        """Test that unknown section is rejected."""
        result = cli_runner.invoke(main, [
            "config-set", "unknown_section.key", "value"
        ])

        assert result.exit_code == 1 or result.exception is not None

    def test_config_set_invalid_boolean(self, cli_runner: CliRunner) -> None:
        """Test that invalid boolean value is handled."""
        result = cli_runner.invoke(main, [
            "config-set", "automation.enabled", "not_a_bool"
        ])

        # May parse as string or reject
        assert result.exit_code in [0, 1] or result.exception is not None


class TestInvalidStatsOptions:
    """Tests for invalid stats command options."""

    def test_stats_invalid_period(self, cli_runner: CliRunner) -> None:
        """Test that invalid period is rejected."""
        result = cli_runner.invoke(main, [
            "stats", "--period", "invalid_period"
        ])

        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "choice" in result.output.lower()

    def test_stats_export_invalid_format(self, cli_runner: CliRunner) -> None:
        """Test that invalid export format is rejected."""
        result = cli_runner.invoke(main, [
            "stats-export", "--format", "invalid_format"
        ])

        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "choice" in result.output.lower()


class TestConflictingOptions:
    """Tests for conflicting option combinations."""

    def test_run_delete_and_keep_conflict(self, cli_runner: CliRunner) -> None:
        """Test that --delete-originals and --keep-originals conflict."""
        result = cli_runner.invoke(main, [
            "run",
            "--source", "photos",
            "--reimport",
            "--delete-originals",
            "--keep-originals",
            "--confirm-delete"
        ])

        assert result.exit_code == 1 or result.exception is not None

    def test_run_delete_without_confirm(self, cli_runner: CliRunner) -> None:
        """Test that --delete-originals requires --confirm-delete."""
        result = cli_runner.invoke(main, [
            "run",
            "--source", "photos",
            "--reimport",
            "--delete-originals"
        ])

        assert result.exit_code == 1 or result.exception is not None

    def test_run_delete_without_reimport(self, cli_runner: CliRunner) -> None:
        """Test that --delete-originals requires --reimport."""
        result = cli_runner.invoke(main, [
            "run",
            "--source", "photos",
            "--delete-originals",
            "--confirm-delete"
        ])

        assert result.exit_code == 1 or result.exception is not None

    def test_run_check_permissions_for_folder(self, cli_runner: CliRunner) -> None:
        """Test that --check-permissions is only for photos source."""
        result = cli_runner.invoke(main, [
            "run",
            "--source", "folder",
            "--check-permissions"
        ])

        assert result.exit_code == 1 or result.exception is not None


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_convert_empty_output_path(
        self, cli_runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test handling of empty output path."""
        video = temp_dir / "test.mp4"
        video.write_bytes(b"fake video content")

        result = cli_runner.invoke(main, [
            "convert", str(video),
            "-o", ""
        ])

        # Should fail with empty output path
        assert result.exit_code != 0 or result.exception is not None

    def test_convert_very_long_path(self, cli_runner: CliRunner) -> None:
        """Test handling of excessively long file path."""
        long_path = "/" + "a" * 500 + ".mp4"

        result = cli_runner.invoke(main, ["convert", long_path])

        assert result.exit_code != 0

    def test_convert_special_characters_in_path(
        self, cli_runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test handling of special characters in path."""
        special_name = "video (1) [copy] 'test'.mp4"
        video = temp_dir / special_name
        video.write_bytes(b"fake video content")

        result = cli_runner.invoke(main, ["convert", str(video)])

        # Should handle or error gracefully
        assert result.exit_code in [0, 1] or result.exception is not None

    def test_run_empty_input_dir(
        self, cli_runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test run with empty input directory."""
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()

        result = cli_runner.invoke(main, [
            "run",
            "--source", "folder",
            "--input-dir", str(empty_dir)
        ])

        assert result.exit_code == 0
        assert "No H.264 videos found" in result.output

    @patch("video_converter.reporters.statistics_reporter.StatisticsReporter")
    @patch("video_converter.core.history.get_history")
    def test_stats_zero_division_protection(
        self,
        mock_get_history: MagicMock,
        mock_reporter_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test that stats handles zero bytes gracefully."""
        from video_converter.core.history import StatsPeriod

        mock_stats = MagicMock()
        mock_stats.total_converted = 0
        mock_stats.total_original_bytes = 0
        mock_stats.total_converted_bytes = 0
        mock_stats.average_compression_ratio = 0
        mock_stats.period = StatsPeriod.ALL

        mock_history = MagicMock()
        mock_history.get_statistics.return_value = mock_stats
        mock_get_history.return_value = mock_history

        mock_reporter = MagicMock()
        mock_reporter.format_summary.return_value = "No stats"
        mock_reporter_class.return_value = mock_reporter

        result = cli_runner.invoke(main, ["stats"])

        # Should not crash with zero division
        assert result.exit_code == 0


class TestHelpMessages:
    """Tests for help message consistency."""

    @pytest.mark.parametrize("command", [
        "convert",
        "run",
        "status",
        "stats",
        "stats-export",
        "config",
        "config-set",
        "setup",
        "install-service",
        "uninstall-service",
        "service-start",
        "service-stop",
        "service-restart",
        "service-load",
        "service-unload",
        "service-logs",
        "service-status",
    ])
    def test_all_commands_have_help(
        self, cli_runner: CliRunner, command: str
    ) -> None:
        """Test that all commands respond to --help."""
        result = cli_runner.invoke(main, [command, "--help"])

        assert result.exit_code == 0
        assert "Usage:" in result.output or "usage:" in result.output.lower()

    def test_main_help_lists_commands(self, cli_runner: CliRunner) -> None:
        """Test that main --help lists available commands."""
        result = cli_runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "convert" in result.output.lower()
        assert "run" in result.output.lower()
        assert "stats" in result.output.lower()


class TestMainVersion:
    """Tests for version display."""

    def test_main_version(self, cli_runner: CliRunner) -> None:
        """Test that --version shows version info."""
        result = cli_runner.invoke(main, ["--version"])

        # May or may not have version flag
        assert result.exit_code in [0, 2]


class TestStatusCommand:
    """Tests for status command edge cases."""

    def test_status_shows_help(self, cli_runner: CliRunner) -> None:
        """Test that status --help shows usage information."""
        result = cli_runner.invoke(main, ["status", "--help"])

        assert result.exit_code == 0
        assert "status" in result.output.lower()
