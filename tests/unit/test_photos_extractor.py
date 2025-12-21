"""Unit tests for photos_extractor module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_converter.extractors.photos_extractor import (
    MediaType,
    PhotosAccessDeniedError,
    PhotosLibrary,
    PhotosLibraryNotFoundError,
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
