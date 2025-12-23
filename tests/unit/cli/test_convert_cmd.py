"""Tests for the 'convert' CLI command.

This module tests the video-converter convert command including:
- Basic conversion workflow
- VMAF options
- Metadata options
- Validation options
- Error handling
- Orchestrator pipeline integration
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from video_converter.__main__ import main


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_codec_info() -> MagicMock:
    """Create a mock CodecInfo for H.264 video."""
    mock = MagicMock()
    mock.is_hevc = False
    mock.is_h264 = True
    mock.codec = "h264"
    mock.size = 100_000_000
    mock.resolution_label = "1080p"
    mock.fps = 30.0
    mock.duration = 120.0
    return mock


@pytest.fixture
def mock_conversion_result() -> MagicMock:
    """Create a successful mock ConversionResult."""
    mock = MagicMock()
    mock.success = True
    mock.original_size = 100_000_000
    mock.converted_size = 50_000_000
    mock.size_saved = 50_000_000
    mock.duration_seconds = 30.0
    mock.speed_ratio = 4.0
    mock.warnings = []
    mock.error_message = None
    mock.vmaf_score = None
    mock.vmaf_quality_level = None
    return mock


class TestConvertVMAFOptions:
    """Tests for VMAF-related options."""

    def test_vmaf_options_in_help(self, cli_runner: CliRunner) -> None:
        """Test that VMAF options are documented."""
        result = cli_runner.invoke(main, ["convert", "--help"])

        assert result.exit_code == 0
        assert "--vmaf" in result.output
        assert "--vmaf-threshold" in result.output
        assert "--vmaf-sample-interval" in result.output

    @patch("video_converter.__main__.CodecDetector")
    @patch("video_converter.__main__.Orchestrator")
    def test_convert_with_vmaf(
        self,
        mock_orchestrator_class: MagicMock,
        mock_detector_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
        mock_codec_info: MagicMock,
    ) -> None:
        """Test conversion with VMAF quality measurement.

        Verifies that --vmaf flag triggers VMAF analysis through the
        Orchestrator pipeline.
        """
        input_file = temp_dir / "input.mp4"
        input_file.write_bytes(b"fake video content")

        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.original_size = 100_000_000
        mock_result.converted_size = 50_000_000
        mock_result.duration_seconds = 30.0
        mock_result.speed_ratio = 4.0
        mock_result.warnings = []
        mock_result.error_message = None
        mock_result.vmaf_score = 95.5
        mock_result.vmaf_quality_level = "excellent"

        # Mock orchestrator.convert_single() - the new integration point
        mock_orchestrator = MagicMock()
        mock_orchestrator.convert_single = AsyncMock(return_value=mock_result)
        mock_orchestrator_class.return_value = mock_orchestrator

        result = cli_runner.invoke(main, [
            "convert",
            str(input_file),
            "--vmaf",
            "--vmaf-threshold", "90",
        ])

        assert "VMAF" in result.output or result.exit_code == 0
        # Verify orchestrator was configured with VMAF enabled
        call_kwargs = mock_orchestrator_class.call_args.kwargs
        assert call_kwargs.get("config").enable_vmaf is True


class TestConvertMetadataOptions:
    """Tests for metadata-related options."""

    def test_metadata_options_in_help(self, cli_runner: CliRunner) -> None:
        """Test that metadata options are documented."""
        result = cli_runner.invoke(main, ["convert", "--help"])

        assert result.exit_code == 0
        assert "--preserve-metadata" in result.output
        assert "--no-preserve-metadata" in result.output

    def test_validate_options_in_help(self, cli_runner: CliRunner) -> None:
        """Test that validation options are documented."""
        result = cli_runner.invoke(main, ["convert", "--help"])

        assert result.exit_code == 0
        assert "--validate" in result.output
        assert "--no-validate" in result.output


class TestConvertModeOptions:
    """Tests for encoder mode options."""

    def test_invalid_mode_rejected(self, cli_runner: CliRunner, temp_dir: Path) -> None:
        """Test that invalid mode values are rejected."""
        input_file = temp_dir / "input.mp4"
        input_file.touch()

        result = cli_runner.invoke(main, [
            "convert",
            str(input_file),
            "--mode", "invalid",
        ])

        assert result.exit_code != 0
        assert "Invalid value" in result.output

    @patch("video_converter.__main__.CodecDetector")
    @patch("video_converter.__main__.Orchestrator")
    def test_hardware_mode(
        self,
        mock_orchestrator_class: MagicMock,
        mock_detector_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
        mock_codec_info: MagicMock,
        mock_conversion_result: MagicMock,
    ) -> None:
        """Test conversion with hardware mode uses orchestrator.convert_single()."""
        input_file = temp_dir / "input.mp4"
        input_file.write_bytes(b"fake video content")

        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        # Mock orchestrator.convert_single() - the new integration point
        mock_orchestrator = MagicMock()
        mock_orchestrator.convert_single = AsyncMock(return_value=mock_conversion_result)
        mock_orchestrator_class.return_value = mock_orchestrator

        result = cli_runner.invoke(main, [
            "convert",
            str(input_file),
            "--mode", "hardware",
        ])

        assert "hardware" in result.output.lower() or "videotoolbox" in result.output.lower()

    @patch("video_converter.__main__.CodecDetector")
    @patch("video_converter.__main__.Orchestrator")
    def test_software_mode(
        self,
        mock_orchestrator_class: MagicMock,
        mock_detector_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
        mock_codec_info: MagicMock,
        mock_conversion_result: MagicMock,
    ) -> None:
        """Test conversion with software mode uses orchestrator.convert_single()."""
        input_file = temp_dir / "input.mp4"
        input_file.write_bytes(b"fake video content")

        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        # Mock orchestrator.convert_single() - the new integration point
        mock_orchestrator = MagicMock()
        mock_orchestrator.convert_single = AsyncMock(return_value=mock_conversion_result)
        mock_orchestrator_class.return_value = mock_orchestrator

        result = cli_runner.invoke(main, [
            "convert",
            str(input_file),
            "--mode", "software",
        ])

        assert "software" in result.output.lower() or "libx265" in result.output.lower()


class TestConvertQualityOptions:
    """Tests for quality-related options."""

    def test_quality_range_in_help(self, cli_runner: CliRunner) -> None:
        """Test that quality option is documented."""
        result = cli_runner.invoke(main, ["convert", "--help"])

        assert result.exit_code == 0
        assert "--quality" in result.output
        assert "1-100" in result.output


class TestConvertEncoderErrors:
    """Tests for encoder availability errors."""

    @patch("video_converter.__main__.CodecDetector")
    @patch("video_converter.__main__.Orchestrator")
    def test_encoder_not_available(
        self,
        mock_orchestrator_class: MagicMock,
        mock_detector_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
        mock_codec_info: MagicMock,
    ) -> None:
        """Test error handling when encoder is not available.

        The orchestrator.convert_single() method internally handles encoder
        availability and returns a failed result with appropriate error message.
        """
        input_file = temp_dir / "input.mp4"
        input_file.write_bytes(b"fake video content")

        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        # Mock convert_single to return a failed result with encoder error
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_message = "Hardware encoder not available"

        mock_orchestrator = MagicMock()
        mock_orchestrator.convert_single = AsyncMock(return_value=mock_result)
        mock_orchestrator_class.return_value = mock_orchestrator

        result = cli_runner.invoke(main, [
            "convert",
            str(input_file),
        ])

        assert result.exit_code == 1
        assert "not available" in result.output.lower() or "error" in result.output.lower()


class TestConvertWarnings:
    """Tests for conversion warnings display."""

    @patch("video_converter.__main__.CodecDetector")
    @patch("video_converter.__main__.Orchestrator")
    def test_conversion_with_warnings(
        self,
        mock_orchestrator_class: MagicMock,
        mock_detector_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
        mock_codec_info: MagicMock,
    ) -> None:
        """Test that conversion warnings are displayed via orchestrator pipeline."""
        input_file = temp_dir / "input.mp4"
        input_file.write_bytes(b"fake video content")

        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.original_size = 100_000_000
        mock_result.converted_size = 50_000_000
        mock_result.duration_seconds = 30.0
        mock_result.speed_ratio = 4.0
        mock_result.warnings = ["Audio stream was re-encoded", "Subtitle stream dropped"]
        mock_result.error_message = None
        mock_result.vmaf_score = None
        mock_result.vmaf_quality_level = None

        # Mock orchestrator.convert_single() - the new integration point
        mock_orchestrator = MagicMock()
        mock_orchestrator.convert_single = AsyncMock(return_value=mock_result)
        mock_orchestrator_class.return_value = mock_orchestrator

        result = cli_runner.invoke(main, [
            "convert",
            str(input_file),
        ])

        assert result.exit_code == 0
        assert "Warnings" in result.output or "Audio stream" in result.output


class TestConvertAnalysisErrors:
    """Tests for video analysis errors."""

    @patch("video_converter.__main__.CodecDetector")
    def test_analyze_error(
        self,
        mock_detector_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
    ) -> None:
        """Test error handling when video analysis fails."""
        input_file = temp_dir / "input.mp4"
        input_file.write_bytes(b"fake video content")

        mock_detector = MagicMock()
        mock_detector.analyze.side_effect = Exception("Cannot read video format")
        mock_detector_class.return_value = mock_detector

        result = cli_runner.invoke(main, [
            "convert",
            str(input_file),
        ])

        assert result.exit_code == 1
        assert "Cannot analyze" in result.output or "error" in result.output.lower()


class TestConvertOrchestratorIntegration:
    """Tests for Orchestrator pipeline integration.

    These tests verify that the convert command properly uses the Orchestrator
    pipeline, enabling VMAF analysis, validation, retry logic, and timestamp sync.

    SRS Reference: SRS-601 (Orchestrator Workflow)
    """

    @patch("video_converter.__main__.CodecDetector")
    @patch("video_converter.__main__.Orchestrator")
    def test_vmaf_flag_triggers_analysis(
        self,
        mock_orchestrator_class: MagicMock,
        mock_detector_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
        mock_codec_info: MagicMock,
    ) -> None:
        """Verify --vmaf flag configures Orchestrator to enable VMAF analysis."""
        input_file = temp_dir / "input.mp4"
        input_file.write_bytes(b"fake video content")

        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.original_size = 100_000_000
        mock_result.converted_size = 50_000_000
        mock_result.duration_seconds = 30.0
        mock_result.speed_ratio = 4.0
        mock_result.warnings = []
        mock_result.error_message = None
        mock_result.vmaf_score = 94.5
        mock_result.vmaf_quality_level = "excellent"

        mock_orchestrator = MagicMock()
        mock_orchestrator.convert_single = AsyncMock(return_value=mock_result)
        mock_orchestrator_class.return_value = mock_orchestrator

        result = cli_runner.invoke(main, [
            "convert",
            str(input_file),
            "--vmaf",
            "--vmaf-threshold", "90",
            "--vmaf-sample-interval", "15",
        ])

        assert result.exit_code == 0

        # Verify OrchestratorConfig was created with VMAF settings
        call_kwargs = mock_orchestrator_class.call_args.kwargs
        config = call_kwargs.get("config")
        assert config is not None
        assert config.enable_vmaf is True
        assert config.vmaf_threshold == 90.0
        assert config.vmaf_sample_interval == 15

    @patch("video_converter.__main__.CodecDetector")
    @patch("video_converter.__main__.Orchestrator")
    def test_validate_flag_runs_validation(
        self,
        mock_orchestrator_class: MagicMock,
        mock_detector_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
        mock_codec_info: MagicMock,
    ) -> None:
        """Verify --validate flag configures Orchestrator to enable validation."""
        input_file = temp_dir / "input.mp4"
        input_file.write_bytes(b"fake video content")

        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.original_size = 100_000_000
        mock_result.converted_size = 50_000_000
        mock_result.duration_seconds = 30.0
        mock_result.speed_ratio = 4.0
        mock_result.warnings = []
        mock_result.error_message = None
        mock_result.vmaf_score = None
        mock_result.vmaf_quality_level = None

        mock_orchestrator = MagicMock()
        mock_orchestrator.convert_single = AsyncMock(return_value=mock_result)
        mock_orchestrator_class.return_value = mock_orchestrator

        result = cli_runner.invoke(main, [
            "convert",
            str(input_file),
            "--validate",
        ])

        assert result.exit_code == 0

        # Verify OrchestratorConfig was created with validation enabled
        call_kwargs = mock_orchestrator_class.call_args.kwargs
        config = call_kwargs.get("config")
        assert config is not None
        assert config.validate_output is True

    @patch("video_converter.__main__.CodecDetector")
    @patch("video_converter.__main__.Orchestrator")
    def test_orchestrator_convert_single_called(
        self,
        mock_orchestrator_class: MagicMock,
        mock_detector_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
        mock_codec_info: MagicMock,
    ) -> None:
        """Verify convert command uses orchestrator.convert_single() method."""
        input_file = temp_dir / "input.mp4"
        output_file = temp_dir / "output.mp4"
        input_file.write_bytes(b"fake video content")

        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.original_size = 100_000_000
        mock_result.converted_size = 50_000_000
        mock_result.duration_seconds = 30.0
        mock_result.speed_ratio = 4.0
        mock_result.warnings = []
        mock_result.error_message = None
        mock_result.vmaf_score = None
        mock_result.vmaf_quality_level = None

        mock_orchestrator = MagicMock()
        mock_orchestrator.convert_single = AsyncMock(return_value=mock_result)
        mock_orchestrator_class.return_value = mock_orchestrator

        result = cli_runner.invoke(main, [
            "convert",
            str(input_file),
            str(output_file),
        ])

        assert result.exit_code == 0

        # Verify convert_single was called with correct arguments
        mock_orchestrator.convert_single.assert_called_once()
        call_kwargs = mock_orchestrator.convert_single.call_args.kwargs
        assert call_kwargs["input_path"] == input_file
        assert call_kwargs["output_path"] == output_file

    @patch("video_converter.__main__.CodecDetector")
    @patch("video_converter.__main__.Orchestrator")
    def test_preserve_metadata_passed_to_orchestrator(
        self,
        mock_orchestrator_class: MagicMock,
        mock_detector_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
        mock_codec_info: MagicMock,
    ) -> None:
        """Verify --preserve-metadata flag is passed to Orchestrator config."""
        input_file = temp_dir / "input.mp4"
        input_file.write_bytes(b"fake video content")

        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.original_size = 100_000_000
        mock_result.converted_size = 50_000_000
        mock_result.duration_seconds = 30.0
        mock_result.speed_ratio = 4.0
        mock_result.warnings = []
        mock_result.error_message = None
        mock_result.vmaf_score = None
        mock_result.vmaf_quality_level = None

        mock_orchestrator = MagicMock()
        mock_orchestrator.convert_single = AsyncMock(return_value=mock_result)
        mock_orchestrator_class.return_value = mock_orchestrator

        # Test with --no-preserve-metadata
        result = cli_runner.invoke(main, [
            "convert",
            str(input_file),
            "--no-preserve-metadata",
        ])

        assert result.exit_code == 0

        # Verify config has preserve_metadata=False
        call_kwargs = mock_orchestrator_class.call_args.kwargs
        config = call_kwargs.get("config")
        assert config is not None
        assert config.preserve_metadata is False
