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


# Import new classes for property comparison tests
from video_converter.processors.quality_validator import (
    ComparisonSeverity,
    PropertyComparer,
    PropertyComparison,
    PropertyComparisonResult,
)


class TestComparisonSeverity:
    """Tests for ComparisonSeverity enum."""

    def test_severity_values(self) -> None:
        """Test that severity enum has expected values."""
        assert ComparisonSeverity.ERROR.value == "error"
        assert ComparisonSeverity.WARNING.value == "warning"


class TestPropertyComparison:
    """Tests for PropertyComparison dataclass."""

    def test_property_comparison_match(self) -> None:
        """Test creating a matching property comparison."""
        comparison = PropertyComparison(
            property_name="resolution",
            original_value="1920x1080",
            converted_value="1920x1080",
            matches=True,
        )
        assert comparison.matches is True
        assert comparison.severity == ComparisonSeverity.WARNING  # default

    def test_property_comparison_mismatch_error(self) -> None:
        """Test creating a mismatched property comparison with ERROR severity."""
        comparison = PropertyComparison(
            property_name="resolution",
            original_value="1920x1080",
            converted_value="1280x720",
            matches=False,
            severity=ComparisonSeverity.ERROR,
            message="Resolution mismatch: 1920x1080 → 1280x720",
        )
        assert comparison.matches is False
        assert comparison.severity == ComparisonSeverity.ERROR
        assert "1920x1080" in comparison.message

    def test_property_comparison_with_tolerance(self) -> None:
        """Test property comparison with tolerance value."""
        comparison = PropertyComparison(
            property_name="fps",
            original_value=29.97,
            converted_value=29.971,
            matches=True,
            tolerance=0.001,
            severity=ComparisonSeverity.WARNING,
        )
        assert comparison.tolerance == 0.001
        assert comparison.matches is True


class TestPropertyComparisonResult:
    """Tests for PropertyComparisonResult dataclass."""

    def test_empty_result(self) -> None:
        """Test default result is all_match True."""
        result = PropertyComparisonResult()
        assert result.all_match is True
        assert result.comparisons == []
        assert result.errors == []
        assert result.warnings == []

    def test_add_matching_comparison(self) -> None:
        """Test adding a matching comparison."""
        result = PropertyComparisonResult()
        comparison = PropertyComparison(
            property_name="resolution",
            original_value="1920x1080",
            converted_value="1920x1080",
            matches=True,
        )
        result.add_comparison(comparison)

        assert result.all_match is True
        assert len(result.comparisons) == 1
        assert result.errors == []
        assert result.warnings == []

    def test_add_error_comparison(self) -> None:
        """Test adding a mismatched ERROR comparison."""
        result = PropertyComparisonResult()
        comparison = PropertyComparison(
            property_name="resolution",
            original_value="1920x1080",
            converted_value="1280x720",
            matches=False,
            severity=ComparisonSeverity.ERROR,
            message="Resolution mismatch",
        )
        result.add_comparison(comparison)

        assert result.all_match is False
        assert len(result.errors) == 1
        assert "Resolution mismatch" in result.errors[0]

    def test_add_warning_comparison(self) -> None:
        """Test adding a mismatched WARNING comparison."""
        result = PropertyComparisonResult()
        comparison = PropertyComparison(
            property_name="fps",
            original_value=30.0,
            converted_value=29.97,
            matches=False,
            severity=ComparisonSeverity.WARNING,
            message="FPS mismatch",
        )
        result.add_comparison(comparison)

        assert result.all_match is True  # warnings don't affect all_match
        assert len(result.warnings) == 1
        assert result.errors == []


class TestPropertyComparer:
    """Tests for PropertyComparer class."""

    @pytest.fixture
    def comparer(self) -> PropertyComparer:
        """Create a PropertyComparer instance."""
        return PropertyComparer()

    @pytest.fixture
    def matching_video_info(self) -> tuple[VideoInfo, VideoInfo]:
        """Create matching VideoInfo pair."""
        video_stream = StreamInfo(
            index=0,
            codec_type="video",
            codec_name="h264",
            width=1920,
            height=1080,
            fps=30.0,
        )
        audio_stream = StreamInfo(
            index=1,
            codec_type="audio",
            codec_name="aac",
            channels=2,
        )

        original = VideoInfo(
            path=Path("original.mp4"),
            format_name="mp4",
            duration=120.0,
            size=50_000_000,
            bit_rate=3_333_333,
            streams=[video_stream, audio_stream],
        )

        converted = VideoInfo(
            path=Path("converted.mp4"),
            format_name="mp4",
            duration=120.0,
            size=40_000_000,
            bit_rate=2_666_666,
            streams=[video_stream, audio_stream],
        )

        return original, converted

    def test_init_default_tolerances(self) -> None:
        """Test default tolerance values."""
        comparer = PropertyComparer()
        assert comparer.fps_tolerance == 0.001
        assert comparer.duration_tolerance == 0.5

    def test_init_custom_tolerances(self) -> None:
        """Test custom tolerance values."""
        comparer = PropertyComparer(fps_tolerance=0.01, duration_tolerance=1.0)
        assert comparer.fps_tolerance == 0.01
        assert comparer.duration_tolerance == 1.0

    def test_compare_matching_videos(
        self,
        comparer: PropertyComparer,
        matching_video_info: tuple[VideoInfo, VideoInfo],
    ) -> None:
        """Test comparing videos with matching properties."""
        original, converted = matching_video_info
        result = comparer.compare(original, converted)

        assert result.all_match is True
        assert result.errors == []
        assert result.warnings == []
        assert len(result.comparisons) == 6  # resolution, fps, duration, aspect, codec, channels

    def test_compare_resolution_mismatch(self, comparer: PropertyComparer) -> None:
        """Test resolution mismatch detection."""
        orig_stream = StreamInfo(0, "video", "h264", width=1920, height=1080, fps=30.0)
        conv_stream = StreamInfo(0, "video", "h264", width=1280, height=720, fps=30.0)

        original = VideoInfo(
            path=Path("original.mp4"),
            format_name="mp4",
            duration=60.0,
            size=10_000_000,
            bit_rate=None,
            streams=[orig_stream],
        )
        converted = VideoInfo(
            path=Path("converted.mp4"),
            format_name="mp4",
            duration=60.0,
            size=5_000_000,
            bit_rate=None,
            streams=[conv_stream],
        )

        result = comparer.compare(original, converted)

        assert result.all_match is False
        assert any("resolution" in e.lower() for e in result.errors)
        # Note: 1920x1080 and 1280x720 have the same aspect ratio (16:9)

    def test_compare_fps_within_tolerance(self, comparer: PropertyComparer) -> None:
        """Test FPS comparison within tolerance."""
        orig_stream = StreamInfo(0, "video", "h264", width=1920, height=1080, fps=29.970)
        conv_stream = StreamInfo(0, "video", "h264", width=1920, height=1080, fps=29.9705)

        original = VideoInfo(
            path=Path("original.mp4"),
            format_name="mp4",
            duration=60.0,
            size=10_000_000,
            bit_rate=None,
            streams=[orig_stream],
        )
        converted = VideoInfo(
            path=Path("converted.mp4"),
            format_name="mp4",
            duration=60.0,
            size=8_000_000,
            bit_rate=None,
            streams=[conv_stream],
        )

        result = comparer.compare(original, converted)

        fps_comparison = next(c for c in result.comparisons if c.property_name == "fps")
        assert fps_comparison.matches is True

    def test_compare_fps_outside_tolerance(self, comparer: PropertyComparer) -> None:
        """Test FPS comparison outside tolerance."""
        orig_stream = StreamInfo(0, "video", "h264", width=1920, height=1080, fps=30.0)
        conv_stream = StreamInfo(0, "video", "h264", width=1920, height=1080, fps=29.97)

        original = VideoInfo(
            path=Path("original.mp4"),
            format_name="mp4",
            duration=60.0,
            size=10_000_000,
            bit_rate=None,
            streams=[orig_stream],
        )
        converted = VideoInfo(
            path=Path("converted.mp4"),
            format_name="mp4",
            duration=60.0,
            size=8_000_000,
            bit_rate=None,
            streams=[conv_stream],
        )

        result = comparer.compare(original, converted)

        fps_comparison = next(c for c in result.comparisons if c.property_name == "fps")
        assert fps_comparison.matches is False
        assert fps_comparison.severity == ComparisonSeverity.WARNING

    def test_compare_duration_within_tolerance(self, comparer: PropertyComparer) -> None:
        """Test duration comparison within tolerance."""
        stream = StreamInfo(0, "video", "h264", width=1920, height=1080, fps=30.0)

        original = VideoInfo(
            path=Path("original.mp4"),
            format_name="mp4",
            duration=120.0,
            size=10_000_000,
            bit_rate=None,
            streams=[stream],
        )
        converted = VideoInfo(
            path=Path("converted.mp4"),
            format_name="mp4",
            duration=120.3,  # within 0.5s tolerance
            size=8_000_000,
            bit_rate=None,
            streams=[stream],
        )

        result = comparer.compare(original, converted)

        duration_comparison = next(c for c in result.comparisons if c.property_name == "duration")
        assert duration_comparison.matches is True

    def test_compare_duration_outside_tolerance(self, comparer: PropertyComparer) -> None:
        """Test duration comparison outside tolerance."""
        stream = StreamInfo(0, "video", "h264", width=1920, height=1080, fps=30.0)

        original = VideoInfo(
            path=Path("original.mp4"),
            format_name="mp4",
            duration=120.0,
            size=10_000_000,
            bit_rate=None,
            streams=[stream],
        )
        converted = VideoInfo(
            path=Path("converted.mp4"),
            format_name="mp4",
            duration=121.0,  # 1.0s difference, outside tolerance
            size=8_000_000,
            bit_rate=None,
            streams=[stream],
        )

        result = comparer.compare(original, converted)

        duration_comparison = next(c for c in result.comparisons if c.property_name == "duration")
        assert duration_comparison.matches is False
        assert duration_comparison.severity == ComparisonSeverity.WARNING

    def test_compare_audio_codec_mismatch(self, comparer: PropertyComparer) -> None:
        """Test audio codec mismatch detection."""
        video_stream = StreamInfo(0, "video", "h264", width=1920, height=1080, fps=30.0)
        orig_audio = StreamInfo(1, "audio", "aac", channels=2)
        conv_audio = StreamInfo(1, "audio", "mp3", channels=2)

        original = VideoInfo(
            path=Path("original.mp4"),
            format_name="mp4",
            duration=60.0,
            size=10_000_000,
            bit_rate=None,
            streams=[video_stream, orig_audio],
        )
        converted = VideoInfo(
            path=Path("converted.mp4"),
            format_name="mp4",
            duration=60.0,
            size=8_000_000,
            bit_rate=None,
            streams=[video_stream, conv_audio],
        )

        result = comparer.compare(original, converted)

        codec_comparison = next(c for c in result.comparisons if c.property_name == "audio_codec")
        assert codec_comparison.matches is False
        assert codec_comparison.severity == ComparisonSeverity.WARNING

    def test_compare_audio_channels_mismatch(self, comparer: PropertyComparer) -> None:
        """Test audio channels mismatch detection."""
        video_stream = StreamInfo(0, "video", "h264", width=1920, height=1080, fps=30.0)
        orig_audio = StreamInfo(1, "audio", "aac", channels=6)  # 5.1 surround
        conv_audio = StreamInfo(1, "audio", "aac", channels=2)  # stereo

        original = VideoInfo(
            path=Path("original.mp4"),
            format_name="mp4",
            duration=60.0,
            size=10_000_000,
            bit_rate=None,
            streams=[video_stream, orig_audio],
        )
        converted = VideoInfo(
            path=Path("converted.mp4"),
            format_name="mp4",
            duration=60.0,
            size=8_000_000,
            bit_rate=None,
            streams=[video_stream, conv_audio],
        )

        result = comparer.compare(original, converted)

        channels_comparison = next(c for c in result.comparisons if c.property_name == "audio_channels")
        assert channels_comparison.matches is False
        assert channels_comparison.severity == ComparisonSeverity.ERROR
        assert result.all_match is False

    def test_compare_no_audio_both(self, comparer: PropertyComparer) -> None:
        """Test comparing videos without audio streams."""
        video_stream = StreamInfo(0, "video", "h264", width=1920, height=1080, fps=30.0)

        original = VideoInfo(
            path=Path("original.mp4"),
            format_name="mp4",
            duration=60.0,
            size=10_000_000,
            bit_rate=None,
            streams=[video_stream],
        )
        converted = VideoInfo(
            path=Path("converted.mp4"),
            format_name="mp4",
            duration=60.0,
            size=8_000_000,
            bit_rate=None,
            streams=[video_stream],
        )

        result = comparer.compare(original, converted)

        audio_codec = next(c for c in result.comparisons if c.property_name == "audio_codec")
        audio_channels = next(c for c in result.comparisons if c.property_name == "audio_channels")
        assert audio_codec.matches is True
        assert audio_channels.matches is True

    def test_compare_missing_video_stream(self, comparer: PropertyComparer) -> None:
        """Test comparing when one video has no video stream."""
        video_stream = StreamInfo(0, "video", "h264", width=1920, height=1080, fps=30.0)

        original = VideoInfo(
            path=Path("original.mp4"),
            format_name="mp4",
            duration=60.0,
            size=10_000_000,
            bit_rate=None,
            streams=[video_stream],
        )
        converted = VideoInfo(
            path=Path("converted.mp4"),
            format_name="mp4",
            duration=60.0,
            size=8_000_000,
            bit_rate=None,
            streams=[],  # no streams
        )

        result = comparer.compare(original, converted)

        assert result.all_match is False
        resolution_comparison = next(c for c in result.comparisons if c.property_name == "resolution")
        assert resolution_comparison.matches is False

    def test_compare_aspect_ratio_mismatch(self, comparer: PropertyComparer) -> None:
        """Test aspect ratio mismatch detection (same resolution but different)."""
        # 16:9
        orig_stream = StreamInfo(0, "video", "h264", width=1920, height=1080, fps=30.0)
        # 4:3
        conv_stream = StreamInfo(0, "video", "h264", width=1440, height=1080, fps=30.0)

        original = VideoInfo(
            path=Path("original.mp4"),
            format_name="mp4",
            duration=60.0,
            size=10_000_000,
            bit_rate=None,
            streams=[orig_stream],
        )
        converted = VideoInfo(
            path=Path("converted.mp4"),
            format_name="mp4",
            duration=60.0,
            size=8_000_000,
            bit_rate=None,
            streams=[conv_stream],
        )

        result = comparer.compare(original, converted)

        aspect_comparison = next(c for c in result.comparisons if c.property_name == "aspect_ratio")
        assert aspect_comparison.matches is False
        assert aspect_comparison.severity == ComparisonSeverity.ERROR


# Import compression validation classes
from video_converter.processors.quality_validator import (
    CompressionRange,
    CompressionSeverity,
    CompressionValidationResult,
    CompressionValidator,
    ContentType,
)


class TestContentType:
    """Tests for ContentType enum."""

    def test_content_type_values(self) -> None:
        """Test that content type enum has expected values."""
        assert ContentType.STANDARD.value == "standard"
        assert ContentType.HIGH_MOTION.value == "high_motion"
        assert ContentType.LOW_MOTION.value == "low_motion"


class TestCompressionRange:
    """Tests for CompressionRange dataclass."""

    def test_valid_range_creation(self) -> None:
        """Test creating a valid compression range."""
        range_ = CompressionRange(0.30, 0.70, ContentType.STANDARD)
        assert range_.min_ratio == 0.30
        assert range_.max_ratio == 0.70
        assert range_.content_type == ContentType.STANDARD

    def test_range_with_default_content_type(self) -> None:
        """Test compression range with default content type."""
        range_ = CompressionRange(0.20, 0.60)
        assert range_.content_type == ContentType.STANDARD

    def test_invalid_min_ratio_negative(self) -> None:
        """Test that negative min_ratio raises ValueError."""
        with pytest.raises(ValueError, match="min_ratio must be between"):
            CompressionRange(-0.1, 0.70)

    def test_invalid_min_ratio_above_one(self) -> None:
        """Test that min_ratio above 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="min_ratio must be between"):
            CompressionRange(1.1, 0.70)

    def test_invalid_max_ratio_negative(self) -> None:
        """Test that negative max_ratio raises ValueError."""
        with pytest.raises(ValueError, match="max_ratio must be between"):
            CompressionRange(0.30, -0.1)

    def test_invalid_max_ratio_above_one(self) -> None:
        """Test that max_ratio above 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="max_ratio must be between"):
            CompressionRange(0.30, 1.5)

    def test_min_greater_than_max(self) -> None:
        """Test that min_ratio > max_ratio raises ValueError."""
        with pytest.raises(ValueError, match="min_ratio .* must be <= max_ratio"):
            CompressionRange(0.70, 0.30)


class TestCompressionSeverity:
    """Tests for CompressionSeverity enum."""

    def test_severity_values(self) -> None:
        """Test that severity enum has expected values."""
        assert CompressionSeverity.NORMAL.value == "normal"
        assert CompressionSeverity.WARNING.value == "warning"
        assert CompressionSeverity.ERROR.value == "error"


class TestCompressionValidationResult:
    """Tests for CompressionValidationResult dataclass."""

    def test_valid_result_creation(self) -> None:
        """Test creating a valid compression result."""
        result = CompressionValidationResult(
            valid=True,
            compression_ratio=0.50,
            original_size=100_000_000,
            converted_size=50_000_000,
            content_type=ContentType.STANDARD,
            severity=CompressionSeverity.NORMAL,
        )
        assert result.valid is True
        assert result.compression_ratio == 0.50
        assert result.original_size == 100_000_000
        assert result.converted_size == 50_000_000

    def test_size_reduction_percent_property(self) -> None:
        """Test size_reduction_percent property calculation."""
        result = CompressionValidationResult(
            valid=True,
            compression_ratio=0.60,
            original_size=100_000_000,
            converted_size=40_000_000,
            content_type=ContentType.STANDARD,
            severity=CompressionSeverity.NORMAL,
        )
        assert result.size_reduction_percent == 60.0

    def test_file_grew_property_true(self) -> None:
        """Test file_grew property when file increased in size."""
        result = CompressionValidationResult(
            valid=False,
            compression_ratio=-0.20,
            original_size=100_000_000,
            converted_size=120_000_000,
            content_type=ContentType.STANDARD,
            severity=CompressionSeverity.ERROR,
        )
        assert result.file_grew is True

    def test_file_grew_property_false(self) -> None:
        """Test file_grew property when file decreased in size."""
        result = CompressionValidationResult(
            valid=True,
            compression_ratio=0.50,
            original_size=100_000_000,
            converted_size=50_000_000,
            content_type=ContentType.STANDARD,
            severity=CompressionSeverity.NORMAL,
        )
        assert result.file_grew is False


class TestCompressionValidator:
    """Tests for CompressionValidator class."""

    @pytest.fixture
    def validator(self) -> CompressionValidator:
        """Create a CompressionValidator instance."""
        return CompressionValidator()

    def test_init_default_values(self) -> None:
        """Test default initialization values."""
        validator = CompressionValidator()
        assert validator.critical_low == 0.20
        assert validator.critical_high == 0.80
        assert len(validator.ranges) == 3

    def test_init_custom_thresholds(self) -> None:
        """Test custom threshold initialization."""
        validator = CompressionValidator(critical_low=0.15, critical_high=0.85)
        assert validator.critical_low == 0.15
        assert validator.critical_high == 0.85

    def test_init_custom_ranges(self) -> None:
        """Test custom ranges initialization."""
        custom_ranges = {
            ContentType.STANDARD: CompressionRange(0.40, 0.60),
        }
        validator = CompressionValidator(ranges=custom_ranges)
        assert len(validator.ranges) == 1
        assert validator.ranges[ContentType.STANDARD].min_ratio == 0.40

    def test_validate_standard_normal_compression(self, validator: CompressionValidator) -> None:
        """Test validation with normal compression for standard content."""
        # 50% compression - within 30-70% range for standard
        result = validator.validate(100_000_000, 50_000_000)

        assert result.valid is True
        assert result.compression_ratio == 0.50
        assert result.severity == CompressionSeverity.NORMAL
        assert result.content_type == ContentType.STANDARD

    def test_validate_high_motion_normal_compression(self, validator: CompressionValidator) -> None:
        """Test validation with normal compression for high motion content."""
        # 40% compression - within 20-60% range for high_motion
        result = validator.validate(100_000_000, 60_000_000, ContentType.HIGH_MOTION)

        assert result.valid is True
        assert result.compression_ratio == 0.40
        assert result.severity == CompressionSeverity.NORMAL
        assert result.content_type == ContentType.HIGH_MOTION

    def test_validate_low_motion_normal_compression(self, validator: CompressionValidator) -> None:
        """Test validation with normal compression for low motion content."""
        # 60% compression - within 40-80% range for low_motion
        result = validator.validate(100_000_000, 40_000_000, ContentType.LOW_MOTION)

        assert result.valid is True
        assert result.compression_ratio == 0.60
        assert result.severity == CompressionSeverity.NORMAL
        assert result.content_type == ContentType.LOW_MOTION

    def test_validate_file_grew(self, validator: CompressionValidator) -> None:
        """Test validation when file grew after conversion."""
        # File grew by 20%
        result = validator.validate(100_000_000, 120_000_000)

        assert result.valid is False
        assert result.compression_ratio == pytest.approx(-0.20)
        assert result.severity == CompressionSeverity.ERROR
        assert result.file_grew is True
        assert "grew" in result.message.lower()

    def test_validate_very_low_compression(self, validator: CompressionValidator) -> None:
        """Test validation with very low compression (below critical_low)."""
        # 10% compression - below 20% critical threshold
        result = validator.validate(100_000_000, 90_000_000)

        assert result.valid is False
        assert result.compression_ratio == pytest.approx(0.10)
        assert result.severity == CompressionSeverity.ERROR
        assert "very low" in result.message.lower()

    def test_validate_very_high_compression(self, validator: CompressionValidator) -> None:
        """Test validation with very high compression (above critical_high)."""
        # 85% compression - above 80% critical threshold
        result = validator.validate(100_000_000, 15_000_000)

        assert result.valid is True  # Still valid but with warning
        assert result.compression_ratio == 0.85
        assert result.severity == CompressionSeverity.WARNING
        assert "quality loss" in result.message.lower()

    def test_validate_below_expected_range(self, validator: CompressionValidator) -> None:
        """Test validation with compression below expected range."""
        # 25% compression - below 30% min for standard
        result = validator.validate(100_000_000, 75_000_000)

        assert result.valid is True  # Still valid but with warning
        assert result.compression_ratio == 0.25
        assert result.severity == CompressionSeverity.WARNING
        assert "below expected range" in result.message.lower()

    def test_validate_above_expected_range(self, validator: CompressionValidator) -> None:
        """Test validation with compression above expected range."""
        # 75% compression - above 70% max for standard
        result = validator.validate(100_000_000, 25_000_000)

        assert result.valid is True  # Still valid but with warning
        assert result.compression_ratio == 0.75
        assert result.severity == CompressionSeverity.WARNING
        assert "above expected range" in result.message.lower()

    def test_validate_zero_converted_size(self, validator: CompressionValidator) -> None:
        """Test validation with zero converted size (100% compression)."""
        result = validator.validate(100_000_000, 0)

        assert result.valid is True
        assert result.compression_ratio == 1.0
        assert result.severity == CompressionSeverity.WARNING
        assert "quality loss" in result.message.lower()

    def test_validate_invalid_original_size_zero(self, validator: CompressionValidator) -> None:
        """Test that zero original_size raises ValueError."""
        with pytest.raises(ValueError, match="original_size must be positive"):
            validator.validate(0, 50_000_000)

    def test_validate_invalid_original_size_negative(self, validator: CompressionValidator) -> None:
        """Test that negative original_size raises ValueError."""
        with pytest.raises(ValueError, match="original_size must be positive"):
            validator.validate(-100, 50_000_000)

    def test_validate_invalid_converted_size_negative(self, validator: CompressionValidator) -> None:
        """Test that negative converted_size raises ValueError."""
        with pytest.raises(ValueError, match="converted_size cannot be negative"):
            validator.validate(100_000_000, -50)

    def test_validate_expected_range_included(self, validator: CompressionValidator) -> None:
        """Test that expected_range is included in result."""
        result = validator.validate(100_000_000, 50_000_000)

        assert result.expected_range is not None
        assert result.expected_range.min_ratio == 0.30
        assert result.expected_range.max_ratio == 0.70

    def test_get_expected_range(self, validator: CompressionValidator) -> None:
        """Test getting expected range for content type."""
        range_ = validator.get_expected_range(ContentType.STANDARD)

        assert range_ is not None
        assert range_.min_ratio == 0.30
        assert range_.max_ratio == 0.70

    def test_get_expected_range_not_found(self) -> None:
        """Test getting expected range for undefined content type."""
        validator = CompressionValidator(ranges={})
        range_ = validator.get_expected_range(ContentType.STANDARD)

        assert range_ is None

    def test_set_range(self, validator: CompressionValidator) -> None:
        """Test setting custom range for content type."""
        custom_range = CompressionRange(0.50, 0.90, ContentType.STANDARD)
        validator.set_range(ContentType.STANDARD, custom_range)

        assert validator.ranges[ContentType.STANDARD].min_ratio == 0.50
        assert validator.ranges[ContentType.STANDARD].max_ratio == 0.90

    def test_validate_with_custom_critical_thresholds(self) -> None:
        """Test validation with custom critical thresholds."""
        validator = CompressionValidator(critical_low=0.10, critical_high=0.90)

        # 15% compression - would be error with default, but OK with custom
        result = validator.validate(100_000_000, 85_000_000)

        assert result.valid is True
        assert result.severity == CompressionSeverity.WARNING

    def test_validate_same_size(self, validator: CompressionValidator) -> None:
        """Test validation when original and converted sizes are the same."""
        result = validator.validate(100_000_000, 100_000_000)

        assert result.valid is False
        assert result.compression_ratio == 0.0
        assert result.severity == CompressionSeverity.ERROR

    def test_validate_high_motion_edge_cases(self, validator: CompressionValidator) -> None:
        """Test high motion content at range boundaries."""
        # Exactly at min boundary (20%)
        result_min = validator.validate(100_000_000, 80_000_000, ContentType.HIGH_MOTION)
        assert result_min.valid is True
        assert result_min.severity == CompressionSeverity.NORMAL

        # Exactly at max boundary (60%)
        result_max = validator.validate(100_000_000, 40_000_000, ContentType.HIGH_MOTION)
        assert result_max.valid is True
        assert result_max.severity == CompressionSeverity.NORMAL

    def test_validate_low_motion_edge_cases(self, validator: CompressionValidator) -> None:
        """Test low motion content at range boundaries."""
        # Exactly at min boundary (40%)
        result_min = validator.validate(100_000_000, 60_000_000, ContentType.LOW_MOTION)
        assert result_min.valid is True
        assert result_min.severity == CompressionSeverity.NORMAL

        # Exactly at max boundary (80%)
        result_max = validator.validate(100_000_000, 20_000_000, ContentType.LOW_MOTION)
        assert result_max.valid is True
        assert result_max.severity == CompressionSeverity.NORMAL
