"""Orchestrator for video conversion workflow.

This module implements the central Orchestrator class that coordinates
the entire video conversion workflow from discovery to completion.

SDS Reference: SDS-C01-002
SRS Reference: SRS-601 (Orchestrator Workflow)

Example:
    >>> from video_converter.core.orchestrator import Orchestrator
    >>> from video_converter.core import ConversionRequest
    >>>
    >>> orchestrator = Orchestrator()
    >>>
    >>> # Convert a single file
    >>> result = await orchestrator.convert_single(
    ...     input_path=Path("input.mov"),
    ...     output_path=Path("output.mp4"),
    ... )
    >>>
    >>> # Run batch conversion with progress tracking
    >>> def on_progress(progress):
    ...     print(f"Progress: {progress.overall_progress:.1%}")
    >>>
    >>> report = await orchestrator.run(
    ...     input_paths=[Path("video1.mov"), Path("video2.mov")],
    ...     output_dir=Path("converted"),
    ...     on_progress=on_progress,
    ... )
    >>> print(f"Converted: {report.successful}/{report.total_files}")
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from video_converter.converters.base import (
    BaseConverter,
    EncoderNotAvailableError,
)
from video_converter.converters.factory import ConverterFactory
from video_converter.core.concurrent import (
    AggregatedProgress,
    ConcurrentProcessor,
)
from video_converter.core.error_recovery import (
    ErrorRecoveryManager,
    FailureRecord,
)
from video_converter.core.session import SessionStateManager
from video_converter.core.types import (
    BatchStatus,
    CompleteCallback,
    ConversionMode,
    ConversionProgress,
    ConversionReport,
    ConversionRequest,
    ConversionResult,
    ConversionStage,
    ConversionStatus,
    ErrorCategory,
    ProgressCallback,
    QueuePriority,
    RecoveryAction,
    SessionState,
    SessionStatus,
    VideoEntry,
)
from video_converter.processors.quality_validator import (
    ValidationResult,
    ValidationStrictness,
    VideoValidator,
)
from video_converter.processors.retry_manager import (
    RetryConfig,
    RetryManager,
)
from video_converter.processors.timestamp import TimestampSynchronizer

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# Common video extensions
VIDEO_EXTENSIONS = {".mov", ".mp4", ".m4v", ".avi", ".mkv", ".wmv", ".flv", ".webm"}


@dataclass
class OrchestratorConfig:
    """Configuration for the Orchestrator.

    Attributes:
        mode: Preferred conversion mode (hardware or software).
        quality: Quality setting for encoding (1-100).
        crf: Constant Rate Factor for software encoding.
        preset: Encoding preset for software encoding.
        output_suffix: Suffix to add to output filenames.
        preserve_metadata: Whether to copy metadata from original.
        preserve_timestamps: Whether to sync timestamps from original.
        validate_output: Whether to validate converted files.
        validation_strictness: How strictly to validate output.
        max_concurrent: Maximum concurrent conversions.
        delete_original: Whether to delete original after success.
        move_to_processed: Directory to move processed originals.
        move_to_failed: Directory to move failed files.
        queue_priority: Priority ordering for batch queue.
        enable_retry: Whether to retry failed conversions.
        retry_config: Configuration for retry behavior.
        check_disk_space: Whether to check disk space before processing.
        min_free_space: Minimum free disk space in bytes (default 1GB).
        pause_on_disk_full: Whether to pause on low disk space.
    """

    mode: ConversionMode = ConversionMode.HARDWARE
    quality: int = 45
    crf: int = 22
    preset: str = "medium"
    output_suffix: str = "_h265"
    preserve_metadata: bool = True
    preserve_timestamps: bool = True
    validate_output: bool = True
    validation_strictness: ValidationStrictness = ValidationStrictness.STANDARD
    max_concurrent: int = 2
    delete_original: bool = False
    move_to_processed: Path | None = None
    move_to_failed: Path | None = None
    queue_priority: QueuePriority = QueuePriority.FIFO
    enable_retry: bool = True
    retry_config: RetryConfig | None = None
    check_disk_space: bool = True
    min_free_space: int = 1024 * 1024 * 1024  # 1GB
    pause_on_disk_full: bool = True


@dataclass
class ConversionTask:
    """A single video conversion task in the queue.

    Attributes:
        input_path: Path to input video.
        output_path: Path for output video.
        status: Current status of the task.
        result: Conversion result (when complete).
        error: Error message (if failed).
    """

    input_path: Path
    output_path: Path
    status: ConversionStatus = ConversionStatus.PENDING
    result: ConversionResult | None = None
    error: str | None = None


class Orchestrator:
    """Coordinates the video conversion workflow.

    The Orchestrator manages the entire conversion pipeline:
    1. Discovery - Finding videos to convert
    2. Queueing - Managing the conversion queue
    3. Converting - Running the encoder
    4. Validating - Verifying output integrity
    5. Cleanup - Moving/deleting files
    6. Reporting - Generating conversion reports

    Attributes:
        config: Orchestrator configuration.
        converter_factory: Factory for creating converters.
        validator: Video file validator.
        timestamp_synchronizer: Timestamp synchronization handler.
        session_manager: Session state manager for persistence.
    """

    def __init__(
        self,
        config: OrchestratorConfig | None = None,
        converter_factory: ConverterFactory | None = None,
        validator: VideoValidator | None = None,
        timestamp_synchronizer: TimestampSynchronizer | None = None,
        session_manager: SessionStateManager | None = None,
        enable_session_persistence: bool = True,
        retry_manager: RetryManager | None = None,
        error_recovery_manager: ErrorRecoveryManager | None = None,
    ) -> None:
        """Initialize the Orchestrator.

        Args:
            config: Optional configuration. Uses defaults if not provided.
            converter_factory: Optional converter factory.
            validator: Optional video validator.
            timestamp_synchronizer: Optional timestamp synchronizer.
            session_manager: Optional session state manager.
            enable_session_persistence: Whether to enable session persistence.
            retry_manager: Optional retry manager for failed conversions.
            error_recovery_manager: Optional error recovery manager.
        """
        self.config = config or OrchestratorConfig()
        self.converter_factory = converter_factory or ConverterFactory()
        self.validator = validator or VideoValidator()
        self.timestamp_synchronizer = timestamp_synchronizer or TimestampSynchronizer()
        self._enable_session_persistence = enable_session_persistence

        if enable_session_persistence:
            self.session_manager = session_manager or SessionStateManager()
        else:
            self.session_manager = None

        if self.config.enable_retry:
            retry_config = self.config.retry_config or RetryConfig()
            self.retry_manager = retry_manager or RetryManager(retry_config)
        else:
            self.retry_manager = None

        # Initialize error recovery manager
        self.error_recovery_manager = error_recovery_manager or ErrorRecoveryManager(
            failed_dir=self.config.move_to_failed,
            min_free_space=self.config.min_free_space,
        )

        self._converter: BaseConverter | None = None
        self._cancelled = False
        self._paused = False
        self._paused_reason: str | None = None
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused initially
        self._batch_status = BatchStatus.IDLE
        self._current_session_id: str | None = None
        self._tasks: list[ConversionTask] = []
        self._current_session: SessionState | None = None

        # Concurrent processing support
        self._concurrent_processor = ConcurrentProcessor(
            max_concurrent=self.config.max_concurrent,
            enable_resource_monitoring=True,
            adaptive_concurrency=False,
        )

    def _get_converter(self) -> BaseConverter:
        """Get or create the video converter.

        Returns:
            A converter instance.

        Raises:
            EncoderNotAvailableError: If no encoder is available.
        """
        if self._converter is None:
            self._converter = self.converter_factory.get_converter(
                mode=self.config.mode,
                fallback=True,
            )
        return self._converter

    async def _retry_conversion(
        self,
        request: ConversionRequest,
        failed_result: ConversionResult,
        on_progress: ProgressCallback | None,
        input_path: Path,
    ) -> ConversionResult:
        """Attempt to retry a failed conversion.

        Args:
            request: The original conversion request.
            failed_result: The initial failed result.
            on_progress: Optional progress callback.
            input_path: Path to input file.

        Returns:
            ConversionResult with retry information.
        """
        if self.retry_manager is None:
            return failed_result

        self._emit_progress(
            on_progress,
            ConversionStage.CONVERT,
            ConversionStatus.IN_PROGRESS,
            current_file=input_path.name,
            message=f"Retrying conversion for {input_path.name}...",
        )

        logger.info(f"Starting retry sequence for {input_path.name}")

        validator = self.validator if self.config.validate_output else None
        retry_result = await self.retry_manager.execute_with_retry(
            request=request,
            converter_factory=self.converter_factory,
            validator=validator,
        )

        if retry_result.success and retry_result.final_result:
            result = retry_result.final_result
            result.retry_count = retry_result.total_attempts
            result.retry_strategy_used = (
                retry_result.final_strategy.value
                if retry_result.final_strategy
                else None
            )
            result.retry_history = [a.to_dict() for a in retry_result.attempts]
            logger.info(
                f"Retry succeeded for {input_path.name} after "
                f"{retry_result.total_attempts} attempts"
            )
            return result

        failed_result.retry_count = retry_result.total_attempts
        failed_result.retry_strategy_used = (
            retry_result.final_strategy.value
            if retry_result.final_strategy
            else None
        )
        failed_result.retry_history = [a.to_dict() for a in retry_result.attempts]

        if retry_result.final_result:
            failed_result.error_message = retry_result.final_result.error_message
            failed_result.warnings.extend(retry_result.final_result.warnings)

        logger.error(
            f"All retry attempts failed for {input_path.name}: "
            f"{retry_result.get_failure_report()}"
        )

        return failed_result

    def _generate_session_id(self) -> str:
        """Generate a unique session ID.

        Returns:
            A UUID string for the session.
        """
        return str(uuid.uuid4())[:8]

    def _create_output_path(
        self,
        input_path: Path,
        output_dir: Path | None = None,
    ) -> Path:
        """Create output path for a converted file.

        Args:
            input_path: Path to the input file.
            output_dir: Optional output directory.

        Returns:
            Path for the output file.
        """
        # Use same directory if output_dir not specified
        if output_dir is None:
            output_dir = input_path.parent

        # Build output filename with suffix
        stem = input_path.stem
        if self.config.output_suffix and not stem.endswith(self.config.output_suffix):
            stem = f"{stem}{self.config.output_suffix}"

        return output_dir / f"{stem}.mp4"

    def _sort_by_priority(self, paths: list[Path]) -> list[Path]:
        """Sort input paths according to configured priority.

        Args:
            paths: List of input file paths.

        Returns:
            Sorted list of paths.
        """
        priority = self.config.queue_priority

        if priority == QueuePriority.FIFO:
            return paths

        if priority == QueuePriority.DATE_OLDEST:
            return sorted(paths, key=lambda p: p.stat().st_mtime)

        if priority == QueuePriority.DATE_NEWEST:
            return sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)

        if priority == QueuePriority.SIZE_SMALLEST:
            return sorted(paths, key=lambda p: p.stat().st_size)

        if priority == QueuePriority.SIZE_LARGEST:
            return sorted(paths, key=lambda p: p.stat().st_size, reverse=True)

        return paths

    def _emit_progress(
        self,
        callback: ProgressCallback | None,
        stage: ConversionStage,
        status: ConversionStatus,
        current_file: str = "",
        current_index: int = 0,
        total_files: int = 0,
        stage_progress: float = 0.0,
        message: str = "",
    ) -> None:
        """Emit a progress update.

        Args:
            callback: The progress callback to invoke.
            stage: Current pipeline stage.
            status: Current status.
            current_file: Name of current file.
            current_index: Index of current file.
            total_files: Total files to process.
            stage_progress: Progress within stage.
            message: Status message.
        """
        if callback is None:
            return

        # Calculate overall progress
        stage_weights = {
            ConversionStage.DISCOVERY: 0.05,
            ConversionStage.EXPORT: 0.05,
            ConversionStage.CONVERT: 0.70,
            ConversionStage.VALIDATE: 0.10,
            ConversionStage.METADATA: 0.05,
            ConversionStage.CLEANUP: 0.05,
            ConversionStage.COMPLETE: 1.0,
        }

        # Calculate progress based on completed stages and current progress
        completed_weight = sum(
            weight
            for s, weight in stage_weights.items()
            if s.value < stage.value and s != ConversionStage.COMPLETE
        )
        current_weight = stage_weights.get(stage, 0.0) * stage_progress
        overall = completed_weight + current_weight

        progress = ConversionProgress(
            stage=stage,
            status=status,
            current_file=current_file,
            current_index=current_index,
            total_files=total_files,
            stage_progress=stage_progress,
            overall_progress=overall,
            message=message,
        )

        try:
            callback(progress)
        except Exception as e:
            logger.warning(f"Progress callback error: {e}")

    async def convert_single(
        self,
        input_path: Path,
        output_path: Path | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> ConversionResult:
        """Convert a single video file through the full pipeline.

        Args:
            input_path: Path to the input video.
            output_path: Path for the output video. Auto-generated if None.
            on_progress: Optional progress callback.

        Returns:
            ConversionResult with success status and statistics.
        """
        self._cancelled = False

        # Validate input
        if not input_path.exists():
            return ConversionResult(
                success=False,
                request=ConversionRequest(
                    input_path=input_path,
                    output_path=output_path or self._create_output_path(input_path),
                ),
                error_message=f"Input file not found: {input_path}",
            )

        # Generate output path if needed
        if output_path is None:
            output_path = self._create_output_path(input_path)

        # Create conversion request
        request = ConversionRequest(
            input_path=input_path,
            output_path=output_path,
            mode=self.config.mode,
            quality=self.config.quality,
            crf=self.config.crf,
            preset=self.config.preset,
            preserve_metadata=self.config.preserve_metadata,
        )

        # Stage 1: Convert
        self._emit_progress(
            on_progress,
            ConversionStage.CONVERT,
            ConversionStatus.IN_PROGRESS,
            current_file=input_path.name,
            message=f"Converting {input_path.name}...",
        )

        try:
            converter = self._get_converter()
        except EncoderNotAvailableError as e:
            return ConversionResult(
                success=False,
                request=request,
                error_message=str(e),
            )

        result = await converter.convert(request)

        if not result.success:
            if self.retry_manager:
                return await self._retry_conversion(
                    request, result, on_progress, input_path
                )
            return result

        if self._cancelled:
            # Clean up output file
            if output_path.exists():
                output_path.unlink()
            result.success = False
            result.error_message = "Conversion cancelled"
            return result

        # Stage 2: Validate
        if self.config.validate_output:
            self._emit_progress(
                on_progress,
                ConversionStage.VALIDATE,
                ConversionStatus.IN_PROGRESS,
                current_file=input_path.name,
                message=f"Validating {output_path.name}...",
            )

            validation = self.validator.validate(
                output_path,
                self.config.validation_strictness,
            )

            if not validation.valid:
                # Validation failed - try retry if enabled
                if self.retry_manager:
                    if output_path.exists():
                        output_path.unlink()
                    result.success = False
                    result.error_message = (
                        f"Validation failed: {', '.join(validation.errors)}"
                    )
                    result.warnings.extend(validation.warnings)
                    return await self._retry_conversion(
                        request, result, on_progress, input_path
                    )

                # No retry - clean up and report
                if output_path.exists():
                    output_path.unlink()
                result.success = False
                result.error_message = (
                    f"Validation failed: {', '.join(validation.errors)}"
                )
                result.warnings.extend(validation.warnings)
                return result

            result.warnings.extend(validation.warnings)

        # Stage 3: Metadata - Sync timestamps
        if self.config.preserve_timestamps:
            self._emit_progress(
                on_progress,
                ConversionStage.METADATA,
                ConversionStatus.IN_PROGRESS,
                current_file=input_path.name,
                message=f"Syncing timestamps for {output_path.name}...",
            )

            timestamp_result = self.timestamp_synchronizer.sync_from_file(
                source=input_path,
                dest=output_path,
            )

            if not timestamp_result.success:
                result.warnings.append(
                    f"Timestamp sync incomplete: {timestamp_result.warnings}"
                )
            elif timestamp_result.warnings:
                result.warnings.extend(timestamp_result.warnings)

            logger.debug(
                "Timestamp sync result: birth=%s, mtime=%s, atime=%s",
                timestamp_result.birth_time_synced,
                timestamp_result.modification_time_synced,
                timestamp_result.access_time_synced,
            )

        # Stage 4: Cleanup
        self._emit_progress(
            on_progress,
            ConversionStage.CLEANUP,
            ConversionStatus.IN_PROGRESS,
            current_file=input_path.name,
            message="Cleaning up...",
        )

        if self.config.delete_original:
            try:
                input_path.unlink()
                logger.info(f"Deleted original: {input_path}")
            except OSError as e:
                result.warnings.append(f"Could not delete original: {e}")

        elif self.config.move_to_processed:
            try:
                dest = self.config.move_to_processed / input_path.name
                self.config.move_to_processed.mkdir(parents=True, exist_ok=True)
                input_path.rename(dest)
                logger.info(f"Moved original to: {dest}")
            except OSError as e:
                result.warnings.append(f"Could not move original: {e}")

        # Complete
        self._emit_progress(
            on_progress,
            ConversionStage.COMPLETE,
            ConversionStatus.COMPLETED,
            current_file=input_path.name,
            stage_progress=1.0,
            message="Conversion complete",
        )

        return result

    async def run(
        self,
        input_paths: list[Path],
        output_dir: Path | None = None,
        on_progress: ProgressCallback | None = None,
        on_complete: CompleteCallback | None = None,
        resume_session: bool = False,
    ) -> ConversionReport:
        """Run batch conversion on multiple files.

        Args:
            input_paths: List of input video paths.
            output_dir: Directory for output files. Uses original dirs if None.
            on_progress: Optional progress callback.
            on_complete: Optional completion callback.
            resume_session: If True, try to resume an interrupted session.

        Returns:
            ConversionReport with batch statistics.
        """
        self._cancelled = False
        self._paused = False
        self._pause_event.set()
        self._batch_status = BatchStatus.RUNNING
        self._current_session_id = self._generate_session_id()

        report = ConversionReport(
            session_id=self._current_session_id,
            started_at=datetime.now(),
            total_files=len(input_paths),
        )

        if not input_paths:
            report.completed_at = datetime.now()
            self._batch_status = BatchStatus.COMPLETED
            if on_complete:
                on_complete(report)
            return report

        # Sort input paths by priority
        sorted_paths = self._sort_by_priority(list(input_paths))

        # Stage 1: Discovery - Build task queue
        self._emit_progress(
            on_progress,
            ConversionStage.DISCOVERY,
            ConversionStatus.IN_PROGRESS,
            total_files=len(sorted_paths),
            message="Discovering videos...",
        )

        self._tasks = []
        for input_path in sorted_paths:
            output_path = self._create_output_path(input_path, output_dir)

            # Skip if output already exists
            if output_path.exists():
                logger.info(f"Skipping (output exists): {input_path.name}")
                report.skipped += 1
                continue

            self._tasks.append(
                ConversionTask(
                    input_path=input_path,
                    output_path=output_path,
                )
            )

        if not self._tasks:
            report.completed_at = datetime.now()
            if on_complete:
                on_complete(report)
            return report

        # Create session state for persistence
        if self.session_manager:
            self._current_session = self.session_manager.create_session(
                video_paths=[t.input_path for t in self._tasks],
                output_dir=output_dir,
                config=self.config,
            )
            self._current_session_id = self._current_session.session_id
            report.session_id = self._current_session_id

        # Stage 2: Process queue
        total_tasks = len(self._tasks)

        # Use concurrent processing if max_concurrent > 1
        if self.config.max_concurrent > 1:
            await self._process_tasks_concurrent(
                report, on_progress, total_tasks
            )
        else:
            await self._process_tasks_sequential(
                report, on_progress, total_tasks
            )

        # Complete
        report.completed_at = datetime.now()
        if not self._cancelled:
            self._batch_status = BatchStatus.COMPLETED
            if self.session_manager:
                self.session_manager.complete_session()

        self._emit_progress(
            on_progress,
            ConversionStage.COMPLETE,
            ConversionStatus.COMPLETED,
            total_files=total_tasks,
            stage_progress=1.0,
            message=(
                f"Completed: {report.successful} succeeded, "
                f"{report.failed} failed, {report.skipped} skipped"
            ),
        )

        if on_complete:
            on_complete(report)

        return report

    async def _process_tasks_sequential(
        self,
        report: ConversionReport,
        on_progress: ProgressCallback | None,
        total_tasks: int,
    ) -> None:
        """Process tasks sequentially (max_concurrent = 1).

        Args:
            report: The conversion report to update.
            on_progress: Optional progress callback.
            total_tasks: Total number of tasks.
        """
        for i, task in enumerate(self._tasks):
            # Wait if paused
            await self._pause_event.wait()

            if self._cancelled:
                report.cancelled = True
                self._batch_status = BatchStatus.CANCELLED
                if self.session_manager:
                    self.session_manager.cancel_session()
                break

            task.status = ConversionStatus.IN_PROGRESS

            # Update session state
            if self._current_session:
                self._current_session.current_index = i

            self._emit_progress(
                on_progress,
                ConversionStage.CONVERT,
                ConversionStatus.IN_PROGRESS,
                current_file=task.input_path.name,
                current_index=i,
                total_files=total_tasks,
                stage_progress=i / total_tasks,
                message=f"Converting {task.input_path.name} ({i + 1}/{total_tasks})...",
            )

            # Convert this file
            result = await self.convert_single(
                input_path=task.input_path,
                output_path=task.output_path,
            )

            self._handle_task_result(task, result, report)

    async def _process_tasks_concurrent(
        self,
        report: ConversionReport,
        on_progress: ProgressCallback | None,
        total_tasks: int,
    ) -> None:
        """Process tasks concurrently using ConcurrentProcessor.

        Args:
            report: The conversion report to update.
            on_progress: Optional progress callback.
            total_tasks: Total number of tasks.
        """
        logger.info(
            f"Starting concurrent processing with max_concurrent={self.config.max_concurrent}"
        )

        # Create a mapping of task index to task for result handling
        task_map = {i: task for i, task in enumerate(self._tasks)}

        def on_aggregated_progress(agg_progress: AggregatedProgress) -> None:
            """Handle aggregated progress from concurrent processor."""
            if on_progress:
                # Calculate stage progress based on completed + in-progress
                stage_progress = agg_progress.overall_progress

                # Build message with current files
                if agg_progress.current_files:
                    files_str = ", ".join(agg_progress.current_files[:3])
                    if len(agg_progress.current_files) > 3:
                        files_str += f" (+{len(agg_progress.current_files) - 3} more)"
                    message = f"Converting: {files_str}"
                else:
                    message = (
                        f"Processing: {agg_progress.completed_jobs}/{agg_progress.total_jobs} completed"
                    )

                self._emit_progress(
                    on_progress,
                    ConversionStage.CONVERT,
                    ConversionStatus.IN_PROGRESS,
                    current_file=", ".join(agg_progress.current_files[:2]) or "",
                    current_index=agg_progress.completed_jobs,
                    total_files=total_tasks,
                    stage_progress=stage_progress,
                    message=message,
                )

        async def process_task(
            task: ConversionTask, progress_callback: callable
        ) -> ConversionResult:
            """Process a single task within concurrent context."""
            # Check for pause/cancel
            await self._pause_event.wait()
            if self._cancelled:
                raise asyncio.CancelledError("Batch cancelled")

            task.status = ConversionStatus.IN_PROGRESS

            # Convert the file
            result = await self.convert_single(
                input_path=task.input_path,
                output_path=task.output_path,
            )

            return result

        # Process all tasks concurrently
        results = await self._concurrent_processor.process_batch(
            items=self._tasks,
            processor=process_task,
            on_progress=on_aggregated_progress,
        )

        # Handle results and update report
        for i, result in enumerate(results):
            if i in task_map:
                task = task_map[i]
                if result is not None:
                    self._handle_task_result(task, result, report)
                else:
                    # Task failed with exception
                    task.status = ConversionStatus.FAILED
                    task.error = "Task failed with exception"

        # Check if cancelled
        if self._cancelled:
            report.cancelled = True
            self._batch_status = BatchStatus.CANCELLED
            if self.session_manager:
                self.session_manager.cancel_session()

    def _handle_task_result(
        self,
        task: ConversionTask,
        result: ConversionResult,
        report: ConversionReport,
    ) -> RecoveryAction | None:
        """Handle the result of a conversion task.

        Args:
            task: The conversion task.
            result: The conversion result.
            report: The conversion report to update.

        Returns:
            RecoveryAction if failed and action is needed, None if successful.
        """
        task.result = result
        if result.success:
            task.status = ConversionStatus.COMPLETED
            # Update session state
            if self.session_manager and self._current_session:
                video_entry = self._find_video_entry(task.input_path)
                if video_entry:
                    self.session_manager.mark_video_completed(
                        video_entry,
                        result.original_size,
                        result.converted_size,
                    )
            report.add_result(result)
            return None

        # Handle failure with error recovery manager
        task.status = ConversionStatus.FAILED
        task.error = result.error_message

        # Classify the error
        error_category = self.error_recovery_manager.classify_error(
            result.error_message, result
        )
        recovery_action = self.error_recovery_manager.get_recovery_action(error_category)

        # Update session state
        if self.session_manager and self._current_session:
            video_entry = self._find_video_entry(task.input_path)
            if video_entry:
                self.session_manager.mark_video_failed(
                    video_entry,
                    result.error_message or "Unknown error",
                )

        # Handle failure with error recovery manager
        # This cleans up partial output and moves to failed directory if configured
        self.error_recovery_manager.handle_failure(
            input_path=task.input_path,
            output_path=task.output_path,
            category=error_category,
            error_message=result.error_message or "Unknown error",
            move_to_failed=self.config.move_to_failed is not None,
        )

        # Handle disk space error specially
        if (
            error_category == ErrorCategory.DISK_SPACE_ERROR
            and self.config.pause_on_disk_full
        ):
            self._paused_reason = "Insufficient disk space"
            self.pause()
            logger.warning(
                "Pausing batch conversion due to insufficient disk space. "
                "Free up space and call resume() to continue."
            )

        report.add_result(result)
        return recovery_action

    def _find_video_entry(self, input_path: Path) -> VideoEntry | None:
        """Find a VideoEntry in the current session by input path.

        Args:
            input_path: The input path to search for.

        Returns:
            The VideoEntry if found, None otherwise.
        """
        if self._current_session is None:
            return None

        for video in self._current_session.pending_videos:
            if video.path == input_path:
                return video
        return None

    async def resume_session(
        self,
        on_progress: ProgressCallback | None = None,
        on_complete: CompleteCallback | None = None,
    ) -> ConversionReport | None:
        """Resume an interrupted or paused session from disk.

        This method loads a previously saved session and continues
        processing any pending videos.

        Args:
            on_progress: Optional progress callback.
            on_complete: Optional completion callback.

        Returns:
            ConversionReport if resumed successfully, None if no session to resume.
        """
        if not self.session_manager:
            logger.warning("Session persistence is disabled, cannot resume")
            return None

        session = self.session_manager.resume_session()
        if session is None:
            logger.info("No resumable session found")
            return None

        self._current_session = session
        self._current_session_id = session.session_id

        logger.info(
            f"Resuming session {session.session_id} with "
            f"{len(session.pending_videos)} pending videos"
        )

        # Get pending video paths
        pending_paths = [v.path for v in session.pending_videos]

        if not pending_paths:
            logger.info("No pending videos to process")
            self.session_manager.complete_session()
            return ConversionReport(
                session_id=session.session_id,
                started_at=session.started_at,
                completed_at=datetime.now(),
                total_files=session.total_videos,
                successful=len(session.completed_videos),
                failed=len(session.failed_videos),
            )

        return await self.run(
            input_paths=pending_paths,
            output_dir=session.output_dir,
            on_progress=on_progress,
            on_complete=on_complete,
        )

    def has_resumable_session(self) -> bool:
        """Check if there is a resumable session available.

        Returns:
            True if a session can be resumed, False otherwise.
        """
        if not self.session_manager:
            return False
        return self.session_manager.has_resumable_session()

    def get_session_status(self) -> dict | None:
        """Get the current session status.

        Returns:
            Session status dictionary, or None if no session.
        """
        if not self.session_manager:
            return None
        return self.session_manager.get_session_status()

    async def run_directory(
        self,
        input_dir: Path,
        output_dir: Path | None = None,
        recursive: bool = False,
        on_progress: ProgressCallback | None = None,
        on_complete: CompleteCallback | None = None,
    ) -> ConversionReport:
        """Run batch conversion on a directory.

        Args:
            input_dir: Directory containing videos.
            output_dir: Directory for output files.
            recursive: Whether to search subdirectories.
            on_progress: Optional progress callback.
            on_complete: Optional completion callback.

        Returns:
            ConversionReport with batch statistics.
        """
        # Discover video files
        video_files: list[Path] = []

        if recursive:
            for ext in VIDEO_EXTENSIONS:
                video_files.extend(input_dir.rglob(f"*{ext}"))
        else:
            for ext in VIDEO_EXTENSIONS:
                video_files.extend(input_dir.glob(f"*{ext}"))

        # Sort by name for consistent ordering
        video_files.sort()

        return await self.run(
            input_paths=video_files,
            output_dir=output_dir,
            on_progress=on_progress,
            on_complete=on_complete,
        )

    def cancel(self) -> None:
        """Cancel the current conversion operation."""
        self._cancelled = True
        self._batch_status = BatchStatus.CANCELLED
        if self._converter:
            self._converter.cancel()
        # Also resume if paused, so the loop can exit
        self._pause_event.set()
        logger.info("Conversion cancelled by user")

    def pause(self) -> bool:
        """Pause the batch conversion.

        Pauses after the current file completes.

        Returns:
            True if paused, False if not running.
        """
        if self._batch_status != BatchStatus.RUNNING:
            return False

        self._paused = True
        self._pause_event.clear()
        self._batch_status = BatchStatus.PAUSED

        # Update session state
        if self.session_manager:
            self.session_manager.pause_session()

        logger.info("Batch conversion paused")
        return True

    def resume(self) -> bool:
        """Resume a paused batch conversion.

        This resumes a batch that was paused in the current session.
        To resume a saved session from disk, use resume_session() instead.

        Returns:
            True if resumed, False if not paused.
        """
        if self._batch_status != BatchStatus.PAUSED:
            return False

        self._paused = False
        self._pause_event.set()
        self._batch_status = BatchStatus.RUNNING

        # Update session state
        if self.session_manager and self._current_session:
            self._current_session.status = SessionStatus.ACTIVE
            self.session_manager.save(force=True)

        logger.info("Batch conversion resumed")
        return True

    def get_batch_status(self) -> BatchStatus:
        """Get current batch conversion status.

        Returns:
            Current BatchStatus.
        """
        return self._batch_status

    def is_paused(self) -> bool:
        """Check if batch conversion is paused.

        Returns:
            True if paused, False otherwise.
        """
        return self._batch_status == BatchStatus.PAUSED

    def get_pending_tasks(self) -> list[ConversionTask]:
        """Get list of pending tasks.

        Returns:
            List of tasks not yet completed.
        """
        return [t for t in self._tasks if t.status == ConversionStatus.PENDING]

    def get_completed_tasks(self) -> list[ConversionTask]:
        """Get list of completed tasks.

        Returns:
            List of successfully completed tasks.
        """
        return [t for t in self._tasks if t.status == ConversionStatus.COMPLETED]

    def get_failed_tasks(self) -> list[ConversionTask]:
        """Get list of failed tasks.

        Returns:
            List of failed tasks.
        """
        return [t for t in self._tasks if t.status == ConversionStatus.FAILED]

    # Synchronous convenience methods

    def convert_single_sync(
        self,
        input_path: Path,
        output_path: Path | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> ConversionResult:
        """Synchronous wrapper for convert_single.

        Args:
            input_path: Path to the input video.
            output_path: Path for the output video.
            on_progress: Optional progress callback.

        Returns:
            ConversionResult with success status and statistics.
        """
        return asyncio.run(
            self.convert_single(input_path, output_path, on_progress)
        )

    def run_sync(
        self,
        input_paths: list[Path],
        output_dir: Path | None = None,
        on_progress: ProgressCallback | None = None,
        on_complete: CompleteCallback | None = None,
    ) -> ConversionReport:
        """Synchronous wrapper for run.

        Args:
            input_paths: List of input video paths.
            output_dir: Directory for output files.
            on_progress: Optional progress callback.
            on_complete: Optional completion callback.

        Returns:
            ConversionReport with batch statistics.
        """
        return asyncio.run(
            self.run(input_paths, output_dir, on_progress, on_complete)
        )

    # Error recovery and manual retry methods

    def check_disk_space(self, path: Path | None = None) -> tuple[bool, dict]:
        """Check if there is sufficient disk space for conversion.

        Args:
            path: Path to check. Uses output directory or home if None.

        Returns:
            Tuple of (has_sufficient_space, disk_info_dict).
        """
        check_path = path
        if check_path is None:
            if self._current_session and self._current_session.output_dir:
                check_path = self._current_session.output_dir
            else:
                check_path = Path.home()

        sufficient, info = self.error_recovery_manager.has_sufficient_space(check_path)
        return sufficient, {
            "path": str(info.path),
            "total_bytes": info.total_bytes,
            "free_bytes": info.free_bytes,
            "used_bytes": info.used_bytes,
            "free_percent": info.free_percent,
            "sufficient": sufficient,
            "required_bytes": self.config.min_free_space,
        }

    def get_failure_records(self) -> list[FailureRecord]:
        """Get list of all recorded failures.

        Returns:
            List of FailureRecord objects from this session.
        """
        return self.error_recovery_manager.failure_records

    def get_retryable_failures(self) -> list[FailureRecord]:
        """Get list of failures that can be retried.

        Returns:
            List of retryable FailureRecord objects.
        """
        return self.error_recovery_manager.get_retryable_failures()

    async def retry_failed(
        self,
        record: FailureRecord,
        on_progress: ProgressCallback | None = None,
    ) -> ConversionResult:
        """Retry a failed conversion.

        This method allows manual retry of a specific failed conversion.

        Args:
            record: The FailureRecord to retry.
            on_progress: Optional progress callback.

        Returns:
            ConversionResult with retry outcome.
        """
        # Prepare the file for retry
        input_path = self.error_recovery_manager.prepare_retry(record)
        if input_path is None:
            return ConversionResult(
                success=False,
                request=ConversionRequest(
                    input_path=record.input_path,
                    output_path=record.output_path,
                ),
                error_message=f"Cannot find file for retry: {record.input_path}",
            )

        # Check disk space before retry
        if self.config.check_disk_space:
            sufficient, _ = self.check_disk_space(record.output_path.parent)
            if not sufficient:
                return ConversionResult(
                    success=False,
                    request=ConversionRequest(
                        input_path=input_path,
                        output_path=record.output_path,
                    ),
                    error_message="Insufficient disk space for retry",
                )

        logger.info(
            f"Retrying failed conversion: {input_path.name} "
            f"(attempt {record.retry_count})"
        )

        # Perform the conversion
        result = await self.convert_single(
            input_path=input_path,
            output_path=record.output_path,
            on_progress=on_progress,
        )

        # Update failure record based on result
        if result.success:
            self.error_recovery_manager.mark_retry_success(record)

        return result

    async def retry_all_failed(
        self,
        on_progress: ProgressCallback | None = None,
    ) -> ConversionReport:
        """Retry all failed conversions that are retryable.

        Args:
            on_progress: Optional progress callback.

        Returns:
            ConversionReport with retry results.
        """
        retryable = self.get_retryable_failures()

        if not retryable:
            logger.info("No retryable failures found")
            return ConversionReport(
                session_id=self._current_session_id or "retry",
                started_at=datetime.now(),
                completed_at=datetime.now(),
                total_files=0,
            )

        report = ConversionReport(
            session_id=f"{self._current_session_id or 'manual'}_retry",
            started_at=datetime.now(),
            total_files=len(retryable),
        )

        logger.info(f"Retrying {len(retryable)} failed conversion(s)")

        for i, record in enumerate(retryable):
            self._emit_progress(
                on_progress,
                ConversionStage.CONVERT,
                ConversionStatus.IN_PROGRESS,
                current_file=record.input_path.name,
                current_index=i,
                total_files=len(retryable),
                stage_progress=i / len(retryable),
                message=f"Retrying {record.input_path.name} ({i + 1}/{len(retryable)})...",
            )

            result = await self.retry_failed(record)
            report.add_result(result)

        report.completed_at = datetime.now()
        return report

    def retry_failed_sync(
        self,
        record: FailureRecord,
        on_progress: ProgressCallback | None = None,
    ) -> ConversionResult:
        """Synchronous wrapper for retry_failed.

        Args:
            record: The FailureRecord to retry.
            on_progress: Optional progress callback.

        Returns:
            ConversionResult with retry outcome.
        """
        return asyncio.run(self.retry_failed(record, on_progress))

    def retry_all_failed_sync(
        self,
        on_progress: ProgressCallback | None = None,
    ) -> ConversionReport:
        """Synchronous wrapper for retry_all_failed.

        Args:
            on_progress: Optional progress callback.

        Returns:
            ConversionReport with retry results.
        """
        return asyncio.run(self.retry_all_failed(on_progress))

    def get_failure_summary(self) -> dict:
        """Get summary of all recorded failures.

        Returns:
            Dictionary with failure statistics.
        """
        return self.error_recovery_manager.get_failure_summary()

    def clear_failure_records(self) -> int:
        """Clear all failure records.

        Returns:
            Number of records cleared.
        """
        return self.error_recovery_manager.clear_failures()

    def get_pause_reason(self) -> str | None:
        """Get the reason for pause if paused.

        Returns:
            Pause reason string, or None if not paused.
        """
        return self._paused_reason if self._paused else None
