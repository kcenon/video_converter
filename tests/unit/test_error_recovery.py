"""Unit tests for error_recovery module."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_converter.core.error_recovery import (
    DEFAULT_MIN_FREE_SPACE,
    ERROR_RECOVERY_MAPPING,
    DiskSpaceInfo,
    ErrorRecoveryManager,
    FailureRecord,
)
from video_converter.core.types import (
    ConversionRequest,
    ConversionResult,
    ErrorCategory,
    RecoveryAction,
)


class TestErrorCategory:
    """Tests for ErrorCategory enum."""

    def test_all_categories_defined(self) -> None:
        """Test that all expected error categories are defined."""
        expected = [
            "input_error",
            "encoding_error",
            "validation_error",
            "metadata_error",
            "disk_space_error",
            "permission_error",
            "unknown_error",
        ]
        actual = [cat.value for cat in ErrorCategory]
        assert sorted(actual) == sorted(expected)


class TestRecoveryAction:
    """Tests for RecoveryAction enum."""

    def test_all_actions_defined(self) -> None:
        """Test that all expected recovery actions are defined."""
        expected = [
            "skip",
            "retry_with_fallback",
            "retry_once",
            "keep_video_log_warning",
            "pause_notify_user",
            "abort",
        ]
        actual = [action.value for action in RecoveryAction]
        assert sorted(actual) == sorted(expected)


class TestErrorRecoveryMapping:
    """Tests for error category to recovery action mapping."""

    def test_mapping_complete(self) -> None:
        """Test that all error categories have a recovery action."""
        for category in ErrorCategory:
            assert category in ERROR_RECOVERY_MAPPING
            assert isinstance(ERROR_RECOVERY_MAPPING[category], RecoveryAction)

    def test_expected_mappings(self) -> None:
        """Test specific expected mappings."""
        assert ERROR_RECOVERY_MAPPING[ErrorCategory.INPUT_ERROR] == RecoveryAction.SKIP
        assert ERROR_RECOVERY_MAPPING[ErrorCategory.ENCODING_ERROR] == RecoveryAction.RETRY_WITH_FALLBACK
        assert ERROR_RECOVERY_MAPPING[ErrorCategory.VALIDATION_ERROR] == RecoveryAction.RETRY_ONCE
        assert ERROR_RECOVERY_MAPPING[ErrorCategory.METADATA_ERROR] == RecoveryAction.KEEP_VIDEO_LOG_WARNING
        assert ERROR_RECOVERY_MAPPING[ErrorCategory.DISK_SPACE_ERROR] == RecoveryAction.PAUSE_NOTIFY_USER


class TestFailureRecord:
    """Tests for FailureRecord dataclass."""

    def test_creation(self) -> None:
        """Test creating a failure record."""
        record = FailureRecord(
            input_path=Path("/test/video.mov"),
            output_path=Path("/test/video_h265.mp4"),
            error_category=ErrorCategory.ENCODING_ERROR,
            error_message="Encoder failed",
        )
        assert record.input_path == Path("/test/video.mov")
        assert record.output_path == Path("/test/video_h265.mp4")
        assert record.error_category == ErrorCategory.ENCODING_ERROR
        assert record.error_message == "Encoder failed"
        assert record.retry_count == 0
        assert record.can_retry is True
        assert record.moved_to is None

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        record = FailureRecord(
            input_path=Path("/test/video.mov"),
            output_path=Path("/test/video_h265.mp4"),
            error_category=ErrorCategory.INPUT_ERROR,
            error_message="File not found",
            can_retry=False,
        )
        data = record.to_dict()
        assert data["input_path"] == "/test/video.mov"
        assert data["output_path"] == "/test/video_h265.mp4"
        assert data["error_category"] == "input_error"
        assert data["error_message"] == "File not found"
        assert data["can_retry"] is False

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        data = {
            "input_path": "/test/video.mov",
            "output_path": "/test/video_h265.mp4",
            "error_category": "encoding_error",
            "error_message": "Encoder failed",
            "timestamp": "2024-01-01T12:00:00",
            "retry_count": 2,
            "can_retry": True,
            "moved_to": None,
        }
        record = FailureRecord.from_dict(data)
        assert record.input_path == Path("/test/video.mov")
        assert record.error_category == ErrorCategory.ENCODING_ERROR
        assert record.retry_count == 2


class TestDiskSpaceInfo:
    """Tests for DiskSpaceInfo dataclass."""

    def test_creation(self) -> None:
        """Test creating disk space info."""
        info = DiskSpaceInfo(
            path=Path("/home"),
            total_bytes=100_000_000_000,
            free_bytes=50_000_000_000,
            used_bytes=50_000_000_000,
        )
        assert info.path == Path("/home")
        assert info.total_bytes == 100_000_000_000
        assert info.free_bytes == 50_000_000_000

    def test_free_percent(self) -> None:
        """Test free space percentage calculation."""
        info = DiskSpaceInfo(
            path=Path("/"),
            total_bytes=100_000_000_000,
            free_bytes=25_000_000_000,
            used_bytes=75_000_000_000,
        )
        assert info.free_percent == 25.0

    def test_free_percent_zero_total(self) -> None:
        """Test free percentage when total is zero."""
        info = DiskSpaceInfo(
            path=Path("/"),
            total_bytes=0,
            free_bytes=0,
            used_bytes=0,
        )
        assert info.free_percent == 0.0


class TestErrorRecoveryManager:
    """Tests for ErrorRecoveryManager class."""

    def test_init_defaults(self) -> None:
        """Test initialization with default values."""
        manager = ErrorRecoveryManager()
        assert manager.failed_dir is None
        assert manager.min_free_space == DEFAULT_MIN_FREE_SPACE
        assert len(manager.failure_records) == 0

    def test_init_custom(self, tmp_path: Path) -> None:
        """Test initialization with custom values."""
        failed_dir = tmp_path / "failed"
        manager = ErrorRecoveryManager(
            failed_dir=failed_dir,
            min_free_space=500_000_000,
        )
        assert manager.failed_dir == failed_dir
        assert manager.min_free_space == 500_000_000

    @pytest.mark.parametrize(
        "error_message,expected_category",
        [
            ("File not found: /test/video.mov", ErrorCategory.INPUT_ERROR),
            ("No such file or directory", ErrorCategory.INPUT_ERROR),
            ("Unsupported codec", ErrorCategory.INPUT_ERROR),
            ("Permission denied", ErrorCategory.PERMISSION_ERROR),
            ("Access denied to file", ErrorCategory.PERMISSION_ERROR),
            ("No space left on device", ErrorCategory.DISK_SPACE_ERROR),
            ("Disk full", ErrorCategory.DISK_SPACE_ERROR),
            ("VideoToolbox encoder failed", ErrorCategory.ENCODING_ERROR),
            ("libx265 encoding error", ErrorCategory.ENCODING_ERROR),
            ("Conversion failed at frame 100", ErrorCategory.ENCODING_ERROR),
            ("Validation failed: duration mismatch", ErrorCategory.VALIDATION_ERROR),
            ("Metadata copy failed", ErrorCategory.METADATA_ERROR),
            ("ExifTool error", ErrorCategory.METADATA_ERROR),
            ("Some random error", ErrorCategory.UNKNOWN_ERROR),
        ],
    )
    def test_classify_error(
        self, error_message: str, expected_category: ErrorCategory
    ) -> None:
        """Test error classification based on error messages."""
        manager = ErrorRecoveryManager()
        category = manager.classify_error(error_message)
        assert category == expected_category

    def test_classify_error_empty(self) -> None:
        """Test classification with empty error message."""
        manager = ErrorRecoveryManager()
        category = manager.classify_error(None)
        assert category == ErrorCategory.UNKNOWN_ERROR

    def test_get_recovery_action(self) -> None:
        """Test getting recovery action for categories."""
        manager = ErrorRecoveryManager()
        assert manager.get_recovery_action(ErrorCategory.INPUT_ERROR) == RecoveryAction.SKIP
        assert manager.get_recovery_action(ErrorCategory.ENCODING_ERROR) == RecoveryAction.RETRY_WITH_FALLBACK

    def test_cleanup_partial_output(self, tmp_path: Path) -> None:
        """Test cleaning up partial output files."""
        manager = ErrorRecoveryManager()
        output_file = tmp_path / "partial_output.mp4"
        output_file.write_text("partial content")

        assert output_file.exists()
        result = manager.cleanup_partial_output(output_file)
        assert result is True
        assert not output_file.exists()

    def test_cleanup_partial_output_not_exists(self, tmp_path: Path) -> None:
        """Test cleanup when file doesn't exist."""
        manager = ErrorRecoveryManager()
        output_file = tmp_path / "nonexistent.mp4"

        result = manager.cleanup_partial_output(output_file)
        assert result is False

    def test_handle_failure_basic(self, tmp_path: Path) -> None:
        """Test handling a failure."""
        manager = ErrorRecoveryManager(failed_dir=tmp_path / "failed")
        input_file = tmp_path / "video.mov"
        output_file = tmp_path / "video_h265.mp4"
        input_file.write_text("video content")
        output_file.write_text("partial output")

        record = manager.handle_failure(
            input_path=input_file,
            output_path=output_file,
            category=ErrorCategory.ENCODING_ERROR,
            error_message="Encoder crashed",
            move_to_failed=True,
        )

        assert record.error_category == ErrorCategory.ENCODING_ERROR
        assert record.can_retry is True
        assert not output_file.exists()  # Cleaned up
        assert record.moved_to is not None
        assert record in manager.failure_records

    def test_handle_failure_no_move(self, tmp_path: Path) -> None:
        """Test handling failure without moving file."""
        manager = ErrorRecoveryManager()
        input_file = tmp_path / "video.mov"
        output_file = tmp_path / "video_h265.mp4"
        input_file.write_text("video content")

        record = manager.handle_failure(
            input_path=input_file,
            output_path=output_file,
            category=ErrorCategory.INPUT_ERROR,
            error_message="Invalid input",
            move_to_failed=False,
        )

        assert record.moved_to is None
        assert input_file.exists()

    def test_check_disk_space(self, tmp_path: Path) -> None:
        """Test disk space checking."""
        manager = ErrorRecoveryManager()
        info = manager.check_disk_space(tmp_path)

        assert info.path.exists()
        assert info.total_bytes > 0
        assert info.free_bytes > 0

    def test_has_sufficient_space(self, tmp_path: Path) -> None:
        """Test sufficient space checking."""
        manager = ErrorRecoveryManager(min_free_space=1024)
        sufficient, info = manager.has_sufficient_space(tmp_path)

        # Most systems have at least 1KB free
        assert sufficient is True

    def test_has_insufficient_space(self, tmp_path: Path) -> None:
        """Test when space is insufficient."""
        manager = ErrorRecoveryManager(min_free_space=10**18)  # 1 Exabyte
        sufficient, info = manager.has_sufficient_space(tmp_path)

        assert sufficient is False

    def test_get_retryable_failures(self, tmp_path: Path) -> None:
        """Test getting retryable failures."""
        manager = ErrorRecoveryManager()

        # Add retryable failure
        manager.handle_failure(
            input_path=tmp_path / "video1.mov",
            output_path=tmp_path / "video1_h265.mp4",
            category=ErrorCategory.ENCODING_ERROR,
            error_message="Encoder failed",
            move_to_failed=False,
        )

        # Add non-retryable failure
        manager.handle_failure(
            input_path=tmp_path / "video2.mov",
            output_path=tmp_path / "video2_h265.mp4",
            category=ErrorCategory.INPUT_ERROR,
            error_message="File not found",
            move_to_failed=False,
        )

        retryable = manager.get_retryable_failures()
        assert len(retryable) == 1
        assert retryable[0].error_category == ErrorCategory.ENCODING_ERROR

    def test_prepare_retry(self, tmp_path: Path) -> None:
        """Test preparing a failed conversion for retry."""
        failed_dir = tmp_path / "failed"
        manager = ErrorRecoveryManager(failed_dir=failed_dir)

        input_file = tmp_path / "video.mov"
        input_file.write_text("video content")

        record = manager.handle_failure(
            input_path=input_file,
            output_path=tmp_path / "video_h265.mp4",
            category=ErrorCategory.ENCODING_ERROR,
            error_message="Encoder failed",
            move_to_failed=True,
        )

        # File should be moved
        assert record.moved_to is not None
        assert record.moved_to.exists()

        # Prepare for retry
        retry_path = manager.prepare_retry(record)
        assert retry_path == input_file
        assert input_file.exists()
        assert record.moved_to is None

    def test_mark_retry_success(self, tmp_path: Path) -> None:
        """Test marking a retry as successful."""
        manager = ErrorRecoveryManager()

        record = manager.handle_failure(
            input_path=tmp_path / "video.mov",
            output_path=tmp_path / "video_h265.mp4",
            category=ErrorCategory.VALIDATION_ERROR,
            error_message="Validation failed",
            move_to_failed=False,
        )

        assert record in manager.failure_records
        manager.mark_retry_success(record)
        assert record not in manager.failure_records

    def test_clear_failures(self, tmp_path: Path) -> None:
        """Test clearing all failure records."""
        manager = ErrorRecoveryManager()

        for i in range(3):
            manager.handle_failure(
                input_path=tmp_path / f"video{i}.mov",
                output_path=tmp_path / f"video{i}_h265.mp4",
                category=ErrorCategory.UNKNOWN_ERROR,
                error_message="Error",
                move_to_failed=False,
            )

        assert len(manager.failure_records) == 3
        count = manager.clear_failures()
        assert count == 3
        assert len(manager.failure_records) == 0

    def test_get_failure_summary(self, tmp_path: Path) -> None:
        """Test getting failure summary."""
        manager = ErrorRecoveryManager()

        manager.handle_failure(
            input_path=tmp_path / "video1.mov",
            output_path=tmp_path / "video1_h265.mp4",
            category=ErrorCategory.ENCODING_ERROR,
            error_message="Encoder failed",
            move_to_failed=False,
        )
        manager.handle_failure(
            input_path=tmp_path / "video2.mov",
            output_path=tmp_path / "video2_h265.mp4",
            category=ErrorCategory.ENCODING_ERROR,
            error_message="Encoder failed again",
            move_to_failed=False,
        )
        manager.handle_failure(
            input_path=tmp_path / "video3.mov",
            output_path=tmp_path / "video3_h265.mp4",
            category=ErrorCategory.INPUT_ERROR,
            error_message="Not found",
            move_to_failed=False,
        )

        summary = manager.get_failure_summary()
        assert summary["total_failures"] == 3
        assert summary["retryable"] == 2
        assert summary["by_category"]["encoding_error"] == 2
        assert summary["by_category"]["input_error"] == 1

    def test_move_to_failed_dir_name_collision(self, tmp_path: Path) -> None:
        """Test moving to failed directory with name collision."""
        failed_dir = tmp_path / "failed"
        failed_dir.mkdir()
        manager = ErrorRecoveryManager(failed_dir=failed_dir)

        # Create input file
        input_file = tmp_path / "video.mov"
        input_file.write_text("content")

        # Create existing file in failed directory
        existing = failed_dir / "video.mov"
        existing.write_text("existing")

        record = manager.handle_failure(
            input_path=input_file,
            output_path=tmp_path / "video_h265.mp4",
            category=ErrorCategory.ENCODING_ERROR,
            error_message="Failed",
            move_to_failed=True,
        )

        # Should have created a new name with timestamp
        assert record.moved_to is not None
        assert record.moved_to.name != "video.mov"
        assert "video_" in record.moved_to.name
