"""launchd plist generator for macOS automation.

This module generates launchd plist files to enable scheduled automatic video
conversion on macOS. It supports time-based scheduling (StartCalendarInterval)
and folder-based triggers (WatchPaths).

SDS Reference: SDS-A01-001
SRS Reference: SRS-701 (launchd Integration)

Example:
    >>> from video_converter.automation.launchd import LaunchdPlistGenerator
    >>> from video_converter.core.config import Config
    >>>
    >>> config = Config.load()
    >>> generator = LaunchdPlistGenerator(config)
    >>>
    >>> # Generate plist for daily run at 3 AM
    >>> plist = generator.generate_plist(hour=3, minute=0)
    >>> generator.write_plist(plist)
    >>>
    >>> # Generate plist with folder watching
    >>> plist = generator.generate_plist(watch_paths=[Path("~/Videos/Import")])
"""

from __future__ import annotations

import logging
import os
import plistlib
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default paths
DEFAULT_LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
DEFAULT_PLIST_NAME = "com.videoconverter.daily.plist"
DEFAULT_LOG_DIR = Path.home() / "Library" / "Logs" / "video_converter"

# Service identifier
SERVICE_LABEL = "com.videoconverter.daily"


@dataclass
class LaunchdSchedule:
    """Schedule configuration for launchd service.

    Attributes:
        hour: Hour to run (0-23). None for watch-only mode.
        minute: Minute to run (0-59).
        weekday: Day of week (0=Sunday, 1=Monday, ..., 6=Saturday).
                 None for daily schedule.
    """

    hour: int | None = None
    minute: int = 0
    weekday: int | None = None

    def __post_init__(self) -> None:
        """Validate schedule values."""
        if self.hour is not None and not (0 <= self.hour <= 23):
            raise ValueError(f"Hour must be 0-23, got {self.hour}")
        if not (0 <= self.minute <= 59):
            raise ValueError(f"Minute must be 0-59, got {self.minute}")
        if self.weekday is not None and not (0 <= self.weekday <= 6):
            raise ValueError(f"Weekday must be 0-6, got {self.weekday}")

    def to_calendar_interval(self) -> dict[str, int]:
        """Convert to StartCalendarInterval dictionary.

        Returns:
            Dictionary with Hour, Minute, and optionally Weekday.
        """
        result: dict[str, int] = {"Minute": self.minute}
        if self.hour is not None:
            result["Hour"] = self.hour
        if self.weekday is not None:
            result["Weekday"] = self.weekday
        return result


@dataclass
class LaunchdConfig:
    """Configuration for launchd plist generation.

    Attributes:
        label: Service identifier (e.g., "com.videoconverter.daily").
        program_args: Command line arguments for the service.
        schedule: Time-based schedule (StartCalendarInterval).
        watch_paths: Folder paths to watch for changes (WatchPaths).
        working_directory: Working directory for the service.
        environment: Environment variables to set.
        stdout_path: Path for stdout log file.
        stderr_path: Path for stderr log file.
        run_at_load: Whether to run immediately when loaded.
        keep_alive: Whether to restart if process exits.
    """

    label: str = SERVICE_LABEL
    program_args: list[str] = field(default_factory=list)
    schedule: LaunchdSchedule | None = None
    watch_paths: list[Path] = field(default_factory=list)
    working_directory: Path | None = None
    environment: dict[str, str] = field(default_factory=dict)
    stdout_path: Path | None = None
    stderr_path: Path | None = None
    run_at_load: bool = False
    keep_alive: bool = False

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not self.schedule and not self.watch_paths:
            raise ValueError("Either schedule or watch_paths must be provided")


class LaunchdPlistGenerator:
    """Generator for launchd plist files.

    This class creates valid launchd plist XML files for scheduling
    automatic video conversion on macOS.

    Attributes:
        python_path: Path to Python interpreter.
        module_name: Python module to execute.
        command: CLI command to run (e.g., "run").
        log_dir: Directory for log files.
    """

    def __init__(
        self,
        python_path: Path | None = None,
        module_name: str = "video_converter",
        command: str = "run",
        log_dir: Path | None = None,
    ) -> None:
        """Initialize the plist generator.

        Args:
            python_path: Path to Python interpreter. Auto-detected if None.
            module_name: Python module to execute.
            command: CLI command to run.
            log_dir: Directory for log files.
        """
        self.python_path = python_path or self._detect_python_path()
        self.module_name = module_name
        self.command = command
        self.log_dir = log_dir or DEFAULT_LOG_DIR

    def _detect_python_path(self) -> Path:
        """Detect the current Python interpreter path.

        Returns:
            Path to the Python interpreter.
        """
        return Path(sys.executable)

    def _build_program_args(
        self,
        extra_args: list[str] | None = None,
    ) -> list[str]:
        """Build the program arguments list.

        Args:
            extra_args: Additional command line arguments.

        Returns:
            List of command line arguments.
        """
        args = [
            str(self.python_path),
            "-m",
            self.module_name,
            self.command,
        ]
        if extra_args:
            args.extend(extra_args)
        return args

    def _build_environment(self) -> dict[str, str]:
        """Build environment variables for the service.

        Returns:
            Dictionary of environment variables.
        """
        env: dict[str, str] = {}

        # Ensure PATH includes common locations
        path_components = [
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/usr/bin",
            "/bin",
            str(self.python_path.parent),
        ]
        env["PATH"] = ":".join(path_components)

        # Set PYTHONUNBUFFERED for real-time logging
        env["PYTHONUNBUFFERED"] = "1"

        # Set HOME for ~ expansion
        env["HOME"] = str(Path.home())

        # Preserve VIRTUAL_ENV if running in one
        venv = os.environ.get("VIRTUAL_ENV")
        if venv:
            env["VIRTUAL_ENV"] = venv

        return env

    def generate_config(
        self,
        hour: int | None = 3,
        minute: int = 0,
        weekday: int | None = None,
        watch_paths: list[Path] | None = None,
        run_at_load: bool = False,
        extra_args: list[str] | None = None,
    ) -> LaunchdConfig:
        """Generate launchd configuration.

        Args:
            hour: Hour to run (0-23). None for watch-only mode.
            minute: Minute to run (0-59).
            weekday: Day of week (0=Sunday). None for daily.
            watch_paths: Folders to watch for changes.
            run_at_load: Whether to run immediately when loaded.
            extra_args: Additional CLI arguments.

        Returns:
            LaunchdConfig with all settings.
        """
        schedule = None
        if hour is not None:
            schedule = LaunchdSchedule(hour=hour, minute=minute, weekday=weekday)

        expanded_watch_paths = []
        if watch_paths:
            expanded_watch_paths = [p.expanduser().resolve() for p in watch_paths]

        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

        return LaunchdConfig(
            label=SERVICE_LABEL,
            program_args=self._build_program_args(extra_args),
            schedule=schedule,
            watch_paths=expanded_watch_paths,
            environment=self._build_environment(),
            stdout_path=self.log_dir / "stdout.log",
            stderr_path=self.log_dir / "stderr.log",
            run_at_load=run_at_load,
        )

    def generate_plist(
        self,
        config: LaunchdConfig | None = None,
        hour: int | None = 3,
        minute: int = 0,
        weekday: int | None = None,
        watch_paths: list[Path] | None = None,
        run_at_load: bool = False,
        extra_args: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate launchd plist dictionary.

        Args:
            config: Pre-built configuration. If None, built from other args.
            hour: Hour to run (0-23). None for watch-only mode.
            minute: Minute to run (0-59).
            weekday: Day of week (0=Sunday). None for daily.
            watch_paths: Folders to watch for changes.
            run_at_load: Whether to run immediately when loaded.
            extra_args: Additional CLI arguments.

        Returns:
            Dictionary representation of plist.

        Example:
            >>> generator = LaunchdPlistGenerator()
            >>> plist = generator.generate_plist(hour=3, minute=0)
            >>> # plist is ready for writing with plistlib
        """
        if config is None:
            config = self.generate_config(
                hour=hour,
                minute=minute,
                weekday=weekday,
                watch_paths=watch_paths,
                run_at_load=run_at_load,
                extra_args=extra_args,
            )

        plist: dict[str, Any] = {
            "Label": config.label,
            "ProgramArguments": config.program_args,
        }

        # Add schedule (StartCalendarInterval)
        if config.schedule:
            plist["StartCalendarInterval"] = config.schedule.to_calendar_interval()

        # Add watch paths (WatchPaths)
        if config.watch_paths:
            plist["WatchPaths"] = [str(p) for p in config.watch_paths]

        # Add working directory
        if config.working_directory:
            plist["WorkingDirectory"] = str(config.working_directory)

        # Add environment variables
        if config.environment:
            plist["EnvironmentVariables"] = config.environment

        # Add logging
        if config.stdout_path:
            plist["StandardOutPath"] = str(config.stdout_path)
        if config.stderr_path:
            plist["StandardErrorPath"] = str(config.stderr_path)

        # Add run at load
        if config.run_at_load:
            plist["RunAtLoad"] = True

        # Add keep alive
        if config.keep_alive:
            plist["KeepAlive"] = True

        return plist

    def plist_to_xml(self, plist: dict[str, Any]) -> bytes:
        """Convert plist dictionary to XML bytes.

        Args:
            plist: Plist dictionary.

        Returns:
            XML representation as bytes.
        """
        return plistlib.dumps(plist, fmt=plistlib.FMT_XML)

    def write_plist(
        self,
        plist: dict[str, Any],
        output_path: Path | None = None,
    ) -> Path:
        """Write plist to file.

        Args:
            plist: Plist dictionary.
            output_path: Path to write plist. Defaults to LaunchAgents dir.

        Returns:
            Path to the written plist file.

        Raises:
            IOError: If file cannot be written.
        """
        if output_path is None:
            output_path = DEFAULT_LAUNCH_AGENTS_DIR / DEFAULT_PLIST_NAME

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("wb") as f:
            plistlib.dump(plist, f, fmt=plistlib.FMT_XML)

        logger.info(f"Wrote plist to {output_path}")
        return output_path

    def get_plist_path(self) -> Path:
        """Get the default plist file path.

        Returns:
            Path to the plist file.
        """
        return DEFAULT_LAUNCH_AGENTS_DIR / DEFAULT_PLIST_NAME


def validate_plist_syntax(plist_path: Path) -> bool:
    """Validate plist file syntax using plutil.

    Args:
        plist_path: Path to plist file.

    Returns:
        True if plist is valid, False otherwise.
    """
    try:
        result = subprocess.run(
            ["plutil", "-lint", str(plist_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        logger.warning("plutil not found, skipping validation")
        return True


def generate_daily_plist(
    hour: int = 3,
    minute: int = 0,
    python_path: Path | None = None,
) -> dict[str, Any]:
    """Convenience function to generate a daily schedule plist.

    Args:
        hour: Hour to run (0-23).
        minute: Minute to run (0-59).
        python_path: Path to Python interpreter.

    Returns:
        Plist dictionary.

    Example:
        >>> plist = generate_daily_plist(hour=3, minute=0)
        >>> # Write to file
        >>> generator = LaunchdPlistGenerator()
        >>> generator.write_plist(plist)
    """
    generator = LaunchdPlistGenerator(python_path=python_path)
    return generator.generate_plist(hour=hour, minute=minute)


def generate_watch_plist(
    watch_paths: list[Path],
    python_path: Path | None = None,
) -> dict[str, Any]:
    """Convenience function to generate a folder-watching plist.

    Args:
        watch_paths: List of folders to watch.
        python_path: Path to Python interpreter.

    Returns:
        Plist dictionary.

    Example:
        >>> plist = generate_watch_plist([Path("~/Videos/Import")])
        >>> generator = LaunchdPlistGenerator()
        >>> generator.write_plist(plist)
    """
    generator = LaunchdPlistGenerator(python_path=python_path)
    return generator.generate_plist(hour=None, watch_paths=watch_paths)


__all__ = [
    "LaunchdSchedule",
    "LaunchdConfig",
    "LaunchdPlistGenerator",
    "validate_plist_syntax",
    "generate_daily_plist",
    "generate_watch_plist",
    "DEFAULT_LAUNCH_AGENTS_DIR",
    "DEFAULT_PLIST_NAME",
    "DEFAULT_LOG_DIR",
    "SERVICE_LABEL",
]
