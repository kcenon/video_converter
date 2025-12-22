"""AppleScript execution utilities for macOS automation.

This module provides utilities for executing AppleScript commands
via the osascript command-line tool.

SDS Reference: SDS-U01-002
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class AppleScriptError(Exception):
    """Base exception for AppleScript execution errors.

    Attributes:
        script: The AppleScript that failed (may be truncated).
        stderr: Error output from osascript.
    """

    def __init__(
        self,
        message: str,
        script: str | None = None,
        stderr: str | None = None,
    ) -> None:
        """Initialize AppleScriptError.

        Args:
            message: Human-readable error message.
            script: The script that failed (for debugging).
            stderr: Standard error output from osascript.
        """
        super().__init__(message)
        self.script = script
        self.stderr = stderr


class AppleScriptTimeoutError(AppleScriptError):
    """Raised when AppleScript execution exceeds timeout.

    Attributes:
        timeout: The timeout value in seconds.
    """

    def __init__(self, timeout: float, script: str | None = None) -> None:
        """Initialize with timeout value.

        Args:
            timeout: The timeout value that was exceeded.
            script: The script that timed out.
        """
        self.timeout = timeout
        super().__init__(
            f"AppleScript execution timed out after {timeout:.1f} seconds",
            script=script,
        )


class AppleScriptExecutionError(AppleScriptError):
    """Raised when AppleScript execution fails with an error."""


@dataclass
class AppleScriptResult:
    """Result of an AppleScript execution.

    Attributes:
        returncode: Exit code from osascript (0 = success).
        stdout: Standard output (script result).
        stderr: Standard error output.
    """

    returncode: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        """Check if script executed successfully."""
        return self.returncode == 0

    @property
    def result(self) -> str:
        """Get the script result (stdout stripped of whitespace)."""
        return self.stdout.strip()


class AppleScriptRunner:
    """Execute AppleScript commands via osascript.

    This class provides a safe interface for running AppleScript code
    with proper timeout handling and error reporting.

    Example:
        >>> runner = AppleScriptRunner()
        >>> result = runner.run('return "Hello, World!"')
        >>> print(result.result)
        Hello, World!

        >>> result = runner.run('tell application "Photos" to activate')
    """

    DEFAULT_TIMEOUT = 60.0  # 1 minute default

    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        """Initialize AppleScriptRunner.

        Args:
            timeout: Default timeout for script execution in seconds.
        """
        self._timeout = timeout

    @property
    def timeout(self) -> float:
        """Get the default timeout value."""
        return self._timeout

    def run(
        self,
        script: str,
        *,
        timeout: float | None = None,
        check: bool = False,
    ) -> AppleScriptResult:
        """Execute an AppleScript.

        Args:
            script: The AppleScript code to execute.
            timeout: Override default timeout (seconds).
                If None, uses the instance default.
            check: If True, raise exception on non-zero exit code.

        Returns:
            AppleScriptResult containing execution result.

        Raises:
            AppleScriptTimeoutError: If execution exceeds timeout.
            AppleScriptExecutionError: If check=True and script fails.
        """
        effective_timeout = timeout if timeout is not None else self._timeout

        logger.debug(f"Executing AppleScript (timeout={effective_timeout}s)")
        logger.debug(f"Script: {script[:200]}{'...' if len(script) > 200 else ''}")

        try:
            process = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=effective_timeout,
            )

            result = AppleScriptResult(
                returncode=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr,
            )

            if result.success:
                logger.debug(f"AppleScript succeeded: {result.result[:100]}")
            else:
                logger.warning(
                    f"AppleScript failed (code {result.returncode}): "
                    f"{result.stderr[:200]}"
                )

            if check and not result.success:
                raise AppleScriptExecutionError(
                    f"AppleScript failed with code {result.returncode}: "
                    f"{result.stderr.strip()}",
                    script=script,
                    stderr=result.stderr,
                )

            return result

        except subprocess.TimeoutExpired as e:
            logger.error(f"AppleScript timed out after {effective_timeout}s")
            raise AppleScriptTimeoutError(effective_timeout, script=script) from e

    def run_script_file(
        self,
        script_path: str,
        *,
        timeout: float | None = None,
        check: bool = False,
    ) -> AppleScriptResult:
        """Execute an AppleScript file.

        Args:
            script_path: Path to the .scpt or .applescript file.
            timeout: Override default timeout (seconds).
            check: If True, raise exception on non-zero exit code.

        Returns:
            AppleScriptResult containing execution result.

        Raises:
            AppleScriptTimeoutError: If execution exceeds timeout.
            AppleScriptExecutionError: If check=True and script fails.
            FileNotFoundError: If script file doesn't exist.
        """
        effective_timeout = timeout if timeout is not None else self._timeout

        logger.debug(f"Executing AppleScript file: {script_path}")

        try:
            process = subprocess.run(
                ["osascript", script_path],
                capture_output=True,
                text=True,
                timeout=effective_timeout,
            )

            result = AppleScriptResult(
                returncode=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr,
            )

            if check and not result.success:
                raise AppleScriptExecutionError(
                    f"AppleScript file '{script_path}' failed: {result.stderr.strip()}",
                    stderr=result.stderr,
                )

            return result

        except subprocess.TimeoutExpired as e:
            logger.error(f"AppleScript file timed out after {effective_timeout}s")
            raise AppleScriptTimeoutError(effective_timeout) from e


def escape_applescript_string(value: str) -> str:
    """Escape a string for safe use in AppleScript.

    This function escapes backslashes and double quotes to prevent
    injection attacks and syntax errors in AppleScript strings.

    Args:
        value: The string to escape.

    Returns:
        Escaped string safe for use in AppleScript.

    Example:
        >>> escape_applescript_string('Hello "World"')
        'Hello \\\\"World\\\\"'
    """
    # Escape backslashes first, then quotes
    return value.replace("\\", "\\\\").replace('"', '\\"')
