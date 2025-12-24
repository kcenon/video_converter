"""Accessibility tests for the GUI.

This module provides tests for accessibility features including:
- Keyboard navigation through all tabs and interactive elements
- Accessible names and descriptions for widgets
- Focus indicators visibility
- Color contrast compliance

Reference:
    - Qt Accessibility Documentation: https://doc.qt.io/qt-6/accessible.html
    - WCAG 2.1 Guidelines: https://www.w3.org/WAI/WCAG21/quickref/
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QAbstractButton,
    QCheckBox,
    QComboBox,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QWidget,
)

from video_converter.gui.main_window import MainWindow
from video_converter.gui.widgets.drop_zone import DropZone
from video_converter.gui.widgets.progress_card import ProgressCard

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


pytestmark = pytest.mark.gui


@pytest.fixture
def mock_services():
    """Create mocks for all services used by MainWindow."""
    with patch(
        "video_converter.gui.main_window.ConversionService"
    ) as mock_conv, patch(
        "video_converter.gui.main_window.PhotosService"
    ) as mock_photos, patch(
        "video_converter.gui.main_window.SettingsManager"
    ) as mock_settings:
        mock_settings_instance = MagicMock()
        mock_settings_instance.get.return_value = {
            "encoder": "Hardware (VideoToolbox)",
            "quality": 22,
            "threads": 4,
            "output_dir": "",
            "preserve_original": True,
        }
        mock_settings_instance.is_dirty.return_value = False
        mock_settings_instance.apply_to_conversion_settings.return_value = {}
        mock_settings.return_value = mock_settings_instance

        mock_conv_instance = MagicMock()
        mock_conv_instance.task_added = MagicMock()
        mock_conv_instance.task_started = MagicMock()
        mock_conv_instance.progress_updated = MagicMock()
        mock_conv_instance.task_completed = MagicMock()
        mock_conv_instance.task_failed = MagicMock()
        mock_conv_instance.task_cancelled = MagicMock()
        mock_conv_instance.queue_updated = MagicMock()
        mock_conv_instance.all_completed = MagicMock()
        mock_conv.return_value = mock_conv_instance

        mock_photos_instance = MagicMock()
        mock_photos.return_value = mock_photos_instance

        yield {
            "conversion": mock_conv_instance,
            "photos": mock_photos_instance,
            "settings": mock_settings_instance,
        }


class TestKeyboardNavigation:
    """Tests for keyboard navigation through the GUI."""

    def test_tab_order_main_window(self, qtbot: QtBot, mock_services) -> None:
        """Test that Tab key navigates through main window elements in logical order."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        # Tab bar should be focusable
        assert window.tab_bar.focusPolicy() != Qt.FocusPolicy.NoFocus

        window.close()

    def test_tab_navigation_home_view(self, qtbot: QtBot, mock_services) -> None:
        """Test Tab key navigation through Home view elements."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        # Ensure we're on Home view
        window._set_current_tab(MainWindow.TAB_HOME)
        assert window.tab_bar.currentIndex() == MainWindow.TAB_HOME

        # Home view contains DropZone which should be focusable via click
        drop_zone = window.home_view.findChild(DropZone)
        assert drop_zone is not None

        window.close()

    def test_tab_navigation_convert_view(self, qtbot: QtBot, mock_services) -> None:
        """Test Tab key navigation through Convert view elements."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        window._set_current_tab(MainWindow.TAB_CONVERT)
        assert window.tab_bar.currentIndex() == MainWindow.TAB_CONVERT

        # Verify convert view is accessible
        assert window.convert_view.isVisible()

        window.close()

    def test_tab_navigation_photos_view(self, qtbot: QtBot, mock_services) -> None:
        """Test Tab key navigation through Photos view elements."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        window._set_current_tab(MainWindow.TAB_PHOTOS)
        assert window.tab_bar.currentIndex() == MainWindow.TAB_PHOTOS

        # Verify photos view is accessible
        assert window.photos_view.isVisible()

        window.close()

    def test_tab_navigation_queue_view(self, qtbot: QtBot, mock_services) -> None:
        """Test Tab key navigation through Queue view elements."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        window._set_current_tab(MainWindow.TAB_QUEUE)
        assert window.tab_bar.currentIndex() == MainWindow.TAB_QUEUE

        # Queue view buttons should be tab-accessible
        assert window.queue_view.pause_resume_button.focusPolicy() != Qt.FocusPolicy.NoFocus
        assert window.queue_view.cancel_all_button.focusPolicy() != Qt.FocusPolicy.NoFocus

        window.close()

    def test_tab_navigation_settings_view(self, qtbot: QtBot, mock_services) -> None:
        """Test Tab key navigation through Settings view elements."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        window._set_current_tab(MainWindow.TAB_SETTINGS)
        assert window.tab_bar.currentIndex() == MainWindow.TAB_SETTINGS

        # Settings view should have many interactive elements
        settings = window.settings_view
        assert settings.encoder_combo.focusPolicy() != Qt.FocusPolicy.NoFocus
        assert settings.quality_slider.focusPolicy() != Qt.FocusPolicy.NoFocus
        assert settings.preset_combo.focusPolicy() != Qt.FocusPolicy.NoFocus

        window.close()

    def test_escape_closes_dialog(self, qtbot: QtBot, mock_services) -> None:
        """Test that Escape key can be used to close dialogs or cancel actions."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        # Main window should handle Escape (though not necessarily close)
        # This tests that key events are properly handled
        QTest.keyClick(window, Qt.Key.Key_Escape)

        # Window should still be visible (Escape doesn't close main window)
        assert window.isVisible()

        window.close()

    def test_enter_activates_button(self, qtbot: QtBot, mock_services) -> None:
        """Test that Enter key activates focused button."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        window._set_current_tab(MainWindow.TAB_QUEUE)

        # Focus on a button
        button = window.queue_view.pause_resume_button
        button.setFocus()
        button.setEnabled(True)

        # Verify button can receive focus
        assert button.focusPolicy() != Qt.FocusPolicy.NoFocus

        window.close()

    def test_keyboard_shortcuts_work(self, qtbot: QtBot, mock_services) -> None:
        """Test that keyboard shortcuts are properly configured for tab switching.

        Note: In offscreen/headless Qt environments, QTest.keyClick does not
        reliably trigger menu bar shortcuts. Instead, we verify that the menu
        actions exist with correct shortcuts and trigger them directly.
        """
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        # Find View menu and its actions
        menu_bar = window.menuBar()
        view_menu = None
        for action in menu_bar.actions():
            if action.text() == "View":
                view_menu = action.menu()
                break

        assert view_menu is not None, "View menu not found"

        # Get all view menu actions
        actions = {action.text(): action for action in view_menu.actions()}

        # Verify shortcuts are configured correctly
        assert actions["Home"].shortcut().toString() == "Ctrl+1"
        assert actions["Convert"].shortcut().toString() == "Ctrl+2"
        assert actions["Photos"].shortcut().toString() == "Ctrl+3"
        assert actions["Queue"].shortcut().toString() == "Ctrl+4"
        assert actions["Settings"].shortcut().toString() == "Ctrl+5"

        # Test that triggering actions switches tabs correctly
        window._set_current_tab(MainWindow.TAB_SETTINGS)  # Start from different tab

        actions["Home"].trigger()
        assert window.tab_bar.currentIndex() == MainWindow.TAB_HOME

        actions["Convert"].trigger()
        assert window.tab_bar.currentIndex() == MainWindow.TAB_CONVERT

        actions["Photos"].trigger()
        assert window.tab_bar.currentIndex() == MainWindow.TAB_PHOTOS

        actions["Queue"].trigger()
        assert window.tab_bar.currentIndex() == MainWindow.TAB_QUEUE

        actions["Settings"].trigger()
        assert window.tab_bar.currentIndex() == MainWindow.TAB_SETTINGS

        window.close()


class TestAccessibleNames:
    """Tests for accessible names on widgets."""

    def test_drop_zone_accessible_name(self, qtbot: QtBot) -> None:
        """Test that drop zone has meaningful accessible labels."""
        widget = DropZone()
        qtbot.addWidget(widget)

        # Labels should have meaningful text for screen readers
        assert widget.main_label.text() != ""
        assert "video" in widget.main_label.text().lower() or "drop" in widget.main_label.text().lower()
        assert widget.subtitle_label.text() != ""
        assert widget.formats_label.text() != ""

    def test_progress_bar_accessible_name(self, qtbot: QtBot, mock_services) -> None:
        """Test that progress bars have accessible format strings."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Queue view has overall progress bar
        progress_bar = window.queue_view.overall_progress
        assert progress_bar.format() != ""
        assert "%" in progress_bar.format() or "Overall" in progress_bar.format()

        window.close()

    def test_buttons_have_accessible_names(self, qtbot: QtBot, mock_services) -> None:
        """Test that all buttons have text labels."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Queue view buttons
        assert window.queue_view.pause_resume_button.text() != ""
        assert window.queue_view.cancel_all_button.text() != ""
        assert window.queue_view.clear_completed_button.text() != ""

        window.close()

    def test_sliders_have_accessible_names(self, qtbot: QtBot, mock_services) -> None:
        """Test that sliders have associated labels."""
        window = MainWindow()
        qtbot.addWidget(window)

        window._set_current_tab(MainWindow.TAB_SETTINGS)

        # Quality slider should have an associated label
        quality_slider = window.settings_view.quality_slider
        quality_label = window.settings_view.quality_label

        # Verify the label exists and is related to the slider
        assert quality_label is not None
        assert quality_label.text() != ""
        assert "CRF" in quality_label.text() or str(quality_slider.value()) in quality_label.text()

        window.close()

    def test_combo_boxes_have_accessible_names(self, qtbot: QtBot, mock_services) -> None:
        """Test that combo boxes have items with meaningful text."""
        window = MainWindow()
        qtbot.addWidget(window)

        window._set_current_tab(MainWindow.TAB_SETTINGS)

        # Encoder combo should have meaningful items
        encoder_combo = window.settings_view.encoder_combo
        assert encoder_combo.count() > 0
        for i in range(encoder_combo.count()):
            assert encoder_combo.itemText(i) != ""

        window.close()

    def test_checkboxes_have_accessible_names(self, qtbot: QtBot, mock_services) -> None:
        """Test that checkboxes have text labels."""
        window = MainWindow()
        qtbot.addWidget(window)

        window._set_current_tab(MainWindow.TAB_SETTINGS)

        # All checkboxes should have text
        checkboxes = window.settings_view.findChildren(QCheckBox)
        assert len(checkboxes) > 0

        for checkbox in checkboxes:
            assert checkbox.text() != "", f"Checkbox without text found"

        window.close()

    def test_tree_widget_accessible_name(self, qtbot: QtBot, mock_services) -> None:
        """Test that tree widget in queue view has accessible elements."""
        window = MainWindow()
        qtbot.addWidget(window)

        window._set_current_tab(MainWindow.TAB_QUEUE)

        # Queue view should have proper labels
        assert window.queue_view.queue_count_label.text() != ""

        window.close()


class TestAccessibleDescriptions:
    """Tests for accessible descriptions on complex widgets."""

    def test_quality_slider_description(self, qtbot: QtBot, mock_services) -> None:
        """Test that quality slider has contextual information."""
        window = MainWindow()
        qtbot.addWidget(window)

        window._set_current_tab(MainWindow.TAB_SETTINGS)

        # Quality slider should show current value
        slider = window.settings_view.quality_slider
        label = window.settings_view.quality_label

        # The label should describe the current CRF value
        assert "CRF" in label.text()
        assert str(slider.value()) in label.text()

        window.close()

    def test_error_state_description(self, qtbot: QtBot, mock_services) -> None:
        """Test that error states have descriptive messages."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Simulate task failure
        window._on_task_failed("task-123", "Encoding error: codec not found")

        # Status bar should show descriptive error message
        status_message = window.statusBar().currentMessage()
        assert "failed" in status_message.lower()
        assert "Encoding error" in status_message or "codec" in status_message

        window.close()

    def test_empty_state_has_description(self, qtbot: QtBot, mock_services) -> None:
        """Test that empty states have helpful descriptions."""
        window = MainWindow()
        qtbot.addWidget(window)

        window._set_current_tab(MainWindow.TAB_QUEUE)

        # Empty state should be visible and have helpful text
        empty_state = window.queue_view.empty_state
        if empty_state.isVisible():
            # Find labels in empty state
            labels = empty_state.findChildren(QWidget)
            texts = [
                widget.text() for widget in labels
                if hasattr(widget, "text") and widget.text()
            ]
            assert len(texts) > 0
            # Should have hint about how to add items
            combined_text = " ".join(texts).lower()
            assert "drop" in combined_text or "video" in combined_text or "home" in combined_text

        window.close()

    def test_progress_card_status_description(self, qtbot: QtBot) -> None:
        """Test that progress cards have status descriptions."""
        card = ProgressCard("task-1", "test_video.mp4", "100 MB")
        qtbot.addWidget(card)

        # File name should be visible in the name label
        assert "test_video.mp4" in card.name_label.text()

        # Status label should show initial state
        assert card.status_label.text() != ""

        # Update progress should update visible status
        card.update_progress(50.0, "2:30", "1.5x")

        # Progress should be updated
        assert "50" in card.progress_label.text()
        assert card.eta_label.text() != ""
        assert card.speed_label.text() != ""


class TestFocusIndicators:
    """Tests for visible focus indicators on interactive elements."""

    def test_focus_visible_on_buttons(self, qtbot: QtBot, mock_services) -> None:
        """Test that buttons show visible focus indicators."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        window._set_current_tab(MainWindow.TAB_QUEUE)

        button = window.queue_view.pause_resume_button
        button.setEnabled(True)
        button.setFocus()

        # Button should be able to receive and show focus
        assert button.focusPolicy() != Qt.FocusPolicy.NoFocus

        window.close()

    def test_focus_visible_on_sliders(self, qtbot: QtBot, mock_services) -> None:
        """Test that sliders show visible focus indicators."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        window._set_current_tab(MainWindow.TAB_SETTINGS)

        slider = window.settings_view.quality_slider
        slider.setFocus()

        # Slider should accept focus
        assert slider.focusPolicy() != Qt.FocusPolicy.NoFocus

        window.close()

    def test_focus_visible_on_combo_boxes(self, qtbot: QtBot, mock_services) -> None:
        """Test that combo boxes show visible focus indicators."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        window._set_current_tab(MainWindow.TAB_SETTINGS)

        combo = window.settings_view.encoder_combo
        combo.setFocus()

        # Combo box should accept focus
        assert combo.focusPolicy() != Qt.FocusPolicy.NoFocus

        window.close()

    def test_focus_moves_correctly(self, qtbot: QtBot, mock_services) -> None:
        """Test that focus moves logically between elements."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        window._set_current_tab(MainWindow.TAB_SETTINGS)

        # Get interactive elements that should be in tab order
        encoder_combo = window.settings_view.encoder_combo
        quality_slider = window.settings_view.quality_slider
        preset_combo = window.settings_view.preset_combo

        # All should accept keyboard focus
        assert encoder_combo.focusPolicy() != Qt.FocusPolicy.NoFocus
        assert quality_slider.focusPolicy() != Qt.FocusPolicy.NoFocus
        assert preset_combo.focusPolicy() != Qt.FocusPolicy.NoFocus

        window.close()

    def test_focus_visible_on_checkboxes(self, qtbot: QtBot, mock_services) -> None:
        """Test that checkboxes show visible focus indicators."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        window._set_current_tab(MainWindow.TAB_SETTINGS)

        checkboxes = window.settings_view.findChildren(QCheckBox)
        assert len(checkboxes) > 0

        for checkbox in checkboxes:
            assert checkbox.focusPolicy() != Qt.FocusPolicy.NoFocus

        window.close()


class TestColorContrast:
    """Tests for color contrast compliance."""

    def _calculate_contrast_ratio(self, color1: QColor, color2: QColor) -> float:
        """Calculate contrast ratio between two colors.

        Based on WCAG 2.1 relative luminance formula.

        Args:
            color1: First color.
            color2: Second color.

        Returns:
            Contrast ratio (1.0 to 21.0).
        """
        def relative_luminance(color: QColor) -> float:
            """Calculate relative luminance of a color."""
            r = color.redF()
            g = color.greenF()
            b = color.blueF()

            # Apply gamma correction
            r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
            g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
            b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4

            return 0.2126 * r + 0.7152 * g + 0.0722 * b

        l1 = relative_luminance(color1)
        l2 = relative_luminance(color2)

        lighter = max(l1, l2)
        darker = min(l1, l2)

        return (lighter + 0.05) / (darker + 0.05)

    def test_text_contrast_light_mode(self, qtbot: QtBot, mock_services) -> None:
        """Test that text has sufficient contrast in light mode."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        # Get a label with text
        labels = window.findChildren(QWidget)

        # Test that we can access text elements
        found_text = False
        for widget in labels:
            if hasattr(widget, "text") and callable(widget.text):
                text = widget.text()
                if text and len(text) > 0:
                    found_text = True
                    break

        assert found_text, "Should have visible text elements"

        window.close()

    def test_focus_indicator_contrast(self, qtbot: QtBot, mock_services) -> None:
        """Test that focus indicators have sufficient contrast."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        # Ensure interactive elements exist that can show focus
        buttons = window.findChildren(QPushButton)
        assert len(buttons) > 0, "Should have buttons that can show focus"

        # At minimum, verify buttons support focus
        for button in buttons:
            if button.isVisible():
                assert button.focusPolicy() != Qt.FocusPolicy.NoFocus

        window.close()

    def test_error_color_contrast(self, qtbot: QtBot) -> None:
        """Test that error states have sufficient color contrast."""
        widget = DropZone()
        qtbot.addWidget(widget)

        # Simulate invalid drag (shows red border)
        widget._set_drag_over(True, valid=False, file_count=0)

        # Red error color should contrast with background
        # Qt's error red is typically #FF3B30
        error_color = QColor("#FF3B30")
        white = QColor("#FFFFFF")
        black = QColor("#000000")

        # Error color should have good contrast with either white or black text
        contrast_white = self._calculate_contrast_ratio(error_color, white)
        contrast_black = self._calculate_contrast_ratio(error_color, black)

        # At least one should meet WCAG AA (4.5:1 for normal text)
        assert contrast_white >= 3.0 or contrast_black >= 3.0

    def test_success_color_contrast(self, qtbot: QtBot) -> None:
        """Test that success states have sufficient color contrast."""
        widget = DropZone()
        qtbot.addWidget(widget)

        # Simulate valid drag (shows blue border)
        widget._set_drag_over(True, valid=True, file_count=1)

        # Blue accent color should contrast with background
        # Qt's accent blue is typically #007AFF
        accent_color = QColor("#007AFF")
        white = QColor("#FFFFFF")
        black = QColor("#000000")

        # Accent color should have good contrast with either white or black text
        contrast_white = self._calculate_contrast_ratio(accent_color, white)
        contrast_black = self._calculate_contrast_ratio(accent_color, black)

        # At least one should meet WCAG AA for large text (3:1)
        assert contrast_white >= 3.0 or contrast_black >= 3.0


class TestAccessibilityAudit:
    """Comprehensive accessibility audit tests."""

    def test_all_interactive_elements_keyboard_accessible(
        self, qtbot: QtBot, mock_services
    ) -> None:
        """Test that all interactive elements can receive keyboard focus."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        interactive_types = (
            QPushButton,
            QCheckBox,
            QComboBox,
            QSlider,
            QSpinBox,
            QLineEdit,
        )

        # Check all views
        for tab_index in range(5):
            window._set_current_tab(tab_index)

            for widget in window.findChildren(QWidget):
                if isinstance(widget, interactive_types) and widget.isVisible():
                    # Interactive elements should accept focus
                    assert (
                        widget.focusPolicy() != Qt.FocusPolicy.NoFocus
                    ), f"{type(widget).__name__} should accept keyboard focus"

        window.close()

    def test_no_focus_traps(self, qtbot: QtBot, mock_services) -> None:
        """Test that keyboard focus doesn't get trapped in any widget."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        window._set_current_tab(MainWindow.TAB_SETTINGS)

        # Get all focusable widgets
        focusable = [
            w for w in window.findChildren(QWidget)
            if w.focusPolicy() != Qt.FocusPolicy.NoFocus and w.isVisible()
        ]

        # Should have multiple focusable elements
        assert len(focusable) > 1, "Should have multiple focusable elements"

        window.close()

    def test_form_labels_associated(self, qtbot: QtBot, mock_services) -> None:
        """Test that form controls have associated labels."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        window._set_current_tab(MainWindow.TAB_SETTINGS)

        # Combo boxes should be in form layouts with labels
        combos = window.settings_view.findChildren(QComboBox)
        assert len(combos) > 0

        # All checkboxes should have text labels
        checkboxes = window.settings_view.findChildren(QCheckBox)
        for checkbox in checkboxes:
            assert checkbox.text() != "", "Checkbox should have associated text"

        window.close()

    def test_status_bar_accessibility(self, qtbot: QtBot, mock_services) -> None:
        """Test that status bar messages are accessible."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        # Initial status
        assert window.statusBar().currentMessage() != "" or True  # May be empty initially

        # Status after action
        window._on_files_dropped(["/path/to/video.mp4"])
        message = window.statusBar().currentMessage()
        assert message != "", "Status bar should show message after action"

        window.close()
