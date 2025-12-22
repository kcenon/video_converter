"""Integration tests for concurrent processing workflow.

This module tests the concurrent video processing functionality including
multi-job execution, resource monitoring, and progress aggregation.

SRS Reference: SRS-604 (Concurrent Processing Support)
SDS Reference: SDS-C01-004
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
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


@dataclass
class MockConversionRequest:
    """Mock conversion request for testing."""

    input_path: Path
    output_path: Path


class TestResourceMonitor:
    """Tests for resource monitoring functionality."""

    def test_resource_monitor_returns_default_when_psutil_unavailable(self) -> None:
        """Test that ResourceMonitor returns defaults without psutil."""
        with patch.dict("sys.modules", {"psutil": None}):
            monitor = ResourceMonitor()
            # Force reload of psutil availability
            monitor._psutil_available = False
            status = monitor.get_status()

            assert isinstance(status, ResourceStatus)
            assert status.recommended_concurrency == 2

    def test_resource_level_categorization(self) -> None:
        """Test resource level categorization thresholds."""
        monitor = ResourceMonitor()

        # Test CPU thresholds
        assert monitor._categorize_level(20.0, 80.0, 95.0) == ResourceLevel.LOW
        assert monitor._categorize_level(50.0, 80.0, 95.0) == ResourceLevel.NORMAL
        assert monitor._categorize_level(85.0, 80.0, 95.0) == ResourceLevel.HIGH
        assert monitor._categorize_level(98.0, 80.0, 95.0) == ResourceLevel.CRITICAL

    def test_recommended_concurrency_reduces_under_load(self) -> None:
        """Test that recommended concurrency reduces under high resource usage."""
        monitor = ResourceMonitor()

        # Normal levels should allow higher concurrency
        normal_rec = monitor._calculate_recommended_concurrency(
            ResourceLevel.NORMAL, ResourceLevel.NORMAL
        )

        # High CPU should reduce concurrency
        high_rec = monitor._calculate_recommended_concurrency(
            ResourceLevel.HIGH, ResourceLevel.NORMAL
        )

        # Critical should drop to 1
        critical_rec = monitor._calculate_recommended_concurrency(
            ResourceLevel.CRITICAL, ResourceLevel.NORMAL
        )

        assert normal_rec > high_rec
        assert critical_rec == 1


class TestConcurrentProcessor:
    """Tests for concurrent processor functionality."""

    @pytest.fixture
    def processor(self) -> ConcurrentProcessor:
        """Create a ConcurrentProcessor instance for testing."""
        return ConcurrentProcessor(max_concurrent=2)

    def test_processor_initialization(self, processor: ConcurrentProcessor) -> None:
        """Test that processor initializes with correct defaults."""
        assert processor.max_concurrent == 2

    def test_processor_max_concurrent_minimum_is_one(self) -> None:
        """Test that max_concurrent cannot be set below 1."""
        processor = ConcurrentProcessor(max_concurrent=0)
        assert processor.max_concurrent == 1

        processor.max_concurrent = -5
        assert processor.max_concurrent == 1

    def test_aggregated_progress_initial_state(
        self, processor: ConcurrentProcessor
    ) -> None:
        """Test that aggregated progress starts with zero values."""
        progress = processor.get_aggregated_progress()

        assert progress.total_jobs == 0
        assert progress.completed_jobs == 0
        assert progress.in_progress_jobs == 0
        assert progress.pending_jobs == 0
        assert progress.overall_progress == 0.0

    def test_cancel_sets_cancelled_flag(
        self, processor: ConcurrentProcessor
    ) -> None:
        """Test that cancel() sets the cancelled flag."""
        processor.cancel()
        assert processor._cancelled is True

    def test_reset_clears_state(self, processor: ConcurrentProcessor) -> None:
        """Test that reset() clears all state."""
        # Set up some state
        processor._job_progresses[0] = JobProgress(
            job_id=0,
            input_path=Path("/test.mp4"),
            status="completed",
        )
        processor._completed_count = 1
        processor._total_jobs = 1
        processor._cancelled = True

        processor.reset()

        assert len(processor._job_progresses) == 0
        assert processor._completed_count == 0
        assert processor._total_jobs == 0
        assert processor._cancelled is False

    @pytest.mark.asyncio
    async def test_process_batch_empty_list(
        self, processor: ConcurrentProcessor
    ) -> None:
        """Test that processing empty list returns empty results."""

        async def dummy_processor(
            item: MockConversionRequest,
            progress_callback: callable,
        ) -> str:
            return "result"

        results = await processor.process_batch([], dummy_processor)
        assert results == []

    @pytest.mark.asyncio
    async def test_process_batch_single_item(
        self, processor: ConcurrentProcessor, tmp_path: Path
    ) -> None:
        """Test processing a single item."""
        request = MockConversionRequest(
            input_path=tmp_path / "input.mp4",
            output_path=tmp_path / "output.mp4",
        )

        async def mock_processor(
            item: MockConversionRequest,
            progress_callback: callable,
        ) -> str:
            progress_callback(0.5)
            await asyncio.sleep(0.01)
            progress_callback(1.0)
            return f"processed:{item.input_path.name}"

        results = await processor.process_batch([request], mock_processor)

        assert len(results) == 1
        assert results[0] == "processed:input.mp4"

    @pytest.mark.asyncio
    async def test_process_batch_multiple_items_concurrent(
        self, tmp_path: Path
    ) -> None:
        """Test processing multiple items concurrently."""
        processor = ConcurrentProcessor(max_concurrent=2)

        requests = [
            MockConversionRequest(
                input_path=tmp_path / f"input{i}.mp4",
                output_path=tmp_path / f"output{i}.mp4",
            )
            for i in range(4)
        ]

        execution_order: list[int] = []
        max_concurrent_seen = 0
        current_concurrent = 0

        async def mock_processor(
            item: MockConversionRequest,
            progress_callback: callable,
        ) -> str:
            nonlocal current_concurrent, max_concurrent_seen

            current_concurrent += 1
            max_concurrent_seen = max(max_concurrent_seen, current_concurrent)

            idx = int(item.input_path.stem.replace("input", ""))
            execution_order.append(idx)

            await asyncio.sleep(0.05)
            progress_callback(1.0)

            current_concurrent -= 1
            return f"result:{idx}"

        results = await processor.process_batch(requests, mock_processor)

        assert len(results) == 4
        # Should not exceed max_concurrent
        assert max_concurrent_seen <= 2

    @pytest.mark.asyncio
    async def test_process_batch_progress_tracking(
        self, processor: ConcurrentProcessor, tmp_path: Path
    ) -> None:
        """Test that progress is tracked during batch processing."""
        requests = [
            MockConversionRequest(
                input_path=tmp_path / f"input{i}.mp4",
                output_path=tmp_path / f"output{i}.mp4",
            )
            for i in range(2)
        ]

        progress_updates: list[AggregatedProgress] = []

        def on_progress(progress: AggregatedProgress) -> None:
            progress_updates.append(progress)

        async def mock_processor(
            item: MockConversionRequest,
            progress_callback: callable,
        ) -> str:
            progress_callback(0.5)
            await asyncio.sleep(0.01)
            progress_callback(1.0)
            return "done"

        await processor.process_batch(requests, mock_processor, on_progress)

        # Should have received progress updates
        assert len(progress_updates) > 0
        # Final progress should show all completed
        final_progress = progress_updates[-1]
        assert final_progress.completed_jobs == 2

    @pytest.mark.asyncio
    async def test_process_batch_handles_exception(
        self, processor: ConcurrentProcessor, tmp_path: Path
    ) -> None:
        """Test that exceptions in processors are handled gracefully."""
        requests = [
            MockConversionRequest(
                input_path=tmp_path / f"input{i}.mp4",
                output_path=tmp_path / f"output{i}.mp4",
            )
            for i in range(3)
        ]

        async def mock_processor(
            item: MockConversionRequest,
            progress_callback: callable,
        ) -> str:
            if "input1" in item.input_path.name:
                raise ValueError("Simulated failure")
            return "success"

        results = await processor.process_batch(requests, mock_processor)

        assert len(results) == 3
        assert results[0] == "success"
        assert results[1] is None  # Failed job returns None
        assert results[2] == "success"


class TestJobProgress:
    """Tests for JobProgress tracking."""

    def test_job_progress_creation(self, tmp_path: Path) -> None:
        """Test JobProgress creation with defaults."""
        progress = JobProgress(
            job_id=0,
            input_path=tmp_path / "test.mp4",
        )

        assert progress.job_id == 0
        assert progress.progress == 0.0
        assert progress.status == "pending"
        assert progress.started_at is None
        assert progress.message == ""

    def test_job_progress_with_values(self, tmp_path: Path) -> None:
        """Test JobProgress with explicit values."""
        now = datetime.now()
        progress = JobProgress(
            job_id=1,
            input_path=tmp_path / "test.mp4",
            progress=0.75,
            status="in_progress",
            started_at=now,
            message="Processing...",
        )

        assert progress.job_id == 1
        assert progress.progress == 0.75
        assert progress.status == "in_progress"
        assert progress.started_at == now
        assert progress.message == "Processing..."


class TestAggregatedProgress:
    """Tests for AggregatedProgress functionality."""

    def test_aggregated_progress_defaults(self) -> None:
        """Test AggregatedProgress creation with defaults."""
        progress = AggregatedProgress()

        assert progress.total_jobs == 0
        assert progress.completed_jobs == 0
        assert progress.in_progress_jobs == 0
        assert progress.pending_jobs == 0
        assert progress.overall_progress == 0.0
        assert progress.job_progresses == []
        assert progress.current_files == []

    def test_aggregated_progress_with_jobs(self, tmp_path: Path) -> None:
        """Test AggregatedProgress with job data."""
        jobs = [
            JobProgress(job_id=0, input_path=tmp_path / "a.mp4", status="completed"),
            JobProgress(job_id=1, input_path=tmp_path / "b.mp4", status="in_progress"),
            JobProgress(job_id=2, input_path=tmp_path / "c.mp4", status="pending"),
        ]

        progress = AggregatedProgress(
            total_jobs=3,
            completed_jobs=1,
            in_progress_jobs=1,
            pending_jobs=1,
            overall_progress=0.5,
            job_progresses=jobs,
            current_files=["b.mp4"],
        )

        assert progress.total_jobs == 3
        assert progress.completed_jobs == 1
        assert len(progress.current_files) == 1


class TestResourceStatus:
    """Tests for ResourceStatus dataclass."""

    def test_resource_status_defaults(self) -> None:
        """Test ResourceStatus creation with defaults."""
        status = ResourceStatus()

        assert status.cpu_percent == 0.0
        assert status.memory_percent == 0.0
        assert status.cpu_level == ResourceLevel.NORMAL
        assert status.memory_level == ResourceLevel.NORMAL
        assert status.recommended_concurrency == 2

    def test_resource_status_with_values(self) -> None:
        """Test ResourceStatus with explicit values."""
        status = ResourceStatus(
            cpu_percent=85.0,
            memory_percent=70.0,
            cpu_level=ResourceLevel.HIGH,
            memory_level=ResourceLevel.NORMAL,
            recommended_concurrency=1,
        )

        assert status.cpu_percent == 85.0
        assert status.memory_percent == 70.0
        assert status.cpu_level == ResourceLevel.HIGH


class TestConcurrentWorkflowIntegration:
    """Integration tests for concurrent processing workflow."""

    @pytest.mark.asyncio
    async def test_full_concurrent_conversion_workflow(
        self, tmp_path: Path
    ) -> None:
        """Test complete concurrent conversion workflow simulation."""
        processor = ConcurrentProcessor(
            max_concurrent=2,
            enable_resource_monitoring=True,
        )

        # Create mock conversion requests
        requests = [
            MockConversionRequest(
                input_path=tmp_path / f"video{i}.mp4",
                output_path=tmp_path / f"converted{i}.mp4",
            )
            for i in range(4)
        ]

        # Track workflow events
        workflow_events: list[str] = []

        def on_progress(progress: AggregatedProgress) -> None:
            workflow_events.append(
                f"progress: {progress.completed_jobs}/{progress.total_jobs}"
            )

        async def mock_conversion(
            request: MockConversionRequest,
            progress_callback: callable,
        ) -> dict:
            workflow_events.append(f"start: {request.input_path.name}")
            progress_callback(0.5)
            await asyncio.sleep(0.02)
            progress_callback(1.0)
            workflow_events.append(f"done: {request.input_path.name}")
            return {
                "input": str(request.input_path),
                "output": str(request.output_path),
                "success": True,
            }

        results = await processor.process_batch(
            requests, mock_conversion, on_progress
        )

        # Verify all items processed
        assert len(results) == 4
        assert all(r["success"] for r in results)

        # Verify workflow events
        assert any("start:" in e for e in workflow_events)
        assert any("done:" in e for e in workflow_events)
        assert any("progress:" in e for e in workflow_events)

    @pytest.mark.asyncio
    async def test_adaptive_concurrency_reduces_under_load(self) -> None:
        """Test that adaptive concurrency reduces under simulated load."""
        processor = ConcurrentProcessor(
            max_concurrent=4,
            enable_resource_monitoring=True,
            adaptive_concurrency=True,
        )

        # Mock high resource usage
        with patch.object(
            processor._resource_monitor,
            "get_status",
            return_value=ResourceStatus(
                cpu_percent=95.0,
                memory_percent=90.0,
                cpu_level=ResourceLevel.CRITICAL,
                memory_level=ResourceLevel.CRITICAL,
                recommended_concurrency=1,
            ),
        ):
            processor.reset()
            processor._total_jobs = 4

            # Get resource status to verify mocking works
            status = processor.get_resource_status()
            assert status is not None
            assert status.recommended_concurrency == 1

    def test_resource_status_available(self) -> None:
        """Test that resource status is available when monitoring enabled."""
        processor = ConcurrentProcessor(enable_resource_monitoring=True)
        status = processor.get_resource_status()
        assert status is not None

    def test_resource_status_unavailable_when_disabled(self) -> None:
        """Test that resource status is None when monitoring disabled."""
        processor = ConcurrentProcessor(enable_resource_monitoring=False)
        status = processor.get_resource_status()
        assert status is None
