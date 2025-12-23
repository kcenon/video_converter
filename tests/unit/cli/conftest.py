"""CLI-specific test fixtures.

This module provides fixtures specifically for testing CLI commands
using Click's CliRunner with isolated filesystem and mocked dependencies.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from click.testing import CliRunner

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Click CLI test runner.

    Returns:
        CliRunner: Configured CLI runner with separated stderr.
    """
    return CliRunner()


@pytest.fixture
def isolated_cli_runner() -> Generator[CliRunner, None, None]:
    """Provide a CLI runner with isolated filesystem.

    Yields:
        CliRunner: CLI runner in an isolated temporary filesystem.
    """
    runner = CliRunner()
    with runner.isolated_filesystem():
        yield runner


@pytest.fixture
def mock_codec_info() -> MagicMock:
    """Create a mock CodecInfo for H.264 video.

    Returns:
        MagicMock: Mock codec info representing H.264 video.
    """
    mock = MagicMock()
    mock.is_hevc = False
    mock.is_h264 = True
    mock.codec = "h264"
    mock.size = 100_000_000  # 100 MB
    mock.resolution_label = "1080p"
    mock.fps = 30.0
    mock.duration = 120.0
    return mock


@pytest.fixture
def mock_hevc_codec_info() -> MagicMock:
    """Create a mock CodecInfo for HEVC video.

    Returns:
        MagicMock: Mock codec info representing HEVC video.
    """
    mock = MagicMock()
    mock.is_hevc = True
    mock.is_h264 = False
    mock.codec = "hevc"
    mock.size = 50_000_000  # 50 MB
    mock.resolution_label = "1080p"
    mock.fps = 30.0
    mock.duration = 120.0
    return mock


@pytest.fixture
def mock_conversion_result() -> MagicMock:
    """Create a successful mock ConversionResult.

    Returns:
        MagicMock: Mock result for successful conversion.
    """
    mock = MagicMock()
    mock.success = True
    mock.original_size = 100_000_000  # 100 MB
    mock.converted_size = 50_000_000  # 50 MB
    mock.size_saved = 50_000_000  # 50 MB
    mock.duration_seconds = 30.0
    mock.speed_ratio = 4.0
    mock.warnings = []
    mock.error_message = None
    mock.vmaf_score = None
    mock.vmaf_quality_level = None
    return mock


@pytest.fixture
def mock_failed_conversion_result() -> MagicMock:
    """Create a failed mock ConversionResult.

    Returns:
        MagicMock: Mock result for failed conversion.
    """
    mock = MagicMock()
    mock.success = False
    mock.original_size = 100_000_000
    mock.converted_size = 0
    mock.size_saved = 0
    mock.duration_seconds = 0.0
    mock.speed_ratio = 0.0
    mock.warnings = []
    mock.error_message = "FFmpeg failed: invalid video stream"
    mock.vmaf_score = None
    mock.vmaf_quality_level = None
    return mock


@pytest.fixture
def mock_converter(mock_conversion_result: MagicMock) -> MagicMock:
    """Create a mock Converter with successful conversion.

    Args:
        mock_conversion_result: Mock result fixture.

    Returns:
        MagicMock: Mock converter that returns success.
    """
    mock = MagicMock()
    mock.convert = AsyncMock(return_value=mock_conversion_result)
    return mock


@pytest.fixture
def mock_orchestrator(mock_converter: MagicMock) -> MagicMock:
    """Create a mock Orchestrator.

    Args:
        mock_converter: Mock converter fixture.

    Returns:
        MagicMock: Mock orchestrator with converter factory.
    """
    mock = MagicMock()
    mock.converter_factory.get_converter.return_value = mock_converter
    mock.has_resumable_session.return_value = False
    return mock


@pytest.fixture
def mock_service_manager() -> MagicMock:
    """Create a mock ServiceManager.

    Returns:
        MagicMock: Mock service manager for launchd operations.
    """
    from video_converter.automation import ServiceState

    mock = MagicMock()

    # Mock status
    mock_status = MagicMock()
    mock_status.state = ServiceState.NOT_INSTALLED
    mock_status.is_installed = False
    mock_status.is_running = False
    mock_status.pid = None
    mock_status.schedule = None
    mock_status.plist_path = None
    mock_status.last_exit_status = None
    mock.get_status.return_value = mock_status

    # Mock detailed status
    mock_detailed = MagicMock()
    mock_detailed.basic_status = mock_status
    mock_detailed.next_run_relative = "Not scheduled"
    mock_detailed.last_run = MagicMock()
    mock_detailed.last_run.timestamp = None
    mock_detailed.last_run.relative_time = "Never"
    mock_detailed.last_run.result_text = ""
    mock_detailed.total_videos_converted = 0
    mock_detailed.total_storage_saved_bytes = 0
    mock.get_detailed_status.return_value = mock_detailed

    # Mock operations
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.message = "Operation completed"
    mock_result.error = None
    mock_result.plist_path = None

    mock.install.return_value = mock_result
    mock.uninstall.return_value = mock_result
    mock.start.return_value = mock_result
    mock.stop.return_value = mock_result
    mock.load.return_value = mock_result
    mock.unload.return_value = mock_result
    mock.restart.return_value = mock_result

    # Mock log paths
    mock.get_log_paths.return_value = (
        Path("/tmp/video_converter_stdout.log"),
        Path("/tmp/video_converter_stderr.log"),
    )
    mock.read_logs.return_value = {"stdout": "", "stderr": ""}

    return mock


@pytest.fixture
def mock_photos_handler() -> MagicMock:
    """Create a mock PhotosSourceHandler.

    Returns:
        MagicMock: Mock Photos handler for library operations.
    """
    mock = MagicMock()
    mock.check_permissions.return_value = True
    mock.get_permission_error.return_value = None
    mock.get_stats.return_value = MagicMock(
        total=100,
        h264=50,
        hevc=50,
        total_size_h264=5_000_000_000,  # 5 GB
    )
    mock.get_library_info.return_value = {
        "path": "/Users/test/Pictures/Photos Library.photoslibrary"
    }
    mock.get_candidates.return_value = []
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


@pytest.fixture
def mock_photos_video_info() -> MagicMock:
    """Create a mock PhotosVideoInfo.

    Returns:
        MagicMock: Mock video info from Photos library.
    """
    mock = MagicMock()
    mock.uuid = "test-uuid-12345"
    mock.filename = "vacation_2024.mp4"
    mock.size = 500_000_000  # 500 MB
    mock.date = datetime(2024, 6, 15, 14, 30, 0)
    mock.albums = ["Vacation", "Summer 2024"]
    mock.path = Path("/Users/test/Pictures/Photos Library.photoslibrary/originals/test.mp4")
    mock.is_icloud = False
    return mock


@pytest.fixture
def mock_history() -> MagicMock:
    """Create a mock ConversionHistory.

    Returns:
        MagicMock: Mock history for statistics.
    """
    from video_converter.core.history import StatsPeriod

    mock = MagicMock()

    # Mock statistics
    mock_stats = MagicMock()
    mock_stats.total_converted = 10
    mock_stats.total_failed = 2
    mock_stats.total_skipped = 1
    mock_stats.total_original_bytes = 10_000_000_000  # 10 GB
    mock_stats.total_converted_bytes = 5_000_000_000  # 5 GB
    mock_stats.total_saved_bytes = 5_000_000_000  # 5 GB
    mock_stats.average_compression_ratio = 50.0
    mock_stats.average_duration_seconds = 30.0
    mock_stats.period = StatsPeriod.ALL

    mock.get_statistics.return_value = mock_stats
    mock.get_records_by_period.return_value = []

    return mock


@pytest.fixture
def mock_config() -> MagicMock:
    """Create a mock Config.

    Returns:
        MagicMock: Mock configuration object.
    """
    mock = MagicMock()

    # Encoding settings
    mock.encoding.mode = "hardware"
    mock.encoding.quality = 45
    mock.encoding.crf = 22
    mock.encoding.preset = "medium"

    # Paths settings
    mock.paths.output = Path("/tmp/video_converter/output")
    mock.paths.processed = Path("/tmp/video_converter/processed")
    mock.paths.failed = Path("/tmp/video_converter/failed")

    # Processing settings
    mock.processing.max_concurrent = 2
    mock.processing.validate_quality = True
    mock.processing.preserve_original = True

    # Automation settings
    mock.automation.enabled = False
    mock.automation.schedule = "daily"
    mock.automation.time = "03:00"

    # Photos settings
    mock.photos.include_albums = []
    mock.photos.exclude_albums = ["Screenshots"]

    # Notification settings
    mock.notification.on_complete = True
    mock.notification.on_error = True
    mock.notification.daily_summary = False

    return mock


def create_test_video_file(path: Path, size_mb: int = 10) -> Path:
    """Create a dummy video file for testing.

    Args:
        path: Path where to create the file.
        size_mb: Size of the file in megabytes.

    Returns:
        Path: Path to the created file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # Create file with specified size (filled with zeros)
    with open(path, "wb") as f:
        f.write(b"\x00" * (size_mb * 1024 * 1024))
    return path


def create_minimal_video_file(path: Path) -> Path:
    """Create a minimal placeholder video file.

    Args:
        path: Path where to create the file.

    Returns:
        Path: Path to the created file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # Just create an empty file as placeholder
    path.write_bytes(b"fake video content for testing")
    return path
