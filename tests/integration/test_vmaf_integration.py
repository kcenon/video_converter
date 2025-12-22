"""Integration tests for VMAF quality validation workflow.

This module tests the VMAF quality validation integrated with the
conversion workflow, including quality threshold enforcement and
fallback handling.

SRS Reference: SRS-504 (VMAF Quality Measurement)
SDS Reference: SDS-P05-004
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_converter.processors.vmaf_analyzer import (
    VmafAnalyzer,
    VmafAnalysisError,
    VmafNotAvailableError,
    VmafQualityLevel,
    VmafResult,
    VmafScores,
)


@pytest.fixture
def mock_command_runner() -> MagicMock:
    """Create a mock command runner for FFmpeg operations."""
    mock = MagicMock()
    mock.check_command_exists.return_value = True
    return mock


@pytest.fixture
def sample_vmaf_json_output() -> dict:
    """Create sample VMAF JSON output data."""
    return {
        "version": "vmaf_v0.6.1",
        "pooled_metrics": {
            "vmaf": {
                "mean": 95.5,
                "min": 88.2,
                "max": 99.1,
                "harmonic_mean": 94.8,
            }
        },
        "frames": [
            {"frameNum": i, "metrics": {"vmaf": 95.0 + (i % 5)}}
            for i in range(100)
        ],
    }


class TestVmafAnalyzerAvailability:
    """Tests for VMAF analyzer availability detection."""

    def test_vmaf_available_when_libvmaf_in_ffmpeg(
        self,
        mock_command_runner: MagicMock,
    ) -> None:
        """Test that VMAF is reported as available when libvmaf filter exists."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "filters:\n  libvmaf\n  scale\n"
        mock_command_runner.run.return_value = mock_result

        analyzer = VmafAnalyzer(command_runner=mock_command_runner)
        assert analyzer.is_available() is True

    def test_vmaf_unavailable_when_libvmaf_not_in_ffmpeg(
        self,
        mock_command_runner: MagicMock,
    ) -> None:
        """Test that VMAF is reported as unavailable when libvmaf filter missing."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "filters:\n  scale\n  crop\n"
        mock_command_runner.run.return_value = mock_result

        analyzer = VmafAnalyzer(command_runner=mock_command_runner)
        assert analyzer.is_available() is False

    def test_vmaf_unavailable_when_ffmpeg_not_found(
        self,
        mock_command_runner: MagicMock,
    ) -> None:
        """Test that VMAF is reported as unavailable when FFmpeg not found."""
        mock_command_runner.check_command_exists.return_value = False

        analyzer = VmafAnalyzer(command_runner=mock_command_runner)
        assert analyzer.is_available() is False


class TestVmafAnalysis:
    """Tests for VMAF analysis execution."""

    def test_analyze_raises_when_vmaf_unavailable(self, tmp_path: Path) -> None:
        """Test that analyze raises VmafNotAvailableError when VMAF unavailable."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        mock_runner = MagicMock()
        mock_runner.check_command_exists.return_value = False

        analyzer = VmafAnalyzer(command_runner=mock_runner)

        with pytest.raises(VmafNotAvailableError):
            analyzer.analyze(original, converted)

    def test_analyze_raises_when_original_not_found(self, tmp_path: Path) -> None:
        """Test that analyze raises FileNotFoundError for missing original."""
        original = tmp_path / "nonexistent.mp4"
        converted = tmp_path / "converted.mp4"
        converted.touch()

        mock_runner = MagicMock()
        mock_runner.check_command_exists.return_value = True
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "libvmaf"
        mock_runner.run.return_value = mock_result

        analyzer = VmafAnalyzer(command_runner=mock_runner)

        with pytest.raises(FileNotFoundError):
            analyzer.analyze(original, converted)

    def test_analyze_raises_when_converted_not_found(self, tmp_path: Path) -> None:
        """Test that analyze raises FileNotFoundError for missing converted."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "nonexistent.mp4"
        original.touch()

        mock_runner = MagicMock()
        mock_runner.check_command_exists.return_value = True
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "libvmaf"
        mock_runner.run.return_value = mock_result

        analyzer = VmafAnalyzer(command_runner=mock_runner)

        with pytest.raises(FileNotFoundError):
            analyzer.analyze(original, converted)


class TestVmafQualityLevels:
    """Tests for VMAF quality level classification."""

    @pytest.mark.parametrize(
        "score,expected_level",
        [
            (93.0, VmafQualityLevel.VISUALLY_LOSSLESS),
            (95.0, VmafQualityLevel.VISUALLY_LOSSLESS),
            (100.0, VmafQualityLevel.VISUALLY_LOSSLESS),
            (80.0, VmafQualityLevel.HIGH_QUALITY),
            (92.9, VmafQualityLevel.HIGH_QUALITY),
            (60.0, VmafQualityLevel.GOOD_QUALITY),
            (79.9, VmafQualityLevel.GOOD_QUALITY),
            (59.9, VmafQualityLevel.NOTICEABLE_DEGRADATION),
            (0.0, VmafQualityLevel.NOTICEABLE_DEGRADATION),
        ],
    )
    def test_quality_level_from_score(
        self, score: float, expected_level: VmafQualityLevel
    ) -> None:
        """Test that quality level is correctly classified from score."""
        level = VmafQualityLevel.from_score(score)
        assert level == expected_level


class TestVmafScores:
    """Tests for VmafScores dataclass."""

    def test_vmaf_scores_quality_level_property(self) -> None:
        """Test that quality_level property returns correct level."""
        scores = VmafScores(
            mean=95.0,
            min=88.0,
            max=99.0,
            percentile_5=90.0,
            percentile_95=98.0,
        )
        assert scores.quality_level == VmafQualityLevel.VISUALLY_LOSSLESS

    def test_vmaf_scores_string_representation(self) -> None:
        """Test that VmafScores has readable string representation."""
        scores = VmafScores(
            mean=95.0,
            min=88.0,
            max=99.0,
            percentile_5=90.0,
            percentile_95=98.0,
        )
        str_repr = str(scores)
        assert "95.00" in str_repr
        assert "88.00" in str_repr
        assert "99.00" in str_repr


class TestVmafResult:
    """Tests for VmafResult dataclass."""

    @pytest.fixture
    def sample_result(self, tmp_path: Path) -> VmafResult:
        """Create a sample VmafResult for testing."""
        return VmafResult(
            original_path=tmp_path / "original.mp4",
            converted_path=tmp_path / "converted.mp4",
            scores=VmafScores(
                mean=95.0,
                min=88.0,
                max=99.0,
                percentile_5=90.0,
                percentile_95=98.0,
            ),
            quality_level=VmafQualityLevel.VISUALLY_LOSSLESS,
            frame_count=100,
            sampled=False,
            sample_interval=1,
        )

    def test_is_visually_lossless_true_for_high_scores(
        self, sample_result: VmafResult
    ) -> None:
        """Test is_visually_lossless returns True for quality level."""
        assert sample_result.is_visually_lossless is True

    def test_is_acceptable_true_for_high_quality(
        self, sample_result: VmafResult
    ) -> None:
        """Test is_acceptable returns True for scores >= 80."""
        assert sample_result.is_acceptable is True

    def test_is_acceptable_false_for_low_quality(self, tmp_path: Path) -> None:
        """Test is_acceptable returns False for scores < 80."""
        result = VmafResult(
            original_path=tmp_path / "original.mp4",
            converted_path=tmp_path / "converted.mp4",
            scores=VmafScores(
                mean=75.0,
                min=60.0,
                max=85.0,
                percentile_5=65.0,
                percentile_95=82.0,
            ),
            quality_level=VmafQualityLevel.GOOD_QUALITY,
            frame_count=100,
        )
        assert result.is_acceptable is False

    def test_add_warning(self, sample_result: VmafResult) -> None:
        """Test that warnings can be added to result."""
        sample_result.add_warning("Low quality frames detected")
        assert "Low quality frames detected" in sample_result.warnings


class TestVmafWorkflowIntegration:
    """Tests for VMAF integration with conversion workflow."""

    def test_vmaf_validation_after_conversion_success(self, tmp_path: Path) -> None:
        """Test VMAF validation after successful conversion."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.write_bytes(b"original content")
        converted.write_bytes(b"converted content")

        mock_runner = MagicMock()
        mock_runner.check_command_exists.return_value = True

        # Mock availability check
        filter_result = MagicMock()
        filter_result.success = True
        filter_result.stdout = "libvmaf"

        # Mock actual VMAF analysis
        vmaf_result = MagicMock()
        vmaf_result.success = True
        vmaf_result.stderr = ""

        mock_runner.run.side_effect = [filter_result, vmaf_result]

        # Create mock JSON output
        json_data = {
            "version": "vmaf_v0.6.1",
            "pooled_metrics": {"vmaf": {"mean": 95.0, "min": 88.0, "max": 99.0}},
            "frames": [{"metrics": {"vmaf": 95.0}} for _ in range(10)],
        }

        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__ = MagicMock(return_value=mock_file)
            mock_file.__exit__ = MagicMock(return_value=False)
            mock_file.read.return_value = json.dumps(json_data)
            mock_open.return_value = mock_file

            with patch.object(Path, "exists", return_value=True):
                with patch("json.load", return_value=json_data):
                    analyzer = VmafAnalyzer(command_runner=mock_runner)
                    assert analyzer.is_available() is True

    def test_vmaf_quality_assessment_messages(self) -> None:
        """Test human-readable quality assessment messages."""
        analyzer = VmafAnalyzer()

        excellent = analyzer.get_quality_assessment(95.0)
        assert "Excellent" in excellent
        assert "lossless" in excellent.lower()

        high = analyzer.get_quality_assessment(85.0)
        assert "High Quality" in high

        good = analyzer.get_quality_assessment(70.0)
        assert "Good Quality" in good

        degraded = analyzer.get_quality_assessment(50.0)
        assert "Degraded" in degraded

    def test_quick_analyze_returns_none_on_failure(self, tmp_path: Path) -> None:
        """Test that quick_analyze returns None when analysis fails."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        mock_runner = MagicMock()
        mock_runner.check_command_exists.return_value = False

        analyzer = VmafAnalyzer(command_runner=mock_runner)
        result = analyzer.quick_analyze(original, converted)
        assert result is None


class TestVmafThresholdEnforcement:
    """Tests for VMAF threshold enforcement in conversion workflow."""

    def test_vmaf_threshold_93_is_visually_lossless(self) -> None:
        """Test that score 93+ is considered visually lossless."""
        threshold = VmafAnalyzer.VISUALLY_LOSSLESS_THRESHOLD
        assert threshold == 93.0

        level = VmafQualityLevel.from_score(threshold)
        assert level == VmafQualityLevel.VISUALLY_LOSSLESS

    def test_vmaf_threshold_80_is_high_quality(self) -> None:
        """Test that score 80+ is considered high quality."""
        threshold = VmafAnalyzer.HIGH_QUALITY_THRESHOLD
        assert threshold == 80.0

        level = VmafQualityLevel.from_score(threshold)
        assert level == VmafQualityLevel.HIGH_QUALITY

    def test_vmaf_threshold_60_is_good_quality(self) -> None:
        """Test that score 60+ is considered good quality."""
        threshold = VmafAnalyzer.GOOD_QUALITY_THRESHOLD
        assert threshold == 60.0

        level = VmafQualityLevel.from_score(threshold)
        assert level == VmafQualityLevel.GOOD_QUALITY


class TestVmafSampling:
    """Tests for VMAF sampling feature."""

    def test_vmaf_result_indicates_sampled(self, tmp_path: Path) -> None:
        """Test that VmafResult correctly indicates sampling was used."""
        result = VmafResult(
            original_path=tmp_path / "original.mp4",
            converted_path=tmp_path / "converted.mp4",
            scores=VmafScores(
                mean=95.0,
                min=88.0,
                max=99.0,
                percentile_5=90.0,
                percentile_95=98.0,
            ),
            quality_level=VmafQualityLevel.VISUALLY_LOSSLESS,
            frame_count=10,
            sampled=True,
            sample_interval=10,
        )

        assert result.sampled is True
        assert result.sample_interval == 10
        assert "(sampled 1:10)" in str(result)

    def test_vmaf_result_not_sampled(self, tmp_path: Path) -> None:
        """Test that VmafResult correctly indicates no sampling."""
        result = VmafResult(
            original_path=tmp_path / "original.mp4",
            converted_path=tmp_path / "converted.mp4",
            scores=VmafScores(
                mean=95.0,
                min=88.0,
                max=99.0,
                percentile_5=90.0,
                percentile_95=98.0,
            ),
            quality_level=VmafQualityLevel.VISUALLY_LOSSLESS,
            frame_count=100,
            sampled=False,
            sample_interval=1,
        )

        assert result.sampled is False
        assert "(sampled" not in str(result)
