"""Unit tests for FFmpeg progress parser."""

from __future__ import annotations

import pytest

from video_converter.utils.progress_parser import FFmpegProgress, FFmpegProgressParser


class TestFFmpegProgress:
    """Tests for FFmpegProgress dataclass."""

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        progress = FFmpegProgress()
        assert progress.frame == 0
        assert progress.fps == 0.0
        assert progress.quality == 0.0
        assert progress.size_kb == 0
        assert progress.time_seconds == 0.0
        assert progress.bitrate_kbps == 0.0
        assert progress.speed == 0.0
        assert progress.percentage == 0.0

    def test_custom_values(self) -> None:
        """Test custom values are stored correctly."""
        progress = FFmpegProgress(
            frame=720,
            fps=180.0,
            quality=32.0,
            size_kb=15360,
            time_seconds=24.0,
            bitrate_kbps=5242.9,
            speed=6.0,
            percentage=20.0,
        )
        assert progress.frame == 720
        assert progress.fps == 180.0
        assert progress.quality == 32.0
        assert progress.size_kb == 15360
        assert progress.time_seconds == 24.0
        assert progress.bitrate_kbps == 5242.9
        assert progress.speed == 6.0
        assert progress.percentage == 20.0


class TestFFmpegProgressParser:
    """Tests for FFmpegProgressParser."""

    def test_init_default_duration(self) -> None:
        """Test initialization with default duration."""
        parser = FFmpegProgressParser()
        assert parser.total_duration == 0.0

    def test_init_custom_duration(self) -> None:
        """Test initialization with custom duration."""
        parser = FFmpegProgressParser(total_duration=120.0)
        assert parser.total_duration == 120.0

    def test_init_negative_duration_clamped(self) -> None:
        """Test negative duration is clamped to 0."""
        parser = FFmpegProgressParser(total_duration=-10.0)
        assert parser.total_duration == 0.0

    def test_parse_line_typical_output(self) -> None:
        """Test parsing typical FFmpeg progress output."""
        parser = FFmpegProgressParser(total_duration=120.0)
        line = (
            "frame=  720 fps=180 q=32.0 size=   15360kB "
            "time=00:00:24.00 bitrate=5242.9kbits/s speed=6.0x"
        )

        progress = parser.parse_line(line)

        assert progress is not None
        assert progress.frame == 720
        assert progress.fps == 180.0
        assert progress.quality == 32.0
        assert progress.size_kb == 15360
        assert progress.time_seconds == 24.0
        assert progress.bitrate_kbps == 5242.9
        assert progress.speed == 6.0
        assert progress.percentage == pytest.approx(20.0, rel=0.01)

    def test_parse_line_no_progress_info(self) -> None:
        """Test parsing line without progress info returns None."""
        parser = FFmpegProgressParser()

        assert parser.parse_line("FFmpeg version 5.0") is None
        assert parser.parse_line("Input #0, mov") is None
        assert parser.parse_line("") is None

    def test_parse_line_partial_frame_info(self) -> None:
        """Test parsing line with only frame (no time) returns None."""
        parser = FFmpegProgressParser()
        line = "frame=  100 fps=0.0"

        assert parser.parse_line(line) is None

    def test_parse_line_with_hours(self) -> None:
        """Test parsing time with hours."""
        parser = FFmpegProgressParser(total_duration=7200.0)  # 2 hours
        line = (
            "frame=108000 fps=60 q=28.0 size= 1024000kB "
            "time=01:30:00.00 bitrate=1500.0kbits/s speed=2.0x"
        )

        progress = parser.parse_line(line)

        assert progress is not None
        assert progress.time_seconds == 5400.0  # 1h 30m = 5400s
        assert progress.percentage == pytest.approx(75.0, rel=0.01)

    def test_parse_line_preserves_last_progress(self) -> None:
        """Test get_last_progress returns most recent progress."""
        parser = FFmpegProgressParser(total_duration=60.0)

        parser.parse_line(
            "frame=300 fps=60 q=30.0 size=1000kB "
            "time=00:00:10.00 bitrate=800.0kbits/s speed=3.0x"
        )

        last = parser.get_last_progress()
        assert last.frame == 300
        assert last.time_seconds == 10.0

    def test_parse_line_percentage_calculation(self) -> None:
        """Test percentage is calculated correctly."""
        parser = FFmpegProgressParser(total_duration=100.0)

        # 25% progress
        progress = parser.parse_line(
            "frame=750 fps=30 q=25.0 size=5000kB "
            "time=00:00:25.00 bitrate=1600.0kbits/s speed=1.5x"
        )
        assert progress is not None
        assert progress.percentage == pytest.approx(25.0, rel=0.01)

        # 50% progress
        progress = parser.parse_line(
            "frame=1500 fps=30 q=25.0 size=10000kB "
            "time=00:00:50.00 bitrate=1600.0kbits/s speed=1.5x"
        )
        assert progress is not None
        assert progress.percentage == pytest.approx(50.0, rel=0.01)

        # 100% progress (capped)
        progress = parser.parse_line(
            "frame=3000 fps=30 q=25.0 size=20000kB "
            "time=00:01:40.00 bitrate=1600.0kbits/s speed=1.5x"
        )
        assert progress is not None
        assert progress.percentage == pytest.approx(100.0, rel=0.01)

    def test_parse_line_zero_duration(self) -> None:
        """Test parsing with zero duration results in 0% progress."""
        parser = FFmpegProgressParser(total_duration=0.0)
        line = (
            "frame=720 fps=180 q=32.0 size=15360kB "
            "time=00:00:24.00 bitrate=5242.9kbits/s speed=6.0x"
        )

        progress = parser.parse_line(line)

        assert progress is not None
        assert progress.percentage == 0.0

    def test_parse_line_centiseconds(self) -> None:
        """Test parsing time with centiseconds."""
        parser = FFmpegProgressParser(total_duration=60.0)
        line = (
            "frame=450 fps=30 q=28.0 size=3000kB "
            "time=00:00:15.50 bitrate=1600.0kbits/s speed=2.0x"
        )

        progress = parser.parse_line(line)

        assert progress is not None
        assert progress.time_seconds == pytest.approx(15.50, rel=0.01)

    def test_parse_time_to_seconds(self) -> None:
        """Test static method for parsing time strings."""
        assert FFmpegProgressParser.parse_time_to_seconds("00:00:00.00") == 0.0
        assert FFmpegProgressParser.parse_time_to_seconds("00:00:30.00") == 30.0
        assert FFmpegProgressParser.parse_time_to_seconds("00:01:00.00") == 60.0
        assert FFmpegProgressParser.parse_time_to_seconds("01:00:00.00") == 3600.0
        assert FFmpegProgressParser.parse_time_to_seconds("00:00:00.50") == 0.5
        assert FFmpegProgressParser.parse_time_to_seconds("02:30:45.25") == pytest.approx(
            9045.25, rel=0.01
        )

    def test_parse_time_to_seconds_invalid(self) -> None:
        """Test parsing invalid time string returns 0."""
        assert FFmpegProgressParser.parse_time_to_seconds("invalid") == 0.0
        assert FFmpegProgressParser.parse_time_to_seconds("") == 0.0

    def test_parse_line_high_speed(self) -> None:
        """Test parsing high speed values (10x+)."""
        parser = FFmpegProgressParser(total_duration=60.0)
        line = (
            "frame=1800 fps=500 q=45.0 size=2000kB "
            "time=00:01:00.00 bitrate=273.1kbits/s speed=15.5x"
        )

        progress = parser.parse_line(line)

        assert progress is not None
        assert progress.speed == 15.5

    def test_parse_line_floating_fps(self) -> None:
        """Test parsing floating point FPS."""
        parser = FFmpegProgressParser(total_duration=60.0)
        line = (
            "frame=900 fps=29.97 q=30.0 size=5000kB "
            "time=00:00:30.03 bitrate=1366.0kbits/s speed=1.0x"
        )

        progress = parser.parse_line(line)

        assert progress is not None
        assert progress.fps == pytest.approx(29.97, rel=0.01)

    def test_get_last_progress_empty(self) -> None:
        """Test get_last_progress returns empty progress when nothing parsed."""
        parser = FFmpegProgressParser()
        last = parser.get_last_progress()

        assert last.frame == 0
        assert last.percentage == 0.0
