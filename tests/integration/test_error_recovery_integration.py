"""Integration tests for error recovery and retry logic.

This module tests the error recovery workflow including error classification,
retry strategies, encoder fallback, and failure tracking.

SRS Reference: SRS-605 (Failure Isolation and Error Recovery)
SDS Reference: SDS-C01-004
"""

from __future__ import annotations

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
    ConversionMode,
    ConversionResult,
    ErrorCategory,
    RecoveryAction,
)
from video_converter.processors.retry_manager import (
    FailureType,
    RetryAttempt,
    RetryConfig,
    RetryManager,
    RetryResult,
    RetryStrategy,
)


class TestErrorClassification:
    """Tests for error message classification."""

    @pytest.fixture
    def recovery_manager(self, tmp_path: Path) -> ErrorRecoveryManager:
        """Create an ErrorRecoveryManager for testing."""
        return ErrorRecoveryManager(failed_dir=tmp_path / "failed")

    @pytest.mark.parametrize(
        "error_message,expected_category",
        [
            ("File not found: /path/to/video.mp4", ErrorCategory.INPUT_ERROR),
            ("No such file or directory", ErrorCategory.INPUT_ERROR),
            ("Invalid input file format", ErrorCategory.INPUT_ERROR),
            ("Unsupported codec in input", ErrorCategory.INPUT_ERROR),
            ("Permission denied: /path/to/file", ErrorCategory.PERMISSION_ERROR),
            ("Access denied to resource", ErrorCategory.PERMISSION_ERROR),
            ("No space left on device", ErrorCategory.DISK_SPACE_ERROR),
            ("Disk full, cannot write output", ErrorCategory.DISK_SPACE_ERROR),
            ("Insufficient storage available", ErrorCategory.DISK_SPACE_ERROR),
            ("VideoToolbox encoder failed", ErrorCategory.ENCODING_ERROR),
            ("FFmpeg conversion failed", ErrorCategory.ENCODING_ERROR),
            ("libx265 encoding error", ErrorCategory.ENCODING_ERROR),
            ("Metadata could not be written", ErrorCategory.METADATA_ERROR),
            ("ExifTool failed to update", ErrorCategory.METADATA_ERROR),
        ],
    )
    def test_classify_error_from_message(
        self,
        recovery_manager: ErrorRecoveryManager,
        error_message: str,
        expected_category: ErrorCategory,
    ) -> None:
        """Test that error messages are classified correctly."""
        category = recovery_manager.classify_error(error_message)
        assert category == expected_category

    def test_classify_error_unknown_for_unrecognized(
        self, recovery_manager: ErrorRecoveryManager
    ) -> None:
        """Test that unrecognized errors are classified as UNKNOWN."""
        category = recovery_manager.classify_error("Something went wrong")
        assert category == ErrorCategory.UNKNOWN_ERROR

    def test_classify_error_from_result(
        self, recovery_manager: ErrorRecoveryManager, tmp_path: Path
    ) -> None:
        """Test error classification from ConversionResult."""
        from video_converter.core.types import ConversionRequest

        request = ConversionRequest(
            input_path=tmp_path / "input.mp4",
            output_path=tmp_path / "output.mp4",
        )

        result = ConversionResult(
            success=False,
            request=request,
            error_message="VideoToolbox encoder initialization failed",
        )

        category = recovery_manager.classify_error(None, result=result)
        assert category == ErrorCategory.ENCODING_ERROR


class TestRecoveryActions:
    """Tests for recovery action mapping."""

    def test_recovery_mapping_completeness(self) -> None:
        """Test that all error categories have recovery actions."""
        for category in ErrorCategory:
            assert category in ERROR_RECOVERY_MAPPING

    @pytest.mark.parametrize(
        "category,expected_action",
        [
            (ErrorCategory.INPUT_ERROR, RecoveryAction.SKIP),
            (ErrorCategory.ENCODING_ERROR, RecoveryAction.RETRY_WITH_FALLBACK),
            (ErrorCategory.VALIDATION_ERROR, RecoveryAction.RETRY_ONCE),
            (ErrorCategory.METADATA_ERROR, RecoveryAction.KEEP_VIDEO_LOG_WARNING),
            (ErrorCategory.DISK_SPACE_ERROR, RecoveryAction.PAUSE_NOTIFY_USER),
            (ErrorCategory.PERMISSION_ERROR, RecoveryAction.SKIP),
            (ErrorCategory.UNKNOWN_ERROR, RecoveryAction.SKIP),
        ],
    )
    def test_recovery_action_mapping(
        self, category: ErrorCategory, expected_action: RecoveryAction
    ) -> None:
        """Test that error categories map to correct recovery actions."""
        manager = ErrorRecoveryManager()
        action = manager.get_recovery_action(category)
        assert action == expected_action


class TestFailureHandling:
    """Tests for failure handling and tracking."""

    @pytest.fixture
    def recovery_manager(self, tmp_path: Path) -> ErrorRecoveryManager:
        """Create an ErrorRecoveryManager for testing."""
        failed_dir = tmp_path / "failed"
        return ErrorRecoveryManager(failed_dir=failed_dir)

    def test_cleanup_partial_output(
        self, recovery_manager: ErrorRecoveryManager, tmp_path: Path
    ) -> None:
        """Test that partial output files are cleaned up."""
        partial_file = tmp_path / "partial_output.mp4"
        partial_file.write_bytes(b"partial content")

        assert partial_file.exists()

        result = recovery_manager.cleanup_partial_output(partial_file)

        assert result is True
        assert not partial_file.exists()

    def test_cleanup_nonexistent_file(
        self, recovery_manager: ErrorRecoveryManager, tmp_path: Path
    ) -> None:
        """Test cleanup of non-existent file returns False."""
        nonexistent = tmp_path / "nonexistent.mp4"
        result = recovery_manager.cleanup_partial_output(nonexistent)
        assert result is False

    def test_handle_failure_creates_record(
        self, recovery_manager: ErrorRecoveryManager, tmp_path: Path
    ) -> None:
        """Test that handle_failure creates a failure record."""
        input_path = tmp_path / "input.mp4"
        output_path = tmp_path / "output.mp4"
        input_path.write_bytes(b"test content")

        record = recovery_manager.handle_failure(
            input_path=input_path,
            output_path=output_path,
            category=ErrorCategory.ENCODING_ERROR,
            error_message="FFmpeg failed",
            move_to_failed=False,
        )

        assert record.input_path == input_path
        assert record.error_category == ErrorCategory.ENCODING_ERROR
        assert record.error_message == "FFmpeg failed"
        assert record.can_retry is True

    def test_handle_failure_cleans_up_partial_output(
        self, recovery_manager: ErrorRecoveryManager, tmp_path: Path
    ) -> None:
        """Test that handle_failure cleans up partial output."""
        input_path = tmp_path / "input.mp4"
        output_path = tmp_path / "partial_output.mp4"
        input_path.write_bytes(b"input content")
        output_path.write_bytes(b"partial output")

        recovery_manager.handle_failure(
            input_path=input_path,
            output_path=output_path,
            category=ErrorCategory.ENCODING_ERROR,
            error_message="Failed mid-conversion",
            move_to_failed=False,
        )

        assert not output_path.exists()

    def test_failure_records_tracking(
        self, recovery_manager: ErrorRecoveryManager, tmp_path: Path
    ) -> None:
        """Test that multiple failures are tracked."""
        for i in range(3):
            input_path = tmp_path / f"input{i}.mp4"
            output_path = tmp_path / f"output{i}.mp4"
            input_path.write_bytes(b"content")

            recovery_manager.handle_failure(
                input_path=input_path,
                output_path=output_path,
                category=ErrorCategory.ENCODING_ERROR,
                error_message=f"Error {i}",
                move_to_failed=False,
            )

        records = recovery_manager.failure_records
        assert len(records) == 3

    def test_get_retryable_failures(
        self, recovery_manager: ErrorRecoveryManager, tmp_path: Path
    ) -> None:
        """Test filtering of retryable failures."""
        # Create retryable failure
        encoding_path = tmp_path / "encoding_fail.mp4"
        encoding_path.write_bytes(b"content")
        recovery_manager.handle_failure(
            input_path=encoding_path,
            output_path=tmp_path / "out1.mp4",
            category=ErrorCategory.ENCODING_ERROR,
            error_message="Encoder failed",
            move_to_failed=False,
        )

        # Create non-retryable failure
        input_path = tmp_path / "input_fail.mp4"
        input_path.write_bytes(b"content")
        recovery_manager.handle_failure(
            input_path=input_path,
            output_path=tmp_path / "out2.mp4",
            category=ErrorCategory.INPUT_ERROR,
            error_message="File corrupted",
            move_to_failed=False,
        )

        retryable = recovery_manager.get_retryable_failures()
        assert len(retryable) == 1
        assert retryable[0].error_category == ErrorCategory.ENCODING_ERROR

    def test_get_failure_summary(
        self, recovery_manager: ErrorRecoveryManager, tmp_path: Path
    ) -> None:
        """Test failure summary generation."""
        # Add failures of different categories
        for category in [ErrorCategory.ENCODING_ERROR, ErrorCategory.ENCODING_ERROR,
                         ErrorCategory.INPUT_ERROR]:
            path = tmp_path / f"{category.value}.mp4"
            path.write_bytes(b"content")
            recovery_manager.handle_failure(
                input_path=path,
                output_path=tmp_path / "out.mp4",
                category=category,
                error_message="Error",
                move_to_failed=False,
            )

        summary = recovery_manager.get_failure_summary()

        assert summary["total_failures"] == 3
        assert summary["by_category"]["encoding_error"] == 2
        assert summary["by_category"]["input_error"] == 1

    def test_clear_failures(
        self, recovery_manager: ErrorRecoveryManager, tmp_path: Path
    ) -> None:
        """Test clearing failure records."""
        input_path = tmp_path / "input.mp4"
        input_path.write_bytes(b"content")

        recovery_manager.handle_failure(
            input_path=input_path,
            output_path=tmp_path / "out.mp4",
            category=ErrorCategory.ENCODING_ERROR,
            error_message="Error",
            move_to_failed=False,
        )

        count = recovery_manager.clear_failures()
        assert count == 1
        assert len(recovery_manager.failure_records) == 0


class TestDiskSpaceChecking:
    """Tests for disk space checking functionality."""

    def test_check_disk_space_returns_info(self, tmp_path: Path) -> None:
        """Test that check_disk_space returns valid info."""
        manager = ErrorRecoveryManager()
        info = manager.check_disk_space(tmp_path)

        assert isinstance(info, DiskSpaceInfo)
        assert info.total_bytes > 0
        assert info.free_bytes >= 0
        assert info.free_percent >= 0

    def test_has_sufficient_space_true(self, tmp_path: Path) -> None:
        """Test has_sufficient_space with adequate space."""
        manager = ErrorRecoveryManager(min_free_space=1024)
        sufficient, info = manager.has_sufficient_space(tmp_path)

        assert sufficient is True
        assert info.free_bytes >= 1024

    def test_has_sufficient_space_with_custom_requirement(
        self, tmp_path: Path
    ) -> None:
        """Test has_sufficient_space with custom byte requirement."""
        manager = ErrorRecoveryManager()
        sufficient, info = manager.has_sufficient_space(tmp_path, required_bytes=1024)

        assert sufficient is True


class TestRetryManager:
    """Tests for retry manager functionality."""

    def test_retry_config_defaults(self) -> None:
        """Test RetryConfig default values."""
        config = RetryConfig()

        assert config.max_attempts == 4
        assert config.switch_encoder_on_failure is True
        assert config.adjust_quality_on_failure is True
        assert config.quality_adjustment_step == 2
        assert config.max_crf_value == 28
        assert config.preserve_original_on_failure is True

    def test_retry_config_validation(self) -> None:
        """Test RetryConfig validation."""
        with pytest.raises(ValueError):
            RetryConfig(max_attempts=0)

        with pytest.raises(ValueError):
            RetryConfig(quality_adjustment_step=0)

    def test_determine_strategy_progression(self) -> None:
        """Test that retry strategies progress correctly."""
        manager = RetryManager()

        # First attempts use same settings
        assert manager._determine_strategy(1, None) == RetryStrategy.SAME_SETTINGS
        assert manager._determine_strategy(2, None) == RetryStrategy.SAME_SETTINGS

        # Third attempt switches encoder
        assert manager._determine_strategy(3, None) == RetryStrategy.SWITCH_ENCODER

        # Fourth attempt adjusts quality
        assert manager._determine_strategy(4, None) == RetryStrategy.ADJUST_QUALITY

    def test_classify_failure_types(self) -> None:
        """Test failure type classification."""
        from video_converter.core.types import ConversionRequest

        manager = RetryManager()
        request = ConversionRequest(
            input_path=Path("/test/input.mp4"),
            output_path=Path("/test/output.mp4"),
        )

        # Encoder failure
        result = ConversionResult(
            success=False,
            request=request,
            error_message="VideoToolbox encoder initialization failed",
        )
        assert manager._classify_failure(result, None) == FailureType.ENCODER_ERROR

        # Conversion failure
        result = ConversionResult(
            success=False,
            request=request,
            error_message="Unknown error occurred",
        )
        assert manager._classify_failure(result, None) == FailureType.CONVERSION_ERROR


class TestRetryResult:
    """Tests for RetryResult functionality."""

    def test_retry_result_success(self) -> None:
        """Test RetryResult for successful retry."""
        result = RetryResult(
            success=True,
            total_attempts=2,
            final_strategy=RetryStrategy.SWITCH_ENCODER,
        )

        assert result.success is True
        assert result.total_attempts == 2
        report = result.get_failure_report()
        assert "Succeeded" in report

    def test_retry_result_failure(self) -> None:
        """Test RetryResult for failed retry."""
        result = RetryResult(
            success=False,
            total_attempts=4,
            attempts=[
                RetryAttempt(
                    attempt_number=i,
                    strategy=RetryStrategy.SAME_SETTINGS,
                    mode=ConversionMode.HARDWARE,
                    crf=22,
                    error_message=f"Error {i}",
                    failure_type=FailureType.ENCODER_ERROR,
                )
                for i in range(1, 5)
            ],
            original_preserved=True,
        )

        report = result.get_failure_report()
        assert "Failed" in report
        assert "4" in report
        assert "preserved" in report.lower()

    def test_retry_result_to_dict(self) -> None:
        """Test RetryResult serialization."""
        result = RetryResult(
            success=True,
            total_attempts=1,
            final_strategy=RetryStrategy.SAME_SETTINGS,
        )

        data = result.to_dict()
        assert data["success"] is True
        assert data["total_attempts"] == 1
        assert data["final_strategy"] == "same_settings"


class TestRetryAttempt:
    """Tests for RetryAttempt functionality."""

    def test_retry_attempt_to_dict(self) -> None:
        """Test RetryAttempt serialization."""
        now = datetime.now()
        attempt = RetryAttempt(
            attempt_number=1,
            strategy=RetryStrategy.SAME_SETTINGS,
            mode=ConversionMode.HARDWARE,
            crf=22,
            started_at=now,
            completed_at=now,
            duration_seconds=5.5,
        )

        data = attempt.to_dict()
        assert data["attempt_number"] == 1
        assert data["strategy"] == "same_settings"
        assert data["mode"] == "hardware"
        assert data["crf"] == 22
        assert data["duration_seconds"] == 5.5


class TestFailureRecord:
    """Tests for FailureRecord functionality."""

    def test_failure_record_to_dict(self, tmp_path: Path) -> None:
        """Test FailureRecord serialization."""
        record = FailureRecord(
            input_path=tmp_path / "input.mp4",
            output_path=tmp_path / "output.mp4",
            error_category=ErrorCategory.ENCODING_ERROR,
            error_message="Test error",
            retry_count=2,
            can_retry=True,
        )

        data = record.to_dict()
        assert "input.mp4" in data["input_path"]
        assert data["error_category"] == "encoding_error"
        assert data["retry_count"] == 2
        assert data["can_retry"] is True

    def test_failure_record_from_dict(self, tmp_path: Path) -> None:
        """Test FailureRecord deserialization."""
        data = {
            "input_path": str(tmp_path / "input.mp4"),
            "output_path": str(tmp_path / "output.mp4"),
            "error_category": "encoding_error",
            "error_message": "Test error",
            "timestamp": datetime.now().isoformat(),
            "retry_count": 1,
            "can_retry": True,
            "moved_to": None,
        }

        record = FailureRecord.from_dict(data)
        assert record.error_category == ErrorCategory.ENCODING_ERROR
        assert record.retry_count == 1


class TestErrorRecoveryWorkflowIntegration:
    """Integration tests for complete error recovery workflow."""

    def test_full_error_recovery_workflow(self, tmp_path: Path) -> None:
        """Test complete error recovery workflow simulation."""
        failed_dir = tmp_path / "failed"
        manager = ErrorRecoveryManager(failed_dir=failed_dir)

        # Simulate failed conversion
        input_file = tmp_path / "video.mp4"
        output_file = tmp_path / "converted.mp4"
        input_file.write_bytes(b"video content")
        output_file.write_bytes(b"partial output")

        # Classify error
        error_message = "FFmpeg hevc encoding failed with exit code 1"
        category = manager.classify_error(error_message)
        assert category == ErrorCategory.ENCODING_ERROR

        # Get recovery action
        action = manager.get_recovery_action(category)
        assert action == RecoveryAction.RETRY_WITH_FALLBACK

        # Handle failure
        record = manager.handle_failure(
            input_path=input_file,
            output_path=output_file,
            category=category,
            error_message=error_message,
            move_to_failed=False,
        )

        # Verify cleanup
        assert not output_file.exists()

        # Check retryable
        retryable = manager.get_retryable_failures()
        assert len(retryable) == 1
        assert record in retryable

        # Prepare for retry
        retry_path = manager.prepare_retry(record)
        assert retry_path == input_file
        assert record.retry_count == 1

    def test_retry_manager_integration_with_error_recovery(
        self, tmp_path: Path
    ) -> None:
        """Test retry manager integration with error recovery."""
        recovery_manager = ErrorRecoveryManager(failed_dir=tmp_path / "failed")
        retry_manager = RetryManager(RetryConfig(max_attempts=3))

        # Simulate encoding error
        error_message = "VideoToolbox encoder not available"
        category = recovery_manager.classify_error(error_message)

        # Get recovery action
        action = recovery_manager.get_recovery_action(category)
        assert action == RecoveryAction.RETRY_WITH_FALLBACK

        # Determine retry strategy
        strategy = retry_manager._determine_strategy(3, FailureType.ENCODER_ERROR)
        assert strategy == RetryStrategy.SWITCH_ENCODER
