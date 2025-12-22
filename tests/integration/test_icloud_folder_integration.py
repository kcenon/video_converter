"""Integration tests for iCloud folder support.

This module tests the iCloud folder detection, stub file handling,
and download workflow for videos stored in iCloud.

SRS Reference: SRS-304 (iCloud Download Handling)
SDS Reference: SDS-P01-007
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
import subprocess

import pytest

from video_converter.extractors.folder_extractor import (
    FolderAccessDeniedError,
    FolderExtractor,
    FolderNotFoundError,
    FolderStats,
    FolderVideoInfo,
)
from video_converter.extractors.icloud_handler import (
    CloudStatus,
    DownloadProgress,
    iCloudDownloadError,
    iCloudHandler,
    iCloudTimeoutError,
)


class TestFolderExtractoriCloudDetection:
    """Tests for iCloud stub file detection in folder extractor."""

    @pytest.fixture
    def extractor(self, tmp_path: Path) -> FolderExtractor:
        """Create a FolderExtractor for testing."""
        return FolderExtractor(tmp_path)

    def test_detects_icloud_stub_file(
        self, extractor: FolderExtractor, tmp_path: Path
    ) -> None:
        """Test that iCloud stub files are correctly detected."""
        stub_file = tmp_path / ".test_video.mp4.icloud"
        stub_file.touch()

        assert extractor._is_icloud_stub(stub_file) is True

    def test_local_file_not_icloud_stub(
        self, extractor: FolderExtractor, tmp_path: Path
    ) -> None:
        """Test that regular files are not detected as iCloud stubs."""
        regular_file = tmp_path / "test_video.mp4"
        regular_file.touch()

        assert extractor._is_icloud_stub(regular_file) is False

    def test_get_original_path_from_stub(
        self, extractor: FolderExtractor, tmp_path: Path
    ) -> None:
        """Test extraction of original path from iCloud stub path."""
        stub_path = tmp_path / ".video.mp4.icloud"
        original = extractor._get_original_path_from_stub(stub_path)

        assert original.name == "video.mp4"
        assert original.parent == stub_path.parent

    def test_get_stub_path_from_original(
        self, extractor: FolderExtractor, tmp_path: Path
    ) -> None:
        """Test generation of stub path from original path."""
        original_path = tmp_path / "video.mp4"
        stub = extractor._get_stub_path(original_path)

        assert stub.name == ".video.mp4.icloud"
        assert stub.parent == original_path.parent


class TestFolderVideoInfoiCloud:
    """Tests for FolderVideoInfo with iCloud files."""

    def test_in_cloud_property(self, tmp_path: Path) -> None:
        """Test that in_cloud property is correctly set."""
        info = FolderVideoInfo(
            path=tmp_path / "video.mp4",
            filename="video.mp4",
            size=0,
            modified_time=datetime.now(),
            in_cloud=True,
            stub_path=tmp_path / ".video.mp4.icloud",
        )

        assert info.in_cloud is True
        assert info.stub_path is not None

    def test_size_zero_for_cloud_only(self, tmp_path: Path) -> None:
        """Test that size is 0 for cloud-only files."""
        info = FolderVideoInfo(
            path=tmp_path / "video.mp4",
            filename="video.mp4",
            size=0,
            modified_time=datetime.now(),
            in_cloud=True,
        )

        assert info.size == 0
        assert info.size_mb == 0.0


class TestFolderStatsiCloud:
    """Tests for FolderStats with iCloud files."""

    def test_in_cloud_count(self) -> None:
        """Test that in_cloud count is tracked."""
        stats = FolderStats(
            total=10,
            h264=5,
            hevc=3,
            other=2,
            in_cloud=3,
        )

        assert stats.in_cloud == 3


class TestFolderExtractorScanning:
    """Tests for folder scanning with iCloud files."""

    def test_scan_includes_icloud_files(self, tmp_path: Path) -> None:
        """Test that scan includes iCloud stub files."""
        # Create stub file
        stub = tmp_path / ".cloud_video.mp4.icloud"
        stub.touch()

        extractor = FolderExtractor(tmp_path)
        paths = list(extractor.scan(include_icloud=True))

        # Should return original path, not stub path
        assert len(paths) == 1
        assert paths[0].name == "cloud_video.mp4"

    def test_scan_excludes_icloud_when_disabled(self, tmp_path: Path) -> None:
        """Test that scan excludes iCloud files when disabled."""
        stub = tmp_path / ".cloud_video.mp4.icloud"
        stub.touch()

        extractor = FolderExtractor(tmp_path)
        paths = list(extractor.scan(include_icloud=False))

        # Should not include iCloud files
        assert len(paths) == 0

    def test_scan_deduplicates_local_and_stub(self, tmp_path: Path) -> None:
        """Test that scan doesn't duplicate local files with stubs."""
        # Create both local file and stub (shouldn't happen normally)
        local = tmp_path / "video.mp4"
        stub = tmp_path / ".video.mp4.icloud"
        local.write_bytes(b"video content")
        stub.touch()

        extractor = FolderExtractor(tmp_path)
        paths = list(extractor.scan())

        # Should only return one entry
        assert len(paths) == 1

    def test_get_video_info_for_cloud_file(self, tmp_path: Path) -> None:
        """Test get_video_info for iCloud-only files."""
        # Create stub only
        stub = tmp_path / ".video.mp4.icloud"
        stub.touch()
        original_path = tmp_path / "video.mp4"

        extractor = FolderExtractor(tmp_path)
        info = extractor.get_video_info(original_path)

        assert info.in_cloud is True
        assert info.stub_path == stub
        assert info.size == 0
        assert info.codec is None  # Can't analyze cloud-only files


class TestiCloudHandler:
    """Tests for iCloud handler functionality."""

    @pytest.fixture
    def handler(self) -> iCloudHandler:
        """Create an iCloudHandler for testing."""
        return iCloudHandler(timeout=60, poll_interval=0.1)

    def test_get_status_local_file(
        self, handler: iCloudHandler, tmp_path: Path
    ) -> None:
        """Test status detection for local files."""
        from video_converter.extractors.photos_extractor import PhotosVideoInfo

        video = PhotosVideoInfo(
            uuid="test-uuid",
            filename="video.mp4",
            path=tmp_path / "video.mp4",
            date=None,
            date_modified=None,
            duration=10.0,
            size=1000,
            in_cloud=False,
        )

        # Create local file
        video.path.write_bytes(b"video content")

        status = handler.get_status(video)
        assert status == CloudStatus.LOCAL

    def test_get_status_cloud_only(
        self, handler: iCloudHandler, tmp_path: Path
    ) -> None:
        """Test status detection for cloud-only files."""
        from video_converter.extractors.photos_extractor import PhotosVideoInfo

        video = PhotosVideoInfo(
            uuid="test-uuid",
            filename="video.mp4",
            path=tmp_path / "video.mp4",
            date=None,
            date_modified=None,
            duration=10.0,
            size=1000,
            in_cloud=True,
        )

        # Create stub file only
        stub = tmp_path / ".video.mp4.icloud"
        stub.touch()

        status = handler.get_status(video)
        assert status == CloudStatus.CLOUD_ONLY

    def test_get_stub_path(self, handler: iCloudHandler, tmp_path: Path) -> None:
        """Test stub path generation."""
        path = tmp_path / "video.mp4"
        stub = handler._get_stub_path(path)

        assert stub.name == ".video.mp4.icloud"

    def test_is_stub_file(self, handler: iCloudHandler, tmp_path: Path) -> None:
        """Test stub file detection."""
        stub = tmp_path / ".video.mp4.icloud"
        normal = tmp_path / "video.mp4"

        assert handler._is_stub_file(stub) is True
        assert handler._is_stub_file(normal) is False


class TestiCloudDownload:
    """Tests for iCloud download functionality."""

    @pytest.fixture
    def handler(self) -> iCloudHandler:
        """Create an iCloudHandler for testing."""
        return iCloudHandler(timeout=5, poll_interval=0.1)

    def test_trigger_download_without_path(self, handler: iCloudHandler) -> None:
        """Test that trigger_download fails without path."""
        from video_converter.extractors.photos_extractor import PhotosVideoInfo

        video = PhotosVideoInfo(
            uuid="test-uuid",
            filename="video.mp4",
            path=None,
            date=None,
            date_modified=None,
            duration=10.0,
            size=1000,
            in_cloud=True,
        )

        result = handler.trigger_download(video)
        assert result is False

    @patch("subprocess.run")
    def test_trigger_download_calls_brctl(
        self, mock_run: MagicMock, handler: iCloudHandler, tmp_path: Path
    ) -> None:
        """Test that trigger_download calls brctl command."""
        from video_converter.extractors.photos_extractor import PhotosVideoInfo

        video = PhotosVideoInfo(
            uuid="test-uuid",
            filename="video.mp4",
            path=tmp_path / "video.mp4",
            date=None,
            date_modified=None,
            duration=10.0,
            size=1000,
            in_cloud=True,
        )

        # Create stub
        stub = tmp_path / ".video.mp4.icloud"
        stub.touch()

        mock_run.return_value = MagicMock(returncode=0)

        result = handler.trigger_download(video)

        assert result is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "brctl"
        assert call_args[1] == "download"

    @patch("subprocess.run")
    def test_trigger_download_handles_failure(
        self, mock_run: MagicMock, handler: iCloudHandler, tmp_path: Path
    ) -> None:
        """Test that trigger_download handles brctl failure."""
        from video_converter.extractors.photos_extractor import PhotosVideoInfo

        video = PhotosVideoInfo(
            uuid="test-uuid",
            filename="video.mp4",
            path=tmp_path / "video.mp4",
            date=None,
            date_modified=None,
            duration=10.0,
            size=1000,
            in_cloud=True,
        )

        mock_run.return_value = MagicMock(returncode=1, stderr="Error")

        result = handler.trigger_download(video)
        assert result is False

    @patch("subprocess.run")
    def test_trigger_download_handles_missing_brctl(
        self, mock_run: MagicMock, handler: iCloudHandler, tmp_path: Path
    ) -> None:
        """Test that trigger_download handles missing brctl command."""
        from video_converter.extractors.photos_extractor import PhotosVideoInfo

        video = PhotosVideoInfo(
            uuid="test-uuid",
            filename="video.mp4",
            path=tmp_path / "video.mp4",
            date=None,
            date_modified=None,
            duration=10.0,
            size=1000,
            in_cloud=True,
        )

        mock_run.side_effect = FileNotFoundError("brctl not found")

        result = handler.trigger_download(video)
        assert result is False


class TestiCloudEviction:
    """Tests for iCloud eviction functionality."""

    @pytest.fixture
    def handler(self) -> iCloudHandler:
        """Create an iCloudHandler for testing."""
        return iCloudHandler()

    def test_evict_without_path(self, handler: iCloudHandler) -> None:
        """Test that evict fails without path."""
        from video_converter.extractors.photos_extractor import PhotosVideoInfo

        video = PhotosVideoInfo(
            uuid="test-uuid",
            filename="video.mp4",
            path=None,
            date=None,
            date_modified=None,
            duration=10.0,
            size=1000,
            in_cloud=False,
        )

        result = handler.evict(video)
        assert result is False

    def test_evict_nonexistent_file(
        self, handler: iCloudHandler, tmp_path: Path
    ) -> None:
        """Test that evict succeeds for non-existent file."""
        from video_converter.extractors.photos_extractor import PhotosVideoInfo

        video = PhotosVideoInfo(
            uuid="test-uuid",
            filename="video.mp4",
            path=tmp_path / "nonexistent.mp4",
            date=None,
            date_modified=None,
            duration=10.0,
            size=1000,
            in_cloud=False,
        )

        result = handler.evict(video)
        assert result is True  # Already not present

    @patch("subprocess.run")
    def test_evict_calls_brctl(
        self, mock_run: MagicMock, handler: iCloudHandler, tmp_path: Path
    ) -> None:
        """Test that evict calls brctl command."""
        from video_converter.extractors.photos_extractor import PhotosVideoInfo

        video = PhotosVideoInfo(
            uuid="test-uuid",
            filename="video.mp4",
            path=tmp_path / "video.mp4",
            date=None,
            date_modified=None,
            duration=10.0,
            size=1000,
            in_cloud=False,
        )

        # Create local file
        video.path.write_bytes(b"video content")

        mock_run.return_value = MagicMock(returncode=0)

        result = handler.evict(video)

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "brctl"
        assert call_args[1] == "evict"


class TestDownloadProgress:
    """Tests for DownloadProgress dataclass."""

    def test_progress_complete(self) -> None:
        """Test is_complete property."""
        progress = DownloadProgress(
            filename="video.mp4",
            status=CloudStatus.LOCAL,
            progress=100.0,
        )

        assert progress.is_complete is True

    def test_progress_failed(self) -> None:
        """Test is_failed property."""
        progress = DownloadProgress(
            filename="video.mp4",
            status=CloudStatus.FAILED,
        )

        assert progress.is_failed is True

    def test_progress_in_progress(self) -> None:
        """Test progress during download."""
        progress = DownloadProgress(
            filename="video.mp4",
            status=CloudStatus.DOWNLOADING,
            progress=50.0,
            bytes_downloaded=500000,
            bytes_total=1000000,
            elapsed_seconds=10.5,
        )

        assert progress.is_complete is False
        assert progress.is_failed is False
        assert progress.progress == 50.0


class TestCloudStatus:
    """Tests for CloudStatus enum."""

    def test_all_statuses_defined(self) -> None:
        """Test that all expected statuses are defined."""
        assert CloudStatus.LOCAL.value == "local"
        assert CloudStatus.CLOUD_ONLY.value == "cloud_only"
        assert CloudStatus.DOWNLOADING.value == "downloading"
        assert CloudStatus.FAILED.value == "failed"
        assert CloudStatus.UNKNOWN.value == "unknown"


class TestiCloudWorkflowIntegration:
    """Integration tests for complete iCloud workflow."""

    def test_full_icloud_detection_workflow(self, tmp_path: Path) -> None:
        """Test complete iCloud detection and handling workflow."""
        # Setup: Create mix of local and cloud files
        local_video = tmp_path / "local.mp4"
        local_video.write_bytes(b"local video content")

        cloud_stub = tmp_path / ".cloud.mp4.icloud"
        cloud_stub.touch()

        # Create extractor
        extractor = FolderExtractor(tmp_path)

        # Scan for all videos
        all_videos = list(extractor.scan())
        assert len(all_videos) == 2

        # Get stats - patch the internal _codec_detector attribute
        mock_detector = MagicMock()
        mock_codec_info = MagicMock()
        mock_codec_info.codec = "h264"
        mock_codec_info.duration = 10.0
        mock_codec_info.width = 1920
        mock_codec_info.height = 1080
        mock_codec_info.fps = 30.0
        mock_codec_info.bitrate = 5000000
        mock_codec_info.container = "mp4"
        mock_detector.analyze.return_value = mock_codec_info
        extractor._codec_detector = mock_detector

        stats = extractor.get_stats()

        assert stats.total == 2
        assert stats.in_cloud == 1

    def test_download_and_convert_workflow(self, tmp_path: Path) -> None:
        """Test workflow of downloading iCloud file before conversion."""
        from video_converter.extractors.photos_extractor import PhotosVideoInfo

        handler = iCloudHandler(timeout=5, poll_interval=0.1)

        video = PhotosVideoInfo(
            uuid="test-uuid",
            filename="cloud_video.mp4",
            path=tmp_path / "cloud_video.mp4",
            date=None,
            date_modified=None,
            duration=10.0,
            size=1000000,
            in_cloud=True,
        )

        # Create stub to simulate cloud-only file
        stub = tmp_path / ".cloud_video.mp4.icloud"
        stub.touch()

        # Check initial status
        status = handler.get_status(video)
        assert status == CloudStatus.CLOUD_ONLY

        # Simulate download completion by creating local file and removing stub
        video.path.write_bytes(b"downloaded video content")
        stub.unlink()

        # Check status after "download"
        status = handler.get_status(video)
        assert status == CloudStatus.LOCAL

    def test_folder_extractor_with_nested_icloud_files(
        self, tmp_path: Path
    ) -> None:
        """Test folder extractor with nested iCloud files."""
        # Create nested structure
        subdir = tmp_path / "subfolder"
        subdir.mkdir()

        # Local file in root
        (tmp_path / "root.mp4").write_bytes(b"content")

        # Cloud file in subfolder
        (subdir / ".nested.mp4.icloud").touch()

        extractor = FolderExtractor(tmp_path, recursive=True)
        paths = list(extractor.scan())

        assert len(paths) == 2
        filenames = [p.name for p in paths]
        assert "root.mp4" in filenames
        assert "nested.mp4" in filenames


class TestiCloudErrorHandling:
    """Tests for iCloud error handling."""

    def test_icloud_download_error_message(self) -> None:
        """Test iCloudDownloadError message format."""
        error = iCloudDownloadError("video.mp4", "Network timeout")

        assert "video.mp4" in str(error)
        assert "Network timeout" in str(error)
        assert error.filename == "video.mp4"
        assert error.reason == "Network timeout"

    def test_icloud_timeout_error_message(self) -> None:
        """Test iCloudTimeoutError message format."""
        error = iCloudTimeoutError("video.mp4", 300)

        assert "video.mp4" in str(error)
        assert "300" in str(error)
        assert error.filename == "video.mp4"
        assert error.timeout == 300
