"""Hardware video converter using VideoToolbox.

This module implements hardware-accelerated H.265 encoding using macOS
VideoToolbox through FFmpeg's hevc_videotoolbox encoder.

SDS Reference: SDS-V01-002
SRS Reference: SRS-203 (Hardware Encoding)

Example:
    >>> from video_converter.converters.hardware import HardwareConverter
    >>> from video_converter.core import ConversionRequest
    >>>
    >>> converter = HardwareConverter()
    >>> if converter.is_available():
    ...     request = ConversionRequest(
    ...         input_path=Path("input.mov"),
    ...         output_path=Path("output.mp4"),
    ...     )
    ...     result = await converter.convert(request)
    ...     print(f"Success: {result.success}")
"""

from __future__ import annotations

import logging
import subprocess

from video_converter.converters.base import BaseConverter
from video_converter.core.types import ConversionMode, ConversionRequest

logger = logging.getLogger(__name__)


class HardwareConverter(BaseConverter):
    """Hardware-accelerated H.265 converter using VideoToolbox.

    This converter uses Apple's VideoToolbox framework through FFmpeg
    for fast, hardware-accelerated H.265 encoding on macOS.

    Attributes:
        mode: Always HARDWARE for this converter.
    """

    # VideoToolbox quality range: 1-100 (higher = better quality)
    MIN_QUALITY = 1
    MAX_QUALITY = 100
    DEFAULT_QUALITY = 45

    def __init__(self) -> None:
        """Initialize the hardware converter."""
        super().__init__(ConversionMode.HARDWARE)
        self._encoder_available: bool | None = None

    @property
    def encoder_name(self) -> str:
        """Get the encoder name.

        Returns:
            The VideoToolbox HEVC encoder name.
        """
        return "hevc_videotoolbox"

    def is_available(self) -> bool:
        """Check if VideoToolbox encoder is available.

        Returns:
            True if hevc_videotoolbox is available, False otherwise.
        """
        if self._encoder_available is not None:
            return self._encoder_available

        try:
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-encoders"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self._encoder_available = "hevc_videotoolbox" in result.stdout
            if self._encoder_available:
                logger.debug("VideoToolbox HEVC encoder is available")
            else:
                logger.warning("VideoToolbox HEVC encoder is not available")
            return self._encoder_available
        except (subprocess.SubprocessError, FileNotFoundError):
            self._encoder_available = False
            return False

    def build_command(self, request: ConversionRequest) -> list[str]:
        """Build FFmpeg command for VideoToolbox encoding.

        Args:
            request: The conversion request with settings.

        Returns:
            FFmpeg command arguments.
        """
        # Clamp quality to valid range
        quality = max(
            self.MIN_QUALITY,
            min(self.MAX_QUALITY, request.quality),
        )

        command = [
            "ffmpeg",
            "-hide_banner",
            "-y",  # Overwrite output
            "-i",
            str(request.input_path),
            # Video encoding
            "-c:v",
            self.encoder_name,
            "-q:v",
            str(quality),
            "-tag:v",
            "hvc1",  # Compatibility tag for Apple devices
            # Audio handling
            "-c:a",
            request.audio_mode,
            # Metadata handling
            "-map_metadata",
            "0",  # Copy all metadata
            "-movflags",
            "+faststart+use_metadata_tags",  # Enable streaming and preserve metadata tags
            # Output
            str(request.output_path),
        ]

        return command


def create_hardware_converter() -> HardwareConverter | None:
    """Factory function to create a hardware converter if available.

    Returns:
        HardwareConverter instance if available, None otherwise.
    """
    converter = HardwareConverter()
    if converter.is_available():
        return converter
    return None
