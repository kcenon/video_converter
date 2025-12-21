"""Unit tests for orchestrator module."""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from video_converter.converters.base import EncoderNotAvailableError
from video_converter.converters.factory import ConverterFactory
from video_converter.core.orchestrator import (
    ConversionTask,
    Orchestrator,
    OrchestratorConfig,
    VIDEO_EXTENSIONS,
)
from video_converter.core.types import (
    BatchStatus,
    ConversionMode,
    ConversionProgress,
    ConversionResult,
    ConversionStage,
    ConversionStatus,
    QueuePriority,
)
from video_converter.processors.quality_validator import (
    ValidationResult,
    ValidationStrictness,
)


class TestOrchestratorConfig:
    """Tests for OrchestratorConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = OrchestratorConfig()
        assert config.mode == ConversionMode.HARDWARE
        assert config.quality == 45
        assert config.crf == 22
        assert config.preset == "medium"
        assert config.output_suffix == "_h265"
        assert config.preserve_metadata is True
        assert config.validate_output is True
        assert config.validation_strictness == ValidationStrictness.STANDARD
        assert config.max_concurrent == 2
        assert config.delete_original is False
        assert config.move_to_processed is None
        assert config.move_to_failed is None

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = OrchestratorConfig(
            mode=ConversionMode.SOFTWARE,
            quality=80,
            crf=18,
            preset="slow",
            output_suffix="_converted",
            validate_output=False,
            delete_original=True,
        )
        assert config.mode == ConversionMode.SOFTWARE
        assert config.quality == 80
        assert config.crf == 18
        assert config.preset == "slow"
        assert config.output_suffix == "_converted"
        assert config.validate_output is False
        assert config.delete_original is True


class TestConversionTask:
    """Tests for ConversionTask."""

    def test_default_status(self) -> None:
        """Test task starts with pending status."""
        task = ConversionTask(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
        )
        assert task.status == ConversionStatus.PENDING
        assert task.result is None
        assert task.error is None


class TestOrchestrator:
    """Tests for Orchestrator."""

    def test_initialization_with_defaults(self) -> None:
        """Test orchestrator initializes with defaults."""
        orchestrator = Orchestrator()
        assert orchestrator.config is not None
        assert orchestrator.converter_factory is not None
        assert orchestrator.validator is not None

    def test_initialization_with_custom_config(self) -> None:
        """Test orchestrator initializes with custom config."""
        config = OrchestratorConfig(quality=80)
        orchestrator = Orchestrator(config=config)
        assert orchestrator.config.quality == 80

    def test_create_output_path_same_directory(self) -> None:
        """Test output path creation in same directory."""
        config = OrchestratorConfig(output_suffix="_h265")
        orchestrator = Orchestrator(config=config)

        input_path = Path("/videos/input.mov")
        output_path = orchestrator._create_output_path(input_path)

        assert output_path == Path("/videos/input_h265.mp4")

    def test_create_output_path_different_directory(self) -> None:
        """Test output path creation in different directory."""
        config = OrchestratorConfig(output_suffix="_h265")
        orchestrator = Orchestrator(config=config)

        input_path = Path("/videos/input.mov")
        output_dir = Path("/converted")
        output_path = orchestrator._create_output_path(input_path, output_dir)

        assert output_path == Path("/converted/input_h265.mp4")

    def test_create_output_path_no_duplicate_suffix(self) -> None:
        """Test output path doesn't duplicate suffix."""
        config = OrchestratorConfig(output_suffix="_h265")
        orchestrator = Orchestrator(config=config)

        # File already has suffix
        input_path = Path("/videos/input_h265.mov")
        output_path = orchestrator._create_output_path(input_path)

        assert output_path == Path("/videos/input_h265.mp4")

    def test_generate_session_id(self) -> None:
        """Test session ID generation."""
        orchestrator = Orchestrator()
        session_id = orchestrator._generate_session_id()

        assert isinstance(session_id, str)
        assert len(session_id) == 8

    def test_cancel(self) -> None:
        """Test cancellation sets flag."""
        orchestrator = Orchestrator()
        assert orchestrator._cancelled is False

        orchestrator.cancel()
        assert orchestrator._cancelled is True


class TestOrchestratorProgressEmit:
    """Tests for progress emission."""

    def test_progress_callback_called(self) -> None:
        """Test progress callback is invoked."""
        orchestrator = Orchestrator()
        callback_data: list[ConversionProgress] = []

        def on_progress(progress: ConversionProgress) -> None:
            callback_data.append(progress)

        orchestrator._emit_progress(
            on_progress,
            ConversionStage.CONVERT,
            ConversionStatus.IN_PROGRESS,
            current_file="test.mov",
            message="Converting...",
        )

        assert len(callback_data) == 1
        assert callback_data[0].stage == ConversionStage.CONVERT
        assert callback_data[0].current_file == "test.mov"

    def test_progress_callback_none_safe(self) -> None:
        """Test None callback doesn't raise."""
        orchestrator = Orchestrator()
        # Should not raise
        orchestrator._emit_progress(
            None,
            ConversionStage.CONVERT,
            ConversionStatus.IN_PROGRESS,
        )

    def test_progress_callback_error_handled(self) -> None:
        """Test callback errors are handled gracefully."""
        orchestrator = Orchestrator()

        def bad_callback(progress: ConversionProgress) -> None:
            raise ValueError("Callback error")

        # Should not raise
        orchestrator._emit_progress(
            bad_callback,
            ConversionStage.CONVERT,
            ConversionStatus.IN_PROGRESS,
        )


class TestOrchestratorConvertSingle:
    """Tests for convert_single method."""

    @pytest.mark.asyncio
    async def test_convert_single_file_not_found(self) -> None:
        """Test conversion fails for missing file."""
        orchestrator = Orchestrator()
        result = await orchestrator.convert_single(
            input_path=Path("/nonexistent/video.mov"),
        )

        assert result.success is False
        assert "not found" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_convert_single_encoder_not_available(self) -> None:
        """Test conversion fails when no encoder available."""
        mock_factory = MagicMock(spec=ConverterFactory)
        mock_factory.get_converter.side_effect = EncoderNotAvailableError(
            "No encoder"
        )

        orchestrator = Orchestrator(converter_factory=mock_factory)

        with tempfile.NamedTemporaryFile(suffix=".mov", delete=False) as f:
            input_path = Path(f.name)

        try:
            result = await orchestrator.convert_single(input_path=input_path)
            assert result.success is False
            assert "No encoder" in result.error_message
        finally:
            input_path.unlink()


class TestOrchestratorRun:
    """Tests for run method."""

    @pytest.mark.asyncio
    async def test_run_empty_list(self) -> None:
        """Test run with empty file list."""
        orchestrator = Orchestrator()
        report = await orchestrator.run(input_paths=[])

        assert report.total_files == 0
        assert report.successful == 0
        assert report.failed == 0

    @pytest.mark.asyncio
    async def test_run_skips_existing_output(self) -> None:
        """Test run skips files with existing output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "video.mov"
            input_path.touch()

            # Create output file that already exists
            output_path = Path(tmpdir) / "video_h265.mp4"
            output_path.touch()

            orchestrator = Orchestrator()
            report = await orchestrator.run(input_paths=[input_path])

            assert report.skipped == 1
            assert report.successful == 0

    @pytest.mark.asyncio
    async def test_run_calls_on_complete(self) -> None:
        """Test run calls completion callback."""
        orchestrator = Orchestrator()
        complete_called = False

        def on_complete(report):
            nonlocal complete_called
            complete_called = True

        await orchestrator.run(input_paths=[], on_complete=on_complete)
        assert complete_called is True


class TestOrchestratorRunDirectory:
    """Tests for run_directory method."""

    @pytest.mark.asyncio
    async def test_run_directory_empty(self) -> None:
        """Test run_directory with empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = Orchestrator()
            report = await orchestrator.run_directory(
                input_dir=Path(tmpdir),
            )

            assert report.total_files == 0

    @pytest.mark.asyncio
    async def test_run_directory_finds_videos(self) -> None:
        """Test run_directory discovers video files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            (Path(tmpdir) / "video1.mov").touch()
            (Path(tmpdir) / "video2.mp4").touch()
            (Path(tmpdir) / "document.pdf").touch()  # Should be ignored

            orchestrator = Orchestrator()

            # Mock the actual run to avoid conversion
            with patch.object(orchestrator, "run") as mock_run:
                mock_run.return_value = MagicMock()
                await orchestrator.run_directory(input_dir=Path(tmpdir))

                # Check that only video files were passed
                call_args = mock_run.call_args
                input_paths = call_args.kwargs["input_paths"]
                assert len(input_paths) == 2
                filenames = {p.name for p in input_paths}
                assert "video1.mov" in filenames
                assert "video2.mp4" in filenames
                assert "document.pdf" not in filenames


class TestOrchestratorTaskManagement:
    """Tests for task management methods."""

    def test_get_pending_tasks(self) -> None:
        """Test getting pending tasks."""
        orchestrator = Orchestrator()
        orchestrator._tasks = [
            ConversionTask(Path("a.mov"), Path("a.mp4"), ConversionStatus.PENDING),
            ConversionTask(Path("b.mov"), Path("b.mp4"), ConversionStatus.COMPLETED),
            ConversionTask(Path("c.mov"), Path("c.mp4"), ConversionStatus.PENDING),
        ]

        pending = orchestrator.get_pending_tasks()
        assert len(pending) == 2

    def test_get_completed_tasks(self) -> None:
        """Test getting completed tasks."""
        orchestrator = Orchestrator()
        orchestrator._tasks = [
            ConversionTask(Path("a.mov"), Path("a.mp4"), ConversionStatus.PENDING),
            ConversionTask(Path("b.mov"), Path("b.mp4"), ConversionStatus.COMPLETED),
            ConversionTask(Path("c.mov"), Path("c.mp4"), ConversionStatus.COMPLETED),
        ]

        completed = orchestrator.get_completed_tasks()
        assert len(completed) == 2

    def test_get_failed_tasks(self) -> None:
        """Test getting failed tasks."""
        orchestrator = Orchestrator()
        orchestrator._tasks = [
            ConversionTask(Path("a.mov"), Path("a.mp4"), ConversionStatus.FAILED),
            ConversionTask(Path("b.mov"), Path("b.mp4"), ConversionStatus.COMPLETED),
        ]

        failed = orchestrator.get_failed_tasks()
        assert len(failed) == 1


class TestVideoExtensions:
    """Tests for VIDEO_EXTENSIONS constant."""

    def test_common_extensions_present(self) -> None:
        """Test common video extensions are included."""
        assert ".mov" in VIDEO_EXTENSIONS
        assert ".mp4" in VIDEO_EXTENSIONS
        assert ".m4v" in VIDEO_EXTENSIONS
        assert ".avi" in VIDEO_EXTENSIONS
        assert ".mkv" in VIDEO_EXTENSIONS


class TestQueuePriority:
    """Tests for queue priority ordering."""

    def test_default_priority_is_fifo(self) -> None:
        """Test default priority is FIFO."""
        config = OrchestratorConfig()
        assert config.queue_priority == QueuePriority.FIFO

    def test_sort_by_priority_fifo(self) -> None:
        """Test FIFO ordering preserves order."""
        config = OrchestratorConfig(queue_priority=QueuePriority.FIFO)
        orchestrator = Orchestrator(config=config)

        paths = [Path("a.mov"), Path("b.mov"), Path("c.mov")]
        sorted_paths = orchestrator._sort_by_priority(paths)

        assert sorted_paths == paths

    def test_sort_by_priority_size_smallest(self) -> None:
        """Test sorting by size (smallest first)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files with different sizes
            small = Path(tmpdir) / "small.mov"
            medium = Path(tmpdir) / "medium.mov"
            large = Path(tmpdir) / "large.mov"

            small.write_bytes(b"x" * 100)
            medium.write_bytes(b"x" * 500)
            large.write_bytes(b"x" * 1000)

            config = OrchestratorConfig(queue_priority=QueuePriority.SIZE_SMALLEST)
            orchestrator = Orchestrator(config=config)

            paths = [large, small, medium]
            sorted_paths = orchestrator._sort_by_priority(paths)

            assert sorted_paths[0] == small
            assert sorted_paths[1] == medium
            assert sorted_paths[2] == large

    def test_sort_by_priority_size_largest(self) -> None:
        """Test sorting by size (largest first)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            small = Path(tmpdir) / "small.mov"
            large = Path(tmpdir) / "large.mov"

            small.write_bytes(b"x" * 100)
            large.write_bytes(b"x" * 1000)

            config = OrchestratorConfig(queue_priority=QueuePriority.SIZE_LARGEST)
            orchestrator = Orchestrator(config=config)

            paths = [small, large]
            sorted_paths = orchestrator._sort_by_priority(paths)

            assert sorted_paths[0] == large
            assert sorted_paths[1] == small


class TestBatchStatus:
    """Tests for batch status management."""

    def test_initial_status_is_idle(self) -> None:
        """Test orchestrator starts in IDLE status."""
        orchestrator = Orchestrator()
        assert orchestrator.get_batch_status() == BatchStatus.IDLE

    def test_pause_when_not_running(self) -> None:
        """Test pause returns False when not running."""
        orchestrator = Orchestrator()
        assert orchestrator.pause() is False

    def test_resume_when_not_paused(self) -> None:
        """Test resume returns False when not paused."""
        orchestrator = Orchestrator()
        assert orchestrator.resume() is False

    def test_is_paused(self) -> None:
        """Test is_paused property."""
        orchestrator = Orchestrator()
        assert orchestrator.is_paused() is False

    def test_cancel_sets_cancelled_status(self) -> None:
        """Test cancel sets CANCELLED status."""
        orchestrator = Orchestrator()
        orchestrator._batch_status = BatchStatus.RUNNING
        orchestrator.cancel()
        assert orchestrator.get_batch_status() == BatchStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_run_sets_running_status(self) -> None:
        """Test run sets RUNNING status initially."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a video file
            video = Path(tmpdir) / "video.mov"
            video.touch()

            orchestrator = Orchestrator()
            # Cancel immediately to exit
            orchestrator._cancelled = True

            await orchestrator.run(input_paths=[video])
            # After run completes (cancelled), check it was running
            assert orchestrator._batch_status in (
                BatchStatus.COMPLETED,
                BatchStatus.CANCELLED,
            )
