"""Unit tests for quality_validator module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_converter.processors.quality_validator import (
    StreamInfo,
    ValidationResult,
    ValidationStrictness,
    VideoInfo,
    VideoValidator,
)
from video_converter.utils.command_runner import CommandExecutionError, FFprobeRunner


class TestStreamInfo:
    """Tests for StreamInfo dataclass."""

    def test_video_stream_creation(self) -> None:
        """Test creating a video stream info."""
        stream = StreamInfo(
            index=0,
            codec_type="video",
            codec_name="h264",
            width=1920,
            height=1080,
            fps=30.0,
        )
        assert stream.index == 0
        assert stream.codec_type == "video"
        assert stream.codec_name == "h264"
        assert stream.width == 1920
        assert stream.height == 1080
        assert stream.fps == 30.0

    def test_audio_stream_creation(self) -> None:
        """Test creating an audio stream info."""
        stream = StreamInfo(
            index=1,
            codec_type="audio",
            codec_name="aac",
            channels=2,
            sample_rate=48000,
        )
        assert stream.codec_type == "audio"
        assert stream.codec_name == "aac"
        assert stream.channels == 2
        assert stream.sample_rate == 48000


class TestVideoInfo:
    """Tests for VideoInfo dataclass."""

    def test_video_info_with_streams(self) -> None:
        """Test VideoInfo with video and audio streams."""
        video_stream = StreamInfo(0, "video", "h264", width=1920, height=1080)
        audio_stream = StreamInfo(1, "audio", "aac", channels=2)

        info = VideoInfo(
            path=Path("test.mp4"),
            format_name="mp4",
            duration=120.0,
            size=50_000_000,
            bit_rate=3_333_333,
            streams=[video_stream, audio_stream],
        )

        assert info.has_video is True
        assert info.has_audio is True
        assert len(info.video_streams) == 1
        assert len(info.audio_streams) == 1
        assert info.primary_video_stream == video_stream
        assert info.primary_audio_stream == audio_stream

    def test_video_info_no_audio(self) -> None:
        """Test VideoInfo without audio stream."""
        video_stream = StreamInfo(0, "video", "h264")
        info = VideoInfo(
            path=Path("test.mp4"),
            format_name="mp4",
            duration=60.0,
            size=10_000_000,
            bit_rate=None,
            streams=[video_stream],
        )

        assert info.has_video is True
        assert info.has_audio is False
        assert info.primary_audio_stream is None

    def test_video_info_empty_streams(self) -> None:
        """Test VideoInfo with no streams."""
        info = VideoInfo(
            path=Path("test.mp4"),
            format_name="mp4",
            duration=0,
            size=1000,
            bit_rate=None,
        )

        assert info.has_video is False
        assert info.has_audio is False
        assert info.primary_video_stream is None
        assert info.primary_audio_stream is None


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_valid_result(self) -> None:
        """Test creating a valid result."""
        result = ValidationResult(valid=True, integrity_ok=True)
        assert result.valid is True
        assert result.integrity_ok is True
        assert result.errors == []
        assert result.warnings == []

    def test_add_error(self) -> None:
        """Test that add_error marks result as invalid."""
        result = ValidationResult(valid=True, integrity_ok=True)
        result.add_error("Test error")
        assert result.valid is False
        assert "Test error" in result.errors

    def test_add_warning(self) -> None:
        """Test that add_warning doesn't affect validity."""
        result = ValidationResult(valid=True, integrity_ok=True)
        result.add_warning("Test warning")
        assert result.valid is True
        assert "Test warning" in result.warnings


class TestVideoValidator:
    """Tests for VideoValidator class."""

    def test_init_default_values(self) -> None:
        """Test default initialization values."""
        validator = VideoValidator()
        assert validator.strictness == ValidationStrictness.STANDARD
        assert validator.timeout == 30.0

    def test_init_custom_values(self) -> None:
        """Test custom initialization values."""
        validator = VideoValidator(
            strictness=ValidationStrictness.STRICT,
            timeout=60.0,
        )
        assert validator.strictness == ValidationStrictness.STRICT
        assert validator.timeout == 60.0

    def test_validate_nonexistent_file(self) -> None:
        """Test validation of non-existent file."""
        validator = VideoValidator()
        result = validator.validate(Path("/nonexistent/video.mp4"))
        assert result.valid is False
        assert result.integrity_ok is False
        assert any("not exist" in e.lower() or "not found" in e.lower() for e in result.errors)

    def test_quick_validate_nonexistent_file(self) -> None:
        """Test quick validation of non-existent file."""
        validator = VideoValidator()
        assert validator.quick_validate(Path("/nonexistent/video.mp4")) is False

    def test_parse_frame_rate_fraction(self) -> None:
        """Test parsing frame rate as fraction."""
        assert VideoValidator._parse_frame_rate("30000/1001") == pytest.approx(29.97, rel=0.01)
        assert VideoValidator._parse_frame_rate("30/1") == 30.0
        assert VideoValidator._parse_frame_rate("24000/1001") == pytest.approx(23.976, rel=0.01)

    def test_parse_frame_rate_number(self) -> None:
        """Test parsing frame rate as number."""
        assert VideoValidator._parse_frame_rate("30") == 30.0
        assert VideoValidator._parse_frame_rate("60.0") == 60.0

    def test_parse_frame_rate_invalid(self) -> None:
        """Test parsing invalid frame rate."""
        assert VideoValidator._parse_frame_rate("invalid") is None
        assert VideoValidator._parse_frame_rate("0/0") is None
        assert VideoValidator._parse_frame_rate("30/0") is None

    def test_validate_with_mock_valid_video(self) -> None:
        """Test validation with mocked valid video."""
        mock_probe_data = {
            "format": {
                "format_name": "mov,mp4",
                "duration": "120.5",
                "size": "50000000",
                "bit_rate": "3333333",
            },
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30/1",
                    "duration": "120.5",
                },
                {
                    "index": 1,
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "channels": 2,
                    "sample_rate": "48000",
                },
            ],
        }

        mock_ffprobe = MagicMock(spec=FFprobeRunner)
        mock_ffprobe.probe.return_value = mock_probe_data

        validator = VideoValidator(ffprobe=mock_ffprobe)

        with patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "is_file", return_value=True), \
             patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 50_000_000
            result = validator.validate(Path("test.mp4"))

        assert result.valid is True
        assert result.integrity_ok is True
        assert result.video_info is not None
        assert result.video_info.has_video is True
        assert result.video_info.has_audio is True

    def test_validate_with_mock_no_video_stream(self) -> None:
        """Test validation when no video stream exists."""
        mock_probe_data = {
            "format": {
                "format_name": "mp3",
                "duration": "180.0",
                "size": "5000000",
            },
            "streams": [
                {
                    "index": 0,
                    "codec_type": "audio",
                    "codec_name": "mp3",
                    "channels": 2,
                },
            ],
        }

        mock_ffprobe = MagicMock(spec=FFprobeRunner)
        mock_ffprobe.probe.return_value = mock_probe_data

        validator = VideoValidator(ffprobe=mock_ffprobe)

        with patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "is_file", return_value=True), \
             patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 5_000_000
            result = validator.validate(Path("test.mp3"))

        assert result.valid is False
        assert any("no video stream" in e.lower() for e in result.errors)

    def test_validate_with_mock_zero_duration(self) -> None:
        """Test validation when duration is zero."""
        mock_probe_data = {
            "format": {
                "format_name": "mp4",
                "duration": "0",
                "size": "1000",
            },
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264",
                },
            ],
        }

        mock_ffprobe = MagicMock(spec=FFprobeRunner)
        mock_ffprobe.probe.return_value = mock_probe_data

        validator = VideoValidator(ffprobe=mock_ffprobe)

        with patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "is_file", return_value=True), \
             patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 1000
            result = validator.validate(Path("test.mp4"))

        assert result.valid is False
        assert any("duration" in e.lower() for e in result.errors)

    def test_validate_strict_mode(self) -> None:
        """Test strict validation mode."""
        mock_probe_data = {
            "format": {
                "format_name": "mp4",
                "duration": "10.0",
                "size": "1000000",
            },
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30/1",
                },
            ],
        }

        mock_ffprobe = MagicMock(spec=FFprobeRunner)
        mock_ffprobe.probe.return_value = mock_probe_data

        validator = VideoValidator(
            strictness=ValidationStrictness.STRICT,
            ffprobe=mock_ffprobe,
        )

        with patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "is_file", return_value=True), \
             patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 1_000_000
            result = validator.validate(Path("test.mp4"))

        # Should have warning for no audio in strict mode
        assert any("audio" in w.lower() for w in result.warnings)

    def test_validate_ffprobe_error(self) -> None:
        """Test validation when FFprobe fails."""
        mock_ffprobe = MagicMock(spec=FFprobeRunner)
        mock_ffprobe.probe.side_effect = CommandExecutionError(
            "ffprobe", 1, "Error processing file"
        )

        validator = VideoValidator(ffprobe=mock_ffprobe)

        with patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "is_file", return_value=True), \
             patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 1000
            result = validator.validate(Path("test.mp4"))

        assert result.valid is False
        assert any("ffprobe failed" in e.lower() for e in result.errors)


class TestVideoValidatorAsync:
    """Async tests for VideoValidator."""

    @pytest.mark.asyncio
    async def test_validate_async_nonexistent_file(self) -> None:
        """Test async validation of non-existent file."""
        validator = VideoValidator()
        result = await validator.validate_async(Path("/nonexistent/video.mp4"))
        assert result.valid is False
        assert result.integrity_ok is False

    @pytest.mark.asyncio
    async def test_validate_async_with_mock(self) -> None:
        """Test async validation with mock."""
        mock_probe_data = {
            "format": {
                "format_name": "mp4",
                "duration": "60.0",
                "size": "10000000",
            },
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "hevc",
                    "width": 3840,
                    "height": 2160,
                },
            ],
        }

        mock_ffprobe = MagicMock(spec=FFprobeRunner)
        mock_ffprobe.probe_async = MagicMock(return_value=mock_probe_data)

        # Make probe_async an actual coroutine
        async def mock_probe_async(*args, **kwargs):
            return mock_probe_data

        mock_ffprobe.probe_async = mock_probe_async

        validator = VideoValidator(ffprobe=mock_ffprobe)

        with patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "is_file", return_value=True), \
             patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 10_000_000
            result = await validator.validate_async(Path("test.mp4"))

        assert result.integrity_ok is True
        assert result.video_info is not None


class TestValidationStrictness:
    """Tests for ValidationStrictness enum."""

    def test_strictness_values(self) -> None:
        """Test that strictness enum has expected values."""
        assert ValidationStrictness.QUICK.value == "quick"
        assert ValidationStrictness.STANDARD.value == "standard"
        assert ValidationStrictness.STRICT.value == "strict"
