"""iCloud video download handling module.

This module provides functionality for detecting and downloading videos
stored in iCloud, including download triggering, progress tracking,
and wait-for-download functionality.

SDS Reference: SDS-P01-007
SRS Reference: SRS-304 (iCloud Download Handling)

Example:
    >>> from video_converter.extractors.icloud_handler import iCloudHandler
    >>> from video_converter.extractors.photos_extractor import PhotosVideoInfo
    >>> handler = iCloudHandler(timeout=1800)
    >>> status = handler.get_status(video)
    >>> if status == CloudStatus.CLOUD_ONLY:
    ...     success = handler.download_and_wait(video)
"""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from video_converter.extractors.photos_extractor import PhotosVideoInfo

logger = logging.getLogger(__name__)


class iCloudError(Exception):
    """Base exception for iCloud operations."""


class iCloudDownloadError(iCloudError):
    """Raised when iCloud download fails.

    This exception indicates that a video file could not be downloaded
    from iCloud, either due to network issues, timeout, or other errors.
    """

    def __init__(
        self,
        filename: str,
        reason: str = "Unknown error",
    ) -> None:
        """Initialize with video filename and failure reason.

        Args:
            filename: Name of the video file that failed to download.
            reason: Description of why the download failed.
        """
        message = f"Failed to download '{filename}' from iCloud: {reason}"
        super().__init__(message)
        self.filename = filename
        self.reason = reason


class iCloudTimeoutError(iCloudError):
    """Raised when iCloud download times out.

    This exception indicates that the download did not complete within
    the specified timeout period.
    """

    def __init__(self, filename: str, timeout: int) -> None:
        """Initialize with video filename and timeout duration.

        Args:
            filename: Name of the video file.
            timeout: Timeout duration in seconds.
        """
        message = f"Download of '{filename}' timed out after {timeout} seconds"
        super().__init__(message)
        self.filename = filename
        self.timeout = timeout


class CloudStatus(Enum):
    """iCloud storage status for a video file.

    Attributes:
        LOCAL: Full file is available locally.
        CLOUD_ONLY: File is stored in iCloud only (stub file locally).
        DOWNLOADING: File is currently being downloaded from iCloud.
        FAILED: Download attempt failed.
        UNKNOWN: Status cannot be determined.
    """

    LOCAL = "local"
    CLOUD_ONLY = "cloud_only"
    DOWNLOADING = "downloading"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class DownloadProgress:
    """Progress information for iCloud download.

    Attributes:
        filename: Name of the file being downloaded.
        status: Current download status.
        progress: Download progress percentage (0-100), -1 if indeterminate.
        bytes_downloaded: Bytes downloaded so far.
        bytes_total: Total file size in bytes.
        elapsed_seconds: Time elapsed since download started.
    """

    filename: str
    status: CloudStatus
    progress: float = -1.0
    bytes_downloaded: int = 0
    bytes_total: int = 0
    elapsed_seconds: float = 0.0

    @property
    def is_complete(self) -> bool:
        """Check if download is complete."""
        return self.status == CloudStatus.LOCAL

    @property
    def is_failed(self) -> bool:
        """Check if download failed."""
        return self.status == CloudStatus.FAILED


class iCloudHandler:
    """Handle iCloud video downloads.

    This class provides functionality to detect, trigger, and monitor
    downloads of videos stored in iCloud. It uses the macOS brctl
    command-line tool to interact with the Bird (iCloud daemon).

    SDS Reference: SDS-P01-007
    SRS Reference: SRS-304 (iCloud Download Handling)

    Example:
        >>> handler = iCloudHandler(timeout=1800)  # 30 min timeout
        >>> for video in candidates:
        ...     status = handler.get_status(video)
        ...     if status == CloudStatus.CLOUD_ONLY:
        ...         print(f"Downloading {video.filename} from iCloud...")
        ...         success = handler.download_and_wait(
        ...             video,
        ...             on_progress=lambda p: print(f"  {p.progress:.1f}%")
        ...         )
        ...         if not success:
        ...             print(f"  Failed to download, skipping")
        ...             continue
        ...     # Proceed with conversion
        ...     convert(video)

    Attributes:
        timeout: Maximum time to wait for download in seconds.
        poll_interval: Time between status checks in seconds.
    """

    # Default timeout: 1 hour for large videos
    DEFAULT_TIMEOUT = 3600

    # Default polling interval: 1 second
    DEFAULT_POLL_INTERVAL = 1.0

    # iCloud stub file prefix
    ICLOUD_STUB_PREFIX = "."
    ICLOUD_STUB_SUFFIX = ".icloud"

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
    ) -> None:
        """Initialize iCloud handler.

        Args:
            timeout: Maximum time to wait for downloads in seconds.
            poll_interval: Time between status checks in seconds.
        """
        self.timeout = timeout
        self.poll_interval = poll_interval

    def get_status(self, video: PhotosVideoInfo) -> CloudStatus:
        """Check iCloud status of a video.

        Determines whether the video file is available locally,
        stored only in iCloud, or currently downloading.

        Args:
            video: Video information from Photos library.

        Returns:
            CloudStatus indicating the current state of the file.
        """
        # If not marked as in cloud, assume local
        if not video.in_cloud:
            return CloudStatus.LOCAL

        # Check for iCloud stub file first
        if video.path is not None:
            stub_path = self._get_stub_path(video.path)
            if stub_path.exists():
                # Stub exists - check if download is in progress
                if self._is_downloading(video.path):
                    return CloudStatus.DOWNLOADING
                return CloudStatus.CLOUD_ONLY

        # If path is available and file exists (no stub), it's local
        if video.path is not None and video.path.exists():
            # Double-check it's not a stub file
            if not self._is_stub_file(video.path):
                return CloudStatus.LOCAL

        # If in_cloud is True but no path, it's cloud only
        if video.in_cloud and video.path is None:
            return CloudStatus.CLOUD_ONLY

        return CloudStatus.UNKNOWN

    def trigger_download(self, video: PhotosVideoInfo) -> bool:
        """Trigger iCloud download for a video.

        Uses the macOS brctl command to request file download from iCloud.
        This is available on macOS 12 (Monterey) and later.

        Args:
            video: Video information with path to download.

        Returns:
            True if download was triggered successfully, False otherwise.
        """
        if video.path is None:
            logger.warning(f"Cannot download video without path: {video.filename}")
            return False

        # Get the target path (use stub path if it exists)
        target_path = video.path
        stub_path = self._get_stub_path(video.path)
        if stub_path.exists():
            target_path = stub_path

        logger.info(f"Triggering iCloud download for: {video.filename}")
        logger.debug(f"Target path: {target_path}")

        try:
            # Use brctl to trigger download
            result = subprocess.run(
                ["brctl", "download", str(target_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                logger.debug(f"Download triggered successfully: {video.filename}")
                return True

            # Log error details
            logger.warning(
                f"brctl download failed for {video.filename}: "
                f"exit code {result.returncode}"
            )
            if result.stderr:
                logger.debug(f"brctl stderr: {result.stderr}")

            return False

        except subprocess.TimeoutExpired:
            logger.warning(f"brctl command timed out for: {video.filename}")
            return False
        except FileNotFoundError:
            logger.error(
                "brctl command not found. "
                "iCloud download requires macOS 12 or later."
            )
            return False
        except subprocess.SubprocessError as e:
            logger.error(f"Failed to run brctl: {e}")
            return False

    def wait_for_download(
        self,
        video: PhotosVideoInfo,
        on_progress: Callable[[DownloadProgress], None] | None = None,
    ) -> bool:
        """Wait for iCloud download to complete.

        Polls the file status until the download completes, fails,
        or the timeout is reached.

        Args:
            video: Video to wait for.
            on_progress: Optional callback for progress updates.

        Returns:
            True if download completed successfully, False otherwise.
        """
        if video.path is None:
            logger.warning(f"Cannot wait for video without path: {video.filename}")
            return False

        start_time = time.time()
        last_status = CloudStatus.UNKNOWN

        logger.debug(f"Waiting for download: {video.filename} (timeout={self.timeout}s)")

        while True:
            elapsed = time.time() - start_time

            # Check timeout
            if elapsed >= self.timeout:
                logger.warning(f"Download timed out: {video.filename}")
                if on_progress:
                    on_progress(
                        DownloadProgress(
                            filename=video.filename,
                            status=CloudStatus.FAILED,
                            elapsed_seconds=elapsed,
                        )
                    )
                return False

            # Check status
            status = self.get_status(video)

            # Report progress if status changed
            if status != last_status:
                logger.debug(f"Status changed: {last_status.value} -> {status.value}")
                last_status = status

            if status == CloudStatus.LOCAL:
                logger.info(f"Download complete: {video.filename}")
                if on_progress:
                    on_progress(
                        DownloadProgress(
                            filename=video.filename,
                            status=CloudStatus.LOCAL,
                            progress=100.0,
                            elapsed_seconds=elapsed,
                        )
                    )
                return True

            if status == CloudStatus.FAILED:
                logger.warning(f"Download failed: {video.filename}")
                if on_progress:
                    on_progress(
                        DownloadProgress(
                            filename=video.filename,
                            status=CloudStatus.FAILED,
                            elapsed_seconds=elapsed,
                        )
                    )
                return False

            # Report intermediate progress
            if on_progress:
                progress = self._get_download_progress(video.path)
                on_progress(
                    DownloadProgress(
                        filename=video.filename,
                        status=status,
                        progress=progress,
                        elapsed_seconds=elapsed,
                    )
                )

            # Wait before next check
            time.sleep(self.poll_interval)

    def download_and_wait(
        self,
        video: PhotosVideoInfo,
        on_progress: Callable[[DownloadProgress], None] | None = None,
    ) -> bool:
        """Trigger download and wait for completion.

        Combined convenience method that triggers a download if needed
        and waits for it to complete.

        Args:
            video: Video to download and wait for.
            on_progress: Optional callback for progress updates.

        Returns:
            True if the video is now available locally, False otherwise.
        """
        status = self.get_status(video)

        # Already local, nothing to do
        if status == CloudStatus.LOCAL:
            logger.debug(f"Video already local: {video.filename}")
            return True

        # Failed status, cannot download
        if status == CloudStatus.FAILED:
            logger.warning(f"Video marked as failed: {video.filename}")
            return False

        # Need to trigger download for cloud-only files
        if status == CloudStatus.CLOUD_ONLY:
            if not self.trigger_download(video):
                logger.warning(f"Failed to trigger download: {video.filename}")
                return False

        # Wait for download to complete
        return self.wait_for_download(video, on_progress)

    def evict(self, video: PhotosVideoInfo) -> bool:
        """Evict a video from local storage (keep in iCloud only).

        Uses the macOS brctl command to remove the local copy while
        keeping the file in iCloud. This frees up local disk space.

        Args:
            video: Video to evict from local storage.

        Returns:
            True if eviction was successful, False otherwise.
        """
        if video.path is None:
            logger.warning(f"Cannot evict video without path: {video.filename}")
            return False

        if not video.path.exists():
            logger.debug(f"Video not present locally: {video.filename}")
            return True

        logger.info(f"Evicting video from local storage: {video.filename}")

        try:
            result = subprocess.run(
                ["brctl", "evict", str(video.path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                logger.debug(f"Eviction successful: {video.filename}")
                return True

            logger.warning(
                f"brctl evict failed for {video.filename}: "
                f"exit code {result.returncode}"
            )
            return False

        except subprocess.TimeoutExpired:
            logger.warning(f"brctl evict timed out: {video.filename}")
            return False
        except FileNotFoundError:
            logger.error("brctl command not found")
            return False
        except subprocess.SubprocessError as e:
            logger.error(f"Failed to run brctl evict: {e}")
            return False

    def _get_stub_path(self, path: Path) -> Path:
        """Get the iCloud stub file path for a video.

        iCloud creates stub files with format: .filename.icloud

        Args:
            path: Original file path.

        Returns:
            Path to the iCloud stub file.
        """
        return path.parent / f"{self.ICLOUD_STUB_PREFIX}{path.name}{self.ICLOUD_STUB_SUFFIX}"

    def _is_stub_file(self, path: Path) -> bool:
        """Check if a path is an iCloud stub file.

        Args:
            path: Path to check.

        Returns:
            True if the path is an iCloud stub file.
        """
        name = path.name
        return (
            name.startswith(self.ICLOUD_STUB_PREFIX)
            and name.endswith(self.ICLOUD_STUB_SUFFIX)
        )

    def _is_downloading(self, path: Path) -> bool:
        """Check if a file is currently downloading.

        Uses brctl monitor-downloads or checks for temporary files
        to determine if a download is in progress.

        Args:
            path: Path to the file.

        Returns:
            True if download is in progress.
        """
        # Check for .downloading file extension (used by some macOS versions)
        downloading_path = Path(str(path) + ".downloading")
        if downloading_path.exists():
            return True

        # Check if stub exists but original file is partially created
        stub_path = self._get_stub_path(path)
        if stub_path.exists() and path.exists():
            # Both exist, likely downloading
            return True

        return False

    def _get_download_progress(self, path: Path) -> float:
        """Get current download progress percentage.

        Attempts to determine download progress by comparing partial
        file size to expected size, or returns -1 if indeterminate.

        Args:
            path: Path to the file being downloaded.

        Returns:
            Progress percentage (0-100), or -1 if indeterminate.
        """
        stub_path = self._get_stub_path(path)

        # If original file exists and stub exists, estimate from size
        if path.exists() and stub_path.exists():
            try:
                current_size = path.stat().st_size
                # We don't know the expected size from stub alone
                # Return indeterminate
                if current_size > 0:
                    # At least we know some progress is made
                    return -1.0
            except OSError:
                pass

        return -1.0


__all__ = [
    "CloudStatus",
    "DownloadProgress",
    "iCloudError",
    "iCloudDownloadError",
    "iCloudHandler",
    "iCloudTimeoutError",
]
