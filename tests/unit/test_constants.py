"""Unit tests for constants module."""

from __future__ import annotations

import pytest

from video_converter.utils.constants import (
    # Size units
    BYTES_PER_GB,
    BYTES_PER_KB,
    BYTES_PER_MB,
    # Time units
    SECONDS_PER_HOUR,
    SECONDS_PER_MINUTE,
    # Timeouts
    ICLOUD_DOWNLOAD_TIMEOUT,
    ICLOUD_POLL_INTERVAL,
    VMAF_ANALYSIS_TIMEOUT,
    VMAF_QUICK_TIMEOUT,
    # Quality settings
    DEFAULT_CRF,
    DEFAULT_QUALITY,
    HARDWARE_MAX_QUALITY,
    HARDWARE_MIN_QUALITY,
    SOFTWARE_MAX_CRF,
    SOFTWARE_MIN_CRF,
    # VMAF thresholds
    VMAF_THRESHOLD_GOOD_QUALITY,
    VMAF_THRESHOLD_HIGH_QUALITY,
    VMAF_THRESHOLD_VISUALLY_LOSSLESS,
    # Encoding presets
    DEFAULT_BIT_DEPTH,
    DEFAULT_PRESET,
    ENCODING_PRESETS,
    SUPPORTED_BIT_DEPTHS,
    # File system
    VIDEO_EXTENSIONS,
    # Processing
    DEFAULT_CONCURRENT_CONVERSIONS,
    MAX_CONCURRENT_CONVERSIONS,
    MIN_CONCURRENT_CONVERSIONS,
    MIN_FREE_DISK_SPACE,
    # Helper functions
    bytes_to_human,
    format_duration,
)


class TestSizeUnits:
    """Tests for size unit constants."""

    def test_bytes_per_kb(self) -> None:
        """Test KB constant is 1024."""
        assert BYTES_PER_KB == 1024

    def test_bytes_per_mb(self) -> None:
        """Test MB constant is 1024 * 1024."""
        assert BYTES_PER_MB == 1024 * 1024
        assert BYTES_PER_MB == 1_048_576

    def test_bytes_per_gb(self) -> None:
        """Test GB constant is 1024 * 1024 * 1024."""
        assert BYTES_PER_GB == 1024 * 1024 * 1024
        assert BYTES_PER_GB == 1_073_741_824


class TestTimeUnits:
    """Tests for time unit constants."""

    def test_seconds_per_minute(self) -> None:
        """Test seconds per minute is 60."""
        assert SECONDS_PER_MINUTE == 60

    def test_seconds_per_hour(self) -> None:
        """Test seconds per hour is 3600."""
        assert SECONDS_PER_HOUR == 3600


class TestTimeouts:
    """Tests for timeout constants."""

    def test_icloud_download_timeout(self) -> None:
        """Test iCloud timeout is 1 hour."""
        assert ICLOUD_DOWNLOAD_TIMEOUT == 3600

    def test_icloud_poll_interval(self) -> None:
        """Test iCloud poll interval is 1 second."""
        assert ICLOUD_POLL_INTERVAL == 1.0

    def test_vmaf_analysis_timeout(self) -> None:
        """Test VMAF analysis timeout is 1 hour."""
        assert VMAF_ANALYSIS_TIMEOUT == 3600.0

    def test_vmaf_quick_timeout(self) -> None:
        """Test VMAF quick timeout is 5 minutes."""
        assert VMAF_QUICK_TIMEOUT == 300.0


class TestQualitySettings:
    """Tests for quality setting constants."""

    def test_hardware_quality_range(self) -> None:
        """Test hardware encoder quality range is 1-100."""
        assert HARDWARE_MIN_QUALITY == 1
        assert HARDWARE_MAX_QUALITY == 100

    def test_default_quality(self) -> None:
        """Test default quality is 45."""
        assert DEFAULT_QUALITY == 45
        assert HARDWARE_MIN_QUALITY <= DEFAULT_QUALITY <= HARDWARE_MAX_QUALITY

    def test_software_crf_range(self) -> None:
        """Test software encoder CRF range is 0-51."""
        assert SOFTWARE_MIN_CRF == 0
        assert SOFTWARE_MAX_CRF == 51

    def test_default_crf(self) -> None:
        """Test default CRF is 22."""
        assert DEFAULT_CRF == 22
        assert SOFTWARE_MIN_CRF <= DEFAULT_CRF <= SOFTWARE_MAX_CRF


class TestVmafThresholds:
    """Tests for VMAF threshold constants."""

    def test_visually_lossless_threshold(self) -> None:
        """Test visually lossless threshold is 93."""
        assert VMAF_THRESHOLD_VISUALLY_LOSSLESS == 93.0

    def test_high_quality_threshold(self) -> None:
        """Test high quality threshold is 80."""
        assert VMAF_THRESHOLD_HIGH_QUALITY == 80.0

    def test_good_quality_threshold(self) -> None:
        """Test good quality threshold is 60."""
        assert VMAF_THRESHOLD_GOOD_QUALITY == 60.0

    def test_threshold_ordering(self) -> None:
        """Test thresholds are in decreasing order."""
        assert (
            VMAF_THRESHOLD_VISUALLY_LOSSLESS
            > VMAF_THRESHOLD_HIGH_QUALITY
            > VMAF_THRESHOLD_GOOD_QUALITY
        )


class TestEncodingPresets:
    """Tests for encoding preset constants."""

    def test_encoding_presets_is_tuple(self) -> None:
        """Test encoding presets is an immutable tuple."""
        assert isinstance(ENCODING_PRESETS, tuple)

    def test_encoding_presets_contains_all_presets(self) -> None:
        """Test all FFmpeg presets are included."""
        expected = (
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
        )
        assert ENCODING_PRESETS == expected

    def test_default_preset_is_valid(self) -> None:
        """Test default preset is in valid presets."""
        assert DEFAULT_PRESET == "medium"
        assert DEFAULT_PRESET in ENCODING_PRESETS

    def test_supported_bit_depths(self) -> None:
        """Test supported bit depths are 8 and 10."""
        assert SUPPORTED_BIT_DEPTHS == (8, 10)

    def test_default_bit_depth(self) -> None:
        """Test default bit depth is 8."""
        assert DEFAULT_BIT_DEPTH == 8
        assert DEFAULT_BIT_DEPTH in SUPPORTED_BIT_DEPTHS


class TestVideoExtensions:
    """Tests for video extension constants."""

    def test_video_extensions_is_frozenset(self) -> None:
        """Test video extensions is an immutable frozenset."""
        assert isinstance(VIDEO_EXTENSIONS, frozenset)

    def test_common_extensions_included(self) -> None:
        """Test common video extensions are included."""
        common = {".mov", ".mp4", ".m4v", ".avi", ".mkv"}
        assert common.issubset(VIDEO_EXTENSIONS)


class TestProcessingConstants:
    """Tests for processing constants."""

    def test_concurrent_conversions_range(self) -> None:
        """Test concurrent conversions range is 1-8."""
        assert MIN_CONCURRENT_CONVERSIONS == 1
        assert MAX_CONCURRENT_CONVERSIONS == 8

    def test_default_concurrent_conversions(self) -> None:
        """Test default concurrent conversions is 2."""
        assert DEFAULT_CONCURRENT_CONVERSIONS == 2
        assert (
            MIN_CONCURRENT_CONVERSIONS
            <= DEFAULT_CONCURRENT_CONVERSIONS
            <= MAX_CONCURRENT_CONVERSIONS
        )

    def test_min_free_disk_space(self) -> None:
        """Test minimum free disk space is 1 GB."""
        assert MIN_FREE_DISK_SPACE == BYTES_PER_GB


class TestBytesToHuman:
    """Tests for bytes_to_human helper function."""

    def test_bytes(self) -> None:
        """Test bytes formatting."""
        assert bytes_to_human(500) == "500 B"
        assert bytes_to_human(0) == "0 B"

    def test_kilobytes(self) -> None:
        """Test kilobytes formatting."""
        assert bytes_to_human(1024) == "1.00 KB"
        assert bytes_to_human(2048) == "2.00 KB"

    def test_megabytes(self) -> None:
        """Test megabytes formatting."""
        assert bytes_to_human(1048576) == "1.00 MB"
        assert bytes_to_human(5242880) == "5.00 MB"

    def test_gigabytes(self) -> None:
        """Test gigabytes formatting."""
        assert bytes_to_human(1073741824) == "1.00 GB"
        assert bytes_to_human(2147483648) == "2.00 GB"


class TestFormatDuration:
    """Tests for format_duration helper function."""

    def test_seconds(self) -> None:
        """Test seconds formatting."""
        assert format_duration(0) == "0 sec"
        assert format_duration(45) == "45 sec"
        assert format_duration(59) == "59 sec"

    def test_minutes(self) -> None:
        """Test minutes formatting."""
        assert format_duration(60) == "1 min 0 sec"
        assert format_duration(90) == "1 min 30 sec"
        assert format_duration(125) == "2 min 5 sec"

    def test_hours(self) -> None:
        """Test hours formatting."""
        assert format_duration(3600) == "1 hr 0 min"
        assert format_duration(3725) == "1 hr 2 min"
        assert format_duration(7200) == "2 hr 0 min"
