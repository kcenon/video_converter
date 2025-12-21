"""Video extractors package.

This package provides modules for extracting videos from various sources,
primarily the macOS Photos library.
"""

from video_converter.extractors.photos_extractor import (
    MediaType,
    PhotosAccessDeniedError,
    PhotosLibrary,
    PhotosLibraryError,
    PhotosLibraryNotFoundError,
    PhotosVideoInfo,
    get_permission_instructions,
)

__all__ = [
    "MediaType",
    "PhotosAccessDeniedError",
    "PhotosLibrary",
    "PhotosLibraryError",
    "PhotosLibraryNotFoundError",
    "PhotosVideoInfo",
    "get_permission_instructions",
]
