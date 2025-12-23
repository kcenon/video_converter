"""Tests for statistics-related CLI commands.

This module tests the video-converter stats commands including:
- stats: View conversion statistics
- stats-export: Export statistics to file
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from video_converter.__main__ import main


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_history_stats() -> MagicMock:
    """Create mock statistics data."""
    from video_converter.core.history import StatsPeriod

    mock_stats = MagicMock()
    mock_stats.total_converted = 10
    mock_stats.total_failed = 2
    mock_stats.total_skipped = 1
    mock_stats.total_original_bytes = 10_000_000_000  # 10 GB
    mock_stats.total_converted_bytes = 5_000_000_000  # 5 GB
    mock_stats.total_saved_bytes = 5_000_000_000  # 5 GB
    mock_stats.average_compression_ratio = 50.0
    mock_stats.average_duration_seconds = 30.0
    mock_stats.period = StatsPeriod.ALL
    return mock_stats


class TestStatsCommand:
    """Tests for the stats command."""

    def test_stats_shows_help(self, cli_runner: CliRunner) -> None:
        """Test that stats --help shows usage information."""
        result = cli_runner.invoke(main, ["stats", "--help"])

        assert result.exit_code == 0
        assert "Show conversion statistics" in result.output
        assert "--period" in result.output
        assert "--json" in result.output
        assert "--detailed" in result.output

    @patch("video_converter.reporters.statistics_reporter.StatisticsReporter")
    @patch("video_converter.core.history.get_history")
    def test_stats_all_time(
        self,
        mock_get_history: MagicMock,
        mock_reporter_class: MagicMock,
        cli_runner: CliRunner,
        mock_history_stats: MagicMock,
    ) -> None:
        """Test stats with all-time period."""
        mock_history = MagicMock()
        mock_history.get_statistics.return_value = mock_history_stats
        mock_get_history.return_value = mock_history

        mock_reporter = MagicMock()
        mock_reporter.format_summary.return_value = "Statistics summary"
        mock_reporter_class.return_value = mock_reporter

        result = cli_runner.invoke(main, ["stats"])

        assert result.exit_code == 0

    @patch("video_converter.reporters.statistics_reporter.StatisticsReporter")
    @patch("video_converter.core.history.get_history")
    def test_stats_period_today(
        self,
        mock_get_history: MagicMock,
        mock_reporter_class: MagicMock,
        cli_runner: CliRunner,
        mock_history_stats: MagicMock,
    ) -> None:
        """Test stats with today period."""
        mock_history = MagicMock()
        mock_history.get_statistics.return_value = mock_history_stats
        mock_get_history.return_value = mock_history

        mock_reporter = MagicMock()
        mock_reporter.format_summary.return_value = "Today's statistics"
        mock_reporter_class.return_value = mock_reporter

        result = cli_runner.invoke(main, ["stats", "--period", "today"])

        assert result.exit_code == 0

    @patch("video_converter.reporters.statistics_reporter.StatisticsReporter")
    @patch("video_converter.core.history.get_history")
    def test_stats_period_week(
        self,
        mock_get_history: MagicMock,
        mock_reporter_class: MagicMock,
        cli_runner: CliRunner,
        mock_history_stats: MagicMock,
    ) -> None:
        """Test stats with week period."""
        mock_history = MagicMock()
        mock_history.get_statistics.return_value = mock_history_stats
        mock_get_history.return_value = mock_history

        mock_reporter = MagicMock()
        mock_reporter.format_summary.return_value = "Week statistics"
        mock_reporter_class.return_value = mock_reporter

        result = cli_runner.invoke(main, ["stats", "--period", "week"])

        assert result.exit_code == 0

    @patch("video_converter.reporters.statistics_reporter.StatisticsReporter")
    @patch("video_converter.core.history.get_history")
    def test_stats_json_output(
        self,
        mock_get_history: MagicMock,
        mock_reporter_class: MagicMock,
        cli_runner: CliRunner,
        mock_history_stats: MagicMock,
    ) -> None:
        """Test stats with JSON output format."""
        mock_history = MagicMock()
        mock_history.get_statistics.return_value = mock_history_stats
        mock_get_history.return_value = mock_history

        mock_reporter = MagicMock()
        mock_reporter.to_dict.return_value = {"total_converted": 10}
        mock_reporter_class.return_value = mock_reporter

        result = cli_runner.invoke(main, ["stats", "--json"])

        assert result.exit_code == 0
        # JSON output should contain the statistics
        assert "total_converted" in result.output or "{" in result.output

    @patch("video_converter.reporters.statistics_reporter.StatisticsReporter")
    @patch("video_converter.core.history.get_history")
    def test_stats_detailed(
        self,
        mock_get_history: MagicMock,
        mock_reporter_class: MagicMock,
        cli_runner: CliRunner,
        mock_history_stats: MagicMock,
    ) -> None:
        """Test stats with detailed output."""
        mock_history = MagicMock()
        mock_history.get_statistics.return_value = mock_history_stats
        mock_history.get_records_by_period.return_value = []
        mock_get_history.return_value = mock_history

        mock_reporter = MagicMock()
        mock_reporter.format_detailed.return_value = "Detailed statistics"
        mock_reporter_class.return_value = mock_reporter

        result = cli_runner.invoke(main, ["stats", "--detailed"])

        assert result.exit_code == 0

    @patch("video_converter.reporters.statistics_reporter.StatisticsReporter")
    @patch("video_converter.core.history.get_history")
    def test_stats_empty_history(
        self,
        mock_get_history: MagicMock,
        mock_reporter_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test stats when no conversions have been recorded."""
        from video_converter.core.history import StatsPeriod

        mock_stats = MagicMock()
        mock_stats.total_converted = 0
        mock_stats.period = StatsPeriod.ALL

        mock_history = MagicMock()
        mock_history.get_statistics.return_value = mock_stats
        mock_get_history.return_value = mock_history

        mock_reporter = MagicMock()
        mock_reporter.format_summary.return_value = "No statistics"
        mock_reporter_class.return_value = mock_reporter

        result = cli_runner.invoke(main, ["stats"])

        assert result.exit_code == 0
        # Should show message about no conversions
        assert "No conversions" in result.output or result.output


class TestStatsExportCommand:
    """Tests for the stats-export command."""

    def test_stats_export_shows_help(self, cli_runner: CliRunner) -> None:
        """Test that stats-export --help shows usage information."""
        result = cli_runner.invoke(main, ["stats-export", "--help"])

        assert result.exit_code == 0
        assert "Export" in result.output
        assert "--format" in result.output
        assert "--output" in result.output
        assert "--include-records" in result.output

    @patch("video_converter.reporters.statistics_reporter.StatisticsReporter")
    @patch("video_converter.core.history.get_history")
    def test_stats_export_json(
        self,
        mock_get_history: MagicMock,
        mock_reporter_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
        mock_history_stats: MagicMock,
    ) -> None:
        """Test exporting statistics to JSON."""
        mock_history = MagicMock()
        mock_history.get_statistics.return_value = mock_history_stats
        mock_get_history.return_value = mock_history

        mock_reporter = MagicMock()
        mock_reporter_class.return_value = mock_reporter

        output_file = temp_dir / "stats.json"
        result = cli_runner.invoke(main, [
            "stats-export",
            "--format", "json",
            "-o", str(output_file),
        ])

        assert result.exit_code == 0
        assert "exported" in result.output.lower()

    @patch("video_converter.reporters.statistics_reporter.StatisticsReporter")
    @patch("video_converter.core.history.get_history")
    def test_stats_export_csv(
        self,
        mock_get_history: MagicMock,
        mock_reporter_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
        mock_history_stats: MagicMock,
    ) -> None:
        """Test exporting statistics to CSV."""
        mock_history = MagicMock()
        mock_history.get_statistics.return_value = mock_history_stats
        mock_get_history.return_value = mock_history

        mock_reporter = MagicMock()
        mock_reporter_class.return_value = mock_reporter

        output_file = temp_dir / "stats.csv"
        result = cli_runner.invoke(main, [
            "stats-export",
            "--format", "csv",
            "-o", str(output_file),
        ])

        assert result.exit_code == 0
        assert "exported" in result.output.lower()

    @patch("video_converter.reporters.statistics_reporter.StatisticsReporter")
    @patch("video_converter.core.history.get_history")
    def test_stats_export_with_period(
        self,
        mock_get_history: MagicMock,
        mock_reporter_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
        mock_history_stats: MagicMock,
    ) -> None:
        """Test exporting statistics with period filter."""
        mock_history = MagicMock()
        mock_history.get_statistics.return_value = mock_history_stats
        mock_get_history.return_value = mock_history

        mock_reporter = MagicMock()
        mock_reporter_class.return_value = mock_reporter

        output_file = temp_dir / "stats_week.json"
        result = cli_runner.invoke(main, [
            "stats-export",
            "--period", "week",
            "-o", str(output_file),
        ])

        assert result.exit_code == 0
        assert "week" in result.output.lower()

    @patch("video_converter.reporters.statistics_reporter.StatisticsReporter")
    @patch("video_converter.core.history.get_history")
    def test_stats_export_include_records(
        self,
        mock_get_history: MagicMock,
        mock_reporter_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
        mock_history_stats: MagicMock,
    ) -> None:
        """Test exporting statistics with records."""
        mock_history = MagicMock()
        mock_history.get_statistics.return_value = mock_history_stats
        mock_history.get_records_by_period.return_value = [MagicMock(), MagicMock()]
        mock_get_history.return_value = mock_history

        mock_reporter = MagicMock()
        mock_reporter_class.return_value = mock_reporter

        output_file = temp_dir / "stats_records.json"
        result = cli_runner.invoke(main, [
            "stats-export",
            "--include-records",
            "-o", str(output_file),
        ])

        assert result.exit_code == 0
        assert "Records: 2" in result.output
