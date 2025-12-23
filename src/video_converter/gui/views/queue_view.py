"""Conversion queue view for the Video Converter GUI.

This module provides the queue management view for monitoring
and controlling active and pending conversions.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from video_converter.gui.widgets.progress_card import ProgressCard


class QueueView(QWidget):
    """Conversion queue management view.

    Provides interface for:
    - Active conversion progress display
    - Pending conversions queue
    - Queue management (pause, cancel, reorder)
    - Overall progress statistics

    Signals:
        pause_all_requested: Emitted when pause all is requested.
        resume_all_requested: Emitted when resume all is requested.
        cancel_all_requested: Emitted when cancel all is requested.
    """

    pause_all_requested = Signal()
    resume_all_requested = Signal()
    cancel_all_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the queue view.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._progress_cards: dict[str, ProgressCard] = {}
        self._is_paused = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header with overall progress
        self._setup_header(layout)

        # Queue content
        self._setup_queue_content(layout)

        # Empty state
        self._setup_empty_state(layout)

        # Control buttons
        self._setup_controls(layout)

    def _setup_header(self, parent_layout: QVBoxLayout) -> None:
        """Set up the header section.

        Args:
            parent_layout: Parent layout.
        """
        header_frame = QFrame()
        header_frame.setObjectName("queueHeader")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 16, 16, 16)

        # Title row
        title_layout = QHBoxLayout()

        title_label = QLabel("Conversion Queue")
        title_label.setObjectName("viewTitle")
        title_layout.addWidget(title_label)

        title_layout.addStretch()

        self.queue_count_label = QLabel("0 items")
        self.queue_count_label.setObjectName("infoLabel")
        title_layout.addWidget(self.queue_count_label)

        header_layout.addLayout(title_layout)

        # Overall progress
        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 100)
        self.overall_progress.setValue(0)
        self.overall_progress.setTextVisible(True)
        self.overall_progress.setFormat("Overall: %p%")
        header_layout.addWidget(self.overall_progress)

        # Statistics row
        stats_layout = QHBoxLayout()

        self.completed_label = QLabel("Completed: 0")
        stats_layout.addWidget(self.completed_label)

        stats_layout.addStretch()

        self.eta_label = QLabel("ETA: --:--")
        stats_layout.addWidget(self.eta_label)

        stats_layout.addStretch()

        self.speed_label = QLabel("Speed: --")
        stats_layout.addWidget(self.speed_label)

        header_layout.addLayout(stats_layout)

        parent_layout.addWidget(header_frame)

    def _setup_queue_content(self, parent_layout: QVBoxLayout) -> None:
        """Set up the queue content area.

        Args:
            parent_layout: Parent layout.
        """
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.queue_container = QWidget()
        self.queue_layout = QVBoxLayout(self.queue_container)
        self.queue_layout.setContentsMargins(0, 0, 0, 0)
        self.queue_layout.setSpacing(12)
        self.queue_layout.addStretch()

        scroll_area.setWidget(self.queue_container)
        parent_layout.addWidget(scroll_area, stretch=1)

    def _setup_empty_state(self, parent_layout: QVBoxLayout) -> None:
        """Set up the empty state display.

        Args:
            parent_layout: Parent layout.
        """
        self.empty_state = QFrame()
        self.empty_state.setObjectName("emptyState")
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_label = QLabel("No conversions in queue")
        empty_label.setObjectName("emptyStateLabel")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_label)

        hint_label = QLabel("Drop video files on the Home tab to start converting")
        hint_label.setObjectName("emptyStateHint")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(hint_label)

        parent_layout.addWidget(self.empty_state)

    def _setup_controls(self, parent_layout: QVBoxLayout) -> None:
        """Set up control buttons.

        Args:
            parent_layout: Parent layout.
        """
        button_layout = QHBoxLayout()

        self.clear_completed_button = QPushButton("Clear Completed")
        self.clear_completed_button.clicked.connect(self._on_clear_completed)
        self.clear_completed_button.setEnabled(False)
        button_layout.addWidget(self.clear_completed_button)

        button_layout.addStretch()

        self.cancel_all_button = QPushButton("Cancel All")
        self.cancel_all_button.clicked.connect(self._on_cancel_all)
        self.cancel_all_button.setEnabled(False)
        button_layout.addWidget(self.cancel_all_button)

        self.pause_resume_button = QPushButton("Pause All")
        self.pause_resume_button.clicked.connect(self._on_pause_resume)
        self.pause_resume_button.setEnabled(False)
        button_layout.addWidget(self.pause_resume_button)

        parent_layout.addLayout(button_layout)

    def add_conversion(
        self,
        task_id: str,
        file_name: str,
        file_size: str,
    ) -> None:
        """Add a conversion to the queue.

        Args:
            task_id: Unique task identifier.
            file_name: Name of the video file.
            file_size: Size of the file as string.
        """
        card = ProgressCard(task_id, file_name, file_size)
        card.cancel_requested.connect(lambda: self._on_cancel_task(task_id))
        card.pause_requested.connect(lambda: self._on_pause_task(task_id))

        # Insert before the stretch
        self.queue_layout.insertWidget(
            self.queue_layout.count() - 1,
            card,
        )
        self._progress_cards[task_id] = card

        self._update_ui_state()

    def update_progress(
        self,
        task_id: str,
        progress: float,
        eta: str | None = None,
        speed: str | None = None,
    ) -> None:
        """Update conversion progress.

        Args:
            task_id: Task identifier.
            progress: Progress percentage (0-100).
            eta: Estimated time remaining.
            speed: Current encoding speed.
        """
        if task_id in self._progress_cards:
            self._progress_cards[task_id].update_progress(progress, eta, speed)

        self._update_overall_progress()

    def mark_completed(self, task_id: str, success: bool = True) -> None:
        """Mark a conversion as completed.

        Args:
            task_id: Task identifier.
            success: Whether conversion was successful.
        """
        if task_id in self._progress_cards:
            self._progress_cards[task_id].mark_completed(success)
            self.clear_completed_button.setEnabled(True)

        self._update_ui_state()

    def remove_conversion(self, task_id: str) -> None:
        """Remove a conversion from the queue.

        Args:
            task_id: Task identifier.
        """
        if task_id in self._progress_cards:
            card = self._progress_cards.pop(task_id)
            self.queue_layout.removeWidget(card)
            card.deleteLater()

        self._update_ui_state()

    def _update_ui_state(self) -> None:
        """Update UI state based on queue contents."""
        count = len(self._progress_cards)
        has_items = count > 0

        self.queue_count_label.setText(f"{count} items")
        self.empty_state.setVisible(not has_items)
        self.pause_resume_button.setEnabled(has_items)
        self.cancel_all_button.setEnabled(has_items)

    def _update_overall_progress(self) -> None:
        """Update overall progress calculation."""
        if not self._progress_cards:
            self.overall_progress.setValue(0)
            return

        total_progress = sum(card.progress for card in self._progress_cards.values())
        average_progress = total_progress / len(self._progress_cards)
        self.overall_progress.setValue(int(average_progress))

    @Slot()
    def _on_pause_resume(self) -> None:
        """Handle pause/resume all button."""
        if self._is_paused:
            self._is_paused = False
            self.pause_resume_button.setText("Pause All")
            self.resume_all_requested.emit()
        else:
            self._is_paused = True
            self.pause_resume_button.setText("Resume All")
            self.pause_all_requested.emit()

    @Slot()
    def _on_cancel_all(self) -> None:
        """Handle cancel all button."""
        self.cancel_all_requested.emit()

    @Slot()
    def _on_clear_completed(self) -> None:
        """Clear completed conversions."""
        completed_ids = [
            task_id for task_id, card in self._progress_cards.items() if card.is_completed
        ]
        for task_id in completed_ids:
            self.remove_conversion(task_id)

        self.clear_completed_button.setEnabled(False)

    def _on_cancel_task(self, task_id: str) -> None:
        """Handle individual task cancellation.

        Args:
            task_id: Task identifier.
        """
        self.remove_conversion(task_id)

    def _on_pause_task(self, task_id: str) -> None:
        """Handle individual task pause.

        Args:
            task_id: Task identifier.
        """
        if task_id in self._progress_cards:
            self._progress_cards[task_id].toggle_pause()
