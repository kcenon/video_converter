"""Tests for the VideoGrid widget.

This module tests the VideoItem dataclass, VideoThumbnail widget,
and VideoGrid container for displaying video thumbnails.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from video_converter.gui.widgets.video_grid import VideoGrid, VideoItem, VideoThumbnail

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


pytestmark = pytest.mark.gui


class TestVideoItem:
    """Tests for VideoItem dataclass."""

    def test_video_item_creation(self) -> None:
        """Test that VideoItem can be created with required fields."""
        item = VideoItem(
            path="/path/to/video.mp4",
            name="video.mp4",
            duration="01:30",
            size=1024000,
        )

        assert item.path == "/path/to/video.mp4"
        assert item.name == "video.mp4"
        assert item.duration == "01:30"
        assert item.size == 1024000

    def test_video_item_default_values(self) -> None:
        """Test VideoItem default values."""
        item = VideoItem(
            path="/path/to/video.mp4",
            name="video.mp4",
            duration="01:30",
            size=1024000,
        )

        assert item.is_icloud is False
        assert item.is_favorite is False
        assert item.thumbnail is None

    def test_video_item_with_icloud(self) -> None:
        """Test VideoItem with iCloud flag set."""
        item = VideoItem(
            path="/path/to/video.mp4",
            name="video.mp4",
            duration="01:30",
            size=1024000,
            is_icloud=True,
        )

        assert item.is_icloud is True

    def test_video_item_with_favorite(self) -> None:
        """Test VideoItem with favorite flag set."""
        item = VideoItem(
            path="/path/to/video.mp4",
            name="video.mp4",
            duration="01:30",
            size=1024000,
            is_favorite=True,
        )

        assert item.is_favorite is True

    def test_video_item_with_thumbnail(self, qtbot: QtBot) -> None:
        """Test VideoItem with a thumbnail pixmap."""
        pixmap = QPixmap(100, 100)
        item = VideoItem(
            path="/path/to/video.mp4",
            name="video.mp4",
            duration="01:30",
            size=1024000,
            thumbnail=pixmap,
        )

        assert item.thumbnail is not None
        assert item.thumbnail.width() == 100


class TestVideoThumbnail:
    """Tests for VideoThumbnail widget."""

    def test_thumbnail_creation(self, qtbot: QtBot) -> None:
        """Test that VideoThumbnail can be created."""
        item = VideoItem(
            path="/path/to/video.mp4",
            name="video.mp4",
            duration="01:30",
            size=1024000,
        )
        thumbnail = VideoThumbnail(item)
        qtbot.addWidget(thumbnail)

        assert thumbnail is not None
        assert thumbnail.path == "/path/to/video.mp4"

    def test_thumbnail_size(self, qtbot: QtBot) -> None:
        """Test that thumbnail has correct fixed size."""
        item = VideoItem(
            path="/path/to/video.mp4",
            name="video.mp4",
            duration="01:30",
            size=1024000,
        )
        thumbnail = VideoThumbnail(item)
        qtbot.addWidget(thumbnail)

        expected_width = VideoThumbnail.THUMBNAIL_SIZE + 20
        expected_height = VideoThumbnail.THUMBNAIL_SIZE + 50

        assert thumbnail.width() == expected_width
        assert thumbnail.height() == expected_height

    def test_thumbnail_labels(self, qtbot: QtBot) -> None:
        """Test that thumbnail has required labels."""
        item = VideoItem(
            path="/path/to/video.mp4",
            name="test_video.mp4",
            duration="02:45",
            size=1024000,
        )
        thumbnail = VideoThumbnail(item)
        qtbot.addWidget(thumbnail)

        assert thumbnail.name_label is not None
        assert thumbnail.duration_label is not None
        assert thumbnail.thumbnail_label is not None
        assert thumbnail.duration_label.text() == "02:45"

    def test_thumbnail_long_name_truncation(self, qtbot: QtBot) -> None:
        """Test that long names are truncated."""
        item = VideoItem(
            path="/path/to/video.mp4",
            name="very_long_video_filename.mp4",
            duration="01:30",
            size=1024000,
        )
        thumbnail = VideoThumbnail(item)
        qtbot.addWidget(thumbnail)

        # Name should be truncated to 12 chars + "..."
        assert len(thumbnail.name_label.text()) <= 15
        assert thumbnail.name_label.text().endswith("...")
        assert thumbnail.name_label.toolTip() == "very_long_video_filename.mp4"

    def test_thumbnail_click_signal(self, qtbot: QtBot) -> None:
        """Test that clicking thumbnail emits clicked signal."""
        item = VideoItem(
            path="/path/to/video.mp4",
            name="video.mp4",
            duration="01:30",
            size=1024000,
        )
        thumbnail = VideoThumbnail(item)
        qtbot.addWidget(thumbnail)

        with qtbot.waitSignal(thumbnail.clicked, timeout=1000) as blocker:
            qtbot.mouseClick(thumbnail, Qt.MouseButton.LeftButton)

        assert blocker.args[0] == "/path/to/video.mp4"

    def test_thumbnail_double_click_signal(self, qtbot: QtBot) -> None:
        """Test that double-clicking emits double_clicked signal."""
        item = VideoItem(
            path="/path/to/video.mp4",
            name="video.mp4",
            duration="01:30",
            size=1024000,
        )
        thumbnail = VideoThumbnail(item)
        qtbot.addWidget(thumbnail)

        with qtbot.waitSignal(thumbnail.double_clicked, timeout=1000) as blocker:
            qtbot.mouseDClick(thumbnail, Qt.MouseButton.LeftButton)

        assert blocker.args[0] == "/path/to/video.mp4"

    def test_thumbnail_selection_default(self, qtbot: QtBot) -> None:
        """Test that thumbnail is not selected by default."""
        item = VideoItem(
            path="/path/to/video.mp4",
            name="video.mp4",
            duration="01:30",
            size=1024000,
        )
        thumbnail = VideoThumbnail(item)
        qtbot.addWidget(thumbnail)

        assert thumbnail.is_selected is False

    def test_thumbnail_selection_state(self, qtbot: QtBot) -> None:
        """Test thumbnail selection state changes."""
        item = VideoItem(
            path="/path/to/video.mp4",
            name="video.mp4",
            duration="01:30",
            size=1024000,
        )
        thumbnail = VideoThumbnail(item)
        qtbot.addWidget(thumbnail)

        thumbnail.set_selected(True)
        assert thumbnail.is_selected is True

        thumbnail.set_selected(False)
        assert thumbnail.is_selected is False

    def test_icloud_badge_visible(self, qtbot: QtBot) -> None:
        """Test that iCloud badge is displayed for iCloud items."""
        item = VideoItem(
            path="/path/to/video.mp4",
            name="video.mp4",
            duration="01:30",
            size=1024000,
            is_icloud=True,
        )
        thumbnail = VideoThumbnail(item)
        qtbot.addWidget(thumbnail)

        # Find status label with iCloud icon
        labels = thumbnail.findChildren(type(thumbnail.name_label))
        has_icloud_icon = any("☁️" in label.text() for label in labels)
        assert has_icloud_icon is True

    def test_favorite_badge_visible(self, qtbot: QtBot) -> None:
        """Test that favorite badge is displayed for favorite items."""
        item = VideoItem(
            path="/path/to/video.mp4",
            name="video.mp4",
            duration="01:30",
            size=1024000,
            is_favorite=True,
        )
        thumbnail = VideoThumbnail(item)
        qtbot.addWidget(thumbnail)

        # Find status label with favorite icon
        labels = thumbnail.findChildren(type(thumbnail.name_label))
        has_favorite_icon = any("⭐" in label.text() for label in labels)
        assert has_favorite_icon is True

    def test_thumbnail_with_pixmap(self, qtbot: QtBot) -> None:
        """Test thumbnail displays pixmap when provided."""
        pixmap = QPixmap(200, 200)
        pixmap.fill(Qt.GlobalColor.blue)

        item = VideoItem(
            path="/path/to/video.mp4",
            name="video.mp4",
            duration="01:30",
            size=1024000,
            thumbnail=pixmap,
        )
        thumbnail = VideoThumbnail(item)
        qtbot.addWidget(thumbnail)

        # Thumbnail label should have a pixmap
        assert thumbnail.thumbnail_label.pixmap() is not None


class TestVideoGrid:
    """Tests for VideoGrid widget."""

    def test_grid_creation(self, qtbot: QtBot) -> None:
        """Test that VideoGrid can be created."""
        grid = VideoGrid()
        qtbot.addWidget(grid)

        assert grid is not None

    def test_grid_initial_state(self, qtbot: QtBot) -> None:
        """Test VideoGrid initial state with empty label."""
        grid = VideoGrid()
        qtbot.addWidget(grid)

        # Empty label should exist and not be hidden
        assert grid._empty_label is not None
        assert grid._empty_label.isHidden() is False
        assert "No videos" in grid._empty_label.text()

    def test_add_single_video(self, qtbot: QtBot) -> None:
        """Test adding a single video to the grid."""
        grid = VideoGrid()
        qtbot.addWidget(grid)

        item = VideoItem(
            path="/path/to/video.mp4",
            name="video.mp4",
            duration="01:30",
            size=1024000,
        )
        grid.add_video(item)

        assert len(grid._thumbnails) == 1
        assert "/path/to/video.mp4" in grid._thumbnails
        assert grid._empty_label.isVisible() is False

    def test_add_multiple_videos(self, qtbot: QtBot) -> None:
        """Test adding multiple videos to the grid."""
        grid = VideoGrid()
        qtbot.addWidget(grid)

        for i in range(5):
            item = VideoItem(
                path=f"/path/to/video{i}.mp4",
                name=f"video{i}.mp4",
                duration="01:30",
                size=1024000,
            )
            grid.add_video(item)

        assert len(grid._thumbnails) == 5

    def test_set_videos(self, qtbot: QtBot) -> None:
        """Test setting all videos at once."""
        grid = VideoGrid()
        qtbot.addWidget(grid)

        items = [
            VideoItem(
                path=f"/path/to/video{i}.mp4",
                name=f"video{i}.mp4",
                duration="01:30",
                size=1024000,
            )
            for i in range(3)
        ]
        grid.set_videos(items)

        assert len(grid._thumbnails) == 3

    def test_clear_grid(self, qtbot: QtBot) -> None:
        """Test clearing all videos from the grid."""
        grid = VideoGrid()
        qtbot.addWidget(grid)

        # Add some videos
        for i in range(3):
            item = VideoItem(
                path=f"/path/to/video{i}.mp4",
                name=f"video{i}.mp4",
                duration="01:30",
                size=1024000,
            )
            grid.add_video(item)

        # Clear
        grid.clear()

        assert len(grid._thumbnails) == 0
        assert grid._empty_label.isHidden() is False

    def test_selection_on_click(self, qtbot: QtBot) -> None:
        """Test that clicking a thumbnail selects it."""
        grid = VideoGrid()
        qtbot.addWidget(grid)

        item = VideoItem(
            path="/path/to/video.mp4",
            name="video.mp4",
            duration="01:30",
            size=1024000,
        )
        grid.add_video(item)

        # Simulate thumbnail click via internal method
        grid._on_thumbnail_clicked("/path/to/video.mp4")

        selected = grid.get_selected_paths()
        assert len(selected) == 1
        assert "/path/to/video.mp4" in selected

    def test_toggle_selection(self, qtbot: QtBot) -> None:
        """Test toggling selection on repeated clicks."""
        grid = VideoGrid()
        qtbot.addWidget(grid)

        item = VideoItem(
            path="/path/to/video.mp4",
            name="video.mp4",
            duration="01:30",
            size=1024000,
        )
        grid.add_video(item)

        # First click - select
        grid._on_thumbnail_clicked("/path/to/video.mp4")
        assert len(grid.get_selected_paths()) == 1

        # Second click - deselect
        grid._on_thumbnail_clicked("/path/to/video.mp4")
        assert len(grid.get_selected_paths()) == 0

    def test_multi_select(self, qtbot: QtBot) -> None:
        """Test selecting multiple videos."""
        grid = VideoGrid()
        qtbot.addWidget(grid)

        for i in range(3):
            item = VideoItem(
                path=f"/path/to/video{i}.mp4",
                name=f"video{i}.mp4",
                duration="01:30",
                size=1024000,
            )
            grid.add_video(item)

        # Select multiple
        grid._on_thumbnail_clicked("/path/to/video0.mp4")
        grid._on_thumbnail_clicked("/path/to/video1.mp4")
        grid._on_thumbnail_clicked("/path/to/video2.mp4")

        selected = grid.get_selected_paths()
        assert len(selected) == 3

    def test_clear_selection(self, qtbot: QtBot) -> None:
        """Test clearing selection."""
        grid = VideoGrid()
        qtbot.addWidget(grid)

        for i in range(2):
            item = VideoItem(
                path=f"/path/to/video{i}.mp4",
                name=f"video{i}.mp4",
                duration="01:30",
                size=1024000,
            )
            grid.add_video(item)

        # Select some
        grid._on_thumbnail_clicked("/path/to/video0.mp4")
        grid._on_thumbnail_clicked("/path/to/video1.mp4")

        # Clear selection
        grid.clear_selection()

        assert len(grid.get_selected_paths()) == 0

    def test_selection_changed_signal(self, qtbot: QtBot) -> None:
        """Test that selection_changed signal is emitted."""
        grid = VideoGrid()
        qtbot.addWidget(grid)

        item = VideoItem(
            path="/path/to/video.mp4",
            name="video.mp4",
            duration="01:30",
            size=1024000,
        )
        grid.add_video(item)

        with qtbot.waitSignal(grid.selection_changed, timeout=1000) as blocker:
            grid._on_thumbnail_clicked("/path/to/video.mp4")

        assert "/path/to/video.mp4" in blocker.args[0]

    def test_video_double_clicked_signal(self, qtbot: QtBot) -> None:
        """Test that video_double_clicked signal is emitted."""
        grid = VideoGrid()
        qtbot.addWidget(grid)

        item = VideoItem(
            path="/path/to/video.mp4",
            name="video.mp4",
            duration="01:30",
            size=1024000,
        )
        grid.add_video(item)

        with qtbot.waitSignal(grid.video_double_clicked, timeout=1000) as blocker:
            # Emit signal directly through thumbnail
            grid._thumbnails["/path/to/video.mp4"].double_clicked.emit("/path/to/video.mp4")

        assert blocker.args[0] == "/path/to/video.mp4"

    def test_update_thumbnail(self, qtbot: QtBot) -> None:
        """Test updating thumbnail for a specific video."""
        grid = VideoGrid()
        qtbot.addWidget(grid)

        item = VideoItem(
            path="/path/to/video.mp4",
            name="video.mp4",
            duration="01:30",
            size=1024000,
        )
        grid.add_video(item)

        # Create new pixmap
        new_pixmap = QPixmap(200, 200)
        new_pixmap.fill(Qt.GlobalColor.red)

        grid.update_thumbnail("/path/to/video.mp4", new_pixmap)

        # Verify thumbnail was updated
        thumbnail = grid._thumbnails["/path/to/video.mp4"]
        assert thumbnail.thumbnail_label.pixmap() is not None

    def test_grid_columns(self, qtbot: QtBot) -> None:
        """Test that grid uses correct number of columns."""
        grid = VideoGrid()
        qtbot.addWidget(grid)

        assert grid.COLUMNS == 4

    def test_get_selected_paths_returns_list(self, qtbot: QtBot) -> None:
        """Test that get_selected_paths returns a list."""
        grid = VideoGrid()
        qtbot.addWidget(grid)

        result = grid.get_selected_paths()
        assert isinstance(result, list)
