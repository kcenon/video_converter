"""Unit tests for photos_importer module.

This module provides comprehensive tests for the PhotosImporter class,
including the OriginalHandling enum and handle_original functionality.

SDS Reference: SDS-P01-008
SRS Reference: SRS-305 (Photos Re-Import)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_converter.importers.photos_importer import (
    DuplicateVideoError,
    ImportFailedError,
    ImportTimeoutError,
    OriginalHandling,
    OriginalHandlingError,
    PhotosImportError,
    PhotosImporter,
    PhotosNotRunningError,
)


class TestOriginalHandling:
    """Tests for OriginalHandling enum."""

    def test_delete_value(self) -> None:
        """Test DELETE enum value."""
        assert OriginalHandling.DELETE.value == "delete"

    def test_archive_value(self) -> None:
        """Test ARCHIVE enum value."""
        assert OriginalHandling.ARCHIVE.value == "archive"

    def test_keep_value(self) -> None:
        """Test KEEP enum value."""
        assert OriginalHandling.KEEP.value == "keep"

    def test_all_values_unique(self) -> None:
        """Test that all enum values are unique."""
        values = [h.value for h in OriginalHandling]
        assert len(values) == len(set(values))

    def test_enum_iteration(self) -> None:
        """Test that enum can be iterated."""
        handling_options = list(OriginalHandling)
        assert len(handling_options) == 3
        assert OriginalHandling.DELETE in handling_options
        assert OriginalHandling.ARCHIVE in handling_options
        assert OriginalHandling.KEEP in handling_options


class TestPhotosImportError:
    """Tests for PhotosImportError exception hierarchy."""

    def test_base_error_with_message(self) -> None:
        """Test base error with message."""
        error = PhotosImportError("Test error")
        assert str(error) == "Test error"
        assert error.video_path is None

    def test_base_error_with_video_path(self) -> None:
        """Test base error with video path."""
        path = Path("/test/video.mp4")
        error = PhotosImportError("Test error", video_path=path)
        assert error.video_path == path

    def test_photos_not_running_error(self) -> None:
        """Test PhotosNotRunningError message."""
        error = PhotosNotRunningError()
        assert "Photos.app could not be activated" in str(error)

    def test_import_timeout_error(self) -> None:
        """Test ImportTimeoutError with timeout value."""
        error = ImportTimeoutError(timeout=30.0)
        assert error.timeout == 30.0
        assert "30.0 seconds" in str(error)

    def test_duplicate_video_error(self) -> None:
        """Test DuplicateVideoError with video path."""
        path = Path("/test/video.mp4")
        error = DuplicateVideoError(path)
        assert "video.mp4" in str(error)
        assert "already exists" in str(error)

    def test_import_failed_error_with_stderr(self) -> None:
        """Test ImportFailedError with stderr."""
        error = ImportFailedError(
            message="Import failed",
            video_path=Path("/test/video.mp4"),
            stderr="AppleScript error",
        )
        assert error.stderr == "AppleScript error"


class TestOriginalHandlingError:
    """Tests for OriginalHandlingError exception."""

    def test_error_with_delete_handling(self) -> None:
        """Test error with DELETE handling type."""
        error = OriginalHandlingError(
            message="Delete failed",
            uuid="test-uuid-123",
            handling=OriginalHandling.DELETE,
        )
        assert error.uuid == "test-uuid-123"
        assert error.handling == OriginalHandling.DELETE
        assert "Delete failed" in str(error)

    def test_error_with_archive_handling(self) -> None:
        """Test error with ARCHIVE handling type."""
        error = OriginalHandlingError(
            message="Archive failed",
            uuid="test-uuid-456",
            handling=OriginalHandling.ARCHIVE,
        )
        assert error.uuid == "test-uuid-456"
        assert error.handling == OriginalHandling.ARCHIVE


class TestPhotosImporterInit:
    """Tests for PhotosImporter initialization."""

    def test_default_timeout(self) -> None:
        """Test default timeout value."""
        importer = PhotosImporter()
        assert importer.timeout == 300.0

    def test_custom_timeout(self) -> None:
        """Test custom timeout value."""
        importer = PhotosImporter(timeout=120.0)
        assert importer.timeout == 120.0


class TestPhotosImporterHandleOriginal:
    """Tests for PhotosImporter.handle_original method."""

    @patch.object(PhotosImporter, "_archive_video")
    def test_handle_original_archive(self, mock_archive: MagicMock) -> None:
        """Test handle_original with ARCHIVE handling."""
        importer = PhotosImporter()
        importer.handle_original(
            original_uuid="test-uuid",
            handling=OriginalHandling.ARCHIVE,
            archive_album="Test Album",
        )
        mock_archive.assert_called_once_with("test-uuid", "Test Album")

    @patch.object(PhotosImporter, "_delete_video")
    def test_handle_original_delete(self, mock_delete: MagicMock) -> None:
        """Test handle_original with DELETE handling."""
        importer = PhotosImporter()
        importer.handle_original(
            original_uuid="test-uuid",
            handling=OriginalHandling.DELETE,
        )
        mock_delete.assert_called_once_with("test-uuid")

    @patch.object(PhotosImporter, "_archive_video")
    @patch.object(PhotosImporter, "_delete_video")
    def test_handle_original_keep(
        self, mock_delete: MagicMock, mock_archive: MagicMock
    ) -> None:
        """Test handle_original with KEEP handling (no action)."""
        importer = PhotosImporter()
        importer.handle_original(
            original_uuid="test-uuid",
            handling=OriginalHandling.KEEP,
        )
        mock_delete.assert_not_called()
        mock_archive.assert_not_called()

    @patch.object(PhotosImporter, "_archive_video")
    def test_handle_original_default_album(self, mock_archive: MagicMock) -> None:
        """Test handle_original with default archive album."""
        importer = PhotosImporter()
        importer.handle_original(
            original_uuid="test-uuid",
            handling=OriginalHandling.ARCHIVE,
        )
        mock_archive.assert_called_once_with("test-uuid", "Converted Originals")


class TestPhotosImporterDeleteVideo:
    """Tests for PhotosImporter._delete_video method."""

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_delete_video_success(self, mock_runner_class: MagicMock) -> None:
        """Test successful video deletion."""
        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.result = "true"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()
        importer._delete_video("test-uuid")

        mock_runner.run.assert_called_once()

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_delete_video_failure(self, mock_runner_class: MagicMock) -> None:
        """Test video deletion failure."""
        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.result = "false: Video not found"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()
        with pytest.raises(OriginalHandlingError) as exc_info:
            importer._delete_video("test-uuid")

        assert exc_info.value.handling == OriginalHandling.DELETE


class TestPhotosImporterArchiveVideo:
    """Tests for PhotosImporter._archive_video method."""

    @patch.object(PhotosImporter, "_create_album_if_not_exists")
    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_archive_video_success(
        self, mock_runner_class: MagicMock, mock_create_album: MagicMock
    ) -> None:
        """Test successful video archiving."""
        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.result = "true"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()
        importer._archive_video("test-uuid", "Test Album")

        mock_create_album.assert_called_once_with("Test Album")
        mock_runner.run.assert_called()

    @patch.object(PhotosImporter, "_create_album_if_not_exists")
    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_archive_video_failure(
        self, mock_runner_class: MagicMock, mock_create_album: MagicMock
    ) -> None:
        """Test video archiving failure."""
        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.result = "false: Album error"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()
        with pytest.raises(OriginalHandlingError) as exc_info:
            importer._archive_video("test-uuid", "Test Album")

        assert exc_info.value.handling == OriginalHandling.ARCHIVE


class TestPhotosImporterAppleScripts:
    """Tests for AppleScript building methods."""

    def test_build_delete_script_contains_uuid(self) -> None:
        """Test that delete script contains the UUID."""
        importer = PhotosImporter()
        script = importer._build_delete_script("test-uuid-123")

        assert "test-uuid-123" in script
        assert "delete targetItem" in script
        assert "Photos" in script

    def test_build_add_to_album_script_contains_both(self) -> None:
        """Test that add to album script contains UUID and album name."""
        importer = PhotosImporter()
        script = importer._build_add_to_album_script("test-uuid", "My Album")

        assert "test-uuid" in script
        assert "My Album" in script
        assert "add" in script

    def test_build_create_album_script_contains_album_name(self) -> None:
        """Test that create album script contains album name."""
        importer = PhotosImporter()
        script = importer._build_create_album_script("New Album")

        assert "New Album" in script
        assert "exists album" in script
        assert "make new album" in script


class TestPhotosImporterImportVideo:
    """Tests for PhotosImporter.import_video method."""

    def test_import_video_file_not_found(self) -> None:
        """Test import_video raises FileNotFoundError for missing file."""
        importer = PhotosImporter()
        with pytest.raises(FileNotFoundError):
            importer.import_video(Path("/nonexistent/video.mp4"))

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_import_video_success(
        self, mock_runner_class: MagicMock, tmp_path: Path
    ) -> None:
        """Test successful video import."""
        # Create a test video file
        video_file = tmp_path / "test.mp4"
        video_file.touch()

        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.result = "imported-uuid-123"
        mock_result.success = True
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()
        uuid = importer.import_video(video_file)

        assert uuid == "imported-uuid-123"


class TestPhotosImporterVerifyImport:
    """Tests for PhotosImporter.verify_import method."""

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_verify_import_exists(self, mock_runner_class: MagicMock) -> None:
        """Test verify_import returns True when video exists."""
        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.result = "true"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()
        result = importer.verify_import("test-uuid")

        assert result is True

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_verify_import_not_exists(self, mock_runner_class: MagicMock) -> None:
        """Test verify_import returns False when video doesn't exist."""
        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.result = "false"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()
        result = importer.verify_import("test-uuid")

        assert result is False
