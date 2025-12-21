"""Unit tests for batch reporter module."""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from video_converter.core.types import ConversionReport, ConversionRequest, ConversionResult
from video_converter.reporters.batch_reporter import BatchReporter, _format_size, _format_duration


class TestFormatSize:
    """Tests for _format_size helper function."""

    def test_bytes(self) -> None:
        """Test formatting bytes."""
        assert _format_size(0) == "0 B"
        assert _format_size(500) == "500 B"
        assert _format_size(1023) == "1023 B"

    def test_kilobytes(self) -> None:
        """Test formatting kilobytes."""
        assert _format_size(1024) == "1.0 KB"
        assert _format_size(1536) == "1.5 KB"
        assert _format_size(1024 * 1000) == "1000.0 KB"

    def test_megabytes(self) -> None:
        """Test formatting megabytes."""
        assert _format_size(1024 * 1024) == "1.0 MB"
        assert _format_size(1024 * 1024 * 512) == "512.0 MB"

    def test_gigabytes(self) -> None:
        """Test formatting gigabytes."""
        assert _format_size(1024 * 1024 * 1024) == "1.00 GB"
        assert _format_size(int(1024 * 1024 * 1024 * 2.5)) == "2.50 GB"


class TestFormatDuration:
    """Tests for _format_duration helper function."""

    def test_seconds(self) -> None:
        """Test formatting seconds."""
        assert _format_duration(0) == "0.0s"
        assert _format_duration(45.5) == "45.5s"
        assert _format_duration(59.9) == "59.9s"

    def test_minutes(self) -> None:
        """Test formatting minutes."""
        assert _format_duration(60) == "1m 0s"
        assert _format_duration(90) == "1m 30s"
        assert _format_duration(3599) == "59m 59s"

    def test_hours(self) -> None:
        """Test formatting hours."""
        assert _format_duration(3600) == "1h 0m"
        assert _format_duration(3660) == "1h 1m"
        assert _format_duration(7200) == "2h 0m"


class TestBatchReporter:
    """Tests for BatchReporter class."""

    def _create_sample_report(self) -> ConversionReport:
        """Create a sample conversion report for testing."""
        started = datetime(2024, 1, 15, 10, 0, 0)
        completed = datetime(2024, 1, 15, 10, 30, 0)

        report = ConversionReport(
            session_id="abc12345",
            started_at=started,
            completed_at=completed,
            total_files=5,
            successful=3,
            failed=1,
            skipped=1,
            total_original_size=1024 * 1024 * 100,  # 100 MB
            total_converted_size=1024 * 1024 * 50,   # 50 MB
        )

        # Add some results
        for i in range(3):
            result = ConversionResult(
                success=True,
                request=ConversionRequest(
                    input_path=Path(f"/videos/video{i}.mov"),
                    output_path=Path(f"/output/video{i}.mp4"),
                ),
                original_size=1024 * 1024 * 30,
                converted_size=1024 * 1024 * 15,
            )
            report.results.append(result)

        # Add a failed result
        failed_result = ConversionResult(
            success=False,
            request=ConversionRequest(
                input_path=Path("/videos/failed.mov"),
                output_path=Path("/output/failed.mp4"),
            ),
            error_message="Encoding failed: corrupt input",
        )
        report.results.append(failed_result)
        report.errors.append("failed.mov: Encoding failed: corrupt input")

        return report

    def test_format_summary(self) -> None:
        """Test summary formatting."""
        reporter = BatchReporter()
        report = self._create_sample_report()

        summary = reporter.format_summary(report)

        assert "abc12345" in summary
        assert "2024-01-15" in summary
        assert "Total files:" in summary
        assert "Successful:" in summary
        assert "Failed:" in summary
        assert "PARTIAL SUCCESS" in summary
        assert "Storage Savings" in summary
        assert "Errors" in summary

    def test_format_summary_empty_report(self) -> None:
        """Test summary formatting for empty report."""
        reporter = BatchReporter()
        report = ConversionReport(
            session_id="empty123",
            started_at=datetime.now(),
            total_files=0,
        )

        summary = reporter.format_summary(report)

        assert "empty123" in summary
        assert "Total files:" in summary

    def test_format_summary_cancelled(self) -> None:
        """Test summary shows cancelled status."""
        reporter = BatchReporter()
        report = ConversionReport(
            session_id="cancel123",
            started_at=datetime.now(),
            total_files=5,
            cancelled=True,
        )

        summary = reporter.format_summary(report)

        assert "CANCELLED" in summary

    def test_format_details(self) -> None:
        """Test details formatting."""
        reporter = BatchReporter()
        report = self._create_sample_report()

        details = reporter.format_details(report)

        assert "File Details" in details
        assert "OK" in details
        assert "FAILED" in details
        assert "video0.mov" in details
        assert "failed.mov" in details

    def test_write_report(self) -> None:
        """Test writing report to file."""
        reporter = BatchReporter()
        report = self._create_sample_report()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.txt"
            reporter.write_report(report, output_path)

            assert output_path.exists()
            content = output_path.read_text()
            assert "abc12345" in content
            assert "File Details" in content

    def test_write_report_without_details(self) -> None:
        """Test writing report without details."""
        reporter = BatchReporter()
        report = self._create_sample_report()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "summary.txt"
            reporter.write_report(report, output_path, include_details=False)

            content = output_path.read_text()
            assert "abc12345" in content
            assert "File Details" not in content

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        reporter = BatchReporter()
        report = self._create_sample_report()

        result_dict = reporter.to_dict(report)

        assert result_dict["session_id"] == "abc12345"
        assert result_dict["total_files"] == 5
        assert result_dict["successful"] == 3
        assert result_dict["failed"] == 1
        assert result_dict["skipped"] == 1
        assert result_dict["total_original_size"] == 1024 * 1024 * 100
        assert result_dict["total_converted_size"] == 1024 * 1024 * 50
        assert len(result_dict["results"]) == 4
        assert len(result_dict["errors"]) == 1

    def test_to_dict_empty_report(self) -> None:
        """Test to_dict with empty report."""
        reporter = BatchReporter()
        report = ConversionReport(
            session_id="empty",
            started_at=datetime.now(),
        )

        result_dict = reporter.to_dict(report)

        assert result_dict["session_id"] == "empty"
        assert result_dict["results"] == []
        assert result_dict["errors"] == []
