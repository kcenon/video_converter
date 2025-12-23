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

        self._setup_window()
        self._setup_views()
        self._setup_navigation()
        self._setup_menu_bar()
        self._setup_status_bar()

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
