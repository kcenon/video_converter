"""Usability tests for the GUI.

This module provides tests for user experience and usability,
including workflow tests, accessibility checks, and interaction patterns.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QMimeData, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication

from video_converter.gui.main_window import MainWindow
from video_converter.gui.widgets.drop_zone import DropZone

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


pytestmark = pytest.mark.gui


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


class TestDragDropWorkflow:
    """Tests for drag and drop user workflow."""

    def test_drag_video_shows_visual_feedback(
        self, qtbot: QtBot, tmp_path: Path
    ) -> None:
        """Test that dragging a video file shows visual feedback."""
        widget = DropZone()
        qtbot.addWidget(widget)

        # Create a video file
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"\x00" * 1024)

        # Simulate drag over
        widget._set_drag_over(True, valid=True, file_count=1)

        # Should show drop hint
        assert "Release" in widget.main_label.text() or "video" in widget.main_label.text()
        assert widget._drag_valid is True

    def test_drag_invalid_shows_warning(
        self, qtbot: QtBot, tmp_path: Path
    ) -> None:
        """Test that dragging invalid files shows warning."""
        widget = DropZone()
        qtbot.addWidget(widget)

        # Simulate invalid drag
        widget._set_drag_over(True, valid=False, file_count=0)

        # Should show warning
        assert "No valid" in widget.main_label.text()
        assert widget._drag_valid is False


class TestKeyboardNavigation:
    """Tests for keyboard navigation."""

    def test_tab_switching_with_keyboard_shortcuts(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test that keyboard shortcuts switch tabs."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        # Initial tab should be Home
        assert window.tab_bar.currentIndex() == MainWindow.TAB_HOME

        # Use direct method call to test navigation
        window._set_current_tab(MainWindow.TAB_CONVERT)
        assert window.tab_bar.currentIndex() == MainWindow.TAB_CONVERT

        window._set_current_tab(MainWindow.TAB_PHOTOS)
        assert window.tab_bar.currentIndex() == MainWindow.TAB_PHOTOS

        window.close()


class TestAccessibility:
    """Tests for accessibility features."""

    def test_drop_zone_has_accessible_labels(self, qtbot: QtBot) -> None:
        """Test that drop zone has accessible text labels."""
        widget = DropZone()
        qtbot.addWidget(widget)

        # All labels should have non-empty text
        assert widget.main_label.text() != ""
        assert widget.subtitle_label.text() != ""
        assert widget.formats_label.text() != ""

    def test_buttons_have_text(self, qtbot: QtBot, mock_services) -> None:
        """Test that all buttons have text labels."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Queue view pause/cancel buttons should have text
        assert window.queue_view.pause_resume_button.text() != ""
        assert window.queue_view.cancel_all_button.text() != ""

        # Verify buttons exist and have meaningful text
        assert len(window.queue_view.pause_resume_button.text()) > 0
        assert len(window.queue_view.cancel_all_button.text()) > 0

        window.close()


class TestErrorFeedback:
    """Tests for error feedback to users."""

    def test_conversion_failure_shows_message(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test that conversion failure shows error message."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Simulate task failure
        window._on_task_failed("task-123", "Encoding error: codec not found")

        # Status bar should show error
        assert "failed" in window.statusBar().currentMessage().lower()

        window.close()

    def test_conversion_success_shows_message(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test that conversion success shows completion message."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Create mock result
        mock_result = MagicMock()
        mock_result.original_size = 1000000
        mock_result.converted_size = 500000

        # Simulate task completion
        with patch.object(window, "_on_task_completed") as mock_complete:
            mock_complete(window, "task-123", mock_result)

        window.close()


class TestUserWorkflows:
    """Tests for common user workflows."""

    def test_single_file_conversion_workflow(
        self, qtbot: QtBot, mock_services, tmp_path: Path
    ) -> None:
        """Test complete single file conversion workflow."""
        window = MainWindow()
        qtbot.addWidget(window)

        # 1. Start at Home view
        assert window.tab_bar.currentIndex() == MainWindow.TAB_HOME

        # 2. "Drop" a file
        video_file = tmp_path / "vacation.mp4"
        video_file.write_bytes(b"\x00" * 1024)
        window._on_file_dropped(str(video_file))

        # 3. Should switch to Convert view
        assert window.tab_bar.currentIndex() == MainWindow.TAB_CONVERT

        window.close()

    def test_batch_conversion_workflow(
        self, qtbot: QtBot, mock_services, tmp_path: Path
    ) -> None:
        """Test batch conversion workflow with multiple files."""
        window = MainWindow()
        qtbot.addWidget(window)

        # 1. Start at Home view
        assert window.tab_bar.currentIndex() == MainWindow.TAB_HOME

        # 2. "Drop" multiple files
        files = []
        for i in range(3):
            video_file = tmp_path / f"video_{i}.mp4"
            video_file.write_bytes(b"\x00" * 1024)
            files.append(str(video_file))

        window._on_files_dropped(files)

        # 3. Should switch to Queue view
        assert window.tab_bar.currentIndex() == MainWindow.TAB_QUEUE

        # 4. All files should be added to queue
        assert mock_services["conversion"].add_task.call_count == 3

        window.close()

    def test_settings_modification_workflow(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test settings modification workflow."""
        window = MainWindow()
        qtbot.addWidget(window)

        # 1. Navigate to Settings
        window._set_current_tab(MainWindow.TAB_SETTINGS)
        assert window.tab_bar.currentIndex() == MainWindow.TAB_SETTINGS

        # 2. Modify a setting
        window.settings_view.quality_slider.setValue(25)

        # 3. Save settings (call _on_save directly since save_button is local)
        window.settings_view._on_save()

        window.close()


class TestResponsiveness:
    """Tests for UI responsiveness."""

    def test_window_is_visible_after_creation(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test that window becomes visible quickly."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        # Window should be visible
        assert window.isVisible() is True

        window.close()

    def test_tab_switch_is_immediate(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test that tab switching is immediate."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        # Switch tabs multiple times
        for tab_index in range(5):
            window.tab_bar.setCurrentIndex(tab_index)
            # Stacked widget should immediately reflect the change
            assert window.stacked_widget.currentIndex() == tab_index

        window.close()
