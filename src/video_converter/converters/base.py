"""Base converter interface for video encoding.

This module defines the abstract base class for all video converters,
establishing a consistent interface for hardware and software encoders.

SDS Reference: SDS-V01-001
SRS Reference: SRS-201 (H.265 Encoding)

Example:
    >>> from video_converter.converters.base import BaseConverter
    >>> from video_converter.core import ConversionRequest, ConversionMode
    >>>
    >>> class MyConverter(BaseConverter):
    ...     def build_command(self, request: ConversionRequest) -> list[str]:
    ...         return ["ffmpeg", "-i", str(request.input_path), ...]
    ...
    >>> converter = MyConverter()
    >>> request = ConversionRequest(
    ...     input_path=Path("input.mov"),
    ...     output_path=Path("output.mp4"),
    ... )
    >>> result = await converter.convert(request)
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from video_converter.converters.progress import ProgressInfo, ProgressParser
from video_converter.core.types import (
    ConversionMode,
    ConversionRequest,
    ConversionResult,
)
from video_converter.utils.command_runner import (
    CommandNotFoundError,
    CommandRunner,
    FFprobeRunner,
)

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class ConversionError(Exception):
    """Exception raised when video conversion fails."""

    pass


class EncoderNotAvailableError(ConversionError):
    """Exception raised when the required encoder is not available."""

    pass


class BaseConverter(ABC):
    """Abstract base class for video converters.

    This class defines the interface that all video converters must implement.
    It provides common functionality for command execution and progress tracking.

    Attributes:
        mode: The conversion mode (hardware or software).
    """

    def __init__(self, mode: ConversionMode) -> None:
        """Initialize the converter.

        Args:
            mode: The conversion mode to use.
        """
        self.mode = mode
        self._command_runner = CommandRunner()
        self._ffprobe_runner = FFprobeRunner(self._command_runner)
        self._cancelled = False
        self._current_process: asyncio.subprocess.Process | None = None

    @property
    @abstractmethod
    def encoder_name(self) -> str:
        """Get the encoder name for FFmpeg.

        Returns:
            The encoder name (e.g., "hevc_videotoolbox", "libx265").
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this encoder is available on the system.

        Returns:
            True if the encoder is available, False otherwise.
        """
        ...

    @abstractmethod
    def build_command(self, request: ConversionRequest) -> list[str]:
        """Build the FFmpeg command for conversion.

        Args:
            request: The conversion request with input/output paths and settings.

        Returns:
            List of command arguments for FFmpeg.
        """
        ...

    def _get_video_duration(self, path: Path) -> float:
        """Get video duration in seconds using ffprobe.

        Args:
            path: Path to the video file.

        Returns:
            Duration in seconds, or 0.0 if cannot be determined.
        """
        try:
            info = self._ffprobe_runner.probe(path, show_streams=False)
            if "format" in info and "duration" in info["format"]:
                return float(info["format"]["duration"])
        except Exception as e:
            logger.debug(f"Could not get video duration: {e}")
        return 0.0

    async def convert(
        self,
        request: ConversionRequest,
        on_progress: Callable[[float], None] | None = None,
        on_progress_info: Callable[[ProgressInfo], None] | None = None,
    ) -> ConversionResult:
        """Convert a video file.

        Args:
            request: The conversion request.
            on_progress: Optional callback for simple progress updates (0.0-1.0).
            on_progress_info: Optional callback for detailed progress updates
                             with ProgressInfo containing ETA and other metrics.

        Returns:
            ConversionResult with success status and statistics.

        Raises:
            ConversionError: If conversion fails.
            EncoderNotAvailableError: If the encoder is not available.

        Note:
            If both callbacks are provided, both will be called.
            on_progress_info provides more detailed information including
            eta_seconds, eta_formatted, and current encoding speed.
        """
        self._cancelled = False
        started_at = datetime.now()
        start_time = time.perf_counter()

        # Validate encoder availability
        if not self.is_available():
            return ConversionResult(
                success=False,
                request=request,
                error_message=f"Encoder '{self.encoder_name}' is not available",
                started_at=started_at,
                completed_at=datetime.now(),
            )

        # Get original file size
        try:
            original_size = request.input_path.stat().st_size
        except OSError as e:
            return ConversionResult(
                success=False,
                request=request,
                error_message=f"Cannot read input file: {e}",
                started_at=started_at,
                completed_at=datetime.now(),
            )

        # Get video duration for progress calculation
        video_duration = self._get_video_duration(request.input_path)
        progress_parser = ProgressParser(total_duration=video_duration)

        # Ensure output directory exists
        request.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build and execute command
        command = self.build_command(request)
        logger.info(f"Starting conversion: {request.input_path.name}")
        logger.debug(f"Command: {' '.join(command)}")

        stderr_output = []
        last_speed = 0.0

        try:
            # Create subprocess with stderr streaming
            self._current_process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Read stderr line by line for progress updates
            while True:
                if self._current_process.stderr is None:
                    break

                line = await self._current_process.stderr.readline()
                if not line:
                    break

                line_str = line.decode("utf-8", errors="replace")
                stderr_output.append(line_str)

                # Parse progress from FFmpeg output
                if progress_info := progress_parser.parse_line(line_str):
                    last_speed = progress_info.speed
                    # Call detailed progress callback with ProgressInfo
                    if on_progress_info:
                        try:
                            on_progress_info(progress_info)
                        except Exception:
                            pass  # Swallow callback errors
                    # Call simple progress callback with ratio (0.0-1.0)
                    if on_progress and video_duration > 0:
                        on_progress(progress_info.percentage / 100.0)

            # Wait for process to complete
            await self._current_process.wait()

            if self._cancelled:
                # Clean up partial output
                if request.output_path.exists():
                    request.output_path.unlink()
                return ConversionResult(
                    success=False,
                    request=request,
                    original_size=original_size,
                    error_message="Conversion cancelled",
                    started_at=started_at,
                    completed_at=datetime.now(),
                )

            if self._current_process.returncode != 0:
                error_msg = "".join(stderr_output).strip()
                # Clean up partial output
                if request.output_path.exists():
                    request.output_path.unlink()
                return ConversionResult(
                    success=False,
                    request=request,
                    original_size=original_size,
                    error_message=f"FFmpeg failed: {error_msg[-500:]}",
                    started_at=started_at,
                    completed_at=datetime.now(),
                )

            # Get converted file size
            if not request.output_path.exists():
                return ConversionResult(
                    success=False,
                    request=request,
                    original_size=original_size,
                    error_message="Output file was not created",
                    started_at=started_at,
                    completed_at=datetime.now(),
                )

            converted_size = request.output_path.stat().st_size
            duration = time.perf_counter() - start_time

            # Calculate speed ratio from FFmpeg's reported speed or actual time
            speed_ratio = last_speed
            if speed_ratio == 0.0 and video_duration > 0 and duration > 0:
                speed_ratio = video_duration / duration

            # Call final progress callback
            if on_progress:
                on_progress(1.0)

            logger.info(
                f"Conversion complete: {request.input_path.name} "
                f"({original_size / 1024 / 1024:.1f}MB -> "
                f"{converted_size / 1024 / 1024:.1f}MB, "
                f"{(1 - converted_size / original_size) * 100:.1f}% reduction, "
                f"{speed_ratio:.1f}x speed)"
            )

            return ConversionResult(
                success=True,
                request=request,
                original_size=original_size,
                converted_size=converted_size,
                duration_seconds=duration,
                speed_ratio=speed_ratio,
                started_at=started_at,
                completed_at=datetime.now(),
            )

        except CommandNotFoundError as e:
            return ConversionResult(
                success=False,
                request=request,
                original_size=original_size,
                error_message=f"FFmpeg not found: {e}",
                started_at=started_at,
                completed_at=datetime.now(),
            )
        except Exception as e:
            logger.exception(f"Conversion error: {e}")
            # Clean up partial output
            if request.output_path.exists():
                request.output_path.unlink()
            return ConversionResult(
                success=False,
                request=request,
                original_size=original_size,
                error_message=str(e),
                started_at=started_at,
                completed_at=datetime.now(),
            )
        finally:
            self._current_process = None

    def cancel(self) -> None:
        """Cancel the current conversion."""
        self._cancelled = True
        if self._current_process:
            try:
                self._current_process.terminate()
            except ProcessLookupError:
                pass  # Process already terminated

    def convert_sync(
        self,
        request: ConversionRequest,
        on_progress: Callable[[float], None] | None = None,
        on_progress_info: Callable[[ProgressInfo], None] | None = None,
    ) -> ConversionResult:
        """Synchronous wrapper for convert.

        Args:
            request: The conversion request.
            on_progress: Optional callback for simple progress updates (0.0-1.0).
            on_progress_info: Optional callback for detailed progress updates
                             with ProgressInfo containing ETA and other metrics.

        Returns:
            ConversionResult with success status and statistics.
        """
        return asyncio.run(self.convert(request, on_progress, on_progress_info))
