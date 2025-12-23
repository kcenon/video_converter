"""Tests for the UpdateService.

This module tests the auto-update service functionality including
version checking, GitHub API integration, and signal emission.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from video_converter.gui.services.update_service import (
    CURRENT_VERSION,
    GITHUB_API_URL,
    ReleaseInfo,
    UpdateCheckWorker,
    UpdateService,
    check_for_updates_sync,
    is_newer_version,
    parse_version,
)

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


pytestmark = pytest.mark.gui


# ============================================================================
# Mock Data
# ============================================================================

MOCK_GITHUB_RESPONSE = {
    "tag_name": "v0.4.0",
    "name": "Video Converter v0.4.0",
    "body": "## What's New\n- AV1 codec support\n- Bug fixes",
    "html_url": "https://github.com/kcenon/video_converter/releases/tag/v0.4.0",
    "published_at": "2025-12-25T00:00:00Z",
    "prerelease": False,
    "assets": [
        {
            "name": "Video.Converter.v0.4.0.dmg",
            "browser_download_url": "https://github.com/kcenon/video_converter/releases/download/v0.4.0/Video.Converter.v0.4.0.dmg",
        }
    ],
}

MOCK_GITHUB_RESPONSE_NO_ASSETS = {
    "tag_name": "v0.4.0",
    "name": "Video Converter v0.4.0",
    "body": "## What's New\n- AV1 codec support",
    "html_url": "https://github.com/kcenon/video_converter/releases/tag/v0.4.0",
    "published_at": "2025-12-25T00:00:00Z",
    "prerelease": False,
    "assets": [],
}

MOCK_GITHUB_RESPONSE_PRERELEASE = {
    "tag_name": "v0.5.0",
    "name": "Video Converter v0.5.0 Beta 1",
    "body": "## Beta Release\n- New experimental features",
    "html_url": "https://github.com/kcenon/video_converter/releases/tag/v0.5.0",
    "published_at": "2025-12-30T00:00:00Z",
    "prerelease": True,
    "assets": [
        {
            "name": "Video.Converter.v0.5.0.dmg",
            "browser_download_url": "https://github.com/kcenon/video_converter/releases/download/v0.5.0/Video.Converter.v0.5.0.dmg",
        }
    ],
}

MOCK_GITHUB_RESPONSE_MINIMAL = {
    "tag_name": "v0.3.1",
    "name": "",
    "body": "",
    "html_url": "",
    "published_at": "",
    "prerelease": False,
    "assets": [],
}


# ============================================================================
# ReleaseInfo Tests
# ============================================================================


class TestReleaseInfo:
    """Tests for ReleaseInfo dataclass."""

    def test_release_info_creation(self) -> None:
        """Test that ReleaseInfo can be created with all fields."""
        release = ReleaseInfo(
            version="0.4.0",
            tag_name="v0.4.0",
            name="Video Converter v0.4.0",
            body="## What's New\n- Bug fixes",
            html_url="https://github.com/kcenon/video_converter/releases/tag/v0.4.0",
            download_url="https://example.com/download.dmg",
            published_at="2025-12-25T00:00:00Z",
            is_prerelease=False,
        )

        assert release.version == "0.4.0"
        assert release.tag_name == "v0.4.0"
        assert release.name == "Video Converter v0.4.0"
        assert release.is_prerelease is False

    def test_from_github_response_full(self) -> None:
        """Test parsing a full GitHub API response."""
        release = ReleaseInfo.from_github_response(MOCK_GITHUB_RESPONSE)

        assert release.version == "0.4.0"
        assert release.tag_name == "v0.4.0"
        assert release.name == "Video Converter v0.4.0"
        assert "AV1 codec support" in release.body
        assert release.html_url == MOCK_GITHUB_RESPONSE["html_url"]
        assert release.is_prerelease is False

    def test_from_github_response_with_dmg_asset(self) -> None:
        """Test that DMG download URL is extracted correctly."""
        release = ReleaseInfo.from_github_response(MOCK_GITHUB_RESPONSE)

        assert release.download_url is not None
        assert release.download_url.endswith(".dmg")

    def test_from_github_response_no_assets(self) -> None:
        """Test parsing response with no assets."""
        release = ReleaseInfo.from_github_response(MOCK_GITHUB_RESPONSE_NO_ASSETS)

        assert release.download_url is None

    def test_from_github_response_minimal(self) -> None:
        """Test parsing a minimal GitHub API response."""
        release = ReleaseInfo.from_github_response(MOCK_GITHUB_RESPONSE_MINIMAL)

        assert release.version == "0.3.1"
        assert release.name == ""
        assert release.body == ""
        assert release.download_url is None

    def test_from_github_response_prerelease(self) -> None:
        """Test parsing a prerelease response."""
        release = ReleaseInfo.from_github_response(MOCK_GITHUB_RESPONSE_PRERELEASE)

        assert release.is_prerelease is True
        assert release.version == "0.5.0"


# ============================================================================
# Version Comparison Tests
# ============================================================================


class TestVersionComparison:
    """Tests for version parsing and comparison functions."""

    def test_parse_version_standard(self) -> None:
        """Test parsing standard version strings."""
        assert parse_version("0.3.0") == (0, 3, 0)
        assert parse_version("1.2.3") == (1, 2, 3)
        assert parse_version("0.3.0.0") == (0, 3, 0, 0)

    def test_parse_version_invalid(self) -> None:
        """Test parsing invalid version strings."""
        assert parse_version("invalid") == (0,)
        assert parse_version("") == (0,)

    def test_newer_version_available(self) -> None:
        """Test that newer version is detected correctly."""
        assert is_newer_version("0.4.0", "0.3.0") is True
        assert is_newer_version("1.0.0", "0.9.9") is True
        assert is_newer_version("0.3.1", "0.3.0") is True

    def test_same_version(self) -> None:
        """Test that same version returns False."""
        assert is_newer_version("0.3.0", "0.3.0") is False

    def test_older_version(self) -> None:
        """Test that older version returns False."""
        assert is_newer_version("0.2.0", "0.3.0") is False
        assert is_newer_version("0.3.0", "0.3.1") is False

    def test_version_with_extra_components(self) -> None:
        """Test version comparison with different component counts."""
        assert is_newer_version("0.3.0.1", "0.3.0") is True
        assert is_newer_version("0.3.0", "0.3.0.0") is False


# ============================================================================
# UpdateCheckWorker Tests
# ============================================================================


class TestUpdateCheckWorker:
    """Tests for UpdateCheckWorker thread."""

    def test_worker_initialization(self) -> None:
        """Test that worker initializes correctly."""
        worker = UpdateCheckWorker()
        assert worker._include_prereleases is False

        worker_with_prereleases = UpdateCheckWorker(include_prereleases=True)
        assert worker_with_prereleases._include_prereleases is True

    def test_checker_emits_result(self, qtbot: QtBot) -> None:
        """Test that worker emits finished signal with release info."""
        worker = UpdateCheckWorker()

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(MOCK_GITHUB_RESPONSE).encode(
            "utf-8"
        )
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            with qtbot.waitSignal(worker.finished, timeout=5000) as blocker:
                worker.run()

        release = blocker.args[0]
        assert release is not None
        assert isinstance(release, ReleaseInfo)
        assert release.version == "0.4.0"

    def test_checker_emits_none_when_no_update(self, qtbot: QtBot) -> None:
        """Test that worker emits None when current version is latest."""
        worker = UpdateCheckWorker()

        # Create response with version equal to current
        response_data = {**MOCK_GITHUB_RESPONSE, "tag_name": f"v{CURRENT_VERSION}"}

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            with qtbot.waitSignal(worker.finished, timeout=5000) as blocker:
                worker.run()

        assert blocker.args[0] is None

    def test_checker_handles_network_error(self, qtbot: QtBot) -> None:
        """Test that worker emits error signal on network failure."""
        worker = UpdateCheckWorker()

        with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
            with qtbot.waitSignal(worker.error, timeout=5000) as blocker:
                worker.run()

        assert "Network error" in blocker.args[0]

    def test_checker_handles_json_error(self, qtbot: QtBot) -> None:
        """Test that worker handles invalid JSON response."""
        worker = UpdateCheckWorker()

        mock_response = MagicMock()
        mock_response.read.return_value = b"not valid json"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            with qtbot.waitSignal(worker.error, timeout=5000) as blocker:
                worker.run()

        assert blocker.args[0] is not None

    def test_checker_skips_prerelease_by_default(self, qtbot: QtBot) -> None:
        """Test that worker skips prerelease versions by default."""
        worker = UpdateCheckWorker(include_prereleases=False)

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            MOCK_GITHUB_RESPONSE_PRERELEASE
        ).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            with qtbot.waitSignal(worker.finished, timeout=5000) as blocker:
                worker.run()

        assert blocker.args[0] is None

    def test_checker_includes_prerelease_when_enabled(self, qtbot: QtBot) -> None:
        """Test that worker includes prerelease when enabled."""
        worker = UpdateCheckWorker(include_prereleases=True)

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            MOCK_GITHUB_RESPONSE_PRERELEASE
        ).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            with qtbot.waitSignal(worker.finished, timeout=5000) as blocker:
                worker.run()

        release = blocker.args[0]
        assert release is not None
        assert release.is_prerelease is True


# ============================================================================
# UpdateService Tests
# ============================================================================


class TestUpdateService:
    """Tests for UpdateService class."""

    @pytest.fixture
    def update_service(self, qtbot: QtBot) -> UpdateService:
        """Create UpdateService instance for testing."""
        service = UpdateService()
        yield service
        # Cleanup any running threads
        service._cleanup()

    def test_service_initialization(self, update_service: UpdateService) -> None:
        """Test that service initializes correctly."""
        assert update_service is not None
        assert update_service._worker is None
        assert update_service._thread is None
        assert update_service._last_release is None

    def test_current_version_property(self, update_service: UpdateService) -> None:
        """Test current_version property returns correct version."""
        assert update_service.current_version == CURRENT_VERSION

    def test_last_release_property(self, update_service: UpdateService) -> None:
        """Test last_release property returns None initially."""
        assert update_service.last_release is None

    def test_check_for_updates_success(
        self, qtbot: QtBot, update_service: UpdateService
    ) -> None:
        """Test successful async update check."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(MOCK_GITHUB_RESPONSE).encode(
            "utf-8"
        )
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            with qtbot.waitSignal(
                update_service.update_available, timeout=5000
            ) as blocker:
                update_service.check_for_updates()

        release = blocker.args[0]
        assert release is not None
        assert release.version == "0.4.0"
        assert update_service.last_release is not None

    def test_check_for_updates_no_update(
        self, qtbot: QtBot, update_service: UpdateService
    ) -> None:
        """Test async check when no update available."""
        response_data = {**MOCK_GITHUB_RESPONSE, "tag_name": f"v{CURRENT_VERSION}"}

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            with qtbot.waitSignal(
                update_service.no_update_available, timeout=5000
            ):
                update_service.check_for_updates()

    def test_check_for_updates_error(
        self, qtbot: QtBot, update_service: UpdateService
    ) -> None:
        """Test async check error handling."""
        with patch("urllib.request.urlopen", side_effect=Exception("Connection failed")):
            with qtbot.waitSignal(
                update_service.update_check_failed, timeout=5000
            ) as blocker:
                update_service.check_for_updates()

        assert "Connection failed" in blocker.args[0]

    def test_update_available_signal(
        self, qtbot: QtBot, update_service: UpdateService
    ) -> None:
        """Test that update_available signal contains ReleaseInfo."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(MOCK_GITHUB_RESPONSE).encode(
            "utf-8"
        )
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            with qtbot.waitSignal(
                update_service.update_available, timeout=5000
            ) as blocker:
                update_service.check_for_updates()

        release = blocker.args[0]
        assert isinstance(release, ReleaseInfo)
        assert release.html_url == MOCK_GITHUB_RESPONSE["html_url"]

    def test_error_signal(
        self, qtbot: QtBot, update_service: UpdateService
    ) -> None:
        """Test that error signal contains error message."""
        with patch("urllib.request.urlopen", side_effect=Exception("Test error")):
            with qtbot.waitSignal(
                update_service.update_check_failed, timeout=5000
            ) as blocker:
                update_service.check_for_updates()

        assert isinstance(blocker.args[0], str)
        assert "Test error" in blocker.args[0]

    def test_concurrent_check_prevention(
        self, qtbot: QtBot, update_service: UpdateService
    ) -> None:
        """Test that concurrent update checks are prevented."""
        # Create a mock that blocks
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(MOCK_GITHUB_RESPONSE).encode(
            "utf-8"
        )
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            # Start first check
            update_service.check_for_updates()

            # Attempt second check while first is running
            thread_before = update_service._thread
            update_service.check_for_updates()

            # Should be the same thread (second check ignored)
            assert update_service._thread is thread_before

            # Wait for completion
            qtbot.waitSignal(update_service.update_available, timeout=5000)


class TestUpdateServiceOpenDownload:
    """Tests for UpdateService browser operations."""

    @pytest.fixture
    def update_service_with_release(self, qtbot: QtBot) -> UpdateService:
        """Create UpdateService with a cached release."""
        service = UpdateService()
        service._last_release = ReleaseInfo.from_github_response(MOCK_GITHUB_RESPONSE)
        yield service
        service._cleanup()

    def test_open_download_page_with_release(
        self, update_service_with_release: UpdateService
    ) -> None:
        """Test opening download page when release is cached."""
        with patch("subprocess.run") as mock_run:
            update_service_with_release.open_download_page()

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "open"
        assert MOCK_GITHUB_RESPONSE["html_url"] in call_args[1]

    def test_open_download_page_without_release(self, qtbot: QtBot) -> None:
        """Test opening download page when no release is cached."""
        service = UpdateService()

        with patch("subprocess.run") as mock_run:
            service.open_download_page()

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "open"
        assert "releases" in call_args[1]

        service._cleanup()

    def test_open_release_notes(
        self, update_service_with_release: UpdateService
    ) -> None:
        """Test opening release notes."""
        with patch("subprocess.run") as mock_run:
            update_service_with_release.open_release_notes()

        mock_run.assert_called_once()


# ============================================================================
# Synchronous Update Check Tests
# ============================================================================


class TestCheckForUpdatesSync:
    """Tests for synchronous update check function."""

    def test_check_for_updates_sync_success(self) -> None:
        """Test successful synchronous update check."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(MOCK_GITHUB_RESPONSE).encode(
            "utf-8"
        )
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            release = check_for_updates_sync()

        assert release is not None
        assert release.version == "0.4.0"

    def test_check_for_updates_sync_no_update(self) -> None:
        """Test synchronous check when no update available."""
        response_data = {**MOCK_GITHUB_RESPONSE, "tag_name": f"v{CURRENT_VERSION}"}

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            release = check_for_updates_sync()

        assert release is None

    def test_check_for_updates_sync_error(self) -> None:
        """Test synchronous check returns None on error."""
        with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
            release = check_for_updates_sync()

        assert release is None

    def test_check_for_updates_sync_skips_prerelease(self) -> None:
        """Test synchronous check skips prerelease by default."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            MOCK_GITHUB_RESPONSE_PRERELEASE
        ).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            release = check_for_updates_sync(include_prereleases=False)

        assert release is None

    def test_check_for_updates_sync_includes_prerelease(self) -> None:
        """Test synchronous check includes prerelease when enabled."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            MOCK_GITHUB_RESPONSE_PRERELEASE
        ).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            release = check_for_updates_sync(include_prereleases=True)

        assert release is not None
        assert release.is_prerelease is True
