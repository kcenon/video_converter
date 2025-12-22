"""Unit tests for UI panels module.

This module tests the Rich panel components for displaying
permission errors and user guidance.
"""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from video_converter.ui.panels import (
    display_photos_library_info,
    display_photos_permission_error,
    display_photos_permission_success,
)


class TestDisplayPhotosPermissionError:
    """Tests for display_photos_permission_error function."""

    def test_access_denied_panel_displays(self) -> None:
        """Test access denied panel is displayed correctly."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display_photos_permission_error(
            console=console,
            error_type="access_denied",
        )

        result = output.getvalue()
        assert "Photos Library Access Denied" in result
        assert "Full Disk Access" in result
        assert "System Settings" in result
        assert "Terminal.app" in result
        assert "x-apple.systempreferences" in result

    def test_not_found_panel_displays(self) -> None:
        """Test library not found panel is displayed correctly."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display_photos_permission_error(
            console=console,
            error_type="not_found",
        )

        result = output.getvalue()
        assert "Photos Library Not Found" in result
        assert "Photos app has never been opened" in result
        assert "--library-path" in result

    def test_not_found_with_library_path(self) -> None:
        """Test library not found panel with custom path."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display_photos_permission_error(
            console=console,
            error_type="not_found",
            library_path="/custom/path/Photos Library.photoslibrary",
        )

        result = output.getvalue()
        assert "Photos Library Not Found" in result
        assert "/custom/path/Photos Library.photoslibrary" in result

    def test_default_console_used(self) -> None:
        """Test default console is used when none provided."""
        with patch("video_converter.ui.panels._console") as mock_console:
            mock_console.print = MagicMock()
            display_photos_permission_error(error_type="access_denied")
            mock_console.print.assert_called_once()


class TestDisplayPhotosPermissionSuccess:
    """Tests for display_photos_permission_success function."""

    def test_success_message_displays(self) -> None:
        """Test success message is displayed."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display_photos_permission_success(console=console)

        result = output.getvalue()
        assert "Photos library access granted" in result

    def test_default_console_used(self) -> None:
        """Test default console is used when none provided."""
        with patch("video_converter.ui.panels._console") as mock_console:
            mock_console.print = MagicMock()
            display_photos_permission_success()
            mock_console.print.assert_called_once()


class TestDisplayPhotosLibraryInfo:
    """Tests for display_photos_library_info function."""

    def test_library_info_displays(self) -> None:
        """Test library info panel displays correctly."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display_photos_library_info(
            console=console,
            library_path="/Users/test/Photos Library.photoslibrary",
            video_count=150,
            h264_count=45,
            total_size_gb=25.5,
        )

        result = output.getvalue()
        assert "Photos Library" in result
        assert "/Users/test/Photos Library.photoslibrary" in result
        assert "150" in result
        assert "45" in result
        assert "25.5" in result

    def test_estimated_savings_shown(self) -> None:
        """Test estimated savings is calculated and shown."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display_photos_library_info(
            console=console,
            video_count=100,
            h264_count=50,
            total_size_gb=20.0,
        )

        result = output.getvalue()
        # 50% savings expected
        assert "10.0" in result or "savings" in result.lower()

    def test_no_library_path_displays(self) -> None:
        """Test panel displays without library path."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display_photos_library_info(
            console=console,
            video_count=100,
            h264_count=50,
        )

        result = output.getvalue()
        assert "Photos Library" in result
        assert "100" in result
        assert "50" in result

    def test_default_console_used(self) -> None:
        """Test default console is used when none provided."""
        with patch("video_converter.ui.panels._console") as mock_console:
            mock_console.print = MagicMock()
            display_photos_library_info(
                video_count=100,
                h264_count=50,
            )
            mock_console.print.assert_called_once()
