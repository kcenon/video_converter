"""Integration tests for Photos CLI commands.

This module tests the video-converter CLI with --source photos option,
including permission handling, filtering options, and progress display.

SRS Reference: SRS-301 (Photos Library Integration)
SDS Reference: SDS-P01-007
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from video_converter.__main__ import main


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Click CLI test runner."""
    return CliRunner()


class TestPhotosRunCommand:
    """Tests for the run command with --source photos."""

    def test_run_help_shows_source_option(self, cli_runner: CliRunner) -> None:
        """Test that run --help shows --source option."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert result.exit_code == 0
        assert "--source" in result.output

    def test_run_help_shows_photos_source(self, cli_runner: CliRunner) -> None:
        """Test that run --help mentions photos as a source."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert result.exit_code == 0
        assert "photos" in result.output.lower()

    def test_run_photos_executes_without_crash(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test run --source photos executes without crashing.

        Note: This test runs against the actual CLI without mocking.
        It verifies that the command executes and produces expected output format.
        """
        result = cli_runner.invoke(main, ["run", "--source", "photos"])

        # Should execute without raising exceptions
        # May succeed (exit 0) or fail due to permission issues (exit 1)
        assert result.exit_code in (0, 1)
        # Should show either scanning message or permission error
        assert (
            "Scanning" in result.output
            or "Access" in result.output
            or "denied" in result.output.lower()
            or "H.264" in result.output
        )

    def test_run_photos_dry_run_option_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test run --source photos --dry-run option is accepted."""
        result = cli_runner.invoke(main, ["run", "--source", "photos", "--dry-run"])

        # Dry-run option should be accepted (not rejected as invalid)
        # May succeed or fail due to permission issues
        assert result.exit_code in (0, 1)
        assert "Invalid" not in result.output or "dry" not in result.output.lower()


class TestPhotosRunCommandFilters:
    """Tests for Photos run command filtering options."""

    def test_run_photos_albums_option(self, cli_runner: CliRunner) -> None:
        """Test that --albums option is available."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert "--albums" in result.output

    def test_run_photos_exclude_albums_option(self, cli_runner: CliRunner) -> None:
        """Test that --exclude-albums option is available."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert "--exclude-albums" in result.output

    def test_run_photos_from_date_option(self, cli_runner: CliRunner) -> None:
        """Test that --from-date option is available."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert "--from-date" in result.output

    def test_run_photos_to_date_option(self, cli_runner: CliRunner) -> None:
        """Test that --to-date option is available."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert "--to-date" in result.output

    def test_run_photos_favorites_only_option(self, cli_runner: CliRunner) -> None:
        """Test that --favorites-only option is available."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert "--favorites" in result.output or "favorites" in result.output.lower()

    def test_run_photos_limit_option(self, cli_runner: CliRunner) -> None:
        """Test that --limit option is available."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert "--limit" in result.output

    def test_run_photos_with_albums_filter_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test run --source photos --albums option is accepted."""
        result = cli_runner.invoke(
            main,
            ["run", "--source", "photos", "--albums", "Vacation,Family"],
        )

        # Option should be accepted (not rejected as invalid)
        assert "Invalid value for '--albums'" not in result.output

    def test_run_photos_with_date_range_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test run --source photos with date range options accepted."""
        result = cli_runner.invoke(
            main,
            [
                "run",
                "--source",
                "photos",
                "--from-date",
                "2024-01-01",
                "--to-date",
                "2024-12-31",
            ],
        )

        # Options should be accepted (not rejected as invalid)
        assert "Invalid value for '--from-date'" not in result.output
        assert "Invalid value for '--to-date'" not in result.output

    def test_run_photos_with_limit_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test run --source photos --limit option is accepted."""
        result = cli_runner.invoke(
            main,
            ["run", "--source", "photos", "--limit", "10"],
        )

        # Option should be accepted (not rejected as invalid)
        assert "Invalid value for '--limit'" not in result.output


class TestPhotosSourceScanning:
    """Tests for Photos source scanning via run command."""

    def test_run_photos_shows_scanning_info(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test run --source photos shows scanning information."""
        result = cli_runner.invoke(main, ["run", "--source", "photos"])

        # Should show scanning or permission info
        assert result.exit_code in (0, 1)
        assert (
            "Scanning" in result.output
            or "H.264" in result.output
            or "Photos" in result.output
            or "Access" in result.output
        )


class TestPhotosCheckPermissionsOption:
    """Tests for --check-permissions option."""

    def test_check_permissions_option_available(self, cli_runner: CliRunner) -> None:
        """Test that --check-permissions option is available."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert "--check-permissions" in result.output

    def test_check_permissions_option_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test that --check-permissions option is accepted."""
        result = cli_runner.invoke(
            main,
            ["run", "--source", "photos", "--check-permissions"],
        )

        # Option should be accepted and should show permission status
        # May succeed or fail depending on system permissions
        assert result.exit_code in (0, 1)
        assert (
            "granted" in result.output.lower()
            or "denied" in result.output.lower()
            or "Full Disk Access" in result.output
            or "Photos" in result.output
        )


class TestPhotosQuietMode:
    """Tests for Photos commands in quiet mode."""

    def test_run_photos_quiet_mode_accepted(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test run --source photos with -q option is accepted."""
        result = cli_runner.invoke(main, ["-q", "run", "--source", "photos"])

        # Quiet mode should be accepted and suppress most output
        # "Scanning" message may or may not appear in quiet mode
        assert result.exit_code in (0, 1)


class TestPhotosConversionWorkflow:
    """Integration tests for complete Photos conversion workflow."""

    def test_photos_workflow_executes(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test Photos conversion workflow executes without crash."""
        result = cli_runner.invoke(main, ["run", "--source", "photos"])

        # Should execute without crashing
        assert result.exit_code in (0, 1)
        # Should show progress or error
        assert len(result.output) > 0


class TestPhotosErrorHandling:
    """Tests for Photos CLI error handling."""

    def test_invalid_source_rejected(self, cli_runner: CliRunner) -> None:
        """Test that invalid source values are rejected."""
        result = cli_runner.invoke(main, ["run", "--source", "invalid_source"])

        assert result.exit_code != 0

    def test_invalid_date_format_rejected(self, cli_runner: CliRunner) -> None:
        """Test that invalid date format is rejected."""
        result = cli_runner.invoke(
            main,
            ["run", "--source", "photos", "--from-date", "invalid-date"],
        )

        assert result.exit_code != 0 or "Invalid" in result.output

    def test_negative_limit_rejected(self, cli_runner: CliRunner) -> None:
        """Test that negative limit is rejected."""
        result = cli_runner.invoke(
            main,
            ["run", "--source", "photos", "--limit", "-1"],
        )

        assert result.exit_code != 0 or "Invalid" in result.output


class TestPhotosReimportOptions:
    """Tests for Photos reimport CLI options."""

    def test_reimport_option_available(self, cli_runner: CliRunner) -> None:
        """Test that --reimport option is available."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert "--reimport" in result.output

    def test_delete_originals_option_available(self, cli_runner: CliRunner) -> None:
        """Test that --delete-originals option is available."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert "--delete-originals" in result.output

    def test_keep_originals_option_available(self, cli_runner: CliRunner) -> None:
        """Test that --keep-originals option is available."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert "--keep-originals" in result.output

    def test_archive_album_option_available(self, cli_runner: CliRunner) -> None:
        """Test that --archive-album option is available."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert "--archive-album" in result.output

    def test_confirm_delete_option_available(self, cli_runner: CliRunner) -> None:
        """Test that --confirm-delete option is available."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert "--confirm-delete" in result.output


class TestPhotosReimportValidation:
    """Tests for Photos reimport option validation."""

    def test_delete_originals_requires_confirm(self, cli_runner: CliRunner) -> None:
        """Test that --delete-originals requires --confirm-delete."""
        result = cli_runner.invoke(
            main,
            ["run", "--source", "photos", "--reimport", "--delete-originals"],
        )

        assert result.exit_code != 0
        assert "--confirm-delete" in result.output or "confirm" in result.output.lower()

    def test_delete_and_keep_mutually_exclusive(self, cli_runner: CliRunner) -> None:
        """Test that --delete-originals and --keep-originals are mutually exclusive."""
        result = cli_runner.invoke(
            main,
            [
                "run",
                "--source",
                "photos",
                "--reimport",
                "--delete-originals",
                "--keep-originals",
                "--confirm-delete",
            ],
        )

        assert result.exit_code != 0
        assert "Cannot use both" in result.output

    def test_delete_originals_requires_reimport(self, cli_runner: CliRunner) -> None:
        """Test that --delete-originals requires --reimport."""
        result = cli_runner.invoke(
            main,
            ["run", "--source", "photos", "--delete-originals", "--confirm-delete"],
        )

        assert result.exit_code != 0
        assert "--reimport" in result.output or "reimport" in result.output.lower()

    def test_keep_originals_requires_reimport(self, cli_runner: CliRunner) -> None:
        """Test that --keep-originals requires --reimport."""
        result = cli_runner.invoke(
            main,
            ["run", "--source", "photos", "--keep-originals"],
        )

        assert result.exit_code != 0
        assert "--reimport" in result.output or "reimport" in result.output.lower()

    def test_reimport_with_delete_and_confirm_accepted(
        self, cli_runner: CliRunner
    ) -> None:
        """Test valid combination of --reimport --delete-originals --confirm-delete."""
        result = cli_runner.invoke(
            main,
            [
                "run",
                "--source",
                "photos",
                "--reimport",
                "--delete-originals",
                "--confirm-delete",
            ],
        )

        # Should not fail due to invalid options
        # May fail due to permission or other runtime issues
        assert "Cannot use both" not in result.output
        assert "requires --confirm-delete" not in result.output

    def test_reimport_with_keep_accepted(self, cli_runner: CliRunner) -> None:
        """Test valid combination of --reimport --keep-originals."""
        result = cli_runner.invoke(
            main,
            ["run", "--source", "photos", "--reimport", "--keep-originals"],
        )

        # Should not fail due to invalid options
        assert "Cannot use both" not in result.output
        assert "require --reimport" not in result.output

    def test_reimport_with_custom_album_accepted(self, cli_runner: CliRunner) -> None:
        """Test --reimport with custom --archive-album."""
        result = cli_runner.invoke(
            main,
            [
                "run",
                "--source",
                "photos",
                "--reimport",
                "--archive-album",
                "My Custom Album",
            ],
        )

        # Should not fail due to invalid options
        assert "Invalid value for '--archive-album'" not in result.output


class TestPhotosMaxConcurrentOption:
    """Tests for --max-concurrent option with Photos source."""

    def test_max_concurrent_option_available(self, cli_runner: CliRunner) -> None:
        """Test that --max-concurrent option is available."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert "--max-concurrent" in result.output

    def test_max_concurrent_option_accepted(self, cli_runner: CliRunner) -> None:
        """Test that valid --max-concurrent value is accepted."""
        result = cli_runner.invoke(
            main,
            ["run", "--source", "photos", "--max-concurrent", "4"],
        )

        # Should not fail due to invalid option
        assert "Invalid value for '--max-concurrent'" not in result.output

    def test_max_concurrent_invalid_below_range(self, cli_runner: CliRunner) -> None:
        """Test that --max-concurrent below 1 is rejected."""
        result = cli_runner.invoke(
            main,
            ["run", "--source", "photos", "--max-concurrent", "0"],
        )

        assert result.exit_code != 0
        assert "--max-concurrent must be between 1 and 8" in result.output

    def test_max_concurrent_invalid_above_range(self, cli_runner: CliRunner) -> None:
        """Test that --max-concurrent above 8 is rejected."""
        result = cli_runner.invoke(
            main,
            ["run", "--source", "photos", "--max-concurrent", "10"],
        )

        assert result.exit_code != 0
        assert "--max-concurrent must be between 1 and 8" in result.output

    def test_max_concurrent_with_valid_values(self, cli_runner: CliRunner) -> None:
        """Test that all valid --max-concurrent values (1-8) are accepted."""
        for value in [1, 2, 4, 8]:
            result = cli_runner.invoke(
                main,
                ["run", "--source", "photos", "--max-concurrent", str(value)],
            )

            # Should not fail due to invalid option value
            assert "--max-concurrent must be between" not in result.output
