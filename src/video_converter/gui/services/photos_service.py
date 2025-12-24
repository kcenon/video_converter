"""Photos library service for the GUI.

This module provides the PhotosService class that bridges the GUI
with the Photos library, handling asynchronous loading of albums,
videos, and thumbnails.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtGui import QPixmap

if TYPE_CHECKING:
    from video_converter.extractors.photos_extractor import PhotosVideoInfo
    from video_converter.handlers.photos_handler import PhotosSourceHandler


logger = logging.getLogger(__name__)


@dataclass
class AlbumInfo:
    """Information about a Photos album.

    Attributes:
        name: Album name.
        video_count: Number of videos in the album.
        album_id: Unique identifier for the album.
    """

    name: str
    video_count: int
    album_id: str = ""


@dataclass
class VideoDisplayInfo:
    """Video information for GUI display.

    Attributes:
        uuid: Unique identifier from Photos.
        filename: Original filename.
        path: Path to the video file (may be None if iCloud-only).
        duration: Video duration in seconds.
        duration_str: Formatted duration string.
        size: File size in bytes.
        size_str: Formatted size string.
        is_icloud: Whether stored in iCloud.
        is_favorite: Whether marked as favorite.
        codec: Video codec name.
        thumbnail: Loaded thumbnail pixmap.
    """

    uuid: str
    filename: str
    path: Path | None
    duration: float
    duration_str: str
    size: int
    size_str: str
    is_icloud: bool
    is_favorite: bool
    codec: str | None = None
    thumbnail: QPixmap | None = None

    @classmethod
    def from_photos_video_info(cls, video: PhotosVideoInfo) -> VideoDisplayInfo:
        """Create from PhotosVideoInfo.

        Args:
            video: PhotosVideoInfo from extractor.

        Returns:
            VideoDisplayInfo for GUI display.
        """
        # Format duration
        total_seconds = int(video.duration)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            duration_str = f"{minutes}:{seconds:02d}"

        # Format size
        size = video.size
        if size >= 1024 * 1024 * 1024:
            size_str = f"{size / (1024 * 1024 * 1024):.1f} GB"
        elif size >= 1024 * 1024:
            size_str = f"{size / (1024 * 1024):.1f} MB"
        elif size >= 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size} B"

        return cls(
            uuid=video.uuid,
            filename=video.filename,
            path=video.path,
            duration=video.duration,
            duration_str=duration_str,
            size=size,
            size_str=size_str,
            is_icloud=video.in_cloud and not video.is_available_locally,
            is_favorite=video.favorite,
            codec=video.codec,
        )


class PhotosWorker(QObject):
    """Worker for Photos library operations in a separate thread.

    Handles loading albums, videos, and generating thumbnails
    without blocking the GUI.

    Signals:
        permission_checked: Emitted after permission check.
        albums_loaded: Emitted when albums are loaded.
        videos_loaded: Emitted when videos for an album are loaded.
        thumbnail_loaded: Emitted when a thumbnail is generated.
        error_occurred: Emitted when an error occurs.
        stats_loaded: Emitted when library stats are loaded.
    """

    permission_checked = Signal(bool, str)  # has_permission, error_message
    albums_loaded = Signal(list)  # List of AlbumInfo
    videos_loaded = Signal(str, list)  # album_id, List of VideoDisplayInfo
    thumbnail_loaded = Signal(str, object)  # video_uuid, QPixmap
    error_occurred = Signal(str)  # error_message
    stats_loaded = Signal(object)  # LibraryStats

    def __init__(self) -> None:
        """Initialize the Photos worker."""
        super().__init__()
        self._handler: PhotosSourceHandler | None = None
        self._temp_dir = Path(tempfile.mkdtemp(prefix="video_converter_thumbs_"))

    def _get_handler(self) -> PhotosSourceHandler:
        """Get or create PhotosSourceHandler.

        Returns:
            PhotosSourceHandler instance.
        """
        if self._handler is None:
            from video_converter.handlers.photos_handler import PhotosSourceHandler

            self._handler = PhotosSourceHandler()
        return self._handler

    @Slot()
    def check_permission(self) -> None:
        """Check Photos library permission."""
        try:
            handler = self._get_handler()
            has_permission = handler.check_permissions()

            if has_permission:
                self.permission_checked.emit(True, "")
            else:
                error = handler.get_permission_error() or "Access denied"
                self.permission_checked.emit(False, error)

        except Exception as e:
            logger.exception("Permission check failed")
            self.permission_checked.emit(False, str(e))

    @Slot()
    def load_albums(self) -> None:
        """Load album list from Photos library."""
        try:
            handler = self._get_handler()

            if not handler.check_permissions():
                self.error_occurred.emit("Photos library access denied")
                return

            library = handler.library

            # Get all videos first
            all_videos = library.get_videos()

            # Build album list
            albums: list[AlbumInfo] = []

            # Add "All Videos" special album
            albums.append(
                AlbumInfo(
                    name="All Videos",
                    video_count=len(all_videos),
                    album_id="__all__",
                )
            )

            # Count videos per album
            album_counts: dict[str, int] = {}
            for video in all_videos:
                for album_name in video.albums:
                    album_counts[album_name] = album_counts.get(album_name, 0) + 1

            # Add user albums (sorted by name)
            for album_name in sorted(album_counts.keys()):
                albums.append(
                    AlbumInfo(
                        name=album_name,
                        video_count=album_counts[album_name],
                        album_id=album_name,
                    )
                )

            self.albums_loaded.emit(albums)

        except Exception as e:
            logger.exception("Failed to load albums")
            self.error_occurred.emit(f"Failed to load albums: {e}")

    @Slot(str, bool, bool, bool)
    def load_videos(
        self,
        album_id: str,
        include_icloud: bool,
        h264_only: bool,
        favorites_only: bool,
    ) -> None:
        """Load videos for a specific album.

        Args:
            album_id: Album identifier or "__all__" for all videos.
            include_icloud: Whether to include iCloud-only videos.
            h264_only: Whether to filter for H.264 only.
            favorites_only: Whether to show favorites only.
        """
        try:
            handler = self._get_handler()

            if not handler.check_permissions():
                self.error_occurred.emit("Photos library access denied")
                return

            library = handler.library

            # Determine album filter
            albums_filter = None if album_id == "__all__" else [album_id]

            # Get videos
            videos = library.get_videos(
                albums=albums_filter,
                favorites_only=favorites_only,
            )

            # Enrich with codec info and apply filters
            display_videos: list[VideoDisplayInfo] = []

            # Get video filter for codec detection
            from video_converter.extractors.photos_extractor import PhotosVideoFilter

            video_filter = PhotosVideoFilter(library)

            for video in videos:
                # Skip iCloud-only if not requested
                if not include_icloud and video.in_cloud and not video.is_available_locally:
                    continue

                # Enrich with codec info
                enriched = video_filter._enrich_with_codec(video)

                # Apply H.264 filter
                if h264_only and not enriched.is_h264:
                    continue

                display_info = VideoDisplayInfo.from_photos_video_info(enriched)
                display_videos.append(display_info)

            self.videos_loaded.emit(album_id, display_videos)

        except Exception as e:
            logger.exception(f"Failed to load videos for album {album_id}")
            self.error_occurred.emit(f"Failed to load videos: {e}")

    @Slot(str, str)
    def generate_thumbnail(self, video_uuid: str, video_path: str) -> None:
        """Generate thumbnail for a video.

        Args:
            video_uuid: Video UUID.
            video_path: Path to the video file.
        """
        try:
            if not video_path:
                return

            path = Path(video_path)
            if not path.exists():
                return

            # Generate thumbnail using ffmpeg
            thumb_path = self._temp_dir / f"{video_uuid}.jpg"

            if not thumb_path.exists():
                result = subprocess.run(
                    [
                        "ffmpeg",
                        "-i",
                        str(path),
                        "-ss",
                        "00:00:01",
                        "-vframes",
                        "1",
                        "-vf",
                        "scale=240:-1",
                        "-y",
                        str(thumb_path),
                    ],
                    capture_output=True,
                    timeout=10,
                )

                if result.returncode != 0:
                    logger.debug(f"Thumbnail generation failed for {video_uuid}")
                    return

            if thumb_path.exists():
                pixmap = QPixmap(str(thumb_path))
                if not pixmap.isNull():
                    self.thumbnail_loaded.emit(video_uuid, pixmap)

        except subprocess.TimeoutExpired:
            logger.debug(f"Thumbnail generation timed out for {video_uuid}")
        except Exception as e:
            logger.debug(f"Thumbnail generation failed for {video_uuid}: {e}")

    @Slot()
    def load_stats(self) -> None:
        """Load library statistics."""
        try:
            handler = self._get_handler()

            if not handler.check_permissions():
                self.error_occurred.emit("Photos library access denied")
                return

            stats = handler.get_stats()
            self.stats_loaded.emit(stats)

        except Exception as e:
            logger.exception("Failed to load stats")
            self.error_occurred.emit(f"Failed to load stats: {e}")

    def cleanup(self) -> None:
        """Cleanup temporary files."""
        import shutil

        if self._temp_dir.exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)

        if self._handler is not None:
            self._handler.close()
            self._handler = None


class PhotosService(QObject):
    """Service for Photos library operations in the GUI.

    This service provides a thread-safe interface for accessing the
    Photos library from the GUI, with asynchronous operations for
    loading albums, videos, and thumbnails.

    Signals:
        permission_checked: Emitted after permission check.
        albums_loaded: Emitted when albums are loaded.
        videos_loaded: Emitted when videos are loaded.
        thumbnail_loaded: Emitted when a thumbnail is loaded.
        error_occurred: Emitted when an error occurs.
        stats_loaded: Emitted when library stats are loaded.
    """

    permission_checked = Signal(bool, str)
    albums_loaded = Signal(list)
    videos_loaded = Signal(str, list)
    thumbnail_loaded = Signal(str, object)
    error_occurred = Signal(str)
    stats_loaded = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        """Initialize the Photos service.

        Args:
            parent: Parent QObject.
        """
        super().__init__(parent)

        # Create worker thread
        self._worker_thread = QThread()
        self._worker = PhotosWorker()
        self._worker.moveToThread(self._worker_thread)

        # Connect worker signals to service signals
        self._worker.permission_checked.connect(self.permission_checked.emit)
        self._worker.albums_loaded.connect(self.albums_loaded.emit)
        self._worker.videos_loaded.connect(self.videos_loaded.emit)
        self._worker.thumbnail_loaded.connect(self.thumbnail_loaded.emit)
        self._worker.error_occurred.connect(self.error_occurred.emit)
        self._worker.stats_loaded.connect(self.stats_loaded.emit)

        # Start worker thread
        self._worker_thread.start()

        # Cache loaded videos
        self._videos_cache: dict[str, list[VideoDisplayInfo]] = {}
        self._has_permission: bool | None = None

    def check_permission(self) -> None:
        """Request permission check asynchronously."""
        from PySide6.QtCore import QMetaObject, Qt

        QMetaObject.invokeMethod(
            self._worker,
            "check_permission",
            Qt.ConnectionType.QueuedConnection,
        )

    def load_albums(self) -> None:
        """Request albums loading asynchronously."""
        from PySide6.QtCore import QMetaObject, Qt

        QMetaObject.invokeMethod(
            self._worker,
            "load_albums",
            Qt.ConnectionType.QueuedConnection,
        )

    def load_videos(
        self,
        album_id: str,
        include_icloud: bool = True,
        h264_only: bool = True,
        favorites_only: bool = False,
    ) -> None:
        """Request videos loading asynchronously.

        Args:
            album_id: Album identifier.
            include_icloud: Whether to include iCloud videos.
            h264_only: Whether to filter for H.264 only.
            favorites_only: Whether to show favorites only.
        """
        from PySide6.QtCore import Q_ARG, QMetaObject, Qt

        QMetaObject.invokeMethod(
            self._worker,
            "load_videos",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, album_id),
            Q_ARG(bool, include_icloud),
            Q_ARG(bool, h264_only),
            Q_ARG(bool, favorites_only),
        )

    def generate_thumbnail(self, video_uuid: str, video_path: str) -> None:
        """Request thumbnail generation asynchronously.

        Args:
            video_uuid: Video UUID.
            video_path: Path to the video file.
        """
        from PySide6.QtCore import Q_ARG, QMetaObject, Qt

        QMetaObject.invokeMethod(
            self._worker,
            "generate_thumbnail",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, video_uuid),
            Q_ARG(str, video_path),
        )

    def load_stats(self) -> None:
        """Request library stats loading asynchronously."""
        from PySide6.QtCore import QMetaObject, Qt

        QMetaObject.invokeMethod(
            self._worker,
            "load_stats",
            Qt.ConnectionType.QueuedConnection,
        )

    def shutdown(self) -> None:
        """Shutdown the service and cleanup resources."""
        self._worker.cleanup()
        self._worker_thread.quit()
        self._worker_thread.wait()
