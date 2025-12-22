"""Metadata verification system for video conversion.

This module provides a comprehensive metadata verification system that compares
original and converted files to ensure all critical metadata was preserved
during conversion.

SDS Reference: SDS-P01-004
SRS Reference: SRS-403 (Metadata Verification)

Example:
    >>> from video_converter.processors.verification import MetadataVerifier
    >>> verifier = MetadataVerifier()
    >>> result = verifier.verify(Path("original.mp4"), Path("converted.mp4"))
    >>> if result.passed:
    ...     print("All metadata preserved successfully")
    >>> else:
    ...     for check in result.failed_checks:
    ...         print(f"FAILED: {check.category} - {check.details}")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from video_converter.processors.gps import GPSHandler
from video_converter.processors.metadata import MetadataProcessor


class VerificationCategory(Enum):
    """Categories of metadata verification.

    Attributes:
        DATE_TIME: Date and time metadata (CreateDate, ModifyDate).
        GPS: GPS location data (Latitude, Longitude, Altitude).
        CAMERA: Camera information (Make, Model).
        VIDEO: Video properties (Duration, Rotation).
        AUDIO: Audio properties (Codec, Channels).
    """

    DATE_TIME = "date_time"
    GPS = "gps"
    CAMERA = "camera"
    VIDEO = "video"
    AUDIO = "audio"


class CheckStatus(Enum):
    """Status of a single verification check.

    Attributes:
        PASSED: Check passed successfully.
        FAILED: Check failed - values don't match within tolerance.
        MISSING_IN_SOURCE: Field not present in original file.
        MISSING_IN_CONVERTED: Field was in original but missing in converted.
        ERROR: An error occurred during verification.
    """

    PASSED = "passed"
    FAILED = "failed"
    MISSING_IN_SOURCE = "missing_in_source"
    MISSING_IN_CONVERTED = "missing_in_converted"
    ERROR = "error"


@dataclass
class ToleranceSettings:
    """Configurable tolerance settings for metadata verification.

    Attributes:
        date_seconds: Tolerance for date/time comparison in seconds.
        gps_degrees: Tolerance for GPS coordinates in decimal degrees.
        duration_seconds: Tolerance for video duration in seconds.
        numeric_relative: Relative tolerance for other numeric values.
    """

    date_seconds: float = 1.0
    gps_degrees: float = 0.000001
    duration_seconds: float = 0.1
    numeric_relative: float = 0.001

    @classmethod
    def strict(cls) -> ToleranceSettings:
        """Create strict tolerance settings with minimal margins."""
        return cls(
            date_seconds=0.0,
            gps_degrees=0.0,
            duration_seconds=0.0,
            numeric_relative=0.0,
        )

    @classmethod
    def relaxed(cls) -> ToleranceSettings:
        """Create relaxed tolerance settings for problematic files."""
        return cls(
            date_seconds=60.0,
            gps_degrees=0.0001,
            duration_seconds=1.0,
            numeric_relative=0.01,
        )


@dataclass
class CheckResult:
    """Result of a single metadata verification check.

    Attributes:
        category: The verification category this check belongs to.
        field_name: Name of the metadata field being verified.
        status: Status of the verification check.
        original_value: Value from the original file.
        converted_value: Value from the converted file.
        tolerance_used: Tolerance value applied to comparison.
        details: Additional details about the check result.
    """

    category: VerificationCategory
    field_name: str
    status: CheckStatus
    original_value: Any = None
    converted_value: Any = None
    tolerance_used: float | None = None
    details: str = ""

    @property
    def passed(self) -> bool:
        """Return True if the check passed."""
        return self.status == CheckStatus.PASSED

    def __str__(self) -> str:
        """Return human-readable check result."""
        status_str = "✓" if self.passed else "✗"
        return f"{status_str} {self.category.value}/{self.field_name}: {self.details}"


@dataclass
class VerificationResult:
    """Result of complete metadata verification between two files.

    Attributes:
        passed: True if all critical checks passed.
        original_path: Path to the original file.
        converted_path: Path to the converted file.
        checks: List of individual check results.
        verification_time: When the verification was performed.
        tolerance_settings: Tolerance settings used for verification.
    """

    passed: bool
    original_path: Path
    converted_path: Path
    checks: list[CheckResult] = field(default_factory=list)
    verification_time: datetime = field(default_factory=datetime.now)
    tolerance_settings: ToleranceSettings = field(default_factory=ToleranceSettings)

    @property
    def failed_checks(self) -> list[CheckResult]:
        """Return list of failed checks."""
        return [c for c in self.checks if not c.passed]

    @property
    def passed_checks(self) -> list[CheckResult]:
        """Return list of passed checks."""
        return [c for c in self.checks if c.passed]

    @property
    def checks_by_category(self) -> dict[VerificationCategory, list[CheckResult]]:
        """Group checks by category."""
        result: dict[VerificationCategory, list[CheckResult]] = {}
        for check in self.checks:
            if check.category not in result:
                result[check.category] = []
            result[check.category].append(check)
        return result

    def get_summary(self) -> str:
        """Generate a summary of the verification result."""
        total = len(self.checks)
        passed = len(self.passed_checks)
        failed = len(self.failed_checks)

        lines = [
            f"Verification Result: {'PASSED' if self.passed else 'FAILED'}",
            f"Original: {self.original_path.name}",
            f"Converted: {self.converted_path.name}",
            f"Checks: {passed}/{total} passed, {failed} failed",
        ]

        if self.failed_checks:
            lines.append("\nFailed checks:")
            for check in self.failed_checks:
                lines.append(f"  - {check}")

        return "\n".join(lines)


class MetadataVerifier:
    """Verify metadata preservation during video conversion.

    This class provides comprehensive metadata verification comparing
    original and converted files across all critical metadata categories.

    Attributes:
        DATE_TIME_FIELDS: Fields to check for date/time category.
        CAMERA_FIELDS: Fields to check for camera information.
        VIDEO_FIELDS: Fields to check for video properties.
        AUDIO_FIELDS: Fields to check for audio properties.

    Example:
        >>> verifier = MetadataVerifier()
        >>> result = verifier.verify(Path("original.mp4"), Path("converted.mp4"))
        >>> print(result.get_summary())
        Verification Result: PASSED
        Original: original.mp4
        Converted: converted.mp4
        Checks: 10/10 passed, 0 failed
    """

    DATE_TIME_FIELDS = [
        "CreateDate",
        "ModifyDate",
        "DateTimeOriginal",
        "MediaCreateDate",
        "MediaModifyDate",
    ]

    CAMERA_FIELDS = [
        "Make",
        "Model",
        "Software",
    ]

    VIDEO_FIELDS = [
        "Duration",
        "Rotation",
        "ImageWidth",
        "ImageHeight",
        "VideoFrameRate",
    ]

    AUDIO_FIELDS = [
        "AudioCodec",
        "AudioChannels",
        "AudioSampleRate",
        "AudioBitsPerSample",
    ]

    def __init__(
        self,
        metadata_processor: MetadataProcessor | None = None,
        gps_handler: GPSHandler | None = None,
        tolerance: ToleranceSettings | None = None,
    ) -> None:
        """Initialize MetadataVerifier.

        Args:
            metadata_processor: MetadataProcessor instance for metadata extraction.
            gps_handler: GPSHandler instance for GPS verification.
            tolerance: ToleranceSettings for comparison. Defaults to standard settings.
        """
        self._processor = metadata_processor or MetadataProcessor()
        self._gps_handler = gps_handler or GPSHandler(self._processor)
        self._tolerance = tolerance or ToleranceSettings()

    @property
    def tolerance(self) -> ToleranceSettings:
        """Get current tolerance settings."""
        return self._tolerance

    @tolerance.setter
    def tolerance(self, value: ToleranceSettings) -> None:
        """Set tolerance settings."""
        self._tolerance = value

    def verify(
        self,
        original: Path,
        converted: Path,
        *,
        tolerance: ToleranceSettings | None = None,
        categories: list[VerificationCategory] | None = None,
    ) -> VerificationResult:
        """Run all verification checks on two files.

        Args:
            original: Path to the original video file.
            converted: Path to the converted video file.
            tolerance: Optional custom tolerance settings for this verification.
            categories: Optional list of categories to verify. If None, verifies all.

        Returns:
            VerificationResult with all check details.

        Raises:
            FileNotFoundError: If either file doesn't exist.
        """
        if not original.exists():
            raise FileNotFoundError(f"Original file not found: {original}")
        if not converted.exists():
            raise FileNotFoundError(f"Converted file not found: {converted}")

        tol = tolerance or self._tolerance
        cats = categories or list(VerificationCategory)

        checks: list[CheckResult] = []
        orig_meta = self._processor.extract(original)
        conv_meta = self._processor.extract(converted)

        if VerificationCategory.DATE_TIME in cats:
            checks.extend(self._verify_dates(orig_meta, conv_meta, tol))

        if VerificationCategory.GPS in cats:
            checks.extend(self._verify_gps(original, converted, tol))

        if VerificationCategory.CAMERA in cats:
            checks.extend(self._verify_camera(orig_meta, conv_meta))

        if VerificationCategory.VIDEO in cats:
            checks.extend(self._verify_video(orig_meta, conv_meta, tol))

        if VerificationCategory.AUDIO in cats:
            checks.extend(self._verify_audio(orig_meta, conv_meta))

        all_passed = all(c.passed for c in checks) if checks else True

        return VerificationResult(
            passed=all_passed,
            original_path=original,
            converted_path=converted,
            checks=checks,
            tolerance_settings=tol,
        )

    def _verify_dates(
        self,
        orig_meta: dict[str, Any],
        conv_meta: dict[str, Any],
        tolerance: ToleranceSettings,
    ) -> list[CheckResult]:
        """Verify date/time metadata fields.

        Args:
            orig_meta: Metadata from original file.
            conv_meta: Metadata from converted file.
            tolerance: Tolerance settings.

        Returns:
            List of CheckResult for date/time fields.
        """
        results: list[CheckResult] = []

        for tag_name in self.DATE_TIME_FIELDS:
            orig_value = self._find_tag_value(orig_meta, tag_name)
            conv_value = self._find_tag_value(conv_meta, tag_name)

            if orig_value is None:
                continue

            if conv_value is None:
                results.append(
                    CheckResult(
                        category=VerificationCategory.DATE_TIME,
                        field_name=tag_name,
                        status=CheckStatus.MISSING_IN_CONVERTED,
                        original_value=orig_value,
                        details=f"Field '{tag_name}' missing in converted file",
                    )
                )
                continue

            try:
                orig_dt = self._parse_datetime(orig_value)
                conv_dt = self._parse_datetime(conv_value)

                if orig_dt is None or conv_dt is None:
                    matched = str(orig_value).strip() == str(conv_value).strip()
                else:
                    diff_seconds = abs((orig_dt - conv_dt).total_seconds())
                    matched = diff_seconds <= tolerance.date_seconds

                if matched:
                    results.append(
                        CheckResult(
                            category=VerificationCategory.DATE_TIME,
                            field_name=tag_name,
                            status=CheckStatus.PASSED,
                            original_value=orig_value,
                            converted_value=conv_value,
                            tolerance_used=tolerance.date_seconds,
                            details="Date/time matches within tolerance",
                        )
                    )
                else:
                    diff = (
                        f"{diff_seconds:.1f}s difference"
                        if orig_dt and conv_dt
                        else "values differ"
                    )
                    results.append(
                        CheckResult(
                            category=VerificationCategory.DATE_TIME,
                            field_name=tag_name,
                            status=CheckStatus.FAILED,
                            original_value=orig_value,
                            converted_value=conv_value,
                            tolerance_used=tolerance.date_seconds,
                            details=f"Date/time mismatch: {diff}",
                        )
                    )

            except (ValueError, TypeError) as e:
                results.append(
                    CheckResult(
                        category=VerificationCategory.DATE_TIME,
                        field_name=tag_name,
                        status=CheckStatus.ERROR,
                        original_value=orig_value,
                        converted_value=conv_value,
                        details=f"Error parsing date: {e}",
                    )
                )

        return results

    def _verify_gps(
        self,
        original: Path,
        converted: Path,
        tolerance: ToleranceSettings,
    ) -> list[CheckResult]:
        """Verify GPS metadata preservation.

        Args:
            original: Path to original file.
            converted: Path to converted file.
            tolerance: Tolerance settings.

        Returns:
            List of CheckResult for GPS verification.
        """
        results: list[CheckResult] = []

        try:
            orig_gps = self._gps_handler.extract(original)
        except Exception:
            orig_gps = None

        try:
            conv_gps = self._gps_handler.extract(converted)
        except Exception:
            conv_gps = None

        if orig_gps is None:
            return results

        if conv_gps is None:
            results.append(
                CheckResult(
                    category=VerificationCategory.GPS,
                    field_name="GPSCoordinates",
                    status=CheckStatus.MISSING_IN_CONVERTED,
                    original_value=str(orig_gps),
                    details="GPS data missing in converted file",
                )
            )
            return results

        lat_diff = abs(orig_gps.latitude - conv_gps.latitude)
        lon_diff = abs(orig_gps.longitude - conv_gps.longitude)
        matched = lat_diff <= tolerance.gps_degrees and lon_diff <= tolerance.gps_degrees

        if matched:
            distance = orig_gps.distance_to(conv_gps)
            results.append(
                CheckResult(
                    category=VerificationCategory.GPS,
                    field_name="GPSCoordinates",
                    status=CheckStatus.PASSED,
                    original_value=str(orig_gps),
                    converted_value=str(conv_gps),
                    tolerance_used=tolerance.gps_degrees,
                    details=f"GPS matches within tolerance (distance: {distance:.2f}m)",
                )
            )
        else:
            distance = orig_gps.distance_to(conv_gps)
            results.append(
                CheckResult(
                    category=VerificationCategory.GPS,
                    field_name="GPSCoordinates",
                    status=CheckStatus.FAILED,
                    original_value=str(orig_gps),
                    converted_value=str(conv_gps),
                    tolerance_used=tolerance.gps_degrees,
                    details=f"GPS mismatch: {distance:.2f}m difference",
                )
            )

        if orig_gps.altitude is not None:
            if conv_gps.altitude is None:
                results.append(
                    CheckResult(
                        category=VerificationCategory.GPS,
                        field_name="GPSAltitude",
                        status=CheckStatus.MISSING_IN_CONVERTED,
                        original_value=orig_gps.altitude,
                        details="Altitude missing in converted file",
                    )
                )
            else:
                alt_diff = abs(orig_gps.altitude - conv_gps.altitude)
                alt_matched = alt_diff <= 1.0

                if alt_matched:
                    results.append(
                        CheckResult(
                            category=VerificationCategory.GPS,
                            field_name="GPSAltitude",
                            status=CheckStatus.PASSED,
                            original_value=orig_gps.altitude,
                            converted_value=conv_gps.altitude,
                            tolerance_used=1.0,
                            details="Altitude matches within tolerance",
                        )
                    )
                else:
                    results.append(
                        CheckResult(
                            category=VerificationCategory.GPS,
                            field_name="GPSAltitude",
                            status=CheckStatus.FAILED,
                            original_value=orig_gps.altitude,
                            converted_value=conv_gps.altitude,
                            tolerance_used=1.0,
                            details=f"Altitude mismatch: {alt_diff:.1f}m difference",
                        )
                    )

        return results

    def _verify_camera(
        self,
        orig_meta: dict[str, Any],
        conv_meta: dict[str, Any],
    ) -> list[CheckResult]:
        """Verify camera metadata fields (exact match required).

        Args:
            orig_meta: Metadata from original file.
            conv_meta: Metadata from converted file.

        Returns:
            List of CheckResult for camera fields.
        """
        results: list[CheckResult] = []

        for tag_name in self.CAMERA_FIELDS:
            orig_value = self._find_tag_value(orig_meta, tag_name)
            conv_value = self._find_tag_value(conv_meta, tag_name)

            if orig_value is None:
                continue

            if conv_value is None:
                results.append(
                    CheckResult(
                        category=VerificationCategory.CAMERA,
                        field_name=tag_name,
                        status=CheckStatus.MISSING_IN_CONVERTED,
                        original_value=orig_value,
                        details=f"Field '{tag_name}' missing in converted file",
                    )
                )
                continue

            orig_str = str(orig_value).strip().lower()
            conv_str = str(conv_value).strip().lower()
            matched = orig_str == conv_str

            if matched:
                results.append(
                    CheckResult(
                        category=VerificationCategory.CAMERA,
                        field_name=tag_name,
                        status=CheckStatus.PASSED,
                        original_value=orig_value,
                        converted_value=conv_value,
                        details="Exact match",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        category=VerificationCategory.CAMERA,
                        field_name=tag_name,
                        status=CheckStatus.FAILED,
                        original_value=orig_value,
                        converted_value=conv_value,
                        details=f"Mismatch: '{orig_value}' vs '{conv_value}'",
                    )
                )

        return results

    def _verify_video(
        self,
        orig_meta: dict[str, Any],
        conv_meta: dict[str, Any],
        tolerance: ToleranceSettings,
    ) -> list[CheckResult]:
        """Verify video metadata fields.

        Args:
            orig_meta: Metadata from original file.
            conv_meta: Metadata from converted file.
            tolerance: Tolerance settings.

        Returns:
            List of CheckResult for video fields.
        """
        results: list[CheckResult] = []

        for tag_name in self.VIDEO_FIELDS:
            orig_value = self._find_tag_value(orig_meta, tag_name)
            conv_value = self._find_tag_value(conv_meta, tag_name)

            if orig_value is None:
                continue

            if conv_value is None:
                results.append(
                    CheckResult(
                        category=VerificationCategory.VIDEO,
                        field_name=tag_name,
                        status=CheckStatus.MISSING_IN_CONVERTED,
                        original_value=orig_value,
                        details=f"Field '{tag_name}' missing in converted file",
                    )
                )
                continue

            if tag_name == "Duration":
                check = self._compare_duration(orig_value, conv_value, tolerance.duration_seconds)
            elif tag_name == "Rotation":
                check = self._compare_exact(orig_value, conv_value)
            else:
                check = self._compare_numeric(orig_value, conv_value, tolerance.numeric_relative)

            check.category = VerificationCategory.VIDEO
            check.field_name = tag_name
            results.append(check)

        return results

    def _verify_audio(
        self,
        orig_meta: dict[str, Any],
        conv_meta: dict[str, Any],
    ) -> list[CheckResult]:
        """Verify audio metadata fields (exact match for codec/channels).

        Args:
            orig_meta: Metadata from original file.
            conv_meta: Metadata from converted file.

        Returns:
            List of CheckResult for audio fields.
        """
        results: list[CheckResult] = []

        for tag_name in self.AUDIO_FIELDS:
            orig_value = self._find_tag_value(orig_meta, tag_name)
            conv_value = self._find_tag_value(conv_meta, tag_name)

            if orig_value is None:
                continue

            if conv_value is None:
                results.append(
                    CheckResult(
                        category=VerificationCategory.AUDIO,
                        field_name=tag_name,
                        status=CheckStatus.MISSING_IN_CONVERTED,
                        original_value=orig_value,
                        details=f"Field '{tag_name}' missing in converted file",
                    )
                )
                continue

            if tag_name in ("AudioCodec", "AudioChannels"):
                check = self._compare_exact(orig_value, conv_value)
            else:
                check = self._compare_numeric(orig_value, conv_value, 0.001)

            check.category = VerificationCategory.AUDIO
            check.field_name = tag_name
            results.append(check)

        return results

    def _find_tag_value(self, metadata: dict[str, Any], tag: str) -> Any:
        """Find a tag value in metadata dict, handling group prefixes.

        Args:
            metadata: Metadata dictionary.
            tag: Tag name to find.

        Returns:
            Tag value if found, None otherwise.
        """
        if tag in metadata:
            return metadata[tag]

        for key, value in metadata.items():
            if key.endswith(f":{tag}") or key == tag:
                return value
            if ":" in key and key.split(":")[-1] == tag:
                return value

        return None

    def _parse_datetime(self, value: Any) -> datetime | None:
        """Parse a datetime value from metadata.

        Args:
            value: Value to parse.

        Returns:
            Parsed datetime or None if parsing fails.
        """
        if isinstance(value, datetime):
            return value

        if not isinstance(value, str):
            return None

        formats = [
            "%Y:%m:%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y:%m:%d %H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
        ]

        value = value.strip()

        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue

        return None

    def _compare_duration(
        self,
        orig: Any,
        conv: Any,
        tolerance_seconds: float,
    ) -> CheckResult:
        """Compare duration values.

        Args:
            orig: Original duration value.
            conv: Converted duration value.
            tolerance_seconds: Allowed difference in seconds.

        Returns:
            CheckResult for duration comparison.
        """
        orig_seconds = self._parse_duration(orig)
        conv_seconds = self._parse_duration(conv)

        if orig_seconds is None or conv_seconds is None:
            orig_str = str(orig).strip()
            conv_str = str(conv).strip()
            matched = orig_str == conv_str
            return CheckResult(
                category=VerificationCategory.VIDEO,
                field_name="Duration",
                status=CheckStatus.PASSED if matched else CheckStatus.FAILED,
                original_value=orig,
                converted_value=conv,
                details="String comparison used" if matched else "Duration format mismatch",
            )

        diff = abs(orig_seconds - conv_seconds)
        matched = diff <= tolerance_seconds

        return CheckResult(
            category=VerificationCategory.VIDEO,
            field_name="Duration",
            status=CheckStatus.PASSED if matched else CheckStatus.FAILED,
            original_value=f"{orig_seconds:.2f}s",
            converted_value=f"{conv_seconds:.2f}s",
            tolerance_used=tolerance_seconds,
            details=f"Duration {'matches' if matched else 'mismatch'}: {diff:.2f}s difference",
        )

    def _parse_duration(self, value: Any) -> float | None:
        """Parse duration to seconds.

        Args:
            value: Duration value (string or number).

        Returns:
            Duration in seconds or None if parsing fails.
        """
        if isinstance(value, (int, float)):
            return float(value)

        if not isinstance(value, str):
            return None

        value = value.strip()

        if match := re.match(r"(\d+):(\d+):(\d+(?:\.\d+)?)", value):
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = float(match.group(3))
            return hours * 3600 + minutes * 60 + seconds

        if match := re.match(r"(\d+):(\d+(?:\.\d+)?)", value):
            minutes = int(match.group(1))
            seconds = float(match.group(2))
            return minutes * 60 + seconds

        if match := re.match(r"([\d.]+)\s*s", value):
            return float(match.group(1))

        try:
            return float(value)
        except ValueError:
            return None

    def _compare_exact(self, orig: Any, conv: Any) -> CheckResult:
        """Compare values for exact match.

        Args:
            orig: Original value.
            conv: Converted value.

        Returns:
            CheckResult for exact comparison.
        """
        if isinstance(orig, (int, float)) and isinstance(conv, (int, float)):
            matched = orig == conv
        else:
            orig_str = str(orig).strip().lower()
            conv_str = str(conv).strip().lower()
            matched = orig_str == conv_str

        return CheckResult(
            category=VerificationCategory.VIDEO,
            field_name="",
            status=CheckStatus.PASSED if matched else CheckStatus.FAILED,
            original_value=orig,
            converted_value=conv,
            details="Exact match" if matched else f"Mismatch: '{orig}' vs '{conv}'",
        )

    def _compare_numeric(
        self,
        orig: Any,
        conv: Any,
        relative_tolerance: float,
    ) -> CheckResult:
        """Compare numeric values with relative tolerance.

        Args:
            orig: Original value.
            conv: Converted value.
            relative_tolerance: Relative tolerance for comparison.

        Returns:
            CheckResult for numeric comparison.
        """
        try:
            orig_num = float(str(orig).strip())
            conv_num = float(str(conv).strip())
        except (ValueError, TypeError):
            orig_str = str(orig).strip()
            conv_str = str(conv).strip()
            matched = orig_str == conv_str
            return CheckResult(
                category=VerificationCategory.VIDEO,
                field_name="",
                status=CheckStatus.PASSED if matched else CheckStatus.FAILED,
                original_value=orig,
                converted_value=conv,
                details="String comparison used" if matched else f"Mismatch: '{orig}' vs '{conv}'",
            )

        if orig_num == 0:
            matched = conv_num == 0
        else:
            relative_diff = abs(orig_num - conv_num) / abs(orig_num)
            matched = relative_diff <= relative_tolerance

        return CheckResult(
            category=VerificationCategory.VIDEO,
            field_name="",
            status=CheckStatus.PASSED if matched else CheckStatus.FAILED,
            original_value=orig_num,
            converted_value=conv_num,
            tolerance_used=relative_tolerance,
            details="Matches within tolerance"
            if matched
            else f"Mismatch: {orig_num} vs {conv_num}",
        )
