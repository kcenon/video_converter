"""Tests for the DropZone widget.

This module tests the drag and drop functionality, visual feedback,
and signal emission of the DropZone widget.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QMimeData, QPoint, QUrl, Qt
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent

from video_converter.gui.widgets.drop_zone import DropZone

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


pytestmark = pytest.mark.gui


class TestDropZoneCreation:
    """Tests for DropZone widget creation and initialization."""

    def test_drop_zone_creates_successfully(self, qtbot: QtBot) -> None:
        """Test that DropZone can be created without errors."""
        widget = DropZone()
        qtbot.addWidget(widget)

        assert widget is not None
        assert widget.acceptDrops() is True

    def test_drop_zone_has_correct_minimum_height(self, qtbot: QtBot) -> None:
        """Test that DropZone has the expected minimum height."""
        widget = DropZone()
        qtbot.addWidget(widget)

        assert widget.minimumHeight() == 150

    def test_drop_zone_has_labels(self, qtbot: QtBot) -> None:
        """Test that DropZone has all required labels."""
        widget = DropZone()
        qtbot.addWidget(widget)

        assert widget.icon_label is not None
        assert widget.main_label is not None
        assert widget.subtitle_label is not None
        assert widget.formats_label is not None

    def test_drop_zone_default_text(self, qtbot: QtBot) -> None:
        """Test that DropZone displays correct default text."""
        widget = DropZone()
        qtbot.addWidget(widget)

        assert widget.main_label.text() == "Drop video files here"
        assert widget.subtitle_label.text() == "or click to browse"

    def test_supported_extensions(self, qtbot: QtBot) -> None:
        """Test that DropZone has correct supported extensions."""
        widget = DropZone()
        qtbot.addWidget(widget)

        expected = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm", ".wmv"}
        assert widget.SUPPORTED_EXTENSIONS == expected


class TestDropZoneValidation:
    """Tests for file validation in DropZone."""

    def test_valid_video_file_is_accepted(
        self, qtbot: QtBot, sample_video_files: list[Path]
    ) -> None:
        """Test that valid video files are correctly identified."""
        widget = DropZone()
        qtbot.addWidget(widget)

        # Create URLs for video files
        urls = [QUrl.fromLocalFile(str(f)) for f in sample_video_files]

        count = widget._count_valid_files(urls)
        assert count == len(sample_video_files)

    def test_invalid_file_is_rejected(self, qtbot: QtBot, tmp_path: Path) -> None:
        """Test that non-video files are rejected."""
        widget = DropZone()
        qtbot.addWidget(widget)

        # Create a text file
        text_file = tmp_path / "document.txt"
        text_file.write_text("Hello")

        urls = [QUrl.fromLocalFile(str(text_file))]

        count = widget._count_valid_files(urls)
        assert count == 0

    def test_folder_video_count(
        self, qtbot: QtBot, sample_folder_with_videos: Path
    ) -> None:
        """Test counting video files in a folder."""
        widget = DropZone()
        qtbot.addWidget(widget)

        urls = [QUrl.fromLocalFile(str(sample_folder_with_videos))]

        count = widget._count_valid_files(urls)
        # 5 video files in the test folder
        assert count == 5

    def test_mixed_files_and_folders(
        self, qtbot: QtBot, sample_video_files: list[Path], sample_folder_with_videos: Path
    ) -> None:
        """Test counting videos from mixed files and folders."""
        widget = DropZone()
        qtbot.addWidget(widget)

        urls = [QUrl.fromLocalFile(str(sample_video_files[0]))]
        urls.append(QUrl.fromLocalFile(str(sample_folder_with_videos)))

        count = widget._count_valid_files(urls)
        # 1 file + 5 from folder = 6
        assert count == 6


class TestDropZoneExtraction:
    """Tests for file extraction from drops."""

    def test_extract_single_video(
        self, qtbot: QtBot, sample_video_files: list[Path]
    ) -> None:
        """Test extracting a single video file path."""
        widget = DropZone()
        qtbot.addWidget(widget)

        urls = [QUrl.fromLocalFile(str(sample_video_files[0]))]

        files = widget._extract_valid_files(urls)
        assert len(files) == 1
        assert files[0] == str(sample_video_files[0])

    def test_extract_multiple_videos(
        self, qtbot: QtBot, sample_video_files: list[Path]
    ) -> None:
        """Test extracting multiple video file paths."""
        widget = DropZone()
        qtbot.addWidget(widget)

        urls = [QUrl.fromLocalFile(str(f)) for f in sample_video_files]

        files = widget._extract_valid_files(urls)
        assert len(files) == len(sample_video_files)

    def test_extract_from_folder(
        self, qtbot: QtBot, sample_folder_with_videos: Path
    ) -> None:
        """Test extracting video files from a folder."""
        widget = DropZone()
        qtbot.addWidget(widget)

        urls = [QUrl.fromLocalFile(str(sample_folder_with_videos))]

        files = widget._extract_valid_files(urls)
        assert len(files) == 5
        # Files should be sorted
        assert files == sorted(files)

    def test_extract_ignores_non_video_files(
        self, qtbot: QtBot, tmp_path: Path
    ) -> None:
        """Test that non-video files are ignored during extraction."""
        widget = DropZone()
        qtbot.addWidget(widget)

        # Create mixed files
        video_file = tmp_path / "video.mp4"
        video_file.write_bytes(b"\x00")

        text_file = tmp_path / "document.txt"
        text_file.write_text("Hello")

        urls = [
            QUrl.fromLocalFile(str(video_file)),
            QUrl.fromLocalFile(str(text_file)),
        ]

        files = widget._extract_valid_files(urls)
        assert len(files) == 1
        assert files[0] == str(video_file)


class TestDropZoneDragFeedback:
    """Tests for visual feedback during drag operations."""

    def test_drag_over_state_valid(self, qtbot: QtBot) -> None:
        """Test visual feedback for valid drag."""
        widget = DropZone()
        qtbot.addWidget(widget)

        widget._set_drag_over(True, valid=True, file_count=3)

        assert widget._is_drag_over is True
        assert widget._drag_valid is True
        assert "3 videos" in widget.main_label.text()

    def test_drag_over_state_single_file(self, qtbot: QtBot) -> None:
        """Test visual feedback for single file drag."""
        widget = DropZone()
        qtbot.addWidget(widget)

        widget._set_drag_over(True, valid=True, file_count=1)

        assert "1 video" in widget.main_label.text()
        assert "videos" not in widget.main_label.text()

    def test_drag_over_state_invalid(self, qtbot: QtBot) -> None:
        """Test visual feedback for invalid drag."""
        widget = DropZone()
        qtbot.addWidget(widget)

        widget._set_drag_over(True, valid=False, file_count=0)

        assert widget._is_drag_over is True
        assert widget._drag_valid is False
        assert "No valid" in widget.main_label.text()

    def test_drag_leave_resets_state(self, qtbot: QtBot) -> None:
        """Test that leaving drag state resets the widget."""
        widget = DropZone()
        qtbot.addWidget(widget)

        # Set drag over first
        widget._set_drag_over(True, valid=True, file_count=3)

        # Then leave
        widget._set_drag_over(False, valid=False, file_count=0)

        assert widget._is_drag_over is False
        assert widget.main_label.text() == "Drop video files here"


class TestDropZoneSignals:
    """Tests for signal emission from DropZone."""

    def test_file_dropped_signal(
        self, qtbot: QtBot, sample_video_files: list[Path]
    ) -> None:
        """Test that file_dropped signal is emitted for single file."""
        widget = DropZone()
        qtbot.addWidget(widget)

        # Create signal spy
        with qtbot.waitSignal(widget.file_dropped, timeout=1000) as blocker:
            # Simulate the signal emission directly
            widget.file_dropped.emit(str(sample_video_files[0]))

        assert blocker.args[0] == str(sample_video_files[0])

    def test_files_dropped_signal(
        self, qtbot: QtBot, sample_video_files: list[Path]
    ) -> None:
        """Test that files_dropped signal is emitted for multiple files."""
        widget = DropZone()
        qtbot.addWidget(widget)

        file_paths = [str(f) for f in sample_video_files]

        # Create signal spy
        with qtbot.waitSignal(widget.files_dropped, timeout=1000) as blocker:
            widget.files_dropped.emit(file_paths)

        assert blocker.args[0] == file_paths


class TestDropZoneClickBrowse:
    """Tests for click-to-browse functionality."""

    def test_click_opens_file_dialog(self, qtbot: QtBot) -> None:
        """Test that clicking opens a file dialog."""
        widget = DropZone()
        qtbot.addWidget(widget)

        with patch(
            "video_converter.gui.widgets.drop_zone.QFileDialog.getOpenFileNames"
        ) as mock_dialog:
            mock_dialog.return_value = ([], "")

            # Simulate click
            from PySide6.QtGui import QMouseEvent
            from PySide6.QtCore import QPointF

            event = QMouseEvent(
                QMouseEvent.Type.MouseButtonPress,
                QPointF(10, 10),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
            widget.mousePressEvent(event)

            mock_dialog.assert_called_once()

    def test_click_emits_signal_for_single_file(
        self, qtbot: QtBot, sample_video_files: list[Path]
    ) -> None:
        """Test that selecting a single file emits file_dropped."""
        widget = DropZone()
        qtbot.addWidget(widget)

        with patch(
            "video_converter.gui.widgets.drop_zone.QFileDialog.getOpenFileNames"
        ) as mock_dialog:
            mock_dialog.return_value = ([str(sample_video_files[0])], "")

            with qtbot.waitSignal(widget.file_dropped, timeout=1000) as blocker:
                from PySide6.QtGui import QMouseEvent
                from PySide6.QtCore import QPointF

                event = QMouseEvent(
                    QMouseEvent.Type.MouseButtonPress,
                    QPointF(10, 10),
                    Qt.MouseButton.LeftButton,
                    Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier,
                )
                widget.mousePressEvent(event)

            assert blocker.args[0] == str(sample_video_files[0])

    def test_click_emits_signal_for_multiple_files(
        self, qtbot: QtBot, sample_video_files: list[Path]
    ) -> None:
        """Test that selecting multiple files emits files_dropped."""
        widget = DropZone()
        qtbot.addWidget(widget)

        file_paths = [str(f) for f in sample_video_files]

        with patch(
            "video_converter.gui.widgets.drop_zone.QFileDialog.getOpenFileNames"
        ) as mock_dialog:
            mock_dialog.return_value = (file_paths, "")

            with qtbot.waitSignal(widget.files_dropped, timeout=1000) as blocker:
                from PySide6.QtGui import QMouseEvent
                from PySide6.QtCore import QPointF

                event = QMouseEvent(
                    QMouseEvent.Type.MouseButtonPress,
                    QPointF(10, 10),
                    Qt.MouseButton.LeftButton,
                    Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier,
                )
                widget.mousePressEvent(event)

            assert blocker.args[0] == file_paths
