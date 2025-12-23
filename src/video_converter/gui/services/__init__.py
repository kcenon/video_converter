"""Service components for the Video Converter GUI.

This module provides services that bridge the GUI with the backend.
"""

from __future__ import annotations

from video_converter.gui.services.conversion_service import (
    ConversionService,
    ConversionTask,
    ConversionWorker,
)
from video_converter.gui.services.photos_service import (
    AlbumInfo,
    PhotosService,
    PhotosWorker,
    VideoDisplayInfo,
)
from video_converter.gui.services.settings_manager import (
    SettingsManager,
    get_default_settings,
)
from video_converter.gui.services.update_service import (
    CURRENT_VERSION,
    ReleaseInfo,
    UpdateService,
    check_for_updates_sync,
)

__all__: list[str] = [
    "AlbumInfo",
    "CURRENT_VERSION",
    "ConversionService",
    "ConversionTask",
    "ConversionWorker",
    "PhotosService",
    "PhotosWorker",
    "ReleaseInfo",
    "SettingsManager",
    "UpdateService",
    "VideoDisplayInfo",
    "check_for_updates_sync",
    "get_default_settings",
]
