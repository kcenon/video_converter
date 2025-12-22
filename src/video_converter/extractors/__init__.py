"""Video extractors package.

This package provides modules for extracting videos from various sources,
including the macOS Photos library and filesystem folders.

SDS Reference: SDS-E01 (Extractors Module)
"""

from video_converter.extractors.folder_extractor import (
    FolderAccessDeniedError,
    FolderExtractor,
    FolderExtractorError,
    FolderNotFoundError,
    FolderStats,
    FolderVideoInfo,
    InvalidVideoFileError,
)
from video_converter.extractors.icloud_handler import (
    CloudStatus,
    DownloadProgress,
    iCloudDownloadError,
    iCloudError,
    iCloudHandler,
    iCloudTimeoutError,
)
from video_converter.extractors.photos_extractor import (
    ExportError,
    LibraryStats,
    MediaType,
    PhotosAccessDeniedError,
    PhotosLibrary,
    PhotosLibraryError,
    PhotosLibraryNotFoundError,
    PhotosVideoFilter,
    PhotosVideoInfo,
    VideoExporter,
    VideoNotAvailableError,
    get_permission_instructions,
)

__all__ = [
    # Folder extractor
    "FolderAccessDeniedError",
    "FolderExtractor",
    "FolderExtractorError",
    "FolderNotFoundError",
    "FolderStats",
    "FolderVideoInfo",
    "InvalidVideoFileError",
    # iCloud handler
    "CloudStatus",
    "DownloadProgress",
    "iCloudDownloadError",
    "iCloudError",
    "iCloudHandler",
    "iCloudTimeoutError",
    # Photos extractor
    "ExportError",
    "LibraryStats",
    "MediaType",
    "PhotosAccessDeniedError",
    "PhotosLibrary",
    "PhotosLibraryError",
    "PhotosLibraryNotFoundError",
    "PhotosVideoFilter",
    "PhotosVideoInfo",
    "VideoExporter",
    "VideoNotAvailableError",
    "get_permission_instructions",
]
