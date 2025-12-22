"""Conversion history tracking for duplicate prevention.

This module implements a conversion history tracking system to prevent
re-converting videos that have already been processed. It uses file hashes
or Photos UUIDs to identify videos across renames and moves.

SDS Reference: SDS-C01-003
SRS Reference: SRS-306 (Conversion History)

Example:
    >>> from video_converter.core.history import ConversionHistory, ConversionRecord
    >>> from pathlib import Path
    >>> from datetime import datetime
    >>>
    >>> history = ConversionHistory()
    >>>
    >>> # Check before converting
    >>> if not history.is_converted(video_uuid):
    ...     # Perform conversion...
    ...     record = ConversionRecord(
    ...         id=video_uuid,
    ...         source_path=str(source),
    ...         output_path=str(output),
    ...         source_codec="h264",
    ...         output_codec="hevc",
    ...         source_size=original_size,
    ...         output_size=converted_size,
    ...         converted_at=datetime.now().isoformat(),
    ...         success=True,
    ...     )
    ...     history.add_record(record)
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING


class StatsPeriod(Enum):
    """Time period for statistics filtering."""

    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    ALL = "all"

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Default path for history storage
DEFAULT_HISTORY_DIR = Path.home() / ".local" / "share" / "video_converter"
DEFAULT_HISTORY_FILE = DEFAULT_HISTORY_DIR / "history.json"


class HistoryError(Exception):
    """Base exception for history operations."""

    pass


class HistoryCorruptedError(HistoryError):
    """Raised when history data is corrupted or invalid."""

    pass


@dataclass
class ConversionRecord:
    """Record of a video conversion.

    Stores all relevant information about a single video conversion,
    including paths, codecs, sizes, and success status.

    Attributes:
        id: Unique identifier (UUID from Photos or file hash).
        source_path: Original file path at time of conversion.
        output_path: Converted file path (None if failed).
        source_codec: Original video codec (e.g., "h264").
        output_codec: Target video codec (e.g., "hevc").
        source_size: Original file size in bytes.
        output_size: Converted file size in bytes (None if failed).
        converted_at: ISO format timestamp of conversion.
        success: Whether conversion completed successfully.
        error_message: Error details if conversion failed.
    """

    id: str
    source_path: str
    output_path: str | None
    source_codec: str
    output_codec: str
    source_size: int
    output_size: int | None
    converted_at: str
    success: bool
    error_message: str | None = None

    def to_dict(self) -> dict:
        """Convert record to JSON-serializable dictionary.

        Returns:
            Dictionary representation of the record.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ConversionRecord:
        """Create a ConversionRecord from dictionary.

        Args:
            data: Dictionary containing record data.

        Returns:
            A new ConversionRecord instance.

        Raises:
            KeyError: If required fields are missing.
        """
        return cls(
            id=data["id"],
            source_path=data["source_path"],
            output_path=data.get("output_path"),
            source_codec=data["source_codec"],
            output_codec=data["output_codec"],
            source_size=data["source_size"],
            output_size=data.get("output_size"),
            converted_at=data["converted_at"],
            success=data["success"],
            error_message=data.get("error_message"),
        )

    @property
    def size_saved(self) -> int:
        """Calculate bytes saved by conversion.

        Returns:
            Bytes saved (0 if conversion failed or increased size).
        """
        if not self.success or self.output_size is None:
            return 0
        return max(0, self.source_size - self.output_size)

    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio.

        Returns:
            Compression ratio (0.0-1.0) where 0.6 means 60% size reduction.
            Returns 0.0 if conversion failed or source size is 0.
        """
        if not self.success or self.output_size is None or self.source_size <= 0:
            return 0.0
        return 1.0 - (self.output_size / self.source_size)


@dataclass
class HistoryStatistics:
    """Statistics summary for conversion history.

    Attributes:
        total_converted: Number of successfully converted videos.
        total_failed: Number of failed conversions.
        total_source_bytes: Sum of all original file sizes.
        total_output_bytes: Sum of all converted file sizes.
        total_saved_bytes: Total bytes saved by compression.
        first_conversion: Timestamp of earliest conversion.
        last_conversion: Timestamp of most recent conversion.
        period: The time period these statistics cover.
        period_start: Start timestamp of the period.
        total_duration_seconds: Total conversion time in seconds.
    """

    total_converted: int = 0
    total_failed: int = 0
    total_source_bytes: int = 0
    total_output_bytes: int = 0
    total_saved_bytes: int = 0
    first_conversion: str | None = None
    last_conversion: str | None = None
    period: str = "all"
    period_start: str | None = None
    total_duration_seconds: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate.

        Returns:
            Success rate as a fraction (0.0-1.0).
        """
        total = self.total_converted + self.total_failed
        if total == 0:
            return 0.0
        return self.total_converted / total

    @property
    def average_compression_ratio(self) -> float:
        """Calculate average compression ratio.

        Returns:
            Average compression ratio (0.0-1.0).
        """
        if self.total_source_bytes <= 0:
            return 0.0
        return 1.0 - (self.total_output_bytes / self.total_source_bytes)

    @property
    def storage_saved_percent(self) -> float:
        """Calculate storage saved percentage.

        Returns:
            Percentage of storage saved (0.0-100.0).
        """
        if self.total_source_bytes <= 0:
            return 0.0
        return (self.total_saved_bytes / self.total_source_bytes) * 100

    def to_dict(self) -> dict:
        """Convert statistics to dictionary.

        Returns:
            Dictionary representation of statistics.
        """
        return {
            "period": self.period,
            "period_start": self.period_start,
            "total_converted": self.total_converted,
            "total_failed": self.total_failed,
            "total_source_bytes": self.total_source_bytes,
            "total_output_bytes": self.total_output_bytes,
            "total_saved_bytes": self.total_saved_bytes,
            "storage_saved_percent": self.storage_saved_percent,
            "first_conversion": self.first_conversion,
            "last_conversion": self.last_conversion,
            "success_rate": self.success_rate,
            "average_compression_ratio": self.average_compression_ratio,
            "total_duration_seconds": self.total_duration_seconds,
        }


class ConversionHistory:
    """Manage conversion history for duplicate prevention.

    Provides functionality to:
    - Track converted videos by unique identifier
    - Store conversion metadata (date, result, output path)
    - Support Photos UUID and file hash identification
    - Persist history across application restarts
    - Generate statistics and reports

    Thread-safe for concurrent access.

    Attributes:
        history_path: Path to the history JSON file.

    Example:
        >>> history = ConversionHistory()
        >>>
        >>> # Check if already converted
        >>> if history.is_converted(video_id):
        ...     print("Already converted, skipping")
        ...
        >>> # Add conversion record
        >>> record = ConversionRecord(...)
        >>> history.add_record(record)
        >>>
        >>> # Get statistics
        >>> stats = history.get_statistics()
        >>> print(f"Converted: {stats.total_converted} videos")
    """

    def __init__(self, history_path: Path | None = None) -> None:
        """Initialize the conversion history manager.

        Args:
            history_path: Path to history file.
                         Defaults to ~/.local/share/video_converter/history.json
        """
        self.history_path = history_path or DEFAULT_HISTORY_FILE
        self._records: dict[str, ConversionRecord] = {}
        self._lock = threading.RLock()  # RLock for reentrant locking
        self._dirty = False

        # Ensure directory exists
        self.history_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing history
        self._load()

    def _load(self) -> None:
        """Load history from file.

        Raises:
            HistoryCorruptedError: If history file is invalid JSON.
        """
        if not self.history_path.exists():
            logger.debug("No existing history file found")
            return

        try:
            with open(self.history_path, encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                msg = "History file must contain a JSON object"
                raise HistoryCorruptedError(msg)

            records_data = data.get("records", {})
            if not isinstance(records_data, dict):
                msg = "Records must be a JSON object"
                raise HistoryCorruptedError(msg)

            for key, record_data in records_data.items():
                try:
                    self._records[key] = ConversionRecord.from_dict(record_data)
                except KeyError as e:
                    logger.warning(f"Skipping invalid record {key}: missing {e}")
                    continue

            logger.info(f"Loaded {len(self._records)} records from history")

        except json.JSONDecodeError as e:
            msg = f"Invalid JSON in history file: {e}"
            raise HistoryCorruptedError(msg) from e

    def _save(self) -> None:
        """Save history to file."""
        try:
            data = {
                "version": "1.0.0",
                "updated_at": datetime.now().isoformat(),
                "records": {k: v.to_dict() for k, v in self._records.items()},
            }

            # Write to temp file first, then rename for atomic update
            temp_path = self.history_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")

            temp_path.replace(self.history_path)
            self._dirty = False
            logger.debug(f"Saved {len(self._records)} records to history")

        except OSError as e:
            logger.error(f"Failed to save history: {e}")

    def is_converted(self, identifier: str) -> bool:
        """Check if a video has been successfully converted.

        Args:
            identifier: UUID (from Photos) or file hash.

        Returns:
            True if video was successfully converted before.
        """
        with self._lock:
            record = self._records.get(identifier)
            return record is not None and record.success

    def add_record(self, record: ConversionRecord) -> None:
        """Add or update a conversion record.

        Args:
            record: The conversion record to add.
        """
        with self._lock:
            self._records[record.id] = record
            self._dirty = True
            self._save()

        logger.debug(f"Added record for {record.id}")

    def get_record(self, identifier: str) -> ConversionRecord | None:
        """Get a conversion record by identifier.

        Args:
            identifier: UUID or file hash.

        Returns:
            The ConversionRecord if found, None otherwise.
        """
        with self._lock:
            return self._records.get(identifier)

    def remove_record(self, identifier: str) -> bool:
        """Remove a record from history.

        Args:
            identifier: UUID or file hash.

        Returns:
            True if record was removed, False if not found.
        """
        with self._lock:
            if identifier in self._records:
                del self._records[identifier]
                self._dirty = True
                self._save()
                logger.debug(f"Removed record for {identifier}")
                return True
            return False

    def clear(self) -> None:
        """Clear all history records."""
        with self._lock:
            count = len(self._records)
            self._records.clear()
            self._dirty = True
            self._save()

        logger.info(f"Cleared {count} records from history")

    def _get_period_start(self, period: StatsPeriod) -> datetime | None:
        """Get the start datetime for a given period.

        Args:
            period: The time period to calculate start for.

        Returns:
            The start datetime or None for ALL period.
        """
        now = datetime.now()
        if period == StatsPeriod.TODAY:
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == StatsPeriod.WEEK:
            start_of_week = now - timedelta(days=now.weekday())
            return start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == StatsPeriod.MONTH:
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return None

    def _filter_records_by_period(
        self,
        records: list[ConversionRecord],
        period: StatsPeriod,
    ) -> list[ConversionRecord]:
        """Filter records by time period.

        Args:
            records: List of records to filter.
            period: Time period to filter by.

        Returns:
            Filtered list of records.
        """
        if period == StatsPeriod.ALL:
            return records

        period_start = self._get_period_start(period)
        if period_start is None:
            return records

        filtered = []
        for record in records:
            if record.converted_at:
                try:
                    record_time = datetime.fromisoformat(record.converted_at)
                    if record_time >= period_start:
                        filtered.append(record)
                except ValueError:
                    continue
        return filtered

    def get_records_by_period(
        self,
        period: StatsPeriod = StatsPeriod.ALL,
    ) -> list[ConversionRecord]:
        """Get all conversion records filtered by time period.

        Args:
            period: Time period to filter by.

        Returns:
            List of ConversionRecord instances within the period.
        """
        with self._lock:
            all_records = list(self._records.values())
            return self._filter_records_by_period(all_records, period)

    def get_statistics(
        self,
        period: StatsPeriod = StatsPeriod.ALL,
    ) -> HistoryStatistics:
        """Get aggregated statistics for conversions.

        Args:
            period: Time period to filter statistics by.

        Returns:
            HistoryStatistics with totals and averages.
        """
        with self._lock:
            stats = HistoryStatistics()
            stats.period = period.value

            # Calculate period start
            period_start = self._get_period_start(period)
            if period_start:
                stats.period_start = period_start.isoformat()

            # Filter records by period
            all_records = list(self._records.values())
            filtered_records = self._filter_records_by_period(all_records, period)

            successful = [r for r in filtered_records if r.success]
            failed = [r for r in filtered_records if not r.success]

            stats.total_converted = len(successful)
            stats.total_failed = len(failed)

            for record in successful:
                stats.total_source_bytes += record.source_size
                if record.output_size is not None:
                    stats.total_output_bytes += record.output_size

            stats.total_saved_bytes = (
                stats.total_source_bytes - stats.total_output_bytes
            )

            # Find first and last conversion times within period
            timestamps = [r.converted_at for r in successful if r.converted_at]
            if timestamps:
                stats.first_conversion = min(timestamps)
                stats.last_conversion = max(timestamps)

            return stats

    def get_all_records(self) -> list[ConversionRecord]:
        """Get all conversion records.

        Returns:
            List of all ConversionRecord instances.
        """
        with self._lock:
            return list(self._records.values())

    def get_failed_records(self) -> list[ConversionRecord]:
        """Get all failed conversion records.

        Returns:
            List of failed ConversionRecord instances.
        """
        with self._lock:
            return [r for r in self._records.values() if not r.success]

    def get_successful_records(self) -> list[ConversionRecord]:
        """Get all successful conversion records.

        Returns:
            List of successful ConversionRecord instances.
        """
        with self._lock:
            return [r for r in self._records.values() if r.success]

    def count(self) -> int:
        """Get total number of records.

        Returns:
            Number of records in history.
        """
        with self._lock:
            return len(self._records)

    def export_to_json(self, path: Path) -> None:
        """Export history to a JSON file.

        Args:
            path: Path to export file.
        """
        with self._lock:
            data = {
                "exported_at": datetime.now().isoformat(),
                "statistics": self.get_statistics().to_dict(),
                "records": [r.to_dict() for r in self._records.values()],
            }

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")

        logger.info(f"Exported history to {path}")

    def export_to_csv(self, path: Path) -> None:
        """Export history to a CSV file.

        Args:
            path: Path to export file.
        """
        import csv

        with self._lock:
            with open(path, "w", newline="", encoding="utf-8") as f:
                fieldnames = [
                    "id",
                    "source_path",
                    "output_path",
                    "source_codec",
                    "output_codec",
                    "source_size",
                    "output_size",
                    "converted_at",
                    "success",
                    "error_message",
                    "size_saved",
                    "compression_ratio",
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for record in self._records.values():
                    row = record.to_dict()
                    row["size_saved"] = record.size_saved
                    row["compression_ratio"] = f"{record.compression_ratio:.2%}"
                    writer.writerow(row)

        logger.info(f"Exported history to {path}")

    @staticmethod
    def compute_file_hash(path: Path) -> str:
        """Compute a hash for file identification.

        Uses SHA-256 hash of first and last 1MB of file for
        efficient identification of large files.

        Args:
            path: Path to the file.

        Returns:
            16-character hex hash string.

        Raises:
            FileNotFoundError: If file does not exist.
            OSError: If file cannot be read.
        """
        sha = hashlib.sha256()
        file_size = path.stat().st_size

        with open(path, "rb") as f:
            # Hash first 1MB
            sha.update(f.read(1024 * 1024))

            # If file is larger than 2MB, also hash last 1MB
            if file_size > 2 * 1024 * 1024:
                f.seek(-1024 * 1024, 2)  # Seek to last 1MB
                sha.update(f.read())
            elif file_size > 1024 * 1024:
                # File between 1MB and 2MB, hash remaining
                sha.update(f.read())

        return sha.hexdigest()[:16]


# Module-level singleton management
_default_history: ConversionHistory | None = None
_history_lock = threading.Lock()


def get_history(history_path: Path | None = None) -> ConversionHistory:
    """Get or create the default ConversionHistory instance.

    Args:
        history_path: Optional path. Only used on first call.

    Returns:
        The default ConversionHistory instance.
    """
    global _default_history
    with _history_lock:
        if _default_history is None:
            _default_history = ConversionHistory(history_path=history_path)
        return _default_history


def reset_history() -> None:
    """Reset the default history instance.

    Primarily useful for testing.
    """
    global _default_history
    with _history_lock:
        _default_history = None


__all__ = [
    "ConversionHistory",
    "ConversionRecord",
    "HistoryStatistics",
    "HistoryError",
    "HistoryCorruptedError",
    "StatsPeriod",
    "get_history",
    "reset_history",
    "DEFAULT_HISTORY_DIR",
    "DEFAULT_HISTORY_FILE",
]
