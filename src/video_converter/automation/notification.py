"""macOS Notification Center integration for video conversion alerts.

This module provides integration with macOS Notification Center to send
alerts for conversion completion, errors, and summary statistics.

SDS Reference: SDS-A01-002
SRS Reference: SRS-801 (macOS Notification Integration)

Example:
    >>> from video_converter.automation.notification import NotificationManager
    >>> from video_converter.core.types import ConversionReport
    >>>
    >>> manager = NotificationManager()
    >>>
    >>> # Send a simple notification
    >>> manager.send_notification(
    ...     title="Conversion Complete",
    ...     body="12 videos converted, 8.5 GB saved",
    ... )
    >>>
    >>> # Send notification from a report
    >>> manager.send_batch_notification(report)
"""

from __future__ import annotations

import logging
import platform
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from video_converter.core.types import ConversionReport

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Type of notification to send.

    Attributes:
        SUCCESS: All conversions completed successfully.
        PARTIAL: Some conversions completed with errors.
        FAILURE: All conversions failed or critical error occurred.
        INFO: Informational notification.
    """

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    INFO = "info"


@dataclass
class NotificationConfig:
    """Configuration for notification behavior.

    Attributes:
        enabled: Whether notifications are enabled.
        sound: Whether to play sound with notification.
        sound_name: Name of the sound to play (macOS system sound).
        group_id: Optional group identifier for notification grouping.
    """

    enabled: bool = True
    sound: bool = True
    sound_name: str = "Glass"
    group_id: str = "com.videoconverter"


@dataclass
class NotificationResult:
    """Result of a notification send attempt.

    Attributes:
        success: Whether the notification was sent successfully.
        error_message: Error message if sending failed.
    """

    success: bool
    error_message: str | None = None


def _format_size(size_bytes: int) -> str:
    """Format size in bytes to human-readable string.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Human-readable size string (e.g., "8.5 GB").
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


class NotificationManager:
    """Manager for sending macOS Notification Center notifications.

    This class provides methods to send notifications for various
    video conversion events including batch completion, errors,
    and progress milestones.

    Attributes:
        config: Notification configuration settings.
    """

    def __init__(self, config: NotificationConfig | None = None) -> None:
        """Initialize the notification manager.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or NotificationConfig()
        self._is_macos = platform.system() == "Darwin"

    def is_available(self) -> bool:
        """Check if notifications are available on this system.

        Returns:
            True if notifications can be sent, False otherwise.
        """
        if not self._is_macos:
            return False

        if not self.config.enabled:
            return False

        try:
            result = subprocess.run(
                ["which", "osascript"],
                capture_output=True,
                check=False,
            )
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def send_notification(
        self,
        title: str,
        body: str,
        sound: bool | None = None,
        subtitle: str | None = None,
    ) -> NotificationResult:
        """Send a notification to macOS Notification Center.

        Args:
            title: The notification title.
            body: The notification body text.
            sound: Whether to play sound. Uses config default if None.
            subtitle: Optional subtitle for the notification.

        Returns:
            NotificationResult indicating success or failure.
        """
        if not self.config.enabled:
            return NotificationResult(success=True)

        if not self._is_macos:
            logger.debug("Notifications not supported on this platform")
            return NotificationResult(
                success=False,
                error_message="Notifications only supported on macOS",
            )

        use_sound = sound if sound is not None else self.config.sound

        try:
            script = self._build_applescript(title, body, use_sound, subtitle)
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown error"
                logger.warning(f"Failed to send notification: {error_msg}")
                return NotificationResult(success=False, error_message=error_msg)

            logger.debug(f"Notification sent: {title}")
            return NotificationResult(success=True)

        except subprocess.TimeoutExpired:
            logger.warning("Notification send timed out")
            return NotificationResult(
                success=False,
                error_message="Notification send timed out",
            )
        except (OSError, subprocess.SubprocessError) as e:
            logger.warning(f"Failed to send notification: {e}")
            return NotificationResult(success=False, error_message=str(e))

    def _build_applescript(
        self,
        title: str,
        body: str,
        sound: bool,
        subtitle: str | None = None,
    ) -> str:
        """Build AppleScript for sending notification.

        Args:
            title: The notification title.
            body: The notification body text.
            sound: Whether to include sound.
            subtitle: Optional subtitle.

        Returns:
            AppleScript string for osascript.
        """
        title_escaped = title.replace('"', '\\"')
        body_escaped = body.replace('"', '\\"')

        parts = [f'display notification "{body_escaped}"']
        parts.append(f'with title "{title_escaped}"')

        if subtitle:
            subtitle_escaped = subtitle.replace('"', '\\"')
            parts.append(f'subtitle "{subtitle_escaped}"')

        if sound:
            parts.append(f'sound name "{self.config.sound_name}"')

        return " ".join(parts)

    def send_batch_notification(
        self,
        report: ConversionReport,
    ) -> NotificationResult:
        """Send notification based on batch conversion report.

        Automatically determines notification type and formats
        the message based on conversion results.

        Args:
            report: The conversion report to notify about.

        Returns:
            NotificationResult indicating success or failure.
        """
        notification_type = self._determine_notification_type(report)
        title = self._get_title_for_type(notification_type)
        body = self._format_report_body(report, notification_type)

        return self.send_notification(title=title, body=body)

    def _determine_notification_type(
        self,
        report: ConversionReport,
    ) -> NotificationType:
        """Determine notification type based on report results.

        Args:
            report: The conversion report.

        Returns:
            Appropriate NotificationType.
        """
        if report.cancelled:
            return NotificationType.INFO

        if report.failed == 0 and report.successful > 0:
            return NotificationType.SUCCESS
        elif report.successful == 0 and report.failed > 0:
            return NotificationType.FAILURE
        elif report.successful > 0 and report.failed > 0:
            return NotificationType.PARTIAL
        else:
            return NotificationType.INFO

    def _get_title_for_type(self, notification_type: NotificationType) -> str:
        """Get notification title for type.

        Args:
            notification_type: The type of notification.

        Returns:
            Title string.
        """
        titles = {
            NotificationType.SUCCESS: "Conversion Complete",
            NotificationType.PARTIAL: "Conversion Completed with Errors",
            NotificationType.FAILURE: "Conversion Failed",
            NotificationType.INFO: "Video Converter",
        }
        return titles.get(notification_type, "Video Converter")

    def _format_report_body(
        self,
        report: ConversionReport,
        notification_type: NotificationType,
    ) -> str:
        """Format notification body from report.

        Args:
            report: The conversion report.
            notification_type: The notification type.

        Returns:
            Formatted body string.
        """
        if report.cancelled:
            return f"Conversion cancelled. {report.successful} completed before cancellation."

        if notification_type == NotificationType.SUCCESS:
            size_saved = _format_size(report.total_size_saved)
            if report.successful == 1:
                return f"1 video converted, {size_saved} saved"
            return f"{report.successful} videos converted, {size_saved} saved"

        elif notification_type == NotificationType.FAILURE:
            if report.failed == 1:
                return "Error during video processing"
            return f"{report.failed} videos failed to convert"

        elif notification_type == NotificationType.PARTIAL:
            total = report.successful + report.failed
            return f"{report.successful}/{total} succeeded, {report.failed} failed"

        else:
            return f"Processed {report.total_files} files"

    def send_success_notification(
        self,
        videos_converted: int,
        size_saved: int,
    ) -> NotificationResult:
        """Send a success notification with statistics.

        Args:
            videos_converted: Number of videos converted.
            size_saved: Total bytes saved.

        Returns:
            NotificationResult indicating success or failure.
        """
        title = "Conversion Complete"
        size_str = _format_size(size_saved)
        if videos_converted == 1:
            body = f"1 video converted, {size_str} saved"
        else:
            body = f"{videos_converted} videos converted, {size_str} saved"

        return self.send_notification(title=title, body=body)

    def send_error_notification(
        self,
        error_message: str,
        file_name: str | None = None,
    ) -> NotificationResult:
        """Send an error notification.

        Args:
            error_message: The error message to display.
            file_name: Optional file name that caused the error.

        Returns:
            NotificationResult indicating success or failure.
        """
        title = "Conversion Failed"
        if file_name:
            body = f"{file_name}: {error_message}"
        else:
            body = error_message

        return self.send_notification(title=title, body=body)

    def send_partial_notification(
        self,
        succeeded: int,
        failed: int,
    ) -> NotificationResult:
        """Send a partial success notification.

        Args:
            succeeded: Number of successful conversions.
            failed: Number of failed conversions.

        Returns:
            NotificationResult indicating success or failure.
        """
        title = "Conversion Completed with Errors"
        total = succeeded + failed
        body = f"{succeeded}/{total} succeeded, {failed} failed"

        return self.send_notification(title=title, body=body)


def send_notification(
    title: str,
    body: str,
    sound: bool = True,
) -> NotificationResult:
    """Convenience function to send a simple notification.

    Args:
        title: The notification title.
        body: The notification body text.
        sound: Whether to play sound.

    Returns:
        NotificationResult indicating success or failure.

    Example:
        >>> result = send_notification(
        ...     title="Conversion Complete",
        ...     body="12 videos converted",
        ... )
    """
    manager = NotificationManager()
    return manager.send_notification(title=title, body=body, sound=sound)


__all__ = [
    "NotificationType",
    "NotificationConfig",
    "NotificationResult",
    "NotificationManager",
    "send_notification",
]
