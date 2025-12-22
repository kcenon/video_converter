"""VMAF (Video Multimethod Assessment Fusion) quality measurement module.

This module provides VMAF-based perceptual video quality measurement to compare
original and converted video files. VMAF is a metric developed by Netflix that
predicts subjective video quality.

SDS Reference: SDS-P05-004
SRS Reference: SRS-504 (VMAF Quality Measurement)

VMAF Score Interpretation:
    - 93+: Visually lossless (indistinguishable from original)
    - 80-93: High quality (minor differences, acceptable for most use cases)
    - 60-80: Good quality (noticeable differences, acceptable for streaming)
    - <60: Noticeable degradation (quality issues visible)

Example:
    >>> analyzer = VmafAnalyzer()
    >>> if analyzer.is_available():
    ...     result = analyzer.analyze(
    ...         original=Path("original.mp4"),
    ...         converted=Path("converted.mp4"),
    ...     )
    ...     print(f"VMAF Score: {result.scores.mean:.2f}")
    ...     print(f"Quality: {result.quality_level.name}")
    ... else:
    ...     print("VMAF not available (libvmaf not installed)")
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from video_converter.utils.command_runner import (
    CommandExecutionError,
    CommandNotFoundError,
    CommandRunner,
)

logger = logging.getLogger(__name__)


class VmafNotAvailableError(Exception):
    """Raised when VMAF analysis is requested but libvmaf is not available.

    This exception indicates that FFmpeg was not compiled with libvmaf support
    or libvmaf is not installed on the system.

    Attributes:
        message: Explanation of why VMAF is not available.
    """

    def __init__(self, message: str = "libvmaf is not available") -> None:
        self.message = message
        super().__init__(
            f"{message}. Install FFmpeg with libvmaf support: "
            "brew install ffmpeg (ensure --with-libvmaf or similar option)"
        )


class VmafAnalysisError(Exception):
    """Raised when VMAF analysis fails.

    Attributes:
        original: Path to the original video.
        converted: Path to the converted video.
        reason: Explanation of the failure.
    """

    def __init__(
        self,
        original: Path,
        converted: Path,
        reason: str,
    ) -> None:
        self.original = original
        self.converted = converted
        self.reason = reason
        super().__init__(f"VMAF analysis failed for {original.name} vs {converted.name}: {reason}")


class VmafQualityLevel(Enum):
    """VMAF quality level classification.

    Based on Netflix's VMAF score interpretation guidelines.

    Attributes:
        VISUALLY_LOSSLESS: Score >= 93, indistinguishable from original.
        HIGH_QUALITY: Score 80-93, minor differences acceptable for most use cases.
        GOOD_QUALITY: Score 60-80, noticeable differences acceptable for streaming.
        NOTICEABLE_DEGRADATION: Score < 60, visible quality issues.
    """

    VISUALLY_LOSSLESS = "visually_lossless"
    HIGH_QUALITY = "high_quality"
    GOOD_QUALITY = "good_quality"
    NOTICEABLE_DEGRADATION = "noticeable_degradation"

    @classmethod
    def from_score(cls, score: float) -> VmafQualityLevel:
        """Determine quality level from VMAF score.

        Args:
            score: VMAF score (0-100).

        Returns:
            Corresponding VmafQualityLevel.
        """
        if score >= 93:
            return cls.VISUALLY_LOSSLESS
        elif score >= 80:
            return cls.HIGH_QUALITY
        elif score >= 60:
            return cls.GOOD_QUALITY
        else:
            return cls.NOTICEABLE_DEGRADATION


@dataclass
class VmafScores:
    """VMAF score statistics.

    Contains various percentile and aggregate scores from VMAF analysis.

    Attributes:
        mean: Mean VMAF score across all frames.
        min: Minimum VMAF score (worst frame).
        max: Maximum VMAF score (best frame).
        percentile_5: 5th percentile score (worst 5% of frames).
        percentile_95: 95th percentile score (best 5% excluded).
        harmonic_mean: Harmonic mean (if available).
        std_dev: Standard deviation (if available).
    """

    mean: float
    min: float
    max: float
    percentile_5: float
    percentile_95: float
    harmonic_mean: float | None = None
    std_dev: float | None = None

    @property
    def quality_level(self) -> VmafQualityLevel:
        """Get quality level based on mean score."""
        return VmafQualityLevel.from_score(self.mean)

    def __str__(self) -> str:
        """Return human-readable summary."""
        return (
            f"VMAF: mean={self.mean:.2f}, min={self.min:.2f}, max={self.max:.2f}, "
            f"5th={self.percentile_5:.2f}, 95th={self.percentile_95:.2f}"
        )


@dataclass
class VmafResult:
    """Complete VMAF analysis result.

    SDS Reference: SDS-P05-004

    Attributes:
        original_path: Path to the original video file.
        converted_path: Path to the converted video file.
        scores: VMAF score statistics.
        quality_level: Quality classification based on mean score.
        frame_count: Number of frames analyzed.
        sampled: Whether sampling was used for faster analysis.
        sample_interval: Sampling interval used (1 = every frame).
        model_version: VMAF model version used.
        warnings: List of warning messages.
        raw_data: Raw JSON output from VMAF (if available).
    """

    original_path: Path
    converted_path: Path
    scores: VmafScores
    quality_level: VmafQualityLevel
    frame_count: int
    sampled: bool = False
    sample_interval: int = 1
    model_version: str = "vmaf_v0.6.1"
    warnings: list[str] = field(default_factory=list)
    raw_data: dict[str, Any] | None = None

    @property
    def is_visually_lossless(self) -> bool:
        """Check if quality is visually lossless (VMAF >= 93)."""
        return self.quality_level == VmafQualityLevel.VISUALLY_LOSSLESS

    @property
    def is_acceptable(self) -> bool:
        """Check if quality is acceptable for most use cases (VMAF >= 80)."""
        return self.scores.mean >= 80

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def __str__(self) -> str:
        """Return human-readable summary."""
        sampled_str = f" (sampled 1:{self.sample_interval})" if self.sampled else ""
        return (
            f"VMAF Analysis{sampled_str}: {self.scores.mean:.2f} "
            f"({self.quality_level.value}) - {self.frame_count} frames"
        )


class VmafAnalyzer:
    """VMAF quality analyzer for video comparison.

    This class provides VMAF-based quality measurement to compare original
    and converted videos. It supports sampling for faster analysis and
    gracefully handles missing libvmaf.

    SDS Reference: SDS-P05-004
    SRS Reference: SRS-504 (VMAF Quality Measurement)

    Features:
        - Calculate VMAF scores between original and converted videos
        - Support sampling for faster analysis of long videos
        - Report percentile scores (min, 5th, mean, 95th)
        - Gracefully handle missing libvmaf

    Example:
        >>> analyzer = VmafAnalyzer()
        >>> # Check availability first
        >>> if not analyzer.is_available():
        ...     print("VMAF not available")
        ...     return
        >>> # Full analysis
        >>> result = analyzer.analyze(
        ...     original=Path("original.mp4"),
        ...     converted=Path("converted.mp4"),
        ... )
        >>> print(f"Score: {result.scores.mean:.2f}")
        >>> # Sampled analysis for long videos (faster)
        >>> result = analyzer.analyze(
        ...     original=Path("long_video.mp4"),
        ...     converted=Path("converted.mp4"),
        ...     sample_interval=10,  # Analyze every 10th frame
        ... )

    Attributes:
        ffmpeg_path: Path to FFmpeg executable.
        timeout: Default timeout for VMAF analysis.
        model_path: Path to VMAF model file (optional).
    """

    FFMPEG_CMD = "ffmpeg"
    DEFAULT_TIMEOUT = 3600.0  # 1 hour for long videos

    # Quality thresholds
    VISUALLY_LOSSLESS_THRESHOLD = 93.0
    HIGH_QUALITY_THRESHOLD = 80.0
    GOOD_QUALITY_THRESHOLD = 60.0

    def __init__(
        self,
        *,
        ffmpeg_path: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        model_path: str | None = None,
        command_runner: CommandRunner | None = None,
    ) -> None:
        """Initialize VMAF analyzer.

        Args:
            ffmpeg_path: Custom path to FFmpeg. Uses PATH if None.
            timeout: Default timeout for analysis in seconds.
            model_path: Custom path to VMAF model file. Uses default if None.
            command_runner: CommandRunner instance. Creates new one if None.
        """
        self._ffmpeg_path = ffmpeg_path or self.FFMPEG_CMD
        self._timeout = timeout
        self._model_path = model_path
        self._runner = command_runner or CommandRunner()
        self._availability_checked = False
        self._is_available = False

    def is_available(self) -> bool:
        """Check if VMAF analysis is available.

        Checks if FFmpeg is installed and has libvmaf support.

        Returns:
            True if VMAF is available, False otherwise.
        """
        if self._availability_checked:
            return self._is_available

        self._is_available = self._check_vmaf_support()
        self._availability_checked = True
        return self._is_available

    def _check_vmaf_support(self) -> bool:
        """Check if FFmpeg has libvmaf support.

        Returns:
            True if libvmaf is available.
        """
        try:
            # Check if ffmpeg exists
            if not self._runner.check_command_exists(self._ffmpeg_path):
                logger.debug("FFmpeg not found")
                return False

            # Check for libvmaf filter
            result = self._runner.run(
                [self._ffmpeg_path, "-filters"],
                timeout=30.0,
            )

            if result.success and "libvmaf" in result.stdout:
                logger.debug("VMAF support detected")
                return True

            logger.debug("libvmaf filter not found in FFmpeg")
            return False

        except (CommandNotFoundError, CommandExecutionError) as e:
            logger.debug(f"Error checking VMAF support: {e}")
            return False

    def analyze(
        self,
        original: Path,
        converted: Path,
        *,
        sample_interval: int = 1,
        timeout: float | None = None,
        resolution: tuple[int, int] | None = None,
    ) -> VmafResult:
        """Analyze video quality using VMAF.

        Compares the converted video against the original and returns
        VMAF scores and quality assessment.

        Args:
            original: Path to the original (reference) video.
            converted: Path to the converted (distorted) video.
            sample_interval: Analyze every Nth frame (1 = all frames).
                Use higher values for faster analysis of long videos.
            timeout: Analysis timeout in seconds. Uses default if None.
            resolution: Target resolution for comparison (width, height).
                If None, videos are scaled to match if needed.

        Returns:
            VmafResult containing scores and quality assessment.

        Raises:
            VmafNotAvailableError: If libvmaf is not available.
            VmafAnalysisError: If analysis fails.
            FileNotFoundError: If either video file doesn't exist.

        Example:
            >>> result = analyzer.analyze(
            ...     original=Path("original.mp4"),
            ...     converted=Path("converted.mp4"),
            ...     sample_interval=5,  # Every 5th frame for speed
            ... )
            >>> if result.is_visually_lossless:
            ...     print("Excellent quality!")
        """
        if not self.is_available():
            raise VmafNotAvailableError()

        if not original.exists():
            raise FileNotFoundError(f"Original video not found: {original}")
        if not converted.exists():
            raise FileNotFoundError(f"Converted video not found: {converted}")

        timeout = timeout or self._timeout

        # Create temporary file for JSON output
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as tmp_file:
            json_path = Path(tmp_file.name)

        try:
            # Build and run FFmpeg command
            args = self._build_vmaf_command(
                original=original,
                converted=converted,
                json_output=json_path,
                sample_interval=sample_interval,
                resolution=resolution,
            )

            logger.info(f"Running VMAF analysis: {original.name} vs {converted.name}")
            logger.debug(f"Command: {' '.join(args)}")

            result = self._runner.run(args, timeout=timeout)

            if not result.success:
                raise VmafAnalysisError(original, converted, f"FFmpeg failed: {result.stderr}")

            # Parse results
            return self._parse_vmaf_output(
                original=original,
                converted=converted,
                json_path=json_path,
                sample_interval=sample_interval,
                stderr=result.stderr,
            )

        except CommandTimeoutError as e:
            raise VmafAnalysisError(
                original, converted, f"Analysis timed out after {timeout}s"
            ) from e
        finally:
            # Clean up temporary file
            if json_path.exists():
                json_path.unlink()

    async def analyze_async(
        self,
        original: Path,
        converted: Path,
        *,
        sample_interval: int = 1,
        timeout: float | None = None,
        resolution: tuple[int, int] | None = None,
    ) -> VmafResult:
        """Analyze video quality using VMAF asynchronously.

        Async version of analyze() for use in async contexts.

        Args:
            original: Path to the original (reference) video.
            converted: Path to the converted (distorted) video.
            sample_interval: Analyze every Nth frame (1 = all frames).
            timeout: Analysis timeout in seconds. Uses default if None.
            resolution: Target resolution for comparison (width, height).

        Returns:
            VmafResult containing scores and quality assessment.

        Raises:
            VmafNotAvailableError: If libvmaf is not available.
            VmafAnalysisError: If analysis fails.
            FileNotFoundError: If either video file doesn't exist.
        """
        if not self.is_available():
            raise VmafNotAvailableError()

        if not original.exists():
            raise FileNotFoundError(f"Original video not found: {original}")
        if not converted.exists():
            raise FileNotFoundError(f"Converted video not found: {converted}")

        timeout = timeout or self._timeout

        # Create temporary file for JSON output
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as tmp_file:
            json_path = Path(tmp_file.name)

        try:
            # Build FFmpeg command
            args = self._build_vmaf_command(
                original=original,
                converted=converted,
                json_output=json_path,
                sample_interval=sample_interval,
                resolution=resolution,
            )

            logger.info(f"Running async VMAF analysis: {original.name} vs {converted.name}")

            result = await self._runner.run_async(args, timeout=timeout)

            if not result.success:
                raise VmafAnalysisError(original, converted, f"FFmpeg failed: {result.stderr}")

            # Parse results
            return self._parse_vmaf_output(
                original=original,
                converted=converted,
                json_path=json_path,
                sample_interval=sample_interval,
                stderr=result.stderr,
            )

        except asyncio.TimeoutError as e:
            raise VmafAnalysisError(
                original, converted, f"Analysis timed out after {timeout}s"
            ) from e
        finally:
            # Clean up temporary file
            if json_path.exists():
                json_path.unlink()

    def _build_vmaf_command(
        self,
        original: Path,
        converted: Path,
        json_output: Path,
        sample_interval: int = 1,
        resolution: tuple[int, int] | None = None,
    ) -> list[str]:
        """Build FFmpeg command for VMAF analysis.

        Args:
            original: Path to original video.
            converted: Path to converted video.
            json_output: Path for JSON output file.
            sample_interval: Frame sampling interval.
            resolution: Target resolution for scaling.

        Returns:
            List of command arguments.
        """
        # Default resolution for VMAF (1080p recommended)
        if resolution is None:
            resolution = (1920, 1080)

        width, height = resolution

        # Build filter graph
        # Scale both videos to same resolution with bicubic interpolation
        scale_filter = f"scale={width}:{height}:flags=bicubic"

        # Build VMAF filter options
        vmaf_opts = [
            "log_fmt=json",
            f"log_path={json_output}",
            "n_threads=4",
        ]

        # Add model path if specified
        if self._model_path:
            vmaf_opts.append(f"model_path={self._model_path}")

        # Add sampling if specified (n_subsample for frame sampling)
        if sample_interval > 1:
            vmaf_opts.append(f"n_subsample={sample_interval}")

        vmaf_filter = f"libvmaf={':'.join(vmaf_opts)}"

        # Complete filter graph:
        # [0:v] = original, [1:v] = converted
        # Scale both, then compare with VMAF
        filter_complex = (
            f"[0:v]{scale_filter}[ref];[1:v]{scale_filter}[main];[main][ref]{vmaf_filter}"
        )

        return [
            self._ffmpeg_path,
            "-i",
            str(original),
            "-i",
            str(converted),
            "-lavfi",
            filter_complex,
            "-f",
            "null",
            "-",
        ]

    def _parse_vmaf_output(
        self,
        original: Path,
        converted: Path,
        json_path: Path,
        sample_interval: int,
        stderr: str,
    ) -> VmafResult:
        """Parse VMAF JSON output.

        Args:
            original: Original video path.
            converted: Converted video path.
            json_path: Path to JSON output file.
            sample_interval: Sampling interval used.
            stderr: FFmpeg stderr output.

        Returns:
            VmafResult with parsed scores.

        Raises:
            VmafAnalysisError: If parsing fails.
        """
        if not json_path.exists():
            raise VmafAnalysisError(original, converted, "VMAF JSON output not created")

        try:
            with open(json_path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise VmafAnalysisError(original, converted, f"Failed to parse VMAF JSON: {e}") from e

        # Extract pooled metrics
        pooled_metrics = data.get("pooled_metrics", {})
        vmaf_metrics = pooled_metrics.get("vmaf", {})

        if not vmaf_metrics:
            # Try alternative format
            vmaf_metrics = self._extract_metrics_fallback(data, stderr)

        if not vmaf_metrics:
            raise VmafAnalysisError(original, converted, "No VMAF metrics found in output")

        # Extract scores
        mean_score = vmaf_metrics.get("mean", 0.0)
        min_score = vmaf_metrics.get("min", 0.0)
        max_score = vmaf_metrics.get("max", 100.0)
        harmonic_mean = vmaf_metrics.get("harmonic_mean")
        std_dev = vmaf_metrics.get("stdev")

        # Calculate percentiles from frame scores if available
        frames = data.get("frames", [])
        frame_scores = [f.get("metrics", {}).get("vmaf", mean_score) for f in frames]

        if frame_scores:
            sorted_scores = sorted(frame_scores)
            n = len(sorted_scores)
            percentile_5 = sorted_scores[int(n * 0.05)] if n > 20 else min_score
            percentile_95 = sorted_scores[int(n * 0.95)] if n > 20 else max_score
            frame_count = n
        else:
            percentile_5 = min_score
            percentile_95 = max_score
            frame_count = 0

        # Create scores object
        scores = VmafScores(
            mean=mean_score,
            min=min_score,
            max=max_score,
            percentile_5=percentile_5,
            percentile_95=percentile_95,
            harmonic_mean=harmonic_mean,
            std_dev=std_dev,
        )

        # Create result
        result = VmafResult(
            original_path=original,
            converted_path=converted,
            scores=scores,
            quality_level=VmafQualityLevel.from_score(mean_score),
            frame_count=frame_count,
            sampled=sample_interval > 1,
            sample_interval=sample_interval,
            model_version=data.get("version", "unknown"),
            raw_data=data,
        )

        # Add warnings for edge cases
        if min_score < 50:
            result.add_warning(f"Some frames have very low quality (min={min_score:.2f})")
        if std_dev and std_dev > 10:
            result.add_warning(f"High quality variance detected (std_dev={std_dev:.2f})")

        return result

    def _extract_metrics_fallback(
        self,
        data: dict[str, Any],
        stderr: str,
    ) -> dict[str, float]:
        """Extract VMAF metrics from alternative formats or stderr.

        Some FFmpeg versions output VMAF differently.

        Args:
            data: Parsed JSON data.
            stderr: FFmpeg stderr output.

        Returns:
            Dictionary with mean, min, max scores if found.
        """
        metrics: dict[str, float] = {}

        # Try to extract from frames array
        frames = data.get("frames", [])
        if frames:
            frame_scores = []
            for frame in frames:
                vmaf_score = frame.get("metrics", {}).get("vmaf")
                if vmaf_score is not None:
                    frame_scores.append(vmaf_score)

            if frame_scores:
                metrics["mean"] = sum(frame_scores) / len(frame_scores)
                metrics["min"] = min(frame_scores)
                metrics["max"] = max(frame_scores)
                return metrics

        # Try to parse from stderr (older FFmpeg versions)
        vmaf_match = re.search(r"VMAF score:\s*([\d.]+)", stderr)
        if vmaf_match:
            score = float(vmaf_match.group(1))
            metrics["mean"] = score
            metrics["min"] = score
            metrics["max"] = score

        return metrics

    def quick_analyze(
        self,
        original: Path,
        converted: Path,
        *,
        timeout: float | None = None,
    ) -> float | None:
        """Perform quick VMAF analysis with sampling.

        Uses aggressive sampling for a quick quality estimate.
        Suitable for initial screening of conversion quality.

        Args:
            original: Path to original video.
            converted: Path to converted video.
            timeout: Analysis timeout in seconds.

        Returns:
            Mean VMAF score, or None if analysis fails.
        """
        try:
            result = self.analyze(
                original=original,
                converted=converted,
                sample_interval=30,  # Every 30th frame
                timeout=timeout or 300.0,  # 5 minute timeout
            )
            return result.scores.mean
        except (VmafNotAvailableError, VmafAnalysisError, FileNotFoundError):
            return None

    def get_quality_assessment(self, score: float) -> str:
        """Get human-readable quality assessment for a VMAF score.

        Args:
            score: VMAF score (0-100).

        Returns:
            Human-readable quality assessment string.
        """
        level = VmafQualityLevel.from_score(score)
        assessments = {
            VmafQualityLevel.VISUALLY_LOSSLESS: (
                f"Excellent ({score:.1f}): Visually lossless - indistinguishable from original"
            ),
            VmafQualityLevel.HIGH_QUALITY: (
                f"High Quality ({score:.1f}): Minor differences - acceptable for most use cases"
            ),
            VmafQualityLevel.GOOD_QUALITY: (
                f"Good Quality ({score:.1f}): Noticeable differences - acceptable for streaming"
            ),
            VmafQualityLevel.NOTICEABLE_DEGRADATION: (
                f"Degraded ({score:.1f}): Visible quality issues - "
                "consider re-encoding with higher quality"
            ),
        }
        return assessments[level]


# Import CommandTimeoutError for exception handling
try:
    from video_converter.utils.command_runner import CommandTimeoutError
except ImportError:
    # Fallback if not available
    CommandTimeoutError = Exception  # type: ignore[misc, assignment]
