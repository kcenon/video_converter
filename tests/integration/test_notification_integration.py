"""Integration tests for notification sending.

This module tests the macOS Notification Center integration for
conversion completion, errors, and summary notifications.

SRS Reference: SRS-801 (macOS Notification Integration)
SDS Reference: SDS-A01-002
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import subprocess

import pytest

from video_converter.automation.notification import (
    NotificationConfig,
    NotificationManager,
    NotificationResult,
    NotificationType,
    send_notification,
)


class MockConversionReport:
    """Mock ConversionReport for testing."""

    def __init__(
        self,
        *,
        total_files: int = 10,
        successful: int = 8,
        failed: int = 2,
        skipped: int = 0,
        cancelled: bool = False,
        total_size_saved: int = 1073741824,  # 1 GB
    ) -> None:
        self.total_files = total_files
        self.successful = successful
        self.failed = failed
        self.skipped = skipped
        self.cancelled = cancelled
        self.total_size_saved = total_size_saved


class TestNotificationConfig:
    """Tests for NotificationConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = NotificationConfig()

        assert config.enabled is True
        assert config.sound is True
        assert config.sound_name == "Glass"
        assert config.group_id == "com.videoconverter"

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = NotificationConfig(
            enabled=False,
            sound=False,
            sound_name="Ping",
            group_id="custom.group",
        )

        assert config.enabled is False
        assert config.sound is False
        assert config.sound_name == "Ping"
        assert config.group_id == "custom.group"


class TestNotificationResult:
    """Tests for NotificationResult."""

    def test_success_result(self) -> None:
        """Test successful notification result."""
        result = NotificationResult(success=True)

        assert result.success is True
        assert result.error_message is None

    def test_failure_result(self) -> None:
        """Test failed notification result."""
        result = NotificationResult(
            success=False,
            error_message="osascript failed",
        )

        assert result.success is False
        assert result.error_message == "osascript failed"


class TestNotificationType:
    """Tests for NotificationType enum."""

    def test_all_types_defined(self) -> None:
        """Test that all notification types are defined."""
        assert NotificationType.SUCCESS.value == "success"
        assert NotificationType.PARTIAL.value == "partial"
        assert NotificationType.FAILURE.value == "failure"
        assert NotificationType.INFO.value == "info"


class TestNotificationManager:
    """Tests for NotificationManager."""

    @pytest.fixture
    def manager(self) -> NotificationManager:
        """Create a NotificationManager for testing."""
        return NotificationManager()

    @pytest.fixture
    def disabled_manager(self) -> NotificationManager:
        """Create a disabled NotificationManager for testing."""
        config = NotificationConfig(enabled=False)
        return NotificationManager(config)

    def test_manager_initialization(self, manager: NotificationManager) -> None:
        """Test manager initialization with defaults."""
        assert manager.config.enabled is True
        assert manager.config.sound is True

    def test_disabled_manager(self, disabled_manager: NotificationManager) -> None:
        """Test disabled manager."""
        assert disabled_manager.config.enabled is False

    @patch("platform.system")
    def test_is_available_on_macos(
        self, mock_system: MagicMock, manager: NotificationManager
    ) -> None:
        """Test is_available returns True on macOS."""
        mock_system.return_value = "Darwin"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = manager.is_available()

        assert result is True

    @patch("video_converter.automation.notification.platform.system")
    def test_is_available_not_on_macos(self, mock_system: MagicMock) -> None:
        """Test is_available returns False on non-macOS."""
        mock_system.return_value = "Linux"
        # Create manager after mock is applied so _is_macos is set correctly
        manager = NotificationManager()

        result = manager.is_available()
        assert result is False

    def test_is_available_when_disabled(
        self, disabled_manager: NotificationManager
    ) -> None:
        """Test is_available returns False when disabled."""
        result = disabled_manager.is_available()
        assert result is False


class TestNotificationSending:
    """Tests for notification sending functionality."""

    @pytest.fixture
    def manager(self) -> NotificationManager:
        """Create a NotificationManager for testing."""
        return NotificationManager()

    def test_send_notification_when_disabled(self) -> None:
        """Test that send_notification succeeds silently when disabled."""
        config = NotificationConfig(enabled=False)
        manager = NotificationManager(config)

        result = manager.send_notification(
            title="Test",
            body="Test message",
        )

        assert result.success is True

    @patch("platform.system")
    def test_send_notification_not_on_macos(
        self, mock_system: MagicMock, manager: NotificationManager
    ) -> None:
        """Test send_notification fails on non-macOS."""
        mock_system.return_value = "Linux"
        manager._is_macos = False

        result = manager.send_notification(
            title="Test",
            body="Test message",
        )

        assert result.success is False
        assert "macOS" in result.error_message

    @patch("platform.system")
    @patch("subprocess.run")
    def test_send_notification_success(
        self,
        mock_run: MagicMock,
        mock_system: MagicMock,
        manager: NotificationManager,
    ) -> None:
        """Test successful notification sending."""
        mock_system.return_value = "Darwin"
        manager._is_macos = True
        mock_run.return_value = MagicMock(returncode=0)

        result = manager.send_notification(
            title="Test Title",
            body="Test body message",
        )

        assert result.success is True
        mock_run.assert_called_once()

    @patch("platform.system")
    @patch("subprocess.run")
    def test_send_notification_with_sound(
        self,
        mock_run: MagicMock,
        mock_system: MagicMock,
        manager: NotificationManager,
    ) -> None:
        """Test notification with sound."""
        mock_system.return_value = "Darwin"
        manager._is_macos = True
        mock_run.return_value = MagicMock(returncode=0)

        manager.send_notification(
            title="Test",
            body="Message",
            sound=True,
        )

        call_args = mock_run.call_args
        script = call_args[0][0][2]  # osascript -e <script>
        assert 'sound name "Glass"' in script

    @patch("platform.system")
    @patch("subprocess.run")
    def test_send_notification_without_sound(
        self,
        mock_run: MagicMock,
        mock_system: MagicMock,
        manager: NotificationManager,
    ) -> None:
        """Test notification without sound."""
        mock_system.return_value = "Darwin"
        manager._is_macos = True
        mock_run.return_value = MagicMock(returncode=0)

        manager.send_notification(
            title="Test",
            body="Message",
            sound=False,
        )

        call_args = mock_run.call_args
        script = call_args[0][0][2]
        assert "sound name" not in script

    @patch("platform.system")
    @patch("subprocess.run")
    def test_send_notification_with_subtitle(
        self,
        mock_run: MagicMock,
        mock_system: MagicMock,
        manager: NotificationManager,
    ) -> None:
        """Test notification with subtitle."""
        mock_system.return_value = "Darwin"
        manager._is_macos = True
        mock_run.return_value = MagicMock(returncode=0)

        manager.send_notification(
            title="Test",
            body="Message",
            subtitle="Subtitle",
        )

        call_args = mock_run.call_args
        script = call_args[0][0][2]
        assert 'subtitle "Subtitle"' in script

    @patch("platform.system")
    @patch("subprocess.run")
    def test_send_notification_escapes_quotes(
        self,
        mock_run: MagicMock,
        mock_system: MagicMock,
        manager: NotificationManager,
    ) -> None:
        """Test that quotes are escaped in notification text."""
        mock_system.return_value = "Darwin"
        manager._is_macos = True
        mock_run.return_value = MagicMock(returncode=0)

        manager.send_notification(
            title='Title with "quotes"',
            body='Body with "quotes"',
        )

        call_args = mock_run.call_args
        script = call_args[0][0][2]
        assert '\\"' in script

    @patch("platform.system")
    @patch("subprocess.run")
    def test_send_notification_handles_timeout(
        self,
        mock_run: MagicMock,
        mock_system: MagicMock,
        manager: NotificationManager,
    ) -> None:
        """Test that timeout is handled gracefully."""
        mock_system.return_value = "Darwin"
        manager._is_macos = True
        mock_run.side_effect = subprocess.TimeoutExpired("osascript", 10)

        result = manager.send_notification(
            title="Test",
            body="Message",
        )

        assert result.success is False
        assert "timed out" in result.error_message.lower()


class TestBatchNotification:
    """Tests for batch notification functionality."""

    @pytest.fixture
    def manager(self) -> NotificationManager:
        """Create a NotificationManager for testing."""
        return NotificationManager()

    def test_determine_notification_type_success(
        self, manager: NotificationManager
    ) -> None:
        """Test type determination for full success."""
        report = MockConversionReport(successful=10, failed=0)
        notification_type = manager._determine_notification_type(report)

        assert notification_type == NotificationType.SUCCESS

    def test_determine_notification_type_failure(
        self, manager: NotificationManager
    ) -> None:
        """Test type determination for full failure."""
        report = MockConversionReport(successful=0, failed=10)
        notification_type = manager._determine_notification_type(report)

        assert notification_type == NotificationType.FAILURE

    def test_determine_notification_type_partial(
        self, manager: NotificationManager
    ) -> None:
        """Test type determination for partial success."""
        report = MockConversionReport(successful=8, failed=2)
        notification_type = manager._determine_notification_type(report)

        assert notification_type == NotificationType.PARTIAL

    def test_determine_notification_type_cancelled(
        self, manager: NotificationManager
    ) -> None:
        """Test type determination for cancelled conversion."""
        report = MockConversionReport(cancelled=True)
        notification_type = manager._determine_notification_type(report)

        assert notification_type == NotificationType.INFO

    def test_get_title_for_success(self, manager: NotificationManager) -> None:
        """Test title for success notification."""
        title = manager._get_title_for_type(NotificationType.SUCCESS)
        assert title == "Conversion Complete"

    def test_get_title_for_failure(self, manager: NotificationManager) -> None:
        """Test title for failure notification."""
        title = manager._get_title_for_type(NotificationType.FAILURE)
        assert title == "Conversion Failed"

    def test_get_title_for_partial(self, manager: NotificationManager) -> None:
        """Test title for partial notification."""
        title = manager._get_title_for_type(NotificationType.PARTIAL)
        assert title == "Conversion Completed with Errors"

    def test_format_report_body_success(
        self, manager: NotificationManager
    ) -> None:
        """Test body formatting for success."""
        report = MockConversionReport(successful=10, failed=0)
        body = manager._format_report_body(report, NotificationType.SUCCESS)

        assert "10 videos converted" in body
        assert "saved" in body

    def test_format_report_body_single_video(
        self, manager: NotificationManager
    ) -> None:
        """Test body formatting for single video success."""
        report = MockConversionReport(successful=1, failed=0)
        body = manager._format_report_body(report, NotificationType.SUCCESS)

        assert "1 video converted" in body

    def test_format_report_body_failure(
        self, manager: NotificationManager
    ) -> None:
        """Test body formatting for failure."""
        report = MockConversionReport(successful=0, failed=5)
        body = manager._format_report_body(report, NotificationType.FAILURE)

        assert "5 videos failed" in body

    def test_format_report_body_partial(
        self, manager: NotificationManager
    ) -> None:
        """Test body formatting for partial."""
        report = MockConversionReport(successful=8, failed=2)
        body = manager._format_report_body(report, NotificationType.PARTIAL)

        assert "8/10 succeeded" in body
        assert "2 failed" in body

    def test_format_report_body_cancelled(
        self, manager: NotificationManager
    ) -> None:
        """Test body formatting for cancelled."""
        report = MockConversionReport(successful=5, cancelled=True)
        body = manager._format_report_body(report, NotificationType.INFO)

        assert "cancelled" in body.lower()
        assert "5" in body


class TestConvenienceNotifications:
    """Tests for convenience notification methods."""

    @pytest.fixture
    def manager(self) -> NotificationManager:
        """Create a NotificationManager for testing."""
        return NotificationManager()

    @patch.object(NotificationManager, "send_notification")
    def test_send_success_notification(
        self, mock_send: MagicMock, manager: NotificationManager
    ) -> None:
        """Test send_success_notification method."""
        mock_send.return_value = NotificationResult(success=True)

        manager.send_success_notification(
            videos_converted=5,
            size_saved=5368709120,  # 5 GB
        )

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["title"] == "Conversion Complete"
        assert "5 videos converted" in call_kwargs["body"]
        assert "GB" in call_kwargs["body"]

    @patch.object(NotificationManager, "send_notification")
    def test_send_success_notification_single(
        self, mock_send: MagicMock, manager: NotificationManager
    ) -> None:
        """Test send_success_notification for single video."""
        mock_send.return_value = NotificationResult(success=True)

        manager.send_success_notification(
            videos_converted=1,
            size_saved=104857600,  # 100 MB
        )

        call_kwargs = mock_send.call_args[1]
        assert "1 video converted" in call_kwargs["body"]

    @patch.object(NotificationManager, "send_notification")
    def test_send_error_notification(
        self, mock_send: MagicMock, manager: NotificationManager
    ) -> None:
        """Test send_error_notification method."""
        mock_send.return_value = NotificationResult(success=True)

        manager.send_error_notification(
            error_message="FFmpeg encoder failed",
            file_name="video.mp4",
        )

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["title"] == "Conversion Failed"
        assert "video.mp4" in call_kwargs["body"]
        assert "FFmpeg" in call_kwargs["body"]

    @patch.object(NotificationManager, "send_notification")
    def test_send_error_notification_no_filename(
        self, mock_send: MagicMock, manager: NotificationManager
    ) -> None:
        """Test send_error_notification without filename."""
        mock_send.return_value = NotificationResult(success=True)

        manager.send_error_notification(error_message="General error")

        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["body"] == "General error"

    @patch.object(NotificationManager, "send_notification")
    def test_send_partial_notification(
        self, mock_send: MagicMock, manager: NotificationManager
    ) -> None:
        """Test send_partial_notification method."""
        mock_send.return_value = NotificationResult(success=True)

        manager.send_partial_notification(succeeded=8, failed=2)

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["title"] == "Conversion Completed with Errors"
        assert "8/10 succeeded" in call_kwargs["body"]
        assert "2 failed" in call_kwargs["body"]


class TestSendNotificationFunction:
    """Tests for the convenience send_notification function."""

    @patch.object(NotificationManager, "send_notification")
    def test_send_notification_function(self, mock_send: MagicMock) -> None:
        """Test the module-level send_notification function."""
        mock_send.return_value = NotificationResult(success=True)

        result = send_notification(
            title="Test Title",
            body="Test Body",
            sound=True,
        )

        assert mock_send.called


class TestNotificationWorkflowIntegration:
    """Integration tests for notification workflow."""

    @patch("platform.system")
    @patch("subprocess.run")
    def test_full_notification_workflow(
        self, mock_run: MagicMock, mock_system: MagicMock
    ) -> None:
        """Test complete notification workflow simulation."""
        mock_system.return_value = "Darwin"
        mock_run.return_value = MagicMock(returncode=0)

        manager = NotificationManager()
        manager._is_macos = True

        # Simulate batch conversion completion
        report = MockConversionReport(
            total_files=10,
            successful=9,
            failed=1,
            total_size_saved=5368709120,  # 5 GB
        )

        # Send batch notification
        result = manager.send_batch_notification(report)

        assert result.success is True
        mock_run.assert_called_once()

        # Verify notification content
        call_args = mock_run.call_args
        script = call_args[0][0][2]
        assert "with title" in script

    @patch("platform.system")
    @patch("subprocess.run")
    def test_notification_after_successful_conversion(
        self, mock_run: MagicMock, mock_system: MagicMock
    ) -> None:
        """Test notification after successful conversion."""
        mock_system.return_value = "Darwin"
        mock_run.return_value = MagicMock(returncode=0)

        manager = NotificationManager()
        manager._is_macos = True

        # Send success notification
        result = manager.send_success_notification(
            videos_converted=5,
            size_saved=2147483648,  # 2 GB
        )

        assert result.success is True

    @patch("video_converter.automation.notification.platform.system")
    def test_notification_graceful_degradation_on_error(
        self, mock_system: MagicMock
    ) -> None:
        """Test that notification failures don't crash the workflow."""
        mock_system.return_value = "Darwin"

        manager = NotificationManager()
        # Ensure manager was created with Darwin platform detection
        assert manager._is_macos is True

        with patch("subprocess.run") as mock_run:
            # Use OSError which is caught by the implementation
            mock_run.side_effect = OSError("Unexpected error")

            result = manager.send_notification(
                title="Test",
                body="Message",
            )

            # Should fail gracefully
            assert result.success is False
            assert result.error_message is not None
