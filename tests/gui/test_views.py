"""Tests for GUI views.

This module tests the individual view components: HomeView, ConvertView,
QueueView, SettingsView, and PhotosView.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt

from video_converter.gui.views.home_view import HomeView
from video_converter.gui.views.convert_view import ConvertView
from video_converter.gui.views.queue_view import QueueView
from video_converter.gui.views.settings_view import SettingsView
from video_converter.gui.views.photos_view import PhotosView
from video_converter.gui.services.photos_service import (
    AlbumInfo,
    PhotosService,
    VideoDisplayInfo,
)
from video_converter.gui.widgets.video_grid import VideoItem

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


class TestPhotosView:
    """Tests for PhotosView."""

    @pytest.fixture
    def photos_view(self, qtbot: QtBot) -> PhotosView:
        """Create a PhotosView instance for testing."""
        view = PhotosView()
        qtbot.addWidget(view)
        return view

    @pytest.fixture
    def mock_photos_service(self) -> MagicMock:
        """Create a mock PhotosService."""
        service = MagicMock(spec=PhotosService)
        service.permission_checked = MagicMock()
        service.albums_loaded = MagicMock()
        service.videos_loaded = MagicMock()
        service.thumbnail_loaded = MagicMock()
        service.error_occurred = MagicMock()
        return service

    @pytest.fixture
    def sample_albums(self) -> list[AlbumInfo]:
        """Create sample album data."""
        return [
            AlbumInfo(name="All Videos", video_count=10, album_id="__all__"),
            AlbumInfo(name="Vacation 2024", video_count=5, album_id="vacation_2024"),
            AlbumInfo(name="Family", video_count=3, album_id="family"),
        ]

    @pytest.fixture
    def sample_videos(self) -> list[VideoDisplayInfo]:
        """Create sample video data."""
        return [
            VideoDisplayInfo(
                uuid="uuid-1",
                filename="video1.mp4",
                path=Path("/photos/video1.mp4"),
                duration=120.0,
                duration_str="2:00",
                size=1024 * 1024 * 100,  # 100 MB
                size_str="100.0 MB",
                is_icloud=False,
                is_favorite=True,
                codec="h264",
            ),
            VideoDisplayInfo(
                uuid="uuid-2",
                filename="video2.mp4",
                path=Path("/photos/video2.mp4"),
                duration=300.0,
                duration_str="5:00",
                size=1024 * 1024 * 250,  # 250 MB
                size_str="250.0 MB",
                is_icloud=False,
                is_favorite=False,
                codec="h264",
            ),
            VideoDisplayInfo(
                uuid="uuid-3",
                filename="cloud_video.mp4",
                path=None,
                duration=60.0,
                duration_str="1:00",
                size=1024 * 1024 * 50,  # 50 MB
                size_str="50.0 MB",
                is_icloud=True,
                is_favorite=False,
                codec="h264",
            ),
        ]

    def test_photos_view_creates_successfully(self, photos_view: PhotosView) -> None:
        """Test that PhotosView can be created."""
        assert photos_view is not None

    def test_photos_view_has_album_tree(self, photos_view: PhotosView) -> None:
        """Test that PhotosView has an album tree."""
        assert photos_view.album_tree is not None

    def test_photos_view_has_video_grid(self, photos_view: PhotosView) -> None:
        """Test that PhotosView has a video grid."""
        assert photos_view.video_grid is not None

    def test_photos_view_has_filter_checkboxes(self, photos_view: PhotosView) -> None:
        """Test that PhotosView has filter checkboxes."""
        assert photos_view.icloud_checkbox is not None
        assert photos_view.h264_only_checkbox is not None
        assert photos_view.favorites_checkbox is not None

    def test_photos_view_has_action_buttons(self, photos_view: PhotosView) -> None:
        """Test that PhotosView has action buttons."""
        assert photos_view.refresh_button is not None
        assert photos_view.convert_button is not None
        assert photos_view.cancel_button is not None

    def test_album_tree_initial_state(self, photos_view: PhotosView) -> None:
        """Test that album tree is empty initially."""
        assert photos_view.album_tree.topLevelItemCount() == 0

    def test_icloud_checkbox_default_checked(self, photos_view: PhotosView) -> None:
        """Test that iCloud checkbox is checked by default."""
        assert photos_view.icloud_checkbox.isChecked() is True

    def test_h264_checkbox_default_checked(self, photos_view: PhotosView) -> None:
        """Test that H.264 filter checkbox is checked by default."""
        assert photos_view.h264_only_checkbox.isChecked() is True

    def test_favorites_checkbox_default_unchecked(self, photos_view: PhotosView) -> None:
        """Test that favorites checkbox is unchecked by default."""
        assert photos_view.favorites_checkbox.isChecked() is False

    def test_convert_button_disabled_initially(self, photos_view: PhotosView) -> None:
        """Test that convert button is disabled without selection."""
        assert photos_view.convert_button.isEnabled() is False

    def test_set_photos_service(
        self, photos_view: PhotosView, mock_photos_service: MagicMock
    ) -> None:
        """Test setting the Photos service."""
        photos_view.set_photos_service(mock_photos_service)

        assert photos_view._photos_service is mock_photos_service
        mock_photos_service.permission_checked.connect.assert_called_once()
        mock_photos_service.albums_loaded.connect.assert_called_once()
        mock_photos_service.videos_loaded.connect.assert_called_once()

    def test_on_albums_loaded(
        self, photos_view: PhotosView, sample_albums: list[AlbumInfo]
    ) -> None:
        """Test album tree population."""
        photos_view._on_albums_loaded(sample_albums)

        assert photos_view.album_tree.topLevelItemCount() == 3
        first_item = photos_view.album_tree.topLevelItem(0)
        assert "All Videos" in first_item.text(0)
        assert "(10)" in first_item.text(0)

    def test_album_selection_stores_album_id(
        self, photos_view: PhotosView, sample_albums: list[AlbumInfo], mock_photos_service: MagicMock
    ) -> None:
        """Test that album selection stores the album ID."""
        photos_view.set_photos_service(mock_photos_service)
        photos_view._on_albums_loaded(sample_albums)

        # First album is auto-selected, verify initial state
        assert photos_view._current_album_id == "__all__"

        # Clear selection and select second album
        photos_view.album_tree.clearSelection()
        second_item = photos_view.album_tree.topLevelItem(1)
        second_item.setSelected(True)

        assert photos_view._current_album_id == "vacation_2024"

    def test_on_videos_loaded(
        self, photos_view: PhotosView, sample_videos: list[VideoDisplayInfo]
    ) -> None:
        """Test video grid population."""
        photos_view._current_album_id = "__all__"
        photos_view._on_videos_loaded("__all__", sample_videos)

        assert len(photos_view._current_videos) == 3
        assert "3 videos" in photos_view._video_count_label.text()

    def test_on_videos_loaded_ignores_wrong_album(
        self, photos_view: PhotosView, sample_videos: list[VideoDisplayInfo]
    ) -> None:
        """Test that videos for wrong album are ignored."""
        photos_view._current_album_id = "__all__"
        photos_view._on_videos_loaded("different_album", sample_videos)

        assert len(photos_view._current_videos) == 0

    def test_video_selection_updates_count(
        self, photos_view: PhotosView, sample_videos: list[VideoDisplayInfo]
    ) -> None:
        """Test that video selection updates the selection count."""
        photos_view._current_album_id = "__all__"
        photos_view._on_videos_loaded("__all__", sample_videos)

        # Simulate selection
        selected_paths = [str(sample_videos[0].path)]
        photos_view._on_selection_changed(selected_paths)

        assert "Selected: 1 videos" in photos_view.selection_label.text()
        assert photos_view.convert_button.isEnabled() is True

    def test_multi_select_total_size(
        self, photos_view: PhotosView, sample_videos: list[VideoDisplayInfo]
    ) -> None:
        """Test that multi-select shows total size."""
        photos_view._current_album_id = "__all__"
        photos_view._on_videos_loaded("__all__", sample_videos)

        # Select first two videos
        selected_paths = [str(sample_videos[0].path), str(sample_videos[1].path)]
        photos_view._on_selection_changed(selected_paths)

        assert "Selected: 2 videos" in photos_view.selection_label.text()
        assert "350.0 MB" in photos_view._total_size_label.text()

    def test_clear_selection(
        self, photos_view: PhotosView, sample_videos: list[VideoDisplayInfo]
    ) -> None:
        """Test clearing video selection."""
        photos_view._current_album_id = "__all__"
        photos_view._on_videos_loaded("__all__", sample_videos)

        # Select then clear
        selected_paths = [str(sample_videos[0].path)]
        photos_view._on_selection_changed(selected_paths)
        photos_view._on_cancel()

        assert "No videos selected" in photos_view.selection_label.text()
        assert photos_view.convert_button.isEnabled() is False

    def test_h264_filter_checkbox(
        self, photos_view: PhotosView, mock_photos_service: MagicMock, sample_albums: list[AlbumInfo]
    ) -> None:
        """Test H.264 filter checkbox triggers reload."""
        photos_view.set_photos_service(mock_photos_service)
        photos_view._on_albums_loaded(sample_albums)

        # Select an album first
        photos_view.album_tree.topLevelItem(0).setSelected(True)
        mock_photos_service.load_videos.reset_mock()

        # Toggle H.264 filter
        photos_view.h264_only_checkbox.setChecked(False)

        mock_photos_service.load_videos.assert_called()

    def test_favorites_filter_checkbox(
        self, photos_view: PhotosView, mock_photos_service: MagicMock, sample_albums: list[AlbumInfo]
    ) -> None:
        """Test favorites filter checkbox triggers reload."""
        photos_view.set_photos_service(mock_photos_service)
        photos_view._on_albums_loaded(sample_albums)

        # Select an album first
        photos_view.album_tree.topLevelItem(0).setSelected(True)
        mock_photos_service.load_videos.reset_mock()

        # Toggle favorites filter
        photos_view.favorites_checkbox.setChecked(True)

        mock_photos_service.load_videos.assert_called()

    def test_permission_denied_shows_warning(self, photos_view: PhotosView) -> None:
        """Test that permission denied shows warning panel."""
        photos_view._on_permission_checked(False, "Access denied")

        # Use isHidden() because isVisible() returns False if parent is hidden
        assert photos_view._permission_frame.isHidden() is False
        assert "Access denied" in photos_view._permission_error_label.text()

    def test_permission_granted_hides_warning(self, photos_view: PhotosView) -> None:
        """Test that permission granted hides warning panel."""
        photos_view._on_permission_checked(True, "")

        assert photos_view._permission_frame.isHidden() is True

    def test_loading_indicator_visibility(
        self, photos_view: PhotosView, mock_photos_service: MagicMock
    ) -> None:
        """Test loading indicator visibility."""
        photos_view._show_loading("Loading...")
        assert photos_view._loading_frame.isHidden() is False

        photos_view._hide_loading()
        assert photos_view._loading_frame.isHidden() is True

    def test_refresh_clears_selection(
        self, photos_view: PhotosView, mock_photos_service: MagicMock, sample_videos: list[VideoDisplayInfo]
    ) -> None:
        """Test that refresh clears current selection."""
        photos_view.set_photos_service(mock_photos_service)
        photos_view._current_album_id = "__all__"
        photos_view._on_videos_loaded("__all__", sample_videos)

        # Select a video
        selected_paths = [str(sample_videos[0].path)]
        photos_view._on_selection_changed(selected_paths)

        # Refresh
        photos_view._on_refresh()

        assert len(photos_view._selected_videos) == 0
        assert len(photos_view._current_videos) == 0

    def test_videos_selected_signal(
        self, qtbot: QtBot, photos_view: PhotosView, sample_videos: list[VideoDisplayInfo]
    ) -> None:
        """Test that videos_selected signal is emitted on convert."""
        photos_view._current_album_id = "__all__"
        photos_view._on_videos_loaded("__all__", sample_videos)

        # Select non-iCloud videos
        selected_paths = [str(sample_videos[0].path), str(sample_videos[1].path)]
        photos_view._on_selection_changed(selected_paths)

        with qtbot.waitSignal(photos_view.videos_selected, timeout=1000) as blocker:
            photos_view._on_convert()

        assert len(blocker.args[0]) == 2

    def test_convert_skips_icloud_videos(
        self, qtbot: QtBot, photos_view: PhotosView, sample_videos: list[VideoDisplayInfo]
    ) -> None:
        """Test that iCloud-only videos are skipped on convert."""
        photos_view._current_album_id = "__all__"
        photos_view._on_videos_loaded("__all__", sample_videos)

        # Select including iCloud video (uuid-3 is iCloud)
        photos_view._selected_videos = sample_videos  # All 3 videos

        with patch.object(photos_view, "videos_selected") as mock_signal:
            with patch("PySide6.QtWidgets.QMessageBox.warning"):
                photos_view._on_convert()

            # Only 2 non-iCloud videos should be emitted
            mock_signal.emit.assert_called_once()
            emitted_paths = mock_signal.emit.call_args[0][0]
            assert len(emitted_paths) == 2

    def test_error_handler_hides_loading(self, photos_view: PhotosView) -> None:
        """Test that error handler hides loading indicator."""
        photos_view._show_loading("Loading...")

        with patch("PySide6.QtWidgets.QMessageBox.warning"):
            photos_view._on_error("Test error")

        assert photos_view._loading_frame.isHidden() is True

    def test_selection_label_no_videos(self, photos_view: PhotosView) -> None:
        """Test selection label when no videos selected."""
        photos_view._on_selection_changed([])

        assert "No videos selected" in photos_view.selection_label.text()
        assert photos_view._total_size_label.text() == ""

    def test_selection_size_display_gb(
        self, photos_view: PhotosView
    ) -> None:
        """Test size display in GB for large selections."""
        large_video = VideoDisplayInfo(
            uuid="uuid-large",
            filename="large_video.mp4",
            path=Path("/photos/large_video.mp4"),
            duration=7200.0,
            duration_str="2:00:00",
            size=1024 * 1024 * 1024 * 2,  # 2 GB
            size_str="2.0 GB",
            is_icloud=False,
            is_favorite=False,
            codec="h264",
        )
        photos_view._current_album_id = "__all__"
        photos_view._on_videos_loaded("__all__", [large_video])

        photos_view._on_selection_changed([str(large_video.path)])

        assert "GB" in photos_view._total_size_label.text()
