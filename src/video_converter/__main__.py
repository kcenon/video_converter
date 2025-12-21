"""CLI entrypoint for video-converter."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import click

from video_converter.automation import ServiceManager, ServiceState


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
@click.version_option()
def main() -> None:
    """Video Converter - Automated H.264 to H.265 conversion for macOS."""
    pass


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.argument("output_file", type=click.Path())
@click.option(
    "--mode",
    type=click.Choice(["hardware", "software"]),
    default="hardware",
    help="Encoding mode (default: hardware)",
)
@click.option(
    "--quality",
    type=int,
    default=45,
    help="Quality setting 1-100 (default: 45)",
)
def convert(input_file: str, output_file: str, mode: str, quality: int) -> None:
    """Convert a single video file from H.264 to H.265."""
    click.echo(f"Converting: {input_file} -> {output_file}")
    click.echo(f"Mode: {mode}, Quality: {quality}")
    # TODO: Implement conversion logic


@main.command()
@click.option(
    "--mode",
    type=click.Choice(["photos", "folder"]),
    default="photos",
    help="Source mode (default: photos)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be converted without actually converting",
)
def run(mode: str, dry_run: bool) -> None:
    """Run batch conversion."""
    click.echo(f"Running batch conversion from: {mode}")
    if dry_run:
        click.echo("(Dry run - no files will be converted)")
    # TODO: Implement batch conversion


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
def stats() -> None:
    """Show conversion statistics."""
    click.echo("Conversion Statistics")
    click.echo("-" * 40)
    # TODO: Implement statistics display


@main.command()
def setup() -> None:
    """Run initial setup wizard."""
    click.echo("Video Converter Setup")
    click.echo("=" * 40)
    # TODO: Implement setup wizard


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

    click.echo(f"Installing service...")

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


if __name__ == "__main__":
    main()
