"""Pytest fixtures for GUI tests.

This module provides fixtures for testing PySide6 GUI components
using pytest-qt. It includes fixtures for creating widgets,
mocking services, and simulating user interactions.

Example:
    def test_drop_zone_creation(qtbot):
        widget = DropZone()
        qtbot.addWidget(widget)
        assert widget.isVisible() is False
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

    from pytestqt.qtbot import QtBot


# ============================================================================
# E2E Test Fixtures
# ============================================================================


def _check_ffmpeg_available() -> bool:
    """Check if FFmpeg is available on the system."""
    return shutil.which("ffmpeg") is not None


def _check_exiftool_available() -> bool:
    """Check if ExifTool is available on the system."""
    return shutil.which("exiftool") is not None


@pytest.fixture(scope="session")
def ffmpeg_available() -> bool:
    """Check if FFmpeg is available for E2E tests.

    Returns:
        bool: True if FFmpeg is installed.
    """
    return _check_ffmpeg_available()


@pytest.fixture(scope="session")
def exiftool_available() -> bool:
    """Check if ExifTool is available for E2E tests.

    Returns:
        bool: True if ExifTool is installed.
    """
    return _check_exiftool_available()


@pytest.fixture(scope="session")
def sample_h264_video(tmp_path_factory: pytest.TempPathFactory) -> Path | None:
    """Create a short H.264 test video using FFmpeg.

    Creates a 5-second 320x240 test pattern video encoded with libx264.
    This fixture is session-scoped for efficiency.

    Args:
        tmp_path_factory: Pytest's session-scoped temp path factory.

    Returns:
        Path to the created H.264 video, or None if FFmpeg unavailable.
    """
    if not _check_ffmpeg_available():
        return None

    output = tmp_path_factory.mktemp("videos") / "test_h264.mp4"
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc=duration=5:size=320x240:rate=30",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-pix_fmt",
                "yuv420p",
                str(output),
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
        return output
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


@pytest.fixture(scope="session")
def sample_video_folder(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path | None:
    """Create a folder with multiple H.264 test videos.

    Args:
        tmp_path_factory: Pytest's session-scoped temp path factory.

    Returns:
        Path to folder with test videos, or None if FFmpeg unavailable.
    """
    if not _check_ffmpeg_available():
        return None

    folder = tmp_path_factory.mktemp("video_folder")
    videos_created = 0

    for i in range(3):
        output = folder / f"test_video_{i}.mp4"
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    f"testsrc=duration=3:size=320x240:rate=30",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "ultrafast",
                    "-pix_fmt",
                    "yuv420p",
                    str(output),
                ],
                check=True,
                capture_output=True,
                timeout=60,
            )
            videos_created += 1
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue

    return folder if videos_created > 0 else None


@pytest.fixture(scope="session")
def video_with_gps(tmp_path_factory: pytest.TempPathFactory) -> Path | None:
    """Create a test video with GPS metadata.

    Args:
        tmp_path_factory: Pytest's session-scoped temp path factory.

    Returns:
        Path to video with GPS metadata, or None if tools unavailable.
    """
    if not _check_ffmpeg_available() or not _check_exiftool_available():
        return None

    output = tmp_path_factory.mktemp("gps_video") / "test_gps.mp4"
    try:
        # Create base video
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc=duration=3:size=320x240:rate=30",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-pix_fmt",
                "yuv420p",
                str(output),
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )

        # Add GPS metadata using ExifTool
        subprocess.run(
            [
                "exiftool",
                "-overwrite_original",
                "-GPSLatitude=37.5665",
                "-GPSLatitudeRef=N",
                "-GPSLongitude=126.9780",
                "-GPSLongitudeRef=E",
                str(output),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        return output
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


@pytest.fixture
def e2e_output_dir(tmp_path: Path) -> Path:
    """Provide a temporary output directory for E2E tests.

    Args:
        tmp_path: Pytest's temporary path fixture.

    Returns:
        Path to the output directory.
    """
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture
def corrupt_video_file(tmp_path: Path) -> Path:
    """Create a corrupt video file for error handling tests.

    Args:
        tmp_path: Pytest's temporary path fixture.

    Returns:
        Path to the corrupt video file.
    """
    corrupt_file = tmp_path / "corrupt.mp4"
    corrupt_file.write_bytes(b"not a valid video file content")
    return corrupt_file


@pytest.fixture
def readonly_output_dir(tmp_path: Path) -> Path:
    """Create a read-only directory for permission testing.

    Args:
        tmp_path: Pytest's temporary path fixture.

    Returns:
        Path to the read-only directory.
    """
    readonly_dir = tmp_path / "readonly"
    readonly_dir.mkdir()
    readonly_dir.chmod(0o444)
    yield readonly_dir
    # Restore permissions for cleanup
    readonly_dir.chmod(0o755)


# Skip all tests in this package if PySide6 is not available
pytest.importorskip("PySide6")


@pytest.fixture
def mock_conversion_service() -> Generator[MagicMock, None, None]:
    """Provide a mock conversion service for testing.

    The mock service provides all necessary signals and methods
    for testing GUI components without actual conversion.

    Yields:
        MagicMock: Mock ConversionService instance.
    """
    from PySide6.QtCore import Signal

    mock_service = MagicMock()
    mock_service.task_added = MagicMock()
    mock_service.task_started = MagicMock()
    mock_service.progress_updated = MagicMock()
    mock_service.task_completed = MagicMock()
    mock_service.task_failed = MagicMock()
    mock_service.task_cancelled = MagicMock()
    mock_service.queue_updated = MagicMock()
    mock_service.all_completed = MagicMock()
    mock_service.get_queue_status.return_value = {
        "total": 0,
        "queued": 0,
        "converting": 0,
        "completed": 0,
        "failed": 0,
        "is_processing": False,
        "is_paused": False,
    }
    mock_service.get_statistics.return_value = {
        "completed": 0,
        "failed": 0,
        "total_original_size": 0,
        "total_converted_size": 0,
        "total_saved": 0,
    }
    yield mock_service


@pytest.fixture
def mock_photos_service() -> Generator[MagicMock, None, None]:
    """Provide a mock photos service for testing.

    Yields:
        MagicMock: Mock PhotosService instance.
    """
    mock_service = MagicMock()
    mock_service.albums_loaded = MagicMock()
    mock_service.videos_loaded = MagicMock()
    mock_service.error_occurred = MagicMock()
    mock_service.get_albums.return_value = []
    mock_service.get_videos.return_value = []
    yield mock_service


@pytest.fixture
def mock_settings_manager() -> Generator[MagicMock, None, None]:
    """Provide a mock settings manager for testing.

    Yields:
        MagicMock: Mock SettingsManager instance.
    """
    mock_manager = MagicMock()
    mock_manager.get.return_value = {
        "encoder": "Hardware (VideoToolbox)",
        "quality": 22,
        "threads": 4,
        "output_dir": "",
        "preserve_original": True,
    }
    mock_manager.is_dirty.return_value = False
    mock_manager.apply_to_conversion_settings.return_value = {}
    yield mock_manager


@pytest.fixture
def sample_video_files(tmp_path: Path) -> list[Path]:
    """Create sample video files for testing drag and drop.

    Args:
        tmp_path: Pytest's temporary path fixture.

    Returns:
        List of paths to sample video files.
    """
    video_files = []
    extensions = [".mp4", ".mov", ".avi", ".mkv"]

    for i, ext in enumerate(extensions):
        video_file = tmp_path / f"sample_video_{i}{ext}"
        video_file.write_bytes(b"\x00" * 1024)  # Create dummy file
        video_files.append(video_file)

    return video_files


@pytest.fixture
def sample_folder_with_videos(tmp_path: Path) -> Path:
    """Create a folder containing sample video files.

    Args:
        tmp_path: Pytest's temporary path fixture.

    Returns:
        Path to the folder containing video files.
    """
    video_folder = tmp_path / "videos"
    video_folder.mkdir()

    for i in range(5):
        video_file = video_folder / f"video_{i}.mp4"
        video_file.write_bytes(b"\x00" * 1024)

    # Add a non-video file that should be ignored
    text_file = video_folder / "readme.txt"
    text_file.write_text("This is not a video")

    return video_folder


@pytest.fixture
def mock_orchestrator() -> Generator[MagicMock, None, None]:
    """Provide a mock orchestrator for conversion tests.

    Yields:
        MagicMock: Mock Orchestrator instance.
    """
    with patch("video_converter.core.orchestrator.Orchestrator") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        # Configure mock result
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.original_size = 1000000
        mock_result.converted_size = 500000
        mock_result.error_message = None

        mock_instance.convert_single.return_value = mock_result
        yield mock_instance


@pytest.fixture
def app_with_mocked_services(
    qtbot: QtBot,
    mock_conversion_service: MagicMock,
    mock_photos_service: MagicMock,
    mock_settings_manager: MagicMock,
):
    """Create main window with mocked services for testing.

    This fixture creates a MainWindow with all services mocked,
    suitable for testing UI interactions without backend calls.

    Args:
        qtbot: pytest-qt's QtBot fixture.
        mock_conversion_service: Mock conversion service.
        mock_photos_service: Mock photos service.
        mock_settings_manager: Mock settings manager.

    Yields:
        MainWindow instance with mocked services.
    """
    from video_converter.gui.main_window import MainWindow

    with patch(
        "video_converter.gui.main_window.ConversionService",
        return_value=mock_conversion_service,
    ), patch(
        "video_converter.gui.main_window.PhotosService",
        return_value=mock_photos_service,
    ), patch(
        "video_converter.gui.main_window.SettingsManager",
        return_value=mock_settings_manager,
    ):
        window = MainWindow()
        qtbot.addWidget(window)
        yield window
        window.close()
