"""Tests for the ProgressCard widget.

This module tests the progress display, state management,
and control functionality of the ProgressCard widget.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PySide6.QtWidgets import QFrame

from video_converter.gui.widgets.progress_card import ProgressCard

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


pytestmark = pytest.mark.gui


class TestProgressCardCreation:
    """Tests for ProgressCard widget creation and initialization."""

    def test_progress_card_creates_successfully(self, qtbot: QtBot) -> None:
        """Test that ProgressCard can be created without errors."""
        widget = ProgressCard(
            task_id="test-123",
            file_name="test_video.mp4",
            file_size="1.5 GB",
        )
        qtbot.addWidget(widget)

        assert widget is not None
        assert widget.task_id == "test-123"

    def test_progress_card_displays_file_info(self, qtbot: QtBot) -> None:
        """Test that ProgressCard displays correct file information."""
        widget = ProgressCard(
            task_id="test-123",
            file_name="vacation_video.mp4",
            file_size="2.5 GB",
        )
        qtbot.addWidget(widget)

        assert "vacation_video.mp4" in widget.name_label.text()
        assert widget.size_label.text() == "2.5 GB"

    def test_progress_card_initial_state(self, qtbot: QtBot) -> None:
        """Test that ProgressCard has correct initial state."""
        widget = ProgressCard(
            task_id="test-123",
            file_name="test.mp4",
            file_size="1 GB",
        )
        qtbot.addWidget(widget)

        assert widget.progress == 0.0
        assert widget.is_completed is False
        assert widget.status_label.text() == "Queued"
        assert widget.progress_bar.value() == 0

    def test_progress_card_has_frame_style(self, qtbot: QtBot) -> None:
        """Test that ProgressCard uses styled panel frame."""
        widget = ProgressCard(
            task_id="test-123",
            file_name="test.mp4",
            file_size="1 GB",
        )
        qtbot.addWidget(widget)

        assert widget.frameShape() == QFrame.Shape.StyledPanel


class TestProgressCardUpdates:
    """Tests for ProgressCard progress updates."""

    def test_update_progress_updates_bar(self, qtbot: QtBot) -> None:
        """Test that updating progress updates the progress bar."""
        widget = ProgressCard(
            task_id="test-123",
            file_name="test.mp4",
            file_size="1 GB",
        )
        qtbot.addWidget(widget)

        widget.update_progress(50.0)

        assert widget.progress == 50.0
        assert widget.progress_bar.value() == 50

    def test_update_progress_updates_label(self, qtbot: QtBot) -> None:
        """Test that updating progress updates the progress label."""
        widget = ProgressCard(
            task_id="test-123",
            file_name="test.mp4",
            file_size="1 GB",
        )
        qtbot.addWidget(widget)

        widget.update_progress(75.5)

        assert "75.5%" in widget.progress_label.text()

    def test_update_progress_with_eta(self, qtbot: QtBot) -> None:
        """Test that updating progress with ETA updates the ETA label."""
        widget = ProgressCard(
            task_id="test-123",
            file_name="test.mp4",
            file_size="1 GB",
        )
        qtbot.addWidget(widget)

        widget.update_progress(30.0, eta="5:30")

        assert "5:30" in widget.eta_label.text()

    def test_update_progress_with_speed(self, qtbot: QtBot) -> None:
        """Test that updating progress with speed updates the speed label."""
        widget = ProgressCard(
            task_id="test-123",
            file_name="test.mp4",
            file_size="1 GB",
        )
        qtbot.addWidget(widget)

        widget.update_progress(30.0, speed="2.5x")

        assert "2.5x" in widget.speed_label.text()

    def test_update_progress_changes_status(self, qtbot: QtBot) -> None:
        """Test that updating progress changes status to Converting."""
        widget = ProgressCard(
            task_id="test-123",
            file_name="test.mp4",
            file_size="1 GB",
        )
        qtbot.addWidget(widget)

        widget.update_progress(10.0)

        assert widget.status_label.text() == "Converting"


class TestProgressCardCompletion:
    """Tests for ProgressCard completion handling."""

    def test_mark_completed_success(self, qtbot: QtBot) -> None:
        """Test marking conversion as successful."""
        widget = ProgressCard(
            task_id="test-123",
            file_name="test.mp4",
            file_size="1 GB",
        )
        qtbot.addWidget(widget)

        widget.mark_completed(success=True)

        assert widget.is_completed is True
        assert "Complete" in widget.status_label.text()
        assert widget.progress_bar.value() == 100
        assert "100%" in widget.progress_label.text()

    def test_mark_completed_failure(self, qtbot: QtBot) -> None:
        """Test marking conversion as failed."""
        widget = ProgressCard(
            task_id="test-123",
            file_name="test.mp4",
            file_size="1 GB",
        )
        qtbot.addWidget(widget)

        widget.mark_completed(success=False)

        assert widget.is_completed is True
        assert "Failed" in widget.status_label.text()

    def test_buttons_disabled_on_completion(self, qtbot: QtBot) -> None:
        """Test that buttons are disabled when completed."""
        widget = ProgressCard(
            task_id="test-123",
            file_name="test.mp4",
            file_size="1 GB",
        )
        qtbot.addWidget(widget)

        widget.mark_completed(success=True)

        assert widget.pause_button.isEnabled() is False
        assert widget.cancel_button.isEnabled() is False

    def test_eta_and_speed_cleared_on_completion(self, qtbot: QtBot) -> None:
        """Test that ETA and speed are cleared when completed."""
        widget = ProgressCard(
            task_id="test-123",
            file_name="test.mp4",
            file_size="1 GB",
        )
        qtbot.addWidget(widget)

        widget.update_progress(50.0, eta="2:00", speed="1.5x")
        widget.mark_completed(success=True)

        assert widget.eta_label.text() == ""
        assert widget.speed_label.text() == ""


class TestProgressCardPauseResume:
    """Tests for ProgressCard pause/resume functionality."""

    def test_toggle_pause_changes_button_text(self, qtbot: QtBot) -> None:
        """Test that toggling pause changes button text."""
        widget = ProgressCard(
            task_id="test-123",
            file_name="test.mp4",
            file_size="1 GB",
        )
        qtbot.addWidget(widget)

        assert widget.pause_button.text() == "Pause"

        widget.toggle_pause()

        assert widget.pause_button.text() == "Resume"

    def test_toggle_pause_changes_status(self, qtbot: QtBot) -> None:
        """Test that toggling pause changes status."""
        widget = ProgressCard(
            task_id="test-123",
            file_name="test.mp4",
            file_size="1 GB",
        )
        qtbot.addWidget(widget)

        widget.toggle_pause()

        assert "Paused" in widget.status_label.text()

    def test_toggle_resume_changes_status(self, qtbot: QtBot) -> None:
        """Test that resuming changes status back to Converting."""
        widget = ProgressCard(
            task_id="test-123",
            file_name="test.mp4",
            file_size="1 GB",
        )
        qtbot.addWidget(widget)

        widget.toggle_pause()  # Pause
        widget.toggle_pause()  # Resume

        assert widget.status_label.text() == "Converting"


class TestProgressCardSignals:
    """Tests for ProgressCard signal emission."""

    def test_pause_requested_signal(self, qtbot: QtBot) -> None:
        """Test that pause button emits pause_requested signal."""
        widget = ProgressCard(
            task_id="test-123",
            file_name="test.mp4",
            file_size="1 GB",
        )
        qtbot.addWidget(widget)

        with qtbot.waitSignal(widget.pause_requested, timeout=1000):
            widget.pause_button.click()

    def test_cancel_requested_signal(self, qtbot: QtBot) -> None:
        """Test that cancel button emits cancel_requested signal."""
        widget = ProgressCard(
            task_id="test-123",
            file_name="test.mp4",
            file_size="1 GB",
        )
        qtbot.addWidget(widget)

        with qtbot.waitSignal(widget.cancel_requested, timeout=1000):
            widget.cancel_button.click()

    def test_pause_signal_after_click(self, qtbot: QtBot) -> None:
        """Test button state changes after pause signal."""
        widget = ProgressCard(
            task_id="test-123",
            file_name="test.mp4",
            file_size="1 GB",
        )
        qtbot.addWidget(widget)

        with qtbot.waitSignal(widget.pause_requested, timeout=1000):
            widget.pause_button.click()

        # Verify state changed to paused
        assert widget.pause_button.text() == "Resume"
