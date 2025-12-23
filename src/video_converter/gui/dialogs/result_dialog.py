"""Conversion result dialog for the Video Converter GUI.

This module provides the ConversionResultDialog for displaying
conversion results and statistics.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from video_converter.core.types import ConversionResult


class ConversionResultDialog(QDialog):
    """Dialog for displaying conversion results.

    Shows a summary of the conversion including:
    - Success/failure status
    - Original and converted file sizes
    - Space saved and compression ratio
    - Duration and speed statistics
    - VMAF quality score (if available)
    """

    def __init__(
        self,
        result: ConversionResult,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the result dialog.

        Args:
            result: ConversionResult from the conversion.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._result = result
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("Conversion Complete")
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header with status icon
        self._setup_header(layout)

        # Statistics
        self._setup_statistics(layout)

        # Warnings if any
        if self._result.warnings:
            self._setup_warnings(layout)

        # Actions
        self._setup_actions(layout)

    def _setup_header(self, parent_layout: QVBoxLayout) -> None:
        """Set up the header section.

        Args:
            parent_layout: Parent layout.
        """
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Status icon
        if self._result.success:
            icon_label = QLabel("✅")
            status_text = "Conversion Successful"
        else:
            icon_label = QLabel("❌")
            status_text = "Conversion Failed"

        icon_label.setObjectName("resultIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 48px;")
        header_layout.addWidget(icon_label)

        # Status text
        status_label = QLabel(status_text)
        status_label.setObjectName("resultStatus")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setStyleSheet("font-size: 18px; font-weight: 600;")
        header_layout.addWidget(status_label)

        # File name
        file_name = self._result.request.input_path.name
        file_label = QLabel(file_name)
        file_label.setObjectName("resultFileName")
        file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        file_label.setStyleSheet("font-size: 13px; color: #86868b;")
        header_layout.addWidget(file_label)

        parent_layout.addLayout(header_layout)

    def _setup_statistics(self, parent_layout: QVBoxLayout) -> None:
        """Set up the statistics section.

        Args:
            parent_layout: Parent layout.
        """
        stats_frame = QFrame()
        stats_frame.setObjectName("statsFrame")
        stats_layout = QVBoxLayout(stats_frame)
        stats_layout.setContentsMargins(16, 16, 16, 16)
        stats_layout.setSpacing(12)

        if self._result.success:
            # Size comparison
            original_size = self._format_size(self._result.original_size)
            converted_size = self._format_size(self._result.converted_size)
            saved_size = self._format_size(self._result.size_saved)
            ratio = self._result.compression_ratio * 100

            self._add_stat_row(stats_layout, "Original Size", original_size)
            self._add_stat_row(stats_layout, "Converted Size", converted_size)
            self._add_stat_row(
                stats_layout,
                "Space Saved",
                f"{saved_size} ({ratio:.1f}%)",
                highlight=True,
            )

            # Duration
            if self._result.duration_seconds > 0:
                duration = self._format_duration(self._result.duration_seconds)
                self._add_stat_row(stats_layout, "Duration", duration)

            # Speed ratio
            if self._result.speed_ratio > 0:
                speed = f"{self._result.speed_ratio:.1f}x realtime"
                self._add_stat_row(stats_layout, "Speed", speed)

            # VMAF score if available
            if self._result.vmaf_score is not None:
                vmaf_text = f"{self._result.vmaf_score:.1f}"
                if self._result.vmaf_quality_level:
                    vmaf_text += f" ({self._result.vmaf_quality_level})"
                self._add_stat_row(stats_layout, "Quality (VMAF)", vmaf_text)

            # Output path
            if self._result.request.output_path:
                output_name = self._result.request.output_path.name
                self._add_stat_row(stats_layout, "Output File", output_name)

        else:
            # Error message
            error = self._result.error_message or "Unknown error"
            error_label = QLabel(error)
            error_label.setWordWrap(True)
            error_label.setStyleSheet("color: #ff453a;")
            stats_layout.addWidget(error_label)

        parent_layout.addWidget(stats_frame)

    def _setup_warnings(self, parent_layout: QVBoxLayout) -> None:
        """Set up the warnings section.

        Args:
            parent_layout: Parent layout.
        """
        warnings_frame = QFrame()
        warnings_frame.setObjectName("warningsFrame")
        warnings_layout = QVBoxLayout(warnings_frame)
        warnings_layout.setContentsMargins(16, 12, 16, 12)
        warnings_layout.setSpacing(8)

        header = QLabel("Warnings")
        header.setStyleSheet("font-weight: 600; color: #ff9500;")
        warnings_layout.addWidget(header)

        for warning in self._result.warnings[:5]:  # Limit to 5 warnings
            warning_label = QLabel(f"• {warning}")
            warning_label.setWordWrap(True)
            warning_label.setStyleSheet("font-size: 12px;")
            warnings_layout.addWidget(warning_label)

        if len(self._result.warnings) > 5:
            more_label = QLabel(f"... and {len(self._result.warnings) - 5} more")
            more_label.setStyleSheet("font-size: 12px; color: #86868b;")
            warnings_layout.addWidget(more_label)

        parent_layout.addWidget(warnings_frame)

    def _setup_actions(self, parent_layout: QVBoxLayout) -> None:
        """Set up the action buttons.

        Args:
            parent_layout: Parent layout.
        """
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        if self._result.success and self._result.request.output_path:
            # Show in Finder button
            show_button = QPushButton("Show in Finder")
            show_button.clicked.connect(self._on_show_in_finder)
            button_layout.addWidget(show_button)

        # Close button
        close_button = QPushButton("Close")
        close_button.setObjectName("primaryButton")
        close_button.clicked.connect(self.accept)
        close_button.setDefault(True)
        button_layout.addWidget(close_button)

        parent_layout.addLayout(button_layout)

    def _add_stat_row(
        self,
        layout: QVBoxLayout,
        label: str,
        value: str,
        highlight: bool = False,
    ) -> None:
        """Add a statistics row.

        Args:
            layout: Layout to add to.
            label: Label text.
            value: Value text.
            highlight: Whether to highlight this row.
        """
        row_layout = QHBoxLayout()

        label_widget = QLabel(label)
        label_widget.setStyleSheet("color: #86868b;")
        row_layout.addWidget(label_widget)

        row_layout.addStretch()

        value_widget = QLabel(value)
        if highlight:
            value_widget.setStyleSheet("font-weight: 600; color: #34c759;")
        else:
            value_widget.setStyleSheet("font-weight: 500;")
        row_layout.addWidget(value_widget)

        layout.addLayout(row_layout)

    def _on_show_in_finder(self) -> None:
        """Show the output file in Finder."""
        output_path = self._result.request.output_path
        if output_path and output_path.exists():
            import subprocess

            subprocess.run(["open", "-R", str(output_path)], check=False)

    def _format_size(self, size_bytes: int) -> str:
        """Format file size for display.

        Args:
            size_bytes: Size in bytes.

        Returns:
            Human-readable size string.
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    def _format_duration(self, seconds: float) -> str:
        """Format duration for display.

        Args:
            seconds: Duration in seconds.

        Returns:
            Human-readable duration string.
        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
