"""Processor modules for video converter.

This package provides video processing functionality including
codec detection, metadata management, and quality validation.

SDS Reference: SDS-P01
"""

from video_converter.processors.metadata import (
    GPSCoordinates,
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
    # Metadata processing
    "GPSCoordinates",
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
