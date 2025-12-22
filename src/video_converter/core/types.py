"""Core type definitions for video conversion workflow.

This module defines the essential data classes used throughout the video
conversion pipeline, including conversion requests, results, progress tracking,
and reporting structures.

SDS Reference: SDS-C01-001
SRS Reference: SRS-601 (Orchestrator Workflow)

Example:
    >>> from video_converter.core.types import ConversionRequest, ConversionResult
    >>> request = ConversionRequest(
    ...     input_path=Path("input.mov"),
    ...     output_path=Path("output.mp4"),
    ...     mode="hardware",
    ... )
    >>> # After conversion
    >>> result = ConversionResult(
    ...     success=True,
    ...     request=request,
    ...     original_size=100_000_000,
    ...     converted_size=40_000_000,
    ...     duration_seconds=120.5,
    ... )
    >>> print(f"Compression ratio: {result.compression_ratio:.1%}")
    Compression ratio: 60.0%
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable


class ConversionMode(Enum):
    """Video conversion mode.

    Attributes:
        HARDWARE: Use hardware encoder (VideoToolbox on macOS).
        SOFTWARE: Use software encoder (libx265).
    """

    HARDWARE = "hardware"
    SOFTWARE = "software"


class QueuePriority(Enum):
    """Queue priority ordering for batch processing.

    Attributes:
        FIFO: First-in, first-out (default).
        DATE_OLDEST: Oldest files first (by modification time).
        DATE_NEWEST: Newest files first (by modification time).
        SIZE_SMALLEST: Smallest files first.
        SIZE_LARGEST: Largest files first.
    """

    FIFO = "fifo"
    DATE_OLDEST = "date_oldest"
    DATE_NEWEST = "date_newest"
    SIZE_SMALLEST = "size_smallest"
    SIZE_LARGEST = "size_largest"


class ConversionStage(Enum):
    """Stages in the conversion pipeline.

    Attributes:
        DISCOVERY: Finding videos to convert.
        EXPORT: Extracting from Photos library.
        CONVERT: Running the encoder.
        VALIDATE: Verifying output integrity.
        METADATA: Copying metadata.
        CLEANUP: Moving/deleting files.
        COMPLETE: All stages finished.
    """

    DISCOVERY = "discovery"
    EXPORT = "export"
    CONVERT = "convert"
    VALIDATE = "validate"
    METADATA = "metadata"
    CLEANUP = "cleanup"
    COMPLETE = "complete"


class ConversionStatus(Enum):
    """Status of a conversion operation.

    Attributes:
        PENDING: Waiting to be processed.
        IN_PROGRESS: Currently being processed.
        COMPLETED: Successfully completed.
        FAILED: Failed during processing.
        SKIPPED: Skipped (already converted or filtered).
        CANCELLED: Cancelled by user.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class BatchStatus(Enum):
    """Status of a batch conversion operation.

    Attributes:
        IDLE: No batch is running.
        RUNNING: Batch is actively processing.
        PAUSED: Batch is paused by user.
        COMPLETED: Batch finished (success or with failures).
        CANCELLED: Batch was cancelled.
    """

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class ConversionRequest:
    """Request for video conversion.

    Attributes:
        input_path: Path to the input video file.
        output_path: Path for the converted output file.
        mode: Conversion mode (hardware or software).
        quality: Quality setting (1-100, higher is better).
        crf: Constant Rate Factor for encoding.
        preset: Encoding preset (speed vs compression trade-off).
        audio_mode: How to handle audio ("copy", "aac", etc.).
        preserve_metadata: Whether to copy metadata from original.
        bit_depth: Output bit depth (8 or 10). 10-bit for HDR content.
        hdr: Enable HDR encoding parameters for 10-bit content.
    """

    input_path: Path
    output_path: Path
    mode: ConversionMode = ConversionMode.HARDWARE
    quality: int = 45
    crf: int = 22
    preset: str = "medium"
    audio_mode: str = "copy"
    preserve_metadata: bool = True
    bit_depth: int = 8
    hdr: bool = False

    def __post_init__(self) -> None:
        """Validate and normalize fields."""
        if isinstance(self.input_path, str):
            self.input_path = Path(self.input_path)
        if isinstance(self.output_path, str):
            self.output_path = Path(self.output_path)
        if isinstance(self.mode, str):
            self.mode = ConversionMode(self.mode)


@dataclass
class ConversionResult:
    """Result of a single video conversion.

    Attributes:
        success: Whether conversion completed successfully.
        request: The original conversion request.
        original_size: Size of input file in bytes.
        converted_size: Size of output file in bytes.
        duration_seconds: Time taken to convert in seconds.
        speed_ratio: Conversion speed relative to realtime.
        error_message: Error message if conversion failed.
        warnings: Non-critical issues encountered.
        started_at: When conversion started.
        completed_at: When conversion finished.
        retry_count: Number of retry attempts made (0 if no retries).
        retry_strategy_used: Final retry strategy that succeeded (or None).
        retry_history: Detailed history of all retry attempts.
    """

    success: bool
    request: ConversionRequest
    original_size: int = 0
    converted_size: int = 0
    duration_seconds: float = 0.0
    speed_ratio: float = 0.0
    error_message: str | None = None
    warnings: list[str] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0
    retry_strategy_used: str | None = None
    retry_history: list[dict] = field(default_factory=list)

    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio (0.0-1.0).

        Returns:
            Compression ratio where 0.6 means 60% size reduction.
        """
        if self.original_size <= 0:
            return 0.0
        return 1.0 - (self.converted_size / self.original_size)

    @property
    def size_saved(self) -> int:
        """Calculate bytes saved by compression."""
        return max(0, self.original_size - self.converted_size)


@dataclass
class ConversionProgress:
    """Progress information for conversion tracking.

    Attributes:
        stage: Current stage in the pipeline.
        status: Current status of the operation.
        current_file: Name of the file being processed.
        current_index: Index of current file (0-based).
        total_files: Total number of files to process.
        stage_progress: Progress within current stage (0.0-1.0).
        overall_progress: Overall progress (0.0-1.0).
        bytes_processed: Bytes processed so far.
        bytes_total: Total bytes to process.
        estimated_time_remaining: Estimated seconds remaining.
        message: Human-readable status message.
    """

    stage: ConversionStage
    status: ConversionStatus
    current_file: str = ""
    current_index: int = 0
    total_files: int = 0
    stage_progress: float = 0.0
    overall_progress: float = 0.0
    bytes_processed: int = 0
    bytes_total: int = 0
    estimated_time_remaining: float | None = None
    message: str = ""

    def __post_init__(self) -> None:
        """Validate progress values."""
        self.stage_progress = max(0.0, min(1.0, self.stage_progress))
        self.overall_progress = max(0.0, min(1.0, self.overall_progress))


@dataclass
class ConversionReport:
    """Summary report for a conversion batch.

    Attributes:
        session_id: Unique identifier for this conversion session.
        started_at: When the batch started.
        completed_at: When the batch finished.
        total_files: Total files in the batch.
        successful: Number of successfully converted files.
        failed: Number of failed conversions.
        skipped: Number of skipped files.
        cancelled: Whether the batch was cancelled.
        total_original_size: Sum of all original file sizes.
        total_converted_size: Sum of all converted file sizes.
        total_duration_seconds: Total conversion time.
        results: Individual conversion results.
        errors: Aggregated error messages.
        warnings: Aggregated warning messages.
    """

    session_id: str
    started_at: datetime
    completed_at: datetime | None = None
    total_files: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    cancelled: bool = False
    total_original_size: int = 0
    total_converted_size: int = 0
    total_duration_seconds: float = 0.0
    results: list[ConversionResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def total_size_saved(self) -> int:
        """Calculate total bytes saved."""
        return max(0, self.total_original_size - self.total_converted_size)

    @property
    def average_compression_ratio(self) -> float:
        """Calculate average compression ratio."""
        if self.total_original_size <= 0:
            return 0.0
        return 1.0 - (self.total_converted_size / self.total_original_size)

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0-1.0)."""
        processed = self.successful + self.failed
        if processed <= 0:
            return 0.0
        return self.successful / processed

    def add_result(self, result: ConversionResult) -> None:
        """Add a conversion result to the report.

        Args:
            result: The conversion result to add.
        """
        self.results.append(result)
        self.total_original_size += result.original_size
        self.total_converted_size += result.converted_size
        self.total_duration_seconds += result.duration_seconds

        if result.success:
            self.successful += 1
        else:
            self.failed += 1
            if result.error_message:
                self.errors.append(
                    f"{result.request.input_path.name}: {result.error_message}"
                )

        self.warnings.extend(result.warnings)


class SessionStatus(Enum):
    """Status of a conversion session for persistence.

    Attributes:
        ACTIVE: Session is currently running.
        PAUSED: Session was paused and can be resumed.
        COMPLETED: Session finished successfully.
        INTERRUPTED: Session was interrupted (crash, shutdown).
        CANCELLED: Session was explicitly cancelled.
    """

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"


@dataclass
class VideoEntry:
    """Entry for a video file in session state.

    Attributes:
        path: Absolute path to the video file.
        output_path: Absolute path to the output file.
        status: Current conversion status.
        error_message: Error message if failed.
        original_size: Size of original file in bytes.
        converted_size: Size of converted file in bytes.
    """

    path: Path
    output_path: Path
    status: ConversionStatus = ConversionStatus.PENDING
    error_message: str | None = None
    original_size: int = 0
    converted_size: int = 0

    def __post_init__(self) -> None:
        """Validate and normalize fields."""
        if isinstance(self.path, str):
            self.path = Path(self.path)
        if isinstance(self.output_path, str):
            self.output_path = Path(self.output_path)
        if isinstance(self.status, str):
            self.status = ConversionStatus(self.status)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "path": str(self.path),
            "output_path": str(self.output_path),
            "status": self.status.value,
            "error_message": self.error_message,
            "original_size": self.original_size,
            "converted_size": self.converted_size,
        }

    @classmethod
    def from_dict(cls, data: dict) -> VideoEntry:
        """Create from dictionary."""
        return cls(
            path=Path(data["path"]),
            output_path=Path(data["output_path"]),
            status=ConversionStatus(data["status"]),
            error_message=data.get("error_message"),
            original_size=data.get("original_size", 0),
            converted_size=data.get("converted_size", 0),
        )


@dataclass
class SessionState:
    """Persistent session state for resumable conversions.

    Tracks all information needed to resume an interrupted conversion session,
    including which files have been processed and any temporary files created.

    Attributes:
        session_id: Unique identifier for this session.
        status: Current session status.
        started_at: When the session started.
        updated_at: When the session was last updated.
        current_index: Index of the file currently being processed.
        pending_videos: List of videos waiting to be processed.
        completed_videos: List of successfully completed videos.
        failed_videos: List of videos that failed conversion.
        temporary_files: List of temporary files created during conversion.
        output_dir: Output directory for converted files.
        config_snapshot: Snapshot of configuration at session start.
    """

    session_id: str
    status: SessionStatus = SessionStatus.ACTIVE
    started_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    current_index: int = 0
    pending_videos: list[VideoEntry] = field(default_factory=list)
    completed_videos: list[VideoEntry] = field(default_factory=list)
    failed_videos: list[VideoEntry] = field(default_factory=list)
    temporary_files: list[Path] = field(default_factory=list)
    output_dir: Path | None = None
    config_snapshot: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and normalize fields."""
        if isinstance(self.status, str):
            self.status = SessionStatus(self.status)
        if isinstance(self.started_at, str):
            self.started_at = datetime.fromisoformat(self.started_at)
        if isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
        if self.output_dir is not None and isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
        # Normalize temporary files
        self.temporary_files = [
            Path(f) if isinstance(f, str) else f for f in self.temporary_files
        ]

    @property
    def total_videos(self) -> int:
        """Get total number of videos in the session."""
        return (
            len(self.pending_videos)
            + len(self.completed_videos)
            + len(self.failed_videos)
        )

    @property
    def progress(self) -> float:
        """Get session progress as a fraction (0.0-1.0)."""
        total = self.total_videos
        if total == 0:
            return 0.0
        processed = len(self.completed_videos) + len(self.failed_videos)
        return processed / total

    @property
    def is_resumable(self) -> bool:
        """Check if this session can be resumed."""
        return self.status in (SessionStatus.PAUSED, SessionStatus.INTERRUPTED)

    def mark_video_completed(
        self,
        video: VideoEntry,
        original_size: int = 0,
        converted_size: int = 0,
    ) -> None:
        """Move a video from pending to completed.

        Args:
            video: The video entry to mark complete.
            original_size: Size of original file in bytes.
            converted_size: Size of converted file in bytes.
        """
        video.status = ConversionStatus.COMPLETED
        video.original_size = original_size
        video.converted_size = converted_size
        if video in self.pending_videos:
            self.pending_videos.remove(video)
        if video not in self.completed_videos:
            self.completed_videos.append(video)
        self.updated_at = datetime.now()

    def mark_video_failed(self, video: VideoEntry, error: str) -> None:
        """Move a video from pending to failed.

        Args:
            video: The video entry to mark failed.
            error: Error message describing the failure.
        """
        video.status = ConversionStatus.FAILED
        video.error_message = error
        if video in self.pending_videos:
            self.pending_videos.remove(video)
        if video not in self.failed_videos:
            self.failed_videos.append(video)
        self.updated_at = datetime.now()

    def add_temporary_file(self, path: Path) -> None:
        """Track a temporary file created during conversion.

        Args:
            path: Path to the temporary file.
        """
        if path not in self.temporary_files:
            self.temporary_files.append(path)
            self.updated_at = datetime.now()

    def remove_temporary_file(self, path: Path) -> None:
        """Remove a temporary file from tracking.

        Args:
            path: Path to the temporary file.
        """
        if path in self.temporary_files:
            self.temporary_files.remove(path)
            self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "current_index": self.current_index,
            "pending_videos": [v.to_dict() for v in self.pending_videos],
            "completed_videos": [v.to_dict() for v in self.completed_videos],
            "failed_videos": [v.to_dict() for v in self.failed_videos],
            "temporary_files": [str(f) for f in self.temporary_files],
            "output_dir": str(self.output_dir) if self.output_dir else None,
            "config_snapshot": self.config_snapshot,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SessionState:
        """Create from dictionary.

        Args:
            data: Dictionary containing session state data.

        Returns:
            A new SessionState instance.
        """
        return cls(
            session_id=data["session_id"],
            status=SessionStatus(data["status"]),
            started_at=datetime.fromisoformat(data["started_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            current_index=data.get("current_index", 0),
            pending_videos=[
                VideoEntry.from_dict(v) for v in data.get("pending_videos", [])
            ],
            completed_videos=[
                VideoEntry.from_dict(v) for v in data.get("completed_videos", [])
            ],
            failed_videos=[
                VideoEntry.from_dict(v) for v in data.get("failed_videos", [])
            ],
            temporary_files=[Path(f) for f in data.get("temporary_files", [])],
            output_dir=Path(data["output_dir"]) if data.get("output_dir") else None,
            config_snapshot=data.get("config_snapshot", {}),
        )


# Type aliases for callbacks
ProgressCallback = Callable[[ConversionProgress], None]
CompleteCallback = Callable[[ConversionReport], None]
