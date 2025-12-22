"""Rich-based progress display components for video conversion.

This module provides beautiful, informative progress displays using the Rich library,
including single file progress bars, batch progress with overall and per-file tracking,
and spinners for indeterminate operations.

SDS Reference: SDS-U01-001
SRS Reference: SRS-801 (Progress Display)

Example:
    >>> from video_converter.ui.progress import ProgressDisplayManager
    >>>
    >>> with ProgressDisplayManager(quiet=False) as manager:
    ...     progress = manager.create_single_file_progress(
    ...         filename="vacation_2024.mp4",
    ...         original_size=1_500_000_000,
    ...     )
    ...     progress.start()
    ...     # During conversion, call:
    ...     progress.update(percentage=42.0, current_size=630_000_000, eta="1:45", speed=4.2)
    ...     progress.finish()
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    Task,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from collections.abc import Generator

    from video_converter.converters.progress import ProgressInfo


class SizeProgressColumn(ProgressColumn):
    """Custom column showing size progress (current -> target).

    Displays the current output size with an arrow indicating the conversion direction.
    Format: "630 MB -> ?" during conversion, or "630 MB -> 270 MB" when estimated.
    """

    def render(self, task: Task) -> Text:
        """Render the size progress column.

        Args:
            task: The progress task to render.

        Returns:
            Formatted text showing size progress.
        """
        current_size = task.fields.get("current_size", "0 B")
        original_size = task.fields.get("original_size", "")
        if original_size:
            return Text(f"{original_size} -> {current_size}", style="cyan")
        return Text(f"-> {current_size}", style="cyan")


class SpeedColumn(ProgressColumn):
    """Custom column showing encoding speed relative to realtime.

    Format: "4.2x" meaning 4.2 times faster than realtime playback.
    """

    def render(self, task: Task) -> Text:
        """Render the speed column.

        Args:
            task: The progress task to render.

        Returns:
            Formatted text showing encoding speed.
        """
        speed = task.fields.get("speed", 0.0)
        if speed > 0:
            return Text(f"{speed:.1f}x", style="green")
        return Text("--", style="dim")


class ETAColumn(ProgressColumn):
    """Custom column showing estimated time of arrival.

    Format: "ETA: 1:45" or "ETA: calculating..."
    """

    def render(self, task: Task) -> Text:
        """Render the ETA column.

        Args:
            task: The progress task to render.

        Returns:
            Formatted text showing ETA.
        """
        eta = task.fields.get("eta", "calculating...")
        return Text(f"ETA: {eta}", style="yellow")


@dataclass
class SingleFileProgressDisplay:
    """Progress display for single file conversion.

    Provides a beautiful progress bar with real-time statistics including
    file size, encoding speed, and ETA.

    Example display:
        Converting vacation_2024.mp4
        [################............] 42% | 1.5 GB -> 630 MB | ETA: 1:45 | 4.2x

    Attributes:
        filename: Name of the file being converted.
        original_size: Original file size in bytes.
        console: Rich console for output.
        progress: Rich Progress instance.
        task_id: ID of the progress task.
    """

    filename: str
    original_size: int = 0
    console: Console = field(default_factory=Console)
    _progress: Progress | None = field(default=None, init=False, repr=False)
    _task_id: int | None = field(default=None, init=False, repr=False)
    _live: Live | None = field(default=None, init=False, repr=False)

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format.

        Args:
            size_bytes: Size in bytes.

        Returns:
            Formatted size string like "1.50 GB" or "680 MB".
        """
        if size_bytes <= 0:
            return "0 B"
        size = float(size_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if abs(size) < 1024.0:
                if unit in ("B", "KB"):
                    return f"{int(size)} {unit}"
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def start(self) -> None:
        """Start the progress display."""
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}[/bold blue]"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TextColumn("[dim]|[/dim]"),
            SizeProgressColumn(),
            TextColumn("[dim]|[/dim]"),
            ETAColumn(),
            TextColumn("[dim]|[/dim]"),
            SpeedColumn(),
            console=self.console,
            expand=False,
        )
        self._progress.start()

        original_formatted = self._format_size(self.original_size)
        self._task_id = self._progress.add_task(
            f"Converting {self.filename}",
            total=100,
            current_size="0 B",
            original_size=original_formatted,
            eta="calculating...",
            speed=0.0,
        )

    def update(
        self,
        percentage: float = 0.0,
        current_size: int = 0,
        eta: str = "calculating...",
        speed: float = 0.0,
    ) -> None:
        """Update the progress display.

        Args:
            percentage: Completion percentage (0-100).
            current_size: Current output file size in bytes.
            eta: Estimated time remaining string.
            speed: Encoding speed multiplier.
        """
        if self._progress is None or self._task_id is None:
            return

        self._progress.update(
            self._task_id,
            completed=percentage,
            current_size=self._format_size(current_size),
            eta=eta,
            speed=speed,
        )

    def update_from_info(self, info: ProgressInfo) -> None:
        """Update the progress display from ProgressInfo.

        Args:
            info: ProgressInfo object from the converter.
        """
        self.update(
            percentage=info.percentage,
            current_size=info.current_size,
            eta=info.eta_formatted,
            speed=info.speed,
        )

    def finish(self) -> None:
        """Stop the progress display."""
        if self._progress is not None:
            self._progress.stop()
            self._progress = None


@dataclass
class BatchProgressDisplay:
    """Progress display for batch file conversion.

    Shows both overall progress and per-file progress with accumulated statistics.

    Example display:
        Converting vacation_2024.mp4 (1 of 15)
        [################............] 42% | 630 MB -> 270 MB | ETA: 1:45 | 4.2x

        Overall Progress: 5/15 videos | 3.2 GB saved
        [########....................] 33% | ETA: 12:30

    Attributes:
        total_files: Total number of files to convert.
        console: Rich console for output.
    """

    total_files: int
    console: Console = field(default_factory=Console)
    _overall_progress: Progress | None = field(default=None, init=False, repr=False)
    _file_progress: Progress | None = field(default=None, init=False, repr=False)
    _overall_task_id: int | None = field(default=None, init=False, repr=False)
    _file_task_id: int | None = field(default=None, init=False, repr=False)
    _live: Live | None = field(default=None, init=False, repr=False)
    _completed_count: int = field(default=0, init=False, repr=False)
    _total_saved_bytes: int = field(default=0, init=False, repr=False)

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes <= 0:
            return "0 B"
        size = float(size_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if abs(size) < 1024.0:
                if unit in ("B", "KB"):
                    return f"{int(size)} {unit}"
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def start(self) -> None:
        """Start the batch progress display."""
        # Per-file progress bar
        self._file_progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}[/bold blue]"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TextColumn("[dim]|[/dim]"),
            SizeProgressColumn(),
            TextColumn("[dim]|[/dim]"),
            ETAColumn(),
            TextColumn("[dim]|[/dim]"),
            SpeedColumn(),
            console=self.console,
            expand=False,
        )

        # Overall progress bar
        self._overall_progress = Progress(
            TextColumn("[bold]{task.description}[/bold]"),
            BarColumn(bar_width=40),
            MofNCompleteColumn(),
            TextColumn("[dim]|[/dim]"),
            TextColumn("[green]{task.fields[saved]}[/green]"),
            TextColumn("[dim]|[/dim]"),
            TimeRemainingColumn(),
            console=self.console,
            expand=False,
        )

        self._file_task_id = self._file_progress.add_task(
            "Waiting...",
            total=100,
            current_size="0 B",
            original_size="",
            eta="--",
            speed=0.0,
        )

        self._overall_task_id = self._overall_progress.add_task(
            "Overall Progress",
            total=self.total_files,
            saved="0 B saved",
        )

        # Create combined display
        progress_group = Group(
            self._file_progress,
            Text(""),  # Empty line separator
            self._overall_progress,
        )

        self._live = Live(
            progress_group,
            console=self.console,
            refresh_per_second=10,
        )
        self._live.start()

    def start_file(
        self,
        filename: str,
        file_index: int,
        original_size: int = 0,
    ) -> None:
        """Start tracking a new file.

        Args:
            filename: Name of the file being converted.
            file_index: 1-based index of the current file.
            original_size: Original file size in bytes.
        """
        if self._file_progress is None or self._file_task_id is None:
            return

        original_formatted = self._format_size(original_size)
        self._file_progress.update(
            self._file_task_id,
            description=f"Converting {filename} ({file_index} of {self.total_files})",
            completed=0,
            current_size="0 B",
            original_size=original_formatted,
            eta="calculating...",
            speed=0.0,
        )

    def update_file(
        self,
        percentage: float = 0.0,
        current_size: int = 0,
        eta: str = "calculating...",
        speed: float = 0.0,
    ) -> None:
        """Update the current file's progress.

        Args:
            percentage: Completion percentage (0-100).
            current_size: Current output file size in bytes.
            eta: Estimated time remaining string.
            speed: Encoding speed multiplier.
        """
        if self._file_progress is None or self._file_task_id is None:
            return

        self._file_progress.update(
            self._file_task_id,
            completed=percentage,
            current_size=self._format_size(current_size),
            eta=eta,
            speed=speed,
        )

    def update_file_from_info(self, info: ProgressInfo) -> None:
        """Update the current file progress from ProgressInfo.

        Args:
            info: ProgressInfo object from the converter.
        """
        self.update_file(
            percentage=info.percentage,
            current_size=info.current_size,
            eta=info.eta_formatted,
            speed=info.speed,
        )

    def complete_file(self, saved_bytes: int = 0) -> None:
        """Mark the current file as complete.

        Args:
            saved_bytes: Bytes saved by this file's conversion.
        """
        self._completed_count += 1
        self._total_saved_bytes += saved_bytes

        if self._overall_progress is None or self._overall_task_id is None:
            return

        self._overall_progress.update(
            self._overall_task_id,
            completed=self._completed_count,
            saved=f"{self._format_size(self._total_saved_bytes)} saved",
        )

    def finish(self) -> None:
        """Stop the batch progress display."""
        if self._live is not None:
            self._live.stop()
            self._live = None

    @property
    def completed_count(self) -> int:
        """Get the number of completed files."""
        return self._completed_count

    @property
    def total_saved_bytes(self) -> int:
        """Get the total bytes saved so far."""
        return self._total_saved_bytes


@dataclass
class IndeterminateSpinner:
    """Spinner for indeterminate operations.

    Used for operations where progress cannot be measured, such as
    file analysis, metadata extraction, or initialization.

    Attributes:
        message: Message to display next to the spinner.
        console: Rich console for output.
    """

    message: str
    console: Console = field(default_factory=Console)
    _progress: Progress | None = field(default=None, init=False, repr=False)
    _task_id: int | None = field(default=None, init=False, repr=False)

    def start(self) -> None:
        """Start the spinner."""
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}[/bold blue]"),
            console=self.console,
            expand=False,
        )
        self._progress.start()
        self._task_id = self._progress.add_task(self.message, total=None)

    def update(self, message: str) -> None:
        """Update the spinner message.

        Args:
            message: New message to display.
        """
        if self._progress is not None and self._task_id is not None:
            self._progress.update(self._task_id, description=message)

    def finish(self, success_message: str | None = None) -> None:
        """Stop the spinner.

        Args:
            success_message: Optional message to print after stopping.
        """
        if self._progress is not None:
            self._progress.stop()
            self._progress = None

        if success_message:
            self.console.print(f"[green]{success_message}[/green]")


@dataclass
class ProgressDisplayManager:
    """Manager for progress displays with quiet mode support.

    Provides a unified interface for creating progress displays that
    respect the quiet mode setting.

    Attributes:
        quiet: If True, suppress all progress output.
        console: Rich console for output.
    """

    quiet: bool = False
    console: Console = field(default_factory=Console)

    def create_single_file_progress(
        self,
        filename: str,
        original_size: int = 0,
    ) -> SingleFileProgressDisplay | _NullProgress:
        """Create a single file progress display.

        Args:
            filename: Name of the file being converted.
            original_size: Original file size in bytes.

        Returns:
            A progress display, or a null object if quiet mode is enabled.
        """
        if self.quiet:
            return _NullProgress()
        return SingleFileProgressDisplay(
            filename=filename,
            original_size=original_size,
            console=self.console,
        )

    def create_batch_progress(
        self,
        total_files: int,
    ) -> BatchProgressDisplay | _NullBatchProgress:
        """Create a batch progress display.

        Args:
            total_files: Total number of files to convert.

        Returns:
            A batch progress display, or a null object if quiet mode is enabled.
        """
        if self.quiet:
            return _NullBatchProgress()
        return BatchProgressDisplay(
            total_files=total_files,
            console=self.console,
        )

    def create_spinner(
        self,
        message: str,
    ) -> IndeterminateSpinner | _NullSpinner:
        """Create an indeterminate spinner.

        Args:
            message: Message to display next to the spinner.

        Returns:
            A spinner, or a null object if quiet mode is enabled.
        """
        if self.quiet:
            return _NullSpinner()
        return IndeterminateSpinner(
            message=message,
            console=self.console,
        )

    @contextmanager
    def spinner(self, message: str) -> Generator[IndeterminateSpinner | _NullSpinner]:
        """Context manager for indeterminate spinner.

        Args:
            message: Message to display next to the spinner.

        Yields:
            A spinner that is automatically started and stopped.
        """
        spinner = self.create_spinner(message)
        spinner.start()
        try:
            yield spinner
        finally:
            spinner.finish()


@dataclass
class _NullProgress:
    """Null object pattern for SingleFileProgressDisplay when quiet mode is enabled."""

    def start(self) -> None:
        """No-op."""

    def update(
        self,
        percentage: float = 0.0,
        current_size: int = 0,
        eta: str = "",
        speed: float = 0.0,
    ) -> None:
        """No-op."""

    def update_from_info(self, info: ProgressInfo) -> None:
        """No-op."""

    def finish(self) -> None:
        """No-op."""


@dataclass
class _NullBatchProgress:
    """Null object pattern for BatchProgressDisplay when quiet mode is enabled."""

    _completed_count: int = field(default=0, init=False)
    _total_saved_bytes: int = field(default=0, init=False)

    def start(self) -> None:
        """No-op."""

    def start_file(
        self,
        filename: str,
        file_index: int,
        original_size: int = 0,
    ) -> None:
        """No-op."""

    def update_file(
        self,
        percentage: float = 0.0,
        current_size: int = 0,
        eta: str = "",
        speed: float = 0.0,
    ) -> None:
        """No-op."""

    def update_file_from_info(self, info: ProgressInfo) -> None:
        """No-op."""

    def complete_file(self, saved_bytes: int = 0) -> None:
        """Track completion even in quiet mode."""
        self._completed_count += 1
        self._total_saved_bytes += saved_bytes

    def finish(self) -> None:
        """No-op."""

    @property
    def completed_count(self) -> int:
        """Get the number of completed files."""
        return self._completed_count

    @property
    def total_saved_bytes(self) -> int:
        """Get the total bytes saved so far."""
        return self._total_saved_bytes


@dataclass
class _NullSpinner:
    """Null object pattern for IndeterminateSpinner when quiet mode is enabled."""

    def start(self) -> None:
        """No-op."""

    def update(self, message: str) -> None:
        """No-op."""

    def finish(self, success_message: str | None = None) -> None:
        """No-op."""
