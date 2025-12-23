"""Tests for the recent conversions list widget.

This module tests the RecentConversionsList and RecentConversionItem widgets.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import Qt

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


class TestConversionItem:
    """Tests for ConversionItem dataclass."""

    def test_conversion_item_creation(self) -> None:
        """Test creating a ConversionItem instance."""
        from video_converter.gui.widgets.recent_list import ConversionItem

        item = ConversionItem(
            file_name="test.mp4",
            status="complete",
            progress=100.0,
            original_size=1024 * 1024 * 100,
            converted_size=1024 * 1024 * 50,
            completed_at=datetime.now(),
        )
        assert item.file_name == "test.mp4"
        assert item.status == "complete"
        assert item.progress == 100.0

    def test_conversion_item_in_progress(self) -> None:
        """Test ConversionItem for in-progress conversion."""
        from video_converter.gui.widgets.recent_list import ConversionItem

        item = ConversionItem(
            file_name="converting.mp4",
            status="in_progress",
            progress=45.5,
            original_size=1024 * 1024 * 200,
            converted_size=None,
            completed_at=None,
        )
        assert item.status == "in_progress"
        assert item.progress == 45.5
        assert item.converted_size is None

    def test_conversion_item_queued(self) -> None:
        """Test ConversionItem for queued conversion."""
        from video_converter.gui.widgets.recent_list import ConversionItem

        item = ConversionItem(
            file_name="queued.mp4",
            status="queued",
            progress=0.0,
            original_size=1024 * 1024 * 150,
            converted_size=None,
            completed_at=None,
        )
        assert item.status == "queued"
        assert item.progress == 0.0


class TestRecentConversionItem:
    """Tests for RecentConversionItem widget."""

    def test_item_creation(self, qtbot: QtBot) -> None:
        """Test creating a RecentConversionItem widget."""
        from video_converter.gui.widgets.recent_list import (
            ConversionItem,
            RecentConversionItem,
        )

        item_data = ConversionItem(
            file_name="test.mp4",
            status="complete",
            progress=100.0,
            original_size=1024 * 1024 * 100,
            converted_size=1024 * 1024 * 50,
            completed_at=datetime.now(),
        )
        widget = RecentConversionItem(item_data)
        qtbot.addWidget(widget)
        assert widget is not None

    def test_item_has_cursor(self, qtbot: QtBot) -> None:
        """Test that item has pointing hand cursor."""
        from video_converter.gui.widgets.recent_list import (
            ConversionItem,
            RecentConversionItem,
        )

        item_data = ConversionItem(
            file_name="test.mp4",
            status="complete",
            progress=100.0,
            original_size=1024 * 1024,
            converted_size=512 * 1024,
            completed_at=datetime.now(),
        )
        widget = RecentConversionItem(item_data)
        qtbot.addWidget(widget)
        assert widget.cursor().shape() == Qt.CursorShape.PointingHandCursor

    def test_item_status_complete(self, qtbot: QtBot) -> None:
        """Test status text for complete item."""
        from video_converter.gui.widgets.recent_list import (
            ConversionItem,
            RecentConversionItem,
        )

        item_data = ConversionItem(
            file_name="test.mp4",
            status="complete",
            progress=100.0,
            original_size=1024 * 1024,
            converted_size=512 * 1024,
            completed_at=datetime.now(),
        )
        widget = RecentConversionItem(item_data)
        qtbot.addWidget(widget)

        status_text = widget._get_status_text()
        assert "Complete" in status_text

    def test_item_status_in_progress(self, qtbot: QtBot) -> None:
        """Test status text for in-progress item."""
        from video_converter.gui.widgets.recent_list import (
            ConversionItem,
            RecentConversionItem,
        )

        item_data = ConversionItem(
            file_name="test.mp4",
            status="in_progress",
            progress=45.0,
            original_size=1024 * 1024,
            converted_size=None,
            completed_at=None,
        )
        widget = RecentConversionItem(item_data)
        qtbot.addWidget(widget)

        status_text = widget._get_status_text()
        assert "45%" in status_text

    def test_item_status_queued(self, qtbot: QtBot) -> None:
        """Test status text for queued item."""
        from video_converter.gui.widgets.recent_list import (
            ConversionItem,
            RecentConversionItem,
        )

        item_data = ConversionItem(
            file_name="test.mp4",
            status="queued",
            progress=0.0,
            original_size=1024 * 1024,
            converted_size=None,
            completed_at=None,
        )
        widget = RecentConversionItem(item_data)
        qtbot.addWidget(widget)

        status_text = widget._get_status_text()
        assert "Queued" in status_text

    def test_item_status_failed(self, qtbot: QtBot) -> None:
        """Test status text for failed item."""
        from video_converter.gui.widgets.recent_list import (
            ConversionItem,
            RecentConversionItem,
        )

        item_data = ConversionItem(
            file_name="test.mp4",
            status="failed",
            progress=0.0,
            original_size=1024 * 1024,
            converted_size=None,
            completed_at=None,
        )
        widget = RecentConversionItem(item_data)
        qtbot.addWidget(widget)

        status_text = widget._get_status_text()
        assert "Failed" in status_text

    def test_item_size_text_complete(self, qtbot: QtBot) -> None:
        """Test size text for complete item."""
        from video_converter.gui.widgets.recent_list import (
            ConversionItem,
            RecentConversionItem,
        )

        item_data = ConversionItem(
            file_name="test.mp4",
            status="complete",
            progress=100.0,
            original_size=1024 * 1024 * 100,
            converted_size=1024 * 1024 * 50,
            completed_at=datetime.now(),
        )
        widget = RecentConversionItem(item_data)
        qtbot.addWidget(widget)

        size_text = widget._get_size_text()
        assert size_text is not None
        assert "→" in size_text

    def test_item_size_text_queued(self, qtbot: QtBot) -> None:
        """Test size text for queued item."""
        from video_converter.gui.widgets.recent_list import (
            ConversionItem,
            RecentConversionItem,
        )

        item_data = ConversionItem(
            file_name="test.mp4",
            status="queued",
            progress=0.0,
            original_size=1024 * 1024 * 100,
            converted_size=None,
            completed_at=None,
        )
        widget = RecentConversionItem(item_data)
        qtbot.addWidget(widget)

        size_text = widget._get_size_text()
        assert size_text is not None
        assert "MB" in size_text

    def test_item_size_text_in_progress(self, qtbot: QtBot) -> None:
        """Test size text for in-progress item."""
        from video_converter.gui.widgets.recent_list import (
            ConversionItem,
            RecentConversionItem,
        )

        item_data = ConversionItem(
            file_name="test.mp4",
            status="in_progress",
            progress=50.0,
            original_size=1024 * 1024 * 100,
            converted_size=None,
            completed_at=None,
        )
        widget = RecentConversionItem(item_data)
        qtbot.addWidget(widget)

        size_text = widget._get_size_text()
        assert size_text is None

    def test_item_format_size_gb(self, qtbot: QtBot) -> None:
        """Test formatting size in GB."""
        from video_converter.gui.widgets.recent_list import RecentConversionItem

        size_str = RecentConversionItem._format_size(1_500_000_000)
        assert "GB" in size_str

    def test_item_format_size_mb(self, qtbot: QtBot) -> None:
        """Test formatting size in MB."""
        from video_converter.gui.widgets.recent_list import RecentConversionItem

        size_str = RecentConversionItem._format_size(50_000_000)
        assert "MB" in size_str

    def test_item_format_size_kb(self, qtbot: QtBot) -> None:
        """Test formatting size in KB."""
        from video_converter.gui.widgets.recent_list import RecentConversionItem

        size_str = RecentConversionItem._format_size(50_000)
        assert "KB" in size_str

    def test_item_click_emits_signal(self, qtbot: QtBot) -> None:
        """Test that clicking item emits signal."""
        from video_converter.gui.widgets.recent_list import (
            ConversionItem,
            RecentConversionItem,
        )

        item_data = ConversionItem(
            file_name="clicked.mp4",
            status="complete",
            progress=100.0,
            original_size=1024 * 1024,
            converted_size=512 * 1024,
            completed_at=datetime.now(),
        )
        widget = RecentConversionItem(item_data)
        qtbot.addWidget(widget)

        with qtbot.waitSignal(widget.clicked, timeout=1000):
            qtbot.mouseClick(widget, Qt.MouseButton.LeftButton)


class TestRecentConversionsList:
    """Tests for RecentConversionsList widget."""

    def test_list_creation(self, qtbot: QtBot) -> None:
        """Test creating a RecentConversionsList widget."""
        from video_converter.gui.widgets.recent_list import RecentConversionsList

        widget = RecentConversionsList()
        qtbot.addWidget(widget)
        assert widget is not None

    def test_list_initially_empty(self, qtbot: QtBot) -> None:
        """Test that list is initially empty."""
        from video_converter.gui.widgets.recent_list import RecentConversionsList

        widget = RecentConversionsList()
        qtbot.addWidget(widget)
        assert len(widget._items) == 0
        # Empty label is not hidden (isHidden returns False means it's visible when parent is visible)
        assert not widget._empty_label.isHidden()

    def test_list_add_item(self, qtbot: QtBot) -> None:
        """Test adding an item to the list."""
        from video_converter.gui.widgets.recent_list import (
            ConversionItem,
            RecentConversionsList,
        )

        widget = RecentConversionsList()
        qtbot.addWidget(widget)

        item = ConversionItem(
            file_name="test.mp4",
            status="complete",
            progress=100.0,
            original_size=1024 * 1024,
            converted_size=512 * 1024,
            completed_at=datetime.now(),
        )
        widget.add_item(item)

        assert len(widget._items) == 1
        # Empty label should be hidden after adding item
        assert widget._empty_label.isHidden()

    def test_list_add_multiple_items(self, qtbot: QtBot) -> None:
        """Test adding multiple items to the list."""
        from video_converter.gui.widgets.recent_list import (
            ConversionItem,
            RecentConversionsList,
        )

        widget = RecentConversionsList()
        qtbot.addWidget(widget)

        for i in range(3):
            item = ConversionItem(
                file_name=f"test{i}.mp4",
                status="complete",
                progress=100.0,
                original_size=1024 * 1024,
                converted_size=512 * 1024,
                completed_at=datetime.now(),
            )
            widget.add_item(item)

        assert len(widget._items) == 3

    def test_list_clear(self, qtbot: QtBot) -> None:
        """Test clearing the list."""
        from video_converter.gui.widgets.recent_list import (
            ConversionItem,
            RecentConversionsList,
        )

        widget = RecentConversionsList()
        qtbot.addWidget(widget)

        item = ConversionItem(
            file_name="test.mp4",
            status="complete",
            progress=100.0,
            original_size=1024 * 1024,
            converted_size=512 * 1024,
            completed_at=datetime.now(),
        )
        widget.add_item(item)
        widget.clear()

        assert len(widget._items) == 0
        # Empty label should be shown after clearing
        assert not widget._empty_label.isHidden()

    def test_list_set_items(self, qtbot: QtBot) -> None:
        """Test setting all items at once."""
        from video_converter.gui.widgets.recent_list import (
            ConversionItem,
            RecentConversionsList,
        )

        widget = RecentConversionsList()
        qtbot.addWidget(widget)

        items = [
            ConversionItem(
                file_name=f"test{i}.mp4",
                status="complete",
                progress=100.0,
                original_size=1024 * 1024,
                converted_size=512 * 1024,
                completed_at=datetime.now(),
            )
            for i in range(5)
        ]
        widget.set_items(items)

        assert len(widget._items) == 5

    def test_list_item_clicked_signal(self, qtbot: QtBot) -> None:
        """Test that list emits item_clicked signal."""
        from video_converter.gui.widgets.recent_list import (
            ConversionItem,
            RecentConversionsList,
        )

        widget = RecentConversionsList()
        qtbot.addWidget(widget)

        item = ConversionItem(
            file_name="signal_test.mp4",
            status="complete",
            progress=100.0,
            original_size=1024 * 1024,
            converted_size=512 * 1024,
            completed_at=datetime.now(),
        )
        widget.add_item(item)

        with qtbot.waitSignal(widget.item_clicked, timeout=1000):
            qtbot.mouseClick(widget._items[0], Qt.MouseButton.LeftButton)

    def test_list_update_item_exists(self, qtbot: QtBot) -> None:
        """Test that update_item method exists."""
        from video_converter.gui.widgets.recent_list import (
            ConversionItem,
            RecentConversionsList,
        )

        widget = RecentConversionsList()
        qtbot.addWidget(widget)

        # Just verify the method exists and can be called
        widget.update_item("test.mp4", status="complete", progress=100.0)
