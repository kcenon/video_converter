"""Unit tests for photos_handler module.

This module provides comprehensive tests for the PhotosSourceHandler class,
which bridges PhotosLibrary/PhotosVideoFilter implementations with the CLI.

SDS Reference: SDS-P01-007
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_converter.extractors.photos_extractor import (
    LibraryStats,
    PhotosAccessDeniedError,
    PhotosLibraryNotFoundError,
    PhotosVideoInfo,
)
from video_converter.handlers.photos_handler import (
    PhotosConversionOptions,
    PhotosConversionResult,
    PhotosSourceHandler,
)


class TestPhotosConversionOptions:
    """Tests for PhotosConversionOptions dataclass."""

    def test_default_values(self) -> None:
        """Test default values for PhotosConversionOptions."""
        options = PhotosConversionOptions()

        assert options.albums is None
        assert options.exclude_albums is None
        assert options.from_date is None
        assert options.to_date is None
        assert options.favorites_only is False
        assert options.include_hidden is False
        assert options.limit is None
        assert options.dry_run is False

    def test_creation_with_values(self) -> None:
        """Test creating options with specific values."""
        options = PhotosConversionOptions(
            albums=["Vacation", "Family"],
            exclude_albums=["Screenshots"],
            from_date=datetime(2024, 1, 1),
            to_date=datetime(2024, 12, 31),
            favorites_only=True,
            include_hidden=False,
            limit=100,
            dry_run=True,
        )

        assert options.albums == ["Vacation", "Family"]
        assert options.exclude_albums == ["Screenshots"]
        assert options.from_date == datetime(2024, 1, 1)
        assert options.to_date == datetime(2024, 12, 31)
        assert options.favorites_only is True
        assert options.limit == 100
        assert options.dry_run is True


class TestPhotosConversionResult:
    """Tests for PhotosConversionResult dataclass."""

    def test_default_values(self) -> None:
        """Test default values for PhotosConversionResult."""
        result = PhotosConversionResult()

        assert result.total_candidates == 0
        assert result.processed == 0
        assert result.successful == 0
        assert result.failed == 0
        assert result.skipped == 0
        assert result.total_size_before == 0
        assert result.total_size_after == 0
        assert result.errors == []

    def test_size_saved_calculation(self) -> None:
        """Test size_saved property calculation."""
        result = PhotosConversionResult(
            total_size_before=10_000_000,
            total_size_after=5_000_000,
        )

        assert result.size_saved == 5_000_000

    def test_size_saved_never_negative(self) -> None:
        """Test that size_saved is never negative."""
        result = PhotosConversionResult(
            total_size_before=5_000_000,
            total_size_after=10_000_000,
        )

        assert result.size_saved == 0

    def test_savings_percentage_calculation(self) -> None:
        """Test savings_percentage property calculation."""
        result = PhotosConversionResult(
            total_size_before=10_000_000,
            total_size_after=5_000_000,
        )

        assert result.savings_percentage == 50.0

    def test_savings_percentage_zero_before(self) -> None:
        """Test savings_percentage when total_size_before is zero."""
        result = PhotosConversionResult(
            total_size_before=0,
            total_size_after=0,
        )

        assert result.savings_percentage == 0.0


class TestPhotosSourceHandler:
    """Tests for PhotosSourceHandler class."""

    def test_init_with_defaults(self) -> None:
        """Test initialization with default values."""
        handler = PhotosSourceHandler()

        assert handler._library_path is None
        assert handler._temp_dir is None
        assert handler._library is None
        assert handler._exporter is None

    def test_init_with_custom_values(self, tmp_path: Path) -> None:
        """Test initialization with custom library and temp paths."""
        library_path = tmp_path / "Custom.photoslibrary"
        library_path.mkdir()
        temp_dir = tmp_path / "temp"

        handler = PhotosSourceHandler(
            library_path=library_path,
            temp_dir=temp_dir,
        )

        assert handler._library_path == library_path
        assert handler._temp_dir == temp_dir

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    def test_library_property_lazy_loading(
        self,
        mock_photos_library: MagicMock,
    ) -> None:
        """Test that library property lazy-loads the PhotosLibrary."""
        mock_lib_instance = MagicMock()
        mock_photos_library.return_value = mock_lib_instance

        handler = PhotosSourceHandler()

        # First access should create the library
        _ = handler.library
        mock_photos_library.assert_called_once_with(None)

        # Second access should use cached instance
        _ = handler.library
        mock_photos_library.assert_called_once()

    @patch("video_converter.handlers.photos_handler.VideoExporter")
    def test_exporter_property_lazy_loading(
        self,
        mock_video_exporter: MagicMock,
    ) -> None:
        """Test that exporter property lazy-loads the VideoExporter."""
        mock_exporter_instance = MagicMock()
        mock_video_exporter.return_value = mock_exporter_instance

        handler = PhotosSourceHandler()

        # First access should create the exporter
        _ = handler.exporter
        mock_video_exporter.assert_called_once_with(None)

        # Second access should use cached instance
        _ = handler.exporter
        mock_video_exporter.assert_called_once()

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    def test_check_permissions_success(
        self,
        mock_photos_library: MagicMock,
    ) -> None:
        """Test check_permissions returns True on success."""
        mock_lib_instance = MagicMock()
        mock_lib_instance.check_permissions.return_value = True
        mock_photos_library.return_value = mock_lib_instance

        handler = PhotosSourceHandler()
        result = handler.check_permissions()

        assert result is True
        assert handler.get_permission_error() is None

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    def test_check_permissions_denied(
        self,
        mock_photos_library: MagicMock,
    ) -> None:
        """Test check_permissions returns False when access denied."""
        mock_lib_instance = MagicMock()
        mock_lib_instance.check_permissions.return_value = False
        mock_photos_library.return_value = mock_lib_instance

        handler = PhotosSourceHandler()
        result = handler.check_permissions()

        assert result is False
        assert handler.get_permission_error() is not None

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    def test_check_permissions_library_not_found(
        self,
        mock_photos_library: MagicMock,
    ) -> None:
        """Test check_permissions handles PhotosLibraryNotFoundError."""
        mock_photos_library.side_effect = PhotosLibraryNotFoundError()

        handler = PhotosSourceHandler()
        result = handler.check_permissions()

        assert result is False
        assert handler.get_permission_error() is not None

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    def test_check_permissions_access_denied_error(
        self,
        mock_photos_library: MagicMock,
    ) -> None:
        """Test check_permissions handles PhotosAccessDeniedError."""
        mock_photos_library.side_effect = PhotosAccessDeniedError()

        handler = PhotosSourceHandler()
        result = handler.check_permissions()

        assert result is False
        assert "Full Disk Access" in handler.get_permission_error()

    def test_get_permission_instructions(self) -> None:
        """Test get_permission_instructions returns useful string."""
        handler = PhotosSourceHandler()
        instructions = handler.get_permission_instructions()

        assert isinstance(instructions, str)
        assert len(instructions) > 0
        assert "System Settings" in instructions

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    @patch("video_converter.handlers.photos_handler.PhotosVideoFilter")
    def test_get_candidates_basic(
        self,
        mock_filter_class: MagicMock,
        mock_library_class: MagicMock,
    ) -> None:
        """Test get_candidates returns filtered videos."""
        # Setup mock library
        mock_lib_instance = MagicMock()
        mock_library_class.return_value = mock_lib_instance

        # Setup mock filter
        mock_filter_instance = MagicMock()
        mock_filter_instance.get_conversion_candidates.return_value = [
            PhotosVideoInfo(
                uuid="uuid1",
                filename="video1.mov",
                path=Path("/path/to/video1.mov"),
                date=datetime(2024, 1, 1),
                date_modified=None,
                duration=60.0,
                favorite=False,
                hidden=False,
                codec="h264",
            ),
        ]
        mock_filter_class.return_value = mock_filter_instance

        handler = PhotosSourceHandler()
        options = PhotosConversionOptions()
        candidates = handler.get_candidates(options)

        assert len(candidates) == 1
        assert candidates[0].uuid == "uuid1"

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    @patch("video_converter.handlers.photos_handler.PhotosVideoFilter")
    def test_get_candidates_filters_favorites(
        self,
        mock_filter_class: MagicMock,
        mock_library_class: MagicMock,
    ) -> None:
        """Test get_candidates filters by favorites_only option."""
        mock_lib_instance = MagicMock()
        mock_library_class.return_value = mock_lib_instance

        # Two videos: one favorite, one not
        mock_filter_instance = MagicMock()
        mock_filter_instance.get_conversion_candidates.return_value = [
            PhotosVideoInfo(
                uuid="uuid1",
                filename="favorite.mov",
                path=Path("/path/to/favorite.mov"),
                date=None,
                date_modified=None,
                duration=60.0,
                favorite=True,
                hidden=False,
            ),
            PhotosVideoInfo(
                uuid="uuid2",
                filename="normal.mov",
                path=Path("/path/to/normal.mov"),
                date=None,
                date_modified=None,
                duration=60.0,
                favorite=False,
                hidden=False,
            ),
        ]
        mock_filter_class.return_value = mock_filter_instance

        handler = PhotosSourceHandler()
        options = PhotosConversionOptions(favorites_only=True)
        candidates = handler.get_candidates(options)

        assert len(candidates) == 1
        assert candidates[0].uuid == "uuid1"
        assert candidates[0].favorite is True

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    @patch("video_converter.handlers.photos_handler.PhotosVideoFilter")
    def test_get_candidates_excludes_hidden_by_default(
        self,
        mock_filter_class: MagicMock,
        mock_library_class: MagicMock,
    ) -> None:
        """Test get_candidates excludes hidden videos by default."""
        mock_lib_instance = MagicMock()
        mock_library_class.return_value = mock_lib_instance

        mock_filter_instance = MagicMock()
        mock_filter_instance.get_conversion_candidates.return_value = [
            PhotosVideoInfo(
                uuid="uuid1",
                filename="visible.mov",
                path=Path("/path/to/visible.mov"),
                date=None,
                date_modified=None,
                duration=60.0,
                hidden=False,
            ),
            PhotosVideoInfo(
                uuid="uuid2",
                filename="hidden.mov",
                path=Path("/path/to/hidden.mov"),
                date=None,
                date_modified=None,
                duration=60.0,
                hidden=True,
            ),
        ]
        mock_filter_class.return_value = mock_filter_instance

        handler = PhotosSourceHandler()
        options = PhotosConversionOptions(include_hidden=False)
        candidates = handler.get_candidates(options)

        assert len(candidates) == 1
        assert candidates[0].uuid == "uuid1"
        assert candidates[0].hidden is False

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    @patch("video_converter.handlers.photos_handler.PhotosVideoFilter")
    def test_get_candidates_includes_hidden_when_requested(
        self,
        mock_filter_class: MagicMock,
        mock_library_class: MagicMock,
    ) -> None:
        """Test get_candidates includes hidden videos when requested."""
        mock_lib_instance = MagicMock()
        mock_library_class.return_value = mock_lib_instance

        mock_filter_instance = MagicMock()
        mock_filter_instance.get_conversion_candidates.return_value = [
            PhotosVideoInfo(
                uuid="uuid1",
                filename="hidden.mov",
                path=Path("/path/to/hidden.mov"),
                date=None,
                date_modified=None,
                duration=60.0,
                hidden=True,
            ),
        ]
        mock_filter_class.return_value = mock_filter_instance

        handler = PhotosSourceHandler()
        options = PhotosConversionOptions(include_hidden=True)
        candidates = handler.get_candidates(options)

        assert len(candidates) == 1
        assert candidates[0].hidden is True

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    @patch("video_converter.handlers.photos_handler.PhotosVideoFilter")
    def test_get_candidates_respects_limit(
        self,
        mock_filter_class: MagicMock,
        mock_library_class: MagicMock,
    ) -> None:
        """Test get_candidates respects the limit option."""
        mock_lib_instance = MagicMock()
        mock_library_class.return_value = mock_lib_instance

        # Return 5 videos
        mock_filter_instance = MagicMock()
        mock_filter_instance.get_conversion_candidates.return_value = [
            PhotosVideoInfo(
                uuid=f"uuid{i}",
                filename=f"video{i}.mov",
                path=Path(f"/path/to/video{i}.mov"),
                date=None,
                date_modified=None,
                duration=60.0,
            )
            for i in range(5)
        ]
        mock_filter_class.return_value = mock_filter_instance

        handler = PhotosSourceHandler()
        options = PhotosConversionOptions(limit=2)
        candidates = handler.get_candidates(options)

        assert len(candidates) == 2

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    @patch("video_converter.handlers.photos_handler.VideoExporter")
    def test_export_video(
        self,
        mock_exporter_class: MagicMock,
        mock_library_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test export_video exports file to temp directory."""
        mock_lib_instance = MagicMock()
        mock_library_class.return_value = mock_lib_instance

        exported_path = tmp_path / "exported.mov"
        mock_exporter_instance = MagicMock()
        mock_exporter_instance.export.return_value = exported_path
        mock_exporter_class.return_value = mock_exporter_instance

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=Path("/path/to/video.mov"),
            date=None,
            date_modified=None,
            duration=60.0,
        )

        handler = PhotosSourceHandler()
        result = handler.export_video(video)

        assert result == exported_path
        mock_exporter_instance.export.assert_called_once()

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    @patch("video_converter.handlers.photos_handler.VideoExporter")
    def test_export_video_with_progress_callback(
        self,
        mock_exporter_class: MagicMock,
        mock_library_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test export_video calls progress callback."""
        mock_lib_instance = MagicMock()
        mock_library_class.return_value = mock_lib_instance

        exported_path = tmp_path / "exported.mov"
        mock_exporter_instance = MagicMock()
        mock_exporter_instance.export.return_value = exported_path
        mock_exporter_class.return_value = mock_exporter_instance

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=Path("/path/to/video.mov"),
            date=None,
            date_modified=None,
            duration=60.0,
        )

        progress_callback = MagicMock()

        handler = PhotosSourceHandler()
        handler.export_video(video, on_progress=progress_callback)

        # Verify export was called with the callback
        mock_exporter_instance.export.assert_called_once_with(video, progress_callback)

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    @patch("video_converter.handlers.photos_handler.VideoExporter")
    def test_cleanup_exported(
        self,
        mock_exporter_class: MagicMock,
        mock_library_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test cleanup_exported removes exported file."""
        mock_lib_instance = MagicMock()
        mock_library_class.return_value = mock_lib_instance

        mock_exporter_instance = MagicMock()
        mock_exporter_instance.cleanup.return_value = True
        mock_exporter_class.return_value = mock_exporter_instance

        exported_path = tmp_path / "exported.mov"

        handler = PhotosSourceHandler()
        result = handler.cleanup_exported(exported_path)

        assert result is True
        mock_exporter_instance.cleanup.assert_called_once_with(exported_path)

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    @patch("video_converter.handlers.photos_handler.VideoExporter")
    def test_cleanup_all(
        self,
        mock_exporter_class: MagicMock,
        mock_library_class: MagicMock,
    ) -> None:
        """Test cleanup_all removes all exported files."""
        mock_lib_instance = MagicMock()
        mock_library_class.return_value = mock_lib_instance

        mock_exporter_instance = MagicMock()
        mock_exporter_instance.cleanup_all.return_value = 5
        mock_exporter_class.return_value = mock_exporter_instance

        handler = PhotosSourceHandler()
        # Access exporter to initialize it
        _ = handler.exporter

        result = handler.cleanup_all()

        assert result == 5
        mock_exporter_instance.cleanup_all.assert_called_once()

    def test_cleanup_all_without_exporter(self) -> None:
        """Test cleanup_all returns 0 when exporter not initialized."""
        handler = PhotosSourceHandler()
        result = handler.cleanup_all()

        assert result == 0

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    @patch("video_converter.handlers.photos_handler.PhotosVideoFilter")
    def test_get_stats(
        self,
        mock_filter_class: MagicMock,
        mock_library_class: MagicMock,
    ) -> None:
        """Test get_stats returns library statistics."""
        mock_lib_instance = MagicMock()
        mock_library_class.return_value = mock_lib_instance

        expected_stats = LibraryStats(
            total=100,
            h264=60,
            hevc=35,
            other=5,
            in_cloud=10,
            total_size_h264=10_000_000_000,
        )
        mock_filter_instance = MagicMock()
        mock_filter_instance.get_stats.return_value = expected_stats
        mock_filter_class.return_value = mock_filter_instance

        handler = PhotosSourceHandler()
        stats = handler.get_stats()

        assert stats.total == 100
        assert stats.h264 == 60
        assert stats.hevc == 35
        assert stats.total_size_h264 == 10_000_000_000

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    def test_get_library_info(
        self,
        mock_library_class: MagicMock,
    ) -> None:
        """Test get_library_info returns library information."""
        mock_lib_instance = MagicMock()
        mock_lib_instance.get_library_info.return_value = {
            "path": "/Users/test/Pictures/Photos Library.photoslibrary",
            "photo_count": 1000,
            "video_count": 150,
        }
        mock_library_class.return_value = mock_lib_instance

        handler = PhotosSourceHandler()
        info = handler.get_library_info()

        assert "path" in info
        assert info["video_count"] == 150

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    @patch("video_converter.handlers.photos_handler.VideoExporter")
    def test_close_cleans_up_resources(
        self,
        mock_exporter_class: MagicMock,
        mock_library_class: MagicMock,
    ) -> None:
        """Test close method cleans up all resources."""
        mock_lib_instance = MagicMock()
        mock_library_class.return_value = mock_lib_instance

        mock_exporter_instance = MagicMock()
        mock_exporter_class.return_value = mock_exporter_instance

        handler = PhotosSourceHandler()
        # Initialize both
        _ = handler.library
        _ = handler.exporter

        handler.close()

        mock_exporter_instance.cleanup_all.assert_called_once()
        mock_lib_instance.close.assert_called_once()
        assert handler._library is None
        assert handler._exporter is None

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    @patch("video_converter.handlers.photos_handler.VideoExporter")
    def test_context_manager(
        self,
        mock_exporter_class: MagicMock,
        mock_library_class: MagicMock,
    ) -> None:
        """Test context manager usage."""
        mock_lib_instance = MagicMock()
        mock_library_class.return_value = mock_lib_instance

        mock_exporter_instance = MagicMock()
        mock_exporter_class.return_value = mock_exporter_instance

        with PhotosSourceHandler() as handler:
            # Initialize resources
            _ = handler.library
            _ = handler.exporter

        # After context exit, resources should be cleaned up
        mock_exporter_instance.cleanup_all.assert_called_once()
        mock_lib_instance.close.assert_called_once()

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    @patch("video_converter.handlers.photos_handler.PhotosVideoFilter")
    def test_get_candidates_with_album_filters(
        self,
        mock_filter_class: MagicMock,
        mock_library_class: MagicMock,
    ) -> None:
        """Test get_candidates passes album filters correctly."""
        mock_lib_instance = MagicMock()
        mock_library_class.return_value = mock_lib_instance

        mock_filter_instance = MagicMock()
        mock_filter_instance.get_conversion_candidates.return_value = []
        mock_filter_class.return_value = mock_filter_instance

        handler = PhotosSourceHandler()
        options = PhotosConversionOptions(
            albums=["Vacation", "Family"],
            exclude_albums=["Screenshots"],
        )
        handler.get_candidates(options)

        # Verify filter was created with correct album options
        mock_filter_class.assert_called_once()
        call_kwargs = mock_filter_class.call_args[1]
        assert call_kwargs["include_albums"] == ["Vacation", "Family"]
        assert call_kwargs["exclude_albums"] == ["Screenshots"]

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    @patch("video_converter.handlers.photos_handler.PhotosVideoFilter")
    def test_get_candidates_with_date_filters(
        self,
        mock_filter_class: MagicMock,
        mock_library_class: MagicMock,
    ) -> None:
        """Test get_candidates passes date filters correctly."""
        mock_lib_instance = MagicMock()
        mock_library_class.return_value = mock_lib_instance

        mock_filter_instance = MagicMock()
        mock_filter_instance.get_conversion_candidates.return_value = []
        mock_filter_class.return_value = mock_filter_instance

        handler = PhotosSourceHandler()
        from_date = datetime(2024, 1, 1)
        to_date = datetime(2024, 12, 31)
        options = PhotosConversionOptions(
            from_date=from_date,
            to_date=to_date,
        )
        handler.get_candidates(options)

        # Verify filter's get_conversion_candidates was called with dates
        mock_filter_instance.get_conversion_candidates.assert_called_once()
        call_kwargs = mock_filter_instance.get_conversion_candidates.call_args[1]
        assert call_kwargs["from_date"] == from_date
        assert call_kwargs["to_date"] == to_date
