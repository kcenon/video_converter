"""Unit tests for folder_extractor module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Check if full dependencies are available for integration-like tests
try:
    from video_converter.processors.codec_detector import CodecDetector  # noqa: F401

    HAS_FULL_DEPS = True
except ImportError:
    HAS_FULL_DEPS = False

requires_full_deps = pytest.mark.skipif(
    not HAS_FULL_DEPS,
    reason="Requires full dependencies (rich, etc.)",
)

from video_converter.extractors.folder_extractor import (
    FolderAccessDeniedError,
    FolderExtractor,
    FolderExtractorError,
    FolderNotFoundError,
    FolderStats,
    FolderVideoInfo,
    InvalidVideoFileError,
)


class TestFolderVideoInfo:
    """Tests for FolderVideoInfo dataclass."""

    def test_video_info_creation(self, tmp_path: Path) -> None:
        """Test creating a video info object."""
        video_file = tmp_path / "vacation.mp4"
        video_file.touch()

        video = FolderVideoInfo(
            path=video_file,
            filename="vacation.mp4",
            size=1024000,
            modified_time=datetime(2024, 1, 15, 10, 30),
            created_time=datetime(2024, 1, 14, 8, 0),
            codec="h264",
            duration=120.5,
            width=1920,
            height=1080,
            fps=29.97,
            bitrate=5000000,
            container="mp4",
        )

        assert video.path == video_file
        assert video.filename == "vacation.mp4"
        assert video.size == 1024000
        assert video.codec == "h264"
        assert video.duration == 120.5
        assert video.width == 1920
        assert video.height == 1080

    def test_is_h264_with_h264_codec(self) -> None:
        """Test is_h264 returns True for H.264 codec."""
        video = FolderVideoInfo(
            path=Path("/video.mp4"),
            filename="video.mp4",
            size=1000,
            modified_time=datetime.now(),
            codec="h264",
        )

        assert video.is_h264 is True
        assert video.is_hevc is False

    def test_is_h264_with_avc_variant(self) -> None:
        """Test is_h264 returns True for AVC codec variant."""
        for codec in ["avc", "avc1", "x264", "H264"]:
            video = FolderVideoInfo(
                path=Path("/video.mp4"),
                filename="video.mp4",
                size=1000,
                modified_time=datetime.now(),
                codec=codec,
            )
            assert video.is_h264 is True, f"Failed for codec: {codec}"

    def test_is_hevc_with_hevc_codec(self) -> None:
        """Test is_hevc returns True for HEVC codec."""
        video = FolderVideoInfo(
            path=Path("/video.mp4"),
            filename="video.mp4",
            size=1000,
            modified_time=datetime.now(),
            codec="hevc",
        )

        assert video.is_hevc is True
        assert video.is_h264 is False

    def test_is_hevc_with_h265_variant(self) -> None:
        """Test is_hevc returns True for H.265 codec variants."""
        for codec in ["h265", "hvc1", "hev1", "x265", "HEVC"]:
            video = FolderVideoInfo(
                path=Path("/video.mp4"),
                filename="video.mp4",
                size=1000,
                modified_time=datetime.now(),
                codec=codec,
            )
            assert video.is_hevc is True, f"Failed for codec: {codec}"

    def test_codec_none_returns_false(self) -> None:
        """Test is_h264 and is_hevc return False when codec is None."""
        video = FolderVideoInfo(
            path=Path("/video.mp4"),
            filename="video.mp4",
            size=1000,
            modified_time=datetime.now(),
            codec=None,
        )

        assert video.is_h264 is False
        assert video.is_hevc is False

    def test_needs_conversion_h264(self) -> None:
        """Test needs_conversion returns True for H.264 video."""
        video = FolderVideoInfo(
            path=Path("/video.mp4"),
            filename="video.mp4",
            size=1000,
            modified_time=datetime.now(),
            codec="h264",
        )

        assert video.needs_conversion is True

    def test_needs_conversion_hevc_returns_false(self) -> None:
        """Test needs_conversion returns False for HEVC video."""
        video = FolderVideoInfo(
            path=Path("/video.mp4"),
            filename="video.mp4",
            size=1000,
            modified_time=datetime.now(),
            codec="hevc",
        )

        assert video.needs_conversion is False

    def test_resolution_label_4k(self) -> None:
        """Test resolution_label returns '4K' for 2160p."""
        video = FolderVideoInfo(
            path=Path("/video.mp4"),
            filename="video.mp4",
            size=1000,
            modified_time=datetime.now(),
            width=3840,
            height=2160,
        )

        assert video.resolution_label == "4K"

    def test_resolution_label_1080p(self) -> None:
        """Test resolution_label returns '1080p' for 1080p."""
        video = FolderVideoInfo(
            path=Path("/video.mp4"),
            filename="video.mp4",
            size=1000,
            modified_time=datetime.now(),
            width=1920,
            height=1080,
        )

        assert video.resolution_label == "1080p"

    def test_resolution_label_720p(self) -> None:
        """Test resolution_label returns '720p' for 720p."""
        video = FolderVideoInfo(
            path=Path("/video.mp4"),
            filename="video.mp4",
            size=1000,
            modified_time=datetime.now(),
            width=1280,
            height=720,
        )

        assert video.resolution_label == "720p"

    def test_resolution_label_unknown(self) -> None:
        """Test resolution_label returns 'unknown' for 0 height."""
        video = FolderVideoInfo(
            path=Path("/video.mp4"),
            filename="video.mp4",
            size=1000,
            modified_time=datetime.now(),
            width=0,
            height=0,
        )

        assert video.resolution_label == "unknown"

    def test_size_mb(self) -> None:
        """Test size_mb returns correct size in megabytes."""
        video = FolderVideoInfo(
            path=Path("/video.mp4"),
            filename="video.mp4",
            size=10 * 1024 * 1024,  # 10 MB
            modified_time=datetime.now(),
        )

        assert video.size_mb == 10.0

    def test_size_gb(self) -> None:
        """Test size_gb returns correct size in gigabytes."""
        video = FolderVideoInfo(
            path=Path("/video.mp4"),
            filename="video.mp4",
            size=2 * 1024 * 1024 * 1024,  # 2 GB
            modified_time=datetime.now(),
        )

        assert video.size_gb == 2.0

    def test_str_representation(self) -> None:
        """Test string representation of FolderVideoInfo."""
        video = FolderVideoInfo(
            path=Path("/video.mp4"),
            filename="video.mp4",
            size=100 * 1024 * 1024,  # 100 MB
            modified_time=datetime.now(),
            codec="h264",
            width=1920,
            height=1080,
        )

        result = str(video)
        assert "video.mp4" in result
        assert "H264" in result
        assert "1080p" in result


class TestFolderStats:
    """Tests for FolderStats dataclass."""

    def test_folder_stats_creation(self) -> None:
        """Test creating FolderStats with values."""
        stats = FolderStats(
            total=100,
            h264=60,
            hevc=30,
            other=5,
            errors=5,
            total_size=10_000_000_000,
            h264_size=6_000_000_000,
        )

        assert stats.total == 100
        assert stats.h264 == 60
        assert stats.hevc == 30
        assert stats.other == 5
        assert stats.errors == 5

    def test_estimated_savings(self) -> None:
        """Test estimated_savings calculation."""
        stats = FolderStats(
            h264_size=10_000_000_000,  # 10 GB
        )

        assert stats.estimated_savings == 5_000_000_000  # 5 GB (50%)

    def test_estimated_savings_gb(self) -> None:
        """Test estimated_savings_gb calculation."""
        stats = FolderStats(
            h264_size=10 * 1024 * 1024 * 1024,  # 10 GB
        )

        assert stats.estimated_savings_gb == 5.0

    def test_total_size_gb(self) -> None:
        """Test total_size_gb calculation."""
        stats = FolderStats(
            total_size=8 * 1024 * 1024 * 1024,  # 8 GB
        )

        assert stats.total_size_gb == 8.0

    def test_default_values(self) -> None:
        """Test default values for FolderStats."""
        stats = FolderStats()

        assert stats.total == 0
        assert stats.h264 == 0
        assert stats.hevc == 0
        assert stats.other == 0
        assert stats.errors == 0
        assert stats.total_size == 0
        assert stats.h264_size == 0


class TestFolderExtractorExceptions:
    """Tests for folder extractor exceptions."""

    def test_folder_not_found_error(self) -> None:
        """Test FolderNotFoundError message includes path."""
        path = Path("/nonexistent/folder")
        error = FolderNotFoundError(path)

        assert "/nonexistent/folder" in str(error)
        assert error.path == path

    def test_folder_access_denied_error(self) -> None:
        """Test FolderAccessDeniedError message includes path."""
        path = Path("/restricted/folder")
        error = FolderAccessDeniedError(path)

        assert "/restricted/folder" in str(error)
        assert error.path == path

    def test_invalid_video_file_error(self) -> None:
        """Test InvalidVideoFileError message includes path and reason."""
        path = Path("/video.mp4")
        error = InvalidVideoFileError(path, "Corrupted header")

        assert "/video.mp4" in str(error)
        assert "Corrupted header" in str(error)
        assert error.path == path
        assert error.reason == "Corrupted header"

    def test_invalid_video_file_error_default_reason(self) -> None:
        """Test InvalidVideoFileError with default reason."""
        path = Path("/video.mp4")
        error = InvalidVideoFileError(path)

        assert "Invalid or corrupted" in str(error)

    def test_exceptions_inherit_from_base(self) -> None:
        """Test all exceptions inherit from FolderExtractorError."""
        assert issubclass(FolderNotFoundError, FolderExtractorError)
        assert issubclass(FolderAccessDeniedError, FolderExtractorError)
        assert issubclass(InvalidVideoFileError, FolderExtractorError)


class TestFolderExtractor:
    """Tests for FolderExtractor class."""

    def test_init_with_valid_path(self, tmp_path: Path) -> None:
        """Test initialization with valid directory path."""
        extractor = FolderExtractor(tmp_path)

        assert extractor.root_path == tmp_path
        assert extractor.recursive is True

    def test_init_with_string_path(self, tmp_path: Path) -> None:
        """Test initialization with string path."""
        extractor = FolderExtractor(str(tmp_path))

        assert extractor.root_path == tmp_path

    def test_init_with_home_expansion(self) -> None:
        """Test initialization expands ~ in path."""
        home = Path.home()
        extractor = FolderExtractor("~")

        assert extractor.root_path == home

    def test_init_nonexistent_path_raises_error(self) -> None:
        """Test initialization with non-existent path raises error."""
        with pytest.raises(FolderNotFoundError) as exc_info:
            FolderExtractor("/nonexistent/path/xyz")

        assert "nonexistent" in str(exc_info.value)

    def test_init_file_path_raises_error(self, tmp_path: Path) -> None:
        """Test initialization with file path raises error."""
        file_path = tmp_path / "file.txt"
        file_path.touch()

        with pytest.raises(FolderNotFoundError):
            FolderExtractor(file_path)

    def test_init_non_recursive(self, tmp_path: Path) -> None:
        """Test initialization with recursive=False."""
        extractor = FolderExtractor(tmp_path, recursive=False)

        assert extractor.recursive is False

    def test_init_custom_video_extensions(self, tmp_path: Path) -> None:
        """Test initialization with custom video extensions."""
        custom_extensions = {".mp4", ".avi"}
        extractor = FolderExtractor(tmp_path, video_extensions=custom_extensions)

        assert extractor._video_extensions == custom_extensions

    def test_init_include_patterns(self, tmp_path: Path) -> None:
        """Test initialization with include patterns."""
        extractor = FolderExtractor(tmp_path, include_patterns=["vacation*", "trip*"])

        assert "vacation*" in extractor._include_patterns
        assert "trip*" in extractor._include_patterns

    def test_init_exclude_patterns(self, tmp_path: Path) -> None:
        """Test initialization with custom exclude patterns."""
        extractor = FolderExtractor(tmp_path, exclude_patterns=["*.tmp", "temp*"])

        assert "*.tmp" in extractor._exclude_patterns
        assert "temp*" in extractor._exclude_patterns

    def test_default_exclude_patterns(self, tmp_path: Path) -> None:
        """Test default exclude patterns are applied."""
        extractor = FolderExtractor(tmp_path)

        assert "*.tmp" in extractor._exclude_patterns
        assert "._*" in extractor._exclude_patterns

    def test_scan_finds_video_files(self, tmp_path: Path) -> None:
        """Test scan finds video files."""
        # Create test video files
        (tmp_path / "video1.mp4").touch()
        (tmp_path / "video2.mov").touch()
        (tmp_path / "document.txt").touch()

        extractor = FolderExtractor(tmp_path)
        files = list(extractor.scan())

        assert len(files) == 2
        filenames = [f.name for f in files]
        assert "video1.mp4" in filenames
        assert "video2.mov" in filenames
        assert "document.txt" not in filenames

    def test_scan_recursive(self, tmp_path: Path) -> None:
        """Test scan finds files in subdirectories."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        (tmp_path / "root.mp4").touch()
        (subdir / "nested.mp4").touch()

        extractor = FolderExtractor(tmp_path, recursive=True)
        files = list(extractor.scan())

        assert len(files) == 2

    def test_scan_non_recursive(self, tmp_path: Path) -> None:
        """Test scan only finds files in root when recursive=False."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        (tmp_path / "root.mp4").touch()
        (subdir / "nested.mp4").touch()

        extractor = FolderExtractor(tmp_path, recursive=False)
        files = list(extractor.scan())

        assert len(files) == 1
        assert files[0].name == "root.mp4"

    def test_scan_excludes_patterns(self, tmp_path: Path) -> None:
        """Test scan excludes files matching exclude patterns."""
        (tmp_path / "video.mp4").touch()
        (tmp_path / "video.mp4.tmp").touch()
        (tmp_path / "._video.mp4").touch()

        extractor = FolderExtractor(tmp_path)
        files = list(extractor.scan())

        assert len(files) == 1
        assert files[0].name == "video.mp4"

    def test_scan_includes_patterns(self, tmp_path: Path) -> None:
        """Test scan only includes files matching include patterns."""
        (tmp_path / "vacation_2024.mp4").touch()
        (tmp_path / "work_meeting.mp4").touch()
        (tmp_path / "trip_paris.mov").touch()

        extractor = FolderExtractor(tmp_path, include_patterns=["vacation*", "trip*"])
        files = list(extractor.scan())

        assert len(files) == 2
        filenames = [f.name for f in files]
        assert "vacation_2024.mp4" in filenames
        assert "trip_paris.mov" in filenames
        assert "work_meeting.mp4" not in filenames

    def test_scan_all_supported_extensions(self, tmp_path: Path) -> None:
        """Test scan finds all supported video extensions."""
        for ext in [".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm"]:
            (tmp_path / f"video{ext}").touch()

        extractor = FolderExtractor(tmp_path)
        files = list(extractor.scan())

        assert len(files) == 6

    def test_get_video_count(self, tmp_path: Path) -> None:
        """Test get_video_count returns correct count."""
        for i in range(5):
            (tmp_path / f"video{i}.mp4").touch()

        extractor = FolderExtractor(tmp_path)
        count = extractor.get_video_count()

        assert count == 5

    @requires_full_deps
    def test_get_video_info(self, tmp_path: Path) -> None:
        """Test get_video_info returns correct information."""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"x" * 1000)

        mock_info = MagicMock()
        mock_info.codec = "h264"
        mock_info.duration = 60.0
        mock_info.width = 1920
        mock_info.height = 1080
        mock_info.fps = 29.97
        mock_info.bitrate = 5000000
        mock_info.container = "mp4"

        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_info

        extractor = FolderExtractor(tmp_path)
        extractor._codec_detector = mock_detector

        # Mock the codec_detector module import to avoid dependency chain issues
        mock_codec_module = MagicMock()
        mock_codec_module.InvalidVideoError = Exception
        mock_codec_module.CorruptedVideoError = Exception
        with patch.dict(
            "sys.modules",
            {"video_converter.processors.codec_detector": mock_codec_module},
        ):
            info = extractor.get_video_info(video_file)

        assert info.filename == "test.mp4"
        assert info.size == 1000
        assert info.codec == "h264"
        assert info.width == 1920
        assert info.height == 1080

    def test_get_video_info_nonexistent_file(self, tmp_path: Path) -> None:
        """Test get_video_info raises for non-existent file."""
        extractor = FolderExtractor(tmp_path)

        with pytest.raises(FileNotFoundError):
            extractor.get_video_info(tmp_path / "nonexistent.mp4")

    @requires_full_deps
    def test_get_video_info_codec_detection_failure(self, tmp_path: Path) -> None:
        """Test get_video_info handles codec detection failure gracefully."""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"invalid data")

        # Create a custom exception class that mimics InvalidVideoError
        class MockInvalidVideoError(Exception):
            pass

        mock_detector = MagicMock()
        mock_detector.analyze.side_effect = MockInvalidVideoError("Not a video")

        extractor = FolderExtractor(tmp_path)
        extractor._codec_detector = mock_detector

        # Mock the codec_detector module to provide our mock exception classes
        mock_codec_module = MagicMock()
        mock_codec_module.InvalidVideoError = MockInvalidVideoError
        mock_codec_module.CorruptedVideoError = MockInvalidVideoError
        with patch.dict(
            "sys.modules",
            {"video_converter.processors.codec_detector": mock_codec_module},
        ):
            info = extractor.get_video_info(video_file)

        # Should still return info but with None codec
        assert info.filename == "test.mp4"
        assert info.codec is None

    @requires_full_deps
    def test_get_videos(self, tmp_path: Path) -> None:
        """Test get_videos returns list of all videos."""
        (tmp_path / "video1.mp4").write_bytes(b"data1")
        (tmp_path / "video2.mov").write_bytes(b"data2")

        mock_info = MagicMock()
        mock_info.codec = "h264"
        mock_info.duration = 60.0
        mock_info.width = 1920
        mock_info.height = 1080
        mock_info.fps = 30.0
        mock_info.bitrate = 5000000
        mock_info.container = "mp4"

        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_info

        extractor = FolderExtractor(tmp_path)
        extractor._codec_detector = mock_detector

        videos = extractor.get_videos()

        assert len(videos) == 2

    @requires_full_deps
    def test_get_conversion_candidates(self, tmp_path: Path) -> None:
        """Test get_conversion_candidates returns only H.264 videos."""
        (tmp_path / "h264_video.mp4").write_bytes(b"h264")
        (tmp_path / "hevc_video.mp4").write_bytes(b"hevc")

        h264_info = MagicMock()
        h264_info.codec = "h264"
        h264_info.duration = 60.0
        h264_info.width = 1920
        h264_info.height = 1080
        h264_info.fps = 30.0
        h264_info.bitrate = 5000000
        h264_info.container = "mp4"

        hevc_info = MagicMock()
        hevc_info.codec = "hevc"
        hevc_info.duration = 60.0
        hevc_info.width = 1920
        hevc_info.height = 1080
        hevc_info.fps = 30.0
        hevc_info.bitrate = 5000000
        hevc_info.container = "mp4"

        mock_detector = MagicMock()
        mock_detector.analyze.side_effect = [h264_info, hevc_info]

        extractor = FolderExtractor(tmp_path)
        extractor._codec_detector = mock_detector

        candidates = extractor.get_conversion_candidates()

        assert len(candidates) == 1
        assert candidates[0].codec == "h264"

    @requires_full_deps
    def test_get_conversion_candidates_with_limit(self, tmp_path: Path) -> None:
        """Test get_conversion_candidates respects limit parameter."""
        for i in range(5):
            (tmp_path / f"video{i}.mp4").write_bytes(b"data")

        mock_info = MagicMock()
        mock_info.codec = "h264"
        mock_info.duration = 60.0
        mock_info.width = 1920
        mock_info.height = 1080
        mock_info.fps = 30.0
        mock_info.bitrate = 5000000
        mock_info.container = "mp4"

        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_info

        extractor = FolderExtractor(tmp_path)
        extractor._codec_detector = mock_detector

        candidates = extractor.get_conversion_candidates(limit=2)

        assert len(candidates) == 2

    @requires_full_deps
    def test_get_stats(self, tmp_path: Path) -> None:
        """Test get_stats returns correct statistics."""
        # Create files with same size to avoid order-dependent assertions
        (tmp_path / "h264_video.mp4").write_bytes(b"x" * 1000)
        (tmp_path / "hevc_video.mp4").write_bytes(b"y" * 500)

        h264_info = MagicMock()
        h264_info.codec = "h264"
        h264_info.duration = 60.0
        h264_info.width = 1920
        h264_info.height = 1080
        h264_info.fps = 30.0
        h264_info.bitrate = 5000000
        h264_info.container = "mp4"

        hevc_info = MagicMock()
        hevc_info.codec = "hevc"
        hevc_info.duration = 60.0
        hevc_info.width = 1920
        hevc_info.height = 1080
        hevc_info.fps = 30.0
        hevc_info.bitrate = 5000000
        hevc_info.container = "mp4"

        # Return based on filename to handle any scan order
        def analyze_side_effect(path: Path) -> MagicMock:
            if "h264" in path.name:
                return h264_info
            return hevc_info

        mock_detector = MagicMock()
        mock_detector.analyze.side_effect = analyze_side_effect

        extractor = FolderExtractor(tmp_path)
        extractor._codec_detector = mock_detector

        stats = extractor.get_stats()

        assert stats.total == 2
        assert stats.h264 == 1
        assert stats.hevc == 1
        assert stats.total_size == 1500
        assert stats.h264_size == 1000

    @requires_full_deps
    def test_get_stats_handles_codec_detection_failure(self, tmp_path: Path) -> None:
        """Test get_stats counts codec detection failures as 'other'.

        When get_video_info fails to detect codec, it returns codec=None
        rather than raising an exception. This is counted as 'other' in stats.
        """
        from video_converter.processors.codec_detector import CorruptedVideoError

        (tmp_path / "good_video.mp4").write_bytes(b"good")
        (tmp_path / "bad_video.mp4").write_bytes(b"bad")

        good_info = MagicMock()
        good_info.codec = "h264"
        good_info.duration = 60.0
        good_info.width = 1920
        good_info.height = 1080
        good_info.fps = 30.0
        good_info.bitrate = 5000000
        good_info.container = "mp4"

        # Return based on filename to handle any scan order
        def analyze_side_effect(path: Path) -> MagicMock:
            if "good" in path.name:
                return good_info
            raise CorruptedVideoError(path, "Corrupted")

        mock_detector = MagicMock()
        mock_detector.analyze.side_effect = analyze_side_effect

        extractor = FolderExtractor(tmp_path)
        extractor._codec_detector = mock_detector

        stats = extractor.get_stats()

        assert stats.total == 2
        assert stats.h264 == 1
        # Codec detection failures result in codec=None, counted as 'other'
        assert stats.other == 1
        assert stats.errors == 0

    def test_context_manager(self, tmp_path: Path) -> None:
        """Test context manager usage."""
        with FolderExtractor(tmp_path) as extractor:
            assert extractor.root_path == tmp_path

    def test_repr(self, tmp_path: Path) -> None:
        """Test repr returns readable string."""
        extractor = FolderExtractor(tmp_path, recursive=False)
        result = repr(extractor)

        assert "FolderExtractor" in result
        assert str(tmp_path) in result
        assert "recursive=False" in result

    @requires_full_deps
    def test_codec_detector_lazy_loading(self, tmp_path: Path) -> None:
        """Test codec_detector is lazily loaded."""
        extractor = FolderExtractor(tmp_path)

        # Should be None initially
        assert extractor._codec_detector is None

        # Access property should create it
        with patch(
            "video_converter.processors.codec_detector.CodecDetector"
        ) as mock_class:
            mock_class.return_value = MagicMock()
            _ = extractor.codec_detector
            mock_class.assert_called_once()


class TestFolderExtractorEdgeCases:
    """Edge case tests for FolderExtractor."""

    def test_empty_folder(self, tmp_path: Path) -> None:
        """Test scan on empty folder returns empty list."""
        extractor = FolderExtractor(tmp_path)
        files = list(extractor.scan())

        assert files == []

    def test_folder_with_only_non_video_files(self, tmp_path: Path) -> None:
        """Test scan on folder with only non-video files."""
        (tmp_path / "document.pdf").touch()
        (tmp_path / "image.jpg").touch()
        (tmp_path / "readme.txt").touch()

        extractor = FolderExtractor(tmp_path)
        files = list(extractor.scan())

        assert files == []

    def test_case_insensitive_extensions(self, tmp_path: Path) -> None:
        """Test scan handles case-insensitive extensions."""
        # Use different filenames to avoid macOS case-insensitive filesystem conflicts
        (tmp_path / "video1.MP4").touch()
        (tmp_path / "video2.MOV").touch()
        (tmp_path / "video3.Mp4").touch()

        extractor = FolderExtractor(tmp_path)
        files = list(extractor.scan())

        assert len(files) == 3

    def test_deeply_nested_directories(self, tmp_path: Path) -> None:
        """Test scan handles deeply nested directories."""
        deep_path = tmp_path / "a" / "b" / "c" / "d" / "e"
        deep_path.mkdir(parents=True)
        (deep_path / "deep_video.mp4").touch()
        (tmp_path / "root_video.mp4").touch()

        extractor = FolderExtractor(tmp_path, recursive=True)
        files = list(extractor.scan())

        assert len(files) == 2

    def test_symlinks_in_directory(self, tmp_path: Path) -> None:
        """Test scan handles symlinks appropriately."""
        video_file = tmp_path / "original.mp4"
        video_file.touch()

        link_path = tmp_path / "link.mp4"
        try:
            link_path.symlink_to(video_file)
        except OSError:
            pytest.skip("Symlinks not supported on this system")

        extractor = FolderExtractor(tmp_path)
        files = list(extractor.scan())

        # Both original and symlink should be found
        assert len(files) >= 1

    def test_special_characters_in_filename(self, tmp_path: Path) -> None:
        """Test scan handles special characters in filenames."""
        special_names = [
            "video with spaces.mp4",
            "video-with-dashes.mp4",
            "video_with_underscores.mp4",
            "video(with)parens.mp4",
        ]

        for name in special_names:
            (tmp_path / name).touch()

        extractor = FolderExtractor(tmp_path)
        files = list(extractor.scan())

        assert len(files) == 4

    def test_unicode_filenames(self, tmp_path: Path) -> None:
        """Test scan handles unicode filenames."""
        (tmp_path / "비디오.mp4").touch()
        (tmp_path / "ビデオ.mov").touch()
        (tmp_path / "vidéo.mkv").touch()

        extractor = FolderExtractor(tmp_path)
        files = list(extractor.scan())

        assert len(files) == 3

    def test_empty_exclude_patterns(self, tmp_path: Path) -> None:
        """Test with empty exclude patterns includes all videos."""
        (tmp_path / "video.mp4").touch()
        (tmp_path / "video.mp4.tmp").touch()  # Would normally be excluded

        extractor = FolderExtractor(tmp_path, exclude_patterns=[])
        files = list(extractor.scan())

        # .tmp files are not video files, so still excluded by extension
        assert len(files) == 1

    def test_both_include_and_exclude_patterns(self, tmp_path: Path) -> None:
        """Test both include and exclude patterns work together."""
        (tmp_path / "vacation_video.mp4").touch()
        (tmp_path / "vacation_temp.mp4").touch()
        (tmp_path / "work_video.mp4").touch()

        extractor = FolderExtractor(
            tmp_path,
            include_patterns=["vacation*"],
            exclude_patterns=["*temp*"],
        )
        files = list(extractor.scan())

        assert len(files) == 1
        assert files[0].name == "vacation_video.mp4"
