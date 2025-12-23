"""Tests for the ConversionService.

This module tests the conversion queue management, task handling,
and signal emission of the ConversionService.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QThread

from video_converter.gui.services.conversion_service import (
    ConversionService,
    ConversionTask,
    ConversionWorker,
)

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


pytestmark = pytest.mark.gui


@pytest.fixture
def conversion_service(qtbot: "QtBot"):
    """Create a ConversionService and ensure proper cleanup."""
    service = ConversionService()
    yield service
    service.shutdown()


class TestConversionTask:
    """Tests for ConversionTask dataclass."""

    def test_task_creation(self, tmp_path: Path) -> None:
        """Test that ConversionTask can be created with required fields."""
        video_file = tmp_path / "test.mp4"
        video_file.touch()

        task = ConversionTask(
            task_id="abc123",
            file_path=video_file,
            file_name="test.mp4",
            file_size=1000000,
        )

        assert task.task_id == "abc123"
        assert task.file_path == video_file
        assert task.status == "queued"
        assert task.progress == 0.0

    def test_task_default_values(self, tmp_path: Path) -> None:
        """Test that ConversionTask has correct default values."""
        video_file = tmp_path / "test.mp4"
        video_file.touch()

        task = ConversionTask(
            task_id="abc123",
            file_path=video_file,
            file_name="test.mp4",
            file_size=1000000,
        )

        assert task.output_path is None
        assert task.settings is None
        assert task.eta_seconds is None
        assert task.speed is None
        assert task.started_at is None
        assert task.completed_at is None
        assert task.error is None


class TestConversionServiceCreation:
    """Tests for ConversionService creation and initialization."""

    def test_service_creates_successfully(self, conversion_service) -> None:
        """Test that ConversionService can be created."""
        assert conversion_service is not None
        assert conversion_service._is_processing is False
        assert conversion_service._is_paused is False

    def test_service_has_empty_queue(self, conversion_service) -> None:
        """Test that new service has empty queue."""
        status = conversion_service.get_queue_status()
        assert status["total"] == 0
        assert status["queued"] == 0
        assert status["is_processing"] is False

    def test_service_has_worker_thread(self, conversion_service) -> None:
        """Test that service creates a worker thread."""
        assert isinstance(conversion_service._worker_thread, QThread)
        assert conversion_service._worker_thread.isRunning() is True


class TestConversionServiceAddTask:
    """Tests for adding tasks to the conversion service."""

    def test_add_task_returns_id(
        self, conversion_service, qtbot: QtBot, tmp_path: Path
    ) -> None:
        """Test that adding a task returns a task ID."""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"\x00" * 1024)

        # Prevent actual processing
        with patch.object(conversion_service, "_process_next"):
            task_id = conversion_service.add_task(str(video_file))

        assert task_id is not None
        assert len(task_id) == 8  # UUID first 8 chars

    def test_add_task_emits_signal(
        self, conversion_service, qtbot: QtBot, tmp_path: Path
    ) -> None:
        """Test that adding a task emits task_added signal."""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"\x00" * 1024)

        with patch.object(conversion_service, "_process_next"):
            with qtbot.waitSignal(
                conversion_service.task_added, timeout=1000
            ) as blocker:
                conversion_service.add_task(str(video_file))

        task_id, file_name, file_size = blocker.args
        assert file_name == "test.mp4"
        assert file_size == "1.0 KB"

    def test_add_task_updates_queue(
        self, conversion_service, qtbot: QtBot, tmp_path: Path
    ) -> None:
        """Test that adding a task updates the queue."""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"\x00" * 1024)

        with patch.object(conversion_service, "_process_next"):
            conversion_service.add_task(str(video_file))

        status = conversion_service.get_queue_status()
        assert status["total"] == 1
        assert status["queued"] == 1

    def test_add_task_with_custom_output_path(
        self, conversion_service, qtbot: QtBot, tmp_path: Path
    ) -> None:
        """Test adding a task with custom output path."""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"\x00" * 1024)
        output_file = tmp_path / "output" / "converted.mp4"

        with patch.object(conversion_service, "_process_next"):
            task_id = conversion_service.add_task(
                str(video_file), output_path=str(output_file)
            )

        task = conversion_service.get_task(task_id)
        assert task is not None
        assert task.output_path == output_file

    def test_add_task_with_settings(
        self, conversion_service, qtbot: QtBot, tmp_path: Path
    ) -> None:
        """Test adding a task with conversion settings."""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"\x00" * 1024)
        settings = {"encoder": "Hardware", "quality": 20}

        with patch.object(conversion_service, "_process_next"):
            task_id = conversion_service.add_task(str(video_file), settings=settings)

        task = conversion_service.get_task(task_id)
        assert task is not None
        assert task.settings == settings


class TestConversionServiceCancelTask:
    """Tests for canceling tasks in the conversion service."""

    def test_cancel_queued_task(
        self, conversion_service, qtbot: QtBot, tmp_path: Path
    ) -> None:
        """Test canceling a queued task."""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"\x00" * 1024)

        with patch.object(conversion_service, "_process_next"):
            task_id = conversion_service.add_task(str(video_file))

        result = conversion_service.cancel_task(task_id)
        assert result is True

        task = conversion_service.get_task(task_id)
        assert task.status == "cancelled"

    def test_cancel_emits_signal(
        self, conversion_service, qtbot: QtBot, tmp_path: Path
    ) -> None:
        """Test that canceling emits task_cancelled signal."""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"\x00" * 1024)

        with patch.object(conversion_service, "_process_next"):
            task_id = conversion_service.add_task(str(video_file))

        with qtbot.waitSignal(
            conversion_service.task_cancelled, timeout=1000
        ) as blocker:
            conversion_service.cancel_task(task_id)

        assert blocker.args[0] == task_id

    def test_cancel_nonexistent_task(self, conversion_service) -> None:
        """Test canceling a task that doesn't exist."""
        result = conversion_service.cancel_task("nonexistent")
        assert result is False

    def test_cancel_all_tasks(
        self, conversion_service, qtbot: QtBot, tmp_path: Path
    ) -> None:
        """Test canceling all tasks."""
        with patch.object(conversion_service, "_process_next"):
            for i in range(3):
                video_file = tmp_path / f"test_{i}.mp4"
                video_file.write_bytes(b"\x00" * 1024)
                conversion_service.add_task(str(video_file))

        conversion_service.cancel_all()

        assert len(conversion_service._queue) == 0
        assert conversion_service._is_processing is False


class TestConversionServicePauseResume:
    """Tests for pause/resume functionality."""

    def test_pause_sets_flag(self, conversion_service) -> None:
        """Test that pausing sets the paused flag."""
        conversion_service.pause_all()
        assert conversion_service._is_paused is True

    def test_resume_clears_flag(self, conversion_service) -> None:
        """Test that resuming clears the paused flag."""
        conversion_service.pause_all()
        conversion_service.resume_all()
        assert conversion_service._is_paused is False

    def test_pause_emits_queue_updated(self, conversion_service, qtbot: QtBot) -> None:
        """Test that pausing emits queue_updated signal."""
        with qtbot.waitSignal(conversion_service.queue_updated, timeout=1000):
            conversion_service.pause_all()


class TestConversionServiceStatistics:
    """Tests for conversion statistics."""

    def test_initial_statistics(self, conversion_service) -> None:
        """Test initial statistics are zeros."""
        stats = conversion_service.get_statistics()

        assert stats["completed"] == 0
        assert stats["failed"] == 0
        assert stats["total_original_size"] == 0
        assert stats["total_converted_size"] == 0
        assert stats["total_saved"] == 0


class TestConversionServiceClearCompleted:
    """Tests for clearing completed tasks."""

    def test_clear_completed_removes_tasks(
        self, conversion_service, qtbot: QtBot, tmp_path: Path
    ) -> None:
        """Test that clear_completed removes finished tasks."""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"\x00" * 1024)

        with patch.object(conversion_service, "_process_next"):
            task_id = conversion_service.add_task(str(video_file))

        # Manually mark as completed
        conversion_service._tasks[task_id].status = "completed"

        conversion_service.clear_completed()

        assert task_id not in conversion_service._tasks


class TestConversionServiceFormatSize:
    """Tests for file size formatting."""

    def test_format_bytes(self, conversion_service) -> None:
        """Test formatting bytes."""
        assert conversion_service._format_size(500) == "500 B"

    def test_format_kilobytes(self, conversion_service) -> None:
        """Test formatting kilobytes."""
        assert conversion_service._format_size(2048) == "2.0 KB"

    def test_format_megabytes(self, conversion_service) -> None:
        """Test formatting megabytes."""
        assert conversion_service._format_size(5 * 1024 * 1024) == "5.0 MB"

    def test_format_gigabytes(self, conversion_service) -> None:
        """Test formatting gigabytes."""
        assert conversion_service._format_size(2 * 1024 * 1024 * 1024) == "2.00 GB"


class TestConversionWorker:
    """Tests for ConversionWorker."""

    def test_worker_creates_successfully(self) -> None:
        """Test that ConversionWorker can be created."""
        worker = ConversionWorker()

        assert worker is not None
        assert worker._orchestrator is None
        assert worker._current_task is None

    def test_worker_cancel(self) -> None:
        """Test worker cancel method."""
        worker = ConversionWorker()

        # Should not raise when orchestrator is None
        worker.cancel()

        # Create mock orchestrator
        worker._orchestrator = MagicMock()
        worker.cancel()

        worker._orchestrator.cancel.assert_called_once()
