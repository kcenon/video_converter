"""Unit tests for core types module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from video_converter.core.types import (
    ConversionMode,
    ConversionProgress,
    ConversionReport,
    ConversionRequest,
    ConversionResult,
    ConversionStage,
    ConversionStatus,
)


class TestConversionMode:
    """Tests for ConversionMode enum."""

    def test_hardware_mode(self) -> None:
        """Test hardware mode value."""
        assert ConversionMode.HARDWARE.value == "hardware"

    def test_software_mode(self) -> None:
        """Test software mode value."""
        assert ConversionMode.SOFTWARE.value == "software"


class TestConversionStage:
    """Tests for ConversionStage enum."""

    def test_all_stages_present(self) -> None:
        """Test all pipeline stages are defined."""
        stages = [s.value for s in ConversionStage]
        assert "discovery" in stages
        assert "export" in stages
        assert "convert" in stages
        assert "validate" in stages
        assert "metadata" in stages
        assert "cleanup" in stages
        assert "complete" in stages


class TestConversionStatus:
    """Tests for ConversionStatus enum."""

    def test_all_statuses_present(self) -> None:
        """Test all statuses are defined."""
        statuses = [s.value for s in ConversionStatus]
        assert "pending" in statuses
        assert "in_progress" in statuses
        assert "completed" in statuses
        assert "failed" in statuses
        assert "skipped" in statuses
        assert "cancelled" in statuses


class TestConversionRequest:
    """Tests for ConversionRequest dataclass."""

    def test_basic_creation(self) -> None:
        """Test creating a basic conversion request."""
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
        )
        assert request.input_path == Path("input.mov")
        assert request.output_path == Path("output.mp4")
        assert request.mode == ConversionMode.HARDWARE
        assert request.quality == 45
        assert request.crf == 22
        assert request.preset == "medium"
        assert request.audio_mode == "copy"
        assert request.preserve_metadata is True

    def test_custom_settings(self) -> None:
        """Test creating a request with custom settings."""
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
            mode=ConversionMode.SOFTWARE,
            quality=80,
            crf=18,
            preset="slow",
            audio_mode="aac",
            preserve_metadata=False,
        )
        assert request.mode == ConversionMode.SOFTWARE
        assert request.quality == 80
        assert request.crf == 18
        assert request.preset == "slow"
        assert request.audio_mode == "aac"
        assert request.preserve_metadata is False

    def test_string_path_conversion(self) -> None:
        """Test that string paths are converted to Path objects."""
        request = ConversionRequest(
            input_path="input.mov",  # type: ignore
            output_path="output.mp4",  # type: ignore
        )
        assert isinstance(request.input_path, Path)
        assert isinstance(request.output_path, Path)

    def test_string_mode_conversion(self) -> None:
        """Test that string mode is converted to enum."""
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
            mode="software",  # type: ignore
        )
        assert request.mode == ConversionMode.SOFTWARE


class TestConversionResult:
    """Tests for ConversionResult dataclass."""

    def test_successful_result(self) -> None:
        """Test creating a successful conversion result."""
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
        )
        result = ConversionResult(
            success=True,
            request=request,
            original_size=100_000_000,
            converted_size=40_000_000,
            duration_seconds=120.5,
            speed_ratio=5.0,
        )
        assert result.success is True
        assert result.original_size == 100_000_000
        assert result.converted_size == 40_000_000
        assert result.compression_ratio == 0.6
        assert result.size_saved == 60_000_000

    def test_failed_result(self) -> None:
        """Test creating a failed conversion result."""
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
        )
        result = ConversionResult(
            success=False,
            request=request,
            error_message="Encoder not available",
        )
        assert result.success is False
        assert result.error_message == "Encoder not available"
        assert result.compression_ratio == 0.0

    def test_compression_ratio_zero_original(self) -> None:
        """Test compression ratio when original size is zero."""
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
        )
        result = ConversionResult(
            success=True,
            request=request,
            original_size=0,
            converted_size=1000,
        )
        assert result.compression_ratio == 0.0

    def test_size_saved_negative(self) -> None:
        """Test size_saved when file grew."""
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
        )
        result = ConversionResult(
            success=True,
            request=request,
            original_size=1000,
            converted_size=2000,
        )
        assert result.size_saved == 0  # Should not be negative


class TestConversionProgress:
    """Tests for ConversionProgress dataclass."""

    def test_basic_creation(self) -> None:
        """Test creating progress info."""
        progress = ConversionProgress(
            stage=ConversionStage.CONVERT,
            status=ConversionStatus.IN_PROGRESS,
            current_file="video.mov",
            current_index=5,
            total_files=10,
            stage_progress=0.5,
            overall_progress=0.35,
        )
        assert progress.stage == ConversionStage.CONVERT
        assert progress.status == ConversionStatus.IN_PROGRESS
        assert progress.current_file == "video.mov"
        assert progress.stage_progress == 0.5
        assert progress.overall_progress == 0.35

    def test_progress_clamping(self) -> None:
        """Test that progress values are clamped to 0.0-1.0."""
        progress = ConversionProgress(
            stage=ConversionStage.CONVERT,
            status=ConversionStatus.IN_PROGRESS,
            stage_progress=1.5,
            overall_progress=-0.5,
        )
        assert progress.stage_progress == 1.0
        assert progress.overall_progress == 0.0


class TestConversionReport:
    """Tests for ConversionReport dataclass."""

    def test_empty_report(self) -> None:
        """Test creating an empty report."""
        report = ConversionReport(
            session_id="test123",
            started_at=datetime.now(),
        )
        assert report.session_id == "test123"
        assert report.total_files == 0
        assert report.successful == 0
        assert report.failed == 0
        assert report.success_rate == 0.0
        assert report.average_compression_ratio == 0.0

    def test_add_successful_result(self) -> None:
        """Test adding a successful result to the report."""
        report = ConversionReport(
            session_id="test123",
            started_at=datetime.now(),
        )
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
        )
        result = ConversionResult(
            success=True,
            request=request,
            original_size=100_000_000,
            converted_size=40_000_000,
            duration_seconds=60.0,
        )

        report.add_result(result)

        assert report.successful == 1
        assert report.failed == 0
        assert report.total_original_size == 100_000_000
        assert report.total_converted_size == 40_000_000
        assert report.total_size_saved == 60_000_000
        assert report.average_compression_ratio == 0.6
        assert report.success_rate == 1.0

    def test_add_failed_result(self) -> None:
        """Test adding a failed result to the report."""
        report = ConversionReport(
            session_id="test123",
            started_at=datetime.now(),
        )
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
        )
        result = ConversionResult(
            success=False,
            request=request,
            error_message="Encoding failed",
        )

        report.add_result(result)

        assert report.successful == 0
        assert report.failed == 1
        assert report.success_rate == 0.0
        assert len(report.errors) == 1
        assert "input.mov" in report.errors[0]

    def test_mixed_results(self) -> None:
        """Test report with mixed success and failure."""
        report = ConversionReport(
            session_id="test123",
            started_at=datetime.now(),
        )

        # Add successful result
        request1 = ConversionRequest(
            input_path=Path("input1.mov"),
            output_path=Path("output1.mp4"),
        )
        result1 = ConversionResult(
            success=True,
            request=request1,
            original_size=100_000_000,
            converted_size=40_000_000,
        )
        report.add_result(result1)

        # Add failed result
        request2 = ConversionRequest(
            input_path=Path("input2.mov"),
            output_path=Path("output2.mp4"),
        )
        result2 = ConversionResult(
            success=False,
            request=request2,
            error_message="Failed",
        )
        report.add_result(result2)

        assert report.successful == 1
        assert report.failed == 1
        assert report.success_rate == 0.5
