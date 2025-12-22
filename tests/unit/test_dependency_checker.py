"""Unit tests for dependency_checker module."""

from __future__ import annotations

from unittest.mock import patch

from video_converter.utils.command_runner import CommandResult
from video_converter.utils.dependency_checker import (
    DependencyChecker,
    DependencyCheckResult,
    DependencyInfo,
    DependencyStatus,
    compare_versions,
)


class TestCompareVersions:
    """Tests for compare_versions function."""

    def test_equal_versions(self) -> None:
        """Test that equal versions return 0."""
        assert compare_versions("5.0", "5.0") == 0
        assert compare_versions("5.1.2", "5.1.2") == 0
        assert compare_versions("6", "6") == 0

    def test_first_version_lower(self) -> None:
        """Test that lower first version returns -1."""
        assert compare_versions("5.0", "5.1") == -1
        assert compare_versions("5.0", "6.0") == -1
        assert compare_versions("5.1.1", "5.1.2") == -1
        assert compare_versions("5", "6") == -1

    def test_first_version_higher(self) -> None:
        """Test that higher first version returns 1."""
        assert compare_versions("5.1", "5.0") == 1
        assert compare_versions("6.0", "5.0") == 1
        assert compare_versions("5.1.2", "5.1.1") == 1
        assert compare_versions("6", "5") == 1

    def test_different_length_versions(self) -> None:
        """Test versions with different number of parts."""
        assert compare_versions("5.0", "5.0.0") == 0
        assert compare_versions("5.0.1", "5.0") == 1
        assert compare_versions("5", "5.0.0") == 0

    def test_versions_with_suffix(self) -> None:
        """Test versions with suffixes like -beta."""
        assert compare_versions("5.0-beta", "5.0") == 0
        assert compare_versions("6.0-rc1", "5.1") == 1
        assert compare_versions("5.0_alpha", "5.0") == 0


class TestDependencyInfo:
    """Tests for DependencyInfo dataclass."""

    def test_is_satisfied_true(self) -> None:
        """Test that is_satisfied returns True when status is SATISFIED."""
        info = DependencyInfo(
            name="Test",
            required_version="1.0",
            current_version="1.0",
            status=DependencyStatus.SATISFIED,
            install_instruction="test",
        )
        assert info.is_satisfied is True

    def test_is_satisfied_false_for_missing(self) -> None:
        """Test that is_satisfied returns False when status is MISSING."""
        info = DependencyInfo(
            name="Test",
            required_version="1.0",
            current_version=None,
            status=DependencyStatus.MISSING,
            install_instruction="test",
        )
        assert info.is_satisfied is False

    def test_is_satisfied_false_for_version_too_low(self) -> None:
        """Test that is_satisfied returns False when version is too low."""
        info = DependencyInfo(
            name="Test",
            required_version="2.0",
            current_version="1.0",
            status=DependencyStatus.VERSION_TOO_LOW,
            install_instruction="test",
        )
        assert info.is_satisfied is False


class TestDependencyCheckResult:
    """Tests for DependencyCheckResult dataclass."""

    def test_all_satisfied_true(self) -> None:
        """Test that all_satisfied returns True when all deps are satisfied."""
        result = DependencyCheckResult(
            dependencies=[
                DependencyInfo(
                    name="A",
                    required_version="1.0",
                    current_version="1.0",
                    status=DependencyStatus.SATISFIED,
                    install_instruction="",
                ),
                DependencyInfo(
                    name="B",
                    required_version="2.0",
                    current_version="2.0",
                    status=DependencyStatus.SATISFIED,
                    install_instruction="",
                ),
            ]
        )
        assert result.all_satisfied is True

    def test_all_satisfied_false(self) -> None:
        """Test that all_satisfied returns False when any dep is missing."""
        result = DependencyCheckResult(
            dependencies=[
                DependencyInfo(
                    name="A",
                    required_version="1.0",
                    current_version="1.0",
                    status=DependencyStatus.SATISFIED,
                    install_instruction="",
                ),
                DependencyInfo(
                    name="B",
                    required_version="2.0",
                    current_version=None,
                    status=DependencyStatus.MISSING,
                    install_instruction="",
                ),
            ]
        )
        assert result.all_satisfied is False

    def test_missing_returns_unsatisfied(self) -> None:
        """Test that missing property returns unsatisfied dependencies."""
        result = DependencyCheckResult(
            dependencies=[
                DependencyInfo(
                    name="A",
                    required_version="1.0",
                    current_version="1.0",
                    status=DependencyStatus.SATISFIED,
                    install_instruction="",
                ),
                DependencyInfo(
                    name="B",
                    required_version="2.0",
                    current_version=None,
                    status=DependencyStatus.MISSING,
                    install_instruction="",
                ),
                DependencyInfo(
                    name="C",
                    required_version="3.0",
                    current_version="2.0",
                    status=DependencyStatus.VERSION_TOO_LOW,
                    install_instruction="",
                ),
            ]
        )
        missing = result.missing
        assert len(missing) == 2
        assert missing[0].name == "B"
        assert missing[1].name == "C"


class TestDependencyChecker:
    """Tests for DependencyChecker class."""

    def test_check_python_satisfied(self) -> None:
        """Test that Python check passes for current interpreter."""
        checker = DependencyChecker()
        result = checker.check_python()
        # Should always pass since we're running Python 3.10+
        assert result.status == DependencyStatus.SATISFIED
        assert result.current_version is not None

    def test_check_macos_with_mock(self) -> None:
        """Test macOS check with mocked sw_vers output."""
        checker = DependencyChecker()
        with patch.object(checker._runner, "run") as mock_run:
            # Mock sw_vers -productVersion
            mock_run.side_effect = [
                CommandResult(returncode=0, stdout="14.2\n", stderr=""),
                CommandResult(returncode=0, stdout="macOS\n", stderr=""),
            ]
            result = checker.check_macos()
            assert result.status == DependencyStatus.SATISFIED
            assert result.current_version == "14.2"

    def test_check_macos_version_too_low(self) -> None:
        """Test macOS check with old version."""
        checker = DependencyChecker()
        with patch.object(checker._runner, "run") as mock_run:
            mock_run.side_effect = [
                CommandResult(returncode=0, stdout="11.0\n", stderr=""),
                CommandResult(returncode=0, stdout="macOS\n", stderr=""),
            ]
            result = checker.check_macos()
            assert result.status == DependencyStatus.VERSION_TOO_LOW
            assert result.current_version == "11.0"

    def test_check_ffmpeg_with_mock(self) -> None:
        """Test FFmpeg check with mocked output."""
        checker = DependencyChecker()
        with (
            patch.object(checker._runner, "check_command_exists", return_value=True),
            patch.object(checker._runner, "run") as mock_run,
        ):
            mock_run.return_value = CommandResult(
                returncode=0,
                stdout="ffmpeg version 6.1 Copyright (c) 2000-2024",
                stderr="",
            )
            result = checker.check_ffmpeg()
            assert result.status == DependencyStatus.SATISFIED
            assert result.current_version == "6.1"

    def test_check_ffmpeg_missing(self) -> None:
        """Test FFmpeg check when not installed."""
        checker = DependencyChecker()
        with patch.object(checker._runner, "check_command_exists", return_value=False):
            result = checker.check_ffmpeg()
            assert result.status == DependencyStatus.MISSING
            assert "brew install ffmpeg" in result.install_instruction

    def test_check_ffmpeg_version_too_low(self) -> None:
        """Test FFmpeg check with old version."""
        checker = DependencyChecker()
        with (
            patch.object(checker._runner, "check_command_exists", return_value=True),
            patch.object(checker._runner, "run") as mock_run,
        ):
            mock_run.return_value = CommandResult(
                returncode=0,
                stdout="ffmpeg version 4.4 Copyright (c) 2000-2021",
                stderr="",
            )
            result = checker.check_ffmpeg()
            assert result.status == DependencyStatus.VERSION_TOO_LOW
            assert result.current_version == "4.4"

    def test_check_videotoolbox_available(self) -> None:
        """Test VideoToolbox check when available."""
        checker = DependencyChecker()
        with (
            patch.object(checker._runner, "check_command_exists", return_value=True),
            patch.object(checker._runner, "run") as mock_run,
        ):
            mock_run.return_value = CommandResult(
                returncode=0,
                stdout="V..... hevc_videotoolbox    VideoToolbox H.265 Encoder (codec hevc)",
                stderr="",
            )
            result = checker.check_videotoolbox()
            assert result.status == DependencyStatus.SATISFIED

    def test_check_videotoolbox_missing(self) -> None:
        """Test VideoToolbox check when not available."""
        checker = DependencyChecker()
        with (
            patch.object(checker._runner, "check_command_exists", return_value=True),
            patch.object(checker._runner, "run") as mock_run,
        ):
            mock_run.return_value = CommandResult(
                returncode=0,
                stdout="V..... libx265             libx265 H.265 / HEVC",
                stderr="",
            )
            result = checker.check_videotoolbox()
            assert result.status == DependencyStatus.MISSING

    def test_check_exiftool_with_mock(self) -> None:
        """Test ExifTool check with mocked output."""
        checker = DependencyChecker()
        with (
            patch.object(checker._runner, "check_command_exists", return_value=True),
            patch.object(checker._runner, "run") as mock_run,
        ):
            mock_run.return_value = CommandResult(
                returncode=0,
                stdout="12.70\n",
                stderr="",
            )
            result = checker.check_exiftool()
            assert result.status == DependencyStatus.SATISFIED
            assert result.current_version == "12.70"

    def test_check_exiftool_missing(self) -> None:
        """Test ExifTool check when not installed."""
        checker = DependencyChecker()
        with patch.object(checker._runner, "check_command_exists", return_value=False):
            result = checker.check_exiftool()
            assert result.status == DependencyStatus.MISSING
            assert "brew install exiftool" in result.install_instruction

    def test_check_osxphotos_missing(self) -> None:
        """Test osxphotos check when not installed."""
        checker = DependencyChecker()
        with (
            patch.dict("sys.modules", {"osxphotos": None}),
            patch("importlib.metadata.version") as mock_version,
        ):
            import importlib.metadata

            mock_version.side_effect = importlib.metadata.PackageNotFoundError()
            result = checker.check_osxphotos()
            assert result.status == DependencyStatus.MISSING

    def test_check_all(self) -> None:
        """Test check_all returns all dependency results."""
        checker = DependencyChecker()
        with patch.object(checker, "check_macos") as mock_macos, \
             patch.object(checker, "check_python") as mock_python, \
             patch.object(checker, "check_ffmpeg") as mock_ffmpeg, \
             patch.object(checker, "check_videotoolbox") as mock_vt, \
             patch.object(checker, "check_exiftool") as mock_exif, \
             patch.object(checker, "check_osxphotos") as mock_osx:

            mock_macos.return_value = DependencyInfo(
                name="macOS", required_version="12.0", current_version="14.0",
                status=DependencyStatus.SATISFIED, install_instruction=""
            )
            mock_python.return_value = DependencyInfo(
                name="Python", required_version="3.10", current_version="3.12",
                status=DependencyStatus.SATISFIED, install_instruction=""
            )
            mock_ffmpeg.return_value = DependencyInfo(
                name="FFmpeg", required_version="5.0", current_version="6.1",
                status=DependencyStatus.SATISFIED, install_instruction=""
            )
            mock_vt.return_value = DependencyInfo(
                name="VideoToolbox", required_version=None, current_version="available",
                status=DependencyStatus.SATISFIED, install_instruction=""
            )
            mock_exif.return_value = DependencyInfo(
                name="ExifTool", required_version="12.0", current_version="12.70",
                status=DependencyStatus.SATISFIED, install_instruction=""
            )
            mock_osx.return_value = DependencyInfo(
                name="osxphotos", required_version="0.70", current_version="0.74",
                status=DependencyStatus.SATISFIED, install_instruction=""
            )

            result = checker.check_all()
            assert len(result.dependencies) == 6
            assert result.all_satisfied is True


class TestFormatReport:
    """Tests for format_report method."""

    def test_format_all_satisfied(self) -> None:
        """Test report formatting when all dependencies are satisfied."""
        checker = DependencyChecker()
        result = DependencyCheckResult(
            dependencies=[
                DependencyInfo(
                    name="Python 3.12",
                    required_version="3.10",
                    current_version="3.12",
                    status=DependencyStatus.SATISFIED,
                    install_instruction="",
                ),
                DependencyInfo(
                    name="FFmpeg 6.1",
                    required_version="5.0",
                    current_version="6.1",
                    status=DependencyStatus.SATISFIED,
                    install_instruction="",
                ),
            ]
        )

        report = checker.format_report(result)
        assert "Checking dependencies..." in report
        assert "✓ Python 3.12" in report
        assert "✓ FFmpeg 6.1" in report
        assert "All dependencies satisfied!" in report

    def test_format_with_missing(self) -> None:
        """Test report formatting with missing dependencies."""
        checker = DependencyChecker()
        result = DependencyCheckResult(
            dependencies=[
                DependencyInfo(
                    name="Python 3.12",
                    required_version="3.10",
                    current_version="3.12",
                    status=DependencyStatus.SATISFIED,
                    install_instruction="",
                ),
                DependencyInfo(
                    name="FFmpeg",
                    required_version="5.0",
                    current_version=None,
                    status=DependencyStatus.MISSING,
                    install_instruction="brew install ffmpeg",
                ),
            ]
        )

        report = checker.format_report(result)
        assert "✓ Python 3.12" in report
        assert "✗ FFmpeg not found" in report
        assert "Missing or outdated dependencies:" in report
        assert "brew install ffmpeg" in report
