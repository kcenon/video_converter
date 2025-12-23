"""Converter factory for creating appropriate video converters.

This module provides a factory pattern implementation for selecting
and instantiating the appropriate video converter based on system
capabilities and user preferences.

SDS Reference: SDS-V01-004
SRS Reference: SRS-204 (Encoder Selection)

Example:
    >>> from video_converter.converters.factory import ConverterFactory
    >>> from video_converter.core import ConversionMode
    >>>
    >>> factory = ConverterFactory()
    >>>
    >>> # Get best available converter
    >>> converter = factory.get_converter()
    >>>
    >>> # Get specific converter type
    >>> hw_converter = factory.get_converter(ConversionMode.HARDWARE)
    >>>
    >>> # Check what's available
    >>> available = factory.get_available_converters()
    >>> print(f"Available: {[c.encoder_name for c in available]}")
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from video_converter.converters.base import BaseConverter, EncoderNotAvailableError
from video_converter.converters.hardware import HardwareConverter
from video_converter.converters.software import SoftwareConverter
from video_converter.core.types import ConversionMode

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ConverterFactory:
    """Factory for creating video converters.

    This factory manages converter instances and provides methods for
    selecting the most appropriate converter based on availability
    and user preferences.
    """

    def __init__(self) -> None:
        """Initialize the converter factory."""
        self._hardware_converter: HardwareConverter | None = None
        self._software_converter: SoftwareConverter | None = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazily initialize converters."""
        if self._initialized:
            return

        self._hardware_converter = HardwareConverter()
        self._software_converter = SoftwareConverter()
        self._initialized = True

    def get_converter(
        self,
        mode: ConversionMode | None = None,
        fallback: bool = True,
    ) -> BaseConverter:
        """Get a converter for the specified mode.

        Args:
            mode: Preferred conversion mode. If None, selects best available.
            fallback: Whether to fall back to alternative if preferred unavailable.

        Returns:
            A converter instance.

        Raises:
            EncoderNotAvailableError: If no suitable encoder is available.
        """
        self._ensure_initialized()

        # Auto-select mode if not specified
        if mode is None:
            return self._get_best_available()

        if mode == ConversionMode.HARDWARE:
            if self._hardware_converter and self._hardware_converter.is_available():
                return self._hardware_converter
            if fallback:
                logger.warning("Hardware encoder not available, falling back to software")
                if self._software_converter and self._software_converter.is_available():
                    return self._software_converter
            raise EncoderNotAvailableError("Hardware encoder (VideoToolbox) is not available")

        if mode == ConversionMode.SOFTWARE:
            if self._software_converter and self._software_converter.is_available():
                return self._software_converter
            if fallback:
                logger.warning("Software encoder not available, falling back to hardware")
                if self._hardware_converter and self._hardware_converter.is_available():
                    return self._hardware_converter
            raise EncoderNotAvailableError("Software encoder (libx265) is not available")

        raise ValueError(f"Unknown conversion mode: {mode}")

    def _get_best_available(self) -> BaseConverter:
        """Get the best available converter.

        Prefers hardware encoding for speed, falls back to software.

        Returns:
            The best available converter.

        Raises:
            EncoderNotAvailableError: If no encoder is available.
        """
        # Prefer hardware for speed
        if self._hardware_converter and self._hardware_converter.is_available():
            logger.debug("Using hardware encoder (VideoToolbox)")
            return self._hardware_converter

        if self._software_converter and self._software_converter.is_available():
            logger.debug("Using software encoder (libx265)")
            return self._software_converter

        raise EncoderNotAvailableError(
            "No video encoders available. Please ensure FFmpeg is installed "
            "with hevc_videotoolbox or libx265 support."
        )

    def get_available_converters(self) -> list[BaseConverter]:
        """Get list of all available converters.

        Returns:
            List of available converter instances.
        """
        self._ensure_initialized()

        available: list[BaseConverter] = []

        if self._hardware_converter and self._hardware_converter.is_available():
            available.append(self._hardware_converter)

        if self._software_converter and self._software_converter.is_available():
            available.append(self._software_converter)

        return available

    def is_hardware_available(self) -> bool:
        """Check if hardware encoding is available.

        Returns:
            True if VideoToolbox encoder is available.
        """
        self._ensure_initialized()
        return bool(self._hardware_converter and self._hardware_converter.is_available())

    def is_software_available(self) -> bool:
        """Check if software encoding is available.

        Returns:
            True if libx265 encoder is available.
        """
        self._ensure_initialized()
        return bool(self._software_converter and self._software_converter.is_available())


# Module-level factory instance for convenience
_default_factory: ConverterFactory | None = None


def get_converter(
    mode: ConversionMode | None = None,
    fallback: bool = True,
) -> BaseConverter:
    """Get a converter using the default factory.

    Args:
        mode: Preferred conversion mode. If None, selects best available.
        fallback: Whether to fall back to alternative if preferred unavailable.

    Returns:
        A converter instance.
    """
    global _default_factory
    if _default_factory is None:
        _default_factory = ConverterFactory()
    return _default_factory.get_converter(mode, fallback)
