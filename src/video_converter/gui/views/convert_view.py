"""Conversion view for the Video Converter GUI.

This module provides the conversion view with file selection,
quality settings, and progress display.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    pass


class ConvertView(QWidget):
    """Conversion view.

    Provides interface for:
    - Input file selection
    - Output settings (format, quality, encoder)
    - Conversion progress display
    - Start/pause/cancel controls

    Signals:
        conversion_started: Emitted when conversion starts.
        conversion_cancelled: Emitted when conversion is cancelled.
    """

    conversion_started = Signal(str, dict)  # file_path, settings
    conversion_cancelled = Signal()

    # Quality presets
    QUALITY_PRESETS = {
        "High": 23,
        "Medium": 28,
        "Low": 32,
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the convert view.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._input_file: str | None = None
        self._is_converting = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Input section
        self._setup_input_section(layout)

        # Output settings section
        self._setup_output_section(layout)

        # Encoding settings section
        self._setup_encoding_section(layout)

        # Progress section
        self._setup_progress_section(layout)

        # Action buttons
        self._setup_action_buttons(layout)

        layout.addStretch()

    def _setup_input_section(self, parent_layout: QVBoxLayout) -> None:
        """Set up input file section.

        Args:
            parent_layout: Parent layout.
        """
        group = QGroupBox("Input")
        group_layout = QVBoxLayout(group)

        # File path row
        file_layout = QHBoxLayout()

        self.input_path_edit = QLineEdit()
        self.input_path_edit.setPlaceholderText("Select a video file...")
        self.input_path_edit.setReadOnly(True)
        file_layout.addWidget(self.input_path_edit)

        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._on_browse_input)
        file_layout.addWidget(browse_button)

        group_layout.addLayout(file_layout)

        # File info
        self.file_info_label = QLabel("No file selected")
        self.file_info_label.setObjectName("infoLabel")
        group_layout.addWidget(self.file_info_label)

        parent_layout.addWidget(group)

    def _setup_output_section(self, parent_layout: QVBoxLayout) -> None:
        """Set up output settings section.

        Args:
            parent_layout: Parent layout.
        """
        group = QGroupBox("Output")
        group_layout = QFormLayout(group)

        # Output directory
        output_layout = QHBoxLayout()
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("Same as input")
        output_layout.addWidget(self.output_path_edit)

        browse_output_button = QPushButton("Browse...")
        browse_output_button.clicked.connect(self._on_browse_output)
        output_layout.addWidget(browse_output_button)

        group_layout.addRow("Output Directory:", output_layout)

        # Output format
        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP4 (H.265/HEVC)", "MOV (H.265/HEVC)"])
        group_layout.addRow("Format:", self.format_combo)

        parent_layout.addWidget(group)

    def _setup_encoding_section(self, parent_layout: QVBoxLayout) -> None:
        """Set up encoding settings section.

        Args:
            parent_layout: Parent layout.
        """
        group = QGroupBox("Encoding Settings")
        group_layout = QFormLayout(group)

        # Encoder selection
        self.encoder_combo = QComboBox()
        self.encoder_combo.addItems(
            [
                "VideoToolbox (Hardware)",
                "libx265 (Software)",
            ]
        )
        group_layout.addRow("Encoder:", self.encoder_combo)

        # Quality preset
        preset_layout = QHBoxLayout()
        self.quality_preset_combo = QComboBox()
        self.quality_preset_combo.addItems(list(self.QUALITY_PRESETS.keys()))
        self.quality_preset_combo.setCurrentText("Medium")
        self.quality_preset_combo.currentTextChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self.quality_preset_combo)

        # Custom quality slider
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(18, 35)
        self.quality_slider.setValue(28)
        self.quality_slider.valueChanged.connect(self._on_quality_changed)
        preset_layout.addWidget(self.quality_slider)

        self.quality_value_label = QLabel("CRF: 28")
        self.quality_value_label.setMinimumWidth(60)
        preset_layout.addWidget(self.quality_value_label)

        group_layout.addRow("Quality:", preset_layout)

        # Audio settings
        self.audio_combo = QComboBox()
        self.audio_combo.addItems(["Copy (No re-encode)", "AAC 128kbps", "AAC 192kbps"])
        group_layout.addRow("Audio:", self.audio_combo)

        # Thread count
        self.thread_spinbox = QSpinBox()
        self.thread_spinbox.setRange(1, 16)
        self.thread_spinbox.setValue(4)
        self.thread_spinbox.setSpecialValueText("Auto")
        group_layout.addRow("Threads:", self.thread_spinbox)

        parent_layout.addWidget(group)

    def _setup_progress_section(self, parent_layout: QVBoxLayout) -> None:
        """Set up progress display section.

        Args:
            parent_layout: Parent layout.
        """
        self.progress_frame = QFrame()
        self.progress_frame.setObjectName("progressFrame")
        self.progress_frame.setVisible(False)

        progress_layout = QVBoxLayout(self.progress_frame)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        progress_layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        # Progress details
        details_layout = QHBoxLayout()

        self.progress_label = QLabel("0%")
        details_layout.addWidget(self.progress_label)

        details_layout.addStretch()

        self.eta_label = QLabel("ETA: --:--")
        details_layout.addWidget(self.eta_label)

        details_layout.addStretch()

        self.speed_label = QLabel("Speed: --")
        details_layout.addWidget(self.speed_label)

        progress_layout.addLayout(details_layout)

        parent_layout.addWidget(self.progress_frame)

    def _setup_action_buttons(self, parent_layout: QVBoxLayout) -> None:
        """Set up action buttons.

        Args:
            parent_layout: Parent layout.
        """
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_button)

        self.convert_button = QPushButton("Start Conversion")
        self.convert_button.setObjectName("primaryButton")
        self.convert_button.setEnabled(False)
        self.convert_button.clicked.connect(self._on_convert)
        button_layout.addWidget(self.convert_button)

        parent_layout.addLayout(button_layout)

    def set_input_file(self, file_path: str) -> None:
        """Set the input file.

        Args:
            file_path: Path to the input video file.
        """
        self._input_file = file_path
        self.input_path_edit.setText(file_path)
        self.convert_button.setEnabled(True)

        # Update file info
        path = Path(file_path)
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            self.file_info_label.setText(f"File: {path.name} | Size: {size_mb:.1f} MB")
        else:
            self.file_info_label.setText("File not found")
            self.convert_button.setEnabled(False)

    def _on_browse_input(self) -> None:
        """Handle input file browse."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            "",
            "Video Files (*.mp4 *.mov *.avi *.mkv *.m4v);;All Files (*)",
        )
        if file_path:
            self.set_input_file(file_path)

    def _on_browse_output(self) -> None:
        """Handle output directory browse."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            "",
        )
        if dir_path:
            self.output_path_edit.setText(dir_path)

    @Slot(str)
    def _on_preset_changed(self, preset: str) -> None:
        """Handle quality preset change.

        Args:
            preset: Selected preset name.
        """
        if preset in self.QUALITY_PRESETS:
            self.quality_slider.setValue(self.QUALITY_PRESETS[preset])

    @Slot(int)
    def _on_quality_changed(self, value: int) -> None:
        """Handle quality slider change.

        Args:
            value: New CRF value.
        """
        self.quality_value_label.setText(f"CRF: {value}")

    def _on_convert(self) -> None:
        """Start conversion."""
        if not self._input_file:
            return

        self._is_converting = True
        self.progress_frame.setVisible(True)
        self.convert_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status_label.setText("Converting...")

        settings = {
            "encoder": self.encoder_combo.currentText(),
            "quality": self.quality_slider.value(),
            "audio": self.audio_combo.currentText(),
            "format": self.format_combo.currentText(),
            "threads": self.thread_spinbox.value(),
            "output_dir": self.output_path_edit.text() or None,
        }

        self.conversion_started.emit(self._input_file, settings)

    def _on_cancel(self) -> None:
        """Cancel conversion."""
        self._is_converting = False
        self.cancel_button.setEnabled(False)
        self.convert_button.setEnabled(True)
        self.status_label.setText("Cancelled")
        self.conversion_cancelled.emit()

    def update_progress(
        self,
        progress: float,
        eta_seconds: int | None = None,
        speed: str | None = None,
    ) -> None:
        """Update conversion progress.

        Args:
            progress: Progress percentage (0-100).
            eta_seconds: Estimated time remaining in seconds.
            speed: Current encoding speed string.
        """
        self.progress_bar.setValue(int(progress))
        self.progress_label.setText(f"{progress:.1f}%")

        if eta_seconds is not None:
            minutes = eta_seconds // 60
            seconds = eta_seconds % 60
            self.eta_label.setText(f"ETA: {minutes}:{seconds:02d}")
        else:
            self.eta_label.setText("ETA: --:--")

        if speed:
            self.speed_label.setText(f"Speed: {speed}")
        else:
            self.speed_label.setText("Speed: --")

    def conversion_complete(self, success: bool, message: str = "") -> None:
        """Handle conversion completion.

        Args:
            success: Whether conversion was successful.
            message: Result message.
        """
        self._is_converting = False
        self.cancel_button.setEnabled(False)
        self.convert_button.setEnabled(True)

        if success:
            self.status_label.setText("Conversion Complete!")
            self.progress_bar.setValue(100)
        else:
            self.status_label.setText(f"Conversion Failed: {message}")
