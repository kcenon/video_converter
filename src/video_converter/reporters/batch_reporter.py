"""Batch conversion reporter for generating completion reports.

This module provides a reporter class that generates formatted output
for batch conversion results.

SDS Reference: SDS-C01-004
SRS Reference: SRS-602 (Batch Processing)

Example:
    >>> from video_converter.reporters.batch_reporter import BatchReporter
    >>> from video_converter.core.types import ConversionReport
    >>>
    >>> reporter = BatchReporter()
    >>> report = ConversionReport(...)
    >>> print(reporter.format_summary(report))
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TextIO

from video_converter.core.types import ConversionReport, ConversionResult


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
        Human-readable duration string (e.g., "1h 23m 45s").
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}m"


class BatchReporter:
    """Reporter for batch conversion results.

    Generates formatted reports for batch conversions including
    summary statistics, individual file results, and error details.
    """

    def format_summary(self, report: ConversionReport) -> str:
        """Format a summary of the batch conversion.

        Args:
            report: Conversion report to format.

        Returns:
            Formatted summary string.
        """
        lines = []
        lines.append("=" * 50)
        lines.append("         Batch Conversion Report")
        lines.append("=" * 50)
        lines.append("")

        # Session info
        lines.append(f"Session ID:   {report.session_id}")
        if report.started_at:
            lines.append(f"Started:      {report.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if report.completed_at:
            lines.append(f"Completed:    {report.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if report.started_at:
                duration = (report.completed_at - report.started_at).total_seconds()
                lines.append(f"Duration:     {_format_duration(duration)}")

        lines.append("")
        lines.append("-" * 50)
        lines.append("                 Summary")
        lines.append("-" * 50)

        # Statistics
        lines.append(f"Total files:      {report.total_files}")
        lines.append(f"Successful:       {report.successful}")
        lines.append(f"Failed:           {report.failed}")
        lines.append(f"Skipped:          {report.skipped}")

        if report.cancelled:
            lines.append("Status:           CANCELLED")
        elif report.failed == 0:
            lines.append("Status:           SUCCESS")
        elif report.successful > 0:
            lines.append("Status:           PARTIAL SUCCESS")
        else:
            lines.append("Status:           FAILED")

        # Size statistics
        if report.total_original_size > 0:
            lines.append("")
            lines.append("-" * 50)
            lines.append("              Storage Savings")
            lines.append("-" * 50)
            lines.append(f"Original size:    {_format_size(report.total_original_size)}")
            lines.append(f"Converted size:   {_format_size(report.total_converted_size)}")
            lines.append(f"Space saved:      {_format_size(report.total_size_saved)}")
            lines.append(f"Compression:      {report.average_compression_ratio:.1%}")

        # Errors
        if report.errors:
            lines.append("")
            lines.append("-" * 50)
            lines.append("                 Errors")
            lines.append("-" * 50)
            for error in report.errors[:10]:  # Limit to first 10
                lines.append(f"  - {error}")
            if len(report.errors) > 10:
                lines.append(f"  ... and {len(report.errors) - 10} more errors")

        # Warnings
        if report.warnings:
            lines.append("")
            lines.append("-" * 50)
            lines.append("                Warnings")
            lines.append("-" * 50)
            for warning in report.warnings[:5]:  # Limit to first 5
                lines.append(f"  - {warning}")
            if len(report.warnings) > 5:
                lines.append(f"  ... and {len(report.warnings) - 5} more warnings")

        lines.append("")
        lines.append("=" * 50)

        return "\n".join(lines)

    def format_details(self, report: ConversionReport) -> str:
        """Format detailed results for each file.

        Args:
            report: Conversion report to format.

        Returns:
            Formatted details string.
        """
        lines = []
        lines.append("-" * 60)
        lines.append("                  File Details")
        lines.append("-" * 60)

        for i, result in enumerate(report.results, 1):
            status = "OK" if result.success else "FAILED"
            filename = result.request.input_path.name

            lines.append(f"[{i:3d}] {status:6s} {filename}")

            if result.success:
                lines.append(
                    f"      {_format_size(result.original_size)} -> "
                    f"{_format_size(result.converted_size)} "
                    f"({result.compression_ratio:.1%} saved)"
                )
            else:
                lines.append(f"      Error: {result.error_message}")

        lines.append("-" * 60)

        return "\n".join(lines)

    def write_report(
        self,
        report: ConversionReport,
        output_path: Path,
        include_details: bool = True,
    ) -> None:
        """Write report to a file.

        Args:
            report: Conversion report to write.
            output_path: Path for the report file.
            include_details: Whether to include per-file details.
        """
        content = self.format_summary(report)
        if include_details and report.results:
            content += "\n" + self.format_details(report)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            f.write(content)

    def print_report(
        self,
        report: ConversionReport,
        stream: TextIO | None = None,
        include_details: bool = False,
    ) -> None:
        """Print report to stdout or a stream.

        Args:
            report: Conversion report to print.
            stream: Output stream. Uses stdout if None.
            include_details: Whether to include per-file details.
        """
        import sys

        output = stream or sys.stdout

        output.write(self.format_summary(report))
        output.write("\n")

        if include_details and report.results:
            output.write(self.format_details(report))
            output.write("\n")

    def to_dict(self, report: ConversionReport) -> dict:
        """Convert report to dictionary for JSON export.

        Args:
            report: Conversion report to convert.

        Returns:
            Dictionary representation of the report.
        """
        return {
            "session_id": report.session_id,
            "started_at": report.started_at.isoformat() if report.started_at else None,
            "completed_at": report.completed_at.isoformat() if report.completed_at else None,
            "duration_seconds": (
                (report.completed_at - report.started_at).total_seconds()
                if report.started_at and report.completed_at
                else None
            ),
            "total_files": report.total_files,
            "successful": report.successful,
            "failed": report.failed,
            "skipped": report.skipped,
            "cancelled": report.cancelled,
            "total_original_size": report.total_original_size,
            "total_converted_size": report.total_converted_size,
            "total_size_saved": report.total_size_saved,
            "compression_ratio": report.average_compression_ratio,
            "success_rate": report.success_rate,
            "errors": report.errors,
            "warnings": report.warnings,
            "results": [
                {
                    "input": str(r.request.input_path),
                    "output": str(r.request.output_path),
                    "success": r.success,
                    "original_size": r.original_size,
                    "converted_size": r.converted_size,
                    "compression_ratio": r.compression_ratio,
                    "error": r.error_message,
                }
                for r in report.results
            ],
        }


__all__ = ["BatchReporter"]
