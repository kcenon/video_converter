"""View components for the Video Converter GUI.

This module provides the main view components for the application,
including home, convert, photos, queue, and settings views.
"""

from __future__ import annotations

from video_converter.gui.views.convert_view import ConvertView
from video_converter.gui.views.home_view import HomeView
from video_converter.gui.views.photos_view import PhotosView
from video_converter.gui.views.queue_view import QueueView
from video_converter.gui.views.settings_view import SettingsView

__all__ = [
    "ConvertView",
    "HomeView",
    "PhotosView",
    "QueueView",
    "SettingsView",
]
