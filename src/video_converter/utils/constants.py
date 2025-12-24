"""Centralized constants for video_converter.

This module contains all magic numbers and default values used
throughout the application. Import from here to ensure consistency.

SDS Reference: SDS-U01-001
SRS Reference: SRS-701 (Constants Management)

Example:
    >>> from video_converter.utils.constants import (
    ...     BYTES_PER_GB,
    ...     DEFAULT_QUALITY,
    ...     VIDEO_EXTENSIONS,
    ... )
    >>> size_gb = file_size / BYTES_PER_GB
    >>> print(f"Quality: {DEFAULT_QUALITY}")
"""

from __future__ import annotations

from pathlib import Path

# =============================================================================
# Size Units (bytes)
# =============================================================================
BYTES_PER_KB = 1024
BYTES_PER_MB = 1024 * 1024
BYTES_PER_GB = 1024 * 1024 * 1024

# =============================================================================
# Time Units (seconds)
# =============================================================================
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600

# =============================================================================
# Timeouts (seconds)
# =============================================================================
ICLOUD_DOWNLOAD_TIMEOUT = 3600  # 1 hour
FFMPEG_PROCESS_TIMEOUT = 600  # 10 minutes
SUBPROCESS_DEFAULT_TIMEOUT = 120  # 2 minutes
VMAF_ANALYSIS_TIMEOUT = 3600.0  # 1 hour for long videos
VMAF_QUICK_TIMEOUT = 300.0  # 5 minutes for quick analysis

# iCloud polling
ICLOUD_POLL_INTERVAL = 1.0  # seconds

# =============================================================================
# Quality Settings
# =============================================================================
# Hardware encoder quality (VideoToolbox)
HARDWARE_MIN_QUALITY = 1
HARDWARE_MAX_QUALITY = 100
DEFAULT_QUALITY = 45

# Software encoder CRF (libx265)
SOFTWARE_MIN_CRF = 0
SOFTWARE_MAX_CRF = 51
DEFAULT_CRF = 22

# CLI-recommended CRF range (narrower for user-friendly defaults)
CLI_MIN_CRF = 18
CLI_MAX_CRF = 28

# =============================================================================
# VMAF Thresholds
# =============================================================================
VMAF_THRESHOLD_VISUALLY_LOSSLESS = 93.0
VMAF_THRESHOLD_HIGH_QUALITY = 80.0
VMAF_THRESHOLD_GOOD_QUALITY = 60.0

# VMAF analysis defaults
VMAF_DEFAULT_SAMPLE_INTERVAL = 30
VMAF_DEFAULT_THREADS = 4
VMAF_DEFAULT_RESOLUTION = (1920, 1080)

# =============================================================================
# Encoding Presets
# =============================================================================
ENCODING_PRESETS = (
    "ultrafast",
    "superfast",
    "veryfast",
    "faster",
    "fast",
    "medium",
    "slow",
    "slower",
    "veryslow",
    "placebo",
)
DEFAULT_PRESET = "medium"

# Simplified presets for CLI
CLI_PRESETS = ("fast", "medium", "slow")

# Bit depth options
SUPPORTED_BIT_DEPTHS = (8, 10)
DEFAULT_BIT_DEPTH = 8

# =============================================================================
# File System
# =============================================================================
VIDEO_EXTENSIONS = frozenset({".mov", ".mp4", ".m4v", ".avi", ".mkv", ".wmv", ".flv", ".webm"})
HEVC_EXTENSIONS = frozenset({".mp4", ".m4v", ".mov", ".mkv"})

# Default paths (unexpanded - use Path.expanduser() when accessing)
DEFAULT_OUTPUT_DIR = Path("~/Videos/Converted")
DEFAULT_PROCESSED_DIR = Path("~/Videos/Processed")
DEFAULT_FAILED_DIR = Path("~/Videos/Failed")

# iCloud stub file markers
ICLOUD_STUB_PREFIX = "."
ICLOUD_STUB_SUFFIX = ".icloud"

# =============================================================================
# Processing
# =============================================================================
MAX_CONCURRENT_CONVERSIONS = 8
MIN_CONCURRENT_CONVERSIONS = 1
DEFAULT_CONCURRENT_CONVERSIONS = 2

# Disk space requirements
MIN_FREE_DISK_SPACE = 1 * BYTES_PER_GB
DEFAULT_MIN_FREE_SPACE_GB = 1.0

# =============================================================================
# Helper Functions
# =============================================================================


def bytes_to_human(size_bytes: int) -> str:
    """Convert bytes to human-readable string.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Formatted size string like "1.50 GB" or "680 MB".

    Example:
        >>> bytes_to_human(1024)
        '1.00 KB'
        >>> bytes_to_human(1024 * 1024 * 1024)
        '1.00 GB'
    """
    if size_bytes >= BYTES_PER_GB:
        return f"{size_bytes / BYTES_PER_GB:.2f} GB"
    elif size_bytes >= BYTES_PER_MB:
        return f"{size_bytes / BYTES_PER_MB:.2f} MB"
    elif size_bytes >= BYTES_PER_KB:
        return f"{size_bytes / BYTES_PER_KB:.2f} KB"
    return f"{size_bytes} B"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted duration string like "3 min 45 sec" or "1 hr 30 min".

    Example:
        >>> format_duration(45)
        '45 sec'
        >>> format_duration(125)
        '2 min 5 sec'
        >>> format_duration(3725)
        '1 hr 2 min'
    """
    if seconds < SECONDS_PER_MINUTE:
        return f"{int(seconds)} sec"
    elif seconds < SECONDS_PER_HOUR:
        mins = int(seconds // SECONDS_PER_MINUTE)
        secs = int(seconds % SECONDS_PER_MINUTE)
        return f"{mins} min {secs} sec"
    else:
        hrs = int(seconds // SECONDS_PER_HOUR)
        mins = int((seconds % SECONDS_PER_HOUR) // SECONDS_PER_MINUTE)
        return f"{hrs} hr {mins} min"


__all__ = [
    # Size units
    "BYTES_PER_KB",
    "BYTES_PER_MB",
    "BYTES_PER_GB",
    # Time units
    "SECONDS_PER_MINUTE",
    "SECONDS_PER_HOUR",
    # Timeouts
    "ICLOUD_DOWNLOAD_TIMEOUT",
    "FFMPEG_PROCESS_TIMEOUT",
    "SUBPROCESS_DEFAULT_TIMEOUT",
    "VMAF_ANALYSIS_TIMEOUT",
    "VMAF_QUICK_TIMEOUT",
    "ICLOUD_POLL_INTERVAL",
    # Quality settings
    "HARDWARE_MIN_QUALITY",
    "HARDWARE_MAX_QUALITY",
    "DEFAULT_QUALITY",
    "SOFTWARE_MIN_CRF",
    "SOFTWARE_MAX_CRF",
    "DEFAULT_CRF",
    "CLI_MIN_CRF",
    "CLI_MAX_CRF",
    # VMAF thresholds
    "VMAF_THRESHOLD_VISUALLY_LOSSLESS",
    "VMAF_THRESHOLD_HIGH_QUALITY",
    "VMAF_THRESHOLD_GOOD_QUALITY",
    "VMAF_DEFAULT_SAMPLE_INTERVAL",
    "VMAF_DEFAULT_THREADS",
    "VMAF_DEFAULT_RESOLUTION",
    # Encoding presets
    "ENCODING_PRESETS",
    "DEFAULT_PRESET",
    "CLI_PRESETS",
    "SUPPORTED_BIT_DEPTHS",
    "DEFAULT_BIT_DEPTH",
    # File system
    "VIDEO_EXTENSIONS",
    "HEVC_EXTENSIONS",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_PROCESSED_DIR",
    "DEFAULT_FAILED_DIR",
    "ICLOUD_STUB_PREFIX",
    "ICLOUD_STUB_SUFFIX",
    # Processing
    "MAX_CONCURRENT_CONVERSIONS",
    "MIN_CONCURRENT_CONVERSIONS",
    "DEFAULT_CONCURRENT_CONVERSIONS",
    "MIN_FREE_DISK_SPACE",
    "DEFAULT_MIN_FREE_SPACE_GB",
    # Helper functions
    "bytes_to_human",
    "format_duration",
]
