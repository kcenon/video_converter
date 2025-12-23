"""Conversion service for bridging GUI with backend.

This module provides the ConversionService class that connects the GUI
with the video conversion backend, handling progress updates, queue
management, and asynchronous conversion execution.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QThread, Signal, Slot

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


@dataclass
class ConversionTask:
    """A conversion task in the queue.

    Attributes:
        task_id: Unique identifier for this task.
        file_path: Path to the input video file.
        file_name: Name of the video file.
        file_size: Size of the file in bytes.
        output_path: Path for the output file.
        settings: Conversion settings dictionary.
        status: Current status of the task.
        progress: Current progress percentage (0-100).
        eta_seconds: Estimated time remaining in seconds.
        speed: Current encoding speed string.
        started_at: When the conversion started.
        completed_at: When the conversion finished.
        error: Error message if failed.
    """

    task_id: str
    file_path: Path
    file_name: str
    file_size: int
    output_path: Path | None = None
    settings: dict | None = None
    status: str = "queued"
    progress: float = 0.0
    eta_seconds: int | None = None
    speed: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


class ConversionWorker(QObject):
    """Worker for running conversions in a separate thread.

    This worker handles the actual conversion process in a background
    thread, emitting signals for progress updates and completion.

    Signals:
        progress_updated: Emitted when conversion progress changes.
        conversion_complete: Emitted when a conversion finishes.
        conversion_failed: Emitted when a conversion fails.
    """

    progress_updated = Signal(str, float, object, object)  # task_id, progress, eta, speed
    conversion_complete = Signal(str, object)  # task_id, result
    conversion_failed = Signal(str, str)  # task_id, error_message

    def __init__(self) -> None:
        """Initialize the conversion worker."""
        super().__init__()
        self._orchestrator = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._current_task: ConversionTask | None = None

    def _get_orchestrator(self):
        """Get or create the orchestrator instance.

        Returns:
            Orchestrator instance.
        """
        if self._orchestrator is None:
            from video_converter.core.config import Config
            from video_converter.core.orchestrator import Orchestrator, OrchestratorConfig
            from video_converter.core.types import ConversionMode

            app_config = Config.load()

            # Resolve conversion mode
            conv_mode = ConversionMode.HARDWARE
            if app_config.encoding.mode == "software":
                conv_mode = ConversionMode.SOFTWARE

            config = OrchestratorConfig(
                mode=conv_mode,
                quality=app_config.encoding.quality,
                crf=app_config.encoding.crf,
                preset=app_config.encoding.preset,
                validate_output=app_config.processing.validate_quality,
                preserve_timestamps=True,
                preserve_metadata=True,
                move_to_processed=app_config.paths.processed if app_config.processing.move_processed else None,
                move_to_failed=app_config.paths.failed if app_config.processing.move_failed else None,
                check_disk_space=app_config.processing.check_disk_space,
                min_free_space=int(app_config.processing.min_free_space_gb * 1024 * 1024 * 1024),
                enable_vmaf=app_config.vmaf.enabled,
                vmaf_threshold=app_config.vmaf.threshold,
                vmaf_sample_interval=app_config.vmaf.sample_interval,
                vmaf_fail_action=app_config.vmaf.fail_action,
            )
            self._orchestrator = Orchestrator(config=config)
        return self._orchestrator

    def _on_progress(self, progress) -> None:
        """Handle progress updates from the orchestrator.

        Args:
            progress: ConversionProgress object from backend.
        """
        if self._current_task is None:
            return

        # Extract progress information
        progress_percent = progress.overall_progress * 100
        eta_seconds = None
        speed = None

        if progress.estimated_time_remaining is not None:
            eta_seconds = int(progress.estimated_time_remaining)

        if progress.message:
            # Try to extract speed from message
            if "Speed:" in progress.message:
                speed = progress.message.split("Speed:")[-1].strip()

        self.progress_updated.emit(
            self._current_task.task_id,
            progress_percent,
            eta_seconds,
            speed,
        )

    @Slot(object)
    def run_conversion(self, task: ConversionTask) -> None:
        """Run a conversion task.

        Args:
            task: The conversion task to run.
        """
        self._current_task = task
        task.status = "converting"
        task.started_at = datetime.now()

        try:
            orchestrator = self._get_orchestrator()

            # Create event loop for this thread if needed
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)

            # Apply settings if provided
            if task.settings:
                self._apply_settings(orchestrator, task.settings)

            # Run the conversion
            result = self._loop.run_until_complete(
                orchestrator.convert_single(
                    input_path=task.file_path,
                    output_path=task.output_path,
                    on_progress=self._on_progress,
                )
            )

            task.completed_at = datetime.now()

            if result.success:
                task.status = "completed"
                task.progress = 100.0
                self.conversion_complete.emit(task.task_id, result)
            else:
                task.status = "failed"
                task.error = result.error_message or "Unknown error"
                self.conversion_failed.emit(task.task_id, task.error)

        except Exception as e:
            logger.exception(f"Conversion failed for {task.file_name}")
            task.status = "failed"
            task.error = str(e)
            task.completed_at = datetime.now()
            self.conversion_failed.emit(task.task_id, str(e))

        finally:
            self._current_task = None

    def _apply_settings(self, orchestrator, settings: dict) -> None:
        """Apply conversion settings to the orchestrator.

        Args:
            orchestrator: Orchestrator instance.
            settings: Settings dictionary from GUI.
        """
        from video_converter.core.types import ConversionMode

        config = orchestrator.config

        # Encoder selection
        encoder = settings.get("encoder", "")
        if "Hardware" in encoder or "VideoToolbox" in encoder:
            config.mode = ConversionMode.HARDWARE
        elif "Software" in encoder or "libx265" in encoder:
            config.mode = ConversionMode.SOFTWARE

        # Quality (CRF)
        if "quality" in settings:
            config.crf = settings["quality"]

        # Thread count
        if "threads" in settings and settings["threads"] > 1:
            config.max_concurrent = 1  # Single file, but set thread hint

    def cancel(self) -> None:
        """Cancel the current conversion."""
        if self._orchestrator:
            self._orchestrator.cancel()


class ConversionService(QObject):
    """Service for managing video conversions.

    This service bridges the GUI with the conversion backend,
    managing the conversion queue and providing progress updates.

    Signals:
        task_added: Emitted when a task is added to the queue.
        task_started: Emitted when a task starts converting.
        progress_updated: Emitted when task progress changes.
        task_completed: Emitted when a task completes successfully.
        task_failed: Emitted when a task fails.
        task_cancelled: Emitted when a task is cancelled.
        queue_updated: Emitted when the queue state changes.
        all_completed: Emitted when all tasks are finished.
    """

    task_added = Signal(str, str, str)  # task_id, file_name, file_size
    task_started = Signal(str)  # task_id
    progress_updated = Signal(str, float, object, object)  # task_id, progress, eta, speed
    task_completed = Signal(str, object)  # task_id, result
    task_failed = Signal(str, str)  # task_id, error
    task_cancelled = Signal(str)  # task_id
    queue_updated = Signal()
    all_completed = Signal(int, int)  # successful, failed

    def __init__(self, parent: QObject | None = None) -> None:
        """Initialize the conversion service.

        Args:
            parent: Parent QObject.
        """
        super().__init__(parent)

        self._tasks: dict[str, ConversionTask] = {}
        self._queue: list[str] = []  # Task IDs in queue order
        self._is_processing = False
        self._is_paused = False

        # Worker thread setup
        self._worker_thread = QThread()
        self._worker = ConversionWorker()
        self._worker.moveToThread(self._worker_thread)

        # Connect worker signals
        self._worker.progress_updated.connect(self._on_worker_progress)
        self._worker.conversion_complete.connect(self._on_worker_complete)
        self._worker.conversion_failed.connect(self._on_worker_failed)

        self._worker_thread.start()

        # Statistics
        self._completed_count = 0
        self._failed_count = 0
        self._total_original_size = 0
        self._total_converted_size = 0

    def add_task(
        self,
        file_path: str | Path,
        output_path: str | Path | None = None,
        settings: dict | None = None,
    ) -> str:
        """Add a conversion task to the queue.

        Args:
            file_path: Path to the input video file.
            output_path: Path for the output file. Auto-generated if None.
            settings: Conversion settings dictionary.

        Returns:
            Task ID for the new task.
        """
        file_path = Path(file_path)

        # Generate task ID
        task_id = str(uuid.uuid4())[:8]

        # Get file info
        file_name = file_path.name
        file_size = file_path.stat().st_size if file_path.exists() else 0

        # Generate output path if not provided
        if output_path is None:
            output_dir = settings.get("output_dir") if settings else None
            if output_dir:
                output_path = Path(output_dir) / f"{file_path.stem}_h265.mp4"
            else:
                output_path = file_path.parent / f"{file_path.stem}_h265.mp4"
        else:
            output_path = Path(output_path)

        # Create task
        task = ConversionTask(
            task_id=task_id,
            file_path=file_path,
            file_name=file_name,
            file_size=file_size,
            output_path=output_path,
            settings=settings,
        )

        self._tasks[task_id] = task
        self._queue.append(task_id)

        # Format file size for display
        size_str = self._format_size(file_size)

        self.task_added.emit(task_id, file_name, size_str)
        self.queue_updated.emit()

        # Start processing if not already
        if not self._is_processing and not self._is_paused:
            self._process_next()

        return task_id

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a specific task.

        Args:
            task_id: ID of the task to cancel.

        Returns:
            True if cancelled, False if not found or already completed.
        """
        if task_id not in self._tasks:
            return False

        task = self._tasks[task_id]

        if task.status == "converting":
            # Cancel active conversion
            self._worker.cancel()
            task.status = "cancelled"
            self.task_cancelled.emit(task_id)
        elif task.status == "queued":
            # Remove from queue
            if task_id in self._queue:
                self._queue.remove(task_id)
            task.status = "cancelled"
            self.task_cancelled.emit(task_id)
        else:
            return False

        self.queue_updated.emit()
        return True

    def cancel_all(self) -> None:
        """Cancel all pending and active tasks."""
        # Cancel current conversion
        self._worker.cancel()

        # Cancel all queued tasks
        for task_id in list(self._queue):
            if task_id in self._tasks:
                self._tasks[task_id].status = "cancelled"
                self.task_cancelled.emit(task_id)

        self._queue.clear()
        self._is_processing = False
        self.queue_updated.emit()

    def pause_all(self) -> None:
        """Pause processing of the queue."""
        self._is_paused = True
        self.queue_updated.emit()

    def resume_all(self) -> None:
        """Resume processing of the queue."""
        self._is_paused = False
        if not self._is_processing:
            self._process_next()
        self.queue_updated.emit()

    def get_task(self, task_id: str) -> ConversionTask | None:
        """Get a task by ID.

        Args:
            task_id: Task ID.

        Returns:
            Task object or None if not found.
        """
        return self._tasks.get(task_id)

    def get_queue_status(self) -> dict:
        """Get current queue status.

        Returns:
            Dictionary with queue statistics.
        """
        queued = sum(1 for t in self._tasks.values() if t.status == "queued")
        converting = sum(1 for t in self._tasks.values() if t.status == "converting")
        completed = sum(1 for t in self._tasks.values() if t.status == "completed")
        failed = sum(1 for t in self._tasks.values() if t.status == "failed")

        return {
            "total": len(self._tasks),
            "queued": queued,
            "converting": converting,
            "completed": completed,
            "failed": failed,
            "is_processing": self._is_processing,
            "is_paused": self._is_paused,
        }

    def get_statistics(self) -> dict:
        """Get conversion statistics.

        Returns:
            Dictionary with conversion statistics.
        """
        return {
            "completed": self._completed_count,
            "failed": self._failed_count,
            "total_original_size": self._total_original_size,
            "total_converted_size": self._total_converted_size,
            "total_saved": self._total_original_size - self._total_converted_size,
        }

    def clear_completed(self) -> None:
        """Remove completed tasks from the list."""
        completed_ids = [
            task_id
            for task_id, task in self._tasks.items()
            if task.status in ("completed", "failed", "cancelled")
        ]
        for task_id in completed_ids:
            del self._tasks[task_id]
            if task_id in self._queue:
                self._queue.remove(task_id)

        self.queue_updated.emit()

    def _process_next(self) -> None:
        """Process the next task in the queue."""
        if self._is_paused:
            return

        if not self._queue:
            self._is_processing = False
            if self._completed_count > 0 or self._failed_count > 0:
                self.all_completed.emit(self._completed_count, self._failed_count)
            return

        self._is_processing = True

        # Get next task
        task_id = self._queue[0]
        task = self._tasks.get(task_id)

        if task is None or task.status != "queued":
            # Skip invalid tasks
            self._queue.pop(0)
            self._process_next()
            return

        # Start conversion
        self.task_started.emit(task_id)

        # Use QMetaObject.invokeMethod for thread-safe call
        from PySide6.QtCore import Q_ARG, QMetaObject, Qt

        QMetaObject.invokeMethod(
            self._worker,
            "run_conversion",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(object, task),
        )

    @Slot(str, float, object, object)
    def _on_worker_progress(
        self,
        task_id: str,
        progress: float,
        eta_seconds: int | None,
        speed: str | None,
    ) -> None:
        """Handle progress update from worker.

        Args:
            task_id: Task ID.
            progress: Progress percentage.
            eta_seconds: Estimated time remaining.
            speed: Encoding speed string.
        """
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.progress = progress
            task.eta_seconds = eta_seconds
            task.speed = speed

        self.progress_updated.emit(task_id, progress, eta_seconds, speed)

    @Slot(str, object)
    def _on_worker_complete(self, task_id: str, result) -> None:
        """Handle conversion completion from worker.

        Args:
            task_id: Task ID.
            result: ConversionResult object.
        """
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.status = "completed"
            task.progress = 100.0

            # Update statistics
            self._completed_count += 1
            if result:
                self._total_original_size += result.original_size
                self._total_converted_size += result.converted_size

        # Remove from queue
        if task_id in self._queue:
            self._queue.remove(task_id)

        self.task_completed.emit(task_id, result)
        self.queue_updated.emit()

        # Process next task
        self._process_next()

    @Slot(str, str)
    def _on_worker_failed(self, task_id: str, error: str) -> None:
        """Handle conversion failure from worker.

        Args:
            task_id: Task ID.
            error: Error message.
        """
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.status = "failed"
            task.error = error

            # Update statistics
            self._failed_count += 1

        # Remove from queue
        if task_id in self._queue:
            self._queue.remove(task_id)

        self.task_failed.emit(task_id, error)
        self.queue_updated.emit()

        # Process next task
        self._process_next()

    def _format_size(self, size_bytes: int) -> str:
        """Format file size for display.

        Args:
            size_bytes: Size in bytes.

        Returns:
            Human-readable size string.
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    def shutdown(self) -> None:
        """Shutdown the service and cleanup resources."""
        self.cancel_all()
        self._worker_thread.quit()
        self._worker_thread.wait()
