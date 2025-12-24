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
from video_converter.utils.constants import (
    DEFAULT_BIT_DEPTH,
    DEFAULT_CRF,
    DEFAULT_PRESET,
    ENCODING_PRESETS,
    SOFTWARE_MAX_CRF,
    SOFTWARE_MIN_CRF,
    SUPPORTED_BIT_DEPTHS,
)

logger = logging.getLogger(__name__)


class SoftwareConverter(BaseConverter):
    """Software-based H.265 converter using libx265.

    This converter uses the libx265 encoder for CPU-based H.265 encoding.
    It's slower than hardware encoding but more widely compatible and
    offers more fine-grained control over encoding parameters.

    Supports both 8-bit and 10-bit encoding for HDR content.

    Attributes:
        mode: Always SOFTWARE for this converter.
    """

    # CRF range for libx265: 0-51 (lower = better quality, 18-28 typical)
    MIN_CRF = SOFTWARE_MIN_CRF
    MAX_CRF = SOFTWARE_MAX_CRF
    DEFAULT_CRF = DEFAULT_CRF

    # Valid presets from fastest to slowest
    VALID_PRESETS = list(ENCODING_PRESETS)
    DEFAULT_PRESET = DEFAULT_PRESET

    # Valid bit depths
    VALID_BIT_DEPTHS = list(SUPPORTED_BIT_DEPTHS)
    DEFAULT_BIT_DEPTH = DEFAULT_BIT_DEPTH

    # HDR x265 parameters for BT.2020 PQ (HDR10)
    HDR_X265_PARAMS = (
        "hdr-opt=1:repeat-headers=1:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc"
    )

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
        preset = request.preset if request.preset in self.VALID_PRESETS else self.DEFAULT_PRESET

        # Validate bit depth
        bit_depth = (
            request.bit_depth
            if request.bit_depth in self.VALID_BIT_DEPTHS
            else self.DEFAULT_BIT_DEPTH
        )

        # Select encoder based on bit depth
        # libx265 handles both 8-bit and 10-bit natively
        encoder = self.encoder_name

        command = [
            "ffmpeg",
            "-hide_banner",
            "-y",  # Overwrite output
            "-i",
            str(request.input_path),
            # Video encoding
            "-c:v",
            encoder,
            "-crf",
            str(crf),
            "-preset",
            preset,
            "-tag:v",
            "hvc1",  # Compatibility tag for Apple devices
        ]

        # Add 10-bit encoding options
        if bit_depth == 10:
            command.extend(["-pix_fmt", "yuv420p10le"])

            # Add HDR parameters if enabled
            if request.hdr:
                command.extend(["-x265-params", self.HDR_X265_PARAMS])

        # Audio handling
        command.extend(["-c:a", request.audio_mode])

        # Metadata handling
        command.extend(
            [
                "-map_metadata",
                "0",  # Copy all metadata
                "-movflags",
                "+faststart+use_metadata_tags",  # Enable streaming and preserve metadata tags
            ]
        )

        # Output
        command.append(str(request.output_path))

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
