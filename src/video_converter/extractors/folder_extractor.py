"""Folder-based video extractor module.

This module provides video extraction from filesystem directories,
allowing users to convert videos stored in regular folders instead
of the macOS Photos library.

SDS Reference: SDS-E01-003
SRS Reference: SRS-304 (Folder-based Video Extraction)

Example:
    >>> extractor = FolderExtractor(Path("~/Videos/iPhone"))
    >>> for video in extractor.scan():
    ...     print(f"Found: {video}")
    ...
    >>> candidates = extractor.get_conversion_candidates()
    >>> print(f"Found {len(candidates)} H.264 videos to convert")
"""

from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from video_converter.processors.codec_detector import CodecDetector, CodecInfo

logger = logging.getLogger(__name__)


class FolderExtractorError(Exception):
    """Base exception for folder extractor operations."""


class FolderNotFoundError(FolderExtractorError):
    """Raised when the specified folder does not exist.

    Attributes:
        path: The path that was not found.
    """

    def __init__(self, path: Path) -> None:
        """Initialize with the missing folder path.

        Args:
            path: Path to the folder that was not found.
        """
        self.path = path
        super().__init__(f"Folder not found: {path}")


class FolderAccessDeniedError(FolderExtractorError):
    """Raised when access to a folder is denied.

    Attributes:
        path: The path that could not be accessed.
    """

    def __init__(self, path: Path) -> None:
        """Initialize with the inaccessible folder path.

        Args:
            path: Path to the folder that could not be accessed.
        """
        self.path = path
        super().__init__(f"Access denied to folder: {path}")


class InvalidVideoFileError(FolderExtractorError):
    """Raised when a video file cannot be read or analyzed.

    Attributes:
        path: Path to the invalid video file.
        reason: Description of why the file is invalid.
    """

    def __init__(self, path: Path, reason: str = "Invalid or corrupted video file") -> None:
        """Initialize with the invalid file path and reason.

        Args:
            path: Path to the invalid video file.
            reason: Description of why the file is invalid.
        """
        self.path = path
        self.reason = reason
        super().__init__(f"Invalid video file '{path}': {reason}")


@dataclass
class FolderVideoInfo:
    """Information about a video file in a folder.

    Attributes:
        path: Absolute path to the video file.
        filename: Name of the video file.
        size: File size in bytes.
        modified_time: Last modification time.
        created_time: Creation time (if available).
        codec: Video codec name (e.g., "h264", "hevc").
        duration: Video duration in seconds.
        width: Video width in pixels.
        height: Video height in pixels.
        fps: Frames per second.
        bitrate: Video bitrate in bits per second.
        container: Container format (e.g., "mp4", "mov").
    """

    path: Path
    filename: str
    size: int
    modified_time: datetime
    created_time: datetime | None = None
    codec: str | None = None
    duration: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    bitrate: int = 0
    container: str = ""

    # Codec name variations for identification
    H264_CODECS = frozenset({"h264", "avc", "avc1", "x264"})
    HEVC_CODECS = frozenset({"hevc", "h265", "hvc1", "hev1", "x265"})

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

        A video needs conversion if its codec is H.264.

        Returns:
            True if the video should be converted to H.265.
        """
        return self.is_h264

    @property
    def resolution_label(self) -> str:
        """Get human-readable resolution label.

        Returns:
            Resolution label like "4K", "1080p", "720p", etc.
        """
        if self.height >= 2160:
            return "4K"
        elif self.height >= 1440:
            return "1440p"
        elif self.height >= 1080:
            return "1080p"
        elif self.height >= 720:
            return "720p"
        elif self.height >= 480:
            return "480p"
        elif self.height > 0:
            return f"{self.height}p"
        return "unknown"

    @property
    def size_mb(self) -> float:
        """Get file size in megabytes.

        Returns:
            File size in MB.
        """
        return self.size / (1024 * 1024)

    @property
    def size_gb(self) -> float:
        """Get file size in gigabytes.

        Returns:
            File size in GB.
        """
        return self.size / (1024 * 1024 * 1024)

    def __str__(self) -> str:
        """Return human-readable summary."""
        codec_str = self.codec.upper() if self.codec else "unknown"
        return (
            f"{self.filename}: {codec_str} {self.resolution_label} "
            f"({self.size_mb:.1f} MB)"
        )


@dataclass
class FolderStats:
    """Statistics about videos in a folder.

    Attributes:
        total: Total number of video files.
        h264: Number of H.264 encoded videos.
        hevc: Number of H.265/HEVC encoded videos.
        other: Number of videos with other codecs.
        errors: Number of files that could not be analyzed.
        total_size: Total size of all videos in bytes.
        h264_size: Total size of H.264 videos in bytes.
    """

    total: int = 0
    h264: int = 0
    hevc: int = 0
    other: int = 0
    errors: int = 0
    total_size: int = 0
    h264_size: int = 0

    @property
    def estimated_savings(self) -> int:
        """Estimate storage savings after H.265 conversion.

        Assumes approximately 50% size reduction with H.265.

        Returns:
            Estimated bytes that could be saved.
        """
        return int(self.h264_size * 0.5)

    @property
    def estimated_savings_gb(self) -> float:
        """Get estimated savings in gigabytes.

        Returns:
            Estimated savings in GB.
        """
        return self.estimated_savings / (1024 * 1024 * 1024)

    @property
    def total_size_gb(self) -> float:
        """Get total size in gigabytes.

        Returns:
            Total size in GB.
        """
        return self.total_size / (1024 * 1024 * 1024)


class FolderExtractor:
    """Extract videos from filesystem folders.

    This class provides video extraction from regular filesystem directories,
    with support for recursive scanning, file filtering, and codec detection.

    SDS Reference: SDS-E01-003
    SRS Reference: SRS-304 (Folder-based Video Extraction)

    Example:
        >>> extractor = FolderExtractor(
        ...     root_path=Path("~/Videos/iPhone"),
        ...     recursive=True,
        ...     exclude_patterns=["*.tmp", "._*"]
        ... )
        >>> candidates = extractor.get_conversion_candidates()
        >>> for video in candidates:
        ...     print(f"{video.filename}: {video.codec}")

    Attributes:
        root_path: Root directory for scanning.
        recursive: Whether to scan subdirectories.
        include_patterns: Glob patterns to include.
        exclude_patterns: Glob patterns to exclude.
    """

    # Supported video file extensions
    VIDEO_EXTENSIONS = frozenset({".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm"})

    # Default patterns to exclude (temporary files, macOS resource forks)
    DEFAULT_EXCLUDE_PATTERNS = frozenset({"*.tmp", "._*", ".DS_Store", "*.part"})

    def __init__(
        self,
        root_path: Path | str,
        *,
        recursive: bool = True,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        video_extensions: set[str] | None = None,
    ) -> None:
        """Initialize folder extractor.

        Args:
            root_path: Root directory to scan for videos.
            recursive: Scan subdirectories if True.
            include_patterns: Glob patterns to include (e.g., ["vacation*"]).
                If None, includes all files matching video extensions.
            exclude_patterns: Glob patterns to exclude (e.g., ["*.tmp"]).
                If None, uses DEFAULT_EXCLUDE_PATTERNS.
            video_extensions: Custom set of video file extensions.
                If None, uses VIDEO_EXTENSIONS.

        Raises:
            FolderNotFoundError: If root_path does not exist.
            FolderAccessDeniedError: If root_path is not readable.
        """
        self._root_path = Path(root_path).expanduser().resolve()
        self._recursive = recursive
        self._include_patterns = list(include_patterns) if include_patterns else []
        self._exclude_patterns = (
            set(exclude_patterns)
            if exclude_patterns is not None
            else set(self.DEFAULT_EXCLUDE_PATTERNS)
        )
        self._video_extensions = video_extensions or self.VIDEO_EXTENSIONS
        self._codec_detector: CodecDetector | None = None

        # Validate root path
        if not self._root_path.exists():
            raise FolderNotFoundError(self._root_path)

        if not self._root_path.is_dir():
            raise FolderNotFoundError(self._root_path)

        # Check read access
        try:
            list(self._root_path.iterdir())
        except PermissionError as e:
            raise FolderAccessDeniedError(self._root_path) from e

        logger.info(
            f"FolderExtractor initialized: {self._root_path} "
            f"(recursive={recursive}, extensions={len(self._video_extensions)})"
        )

    @property
    def root_path(self) -> Path:
        """Get the root directory path.

        Returns:
            Path to the root directory.
        """
        return self._root_path

    @property
    def recursive(self) -> bool:
        """Check if recursive scanning is enabled.

        Returns:
            True if scanning subdirectories.
        """
        return self._recursive

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

    def _is_video_file(self, path: Path) -> bool:
        """Check if a path is a video file.

        Args:
            path: Path to check.

        Returns:
            True if the path has a video file extension.
        """
        return path.suffix.lower() in self._video_extensions

    def _passes_filters(self, path: Path) -> bool:
        """Check if a path passes include/exclude filters.

        Args:
            path: Path to check.

        Returns:
            True if the path passes all filters.
        """
        filename = path.name

        # Check exclude patterns first
        for pattern in self._exclude_patterns:
            if fnmatch.fnmatch(filename, pattern):
                logger.debug(f"Excluded by pattern '{pattern}': {filename}")
                return False

        # If no include patterns, include all
        if not self._include_patterns:
            return True

        # Check include patterns
        for pattern in self._include_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True

        logger.debug(f"Not matched by include patterns: {filename}")
        return False

    def scan(self) -> Iterator[Path]:
        """Scan for video files in the root directory.

        Yields video file paths that match the configured filters.

        Yields:
            Path to each video file found.

        Example:
            >>> extractor = FolderExtractor(Path("~/Videos"))
            >>> for video_path in extractor.scan():
            ...     print(video_path)
        """
        logger.info(f"Scanning for videos in: {self._root_path}")

        pattern = "**/*" if self._recursive else "*"

        count = 0
        for path in self._root_path.glob(pattern):
            # Skip directories
            if not path.is_file():
                continue

            # Skip non-video files
            if not self._is_video_file(path):
                continue

            # Apply filters
            if not self._passes_filters(path):
                continue

            count += 1
            yield path

        logger.info(f"Scan complete: found {count} video files")

    def get_video_info(self, path: Path) -> FolderVideoInfo:
        """Get video information for a single file.

        Args:
            path: Path to the video file.

        Returns:
            FolderVideoInfo with file and video properties.

        Raises:
            FileNotFoundError: If the file does not exist.
            InvalidVideoFileError: If the file cannot be analyzed.
        """
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {path}")

        # Get file stats
        try:
            stat = path.stat()
            size = stat.st_size
            modified_time = datetime.fromtimestamp(stat.st_mtime)
            created_time = datetime.fromtimestamp(stat.st_birthtime)
        except (OSError, AttributeError) as e:
            logger.warning(f"Failed to get file stats for {path}: {e}")
            size = 0
            modified_time = datetime.now()
            created_time = None

        # Analyze codec
        codec_info: CodecInfo | None = None
        try:
            from video_converter.processors.codec_detector import (
                CorruptedVideoError,
                InvalidVideoError,
            )

            codec_info = self.codec_detector.analyze(path)
        except (InvalidVideoError, CorruptedVideoError) as e:
            logger.warning(f"Failed to analyze video codec for {path}: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error analyzing {path}: {e}")

        return FolderVideoInfo(
            path=path,
            filename=path.name,
            size=size,
            modified_time=modified_time,
            created_time=created_time,
            codec=codec_info.codec if codec_info else None,
            duration=codec_info.duration if codec_info else 0.0,
            width=codec_info.width if codec_info else 0,
            height=codec_info.height if codec_info else 0,
            fps=codec_info.fps if codec_info else 0.0,
            bitrate=codec_info.bitrate if codec_info else 0,
            container=codec_info.container if codec_info else "",
        )

    def get_videos(self) -> list[FolderVideoInfo]:
        """Get all videos with their information.

        Scans the folder and retrieves detailed information for each video.

        Returns:
            List of FolderVideoInfo for all videos found.

        Example:
            >>> extractor = FolderExtractor(Path("~/Videos"))
            >>> videos = extractor.get_videos()
            >>> for video in videos:
            ...     print(f"{video.filename}: {video.codec}")
        """
        logger.info("Getting video information for all files...")
        videos: list[FolderVideoInfo] = []

        for path in self.scan():
            try:
                video_info = self.get_video_info(path)
                videos.append(video_info)
            except (FileNotFoundError, InvalidVideoFileError) as e:
                logger.warning(f"Skipping {path}: {e}")

        logger.info(f"Retrieved information for {len(videos)} videos")
        return videos

    def get_conversion_candidates(
        self,
        *,
        limit: int | None = None,
    ) -> list[FolderVideoInfo]:
        """Get videos that need conversion from H.264 to H.265.

        This method scans the folder and identifies H.264 videos
        that are candidates for conversion.

        Args:
            limit: Maximum number of candidates to return.

        Returns:
            List of FolderVideoInfo for H.264 videos.

        Example:
            >>> extractor = FolderExtractor(Path("~/Videos"))
            >>> candidates = extractor.get_conversion_candidates(limit=10)
            >>> print(f"Found {len(candidates)} videos to convert")
        """
        logger.info("Searching for H.264 conversion candidates...")
        candidates: list[FolderVideoInfo] = []

        for path in self.scan():
            try:
                video_info = self.get_video_info(path)

                if video_info.needs_conversion:
                    candidates.append(video_info)
                    logger.debug(
                        f"Found candidate: {video_info.filename} "
                        f"({video_info.codec}, {video_info.size_mb:.1f} MB)"
                    )

                    if limit is not None and len(candidates) >= limit:
                        break

            except (FileNotFoundError, InvalidVideoFileError) as e:
                logger.warning(f"Skipping {path}: {e}")

        logger.info(f"Found {len(candidates)} H.264 videos for conversion")
        return candidates

    def get_stats(self) -> FolderStats:
        """Get statistics about videos in the folder.

        Analyzes all videos to provide statistics about codec distribution
        and potential storage savings.

        Returns:
            FolderStats with codec distribution and size information.

        Example:
            >>> extractor = FolderExtractor(Path("~/Videos"))
            >>> stats = extractor.get_stats()
            >>> print(f"Found {stats.h264} H.264 videos")
            >>> print(f"Estimated savings: {stats.estimated_savings_gb:.1f} GB")
        """
        logger.info("Analyzing folder statistics...")
        stats = FolderStats()

        for path in self.scan():
            stats.total += 1

            try:
                stat = path.stat()
                size = stat.st_size
                stats.total_size += size
            except OSError:
                size = 0

            try:
                video_info = self.get_video_info(path)

                if video_info.is_h264:
                    stats.h264 += 1
                    stats.h264_size += size
                elif video_info.is_hevc:
                    stats.hevc += 1
                else:
                    stats.other += 1

            except (FileNotFoundError, InvalidVideoFileError):
                stats.errors += 1
            except Exception as e:
                logger.warning(f"Error analyzing {path}: {e}")
                stats.errors += 1

        logger.info(
            f"Folder stats: {stats.total} total, {stats.h264} H.264, "
            f"{stats.hevc} HEVC, {stats.other} other, {stats.errors} errors"
        )
        return stats

    def get_video_count(self) -> int:
        """Get the total number of video files in the folder.

        Returns:
            Number of video files matching the configured filters.
        """
        return sum(1 for _ in self.scan())

    def __enter__(self) -> FolderExtractor:
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
        # No resources to clean up currently
        pass

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"FolderExtractor(root_path={self._root_path!r}, "
            f"recursive={self._recursive})"
        )
