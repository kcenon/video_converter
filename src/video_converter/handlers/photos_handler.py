"""Photos library source handler for CLI integration.

This module provides the PhotosSourceHandler class that bridges
the PhotosLibrary/PhotosVideoFilter implementations with the CLI
interface for batch video conversion.

SDS Reference: SDS-P01-007
SRS Reference: SRS-301 (Photos Library Integration)

Example:
    >>> handler = PhotosSourceHandler()
    >>> if handler.check_permissions():
    ...     options = PhotosConversionOptions(limit=10)
    ...     candidates = handler.get_candidates(options)
    ...     for video in candidates:
    ...         exported = handler.export_video(video)
    ...         # ... convert video ...
    ...         handler.cleanup_exported(exported)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

from video_converter.extractors.photos_extractor import (
    LibraryStats,
    PhotosAccessDeniedError,
    PhotosLibrary,
    PhotosLibraryError,
    PhotosLibraryNotFoundError,
    PhotosVideoFilter,
    PhotosVideoInfo,
    VideoExporter,
    get_permission_instructions,
)

logger = logging.getLogger(__name__)


@dataclass
class PhotosConversionOptions:
    """Options for Photos library conversion.

    Attributes:
        albums: Only include videos from these albums.
            If None, includes all albums.
        exclude_albums: Exclude videos from these albums.
            If None, uses PhotosVideoFilter defaults.
        from_date: Only include videos created on or after this date.
        to_date: Only include videos created on or before this date.
        favorites_only: Only include favorite videos.
        include_hidden: Include hidden videos.
        limit: Maximum number of videos to process.
        dry_run: If True, only preview without converting.
    """

    albums: list[str] | None = None
    exclude_albums: list[str] | None = None
    from_date: datetime | None = None
    to_date: datetime | None = None
    favorites_only: bool = False
    include_hidden: bool = False
    limit: int | None = None
    dry_run: bool = False


@dataclass
class PhotosConversionResult:
    """Result of a Photos conversion operation.

    Attributes:
        total_candidates: Total number of conversion candidates found.
        processed: Number of videos processed.
        successful: Number of successful conversions.
        failed: Number of failed conversions.
        skipped: Number of skipped videos.
        total_size_before: Total size before conversion in bytes.
        total_size_after: Total size after conversion in bytes.
        errors: List of error messages from failed conversions.
    """

    total_candidates: int = 0
    processed: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    total_size_before: int = 0
    total_size_after: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def size_saved(self) -> int:
        """Calculate total size saved.

        Returns:
            Size saved in bytes.
        """
        return max(0, self.total_size_before - self.total_size_after)

    @property
    def savings_percentage(self) -> float:
        """Calculate savings percentage.

        Returns:
            Percentage of size reduction.
        """
        if self.total_size_before == 0:
            return 0.0
        return (self.size_saved / self.total_size_before) * 100


class PhotosSourceHandler:
    """Handler for Photos library source in CLI.

    This class bridges the gap between the PhotosLibrary/PhotosVideoFilter
    implementations and the CLI interface, providing a unified API for
    Photos-based video conversion.

    SDS Reference: SDS-P01-007

    Example:
        >>> handler = PhotosSourceHandler()
        >>> if handler.check_permissions():
        ...     options = PhotosConversionOptions(albums=["Vacation"])
        ...     candidates = handler.get_candidates(options)
        ...     print(f"Found {len(candidates)} videos to convert")

    Attributes:
        library: PhotosLibrary instance.
        exporter: VideoExporter instance for file export.
    """

    def __init__(
        self,
        library_path: Path | None = None,
        temp_dir: Path | None = None,
    ) -> None:
        """Initialize PhotosSourceHandler.

        Args:
            library_path: Custom Photos library path.
                If None, uses the default system library.
            temp_dir: Custom temporary directory for exports.
                If None, creates a system temporary directory.
        """
        self._library_path = library_path
        self._temp_dir = temp_dir
        self._library: PhotosLibrary | None = None
        self._exporter: VideoExporter | None = None
        self._filter: PhotosVideoFilter | None = None
        self._permission_error: str | None = None

        logger.debug(
            f"PhotosSourceHandler initialized: "
            f"library_path={library_path}, temp_dir={temp_dir}"
        )

    @property
    def library(self) -> PhotosLibrary:
        """Get or create PhotosLibrary instance.

        Returns:
            PhotosLibrary instance.

        Raises:
            PhotosLibraryError: If library cannot be accessed.
        """
        if self._library is None:
            self._library = PhotosLibrary(self._library_path)
        return self._library

    @property
    def exporter(self) -> VideoExporter:
        """Get or create VideoExporter instance.

        Returns:
            VideoExporter instance for file export.
        """
        if self._exporter is None:
            self._exporter = VideoExporter(self._temp_dir)
        return self._exporter

    def _get_filter(
        self,
        include_albums: list[str] | None = None,
        exclude_albums: list[str] | None = None,
    ) -> PhotosVideoFilter:
        """Get or create PhotosVideoFilter instance.

        Args:
            include_albums: Albums to include.
            exclude_albums: Albums to exclude.

        Returns:
            PhotosVideoFilter instance.
        """
        return PhotosVideoFilter(
            library=self.library,
            include_albums=include_albums,
            exclude_albums=exclude_albums,
        )

    def check_permissions(self) -> bool:
        """Check if we have access to the Photos library.

        This method attempts to access the Photos library to verify
        permissions. If access is denied, the error is stored for
        later retrieval via get_permission_error().

        Returns:
            True if access is granted, False otherwise.
        """
        try:
            result = self.library.check_permissions()
            if not result:
                self._permission_error = "Photos library access denied"
            return result
        except PhotosLibraryNotFoundError as e:
            self._permission_error = str(e)
            logger.warning(f"Photos library not found: {e}")
            return False
        except PhotosAccessDeniedError as e:
            self._permission_error = str(e)
            logger.warning(f"Photos library access denied: {e}")
            return False
        except PhotosLibraryError as e:
            self._permission_error = str(e)
            logger.warning(f"Photos library error: {e}")
            return False

    def get_permission_error(self) -> str | None:
        """Get the last permission error message.

        Returns:
            Error message if permission check failed, None otherwise.
        """
        return self._permission_error

    def get_permission_instructions(self) -> str:
        """Get instructions for granting Photos library access.

        Returns:
            Multi-line string with detailed instructions.
        """
        return get_permission_instructions()

    def get_candidates(
        self,
        options: PhotosConversionOptions,
    ) -> list[PhotosVideoInfo]:
        """Get videos that need conversion from H.264 to H.265.

        This method filters Photos library videos to find candidates
        for conversion, applying the specified options.

        Args:
            options: Conversion options including filters.

        Returns:
            List of PhotosVideoInfo for videos that need conversion.

        Raises:
            PhotosAccessDeniedError: If access is denied.
        """
        logger.info("Searching for conversion candidates in Photos library...")

        # Create filter with album options
        video_filter = self._get_filter(
            include_albums=options.albums,
            exclude_albums=options.exclude_albums,
        )

        # Get candidates with date filtering
        candidates = video_filter.get_conversion_candidates(
            from_date=options.from_date,
            to_date=options.to_date,
            limit=options.limit,
        )

        # Apply additional filters
        filtered_candidates: list[PhotosVideoInfo] = []
        for video in candidates:
            # Filter by favorites
            if options.favorites_only and not video.favorite:
                continue

            # Filter by hidden status
            if not options.include_hidden and video.hidden:
                continue

            filtered_candidates.append(video)

            # Check limit
            if options.limit and len(filtered_candidates) >= options.limit:
                break

        logger.info(
            f"Found {len(filtered_candidates)} conversion candidates "
            f"(from {len(candidates)} total H.264 videos)"
        )
        return filtered_candidates

    def export_video(
        self,
        video: PhotosVideoInfo,
        on_progress: Callable[[float], None] | None = None,
    ) -> Path:
        """Export a video from Photos library to temporary directory.

        Args:
            video: Video information from Photos library.
            on_progress: Optional callback for progress updates.
                Called with progress value from 0.0 to 1.0.

        Returns:
            Path to the exported video file.

        Raises:
            VideoNotAvailableError: Video is in iCloud only.
            ExportError: Export failed.
        """
        logger.info(f"Exporting video: {video.filename}")
        return self.exporter.export(video, on_progress)

    def cleanup_exported(self, path: Path) -> bool:
        """Remove an exported video file.

        Args:
            path: Path to the exported file to remove.

        Returns:
            True if file was removed, False otherwise.
        """
        return self.exporter.cleanup(path)

    def cleanup_all(self) -> int:
        """Remove all exported files and cleanup resources.

        Returns:
            Number of files removed.
        """
        if self._exporter is not None:
            return self._exporter.cleanup_all()
        return 0

    def get_stats(self) -> LibraryStats:
        """Get statistics about videos in the library.

        Returns:
            LibraryStats with codec distribution and size information.

        Raises:
            PhotosAccessDeniedError: If access is denied.
        """
        video_filter = self._get_filter()
        return video_filter.get_stats()

    def get_library_info(self) -> dict[str, str | int]:
        """Get information about the Photos library.

        Returns:
            Dictionary with library path, photo count, and video count.

        Raises:
            PhotosAccessDeniedError: If access is denied.
        """
        return self.library.get_library_info()

    def close(self) -> None:
        """Close handler and cleanup resources.

        This releases any resources held by the library connection
        and cleans up temporary files.
        """
        if self._exporter is not None:
            self._exporter.cleanup_all()
            self._exporter = None

        if self._library is not None:
            self._library.close()
            self._library = None

        logger.debug("PhotosSourceHandler closed")

    def __enter__(self) -> PhotosSourceHandler:
        """Context manager entry.

        Returns:
            Self for context manager usage.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Context manager exit - cleanup resources.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        self.close()
