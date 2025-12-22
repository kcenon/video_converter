"""Unit tests for Photos permission handling and UI panels.

This module provides tests for permission checking, error handling,
and the permission instruction UI panels.

SDS Reference: SDS-P01-007
SRS Reference: SRS-802 (User Guidance)
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from video_converter.extractors.photos_extractor import (
    PhotosAccessDeniedError,
    PhotosLibraryError,
    PhotosLibraryNotFoundError,
    get_permission_instructions,
)
from video_converter.handlers.photos_handler import PhotosSourceHandler
from video_converter.ui.panels import (
    display_photos_library_info,
    display_photos_permission_error,
    display_photos_permission_success,
)


class TestGetPermissionInstructions:
    """Tests for get_permission_instructions function."""

    def test_returns_string(self) -> None:
        """Test that function returns a string."""
        instructions = get_permission_instructions()

        assert isinstance(instructions, str)
        assert len(instructions) > 0

    def test_contains_system_settings(self) -> None:
        """Test that instructions mention System Settings."""
        instructions = get_permission_instructions()

        assert "System Settings" in instructions

    def test_contains_full_disk_access(self) -> None:
        """Test that instructions mention Full Disk Access."""
        instructions = get_permission_instructions()

        assert "Full Disk Access" in instructions

    def test_contains_terminal(self) -> None:
        """Test that instructions mention Terminal."""
        instructions = get_permission_instructions()

        assert "Terminal" in instructions

    def test_contains_quick_access_command(self) -> None:
        """Test that instructions contain the quick access command."""
        instructions = get_permission_instructions()

        assert "open" in instructions
        assert "preference.security" in instructions


class TestPhotosAccessDeniedError:
    """Tests for PhotosAccessDeniedError exception."""

    def test_default_message(self) -> None:
        """Test default error message contains key info."""
        error = PhotosAccessDeniedError()
        message = str(error)

        assert "access denied" in message.lower()
        assert "Full Disk Access" in message

    def test_custom_message(self) -> None:
        """Test custom error message is used."""
        error = PhotosAccessDeniedError("Custom permission error")

        assert str(error) == "Custom permission error"


class TestPhotosLibraryNotFoundError:
    """Tests for PhotosLibraryNotFoundError exception."""

    def test_with_path(self) -> None:
        """Test error message includes the attempted path."""
        path = Path("/custom/library.photoslibrary")
        error = PhotosLibraryNotFoundError(path)
        message = str(error)

        assert "/custom/library.photoslibrary" in message

    def test_without_path(self) -> None:
        """Test error message for default library."""
        error = PhotosLibraryNotFoundError()
        message = str(error)

        assert "Default" in message


class TestPhotosLibraryError:
    """Tests for base PhotosLibraryError exception."""

    def test_is_base_exception(self) -> None:
        """Test that it's the base for Photos errors."""
        access_error = PhotosAccessDeniedError()
        not_found_error = PhotosLibraryNotFoundError()

        assert isinstance(access_error, PhotosLibraryError)
        assert isinstance(not_found_error, PhotosLibraryError)


class TestPermissionCheckFlow:
    """Tests for permission check flow in PhotosSourceHandler."""

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    def test_permission_check_success_flow(
        self,
        mock_library_class: MagicMock,
    ) -> None:
        """Test successful permission check flow."""
        mock_lib = MagicMock()
        mock_lib.check_permissions.return_value = True
        mock_library_class.return_value = mock_lib

        handler = PhotosSourceHandler()

        assert handler.check_permissions() is True
        assert handler.get_permission_error() is None

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    def test_permission_check_denied_flow(
        self,
        mock_library_class: MagicMock,
    ) -> None:
        """Test permission denied flow."""
        mock_lib = MagicMock()
        mock_lib.check_permissions.return_value = False
        mock_library_class.return_value = mock_lib

        handler = PhotosSourceHandler()

        assert handler.check_permissions() is False
        error = handler.get_permission_error()
        assert error is not None
        assert "denied" in error.lower()

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    def test_permission_check_library_not_found_flow(
        self,
        mock_library_class: MagicMock,
    ) -> None:
        """Test library not found flow."""
        mock_library_class.side_effect = PhotosLibraryNotFoundError(
            Path("/custom/path.photoslibrary")
        )

        handler = PhotosSourceHandler()

        assert handler.check_permissions() is False
        error = handler.get_permission_error()
        assert error is not None
        assert "/custom/path.photoslibrary" in error

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    def test_permission_check_access_denied_exception_flow(
        self,
        mock_library_class: MagicMock,
    ) -> None:
        """Test access denied exception flow."""
        mock_library_class.side_effect = PhotosAccessDeniedError()

        handler = PhotosSourceHandler()

        assert handler.check_permissions() is False
        error = handler.get_permission_error()
        assert error is not None
        assert "Full Disk Access" in error

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    def test_permission_check_generic_library_error_flow(
        self,
        mock_library_class: MagicMock,
    ) -> None:
        """Test generic library error flow."""
        mock_library_class.side_effect = PhotosLibraryError("Unknown error")

        handler = PhotosSourceHandler()

        assert handler.check_permissions() is False
        error = handler.get_permission_error()
        assert error is not None
        assert "Unknown error" in error

    def test_get_permission_instructions_returns_content(self) -> None:
        """Test that handler's get_permission_instructions works."""
        handler = PhotosSourceHandler()
        instructions = handler.get_permission_instructions()

        assert len(instructions) > 0
        assert "System Settings" in instructions


class TestDisplayPhotosPermissionError:
    """Tests for display_photos_permission_error function."""

    def test_access_denied_displays_panel(self) -> None:
        """Test access denied error displays Rich panel."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display_photos_permission_error(console=console, error_type="access_denied")

        result = output.getvalue()
        assert "Photos Library Access Denied" in result
        assert "Full Disk Access" in result

    def test_access_denied_contains_instructions(self) -> None:
        """Test access denied panel contains step-by-step instructions."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display_photos_permission_error(console=console)

        result = output.getvalue()
        assert "System Settings" in result
        assert "Privacy" in result
        assert "Terminal" in result

    def test_access_denied_contains_quick_access(self) -> None:
        """Test access denied panel contains quick access command."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display_photos_permission_error(console=console)

        result = output.getvalue()
        assert "open" in result
        assert "preference.security" in result

    def test_not_found_displays_panel(self) -> None:
        """Test library not found displays Rich panel."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display_photos_permission_error(console=console, error_type="not_found")

        result = output.getvalue()
        assert "Photos Library Not Found" in result

    def test_not_found_with_path(self) -> None:
        """Test library not found panel shows attempted path."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display_photos_permission_error(
            console=console,
            error_type="not_found",
            library_path="/custom/path.photoslibrary",
        )

        result = output.getvalue()
        assert "/custom/path.photoslibrary" in result

    def test_not_found_contains_solutions(self) -> None:
        """Test library not found panel contains solutions."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display_photos_permission_error(console=console, error_type="not_found")

        result = output.getvalue()
        assert "Solutions" in result
        assert "Photos app" in result
        assert "--library-path" in result

    def test_uses_default_console(self) -> None:
        """Test function works with default console (no errors)."""
        # This should not raise any exceptions
        with patch("video_converter.ui.panels._console") as mock_console:
            display_photos_permission_error()
            mock_console.print.assert_called_once()


class TestDisplayPhotosPermissionSuccess:
    """Tests for display_photos_permission_success function."""

    def test_displays_success_message(self) -> None:
        """Test success message is displayed."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display_photos_permission_success(console=console)

        result = output.getvalue()
        assert "Photos library access granted" in result

    def test_uses_default_console(self) -> None:
        """Test function works with default console."""
        with patch("video_converter.ui.panels._console") as mock_console:
            display_photos_permission_success()
            mock_console.print.assert_called_once()


class TestDisplayPhotosLibraryInfo:
    """Tests for display_photos_library_info function."""

    def test_displays_library_path(self) -> None:
        """Test library path is displayed."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display_photos_library_info(
            console=console,
            library_path="/Users/test/Pictures/Photos Library.photoslibrary",
        )

        result = output.getvalue()
        assert "Library" in result

    def test_displays_video_count(self) -> None:
        """Test video count is displayed."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display_photos_library_info(
            console=console,
            video_count=100,
            h264_count=60,
        )

        result = output.getvalue()
        assert "Videos" in result
        assert "H.264" in result

    def test_displays_total_size(self) -> None:
        """Test total size is displayed."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display_photos_library_info(
            console=console,
            h264_count=60,
            total_size_gb=10.5,
        )

        result = output.getvalue()
        assert "10.5 GB" in result

    def test_displays_estimated_savings(self) -> None:
        """Test estimated savings is displayed."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display_photos_library_info(
            console=console,
            h264_count=60,
            total_size_gb=10.0,
        )

        result = output.getvalue()
        # Estimated savings should be ~50% of total size
        assert "Est. savings" in result
        assert "5.0 GB" in result

    def test_no_savings_when_no_h264(self) -> None:
        """Test no savings displayed when no H.264 videos."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)

        display_photos_library_info(
            console=console,
            h264_count=0,
            total_size_gb=0.0,
        )

        result = output.getvalue()
        # Should not show savings line
        assert "Est. savings" not in result

    def test_uses_default_console(self) -> None:
        """Test function works with default console."""
        with patch("video_converter.ui.panels._console") as mock_console:
            display_photos_library_info()
            mock_console.print.assert_called_once()


class TestPermissionErrorHandling:
    """Integration tests for permission error handling flow."""

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    def test_full_permission_denied_flow(
        self,
        mock_library_class: MagicMock,
    ) -> None:
        """Test complete flow from permission check to error display."""
        mock_library_class.side_effect = PhotosAccessDeniedError()

        handler = PhotosSourceHandler()

        # Check permissions
        has_permission = handler.check_permissions()
        assert has_permission is False

        # Get error message
        error = handler.get_permission_error()
        assert error is not None

        # Get instructions
        instructions = handler.get_permission_instructions()
        assert "System Settings" in instructions

        # Display error (should not raise)
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        display_photos_permission_error(console=console)

        result = output.getvalue()
        assert len(result) > 0

    @patch("video_converter.handlers.photos_handler.PhotosLibrary")
    def test_full_library_not_found_flow(
        self,
        mock_library_class: MagicMock,
    ) -> None:
        """Test complete flow from library not found to error display."""
        custom_path = Path("/custom/library.photoslibrary")
        mock_library_class.side_effect = PhotosLibraryNotFoundError(custom_path)

        handler = PhotosSourceHandler(library_path=custom_path)

        # Check permissions
        has_permission = handler.check_permissions()
        assert has_permission is False

        # Get error message
        error = handler.get_permission_error()
        assert str(custom_path) in error

        # Display error
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        display_photos_permission_error(
            console=console,
            error_type="not_found",
            library_path=str(custom_path),
        )

        result = output.getvalue()
        assert str(custom_path) in result
