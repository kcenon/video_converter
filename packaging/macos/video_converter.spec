# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Video Converter macOS application.

This spec file configures PyInstaller to create a macOS .app bundle
with all necessary dependencies and resources.
"""

import os
import sys
from pathlib import Path

# Determine paths
SPEC_DIR = Path(SPECPATH)
PROJECT_ROOT = SPEC_DIR.parent.parent
SRC_DIR = PROJECT_ROOT / "src"


def get_version_from_pyproject() -> str:
    """Read version from pyproject.toml."""
    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    if pyproject_path.exists():
        try:
            # Python 3.11+ has tomllib built-in
            import tomllib
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                return data.get("project", {}).get("version", "0.0.0")
        except ImportError:
            # Fallback for Python < 3.11: parse manually
            import re
            content = pyproject_path.read_text()
            match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
            if match:
                return match.group(1)
    return "0.0.0"


# App metadata
APP_NAME = "Video Converter"
APP_VERSION = get_version_from_pyproject()
BUNDLE_ID = "com.github.kcenon.videoconverter"

# Analysis configuration
a = Analysis(
    [str(SRC_DIR / "video_converter" / "gui" / "app.py")],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=[
        # Include package data
        (str(SRC_DIR / "video_converter" / "py.typed"), "video_converter"),
    ],
    hiddenimports=[
        # PySide6 modules
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtSvg",
        # Video converter modules
        "video_converter",
        "video_converter.gui",
        "video_converter.gui.app",
        "video_converter.gui.main_window",
        "video_converter.gui.menubar",
        "video_converter.gui.menubar.menubar_app",
        "video_converter.gui.views",
        "video_converter.gui.views.home_view",
        "video_converter.gui.views.convert_view",
        "video_converter.gui.views.queue_view",
        "video_converter.gui.views.settings_view",
        "video_converter.gui.views.photos_view",
        "video_converter.gui.widgets",
        "video_converter.gui.widgets.drop_zone",
        "video_converter.gui.widgets.progress_card",
        "video_converter.gui.widgets.recent_list",
        "video_converter.gui.widgets.video_grid",
        "video_converter.gui.dialogs",
        "video_converter.gui.dialogs.result_dialog",
        "video_converter.gui.services",
        "video_converter.gui.services.conversion_service",
        "video_converter.gui.services.settings_manager",
        "video_converter.gui.services.photos_service",
        "video_converter.gui.styles",
        "video_converter.gui.styles.theme",
        # Core modules
        "video_converter.core",
        "video_converter.converters",
        "video_converter.processors",
        "video_converter.handlers",
        "video_converter.utils",
        # Dependencies
        "osxphotos",
        "rich",
        "click",
        "pydantic",
        "pydantic_settings",
        "PIL",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce bundle size
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
        "mypy",
        "ruff",
    ],
    noarchive=False,
    optimize=0,
)

# Remove duplicate binaries and datas
pyz = PYZ(a.pure)

# Executable configuration
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Video Converter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=str(SPEC_DIR / "entitlements.plist"),
)

# Collect all files
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Video Converter",
)

# macOS .app bundle configuration
app = BUNDLE(
    coll,
    name=f"{APP_NAME}.app",
    icon=str(SPEC_DIR / "resources" / "AppIcon.icns"),
    bundle_identifier=BUNDLE_ID,
    version=APP_VERSION,
    info_plist={
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleExecutable": "Video Converter",
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleVersion": APP_VERSION,
        "CFBundleShortVersionString": APP_VERSION,
        "CFBundlePackageType": "APPL",
        "CFBundleSignature": "????",
        "CFBundleInfoDictionaryVersion": "6.0",
        "LSMinimumSystemVersion": "12.0",
        "NSHumanReadableCopyright": "Copyright 2024 Video Converter Team",
        "NSHighResolutionCapable": True,
        "NSSupportsAutomaticGraphicsSwitching": True,
        "NSRequiresAquaSystemAppearance": False,
        # Privacy permissions
        "NSPhotoLibraryUsageDescription": (
            "Video Converter needs access to your Photos library "
            "to convert videos stored in Photos."
        ),
        "NSAppleEventsUsageDescription": (
            "Video Converter needs to control Photos app "
            "to import converted videos."
        ),
        # File associations
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "Video File",
                "CFBundleTypeRole": "Viewer",
                "LSItemContentTypes": [
                    "public.movie",
                    "public.video",
                    "com.apple.quicktime-movie",
                    "public.mpeg-4",
                    "public.avi",
                ],
                "LSHandlerRank": "Alternate",
            },
        ],
        # URL scheme
        "CFBundleURLTypes": [
            {
                "CFBundleURLName": BUNDLE_ID,
                "CFBundleURLSchemes": ["videoconverter"],
            },
        ],
        # Sparkle auto-update (if enabled)
        "SUFeedURL": "https://github.com/kcenon/video_converter/releases.atom",
        "SUPublicEDKey": "",  # Add Ed25519 public key for Sparkle
    },
)
