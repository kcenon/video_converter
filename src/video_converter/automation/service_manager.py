"""Service manager for macOS launchd automation.

This module provides a high-level interface for installing, uninstalling,
and managing the video converter launchd service on macOS.

SDS Reference: SDS-A01-002
SRS Reference: SRS-702 (Service Install/Uninstall)

Example:
    >>> from video_converter.automation.service_manager import ServiceManager
    >>>
    >>> manager = ServiceManager()
    >>>
    >>> # Install service to run daily at 3 AM
    >>> result = manager.install(hour=3, minute=0)
    >>> print(result.message)
    >>>
    >>> # Check service status
    >>> status = manager.get_status()
    >>> print(f"Installed: {status.is_installed}")
    >>>
    >>> # Uninstall service
    >>> result = manager.uninstall()
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from video_converter.automation.launchd import (
    DEFAULT_LAUNCH_AGENTS_DIR,
    DEFAULT_LOG_DIR,
    DEFAULT_PLIST_NAME,
    SERVICE_LABEL,
    LaunchdPlistGenerator,
    validate_plist_syntax,
)

logger = logging.getLogger(__name__)


class ServiceState(Enum):
    """State of the launchd service."""

    NOT_INSTALLED = "not_installed"
    INSTALLED_IDLE = "installed_idle"
    INSTALLED_RUNNING = "installed_running"
    INSTALLED_ERROR = "installed_error"


@dataclass
class ServiceStatus:
    """Status information for the launchd service.

    Attributes:
        state: Current state of the service.
        is_installed: Whether the plist file exists.
        is_loaded: Whether the service is loaded in launchd.
        is_running: Whether the service is currently running.
        pid: Process ID if running, None otherwise.
        last_exit_status: Exit status from last run, None if never run.
        plist_path: Path to the plist file.
        schedule: Human-readable schedule description.
        next_run: Estimated next run time, None if not scheduled.
    """

    state: ServiceState
    is_installed: bool
    is_loaded: bool
    is_running: bool
    pid: int | None = None
    last_exit_status: int | None = None
    plist_path: Path | None = None
    schedule: str | None = None
    next_run: datetime | None = None


@dataclass
class ServiceResult:
    """Result of a service operation.

    Attributes:
        success: Whether the operation succeeded.
        message: Human-readable result message.
        error: Error message if failed, None otherwise.
        plist_path: Path to the plist file, if applicable.
    """

    success: bool
    message: str
    error: str | None = None
    plist_path: Path | None = None


@dataclass
class LastRunInfo:
    """Information about the last service run.

    Attributes:
        timestamp: When the service last ran.
        success: Whether the last run was successful.
        videos_converted: Number of videos converted in last run.
        storage_saved_bytes: Bytes saved in last run.
        error_message: Error message if last run failed.
    """

    timestamp: datetime | None = None
    success: bool | None = None
    videos_converted: int = 0
    storage_saved_bytes: int = 0
    error_message: str | None = None

    @property
    def relative_time(self) -> str:
        """Get relative time description (e.g., 'Today', 'Yesterday').

        Returns:
            Human-readable relative time string.
        """
        if self.timestamp is None:
            return "Never"

        now = datetime.now()
        diff = now - self.timestamp

        if diff.days == 0:
            return f"Today, {self.timestamp.strftime('%H:%M')}"
        elif diff.days == 1:
            return f"Yesterday, {self.timestamp.strftime('%H:%M')}"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        else:
            return self.timestamp.strftime("%Y-%m-%d %H:%M")

    @property
    def result_text(self) -> str:
        """Get result description.

        Returns:
            Human-readable result string.
        """
        if self.success is None:
            return "Unknown"
        elif self.success:
            return "Success"
        else:
            return "Failed"


@dataclass
class DetailedServiceStatus:
    """Extended status information including history and next run.

    Attributes:
        basic_status: Basic ServiceStatus information.
        next_run: Estimated next run time.
        next_run_relative: Human-readable next run description.
        last_run: Information about the last run.
        total_videos_converted: Total videos converted (all time).
        total_storage_saved_bytes: Total storage saved (all time).
        success_rate: Overall success rate (0.0-1.0).
    """

    basic_status: ServiceStatus
    next_run: datetime | None = None
    next_run_relative: str = "Unknown"
    last_run: LastRunInfo = field(default_factory=LastRunInfo)
    total_videos_converted: int = 0
    total_storage_saved_bytes: int = 0
    success_rate: float = 0.0


class ServiceManager:
    """Manager for launchd service operations.

    This class provides high-level operations for installing, uninstalling,
    and querying the status of the video converter launchd service.

    Attributes:
        plist_path: Path to the launchd plist file.
        log_dir: Directory for service log files.
    """

    def __init__(
        self,
        plist_path: Path | None = None,
        log_dir: Path | None = None,
    ) -> None:
        """Initialize the service manager.

        Args:
            plist_path: Path to plist file. Defaults to LaunchAgents directory.
            log_dir: Directory for log files.
        """
        self.plist_path = plist_path or (DEFAULT_LAUNCH_AGENTS_DIR / DEFAULT_PLIST_NAME)
        self.log_dir = log_dir or DEFAULT_LOG_DIR
        self._generator = LaunchdPlistGenerator(log_dir=self.log_dir)

    def install(
        self,
        hour: int = 3,
        minute: int = 0,
        weekday: int | None = None,
        watch_paths: list[Path] | None = None,
        run_at_load: bool = False,
        force: bool = False,
    ) -> ServiceResult:
        """Install the launchd service.

        This method generates a plist file and loads it into launchd.
        If the service is already installed, it will be updated if force=True.

        Args:
            hour: Hour to run (0-23). None for watch-only mode.
            minute: Minute to run (0-59).
            weekday: Day of week (0=Sunday). None for daily.
            watch_paths: Folders to watch for changes.
            run_at_load: Whether to run immediately when loaded.
            force: If True, reinstall even if already installed.

        Returns:
            ServiceResult with success status and message.

        Example:
            >>> manager = ServiceManager()
            >>> result = manager.install(hour=3, minute=0)
            >>> if result.success:
            ...     print("Service installed successfully")
        """
        # Check if already installed
        status = self.get_status()
        if status.is_installed and not force:
            return ServiceResult(
                success=False,
                message="Service is already installed. Use --force to reinstall.",
                error="Service already exists",
                plist_path=self.plist_path,
            )

        # Unload existing service if loaded
        if status.is_loaded:
            unload_result = self._unload_service()
            if not unload_result.success:
                return unload_result

        try:
            # Generate plist
            plist = self._generator.generate_plist(
                hour=hour,
                minute=minute,
                weekday=weekday,
                watch_paths=watch_paths,
                run_at_load=run_at_load,
            )

            # Write plist to file
            self._generator.write_plist(plist, self.plist_path)

            # Validate plist syntax
            if not validate_plist_syntax(self.plist_path):
                return ServiceResult(
                    success=False,
                    message="Generated plist file is invalid",
                    error="Plist validation failed",
                    plist_path=self.plist_path,
                )

            # Load service
            load_result = self._load_service()
            if not load_result.success:
                return load_result

            # Build schedule description
            schedule_desc = self._build_schedule_description(hour, minute, weekday, watch_paths)

            logger.info(f"Service installed successfully: {schedule_desc}")
            return ServiceResult(
                success=True,
                message=f"Service installed successfully. Schedule: {schedule_desc}",
                plist_path=self.plist_path,
            )

        except Exception as e:
            logger.exception("Failed to install service")
            return ServiceResult(
                success=False,
                message="Failed to install service",
                error=str(e),
            )

    def uninstall(self, remove_logs: bool = False) -> ServiceResult:
        """Uninstall the launchd service.

        This method unloads the service from launchd and removes the plist file.

        Args:
            remove_logs: If True, also remove log files.

        Returns:
            ServiceResult with success status and message.

        Example:
            >>> manager = ServiceManager()
            >>> result = manager.uninstall()
            >>> if result.success:
            ...     print("Service uninstalled successfully")
        """
        status = self.get_status()

        if not status.is_installed:
            return ServiceResult(
                success=True,
                message="Service is not installed",
            )

        try:
            # Unload service if loaded
            if status.is_loaded:
                unload_result = self._unload_service()
                if not unload_result.success:
                    logger.warning(f"Failed to unload service: {unload_result.error}")

            # Remove plist file
            if self.plist_path.exists():
                self.plist_path.unlink()
                logger.info(f"Removed plist file: {self.plist_path}")

            # Remove logs if requested
            if remove_logs and self.log_dir.exists():
                for log_file in self.log_dir.glob("*.log"):
                    log_file.unlink()
                    logger.info(f"Removed log file: {log_file}")

            return ServiceResult(
                success=True,
                message="Service uninstalled successfully",
            )

        except Exception as e:
            logger.exception("Failed to uninstall service")
            return ServiceResult(
                success=False,
                message="Failed to uninstall service",
                error=str(e),
            )

    def get_status(self) -> ServiceStatus:
        """Get the current status of the service.

        Returns:
            ServiceStatus with detailed status information.

        Example:
            >>> manager = ServiceManager()
            >>> status = manager.get_status()
            >>> print(f"Installed: {status.is_installed}")
            >>> print(f"Running: {status.is_running}")
        """
        is_installed = self.plist_path.exists()
        is_loaded = False
        is_running = False
        pid = None
        last_exit_status = None
        schedule = None

        if is_installed:
            # Query launchctl for service status
            launchctl_info = self._get_launchctl_info()
            is_loaded = launchctl_info.get("loaded", False)
            pid = launchctl_info.get("pid")
            last_exit_status = launchctl_info.get("last_exit_status")
            is_running = pid is not None

            # Parse schedule from plist
            schedule = self._get_schedule_from_plist()

        # Determine state
        if not is_installed:
            state = ServiceState.NOT_INSTALLED
        elif is_running:
            state = ServiceState.INSTALLED_RUNNING
        elif last_exit_status is not None and last_exit_status != 0:
            state = ServiceState.INSTALLED_ERROR
        else:
            state = ServiceState.INSTALLED_IDLE

        return ServiceStatus(
            state=state,
            is_installed=is_installed,
            is_loaded=is_loaded,
            is_running=is_running,
            pid=pid,
            last_exit_status=last_exit_status,
            plist_path=self.plist_path if is_installed else None,
            schedule=schedule,
        )

    def start(self) -> ServiceResult:
        """Manually start the service.

        This triggers an immediate run of the service, regardless of schedule.

        Returns:
            ServiceResult with success status and message.
        """
        status = self.get_status()

        if not status.is_installed:
            return ServiceResult(
                success=False,
                message="Service is not installed",
                error="Service not found",
            )

        if not status.is_loaded:
            load_result = self._load_service()
            if not load_result.success:
                return load_result

        try:
            result = subprocess.run(
                ["launchctl", "start", SERVICE_LABEL],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                return ServiceResult(
                    success=True,
                    message="Service started successfully",
                )
            else:
                return ServiceResult(
                    success=False,
                    message="Failed to start service",
                    error=result.stderr.strip() or "Unknown error",
                )

        except Exception as e:
            return ServiceResult(
                success=False,
                message="Failed to start service",
                error=str(e),
            )

    def stop(self) -> ServiceResult:
        """Stop the currently running service.

        Returns:
            ServiceResult with success status and message.
        """
        status = self.get_status()

        if not status.is_running:
            return ServiceResult(
                success=True,
                message="Service is not running",
            )

        try:
            result = subprocess.run(
                ["launchctl", "stop", SERVICE_LABEL],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                return ServiceResult(
                    success=True,
                    message="Service stopped successfully",
                )
            else:
                return ServiceResult(
                    success=False,
                    message="Failed to stop service",
                    error=result.stderr.strip() or "Unknown error",
                )

        except Exception as e:
            return ServiceResult(
                success=False,
                message="Failed to stop service",
                error=str(e),
            )

    def load(self) -> ServiceResult:
        """Load the service into launchd.

        This is the public wrapper for loading the service plist into launchd.
        The service must be installed (plist file exists) before loading.

        Returns:
            ServiceResult with success status and message.

        Example:
            >>> manager = ServiceManager()
            >>> result = manager.load()
            >>> if result.success:
            ...     print("Service loaded into launchd")
        """
        status = self.get_status()

        if not status.is_installed:
            return ServiceResult(
                success=False,
                message="Service is not installed. Run 'install-service' first.",
                error="Plist file not found",
            )

        if status.is_loaded:
            return ServiceResult(
                success=True,
                message="Service is already loaded",
            )

        # Check plist file permissions
        perm_result = self._check_plist_permissions()
        if not perm_result.success:
            return perm_result

        return self._load_service()

    def unload(self) -> ServiceResult:
        """Unload the service from launchd.

        This is the public wrapper for unloading the service from launchd.
        The service will stop running but the plist file remains installed.

        Returns:
            ServiceResult with success status and message.

        Example:
            >>> manager = ServiceManager()
            >>> result = manager.unload()
            >>> if result.success:
            ...     print("Service unloaded from launchd")
        """
        status = self.get_status()

        if not status.is_installed:
            return ServiceResult(
                success=False,
                message="Service is not installed",
                error="Plist file not found",
            )

        if not status.is_loaded:
            return ServiceResult(
                success=True,
                message="Service is already unloaded",
            )

        return self._unload_service()

    def restart(self) -> ServiceResult:
        """Restart the service.

        Unloads and reloads the service from launchd.

        Returns:
            ServiceResult with success status and message.

        Example:
            >>> manager = ServiceManager()
            >>> result = manager.restart()
            >>> if result.success:
            ...     print("Service restarted")
        """
        status = self.get_status()

        if not status.is_installed:
            return ServiceResult(
                success=False,
                message="Service is not installed",
                error="Plist file not found",
            )

        # Unload if loaded
        if status.is_loaded:
            unload_result = self._unload_service()
            if not unload_result.success:
                return ServiceResult(
                    success=False,
                    message="Failed to restart service",
                    error=f"Unload failed: {unload_result.error}",
                )

        # Load the service
        load_result = self._load_service()
        if not load_result.success:
            return ServiceResult(
                success=False,
                message="Failed to restart service",
                error=f"Load failed: {load_result.error}",
            )

        return ServiceResult(
            success=True,
            message="Service restarted successfully",
        )

    def _check_plist_permissions(self) -> ServiceResult:
        """Check if plist file has correct permissions.

        launchd requires plist files to have appropriate permissions
        (readable by user, not world-writable).

        Returns:
            ServiceResult indicating if permissions are correct.
        """
        if not self.plist_path.exists():
            return ServiceResult(
                success=False,
                message="Plist file does not exist",
                error="File not found",
            )

        try:
            import stat

            file_stat = self.plist_path.stat()
            mode = file_stat.st_mode

            # Check if file is readable by owner
            if not (mode & stat.S_IRUSR):
                return ServiceResult(
                    success=False,
                    message="Plist file is not readable",
                    error="Fix with: chmod u+r " + str(self.plist_path),
                )

            # Check if file is world-writable (security issue)
            if mode & stat.S_IWOTH:
                return ServiceResult(
                    success=False,
                    message="Plist file is world-writable (security risk)",
                    error="Fix with: chmod o-w " + str(self.plist_path),
                )

            return ServiceResult(
                success=True,
                message="Plist file permissions are correct",
            )

        except Exception as e:
            logger.warning(f"Failed to check plist permissions: {e}")
            # Don't fail on permission check errors, let launchctl handle it
            return ServiceResult(
                success=True,
                message="Permission check skipped",
            )

    def _load_service(self) -> ServiceResult:
        """Load the service into launchd.

        Returns:
            ServiceResult with success status.
        """
        try:
            result = subprocess.run(
                ["launchctl", "load", str(self.plist_path)],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                logger.info(f"Loaded service from {self.plist_path}")
                return ServiceResult(
                    success=True,
                    message="Service loaded successfully",
                )
            else:
                error_msg = result.stderr.strip() or "Unknown error"
                logger.error(f"Failed to load service: {error_msg}")
                return ServiceResult(
                    success=False,
                    message="Failed to load service",
                    error=error_msg,
                )

        except Exception as e:
            return ServiceResult(
                success=False,
                message="Failed to load service",
                error=str(e),
            )

    def _unload_service(self) -> ServiceResult:
        """Unload the service from launchd.

        Returns:
            ServiceResult with success status.
        """
        try:
            result = subprocess.run(
                ["launchctl", "unload", str(self.plist_path)],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                logger.info(f"Unloaded service from {self.plist_path}")
                return ServiceResult(
                    success=True,
                    message="Service unloaded successfully",
                )
            else:
                error_msg = result.stderr.strip() or "Unknown error"
                logger.warning(f"Failed to unload service: {error_msg}")
                return ServiceResult(
                    success=False,
                    message="Failed to unload service",
                    error=error_msg,
                )

        except Exception as e:
            return ServiceResult(
                success=False,
                message="Failed to unload service",
                error=str(e),
            )

    def _get_launchctl_info(self) -> dict[str, Any]:
        """Get service information from launchctl.

        Returns:
            Dictionary with service information.
        """
        info: dict[str, Any] = {"loaded": False}

        try:
            result = subprocess.run(
                ["launchctl", "list"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if SERVICE_LABEL in line:
                        info["loaded"] = True
                        parts = line.split()
                        if len(parts) >= 3:
                            # Format: PID Status Label
                            pid_str = parts[0]
                            status_str = parts[1]

                            if pid_str != "-":
                                info["pid"] = int(pid_str)

                            if status_str != "-":
                                info["last_exit_status"] = int(status_str)

                        break

        except Exception as e:
            logger.warning(f"Failed to get launchctl info: {e}")

        return info

    def _get_schedule_from_plist(self) -> str | None:
        """Parse schedule description from plist file.

        Returns:
            Human-readable schedule description, or None.
        """
        if not self.plist_path.exists():
            return None

        try:
            import plistlib

            with self.plist_path.open("rb") as f:
                plist = plistlib.load(f)

            schedule_parts = []

            # Check StartCalendarInterval
            if "StartCalendarInterval" in plist:
                interval = plist["StartCalendarInterval"]
                hour = interval.get("Hour")
                minute = interval.get("Minute", 0)
                weekday = interval.get("Weekday")

                if weekday is not None:
                    days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
                    day_name = days[weekday] if 0 <= weekday <= 6 else str(weekday)
                    schedule_parts.append(f"Weekly on {day_name}")
                else:
                    schedule_parts.append("Daily")

                if hour is not None:
                    schedule_parts.append(f"at {hour:02d}:{minute:02d}")

            # Check WatchPaths
            if "WatchPaths" in plist:
                watch_count = len(plist["WatchPaths"])
                schedule_parts.append(f"Watching {watch_count} folder(s)")

            return " ".join(schedule_parts) if schedule_parts else None

        except Exception as e:
            logger.warning(f"Failed to parse schedule from plist: {e}")
            return None

    def _build_schedule_description(
        self,
        hour: int | None,
        minute: int,
        weekday: int | None,
        watch_paths: list[Path] | None,
    ) -> str:
        """Build a human-readable schedule description.

        Args:
            hour: Hour to run.
            minute: Minute to run.
            weekday: Day of week.
            watch_paths: Folders to watch.

        Returns:
            Human-readable schedule description.
        """
        parts = []

        if hour is not None:
            if weekday is not None:
                days = [
                    "Sunday",
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                ]
                day_name = days[weekday] if 0 <= weekday <= 6 else str(weekday)
                parts.append(f"Every {day_name} at {hour:02d}:{minute:02d}")
            else:
                parts.append(f"Daily at {hour:02d}:{minute:02d}")

        if watch_paths:
            paths_str = ", ".join(str(p) for p in watch_paths[:2])
            if len(watch_paths) > 2:
                paths_str += f" and {len(watch_paths) - 2} more"
            parts.append(f"Watching: {paths_str}")

        return "; ".join(parts) if parts else "No schedule"

    def get_log_paths(self) -> tuple[Path, Path]:
        """Get paths to stdout and stderr log files.

        Returns:
            Tuple of (stdout_path, stderr_path).
        """
        return (
            self.log_dir / "stdout.log",
            self.log_dir / "stderr.log",
        )

    def read_logs(self, lines: int = 50) -> dict[str, str]:
        """Read recent log entries.

        Args:
            lines: Number of lines to read from each log file.

        Returns:
            Dictionary with 'stdout' and 'stderr' log contents.
        """
        stdout_path, stderr_path = self.get_log_paths()
        logs = {"stdout": "", "stderr": ""}

        for key, path in [("stdout", stdout_path), ("stderr", stderr_path)]:
            if path.exists():
                try:
                    content = path.read_text()
                    log_lines = content.splitlines()
                    logs[key] = "\n".join(log_lines[-lines:])
                except Exception as e:
                    logs[key] = f"Error reading log: {e}"

        return logs

    def calculate_next_run(self) -> tuple[datetime | None, str]:
        """Calculate the next scheduled run time.

        Parses the plist file to determine when the service will next run
        based on StartCalendarInterval settings.

        Returns:
            Tuple of (next_run_datetime, human_readable_description).
            Returns (None, "Not scheduled") if no schedule is configured.

        Example:
            >>> manager = ServiceManager()
            >>> next_run, description = manager.calculate_next_run()
            >>> print(f"Next run: {description}")
        """
        if not self.plist_path.exists():
            return None, "Not installed"

        try:
            import plistlib

            with self.plist_path.open("rb") as f:
                plist = plistlib.load(f)

            # Check StartCalendarInterval
            if "StartCalendarInterval" not in plist:
                # Check for WatchPaths only
                if "WatchPaths" in plist:
                    return None, "Triggered by folder changes"
                return None, "Not scheduled"

            interval = plist["StartCalendarInterval"]
            hour = interval.get("Hour")
            minute = interval.get("Minute", 0)
            weekday = interval.get("Weekday")

            if hour is None:
                return None, "No time specified"

            now = datetime.now()
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            if weekday is not None:
                # Weekly schedule
                # Convert launchd weekday (0=Sun, 1=Mon, ..., 6=Sat)
                # to Python weekday (0=Mon, 1=Tue, ..., 6=Sun)
                python_weekday = (weekday - 1) % 7
                days_ahead = python_weekday - now.weekday()
                if days_ahead < 0:
                    days_ahead += 7
                elif days_ahead == 0 and next_run <= now:
                    days_ahead = 7
                next_run += timedelta(days=days_ahead)
            else:
                # Daily schedule
                if next_run <= now:
                    next_run += timedelta(days=1)

            # Generate human-readable description
            diff = next_run - now
            if diff.days == 0:
                description = f"Today, {next_run.strftime('%H:%M')}"
            elif diff.days == 1:
                description = f"Tomorrow, {next_run.strftime('%H:%M')}"
            else:
                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                day_name = day_names[next_run.weekday()]
                description = f"{day_name}, {next_run.strftime('%H:%M')}"

            return next_run, description

        except Exception as e:
            logger.warning(f"Failed to calculate next run: {e}")
            return None, "Unknown"

    def get_last_run_info(self) -> LastRunInfo:
        """Get information about the last service run.

        Determines last run time from log file modification times and
        parses log content for success/failure information.

        Returns:
            LastRunInfo with timestamp, success status, and statistics.

        Example:
            >>> manager = ServiceManager()
            >>> last_run = manager.get_last_run_info()
            >>> print(f"Last run: {last_run.relative_time} ({last_run.result_text})")
        """
        info = LastRunInfo()
        stdout_path, stderr_path = self.get_log_paths()

        # Get timestamp from log file
        try:
            if stdout_path.exists():
                mtime = stdout_path.stat().st_mtime
                info.timestamp = datetime.fromtimestamp(mtime)

                # Parse log for success/failure and statistics
                content = stdout_path.read_text()
                lines = content.splitlines()

                # Look for completion indicators
                for line in reversed(lines[-100:]):
                    line_lower = line.lower()
                    if "completed" in line_lower or "success" in line_lower:
                        info.success = True
                        break
                    elif "failed" in line_lower or "error" in line_lower:
                        info.success = False
                        break

                # Look for statistics in log
                for line in reversed(lines[-50:]):
                    if "converted" in line.lower():
                        # Try to extract number of videos
                        import re

                        match = re.search(r"(\d+)\s*videos?\s*converted", line, re.I)
                        if match:
                            info.videos_converted = int(match.group(1))
                    if "saved" in line.lower():
                        # Try to extract bytes saved
                        import re

                        match = re.search(r"(\d+\.?\d*)\s*(GB|MB|KB|B)\s*saved", line, re.I)
                        if match:
                            value = float(match.group(1))
                            unit = match.group(2).upper()
                            multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
                            info.storage_saved_bytes = int(value * multipliers.get(unit, 1))

            # Check stderr for errors
            if stderr_path.exists():
                stderr_content = stderr_path.read_text().strip()
                if stderr_content:
                    # Only mark as failed if there's actual error content
                    last_lines = stderr_content.splitlines()[-5:]
                    error_indicators = ["error", "failed", "exception", "traceback"]
                    for line in last_lines:
                        if any(ind in line.lower() for ind in error_indicators):
                            info.success = False
                            info.error_message = line.strip()[:200]
                            break

        except Exception as e:
            logger.warning(f"Failed to get last run info: {e}")

        return info

    def get_detailed_status(self) -> DetailedServiceStatus:
        """Get comprehensive status including history and scheduling.

        Combines basic service status with conversion history statistics
        and next run calculations.

        Returns:
            DetailedServiceStatus with all status information.

        Example:
            >>> manager = ServiceManager()
            >>> status = manager.get_detailed_status()
            >>> print(f"Status: {status.basic_status.state}")
            >>> print(f"Next run: {status.next_run_relative}")
            >>> print(f"Last run: {status.last_run.relative_time}")
            >>> print(f"Total converted: {status.total_videos_converted}")
        """
        # Get basic status
        basic_status = self.get_status()

        # Calculate next run
        next_run, next_run_relative = self.calculate_next_run()

        # Get last run info
        last_run = self.get_last_run_info()

        # Get conversion history statistics
        total_converted = 0
        total_saved = 0
        success_rate = 0.0

        try:
            from video_converter.core.history import get_history

            history = get_history()
            stats = history.get_statistics()
            total_converted = stats.total_converted
            total_saved = stats.total_saved_bytes
            success_rate = stats.success_rate
        except Exception as e:
            logger.debug(f"Could not load conversion history: {e}")

        return DetailedServiceStatus(
            basic_status=basic_status,
            next_run=next_run,
            next_run_relative=next_run_relative,
            last_run=last_run,
            total_videos_converted=total_converted,
            total_storage_saved_bytes=total_saved,
            success_rate=success_rate,
        )


def format_bytes(bytes_value: int) -> str:
    """Format bytes into human-readable string.

    Args:
        bytes_value: Number of bytes.

    Returns:
        Formatted string like "1.5 GB" or "256 MB".
    """
    if bytes_value < 1024:
        return f"{bytes_value} B"
    elif bytes_value < 1024**2:
        return f"{bytes_value / 1024:.1f} KB"
    elif bytes_value < 1024**3:
        return f"{bytes_value / 1024**2:.1f} MB"
    else:
        return f"{bytes_value / 1024**3:.1f} GB"


__all__ = [
    "ServiceState",
    "ServiceStatus",
    "ServiceResult",
    "LastRunInfo",
    "DetailedServiceStatus",
    "ServiceManager",
    "format_bytes",
]
