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
        """Test that timeout error has correct message."""
        error = CommandTimeoutError("ffmpeg", 60.0)
        assert "ffmpeg" in str(error)
        assert "60.0" in str(error)
        assert error.command == "ffmpeg"
        assert error.timeout == 60.0

    def test_timeout_error_inheritance(self) -> None:
        """Test that CommandTimeoutError is an Exception."""
        error = CommandTimeoutError("cmd", 10.0)
        assert isinstance(error, Exception)


class TestCommandNotFoundErrorHints:
    """Tests for CommandNotFoundError installation hints."""

    def test_ffmpeg_install_hint(self) -> None:
        """Test that FFmpeg not found error includes install hint."""
        error = CommandNotFoundError("ffmpeg")
        assert "brew install ffmpeg" in str(error)

    def test_exiftool_install_hint(self) -> None:
        """Test that ExifTool not found error includes install hint."""
        error = CommandNotFoundError("exiftool")
        assert "brew install exiftool" in str(error)

    def test_unknown_command_no_hint(self) -> None:
        """Test that unknown command has no install hint."""
        error = CommandNotFoundError("unknown_tool")
        assert "unknown_tool" in str(error)
        assert "brew" not in str(error)


class TestRunWithCallback:
    """Tests for run_with_callback method."""

    def test_callback_receives_output(self) -> None:
        """Test that callback receives output lines."""
        runner = CommandRunner()
        lines_received: list[str] = []

        def callback(line: str) -> None:
            lines_received.append(line)

        result = runner.run_with_callback(
            ["echo", "hello\nworld"],
            on_output=callback,
        )
        assert result.success
        assert len(lines_received) > 0

    def test_callback_with_command_not_found(self) -> None:
        """Test that callback raises for non-existent command."""
        runner = CommandRunner()

        with pytest.raises(CommandNotFoundError):
            runner.run_with_callback(
                ["nonexistent_command_xyz"],
                on_output=lambda _: None,
            )


class TestExifToolRunner:
    """Tests for ExifToolRunner class."""

    def test_read_metadata_nonexistent_file(self) -> None:
        """Test read_metadata raises for non-existent file."""
        runner = ExifToolRunner()
        with pytest.raises(FileNotFoundError):
            runner.read_metadata(Path("/nonexistent/video.mp4"))

    def test_write_metadata_nonexistent_file(self) -> None:
        """Test write_metadata raises for non-existent file."""
        runner = ExifToolRunner()
        with pytest.raises(FileNotFoundError):
            runner.write_metadata(Path("/nonexistent/video.mp4"), {"Title": "Test"})

    def test_copy_metadata_nonexistent_source(self) -> None:
        """Test copy_metadata raises for non-existent source."""
        runner = ExifToolRunner()
        with pytest.raises(FileNotFoundError):
            runner.copy_metadata(
                Path("/nonexistent/source.mp4"),
                Path("/nonexistent/dest.mp4"),
            )

    def test_quick_check_nonexistent_file(self) -> None:
        """Test quick_check returns False for non-existent file."""
        runner = ExifToolRunner()
        result = runner.quick_check(Path("/nonexistent/video.mp4"))
        assert result is False

    def test_read_metadata_with_mock(self) -> None:
        """Test read_metadata with mocked ExifTool output."""
        runner = ExifToolRunner()
        mock_output = [
            {
                "SourceFile": "test.mp4",
                "CreateDate": "2024:01:15 10:30:00",
                "GPSLatitude": 37.5665,
                "GPSLongitude": 126.9780,
            }
        ]

        with patch.object(runner._runner, "run") as mock_run:
            import json
            mock_run.return_value = CommandResult(
                returncode=0,
                stdout=json.dumps(mock_output),
                stderr="",
            )
            with patch.object(Path, "exists", return_value=True):
                result = runner.read_metadata(Path("test.mp4"))
                assert "CreateDate" in result
                assert result["CreateDate"] == "2024:01:15 10:30:00"


class TestExifToolRunnerAsync:
    """Async tests for ExifToolRunner."""

    @pytest.mark.asyncio
    async def test_read_metadata_async_nonexistent_file(self) -> None:
        """Test read_metadata_async raises for non-existent file."""
        runner = ExifToolRunner()
        with pytest.raises(FileNotFoundError):
            await runner.read_metadata_async(Path("/nonexistent/video.mp4"))


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_run_command_success(self) -> None:
        """Test run_command with successful command."""
        result = run_command(["echo", "test"])
        assert result.success
        assert "test" in result.stdout

    def test_run_command_failure(self) -> None:
        """Test run_command with failing command."""
        result = run_command(["ls", "/nonexistent_path_xyz"])
        assert not result.success

    def test_run_command_not_found(self) -> None:
        """Test run_command with non-existent command."""
        with pytest.raises(CommandNotFoundError):
            run_command(["nonexistent_command_xyz"])

    def test_run_command_with_callback(self) -> None:
        """Test run_command with output callback."""
        lines: list[str] = []
        result = run_command(["echo", "hello"], on_output=lines.append)
        assert result.success

    def test_run_ffprobe_nonexistent_file(self) -> None:
        """Test run_ffprobe with non-existent file."""
        with pytest.raises(FileNotFoundError):
            run_ffprobe("/nonexistent/video.mp4")

    def test_run_exiftool_nonexistent_file(self) -> None:
        """Test run_exiftool with non-existent file."""
        with pytest.raises(FileNotFoundError):
            run_exiftool("/nonexistent/video.mp4")
