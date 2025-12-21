"""Unit tests for GPS handling module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from video_converter.processors.gps import (
    GPSCoordinates,
    GPSFormat,
    GPSHandler,
    GPSVerificationResult,
)
from video_converter.processors.metadata import MetadataProcessor
from video_converter.utils.command_runner import CommandResult, CommandRunner


class TestGPSCoordinates:
    """Tests for GPSCoordinates dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic coordinate creation."""
        coords = GPSCoordinates(latitude=37.7749, longitude=-122.4194)
        assert coords.latitude == pytest.approx(37.7749)
        assert coords.longitude == pytest.approx(-122.4194)
        assert coords.altitude is None
        assert coords.accuracy is None

    def test_creation_with_altitude_and_accuracy(self) -> None:
        """Test creation with all optional fields."""
        coords = GPSCoordinates(
            latitude=37.7749,
            longitude=-122.4194,
            altitude=10.5,
            accuracy=5.0,
        )
        assert coords.altitude == pytest.approx(10.5)
        assert coords.accuracy == pytest.approx(5.0)

    def test_invalid_latitude(self) -> None:
        """Test that invalid latitude raises ValueError."""
        with pytest.raises(ValueError, match="Latitude"):
            GPSCoordinates(latitude=91.0, longitude=0.0)
        with pytest.raises(ValueError, match="Latitude"):
            GPSCoordinates(latitude=-91.0, longitude=0.0)

    def test_invalid_longitude(self) -> None:
        """Test that invalid longitude raises ValueError."""
        with pytest.raises(ValueError, match="Longitude"):
            GPSCoordinates(latitude=0.0, longitude=181.0)
        with pytest.raises(ValueError, match="Longitude"):
            GPSCoordinates(latitude=0.0, longitude=-181.0)

    def test_str_north_east(self) -> None:
        """Test string representation for north-east coordinates."""
        coords = GPSCoordinates(latitude=37.7749, longitude=122.4194)
        result = str(coords)
        assert "37.774900°N" in result
        assert "122.419400°E" in result

    def test_str_south_west(self) -> None:
        """Test string representation for south-west coordinates."""
        coords = GPSCoordinates(latitude=-33.8688, longitude=-151.2093)
        result = str(coords)
        assert "33.868800°S" in result
        assert "151.209300°W" in result

    def test_str_with_altitude(self) -> None:
        """Test string includes altitude when present."""
        coords = GPSCoordinates(latitude=37.0, longitude=122.0, altitude=100.5)
        result = str(coords)
        assert "100.5m" in result

    def test_str_with_accuracy(self) -> None:
        """Test string includes accuracy when present."""
        coords = GPSCoordinates(
            latitude=37.0, longitude=122.0, accuracy=5.0
        )
        result = str(coords)
        assert "±5.0m" in result


class TestGPSCoordinatesToQuicktime:
    """Tests for QuickTime format conversion."""

    def test_positive_coordinates(self) -> None:
        """Test QuickTime format for positive coordinates."""
        coords = GPSCoordinates(latitude=37.7749, longitude=122.4194)
        result = coords.to_quicktime()
        assert result == "+37.774900+122.419400/"

    def test_negative_coordinates(self) -> None:
        """Test QuickTime format for negative coordinates."""
        coords = GPSCoordinates(latitude=-33.8688, longitude=-151.2093)
        result = coords.to_quicktime()
        assert result == "-33.868800-151.209300/"

    def test_mixed_coordinates(self) -> None:
        """Test QuickTime format for mixed sign coordinates."""
        coords = GPSCoordinates(latitude=37.7749, longitude=-122.4194)
        result = coords.to_quicktime()
        assert result == "+37.774900-122.419400/"

    def test_with_altitude(self) -> None:
        """Test QuickTime format includes altitude."""
        coords = GPSCoordinates(
            latitude=37.7749, longitude=-122.4194, altitude=10.5
        )
        result = coords.to_quicktime()
        assert result == "+37.774900-122.419400+10.50/"

    def test_with_negative_altitude(self) -> None:
        """Test QuickTime format with negative altitude (below sea level)."""
        coords = GPSCoordinates(
            latitude=37.7749, longitude=-122.4194, altitude=-50.0
        )
        result = coords.to_quicktime()
        assert result == "+37.774900-122.419400-50.00/"


class TestGPSCoordinatesToXMP:
    """Tests for XMP format conversion."""

    def test_north_east(self) -> None:
        """Test XMP format for north-east coordinates."""
        coords = GPSCoordinates(latitude=37.7749, longitude=122.4194)
        lat, lon = coords.to_xmp()
        assert lat == "37.774900 N"
        assert lon == "122.419400 E"

    def test_south_west(self) -> None:
        """Test XMP format for south-west coordinates."""
        coords = GPSCoordinates(latitude=-33.8688, longitude=-151.2093)
        lat, lon = coords.to_xmp()
        assert lat == "33.868800 S"
        assert lon == "151.209300 W"


class TestGPSCoordinatesToExifDMS:
    """Tests for EXIF DMS format conversion."""

    def test_simple_conversion(self) -> None:
        """Test DMS conversion for simple coordinates."""
        coords = GPSCoordinates(latitude=37.775, longitude=-122.4194)
        lat, lat_ref, lon, lon_ref = coords.to_exif_dms()
        assert lat_ref == "N"
        assert lon_ref == "W"
        # 37.775 = 37° 46' 30.00"
        assert "37 deg 46'" in lat

    def test_southern_coordinates(self) -> None:
        """Test DMS conversion for southern coordinates."""
        coords = GPSCoordinates(latitude=-33.8688, longitude=151.2093)
        lat, lat_ref, lon, lon_ref = coords.to_exif_dms()
        assert lat_ref == "S"
        assert lon_ref == "E"


class TestGPSCoordinatesFromQuicktime:
    """Tests for parsing QuickTime format."""

    def test_basic_format(self) -> None:
        """Test parsing basic QuickTime format."""
        coords = GPSCoordinates.from_quicktime("+37.774900-122.419400/")
        assert coords is not None
        assert coords.latitude == pytest.approx(37.7749, rel=1e-5)
        assert coords.longitude == pytest.approx(-122.4194, rel=1e-5)
        assert coords.source_format == GPSFormat.QUICKTIME

    def test_with_altitude(self) -> None:
        """Test parsing QuickTime format with altitude."""
        coords = GPSCoordinates.from_quicktime("+37.774900-122.419400+10.50/")
        assert coords is not None
        assert coords.altitude == pytest.approx(10.5)

    def test_without_trailing_slash(self) -> None:
        """Test parsing without trailing slash."""
        coords = GPSCoordinates.from_quicktime("+37.774900-122.419400")
        assert coords is not None
        assert coords.latitude == pytest.approx(37.7749, rel=1e-5)

    def test_invalid_format(self) -> None:
        """Test parsing invalid format returns None."""
        assert GPSCoordinates.from_quicktime("invalid") is None
        assert GPSCoordinates.from_quicktime("") is None


class TestGPSCoordinatesFromXMP:
    """Tests for parsing XMP format."""

    def test_basic_format(self) -> None:
        """Test parsing basic XMP format."""
        coords = GPSCoordinates.from_xmp("37.7749 N", "122.4194 W")
        assert coords is not None
        assert coords.latitude == pytest.approx(37.7749)
        assert coords.longitude == pytest.approx(-122.4194)
        assert coords.source_format == GPSFormat.XMP

    def test_comma_separator(self) -> None:
        """Test parsing XMP format with comma separator."""
        coords = GPSCoordinates.from_xmp("37.7749,N", "122.4194,W")
        assert coords is not None
        assert coords.latitude == pytest.approx(37.7749)

    def test_lowercase_direction(self) -> None:
        """Test parsing with lowercase direction."""
        coords = GPSCoordinates.from_xmp("37.7749 n", "122.4194 w")
        assert coords is not None
        assert coords.latitude == pytest.approx(37.7749)

    def test_invalid_format(self) -> None:
        """Test parsing invalid format returns None."""
        assert GPSCoordinates.from_xmp("invalid", "invalid") is None
        assert GPSCoordinates.from_xmp("37.7749", "122.4194") is None


class TestGPSCoordinatesFromExifDMS:
    """Tests for parsing EXIF DMS format."""

    def test_basic_format(self) -> None:
        """Test parsing basic DMS format."""
        coords = GPSCoordinates.from_exif_dms(
            "37 deg 46' 30.00\"", "N",
            "122 deg 25' 10.00\"", "W",
        )
        assert coords is not None
        assert coords.latitude == pytest.approx(37.775, rel=0.001)
        assert coords.longitude == pytest.approx(-122.4194, rel=0.001)
        assert coords.source_format == GPSFormat.EXIF

    def test_degree_symbol(self) -> None:
        """Test parsing with degree symbol."""
        coords = GPSCoordinates.from_exif_dms(
            "37° 46' 30.00\"", "N",
            "122° 25' 10.00\"", "W",
        )
        assert coords is not None

    def test_colon_separator(self) -> None:
        """Test parsing with colon separator."""
        coords = GPSCoordinates.from_exif_dms(
            "37:46:30.00", "N",
            "122:25:10.00", "W",
        )
        assert coords is not None


class TestGPSCoordinatesMatches:
    """Tests for coordinate matching."""

    def test_exact_match(self) -> None:
        """Test exact coordinate matching."""
        coords1 = GPSCoordinates(latitude=37.7749, longitude=-122.4194)
        coords2 = GPSCoordinates(latitude=37.7749, longitude=-122.4194)
        assert coords1.matches(coords2) is True

    def test_within_default_tolerance(self) -> None:
        """Test matching within default tolerance (~0.1m)."""
        coords1 = GPSCoordinates(latitude=37.7749, longitude=-122.4194)
        coords2 = GPSCoordinates(
            latitude=37.7749 + 0.0000005,
            longitude=-122.4194 + 0.0000005,
        )
        assert coords1.matches(coords2) is True

    def test_outside_default_tolerance(self) -> None:
        """Test non-matching outside default tolerance."""
        coords1 = GPSCoordinates(latitude=37.7749, longitude=-122.4194)
        coords2 = GPSCoordinates(
            latitude=37.7749 + 0.00001,
            longitude=-122.4194 + 0.00001,
        )
        assert coords1.matches(coords2) is False

    def test_custom_tolerance(self) -> None:
        """Test matching with custom tolerance."""
        coords1 = GPSCoordinates(latitude=37.7749, longitude=-122.4194)
        coords2 = GPSCoordinates(
            latitude=37.7749 + 0.0001,
            longitude=-122.4194 + 0.0001,
        )
        # Should fail with default tolerance
        assert coords1.matches(coords2) is False
        # Should pass with larger tolerance
        assert coords1.matches(coords2, tolerance=0.001) is True


class TestGPSCoordinatesDistance:
    """Tests for distance calculation."""

    def test_same_location(self) -> None:
        """Test distance to same location is zero."""
        coords1 = GPSCoordinates(latitude=37.7749, longitude=-122.4194)
        coords2 = GPSCoordinates(latitude=37.7749, longitude=-122.4194)
        assert coords1.distance_to(coords2) == pytest.approx(0, abs=0.01)

    def test_short_distance(self) -> None:
        """Test short distance calculation (~100m)."""
        coords1 = GPSCoordinates(latitude=37.7749, longitude=-122.4194)
        coords2 = GPSCoordinates(latitude=37.7759, longitude=-122.4194)
        # ~111m per degree of latitude
        distance = coords1.distance_to(coords2)
        assert 100 < distance < 150

    def test_known_distance(self) -> None:
        """Test distance between known points."""
        # San Francisco to Los Angeles (~559 km)
        sf = GPSCoordinates(latitude=37.7749, longitude=-122.4194)
        la = GPSCoordinates(latitude=34.0522, longitude=-118.2437)
        distance = sf.distance_to(la)
        assert 550_000 < distance < 570_000  # meters


class TestGPSVerificationResult:
    """Tests for GPSVerificationResult dataclass."""

    def test_passed_result(self) -> None:
        """Test passed verification result."""
        coords = GPSCoordinates(latitude=37.7749, longitude=-122.4194)
        result = GPSVerificationResult(
            passed=True,
            original=coords,
            converted=coords,
            distance_meters=0.0,
        )
        assert result.passed is True

    def test_failed_result(self) -> None:
        """Test failed verification result."""
        result = GPSVerificationResult(
            passed=False,
            original=GPSCoordinates(latitude=37.7749, longitude=-122.4194),
            converted=None,
            details="GPS missing in converted file",
        )
        assert result.passed is False
        assert "missing" in result.details


class TestGPSHandler:
    """Tests for GPSHandler class."""

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
    def handler(self, mock_processor: MetadataProcessor) -> GPSHandler:
        """Create a GPSHandler with mock processor."""
        return GPSHandler(mock_processor)

    @pytest.fixture
    def sample_metadata_with_gps(self) -> dict:
        """Sample metadata with GPS data."""
        return {
            "SourceFile": "/path/to/video.mp4",
            "Composite:GPSLatitude": 37.7749,
            "Composite:GPSLongitude": -122.4194,
            "Composite:GPSAltitude": 10.5,
        }

    @pytest.fixture
    def sample_metadata_no_gps(self) -> dict:
        """Sample metadata without GPS data."""
        return {
            "SourceFile": "/path/to/video.mp4",
            "QuickTime:CreateDate": "2024:01:15 10:30:00",
        }

    def test_init_with_processor(self, mock_processor: MetadataProcessor) -> None:
        """Test initialization with provided processor."""
        handler = GPSHandler(mock_processor)
        assert handler._processor is mock_processor

    def test_init_without_processor(self) -> None:
        """Test initialization creates default processor."""
        handler = GPSHandler()
        assert handler._processor is not None
        assert isinstance(handler._processor, MetadataProcessor)

    def test_extract_with_gps(
        self,
        handler: GPSHandler,
        mock_runner: MagicMock,
        sample_metadata_with_gps: dict,
        tmp_path: Path,
    ) -> None:
        """Test extracting GPS from file with GPS data."""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout=json.dumps([sample_metadata_with_gps]),
            stderr="",
        )

        coords = handler.extract(video_file)

        assert coords is not None
        assert coords.latitude == pytest.approx(37.7749)
        assert coords.longitude == pytest.approx(-122.4194)
        assert coords.altitude == pytest.approx(10.5)

    def test_extract_without_gps(
        self,
        handler: GPSHandler,
        mock_runner: MagicMock,
        sample_metadata_no_gps: dict,
        tmp_path: Path,
    ) -> None:
        """Test extracting GPS from file without GPS data."""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout=json.dumps([sample_metadata_no_gps]),
            stderr="",
        )

        coords = handler.extract(video_file)
        assert coords is None

    def test_extract_file_not_found(self, handler: GPSHandler) -> None:
        """Test extract raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            handler.extract(Path("/nonexistent/video.mp4"))

    def test_extract_quicktime_format(
        self,
        handler: GPSHandler,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test extracting GPS in QuickTime format."""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        metadata = {
            "SourceFile": "/video.mp4",
            "QuickTime:GPSCoordinates": "+37.774900-122.419400/",
        }

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout=json.dumps([metadata]),
            stderr="",
        )

        coords = handler.extract(video_file)

        assert coords is not None
        assert coords.latitude == pytest.approx(37.7749, rel=1e-4)
        assert coords.longitude == pytest.approx(-122.4194, rel=1e-4)

    def test_extract_gps_position_format(
        self,
        handler: GPSHandler,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test extracting GPS from composite GPSPosition."""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        metadata = {
            "SourceFile": "/video.mp4",
            "Composite:GPSPosition": "37.7749 -122.4194",
        }

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout=json.dumps([metadata]),
            stderr="",
        )

        coords = handler.extract(video_file)

        assert coords is not None
        assert coords.latitude == pytest.approx(37.7749)
        assert coords.longitude == pytest.approx(-122.4194)

    def test_has_gps_true(
        self,
        handler: GPSHandler,
        mock_runner: MagicMock,
        sample_metadata_with_gps: dict,
        tmp_path: Path,
    ) -> None:
        """Test has_gps returns True when GPS exists."""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout=json.dumps([sample_metadata_with_gps]),
            stderr="",
        )

        assert handler.has_gps(video_file) is True

    def test_has_gps_false(
        self,
        handler: GPSHandler,
        mock_runner: MagicMock,
        sample_metadata_no_gps: dict,
        tmp_path: Path,
    ) -> None:
        """Test has_gps returns False when no GPS exists."""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout=json.dumps([sample_metadata_no_gps]),
            stderr="",
        )

        assert handler.has_gps(video_file) is False

    def test_has_gps_file_not_found(self, handler: GPSHandler) -> None:
        """Test has_gps returns False for missing file."""
        assert handler.has_gps(Path("/nonexistent.mp4")) is False


class TestGPSHandlerVerify:
    """Tests for GPSHandler.verify method."""

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
    def handler(self, mock_processor: MetadataProcessor) -> GPSHandler:
        """Create a GPSHandler with mock processor."""
        return GPSHandler(mock_processor)

    def test_verify_both_have_matching_gps(
        self,
        handler: GPSHandler,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test verification when both files have matching GPS."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        metadata = {
            "Composite:GPSLatitude": 37.7749,
            "Composite:GPSLongitude": -122.4194,
        }

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout=json.dumps([metadata]),
            stderr="",
        )

        result = handler.verify(original, converted)

        assert result.passed is True
        assert result.original is not None
        assert result.converted is not None
        assert "preserved" in result.details.lower()

    def test_verify_gps_missing_in_converted(
        self,
        handler: GPSHandler,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test verification when GPS is missing in converted file."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        orig_metadata = {
            "Composite:GPSLatitude": 37.7749,
            "Composite:GPSLongitude": -122.4194,
        }
        conv_metadata = {"SourceFile": "/converted.mp4"}

        mock_runner.run.side_effect = [
            CommandResult(0, json.dumps([orig_metadata]), ""),
            CommandResult(0, json.dumps([conv_metadata]), ""),
        ]

        result = handler.verify(original, converted)

        assert result.passed is False
        assert result.original is not None
        assert result.converted is None
        assert "missing" in result.details.lower()

    def test_verify_no_gps_in_original(
        self,
        handler: GPSHandler,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test verification when original has no GPS (should pass)."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        metadata = {"SourceFile": "/video.mp4"}

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout=json.dumps([metadata]),
            stderr="",
        )

        result = handler.verify(original, converted)

        assert result.passed is True
        assert result.original is None
        assert "No GPS" in result.details

    def test_verify_gps_mismatch(
        self,
        handler: GPSHandler,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test verification when GPS coordinates don't match."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        orig_metadata = {
            "Composite:GPSLatitude": 37.7749,
            "Composite:GPSLongitude": -122.4194,
        }
        conv_metadata = {
            "Composite:GPSLatitude": 40.7128,  # New York
            "Composite:GPSLongitude": -74.0060,
        }

        mock_runner.run.side_effect = [
            CommandResult(0, json.dumps([orig_metadata]), ""),
            CommandResult(0, json.dumps([conv_metadata]), ""),
        ]

        result = handler.verify(original, converted)

        assert result.passed is False
        assert result.distance_meters is not None
        assert result.distance_meters > 1000  # Different cities

    def test_verify_file_not_found(
        self,
        handler: GPSHandler,
        tmp_path: Path,
    ) -> None:
        """Test verify raises FileNotFoundError for missing files."""
        converted = tmp_path / "converted.mp4"
        converted.touch()

        with pytest.raises(FileNotFoundError, match="Original"):
            handler.verify(Path("/nonexistent.mp4"), converted)

        original = tmp_path / "original.mp4"
        original.touch()

        with pytest.raises(FileNotFoundError, match="Converted"):
            handler.verify(original, Path("/nonexistent.mp4"))


class TestGPSHandlerCopy:
    """Tests for GPSHandler.copy method."""

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
    def handler(self, mock_processor: MetadataProcessor) -> GPSHandler:
        """Create a GPSHandler with mock processor."""
        return GPSHandler(mock_processor)

    def test_copy_success(
        self,
        handler: GPSHandler,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test successful GPS copy."""
        source = tmp_path / "source.mp4"
        dest = tmp_path / "dest.mp4"
        source.touch()
        dest.touch()

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout="1 image files updated",
            stderr="",
        )

        result = handler.copy(source, dest)

        assert result is True
        # Verify GPS tags were requested
        call_args = mock_runner.run.call_args[0][0]
        assert "-GPS*" in call_args or "GPS" in str(call_args)


class TestGPSHandlerApply:
    """Tests for GPSHandler.apply method."""

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
    def handler(self, mock_processor: MetadataProcessor) -> GPSHandler:
        """Create a GPSHandler with mock processor."""
        return GPSHandler(mock_processor)

    def test_apply_success(
        self,
        handler: GPSHandler,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test successful GPS application."""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        coords = GPSCoordinates(
            latitude=37.7749,
            longitude=-122.4194,
            altitude=10.5,
        )

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout="1 image files updated",
            stderr="",
        )

        result = handler.apply(video_file, coords)

        assert result is True

    def test_apply_file_not_found(self, handler: GPSHandler) -> None:
        """Test apply raises FileNotFoundError for missing file."""
        coords = GPSCoordinates(latitude=37.7749, longitude=-122.4194)

        with pytest.raises(FileNotFoundError):
            handler.apply(Path("/nonexistent.mp4"), coords)
