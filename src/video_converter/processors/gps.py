"""GPS coordinate handling for video metadata.

This module provides specialized handling for GPS coordinate preservation
during video conversion. It ensures location data is accurately maintained
across different metadata container formats.

SDS Reference: SDS-P01-003
SRS Reference: SRS-402 (GPS Preservation)

Example:
    >>> from video_converter.utils.command_runner import CommandRunner
    >>> from video_converter.processors.gps import GPSHandler
    >>> handler = GPSHandler(CommandRunner())
    >>> coords = handler.extract(Path("video.mp4"))
    >>> if coords:
    ...     print(f"Location: {coords}")
    ...     print(f"QuickTime format: {coords.to_quicktime()}")

    >>> # Verify GPS was preserved
    >>> result = handler.verify(original_path, converted_path)
    >>> if result.passed:
    ...     print("GPS preserved successfully")
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from video_converter.processors.metadata import (
    MetadataExtractionError,
    MetadataProcessor,
)


class GPSFormat(Enum):
    """GPS coordinate storage formats.

    Different metadata containers store GPS data in different formats.
    This enum identifies the source format for proper handling.
    """

    QUICKTIME = "quicktime"  # +37.7749-122.4194/
    XMP = "xmp"  # 37.7749 N, 122.4194 W
    EXIF = "exif"  # 37 deg 46' 30.00" N
    KEYS = "keys"  # Composite string
    DECIMAL = "decimal"  # Simple decimal degrees


@dataclass
class GPSCoordinates:
    """GPS coordinate data with format conversion support.

    This class represents GPS coordinates with support for converting
    between different metadata container formats. It preserves accuracy
    to 6 decimal places (~0.1 meter precision).

    Attributes:
        latitude: Latitude in decimal degrees (-90 to 90).
        longitude: Longitude in decimal degrees (-180 to 180).
        altitude: Altitude in meters (optional).
        accuracy: Horizontal accuracy in meters (optional).
        source_format: Original format the coordinates were parsed from.

    Example:
        >>> coords = GPSCoordinates(
        ...     latitude=37.7749,
        ...     longitude=-122.4194,
        ...     altitude=10.5
        ... )
        >>> print(coords.to_quicktime())
        +37.774900-122.419400/
    """

    latitude: float
    longitude: float
    altitude: float | None = None
    accuracy: float | None = None
    source_format: GPSFormat = GPSFormat.DECIMAL

    # Precision for coordinate storage (6 decimal places = ~0.1m)
    PRECISION = 6
    # Tolerance for GPS verification (in decimal degrees)
    # 0.000001 degrees ≈ 0.1 meters
    TOLERANCE = 0.000001

    def __post_init__(self) -> None:
        """Validate and normalize coordinates."""
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"Latitude must be between -90 and 90: {self.latitude}")
        if not -180 <= self.longitude <= 180:
            raise ValueError(
                f"Longitude must be between -180 and 180: {self.longitude}"
            )

    def __str__(self) -> str:
        """Return human-readable coordinate string."""
        lat_dir = "N" if self.latitude >= 0 else "S"
        lon_dir = "E" if self.longitude >= 0 else "W"
        result = (
            f"{abs(self.latitude):.{self.PRECISION}f}°{lat_dir}, "
            f"{abs(self.longitude):.{self.PRECISION}f}°{lon_dir}"
        )
        if self.altitude is not None:
            result += f", {self.altitude:.1f}m"
        if self.accuracy is not None:
            result += f" (±{self.accuracy:.1f}m)"
        return result

    def to_quicktime(self) -> str:
        """Convert to QuickTime GPS format.

        QuickTime uses ISO 6709 format: +DD.DDDDDD-DDD.DDDDDD/

        Returns:
            GPS string in QuickTime format.

        Example:
            >>> coords = GPSCoordinates(37.7749, -122.4194)
            >>> coords.to_quicktime()
            '+37.774900-122.419400/'
        """
        lat_sign = "+" if self.latitude >= 0 else ""
        lon_sign = "+" if self.longitude >= 0 else ""
        result = (
            f"{lat_sign}{self.latitude:.{self.PRECISION}f}"
            f"{lon_sign}{self.longitude:.{self.PRECISION}f}"
        )
        if self.altitude is not None:
            alt_sign = "+" if self.altitude >= 0 else ""
            result += f"{alt_sign}{self.altitude:.2f}"
        return result + "/"

    def to_xmp(self) -> tuple[str, str]:
        """Convert to XMP GPS format.

        XMP uses "DD.DDDDDD,D" format with direction suffix.

        Returns:
            Tuple of (latitude_string, longitude_string).

        Example:
            >>> coords = GPSCoordinates(37.7749, -122.4194)
            >>> coords.to_xmp()
            ('37.774900 N', '122.419400 W')
        """
        lat_dir = "N" if self.latitude >= 0 else "S"
        lon_dir = "E" if self.longitude >= 0 else "W"
        return (
            f"{abs(self.latitude):.{self.PRECISION}f} {lat_dir}",
            f"{abs(self.longitude):.{self.PRECISION}f} {lon_dir}",
        )

    def to_exif_dms(self) -> tuple[str, str, str, str]:
        """Convert to EXIF DMS (degrees, minutes, seconds) format.

        Returns:
            Tuple of (latitude, lat_ref, longitude, lon_ref).

        Example:
            >>> coords = GPSCoordinates(37.775, -122.4194)
            >>> lat, lat_ref, lon, lon_ref = coords.to_exif_dms()
            >>> print(f"{lat} {lat_ref}")
            37 deg 46' 30.00" N
        """
        lat_dir = "N" if self.latitude >= 0 else "S"
        lon_dir = "E" if self.longitude >= 0 else "W"

        lat_dms = self._decimal_to_dms(abs(self.latitude))
        lon_dms = self._decimal_to_dms(abs(self.longitude))

        return (lat_dms, lat_dir, lon_dms, lon_dir)

    def matches(self, other: GPSCoordinates, tolerance: float | None = None) -> bool:
        """Check if coordinates match within tolerance.

        Args:
            other: Another GPSCoordinates to compare.
            tolerance: Optional custom tolerance in decimal degrees.
                      Defaults to TOLERANCE (0.000001 = ~0.1m).

        Returns:
            True if coordinates match within tolerance.
        """
        tol = tolerance if tolerance is not None else self.TOLERANCE
        lat_match = abs(self.latitude - other.latitude) <= tol
        lon_match = abs(self.longitude - other.longitude) <= tol
        return lat_match and lon_match

    def distance_to(self, other: GPSCoordinates) -> float:
        """Calculate approximate distance to another coordinate in meters.

        Uses the Haversine formula for spherical distance calculation.

        Args:
            other: Another GPSCoordinates.

        Returns:
            Approximate distance in meters.
        """
        import math

        R = 6371000  # Earth's radius in meters

        lat1 = math.radians(self.latitude)
        lat2 = math.radians(other.latitude)
        dlat = math.radians(other.latitude - self.latitude)
        dlon = math.radians(other.longitude - self.longitude)

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    @staticmethod
    def _decimal_to_dms(decimal: float) -> str:
        """Convert decimal degrees to DMS string."""
        degrees = int(decimal)
        minutes_float = (decimal - degrees) * 60
        minutes = int(minutes_float)
        seconds = (minutes_float - minutes) * 60
        return f"{degrees} deg {minutes}' {seconds:.2f}\""

    @classmethod
    def from_quicktime(cls, value: str) -> GPSCoordinates | None:
        """Parse QuickTime GPS format (ISO 6709).

        Args:
            value: GPS string like "+37.7749-122.4194/" or "+37.7749-122.4194+10.5/"

        Returns:
            GPSCoordinates if parsed successfully, None otherwise.
        """
        value = value.strip().rstrip("/")
        if not value:
            return None

        # Find all signed numbers in the string
        # Matches patterns like: +37.774900, -122.419400, +10.50
        parts = re.findall(r"[+-]?\d+(?:\.\d+)?", value)

        if len(parts) < 2:
            return None

        try:
            lat = float(parts[0])
            lon = float(parts[1])
            alt = float(parts[2]) if len(parts) > 2 else None
            return cls(
                latitude=lat,
                longitude=lon,
                altitude=alt,
                source_format=GPSFormat.QUICKTIME,
            )
        except (ValueError, TypeError, IndexError):
            return None

    @classmethod
    def from_xmp(cls, lat_str: str, lon_str: str) -> GPSCoordinates | None:
        """Parse XMP GPS format.

        Args:
            lat_str: Latitude string like "37.7749 N" or "37.7749,N"
            lon_str: Longitude string like "122.4194 W" or "122.4194,W"

        Returns:
            GPSCoordinates if parsed successfully, None otherwise.
        """
        try:
            lat_match = re.match(r"([\d.]+)[,\s]*([NS])", lat_str.strip(), re.I)
            lon_match = re.match(r"([\d.]+)[,\s]*([EW])", lon_str.strip(), re.I)

            if not lat_match or not lon_match:
                return None

            lat = float(lat_match.group(1))
            if lat_match.group(2).upper() == "S":
                lat = -lat

            lon = float(lon_match.group(1))
            if lon_match.group(2).upper() == "W":
                lon = -lon

            return cls(
                latitude=lat,
                longitude=lon,
                source_format=GPSFormat.XMP,
            )
        except (ValueError, TypeError):
            return None

    @classmethod
    def from_exif_dms(
        cls,
        lat_dms: str,
        lat_ref: str,
        lon_dms: str,
        lon_ref: str,
    ) -> GPSCoordinates | None:
        """Parse EXIF DMS format.

        Args:
            lat_dms: Latitude in DMS like "37 deg 46' 30.00\""
            lat_ref: Latitude reference ("N" or "S")
            lon_dms: Longitude in DMS like "122 deg 25' 10.00\""
            lon_ref: Longitude reference ("E" or "W")

        Returns:
            GPSCoordinates if parsed successfully, None otherwise.
        """
        try:
            lat = cls._parse_dms(lat_dms)
            if lat_ref.upper() == "S":
                lat = -lat

            lon = cls._parse_dms(lon_dms)
            if lon_ref.upper() == "W":
                lon = -lon

            return cls(
                latitude=lat,
                longitude=lon,
                source_format=GPSFormat.EXIF,
            )
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_dms(dms: str) -> float:
        """Parse DMS string to decimal degrees."""
        # Handle multiple DMS formats
        patterns = [
            # "37 deg 46' 30.00""
            r"(\d+)\s*deg\s*(\d+)['\u2019]\s*([\d.]+)[\"″]?",
            # "37° 46' 30.00""
            r"(\d+)[°]\s*(\d+)['\u2019]\s*([\d.]+)[\"″]?",
            # "37:46:30.00"
            r"(\d+):(\d+):([\d.]+)",
        ]

        for pattern in patterns:
            match = re.match(pattern, dms.strip(), re.IGNORECASE)
            if match:
                degrees = float(match.group(1))
                minutes = float(match.group(2))
                seconds = float(match.group(3))
                return degrees + minutes / 60 + seconds / 3600

        raise ValueError(f"Cannot parse DMS string: {dms}")


@dataclass
class GPSVerificationResult:
    """Result of GPS coordinate verification.

    Attributes:
        passed: True if GPS was preserved within tolerance.
        original: Original GPS coordinates (None if not present).
        converted: Converted GPS coordinates (None if not present).
        distance_meters: Distance between coordinates in meters (if both exist).
        tolerance_used: Tolerance used for comparison in decimal degrees.
        details: Additional verification details.
    """

    passed: bool
    original: GPSCoordinates | None = None
    converted: GPSCoordinates | None = None
    distance_meters: float | None = None
    tolerance_used: float = GPSCoordinates.TOLERANCE
    details: str = ""


class GPSHandler:
    """Handle GPS coordinate preservation during video conversion.

    This class provides specialized methods for extracting, applying,
    and verifying GPS coordinates across different metadata formats.

    Example:
        >>> handler = GPSHandler(CommandRunner())
        >>> coords = handler.extract(Path("video.mp4"))
        >>> if coords:
        ...     handler.apply(Path("output.mp4"), coords)
        ...     result = handler.verify(Path("video.mp4"), Path("output.mp4"))
        ...     print(f"Verification: {result.passed}")
    """

    def __init__(self, metadata_processor: MetadataProcessor | None = None) -> None:
        """Initialize GPSHandler.

        Args:
            metadata_processor: MetadataProcessor to use for metadata operations.
                              If None, creates a new one.
        """
        self._processor = metadata_processor or MetadataProcessor()

    def extract(self, path: Path) -> GPSCoordinates | None:
        """Extract GPS coordinates from a video file.

        Checks all possible GPS tag locations (QuickTime, XMP, EXIF, Keys)
        and returns coordinates if found.

        Args:
            path: Path to the video file.

        Returns:
            GPSCoordinates if found, None otherwise.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            MetadataExtractionError: If extraction fails.
        """
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        metadata = self._processor.extract(path)
        return self._parse_gps_from_metadata(metadata)

    def apply(
        self,
        path: Path,
        coords: GPSCoordinates,
        *,
        overwrite_original: bool = True,
    ) -> bool:
        """Apply GPS coordinates to a video file.

        Writes GPS data in multiple formats to ensure maximum compatibility.

        Args:
            path: Path to the video file.
            coords: GPS coordinates to apply.
            overwrite_original: If True, modify file in place.

        Returns:
            True if GPS was applied successfully.

        Raises:
            FileNotFoundError: If the file doesn't exist.
        """
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        # Set GPS tags in multiple formats for maximum compatibility
        tags_to_set = self._build_gps_tags(coords)

        success = True
        for tag, value in tags_to_set.items():
            result = self._processor.set_tag(
                path, tag, value, overwrite_original=overwrite_original
            )
            if not result:
                success = False

        return success

    def copy(
        self,
        source: Path,
        dest: Path,
        *,
        overwrite_original: bool = True,
    ) -> bool:
        """Copy GPS data from source to destination file.

        Args:
            source: Source file with GPS data.
            dest: Destination file.
            overwrite_original: If True, modify dest in place.

        Returns:
            True if GPS was copied successfully.
        """
        return self._processor.copy_gps(
            source, dest, overwrite_original=overwrite_original
        )

    def verify(
        self,
        original: Path,
        converted: Path,
        *,
        tolerance: float | None = None,
    ) -> GPSVerificationResult:
        """Verify GPS was preserved during conversion.

        Args:
            original: Original source file.
            converted: Converted output file.
            tolerance: Custom tolerance in decimal degrees.
                      Defaults to GPSCoordinates.TOLERANCE (~0.1m).

        Returns:
            GPSVerificationResult with detailed comparison.

        Raises:
            FileNotFoundError: If either file doesn't exist.
        """
        if not original.exists():
            raise FileNotFoundError(f"Original file not found: {original}")
        if not converted.exists():
            raise FileNotFoundError(f"Converted file not found: {converted}")

        tol = tolerance if tolerance is not None else GPSCoordinates.TOLERANCE

        try:
            orig_gps = self.extract(original)
        except MetadataExtractionError:
            orig_gps = None

        try:
            conv_gps = self.extract(converted)
        except MetadataExtractionError:
            conv_gps = None

        # Case 1: No GPS in original (OK)
        if orig_gps is None:
            return GPSVerificationResult(
                passed=True,
                original=None,
                converted=conv_gps,
                tolerance_used=tol,
                details="No GPS in original file",
            )

        # Case 2: GPS in original but not in converted (FAIL)
        if conv_gps is None:
            return GPSVerificationResult(
                passed=False,
                original=orig_gps,
                converted=None,
                tolerance_used=tol,
                details="GPS missing in converted file",
            )

        # Case 3: Compare coordinates
        distance = orig_gps.distance_to(conv_gps)
        matches = orig_gps.matches(conv_gps, tolerance=tol)

        if matches:
            details = f"GPS preserved (distance: {distance:.2f}m)"
        else:
            details = (
                f"GPS mismatch: original {orig_gps} vs converted {conv_gps} "
                f"(distance: {distance:.2f}m)"
            )

        return GPSVerificationResult(
            passed=matches,
            original=orig_gps,
            converted=conv_gps,
            distance_meters=distance,
            tolerance_used=tol,
            details=details,
        )

    def has_gps(self, path: Path) -> bool:
        """Check if a video file has GPS data.

        Args:
            path: Path to the video file.

        Returns:
            True if the file has GPS coordinates.
        """
        try:
            return self.extract(path) is not None
        except (FileNotFoundError, MetadataExtractionError):
            return False

    def _parse_gps_from_metadata(self, metadata: dict[str, Any]) -> GPSCoordinates | None:
        """Parse GPS coordinates from metadata dictionary.

        Checks all possible GPS tag locations in order of preference.

        Args:
            metadata: Metadata dictionary from exiftool.

        Returns:
            GPSCoordinates if found, None otherwise.
        """
        # Try QuickTime/Composite GPS Position first (most common for videos)
        gps_position = self._find_tag(metadata, "GPSPosition")
        if gps_position:
            coords = self._parse_gps_position(gps_position)
            if coords:
                return coords

        # Try QuickTime GPSCoordinates (ISO 6709 format)
        gps_coords = self._find_tag(metadata, "GPSCoordinates")
        if gps_coords:
            coords = GPSCoordinates.from_quicktime(str(gps_coords))
            if coords:
                return coords

        # Try separate lat/lon tags
        lat = self._find_tag(metadata, "GPSLatitude")
        lon = self._find_tag(metadata, "GPSLongitude")

        if lat is not None and lon is not None:
            try:
                lat_float = self._parse_coordinate(lat, metadata, "Latitude")
                lon_float = self._parse_coordinate(lon, metadata, "Longitude")

                alt = self._find_tag(metadata, "GPSAltitude")
                alt_float = float(alt) if alt is not None else None

                accuracy = self._find_tag(metadata, "GPSHPositioningError")
                acc_float = float(accuracy) if accuracy is not None else None

                return GPSCoordinates(
                    latitude=lat_float,
                    longitude=lon_float,
                    altitude=alt_float,
                    accuracy=acc_float,
                )
            except (ValueError, TypeError):
                pass

        return None

    def _find_tag(self, metadata: dict[str, Any], tag: str) -> Any:
        """Find a tag value in metadata, handling group prefixes."""
        # Direct match
        if tag in metadata:
            return metadata[tag]

        # Match with any group prefix
        for key, value in metadata.items():
            if key.endswith(f":{tag}") or key == tag:
                return value
            if ":" in key and key.split(":")[-1] == tag:
                return value

        return None

    def _parse_coordinate(
        self,
        value: Any,
        metadata: dict[str, Any],
        coord_type: str,
    ) -> float:
        """Parse a GPS coordinate value to decimal degrees."""
        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            # Try DMS format
            dms_match = re.match(
                r"(\d+)\s*deg\s*(\d+)['\u2019]\s*([\d.]+)[\"″]?\s*([NSEW])?",
                value,
                re.IGNORECASE,
            )
            if dms_match:
                degrees = float(dms_match.group(1))
                minutes = float(dms_match.group(2))
                seconds = float(dms_match.group(3))
                direction = dms_match.group(4)

                decimal = degrees + minutes / 60 + seconds / 3600

                if direction and direction.upper() in ("S", "W"):
                    decimal = -decimal
                return decimal

            # Try simple float
            try:
                return float(value)
            except ValueError:
                pass

        raise ValueError(f"Cannot parse GPS value: {value}")

    def _parse_gps_position(self, position: Any) -> GPSCoordinates | None:
        """Parse GPS position composite string."""
        if not isinstance(position, str):
            return None

        # Format: "lat lon" or "lat, lon"
        parts = re.split(r"[,\s]+", position.strip())

        if len(parts) >= 2:
            try:
                lat = float(parts[0])
                lon = float(parts[1])
                return GPSCoordinates(latitude=lat, longitude=lon)
            except ValueError:
                pass

        return None

    def _build_gps_tags(self, coords: GPSCoordinates) -> dict[str, str]:
        """Build GPS tags for writing to file."""
        lat_xmp, lon_xmp = coords.to_xmp()

        tags = {
            # QuickTime format
            "GPSCoordinates": coords.to_quicktime(),
            # XMP format
            "XMP:GPSLatitude": lat_xmp,
            "XMP:GPSLongitude": lon_xmp,
            # Standard GPS tags
            "GPSLatitude": str(abs(coords.latitude)),
            "GPSLatitudeRef": "N" if coords.latitude >= 0 else "S",
            "GPSLongitude": str(abs(coords.longitude)),
            "GPSLongitudeRef": "E" if coords.longitude >= 0 else "W",
        }

        if coords.altitude is not None:
            tags["GPSAltitude"] = str(abs(coords.altitude))
            tags["GPSAltitudeRef"] = "0" if coords.altitude >= 0 else "1"

        return tags
