"""Importers for re-importing converted videos.

This module provides importer classes for bringing converted videos
back into their source libraries with metadata preservation.

SRS Reference: SRS-305 (Photos Re-Import)
SRS Reference: SRS-306 (Metadata Preservation)
"""

from __future__ import annotations

from video_converter.importers.metadata_preservation import (
    MetadataApplicationError,
    MetadataEmbedError,
    MetadataPreservationError,
    MetadataPreserver,
    MetadataTolerance,
    VerificationResult,
    VideoMetadataSnapshot,
)
from video_converter.importers.photos_importer import (
    DuplicateVideoError,
    ImportFailedError,
    ImportTimeoutError,
    PhotosImporter,
    PhotosImportError,
    PhotosNotRunningError,
)

__all__ = [
    # Main classes
    "PhotosImporter",
    "MetadataPreserver",
    # Data classes
    "VideoMetadataSnapshot",
    "MetadataTolerance",
    "VerificationResult",
    # Photos Importer Exceptions
    "PhotosImportError",
    "PhotosNotRunningError",
    "ImportTimeoutError",
    "DuplicateVideoError",
    "ImportFailedError",
    # Metadata Preservation Exceptions
    "MetadataPreservationError",
    "MetadataEmbedError",
    "MetadataApplicationError",
]
