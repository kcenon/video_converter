"""Photos library importer for re-importing converted videos.

This module provides the PhotosImporter class that handles importing
converted videos back to the Photos library using AppleScript integration.

SDS Reference: SDS-P01-008
SRS Reference: SRS-305 (Photos Re-Import)

Example:
    >>> importer = PhotosImporter()
    >>> uuid = importer.import_video(Path("/path/to/converted.mp4"))
    >>> print(f"Imported with UUID: {uuid}")
"""

from __future__ import annotations

import logging
from pathlib import Path

from video_converter.utils.applescript import (
    AppleScriptExecutionError,
    AppleScriptRunner,
    AppleScriptTimeoutError,
    escape_applescript_string,
)

logger = logging.getLogger(__name__)


class PhotosImportError(Exception):
    """Base exception for Photos import operations.

    Attributes:
        video_path: Path to the video that failed to import.
    """

    def __init__(
        self,
        message: str,
        video_path: Path | None = None,
    ) -> None:
        """Initialize PhotosImportError.

        Args:
            message: Human-readable error message.
            video_path: Path to the video that failed.
        """
        super().__init__(message)
        self.video_path = video_path


class PhotosNotRunningError(PhotosImportError):
    """Raised when Photos.app cannot be activated.

    This typically occurs when Photos.app is not installed or
    cannot be launched due to system issues.
    """

    def __init__(self, video_path: Path | None = None) -> None:
        """Initialize with optional video path.

        Args:
            video_path: Path to the video that was being imported.
        """
        super().__init__(
            "Photos.app could not be activated. "
            "Ensure Photos is installed and accessible.",
            video_path=video_path,
        )


class ImportTimeoutError(PhotosImportError):
    """Raised when import operation exceeds timeout.

    Attributes:
        timeout: The timeout value in seconds.
    """

    def __init__(
        self,
        timeout: float,
        video_path: Path | None = None,
    ) -> None:
        """Initialize with timeout value.

        Args:
            timeout: The timeout value that was exceeded.
            video_path: Path to the video that was being imported.
        """
        self.timeout = timeout
        super().__init__(
            f"Import operation timed out after {timeout:.1f} seconds. "
            "The video may still be importing in the background.",
            video_path=video_path,
        )


class DuplicateVideoError(PhotosImportError):
    """Raised when video already exists in library.

    This exception indicates that Photos detected the video
    as a duplicate and did not import it.
    """

    def __init__(self, video_path: Path) -> None:
        """Initialize with video path.

        Args:
            video_path: Path to the duplicate video.
        """
        super().__init__(
            f"Video '{video_path.name}' already exists in Photos library.",
            video_path=video_path,
        )


class ImportFailedError(PhotosImportError):
    """Raised when import fails for an unknown reason.

    Attributes:
        stderr: Error output from AppleScript execution.
    """

    def __init__(
        self,
        message: str,
        video_path: Path | None = None,
        stderr: str | None = None,
    ) -> None:
        """Initialize with error details.

        Args:
            message: Human-readable error message.
            video_path: Path to the video that failed.
            stderr: Error output from AppleScript.
        """
        super().__init__(message, video_path=video_path)
        self.stderr = stderr


class PhotosImporter:
    """Import videos to macOS Photos library via AppleScript.

    This class provides methods to import converted video files
    back into the Photos library, preserving the ability to add
    them to albums and apply metadata.

    SDS Reference: SDS-P01-008

    Example:
        >>> importer = PhotosImporter()
        >>> uuid = importer.import_video(Path("converted.mp4"))
        >>> if importer.verify_import(uuid):
        ...     print("Import verified successfully")

    Attributes:
        DEFAULT_TIMEOUT: Default timeout for import operations (5 minutes).
    """

    DEFAULT_TIMEOUT = 300.0  # 5 minutes

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize PhotosImporter.

        Args:
            timeout: Timeout for import operations in seconds.
                Default is 5 minutes to allow for large videos.
        """
        self._timeout = timeout
        self._script_runner = AppleScriptRunner(timeout=timeout)

        logger.debug(f"PhotosImporter initialized (timeout={timeout}s)")

    @property
    def timeout(self) -> float:
        """Get the timeout value for import operations."""
        return self._timeout

    def import_video(self, video_path: Path) -> str:
        """Import video to Photos library.

        This method activates Photos.app, imports the specified video,
        and returns the UUID of the imported media item.

        Args:
            video_path: Path to the video file to import.

        Returns:
            UUID of the imported video in Photos library.

        Raises:
            FileNotFoundError: If video file doesn't exist.
            PhotosNotRunningError: If Photos.app cannot be activated.
            ImportTimeoutError: If import operation times out.
            DuplicateVideoError: If video already exists in library.
            ImportFailedError: If import fails for other reasons.
        """
        # Validate file exists
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if not video_path.is_file():
            raise FileNotFoundError(f"Path is not a file: {video_path}")

        logger.info(f"Importing video to Photos: {video_path.name}")

        # Build AppleScript for import
        posix_path = escape_applescript_string(str(video_path.resolve()))
        script = self._build_import_script(posix_path)

        try:
            result = self._script_runner.run(script, check=True)
            uuid = result.result

            if not uuid:
                raise ImportFailedError(
                    "Import returned empty UUID",
                    video_path=video_path,
                )

            logger.info(f"Successfully imported video with UUID: {uuid}")
            return uuid

        except AppleScriptTimeoutError as e:
            raise ImportTimeoutError(e.timeout, video_path=video_path) from e

        except AppleScriptExecutionError as e:
            # Parse the error to provide more specific exceptions
            error_msg = e.stderr or str(e)

            if "Photos got an error" in error_msg:
                if "activate" in error_msg.lower():
                    raise PhotosNotRunningError(video_path=video_path) from e
                if "duplicate" in error_msg.lower():
                    raise DuplicateVideoError(video_path) from e

            raise ImportFailedError(
                f"Failed to import video: {error_msg}",
                video_path=video_path,
                stderr=e.stderr,
            ) from e

    def verify_import(self, uuid: str) -> bool:
        """Verify that a video was successfully imported.

        This method checks if a media item with the given UUID
        exists in the Photos library.

        Args:
            uuid: UUID of the imported video to verify.

        Returns:
            True if the video exists in the library, False otherwise.
        """
        logger.debug(f"Verifying import for UUID: {uuid}")

        script = self._build_verify_script(uuid)

        try:
            result = self._script_runner.run(script, timeout=30.0)
            exists = result.result.lower() == "true"

            if exists:
                logger.debug(f"Verified: video {uuid} exists in Photos library")
            else:
                logger.warning(f"Verification failed: video {uuid} not found")

            return exists

        except (AppleScriptTimeoutError, AppleScriptExecutionError) as e:
            logger.warning(f"Verification failed with error: {e}")
            return False

    def get_video_info(self, uuid: str) -> dict[str, str] | None:
        """Get information about an imported video.

        Args:
            uuid: UUID of the video in Photos library.

        Returns:
            Dictionary with video info (filename, date, etc.) or None if not found.
        """
        logger.debug(f"Getting info for video: {uuid}")

        script = self._build_info_script(uuid)

        try:
            result = self._script_runner.run(script, timeout=30.0)

            if not result.success or not result.result:
                return None

            # Parse the result (format: "filename|date|duration")
            parts = result.result.split("|")
            if len(parts) >= 3:
                return {
                    "filename": parts[0],
                    "date": parts[1],
                    "duration": parts[2],
                }
            return None

        except (AppleScriptTimeoutError, AppleScriptExecutionError):
            return None

    def _build_import_script(self, posix_path: str) -> str:
        """Build AppleScript for importing a video.

        Args:
            posix_path: POSIX path to the video file (escaped).

        Returns:
            AppleScript code for import operation.
        """
        return f'''
tell application "Photos"
    activate
    delay 1

    set videoFile to POSIX file "{posix_path}"
    set importedItems to import {{videoFile}} skip check duplicates no

    if (count of importedItems) > 0 then
        set importedPhoto to item 1 of importedItems
        return id of importedPhoto
    else
        error "Import returned no items"
    end if
end tell
'''

    def _build_verify_script(self, uuid: str) -> str:
        """Build AppleScript for verifying import.

        Args:
            uuid: UUID of the video to verify.

        Returns:
            AppleScript code for verification.
        """
        escaped_uuid = escape_applescript_string(uuid)
        return f'''
tell application "Photos"
    try
        set targetItem to media item id "{escaped_uuid}"
        return "true"
    on error
        return "false"
    end try
end tell
'''

    def _build_info_script(self, uuid: str) -> str:
        """Build AppleScript for getting video info.

        Args:
            uuid: UUID of the video.

        Returns:
            AppleScript code for getting info.
        """
        escaped_uuid = escape_applescript_string(uuid)
        return f'''
tell application "Photos"
    try
        set targetItem to media item id "{escaped_uuid}"
        set itemFilename to filename of targetItem
        set itemDate to date of targetItem as string
        set itemDuration to duration of targetItem as string
        return itemFilename & "|" & itemDate & "|" & itemDuration
    on error
        return ""
    end try
end tell
'''
