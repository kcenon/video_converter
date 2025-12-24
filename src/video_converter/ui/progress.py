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
    TaskID,
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
    _task_id: TaskID | None = field(default=None, init=False, repr=False)
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
    _overall_task_id: TaskID | None = field(default=None, init=False, repr=False)
    _file_task_id: TaskID | None = field(default=None, init=False, repr=False)
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
    _task_id: TaskID | None = field(default=None, init=False, repr=False)

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

    def create_photos_progress(
        self,
        total_videos: int,
        total_size: int = 0,
    ) -> PhotosProgressDisplay | _NullPhotosProgress:
        """Create a Photos library progress display.

        Args:
            total_videos: Total number of videos to convert.
            total_size: Total size of videos in bytes.

        Returns:
            A Photos progress display, or a null object if quiet mode is enabled.
        """
        if self.quiet:
            return _NullPhotosProgress()
        return PhotosProgressDisplay(
            total_videos=total_videos,
            total_size=total_size,
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
    def spinner(self, message: str) -> Generator[IndeterminateSpinner | _NullSpinner, None, None]:
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
class PhotosLibraryInfo:
    """Information about the Photos library for display.

    Attributes:
        library_path: Path to the Photos library.
        total_videos: Total number of H.264 videos found.
        total_size: Total size of H.264 videos in bytes.
        estimated_savings: Estimated storage savings in bytes.
    """

    library_path: str
    total_videos: int
    total_size: int
    estimated_savings: int


@dataclass
class PhotosProgressDisplay:
    """Progress display for Photos library conversion.

    Shows Photos-specific information during conversion including
    album names, video dates, and two-phase progress (export + convert).

    SDS Reference: SDS-U01-002
    SRS Reference: SRS-801 (Progress Display)

    Example display:
        ╭──────────────────────────────────────────────────────────────╮
        │ Photos Library Conversion                                     │
        ├──────────────────────────────────────────────────────────────┤
        │ Library: ~/Pictures/Photos Library.photoslibrary             │
        │ Found: 150 H.264 videos (45.2 GB)                            │
        │ Est. savings: ~22.6 GB                                        │
        ╰──────────────────────────────────────────────────────────────╯

        Overall Progress ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  15/150  10%

        Current: IMG_1234.MOV
        Album: Vacation 2024 | Date: 2024-07-15
        ├─ Export:  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  100%  ✓
        └─ Convert: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━            65%  2.1x  ETA: 00:45

    Attributes:
        total_videos: Total number of videos to convert.
        console: Rich console for output.
    """

    total_videos: int
    total_size: int = 0
    console: Console = field(default_factory=Console)
    _overall_progress: Progress | None = field(default=None, init=False, repr=False)
    _export_progress: Progress | None = field(default=None, init=False, repr=False)
    _convert_progress: Progress | None = field(default=None, init=False, repr=False)
    _overall_task_id: TaskID | None = field(default=None, init=False, repr=False)
    _export_task_id: TaskID | None = field(default=None, init=False, repr=False)
    _convert_task_id: TaskID | None = field(default=None, init=False, repr=False)
    _live: Live | None = field(default=None, init=False, repr=False)
    _completed_count: int = field(default=0, init=False, repr=False)
    _failed_count: int = field(default=0, init=False, repr=False)
    _total_saved_bytes: int = field(default=0, init=False, repr=False)
    _current_video_info: Table | None = field(default=None, init=False, repr=False)
    _library_info: PhotosLibraryInfo | None = field(default=None, init=False, repr=False)

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

    def show_library_info(self, info: PhotosLibraryInfo) -> None:
        """Display Photos library information panel.

        Args:
            info: Library information to display.
        """
        self._library_info = info

        # Truncate library path for display
        lib_path = info.library_path
        if len(lib_path) > 50:
            lib_path = "~" + lib_path[lib_path.rfind("/Pictures") :]

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Label", style="dim")
        table.add_column("Value", style="bold")

        table.add_row("Library:", lib_path)
        table.add_row(
            "Found:",
            f"{info.total_videos} H.264 videos ({self._format_size(info.total_size)})",
        )
        table.add_row(
            "Est. savings:",
            f"~{self._format_size(info.estimated_savings)}",
        )

        panel = Panel(
            table,
            title="[bold blue]Photos Library Conversion[/bold blue]",
            border_style="blue",
        )
        self.console.print(panel)
        self.console.print()

    def start(self) -> None:
        """Start the Photos progress display."""
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

        # Export progress bar (simpler)
        self._export_progress = Progress(
            TextColumn("  [dim]├─[/dim] Export:  "),
            BarColumn(bar_width=30),
            TaskProgressColumn(),
            TextColumn("{task.fields[status]}"),
            console=self.console,
            expand=False,
        )

        # Convert progress bar (with speed and ETA)
        self._convert_progress = Progress(
            TextColumn("  [dim]└─[/dim] Convert: "),
            BarColumn(bar_width=30),
            TaskProgressColumn(),
            TextColumn("[dim]|[/dim]"),
            SpeedColumn(),
            TextColumn("[dim]|[/dim]"),
            ETAColumn(),
            console=self.console,
            expand=False,
        )

        # Create current video info table (will be updated per video)
        self._current_video_info = Table(show_header=False, box=None, padding=(0, 1))
        self._current_video_info.add_column("Label", style="dim")
        self._current_video_info.add_column("Value")
        self._current_video_info.add_row("Current:", "[dim]Waiting...[/dim]")
        self._current_video_info.add_row("Album:", "[dim]-[/dim]")

        # Initialize tasks
        self._overall_task_id = self._overall_progress.add_task(
            "Overall Progress",
            total=self.total_videos,
            saved="0 B saved",
        )

        self._export_task_id = self._export_progress.add_task(
            "export",
            total=100,
            status="",
        )

        self._convert_task_id = self._convert_progress.add_task(
            "convert",
            total=100,
            eta="--",
            speed=0.0,
        )

        # Create combined display
        progress_group = Group(
            self._overall_progress,
            Text(""),  # Empty line separator
            self._current_video_info,
            self._export_progress,
            self._convert_progress,
        )

        self._live = Live(
            progress_group,
            console=self.console,
            refresh_per_second=10,
        )
        self._live.start()

    def start_video(
        self,
        filename: str,
        video_index: int,
        album: str | None = None,
        date: str | None = None,
        original_size: int = 0,
    ) -> None:
        """Start tracking a new video.

        Args:
            filename: Name of the video file.
            video_index: 1-based index of the current video.
            album: Album name (first album if multiple).
            date: Date string (formatted as YYYY-MM-DD).
            original_size: Original file size in bytes.
        """
        # Update video info table
        self._current_video_info = Table(show_header=False, box=None, padding=(0, 1))
        self._current_video_info.add_column("Label", style="dim")
        self._current_video_info.add_column("Value")

        # Truncate filename if too long
        display_name = filename[:40] + "..." if len(filename) > 40 else filename
        self._current_video_info.add_row(
            "Current:",
            f"[bold cyan]{display_name}[/bold cyan] ({video_index}/{self.total_videos})",
        )

        # Format album and date info
        info_parts = []
        if album:
            info_parts.append(f"Album: [yellow]{album}[/yellow]")
        if date:
            info_parts.append(f"Date: [blue]{date}[/blue]")
        if original_size > 0:
            info_parts.append(f"Size: [green]{self._format_size(original_size)}[/green]")

        info_str = " | ".join(info_parts) if info_parts else "-"
        self._current_video_info.add_row("Info:", info_str)

        # Reset progress bars
        if self._export_progress and self._export_task_id is not None:
            self._export_progress.update(
                self._export_task_id,
                completed=0,
                status="",
            )

        if self._convert_progress and self._convert_task_id is not None:
            self._convert_progress.update(
                self._convert_task_id,
                completed=0,
                eta="calculating...",
                speed=0.0,
            )

        # Update live display
        self._refresh_display()

    def update_export_progress(self, percentage: float) -> None:
        """Update export progress.

        Args:
            percentage: Export completion percentage (0-100).
        """
        if self._export_progress is None or self._export_task_id is None:
            return

        status = "[green]✓[/green]" if percentage >= 100 else ""
        self._export_progress.update(
            self._export_task_id,
            completed=percentage,
            status=status,
        )

    def update_convert_progress(
        self,
        percentage: float = 0.0,
        speed: float = 0.0,
        eta: str = "calculating...",
    ) -> None:
        """Update conversion progress.

        Args:
            percentage: Conversion completion percentage (0-100).
            speed: Encoding speed multiplier.
            eta: Estimated time remaining string.
        """
        if self._convert_progress is None or self._convert_task_id is None:
            return

        self._convert_progress.update(
            self._convert_task_id,
            completed=percentage,
            speed=speed,
            eta=eta,
        )

    def update_convert_from_info(self, info: ProgressInfo) -> None:
        """Update conversion progress from ProgressInfo.

        Args:
            info: ProgressInfo object from the converter.
        """
        self.update_convert_progress(
            percentage=info.percentage,
            speed=info.speed,
            eta=info.eta_formatted,
        )

    def complete_video(self, success: bool, saved_bytes: int = 0) -> None:
        """Mark the current video as complete.

        Args:
            success: Whether conversion was successful.
            saved_bytes: Bytes saved by this conversion.
        """
        if success:
            self._completed_count += 1
            self._total_saved_bytes += saved_bytes
        else:
            self._failed_count += 1

        if self._overall_progress is None or self._overall_task_id is None:
            return

        self._overall_progress.update(
            self._overall_task_id,
            completed=self._completed_count + self._failed_count,
            saved=f"{self._format_size(self._total_saved_bytes)} saved",
        )

    def _refresh_display(self) -> None:
        """Refresh the live display with updated components."""
        if (
            self._live is None
            or self._overall_progress is None
            or self._current_video_info is None
            or self._export_progress is None
            or self._convert_progress is None
        ):
            return

        progress_group = Group(
            self._overall_progress,
            Text(""),
            self._current_video_info,
            self._export_progress,
            self._convert_progress,
        )
        self._live.update(progress_group)

    def finish(self) -> None:
        """Stop the Photos progress display."""
        if self._live is not None:
            self._live.stop()
            self._live = None

    def show_summary(
        self,
        successful: int,
        failed: int,
        total_saved: int,
        elapsed_time: float,
    ) -> None:
        """Display conversion summary.

        Args:
            successful: Number of successful conversions.
            failed: Number of failed conversions.
            total_saved: Total bytes saved.
            elapsed_time: Total elapsed time in seconds.
        """
        self.console.print()

        # Format elapsed time
        minutes, seconds = divmod(int(elapsed_time), 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            time_str = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            time_str = f"{minutes}m {seconds}s"
        else:
            time_str = f"{seconds}s"

        # Create summary table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Label", style="dim")
        table.add_column("Value", style="bold")

        table.add_row("Successful:", f"[green]{successful}[/green]")
        if failed > 0:
            table.add_row("Failed:", f"[red]{failed}[/red]")
        table.add_row("Total saved:", f"[cyan]{self._format_size(total_saved)}[/cyan]")
        table.add_row("Elapsed time:", time_str)

        panel = Panel(
            table,
            title="[bold green]Conversion Complete[/bold green]",
            border_style="green",
        )
        self.console.print(panel)

    @property
    def completed_count(self) -> int:
        """Get the number of completed files."""
        return self._completed_count

    @property
    def failed_count(self) -> int:
        """Get the number of failed files."""
        return self._failed_count

    @property
    def total_saved_bytes(self) -> int:
        """Get the total bytes saved so far."""
        return self._total_saved_bytes


@dataclass
class _NullPhotosProgress:
    """Null object pattern for PhotosProgressDisplay when quiet mode is enabled."""

    _completed_count: int = field(default=0, init=False)
    _failed_count: int = field(default=0, init=False)
    _total_saved_bytes: int = field(default=0, init=False)

    def show_library_info(self, info: PhotosLibraryInfo) -> None:
        """No-op."""

    def start(self) -> None:
        """No-op."""

    def start_video(
        self,
        filename: str,
        video_index: int,
        album: str | None = None,
        date: str | None = None,
        original_size: int = 0,
    ) -> None:
        """No-op."""

    def update_export_progress(self, percentage: float) -> None:
        """No-op."""

    def update_convert_progress(
        self,
        percentage: float = 0.0,
        speed: float = 0.0,
        eta: str = "",
    ) -> None:
        """No-op."""

    def update_convert_from_info(self, info: ProgressInfo) -> None:
        """No-op."""

    def complete_video(self, success: bool, saved_bytes: int = 0) -> None:
        """Track completion even in quiet mode."""
        if success:
            self._completed_count += 1
            self._total_saved_bytes += saved_bytes
        else:
            self._failed_count += 1

    def finish(self) -> None:
        """No-op."""

    def show_summary(
        self,
        successful: int,
        failed: int,
        total_saved: int,
        elapsed_time: float,
    ) -> None:
        """No-op."""

    @property
    def completed_count(self) -> int:
        """Get the number of completed files."""
        return self._completed_count

    @property
    def failed_count(self) -> int:
        """Get the number of failed files."""
        return self._failed_count

    @property
    def total_saved_bytes(self) -> int:
        """Get the total bytes saved so far."""
        return self._total_saved_bytes


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
