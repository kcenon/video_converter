"""Unit tests for command_runner module."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_converter.utils.command_runner import (
    CommandExecutionError,
    CommandNotFoundError,
    CommandResult,
    CommandRunner,
    FFprobeRunner,
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
        mock_output = {
            "format": {
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
                "duration": "10.5",
                "size": "1048576",
                "bit_rate": "800000",
            },
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30/1",
                }
            ],
        }

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
