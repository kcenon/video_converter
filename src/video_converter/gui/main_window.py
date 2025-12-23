"""Main window for the Video Converter GUI.

This module provides the main application window with tab navigation
and central widget management.
"""

from __future__ import annotations

from PySide6.QtCore import Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QStackedWidget,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from video_converter.gui.dialogs.result_dialog import ConversionResultDialog
from video_converter.gui.services.conversion_service import ConversionService
from video_converter.gui.services.settings_manager import SettingsManager
from video_converter.gui.views.convert_view import ConvertView
from video_converter.gui.views.home_view import HomeView
from video_converter.gui.views.photos_view import PhotosView
from video_converter.gui.views.queue_view import QueueView
from video_converter.gui.views.settings_view import SettingsView


class MainWindow(QMainWindow):
    """Main application window.

    Provides the main window with tab-based navigation between different
    views: Home, Convert, Photos, Queue, and Settings.

    Attributes:
        tab_bar: Navigation tab bar.
        stacked_widget: Widget stack for view switching.
        home_view: Home/Dashboard view.
        convert_view: Conversion view.
        photos_view: Photos library browser view.
        queue_view: Conversion queue view.
        settings_view: Settings/Preferences view.
    """

    # Minimum window dimensions
    MIN_WIDTH = 900
    MIN_HEIGHT = 600

    # Tab indices
    TAB_HOME = 0
    TAB_CONVERT = 1
    TAB_PHOTOS = 2
    TAB_QUEUE = 3
    TAB_SETTINGS = 4

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()

        # Create settings manager and load settings
        self._settings_manager = SettingsManager(self)
        self._settings_manager.load()

        # Create conversion service
        self._conversion_service = ConversionService(self)

        self._setup_window()
        self._setup_views()
        self._setup_navigation()
        self._setup_menu_bar()
        self._setup_status_bar()
        self._connect_conversion_service()
        self._connect_settings_manager()

    def _setup_window(self) -> None:
        """Configure window properties."""
        self.setWindowTitle("Video Converter")
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.resize(1024, 720)

        # Center on screen
        screen = self.screen()
        if screen:
            screen_geometry = screen.availableGeometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

    def _setup_views(self) -> None:
        """Create and configure all views."""
        # Create stacked widget for views
        self.stacked_widget = QStackedWidget()

        # Create views
        self.home_view = HomeView()
        self.convert_view = ConvertView()
        self.photos_view = PhotosView()
        self.queue_view = QueueView()
        self.settings_view = SettingsView()

        # Add views to stack
        self.stacked_widget.addWidget(self.home_view)
        self.stacked_widget.addWidget(self.convert_view)
        self.stacked_widget.addWidget(self.photos_view)
        self.stacked_widget.addWidget(self.queue_view)
        self.stacked_widget.addWidget(self.settings_view)

        # Connect view signals
        self.home_view.file_dropped.connect(self._on_file_dropped)
        self.home_view.browse_photos_requested.connect(self._show_photos_view)

    def _setup_navigation(self) -> None:
        """Set up tab-based navigation."""
        # Create tab bar
        self.tab_bar = QTabBar()
        self.tab_bar.setDocumentMode(True)
        self.tab_bar.setExpanding(False)

        # Add tabs
        self.tab_bar.addTab("Home")
        self.tab_bar.addTab("Convert")
        self.tab_bar.addTab("Photos")
        self.tab_bar.addTab("Queue")
        self.tab_bar.addTab("Settings")

        # Connect tab change
        self.tab_bar.currentChanged.connect(self._on_tab_changed)

        # Create central widget with layout
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.tab_bar)
        layout.addWidget(self.stacked_widget)

        self.setCentralWidget(central_widget)

    def _setup_menu_bar(self) -> None:
        """Set up the menu bar."""
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")

        open_action = QAction("Open Video...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        close_action = QAction("Close Window", self)
        close_action.setShortcut(QKeySequence.StandardKey.Close)
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)

        # Edit menu
        edit_menu = menu_bar.addMenu("Edit")

        preferences_action = QAction("Preferences...", self)
        preferences_action.setShortcut(QKeySequence("Ctrl+,"))
        preferences_action.triggered.connect(self._show_settings)
        edit_menu.addAction(preferences_action)

        # View menu
        view_menu = menu_bar.addMenu("View")

        home_action = QAction("Home", self)
        home_action.setShortcut(QKeySequence("Ctrl+1"))
        home_action.triggered.connect(lambda: self._set_current_tab(self.TAB_HOME))
        view_menu.addAction(home_action)

        convert_action = QAction("Convert", self)
        convert_action.setShortcut(QKeySequence("Ctrl+2"))
        convert_action.triggered.connect(lambda: self._set_current_tab(self.TAB_CONVERT))
        view_menu.addAction(convert_action)

        photos_action = QAction("Photos", self)
        photos_action.setShortcut(QKeySequence("Ctrl+3"))
        photos_action.triggered.connect(lambda: self._set_current_tab(self.TAB_PHOTOS))
        view_menu.addAction(photos_action)

        queue_action = QAction("Queue", self)
        queue_action.setShortcut(QKeySequence("Ctrl+4"))
        queue_action.triggered.connect(lambda: self._set_current_tab(self.TAB_QUEUE))
        view_menu.addAction(queue_action)

        settings_action = QAction("Settings", self)
        settings_action.setShortcut(QKeySequence("Ctrl+5"))
        settings_action.triggered.connect(lambda: self._set_current_tab(self.TAB_SETTINGS))
        view_menu.addAction(settings_action)

        # Help menu
        help_menu = menu_bar.addMenu("Help")

        about_action = QAction("About Video Converter", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_status_bar(self) -> None:
        """Set up the status bar."""
        self.statusBar().showMessage("Ready")

    @Slot(int)
    def _on_tab_changed(self, index: int) -> None:
        """Handle tab change.

        Args:
            index: The new tab index.
        """
        self.stacked_widget.setCurrentIndex(index)

    def _set_current_tab(self, index: int) -> None:
        """Set the current tab.

        Args:
            index: The tab index to switch to.
        """
        self.tab_bar.setCurrentIndex(index)

    @Slot(str)
    def _on_file_dropped(self, file_path: str) -> None:
        """Handle file drop on home view.

        Args:
            file_path: Path to the dropped file.
        """
        self.convert_view.set_input_file(file_path)
        self._set_current_tab(self.TAB_CONVERT)

    @Slot()
    def _show_photos_view(self) -> None:
        """Switch to Photos view."""
        self._set_current_tab(self.TAB_PHOTOS)

    @Slot()
    def _on_open_file(self) -> None:
        """Handle open file action."""
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video File",
            "",
            "Video Files (*.mp4 *.mov *.avi *.mkv *.m4v);;All Files (*)",
        )
        if file_path:
            self._on_file_dropped(file_path)

    @Slot()
    def _show_settings(self) -> None:
        """Switch to Settings view."""
        self._set_current_tab(self.TAB_SETTINGS)

    @Slot()
    def _show_about(self) -> None:
        """Show about dialog."""
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.about(
            self,
            "About Video Converter",
            "<h3>Video Converter</h3>"
            "<p>Version 0.3.0.0</p>"
            "<p>Automated H.264 to H.265 video conversion for macOS "
            "with Photos library integration.</p>"
            "<p>Copyright 2024 Video Converter Team</p>",
        )

    def _connect_settings_manager(self) -> None:
        """Connect settings manager with views."""
        # Load saved settings into settings view
        self.settings_view.load_settings(self._settings_manager.get())

        # Connect settings view signals to manager
        self.settings_view.settings_changed.connect(self._on_settings_changed)
        self.settings_view.settings_saved.connect(self._on_settings_saved)

    @Slot(dict)
    def _on_settings_changed(self, settings: dict) -> None:
        """Handle settings change from settings view.

        Args:
            settings: New settings dictionary.
        """
        self._settings_manager.set(settings)

    @Slot()
    def _on_settings_saved(self) -> None:
        """Handle settings save request."""
        if self._settings_manager.save():
            self.statusBar().showMessage("Settings saved", 3000)
        else:
            self.statusBar().showMessage("Failed to save settings", 3000)

    def _connect_conversion_service(self) -> None:
        """Connect conversion service signals to views."""
        # Connect ConvertView signals
        self.convert_view.conversion_started.connect(self._on_conversion_started)
        self.convert_view.conversion_cancelled.connect(
            self._conversion_service.cancel_all
        )

        # Connect QueueView signals
        self.queue_view.pause_all_requested.connect(self._conversion_service.pause_all)
        self.queue_view.resume_all_requested.connect(
            self._conversion_service.resume_all
        )
        self.queue_view.cancel_all_requested.connect(
            self._conversion_service.cancel_all
        )

        # Connect service signals to QueueView
        self._conversion_service.task_added.connect(self._on_task_added)
        self._conversion_service.progress_updated.connect(self._on_progress_updated)
        self._conversion_service.task_completed.connect(self._on_task_completed)
        self._conversion_service.task_failed.connect(self._on_task_failed)
        self._conversion_service.all_completed.connect(self._on_all_completed)

    @Slot(str, dict)
    def _on_conversion_started(self, file_path: str, settings: dict) -> None:
        """Handle conversion start from ConvertView.

        Args:
            file_path: Path to the input file.
            settings: Conversion settings dictionary.
        """
        # Apply saved settings to conversion settings
        enhanced_settings = self._settings_manager.apply_to_conversion_settings(
            settings.copy()
        )

        # Add task to queue
        self._conversion_service.add_task(file_path, settings=enhanced_settings)

        # Switch to Queue view to show progress
        self._set_current_tab(self.TAB_QUEUE)

        # Update status bar
        self.statusBar().showMessage(f"Converting: {file_path}")

    @Slot(str, str, str)
    def _on_task_added(self, task_id: str, file_name: str, file_size: str) -> None:
        """Handle task added to queue.

        Args:
            task_id: Task ID.
            file_name: Name of the video file.
            file_size: File size string.
        """
        self.queue_view.add_conversion(task_id, file_name, file_size)

    @Slot(str, float, object, object)
    def _on_progress_updated(
        self,
        task_id: str,
        progress: float,
        eta_seconds: int | None,
        speed: str | None,
    ) -> None:
        """Handle progress update from conversion service.

        Args:
            task_id: Task ID.
            progress: Progress percentage.
            eta_seconds: Estimated time remaining.
            speed: Encoding speed string.
        """
        # Update queue view
        eta_str = None
        if eta_seconds is not None:
            minutes = eta_seconds // 60
            seconds = eta_seconds % 60
            eta_str = f"{minutes}:{seconds:02d}"

        self.queue_view.update_progress(task_id, progress, eta_str, speed)

        # Update convert view if it's the current task
        self.convert_view.update_progress(progress, eta_seconds, speed)

        # Update status bar
        self.statusBar().showMessage(f"Converting: {progress:.1f}%")

    @Slot(str, object)
    def _on_task_completed(self, task_id: str, result) -> None:
        """Handle task completion.

        Args:
            task_id: Task ID.
            result: ConversionResult object.
        """
        self.queue_view.mark_completed(task_id, success=True)
        self.convert_view.conversion_complete(success=True)

        # Show result dialog
        if result:
            dialog = ConversionResultDialog(result, self)
            dialog.exec()

        # Update status bar
        self.statusBar().showMessage("Conversion complete")

    @Slot(str, str)
    def _on_task_failed(self, task_id: str, error: str) -> None:
        """Handle task failure.

        Args:
            task_id: Task ID.
            error: Error message.
        """
        self.queue_view.mark_completed(task_id, success=False)
        self.convert_view.conversion_complete(success=False, message=error)

        # Update status bar
        self.statusBar().showMessage(f"Conversion failed: {error}")

    @Slot(int, int)
    def _on_all_completed(self, successful: int, failed: int) -> None:
        """Handle all tasks completed.

        Args:
            successful: Number of successful conversions.
            failed: Number of failed conversions.
        """
        total = successful + failed
        self.statusBar().showMessage(
            f"Completed: {successful}/{total} succeeded, {failed} failed"
        )

    def closeEvent(self, event) -> None:
        """Handle window close event.

        Args:
            event: Close event.
        """
        # Save settings if there are unsaved changes
        if self._settings_manager.is_dirty():
            self._settings_manager.save()

        # Shutdown conversion service
        self._conversion_service.shutdown()
        super().closeEvent(event)
