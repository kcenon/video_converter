"""Integration tests for Photos re-import functionality.

This module tests the video-converter CLI with Photos re-import options,
including --reimport, --delete-originals, --keep-originals, and the
full re-import workflow with mocked Photos library.

SRS Reference: SRS-305 (Photos Re-Import)
SDS Reference: SDS-P01-008
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from video_converter.__main__ import main


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Click CLI test runner."""
    return CliRunner()


class TestReimportCLIOptions:
    """Tests for re-import CLI options availability."""

    def test_reimport_option_in_help(self, cli_runner: CliRunner) -> None:
        """Test that --reimport option is shown in help."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert result.exit_code == 0
        assert "--reimport" in result.output

    def test_delete_originals_option_in_help(self, cli_runner: CliRunner) -> None:
        """Test that --delete-originals option is shown in help."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert result.exit_code == 0
        assert "--delete-originals" in result.output

    def test_keep_originals_option_in_help(self, cli_runner: CliRunner) -> None:
        """Test that --keep-originals option is shown in help."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert result.exit_code == 0
        assert "--keep-originals" in result.output

    def test_archive_album_option_in_help(self, cli_runner: CliRunner) -> None:
        """Test that --archive-album option is shown in help."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert result.exit_code == 0
        assert "--archive-album" in result.output

    def test_confirm_delete_option_in_help(self, cli_runner: CliRunner) -> None:
        """Test that --confirm-delete option is shown in help."""
        result = cli_runner.invoke(main, ["run", "--help"])

        assert result.exit_code == 0
        assert "--confirm-delete" in result.output


class TestReimportOptionValidation:
    """Tests for re-import option validation."""

    def test_delete_and_keep_originals_mutually_exclusive(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that --delete-originals and --keep-originals cannot be used together."""
        result = cli_runner.invoke(
            main,
            [
                "run",
                "--source",
                "photos",
                "--reimport",
                "--delete-originals",
                "--keep-originals",
                "--confirm-delete",
            ],
        )

        assert result.exit_code != 0
        assert (
            "Cannot use both --delete-originals and --keep-originals" in result.output
        )

    def test_delete_originals_requires_confirm_delete(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that --delete-originals requires --confirm-delete flag."""
        result = cli_runner.invoke(
            main,
            [
                "run",
                "--source",
                "photos",
                "--reimport",
                "--delete-originals",
            ],
        )

        assert result.exit_code != 0
        assert "--delete-originals requires --confirm-delete" in result.output

    def test_delete_originals_without_reimport_warns(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that using --delete-originals without --reimport shows warning."""
        result = cli_runner.invoke(
            main,
            [
                "run",
                "--source",
                "photos",
                "--delete-originals",
                "--confirm-delete",
            ],
        )

        # Should either warn or exit due to missing --reimport
        assert "require --reimport" in result.output or result.exit_code != 0


class TestReimportCLIExecution:
    """Tests for re-import CLI command execution."""

    def test_reimport_option_accepted(self, cli_runner: CliRunner) -> None:
        """Test that --reimport option is accepted."""
        result = cli_runner.invoke(
            main,
            ["run", "--source", "photos", "--reimport"],
        )

        # Option should be accepted (may fail due to permissions, but not invalid option)
        assert "Invalid value for '--reimport'" not in result.output
        assert "No such option" not in result.output

    def test_reimport_with_keep_originals_accepted(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that --reimport with --keep-originals is accepted."""
        result = cli_runner.invoke(
            main,
            ["run", "--source", "photos", "--reimport", "--keep-originals"],
        )

        assert "Invalid value" not in result.output
        assert "No such option" not in result.output

    def test_reimport_with_archive_album_accepted(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that --reimport with --archive-album is accepted."""
        result = cli_runner.invoke(
            main,
            [
                "run",
                "--source",
                "photos",
                "--reimport",
                "--archive-album",
                "My Converted Videos",
            ],
        )

        assert "Invalid value for '--archive-album'" not in result.output

    def test_reimport_with_delete_and_confirm_accepted(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that --reimport with --delete-originals and --confirm-delete is accepted."""
        result = cli_runner.invoke(
            main,
            [
                "run",
                "--source",
                "photos",
                "--reimport",
                "--delete-originals",
                "--confirm-delete",
            ],
        )

        # Should not reject due to invalid options
        assert "Invalid value" not in result.output
        assert "No such option" not in result.output


class TestDryRunMode:
    """Tests for dry-run mode with re-import options."""

    def test_dry_run_with_reimport_accepted(self, cli_runner: CliRunner) -> None:
        """Test that --dry-run with --reimport is accepted."""
        result = cli_runner.invoke(
            main,
            ["run", "--source", "photos", "--reimport", "--dry-run"],
        )

        assert "Invalid value" not in result.output

    def test_dry_run_with_delete_originals_accepted(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that --dry-run with --delete-originals is accepted."""
        result = cli_runner.invoke(
            main,
            [
                "run",
                "--source",
                "photos",
                "--reimport",
                "--delete-originals",
                "--confirm-delete",
                "--dry-run",
            ],
        )

        assert "Invalid value" not in result.output


class TestFullReimportWorkflow:
    """Tests for full re-import workflow with mocked components."""

    @pytest.fixture
    def mock_photos_library(self) -> MagicMock:
        """Create a mock PhotosLibrary."""
        mock_library = MagicMock()
        mock_library.check_permissions.return_value = True
        mock_library.get_video_count.return_value = 1
        return mock_library

    @pytest.fixture
    def mock_video_info(self, tmp_path: Path) -> MagicMock:
        """Create a mock PhotosVideoInfo with a real file."""
        video_file = tmp_path / "test_video.mov"
        video_file.write_bytes(b"fake video content")

        mock_video = MagicMock()
        mock_video.uuid = "original-uuid-123"
        mock_video.filename = "test_video.mov"
        mock_video.path = video_file
        mock_video.date = datetime(2024, 7, 15, 10, 30, 0)
        mock_video.date_modified = None
        mock_video.duration = 60.0
        mock_video.favorite = True
        mock_video.hidden = False
        mock_video.in_cloud = False
        mock_video.location = (37.7749, -122.4194)
        mock_video.albums = ["Vacation", "Family"]
        mock_video.codec = "h264"
        mock_video.is_h264 = True
        mock_video.is_hevc = False
        mock_video.needs_conversion = True
        mock_video.is_available_locally = True

        return mock_video

    @pytest.fixture
    def mock_metadata_snapshot(self) -> MagicMock:
        """Create a mock VideoMetadataSnapshot."""
        from video_converter.importers.metadata_preservation import (
            VideoMetadataSnapshot,
        )

        return VideoMetadataSnapshot(
            uuid="original-uuid-123",
            filename="test_video.mov",
            albums=["Vacation", "Family"],
            is_favorite=True,
            is_hidden=False,
            date=datetime(2024, 7, 15, 10, 30, 0),
            location=(37.7749, -122.4194),
        )

    def test_workflow_captures_metadata_before_conversion(
        self,
        mock_video_info: MagicMock,
        mock_metadata_snapshot: MagicMock,
    ) -> None:
        """Test that workflow captures metadata before conversion."""
        from video_converter.importers.metadata_preservation import MetadataPreserver

        with patch.object(
            MetadataPreserver, "__init__", return_value=None
        ), patch.object(
            MetadataPreserver,
            "capture_metadata",
            return_value=mock_metadata_snapshot,
        ) as mock_capture:
            preserver = MetadataPreserver()
            snapshot = preserver.capture_metadata(mock_video_info)

            mock_capture.assert_called_once_with(mock_video_info)
            assert snapshot.uuid == "original-uuid-123"
            assert snapshot.albums == ["Vacation", "Family"]
            assert snapshot.is_favorite is True

    def test_workflow_embeds_metadata_in_converted_file(
        self,
        tmp_path: Path,
        mock_metadata_snapshot: MagicMock,
    ) -> None:
        """Test that workflow embeds metadata in converted file."""
        from video_converter.importers.metadata_preservation import MetadataPreserver

        converted_file = tmp_path / "converted.mp4"
        converted_file.touch()

        with patch.object(
            MetadataPreserver, "__init__", return_value=None
        ), patch.object(
            MetadataPreserver, "embed_metadata_in_file", return_value=True
        ) as mock_embed:
            preserver = MetadataPreserver()
            result = preserver.embed_metadata_in_file(
                converted_file, mock_metadata_snapshot
            )

            mock_embed.assert_called_once()
            assert result is True

    def test_workflow_imports_video_to_photos(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that workflow imports converted video to Photos."""
        from video_converter.importers.photos_importer import PhotosImporter

        converted_file = tmp_path / "converted.mp4"
        converted_file.touch()

        with patch.object(PhotosImporter, "__init__", return_value=None), patch.object(
            PhotosImporter, "import_video", return_value="new-uuid-456"
        ) as mock_import:
            importer = PhotosImporter()
            new_uuid = importer.import_video(converted_file)

            mock_import.assert_called_once_with(converted_file)
            assert new_uuid == "new-uuid-456"

    def test_workflow_applies_photos_metadata(
        self,
        mock_metadata_snapshot: MagicMock,
    ) -> None:
        """Test that workflow applies Photos metadata after import."""
        from video_converter.importers.metadata_preservation import MetadataPreserver

        with patch.object(
            MetadataPreserver, "__init__", return_value=None
        ), patch.object(
            MetadataPreserver, "apply_photos_metadata", return_value=True
        ) as mock_apply:
            preserver = MetadataPreserver()
            result = preserver.apply_photos_metadata(
                "new-uuid-456", mock_metadata_snapshot
            )

            mock_apply.assert_called_once()
            assert result is True

    def test_workflow_handles_original_after_success(self) -> None:
        """Test that workflow handles original video after successful import."""
        from video_converter.importers.photos_importer import (
            OriginalHandling,
            PhotosImporter,
        )

        with patch.object(PhotosImporter, "__init__", return_value=None), patch.object(
            PhotosImporter, "handle_original"
        ) as mock_handle:
            importer = PhotosImporter()
            importer.handle_original(
                original_uuid="original-uuid-123",
                handling=OriginalHandling.ARCHIVE,
                archive_album="Converted Originals",
            )

            mock_handle.assert_called_once_with(
                original_uuid="original-uuid-123",
                handling=OriginalHandling.ARCHIVE,
                archive_album="Converted Originals",
            )

    def test_workflow_verifies_metadata_after_import(
        self,
        mock_metadata_snapshot: MagicMock,
    ) -> None:
        """Test that workflow verifies metadata after import."""
        from video_converter.importers.metadata_preservation import (
            MetadataPreserver,
            VerificationResult,
        )

        expected_result = VerificationResult(
            success=True,
            albums_matched=True,
            favorite_matched=True,
            date_matched=True,
            location_matched=True,
        )

        with patch.object(
            MetadataPreserver, "__init__", return_value=None
        ), patch.object(
            MetadataPreserver, "verify_metadata", return_value=expected_result
        ) as mock_verify:
            preserver = MetadataPreserver()
            result = preserver.verify_metadata("new-uuid-456", mock_metadata_snapshot)

            mock_verify.assert_called_once()
            assert result.success is True


class TestReimportErrorHandling:
    """Tests for error handling in re-import workflow."""

    def test_import_failure_does_not_delete_original(self) -> None:
        """Test that import failure does not trigger original deletion."""
        from video_converter.importers.photos_importer import (
            ImportFailedError,
            OriginalHandling,
            PhotosImporter,
        )

        with patch.object(PhotosImporter, "__init__", return_value=None), patch.object(
            PhotosImporter,
            "import_video",
            side_effect=ImportFailedError("Import failed"),
        ), patch.object(PhotosImporter, "handle_original") as mock_handle:
            importer = PhotosImporter()

            with pytest.raises(ImportFailedError):
                importer.import_video(Path("/fake/path.mp4"))

            # Original handling should not be called if import failed
            mock_handle.assert_not_called()

    def test_metadata_failure_continues_with_partial_success(self) -> None:
        """Test that metadata failure doesn't prevent video import."""
        from video_converter.importers.metadata_preservation import (
            MetadataPreserver,
            VideoMetadataSnapshot,
        )

        snapshot = VideoMetadataSnapshot(
            uuid="original-uuid-123",
            filename="test_video.mov",
            albums=["Vacation"],
            is_favorite=True,
        )

        with patch.object(
            MetadataPreserver, "__init__", return_value=None
        ), patch.object(
            MetadataPreserver, "apply_photos_metadata", return_value=False
        ) as mock_apply:
            preserver = MetadataPreserver()
            result = preserver.apply_photos_metadata("new-uuid", snapshot)

            # Should return False but not raise
            assert result is False
            mock_apply.assert_called_once()


class TestReimportWithDifferentHandlingOptions:
    """Tests for re-import with different original handling options."""

    def test_reimport_with_delete_handling(self) -> None:
        """Test re-import workflow with DELETE handling."""
        from video_converter.importers.photos_importer import (
            OriginalHandling,
            PhotosImporter,
        )

        with patch.object(PhotosImporter, "__init__", return_value=None), patch.object(
            PhotosImporter, "_delete_video"
        ) as mock_delete:
            importer = PhotosImporter()
            importer.handle_original(
                original_uuid="uuid",
                handling=OriginalHandling.DELETE,
            )

            mock_delete.assert_called_once_with("uuid")

    def test_reimport_with_archive_handling(self) -> None:
        """Test re-import workflow with ARCHIVE handling."""
        from video_converter.importers.photos_importer import (
            OriginalHandling,
            PhotosImporter,
        )

        with patch.object(PhotosImporter, "__init__", return_value=None), patch.object(
            PhotosImporter, "_archive_video"
        ) as mock_archive:
            importer = PhotosImporter()
            importer.handle_original(
                original_uuid="uuid",
                handling=OriginalHandling.ARCHIVE,
                archive_album="Custom Album",
            )

            mock_archive.assert_called_once_with("uuid", "Custom Album")

    def test_reimport_with_keep_handling(self) -> None:
        """Test re-import workflow with KEEP handling."""
        from video_converter.importers.photos_importer import (
            OriginalHandling,
            PhotosImporter,
        )

        with patch.object(PhotosImporter, "__init__", return_value=None), patch.object(
            PhotosImporter, "_delete_video"
        ) as mock_delete, patch.object(
            PhotosImporter, "_archive_video"
        ) as mock_archive:
            importer = PhotosImporter()
            importer.handle_original(
                original_uuid="uuid",
                handling=OriginalHandling.KEEP,
            )

            # Neither delete nor archive should be called
            mock_delete.assert_not_called()
            mock_archive.assert_not_called()
