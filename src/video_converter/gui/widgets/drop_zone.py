"""Drag and drop zone widget for the Video Converter GUI.

This module provides a drop zone widget for accepting video files
via drag and drop, with support for folders and enhanced visual feedback.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QMouseEvent,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

if TYPE_CHECKING:
    from PySide6.QtGui import QPaintEvent


class DropZone(QWidget):
    """Drag and drop zone for video files and folders.

    Provides a visual drop zone that accepts video files and folders,
    with enhanced visual feedback during drag operations.

    Features:
        - Single and multiple file drop support
        - Folder drop support (recursively finds video files)
        - Visual feedback showing file count during drag
        - File type validation with visual indication
        - Click to browse support

    Signals:
        file_dropped: Emitted when a single file is dropped.
        files_dropped: Emitted when multiple files are dropped.
    """

    # Supported video extensions
    SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm", ".wmv"}

    file_dropped = Signal(str)
    files_dropped = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the drop zone.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._is_drag_over = False
        self._drag_valid = False
        self._pending_file_count = 0
        self._default_main_text = "Drop video files here"
        self._default_subtitle_text = "or click to browse"
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setAcceptDrops(True)
        self.setMinimumHeight(150)
        self.setObjectName("dropZone")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon/emoji
        self.icon_label = QLabel("📁")
        self.icon_label.setObjectName("dropZoneIcon")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)

        # Main text
        self.main_label = QLabel("Drop video files here")
        self.main_label.setObjectName("dropZoneMain")
        self.main_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.main_label)

        # Subtitle
        self.subtitle_label = QLabel("or click to browse")
        self.subtitle_label.setObjectName("dropZoneSubtitle")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.subtitle_label)

        # Supported formats
        formats = ", ".join(ext.upper()[1:] for ext in sorted(self.SUPPORTED_EXTENSIONS))
        self.formats_label = QLabel(f"Supported: {formats}")
        self.formats_label.setObjectName("dropZoneFormats")
        self.formats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.formats_label)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the drop zone with dashed border.

        Border color indicates drag state:
        - Gray: Idle state
        - Blue: Valid files being dragged
        - Red: Invalid files being dragged

        Args:
            event: Paint event.
        """
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Choose border color based on drag state
        if self._is_drag_over:
            if self._drag_valid:
                # Valid drop: blue border
                pen = QPen(QColor("#007AFF"))
                pen.setWidth(3)
            else:
                # Invalid drop: red border
                pen = QPen(QColor("#FF3B30"))
                pen.setWidth(2)
        else:
            pen = QPen(Qt.GlobalColor.gray)
            pen.setWidth(1)

        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)

        # Draw rounded rectangle
        margin = 8
        painter.drawRoundedRect(
            margin,
            margin,
            self.width() - 2 * margin,
            self.height() - 2 * margin,
            12,
            12,
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter event.

        Accepts both video files and folders containing video files.
        Shows file count and validation feedback during drag.

        Args:
            event: Drag enter event.
        """
        if event.mimeData().hasUrls():
            valid_files = self._count_valid_files(event.mimeData().urls())

            if valid_files > 0:
                event.acceptProposedAction()
                self._set_drag_over(True, valid=True, file_count=valid_files)
                return
            else:
                # Show invalid drag feedback (red border)
                event.acceptProposedAction()
                self._set_drag_over(True, valid=False, file_count=0)
                return

        event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """Handle drag move event.

        Maintains visual feedback during drag movement.

        Args:
            event: Drag move event.
        """
        if self._is_drag_over:
            event.acceptProposedAction()
        else:
            event.ignore()

    def _count_valid_files(self, urls: list) -> int:
        """Count valid video files from URLs.

        Handles both direct file drops and folder drops.
        For folders, recursively counts video files inside.

        Args:
            urls: List of QUrl objects.

        Returns:
            Number of valid video files.
        """
        count = 0
        for url in urls:
            if url.isLocalFile():
                path = Path(url.toLocalFile())
                if path.is_file():
                    if path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                        count += 1
                elif path.is_dir():
                    # Count video files in folder (non-recursive for performance)
                    count += self._count_videos_in_folder(path, recursive=False)
        return count

    def _count_videos_in_folder(self, folder: Path, recursive: bool = False) -> int:
        """Count video files in a folder.

        Args:
            folder: Folder path.
            recursive: Whether to search recursively.

        Returns:
            Number of video files found.
        """
        count = 0
        try:
            pattern = "**/*" if recursive else "*"
            for item in folder.glob(pattern):
                if item.is_file() and item.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    count += 1
        except (PermissionError, OSError):
            pass
        return count

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        """Handle drag leave event.

        Args:
            event: Drag leave event.
        """
        self._set_drag_over(False, valid=False, file_count=0)
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop event.

        Processes both file drops and folder drops.
        For folders, extracts all video files.

        Args:
            event: Drop event.
        """
        self._set_drag_over(False, valid=False, file_count=0)

        if not event.mimeData().hasUrls():
            event.ignore()
            return

        valid_files = self._extract_valid_files(event.mimeData().urls())

        if valid_files:
            event.acceptProposedAction()

            if len(valid_files) == 1:
                self.file_dropped.emit(valid_files[0])
            else:
                self.files_dropped.emit(valid_files)
        else:
            event.ignore()

    def _extract_valid_files(self, urls: list) -> list[str]:
        """Extract valid video files from URLs.

        Handles both direct file drops and folder drops.
        For folders, extracts all video files at the top level.

        Args:
            urls: List of QUrl objects.

        Returns:
            List of valid video file paths.
        """
        valid_files: list[str] = []

        for url in urls:
            if url.isLocalFile():
                path = Path(url.toLocalFile())
                if path.is_file():
                    if path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                        valid_files.append(str(path))
                elif path.is_dir():
                    # Extract video files from folder
                    valid_files.extend(self._extract_videos_from_folder(path))

        return valid_files

    def _extract_videos_from_folder(self, folder: Path, recursive: bool = False) -> list[str]:
        """Extract video files from a folder.

        Args:
            folder: Folder path.
            recursive: Whether to search recursively.

        Returns:
            List of video file paths.
        """
        videos: list[str] = []
        try:
            pattern = "**/*" if recursive else "*"
            for item in folder.glob(pattern):
                if item.is_file() and item.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    videos.append(str(item))
        except (PermissionError, OSError):
            pass
        return sorted(videos)

    def _set_drag_over(self, is_over: bool, *, valid: bool = True, file_count: int = 0) -> None:
        """Set drag over state with visual feedback.

        Updates the drop zone appearance to indicate:
        - Whether items are being dragged over
        - Whether the items are valid video files
        - How many valid files will be added

        Args:
            is_over: Whether drag is over the widget.
            valid: Whether the dragged items are valid video files.
            file_count: Number of valid video files being dragged.
        """
        self._is_drag_over = is_over
        self._drag_valid = valid
        self._pending_file_count = file_count
        self.update()

        if is_over:
            if valid and file_count > 0:
                # Valid files: show count
                if file_count == 1:
                    self.main_label.setText("Release to add 1 video")
                else:
                    self.main_label.setText(f"Release to add {file_count} videos")
                self.subtitle_label.setText("Drop now!")
            else:
                # Invalid files: show warning
                self.main_label.setText("No valid video files")
                self.subtitle_label.setText("Only video files are supported")
            self.setProperty("dragOver", True)
        else:
            # Reset to default state
            self.main_label.setText(self._default_main_text)
            self.subtitle_label.setText(self._default_subtitle_text)
            self.setProperty("dragOver", False)

        self.style().polish(self)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press to open file dialog.

        Args:
            event: Mouse press event.
        """
        from PySide6.QtWidgets import QFileDialog

        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Video Files",
            "",
            "Video Files (*.mp4 *.mov *.avi *.mkv *.m4v);;All Files (*)",
        )

        if file_paths:
            if len(file_paths) == 1:
                self.file_dropped.emit(file_paths[0])
            else:
                self.files_dropped.emit(file_paths)
