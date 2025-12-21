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
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import osxphotos

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

    @property
    def is_available_locally(self) -> bool:
        """Check if the video file is available locally.

        Returns:
            True if the file exists locally, False if in iCloud only.
        """
        if self.path is None:
            return False
        return self.path.exists()


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
