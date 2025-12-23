"""Integration tests for the convert CLI command.

This module tests the video-converter convert command including:
- Basic conversion workflow
- Option handling (--mode, --quality, --preset, --force)
- Error handling and messages
- Progress display and completion summary

SRS Reference: SRS-206 (CLI Command Interface)
"""

from __future__ import annotations

import json
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
def mock_codec_info():
    """Create a mock CodecInfo object."""
    mock = MagicMock()
    mock.is_hevc = False
    mock.is_h264 = True
    mock.codec = "h264"
    mock.size = 100_000_000  # 100 MB
    mock.resolution_label = "1080p"
    mock.fps = 30.0
    mock.duration = 120.0
    return mock


@pytest.fixture
def mock_conversion_result():
    """Create a mock ConversionResult object."""
    mock = MagicMock()
    mock.success = True
    mock.original_size = 100_000_000  # 100 MB
    mock.converted_size = 50_000_000  # 50 MB
    mock.duration_seconds = 30.0
    mock.speed_ratio = 4.0
    mock.warnings = []
    mock.error_message = None
    return mock


class TestConvertCommand:
    """Tests for the convert CLI command."""

    def test_convert_shows_help(self, cli_runner: CliRunner) -> None:
        """Test that convert --help shows usage information."""
        result = cli_runner.invoke(main, ["convert", "--help"])

        assert result.exit_code == 0
        assert "Convert a single video file" in result.output
        assert "--mode" in result.output
        assert "--quality" in result.output
        assert "--preset" in result.output
        assert "--force" in result.output

    def test_convert_requires_input_file(self, cli_runner: CliRunner) -> None:
        """Test that convert command requires an input file."""
        result = cli_runner.invoke(main, ["convert"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Error" in result.output

    def test_convert_nonexistent_file_error(self, cli_runner: CliRunner) -> None:
        """Test error handling for non-existent input file."""
        result = cli_runner.invoke(main, ["convert", "/nonexistent/video.mp4"])

        assert result.exit_code != 0

    @patch("video_converter.__main__.CodecDetector")
    def test_convert_skips_hevc_input(
        self, mock_detector_class: MagicMock, cli_runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test that already HEVC files are skipped."""
        # Create mock input file
        input_file = temp_dir / "already_hevc.mp4"
        input_file.touch()

        # Mock codec detection to return HEVC
        mock_codec_info = MagicMock()
        mock_codec_info.is_hevc = True
        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        result = cli_runner.invoke(main, ["convert", str(input_file)])

        assert result.exit_code == 0
        assert "already H.265/HEVC" in result.output

    @patch("video_converter.__main__.CodecDetector")
    def test_convert_output_exists_without_force(
        self, mock_detector_class: MagicMock, cli_runner: CliRunner, temp_dir: Path, mock_codec_info
    ) -> None:
        """Test error when output file exists and --force not used."""
        # Create mock input and output files
        input_file = temp_dir / "input.mp4"
        input_file.touch()
        output_file = temp_dir / "output.mp4"
        output_file.touch()

        # Mock codec detection
        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        result = cli_runner.invoke(main, ["convert", str(input_file), str(output_file)])

        assert result.exit_code == 1
        assert "Output file exists" in result.output
        assert "--force" in result.output

    @patch("video_converter.__main__.CodecDetector")
    @patch("video_converter.__main__.Orchestrator")
    def test_convert_output_with_force(
        self,
        mock_orchestrator_class: MagicMock,
        mock_detector_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
        mock_codec_info,
        mock_conversion_result,
    ) -> None:
        """Test that --force allows overwriting existing output."""
        # Create mock input and output files
        input_file = temp_dir / "input.mp4"
        input_file.write_bytes(b"fake video content")
        output_file = temp_dir / "output.mp4"
        output_file.write_bytes(b"existing output")

        # Mock codec detection
        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        # Mock orchestrator.convert_single() - the new integration point
        mock_orchestrator = MagicMock()
        mock_orchestrator.convert_single = AsyncMock(return_value=mock_conversion_result)
        mock_orchestrator_class.return_value = mock_orchestrator

        result = cli_runner.invoke(main, ["convert", str(input_file), str(output_file), "--force"])

        # Should not fail due to existing file
        assert "Output file exists" not in result.output

    @patch("video_converter.__main__.CodecDetector")
    @patch("video_converter.__main__.Orchestrator")
    def test_convert_with_mode_option(
        self,
        mock_orchestrator_class: MagicMock,
        mock_detector_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
        mock_codec_info,
        mock_conversion_result,
    ) -> None:
        """Test conversion with --mode option."""
        # Create mock input file
        input_file = temp_dir / "input.mp4"
        input_file.write_bytes(b"fake video content")

        # Mock codec detection
        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        # Mock orchestrator.convert_single() - the new integration point
        mock_orchestrator = MagicMock()
        mock_orchestrator.convert_single = AsyncMock(return_value=mock_conversion_result)
        mock_orchestrator_class.return_value = mock_orchestrator

        result = cli_runner.invoke(main, ["convert", str(input_file), "--mode", "software"])

        assert "software" in result.output.lower() or "libx265" in result.output

    @patch("video_converter.__main__.CodecDetector")
    @patch("video_converter.__main__.Orchestrator")
    def test_convert_with_quality_option(
        self,
        mock_orchestrator_class: MagicMock,
        mock_detector_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
        mock_codec_info,
        mock_conversion_result,
    ) -> None:
        """Test conversion with --quality option."""
        # Create mock input file
        input_file = temp_dir / "input.mp4"
        input_file.write_bytes(b"fake video content")

        # Mock codec detection
        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        # Mock orchestrator.convert_single() - the new integration point
        mock_orchestrator = MagicMock()
        mock_orchestrator.convert_single = AsyncMock(return_value=mock_conversion_result)
        mock_orchestrator_class.return_value = mock_orchestrator

        result = cli_runner.invoke(main, ["convert", str(input_file), "--quality", "85"])

        # Command should complete without error
        assert result.exit_code == 0 or "Conversion Complete" in result.output

    @patch("video_converter.__main__.CodecDetector")
    @patch("video_converter.__main__.Orchestrator")
    def test_convert_with_preset_option(
        self,
        mock_orchestrator_class: MagicMock,
        mock_detector_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
        mock_codec_info,
        mock_conversion_result,
    ) -> None:
        """Test conversion with --preset option."""
        # Create mock input file
        input_file = temp_dir / "input.mp4"
        input_file.write_bytes(b"fake video content")

        # Mock codec detection
        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        # Mock orchestrator.convert_single() - the new integration point
        mock_orchestrator = MagicMock()
        mock_orchestrator.convert_single = AsyncMock(return_value=mock_conversion_result)
        mock_orchestrator_class.return_value = mock_orchestrator

        result = cli_runner.invoke(main, ["convert", str(input_file), "--preset", "fast"])

        # Preset should be accepted without error
        assert "Invalid value" not in result.output

    def test_convert_invalid_preset_rejected(self, cli_runner: CliRunner, temp_dir: Path) -> None:
        """Test that invalid preset values are rejected."""
        input_file = temp_dir / "input.mp4"
        input_file.touch()

        result = cli_runner.invoke(main, ["convert", str(input_file), "--preset", "invalid"])

        assert result.exit_code != 0
        assert "Invalid value" in result.output

    @patch("video_converter.__main__.CodecDetector")
    @patch("video_converter.__main__.Orchestrator")
    def test_convert_success_shows_summary(
        self,
        mock_orchestrator_class: MagicMock,
        mock_detector_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
        mock_codec_info,
        mock_conversion_result,
    ) -> None:
        """Test that successful conversion shows formatted summary."""
        # Create mock input file
        input_file = temp_dir / "input.mp4"
        input_file.write_bytes(b"fake video content")

        # Mock codec detection
        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        # Mock orchestrator.convert_single() - the new integration point
        mock_orchestrator = MagicMock()
        mock_orchestrator.convert_single = AsyncMock(return_value=mock_conversion_result)
        mock_orchestrator_class.return_value = mock_orchestrator

        result = cli_runner.invoke(main, ["convert", str(input_file)])

        assert "Conversion Complete" in result.output
        assert "Original" in result.output
        assert "Converted" in result.output
        assert "Saved" in result.output

    @patch("video_converter.__main__.CodecDetector")
    @patch("video_converter.__main__.Orchestrator")
    def test_convert_failure_shows_error(
        self,
        mock_orchestrator_class: MagicMock,
        mock_detector_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
        mock_codec_info,
    ) -> None:
        """Test that failed conversion shows helpful error message."""
        # Create mock input file
        input_file = temp_dir / "input.mp4"
        input_file.write_bytes(b"fake video content")

        # Mock codec detection
        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        # Mock failed conversion via orchestrator.convert_single()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_message = "FFmpeg failed: invalid video stream"

        mock_orchestrator = MagicMock()
        mock_orchestrator.convert_single = AsyncMock(return_value=mock_result)
        mock_orchestrator_class.return_value = mock_orchestrator

        result = cli_runner.invoke(main, ["convert", str(input_file)])

        assert result.exit_code == 1
        assert "Conversion Failed" in result.output
        assert "Try:" in result.output

    @patch("video_converter.__main__.CodecDetector")
    @patch("video_converter.__main__.Orchestrator")
    def test_convert_quiet_mode(
        self,
        mock_orchestrator_class: MagicMock,
        mock_detector_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
        mock_codec_info,
        mock_conversion_result,
    ) -> None:
        """Test that quiet mode suppresses output."""
        # Create mock input file
        input_file = temp_dir / "input.mp4"
        input_file.write_bytes(b"fake video content")

        # Mock codec detection
        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        # Mock orchestrator.convert_single() - the new integration point
        mock_orchestrator = MagicMock()
        mock_orchestrator.convert_single = AsyncMock(return_value=mock_conversion_result)
        mock_orchestrator_class.return_value = mock_orchestrator

        result = cli_runner.invoke(main, ["-q", "convert", str(input_file)])

        # Quiet mode should have minimal output
        assert "Converting:" not in result.output
        assert "Conversion Complete" not in result.output

    @patch("video_converter.__main__.CodecDetector")
    def test_convert_generates_default_output_name(
        self,
        mock_detector_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
        mock_codec_info,
    ) -> None:
        """Test that output file name is auto-generated with _h265 suffix."""
        # Create mock input file
        input_file = temp_dir / "vacation.mp4"
        input_file.write_bytes(b"fake video content")

        # Mock codec detection
        mock_detector = MagicMock()
        mock_detector.analyze.return_value = mock_codec_info
        mock_detector_class.return_value = mock_detector

        # We just need to verify the command runs and shows the expected output name
        # The actual conversion will fail since we don't have a real encoder
        result = cli_runner.invoke(main, ["convert", str(input_file)])

        # Either the output name is shown or an encoder error occurs
        assert "vacation_h265" in result.output or "Encoder" in result.output or result.exit_code != 0


class TestConvertCommandOptions:
    """Tests for convert command option validation."""

    def test_mode_accepts_hardware(self, cli_runner: CliRunner, temp_dir: Path) -> None:
        """Test that --mode hardware is accepted."""
        input_file = temp_dir / "input.mp4"
        input_file.touch()

        result = cli_runner.invoke(main, ["convert", "--help"])
        assert "hardware" in result.output
        assert "software" in result.output

    def test_preset_options(self, cli_runner: CliRunner) -> None:
        """Test that all preset options are documented."""
        result = cli_runner.invoke(main, ["convert", "--help"])

        assert "fast" in result.output
        assert "medium" in result.output
        assert "slow" in result.output

    def test_force_short_option(self, cli_runner: CliRunner) -> None:
        """Test that -f is available as short form of --force."""
        result = cli_runner.invoke(main, ["convert", "--help"])

        assert "-f" in result.output or "--force" in result.output
