"""File timestamp synchronization for video conversion.

This module provides functionality to synchronize filesystem timestamps
(creation date, modification date) between original and converted video files.
This ensures converted videos appear in the correct chronological order
when sorted by date in macOS Finder.

SDS Reference: SDS-P01-004
SRS Reference: SRS-403 (Timestamp Preservation)

Example:
    >>> from video_converter.processors.timestamp import TimestampSynchronizer
    >>> synchronizer = TimestampSynchronizer()
    >>> # Copy all timestamps from original to converted
    >>> result = synchronizer.sync_from_file(
    ...     source=Path("original.mov"),
    ...     dest=Path("converted.mp4"),
    ... )
    >>> if result.success:
    ...     print("Timestamps synchronized successfully")

    >>> # Verify timestamps were preserved
    >>> verification = synchronizer.verify(
    ...     original=Path("original.mov"),
    ...     converted=Path("converted.mp4"),
    ... )
    >>> print(f"Passed: {verification.passed}")
"""

from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from video_converter.core.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

# Tolerance for timestamp comparison (in seconds)
TIMESTAMP_TOLERANCE_SECONDS = 2.0


class TimestampError(Exception):
    """Base exception for timestamp operations.

    Attributes:
        path: The path where the error occurred.
        reason: Description of the error.
    """

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Timestamp error for {path}: {reason}")


class TimestampSyncError(TimestampError):
    """Raised when timestamp synchronization fails."""

    pass


class TimestampReadError(TimestampError):
    """Raised when reading timestamps fails."""

    pass


@dataclass
class FileTimestamps:
    """Container for file timestamp information.

    Attributes:
        path: Path to the file.
        birth_time: File creation time (macOS-specific, may be None on other OS).
        modification_time: Last modification time.
        access_time: Last access time.
        metadata_change_time: Last metadata change time (read-only on most systems).

    Example:
        >>> timestamps = FileTimestamps.from_file(Path("video.mp4"))
        >>> print(f"Created: {timestamps.birth_time}")
        >>> print(f"Modified: {timestamps.modification_time}")
    """

    path: Path
    birth_time: datetime | None = None
    modification_time: datetime | None = None
    access_time: datetime | None = None
    metadata_change_time: datetime | None = None

    @classmethod
    def from_file(cls, path: Path) -> FileTimestamps:
        """Extract timestamps from a file.

        Args:
            path: Path to the file.

        Returns:
            FileTimestamps with all available timestamp information.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            TimestampReadError: If reading timestamps fails.
        """
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        try:
            stat = path.stat()

            # Get modification and access times (always available)
            mtime = datetime.fromtimestamp(stat.st_mtime)
            atime = datetime.fromtimestamp(stat.st_atime)
            ctime = datetime.fromtimestamp(stat.st_ctime)

            # Get birth time (macOS-specific)
            birth_time = None
            if hasattr(stat, "st_birthtime"):
                birth_time = datetime.fromtimestamp(stat.st_birthtime)

            return cls(
                path=path,
                birth_time=birth_time,
                modification_time=mtime,
                access_time=atime,
                metadata_change_time=ctime,
            )
        except OSError as e:
            raise TimestampReadError(path, str(e)) from e

    def __str__(self) -> str:
        """Return human-readable timestamp information."""
        lines = [f"Timestamps for {self.path.name}:"]
        if self.birth_time:
            lines.append(f"  Created:  {self.birth_time.isoformat()}")
        if self.modification_time:
            lines.append(f"  Modified: {self.modification_time.isoformat()}")
        if self.access_time:
            lines.append(f"  Accessed: {self.access_time.isoformat()}")
        return "\n".join(lines)


@dataclass
class TimestampSyncResult:
    """Result of a timestamp synchronization operation.

    Attributes:
        success: Whether synchronization completed successfully.
        source: Source file path.
        dest: Destination file path.
        birth_time_synced: Whether birth time was synchronized.
        modification_time_synced: Whether modification time was synchronized.
        access_time_synced: Whether access time was synchronized.
        error_message: Error message if synchronization failed.
        warnings: Non-critical issues encountered.

    Example:
        >>> result = synchronizer.sync_from_file(source, dest)
        >>> if result.success:
        ...     print("All timestamps synced")
        >>> else:
        ...     print(f"Error: {result.error_message}")
    """

    success: bool
    source: Path
    dest: Path
    birth_time_synced: bool = False
    modification_time_synced: bool = False
    access_time_synced: bool = False
    error_message: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class TimestampVerificationResult:
    """Result of timestamp verification between two files.

    Attributes:
        passed: Whether timestamps match within tolerance.
        original: Timestamps from original file.
        converted: Timestamps from converted file.
        birth_time_match: Whether birth times match.
        modification_time_match: Whether modification times match.
        tolerance_seconds: Tolerance used for comparison.
        details: Additional verification details.

    Example:
        >>> result = synchronizer.verify(original, converted)
        >>> if result.passed:
        ...     print("Timestamps preserved correctly")
        >>> else:
        ...     print(result.details)
    """

    passed: bool
    original: FileTimestamps | None = None
    converted: FileTimestamps | None = None
    birth_time_match: bool = False
    modification_time_match: bool = False
    tolerance_seconds: float = TIMESTAMP_TOLERANCE_SECONDS
    details: str = ""


class TimestampSynchronizer:
    """Synchronize filesystem timestamps between video files.

    This class handles copying timestamps from original files to converted
    files, ensuring that Finder sorting by date works correctly. It supports
    macOS-specific features like birth time (creation date).

    Attributes:
        is_macos: Whether running on macOS.

    Example:
        >>> synchronizer = TimestampSynchronizer()
        >>> # Sync from original file
        >>> result = synchronizer.sync_from_file(
        ...     source=Path("original.mov"),
        ...     dest=Path("converted.mp4"),
        ... )
        >>> # Or sync from specific datetime
        >>> result = synchronizer.sync_from_datetime(
        ...     path=Path("converted.mp4"),
        ...     creation_date=datetime(2023, 1, 15, 10, 30, 0),
        ... )
    """

    def __init__(self) -> None:
        """Initialize TimestampSynchronizer."""
        self.is_macos = platform.system() == "Darwin"
        logger.debug("TimestampSynchronizer initialized (macOS: %s)", self.is_macos)

    def sync_from_file(
        self,
        source: Path,
        dest: Path,
        *,
        sync_birth_time: bool = True,
        sync_modification_time: bool = True,
        sync_access_time: bool = True,
    ) -> TimestampSyncResult:
        """Copy timestamps from source file to destination file.

        Copies creation date, modification date, and access time from the
        source file to the destination file.

        Args:
            source: Source file to copy timestamps from.
            dest: Destination file to apply timestamps to.
            sync_birth_time: Whether to sync birth time (creation date).
            sync_modification_time: Whether to sync modification time.
            sync_access_time: Whether to sync access time.

        Returns:
            TimestampSyncResult with details of the synchronization.

        Example:
            >>> result = synchronizer.sync_from_file(
            ...     source=Path("original.mov"),
            ...     dest=Path("converted.mp4"),
            ... )
            >>> print(f"Success: {result.success}")
        """
        logger.debug("Syncing timestamps from %s to %s", source, dest)

        # Validate files exist
        if not source.exists():
            return TimestampSyncResult(
                success=False,
                source=source,
                dest=dest,
                error_message=f"Source file not found: {source}",
            )

        if not dest.exists():
            return TimestampSyncResult(
                success=False,
                source=source,
                dest=dest,
                error_message=f"Destination file not found: {dest}",
            )

        try:
            # Get source timestamps
            source_timestamps = FileTimestamps.from_file(source)
        except TimestampReadError as e:
            return TimestampSyncResult(
                success=False,
                source=source,
                dest=dest,
                error_message=f"Failed to read source timestamps: {e.reason}",
            )

        warnings: list[str] = []
        birth_synced = False
        mtime_synced = False
        atime_synced = False

        # Sync modification and access times using os.utime
        if sync_modification_time or sync_access_time:
            try:
                stat = source.stat()
                atime = stat.st_atime if sync_access_time else dest.stat().st_atime
                mtime = stat.st_mtime if sync_modification_time else dest.stat().st_mtime
                os.utime(dest, (atime, mtime))
                mtime_synced = sync_modification_time
                atime_synced = sync_access_time
                logger.debug("Set mtime/atime on %s", dest)
            except OSError as e:
                warnings.append(f"Failed to set modification/access time: {e}")
                logger.warning("Failed to set mtime/atime on %s: %s", dest, e)

        # Sync birth time (macOS-specific)
        if sync_birth_time and source_timestamps.birth_time:
            birth_synced = self._set_birth_time(dest, source_timestamps.birth_time, warnings)

        success = (
            (not sync_modification_time or mtime_synced)
            and (not sync_access_time or atime_synced)
            and (not sync_birth_time or birth_synced or not self.is_macos)
        )

        result = TimestampSyncResult(
            success=success,
            source=source,
            dest=dest,
            birth_time_synced=birth_synced,
            modification_time_synced=mtime_synced,
            access_time_synced=atime_synced,
            warnings=warnings,
        )

        if success:
            logger.info("Timestamps synchronized: %s -> %s", source.name, dest.name)
        else:
            logger.warning(
                "Timestamp sync incomplete: %s -> %s (warnings: %s)",
                source.name,
                dest.name,
                warnings,
            )

        return result

    def sync_from_datetime(
        self,
        path: Path,
        creation_date: datetime | None = None,
        modification_date: datetime | None = None,
        access_date: datetime | None = None,
    ) -> TimestampSyncResult:
        """Set file timestamps from datetime values.

        Allows setting specific timestamps on a file without a source file.

        Args:
            path: Path to the file to modify.
            creation_date: Creation date to set (macOS only).
            modification_date: Modification date to set.
            access_date: Access date to set.

        Returns:
            TimestampSyncResult with details of the synchronization.

        Example:
            >>> from datetime import datetime
            >>> result = synchronizer.sync_from_datetime(
            ...     path=Path("video.mp4"),
            ...     creation_date=datetime(2023, 1, 15, 10, 30, 0),
            ...     modification_date=datetime(2023, 1, 15, 10, 30, 0),
            ... )
        """
        logger.debug("Setting timestamps on %s from datetime values", path)

        if not path.exists():
            return TimestampSyncResult(
                success=False,
                source=path,
                dest=path,
                error_message=f"File not found: {path}",
            )

        warnings: list[str] = []
        birth_synced = False
        mtime_synced = False
        atime_synced = False

        # Set modification and access times
        if modification_date or access_date:
            try:
                current_stat = path.stat()
                atime = access_date.timestamp() if access_date else current_stat.st_atime
                mtime = (
                    modification_date.timestamp() if modification_date else current_stat.st_mtime
                )
                os.utime(path, (atime, mtime))
                mtime_synced = modification_date is not None
                atime_synced = access_date is not None
                logger.debug("Set mtime/atime on %s", path)
            except OSError as e:
                warnings.append(f"Failed to set modification/access time: {e}")

        # Set birth time (macOS-specific)
        if creation_date:
            birth_synced = self._set_birth_time(path, creation_date, warnings)

        success = not warnings or (mtime_synced or atime_synced or birth_synced)

        return TimestampSyncResult(
            success=success,
            source=path,
            dest=path,
            birth_time_synced=birth_synced,
            modification_time_synced=mtime_synced,
            access_time_synced=atime_synced,
            warnings=warnings,
        )

    def _set_birth_time(
        self,
        path: Path,
        birth_time: datetime,
        warnings: list[str],
    ) -> bool:
        """Set the birth time (creation date) on a file.

        On macOS, uses SetFile command or touch with -t flag.

        Args:
            path: Path to the file.
            birth_time: Birth time to set.
            warnings: List to append warnings to.

        Returns:
            True if birth time was set successfully.
        """
        if not self.is_macos:
            warnings.append("Birth time setting is only supported on macOS")
            return False

        # Try using SetFile (requires Xcode Command Line Tools)
        try:
            # SetFile uses MM/DD/YYYY HH:MM:SS format
            date_str = birth_time.strftime("%m/%d/%Y %H:%M:%S")
            result = subprocess.run(
                ["SetFile", "-d", date_str, str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                logger.debug("Set birth time using SetFile: %s", path)
                return True
            else:
                logger.debug("SetFile failed: %s", result.stderr)
        except FileNotFoundError:
            logger.debug("SetFile not found, trying touch")

        # Fallback: try using touch with -t flag (sets both mtime and creates file)
        # Note: touch can't directly set birth time, but we try anyway
        try:
            # touch uses [[CC]YY]MMDDhhmm[.SS] format
            date_str = birth_time.strftime("%Y%m%d%H%M.%S")
            result = subprocess.run(
                ["touch", "-t", date_str, str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                # touch doesn't set birth time, but at least we set mtime
                logger.debug("Used touch to set timestamp: %s", path)
                warnings.append("Used touch instead of SetFile - birth time may not be preserved")
                return False
        except FileNotFoundError:
            pass

        warnings.append("Failed to set birth time - SetFile command not available")
        return False

    def get_timestamps(self, path: Path) -> FileTimestamps:
        """Get all timestamps from a file.

        Args:
            path: Path to the file.

        Returns:
            FileTimestamps with all available timestamp information.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            TimestampReadError: If reading timestamps fails.
        """
        return FileTimestamps.from_file(path)

    def verify(
        self,
        original: Path,
        converted: Path,
        *,
        tolerance_seconds: float = TIMESTAMP_TOLERANCE_SECONDS,
        check_birth_time: bool = True,
        check_modification_time: bool = True,
    ) -> TimestampVerificationResult:
        """Verify timestamps were preserved during conversion.

        Compares timestamps between original and converted files to ensure
        they match within the specified tolerance.

        Args:
            original: Original source file.
            converted: Converted output file.
            tolerance_seconds: Maximum allowed difference in seconds.
            check_birth_time: Whether to check birth time match.
            check_modification_time: Whether to check modification time match.

        Returns:
            TimestampVerificationResult with detailed comparison.

        Raises:
            FileNotFoundError: If either file doesn't exist.

        Example:
            >>> result = synchronizer.verify(
            ...     original=Path("original.mov"),
            ...     converted=Path("converted.mp4"),
            ... )
            >>> if result.passed:
            ...     print("Timestamps preserved correctly")
        """
        if not original.exists():
            raise FileNotFoundError(f"Original file not found: {original}")
        if not converted.exists():
            raise FileNotFoundError(f"Converted file not found: {converted}")

        try:
            orig_timestamps = FileTimestamps.from_file(original)
        except TimestampReadError as e:
            return TimestampVerificationResult(
                passed=False,
                tolerance_seconds=tolerance_seconds,
                details=f"Failed to read original timestamps: {e.reason}",
            )

        try:
            conv_timestamps = FileTimestamps.from_file(converted)
        except TimestampReadError as e:
            return TimestampVerificationResult(
                passed=False,
                original=orig_timestamps,
                tolerance_seconds=tolerance_seconds,
                details=f"Failed to read converted timestamps: {e.reason}",
            )

        birth_match = True
        mtime_match = True
        details_parts: list[str] = []

        # Check birth time
        if check_birth_time and orig_timestamps.birth_time:
            if conv_timestamps.birth_time:
                diff = abs(
                    (orig_timestamps.birth_time - conv_timestamps.birth_time).total_seconds()
                )
                birth_match = diff <= tolerance_seconds
                if birth_match:
                    details_parts.append(f"Birth time match (diff: {diff:.2f}s)")
                else:
                    details_parts.append(
                        f"Birth time mismatch: {orig_timestamps.birth_time} vs "
                        f"{conv_timestamps.birth_time} (diff: {diff:.2f}s)"
                    )
            else:
                birth_match = False
                details_parts.append("Birth time missing in converted file")

        # Check modification time
        if check_modification_time:
            if orig_timestamps.modification_time and conv_timestamps.modification_time:
                diff = abs(
                    (
                        orig_timestamps.modification_time - conv_timestamps.modification_time
                    ).total_seconds()
                )
                mtime_match = diff <= tolerance_seconds
                if mtime_match:
                    details_parts.append(f"Modification time match (diff: {diff:.2f}s)")
                else:
                    details_parts.append(
                        f"Modification time mismatch: {orig_timestamps.modification_time} "
                        f"vs {conv_timestamps.modification_time} (diff: {diff:.2f}s)"
                    )
            elif orig_timestamps.modification_time:
                mtime_match = False
                details_parts.append("Modification time missing in converted file")

        passed = (not check_birth_time or birth_match or not self.is_macos) and (
            not check_modification_time or mtime_match
        )

        return TimestampVerificationResult(
            passed=passed,
            original=orig_timestamps,
            converted=conv_timestamps,
            birth_time_match=birth_match,
            modification_time_match=mtime_match,
            tolerance_seconds=tolerance_seconds,
            details="; ".join(details_parts) if details_parts else "All checks passed",
        )


__all__ = [
    # Exceptions
    "TimestampError",
    "TimestampSyncError",
    "TimestampReadError",
    # Data classes
    "FileTimestamps",
    "TimestampSyncResult",
    "TimestampVerificationResult",
    # Main class
    "TimestampSynchronizer",
    # Constants
    "TIMESTAMP_TOLERANCE_SECONDS",
]
