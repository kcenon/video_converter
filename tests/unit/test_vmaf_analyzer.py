"""Unit tests for VMAF analyzer module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_converter.processors.vmaf_analyzer import (
    VmafAnalysisError,
    VmafAnalyzer,
    VmafNotAvailableError,
    VmafQualityLevel,
    VmafResult,
    VmafScores,
)
from video_converter.utils.command_runner import (
    CommandResult,
    CommandRunner,
)


class TestVmafQualityLevel:
    """Tests for VmafQualityLevel enum."""

    def test_visually_lossless_threshold(self) -> None:
        """Test that scores >= 93 are visually lossless."""
        assert VmafQualityLevel.from_score(93.0) == VmafQualityLevel.VISUALLY_LOSSLESS
        assert VmafQualityLevel.from_score(95.5) == VmafQualityLevel.VISUALLY_LOSSLESS
        assert VmafQualityLevel.from_score(100.0) == VmafQualityLevel.VISUALLY_LOSSLESS

    def test_high_quality_threshold(self) -> None:
        """Test that scores 80-93 are high quality."""
        assert VmafQualityLevel.from_score(80.0) == VmafQualityLevel.HIGH_QUALITY
        assert VmafQualityLevel.from_score(85.0) == VmafQualityLevel.HIGH_QUALITY
        assert VmafQualityLevel.from_score(92.9) == VmafQualityLevel.HIGH_QUALITY

    def test_good_quality_threshold(self) -> None:
        """Test that scores 60-80 are good quality."""
        assert VmafQualityLevel.from_score(60.0) == VmafQualityLevel.GOOD_QUALITY
        assert VmafQualityLevel.from_score(70.0) == VmafQualityLevel.GOOD_QUALITY
        assert VmafQualityLevel.from_score(79.9) == VmafQualityLevel.GOOD_QUALITY

    def test_noticeable_degradation_threshold(self) -> None:
        """Test that scores < 60 show noticeable degradation."""
        assert VmafQualityLevel.from_score(59.9) == VmafQualityLevel.NOTICEABLE_DEGRADATION
        assert VmafQualityLevel.from_score(50.0) == VmafQualityLevel.NOTICEABLE_DEGRADATION
        assert VmafQualityLevel.from_score(0.0) == VmafQualityLevel.NOTICEABLE_DEGRADATION

    def test_enum_values(self) -> None:
        """Test enum value strings."""
        assert VmafQualityLevel.VISUALLY_LOSSLESS.value == "visually_lossless"
        assert VmafQualityLevel.HIGH_QUALITY.value == "high_quality"
        assert VmafQualityLevel.GOOD_QUALITY.value == "good_quality"
        assert VmafQualityLevel.NOTICEABLE_DEGRADATION.value == "noticeable_degradation"


class TestVmafScores:
    """Tests for VmafScores dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic VmafScores creation."""
        scores = VmafScores(
            mean=85.5,
            min=70.0,
            max=95.0,
            percentile_5=72.5,
            percentile_95=93.0,
        )
        assert scores.mean == pytest.approx(85.5)
        assert scores.min == pytest.approx(70.0)
        assert scores.max == pytest.approx(95.0)
        assert scores.percentile_5 == pytest.approx(72.5)
        assert scores.percentile_95 == pytest.approx(93.0)

    def test_creation_with_optional_fields(self) -> None:
        """Test VmafScores with all optional fields."""
        scores = VmafScores(
            mean=85.5,
            min=70.0,
            max=95.0,
            percentile_5=72.5,
            percentile_95=93.0,
            harmonic_mean=84.0,
            std_dev=5.2,
        )
        assert scores.harmonic_mean == pytest.approx(84.0)
        assert scores.std_dev == pytest.approx(5.2)

    def test_quality_level_property(self) -> None:
        """Test quality_level property returns correct level."""
        scores = VmafScores(
            mean=95.0,
            min=90.0,
            max=98.0,
            percentile_5=91.0,
            percentile_95=97.0,
        )
        assert scores.quality_level == VmafQualityLevel.VISUALLY_LOSSLESS

    def test_str_format(self) -> None:
        """Test string representation."""
        scores = VmafScores(
            mean=85.5,
            min=70.0,
            max=95.0,
            percentile_5=72.5,
            percentile_95=93.0,
        )
        result = str(scores)
        assert "85.5" in result
        assert "70.0" in result
        assert "95.0" in result


class TestVmafResult:
    """Tests for VmafResult dataclass."""

    def _create_scores(
        self,
        mean: float = 85.0,
        min_score: float = 70.0,
        max_score: float = 95.0,
    ) -> VmafScores:
        """Create test scores."""
        return VmafScores(
            mean=mean,
            min=min_score,
            max=max_score,
            percentile_5=min_score + 2.0,
            percentile_95=max_score - 2.0,
        )

    def test_basic_creation(self, tmp_path: Path) -> None:
        """Test basic VmafResult creation."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        scores = self._create_scores()

        result = VmafResult(
            original_path=original,
            converted_path=converted,
            scores=scores,
            quality_level=VmafQualityLevel.HIGH_QUALITY,
            frame_count=1000,
        )

        assert result.original_path == original
        assert result.converted_path == converted
        assert result.scores == scores
        assert result.quality_level == VmafQualityLevel.HIGH_QUALITY
        assert result.frame_count == 1000
        assert result.sampled is False
        assert result.sample_interval == 1

    def test_sampled_analysis(self, tmp_path: Path) -> None:
        """Test VmafResult with sampling."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        scores = self._create_scores()

        result = VmafResult(
            original_path=original,
            converted_path=converted,
            scores=scores,
            quality_level=VmafQualityLevel.HIGH_QUALITY,
            frame_count=100,
            sampled=True,
            sample_interval=10,
        )

        assert result.sampled is True
        assert result.sample_interval == 10

    def test_is_visually_lossless_true(self, tmp_path: Path) -> None:
        """Test is_visually_lossless returns True for high scores."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        scores = self._create_scores(mean=95.0)

        result = VmafResult(
            original_path=original,
            converted_path=converted,
            scores=scores,
            quality_level=VmafQualityLevel.VISUALLY_LOSSLESS,
            frame_count=1000,
        )

        assert result.is_visually_lossless is True

    def test_is_visually_lossless_false(self, tmp_path: Path) -> None:
        """Test is_visually_lossless returns False for lower scores."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        scores = self._create_scores(mean=85.0)

        result = VmafResult(
            original_path=original,
            converted_path=converted,
            scores=scores,
            quality_level=VmafQualityLevel.HIGH_QUALITY,
            frame_count=1000,
        )

        assert result.is_visually_lossless is False

    def test_is_acceptable(self, tmp_path: Path) -> None:
        """Test is_acceptable property."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"

        # Score >= 80 is acceptable
        scores = self._create_scores(mean=82.0)
        result = VmafResult(
            original_path=original,
            converted_path=converted,
            scores=scores,
            quality_level=VmafQualityLevel.HIGH_QUALITY,
            frame_count=1000,
        )
        assert result.is_acceptable is True

        # Score < 80 is not acceptable
        scores = self._create_scores(mean=75.0)
        result = VmafResult(
            original_path=original,
            converted_path=converted,
            scores=scores,
            quality_level=VmafQualityLevel.GOOD_QUALITY,
            frame_count=1000,
        )
        assert result.is_acceptable is False

    def test_add_warning(self, tmp_path: Path) -> None:
        """Test adding warnings to result."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        scores = self._create_scores()

        result = VmafResult(
            original_path=original,
            converted_path=converted,
            scores=scores,
            quality_level=VmafQualityLevel.HIGH_QUALITY,
            frame_count=1000,
        )

        assert len(result.warnings) == 0
        result.add_warning("Test warning")
        assert len(result.warnings) == 1
        assert "Test warning" in result.warnings

    def test_str_format(self, tmp_path: Path) -> None:
        """Test string representation."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        scores = self._create_scores(mean=85.5)

        result = VmafResult(
            original_path=original,
            converted_path=converted,
            scores=scores,
            quality_level=VmafQualityLevel.HIGH_QUALITY,
            frame_count=1000,
        )

        result_str = str(result)
        assert "85.5" in result_str
        assert "1000" in result_str


class TestVmafErrors:
    """Tests for VMAF error classes."""

    def test_vmaf_not_available_error(self) -> None:
        """Test VmafNotAvailableError message."""
        error = VmafNotAvailableError()
        assert "libvmaf" in str(error)
        assert "not available" in str(error)

    def test_vmaf_not_available_error_custom_message(self) -> None:
        """Test VmafNotAvailableError with custom message."""
        error = VmafNotAvailableError("Custom reason")
        assert "Custom reason" in str(error)

    def test_vmaf_analysis_error(self, tmp_path: Path) -> None:
        """Test VmafAnalysisError message."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        error = VmafAnalysisError(original, converted, "Test failure")

        assert error.original == original
        assert error.converted == converted
        assert error.reason == "Test failure"
        assert "original.mp4" in str(error)
        assert "converted.mp4" in str(error)
        assert "Test failure" in str(error)


class TestVmafAnalyzer:
    """Tests for VmafAnalyzer class."""

    def _create_mock_runner(
        self,
        vmaf_available: bool = True,
    ) -> MagicMock:
        """Create mock CommandRunner."""
        mock_runner = MagicMock(spec=CommandRunner)
        mock_runner.check_command_exists.return_value = True

        # Mock -filters check for VMAF support
        filters_result = MagicMock(spec=CommandResult)
        filters_result.success = True
        filters_result.stdout = "libvmaf" if vmaf_available else "no vmaf"
        mock_runner.run.return_value = filters_result

        return mock_runner

    def test_is_available_true(self) -> None:
        """Test is_available returns True when libvmaf is present."""
        mock_runner = self._create_mock_runner(vmaf_available=True)
        analyzer = VmafAnalyzer(command_runner=mock_runner)

        assert analyzer.is_available() is True

    def test_is_available_false(self) -> None:
        """Test is_available returns False when libvmaf is missing."""
        mock_runner = self._create_mock_runner(vmaf_available=False)
        analyzer = VmafAnalyzer(command_runner=mock_runner)

        assert analyzer.is_available() is False

    def test_is_available_cached(self) -> None:
        """Test is_available caches the result."""
        mock_runner = self._create_mock_runner(vmaf_available=True)
        analyzer = VmafAnalyzer(command_runner=mock_runner)

        # First call
        result1 = analyzer.is_available()
        # Second call
        result2 = analyzer.is_available()

        assert result1 is True
        assert result2 is True
        # Should only call run once due to caching
        assert mock_runner.run.call_count == 1

    def test_is_available_ffmpeg_not_found(self) -> None:
        """Test is_available returns False when FFmpeg not found."""
        mock_runner = MagicMock(spec=CommandRunner)
        mock_runner.check_command_exists.return_value = False

        analyzer = VmafAnalyzer(command_runner=mock_runner)
        assert analyzer.is_available() is False

    def test_analyze_raises_when_not_available(self, tmp_path: Path) -> None:
        """Test analyze raises error when VMAF not available."""
        mock_runner = self._create_mock_runner(vmaf_available=False)
        analyzer = VmafAnalyzer(command_runner=mock_runner)

        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.write_bytes(b"content")
        converted.write_bytes(b"content")

        with pytest.raises(VmafNotAvailableError):
            analyzer.analyze(original, converted)

    def test_analyze_raises_file_not_found_original(self, tmp_path: Path) -> None:
        """Test analyze raises FileNotFoundError for missing original."""
        mock_runner = self._create_mock_runner(vmaf_available=True)
        analyzer = VmafAnalyzer(command_runner=mock_runner)

        original = tmp_path / "nonexistent.mp4"
        converted = tmp_path / "converted.mp4"
        converted.write_bytes(b"content")

        with pytest.raises(FileNotFoundError, match="Original video not found"):
            analyzer.analyze(original, converted)

    def test_analyze_raises_file_not_found_converted(self, tmp_path: Path) -> None:
        """Test analyze raises FileNotFoundError for missing converted."""
        mock_runner = self._create_mock_runner(vmaf_available=True)
        analyzer = VmafAnalyzer(command_runner=mock_runner)

        original = tmp_path / "original.mp4"
        converted = tmp_path / "nonexistent.mp4"
        original.write_bytes(b"content")

        with pytest.raises(FileNotFoundError, match="Converted video not found"):
            analyzer.analyze(original, converted)

    def test_build_vmaf_command_default_resolution(self) -> None:
        """Test VMAF command includes default 1080p resolution."""
        mock_runner = self._create_mock_runner()
        analyzer = VmafAnalyzer(command_runner=mock_runner)

        cmd = analyzer._build_vmaf_command(
            original=Path("original.mp4"),
            converted=Path("converted.mp4"),
            json_output=Path("output.json"),
        )

        # Check command structure
        assert cmd[0] == "ffmpeg"
        assert "-i" in cmd
        assert "-lavfi" in cmd
        assert "-f" in cmd
        assert "null" in cmd

        # Check filter contains scale to 1080p
        lavfi_idx = cmd.index("-lavfi")
        filter_graph = cmd[lavfi_idx + 1]
        assert "scale=1920:1080" in filter_graph
        assert "libvmaf" in filter_graph

    def test_build_vmaf_command_custom_resolution(self) -> None:
        """Test VMAF command with custom resolution."""
        mock_runner = self._create_mock_runner()
        analyzer = VmafAnalyzer(command_runner=mock_runner)

        cmd = analyzer._build_vmaf_command(
            original=Path("original.mp4"),
            converted=Path("converted.mp4"),
            json_output=Path("output.json"),
            resolution=(1280, 720),
        )

        lavfi_idx = cmd.index("-lavfi")
        filter_graph = cmd[lavfi_idx + 1]
        assert "scale=1280:720" in filter_graph

    def test_build_vmaf_command_with_sampling(self) -> None:
        """Test VMAF command with frame sampling."""
        mock_runner = self._create_mock_runner()
        analyzer = VmafAnalyzer(command_runner=mock_runner)

        cmd = analyzer._build_vmaf_command(
            original=Path("original.mp4"),
            converted=Path("converted.mp4"),
            json_output=Path("output.json"),
            sample_interval=10,
        )

        lavfi_idx = cmd.index("-lavfi")
        filter_graph = cmd[lavfi_idx + 1]
        assert "n_subsample=10" in filter_graph

    def test_build_vmaf_command_with_model_path(self) -> None:
        """Test VMAF command with custom model path."""
        mock_runner = self._create_mock_runner()
        analyzer = VmafAnalyzer(
            command_runner=mock_runner,
            model_path="/path/to/vmaf_v0.6.1.json",
        )

        cmd = analyzer._build_vmaf_command(
            original=Path("original.mp4"),
            converted=Path("converted.mp4"),
            json_output=Path("output.json"),
        )

        lavfi_idx = cmd.index("-lavfi")
        filter_graph = cmd[lavfi_idx + 1]
        assert "model_path=/path/to/vmaf_v0.6.1.json" in filter_graph

    def test_get_quality_assessment_visually_lossless(self) -> None:
        """Test quality assessment for visually lossless scores."""
        mock_runner = self._create_mock_runner()
        analyzer = VmafAnalyzer(command_runner=mock_runner)

        assessment = analyzer.get_quality_assessment(95.0)
        assert "Excellent" in assessment
        assert "95.0" in assessment
        assert "indistinguishable" in assessment

    def test_get_quality_assessment_high_quality(self) -> None:
        """Test quality assessment for high quality scores."""
        mock_runner = self._create_mock_runner()
        analyzer = VmafAnalyzer(command_runner=mock_runner)

        assessment = analyzer.get_quality_assessment(85.0)
        assert "High Quality" in assessment
        assert "85.0" in assessment

    def test_get_quality_assessment_good_quality(self) -> None:
        """Test quality assessment for good quality scores."""
        mock_runner = self._create_mock_runner()
        analyzer = VmafAnalyzer(command_runner=mock_runner)

        assessment = analyzer.get_quality_assessment(70.0)
        assert "Good Quality" in assessment
        assert "70.0" in assessment

    def test_get_quality_assessment_degraded(self) -> None:
        """Test quality assessment for degraded scores."""
        mock_runner = self._create_mock_runner()
        analyzer = VmafAnalyzer(command_runner=mock_runner)

        assessment = analyzer.get_quality_assessment(50.0)
        assert "Degraded" in assessment
        assert "50.0" in assessment
        assert "re-encoding" in assessment


class TestVmafAnalyzerParsing:
    """Tests for VMAF output parsing."""

    def _create_vmaf_json_data(
        self,
        mean: float = 85.0,
        min_score: float = 70.0,
        max_score: float = 95.0,
        frame_count: int = 100,
        include_frames: bool = True,
    ) -> dict:
        """Create mock VMAF JSON output data."""
        data: dict = {
            "version": "vmaf_v0.6.1",
            "pooled_metrics": {
                "vmaf": {
                    "mean": mean,
                    "min": min_score,
                    "max": max_score,
                    "harmonic_mean": mean - 1.0,
                    "stdev": 5.0,
                },
            },
        }

        if include_frames:
            # Generate frame data with scores between min and max
            import random

            random.seed(42)
            frames = []
            for i in range(frame_count):
                score = random.uniform(min_score, max_score)
                frames.append(
                    {
                        "frameNum": i,
                        "metrics": {"vmaf": score},
                    }
                )
            data["frames"] = frames

        return data

    def test_parse_vmaf_output_basic(self, tmp_path: Path) -> None:
        """Test parsing basic VMAF JSON output."""
        mock_runner = MagicMock(spec=CommandRunner)
        mock_runner.check_command_exists.return_value = True

        analyzer = VmafAnalyzer(command_runner=mock_runner)

        # Create mock JSON file
        json_path = tmp_path / "vmaf.json"
        import json

        json_data = self._create_vmaf_json_data(mean=85.5, min_score=70.0, max_score=95.0)
        json_path.write_text(json.dumps(json_data))

        result = analyzer._parse_vmaf_output(
            original=tmp_path / "original.mp4",
            converted=tmp_path / "converted.mp4",
            json_path=json_path,
            sample_interval=1,
            stderr="",
        )

        assert result.scores.mean == pytest.approx(85.5)
        assert result.scores.min == pytest.approx(70.0)
        assert result.scores.max == pytest.approx(95.0)
        assert result.quality_level == VmafQualityLevel.HIGH_QUALITY
        assert result.sampled is False

    def test_parse_vmaf_output_with_sampling(self, tmp_path: Path) -> None:
        """Test parsing VMAF output with sampling enabled."""
        mock_runner = MagicMock(spec=CommandRunner)
        mock_runner.check_command_exists.return_value = True

        analyzer = VmafAnalyzer(command_runner=mock_runner)

        # Create mock JSON file
        json_path = tmp_path / "vmaf.json"
        import json

        json_data = self._create_vmaf_json_data(frame_count=10)
        json_path.write_text(json.dumps(json_data))

        result = analyzer._parse_vmaf_output(
            original=tmp_path / "original.mp4",
            converted=tmp_path / "converted.mp4",
            json_path=json_path,
            sample_interval=10,
            stderr="",
        )

        assert result.sampled is True
        assert result.sample_interval == 10

    def test_parse_vmaf_output_missing_file(self, tmp_path: Path) -> None:
        """Test parsing raises error when JSON file missing."""
        mock_runner = MagicMock(spec=CommandRunner)
        analyzer = VmafAnalyzer(command_runner=mock_runner)

        with pytest.raises(VmafAnalysisError, match="JSON output not created"):
            analyzer._parse_vmaf_output(
                original=tmp_path / "original.mp4",
                converted=tmp_path / "converted.mp4",
                json_path=tmp_path / "nonexistent.json",
                sample_interval=1,
                stderr="",
            )

    def test_parse_vmaf_output_invalid_json(self, tmp_path: Path) -> None:
        """Test parsing raises error for invalid JSON."""
        mock_runner = MagicMock(spec=CommandRunner)
        analyzer = VmafAnalyzer(command_runner=mock_runner)

        json_path = tmp_path / "vmaf.json"
        json_path.write_text("not valid json {{{")

        with pytest.raises(VmafAnalysisError, match="Failed to parse VMAF JSON"):
            analyzer._parse_vmaf_output(
                original=tmp_path / "original.mp4",
                converted=tmp_path / "converted.mp4",
                json_path=json_path,
                sample_interval=1,
                stderr="",
            )

    def test_parse_vmaf_output_no_metrics(self, tmp_path: Path) -> None:
        """Test parsing raises error when no VMAF metrics found."""
        mock_runner = MagicMock(spec=CommandRunner)
        analyzer = VmafAnalyzer(command_runner=mock_runner)

        json_path = tmp_path / "vmaf.json"
        import json

        json_path.write_text(json.dumps({"version": "vmaf_v0.6.1"}))

        with pytest.raises(VmafAnalysisError, match="No VMAF metrics found"):
            analyzer._parse_vmaf_output(
                original=tmp_path / "original.mp4",
                converted=tmp_path / "converted.mp4",
                json_path=json_path,
                sample_interval=1,
                stderr="",
            )

    def test_parse_vmaf_output_adds_warning_low_min(self, tmp_path: Path) -> None:
        """Test parsing adds warning for very low minimum scores."""
        mock_runner = MagicMock(spec=CommandRunner)
        analyzer = VmafAnalyzer(command_runner=mock_runner)

        json_path = tmp_path / "vmaf.json"
        import json

        json_data = self._create_vmaf_json_data(mean=75.0, min_score=40.0, max_score=90.0)
        json_path.write_text(json.dumps(json_data))

        result = analyzer._parse_vmaf_output(
            original=tmp_path / "original.mp4",
            converted=tmp_path / "converted.mp4",
            json_path=json_path,
            sample_interval=1,
            stderr="",
        )

        assert len(result.warnings) >= 1
        assert any("low quality" in w for w in result.warnings)

    def test_parse_vmaf_output_adds_warning_high_variance(self, tmp_path: Path) -> None:
        """Test parsing adds warning for high quality variance."""
        mock_runner = MagicMock(spec=CommandRunner)
        analyzer = VmafAnalyzer(command_runner=mock_runner)

        json_path = tmp_path / "vmaf.json"
        import json

        json_data = self._create_vmaf_json_data()
        json_data["pooled_metrics"]["vmaf"]["stdev"] = 15.0  # High variance
        json_path.write_text(json.dumps(json_data))

        result = analyzer._parse_vmaf_output(
            original=tmp_path / "original.mp4",
            converted=tmp_path / "converted.mp4",
            json_path=json_path,
            sample_interval=1,
            stderr="",
        )

        assert len(result.warnings) >= 1
        assert any("variance" in w for w in result.warnings)


class TestVmafAnalyzerFallback:
    """Tests for VMAF metrics fallback extraction."""

    def test_extract_metrics_from_frames(self) -> None:
        """Test extracting metrics from frames array."""
        mock_runner = MagicMock(spec=CommandRunner)
        analyzer = VmafAnalyzer(command_runner=mock_runner)

        data = {
            "frames": [
                {"metrics": {"vmaf": 80.0}},
                {"metrics": {"vmaf": 85.0}},
                {"metrics": {"vmaf": 90.0}},
            ],
        }

        metrics = analyzer._extract_metrics_fallback(data, "")

        assert "mean" in metrics
        assert metrics["mean"] == pytest.approx(85.0)
        assert metrics["min"] == pytest.approx(80.0)
        assert metrics["max"] == pytest.approx(90.0)

    def test_extract_metrics_from_stderr(self) -> None:
        """Test extracting metrics from FFmpeg stderr."""
        mock_runner = MagicMock(spec=CommandRunner)
        analyzer = VmafAnalyzer(command_runner=mock_runner)

        stderr = "[Parsed_libvmaf_0 @ 0x12345] VMAF score: 87.5"
        metrics = analyzer._extract_metrics_fallback({}, stderr)

        assert "mean" in metrics
        assert metrics["mean"] == pytest.approx(87.5)

    def test_extract_metrics_no_data(self) -> None:
        """Test extraction returns empty dict when no data found."""
        mock_runner = MagicMock(spec=CommandRunner)
        analyzer = VmafAnalyzer(command_runner=mock_runner)

        metrics = analyzer._extract_metrics_fallback({}, "")

        assert metrics == {}


class TestVmafAnalyzerQuickAnalyze:
    """Tests for quick_analyze convenience method."""

    def test_quick_analyze_returns_score(self, tmp_path: Path) -> None:
        """Test quick_analyze returns mean score on success."""
        mock_runner = MagicMock(spec=CommandRunner)
        mock_runner.check_command_exists.return_value = True

        # Mock the run method for availability check
        filters_result = MagicMock(spec=CommandResult)
        filters_result.success = True
        filters_result.stdout = "libvmaf"
        mock_runner.run.return_value = filters_result

        analyzer = VmafAnalyzer(command_runner=mock_runner)

        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.write_bytes(b"content")
        converted.write_bytes(b"content")

        # Mock analyze to return a result
        with patch.object(analyzer, "analyze") as mock_analyze:
            mock_result = MagicMock(spec=VmafResult)
            mock_result.scores = MagicMock()
            mock_result.scores.mean = 85.0
            mock_analyze.return_value = mock_result

            score = analyzer.quick_analyze(original, converted)

            assert score == pytest.approx(85.0)
            # Check that sampling was used
            mock_analyze.assert_called_once()
            call_kwargs = mock_analyze.call_args[1]
            assert call_kwargs["sample_interval"] == 30

    def test_quick_analyze_returns_none_on_error(self, tmp_path: Path) -> None:
        """Test quick_analyze returns None on error."""
        mock_runner = MagicMock(spec=CommandRunner)
        mock_runner.check_command_exists.return_value = False

        analyzer = VmafAnalyzer(command_runner=mock_runner)

        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"

        score = analyzer.quick_analyze(original, converted)

        assert score is None
