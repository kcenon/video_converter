"""Video grid widget for the Video Converter GUI.

This module provides a grid view for displaying video thumbnails
from the Photos library.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


@dataclass
class VideoItem:
    """Data class for video grid items."""

    path: str
    name: str
    duration: str
    size: int  # bytes
    is_icloud: bool = False
    is_favorite: bool = False
    thumbnail: QPixmap | None = None


class VideoThumbnail(QFrame):
    """Individual video thumbnail in the grid."""

    clicked = Signal(str)
    double_clicked = Signal(str)

    THUMBNAIL_SIZE = 120

    def __init__(self, item: VideoItem, parent: QWidget | None = None) -> None:
        """Initialize the thumbnail.

        Args:
            item: Video item data.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._item = item
        self._is_selected = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setObjectName("videoThumbnail")
        self.setFixedSize(self.THUMBNAIL_SIZE + 20, self.THUMBNAIL_SIZE + 50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Thumbnail image
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(self.THUMBNAIL_SIZE, self.THUMBNAIL_SIZE)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setObjectName("thumbnailImage")

        if self._item.thumbnail:
            scaled = self._item.thumbnail.scaled(
                self.THUMBNAIL_SIZE,
                self.THUMBNAIL_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.thumbnail_label.setPixmap(scaled)
        else:
            self.thumbnail_label.setText("🎬")
            self.thumbnail_label.setStyleSheet("font-size: 48px;")

        layout.addWidget(self.thumbnail_label)

        # Name label
        name = self._item.name
        if len(name) > 15:
            name = name[:12] + "..."
        self.name_label = QLabel(name)
        self.name_label.setObjectName("thumbnailName")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setToolTip(self._item.name)
        layout.addWidget(self.name_label)

        # Duration label
        self.duration_label = QLabel(self._item.duration)
        self.duration_label.setObjectName("thumbnailDuration")
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.duration_label)

        # Status icons (iCloud, favorite)
        if self._item.is_icloud or self._item.is_favorite:
            icons = ""
            if self._item.is_icloud:
                icons += "☁️ "
            if self._item.is_favorite:
                icons += "⭐"
            status_label = QLabel(icons.strip())
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(status_label)

    @property
    def path(self) -> str:
        """Get video path."""
        return self._item.path

    @property
    def is_selected(self) -> bool:
        """Check if thumbnail is selected."""
        return self._is_selected

    def set_selected(self, selected: bool) -> None:
        """Set selection state.

        Args:
            selected: Whether to select the thumbnail.
        """
        self._is_selected = selected
        self.setProperty("selected", selected)
        self.style().polish(self)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press.

        Args:
            event: Mouse event.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._item.path)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Handle mouse double click.

        Args:
            event: Mouse event.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self._item.path)
        super().mouseDoubleClickEvent(event)


class VideoGrid(QWidget):
    """Grid of video thumbnails.

    Displays videos in a grid layout with selection support.

    Signals:
        selection_changed: Emitted when selection changes.
        video_double_clicked: Emitted when a video is double-clicked.
    """

    selection_changed = Signal(list)  # List of selected paths
    video_double_clicked = Signal(str)

    COLUMNS = 4

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the grid.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._thumbnails: dict[str, VideoThumbnail] = {}
        self._selected_paths: set[str] = set()
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Grid container
        self._grid_widget = QWidget()
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setContentsMargins(8, 8, 8, 8)
        self._grid_layout.setSpacing(12)
        self._grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        scroll.setWidget(self._grid_widget)
        layout.addWidget(scroll)

        # Empty state
        self._empty_label = QLabel("No videos to display")
        self._empty_label.setObjectName("emptyLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._grid_layout.addWidget(self._empty_label, 0, 0, 1, self.COLUMNS)

    def add_video(self, item: VideoItem) -> None:
        """Add a video to the grid.

        Args:
            item: Video item data.
        """
        # Hide empty label
        if self._empty_label.isVisible():
            self._empty_label.hide()

        # Create thumbnail
        thumbnail = VideoThumbnail(item)
        thumbnail.clicked.connect(self._on_thumbnail_clicked)
        thumbnail.double_clicked.connect(self.video_double_clicked.emit)

        # Add to grid
        count = len(self._thumbnails)
        row = count // self.COLUMNS
        col = count % self.COLUMNS
        self._grid_layout.addWidget(thumbnail, row, col)

        self._thumbnails[item.path] = thumbnail

    def set_videos(self, items: list[VideoItem]) -> None:
        """Set all videos in the grid.

        Args:
            items: List of video items.
        """
        self.clear()
        for item in items:
            self.add_video(item)

    def clear(self) -> None:
        """Clear all videos from the grid."""
        for thumbnail in self._thumbnails.values():
            self._grid_layout.removeWidget(thumbnail)
            thumbnail.deleteLater()

        self._thumbnails.clear()
        self._selected_paths.clear()
        self._empty_label.show()

    def clear_selection(self) -> None:
        """Clear current selection."""
        for path in self._selected_paths:
            if path in self._thumbnails:
                self._thumbnails[path].set_selected(False)

        self._selected_paths.clear()
        self.selection_changed.emit([])

    def _on_thumbnail_clicked(self, path: str) -> None:
        """Handle thumbnail click.

        Args:
            path: Video path.
        """
        # Toggle selection
        if path in self._selected_paths:
            self._selected_paths.remove(path)
            self._thumbnails[path].set_selected(False)
        else:
            self._selected_paths.add(path)
            self._thumbnails[path].set_selected(True)

        self.selection_changed.emit(list(self._selected_paths))

    def get_selected_paths(self) -> list[str]:
        """Get list of selected video paths.

        Returns:
            List of selected paths.
        """
        return list(self._selected_paths)

    def update_thumbnail(self, path: str, pixmap: QPixmap) -> None:
        """Update thumbnail for a specific video.

        Args:
            path: Video path.
            pixmap: New thumbnail pixmap.
        """
        if path in self._thumbnails:
            thumbnail = self._thumbnails[path]
            scaled = pixmap.scaled(
                VideoThumbnail.THUMBNAIL_SIZE,
                VideoThumbnail.THUMBNAIL_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            thumbnail.thumbnail_label.setPixmap(scaled)
            thumbnail.thumbnail_label.setStyleSheet("")
