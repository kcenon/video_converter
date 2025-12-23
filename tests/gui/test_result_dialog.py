"""Tests for the ConversionResultDialog.

This module tests the conversion result dialog for displaying
conversion results and statistics.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from video_converter.gui.dialogs.result_dialog import ConversionResultDialog

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


pytestmark = pytest.mark.gui


def create_mock_result(
    success: bool = True,
    input_name: str = "test_video.mp4",
    output_name: str = "test_video_converted.mp4",
    original_size: int = 10_000_000,
    converted_size: int = 5_000_000,
    duration_seconds: float = 30.0,
    speed_ratio: float = 2.5,
    vmaf_score: float | None = None,
    vmaf_quality_level: str | None = None,
    error_message: str | None = None,
    warnings: list[str] | None = None,
) -> MagicMock:
    """Create a mock ConversionResult for testing.

    Args:
        success: Whether conversion was successful.
        input_name: Input file name.
        output_name: Output file name.
        original_size: Original file size in bytes.
        converted_size: Converted file size in bytes.
        duration_seconds: Conversion duration.
        speed_ratio: Conversion speed ratio.
        vmaf_score: VMAF quality score.
        vmaf_quality_level: VMAF quality classification.
        error_message: Error message for failed conversions.
        warnings: List of warning messages.

    Returns:
        Mock ConversionResult object.
    """
    mock_request = MagicMock()
    mock_request.input_path = Path(f"/path/to/{input_name}")
    mock_request.input_path.name = input_name
    mock_request.output_path = Path(f"/path/to/{output_name}")
    mock_request.output_path.name = output_name
    mock_request.output_path.exists.return_value = True

    mock_result = MagicMock()
    mock_result.success = success
    mock_result.request = mock_request
    mock_result.original_size = original_size
    mock_result.converted_size = converted_size
    mock_result.size_saved = original_size - converted_size
    mock_result.compression_ratio = (original_size - converted_size) / original_size if original_size > 0 else 0
    mock_result.duration_seconds = duration_seconds
    mock_result.speed_ratio = speed_ratio
    mock_result.vmaf_score = vmaf_score
    mock_result.vmaf_quality_level = vmaf_quality_level
    mock_result.error_message = error_message
    mock_result.warnings = warnings or []

    return mock_result


class TestConversionResultDialogCreation:
    """Tests for ConversionResultDialog creation."""

    def test_dialog_creates_successfully(self, qtbot: QtBot) -> None:
        """Test that dialog can be created without errors."""
        mock_result = create_mock_result()
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        assert dialog is not None

    def test_dialog_has_correct_title(self, qtbot: QtBot) -> None:
        """Test that dialog has the expected title."""
        mock_result = create_mock_result()
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Conversion Complete"

    def test_dialog_is_modal(self, qtbot: QtBot) -> None:
        """Test that dialog is modal."""
        mock_result = create_mock_result()
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        assert dialog.isModal() is True

    def test_dialog_minimum_width(self, qtbot: QtBot) -> None:
        """Test dialog has minimum width."""
        mock_result = create_mock_result()
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        assert dialog.minimumWidth() >= 400


class TestSuccessDialog:
    """Tests for successful conversion result display."""

    def test_success_icon_displayed(self, qtbot: QtBot) -> None:
        """Test that success icon is shown for successful conversions."""
        mock_result = create_mock_result(success=True)
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        # Find icon label - should contain success emoji
        from PySide6.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)
        icon_labels = [l for l in labels if l.objectName() == "resultIcon"]

        assert len(icon_labels) == 1
        assert "✅" in icon_labels[0].text()

    def test_success_status_text(self, qtbot: QtBot) -> None:
        """Test that success status text is displayed."""
        mock_result = create_mock_result(success=True)
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        from PySide6.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)
        status_labels = [l for l in labels if l.objectName() == "resultStatus"]

        assert len(status_labels) == 1
        assert "Successful" in status_labels[0].text()

    def test_file_name_displayed(self, qtbot: QtBot) -> None:
        """Test that file name is displayed."""
        mock_result = create_mock_result(input_name="my_video.mp4")
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        from PySide6.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)
        file_labels = [l for l in labels if l.objectName() == "resultFileName"]

        assert len(file_labels) == 1
        assert "my_video.mp4" in file_labels[0].text()

    def test_show_in_finder_button_visible(self, qtbot: QtBot) -> None:
        """Test that 'Show in Finder' button is visible for successful conversions."""
        mock_result = create_mock_result(success=True)
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        from PySide6.QtWidgets import QPushButton
        buttons = dialog.findChildren(QPushButton)
        finder_buttons = [b for b in buttons if "Finder" in b.text()]

        assert len(finder_buttons) == 1


class TestFailureDialog:
    """Tests for failed conversion result display."""

    def test_failure_icon_displayed(self, qtbot: QtBot) -> None:
        """Test that failure icon is shown for failed conversions."""
        mock_result = create_mock_result(
            success=False,
            error_message="Encoding failed",
        )
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        from PySide6.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)
        icon_labels = [l for l in labels if l.objectName() == "resultIcon"]

        assert len(icon_labels) == 1
        assert "❌" in icon_labels[0].text()

    def test_failure_status_text(self, qtbot: QtBot) -> None:
        """Test that failure status text is displayed."""
        mock_result = create_mock_result(
            success=False,
            error_message="Encoding failed",
        )
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        from PySide6.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)
        status_labels = [l for l in labels if l.objectName() == "resultStatus"]

        assert len(status_labels) == 1
        assert "Failed" in status_labels[0].text()

    def test_error_message_displayed(self, qtbot: QtBot) -> None:
        """Test that error message is displayed for failed conversions."""
        error_msg = "FFmpeg encoding failed with error code 1"
        mock_result = create_mock_result(
            success=False,
            error_message=error_msg,
        )
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        from PySide6.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)
        error_labels = [l for l in labels if error_msg in l.text()]

        assert len(error_labels) == 1

    def test_no_show_in_finder_for_failure(self, qtbot: QtBot) -> None:
        """Test that 'Show in Finder' button is not visible for failed conversions."""
        mock_result = create_mock_result(
            success=False,
            error_message="Encoding failed",
        )
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        from PySide6.QtWidgets import QPushButton
        buttons = dialog.findChildren(QPushButton)
        finder_buttons = [b for b in buttons if "Finder" in b.text()]

        assert len(finder_buttons) == 0


class TestStatisticsDisplay:
    """Tests for conversion statistics display."""

    def test_original_size_displayed(self, qtbot: QtBot) -> None:
        """Test that original file size is displayed."""
        mock_result = create_mock_result(original_size=10_485_760)  # 10 MB
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        from PySide6.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)
        # Look for size-related labels
        has_original_size = any("Original" in l.text() or "10" in l.text() for l in labels)

        assert has_original_size is True

    def test_converted_size_displayed(self, qtbot: QtBot) -> None:
        """Test that converted file size is displayed."""
        mock_result = create_mock_result(converted_size=5_242_880)  # 5 MB
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        from PySide6.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)
        # Look for converted size label
        has_converted_size = any("Converted" in l.text() or "5" in l.text() for l in labels)

        assert has_converted_size is True

    def test_space_saved_displayed(self, qtbot: QtBot) -> None:
        """Test that space saved is displayed."""
        mock_result = create_mock_result(
            original_size=10_000_000,
            converted_size=5_000_000,
        )
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        from PySide6.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)
        has_saved = any("Saved" in l.text() for l in labels)

        assert has_saved is True

    def test_compression_ratio_displayed(self, qtbot: QtBot) -> None:
        """Test that compression ratio is displayed."""
        mock_result = create_mock_result(
            original_size=10_000_000,
            converted_size=5_000_000,  # 50% compression
        )
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        from PySide6.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)
        # Look for percentage
        has_percentage = any("%" in l.text() for l in labels)

        assert has_percentage is True

    def test_duration_displayed_when_positive(self, qtbot: QtBot) -> None:
        """Test that duration is displayed when greater than zero."""
        mock_result = create_mock_result(duration_seconds=45.5)
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        from PySide6.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)
        has_duration = any("Duration" in l.text() for l in labels)

        assert has_duration is True

    def test_speed_ratio_displayed(self, qtbot: QtBot) -> None:
        """Test that speed ratio is displayed."""
        mock_result = create_mock_result(speed_ratio=2.5)
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        from PySide6.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)
        has_speed = any("Speed" in l.text() or "realtime" in l.text() for l in labels)

        assert has_speed is True

    def test_vmaf_score_displayed_when_available(self, qtbot: QtBot) -> None:
        """Test that VMAF score is displayed when available."""
        mock_result = create_mock_result(
            vmaf_score=92.5,
            vmaf_quality_level="Excellent",
        )
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        from PySide6.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)
        has_vmaf = any("VMAF" in l.text() or "Quality" in l.text() for l in labels)

        assert has_vmaf is True


class TestWarningsDisplay:
    """Tests for warnings display."""

    def test_warnings_displayed_when_present(self, qtbot: QtBot) -> None:
        """Test that warnings are displayed when present."""
        mock_result = create_mock_result(
            warnings=["Audio codec not supported", "Metadata may be incomplete"],
        )
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        from PySide6.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)
        has_warning_header = any("Warning" in l.text() for l in labels)

        assert has_warning_header is True

    def test_multiple_warnings_displayed(self, qtbot: QtBot) -> None:
        """Test that multiple warnings are displayed."""
        warnings = [
            "Warning 1",
            "Warning 2",
            "Warning 3",
        ]
        mock_result = create_mock_result(warnings=warnings)
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        from PySide6.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)
        warning_count = sum(1 for l in labels if "Warning" in l.text())

        # At least header + some warnings should be visible
        assert warning_count >= 1

    def test_max_five_warnings_shown(self, qtbot: QtBot) -> None:
        """Test that only up to 5 warnings are shown."""
        warnings = [f"Warning {i}" for i in range(10)]
        mock_result = create_mock_result(warnings=warnings)
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        from PySide6.QtWidgets import QLabel
        labels = dialog.findChildren(QLabel)
        # Should show "... and N more" label
        has_more_label = any("more" in l.text() for l in labels)

        assert has_more_label is True


class TestDialogActions:
    """Tests for dialog action buttons."""

    def test_close_button_exists(self, qtbot: QtBot) -> None:
        """Test that close button exists."""
        mock_result = create_mock_result()
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        from PySide6.QtWidgets import QPushButton
        buttons = dialog.findChildren(QPushButton)
        close_buttons = [b for b in buttons if "Close" in b.text()]

        assert len(close_buttons) == 1

    def test_close_button_is_default(self, qtbot: QtBot) -> None:
        """Test that close button is the default button."""
        mock_result = create_mock_result()
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        from PySide6.QtWidgets import QPushButton
        buttons = dialog.findChildren(QPushButton)
        close_buttons = [b for b in buttons if "Close" in b.text()]

        assert len(close_buttons) == 1
        assert close_buttons[0].isDefault() is True

    def test_close_button_accepts_dialog(self, qtbot: QtBot) -> None:
        """Test that close button closes the dialog."""
        mock_result = create_mock_result()
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        from PySide6.QtWidgets import QPushButton
        buttons = dialog.findChildren(QPushButton)
        close_button = next(b for b in buttons if "Close" in b.text())

        with qtbot.waitSignal(dialog.accepted, timeout=1000):
            close_button.click()

    def test_show_in_finder_opens_subprocess(self, qtbot: QtBot) -> None:
        """Test that 'Show in Finder' opens the file location."""
        mock_result = create_mock_result()
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        with patch("subprocess.run") as mock_run:
            dialog._on_show_in_finder()
            mock_run.assert_called_once()
            # Should call 'open -R' command
            call_args = mock_run.call_args[0][0]
            assert "open" in call_args
            assert "-R" in call_args


class TestFormatMethods:
    """Tests for format helper methods."""

    def test_format_size_bytes(self, qtbot: QtBot) -> None:
        """Test size formatting for bytes."""
        mock_result = create_mock_result()
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        result = dialog._format_size(500)
        assert "B" in result
        assert "500" in result

    def test_format_size_kilobytes(self, qtbot: QtBot) -> None:
        """Test size formatting for kilobytes."""
        mock_result = create_mock_result()
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        result = dialog._format_size(5120)  # 5 KB
        assert "KB" in result

    def test_format_size_megabytes(self, qtbot: QtBot) -> None:
        """Test size formatting for megabytes."""
        mock_result = create_mock_result()
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        result = dialog._format_size(5_242_880)  # 5 MB
        assert "MB" in result

    def test_format_size_gigabytes(self, qtbot: QtBot) -> None:
        """Test size formatting for gigabytes."""
        mock_result = create_mock_result()
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        result = dialog._format_size(2_147_483_648)  # 2 GB
        assert "GB" in result

    def test_format_duration_seconds(self, qtbot: QtBot) -> None:
        """Test duration formatting for seconds only."""
        mock_result = create_mock_result()
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        result = dialog._format_duration(45.5)
        assert "s" in result
        assert "m" not in result

    def test_format_duration_minutes(self, qtbot: QtBot) -> None:
        """Test duration formatting for minutes."""
        mock_result = create_mock_result()
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        result = dialog._format_duration(125)  # 2m 5s
        assert "m" in result

    def test_format_duration_hours(self, qtbot: QtBot) -> None:
        """Test duration formatting for hours."""
        mock_result = create_mock_result()
        dialog = ConversionResultDialog(mock_result)
        qtbot.addWidget(dialog)

        result = dialog._format_duration(7500)  # 2h 5m
        assert "h" in result
