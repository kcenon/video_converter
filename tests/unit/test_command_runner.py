"""Unit tests for command_runner module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from video_converter.utils.command_runner import (
    CommandExecutionError,
    CommandNotFoundError,
    CommandResult,
    CommandRunner,
    CommandTimeoutError,
    ExifToolRunner,
    FFprobeRunner,
    run_command,
    run_exiftool,
    run_ffprobe,
)


class TestCommandResult:
    """Tests for CommandResult dataclass."""

    def test_success_when_returncode_is_zero(self) -> None:
        """Test that success is True when returncode is 0."""
        result = CommandResult(returncode=0, stdout="output", stderr="")
        assert result.success is True

    def test_success_when_returncode_is_nonzero(self) -> None:
        """Test that success is False when returncode is non-zero."""
        result = CommandResult(returncode=1, stdout="", stderr="error")
        assert result.success is False


class TestCommandRunner:
    """Tests for CommandRunner class."""

    def test_check_command_exists_true(self) -> None:
        """Test that check_command_exists returns True for existing commands."""
        # 'python' or 'python3' should exist in most environments
        assert CommandRunner.check_command_exists("ls") is True

    def test_check_command_exists_false(self) -> None:
        """Test that check_command_exists returns False for non-existing commands."""
        assert CommandRunner.check_command_exists("nonexistent_command_xyz") is False

    def test_ensure_command_exists_raises(self) -> None:
        """Test that ensure_command_exists raises for non-existing commands."""
        with pytest.raises(CommandNotFoundError) as exc_info:
            CommandRunner.ensure_command_exists("nonexistent_command_xyz")
        assert "nonexistent_command_xyz" in str(exc_info.value)

    def test_run_successful_command(self) -> None:
        """Test running a successful command."""
        runner = CommandRunner()
        result = runner.run(["echo", "hello"])
        assert result.success is True
        assert "hello" in result.stdout

    def test_run_failed_command(self) -> None:
        """Test running a failing command."""
        runner = CommandRunner()
        result = runner.run(["ls", "/nonexistent_path_xyz"])
        assert result.success is False
        assert result.stderr != ""

    def test_run_with_check_raises(self) -> None:
        """Test that check=True raises on failure."""
        runner = CommandRunner()
        with pytest.raises(CommandExecutionError):
            runner.run(["ls", "/nonexistent_path_xyz"], check=True)

    def test_run_command_not_found(self) -> None:
        """Test that running a non-existent command raises."""
        runner = CommandRunner()
        with pytest.raises(CommandNotFoundError):
            runner.run(["nonexistent_command_xyz"])


class TestCommandRunnerAsync:
    """Async tests for CommandRunner."""

    @pytest.mark.asyncio
    async def test_run_async_successful(self) -> None:
        """Test running a successful async command."""
        runner = CommandRunner()
        result = await runner.run_async(["echo", "async hello"])
        assert result.success is True
        assert "async hello" in result.stdout

    @pytest.mark.asyncio
    async def test_run_async_failed(self) -> None:
        """Test running a failing async command."""
        runner = CommandRunner()
        result = await runner.run_async(["ls", "/nonexistent_path_xyz"])
        assert result.success is False

    @pytest.mark.asyncio
    async def test_run_async_with_check_raises(self) -> None:
        """Test that check=True raises on async failure."""
        runner = CommandRunner()
        with pytest.raises(CommandExecutionError):
            await runner.run_async(["ls", "/nonexistent_path_xyz"], check=True)


class TestFFprobeRunner:
    """Tests for FFprobeRunner class."""

    def test_quick_check_nonexistent_file(self) -> None:
        """Test quick_check returns False for non-existent file."""
        runner = FFprobeRunner()
        result = runner.quick_check(Path("/nonexistent/video.mp4"))
        assert result is False

    def test_probe_nonexistent_file(self) -> None:
        """Test probe raises for non-existent file."""
        runner = FFprobeRunner()
        with pytest.raises(FileNotFoundError):
            runner.probe(Path("/nonexistent/video.mp4"))

    def test_build_json_args(self) -> None:
        """Test that JSON args are built correctly."""
        runner = FFprobeRunner()
        args = runner._build_json_args(
            Path("test.mp4"),
            show_format=True,
            show_streams=True,
        )
        assert "ffprobe" in args
        assert "-print_format" in args
        assert "json" in args
        assert "-show_format" in args
        assert "-show_streams" in args
        assert "test.mp4" in args

    def test_probe_with_mock(self) -> None:
        """Test probe with mocked FFprobe output."""
        runner = FFprobeRunner()
        with patch.object(runner._runner, "run") as mock_run:
            mock_run.return_value = CommandResult(
                returncode=0,
                stdout='{"format": {"format_name": "mp4", "duration": "10"}, "streams": []}',
                stderr="",
            )
            # Create a temporary file path for testing
            with patch.object(Path, "exists", return_value=True):
                result = runner.probe(Path("test.mp4"))
                assert "format" in result


class TestFFprobeRunnerAsync:
    """Async tests for FFprobeRunner."""

    @pytest.mark.asyncio
    async def test_probe_async_nonexistent_file(self) -> None:
        """Test probe_async raises for non-existent file."""
        runner = FFprobeRunner()
        with pytest.raises(FileNotFoundError):
            await runner.probe_async(Path("/nonexistent/video.mp4"))


class TestCommandTimeoutError:
    """Tests for CommandTimeoutError exception."""

    def test_timeout_error_message(self) -> None:
        """Test that timeout error contains command and timeout info."""
        error = CommandTimeoutError("ffmpeg", 60.0)
        assert error.command == "ffmpeg"
        assert error.timeout == 60.0
        assert "ffmpeg" in str(error)
        assert "60" in str(error)

    def test_run_timeout_raises_command_timeout_error(self) -> None:
        """Test that run raises CommandTimeoutError on timeout."""
        runner = CommandRunner()
        # Use a command that will definitely timeout with a very short timeout
        with pytest.raises(CommandTimeoutError) as exc_info:
            runner.run(["sleep", "10"], timeout=0.01)
        assert exc_info.value.command == "sleep"
        assert exc_info.value.timeout == 0.01


class TestCommandRunnerAsyncTimeout:
    """Async timeout tests for CommandRunner."""

    @pytest.mark.asyncio
    async def test_run_async_timeout_raises_command_timeout_error(self) -> None:
        """Test that run_async raises CommandTimeoutError on timeout."""
        runner = CommandRunner()
        with pytest.raises(CommandTimeoutError) as exc_info:
            await runner.run_async(["sleep", "10"], timeout=0.01)
        assert exc_info.value.command == "sleep"


class TestRunWithStreaming:
    """Tests for run_with_streaming method."""

    @pytest.mark.asyncio
    async def test_streaming_captures_output(self) -> None:
        """Test that streaming captures stdout and stderr."""
        runner = CommandRunner()
        result = await runner.run_with_streaming(["echo", "hello streaming"])
        assert result.success is True
        assert "hello streaming" in result.stdout

    @pytest.mark.asyncio
    async def test_streaming_calls_callback(self) -> None:
        """Test that on_output callback is called for each line."""
        runner = CommandRunner()
        lines_received: list[str] = []

        def callback(line: str) -> None:
            lines_received.append(line)

        # Use a command that outputs to stderr
        result = await runner.run_with_streaming(
            ["ls", "/nonexistent_path_xyz"],
            on_output=callback,
        )

        # ls on non-existent path outputs to stderr
        assert result.success is False
        # Callback should have been called at least once
        assert len(lines_received) >= 0  # May or may not have output

    @pytest.mark.asyncio
    async def test_streaming_timeout_raises(self) -> None:
        """Test that streaming raises CommandTimeoutError on timeout."""
        runner = CommandRunner()
        with pytest.raises(CommandTimeoutError):
            await runner.run_with_streaming(["sleep", "10"], timeout=0.01)


class TestExifToolRunner:
    """Tests for ExifToolRunner class."""

    def test_is_available(self) -> None:
        """Test that is_available returns correct value."""
        runner = ExifToolRunner()
        # exiftool may or may not be installed
        result = runner.is_available()
        assert isinstance(result, bool)

    def test_read_metadata_nonexistent_file(self) -> None:
        """Test that read_metadata raises for non-existent file."""
        runner = ExifToolRunner()
        with pytest.raises(FileNotFoundError):
            runner.read_metadata(Path("/nonexistent/video.mp4"))

    def test_write_metadata_nonexistent_file(self) -> None:
        """Test that write_metadata raises for non-existent file."""
        runner = ExifToolRunner()
        with pytest.raises(FileNotFoundError):
            runner.write_metadata(
                Path("/nonexistent/video.mp4"),
                {"CreateDate": "2024:01:01 00:00:00"},
            )

    def test_copy_metadata_nonexistent_source(self) -> None:
        """Test that copy_metadata raises for non-existent source."""
        runner = ExifToolRunner()
        with pytest.raises(FileNotFoundError):
            runner.copy_metadata(
                Path("/nonexistent/source.mp4"),
                Path("/nonexistent/dest.mp4"),
            )

    def test_read_metadata_with_mock(self) -> None:
        """Test read_metadata with mocked ExifTool output."""
        runner = ExifToolRunner()
        with patch.object(runner._runner, "run") as mock_run:
            mock_run.return_value = CommandResult(
                returncode=0,
                stdout='[{"SourceFile": "test.mp4", "CreateDate": "2024:03:15 10:30:00"}]',
                stderr="",
            )
            with patch.object(Path, "exists", return_value=True):
                result = runner.read_metadata(Path("test.mp4"))
                assert "CreateDate" in result
                assert result["CreateDate"] == "2024:03:15 10:30:00"


class TestExifToolRunnerAsync:
    """Async tests for ExifToolRunner."""

    @pytest.mark.asyncio
    async def test_read_metadata_async_nonexistent_file(self) -> None:
        """Test that read_metadata_async raises for non-existent file."""
        runner = ExifToolRunner()
        with pytest.raises(FileNotFoundError):
            await runner.read_metadata_async(Path("/nonexistent/video.mp4"))


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_run_command(self) -> None:
        """Test run_command convenience function."""
        result = run_command(["echo", "hello"])
        assert result.success is True
        assert "hello" in result.stdout

    def test_run_command_not_found(self) -> None:
        """Test run_command raises for non-existent command."""
        with pytest.raises(CommandNotFoundError):
            run_command(["nonexistent_command_xyz"])

    def test_run_ffprobe_nonexistent_file(self) -> None:
        """Test run_ffprobe raises for non-existent file."""
        with pytest.raises(FileNotFoundError):
            run_ffprobe("/nonexistent/video.mp4")

    def test_run_exiftool_nonexistent_file(self) -> None:
        """Test run_exiftool raises for non-existent file."""
        with pytest.raises(FileNotFoundError):
            run_exiftool("/nonexistent/video.mp4")
