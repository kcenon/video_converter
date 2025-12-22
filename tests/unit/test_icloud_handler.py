"""Unit tests for icloud_handler module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_converter.extractors.icloud_handler import (
    CloudStatus,
    DownloadProgress,
    iCloudDownloadError,
    iCloudError,
    iCloudHandler,
    iCloudTimeoutError,
)
from video_converter.extractors.photos_extractor import PhotosVideoInfo


class TestCloudStatus:
    """Tests for CloudStatus enum."""

    def test_cloud_status_values(self) -> None:
        """Test CloudStatus enum values."""
        assert CloudStatus.LOCAL.value == "local"
        assert CloudStatus.CLOUD_ONLY.value == "cloud_only"
        assert CloudStatus.DOWNLOADING.value == "downloading"
        assert CloudStatus.FAILED.value == "failed"
        assert CloudStatus.UNKNOWN.value == "unknown"


class TestDownloadProgress:
    """Tests for DownloadProgress dataclass."""

    def test_download_progress_creation(self) -> None:
        """Test creating a download progress object."""
        progress = DownloadProgress(
            filename="video.mov",
            status=CloudStatus.DOWNLOADING,
            progress=50.0,
            bytes_downloaded=500_000,
            bytes_total=1_000_000,
            elapsed_seconds=10.5,
        )

        assert progress.filename == "video.mov"
        assert progress.status == CloudStatus.DOWNLOADING
        assert progress.progress == 50.0
        assert progress.bytes_downloaded == 500_000
        assert progress.bytes_total == 1_000_000
        assert progress.elapsed_seconds == 10.5

    def test_is_complete_when_local(self) -> None:
        """Test is_complete returns True when status is LOCAL."""
        progress = DownloadProgress(
            filename="video.mov",
            status=CloudStatus.LOCAL,
        )
        assert progress.is_complete is True

    def test_is_complete_when_downloading(self) -> None:
        """Test is_complete returns False when still downloading."""
        progress = DownloadProgress(
            filename="video.mov",
            status=CloudStatus.DOWNLOADING,
        )
        assert progress.is_complete is False

    def test_is_failed_when_failed(self) -> None:
        """Test is_failed returns True when status is FAILED."""
        progress = DownloadProgress(
            filename="video.mov",
            status=CloudStatus.FAILED,
        )
        assert progress.is_failed is True

    def test_is_failed_when_local(self) -> None:
        """Test is_failed returns False when download succeeded."""
        progress = DownloadProgress(
            filename="video.mov",
            status=CloudStatus.LOCAL,
        )
        assert progress.is_failed is False

    def test_default_values(self) -> None:
        """Test default values for optional fields."""
        progress = DownloadProgress(
            filename="video.mov",
            status=CloudStatus.UNKNOWN,
        )

        assert progress.progress == -1.0
        assert progress.bytes_downloaded == 0
        assert progress.bytes_total == 0
        assert progress.elapsed_seconds == 0.0


class TestiCloudExceptions:
    """Tests for iCloud exception classes."""

    def test_icloud_download_error(self) -> None:
        """Test iCloudDownloadError exception."""
        error = iCloudDownloadError("video.mov", "Network timeout")
        assert "video.mov" in str(error)
        assert "Network timeout" in str(error)
        assert error.filename == "video.mov"
        assert error.reason == "Network timeout"

    def test_icloud_download_error_default_reason(self) -> None:
        """Test iCloudDownloadError with default reason."""
        error = iCloudDownloadError("video.mov")
        assert "Unknown error" in str(error)

    def test_icloud_timeout_error(self) -> None:
        """Test iCloudTimeoutError exception."""
        error = iCloudTimeoutError("video.mov", 3600)
        assert "video.mov" in str(error)
        assert "3600" in str(error)
        assert error.filename == "video.mov"
        assert error.timeout == 3600

    def test_icloud_error_base_class(self) -> None:
        """Test that exceptions inherit from iCloudError."""
        assert issubclass(iCloudDownloadError, iCloudError)
        assert issubclass(iCloudTimeoutError, iCloudError)


class TestiCloudHandler:
    """Tests for iCloudHandler class."""

    def test_init_with_defaults(self) -> None:
        """Test iCloudHandler initialization with default values."""
        handler = iCloudHandler()

        assert handler.timeout == iCloudHandler.DEFAULT_TIMEOUT
        assert handler.poll_interval == iCloudHandler.DEFAULT_POLL_INTERVAL

    def test_init_with_custom_values(self) -> None:
        """Test iCloudHandler initialization with custom values."""
        handler = iCloudHandler(timeout=1800, poll_interval=0.5)

        assert handler.timeout == 1800
        assert handler.poll_interval == 0.5

    def test_get_status_local_not_in_cloud(self) -> None:
        """Test get_status returns LOCAL when video is not in cloud."""
        handler = iCloudHandler()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=Path("/path/to/video.mov"),
            date=datetime(2024, 1, 1),
            date_modified=None,
            duration=60.0,
            in_cloud=False,
        )

        status = handler.get_status(video)
        assert status == CloudStatus.LOCAL

    def test_get_status_local_with_existing_file(self, tmp_path: Path) -> None:
        """Test get_status returns LOCAL when file exists locally."""
        handler = iCloudHandler()

        video_file = tmp_path / "video.mov"
        video_file.touch()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=video_file,
            date=datetime(2024, 1, 1),
            date_modified=None,
            duration=60.0,
            in_cloud=True,
        )

        status = handler.get_status(video)
        assert status == CloudStatus.LOCAL

    def test_get_status_cloud_only_with_stub(self, tmp_path: Path) -> None:
        """Test get_status returns CLOUD_ONLY when stub file exists."""
        handler = iCloudHandler()

        video_path = tmp_path / "video.mov"
        stub_path = tmp_path / ".video.mov.icloud"
        stub_path.touch()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=video_path,
            date=datetime(2024, 1, 1),
            date_modified=None,
            duration=60.0,
            in_cloud=True,
        )

        status = handler.get_status(video)
        assert status == CloudStatus.CLOUD_ONLY

    def test_get_status_downloading_both_files_exist(self, tmp_path: Path) -> None:
        """Test get_status returns DOWNLOADING when both stub and file exist."""
        handler = iCloudHandler()

        video_path = tmp_path / "video.mov"
        video_path.touch()
        stub_path = tmp_path / ".video.mov.icloud"
        stub_path.touch()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=video_path,
            date=datetime(2024, 1, 1),
            date_modified=None,
            duration=60.0,
            in_cloud=True,
        )

        status = handler.get_status(video)
        assert status == CloudStatus.DOWNLOADING

    def test_get_status_cloud_only_no_path(self) -> None:
        """Test get_status returns CLOUD_ONLY when path is None."""
        handler = iCloudHandler()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=None,
            date=datetime(2024, 1, 1),
            date_modified=None,
            duration=60.0,
            in_cloud=True,
        )

        status = handler.get_status(video)
        assert status == CloudStatus.CLOUD_ONLY

    def test_get_stub_path(self) -> None:
        """Test _get_stub_path returns correct path."""
        handler = iCloudHandler()

        original_path = Path("/path/to/video.mov")
        stub_path = handler._get_stub_path(original_path)

        assert stub_path == Path("/path/to/.video.mov.icloud")

    def test_is_stub_file_true(self) -> None:
        """Test _is_stub_file returns True for stub files."""
        handler = iCloudHandler()

        assert handler._is_stub_file(Path(".video.mov.icloud")) is True
        assert handler._is_stub_file(Path("/path/to/.video.mov.icloud")) is True

    def test_is_stub_file_false(self) -> None:
        """Test _is_stub_file returns False for regular files."""
        handler = iCloudHandler()

        assert handler._is_stub_file(Path("video.mov")) is False
        assert handler._is_stub_file(Path("/path/to/video.mov")) is False

    @patch("video_converter.extractors.icloud_handler.subprocess.run")
    def test_trigger_download_success(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Test trigger_download returns True on success."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        handler = iCloudHandler()

        video_file = tmp_path / "video.mov"
        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=video_file,
            date=None,
            date_modified=None,
            duration=60.0,
        )

        result = handler.trigger_download(video)

        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "brctl"
        assert args[1] == "download"

    @patch("video_converter.extractors.icloud_handler.subprocess.run")
    def test_trigger_download_failure(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Test trigger_download returns False on failure."""
        mock_run.return_value = MagicMock(returncode=1, stderr="Error")

        handler = iCloudHandler()

        video_file = tmp_path / "video.mov"
        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=video_file,
            date=None,
            date_modified=None,
            duration=60.0,
        )

        result = handler.trigger_download(video)

        assert result is False

    def test_trigger_download_no_path(self) -> None:
        """Test trigger_download returns False when path is None."""
        handler = iCloudHandler()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=None,
            date=None,
            date_modified=None,
            duration=60.0,
        )

        result = handler.trigger_download(video)

        assert result is False

    @patch("video_converter.extractors.icloud_handler.subprocess.run")
    def test_trigger_download_uses_stub_path(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Test trigger_download uses stub path when it exists."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        handler = iCloudHandler()

        video_path = tmp_path / "video.mov"
        stub_path = tmp_path / ".video.mov.icloud"
        stub_path.touch()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=video_path,
            date=None,
            date_modified=None,
            duration=60.0,
        )

        handler.trigger_download(video)

        args = mock_run.call_args[0][0]
        assert str(stub_path) in args[2]

    @patch("video_converter.extractors.icloud_handler.subprocess.run")
    def test_trigger_download_brctl_not_found(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Test trigger_download handles brctl not found."""
        mock_run.side_effect = FileNotFoundError("brctl not found")

        handler = iCloudHandler()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=tmp_path / "video.mov",
            date=None,
            date_modified=None,
            duration=60.0,
        )

        result = handler.trigger_download(video)

        assert result is False

    @patch("video_converter.extractors.icloud_handler.subprocess.run")
    def test_trigger_download_timeout(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Test trigger_download handles timeout."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("brctl", 30)

        handler = iCloudHandler()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=tmp_path / "video.mov",
            date=None,
            date_modified=None,
            duration=60.0,
        )

        result = handler.trigger_download(video)

        assert result is False

    def test_wait_for_download_already_local(self, tmp_path: Path) -> None:
        """Test wait_for_download returns True for local file."""
        handler = iCloudHandler()

        video_file = tmp_path / "video.mov"
        video_file.touch()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=video_file,
            date=None,
            date_modified=None,
            duration=60.0,
            in_cloud=False,
        )

        progress_updates: list[DownloadProgress] = []

        result = handler.wait_for_download(
            video,
            on_progress=lambda p: progress_updates.append(p),
        )

        assert result is True
        assert len(progress_updates) == 1
        assert progress_updates[0].status == CloudStatus.LOCAL

    def test_wait_for_download_no_path(self) -> None:
        """Test wait_for_download returns False when path is None."""
        handler = iCloudHandler()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=None,
            date=None,
            date_modified=None,
            duration=60.0,
        )

        result = handler.wait_for_download(video)

        assert result is False

    @patch.object(iCloudHandler, "get_status")
    def test_wait_for_download_timeout(
        self, mock_get_status: MagicMock, tmp_path: Path
    ) -> None:
        """Test wait_for_download returns False on timeout."""
        mock_get_status.return_value = CloudStatus.DOWNLOADING

        handler = iCloudHandler(timeout=0.1, poll_interval=0.05)

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=tmp_path / "video.mov",
            date=None,
            date_modified=None,
            duration=60.0,
        )

        progress_updates: list[DownloadProgress] = []

        result = handler.wait_for_download(
            video,
            on_progress=lambda p: progress_updates.append(p),
        )

        assert result is False
        assert len(progress_updates) > 0
        assert progress_updates[-1].status == CloudStatus.FAILED

    def test_download_and_wait_already_local(self, tmp_path: Path) -> None:
        """Test download_and_wait returns True when already local."""
        handler = iCloudHandler()

        video_file = tmp_path / "video.mov"
        video_file.touch()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=video_file,
            date=None,
            date_modified=None,
            duration=60.0,
            in_cloud=False,
        )

        result = handler.download_and_wait(video)

        assert result is True

    @patch.object(iCloudHandler, "get_status")
    def test_download_and_wait_failed_status(
        self, mock_get_status: MagicMock, tmp_path: Path
    ) -> None:
        """Test download_and_wait returns False when status is FAILED."""
        mock_get_status.return_value = CloudStatus.FAILED

        handler = iCloudHandler()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=tmp_path / "video.mov",
            date=None,
            date_modified=None,
            duration=60.0,
        )

        result = handler.download_and_wait(video)

        assert result is False

    @patch.object(iCloudHandler, "wait_for_download")
    @patch.object(iCloudHandler, "trigger_download")
    @patch.object(iCloudHandler, "get_status")
    def test_download_and_wait_triggers_download(
        self,
        mock_get_status: MagicMock,
        mock_trigger: MagicMock,
        mock_wait: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test download_and_wait triggers download for cloud-only files."""
        mock_get_status.return_value = CloudStatus.CLOUD_ONLY
        mock_trigger.return_value = True
        mock_wait.return_value = True

        handler = iCloudHandler()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=tmp_path / "video.mov",
            date=None,
            date_modified=None,
            duration=60.0,
        )

        result = handler.download_and_wait(video)

        assert result is True
        mock_trigger.assert_called_once()
        mock_wait.assert_called_once()

    @patch.object(iCloudHandler, "trigger_download")
    @patch.object(iCloudHandler, "get_status")
    def test_download_and_wait_trigger_fails(
        self,
        mock_get_status: MagicMock,
        mock_trigger: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test download_and_wait returns False when trigger fails."""
        mock_get_status.return_value = CloudStatus.CLOUD_ONLY
        mock_trigger.return_value = False

        handler = iCloudHandler()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=tmp_path / "video.mov",
            date=None,
            date_modified=None,
            duration=60.0,
        )

        result = handler.download_and_wait(video)

        assert result is False

    @patch("video_converter.extractors.icloud_handler.subprocess.run")
    def test_evict_success(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test evict returns True on success."""
        mock_run.return_value = MagicMock(returncode=0)

        handler = iCloudHandler()

        video_file = tmp_path / "video.mov"
        video_file.touch()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=video_file,
            date=None,
            date_modified=None,
            duration=60.0,
        )

        result = handler.evict(video)

        assert result is True
        args = mock_run.call_args[0][0]
        assert args[0] == "brctl"
        assert args[1] == "evict"

    @patch("video_converter.extractors.icloud_handler.subprocess.run")
    def test_evict_failure(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test evict returns False on failure."""
        mock_run.return_value = MagicMock(returncode=1)

        handler = iCloudHandler()

        video_file = tmp_path / "video.mov"
        video_file.touch()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=video_file,
            date=None,
            date_modified=None,
            duration=60.0,
        )

        result = handler.evict(video)

        assert result is False

    def test_evict_no_path(self) -> None:
        """Test evict returns False when path is None."""
        handler = iCloudHandler()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=None,
            date=None,
            date_modified=None,
            duration=60.0,
        )

        result = handler.evict(video)

        assert result is False

    def test_evict_file_not_present(self, tmp_path: Path) -> None:
        """Test evict returns True when file not present locally."""
        handler = iCloudHandler()

        video = PhotosVideoInfo(
            uuid="uuid1",
            filename="video.mov",
            path=tmp_path / "nonexistent.mov",
            date=None,
            date_modified=None,
            duration=60.0,
        )

        result = handler.evict(video)

        assert result is True

    def test_is_downloading_with_downloading_suffix(self, tmp_path: Path) -> None:
        """Test _is_downloading returns True when .downloading file exists."""
        handler = iCloudHandler()

        video_path = tmp_path / "video.mov"
        downloading_path = Path(str(video_path) + ".downloading")
        downloading_path.touch()

        result = handler._is_downloading(video_path)

        assert result is True

    def test_is_downloading_false(self, tmp_path: Path) -> None:
        """Test _is_downloading returns False when no download in progress."""
        handler = iCloudHandler()

        video_path = tmp_path / "video.mov"

        result = handler._is_downloading(video_path)

        assert result is False

    def test_get_download_progress_indeterminate(self, tmp_path: Path) -> None:
        """Test _get_download_progress returns -1 when indeterminate."""
        handler = iCloudHandler()

        video_path = tmp_path / "video.mov"

        result = handler._get_download_progress(video_path)

        assert result == -1.0


class TestConfigIntegration:
    """Tests for iCloud configuration options."""

    def test_photos_config_has_icloud_timeout(self) -> None:
        """Test PhotosConfig has icloud_timeout field."""
        from video_converter.core.config import PhotosConfig

        config = PhotosConfig()
        assert hasattr(config, "icloud_timeout")
        assert config.icloud_timeout == 3600

    def test_photos_config_has_skip_cloud_only(self) -> None:
        """Test PhotosConfig has skip_cloud_only field."""
        from video_converter.core.config import PhotosConfig

        config = PhotosConfig()
        assert hasattr(config, "skip_cloud_only")
        assert config.skip_cloud_only is False

    def test_icloud_timeout_validation(self) -> None:
        """Test icloud_timeout validation constraints."""
        from pydantic import ValidationError

        from video_converter.core.config import PhotosConfig

        # Valid range
        config = PhotosConfig(icloud_timeout=3600)
        assert config.icloud_timeout == 3600

        # Too small
        with pytest.raises(ValidationError):
            PhotosConfig(icloud_timeout=30)

        # Too large
        with pytest.raises(ValidationError):
            PhotosConfig(icloud_timeout=100000)
