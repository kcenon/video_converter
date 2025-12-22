"""Unit tests for original video handling functionality.

This module provides comprehensive tests for handling original videos
after successful re-import, including delete, archive, and keep options,
as well as rollback scenarios.

SDS Reference: SDS-P01-008
SRS Reference: SRS-305 (Photos Re-Import)
"""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from video_converter.importers.photos_importer import (
    OriginalHandling,
    OriginalHandlingError,
    PhotosImporter,
)
from video_converter.utils.applescript import (
    AppleScriptExecutionError,
    AppleScriptTimeoutError,
)


class TestOriginalHandlingDeleteOption:
    """Tests for DELETE handling option."""

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_delete_executes_applescript(self, mock_runner_class: MagicMock) -> None:
        """Test that delete option executes AppleScript with correct UUID."""
        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.result = "true"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()
        importer.handle_original(
            original_uuid="test-uuid-to-delete",
            handling=OriginalHandling.DELETE,
        )

        mock_runner.run.assert_called()
        call_args = mock_runner.run.call_args[0][0]
        assert "test-uuid-to-delete" in call_args
        assert "delete" in call_args.lower()

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_delete_raises_on_video_not_found(
        self, mock_runner_class: MagicMock
    ) -> None:
        """Test that delete raises OriginalHandlingError when video not found."""
        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.result = "false: Video not found in library"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()

        with pytest.raises(OriginalHandlingError) as exc_info:
            importer.handle_original(
                original_uuid="nonexistent-uuid",
                handling=OriginalHandling.DELETE,
            )

        assert exc_info.value.handling == OriginalHandling.DELETE
        assert exc_info.value.uuid == "nonexistent-uuid"

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_delete_raises_on_timeout(self, mock_runner_class: MagicMock) -> None:
        """Test that delete raises OriginalHandlingError on timeout."""
        mock_runner = MagicMock()
        mock_runner.run.side_effect = AppleScriptTimeoutError(timeout=300.0)
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()

        with pytest.raises(OriginalHandlingError) as exc_info:
            importer.handle_original(
                original_uuid="test-uuid",
                handling=OriginalHandling.DELETE,
            )

        assert exc_info.value.handling == OriginalHandling.DELETE
        assert "timed out" in str(exc_info.value).lower()

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_delete_raises_on_execution_error(
        self, mock_runner_class: MagicMock
    ) -> None:
        """Test that delete raises OriginalHandlingError on AppleScript failure."""
        mock_runner = MagicMock()
        mock_runner.run.side_effect = AppleScriptExecutionError(
            "Photos got an error: can't delete",
            stderr="System permission denied",
        )
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()

        with pytest.raises(OriginalHandlingError) as exc_info:
            importer.handle_original(
                original_uuid="test-uuid",
                handling=OriginalHandling.DELETE,
            )

        assert exc_info.value.handling == OriginalHandling.DELETE


class TestOriginalHandlingArchiveOption:
    """Tests for ARCHIVE handling option."""

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_archive_creates_album_and_adds_video(
        self, mock_runner_class: MagicMock
    ) -> None:
        """Test that archive creates album and adds video to it."""
        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.result = "true"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()
        importer.handle_original(
            original_uuid="test-uuid-to-archive",
            handling=OriginalHandling.ARCHIVE,
            archive_album="My Archive Album",
        )

        # Should be called twice: once for album creation, once for adding
        assert mock_runner.run.call_count == 2

        # First call should create album
        first_call_script = mock_runner.run.call_args_list[0][0][0]
        assert "My Archive Album" in first_call_script
        assert "make new album" in first_call_script.lower()

        # Second call should add to album
        second_call_script = mock_runner.run.call_args_list[1][0][0]
        assert "test-uuid-to-archive" in second_call_script
        assert "add" in second_call_script.lower()

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_archive_uses_default_album_name(
        self, mock_runner_class: MagicMock
    ) -> None:
        """Test that archive uses default album name when not specified."""
        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.result = "true"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()
        importer.handle_original(
            original_uuid="test-uuid",
            handling=OriginalHandling.ARCHIVE,
        )

        # Check that "Converted Originals" is in the script
        first_call_script = mock_runner.run.call_args_list[0][0][0]
        assert "Converted Originals" in first_call_script

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_archive_with_special_characters_in_album_name(
        self, mock_runner_class: MagicMock
    ) -> None:
        """Test archive handles special characters in album name."""
        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.result = "true"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()
        importer.handle_original(
            original_uuid="test-uuid",
            handling=OriginalHandling.ARCHIVE,
            archive_album='Album "With" Quotes',
        )

        mock_runner.run.assert_called()

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_archive_raises_on_album_creation_failure(
        self, mock_runner_class: MagicMock
    ) -> None:
        """Test that archive raises OriginalHandlingError on album creation failure."""
        mock_runner = MagicMock()
        mock_runner.run.side_effect = AppleScriptExecutionError(
            "Failed to create album",
            stderr="Album creation failed",
        )
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()

        with pytest.raises(OriginalHandlingError) as exc_info:
            importer.handle_original(
                original_uuid="test-uuid",
                handling=OriginalHandling.ARCHIVE,
            )

        assert exc_info.value.handling == OriginalHandling.ARCHIVE

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_archive_raises_on_add_to_album_failure(
        self, mock_runner_class: MagicMock
    ) -> None:
        """Test archive raises OriginalHandlingError when adding to album fails."""
        mock_runner = MagicMock()

        # First call succeeds (album creation), second fails (add to album)
        mock_success = MagicMock()
        mock_success.result = "true"

        mock_failure = MagicMock()
        mock_failure.result = "false: Could not add item to album"

        mock_runner.run.side_effect = [mock_success, mock_failure]
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()

        with pytest.raises(OriginalHandlingError) as exc_info:
            importer.handle_original(
                original_uuid="test-uuid",
                handling=OriginalHandling.ARCHIVE,
            )

        assert exc_info.value.handling == OriginalHandling.ARCHIVE


class TestOriginalHandlingKeepOption:
    """Tests for KEEP handling option."""

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_keep_does_nothing(self, mock_runner_class: MagicMock) -> None:
        """Test that KEEP option does not execute any AppleScript."""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()
        importer.handle_original(
            original_uuid="test-uuid",
            handling=OriginalHandling.KEEP,
        )

        # Should not call run since KEEP does nothing
        mock_runner.run.assert_not_called()

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_keep_ignores_archive_album_parameter(
        self, mock_runner_class: MagicMock
    ) -> None:
        """Test that KEEP option ignores archive_album parameter."""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()
        importer.handle_original(
            original_uuid="test-uuid",
            handling=OriginalHandling.KEEP,
            archive_album="Some Album",  # Should be ignored
        )

        mock_runner.run.assert_not_called()


class TestAlbumCreation:
    """Tests for album creation functionality."""

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_create_album_script_checks_existence(
        self, mock_runner_class: MagicMock
    ) -> None:
        """Test that album creation script checks if album exists first."""
        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.result = "true"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()
        script = importer._build_create_album_script("Test Album")

        assert "exists album" in script.lower()
        assert "make new album" in script.lower()
        assert "Test Album" in script

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_create_album_if_not_exists(self, mock_runner_class: MagicMock) -> None:
        """Test _create_album_if_not_exists method."""
        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.result = "true"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()
        importer._create_album_if_not_exists("New Album")

        mock_runner.run.assert_called_once()
        call_args = mock_runner.run.call_args[0][0]
        assert "New Album" in call_args

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_create_album_raises_on_failure(
        self, mock_runner_class: MagicMock
    ) -> None:
        """Test that album creation raises OriginalHandlingError on failure."""
        mock_runner = MagicMock()
        mock_runner.run.side_effect = AppleScriptExecutionError(
            "Failed", stderr="Permission denied"
        )
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()

        with pytest.raises(OriginalHandlingError) as exc_info:
            importer._create_album_if_not_exists("Problematic Album")

        assert exc_info.value.handling == OriginalHandling.ARCHIVE


class TestHandlingRollback:
    """Tests for handling failure and rollback scenarios."""

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_delete_failure_does_not_corrupt_library(
        self, mock_runner_class: MagicMock
    ) -> None:
        """Test that delete failure leaves library in consistent state."""
        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.result = "false: Unable to delete"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()

        # Should raise but not leave partial state
        with pytest.raises(OriginalHandlingError):
            importer.handle_original(
                original_uuid="test-uuid",
                handling=OriginalHandling.DELETE,
            )

        # Only one call should have been made
        assert mock_runner.run.call_count == 1

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_archive_partial_failure_reports_correctly(
        self, mock_runner_class: MagicMock
    ) -> None:
        """Test that archive partial failure (after album creation) reports error."""
        mock_runner = MagicMock()

        # Album creation succeeds
        mock_album_success = MagicMock()
        mock_album_success.result = "true"

        # Add to album fails
        mock_add_failure = MagicMock()
        mock_add_failure.result = "false: Video not found"

        mock_runner.run.side_effect = [mock_album_success, mock_add_failure]
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()

        with pytest.raises(OriginalHandlingError) as exc_info:
            importer.handle_original(
                original_uuid="test-uuid",
                handling=OriginalHandling.ARCHIVE,
            )

        # Album was created but video wasn't added
        assert exc_info.value.handling == OriginalHandling.ARCHIVE
        assert mock_runner.run.call_count == 2

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_handling_preserves_original_on_any_error(
        self, mock_runner_class: MagicMock
    ) -> None:
        """Test that original video is preserved if any handling step fails."""
        mock_runner = MagicMock()
        mock_runner.run.side_effect = AppleScriptExecutionError(
            "Unexpected error", stderr="Error details"
        )
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()

        # Archive fails - original should still exist in Photos
        with pytest.raises(OriginalHandlingError):
            importer.handle_original(
                original_uuid="precious-video-uuid",
                handling=OriginalHandling.ARCHIVE,
            )

        # Delete fails - original should still exist in Photos
        with pytest.raises(OriginalHandlingError):
            importer.handle_original(
                original_uuid="precious-video-uuid",
                handling=OriginalHandling.DELETE,
            )


class TestAppleScriptBuilding:
    """Tests for AppleScript generation methods."""

    def test_delete_script_structure(self) -> None:
        """Test that delete script has correct structure."""
        importer = PhotosImporter()
        script = importer._build_delete_script("test-uuid-123")

        assert "test-uuid-123" in script
        assert "tell application" in script.lower()
        assert "photos" in script.lower()
        assert "delete" in script.lower()
        assert "return" in script.lower()

    def test_add_to_album_script_structure(self) -> None:
        """Test that add to album script has correct structure."""
        importer = PhotosImporter()
        script = importer._build_add_to_album_script("test-uuid", "My Album")

        assert "test-uuid" in script
        assert "My Album" in script
        assert "tell application" in script.lower()
        assert "add" in script.lower()

    def test_create_album_script_structure(self) -> None:
        """Test that create album script has correct structure."""
        importer = PhotosImporter()
        script = importer._build_create_album_script("New Album Name")

        assert "New Album Name" in script
        assert "exists album" in script.lower()
        assert "make new album" in script.lower()

    def test_scripts_escape_special_characters(self) -> None:
        """Test that scripts properly escape special characters."""
        importer = PhotosImporter()

        # Test with quotes in album name
        script = importer._build_create_album_script('Album "with" quotes')
        assert "Album" in script

        # Test with backslashes
        script = importer._build_add_to_album_script("uuid", "Album\\Path")
        assert "Album" in script


class TestOriginalHandlingEnumIntegration:
    """Integration tests for OriginalHandling enum with PhotosImporter."""

    def test_all_handling_types_are_processed(self) -> None:
        """Test that all OriginalHandling types have corresponding handlers."""
        with patch("video_converter.importers.photos_importer.AppleScriptRunner"):
            importer = PhotosImporter()

            # Each handling type should be processable
            for handling in OriginalHandling:
                with patch.object(importer, "_delete_video"), patch.object(
                    importer, "_archive_video"
                ):
                    # Should not raise for any handling type
                    importer.handle_original(
                        original_uuid="test-uuid",
                        handling=handling,
                    )

    @patch("video_converter.importers.photos_importer.AppleScriptRunner")
    def test_handling_type_determines_action(
        self, mock_runner_class: MagicMock
    ) -> None:
        """Test that different handling types trigger different actions."""
        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.result = "true"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        importer = PhotosImporter()

        # DELETE should call delete script
        importer.handle_original("uuid1", OriginalHandling.DELETE)
        delete_call_script = mock_runner.run.call_args[0][0]
        assert "delete" in delete_call_script.lower()

        mock_runner.reset_mock()

        # ARCHIVE should call album scripts
        importer.handle_original("uuid2", OriginalHandling.ARCHIVE)
        assert mock_runner.run.call_count == 2  # album creation + add to album

        mock_runner.reset_mock()

        # KEEP should not call anything
        importer.handle_original("uuid3", OriginalHandling.KEEP)
        mock_runner.run.assert_not_called()
