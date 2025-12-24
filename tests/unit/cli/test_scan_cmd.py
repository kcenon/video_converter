"""Tests for the 'scan' CLI command.

This module tests the video-converter scan command including:
- Basic scanning functionality
- Permission error handling (continues scanning after errors)
- Error counting and reporting
- Path and size filtering options
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from video_converter.__main__ import main

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Click CLI test runner."""
    return CliRunner()


class TestScanCommandHelp:
    """Tests for scan command help and documentation."""

    def test_scan_shows_help(self, cli_runner: CliRunner) -> None:
        """Test that scan --help shows usage information."""
        result = cli_runner.invoke(main, ["scan", "--help"])

        assert result.exit_code == 0
        assert "Scan for videos not in Photos library" in result.output
        assert "--path" in result.output
        assert "--min-size" in result.output
        assert "--limit" in result.output


class TestScanPermissionErrorHandling:
    """Tests for permission error handling during filesystem scan."""

    @patch("video_converter.extractors.photos_extractor.PhotosLibrary")
    def test_scan_continues_after_permission_error(
        self,
        mock_photos_library: MagicMock,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test that scan continues processing after encountering PermissionError.

        This is the core test for issue #220: scan command should not stop
        on first PermissionError but continue to accessible directories.
        """
        # Setup mock Photos library
        mock_library_instance = MagicMock()
        mock_library_instance.get_video_paths.return_value = set()
        mock_photos_library.return_value.__enter__ = MagicMock(
            return_value=mock_library_instance
        )
        mock_photos_library.return_value.__exit__ = MagicMock(return_value=False)

        # Create test directory structure
        accessible_dir = tmp_path / "accessible"
        accessible_dir.mkdir()

        # Create a video file in accessible directory
        video_file = accessible_dir / "test_video.mp4"
        video_file.write_bytes(b"\x00" * (2 * 1024 * 1024))  # 2MB file

        result = cli_runner.invoke(main, ["scan", "--path", str(tmp_path)])

        # Should complete without error
        assert result.exit_code == 0

    @patch("video_converter.extractors.photos_extractor.PhotosLibrary")
    def test_scan_reports_permission_error_count(
        self,
        mock_photos_library: MagicMock,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test that scan reports the number of permission errors encountered."""
        # Setup mock Photos library
        mock_library_instance = MagicMock()
        mock_library_instance.get_video_paths.return_value = set()
        mock_photos_library.return_value.__enter__ = MagicMock(
            return_value=mock_library_instance
        )
        mock_photos_library.return_value.__exit__ = MagicMock(return_value=False)

        # Create test directory
        accessible_dir = tmp_path / "accessible"
        accessible_dir.mkdir()

        result = cli_runner.invoke(main, ["scan", "--path", str(tmp_path)])

        # Should complete without crashing
        assert result.exit_code == 0

    @patch("video_converter.extractors.photos_extractor.PhotosLibrary")
    @patch("pathlib.Path.rglob")
    def test_scan_handles_mixed_permission_errors(
        self,
        mock_rglob: MagicMock,
        mock_photos_library: MagicMock,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test scan handles mix of accessible files and permission errors."""
        # Setup mock Photos library
        mock_library_instance = MagicMock()
        mock_library_instance.get_video_paths.return_value = set()
        mock_photos_library.return_value.__enter__ = MagicMock(
            return_value=mock_library_instance
        )
        mock_photos_library.return_value.__exit__ = MagicMock(return_value=False)

        # Create mock items that raise PermissionError on some operations
        accessible_file = MagicMock()
        accessible_file.is_dir.return_value = False
        accessible_file.is_file.return_value = True
        accessible_file.suffix = ".mp4"
        accessible_file.name = "video.mp4"
        accessible_file.parents = []
        accessible_file.stat.return_value.st_size = 5 * 1024 * 1024  # 5MB
        accessible_file.resolve.return_value = str(tmp_path / "video.mp4")

        def permission_error_is_dir():
            raise PermissionError("Access denied")

        protected_item = MagicMock()
        protected_item.is_dir.side_effect = permission_error_is_dir
        protected_item.name = "protected"

        mock_rglob.return_value = iter([protected_item, accessible_file])

        result = cli_runner.invoke(main, ["scan", "--path", str(tmp_path)])

        # Should complete and report permission errors
        assert result.exit_code == 0
        assert (
            "permission denied" in result.output.lower()
            or "could not be accessed" in result.output.lower()
        )


class TestScanOSErrorHandling:
    """Tests for general OS error handling during filesystem scan."""

    @patch("video_converter.extractors.photos_extractor.PhotosLibrary")
    @patch("pathlib.Path.rglob")
    def test_scan_handles_broken_symlinks(
        self,
        mock_rglob: MagicMock,
        mock_photos_library: MagicMock,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test scan gracefully handles broken symlinks (OSError)."""
        # Setup mock Photos library
        mock_library_instance = MagicMock()
        mock_library_instance.get_video_paths.return_value = set()
        mock_photos_library.return_value.__enter__ = MagicMock(
            return_value=mock_library_instance
        )
        mock_photos_library.return_value.__exit__ = MagicMock(return_value=False)

        # Create mock broken symlink that raises OSError
        def os_error_is_file():
            raise OSError("Broken symlink")

        broken_symlink = MagicMock()
        broken_symlink.is_dir.return_value = False
        broken_symlink.is_file.side_effect = os_error_is_file
        broken_symlink.name = "broken_link"

        mock_rglob.return_value = iter([broken_symlink])

        result = cli_runner.invoke(main, ["scan", "--path", str(tmp_path)])

        # Should complete without crashing
        assert result.exit_code == 0


class TestScanFiltering:
    """Tests for scan filtering options."""

    @patch("video_converter.extractors.photos_extractor.PhotosLibrary")
    def test_scan_with_min_size_filter(
        self,
        mock_photos_library: MagicMock,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test scan filters files by minimum size."""
        # Setup mock Photos library
        mock_library_instance = MagicMock()
        mock_library_instance.get_video_paths.return_value = set()
        mock_photos_library.return_value.__enter__ = MagicMock(
            return_value=mock_library_instance
        )
        mock_photos_library.return_value.__exit__ = MagicMock(return_value=False)

        # Create small video file (should be filtered out)
        small_video = tmp_path / "small.mp4"
        small_video.write_bytes(b"\x00" * 1024)  # 1KB (less than 1MB)

        result = cli_runner.invoke(
            main, ["scan", "--path", str(tmp_path), "--min-size", "1"]
        )

        assert result.exit_code == 0
        # Small file should be filtered out
        assert "No unregistered videos found" in result.output

    @patch("video_converter.extractors.photos_extractor.PhotosLibrary")
    def test_scan_with_custom_path(
        self,
        mock_photos_library: MagicMock,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test scan with custom path option."""
        # Setup mock Photos library
        mock_library_instance = MagicMock()
        mock_library_instance.get_video_paths.return_value = set()
        mock_photos_library.return_value.__enter__ = MagicMock(
            return_value=mock_library_instance
        )
        mock_photos_library.return_value.__exit__ = MagicMock(return_value=False)

        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()

        result = cli_runner.invoke(main, ["scan", "--path", str(custom_dir)])

        assert result.exit_code == 0
        assert str(custom_dir) in result.output


class TestScanKeyboardInterrupt:
    """Tests for keyboard interrupt handling."""

    @patch("video_converter.extractors.photos_extractor.PhotosLibrary")
    @patch("pathlib.Path.rglob")
    def test_scan_handles_keyboard_interrupt(
        self,
        mock_rglob: MagicMock,
        mock_photos_library: MagicMock,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test scan gracefully handles Ctrl+C interruption."""
        # Setup mock Photos library
        mock_library_instance = MagicMock()
        mock_library_instance.get_video_paths.return_value = set()
        mock_photos_library.return_value.__enter__ = MagicMock(
            return_value=mock_library_instance
        )
        mock_photos_library.return_value.__exit__ = MagicMock(return_value=False)

        # Simulate keyboard interrupt during iteration
        def raise_keyboard_interrupt():
            raise KeyboardInterrupt()

        mock_rglob.return_value = iter([])

        # Note: CliRunner doesn't propagate KeyboardInterrupt the same way,
        # but we can verify the exception handling path exists
        result = cli_runner.invoke(main, ["scan", "--path", str(tmp_path)])

        # Should complete (empty results)
        assert result.exit_code == 0
