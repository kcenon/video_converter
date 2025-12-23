"""Auto-update service for Video Converter GUI.

This module provides functionality to check for application updates
via GitHub Releases API and optionally download/install updates.
"""

from __future__ import annotations

import json
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QThread, Signal

if TYPE_CHECKING:
    from typing import Any


# Current application version
CURRENT_VERSION = "0.3.0"

# GitHub repository information
GITHUB_OWNER = "kcenon"
GITHUB_REPO = "video_converter"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"


@dataclass
class ReleaseInfo:
    """Information about a GitHub release."""

    version: str
    tag_name: str
    name: str
    body: str
    html_url: str
    download_url: str | None
    published_at: str
    is_prerelease: bool

    @classmethod
    def from_github_response(cls, data: dict[str, Any]) -> ReleaseInfo:
        """Create ReleaseInfo from GitHub API response.

        Args:
            data: GitHub API release response.

        Returns:
            ReleaseInfo instance.
        """
        # Find DMG asset
        download_url = None
        for asset in data.get("assets", []):
            if asset.get("name", "").endswith(".dmg"):
                download_url = asset.get("browser_download_url")
                break

        # Extract version from tag (remove 'v' prefix if present)
        tag_name = data.get("tag_name", "")
        version = tag_name.lstrip("v")

        return cls(
            version=version,
            tag_name=tag_name,
            name=data.get("name", ""),
            body=data.get("body", ""),
            html_url=data.get("html_url", ""),
            download_url=download_url,
            published_at=data.get("published_at", ""),
            is_prerelease=data.get("prerelease", False),
        )


def parse_version(version: str) -> tuple[int, ...]:
    """Parse version string into comparable tuple.

    Args:
        version: Version string (e.g., "0.3.0" or "0.3.0.0").

    Returns:
        Tuple of version components as integers.
    """
    try:
        return tuple(int(x) for x in version.split("."))
    except ValueError:
        return (0,)


def is_newer_version(latest: str, current: str) -> bool:
    """Check if latest version is newer than current.

    Args:
        latest: Latest available version.
        current: Current installed version.

    Returns:
        True if latest is newer than current.
    """
    return parse_version(latest) > parse_version(current)


class UpdateCheckWorker(QObject):
    """Worker thread for checking updates."""

    finished = Signal(object)  # ReleaseInfo or None
    error = Signal(str)

    def __init__(self, include_prereleases: bool = False) -> None:
        """Initialize the worker.

        Args:
            include_prereleases: Whether to include prerelease versions.
        """
        super().__init__()
        self._include_prereleases = include_prereleases

    def run(self) -> None:
        """Check for updates from GitHub."""
        try:
            # Create request with user agent (required by GitHub API)
            request = urllib.request.Request(
                GITHUB_API_URL,
                headers={"User-Agent": f"VideoConverter/{CURRENT_VERSION}"},
            )

            # Fetch release info
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

            # Parse release info
            release = ReleaseInfo.from_github_response(data)

            # Check if it's a prerelease and we should skip it
            if release.is_prerelease and not self._include_prereleases:
                self.finished.emit(None)
                return

            # Check if it's newer than current version
            if is_newer_version(release.version, CURRENT_VERSION):
                self.finished.emit(release)
            else:
                self.finished.emit(None)

        except Exception as e:
            self.error.emit(str(e))


class UpdateService(QObject):
    """Service for checking and managing application updates.

    This service provides methods to check for updates from GitHub Releases
    and optionally open the download page or trigger an update.

    Signals:
        update_available: Emitted when a new update is available.
        no_update_available: Emitted when no update is available.
        update_check_failed: Emitted when update check fails.
    """

    update_available = Signal(object)  # ReleaseInfo
    no_update_available = Signal()
    update_check_failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        """Initialize the update service.

        Args:
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._worker: UpdateCheckWorker | None = None
        self._thread: QThread | None = None
        self._last_release: ReleaseInfo | None = None

    @property
    def current_version(self) -> str:
        """Get the current application version."""
        return CURRENT_VERSION

    @property
    def last_release(self) -> ReleaseInfo | None:
        """Get the last checked release info."""
        return self._last_release

    def check_for_updates(self, include_prereleases: bool = False) -> None:
        """Check for available updates asynchronously.

        Args:
            include_prereleases: Whether to include prerelease versions.
        """
        # Don't start a new check if one is already running
        if self._thread is not None and self._thread.isRunning():
            return

        # Create worker and thread
        self._worker = UpdateCheckWorker(include_prereleases)
        self._thread = QThread()

        # Move worker to thread
        self._worker.moveToThread(self._thread)

        # Connect signals
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_check_finished)
        self._worker.error.connect(self._on_check_error)
        self._worker.finished.connect(self._cleanup)
        self._worker.error.connect(self._cleanup)

        # Start thread
        self._thread.start()

    def _on_check_finished(self, release: ReleaseInfo | None) -> None:
        """Handle successful update check.

        Args:
            release: Release info if update available, None otherwise.
        """
        if release is not None:
            self._last_release = release
            self.update_available.emit(release)
        else:
            self.no_update_available.emit()

    def _on_check_error(self, error: str) -> None:
        """Handle update check error.

        Args:
            error: Error message.
        """
        self.update_check_failed.emit(error)

    def _cleanup(self) -> None:
        """Clean up worker thread."""
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
        self._worker = None

    def open_download_page(self) -> None:
        """Open the download page in the default browser."""
        if self._last_release is not None and self._last_release.html_url:
            subprocess.run(
                ["open", self._last_release.html_url],
                check=False,
            )
        else:
            # Open releases page
            subprocess.run(
                ["open", f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"],
                check=False,
            )

    def open_release_notes(self) -> None:
        """Open the release notes page in the default browser."""
        self.open_download_page()

    def download_update(self, destination: Path | None = None) -> Path | None:
        """Download the latest update DMG.

        This is a synchronous operation and should be called from a worker thread.

        Args:
            destination: Destination path for the DMG. If None, downloads to temp.

        Returns:
            Path to downloaded DMG, or None if download failed.
        """
        if self._last_release is None or self._last_release.download_url is None:
            return None

        if destination is None:
            destination = Path.home() / "Downloads" / f"VideoConverter-{self._last_release.version}.dmg"

        try:
            request = urllib.request.Request(
                self._last_release.download_url,
                headers={"User-Agent": f"VideoConverter/{CURRENT_VERSION}"},
            )

            with urllib.request.urlopen(request, timeout=300) as response:
                with open(destination, "wb") as f:
                    while chunk := response.read(8192):
                        f.write(chunk)

            return destination
        except Exception:
            return None


def check_for_updates_sync(include_prereleases: bool = False) -> ReleaseInfo | None:
    """Synchronous version of update check for CLI usage.

    Args:
        include_prereleases: Whether to include prerelease versions.

    Returns:
        ReleaseInfo if update available, None otherwise.
    """
    try:
        request = urllib.request.Request(
            GITHUB_API_URL,
            headers={"User-Agent": f"VideoConverter/{CURRENT_VERSION}"},
        )

        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        release = ReleaseInfo.from_github_response(data)

        if release.is_prerelease and not include_prereleases:
            return None

        if is_newer_version(release.version, CURRENT_VERSION):
            return release

        return None
    except Exception:
        return None
