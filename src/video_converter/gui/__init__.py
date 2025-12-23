"""GUI module for Video Converter.

This module provides a PySide6-based graphical user interface for the video
converter application. It offers an intuitive interface for video conversion,
Photos library integration, and real-time progress monitoring.

Features:
    - Drag & drop video file support
    - Photos library browser
    - Real-time conversion progress display
    - Menubar app for background monitoring
    - Dark mode support
    - macOS native look and feel

Example:
    Run the GUI application::

        $ video-converter-gui

    Or programmatically::

        from video_converter.gui.app import main
        main()

Note:
    This module requires the 'gui' optional dependencies::

        pip install video-converter[gui]
"""

from __future__ import annotations

__all__: list[str] = []
