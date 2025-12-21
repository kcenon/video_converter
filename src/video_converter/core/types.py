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
    """

    input_path: Path
    output_path: Path
    mode: ConversionMode = ConversionMode.HARDWARE
    quality: int = 45
    crf: int = 22
    preset: str = "medium"
    audio_mode: str = "copy"
    preserve_metadata: bool = True

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


# Type aliases for callbacks
ProgressCallback = Callable[[ConversionProgress], None]
CompleteCallback = Callable[[ConversionReport], None]
