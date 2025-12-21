"""Photos library integration module.

This module provides read-only access to the macOS Photos library
for querying video assets using the osxphotos library.

SDS Reference: SDS-P01-004
SRS Reference: SRS-301 (Photos Library Integration)

Example:
    >>> library = PhotosLibrary()
    >>> if library.check_permissions():
    ...     print(f"Found {library.get_video_count()} videos")
    ... else:
    ...     print("Access denied")
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    import osxphotos

    from video_converter.processors.codec_detector import CodecDetector

logger = logging.getLogger(__name__)


class PhotosLibraryError(Exception):
    """Base exception for Photos library operations."""


class PhotosAccessDeniedError(PhotosLibraryError):
    """Raised when access to Photos library is denied.

    This typically occurs when the application doesn't have
    Full Disk Access permission in System Settings.
    """

    def __init__(self, message: str | None = None) -> None:
        """Initialize with optional custom message.

        Args:
            message: Custom error message. If None, uses default.
        """
        if message is None:
            message = (
                "Photos library access denied. "
                "Grant Full Disk Access permission in System Settings."
            )
        super().__init__(message)


class PhotosLibraryNotFoundError(PhotosLibraryError):
    """Raised when Photos library cannot be found."""

    def __init__(self, path: Path | None = None) -> None:
        """Initialize with optional library path.

        Args:
            path: Path that was attempted if custom path was specified.
        """
        if path:
            message = f"Photos library not found at: {path}"
        else:
            message = "Default Photos library not found"
        super().__init__(message)


class VideoNotAvailableError(PhotosLibraryError):
    """Raised when video is not available locally (iCloud only).

    This exception indicates that the video file exists only in iCloud
    and must be downloaded first using the Photos app.
    """

    def __init__(self, filename: str) -> None:
        """Initialize with video filename.

        Args:
            filename: Name of the unavailable video file.
        """
        message = (
            f"'{filename}' is stored in iCloud only. "
            "Download it first in Photos app before exporting."
        )
        super().__init__(message)


class ExportError(PhotosLibraryError):
    """Raised when video export fails.

    This exception covers various export failures including file copy
    errors, permission issues, and insufficient disk space.
    """

    def __init__(self, message: str, filename: str | None = None) -> None:
        """Initialize with error message and optional filename.

        Args:
            message: Description of what failed.
            filename: Name of the video file if applicable.
        """
        if filename:
            full_message = f"Failed to export '{filename}': {message}"
        else:
            full_message = f"Export failed: {message}"
        super().__init__(full_message)


class MediaType(Enum):
    """Media types available in Photos library.

    Attributes:
        VIDEO: Video files (mov, mp4, etc.).
        PHOTO: Photo files (jpg, heic, etc.).
        ALL: All media types.
    """

    VIDEO = "video"
    PHOTO = "photo"
    ALL = "all"


@dataclass
class PhotosVideoInfo:
    """Information about a video in the Photos library.

    Attributes:
        uuid: Unique identifier for the asset in Photos.
        filename: Original filename of the video.
        path: Path to the video file (may be None if in iCloud).
        date: Creation date of the video.
        date_modified: Last modification date.
        duration: Video duration in seconds.
        favorite: Whether the video is marked as favorite.
        hidden: Whether the video is hidden.
        in_cloud: Whether the video is stored in iCloud.
        location: GPS coordinates (latitude, longitude) if available.
        albums: List of album names containing this video.
        codec: Video codec name (e.g., "h264", "hevc").
        size: File size in bytes.
    """

    uuid: str
    filename: str
    path: Path | None
    date: datetime | None
    date_modified: datetime | None
    duration: float
    favorite: bool = False
    hidden: bool = False
    in_cloud: bool = False
    location: tuple[float, float] | None = None
    albums: list[str] = field(default_factory=list)
    codec: str | None = None
    size: int = 0

    # Codec name variations for identification
    H264_CODECS = frozenset({"h264", "avc", "avc1", "x264"})
    HEVC_CODECS = frozenset({"hevc", "h265", "hvc1", "hev1", "x265"})

    @property
    def is_available_locally(self) -> bool:
        """Check if the video file is available locally.

        Returns:
            True if the file exists locally, False if in iCloud only.
        """
        if self.path is None:
            return False
        return self.path.exists()

    @property
    def is_h264(self) -> bool:
        """Check if video codec is H.264/AVC.

        Returns:
            True if the codec is any variant of H.264.
        """
        if self.codec is None:
            return False
        return self.codec.lower() in self.H264_CODECS

    @property
    def is_hevc(self) -> bool:
        """Check if video codec is H.265/HEVC.

        Returns:
            True if the codec is any variant of H.265/HEVC.
        """
        if self.codec is None:
            return False
        return self.codec.lower() in self.HEVC_CODECS

    @property
    def needs_conversion(self) -> bool:
        """Check if video needs H.265 conversion.

        A video needs conversion if:
        - It is locally available (not iCloud-only)
        - Its codec is H.264

        Returns:
            True if the video should be converted to H.265.
        """
        return self.is_available_locally and self.is_h264


class PhotosLibrary:
    """Interface to macOS Photos library via osxphotos.

    This class provides a high-level interface for querying videos
    from the macOS Photos library. It handles library initialization,
    permission checking, and provides caching for performance.

    SDS Reference: SDS-P01-004

    Example:
        >>> library = PhotosLibrary()
        >>> if library.check_permissions():
        ...     videos = library.get_videos()
        ...     for video in videos:
        ...         print(f"{video.filename}: {video.duration}s")

    Attributes:
        library_path: Path to the Photos library (None for default).
    """

    # Default Photos library location
    DEFAULT_LIBRARY_PATH = Path.home() / "Pictures" / "Photos Library.photoslibrary"

    def __init__(self, library_path: Path | None = None) -> None:
        """Initialize Photos library connection.

        Args:
            library_path: Custom library path. None uses the default
                system Photos library.

        Raises:
            PhotosLibraryNotFoundError: If specified library path doesn't exist.
        """
        self._library_path = library_path
        self._db: osxphotos.PhotosDB | None = None
        self._initialized: bool = False
        self._permission_checked: bool = False
        self._has_permission: bool = False

        # Validate custom path if provided
        if library_path is not None and not library_path.exists():
            raise PhotosLibraryNotFoundError(library_path)

    @property
    def library_path(self) -> Path:
        """Get the Photos library path.

        Returns:
            Path to the Photos library (default or custom).
        """
        if self._library_path is not None:
            return self._library_path
        return self.DEFAULT_LIBRARY_PATH

    @property
    def db(self) -> osxphotos.PhotosDB:
        """Get the PhotosDB instance (lazy-loaded).

        Returns:
            osxphotos.PhotosDB instance.

        Raises:
            PhotosAccessDeniedError: If access is denied.
            PhotosLibraryNotFoundError: If library cannot be found.
        """
        if self._db is None:
            self._db = self._initialize_db()
        return self._db

    def _initialize_db(self) -> osxphotos.PhotosDB:
        """Initialize the PhotosDB connection.

        Returns:
            Initialized PhotosDB instance.

        Raises:
            PhotosAccessDeniedError: If access is denied.
            PhotosLibraryNotFoundError: If library cannot be found.
        """
        import osxphotos

        logger.info("Initializing Photos library connection")

        try:
            if self._library_path is not None:
                db = osxphotos.PhotosDB(dbfile=str(self._library_path))
            else:
                db = osxphotos.PhotosDB()

            self._initialized = True
            logger.info(f"Photos library opened: {db.library_path}")
            return db

        except FileNotFoundError as e:
            logger.error(f"Photos library not found: {e}")
            raise PhotosLibraryNotFoundError(self._library_path) from e
        except PermissionError as e:
            logger.error(f"Photos library access denied: {e}")
            raise PhotosAccessDeniedError() from e
        except Exception as e:
            # osxphotos may raise various exceptions for permission issues
            error_str = str(e).lower()
            if "permission" in error_str or "access" in error_str:
                logger.error(f"Photos library access denied: {e}")
                raise PhotosAccessDeniedError(str(e)) from e
            logger.error(f"Failed to open Photos library: {e}")
            raise PhotosLibraryError(f"Failed to open Photos library: {e}") from e

    def check_permissions(self) -> bool:
        """Check if we have access to the Photos library.

        This method attempts to open the Photos library to verify
        permissions. The result is cached for subsequent calls.

        Returns:
            True if access is granted, False otherwise.
        """
        if self._permission_checked:
            return self._has_permission

        try:
            # Try to access the library
            _ = self.db.library_path
            self._has_permission = True
            logger.info("Photos library permission check passed")
        except PhotosAccessDeniedError:
            self._has_permission = False
            logger.warning("Photos library permission denied")
        except PhotosLibraryNotFoundError:
            self._has_permission = False
            logger.warning("Photos library not found")
        except Exception as e:
            self._has_permission = False
            logger.warning(f"Photos library permission check failed: {e}")

        self._permission_checked = True
        return self._has_permission

    def get_library_info(self) -> dict[str, str | int]:
        """Get information about the Photos library.

        Returns:
            Dictionary with library information:
                - path: Library path
                - photo_count: Total number of photos
                - video_count: Total number of videos

        Raises:
            PhotosAccessDeniedError: If access is denied.
        """
        return {
            "path": str(self.db.library_path),
            "photo_count": len(self.db.photos(media_type=["photo"])),
            "video_count": len(self.db.photos(media_type=["video"])),
        }

    def get_video_count(self) -> int:
        """Get the total number of videos in the library.

        Returns:
            Number of videos in the Photos library.

        Raises:
            PhotosAccessDeniedError: If access is denied.
        """
        return len(self.db.photos(media_type=["video"]))

    def get_videos(
        self,
        *,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        albums: list[str] | None = None,
        favorites_only: bool = False,
        include_hidden: bool = False,
    ) -> list[PhotosVideoInfo]:
        """Get videos from the Photos library.

        Args:
            from_date: Only include videos created on or after this date.
            to_date: Only include videos created on or before this date.
            albums: Filter by album names (None for all albums).
            favorites_only: Only include favorite videos.
            include_hidden: Include hidden videos.

        Returns:
            List of PhotosVideoInfo objects.

        Raises:
            PhotosAccessDeniedError: If access is denied.
        """
        logger.debug(
            f"Querying videos: from_date={from_date}, to_date={to_date}, "
            f"albums={albums}, favorites={favorites_only}, hidden={include_hidden}"
        )

        # Build query parameters
        query_params: dict[str, list[str] | datetime | bool] = {
            "media_type": ["video"],
        }

        if from_date is not None:
            query_params["from_date"] = from_date

        if to_date is not None:
            query_params["to_date"] = to_date

        # Query videos
        photos = self.db.photos(**query_params)  # type: ignore[arg-type]

        # Apply additional filters
        videos: list[PhotosVideoInfo] = []
        for photo in photos:
            # Skip hidden if not requested
            if photo.hidden and not include_hidden:
                continue

            # Skip non-favorites if favorites_only
            if favorites_only and not photo.favorite:
                continue

            # Filter by albums if specified
            if albums is not None:
                photo_albums = [a.title for a in photo.albums]
                if not any(album in photo_albums for album in albums):
                    continue

            video_info = self._convert_to_video_info(photo)
            videos.append(video_info)

        logger.info(f"Found {len(videos)} videos matching criteria")
        return videos

    def get_video_by_uuid(self, uuid: str) -> PhotosVideoInfo | None:
        """Get a specific video by its UUID.

        Args:
            uuid: The UUID of the video asset.

        Returns:
            PhotosVideoInfo if found, None otherwise.

        Raises:
            PhotosAccessDeniedError: If access is denied.
        """
        photos = self.db.photos(uuid=[uuid])
        if not photos:
            return None

        return self._convert_to_video_info(photos[0])

    def _convert_to_video_info(self, photo: osxphotos.PhotoInfo) -> PhotosVideoInfo:
        """Convert osxphotos PhotoInfo to PhotosVideoInfo.

        Args:
            photo: osxphotos PhotoInfo object.

        Returns:
            PhotosVideoInfo with extracted information.
        """
        # Get path (may be None for iCloud-only files)
        path: Path | None = None
        if photo.path:
            path = Path(photo.path)

        # Get location
        location: tuple[float, float] | None = None
        if photo.location and photo.location[0] is not None:
            location = (photo.location[0], photo.location[1])

        # Get album names
        albums = [album.title for album in photo.albums if album.title]

        return PhotosVideoInfo(
            uuid=photo.uuid,
            filename=photo.original_filename,
            path=path,
            date=photo.date,
            date_modified=photo.date_modified,
            duration=photo.duration or 0.0,
            favorite=photo.favorite,
            hidden=photo.hidden,
            in_cloud=photo.iscloudasset,
            location=location,
            albums=albums,
        )

    def close(self) -> None:
        """Close the Photos library connection.

        This releases any resources held by the connection.
        The library can be reopened by accessing the db property.
        """
        self._db = None
        self._initialized = False
        self._permission_checked = False
        logger.debug("Photos library connection closed")

    def __enter__(self) -> PhotosLibrary:
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
        """Context manager exit.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        self.close()


def get_permission_instructions() -> str:
    """Get instructions for granting Photos library access.

    Returns:
        Multi-line string with detailed instructions for granting
        Full Disk Access permission.
    """
    return """
Photos Library Access Denied

Video Converter needs access to your Photos library.

To grant access:
1. Open System Settings → Privacy & Security → Full Disk Access
2. Click the + button
3. Navigate to: /Applications/Utilities/Terminal.app
   (or the application running this script)
4. Add it to the list and enable the toggle
5. Restart the application and try again

Quick access command:
  open "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"
""".strip()


@dataclass
class LibraryStats:
    """Statistics about videos in the Photos library.

    Attributes:
        total: Total number of videos.
        h264: Number of H.264 encoded videos.
        hevc: Number of H.265/HEVC encoded videos.
        other: Number of videos with other codecs.
        in_cloud: Number of videos stored in iCloud only.
        total_size_h264: Total size of H.264 videos in bytes.
        estimated_savings: Estimated storage savings after conversion in bytes.
    """

    total: int = 0
    h264: int = 0
    hevc: int = 0
    other: int = 0
    in_cloud: int = 0
    total_size_h264: int = 0

    @property
    def estimated_savings(self) -> int:
        """Estimate storage savings after H.265 conversion.

        Assumes approximately 50% size reduction with H.265.

        Returns:
            Estimated bytes that could be saved.
        """
        return int(self.total_size_h264 * 0.5)

    @property
    def estimated_savings_gb(self) -> float:
        """Get estimated savings in gigabytes.

        Returns:
            Estimated savings in GB.
        """
        return self.estimated_savings / (1024 * 1024 * 1024)


class PhotosVideoFilter:
    """Filter Photos library videos for conversion candidates.

    This class provides filtering capabilities to identify H.264 videos
    that need conversion to H.265/HEVC, with support for album-based
    and date-based filtering.

    SDS Reference: SDS-P01-005
    SRS Reference: SRS-302 (Video Filtering)

    Example:
        >>> library = PhotosLibrary()
        >>> filter = PhotosVideoFilter(
        ...     library,
        ...     exclude_albums=["Screenshots", "Bursts"]
        ... )
        >>> candidates = filter.get_conversion_candidates(limit=100)
        >>> print(f"Found {len(candidates)} videos to convert")
    """

    # Default albums to exclude from conversion
    DEFAULT_EXCLUDE_ALBUMS = frozenset({"Screenshots", "Bursts", "Slo-mo"})

    def __init__(
        self,
        library: PhotosLibrary,
        include_albums: list[str] | None = None,
        exclude_albums: list[str] | None = None,
    ) -> None:
        """Initialize PhotosVideoFilter.

        Args:
            library: PhotosLibrary instance to filter.
            include_albums: Only include videos from these albums.
                If None, includes all albums.
            exclude_albums: Exclude videos from these albums.
                If None, uses DEFAULT_EXCLUDE_ALBUMS.
        """
        self._library = library
        self._include_albums = set(include_albums) if include_albums else None
        self._exclude_albums = (
            set(exclude_albums)
            if exclude_albums is not None
            else set(self.DEFAULT_EXCLUDE_ALBUMS)
        )
        self._codec_detector: CodecDetector | None = None

    @property
    def codec_detector(self) -> CodecDetector:
        """Get or create codec detector instance.

        Returns:
            CodecDetector for analyzing video codecs.
        """
        if self._codec_detector is None:
            from video_converter.processors.codec_detector import CodecDetector
            self._codec_detector = CodecDetector()
        return self._codec_detector

    def _passes_album_filter(self, video: PhotosVideoInfo) -> bool:
        """Check if video passes album filter.

        Args:
            video: Video to check.

        Returns:
            True if video passes album filter, False otherwise.
        """
        video_albums = set(video.albums)

        # Check exclude filter first
        if self._exclude_albums and video_albums & self._exclude_albums:
            return False

        # Check include filter
        if self._include_albums is not None:
            if not video_albums & self._include_albums:
                return False

        return True

    def _detect_codec(self, video: PhotosVideoInfo) -> str | None:
        """Detect video codec using FFprobe.

        Args:
            video: Video to analyze.

        Returns:
            Codec name or None if detection fails.
        """
        if not video.is_available_locally or video.path is None:
            return None

        try:
            from video_converter.processors.codec_detector import (
                CorruptedVideoError,
                InvalidVideoError,
            )
            info = self.codec_detector.analyze(video.path)
            return info.codec
        except (InvalidVideoError, CorruptedVideoError, FileNotFoundError) as e:
            logger.warning(f"Failed to detect codec for {video.filename}: {e}")
            return None

    def _enrich_with_codec(self, video: PhotosVideoInfo) -> PhotosVideoInfo:
        """Enrich video info with codec and size data.

        Args:
            video: Video to enrich.

        Returns:
            Video with codec and size information.
        """
        if not video.is_available_locally or video.path is None:
            return video

        # Get codec
        codec = self._detect_codec(video)

        # Get file size
        try:
            size = video.path.stat().st_size if video.path else 0
        except OSError:
            size = 0

        return PhotosVideoInfo(
            uuid=video.uuid,
            filename=video.filename,
            path=video.path,
            date=video.date,
            date_modified=video.date_modified,
            duration=video.duration,
            favorite=video.favorite,
            hidden=video.hidden,
            in_cloud=video.in_cloud,
            location=video.location,
            albums=video.albums,
            codec=codec,
            size=size,
        )

    def get_conversion_candidates(
        self,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int | None = None,
    ) -> list[PhotosVideoInfo]:
        """Get videos that need conversion from H.264 to H.265.

        This method filters Photos library videos to find candidates
        for conversion, applying album and date filters.

        Args:
            from_date: Only include videos created after this date.
            to_date: Only include videos created before this date.
            limit: Maximum number of candidates to return.

        Returns:
            List of PhotosVideoInfo for videos that need conversion.
        """
        logger.info("Searching for H.264 conversion candidates...")

        candidates: list[PhotosVideoInfo] = []

        # Get all videos with date filtering
        videos = self._library.get_videos(
            from_date=from_date,
            to_date=to_date,
        )

        for video in videos:
            # Skip if doesn't pass album filter
            if not self._passes_album_filter(video):
                continue

            # Skip if not available locally
            if not video.is_available_locally:
                logger.debug(f"Skipping iCloud-only video: {video.filename}")
                continue

            # Enrich with codec info
            enriched = self._enrich_with_codec(video)

            # Check if needs conversion
            if enriched.needs_conversion:
                candidates.append(enriched)
                logger.debug(f"Found candidate: {enriched.filename} ({enriched.codec})")

                if limit and len(candidates) >= limit:
                    break

        logger.info(f"Found {len(candidates)} H.264 videos for conversion")
        return candidates

    def get_stats(self) -> LibraryStats:
        """Get statistics about videos in the library.

        Analyzes all videos in the library to provide statistics
        about codec distribution and potential storage savings.

        Returns:
            LibraryStats with codec distribution and size information.
        """
        logger.info("Analyzing library statistics...")

        stats = LibraryStats()

        videos = self._library.get_videos()
        stats.total = len(videos)

        for video in videos:
            # Track iCloud-only videos
            if not video.is_available_locally:
                stats.in_cloud += 1
                continue

            # Detect codec
            codec = self._detect_codec(video)
            if codec is None:
                stats.other += 1
                continue

            codec_lower = codec.lower()
            if codec_lower in PhotosVideoInfo.H264_CODECS:
                stats.h264 += 1
                try:
                    if video.path:
                        stats.total_size_h264 += video.path.stat().st_size
                except OSError:
                    pass
            elif codec_lower in PhotosVideoInfo.HEVC_CODECS:
                stats.hevc += 1
            else:
                stats.other += 1

        logger.info(
            f"Library stats: {stats.total} total, {stats.h264} H.264, "
            f"{stats.hevc} HEVC, {stats.in_cloud} in cloud"
        )
        return stats


class VideoExporter:
    """Export videos from Photos library to temporary directory.

    This class provides functionality to export original quality videos
    from the Photos library to a temporary directory for conversion,
    with support for progress tracking and cleanup.

    SDS Reference: SDS-P01-006
    SRS Reference: SRS-303 (Video Export)

    Example:
        >>> exporter = VideoExporter()
        >>> video = library.get_video_by_uuid("some-uuid")
        >>> if video and video.is_available_locally:
        ...     exported_path = exporter.export(video)
        ...     # ... do conversion ...
        ...     exporter.cleanup(exported_path)
        >>> exporter.cleanup_all()

    Attributes:
        temp_dir: Directory where exported files are stored.
    """

    # Buffer size for file copy operations (1 MB)
    COPY_BUFFER_SIZE = 1024 * 1024

    def __init__(self, temp_dir: Path | None = None) -> None:
        """Initialize video exporter.

        Args:
            temp_dir: Custom temporary directory for exports.
                If None, creates a system temporary directory.
        """
        if temp_dir is not None:
            self._temp_dir = temp_dir
            self._temp_dir.mkdir(parents=True, exist_ok=True)
            self._owns_temp_dir = False
        else:
            self._temp_dir = Path(tempfile.mkdtemp(prefix="video_converter_"))
            self._owns_temp_dir = True

        self._exported_files: set[Path] = set()
        logger.debug(f"VideoExporter initialized with temp_dir: {self._temp_dir}")

    @property
    def temp_dir(self) -> Path:
        """Get the temporary directory path.

        Returns:
            Path to the temporary directory.
        """
        return self._temp_dir

    def export(
        self,
        video: PhotosVideoInfo,
        on_progress: Callable[[float], None] | None = None,
    ) -> Path:
        """Export video to temporary directory.

        Copies the original video file to the temporary directory,
        preserving file metadata (modification times).

        Args:
            video: Video information from Photos library.
            on_progress: Optional callback for progress updates.
                Called with progress value from 0.0 to 1.0.

        Returns:
            Path to the exported video file.

        Raises:
            VideoNotAvailableError: Video is in iCloud and not downloaded.
            ExportError: Export failed due to file system error.
        """
        # Validate video availability
        if video.in_cloud and not video.is_available_locally:
            raise VideoNotAvailableError(video.filename)

        if video.path is None:
            raise ExportError("No path available", video.filename)

        if not video.path.exists():
            raise ExportError("Source file does not exist", video.filename)

        # Generate unique output path to avoid collisions
        output_path = self._temp_dir / f"{video.uuid}_{video.filename}"

        logger.info(f"Exporting video: {video.filename}")
        logger.debug(f"Source: {video.path}")
        logger.debug(f"Destination: {output_path}")

        try:
            if on_progress is not None:
                self._copy_with_progress(video.path, output_path, on_progress)
            else:
                # Use shutil.copy2 to preserve metadata
                shutil.copy2(video.path, output_path)

            self._exported_files.add(output_path)
            logger.info(f"Exported: {video.filename} -> {output_path.name}")
            return output_path

        except PermissionError as e:
            raise ExportError(f"Permission denied: {e}", video.filename) from e
        except OSError as e:
            # Clean up partial file if it exists
            if output_path.exists():
                try:
                    output_path.unlink()
                except OSError:
                    pass
            raise ExportError(str(e), video.filename) from e

    def _copy_with_progress(
        self,
        src: Path,
        dst: Path,
        callback: Callable[[float], None],
    ) -> None:
        """Copy file with progress reporting.

        Copies file in chunks and reports progress via callback.
        Also preserves file metadata after copy.

        Args:
            src: Source file path.
            dst: Destination file path.
            callback: Progress callback (0.0 to 1.0).
        """
        total_size = src.stat().st_size
        copied = 0

        with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
            while True:
                chunk = fsrc.read(self.COPY_BUFFER_SIZE)
                if not chunk:
                    break
                fdst.write(chunk)
                copied += len(chunk)
                callback(copied / total_size)

        # Preserve file metadata (modification times)
        shutil.copystat(src, dst)

    def cleanup(self, path: Path) -> bool:
        """Remove a single exported file.

        Only removes files that are within the temporary directory
        and were exported by this exporter.

        Args:
            path: Path to the exported file to remove.

        Returns:
            True if file was removed, False otherwise.
        """
        # Safety check: only remove files in our temp directory
        try:
            path.relative_to(self._temp_dir)
        except ValueError:
            logger.warning(f"Refusing to cleanup file outside temp_dir: {path}")
            return False

        if path.exists():
            try:
                path.unlink()
                self._exported_files.discard(path)
                logger.debug(f"Cleaned up: {path.name}")
                return True
            except OSError as e:
                logger.warning(f"Failed to cleanup {path.name}: {e}")
                return False
        return False

    def cleanup_all(self) -> int:
        """Remove all exported files and the temporary directory.

        Only removes the temporary directory if it was created by
        this exporter (not a custom directory).

        Returns:
            Number of files removed.
        """
        removed_count = 0

        # Remove tracked files
        for path in list(self._exported_files):
            if self.cleanup(path):
                removed_count += 1

        # Remove temp directory if we own it
        if self._owns_temp_dir and self._temp_dir.exists():
            try:
                shutil.rmtree(self._temp_dir, ignore_errors=True)
                logger.info(f"Removed temporary directory: {self._temp_dir}")
            except OSError as e:
                logger.warning(f"Failed to remove temp directory: {e}")

        self._exported_files.clear()
        return removed_count

    def get_exported_count(self) -> int:
        """Get the number of currently exported files.

        Returns:
            Number of files in the exported files set.
        """
        return len(self._exported_files)

    def get_temp_dir_size(self) -> int:
        """Get total size of files in the temporary directory.

        Returns:
            Total size in bytes.
        """
        total = 0
        if self._temp_dir.exists():
            for path in self._temp_dir.iterdir():
                if path.is_file():
                    try:
                        total += path.stat().st_size
                    except OSError:
                        pass
        return total

    def __enter__(self) -> VideoExporter:
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
        """Context manager exit - cleanup all exported files.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        self.cleanup_all()
