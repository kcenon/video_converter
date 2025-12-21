"""Unit tests for ServiceManager class."""

from __future__ import annotations

import plistlib
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_converter.automation.launchd import SERVICE_LABEL
from video_converter.automation.service_manager import (
    ServiceManager,
    ServiceResult,
    ServiceState,
    ServiceStatus,
)


class TestServiceStatus:
    """Tests for ServiceStatus dataclass."""

    def test_not_installed_status(self) -> None:
        """Test status for uninstalled service."""
        status = ServiceStatus(
            state=ServiceState.NOT_INSTALLED,
            is_installed=False,
            is_loaded=False,
            is_running=False,
        )
        assert status.state == ServiceState.NOT_INSTALLED
        assert not status.is_installed
        assert not status.is_loaded
        assert not status.is_running
        assert status.pid is None
        assert status.plist_path is None

    def test_installed_idle_status(self) -> None:
        """Test status for installed but idle service."""
        status = ServiceStatus(
            state=ServiceState.INSTALLED_IDLE,
            is_installed=True,
            is_loaded=True,
            is_running=False,
            plist_path=Path("/test/path.plist"),
            schedule="Daily at 03:00",
        )
        assert status.state == ServiceState.INSTALLED_IDLE
        assert status.is_installed
        assert status.is_loaded
        assert not status.is_running
        assert status.schedule == "Daily at 03:00"

    def test_running_status(self) -> None:
        """Test status for running service."""
        status = ServiceStatus(
            state=ServiceState.INSTALLED_RUNNING,
            is_installed=True,
            is_loaded=True,
            is_running=True,
            pid=12345,
        )
        assert status.state == ServiceState.INSTALLED_RUNNING
        assert status.is_running
        assert status.pid == 12345


class TestServiceResult:
    """Tests for ServiceResult dataclass."""

    def test_success_result(self) -> None:
        """Test successful result."""
        result = ServiceResult(
            success=True,
            message="Service installed successfully",
            plist_path=Path("/test/path.plist"),
        )
        assert result.success
        assert result.error is None
        assert result.plist_path is not None

    def test_failure_result(self) -> None:
        """Test failure result."""
        result = ServiceResult(
            success=False,
            message="Failed to install service",
            error="Permission denied",
        )
        assert not result.success
        assert result.error == "Permission denied"


class TestServiceManager:
    """Tests for ServiceManager class."""

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_dir: Path) -> ServiceManager:
        """Create a ServiceManager with temporary paths."""
        plist_path = temp_dir / "test.plist"
        log_dir = temp_dir / "logs"
        return ServiceManager(plist_path=plist_path, log_dir=log_dir)

    def test_initialization_default(self) -> None:
        """Test manager with default settings."""
        manager = ServiceManager()
        assert manager.plist_path.name == "com.videoconverter.daily.plist"
        assert "LaunchAgents" in str(manager.plist_path)

    def test_initialization_custom_paths(self, temp_dir: Path) -> None:
        """Test manager with custom paths."""
        plist_path = temp_dir / "custom.plist"
        log_dir = temp_dir / "custom_logs"

        manager = ServiceManager(plist_path=plist_path, log_dir=log_dir)

        assert manager.plist_path == plist_path
        assert manager.log_dir == log_dir

    def test_get_status_not_installed(self, manager: ServiceManager) -> None:
        """Test status when service is not installed."""
        status = manager.get_status()

        assert status.state == ServiceState.NOT_INSTALLED
        assert not status.is_installed
        assert not status.is_loaded

    @patch("subprocess.run")
    def test_get_status_installed_idle(
        self, mock_run: MagicMock, manager: ServiceManager
    ) -> None:
        """Test status when service is installed but idle."""
        # Create plist file
        plist = {
            "Label": SERVICE_LABEL,
            "StartCalendarInterval": {"Hour": 3, "Minute": 0},
        }
        with manager.plist_path.open("wb") as f:
            plistlib.dump(plist, f)

        # Mock launchctl list output (service loaded but not running)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=f"-\t0\t{SERVICE_LABEL}\n",
        )

        status = manager.get_status()

        assert status.is_installed
        assert status.is_loaded
        assert not status.is_running
        assert status.state == ServiceState.INSTALLED_IDLE
        assert "Daily" in (status.schedule or "")

    @patch("subprocess.run")
    def test_get_status_running(
        self, mock_run: MagicMock, manager: ServiceManager
    ) -> None:
        """Test status when service is running."""
        # Create plist file
        plist = {"Label": SERVICE_LABEL}
        manager.plist_path.parent.mkdir(parents=True, exist_ok=True)
        with manager.plist_path.open("wb") as f:
            plistlib.dump(plist, f)

        # Mock launchctl list output (service running with PID)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=f"12345\t0\t{SERVICE_LABEL}\n",
        )

        status = manager.get_status()

        assert status.is_running
        assert status.pid == 12345
        assert status.state == ServiceState.INSTALLED_RUNNING

    @patch("subprocess.run")
    def test_install_success(
        self, mock_run: MagicMock, manager: ServiceManager
    ) -> None:
        """Test successful service installation."""
        # Mock all subprocess calls to succeed
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = manager.install(hour=3, minute=0)

        assert result.success
        assert manager.plist_path.exists()
        assert result.plist_path == manager.plist_path

        # Verify plist content
        with manager.plist_path.open("rb") as f:
            plist = plistlib.load(f)
        assert plist["Label"] == SERVICE_LABEL
        assert plist["StartCalendarInterval"]["Hour"] == 3

    @patch("subprocess.run")
    def test_install_already_installed(
        self, mock_run: MagicMock, manager: ServiceManager
    ) -> None:
        """Test installation when service already exists."""
        # Create existing plist
        plist = {"Label": SERVICE_LABEL}
        manager.plist_path.parent.mkdir(parents=True, exist_ok=True)
        with manager.plist_path.open("wb") as f:
            plistlib.dump(plist, f)

        # Mock launchctl list to show service is loaded
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=f"-\t0\t{SERVICE_LABEL}\n",
        )

        result = manager.install(hour=3, minute=0, force=False)

        assert not result.success
        assert "already installed" in result.message

    @patch("subprocess.run")
    def test_install_force_reinstall(
        self, mock_run: MagicMock, manager: ServiceManager
    ) -> None:
        """Test force reinstallation."""
        # Create existing plist
        plist = {"Label": SERVICE_LABEL}
        manager.plist_path.parent.mkdir(parents=True, exist_ok=True)
        with manager.plist_path.open("wb") as f:
            plistlib.dump(plist, f)

        # Mock all subprocess calls to succeed
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = manager.install(hour=4, minute=30, force=True)

        assert result.success

        # Verify new schedule
        with manager.plist_path.open("rb") as f:
            plist = plistlib.load(f)
        assert plist["StartCalendarInterval"]["Hour"] == 4
        assert plist["StartCalendarInterval"]["Minute"] == 30

    @patch("subprocess.run")
    def test_install_with_watch_paths(
        self, mock_run: MagicMock, manager: ServiceManager, temp_dir: Path
    ) -> None:
        """Test installation with folder watching."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        watch_folder = temp_dir / "watch"
        watch_folder.mkdir()

        result = manager.install(hour=None, watch_paths=[watch_folder])

        assert result.success

        with manager.plist_path.open("rb") as f:
            plist = plistlib.load(f)
        assert "WatchPaths" in plist
        # Compare resolved paths (macOS symlink /var -> /private/var)
        resolved_watch = str(watch_folder.resolve())
        assert any(resolved_watch in wp or wp in resolved_watch
                   for wp in plist["WatchPaths"])

    @patch("subprocess.run")
    def test_uninstall_success(
        self, mock_run: MagicMock, manager: ServiceManager
    ) -> None:
        """Test successful uninstallation."""
        # Create plist file
        plist = {"Label": SERVICE_LABEL}
        manager.plist_path.parent.mkdir(parents=True, exist_ok=True)
        with manager.plist_path.open("wb") as f:
            plistlib.dump(plist, f)

        # Mock launchctl calls
        def mock_subprocess(cmd, **kwargs):
            if "list" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout=f"-\t0\t{SERVICE_LABEL}\n",
                )
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_subprocess

        result = manager.uninstall()

        assert result.success
        assert not manager.plist_path.exists()

    def test_uninstall_not_installed(self, manager: ServiceManager) -> None:
        """Test uninstallation when service is not installed."""
        result = manager.uninstall()

        assert result.success
        assert "not installed" in result.message

    @patch("subprocess.run")
    def test_uninstall_with_logs(
        self, mock_run: MagicMock, manager: ServiceManager
    ) -> None:
        """Test uninstallation with log removal."""
        # Create plist and log files
        plist = {"Label": SERVICE_LABEL}
        manager.plist_path.parent.mkdir(parents=True, exist_ok=True)
        with manager.plist_path.open("wb") as f:
            plistlib.dump(plist, f)

        manager.log_dir.mkdir(parents=True, exist_ok=True)
        (manager.log_dir / "stdout.log").write_text("test log")
        (manager.log_dir / "stderr.log").write_text("test error")

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = manager.uninstall(remove_logs=True)

        assert result.success
        assert not (manager.log_dir / "stdout.log").exists()
        assert not (manager.log_dir / "stderr.log").exists()

    @patch("subprocess.run")
    def test_start_service(
        self, mock_run: MagicMock, manager: ServiceManager
    ) -> None:
        """Test manual service start."""
        # Create plist file
        plist = {"Label": SERVICE_LABEL}
        manager.plist_path.parent.mkdir(parents=True, exist_ok=True)
        with manager.plist_path.open("wb") as f:
            plistlib.dump(plist, f)

        # Mock subprocess calls
        def mock_subprocess(cmd, **kwargs):
            if "list" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout=f"-\t0\t{SERVICE_LABEL}\n",
                )
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_subprocess

        result = manager.start()

        assert result.success

    def test_start_not_installed(self, manager: ServiceManager) -> None:
        """Test start when service is not installed."""
        result = manager.start()

        assert not result.success
        assert "not installed" in result.message

    @patch("subprocess.run")
    def test_stop_service(
        self, mock_run: MagicMock, manager: ServiceManager
    ) -> None:
        """Test service stop."""
        # Create plist file
        plist = {"Label": SERVICE_LABEL}
        manager.plist_path.parent.mkdir(parents=True, exist_ok=True)
        with manager.plist_path.open("wb") as f:
            plistlib.dump(plist, f)

        # Mock subprocess calls to show running service
        def mock_subprocess(cmd, **kwargs):
            if "list" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout=f"12345\t0\t{SERVICE_LABEL}\n",
                )
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_subprocess

        result = manager.stop()

        assert result.success

    def test_stop_not_running(self, manager: ServiceManager) -> None:
        """Test stop when service is not running."""
        result = manager.stop()

        assert result.success
        assert "not running" in result.message

    def test_get_log_paths(self, manager: ServiceManager) -> None:
        """Test getting log file paths."""
        stdout_path, stderr_path = manager.get_log_paths()

        assert stdout_path.name == "stdout.log"
        assert stderr_path.name == "stderr.log"
        assert stdout_path.parent == manager.log_dir

    def test_read_logs_empty(self, manager: ServiceManager) -> None:
        """Test reading logs when files don't exist."""
        logs = manager.read_logs()

        assert logs["stdout"] == ""
        assert logs["stderr"] == ""

    def test_read_logs_with_content(self, manager: ServiceManager) -> None:
        """Test reading logs with content."""
        manager.log_dir.mkdir(parents=True, exist_ok=True)

        stdout_content = "Line 1\nLine 2\nLine 3"
        stderr_content = "Error 1\nError 2"

        (manager.log_dir / "stdout.log").write_text(stdout_content)
        (manager.log_dir / "stderr.log").write_text(stderr_content)

        logs = manager.read_logs()

        assert "Line 1" in logs["stdout"]
        assert "Error 1" in logs["stderr"]


class TestScheduleDescription:
    """Tests for schedule description building."""

    @pytest.fixture
    def manager(self) -> ServiceManager:
        """Create a ServiceManager for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield ServiceManager(
                plist_path=Path(tmpdir) / "test.plist",
                log_dir=Path(tmpdir) / "logs",
            )

    def test_daily_schedule_description(self, manager: ServiceManager) -> None:
        """Test description for daily schedule."""
        desc = manager._build_schedule_description(
            hour=3, minute=0, weekday=None, watch_paths=None
        )
        assert "Daily" in desc
        assert "03:00" in desc

    def test_weekly_schedule_description(self, manager: ServiceManager) -> None:
        """Test description for weekly schedule."""
        desc = manager._build_schedule_description(
            hour=9, minute=30, weekday=1, watch_paths=None
        )
        assert "Monday" in desc
        assert "09:30" in desc

    def test_watch_paths_description(self, manager: ServiceManager) -> None:
        """Test description with watch paths."""
        desc = manager._build_schedule_description(
            hour=None,
            minute=0,
            weekday=None,
            watch_paths=[Path("/path/to/folder")],
        )
        assert "Watching" in desc

    def test_combined_schedule_description(self, manager: ServiceManager) -> None:
        """Test description with both schedule and watch paths."""
        desc = manager._build_schedule_description(
            hour=3,
            minute=0,
            weekday=None,
            watch_paths=[Path("/path/to/folder")],
        )
        assert "Daily" in desc
        assert "Watching" in desc
