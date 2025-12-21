"""Processor modules for video converter.

This package provides video processing functionality including
codec detection, metadata management, and quality validation.

SDS Reference: SDS-P01
"""

from video_converter.processors.quality_validator import (
    ComparisonSeverity,
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
    "ComparisonSeverity",
    "PropertyComparer",
    "PropertyComparison",
    "PropertyComparisonResult",
    "StreamInfo",
    "ValidationResult",
    "ValidationStrictness",
    "VideoInfo",
    "VideoValidator",
]
