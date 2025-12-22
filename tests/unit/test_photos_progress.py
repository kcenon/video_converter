"""Unit tests for Photos-specific progress display components.

This module provides tests for PhotosProgressDisplay, PhotosLibraryInfo,
and the null object pattern implementations for quiet mode.

SDS Reference: SDS-U01-002
SRS Reference: SRS-801 (Progress Display)
"""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock

import pytest
from rich.console import Console

from video_converter.ui.progress import (
    PhotosLibraryInfo,
    PhotosProgressDisplay,
    ProgressDisplayManager,
    _NullPhotosProgress,
)


class TestPhotosLibraryInfo:
    """Tests for PhotosLibraryInfo dataclass."""

    def test_creation_with_values(self) -> None:
        """Test creating PhotosLibraryInfo with values."""
        info = PhotosLibraryInfo(
            library_path="/Users/test/Pictures/Photos Library.photoslibrary",
            total_videos=150,
            total_size=50_000_000_000,
            estimated_savings=25_000_000_000,
        )

        assert info.library_path == "/Users/test/Pictures/Photos Library.photoslibrary"
        assert info.total_videos == 150
        assert info.total_size == 50_000_000_000
        assert info.estimated_savings == 25_000_000_000


class TestPhotosProgressDisplay:
    """Tests for PhotosProgressDisplay class."""

    def test_initialization(self) -> None:
        """Test PhotosProgressDisplay initialization."""
        display = PhotosProgressDisplay(total_videos=100, total_size=10_000_000_000)

        assert display.total_videos == 100
        assert display.total_size == 10_000_000_000
        assert display.completed_count == 0
        assert display.failed_count == 0
        assert display.total_saved_bytes == 0

    def test_initialization_with_defaults(self) -> None:
        """Test PhotosProgressDisplay initialization with defaults."""
        display = PhotosProgressDisplay(total_videos=50)

        assert display.total_videos == 50
        assert display.total_size == 0

    def test_show_library_info(self) -> None:
        """Test show_library_info displays panel."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display = PhotosProgressDisplay(
            total_videos=100,
            total_size=50_000_000_000,
            console=console,
        )

        info = PhotosLibraryInfo(
            library_path="/Users/test/Pictures/Photos Library.photoslibrary",
            total_videos=100,
            total_size=50_000_000_000,
            estimated_savings=25_000_000_000,
        )

        display.show_library_info(info)

        result = output.getvalue()
        assert "Photos Library Conversion" in result
        assert "100" in result

    def test_show_library_info_truncates_long_path(self) -> None:
        """Test show_library_info truncates long library paths."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display = PhotosProgressDisplay(total_videos=10, console=console)

        # Create a very long path
        long_path = "/Users/username/Pictures/Photos Library.photoslibrary"
        info = PhotosLibraryInfo(
            library_path=long_path,
            total_videos=10,
            total_size=1_000_000_000,
            estimated_savings=500_000_000,
        )

        display.show_library_info(info)

        # Should not raise any errors
        result = output.getvalue()
        assert len(result) > 0

    def test_start_and_finish(self) -> None:
        """Test start and finish methods."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display = PhotosProgressDisplay(total_videos=10, console=console)

        # Start should not raise
        display.start()
        assert display._live is not None

        # Finish should clean up
        display.finish()
        assert display._live is None

    def test_start_video(self) -> None:
        """Test start_video updates display."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display = PhotosProgressDisplay(total_videos=10, console=console)
        display.start()

        try:
            display.start_video(
                filename="vacation_2024.mov",
                video_index=1,
                album="Vacation",
                date="2024-07-15",
                original_size=1_000_000_000,
            )

            # Verify internal state updated
            assert display._current_video_info is not None
        finally:
            display.finish()

    def test_start_video_truncates_long_filename(self) -> None:
        """Test start_video truncates very long filenames."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display = PhotosProgressDisplay(total_videos=10, console=console)
        display.start()

        try:
            long_filename = "a" * 50 + ".mov"
            display.start_video(
                filename=long_filename,
                video_index=1,
            )

            # Should not raise
            assert display._current_video_info is not None
        finally:
            display.finish()

    def test_update_export_progress(self) -> None:
        """Test update_export_progress updates display."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display = PhotosProgressDisplay(total_videos=10, console=console)
        display.start()

        try:
            display.update_export_progress(50.0)
            display.update_export_progress(100.0)
            # Should not raise
        finally:
            display.finish()

    def test_update_convert_progress(self) -> None:
        """Test update_convert_progress updates display."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display = PhotosProgressDisplay(total_videos=10, console=console)
        display.start()

        try:
            display.update_convert_progress(
                percentage=42.0,
                speed=3.5,
                eta="1:30",
            )
            # Should not raise
        finally:
            display.finish()

    def test_update_convert_from_info(self) -> None:
        """Test update_convert_from_info with ProgressInfo object."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display = PhotosProgressDisplay(total_videos=10, console=console)
        display.start()

        try:
            # Create a mock ProgressInfo
            mock_info = MagicMock()
            mock_info.percentage = 65.0
            mock_info.speed = 4.2
            mock_info.eta_formatted = "0:45"

            display.update_convert_from_info(mock_info)
            # Should not raise
        finally:
            display.finish()

    def test_complete_video_success(self) -> None:
        """Test complete_video tracks successful conversion."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display = PhotosProgressDisplay(total_videos=10, console=console)
        display.start()

        try:
            assert display.completed_count == 0
            assert display.total_saved_bytes == 0

            display.complete_video(success=True, saved_bytes=500_000_000)

            assert display.completed_count == 1
            assert display.failed_count == 0
            assert display.total_saved_bytes == 500_000_000
        finally:
            display.finish()

    def test_complete_video_failure(self) -> None:
        """Test complete_video tracks failed conversion."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display = PhotosProgressDisplay(total_videos=10, console=console)
        display.start()

        try:
            display.complete_video(success=False)

            assert display.completed_count == 0
            assert display.failed_count == 1
            assert display.total_saved_bytes == 0
        finally:
            display.finish()

    def test_complete_video_multiple(self) -> None:
        """Test complete_video with multiple videos."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display = PhotosProgressDisplay(total_videos=10, console=console)
        display.start()

        try:
            display.complete_video(success=True, saved_bytes=100_000_000)
            display.complete_video(success=True, saved_bytes=200_000_000)
            display.complete_video(success=False)
            display.complete_video(success=True, saved_bytes=150_000_000)

            assert display.completed_count == 3
            assert display.failed_count == 1
            assert display.total_saved_bytes == 450_000_000
        finally:
            display.finish()

    def test_show_summary(self) -> None:
        """Test show_summary displays completion panel."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display = PhotosProgressDisplay(total_videos=10, console=console)

        display.show_summary(
            successful=8,
            failed=2,
            total_saved=5_000_000_000,
            elapsed_time=3600.0,
        )

        result = output.getvalue()
        assert "Conversion Complete" in result
        assert "8" in result  # successful count

    def test_show_summary_with_hours(self) -> None:
        """Test show_summary formats hours correctly."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display = PhotosProgressDisplay(total_videos=10, console=console)

        # 2 hours 30 minutes 45 seconds
        display.show_summary(
            successful=10,
            failed=0,
            total_saved=10_000_000_000,
            elapsed_time=9045.0,
        )

        result = output.getvalue()
        assert "2h" in result
        assert "30m" in result

    def test_show_summary_with_minutes(self) -> None:
        """Test show_summary formats minutes correctly."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display = PhotosProgressDisplay(total_videos=10, console=console)

        # 45 minutes 30 seconds
        display.show_summary(
            successful=10,
            failed=0,
            total_saved=10_000_000_000,
            elapsed_time=2730.0,
        )

        result = output.getvalue()
        assert "45m" in result

    def test_show_summary_with_seconds_only(self) -> None:
        """Test show_summary formats seconds only correctly."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display = PhotosProgressDisplay(total_videos=10, console=console)

        display.show_summary(
            successful=1,
            failed=0,
            total_saved=100_000_000,
            elapsed_time=45.0,
        )

        result = output.getvalue()
        assert "45s" in result

    def test_format_size_bytes(self) -> None:
        """Test _format_size with bytes."""
        display = PhotosProgressDisplay(total_videos=10)
        assert display._format_size(500) == "500 B"

    def test_format_size_kilobytes(self) -> None:
        """Test _format_size with kilobytes."""
        display = PhotosProgressDisplay(total_videos=10)
        assert display._format_size(1500) == "1 KB"

    def test_format_size_megabytes(self) -> None:
        """Test _format_size with megabytes."""
        display = PhotosProgressDisplay(total_videos=10)
        result = display._format_size(150_000_000)
        assert "MB" in result

    def test_format_size_gigabytes(self) -> None:
        """Test _format_size with gigabytes."""
        display = PhotosProgressDisplay(total_videos=10)
        result = display._format_size(5_000_000_000)
        assert "GB" in result

    def test_format_size_terabytes(self) -> None:
        """Test _format_size with terabytes."""
        display = PhotosProgressDisplay(total_videos=10)
        result = display._format_size(5_000_000_000_000)
        assert "TB" in result

    def test_format_size_zero(self) -> None:
        """Test _format_size with zero."""
        display = PhotosProgressDisplay(total_videos=10)
        assert display._format_size(0) == "0 B"

    def test_format_size_negative(self) -> None:
        """Test _format_size with negative value."""
        display = PhotosProgressDisplay(total_videos=10)
        assert display._format_size(-100) == "0 B"


class TestNullPhotosProgress:
    """Tests for _NullPhotosProgress null object."""

    def test_initialization(self) -> None:
        """Test _NullPhotosProgress initialization."""
        null_progress = _NullPhotosProgress()

        assert null_progress.completed_count == 0
        assert null_progress.failed_count == 0
        assert null_progress.total_saved_bytes == 0

    def test_show_library_info_no_op(self) -> None:
        """Test show_library_info is a no-op."""
        null_progress = _NullPhotosProgress()
        info = PhotosLibraryInfo(
            library_path="/path",
            total_videos=10,
            total_size=1000,
            estimated_savings=500,
        )

        # Should not raise
        null_progress.show_library_info(info)

    def test_start_no_op(self) -> None:
        """Test start is a no-op."""
        null_progress = _NullPhotosProgress()
        null_progress.start()  # Should not raise

    def test_start_video_no_op(self) -> None:
        """Test start_video is a no-op."""
        null_progress = _NullPhotosProgress()
        null_progress.start_video(
            filename="test.mov",
            video_index=1,
            album="Test",
            date="2024-01-01",
            original_size=1000,
        )  # Should not raise

    def test_update_export_progress_no_op(self) -> None:
        """Test update_export_progress is a no-op."""
        null_progress = _NullPhotosProgress()
        null_progress.update_export_progress(50.0)  # Should not raise

    def test_update_convert_progress_no_op(self) -> None:
        """Test update_convert_progress is a no-op."""
        null_progress = _NullPhotosProgress()
        null_progress.update_convert_progress(
            percentage=50.0,
            speed=3.0,
            eta="1:00",
        )  # Should not raise

    def test_update_convert_from_info_no_op(self) -> None:
        """Test update_convert_from_info is a no-op."""
        null_progress = _NullPhotosProgress()
        mock_info = MagicMock()
        null_progress.update_convert_from_info(mock_info)  # Should not raise

    def test_complete_video_tracks_success(self) -> None:
        """Test complete_video still tracks counts even in quiet mode."""
        null_progress = _NullPhotosProgress()

        null_progress.complete_video(success=True, saved_bytes=1000)
        assert null_progress.completed_count == 1
        assert null_progress.total_saved_bytes == 1000

        null_progress.complete_video(success=True, saved_bytes=2000)
        assert null_progress.completed_count == 2
        assert null_progress.total_saved_bytes == 3000

    def test_complete_video_tracks_failure(self) -> None:
        """Test complete_video tracks failures in quiet mode."""
        null_progress = _NullPhotosProgress()

        null_progress.complete_video(success=False)
        assert null_progress.failed_count == 1
        assert null_progress.completed_count == 0

    def test_finish_no_op(self) -> None:
        """Test finish is a no-op."""
        null_progress = _NullPhotosProgress()
        null_progress.finish()  # Should not raise

    def test_show_summary_no_op(self) -> None:
        """Test show_summary is a no-op."""
        null_progress = _NullPhotosProgress()
        null_progress.show_summary(
            successful=10,
            failed=2,
            total_saved=5000,
            elapsed_time=3600.0,
        )  # Should not raise


class TestProgressDisplayManager:
    """Tests for ProgressDisplayManager Photos-related methods."""

    def test_create_photos_progress_normal_mode(self) -> None:
        """Test create_photos_progress returns real display in normal mode."""
        manager = ProgressDisplayManager(quiet=False)
        display = manager.create_photos_progress(total_videos=10, total_size=1000)

        assert isinstance(display, PhotosProgressDisplay)

    def test_create_photos_progress_quiet_mode(self) -> None:
        """Test create_photos_progress returns null object in quiet mode."""
        manager = ProgressDisplayManager(quiet=True)
        display = manager.create_photos_progress(total_videos=10, total_size=1000)

        assert isinstance(display, _NullPhotosProgress)

    def test_create_photos_progress_with_custom_console(self) -> None:
        """Test create_photos_progress uses custom console."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)

        manager = ProgressDisplayManager(quiet=False, console=console)
        display = manager.create_photos_progress(total_videos=10)

        assert isinstance(display, PhotosProgressDisplay)
        assert display.console == console


class TestPhotosProgressDisplayIntegration:
    """Integration tests for PhotosProgressDisplay workflow."""

    def test_full_conversion_workflow(self) -> None:
        """Test complete Photos conversion display workflow."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display = PhotosProgressDisplay(
            total_videos=3,
            total_size=3_000_000_000,
            console=console,
        )

        # Show library info
        info = PhotosLibraryInfo(
            library_path="~/Pictures/Photos Library.photoslibrary",
            total_videos=3,
            total_size=3_000_000_000,
            estimated_savings=1_500_000_000,
        )
        display.show_library_info(info)

        # Start progress
        display.start()

        try:
            # Process video 1
            display.start_video(
                filename="video1.mov",
                video_index=1,
                album="Vacation",
                date="2024-01-15",
                original_size=1_000_000_000,
            )
            display.update_export_progress(50.0)
            display.update_export_progress(100.0)
            display.update_convert_progress(50.0, speed=3.0, eta="0:30")
            display.update_convert_progress(100.0, speed=3.0, eta="0:00")
            display.complete_video(success=True, saved_bytes=500_000_000)

            # Process video 2
            display.start_video(
                filename="video2.mov",
                video_index=2,
                original_size=1_000_000_000,
            )
            display.update_export_progress(100.0)
            display.update_convert_progress(100.0, speed=4.0, eta="0:00")
            display.complete_video(success=True, saved_bytes=500_000_000)

            # Process video 3 (failure)
            display.start_video(
                filename="video3.mov",
                video_index=3,
                original_size=1_000_000_000,
            )
            display.update_export_progress(100.0)
            display.update_convert_progress(30.0, speed=2.0, eta="1:00")
            display.complete_video(success=False)

            assert display.completed_count == 2
            assert display.failed_count == 1
            assert display.total_saved_bytes == 1_000_000_000

        finally:
            display.finish()

        # Show summary
        display.show_summary(
            successful=2,
            failed=1,
            total_saved=1_000_000_000,
            elapsed_time=120.0,
        )

        result = output.getvalue()
        assert "Conversion Complete" in result

    def test_quiet_mode_workflow(self) -> None:
        """Test Photos conversion workflow in quiet mode."""
        manager = ProgressDisplayManager(quiet=True)
        display = manager.create_photos_progress(total_videos=3, total_size=3000)

        # All operations should be no-ops but still track counts
        info = PhotosLibraryInfo(
            library_path="/path",
            total_videos=3,
            total_size=3000,
            estimated_savings=1500,
        )
        display.show_library_info(info)
        display.start()
        display.start_video("video1.mov", 1)
        display.update_export_progress(100.0)
        display.update_convert_progress(100.0)
        display.complete_video(success=True, saved_bytes=500)
        display.complete_video(success=True, saved_bytes=500)
        display.complete_video(success=False)
        display.finish()
        display.show_summary(2, 1, 1000, 60.0)

        # Counts should still be tracked
        assert display.completed_count == 2
        assert display.failed_count == 1
        assert display.total_saved_bytes == 1000
