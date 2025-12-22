"""Unit tests for UI progress display module."""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from video_converter.ui.progress import (
    BatchProgressDisplay,
    IndeterminateSpinner,
    ProgressDisplayManager,
    SingleFileProgressDisplay,
    _NullBatchProgress,
    _NullProgress,
    _NullSpinner,
)


class TestSingleFileProgressDisplay:
    """Tests for SingleFileProgressDisplay."""

    def test_init_with_defaults(self) -> None:
        """Test initialization with default values."""
        progress = SingleFileProgressDisplay(filename="test.mp4")
        assert progress.filename == "test.mp4"
        assert progress.original_size == 0

    def test_init_with_custom_values(self) -> None:
        """Test initialization with custom values."""
        console = Console(file=StringIO())
        progress = SingleFileProgressDisplay(
            filename="video.mov",
            original_size=1_500_000_000,
            console=console,
        )
        assert progress.filename == "video.mov"
        assert progress.original_size == 1_500_000_000

    def test_format_size_bytes(self) -> None:
        """Test size formatting for bytes."""
        progress = SingleFileProgressDisplay(filename="test.mp4")
        assert progress._format_size(500) == "500 B"
        assert progress._format_size(0) == "0 B"

    def test_format_size_kilobytes(self) -> None:
        """Test size formatting for kilobytes."""
        progress = SingleFileProgressDisplay(filename="test.mp4")
        assert progress._format_size(1024) == "1 KB"
        assert progress._format_size(2048) == "2 KB"

    def test_format_size_megabytes(self) -> None:
        """Test size formatting for megabytes."""
        progress = SingleFileProgressDisplay(filename="test.mp4")
        assert progress._format_size(1024 * 1024) == "1.0 MB"
        assert progress._format_size(500 * 1024 * 1024) == "500.0 MB"

    def test_format_size_gigabytes(self) -> None:
        """Test size formatting for gigabytes."""
        progress = SingleFileProgressDisplay(filename="test.mp4")
        assert progress._format_size(1024 * 1024 * 1024) == "1.0 GB"
        assert progress._format_size(2 * 1024 * 1024 * 1024) == "2.0 GB"

    def test_start_creates_progress(self) -> None:
        """Test start creates progress instance."""
        console = Console(file=StringIO(), force_terminal=True)
        progress = SingleFileProgressDisplay(
            filename="test.mp4",
            original_size=1_000_000,
            console=console,
        )
        progress.start()
        assert progress._progress is not None
        assert progress._task_id is not None
        progress.finish()

    def test_finish_clears_progress(self) -> None:
        """Test finish clears progress instance."""
        console = Console(file=StringIO(), force_terminal=True)
        progress = SingleFileProgressDisplay(filename="test.mp4", console=console)
        progress.start()
        progress.finish()
        assert progress._progress is None

    def test_update_before_start_is_safe(self) -> None:
        """Test update before start does not raise error."""
        progress = SingleFileProgressDisplay(filename="test.mp4")
        # Should not raise
        progress.update(percentage=50.0, current_size=500_000)

    def test_update_with_info_object(self) -> None:
        """Test update_from_info with ProgressInfo object."""
        from video_converter.converters.progress import ProgressInfo

        console = Console(file=StringIO(), force_terminal=True)
        progress = SingleFileProgressDisplay(filename="test.mp4", console=console)
        progress.start()

        info = ProgressInfo(
            current_time=30.0,
            total_time=120.0,
            current_size=15_000_000,
            speed=4.2,
        )
        progress.update_from_info(info)
        progress.finish()


class TestBatchProgressDisplay:
    """Tests for BatchProgressDisplay."""

    def test_init_with_defaults(self) -> None:
        """Test initialization with default values."""
        progress = BatchProgressDisplay(total_files=10)
        assert progress.total_files == 10

    def test_format_size(self) -> None:
        """Test size formatting method."""
        progress = BatchProgressDisplay(total_files=5)
        assert progress._format_size(0) == "0 B"
        assert progress._format_size(1024) == "1 KB"
        assert progress._format_size(1024 * 1024) == "1.0 MB"

    def test_start_creates_progress_components(self) -> None:
        """Test start creates all progress components."""
        console = Console(file=StringIO(), force_terminal=True)
        progress = BatchProgressDisplay(total_files=5, console=console)
        progress.start()
        assert progress._file_progress is not None
        assert progress._overall_progress is not None
        assert progress._live is not None
        progress.finish()

    def test_complete_file_increments_count(self) -> None:
        """Test complete_file increments completed count."""
        console = Console(file=StringIO(), force_terminal=True)
        progress = BatchProgressDisplay(total_files=3, console=console)
        progress.start()

        assert progress.completed_count == 0
        progress.complete_file(saved_bytes=100_000)
        assert progress.completed_count == 1
        progress.complete_file(saved_bytes=200_000)
        assert progress.completed_count == 2

        progress.finish()

    def test_complete_file_accumulates_saved_bytes(self) -> None:
        """Test complete_file accumulates saved bytes."""
        console = Console(file=StringIO(), force_terminal=True)
        progress = BatchProgressDisplay(total_files=3, console=console)
        progress.start()

        assert progress.total_saved_bytes == 0
        progress.complete_file(saved_bytes=100_000)
        assert progress.total_saved_bytes == 100_000
        progress.complete_file(saved_bytes=200_000)
        assert progress.total_saved_bytes == 300_000

        progress.finish()

    def test_finish_clears_live(self) -> None:
        """Test finish clears live display."""
        console = Console(file=StringIO(), force_terminal=True)
        progress = BatchProgressDisplay(total_files=5, console=console)
        progress.start()
        progress.finish()
        assert progress._live is None


class TestIndeterminateSpinner:
    """Tests for IndeterminateSpinner."""

    def test_init(self) -> None:
        """Test initialization."""
        spinner = IndeterminateSpinner(message="Loading...")
        assert spinner.message == "Loading..."

    def test_start_creates_progress(self) -> None:
        """Test start creates progress instance."""
        console = Console(file=StringIO(), force_terminal=True)
        spinner = IndeterminateSpinner(message="Processing...", console=console)
        spinner.start()
        assert spinner._progress is not None
        spinner.finish()

    def test_update_message(self) -> None:
        """Test update changes message."""
        console = Console(file=StringIO(), force_terminal=True)
        spinner = IndeterminateSpinner(message="Step 1", console=console)
        spinner.start()
        spinner.update("Step 2")  # Should not raise
        spinner.finish()

    def test_finish_clears_progress(self) -> None:
        """Test finish clears progress instance."""
        console = Console(file=StringIO(), force_terminal=True)
        spinner = IndeterminateSpinner(message="Working...", console=console)
        spinner.start()
        spinner.finish()
        assert spinner._progress is None


class TestProgressDisplayManager:
    """Tests for ProgressDisplayManager."""

    def test_init_defaults_to_not_quiet(self) -> None:
        """Test default initialization is not quiet."""
        manager = ProgressDisplayManager()
        assert manager.quiet is False

    def test_init_with_quiet_mode(self) -> None:
        """Test initialization with quiet mode."""
        manager = ProgressDisplayManager(quiet=True)
        assert manager.quiet is True

    def test_create_single_file_progress_normal_mode(self) -> None:
        """Test create_single_file_progress returns real progress in normal mode."""
        manager = ProgressDisplayManager(quiet=False)
        progress = manager.create_single_file_progress("test.mp4", 1_000_000)
        assert isinstance(progress, SingleFileProgressDisplay)

    def test_create_single_file_progress_quiet_mode(self) -> None:
        """Test create_single_file_progress returns null progress in quiet mode."""
        manager = ProgressDisplayManager(quiet=True)
        progress = manager.create_single_file_progress("test.mp4", 1_000_000)
        assert isinstance(progress, _NullProgress)

    def test_create_batch_progress_normal_mode(self) -> None:
        """Test create_batch_progress returns real progress in normal mode."""
        manager = ProgressDisplayManager(quiet=False)
        progress = manager.create_batch_progress(total_files=5)
        assert isinstance(progress, BatchProgressDisplay)

    def test_create_batch_progress_quiet_mode(self) -> None:
        """Test create_batch_progress returns null progress in quiet mode."""
        manager = ProgressDisplayManager(quiet=True)
        progress = manager.create_batch_progress(total_files=5)
        assert isinstance(progress, _NullBatchProgress)

    def test_create_spinner_normal_mode(self) -> None:
        """Test create_spinner returns real spinner in normal mode."""
        manager = ProgressDisplayManager(quiet=False)
        spinner = manager.create_spinner("Processing...")
        assert isinstance(spinner, IndeterminateSpinner)

    def test_create_spinner_quiet_mode(self) -> None:
        """Test create_spinner returns null spinner in quiet mode."""
        manager = ProgressDisplayManager(quiet=True)
        spinner = manager.create_spinner("Processing...")
        assert isinstance(spinner, _NullSpinner)

    def test_spinner_context_manager(self) -> None:
        """Test spinner context manager starts and stops spinner."""
        console = Console(file=StringIO(), force_terminal=True)
        manager = ProgressDisplayManager(quiet=False, console=console)

        with manager.spinner("Working...") as spinner:
            assert spinner._progress is not None

        # After context, spinner should be stopped
        assert spinner._progress is None


class TestNullProgress:
    """Tests for _NullProgress null object."""

    def test_all_methods_are_noop(self) -> None:
        """Test all methods do nothing without raising."""
        null = _NullProgress()
        null.start()
        null.update(percentage=50.0, current_size=500_000)
        null.finish()  # Should not raise

    def test_update_from_info_is_noop(self) -> None:
        """Test update_from_info does nothing."""
        from video_converter.converters.progress import ProgressInfo

        null = _NullProgress()
        info = ProgressInfo(current_time=30.0, total_time=120.0)
        null.update_from_info(info)  # Should not raise


class TestNullBatchProgress:
    """Tests for _NullBatchProgress null object."""

    def test_all_methods_are_noop(self) -> None:
        """Test most methods do nothing without raising."""
        null = _NullBatchProgress()
        null.start()
        null.start_file("test.mp4", 1, 1_000_000)
        null.update_file(percentage=50.0)
        null.finish()  # Should not raise

    def test_complete_file_tracks_count(self) -> None:
        """Test complete_file still tracks completion count."""
        null = _NullBatchProgress()
        assert null.completed_count == 0
        null.complete_file(saved_bytes=100_000)
        assert null.completed_count == 1
        assert null.total_saved_bytes == 100_000

    def test_properties_work_correctly(self) -> None:
        """Test properties return tracked values."""
        null = _NullBatchProgress()
        null.complete_file(saved_bytes=50_000)
        null.complete_file(saved_bytes=100_000)
        assert null.completed_count == 2
        assert null.total_saved_bytes == 150_000


class TestNullSpinner:
    """Tests for _NullSpinner null object."""

    def test_all_methods_are_noop(self) -> None:
        """Test all methods do nothing without raising."""
        null = _NullSpinner()
        null.start()
        null.update("New message")
        null.finish()
        null.finish("Success!")  # Should not raise
