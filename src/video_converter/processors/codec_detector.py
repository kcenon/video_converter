"""Video codec detection module using FFprobe.

This module provides codec detection functionality to analyze video files
and determine their codec, resolution, and other properties. It is used
to identify H.264 videos that need conversion to H.265/HEVC.

SDS Reference: SDS-P01-002
SRS Reference: SRS-201 (Codec Detection)

Example:
    >>> from video_converter.processors.codec_detector import CodecDetector
    >>> detector = CodecDetector()
    >>> info = detector.analyze(Path("vacation.mp4"))
    >>> print(f"Codec: {info.codec}")           # "h264"
    >>> print(f"Resolution: {info.resolution_label}")  # "4K"
    >>> print(f"Needs conversion: {info.is_h264}")  # True
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from video_converter.utils.command_runner import (
    CommandExecutionError,
    CommandNotFoundError,
    FFprobeRunner,
)


class InvalidVideoError(Exception):
    """Raised when a file is not a valid video.

    This error indicates that the file cannot be recognized as a valid
    video format by FFprobe.

    Attributes:
        path: Path to the invalid file.
        reason: Explanation of why the file is invalid.
    """

    def __init__(self, path: Path, reason: str = "Not a valid video file") -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"{path}: {reason}")


class CorruptedVideoError(Exception):
    """Raised when a video file is corrupted or incomplete.

    This error indicates that while the file is recognized as a video,
    it cannot be properly read or is missing critical data.

    Attributes:
        path: Path to the corrupted file.
        reason: Explanation of the corruption.
    """

    def __init__(self, path: Path, reason: str = "Video file is corrupted") -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"{path}: {reason}")


class UnsupportedCodecError(Exception):
    """Raised when an unknown or unsupported codec is encountered.

    This error indicates that the video uses a codec that is not
    recognized or supported by the converter.

    Attributes:
        path: Path to the video file.
        codec: The unsupported codec name.
    """

    def __init__(self, path: Path, codec: str) -> None:
        self.path = path
        self.codec = codec
        super().__init__(f"{path}: Unsupported codec '{codec}'")


@dataclass
class CodecInfo:
    """Video codec and property information.

    This class contains detailed information about a video file's codec
    and properties, used to determine if conversion is needed.

    Attributes:
        path: Path to the video file.
        codec: Video codec name (e.g., "h264", "hevc", "vp9").
        width: Video width in pixels.
        height: Video height in pixels.
        fps: Frames per second.
        duration: Duration in seconds.
        bitrate: Video bitrate in bits per second.
        size: File size in bytes.
        audio_codec: Audio codec name (e.g., "aac", "opus").
        container: Container format (e.g., "mp4", "mov", "mkv").
        creation_time: Recording timestamp (if available).
        color_space: Video color space (if available).
        bit_depth: Video bit depth (if available).
        profile: Codec profile (e.g., "High", "Main").
        level: Codec level (e.g., "4.0", "5.1").

    Example:
        >>> info = CodecInfo(
        ...     path=Path("video.mp4"),
        ...     codec="h264",
        ...     width=3840,
        ...     height=2160,
        ...     fps=29.97,
        ...     duration=180.5,
        ...     bitrate=50_000_000,
        ...     size=1_125_000_000,
        ...     audio_codec="aac",
        ...     container="mp4"
        ... )
        >>> print(f"Resolution: {info.resolution_label}")  # "4K"
        >>> print(f"Needs conversion: {info.is_h264}")  # True
    """

    path: Path
    codec: str
    width: int
    height: int
    fps: float
    duration: float
    bitrate: int
    size: int
    audio_codec: str | None
    container: str
    creation_time: datetime | None = None
    color_space: str | None = None
    bit_depth: int | None = None
    profile: str | None = None
    level: str | None = None

    # Codec name variations for identification
    H264_CODECS = frozenset({"h264", "avc", "avc1", "x264"})
    HEVC_CODECS = frozenset({"hevc", "h265", "hvc1", "hev1", "x265"})

    @property
    def is_h264(self) -> bool:
        """Check if video codec is H.264/AVC.

        Returns:
            True if the codec is any variant of H.264.
        """
        return self.codec.lower() in self.H264_CODECS

    @property
    def is_hevc(self) -> bool:
        """Check if video codec is H.265/HEVC.

        Returns:
            True if the codec is any variant of H.265/HEVC.
        """
        return self.codec.lower() in self.HEVC_CODECS

    @property
    def needs_conversion(self) -> bool:
        """Check if video needs H.265 conversion.

        Returns:
            True if the video is H.264 and would benefit from conversion.
        """
        return self.is_h264

    @property
    def resolution_label(self) -> str:
        """Get human-readable resolution label.

        Returns:
            Resolution label like "4K", "1080p", "720p", etc.
        """
        if self.height >= 2160:
            return "4K"
        elif self.height >= 1440:
            return "1440p"
        elif self.height >= 1080:
            return "1080p"
        elif self.height >= 720:
            return "720p"
        elif self.height >= 480:
            return "480p"
        return f"{self.height}p"

    @property
    def aspect_ratio(self) -> str:
        """Calculate aspect ratio.

        Returns:
            Aspect ratio string like "16:9", "4:3", etc.
        """
        from math import gcd

        if self.width == 0 or self.height == 0:
            return "unknown"

        divisor = gcd(self.width, self.height)
        w = self.width // divisor
        h = self.height // divisor

        # Common ratios
        common_ratios = {
            (16, 9): "16:9",
            (4, 3): "4:3",
            (21, 9): "21:9",
            (1, 1): "1:1",
            (9, 16): "9:16",
        }

        return common_ratios.get((w, h), f"{w}:{h}")

    @property
    def bitrate_mbps(self) -> float:
        """Get bitrate in Mbps.

        Returns:
            Bitrate in megabits per second.
        """
        return self.bitrate / 1_000_000

    @property
    def size_mb(self) -> float:
        """Get file size in MB.

        Returns:
            File size in megabytes.
        """
        return self.size / (1024 * 1024)

    @property
    def size_gb(self) -> float:
        """Get file size in GB.

        Returns:
            File size in gigabytes.
        """
        return self.size / (1024 * 1024 * 1024)

    def __str__(self) -> str:
        """Return human-readable summary."""
        return (
            f"{self.path.name}: {self.codec.upper()} {self.resolution_label} "
            f"@ {self.fps:.2f}fps, {self.duration:.1f}s, {self.size_mb:.1f}MB"
        )


class CodecDetector:
    """Video codec detector using FFprobe.

    This class analyzes video files to extract codec information
    and determine if conversion to H.265/HEVC is needed.

    SDS Reference: SDS-P01-002

    Example:
        >>> detector = CodecDetector()
        >>> info = detector.analyze(Path("vacation.mp4"))
        >>> if info.needs_conversion:
        ...     print(f"Converting {info.path.name} from {info.codec} to HEVC")
        ...
        >>> # Batch analysis
        >>> videos = list(Path("videos").glob("*.mp4"))
        >>> h264_videos = [v for v in videos if detector.analyze(v).is_h264]

    Attributes:
        ffprobe: FFprobe runner instance.
        timeout: Default timeout for FFprobe commands.
    """

    # Supported container formats
    SUPPORTED_CONTAINERS = frozenset({"mp4", "mov", "m4v", "mkv", "avi", "webm", "mts", "m2ts"})

    def __init__(
        self,
        ffprobe_runner: FFprobeRunner | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Initialize CodecDetector.

        Args:
            ffprobe_runner: FFprobe runner to use. If None, creates a new one.
            timeout: Default timeout for FFprobe commands in seconds.
        """
        self._ffprobe = ffprobe_runner or FFprobeRunner()
        self._timeout = timeout

    def analyze(self, path: Path) -> CodecInfo:
        """Analyze a video file and return codec information.

        Args:
            path: Path to the video file.

        Returns:
            CodecInfo containing video properties.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            InvalidVideoError: If the file is not a valid video.
            CorruptedVideoError: If the video file is corrupted.
            CommandNotFoundError: If FFprobe is not installed.
        """
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {path}")

        try:
            probe_data = self._ffprobe.probe(
                path,
                show_format=True,
                show_streams=True,
                timeout=self._timeout,
            )
        except CommandExecutionError as e:
            raise InvalidVideoError(path, f"FFprobe failed: {e.stderr}") from e
        except CommandNotFoundError:
            raise

        return self._parse_probe_data(path, probe_data)

    async def analyze_async(self, path: Path) -> CodecInfo:
        """Analyze a video file asynchronously.

        Args:
            path: Path to the video file.

        Returns:
            CodecInfo containing video properties.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            InvalidVideoError: If the file is not a valid video.
            CorruptedVideoError: If the video file is corrupted.
            CommandNotFoundError: If FFprobe is not installed.
        """
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {path}")

        try:
            probe_data = await self._ffprobe.probe_async(
                path,
                show_format=True,
                show_streams=True,
                timeout=self._timeout,
            )
        except CommandExecutionError as e:
            raise InvalidVideoError(path, f"FFprobe failed: {e.stderr}") from e
        except CommandNotFoundError:
            raise

        return self._parse_probe_data(path, probe_data)

    def is_h264(self, path: Path) -> bool:
        """Quick check if a video is H.264 encoded.

        Args:
            path: Path to the video file.

        Returns:
            True if the video is H.264, False otherwise.
        """
        try:
            info = self.analyze(path)
            return info.is_h264
        except (InvalidVideoError, CorruptedVideoError, FileNotFoundError):
            return False

    def is_hevc(self, path: Path) -> bool:
        """Quick check if a video is H.265/HEVC encoded.

        Args:
            path: Path to the video file.

        Returns:
            True if the video is HEVC, False otherwise.
        """
        try:
            info = self.analyze(path)
            return info.is_hevc
        except (InvalidVideoError, CorruptedVideoError, FileNotFoundError):
            return False

    def needs_conversion(self, path: Path) -> bool:
        """Check if a video needs conversion to H.265.

        Args:
            path: Path to the video file.

        Returns:
            True if the video is H.264 and should be converted.
        """
        return self.is_h264(path)

    def get_codec(self, path: Path) -> str:
        """Get the video codec name.

        Args:
            path: Path to the video file.

        Returns:
            Codec name (e.g., "h264", "hevc").

        Raises:
            InvalidVideoError: If the file is not a valid video.
        """
        return self.analyze(path).codec

    def _parse_probe_data(self, path: Path, data: dict[str, Any]) -> CodecInfo:
        """Parse FFprobe output into CodecInfo.

        Args:
            path: Path to the video file.
            data: FFprobe JSON output.

        Returns:
            CodecInfo with parsed video properties.

        Raises:
            InvalidVideoError: If no video stream found.
            CorruptedVideoError: If required data is missing.
        """
        streams = data.get("streams", [])
        format_info = data.get("format", {})

        # Find video stream
        video_stream = self._find_video_stream(streams)
        if video_stream is None:
            raise InvalidVideoError(path, "No video stream found")

        # Find audio stream (optional)
        audio_stream = self._find_audio_stream(streams)

        # Extract video codec
        codec = video_stream.get("codec_name", "")
        if not codec:
            raise CorruptedVideoError(path, "Video codec not detected")

        # Extract dimensions
        width = video_stream.get("width", 0)
        height = video_stream.get("height", 0)
        if width == 0 or height == 0:
            raise CorruptedVideoError(path, "Invalid video dimensions")

        # Extract frame rate
        fps = self._parse_frame_rate(video_stream)

        # Extract duration
        duration = self._parse_duration(video_stream, format_info)
        if duration <= 0:
            raise CorruptedVideoError(path, "Invalid video duration")

        # Extract bitrate
        bitrate = self._parse_bitrate(video_stream, format_info)

        # Extract file size
        size = int(format_info.get("size", 0))
        if size == 0:
            size = path.stat().st_size

        # Extract audio codec
        audio_codec = audio_stream.get("codec_name") if audio_stream else None

        # Extract container format
        container = self._parse_container(format_info)

        # Extract creation time
        creation_time = self._parse_creation_time(format_info)

        # Extract additional properties
        color_space = video_stream.get("color_space")
        bit_depth = self._parse_bit_depth(video_stream)
        profile = video_stream.get("profile")
        level = self._parse_level(video_stream)

        return CodecInfo(
            path=path,
            codec=codec,
            width=width,
            height=height,
            fps=fps,
            duration=duration,
            bitrate=bitrate,
            size=size,
            audio_codec=audio_codec,
            container=container,
            creation_time=creation_time,
            color_space=color_space,
            bit_depth=bit_depth,
            profile=profile,
            level=level,
        )

    def _find_video_stream(self, streams: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Find the first video stream.

        Args:
            streams: List of stream dictionaries.

        Returns:
            Video stream dictionary or None if not found.
        """
        for stream in streams:
            if stream.get("codec_type") == "video":
                return stream
        return None

    def _find_audio_stream(self, streams: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Find the first audio stream.

        Args:
            streams: List of stream dictionaries.

        Returns:
            Audio stream dictionary or None if not found.
        """
        for stream in streams:
            if stream.get("codec_type") == "audio":
                return stream
        return None

    def _parse_frame_rate(self, stream: dict[str, Any]) -> float:
        """Parse frame rate from stream data.

        Handles various FFprobe output formats for frame rate.

        Args:
            stream: Video stream dictionary.

        Returns:
            Frame rate in fps.
        """
        # Try avg_frame_rate first (most accurate)
        avg_fps = stream.get("avg_frame_rate", "0/1")
        if "/" in str(avg_fps):
            num, den = str(avg_fps).split("/")
            if float(den) > 0:
                return float(num) / float(den)

        # Fall back to r_frame_rate
        r_fps = stream.get("r_frame_rate", "0/1")
        if "/" in str(r_fps):
            num, den = str(r_fps).split("/")
            if float(den) > 0:
                return float(num) / float(den)

        return 0.0

    def _parse_duration(
        self,
        stream: dict[str, Any],
        format_info: dict[str, Any],
    ) -> float:
        """Parse duration from stream or format data.

        Args:
            stream: Video stream dictionary.
            format_info: Format information dictionary.

        Returns:
            Duration in seconds.
        """
        # Try stream duration first
        duration = stream.get("duration")
        if duration is not None:
            try:
                return float(duration)
            except (ValueError, TypeError):
                pass

        # Fall back to format duration
        duration = format_info.get("duration")
        if duration is not None:
            try:
                return float(duration)
            except (ValueError, TypeError):
                pass

        return 0.0

    def _parse_bitrate(
        self,
        stream: dict[str, Any],
        format_info: dict[str, Any],
    ) -> int:
        """Parse bitrate from stream or format data.

        Args:
            stream: Video stream dictionary.
            format_info: Format information dictionary.

        Returns:
            Bitrate in bits per second.
        """
        # Try stream bitrate first
        bitrate = stream.get("bit_rate")
        if bitrate is not None:
            try:
                return int(bitrate)
            except (ValueError, TypeError):
                pass

        # Fall back to format bitrate
        bitrate = format_info.get("bit_rate")
        if bitrate is not None:
            try:
                return int(bitrate)
            except (ValueError, TypeError):
                pass

        return 0

    def _parse_container(self, format_info: dict[str, Any]) -> str:
        """Parse container format from format data.

        Args:
            format_info: Format information dictionary.

        Returns:
            Container format name.
        """
        format_name: str = format_info.get("format_name", "")

        # Handle comma-separated format names
        if "," in format_name:
            formats = format_name.split(",")
            # Prefer common formats
            for fmt in formats:
                if fmt in self.SUPPORTED_CONTAINERS:
                    return fmt
            return formats[0]

        return format_name

    def _parse_creation_time(self, format_info: dict[str, Any]) -> datetime | None:
        """Parse creation time from format tags.

        Args:
            format_info: Format information dictionary.

        Returns:
            Creation datetime or None if not available.
        """
        tags = format_info.get("tags", {})
        creation_str = tags.get("creation_time") or tags.get("date")

        if creation_str:
            try:
                # Handle ISO 8601 format
                creation_str = creation_str.replace("Z", "+00:00")
                return datetime.fromisoformat(creation_str)
            except (ValueError, TypeError):
                pass

        return None

    def _parse_bit_depth(self, stream: dict[str, Any]) -> int | None:
        """Parse bit depth from stream data.

        Args:
            stream: Video stream dictionary.

        Returns:
            Bit depth or None if not available.
        """
        bit_depth = stream.get("bits_per_raw_sample")
        if bit_depth is not None:
            try:
                return int(bit_depth)
            except (ValueError, TypeError):
                pass
        return None

    def _parse_level(self, stream: dict[str, Any]) -> str | None:
        """Parse codec level from stream data.

        Args:
            stream: Video stream dictionary.

        Returns:
            Level string or None if not available.
        """
        level = stream.get("level")
        if level is not None:
            try:
                # Convert level number to common format (e.g., 40 -> "4.0")
                level_num = int(level)
                if level_num > 10:
                    return f"{level_num // 10}.{level_num % 10}"
                return str(level_num)
            except (ValueError, TypeError):
                return str(level)
        return None
