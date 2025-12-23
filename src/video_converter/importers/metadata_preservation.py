"""Metadata preservation for Photos re-import functionality.

This module provides classes and functions for preserving metadata
when re-importing converted videos to the Photos library, including
album membership, favorites status, date/time, location, and other metadata.

SDS Reference: SDS-P01-010
SRS Reference: SRS-306 (Metadata Preservation)

Example:
    >>> from video_converter.importers.metadata_preservation import (
    ...     MetadataPreserver,
    ...     VideoMetadataSnapshot,
    ... )
    >>> preserver = MetadataPreserver()
    >>> snapshot = preserver.capture_metadata(video_info)
    >>> # ... convert video ...
    >>> preserver.embed_metadata_in_file(converted_path, snapshot)
    >>> new_uuid = importer.import_video(converted_path)
    >>> preserver.apply_photos_metadata(new_uuid, snapshot)
    >>> result = preserver.verify_metadata(new_uuid, snapshot)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from video_converter.processors.metadata import MetadataProcessor
from video_converter.utils.applescript import (
    AppleScriptExecutionError,
    AppleScriptRunner,
    AppleScriptTimeoutError,
    escape_applescript_string,
)

if TYPE_CHECKING:
    from video_converter.extractors.photos_extractor import PhotosVideoInfo

logger = logging.getLogger(__name__)


class MetadataPreservationError(Exception):
    """Base exception for metadata preservation operations.

    Attributes:
        message: Human-readable error message.
        uuid: UUID of the video involved (if applicable).
    """

    def __init__(self, message: str, uuid: str | None = None) -> None:
        """Initialize MetadataPreservationError.

        Args:
            message: Human-readable error message.
            uuid: UUID of the video involved.
        """
        super().__init__(message)
        self.uuid = uuid


class MetadataEmbedError(MetadataPreservationError):
    """Raised when embedding metadata in file fails."""

    def __init__(self, path: Path, reason: str) -> None:
        """Initialize MetadataEmbedError.

        Args:
            path: Path to the video file.
            reason: Description of what failed.
        """
        super().__init__(f"Failed to embed metadata in {path.name}: {reason}")
        self.path = path
        self.reason = reason


class MetadataApplicationError(MetadataPreservationError):
    """Raised when applying metadata via Photos AppleScript fails."""

    def __init__(self, uuid: str, reason: str) -> None:
        """Initialize MetadataApplicationError.

        Args:
            uuid: UUID of the video in Photos.
            reason: Description of what failed.
        """
        super().__init__(f"Failed to apply metadata to {uuid}: {reason}", uuid=uuid)
        self.reason = reason


@dataclass
class VideoMetadataSnapshot:
    """Complete snapshot of video metadata for re-import.

    This dataclass captures all metadata from an original video
    that should be preserved when re-importing the converted version.

    Attributes:
        uuid: Original video UUID in Photos library.
        filename: Original filename.
        albums: List of album names containing this video.
        is_favorite: Whether the video is marked as favorite.
        is_hidden: Whether the video is hidden.
        date: Original creation date.
        date_modified: Last modification date.
        location: GPS coordinates as (latitude, longitude) tuple.
        description: Video description/caption.
        title: Video title (may be same as filename).
        keywords: List of keywords/tags.

    Example:
        >>> snapshot = VideoMetadataSnapshot(
        ...     uuid="ABC123",
        ...     filename="vacation.mov",
        ...     albums=["Vacation", "2024"],
        ...     is_favorite=True,
        ...     date=datetime(2024, 7, 15, 10, 30, 0),
        ...     location=(37.7749, -122.4194),
        ... )
    """

    uuid: str
    filename: str
    albums: list[str] = field(default_factory=list)
    is_favorite: bool = False
    is_hidden: bool = False
    date: datetime | None = None
    date_modified: datetime | None = None
    location: tuple[float, float] | None = None
    description: str | None = None
    title: str | None = None
    keywords: list[str] = field(default_factory=list)

    @property
    def has_location(self) -> bool:
        """Check if the snapshot has GPS location data."""
        return self.location is not None

    @property
    def has_albums(self) -> bool:
        """Check if the snapshot has album membership."""
        return len(self.albums) > 0


@dataclass
class MetadataTolerance:
    """Tolerance settings for metadata verification.

    Defines acceptable differences between original and imported metadata.

    Attributes:
        date_seconds: Maximum date difference in seconds.
        location_degrees: Maximum GPS coordinate difference in degrees.

    Example:
        >>> tolerance = MetadataTolerance.default()
        >>> tolerance.date_seconds
        1.0
    """

    date_seconds: float = 1.0
    location_degrees: float = 0.000001  # ~0.1 meters

    @classmethod
    def default(cls) -> MetadataTolerance:
        """Create default tolerance settings."""
        return cls()

    @classmethod
    def strict(cls) -> MetadataTolerance:
        """Create strict tolerance settings for exact matching."""
        return cls(date_seconds=0.0, location_degrees=0.0)

    @classmethod
    def relaxed(cls) -> MetadataTolerance:
        """Create relaxed tolerance for Photos app quirks."""
        return cls(date_seconds=60.0, location_degrees=0.0001)


@dataclass
class VerificationResult:
    """Result of metadata verification after re-import.

    Attributes:
        success: True if all critical metadata was preserved.
        albums_matched: True if all albums were preserved.
        favorite_matched: True if favorite status was preserved.
        date_matched: True if date was preserved within tolerance.
        location_matched: True if GPS was preserved within tolerance.
        details: Additional verification details or error messages.
        missing_albums: Albums that were not preserved.

    Example:
        >>> result = VerificationResult(
        ...     success=True,
        ...     albums_matched=True,
        ...     favorite_matched=True,
        ...     date_matched=True,
        ...     location_matched=True,
        ... )
    """

    success: bool
    albums_matched: bool = True
    favorite_matched: bool = True
    date_matched: bool = True
    location_matched: bool = True
    details: str = ""
    missing_albums: list[str] = field(default_factory=list)


class MetadataPreserver:
    """Preserve metadata when re-importing converted videos to Photos.

    This class provides methods to capture, embed, apply, and verify
    metadata during the Photos re-import workflow.

    SDS Reference: SDS-P01-010

    Example:
        >>> preserver = MetadataPreserver()
        >>> # Capture before conversion
        >>> snapshot = preserver.capture_metadata(video_info)
        >>> # Embed in converted file
        >>> preserver.embed_metadata_in_file(converted_path, snapshot)
        >>> # Import to Photos
        >>> new_uuid = importer.import_video(converted_path)
        >>> # Apply Photos-specific metadata
        >>> preserver.apply_photos_metadata(new_uuid, snapshot)
        >>> # Verify
        >>> result = preserver.verify_metadata(new_uuid, snapshot)
    """

    def __init__(
        self,
        metadata_processor: MetadataProcessor | None = None,
        script_runner: AppleScriptRunner | None = None,
    ) -> None:
        """Initialize MetadataPreserver.

        Args:
            metadata_processor: MetadataProcessor for ExifTool operations.
                If None, creates a new one.
            script_runner: AppleScriptRunner for Photos automation.
                If None, creates a new one.
        """
        self._metadata_processor = metadata_processor or MetadataProcessor()
        self._script_runner = script_runner or AppleScriptRunner(timeout=120.0)

        logger.debug("MetadataPreserver initialized")

    def capture_metadata(self, video: PhotosVideoInfo) -> VideoMetadataSnapshot:
        """Capture all metadata from original video.

        Creates a snapshot of all relevant metadata from the original
        video that should be preserved during re-import.

        Args:
            video: PhotosVideoInfo from the Photos library.

        Returns:
            VideoMetadataSnapshot containing all captured metadata.

        Example:
            >>> library = PhotosLibrary()
            >>> video = library.get_video_by_uuid("ABC123")
            >>> snapshot = preserver.capture_metadata(video)
        """
        logger.info(f"Capturing metadata from: {video.filename}")

        snapshot = VideoMetadataSnapshot(
            uuid=video.uuid,
            filename=video.filename,
            albums=list(video.albums),
            is_favorite=video.favorite,
            is_hidden=video.hidden,
            date=video.date,
            date_modified=video.date_modified,
            location=video.location,
        )

        logger.debug(
            f"Captured metadata: albums={len(snapshot.albums)}, "
            f"favorite={snapshot.is_favorite}, "
            f"has_location={snapshot.has_location}"
        )

        return snapshot

    def embed_metadata_in_file(
        self,
        video_path: Path,
        metadata: VideoMetadataSnapshot,
    ) -> bool:
        """Embed metadata in video file using ExifTool.

        This method embeds date/time and GPS metadata directly in the
        video file before importing to Photos.

        Args:
            video_path: Path to the converted video file.
            metadata: Metadata snapshot to embed.

        Returns:
            True if metadata was embedded successfully.

        Raises:
            FileNotFoundError: If video file doesn't exist.
            MetadataEmbedError: If embedding fails.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        logger.info(f"Embedding metadata in: {video_path.name}")

        success = True

        # Embed creation date
        if metadata.date is not None:
            date_str = metadata.date.strftime("%Y:%m:%d %H:%M:%S")
            try:
                # Set multiple date tags for maximum compatibility
                date_tags = [
                    "CreateDate",
                    "ModifyDate",
                    "MediaCreateDate",
                    "MediaModifyDate",
                    "TrackCreateDate",
                    "TrackModifyDate",
                ]
                for tag in date_tags:
                    result = self._metadata_processor.set_tag(
                        video_path, tag, date_str, overwrite_original=True
                    )
                    if not result:
                        logger.warning(f"Failed to set {tag}")
                        success = False

                logger.debug(f"Embedded date: {date_str}")
            except Exception as e:
                logger.error(f"Failed to embed date: {e}")
                raise MetadataEmbedError(video_path, f"Failed to set date: {e}") from e

        # Embed GPS location
        if metadata.location is not None:
            lat, lon = metadata.location
            try:
                # Set GPS tags
                lat_ref = "N" if lat >= 0 else "S"
                lon_ref = "E" if lon >= 0 else "W"

                gps_tags = {
                    "GPSLatitude": str(abs(lat)),
                    "GPSLatitudeRef": lat_ref,
                    "GPSLongitude": str(abs(lon)),
                    "GPSLongitudeRef": lon_ref,
                }

                # QuickTime GPS coordinates format
                lat_sign = "+" if lat >= 0 else ""
                lon_sign = "+" if lon >= 0 else ""
                gps_coords = f"{lat_sign}{lat:.6f}{lon_sign}{lon:.6f}/"
                gps_tags["GPSCoordinates"] = gps_coords

                for tag, value in gps_tags.items():
                    result = self._metadata_processor.set_tag(
                        video_path, tag, value, overwrite_original=True
                    )
                    if not result:
                        logger.warning(f"Failed to set {tag}")
                        success = False

                logger.debug(f"Embedded GPS: {lat:.6f}, {lon:.6f}")
            except Exception as e:
                logger.error(f"Failed to embed GPS: {e}")
                raise MetadataEmbedError(video_path, f"Failed to set GPS: {e}") from e

        # Embed description if present
        if metadata.description:
            try:
                result = self._metadata_processor.set_tag(
                    video_path,
                    "Description",
                    metadata.description,
                    overwrite_original=True,
                )
                if not result:
                    logger.warning("Failed to set Description")
                    success = False
            except Exception as e:
                logger.warning(f"Failed to embed description: {e}")

        # Embed keywords if present
        if metadata.keywords:
            try:
                keywords_str = ", ".join(metadata.keywords)
                result = self._metadata_processor.set_tag(
                    video_path, "Keywords", keywords_str, overwrite_original=True
                )
                if not result:
                    logger.warning("Failed to set Keywords")
                    success = False
            except Exception as e:
                logger.warning(f"Failed to embed keywords: {e}")

        logger.info(f"Metadata embedding {'succeeded' if success else 'partially failed'}")
        return success

    def apply_photos_metadata(
        self,
        new_uuid: str,
        metadata: VideoMetadataSnapshot,
    ) -> bool:
        """Apply Photos-specific metadata via AppleScript.

        This method applies metadata that cannot be embedded in the file,
        such as album membership and favorite status.

        Args:
            new_uuid: UUID of the newly imported video in Photos.
            metadata: Metadata snapshot to apply.

        Returns:
            True if all metadata was applied successfully.

        Raises:
            MetadataApplicationError: If applying metadata fails.
        """
        logger.info(f"Applying Photos metadata to: {new_uuid}")

        success = True

        # Set favorite status
        if metadata.is_favorite:
            try:
                self._set_favorite(new_uuid, favorite=True)
                logger.debug("Set favorite status")
            except Exception as e:
                logger.error(f"Failed to set favorite: {e}")
                success = False

        # Set hidden status
        if metadata.is_hidden:
            try:
                self._set_hidden(new_uuid, hidden=True)
                logger.debug("Set hidden status")
            except Exception as e:
                logger.warning(f"Failed to set hidden status: {e}")
                success = False

        # Add to albums
        for album_name in metadata.albums:
            try:
                self._add_to_album(new_uuid, album_name)
                logger.debug(f"Added to album: {album_name}")
            except Exception as e:
                logger.warning(f"Failed to add to album '{album_name}': {e}")
                success = False

        # Set description
        if metadata.description:
            try:
                self._set_description(new_uuid, metadata.description)
                logger.debug("Set description")
            except Exception as e:
                logger.warning(f"Failed to set description: {e}")

        # Set keywords
        if metadata.keywords:
            try:
                self._set_keywords(new_uuid, metadata.keywords)
                logger.debug("Set keywords")
            except Exception as e:
                logger.warning(f"Failed to set keywords: {e}")

        logger.info(f"Photos metadata application {'succeeded' if success else 'partially failed'}")
        return success

    def verify_metadata(
        self,
        new_uuid: str,
        expected: VideoMetadataSnapshot,
        tolerance: MetadataTolerance | None = None,
    ) -> VerificationResult:
        """Verify metadata was preserved correctly.

        Compares the metadata of the imported video against the expected
        values from the original.

        Args:
            new_uuid: UUID of the imported video in Photos.
            expected: Expected metadata snapshot.
            tolerance: Tolerance settings for comparison.
                If None, uses default tolerance.

        Returns:
            VerificationResult with detailed comparison results.
        """
        logger.info(f"Verifying metadata for: {new_uuid}")

        if tolerance is None:
            tolerance = MetadataTolerance.default()

        # Get actual metadata from Photos
        actual = self._get_photos_metadata(new_uuid)
        if actual is None:
            return VerificationResult(
                success=False,
                details=f"Could not retrieve metadata for UUID: {new_uuid}",
            )

        # Check albums
        missing_albums = []
        for album in expected.albums:
            if album not in actual.get("albums", []):
                missing_albums.append(album)
        albums_matched = len(missing_albums) == 0

        # Check favorite
        favorite_matched = expected.is_favorite == actual.get("favorite", False)

        # Check date (with tolerance)
        date_matched = True
        if expected.date is not None:
            actual_date = actual.get("date")
            if actual_date is not None:
                diff = abs((expected.date - actual_date).total_seconds())
                date_matched = diff <= tolerance.date_seconds
            else:
                date_matched = False

        # Check location (with tolerance)
        location_matched = True
        if expected.location is not None:
            actual_location = actual.get("location")
            if actual_location is not None:
                lat_diff = abs(expected.location[0] - actual_location[0])
                lon_diff = abs(expected.location[1] - actual_location[1])
                location_matched = (
                    lat_diff <= tolerance.location_degrees
                    and lon_diff <= tolerance.location_degrees
                )
            else:
                location_matched = False

        # Build result
        success = albums_matched and favorite_matched and date_matched and location_matched

        details_parts = []
        if not albums_matched:
            details_parts.append(f"Missing albums: {missing_albums}")
        if not favorite_matched:
            details_parts.append(
                f"Favorite mismatch: expected {expected.is_favorite}, "
                f"got {actual.get('favorite', False)}"
            )
        if not date_matched:
            details_parts.append("Date mismatch")
        if not location_matched:
            details_parts.append("Location mismatch")

        result = VerificationResult(
            success=success,
            albums_matched=albums_matched,
            favorite_matched=favorite_matched,
            date_matched=date_matched,
            location_matched=location_matched,
            missing_albums=missing_albums,
            details="; ".join(details_parts) if details_parts else "All metadata verified",
        )

        logger.info(f"Verification {'passed' if success else 'failed'}: {result.details}")
        return result

    def _set_favorite(self, uuid: str, *, favorite: bool) -> None:
        """Set favorite status via AppleScript."""
        escaped_uuid = escape_applescript_string(uuid)
        favorite_str = "true" if favorite else "false"
        script = f'''
tell application "Photos"
    set targetItem to media item id "{escaped_uuid}"
    set favorite of targetItem to {favorite_str}
end tell
'''
        try:
            self._script_runner.run(script, check=True)
        except (AppleScriptTimeoutError, AppleScriptExecutionError) as e:
            raise MetadataApplicationError(uuid, f"Failed to set favorite: {e}") from e

    def _set_hidden(self, uuid: str, *, hidden: bool) -> None:
        """Set hidden status via AppleScript."""
        escaped_uuid = escape_applescript_string(uuid)
        hidden_str = "true" if hidden else "false"
        script = f'''
tell application "Photos"
    set targetItem to media item id "{escaped_uuid}"
    set hidden of targetItem to {hidden_str}
end tell
'''
        try:
            self._script_runner.run(script, check=True)
        except (AppleScriptTimeoutError, AppleScriptExecutionError) as e:
            logger.warning(f"Failed to set hidden status: {e}")

    def _add_to_album(self, uuid: str, album_name: str) -> None:
        """Add video to album via AppleScript."""
        escaped_uuid = escape_applescript_string(uuid)
        escaped_album = escape_applescript_string(album_name)
        script = f'''
tell application "Photos"
    set targetItem to media item id "{escaped_uuid}"
    try
        set targetAlbum to album "{escaped_album}"
        add {{targetItem}} to targetAlbum
    on error errMsg
        error "Album not found or cannot add: " & errMsg
    end try
end tell
'''
        try:
            self._script_runner.run(script, check=True)
        except (AppleScriptTimeoutError, AppleScriptExecutionError) as e:
            raise MetadataApplicationError(
                uuid, f"Failed to add to album '{album_name}': {e}"
            ) from e

    def _set_description(self, uuid: str, description: str) -> None:
        """Set description via AppleScript."""
        escaped_uuid = escape_applescript_string(uuid)
        escaped_desc = escape_applescript_string(description)
        script = f'''
tell application "Photos"
    set targetItem to media item id "{escaped_uuid}"
    set description of targetItem to "{escaped_desc}"
end tell
'''
        try:
            self._script_runner.run(script, check=True)
        except (AppleScriptTimeoutError, AppleScriptExecutionError) as e:
            logger.warning(f"Failed to set description: {e}")

    def _set_keywords(self, uuid: str, keywords: list[str]) -> None:
        """Set keywords via AppleScript."""
        escaped_uuid = escape_applescript_string(uuid)
        keywords_list = ", ".join(f'"{escape_applescript_string(k)}"' for k in keywords)
        script = f'''
tell application "Photos"
    set targetItem to media item id "{escaped_uuid}"
    set keywords of targetItem to {{{keywords_list}}}
end tell
'''
        try:
            self._script_runner.run(script, check=True)
        except (AppleScriptTimeoutError, AppleScriptExecutionError) as e:
            logger.warning(f"Failed to set keywords: {e}")

    def _get_photos_metadata(self, uuid: str) -> dict | None:
        """Get metadata from Photos library via AppleScript."""
        escaped_uuid = escape_applescript_string(uuid)
        script = f'''
tell application "Photos"
    try
        set targetItem to media item id "{escaped_uuid}"
        set itemFavorite to favorite of targetItem
        set itemDate to date of targetItem
        set itemAlbums to {{}}

        repeat with anAlbum in albums
            if {{targetItem}} is in (get media items of anAlbum) then
                set end of itemAlbums to name of anAlbum
            end if
        end repeat

        set dateStr to (year of itemDate as text) & "-" & ¬
            (text -2 thru -1 of ("0" & (month of itemDate as number))) & "-" & ¬
            (text -2 thru -1 of ("0" & day of itemDate)) & "T" & ¬
            (text -2 thru -1 of ("0" & hours of itemDate)) & ":" & ¬
            (text -2 thru -1 of ("0" & minutes of itemDate)) & ":" & ¬
            (text -2 thru -1 of ("0" & seconds of itemDate))

        set albumStr to ""
        repeat with i from 1 to count of itemAlbums
            if i > 1 then set albumStr to albumStr & "|"
            set albumStr to albumStr & (item i of itemAlbums)
        end repeat

        return itemFavorite & "|||" & dateStr & "|||" & albumStr
    on error errMsg
        return "ERROR:" & errMsg
    end try
end tell
'''
        try:
            result = self._script_runner.run(script, timeout=60.0)
            if not result.success or result.result.startswith("ERROR:"):
                logger.warning(f"Failed to get Photos metadata: {result.result}")
                return None

            parts = result.result.split("|||")
            if len(parts) < 3:
                return None

            metadata: dict = {
                "favorite": parts[0].lower() == "true",
                "albums": parts[2].split("|") if parts[2] else [],
            }

            # Parse date
            try:
                metadata["date"] = datetime.fromisoformat(parts[1])
            except ValueError:
                metadata["date"] = None

            return metadata

        except (AppleScriptTimeoutError, AppleScriptExecutionError) as e:
            logger.warning(f"Failed to get Photos metadata: {e}")
            return None
