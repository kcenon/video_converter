"""Drag and drop zone widget for the Video Converter GUI.

This module provides a drop zone widget for accepting video files
via drag and drop.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent, QPainter, QPen
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

if TYPE_CHECKING:
    from PySide6.QtGui import QPaintEvent


class DropZone(QWidget):
    """Drag and drop zone for video files.

    Provides a visual drop zone that accepts video files and emits
    signals when files are dropped.

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

        Args:
            event: Paint event.
        """
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw dashed border
        if self._is_drag_over:
            pen = QPen(Qt.GlobalColor.blue)
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

        Args:
            event: Drag enter event.
        """
        if event.mimeData().hasUrls():
            # Check if any URL is a supported video file
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    path = Path(url.toLocalFile())
                    if path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                        event.acceptProposedAction()
                        self._set_drag_over(True)
                        return

        event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        """Handle drag leave event.

        Args:
            event: Drag leave event.
        """
        self._set_drag_over(False)
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop event.

        Args:
            event: Drop event.
        """
        self._set_drag_over(False)

        if not event.mimeData().hasUrls():
            event.ignore()
            return

        valid_files: list[str] = []

        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = Path(url.toLocalFile())
                if path.suffix.lower() in self.SUPPORTED_EXTENSIONS and path.is_file():
                    valid_files.append(str(path))

        if valid_files:
            event.acceptProposedAction()

            if len(valid_files) == 1:
                self.file_dropped.emit(valid_files[0])
            else:
                self.files_dropped.emit(valid_files)
        else:
            event.ignore()

    def _set_drag_over(self, is_over: bool) -> None:
        """Set drag over state.

        Args:
            is_over: Whether drag is over the widget.
        """
        self._is_drag_over = is_over
        self.update()

        if is_over:
            self.main_label.setText("Release to add files")
            self.setProperty("dragOver", True)
        else:
            self.main_label.setText("Drop video files here")
            self.setProperty("dragOver", False)

        self.style().polish(self)

    def mousePressEvent(self, event) -> None:
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
