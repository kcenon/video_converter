"""Unit tests for converters progress monitoring module."""

from __future__ import annotations

import time
from unittest.mock import Mock

import pytest

from video_converter.converters.progress import (
    ProgressInfo,
    ProgressMonitor,
    ProgressParser,
    create_simple_callback,
)


class TestProgressInfo:
    """Tests for ProgressInfo dataclass."""

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        info = ProgressInfo()
        assert info.frame == 0
        assert info.fps == 0.0
        assert info.current_time == 0.0
        assert info.total_time == 0.0
        assert info.current_size == 0
        assert info.bitrate == 0.0
        assert info.speed == 0.0
        assert info.quality == 0.0

    def test_custom_values(self) -> None:
        """Test custom values are stored correctly."""
        info = ProgressInfo(
            frame=720,
            fps=180.0,
            current_time=24.0,
            total_time=120.0,
            current_size=15728640,  # 15 MB
            bitrate=5242.9,
            speed=6.0,
            quality=32.0,
        )
        assert info.frame == 720
        assert info.fps == 180.0
        assert info.current_time == 24.0
        assert info.total_time == 120.0
        assert info.current_size == 15728640
        assert info.bitrate == 5242.9
        assert info.speed == 6.0
        assert info.quality == 32.0

    def test_percentage_calculation(self) -> None:
        """Test percentage property calculates correctly."""
        info = ProgressInfo(current_time=30.0, total_time=120.0)
        assert info.percentage == pytest.approx(25.0, rel=0.01)

        info = ProgressInfo(current_time=60.0, total_time=120.0)
        assert info.percentage == pytest.approx(50.0, rel=0.01)

        info = ProgressInfo(current_time=120.0, total_time=120.0)
        assert info.percentage == pytest.approx(100.0, rel=0.01)

    def test_percentage_zero_total_time(self) -> None:
        """Test percentage is 0 when total_time is 0."""
        info = ProgressInfo(current_time=30.0, total_time=0.0)
        assert info.percentage == 0.0

    def test_percentage_capped_at_100(self) -> None:
        """Test percentage is capped at 100."""
        info = ProgressInfo(current_time=150.0, total_time=120.0)
        assert info.percentage == 100.0

    def test_eta_seconds_calculation(self) -> None:
        """Test eta_seconds property calculates correctly."""
        # 60s remaining at 2x speed = 30s ETA
        info = ProgressInfo(current_time=60.0, total_time=120.0, speed=2.0)
        assert info.eta_seconds == pytest.approx(30.0, rel=0.01)

        # 90s remaining at 3x speed = 30s ETA
        info = ProgressInfo(current_time=30.0, total_time=120.0, speed=3.0)
        assert info.eta_seconds == pytest.approx(30.0, rel=0.01)

    def test_eta_seconds_zero_speed(self) -> None:
        """Test eta_seconds is infinity when speed is 0."""
        info = ProgressInfo(current_time=30.0, total_time=120.0, speed=0.0)
        assert info.eta_seconds == float("inf")

    def test_eta_seconds_completed(self) -> None:
        """Test eta_seconds is 0 when complete."""
        info = ProgressInfo(current_time=120.0, total_time=120.0, speed=2.0)
        assert info.eta_seconds == 0.0

    def test_eta_formatted_hours(self) -> None:
        """Test eta_formatted with hours."""
        # 2 hours remaining at 1x speed
        info = ProgressInfo(current_time=0.0, total_time=7200.0, speed=1.0)
        assert info.eta_formatted == "2h 0m"

        # 1.5 hours remaining
        info = ProgressInfo(current_time=0.0, total_time=5400.0, speed=1.0)
        assert info.eta_formatted == "1h 30m"

    def test_eta_formatted_minutes(self) -> None:
        """Test eta_formatted with minutes."""
        # 5 minutes remaining at 1x speed
        info = ProgressInfo(current_time=0.0, total_time=300.0, speed=1.0)
        assert info.eta_formatted == "5m 0s"

        # 2.5 minutes remaining
        info = ProgressInfo(current_time=0.0, total_time=150.0, speed=1.0)
        assert info.eta_formatted == "2m 30s"

    def test_eta_formatted_seconds(self) -> None:
        """Test eta_formatted with seconds only."""
        info = ProgressInfo(current_time=0.0, total_time=45.0, speed=1.0)
        assert info.eta_formatted == "45s"

    def test_eta_formatted_calculating(self) -> None:
        """Test eta_formatted shows 'calculating...' when speed is 0."""
        info = ProgressInfo(current_time=30.0, total_time=120.0, speed=0.0)
        assert info.eta_formatted == "calculating..."

    def test_eta_formatted_zero(self) -> None:
        """Test eta_formatted shows '0s' when complete."""
        info = ProgressInfo(current_time=120.0, total_time=120.0, speed=2.0)
        assert info.eta_formatted == "0s"

    def test_size_formatted(self) -> None:
        """Test size_formatted property."""
        info = ProgressInfo(current_size=0)
        assert info.size_formatted == "0 B"

        info = ProgressInfo(current_size=512)
        assert info.size_formatted == "512.0 B"

        info = ProgressInfo(current_size=1024)
        assert info.size_formatted == "1.0 KB"

        info = ProgressInfo(current_size=1048576)
        assert info.size_formatted == "1.0 MB"

        info = ProgressInfo(current_size=1073741824)
        assert info.size_formatted == "1.0 GB"


class TestProgressParser:
    """Tests for ProgressParser."""

    def test_init_default_duration(self) -> None:
        """Test initialization with default duration."""
        parser = ProgressParser()
        assert parser.total_duration == 0.0

    def test_init_custom_duration(self) -> None:
        """Test initialization with custom duration."""
        parser = ProgressParser(total_duration=120.0)
        assert parser.total_duration == 120.0

    def test_init_negative_duration_clamped(self) -> None:
        """Test negative duration is clamped to 0."""
        parser = ProgressParser(total_duration=-10.0)
        assert parser.total_duration == 0.0

    def test_parse_line_typical_output(self) -> None:
        """Test parsing typical FFmpeg progress output."""
        parser = ProgressParser(total_duration=120.0)
        line = (
            "frame=  720 fps=180 q=32.0 size=   15360kB "
            "time=00:00:24.00 bitrate=5242.9kbits/s speed=6.0x"
        )

        info = parser.parse_line(line)

        assert info is not None
        assert info.frame == 720
        assert info.fps == 180.0
        assert info.quality == 32.0
        assert info.current_size == 15360 * 1024  # kB to bytes
        assert info.current_time == 24.0
        assert info.total_time == 120.0
        assert info.bitrate == 5242.9
        assert info.speed == 6.0
        assert info.percentage == pytest.approx(20.0, rel=0.01)

    def test_parse_line_no_progress_info(self) -> None:
        """Test parsing line without progress info returns None."""
        parser = ProgressParser()

        assert parser.parse_line("FFmpeg version 5.0") is None
        assert parser.parse_line("Input #0, mov") is None
        assert parser.parse_line("") is None

    def test_parse_line_with_hours(self) -> None:
        """Test parsing time with hours."""
        parser = ProgressParser(total_duration=7200.0)  # 2 hours
        line = (
            "frame=108000 fps=60 q=28.0 size= 1024000kB "
            "time=01:30:00.00 bitrate=1500.0kbits/s speed=2.0x"
        )

        info = parser.parse_line(line)

        assert info is not None
        assert info.current_time == 5400.0  # 1h 30m = 5400s
        assert info.percentage == pytest.approx(75.0, rel=0.01)

    def test_last_info_property(self) -> None:
        """Test last_info returns most recent parsed info."""
        parser = ProgressParser(total_duration=60.0)

        assert parser.last_info is None

        parser.parse_line(
            "frame=300 fps=60 q=30.0 size=1000kB "
            "time=00:00:10.00 bitrate=800.0kbits/s speed=3.0x"
        )

        assert parser.last_info is not None
        assert parser.last_info.frame == 300
        assert parser.last_info.current_time == 10.0

    def test_parse_line_eta_calculation(self) -> None:
        """Test ETA is calculated from parsed progress."""
        parser = ProgressParser(total_duration=100.0)
        line = (
            "frame=750 fps=30 q=25.0 size=5000kB "
            "time=00:00:25.00 bitrate=1600.0kbits/s speed=2.5x"
        )

        info = parser.parse_line(line)

        assert info is not None
        # 75s remaining at 2.5x speed = 30s ETA
        assert info.eta_seconds == pytest.approx(30.0, rel=0.01)
        assert info.eta_formatted == "30s"


class TestProgressMonitor:
    """Tests for ProgressMonitor."""

    def test_init(self) -> None:
        """Test ProgressMonitor initialization."""
        callback = Mock()
        monitor = ProgressMonitor(total_duration=120.0, callback=callback)

        assert monitor.total_duration == 120.0
        assert monitor.callback == callback
        assert monitor.min_interval == 0.1

    def test_on_output_calls_callback(self) -> None:
        """Test on_output calls callback with ProgressInfo."""
        callback = Mock()
        monitor = ProgressMonitor(
            total_duration=120.0, callback=callback, min_interval=0.0
        )

        line = (
            "frame=720 fps=180 q=32.0 size=15360kB "
            "time=00:00:24.00 bitrate=5242.9kbits/s speed=6.0x"
        )
        monitor.on_output(line)

        callback.assert_called_once()
        info = callback.call_args[0][0]
        assert isinstance(info, ProgressInfo)
        assert info.frame == 720
        assert info.percentage == pytest.approx(20.0, rel=0.01)

    def test_on_output_ignores_non_progress_lines(self) -> None:
        """Test on_output ignores lines without progress info."""
        callback = Mock()
        monitor = ProgressMonitor(
            total_duration=120.0, callback=callback, min_interval=0.0
        )

        monitor.on_output("FFmpeg version 5.0")
        monitor.on_output("Input #0, mov")
        monitor.on_output("")

        callback.assert_not_called()

    def test_on_output_respects_min_interval(self) -> None:
        """Test on_output respects min_interval between callbacks."""
        callback = Mock()
        monitor = ProgressMonitor(
            total_duration=120.0, callback=callback, min_interval=0.5
        )

        line1 = (
            "frame=360 fps=180 q=32.0 size=7680kB "
            "time=00:00:12.00 bitrate=5242.9kbits/s speed=6.0x"
        )
        line2 = (
            "frame=720 fps=180 q=32.0 size=15360kB "
            "time=00:00:24.00 bitrate=5242.9kbits/s speed=6.0x"
        )

        monitor.on_output(line1)
        assert callback.call_count == 1

        # Second call immediately - should be throttled
        monitor.on_output(line2)
        assert callback.call_count == 1

        # Wait for interval and call again
        time.sleep(0.6)
        monitor.on_output(line2)
        assert callback.call_count == 2

    def test_on_output_swallows_callback_exceptions(self) -> None:
        """Test on_output doesn't propagate callback exceptions."""
        callback = Mock(side_effect=ValueError("test error"))
        monitor = ProgressMonitor(
            total_duration=120.0, callback=callback, min_interval=0.0
        )

        line = (
            "frame=720 fps=180 q=32.0 size=15360kB "
            "time=00:00:24.00 bitrate=5242.9kbits/s speed=6.0x"
        )

        # Should not raise
        monitor.on_output(line)
        callback.assert_called_once()

    def test_get_current_progress(self) -> None:
        """Test get_current_progress returns current progress."""
        callback = Mock()
        monitor = ProgressMonitor(
            total_duration=120.0, callback=callback, min_interval=0.0
        )

        assert monitor.get_current_progress() is None

        line = (
            "frame=720 fps=180 q=32.0 size=15360kB "
            "time=00:00:24.00 bitrate=5242.9kbits/s speed=6.0x"
        )
        monitor.on_output(line)

        info = monitor.get_current_progress()
        assert info is not None
        assert info.frame == 720

    def test_force_callback(self) -> None:
        """Test force_callback calls callback ignoring interval."""
        callback = Mock()
        monitor = ProgressMonitor(
            total_duration=120.0, callback=callback, min_interval=10.0
        )

        line = (
            "frame=720 fps=180 q=32.0 size=15360kB "
            "time=00:00:24.00 bitrate=5242.9kbits/s speed=6.0x"
        )
        monitor.on_output(line)
        assert callback.call_count == 1

        # force_callback should work even within interval
        monitor.force_callback()
        assert callback.call_count == 2


class TestCreateSimpleCallback:
    """Tests for create_simple_callback helper."""

    def test_creates_callable(self) -> None:
        """Test create_simple_callback returns a callable."""
        callback = create_simple_callback()
        assert callable(callback)

    def test_callback_doesnt_raise(self) -> None:
        """Test callback doesn't raise on valid ProgressInfo."""
        callback = create_simple_callback(show_bar=False)
        info = ProgressInfo(
            current_time=30.0,
            total_time=120.0,
            current_size=1048576,
            speed=2.0,
        )

        # Should not raise
        callback(info)

    def test_callback_with_bar(self) -> None:
        """Test callback with bar enabled doesn't raise."""
        callback = create_simple_callback(show_bar=True, bar_width=20)
        info = ProgressInfo(
            current_time=60.0,
            total_time=120.0,
            current_size=5242880,
            speed=3.0,
        )

        # Should not raise
        callback(info)
