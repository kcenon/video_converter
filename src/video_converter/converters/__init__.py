"""Video converters module.

This module provides video encoding functionality using both hardware
(VideoToolbox) and software (libx265) encoders, along with real-time
progress monitoring capabilities.
"""

from video_converter.converters.base import (
    BaseConverter,
    ConversionError,
    EncoderNotAvailableError,
)
from video_converter.converters.factory import ConverterFactory, get_converter
from video_converter.converters.hardware import HardwareConverter
from video_converter.converters.progress import (
    ProgressInfo,
    ProgressMonitor,
    ProgressParser,
    create_simple_callback,
)
from video_converter.converters.software import SoftwareConverter

__all__ = [
    "BaseConverter",
    "ConversionError",
    "ConverterFactory",
    "EncoderNotAvailableError",
    "HardwareConverter",
    "ProgressInfo",
    "ProgressMonitor",
    "ProgressParser",
    "SoftwareConverter",
    "create_simple_callback",
    "get_converter",
]
