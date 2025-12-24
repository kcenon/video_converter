"""Command execution utilities for external tools.

This module provides a wrapper for executing external commands like FFprobe,
FFmpeg, and ExifTool with proper error handling and output capture.

SDS Reference: SDS-U01-001
"""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
    """Raised when required external command is not found.

    This exception provides helpful installation instructions for common tools.

    Attributes:
        command: The command that was not found.
    """

    INSTALL_HINTS = {
        "ffmpeg": "Install with: brew install ffmpeg",
        "ffprobe": "Install with: brew install ffmpeg",
        "exiftool": "Install with: brew install exiftool",
    }

    def __init__(self, command: str) -> None:
        self.command = command
        hint = self.INSTALL_HINTS.get(command, "")
        msg = f"Command '{command}' not found."
        if hint:
            msg += f" {hint}"
        super().__init__(msg)


class CommandTimeoutError(Exception):
    """Raised when command execution exceeds timeout.

    Attributes:
        command: The command that timed out.
        timeout: The timeout value in seconds.
    """

    def __init__(self, command: str, timeout: float) -> None:
        self.command = command
        self.timeout = timeout
        super().__init__(f"Command '{command}' timed out after {timeout:.1f} seconds.")


class CommandExecutionError(Exception):
    """Raised when command execution fails."""

    def __init__(self, command: str, returncode: int, stderr: str) -> None:
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"Command '{command}' failed with code {returncode}: {stderr}")


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
            subprocess.TimeoutExpired: If command times out.
        """
        command_name = args[0] if args else ""
        self.ensure_command_exists(command_name)

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

            if check and not cmd_result.success:
                raise CommandExecutionError(command_name, cmd_result.returncode, cmd_result.stderr)

            return cmd_result

        except FileNotFoundError as e:
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
            asyncio.TimeoutError: If command times out.
        """
        command_name = args[0] if args else ""
        self.ensure_command_exists(command_name)

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

            if check and not cmd_result.success:
                raise CommandExecutionError(command_name, cmd_result.returncode, cmd_result.stderr)

            return cmd_result

        except FileNotFoundError as e:
            raise CommandNotFoundError(command_name) from e

    def run_with_callback(
        self,
        args: list[str],
        on_output: Callable[[str], None],
        *,
        timeout: float | None = 600.0,
        check: bool = False,
        read_stderr: bool = True,
    ) -> CommandResult:
        """Run a command with real-time output streaming.

        This method allows monitoring command output in real-time, which is
        useful for tracking progress of long-running operations like video
        encoding.

        Args:
            args: Command and arguments to execute.
            on_output: Callback function called for each output line.
            timeout: Maximum time to wait for command (seconds).
            check: If True, raise exception on non-zero exit code.
            read_stderr: If True, read from stderr (FFmpeg outputs to stderr).

        Returns:
            CommandResult containing the final execution result.

        Raises:
            CommandNotFoundError: If the command is not found.
            CommandExecutionError: If check=True and command fails.
            CommandTimeoutError: If command times out.

        Example:
            >>> def on_progress(line: str):
            ...     if "frame=" in line:
            ...         print(f"Progress: {line}")
            >>> runner = CommandRunner()
            >>> result = runner.run_with_callback(
            ...     ["ffmpeg", "-i", "input.mp4", "output.mp4"],
            ...     on_output=on_progress,
            ...     read_stderr=True,
            ... )
        """
        command_name = args[0] if args else ""
        self.ensure_command_exists(command_name)

        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        try:
            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE if read_stderr else subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )

            import selectors
            import time

            sel = selectors.DefaultSelector()
            if process.stdout:
                sel.register(process.stdout, selectors.EVENT_READ)
            if read_stderr and process.stderr:
                sel.register(process.stderr, selectors.EVENT_READ)

            start_time = time.monotonic()

            while True:
                # Check timeout
                if timeout is not None:
                    elapsed = time.monotonic() - start_time
                    if elapsed >= timeout:
                        process.kill()
                        process.wait()
                        raise CommandTimeoutError(command_name, timeout)

                    remaining = timeout - elapsed
                else:
                    remaining = None

                events = sel.select(timeout=min(remaining, 0.1) if remaining else 0.1)

                for key, _ in events:
                    line = key.fileobj.readline()  # type: ignore[union-attr]
                    if line:
                        line = line.rstrip("\n\r")
                        if key.fileobj == process.stdout:
                            stdout_lines.append(line)
                        else:
                            stderr_lines.append(line)
                        on_output(line)

                # Check if process has finished
                if process.poll() is not None:
                    # Read remaining output
                    if process.stdout:
                        for line in process.stdout:
                            line = line.rstrip("\n\r")
                            stdout_lines.append(line)
                            on_output(line)
                    if read_stderr and process.stderr:
                        for line in process.stderr:
                            line = line.rstrip("\n\r")
                            stderr_lines.append(line)
                            on_output(line)
                    break

            sel.close()

            cmd_result = CommandResult(
                returncode=process.returncode or 0,
                stdout="\n".join(stdout_lines),
                stderr="\n".join(stderr_lines),
            )

            if check and not cmd_result.success:
                raise CommandExecutionError(command_name, cmd_result.returncode, cmd_result.stderr)

            return cmd_result

        except FileNotFoundError as e:
            raise CommandNotFoundError(command_name) from e


class FFprobeRunner:
    """Specialized runner for FFprobe commands.

    Provides convenient methods for common FFprobe operations with
    JSON output parsing.

    Example:
        ```python
        runner = FFprobeRunner()
        info = runner.get_format_info(Path("video.mp4"))
        print(info["format"]["duration"])
        ```
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
            "-v",
            "error",
            "-print_format",
            "json",
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
        parsed: dict[str, Any] = json.loads(result.stdout)
        return parsed

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
        parsed: dict[str, Any] = json.loads(result.stdout)
        return parsed

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
            "-v",
            "error",
            str(path),
        ]

        try:
            result = self._runner.run(args, timeout=timeout)
            return result.success and not result.stderr.strip()
        except (CommandNotFoundError, CommandExecutionError):
            return False


class ExifToolRunner:
    """Specialized runner for ExifTool commands.

    Provides convenient methods for extracting and modifying metadata
    from media files using ExifTool.

    Example:
        >>> runner = ExifToolRunner()
        >>> metadata = runner.read_metadata(Path("video.mp4"))
        >>> print(metadata.get("CreateDate"))
        '2024:01:15 10:30:00'
    """

    EXIFTOOL_CMD = "exiftool"

    def __init__(self, command_runner: CommandRunner | None = None) -> None:
        """Initialize ExifTool runner.

        Args:
            command_runner: CommandRunner instance to use. If None, creates a new one.
        """
        self._runner = command_runner or CommandRunner()

    def read_metadata(
        self,
        path: Path,
        *,
        timeout: float = 30.0,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Read metadata from a file.

        Args:
            path: Path to the file.
            timeout: Maximum time to wait (seconds).
            tags: Specific tags to read. If None, reads all tags.

        Returns:
            Dictionary containing metadata key-value pairs.

        Raises:
            CommandNotFoundError: If ExifTool is not installed.
            CommandExecutionError: If reading fails.
            FileNotFoundError: If the file doesn't exist.
        """
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        args = [self.EXIFTOOL_CMD, "-j", "-n"]

        if tags:
            args.extend(f"-{tag}" for tag in tags)

        args.append(str(path))

        result = self._runner.run(args, timeout=timeout, check=True)
        data = json.loads(result.stdout)

        # ExifTool returns a list with one dict per file
        return data[0] if data else {}

    async def read_metadata_async(
        self,
        path: Path,
        *,
        timeout: float = 30.0,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Read metadata from a file asynchronously.

        Args:
            path: Path to the file.
            timeout: Maximum time to wait (seconds).
            tags: Specific tags to read. If None, reads all tags.

        Returns:
            Dictionary containing metadata key-value pairs.
        """
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        args = [self.EXIFTOOL_CMD, "-j", "-n"]

        if tags:
            args.extend(f"-{tag}" for tag in tags)

        args.append(str(path))

        result = await self._runner.run_async(args, timeout=timeout, check=True)
        data = json.loads(result.stdout)

        return data[0] if data else {}

    def write_metadata(
        self,
        path: Path,
        metadata: dict[str, Any],
        *,
        timeout: float = 30.0,
        overwrite_original: bool = True,
    ) -> bool:
        """Write metadata to a file.

        Args:
            path: Path to the file.
            metadata: Dictionary of tag-value pairs to write.
            timeout: Maximum time to wait (seconds).
            overwrite_original: If True, modify file in place without backup.

        Returns:
            True if metadata was written successfully.

        Raises:
            CommandNotFoundError: If ExifTool is not installed.
            CommandExecutionError: If writing fails.
            FileNotFoundError: If the file doesn't exist.
        """
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        args = [self.EXIFTOOL_CMD]

        if overwrite_original:
            args.append("-overwrite_original")

        for tag, value in metadata.items():
            args.append(f"-{tag}={value}")

        args.append(str(path))

        result = self._runner.run(args, timeout=timeout, check=True)
        return result.success

    def copy_metadata(
        self,
        source: Path,
        dest: Path,
        *,
        timeout: float = 30.0,
        overwrite_original: bool = True,
        all_tags: bool = True,
    ) -> bool:
        """Copy metadata from source file to destination file.

        Args:
            source: Source file to copy metadata from.
            dest: Destination file to copy metadata to.
            timeout: Maximum time to wait (seconds).
            overwrite_original: If True, modify dest in place without backup.
            all_tags: If True, copy all tags. Otherwise, only common tags.

        Returns:
            True if metadata was copied successfully.

        Raises:
            CommandNotFoundError: If ExifTool is not installed.
            FileNotFoundError: If either file doesn't exist.
        """
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")
        if not dest.exists():
            raise FileNotFoundError(f"Destination file not found: {dest}")

        args = [self.EXIFTOOL_CMD]

        if overwrite_original:
            args.append("-overwrite_original")

        if all_tags:
            args.append("-TagsFromFile")
            args.append(str(source))
            args.append("-all:all")
        else:
            args.append("-TagsFromFile")
            args.append(str(source))

        args.append(str(dest))

        result = self._runner.run(args, timeout=timeout, check=True)
        return result.success

    def quick_check(self, path: Path, timeout: float = 10.0) -> bool:
        """Quickly check if ExifTool can read a file.

        Args:
            path: Path to the file.
            timeout: Maximum time to wait (seconds).

        Returns:
            True if the file is readable, False otherwise.
        """
        if not path.exists():
            return False

        args = [self.EXIFTOOL_CMD, "-ver", str(path)]

        try:
            result = self._runner.run(args, timeout=timeout)
            return result.success
        except (CommandNotFoundError, CommandExecutionError):
            return False


# Convenience functions for simple use cases


def run_command(
    args: list[str],
    *,
    timeout: float | None = 60.0,
    check: bool = False,
    on_output: Callable[[str], None] | None = None,
) -> CommandResult:
    """Run an external command.

    This is a convenience function that creates a CommandRunner instance
    and executes the command.

    Args:
        args: Command and arguments to execute.
        timeout: Maximum time to wait for command (seconds).
        check: If True, raise exception on non-zero exit code.
        on_output: Optional callback for real-time output streaming.

    Returns:
        CommandResult containing the execution result.

    Example:
        >>> result = run_command(["ffmpeg", "-version"])
        >>> print(result.stdout)
    """
    runner = CommandRunner()
    if on_output is not None:
        return runner.run_with_callback(args, on_output, timeout=timeout, check=check)
    return runner.run(args, timeout=timeout, check=check)


def run_ffprobe(
    path: str | Path,
    *,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Run FFprobe on a video file and return parsed JSON output.

    This is a convenience function for quick video analysis.

    Args:
        path: Path to the video file.
        timeout: Maximum time to wait (seconds).

    Returns:
        Dictionary containing video information.

    Example:
        ```python
        info = run_ffprobe("video.mp4")
        print(info["streams"][0]["codec_name"])
        # Output: 'h264'
        ```
    """
    runner = FFprobeRunner()
    return runner.probe(Path(path), timeout=timeout)


def run_exiftool(
    path: str | Path,
    *,
    timeout: float = 30.0,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Run ExifTool on a file and return metadata.

    This is a convenience function for quick metadata extraction.

    Args:
        path: Path to the file.
        timeout: Maximum time to wait (seconds).
        tags: Specific tags to read. If None, reads all tags.

    Returns:
        Dictionary containing metadata key-value pairs.

    Example:
        >>> metadata = run_exiftool("video.mp4")
        >>> print(metadata.get("CreateDate"))
        '2024:01:15 10:30:00'
    """
    runner = ExifToolRunner()
    return runner.read_metadata(Path(path), timeout=timeout, tags=tags)
