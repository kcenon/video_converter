"""Unit tests for metadata_preservation module.

This module provides comprehensive tests for the MetadataPreserver class,
VideoMetadataSnapshot dataclass, and related metadata preservation functionality.

SDS Reference: SDS-P01-010
SRS Reference: SRS-306 (Metadata Preservation)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_converter.importers.metadata_preservation import (
    MetadataApplicationError,
    MetadataEmbedError,
    MetadataPreservationError,
    MetadataPreserver,
    MetadataTolerance,
    VerificationResult,
    VideoMetadataSnapshot,
)


class TestVideoMetadataSnapshot:
    """Tests for VideoMetadataSnapshot dataclass."""

    def test_creation_with_required_fields(self) -> None:
        """Test creating snapshot with required fields only."""
        snapshot = VideoMetadataSnapshot(
            uuid="test-uuid-123",
            filename="video.mov",
        )

        assert snapshot.uuid == "test-uuid-123"
        assert snapshot.filename == "video.mov"
        assert snapshot.albums == []
        assert snapshot.is_favorite is False
        assert snapshot.is_hidden is False
        assert snapshot.date is None
        assert snapshot.location is None

    def test_creation_with_all_fields(self) -> None:
        """Test creating snapshot with all fields."""
        snapshot = VideoMetadataSnapshot(
            uuid="test-uuid-456",
            filename="vacation.mov",
            albums=["Vacation", "Family"],
            is_favorite=True,
            is_hidden=False,
            date=datetime(2024, 7, 15, 10, 30, 0),
            date_modified=datetime(2024, 7, 16, 12, 0, 0),
            location=(37.7749, -122.4194),
            description="Summer vacation video",
            title="Beach Day",
            keywords=["vacation", "summer", "beach"],
        )

        assert snapshot.uuid == "test-uuid-456"
        assert snapshot.filename == "vacation.mov"
        assert snapshot.albums == ["Vacation", "Family"]
        assert snapshot.is_favorite is True
        assert snapshot.is_hidden is False
        assert snapshot.date == datetime(2024, 7, 15, 10, 30, 0)
        assert snapshot.location == (37.7749, -122.4194)
        assert snapshot.description == "Summer vacation video"
        assert snapshot.keywords == ["vacation", "summer", "beach"]

    def test_has_location_true(self) -> None:
        """Test has_location returns True when location is set."""
        snapshot = VideoMetadataSnapshot(
            uuid="uuid",
            filename="video.mov",
            location=(37.7749, -122.4194),
        )

        assert snapshot.has_location is True

    def test_has_location_false(self) -> None:
        """Test has_location returns False when location is None."""
        snapshot = VideoMetadataSnapshot(
            uuid="uuid",
            filename="video.mov",
        )

        assert snapshot.has_location is False

    def test_has_albums_true(self) -> None:
        """Test has_albums returns True when albums list is not empty."""
        snapshot = VideoMetadataSnapshot(
            uuid="uuid",
            filename="video.mov",
            albums=["Album1"],
        )

        assert snapshot.has_albums is True

    def test_has_albums_false(self) -> None:
        """Test has_albums returns False when albums list is empty."""
        snapshot = VideoMetadataSnapshot(
            uuid="uuid",
            filename="video.mov",
        )

        assert snapshot.has_albums is False


class TestMetadataTolerance:
    """Tests for MetadataTolerance dataclass."""

    def test_default_values(self) -> None:
        """Test default tolerance values."""
        tolerance = MetadataTolerance()

        assert tolerance.date_seconds == 1.0
        assert tolerance.location_degrees == 0.000001

    def test_default_factory(self) -> None:
        """Test default() factory method."""
        tolerance = MetadataTolerance.default()

        assert tolerance.date_seconds == 1.0
        assert tolerance.location_degrees == 0.000001

    def test_strict_factory(self) -> None:
        """Test strict() factory method for exact matching."""
        tolerance = MetadataTolerance.strict()

        assert tolerance.date_seconds == 0.0
        assert tolerance.location_degrees == 0.0

    def test_relaxed_factory(self) -> None:
        """Test relaxed() factory method for Photos app quirks."""
        tolerance = MetadataTolerance.relaxed()

        assert tolerance.date_seconds == 60.0
        assert tolerance.location_degrees == 0.0001


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_successful_result(self) -> None:
        """Test creating a successful verification result."""
        result = VerificationResult(
            success=True,
            albums_matched=True,
            favorite_matched=True,
            date_matched=True,
            location_matched=True,
            details="All metadata verified",
        )

        assert result.success is True
        assert result.albums_matched is True
        assert result.favorite_matched is True
        assert result.date_matched is True
        assert result.location_matched is True

    def test_failed_result_missing_albums(self) -> None:
        """Test creating a failed result with missing albums."""
        result = VerificationResult(
            success=False,
            albums_matched=False,
            missing_albums=["Vacation", "Family"],
            details="Missing albums: ['Vacation', 'Family']",
        )

        assert result.success is False
        assert result.albums_matched is False
        assert result.missing_albums == ["Vacation", "Family"]

    def test_default_values(self) -> None:
        """Test default values for optional fields."""
        result = VerificationResult(success=True)

        assert result.albums_matched is True
        assert result.favorite_matched is True
        assert result.date_matched is True
        assert result.location_matched is True
        assert result.details == ""
        assert result.missing_albums == []


class TestMetadataPreservationErrors:
    """Tests for metadata preservation exception classes."""

    def test_base_error_with_message(self) -> None:
        """Test MetadataPreservationError with message."""
        error = MetadataPreservationError("Test error")
        assert str(error) == "Test error"
        assert error.uuid is None

    def test_base_error_with_uuid(self) -> None:
        """Test MetadataPreservationError with UUID."""
        error = MetadataPreservationError("Test error", uuid="test-uuid")
        assert error.uuid == "test-uuid"

    def test_metadata_embed_error(self) -> None:
        """Test MetadataEmbedError with path and reason."""
        path = Path("/test/video.mp4")
        error = MetadataEmbedError(path, "Failed to write metadata")

        assert error.path == path
        assert error.reason == "Failed to write metadata"
        assert "video.mp4" in str(error)
        assert "Failed to write metadata" in str(error)

    def test_metadata_application_error(self) -> None:
        """Test MetadataApplicationError with UUID and reason."""
        error = MetadataApplicationError("test-uuid", "AppleScript failed")

        assert error.uuid == "test-uuid"
        assert error.reason == "AppleScript failed"
        assert "test-uuid" in str(error)
        assert "AppleScript failed" in str(error)


class TestMetadataPreserverInit:
    """Tests for MetadataPreserver initialization."""

    def test_default_init(self) -> None:
        """Test default initialization."""
        with patch("video_converter.importers.metadata_preservation.MetadataProcessor"):
            with patch(
                "video_converter.importers.metadata_preservation.AppleScriptRunner"
            ):
                preserver = MetadataPreserver()
                assert preserver is not None

    def test_init_with_custom_components(self) -> None:
        """Test initialization with custom components."""
        mock_processor = MagicMock()
        mock_runner = MagicMock()

        preserver = MetadataPreserver(
            metadata_processor=mock_processor,
            script_runner=mock_runner,
        )

        assert preserver._metadata_processor == mock_processor
        assert preserver._script_runner == mock_runner


class TestMetadataPreserverCaptureMetadata:
    """Tests for MetadataPreserver.capture_metadata method."""

    def test_capture_metadata_basic(self) -> None:
        """Test capturing basic metadata from PhotosVideoInfo."""
        mock_video = MagicMock()
        mock_video.uuid = "test-uuid-123"
        mock_video.filename = "test_video.mov"
        mock_video.albums = ["Album1", "Album2"]
        mock_video.favorite = True
        mock_video.hidden = False
        mock_video.date = datetime(2024, 1, 15, 10, 30, 0)
        mock_video.date_modified = datetime(2024, 1, 16, 12, 0, 0)
        mock_video.location = (37.7749, -122.4194)

        with patch("video_converter.importers.metadata_preservation.MetadataProcessor"):
            with patch(
                "video_converter.importers.metadata_preservation.AppleScriptRunner"
            ):
                preserver = MetadataPreserver()
                snapshot = preserver.capture_metadata(mock_video)

        assert snapshot.uuid == "test-uuid-123"
        assert snapshot.filename == "test_video.mov"
        assert snapshot.albums == ["Album1", "Album2"]
        assert snapshot.is_favorite is True
        assert snapshot.is_hidden is False
        assert snapshot.date == datetime(2024, 1, 15, 10, 30, 0)
        assert snapshot.location == (37.7749, -122.4194)

    def test_capture_metadata_minimal(self) -> None:
        """Test capturing metadata with minimal fields."""
        mock_video = MagicMock()
        mock_video.uuid = "minimal-uuid"
        mock_video.filename = "minimal.mov"
        mock_video.albums = []
        mock_video.favorite = False
        mock_video.hidden = False
        mock_video.date = None
        mock_video.date_modified = None
        mock_video.location = None

        with patch("video_converter.importers.metadata_preservation.MetadataProcessor"):
            with patch(
                "video_converter.importers.metadata_preservation.AppleScriptRunner"
            ):
                preserver = MetadataPreserver()
                snapshot = preserver.capture_metadata(mock_video)

        assert snapshot.uuid == "minimal-uuid"
        assert snapshot.albums == []
        assert snapshot.is_favorite is False
        assert snapshot.date is None
        assert snapshot.location is None


class TestMetadataPreserverEmbedMetadata:
    """Tests for MetadataPreserver.embed_metadata_in_file method."""

    def test_embed_metadata_file_not_found(self) -> None:
        """Test embed_metadata_in_file raises FileNotFoundError."""
        snapshot = VideoMetadataSnapshot(
            uuid="uuid",
            filename="video.mov",
        )

        with patch("video_converter.importers.metadata_preservation.MetadataProcessor"):
            with patch(
                "video_converter.importers.metadata_preservation.AppleScriptRunner"
            ):
                preserver = MetadataPreserver()

                with pytest.raises(FileNotFoundError):
                    preserver.embed_metadata_in_file(
                        Path("/nonexistent/video.mp4"),
                        snapshot,
                    )

    def test_embed_metadata_with_date(self, tmp_path: Path) -> None:
        """Test embedding date metadata in file."""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        snapshot = VideoMetadataSnapshot(
            uuid="uuid",
            filename="video.mov",
            date=datetime(2024, 7, 15, 10, 30, 0),
        )

        mock_processor = MagicMock()
        mock_processor.set_tag.return_value = True

        with patch(
            "video_converter.importers.metadata_preservation.AppleScriptRunner"
        ):
            preserver = MetadataPreserver(metadata_processor=mock_processor)
            result = preserver.embed_metadata_in_file(video_file, snapshot)

        assert result is True
        # Should set multiple date tags
        assert mock_processor.set_tag.call_count >= 6

    def test_embed_metadata_with_location(self, tmp_path: Path) -> None:
        """Test embedding GPS location in file."""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        snapshot = VideoMetadataSnapshot(
            uuid="uuid",
            filename="video.mov",
            location=(37.7749, -122.4194),
        )

        mock_processor = MagicMock()
        mock_processor.set_tag.return_value = True

        with patch(
            "video_converter.importers.metadata_preservation.AppleScriptRunner"
        ):
            preserver = MetadataPreserver(metadata_processor=mock_processor)
            result = preserver.embed_metadata_in_file(video_file, snapshot)

        assert result is True
        # Should set GPS tags
        assert mock_processor.set_tag.call_count >= 5

    def test_embed_metadata_with_description(self, tmp_path: Path) -> None:
        """Test embedding description metadata in file."""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        snapshot = VideoMetadataSnapshot(
            uuid="uuid",
            filename="video.mov",
            description="Test description",
        )

        mock_processor = MagicMock()
        mock_processor.set_tag.return_value = True

        with patch(
            "video_converter.importers.metadata_preservation.AppleScriptRunner"
        ):
            preserver = MetadataPreserver(metadata_processor=mock_processor)
            result = preserver.embed_metadata_in_file(video_file, snapshot)

        assert result is True
        # Verify description tag was set
        mock_processor.set_tag.assert_called_with(
            video_file,
            "Description",
            "Test description",
            overwrite_original=True,
        )

    def test_embed_metadata_with_keywords(self, tmp_path: Path) -> None:
        """Test embedding keywords metadata in file."""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        snapshot = VideoMetadataSnapshot(
            uuid="uuid",
            filename="video.mov",
            keywords=["vacation", "summer", "beach"],
        )

        mock_processor = MagicMock()
        mock_processor.set_tag.return_value = True

        with patch(
            "video_converter.importers.metadata_preservation.AppleScriptRunner"
        ):
            preserver = MetadataPreserver(metadata_processor=mock_processor)
            result = preserver.embed_metadata_in_file(video_file, snapshot)

        assert result is True
        mock_processor.set_tag.assert_called_with(
            video_file,
            "Keywords",
            "vacation, summer, beach",
            overwrite_original=True,
        )

    def test_embed_metadata_partial_failure(self, tmp_path: Path) -> None:
        """Test embed_metadata_in_file returns False on partial failure."""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        snapshot = VideoMetadataSnapshot(
            uuid="uuid",
            filename="video.mov",
            date=datetime(2024, 7, 15, 10, 30, 0),
        )

        mock_processor = MagicMock()
        mock_processor.set_tag.return_value = False  # Simulate failure

        with patch(
            "video_converter.importers.metadata_preservation.AppleScriptRunner"
        ):
            preserver = MetadataPreserver(metadata_processor=mock_processor)
            result = preserver.embed_metadata_in_file(video_file, snapshot)

        assert result is False


class TestMetadataPreserverApplyPhotosMetadata:
    """Tests for MetadataPreserver.apply_photos_metadata method."""

    def test_apply_photos_metadata_favorite(self) -> None:
        """Test applying favorite status via AppleScript."""
        snapshot = VideoMetadataSnapshot(
            uuid="uuid",
            filename="video.mov",
            is_favorite=True,
        )

        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_runner.run.return_value = mock_result

        with patch("video_converter.importers.metadata_preservation.MetadataProcessor"):
            preserver = MetadataPreserver(script_runner=mock_runner)
            result = preserver.apply_photos_metadata("new-uuid", snapshot)

        assert result is True
        mock_runner.run.assert_called()

    def test_apply_photos_metadata_albums(self) -> None:
        """Test adding video to multiple albums."""
        snapshot = VideoMetadataSnapshot(
            uuid="uuid",
            filename="video.mov",
            albums=["Vacation", "Family"],
        )

        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_runner.run.return_value = mock_result

        with patch("video_converter.importers.metadata_preservation.MetadataProcessor"):
            preserver = MetadataPreserver(script_runner=mock_runner)
            result = preserver.apply_photos_metadata("new-uuid", snapshot)

        assert result is True
        # Should be called for each album
        assert mock_runner.run.call_count >= 2

    def test_apply_photos_metadata_hidden(self) -> None:
        """Test applying hidden status via AppleScript."""
        snapshot = VideoMetadataSnapshot(
            uuid="uuid",
            filename="video.mov",
            is_hidden=True,
        )

        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_runner.run.return_value = mock_result

        with patch("video_converter.importers.metadata_preservation.MetadataProcessor"):
            preserver = MetadataPreserver(script_runner=mock_runner)
            result = preserver.apply_photos_metadata("new-uuid", snapshot)

        assert result is True

    def test_apply_photos_metadata_failure(self) -> None:
        """Test apply_photos_metadata returns False on failure."""
        from video_converter.utils.applescript import AppleScriptExecutionError

        snapshot = VideoMetadataSnapshot(
            uuid="uuid",
            filename="video.mov",
            is_favorite=True,
        )

        mock_runner = MagicMock()
        mock_runner.run.side_effect = AppleScriptExecutionError(
            "Failed", stderr="AppleScript error"
        )

        with patch("video_converter.importers.metadata_preservation.MetadataProcessor"):
            preserver = MetadataPreserver(script_runner=mock_runner)
            result = preserver.apply_photos_metadata("new-uuid", snapshot)

        assert result is False


class TestMetadataPreserverVerifyMetadata:
    """Tests for MetadataPreserver.verify_metadata method."""

    def test_verify_metadata_success(self) -> None:
        """Test successful metadata verification."""
        expected = VideoMetadataSnapshot(
            uuid="original-uuid",
            filename="video.mov",
            albums=["Vacation"],
            is_favorite=True,
            date=datetime(2024, 7, 15, 10, 30, 0),
        )

        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.result = "true|||2024-07-15T10:30:00|||Vacation"
        mock_runner.run.return_value = mock_result

        with patch("video_converter.importers.metadata_preservation.MetadataProcessor"):
            preserver = MetadataPreserver(script_runner=mock_runner)
            result = preserver.verify_metadata("new-uuid", expected)

        assert result.success is True
        assert result.albums_matched is True
        assert result.favorite_matched is True
        assert result.date_matched is True

    def test_verify_metadata_missing_albums(self) -> None:
        """Test verification fails when albums are missing."""
        expected = VideoMetadataSnapshot(
            uuid="original-uuid",
            filename="video.mov",
            albums=["Vacation", "Family"],
            is_favorite=False,
        )

        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        # Only one album matched
        mock_result.result = "false|||2024-07-15T10:30:00|||Vacation"
        mock_runner.run.return_value = mock_result

        with patch("video_converter.importers.metadata_preservation.MetadataProcessor"):
            preserver = MetadataPreserver(script_runner=mock_runner)
            result = preserver.verify_metadata("new-uuid", expected)

        assert result.albums_matched is False
        assert "Family" in result.missing_albums

    def test_verify_metadata_wrong_date(self) -> None:
        """Test verification fails when date is wrong."""
        expected = VideoMetadataSnapshot(
            uuid="original-uuid",
            filename="video.mov",
            date=datetime(2024, 7, 15, 10, 30, 0),
        )

        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        # Different date
        mock_result.result = "false|||2024-07-16T10:30:00|||"
        mock_runner.run.return_value = mock_result

        tolerance = MetadataTolerance.strict()

        with patch("video_converter.importers.metadata_preservation.MetadataProcessor"):
            preserver = MetadataPreserver(script_runner=mock_runner)
            result = preserver.verify_metadata("new-uuid", expected, tolerance)

        assert result.date_matched is False

    def test_verify_metadata_with_tolerance(self) -> None:
        """Test verification with relaxed tolerance."""
        expected = VideoMetadataSnapshot(
            uuid="original-uuid",
            filename="video.mov",
            date=datetime(2024, 7, 15, 10, 30, 0),
        )

        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        # Date is 30 seconds off
        mock_result.result = "false|||2024-07-15T10:30:30|||"
        mock_runner.run.return_value = mock_result

        # Relaxed tolerance allows 60 seconds difference
        tolerance = MetadataTolerance.relaxed()

        with patch("video_converter.importers.metadata_preservation.MetadataProcessor"):
            preserver = MetadataPreserver(script_runner=mock_runner)
            result = preserver.verify_metadata("new-uuid", expected, tolerance)

        assert result.date_matched is True

    def test_verify_metadata_retrieval_failure(self) -> None:
        """Test verification when metadata retrieval fails."""
        expected = VideoMetadataSnapshot(
            uuid="original-uuid",
            filename="video.mov",
        )

        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.result = "ERROR:Could not find media item"
        mock_runner.run.return_value = mock_result

        with patch("video_converter.importers.metadata_preservation.MetadataProcessor"):
            preserver = MetadataPreserver(script_runner=mock_runner)
            result = preserver.verify_metadata("new-uuid", expected)

        assert result.success is False
        assert "Could not retrieve metadata" in result.details


class TestMetadataPreserverInternalMethods:
    """Tests for internal MetadataPreserver methods."""

    def test_set_favorite_success(self) -> None:
        """Test _set_favorite successfully sets favorite status."""
        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_runner.run.return_value = mock_result

        with patch("video_converter.importers.metadata_preservation.MetadataProcessor"):
            preserver = MetadataPreserver(script_runner=mock_runner)
            preserver._set_favorite("test-uuid", favorite=True)

        mock_runner.run.assert_called_once()
        call_args = mock_runner.run.call_args[0][0]
        assert "test-uuid" in call_args
        assert "true" in call_args

    def test_add_to_album_success(self) -> None:
        """Test _add_to_album successfully adds to album."""
        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_runner.run.return_value = mock_result

        with patch("video_converter.importers.metadata_preservation.MetadataProcessor"):
            preserver = MetadataPreserver(script_runner=mock_runner)
            preserver._add_to_album("test-uuid", "My Album")

        mock_runner.run.assert_called_once()
        call_args = mock_runner.run.call_args[0][0]
        assert "test-uuid" in call_args
        assert "My Album" in call_args

    def test_add_to_album_failure(self) -> None:
        """Test _add_to_album raises MetadataApplicationError on failure."""
        from video_converter.utils.applescript import AppleScriptExecutionError

        mock_runner = MagicMock()
        mock_runner.run.side_effect = AppleScriptExecutionError(
            "Album not found", stderr="Album not found error"
        )

        with patch("video_converter.importers.metadata_preservation.MetadataProcessor"):
            preserver = MetadataPreserver(script_runner=mock_runner)

            with pytest.raises(MetadataApplicationError) as exc_info:
                preserver._add_to_album("test-uuid", "NonexistentAlbum")

            assert "NonexistentAlbum" in str(exc_info.value)
