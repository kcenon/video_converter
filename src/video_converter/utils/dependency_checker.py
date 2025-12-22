"""Dependency checker for required external tools.

This module validates that all required external tools are installed
and provides installation instructions for missing dependencies.

SDS Reference: SDS-U01-002
"""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass, field
from enum import Enum

from video_converter.utils.command_runner import CommandRunner

logger = logging.getLogger(__name__)


class DependencyStatus(Enum):
    """Status of a dependency check."""

    SATISFIED = "satisfied"
    MISSING = "missing"
    VERSION_TOO_LOW = "version_too_low"
    CHECK_FAILED = "check_failed"


@dataclass
class DependencyInfo:
    """Information about a single dependency.

    Attributes:
        name: Name of the dependency.
        required_version: Minimum required version (None if any version is OK).
        current_version: Currently installed version (None if not found).
        status: Status of the dependency check.
        install_instruction: How to install this dependency.
        description: Brief description of what this dependency is for.
    """

    name: str
    required_version: str | None
    current_version: str | None
    status: DependencyStatus
    install_instruction: str
    description: str = ""

    @property
    def is_satisfied(self) -> bool:
        """Check if dependency is satisfied."""
        return self.status == DependencyStatus.SATISFIED


@dataclass
class DependencyCheckResult:
    """Result of checking all dependencies.

    Attributes:
        dependencies: List of all checked dependencies.
        all_satisfied: Whether all dependencies are satisfied.
    """

    dependencies: list[DependencyInfo] = field(default_factory=list)

    @property
    def all_satisfied(self) -> bool:
        """Check if all dependencies are satisfied."""
        return all(dep.is_satisfied for dep in self.dependencies)

    @property
    def missing(self) -> list[DependencyInfo]:
        """Get list of missing or unsatisfied dependencies."""
        return [dep for dep in self.dependencies if not dep.is_satisfied]

    @property
    def satisfied(self) -> list[DependencyInfo]:
        """Get list of satisfied dependencies."""
        return [dep for dep in self.dependencies if dep.is_satisfied]


def compare_versions(version1: str, version2: str) -> int:
    """Compare two version strings.

    Supports semantic versioning (e.g., "5.0", "5.1.2", "6.0-beta").

    Args:
        version1: First version string.
        version2: Second version string.

    Returns:
        -1 if version1 < version2
        0 if version1 == version2
        1 if version1 > version2

    Example:
        >>> compare_versions("5.0", "5.1")
        -1
        >>> compare_versions("6.0", "5.1")
        1
        >>> compare_versions("5.1", "5.1")
        0
    """

    def normalize(v: str) -> list[int]:
        """Normalize version string to list of integers."""
        # Remove any suffix like -beta, -rc1, etc.
        v = re.split(r"[-_]", v)[0]
        # Split by dots and convert to integers
        parts = []
        for part in v.split("."):
            # Extract leading digits
            match = re.match(r"(\d+)", part)
            if match:
                parts.append(int(match.group(1)))
        return parts

    v1_parts = normalize(version1)
    v2_parts = normalize(version2)

    # Pad shorter version with zeros
    max_len = max(len(v1_parts), len(v2_parts))
    v1_parts.extend([0] * (max_len - len(v1_parts)))
    v2_parts.extend([0] * (max_len - len(v2_parts)))

    for p1, p2 in zip(v1_parts, v2_parts, strict=True):
        if p1 < p2:
            return -1
        if p1 > p2:
            return 1

    return 0


class DependencyChecker:
    """Check for required external dependencies.

    This class validates that all required tools are installed and
    provides installation instructions for missing dependencies.

    Example:
        >>> checker = DependencyChecker()
        >>> result = checker.check_all()
        >>> if not result.all_satisfied:
        ...     for dep in result.missing:
        ...         print(f"Missing: {dep.name}")
        ...         print(f"Install: {dep.install_instruction}")
    """

    # Minimum required versions
    MIN_MACOS_VERSION = "12.0"  # Monterey
    MIN_PYTHON_VERSION = "3.10"
    MIN_FFMPEG_VERSION = "5.0"
    MIN_EXIFTOOL_VERSION = "12.0"
    MIN_OSXPHOTOS_VERSION = "0.70"

    def __init__(self, command_runner: CommandRunner | None = None) -> None:
        """Initialize dependency checker.

        Args:
            command_runner: CommandRunner instance to use. If None, creates a new one.
        """
        self._runner = command_runner or CommandRunner()

    def check_all(self) -> DependencyCheckResult:
        """Check all dependencies.

        Returns:
            DependencyCheckResult containing status of all dependencies.
        """
        result = DependencyCheckResult()

        # Check each dependency
        result.dependencies.append(self.check_macos())
        result.dependencies.append(self.check_python())
        result.dependencies.append(self.check_ffmpeg())
        result.dependencies.append(self.check_videotoolbox())
        result.dependencies.append(self.check_exiftool())
        result.dependencies.append(self.check_osxphotos())

        return result

    def check_macos(self) -> DependencyInfo:
        """Check macOS version.

        Returns:
            DependencyInfo for macOS.
        """
        name = "macOS"
        install_instruction = "Upgrade macOS to version 12.0 (Monterey) or later"
        description = "Operating system"

        try:
            # Get macOS version using sw_vers
            result = self._runner.run(["sw_vers", "-productVersion"], timeout=5.0)
            if not result.success:
                return DependencyInfo(
                    name=name,
                    required_version=self.MIN_MACOS_VERSION,
                    current_version=None,
                    status=DependencyStatus.CHECK_FAILED,
                    install_instruction=install_instruction,
                    description=description,
                )

            version = result.stdout.strip()
            logger.debug("Detected macOS version: %s", version)

            # Get macOS name
            name_result = self._runner.run(
                ["sw_vers", "-productName"], timeout=5.0
            )
            product_name = name_result.stdout.strip() if name_result.success else "macOS"

            if compare_versions(version, self.MIN_MACOS_VERSION) >= 0:
                return DependencyInfo(
                    name=f"{product_name} {version}",
                    required_version=self.MIN_MACOS_VERSION,
                    current_version=version,
                    status=DependencyStatus.SATISFIED,
                    install_instruction=install_instruction,
                    description=description,
                )
            else:
                return DependencyInfo(
                    name=name,
                    required_version=self.MIN_MACOS_VERSION,
                    current_version=version,
                    status=DependencyStatus.VERSION_TOO_LOW,
                    install_instruction=install_instruction,
                    description=description,
                )

        except Exception as e:
            logger.warning("Failed to check macOS version: %s", e)
            return DependencyInfo(
                name=name,
                required_version=self.MIN_MACOS_VERSION,
                current_version=None,
                status=DependencyStatus.CHECK_FAILED,
                install_instruction=install_instruction,
                description=description,
            )

    def check_python(self) -> DependencyInfo:
        """Check Python version.

        Returns:
            DependencyInfo for Python.
        """
        name = "Python"
        install_instruction = "Install Python 3.10+ from python.org or brew install python@3.10"
        description = "Python interpreter"

        version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        version_short = f"{sys.version_info.major}.{sys.version_info.minor}"

        if compare_versions(version_short, self.MIN_PYTHON_VERSION) >= 0:
            return DependencyInfo(
                name=f"Python {version}",
                required_version=self.MIN_PYTHON_VERSION,
                current_version=version,
                status=DependencyStatus.SATISFIED,
                install_instruction=install_instruction,
                description=description,
            )
        else:
            return DependencyInfo(
                name=name,
                required_version=self.MIN_PYTHON_VERSION,
                current_version=version,
                status=DependencyStatus.VERSION_TOO_LOW,
                install_instruction=install_instruction,
                description=description,
            )

    def check_ffmpeg(self) -> DependencyInfo:
        """Check FFmpeg installation and version.

        Returns:
            DependencyInfo for FFmpeg.
        """
        name = "FFmpeg"
        install_instruction = "brew install ffmpeg"
        description = "Video processing tool"

        try:
            if not self._runner.check_command_exists("ffmpeg"):
                return DependencyInfo(
                    name=name,
                    required_version=self.MIN_FFMPEG_VERSION,
                    current_version=None,
                    status=DependencyStatus.MISSING,
                    install_instruction=install_instruction,
                    description=description,
                )

            # Get FFmpeg version
            result = self._runner.run(["ffmpeg", "-version"], timeout=5.0)
            if not result.success:
                return DependencyInfo(
                    name=name,
                    required_version=self.MIN_FFMPEG_VERSION,
                    current_version=None,
                    status=DependencyStatus.CHECK_FAILED,
                    install_instruction=install_instruction,
                    description=description,
                )

            # Parse version from output: "ffmpeg version 6.1 Copyright..."
            version_match = re.search(r"ffmpeg version (\d+\.\d+(?:\.\d+)?)", result.stdout)
            if not version_match:
                # Try alternative format: "ffmpeg version N-xxxxx-..."
                version_match = re.search(r"ffmpeg version (\d+)", result.stdout)

            if version_match:
                version = version_match.group(1)
                logger.debug("Detected FFmpeg version: %s", version)

                if compare_versions(version, self.MIN_FFMPEG_VERSION) >= 0:
                    return DependencyInfo(
                        name=f"FFmpeg {version}",
                        required_version=self.MIN_FFMPEG_VERSION,
                        current_version=version,
                        status=DependencyStatus.SATISFIED,
                        install_instruction=install_instruction,
                        description=description,
                    )
                else:
                    return DependencyInfo(
                        name=name,
                        required_version=self.MIN_FFMPEG_VERSION,
                        current_version=version,
                        status=DependencyStatus.VERSION_TOO_LOW,
                        install_instruction="brew upgrade ffmpeg",
                        description=description,
                    )
            else:
                return DependencyInfo(
                    name=name,
                    required_version=self.MIN_FFMPEG_VERSION,
                    current_version="unknown",
                    status=DependencyStatus.SATISFIED,  # Assume OK if we can't parse
                    install_instruction=install_instruction,
                    description=description,
                )

        except Exception as e:
            logger.warning("Failed to check FFmpeg: %s", e)
            return DependencyInfo(
                name=name,
                required_version=self.MIN_FFMPEG_VERSION,
                current_version=None,
                status=DependencyStatus.CHECK_FAILED,
                install_instruction=install_instruction,
                description=description,
            )

    def check_videotoolbox(self) -> DependencyInfo:
        """Check VideoToolbox/hevc_videotoolbox encoder availability.

        Returns:
            DependencyInfo for VideoToolbox encoder.
        """
        name = "hevc_videotoolbox"
        install_instruction = "brew reinstall ffmpeg (ensure VideoToolbox is enabled)"
        description = "Hardware H.265 encoder"

        try:
            if not self._runner.check_command_exists("ffmpeg"):
                return DependencyInfo(
                    name=name,
                    required_version=None,
                    current_version=None,
                    status=DependencyStatus.MISSING,
                    install_instruction="Install FFmpeg first: brew install ffmpeg",
                    description=description,
                )

            # Check if hevc_videotoolbox encoder is available
            result = self._runner.run(["ffmpeg", "-encoders"], timeout=5.0)
            if not result.success:
                return DependencyInfo(
                    name=name,
                    required_version=None,
                    current_version=None,
                    status=DependencyStatus.CHECK_FAILED,
                    install_instruction=install_instruction,
                    description=description,
                )

            if "hevc_videotoolbox" in result.stdout:
                return DependencyInfo(
                    name=name,
                    required_version=None,
                    current_version="available",
                    status=DependencyStatus.SATISFIED,
                    install_instruction=install_instruction,
                    description=description,
                )
            else:
                return DependencyInfo(
                    name=name,
                    required_version=None,
                    current_version=None,
                    status=DependencyStatus.MISSING,
                    install_instruction=install_instruction,
                    description=description,
                )

        except Exception as e:
            logger.warning("Failed to check VideoToolbox: %s", e)
            return DependencyInfo(
                name=name,
                required_version=None,
                current_version=None,
                status=DependencyStatus.CHECK_FAILED,
                install_instruction=install_instruction,
                description=description,
            )

    def check_exiftool(self) -> DependencyInfo:
        """Check ExifTool installation and version.

        Returns:
            DependencyInfo for ExifTool.
        """
        name = "ExifTool"
        install_instruction = "brew install exiftool"
        description = "Metadata extraction tool"

        try:
            if not self._runner.check_command_exists("exiftool"):
                return DependencyInfo(
                    name=name,
                    required_version=self.MIN_EXIFTOOL_VERSION,
                    current_version=None,
                    status=DependencyStatus.MISSING,
                    install_instruction=install_instruction,
                    description=description,
                )

            # Get ExifTool version
            result = self._runner.run(["exiftool", "-ver"], timeout=5.0)
            if not result.success:
                return DependencyInfo(
                    name=name,
                    required_version=self.MIN_EXIFTOOL_VERSION,
                    current_version=None,
                    status=DependencyStatus.CHECK_FAILED,
                    install_instruction=install_instruction,
                    description=description,
                )

            version = result.stdout.strip()
            logger.debug("Detected ExifTool version: %s", version)

            if compare_versions(version, self.MIN_EXIFTOOL_VERSION) >= 0:
                return DependencyInfo(
                    name=f"ExifTool {version}",
                    required_version=self.MIN_EXIFTOOL_VERSION,
                    current_version=version,
                    status=DependencyStatus.SATISFIED,
                    install_instruction=install_instruction,
                    description=description,
                )
            else:
                return DependencyInfo(
                    name=name,
                    required_version=self.MIN_EXIFTOOL_VERSION,
                    current_version=version,
                    status=DependencyStatus.VERSION_TOO_LOW,
                    install_instruction="brew upgrade exiftool",
                    description=description,
                )

        except Exception as e:
            logger.warning("Failed to check ExifTool: %s", e)
            return DependencyInfo(
                name=name,
                required_version=self.MIN_EXIFTOOL_VERSION,
                current_version=None,
                status=DependencyStatus.CHECK_FAILED,
                install_instruction=install_instruction,
                description=description,
            )

    def check_osxphotos(self) -> DependencyInfo:
        """Check osxphotos package installation.

        Returns:
            DependencyInfo for osxphotos.
        """
        name = "osxphotos"
        install_instruction = "pip install osxphotos>=0.70"
        description = "macOS Photos library access"

        try:
            import importlib.metadata

            version = importlib.metadata.version("osxphotos")
            logger.debug("Detected osxphotos version: %s", version)

            if compare_versions(version, self.MIN_OSXPHOTOS_VERSION) >= 0:
                return DependencyInfo(
                    name=f"osxphotos {version}",
                    required_version=self.MIN_OSXPHOTOS_VERSION,
                    current_version=version,
                    status=DependencyStatus.SATISFIED,
                    install_instruction=install_instruction,
                    description=description,
                )
            else:
                return DependencyInfo(
                    name=name,
                    required_version=self.MIN_OSXPHOTOS_VERSION,
                    current_version=version,
                    status=DependencyStatus.VERSION_TOO_LOW,
                    install_instruction="pip install --upgrade osxphotos",
                    description=description,
                )

        except importlib.metadata.PackageNotFoundError:
            return DependencyInfo(
                name=name,
                required_version=self.MIN_OSXPHOTOS_VERSION,
                current_version=None,
                status=DependencyStatus.MISSING,
                install_instruction=install_instruction,
                description=description,
            )
        except Exception as e:
            logger.warning("Failed to check osxphotos: %s", e)
            return DependencyInfo(
                name=name,
                required_version=self.MIN_OSXPHOTOS_VERSION,
                current_version=None,
                status=DependencyStatus.CHECK_FAILED,
                install_instruction=install_instruction,
                description=description,
            )

    def format_report(self, result: DependencyCheckResult) -> str:
        """Format dependency check result as a readable report.

        Args:
            result: The dependency check result.

        Returns:
            Formatted string report.
        """
        lines = ["Checking dependencies...", ""]

        for dep in result.dependencies:
            if dep.is_satisfied:
                status_icon = "✓"
                lines.append(f"{status_icon} {dep.name}")
            else:
                status_icon = "✗"
                if dep.status == DependencyStatus.MISSING:
                    lines.append(f"{status_icon} {dep.name} not found")
                elif dep.status == DependencyStatus.VERSION_TOO_LOW:
                    lines.append(
                        f"{status_icon} {dep.name} {dep.current_version} "
                        f"(requires {dep.required_version}+)"
                    )
                else:
                    lines.append(f"{status_icon} {dep.name} (check failed)")

        lines.append("")

        if result.all_satisfied:
            lines.append("All dependencies satisfied!")
        else:
            lines.append("Missing or outdated dependencies:")
            for dep in result.missing:
                lines.append(f"  {dep.name}: {dep.install_instruction}")
            lines.append("")
            lines.append("Please install missing dependencies and try again.")

        return "\n".join(lines)


__all__ = [
    "DependencyStatus",
    "DependencyInfo",
    "DependencyCheckResult",
    "DependencyChecker",
    "compare_versions",
]
