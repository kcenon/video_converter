"""Performance and memory tests for the GUI.

This module tests performance characteristics and memory usage
of GUI components, including startup time, memory leaks, and
responsiveness under load.
"""

from __future__ import annotations

import gc
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from video_converter.gui.widgets.drop_zone import DropZone
from video_converter.gui.widgets.progress_card import ProgressCard

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


pytestmark = [pytest.mark.gui, pytest.mark.slow]


@pytest.fixture
def mock_services():
    """Create mocks for all services used by MainWindow."""
    with patch(
        "video_converter.gui.main_window.ConversionService"
    ) as mock_conv, patch(
        "video_converter.gui.main_window.PhotosService"
    ) as mock_photos, patch(
        "video_converter.gui.main_window.SettingsManager"
    ) as mock_settings:
        mock_settings_instance = MagicMock()
        mock_settings_instance.get.return_value = {
            "encoder": "Hardware (VideoToolbox)",
            "quality": 22,
            "threads": 4,
            "output_dir": "",
            "preserve_original": True,
        }
        mock_settings_instance.is_dirty.return_value = False
        mock_settings_instance.apply_to_conversion_settings.return_value = {}
        mock_settings.return_value = mock_settings_instance

        mock_conv_instance = MagicMock()
        mock_conv_instance.task_added = MagicMock()
        mock_conv_instance.task_started = MagicMock()
        mock_conv_instance.progress_updated = MagicMock()
        mock_conv_instance.task_completed = MagicMock()
        mock_conv_instance.task_failed = MagicMock()
        mock_conv_instance.task_cancelled = MagicMock()
        mock_conv_instance.queue_updated = MagicMock()
        mock_conv_instance.all_completed = MagicMock()
        mock_conv.return_value = mock_conv_instance

        mock_photos_instance = MagicMock()
        mock_photos.return_value = mock_photos_instance

        yield {
            "conversion": mock_conv_instance,
            "photos": mock_photos_instance,
            "settings": mock_settings_instance,
        }


class TestStartupPerformance:
    """Tests for application startup performance."""

    def test_main_window_startup_time(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test that MainWindow starts within acceptable time."""
        from video_converter.gui.main_window import MainWindow

        start_time = time.perf_counter()

        window = MainWindow()
        qtbot.addWidget(window)

        elapsed = time.perf_counter() - start_time

        # MainWindow should initialize in under 3 seconds
        # (as per acceptance criteria)
        assert elapsed < 3.0, f"Startup took {elapsed:.2f}s, expected < 3s"

        window.close()

    def test_drop_zone_creation_time(self, qtbot: QtBot) -> None:
        """Test that DropZone creates quickly."""
        start_time = time.perf_counter()

        widget = DropZone()
        qtbot.addWidget(widget)

        elapsed = time.perf_counter() - start_time

        # Widget should create in under 100ms
        assert elapsed < 0.1, f"Creation took {elapsed:.3f}s, expected < 0.1s"

    def test_progress_card_creation_time(self, qtbot: QtBot) -> None:
        """Test that ProgressCard creates quickly."""
        start_time = time.perf_counter()

        widget = ProgressCard(
            task_id="test-123",
            file_name="test.mp4",
            file_size="1 GB",
        )
        qtbot.addWidget(widget)

        elapsed = time.perf_counter() - start_time

        # Widget should create in under 50ms
        assert elapsed < 0.05, f"Creation took {elapsed:.3f}s, expected < 0.05s"


class TestMemoryLeaks:
    """Tests for memory leak detection."""

    def test_drop_zone_no_memory_leak(self, qtbot: QtBot) -> None:
        """Test that DropZone doesn't leak memory on creation/destruction."""
        # Force garbage collection
        gc.collect()

        # Get initial object count
        initial_objects = len(gc.get_objects())

        # Create and destroy widgets multiple times
        for _ in range(10):
            widget = DropZone()
            qtbot.addWidget(widget)
            widget.close()
            widget.deleteLater()

        # Process events and collect garbage
        from PySide6.QtWidgets import QApplication

        QApplication.processEvents()
        gc.collect()

        # Object count shouldn't grow significantly
        final_objects = len(gc.get_objects())
        growth = final_objects - initial_objects

        # Allow some growth but not excessive
        # (widget objects are tracked by Qt, so some growth is normal)
        assert growth < 1000, f"Object count grew by {growth}, possible leak"

    def test_progress_card_no_memory_leak(self, qtbot: QtBot) -> None:
        """Test that ProgressCard doesn't leak memory."""
        gc.collect()
        initial_objects = len(gc.get_objects())

        for i in range(20):
            widget = ProgressCard(
                task_id=f"test-{i}",
                file_name=f"video_{i}.mp4",
                file_size="1 GB",
            )
            qtbot.addWidget(widget)
            widget.close()
            widget.deleteLater()

        from PySide6.QtWidgets import QApplication

        QApplication.processEvents()
        gc.collect()

        final_objects = len(gc.get_objects())
        growth = final_objects - initial_objects

        assert growth < 2000, f"Object count grew by {growth}, possible leak"

    def test_main_window_no_memory_leak(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test that MainWindow doesn't leak memory."""
        from video_converter.gui.main_window import MainWindow

        gc.collect()
        initial_objects = len(gc.get_objects())

        for _ in range(3):
            window = MainWindow()
            qtbot.addWidget(window)
            window.show()
            window.close()

        from PySide6.QtWidgets import QApplication

        QApplication.processEvents()
        gc.collect()

        final_objects = len(gc.get_objects())
        growth = final_objects - initial_objects

        # MainWindow is complex, allow more growth
        assert growth < 5000, f"Object count grew by {growth}, possible leak"


class TestProgressUpdatePerformance:
    """Tests for progress update performance."""

    def test_rapid_progress_updates(self, qtbot: QtBot) -> None:
        """Test that rapid progress updates don't cause performance issues."""
        widget = ProgressCard(
            task_id="test-123",
            file_name="test.mp4",
            file_size="1 GB",
        )
        qtbot.addWidget(widget)

        start_time = time.perf_counter()

        # Simulate 100 rapid progress updates
        for i in range(100):
            progress = i
            widget.update_progress(progress, eta=f"{100-i}:00", speed="1.5x")

        elapsed = time.perf_counter() - start_time

        # 100 updates should complete in under 1 second
        assert elapsed < 1.0, f"Updates took {elapsed:.2f}s, expected < 1s"


class TestQueuePerformance:
    """Tests for queue performance with many items."""

    def test_large_queue_performance(self, qtbot: QtBot) -> None:
        """Test queue performance with many conversion items."""
        from video_converter.gui.views.queue_view import QueueView

        view = QueueView()
        qtbot.addWidget(view)

        start_time = time.perf_counter()

        # Add 100 items to the queue
        for i in range(100):
            view.add_conversion(f"task-{i}", f"video_{i}.mp4", "1 GB")

        elapsed = time.perf_counter() - start_time

        # Adding 100 items should take less than 5 seconds
        assert elapsed < 5.0, f"Adding items took {elapsed:.2f}s, expected < 5s"
        assert view.queue_list.count() == 100


class TestStabilityUnderLoad:
    """Tests for stability under load conditions."""

    def test_consecutive_conversions_stability(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test stability during many consecutive conversions.

        This test simulates the acceptance criteria requirement of
        no crashes in 1000 consecutive conversions.
        """
        from video_converter.gui.views.queue_view import QueueView

        view = QueueView()
        qtbot.addWidget(view)

        # Simulate 100 consecutive conversion cycles
        # (reduced from 1000 for practical test runtime)
        for i in range(100):
            task_id = f"task-{i}"

            # Add to queue
            view.add_conversion(task_id, f"video_{i}.mp4", "1 GB")

            # Simulate progress updates
            for progress in [25, 50, 75, 100]:
                view.update_progress(task_id, progress, "1:00", "1.5x")

            # Mark complete
            view.mark_completed(task_id, success=True)

        # Should complete without crashes
        assert True, "Completed 100 conversion cycles without crash"

    def test_tab_switching_stability(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test stability during rapid tab switching."""
        from video_converter.gui.main_window import MainWindow

        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        # Rapidly switch between all tabs 50 times
        for _ in range(50):
            for tab in range(5):
                window.tab_bar.setCurrentIndex(tab)

        # Should complete without crashes
        assert window.isVisible() is True

        window.close()
