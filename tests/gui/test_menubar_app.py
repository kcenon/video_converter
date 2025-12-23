"""Tests for the menubar application component.

This module tests the MenubarApp class which provides system tray
integration for background monitoring.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QSystemTrayIcon

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


class TestMenubarAppCreation:
    """Tests for MenubarApp initialization."""

    def test_menubar_app_creates_successfully(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test that MenubarApp creates without errors."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        # Create real signals for the mock
        mock_conversion_service.task_added = Signal(str, str, str)
        mock_conversion_service.task_started = Signal(str)
        mock_conversion_service.progress_updated = Signal(str, float, object, object)
        mock_conversion_service.task_completed = Signal(str, object)
        mock_conversion_service.task_failed = Signal(str, str)
        mock_conversion_service.all_completed = Signal(int, int)
        mock_conversion_service.queue_updated = Signal()

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    assert menubar is not None

    def test_menubar_app_has_tray_icon(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test that MenubarApp creates a system tray icon."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    assert hasattr(menubar, "tray_icon")
                                    assert isinstance(
                                        menubar.tray_icon, QSystemTrayIcon
                                    )

    def test_menubar_app_has_tray_menu(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test that MenubarApp creates a context menu."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    assert hasattr(menubar, "tray_menu")
                                    assert menubar.tray_menu is not None


class TestMenubarAppVisibility:
    """Tests for MenubarApp visibility control."""

    def test_show_makes_tray_visible(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test that show() makes the tray icon visible."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    menubar.show()
                                    assert menubar.is_visible()

    def test_hide_makes_tray_hidden(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test that hide() hides the tray icon."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    menubar.show()
                                    menubar.hide()
                                    assert not menubar.is_visible()


class TestMenubarAppSignals:
    """Tests for MenubarApp signal emission."""

    def test_open_main_window_emits_signal(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test that clicking open emits show_main_window_requested."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    with qtbot.waitSignal(
                                        menubar.show_main_window_requested, timeout=1000
                                    ):
                                        menubar._on_open_main_window()

    def test_quit_emits_signal(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test that clicking quit emits quit_requested."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    with qtbot.waitSignal(
                                        menubar.quit_requested, timeout=1000
                                    ):
                                        menubar._on_quit()


class TestMenubarAppPauseResume:
    """Tests for pause/resume functionality."""

    def test_pause_all_calls_service(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test that pause all calls the conversion service."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    menubar._is_paused = False
                                    menubar._on_pause_all()
                                    mock_conversion_service.pause_all.assert_called_once()
                                    assert menubar._is_paused is True

    def test_resume_all_calls_service(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test that resume all calls the conversion service."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    menubar._is_paused = True
                                    menubar._on_pause_all()
                                    mock_conversion_service.resume_all.assert_called_once()
                                    assert menubar._is_paused is False


class TestMenubarAppCancelAll:
    """Tests for cancel all functionality."""

    def test_cancel_all_calls_service(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test that cancel all calls the conversion service."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    menubar._on_cancel_all()
                                    mock_conversion_service.cancel_all.assert_called_once()


class TestMenubarAppStatusDisplay:
    """Tests for status display updates."""

    def test_update_status_idle(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test status display when idle."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        mock_conversion_service.get_queue_status.return_value = {
            "converting": 0,
            "queued": 0,
        }

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    menubar._update_status_display()
                                    assert "No active" in menubar._progress_action.text()

    def test_update_status_converting(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test status display when converting."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        mock_conversion_service.get_queue_status.return_value = {
            "converting": 1,
            "queued": 2,
        }

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    menubar._current_progress = 50.0
                                    menubar._update_status_display()
                                    assert "Converting" in menubar._progress_action.text()

    def test_update_status_queued(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test status display when items are queued."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        mock_conversion_service.get_queue_status.return_value = {
            "converting": 0,
            "queued": 3,
        }

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    menubar._update_status_display()
                                    assert "queued" in menubar._progress_action.text()


class TestMenubarAppEventHandlers:
    """Tests for event handler methods."""

    def test_on_task_added_updates_display(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test that task added updates the display."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    with patch.object(
                                        menubar, "_update_status_display"
                                    ) as mock_update:
                                        menubar._on_task_added("task1", "test.mp4", "1MB")
                                        mock_update.assert_called_once()

    def test_on_task_started_shows_current_task(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test that task started sets task info text."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        mock_task = MagicMock()
        mock_task.file_name = "test_video.mp4"
        mock_conversion_service.get_task.return_value = mock_task
        # Set converting status so the action stays visible
        mock_conversion_service.get_queue_status.return_value = {
            "converting": 1,
            "queued": 0,
        }

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    menubar._on_task_started("task1")
                                    # Check that the text was set correctly
                                    assert "test_video.mp4" in menubar._current_task_action.text()

    def test_on_progress_updated_updates_progress(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test that progress updates the current progress."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        mock_task = MagicMock()
        mock_task.file_name = "test.mp4"
        mock_conversion_service.get_task.return_value = mock_task

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    menubar._on_progress_updated("task1", 75.0, 120, "2x")
                                    assert menubar._current_progress == 75.0

    def test_on_task_completed_resets_progress(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test that task completed resets progress."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        mock_result = MagicMock()
        mock_result.original_size = 1000000
        mock_result.converted_size = 500000

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    menubar._current_progress = 100.0
                                    menubar._on_task_completed("task1", mock_result)
                                    assert menubar._current_progress == 0.0

    def test_on_task_failed_resets_progress(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test that task failed resets progress."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        mock_task = MagicMock()
        mock_task.file_name = "failed.mp4"
        mock_conversion_service.get_task.return_value = mock_task

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    menubar._current_progress = 50.0
                                    menubar._on_task_failed("task1", "Error message")
                                    assert menubar._current_progress == 0.0

    def test_on_all_completed_resets_progress(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test that all completed resets progress."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    menubar._current_progress = 100.0
                                    menubar._on_all_completed(5, 0)
                                    assert menubar._current_progress == 0.0

    def test_on_queue_updated_syncs_pause_state(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test that queue updated syncs pause state."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        mock_conversion_service.get_queue_status.return_value = {
            "converting": 0,
            "queued": 0,
            "is_paused": True,
        }

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    menubar._on_queue_updated()
                                    assert menubar._is_paused is True


class TestMenubarAppTrayActivation:
    """Tests for tray icon activation handling."""

    def test_single_click_emits_show_signal(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test that single click emits show main window signal."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    with qtbot.waitSignal(
                                        menubar.show_main_window_requested, timeout=1000
                                    ):
                                        menubar._on_tray_activated(
                                            QSystemTrayIcon.ActivationReason.Trigger
                                        )

    def test_double_click_emits_show_signal(
        self, qtbot: QtBot, mock_conversion_service: MagicMock
    ) -> None:
        """Test that double click emits show main window signal."""
        from video_converter.gui.menubar.menubar_app import MenubarApp

        with patch.object(mock_conversion_service, "task_added", MagicMock()):
            with patch.object(mock_conversion_service, "task_started", MagicMock()):
                with patch.object(
                    mock_conversion_service, "progress_updated", MagicMock()
                ):
                    with patch.object(
                        mock_conversion_service, "task_completed", MagicMock()
                    ):
                        with patch.object(
                            mock_conversion_service, "task_failed", MagicMock()
                        ):
                            with patch.object(
                                mock_conversion_service, "all_completed", MagicMock()
                            ):
                                with patch.object(
                                    mock_conversion_service, "queue_updated", MagicMock()
                                ):
                                    menubar = MenubarApp(mock_conversion_service)
                                    with qtbot.waitSignal(
                                        menubar.show_main_window_requested, timeout=1000
                                    ):
                                        menubar._on_tray_activated(
                                            QSystemTrayIcon.ActivationReason.DoubleClick
                                        )
