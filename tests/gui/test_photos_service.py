"""Tests for the Photos service module.

This module tests the PhotosService and related classes.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


class TestAlbumInfo:
    """Tests for AlbumInfo dataclass."""

    def test_album_info_creation(self) -> None:
        """Test creating an AlbumInfo instance."""
        from video_converter.gui.services.photos_service import AlbumInfo

        album = AlbumInfo(name="Test Album", video_count=10, album_id="abc123")
        assert album.name == "Test Album"
        assert album.video_count == 10
        assert album.album_id == "abc123"

    def test_album_info_default_id(self) -> None:
        """Test AlbumInfo with default album_id."""
        from video_converter.gui.services.photos_service import AlbumInfo

        album = AlbumInfo(name="Test Album", video_count=5)
        assert album.album_id == ""


class TestVideoDisplayInfo:
    """Tests for VideoDisplayInfo dataclass."""

    def test_video_display_info_creation(self) -> None:
        """Test creating a VideoDisplayInfo instance."""
        from video_converter.gui.services.photos_service import VideoDisplayInfo

        video = VideoDisplayInfo(
            uuid="test-uuid",
            filename="test.mp4",
            path=Path("/path/to/video.mp4"),
            duration=120.5,
            duration_str="2:00",
            size=1024 * 1024 * 100,
            size_str="100 MB",
            is_icloud=False,
            is_favorite=True,
            codec="h264",
        )
        assert video.uuid == "test-uuid"
        assert video.filename == "test.mp4"
        assert video.is_favorite is True

    def test_video_display_info_optional_fields(self) -> None:
        """Test VideoDisplayInfo with optional fields."""
        from video_converter.gui.services.photos_service import VideoDisplayInfo

        video = VideoDisplayInfo(
            uuid="test-uuid",
            filename="test.mp4",
            path=None,
            duration=60.0,
            duration_str="1:00",
            size=1024,
            size_str="1 KB",
            is_icloud=True,
            is_favorite=False,
        )
        assert video.path is None
        assert video.codec is None
        assert video.thumbnail is None

    def test_from_photos_video_info_short_duration(self) -> None:
        """Test from_photos_video_info with short duration."""
        from video_converter.gui.services.photos_service import VideoDisplayInfo

        mock_video = MagicMock()
        mock_video.uuid = "test-uuid"
        mock_video.filename = "test.mp4"
        mock_video.path = Path("/test/path.mp4")
        mock_video.duration = 65.0  # 1:05
        mock_video.size = 1024 * 1024  # 1 MB
        mock_video.in_cloud = False
        mock_video.is_available_locally = True
        mock_video.favorite = False
        mock_video.codec = "h264"

        video = VideoDisplayInfo.from_photos_video_info(mock_video)
        assert video.duration_str == "1:05"
        assert "MB" in video.size_str

    def test_from_photos_video_info_long_duration(self) -> None:
        """Test from_photos_video_info with hour+ duration."""
        from video_converter.gui.services.photos_service import VideoDisplayInfo

        mock_video = MagicMock()
        mock_video.uuid = "test-uuid"
        mock_video.filename = "test.mp4"
        mock_video.path = Path("/test/path.mp4")
        mock_video.duration = 3725.0  # 1:02:05
        mock_video.size = 1024 * 1024 * 1024 * 2  # 2 GB
        mock_video.in_cloud = False
        mock_video.is_available_locally = True
        mock_video.favorite = True
        mock_video.codec = "hevc"

        video = VideoDisplayInfo.from_photos_video_info(mock_video)
        assert video.duration_str == "1:02:05"
        assert "GB" in video.size_str

    def test_from_photos_video_info_small_size(self) -> None:
        """Test from_photos_video_info with small file."""
        from video_converter.gui.services.photos_service import VideoDisplayInfo

        mock_video = MagicMock()
        mock_video.uuid = "test-uuid"
        mock_video.filename = "test.mp4"
        mock_video.path = Path("/test/path.mp4")
        mock_video.duration = 5.0
        mock_video.size = 500  # 500 bytes
        mock_video.in_cloud = False
        mock_video.is_available_locally = True
        mock_video.favorite = False
        mock_video.codec = "h264"

        video = VideoDisplayInfo.from_photos_video_info(mock_video)
        assert "B" in video.size_str

    def test_from_photos_video_info_kb_size(self) -> None:
        """Test from_photos_video_info with KB size."""
        from video_converter.gui.services.photos_service import VideoDisplayInfo

        mock_video = MagicMock()
        mock_video.uuid = "test-uuid"
        mock_video.filename = "test.mp4"
        mock_video.path = Path("/test/path.mp4")
        mock_video.duration = 5.0
        mock_video.size = 50 * 1024  # 50 KB
        mock_video.in_cloud = False
        mock_video.is_available_locally = True
        mock_video.favorite = False
        mock_video.codec = "h264"

        video = VideoDisplayInfo.from_photos_video_info(mock_video)
        assert "KB" in video.size_str

    def test_from_photos_video_info_icloud(self) -> None:
        """Test from_photos_video_info with iCloud video."""
        from video_converter.gui.services.photos_service import VideoDisplayInfo

        mock_video = MagicMock()
        mock_video.uuid = "test-uuid"
        mock_video.filename = "test.mp4"
        mock_video.path = None
        mock_video.duration = 30.0
        mock_video.size = 1024 * 1024 * 10
        mock_video.in_cloud = True
        mock_video.is_available_locally = False
        mock_video.favorite = False
        mock_video.codec = "h264"

        video = VideoDisplayInfo.from_photos_video_info(mock_video)
        assert video.is_icloud is True


class TestPhotosWorker:
    """Tests for PhotosWorker class."""

    def test_worker_creation(self, qtbot: QtBot) -> None:
        """Test creating a PhotosWorker instance."""
        from video_converter.gui.services.photos_service import PhotosWorker

        worker = PhotosWorker()
        assert worker is not None

    def test_worker_has_signals(self, qtbot: QtBot) -> None:
        """Test that worker has all required signals."""
        from video_converter.gui.services.photos_service import PhotosWorker

        worker = PhotosWorker()
        assert hasattr(worker, "permission_checked")
        assert hasattr(worker, "albums_loaded")
        assert hasattr(worker, "videos_loaded")
        assert hasattr(worker, "thumbnail_loaded")
        assert hasattr(worker, "error_occurred")
        assert hasattr(worker, "stats_loaded")

    def test_worker_cleanup(self, qtbot: QtBot) -> None:
        """Test worker cleanup."""
        from video_converter.gui.services.photos_service import PhotosWorker

        worker = PhotosWorker()
        mock_handler = MagicMock()
        worker._handler = mock_handler
        worker.cleanup()
        # Handler is set to None after close
        mock_handler.close.assert_called_once()
        assert worker._handler is None


class TestPhotosService:
    """Tests for PhotosService class."""

    def test_service_creation(self, qtbot: QtBot) -> None:
        """Test creating a PhotosService instance."""
        from video_converter.gui.services.photos_service import PhotosService

        service = PhotosService()
        assert service is not None
        service.shutdown()

    def test_service_has_signals(self, qtbot: QtBot) -> None:
        """Test that service has all required signals."""
        from video_converter.gui.services.photos_service import PhotosService

        service = PhotosService()

        assert hasattr(service, "permission_checked")
        assert hasattr(service, "albums_loaded")
        assert hasattr(service, "videos_loaded")
        assert hasattr(service, "thumbnail_loaded")
        assert hasattr(service, "error_occurred")
        assert hasattr(service, "stats_loaded")

        service.shutdown()

    def test_service_has_worker_thread(self, qtbot: QtBot) -> None:
        """Test that service creates a worker thread."""
        from video_converter.gui.services.photos_service import PhotosService

        service = PhotosService()

        assert service._worker_thread is not None
        assert service._worker_thread.isRunning()

        service.shutdown()

    def test_service_check_permission_method(self, qtbot: QtBot) -> None:
        """Test check_permission method exists and is callable."""
        from video_converter.gui.services.photos_service import PhotosService

        service = PhotosService()

        # Just verify the method exists and can be called
        service.check_permission()
        service.shutdown()

    def test_service_load_albums_method(self, qtbot: QtBot) -> None:
        """Test load_albums method exists and is callable."""
        from video_converter.gui.services.photos_service import PhotosService

        service = PhotosService()

        service.load_albums()
        service.shutdown()

    def test_service_load_videos_method(self, qtbot: QtBot) -> None:
        """Test load_videos method exists and is callable."""
        from video_converter.gui.services.photos_service import PhotosService

        service = PhotosService()

        service.load_videos("__all__", include_icloud=True, h264_only=True)
        service.shutdown()

    def test_service_generate_thumbnail_method(self, qtbot: QtBot) -> None:
        """Test generate_thumbnail method exists and is callable."""
        from video_converter.gui.services.photos_service import PhotosService

        service = PhotosService()

        service.generate_thumbnail("test-uuid", "/path/to/video.mp4")
        service.shutdown()

    def test_service_load_stats_method(self, qtbot: QtBot) -> None:
        """Test load_stats method exists and is callable."""
        from video_converter.gui.services.photos_service import PhotosService

        service = PhotosService()

        service.load_stats()
        service.shutdown()

    def test_service_shutdown(self, qtbot: QtBot) -> None:
        """Test service shutdown."""
        from video_converter.gui.services.photos_service import PhotosService

        service = PhotosService()

        service.shutdown()
        assert not service._worker_thread.isRunning()
