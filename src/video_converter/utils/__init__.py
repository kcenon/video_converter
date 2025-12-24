"""Utility modules for video converter.

This package provides common utilities used across the video converter.

SDS Reference: SDS-U01
"""

from video_converter.utils.applescript import (
    AppleScriptError,
    AppleScriptExecutionError,
    AppleScriptResult,
    AppleScriptRunner,
    AppleScriptTimeoutError,
    escape_applescript_string,
)
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
from video_converter.utils.progress_parser import (
    FFmpegProgress,
    FFmpegProgressParser,
)
from video_converter.utils.constants import (
    # Size units
    BYTES_PER_KB,
    BYTES_PER_MB,
    BYTES_PER_GB,
    # Time units
    SECONDS_PER_MINUTE,
    SECONDS_PER_HOUR,
    # Timeouts
    ICLOUD_DOWNLOAD_TIMEOUT,
    FFMPEG_PROCESS_TIMEOUT,
    SUBPROCESS_DEFAULT_TIMEOUT,
    VMAF_ANALYSIS_TIMEOUT,
    VMAF_QUICK_TIMEOUT,
    ICLOUD_POLL_INTERVAL,
    # Quality settings
    HARDWARE_MIN_QUALITY,
    HARDWARE_MAX_QUALITY,
    DEFAULT_QUALITY,
    SOFTWARE_MIN_CRF,
    SOFTWARE_MAX_CRF,
    DEFAULT_CRF,
    # VMAF thresholds
    VMAF_THRESHOLD_VISUALLY_LOSSLESS,
    VMAF_THRESHOLD_HIGH_QUALITY,
    VMAF_THRESHOLD_GOOD_QUALITY,
    VMAF_DEFAULT_SAMPLE_INTERVAL,
    VMAF_DEFAULT_THREADS,
    VMAF_DEFAULT_RESOLUTION,
    # Encoding presets
    ENCODING_PRESETS,
    DEFAULT_PRESET,
    CLI_PRESETS,
    SUPPORTED_BIT_DEPTHS,
    DEFAULT_BIT_DEPTH,
    # File system
    VIDEO_EXTENSIONS,
    HEVC_EXTENSIONS,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PROCESSED_DIR,
    DEFAULT_FAILED_DIR,
    ICLOUD_STUB_PREFIX,
    ICLOUD_STUB_SUFFIX,
    # Processing
    MAX_CONCURRENT_CONVERSIONS,
    MIN_CONCURRENT_CONVERSIONS,
    DEFAULT_CONCURRENT_CONVERSIONS,
    MIN_FREE_DISK_SPACE,
    DEFAULT_MIN_FREE_SPACE_GB,
    # Helper functions
    bytes_to_human,
    format_duration,
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
    # Constants - Size units
    "BYTES_PER_KB",
    "BYTES_PER_MB",
    "BYTES_PER_GB",
    # Constants - Time units
    "SECONDS_PER_MINUTE",
    "SECONDS_PER_HOUR",
    # Constants - Timeouts
    "ICLOUD_DOWNLOAD_TIMEOUT",
    "FFMPEG_PROCESS_TIMEOUT",
    "SUBPROCESS_DEFAULT_TIMEOUT",
    "VMAF_ANALYSIS_TIMEOUT",
    "VMAF_QUICK_TIMEOUT",
    "ICLOUD_POLL_INTERVAL",
    # Constants - Quality settings
    "HARDWARE_MIN_QUALITY",
    "HARDWARE_MAX_QUALITY",
    "DEFAULT_QUALITY",
    "SOFTWARE_MIN_CRF",
    "SOFTWARE_MAX_CRF",
    "DEFAULT_CRF",
    # Constants - VMAF thresholds
    "VMAF_THRESHOLD_VISUALLY_LOSSLESS",
    "VMAF_THRESHOLD_HIGH_QUALITY",
    "VMAF_THRESHOLD_GOOD_QUALITY",
    "VMAF_DEFAULT_SAMPLE_INTERVAL",
    "VMAF_DEFAULT_THREADS",
    "VMAF_DEFAULT_RESOLUTION",
    # Constants - Encoding presets
    "ENCODING_PRESETS",
    "DEFAULT_PRESET",
    "CLI_PRESETS",
    "SUPPORTED_BIT_DEPTHS",
    "DEFAULT_BIT_DEPTH",
    # Constants - File system
    "VIDEO_EXTENSIONS",
    "HEVC_EXTENSIONS",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_PROCESSED_DIR",
    "DEFAULT_FAILED_DIR",
    "ICLOUD_STUB_PREFIX",
    "ICLOUD_STUB_SUFFIX",
    # Constants - Processing
    "MAX_CONCURRENT_CONVERSIONS",
    "MIN_CONCURRENT_CONVERSIONS",
    "DEFAULT_CONCURRENT_CONVERSIONS",
    "MIN_FREE_DISK_SPACE",
    "DEFAULT_MIN_FREE_SPACE_GB",
    # Constants - Helper functions
    "bytes_to_human",
    "format_duration",
]
