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

    def test_service_creates_successfully(self, qtbot: QtBot) -> None:
        """Test that ConversionService can be created."""
        service = ConversionService()
        qtbot.addWidget(service)

        assert service is not None
        assert service._is_processing is False
        assert service._is_paused is False

        service.shutdown()

    def test_service_has_empty_queue(self, qtbot: QtBot) -> None:
        """Test that new service has empty queue."""
        service = ConversionService()
        qtbot.addWidget(service)

        status = service.get_queue_status()
        assert status["total"] == 0
        assert status["queued"] == 0
        assert status["is_processing"] is False

        service.shutdown()

    def test_service_has_worker_thread(self, qtbot: QtBot) -> None:
        """Test that service creates a worker thread."""
        service = ConversionService()
        qtbot.addWidget(service)

        assert isinstance(service._worker_thread, QThread)
        assert service._worker_thread.isRunning() is True

        service.shutdown()


class TestConversionServiceAddTask:
    """Tests for adding tasks to the conversion service."""

    def test_add_task_returns_id(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that adding a task returns a task ID."""
        service = ConversionService()
        qtbot.addWidget(service)

        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"\x00" * 1024)

        # Prevent actual processing
        with patch.object(service, "_process_next"):
            task_id = service.add_task(str(video_file))

        assert task_id is not None
        assert len(task_id) == 8  # UUID first 8 chars

        service.shutdown()

    def test_add_task_emits_signal(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that adding a task emits task_added signal."""
        service = ConversionService()
        qtbot.addWidget(service)

        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"\x00" * 1024)

        with patch.object(service, "_process_next"):
            with qtbot.waitSignal(service.task_added, timeout=1000) as blocker:
                service.add_task(str(video_file))

        task_id, file_name, file_size = blocker.args
        assert file_name == "test.mp4"
        assert file_size == "1.0 KB"

        service.shutdown()

    def test_add_task_updates_queue(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that adding a task updates the queue."""
        service = ConversionService()
        qtbot.addWidget(service)

        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"\x00" * 1024)

        with patch.object(service, "_process_next"):
            service.add_task(str(video_file))

        status = service.get_queue_status()
        assert status["total"] == 1
        assert status["queued"] == 1

        service.shutdown()

    def test_add_task_with_custom_output_path(
        self, qtbot: QtBot, tmp_path: Path
    ) -> None:
        """Test adding a task with custom output path."""
        service = ConversionService()
        qtbot.addWidget(service)

        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"\x00" * 1024)
        output_file = tmp_path / "output" / "converted.mp4"

        with patch.object(service, "_process_next"):
            task_id = service.add_task(str(video_file), output_path=str(output_file))

        task = service.get_task(task_id)
        assert task is not None
        assert task.output_path == output_file

        service.shutdown()

    def test_add_task_with_settings(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test adding a task with conversion settings."""
        service = ConversionService()
        qtbot.addWidget(service)

        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"\x00" * 1024)
        settings = {"encoder": "Hardware", "quality": 20}

        with patch.object(service, "_process_next"):
            task_id = service.add_task(str(video_file), settings=settings)

        task = service.get_task(task_id)
        assert task is not None
        assert task.settings == settings

        service.shutdown()


class TestConversionServiceCancelTask:
    """Tests for canceling tasks in the conversion service."""

    def test_cancel_queued_task(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test canceling a queued task."""
        service = ConversionService()
        qtbot.addWidget(service)

        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"\x00" * 1024)

        with patch.object(service, "_process_next"):
            task_id = service.add_task(str(video_file))

        result = service.cancel_task(task_id)
        assert result is True

        task = service.get_task(task_id)
        assert task.status == "cancelled"

        service.shutdown()

    def test_cancel_emits_signal(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that canceling emits task_cancelled signal."""
        service = ConversionService()
        qtbot.addWidget(service)

        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"\x00" * 1024)

        with patch.object(service, "_process_next"):
            task_id = service.add_task(str(video_file))

        with qtbot.waitSignal(service.task_cancelled, timeout=1000) as blocker:
            service.cancel_task(task_id)

        assert blocker.args[0] == task_id

        service.shutdown()

    def test_cancel_nonexistent_task(self, qtbot: QtBot) -> None:
        """Test canceling a task that doesn't exist."""
        service = ConversionService()
        qtbot.addWidget(service)

        result = service.cancel_task("nonexistent")
        assert result is False

        service.shutdown()

    def test_cancel_all_tasks(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test canceling all tasks."""
        service = ConversionService()
        qtbot.addWidget(service)

        with patch.object(service, "_process_next"):
            for i in range(3):
                video_file = tmp_path / f"test_{i}.mp4"
                video_file.write_bytes(b"\x00" * 1024)
                service.add_task(str(video_file))

        service.cancel_all()

        assert len(service._queue) == 0
        assert service._is_processing is False

        service.shutdown()


class TestConversionServicePauseResume:
    """Tests for pause/resume functionality."""

    def test_pause_sets_flag(self, qtbot: QtBot) -> None:
        """Test that pausing sets the paused flag."""
        service = ConversionService()
        qtbot.addWidget(service)

        service.pause_all()

        assert service._is_paused is True

        service.shutdown()

    def test_resume_clears_flag(self, qtbot: QtBot) -> None:
        """Test that resuming clears the paused flag."""
        service = ConversionService()
        qtbot.addWidget(service)

        service.pause_all()
        service.resume_all()

        assert service._is_paused is False

        service.shutdown()

    def test_pause_emits_queue_updated(self, qtbot: QtBot) -> None:
        """Test that pausing emits queue_updated signal."""
        service = ConversionService()
        qtbot.addWidget(service)

        with qtbot.waitSignal(service.queue_updated, timeout=1000):
            service.pause_all()

        service.shutdown()


class TestConversionServiceStatistics:
    """Tests for conversion statistics."""

    def test_initial_statistics(self, qtbot: QtBot) -> None:
        """Test initial statistics are zeros."""
        service = ConversionService()
        qtbot.addWidget(service)

        stats = service.get_statistics()

        assert stats["completed"] == 0
        assert stats["failed"] == 0
        assert stats["total_original_size"] == 0
        assert stats["total_converted_size"] == 0
        assert stats["total_saved"] == 0

        service.shutdown()


class TestConversionServiceClearCompleted:
    """Tests for clearing completed tasks."""

    def test_clear_completed_removes_tasks(
        self, qtbot: QtBot, tmp_path: Path
    ) -> None:
        """Test that clear_completed removes finished tasks."""
        service = ConversionService()
        qtbot.addWidget(service)

        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"\x00" * 1024)

        with patch.object(service, "_process_next"):
            task_id = service.add_task(str(video_file))

        # Manually mark as completed
        service._tasks[task_id].status = "completed"

        service.clear_completed()

        assert task_id not in service._tasks

        service.shutdown()


class TestConversionServiceFormatSize:
    """Tests for file size formatting."""

    def test_format_bytes(self, qtbot: QtBot) -> None:
        """Test formatting bytes."""
        service = ConversionService()
        qtbot.addWidget(service)

        assert service._format_size(500) == "500 B"

        service.shutdown()

    def test_format_kilobytes(self, qtbot: QtBot) -> None:
        """Test formatting kilobytes."""
        service = ConversionService()
        qtbot.addWidget(service)

        assert service._format_size(2048) == "2.0 KB"

        service.shutdown()

    def test_format_megabytes(self, qtbot: QtBot) -> None:
        """Test formatting megabytes."""
        service = ConversionService()
        qtbot.addWidget(service)

        assert service._format_size(5 * 1024 * 1024) == "5.0 MB"

        service.shutdown()

    def test_format_gigabytes(self, qtbot: QtBot) -> None:
        """Test formatting gigabytes."""
        service = ConversionService()
        qtbot.addWidget(service)

        assert service._format_size(2 * 1024 * 1024 * 1024) == "2.00 GB"

        service.shutdown()


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
