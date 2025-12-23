"""Progress card widget for the Video Converter GUI.

This module provides a card widget for displaying individual
conversion progress.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)


class ProgressCard(QFrame):
    """Progress card for individual conversion.

    Displays conversion progress for a single video file with
    controls for pause/resume and cancel.

    Signals:
        pause_requested: Emitted when pause is requested.
        cancel_requested: Emitted when cancel is requested.
    """

    pause_requested = Signal()
    cancel_requested = Signal()

    def __init__(
        self,
        task_id: str,
        file_name: str,
        file_size: str,
        parent: QFrame | None = None,
    ) -> None:
        """Initialize the progress card.

        Args:
            task_id: Unique task identifier.
            file_name: Name of the video file.
            file_size: Size of the file as string.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.task_id = task_id
        self._file_name = file_name
        self._file_size = file_size
        self._progress = 0.0
        self._is_paused = False
        self._is_completed = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setObjectName("progressCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Header row
        header_layout = QHBoxLayout()

        # File icon and name
        self.name_label = QLabel(f"📹 {self._file_name}")
        self.name_label.setObjectName("cardTitle")
        header_layout.addWidget(self.name_label)

        header_layout.addStretch()

        # Status label
        self.status_label = QLabel("Queued")
        self.status_label.setObjectName("cardStatus")
        header_layout.addWidget(self.status_label)

        layout.addLayout(header_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # Details row
        details_layout = QHBoxLayout()

        # Progress percentage
        self.progress_label = QLabel("0%")
        details_layout.addWidget(self.progress_label)

        # File size
        self.size_label = QLabel(self._file_size)
        self.size_label.setObjectName("cardInfo")
        details_layout.addWidget(self.size_label)

        details_layout.addStretch()

        # ETA
        self.eta_label = QLabel("ETA: --:--")
        self.eta_label.setObjectName("cardInfo")
        details_layout.addWidget(self.eta_label)

        # Speed
        self.speed_label = QLabel("Speed: --")
        self.speed_label.setObjectName("cardInfo")
        details_layout.addWidget(self.speed_label)

        layout.addLayout(details_layout)

        # Control buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.pause_button = QPushButton("Pause")
        self.pause_button.setObjectName("cardButton")
        self.pause_button.clicked.connect(self._on_pause)
        button_layout.addWidget(self.pause_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("cardButton")
        self.cancel_button.clicked.connect(self.cancel_requested.emit)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

    @property
    def progress(self) -> float:
        """Get current progress percentage."""
        return self._progress

    @property
    def is_completed(self) -> bool:
        """Check if conversion is completed."""
        return self._is_completed

    def update_progress(
        self,
        progress: float,
        eta: str | None = None,
        speed: str | None = None,
    ) -> None:
        """Update conversion progress.

        Args:
            progress: Progress percentage (0-100).
            eta: Estimated time remaining.
            speed: Current encoding speed.
        """
        self._progress = progress
        self.progress_bar.setValue(int(progress))
        self.progress_label.setText(f"{progress:.1f}%")
        self.status_label.setText("Converting")

        if eta:
            self.eta_label.setText(f"ETA: {eta}")
        if speed:
            self.speed_label.setText(f"Speed: {speed}")

    def mark_completed(self, success: bool = True) -> None:
        """Mark conversion as completed.

        Args:
            success: Whether conversion was successful.
        """
        self._is_completed = True
        self.pause_button.setEnabled(False)
        self.cancel_button.setEnabled(False)

        if success:
            self.status_label.setText("✅ Complete")
            self.progress_bar.setValue(100)
            self.progress_label.setText("100%")
        else:
            self.status_label.setText("❌ Failed")

        self.eta_label.setText("")
        self.speed_label.setText("")

    def toggle_pause(self) -> None:
        """Toggle pause state."""
        self._is_paused = not self._is_paused

        if self._is_paused:
            self.pause_button.setText("Resume")
            self.status_label.setText("⏸ Paused")
        else:
            self.pause_button.setText("Pause")
            self.status_label.setText("Converting")

    def _on_pause(self) -> None:
        """Handle pause button click."""
        self.toggle_pause()
        self.pause_requested.emit()
