"""Handlers for different video sources.

This module provides handler classes for various video sources
used in CLI commands.
"""

from __future__ import annotations

from video_converter.handlers.photos_handler import (
    PhotosConversionOptions,
    PhotosSourceHandler,
)

__all__ = [
    "PhotosConversionOptions",
    "PhotosSourceHandler",
]
