"""Unit tests for statistics reporter module."""

from __future__ import annotations

import csv
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from video_converter.core.history import (
    ConversionHistory,
    ConversionRecord,
    HistoryStatistics,
    StatsPeriod,
)
from video_converter.reporters.statistics_reporter import (
    StatisticsReporter,
    _format_size,
    _format_duration,
    _get_period_display,
)


class TestFormatSize:
    """Tests for _format_size helper function."""

    def test_bytes(self) -> None:
        """Test formatting bytes."""
        assert _format_size(100) == "100 B"
        assert _format_size(0) == "0 B"

    def test_kilobytes(self) -> None:
        """Test formatting kilobytes."""
        assert _format_size(1024) == "1.0 KB"
        assert _format_size(1536) == "1.5 KB"

    def test_megabytes(self) -> None:
        """Test formatting megabytes."""
        assert _format_size(1024 * 1024) == "1.0 MB"
        assert _format_size(1024 * 1024 * 500) == "500.0 MB"

    def test_gigabytes(self) -> None:
        """Test formatting gigabytes."""
        assert _format_size(1024 * 1024 * 1024) == "1.00 GB"
        assert _format_size(int(1.5 * 1024 * 1024 * 1024)) == "1.50 GB"


class TestFormatDuration:
    """Tests for _format_duration helper function."""

    def test_seconds(self) -> None:
        """Test formatting seconds."""
        assert _format_duration(45) == "45s"
        assert _format_duration(0) == "0s"

    def test_minutes(self) -> None:
        """Test formatting minutes."""
        assert _format_duration(65) == "1m 5s"
        assert _format_duration(120) == "2m 0s"

    def test_hours(self) -> None:
        """Test formatting hours."""
        assert _format_duration(3665) == "1h 1m"
        assert _format_duration(7200) == "2h 0m"


class TestGetPeriodDisplay:
    """Tests for _get_period_display helper function."""

    def test_all_period(self) -> None:
        """Test display for all time period."""
        result = _get_period_display("all", None)
        assert result == "All Time"

    def test_all_period_with_start(self) -> None:
        """Test display for all time period with start date."""
        result = _get_period_display("all", "2024-01-01T00:00:00")
        assert "2024-01-01" in result

    def test_today_period(self) -> None:
        """Test display for today period."""
        result = _get_period_display("today", None)
        assert "Today" in result
        assert datetime.now().strftime("%Y-%m-%d") in result

    def test_week_period(self) -> None:
        """Test display for week period."""
        result = _get_period_display("week", None)
        assert result == "This Week"

    def test_month_period(self) -> None:
        """Test display for month period."""
        result = _get_period_display("month", None)
        assert "This Month" in result


class TestStatisticsReporter:
    """Tests for StatisticsReporter class."""

    @pytest.fixture
    def sample_stats(self) -> HistoryStatistics:
        """Create sample statistics for testing."""
        return HistoryStatistics(
            total_converted=100,
            total_failed=5,
            total_source_bytes=1024 * 1024 * 1024 * 10,  # 10 GB
            total_output_bytes=1024 * 1024 * 1024 * 5,   # 5 GB
            total_saved_bytes=1024 * 1024 * 1024 * 5,    # 5 GB
            first_conversion="2024-01-01T00:00:00",
            last_conversion="2024-12-31T23:59:59",
            period="all",
            total_duration_seconds=3600,
        )

    @pytest.fixture
    def sample_records(self) -> list[ConversionRecord]:
        """Create sample records for testing."""
        return [
            ConversionRecord(
                id=f"test-{i}",
                source_path=f"/videos/video{i}.mov",
                output_path=f"/videos/video{i}_h265.mp4",
                source_codec="h264",
                output_codec="hevc",
                source_size=1000000 * (i + 1),
                output_size=500000 * (i + 1),
                converted_at=f"2024-01-{i+1:02d}T10:00:00",
                success=True,
            )
            for i in range(5)
        ]

    def test_format_summary(self, sample_stats: HistoryStatistics) -> None:
        """Test format_summary output."""
        reporter = StatisticsReporter()
        output = reporter.format_summary(sample_stats)

        assert "Conversion Statistics" in output
        assert "100" in output  # total_converted
        assert "95.2%" in output  # success rate (100/105)
        assert "5.00 GB" in output  # saved

    def test_format_summary_box_characters(
        self, sample_stats: HistoryStatistics
    ) -> None:
        """Test format_summary uses box drawing characters."""
        reporter = StatisticsReporter()
        output = reporter.format_summary(sample_stats)

        # Check box drawing characters
        assert "╭" in output  # top-left corner
        assert "╯" in output  # bottom-right corner
        assert "│" in output  # vertical bar
        assert "├" in output  # left junction

    def test_format_compact(self, sample_stats: HistoryStatistics) -> None:
        """Test format_compact output."""
        reporter = StatisticsReporter()
        output = reporter.format_compact(sample_stats)

        assert "100 videos converted" in output
        assert "95.2% success" in output
        assert "saved" in output

    def test_format_detailed(
        self,
        sample_stats: HistoryStatistics,
        sample_records: list[ConversionRecord],
    ) -> None:
        """Test format_detailed output with records."""
        reporter = StatisticsReporter()
        output = reporter.format_detailed(sample_stats, sample_records)

        # Should include summary
        assert "Conversion Statistics" in output

        # Should include records section
        assert "Recent Conversions" in output
        assert "video0.mov" in output

    def test_to_dict(self, sample_stats: HistoryStatistics) -> None:
        """Test to_dict conversion."""
        reporter = StatisticsReporter()
        result = reporter.to_dict(sample_stats)

        assert result["total_converted"] == 100
        assert result["total_failed"] == 5
        assert "success_rate" in result
        assert "average_compression_ratio" in result

    def test_export_json(
        self,
        sample_stats: HistoryStatistics,
        sample_records: list[ConversionRecord],
    ) -> None:
        """Test JSON export."""
        reporter = StatisticsReporter()

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "stats.json"
            reporter.export_json(sample_stats, output_path, sample_records)

            assert output_path.exists()

            with open(output_path) as f:
                data = json.load(f)

            assert "exported_at" in data
            assert "statistics" in data
            assert "records" in data
            assert len(data["records"]) == 5

    def test_export_json_without_records(
        self, sample_stats: HistoryStatistics
    ) -> None:
        """Test JSON export without records."""
        reporter = StatisticsReporter()

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "stats.json"
            reporter.export_json(sample_stats, output_path)

            with open(output_path) as f:
                data = json.load(f)

            assert "statistics" in data
            assert "records" not in data

    def test_export_csv(
        self,
        sample_stats: HistoryStatistics,
        sample_records: list[ConversionRecord],
    ) -> None:
        """Test CSV export."""
        reporter = StatisticsReporter()

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "stats.csv"
            reporter.export_csv(sample_stats, output_path, sample_records)

            assert output_path.exists()

            with open(output_path) as f:
                content = f.read()

            # Check header comments
            assert "# Video Converter Statistics Export" in content
            assert "# Total Converted: 100" in content

            # Parse CSV data
            lines = [l for l in content.split("\n") if not l.startswith("#") and l]
            assert len(lines) == 6  # header + 5 records

    def test_export_csv_creates_directory(
        self, sample_stats: HistoryStatistics
    ) -> None:
        """Test CSV export creates parent directory."""
        reporter = StatisticsReporter()

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "subdir" / "stats.csv"
            reporter.export_csv(sample_stats, output_path, [])

            assert output_path.parent.exists()


class TestStatsPeriodFiltering:
    """Tests for time-based filtering in ConversionHistory."""

    @pytest.fixture
    def history_with_records(self) -> ConversionHistory:
        """Create a ConversionHistory with test records."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            history_path = Path(tmp_dir) / "history.json"
            history = ConversionHistory(history_path)

            now = datetime.now()

            # Add records from different time periods
            records = [
                # Today
                ConversionRecord(
                    id="today-1",
                    source_path="/videos/today1.mov",
                    output_path="/videos/today1_h265.mp4",
                    source_codec="h264",
                    output_codec="hevc",
                    source_size=1000000,
                    output_size=500000,
                    converted_at=now.isoformat(),
                    success=True,
                ),
                # Yesterday
                ConversionRecord(
                    id="yesterday-1",
                    source_path="/videos/yesterday1.mov",
                    output_path="/videos/yesterday1_h265.mp4",
                    source_codec="h264",
                    output_codec="hevc",
                    source_size=2000000,
                    output_size=1000000,
                    converted_at=(now - timedelta(days=1)).isoformat(),
                    success=True,
                ),
                # Last week
                ConversionRecord(
                    id="lastweek-1",
                    source_path="/videos/lastweek1.mov",
                    output_path="/videos/lastweek1_h265.mp4",
                    source_codec="h264",
                    output_codec="hevc",
                    source_size=3000000,
                    output_size=1500000,
                    converted_at=(now - timedelta(days=10)).isoformat(),
                    success=True,
                ),
                # Last month
                ConversionRecord(
                    id="lastmonth-1",
                    source_path="/videos/lastmonth1.mov",
                    output_path="/videos/lastmonth1_h265.mp4",
                    source_codec="h264",
                    output_codec="hevc",
                    source_size=4000000,
                    output_size=2000000,
                    converted_at=(now - timedelta(days=40)).isoformat(),
                    success=True,
                ),
            ]

            for record in records:
                history.add_record(record)

            yield history

    def test_get_records_all(self, history_with_records: ConversionHistory) -> None:
        """Test getting all records."""
        records = history_with_records.get_records_by_period(StatsPeriod.ALL)
        assert len(records) == 4

    def test_get_records_today(self, history_with_records: ConversionHistory) -> None:
        """Test getting today's records."""
        records = history_with_records.get_records_by_period(StatsPeriod.TODAY)
        assert len(records) == 1
        assert records[0].id == "today-1"

    def test_get_statistics_all(self, history_with_records: ConversionHistory) -> None:
        """Test statistics for all time."""
        stats = history_with_records.get_statistics(StatsPeriod.ALL)
        assert stats.total_converted == 4
        assert stats.period == "all"

    def test_get_statistics_today(
        self, history_with_records: ConversionHistory
    ) -> None:
        """Test statistics for today."""
        stats = history_with_records.get_statistics(StatsPeriod.TODAY)
        assert stats.total_converted == 1
        assert stats.period == "today"
        assert stats.period_start is not None

    def test_get_statistics_week(
        self, history_with_records: ConversionHistory
    ) -> None:
        """Test statistics for this week."""
        stats = history_with_records.get_statistics(StatsPeriod.WEEK)
        # At minimum, today's record should be included
        assert stats.total_converted >= 1
        assert stats.period == "week"

    def test_get_statistics_month(
        self, history_with_records: ConversionHistory
    ) -> None:
        """Test statistics for this month."""
        stats = history_with_records.get_statistics(StatsPeriod.MONTH)
        # Records from this month
        assert stats.period == "month"


class TestHistoryStatisticsProperties:
    """Tests for HistoryStatistics computed properties."""

    def test_success_rate_calculation(self) -> None:
        """Test success rate calculation."""
        stats = HistoryStatistics(
            total_converted=90,
            total_failed=10,
        )
        assert stats.success_rate == pytest.approx(0.9)

    def test_success_rate_zero_total(self) -> None:
        """Test success rate with zero conversions."""
        stats = HistoryStatistics()
        assert stats.success_rate == 0.0

    def test_average_compression_ratio(self) -> None:
        """Test compression ratio calculation."""
        stats = HistoryStatistics(
            total_source_bytes=1000000,
            total_output_bytes=400000,
        )
        assert stats.average_compression_ratio == pytest.approx(0.6)

    def test_average_compression_ratio_zero_source(self) -> None:
        """Test compression ratio with zero source bytes."""
        stats = HistoryStatistics()
        assert stats.average_compression_ratio == 0.0

    def test_storage_saved_percent(self) -> None:
        """Test storage saved percentage calculation."""
        stats = HistoryStatistics(
            total_source_bytes=1000000,
            total_saved_bytes=600000,
        )
        assert stats.storage_saved_percent == pytest.approx(60.0)

    def test_storage_saved_percent_zero_source(self) -> None:
        """Test storage saved percentage with zero source bytes."""
        stats = HistoryStatistics()
        assert stats.storage_saved_percent == 0.0
