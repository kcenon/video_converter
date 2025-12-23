"""Tests for the theme module.

This module tests the theme and styling functions for the GUI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


class TestIsDarkMode:
    """Tests for is_dark_mode function."""

    def test_dark_mode_detection_dark(self, qtbot: QtBot) -> None:
        """Test dark mode is detected when window lightness is low."""
        from video_converter.gui.styles.theme import is_dark_mode

        with patch("video_converter.gui.styles.theme.QApplication") as mock_app:
            mock_palette = MagicMock()
            mock_color = MagicMock()
            mock_color.lightness.return_value = 50  # Dark
            mock_palette.color.return_value = mock_color
            mock_app.palette.return_value = mock_palette

            result = is_dark_mode()
            assert result is True

    def test_dark_mode_detection_light(self, qtbot: QtBot) -> None:
        """Test light mode is detected when window lightness is high."""
        from video_converter.gui.styles.theme import is_dark_mode

        with patch("video_converter.gui.styles.theme.QApplication") as mock_app:
            mock_palette = MagicMock()
            mock_color = MagicMock()
            mock_color.lightness.return_value = 200  # Light
            mock_palette.color.return_value = mock_color
            mock_app.palette.return_value = mock_palette

            result = is_dark_mode()
            assert result is False

    def test_dark_mode_boundary(self, qtbot: QtBot) -> None:
        """Test the boundary value of 128 for dark mode."""
        from video_converter.gui.styles.theme import is_dark_mode

        with patch("video_converter.gui.styles.theme.QApplication") as mock_app:
            mock_palette = MagicMock()
            mock_color = MagicMock()
            mock_color.lightness.return_value = 128  # Boundary
            mock_palette.color.return_value = mock_color
            mock_app.palette.return_value = mock_palette

            result = is_dark_mode()
            assert result is False  # 128 is not < 128


class TestApplyMacosTheme:
    """Tests for apply_macos_theme function."""

    def test_apply_theme_dark_mode(self, qtbot: QtBot) -> None:
        """Test applying theme in dark mode."""
        from video_converter.gui.styles.theme import apply_macos_theme

        mock_app = MagicMock()

        with patch(
            "video_converter.gui.styles.theme.is_dark_mode", return_value=True
        ), patch(
            "video_converter.gui.styles.theme.get_dark_mode_stylesheet",
            return_value="dark_style",
        ):
            apply_macos_theme(mock_app)

            mock_app.setStyle.assert_called_once_with("macOS")
            mock_app.setStyleSheet.assert_called_once_with("dark_style")

    def test_apply_theme_light_mode(self, qtbot: QtBot) -> None:
        """Test applying theme in light mode."""
        from video_converter.gui.styles.theme import apply_macos_theme

        mock_app = MagicMock()

        with patch(
            "video_converter.gui.styles.theme.is_dark_mode", return_value=False
        ), patch(
            "video_converter.gui.styles.theme.get_light_mode_stylesheet",
            return_value="light_style",
        ):
            apply_macos_theme(mock_app)

            mock_app.setStyle.assert_called_once_with("macOS")
            mock_app.setStyleSheet.assert_called_once_with("light_style")


class TestGetBaseStylesheet:
    """Tests for get_base_stylesheet function."""

    def test_base_stylesheet_not_empty(self, qtbot: QtBot) -> None:
        """Test that base stylesheet is not empty."""
        from video_converter.gui.styles.theme import get_base_stylesheet

        stylesheet = get_base_stylesheet()
        assert stylesheet is not None
        assert len(stylesheet) > 0

    def test_base_stylesheet_contains_widget_styles(self, qtbot: QtBot) -> None:
        """Test that base stylesheet contains QWidget styles."""
        from video_converter.gui.styles.theme import get_base_stylesheet

        stylesheet = get_base_stylesheet()
        assert "QWidget" in stylesheet

    def test_base_stylesheet_contains_button_styles(self, qtbot: QtBot) -> None:
        """Test that base stylesheet contains QPushButton styles."""
        from video_converter.gui.styles.theme import get_base_stylesheet

        stylesheet = get_base_stylesheet()
        assert "QPushButton" in stylesheet

    def test_base_stylesheet_contains_progress_bar_styles(self, qtbot: QtBot) -> None:
        """Test that base stylesheet contains QProgressBar styles."""
        from video_converter.gui.styles.theme import get_base_stylesheet

        stylesheet = get_base_stylesheet()
        assert "QProgressBar" in stylesheet

    def test_base_stylesheet_contains_drop_zone_styles(self, qtbot: QtBot) -> None:
        """Test that base stylesheet contains drop zone styles."""
        from video_converter.gui.styles.theme import get_base_stylesheet

        stylesheet = get_base_stylesheet()
        assert "#dropZone" in stylesheet

    def test_base_stylesheet_contains_progress_card_styles(self, qtbot: QtBot) -> None:
        """Test that base stylesheet contains progress card styles."""
        from video_converter.gui.styles.theme import get_base_stylesheet

        stylesheet = get_base_stylesheet()
        assert "#progressCard" in stylesheet


class TestGetLightModeStylesheet:
    """Tests for get_light_mode_stylesheet function."""

    def test_light_stylesheet_not_empty(self, qtbot: QtBot) -> None:
        """Test that light mode stylesheet is not empty."""
        from video_converter.gui.styles.theme import get_light_mode_stylesheet

        stylesheet = get_light_mode_stylesheet()
        assert stylesheet is not None
        assert len(stylesheet) > 0

    def test_light_stylesheet_contains_base(self, qtbot: QtBot) -> None:
        """Test that light mode stylesheet includes base styles."""
        from video_converter.gui.styles.theme import (
            get_base_stylesheet,
            get_light_mode_stylesheet,
        )

        base = get_base_stylesheet()
        light = get_light_mode_stylesheet()
        assert base in light

    def test_light_stylesheet_has_light_colors(self, qtbot: QtBot) -> None:
        """Test that light mode stylesheet uses light colors."""
        from video_converter.gui.styles.theme import get_light_mode_stylesheet

        stylesheet = get_light_mode_stylesheet()
        # Light mode uses light backgrounds like #f5f5f7
        assert "#f5f5f7" in stylesheet

    def test_light_stylesheet_has_blue_accent(self, qtbot: QtBot) -> None:
        """Test that light mode uses blue accent color."""
        from video_converter.gui.styles.theme import get_light_mode_stylesheet

        stylesheet = get_light_mode_stylesheet()
        # Apple blue accent
        assert "#007aff" in stylesheet


class TestGetDarkModeStylesheet:
    """Tests for get_dark_mode_stylesheet function."""

    def test_dark_stylesheet_not_empty(self, qtbot: QtBot) -> None:
        """Test that dark mode stylesheet is not empty."""
        from video_converter.gui.styles.theme import get_dark_mode_stylesheet

        stylesheet = get_dark_mode_stylesheet()
        assert stylesheet is not None
        assert len(stylesheet) > 0

    def test_dark_stylesheet_contains_base(self, qtbot: QtBot) -> None:
        """Test that dark mode stylesheet includes base styles."""
        from video_converter.gui.styles.theme import (
            get_base_stylesheet,
            get_dark_mode_stylesheet,
        )

        base = get_base_stylesheet()
        dark = get_dark_mode_stylesheet()
        assert base in dark

    def test_dark_stylesheet_has_dark_colors(self, qtbot: QtBot) -> None:
        """Test that dark mode stylesheet uses dark colors."""
        from video_converter.gui.styles.theme import get_dark_mode_stylesheet

        stylesheet = get_dark_mode_stylesheet()
        # Dark mode uses dark backgrounds like #1c1c1e
        assert "#1c1c1e" in stylesheet

    def test_dark_stylesheet_has_blue_accent(self, qtbot: QtBot) -> None:
        """Test that dark mode uses blue accent color."""
        from video_converter.gui.styles.theme import get_dark_mode_stylesheet

        stylesheet = get_dark_mode_stylesheet()
        # Apple blue accent for dark mode
        assert "#0a84ff" in stylesheet

    def test_dark_stylesheet_different_from_light(self, qtbot: QtBot) -> None:
        """Test that dark and light stylesheets are different."""
        from video_converter.gui.styles.theme import (
            get_dark_mode_stylesheet,
            get_light_mode_stylesheet,
        )

        light = get_light_mode_stylesheet()
        dark = get_dark_mode_stylesheet()
        assert light != dark
