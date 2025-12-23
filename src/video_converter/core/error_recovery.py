"""Error recovery and failure isolation for video conversion.

This module implements failure isolation to ensure one video's failure
doesn't affect others, with proper error recovery strategies.

SDS Reference: SDS-C01-004
SRS Reference: SRS-605 (Failure Isolation and Error Recovery)

Error Categories and Recovery Actions:
    | Category       | Recovery Action         |
    |----------------|-------------------------|
    | Input Error    | Skip, log warning       |
    | Encoding Error | Retry with fallback     |
    | Validation     | Retry once              |
    | Metadata Error | Keep video, log warning |
    | Disk Space     | Pause, notify user      |

Example:
    >>> from video_converter.core.error_recovery import ErrorRecoveryManager
    >>> from pathlib import Path
    >>>
    >>> manager = ErrorRecoveryManager(failed_dir=Path("./failed"))
    >>>
    >>> # Classify an error
    >>> category = manager.classify_error(error_message, result)
    >>> action = manager.get_recovery_action(category)
    >>>
    >>> # Handle a failed conversion
    >>> manager.handle_failure(input_path, output_path, category, error_message)
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from video_converter.core.types import (
    ConversionResult,
    ErrorCategory,
    RecoveryAction,
)

if TYPE_CHECKING:
    from video_converter.processors.quality_validator import ValidationResult

logger = logging.getLogger(__name__)


# Mapping of error categories to default recovery actions
ERROR_RECOVERY_MAPPING: dict[ErrorCategory, RecoveryAction] = {
    ErrorCategory.INPUT_ERROR: RecoveryAction.SKIP,
    ErrorCategory.ENCODING_ERROR: RecoveryAction.RETRY_WITH_FALLBACK,
    ErrorCategory.VALIDATION_ERROR: RecoveryAction.RETRY_ONCE,
    ErrorCategory.METADATA_ERROR: RecoveryAction.KEEP_VIDEO_LOG_WARNING,
    ErrorCategory.DISK_SPACE_ERROR: RecoveryAction.PAUSE_NOTIFY_USER,
    ErrorCategory.PERMISSION_ERROR: RecoveryAction.SKIP,
    ErrorCategory.UNKNOWN_ERROR: RecoveryAction.SKIP,
}

# Minimum free disk space required (in bytes) - default 1GB
DEFAULT_MIN_FREE_SPACE = 1024 * 1024 * 1024


@dataclass
class FailureRecord:
    """Record of a conversion failure for tracking and retry.

    Attributes:
        input_path: Path to the original input file.
        output_path: Intended output path.
        error_category: Classified error category.
        error_message: Detailed error message.
        timestamp: When the failure occurred.
        retry_count: Number of retry attempts made.
        can_retry: Whether this failure can be retried.
        moved_to: Path where failed file was moved (if any).
    """

    input_path: Path
    output_path: Path
    error_category: ErrorCategory
    error_message: str
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    can_retry: bool = True
    moved_to: Path | None = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "input_path": str(self.input_path),
            "output_path": str(self.output_path),
            "error_category": self.error_category.value,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
            "retry_count": self.retry_count,
            "can_retry": self.can_retry,
            "moved_to": str(self.moved_to) if self.moved_to else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> FailureRecord:
        """Create from dictionary."""
        return cls(
            input_path=Path(data["input_path"]),
            output_path=Path(data["output_path"]),
            error_category=ErrorCategory(data["error_category"]),
            error_message=data["error_message"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            retry_count=data.get("retry_count", 0),
            can_retry=data.get("can_retry", True),
            moved_to=Path(data["moved_to"]) if data.get("moved_to") else None,
        )


@dataclass
class DiskSpaceInfo:
    """Information about disk space availability.

    Attributes:
        path: Path checked for disk space.
        total_bytes: Total disk space in bytes.
        free_bytes: Available disk space in bytes.
        used_bytes: Used disk space in bytes.
        free_percent: Free space as percentage (0-100).
    """

    path: Path
    total_bytes: int
    free_bytes: int
    used_bytes: int

    @property
    def free_percent(self) -> float:
        """Calculate free space percentage."""
        if self.total_bytes <= 0:
            return 0.0
        return (self.free_bytes / self.total_bytes) * 100


class ErrorRecoveryManager:
    """Manage error recovery and failure isolation for conversions.

    This class provides:
    - Error classification based on error messages and context
    - Recovery action determination
    - Partial output file cleanup
    - Failed file tracking and movement
    - Disk space monitoring
    - Manual retry support for failed conversions

    Attributes:
        failed_dir: Directory for moving failed files.
        min_free_space: Minimum required free disk space in bytes.
        failure_records: List of recorded failures.
    """

    def __init__(
        self,
        failed_dir: Path | None = None,
        min_free_space: int = DEFAULT_MIN_FREE_SPACE,
    ) -> None:
        """Initialize the error recovery manager.

        Args:
            failed_dir: Directory to move failed files. If None, files stay in place.
            min_free_space: Minimum required free disk space in bytes.
        """
        self.failed_dir = failed_dir
        self.min_free_space = min_free_space
        self._failure_records: list[FailureRecord] = []

    @property
    def failure_records(self) -> list[FailureRecord]:
        """Get all recorded failures."""
        return self._failure_records.copy()

    def classify_error(
        self,
        error_message: str | None,
        result: ConversionResult | None = None,
        validation: ValidationResult | None = None,
    ) -> ErrorCategory:
        """Classify an error into a category for recovery action.

        Args:
            error_message: The error message to classify.
            result: Optional conversion result for additional context.
            validation: Optional validation result.

        Returns:
            The classified error category.
        """
        if not error_message:
            if result and not result.success:
                error_message = result.error_message or ""
            else:
                return ErrorCategory.UNKNOWN_ERROR

        msg_lower = error_message.lower()

        # Input errors
        if any(
            phrase in msg_lower
            for phrase in [
                "no such file",
                "not found",
                "does not exist",
                "invalid input",
                "unsupported",
                "corrupt",
                "cannot open",
            ]
        ):
            return ErrorCategory.INPUT_ERROR

        # Permission errors
        if any(
            phrase in msg_lower
            for phrase in [
                "permission denied",
                "access denied",
                "not permitted",
                "read-only",
            ]
        ):
            return ErrorCategory.PERMISSION_ERROR

        # Disk space errors
        if any(
            phrase in msg_lower
            for phrase in [
                "no space",
                "disk full",
                "not enough space",
                "insufficient storage",
                "quota exceeded",
            ]
        ):
            return ErrorCategory.DISK_SPACE_ERROR

        # Encoding errors
        if any(
            phrase in msg_lower
            for phrase in [
                "encoder",
                "encoding",
                "videotoolbox",
                "hevc",
                "h265",
                "libx265",
                "ffmpeg",
                "conversion failed",
            ]
        ):
            return ErrorCategory.ENCODING_ERROR

        # Validation errors
        if validation and not validation.valid:
            return ErrorCategory.VALIDATION_ERROR

        if any(
            phrase in msg_lower
            for phrase in [
                "validation",
                "integrity",
                "verify",
                "corrupt output",
                "invalid output",
            ]
        ):
            return ErrorCategory.VALIDATION_ERROR

        # Metadata errors
        if any(
            phrase in msg_lower
            for phrase in [
                "metadata",
                "exiftool",
                "timestamp",
                "gps",
                "exif",
            ]
        ):
            return ErrorCategory.METADATA_ERROR

        return ErrorCategory.UNKNOWN_ERROR

    def get_recovery_action(self, category: ErrorCategory) -> RecoveryAction:
        """Get the recommended recovery action for an error category.

        Args:
            category: The error category.

        Returns:
            The recommended recovery action.
        """
        return ERROR_RECOVERY_MAPPING.get(category, RecoveryAction.SKIP)

    def cleanup_partial_output(self, output_path: Path) -> bool:
        """Clean up a partial or failed output file.

        Args:
            output_path: Path to the output file to clean up.

        Returns:
            True if file was removed, False otherwise.
        """
        if not output_path.exists():
            return False

        try:
            output_path.unlink()
            logger.info(f"Cleaned up partial output: {output_path}")
            return True
        except OSError as e:
            logger.warning(f"Failed to clean up partial output {output_path}: {e}")
            return False

    def handle_failure(
        self,
        input_path: Path,
        output_path: Path,
        category: ErrorCategory,
        error_message: str,
        move_to_failed: bool = True,
    ) -> FailureRecord:
        """Handle a conversion failure with proper cleanup and tracking.

        This method:
        1. Cleans up any partial output file
        2. Logs detailed error information
        3. Optionally moves the failed input to a dedicated directory
        4. Records the failure for potential retry

        Args:
            input_path: Path to the input file that failed.
            output_path: Path to the (partial) output file.
            category: Classified error category.
            error_message: Detailed error message.
            move_to_failed: Whether to move the file to failed directory.

        Returns:
            FailureRecord documenting this failure.
        """
        # Clean up partial output
        self.cleanup_partial_output(output_path)

        # Determine if this error can be retried
        can_retry = category in (
            ErrorCategory.ENCODING_ERROR,
            ErrorCategory.VALIDATION_ERROR,
            ErrorCategory.DISK_SPACE_ERROR,
        )

        # Create failure record
        record = FailureRecord(
            input_path=input_path,
            output_path=output_path,
            error_category=category,
            error_message=error_message,
            can_retry=can_retry,
        )

        # Log detailed error information
        self._log_failure(record)

        # Move to failed directory if configured
        if move_to_failed and self.failed_dir and input_path.exists():
            moved_path = self._move_to_failed_dir(input_path)
            if moved_path:
                record.moved_to = moved_path

        self._failure_records.append(record)
        return record

    def _log_failure(self, record: FailureRecord) -> None:
        """Log detailed failure information.

        Args:
            record: The failure record to log.
        """
        action = self.get_recovery_action(record.error_category)

        logger.error(
            "Conversion failed:\n"
            f"  File: {record.input_path.name}\n"
            f"  Path: {record.input_path}\n"
            f"  Category: {record.error_category.value}\n"
            f"  Recovery: {action.value}\n"
            f"  Can Retry: {record.can_retry}\n"
            f"  Error: {record.error_message}"
        )

    def _move_to_failed_dir(self, input_path: Path) -> Path | None:
        """Move a failed file to the failed directory.

        Args:
            input_path: Path to the file to move.

        Returns:
            New path if moved successfully, None otherwise.
        """
        if not self.failed_dir:
            return None

        try:
            self.failed_dir.mkdir(parents=True, exist_ok=True)
            dest = self.failed_dir / input_path.name

            # Handle name collision
            if dest.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dest = self.failed_dir / f"{input_path.stem}_{timestamp}{input_path.suffix}"

            shutil.move(str(input_path), str(dest))
            logger.info(f"Moved failed file to: {dest}")
            return dest
        except OSError as e:
            logger.warning(f"Could not move failed file {input_path}: {e}")
            return None

    def check_disk_space(self, path: Path) -> DiskSpaceInfo:
        """Check available disk space at a path.

        Args:
            path: Path to check disk space for.

        Returns:
            DiskSpaceInfo with space details.
        """
        check_path = path if path.is_dir() else path.parent
        if not check_path.exists():
            check_path = Path.home()

        try:
            stat = os.statvfs(check_path)
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bavail * stat.f_frsize
            used = total - free

            return DiskSpaceInfo(
                path=check_path,
                total_bytes=total,
                free_bytes=free,
                used_bytes=used,
            )
        except OSError as e:
            logger.warning(f"Could not check disk space for {check_path}: {e}")
            return DiskSpaceInfo(
                path=check_path,
                total_bytes=0,
                free_bytes=0,
                used_bytes=0,
            )

    def has_sufficient_space(
        self,
        path: Path,
        required_bytes: int | None = None,
    ) -> tuple[bool, DiskSpaceInfo]:
        """Check if there is sufficient disk space.

        Args:
            path: Path to check.
            required_bytes: Required bytes. Uses min_free_space if None.

        Returns:
            Tuple of (has_sufficient_space, disk_info).
        """
        required = required_bytes or self.min_free_space
        info = self.check_disk_space(path)

        sufficient = info.free_bytes >= required

        if not sufficient:
            logger.warning(
                f"Insufficient disk space at {info.path}: "
                f"{info.free_bytes / 1024 / 1024:.1f} MB free, "
                f"{required / 1024 / 1024:.1f} MB required"
            )

        return sufficient, info

    def get_retryable_failures(self) -> list[FailureRecord]:
        """Get list of failures that can be retried.

        Returns:
            List of retryable failure records.
        """
        return [r for r in self._failure_records if r.can_retry]

    def prepare_retry(self, record: FailureRecord) -> Path | None:
        """Prepare a failed conversion for retry.

        If the file was moved to the failed directory, this will
        move it back to its original location.

        Args:
            record: The failure record to prepare for retry.

        Returns:
            Path to the file ready for retry, or None if not possible.
        """
        record.retry_count += 1

        # If file was moved, move it back
        if record.moved_to and record.moved_to.exists():
            try:
                # Move back to original location
                shutil.move(str(record.moved_to), str(record.input_path))
                record.moved_to = None
                logger.info(f"Restored file for retry: {record.input_path}")
                return record.input_path
            except OSError as e:
                logger.error(f"Failed to restore file for retry: {e}")
                return None

        # Check if original file still exists
        if record.input_path.exists():
            return record.input_path

        return None

    def mark_retry_success(self, record: FailureRecord) -> None:
        """Mark a retry as successful and remove from failure records.

        Args:
            record: The failure record that succeeded on retry.
        """
        if record in self._failure_records:
            self._failure_records.remove(record)
            logger.info(
                f"Retry succeeded for {record.input_path.name} "
                f"after {record.retry_count} attempt(s)"
            )

    def clear_failures(self) -> int:
        """Clear all failure records.

        Returns:
            Number of records cleared.
        """
        count = len(self._failure_records)
        self._failure_records.clear()
        return count

    def get_failure_summary(self) -> dict:
        """Get summary of all recorded failures.

        Returns:
            Dictionary with failure statistics by category.
        """
        summary: dict[str, int] = {}
        for record in self._failure_records:
            category = record.error_category.value
            summary[category] = summary.get(category, 0) + 1

        return {
            "total_failures": len(self._failure_records),
            "retryable": len(self.get_retryable_failures()),
            "by_category": summary,
        }


__all__ = [
    "ErrorRecoveryManager",
    "FailureRecord",
    "DiskSpaceInfo",
    "ERROR_RECOVERY_MAPPING",
    "DEFAULT_MIN_FREE_SPACE",
]
