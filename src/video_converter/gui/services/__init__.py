"""Service components for the Video Converter GUI.

This module provides services that bridge the GUI with the backend.
"""

from __future__ import annotations

from video_converter.gui.services.conversion_service import (
    ConversionService,
    ConversionTask,
    ConversionWorker,
)
from video_converter.gui.services.settings_manager import (
    SettingsManager,
    get_default_settings,
)

__all__: list[str] = [
    "ConversionService",
    "ConversionTask",
    "ConversionWorker",
    "SettingsManager",
    "get_default_settings",
]
