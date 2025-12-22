"""Real-time conversion progress monitoring module.

This module provides real-time progress monitoring for FFmpeg video conversions,
including accurate progress tracking, ETA calculation, and callback-based updates.

SDS Reference: SDS-V01-005
SRS Reference: SRS-205 (Real-time Progress Monitoring)

Example:
    >>> from video_converter.converters.progress import ProgressMonitor, ProgressInfo
    >>>
    >>> def on_progress(info: ProgressInfo) -> None:
    ...     print(f"Progress: {info.percentage:.1f}% | ETA: {info.eta_formatted}")
    >>>
    >>> monitor = ProgressMonitor(total_duration=180.5, callback=on_progress)
    >>> monitor.on_output("frame=  720 fps=180 time=00:00:24.00 speed=6.0x")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class ProgressInfo:
    """Progress information for video conversion.

    This dataclass contains all progress metrics extracted from FFmpeg output,
    including calculated properties for percentage and ETA.

    Attributes:
        frame: Current frame number being processed.
        fps: Encoding frames per second.
        current_time: Current position in seconds.
        total_time: Total video duration in seconds.
        current_size: Current output file size in bytes.
        bitrate: Current encoding bitrate in kbps.
        speed: Encoding speed multiplier (e.g., 6.0 means 6x realtime).
        quality: FFmpeg quality parameter (q value).
    """

    frame: int = 0
    fps: float = 0.0
    current_time: float = 0.0
    total_time: float = 0.0
    current_size: int = 0
    bitrate: float = 0.0
    speed: float = 0.0
    quality: float = 0.0

    @property
    def percentage(self) -> float:
        """Calculate completion percentage.

        Returns:
            Completion percentage from 0.0 to 100.0.
        """
        if self.total_time <= 0:
            return 0.0
        return min(100.0, (self.current_time / self.total_time) * 100)

    @property
    def eta_seconds(self) -> float:
        """Calculate estimated time remaining in seconds.

        Returns:
            Estimated seconds remaining, or infinity if speed is zero.
        """
        if self.speed <= 0:
            return float("inf")
        remaining_time = self.total_time - self.current_time
        if remaining_time <= 0:
            return 0.0
        return remaining_time / self.speed

    @property
    def eta_formatted(self) -> str:
        """Get human-readable ETA string.

        Returns:
            Formatted ETA string like "1h 30m", "5m 30s", or "calculating...".
        """
        seconds = self.eta_seconds
        if seconds == float("inf"):
            return "calculating..."
        if seconds <= 0:
            return "0s"

        total_seconds = int(seconds)
        minutes, secs = divmod(total_seconds, 60)
        hours, mins = divmod(minutes, 60)

        if hours > 0:
            return f"{hours}h {mins}m"
        elif mins > 0:
            return f"{mins}m {secs}s"
        return f"{secs}s"

    @property
    def size_formatted(self) -> str:
        """Get human-readable current size string.

        Returns:
            Formatted size string like "1.5 GB", "256 MB", or "0 B".
        """
        if self.current_size <= 0:
            return "0 B"

        size = float(self.current_size)
        for unit in ("B", "KB", "MB", "GB"):
            if abs(size) < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class ProgressParser:
    """Parser for FFmpeg stderr progress output.

    This parser extracts real-time progress information from FFmpeg's stderr,
    converting it into ProgressInfo objects for further processing.

    Attributes:
        total_duration: Total video duration in seconds.
    """

    # Regex patterns for extracting FFmpeg progress components
    _FRAME_PATTERN = re.compile(r"frame=\s*(\d+)")
    _FPS_PATTERN = re.compile(r"fps=\s*([\d.]+)")
    _QUALITY_PATTERN = re.compile(r"q=\s*([\d.-]+)")
    _SIZE_PATTERN = re.compile(r"size=\s*(\d+)kB")
    _TIME_PATTERN = re.compile(r"time=(\d+):(\d+):(\d+)\.(\d+)")
    _BITRATE_PATTERN = re.compile(r"bitrate=\s*([\d.]+)kbits/s")
    _SPEED_PATTERN = re.compile(r"speed=\s*([\d.]+)x")

    def __init__(self, total_duration: float = 0.0) -> None:
        """Initialize the progress parser.

        Args:
            total_duration: Total video duration in seconds.
                           Used for percentage and ETA calculations.
        """
        self.total_duration = max(0.0, total_duration)
        self._last_info: ProgressInfo | None = None

    def parse_line(self, line: str) -> ProgressInfo | None:
        """Parse a single line of FFmpeg stderr output.

        Args:
            line: A line from FFmpeg's stderr output.

        Returns:
            ProgressInfo object if progress data was found, None otherwise.
        """
        # Quick check for progress-related content
        if "frame=" not in line or "time=" not in line:
            return None

        info = ProgressInfo(total_time=self.total_duration)

        # Parse frame count
        if match := self._FRAME_PATTERN.search(line):
            info.frame = int(match.group(1))

        # Parse FPS
        if match := self._FPS_PATTERN.search(line):
            info.fps = float(match.group(1))

        # Parse quality
        if match := self._QUALITY_PATTERN.search(line):
            info.quality = float(match.group(1))

        # Parse current output size (convert from kB to bytes)
        if match := self._SIZE_PATTERN.search(line):
            info.current_size = int(match.group(1)) * 1024

        # Parse current time position
        if match := self._TIME_PATTERN.search(line):
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            centiseconds = int(match.group(4))
            info.current_time = (
                hours * 3600 + minutes * 60 + seconds + centiseconds / 100
            )

        # Parse bitrate
        if match := self._BITRATE_PATTERN.search(line):
            info.bitrate = float(match.group(1))

        # Parse encoding speed
        if match := self._SPEED_PATTERN.search(line):
            info.speed = float(match.group(1))

        self._last_info = info
        return info

    @property
    def last_info(self) -> ProgressInfo | None:
        """Get the most recently parsed progress info.

        Returns:
            The last ProgressInfo parsed, or None if nothing parsed yet.
        """
        return self._last_info


@dataclass
class ProgressMonitor:
    """Monitor and report FFmpeg conversion progress.

    This class combines parsing and callback functionality to provide
    a complete progress monitoring solution. It handles debouncing,
    minimum update intervals, and error handling.

    Attributes:
        total_duration: Total video duration in seconds.
        callback: Function to call with progress updates.
        min_interval: Minimum seconds between callback invocations.
    """

    total_duration: float
    callback: Callable[[ProgressInfo], None]
    min_interval: float = 0.1
    _parser: ProgressParser = field(init=False, repr=False)
    _last_callback_time: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize the parser after dataclass initialization."""
        self._parser = ProgressParser(self.total_duration)

    def on_output(self, line: str) -> None:
        """Process a line of FFmpeg output.

        This method parses the line and invokes the callback if new
        progress information is available and enough time has passed
        since the last callback.

        Args:
            line: A line from FFmpeg's stderr output.
        """
        import time

        info = self._parser.parse_line(line)
        if info is None:
            return

        current_time = time.monotonic()
        if current_time - self._last_callback_time >= self.min_interval:
            self._last_callback_time = current_time
            try:
                self.callback(info)
            except Exception:
                # Swallow callback exceptions to prevent conversion interruption
                pass

    def get_current_progress(self) -> ProgressInfo | None:
        """Get the current progress without triggering a callback.

        Returns:
            The most recent ProgressInfo, or None if not available.
        """
        return self._parser.last_info

    def force_callback(self) -> None:
        """Force a callback with current progress, ignoring interval.

        Useful for final progress update at 100% completion.
        """
        if info := self._parser.last_info:
            try:
                self.callback(info)
            except Exception:
                pass


def create_simple_callback(
    show_bar: bool = True, bar_width: int = 30
) -> Callable[[ProgressInfo], None]:
    """Create a simple console progress callback.

    Args:
        show_bar: Whether to show a visual progress bar.
        bar_width: Width of the progress bar in characters.

    Returns:
        A callback function suitable for ProgressMonitor.

    Example:
        >>> callback = create_simple_callback()
        >>> monitor = ProgressMonitor(duration, callback)
    """

    def callback(info: ProgressInfo) -> None:
        if show_bar:
            filled = int(info.percentage / 100 * bar_width)
            bar = "\u2588" * filled + "\u2591" * (bar_width - filled)
            print(
                f"\r[{bar}] {info.percentage:.1f}% | "
                f"{info.size_formatted} | "
                f"ETA: {info.eta_formatted} | "
                f"{info.speed:.1f}x",
                end="",
                flush=True,
            )
        else:
            print(
                f"\rProgress: {info.percentage:.1f}% | ETA: {info.eta_formatted}",
                end="",
                flush=True,
            )

    return callback
