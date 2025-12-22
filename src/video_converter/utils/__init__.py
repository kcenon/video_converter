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
from video_converter.utils.file_utils import (
    AtomicWriteError,
    InsufficientSpaceError,
    atomic_write,
    check_disk_space,
    cleanup_temp_files,
    create_temp_directory,
    ensure_directory,
    ensure_disk_space,
    expand_path,
    format_size,
    generate_output_path,
    get_directory_size,
    get_file_size,
    get_temp_dir,
    get_temp_path,
    is_video_file,
    parse_size,
    safe_copy,
    safe_delete,
    safe_move,
)
from video_converter.utils.applescript import (
    AppleScriptError,
    AppleScriptExecutionError,
    AppleScriptResult,
    AppleScriptRunner,
    AppleScriptTimeoutError,
    escape_applescript_string,
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
    # File utilities - Exceptions
    "InsufficientSpaceError",
    "AtomicWriteError",
    # File utilities - Path functions
    "expand_path",
    "ensure_directory",
    "generate_output_path",
    # File utilities - Size functions
    "format_size",
    "parse_size",
    "get_file_size",
    "get_directory_size",
    # File utilities - Temp file functions
    "get_temp_dir",
    "get_temp_path",
    "create_temp_directory",
    "cleanup_temp_files",
    # File utilities - Disk space functions
    "check_disk_space",
    "ensure_disk_space",
    # File utilities - File operations
    "safe_move",
    "safe_copy",
    "safe_delete",
    "atomic_write",
    # File utilities - File checks
    "is_video_file",
    # Progress parsing
    "FFmpegProgress",
    "FFmpegProgressParser",
    # AppleScript execution
    "AppleScriptRunner",
    "AppleScriptResult",
    "AppleScriptError",
    "AppleScriptExecutionError",
    "AppleScriptTimeoutError",
    "escape_applescript_string",
]
