"""CLI entrypoint for video-converter."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from video_converter import __version__
from video_converter.automation import ServiceManager, ServiceState
from video_converter.core.config import Config, DEFAULT_CONFIG_FILE
from video_converter.core.logger import configure_logging, set_log_level
from video_converter.core.orchestrator import Orchestrator, OrchestratorConfig
from video_converter.core.types import ConversionMode, ConversionProgress
from video_converter.converters.factory import ConverterFactory
from video_converter.processors.codec_detector import CodecDetector

# Rich console for formatted output
console = Console()


@dataclass
class CLIContext:
    """Context object passed between CLI commands."""

    config: Config
    verbose: bool
    quiet: bool


pass_context = click.make_pass_decorator(CLIContext, ensure=True)


def parse_time(time_str: str) -> tuple[int, int]:
    """Parse time string in HH:MM format.

    Args:
        time_str: Time string in HH:MM format.

    Returns:
        Tuple of (hour, minute).

    Raises:
        click.BadParameter: If time format is invalid.
    """
    match = re.match(r"^(\d{1,2}):(\d{2})$", time_str)
    if not match:
        raise click.BadParameter(
            f"Invalid time format: {time_str}. Use HH:MM format (e.g., 03:00)"
        )

    hour = int(match.group(1))
    minute = int(match.group(2))

    if not (0 <= hour <= 23):
        raise click.BadParameter(f"Hour must be 0-23, got {hour}")
    if not (0 <= minute <= 59):
        raise click.BadParameter(f"Minute must be 0-59, got {minute}")

    return hour, minute


@click.group()
@click.version_option(version=__version__)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to custom configuration file.",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Enable verbose output (DEBUG level logging).",
)
@click.option(
    "--quiet", "-q",
    is_flag=True,
    default=False,
    help="Minimal output (only errors and results).",
)
@click.pass_context
def main(ctx: click.Context, config_path: Path | None, verbose: bool, quiet: bool) -> None:
    """Video Converter - Automated H.264 to H.265 conversion for macOS.

    A CLI tool for converting H.264 videos to H.265 (HEVC) format with
    hardware acceleration support on macOS.
    """
    # Load configuration
    config = Config.load()

    # Configure logging based on verbosity
    if verbose:
        configure_logging(level=logging.DEBUG, console_output=True)
    elif quiet:
        configure_logging(level=logging.ERROR, console_output=True)
    else:
        configure_logging(level=logging.INFO, console_output=True)

    # Store context for subcommands
    ctx.ensure_object(dict)
    ctx.obj = CLIContext(config=config, verbose=verbose, quiet=quiet)


def _create_progress_callback(quiet: bool) -> Any:
    """Create a progress callback for conversion.

    Args:
        quiet: Whether to suppress progress output.

    Returns:
        Progress callback function or None.
    """
    if quiet:
        return None

    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    )
    task_id = None

    def callback(prog: ConversionProgress) -> None:
        nonlocal task_id
        if task_id is None:
            progress.start()
            task_id = progress.add_task(
                f"Converting {prog.current_file}...",
                total=100,
            )
        progress.update(task_id, completed=int(prog.stage_progress * 100))
        if prog.stage_progress >= 1.0:
            progress.stop()

    return callback


def _format_duration(seconds: float) -> str:
    """Format duration in human-readable format.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted duration string like "3 min 45 sec" or "1 hr 30 min".
    """
    if seconds < 60:
        return f"{int(seconds)} sec"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins} min {secs} sec"
    else:
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hrs} hr {mins} min"


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Formatted size string like "1.50 GB" or "680 MB".
    """
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    elif size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.0f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.0f} KB"
    return f"{size_bytes} B"


def _display_conversion_summary(
    input_file: Path,
    output_file: Path,
    original_size: int,
    converted_size: int,
    duration_seconds: float,
    speed_ratio: float,
    encoder_mode: str,
) -> None:
    """Display formatted conversion summary.

    Args:
        input_file: Input file path.
        output_file: Output file path.
        original_size: Original file size in bytes.
        converted_size: Converted file size in bytes.
        duration_seconds: Conversion duration in seconds.
        speed_ratio: Speed ratio (e.g., 6.0 means 6x realtime).
        encoder_mode: Encoder mode used ("hardware" or "software").
    """
    saved_bytes = original_size - converted_size
    saved_pct = (saved_bytes / original_size) * 100 if original_size > 0 else 0
    codec_change = f"H.264 → H.265 ({encoder_mode})"

    console.print()
    console.print("╭──────────────────────────────────────────────╮")
    console.print("│            [bold green]Conversion Complete[/bold green]              │")
    console.print("├──────────────────────────────────────────────┤")
    console.print(f"│  Input:      {input_file.name[:31]:<31} │")
    console.print(f"│  Output:     {output_file.name[:31]:<31} │")
    console.print(f"│  Codec:      {codec_change:<31} │")
    console.print("├──────────────────────────────────────────────┤")
    console.print(f"│  Original:   {_format_size(original_size):<31} │")
    console.print(f"│  Converted:  {_format_size(converted_size):<31} │")
    console.print(f"│  [green]Saved:      {_format_size(saved_bytes)} ({saved_pct:.1f}%)[/green]{' ' * (20 - len(f'{saved_pct:.1f}'))}│")
    console.print("├──────────────────────────────────────────────┤")
    console.print(f"│  Duration:   {_format_duration(duration_seconds):<31} │")
    console.print(f"│  Speed:      {speed_ratio:.1f}x realtime{' ' * 20}│")
    console.print("╰──────────────────────────────────────────────╯")


def _display_conversion_error(
    input_file: Path,
    error_message: str,
) -> None:
    """Display formatted error message with suggestions.

    Args:
        input_file: Input file path.
        error_message: Error message from conversion.
    """
    console.print()
    console.print("[bold red]❌ Conversion Failed[/bold red]")
    console.print()
    console.print(f"[bold]Error:[/bold] {error_message}")
    console.print(f"[bold]File:[/bold] {input_file}")
    console.print()
    console.print("[bold]Try:[/bold]")
    console.print("  1. Verify the file plays in QuickTime Player")
    console.print("  2. Check if the file is completely downloaded")
    console.print(f"  3. Run: ffprobe {input_file}")
    console.print("  4. Use --mode software for problematic files")


@main.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.argument("output_file", type=click.Path(path_type=Path), required=False)
@click.option(
    "--mode",
    type=click.Choice(["hardware", "software"]),
    default=None,
    help="Encoding mode. Uses config default if not specified.",
)
@click.option(
    "--quality",
    type=int,
    default=None,
    help="Quality setting 1-100. Uses config default if not specified.",
)
@click.option(
    "--preset",
    type=click.Choice(["fast", "medium", "slow"]),
    default=None,
    help="Encoder preset: fast, medium, slow. Uses config default if not specified.",
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Overwrite output file if exists.",
)
@click.option(
    "--preserve-metadata/--no-preserve-metadata",
    default=True,
    help="Preserve original metadata (default: True).",
)
@click.option(
    "--validate/--no-validate",
    default=True,
    help="Validate output file after conversion (default: True).",
)
@click.pass_context
def convert(
    ctx: click.Context,
    input_file: Path,
    output_file: Path | None,
    mode: str | None,
    quality: int | None,
    preset: str | None,
    force: bool,
    preserve_metadata: bool,
    validate: bool,
) -> None:
    """Convert a single video file from H.264 to H.265.

    INPUT_FILE is the path to the video file to convert.
    OUTPUT_FILE is optional; if not provided, a default name will be generated.

    Examples:

        # Basic conversion
        video-converter convert video.mp4 video_h265.mp4

        # Use software encoding
        video-converter convert --mode software video.mp4

        # High quality software encoding
        video-converter convert input.mov output.mov --mode software --quality 85

        # Overwrite existing file
        video-converter convert old.mp4 new.mp4 --force

        # Quiet mode for scripts
        video-converter -q convert input.mp4 output.mp4
    """
    cli_ctx: CLIContext = ctx.obj
    config = cli_ctx.config

    # Check if input is already H.265
    detector = CodecDetector()
    try:
        codec_info = detector.analyze(input_file)
    except Exception as e:
        _display_conversion_error(input_file, f"Cannot analyze video: {e}")
        sys.exit(1)

    if codec_info and codec_info.is_hevc:
        console.print(f"[yellow]⚠ {input_file.name} is already H.265/HEVC. Skipping.[/yellow]")
        return

    # Generate output path if not provided
    if output_file is None:
        suffix = "_h265"
        output_file = input_file.parent / f"{input_file.stem}{suffix}.mp4"

    # Check if output exists
    if output_file.exists() and not force:
        console.print(f"[red]✗ Output file exists: {output_file}[/red]")
        console.print("[dim]Use --force to overwrite.[/dim]")
        sys.exit(1)

    # Remove existing output if force
    if output_file.exists() and force:
        output_file.unlink()

    # Resolve conversion mode
    conv_mode = ConversionMode.HARDWARE
    if mode == "software":
        conv_mode = ConversionMode.SOFTWARE
    elif mode == "hardware":
        conv_mode = ConversionMode.HARDWARE
    elif config.encoding.mode == "software":
        conv_mode = ConversionMode.SOFTWARE

    # Resolve quality and preset
    conv_quality = quality if quality is not None else config.encoding.quality
    conv_preset = preset if preset is not None else config.encoding.preset

    # Get encoder name for display
    encoder_name = "hevc_videotoolbox" if conv_mode == ConversionMode.HARDWARE else "libx265"

    if not cli_ctx.quiet:
        console.print(f"[bold]Converting:[/bold] {input_file.name}")
        console.print(f"[bold]Mode:[/bold] {conv_mode.value} ({encoder_name})")
        console.print(
            f"[bold]Input:[/bold] {_format_size(codec_info.size)} "
            f"({codec_info.codec.upper()}, {codec_info.resolution_label}@{codec_info.fps:.0f}fps, "
            f"{_format_duration(codec_info.duration)})"
        )
        console.print()

    # Create orchestrator with config
    orch_config = OrchestratorConfig(
        mode=conv_mode,
        quality=conv_quality,
        crf=config.encoding.crf,
        preset=conv_preset,
        preserve_metadata=preserve_metadata,
        validate_output=validate,
    )
    orchestrator = Orchestrator(config=orch_config, enable_session_persistence=False)

    # Get converter for direct progress tracking
    try:
        converter = orchestrator.converter_factory.get_converter(conv_mode)
    except Exception as e:
        _display_conversion_error(input_file, f"Encoder not available: {e}")
        sys.exit(1)

    # Create conversion request
    from video_converter.core.types import ConversionRequest
    request = ConversionRequest(
        input_path=input_file,
        output_path=output_file,
        mode=conv_mode,
        quality=conv_quality,
        crf=config.encoding.crf,
        preset=conv_preset,
        preserve_metadata=preserve_metadata,
    )

    # Run conversion with progress bar
    try:
        if cli_ctx.quiet:
            # Quiet mode - no progress display
            result = asyncio.run(converter.convert(request))
        else:
            # Progress bar display
            from rich.progress import (
                Progress,
                SpinnerColumn,
                TextColumn,
                BarColumn,
                TaskProgressColumn,
                TimeRemainingColumn,
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=40),
                TaskProgressColumn(),
                TextColumn("│"),
                TextColumn("[cyan]{task.fields[size]}[/cyan]"),
                TextColumn("│"),
                TextColumn("ETA: [cyan]{task.fields[eta]}[/cyan]"),
                console=console,
            ) as progress:
                task_id = progress.add_task(
                    f"Converting {input_file.name}",
                    total=100,
                    size="0 MB",
                    eta="calculating...",
                )

                def on_progress_info(info: Any) -> None:
                    progress.update(
                        task_id,
                        completed=int(info.percentage),
                        size=info.size_formatted,
                        eta=info.eta_formatted,
                    )

                result = asyncio.run(converter.convert(request, on_progress_info=on_progress_info))

        if result.success:
            # Display summary
            if not cli_ctx.quiet:
                _display_conversion_summary(
                    input_file=input_file,
                    output_file=output_file,
                    original_size=result.original_size,
                    converted_size=result.converted_size,
                    duration_seconds=result.duration_seconds,
                    speed_ratio=result.speed_ratio,
                    encoder_mode=conv_mode.value,
                )

            if result.warnings and not cli_ctx.quiet:
                console.print()
                console.print("[yellow]Warnings:[/yellow]")
                for warning in result.warnings:
                    console.print(f"  - {warning}")
        else:
            _display_conversion_error(input_file, result.error_message or "Unknown error")
            sys.exit(1)

    except KeyboardInterrupt:
        console.print()
        console.print("[yellow]Conversion cancelled by user.[/yellow]")
        # Clean up partial output
        if output_file.exists():
            output_file.unlink()
        sys.exit(130)
    except Exception as e:
        _display_conversion_error(input_file, str(e))
        sys.exit(1)


@main.command()
@click.option(
    "--source",
    type=click.Choice(["photos", "folder"]),
    default="folder",
    help="Source mode (default: folder).",
)
@click.option(
    "--input-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Input directory for folder mode.",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Output directory for converted files.",
)
@click.option(
    "--recursive", "-r",
    is_flag=True,
    help="Recursively scan subdirectories.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be converted without actually converting.",
)
@click.option(
    "--resume",
    is_flag=True,
    help="Resume a previously interrupted session.",
)
@click.pass_context
def run(
    ctx: click.Context,
    source: str,
    input_dir: Path | None,
    output_dir: Path | None,
    recursive: bool,
    dry_run: bool,
    resume: bool,
) -> None:
    """Run batch conversion on multiple videos.

    Scans for H.264 videos and converts them to H.265 (HEVC) format.

    Examples:

        # Convert all videos in current directory
        video-converter run --input-dir .

        # Convert with recursive scan
        video-converter run --input-dir ~/Videos -r

        # Dry run to see what would be converted
        video-converter run --input-dir ~/Videos --dry-run

        # Resume an interrupted session
        video-converter run --resume
    """
    cli_ctx: CLIContext = ctx.obj
    config = cli_ctx.config

    # Handle resume mode
    if resume:
        _run_resume_session(cli_ctx)
        return

    # Validate input directory for folder mode
    if source == "folder":
        if input_dir is None:
            console.print("[red]✗ --input-dir is required for folder mode[/red]", err=True)
            sys.exit(1)

        # Scan for videos
        video_files = _scan_for_videos(input_dir, recursive)

        if not video_files:
            console.print("[yellow]No H.264 videos found to convert.[/yellow]")
            return

        # Filter to only H.264 videos
        detector = CodecDetector()
        h264_videos = []
        for video_path in video_files:
            codec_info = detector.detect(video_path)
            if codec_info and not codec_info.is_hevc:
                h264_videos.append(video_path)

        if not h264_videos:
            console.print("[yellow]No H.264 videos found to convert.[/yellow]")
            return

        console.print(f"[bold]Found {len(h264_videos)} H.264 video(s) to convert[/bold]")
        console.print()

        if dry_run:
            _display_dry_run(h264_videos, output_dir)
            return

        _run_batch_conversion(cli_ctx, h264_videos, output_dir)

    elif source == "photos":
        console.print("[yellow]Photos library integration is not yet implemented.[/yellow]")
        console.print("Use --source folder --input-dir <path> instead.")
        sys.exit(1)


def _scan_for_videos(input_dir: Path, recursive: bool) -> list[Path]:
    """Scan directory for video files.

    Args:
        input_dir: Directory to scan.
        recursive: Whether to scan recursively.

    Returns:
        List of video file paths.
    """
    video_extensions = {".mov", ".mp4", ".m4v", ".avi", ".mkv", ".wmv", ".flv", ".webm"}
    video_files: list[Path] = []

    if recursive:
        for ext in video_extensions:
            video_files.extend(input_dir.rglob(f"*{ext}"))
    else:
        for ext in video_extensions:
            video_files.extend(input_dir.glob(f"*{ext}"))

    return sorted(video_files)


def _display_dry_run(video_files: list[Path], output_dir: Path | None) -> None:
    """Display what would be converted in dry run mode.

    Args:
        video_files: List of video files.
        output_dir: Output directory.
    """
    table = Table(title="Videos to Convert (Dry Run)")
    table.add_column("Input File", style="cyan")
    table.add_column("Size", style="green")
    table.add_column("Output", style="yellow")

    total_size = 0
    for video_path in video_files:
        size_mb = video_path.stat().st_size / (1024 * 1024)
        total_size += size_mb

        if output_dir:
            out_path = output_dir / f"{video_path.stem}_h265.mp4"
        else:
            out_path = video_path.parent / f"{video_path.stem}_h265.mp4"

        table.add_row(
            video_path.name,
            f"{size_mb:.1f} MB",
            str(out_path.name),
        )

    console.print(table)
    console.print()
    console.print(f"[bold]Total:[/bold] {len(video_files)} files, {total_size:.1f} MB")
    console.print()
    console.print("[dim]Run without --dry-run to start conversion.[/dim]")


def _run_batch_conversion(
    cli_ctx: CLIContext,
    video_files: list[Path],
    output_dir: Path | None,
) -> None:
    """Run batch conversion.

    Args:
        cli_ctx: CLI context.
        video_files: List of video files to convert.
        output_dir: Output directory.
    """
    config = cli_ctx.config

    # Create output directory if specified
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Resolve conversion mode
    conv_mode = ConversionMode.HARDWARE
    if config.encoding.mode == "software":
        conv_mode = ConversionMode.SOFTWARE

    # Create orchestrator
    orch_config = OrchestratorConfig(
        mode=conv_mode,
        quality=config.encoding.quality,
        crf=config.encoding.crf,
        preset=config.encoding.preset,
        preserve_metadata=True,
        validate_output=config.processing.validate_quality,
        max_concurrent=config.processing.max_concurrent,
    )
    orchestrator = Orchestrator(config=orch_config)

    # Progress display
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        TaskProgressColumn,
        TimeRemainingColumn,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Converting...", total=len(video_files))

        def on_progress(prog: ConversionProgress) -> None:
            progress.update(
                task,
                completed=prog.current_index,
                description=f"Converting {prog.current_file}...",
            )

        def on_complete(report: Any) -> None:
            progress.update(task, completed=len(video_files))

        # Run conversion
        report = asyncio.run(
            orchestrator.run(
                input_paths=video_files,
                output_dir=output_dir,
                on_progress=on_progress,
                on_complete=on_complete,
            )
        )

    # Display results
    console.print()
    console.print("═" * 50)
    console.print("[bold]Conversion Complete[/bold]")
    console.print("═" * 50)
    console.print()

    console.print(f"  Total files:   {report.total_files}")
    console.print(f"  [green]Successful:[/green]   {report.successful}")
    console.print(f"  [red]Failed:[/red]       {report.failed}")
    console.print(f"  [yellow]Skipped:[/yellow]      {report.skipped}")

    if report.total_original_size > 0:
        original_mb = report.total_original_size / (1024 * 1024)
        converted_mb = report.total_converted_size / (1024 * 1024)
        saved_mb = original_mb - converted_mb
        saved_pct = (saved_mb / original_mb) * 100

        console.print()
        console.print(f"  Original:   {original_mb:.1f} MB")
        console.print(f"  Converted:  {converted_mb:.1f} MB")
        console.print(f"  [green]Saved:      {saved_mb:.1f} MB ({saved_pct:.1f}%)[/green]")

    if report.duration:
        console.print()
        console.print(f"  Duration:   {report.duration}")

    if report.failed > 0:
        sys.exit(1)


def _run_resume_session(cli_ctx: CLIContext) -> None:
    """Resume a previously interrupted session.

    Args:
        cli_ctx: CLI context.
    """
    config = cli_ctx.config

    # Resolve conversion mode
    conv_mode = ConversionMode.HARDWARE
    if config.encoding.mode == "software":
        conv_mode = ConversionMode.SOFTWARE

    orch_config = OrchestratorConfig(
        mode=conv_mode,
        quality=config.encoding.quality,
        crf=config.encoding.crf,
        preset=config.encoding.preset,
    )
    orchestrator = Orchestrator(config=orch_config)

    if not orchestrator.has_resumable_session():
        console.print("[yellow]No resumable session found.[/yellow]")
        return

    console.print("[bold]Resuming previous session...[/bold]")

    report = asyncio.run(orchestrator.resume_session())

    if report:
        console.print(f"[green]✓ Session resumed: {report.successful} successful, {report.failed} failed[/green]")
    else:
        console.print("[yellow]Could not resume session.[/yellow]")


@main.command()
def status() -> None:
    """Show service status."""
    manager = ServiceManager()
    service_status = manager.get_status()

    click.echo()
    click.echo("╭" + "─" * 46 + "╮")
    click.echo("│" + "Video Converter Service".center(46) + "│")
    click.echo("├" + "─" * 46 + "┤")

    # Status line
    if service_status.state == ServiceState.NOT_INSTALLED:
        status_text = "✗ Not Installed"
        status_style = "red"
    elif service_status.state == ServiceState.INSTALLED_RUNNING:
        status_text = f"● Running (PID: {service_status.pid})"
        status_style = "green"
    elif service_status.state == ServiceState.INSTALLED_ERROR:
        status_text = f"✗ Error (exit: {service_status.last_exit_status})"
        status_style = "red"
    else:
        status_text = "○ Idle"
        status_style = "yellow"

    click.echo(f"│  Status:     {click.style(status_text, fg=status_style):<35}│")

    # Schedule line
    if service_status.schedule:
        click.echo(f"│  Schedule:   {service_status.schedule:<33}│")

    # Plist path
    if service_status.plist_path:
        plist_display = str(service_status.plist_path)
        if len(plist_display) > 33:
            plist_display = "..." + plist_display[-30:]
        click.echo(f"│  Plist:      {plist_display:<33}│")

    click.echo("╰" + "─" * 46 + "╯")
    click.echo()


@main.command()
@click.option(
    "--period",
    type=click.Choice(["today", "week", "month", "all"]),
    default="all",
    help="Time period for statistics (default: all).",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output statistics in JSON format.",
)
@click.pass_context
def stats(ctx: click.Context, period: str, output_json: bool) -> None:
    """Show conversion statistics.

    Display cumulative statistics about video conversions including
    total files converted, storage saved, and success rates.

    Examples:

        # Show all-time statistics
        video-converter stats

        # Show statistics for this week
        video-converter stats --period week

        # Export statistics as JSON
        video-converter stats --json
    """
    from video_converter.core.session import SessionStateManager
    from datetime import datetime, timedelta

    # Get statistics from session manager
    session_manager = SessionStateManager()
    session_status = session_manager.get_session_status()

    # Calculate statistics (placeholder values for now)
    # In a full implementation, this would query historical data
    stats_data = {
        "period": period,
        "total_converted": 0,
        "total_failed": 0,
        "success_rate": 0.0,
        "total_original_bytes": 0,
        "total_converted_bytes": 0,
        "storage_saved_bytes": 0,
        "storage_saved_percent": 0.0,
    }

    if session_status:
        stats_data["total_converted"] = session_status.get("completed_count", 0)
        stats_data["total_failed"] = session_status.get("failed_count", 0)
        total = stats_data["total_converted"] + stats_data["total_failed"]
        if total > 0:
            stats_data["success_rate"] = (stats_data["total_converted"] / total) * 100

    if output_json:
        console.print(json.dumps(stats_data, indent=2))
        return

    # Display formatted statistics
    console.print()
    console.print("╭" + "─" * 48 + "╮")
    console.print("│" + "Conversion Statistics".center(48) + "│")
    console.print("├" + "─" * 48 + "┤")
    console.print(f"│  Period: {period.capitalize():<38}│")
    console.print("├" + "─" * 48 + "┤")

    console.print(f"│  Videos Converted:     {stats_data['total_converted']:<23}│")
    console.print(f"│  Videos Failed:        {stats_data['total_failed']:<23}│")
    console.print(f"│  Success Rate:         {stats_data['success_rate']:.1f}%{' ' * 20}│")

    if stats_data["total_original_bytes"] > 0:
        original_gb = stats_data["total_original_bytes"] / (1024 ** 3)
        converted_gb = stats_data["total_converted_bytes"] / (1024 ** 3)
        saved_gb = stats_data["storage_saved_bytes"] / (1024 ** 3)
        saved_pct = stats_data["storage_saved_percent"]

        console.print("├" + "─" * 48 + "┤")
        console.print(f"│  Total Original:       {original_gb:.1f} GB{' ' * 17}│")
        console.print(f"│  Total Converted:      {converted_gb:.1f} GB{' ' * 17}│")
        console.print(f"│  Storage Saved:        {saved_gb:.1f} GB ({saved_pct:.1f}%){' ' * 8}│")

    console.print("╰" + "─" * 48 + "╯")
    console.print()

    if stats_data["total_converted"] == 0:
        console.print("[dim]No conversions recorded yet. Run 'video-converter run' to start converting.[/dim]")


@main.command()
@click.pass_context
def config(ctx: click.Context) -> None:
    """View current configuration.

    Display the current configuration settings including encoding options,
    paths, and automation settings.

    Examples:

        # View current configuration
        video-converter config

        # View with verbose output
        video-converter -v config
    """
    cli_ctx: CLIContext = ctx.obj
    cfg = cli_ctx.config

    console.print()
    console.print("[bold]Video Converter Configuration[/bold]")
    console.print("=" * 50)
    console.print()

    # Encoding settings
    console.print("[bold cyan]Encoding[/bold cyan]")
    console.print(f"  Mode:     {cfg.encoding.mode}")
    console.print(f"  Quality:  {cfg.encoding.quality}")
    console.print(f"  CRF:      {cfg.encoding.crf}")
    console.print(f"  Preset:   {cfg.encoding.preset}")
    console.print()

    # Paths settings
    console.print("[bold cyan]Paths[/bold cyan]")
    console.print(f"  Output:     {cfg.paths.output}")
    console.print(f"  Processed:  {cfg.paths.processed}")
    console.print(f"  Failed:     {cfg.paths.failed}")
    console.print()

    # Processing settings
    console.print("[bold cyan]Processing[/bold cyan]")
    console.print(f"  Max Concurrent:    {cfg.processing.max_concurrent}")
    console.print(f"  Validate Quality:  {cfg.processing.validate_quality}")
    console.print(f"  Preserve Original: {cfg.processing.preserve_original}")
    console.print()

    # Automation settings
    console.print("[bold cyan]Automation[/bold cyan]")
    console.print(f"  Enabled:   {cfg.automation.enabled}")
    console.print(f"  Schedule:  {cfg.automation.schedule}")
    console.print(f"  Time:      {cfg.automation.time}")
    console.print()

    # Config file location
    console.print("[bold cyan]Config File[/bold cyan]")
    console.print(f"  Location:  {DEFAULT_CONFIG_FILE}")
    console.print()

    console.print("[dim]Edit the config file directly or use 'video-converter setup' to reconfigure.[/dim]")


@main.command("config-set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str) -> None:
    """Set a configuration value.

    KEY is the configuration key in dot notation (e.g., encoding.mode).
    VALUE is the new value to set.

    Examples:

        # Set encoding mode
        video-converter config-set encoding.mode software

        # Set quality level
        video-converter config-set encoding.quality 60

        # Set max concurrent jobs
        video-converter config-set processing.max_concurrent 4
    """
    cli_ctx: CLIContext = ctx.obj
    cfg = cli_ctx.config

    # Parse the key path
    parts = key.split(".")
    if len(parts) != 2:
        console.print(f"[red]✗ Invalid key format: {key}[/red]", err=True)
        console.print("[dim]Use format: section.key (e.g., encoding.mode)[/dim]")
        sys.exit(1)

    section, attr = parts

    # Get the section
    section_map = {
        "encoding": cfg.encoding,
        "paths": cfg.paths,
        "processing": cfg.processing,
        "automation": cfg.automation,
        "photos": cfg.photos,
        "notification": cfg.notification,
    }

    if section not in section_map:
        console.print(f"[red]✗ Unknown section: {section}[/red]", err=True)
        console.print(f"[dim]Available sections: {', '.join(section_map.keys())}[/dim]")
        sys.exit(1)

    section_obj = section_map[section]

    if not hasattr(section_obj, attr):
        console.print(f"[red]✗ Unknown attribute: {attr} in section {section}[/red]", err=True)
        sys.exit(1)

    # Convert value to appropriate type
    current_value = getattr(section_obj, attr)
    try:
        if isinstance(current_value, bool):
            new_value = value.lower() in ("true", "1", "yes", "on")
        elif isinstance(current_value, int):
            new_value = int(value)
        elif isinstance(current_value, Path):
            new_value = Path(value).expanduser()
        else:
            new_value = value

        setattr(section_obj, attr, new_value)
        cfg.save()

        console.print(f"[green]✓ Set {key} = {new_value}[/green]")

    except (ValueError, TypeError) as e:
        console.print(f"[red]✗ Invalid value: {e}[/red]", err=True)
        sys.exit(1)


@main.command()
@click.pass_context
def setup(ctx: click.Context) -> None:
    """Run initial setup wizard.

    Interactive setup to configure the video converter for first-time use.
    This will guide you through setting up encoding preferences, paths,
    and optional automation.

    Examples:

        video-converter setup
    """
    cli_ctx: CLIContext = ctx.obj
    cfg = cli_ctx.config

    console.print()
    console.print("[bold]Video Converter Setup Wizard[/bold]")
    console.print("=" * 50)
    console.print()
    console.print("This wizard will help you configure the video converter.")
    console.print()

    # Check encoder availability
    console.print("[bold]Checking system capabilities...[/bold]")
    factory = ConverterFactory()

    hw_available = factory.is_hardware_available()
    sw_available = factory.is_software_available()

    if hw_available:
        console.print("  [green]✓[/green] Hardware encoding (VideoToolbox)")
    else:
        console.print("  [red]✗[/red] Hardware encoding (VideoToolbox)")

    if sw_available:
        console.print("  [green]✓[/green] Software encoding (libx265)")
    else:
        console.print("  [red]✗[/red] Software encoding (libx265)")

    if not hw_available and not sw_available:
        console.print()
        console.print("[red]✗ No encoders available. Please install FFmpeg with HEVC support.[/red]")
        sys.exit(1)

    console.print()

    # Encoding mode selection
    if hw_available and sw_available:
        mode = click.prompt(
            "Encoding mode",
            type=click.Choice(["hardware", "software"]),
            default="hardware",
        )
    elif hw_available:
        mode = "hardware"
        console.print("Using hardware encoding (only available option)")
    else:
        mode = "software"
        console.print("Using software encoding (only available option)")

    # Quality setting
    quality = click.prompt(
        "Quality (1-100, higher = better quality, larger files)",
        type=click.IntRange(1, 100),
        default=45,
    )

    # Output directory
    default_output = Path("~/Videos/Converted").expanduser()
    output_dir = click.prompt(
        "Output directory for converted files",
        type=click.Path(),
        default=str(default_output),
    )

    # Automation
    enable_automation = click.confirm(
        "Enable automatic scheduled conversion?",
        default=False,
    )

    schedule_time = "03:00"
    if enable_automation:
        schedule_time = click.prompt(
            "Schedule time (HH:MM)",
            default="03:00",
        )

    console.print()
    console.print("[bold]Saving configuration...[/bold]")

    # Update configuration
    cfg.encoding.mode = mode
    cfg.encoding.quality = quality
    cfg.paths.output = Path(output_dir).expanduser()
    cfg.automation.enabled = enable_automation
    cfg.automation.time = schedule_time

    cfg.save()

    console.print("[green]✓ Configuration saved![/green]")
    console.print()

    # Show summary
    console.print("[bold]Configuration Summary:[/bold]")
    console.print(f"  Mode:        {mode}")
    console.print(f"  Quality:     {quality}")
    console.print(f"  Output:      {output_dir}")
    console.print(f"  Automation:  {'Enabled at ' + schedule_time if enable_automation else 'Disabled'}")
    console.print()

    if enable_automation:
        console.print("To install the automation service, run:")
        console.print("  video-converter install-service")
        console.print()

    console.print("[green]Setup complete![/green]")


@main.command("install-service")
@click.option(
    "--time",
    "schedule_time",
    default="03:00",
    help="Daily execution time in HH:MM format (default: 03:00)",
)
@click.option(
    "--weekday",
    type=click.IntRange(0, 6),
    default=None,
    help="Day of week (0=Sunday, 6=Saturday). If not set, runs daily.",
)
@click.option(
    "--watch",
    "watch_paths",
    multiple=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Folder to watch for new videos. Can be specified multiple times.",
)
@click.option(
    "--run-now",
    is_flag=True,
    help="Run the service immediately after installation.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force reinstall if service already exists.",
)
def install_service(
    schedule_time: str,
    weekday: int | None,
    watch_paths: tuple[str, ...],
    run_now: bool,
    force: bool,
) -> None:
    """Install launchd automation service.

    This command creates a launchd plist and loads it to enable
    automatic video conversion on a schedule.

    Examples:

        # Install with default schedule (daily at 3:00 AM)
        video-converter install-service

        # Install to run at 2:00 AM
        video-converter install-service --time 02:00

        # Install to run every Monday at 4:00 AM
        video-converter install-service --time 04:00 --weekday 1

        # Install with folder watching
        video-converter install-service --watch ~/Videos/Import

        # Combine time schedule with folder watching
        video-converter install-service --time 03:00 --watch ~/Videos/Import
    """
    # Parse time
    try:
        hour, minute = parse_time(schedule_time)
    except click.BadParameter as e:
        click.echo(click.style(f"Error: {e.message}", fg="red"), err=True)
        sys.exit(1)

    # Convert watch paths
    watch_path_list = [Path(p) for p in watch_paths] if watch_paths else None

    # Determine if we need a time schedule
    schedule_hour: int | None = hour
    if watch_path_list and not schedule_time:
        schedule_hour = None

    manager = ServiceManager()

    click.echo("Installing service...")

    result = manager.install(
        hour=schedule_hour,
        minute=minute,
        weekday=weekday,
        watch_paths=watch_path_list,
        run_at_load=run_now,
        force=force,
    )

    if result.success:
        click.echo(click.style("✓ " + result.message, fg="green"))

        if result.plist_path:
            click.echo(f"  Plist: {result.plist_path}")

        # Show log file locations
        stdout_log, stderr_log = manager.get_log_paths()
        click.echo(f"  Logs:  {stdout_log.parent}/")

        if run_now:
            click.echo()
            click.echo("Service will run immediately.")
    else:
        click.echo(click.style(f"✗ {result.message}", fg="red"), err=True)
        if result.error:
            click.echo(click.style(f"  Error: {result.error}", fg="red"), err=True)
        sys.exit(1)


@main.command("uninstall-service")
@click.option(
    "--remove-logs",
    is_flag=True,
    help="Also remove log files.",
)
@click.option(
    "--yes", "-y",
    is_flag=True,
    help="Skip confirmation prompt.",
)
def uninstall_service(remove_logs: bool, yes: bool) -> None:
    """Remove launchd automation service.

    This command unloads the service from launchd and removes
    the plist file.

    Examples:

        # Uninstall service (with confirmation)
        video-converter uninstall-service

        # Uninstall without confirmation
        video-converter uninstall-service --yes

        # Uninstall and remove log files
        video-converter uninstall-service --remove-logs
    """
    manager = ServiceManager()
    status = manager.get_status()

    if not status.is_installed:
        click.echo("Service is not installed.")
        return

    # Confirmation
    if not yes:
        click.echo(f"Service will be removed: {status.plist_path}")
        if remove_logs:
            click.echo("Log files will also be removed.")
        if not click.confirm("Do you want to continue?"):
            click.echo("Cancelled.")
            return

    click.echo("Uninstalling service...")

    result = manager.uninstall(remove_logs=remove_logs)

    if result.success:
        click.echo(click.style("✓ " + result.message, fg="green"))
    else:
        click.echo(click.style(f"✗ {result.message}", fg="red"), err=True)
        if result.error:
            click.echo(click.style(f"  Error: {result.error}", fg="red"), err=True)
        sys.exit(1)


@main.command("service-status")
def service_status() -> None:
    """Show detailed service status.

    Alias for 'status' command with more details about the launchd service.
    """
    # Delegate to status command
    status()


@main.command("service-start")
def service_start() -> None:
    """Manually start the service.

    Triggers an immediate run of the video conversion service,
    regardless of the configured schedule.

    Examples:

        # Start the service immediately
        video-converter service-start
    """
    manager = ServiceManager()
    result = manager.start()

    if result.success:
        click.echo(click.style("✓ " + result.message, fg="green"))
    else:
        click.echo(click.style(f"✗ {result.message}", fg="red"), err=True)
        if result.error:
            click.echo(click.style(f"  Error: {result.error}", fg="red"), err=True)
        sys.exit(1)


@main.command("service-stop")
def service_stop() -> None:
    """Stop the running service.

    Stops the currently running video conversion service.

    Examples:

        # Stop the running service
        video-converter service-stop
    """
    manager = ServiceManager()
    result = manager.stop()

    if result.success:
        click.echo(click.style("✓ " + result.message, fg="green"))
    else:
        click.echo(click.style(f"✗ {result.message}", fg="red"), err=True)
        if result.error:
            click.echo(click.style(f"  Error: {result.error}", fg="red"), err=True)
        sys.exit(1)


@main.command("service-load")
def service_load() -> None:
    """Load the service into launchd.

    Loads the installed service plist into launchd. The service
    must be installed first using 'install-service'.

    Examples:

        # Load the service
        video-converter service-load
    """
    manager = ServiceManager()
    result = manager.load()

    if result.success:
        click.echo(click.style("✓ " + result.message, fg="green"))
    else:
        click.echo(click.style(f"✗ {result.message}", fg="red"), err=True)
        if result.error:
            click.echo(click.style(f"  Error: {result.error}", fg="red"), err=True)
        sys.exit(1)


@main.command("service-unload")
def service_unload() -> None:
    """Unload the service from launchd.

    Unloads the service from launchd. The plist file remains
    installed but the service will not run until reloaded.

    Examples:

        # Unload the service
        video-converter service-unload
    """
    manager = ServiceManager()
    result = manager.unload()

    if result.success:
        click.echo(click.style("✓ " + result.message, fg="green"))
    else:
        click.echo(click.style(f"✗ {result.message}", fg="red"), err=True)
        if result.error:
            click.echo(click.style(f"  Error: {result.error}", fg="red"), err=True)
        sys.exit(1)


@main.command("service-restart")
def service_restart() -> None:
    """Restart the service.

    Unloads and reloads the service from launchd.

    Examples:

        # Restart the service
        video-converter service-restart
    """
    manager = ServiceManager()
    result = manager.restart()

    if result.success:
        click.echo(click.style("✓ " + result.message, fg="green"))
    else:
        click.echo(click.style(f"✗ {result.message}", fg="red"), err=True)
        if result.error:
            click.echo(click.style(f"  Error: {result.error}", fg="red"), err=True)
        sys.exit(1)


@main.command("service-logs")
@click.option(
    "--lines", "-n",
    type=int,
    default=50,
    help="Number of lines to display (default: 50).",
)
@click.option(
    "--follow", "-f",
    is_flag=True,
    help="Follow log output (like tail -f).",
)
@click.option(
    "--stderr",
    is_flag=True,
    help="Show stderr instead of stdout.",
)
def service_logs(lines: int, follow: bool, stderr: bool) -> None:
    """View service log files.

    Display recent log entries from the video converter service.
    By default shows stdout logs; use --stderr for error logs.

    Examples:

        # View last 50 lines of logs
        video-converter service-logs

        # View last 100 lines
        video-converter service-logs -n 100

        # View error logs
        video-converter service-logs --stderr

        # Follow logs in real-time
        video-converter service-logs -f
    """
    manager = ServiceManager()
    stdout_path, stderr_path = manager.get_log_paths()
    log_path = stderr_path if stderr else stdout_path

    if not log_path.exists():
        log_type = "stderr" if stderr else "stdout"
        click.echo(f"No {log_type} log file found at: {log_path}")
        click.echo()
        click.echo("Logs are created when the service runs.")
        return

    if follow:
        # Use tail -f for following logs
        click.echo(f"Following {log_path.name} (Ctrl+C to exit)...")
        click.echo("-" * 50)
        try:
            subprocess.run(
                ["tail", "-f", str(log_path)],
                check=False,
            )
        except KeyboardInterrupt:
            click.echo()
            click.echo("Stopped following logs.")
    else:
        # Read and display logs
        logs = manager.read_logs(lines=lines)
        log_content = logs["stderr"] if stderr else logs["stdout"]

        if not log_content:
            click.echo("Log file is empty.")
            return

        log_type = "stderr" if stderr else "stdout"
        click.echo(f"=== {log_type.upper()} Log ({log_path}) ===")
        click.echo()
        click.echo(log_content)
        click.echo()
        click.echo(f"--- End of log ({lines} lines) ---")


if __name__ == "__main__":
    main()
