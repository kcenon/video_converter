"""Photos library browser view for the Video Converter GUI.

This module provides a view for browsing and selecting videos from
the macOS Photos library.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from video_converter.gui.widgets.video_grid import VideoGrid


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
        self._selected_videos: list[str] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self._setup_header(layout)

        # Main content with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Album tree
        left_panel = self._create_album_panel()
        splitter.addWidget(left_panel)

        # Right panel: Video grid
        right_panel = self._create_video_panel()
        splitter.addWidget(right_panel)

        # Set initial sizes (30% for albums, 70% for videos)
        splitter.setSizes([300, 700])

        layout.addWidget(splitter, stretch=1)

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

        # Populate with placeholder albums
        self._populate_albums()

        # Filter options
        layout.addSpacing(8)

        self.icloud_checkbox = QCheckBox("Include iCloud videos")
        self.icloud_checkbox.setChecked(True)
        self.icloud_checkbox.stateChanged.connect(self._on_filter_changed)
        layout.addWidget(self.icloud_checkbox)

        self.h264_only_checkbox = QCheckBox("H.264 only")
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

        # Videos header
        self.videos_header = QLabel("Videos (H.264 only)")
        self.videos_header.setObjectName("sectionHeader")
        layout.addWidget(self.videos_header)

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

        # Action buttons
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._on_cancel)
        footer_layout.addWidget(self.cancel_button)

        self.convert_button = QPushButton("Convert")
        self.convert_button.setObjectName("primaryButton")
        self.convert_button.setEnabled(False)
        self.convert_button.clicked.connect(self._on_convert)
        footer_layout.addWidget(self.convert_button)

        parent_layout.addWidget(footer_frame)

    def _populate_albums(self) -> None:
        """Populate the album tree with library albums."""
        self.album_tree.clear()

        # All Videos
        all_videos = QTreeWidgetItem(["All Videos (0)"])
        all_videos.setData(0, Qt.ItemDataRole.UserRole, "all")
        self.album_tree.addTopLevelItem(all_videos)

        # Recents
        recents = QTreeWidgetItem(["Recents (0)"])
        recents.setData(0, Qt.ItemDataRole.UserRole, "recents")
        self.album_tree.addTopLevelItem(recents)

        # User albums (placeholder)
        placeholder = QTreeWidgetItem(["Loading albums..."])
        placeholder.setDisabled(True)
        self.album_tree.addTopLevelItem(placeholder)

        # Select All Videos by default
        all_videos.setSelected(True)

    def _on_album_selected(self) -> None:
        """Handle album selection change."""
        items = self.album_tree.selectedItems()
        if not items:
            return

        album_id = items[0].data(0, Qt.ItemDataRole.UserRole)
        if album_id:
            self._load_videos_for_album(album_id)

    def _load_videos_for_album(self, album_id: str) -> None:
        """Load videos for the selected album.

        Args:
            album_id: Album identifier.
        """
        # This will be implemented to load actual videos
        self.videos_header.setText(f"Videos - {album_id}")
        # TODO: Load videos from Photos library

    def _on_filter_changed(self) -> None:
        """Handle filter option change."""
        # Reload videos with new filters
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
        self._selected_videos = selected_paths
        count = len(selected_paths)

        if count == 0:
            self.selection_label.setText("No videos selected")
            self.convert_button.setEnabled(False)
        else:
            # Calculate total size (placeholder)
            self.selection_label.setText(f"Selected: {count} videos")
            self.convert_button.setEnabled(True)

    def _on_refresh(self) -> None:
        """Refresh the Photos library."""
        self._populate_albums()
        self.video_grid.clear()
        self._selected_videos = []
        self._on_selection_changed([])

    def _on_cancel(self) -> None:
        """Cancel selection."""
        self.video_grid.clear_selection()
        self._selected_videos = []
        self._on_selection_changed([])

    def _on_convert(self) -> None:
        """Start conversion for selected videos."""
        if self._selected_videos:
            self.videos_selected.emit(self._selected_videos)
