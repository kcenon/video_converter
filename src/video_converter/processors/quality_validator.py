"""Video quality validation module.

This module provides video file integrity validation using FFprobe to ensure
converted files are playable and not corrupted.

SDS Reference: SDS-P01-003
SRS Reference: SRS-501 (Conversion Result Verification)

Example:
    >>> validator = VideoValidator()
    >>> result = validator.validate(Path("output.mp4"))
    >>> if result.valid:
    ...     print("Video is valid!")
    ... else:
    ...     print(f"Errors: {result.errors}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from video_converter.utils.command_runner import (
    CommandExecutionError,
    CommandNotFoundError,
    FFprobeRunner,
)


class ValidationStrictness(Enum):
    """Validation strictness levels.

    Attributes:
        QUICK: Only check if file is readable (fastest).
        STANDARD: Check integrity and basic properties (default).
        STRICT: Full validation including all streams and metadata.
    """

    QUICK = "quick"
    STANDARD = "standard"
    STRICT = "strict"


@dataclass
class StreamInfo:
    """Information about a media stream.

    Attributes:
        index: Stream index in the file.
        codec_type: Type of stream (video, audio, subtitle, etc.).
        codec_name: Name of the codec (h264, hevc, aac, etc.).
        duration: Duration in seconds (if available).
        bit_rate: Bit rate in bits/second (if available).
        width: Width in pixels (video only).
        height: Height in pixels (video only).
        fps: Frames per second (video only).
        channels: Number of audio channels (audio only).
        sample_rate: Audio sample rate (audio only).
    """

    index: int
    codec_type: str
    codec_name: str
    duration: float | None = None
    bit_rate: int | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    channels: int | None = None
    sample_rate: int | None = None


@dataclass
class VideoInfo:
    """Complete video file information.

    Attributes:
        path: Path to the video file.
        format_name: Container format name.
        duration: Total duration in seconds.
        size: File size in bytes.
        bit_rate: Overall bit rate.
        streams: List of stream information.
        video_streams: List of video stream information.
        audio_streams: List of audio stream information.
    """

    path: Path
    format_name: str
    duration: float
    size: int
    bit_rate: int | None
    streams: list[StreamInfo] = field(default_factory=list)

    @property
    def video_streams(self) -> list[StreamInfo]:
        """Get all video streams."""
        return [s for s in self.streams if s.codec_type == "video"]

    @property
    def audio_streams(self) -> list[StreamInfo]:
        """Get all audio streams."""
        return [s for s in self.streams if s.codec_type == "audio"]

    @property
    def has_video(self) -> bool:
        """Check if file has at least one video stream."""
        return len(self.video_streams) > 0

    @property
    def has_audio(self) -> bool:
        """Check if file has at least one audio stream."""
        return len(self.audio_streams) > 0

    @property
    def primary_video_stream(self) -> StreamInfo | None:
        """Get the primary (first) video stream."""
        streams = self.video_streams
        return streams[0] if streams else None

    @property
    def primary_audio_stream(self) -> StreamInfo | None:
        """Get the primary (first) audio stream."""
        streams = self.audio_streams
        return streams[0] if streams else None


@dataclass
class ValidationResult:
    """Result of video validation.

    Attributes:
        valid: Overall validation result (True if all checks passed).
        integrity_ok: File integrity check passed.
        properties_match: Properties match expected values.
        compression_normal: Compression ratio is within normal range.
        vmaf_score: VMAF quality score (if measured, None otherwise).
        errors: List of error messages (validation failures).
        warnings: List of warning messages (non-critical issues).
        video_info: Parsed video information (if successful).
    """

    valid: bool
    integrity_ok: bool
    properties_match: bool = True
    compression_normal: bool = True
    vmaf_score: float | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    video_info: VideoInfo | None = None

    def add_error(self, message: str) -> None:
        """Add an error message and mark as invalid."""
        self.errors.append(message)
        self.valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)


class VideoValidator:
    """Video file integrity validator using FFprobe.

    This class provides comprehensive validation for video files to ensure
    they are playable and not corrupted. It supports configurable strictness
    levels for different use cases.

    SDS Reference: SDS-P01-003

    Validation Checks:
        1. File existence and size > 0
        2. FFprobe can read the file without errors
        3. Video stream exists and is decodable
        4. Audio stream integrity (if present)
        5. Duration is valid (> 0)
        6. Codec information is extractable

    Example:
        >>> validator = VideoValidator()
        >>> # Quick validation
        >>> if validator.quick_validate(Path("video.mp4")):
        ...     print("Video is playable")
        >>> # Full validation
        >>> result = validator.validate(Path("video.mp4"))
        >>> print(f"Valid: {result.valid}, Errors: {result.errors}")

    Attributes:
        ffprobe: FFprobe runner instance.
        strictness: Validation strictness level.
        timeout: Maximum time for FFprobe commands.
    """

    # Minimum valid duration in seconds
    MIN_DURATION = 0.1

    # Supported video codecs
    SUPPORTED_VIDEO_CODECS = {"h264", "hevc", "h265", "av1", "vp9", "vp8", "mpeg4"}

    # Supported audio codecs
    SUPPORTED_AUDIO_CODECS = {"aac", "mp3", "ac3", "eac3", "flac", "opus", "vorbis", "pcm_s16le"}

    def __init__(
        self,
        *,
        strictness: ValidationStrictness = ValidationStrictness.STANDARD,
        timeout: float = 30.0,
        ffprobe: FFprobeRunner | None = None,
    ) -> None:
        """Initialize the video validator.

        Args:
            strictness: Validation strictness level.
            timeout: Maximum time for FFprobe operations (seconds).
            ffprobe: FFprobe runner to use (creates new one if None).
        """
        self.strictness = strictness
        self.timeout = timeout
        self.ffprobe = ffprobe or FFprobeRunner()

    def quick_validate(self, path: Path) -> bool:
        """Quickly check if a video file is valid.

        This performs a minimal check to see if the file can be opened.
        Use this for fast validation when detailed error information
        is not needed.

        Args:
            path: Path to the video file.

        Returns:
            True if the file appears valid, False otherwise.
        """
        return self.ffprobe.quick_check(path, timeout=self.timeout)

    def validate(
        self,
        path: Path,
        *,
        strictness: ValidationStrictness | None = None,
    ) -> ValidationResult:
        """Validate a video file comprehensively.

        Performs full validation according to the specified strictness level.
        Returns detailed information about any issues found.

        Args:
            path: Path to the video file to validate.
            strictness: Override the default strictness level.

        Returns:
            ValidationResult containing validation details.

        Raises:
            CommandNotFoundError: If FFprobe is not installed.
        """
        level = strictness or self.strictness
        result = ValidationResult(valid=True, integrity_ok=False)

        # Step 1: Check file exists and has size > 0
        if not self._check_file_exists(path, result):
            return result

        # Step 2: Probe the file with FFprobe
        try:
            probe_data = self.ffprobe.probe(
                path,
                show_format=True,
                show_streams=True,
                timeout=self.timeout,
            )
        except CommandNotFoundError:
            raise
        except CommandExecutionError as e:
            result.add_error(f"FFprobe failed: {e.stderr}")
            return result
        except FileNotFoundError:
            result.add_error(f"File not found: {path}")
            return result
        except Exception as e:
            result.add_error(f"Error probing file: {e}")
            return result

        # Step 3: Parse and validate the probe data
        video_info = self._parse_probe_data(path, probe_data, result)
        if video_info is None:
            return result

        result.video_info = video_info
        result.integrity_ok = True

        # Step 4: Validate video streams
        self._validate_video_streams(video_info, result, level)

        # Step 5: Validate audio streams (if strict mode)
        if level in (ValidationStrictness.STANDARD, ValidationStrictness.STRICT):
            self._validate_audio_streams(video_info, result, level)

        # Step 6: Validate duration
        self._validate_duration(video_info, result)

        # Step 7: Additional strict checks
        if level == ValidationStrictness.STRICT:
            self._validate_strict(video_info, result)

        return result

    async def validate_async(
        self,
        path: Path,
        *,
        strictness: ValidationStrictness | None = None,
    ) -> ValidationResult:
        """Validate a video file asynchronously.

        Async version of validate() for use in async contexts.

        Args:
            path: Path to the video file to validate.
            strictness: Override the default strictness level.

        Returns:
            ValidationResult containing validation details.
        """
        level = strictness or self.strictness
        result = ValidationResult(valid=True, integrity_ok=False)

        if not self._check_file_exists(path, result):
            return result

        try:
            probe_data = await self.ffprobe.probe_async(
                path,
                show_format=True,
                show_streams=True,
                timeout=self.timeout,
            )
        except CommandNotFoundError:
            raise
        except CommandExecutionError as e:
            result.add_error(f"FFprobe failed: {e.stderr}")
            return result
        except FileNotFoundError:
            result.add_error(f"File not found: {path}")
            return result
        except Exception as e:
            result.add_error(f"Error probing file: {e}")
            return result

        video_info = self._parse_probe_data(path, probe_data, result)
        if video_info is None:
            return result

        result.video_info = video_info
        result.integrity_ok = True

        self._validate_video_streams(video_info, result, level)

        if level in (ValidationStrictness.STANDARD, ValidationStrictness.STRICT):
            self._validate_audio_streams(video_info, result, level)

        self._validate_duration(video_info, result)

        if level == ValidationStrictness.STRICT:
            self._validate_strict(video_info, result)

        return result

    def _check_file_exists(self, path: Path, result: ValidationResult) -> bool:
        """Check if file exists and has content.

        Args:
            path: Path to check.
            result: ValidationResult to update.

        Returns:
            True if file exists and has size > 0.
        """
        if not path.exists():
            result.add_error(f"File does not exist: {path}")
            return False

        if not path.is_file():
            result.add_error(f"Path is not a file: {path}")
            return False

        size = path.stat().st_size
        if size == 0:
            result.add_error("File is empty (0 bytes)")
            return False

        return True

    def _parse_probe_data(
        self,
        path: Path,
        data: dict[str, Any],
        result: ValidationResult,
    ) -> VideoInfo | None:
        """Parse FFprobe output into VideoInfo.

        Args:
            path: Original file path.
            data: FFprobe JSON output.
            result: ValidationResult to update on errors.

        Returns:
            VideoInfo if parsing succeeded, None otherwise.
        """
        # Check for errors in probe output
        if "error" in data:
            error = data["error"]
            result.add_error(f"FFprobe error: {error.get('string', 'Unknown error')}")
            return None

        # Parse format information
        format_data = data.get("format", {})
        if not format_data:
            result.add_error("No format information found")
            return None

        try:
            duration = float(format_data.get("duration", 0))
        except (ValueError, TypeError):
            duration = 0.0

        try:
            size = int(format_data.get("size", 0))
        except (ValueError, TypeError):
            size = path.stat().st_size if path.exists() else 0

        try:
            bit_rate = int(format_data.get("bit_rate", 0))
        except (ValueError, TypeError):
            bit_rate = None

        video_info = VideoInfo(
            path=path,
            format_name=format_data.get("format_name", "unknown"),
            duration=duration,
            size=size,
            bit_rate=bit_rate,
        )

        # Parse stream information
        streams_data = data.get("streams", [])
        for stream_data in streams_data:
            stream_info = self._parse_stream(stream_data)
            if stream_info:
                video_info.streams.append(stream_info)

        return video_info

    def _parse_stream(self, data: dict[str, Any]) -> StreamInfo | None:
        """Parse a single stream's information.

        Args:
            data: Stream data from FFprobe.

        Returns:
            StreamInfo if parsing succeeded, None otherwise.
        """
        codec_type = data.get("codec_type")
        if not codec_type:
            return None

        # Parse duration
        try:
            duration = float(data.get("duration", 0))
        except (ValueError, TypeError):
            duration = None

        # Parse bit rate
        try:
            bit_rate = int(data.get("bit_rate", 0))
        except (ValueError, TypeError):
            bit_rate = None

        stream_info = StreamInfo(
            index=data.get("index", 0),
            codec_type=codec_type,
            codec_name=data.get("codec_name", "unknown"),
            duration=duration,
            bit_rate=bit_rate,
        )

        # Parse video-specific fields
        if codec_type == "video":
            try:
                stream_info.width = int(data.get("width", 0))
                stream_info.height = int(data.get("height", 0))
            except (ValueError, TypeError):
                pass

            # Parse frame rate
            fps_str = data.get("r_frame_rate", "0/1")
            stream_info.fps = self._parse_frame_rate(fps_str)

        # Parse audio-specific fields
        elif codec_type == "audio":
            try:
                stream_info.channels = int(data.get("channels", 0))
            except (ValueError, TypeError):
                pass

            try:
                stream_info.sample_rate = int(data.get("sample_rate", 0))
            except (ValueError, TypeError):
                pass

        return stream_info

    @staticmethod
    def _parse_frame_rate(fps_str: str) -> float | None:
        """Parse frame rate string (e.g., '30000/1001' or '30').

        Args:
            fps_str: Frame rate string from FFprobe.

        Returns:
            Frame rate as float, or None if parsing fails.
        """
        try:
            if "/" in fps_str:
                num, den = fps_str.split("/")
                if int(den) == 0:
                    return None
                return float(num) / float(den)
            return float(fps_str)
        except (ValueError, TypeError, ZeroDivisionError):
            return None

    def _validate_video_streams(
        self,
        video_info: VideoInfo,
        result: ValidationResult,
        level: ValidationStrictness,
    ) -> None:
        """Validate video streams.

        Args:
            video_info: Parsed video information.
            result: ValidationResult to update.
            level: Validation strictness level.
        """
        if not video_info.has_video:
            result.add_error("No video stream found")
            return

        primary_video = video_info.primary_video_stream
        if primary_video is None:
            result.add_error("Could not access primary video stream")
            return

        # Check codec is recognized
        if primary_video.codec_name == "unknown":
            result.add_error("Unknown video codec")

        # Check resolution (strict mode)
        if level == ValidationStrictness.STRICT:
            if not primary_video.width or not primary_video.height:
                result.add_warning("Could not determine video resolution")
            elif primary_video.width <= 0 or primary_video.height <= 0:
                result.add_error("Invalid video resolution")

        # Check frame rate (strict mode)
        if level == ValidationStrictness.STRICT:
            if primary_video.fps is None or primary_video.fps <= 0:
                result.add_warning("Could not determine frame rate")

    def _validate_audio_streams(
        self,
        video_info: VideoInfo,
        result: ValidationResult,
        level: ValidationStrictness,
    ) -> None:
        """Validate audio streams.

        Args:
            video_info: Parsed video information.
            result: ValidationResult to update.
            level: Validation strictness level.
        """
        if not video_info.has_audio:
            # No audio is a warning, not an error (some videos don't have audio)
            result.add_warning("No audio stream found")
            return

        primary_audio = video_info.primary_audio_stream
        if primary_audio is None:
            return

        # Check audio codec
        if primary_audio.codec_name == "unknown":
            result.add_warning("Unknown audio codec")

        # Strict mode: check channels and sample rate
        if level == ValidationStrictness.STRICT:
            if not primary_audio.channels or primary_audio.channels <= 0:
                result.add_warning("Could not determine audio channels")

            if not primary_audio.sample_rate or primary_audio.sample_rate <= 0:
                result.add_warning("Could not determine audio sample rate")

    def _validate_duration(
        self,
        video_info: VideoInfo,
        result: ValidationResult,
    ) -> None:
        """Validate video duration.

        Args:
            video_info: Parsed video information.
            result: ValidationResult to update.
        """
        if video_info.duration <= 0:
            result.add_error("Invalid duration (0 or negative)")
        elif video_info.duration < self.MIN_DURATION:
            result.add_warning(f"Very short duration: {video_info.duration:.3f}s")

    def _validate_strict(
        self,
        video_info: VideoInfo,
        result: ValidationResult,
    ) -> None:
        """Perform additional strict validation.

        Args:
            video_info: Parsed video information.
            result: ValidationResult to update.
        """
        # Check file size vs duration ratio (detect severely corrupted files)
        if video_info.duration > 0 and video_info.size > 0:
            bytes_per_second = video_info.size / video_info.duration
            # Very low bitrate might indicate corruption
            if bytes_per_second < 1000:  # Less than 8 kbps
                result.add_warning("Unusually low bitrate, file might be corrupted")

        # Check for multiple video streams (unusual, might indicate issues)
        if len(video_info.video_streams) > 1:
            result.add_warning(f"Multiple video streams detected: {len(video_info.video_streams)}")
