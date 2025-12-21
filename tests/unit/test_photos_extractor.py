"""Unit tests for photos_extractor module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_converter.extractors.photos_extractor import (
    LibraryStats,
    MediaType,
    PhotosAccessDeniedError,
    PhotosLibrary,
    PhotosLibraryNotFoundError,
    PhotosVideoFilter,
    PhotosVideoInfo,
    get_permission_instructions,
)


class TestPhotosVideoInfo:
    """Tests for PhotosVideoInfo dataclass."""

    def test_video_info_creation(self) -> None:
        """Test creating a video info object."""
        video = PhotosVideoInfo(
            uuid="ABC123",
            filename="vacation.mov",
            path=Path("/path/to/video.mov"),
            date=datetime(2024, 1, 15),
            date_modified=datetime(2024, 1, 16),
            duration=120.5,
            favorite=True,
            hidden=False,
            in_cloud=False,
            location=(37.7749, -122.4194),
            albums=["Vacation 2024", "Favorites"],
        )

        assert video.uuid == "ABC123"
        assert video.filename == "vacation.mov"
        assert video.duration == 120.5
        assert video.favorite is True
        assert video.location == (37.7749, -122.4194)
        assert "Vacation 2024" in video.albums

    def test_is_available_locally_with_existing_path(self, tmp_path: Path) -> None:
        """Test is_available_locally with existing file."""
        video_file = tmp_path / "test.mov"
        video_file.touch()

        video = PhotosVideoInfo(
            uuid="ABC123",
            filename="test.mov",
            path=video_file,
            date=None,
            date_modified=None,
            duration=60.0,
        )

        assert video.is_available_locally is True

    def test_is_available_locally_with_nonexistent_path(self) -> None:
        """Test is_available_locally with non-existent file."""
        video = PhotosVideoInfo(
            uuid="ABC123",
            filename="test.mov",
            path=Path("/nonexistent/path.mov"),
            date=None,
            date_modified=None,
            duration=60.0,
        )

        assert video.is_available_locally is False

    def test_is_available_locally_with_none_path(self) -> None:
        """Test is_available_locally when path is None (iCloud only)."""
        video = PhotosVideoInfo(
            uuid="ABC123",
            filename="test.mov",
            path=None,
            date=None,
            date_modified=None,
            duration=60.0,
            in_cloud=True,
        )

        assert video.is_available_locally is False

    def test_default_values(self) -> None:
        """Test default values for optional fields."""
        video = PhotosVideoInfo(
            uuid="ABC123",
            filename="test.mov",
            path=None,
            date=None,
            date_modified=None,
            duration=0.0,
        )

        assert video.favorite is False
        assert video.hidden is False
        assert video.in_cloud is False
        assert video.location is None
        assert video.albums == []


class TestMediaType:
    """Tests for MediaType enum."""

    def test_media_type_values(self) -> None:
        """Test MediaType enum values."""
        assert MediaType.VIDEO.value == "video"
        assert MediaType.PHOTO.value == "photo"
        assert MediaType.ALL.value == "all"


class TestPhotosLibraryExceptions:
    """Tests for Photos library exceptions."""

    def test_photos_access_denied_error_default_message(self) -> None:
        """Test PhotosAccessDeniedError with default message."""
        error = PhotosAccessDeniedError()
        assert "access denied" in str(error).lower()
        assert "Full Disk Access" in str(error)

    def test_photos_access_denied_error_custom_message(self) -> None:
        """Test PhotosAccessDeniedError with custom message."""
        error = PhotosAccessDeniedError("Custom error message")
        assert str(error) == "Custom error message"

    def test_photos_library_not_found_error_with_path(self) -> None:
        """Test PhotosLibraryNotFoundError with path."""
        path = Path("/custom/library.photoslibrary")
        error = PhotosLibraryNotFoundError(path)
        assert "/custom/library.photoslibrary" in str(error)

    def test_photos_library_not_found_error_without_path(self) -> None:
        """Test PhotosLibraryNotFoundError without path."""
        error = PhotosLibraryNotFoundError()
        assert "Default" in str(error)


class TestPhotosLibrary:
    """Tests for PhotosLibrary class."""

    def test_init_with_default_path(self) -> None:
        """Test initialization with default library path."""
        library = PhotosLibrary()
        expected_path = Path.home() / "Pictures" / "Photos Library.photoslibrary"
        assert library.library_path == expected_path

    def test_init_with_custom_path(self, tmp_path: Path) -> None:
        """Test initialization with custom library path."""
        custom_lib = tmp_path / "Custom.photoslibrary"
        custom_lib.mkdir()

        library = PhotosLibrary(library_path=custom_lib)
        assert library.library_path == custom_lib

    def test_init_with_nonexistent_path_raises_error(self) -> None:
        """Test that non-existent path raises PhotosLibraryNotFoundError."""
        with pytest.raises(PhotosLibraryNotFoundError):
            PhotosLibrary(library_path=Path("/nonexistent/path.photoslibrary"))

    @patch("video_converter.extractors.photos_extractor.osxphotos")
    def test_db_property_lazy_loading(self, mock_osxphotos: MagicMock) -> None:
        """Test that db property lazy-loads the database."""
        mock_db = MagicMock()
        mock_osxphotos.PhotosDB.return_value = mock_db

        library = PhotosLibrary()
        # First access should initialize
        _ = library.db
        mock_osxphotos.PhotosDB.assert_called_once()

        # Second access should use cached instance
        _ = library.db
        mock_osxphotos.PhotosDB.assert_called_once()

    @patch("video_converter.extractors.photos_extractor.osxphotos")
    def test_db_property_with_custom_path(self, mock_osxphotos: MagicMock, tmp_path: Path) -> None:
        """Test db property with custom library path."""
        mock_db = MagicMock()
        mock_osxphotos.PhotosDB.return_value = mock_db

        custom_lib = tmp_path / "Custom.photoslibrary"
        custom_lib.mkdir()

        library = PhotosLibrary(library_path=custom_lib)
        _ = library.db

        mock_osxphotos.PhotosDB.assert_called_once_with(dbfile=str(custom_lib))

    @patch("video_converter.extractors.photos_extractor.osxphotos")
    def test_check_permissions_success(self, mock_osxphotos: MagicMock) -> None:
        """Test check_permissions returns True on success."""
        mock_db = MagicMock()
        mock_db.library_path = "/path/to/library"
        mock_osxphotos.PhotosDB.return_value = mock_db

        library = PhotosLibrary()
        assert library.check_permissions() is True

    @patch("video_converter.extractors.photos_extractor.osxphotos")
    def test_check_permissions_denied(self, mock_osxphotos: MagicMock) -> None:
        """Test check_permissions returns False when access denied."""
        mock_osxphotos.PhotosDB.side_effect = PermissionError("Access denied")

        library = PhotosLibrary()
        assert library.check_permissions() is False

    @patch("video_converter.extractors.photos_extractor.osxphotos")
    def test_check_permissions_caches_result(self, mock_osxphotos: MagicMock) -> None:
        """Test that check_permissions caches the result."""
        mock_db = MagicMock()
        mock_db.library_path = "/path/to/library"
        mock_osxphotos.PhotosDB.return_value = mock_db

        library = PhotosLibrary()

        # First check
        result1 = library.check_permissions()
        # Second check should use cached result
        result2 = library.check_permissions()

        assert result1 == result2 is True
        # Should only call PhotosDB once due to caching
        mock_osxphotos.PhotosDB.assert_called_once()

    @patch("video_converter.extractors.photos_extractor.osxphotos")
    def test_get_video_count(self, mock_osxphotos: MagicMock) -> None:
        """Test get_video_count returns correct count."""
        mock_db = MagicMock()
        mock_db.photos.return_value = [MagicMock(), MagicMock(), MagicMock()]
        mock_osxphotos.PhotosDB.return_value = mock_db

        library = PhotosLibrary()
        count = library.get_video_count()

        assert count == 3
        mock_db.photos.assert_called_once_with(media_type=["video"])

    @patch("video_converter.extractors.photos_extractor.osxphotos")
    def test_get_library_info(self, mock_osxphotos: MagicMock) -> None:
        """Test get_library_info returns expected structure."""
        mock_db = MagicMock()
        mock_db.library_path = "/path/to/library"
        mock_db.photos.side_effect = [
            [MagicMock()] * 10,  # photos
            [MagicMock()] * 5,  # videos
        ]
        mock_osxphotos.PhotosDB.return_value = mock_db

        library = PhotosLibrary()
        info = library.get_library_info()

        assert info["path"] == "/path/to/library"
        assert info["photo_count"] == 10
        assert info["video_count"] == 5

    @patch("video_converter.extractors.photos_extractor.osxphotos")
    def test_get_videos_empty_library(self, mock_osxphotos: MagicMock) -> None:
        """Test get_videos with empty library."""
        mock_db = MagicMock()
        mock_db.photos.return_value = []
        mock_osxphotos.PhotosDB.return_value = mock_db

        library = PhotosLibrary()
        videos = library.get_videos()

        assert videos == []

    @patch("video_converter.extractors.photos_extractor.osxphotos")
    def test_get_videos_with_filters(self, mock_osxphotos: MagicMock) -> None:
        """Test get_videos with favorites_only filter."""
        mock_photo1 = MagicMock()
        mock_photo1.uuid = "uuid1"
        mock_photo1.original_filename = "video1.mov"
        mock_photo1.path = "/path/to/video1.mov"
        mock_photo1.date = datetime(2024, 1, 1)
        mock_photo1.date_modified = datetime(2024, 1, 2)
        mock_photo1.duration = 60.0
        mock_photo1.favorite = True
        mock_photo1.hidden = False
        mock_photo1.iscloudasset = False
        mock_photo1.location = (37.0, -122.0)
        mock_photo1.albums = []

        mock_photo2 = MagicMock()
        mock_photo2.uuid = "uuid2"
        mock_photo2.original_filename = "video2.mov"
        mock_photo2.favorite = False
        mock_photo2.hidden = False

        mock_db = MagicMock()
        mock_db.photos.return_value = [mock_photo1, mock_photo2]
        mock_osxphotos.PhotosDB.return_value = mock_db

        library = PhotosLibrary()
        videos = library.get_videos(favorites_only=True)

        assert len(videos) == 1
        assert videos[0].uuid == "uuid1"
        assert videos[0].favorite is True

    @patch("video_converter.extractors.photos_extractor.osxphotos")
    def test_get_videos_excludes_hidden_by_default(self, mock_osxphotos: MagicMock) -> None:
        """Test that hidden videos are excluded by default."""
        mock_visible = MagicMock()
        mock_visible.uuid = "visible"
        mock_visible.original_filename = "visible.mov"
        mock_visible.path = None
        mock_visible.date = None
        mock_visible.date_modified = None
        mock_visible.duration = 30.0
        mock_visible.favorite = False
        mock_visible.hidden = False
        mock_visible.iscloudasset = False
        mock_visible.location = None
        mock_visible.albums = []

        mock_hidden = MagicMock()
        mock_hidden.hidden = True

        mock_db = MagicMock()
        mock_db.photos.return_value = [mock_visible, mock_hidden]
        mock_osxphotos.PhotosDB.return_value = mock_db

        library = PhotosLibrary()
        videos = library.get_videos()

        assert len(videos) == 1
        assert videos[0].uuid == "visible"

    @patch("video_converter.extractors.photos_extractor.osxphotos")
    def test_get_videos_includes_hidden_when_requested(self, mock_osxphotos: MagicMock) -> None:
        """Test that hidden videos are included when requested."""
        mock_hidden = MagicMock()
        mock_hidden.uuid = "hidden"
        mock_hidden.original_filename = "hidden.mov"
        mock_hidden.path = None
        mock_hidden.date = None
        mock_hidden.date_modified = None
        mock_hidden.duration = 30.0
        mock_hidden.favorite = False
        mock_hidden.hidden = True
        mock_hidden.iscloudasset = False
        mock_hidden.location = None
        mock_hidden.albums = []

        mock_db = MagicMock()
        mock_db.photos.return_value = [mock_hidden]
        mock_osxphotos.PhotosDB.return_value = mock_db

        library = PhotosLibrary()
        videos = library.get_videos(include_hidden=True)

        assert len(videos) == 1
        assert videos[0].uuid == "hidden"

    @patch("video_converter.extractors.photos_extractor.osxphotos")
    def test_get_video_by_uuid_found(self, mock_osxphotos: MagicMock) -> None:
        """Test get_video_by_uuid when video exists."""
        mock_photo = MagicMock()
        mock_photo.uuid = "target-uuid"
        mock_photo.original_filename = "found.mov"
        mock_photo.path = None
        mock_photo.date = None
        mock_photo.date_modified = None
        mock_photo.duration = 45.0
        mock_photo.favorite = False
        mock_photo.hidden = False
        mock_photo.iscloudasset = False
        mock_photo.location = None
        mock_photo.albums = []

        mock_db = MagicMock()
        mock_db.photos.return_value = [mock_photo]
        mock_osxphotos.PhotosDB.return_value = mock_db

        library = PhotosLibrary()
        video = library.get_video_by_uuid("target-uuid")

        assert video is not None
        assert video.uuid == "target-uuid"
        mock_db.photos.assert_called_with(uuid=["target-uuid"])

    @patch("video_converter.extractors.photos_extractor.osxphotos")
    def test_get_video_by_uuid_not_found(self, mock_osxphotos: MagicMock) -> None:
        """Test get_video_by_uuid when video doesn't exist."""
        mock_db = MagicMock()
        mock_db.photos.return_value = []
        mock_osxphotos.PhotosDB.return_value = mock_db

        library = PhotosLibrary()
        video = library.get_video_by_uuid("nonexistent-uuid")

        assert video is None

    @patch("video_converter.extractors.photos_extractor.osxphotos")
    def test_close_resets_state(self, mock_osxphotos: MagicMock) -> None:
        """Test that close resets internal state."""
        mock_db = MagicMock()
        mock_db.library_path = "/path"
        mock_osxphotos.PhotosDB.return_value = mock_db

        library = PhotosLibrary()
        _ = library.db  # Initialize
        library.check_permissions()

        library.close()

        # Internal state should be reset
        assert library._db is None
        assert library._initialized is False
        assert library._permission_checked is False

    @patch("video_converter.extractors.photos_extractor.osxphotos")
    def test_context_manager(self, mock_osxphotos: MagicMock) -> None:
        """Test context manager usage."""
        mock_db = MagicMock()
        mock_osxphotos.PhotosDB.return_value = mock_db

        with PhotosLibrary() as library:
            _ = library.db

        # After context exit, library should be closed
        assert library._db is None


class TestGetPermissionInstructions:
    """Tests for get_permission_instructions function."""

    def test_returns_instructions_string(self) -> None:
        """Test that get_permission_instructions returns a string."""
        instructions = get_permission_instructions()
        assert isinstance(instructions, str)
        assert len(instructions) > 0

    def test_contains_key_information(self) -> None:
        """Test that instructions contain key information."""
        instructions = get_permission_instructions()
        assert "System Settings" in instructions
        assert "Full Disk Access" in instructions
        assert "Terminal" in instructions

    def test_contains_quick_access_command(self) -> None:
        """Test that instructions contain quick access command."""
        instructions = get_permission_instructions()
        assert "open" in instructions
        assert "preference.security" in instructions


class TestPhotosVideoInfoCodec:
    """Tests for PhotosVideoInfo codec-related properties."""

    def test_is_h264_with_h264_codec(self, tmp_path: Path) -> None:
        """Test is_h264 returns True for H.264 codec."""
        video_file = tmp_path / "video.mov"
        video_file.touch()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=video_file,
            date=None,
            date_modified=None,
            duration=60.0,
            codec="h264",
        )

        assert video.is_h264 is True
        assert video.is_hevc is False

    def test_is_h264_with_avc_codec(self, tmp_path: Path) -> None:
        """Test is_h264 returns True for AVC codec variant."""
        video_file = tmp_path / "video.mov"
        video_file.touch()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=video_file,
            date=None,
            date_modified=None,
            duration=60.0,
            codec="avc1",
        )

        assert video.is_h264 is True

    def test_is_hevc_with_hevc_codec(self, tmp_path: Path) -> None:
        """Test is_hevc returns True for HEVC codec."""
        video_file = tmp_path / "video.mov"
        video_file.touch()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=video_file,
            date=None,
            date_modified=None,
            duration=60.0,
            codec="hevc",
        )

        assert video.is_hevc is True
        assert video.is_h264 is False

    def test_is_hevc_with_h265_codec(self, tmp_path: Path) -> None:
        """Test is_hevc returns True for H.265 codec variant."""
        video_file = tmp_path / "video.mov"
        video_file.touch()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=video_file,
            date=None,
            date_modified=None,
            duration=60.0,
            codec="h265",
        )

        assert video.is_hevc is True

    def test_codec_none_returns_false(self) -> None:
        """Test is_h264 and is_hevc return False when codec is None."""
        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=None,
            date=None,
            date_modified=None,
            duration=60.0,
            codec=None,
        )

        assert video.is_h264 is False
        assert video.is_hevc is False

    def test_needs_conversion_h264_local(self, tmp_path: Path) -> None:
        """Test needs_conversion returns True for local H.264 video."""
        video_file = tmp_path / "video.mov"
        video_file.touch()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=video_file,
            date=None,
            date_modified=None,
            duration=60.0,
            codec="h264",
        )

        assert video.needs_conversion is True

    def test_needs_conversion_hevc_returns_false(self, tmp_path: Path) -> None:
        """Test needs_conversion returns False for HEVC video."""
        video_file = tmp_path / "video.mov"
        video_file.touch()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=video_file,
            date=None,
            date_modified=None,
            duration=60.0,
            codec="hevc",
        )

        assert video.needs_conversion is False

    def test_needs_conversion_icloud_only_returns_false(self) -> None:
        """Test needs_conversion returns False for iCloud-only video."""
        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=None,
            date=None,
            date_modified=None,
            duration=60.0,
            codec="h264",
            in_cloud=True,
        )

        assert video.needs_conversion is False


class TestLibraryStats:
    """Tests for LibraryStats dataclass."""

    def test_library_stats_creation(self) -> None:
        """Test creating LibraryStats with values."""
        stats = LibraryStats(
            total=100,
            h264=60,
            hevc=30,
            other=5,
            in_cloud=5,
            total_size_h264=10_000_000_000,  # 10 GB
        )

        assert stats.total == 100
        assert stats.h264 == 60
        assert stats.hevc == 30

    def test_estimated_savings(self) -> None:
        """Test estimated_savings calculation."""
        stats = LibraryStats(
            total_size_h264=10_000_000_000,  # 10 GB
        )

        assert stats.estimated_savings == 5_000_000_000  # 5 GB

    def test_estimated_savings_gb(self) -> None:
        """Test estimated_savings_gb calculation."""
        stats = LibraryStats(
            total_size_h264=10 * 1024 * 1024 * 1024,  # 10 GB
        )

        assert stats.estimated_savings_gb == 5.0

    def test_default_values(self) -> None:
        """Test default values for LibraryStats."""
        stats = LibraryStats()

        assert stats.total == 0
        assert stats.h264 == 0
        assert stats.hevc == 0
        assert stats.other == 0
        assert stats.in_cloud == 0
        assert stats.total_size_h264 == 0


class TestPhotosVideoFilter:
    """Tests for PhotosVideoFilter class."""

    def test_init_with_defaults(self) -> None:
        """Test PhotosVideoFilter initialization with defaults."""
        mock_library = MagicMock(spec=PhotosLibrary)

        filter = PhotosVideoFilter(mock_library)

        assert filter._library == mock_library
        assert filter._include_albums is None
        assert "Screenshots" in filter._exclude_albums

    def test_init_with_custom_albums(self) -> None:
        """Test PhotosVideoFilter initialization with custom albums."""
        mock_library = MagicMock(spec=PhotosLibrary)

        filter = PhotosVideoFilter(
            mock_library,
            include_albums=["Vacation", "Family"],
            exclude_albums=["Private"],
        )

        assert filter._include_albums == {"Vacation", "Family"}
        assert filter._exclude_albums == {"Private"}

    def test_init_with_empty_exclude(self) -> None:
        """Test PhotosVideoFilter with empty exclude list."""
        mock_library = MagicMock(spec=PhotosLibrary)

        filter = PhotosVideoFilter(mock_library, exclude_albums=[])

        assert filter._exclude_albums == set()

    def test_passes_album_filter_no_filters(self) -> None:
        """Test album filter passes when no filters set."""
        mock_library = MagicMock(spec=PhotosLibrary)
        filter = PhotosVideoFilter(mock_library, exclude_albums=[])

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=None,
            date=None,
            date_modified=None,
            duration=60.0,
            albums=["Random Album"],
        )

        assert filter._passes_album_filter(video) is True

    def test_passes_album_filter_excluded(self) -> None:
        """Test album filter rejects excluded album."""
        mock_library = MagicMock(spec=PhotosLibrary)
        filter = PhotosVideoFilter(
            mock_library,
            exclude_albums=["Screenshots"],
        )

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=None,
            date=None,
            date_modified=None,
            duration=60.0,
            albums=["Screenshots"],
        )

        assert filter._passes_album_filter(video) is False

    def test_passes_album_filter_included(self) -> None:
        """Test album filter passes for included album."""
        mock_library = MagicMock(spec=PhotosLibrary)
        filter = PhotosVideoFilter(
            mock_library,
            include_albums=["Vacation"],
            exclude_albums=[],
        )

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=None,
            date=None,
            date_modified=None,
            duration=60.0,
            albums=["Vacation", "2024"],
        )

        assert filter._passes_album_filter(video) is True

    def test_passes_album_filter_not_in_include(self) -> None:
        """Test album filter rejects video not in include list."""
        mock_library = MagicMock(spec=PhotosLibrary)
        filter = PhotosVideoFilter(
            mock_library,
            include_albums=["Vacation"],
            exclude_albums=[],
        )

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=None,
            date=None,
            date_modified=None,
            duration=60.0,
            albums=["Work"],
        )

        assert filter._passes_album_filter(video) is False

    def test_get_conversion_candidates_filters_h264(self, tmp_path: Path) -> None:
        """Test get_conversion_candidates returns only H.264 videos."""
        mock_library = MagicMock(spec=PhotosLibrary)

        video_file = tmp_path / "video.mov"
        video_file.write_bytes(b"fake video content")

        h264_video = PhotosVideoInfo(
            uuid="uuid1",
            filename="h264_video.mov",
            path=video_file,
            date=datetime(2024, 1, 1),
            date_modified=None,
            duration=60.0,
        )

        hevc_video = PhotosVideoInfo(
            uuid="uuid2",
            filename="hevc_video.mov",
            path=video_file,
            date=datetime(2024, 1, 1),
            date_modified=None,
            duration=60.0,
        )

        mock_library.get_videos.return_value = [h264_video, hevc_video]

        filter = PhotosVideoFilter(mock_library, exclude_albums=[])

        # Mock codec detector to return h264 for first, hevc for second
        with patch.object(filter, "_detect_codec") as mock_detect:
            mock_detect.side_effect = ["h264", "hevc"]
            candidates = filter.get_conversion_candidates()

        assert len(candidates) == 1
        assert candidates[0].codec == "h264"

    def test_get_conversion_candidates_skips_icloud_only(self) -> None:
        """Test get_conversion_candidates skips iCloud-only videos."""
        mock_library = MagicMock(spec=PhotosLibrary)

        icloud_video = PhotosVideoInfo(
            uuid="uuid1",
            filename="icloud_video.mov",
            path=None,
            date=datetime(2024, 1, 1),
            date_modified=None,
            duration=60.0,
            in_cloud=True,
        )

        mock_library.get_videos.return_value = [icloud_video]

        filter = PhotosVideoFilter(mock_library, exclude_albums=[])

        candidates = filter.get_conversion_candidates()

        assert len(candidates) == 0

    def test_get_conversion_candidates_respects_limit(self, tmp_path: Path) -> None:
        """Test get_conversion_candidates respects limit parameter."""
        mock_library = MagicMock(spec=PhotosLibrary)

        videos = []
        for i in range(5):
            video_file = tmp_path / f"video{i}.mov"
            video_file.write_bytes(b"fake")
            videos.append(
                PhotosVideoInfo(
                    uuid=f"uuid{i}",
                    filename=f"video{i}.mov",
                    path=video_file,
                    date=datetime(2024, 1, 1),
                    date_modified=None,
                    duration=60.0,
                )
            )

        mock_library.get_videos.return_value = videos

        filter = PhotosVideoFilter(mock_library, exclude_albums=[])

        with patch.object(filter, "_detect_codec", return_value="h264"):
            candidates = filter.get_conversion_candidates(limit=2)

        assert len(candidates) == 2

    def test_get_stats(self, tmp_path: Path) -> None:
        """Test get_stats returns correct statistics."""
        mock_library = MagicMock(spec=PhotosLibrary)

        video_file = tmp_path / "video.mov"
        video_file.write_bytes(b"x" * 1000)

        local_h264 = PhotosVideoInfo(
            uuid="uuid1",
            filename="h264.mov",
            path=video_file,
            date=None,
            date_modified=None,
            duration=60.0,
        )

        local_hevc = PhotosVideoInfo(
            uuid="uuid2",
            filename="hevc.mov",
            path=video_file,
            date=None,
            date_modified=None,
            duration=60.0,
        )

        icloud_video = PhotosVideoInfo(
            uuid="uuid3",
            filename="icloud.mov",
            path=None,
            date=None,
            date_modified=None,
            duration=60.0,
            in_cloud=True,
        )

        mock_library.get_videos.return_value = [local_h264, local_hevc, icloud_video]

        filter = PhotosVideoFilter(mock_library, exclude_albums=[])

        with patch.object(filter, "_detect_codec") as mock_detect:
            mock_detect.side_effect = ["h264", "hevc", None]
            stats = filter.get_stats()

        assert stats.total == 3
        assert stats.h264 == 1
        assert stats.hevc == 1
        assert stats.in_cloud == 1
