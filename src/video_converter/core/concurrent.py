"""Concurrent processing support for video conversion.

This module implements concurrent video processing with configurable
parallelism, resource management, and aggregated progress tracking.

SDS Reference: SDS-C01-004
SRS Reference: SRS-604 (Concurrent Processing Support)

Example:
    >>> from video_converter.core.concurrent import ConcurrentProcessor
    >>> from video_converter.core.types import ConversionRequest
    >>>
    >>> processor = ConcurrentProcessor(max_concurrent=2)
    >>>
    >>> async def convert_video(request):
    ...     # Perform conversion
    ...     return result
    >>>
    >>> requests = [request1, request2, request3]
    >>> results = await processor.process_batch(requests, convert_video)
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


class ResourceLevel(Enum):
    """System resource utilization level.

    Attributes:
        LOW: Resources are underutilized.
        NORMAL: Resources are at normal levels.
        HIGH: Resources are heavily utilized.
        CRITICAL: Resources are at critical levels.
    """

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ResourceStatus:
    """Current system resource status.

    Attributes:
        cpu_percent: Current CPU utilization percentage.
        memory_percent: Current memory utilization percentage.
        cpu_level: Categorized CPU level.
        memory_level: Categorized memory level.
        recommended_concurrency: Suggested concurrent job count.
    """

    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    cpu_level: ResourceLevel = ResourceLevel.NORMAL
    memory_level: ResourceLevel = ResourceLevel.NORMAL
    recommended_concurrency: int = 2


@dataclass
class JobProgress:
    """Progress information for a single concurrent job.

    Attributes:
        job_id: Unique identifier for this job.
        input_path: Path to the input file.
        progress: Current progress (0.0-1.0).
        status: Current job status.
        started_at: When the job started.
        message: Current status message.
    """

    job_id: int
    input_path: Path
    progress: float = 0.0
    status: str = "pending"
    started_at: datetime | None = None
    message: str = ""


@dataclass
class AggregatedProgress:
    """Aggregated progress for all concurrent jobs.

    Attributes:
        total_jobs: Total number of jobs.
        completed_jobs: Number of completed jobs.
        in_progress_jobs: Number of jobs currently running.
        pending_jobs: Number of pending jobs.
        overall_progress: Overall progress (0.0-1.0).
        job_progresses: Progress of individual jobs.
        current_files: Names of files currently being processed.
    """

    total_jobs: int = 0
    completed_jobs: int = 0
    in_progress_jobs: int = 0
    pending_jobs: int = 0
    overall_progress: float = 0.0
    job_progresses: list[JobProgress] = field(default_factory=list)
    current_files: list[str] = field(default_factory=list)


class ResourceMonitor:
    """Monitors system resources for concurrent processing.

    Provides CPU and memory utilization tracking to help manage
    concurrent job limits dynamically.
    """

    # Thresholds for resource levels
    CPU_HIGH_THRESHOLD = 80.0
    CPU_CRITICAL_THRESHOLD = 95.0
    MEMORY_HIGH_THRESHOLD = 75.0
    MEMORY_CRITICAL_THRESHOLD = 90.0

    def __init__(self) -> None:
        """Initialize the resource monitor."""
        self._psutil_available = False
        try:
            import psutil

            self._psutil = psutil
            self._psutil_available = True
        except ImportError:
            logger.debug("psutil not available, resource monitoring disabled")

    def get_status(self) -> ResourceStatus:
        """Get current resource status.

        Returns:
            ResourceStatus with current utilization levels.
        """
        if not self._psutil_available:
            return ResourceStatus()

        try:
            cpu_percent = self._psutil.cpu_percent(interval=0.1)
            memory = self._psutil.virtual_memory()
            memory_percent = memory.percent

            cpu_level = self._categorize_level(
                cpu_percent,
                self.CPU_HIGH_THRESHOLD,
                self.CPU_CRITICAL_THRESHOLD,
            )

            memory_level = self._categorize_level(
                memory_percent,
                self.MEMORY_HIGH_THRESHOLD,
                self.MEMORY_CRITICAL_THRESHOLD,
            )

            recommended = self._calculate_recommended_concurrency(cpu_level, memory_level)

            return ResourceStatus(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                cpu_level=cpu_level,
                memory_level=memory_level,
                recommended_concurrency=recommended,
            )
        except Exception as e:
            logger.debug(f"Error getting resource status: {e}")
            return ResourceStatus()

    def _categorize_level(
        self, value: float, high_threshold: float, critical_threshold: float
    ) -> ResourceLevel:
        """Categorize a resource utilization value.

        Args:
            value: The utilization percentage.
            high_threshold: Threshold for HIGH level.
            critical_threshold: Threshold for CRITICAL level.

        Returns:
            The corresponding ResourceLevel.
        """
        if value >= critical_threshold:
            return ResourceLevel.CRITICAL
        if value >= high_threshold:
            return ResourceLevel.HIGH
        if value < 30.0:
            return ResourceLevel.LOW
        return ResourceLevel.NORMAL

    def _calculate_recommended_concurrency(
        self, cpu_level: ResourceLevel, memory_level: ResourceLevel
    ) -> int:
        """Calculate recommended concurrent job count.

        Args:
            cpu_level: Current CPU utilization level.
            memory_level: Current memory utilization level.

        Returns:
            Recommended number of concurrent jobs.
        """
        # Get CPU count for baseline
        try:
            cpu_count = os.cpu_count() or 2
        except Exception:
            cpu_count = 2

        # Start with a reasonable default based on CPU count
        # For video encoding, 2 is usually optimal due to hardware encoder limits
        base_concurrency = min(cpu_count, 4)

        # Reduce based on resource levels
        if cpu_level == ResourceLevel.CRITICAL or memory_level == ResourceLevel.CRITICAL:
            return 1
        if cpu_level == ResourceLevel.HIGH or memory_level == ResourceLevel.HIGH:
            return max(1, base_concurrency // 2)

        return base_concurrency


class ConcurrentProcessor:
    """Manages concurrent video processing with resource awareness.

    This class provides:
    - Configurable maximum concurrent jobs
    - Resource monitoring and adaptive concurrency
    - Aggregated progress tracking
    - Thread-safe job management
    """

    def __init__(
        self,
        max_concurrent: int = 2,
        enable_resource_monitoring: bool = True,
        adaptive_concurrency: bool = False,
    ) -> None:
        """Initialize the concurrent processor.

        Args:
            max_concurrent: Maximum number of concurrent jobs.
            enable_resource_monitoring: Whether to monitor system resources.
            adaptive_concurrency: Whether to adjust concurrency based on resources.
        """
        self._max_concurrent = max(1, max_concurrent)
        self._enable_resource_monitoring = enable_resource_monitoring
        self._adaptive_concurrency = adaptive_concurrency

        self._semaphore: asyncio.Semaphore | None = None
        self._resource_monitor = ResourceMonitor() if enable_resource_monitoring else None
        self._lock = threading.Lock()

        self._job_progresses: dict[int, JobProgress] = {}
        self._completed_count = 0
        self._total_jobs = 0
        self._cancelled = False

    @property
    def max_concurrent(self) -> int:
        """Get maximum concurrent job count."""
        return self._max_concurrent

    @max_concurrent.setter
    def max_concurrent(self, value: int) -> None:
        """Set maximum concurrent job count."""
        self._max_concurrent = max(1, value)

    def get_resource_status(self) -> ResourceStatus | None:
        """Get current resource status.

        Returns:
            ResourceStatus if monitoring enabled, None otherwise.
        """
        if self._resource_monitor:
            return self._resource_monitor.get_status()
        return None

    def get_aggregated_progress(self) -> AggregatedProgress:
        """Get aggregated progress for all jobs.

        Returns:
            AggregatedProgress with current state of all jobs.
        """
        with self._lock:
            job_list = list(self._job_progresses.values())
            in_progress = [j for j in job_list if j.status == "in_progress"]
            pending = [j for j in job_list if j.status == "pending"]

            # Calculate overall progress
            if self._total_jobs > 0:
                completed_progress = self._completed_count
                in_progress_sum = sum(j.progress for j in in_progress)
                overall = (completed_progress + in_progress_sum) / self._total_jobs
            else:
                overall = 0.0

            return AggregatedProgress(
                total_jobs=self._total_jobs,
                completed_jobs=self._completed_count,
                in_progress_jobs=len(in_progress),
                pending_jobs=len(pending),
                overall_progress=overall,
                job_progresses=job_list,
                current_files=[j.input_path.name for j in in_progress],
            )

    def cancel(self) -> None:
        """Cancel all pending and running jobs."""
        self._cancelled = True

    def reset(self) -> None:
        """Reset the processor state for a new batch."""
        with self._lock:
            self._job_progresses.clear()
            self._completed_count = 0
            self._total_jobs = 0
            self._cancelled = False

    async def process_batch(
        self,
        items: list[T],
        processor: Callable[[T, Callable[[float], None]], Awaitable[R]],
        on_progress: Callable[[AggregatedProgress], None] | None = None,
    ) -> list[R | None]:
        """Process a batch of items concurrently.

        Args:
            items: List of items to process.
            processor: Async function that processes an item.
                      Takes (item, progress_callback) and returns result.
            on_progress: Optional callback for aggregated progress updates.

        Returns:
            List of results in the same order as input items.
        """
        self.reset()
        self._total_jobs = len(items)

        if not items:
            return []

        # Determine effective concurrency
        effective_concurrency = self._max_concurrent
        if self._adaptive_concurrency and self._resource_monitor:
            status = self._resource_monitor.get_status()
            effective_concurrency = min(self._max_concurrent, status.recommended_concurrency)

        self._semaphore = asyncio.Semaphore(effective_concurrency)

        logger.info(
            f"Starting batch processing: {len(items)} jobs, max concurrent: {effective_concurrency}"
        )

        # Create tasks for all items
        tasks = []
        for i, item in enumerate(items):
            self._create_job_progress(i, item)
            task = asyncio.create_task(
                self._process_with_semaphore(i, item, processor, on_progress)
            )
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        final_results: list[R | None] = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                logger.error(f"Job {i} failed with exception: {result}")
                final_results.append(None)
            else:
                final_results.append(result)

        return final_results

    def _create_job_progress(self, job_id: int, item: T) -> JobProgress:
        """Create a job progress entry.

        Args:
            job_id: The job identifier.
            item: The item being processed.

        Returns:
            New JobProgress instance.
        """
        input_path = Path("unknown")
        if hasattr(item, "input_path"):
            input_path = item.input_path
        elif hasattr(item, "path"):
            input_path = item.path
        elif isinstance(item, Path):
            input_path = item

        progress = JobProgress(
            job_id=job_id,
            input_path=input_path,
            status="pending",
        )

        with self._lock:
            self._job_progresses[job_id] = progress

        return progress

    async def _process_with_semaphore(
        self,
        job_id: int,
        item: T,
        processor: Callable[[T, Callable[[float], None]], Awaitable[R]],
        on_progress: Callable[[AggregatedProgress], None] | None,
    ) -> R:
        """Process an item with semaphore control.

        Args:
            job_id: The job identifier.
            item: The item to process.
            processor: The processing function.
            on_progress: Optional progress callback.

        Returns:
            The processing result.
        """
        assert self._semaphore is not None, "Semaphore not initialized"
        async with self._semaphore:
            if self._cancelled:
                raise asyncio.CancelledError("Batch processing cancelled")

            # Update status to in_progress
            with self._lock:
                if job_id in self._job_progresses:
                    self._job_progresses[job_id].status = "in_progress"
                    self._job_progresses[job_id].started_at = datetime.now()

            # Emit progress update
            if on_progress:
                on_progress(self.get_aggregated_progress())

            try:
                # Create progress callback for this job
                def job_progress_callback(progress: float) -> None:
                    with self._lock:
                        if job_id in self._job_progresses:
                            self._job_progresses[job_id].progress = progress
                    if on_progress:
                        on_progress(self.get_aggregated_progress())

                # Process the item
                result = await processor(item, job_progress_callback)

                # Mark as completed
                with self._lock:
                    if job_id in self._job_progresses:
                        self._job_progresses[job_id].status = "completed"
                        self._job_progresses[job_id].progress = 1.0
                    self._completed_count += 1

                # Emit final progress update
                if on_progress:
                    on_progress(self.get_aggregated_progress())

                return result

            except Exception as e:
                # Mark as failed
                with self._lock:
                    if job_id in self._job_progresses:
                        self._job_progresses[job_id].status = "failed"
                        self._job_progresses[job_id].message = str(e)
                    self._completed_count += 1
                raise
