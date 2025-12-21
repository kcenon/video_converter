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
    ProgressCallback,
    QueuePriority,
    SessionState,
    SessionStatus,
    VideoEntry,
)
from video_converter.processors.quality_validator import (
    ValidationResult,
    ValidationStrictness,
    VideoValidator,
)

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
        validate_output: Whether to validate converted files.
        validation_strictness: How strictly to validate output.
        max_concurrent: Maximum concurrent conversions.
        delete_original: Whether to delete original after success.
        move_to_processed: Directory to move processed originals.
        move_to_failed: Directory to move failed files.
        queue_priority: Priority ordering for batch queue.
    """

    mode: ConversionMode = ConversionMode.HARDWARE
    quality: int = 45
    crf: int = 22
    preset: str = "medium"
    output_suffix: str = "_h265"
    preserve_metadata: bool = True
    validate_output: bool = True
    validation_strictness: ValidationStrictness = ValidationStrictness.STANDARD
    max_concurrent: int = 2
    delete_original: bool = False
    move_to_processed: Path | None = None
    move_to_failed: Path | None = None
    queue_priority: QueuePriority = QueuePriority.FIFO


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
        session_manager: Session state manager for persistence.
    """

    def __init__(
        self,
        config: OrchestratorConfig | None = None,
        converter_factory: ConverterFactory | None = None,
        validator: VideoValidator | None = None,
        session_manager: SessionStateManager | None = None,
        enable_session_persistence: bool = True,
    ) -> None:
        """Initialize the Orchestrator.

        Args:
            config: Optional configuration. Uses defaults if not provided.
            converter_factory: Optional converter factory.
            validator: Optional video validator.
            session_manager: Optional session state manager.
            enable_session_persistence: Whether to enable session persistence.
        """
        self.config = config or OrchestratorConfig()
        self.converter_factory = converter_factory or ConverterFactory()
        self.validator = validator or VideoValidator()
        self._enable_session_persistence = enable_session_persistence

        if enable_session_persistence:
            self.session_manager = session_manager or SessionStateManager()
        else:
            self.session_manager = None

        self._converter: BaseConverter | None = None
        self._cancelled = False
        self._paused = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused initially
        self._batch_status = BatchStatus.IDLE
        self._current_session_id: str | None = None
        self._tasks: list[ConversionTask] = []
        self._current_session: SessionState | None = None

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
                # Validation failed - clean up and report
                if output_path.exists():
                    output_path.unlink()
                result.success = False
                result.error_message = (
                    f"Validation failed: {', '.join(validation.errors)}"
                )
                result.warnings.extend(validation.warnings)
                return result

            result.warnings.extend(validation.warnings)

        # Stage 3: Cleanup
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
            else:
                task.status = ConversionStatus.FAILED
                task.error = result.error_message

                # Update session state
                if self.session_manager and self._current_session:
                    video_entry = self._find_video_entry(task.input_path)
                    if video_entry:
                        self.session_manager.mark_video_failed(
                            video_entry,
                            result.error_message or "Unknown error",
                        )

                # Move to failed directory if configured
                if self.config.move_to_failed and task.input_path.exists():
                    try:
                        dest = self.config.move_to_failed / task.input_path.name
                        self.config.move_to_failed.mkdir(parents=True, exist_ok=True)
                        task.input_path.rename(dest)
                    except OSError as e:
                        logger.warning(f"Could not move failed file: {e}")

            report.add_result(result)

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
