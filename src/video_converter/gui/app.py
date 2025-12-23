"""Main application entry point for the Video Converter GUI.

This module provides the QApplication setup and main entry point for
the graphical user interface.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from video_converter.gui.main_window import MainWindow
from video_converter.gui.styles.theme import apply_macos_theme

if TYPE_CHECKING:
    from collections.abc import Sequence


class VideoConverterApp(QApplication):
    """Main application class for Video Converter GUI.

    This class extends QApplication to provide application-wide settings
    and initialization for the Video Converter GUI.

    Attributes:
        main_window: The main application window.
    """

    def __init__(self, argv: Sequence[str] | None = None) -> None:
        """Initialize the application.

        Args:
            argv: Command line arguments. Defaults to sys.argv if None.
        """
        if argv is None:
            argv = sys.argv
        super().__init__(list(argv))

        # Set application metadata
        self.setApplicationName("Video Converter")
        self.setApplicationDisplayName("Video Converter")
        self.setOrganizationName("VideoConverter")
        self.setOrganizationDomain("github.com/kcenon/video_converter")

        # Enable high DPI scaling
        self.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

        # Apply macOS theme
        apply_macos_theme(self)

        # Create main window
        self.main_window = MainWindow()

    def run(self) -> int:
        """Run the application event loop.

        Returns:
            Exit code from the application.
        """
        self.main_window.show()
        return int(self.exec())


def main() -> int:
    """Main entry point for the GUI application.

    Returns:
        Exit code from the application.
    """
    app = VideoConverterApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
