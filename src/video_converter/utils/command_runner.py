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
                raise CommandExecutionError(
                    command_name, cmd_result.returncode, cmd_result.stderr
                )

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
                raise CommandExecutionError(
                    command_name, cmd_result.returncode, cmd_result.stderr
                )

            return cmd_result

        except FileNotFoundError as e:
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
        except (CommandNotFoundError, CommandExecutionError):
            return False
