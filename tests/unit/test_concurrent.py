"""Unit tests for concurrent processing module."""

from __future__ import annotations

import asyncio
import tempfile
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_converter.core.concurrent import (
    AggregatedProgress,
    ConcurrentProcessor,
    JobProgress,
    ResourceLevel,
    ResourceMonitor,
    ResourceStatus,
)


class TestResourceLevel:
    """Tests for ResourceLevel enum."""

    def test_resource_levels_exist(self) -> None:
        """Test all resource levels exist."""
        assert ResourceLevel.LOW is not None
        assert ResourceLevel.NORMAL is not None
        assert ResourceLevel.HIGH is not None
        assert ResourceLevel.CRITICAL is not None


class TestResourceStatus:
    """Tests for ResourceStatus dataclass."""

    def test_default_values(self) -> None:
        """Test default resource status values."""
        status = ResourceStatus()
        assert status.cpu_percent == 0.0
        assert status.memory_percent == 0.0
        assert status.cpu_level == ResourceLevel.NORMAL
        assert status.memory_level == ResourceLevel.NORMAL
        assert status.recommended_concurrency == 2

    def test_custom_values(self) -> None:
        """Test custom resource status values."""
        status = ResourceStatus(
            cpu_percent=75.0,
            memory_percent=60.0,
            cpu_level=ResourceLevel.HIGH,
            memory_level=ResourceLevel.NORMAL,
            recommended_concurrency=1,
        )
        assert status.cpu_percent == 75.0
        assert status.memory_percent == 60.0
        assert status.cpu_level == ResourceLevel.HIGH
        assert status.recommended_concurrency == 1


class TestJobProgress:
    """Tests for JobProgress dataclass."""

    def test_default_values(self) -> None:
        """Test default job progress values."""
        progress = JobProgress(
            job_id=0,
            input_path=Path("test.mov"),
        )
        assert progress.job_id == 0
        assert progress.progress == 0.0
        assert progress.status == "pending"
        assert progress.started_at is None
        assert progress.message == ""

    def test_custom_values(self) -> None:
        """Test custom job progress values."""
        from datetime import datetime

        now = datetime.now()
        progress = JobProgress(
            job_id=5,
            input_path=Path("video.mp4"),
            progress=0.75,
            status="in_progress",
            started_at=now,
            message="Converting...",
        )
        assert progress.job_id == 5
        assert progress.progress == 0.75
        assert progress.status == "in_progress"
        assert progress.started_at == now


class TestAggregatedProgress:
    """Tests for AggregatedProgress dataclass."""

    def test_default_values(self) -> None:
        """Test default aggregated progress values."""
        progress = AggregatedProgress()
        assert progress.total_jobs == 0
        assert progress.completed_jobs == 0
        assert progress.in_progress_jobs == 0
        assert progress.pending_jobs == 0
        assert progress.overall_progress == 0.0
        assert progress.job_progresses == []
        assert progress.current_files == []

    def test_custom_values(self) -> None:
        """Test custom aggregated progress values."""
        job1 = JobProgress(job_id=0, input_path=Path("a.mov"))
        job2 = JobProgress(job_id=1, input_path=Path("b.mov"))

        progress = AggregatedProgress(
            total_jobs=5,
            completed_jobs=2,
            in_progress_jobs=2,
            pending_jobs=1,
            overall_progress=0.5,
            job_progresses=[job1, job2],
            current_files=["a.mov", "b.mov"],
        )
        assert progress.total_jobs == 5
        assert progress.completed_jobs == 2
        assert progress.overall_progress == 0.5
        assert len(progress.job_progresses) == 2


class TestResourceMonitor:
    """Tests for ResourceMonitor class."""

    def test_initialization(self) -> None:
        """Test resource monitor initialization."""
        monitor = ResourceMonitor()
        assert monitor is not None

    def test_get_status_returns_resource_status(self) -> None:
        """Test get_status returns ResourceStatus."""
        monitor = ResourceMonitor()
        status = monitor.get_status()
        assert isinstance(status, ResourceStatus)

    def test_categorize_level_low(self) -> None:
        """Test categorization of low resource level."""
        monitor = ResourceMonitor()
        level = monitor._categorize_level(20.0, 80.0, 95.0)
        assert level == ResourceLevel.LOW

    def test_categorize_level_normal(self) -> None:
        """Test categorization of normal resource level."""
        monitor = ResourceMonitor()
        level = monitor._categorize_level(50.0, 80.0, 95.0)
        assert level == ResourceLevel.NORMAL

    def test_categorize_level_high(self) -> None:
        """Test categorization of high resource level."""
        monitor = ResourceMonitor()
        level = monitor._categorize_level(85.0, 80.0, 95.0)
        assert level == ResourceLevel.HIGH

    def test_categorize_level_critical(self) -> None:
        """Test categorization of critical resource level."""
        monitor = ResourceMonitor()
        level = monitor._categorize_level(98.0, 80.0, 95.0)
        assert level == ResourceLevel.CRITICAL

    def test_calculate_recommended_concurrency_critical(self) -> None:
        """Test recommended concurrency at critical level."""
        monitor = ResourceMonitor()
        recommended = monitor._calculate_recommended_concurrency(
            ResourceLevel.CRITICAL, ResourceLevel.NORMAL
        )
        assert recommended == 1

    def test_calculate_recommended_concurrency_high(self) -> None:
        """Test recommended concurrency at high level."""
        monitor = ResourceMonitor()
        recommended = monitor._calculate_recommended_concurrency(
            ResourceLevel.HIGH, ResourceLevel.NORMAL
        )
        assert recommended >= 1


class TestConcurrentProcessor:
    """Tests for ConcurrentProcessor class."""

    def test_initialization_defaults(self) -> None:
        """Test concurrent processor initialization with defaults."""
        processor = ConcurrentProcessor()
        assert processor.max_concurrent == 2
        assert processor is not None

    def test_initialization_custom(self) -> None:
        """Test concurrent processor initialization with custom values."""
        processor = ConcurrentProcessor(
            max_concurrent=4,
            enable_resource_monitoring=False,
            adaptive_concurrency=True,
        )
        assert processor.max_concurrent == 4

    def test_max_concurrent_property(self) -> None:
        """Test max_concurrent property getter and setter."""
        processor = ConcurrentProcessor(max_concurrent=2)
        assert processor.max_concurrent == 2

        processor.max_concurrent = 5
        assert processor.max_concurrent == 5

        # Minimum is 1
        processor.max_concurrent = 0
        assert processor.max_concurrent == 1

    def test_get_resource_status_with_monitoring(self) -> None:
        """Test get_resource_status with monitoring enabled."""
        processor = ConcurrentProcessor(enable_resource_monitoring=True)
        status = processor.get_resource_status()
        assert status is not None
        assert isinstance(status, ResourceStatus)

    def test_get_resource_status_without_monitoring(self) -> None:
        """Test get_resource_status with monitoring disabled."""
        processor = ConcurrentProcessor(enable_resource_monitoring=False)
        status = processor.get_resource_status()
        assert status is None

    def test_get_aggregated_progress_empty(self) -> None:
        """Test get_aggregated_progress with no jobs."""
        processor = ConcurrentProcessor()
        progress = processor.get_aggregated_progress()
        assert progress.total_jobs == 0
        assert progress.overall_progress == 0.0

    def test_cancel(self) -> None:
        """Test cancel method sets flag."""
        processor = ConcurrentProcessor()
        assert processor._cancelled is False
        processor.cancel()
        assert processor._cancelled is True

    def test_reset(self) -> None:
        """Test reset clears state."""
        processor = ConcurrentProcessor()
        processor._cancelled = True
        processor._total_jobs = 10
        processor._completed_count = 5

        processor.reset()
        assert processor._cancelled is False
        assert processor._total_jobs == 0
        assert processor._completed_count == 0

    @pytest.mark.asyncio
    async def test_process_batch_empty(self) -> None:
        """Test process_batch with empty list."""
        processor = ConcurrentProcessor()

        async def dummy_processor(item, callback):
            return item

        results = await processor.process_batch([], dummy_processor)
        assert results == []

    @pytest.mark.asyncio
    async def test_process_batch_single_item(self) -> None:
        """Test process_batch with single item."""
        processor = ConcurrentProcessor(max_concurrent=2)

        async def dummy_processor(item, callback):
            callback(1.0)  # Report complete
            return item * 2

        results = await processor.process_batch([5], dummy_processor)
        assert results == [10]

    @pytest.mark.asyncio
    async def test_process_batch_multiple_items(self) -> None:
        """Test process_batch with multiple items."""
        processor = ConcurrentProcessor(max_concurrent=2)
        execution_order = []

        async def tracking_processor(item, callback):
            execution_order.append(f"start_{item}")
            await asyncio.sleep(0.01)  # Small delay
            callback(1.0)
            execution_order.append(f"end_{item}")
            return item * 2

        results = await processor.process_batch([1, 2, 3], tracking_processor)
        assert len(results) == 3
        assert results == [2, 4, 6]
        # All items should be processed
        assert len(execution_order) == 6

    @pytest.mark.asyncio
    async def test_process_batch_respects_concurrency_limit(self) -> None:
        """Test process_batch respects max_concurrent limit."""
        processor = ConcurrentProcessor(max_concurrent=2)
        max_concurrent_seen = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def counting_processor(item, callback):
            nonlocal max_concurrent_seen, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent_seen:
                    max_concurrent_seen = current_concurrent

            await asyncio.sleep(0.05)  # Simulate work
            callback(1.0)

            async with lock:
                current_concurrent -= 1

            return item

        results = await processor.process_batch([1, 2, 3, 4], counting_processor)
        assert len(results) == 4
        # Should never exceed max_concurrent
        assert max_concurrent_seen <= 2

    @pytest.mark.asyncio
    async def test_process_batch_handles_exceptions(self) -> None:
        """Test process_batch handles exceptions gracefully."""
        processor = ConcurrentProcessor(max_concurrent=2)

        async def failing_processor(item, callback):
            if item == 2:
                raise ValueError("Test error")
            return item

        results = await processor.process_batch([1, 2, 3], failing_processor)
        assert len(results) == 3
        assert results[0] == 1
        assert results[1] is None  # Failed item
        assert results[2] == 3

    @pytest.mark.asyncio
    async def test_process_batch_progress_callback(self) -> None:
        """Test process_batch calls progress callback."""
        processor = ConcurrentProcessor(max_concurrent=1)
        progress_updates = []

        def on_progress(agg_progress: AggregatedProgress) -> None:
            progress_updates.append(agg_progress)

        async def dummy_processor(item, callback):
            callback(0.5)
            await asyncio.sleep(0.01)
            callback(1.0)
            return item

        await processor.process_batch([1, 2], dummy_processor, on_progress)
        assert len(progress_updates) > 0

    @pytest.mark.asyncio
    async def test_process_batch_with_path_items(self) -> None:
        """Test process_batch extracts input_path from items."""
        processor = ConcurrentProcessor(max_concurrent=2)

        @dataclass
        class MockTask:
            input_path: Path
            value: int

        tasks = [
            MockTask(input_path=Path("a.mov"), value=1),
            MockTask(input_path=Path("b.mov"), value=2),
        ]

        async def path_processor(item, callback):
            return item.value * 2

        results = await processor.process_batch(tasks, path_processor)
        assert results == [2, 4]

        # Check that paths were extracted
        agg = processor.get_aggregated_progress()
        assert agg.total_jobs == 2


class TestConcurrentProcessorIntegration:
    """Integration tests for ConcurrentProcessor."""

    @pytest.mark.asyncio
    async def test_full_workflow(self) -> None:
        """Test complete concurrent processing workflow."""
        processor = ConcurrentProcessor(max_concurrent=2)
        processed_items = []

        async def workflow_processor(item, callback):
            callback(0.25)
            await asyncio.sleep(0.01)
            callback(0.50)
            await asyncio.sleep(0.01)
            callback(0.75)
            await asyncio.sleep(0.01)
            callback(1.0)
            processed_items.append(item)
            return f"processed_{item}"

        items = ["a", "b", "c", "d"]
        results = await processor.process_batch(items, workflow_processor)

        assert len(results) == 4
        assert all(r.startswith("processed_") for r in results)
        assert len(processed_items) == 4

        # Verify aggregated progress at end
        agg = processor.get_aggregated_progress()
        assert agg.completed_jobs == 4
        assert agg.overall_progress == 1.0

    @pytest.mark.asyncio
    async def test_cancel_during_processing(self) -> None:
        """Test cancellation during batch processing."""
        processor = ConcurrentProcessor(max_concurrent=1)
        started_items = []

        async def slow_processor(item, callback):
            started_items.append(item)
            if item == 2:
                processor.cancel()
            await asyncio.sleep(0.01)
            return item

        # Note: Due to async nature, some items may still process
        try:
            results = await processor.process_batch([1, 2, 3, 4], slow_processor)
        except asyncio.CancelledError:
            pass  # Expected

        # At least first two items should have started
        assert 1 in started_items
        assert 2 in started_items
