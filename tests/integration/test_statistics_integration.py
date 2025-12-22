"""Integration tests for statistics reporting.

This module tests the statistics collection, formatting, and export
functionality for conversion history tracking.

SRS Reference: SRS-803 (Statistics and Reporting)
SDS Reference: SDS-C01-005
"""

from __future__ import annotations

import json
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from video_converter.reporters.statistics_reporter import (
    StatisticsReporter,
    _format_duration,
    _format_size,
    _get_period_display,
)


class MockHistoryStatistics:
    """Mock HistoryStatistics for testing."""

    def __init__(
        self,
        *,
        period: str = "week",
        total_converted: int = 100,
        total_failed: int = 5,
        success_rate: float = 0.95,
        total_source_bytes: int = 10 * 1024 * 1024 * 1024,  # 10 GB
        total_output_bytes: int = 5 * 1024 * 1024 * 1024,  # 5 GB
        total_saved_bytes: int = 5 * 1024 * 1024 * 1024,  # 5 GB
        storage_saved_percent: float = 50.0,
        average_compression_ratio: float = 0.5,
        total_duration_seconds: float = 3600.0,
        first_conversion: str | None = None,
    ) -> None:
        self.period = period
        self.total_converted = total_converted
        self.total_failed = total_failed
        self.success_rate = success_rate
        self.total_source_bytes = total_source_bytes
        self.total_output_bytes = total_output_bytes
        self.total_saved_bytes = total_saved_bytes
        self.storage_saved_percent = storage_saved_percent
        self.average_compression_ratio = average_compression_ratio
        self.total_duration_seconds = total_duration_seconds
        self.first_conversion = first_conversion

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "period": self.period,
            "total_converted": self.total_converted,
            "total_failed": self.total_failed,
            "success_rate": self.success_rate,
            "total_source_bytes": self.total_source_bytes,
            "total_output_bytes": self.total_output_bytes,
            "total_saved_bytes": self.total_saved_bytes,
            "storage_saved_percent": self.storage_saved_percent,
            "average_compression_ratio": self.average_compression_ratio,
            "total_duration_seconds": self.total_duration_seconds,
        }


class MockHistoryRecord:
    """Mock history record for testing."""

    def __init__(
        self,
        *,
        id: str = "1",
        source_path: str = "/test/input.mp4",
        output_path: str = "/test/output.mp4",
        source_codec: str = "h264",
        output_codec: str = "hevc",
        source_size: int = 100000000,
        output_size: int = 50000000,
        size_saved: int = 50000000,
        compression_ratio: float = 0.5,
        converted_at: str = "2024-01-15T10:30:00",
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        self.id = id
        self.source_path = source_path
        self.output_path = output_path
        self.source_codec = source_codec
        self.output_codec = output_codec
        self.source_size = source_size
        self.output_size = output_size
        self.size_saved = size_saved
        self.compression_ratio = compression_ratio
        self.converted_at = converted_at
        self.success = success
        self.error_message = error_message


class TestSizeFormatting:
    """Tests for size formatting utility."""

    @pytest.mark.parametrize(
        "size_bytes,expected",
        [
            (0, "0 B"),
            (100, "100 B"),
            (1024, "1.0 KB"),
            (1500, "1.5 KB"),
            (1048576, "1.0 MB"),
            (1572864, "1.5 MB"),
            (1073741824, "1.00 GB"),
            (1610612736, "1.50 GB"),
            (10737418240, "10.00 GB"),
        ],
    )
    def test_format_size(self, size_bytes: int, expected: str) -> None:
        """Test size formatting for various byte values."""
        result = _format_size(size_bytes)
        assert result == expected


class TestDurationFormatting:
    """Tests for duration formatting utility."""

    @pytest.mark.parametrize(
        "seconds,expected",
        [
            (0, "0s"),
            (30, "30s"),
            (59, "59s"),
            (60, "1m 0s"),
            (90, "1m 30s"),
            (3599, "59m 59s"),
            (3600, "1h 0m"),
            (3660, "1h 1m"),
            (7200, "2h 0m"),
            (7380, "2h 3m"),
        ],
    )
    def test_format_duration(self, seconds: float, expected: str) -> None:
        """Test duration formatting for various second values."""
        result = _format_duration(seconds)
        assert result == expected


class TestPeriodDisplay:
    """Tests for period display formatting."""

    def test_period_today(self) -> None:
        """Test today period display."""
        result = _get_period_display("today", None)
        assert "Today" in result
        assert datetime.now().strftime("%Y-%m-%d") in result

    def test_period_week(self) -> None:
        """Test week period display."""
        result = _get_period_display("week", None)
        assert result == "This Week"

    def test_period_month(self) -> None:
        """Test month period display."""
        result = _get_period_display("month", None)
        assert "This Month" in result
        assert datetime.now().strftime("%B") in result

    def test_period_all_with_start(self) -> None:
        """Test all time period with start date."""
        result = _get_period_display("all", "2024-01-01T00:00:00")
        assert "All Time" in result
        assert "2024-01-01" in result

    def test_period_all_without_start(self) -> None:
        """Test all time period without start date."""
        result = _get_period_display("all", None)
        assert result == "All Time"


class TestStatisticsReporter:
    """Tests for StatisticsReporter class."""

    @pytest.fixture
    def reporter(self) -> StatisticsReporter:
        """Create a StatisticsReporter for testing."""
        return StatisticsReporter()

    @pytest.fixture
    def sample_stats(self) -> MockHistoryStatistics:
        """Create sample statistics for testing."""
        return MockHistoryStatistics()

    def test_format_summary_contains_header(
        self, reporter: StatisticsReporter, sample_stats: MockHistoryStatistics
    ) -> None:
        """Test that format_summary includes header."""
        result = reporter.format_summary(sample_stats)
        assert "Conversion Statistics" in result

    def test_format_summary_contains_period(
        self, reporter: StatisticsReporter, sample_stats: MockHistoryStatistics
    ) -> None:
        """Test that format_summary includes period."""
        result = reporter.format_summary(sample_stats)
        assert "Period" in result
        assert "Week" in result

    def test_format_summary_contains_video_count(
        self, reporter: StatisticsReporter, sample_stats: MockHistoryStatistics
    ) -> None:
        """Test that format_summary includes video count."""
        result = reporter.format_summary(sample_stats)
        assert "Videos Converted" in result
        assert "100" in result

    def test_format_summary_contains_success_rate(
        self, reporter: StatisticsReporter, sample_stats: MockHistoryStatistics
    ) -> None:
        """Test that format_summary includes success rate."""
        result = reporter.format_summary(sample_stats)
        assert "Success Rate" in result
        assert "95.0%" in result

    def test_format_summary_contains_storage_info(
        self, reporter: StatisticsReporter, sample_stats: MockHistoryStatistics
    ) -> None:
        """Test that format_summary includes storage information."""
        result = reporter.format_summary(sample_stats)
        assert "Storage Saved" in result
        assert "GB" in result

    def test_format_summary_contains_compression_ratio(
        self, reporter: StatisticsReporter, sample_stats: MockHistoryStatistics
    ) -> None:
        """Test that format_summary includes compression ratio."""
        result = reporter.format_summary(sample_stats)
        assert "Compression" in result
        assert "50.0%" in result

    def test_format_summary_contains_total_time(
        self, reporter: StatisticsReporter, sample_stats: MockHistoryStatistics
    ) -> None:
        """Test that format_summary includes total time."""
        result = reporter.format_summary(sample_stats)
        assert "Total Time" in result
        assert "1h" in result

    def test_format_summary_box_drawing(
        self, reporter: StatisticsReporter, sample_stats: MockHistoryStatistics
    ) -> None:
        """Test that format_summary uses box drawing characters."""
        result = reporter.format_summary(sample_stats)
        # Check for box drawing characters
        assert "╭" in result or "─" in result

    def test_format_compact(
        self, reporter: StatisticsReporter, sample_stats: MockHistoryStatistics
    ) -> None:
        """Test compact format output."""
        result = reporter.format_compact(sample_stats)

        assert "100 videos converted" in result
        assert "95.0% success" in result
        assert "saved" in result

    def test_format_detailed_includes_summary(
        self, reporter: StatisticsReporter, sample_stats: MockHistoryStatistics
    ) -> None:
        """Test that detailed format includes summary."""
        result = reporter.format_detailed(sample_stats)
        assert "Conversion Statistics" in result

    def test_format_detailed_with_records(
        self, reporter: StatisticsReporter, sample_stats: MockHistoryStatistics
    ) -> None:
        """Test detailed format with records."""
        records = [
            MockHistoryRecord(id="1", source_path="/test/video1.mp4"),
            MockHistoryRecord(id="2", source_path="/test/video2.mp4"),
        ]

        result = reporter.format_detailed(sample_stats, records)

        assert "Recent Conversions" in result
        assert "video1.mp4" in result
        assert "video2.mp4" in result

    def test_to_dict(
        self, reporter: StatisticsReporter, sample_stats: MockHistoryStatistics
    ) -> None:
        """Test dictionary conversion."""
        result = reporter.to_dict(sample_stats)

        assert isinstance(result, dict)
        assert result["total_converted"] == 100
        assert result["success_rate"] == 0.95


class TestStatisticsExport:
    """Tests for statistics export functionality."""

    @pytest.fixture
    def reporter(self) -> StatisticsReporter:
        """Create a StatisticsReporter for testing."""
        return StatisticsReporter()

    @pytest.fixture
    def sample_stats(self) -> MockHistoryStatistics:
        """Create sample statistics for testing."""
        return MockHistoryStatistics()

    def test_export_json(
        self,
        reporter: StatisticsReporter,
        sample_stats: MockHistoryStatistics,
        tmp_path: Path,
    ) -> None:
        """Test JSON export."""
        output_path = tmp_path / "stats.json"
        reporter.export_json(sample_stats, output_path)

        assert output_path.exists()

        with open(output_path) as f:
            data = json.load(f)

        assert "exported_at" in data
        assert "statistics" in data
        assert data["statistics"]["total_converted"] == 100

    def test_export_json_with_records(
        self,
        reporter: StatisticsReporter,
        sample_stats: MockHistoryStatistics,
        tmp_path: Path,
    ) -> None:
        """Test JSON export with records."""
        records = [
            MockHistoryRecord(id="1"),
            MockHistoryRecord(id="2"),
        ]

        output_path = tmp_path / "stats_with_records.json"
        reporter.export_json(sample_stats, output_path, records)

        with open(output_path) as f:
            data = json.load(f)

        assert "records" in data
        assert len(data["records"]) == 2

    def test_export_json_creates_directory(
        self,
        reporter: StatisticsReporter,
        sample_stats: MockHistoryStatistics,
        tmp_path: Path,
    ) -> None:
        """Test that JSON export creates parent directory."""
        output_path = tmp_path / "subdir" / "stats.json"
        reporter.export_json(sample_stats, output_path)

        assert output_path.exists()

    def test_export_csv(
        self,
        reporter: StatisticsReporter,
        sample_stats: MockHistoryStatistics,
        tmp_path: Path,
    ) -> None:
        """Test CSV export."""
        records = [
            MockHistoryRecord(id="1"),
            MockHistoryRecord(id="2"),
        ]

        output_path = tmp_path / "stats.csv"
        reporter.export_csv(sample_stats, output_path, records)

        assert output_path.exists()

        content = output_path.read_text()
        assert "# Video Converter Statistics Export" in content
        assert "id,source_path,output_path" in content

    def test_export_csv_with_comment_header(
        self,
        reporter: StatisticsReporter,
        sample_stats: MockHistoryStatistics,
        tmp_path: Path,
    ) -> None:
        """Test that CSV export includes comment header."""
        output_path = tmp_path / "stats.csv"
        reporter.export_csv(sample_stats, output_path, [])

        content = output_path.read_text()
        assert "# Period: week" in content
        assert "# Total Converted: 100" in content


class TestStatisticsPrinting:
    """Tests for statistics printing functionality."""

    @pytest.fixture
    def reporter(self) -> StatisticsReporter:
        """Create a StatisticsReporter for testing."""
        return StatisticsReporter()

    @pytest.fixture
    def sample_stats(self) -> MockHistoryStatistics:
        """Create sample statistics for testing."""
        return MockHistoryStatistics()

    def test_print_summary_to_stream(
        self, reporter: StatisticsReporter, sample_stats: MockHistoryStatistics
    ) -> None:
        """Test printing summary to a stream."""
        stream = StringIO()
        reporter.print_summary(sample_stats, stream)

        output = stream.getvalue()
        assert "Conversion Statistics" in output


class TestStatisticsWorkflowIntegration:
    """Integration tests for statistics workflow."""

    def test_full_statistics_workflow(self, tmp_path: Path) -> None:
        """Test complete statistics workflow simulation."""
        reporter = StatisticsReporter()

        # Simulate statistics after batch conversion
        stats = MockHistoryStatistics(
            period="today",
            total_converted=50,
            total_failed=2,
            success_rate=0.96,
            total_source_bytes=25 * 1024 * 1024 * 1024,  # 25 GB
            total_output_bytes=12 * 1024 * 1024 * 1024,  # 12 GB
            total_saved_bytes=13 * 1024 * 1024 * 1024,  # 13 GB
            storage_saved_percent=52.0,
            average_compression_ratio=0.48,
            total_duration_seconds=7200.0,  # 2 hours
        )

        # Generate summary
        summary = reporter.format_summary(stats)
        assert "50" in summary
        assert "96.0%" in summary

        # Generate compact
        compact = reporter.format_compact(stats)
        assert "50 videos" in compact

        # Export to JSON
        json_path = tmp_path / "conversion_stats.json"
        reporter.export_json(stats, json_path)
        assert json_path.exists()

        # Verify JSON content
        with open(json_path) as f:
            data = json.load(f)
        assert data["statistics"]["total_converted"] == 50

    def test_statistics_with_failed_records(self, tmp_path: Path) -> None:
        """Test statistics with failed conversion records."""
        reporter = StatisticsReporter()

        stats = MockHistoryStatistics(
            total_converted=10,
            total_failed=5,
            success_rate=0.67,
        )

        records = [
            MockHistoryRecord(id=str(i), success=(i < 7))
            for i in range(12)
        ]
        # Add error messages to failed ones
        for i in range(7, 12):
            records[i].error_message = f"Error in conversion {i}"

        detailed = reporter.format_detailed(stats, records)
        assert "FAILED" in detailed or "Recent Conversions" in detailed

    def test_statistics_zero_conversions(self) -> None:
        """Test statistics with zero conversions."""
        reporter = StatisticsReporter()

        stats = MockHistoryStatistics(
            total_converted=0,
            total_failed=0,
            success_rate=0.0,
            total_source_bytes=0,
            total_output_bytes=0,
            total_saved_bytes=0,
            storage_saved_percent=0.0,
            average_compression_ratio=0.0,
            total_duration_seconds=0.0,
        )

        summary = reporter.format_summary(stats)
        assert "0" in summary

        compact = reporter.format_compact(stats)
        assert "0 videos" in compact
