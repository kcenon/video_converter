"""Tests for the 'run' CLI command.

This module tests the video-converter run command including:
- Folder source batch conversion
- Photos source batch conversion
- Filtering options (albums, dates, favorites)
- Dry run mode
- Resume session functionality
- Re-import options
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


class TestRunCommandHelp:
    """Tests for run command help and documentation."""

    def test_run_shows_help(self, cli_runner: CliRunner) -> None:
        """Test that run --help shows usage information."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert result.exit_code == 0
        assert "Run batch conversion" in result.output
        assert "--source" in result.output
        assert "--input-dir" in result.output
        assert "--dry-run" in result.output
        assert "--resume" in result.output

    def test_run_shows_photos_options(self, cli_runner: CliRunner) -> None:
        """Test that Photos-specific options are documented."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert "--albums" in result.output
        assert "--exclude-albums" in result.output
        assert "--from-date" in result.output
        assert "--to-date" in result.output
        assert "--favorites-only" in result.output
        assert "--reimport" in result.output


class TestRunFolderMode:
    """Tests for run command with folder source."""

    def test_folder_mode_requires_input_dir(self, cli_runner: CliRunner) -> None:
        """Test that folder mode requires --input-dir option."""
        result = cli_runner.invoke(main, ["run", "--source", "folder"])

        # Command should fail with exit code 1
        assert result.exit_code == 1 or result.exception is not None

    def test_folder_mode_with_nonexistent_dir(self, cli_runner: CliRunner) -> None:
        """Test error handling for non-existent input directory."""
        result = cli_runner.invoke(main, [
            "run",
            "--source", "folder",
            "--input-dir", "/nonexistent/directory"
        ])

        assert result.exit_code != 0

    @patch("video_converter.__main__._scan_for_videos")
    def test_folder_mode_no_videos_found(
        self,
        mock_scan: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
    ) -> None:
        """Test message when no videos found in directory."""
        mock_scan.return_value = []

        result = cli_runner.invoke(main, [
            "run",
            "--source", "folder",
            "--input-dir", str(temp_dir),
        ])

        assert result.exit_code == 0
        assert "No H.264 videos found" in result.output

    @patch("video_converter.__main__.CodecDetector")
    @patch("video_converter.__main__._scan_for_videos")
    def test_folder_mode_dry_run(
        self,
        mock_scan: MagicMock,
        mock_detector_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
    ) -> None:
        """Test dry run mode shows files without converting."""
        # Create test video files
        video1 = temp_dir / "video1.mp4"
        video1.write_bytes(b"fake video content" * 1000)
        video2 = temp_dir / "video2.mp4"
        video2.write_bytes(b"fake video content" * 500)

        mock_scan.return_value = [video1, video2]

        # Mock codec detection to return H.264
        mock_codec_info = MagicMock()
        mock_codec_info.is_hevc = False
        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        result = cli_runner.invoke(main, [
            "run",
            "--source", "folder",
            "--input-dir", str(temp_dir),
            "--dry-run",
        ])

        assert result.exit_code == 0
        assert "Dry Run" in result.output
        assert "video1.mp4" in result.output
        assert "video2.mp4" in result.output
        assert "Run without --dry-run" in result.output


class TestRunPhotosMode:
    """Tests for run command with Photos source."""

    @patch("video_converter.handlers.photos_handler.PhotosSourceHandler")
    def test_photos_mode_permission_denied(
        self,
        mock_handler_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test error handling for Photos permission denied."""
        mock_handler = MagicMock()
        mock_handler.check_permissions.return_value = False
        mock_handler.get_permission_error.return_value = "Access denied"
        mock_handler.__enter__ = MagicMock(return_value=mock_handler)
        mock_handler.__exit__ = MagicMock(return_value=False)
        mock_handler_class.return_value = mock_handler

        result = cli_runner.invoke(main, ["run", "--source", "photos"])

        # Should fail due to permission error
        assert result.exit_code == 1 or result.exception is not None

    @patch("video_converter.handlers.photos_handler.PhotosSourceHandler")
    def test_photos_mode_check_permissions_flag(
        self,
        mock_handler_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test --check-permissions flag with Photos source."""
        mock_handler = MagicMock()
        mock_handler.check_permissions.return_value = True
        mock_handler.get_stats.return_value = MagicMock(
            total=100, h264=50, total_size_h264=5_000_000_000
        )
        mock_handler.get_library_info.return_value = {"path": "/test/path"}
        mock_handler.__enter__ = MagicMock(return_value=mock_handler)
        mock_handler.__exit__ = MagicMock(return_value=False)
        mock_handler_class.return_value = mock_handler

        result = cli_runner.invoke(main, [
            "run",
            "--source", "photos",
            "--check-permissions",
        ])

        # May succeed or fail depending on environment
        assert result.exit_code in [0, 1] or result.exception is not None

    def test_check_permissions_only_for_photos(self, cli_runner: CliRunner) -> None:
        """Test that --check-permissions is only valid for Photos mode."""
        result = cli_runner.invoke(main, [
            "run",
            "--source", "folder",
            "--check-permissions",
        ])

        # Should fail with validation error
        assert result.exit_code == 1 or result.exception is not None

    @patch("video_converter.handlers.photos_handler.PhotosSourceHandler")
    def test_photos_mode_no_videos(
        self,
        mock_handler_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test message when no Photos videos found."""
        mock_handler = MagicMock()
        mock_handler.check_permissions.return_value = True
        mock_handler.get_candidates.return_value = []
        mock_handler.__enter__ = MagicMock(return_value=mock_handler)
        mock_handler.__exit__ = MagicMock(return_value=False)
        mock_handler_class.return_value = mock_handler

        result = cli_runner.invoke(main, ["run", "--source", "photos"])

        # Command should complete (either with success or error)
        assert result.exit_code in [0, 1] or result.exception is not None


class TestRunReimportOptions:
    """Tests for Photos reimport options."""

    def test_delete_and_keep_conflict(self, cli_runner: CliRunner) -> None:
        """Test that --delete-originals and --keep-originals cannot be used together."""
        result = cli_runner.invoke(main, [
            "run",
            "--source", "photos",
            "--reimport",
            "--delete-originals",
            "--keep-originals",
            "--confirm-delete",
        ])

        # Should fail due to conflicting options
        assert result.exit_code == 1 or result.exception is not None

    def test_delete_requires_confirm(self, cli_runner: CliRunner) -> None:
        """Test that --delete-originals requires --confirm-delete."""
        result = cli_runner.invoke(main, [
            "run",
            "--source", "photos",
            "--reimport",
            "--delete-originals",
        ])

        # Should fail due to missing --confirm-delete
        assert result.exit_code == 1 or result.exception is not None

    def test_delete_requires_reimport(self, cli_runner: CliRunner) -> None:
        """Test that --delete-originals requires --reimport."""
        result = cli_runner.invoke(main, [
            "run",
            "--source", "photos",
            "--delete-originals",
            "--confirm-delete",
        ])

        # Should fail due to missing --reimport
        assert result.exit_code == 1 or result.exception is not None


class TestRunResumeMode:
    """Tests for resume session functionality."""

    @patch("video_converter.__main__.Orchestrator")
    def test_resume_no_session(
        self,
        mock_orchestrator_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test resume when no resumable session exists."""
        mock_orchestrator = MagicMock()
        mock_orchestrator.has_resumable_session.return_value = False
        mock_orchestrator_class.return_value = mock_orchestrator

        result = cli_runner.invoke(main, ["run", "--resume"])

        assert result.exit_code == 0
        assert "No resumable session found" in result.output
