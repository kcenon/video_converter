"""Tests for the 'convert' CLI command.

This module tests the video-converter convert command including:
- Basic conversion workflow
- VMAF options
- Metadata options
- Validation options
- Error handling
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
        """Test conversion with VMAF quality measurement."""
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

        mock_converter = MagicMock()
        mock_converter.convert = AsyncMock(return_value=mock_result)

        mock_orchestrator = MagicMock()
        mock_orchestrator.converter_factory.get_converter.return_value = mock_converter
        mock_orchestrator_class.return_value = mock_orchestrator

        result = cli_runner.invoke(main, [
            "convert",
            str(input_file),
            "--vmaf",
            "--vmaf-threshold", "90",
        ])

        assert "VMAF" in result.output or result.exit_code == 0


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
        """Test conversion with hardware mode."""
        input_file = temp_dir / "input.mp4"
        input_file.write_bytes(b"fake video content")

        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        mock_converter = MagicMock()
        mock_converter.convert = AsyncMock(return_value=mock_conversion_result)

        mock_orchestrator = MagicMock()
        mock_orchestrator.converter_factory.get_converter.return_value = mock_converter
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
        """Test conversion with software mode."""
        input_file = temp_dir / "input.mp4"
        input_file.write_bytes(b"fake video content")

        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        mock_converter = MagicMock()
        mock_converter.convert = AsyncMock(return_value=mock_conversion_result)

        mock_orchestrator = MagicMock()
        mock_orchestrator.converter_factory.get_converter.return_value = mock_converter
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
        """Test error handling when encoder is not available."""
        input_file = temp_dir / "input.mp4"
        input_file.write_bytes(b"fake video content")

        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        mock_orchestrator = MagicMock()
        mock_orchestrator.converter_factory.get_converter.side_effect = Exception(
            "Hardware encoder not available"
        )
        mock_orchestrator_class.return_value = mock_orchestrator

        result = cli_runner.invoke(main, [
            "convert",
            str(input_file),
        ])

        assert result.exit_code == 1
        assert "Encoder" in result.output or "not available" in result.output


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
        """Test that conversion warnings are displayed."""
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

        mock_converter = MagicMock()
        mock_converter.convert = AsyncMock(return_value=mock_result)

        mock_orchestrator = MagicMock()
        mock_orchestrator.converter_factory.get_converter.return_value = mock_converter
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
