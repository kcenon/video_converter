"""Recent conversions list widget for the Video Converter GUI.

This module provides a list widget for displaying recent conversion
history on the home view.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


@dataclass
class ConversionItem:
    """Data class for conversion list items."""

    file_name: str
    status: str  # "complete", "in_progress", "queued", "failed"
    progress: float  # 0-100 for in_progress
    original_size: int  # bytes
    converted_size: int | None  # bytes, None if not complete
    completed_at: datetime | None


class RecentConversionItem(QFrame):
    """Individual item in the recent conversions list."""

    clicked = Signal(str)

    def __init__(self, item: ConversionItem, parent: QWidget | None = None) -> None:
        """Initialize the conversion item.

        Args:
            item: Conversion item data.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._item = item
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setObjectName("recentItem")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        # Icon and name
        icon = "📹"
        name_label = QLabel(f"{icon} {self._item.file_name}")
        name_label.setObjectName("recentItemName")
        layout.addWidget(name_label)

        layout.addStretch()

        # Status
        status_text = self._get_status_text()
        status_label = QLabel(status_text)
        status_label.setObjectName("recentItemStatus")
        layout.addWidget(status_label)

        # Size info
        size_text = self._get_size_text()
        if size_text:
            size_label = QLabel(size_text)
            size_label.setObjectName("recentItemSize")
            layout.addWidget(size_label)

    def _get_status_text(self) -> str:
        """Get status display text.

        Returns:
            Status text with icon.
        """
        status_map = {
            "complete": "✅ Complete",
            "in_progress": f"⏳ {self._item.progress:.0f}%",
            "queued": "📋 Queued",
            "failed": "❌ Failed",
        }
        return status_map.get(self._item.status, self._item.status)

    def _get_size_text(self) -> str | None:
        """Get size display text.

        Returns:
            Size text or None.
        """
        if self._item.status == "complete" and self._item.converted_size:
            orig = self._format_size(self._item.original_size)
            conv = self._format_size(self._item.converted_size)
            return f"{orig} → {conv}"
        elif self._item.status == "queued":
            return self._format_size(self._item.original_size)
        return None

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format size in bytes to human-readable string.

        Args:
            size_bytes: Size in bytes.

        Returns:
            Formatted size string.
        """
        if size_bytes >= 1_000_000_000:
            return f"{size_bytes / 1_000_000_000:.1f}GB"
        elif size_bytes >= 1_000_000:
            return f"{size_bytes / 1_000_000:.0f}MB"
        else:
            return f"{size_bytes / 1_000:.0f}KB"

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press.

        Args:
            event: Mouse event.
        """
        self.clicked.emit(self._item.file_name)
        super().mousePressEvent(event)


class RecentConversionsList(QWidget):
    """List of recent conversions.

    Displays a list of recent conversion items with status,
    progress, and size information.

    Signals:
        item_clicked: Emitted when an item is clicked.
    """

    item_clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the list.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._items: list[RecentConversionItem] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)

        # Empty state
        self._empty_label = QLabel("No recent conversions")
        self._empty_label.setObjectName("emptyLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._empty_label)

        self._layout.addStretch()

    def add_item(self, item: ConversionItem) -> None:
        """Add a conversion item to the list.

        Args:
            item: Conversion item data.
        """
        # Hide empty label if this is the first item
        if not self._items:
            self._empty_label.hide()

        # Create item widget
        item_widget = RecentConversionItem(item)
        item_widget.clicked.connect(self.item_clicked.emit)

        # Insert at top (before stretch)
        self._layout.insertWidget(len(self._items), item_widget)
        self._items.append(item_widget)

    def clear(self) -> None:
        """Clear all items from the list."""
        for item in self._items:
            self._layout.removeWidget(item)
            item.deleteLater()

        self._items.clear()
        self._empty_label.show()

    def update_item(
        self,
        file_name: str,
        status: str | None = None,
        progress: float | None = None,
    ) -> None:
        """Update an existing item.

        Args:
            file_name: File name to update.
            status: New status.
            progress: New progress value.
        """
        # This would need to be implemented to update existing items
        # For now, items are immutable after creation
        pass

    def set_items(self, items: list[ConversionItem]) -> None:
        """Set all items in the list.

        Args:
            items: List of conversion items.
        """
        self.clear()
        for item in items:
            self.add_item(item)
