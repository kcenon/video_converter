"""Metadata processing module for video files.

This module provides ExifTool integration for extracting and applying metadata
on video files. It handles GPS coordinates, creation dates, camera information,
and other critical metadata tags.

SDS Reference: SDS-P01-002
SRS Reference: SRS-401 (Metadata Preservation)

Example:
    >>> from video_converter.utils.command_runner import CommandRunner
    >>> runner = CommandRunner()
    >>> processor = MetadataProcessor(runner)
    >>> metadata = processor.extract(Path("video.mp4"))
    >>> print(metadata.get("QuickTime:CreateDate"))

    >>> # Copy all metadata
    >>> processor.copy_all(source_path, dest_path)

    >>> # Verify critical tags
    >>> results = processor.verify_critical_tags(original, converted)
    >>> for tag, matched in results.items():
    ...     print(f"{tag}: {'OK' if matched else 'MISMATCH'}")
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from video_converter.utils.command_runner import (
    CommandRunner,
    CommandExecutionError,
    CommandNotFoundError,
)


class MetadataExtractionError(Exception):
    """Raised when metadata extraction fails."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to extract metadata from {path}: {reason}")


class MetadataApplicationError(Exception):
    """Raised when metadata application fails."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to apply metadata to {path}: {reason}")


@dataclass
class GPSCoordinates:
    """GPS coordinate data.

    Attributes:
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.
        altitude: Altitude in meters (optional).
    """

    latitude: float
    longitude: float
    altitude: float | None = None

    def __str__(self) -> str:
        """Return human-readable coordinate string."""
        lat_dir = "N" if self.latitude >= 0 else "S"
        lon_dir = "E" if self.longitude >= 0 else "W"
        result = f"{abs(self.latitude):.6f}°{lat_dir}, {abs(self.longitude):.6f}°{lon_dir}"
        if self.altitude is not None:
            result += f", {self.altitude:.1f}m"
        return result


@dataclass
class MetadataVerificationResult:
    """Result of metadata verification between two files.

    Attributes:
        all_matched: True if all critical tags matched.
        tag_results: Dictionary mapping tag names to match status.
        missing_in_source: Tags present in source but missing in destination.
        missing_in_dest: Tags missing in destination that were in source.
    """

    all_matched: bool
    tag_results: dict[str, bool] = field(default_factory=dict)
    missing_in_source: list[str] = field(default_factory=list)
    missing_in_dest: list[str] = field(default_factory=list)


class MetadataProcessor:
    """Handle video metadata extraction and application using ExifTool.

    This class provides methods to extract metadata from video files,
    copy metadata between files, and verify that critical metadata
    was preserved during conversion.

    Attributes:
        EXIFTOOL_CMD: The exiftool command name.
        CRITICAL_TAGS: List of metadata tags that must be preserved.
        GPS_TAGS: Tags related to GPS/location data.
        DATE_TAGS: Tags related to dates and times.

    Example:
        >>> runner = CommandRunner()
        >>> processor = MetadataProcessor(runner)
        >>> metadata = processor.extract(Path("video.mp4"))
        >>> gps = processor.extract_gps(Path("video.mp4"))
        >>> if gps:
        ...     print(f"Location: {gps}")
    """

    EXIFTOOL_CMD = "exiftool"

    CRITICAL_TAGS = [
        "CreateDate",
        "ModifyDate",
        "GPSLatitude",
        "GPSLongitude",
        "GPSAltitude",
        "GPSCoordinates",
        "Make",
        "Model",
        "Duration",
        "Rotation",
    ]

    GPS_TAGS = [
        "GPSLatitude",
        "GPSLongitude",
        "GPSAltitude",
        "GPSLatitudeRef",
        "GPSLongitudeRef",
        "GPSAltitudeRef",
        "GPSCoordinates",
        "GPSPosition",
    ]

    DATE_TAGS = [
        "CreateDate",
        "ModifyDate",
        "DateTimeOriginal",
        "MediaCreateDate",
        "MediaModifyDate",
        "TrackCreateDate",
        "TrackModifyDate",
    ]

    def __init__(self, command_runner: CommandRunner | None = None) -> None:
        """Initialize MetadataProcessor.

        Args:
            command_runner: CommandRunner instance to use. If None, creates a new one.
        """
        self._runner = command_runner or CommandRunner()

    def is_available(self) -> bool:
        """Check if ExifTool is available.

        Returns:
            True if exiftool command is available.
        """
        return self._runner.check_command_exists(self.EXIFTOOL_CMD)

    def ensure_available(self) -> None:
        """Ensure ExifTool is available, raising error if not.

        Raises:
            CommandNotFoundError: If exiftool is not installed.
        """
        self._runner.ensure_command_exists(self.EXIFTOOL_CMD)

    def extract(self, path: Path, *, include_binary: bool = False) -> dict[str, Any]:
        """Extract all metadata from a video file.

        Args:
            path: Path to the video file.
            include_binary: Include binary data in output (default: False).

        Returns:
            Dictionary of metadata tags and values.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            MetadataExtractionError: If extraction fails.
            CommandNotFoundError: If exiftool is not installed.
        """
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        args = [
            self.EXIFTOOL_CMD,
            "-json",
            "-G",  # Show group names
            "-a",  # Allow duplicate tags
            "-u",  # Show unknown tags
            "-n",  # Numeric output (no formatting)
        ]

        if not include_binary:
            args.append("-b")
            # Actually -b includes binary, we want to exclude
            # Use -X for XMP or just don't include -b
            args.remove("-b")

        args.append(str(path))

        try:
            result = self._runner.run(args, timeout=30.0)
            if not result.success:
                raise MetadataExtractionError(path, result.stderr)

            data = json.loads(result.stdout)
            return data[0] if data else {}

        except json.JSONDecodeError as e:
            raise MetadataExtractionError(path, f"Invalid JSON output: {e}") from e
        except CommandExecutionError as e:
            raise MetadataExtractionError(path, str(e)) from e

    def extract_gps(self, path: Path) -> GPSCoordinates | None:
        """Extract GPS coordinates from a video file.

        Args:
            path: Path to the video file.

        Returns:
            GPSCoordinates if found, None otherwise.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            MetadataExtractionError: If extraction fails.
        """
        metadata = self.extract(path)

        # Try different GPS tag formats
        lat = self._find_tag_value(metadata, "GPSLatitude")
        lon = self._find_tag_value(metadata, "GPSLongitude")

        if lat is None or lon is None:
            # Try Composite:GPSPosition format
            gps_pos = self._find_tag_value(metadata, "GPSPosition")
            if gps_pos and isinstance(gps_pos, str):
                coords = self._parse_gps_position(gps_pos)
                if coords:
                    lat, lon = coords

        if lat is not None and lon is not None:
            try:
                lat_float = self._convert_gps_to_decimal(lat, metadata, "Latitude")
                lon_float = self._convert_gps_to_decimal(lon, metadata, "Longitude")

                alt = self._find_tag_value(metadata, "GPSAltitude")
                alt_float = float(alt) if alt is not None else None

                return GPSCoordinates(
                    latitude=lat_float,
                    longitude=lon_float,
                    altitude=alt_float,
                )
            except (ValueError, TypeError):
                return None

        return None

    def copy_all(
        self,
        source: Path,
        dest: Path,
        *,
        overwrite_original: bool = True,
    ) -> bool:
        """Copy all metadata from source to destination file.

        Args:
            source: Source file with metadata.
            dest: Destination file to receive metadata.
            overwrite_original: If True, modify dest in place without backup.

        Returns:
            True if metadata was copied successfully.

        Raises:
            FileNotFoundError: If source or dest doesn't exist.
            MetadataApplicationError: If copying fails.
        """
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")
        if not dest.exists():
            raise FileNotFoundError(f"Destination file not found: {dest}")

        args = [self.EXIFTOOL_CMD]

        if overwrite_original:
            args.append("-overwrite_original")

        args.extend([
            "-tagsFromFile",
            str(source),
            "-all:all",
            str(dest),
        ])

        try:
            result = self._runner.run(args, timeout=60.0)
            return result.success
        except CommandExecutionError as e:
            raise MetadataApplicationError(dest, str(e)) from e

    def copy_tags(
        self,
        source: Path,
        dest: Path,
        tags: list[str],
        *,
        overwrite_original: bool = True,
    ) -> bool:
        """Copy specific metadata tags from source to destination.

        Args:
            source: Source file with metadata.
            dest: Destination file to receive metadata.
            tags: List of tag patterns (e.g., ["GPS*", "CreateDate"]).
            overwrite_original: If True, modify dest in place.

        Returns:
            True if tags were copied successfully.

        Raises:
            FileNotFoundError: If source or dest doesn't exist.
            MetadataApplicationError: If copying fails.
        """
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")
        if not dest.exists():
            raise FileNotFoundError(f"Destination file not found: {dest}")
        if not tags:
            return True  # Nothing to copy

        args = [self.EXIFTOOL_CMD]

        if overwrite_original:
            args.append("-overwrite_original")

        args.extend(["-tagsFromFile", str(source)])

        for tag in tags:
            args.append(f"-{tag}")

        args.append(str(dest))

        try:
            result = self._runner.run(args, timeout=60.0)
            return result.success
        except CommandExecutionError as e:
            raise MetadataApplicationError(dest, str(e)) from e

    def copy_gps(
        self,
        source: Path,
        dest: Path,
        *,
        overwrite_original: bool = True,
    ) -> bool:
        """Copy GPS metadata from source to destination.

        This is a convenience method that copies all GPS-related tags.

        Args:
            source: Source file with GPS data.
            dest: Destination file.
            overwrite_original: If True, modify dest in place.

        Returns:
            True if GPS data was copied successfully.
        """
        return self.copy_tags(
            source,
            dest,
            ["GPS*", "GPSCoordinates", "GPSPosition"],
            overwrite_original=overwrite_original,
        )

    def copy_dates(
        self,
        source: Path,
        dest: Path,
        *,
        overwrite_original: bool = True,
    ) -> bool:
        """Copy date/time metadata from source to destination.

        Args:
            source: Source file with date metadata.
            dest: Destination file.
            overwrite_original: If True, modify dest in place.

        Returns:
            True if dates were copied successfully.
        """
        return self.copy_tags(
            source,
            dest,
            self.DATE_TAGS,
            overwrite_original=overwrite_original,
        )

    def verify_critical_tags(
        self,
        original: Path,
        converted: Path,
    ) -> MetadataVerificationResult:
        """Verify that critical metadata was preserved during conversion.

        Args:
            original: Original source file.
            converted: Converted output file.

        Returns:
            MetadataVerificationResult with comparison details.

        Raises:
            FileNotFoundError: If either file doesn't exist.
            MetadataExtractionError: If metadata extraction fails.
        """
        orig_meta = self.extract(original)
        conv_meta = self.extract(converted)

        tag_results: dict[str, bool] = {}
        missing_in_source: list[str] = []
        missing_in_dest: list[str] = []

        for tag in self.CRITICAL_TAGS:
            orig_value = self._find_tag_value(orig_meta, tag)
            conv_value = self._find_tag_value(conv_meta, tag)

            if orig_value is None:
                missing_in_source.append(tag)
                continue

            if conv_value is None:
                missing_in_dest.append(tag)
                tag_results[tag] = False
            else:
                tag_results[tag] = self._values_match(orig_value, conv_value)

        all_matched = all(tag_results.values()) if tag_results else True

        return MetadataVerificationResult(
            all_matched=all_matched,
            tag_results=tag_results,
            missing_in_source=missing_in_source,
            missing_in_dest=missing_in_dest,
        )

    def set_tag(
        self,
        path: Path,
        tag: str,
        value: str,
        *,
        overwrite_original: bool = True,
    ) -> bool:
        """Set a single metadata tag on a file.

        Args:
            path: Path to the file.
            tag: Tag name to set.
            value: Value to set.
            overwrite_original: If True, modify file in place.

        Returns:
            True if the tag was set successfully.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            MetadataApplicationError: If setting fails.
        """
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        args = [self.EXIFTOOL_CMD]

        if overwrite_original:
            args.append("-overwrite_original")

        # Escape special characters in value
        escaped_value = self._escape_value(value)
        args.append(f"-{tag}={escaped_value}")
        args.append(str(path))

        try:
            result = self._runner.run(args, timeout=30.0)
            return result.success
        except CommandExecutionError as e:
            raise MetadataApplicationError(path, str(e)) from e

    def batch_copy_all(
        self,
        source_dest_pairs: list[tuple[Path, Path]],
        *,
        overwrite_original: bool = True,
    ) -> dict[Path, bool]:
        """Copy metadata for multiple file pairs.

        Args:
            source_dest_pairs: List of (source, dest) path tuples.
            overwrite_original: If True, modify dest files in place.

        Returns:
            Dictionary mapping destination paths to success status.
        """
        results: dict[Path, bool] = {}

        for source, dest in source_dest_pairs:
            try:
                success = self.copy_all(
                    source, dest, overwrite_original=overwrite_original
                )
                results[dest] = success
            except (FileNotFoundError, MetadataApplicationError):
                results[dest] = False

        return results

    def _find_tag_value(self, metadata: dict[str, Any], tag: str) -> Any:
        """Find a tag value in metadata dict, handling group prefixes.

        Args:
            metadata: Metadata dictionary.
            tag: Tag name to find (may or may not have group prefix).

        Returns:
            Tag value if found, None otherwise.
        """
        # Direct match
        if tag in metadata:
            return metadata[tag]

        # Match with any group prefix
        for key, value in metadata.items():
            if key.endswith(f":{tag}") or key == tag:
                return value
            # Also check without group prefix in key
            if ":" in key and key.split(":")[-1] == tag:
                return value

        return None

    def _values_match(self, val1: Any, val2: Any) -> bool:
        """Compare two metadata values for equality.

        Handles numeric comparisons with tolerance and string normalization.

        Args:
            val1: First value.
            val2: Second value.

        Returns:
            True if values are considered equal.
        """
        if val1 is None or val2 is None:
            return val1 == val2

        # Both numeric
        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            # Allow small tolerance for floating point
            if isinstance(val1, float) or isinstance(val2, float):
                return abs(float(val1) - float(val2)) < 0.0001
            return val1 == val2

        # Convert to strings and compare
        str1 = str(val1).strip().lower()
        str2 = str(val2).strip().lower()

        return str1 == str2

    def _escape_value(self, value: str) -> str:
        """Escape special characters in metadata value.

        Args:
            value: Value to escape.

        Returns:
            Escaped value safe for command line.
        """
        # ExifTool handles most escaping, but we need to handle newlines
        return value.replace("\n", "\\n").replace("\r", "")

    def _convert_gps_to_decimal(
        self,
        value: Any,
        metadata: dict[str, Any],
        coord_type: str,
    ) -> float:
        """Convert GPS coordinate to decimal degrees.

        Args:
            value: GPS value (may be string or numeric).
            metadata: Full metadata dict (for reference direction).
            coord_type: "Latitude" or "Longitude".

        Returns:
            Coordinate in decimal degrees.
        """
        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            # Parse DMS format: "37 deg 46' 30.00\" N"
            match = re.match(
                r"(\d+)\s*deg\s*(\d+)['\u2019]\s*([\d.]+)[\"″]?\s*([NSEW])?",
                value,
                re.IGNORECASE,
            )
            if match:
                degrees = float(match.group(1))
                minutes = float(match.group(2))
                seconds = float(match.group(3))
                direction = match.group(4)

                decimal = degrees + minutes / 60 + seconds / 3600

                if direction and direction.upper() in ("S", "W"):
                    decimal = -decimal

                return decimal

            # Try simple float conversion
            try:
                return float(value)
            except ValueError:
                pass

        raise ValueError(f"Cannot parse GPS value: {value}")

    def _parse_gps_position(self, position: str) -> tuple[float, float] | None:
        """Parse GPS position string.

        Args:
            position: Position string like "37.7749 N, 122.4194 W".

        Returns:
            Tuple of (latitude, longitude) or None if parse fails.
        """
        # Format: "lat lon" or "lat, lon"
        parts = re.split(r"[,\s]+", position.strip())

        if len(parts) >= 2:
            try:
                lat = float(parts[0])
                lon = float(parts[1])
                return (lat, lon)
            except ValueError:
                pass

        return None
