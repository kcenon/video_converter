"""Tests for CLI helper functions.

This module tests the helper functions used by CLI commands,
including formatting functions and validators.
"""

from __future__ import annotations

import pytest
from click import BadParameter

from video_converter.__main__ import parse_time
from video_converter.utils.constants import bytes_to_human, format_duration


class TestParseTime:
    """Tests for parse_time function."""

    def test_parse_valid_time(self) -> None:
        """Test parsing valid time strings."""
        assert parse_time("03:00") == (3, 0)
        assert parse_time("12:30") == (12, 30)
        assert parse_time("00:00") == (0, 0)
        assert parse_time("23:59") == (23, 59)

    def test_parse_single_digit_hour(self) -> None:
        """Test parsing time with single digit hour."""
        assert parse_time("3:00") == (3, 0)
        assert parse_time("9:45") == (9, 45)

    def test_invalid_format_raises_error(self) -> None:
        """Test that invalid format raises BadParameter."""
        with pytest.raises(BadParameter) as exc_info:
            parse_time("3:0")  # Minute needs two digits
        assert "Invalid time format" in str(exc_info.value)

        with pytest.raises(BadParameter):
            parse_time("03-00")  # Wrong separator

        with pytest.raises(BadParameter):
            parse_time("03:00:00")  # Too many parts

        with pytest.raises(BadParameter):
            parse_time("abc")  # Not a time

    def test_invalid_hour_raises_error(self) -> None:
        """Test that hour > 23 raises BadParameter."""
        with pytest.raises(BadParameter) as exc_info:
            parse_time("24:00")
        assert "Hour must be 0-23" in str(exc_info.value)

        with pytest.raises(BadParameter):
            parse_time("25:30")

    def test_invalid_minute_raises_error(self) -> None:
        """Test that minute > 59 raises BadParameter."""
        with pytest.raises(BadParameter) as exc_info:
            parse_time("03:60")
        assert "Minute must be 0-59" in str(exc_info.value)

        with pytest.raises(BadParameter):
            parse_time("12:99")


class TestFormatDuration:
    """Tests for format_duration function from constants."""

    def test_seconds_only(self) -> None:
        """Test formatting durations under 60 seconds."""
        assert format_duration(0) == "0 sec"
        assert format_duration(30) == "30 sec"
        assert format_duration(59) == "59 sec"

    def test_minutes_and_seconds(self) -> None:
        """Test formatting durations in minutes."""
        assert format_duration(60) == "1 min 0 sec"
        assert format_duration(90) == "1 min 30 sec"
        assert format_duration(3599) == "59 min 59 sec"

    def test_hours_and_minutes(self) -> None:
        """Test formatting durations in hours."""
        assert format_duration(3600) == "1 hr 0 min"
        assert format_duration(5400) == "1 hr 30 min"
        assert format_duration(7200) == "2 hr 0 min"

    def test_decimal_seconds(self) -> None:
        """Test formatting with decimal seconds."""
        assert format_duration(30.7) == "30 sec"
        assert format_duration(90.5) == "1 min 30 sec"


class TestBytesToHuman:
    """Tests for bytes_to_human function from constants."""

    def test_bytes(self) -> None:
        """Test formatting sizes in bytes."""
        assert bytes_to_human(0) == "0 B"
        assert bytes_to_human(500) == "500 B"
        assert bytes_to_human(1023) == "1023 B"

    def test_kilobytes(self) -> None:
        """Test formatting sizes in kilobytes."""
        assert bytes_to_human(1024) == "1.00 KB"
        assert bytes_to_human(1536) == "1.50 KB"
        assert bytes_to_human(1024 * 500) == "500.00 KB"

    def test_megabytes(self) -> None:
        """Test formatting sizes in megabytes."""
        assert bytes_to_human(1024 * 1024) == "1.00 MB"
        assert bytes_to_human(1024 * 1024 * 100) == "100.00 MB"
        assert bytes_to_human(1024 * 1024 * 680) == "680.00 MB"

    def test_gigabytes(self) -> None:
        """Test formatting sizes in gigabytes."""
        assert bytes_to_human(1024 * 1024 * 1024) == "1.00 GB"
        assert bytes_to_human(int(1024 * 1024 * 1024 * 1.5)) == "1.50 GB"
        assert bytes_to_human(1024 * 1024 * 1024 * 10) == "10.00 GB"
