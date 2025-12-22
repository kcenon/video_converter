"""Unit tests for metadata verification module."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from video_converter.processors.metadata import MetadataProcessor
from video_converter.processors.verification import (
    CheckResult,
    CheckStatus,
    MetadataVerifier,
    ToleranceSettings,
    VerificationCategory,
    VerificationResult,
)
from video_converter.utils.command_runner import CommandResult, CommandRunner


class TestToleranceSettings:
    """Tests for ToleranceSettings dataclass."""

    def test_default_values(self) -> None:
        """Test default tolerance values."""
        settings = ToleranceSettings()
        assert settings.date_seconds == 1.0
        assert settings.gps_degrees == 0.000001
        assert settings.duration_seconds == 0.1
        assert settings.numeric_relative == 0.001

    def test_strict_factory(self) -> None:
        """Test strict tolerance factory method."""
        settings = ToleranceSettings.strict()
        assert settings.date_seconds == 0.0
        assert settings.gps_degrees == 0.0
        assert settings.duration_seconds == 0.0
        assert settings.numeric_relative == 0.0

    def test_relaxed_factory(self) -> None:
        """Test relaxed tolerance factory method."""
        settings = ToleranceSettings.relaxed()
        assert settings.date_seconds == 60.0
        assert settings.gps_degrees == 0.0001
        assert settings.duration_seconds == 1.0
        assert settings.numeric_relative == 0.01

    def test_custom_values(self) -> None:
        """Test custom tolerance values."""
        settings = ToleranceSettings(
            date_seconds=5.0,
            gps_degrees=0.00001,
            duration_seconds=0.5,
            numeric_relative=0.01,
        )
        assert settings.date_seconds == 5.0
        assert settings.gps_degrees == 0.00001


class TestCheckResult:
    """Tests for CheckResult dataclass."""

    def test_passed_check(self) -> None:
        """Test passed check result."""
        check = CheckResult(
            category=VerificationCategory.DATE_TIME,
            field_name="CreateDate",
            status=CheckStatus.PASSED,
            original_value="2024:01:15 10:00:00",
            converted_value="2024:01:15 10:00:00",
            details="Date/time matches",
        )
        assert check.passed is True
        assert "✓" in str(check)

    def test_failed_check(self) -> None:
        """Test failed check result."""
        check = CheckResult(
            category=VerificationCategory.GPS,
            field_name="GPSCoordinates",
            status=CheckStatus.FAILED,
            original_value="37.7749°N, 122.4194°W",
            converted_value="40.7128°N, 74.0060°W",
            details="GPS mismatch",
        )
        assert check.passed is False
        assert "✗" in str(check)

    def test_missing_in_converted(self) -> None:
        """Test missing field in converted file."""
        check = CheckResult(
            category=VerificationCategory.CAMERA,
            field_name="Make",
            status=CheckStatus.MISSING_IN_CONVERTED,
            original_value="Apple",
            details="Field missing in converted file",
        )
        assert check.passed is False

    def test_str_representation(self) -> None:
        """Test string representation includes key info."""
        check = CheckResult(
            category=VerificationCategory.VIDEO,
            field_name="Duration",
            status=CheckStatus.PASSED,
            details="Duration matches",
        )
        result = str(check)
        assert "video" in result
        assert "Duration" in result


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    @pytest.fixture
    def sample_checks(self) -> list[CheckResult]:
        """Create sample check results."""
        return [
            CheckResult(
                category=VerificationCategory.DATE_TIME,
                field_name="CreateDate",
                status=CheckStatus.PASSED,
            ),
            CheckResult(
                category=VerificationCategory.GPS,
                field_name="GPSCoordinates",
                status=CheckStatus.PASSED,
            ),
            CheckResult(
                category=VerificationCategory.CAMERA,
                field_name="Make",
                status=CheckStatus.FAILED,
            ),
        ]

    def test_passed_result(self, tmp_path: Path) -> None:
        """Test passed verification result."""
        result = VerificationResult(
            passed=True,
            original_path=tmp_path / "original.mp4",
            converted_path=tmp_path / "converted.mp4",
        )
        assert result.passed is True
        assert len(result.failed_checks) == 0

    def test_failed_result(self, sample_checks: list[CheckResult], tmp_path: Path) -> None:
        """Test failed verification result."""
        result = VerificationResult(
            passed=False,
            original_path=tmp_path / "original.mp4",
            converted_path=tmp_path / "converted.mp4",
            checks=sample_checks,
        )
        assert result.passed is False
        assert len(result.failed_checks) == 1
        assert len(result.passed_checks) == 2

    def test_checks_by_category(self, sample_checks: list[CheckResult], tmp_path: Path) -> None:
        """Test grouping checks by category."""
        result = VerificationResult(
            passed=False,
            original_path=tmp_path / "original.mp4",
            converted_path=tmp_path / "converted.mp4",
            checks=sample_checks,
        )
        by_category = result.checks_by_category
        assert VerificationCategory.DATE_TIME in by_category
        assert VerificationCategory.GPS in by_category
        assert VerificationCategory.CAMERA in by_category

    def test_get_summary(self, sample_checks: list[CheckResult], tmp_path: Path) -> None:
        """Test summary generation."""
        result = VerificationResult(
            passed=False,
            original_path=tmp_path / "original.mp4",
            converted_path=tmp_path / "converted.mp4",
            checks=sample_checks,
        )
        summary = result.get_summary()
        assert "FAILED" in summary
        assert "2/3 passed" in summary
        assert "1 failed" in summary


class TestMetadataVerifier:
    """Tests for MetadataVerifier class."""

    @pytest.fixture
    def mock_runner(self) -> MagicMock:
        """Create a mock CommandRunner."""
        runner = MagicMock(spec=CommandRunner)
        runner.check_command_exists.return_value = True
        return runner

    @pytest.fixture
    def mock_processor(self, mock_runner: MagicMock) -> MetadataProcessor:
        """Create a MetadataProcessor with mock runner."""
        return MetadataProcessor(mock_runner)

    @pytest.fixture
    def verifier(self, mock_processor: MetadataProcessor) -> MetadataVerifier:
        """Create a MetadataVerifier with mock processor."""
        return MetadataVerifier(metadata_processor=mock_processor)

    @pytest.fixture
    def sample_metadata(self) -> dict:
        """Sample metadata for testing."""
        return {
            "SourceFile": "/path/to/video.mp4",
            "QuickTime:CreateDate": "2024:01:15 10:30:00",
            "QuickTime:ModifyDate": "2024:01:15 10:30:00",
            "Composite:GPSLatitude": 37.7749,
            "Composite:GPSLongitude": -122.4194,
            "Composite:GPSAltitude": 10.5,
            "QuickTime:Make": "Apple",
            "QuickTime:Model": "iPhone 14 Pro",
            "QuickTime:Duration": "00:01:30.50",
            "Composite:Rotation": 0,
            "QuickTime:AudioCodec": "AAC",
            "QuickTime:AudioChannels": 2,
        }

    def test_init_with_processor(self, mock_processor: MetadataProcessor) -> None:
        """Test initialization with provided processor."""
        verifier = MetadataVerifier(metadata_processor=mock_processor)
        assert verifier._processor is mock_processor

    def test_init_without_processor(self) -> None:
        """Test initialization creates default processor."""
        verifier = MetadataVerifier()
        assert verifier._processor is not None
        assert isinstance(verifier._processor, MetadataProcessor)

    def test_tolerance_property(self, verifier: MetadataVerifier) -> None:
        """Test tolerance property getter and setter."""
        default_tol = verifier.tolerance
        assert default_tol.date_seconds == 1.0

        new_tol = ToleranceSettings.strict()
        verifier.tolerance = new_tol
        assert verifier.tolerance.date_seconds == 0.0

    def test_verify_file_not_found(self, verifier: MetadataVerifier, tmp_path: Path) -> None:
        """Test verify raises FileNotFoundError for missing files."""
        converted = tmp_path / "converted.mp4"
        converted.touch()

        with pytest.raises(FileNotFoundError, match="Original"):
            verifier.verify(Path("/nonexistent.mp4"), converted)

        original = tmp_path / "original.mp4"
        original.touch()

        with pytest.raises(FileNotFoundError, match="Converted"):
            verifier.verify(original, Path("/nonexistent.mp4"))


class TestMetadataVerifierDates:
    """Tests for date/time verification."""

    @pytest.fixture
    def mock_runner(self) -> MagicMock:
        """Create a mock CommandRunner."""
        runner = MagicMock(spec=CommandRunner)
        runner.check_command_exists.return_value = True
        return runner

    @pytest.fixture
    def verifier(self, mock_runner: MagicMock) -> MetadataVerifier:
        """Create a MetadataVerifier with mock runner."""
        processor = MetadataProcessor(mock_runner)
        return MetadataVerifier(metadata_processor=processor)

    def test_dates_match(
        self, verifier: MetadataVerifier, mock_runner: MagicMock, tmp_path: Path
    ) -> None:
        """Test verification when dates match exactly."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        metadata = {
            "QuickTime:CreateDate": "2024:01:15 10:30:00",
            "QuickTime:ModifyDate": "2024:01:15 10:30:00",
        }

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout=json.dumps([metadata]),
            stderr="",
        )

        result = verifier.verify(original, converted, categories=[VerificationCategory.DATE_TIME])

        assert result.passed is True
        date_checks = [c for c in result.checks if c.category == VerificationCategory.DATE_TIME]
        assert all(c.passed for c in date_checks)

    def test_dates_within_tolerance(
        self, verifier: MetadataVerifier, mock_runner: MagicMock, tmp_path: Path
    ) -> None:
        """Test verification when dates differ within tolerance."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        orig_meta = {"QuickTime:CreateDate": "2024:01:15 10:30:00"}
        conv_meta = {"QuickTime:CreateDate": "2024:01:15 10:30:01"}

        mock_runner.run.side_effect = [
            CommandResult(0, json.dumps([orig_meta]), ""),
            CommandResult(0, json.dumps([conv_meta]), ""),
        ]

        result = verifier.verify(original, converted, categories=[VerificationCategory.DATE_TIME])

        date_checks = [
            c
            for c in result.checks
            if c.category == VerificationCategory.DATE_TIME and c.field_name == "CreateDate"
        ]
        assert len(date_checks) == 1
        assert date_checks[0].passed is True

    def test_dates_outside_tolerance(
        self, verifier: MetadataVerifier, mock_runner: MagicMock, tmp_path: Path
    ) -> None:
        """Test verification when dates differ beyond tolerance."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        orig_meta = {"QuickTime:CreateDate": "2024:01:15 10:30:00"}
        conv_meta = {"QuickTime:CreateDate": "2024:01:15 10:30:05"}

        mock_runner.run.side_effect = [
            CommandResult(0, json.dumps([orig_meta]), ""),
            CommandResult(0, json.dumps([conv_meta]), ""),
        ]

        result = verifier.verify(original, converted, categories=[VerificationCategory.DATE_TIME])

        date_checks = [
            c
            for c in result.checks
            if c.category == VerificationCategory.DATE_TIME and c.field_name == "CreateDate"
        ]
        assert len(date_checks) == 1
        assert date_checks[0].passed is False

    def test_date_missing_in_converted(
        self, verifier: MetadataVerifier, mock_runner: MagicMock, tmp_path: Path
    ) -> None:
        """Test verification when date is missing in converted file."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        orig_meta = {"QuickTime:CreateDate": "2024:01:15 10:30:00"}
        conv_meta = {"SourceFile": "/converted.mp4"}

        mock_runner.run.side_effect = [
            CommandResult(0, json.dumps([orig_meta]), ""),
            CommandResult(0, json.dumps([conv_meta]), ""),
        ]

        result = verifier.verify(original, converted, categories=[VerificationCategory.DATE_TIME])

        missing_checks = [c for c in result.checks if c.status == CheckStatus.MISSING_IN_CONVERTED]
        assert len(missing_checks) >= 1


class TestMetadataVerifierGPS:
    """Tests for GPS verification."""

    @pytest.fixture
    def mock_runner(self) -> MagicMock:
        """Create a mock CommandRunner."""
        runner = MagicMock(spec=CommandRunner)
        runner.check_command_exists.return_value = True
        return runner

    @pytest.fixture
    def verifier(self, mock_runner: MagicMock) -> MetadataVerifier:
        """Create a MetadataVerifier with mock runner."""
        processor = MetadataProcessor(mock_runner)
        return MetadataVerifier(metadata_processor=processor)

    def test_gps_matches(
        self, verifier: MetadataVerifier, mock_runner: MagicMock, tmp_path: Path
    ) -> None:
        """Test verification when GPS matches."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        metadata = {
            "Composite:GPSLatitude": 37.7749,
            "Composite:GPSLongitude": -122.4194,
        }

        # All 4 calls return the same metadata (matching GPS)
        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout=json.dumps([metadata]),
            stderr="",
        )

        result = verifier.verify(original, converted, categories=[VerificationCategory.GPS])

        gps_checks = [c for c in result.checks if c.category == VerificationCategory.GPS]
        assert len(gps_checks) >= 1
        assert all(c.passed for c in gps_checks)

    def test_gps_mismatch(
        self, verifier: MetadataVerifier, mock_runner: MagicMock, tmp_path: Path
    ) -> None:
        """Test verification when GPS doesn't match."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        orig_meta = {
            "Composite:GPSLatitude": 37.7749,
            "Composite:GPSLongitude": -122.4194,
        }
        conv_meta = {
            "Composite:GPSLatitude": 40.7128,
            "Composite:GPSLongitude": -74.0060,
        }

        # verify() calls extract twice (for general metadata), then GPS handler
        # calls extract again for each file (4 total calls)
        mock_runner.run.side_effect = [
            CommandResult(0, json.dumps([orig_meta]), ""),  # General metadata original
            CommandResult(0, json.dumps([conv_meta]), ""),  # General metadata converted
            CommandResult(0, json.dumps([orig_meta]), ""),  # GPS handler original
            CommandResult(0, json.dumps([conv_meta]), ""),  # GPS handler converted
        ]

        result = verifier.verify(original, converted, categories=[VerificationCategory.GPS])

        gps_checks = [c for c in result.checks if c.category == VerificationCategory.GPS]
        assert any(not c.passed for c in gps_checks)

    def test_gps_missing_in_converted(
        self, verifier: MetadataVerifier, mock_runner: MagicMock, tmp_path: Path
    ) -> None:
        """Test verification when GPS is missing in converted file."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        orig_meta = {
            "Composite:GPSLatitude": 37.7749,
            "Composite:GPSLongitude": -122.4194,
        }
        conv_meta = {"SourceFile": "/converted.mp4"}

        # verify() calls extract twice (for general metadata), then GPS handler
        # calls extract again for each file (4 total calls)
        mock_runner.run.side_effect = [
            CommandResult(0, json.dumps([orig_meta]), ""),  # General metadata original
            CommandResult(0, json.dumps([conv_meta]), ""),  # General metadata converted
            CommandResult(0, json.dumps([orig_meta]), ""),  # GPS handler original
            CommandResult(0, json.dumps([conv_meta]), ""),  # GPS handler converted
        ]

        result = verifier.verify(original, converted, categories=[VerificationCategory.GPS])

        gps_checks = [c for c in result.checks if c.category == VerificationCategory.GPS]
        assert any(c.status == CheckStatus.MISSING_IN_CONVERTED for c in gps_checks)


class TestMetadataVerifierCamera:
    """Tests for camera metadata verification."""

    @pytest.fixture
    def mock_runner(self) -> MagicMock:
        """Create a mock CommandRunner."""
        runner = MagicMock(spec=CommandRunner)
        runner.check_command_exists.return_value = True
        return runner

    @pytest.fixture
    def verifier(self, mock_runner: MagicMock) -> MetadataVerifier:
        """Create a MetadataVerifier with mock runner."""
        processor = MetadataProcessor(mock_runner)
        return MetadataVerifier(metadata_processor=processor)

    def test_camera_exact_match(
        self, verifier: MetadataVerifier, mock_runner: MagicMock, tmp_path: Path
    ) -> None:
        """Test verification when camera info matches exactly."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        metadata = {
            "QuickTime:Make": "Apple",
            "QuickTime:Model": "iPhone 14 Pro",
        }

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout=json.dumps([metadata]),
            stderr="",
        )

        result = verifier.verify(original, converted, categories=[VerificationCategory.CAMERA])

        camera_checks = [c for c in result.checks if c.category == VerificationCategory.CAMERA]
        assert all(c.passed for c in camera_checks)

    def test_camera_mismatch(
        self, verifier: MetadataVerifier, mock_runner: MagicMock, tmp_path: Path
    ) -> None:
        """Test verification when camera info doesn't match."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        orig_meta = {"QuickTime:Make": "Apple"}
        conv_meta = {"QuickTime:Make": "Samsung"}

        mock_runner.run.side_effect = [
            CommandResult(0, json.dumps([orig_meta]), ""),
            CommandResult(0, json.dumps([conv_meta]), ""),
        ]

        result = verifier.verify(original, converted, categories=[VerificationCategory.CAMERA])

        camera_checks = [c for c in result.checks if c.category == VerificationCategory.CAMERA]
        assert any(not c.passed for c in camera_checks)


class TestMetadataVerifierVideo:
    """Tests for video metadata verification."""

    @pytest.fixture
    def mock_runner(self) -> MagicMock:
        """Create a mock CommandRunner."""
        runner = MagicMock(spec=CommandRunner)
        runner.check_command_exists.return_value = True
        return runner

    @pytest.fixture
    def verifier(self, mock_runner: MagicMock) -> MetadataVerifier:
        """Create a MetadataVerifier with mock runner."""
        processor = MetadataProcessor(mock_runner)
        return MetadataVerifier(metadata_processor=processor)

    def test_duration_within_tolerance(
        self, verifier: MetadataVerifier, mock_runner: MagicMock, tmp_path: Path
    ) -> None:
        """Test verification when duration differs within tolerance."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        orig_meta = {"QuickTime:Duration": "00:01:30.50"}
        conv_meta = {"QuickTime:Duration": "00:01:30.55"}

        mock_runner.run.side_effect = [
            CommandResult(0, json.dumps([orig_meta]), ""),
            CommandResult(0, json.dumps([conv_meta]), ""),
        ]

        result = verifier.verify(original, converted, categories=[VerificationCategory.VIDEO])

        duration_checks = [
            c
            for c in result.checks
            if c.category == VerificationCategory.VIDEO and c.field_name == "Duration"
        ]
        assert len(duration_checks) == 1
        assert duration_checks[0].passed is True

    def test_duration_outside_tolerance(
        self, verifier: MetadataVerifier, mock_runner: MagicMock, tmp_path: Path
    ) -> None:
        """Test verification when duration differs beyond tolerance."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        orig_meta = {"QuickTime:Duration": "00:01:30.00"}
        conv_meta = {"QuickTime:Duration": "00:01:31.00"}

        mock_runner.run.side_effect = [
            CommandResult(0, json.dumps([orig_meta]), ""),
            CommandResult(0, json.dumps([conv_meta]), ""),
        ]

        result = verifier.verify(original, converted, categories=[VerificationCategory.VIDEO])

        duration_checks = [
            c
            for c in result.checks
            if c.category == VerificationCategory.VIDEO and c.field_name == "Duration"
        ]
        assert len(duration_checks) == 1
        assert duration_checks[0].passed is False


class TestMetadataVerifierAudio:
    """Tests for audio metadata verification."""

    @pytest.fixture
    def mock_runner(self) -> MagicMock:
        """Create a mock CommandRunner."""
        runner = MagicMock(spec=CommandRunner)
        runner.check_command_exists.return_value = True
        return runner

    @pytest.fixture
    def verifier(self, mock_runner: MagicMock) -> MetadataVerifier:
        """Create a MetadataVerifier with mock runner."""
        processor = MetadataProcessor(mock_runner)
        return MetadataVerifier(metadata_processor=processor)

    def test_audio_exact_match(
        self, verifier: MetadataVerifier, mock_runner: MagicMock, tmp_path: Path
    ) -> None:
        """Test verification when audio info matches exactly."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        metadata = {
            "QuickTime:AudioCodec": "AAC",
            "QuickTime:AudioChannels": 2,
        }

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout=json.dumps([metadata]),
            stderr="",
        )

        result = verifier.verify(original, converted, categories=[VerificationCategory.AUDIO])

        audio_checks = [c for c in result.checks if c.category == VerificationCategory.AUDIO]
        assert all(c.passed for c in audio_checks)

    def test_audio_codec_mismatch(
        self, verifier: MetadataVerifier, mock_runner: MagicMock, tmp_path: Path
    ) -> None:
        """Test verification when audio codec doesn't match."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        orig_meta = {"QuickTime:AudioCodec": "AAC"}
        conv_meta = {"QuickTime:AudioCodec": "MP3"}

        mock_runner.run.side_effect = [
            CommandResult(0, json.dumps([orig_meta]), ""),
            CommandResult(0, json.dumps([conv_meta]), ""),
        ]

        result = verifier.verify(original, converted, categories=[VerificationCategory.AUDIO])

        audio_checks = [c for c in result.checks if c.category == VerificationCategory.AUDIO]
        assert any(not c.passed for c in audio_checks)


class TestMetadataVerifierIntegration:
    """Integration tests for full verification flow."""

    @pytest.fixture
    def mock_runner(self) -> MagicMock:
        """Create a mock CommandRunner."""
        runner = MagicMock(spec=CommandRunner)
        runner.check_command_exists.return_value = True
        return runner

    @pytest.fixture
    def verifier(self, mock_runner: MagicMock) -> MetadataVerifier:
        """Create a MetadataVerifier with mock runner."""
        processor = MetadataProcessor(mock_runner)
        return MetadataVerifier(metadata_processor=processor)

    def test_full_verification_pass(
        self, verifier: MetadataVerifier, mock_runner: MagicMock, tmp_path: Path
    ) -> None:
        """Test full verification when all categories pass."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        metadata = {
            "QuickTime:CreateDate": "2024:01:15 10:30:00",
            "QuickTime:ModifyDate": "2024:01:15 10:30:00",
            "Composite:GPSLatitude": 37.7749,
            "Composite:GPSLongitude": -122.4194,
            "QuickTime:Make": "Apple",
            "QuickTime:Model": "iPhone 14 Pro",
            "QuickTime:Duration": "00:01:30.00",
            "Composite:Rotation": 0,
            "QuickTime:AudioCodec": "AAC",
            "QuickTime:AudioChannels": 2,
        }

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout=json.dumps([metadata]),
            stderr="",
        )

        result = verifier.verify(original, converted)

        assert result.passed is True
        assert len(result.failed_checks) == 0

    def test_full_verification_fail(
        self, verifier: MetadataVerifier, mock_runner: MagicMock, tmp_path: Path
    ) -> None:
        """Test full verification when some categories fail."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        orig_meta = {
            "QuickTime:CreateDate": "2024:01:15 10:30:00",
            "Composite:GPSLatitude": 37.7749,
            "Composite:GPSLongitude": -122.4194,
            "QuickTime:Make": "Apple",
        }
        conv_meta = {
            "QuickTime:CreateDate": "2024:01:15 10:30:00",
            "QuickTime:Make": "Samsung",
        }

        mock_runner.run.side_effect = [
            CommandResult(0, json.dumps([orig_meta]), ""),
            CommandResult(0, json.dumps([conv_meta]), ""),
        ]

        result = verifier.verify(original, converted)

        assert result.passed is False
        assert len(result.failed_checks) >= 1

    def test_custom_tolerance(
        self, verifier: MetadataVerifier, mock_runner: MagicMock, tmp_path: Path
    ) -> None:
        """Test verification with custom tolerance settings."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        orig_meta = {"QuickTime:CreateDate": "2024:01:15 10:30:00"}
        conv_meta = {"QuickTime:CreateDate": "2024:01:15 10:30:30"}

        mock_runner.run.side_effect = [
            CommandResult(0, json.dumps([orig_meta]), ""),
            CommandResult(0, json.dumps([conv_meta]), ""),
        ]

        result = verifier.verify(
            original,
            converted,
            tolerance=ToleranceSettings.relaxed(),
            categories=[VerificationCategory.DATE_TIME],
        )

        date_checks = [
            c
            for c in result.checks
            if c.category == VerificationCategory.DATE_TIME and c.field_name == "CreateDate"
        ]
        assert len(date_checks) == 1
        assert date_checks[0].passed is True

    def test_select_categories(
        self, verifier: MetadataVerifier, mock_runner: MagicMock, tmp_path: Path
    ) -> None:
        """Test verification with specific categories only."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        metadata = {
            "QuickTime:CreateDate": "2024:01:15 10:30:00",
            "QuickTime:Make": "Apple",
        }

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout=json.dumps([metadata]),
            stderr="",
        )

        result = verifier.verify(
            original,
            converted,
            categories=[VerificationCategory.DATE_TIME, VerificationCategory.CAMERA],
        )

        categories_in_result = {c.category for c in result.checks}
        assert VerificationCategory.GPS not in categories_in_result
        assert VerificationCategory.VIDEO not in categories_in_result
        assert VerificationCategory.AUDIO not in categories_in_result


class TestParseDuration:
    """Tests for duration parsing."""

    @pytest.fixture
    def verifier(self) -> MetadataVerifier:
        """Create a MetadataVerifier."""
        return MetadataVerifier()

    def test_parse_hms_format(self, verifier: MetadataVerifier) -> None:
        """Test parsing HH:MM:SS.ss format."""
        result = verifier._parse_duration("01:30:45.50")
        assert result == pytest.approx(5445.50)

    def test_parse_ms_format(self, verifier: MetadataVerifier) -> None:
        """Test parsing MM:SS.ss format."""
        result = verifier._parse_duration("01:30.50")
        assert result == pytest.approx(90.50)

    def test_parse_seconds_format(self, verifier: MetadataVerifier) -> None:
        """Test parsing SS.ss s format."""
        result = verifier._parse_duration("90.5 s")
        assert result == pytest.approx(90.5)

    def test_parse_numeric(self, verifier: MetadataVerifier) -> None:
        """Test parsing numeric value."""
        result = verifier._parse_duration(90.5)
        assert result == pytest.approx(90.5)

    def test_parse_string_numeric(self, verifier: MetadataVerifier) -> None:
        """Test parsing string numeric value."""
        result = verifier._parse_duration("90.5")
        assert result == pytest.approx(90.5)

    def test_parse_invalid(self, verifier: MetadataVerifier) -> None:
        """Test parsing invalid value returns None."""
        result = verifier._parse_duration("invalid")
        assert result is None


class TestParseDatetime:
    """Tests for datetime parsing."""

    @pytest.fixture
    def verifier(self) -> MetadataVerifier:
        """Create a MetadataVerifier."""
        return MetadataVerifier()

    def test_parse_exif_format(self, verifier: MetadataVerifier) -> None:
        """Test parsing EXIF date format."""
        result = verifier._parse_datetime("2024:01:15 10:30:00")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30

    def test_parse_iso_format(self, verifier: MetadataVerifier) -> None:
        """Test parsing ISO date format."""
        result = verifier._parse_datetime("2024-01-15T10:30:00")
        assert result is not None
        assert result.year == 2024

    def test_parse_datetime_object(self, verifier: MetadataVerifier) -> None:
        """Test parsing datetime object."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = verifier._parse_datetime(dt)
        assert result is dt

    def test_parse_invalid(self, verifier: MetadataVerifier) -> None:
        """Test parsing invalid value returns None."""
        result = verifier._parse_datetime("invalid")
        assert result is None
