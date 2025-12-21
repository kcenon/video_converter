"""CLI entrypoint for video-converter."""

import click


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
    click.echo("Checking service status...")
    # TODO: Implement status check


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
    default="03:00",
    help="Daily execution time (default: 03:00)",
)
def install_service(time: str) -> None:
    """Install launchd automation service."""
    click.echo(f"Installing service to run daily at {time}...")
    # TODO: Implement service installation


@main.command("uninstall-service")
def uninstall_service() -> None:
    """Remove launchd automation service."""
    click.echo("Removing automation service...")
    # TODO: Implement service removal


if __name__ == "__main__":
    main()
