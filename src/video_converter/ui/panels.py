"""Rich-based panel components for user information and guidance.

This module provides beautiful, informative panels using the Rich library
for displaying permission errors, help information, and other user guidance.

SDS Reference: SDS-U01-002
SRS Reference: SRS-802 (User Guidance)

Example:
    >>> from video_converter.ui.panels import display_photos_permission_error
    >>>
    >>> display_photos_permission_error()
    # Displays a formatted panel with permission instructions
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Default console for output
_console = Console()


def display_photos_permission_error(
    console: Console | None = None,
    error_type: str = "access_denied",
    library_path: str | None = None,
) -> None:
    """Display a Rich panel for Photos library permission errors.

    Displays a formatted panel with step-by-step instructions for granting
    Full Disk Access permission in macOS System Settings.

    Args:
        console: Rich Console to use for output. Uses default if None.
        error_type: Type of error - "access_denied" or "not_found".
        library_path: Optional library path that was attempted.

    Example:
        >>> display_photos_permission_error()
        # Displays permission denied panel

        >>> display_photos_permission_error(error_type="not_found")
        # Displays library not found panel
    """
    if console is None:
        console = _console

    if error_type == "not_found":
        _display_library_not_found(console, library_path)
    else:
        _display_access_denied(console)


def _display_access_denied(console: Console) -> None:
    """Display access denied panel with instructions.

    Args:
        console: Rich Console for output.
    """
    title = "[bold yellow]Photos Library Access Denied[/bold yellow]"

    content = Text()
    content.append("Video Converter needs ", style="")
    content.append("Full Disk Access", style="bold")
    content.append(" to read your Photos library.\n\n", style="")

    content.append("To grant access:\n", style="bold")
    content.append("  1. Open ", style="")
    content.append("System Settings", style="cyan")
    content.append(" → ", style="dim")
    content.append("Privacy & Security", style="cyan")
    content.append("\n")
    content.append("  2. Click ", style="")
    content.append("Full Disk Access", style="cyan")
    content.append("\n")
    content.append("  3. Click the ", style="")
    content.append("+", style="bold cyan")
    content.append(" button\n", style="")
    content.append("  4. Add ", style="")
    content.append("Terminal.app", style="cyan")
    content.append(" (or your terminal application)\n", style="")
    content.append("  5. Enable the toggle\n", style="")
    content.append("  6. Restart your terminal and try again\n\n", style="")

    content.append("Quick access:\n", style="bold")
    content.append(
        '  open "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"',
        style="dim cyan",
    )

    panel = Panel(
        content,
        title=title,
        border_style="yellow",
        padding=(1, 2),
    )
    console.print(panel)


def _display_library_not_found(
    console: Console,
    library_path: str | None = None,
) -> None:
    """Display library not found panel with suggestions.

    Args:
        console: Rich Console for output.
        library_path: Optional library path that was attempted.
    """
    title = "[bold red]Photos Library Not Found[/bold red]"

    content = Text()
    if library_path:
        content.append("Could not find Photos library at:\n", style="")
        content.append(f"  {library_path}\n\n", style="cyan")
    else:
        content.append("Could not find the default Photos library.\n\n", style="")

    content.append("Possible causes:\n", style="bold")
    content.append("  • Photos app has never been opened\n", style="")
    content.append("  • Library is stored in a custom location\n", style="")
    content.append("  • Library was moved or deleted\n\n", style="")

    content.append("Solutions:\n", style="bold")
    content.append("  1. Open the Photos app at least once\n", style="")
    content.append("  2. Use ", style="")
    content.append("--library-path", style="cyan")
    content.append(" to specify a custom location:\n", style="")
    content.append(
        '     video-converter run --source photos --library-path "/path/to/Photos Library.photoslibrary"',
        style="dim",
    )

    panel = Panel(
        content,
        title=title,
        border_style="red",
        padding=(1, 2),
    )
    console.print(panel)


def display_photos_permission_success(console: Console | None = None) -> None:
    """Display a success message for Photos library access.

    Args:
        console: Rich Console to use for output. Uses default if None.
    """
    if console is None:
        console = _console

    console.print("[green]✓[/green] Photos library access granted")


def display_photos_library_info(
    console: Console | None = None,
    library_path: str | None = None,
    video_count: int = 0,
    h264_count: int = 0,
    total_size_gb: float = 0.0,
) -> None:
    """Display Photos library information panel.

    Args:
        console: Rich Console to use for output. Uses default if None.
        library_path: Path to the Photos library.
        video_count: Total number of videos in library.
        h264_count: Number of H.264 videos.
        total_size_gb: Total size of H.264 videos in GB.
    """
    if console is None:
        console = _console

    content = Text()
    if library_path:
        content.append("Library: ", style="bold")
        content.append(f"{library_path}\n", style="cyan")
    content.append("Videos: ", style="bold")
    content.append(f"{video_count:,}\n", style="")
    content.append("H.264 videos: ", style="bold")
    content.append(f"{h264_count:,}", style="yellow")
    if total_size_gb > 0:
        content.append(f" ({total_size_gb:.1f} GB)", style="dim")
    content.append("\n", style="")

    if h264_count > 0:
        estimated_savings = total_size_gb * 0.5
        content.append("Est. savings: ", style="bold")
        content.append(f"~{estimated_savings:.1f} GB", style="green")

    panel = Panel(
        content,
        title="[bold]Photos Library[/bold]",
        border_style="blue",
        padding=(0, 1),
    )
    console.print(panel)
