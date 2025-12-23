"""Tests for service-related CLI commands.

This module tests the video-converter service commands including:
- install-service: Install launchd service
- uninstall-service: Remove launchd service
- service-start/stop/restart: Control service
- service-load/unload: Load/unload from launchd
- service-logs: View service logs
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from video_converter.__main__ import main
from video_converter.automation import ServiceState


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_service_manager() -> MagicMock:
    """Create a mock ServiceManager."""
    mock = MagicMock()

    # Mock status
    mock_status = MagicMock()
    mock_status.state = ServiceState.NOT_INSTALLED
    mock_status.is_installed = False
    mock_status.is_running = False
    mock_status.plist_path = None
    mock.get_status.return_value = mock_status

    # Mock operation result
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.message = "Operation completed"
    mock_result.error = None
    mock_result.plist_path = Path("/tmp/test.plist")

    mock.install.return_value = mock_result
    mock.uninstall.return_value = mock_result
    mock.start.return_value = mock_result
    mock.stop.return_value = mock_result
    mock.load.return_value = mock_result
    mock.unload.return_value = mock_result
    mock.restart.return_value = mock_result

    # Mock log paths
    mock.get_log_paths.return_value = (
        Path("/tmp/stdout.log"),
        Path("/tmp/stderr.log"),
    )
    mock.read_logs.return_value = {"stdout": "", "stderr": ""}

    return mock


class TestInstallServiceCommand:
    """Tests for the install-service command."""

    def test_install_service_shows_help(self, cli_runner: CliRunner) -> None:
        """Test that install-service --help shows usage information."""
        result = cli_runner.invoke(main, ["install-service", "--help"])

        assert result.exit_code == 0
        assert "Install launchd" in result.output
        assert "--time" in result.output
        assert "--weekday" in result.output
        assert "--watch" in result.output

    @patch("video_converter.__main__.ServiceManager")
    def test_install_service_default(
        self,
        mock_manager_class: MagicMock,
        cli_runner: CliRunner,
        mock_service_manager: MagicMock,
    ) -> None:
        """Test basic service installation."""
        mock_manager_class.return_value = mock_service_manager

        result = cli_runner.invoke(main, ["install-service"])

        assert result.exit_code == 0 or "Operation completed" in result.output

    @patch("video_converter.__main__.ServiceManager")
    def test_install_service_custom_time(
        self,
        mock_manager_class: MagicMock,
        cli_runner: CliRunner,
        mock_service_manager: MagicMock,
    ) -> None:
        """Test installation with custom time."""
        mock_manager_class.return_value = mock_service_manager

        result = cli_runner.invoke(main, ["install-service", "--time", "02:30"])

        assert result.exit_code == 0 or "Operation completed" in result.output

    def test_install_service_invalid_time(self, cli_runner: CliRunner) -> None:
        """Test that invalid time format is rejected."""
        result = cli_runner.invoke(main, ["install-service", "--time", "25:00"])

        # Should fail due to invalid hour
        assert result.exit_code != 0 or "Hour must be" in result.output

    @patch("video_converter.__main__.ServiceManager")
    def test_install_service_with_weekday(
        self,
        mock_manager_class: MagicMock,
        cli_runner: CliRunner,
        mock_service_manager: MagicMock,
    ) -> None:
        """Test installation with weekday schedule."""
        mock_manager_class.return_value = mock_service_manager

        result = cli_runner.invoke(main, [
            "install-service",
            "--time", "04:00",
            "--weekday", "1",  # Monday
        ])

        assert result.exit_code == 0 or "Operation completed" in result.output

    @patch("video_converter.__main__.ServiceManager")
    def test_install_service_run_now(
        self,
        mock_manager_class: MagicMock,
        cli_runner: CliRunner,
        mock_service_manager: MagicMock,
    ) -> None:
        """Test installation with immediate run."""
        mock_manager_class.return_value = mock_service_manager

        result = cli_runner.invoke(main, ["install-service", "--run-now"])

        assert result.exit_code == 0 or "immediately" in result.output.lower()

    @patch("video_converter.__main__.ServiceManager")
    def test_install_service_failure(
        self,
        mock_manager_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test handling of installation failure."""
        mock_manager = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.message = "Installation failed"
        mock_result.error = "Permission denied"
        mock_manager.install.return_value = mock_result
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(main, ["install-service"])

        assert result.exit_code == 1


class TestUninstallServiceCommand:
    """Tests for the uninstall-service command."""

    def test_uninstall_service_shows_help(self, cli_runner: CliRunner) -> None:
        """Test that uninstall-service --help shows usage information."""
        result = cli_runner.invoke(main, ["uninstall-service", "--help"])

        assert result.exit_code == 0
        assert "Remove launchd" in result.output
        assert "--remove-logs" in result.output
        assert "--yes" in result.output

    @patch("video_converter.__main__.ServiceManager")
    def test_uninstall_not_installed(
        self,
        mock_manager_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test uninstall when service is not installed."""
        mock_manager = MagicMock()
        mock_status = MagicMock()
        mock_status.is_installed = False
        mock_manager.get_status.return_value = mock_status
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(main, ["uninstall-service", "--yes"])

        assert "not installed" in result.output.lower()

    @patch("video_converter.__main__.ServiceManager")
    def test_uninstall_with_confirmation_skip(
        self,
        mock_manager_class: MagicMock,
        cli_runner: CliRunner,
        mock_service_manager: MagicMock,
    ) -> None:
        """Test uninstall with --yes flag."""
        mock_service_manager.get_status.return_value.is_installed = True
        mock_service_manager.get_status.return_value.plist_path = "/tmp/test.plist"
        mock_manager_class.return_value = mock_service_manager

        result = cli_runner.invoke(main, ["uninstall-service", "--yes"])

        assert result.exit_code == 0 or "completed" in result.output.lower()


class TestServiceControlCommands:
    """Tests for service control commands."""

    @patch("video_converter.__main__.ServiceManager")
    def test_service_start(
        self,
        mock_manager_class: MagicMock,
        cli_runner: CliRunner,
        mock_service_manager: MagicMock,
    ) -> None:
        """Test service-start command."""
        mock_manager_class.return_value = mock_service_manager

        result = cli_runner.invoke(main, ["service-start"])

        assert result.exit_code == 0

    @patch("video_converter.__main__.ServiceManager")
    def test_service_stop(
        self,
        mock_manager_class: MagicMock,
        cli_runner: CliRunner,
        mock_service_manager: MagicMock,
    ) -> None:
        """Test service-stop command."""
        mock_manager_class.return_value = mock_service_manager

        result = cli_runner.invoke(main, ["service-stop"])

        assert result.exit_code == 0

    @patch("video_converter.__main__.ServiceManager")
    def test_service_restart(
        self,
        mock_manager_class: MagicMock,
        cli_runner: CliRunner,
        mock_service_manager: MagicMock,
    ) -> None:
        """Test service-restart command."""
        mock_manager_class.return_value = mock_service_manager

        result = cli_runner.invoke(main, ["service-restart"])

        assert result.exit_code == 0

    @patch("video_converter.__main__.ServiceManager")
    def test_service_load(
        self,
        mock_manager_class: MagicMock,
        cli_runner: CliRunner,
        mock_service_manager: MagicMock,
    ) -> None:
        """Test service-load command."""
        mock_manager_class.return_value = mock_service_manager

        result = cli_runner.invoke(main, ["service-load"])

        assert result.exit_code == 0

    @patch("video_converter.__main__.ServiceManager")
    def test_service_unload(
        self,
        mock_manager_class: MagicMock,
        cli_runner: CliRunner,
        mock_service_manager: MagicMock,
    ) -> None:
        """Test service-unload command."""
        mock_manager_class.return_value = mock_service_manager

        result = cli_runner.invoke(main, ["service-unload"])

        assert result.exit_code == 0

    @patch("video_converter.__main__.ServiceManager")
    def test_service_control_failure(
        self,
        mock_manager_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test handling of service control failure."""
        mock_manager = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.message = "Service not found"
        mock_result.error = "launchd error"
        mock_manager.start.return_value = mock_result
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(main, ["service-start"])

        assert result.exit_code == 1


class TestServiceLogsCommand:
    """Tests for the service-logs command."""

    def test_service_logs_shows_help(self, cli_runner: CliRunner) -> None:
        """Test that service-logs --help shows usage information."""
        result = cli_runner.invoke(main, ["service-logs", "--help"])

        assert result.exit_code == 0
        assert "--lines" in result.output
        assert "--follow" in result.output
        assert "--stderr" in result.output

    @patch("video_converter.__main__.ServiceManager")
    def test_service_logs_no_file(
        self,
        mock_manager_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test service-logs when log file doesn't exist."""
        mock_manager = MagicMock()
        mock_manager.get_log_paths.return_value = (
            Path("/nonexistent/stdout.log"),
            Path("/nonexistent/stderr.log"),
        )
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(main, ["service-logs"])

        assert "No" in result.output or "log file" in result.output.lower()

    @patch("video_converter.__main__.ServiceManager")
    def test_service_logs_with_lines_option(
        self,
        mock_manager_class: MagicMock,
        cli_runner: CliRunner,
        temp_dir: Path,
    ) -> None:
        """Test service-logs with custom line count."""
        log_file = temp_dir / "stdout.log"
        log_file.write_text("line1\nline2\nline3\n")

        mock_manager = MagicMock()
        mock_manager.get_log_paths.return_value = (log_file, temp_dir / "stderr.log")
        mock_manager.read_logs.return_value = {"stdout": "line1\nline2\nline3\n", "stderr": ""}
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(main, ["service-logs", "-n", "10"])

        assert result.exit_code == 0


class TestServiceStatusCommand:
    """Tests for the service-status command."""

    def test_service_status_shows_help(self, cli_runner: CliRunner) -> None:
        """Test that service-status --help shows usage information."""
        result = cli_runner.invoke(main, ["service-status", "--help"])

        assert result.exit_code == 0
        assert "status" in result.output.lower()
