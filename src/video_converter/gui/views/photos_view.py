"""Photos library browser view for the Video Converter GUI.

This module provides a view for browsing and selecting videos from
the macOS Photos library.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from video_converter.gui.services.photos_service import (
    AlbumInfo,
    PhotosService,
    VideoDisplayInfo,
)
from video_converter.gui.widgets.video_grid import VideoGrid, VideoItem

if TYPE_CHECKING:
    from PySide6.QtGui import QPixmap


logger = logging.getLogger(__name__)


class PhotosView(QWidget):
    """Photos library browser view.

    Provides interface for:
    - Album tree navigation
    - Video grid with thumbnails
    - Multi-selection for batch conversion
    - iCloud status display

    Signals:
        videos_selected: Emitted when videos are selected for conversion.
    """

    videos_selected = Signal(list)  # List of video paths

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the photos view.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._selected_videos: list[VideoDisplayInfo] = []
        self._current_videos: list[VideoDisplayInfo] = {}
        self._current_album_id: str = "__all__"
        self._photos_service: PhotosService | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self._setup_header(layout)

        # Permission warning (hidden by default)
        self._setup_permission_warning(layout)

        # Loading indicator (hidden by default)
        self._setup_loading_indicator(layout)

        # Main content with splitter
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Album tree
        left_panel = self._create_album_panel()
        self._splitter.addWidget(left_panel)

        # Right panel: Video grid
        right_panel = self._create_video_panel()
        self._splitter.addWidget(right_panel)

        # Set initial sizes (30% for albums, 70% for videos)
        self._splitter.setSizes([300, 700])

        layout.addWidget(self._splitter, stretch=1)

        # Footer with selection info and actions
        self._setup_footer(layout)

    def _setup_header(self, parent_layout: QVBoxLayout) -> None:
        """Set up the header section.

        Args:
            parent_layout: Parent layout.
        """
        header_frame = QFrame()
        header_frame.setObjectName("viewHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 12, 16, 12)

        title_label = QLabel("Photos Library")
        title_label.setObjectName("viewTitle")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._on_refresh)
        header_layout.addWidget(self.refresh_button)

        parent_layout.addWidget(header_frame)

    def _setup_permission_warning(self, parent_layout: QVBoxLayout) -> None:
        """Set up the permission warning section.

        Args:
            parent_layout: Parent layout.
        """
        self._permission_frame = QFrame()
        self._permission_frame.setObjectName("warningFrame")
        self._permission_frame.setVisible(False)

        permission_layout = QVBoxLayout(self._permission_frame)
        permission_layout.setContentsMargins(16, 12, 16, 12)

        warning_label = QLabel(
            "Photos library access denied. Please grant Full Disk Access permission."
        )
        warning_label.setObjectName("warningLabel")
        warning_label.setWordWrap(True)
        permission_layout.addWidget(warning_label)

        self._permission_error_label = QLabel()
        self._permission_error_label.setObjectName("errorLabel")
        self._permission_error_label.setWordWrap(True)
        permission_layout.addWidget(self._permission_error_label)

        button_layout = QHBoxLayout()
        open_settings_button = QPushButton("Open System Settings")
        open_settings_button.clicked.connect(self._open_system_settings)
        button_layout.addWidget(open_settings_button)
        button_layout.addStretch()
        permission_layout.addLayout(button_layout)

        parent_layout.addWidget(self._permission_frame)

    def _setup_loading_indicator(self, parent_layout: QVBoxLayout) -> None:
        """Set up the loading indicator.

        Args:
            parent_layout: Parent layout.
        """
        self._loading_frame = QFrame()
        self._loading_frame.setObjectName("loadingFrame")
        self._loading_frame.setVisible(False)

        loading_layout = QHBoxLayout(self._loading_frame)
        loading_layout.setContentsMargins(16, 8, 16, 8)

        self._loading_label = QLabel("Loading...")
        loading_layout.addWidget(self._loading_label)

        self._loading_progress = QProgressBar()
        self._loading_progress.setMaximum(0)  # Indeterminate
        self._loading_progress.setMinimumWidth(200)
        loading_layout.addWidget(self._loading_progress)

        loading_layout.addStretch()

        parent_layout.addWidget(self._loading_frame)

    def _create_album_panel(self) -> QWidget:
        """Create the album tree panel.

        Returns:
            Album panel widget.
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 8, 16)

        # Albums header
        header_label = QLabel("Albums")
        header_label.setObjectName("sectionHeader")
        layout.addWidget(header_label)

        # Album tree
        self.album_tree = QTreeWidget()
        self.album_tree.setHeaderHidden(True)
        self.album_tree.setIndentation(16)
        self.album_tree.itemSelectionChanged.connect(self._on_album_selected)
        layout.addWidget(self.album_tree, stretch=1)

        # Filter options
        layout.addSpacing(8)

        self.icloud_checkbox = QCheckBox("Include iCloud videos")
        self.icloud_checkbox.setChecked(True)
        self.icloud_checkbox.stateChanged.connect(self._on_filter_changed)
        layout.addWidget(self.icloud_checkbox)

        self.h264_only_checkbox = QCheckBox("H.264 only (convertible)")
        self.h264_only_checkbox.setChecked(True)
        self.h264_only_checkbox.stateChanged.connect(self._on_filter_changed)
        layout.addWidget(self.h264_only_checkbox)

        self.favorites_checkbox = QCheckBox("Favorites only")
        self.favorites_checkbox.stateChanged.connect(self._on_filter_changed)
        layout.addWidget(self.favorites_checkbox)

        return panel

    def _create_video_panel(self) -> QWidget:
        """Create the video grid panel.

        Returns:
            Video panel widget.
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 16, 16, 16)

        # Videos header with count
        header_layout = QHBoxLayout()
        self.videos_header = QLabel("Videos")
        self.videos_header.setObjectName("sectionHeader")
        header_layout.addWidget(self.videos_header)

        header_layout.addStretch()

        self._video_count_label = QLabel("0 videos")
        self._video_count_label.setObjectName("infoLabel")
        header_layout.addWidget(self._video_count_label)

        layout.addLayout(header_layout)

        # Video grid
        self.video_grid = VideoGrid()
        self.video_grid.selection_changed.connect(self._on_selection_changed)
        layout.addWidget(self.video_grid, stretch=1)

        return panel

    def _setup_footer(self, parent_layout: QVBoxLayout) -> None:
        """Set up the footer section.

        Args:
            parent_layout: Parent layout.
        """
        footer_frame = QFrame()
        footer_frame.setObjectName("viewFooter")
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(16, 12, 16, 12)

        # Selection info
        self.selection_label = QLabel("No videos selected")
        self.selection_label.setObjectName("infoLabel")
        footer_layout.addWidget(self.selection_label)

        footer_layout.addStretch()

        # Total size indicator
        self._total_size_label = QLabel()
        self._total_size_label.setObjectName("infoLabel")
        footer_layout.addWidget(self._total_size_label)

        footer_layout.addSpacing(16)

        # Action buttons
        self.cancel_button = QPushButton("Clear Selection")
        self.cancel_button.clicked.connect(self._on_cancel)
        footer_layout.addWidget(self.cancel_button)

        self.convert_button = QPushButton("Convert Selected")
        self.convert_button.setObjectName("primaryButton")
        self.convert_button.setEnabled(False)
        self.convert_button.clicked.connect(self._on_convert)
        footer_layout.addWidget(self.convert_button)

        parent_layout.addWidget(footer_frame)

    def set_photos_service(self, service: PhotosService) -> None:
        """Set the Photos service.

        Args:
            service: PhotosService instance.
        """
        self._photos_service = service

        # Connect service signals
        service.permission_checked.connect(self._on_permission_checked)
        service.albums_loaded.connect(self._on_albums_loaded)
        service.videos_loaded.connect(self._on_videos_loaded)
        service.thumbnail_loaded.connect(self._on_thumbnail_loaded)
        service.error_occurred.connect(self._on_error)

    def initialize(self) -> None:
        """Initialize the view by checking permissions and loading data."""
        if self._photos_service is None:
            return

        self._show_loading("Checking Photos library access...")
        self._photos_service.check_permission()

    def _show_loading(self, message: str) -> None:
        """Show loading indicator.

        Args:
            message: Loading message.
        """
        self._loading_label.setText(message)
        self._loading_frame.setVisible(True)

    def _hide_loading(self) -> None:
        """Hide loading indicator."""
        self._loading_frame.setVisible(False)

    def _on_permission_checked(self, has_permission: bool, error: str) -> None:
        """Handle permission check result.

        Args:
            has_permission: Whether permission is granted.
            error: Error message if denied.
        """
        self._hide_loading()

        if has_permission:
            self._permission_frame.setVisible(False)
            self._splitter.setVisible(True)
            self._load_albums()
        else:
            self._permission_error_label.setText(error)
            self._permission_frame.setVisible(True)
            self._splitter.setVisible(False)

    def _load_albums(self) -> None:
        """Load albums from Photos library."""
        if self._photos_service is None:
            return

        self._show_loading("Loading albums...")
        self._photos_service.load_albums()

    def _on_albums_loaded(self, albums: list[AlbumInfo]) -> None:
        """Handle albums loaded.

        Args:
            albums: List of album info.
        """
        self._hide_loading()
        self.album_tree.clear()

        for album in albums:
            item = QTreeWidgetItem([f"{album.name} ({album.video_count})"])
            item.setData(0, Qt.ItemDataRole.UserRole, album.album_id)

            # Add icon for special albums
            if album.album_id == "__all__":
                item.setIcon(0, self.style().standardIcon(
                    self.style().StandardPixmap.SP_DirHomeIcon
                ))
            else:
                item.setIcon(0, self.style().standardIcon(
                    self.style().StandardPixmap.SP_DirIcon
                ))

            self.album_tree.addTopLevelItem(item)

        # Select first album (All Videos)
        if self.album_tree.topLevelItemCount() > 0:
            self.album_tree.topLevelItem(0).setSelected(True)

    def _on_album_selected(self) -> None:
        """Handle album selection change."""
        items = self.album_tree.selectedItems()
        if not items:
            return

        album_id = items[0].data(0, Qt.ItemDataRole.UserRole)
        if album_id:
            self._current_album_id = album_id
            self._load_videos_for_album(album_id)

    def _load_videos_for_album(self, album_id: str) -> None:
        """Load videos for the selected album.

        Args:
            album_id: Album identifier.
        """
        if self._photos_service is None:
            return

        self._show_loading("Loading videos...")
        self.video_grid.clear()

        self._photos_service.load_videos(
            album_id=album_id,
            include_icloud=self.icloud_checkbox.isChecked(),
            h264_only=self.h264_only_checkbox.isChecked(),
            favorites_only=self.favorites_checkbox.isChecked(),
        )

    def _on_videos_loaded(self, album_id: str, videos: list[VideoDisplayInfo]) -> None:
        """Handle videos loaded.

        Args:
            album_id: Album that was loaded.
            videos: List of video display info.
        """
        self._hide_loading()

        if album_id != self._current_album_id:
            return

        self._current_videos = {v.uuid: v for v in videos}

        # Update header
        filter_text = ""
        if self.h264_only_checkbox.isChecked():
            filter_text = " (H.264 only)"
        self.videos_header.setText(f"Videos{filter_text}")
        self._video_count_label.setText(f"{len(videos)} videos")

        # Populate grid
        self.video_grid.clear()
        for video in videos:
            item = VideoItem(
                path=str(video.path) if video.path else video.uuid,
                name=video.filename,
                duration=video.duration_str,
                size=video.size,
                is_icloud=video.is_icloud,
                is_favorite=video.is_favorite,
            )
            self.video_grid.add_video(item)

            # Request thumbnail generation
            if video.path and self._photos_service:
                self._photos_service.generate_thumbnail(
                    video.uuid,
                    str(video.path),
                )

    def _on_thumbnail_loaded(self, video_uuid: str, pixmap: QPixmap) -> None:
        """Handle thumbnail loaded.

        Args:
            video_uuid: Video UUID.
            pixmap: Loaded thumbnail.
        """
        # Find video and update thumbnail
        if video_uuid in self._current_videos:
            video = self._current_videos[video_uuid]
            path = str(video.path) if video.path else video_uuid
            self.video_grid.update_thumbnail(path, pixmap)

    def _on_filter_changed(self) -> None:
        """Handle filter option change."""
        items = self.album_tree.selectedItems()
        if items:
            album_id = items[0].data(0, Qt.ItemDataRole.UserRole)
            if album_id:
                self._load_videos_for_album(album_id)

    def _on_selection_changed(self, selected_paths: list[str]) -> None:
        """Handle video selection change.

        Args:
            selected_paths: List of selected video paths.
        """
        # Map paths back to VideoDisplayInfo
        self._selected_videos = []
        for path in selected_paths:
            for video in self._current_videos.values():
                video_path = str(video.path) if video.path else video.uuid
                if video_path == path:
                    self._selected_videos.append(video)
                    break

        count = len(self._selected_videos)

        if count == 0:
            self.selection_label.setText("No videos selected")
            self._total_size_label.setText("")
            self.convert_button.setEnabled(False)
        else:
            # Calculate total size
            total_size = sum(v.size for v in self._selected_videos)
            if total_size >= 1024 * 1024 * 1024:
                size_str = f"{total_size / (1024 * 1024 * 1024):.1f} GB"
            elif total_size >= 1024 * 1024:
                size_str = f"{total_size / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{total_size / 1024:.1f} KB"

            self.selection_label.setText(f"Selected: {count} videos")
            self._total_size_label.setText(f"Total: {size_str}")
            self.convert_button.setEnabled(True)

    def _on_refresh(self) -> None:
        """Refresh the Photos library."""
        self.video_grid.clear()
        self._selected_videos = []
        self._current_videos = {}
        self._on_selection_changed([])
        self._load_albums()

    def _on_cancel(self) -> None:
        """Cancel selection."""
        self.video_grid.clear_selection()
        self._selected_videos = []
        self._on_selection_changed([])

    def _on_convert(self) -> None:
        """Start conversion for selected videos."""
        if not self._selected_videos:
            return

        # Filter out iCloud-only videos
        convertible = [v for v in self._selected_videos if not v.is_icloud]
        icloud_count = len(self._selected_videos) - len(convertible)

        if icloud_count > 0:
            QMessageBox.warning(
                self,
                "iCloud Videos",
                f"{icloud_count} video(s) are stored in iCloud only and will be "
                "skipped. Please download them in the Photos app first.",
            )

        if convertible:
            paths = [str(v.path) for v in convertible if v.path]
            self.videos_selected.emit(paths)

    def _on_error(self, error: str) -> None:
        """Handle error from Photos service.

        Args:
            error: Error message.
        """
        self._hide_loading()
        logger.error(f"Photos service error: {error}")
        QMessageBox.warning(self, "Error", error)

    def _open_system_settings(self) -> None:
        """Open macOS System Settings for Full Disk Access."""
        import subprocess

        subprocess.run(
            ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"],
            check=False,
        )
