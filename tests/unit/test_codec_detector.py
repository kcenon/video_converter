"""Unit tests for codec detector module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_converter.processors.codec_detector import (
    CodecDetector,
    CodecInfo,
    CorruptedVideoError,
    InvalidVideoError,
    UnsupportedCodecError,
)
from video_converter.utils.command_runner import (
    CommandExecutionError,
    CommandNotFoundError,
    FFprobeRunner,
)


class TestCodecInfo:
    """Tests for CodecInfo dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic CodecInfo creation."""
        info = CodecInfo(
            path=Path("video.mp4"),
            codec="h264",
            width=1920,
            height=1080,
            fps=30.0,
            duration=120.0,
            bitrate=5_000_000,
            size=75_000_000,
            audio_codec="aac",
            container="mp4",
        )
        assert info.codec == "h264"
        assert info.width == 1920
        assert info.height == 1080
        assert info.fps == pytest.approx(30.0)
        assert info.duration == pytest.approx(120.0)
        assert info.bitrate == 5_000_000
        assert info.size == 75_000_000
        assert info.audio_codec == "aac"
        assert info.container == "mp4"

    def test_creation_with_optional_fields(self) -> None:
        """Test CodecInfo with all optional fields."""
        creation = datetime(2024, 1, 15, 10, 30, 0)
        info = CodecInfo(
            path=Path("video.mp4"),
            codec="hevc",
            width=3840,
            height=2160,
            fps=60.0,
            duration=180.0,
            bitrate=20_000_000,
            size=450_000_000,
            audio_codec="opus",
            container="mkv",
            creation_time=creation,
            color_space="bt709",
            bit_depth=10,
            profile="Main 10",
            level="5.1",
        )
        assert info.creation_time == creation
        assert info.color_space == "bt709"
        assert info.bit_depth == 10
        assert info.profile == "Main 10"
        assert info.level == "5.1"


class TestCodecInfoIsH264:
    """Tests for is_h264 property."""

    @pytest.mark.parametrize("codec", ["h264", "H264", "avc", "AVC", "avc1", "x264"])
    def test_h264_codecs(self, codec: str) -> None:
        """Test various H.264 codec names."""
        info = CodecInfo(
            path=Path("video.mp4"),
            codec=codec,
            width=1920,
            height=1080,
            fps=30.0,
            duration=120.0,
            bitrate=5_000_000,
            size=75_000_000,
            audio_codec="aac",
            container="mp4",
        )
        assert info.is_h264 is True

    @pytest.mark.parametrize("codec", ["hevc", "vp9", "av1", "mpeg4"])
    def test_non_h264_codecs(self, codec: str) -> None:
        """Test non-H.264 codec names."""
        info = CodecInfo(
            path=Path("video.mp4"),
            codec=codec,
            width=1920,
            height=1080,
            fps=30.0,
            duration=120.0,
            bitrate=5_000_000,
            size=75_000_000,
            audio_codec="aac",
            container="mp4",
        )
        assert info.is_h264 is False


class TestCodecInfoIsHEVC:
    """Tests for is_hevc property."""

    @pytest.mark.parametrize("codec", ["hevc", "HEVC", "h265", "H265", "hvc1", "hev1", "x265"])
    def test_hevc_codecs(self, codec: str) -> None:
        """Test various HEVC codec names."""
        info = CodecInfo(
            path=Path("video.mp4"),
            codec=codec,
            width=1920,
            height=1080,
            fps=30.0,
            duration=120.0,
            bitrate=5_000_000,
            size=75_000_000,
            audio_codec="aac",
            container="mp4",
        )
        assert info.is_hevc is True

    @pytest.mark.parametrize("codec", ["h264", "vp9", "av1", "mpeg4"])
    def test_non_hevc_codecs(self, codec: str) -> None:
        """Test non-HEVC codec names."""
        info = CodecInfo(
            path=Path("video.mp4"),
            codec=codec,
            width=1920,
            height=1080,
            fps=30.0,
            duration=120.0,
            bitrate=5_000_000,
            size=75_000_000,
            audio_codec="aac",
            container="mp4",
        )
        assert info.is_hevc is False


class TestCodecInfoNeedsConversion:
    """Tests for needs_conversion property."""

    def test_h264_needs_conversion(self) -> None:
        """Test that H.264 videos need conversion."""
        info = CodecInfo(
            path=Path("video.mp4"),
            codec="h264",
            width=1920,
            height=1080,
            fps=30.0,
            duration=120.0,
            bitrate=5_000_000,
            size=75_000_000,
            audio_codec="aac",
            container="mp4",
        )
        assert info.needs_conversion is True

    def test_hevc_does_not_need_conversion(self) -> None:
        """Test that HEVC videos don't need conversion."""
        info = CodecInfo(
            path=Path("video.mp4"),
            codec="hevc",
            width=1920,
            height=1080,
            fps=30.0,
            duration=120.0,
            bitrate=5_000_000,
            size=75_000_000,
            audio_codec="aac",
            container="mp4",
        )
        assert info.needs_conversion is False


class TestCodecInfoResolutionLabel:
    """Tests for resolution_label property."""

    @pytest.mark.parametrize(
        "height,expected",
        [
            (2160, "4K"),
            (2200, "4K"),
            (1440, "1440p"),
            (1080, "1080p"),
            (720, "720p"),
            (480, "480p"),
            (360, "360p"),
        ],
    )
    def test_resolution_labels(self, height: int, expected: str) -> None:
        """Test resolution label for various heights."""
        info = CodecInfo(
            path=Path("video.mp4"),
            codec="h264",
            width=1920,
            height=height,
            fps=30.0,
            duration=120.0,
            bitrate=5_000_000,
            size=75_000_000,
            audio_codec="aac",
            container="mp4",
        )
        assert info.resolution_label == expected


class TestCodecInfoAspectRatio:
    """Tests for aspect_ratio property."""

    @pytest.mark.parametrize(
        "width,height,expected",
        [
            (1920, 1080, "16:9"),
            (3840, 2160, "16:9"),
            (1280, 720, "16:9"),
            (1440, 1080, "4:3"),
            (2560, 1080, "64:27"),  # "21:9" is approximate, exact ratio is 64:27
            (1080, 1080, "1:1"),
            (1080, 1920, "9:16"),  # Vertical video
        ],
    )
    def test_common_aspect_ratios(self, width: int, height: int, expected: str) -> None:
        """Test common aspect ratio calculations."""
        info = CodecInfo(
            path=Path("video.mp4"),
            codec="h264",
            width=width,
            height=height,
            fps=30.0,
            duration=120.0,
            bitrate=5_000_000,
            size=75_000_000,
            audio_codec="aac",
            container="mp4",
        )
        assert info.aspect_ratio == expected

    def test_zero_dimensions(self) -> None:
        """Test aspect ratio with zero dimensions."""
        info = CodecInfo(
            path=Path("video.mp4"),
            codec="h264",
            width=0,
            height=1080,
            fps=30.0,
            duration=120.0,
            bitrate=5_000_000,
            size=75_000_000,
            audio_codec="aac",
            container="mp4",
        )
        assert info.aspect_ratio == "unknown"


class TestCodecInfoSizeConversions:
    """Tests for size conversion properties."""

    def test_bitrate_mbps(self) -> None:
        """Test bitrate conversion to Mbps."""
        info = CodecInfo(
            path=Path("video.mp4"),
            codec="h264",
            width=1920,
            height=1080,
            fps=30.0,
            duration=120.0,
            bitrate=50_000_000,  # 50 Mbps
            size=75_000_000,
            audio_codec="aac",
            container="mp4",
        )
        assert info.bitrate_mbps == pytest.approx(50.0)

    def test_size_mb(self) -> None:
        """Test size conversion to MB."""
        info = CodecInfo(
            path=Path("video.mp4"),
            codec="h264",
            width=1920,
            height=1080,
            fps=30.0,
            duration=120.0,
            bitrate=5_000_000,
            size=1024 * 1024 * 100,  # 100 MB
            audio_codec="aac",
            container="mp4",
        )
        assert info.size_mb == pytest.approx(100.0)

    def test_size_gb(self) -> None:
        """Test size conversion to GB."""
        info = CodecInfo(
            path=Path("video.mp4"),
            codec="h264",
            width=1920,
            height=1080,
            fps=30.0,
            duration=120.0,
            bitrate=5_000_000,
            size=1024 * 1024 * 1024 * 2,  # 2 GB
            audio_codec="aac",
            container="mp4",
        )
        assert info.size_gb == pytest.approx(2.0)


class TestCodecInfoStr:
    """Tests for string representation."""

    def test_str_format(self) -> None:
        """Test string format includes key information."""
        info = CodecInfo(
            path=Path("/path/to/video.mp4"),
            codec="h264",
            width=1920,
            height=1080,
            fps=29.97,
            duration=120.5,
            bitrate=5_000_000,
            size=75_000_000,
            audio_codec="aac",
            container="mp4",
        )
        result = str(info)
        assert "video.mp4" in result
        assert "H264" in result
        assert "1080p" in result
        assert "29.97" in result
        assert "120.5" in result


class TestErrorClasses:
    """Tests for error classes."""

    def test_invalid_video_error(self) -> None:
        """Test InvalidVideoError message."""
        path = Path("/path/to/file.txt")
        error = InvalidVideoError(path, "Not a video")
        assert error.path == path
        assert error.reason == "Not a video"
        assert str(path) in str(error)
        assert "Not a video" in str(error)

    def test_corrupted_video_error(self) -> None:
        """Test CorruptedVideoError message."""
        path = Path("/path/to/corrupted.mp4")
        error = CorruptedVideoError(path, "Missing header")
        assert error.path == path
        assert error.reason == "Missing header"
        assert str(path) in str(error)

    def test_unsupported_codec_error(self) -> None:
        """Test UnsupportedCodecError message."""
        path = Path("/path/to/video.mp4")
        error = UnsupportedCodecError(path, "unknown_codec")
        assert error.path == path
        assert error.codec == "unknown_codec"
        assert "unknown_codec" in str(error)


class TestCodecDetector:
    """Tests for CodecDetector class."""

    def _create_mock_probe_data(
        self,
        codec: str = "h264",
        width: int = 1920,
        height: int = 1080,
        fps: str = "30/1",
        duration: str = "120.0",
        bitrate: str = "5000000",
        audio_codec: str = "aac",
        container: str = "mp4",
    ) -> dict:
        """Create mock FFprobe output data."""
        return {
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": codec,
                    "width": width,
                    "height": height,
                    "avg_frame_rate": fps,
                    "duration": duration,
                    "bit_rate": bitrate,
                    "profile": "High",
                    "level": 40,
                },
                {
                    "index": 1,
                    "codec_type": "audio",
                    "codec_name": audio_codec,
                    "channels": 2,
                    "sample_rate": "48000",
                },
            ],
            "format": {
                "format_name": container,
                "duration": duration,
                "size": "75000000",
                "bit_rate": bitrate,
                "tags": {
                    "creation_time": "2024-01-15T10:30:00.000000Z",
                },
            },
        }

    def test_analyze_h264_video(self, tmp_path: Path) -> None:
        """Test analyzing H.264 video."""
        video_path = tmp_path / "test.mp4"
        video_path.write_bytes(b"fake video content")

        mock_runner = MagicMock(spec=FFprobeRunner)
        mock_runner.probe.return_value = self._create_mock_probe_data(codec="h264")

        detector = CodecDetector(ffprobe_runner=mock_runner)
        info = detector.analyze(video_path)

        assert info.codec == "h264"
        assert info.is_h264 is True
        assert info.is_hevc is False
        assert info.needs_conversion is True
        assert info.resolution_label == "1080p"

    def test_analyze_hevc_video(self, tmp_path: Path) -> None:
        """Test analyzing HEVC video."""
        video_path = tmp_path / "test.mp4"
        video_path.write_bytes(b"fake video content")

        mock_runner = MagicMock(spec=FFprobeRunner)
        mock_runner.probe.return_value = self._create_mock_probe_data(codec="hevc")

        detector = CodecDetector(ffprobe_runner=mock_runner)
        info = detector.analyze(video_path)

        assert info.codec == "hevc"
        assert info.is_hevc is True
        assert info.is_h264 is False
        assert info.needs_conversion is False

    def test_analyze_4k_video(self, tmp_path: Path) -> None:
        """Test analyzing 4K video."""
        video_path = tmp_path / "test.mp4"
        video_path.write_bytes(b"fake video content")

        mock_runner = MagicMock(spec=FFprobeRunner)
        mock_runner.probe.return_value = self._create_mock_probe_data(
            width=3840, height=2160
        )

        detector = CodecDetector(ffprobe_runner=mock_runner)
        info = detector.analyze(video_path)

        assert info.width == 3840
        assert info.height == 2160
        assert info.resolution_label == "4K"

    def test_analyze_nonexistent_file(self) -> None:
        """Test analyzing non-existent file raises error."""
        detector = CodecDetector()
        with pytest.raises(FileNotFoundError):
            detector.analyze(Path("/nonexistent/video.mp4"))

    def test_analyze_invalid_video(self, tmp_path: Path) -> None:
        """Test analyzing invalid video raises error."""
        video_path = tmp_path / "invalid.txt"
        video_path.write_text("not a video")

        mock_runner = MagicMock(spec=FFprobeRunner)
        mock_runner.probe.side_effect = CommandExecutionError(
            "ffprobe", 1, "Invalid data found"
        )

        detector = CodecDetector(ffprobe_runner=mock_runner)
        with pytest.raises(InvalidVideoError):
            detector.analyze(video_path)

    def test_analyze_no_video_stream(self, tmp_path: Path) -> None:
        """Test analyzing file with no video stream."""
        video_path = tmp_path / "audio.mp3"
        video_path.write_bytes(b"audio content")

        mock_runner = MagicMock(spec=FFprobeRunner)
        mock_runner.probe.return_value = {
            "streams": [
                {
                    "index": 0,
                    "codec_type": "audio",
                    "codec_name": "mp3",
                },
            ],
            "format": {
                "format_name": "mp3",
                "duration": "180.0",
                "size": "4500000",
            },
        }

        detector = CodecDetector(ffprobe_runner=mock_runner)
        with pytest.raises(InvalidVideoError, match="No video stream"):
            detector.analyze(video_path)

    def test_analyze_missing_codec(self, tmp_path: Path) -> None:
        """Test analyzing video with missing codec info."""
        video_path = tmp_path / "broken.mp4"
        video_path.write_bytes(b"broken content")

        mock_runner = MagicMock(spec=FFprobeRunner)
        mock_runner.probe.return_value = {
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "",  # Missing codec
                    "width": 1920,
                    "height": 1080,
                },
            ],
            "format": {
                "format_name": "mp4",
                "duration": "120.0",
                "size": "75000000",
            },
        }

        detector = CodecDetector(ffprobe_runner=mock_runner)
        with pytest.raises(CorruptedVideoError, match="codec not detected"):
            detector.analyze(video_path)

    def test_analyze_invalid_dimensions(self, tmp_path: Path) -> None:
        """Test analyzing video with invalid dimensions."""
        video_path = tmp_path / "bad_dims.mp4"
        video_path.write_bytes(b"content")

        mock_runner = MagicMock(spec=FFprobeRunner)
        mock_runner.probe.return_value = {
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 0,  # Invalid
                    "height": 0,  # Invalid
                },
            ],
            "format": {
                "format_name": "mp4",
                "duration": "120.0",
                "size": "75000000",
            },
        }

        detector = CodecDetector(ffprobe_runner=mock_runner)
        with pytest.raises(CorruptedVideoError, match="Invalid video dimensions"):
            detector.analyze(video_path)

    def test_analyze_invalid_duration(self, tmp_path: Path) -> None:
        """Test analyzing video with invalid duration."""
        video_path = tmp_path / "bad_dur.mp4"
        video_path.write_bytes(b"content")

        mock_runner = MagicMock(spec=FFprobeRunner)
        mock_runner.probe.return_value = {
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                },
            ],
            "format": {
                "format_name": "mp4",
                "duration": "0",  # Invalid
                "size": "75000000",
            },
        }

        detector = CodecDetector(ffprobe_runner=mock_runner)
        with pytest.raises(CorruptedVideoError, match="Invalid video duration"):
            detector.analyze(video_path)


class TestCodecDetectorConvenienceMethods:
    """Tests for convenience methods."""

    def _create_detector_with_mock(
        self, codec: str, tmp_path: Path
    ) -> tuple[CodecDetector, Path]:
        """Create detector with mock and test file."""
        video_path = tmp_path / "test.mp4"
        video_path.write_bytes(b"content")

        mock_runner = MagicMock(spec=FFprobeRunner)
        mock_runner.probe.return_value = {
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": codec,
                    "width": 1920,
                    "height": 1080,
                    "avg_frame_rate": "30/1",
                    "duration": "120.0",
                },
            ],
            "format": {
                "format_name": "mp4",
                "duration": "120.0",
                "size": "75000000",
            },
        }

        return CodecDetector(ffprobe_runner=mock_runner), video_path

    def test_is_h264_true(self, tmp_path: Path) -> None:
        """Test is_h264 returns True for H.264."""
        detector, video_path = self._create_detector_with_mock("h264", tmp_path)
        assert detector.is_h264(video_path) is True

    def test_is_h264_false(self, tmp_path: Path) -> None:
        """Test is_h264 returns False for HEVC."""
        detector, video_path = self._create_detector_with_mock("hevc", tmp_path)
        assert detector.is_h264(video_path) is False

    def test_is_hevc_true(self, tmp_path: Path) -> None:
        """Test is_hevc returns True for HEVC."""
        detector, video_path = self._create_detector_with_mock("hevc", tmp_path)
        assert detector.is_hevc(video_path) is True

    def test_is_hevc_false(self, tmp_path: Path) -> None:
        """Test is_hevc returns False for H.264."""
        detector, video_path = self._create_detector_with_mock("h264", tmp_path)
        assert detector.is_hevc(video_path) is False

    def test_needs_conversion(self, tmp_path: Path) -> None:
        """Test needs_conversion returns True for H.264."""
        detector, video_path = self._create_detector_with_mock("h264", tmp_path)
        assert detector.needs_conversion(video_path) is True

    def test_get_codec(self, tmp_path: Path) -> None:
        """Test get_codec returns codec name."""
        detector, video_path = self._create_detector_with_mock("h264", tmp_path)
        assert detector.get_codec(video_path) == "h264"

    def test_is_h264_handles_error(self, tmp_path: Path) -> None:
        """Test is_h264 returns False on error."""
        detector = CodecDetector()
        assert detector.is_h264(tmp_path / "nonexistent.mp4") is False


class TestCodecDetectorFrameRateParsing:
    """Tests for frame rate parsing."""

    def test_parse_fractional_fps(self, tmp_path: Path) -> None:
        """Test parsing fractional frame rate like 30000/1001."""
        video_path = tmp_path / "test.mp4"
        video_path.write_bytes(b"content")

        mock_runner = MagicMock(spec=FFprobeRunner)
        mock_runner.probe.return_value = {
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "avg_frame_rate": "30000/1001",  # ~29.97 fps
                    "duration": "120.0",
                },
            ],
            "format": {
                "format_name": "mp4",
                "duration": "120.0",
                "size": "75000000",
            },
        }

        detector = CodecDetector(ffprobe_runner=mock_runner)
        info = detector.analyze(video_path)
        assert info.fps == pytest.approx(29.97, rel=0.01)

    def test_parse_integer_fps(self, tmp_path: Path) -> None:
        """Test parsing integer frame rate like 60/1."""
        video_path = tmp_path / "test.mp4"
        video_path.write_bytes(b"content")

        mock_runner = MagicMock(spec=FFprobeRunner)
        mock_runner.probe.return_value = {
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "avg_frame_rate": "60/1",
                    "duration": "120.0",
                },
            ],
            "format": {
                "format_name": "mp4",
                "duration": "120.0",
                "size": "75000000",
            },
        }

        detector = CodecDetector(ffprobe_runner=mock_runner)
        info = detector.analyze(video_path)
        assert info.fps == pytest.approx(60.0)


class TestCodecDetectorContainerParsing:
    """Tests for container format parsing."""

    def test_parse_single_format(self, tmp_path: Path) -> None:
        """Test parsing single format name."""
        video_path = tmp_path / "test.mp4"
        video_path.write_bytes(b"content")

        mock_runner = MagicMock(spec=FFprobeRunner)
        mock_runner.probe.return_value = {
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "avg_frame_rate": "30/1",
                    "duration": "120.0",
                },
            ],
            "format": {
                "format_name": "mp4",
                "duration": "120.0",
                "size": "75000000",
            },
        }

        detector = CodecDetector(ffprobe_runner=mock_runner)
        info = detector.analyze(video_path)
        assert info.container == "mp4"

    def test_parse_comma_separated_formats(self, tmp_path: Path) -> None:
        """Test parsing comma-separated format names."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"content")

        mock_runner = MagicMock(spec=FFprobeRunner)
        mock_runner.probe.return_value = {
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "avg_frame_rate": "30/1",
                    "duration": "120.0",
                },
            ],
            "format": {
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2",  # QuickTime output
                "duration": "120.0",
                "size": "75000000",
            },
        }

        detector = CodecDetector(ffprobe_runner=mock_runner)
        info = detector.analyze(video_path)
        assert info.container == "mov"


class TestCodecDetectorCreationTimeParsing:
    """Tests for creation time parsing."""

    def test_parse_iso_creation_time(self, tmp_path: Path) -> None:
        """Test parsing ISO 8601 creation time."""
        video_path = tmp_path / "test.mp4"
        video_path.write_bytes(b"content")

        mock_runner = MagicMock(spec=FFprobeRunner)
        mock_runner.probe.return_value = {
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "avg_frame_rate": "30/1",
                    "duration": "120.0",
                },
            ],
            "format": {
                "format_name": "mp4",
                "duration": "120.0",
                "size": "75000000",
                "tags": {
                    "creation_time": "2024-06-15T14:30:00.000000Z",
                },
            },
        }

        detector = CodecDetector(ffprobe_runner=mock_runner)
        info = detector.analyze(video_path)
        assert info.creation_time is not None
        assert info.creation_time.year == 2024
        assert info.creation_time.month == 6
        assert info.creation_time.day == 15

    def test_missing_creation_time(self, tmp_path: Path) -> None:
        """Test handling missing creation time."""
        video_path = tmp_path / "test.mp4"
        video_path.write_bytes(b"content")

        mock_runner = MagicMock(spec=FFprobeRunner)
        mock_runner.probe.return_value = {
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "avg_frame_rate": "30/1",
                    "duration": "120.0",
                },
            ],
            "format": {
                "format_name": "mp4",
                "duration": "120.0",
                "size": "75000000",
            },
        }

        detector = CodecDetector(ffprobe_runner=mock_runner)
        info = detector.analyze(video_path)
        assert info.creation_time is None


class TestCodecDetectorLevelParsing:
    """Tests for codec level parsing."""

    def test_parse_level_40(self, tmp_path: Path) -> None:
        """Test parsing level 40 -> 4.0."""
        video_path = tmp_path / "test.mp4"
        video_path.write_bytes(b"content")

        mock_runner = MagicMock(spec=FFprobeRunner)
        mock_runner.probe.return_value = {
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "avg_frame_rate": "30/1",
                    "duration": "120.0",
                    "level": 40,
                },
            ],
            "format": {
                "format_name": "mp4",
                "duration": "120.0",
                "size": "75000000",
            },
        }

        detector = CodecDetector(ffprobe_runner=mock_runner)
        info = detector.analyze(video_path)
        assert info.level == "4.0"

    def test_parse_level_51(self, tmp_path: Path) -> None:
        """Test parsing level 51 -> 5.1."""
        video_path = tmp_path / "test.mp4"
        video_path.write_bytes(b"content")

        mock_runner = MagicMock(spec=FFprobeRunner)
        mock_runner.probe.return_value = {
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "hevc",
                    "width": 3840,
                    "height": 2160,
                    "avg_frame_rate": "60/1",
                    "duration": "120.0",
                    "level": 51,
                },
            ],
            "format": {
                "format_name": "mp4",
                "duration": "120.0",
                "size": "750000000",
            },
        }

        detector = CodecDetector(ffprobe_runner=mock_runner)
        info = detector.analyze(video_path)
        assert info.level == "5.1"
