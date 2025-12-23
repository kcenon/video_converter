"""Menubar application for the Video Converter GUI.

This module provides the macOS menubar (system tray) application for
background monitoring and quick access to conversion status.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from video_converter.gui.services.conversion_service import ConversionService


class MenubarApp(QObject):
    """Menubar application for background conversion monitoring.

    Provides a system tray icon with a menu for monitoring conversion
    progress, accessing the main window, and controlling conversions.

    Signals:
        show_main_window_requested: Emitted when user requests main window.
        quit_requested: Emitted when user requests to quit the application.

    Attributes:
        tray_icon: The system tray icon.
        tray_menu: The context menu for the tray icon.
    """

    show_main_window_requested = Signal()
    quit_requested = Signal()

    # Status icons (using text for now, can be replaced with actual icons)
    ICON_IDLE = "🎬"
    ICON_CONVERTING = "⏳"
    ICON_COMPLETE = "✅"
    ICON_ERROR = "❌"

    def __init__(
        self,
        conversion_service: ConversionService,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the menubar application.

        Args:
            conversion_service: The conversion service to monitor.
            parent: Parent widget.
        """
        super().__init__(parent)

        self._conversion_service = conversion_service
        self._current_progress = 0.0
        self._converting_count = 0
        self._total_count = 0
        self._is_paused = False

        self._setup_tray_icon()
        self._setup_menu()
        self._connect_signals()

    def _setup_tray_icon(self) -> None:
        """Set up the system tray icon."""
        self.tray_icon = QSystemTrayIcon(self)

        # Use a default icon (can be customized with actual icon file)
        icon = QIcon.fromTheme("video-display")
        if icon.isNull():
            # Fallback to application icon
            from PySide6.QtWidgets import QApplication

            icon = QApplication.instance().windowIcon()

        if not icon.isNull():
            self.tray_icon.setIcon(icon)

        self.tray_icon.setToolTip("Video Converter - Idle")
        self.tray_icon.activated.connect(self._on_tray_activated)

    def _setup_menu(self) -> None:
        """Set up the tray icon context menu."""
        self.tray_menu = QMenu()

        # Status header (non-clickable)
        self._status_action = QAction("Video Converter", self)
        self._status_action.setEnabled(False)
        self.tray_menu.addAction(self._status_action)

        self.tray_menu.addSeparator()

        # Progress section
        self._progress_action = QAction("No active conversions", self)
        self._progress_action.setEnabled(False)
        self.tray_menu.addAction(self._progress_action)

        self._progress_bar_action = QAction("", self)
        self._progress_bar_action.setEnabled(False)
        self._progress_bar_action.setVisible(False)
        self.tray_menu.addAction(self._progress_bar_action)

        # Current task info
        self._current_task_action = QAction("", self)
        self._current_task_action.setEnabled(False)
        self._current_task_action.setVisible(False)
        self.tray_menu.addAction(self._current_task_action)

        self.tray_menu.addSeparator()

        # Control actions
        self._open_action = QAction("Open Main Window...", self)
        self._open_action.triggered.connect(self._on_open_main_window)
        self.tray_menu.addAction(self._open_action)

        self._pause_action = QAction("Pause All", self)
        self._pause_action.triggered.connect(self._on_pause_all)
        self._pause_action.setEnabled(False)
        self.tray_menu.addAction(self._pause_action)

        self._cancel_action = QAction("Cancel All", self)
        self._cancel_action.triggered.connect(self._on_cancel_all)
        self._cancel_action.setEnabled(False)
        self.tray_menu.addAction(self._cancel_action)

        self.tray_menu.addSeparator()

        # Quit action
        self._quit_action = QAction("Quit Video Converter", self)
        self._quit_action.triggered.connect(self._on_quit)
        self.tray_menu.addAction(self._quit_action)

        self.tray_icon.setContextMenu(self.tray_menu)

    def _connect_signals(self) -> None:
        """Connect conversion service signals."""
        self._conversion_service.task_added.connect(self._on_task_added)
        self._conversion_service.task_started.connect(self._on_task_started)
        self._conversion_service.progress_updated.connect(self._on_progress_updated)
        self._conversion_service.task_completed.connect(self._on_task_completed)
        self._conversion_service.task_failed.connect(self._on_task_failed)
        self._conversion_service.all_completed.connect(self._on_all_completed)
        self._conversion_service.queue_updated.connect(self._on_queue_updated)

    def show(self) -> None:
        """Show the tray icon."""
        self.tray_icon.show()

    def hide(self) -> None:
        """Hide the tray icon."""
        self.tray_icon.hide()

    def is_visible(self) -> bool:
        """Check if the tray icon is visible.

        Returns:
            True if the tray icon is visible.
        """
        return self.tray_icon.isVisible()

    def show_notification(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
        duration_ms: int = 5000,
    ) -> None:
        """Show a system notification.

        Args:
            title: Notification title.
            message: Notification message.
            icon: Icon to display with the notification.
            duration_ms: How long to show the notification in milliseconds.
        """
        if self.tray_icon.supportsMessages():
            self.tray_icon.showMessage(title, message, icon, duration_ms)

    def _update_status_display(self) -> None:
        """Update the menu status display based on current state."""
        status = self._conversion_service.get_queue_status()
        converting = status["converting"]
        queued = status["queued"]
        total = converting + queued

        if converting > 0:
            # Active conversion
            self._progress_action.setText(f"Converting: {converting} of {total}")
            self._progress_action.setVisible(True)

            # Show progress bar
            progress_percent = int(self._current_progress)
            filled = progress_percent // 5  # 20 chars total
            empty = 20 - filled
            bar = "▓" * filled + "░" * empty
            self._progress_bar_action.setText(f"{bar} {progress_percent}%")
            self._progress_bar_action.setVisible(True)

            # Enable controls
            self._pause_action.setEnabled(True)
            self._cancel_action.setEnabled(True)

            if self._is_paused:
                self._pause_action.setText("Resume All")
            else:
                self._pause_action.setText("Pause All")

            # Update tooltip
            self.tray_icon.setToolTip(
                f"Video Converter - Converting {converting}/{total} ({progress_percent}%)"
            )

        elif queued > 0:
            # Queued but not converting
            self._progress_action.setText(f"{queued} video(s) queued")
            self._progress_action.setVisible(True)
            self._progress_bar_action.setVisible(False)

            self._pause_action.setEnabled(True)
            self._cancel_action.setEnabled(True)

            self.tray_icon.setToolTip(f"Video Converter - {queued} queued")

        else:
            # Idle
            self._progress_action.setText("No active conversions")
            self._progress_action.setVisible(True)
            self._progress_bar_action.setVisible(False)
            self._current_task_action.setVisible(False)

            self._pause_action.setEnabled(False)
            self._cancel_action.setEnabled(False)

            self.tray_icon.setToolTip("Video Converter - Idle")

    @Slot(object)
    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation.

        Args:
            reason: The activation reason.
        """
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single click - show main window
            self.show_main_window_requested.emit()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # Double click - show main window
            self.show_main_window_requested.emit()

    @Slot()
    def _on_open_main_window(self) -> None:
        """Handle open main window action."""
        self.show_main_window_requested.emit()

    @Slot()
    def _on_pause_all(self) -> None:
        """Handle pause/resume all action."""
        if self._is_paused:
            self._conversion_service.resume_all()
            self._is_paused = False
            self._pause_action.setText("Pause All")
        else:
            self._conversion_service.pause_all()
            self._is_paused = True
            self._pause_action.setText("Resume All")

    @Slot()
    def _on_cancel_all(self) -> None:
        """Handle cancel all action."""
        self._conversion_service.cancel_all()

    @Slot()
    def _on_quit(self) -> None:
        """Handle quit action."""
        self.quit_requested.emit()

    @Slot(str, str, str)
    def _on_task_added(self, task_id: str, file_name: str, file_size: str) -> None:
        """Handle task added to queue.

        Args:
            task_id: Task ID.
            file_name: Name of the video file.
            file_size: File size string.
        """
        self._update_status_display()

    @Slot(str)
    def _on_task_started(self, task_id: str) -> None:
        """Handle task started.

        Args:
            task_id: Task ID.
        """
        task = self._conversion_service.get_task(task_id)
        if task:
            self._current_task_action.setText(f"  {task.file_name}")
            self._current_task_action.setVisible(True)
        self._update_status_display()

    @Slot(str, float, object, object)
    def _on_progress_updated(
        self,
        task_id: str,
        progress: float,
        eta_seconds: int | None,
        speed: str | None,
    ) -> None:
        """Handle progress update.

        Args:
            task_id: Task ID.
            progress: Progress percentage.
            eta_seconds: Estimated time remaining.
            speed: Encoding speed string.
        """
        self._current_progress = progress

        # Update current task info with ETA
        task = self._conversion_service.get_task(task_id)
        if task:
            eta_str = ""
            if eta_seconds is not None:
                minutes = eta_seconds // 60
                seconds = eta_seconds % 60
                eta_str = f" - ETA: {minutes}:{seconds:02d}"
            self._current_task_action.setText(f"  {task.file_name}{eta_str}")
            self._current_task_action.setVisible(True)

        self._update_status_display()

    @Slot(str, object)
    def _on_task_completed(self, task_id: str, result) -> None:
        """Handle task completion.

        Args:
            task_id: Task ID.
            result: ConversionResult object.
        """
        self._current_progress = 0.0
        self._current_task_action.setVisible(False)
        self._update_status_display()

        # Show notification for single task completion
        if result:
            size_saved = result.original_size - result.converted_size
            size_saved_mb = size_saved / (1024 * 1024)
            self.show_notification(
                "Conversion Complete",
                f"Saved {size_saved_mb:.1f} MB",
                QSystemTrayIcon.MessageIcon.Information,
            )

    @Slot(str, str)
    def _on_task_failed(self, task_id: str, error: str) -> None:
        """Handle task failure.

        Args:
            task_id: Task ID.
            error: Error message.
        """
        self._current_progress = 0.0
        self._current_task_action.setVisible(False)
        self._update_status_display()

        # Show error notification
        task = self._conversion_service.get_task(task_id)
        file_name = task.file_name if task else "Unknown"
        self.show_notification(
            "Conversion Failed",
            f"{file_name}: {error}",
            QSystemTrayIcon.MessageIcon.Critical,
        )

    @Slot(int, int)
    def _on_all_completed(self, successful: int, failed: int) -> None:
        """Handle all tasks completed.

        Args:
            successful: Number of successful conversions.
            failed: Number of failed conversions.
        """
        self._current_progress = 0.0
        self._update_status_display()

        # Show summary notification
        total = successful + failed
        if total > 1:
            message = f"{successful} succeeded"
            if failed > 0:
                message += f", {failed} failed"

            icon = (
                QSystemTrayIcon.MessageIcon.Information
                if failed == 0
                else QSystemTrayIcon.MessageIcon.Warning
            )

            self.show_notification("All Conversions Complete", message, icon)

    @Slot()
    def _on_queue_updated(self) -> None:
        """Handle queue state change."""
        status = self._conversion_service.get_queue_status()
        self._is_paused = status["is_paused"]
        self._update_status_display()
