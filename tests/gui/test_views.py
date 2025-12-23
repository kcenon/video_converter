"""Tests for GUI views.

This module tests the individual view components: HomeView, ConvertView,
QueueView, SettingsView, and PhotosView.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from video_converter.gui.views.home_view import HomeView
from video_converter.gui.views.convert_view import ConvertView
from video_converter.gui.views.queue_view import QueueView
from video_converter.gui.views.settings_view import SettingsView

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


pytestmark = pytest.mark.gui


class TestHomeView:
    """Tests for HomeView."""

    def test_home_view_creates_successfully(self, qtbot: QtBot) -> None:
        """Test that HomeView can be created."""
        view = HomeView()
        qtbot.addWidget(view)

        assert view is not None

    def test_home_view_has_drop_zone(self, qtbot: QtBot) -> None:
        """Test that HomeView has a drop zone."""
        view = HomeView()
        qtbot.addWidget(view)

        assert view.drop_zone is not None

    def test_home_view_has_recent_list(self, qtbot: QtBot) -> None:
        """Test that HomeView has a recent conversions list."""
        view = HomeView()
        qtbot.addWidget(view)

        assert view.recent_list is not None

    def test_file_dropped_signal(self, qtbot: QtBot) -> None:
        """Test that file_dropped signal is propagated."""
        view = HomeView()
        qtbot.addWidget(view)

        with qtbot.waitSignal(view.file_dropped, timeout=1000) as blocker:
            view.drop_zone.file_dropped.emit("/path/to/video.mp4")

        assert blocker.args[0] == "/path/to/video.mp4"

    def test_files_dropped_signal(self, qtbot: QtBot) -> None:
        """Test that files_dropped signal is propagated."""
        view = HomeView()
        qtbot.addWidget(view)

        files = ["/path/to/video1.mp4", "/path/to/video2.mp4"]

        with qtbot.waitSignal(view.files_dropped, timeout=1000) as blocker:
            view.drop_zone.files_dropped.emit(files)

        assert blocker.args[0] == files


class TestConvertView:
    """Tests for ConvertView."""

    def test_convert_view_creates_successfully(self, qtbot: QtBot) -> None:
        """Test that ConvertView can be created."""
        view = ConvertView()
        qtbot.addWidget(view)

        assert view is not None

    def test_set_input_file(self, qtbot: QtBot) -> None:
        """Test setting the input file."""
        view = ConvertView()
        qtbot.addWidget(view)

        view.set_input_file("/path/to/test_video.mp4")

        # The view should display the file name
        assert view._input_file == "/path/to/test_video.mp4"

    def test_update_progress(self, qtbot: QtBot) -> None:
        """Test updating conversion progress."""
        view = ConvertView()
        qtbot.addWidget(view)

        view.update_progress(50.0, eta_seconds=120, speed="1.5x")

        # Progress should be updated
        assert view.progress_bar.value() == 50

    def test_conversion_complete_success(self, qtbot: QtBot) -> None:
        """Test handling successful completion."""
        view = ConvertView()
        qtbot.addWidget(view)

        view.conversion_complete(success=True)

        # View should reset for next conversion
        assert view.progress_bar.value() == 0 or view.progress_bar.value() == 100

    def test_conversion_complete_failure(self, qtbot: QtBot) -> None:
        """Test handling failed conversion."""
        view = ConvertView()
        qtbot.addWidget(view)

        view.conversion_complete(success=False, message="Encoding failed")

        # View should show error state
        assert "failed" in view.status_label.text().lower()


class TestQueueView:
    """Tests for QueueView."""

    def test_queue_view_creates_successfully(self, qtbot: QtBot) -> None:
        """Test that QueueView can be created."""
        view = QueueView()
        qtbot.addWidget(view)

        assert view is not None

    def test_add_conversion(self, qtbot: QtBot) -> None:
        """Test adding a conversion to the queue."""
        view = QueueView()
        qtbot.addWidget(view)

        view.add_conversion("task-123", "video.mp4", "1.5 GB")

        # Queue should have one item
        assert len(view._progress_cards) == 1

    def test_add_multiple_conversions(self, qtbot: QtBot) -> None:
        """Test adding multiple conversions."""
        view = QueueView()
        qtbot.addWidget(view)

        view.add_conversion("task-1", "video1.mp4", "1 GB")
        view.add_conversion("task-2", "video2.mp4", "2 GB")
        view.add_conversion("task-3", "video3.mp4", "3 GB")

        assert len(view._progress_cards) == 3

    def test_update_progress(self, qtbot: QtBot) -> None:
        """Test updating progress for a queued item."""
        view = QueueView()
        qtbot.addWidget(view)

        view.add_conversion("task-123", "video.mp4", "1.5 GB")
        view.update_progress("task-123", 50.0, "2:30", "1.5x")

        # The item's progress should be updated
        card = view._progress_cards.get("task-123")
        if card:
            assert card.progress == 50.0

    def test_mark_completed(self, qtbot: QtBot) -> None:
        """Test marking a conversion as completed."""
        view = QueueView()
        qtbot.addWidget(view)

        view.add_conversion("task-123", "video.mp4", "1.5 GB")
        view.mark_completed("task-123", success=True)

        card = view._progress_cards.get("task-123")
        if card:
            assert card.is_completed is True

    def test_pause_all_signal(self, qtbot: QtBot) -> None:
        """Test pause all button emits signal."""
        view = QueueView()
        qtbot.addWidget(view)

        # Add a conversion to enable the button
        view.add_conversion("task-1", "video.mp4", "1 GB")

        with qtbot.waitSignal(view.pause_all_requested, timeout=1000):
            view.pause_resume_button.click()

    def test_cancel_all_signal(self, qtbot: QtBot) -> None:
        """Test cancel all button emits signal."""
        view = QueueView()
        qtbot.addWidget(view)

        # Add a conversion to enable the button
        view.add_conversion("task-1", "video.mp4", "1 GB")

        with qtbot.waitSignal(view.cancel_all_requested, timeout=1000):
            view.cancel_all_button.click()


class TestSettingsView:
    """Tests for SettingsView."""

    def test_settings_view_creates_successfully(self, qtbot: QtBot) -> None:
        """Test that SettingsView can be created."""
        view = SettingsView()
        qtbot.addWidget(view)

        assert view is not None

    def test_load_settings(self, qtbot: QtBot) -> None:
        """Test loading settings into the view."""
        view = SettingsView()
        qtbot.addWidget(view)

        settings = {
            "encoding": {
                "encoder": "VideoToolbox (Hardware)",
                "quality": 22,
                "preset": "medium",
            },
            "paths": {
                "output_dir": "/output",
            },
        }

        view.load_settings(settings)

        # Settings should be reflected in the UI
        assert view.quality_slider.value() == 22

    def test_settings_saved_signal(self, qtbot: QtBot) -> None:
        """Test that save triggers settings_saved signal."""
        view = SettingsView()
        qtbot.addWidget(view)

        with qtbot.waitSignal(view.settings_saved, timeout=1000):
            view._on_save()

    def test_quality_range(self, qtbot: QtBot) -> None:
        """Test quality slider has valid range."""
        view = SettingsView()
        qtbot.addWidget(view)

        # CRF values typically range from 18 to 35 in this app
        assert view.quality_slider.minimum() >= 0
        assert view.quality_slider.maximum() <= 51

    def test_get_settings(self, qtbot: QtBot) -> None:
        """Test getting settings as dictionary."""
        view = SettingsView()
        qtbot.addWidget(view)

        view.quality_slider.setValue(25)

        settings = view.get_settings()

        assert settings["encoding"]["quality"] == 25
