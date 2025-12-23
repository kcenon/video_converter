"""FFmpeg progress parsing utilities.

This module provides utilities for parsing FFmpeg stderr output
to extract progress information during video conversion.

SDS Reference: SDS-U01-002
SRS Reference: SRS-205 (Real-time Progress Monitoring)

Example:
    >>> parser = FFmpegProgressParser(total_duration=120.0)
    >>> progress = parser.parse_line(
    ...     "frame=  720 fps=180 q=32.0 size=   15360kB "
    ...     "time=00:00:24.00 bitrate=5242.9kbits/s speed=6.0x"
    ... )
    >>> print(f"Progress: {progress.percentage:.1f}%")
    Progress: 20.0%
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class FFmpegProgress:
    """Progress information extracted from FFmpeg output.

    Attributes:
        frame: Current frame number.
        fps: Frames per second being processed.
        quality: Quality value (q parameter).
        size_kb: Current output size in kilobytes.
        time_seconds: Current position in seconds.
        bitrate_kbps: Current bitrate in kbits/s.
        speed: Encoding speed multiplier (e.g., 6.0 means 6x realtime).
        percentage: Progress percentage (0.0-100.0).
    """

    frame: int = 0
    fps: float = 0.0
    quality: float = 0.0
    size_kb: int = 0
    time_seconds: float = 0.0
    bitrate_kbps: float = 0.0
    speed: float = 0.0
    percentage: float = 0.0


class FFmpegProgressParser:
    """Parser for FFmpeg stderr progress output.

    This parser extracts progress information from FFmpeg's stderr output,
    which includes frame count, time position, speed, and other metrics.

    Attributes:
        total_duration: Total duration of the video in seconds.
    """

    # Regex patterns for extracting progress components
    _FRAME_PATTERN = re.compile(r"frame=\s*(\d+)")
    _FPS_PATTERN = re.compile(r"fps=\s*([\d.]+)")
    _QUALITY_PATTERN = re.compile(r"q=\s*([\d.]+)")
    _SIZE_PATTERN = re.compile(r"size=\s*(\d+)kB")
    _TIME_PATTERN = re.compile(r"time=(\d+):(\d+):(\d+)\.(\d+)")
    _BITRATE_PATTERN = re.compile(r"bitrate=\s*([\d.]+)kbits/s")
    _SPEED_PATTERN = re.compile(r"speed=\s*([\d.]+)x")

    def __init__(self, total_duration: float = 0.0) -> None:
        """Initialize the progress parser.

        Args:
            total_duration: Total duration of the video in seconds.
                           Used to calculate percentage progress.
        """
        self.total_duration = max(0.0, total_duration)
        self._last_progress = FFmpegProgress()

    def parse_line(self, line: str) -> FFmpegProgress | None:
        """Parse a single line of FFmpeg stderr output.

        Args:
            line: A line from FFmpeg's stderr output.

        Returns:
            FFmpegProgress object if progress info was found, None otherwise.
        """
        if "frame=" not in line or "time=" not in line:
            return None

        progress = FFmpegProgress()

        # Parse frame
        if match := self._FRAME_PATTERN.search(line):
            progress.frame = int(match.group(1))

        # Parse FPS
        if match := self._FPS_PATTERN.search(line):
            progress.fps = float(match.group(1))

        # Parse quality
        if match := self._QUALITY_PATTERN.search(line):
            progress.quality = float(match.group(1))

        # Parse size
        if match := self._SIZE_PATTERN.search(line):
            progress.size_kb = int(match.group(1))

        # Parse time
        if match := self._TIME_PATTERN.search(line):
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            centiseconds = int(match.group(4))
            progress.time_seconds = hours * 3600 + minutes * 60 + seconds + centiseconds / 100

        # Parse bitrate
        if match := self._BITRATE_PATTERN.search(line):
            progress.bitrate_kbps = float(match.group(1))

        # Parse speed
        if match := self._SPEED_PATTERN.search(line):
            progress.speed = float(match.group(1))

        # Calculate percentage
        if self.total_duration > 0 and progress.time_seconds > 0:
            progress.percentage = min(100.0, (progress.time_seconds / self.total_duration) * 100)

        self._last_progress = progress
        return progress

    def get_last_progress(self) -> FFmpegProgress:
        """Get the last parsed progress.

        Returns:
            The most recently parsed progress, or empty progress if none parsed.
        """
        return self._last_progress

    @staticmethod
    def parse_time_to_seconds(time_str: str) -> float:
        """Parse FFmpeg time string to seconds.

        Args:
            time_str: Time string in format HH:MM:SS.cs or similar.

        Returns:
            Time in seconds.
        """
        pattern = re.compile(r"(\d+):(\d+):(\d+)\.?(\d*)")
        if match := pattern.match(time_str):
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            centiseconds = int(match.group(4)) if match.group(4) else 0
            return hours * 3600 + minutes * 60 + seconds + centiseconds / 100
        return 0.0
