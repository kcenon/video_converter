"""Theme and styling for the Video Converter GUI.

This module provides macOS-native theming and dark mode support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

if TYPE_CHECKING:
    pass


def is_dark_mode() -> bool:
    """Check if system is in dark mode.

    Returns:
        True if dark mode is enabled.
    """
    palette = QApplication.palette()
    lightness = palette.color(QPalette.ColorRole.Window).lightness()
    return bool(lightness < 128)


def apply_macos_theme(app: QApplication) -> None:
    """Apply macOS-native theming to the application.

    Args:
        app: QApplication instance.
    """
    # Set macOS-specific style
    app.setStyle("macOS")

    # Apply custom stylesheet
    if is_dark_mode():
        stylesheet = get_dark_mode_stylesheet()
    else:
        stylesheet = get_light_mode_stylesheet()

    app.setStyleSheet(stylesheet)


def get_base_stylesheet() -> str:
    """Get base stylesheet shared between light and dark modes.

    Returns:
        Base stylesheet string.
    """
    return """
/* General */
QWidget {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue";
    font-size: 13px;
}

/* Tab Bar */
QTabBar {
    qproperty-drawBase: 0;
}

QTabBar::tab {
    padding: 8px 16px;
    margin-right: 4px;
    border: none;
    border-radius: 6px;
}

/* Scroll Areas */
QScrollArea {
    border: none;
}

QScrollBar:vertical {
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    min-height: 30px;
    border-radius: 4px;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}

/* Group Boxes */
QGroupBox {
    font-weight: 500;
    border: 1px solid;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    left: 12px;
}

/* Progress Bars */
QProgressBar {
    border: none;
    border-radius: 4px;
    text-align: center;
    height: 8px;
}

QProgressBar::chunk {
    border-radius: 4px;
}

/* Buttons */
QPushButton {
    padding: 6px 16px;
    border-radius: 6px;
    font-weight: 500;
}

QPushButton#primaryButton {
    font-weight: 600;
}

/* Input Fields */
QLineEdit, QSpinBox, QComboBox {
    padding: 6px 10px;
    border-radius: 6px;
    border: 1px solid;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 4px;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}

/* Check Boxes */
QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
}

/* Labels */
#welcomeLabel {
    font-size: 24px;
    font-weight: 600;
}

#subtitleLabel {
    font-size: 14px;
}

#sectionHeader {
    font-size: 14px;
    font-weight: 600;
}

#viewTitle {
    font-size: 20px;
    font-weight: 600;
}

#infoLabel, #cardInfo {
    font-size: 12px;
}

#emptyLabel, #emptyStateLabel {
    font-size: 16px;
    font-weight: 500;
}

#emptyStateHint {
    font-size: 13px;
}

/* Drop Zone */
#dropZone {
    min-height: 150px;
    border-radius: 12px;
}

#dropZoneIcon {
    font-size: 48px;
}

#dropZoneMain {
    font-size: 16px;
    font-weight: 500;
}

#dropZoneSubtitle {
    font-size: 13px;
}

#dropZoneFormats {
    font-size: 11px;
}

/* Progress Card */
#progressCard {
    border-radius: 8px;
}

#cardTitle {
    font-size: 14px;
    font-weight: 500;
}

/* Video Thumbnail */
#videoThumbnail {
    border-radius: 8px;
}

#videoThumbnail[selected="true"] {
    border: 2px solid;
}

#thumbnailImage {
    border-radius: 6px;
}

#thumbnailName {
    font-size: 11px;
    font-weight: 500;
}

#thumbnailDuration {
    font-size: 10px;
}

/* Recent Item */
#recentItem {
    border-radius: 6px;
}

#recentItemName {
    font-weight: 500;
}

#recentItemStatus {
    font-size: 12px;
}

#recentItemSize {
    font-size: 12px;
}
"""


def get_light_mode_stylesheet() -> str:
    """Get light mode stylesheet.

    Returns:
        Light mode stylesheet string.
    """
    base = get_base_stylesheet()
    light_colors = """
/* Light Mode Colors */
QMainWindow, QWidget {
    background-color: #f5f5f7;
    color: #1d1d1f;
}

QTabBar::tab {
    background-color: transparent;
    color: #666;
}

QTabBar::tab:selected {
    background-color: #e8e8ed;
    color: #1d1d1f;
}

QTabBar::tab:hover:!selected {
    background-color: #f0f0f5;
}

QGroupBox {
    border-color: #d2d2d7;
    background-color: #ffffff;
}

QProgressBar {
    background-color: #e5e5ea;
}

QProgressBar::chunk {
    background-color: #007aff;
}

QPushButton {
    background-color: #ffffff;
    border: 1px solid #d2d2d7;
    color: #1d1d1f;
}

QPushButton:hover {
    background-color: #f5f5f7;
}

QPushButton:pressed {
    background-color: #e5e5ea;
}

QPushButton#primaryButton {
    background-color: #007aff;
    border: none;
    color: #ffffff;
}

QPushButton#primaryButton:hover {
    background-color: #0066d6;
}

QPushButton#primaryButton:pressed {
    background-color: #0055b3;
}

QPushButton#primaryButton:disabled {
    background-color: #c7c7cc;
}

QLineEdit, QSpinBox, QComboBox {
    background-color: #ffffff;
    border-color: #d2d2d7;
    color: #1d1d1f;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #007aff;
}

QSlider::groove:horizontal {
    background-color: #e5e5ea;
}

QSlider::handle:horizontal {
    background-color: #ffffff;
    border: 1px solid #d2d2d7;
}

QCheckBox::indicator {
    border: 1px solid #d2d2d7;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #007aff;
    border-color: #007aff;
}

QScrollBar::handle:vertical {
    background-color: #c7c7cc;
}

#subtitleLabel, #infoLabel, #cardInfo {
    color: #86868b;
}

#dropZone {
    background-color: #fafafa;
}

#dropZone[dragOver="true"] {
    background-color: #e8f4ff;
}

#progressCard, #recentItem {
    background-color: #ffffff;
    border: 1px solid #e5e5ea;
}

#videoThumbnail {
    background-color: #ffffff;
    border: 1px solid #e5e5ea;
}

#videoThumbnail[selected="true"] {
    border-color: #007aff;
}

#thumbnailImage {
    background-color: #f5f5f7;
}

#statsBar, #viewHeader, #viewFooter {
    background-color: #ffffff;
    border-top: 1px solid #e5e5ea;
}

#viewHeader {
    border-top: none;
    border-bottom: 1px solid #e5e5ea;
}

#queueHeader {
    background-color: #ffffff;
    border: 1px solid #e5e5ea;
    border-radius: 8px;
}

#emptyState {
    background-color: #f5f5f7;
    border-radius: 12px;
}
"""
    return base + light_colors


def get_dark_mode_stylesheet() -> str:
    """Get dark mode stylesheet.

    Returns:
        Dark mode stylesheet string.
    """
    base = get_base_stylesheet()
    dark_colors = """
/* Dark Mode Colors */
QMainWindow, QWidget {
    background-color: #1c1c1e;
    color: #f5f5f7;
}

QTabBar::tab {
    background-color: transparent;
    color: #98989d;
}

QTabBar::tab:selected {
    background-color: #3a3a3c;
    color: #f5f5f7;
}

QTabBar::tab:hover:!selected {
    background-color: #2c2c2e;
}

QGroupBox {
    border-color: #3a3a3c;
    background-color: #2c2c2e;
}

QProgressBar {
    background-color: #3a3a3c;
}

QProgressBar::chunk {
    background-color: #0a84ff;
}

QPushButton {
    background-color: #3a3a3c;
    border: 1px solid #48484a;
    color: #f5f5f7;
}

QPushButton:hover {
    background-color: #48484a;
}

QPushButton:pressed {
    background-color: #545456;
}

QPushButton#primaryButton {
    background-color: #0a84ff;
    border: none;
    color: #ffffff;
}

QPushButton#primaryButton:hover {
    background-color: #0077ed;
}

QPushButton#primaryButton:pressed {
    background-color: #006adb;
}

QPushButton#primaryButton:disabled {
    background-color: #48484a;
}

QLineEdit, QSpinBox, QComboBox {
    background-color: #2c2c2e;
    border-color: #3a3a3c;
    color: #f5f5f7;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #0a84ff;
}

QSlider::groove:horizontal {
    background-color: #3a3a3c;
}

QSlider::handle:horizontal {
    background-color: #f5f5f7;
    border: none;
}

QCheckBox::indicator {
    border: 1px solid #48484a;
    background-color: #2c2c2e;
}

QCheckBox::indicator:checked {
    background-color: #0a84ff;
    border-color: #0a84ff;
}

QScrollBar::handle:vertical {
    background-color: #636366;
}

#subtitleLabel, #infoLabel, #cardInfo {
    color: #98989d;
}

#dropZone {
    background-color: #2c2c2e;
}

#dropZone[dragOver="true"] {
    background-color: #1a3a5c;
}

#progressCard, #recentItem {
    background-color: #2c2c2e;
    border: 1px solid #3a3a3c;
}

#videoThumbnail {
    background-color: #2c2c2e;
    border: 1px solid #3a3a3c;
}

#videoThumbnail[selected="true"] {
    border-color: #0a84ff;
}

#thumbnailImage {
    background-color: #1c1c1e;
}

#statsBar, #viewHeader, #viewFooter {
    background-color: #2c2c2e;
    border-top: 1px solid #3a3a3c;
}

#viewHeader {
    border-top: none;
    border-bottom: 1px solid #3a3a3c;
}

#queueHeader {
    background-color: #2c2c2e;
    border: 1px solid #3a3a3c;
    border-radius: 8px;
}

#emptyState {
    background-color: #2c2c2e;
    border-radius: 12px;
}
"""
    return base + dark_colors
