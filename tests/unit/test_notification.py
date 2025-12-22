"""Unit tests for macOS Notification Center integration."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_converter.automation.notification import (
    NotificationConfig,
    NotificationManager,
    NotificationResult,
    NotificationType,
    _format_size,
    send_notification,
)
from video_converter.core.types import ConversionReport, ConversionRequest, ConversionResult


class TestNotificationType:
    """Tests for NotificationType enum."""

    def test_success_type(self) -> None:
        """Test SUCCESS notification type."""
        assert NotificationType.SUCCESS.value == "success"

    def test_partial_type(self) -> None:
        """Test PARTIAL notification type."""
        assert NotificationType.PARTIAL.value == "partial"

    def test_failure_type(self) -> None:
        """Test FAILURE notification type."""
        assert NotificationType.FAILURE.value == "failure"

    def test_info_type(self) -> None:
        """Test INFO notification type."""
        assert NotificationType.INFO.value == "info"


class TestNotificationConfig:
    """Tests for NotificationConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = NotificationConfig()
        assert config.enabled is True
        assert config.sound is True
        assert config.sound_name == "Glass"
        assert config.group_id == "com.videoconverter"

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = NotificationConfig(
            enabled=False,
            sound=False,
            sound_name="Pop",
            group_id="custom.app",
        )
        assert config.enabled is False
        assert config.sound is False
        assert config.sound_name == "Pop"
        assert config.group_id == "custom.app"


class TestNotificationResult:
    """Tests for NotificationResult dataclass."""

    def test_success_result(self) -> None:
        """Test successful result."""
        result = NotificationResult(success=True)
        assert result.success is True
        assert result.error_message is None

    def test_failure_result(self) -> None:
        """Test failure result with error message."""
        result = NotificationResult(
            success=False,
            error_message="Connection failed",
        )
        assert result.success is False
        assert result.error_message == "Connection failed"


class TestFormatSize:
    """Tests for _format_size helper function."""

    def test_bytes(self) -> None:
        """Test formatting bytes."""
        assert _format_size(500) == "500 B"

    def test_kilobytes(self) -> None:
        """Test formatting kilobytes."""
        assert _format_size(1024) == "1.0 KB"
        assert _format_size(2048) == "2.0 KB"

    def test_megabytes(self) -> None:
        """Test formatting megabytes."""
        assert _format_size(1024 * 1024) == "1.0 MB"
        assert _format_size(5 * 1024 * 1024) == "5.0 MB"

    def test_gigabytes(self) -> None:
        """Test formatting gigabytes."""
        assert _format_size(1024 * 1024 * 1024) == "1.0 GB"
        assert _format_size(int(8.5 * 1024 * 1024 * 1024)) == "8.5 GB"


class TestNotificationManager:
    """Tests for NotificationManager class."""

    def test_initialization_default(self) -> None:
        """Test manager with default configuration."""
        manager = NotificationManager()
        assert manager.config.enabled is True
        assert manager.config.sound is True

    def test_initialization_custom(self) -> None:
        """Test manager with custom configuration."""
        config = NotificationConfig(enabled=False, sound=False)
        manager = NotificationManager(config=config)
        assert manager.config.enabled is False
        assert manager.config.sound is False

    @patch("video_converter.automation.notification.platform.system")
    def test_is_available_on_macos(self, mock_system: MagicMock) -> None:
        """Test is_available returns True on macOS."""
        mock_system.return_value = "Darwin"
        manager = NotificationManager()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert manager.is_available() is True

    @patch("video_converter.automation.notification.platform.system")
    def test_is_available_on_linux(self, mock_system: MagicMock) -> None:
        """Test is_available returns False on Linux."""
        mock_system.return_value = "Linux"
        manager = NotificationManager()
        assert manager.is_available() is False

    @patch("video_converter.automation.notification.platform.system")
    def test_is_available_when_disabled(self, mock_system: MagicMock) -> None:
        """Test is_available returns False when disabled."""
        mock_system.return_value = "Darwin"
        config = NotificationConfig(enabled=False)
        manager = NotificationManager(config=config)
        assert manager.is_available() is False

    def test_send_notification_disabled(self) -> None:
        """Test sending notification when disabled."""
        config = NotificationConfig(enabled=False)
        manager = NotificationManager(config=config)
        result = manager.send_notification("Title", "Body")
        assert result.success is True  # Success because disabled (no-op)

    @patch("video_converter.automation.notification.platform.system")
    def test_send_notification_non_macos(self, mock_system: MagicMock) -> None:
        """Test sending notification on non-macOS platform."""
        mock_system.return_value = "Linux"
        manager = NotificationManager()
        result = manager.send_notification("Title", "Body")
        assert result.success is False
        assert "only supported on macOS" in result.error_message

    @patch("video_converter.automation.notification.platform.system")
    @patch("subprocess.run")
    def test_send_notification_success(
        self,
        mock_run: MagicMock,
        mock_system: MagicMock,
    ) -> None:
        """Test successful notification sending."""
        mock_system.return_value = "Darwin"
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        manager = NotificationManager()
        result = manager.send_notification("Test Title", "Test Body")
        assert result.success is True
        mock_run.assert_called_once()

    @patch("video_converter.automation.notification.platform.system")
    @patch("subprocess.run")
    def test_send_notification_with_sound(
        self,
        mock_run: MagicMock,
        mock_system: MagicMock,
    ) -> None:
        """Test notification includes sound in AppleScript."""
        mock_system.return_value = "Darwin"
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        manager = NotificationManager()
        manager.send_notification("Title", "Body", sound=True)

        call_args = mock_run.call_args[0][0]
        script = call_args[2]  # osascript -e <script>
        assert "sound name" in script

    @patch("video_converter.automation.notification.platform.system")
    @patch("subprocess.run")
    def test_send_notification_without_sound(
        self,
        mock_run: MagicMock,
        mock_system: MagicMock,
    ) -> None:
        """Test notification without sound."""
        mock_system.return_value = "Darwin"
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        manager = NotificationManager()
        manager.send_notification("Title", "Body", sound=False)

        call_args = mock_run.call_args[0][0]
        script = call_args[2]
        assert "sound name" not in script

    @patch("video_converter.automation.notification.platform.system")
    @patch("subprocess.run")
    def test_send_notification_escapes_quotes(
        self,
        mock_run: MagicMock,
        mock_system: MagicMock,
    ) -> None:
        """Test that quotes in title/body are escaped."""
        mock_system.return_value = "Darwin"
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        manager = NotificationManager()
        manager.send_notification('Title with "quotes"', 'Body with "quotes"')

        call_args = mock_run.call_args[0][0]
        script = call_args[2]
        assert '\\"' in script

    @patch("video_converter.automation.notification.platform.system")
    @patch("subprocess.run")
    def test_send_notification_failure(
        self,
        mock_run: MagicMock,
        mock_system: MagicMock,
    ) -> None:
        """Test handling osascript failure."""
        mock_system.return_value = "Darwin"
        mock_run.return_value = MagicMock(returncode=1, stderr="Error message")
        manager = NotificationManager()
        result = manager.send_notification("Title", "Body")
        assert result.success is False
        assert result.error_message == "Error message"

    @patch("video_converter.automation.notification.platform.system")
    @patch("subprocess.run")
    def test_send_notification_timeout(
        self,
        mock_run: MagicMock,
        mock_system: MagicMock,
    ) -> None:
        """Test handling timeout."""
        import subprocess
        mock_system.return_value = "Darwin"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="osascript", timeout=10)
        manager = NotificationManager()
        result = manager.send_notification("Title", "Body")
        assert result.success is False
        assert "timed out" in result.error_message


class TestNotificationManagerBatch:
    """Tests for NotificationManager batch notification methods."""

    def _create_report(
        self,
        successful: int = 0,
        failed: int = 0,
        cancelled: bool = False,
        size_saved: int = 0,
    ) -> ConversionReport:
        """Create a test ConversionReport."""
        report = ConversionReport(
            session_id="test-session",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            total_files=successful + failed,
            successful=successful,
            failed=failed,
            cancelled=cancelled,
            total_original_size=size_saved * 2 if size_saved else 0,
            total_converted_size=size_saved if size_saved else 0,
        )
        return report

    def test_determine_notification_type_success(self) -> None:
        """Test type determination for full success."""
        manager = NotificationManager()
        report = self._create_report(successful=10, failed=0)
        notification_type = manager._determine_notification_type(report)
        assert notification_type == NotificationType.SUCCESS

    def test_determine_notification_type_failure(self) -> None:
        """Test type determination for full failure."""
        manager = NotificationManager()
        report = self._create_report(successful=0, failed=5)
        notification_type = manager._determine_notification_type(report)
        assert notification_type == NotificationType.FAILURE

    def test_determine_notification_type_partial(self) -> None:
        """Test type determination for partial success."""
        manager = NotificationManager()
        report = self._create_report(successful=8, failed=2)
        notification_type = manager._determine_notification_type(report)
        assert notification_type == NotificationType.PARTIAL

    def test_determine_notification_type_cancelled(self) -> None:
        """Test type determination for cancelled batch."""
        manager = NotificationManager()
        report = self._create_report(successful=5, cancelled=True)
        notification_type = manager._determine_notification_type(report)
        assert notification_type == NotificationType.INFO

    def test_get_title_for_success(self) -> None:
        """Test title for success notification."""
        manager = NotificationManager()
        title = manager._get_title_for_type(NotificationType.SUCCESS)
        assert title == "Conversion Complete"

    def test_get_title_for_failure(self) -> None:
        """Test title for failure notification."""
        manager = NotificationManager()
        title = manager._get_title_for_type(NotificationType.FAILURE)
        assert title == "Conversion Failed"

    def test_get_title_for_partial(self) -> None:
        """Test title for partial success notification."""
        manager = NotificationManager()
        title = manager._get_title_for_type(NotificationType.PARTIAL)
        assert title == "Conversion Completed with Errors"

    def test_format_report_body_success_single(self) -> None:
        """Test body formatting for single file success."""
        manager = NotificationManager()
        report = self._create_report(
            successful=1,
            failed=0,
            size_saved=1024 * 1024 * 100,  # 100 MB
        )
        body = manager._format_report_body(report, NotificationType.SUCCESS)
        assert "1 video converted" in body
        assert "MB" in body or "GB" in body

    def test_format_report_body_success_multiple(self) -> None:
        """Test body formatting for multiple files success."""
        manager = NotificationManager()
        report = self._create_report(
            successful=12,
            failed=0,
            size_saved=int(8.5 * 1024 * 1024 * 1024),  # 8.5 GB
        )
        body = manager._format_report_body(report, NotificationType.SUCCESS)
        assert "12 videos converted" in body
        assert "GB" in body

    def test_format_report_body_failure(self) -> None:
        """Test body formatting for failure."""
        manager = NotificationManager()
        report = self._create_report(successful=0, failed=3)
        body = manager._format_report_body(report, NotificationType.FAILURE)
        assert "failed" in body

    def test_format_report_body_partial(self) -> None:
        """Test body formatting for partial success."""
        manager = NotificationManager()
        report = self._create_report(successful=10, failed=2)
        body = manager._format_report_body(report, NotificationType.PARTIAL)
        assert "10/12" in body
        assert "2 failed" in body

    def test_format_report_body_cancelled(self) -> None:
        """Test body formatting for cancelled batch."""
        manager = NotificationManager()
        report = self._create_report(successful=5, cancelled=True)
        body = manager._format_report_body(report, NotificationType.INFO)
        assert "cancelled" in body
        assert "5" in body

    @patch("video_converter.automation.notification.platform.system")
    @patch("subprocess.run")
    def test_send_batch_notification(
        self,
        mock_run: MagicMock,
        mock_system: MagicMock,
    ) -> None:
        """Test sending batch notification."""
        mock_system.return_value = "Darwin"
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        manager = NotificationManager()
        report = self._create_report(
            successful=10,
            failed=0,
            size_saved=int(5 * 1024 * 1024 * 1024),
        )
        result = manager.send_batch_notification(report)
        assert result.success is True
        mock_run.assert_called_once()


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @patch("video_converter.automation.notification.platform.system")
    @patch("subprocess.run")
    def test_send_notification_function(
        self,
        mock_run: MagicMock,
        mock_system: MagicMock,
    ) -> None:
        """Test send_notification convenience function."""
        mock_system.return_value = "Darwin"
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        result = send_notification(
            title="Test Title",
            body="Test Body",
            sound=True,
        )
        assert result.success is True


class TestSpecificNotificationMethods:
    """Tests for specific notification methods."""

    @patch("video_converter.automation.notification.platform.system")
    @patch("subprocess.run")
    def test_send_success_notification(
        self,
        mock_run: MagicMock,
        mock_system: MagicMock,
    ) -> None:
        """Test send_success_notification method."""
        mock_system.return_value = "Darwin"
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        manager = NotificationManager()
        result = manager.send_success_notification(
            videos_converted=5,
            size_saved=1024 * 1024 * 500,  # 500 MB
        )
        assert result.success is True
        call_args = mock_run.call_args[0][0]
        script = call_args[2]
        assert "Conversion Complete" in script
        assert "5 videos" in script

    @patch("video_converter.automation.notification.platform.system")
    @patch("subprocess.run")
    def test_send_success_notification_single(
        self,
        mock_run: MagicMock,
        mock_system: MagicMock,
    ) -> None:
        """Test send_success_notification for single video."""
        mock_system.return_value = "Darwin"
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        manager = NotificationManager()
        result = manager.send_success_notification(
            videos_converted=1,
            size_saved=1024 * 1024 * 100,
        )
        assert result.success is True
        call_args = mock_run.call_args[0][0]
        script = call_args[2]
        assert "1 video converted" in script

    @patch("video_converter.automation.notification.platform.system")
    @patch("subprocess.run")
    def test_send_error_notification(
        self,
        mock_run: MagicMock,
        mock_system: MagicMock,
    ) -> None:
        """Test send_error_notification method."""
        mock_system.return_value = "Darwin"
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        manager = NotificationManager()
        result = manager.send_error_notification(
            error_message="Encoding failed",
            file_name="video.mov",
        )
        assert result.success is True
        call_args = mock_run.call_args[0][0]
        script = call_args[2]
        assert "Conversion Failed" in script
        assert "video.mov" in script

    @patch("video_converter.automation.notification.platform.system")
    @patch("subprocess.run")
    def test_send_partial_notification(
        self,
        mock_run: MagicMock,
        mock_system: MagicMock,
    ) -> None:
        """Test send_partial_notification method."""
        mock_system.return_value = "Darwin"
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        manager = NotificationManager()
        result = manager.send_partial_notification(
            succeeded=10,
            failed=2,
        )
        assert result.success is True
        call_args = mock_run.call_args[0][0]
        script = call_args[2]
        assert "Completed with Errors" in script
        assert "10/12" in script
