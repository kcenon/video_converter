"""Shared pytest fixtures for video_converter tests.

This module provides common fixtures used across all test modules,
including mock configurations, temporary directories, and mock
external command execution.

Example:
    def test_with_temp_dir(temp_dir):
        test_file = temp_dir / "test.txt"
        test_file.write_text("hello")
        assert test_file.exists()

    def test_with_mock_config(mock_config):
        assert mock_config.encoding.mode == "hardware"
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from video_converter.core.config import Config

if TYPE_CHECKING:
    from collections.abc import Generator


@dataclass
class MockCommandResult:
    """Mock result for command execution.

    Attributes:
        returncode: Exit code (0 = success).
        stdout: Standard output.
        stderr: Standard error output.
    """

    returncode: int = 0
    stdout: str = ""
    stderr: str = ""

    @property
    def success(self) -> bool:
        """Check if command completed successfully."""
        return self.returncode == 0


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for test files.

    This fixture wraps pytest's tmp_path to provide a clean temporary
    directory that is automatically cleaned up after each test.

    Args:
        tmp_path: Pytest's built-in temporary path fixture.

    Returns:
        Path: Temporary directory path.
    """
    return tmp_path


@pytest.fixture
def mock_config_data() -> dict:
    """Provide sample configuration data for testing.

    Returns:
        dict: Configuration dictionary with test values.
    """
    return {
        "version": "0.1.0.0",
        "encoding": {
            "mode": "hardware",
            "quality": 45,
            "crf": 22,
            "preset": "medium",
        },
        "paths": {
            "output": "/tmp/video_converter_test/output",
        },
        "automation": {
            "enabled": False,
            "schedule": "daily",
            "time": "03:00",
        },
        "photos": {
            "include_albums": [],
            "exclude_albums": ["Screenshots"],
            "download_from_icloud": True,
            "icloud_timeout": 3600,
            "skip_cloud_only": False,
        },
        "processing": {
            "max_concurrent": 2,
            "validate_quality": True,
            "preserve_original": True,
        },
        "notification": {
            "on_complete": True,
            "on_error": True,
            "daily_summary": False,
        },
    }


@pytest.fixture
def mock_config_file(temp_dir: Path, mock_config_data: dict) -> Path:
    """Create a temporary config file for testing.

    Args:
        temp_dir: Temporary directory fixture.
        mock_config_data: Configuration data fixture.

    Returns:
        Path: Path to the created config file.
    """
    config_path = temp_dir / "config.json"
    config_path.write_text(json.dumps(mock_config_data, indent=2))
    return config_path


@pytest.fixture
def mock_config(mock_config_file: Path) -> Generator[Config, None, None]:
    """Provide a mock configuration instance for testing.

    This fixture creates a Config instance from a temporary config file
    and ensures the singleton is reset after the test.

    Args:
        mock_config_file: Path to temporary config file.

    Yields:
        Config: Configuration instance for testing.
    """
    Config.reset()
    config = Config.load()
    yield config
    Config.reset()


@pytest.fixture
def mock_ffmpeg(mocker):
    """Mock FFmpeg command execution.

    This fixture prevents actual FFmpeg execution during tests by mocking
    the command runner module.

    Args:
        mocker: pytest-mock's mocker fixture.

    Returns:
        MagicMock: The mocked run_command function.
    """
    return mocker.patch(
        "video_converter.utils.command_runner.run_command",
        return_value=MockCommandResult(returncode=0, stdout="ffmpeg version 6.1"),
    )


@pytest.fixture
def mock_ffprobe(mocker):
    """Mock FFprobe command execution for media analysis.

    Args:
        mocker: pytest-mock's mocker fixture.

    Returns:
        MagicMock: The mocked run_command function.
    """
    probe_output = json.dumps(
        {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "duration": "120.0",
                }
            ],
            "format": {
                "duration": "120.0",
                "size": "100000000",
                "bit_rate": "6666666",
            },
        }
    )
    return mocker.patch(
        "video_converter.utils.command_runner.run_command",
        return_value=MockCommandResult(returncode=0, stdout=probe_output),
    )


@pytest.fixture
def mock_exiftool(mocker):
    """Mock ExifTool command execution for metadata operations.

    Args:
        mocker: pytest-mock's mocker fixture.

    Returns:
        MagicMock: The mocked run_command function.
    """
    return mocker.patch(
        "video_converter.utils.command_runner.run_command",
        return_value=MockCommandResult(returncode=0, stdout="ExifTool Version: 12.76"),
    )


@pytest.fixture
def sample_video_path(temp_dir: Path) -> Path:
    """Create a dummy video file path for testing.

    Note: This does not create an actual video file, just a path.
    For actual video file testing, use the fixtures in tests/fixtures/.

    Args:
        temp_dir: Temporary directory fixture.

    Returns:
        Path: Path to a dummy video file location.
    """
    video_path = temp_dir / "sample_video.mp4"
    # Create an empty file as a placeholder
    video_path.touch()
    return video_path


@pytest.fixture
def sample_h264_metadata() -> dict:
    """Provide sample H.264 video metadata.

    Returns:
        dict: Metadata dictionary for H.264 video.
    """
    return {
        "codec_name": "h264",
        "codec_long_name": "H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10",
        "profile": "High",
        "width": 1920,
        "height": 1080,
        "duration": "120.5",
        "bit_rate": "5000000",
    }


@pytest.fixture
def sample_h265_metadata() -> dict:
    """Provide sample H.265 video metadata.

    Returns:
        dict: Metadata dictionary for H.265 video.
    """
    return {
        "codec_name": "hevc",
        "codec_long_name": "H.265 / HEVC (High Efficiency Video Coding)",
        "profile": "Main",
        "width": 1920,
        "height": 1080,
        "duration": "120.5",
        "bit_rate": "2500000",
    }


@pytest.fixture
def mock_osxphotos() -> Generator[MagicMock, None, None]:
    """Mock osxphotos module for Photos library tests.

    This fixture handles the lazy import of osxphotos by injecting
    a mock module into sys.modules before tests run.

    Yields:
        MagicMock: The mocked osxphotos module.
    """
    mock_module = MagicMock()
    mock_db = MagicMock()
    mock_db.library_path = "/Users/test/Pictures/Photos Library.photoslibrary"
    mock_module.PhotosDB.return_value = mock_db

    # Store original module if it exists
    original = sys.modules.get("osxphotos")

    # Inject mock into sys.modules
    sys.modules["osxphotos"] = mock_module

    yield mock_module

    # Restore original module
    if original is not None:
        sys.modules["osxphotos"] = original
    else:
        del sys.modules["osxphotos"]
