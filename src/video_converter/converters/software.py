"""Software video converter using libx265.

This module implements software-based H.265 encoding using the libx265
encoder through FFmpeg.

SDS Reference: SDS-V01-003
SRS Reference: SRS-202 (Software Encoding)

Example:
    >>> from video_converter.converters.software import SoftwareConverter
    >>> from video_converter.core import ConversionRequest
    >>>
    >>> converter = SoftwareConverter()
    >>> if converter.is_available():
    ...     request = ConversionRequest(
    ...         input_path=Path("input.mov"),
    ...         output_path=Path("output.mp4"),
    ...         preset="medium",
    ...         crf=22,
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


class SoftwareConverter(BaseConverter):
    """Software-based H.265 converter using libx265.

    This converter uses the libx265 encoder for CPU-based H.265 encoding.
    It's slower than hardware encoding but more widely compatible and
    offers more fine-grained control over encoding parameters.

    Attributes:
        mode: Always SOFTWARE for this converter.
    """

    # CRF range for libx265: 0-51 (lower = better quality, 18-28 typical)
    MIN_CRF = 0
    MAX_CRF = 51
    DEFAULT_CRF = 22

    # Valid presets from fastest to slowest
    VALID_PRESETS = [
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
    ]
    DEFAULT_PRESET = "medium"

    def __init__(self) -> None:
        """Initialize the software converter."""
        super().__init__(ConversionMode.SOFTWARE)
        self._encoder_available: bool | None = None

    @property
    def encoder_name(self) -> str:
        """Get the encoder name.

        Returns:
            The libx265 encoder name.
        """
        return "libx265"

    def is_available(self) -> bool:
        """Check if libx265 encoder is available.

        Returns:
            True if libx265 is available, False otherwise.
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
            self._encoder_available = "libx265" in result.stdout
            if self._encoder_available:
                logger.debug("libx265 encoder is available")
            else:
                logger.warning("libx265 encoder is not available")
            return self._encoder_available
        except (subprocess.SubprocessError, FileNotFoundError):
            self._encoder_available = False
            return False

    def build_command(self, request: ConversionRequest) -> list[str]:
        """Build FFmpeg command for libx265 encoding.

        Args:
            request: The conversion request with settings.

        Returns:
            FFmpeg command arguments.
        """
        # Clamp CRF to valid range
        crf = max(self.MIN_CRF, min(self.MAX_CRF, request.crf))

        # Validate preset
        preset = (
            request.preset
            if request.preset in self.VALID_PRESETS
            else self.DEFAULT_PRESET
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
            "-crf",
            str(crf),
            "-preset",
            preset,
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


def create_software_converter() -> SoftwareConverter | None:
    """Factory function to create a software converter if available.

    Returns:
        SoftwareConverter instance if available, None otherwise.
    """
    converter = SoftwareConverter()
    if converter.is_available():
        return converter
    return None
