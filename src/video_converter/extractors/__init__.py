"""Video extractors package.

This package provides modules for extracting videos from various sources,
primarily the macOS Photos library.
"""

from video_converter.extractors.photos_extractor import (
    LibraryStats,
    MediaType,
    PhotosAccessDeniedError,
    PhotosLibrary,
    PhotosLibraryError,
    PhotosLibraryNotFoundError,
    PhotosVideoFilter,
    PhotosVideoInfo,
    get_permission_instructions,
)

__all__ = [
    "LibraryStats",
    "MediaType",
    "PhotosAccessDeniedError",
    "PhotosLibrary",
    "PhotosLibraryError",
    "PhotosLibraryNotFoundError",
    "PhotosVideoFilter",
    "PhotosVideoInfo",
    "get_permission_instructions",
]
