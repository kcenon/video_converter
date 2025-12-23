"""Statistics reporter for generating formatted conversion statistics.

This module provides a reporter class that generates formatted output
for conversion statistics with support for various output formats.

SDS Reference: SDS-C01-005
SRS Reference: SRS-803 (Statistics and Reporting)

Example:
    >>> from video_converter.reporters.statistics_reporter import StatisticsReporter
    >>> from video_converter.core.history import get_history, StatsPeriod
    >>>
    >>> reporter = StatisticsReporter()
    >>> history = get_history()
    >>> stats = history.get_statistics(StatsPeriod.WEEK)
    >>> print(reporter.format_summary(stats))
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from video_converter.core.history import HistoryStatistics


def _format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Human-readable size string (e.g., "1.5 GB").
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _format_duration(seconds: float) -> str:
    """Format duration as human-readable string.

    Args:
        seconds: Duration in seconds.

    Returns:
        Human-readable duration string (e.g., "1h 23m").
    """
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}m"


def _get_period_display(period: str, period_start: str | None) -> str:
    """Get display string for the time period.

    Args:
        period: Period name (today, week, month, all).
        period_start: ISO format start date.

    Returns:
        Human-readable period description.
    """
    if period == "all":
        if period_start:
            try:
                start_date = datetime.fromisoformat(period_start)
                return f"All Time (since {start_date.strftime('%Y-%m-%d')})"
            except ValueError:
                pass
        return "All Time"
    elif period == "today":
        return f"Today ({datetime.now().strftime('%Y-%m-%d')})"
    elif period == "week":
        return "This Week"
    elif period == "month":
        return f"This Month ({datetime.now().strftime('%B %Y')})"
    return period.capitalize()


class StatisticsReporter:
    """Reporter for conversion statistics.

    Generates formatted reports for conversion statistics including
    totals, averages, and storage savings information.
    """

    BOX_WIDTH = 48

    def format_summary(self, stats: HistoryStatistics) -> str:
        """Format a summary of conversion statistics.

        Args:
            stats: Statistics to format.

        Returns:
            Formatted summary string with box drawing.
        """
        lines = []
        w = self.BOX_WIDTH

        # Top border
        lines.append(f"\u256d{'─' * w}\u256e")
        lines.append(f"│{'Conversion Statistics':^{w}}│")
        lines.append(f"├{'─' * w}┤")

        # Period info
        period_display = _get_period_display(stats.period, stats.first_conversion)
        lines.append(f"│  Period: {period_display:<{w - 11}}│")
        lines.append(f"├{'─' * w}┤")

        # Video counts
        lines.append(f"│  Videos Converted:     {stats.total_converted:<{w - 26}}│")
        lines.append(f"│  Success Rate:         {stats.success_rate * 100:.1f}%{' ' * (w - 31)}│")

        # Storage info
        original_str = _format_size(stats.total_source_bytes)
        converted_str = _format_size(stats.total_output_bytes)
        saved_str = _format_size(stats.total_saved_bytes)
        saved_pct = stats.storage_saved_percent

        lines.append(f"│  Total Original:       {original_str:<{w - 26}}│")
        lines.append(f"│  Total Converted:      {converted_str:<{w - 26}}│")
        lines.append(
            f"│  Storage Saved:        {saved_str} ({saved_pct:.1f}%){' ' * (w - 38 - len(saved_str))}│"
        )
        lines.append(f"├{'─' * w}┤")

        # Compression info
        compression_pct = stats.average_compression_ratio * 100
        lines.append(f"│  Average Compression:  {compression_pct:.1f}%{' ' * (w - 29)}│")

        # Time info if available
        if stats.total_duration_seconds > 0:
            duration_str = _format_duration(stats.total_duration_seconds)
            lines.append(f"│  Total Time:           {duration_str:<{w - 26}}│")

        # Bottom border
        lines.append(f"\u2570{'─' * w}\u256f")

        return "\n".join(lines)

    def format_compact(self, stats: HistoryStatistics) -> str:
        """Format a compact one-line summary.

        Args:
            stats: Statistics to format.

        Returns:
            Compact summary string.
        """
        saved_str = _format_size(stats.total_saved_bytes)
        return (
            f"{stats.total_converted} videos converted, "
            f"{stats.success_rate * 100:.1f}% success, "
            f"{saved_str} saved ({stats.storage_saved_percent:.1f}%)"
        )

    def format_detailed(
        self,
        stats: HistoryStatistics,
        records: list | None = None,
    ) -> str:
        """Format detailed statistics with optional record list.

        Args:
            stats: Statistics to format.
            records: Optional list of individual records.

        Returns:
            Detailed formatted string.
        """
        lines = [self.format_summary(stats)]

        if records:
            lines.append("")
            lines.append("-" * 60)
            lines.append("                  Recent Conversions")
            lines.append("-" * 60)

            for record in records[-10:]:  # Last 10 records
                status = "OK" if record.success else "FAILED"
                filename = Path(record.source_path).name
                if len(filename) > 35:
                    filename = filename[:32] + "..."
                lines.append(f"  [{status:6s}] {filename}")
                if record.success:
                    original = _format_size(record.source_size)
                    converted = _format_size(record.output_size or 0)
                    ratio = record.compression_ratio * 100
                    lines.append(f"           {original} -> {converted} ({ratio:.1f}% saved)")

            lines.append("-" * 60)

        return "\n".join(lines)

    def to_dict(self, stats: HistoryStatistics) -> dict:
        """Convert statistics to dictionary for JSON export.

        Args:
            stats: Statistics to convert.

        Returns:
            Dictionary representation of statistics.
        """
        return stats.to_dict()

    def export_json(
        self,
        stats: HistoryStatistics,
        output_path: Path,
        records: list | None = None,
    ) -> None:
        """Export statistics to JSON file.

        Args:
            stats: Statistics to export.
            output_path: Path for the JSON file.
            records: Optional list of records to include.
        """
        data = {
            "exported_at": datetime.now().isoformat(),
            "statistics": self.to_dict(stats),
        }

        if records:
            data["records"] = [
                {
                    "id": r.id,
                    "source_path": r.source_path,
                    "output_path": r.output_path,
                    "source_size": r.source_size,
                    "output_size": r.output_size,
                    "compression_ratio": r.compression_ratio,
                    "converted_at": r.converted_at,
                    "success": r.success,
                }
                for r in records
            ]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    def export_csv(
        self,
        stats: HistoryStatistics,
        output_path: Path,
        records: list | None = None,
    ) -> None:
        """Export statistics to CSV file.

        Args:
            stats: Statistics to export (used for header comment).
            output_path: Path for the CSV file.
            records: List of records to export.
        """
        import csv

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            # Write summary as comment
            f.write("# Video Converter Statistics Export\n")
            f.write(f"# Period: {stats.period}\n")
            f.write(f"# Total Converted: {stats.total_converted}\n")
            f.write(f"# Storage Saved: {_format_size(stats.total_saved_bytes)}\n")
            f.write(f"# Exported: {datetime.now().isoformat()}\n")
            f.write("#\n")

            if records:
                fieldnames = [
                    "id",
                    "source_path",
                    "output_path",
                    "source_codec",
                    "output_codec",
                    "source_size",
                    "output_size",
                    "size_saved",
                    "compression_ratio",
                    "converted_at",
                    "success",
                    "error_message",
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for record in records:
                    row = {
                        "id": record.id,
                        "source_path": record.source_path,
                        "output_path": record.output_path,
                        "source_codec": record.source_codec,
                        "output_codec": record.output_codec,
                        "source_size": record.source_size,
                        "output_size": record.output_size,
                        "size_saved": record.size_saved,
                        "compression_ratio": f"{record.compression_ratio:.2%}",
                        "converted_at": record.converted_at,
                        "success": record.success,
                        "error_message": record.error_message or "",
                    }
                    writer.writerow(row)

    def print_summary(
        self,
        stats: HistoryStatistics,
        stream: TextIO | None = None,
    ) -> None:
        """Print statistics summary to stdout or a stream.

        Args:
            stats: Statistics to print.
            stream: Output stream. Uses stdout if None.
        """
        import sys

        output = stream or sys.stdout
        output.write(self.format_summary(stats))
        output.write("\n")


__all__ = ["StatisticsReporter"]
