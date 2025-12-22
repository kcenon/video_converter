"""Command execution utilities for external tools.

This module provides a wrapper for executing external commands like FFprobe,
FFmpeg, and ExifTool with proper error handling and output capture.

SDS Reference: SDS-U01-001

Example:
    >>> from video_converter.utils.command_runner import run_command, run_ffprobe, run_exiftool
    >>>
    >>> # Basic command execution
    >>> result = run_command(["ffmpeg", "-version"])
    >>> print(result.stdout)
    >>>
    >>> # FFprobe with JSON output
    >>> video_info = run_ffprobe("input.mp4")
    >>> print(video_info["streams"][0]["codec_name"])
    >>>
    >>> # ExifTool metadata extraction
    >>> metadata = run_exiftool("input.mp4")
    >>> print(metadata["CreateDate"])
    >>>
    >>> # Real-time progress callback
    >>> def on_progress(line: str):
    ...     if "frame=" in line:
    ...         parse_progress(line)
    ...
    >>> run_command(["ffmpeg", ...], on_output=on_progress)
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Result of a command execution.

    Attributes:
        returncode: Exit code of the command (0 = success).
        stdout: Standard output from the command.
        stderr: Standard error output from the command.
        success: Whether the command completed successfully.
    """

    returncode: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        """Check if command completed successfully."""
        return self.returncode == 0


class CommandNotFoundError(Exception):
    """Raised when required external command is not found."""

    def __init__(self, command: str) -> None:
        self.command = command
        super().__init__(f"Command '{command}' not found. Please install it first.")


class CommandExecutionError(Exception):
    """Raised when command execution fails."""

    def __init__(self, command: str, returncode: int, stderr: str) -> None:
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"Command '{command}' failed with code {returncode}: {stderr}")


class CommandTimeoutError(Exception):
    """Raised when command exceeds timeout.

    Attributes:
        command: The command that timed out.
        timeout: The timeout value in seconds.
    """

    def __init__(self, command: str, timeout: float) -> None:
        self.command = command
        self.timeout = timeout
        super().__init__(f"Command '{command}' timed out after {timeout} seconds")


class CommandRunner:
    """Wrapper for executing external commands.

    This class provides both synchronous and asynchronous methods for
    running external commands with proper error handling.

    Example:
        >>> runner = CommandRunner()
        >>> result = runner.run(["ffprobe", "-version"])
        >>> print(result.stdout)
    """

    @staticmethod
    def check_command_exists(command: str) -> bool:
        """Check if a command exists in PATH.

        Args:
            command: The command name to check.

        Returns:
            True if the command exists, False otherwise.
        """
        return shutil.which(command) is not None

    @staticmethod
    def ensure_command_exists(command: str) -> None:
        """Ensure a command exists, raising an error if not.

        Args:
            command: The command name to check.

        Raises:
            CommandNotFoundError: If the command is not found.
        """
        if not CommandRunner.check_command_exists(command):
            raise CommandNotFoundError(command)

    def run(
        self,
        args: list[str],
        *,
        timeout: float | None = 60.0,
        check: bool = False,
        capture_output: bool = True,
    ) -> CommandResult:
        """Run a command synchronously.

        Args:
            args: Command and arguments to execute.
            timeout: Maximum time to wait for command (seconds).
            check: If True, raise exception on non-zero exit code.
            capture_output: If True, capture stdout and stderr.

        Returns:
            CommandResult containing the execution result.

        Raises:
            CommandNotFoundError: If the command is not found.
            CommandExecutionError: If check=True and command fails.
            CommandTimeoutError: If command times out.
        """
        command_name = args[0] if args else ""
        self.ensure_command_exists(command_name)

        logger.debug("Executing command: %s", " ".join(args))

        try:
            result = subprocess.run(
                args,
                timeout=timeout,
                capture_output=capture_output,
                text=True,
            )

            cmd_result = CommandResult(
                returncode=result.returncode,
                stdout=result.stdout if capture_output else "",
                stderr=result.stderr if capture_output else "",
            )

            if cmd_result.success:
                logger.debug("Command completed successfully: %s", command_name)
            else:
                logger.warning(
                    "Command failed with code %d: %s",
                    cmd_result.returncode,
                    command_name,
                )

            if check and not cmd_result.success:
                raise CommandExecutionError(
                    command_name, cmd_result.returncode, cmd_result.stderr
                )

            return cmd_result

        except subprocess.TimeoutExpired as e:
            logger.error("Command timed out after %s seconds: %s", timeout, command_name)
            raise CommandTimeoutError(command_name, timeout or 0) from e
        except FileNotFoundError as e:
            logger.error("Command not found: %s", command_name)
            raise CommandNotFoundError(command_name) from e

    async def run_async(
        self,
        args: list[str],
        *,
        timeout: float | None = 60.0,
        check: bool = False,
    ) -> CommandResult:
        """Run a command asynchronously.

        Args:
            args: Command and arguments to execute.
            timeout: Maximum time to wait for command (seconds).
            check: If True, raise exception on non-zero exit code.

        Returns:
            CommandResult containing the execution result.

        Raises:
            CommandNotFoundError: If the command is not found.
            CommandExecutionError: If check=True and command fails.
            CommandTimeoutError: If command times out.
        """
        command_name = args[0] if args else ""
        self.ensure_command_exists(command_name)

        logger.debug("Executing async command: %s", " ".join(args))

        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            cmd_result = CommandResult(
                returncode=process.returncode or 0,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
            )

            if cmd_result.success:
                logger.debug("Async command completed successfully: %s", command_name)
            else:
                logger.warning(
                    "Async command failed with code %d: %s",
                    cmd_result.returncode,
                    command_name,
                )

            if check and not cmd_result.success:
                raise CommandExecutionError(
                    command_name, cmd_result.returncode, cmd_result.stderr
                )

            return cmd_result

        except asyncio.TimeoutError as e:
            logger.error("Async command timed out after %s seconds: %s", timeout, command_name)
            raise CommandTimeoutError(command_name, timeout or 0) from e
        except FileNotFoundError as e:
            logger.error("Command not found: %s", command_name)
            raise CommandNotFoundError(command_name) from e

    async def run_with_streaming(
        self,
        args: list[str],
        *,
        timeout: float | None = 600.0,
        on_output: Callable[[str], None] | None = None,
        check: bool = False,
    ) -> CommandResult:
        """Run a command with real-time output streaming.

        This method is useful for long-running commands like FFmpeg where
        progress information is output to stderr in real-time.

        Args:
            args: Command and arguments to execute.
            timeout: Maximum time to wait for command (seconds). Default: 600 (10 min).
            on_output: Optional callback for each line of stderr output.
            check: If True, raise exception on non-zero exit code.

        Returns:
            CommandResult containing the execution result.

        Raises:
            CommandNotFoundError: If the command is not found.
            CommandExecutionError: If check=True and command fails.
            CommandTimeoutError: If command times out.

        Example:
            >>> def handle_progress(line: str):
            ...     if "frame=" in line:
            ...         print(f"Progress: {line}")
            ...
            >>> result = await runner.run_with_streaming(
            ...     ["ffmpeg", "-i", "input.mp4", "-c:v", "libx265", "output.mp4"],
            ...     on_output=handle_progress,
            ... )
        """
        command_name = args[0] if args else ""
        self.ensure_command_exists(command_name)

        logger.debug("Executing streaming command: %s", " ".join(args))

        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            async def read_stream(
                stream: asyncio.StreamReader | None,
                lines: list[str],
                callback: Callable[[str], None] | None = None,
            ) -> None:
                """Read lines from stream and optionally call callback."""
                if stream is None:
                    return
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    line_str = line.decode("utf-8", errors="replace").rstrip("\n\r")
                    lines.append(line_str)
                    if callback:
                        callback(line_str)

            # Create tasks for reading both streams concurrently
            await asyncio.wait_for(
                asyncio.gather(
                    read_stream(process.stdout, stdout_lines),
                    read_stream(process.stderr, stderr_lines, on_output),
                ),
                timeout=timeout,
            )

            await process.wait()

            cmd_result = CommandResult(
                returncode=process.returncode or 0,
                stdout="\n".join(stdout_lines),
                stderr="\n".join(stderr_lines),
            )

            if cmd_result.success:
                logger.debug("Streaming command completed successfully: %s", command_name)
            else:
                logger.warning(
                    "Streaming command failed with code %d: %s",
                    cmd_result.returncode,
                    command_name,
                )

            if check and not cmd_result.success:
                raise CommandExecutionError(
                    command_name, cmd_result.returncode, cmd_result.stderr
                )

            return cmd_result

        except asyncio.TimeoutError as e:
            logger.error(
                "Streaming command timed out after %s seconds: %s", timeout, command_name
            )
            # Attempt to terminate the process
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except (ProcessLookupError, asyncio.TimeoutError):
                with contextlib.suppress(ProcessLookupError):
                    process.kill()
            raise CommandTimeoutError(command_name, timeout or 0) from e
        except FileNotFoundError as e:
            logger.error("Command not found: %s", command_name)
            raise CommandNotFoundError(command_name) from e


class FFprobeRunner:
    """Specialized runner for FFprobe commands.

    Provides convenient methods for common FFprobe operations with
    JSON output parsing.

    Example:
        >>> runner = FFprobeRunner()
        >>> info = runner.get_format_info(Path("video.mp4"))
        >>> print(info["format"]["duration"])
    """

    FFPROBE_CMD = "ffprobe"

    def __init__(self, command_runner: CommandRunner | None = None) -> None:
        """Initialize FFprobe runner.

        Args:
            command_runner: CommandRunner instance to use. If None, creates a new one.
        """
        self._runner = command_runner or CommandRunner()

    def _build_json_args(
        self,
        path: Path,
        show_format: bool = True,
        show_streams: bool = True,
        show_error: bool = True,
    ) -> list[str]:
        """Build FFprobe arguments for JSON output.

        Args:
            path: Path to the video file.
            show_format: Include format information.
            show_streams: Include stream information.
            show_error: Include error information.

        Returns:
            List of command arguments.
        """
        args = [
            self.FFPROBE_CMD,
            "-v", "error",
            "-print_format", "json",
        ]

        if show_format:
            args.append("-show_format")
        if show_streams:
            args.append("-show_streams")
        if show_error:
            args.append("-show_error")

        args.append(str(path))
        return args

    def probe(
        self,
        path: Path,
        *,
        show_format: bool = True,
        show_streams: bool = True,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Probe a video file and return information as a dictionary.

        Args:
            path: Path to the video file.
            show_format: Include format information.
            show_streams: Include stream information.
            timeout: Maximum time to wait (seconds).

        Returns:
            Dictionary containing video information.

        Raises:
            CommandNotFoundError: If FFprobe is not installed.
            CommandExecutionError: If probing fails.
            json.JSONDecodeError: If output cannot be parsed.
            FileNotFoundError: If the video file doesn't exist.
        """
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {path}")

        args = self._build_json_args(
            path,
            show_format=show_format,
            show_streams=show_streams,
        )

        result = self._runner.run(args, timeout=timeout, check=True)
        return json.loads(result.stdout)

    async def probe_async(
        self,
        path: Path,
        *,
        show_format: bool = True,
        show_streams: bool = True,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Probe a video file asynchronously.

        Args:
            path: Path to the video file.
            show_format: Include format information.
            show_streams: Include stream information.
            timeout: Maximum time to wait (seconds).

        Returns:
            Dictionary containing video information.
        """
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {path}")

        args = self._build_json_args(
            path,
            show_format=show_format,
            show_streams=show_streams,
        )

        result = await self._runner.run_async(args, timeout=timeout, check=True)
        return json.loads(result.stdout)

    def quick_check(self, path: Path, timeout: float = 10.0) -> bool:
        """Quickly check if a video file is valid.

        This performs a minimal check to see if the file can be opened
        and basic information can be read.

        Args:
            path: Path to the video file.
            timeout: Maximum time to wait (seconds).

        Returns:
            True if the file is valid, False otherwise.
        """
        if not path.exists():
            return False

        args = [
            self.FFPROBE_CMD,
            "-v", "error",
            str(path),
        ]

        try:
            result = self._runner.run(args, timeout=timeout)
            return result.success and not result.stderr.strip()
        except (CommandNotFoundError, CommandExecutionError, CommandTimeoutError):
            return False


class ExifToolRunner:
    """Specialized runner for ExifTool commands.

    Provides methods for reading and writing metadata from media files
    using ExifTool with JSON output parsing.

    ExifTool is a powerful metadata manipulation tool that supports a wide
    variety of file formats including video files (MP4, MOV, etc.).

    Example:
        >>> runner = ExifToolRunner()
        >>> metadata = runner.read_metadata(Path("video.mp4"))
        >>> print(metadata.get("CreateDate"))
        >>> print(metadata.get("GPSLatitude"))

    Installation:
        brew install exiftool
    """

    EXIFTOOL_CMD = "exiftool"

    # Common video metadata tags
    DATE_TAGS = ["CreateDate", "DateTimeOriginal", "MediaCreateDate", "TrackCreateDate"]
    GPS_TAGS = ["GPSLatitude", "GPSLongitude", "GPSAltitude", "GPSPosition"]
    CAMERA_TAGS = ["Make", "Model", "Software"]

    def __init__(self, command_runner: CommandRunner | None = None) -> None:
        """Initialize ExifTool runner.

        Args:
            command_runner: CommandRunner instance to use. If None, creates a new one.
        """
        self._runner = command_runner or CommandRunner()

    def is_available(self) -> bool:
        """Check if ExifTool is installed and available.

        Returns:
            True if ExifTool is available, False otherwise.
        """
        return CommandRunner.check_command_exists(self.EXIFTOOL_CMD)

    def read_metadata(
        self,
        path: Path,
        *,
        tags: list[str] | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Read metadata from a file.

        Args:
            path: Path to the media file.
            tags: Specific tags to read. If None, reads all tags.
            timeout: Maximum time to wait (seconds).

        Returns:
            Dictionary containing metadata key-value pairs.

        Raises:
            CommandNotFoundError: If ExifTool is not installed.
            CommandExecutionError: If reading fails.
            FileNotFoundError: If the file doesn't exist.

        Example:
            >>> runner = ExifToolRunner()
            >>> meta = runner.read_metadata(Path("video.mp4"))
            >>> print(meta.get("CreateDate"))
            '2024:03:15 10:30:00'
        """
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        args = [self.EXIFTOOL_CMD, "-json", "-n"]  # -n for numeric values

        if tags:
            for tag in tags:
                args.append(f"-{tag}")

        args.append(str(path))

        logger.debug("Reading metadata from: %s", path)
        result = self._runner.run(args, timeout=timeout, check=True)

        try:
            data = json.loads(result.stdout)
            # ExifTool returns a list with one dict per file
            if data and isinstance(data, list):
                return data[0]
            return {}
        except json.JSONDecodeError as e:
            logger.error("Failed to parse ExifTool output: %s", e)
            return {}

    async def read_metadata_async(
        self,
        path: Path,
        *,
        tags: list[str] | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Read metadata from a file asynchronously.

        Args:
            path: Path to the media file.
            tags: Specific tags to read. If None, reads all tags.
            timeout: Maximum time to wait (seconds).

        Returns:
            Dictionary containing metadata key-value pairs.
        """
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        args = [self.EXIFTOOL_CMD, "-json", "-n"]

        if tags:
            for tag in tags:
                args.append(f"-{tag}")

        args.append(str(path))

        logger.debug("Reading metadata async from: %s", path)
        result = await self._runner.run_async(args, timeout=timeout, check=True)

        try:
            data = json.loads(result.stdout)
            if data and isinstance(data, list):
                return data[0]
            return {}
        except json.JSONDecodeError as e:
            logger.error("Failed to parse ExifTool output: %s", e)
            return {}

    def write_metadata(
        self,
        path: Path,
        metadata: dict[str, Any],
        *,
        overwrite_original: bool = True,
        timeout: float = 30.0,
    ) -> bool:
        """Write metadata to a file.

        Args:
            path: Path to the media file.
            metadata: Dictionary of tag-value pairs to write.
            overwrite_original: If True, modify file in place (no backup).
            timeout: Maximum time to wait (seconds).

        Returns:
            True if metadata was written successfully.

        Raises:
            CommandNotFoundError: If ExifTool is not installed.
            CommandExecutionError: If writing fails.
            FileNotFoundError: If the file doesn't exist.

        Example:
            >>> runner = ExifToolRunner()
            >>> runner.write_metadata(
            ...     Path("video.mp4"),
            ...     {"CreateDate": "2024:03:15 10:30:00"}
            ... )
        """
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        args = [self.EXIFTOOL_CMD]

        if overwrite_original:
            args.append("-overwrite_original")

        for tag, value in metadata.items():
            # Handle different value types
            if isinstance(value, (str, int, float)):
                args.append(f"-{tag}={value}")
            else:
                args.append(f"-{tag}={str(value)}")

        args.append(str(path))

        logger.debug("Writing metadata to: %s", path)
        result = self._runner.run(args, timeout=timeout)

        if result.success:
            logger.debug("Metadata written successfully to: %s", path)
        else:
            logger.warning("Failed to write metadata to %s: %s", path, result.stderr)

        return result.success

    def copy_metadata(
        self,
        source: Path,
        dest: Path,
        *,
        tags: list[str] | None = None,
        overwrite_original: bool = True,
        timeout: float = 30.0,
    ) -> bool:
        """Copy metadata from one file to another.

        Args:
            source: Path to the source file.
            dest: Path to the destination file.
            tags: Specific tags to copy. If None, copies all tags.
            overwrite_original: If True, modify dest file in place.
            timeout: Maximum time to wait (seconds).

        Returns:
            True if metadata was copied successfully.

        Example:
            >>> runner = ExifToolRunner()
            >>> runner.copy_metadata(
            ...     Path("original.mp4"),
            ...     Path("converted.mp4"),
            ...     tags=["CreateDate", "GPSLatitude", "GPSLongitude"]
            ... )
        """
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")
        if not dest.exists():
            raise FileNotFoundError(f"Destination file not found: {dest}")

        args = [self.EXIFTOOL_CMD, "-TagsFromFile", str(source)]

        if tags:
            for tag in tags:
                args.append(f"-{tag}")
        else:
            args.append("-all:all")

        if overwrite_original:
            args.append("-overwrite_original")

        args.append(str(dest))

        logger.debug("Copying metadata from %s to %s", source, dest)
        result = self._runner.run(args, timeout=timeout)

        if result.success:
            logger.debug("Metadata copied successfully")
        else:
            logger.warning("Failed to copy metadata: %s", result.stderr)

        return result.success

    def get_date_info(self, path: Path, timeout: float = 10.0) -> dict[str, str]:
        """Get date-related metadata from a file.

        Args:
            path: Path to the media file.
            timeout: Maximum time to wait (seconds).

        Returns:
            Dictionary with date tags and their values.
        """
        return self.read_metadata(path, tags=self.DATE_TAGS, timeout=timeout)

    def get_gps_info(self, path: Path, timeout: float = 10.0) -> dict[str, Any]:
        """Get GPS-related metadata from a file.

        Args:
            path: Path to the media file.
            timeout: Maximum time to wait (seconds).

        Returns:
            Dictionary with GPS tags and their values.
        """
        return self.read_metadata(path, tags=self.GPS_TAGS, timeout=timeout)


# Convenience functions for simple use cases

def run_command(
    args: list[str],
    *,
    timeout: float | None = 60.0,
    check: bool = False,
) -> CommandResult:
    """Run a command synchronously.

    Convenience function that creates a CommandRunner and runs the command.

    Args:
        args: Command and arguments to execute.
        timeout: Maximum time to wait for command (seconds).
        check: If True, raise exception on non-zero exit code.

    Returns:
        CommandResult containing the execution result.

    Example:
        >>> result = run_command(["ffmpeg", "-version"])
        >>> print(result.stdout)
    """
    runner = CommandRunner()
    return runner.run(args, timeout=timeout, check=check)


def run_ffprobe(
    path: Path | str,
    *,
    show_format: bool = True,
    show_streams: bool = True,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Run FFprobe and return parsed JSON output.

    Convenience function for quick FFprobe operations.

    Args:
        path: Path to the video file.
        show_format: Include format information.
        show_streams: Include stream information.
        timeout: Maximum time to wait (seconds).

    Returns:
        Dictionary containing video information.

    Example:
        >>> info = run_ffprobe("video.mp4")
        >>> print(info["streams"][0]["codec_name"])
    """
    runner = FFprobeRunner()
    return runner.probe(
        Path(path) if isinstance(path, str) else path,
        show_format=show_format,
        show_streams=show_streams,
        timeout=timeout,
    )


def run_exiftool(
    path: Path | str,
    *,
    tags: list[str] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Run ExifTool and return parsed metadata.

    Convenience function for quick ExifTool operations.

    Args:
        path: Path to the media file.
        tags: Specific tags to read. If None, reads all tags.
        timeout: Maximum time to wait (seconds).

    Returns:
        Dictionary containing metadata.

    Example:
        >>> metadata = run_exiftool("video.mp4")
        >>> print(metadata.get("CreateDate"))
    """
    runner = ExifToolRunner()
    return runner.read_metadata(
        Path(path) if isinstance(path, str) else path,
        tags=tags,
        timeout=timeout,
    )


__all__ = [
    # Result type
    "CommandResult",
    # Exceptions
    "CommandNotFoundError",
    "CommandExecutionError",
    "CommandTimeoutError",
    # Runner classes
    "CommandRunner",
    "FFprobeRunner",
    "ExifToolRunner",
    # Convenience functions
    "run_command",
    "run_ffprobe",
    "run_exiftool",
]
