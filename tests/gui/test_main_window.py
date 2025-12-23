"""Tests for the MainWindow.

This module tests the main window creation, navigation,
and integration between views and services.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTabBar

from video_converter.gui.main_window import MainWindow

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
        # Configure mock settings manager
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

        # Configure mock conversion service
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

        # Configure mock photos service
        mock_photos_instance = MagicMock()
        mock_photos.return_value = mock_photos_instance

        yield {
            "conversion": mock_conv_instance,
            "photos": mock_photos_instance,
            "settings": mock_settings_instance,
        }


class TestMainWindowCreation:
    """Tests for MainWindow creation and initialization."""

    def test_main_window_creates_successfully(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test that MainWindow can be created without errors."""
        window = MainWindow()
        qtbot.addWidget(window)

        assert window is not None
        window.close()

    def test_main_window_has_correct_title(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test that MainWindow has the correct title."""
        window = MainWindow()
        qtbot.addWidget(window)

        assert window.windowTitle() == "Video Converter"
        window.close()

    def test_main_window_minimum_size(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test that MainWindow has correct minimum size."""
        window = MainWindow()
        qtbot.addWidget(window)

        assert window.minimumWidth() == MainWindow.MIN_WIDTH
        assert window.minimumHeight() == MainWindow.MIN_HEIGHT
        window.close()

    def test_main_window_has_tab_bar(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test that MainWindow has a navigation tab bar."""
        window = MainWindow()
        qtbot.addWidget(window)

        assert isinstance(window.tab_bar, QTabBar)
        assert window.tab_bar.count() == 5
        window.close()

    def test_main_window_tab_names(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test that tabs have correct names."""
        window = MainWindow()
        qtbot.addWidget(window)

        expected_tabs = ["Home", "Convert", "Photos", "Queue", "Settings"]
        for i, name in enumerate(expected_tabs):
            assert window.tab_bar.tabText(i) == name
        window.close()


class TestMainWindowViews:
    """Tests for MainWindow views."""

    def test_has_all_views(self, qtbot: QtBot, mock_services) -> None:
        """Test that MainWindow has all required views."""
        window = MainWindow()
        qtbot.addWidget(window)

        assert window.home_view is not None
        assert window.convert_view is not None
        assert window.photos_view is not None
        assert window.queue_view is not None
        assert window.settings_view is not None
        window.close()

    def test_stacked_widget_has_views(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test that stacked widget contains all views."""
        window = MainWindow()
        qtbot.addWidget(window)

        assert window.stacked_widget.count() == 5
        window.close()


class TestMainWindowNavigation:
    """Tests for MainWindow tab navigation."""

    def test_tab_change_updates_view(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test that changing tab updates the displayed view."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Start at Home
        assert window.stacked_widget.currentIndex() == 0

        # Switch to Convert
        window.tab_bar.setCurrentIndex(MainWindow.TAB_CONVERT)
        assert window.stacked_widget.currentIndex() == MainWindow.TAB_CONVERT

        # Switch to Settings
        window.tab_bar.setCurrentIndex(MainWindow.TAB_SETTINGS)
        assert window.stacked_widget.currentIndex() == MainWindow.TAB_SETTINGS
        window.close()

    def test_set_current_tab(self, qtbot: QtBot, mock_services) -> None:
        """Test _set_current_tab method."""
        window = MainWindow()
        qtbot.addWidget(window)

        window._set_current_tab(MainWindow.TAB_QUEUE)
        assert window.tab_bar.currentIndex() == MainWindow.TAB_QUEUE
        window.close()


class TestMainWindowMenuBar:
    """Tests for MainWindow menu bar."""

    def test_has_menu_bar(self, qtbot: QtBot, mock_services) -> None:
        """Test that MainWindow has a menu bar."""
        window = MainWindow()
        qtbot.addWidget(window)

        menu_bar = window.menuBar()
        assert menu_bar is not None
        window.close()

    def test_has_file_menu(self, qtbot: QtBot, mock_services) -> None:
        """Test that menu bar has File menu."""
        window = MainWindow()
        qtbot.addWidget(window)

        menu_bar = window.menuBar()
        actions = menu_bar.actions()
        menu_titles = [action.text() for action in actions]

        assert "File" in menu_titles
        window.close()


class TestMainWindowStatusBar:
    """Tests for MainWindow status bar."""

    def test_has_status_bar(self, qtbot: QtBot, mock_services) -> None:
        """Test that MainWindow has a status bar."""
        window = MainWindow()
        qtbot.addWidget(window)

        assert window.statusBar() is not None
        window.close()

    def test_initial_status_message(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test initial status bar message."""
        window = MainWindow()
        qtbot.addWidget(window)

        assert window.statusBar().currentMessage() == "Ready"
        window.close()


class TestMainWindowFileHandling:
    """Tests for file handling in MainWindow."""

    def test_file_dropped_switches_to_convert(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test that dropping a file switches to Convert view."""
        window = MainWindow()
        qtbot.addWidget(window)

        window._on_file_dropped("/path/to/video.mp4")

        assert window.tab_bar.currentIndex() == MainWindow.TAB_CONVERT
        window.close()

    def test_files_dropped_switches_to_queue(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test that dropping multiple files switches to Queue view."""
        window = MainWindow()
        qtbot.addWidget(window)

        window._on_files_dropped(["/path/to/video1.mp4", "/path/to/video2.mp4"])

        assert window.tab_bar.currentIndex() == MainWindow.TAB_QUEUE
        window.close()

    def test_files_dropped_adds_to_queue(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test that dropped files are added to conversion queue."""
        window = MainWindow()
        qtbot.addWidget(window)

        files = ["/path/to/video1.mp4", "/path/to/video2.mp4"]
        window._on_files_dropped(files)

        # Verify add_task was called for each file
        assert mock_services["conversion"].add_task.call_count == 2
        window.close()


class TestMainWindowServices:
    """Tests for MainWindow service properties."""

    def test_conversion_service_property(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test conversion_service property."""
        window = MainWindow()
        qtbot.addWidget(window)

        assert window.conversion_service is not None
        window.close()

    def test_photos_service_property(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test photos_service property."""
        window = MainWindow()
        qtbot.addWidget(window)

        assert window.photos_service is not None
        window.close()


class TestMainWindowCleanup:
    """Tests for MainWindow cleanup on close."""

    def test_close_shuts_down_services(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test that closing window shuts down services."""
        window = MainWindow()
        qtbot.addWidget(window)

        window.close()

        mock_services["conversion"].shutdown.assert_called_once()
        mock_services["photos"].shutdown.assert_called_once()

    def test_close_saves_dirty_settings(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test that closing saves settings if dirty."""
        mock_services["settings"].is_dirty.return_value = True

        window = MainWindow()
        qtbot.addWidget(window)

        window.close()

        mock_services["settings"].save.assert_called()
