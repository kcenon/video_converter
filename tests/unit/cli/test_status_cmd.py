"""Tests for the 'status' CLI command.

This module tests the video-converter status command including:
- Service status display
- Various service states (installed, running, error)
- Status information formatting
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from video_converter.__main__ import main
from video_converter.automation import ServiceState


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Click CLI test runner."""
    return CliRunner()


class TestStatusCommand:
    """Tests for the status command."""

    @patch("video_converter.__main__.ServiceManager")
    def test_status_not_installed(
        self,
        mock_manager_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test status display when service is not installed."""
        mock_status = MagicMock()
        mock_status.state = ServiceState.NOT_INSTALLED
        mock_status.is_installed = False
        mock_status.pid = None
        mock_status.schedule = None
        mock_status.last_exit_status = None

        mock_detailed = MagicMock()
        mock_detailed.basic_status = mock_status
        mock_detailed.next_run_relative = "Not scheduled"
        mock_detailed.last_run = MagicMock()
        mock_detailed.last_run.timestamp = None
        mock_detailed.total_videos_converted = 0
        mock_detailed.total_storage_saved_bytes = 0

        mock_manager = MagicMock()
        mock_manager.get_detailed_status.return_value = mock_detailed
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(main, ["status"])

        assert result.exit_code == 0
        assert "Not Installed" in result.output

    @patch("video_converter.__main__.ServiceManager")
    def test_status_running(
        self,
        mock_manager_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test status display when service is running."""
        mock_status = MagicMock()
        mock_status.state = ServiceState.INSTALLED_RUNNING
        mock_status.is_installed = True
        mock_status.pid = 12345
        mock_status.schedule = "Daily at 03:00"
        mock_status.last_exit_status = 0

        mock_detailed = MagicMock()
        mock_detailed.basic_status = mock_status
        mock_detailed.next_run_relative = "in 8 hours"
        mock_detailed.last_run = MagicMock()
        mock_detailed.last_run.timestamp = "2024-01-01 03:00:00"
        mock_detailed.last_run.relative_time = "8 hours ago"
        mock_detailed.last_run.result_text = "Success"
        mock_detailed.total_videos_converted = 50
        mock_detailed.total_storage_saved_bytes = 5_000_000_000

        mock_manager = MagicMock()
        mock_manager.get_detailed_status.return_value = mock_detailed
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(main, ["status"])

        assert result.exit_code == 0
        assert "Running" in result.output
        assert "12345" in result.output

    @patch("video_converter.__main__.ServiceManager")
    def test_status_installed_idle(
        self,
        mock_manager_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test status display when service is installed but idle."""
        mock_status = MagicMock()
        mock_status.state = ServiceState.INSTALLED_IDLE
        mock_status.is_installed = True
        mock_status.pid = None
        mock_status.schedule = "Daily at 03:00"
        mock_status.last_exit_status = 0

        mock_detailed = MagicMock()
        mock_detailed.basic_status = mock_status
        mock_detailed.next_run_relative = "in 8 hours"
        mock_detailed.last_run = MagicMock()
        mock_detailed.last_run.timestamp = None
        mock_detailed.total_videos_converted = 0
        mock_detailed.total_storage_saved_bytes = 0

        mock_manager = MagicMock()
        mock_manager.get_detailed_status.return_value = mock_detailed
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(main, ["status"])

        assert result.exit_code == 0
        assert "Installed" in result.output or "Idle" in result.output

    @patch("video_converter.__main__.ServiceManager")
    def test_status_error(
        self,
        mock_manager_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test status display when service has error."""
        mock_status = MagicMock()
        mock_status.state = ServiceState.INSTALLED_ERROR
        mock_status.is_installed = True
        mock_status.pid = None
        mock_status.schedule = "Daily at 03:00"
        mock_status.last_exit_status = 1

        mock_detailed = MagicMock()
        mock_detailed.basic_status = mock_status
        mock_detailed.next_run_relative = "in 8 hours"
        mock_detailed.last_run = MagicMock()
        mock_detailed.last_run.timestamp = "2024-01-01 03:00:00"
        mock_detailed.last_run.relative_time = "8 hours ago"
        mock_detailed.last_run.result_text = "Failed"
        mock_detailed.total_videos_converted = 10
        mock_detailed.total_storage_saved_bytes = 1_000_000_000

        mock_manager = MagicMock()
        mock_manager.get_detailed_status.return_value = mock_detailed
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(main, ["status"])

        assert result.exit_code == 0
        assert "Error" in result.output

    @patch("video_converter.__main__.ServiceManager")
    def test_status_shows_schedule(
        self,
        mock_manager_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test that status shows schedule information."""
        mock_status = MagicMock()
        mock_status.state = ServiceState.INSTALLED_IDLE
        mock_status.is_installed = True
        mock_status.pid = None
        mock_status.schedule = "Every Monday at 03:00"
        mock_status.last_exit_status = None

        mock_detailed = MagicMock()
        mock_detailed.basic_status = mock_status
        mock_detailed.next_run_relative = "in 3 days"
        mock_detailed.last_run = MagicMock()
        mock_detailed.last_run.timestamp = None
        mock_detailed.total_videos_converted = 0
        mock_detailed.total_storage_saved_bytes = 0

        mock_manager = MagicMock()
        mock_manager.get_detailed_status.return_value = mock_detailed
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(main, ["status"])

        assert result.exit_code == 0
        assert "Monday" in result.output or "Schedule" in result.output
