"""Settings view for the Video Converter GUI.

This module provides the settings/preferences view for configuring
encoding, paths, automation, and notification settings.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class SettingsView(QWidget):
    """Settings/Preferences view.

    Provides configuration for:
    - Encoding settings (encoder, quality, presets)
    - Path settings (output directory, temp directory)
    - Automation settings (watch folders, scheduling)
    - Notification settings (desktop, sound)

    Signals:
        settings_changed: Emitted when settings are modified.
        settings_saved: Emitted when settings are saved.
    """

    settings_changed = Signal(dict)
    settings_saved = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the settings view.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Scrollable content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(scroll_area.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(20)

        # Title
        title = QLabel("Settings")
        title.setObjectName("viewTitle")
        content_layout.addWidget(title)

        # Encoding settings
        self._setup_encoding_settings(content_layout)

        # Path settings
        self._setup_path_settings(content_layout)

        # Automation settings
        self._setup_automation_settings(content_layout)

        # Notification settings
        self._setup_notification_settings(content_layout)

        content_layout.addStretch()

        scroll_area.setWidget(content)
        layout.addWidget(scroll_area)

        # Action buttons
        self._setup_buttons(layout)

    def _setup_encoding_settings(self, parent_layout: QVBoxLayout) -> None:
        """Set up encoding settings section.

        Args:
            parent_layout: Parent layout.
        """
        group = QGroupBox("Encoding")
        form = QFormLayout(group)

        # Default encoder
        self.encoder_combo = QComboBox()
        self.encoder_combo.addItems([
            "VideoToolbox (Hardware)",
            "libx265 (Software)",
            "Auto (Prefer Hardware)",
        ])
        self.encoder_combo.setCurrentIndex(2)  # Auto
        form.addRow("Default Encoder:", self.encoder_combo)

        # Default quality
        quality_layout = QHBoxLayout()

        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(18, 35)
        self.quality_slider.setValue(28)
        self.quality_slider.valueChanged.connect(self._on_quality_changed)
        quality_layout.addWidget(self.quality_slider)

        self.quality_label = QLabel("CRF: 28")
        self.quality_label.setMinimumWidth(60)
        quality_layout.addWidget(self.quality_label)

        form.addRow("Default Quality:", quality_layout)

        # Preset
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
        ])
        self.preset_combo.setCurrentText("medium")
        form.addRow("Encoding Preset:", self.preset_combo)

        # Audio settings
        self.audio_combo = QComboBox()
        self.audio_combo.addItems([
            "Copy (No re-encode)",
            "AAC 128kbps",
            "AAC 192kbps",
            "AAC 256kbps",
        ])
        form.addRow("Audio Handling:", self.audio_combo)

        # Concurrent jobs
        self.concurrent_spinbox = QSpinBox()
        self.concurrent_spinbox.setRange(1, 8)
        self.concurrent_spinbox.setValue(2)
        form.addRow("Concurrent Jobs:", self.concurrent_spinbox)

        parent_layout.addWidget(group)

    def _setup_path_settings(self, parent_layout: QVBoxLayout) -> None:
        """Set up path settings section.

        Args:
            parent_layout: Parent layout.
        """
        group = QGroupBox("Paths")
        form = QFormLayout(group)

        # Output directory
        output_layout = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Same as input file")
        output_layout.addWidget(self.output_dir_edit)

        output_browse = QPushButton("Browse...")
        output_browse.clicked.connect(self._on_browse_output)
        output_layout.addWidget(output_browse)

        form.addRow("Output Directory:", output_layout)

        # Temp directory
        temp_layout = QHBoxLayout()
        self.temp_dir_edit = QLineEdit()
        self.temp_dir_edit.setPlaceholderText("System default")
        temp_layout.addWidget(self.temp_dir_edit)

        temp_browse = QPushButton("Browse...")
        temp_browse.clicked.connect(self._on_browse_temp)
        temp_layout.addWidget(temp_browse)

        form.addRow("Temp Directory:", temp_layout)

        # Naming pattern
        self.naming_combo = QComboBox()
        self.naming_combo.addItems([
            "{name}_hevc.{ext}",
            "{name}.hevc.{ext}",
            "{name} (H.265).{ext}",
            "HEVC/{name}.{ext}",
        ])
        form.addRow("Output Naming:", self.naming_combo)

        parent_layout.addWidget(group)

    def _setup_automation_settings(self, parent_layout: QVBoxLayout) -> None:
        """Set up automation settings section.

        Args:
            parent_layout: Parent layout.
        """
        group = QGroupBox("Automation")
        form = QFormLayout(group)

        # Delete original
        self.delete_original_checkbox = QCheckBox("Delete original after successful conversion")
        form.addRow("", self.delete_original_checkbox)

        # Skip existing
        self.skip_existing_checkbox = QCheckBox("Skip files that have already been converted")
        self.skip_existing_checkbox.setChecked(True)
        form.addRow("", self.skip_existing_checkbox)

        # Auto-start
        self.auto_start_checkbox = QCheckBox("Automatically start conversion when files are added")
        self.auto_start_checkbox.setChecked(True)
        form.addRow("", self.auto_start_checkbox)

        # Launch at login
        self.launch_login_checkbox = QCheckBox("Launch at login")
        form.addRow("", self.launch_login_checkbox)

        # Background mode
        self.background_checkbox = QCheckBox("Keep running in menubar when window is closed")
        self.background_checkbox.setChecked(True)
        form.addRow("", self.background_checkbox)

        parent_layout.addWidget(group)

    def _setup_notification_settings(self, parent_layout: QVBoxLayout) -> None:
        """Set up notification settings section.

        Args:
            parent_layout: Parent layout.
        """
        group = QGroupBox("Notifications")
        form = QFormLayout(group)

        # Desktop notifications
        self.notify_complete_checkbox = QCheckBox("Show notification when conversion completes")
        self.notify_complete_checkbox.setChecked(True)
        form.addRow("", self.notify_complete_checkbox)

        self.notify_error_checkbox = QCheckBox("Show notification on errors")
        self.notify_error_checkbox.setChecked(True)
        form.addRow("", self.notify_error_checkbox)

        # Sound
        self.sound_checkbox = QCheckBox("Play sound on completion")
        form.addRow("", self.sound_checkbox)

        parent_layout.addWidget(group)

    def _setup_buttons(self, parent_layout: QVBoxLayout) -> None:
        """Set up action buttons.

        Args:
            parent_layout: Parent layout.
        """
        button_frame = QWidget()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(24, 16, 24, 16)

        reset_button = QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self._on_reset)
        button_layout.addWidget(reset_button)

        button_layout.addStretch()

        save_button = QPushButton("Save Settings")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self._on_save)
        button_layout.addWidget(save_button)

        parent_layout.addWidget(button_frame)

    def _on_quality_changed(self, value: int) -> None:
        """Handle quality slider change.

        Args:
            value: New CRF value.
        """
        self.quality_label.setText(f"CRF: {value}")

    def _on_browse_output(self) -> None:
        """Browse for output directory."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
        )
        if path:
            self.output_dir_edit.setText(path)

    def _on_browse_temp(self) -> None:
        """Browse for temp directory."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Temp Directory",
        )
        if path:
            self.temp_dir_edit.setText(path)

    def _on_reset(self) -> None:
        """Reset settings to defaults."""
        # Encoding
        self.encoder_combo.setCurrentIndex(2)
        self.quality_slider.setValue(28)
        self.preset_combo.setCurrentText("medium")
        self.audio_combo.setCurrentIndex(0)
        self.concurrent_spinbox.setValue(2)

        # Paths
        self.output_dir_edit.clear()
        self.temp_dir_edit.clear()
        self.naming_combo.setCurrentIndex(0)

        # Automation
        self.delete_original_checkbox.setChecked(False)
        self.skip_existing_checkbox.setChecked(True)
        self.auto_start_checkbox.setChecked(True)
        self.launch_login_checkbox.setChecked(False)
        self.background_checkbox.setChecked(True)

        # Notifications
        self.notify_complete_checkbox.setChecked(True)
        self.notify_error_checkbox.setChecked(True)
        self.sound_checkbox.setChecked(False)

    def _on_save(self) -> None:
        """Save current settings."""
        settings = self.get_settings()
        self.settings_changed.emit(settings)
        self.settings_saved.emit()

    def get_settings(self) -> dict:
        """Get current settings as dictionary.

        Returns:
            Dictionary of current settings.
        """
        return {
            "encoding": {
                "encoder": self.encoder_combo.currentText(),
                "quality": self.quality_slider.value(),
                "preset": self.preset_combo.currentText(),
                "audio": self.audio_combo.currentText(),
                "concurrent_jobs": self.concurrent_spinbox.value(),
            },
            "paths": {
                "output_dir": self.output_dir_edit.text() or None,
                "temp_dir": self.temp_dir_edit.text() or None,
                "naming_pattern": self.naming_combo.currentText(),
            },
            "automation": {
                "delete_original": self.delete_original_checkbox.isChecked(),
                "skip_existing": self.skip_existing_checkbox.isChecked(),
                "auto_start": self.auto_start_checkbox.isChecked(),
                "launch_login": self.launch_login_checkbox.isChecked(),
                "background_mode": self.background_checkbox.isChecked(),
            },
            "notifications": {
                "notify_complete": self.notify_complete_checkbox.isChecked(),
                "notify_error": self.notify_error_checkbox.isChecked(),
                "play_sound": self.sound_checkbox.isChecked(),
            },
        }

    def load_settings(self, settings: dict) -> None:
        """Load settings from dictionary.

        Args:
            settings: Settings dictionary to load.
        """
        encoding = settings.get("encoding", {})
        if "encoder" in encoding:
            index = self.encoder_combo.findText(encoding["encoder"])
            if index >= 0:
                self.encoder_combo.setCurrentIndex(index)
        if "quality" in encoding:
            self.quality_slider.setValue(encoding["quality"])
        if "preset" in encoding:
            self.preset_combo.setCurrentText(encoding["preset"])
        if "audio" in encoding:
            index = self.audio_combo.findText(encoding["audio"])
            if index >= 0:
                self.audio_combo.setCurrentIndex(index)
        if "concurrent_jobs" in encoding:
            self.concurrent_spinbox.setValue(encoding["concurrent_jobs"])

        paths = settings.get("paths", {})
        if paths.get("output_dir"):
            self.output_dir_edit.setText(paths["output_dir"])
        if paths.get("temp_dir"):
            self.temp_dir_edit.setText(paths["temp_dir"])
        if "naming_pattern" in paths:
            index = self.naming_combo.findText(paths["naming_pattern"])
            if index >= 0:
                self.naming_combo.setCurrentIndex(index)

        automation = settings.get("automation", {})
        self.delete_original_checkbox.setChecked(automation.get("delete_original", False))
        self.skip_existing_checkbox.setChecked(automation.get("skip_existing", True))
        self.auto_start_checkbox.setChecked(automation.get("auto_start", True))
        self.launch_login_checkbox.setChecked(automation.get("launch_login", False))
        self.background_checkbox.setChecked(automation.get("background_mode", True))

        notifications = settings.get("notifications", {})
        self.notify_complete_checkbox.setChecked(notifications.get("notify_complete", True))
        self.notify_error_checkbox.setChecked(notifications.get("notify_error", True))
        self.sound_checkbox.setChecked(notifications.get("play_sound", False))
