"""Utility modules for video converter.

This package provides common utilities used across the video converter.

SDS Reference: SDS-U01
"""

from video_converter.utils.command_runner import (
    CommandExecutionError,
    CommandNotFoundError,
    CommandResult,
    CommandRunner,
    CommandTimeoutError,
    ExifToolRunner,
    FFprobeRunner,
    run_command,
    run_exiftool,
    run_ffprobe,
)
from video_converter.utils.dependency_checker import (
    DependencyChecker,
    DependencyCheckResult,
    DependencyInfo,
    DependencyStatus,
    compare_versions,
)
from video_converter.utils.progress_parser import (
    FFmpegProgress,
    FFmpegProgressParser,
)

__all__ = [
    # Command execution
    "CommandResult",
    "CommandRunner",
    "CommandNotFoundError",
    "CommandExecutionError",
    "CommandTimeoutError",
    # Specialized runners
    "FFprobeRunner",
    "ExifToolRunner",
    # Convenience functions
    "run_command",
    "run_ffprobe",
    "run_exiftool",
    # Dependency checking
    "DependencyChecker",
    "DependencyCheckResult",
    "DependencyInfo",
    "DependencyStatus",
    "compare_versions",
    # Progress parsing
    "FFmpegProgress",
    "FFmpegProgressParser",
]
