"""Processor modules for video converter.

This package provides video processing functionality including
codec detection, metadata management, GPS handling, and quality validation.

SDS Reference: SDS-P01
"""

from video_converter.processors.codec_detector import (
    CodecDetector,
    CodecInfo,
    CorruptedVideoError,
    InvalidVideoError,
    UnsupportedCodecError,
)
from video_converter.processors.gps import (
    GPSCoordinates,
    GPSFormat,
    GPSHandler,
    GPSVerificationResult,
)
from video_converter.processors.metadata import (
    MetadataApplicationError,
    MetadataExtractionError,
    MetadataProcessor,
    MetadataVerificationResult,
)
from video_converter.processors.quality_validator import (
    ComparisonSeverity,
    CompressionRange,
    CompressionSeverity,
    CompressionValidationResult,
    CompressionValidator,
    ContentType,
    PropertyComparer,
    PropertyComparison,
    PropertyComparisonResult,
    StreamInfo,
    ValidationResult,
    ValidationStrictness,
    VideoInfo,
    VideoValidator,
)

__all__ = [
    # Codec detection
    "CodecDetector",
    "CodecInfo",
    "CorruptedVideoError",
    "InvalidVideoError",
    "UnsupportedCodecError",
    # GPS handling
    "GPSCoordinates",
    "GPSFormat",
    "GPSHandler",
    "GPSVerificationResult",
    # Metadata processing
    "MetadataApplicationError",
    "MetadataExtractionError",
    "MetadataProcessor",
    "MetadataVerificationResult",
    # Quality validation
    "ComparisonSeverity",
    "CompressionRange",
    "CompressionSeverity",
    "CompressionValidationResult",
    "CompressionValidator",
    "ContentType",
    "PropertyComparer",
    "PropertyComparison",
    "PropertyComparisonResult",
    "StreamInfo",
    "ValidationResult",
    "ValidationStrictness",
    "VideoInfo",
    "VideoValidator",
]
