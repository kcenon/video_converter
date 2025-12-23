"""Home view (dashboard) for the Video Converter GUI.

This module provides the home/dashboard view with drag & drop zone
and recent conversions list.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from video_converter.gui.widgets.drop_zone import DropZone
from video_converter.gui.widgets.recent_list import RecentConversionsList


class HomeView(QWidget):
    """Home/Dashboard view.

    Provides the main landing view with:
    - Drag & drop zone for video files
    - Quick access buttons
    - Recent conversions list
    - Summary statistics

    Signals:
        file_dropped: Emitted when a file is dropped on the drop zone.
        browse_photos_requested: Emitted when Photos browse is requested.
    """

    file_dropped = Signal(str)
    browse_photos_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the home view.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Welcome section
        welcome_label = QLabel("Welcome to Video Converter")
        welcome_label.setObjectName("welcomeLabel")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome_label)

        subtitle_label = QLabel(
            "Convert H.264 videos to H.265 (HEVC) with hardware acceleration"
        )
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle_label)

        layout.addSpacing(10)

        # Drop zone
        self.drop_zone = DropZone()
        self.drop_zone.file_dropped.connect(self.file_dropped.emit)
        layout.addWidget(self.drop_zone)

        # Quick action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        self.browse_button = QPushButton("Browse Photos Library")
        self.browse_button.setObjectName("primaryButton")
        self.browse_button.clicked.connect(self.browse_photos_requested.emit)
        button_layout.addWidget(self.browse_button)

        self.open_file_button = QPushButton("Open Video File")
        self.open_file_button.clicked.connect(self._on_open_file)
        button_layout.addWidget(self.open_file_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        layout.addSpacing(10)

        # Recent conversions section
        recent_header = QLabel("Recent Conversions")
        recent_header.setObjectName("sectionHeader")
        layout.addWidget(recent_header)

        # Recent conversions list in scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.recent_list = RecentConversionsList()
        scroll_area.setWidget(self.recent_list)
        layout.addWidget(scroll_area, stretch=1)

        # Statistics bar
        self._setup_stats_bar(layout)

    def _setup_stats_bar(self, parent_layout: QVBoxLayout) -> None:
        """Set up the statistics bar.

        Args:
            parent_layout: Parent layout to add the stats bar to.
        """
        stats_frame = QFrame()
        stats_frame.setObjectName("statsBar")
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(16, 12, 16, 12)

        # Hardware encoder status
        self.encoder_label = QLabel("Hardware Encoder: Checking...")
        self.encoder_label.setObjectName("statsLabel")
        stats_layout.addWidget(self.encoder_label)

        stats_layout.addStretch()

        # Space saved
        self.space_saved_label = QLabel("Space Saved: Calculating...")
        self.space_saved_label.setObjectName("statsLabel")
        stats_layout.addWidget(self.space_saved_label)

        stats_layout.addStretch()

        # Videos converted
        self.videos_converted_label = QLabel("Videos Converted: 0")
        self.videos_converted_label.setObjectName("statsLabel")
        stats_layout.addWidget(self.videos_converted_label)

        parent_layout.addWidget(stats_frame)

    def _on_open_file(self) -> None:
        """Handle open file button click."""
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video File",
            "",
            "Video Files (*.mp4 *.mov *.avi *.mkv *.m4v);;All Files (*)",
        )
        if file_path:
            self.file_dropped.emit(file_path)

    def update_stats(
        self,
        encoder_available: bool,
        space_saved_bytes: int,
        videos_converted: int,
    ) -> None:
        """Update statistics display.

        Args:
            encoder_available: Whether hardware encoder is available.
            space_saved_bytes: Total space saved in bytes.
            videos_converted: Total number of videos converted.
        """
        encoder_status = "Active" if encoder_available else "Not Available"
        self.encoder_label.setText(f"Hardware Encoder: {encoder_status}")

        # Format bytes to human-readable
        if space_saved_bytes >= 1_000_000_000:
            space_str = f"{space_saved_bytes / 1_000_000_000:.1f} GB"
        elif space_saved_bytes >= 1_000_000:
            space_str = f"{space_saved_bytes / 1_000_000:.1f} MB"
        else:
            space_str = f"{space_saved_bytes / 1_000:.1f} KB"

        self.space_saved_label.setText(f"Space Saved: {space_str}")
        self.videos_converted_label.setText(f"Videos Converted: {videos_converted}")
